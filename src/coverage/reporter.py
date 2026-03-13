"""
CoverageReporter — field-level coverage analysis across suppliers.
Answers: which metrics can fire, which are blocked by missing data, and why.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from src.schema.canonical import DataBatch, SupplierDataCoverage

OPTIONAL_FIELDS = [
    "model_name",
    "token_count",
    "confidence_score",
    "response_latency_ms",
    "demographic_group",
    "session_id",
    "metadata",
]

# Which optional fields each metric needs
METRIC_FIELD_REQUIREMENTS: Dict[str, List[str]] = {
    "security":      [],                          # works on user_query + system_response only
    "fairness":      ["demographic_group"],
    "transparency":  ["confidence_score"],
}


@dataclass
class MetricEligibility:
    metric_name: str
    supplier_id: str
    eligible: bool
    coverage_pct: float          # 0–100; average of required fields
    missing_fields: List[str] = field(default_factory=list)
    note: str = ""


@dataclass
class SupplierCoverageReport:
    supplier_id: str
    total_records: int
    field_coverage: Dict[str, float]          # field → coverage %
    metric_eligibility: List[MetricEligibility]
    gaps: List[str]                           # human-readable gap descriptions


class CoverageReporter:
    """Compute and compare coverage for one or many suppliers."""

    def report(self, batch: DataBatch) -> SupplierCoverageReport:
        cov: SupplierDataCoverage = batch.coverage
        field_coverage = {
            f: cov.coverage_pct(f) for f in OPTIONAL_FIELDS
        }
        eligibility = []
        gaps = []

        for metric, required in METRIC_FIELD_REQUIREMENTS.items():
            if not required:
                elig = MetricEligibility(
                    metric_name=metric,
                    supplier_id=cov.supplier_id,
                    eligible=True,
                    coverage_pct=100.0,
                    note="No optional fields required.",
                )
            else:
                field_pcts = [field_coverage.get(f, 0.0) for f in required]
                avg_pct = sum(field_pcts) / len(field_pcts)
                missing = [f for f, p in zip(required, field_pcts) if p == 0.0]
                eligible = avg_pct > 0.0
                note = ""
                if missing:
                    note = f"Missing: {', '.join(missing)}. Graceful degradation applied."
                    gaps.append(
                        f"[{cov.supplier_id}] {metric} blocked by missing field(s): "
                        + ", ".join(missing)
                    )
                elig = MetricEligibility(
                    metric_name=metric,
                    supplier_id=cov.supplier_id,
                    eligible=eligible,
                    coverage_pct=round(avg_pct, 1),
                    missing_fields=missing,
                    note=note,
                )
            eligibility.append(elig)

        # Add ingestion warnings as gaps
        for w in batch.ingestion_warnings:
            if w not in gaps:
                gaps.append(w)

        return SupplierCoverageReport(
            supplier_id=cov.supplier_id,
            total_records=cov.total_records,
            field_coverage=field_coverage,
            metric_eligibility=eligibility,
            gaps=gaps,
        )

    def compare_suppliers(
        self, batches: List[DataBatch]
    ) -> Dict[str, SupplierCoverageReport]:
        return {b.supplier_id: self.report(b) for b in batches}
