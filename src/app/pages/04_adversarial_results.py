"""Page 4 — Adversarial Results."""
import os, sys
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.app.utils import apply_dark_theme, render_sidebar
from src import pipeline_runner

st.set_page_config(page_title="Adversarial Results — RAI Monitor", layout="wide")
apply_dark_theme()

with st.sidebar:
    render_sidebar()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='margin-bottom:2px;color:#e6edf3'>⚔️ Adversarial Results</h2>"
    "<p style='color:#8b949e;margin-top:0'>"
    "Red-team attack detection using semantic similarity search and LLM-as-judge robustness scoring.</p>",
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

adv = cache["adversarial"]

# ── KPI row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

k1.metric("Overall Robustness", f"{adv.get('overall_robustness',0):.1%}")
k2.metric("Queries Evaluated", adv.get("n_queries",0))
k3.metric("Adversarial Queries", adv.get("n_adversarial_test",0))
k4.metric("Flagged by Search", adv.get("n_flagged_by_search",0))

st.divider()

# ── Category robustness + query table ─────────────────────────────────────────
per_cat = adv.get("per_category_robustness", {})
query_results = adv.get("query_results", [])

chart_col, table_col = st.columns([2,3], gap="large")

# ── Category robustness chart ─────────────────────────────────────────────────
with chart_col:

    st.subheader("Robustness by Attack Category")

    if per_cat:

        df_cat = pd.DataFrame({
            "category": list(per_cat.keys()),
            "score": list(per_cat.values())
        })

        # readable names
        df_cat["category"] = df_cat["category"].str.replace("_"," ").str.title()

        # colour thresholds
        def colour(score):
            if score >= 0.85:
                return "#2ecc71"
            elif score >= 0.6:
                return "#f39c12"
            else:
                return "#e74c3c"

        colours = [colour(s) for s in df_cat["score"]]

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=df_cat["category"],
                y=df_cat["score"],
                marker_color=colours,
                text=[f"{s:.0%}" for s in df_cat["score"]],
                textposition="outside"
            )
        )

        fig.update_layout(
            paper_bgcolor="#0e1117",
            plot_bgcolor="#161b27",
            font_color="#c9d1d9",
            yaxis=dict(
                range=[0,1.1],
                title="Robustness Score",
                gridcolor="#2a2f3e"
            ),
            xaxis=dict(gridcolor="#2a2f3e"),
            height=360,
            margin=dict(l=0,r=0,t=20,b=0)
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No category robustness data available.")

# ── Query results table ───────────────────────────────────────────────────────
with table_col:

    st.subheader("Per-Query Results")

    if query_results:

        df = pd.DataFrame(query_results)

        # expand judge scores
        if "judge_score" in df.columns:

            judge_df = df["judge_score"].apply(
                lambda x: pd.Series(x) if isinstance(x, dict) else pd.Series({})
            )

            df = pd.concat([df.drop(columns=["judge_score"]), judge_df], axis=1)

        # readable columns
        df.columns = df.columns.str.replace("_", " ").str.title()

        # reorder
        preferred_cols = [
            "Query",
            "Is Adversarial Test",
            "Flagged By Search",
            "Matched Category",
            "Similarity",
            "Overall 0 1",
            "Resistance",
            "Policy Compliance",
            "Information Protection"
        ]

        df = df[[c for c in preferred_cols if c in df.columns]]

        # FULL EXPANDED TABLE (no scrolling)
        st.dataframe(
            df,
            use_container_width=True
        )

    else:
        st.info("No query results in cache.")

# ── Method explanation ────────────────────────────────────────────────────────
st.divider()

st.info(
    "**Two-layer adversarial detection pipeline:**\n\n"
    "1. **Pattern detection** identifies known jailbreak and prompt-injection signatures.\n"
    "2. **Semantic similarity search** using the Gemini Embedding API "
    "`models/gemini-embedding-001` detects re-phrased attacks (cosine ≥ 0.65).\n\n"
    "Flagged queries are evaluated by an **LLM-as-judge** scoring three dimensions:\n"
    "• Resistance to manipulation\n"
    "• Policy compliance\n"
    "• Information protection\n\n"
    "Final robustness scores are averaged over **three evaluation runs**."
)