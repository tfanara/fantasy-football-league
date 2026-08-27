import streamlit as st
import pandas as pd
from pathlib import Path


# -----------------------------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Lineup Efficiency",
    page_icon="🎯",
    layout="wide",
)


# -----------------------------------------------------------------------------
# PATHS
# -----------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

ANALYSIS_DIR = (
    BASE_DIR
    / "data"
    / "matchups"
    / "player_week_stats"
    / "analysis"
)

TEAM_WEEK_FILE = ANALYSIS_DIR / "lineup_efficiency_team_week.csv"
SEASON_FILE = ANALYSIS_DIR / "lineup_efficiency_season.csv"
ALL_TIME_FILE = ANALYSIS_DIR / "lineup_efficiency_all_time.csv"
DECISIONS_FILE = ANALYSIS_DIR / "lineup_efficiency_decisions.csv"


# -----------------------------------------------------------------------------
# STYLE
# -----------------------------------------------------------------------------

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 3rem;
            max-width: 1450px;
        }

        .hero {
            padding: 1.6rem 1.8rem;
            border-radius: 18px;
            background:
                linear-gradient(
                    135deg,
                    rgba(30, 41, 59, 0.98),
                    rgba(15, 23, 42, 0.98)
                );
            color: white;
            margin-bottom: 1.4rem;
            box-shadow: 0 10px 30px rgba(0,0,0,.18);
        }

        .hero h1 {
            margin: 0;
            font-size: 2.2rem;
            font-weight: 800;
        }

        .hero p {
            margin: .4rem 0 0 0;
            color: #cbd5e1;
            font-size: 1rem;
        }

        .section-title {
            font-size: 1.25rem;
            font-weight: 800;
            margin-top: 1.1rem;
            margin-bottom: .5rem;
        }

        .subtle {
            color: #64748b;
            font-size: .92rem;
        }

        div[data-testid="stMetric"] {
            background: rgba(148, 163, 184, 0.08);
            border: 1px solid rgba(148, 163, 184, 0.20);
            padding: 1rem 1rem;
            border-radius: 14px;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 14px;
            overflow: hidden;
        }

        .callout {
            padding: 1rem 1.1rem;
            border-radius: 14px;
            background: rgba(148,163,184,.08);
            border: 1px solid rgba(148,163,184,.18);
            margin-bottom: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# LOAD DATA
# -----------------------------------------------------------------------------

@st.cache_data
def load_data():
    files = {
        "team_week": TEAM_WEEK_FILE,
        "season": SEASON_FILE,
        "all_time": ALL_TIME_FILE,
        "decisions": DECISIONS_FILE,
    }

    missing = [
        str(path)
        for path in files.values()
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing lineup-efficiency analysis file(s):\n"
            + "\n".join(missing)
        )

    return (
        pd.read_csv(files["team_week"]),
        pd.read_csv(files["season"]),
        pd.read_csv(files["all_time"]),
        pd.read_csv(files["decisions"]),
    )


try:
    team_week, season, all_time, decisions = load_data()
except Exception as exc:
    st.error("Could not load lineup-efficiency analysis data.")
    st.exception(exc)
    st.stop()


# -----------------------------------------------------------------------------
# CLEAN / DERIVED FIELDS
# -----------------------------------------------------------------------------

for df in [team_week, season, all_time, decisions]:
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "week" in df.columns:
        df["week"] = pd.to_numeric(df["week"], errors="coerce").astype("Int64")

numeric_cols = [
    "actual_score",
    "optimal_score",
    "points_left_on_bench",
    "lineup_efficiency_pct",
    "actual_points",
    "optimal_points",
    "avg_weekly_points_left",
    "avg_lineup_efficiency_pct",
    "season_efficiency_pct",
    "all_time_efficiency_pct",
    "worst_week_points_left",
    "fantasy_points",
]

for df in [team_week, season, all_time, decisions]:
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


# -----------------------------------------------------------------------------
# HERO
# -----------------------------------------------------------------------------

st.markdown(
    """
    <div class="hero">
        <h1>🎯 Lineup Efficiency</h1>
        <p>
            How much did each manager squeeze out of the roster they actually had?
            This compares the real starting lineup to the best legal lineup that
            could have been started that week.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# TOP-LEVEL LEAGUE METRICS
# -----------------------------------------------------------------------------

total_actual = team_week["actual_score"].sum()
total_optimal = team_week["optimal_score"].sum()
total_left = team_week["points_left_on_bench"].sum()

league_efficiency = (
    total_actual / total_optimal * 100
    if total_optimal
    else 0
)

worst_week_row = team_week.loc[
    team_week["points_left_on_bench"].idxmax()
]

best_all_time_row = all_time.sort_values(
    "all_time_efficiency_pct",
    ascending=False,
).iloc[0]

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "League Efficiency",
    f"{league_efficiency:.1f}%",
)

c2.metric(
    "Points Left on Bench",
    f"{total_left:,.1f}",
)

c3.metric(
    "Best All-Time Manager",
    str(best_all_time_row["fantasy_team"]),
    f"{best_all_time_row['all_time_efficiency_pct']:.1f}% efficient",
)

c4.metric(
    "Worst Single Week",
    f"{worst_week_row['points_left_on_bench']:.1f} pts",
    (
        f"{worst_week_row['fantasy_team']} · "
        f"{int(worst_week_row['year'])} W{int(worst_week_row['week'])}"
    ),
)


# -----------------------------------------------------------------------------
# TABS
# -----------------------------------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🏆 All-Time",
        "📅 By Season",
        "💥 Worst Decisions",
        "🔎 Team Explorer",
    ]
)


# -----------------------------------------------------------------------------
# ALL-TIME
# -----------------------------------------------------------------------------

with tab1:
    st.markdown(
        '<div class="section-title">All-Time Lineup Efficiency Rankings</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="subtle">
            Higher efficiency is better. Points left on the bench is the gap
            between the lineup actually started and the best legal lineup available.
        </div>
        """,
        unsafe_allow_html=True,
    )

    all_time_view = all_time.copy()

    sort_cols = [
        c for c in [
            "efficiency_rank",
            "all_time_efficiency_pct",
        ]
        if c in all_time_view.columns
    ]

    if "efficiency_rank" in all_time_view.columns:
        all_time_view = all_time_view.sort_values(
            ["efficiency_rank", "fantasy_team"]
        )
    else:
        all_time_view = all_time_view.sort_values(
            "all_time_efficiency_pct",
            ascending=False,
        )

    rename = {
        "efficiency_rank": "Rank",
        "fantasy_team": "Team",
        "team_weeks": "Team-Weeks",
        "actual_points": "Actual Pts",
        "optimal_points": "Optimal Pts",
        "points_left_on_bench": "Pts Left",
        "avg_weekly_points_left": "Avg Left / Week",
        "all_time_efficiency_pct": "Efficiency %",
        "worst_week_points_left": "Worst Week",
        "avoidable_starts": "Avoidable Starts",
    }

    display_cols = [
        c for c in rename
        if c in all_time_view.columns
    ]

    leaderboard = all_time_view[display_cols].rename(
        columns=rename
    )

    st.dataframe(
        leaderboard,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Efficiency %": st.column_config.NumberColumn(
                format="%.2f%%"
            ),
            "Actual Pts": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Optimal Pts": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Pts Left": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Avg Left / Week": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Worst Week": st.column_config.NumberColumn(
                format="%.2f"
            ),
        },
    )

    st.markdown(
        '<div class="section-title">Best vs. Worst Managers</div>',
        unsafe_allow_html=True,
    )

    best5 = all_time.sort_values(
        "all_time_efficiency_pct",
        ascending=False,
    ).head(5)

    worst5 = all_time.sort_values(
        "all_time_efficiency_pct",
        ascending=True,
    ).head(5)

    left, right = st.columns(2)

    with left:
        st.markdown("**Most Efficient**")
        st.bar_chart(
            best5.set_index("fantasy_team")[
                "all_time_efficiency_pct"
            ]
        )

    with right:
        st.markdown("**Least Efficient**")
        st.bar_chart(
            worst5.set_index("fantasy_team")[
                "all_time_efficiency_pct"
            ]
        )


