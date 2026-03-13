"""Tests for CoverageReporter."""
import os
from src.adapters.factory import AdapterFactory
from src.coverage.reporter import CoverageReporter

DATA_ROOT = os.path.join(os.path.dirname(__file__), "..", "data")


def _batch(supplier, fname):
    adapter = AdapterFactory.get(supplier)
    return adapter.ingest(os.path.join(DATA_ROOT, supplier, fname))


def test_supplier_a_all_metrics_eligible():
    reporter = CoverageReporter()
    batch = _batch("supplier_a", "interactions.json")
    report = reporter.report(batch)
    for elig in report.metric_eligibility:
        assert elig.eligible, f"Expected {elig.metric_name} eligible for supplier_a"


def test_supplier_c_transparency_not_eligible():
    reporter = CoverageReporter()
    batch = _batch("supplier_c", "sample_interactions.json")
    report = reporter.report(batch)
    transp = next(e for e in report.metric_eligibility if e.metric_name == "transparency")
    assert not transp.eligible


def test_supplier_c_security_always_eligible():
    reporter = CoverageReporter()
    batch = _batch("supplier_c", "sample_interactions.json")
    report = reporter.report(batch)
    sec = next(e for e in report.metric_eligibility if e.metric_name == "security")
    assert sec.eligible


def test_compare_suppliers_returns_all():
    reporter = CoverageReporter()
    batches = [
        _batch("supplier_a", "interactions.json"),
        _batch("supplier_b", "daily_log.csv"),
        _batch("supplier_c", "sample_interactions.json"),
    ]
    reports = reporter.compare_suppliers(batches)
    assert set(reports.keys()) == {"supplier_a", "supplier_b", "supplier_c"}


def test_field_coverage_values_in_range():
    reporter = CoverageReporter()
    batch = _batch("supplier_a", "interactions.json")
    report = reporter.report(batch)
    for f, pct in report.field_coverage.items():
        assert 0.0 <= pct <= 100.0, f"Coverage for {f} out of range: {pct}"
