"""Shared utilities for Streamlit pages."""
from __future__ import annotations

import os
import sys
import time

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.adapters.factory import AdapterFactory
from src.schema.canonical import DataBatch

DATA_PATHS = {
    "supplier_a": os.path.join(_project_root, "data", "supplier_a", "interactions.json"),
    "supplier_b": os.path.join(_project_root, "data", "supplier_b", "daily_log.csv"),
    "supplier_c": os.path.join(_project_root, "data", "supplier_c", "sample_interactions.json"),
}

RED_TEAM_PATH = os.path.join(_project_root, "data", "red_team", "attack_prompts.json")


def load_all_batches() -> dict[str, DataBatch]:
    batches = {}
    for sid, path in DATA_PATHS.items():
        adapter = AdapterFactory.get(sid)
        batches[sid] = adapter.ingest(path)
    return batches


STATUS_COLORS = {
    "PASS":             "#2ecc71",
    "WARNING":          "#f39c12",
    "FAIL":             "#e74c3c",
    "INSUFFICIENT_DATA":"#95a5a6",
}

# ── Dark theme (always applied) ───────────────────────────────────────────────

_DARK_CSS = """
<style>
.stApp, [data-testid="stAppViewContainer"] {
    background-color: #0e1117 !important;
}
section[data-testid="stSidebar"] {
    background-color: #161b27 !important;
    border-right: 1px solid #2a2f3e !important;
}
section[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
[data-testid="stMain"] .stMarkdown p,
[data-testid="stMain"] .stMarkdown li,
[data-testid="stMain"] .stMarkdown h1,
[data-testid="stMain"] .stMarkdown h2,
[data-testid="stMain"] .stMarkdown h3,
[data-testid="stMain"] .stMarkdown h4 { color: #e0e0e0 !important; }
h1, h2, h3, h4, h5, h6 { color: #e6edf3 !important; }
[data-testid="stMetricValue"] { color: #ffffff !important; }
[data-testid="stMetricLabel"] { color: #8b949e !important; }
[data-testid="stCaption"]     { color: #8b949e !important; }
p, label { color: #c9d1d9 !important; }
[data-testid="stDataFrame"] { background: #161b27 !important; }
</style>
"""


def apply_dark_theme() -> None:
    """Inject dark-mode CSS. Call once per page after set_page_config."""
    import streamlit as st
    st.markdown(_DARK_CSS, unsafe_allow_html=True)


# ── Unified sidebar ───────────────────────────────────────────────────────────

def render_sidebar() -> None:
    """Complete sidebar renderer — brand header, status, navigation.

    Call this inside `with st.sidebar:` at the top of every page.
    It handles auto-start, polling, and toast notification internally.
    """
    import streamlit as st
    from src import pipeline_runner
    from src.llm.provider import get_provider_info

    # ── Brand header (always at top) ─────────────────────────────────────────
    st.markdown(
        "<div style='padding:10px 0 4px 0'>"
        "<div style='font-size:1.15rem;font-weight:700;color:#e6edf3;letter-spacing:.02em'>"
        "🛡️ Responsible AI Monitoring</div>"
        "<div style='font-size:0.78rem;color:#8b949e;margin-top:2px'>"
        "UK Government · RAI Tracker</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Analysis status ───────────────────────────────────────────────────────
    pipeline_runner.start_if_needed()

    if pipeline_runner.is_running():
        st.warning("⏳ Analysing data in background…")
        time.sleep(2)
        st.rerun()
    elif pipeline_runner.get_error():
        st.error(f"Analysis error: {pipeline_runner.get_error()}")
    else:
        if pipeline_runner.cache_exists():
            cache = pipeline_runner.load_cache()
            ts = (cache or {}).get("generated_at", "—")
            st.markdown(
                f"<div style='font-size:0.75rem;color:#8b949e;padding:2px 0'>"
                f"Last run: {ts}</div>",
                unsafe_allow_html=True,
            )
        provider = get_provider_info()
        st.markdown(
            f"<div style='font-size:0.75rem;color:#8b949e;padding:2px 0 6px 0'>"
            f"Provider: {provider['model']}</div>",
            unsafe_allow_html=True,
        )

    # Toast once on completion
    if pipeline_runner.is_done() and not st.session_state.get("_analysis_toast_shown"):
        st.session_state["_analysis_toast_shown"] = True
        st.toast("✅ Analysis complete — results are ready!", icon="✅")

    st.divider()

    # ── Navigation ────────────────────────────────────────────────────────────
    st.page_link("streamlit_app.py",                  label="🏠 Home")
    st.page_link("pages/01_supplier_overview.py",     label="📦 Supplier Overview")
    st.page_link("pages/02_metric_scores.py",         label="📊 Metric Scores")
    st.page_link("pages/03_coverage_report.py",       label="🗺️ Coverage Report")
    st.page_link("pages/04_adversarial_results.py",   label="⚔️ Adversarial Results")

    st.divider()
    st.markdown(
        "<div style='font-size:0.72rem;color:#484f58;text-align:center;padding:4px 0'>"
        "© 2026 RAI Tracker Limited</div>",
        unsafe_allow_html=True,
    )
