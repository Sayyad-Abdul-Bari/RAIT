"""Tests for supplier adapters."""
import os
import pytest
from src.adapters.factory import AdapterFactory
from src.schema.canonical import DataBatch

DATA_ROOT = os.path.join(os.path.dirname(__file__), "..", "data")


def _path(supplier, fname):
    return os.path.join(DATA_ROOT, supplier, fname)


def test_supplier_a_loads():
    adapter = AdapterFactory.get("supplier_a")
    batch = adapter.ingest(_path("supplier_a", "interactions.json"))
    assert isinstance(batch, DataBatch)
    assert len(batch.records) == 5
    assert batch.supplier_id == "supplier_a"


def test_supplier_a_full_coverage():
    adapter = AdapterFactory.get("supplier_a")
    batch = adapter.ingest(_path("supplier_a", "interactions.json"))
    cov = batch.coverage
    assert cov.coverage_pct("confidence_score") == 100.0
    assert cov.coverage_pct("demographic_group") == 100.0


def test_supplier_b_loads():
    adapter = AdapterFactory.get("supplier_b")
    batch = adapter.ingest(_path("supplier_b", "daily_log.csv"))
    assert isinstance(batch, DataBatch)
    assert len(batch.records) == 5
    assert batch.supplier_id == "supplier_b"


def test_supplier_b_no_token_count():
    adapter = AdapterFactory.get("supplier_b")
    batch = adapter.ingest(_path("supplier_b", "daily_log.csv"))
    assert batch.coverage.coverage_pct("token_count") == 0.0


def test_supplier_c_loads():
    adapter = AdapterFactory.get("supplier_c")
    batch = adapter.ingest(_path("supplier_c", "sample_interactions.json"))
    assert isinstance(batch, DataBatch)
    assert len(batch.records) == 5
    assert batch.supplier_id == "supplier_c"


def test_supplier_c_synthesised_ids():
    adapter = AdapterFactory.get("supplier_c")
    batch = adapter.ingest(_path("supplier_c", "sample_interactions.json"))
    ids = [r.interaction_id for r in batch.records]
    assert all(iid.startswith("C-") for iid in ids)


def test_supplier_c_no_confidence():
    adapter = AdapterFactory.get("supplier_c")
    batch = adapter.ingest(_path("supplier_c", "sample_interactions.json"))
    assert batch.coverage.coverage_pct("confidence_score") == 0.0


def test_factory_unknown_raises():
    with pytest.raises(KeyError):
        AdapterFactory.get("supplier_unknown")


def test_factory_register_and_get():
    from src.adapters.supplier_a import SupplierAAdapter
    AdapterFactory.register("supplier_test", SupplierAAdapter)
    adapter = AdapterFactory.get("supplier_test")
    assert isinstance(adapter, SupplierAAdapter)
