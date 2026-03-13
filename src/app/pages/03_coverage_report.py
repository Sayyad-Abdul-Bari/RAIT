"""Page 3 — Coverage Report."""
import os, sys
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.app.utils import apply_dark_theme, render_sidebar
from src import pipeline_runner

st.set_page_config(page_title="Coverage Report — RAI Monitor", layout="wide")
apply_dark_theme()

with st.sidebar:
    render_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='margin-bottom:2px;color:#e6edf3'>🗺️ Coverage Report</h2>"
    "<p style='color:#8b949e;margin-top:0'>"
    "Which metrics can fire for each supplier, and which are blocked by missing data.</p>",
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

coverage = cache["coverage"]

# ── Metric eligibility matrix ─────────────────────────────────────────────────
st.subheader("Metric Eligibility Matrix")
st.caption("✅ = supplier provides required fields · ❌ = required field(s) absent → graceful degradation")

matrix_rows = []
for sid, rpt in coverage.items():
    row = {"Supplier": sid, "Records": rpt["total_records"]}
    for elig in rpt["metric_eligibility"]:
        icon = "✅" if elig["eligible"] else "❌"
        row[elig["metric_name"]] = f"{icon} {elig['coverage_pct']:.0f}%"
    matrix_rows.append(row)

st.dataframe(pd.DataFrame(matrix_rows), width="content", hide_index=True)

st.divider()

# ── Field coverage chart ──────────────────────────────────────────────────────
left, right = st.columns([3, 2], gap="large")

with left:
    st.subheader("Field Coverage by Supplier (%)")
    first_rpt = next(iter(coverage.values()))
    fields = list(first_rpt["field_coverage"].keys())

    _SUPPLIER_COLOURS = {
        "supplier_a": "#3498db",
        "supplier_b": "#2ecc71",
        "supplier_c": "#e67e22",
    }

    fig = go.Figure()
    for sid, rpt in coverage.items():
        fig.add_trace(go.Bar(
            name=sid,
            x=fields,
            y=[rpt["field_coverage"].get(f, 0.0) for f in fields],
            marker_color=_SUPPLIER_COLOURS.get(sid, "#aaa"),
        ))
    fig.update_layout(
        barmode="group",
        paper_bgcolor="#0e1117", plot_bgcolor="#161b27", font_color="#c9d1d9",
        yaxis=dict(range=[0, 110], title="Coverage %", gridcolor="#2a2f3e"),
        xaxis=dict(gridcolor="#2a2f3e", tickangle=-25),
        height=360,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(bgcolor="#0e1117"),
    )
    st.plotly_chart(fig, width="content")

with right:
    st.subheader("Data Gaps")
    st.caption("Gaps and ingestion warnings per supplier.")
    for sid, rpt in coverage.items():
        gaps = rpt.get("gaps", [])
        with st.expander(f"{sid} — {len(gaps)} gap(s)", expanded=False):
            if not gaps:
                st.success("No gaps detected.")
            else:
                for gap in gaps:
                    if "missing" in gap.lower() or "blocked" in gap.lower():
                        st.error(gap)
                    elif "proxy" in gap.lower() or "synthesised" in gap.lower():
                        st.warning(gap)
                    else:
                        st.info(gap)

# ── Design note ───────────────────────────────────────────────────────────────
st.divider()
st.info(
    "**Graceful degradation:** Supplier C provides only `user_query` and `system_response`. "
    "IDs and timestamps are synthesised on ingestion (flagged as gaps). "
    "`confidence_score` absent → Transparency = **INSUFFICIENT_DATA**, not FAIL. "
    "`demographic_group` absent → proxy inferred from query keywords. "
    "Data absence ≠ AI failure — the platform distinguishes these two failure modes explicitly."
)
