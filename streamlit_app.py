"""
LLM Evaluation Dashboard
Streamlit app to visualize llama3.2 vs qwen2.5 evaluation results.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LLM Eval Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e1e2e, #2a2a3e);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #3a3a5c;
    }
    [data-testid="stMetricValue"] { font-size: 2rem; }
    .section-header {
        font-size: 1.1rem;
        color: #aaa;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
""", unsafe_allow_html=True)

# ── Color palette ─────────────────────────────────────────────────────────────
MODEL_COLORS = {
    "llama3.2:latest": "#0078D4",
    "qwen2.5:latest":  "#FF8C00",
}

# ── Data loading ──────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"


@st.cache_data
def load_data():
    prompts     = pd.read_csv(DATA_DIR / "prompts.csv")
    runs        = pd.read_csv(DATA_DIR / "runs.csv")
    auto_scores = pd.read_csv(DATA_DIR / "auto_scores.csv")

    # Type fixes
    runs["timestamp"] = pd.to_datetime(runs["timestamp"], errors="coerce")
    runs["latency_s"] = runs["latency_ms"] / 1000

    # Join everything into one flat frame for easy plotting
    df = (
        runs
        .merge(auto_scores, on="run_id", how="left")
        .merge(prompts, on="prompt_id", how="left")
    )
    return prompts, runs, auto_scores, df


prompts, runs, auto_scores, df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🤖 LLM Eval")
    st.caption("llama3.2 vs qwen2.5")
    st.divider()

    selected_models = st.multiselect(
        "Models",
        options=df["model_name"].unique().tolist(),
        default=df["model_name"].unique().tolist(),
    )

    selected_categories = st.multiselect(
        "Categories",
        options=df["category"].unique().tolist(),
        default=df["category"].unique().tolist(),
    )

    selected_difficulties = st.multiselect(
        "Difficulty",
        options=sorted(df["difficulty"].unique().tolist()),
        default=sorted(df["difficulty"].unique().tolist()),
    )

    st.divider()
    st.caption(f"📦 {len(df)} total runs")
    st.caption(f"📝 {len(prompts)} prompts")

# ── Filter ────────────────────────────────────────────────────────────────────
mask = (
    df["model_name"].isin(selected_models) &
    df["category"].isin(selected_categories) &
    df["difficulty"].isin(selected_difficulties)
)
dff = df[mask]

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Overview", "🔍 Deep Dive", "📋 Data Explorer"])


