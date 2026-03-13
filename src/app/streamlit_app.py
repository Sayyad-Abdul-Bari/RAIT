"""
Responsible AI Monitoring Dashboard — Home
Run with: streamlit run src/app/streamlit_app.py
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from src.app.utils import apply_dark_theme, render_sidebar
from src import pipeline_runner

st.set_page_config(
    page_title="Responsible AI Monitoring — UK Government",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_dark_theme()

with st.sidebar:
    render_sidebar()

# ── Page header ──────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='margin-bottom:2px;color:#e6edf3'>Responsible AI Monitoring</h1>"
    "<p style='color:#8b949e;font-size:1rem;margin-top:0'>UK Government · Supplier Evaluation Dashboard</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── Platform overview cards ───────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Suppliers Evaluated", "3", help="Supplier A (JSON), Supplier B (CSV), Supplier C (Minimal JSON)")
c2.metric("RAI Metrics",         "3", help="Security · Fairness · Transparency")
c3.metric("Red-team Prompts",   "10", help="4 attack categories: injection, jailbreak, extraction, policy")
c4.metric("Embedding Model",     "Gemini", help="models/gemini-embedding-001 for semantic attack detection")

st.divider()

# ── Platform description ──────────────────────────────────────────────────────
left, right = st.columns([3, 2], gap="large")

with left:
    st.subheader("About this Platform")
    st.markdown(
        """
        This dashboard evaluates AI chatbot services from three UK government suppliers
        against standardised Responsible AI metrics.

        Each supplier provides interaction logs in different formats and with varying
        levels of metadata. The platform automatically normalises the data and evaluates
        three Responsible AI dimensions:

        • Security  
        • Fairness  
        • Transparency  

        The system handles missing metadata gracefully and distinguishes between
        true model failures and incomplete supplier telemetry.

        > Missing data produces **INSUFFICIENT_DATA**, not FAIL.
        """
    )

with right:
    st.subheader("Pages")
    st.markdown(
        """
        | | Page | Shows |
        |---|---|---|
        | 📦 | **Supplier Overview** | Ingestion status, record counts, field coverage heatmap |
        | 📊 | **Metric Scores** | Security · Fairness · Transparency scores with status |
        | 🗺️ | **Coverage Report** | Metric eligibility matrix — which metrics can fire |
        | ⚔️ | **Adversarial Results** | Red-team detection + LLM-judge robustness scores |
        """
    )

st.divider()

# ── Quick results summary (Pivot Table) ──────────────────────────────────────
import pandas as pd

cache = pipeline_runner.load_cache()

if cache:
    st.divider()
    st.subheader("Latest Analysis Summary")
    st.caption(
        f"Generated: {cache.get('generated_at', '—')}  ·  Provider: {cache['provider']['model']}"
    )

    metrics = cache.get("metrics", [])

    if metrics:

        df = pd.DataFrame(metrics)

        # Pivot by supplier
        pivot = df.pivot_table(
            index="supplier_id",
            columns="metric_name",
            values="score",
            aggfunc="mean"
        )

        pivot = pivot.round(3)

        # Status table for colouring
        status_df = df.pivot_table(
            index="supplier_id",
            columns="metric_name",
            values="status",
            aggfunc="first"
        )

        from src.app.utils import STATUS_COLORS

        def color_cells(val, metric, supplier):
            status = status_df.loc[supplier, metric]
            return f"background-color: {STATUS_COLORS.get(status,'#333')}"

        styled = pivot.style.format("{:.2f}")

        # Apply colours metric-wise
        for metric in pivot.columns:
            styled = styled.apply(
                lambda row: [
                    f"background-color: {STATUS_COLORS.get(status_df.loc[row.name, metric],'#333')}"
                    if col == metric else ""
                    for col in pivot.columns
                ],
                axis=1
            )

        st.dataframe(
            styled,
            use_container_width=True
        )

    adv = cache.get("adversarial", {})
    if adv:
        st.markdown(
            f"**Adversarial robustness:** `{adv.get('overall_robustness', 0):.1%}` — "
            f"{adv.get('n_queries', 0)} queries evaluated, "
            f"{adv.get('n_flagged_by_search', 0)} flagged by semantic search"
        )

elif pipeline_runner.is_running():
    st.divider()
    st.info("⏳ Analysis is running in the background. Summary will appear here when complete.")


