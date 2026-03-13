"""
Canonical Schema — the single data contract between suppliers and metrics.

Required fields: every metric needs these.
Optional fields: some metrics need these; absence triggers graceful degradation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, field_serializer


class InteractionRecord(BaseModel):
    """
    Unified representation of one AI interaction.

    Mandatory minimum contract:
        interaction_id, timestamp, user_query, system_response, supplier_id

    Optional fields control which metrics can fire:
        confidence_score  → Transparency / ECE metric
        demographic_group → Fairness / Sentiment consistency metric
        token_count       → general analytics
        response_latency_ms → SLA reporting
    """

    # ── Required ──────────────────────────────────────────────────────────
    interaction_id: str
    timestamp: datetime
    user_query: str
    system_response: str
    supplier_id: str

    # ── Optional ──────────────────────────────────────────────────────────
    model_name: Optional[str] = None
    token_count: Optional[int] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    response_latency_ms: Optional[float] = None
    demographic_group: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("interaction_id")
    @classmethod
    def id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("interaction_id must not be blank")
        return v.strip()

    @field_validator("user_query", "system_response")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("user_query / system_response must not be blank")
        return v.strip()

    @field_serializer("timestamp")
    def _serialize_ts(self, v: datetime) -> str:
        return v.isoformat()


@dataclass
class SupplierDataCoverage:
    """Field-level coverage for a single supplier's batch."""

    supplier_id: str
    total_records: int
    # field → count of non-null values
    field_counts: Dict[str, int] = field(default_factory=dict)

    def coverage_pct(self, field_name: str) -> float:
        if self.total_records == 0:
            return 0.0
        return round(self.field_counts.get(field_name, 0) / self.total_records * 100, 1)

    def to_dict(self) -> Dict[str, Any]:
        optional_fields = [
            "model_name",
            "token_count",
            "confidence_score",
            "response_latency_ms",
            "demographic_group",
            "session_id",
            "metadata",
        ]
        return {
            "supplier_id": self.supplier_id,
            "total_records": self.total_records,
            "coverage": {f: self.coverage_pct(f) for f in optional_fields},
        }


@dataclass
class DataBatch:
    """Container returned by every adapter."""

    supplier_id: str
    records: List[InteractionRecord]
    coverage: SupplierDataCoverage
    ingestion_warnings: List[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.records)
