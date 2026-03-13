# Synthetic Data Generation

This document describes how the three supplier data files in `data/` were produced — from
the initial query set through to the formatted, supplier-specific interaction logs consumed
by the RAIT dashboard.

---

## 1. Overview

The synthetic data pipeline lives in a companion repository (`Synthetic-Data-Generator/`).
It simulates how three real UK government AI suppliers might expose interaction data in
different formats. A single set of five UK-government service queries is answered by the
**same underlying LLM** three times, once per supplier, with different model parameters.
The results are then reformatted into three different output schemas.

---

## 2. Input Files

| File | Purpose |
|------|---------|
| `user_query.csv` | Five UK government service queries (query_id, user_query) |
| `configs/supplier_specification.json` | Per-supplier LLM config: model, max_tokens, temperature |

**Example query set** (5 queries):
```
How do I apply for a UK spouse visa?
What are the requirements for British citizenship by naturalisation?
How do I renew my biometric residence permit?
What documents are required for a student visa application?
How can I appeal a visa refusal decision?
```

**Supplier specification** (excerpt):
```json
{
  "supplier_a": { "model_name": "gpt-4.1-nano", "max_tokens": 300, "temperature": 0.7 },
  "supplier_b": { "model_name": "gpt-4.1-nano", "max_tokens": 150, "temperature": 0.5 },
  "supplier_c": { "model_name": "gpt-4.1-nano", "max_tokens": 100, "temperature": 0.9 }
}
```

---

## 3. Response Generation (`response_generator.py`)

For each query × supplier combination, the script:

1. **Calls the LLM API** for each supplier using its configured model and parameters.
2. **Captures wall-clock timestamp** (ISO UTC) immediately before the API call.
3. **Stores full API metadata** per supplier entry:
   - `response` — the generated text
   - `timestamp` — wall-clock ISO UTC string
   - `latency_ms` — end-to-end request latency
   - `response_id` — API-assigned response ID
   - `finish_reason` — `stop` or `length`
   - `usage` — `prompt_tokens`, `completion_tokens`, `total_tokens`
4. **Generates demographic group** once per query using Supplier A's model with a
   zero-temperature classification prompt. This is stored at query level in
   `original_response.json` so all three supplier entries for a query share the same
   demographic label.

**Output**: `data/original_response.json`

```json
{
  "Q-001": {
    "demographic_group": "south_asian",
    "suppliers": {
      "supplier_a": {
        "response": "...",
        "timestamp": "2025-10-01T14:23:11Z",
        "latency_ms": 847,
        "response_id": "resp_abc123",
        "finish_reason": "stop",
        "usage": { "prompt_tokens": 55, "completion_tokens": 214, "total_tokens": 269 }
      },
      "supplier_b": { ... },
      "supplier_c": { ... }
    }
  },
  ...
}
```

---

## 4. Format Conversion (`format_for_rait.py`)

The formatter reads three sources simultaneously:
- `original_response.json` — runtime results (response, timestamp, usage, finish_reason)
- `supplier_specification.json` — static config (temperature, max_tokens)
- `user_query.csv` — the original query text

It produces three output files with different schemas matching each supplier's declared format.

### Supplier A — Full JSON (`interactions.json`)

Represents a supplier with a rich API that exposes all metadata fields.

**Fields produced:**
| Field | Source |
|-------|--------|
| `interaction_id` | Synthesised (`A-{query_id}-001`) |
| `timestamp` | `original_response.json` → wall-clock |
| `user_query` | `user_query.csv` |
| `system_response` | `original_response.json` |
| `model_name` | `supplier_specification.json` |
| `token_count` | `original_response.json` → `usage.total_tokens` |
| `response_latency_ms` | `original_response.json` |
| `confidence_score` | Derived: `finish_reason` + `temperature` |
| `demographic_group` | `original_response.json` (query-level) |
| `response_id` | `original_response.json` |
| `finish_reason` | `original_response.json` |
| `prompt_tokens` | `original_response.json` |
| `completion_tokens` | `original_response.json` |
| `total_tokens` | `original_response.json` |

**Confidence score derivation:**
```
base = 0.85  if finish_reason == "stop"
       0.65  if finish_reason == "length"
       0.70  otherwise
penalty = max(0, temperature - 0.2) × 0.05
confidence = clamp(base - penalty, 0.50, 0.95)
```
This is a lightweight heuristic: `stop` means the model completed its thought (high confidence),
`length` means it was truncated (lower confidence), and higher temperature indicates less
deterministic output.

### Supplier B — CSV (`daily_log.csv`)

Represents a supplier with a simple batch log format that lacks token counts.

**Fields produced:** `interaction_id`, `timestamp`, `user_query`, `system_response`,
`model_name`, `response_latency_ms`, `confidence_score`, `demographic_group`

### Supplier C — Minimal JSON (`sample_interactions.json`)

Represents a supplier that shares only the bare minimum: query and response.

**Fields produced:** `user_query`, `system_response`

No IDs, no timestamps, no metadata. The RAIT platform synthesises `interaction_id` and
`timestamp` on ingestion and flags these as coverage gaps.

---

## 5. Confidence Score Design

The `confidence_score` is the only field that is _derived_ rather than directly extracted.
All other fields come from the API response or the config file verbatim. The derivation
is documented explicitly in `format_for_rait.py` and in the Supplier A output, which
also includes the raw `finish_reason` so evaluators can verify the derivation independently.

---

## 6. From Synthetic Data to Dashboard

```
user_query.csv
supplier_specification.json
        │
        ▼
response_generator.py  ──→  original_response.json
        │
        ▼
format_for_rait.py
        │
  ┌─────┼────────────┐
  ▼     ▼            ▼
data/  data/        data/
supplier_a/  supplier_b/  supplier_c/
        │
        ▼
rait-mle-assessment/
  SupplierA/B/CAdapter → InteractionRecord → DataBatch
        │
  Metric Engine + CoverageReporter + AdversarialPipeline
        │
  pipeline_runner.py → results_cache.json
        │
  Streamlit Dashboard (4 pages, read from cache)
```

---

## 7. Data Volume

Each supplier produces exactly **5 records** (one per user query). This is sufficient
to demonstrate:
- Field coverage differences between suppliers
- Graceful degradation for missing fields
- Semantic search across a small interaction set
- All three metric calculations with meaningful variation

---

## 8. Reproducibility

The response generation uses real LLM API calls, so exact responses will differ between
runs due to model stochasticity. However, the **schema structure**, **field coverage
properties**, and **confidence derivation logic** are deterministic and reproducible.
The formatted output files in `data/` are committed to the repository so the dashboard
can be evaluated without re-running the generation pipeline.
