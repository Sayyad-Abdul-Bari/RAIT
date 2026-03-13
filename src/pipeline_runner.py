"""
Pipeline Runner — executes the full RAIT analysis once and caches results to disk.

Auto-starts in a background thread when the app launches.
Results are saved to data/results/results_cache.json so all dashboard pages
load instantly without re-calling any LLM API.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from typing import Callable, Optional

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.adapters.factory import AdapterFactory
from src.adversarial.pipeline import AdversarialPipeline
from src.coverage.reporter import CoverageReporter
from src.llm.provider import get_provider_info
from src.metrics.fairness import SentimentConsistencyMetric
from src.metrics.security import PromptInjectionDetectionMetric
from src.metrics.transparency import ConfidenceCalibrationMetric

_CACHE_PATH = os.path.join(_root, "data", "results", "results_cache.json")

_DATA_PATHS = {
    "supplier_a": os.path.join(_root, "data", "supplier_a", "interactions.json"),
    "supplier_b": os.path.join(_root, "data", "supplier_b", "daily_log.csv"),
    "supplier_c": os.path.join(_root, "data", "supplier_c", "sample_interactions.json"),
}

_RED_TEAM_PATH = os.path.join(_root, "data", "red_team", "attack_prompts.json")

_FORMAT_LABELS = {
    "supplier_a": "JSON API",
    "supplier_b": "CSV Batch",
    "supplier_c": "Minimal JSON",
}

# ── Background-thread state (module-level; persists across Streamlit reruns) ──
_STATE: dict = {
    "started": False,   # True once start_if_needed() has fired
    "running": False,   # True while background thread is active
    "done":    False,   # True when run_all() completed successfully
    "error":   None,    # str if an exception was raised
}
_LOCK = threading.Lock()


def _coverage_to_dict(report) -> dict:
    return {
        "supplier_id": report.supplier_id,
        "total_records": report.total_records,
        "field_coverage": report.field_coverage,
        "metric_eligibility": [
            {
                "metric_name": e.metric_name,
                "supplier_id": e.supplier_id,
                "eligible": e.eligible,
                "coverage_pct": e.coverage_pct,
                "missing_fields": e.missing_fields,
                "note": e.note,
            }
            for e in report.metric_eligibility
        ],
        "gaps": report.gaps,
    }


def _run_bg() -> None:
    """Background-thread target — never calls Streamlit functions."""
    with _LOCK:
        _STATE["running"] = True
    try:
        run_all(progress_callback=None)
        with _LOCK:
            _STATE["done"] = True
    except Exception as exc:
        with _LOCK:
            _STATE["error"] = str(exc)
    finally:
        with _LOCK:
            _STATE["running"] = False


def start_if_needed() -> bool:
    """Auto-start analysis in background if not already started and no cache exists.

    Returns True if a new thread was launched, False otherwise.
    Call this once at the top of each page script.
    """
    with _LOCK:
        if _STATE["started"] or cache_exists():
            return False
        _STATE["started"] = True
    threading.Thread(target=_run_bg, daemon=True).start()
    return True


def is_running() -> bool:
    return _STATE["running"]


def is_done() -> bool:
    return _STATE["done"]


def get_error() -> Optional[str]:
    return _STATE.get("error")


def run_all(progress_callback: Optional[Callable[[str], None]] = None) -> dict:
    """Run full analysis pipeline and persist results to cache. Returns the cache dict."""

    def _progress(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    # ── 1. Ingest data ───────────────────────────────────────────────────────
    _progress("Loading supplier data…")
    batches = {}
    for sid, path in _DATA_PATHS.items():
        adapter = AdapterFactory.get(sid)
        batches[sid] = adapter.ingest(path)

    ingestion = {
        sid: {
            "records": len(batch.records),
            "warnings": list(batch.ingestion_warnings),
            "format": _FORMAT_LABELS.get(sid, "Unknown"),
        }
        for sid, batch in batches.items()
    }

    # ── 2. RAI metrics ───────────────────────────────────────────────────────
    _progress("Running RAI metrics (Security · Fairness · Transparency)…")
    metrics = [
        PromptInjectionDetectionMetric(),
        SentimentConsistencyMetric(),
        ConfidenceCalibrationMetric(),
    ]
    metric_results = []
    for batch in batches.values():
        for metric in metrics:
            r = metric.evaluate(batch)
            metric_results.append(r.to_dict())

    # ── 3. Coverage reports ──────────────────────────────────────────────────
    _progress("Computing field coverage reports…")
    reporter = CoverageReporter()
    coverage_reports = reporter.compare_suppliers(list(batches.values()))
    coverage_data = {
        sid: _coverage_to_dict(rpt) for sid, rpt in coverage_reports.items()
    }

    # ── 4. Adversarial pipeline ──────────────────────────────────────────────
    _progress("Building embedding index and running adversarial pipeline…")
    pipeline = AdversarialPipeline(red_team_path=_RED_TEAM_PATH)
    adv_report = pipeline.run(batch=batches["supplier_a"])
    adversarial_data = {
        **adv_report.summary(),
        "query_results": [r.to_dict() for r in adv_report.query_results],
    }

    # ── 5. Persist cache ─────────────────────────────────────────────────────
    cache = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provider": get_provider_info(),
        "ingestion": ingestion,
        "metrics": metric_results,
        "coverage": coverage_data,
        "adversarial": adversarial_data,
    }

    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
    with open(_CACHE_PATH, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2)

    return cache


def load_cache() -> Optional[dict]:
    """Load cached results from disk. Returns None if cache does not exist."""
    if not os.path.exists(_CACHE_PATH):
        return None
    with open(_CACHE_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def cache_exists() -> bool:
    return os.path.exists(_CACHE_PATH)


def cache_path() -> str:
    return _CACHE_PATH
