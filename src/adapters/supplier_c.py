"""
Supplier C Adapter — Minimal JSON sample (50 records, no metadata).
Only user_query and system_response are provided.
Synthetic IDs and timestamps are generated for canonical compatibility.
"""
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict

from src.adapters.base import BaseAdapter
from src.schema.canonical import DataBatch, InteractionRecord, SupplierDataCoverage

SUPPLIER_ID = "supplier_c"
OPTIONAL_FIELDS = [
    "model_name", "token_count", "confidence_score",
    "response_latency_ms", "demographic_group", "session_id", "metadata",
]
_BASE_TIME = datetime(2026, 2, 1, 8, 0, 0, tzinfo=timezone.utc)


class SupplierCAdapter(BaseAdapter):
    """
    Ingests Supplier C's minimal JSON sample.
    Generates synthetic interaction_id and timestamp because the supplier
    does not provide them — documented as a coverage gap.
    """

    def ingest(self, source: str) -> DataBatch:
        with open(source, "r", encoding="utf-8") as f:
            raw = json.load(f)

        records = []
        warnings = ["supplier_c: interaction_id synthesised (not provided by supplier)"]
        warnings.append("supplier_c: timestamp synthesised (not provided by supplier)")
        warnings.append("supplier_c: no metadata fields — confidence, demographic, latency unavailable")

        field_counts: Dict[str, int] = {k: 0 for k in OPTIONAL_FIELDS}

        for idx, item in enumerate(raw):
            try:
                synthetic_id = f"C-{str(uuid.uuid4())[:8].upper()}"
                synthetic_ts = _BASE_TIME + timedelta(minutes=idx * 15)

                # Attempt to detect demographic signals in query text as proxy
                demo_group = _infer_demographic_proxy(item.get("user_query", ""))

                record = InteractionRecord(
                    interaction_id=synthetic_id,
                    timestamp=synthetic_ts,
                    user_query=item["user_query"],
                    system_response=item["system_response"],
                    supplier_id=SUPPLIER_ID,
                    # All optional fields absent for Supplier C
                    model_name=None,
                    token_count=None,
                    confidence_score=None,
                    response_latency_ms=None,
                    demographic_group=demo_group,  # proxy only
                    session_id=None,
                    metadata=None,
                )
                for f_name in OPTIONAL_FIELDS:
                    if getattr(record, f_name) is not None:
                        field_counts[f_name] += 1
                records.append(record)
            except Exception as exc:
                warnings.append(f"Skipped record index {idx}: {exc}")

        if field_counts.get("demographic_group", 0) > 0:
            warnings.append(
                "supplier_c: demographic_group is a TEXT PROXY inferred from query keywords, "
                "not supplier-provided data. Fairness metric coverage marked as partial."
            )

        coverage = SupplierDataCoverage(
            supplier_id=SUPPLIER_ID,
            total_records=len(records),
            field_counts=field_counts,
        )
        return DataBatch(
            supplier_id=SUPPLIER_ID,
            records=records,
            coverage=coverage,
            ingestion_warnings=warnings,
        )


def _infer_demographic_proxy(query: str) -> str | None:
    """
    Very rough proxy: detect demographic signals in query text.
    This is a best-effort heuristic, NOT verified supplier data.
    Returns None if no signal found.
    """
    q = query.lower()
    if any(w in q for w in ["disability", "disabled", "pip", "blue badge", "access to work"]):
        return "proxy_disabled"
    if any(w in q for w in ["single parent", "lone parent", "child benefit", "childcare"]):
        return "proxy_family"
    if any(w in q for w in ["apprentice", "apprenticeship", "university", "student"]):
        return "proxy_young_adult"
    if any(w in q for w in ["pension", "retirement", "care home", "over 65"]):
        return "proxy_older_adult"
    return None
