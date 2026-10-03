# Document-backed API evaluation cases

These cases call real extraction and generation APIs. Expected answers stay in the local manifests and are never included in model requests. Results require human review: no automatic accuracy percentage is claimed.

## Run

Use a separate terminal for an evaluation-only API instance, from the AI Service repository:

```bash
CHROMA_PATH=./data/evaluation/chroma UPLOAD_PATH=./data/evaluation/uploads AGENT_DB_PATH=./data/evaluation/checkpoints.sqlite python -m uvicorn app.main:app --port 8003
```

Keep the generation model and configured judge server running. Export `APAKHABAR_AI_SERVICE_TOKEN` in the runner terminal if API authentication is enabled (the runner does not read .env). On Windows, set the three environment variables with PowerShell `$env:NAME='value'` before starting uvicorn.

```bash
python scripts/run_api_cases.py
python scripts/run_api_cases.py --case TC13 --run
python scripts/run_api_cases.py --run
```

Without `--run`, only file availability is checked. Reports go to `evaluations/results/<timestamp>/`. They contain each extraction, the API response, elapsed time and the expected-behaviour checklist. API errors are recorded and remaining cases continue. Judge feedback is in the generation response; it is not independently measured accuracy.

## Scope and limitations

- TC01–TC11 (including TC10_PDF) and TC13/14/16 exercise extraction followed by news generation. TC15/17 use the conversation API to summarise extracted facts, without forcing a news draft.
- Clarification and source-approval responses are saved for inspection, not answered automatically. TC13 should expose conflicting totals; TC14 may ask for date/location. No invented answers are supplied.
- This isolates Python extraction and model behaviour. It does not test Laravel moderation, publishing, background jobs or automatic historical retrieval. Extracted facts are caller-supplied test evidence, not a claim that a moderator approved them.
- TC12 now executes two ordered turns: extract/summarise 2025 with Prompt 1; index that extraction as approved TEST knowledge; extract 2026 and generate with Prompt 2. Only 2026 facts and eligible historical IDs are passed to generation. The agent must retrieve the 2025 text through its tool. Each run uses a unique owner and deletes its historical vectors afterward, recording cleanup errors. This tests Python retrieval across separate requests, not Laravel conversation persistence or actual moderator approval.
- The reports concern different villages (2025 Suka Maju at 35%, 2026 Punggul at 50%). A 15-percentage-point difference must not be represented as a confirmed same-location trend.
- TC01–TC06 are included with source-checked expectations; TC02 concerns eco-enzyme preparation, not digital training.
- TC17/18/20 were inaccessible in WhatsApp temporary storage. Copy the original files into `files/` using the filenames in their manifests.
- TC10 uses the supplied JPEG poster, visually checked for activity, date (25 October 2026), time (07.00 WITA), meeting point (kantor desa), and gloves instruction. TC10_PDF preserves the earlier scanned PDF as a separate case with its original checklist. Both require working OCR.
- TC07 source totals were verified: 400 kg and 40 participations, with no unique-person identifiers. TC08 and TC09 expectations match the source text. Evaluate date-sensitive language relative to the run date; a past scheduled date does not prove an event or restoration occurred.
- Source inspection confirms TC11: 20/15 in 2025 and 30/24 in 2026, giving +10 participants (+50%), completion 75% vs 80% (+5 percentage points). TC13 really contains 40 vs 36. TC14 omits date/location. TC15 has 100 rows and 90 distinct registration/participant IDs.
- Check expected facts against originals before grading. Score precision, coverage and supported claims manually using atomic facts; record human ratings separately. These runs are not mocked quality demonstrations.

## Benchmark scores for existing runs

Keep the configured judge running, then use:

```bash
python scripts/score_api_cases.py evaluations/results/20261002-223547-8d8ae03a
```

Use `--case TC04` to test one case. No generation or API resume is performed. Each recorded extraction is judged against normalized source text; draft, analysis and clarification responses are judged against the saved case requirements. Results go into that run's `benchmark/` folder as per-case JSON plus `summary.csv`.

Extraction and response scores are separate. Each rubric requirement receives pass (1), partial (0.5), fail (0), or unverifiable. The score is the equally weighted requirement average multiplied by 100; any unverifiable requirement makes the aggregate unavailable. These are automated rubric-satisfaction scores, not measured factual accuracy or independent human validation. Grouped requirements have equal weight even if their number of subconditions differs. OCR is evaluated only against recorded normalized text; correctness against original image pixels still needs visual review. Technical failures are N/A, not zero quality. Oversized evidence is rejected rather than silently truncated. Historical test approval is simulated; this cannot certify Laravel integration. Review scores and rationales before presentation.
