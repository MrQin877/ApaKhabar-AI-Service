# Separate judge and DeepEval

The writer still plans, researches and writes. With `EVALUATOR_ENABLED=true`, only
the Reflection step uses the configured judge. The judge sees source evidence,
the draft and completeness findings, not the writer's earlier quality score.
Existing deterministic table checks still run after model evaluation.

The app does not require DeepEval. DeepEval is an optional offline benchmark
runner, isolated from production dependencies. Both use the separate judge.

## Evaluation scope

Production Reflection reviews the **draft against supplied sources**. It does not independently audit every extracted information item against the original file. Laravel extraction-quality scores use evidence, completeness, and model-confidence heuristics. DeepEval currently runs synthetic draft calibration cases, not extraction benchmarks. A draft score is neither an extraction accuracy score nor a percentage of factual correctness.

The workflow computes the final weighted score from judge dimensions: accuracy 30%, completeness 20%, relevance 15%, readability 10%, structure 10%, language 10%, safety 5%. Deterministic checks can still require review or block publication.

## Configure the hosted evaluator

Set these in the AI Service `.env`, then restart Uvicorn:

```dotenv
EVALUATOR_ENABLED=true
EVALUATOR_BASE_URL=https://api.groq.com/openai/v1
EVALUATOR_API_KEY=your-provider-key
EVALUATOR_MODEL=your-available-judge-model
EVALUATOR_TIMEOUT_SECONDS=180
EVALUATOR_MAX_TOKENS=4096
```

The writer uses independent `AI_BASE_URL`, `AI_API_KEY`, and `AI_MODEL` settings.
The application rejects identical writer/judge model names. Distinct aliases do
not by themselves establish independent underlying models. Both endpoints need
usable provider quota. Probe them separately with `/health/models` and
`/health/models?target=evaluator` using the service authentication header.
These probes perform inference and consume quota. No local generation server is required.

Existing saved scores are not re-evaluated automatically. Generate a new draft
to verify the new evaluator metadata. The UI identifies the evaluator and displays
scores out of 100, not as probabilities of accuracy. A judge outage retains the
draft with `evaluation_unavailable` and blocks publishing. It does not silently
fall back to self-review. The numeric zero stored for compatibility is not a
measured score and is hidden by the badge. Regenerate after restoring the judge.

## Run DeepEval locally

Use a separate Python environment so evaluation dependencies cannot change the
working AI Service environment:

```sh
python -m venv .venv-eval
# macOS/Linux:
.venv-eval/bin/python -m pip install -r requirements-evaluation.txt
.venv-eval/bin/python scripts/evaluate_news_deepeval.py
```

Windows PowerShell:

```powershell
.\.venv-eval\Scripts\python.exe -m pip install -r requirements-evaluation.txt
.\.venv-eval\Scripts\python.exe scripts/evaluate_news_deepeval.py
```

The runner explicitly supplies the hosted judge to every metric and writes
`evaluation/results/judge_report.json`. It does not call the hosted evaluation
dashboard. Model execution errors are recorded separately from failed quality
checks. A nonzero exit code means execution failed or the judge disagreed with
at least one expected label; it must not be reported as a passing benchmark.

`evaluation/judge_calibration.json` contains synthetic examples: one supported
draft and deliberately flawed drafts with a wrong count, invented income effect,
and planned assistance misrepresented as completed. These are calibration cases,
not measured production accuracy. Edit/add cases using the same JSON fields:
`id`, `prompt`, `sources`, `reference`, `draft`, `expected_pass`.

For presentation evidence, have two people label a larger diverse dataset, resolve
disagreements, and reserve a held-out subset before tuning. Report judge agreement,
missed errors and false alarms as well as writing scores. Compare generations from
the old and new flows against the same references. Do not tune on the held-out
set or treat the evaluator's own scores as independent ground truth.

References: https://deepeval.com/guides/guides-using-custom-llms and
https://huggingface.co/Qwen/Qwen3-4B-GGUF

## Historical local-model smoke results (29 September 2026)

DeepEval 3.9.9 with Qwen3-4B Q4_K_M completed all four calibration cases.
Agreement was 3/4 (75% on these four examples only). It rejected the wrong total
and invented income claim, but scored the planned-as-completed example 0.8,
which incorrectly passed the 0.8 threshold despite its explanation noticing the
contradiction. Do not present this as validated reliability or change the cutoff
solely to make this tiny set pass. Collect independent labels and more held-out
cases; evaluate a stronger judge if needed.

A separate live full graph test completed with Gemma writing and apakhabar-judge
assessing five claims. The returned editorial score was 94/100. That is a smoke
test of routing and structured output, not a measurement of factual accuracy.

The direct claim-level Reflection check also missed the planned-versus-completed
error in a separate call. The separate evaluator remains disabled by default in application settings.
The local `.env` inspected on 1 October 2026 enables it; restart Uvicorn after
configuration changes, and use returned evaluator metadata to confirm routing.
Enabling the judge does not resolve the calibration limitation or make it
independently validated. Human review and deterministic checks remain necessary.