# -----------------------------------------------------------------------------
# BY SEASON
# -----------------------------------------------------------------------------

with tab2:
    st.markdown(
        '<div class="section-title">Season-by-Season Rankings</div>',
        unsafe_allow_html=True,
    )

    years = sorted(
        season["year"].dropna().astype(int).unique(),
        reverse=True,
    )

    selected_year = st.selectbox(
        "Season",
        years,
        index=0,
    )

    year_df = season[
        season["year"] == selected_year
    ].copy()

    efficiency_col = (
        "season_efficiency_pct"
        if "season_efficiency_pct" in year_df.columns
        else "avg_lineup_efficiency_pct"
    )

    year_df = year_df.sort_values(
        efficiency_col,
        ascending=False,
    )

    year_df.insert(
        0,
        "rank",
        range(1, len(year_df) + 1),
    )

    season_rename = {
        "rank": "Rank",
        "fantasy_team": "Team",
        "weeks": "Weeks",
        "actual_points": "Actual Pts",
        "optimal_points": "Optimal Pts",
        "points_left_on_bench": "Pts Left",
        "avg_weekly_points_left": "Avg Left / Week",
        "season_efficiency_pct": "Efficiency %",
        "avg_lineup_efficiency_pct": "Avg Weekly Efficiency %",
        "worst_week_points_left": "Worst Week",
        "avoidable_starts": "Avoidable Starts",
    }

    season_cols = [
        c for c in season_rename
        if c in year_df.columns
    ]

    st.dataframe(
        year_df[season_cols].rename(
            columns=season_rename
        ),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Efficiency %": st.column_config.NumberColumn(
                format="%.2f%%"
            ),
            "Avg Weekly Efficiency %": st.column_config.NumberColumn(
                format="%.2f%%"
            ),
            "Actual Pts": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Optimal Pts": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Pts Left": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Avg Left / Week": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Worst Week": st.column_config.NumberColumn(
                format="%.2f"
            ),
        },
    )

    st.markdown(
        '<div class="section-title">Efficiency by Team</div>',
        unsafe_allow_html=True,
    )

    st.bar_chart(
        year_df.set_index("fantasy_team")[
            efficiency_col
        ]
    )


