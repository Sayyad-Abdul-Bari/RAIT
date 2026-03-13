"""Page 2 — Metric Scores."""
import os, sys
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.app.utils import STATUS_COLORS, apply_dark_theme, render_sidebar
from src import pipeline_runner

st.set_page_config(page_title="Metric Scores — RAI Monitor", layout="wide")
apply_dark_theme()

with st.sidebar:
    render_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='margin-bottom:2px;color:#e6edf3'>📊 Metric Scores</h2>"
    "<p style='color:#8b949e;margin-top:0'>"
    "Security · Fairness · Transparency evaluated across all suppliers. "
    "Graceful degradation applied where data is insufficient.</p>",
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

results = cache["metrics"]
suppliers    = sorted(set(r["supplier_id"]  for r in results))
metric_names = sorted(set(r["metric_name"] for r in results))

# ── Quick results summary (Pivot Table) ──────────────────────────────────────
if cache:
    st.divider()
    st.subheader("Latest Analysis Summary")

    provider_model = cache.get("provider", {}).get("model", "—")

    st.caption(
        f"Generated: {cache.get('generated_at', '—')}  ·  Provider: {provider_model}"
    )

    metrics = cache.get("metrics", [])

    if metrics:

        df = pd.DataFrame(metrics)

        # Readable supplier names
        supplier_map = {
            "supplier_a": "Supplier A",
            "supplier_b": "Supplier B",
            "supplier_c": "Supplier C"
        }

        df["supplier_id"] = df["supplier_id"].map(lambda x: supplier_map.get(x, x))

        # ── Score Pivot Table ──────────────────────────
        score_pivot = df.pivot_table(
            index="supplier_id",
            columns="metric_name",
            values="score",
            aggfunc="mean"
        ).round(3)

        # ── Status Pivot Table (for coloring) ──────────
        status_pivot = df.pivot_table(
            index="supplier_id",
            columns="metric_name",
            values="status",
            aggfunc="first"
        )

        from src.app.utils import STATUS_COLORS

        # Ensure both pivots align
        status_pivot = status_pivot.reindex_like(score_pivot)

        # ── Cell colouring function ────────────────────
        def color_cell(val, supplier, metric):

            status = status_pivot.loc[supplier, metric]

            colour = STATUS_COLORS.get(status, "#444")

            return f"background-color:{colour}; color:white"

        # Apply styling per cell
        styled = score_pivot.style.format("{:.2f}")

        for metric in score_pivot.columns:
            styled = styled.applymap(
                lambda v, metric=metric: color_cell(
                    v,
                    supplier=score_pivot.index[styled.data.index.get_loc(styled.data.index[styled.data.index.get_loc(v) if False else 0])],
                    metric=metric
                )
            )

        # Simpler reliable method
        styled = score_pivot.style.format("{:.2f}")

        for supplier in score_pivot.index:
            for metric in score_pivot.columns:

                status = status_pivot.loc[supplier, metric]
                colour = STATUS_COLORS.get(status, "#444")

                styled = styled.set_properties(
                    subset=pd.IndexSlice[[supplier], [metric]],
                    **{
                        "background-color": colour,
                        "color": "white"
                    }
                )

        st.dataframe(
            styled,
            use_container_width=True
        )

elif pipeline_runner.is_running():

    st.divider()

    st.info(
        "⏳ Analysis is running in the background. "
        "Summary will appear here when complete."
    )

# ── Score comparison bar chart ─────────────────────────────────────────────────
st.subheader("Score Comparison")

_METRIC_COLOURS = {
    "security_prompt_injection": "#e74c3c",
    "fairness_sentiment_consistency": "#2ecc71",
    "transparency_confidence_calibration    `": "#3498db"
}


fig = go.Figure()
for metric in metric_names:
    scores = [
        next((r["score"] for r in results if r["supplier_id"] == sid and r["metric_name"] == metric), 0.0)
        for sid in suppliers
    ]
    fig.add_trace(go.Bar(
        name=metric,
        x=suppliers,
        y=scores,
        marker_color=_METRIC_COLOURS.get(metric, "#aaa"),
    ))

fig.update_layout(
    barmode="group",
    paper_bgcolor="#0e1117", plot_bgcolor="#161b27", font_color="#c9d1d9",
    yaxis=dict(range=[0, 1.05], title="Score (0–1)", gridcolor="#2a2f3e"),
    xaxis=dict(gridcolor="#2a2f3e"),
    legend_title="Metric",
    height=380,
    margin=dict(l=0, r=0, t=20, b=0),
)
st.plotly_chart(fig, width="content")

st.divider()

# ── Detailed expanders ────────────────────────────────────────────────────────
st.subheader("Detailed Results")
for r in results:
    colour = STATUS_COLORS.get(r["status"], "#ccc")
    with st.expander(f"{r['supplier_id']}  ·  {r['metric_name']}  ·  {r['status']}"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Score",    f"{r['score']:.4f}")
        c2.metric("Coverage", f"{r['coverage_pct']:.1f}%")
        c3.metric("Records",  r["sample_size"])
        st.markdown(
            f"<span style='background:{colour}22;color:{colour};"
            f"padding:3px 10px;border-radius:4px;font-weight:600'>"
            f"{r['status']}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(f"**Threshold rationale:** {r['threshold_rationale']}")
        if r.get("details"):
            st.json(r["details"])
