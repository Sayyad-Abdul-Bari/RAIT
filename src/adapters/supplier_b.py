"""
Supplier B Adapter — CSV batch log (partial metadata).
Has confidence_score + demographic_group but no session_id or metadata dict.
"""
from datetime import datetime
from typing import Dict

import pandas as pd

from src.adapters.base import BaseAdapter
from src.schema.canonical import DataBatch, InteractionRecord, SupplierDataCoverage

SUPPLIER_ID = "supplier_b"
OPTIONAL_FIELDS = [
    "model_name", "token_count", "confidence_score",
    "response_latency_ms", "demographic_group", "session_id", "metadata",
]


class SupplierBAdapter(BaseAdapter):
    """Ingests Supplier B's CSV daily log (partial coverage)."""

    def ingest(self, source: str) -> DataBatch:
        df = pd.read_csv(source)

        records = []
        warnings = []
        field_counts: Dict[str, int] = {k: 0 for k in OPTIONAL_FIELDS}

        for _, row in df.iterrows():
            try:
                record = InteractionRecord(
                    interaction_id=str(row["interaction_id"]),
                    timestamp=datetime.fromisoformat(
                        str(row["timestamp"]).replace("Z", "+00:00")
                    ),
                    user_query=str(row["user_query"]),
                    system_response=str(row["system_response"]),
                    supplier_id=SUPPLIER_ID,
                    model_name=row.get("model_name") if pd.notna(row.get("model_name")) else None,
                    token_count=None,  # not in CSV
                    confidence_score=float(row["confidence_score"]) if pd.notna(row.get("confidence_score")) else None,
                    response_latency_ms=float(row["response_latency_ms"]) if pd.notna(row.get("response_latency_ms")) else None,
                    demographic_group=str(row["demographic_group"]) if pd.notna(row.get("demographic_group")) else None,
                    session_id=None,  # not in CSV
                    metadata=None,    # not in CSV
                )
                for f in OPTIONAL_FIELDS:
                    if getattr(record, f) is not None:
                        field_counts[f] += 1
                records.append(record)
            except Exception as exc:
                warnings.append(f"Skipped row {row.get('interaction_id', '?')}: {exc}")

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
