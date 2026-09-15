# Model Evaluation and Tuning Guide

This guide measures the two ApaKhabar objectives without treating model-reported
`confidence` as real accuracy.

## Success criteria

1. **Data-to-information:** micro-averaged field-level F1 must be at least 0.95.
2. **Information-to-news:** at least 80% of held-out articles must score 80/100 or
   higher and contain no critical unsupported claim.

Keep a test set that is never used for prompt changes, RAG tuning, model selection,
or fine-tuning. A practical split is 70% training, 15% validation, and 15% test.
Include PDF, scanned PDF, DOCX, XLSX, CSV, TXT, both supported languages, and both
clean and noisy documents.

## Step 1: Label extraction examples

Copy `evaluation/data/extraction.example.jsonl`. Each line is one JSON object:

```json
{
  "id": "extract-002",
  "input": "The exact normalized document text, including source markers.",
  "expected_facts": [
    {"field": "type", "value": "Event"},
    {"field": "location", "value": "Kuala Lumpur"},
    {"field": "date", "value": "2026-09-15"}
  ]
}
```

Use the field names you expect the model to place in `fields`. `type` and `label`
are also supported. Free-form title and summary text are excluded from exact-match
F1 because valid paraphrases would otherwise be marked wrong. Do not add a fact unless it is explicitly supported by
the source. Agree on date, currency, name, and location normalization rules before
labelling the full dataset.

## Step 2: Run extraction evaluation

Start Ollama and ensure the configured model is installed, then run:

```bash
source .venv/bin/activate
python scripts/evaluate_model.py extraction \
  --dataset evaluation/data/extraction.example.jsonl \
  --output evaluation/results/extraction.json
```

The aggregate result reports true positives, false positives, false negatives,
precision, recall, F1, and whether the 0.95 target passed. Extra model facts reduce
precision; missed expected facts reduce recall.

## Step 3: Generate and review news

Generate articles from the held-out information records. Two reviewers should score
each article independently from 0 (unacceptable) to 5 (excellent):

| Criterion | Weight |
|---|---:|
| Factual grounding | 40 |
| Fact coverage | 25 |
| Structure | 15 |
| Language and style | 10 |
| Source attribution | 10 |

A critical hallucination is an invented or contradicted fact that could materially
mislead a reader, such as a wrong person, date, location, amount, event, or quote.
Such an article fails even if its weighted score is high.

Copy `evaluation/data/news_ratings.example.jsonl`, add one row per reviewed article,
and run:

```bash
python scripts/evaluate_model.py news \
  --dataset evaluation/data/news_ratings.example.jsonl \
  --output evaluation/results/news.json
```

Resolve large reviewer disagreements and record the final adjudicated rating. In
the thesis, report the dataset size, category and format distribution, model name,
prompt version, F1, news acceptance rate, and critical hallucination rate.

## Step 4: Improve the baseline

Tune one layer at a time and rerun the validation set after every change:

1. Fix parsing and OCR errors first.
2. Improve field definitions, examples, and normalization in the extraction prompt.
3. Keep extraction temperature at zero.
4. Measure RAG retrieval recall before changing the writer.
5. Compare suitable Ollama models using the same validation data.
6. Fine-tune only if repeated errors remain after those steps.

Record each experiment, its changed variable, validation metrics, latency, and
hardware. Select the best configuration once, then run the frozen test set once for
the final reported result.

## Fine-tuning path

Prepare high-quality prompt/completion examples from the training split. Train the
original Hugging Face checkpoint with a LoRA or QLoRA adapter using PEFT and TRL;
do not train on the final test set. Extraction and news writing should use separate
datasets and preferably separate adapters. Evaluate the adapter before exporting a
compatible model for Ollama.

Possible initial LoRA experiment settings are rank 8 or 16, alpha 16 or 32,
dropout 0.05, learning rate 0.0001, and two or three epochs. These are starting
points, not guaranteed optimal values. Stop or reduce training when validation
performance worsens.

Fine-tuning cannot guarantee either target. The target is demonstrated only by the
held-out evaluation results.
