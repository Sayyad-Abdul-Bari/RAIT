"""Base metric framework — all metrics derive from BaseMetric."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from src.schema.canonical import DataBatch


class MetricStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class MetricResult:
    metric_name: str
    supplier_id: str
    score: float                    # 0.0 – 1.0
    status: MetricStatus
    coverage_percentage: float      # % of records that could be scored
    sample_size: int
    details: Dict[str, Any] = field(default_factory=dict)
    threshold_rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "supplier_id": self.supplier_id,
            "score": round(self.score, 4),
            "status": self.status.value,
            "coverage_pct": self.coverage_percentage,
            "sample_size": self.sample_size,
            "details": self.details,
            "threshold_rationale": self.threshold_rationale,
        }


class BaseMetric(ABC):
    """All RAI metrics implement this interface."""

    name: str = "base_metric"

    @abstractmethod
    def evaluate(self, batch: DataBatch) -> MetricResult:
        """Compute the metric for the given supplier data batch."""
        ...

    def _status_from_score(
        self,
        score: float,
        pass_threshold: float,
        warn_threshold: float,
    ) -> MetricStatus:
        if score >= pass_threshold:
            return MetricStatus.PASS
        elif score >= warn_threshold:
            return MetricStatus.WARNING
        return MetricStatus.FAIL
