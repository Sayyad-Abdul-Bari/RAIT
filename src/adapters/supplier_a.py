"""
Supplier A Adapter — JSON API (full metadata).
All optional fields present: confidence_score, demographic_group, latency, etc.
"""
import json
from datetime import datetime
from typing import Dict

from src.adapters.base import BaseAdapter
from src.schema.canonical import DataBatch, InteractionRecord, SupplierDataCoverage

SUPPLIER_ID = "supplier_a"
OPTIONAL_FIELDS = [
    "model_name", "token_count", "confidence_score",
    "response_latency_ms", "demographic_group", "session_id", "metadata",
]


class SupplierAAdapter(BaseAdapter):
    """Ingests Supplier A's JSON API dump (full coverage)."""

    def ingest(self, source: str) -> DataBatch:
        with open(source, "r", encoding="utf-8") as f:
            raw = json.load(f)

        records = []
        warnings = []
        field_counts: Dict[str, int] = {k: 0 for k in OPTIONAL_FIELDS}

        for item in raw:
            try:
                record = InteractionRecord(
                    interaction_id=item["interaction_id"],
                    timestamp=datetime.fromisoformat(
                        item["timestamp"].replace("Z", "+00:00")
                    ),
                    user_query=item["user_query"],
                    system_response=item["system_response"],
                    supplier_id=SUPPLIER_ID,
                    model_name=item.get("model_name"),
                    token_count=item.get("token_count"),
                    confidence_score=item.get("confidence_score"),
                    response_latency_ms=item.get("response_latency_ms"),
                    demographic_group=item.get("demographic_group"),
                    session_id=item.get("session_id"),
                    metadata=item.get("metadata"),
                )
                for f in OPTIONAL_FIELDS:
                    if getattr(record, f) is not None:
                        field_counts[f] += 1
                records.append(record)
            except Exception as exc:
                warnings.append(f"Skipped record {item.get('interaction_id', '?')}: {exc}")

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