# -----------------------------------------------------------------------------
# WORST DECISIONS
# -----------------------------------------------------------------------------

with tab3:
    st.markdown(
        '<div class="section-title">Biggest Weekly Lineup Misses</div>',
        unsafe_allow_html=True,
    )

    worst_weeks = (
        team_week.sort_values(
            "points_left_on_bench",
            ascending=False,
        )
        .head(50)
        .copy()
    )

    worst_weeks["Game"] = (
        worst_weeks["year"].astype(str)
        + " W"
        + worst_weeks["week"].astype(str)
    )

    worst_cols = [
        "Game",
        "fantasy_team",
        "opponent",
        "actual_score",
        "optimal_score",
        "points_left_on_bench",
        "lineup_efficiency_pct",
        "should_have_benched",
        "should_have_started",
    ]

    worst_cols = [
        c for c in worst_cols
        if c in worst_weeks.columns
    ]

    worst_rename = {
        "fantasy_team": "Team",
        "opponent": "Opponent",
        "actual_score": "Actual",
        "optimal_score": "Optimal",
        "points_left_on_bench": "Pts Left",
        "lineup_efficiency_pct": "Efficiency %",
        "should_have_benched": "Should Have Benched",
        "should_have_started": "Should Have Started",
    }

    st.dataframe(
        worst_weeks[worst_cols].rename(
            columns=worst_rename
        ),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Actual": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Optimal": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Pts Left": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Efficiency %": st.column_config.NumberColumn(
                format="%.2f%%"
            ),
        },
    )

    if not decisions.empty:
        st.markdown(
            '<div class="section-title">Individual Bench Explosions</div>',
            unsafe_allow_html=True,
        )

        missed = decisions[
            decisions["decision_type"] == "Should Have Started"
        ].copy()

        missed = missed.sort_values(
            "fantasy_points",
            ascending=False,
        ).head(40)

        decision_cols = [
            c for c in [
                "year",
                "week",
                "fantasy_team",
                "opponent",
                "player",
                "player_position",
                "lineup_slot",
                "fantasy_points",
            ]
            if c in missed.columns
        ]

        st.dataframe(
            missed[decision_cols].rename(
                columns={
                    "year": "Year",
                    "week": "Week",
                    "fantasy_team": "Team",
                    "opponent": "Opponent",
                    "player": "Player",
                    "player_position": "Pos",
                    "lineup_slot": "Original Slot",
                    "fantasy_points": "Fantasy Pts",
                }
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Fantasy Pts": st.column_config.NumberColumn(
                    format="%.2f"
                )
            },
        )


