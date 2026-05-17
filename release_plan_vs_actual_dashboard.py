"""Release Plan vs Actual Dashboard

A single-file Streamlit app for visualizing:
- Planned vs actual release progression by week
- Cumulative cell adoption by version and stagger
- Plan adherence over time
- Weekly heatmaps and drilldowns

Data inputs expected:
1) Actuals query output with columns like:
   current_version, week_start, pct_of_SB0, pct_of_SB1, pct_of_R0, pct_of_R1, pct_of_R2a, pct_of_R2b

2) Plan data in a wide table like:
   row label in first column (Moratorium, Code Freeze, Leftshift, CD Testing, SB0, SB1/SB2.w1, ...)
   dates across columns
   cells containing version values or blanks

This script includes a parser for the plan table format pasted into chat.

Run:
    streamlit run release_plan_vs_actual_dashboard.py
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# -----------------------------
# App config
# -----------------------------

st.set_page_config(
    page_title="Release Plan vs Actual Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

STAGES = ["SB0", "SB1", "R0", "R1", "R2a", "R2b"]
STAGE_ALIASES = {
    "SB1/SB2.w1": "SB1",
    "SB1/SB2.w2": "SB1",
    "R*.w1": "R1",
    'R*.w2, GIA2H': "R2a",
    "R*.w2": "R2a",
}

DEFAULT_STAGE_ORDER = ["Moratorium", "Code Freeze", "Leftshift", "CD Testing", *STAGES]


# -----------------------------
# Helpers
# -----------------------------

def normalize_version(val: object) -> str:
    """Convert values like 262.11 or 26211 into a canonical string."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    s = str(val).strip()
    if not s:
        return ""
    # Keep as-is if already looks like x.y
    if re.fullmatch(r"\d+\.\d+", s):
        return s
    # Convert integer-like versions 26211 -> 262.11
    if re.fullmatch(r"\d+", s):
        if len(s) > 3:
            return f"{int(s[:-2])}.{int(s[-2:])}"
        return s
    return s


