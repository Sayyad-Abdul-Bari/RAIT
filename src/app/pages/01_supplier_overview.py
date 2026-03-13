"""Page 1 — Supplier Overview."""
import os, sys
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.app.utils import apply_dark_theme, render_sidebar
from src import pipeline_runner

st.set_page_config(page_title="Supplier Overview — RAI Monitor", layout="wide")
apply_dark_theme()

with st.sidebar:
    render_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='margin-bottom:2px;color:#e6edf3'>📦 Supplier Overview</h2>"
    "<p style='color:#8b949e;margin-top:0'>Ingestion status and field coverage across all three suppliers</p>",
    unsafe_allow_html=True,
)
st.divider()

cache = pipeline_runner.load_cache()
if cache is None:
    if pipeline_runner.is_running():
        st.info("⏳ Analysis is running in the background — results will appear here automatically.")
    else:
        st.info("Analysis will start automatically when the app is launched from the Home page.")
    st.stop()

ingestion = cache["ingestion"]
coverage  = cache["coverage"]

# ── Suppliers overview ────────────────────────────────────────────────────────
st.subheader("Supplier Profiles")
sa, sb, sc = st.columns(3, gap="medium")

with sa:
    st.markdown("**Supplier A — JSON API**")
    st.markdown(
        "Full metadata. All fields present. All three RAI metrics fully scoreable. "
        "Provides confidence scores, token counts, latency, and demographic groups."
    )
    st.success("All metrics: PASS eligible")

with sb:
    st.markdown("**Supplier B — CSV Batch Log**")
    st.markdown(
        "Partial metadata. Token counts absent. Security and Fairness metrics fully scoreable. "
        "Transparency metric scoreable via confidence field."
    )
    st.warning("2 of 3 metrics: full coverage")

with sc:
    st.markdown("**Supplier C — Minimal JSON**")
    st.markdown(
        "Query and response only. No metadata whatsoever. IDs and timestamps synthesised "
        "on ingestion. Confidence absent → Transparency = INSUFFICIENT_DATA."
    )
    st.info("Graceful degradation applied")
# ── Supplier summary cards ────────────────────────────────────────────────────
cols = st.columns(3, gap="medium")
labels = {"supplier_a": "Supplier A — JSON API", "supplier_b": "Supplier B — CSV Batch", "supplier_c": "Supplier C — Minimal JSON"}

for col, (sid, info) in zip(cols, ingestion.items()):
    warn_count = len(info["warnings"])
    with col:
        st.markdown(f"**{labels.get(sid, sid)}**")
        m1, m2 = st.columns(2)
        m1.metric("Records",  info["records"])
        m2.metric("Warnings", warn_count)
        st.caption(info["format"])
        if warn_count == 0:
            st.success("Clean ingestion")
        else:
            st.warning(f"{warn_count} warning(s)")

st.divider()

# ── Field coverage heatmap ────────────────────────────────────────────────────
st.subheader("Optional Field Coverage (%)")
st.caption("Shows which metadata fields each supplier provides. Green = present, red = absent.")

OPTIONAL_FIELDS = [
    "model_name", "token_count", "confidence_score",
    "response_latency_ms", "demographic_group", "session_id", "metadata",
]

heat_data = {
    sid: [rpt["field_coverage"].get(f, 0.0) for f in OPTIONAL_FIELDS]
    for sid, rpt in coverage.items()
}

fig = go.Figure(data=go.Heatmap(
    z=list(heat_data.values()),
    x=OPTIONAL_FIELDS,
    y=list(heat_data.keys()),
    colorscale="RdYlGn",
    zmin=0, zmax=100,
    text=[[f"{v:.0f}%" for v in row] for row in heat_data.values()],
    texttemplate="%{text}",
    showscale=True,
))
fig.update_layout(
    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", font_color="#c9d1d9",
    height=260, margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig, width="content")

st.divider()

# ── Ingestion warnings ────────────────────────────────────────────────────────
st.subheader("Ingestion Warnings")
any_warnings = False
for sid, info in ingestion.items():
    if info["warnings"]:
        any_warnings = True
        with st.expander(f"{labels.get(sid, sid)} — {len(info['warnings'])} warning(s)"):
            for w in info["warnings"]:
                st.warning(w)
if not any_warnings:
    st.success("No ingestion warnings across all suppliers.")