# ═══════════════════════════════════════════════════════
# TAB 1 — EXECUTIVE OVERVIEW
# ═══════════════════════════════════════════════════════
with tab1:
    st.header("Executive Overview")

    # KPI cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Runs", len(dff))
    with col2:
        avg_lat = dff["latency_ms"].mean() / 1000
        st.metric("Avg Latency", f"{avg_lat:.1f}s")
    with col3:
        cite_rate = dff["citations_present"].mean() * 100 if "citations_present" in dff else 0
        st.metric("Citation Rate", f"{cite_rate:.0f}%")
    with col4:
        fmt_rate = dff["format_followed"].mean() * 100 if "format_followed" in dff else 0
        st.metric("Format Compliance", f"{fmt_rate:.0f}%")

    st.divider()

    col_left, col_right = st.columns(2)

    # ── Bar: Avg latency by model ──
    with col_left:
        st.subheader("Average Latency by Model")
        lat_df = (
            dff.groupby("model_name")["latency_s"]
            .mean()
            .reset_index()
            .rename(columns={"latency_s": "Avg Latency (s)"})
        )
        fig = px.bar(
            lat_df,
            x="model_name",
            y="Avg Latency (s)",
            color="model_name",
            color_discrete_map=MODEL_COLORS,
            text_auto=".1f",
            labels={"model_name": "Model"},
        )
        fig.update_layout(showlegend=False, xaxis_title="", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    # ── Grouped bar: Quality metrics by model ──
    with col_right:
        st.subheader("Quality Metrics by Model (%)")
        score_cols = ["citations_present", "format_followed", "mentions_uncertainty"]
        score_labels = {
            "citations_present": "Citations",
            "format_followed": "Format OK",
            "mentions_uncertainty": "Uncertainty",
        }
        score_df = (
            dff.groupby("model_name")[score_cols]
            .mean()
            .mul(100)
            .reset_index()
            .melt(id_vars="model_name", var_name="Metric", value_name="Rate (%)")
        )
        score_df["Metric"] = score_df["Metric"].map(score_labels)
        fig2 = px.bar(
            score_df,
            x="Metric",
            y="Rate (%)",
            color="model_name",
            barmode="group",
            color_discrete_map=MODEL_COLORS,
            text_auto=".0f",
            labels={"model_name": "Model"},
        )
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        fig2.update_traces(textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Bottom of page: slowest prompts table ──
    st.subheader("Slowest Prompts")
    slow_df = (
        dff[["run_id", "model_name", "prompt_text", "latency_ms", "citations_present"]]
        .sort_values("latency_ms", ascending=False)
        .head(5)
        .rename(columns={
            "run_id": "Run",
            "model_name": "Model",
            "prompt_text": "Prompt",
            "latency_ms": "Latency (ms)",
            "citations_present": "Citations",
        })
    )
    slow_df["Prompt"] = slow_df["Prompt"].str[:80] + "…"
    st.dataframe(slow_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════
# TAB 2 — DEEP DIVE
# ═══════════════════════════════════════════════════════
with tab2:
    st.header("Deep Dive Analysis")

    col_a, col_b = st.columns(2)

    # ── Scatter: latency vs output length ──
    with col_a:
        st.subheader("Latency vs Output Length")
        fig3 = px.scatter(
            dff,
            x="latency_ms",
            y="output_len_chars",
            color="model_name",
            color_discrete_map=MODEL_COLORS,
            hover_data=["run_id", "category"],
            labels={
                "latency_ms": "Latency (ms)",
                "output_len_chars": "Output Length (chars)",
                "model_name": "Model",
            },
        )
        fig3.update_traces(marker=dict(size=10, opacity=0.8))
        fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)

    # ── Grouped bar: citations by category ──
    with col_b:
        st.subheader("Citations by Category & Model")
        cat_df = (
            dff.groupby(["category", "model_name"])["citations_present"]
            .sum()
            .reset_index()
            .rename(columns={"citations_present": "Citations"})
        )
        fig4 = px.bar(
            cat_df,
            x="category",
            y="Citations",
            color="model_name",
            barmode="group",
            color_discrete_map=MODEL_COLORS,
            text_auto=True,
            labels={"category": "Category", "model_name": "Model"},
        )
        fig4.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig4, use_container_width=True)

    # ── Citation rate by difficulty ──
    st.subheader("Citation Rate by Prompt Difficulty")
    diff_df = (
        dff.groupby(["difficulty", "model_name"])["citations_present"]
        .mean()
        .mul(100)
        .reset_index()
        .rename(columns={"citations_present": "Citation Rate (%)"})
    )
    fig5 = px.bar(
        diff_df,
        x="difficulty",
        y="Citation Rate (%)",
        color="model_name",
        barmode="group",
        color_discrete_map=MODEL_COLORS,
        text_auto=".0f",
        labels={"difficulty": "Difficulty", "model_name": "Model"},
        category_orders={"difficulty": [1, 2, 3]},
    )
    fig5.update_layout(plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig5, use_container_width=True)


# ═══════════════════════════════════════════════════════
# TAB 3 — DATA EXPLORER
# ═══════════════════════════════════════════════════════
with tab3:
    st.header("Data Explorer")
    st.caption("Use the sidebar filters to narrow results. Click column headers to sort.")

    # Build display frame
    explore_df = dff[[
        "run_id", "model_name", "category", "difficulty",
        "latency_ms", "output_len_chars",
        "citations_present", "format_followed", "mentions_uncertainty",
        "output_text",
    ]].rename(columns={
        "run_id": "Run",
        "model_name": "Model",
        "category": "Category",
        "difficulty": "Difficulty",
        "latency_ms": "Latency (ms)",
        "output_len_chars": "Output Chars",
        "citations_present": "Citations",
        "format_followed": "Format OK",
        "mentions_uncertainty": "Uncertainty",
        "output_text": "Output (truncated)",
    }).copy()

    # Truncate output text for display
    explore_df["Output (truncated)"] = explore_df["Output (truncated)"].str[:200] + "…"

    # Highlight slow rows
    def highlight_latency(val):
        if isinstance(val, (int, float)) and val > 30000:
            return "background-color: #5c2222"
        return ""

    st.dataframe(
        explore_df.style.map(highlight_latency, subset=["Latency (ms)"]),
        use_container_width=True,
        hide_index=True,
        height=500,
    )

    st.caption("🔴 Rows with latency > 30,000 ms are highlighted.")

    # Download button
    csv_bytes = explore_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download filtered data as CSV",
        data=csv_bytes,
        file_name="llm_eval_filtered.csv",
        mime="text/csv",
    )