def parse_date_col(col: object) -> Optional[pd.Timestamp]:
    s = str(col).strip()
    if not s:
        return None
    for fmt in (None, "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            dt = pd.to_datetime(s, format=fmt) if fmt else pd.to_datetime(s)
            return pd.Timestamp(dt).normalize()
        except Exception:
            continue
    return None


def week_start(ts: pd.Timestamp) -> pd.Timestamp:
    return (pd.Timestamp(ts).normalize() - pd.Timedelta(days=pd.Timestamp(ts).weekday())).normalize()


@dataclass
class PlanParseResult:
    raw: pd.DataFrame
    long: pd.DataFrame
    versions_by_stage: pd.DataFrame


@st.cache_data(show_spinner=False)
def parse_plan_text(plan_text: str) -> PlanParseResult:
    """Parse the pasted plan block into a long dataframe.

    Expected format is CSV-like text where:
    - first column is stage name
    - remaining columns are dates
    - cell values contain versions or blanks
    """
    lines = [ln.strip() for ln in plan_text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        raise ValueError("Plan text is too short.")

    # Use csv reader-like parsing with pandas from a string buffer.
    # We preserve quoted commas in stage names.
    df = pd.read_csv(io.StringIO(plan_text), header=None)
    header = df.iloc[0].tolist()

    # Locate first date-like column in header row.
    date_cols: List[Tuple[int, pd.Timestamp]] = []
    for i, col in enumerate(header[1:], start=1):
        dt = parse_date_col(col)
        if dt is not None:
            date_cols.append((i, dt))
    if not date_cols:
        raise ValueError("Could not find date columns in the plan data.")

    rows = []
    for _, row in df.iloc[1:].iterrows():
        stage = str(row.iloc[0]).strip()
        if not stage or stage == "nan":
            continue
        for col_idx, dt in date_cols:
            val = row.iloc[col_idx] if col_idx < len(row) else ""
            version = normalize_version(val)
            if version:
                rows.append(
                    {
                        "stage": stage,
                        "week_start": week_start(dt),
                        "planned_version": version,
                    }
                )

    long_df = pd.DataFrame(rows)
    if long_df.empty:
        raise ValueError("No planned versions could be parsed from the plan data.")

    # Normalize stage names and aliases.
    long_df["stage"] = long_df["stage"].replace(STAGE_ALIASES)
    long_df.loc[~long_df["stage"].isin(DEFAULT_STAGE_ORDER), "stage"] = long_df.loc[
        ~long_df["stage"].isin(DEFAULT_STAGE_ORDER), "stage"
    ]

    versions_by_stage = (
        long_df.groupby(["stage", "planned_version"], as_index=False)
        .agg(first_week_start=("week_start", "min"), last_week_start=("week_start", "max"))
        .sort_values(["stage", "first_week_start", "planned_version"])
    )
    raw = df
    return PlanParseResult(raw=raw, long=long_df, versions_by_stage=versions_by_stage)


@st.cache_data(show_spinner=False)
def load_actuals_csv(uploaded_file) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file)
    required = {"current_version", "week_start"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Actuals file missing required columns: {sorted(missing)}")

    df = df.copy()
    df["current_version"] = df["current_version"].astype(str).map(normalize_version)
    df["week_start"] = pd.to_datetime(df["week_start"]).dt.normalize()
    pct_cols = [c for c in df.columns if c.startswith("pct_of_")]
    for c in pct_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    return df


@st.cache_data(show_spinner=False)
def build_stage_actual_summary(actuals: pd.DataFrame) -> pd.DataFrame:
    pct_cols = [c for c in actuals.columns if c.startswith("pct_of_")]
    if not pct_cols:
        raise ValueError("Actuals file does not contain pct_of_* columns.")

    agg = (
        actuals.groupby("week_start", as_index=False)[pct_cols]
        .mean(numeric_only=True)
        .sort_values("week_start")
    )
    return agg


@st.cache_data(show_spinner=False)
def build_plan_adherence(plan_long: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Compare actual cumulative stage % against plan progression.

    Since the plan table contains version placements by stage/week, we convert it into
    a weekly plan cumulative curve by stage:
      - planned cumulative pct in a stage = unique planned versions seen by that week / total versions for that stage

    This is a practical interpretation for plan vs actual.
    """
    # Planned totals by stage.
    stage_totals = (
        plan_long.groupby("stage", as_index=False)
        .agg(total_planned_versions=("planned_version", "nunique"))
    )
    stage_totals = stage_totals[stage_totals["stage"].isin(STAGES)]

    # Build weekly cumulative planned counts.
    plan_rows = []
    for stage in STAGES:
        sub = plan_long[plan_long["stage"] == stage].copy()
        if sub.empty:
            continue
        total = sub["planned_version"].nunique()
        for wk in sorted(sub["week_start"].unique()):
            seen = sub[sub["week_start"] <= wk]["planned_version"].nunique()
            plan_rows.append(
                {
                    "week_start": wk,
                    "stage": stage,
                    "planned_pct": 100.0 * seen / total if total else 0.0,
                    "planned_count": seen,
                    "planned_total": total,
                }
            )
    plan_curve = pd.DataFrame(plan_rows)

    # Actuals assumed already represent cumulative % by stage.
    actual_long = actuals.melt(
        id_vars=["current_version", "week_start"],
        value_vars=[c for c in actuals.columns if c.startswith("pct_of_")],
        var_name="stage_col",
        value_name="actual_pct",
    )
    actual_long["stage"] = actual_long["stage_col"].str.replace("pct_of_", "", regex=False)
    actual_long["stage"] = actual_long["stage"].replace({"SB0": "SB0", "SB1": "SB1", "R0": "R0", "R1": "R1", "R2a": "R2a", "R2b": "R2b"})

    # Align a version's stage curve with the plan curve by current_version.
    # In practice, this is most useful as a single dashboard summary, not a strict row-by-row diff.
    actual_summary = (
        actual_long.groupby(["week_start", "stage"], as_index=False)
        .agg(actual_pct=("actual_pct", "mean"))
        .sort_values(["week_start", "stage"])
    )

    merged = plan_curve.merge(actual_summary, on=["week_start", "stage"], how="outer")
    merged = merged.sort_values(["stage", "week_start"]).reset_index(drop=True)
    return merged


@st.cache_data(show_spinner=False)
def latest_week_snapshot(actuals: pd.DataFrame) -> pd.DataFrame:
    if actuals.empty:
        return actuals
    latest_week = actuals["week_start"].max()
    return actuals[actuals["week_start"] == latest_week].copy()


# -----------------------------
# Sidebar
# -----------------------------

st.sidebar.title("Release dashboard")

actuals_file = st.sidebar.file_uploader(
    "Upload actuals CSV",
    type=["csv"],
    help="CSV with columns like current_version, week_start, pct_of_SB0, pct_of_SB1, pct_of_R0, pct_of_R1, pct_of_R2a, pct_of_R2b",
)

plan_text_input = st.sidebar.text_area(
    "Paste plan data",
    height=320,
    help="Paste the plan table text in CSV-like form, including the header row of dates.",
)

show_only_latest = st.sidebar.checkbox("Show only latest week", value=False)
show_heatmap = st.sidebar.checkbox("Show stage heatmap", value=True)

# -----------------------------
# Load data
# -----------------------------

if not actuals_file:
    st.title("Release Plan vs Actual Dashboard")
    st.info("Upload the actuals CSV and paste the plan table to generate the dashboard.")
    st.stop()

try:
    actuals = load_actuals_csv(actuals_file)
except Exception as e:
    st.error(f"Could not read actuals CSV: {e}")
    st.stop()

try:
    if plan_text_input.strip():
        plan = parse_plan_text(plan_text_input)
    else:
        plan = None
except Exception as e:
    st.error(f"Could not parse plan data: {e}")
    st.stop()

# -----------------------------
# Derived datasets
# -----------------------------

actuals_view = latest_week_snapshot(actuals) if show_only_latest else actuals.copy()
actuals_view = actuals_view.sort_values(["current_version", "week_start"])

pct_cols = [c for c in actuals.columns if c.startswith("pct_of_")]

plan_curve = None
if plan is not None:
    plan_curve = build_plan_adherence(plan.long, actuals)

# -----------------------------
# Header KPIs
# -----------------------------

st.title("Release Plan vs Actual Dashboard")
st.caption("Plan data is parsed from your pasted table; actuals come from your weekly cumulative query output.")

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("Versions", f"{actuals['current_version'].nunique():,}")
with c2:
    st.metric("Weeks", f"{actuals['week_start'].nunique():,}")
with c3:
    st.metric("Latest week", actuals['week_start'].max().date().isoformat())
with c4:
    st.metric("Rows", f"{len(actuals_view):,}")
with c5:
    if plan is not None:
        st.metric("Planned rows", f"{len(plan.long):,}")
    else:
        st.metric("Planned rows", "0")

st.divider()

# -----------------------------
# Main charts
# -----------------------------

left, right = st.columns([2.2, 1])

with left:
    st.subheader("1. Release journey over time")
    if actuals_view.empty:
        st.warning("No actuals available for the selected view.")
    else:
        # A release-level timeline / heatmap-like chart.
        heatmap_df = actuals_view.melt(
            id_vars=["current_version", "week_start"],
            value_vars=pct_cols,
            var_name="stage_col",
            value_name="pct",
        )
        heatmap_df["stage"] = heatmap_df["stage_col"].str.replace("pct_of_", "", regex=False)
        heatmap_df["stage"] = heatmap_df["stage"].replace({"SB0": "SB0", "SB1": "SB1", "R0": "R0", "R1": "R1", "R2a": "R2a", "R2b": "R2b"})
        heatmap_df = heatmap_df.sort_values(["current_version", "week_start", "stage"])

        # One chart per selected version, with slider.
        versions = actuals_view["current_version"].dropna().unique().tolist()
        selected_version = st.selectbox("Release / version", versions, index=0)
        release_df = heatmap_df[heatmap_df["current_version"] == selected_version].copy()

        if release_df.empty:
            st.info("No rows for this version.")
        else:
            pivot = release_df.pivot_table(index="stage", columns="week_start", values="pct", aggfunc="mean")
            pivot = pivot.reindex(STAGES)
            fig = px.imshow(
                pivot,
                aspect="auto",
                color_continuous_scale="Blues",
                labels=dict(x="Week", y="Stage", color="Pct"),
                title=f"Cumulative actual progress for version {selected_version}",
            )
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

    if show_heatmap and plan_curve is not None:
        st.subheader("2. Plan vs actual adherence")
        # Stage-level curves.
        plan_plot = plan_curve.copy()
        plan_plot["week_start"] = pd.to_datetime(plan_plot["week_start"])
        plan_plot = plan_plot.sort_values(["stage", "week_start"])

        # Build long form for plotting.
        long_plot = plan_plot.melt(
            id_vars=["week_start", "stage"],
            value_vars=["planned_pct", "actual_pct"],
            var_name="series",
            value_name="pct",
        )
        long_plot["series"] = long_plot["series"].map({"planned_pct": "Planned", "actual_pct": "Actual"})
        long_plot = long_plot.dropna(subset=["pct"])

        fig = px.line(
            long_plot,
            x="week_start",
            y="pct",
            color="series",
            facet_row="stage",
            facet_row_spacing=0.03,
            markers=True,
            title="Stage plan vs actual (cumulative %)",
        )
        fig.update_yaxes(matches=None)
        fig.update_layout(height=900, legend_title_text="", margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("At a glance")

    if plan_curve is not None:
        # Compute simple adherence metric.
        combined = plan_curve.dropna(subset=["planned_pct", "actual_pct"]).copy()
        if not combined.empty:
            diff = (combined["actual_pct"] - combined["planned_pct"]).abs().mean()
            st.metric("Avg abs plan gap", f"{diff:.1f} pts")
        else:
            st.metric("Avg abs plan gap", "n/a")

        latest = plan_curve.sort_values("week_start").groupby("stage", as_index=False).tail(1)
        latest = latest[["stage", "planned_pct", "actual_pct"]].copy()
        latest["gap"] = latest["actual_pct"].fillna(0) - latest["planned_pct"].fillna(0)
        st.dataframe(
            latest.sort_values("stage"),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Latest actuals snapshot")
    latest_actuals = latest_week_snapshot(actuals)
    st.dataframe(
        latest_actuals.head(20),
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------
# Extra visuals
# -----------------------------

st.divider()
st.subheader("3. Weekly overview")

cols = st.columns(2)
with cols[0]:
    if actuals_view.empty:
        st.info("No weekly data to show.")
    else:
        weekly = actuals_view.groupby("week_start", as_index=False)[pct_cols].mean(numeric_only=True)
        weekly_long = weekly.melt(id_vars=["week_start"], var_name="stage_col", value_name="pct")
        weekly_long["stage"] = weekly_long["stage_col"].str.replace("pct_of_", "", regex=False)
        fig = px.line(
            weekly_long,
            x="week_start",
            y="pct",
            color="stage",
            markers=True,
            title="Average cumulative % by stage over time",
        )
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

with cols[1]:
    if plan_curve is None:
        st.info("Paste plan data to enable the plan-versus-actual chart.")
    else:
        # Show a compact plan vs actual summary.
        summary = (
            plan_curve.groupby("stage", as_index=False)
            .agg(
                planned_pct=("planned_pct", "mean"),
                actual_pct=("actual_pct", "mean"),
                max_planned_pct=("planned_pct", "max"),
                max_actual_pct=("actual_pct", "max"),
            )
            .sort_values("stage")
        )
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Planned", x=summary["stage"], y=summary["planned_pct"]))
        fig.add_trace(go.Bar(name="Actual", x=summary["stage"], y=summary["actual_pct"]))
        fig.update_layout(
            barmode="group",
            title="Average plan vs actual by stage",
            height=420,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Data tables / debug views
# -----------------------------

st.divider()
st.subheader("4. Data tables")

tab1, tab2, tab3 = st.tabs(["Actuals", "Plan parsed", "Plan vs actual"])

with tab1:
    st.dataframe(actuals_view, use_container_width=True, hide_index=True)

with tab2:
    if plan is None:
        st.info("No plan data pasted yet.")
    else:
        st.dataframe(plan.long.sort_values(["stage", "week_start", "planned_version"]), use_container_width=True, hide_index=True)

with tab3:
    if plan_curve is None:
        st.info("No plan-versus-actual summary available.")
    else:
        st.dataframe(plan_curve.sort_values(["stage", "week_start"]), use_container_width=True, hide_index=True)

# -----------------------------
# Footer notes
# -----------------------------

with st.expander("Implementation notes"):
    st.markdown(
        """
- The app assumes your actuals query already returns cumulative percentages by stagger per version per week.
- Plan data is interpreted as a weekly planned version schedule per stage.
- If you want strict plan-vs-actual per cell, add a cell-level plan table and join on `week_start + cell + stage`.
- For a production deployment, connect the app directly to the SQL query and cache results on a schedule.
        """
    )