# -----------------------------------------------------------------------------
# TEAM EXPLORER
# -----------------------------------------------------------------------------

with tab4:
    st.markdown(
        '<div class="section-title">Team Explorer</div>',
        unsafe_allow_html=True,
    )

    teams = sorted(
        team_week["fantasy_team"]
        .dropna()
        .astype(str)
        .unique()
    )

    selected_team = st.selectbox(
        "Team",
        teams,
    )

    team_data = team_week[
        team_week["fantasy_team"] == selected_team
    ].copy()

    if team_data.empty:
        st.info("No lineup-efficiency data found for this team.")
    else:
        actual = team_data["actual_score"].sum()
        optimal = team_data["optimal_score"].sum()
        left_pts = team_data["points_left_on_bench"].sum()
        eff = actual / optimal * 100 if optimal else 0

        worst = team_data.loc[
            team_data["points_left_on_bench"].idxmax()
        ]

        best_week = team_data.loc[
            team_data["lineup_efficiency_pct"].idxmax()
        ]

        m1, m2, m3, m4 = st.columns(4)

        m1.metric(
            "Overall Efficiency",
            f"{eff:.1f}%",
        )
        m2.metric(
            "Points Left",
            f"{left_pts:,.1f}",
        )
        m3.metric(
            "Worst Week",
            f"{worst['points_left_on_bench']:.1f} pts",
            f"{int(worst['year'])} W{int(worst['week'])}",
        )
        m4.metric(
            "Best Weekly Efficiency",
            f"{best_week['lineup_efficiency_pct']:.1f}%",
            f"{int(best_week['year'])} W{int(best_week['week'])}",
        )

        trend = (
            team_data.sort_values(
                ["year", "week"]
            )
            .copy()
        )

        trend["Season-Week"] = (
            trend["year"].astype(str)
            + "-W"
            + trend["week"].astype(str).str.zfill(2)
        )

        st.markdown(
            '<div class="section-title">Weekly Efficiency Trend</div>',
            unsafe_allow_html=True,
        )

        st.line_chart(
            trend.set_index("Season-Week")[
                "lineup_efficiency_pct"
            ]
        )

        st.markdown(
            '<div class="section-title">Worst Lineup Decisions</div>',
            unsafe_allow_html=True,
        )

        team_worst = trend.sort_values(
            "points_left_on_bench",
            ascending=False,
        ).head(15)

        st.dataframe(
            team_worst[
                [
                    c for c in [
                        "year",
                        "week",
                        "opponent",
                        "actual_score",
                        "optimal_score",
                        "points_left_on_bench",
                        "lineup_efficiency_pct",
                        "should_have_benched",
                        "should_have_started",
                    ]
                    if c in team_worst.columns
                ]
            ].rename(
                columns={
                    "year": "Year",
                    "week": "Week",
                    "opponent": "Opponent",
                    "actual_score": "Actual",
                    "optimal_score": "Optimal",
                    "points_left_on_bench": "Pts Left",
                    "lineup_efficiency_pct": "Efficiency %",
                    "should_have_benched": "Should Have Benched",
                    "should_have_started": "Should Have Started",
                }
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Actual": st.column_config.NumberColumn(
                    format="%.2f"
                ),
                "Optimal": st.column_config.NumberColumn(
                    format="%.2f"
                ),
                "Pts Left": st.column_config.NumberColumn(
                    format="%.2f"
                ),
                "Efficiency %": st.column_config.NumberColumn(
                    format="%.2f%%"
                ),
            },
        )


# -----------------------------------------------------------------------------
# FOOTNOTE
# -----------------------------------------------------------------------------

st.markdown("---")

st.caption(
    "Lineup efficiency compares each submitted starting lineup against the "
    "highest-scoring legal lineup available on that team's active roster for "
    "that week. IR players are excluded from optimal-lineup selection."
)