import streamlit as st
import pandas as pd
import json
import html
from pathlib import Path

from season_config import CURRENT_SEASON

try:
    from team_aliases import canonical_team
except ImportError:
    def canonical_team(name):
        aliases = {
            "PickUpYourBratsMalle": "ThreatLevelMidnight",
            "Little Red Fournette": "Post Mahomes",
            "Ur The Best Bellows": "Joe Mantegna",
            "You Better Park It": "Buttermilk Puuump",
            "Buttermilk Pump": "Buttermilk Puuump",
        }
        return aliases.get(name, name)


st.set_page_config(
    page_title="Power Rankings",
    page_icon="⚡",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent.parent
WEEKLY_FILE = BASE_DIR / "data" / "analysis" / "power_rankings_weekly.csv"
COMMENTARY_DIR = BASE_DIR / "data" / "power_rankings"


@st.cache_data
def load_rankings():
    if not WEEKLY_FILE.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(WEEKLY_FILE)
    except Exception:
        return pd.DataFrame()

    if "fantasy_team" in df.columns:
        df["fantasy_team"] = df["fantasy_team"].apply(canonical_team)

    for col in [
        "year", "through_week", "power_rank", "previous_rank",
        "rank_change", "power_score", "avg_points", "all_play_pct",
        "lineup_efficiency_pct", "scoring_rank", "all_play_rank",
        "efficiency_rank", "points_left_on_bench",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data
def load_generated_commentary(year, week):
    """Load validated editorial commentary for one ranking snapshot."""
    path = (
        COMMENTARY_DIR
        / str(int(year))
        / f"week_{int(week):02d}_commentary.json"
    )
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if payload.get("schema_version") != 1:
        return {}

    try:
        if int(payload.get("season")) != int(year):
            return {}
        if int(payload.get("week")) != int(week):
            return {}
    except (TypeError, ValueError):
        return {}

    rows = payload.get("commentary")
    if not isinstance(rows, list):
        return {}

    commentary = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        team = canonical_team(str(row.get("team", "")).strip())
        body = str(row.get("commentary", "")).strip()
        if team and body and body.lower() != "nan":
            commentary[team] = body

    return commentary


def movement_text(row):
    previous = row.get("previous_rank")
    change = row.get("rank_change")

    if pd.isna(previous):
        return "NEW"

    change = int(change or 0)
    if change > 0:
        return f"▲ {change}"
    if change < 0:
        return f"▼ {abs(change)}"
    return "—"


def movement_class(row):
    previous = row.get("previous_rank")
    change = row.get("rank_change")
    if pd.isna(previous):
        return "move-new"
    change = int(change or 0)
    if change > 0:
        return "move-up"
    if change < 0:
        return "move-down"
    return "move-flat"


def safe_rank(value):
    return "—" if pd.isna(value) else f"#{int(value)}"


def safe_num(value, digits=2):
    return "—" if pd.isna(value) else f"{float(value):.{digits}f}"


rankings = load_rankings()

st.markdown("""
<style>
.rank-card {
    border: 1px solid rgba(128,128,128,.28);
    border-radius: 14px;
    padding: 13px 16px 12px;
    margin: 0 0 9px 0;
    background: rgba(128,128,128,.045);
}
.rank-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
}
.rank-identity {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    min-width: 0;
}
.rank-number {
    font-size: 1.45rem;
    font-weight: 800;
    line-height: 1.05;
    min-width: 30px;
}
.rank-team {
    font-size: 1.08rem;
    font-weight: 750;
    line-height: 1.2;
    overflow-wrap: anywhere;
}
.rank-record {
    color: rgba(128,128,128,.95);
    font-size: .80rem;
    margin-top: 2px;
}
.score-wrap {
    text-align: right;
    flex-shrink: 0;
}
.power-score {
    font-size: 1.32rem;
    font-weight: 800;
    line-height: 1;
}
.power-label {
    color: rgba(128,128,128,.90);
    font-size: .65rem;
    margin-top: 3px;
    text-transform: uppercase;
    letter-spacing: .04em;
}
.rank-commentary {
    margin: 9px 0 0 40px;
    font-size: .92rem;
    line-height: 1.45;
    color: rgba(210,210,210,.95);
    max-width: 1050px;
}
.rank-metrics {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 5px 0;
    margin: 9px 0 0 40px;
    padding-top: 8px;
    border-top: 1px solid rgba(128,128,128,.18);
    color: rgba(128,128,128,.95);
    font-size: .75rem;
}
.metric-inline { white-space: nowrap; }
.metric-inline + .metric-inline::before {
    content: "•";
    margin: 0 9px;
    color: rgba(128,128,128,.55);
}
.metric-inline strong {
    color: rgba(225,225,225,.95);
    font-size: .79rem;
    font-weight: 700;
}
.move {
    display: inline-block;
    font-weight: 700;
    font-size: .72rem;
    margin-left: 6px;
}
.move-up { color: #2e9d55; }
.move-down { color: #d44c4c; }
.move-flat, .move-new { color: rgba(128,128,128,.95); }

@media (max-width: 640px) {
    .rank-card {
        padding: 12px;
        border-radius: 12px;
        margin-bottom: 8px;
    }
    .rank-number {
        font-size: 1.25rem;
        min-width: 25px;
    }
    .rank-identity { gap: 7px; }
    .rank-team { font-size: .98rem; }
    .rank-record { font-size: .76rem; }
    .power-score { font-size: 1.12rem; }
    .power-label { font-size: .58rem; }
    .rank-commentary {
        margin-left: 32px;
        margin-top: 8px;
        font-size: .87rem;
        line-height: 1.42;
    }
    .rank-metrics {
        margin-left: 32px;
        margin-top: 8px;
        padding-top: 7px;
        font-size: .70rem;
        line-height: 1.4;
    }
    .metric-inline + .metric-inline::before { margin: 0 6px; }
    .metric-inline strong { font-size: .73rem; }
}
</style>
""", unsafe_allow_html=True)

st.title("⚡ Power Rankings")

if rankings.empty:
    st.warning(
        "Power rankings have not been built yet. "
        "Run `python build_power_rankings.py` and redeploy the generated data."
    )
    st.stop()

years = sorted(
    rankings["year"].dropna().astype(int).unique(),
    reverse=True,
)

default_year = CURRENT_SEASON if CURRENT_SEASON in years else years[0]

selector_col1, selector_col2 = st.columns(2)

with selector_col1:
    selected_year = st.selectbox(
        "Season",
        years,
        index=years.index(default_year),
    )

available_weeks = sorted(
    rankings.loc[
        rankings["year"].eq(selected_year),
        "through_week",
    ].dropna().astype(int).unique()
)

with selector_col2:
    selected_week = st.selectbox(
        "Through Week",
        available_weeks,
        index=len(available_weeks) - 1,
    )

snapshot = rankings[
    rankings["year"].eq(selected_year)
    & rankings["through_week"].eq(selected_week)
].copy()

# The ranking engine is the single source of truth.
# Never recalculate or override its ordering in the Streamlit UI.
snapshot = snapshot.sort_values(
    ["power_rank", "fantasy_team"],
    ascending=[True, True],
).reset_index(drop=True)
snapshot["display_rank"] = snapshot["power_rank"]

generated_commentary = load_generated_commentary(
    selected_year,
    selected_week,
)

st.caption(
    f"{selected_year} Power Rankings through Week {selected_week}. "
    "Power rankings measure current team strength, not simply the standings."
)

rounded_scores = pd.to_numeric(
    snapshot["power_score"], errors="coerce"
).round(2)
duplicate_rounded_scores = set(
    rounded_scores[rounded_scores.duplicated(keep=False)].dropna().tolist()
)

for _, row in snapshot.iterrows():
    movement = movement_text(row)
    move_class = movement_class(row)

    team = str(row["fantasy_team"])
    record = str(row.get("record", "—"))
    team_html = html.escape(team)
    record_html = html.escape(record)
    raw_score = row.get("power_score")
    score_digits = (
        3
        if pd.notna(raw_score) and round(float(raw_score), 2) in duplicate_rounded_scores
        else 2
    )
    score = safe_num(raw_score, score_digits)
    avg = safe_num(row.get("avg_points"), 2)

    all_play = row.get("all_play_pct")
    all_play_display = (
        "—" if pd.isna(all_play) else f"{float(all_play) * 100:.1f}%"
    )

    efficiency = row.get("lineup_efficiency_pct")
    efficiency_display = (
        "—" if pd.isna(efficiency) else f"{float(efficiency):.1f}%"
    )

    rank = int(row["display_rank"])

    # Use only separately generated, validated editorial commentary.
    # Evidence tags remain internal and are never rendered.
    commentary = generated_commentary.get(team, "")
    commentary_html = (
        f'<div class="rank-commentary">{html.escape(commentary)}</div>'
        if commentary
        else ""
    )

    st.markdown(
        f"""
        <div class="rank-card">
          <div class="rank-top">
            <div class="rank-identity">
              <div class="rank-number">{rank}</div>
              <div>
                <div class="rank-team">
                  {team_html}
                  <span class="move {move_class}">{movement}</span>
                </div>
                <div class="rank-record">{record_html}</div>
              </div>
            </div>
            <div class="score-wrap">
              <div class="power-score">{score}</div>
              <div class="power-label">Power Score</div>
            </div>
          </div>
          {commentary_html}
          <div class="rank-metrics">
            <span class="metric-inline"><strong>{avg}</strong> PPG {safe_rank(row.get("scoring_rank"))}</span>
            <span class="metric-inline"><strong>{all_play_display}</strong> All-Play {safe_rank(row.get("all_play_rank"))}</span>
            <span class="metric-inline"><strong>{efficiency_display}</strong> Lineup {safe_rank(row.get("efficiency_rank"))}</span>
            <span class="metric-inline"><strong>{movement}</strong> Movement</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.expander("About the Power Rankings"):
    st.markdown(
        """
Power Rankings are designed to measure **current team strength**, not simply
reproduce the standings.

The model considers multiple signals from each team's performance, including
scoring, performance against the rest of the league, lineup execution, results,
and recent form as the season develops.

A strong record does not automatically mean a high Power Ranking, and a team can
rank well despite a loss if its underlying weekly performance was strong.

The exact ranking formula is intentionally kept behind the curtain.
        """
    )

with st.expander("Detailed Ranking Data"):
    detail = snapshot[
        [
            c for c in [
                "display_rank",
                "fantasy_team",
                "record",
                "power_score",
                "avg_points",
                "all_play_pct",
                "lineup_efficiency_pct",
                "points_left_on_bench",
                "scoring_rank",
                "all_play_rank",
                "efficiency_rank",
            ]
            if c in snapshot.columns
        ]
    ].copy()

    detail = detail.rename(
        columns={
            "display_rank": "Rank",
            "fantasy_team": "Franchise",
            "record": "Record",
            "power_score": "Power Score",
            "avg_points": "Avg Points",
            "all_play_pct": "All-Play %",
            "lineup_efficiency_pct": "Lineup Efficiency %",
            "points_left_on_bench": "Points Left on Bench",
            "scoring_rank": "Scoring Rank",
            "all_play_rank": "All-Play Rank",
            "efficiency_rank": "Efficiency Rank",
        }
    )

    if "All-Play %" in detail.columns:
        detail["All-Play %"] = detail["All-Play %"] * 100

    st.dataframe(
        detail,
        use_container_width=True,
        hide_index=True,
    )