import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from textwrap import dedent

from season_config import (
    LAST_COMPLETED_SEASON,
    LAST_COMPLETED_DRAFT_SEASON,
)

try:
    from team_aliases import canonical_team
except ImportError:
    def canonical_team(name):
        return name


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="League Analysis",
    page_icon="📊",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = BASE_DIR / "data" / "analysis"

FILES = {
    "detail": ANALYSIS_DIR / "qb_wr_stacks.csv",
    "summary": ANALYSIS_DIR / "qb_wr_stack_summary.csv",
    "team_season": ANALYSIS_DIR / "qb_wr_stack_team_season.csv",
    "within_summary": ANALYSIS_DIR / "qb_wr_stack_within_summary.csv",
    "by_season": ANALYSIS_DIR / "qb_wr_stack_by_season.csv",
    "by_franchise": ANALYSIS_DIR / "qb_wr_stack_by_franchise.csv",
    "pairs": ANALYSIS_DIR / "qb_wr_stack_pairs.csv",
}


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>
    .block-container{
        max-width:1500px;
        padding-top:1.5rem;
        padding-bottom:3rem;
    }

    .analysis-hero{
        padding:1.6rem 1.8rem;
        border-radius:18px;
        background:linear-gradient(
            135deg,
            rgba(30,41,59,.98),
            rgba(15,23,42,.98)
        );
        color:white;
        margin-bottom:1.2rem;
    }

    .analysis-hero h1{
        margin:0;
        font-size:2.25rem;
        font-weight:800;
    }

    .analysis-hero p{
        margin:.4rem 0 0 0;
        color:#cbd5e1;
    }

    div[data-testid="stMetric"]{
        background:rgba(148,163,184,.08);
        border:1px solid rgba(148,163,184,.18);
        padding:.85rem;
        border-radius:14px;
    }

    .verdict-box{
        padding:1.2rem 1.35rem;
        border-radius:16px;
        border:1px solid rgba(148,163,184,.22);
        background:rgba(148,163,184,.07);
        margin:.7rem 0 1.2rem 0;
    }

    .verdict-title{
        font-size:1.25rem;
        font-weight:850;
        margin-bottom:.35rem;
    }

    .verdict-text{
        font-size:1rem;
        line-height:1.55;
        opacity:.88;
    }

    .section-note{
        opacity:.70;
        font-size:.90rem;
    }
    
    .stack-effect-box{
        padding:1rem 1.2rem;
        border-radius:16px;
        border:1px solid rgba(148,163,184,.18);
        background:rgba(148,163,184,.045);
        margin:.65rem 0 .2rem 0;
    }

    .stack-effect-title{
        font-size:.78rem;
        font-weight:850;
        opacity:.60;
        text-transform:uppercase;
        letter-spacing:.07em;
        margin-bottom:.7rem;
    }

    .effect-row{
        display:grid;
        grid-template-columns:155px 95px 1fr 70px;
        gap:.75rem;
        align-items:center;
        margin:.5rem 0;
    }

    .effect-label{
        font-weight:750;
        white-space:nowrap;
    }

    .effect-value{
        font-weight:850;
        text-align:right;
    }

    .effect-track{
        height:10px;
        background:rgba(148,163,184,.12);
        border-radius:999px;
        overflow:hidden;
    }

    .effect-fill{
        height:100%;
        border-radius:999px;
        background:rgba(148,163,184,.72);
    }

    .effect-direction{
        font-size:.85rem;
        font-weight:750;
        opacity:.68;
        text-align:right;
    }
    
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data():
    out = {}

    for name, path in FILES.items():
        try:
            out[name] = (
                pd.read_csv(path)
                if path.exists()
                else pd.DataFrame()
            )
        except Exception:
            out[name] = pd.DataFrame()

    return out


data = load_data()

detail = data["detail"].copy()
summary = data["summary"].copy()
team_season = data["team_season"].copy()
within_summary = data["within_summary"].copy()
by_season = data["by_season"].copy()
by_franchise = data["by_franchise"].copy()
pairs = data["pairs"].copy()


# ============================================================
# HELPERS
# ============================================================

def numeric(df, cols):
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )


numeric(
    detail,
    [
        "year",
        "week",
        "team_score",
        "opponent_score",
        "margin",
        "win",
        "top_quartile_score",
    ],
)

numeric(
    team_season,
    [
        "year",
        "stack_weeks",
        "nonstack_weeks",
        "stack_avg_score",
        "nonstack_avg_score",
        "score_difference",
        "stack_win_rate",
        "nonstack_win_rate",
        "win_rate_difference",
        "stack_avg_margin",
        "nonstack_avg_margin",
        "margin_difference",
        "stack_top_quartile_rate",
        "nonstack_top_quartile_rate",
        "top_quartile_difference",
    ],
)

numeric(
    by_franchise,
    [
        "stack_weeks",
        "stack_wins",
        "stack_win_rate",
        "stack_avg_score",
        "stack_avg_margin",
        "stack_top_quartile_rate",
        "total_team_weeks",
        "stack_rate",
    ],
)

numeric(
    pairs,
    [
        "stack_weeks",
        "wins",
        "win_rate",
        "avg_team_score",
        "avg_margin",
        "top_quartile_rate",
        "avg_qb_points",
        "avg_wr_points",
        "avg_stack_player_points",
    ],
)


def pct(value, decimals=1):
    if pd.isna(value):
        return "—"

    return f"{value * 100:.{decimals}f}%"


def signed_pct(value, decimals=1):
    if pd.isna(value):
        return "—"

    return f"{value * 100:+.{decimals}f}%"


def points(value, signed=False):
    if pd.isna(value):
        return "—"

    if signed:
        return f"{value:+.2f}"

    return f"{value:.2f}"


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
    <div class="analysis-hero">
        <h1>📊 League Analysis</h1>
        <p>
            Digging into the strategies, trends, and questionable
            decisions that have shaped league history.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# ANALYSIS SELECTOR

# ============================================================

analysis_groups = [
    (
        "Strategy",
        [
            ("🏈 QB/WR Stacks", "🏈 QB/WR Stacking", True),
            ("🏟️ Positional Edge", "🏟️ Positional Advantage", True),
            ("📝 Draft Trends", "📝 Draft Trends", True),
            ("👑 Star Dependency", "👑 Star Dependency", False),
        ],
    ),
    (
        "Management",
        [
            ("🪑 Bench Decisions", "🪑 Bench Decisions", False),
            ("📈 Draft Value", "📈 Draft Value", True),
            ("🔄 Waiver Value", "🔄 Waiver Value", True),
        ],
    ),
    (
        "Luck",
        [
            ("💀 Bad Beats", "💀 Bad Beat Index", True),
            ("🎲 Schedule Swap", "🎲 Schedule Swap", True),
        ],
    ),
    (
        "Winning",
        [
            ("🏆 Championship DNA", "🏆 Championship DNA", True),
            ("🧠 Manager Skill", "🧠 Manager Skill", True),
        ],
    ),
]

if "analysis_choice" not in st.session_state:
    st.session_state["analysis_choice"] = "🏈 QB/WR Stacking"


def choose_analysis(name):
    st.session_state["analysis_choice"] = name


for group_name, options in analysis_groups:

    label_col, *button_cols = st.columns(
        [0.72] + [1.0] * len(options),
        gap="small",
    )

    with label_col:
        st.markdown(
            f"""
            <div style='
                padding-top:.45rem;
                font-size:.78rem;
                font-weight:800;
                opacity:.60;
                text-transform:uppercase;
                letter-spacing:.06em;
            '>
                {group_name}
            </div>
            """,
            unsafe_allow_html=True,
        )

    for col, (label, option, enabled) in zip(
        button_cols,
        options,
    ):

        with col:

            active = (
                st.session_state["analysis_choice"]
                == option
            )

            if enabled:
                st.button(
                    f"● {label}" if active else label,
                    key=f"analysis_btn_{option}",
                    use_container_width=True,
                    type="primary" if active else "secondary",
                    on_click=choose_analysis,
                    args=(option,),
                )

            else:
                st.button(
                    label,
                    key=f"analysis_btn_{option}",
                    use_container_width=True,
                    disabled=True,
                    help="Coming soon",
                )


analysis_choice = st.session_state["analysis_choice"]

st.divider()


# ============================================================

# QB / WR STACKING
# ============================================================

if analysis_choice == "🏈 QB/WR Stacking":

    st.header("🏈 QB/WR Stacking")

    st.caption(
        "A QB/WR stack occurs when a fantasy team starts a quarterback "
        "and at least one wide receiver from the same NFL team. "
        "Wide receivers started in a FLEX spot count."
    )

    required = [
        detail,
        summary,
        within_summary,
    ]

    if any(df.empty for df in required):

        st.error(
            "QB/WR stack analysis data is missing. "
            "Run build_stack_analysis.py."
        )

        st.stop()


    # ========================================================
    # CORE RESULTS
    # ========================================================

    stack_row = summary[
        summary["stack_status"]
        == "QB/WR Stack"
    ]

    no_stack_row = summary[
        summary["stack_status"]
        == "No QB/WR Stack"
    ]

    if stack_row.empty or no_stack_row.empty:
        st.error(
            "Stack summary does not contain both comparison groups."
        )
        st.stop()

    stack_row = stack_row.iloc[0]
    no_stack_row = no_stack_row.iloc[0]

    within = within_summary.iloc[0]


    # ========================================================
    # VERDICT

    # ========================================================

    st.markdown(
        """
        <div class="verdict-box">
            <div class="verdict-title">
                📈 League Verdict: Higher Ceiling, No Clear Win Advantage
            </div>
            <div class="verdict-text">
                Stack weeks have produced more high-end scoring performances,
                but that extra ceiling has not translated into more wins.
                Stacking looks more like an upside strategy than a consistent
                weekly advantage.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================

    # HEADLINE METRICS

    # ========================================================

    score_effect = float(
        within["mean_team_season_score_difference"]
    )

    top_quartile_effect = float(
        within["mean_team_season_top_quartile_difference"]
    )

    win_rate_effect = float(
        within["mean_team_season_win_rate_difference"]
    )

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "🏈 Stack Weeks",
        f"{int(stack_row['team_weeks']):,}",
    )

    m2.metric(
        "📈 Avg Scoring Effect",
        f"{score_effect:+.2f} pts",
    )

    m3.metric(
        "🚀 Top-Quartile Effect",
        f"{top_quartile_effect * 100:+.1f}%",
    )

    m4.metric(
        "🏆 Win-Rate Effect",
        f"{win_rate_effect * 100:+.1f}%",
    )

    st.caption(
        f"Within-team comparison: "
        f"{int(within['team_seasons'])} team-seasons where the same "
        f"franchise used both stacked and non-stacked lineups."
    )

    score_width = min(
        100,
        abs(score_effect) / 4.0 * 100,
    )

    quartile_width = min(
        100,
        abs(top_quartile_effect) / .10 * 100,
    )

    win_width = min(
        100,
        abs(win_rate_effect) / .10 * 100,
    )

    st.markdown("### Stack Effect")

    e1, e2, e3 = st.columns(3)

    with e1:
        st.metric(
            "📈 Scoring",
            f"{score_effect:+.2f} pts",
        )
        st.progress(
            min(abs(score_effect) / 4.0, 1.0)
        )
        st.caption("Higher")

    with e2:
        st.metric(
            "🚀 Top Quartile",
            f"{top_quartile_effect * 100:+.1f}%",
        )
        st.progress(
            min(abs(top_quartile_effect) / .10, 1.0)
        )
        st.caption("Higher")

    with e3:
        st.metric(
            "🏆 Win Rate",
            f"{win_rate_effect * 100:+.1f}%",
        )
        st.progress(
            min(abs(win_rate_effect) / .10, 1.0)
        )
        st.caption("Lower")

    st.info(
        "**What does Top Quartile mean?** "
        "A top-quartile week is a team score that ranks in the top 25% "
        "of all scores from that season. The +7.7% effect means stacked "
        "lineups were more likely to produce one of these high-end "
        "scoring weeks."
    )

    st.divider()


    # ========================================================

    # OVERALL COMPARISON
    # ========================================================

    st.subheader("Stacked vs. Non-Stacked")

    st.caption(
        "Raw league-wide results across every regular-season team-week."
    )

    overall = pd.DataFrame(
        [
            {
                "Lineup": "🏈 QB/WR Stack",
                "Team-Weeks":
                    int(stack_row["team_weeks"]),
                "Win Rate":
                    f"{float(stack_row['win_rate']):.1f}\u00a0%",
                "Avg Score":
                    stack_row["avg_score"],
                "Median Score":
                    stack_row["median_score"],
                "Avg Margin":
                    stack_row["avg_margin"],
                "Top Quartile":
                    f"{float(stack_row['top_quartile_rate']):.1f}\u00a0%",
            },
            {
                "Lineup": "No Stack",
                "Team-Weeks":
                    int(no_stack_row["team_weeks"]),
                "Win Rate":
                    f"{float(no_stack_row['win_rate']):.1f}\u00a0%",
                "Avg Score":
                    no_stack_row["avg_score"],
                "Median Score":
                    no_stack_row["median_score"],
                "Avg Margin":
                    no_stack_row["avg_margin"],
                "Top Quartile":
                    f"{float(no_stack_row['top_quartile_rate']):.1f}\u00a0%",
            },
        ]
    )

    st.dataframe(
        overall,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Lineup":
                st.column_config.TextColumn(
                    "Lineup",
                    width="large",
                ),
            "Team-Weeks":
                st.column_config.NumberColumn(
                    "Team-Weeks",
                    format="%d",
                ),
            "Win Rate":
                st.column_config.TextColumn(
                    "Win Rate",
                ),
            "Avg Score":
                st.column_config.NumberColumn(
                    "Avg Score",
                    format="%.2f",
                ),
            "Median Score":
                st.column_config.NumberColumn(
                    "Median Score",
                    format="%.2f",
                ),
            "Avg Margin":
                st.column_config.NumberColumn(
                    "Avg Margin",
                    format="%.2f",
                ),
            "Top Quartile":
                st.column_config.TextColumn(
                    "Top Quartile",
                ),
        },
    )

    st.caption(
        "Raw results are descriptive, not causal. Strong NFL offenses "
        "and elite players may be more likely to create attractive stacks."
    )

    st.divider()


    # ========================================================
    # WITHIN TEAM-SEASON
    # ========================================================

    st.subheader("🔬 Apples-to-Apples Comparison")

    st.caption(
        "This comparison only uses team-seasons in which the same "
        "fantasy team had at least one stack week and at least one "
        "non-stack week."
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Qualifying Team-Seasons",
        f"{int(within['team_seasons'])}",
    )

    c2.metric(
        "Average Difference",
        f"{float(within['mean_team_season_score_difference']):+.2f} pts",
    )

    c3.metric(
        "Median Difference",
        f"{float(within['median_team_season_score_difference']):+.2f} pts",
    )

    c4.metric(
        "Stack Scored More",
        pct(
            within[
                "pct_team_seasons_stack_scored_more"
            ]
        ),
    )

    st.caption(
        f"Stack weeks scored more in "
        f"{int(within['team_seasons_stack_scored_more'])} of "
        f"{int(within['team_seasons'])} qualifying team-seasons."
    )

    st.markdown(
        """
        **How to read this:** the average result favors stacking,
        but the median result is much smaller and only about half
        of qualifying team-seasons actually scored more during
        their stack weeks. The clearest historical difference is
        an increased chance of producing a high-end scoring week.
        """
    )

    st.divider()


    # ========================================================
    # STACK USAGE BY SEASON
    # ========================================================

    st.subheader("📅 Stack Usage Over Time")

    if by_season.empty:

        st.info("Season-level stack data is unavailable.")

    else:

        season_usage = (
            detail.groupby(
                "year",
                as_index=False,
            )
            .agg(
                Team_Weeks=(
                    "fantasy_team",
                    "size",
                ),
                Stack_Weeks=(
                    "has_qb_wr_stack",
                    "sum",
                ),
            )
        )

        season_usage["Stack Rate"] = (
            season_usage["Stack_Weeks"]
            / season_usage["Team_Weeks"]
            * 100
        )

        chart = (
            season_usage[
                [
                    "year",
                    "Stack Rate",
                ]
            ]
            .set_index("year")
        )

        st.bar_chart(
            chart,
            use_container_width=True,
        )

        usage_display = (
            season_usage
            .rename(
                columns={
                    "year": "Season",
                    "Team_Weeks": "Team-Weeks",
                    "Stack_Weeks": "Stack Weeks",
                }
            )
        )

        st.dataframe(
            usage_display,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Season":
                    st.column_config.NumberColumn(
                        "Season",
                        format="%d",
                    ),
                "Team-Weeks":
                    st.column_config.NumberColumn(
                        "Team-Weeks",
                        format="%d",
                    ),
                "Stack Weeks":
                    st.column_config.NumberColumn(
                        "Stack Weeks",
                        format="%d",
                    ),
                "Stack Rate":
                    st.column_config.NumberColumn(
                        "Stack Rate",
                        format="%.1f%%",
                    ),
            },
        )

    st.divider()


    # ========================================================
    # PAIR HISTORY
    # ========================================================

    st.subheader("🤝 QB/WR Stack Pair History")

    st.caption(
        "Historical results when each quarterback/receiver "
        "combination was started together as a stack."
    )

    if pairs.empty:

        st.info("Stack-pair history is unavailable.")

    else:

        min_starts_max = max(
            1,
            int(pairs["stack_weeks"].max()),
        )

        left, right = st.columns(
            [0.30, 0.70],
            gap="large",
        )

        with left:

            min_starts = st.slider(
                "Minimum stack starts",
                min_value=1,
                max_value=min_starts_max,
                value=min(
                    3,
                    min_starts_max,
                ),
                step=1,
            )

        pair_view = pairs[
            pairs["stack_weeks"]
            >= min_starts
        ].copy()

        pair_view = pair_view.sort_values(
            [
                "stack_weeks",
                "avg_team_score",
            ],
            ascending=[
                False,
                False,
            ],
        )

        pair_display = pd.DataFrame(
            {
                "QB":
                    pair_view["qb"],
                "WR":
                    pair_view["wr"],
                "NFL":
                    pair_view["qb_nfl_team"],
                "Starts":
                    pair_view["stack_weeks"],
                "Record":
                    (
                        pair_view["wins"]
                        .fillna(0)
                        .astype(int)
                        .astype(str)
                        + "-"
                        + (
                            pair_view["stack_weeks"]
                            - pair_view["wins"]
                        )
                        .fillna(0)
                        .astype(int)
                        .astype(str)
                    ),
                "Win Rate":
                    pair_view["win_rate"] * 100,
                "Avg Team Score":
                    pair_view["avg_team_score"],
                "Avg Margin":
                    pair_view["avg_margin"],
                "QB + WR Pts":
                    pair_view[
                        "avg_stack_player_points"
                    ],
                "Top Quartile":
                    pair_view[
                        "top_quartile_rate"
                    ] * 100,
            }
        )

        st.dataframe(
            pair_display,
            hide_index=True,
            use_container_width=True,
            height=520,
            column_config={
                "QB":
                    st.column_config.TextColumn(
                        "QB",
                        width="medium",
                    ),
                "WR":
                    st.column_config.TextColumn(
                        "WR",
                        width="medium",
                    ),
                "NFL":
                    st.column_config.TextColumn(
                        "NFL",
                        width="small",
                    ),
                "Starts":
                    st.column_config.NumberColumn(
                        "Starts",
                        format="%d",
                    ),
                "Record":
                    st.column_config.TextColumn(
                        "Record",
                        width="small",
                    ),
                "Win Rate":
                    st.column_config.NumberColumn(
                        "Win Rate",
                        format="%.1f%%",
                    ),
                "Avg Team Score":
                    st.column_config.NumberColumn(
                        "Avg Team Score",
                        format="%.2f",
                    ),
                "Avg Margin":
                    st.column_config.NumberColumn(
                        "Avg Margin",
                        format="%.2f",
                    ),
                "QB + WR Pts":
                    st.column_config.NumberColumn(
                        "QB + WR Pts",
                        format="%.2f",
                    ),
                "Top Quartile":
                    st.column_config.NumberColumn(
                        "Top Quartile",
                        format="%.1f%%",
                    ),
            },
        )

    st.divider()


    # ========================================================
    # FRANCHISE HISTORY
    # ========================================================

    st.subheader("🏛️ Franchise Stack History")

    st.caption(
        "Historical stack usage and results are consolidated "
        "under each franchise's canonical team name."
    )

    if by_franchise.empty:

        st.info("Franchise stack history is unavailable.")

    else:

        franchise_view = (
            by_franchise
            .sort_values(
                [
                    "stack_weeks",
                    "stack_avg_score",
                ],
                ascending=[
                    False,
                    False,
                ],
            )
            .copy()
        )

        franchise_display = pd.DataFrame(
            {
                "Franchise":
                    franchise_view[
                        "canonical_team"
                    ],
                "Stack Weeks":
                    franchise_view[
                        "stack_weeks"
                    ],
                "Usage Rate":
                    franchise_view[
                        "stack_rate"
                    ] * 100,
                "Record":
                    (
                        franchise_view[
                            "stack_wins"
                        ]
                        .fillna(0)
                        .astype(int)
                        .astype(str)
                        + "-"
                        + (
                            franchise_view[
                                "stack_weeks"
                            ]
                            - franchise_view[
                                "stack_wins"
                            ]
                        )
                        .fillna(0)
                        .astype(int)
                        .astype(str)
                    ),
                "Win Rate":
                    franchise_view[
                        "stack_win_rate"
                    ] * 100,
                "Avg Score":
                    franchise_view[
                        "stack_avg_score"
                    ],
                "Avg Margin":
                    franchise_view[
                        "stack_avg_margin"
                    ],
                "Top Quartile":
                    franchise_view[
                        "stack_top_quartile_rate"
                    ] * 100,
            }
        )

        st.dataframe(
            franchise_display,
            hide_index=True,
            use_container_width=True,
            height=520,
            column_config={
                "Franchise":
                    st.column_config.TextColumn(
                        "Franchise",
                        width="large",
                    ),
                "Stack Weeks":
                    st.column_config.NumberColumn(
                        "Stack Weeks",
                        format="%d",
                    ),
                "Usage Rate":
                    st.column_config.NumberColumn(
                        "Usage Rate",
                        format="%.1f%%",
                    ),
                "Record":
                    st.column_config.TextColumn(
                        "Record",
                        width="small",
                    ),
                "Win Rate":
                    st.column_config.NumberColumn(
                        "Win Rate",
                        format="%.1f%%",
                    ),
                "Avg Score":
                    st.column_config.NumberColumn(
                        "Avg Score",
                        format="%.2f",
                    ),
                "Avg Margin":
                    st.column_config.NumberColumn(
                        "Avg Margin",
                        format="%.2f",
                    ),
                "Top Quartile":
                    st.column_config.NumberColumn(
                        "Top Quartile",
                        format="%.1f%%",
                    ),
            },
        )

    st.divider()


    # ========================================================
    # NOTABLE HISTORICAL STACKS
    # ========================================================

    st.subheader("⭐ Notable Stack History")

    if not pairs.empty:

        eligible = pairs[
            pairs["stack_weeks"] >= 5
        ].copy()

        if not eligible.empty:

            most_used = (
                eligible
                .sort_values(
                    "stack_weeks",
                    ascending=False,
                )
                .iloc[0]
            )

            best_record = (
                eligible
                .sort_values(
                    [
                        "win_rate",
                        "stack_weeks",
                    ],
                    ascending=[
                        False,
                        False,
                    ],
                )
                .iloc[0]
            )

            highest_scoring = (
                eligible
                .sort_values(
                    "avg_team_score",
                    ascending=False,
                )
                .iloc[0]
            )

            best_combo = (
                eligible
                .sort_values(
                    "avg_stack_player_points",
                    ascending=False,
                )
                .iloc[0]
            )

            n1, n2, n3, n4 = st.columns(4)

            notable_cards = [
                (
                    n1,
                    "Most Used",
                    most_used,
                    f"{int(most_used['stack_weeks'])} starts",
                ),
                (
                    n2,
                    "Best Win Rate",
                    best_record,
                    pct(best_record["win_rate"]),
                ),
                (
                    n3,
                    "Highest Team Scoring",
                    highest_scoring,
                    f"{highest_scoring['avg_team_score']:.2f} pts/week",
                ),
                (
                    n4,
                    "Most Stack Points",
                    best_combo,
                    f"{best_combo['avg_stack_player_points']:.2f} QB+WR pts",
                ),
            ]

            for col, title, row, stat in notable_cards:

                with col:
                    st.markdown(f"**{title}**")
                    st.markdown(f"### {row['qb']}")
                    st.markdown("**+**")
                    st.markdown(f"### {row['wr']}")
                    st.caption(stat)

            st.caption(stat)

            st.caption(
                "Notable-stack cards require at least five "
                "historical starts together."
            )


    # ========================================================
    # METHODOLOGY
    # ========================================================

    with st.expander(
        "📖 Methodology & Caveats",
        expanded=False,
    ):

        st.markdown(
            """
            **What counts as a stack?**

            A team-week is classified as a QB/WR stack when the
            quarterback actually started in the Yahoo **QB lineup
            slot** and at least one starting NFL wide receiver played
            for that quarterback's NFL team.

            Wide receivers started at FLEX count. Bench players do not.

            **Why use the QB lineup slot?**

            Historical position eligibility can be strange. Players
            such as Taysom Hill or Kendall Hinton may carry quarterback
            eligibility even when they were not the fantasy team's
            actual starting QB. Using the lineup slot prevents those
            cases from creating false stacks.

            **What does the within-team comparison mean?**

            The apples-to-apples comparison only includes team-seasons
            where the same fantasy team had both stack and non-stack
            weeks. This reduces — but does not eliminate — differences
            caused by comparing completely different fantasy teams.

            **Does this prove stacking causes higher scores?**

            No. This is historical observational analysis. Better NFL
            offenses and elite players may naturally create both better
            fantasy scores and more attractive stacking opportunities.

            The strongest historical signal in this league is a higher
            **scoring ceiling**, not a demonstrated win-rate advantage.
            """
        )


# ============================================================
# BAD BEAT INDEX PAGE
# ============================================================



elif analysis_choice == "📝 Draft Trends":

    # ========================================================
    # DRAFT TRENDS
    # ========================================================

    st.header("📝 Draft Trends")
    st.caption(
        f"Draft-selection trends include completed drafts through "
        f"{LAST_COMPLETED_DRAFT_SEASON}. Finish/outcome comparisons use only "
        f"completed seasons through {LAST_COMPLETED_SEASON}."
    )

    draft_file = BASE_DIR / "data" / "drafts" / "all_drafts.csv"
    strategy_file = BASE_DIR / "data" / "drafts" / "draft_position_strategy.csv"
    standings_file = BASE_DIR / "data" / "all_standings.csv"
    championships_file = BASE_DIR / "data" / "playoffs" / "championships.csv"
    playoff_file = BASE_DIR / "data" / "playoffs" / "playoff_appearances.csv"

    required_paths = [
        draft_file,
        strategy_file,
        standings_file,
        championships_file,
        playoff_file,
    ]

    missing_paths = [str(path) for path in required_paths if not path.exists()]

    if missing_paths:
        st.error(
            "Draft Trends data is incomplete. Run the draft strategy builder and "
            "confirm the historical standings/playoff files are present."
        )
        with st.expander("Missing files"):
            for path in missing_paths:
                st.code(path)
        st.stop()

    drafts_trends = pd.read_csv(draft_file)
    strategy = pd.read_csv(strategy_file)
    standings_history = pd.read_csv(standings_file)
    championships_trends = pd.read_csv(championships_file)
    playoff_trends = pd.read_csv(playoff_file)

    for frame, cols in [
        (drafts_trends, ["year", "round", "pick_in_round", "overall_pick"]),
        (strategy, ["year"]),
        (standings_history, ["year", "rank", "points_for"]),
        (championships_trends, ["year"]),
        (playoff_trends, ["year"]),
    ]:
        numeric(frame, cols)

    if "team" in drafts_trends.columns:
        drafts_trends["team"] = drafts_trends["team"].apply(canonical_team)
    if "team" in strategy.columns:
        strategy["team"] = strategy["team"].apply(canonical_team)
    if "team" in standings_history.columns:
        standings_history["team"] = standings_history["team"].apply(canonical_team)
    if "team" in playoff_trends.columns:
        playoff_trends["team"] = playoff_trends["team"].apply(canonical_team)
    if "champion" in championships_trends.columns:
        championships_trends["champion"] = championships_trends["champion"].apply(canonical_team)
    if "runner_up" in championships_trends.columns:
        championships_trends["runner_up"] = championships_trends["runner_up"].apply(canonical_team)

    strategy_columns = [
        "first_qb_overall",
        "second_qb_overall",
        "first_rb_overall",
        "second_rb_overall",
        "third_rb_overall",
        "first_wr_overall",
        "second_wr_overall",
        "third_wr_overall",
        "first_te_overall",
        "first_k_overall",
        "first_def_overall",
    ]
    numeric(strategy, strategy_columns)

    # Selection-behavior analysis may include the latest completed draft.
    drafts_selection = drafts_trends[
        drafts_trends["year"] <= LAST_COMPLETED_DRAFT_SEASON
    ].copy()
    strategy_selection = strategy[
        strategy["year"] <= LAST_COMPLETED_DRAFT_SEASON
    ].copy()

    # Any comparison to standings/playoffs/championships must stop at the
    # latest fully completed season.
    drafts_outcomes = drafts_trends[
        drafts_trends["year"] <= LAST_COMPLETED_SEASON
    ].copy()
    strategy_outcomes = strategy[
        strategy["year"] <= LAST_COMPLETED_SEASON
    ].copy()

    completed_outcome_years = sorted(
        drafts_outcomes["year"].dropna().astype(int).unique().tolist()
    )

    def format_round_pick(value):
        if pd.isna(value):
            return "—"

        value = float(value)
        round_number = int((value - 1) // 12) + 1
        pick_in_round = value - (round_number - 1) * 12

        if abs(pick_in_round - round(pick_in_round)) < 0.05:
            pick_text = str(int(round(pick_in_round)))
        else:
            pick_text = f"{pick_in_round:.1f}"

        return f"R{round_number}, P{pick_text}"

    def format_strategy_difference(value):
        if pd.isna(value):
            return "—"
        return f"{value:+.1f} picks"

    # --------------------------------------------------------
    # SUB-NAVIGATION
    # --------------------------------------------------------

    draft_trend_view = st.segmented_control(
        "Draft analysis",
        options=[
            "Draft Slot Outcomes",
            "Strategy by Finish",
            "Franchise Tendencies",
        ],
        default="Draft Slot Outcomes",
        key="draft_trends_view",
    )

    st.divider()

    # ========================================================
    # DRAFT SLOT OUTCOMES
    # ========================================================

    if draft_trend_view == "Draft Slot Outcomes":

        st.subheader("🎯 Draft Slot Outcomes")
        st.caption(
            "Do earlier first-round draft slots actually lead to better finishes?"
        )

        first_round_positions = (
            drafts_outcomes[drafts_outcomes["round"] == 1][
                ["year", "team", "pick_in_round"]
            ]
            .copy()
            .rename(columns={"pick_in_round": "draft_position"})
        )

        champion_lookup = championships_trends[
            ["year", "champion", "runner_up"]
        ].copy()

        team_season_positions = first_round_positions.merge(
            champion_lookup,
            on="year",
            how="left",
        )

        team_season_positions["is_champion"] = (
            team_season_positions["team"] == team_season_positions["champion"]
        )
        team_season_positions["is_runner_up"] = (
            team_season_positions["team"] == team_season_positions["runner_up"]
        )

        playoff_lookup = playoff_trends[
            ["year", "team", "finish"]
        ].copy()

        team_season_positions = team_season_positions.merge(
            playoff_lookup,
            on=["year", "team"],
            how="left",
        )
        team_season_positions["made_playoffs"] = (
            team_season_positions["finish"].notna()
        )

        champion_draft_positions = (
            championships_trends[["year", "champion"]]
            .merge(
                first_round_positions,
                left_on=["year", "champion"],
                right_on=["year", "team"],
                how="left",
            )
            .drop(columns=["team"])
            .rename(
                columns={
                    "year": "Season",
                    "champion": "Champion",
                    "draft_position": "Draft Position",
                }
            )
            .sort_values("Season", ascending=False)
        )

        valid_champions = champion_draft_positions.dropna(
            subset=["Draft Position"]
        ).copy()

        if valid_champions.empty:
            st.info("Champion draft-position history is unavailable.")
        else:
            avg_champion_position = valid_champions["Draft Position"].mean()
            earliest_champion = valid_champions.sort_values(
                "Draft Position"
            ).iloc[0]
            latest_champion = valid_champions.sort_values(
                "Draft Position", ascending=False
            ).iloc[0]

            c1, c2, c3 = st.columns(3)
            c1.metric(
                "Average Champion Slot",
                f"{avg_champion_position:.1f}",
            )
            c2.metric(
                "Earliest-Drafting Champion",
                f"Pick {int(earliest_champion['Draft Position'])}",
                f"{earliest_champion['Champion']} ({int(earliest_champion['Season'])})",
            )
            c3.metric(
                "Latest-Drafting Champion",
                f"Pick {int(latest_champion['Draft Position'])}",
                f"{latest_champion['Champion']} ({int(latest_champion['Season'])})",
            )

        champion_avg = team_season_positions.loc[
            team_season_positions["is_champion"], "draft_position"
        ].mean()
        runner_up_avg = team_season_positions.loc[
            team_season_positions["is_runner_up"], "draft_position"
        ].mean()
        playoff_avg = team_season_positions.loc[
            team_season_positions["made_playoffs"], "draft_position"
        ].mean()
        missed_avg = team_season_positions.loc[
            ~team_season_positions["made_playoffs"], "draft_position"
        ].mean()

        st.markdown("### Average Draft Slot by Finish")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Champions", f"{champion_avg:.1f}")
        c2.metric("Runner-Ups", f"{runner_up_avg:.1f}")
        c3.metric("Playoff Teams", f"{playoff_avg:.1f}")
        c4.metric("Missed Playoffs", f"{missed_avg:.1f}")
        st.caption("Lower numbers mean the franchise drafted earlier.")

        slot_stats = (
            team_season_positions
            .groupby("draft_position")
            .agg(
                Seasons=("year", "size"),
                Championships=("is_champion", "sum"),
                Runner_Ups=("is_runner_up", "sum"),
                Playoff_Appearances=("made_playoffs", "sum"),
            )
            .reset_index()
        )

        slot_stats["Finals"] = (
            slot_stats["Runner_Ups"] + slot_stats["Championships"]
        )
        slot_stats["Playoff %"] = (
            slot_stats["Playoff_Appearances"]
            / slot_stats["Seasons"]
            * 100
        ).round(1)
        slot_stats["Championship %"] = (
            slot_stats["Championships"]
            / slot_stats["Seasons"]
            * 100
        ).round(1)

        slot_stats = slot_stats.rename(
            columns={
                "draft_position": "Draft Position",
                "Playoff_Appearances": "Playoff Appearances",
            }
        )

        st.markdown("### Results by Draft Slot")
        st.dataframe(
            slot_stats[
                [
                    "Draft Position",
                    "Seasons",
                    "Championships",
                    "Finals",
                    "Playoff Appearances",
                    "Playoff %",
                    "Championship %",
                ]
            ],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Draft Position": st.column_config.NumberColumn(format="%d"),
                "Seasons": st.column_config.NumberColumn(format="%d"),
                "Championships": st.column_config.NumberColumn(format="%d"),
                "Finals": st.column_config.NumberColumn(format="%d"),
                "Playoff Appearances": st.column_config.NumberColumn(format="%d"),
                "Playoff %": st.column_config.NumberColumn(format="%.1f%%"),
                "Championship %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

        chart = slot_stats.set_index("Draft Position")[["Championships"]]
        st.bar_chart(chart, y="Championships", use_container_width=True)

        if not slot_stats.empty:
            best_slot = (
                slot_stats
                .sort_values(
                    ["Championships", "Playoff %"],
                    ascending=[False, False],
                )
                .iloc[0]
            )
            st.info(
                f"Across {len(completed_outcome_years)} completed seasons, slot "
                f"#{int(best_slot['Draft Position'])} has produced the most "
                f"championships ({int(best_slot['Championships'])}) and a "
                f"{best_slot['Playoff %']:.1f}% playoff rate."
            )

        with st.expander("Champion draft slots by season"):
            st.dataframe(
                champion_draft_positions,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Season": st.column_config.NumberColumn(format="%d"),
                    "Draft Position": st.column_config.NumberColumn(format="%d"),
                },
            )

    # ========================================================
    # STRATEGY BY FINISH
    # ========================================================

    elif draft_trend_view == "Strategy by Finish":

        st.subheader("🧠 Draft Strategy by Finish")
        st.caption(
            "Compare when teams addressed each roster-building milestone. "
            "Lower picks mean that position was addressed earlier."
        )

        strategy_view_mode = st.radio(
            "Show draft strategy as",
            ["Overall Pick", "Round & Pick"],
            horizontal=True,
            key="draft_strategy_view_mode_analysis",
        )

        strategy_years = set(
            strategy_outcomes["year"].dropna().astype(int).unique()
        )

        outcome = strategy_outcomes.copy()

        champion_lookup_strategy = championships_trends[
            ["year", "champion", "runner_up"]
        ].copy()

        outcome = outcome.merge(
            champion_lookup_strategy,
            on="year",
            how="left",
        )

        outcome["is_champion"] = outcome["team"] == outcome["champion"]
        outcome["is_runner_up"] = outcome["team"] == outcome["runner_up"]

        playoff_keys = (
            playoff_trends[
                playoff_trends["year"].isin(strategy_years)
            ][["year", "team"]]
            .drop_duplicates()
            .assign(made_playoffs=True)
        )

        outcome = outcome.merge(
            playoff_keys,
            on=["year", "team"],
            how="left",
        )
        outcome["made_playoffs"] = (
            outcome["made_playoffs"].fillna(False).astype(bool)
        )

        standings_completed = standings_history[
            standings_history["year"].isin(strategy_years)
        ].copy()

        def parse_standings_record(record):
            try:
                parts = [int(x) for x in str(record).strip().split("-")]
                if len(parts) == 2:
                    wins, losses = parts
                    ties = 0
                elif len(parts) == 3:
                    wins, losses, ties = parts
                else:
                    raise ValueError

                games = wins + losses + ties
                win_pct = (wins + 0.5 * ties) / games if games else pd.NA

                return pd.Series(
                    {
                        "wins": wins,
                        "losses": losses,
                        "ties": ties,
                        "win_pct": win_pct,
                    }
                )
            except Exception:
                return pd.Series(
                    {
                        "wins": pd.NA,
                        "losses": pd.NA,
                        "ties": pd.NA,
                        "win_pct": pd.NA,
                    }
                )

        record_parts = standings_completed["record"].apply(
            parse_standings_record
        )
        standings_completed = pd.concat(
            [standings_completed, record_parts],
            axis=1,
        )

        cellar_rows = (
            standings_completed
            .dropna(subset=["win_pct", "points_for"])
            .sort_values(
                ["year", "win_pct", "points_for"],
                ascending=[True, True, True],
            )
            .groupby("year", as_index=False)
            .first()[
                ["year", "team", "record", "points_for", "win_pct"]
            ]
            .rename(
                columns={
                    "team": "cellar_boy",
                    "record": "cellar_record",
                    "points_for": "cellar_points_for",
                    "win_pct": "cellar_win_pct",
                }
            )
        )

        outcome = outcome.merge(
            cellar_rows,
            on="year",
            how="left",
        )
        outcome["is_cellar_boy"] = (
            outcome["team"] == outcome["cellar_boy"]
        )

        main_metrics = {
            "first_qb_overall": "1st QB",
            "second_qb_overall": "2nd QB",
            "first_rb_overall": "1st RB",
            "second_rb_overall": "2nd RB",
            "third_rb_overall": "3rd RB",
            "first_wr_overall": "1st WR",
            "second_wr_overall": "2nd WR",
            "third_wr_overall": "3rd WR",
            "first_te_overall": "1st TE",
        }

        def strategy_group_row(label, frame):
            row = {
                "Finish": label,
                "Team-Seasons": len(frame),
            }
            for source, display in main_metrics.items():
                row[display] = frame[source].mean()
            return row

        strategy_finish_table = pd.DataFrame(
            [
                strategy_group_row(
                    "Champions",
                    outcome[outcome["is_champion"]],
                ),
                strategy_group_row(
                    "Runner-Ups",
                    outcome[outcome["is_runner_up"]],
                ),
                strategy_group_row(
                    "Playoff Teams",
                    outcome[outcome["made_playoffs"]],
                ),
                strategy_group_row(
                    "Non-Playoff Teams",
                    outcome[~outcome["made_playoffs"]],
                ),
                strategy_group_row(
                    "Cellar Boy",
                    outcome[outcome["is_cellar_boy"]],
                ),
                strategy_group_row(
                    "League Average",
                    outcome,
                ),
            ]
        )

        for col in main_metrics.values():
            strategy_finish_table[col] = (
                strategy_finish_table[col].round(1)
            )

        display = strategy_finish_table.copy()

        if strategy_view_mode == "Round & Pick":
            for col in main_metrics.values():
                display[col] = display[col].apply(format_round_pick)
            column_config = {
                "Team-Seasons": st.column_config.NumberColumn(format="%d")
            }
        else:
            column_config = {
                "Team-Seasons": st.column_config.NumberColumn(format="%d"),
                **{
                    col: st.column_config.NumberColumn(format="%.1f")
                    for col in main_metrics.values()
                },
            }

        st.markdown("### Average Position-Building Picks")
        st.dataframe(
            display,
            hide_index=True,
            use_container_width=True,
            column_config=column_config,
        )

        st.markdown("### Kicker & Defense Strategy")

        special_rows = []
        for label, frame in [
            ("Champions", outcome[outcome["is_champion"]]),
            ("Runner-Ups", outcome[outcome["is_runner_up"]]),
            ("Playoff Teams", outcome[outcome["made_playoffs"]]),
            ("Non-Playoff Teams", outcome[~outcome["made_playoffs"]]),
            ("Cellar Boy", outcome[outcome["is_cellar_boy"]]),
            ("League Average", outcome),
        ]:
            special_rows.append(
                {
                    "Finish": label,
                    "1st K": frame["first_k_overall"].mean(),
                    "1st DEF": frame["first_def_overall"].mean(),
                }
            )

        special_table = pd.DataFrame(special_rows)
        special_table[["1st K", "1st DEF"]] = (
            special_table[["1st K", "1st DEF"]].round(1)
        )

        if strategy_view_mode == "Round & Pick":
            special_display = special_table.copy()
            for col in ["1st K", "1st DEF"]:
                special_display[col] = special_display[col].apply(
                    format_round_pick
                )
            special_config = {}
        else:
            special_display = special_table
            special_config = {
                "1st K": st.column_config.NumberColumn(format="%.1f"),
                "1st DEF": st.column_config.NumberColumn(format="%.1f"),
            }

        st.dataframe(
            special_display,
            hide_index=True,
            use_container_width=True,
            column_config=special_config,
        )

        with st.expander("Cellar Boy by Season"):
            cellar_display = (
                cellar_rows
                .rename(
                    columns={
                        "year": "Season",
                        "cellar_boy": "Cellar Boy",
                        "cellar_record": "Record",
                        "cellar_points_for": "Points For",
                        "cellar_win_pct": "Win %",
                    }
                )
                .sort_values("Season", ascending=False)
            )

            st.dataframe(
                cellar_display,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Season": st.column_config.NumberColumn(format="%d"),
                    "Points For": st.column_config.NumberColumn(format="%.2f"),
                    "Win %": st.column_config.NumberColumn(format="%.3f"),
                },
            )

    # ========================================================
    # FRANCHISE TENDENCIES
    # ========================================================

    else:

        st.subheader("🏗️ Franchise Draft Tendencies")
        st.caption(
            "How each franchise historically built its roster, measured by "
            "the average overall pick used on each positional milestone."
        )

        strategy_view_mode = st.radio(
            "Show draft strategy as",
            ["Overall Pick", "Round & Pick"],
            horizontal=True,
            key="draft_tendencies_view_mode_analysis",
        )

        strategy_teams = sorted(
            strategy_selection["team"].dropna().unique()
        )

        strategy_team = st.selectbox(
            "Choose a franchise",
            strategy_teams,
            key="analysis_strategy_franchise",
        )

        franchise_strategy = (
            strategy_selection[
                strategy_selection["team"] == strategy_team
            ]
            .copy()
            .sort_values("year")
        )

        comparison_metrics = {
            "first_qb_overall": "1st QB",
            "second_qb_overall": "2nd QB",
            "first_rb_overall": "1st RB",
            "second_rb_overall": "2nd RB",
            "third_rb_overall": "3rd RB",
            "first_wr_overall": "1st WR",
            "second_wr_overall": "2nd WR",
            "third_wr_overall": "3rd WR",
            "first_te_overall": "1st TE",
            "first_k_overall": "1st K",
            "first_def_overall": "1st DEF",
        }

        comparison_rows = []
        for source, display_name in comparison_metrics.items():
            team_avg = franchise_strategy[source].mean()
            league_avg = strategy_selection[source].mean()
            comparison_rows.append(
                {
                    "Position Slot": display_name,
                    "Franchise Avg Pick": team_avg,
                    "League Avg Pick": league_avg,
                    "Difference": team_avg - league_avg,
                }
            )

        franchise_comparison = pd.DataFrame(comparison_rows)
        franchise_comparison[
            ["Franchise Avg Pick", "League Avg Pick", "Difference"]
        ] = franchise_comparison[
            ["Franchise Avg Pick", "League Avg Pick", "Difference"]
        ].round(1)

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Drafts Analyzed",
            franchise_strategy["year"].nunique(),
        )

        first_qb_avg = franchise_strategy["first_qb_overall"].mean()
        first_rb_avg = franchise_strategy["first_rb_overall"].mean()

        c2.metric(
            "Average 1st QB Pick",
            (
                format_round_pick(first_qb_avg)
                if strategy_view_mode == "Round & Pick"
                else (f"{first_qb_avg:.1f}" if pd.notna(first_qb_avg) else "—")
            ),
        )
        c3.metric(
            "Average 1st RB Pick",
            (
                format_round_pick(first_rb_avg)
                if strategy_view_mode == "Round & Pick"
                else (f"{first_rb_avg:.1f}" if pd.notna(first_rb_avg) else "—")
            ),
        )

        st.markdown("### Franchise vs. League")

        comparison_display = franchise_comparison.copy()

        if strategy_view_mode == "Round & Pick":
            for col in ["Franchise Avg Pick", "League Avg Pick"]:
                comparison_display[col] = comparison_display[col].apply(
                    format_round_pick
                )
            comparison_display["Difference"] = comparison_display[
                "Difference"
            ].apply(format_strategy_difference)
            comparison_config = {}
        else:
            comparison_config = {
                "Franchise Avg Pick": st.column_config.NumberColumn(format="%.1f"),
                "League Avg Pick": st.column_config.NumberColumn(format="%.1f"),
                "Difference": st.column_config.NumberColumn(
                    format="%+.1f",
                    help=(
                        "Negative means this franchise drafts the position "
                        "earlier than league average; positive means later."
                    ),
                ),
            }

        st.dataframe(
            comparison_display,
            hide_index=True,
            use_container_width=True,
            column_config=comparison_config,
        )

        st.caption(
            "Negative differences mean the franchise addressed that position "
            "earlier than league average. Positive differences mean it waited longer."
        )

        st.markdown("### Year-by-Year Draft Strategy")

        year_columns = {
            "year": "Season",
            **comparison_metrics,
        }

        year_by_year = (
            franchise_strategy[list(year_columns.keys())]
            .rename(columns=year_columns)
            .sort_values("Season", ascending=False)
        )

        year_by_year_display = year_by_year.copy()
        if strategy_view_mode == "Round & Pick":
            for col in comparison_metrics.values():
                year_by_year_display[col] = year_by_year_display[col].apply(
                    format_round_pick
                )
            year_config = {
                "Season": st.column_config.NumberColumn(format="%d")
            }
        else:
            year_config = {
                "Season": st.column_config.NumberColumn(format="%d"),
                **{
                    col: st.column_config.NumberColumn(format="%.1f")
                    for col in comparison_metrics.values()
                },
            }

        st.dataframe(
            year_by_year_display,
            hide_index=True,
            use_container_width=True,
            column_config=year_config,
        )

        with st.expander("All-Franchise Strategy Averages"):
            franchise_average_table = (
                strategy
                .groupby("team")[list(comparison_metrics.keys())]
                .mean()
                .rename(columns=comparison_metrics)
                .round(1)
                .reset_index()
                .rename(columns={"team": "Franchise"})
                .sort_values("Franchise")
            )

            franchise_average_display = franchise_average_table.copy()

            if strategy_view_mode == "Round & Pick":
                for col in comparison_metrics.values():
                    franchise_average_display[col] = (
                        franchise_average_display[col].apply(format_round_pick)
                    )
                franchise_average_config = {}
            else:
                franchise_average_config = {
                    display_name: st.column_config.NumberColumn(format="%.1f")
                    for display_name in comparison_metrics.values()
                }

            st.dataframe(
                franchise_average_display,
                hide_index=True,
                use_container_width=True,
                column_config=franchise_average_config,
            )

    with st.expander("Methodology & scope"):
        st.markdown(
            """
            **Draft Slot Outcomes**
            uses each franchise's first-round draft position from completed
            drafts and compares that slot with playoff, finals, and championship
            outcomes from the same season.

            **Strategy by Finish**
            measures the overall pick where a team first addressed QB, RB, WR,
            TE, K and DEF roster-building milestones, then compares champions,
            runner-ups, playoff teams, non-playoff teams, and the season's
            lowest regular-season finisher.

            **Franchise Tendencies**
            compares each franchise's historical position-building timing with
            the league average.

            These are descriptive historical patterns, not proof that drafting
            from a particular slot or selecting a position at a particular time
            causes better results.
            """
        )


elif analysis_choice == "📈 Draft Value":

    # ========================================================
    # DRAFT VALUE
    # ========================================================

    analysis_dir = Path("data/analysis")

    picks = pd.read_csv(
        analysis_dir / "draft_value_picks.csv"
    )

    franchise = pd.read_csv(
        analysis_dir / "draft_value_franchise.csv"
    )

    team_season = pd.read_csv(
        analysis_dir / "draft_value_team_season.csv"
    )

    late_round = pd.read_csv(
        analysis_dir / "draft_value_late_round_steals.csv"
    )

    first_round = pd.read_csv(
        analysis_dir / "draft_value_first_round.csv"
    )


    # ========================================================
    # HERO / VERDICT
    # ========================================================

    st.subheader("📈 Draft Value")

    st.markdown(
        """
        **Who actually gets the most out of the draft?**

        Draft Value compares each non-keeper QB, RB, WR and TE
        selection with what that draft capital historically
        produced. Player outcomes are ranked against others at
        the same position and in the same season, allowing
        different positions and scoring environments to be
        compared on one scale.
        """
    )


    # ========================================================
    # LEAGUE LEADER
    # ========================================================

    leader = (
        franchise
        .sort_values(
            "draft_value_rank"
        )
        .iloc[0]
    )

    best_class = (
        team_season
        .sort_values(
            "avg_draft_value",
            ascending=False,
        )
        .iloc[0]
    )

    biggest_steal = (
        picks[
            picks["draft_value_eligible"]
            & picks["draft_value"].notna()
        ]
        .sort_values(
            "draft_value",
            ascending=False,
        )
        .iloc[0]
    )

    biggest_bust = (
        picks[
            picks["draft_value_eligible"]
            & picks["draft_value"].notna()
        ]
        .sort_values(
            "draft_value",
            ascending=True,
        )
        .iloc[0]
    )


    st.markdown(
        f"""
        ### League Verdict

        **{leader['canonical_team']}** has produced the best
        overall draft results in league history, averaging
        **{leader['avg_draft_value']:+.1f} Draft Value per rated pick**.

        The best individual draft class belongs to
        **{best_class['canonical_team']} ({int(best_class['year'])})**,
        which averaged **{best_class['avg_draft_value']:+.1f}**
        per selection.
        """
    )


    # ========================================================
    # HEADLINE METRICS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Best Drafting Franchise",
        leader["canonical_team"],
        f"{leader['avg_draft_value']:+.1f} / pick",
    )

    c2.metric(
        "Best Draft Class",
        f"{int(best_class['year'])} {best_class['canonical_team']}",
        f"{best_class['avg_draft_value']:+.1f} / pick",
    )

    c3.metric(
        "Biggest Steal",
        biggest_steal["player"],
        f"{biggest_steal['draft_value']:+.1f}",
    )

    c4.metric(
        "Biggest Bust",
        biggest_bust["player"],
        f"{biggest_bust['draft_value']:+.1f}",
    )


    st.divider()


    # ========================================================
    # WHAT DRAFT VALUE MEANS
    # ========================================================

    st.subheader("What Does Draft Value Mean?")

    st.markdown(
        """
        Every player is first graded by where his regular-season
        production ranked among players at the **same position
        that season**.

        We then compare that positional percentile with what
        players selected around the same overall pick historically
        produced.

        **Draft Value = Actual Positional Percentile − Expected Positional Percentile**

        So a **+30 Draft Value** means the player finished
        30 positional-percentile points better than historical
        expectation for that draft capital.

        A negative value means the pick underperformed expectation.
        """
    )

    explanation_example = biggest_steal

    st.info(
        f"Example: {explanation_example['player']} "
        f"({int(explanation_example['year'])}, "
        f"pick {int(explanation_example['overall_pick'])}) "
        f"produced a {explanation_example['position_percentile']:.1f}th-"
        f"percentile {explanation_example['position']} season. "
        f"That draft capital historically produced about a "
        f"{explanation_example['expected_position_percentile']:.1f}th-"
        f"percentile outcome, giving the pick "
        f"{explanation_example['draft_value']:+.1f} Draft Value."
    )


    st.divider()


    # ========================================================
    # FRANCHISE RANKINGS
    # ========================================================

    st.subheader("🏆 All-Time Drafting Rankings")

    st.caption(
        "Primary ranking is average Draft Value per rated "
        "non-keeper QB/RB/WR/TE selection."
    )

    franchise_display = (
        franchise
        .sort_values(
            "draft_value_rank"
        )
        .copy()
    )

    franchise_display["Rank"] = (
        franchise_display[
            "draft_value_rank"
        ].astype(int)
    )

    franchise_display["Team"] = (
        franchise_display[
            "canonical_team"
        ]
    )

    franchise_display["Rated Picks"] = (
        franchise_display[
            "rated_picks"
        ].astype(int)
    )

    franchise_display["Avg Draft Value"] = (
        franchise_display[
            "avg_draft_value"
        ].round(1)
    )

    franchise_display["Median"] = (
        franchise_display[
            "median_draft_value"
        ].round(1)
    )

    franchise_display["Steals"] = (
        franchise_display[
            "steals"
        ].astype(int)
    )

    franchise_display["Busts"] = (
        franchise_display[
            "busts"
        ].astype(int)
    )

    franchise_display["Steal Rate"] = (
        franchise_display[
            "steal_rate"
        ] * 100
    ).round(1).astype(str) + "%"

    franchise_display["Bust Rate"] = (
        franchise_display[
            "bust_rate"
        ] * 100
    ).round(1).astype(str) + "%"

    st.dataframe(
        franchise_display[
            [
                "Rank",
                "Team",
                "Rated Picks",
                "Avg Draft Value",
                "Median",
                "Steals",
                "Busts",
                "Steal Rate",
                "Bust Rate",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    st.divider()


    # ========================================================
    # BIGGEST STEALS
    # ========================================================

    st.subheader("💎 Biggest Draft Steals")

    st.caption(
        "The selections that most dramatically outperformed "
        "historical expectation for their draft capital."
    )

    steals = (
        picks[
            picks["draft_value_eligible"]
            & picks["draft_value"].notna()
        ]
        .sort_values(
            "draft_value",
            ascending=False,
        )
        .head(20)
        .copy()
    )

    steals["Year"] = steals["year"].astype(int)
    steals["Player"] = steals["player"]
    steals["Team"] = steals["canonical_team"]
    steals["Pos"] = steals["position"]
    steals["Round"] = steals["round"].astype(int)
    steals["Pick"] = steals["overall_pick"].astype(int)

    steals["Actual %ile"] = (
        steals["position_percentile"]
        .round(1)
    )

    steals["Expected %ile"] = (
        steals[
            "expected_position_percentile"
        ]
        .round(1)
    )

    steals["Draft Value"] = (
        steals["draft_value"]
        .round(1)
    )

    st.dataframe(
        steals[
            [
                "Year",
                "Player",
                "Team",
                "Pos",
                "Round",
                "Pick",
                "Actual %ile",
                "Expected %ile",
                "Draft Value",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    st.divider()


    # ========================================================
    # BIGGEST BUSTS
    # ========================================================

    st.subheader("💥 Biggest Draft Busts")

    st.caption(
        "Outcome-based busts: injuries, holdouts and other "
        "lost seasons count because this measures the result "
        "of the draft pick, not whether the decision was "
        "reasonable on draft day."
    )

    busts = (
        picks[
            picks["draft_value_eligible"]
            & picks["draft_value"].notna()
        ]
        .sort_values(
            "draft_value",
            ascending=True,
        )
        .head(20)
        .copy()
    )

    busts["Year"] = busts["year"].astype(int)
    busts["Player"] = busts["player"]
    busts["Team"] = busts["canonical_team"]
    busts["Pos"] = busts["position"]
    busts["Round"] = busts["round"].astype(int)
    busts["Pick"] = busts["overall_pick"].astype(int)

    busts["Actual %ile"] = (
        busts["position_percentile"]
        .round(1)
    )

    busts["Expected %ile"] = (
        busts[
            "expected_position_percentile"
        ]
        .round(1)
    )

    busts["Draft Value"] = (
        busts["draft_value"]
        .round(1)
    )

    st.dataframe(
        busts[
            [
                "Year",
                "Player",
                "Team",
                "Pos",
                "Round",
                "Pick",
                "Actual %ile",
                "Expected %ile",
                "Draft Value",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    st.divider()


    # ========================================================
    # DRAFT CLASS HISTORY
    # ========================================================

    st.subheader("📚 Best Draft Classes")

    best_classes = (
        team_season
        .sort_values(
            "avg_draft_value",
            ascending=False,
        )
        .head(15)
        .copy()
    )

    best_classes["Year"] = (
        best_classes["year"]
        .astype(int)
    )

    best_classes["Team"] = (
        best_classes[
            "canonical_team"
        ]
    )

    best_classes["Picks"] = (
        best_classes[
            "rated_picks"
        ].astype(int)
    )

    best_classes["Avg Value"] = (
        best_classes[
            "avg_draft_value"
        ].round(1)
    )

    best_classes["Steals"] = (
        best_classes["steals"]
        .astype(int)
    )

    best_classes["Busts"] = (
        best_classes["busts"]
        .astype(int)
    )

    best_classes["Net Hits"] = (
        best_classes["net_hits"]
        .astype(int)
    )

    st.dataframe(
        best_classes[
            [
                "Year",
                "Team",
                "Picks",
                "Avg Value",
                "Steals",
                "Busts",
                "Net Hits",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    st.subheader("🗑️ Worst Draft Classes")

    worst_classes = (
        team_season
        .sort_values(
            "avg_draft_value",
            ascending=True,
        )
        .head(15)
        .copy()
    )

    worst_classes["Year"] = (
        worst_classes["year"]
        .astype(int)
    )

    worst_classes["Team"] = (
        worst_classes[
            "canonical_team"
        ]
    )

    worst_classes["Picks"] = (
        worst_classes[
            "rated_picks"
        ].astype(int)
    )

    worst_classes["Avg Value"] = (
        worst_classes[
            "avg_draft_value"
        ].round(1)
    )

    worst_classes["Steals"] = (
        worst_classes["steals"]
        .astype(int)
    )

    worst_classes["Busts"] = (
        worst_classes["busts"]
        .astype(int)
    )

    worst_classes["Net Hits"] = (
        worst_classes["net_hits"]
        .astype(int)
    )

    st.dataframe(
        worst_classes[
            [
                "Year",
                "Team",
                "Picks",
                "Avg Value",
                "Steals",
                "Busts",
                "Net Hits",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    st.divider()


    # ========================================================
    # LATE ROUND LOTTERY TICKETS
    # ========================================================

    st.subheader("🎯 Late-Round Lottery Tickets")

    st.caption(
        "Best selections from Round 8 or later."
    )

    late = (
        late_round[
            late_round[
                "draft_value"
            ].notna()
        ]
        .sort_values(
            "draft_value",
            ascending=False,
        )
        .head(15)
        .copy()
    )

    late["Year"] = late["year"].astype(int)
    late["Player"] = late["player"]
    late["Team"] = late["canonical_team"]
    late["Round"] = late["round"].astype(int)
    late["Pick"] = late["overall_pick"].astype(int)
    late["Value"] = late["draft_value"].round(1)

    st.dataframe(
        late[
            [
                "Year",
                "Player",
                "Team",
                "Round",
                "Pick",
                "Value",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    st.divider()


    # ========================================================
    # FIRST ROUND GRAVEYARD
    # ========================================================

    st.subheader("⚰️ First-Round Graveyard")

    st.caption(
        "The most expensive first-round misses in league history."
    )

    first = (
        first_round[
            first_round[
                "draft_value"
            ].notna()
        ]
        .sort_values(
            "draft_value",
            ascending=True,
        )
        .head(15)
        .copy()
    )

    first["Year"] = first["year"].astype(int)
    first["Player"] = first["player"]
    first["Team"] = first["canonical_team"]
    first["Pick"] = first["overall_pick"].astype(int)
    first["Value"] = first["draft_value"].round(1)

    st.dataframe(
        first[
            [
                "Year",
                "Player",
                "Team",
                "Pick",
                "Value",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    st.divider()


    # ========================================================
    # METHODOLOGY
    # ========================================================

    with st.expander(
        "How Draft Value is calculated"
    ):

        st.markdown(
            """
            **Eligible picks**

            Primary Draft Value includes non-keeper selections
            at QB, RB, WR and TE. Kickers and defenses remain
            in the underlying draft history but are excluded
            from the primary rankings.

            **Step 1 — Positional outcome**

            Each player's regular-season fantasy production is
            ranked against players at the same position in the
            same season and converted to a 0–100 percentile.

            **Step 2 — Draft-capital expectation**

            For each pick, historical non-keeper skill-position
            selections made within ±12 overall picks in other
            seasons establish the expected positional percentile.

            **Step 3 — Draft Value**

            `Draft Value = Actual Positional Percentile − Expected Positional Percentile`

            **Classification**

            - Elite Steal: +40 or better
            - Steal: +25 to +39.9
            - Near Expectation: between -25 and +25
            - Bust: -25 to -39.9
            - Major Bust: -40 or worse

            **Important caveat**

            Draft Value measures **outcomes**, not the quality of
            the decision using only information available on draft
            day. Injuries, holdouts and other lost seasons therefore
            count as poor outcomes.

            Keepers are excluded because keeper cost and selection
            mechanics are fundamentally different from open-draft
            capital.
            """
        )



# ============================================================
# WAIVER VALUE PAGE
# ============================================================


elif analysis_choice == "🔄 Waiver Value":

    analysis_dir = Path("data/analysis")

    acquisition_path = (
        analysis_dir
        / "waiver_value_acquisitions.csv"
    )

    franchise_path = (
        analysis_dir
        / "waiver_value_franchise.csv"
    )

    season_path = (
        analysis_dir
        / "waiver_value_team_season.csv"
    )

    hof_path = (
        analysis_dir
        / "waiver_value_hall_of_fame.csv"
    )

    required_files = [
        acquisition_path,
        franchise_path,
        season_path,
        hof_path,
    ]

    missing_files = [
        str(path)
        for path in required_files
        if not path.exists()
    ]

    if missing_files:

        st.error(
            "Waiver Value analysis files are missing. "
            "Run `python build_waiver_value_analysis.py` "
            "before loading this analysis."
        )

        with st.expander("Missing files"):
            for path in missing_files:
                st.code(path)

        st.stop()


    # ========================================================
    # LOAD DATA
    # ========================================================

    waiver = pd.read_csv(
        acquisition_path
    )

    franchise = pd.read_csv(
        franchise_path
    )

    team_season = pd.read_csv(
        season_path
    )

    hall = pd.read_csv(
        hof_path
    )


    # ========================================================
    # HERO
    # ========================================================

    st.subheader("🔄 Waiver Value")

    st.markdown(
        """
        **Who has been best at finding useful players after the draft?**

        Waiver Value grades regular-season waiver and free-agent
        acquisitions at QB, RB, WR and TE based on what those players
        produced **after they were acquired and while they remained on
        that manager's roster**.

        The score rewards both weekly production and sustained value,
        while comparing players with waiver acquisitions at the same
        position in the same season.
        """
    )

    st.info(
        "2018 is excluded because complete transaction history is "
        "not available for that season. It is not treated as a "
        "zero-activity season."
    )


    # ========================================================
    # OFFICIAL LEADER
    # ========================================================

    official = (
        franchise[
            franchise[
                "official_ranking_eligible"
            ].astype(str).str.lower().eq("true")
        ]
        .sort_values(
            "official_rank"
        )
        .copy()
    )

    leader = official.iloc[0]

    elite_pick = (
        hall
        .sort_values(
            [
                "waiver_score",
                "scoring_production_points",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .iloc[0]
    )

    st.markdown(
        f"""
        ### League Verdict

        **{leader['team']}** has produced the best all-time
        waiver results among franchises with at least 20 meaningful
        acquisitions, averaging **{leader['avg_waiver_value']:+.1f}
        Waiver Value per meaningful pickup**.

        The highest-rated individual acquisition is
        **{elite_pick['player']} ({int(elite_pick['year'])},
        {elite_pick['team_canonical']})**, with a
        **{elite_pick['waiver_score']:.1f} Waiver Score**.
        """
    )


    # ========================================================
    # HEADLINE METRICS
    # ========================================================

    meaningful_count = int(
        waiver[
            "meaningful_acquisition"
        ]
        .astype(str)
        .str.lower()
        .eq("true")
        .sum()
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Best Waiver Franchise",
        leader["team"],
        f"{leader['avg_waiver_value']:+.1f} avg value",
    )

    c2.metric(
        "Meaningful Pickups",
        f"{meaningful_count:,}",
    )

    c3.metric(
        "Eligible Acquisitions",
        f"{len(waiver):,}",
    )

    c4.metric(
        "Seasons With Data",
        f"{waiver['year'].nunique()}",
    )


    st.divider()


    # ========================================================
    # WHAT WAIVER VALUE MEANS
    # ========================================================

    st.subheader("What Does Waiver Value Mean?")

    st.markdown(
        """
        Every eligible acquisition receives two percentile scores
        against **same-position waiver/free-agent acquisitions from
        that season**:

        - **Rate Score** — how strong the player's production was
          per scoring opportunity week.
        - **Sustained Score** — how much total production the player
          delivered while owned.

        Those are combined as:

        **Waiver Score = 35% Rate Score + 65% Sustained Score**

        The 0–100 Waiver Score is then centered around 50:

        **Waiver Value = Waiver Score − 50**

        That means positive Waiver Value represents an acquisition
        that outperformed the middle of its position-season waiver
        market, while negative value represents a weaker outcome.
        """
    )

    example = (
        hall
        .sort_values(
            "waiver_score",
            ascending=False,
        )
        .iloc[0]
    )

    st.info(
        f"Example: {example['player']} "
        f"({int(example['year'])}, "
        f"{example['player_position']}) earned a "
        f"{example['waiver_score']:.1f} Waiver Score, "
        f"or {example['waiver_value']:+.1f} Waiver Value."
    )


    st.divider()


    # ========================================================
    # ALL-TIME FRANCHISE RANKINGS
    # ========================================================

    st.subheader("🏆 Best Waiver Managers")

    st.caption(
        "Official ranking requires at least 20 meaningful "
        "QB/RB/WR/TE acquisitions. Primary ranking is average "
        "Waiver Value per meaningful acquisition."
    )

    official_display = official.copy()

    official_display["Rank"] = (
        official_display[
            "official_rank"
        ].astype(int)
    )

    official_display["Franchise"] = (
        official_display["team"]
    )

    official_display["Meaningful Adds"] = (
        official_display[
            "meaningful_acquisitions"
        ].astype(int)
    )

    official_display["Avg Waiver Value"] = (
        official_display[
            "avg_waiver_value"
        ].round(1)
    )

    official_display["Good Pickup Rate"] = (
        official_display[
            "good_rate"
        ].round(1).astype(str)
        + "%"
    )

    official_display["Elite Finds"] = (
        official_display[
            "elite_finds"
        ].astype(int)
    )

    official_display["Bust Rate"] = (
        official_display[
            "bust_rate"
        ].round(1).astype(str)
        + "%"
    )

    st.dataframe(
        official_display[
            [
                "Rank",
                "Franchise",
                "Meaningful Adds",
                "Avg Waiver Value",
                "Good Pickup Rate",
                "Elite Finds",
                "Bust Rate",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    # ========================================================
    # LIMITED SAMPLE
    # ========================================================

    limited = (
        franchise[
            ~franchise[
                "official_ranking_eligible"
            ].astype(str).str.lower().eq("true")
        ]
        .sort_values(
            "avg_waiver_value",
            ascending=False,
        )
        .copy()
    )

    if not limited.empty:

        with st.expander(
            "Limited-sample franchises"
        ):

            st.caption(
                "These franchises have fewer than 20 meaningful "
                "acquisitions and are therefore not included in "
                "the official all-time ranking."
            )

            limited["Franchise"] = (
                limited["team"]
            )

            limited["Meaningful Adds"] = (
                limited[
                    "meaningful_acquisitions"
                ].astype(int)
            )

            limited["Avg Waiver Value"] = (
                limited[
                    "avg_waiver_value"
                ].round(1)
            )

            limited["Seasons"] = (
                limited[
                    "seasons_with_data"
                ].astype(int)
            )

            st.dataframe(
                limited[
                    [
                        "Franchise",
                        "Seasons",
                        "Meaningful Adds",
                        "Avg Waiver Value",
                    ]
                ],
                hide_index=True,
                use_container_width=True,
            )


    st.divider()


    # ========================================================
    # TOTAL POSITIVE VALUE
    # ========================================================

    st.subheader("📦 Most Total Positive Waiver Value")

    st.caption(
        "This is a volume statistic rather than the official "
        "manager ranking. It rewards franchises for accumulating "
        "positive-value pickups over time."
    )

    volume = (
        franchise
        .sort_values(
            "total_positive_value",
            ascending=False,
        )
        .copy()
    )

    volume["Franchise"] = volume["team"]

    volume["Meaningful Adds"] = (
        volume[
            "meaningful_acquisitions"
        ].astype(int)
    )

    volume["Total Positive Value"] = (
        volume[
            "total_positive_value"
        ].round(1)
    )

    volume["Avg Waiver Value"] = (
        volume[
            "avg_waiver_value"
        ].round(1)
    )

    st.dataframe(
        volume[
            [
                "Franchise",
                "Meaningful Adds",
                "Total Positive Value",
                "Avg Waiver Value",
            ]
        ].head(15),
        hide_index=True,
        use_container_width=True,
    )


    st.divider()


    # ========================================================
    # WAIVER HALL OF FAME
    # ========================================================

    st.subheader("💎 Waiver Wire Hall of Fame")

    st.caption(
        "The highest-rated meaningful waiver and free-agent "
        "acquisitions in league history."
    )

    hof_display = (
        hall
        .sort_values(
            [
                "waiver_score",
                "scoring_production_points",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .head(25)
        .copy()
    )

    hof_display["Year"] = (
        hof_display["year"].astype(int)
    )

    hof_display["Player"] = (
        hof_display["player"]
    )

    hof_display["Franchise"] = (
        hof_display["team_canonical"]
    )

    hof_display["Pos"] = (
        hof_display["player_position"]
    )

    hof_display["Week Added"] = (
        pd.to_numeric(
            hof_display[
                "first_eligible_week"
            ],
            errors="coerce",
        )
        .round()
        .astype("Int64")
    )

    hof_display["Weeks"] = (
        hof_display[
            "scoring_opportunity_weeks"
        ]
        .round()
        .astype("Int64")
    )

    hof_display["Points"] = (
        hof_display[
            "scoring_production_points"
        ].round(1)
    )

    hof_display["Waiver Score"] = (
        hof_display[
            "waiver_score"
        ].round(1)
    )

    hof_display["Waiver Value"] = (
        hof_display[
            "waiver_value"
        ].round(1)
    )

    hof_display["Grade"] = (
        hof_display[
            "waiver_category"
        ]
    )

    st.dataframe(
        hof_display[
            [
                "Year",
                "Player",
                "Franchise",
                "Pos",
                "Week Added",
                "Weeks",
                "Points",
                "Waiver Score",
                "Waiver Value",
                "Grade",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    st.divider()


    # ========================================================
    # ACQUISITION EXPLORER
    # ========================================================

    st.subheader("🔎 Acquisition Explorer")

    st.caption(
        "Explore every rated skill-position waiver/free-agent "
        "acquisition. Trivial churn remains in this history even "
        "when it is excluded from manager rankings."
    )

    f1, f2, f3 = st.columns(3)

    year_options = [
        "All"
    ] + [
        str(int(year))
        for year in sorted(
            waiver["year"].dropna().unique(),
            reverse=True,
        )
    ]

    selected_year = f1.selectbox(
        "Season",
        year_options,
        key="waiver_value_year",
    )

    position_options = [
        "All",
        "QB",
        "RB",
        "WR",
        "TE",
    ]

    selected_position = f2.selectbox(
        "Position",
        position_options,
        key="waiver_value_position",
    )

    franchise_options = [
        "All"
    ] + sorted(
        waiver[
            "team_canonical"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_franchise = f3.selectbox(
        "Franchise",
        franchise_options,
        key="waiver_value_franchise",
    )

    explorer = waiver.copy()

    if selected_year != "All":
        explorer = explorer[
            explorer["year"].eq(
                int(selected_year)
            )
        ]

    if selected_position != "All":
        explorer = explorer[
            explorer[
                "player_position"
            ].eq(selected_position)
        ]

    if selected_franchise != "All":
        explorer = explorer[
            explorer[
                "team_canonical"
            ].eq(selected_franchise)
        ]

    explorer = (
        explorer
        .sort_values(
            [
                "waiver_score",
                "scoring_production_points",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .copy()
    )

    explorer["Year"] = (
        explorer["year"].astype(int)
    )

    explorer["Player"] = (
        explorer["player"]
    )

    explorer["Franchise"] = (
        explorer["team_canonical"]
    )

    explorer["Pos"] = (
        explorer["player_position"]
    )

    explorer["Type"] = (
        explorer["acquisition_type"]
    )

    explorer["Week Added"] = (
        pd.to_numeric(
            explorer[
                "first_eligible_week"
            ],
            errors="coerce",
        )
        .round()
        .astype("Int64")
    )

    explorer["Weeks"] = (
        explorer[
            "scoring_opportunity_weeks"
        ]
        .round()
        .astype("Int64")
    )

    explorer["Points"] = (
        explorer[
            "scoring_production_points"
        ].round(1)
    )

    explorer["Waiver Score"] = (
        explorer[
            "waiver_score"
        ].round(1)
    )

    explorer["Waiver Value"] = (
        explorer[
            "waiver_value"
        ].round(1)
    )

    explorer["Grade"] = (
        explorer[
            "waiver_category"
        ]
    )

    explorer["Meaningful"] = (
        explorer[
            "meaningful_acquisition"
        ]
        .astype(str)
        .str.lower()
        .eq("true")
        .map(
            {
                True: "Yes",
                False: "No",
            }
        )
    )

    st.dataframe(
        explorer[
            [
                "Year",
                "Player",
                "Franchise",
                "Pos",
                "Type",
                "Week Added",
                "Weeks",
                "Points",
                "Waiver Score",
                "Waiver Value",
                "Grade",
                "Meaningful",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    st.divider()


    # ========================================================
    # SEASON HISTORY
    # ========================================================

    st.subheader("📚 Waiver Performance by Season")

    st.caption(
        "Season-level results are shown for context rather than "
        "used as an official 'best season' ranking because a "
        "small number of acquisitions can create extreme averages."
    )

    season_display = (
        team_season
        .sort_values(
            [
                "year",
                "avg_waiver_value",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .copy()
    )

    season_display["Year"] = (
        season_display["year"].astype(int)
    )

    season_display["Franchise"] = (
        season_display["team"]
    )

    season_display["Meaningful Adds"] = (
        season_display[
            "meaningful_acquisitions"
        ].astype(int)
    )

    season_display["Avg Waiver Value"] = (
        season_display[
            "avg_waiver_value"
        ].round(1)
    )

    season_display["Total Positive Value"] = (
        season_display[
            "total_positive_value"
        ].round(1)
    )

    season_display["Good Pickup Rate"] = (
        season_display[
            "good_rate"
        ].round(1).astype(str)
        + "%"
    )

    season_display["Elite Finds"] = (
        season_display[
            "elite_finds"
        ].astype(int)
    )

    season_display["Bust Rate"] = (
        season_display[
            "bust_rate"
        ].round(1).astype(str)
        + "%"
    )

    st.dataframe(
        season_display[
            [
                "Year",
                "Franchise",
                "Meaningful Adds",
                "Avg Waiver Value",
                "Total Positive Value",
                "Good Pickup Rate",
                "Elite Finds",
                "Bust Rate",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    st.divider()


    # ========================================================
    # METHODOLOGY
    # ========================================================

    with st.expander(
        "How Waiver Value is calculated"
    ):

        st.markdown(
            """
            **Eligible acquisitions**

            Waiver Value includes regular-season waiver and
            free-agent acquisitions at QB, RB, WR and TE.
            Kickers and defenses are excluded from the primary
            analysis.

            **2018**

            Complete 2018 transaction history is unavailable,
            so that season is excluded rather than treated as
            having zero waiver activity.

            **Ownership**

            Transaction history determines when a player enters
            and leaves a manager's roster. Production is credited
            only during the acquisition stint.

            **Acquisition timing**

            The first eligible scoring week is determined using
            transaction timestamps and the NFL schedule. Bye weeks
            do not count as production opportunities.

            **Step 1 — Rate Score**

            Points per scoring opportunity week are ranked against
            other eligible waiver/free-agent acquisitions at the
            same position in the same season.

            **Step 2 — Sustained Score**

            Total regular-season production while owned is ranked
            against that same position-season acquisition pool.

            **Step 3 — Waiver Score**

            `Waiver Score = 35% Rate Score + 65% Sustained Score`

            **Step 4 — Waiver Value**

            `Waiver Value = Waiver Score − 50`

            **Meaningful acquisition**

            A pickup is considered meaningful for manager rankings
            when it produced at least **2 scoring opportunity weeks**
            or at least **10 fantasy points** while owned.

            All eligible acquisitions remain in the acquisition
            history. The meaningful filter only prevents brief,
            low-impact churn from carrying equal weight in manager
            rankings.

            **Official franchise ranking**

            A franchise needs at least **20 meaningful acquisitions**
            to qualify. Qualified franchises are ranked by average
            Waiver Value per meaningful acquisition.

            **Classification**

            - Elite Find: Waiver Score 92+
            - Great Pickup: 87–91.9
            - Good Pickup: 74–86.9
            - Ordinary: 30–73.9
            - Poor Pickup: 12–29.9
            - Waiver Bust: below 12

            **What this does not measure**

            Waiver Value measures the **outcome of the acquisition**,
            not whether the manager started the player correctly
            afterward. Lineup utilization is intentionally separate
            from acquisition quality.
            """
        )


elif analysis_choice == "💀 Bad Beat Index":

    st.header("💀 Bad Beat Index")

    st.caption(
        "How often did a team play well enough to win, only to draw "
        "one of the few opponents capable of beating them?"
    )

    bad_beat_dir = Path("data/analysis")

    bad_team_week_path = (
        bad_beat_dir / "bad_beat_team_week.csv"
    )
    bad_franchise_path = (
        bad_beat_dir / "bad_beat_franchise.csv"
    )
    bad_season_path = (
        bad_beat_dir / "bad_beat_season.csv"
    )
    bad_history_path = (
        bad_beat_dir / "bad_beat_history.csv"
    )
    lucky_history_path = (
        bad_beat_dir / "lucky_win_history.csv"
    )

    required_bad_beat_files = [
        bad_team_week_path,
        bad_franchise_path,
        bad_season_path,
        bad_history_path,
        lucky_history_path,
    ]

    if not all(
        path.exists()
        for path in required_bad_beat_files
    ):
        st.error(
            "Bad Beat analysis data is missing. "
            "Run build_bad_beat_analysis.py."
        )
        st.stop()

    bad_team_week = pd.read_csv(
        bad_team_week_path
    )
    bad_franchise = pd.read_csv(
        bad_franchise_path
    )
    bad_season = pd.read_csv(
        bad_season_path
    )
    bad_history = pd.read_csv(
        bad_history_path
    )
    lucky_history = pd.read_csv(
        lucky_history_path
    )


    # ========================================================
    # LEAGUE VERDICT
    # ========================================================

    total_bad_beats = int(
        bad_team_week["bad_beat"].sum()
    )

    brutal_bad_beats = int(
        bad_team_week[
            "brutal_bad_beat"
        ].sum()
    )

    most_unlucky = (
        bad_franchise
        .sort_values(
            "wins_below_expected",
            ascending=False,
        )
        .iloc[0]
    )

    most_fortunate = (
        bad_franchise
        .sort_values(
            "wins_below_expected",
            ascending=True,
        )
        .iloc[0]
    )

    st.info(
        "🍀 **League Verdict: Schedule Luck Matters.** "
        f"Across league history, there have been "
        f"**{total_bad_beats} losses** by teams whose score "
        f"would have beaten at least half of the league that week. "
        f"That includes **{brutal_bad_beats} losses by teams that "
        f"finished among the week's top three scorers.**"
    )


    # ========================================================
    # HEADLINE METRICS
    # ========================================================

    b1, b2, b3, b4 = st.columns(4)

    b1.metric(
        "💀 Bad Beats",
        f"{total_bad_beats:,}",
    )

    b2.metric(
        "🔥 Top-3 Score Losses",
        f"{brutal_bad_beats:,}",
    )

    b3.metric(
        "☔ Unluckiest Franchise",
        str(
            most_unlucky[
                "canonical_team"
            ]
        ),
    )

    b4.metric(
        "📉 Wins Below Expected",
        (
            f"{float(most_unlucky['wins_below_expected']):+.2f}"
        ),
    )

    st.caption(
        "A Bad Beat is a loss despite scoring enough to beat "
        "at least half of the other teams that week."
    )


    # ========================================================
    # ALL-PLAY EXPLANATION
    # ========================================================

    st.subheader("🎯 What Are All-Play Expected Wins?")

    st.info(
        "**All-Play Expected Wins** compare each weekly score "
        "against every other team in the league that week. "
        "If your score would have beaten 10 of the other 11 teams, "
        "that performance is worth **10/11 = 0.91 expected wins**. "
        "Comparing those expected wins with actual head-to-head wins "
        "shows how much matchup scheduling helped or hurt a franchise."
    )


    # ========================================================
    # LUCK SPECTRUM
    # ========================================================

    st.divider()

    st.subheader("🍀 Bad Luck vs. Good Luck")

    st.caption(
        "Positive Wins vs. Expected means a team has won more games "
        "than its weekly scoring performances would predict. "
        "Negative means the schedule has cost it wins."
    )

    luck_view = (
        bad_franchise[
            [
                "canonical_team",
                "team_weeks",
                "actual_wins",
                "expected_wins",
                "wins_below_expected",
                "bad_beats",
                "severe_bad_beats",
                "lucky_wins",
            ]
        ]
        .copy()
    )

    luck_view["expected_wins"] = (
        luck_view["expected_wins"]
        .round(2)
    )

    luck_view["wins_vs_expected"] = (
        -luck_view["wins_below_expected"]
    ).round(2)

    luck_view = (
        luck_view
        .sort_values(
            "wins_vs_expected",
            ascending=True,
        )
        .rename(
            columns={
                "canonical_team": "Franchise",
                "team_weeks": "Team Weeks",
                "actual_wins": "Actual Wins",
                "expected_wins": "All-Play Expected Wins",
                "wins_vs_expected": "Wins vs. Expected",
                "bad_beats": "Bad Beats",
                "severe_bad_beats": "Severe Bad Beats",
                "lucky_wins": "Lucky Wins",
            }
        )
    )

    luck_view = luck_view.drop(
        columns=["wins_below_expected"]
    )

    st.dataframe(
        luck_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Franchise": st.column_config.TextColumn(
                "Franchise"
            ),
            "Team Weeks": st.column_config.NumberColumn(
                "Team Weeks",
                format="%d",
            ),
            "Actual Wins": st.column_config.NumberColumn(
                "Actual Wins",
                format="%d",
            ),
            "All-Play Expected Wins":
                st.column_config.NumberColumn(
                    "All-Play Expected Wins",
                    format="%.2f",
                ),
            "Wins vs. Expected":
                st.column_config.NumberColumn(
                    "Wins vs. Expected",
                    format="%+.2f",
                ),
            "Bad Beats": st.column_config.NumberColumn(
                "Bad Beats",
                format="%d",
            ),
            "Severe Bad Beats":
                st.column_config.NumberColumn(
                    "Severe Bad Beats",
                    format="%d",
                ),
            "Lucky Wins": st.column_config.NumberColumn(
                "Lucky Wins",
                format="%d",
            ),
        },
    )

    st.caption(
        f"At the extremes: "
        f"{most_unlucky['canonical_team']} has won "
        f"{float(most_unlucky['wins_below_expected']):.2f} fewer games "
        f"than all-play expectation, while "
        f"{most_fortunate['canonical_team']} has won "
        f"{abs(float(most_fortunate['wins_below_expected'])):.2f} "
        f"more games than expected."
    )


    # ========================================================
    # ULTIMATE BAD BEAT
    # ========================================================

    st.divider()

    st.subheader("💀 Worst Bad Beats in League History")

    actual_bad_beats = (
        bad_history[
            bad_history["bad_beat"] == 1
        ]
        .copy()
        .sort_values(
            [
                "bad_beat_value",
                "score",
            ],
            ascending=[
                False,
                False,
            ],
        )
    )

    if not actual_bad_beats.empty:

        worst = actual_bad_beats.iloc[0]

        possible_opponents = (
            int(worst["teams_that_week"])
            - 1
        )

        teams_beaten = int(
            worst["all_play_wins"]
        )

        w1, w2, w3, w4 = st.columns(4)

        w1.metric(
            "Season / Week",
            (
                f"{int(worst['year'])} "
                f"Week {int(worst['week'])}"
            ),
        )

        w2.metric(
            "Victim",
            str(
                worst["canonical_team"]
            ),
        )

        w3.metric(
            "Score",
            f"{float(worst['score']):.2f}",
        )

        w4.metric(
            "Weekly Rank",
            f"#{int(worst['weekly_score_rank'])}",
        )

        st.markdown(
            f"### {worst['canonical_team']} "
            f"{float(worst['score']):.2f} — "
            f"{worst['canonical_opponent']} "
            f"{float(worst['opponent_score']):.2f}"
        )

        st.caption(
            f"{worst['canonical_team']} would have beaten "
            f"{teams_beaten} of {possible_opponents} possible "
            f"opponents that week."
        )


    # ========================================================
    # HALL OF PAIN
    # ========================================================

    st.subheader("🏥 Bad Beat Hall of Pain")

    hall = (
        bad_franchise[
            [
                "canonical_team",
                "bad_beats",
                "severe_bad_beats",
                "brutal_bad_beats",
                "lucky_wins",
            ]
        ]
        .copy()
        .sort_values(
            [
                "severe_bad_beats",
                "bad_beats",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .rename(
            columns={
                "canonical_team": "Franchise",
                "bad_beats": "Bad Beats",
                "severe_bad_beats": "Severe",
                "brutal_bad_beats": "Top-3 Score Losses",
                "lucky_wins": "Lucky Wins",
            }
        )
    )

    st.dataframe(
        hall,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Franchise": st.column_config.TextColumn(
                "Franchise"
            ),
            "Bad Beats": st.column_config.NumberColumn(
                "Bad Beats",
                format="%d",
            ),
            "Severe": st.column_config.NumberColumn(
                "Severe",
                format="%d",
                help=(
                    "Loss despite a score that would have beaten "
                    "at least 75% of the league."
                ),
            ),
            "Top-3 Score Losses":
                st.column_config.NumberColumn(
                    "Top-3 Score Losses",
                    format="%d",
                ),
            "Lucky Wins": st.column_config.NumberColumn(
                "Lucky Wins",
                format="%d",
            ),
        },
    )


    # ========================================================
    # HISTORICAL BAD BEATS
    # ========================================================

    st.divider()

    st.subheader("📜 Biggest Historical Bad Beats")

    history_view = (
        actual_bad_beats
        .head(20)[
            [
                "year",
                "week",
                "canonical_team",
                "canonical_opponent",
                "score",
                "opponent_score",
                "weekly_score_rank",
                "all_play_wins",
                "expected_win_rate",
            ]
        ]
        .copy()
    )

    history_view[
        "expected_win_rate"
    ] = (
        history_view[
            "expected_win_rate"
        ]
        * 100
    )

    history_view = history_view.rename(
        columns={
            "year": "Year",
            "week": "Week",
            "canonical_team": "Team",
            "canonical_opponent": "Opponent",
            "score": "Score",
            "opponent_score": "Opponent Score",
            "weekly_score_rank": "Weekly Rank",
            "all_play_wins": "Teams Beaten",
            "expected_win_rate": "Would-Beat Rate",
        }
    )

    st.dataframe(
        history_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Year": st.column_config.NumberColumn(
                "Year",
                format="%d",
            ),
            "Week": st.column_config.NumberColumn(
                "Week",
                format="%d",
            ),
            "Team": st.column_config.TextColumn(
                "Team"
            ),
            "Opponent": st.column_config.TextColumn(
                "Opponent"
            ),
            "Score": st.column_config.NumberColumn(
                "Score",
                format="%.2f",
            ),
            "Opponent Score":
                st.column_config.NumberColumn(
                    "Opponent Score",
                    format="%.2f",
                ),
            "Weekly Rank":
                st.column_config.NumberColumn(
                    "Weekly Rank",
                    format="#%d",
                ),
            "Teams Beaten":
                st.column_config.NumberColumn(
                    "Teams Beaten",
                    format="%d",
                ),
            "Would-Beat Rate":
                st.column_config.NumberColumn(
                    "Would-Beat Rate",
                    format="%.1f%%",
                ),
        },
    )


    # ========================================================
    # LUCKY WINS
    # ========================================================

    st.divider()

    st.subheader("🍀 Luckiest Wins")

    actual_lucky_wins = (
        lucky_history[
            lucky_history["lucky_win"] == 1
        ]
        .copy()
        .sort_values(
            [
                "expected_win_rate",
                "score",
            ],
            ascending=[
                True,
                True,
            ],
        )
    )

    lucky_view = (
        actual_lucky_wins
        .head(15)[
            [
                "year",
                "week",
                "canonical_team",
                "canonical_opponent",
                "score",
                "opponent_score",
                "weekly_score_rank",
                "expected_win_rate",
            ]
        ]
        .copy()
    )

    lucky_view[
        "expected_win_rate"
    ] = (
        lucky_view[
            "expected_win_rate"
        ]
        * 100
    )

    lucky_view = lucky_view.rename(
        columns={
            "year": "Year",
            "week": "Week",
            "canonical_team": "Winner",
            "canonical_opponent": "Opponent",
            "score": "Winning Score",
            "opponent_score": "Opponent Score",
            "weekly_score_rank": "Weekly Rank",
            "expected_win_rate": "Would-Beat Rate",
        }
    )

    st.dataframe(
        lucky_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Year": st.column_config.NumberColumn(
                "Year",
                format="%d",
            ),
            "Week": st.column_config.NumberColumn(
                "Week",
                format="%d",
            ),
            "Winner": st.column_config.TextColumn(
                "Winner"
            ),
            "Opponent": st.column_config.TextColumn(
                "Opponent"
            ),
            "Winning Score":
                st.column_config.NumberColumn(
                    "Winning Score",
                    format="%.2f",
                ),
            "Opponent Score":
                st.column_config.NumberColumn(
                    "Opponent Score",
                    format="%.2f",
                ),
            "Weekly Rank":
                st.column_config.NumberColumn(
                    "Weekly Rank",
                    format="#%d",
                ),
            "Would-Beat Rate":
                st.column_config.NumberColumn(
                    "Would-Beat Rate",
                    format="%.1f%%",
                ),
        },
    )


    # ========================================================
    # METHODOLOGY
    # ========================================================

    with st.expander(
        "📖 Methodology & Definitions",
        expanded=False,
    ):

        st.markdown(
            """
            **Bad Beat**  
            A loss in a week where the team's score would have
            beaten at least half of the other teams in the league.

            **Severe Bad Beat**  
            A loss despite scoring enough to beat at least 75%
            of the league.

            **Top-3 Score Loss**  
            A loss despite finishing among the three highest
            scores in the league that week.

            **Lucky Win**  
            A victory despite a score that would have lost to at
            least half of the league.

            **All-Play Expected Wins**  
            Every weekly score is compared against all 11 other
            teams. Beating 10 of 11 possible opponents produces
            0.91 expected wins for that week.

            These statistics describe historical schedule outcomes.
            They do not imply that matchup schedules were biased or
            that expected wins are literal wins that should be added
            to a franchise's official record.
            """
        )


# ============================================================
# BENCH DECISIONS PAGE
# ============================================================


# ============================================================
# SCHEDULE SWAP PAGE
# ============================================================


elif analysis_choice == "🎲 Schedule Swap":

    schedule_dir = Path("data/analysis")

    matrix_path = (
        schedule_dir
        / "schedule_swap_matrix_long.csv"
    )

    season_path = (
        schedule_dir
        / "schedule_swap_season.csv"
    )

    franchise_path = (
        schedule_dir
        / "schedule_swap_franchise.csv"
    )

    extremes_path = (
        schedule_dir
        / "schedule_swap_extremes.csv"
    )

    required_files = [
        matrix_path,
        season_path,
        franchise_path,
        extremes_path,
    ]

    missing_files = [
        str(path)
        for path in required_files
        if not path.exists()
    ]

    if missing_files:

        st.error(
            "Schedule Swap analysis files are missing. "
            "Run `python build_schedule_swap_analysis.py` "
            "before loading this analysis."
        )

        with st.expander("Missing files"):
            for path in missing_files:
                st.code(path)

        st.stop()


    # ========================================================
    # LOAD DATA
    # ========================================================

    swap = pd.read_csv(matrix_path)
    schedule_season = pd.read_csv(season_path)
    schedule_franchise = pd.read_csv(franchise_path)
    schedule_extremes = pd.read_csv(extremes_path)


    # ========================================================
    # HERO
    # ========================================================

    st.header("🎲 Schedule Swap")

    st.markdown(
        """
        **What would your record have been with somebody else's
        schedule?**

        Schedule Swap keeps each team's **actual weekly scores**
        exactly the same, but replaces its opponents with the
        opponents faced by another team that season.

        Every franchise is tested against all 12 schedules from
        that year, giving us a direct measure of how much the actual
        matchup draw helped or hurt.
        """
    )

    st.caption(
        "Positive Schedule Luck means the actual schedule produced "
        "more wins than the team's average result across all 12 "
        "league schedules. Negative values mean the actual schedule "
        "cost wins."
    )


    # ========================================================
    # SEASON SELECTOR
    # ========================================================

    available_years = sorted(
        schedule_season["year"]
        .dropna()
        .astype(int)
        .unique()
        .tolist(),
        reverse=True,
    )

    selected_year = st.selectbox(
        "Season",
        available_years,
        key="schedule_swap_year",
    )

    year_season = (
        schedule_season[
            schedule_season["year"].eq(
                selected_year
            )
        ]
        .copy()
    )

    year_swap = (
        swap[
            swap["year"].eq(
                selected_year
            )
        ]
        .copy()
    )


    # ========================================================
    # SEASON VERDICT
    # ========================================================

    most_helped = (
        year_season
        .sort_values(
            "schedule_luck",
            ascending=False,
        )
        .iloc[0]
    )

    most_hurt = (
        year_season
        .sort_values(
            "schedule_luck",
            ascending=True,
        )
        .iloc[0]
    )

    biggest_range = (
        year_season
        .sort_values(
            "schedule_range",
            ascending=False,
        )
        .iloc[0]
    )

    st.markdown(
        f"""
        ### {selected_year} Verdict

        **{most_helped['team']}** received the most favorable
        schedule draw, winning **{most_helped['actual_win_equivalent']:.1f}**
        games compared with an average of
        **{most_helped['average_schedule_wins']:.1f}** across all
        league schedules — a difference of
        **{most_helped['schedule_luck']:+.1f} wins**.

        **{most_hurt['team']}** was hurt the most, finishing
        **{most_hurt['schedule_luck']:+.1f} wins** below its
        schedule-neutral expectation.
        """
    )


    # ========================================================
    # HEADLINE METRICS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Most Helped",
        most_helped["team"],
        f"{most_helped['schedule_luck']:+.1f} wins",
    )

    c2.metric(
        "Most Hurt",
        most_hurt["team"],
        f"{most_hurt['schedule_luck']:+.1f} wins",
    )

    c3.metric(
        "Biggest Schedule Range",
        biggest_range["team"],
        f"{biggest_range['schedule_range']:.1f} wins",
    )

    c4.metric(
        "Schedules Tested",
        "12 per team",
    )


    st.divider()


    # ========================================================
    # SEASON RESULTS
    # ========================================================

    st.subheader(
        f"📊 {selected_year} Schedule Luck"
    )

    st.caption(
        "Actual Wins are compared with the team's average win total "
        "when its scoring is run through all 12 schedules."
    )

    season_display = (
        year_season
        .sort_values(
            "schedule_luck",
            ascending=False,
        )
        .copy()
    )

    season_display["Team"] = (
        season_display["team"]
    )

    season_display["Actual Wins"] = (
        season_display[
            "actual_win_equivalent"
        ].round(1)
    )

    season_display["Average Across Schedules"] = (
        season_display[
            "average_schedule_wins"
        ].round(2)
    )

    season_display["Schedule Luck"] = (
        season_display[
            "schedule_luck"
        ].round(2)
    )

    season_display["Best Possible"] = (
        season_display[
            "best_schedule_wins"
        ].round(1)
    )

    season_display["Worst Possible"] = (
        season_display[
            "worst_schedule_wins"
        ].round(1)
    )

    season_display["Range"] = (
        season_display[
            "schedule_range"
        ].round(1)
    )

    st.dataframe(
        season_display[
            [
                "Team",
                "Actual Wins",
                "Average Across Schedules",
                "Schedule Luck",
                "Best Possible",
                "Worst Possible",
                "Range",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    st.divider()


    # ========================================================
    # 12 x 12 MATRIX
    # ========================================================

    st.subheader(
        f"🎲 {selected_year} Schedule Swap Matrix"
    )

    st.caption(
        "Rows are the scoring team. Columns are the borrowed "
        "schedule. Each cell shows how many wins that team would "
        "have produced using that schedule."
    )

    matrix = (
        year_swap
        .pivot(
            index="team",
            columns="schedule_team",
            values="win_equivalent",
        )
    )

    team_order = (
        year_season
        .sort_values(
            "actual_win_equivalent",
            ascending=False,
        )["team"]
        .tolist()
    )

    matrix = matrix.reindex(
        index=team_order,
        columns=team_order,
    )

    matrix.index.name = "Scoring Team"
    matrix.columns.name = "Borrowed Schedule"

    st.dataframe(
        matrix.round(1),
        use_container_width=True,
    )

    st.info(
        "The diagonal represents each team's real schedule. "
        "Those values exactly reconcile to the actual records "
        "in the matchup history."
    )


    st.divider()


    # ========================================================
    # TEAM SCHEDULE EXPLORER
    # ========================================================

    st.subheader("🔎 Team Schedule Explorer")

    selected_team = st.selectbox(
        "Team",
        sorted(
            year_season["team"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        ),
        key="schedule_swap_team",
    )

    team_result = (
        year_season[
            year_season["team"].eq(
                selected_team
            )
        ]
        .iloc[0]
    )

    team_schedules = (
        year_swap[
            year_swap["team"].eq(
                selected_team
            )
        ]
        .sort_values(
            "win_equivalent",
            ascending=False,
        )
        .copy()
    )

    best_schedule_team = (
        team_result[
            "best_schedule_team"
        ]
    )

    worst_schedule_team = (
        team_result[
            "worst_schedule_team"
        ]
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Actual Record",
        f"{team_result['actual_wins']:.0f}-"
        f"{team_result['actual_losses']:.0f}",
    )

    c2.metric(
        "Average Schedule",
        f"{team_result['average_schedule_wins']:.1f} wins",
        f"{team_result['schedule_luck']:+.1f} actual",
    )

    c3.metric(
        "Best Schedule",
        str(best_schedule_team),
        f"{team_result['best_schedule_record_wins']:.1f} wins",
    )

    c4.metric(
        "Worst Schedule",
        str(worst_schedule_team),
        f"{team_result['worst_schedule_record_wins']:.1f} wins",
    )

    team_schedules["Schedule"] = (
        team_schedules["schedule_team"]
    )

    team_schedules["Wins"] = (
        team_schedules[
            "win_equivalent"
        ].round(1)
    )

    team_schedules["Record"] = (
        team_schedules.apply(
            lambda row:
                f"{int(row['wins'])}-"
                f"{int(row['losses'])}"
                + (
                    f"-{int(row['ties'])}"
                    if row["ties"] > 0
                    else ""
                ),
            axis=1,
        )
    )

    team_schedules["Actual Schedule"] = (
        team_schedules[
            "is_actual_schedule"
        ]
        .astype(str)
        .str.lower()
        .eq("true")
        .map(
            {
                True: "Yes",
                False: "",
            }
        )
    )

    st.dataframe(
        team_schedules[
            [
                "Schedule",
                "Record",
                "Wins",
                "Actual Schedule",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    st.divider()


    # ========================================================
    # ALL-TIME SCHEDULE LUCK
    # ========================================================

    st.subheader("🏆 All-Time Schedule Luck")

    st.caption(
        "Cumulative Schedule Luck compares actual wins with expected "
        "wins across all available schedules. Seasons played are "
        "shown because historical franchises have different sample "
        "sizes."
    )

    all_time = (
        schedule_franchise
        .sort_values(
            "total_schedule_luck",
            ascending=False,
        )
        .copy()
    )

    all_time["Rank"] = (
        range(
            1,
            len(all_time) + 1,
        )
    )

    all_time["Franchise"] = (
        all_time["team"]
    )

    all_time["Seasons"] = (
        all_time["seasons"].astype(int)
    )

    all_time["Actual Wins"] = (
        all_time[
            "actual_wins"
        ].round(1)
    )

    all_time["Schedule-Neutral Wins"] = (
        all_time[
            "expected_wins_by_schedule"
        ].round(1)
    )

    all_time["Total Schedule Luck"] = (
        all_time[
            "total_schedule_luck"
        ].round(2)
    )

    all_time["Per Season"] = (
        all_time[
            "avg_schedule_luck"
        ].round(2)
    )

    st.dataframe(
        all_time[
            [
                "Rank",
                "Franchise",
                "Seasons",
                "Actual Wins",
                "Schedule-Neutral Wins",
                "Total Schedule Luck",
                "Per Season",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    # ========================================================
    # ALL-TIME VERDICT
    # ========================================================

    all_time_helped = (
        schedule_franchise
        .sort_values(
            "total_schedule_luck",
            ascending=False,
        )
        .iloc[0]
    )

    all_time_hurt = (
        schedule_franchise
        .sort_values(
            "total_schedule_luck",
            ascending=True,
        )
        .iloc[0]
    )

    st.markdown(
        f"""
        Across the full history available here,
        **{all_time_helped['team']}** has gained the most from
        schedule draw at approximately
        **{all_time_helped['total_schedule_luck']:+.1f} wins**.

        At the other extreme,
        **{all_time_hurt['team']}** has lost approximately
        **{all_time_hurt['total_schedule_luck']:+.1f} wins**
        relative to its average results across the league's
        schedules.
        """
    )


    st.divider()


    # ========================================================
    # BIGGEST HISTORICAL SWINGS
    # ========================================================

    st.subheader("📚 Biggest Schedule Swings")

    helped_tab, hurt_tab = st.tabs(
        [
            "Most Helped",
            "Most Hurt",
        ]
    )

    historical_helped = (
        schedule_season
        .sort_values(
            "schedule_luck",
            ascending=False,
        )
        .head(15)
        .copy()
    )

    historical_hurt = (
        schedule_season
        .sort_values(
            "schedule_luck",
            ascending=True,
        )
        .head(15)
        .copy()
    )


    def format_schedule_history(df):

        out = df.copy()

        out["Year"] = (
            out["year"].astype(int)
        )

        out["Team"] = out["team"]

        out["Actual Wins"] = (
            out[
                "actual_win_equivalent"
            ].round(1)
        )

        out["Average Schedule"] = (
            out[
                "average_schedule_wins"
            ].round(2)
        )

        out["Schedule Luck"] = (
            out[
                "schedule_luck"
            ].round(2)
        )

        out["Best"] = (
            out[
                "best_schedule_wins"
            ].round(1)
        )

        out["Worst"] = (
            out[
                "worst_schedule_wins"
            ].round(1)
        )

        return out[
            [
                "Year",
                "Team",
                "Actual Wins",
                "Average Schedule",
                "Schedule Luck",
                "Best",
                "Worst",
            ]
        ]


    with helped_tab:

        st.dataframe(
            format_schedule_history(
                historical_helped
            ),
            hide_index=True,
            use_container_width=True,
        )


    with hurt_tab:

        st.dataframe(
            format_schedule_history(
                historical_hurt
            ),
            hide_index=True,
            use_container_width=True,
        )


    st.divider()


    # ========================================================
    # METHODOLOGY
    # ========================================================

    with st.expander(
        "How Schedule Swap is calculated"
    ):

        st.markdown(
            """
            **1. Keep the scoring**

            A team's real fantasy score from each regular-season
            week never changes.

            **2. Borrow another team's schedule**

            The team's score is compared with the opponent faced by
            another franchise in that same week.

            This is repeated using all 12 schedules from the season.

            **3. Handle the self-opponent problem**

            Suppose Team A borrows Team B's schedule in a week when
            Team B actually played Team A.

            Using Team B's opponent literally would make Team A play
            itself. Instead, Team A faces **Team B** for that week.
            This preserves the matchup that existed between those
            two franchises while avoiding an artificial self-game.

            **4. Average across every schedule**

            `Average Schedule Wins` is the mean number of wins the
            team's scoring would have produced using each of the
            league's 12 schedules.

            **5. Schedule Luck**

            `Schedule Luck = Actual Wins − Average Schedule Wins`

            - Positive: the actual schedule helped.
            - Negative: the actual schedule hurt.
            - Near zero: the actual matchup draw was close to
              schedule-neutral.

            **Best / Worst Possible**

            These are the highest and lowest win totals produced
            among the 12 schedules actually played in that season.
            They are not theoretical schedules constructed from the
            easiest or hardest opponent every week.

            **What this does not mean**

            Schedule Luck does not say a team's official record
            should be changed. It also does not measure roster
            quality, lineup quality, injuries, or whether the league
            schedule was intentionally favorable or unfavorable.

            It answers one narrower question:

            **How differently would the same weekly scoring have
            performed under the schedules that other teams actually
            received?**
            """
        )



# ============================================================
# CHAMPIONSHIP DNA PAGE
# ============================================================


elif analysis_choice == "🏆 Championship DNA":

    dna_dir = Path("data/analysis")

    team_season_path = (
        dna_dir
        / "championship_dna_team_season.csv"
    )

    champions_path = (
        dna_dir
        / "championship_dna_champions.csv"
    )

    comparison_path = (
        dna_dir
        / "championship_dna_comparison.csv"
    )

    traits_path = (
        dna_dir
        / "championship_dna_traits.csv"
    )

    required_files = [
        team_season_path,
        champions_path,
        comparison_path,
        traits_path,
    ]

    missing_files = [
        str(path)
        for path in required_files
        if not path.exists()
    ]

    if missing_files:

        st.error(
            "Championship DNA analysis files are missing. "
            "Run `python build_championship_dna.py` first."
        )

        with st.expander("Missing files"):
            for path in missing_files:
                st.code(path)

        st.stop()


    # ========================================================
    # LOAD
    # ========================================================

    dna = pd.read_csv(team_season_path)
    champions = pd.read_csv(champions_path)
    comparison = pd.read_csv(comparison_path)
    traits = pd.read_csv(traits_path)


    # ========================================================
    # HERO
    # ========================================================

    st.header("🏆 Championship DNA")

    st.markdown(
        """
        **What actually separates champions from everyone else?**

        Instead of inventing a single Championship DNA score,
        this analysis compares every champion with the rest of
        the league across the traits we can measure consistently:

        **winning, scoring, lineup efficiency, bench management,
        drafting, and waivers.**
        """
    )

    st.caption(
        "The goal is descriptive: identify the traits champions "
        "actually shared, while also showing the very different "
        "ways individual champions were built."
    )


    # ========================================================
    # TOP-LINE FINDING
    # ========================================================

    comparison_lookup = (
        comparison
        .set_index("metric")
    )

    win_gap = comparison_lookup.loc[
        "Winning",
        "favorable_standardized_gap",
    ]

    efficiency_gap = comparison_lookup.loc[
        "Lineup Efficiency",
        "favorable_standardized_gap",
    ]

    scoring_gap = comparison_lookup.loc[
        "Scoring",
        "favorable_standardized_gap",
    ]

    waiver_gap = comparison_lookup.loc[
        "Waiver Value",
        "favorable_standardized_gap",
    ]

    st.markdown(
        f"""
        ### The historical pattern

        Championship teams separated themselves most through
        **winning ({win_gap:+.2f} SD)**,
        **lineup efficiency ({efficiency_gap:+.2f} SD)**, and
        **scoring ({scoring_gap:+.2f} SD)**.

        Draft performance helped, but was much less consistent.
        Waiver Value was actually
        **{waiver_gap:+.2f} SD relative to non-champions**,
        meaning elite waiver performance has not been a necessary
        ingredient for winning this league.
        """
    )


    # ========================================================
    # CHAMPION TRAIT PROFILE
    # ========================================================

    st.divider()

    st.subheader("🧬 The Average Champion")

    st.caption(
        "Percentiles are calculated within each season so that "
        "different scoring environments remain comparable. "
        "100 means best in the league that season."
    )

    trait_display = (
        traits
        .sort_values(
            "champion_average_percentile",
            ascending=False,
        )
        .copy()
    )

    trait_display["Trait"] = (
        trait_display["trait"]
    )

    trait_display["Average Champion Percentile"] = (
        trait_display[
            "champion_average_percentile"
        ].round(1)
    )

    trait_display["Median Champion Percentile"] = (
        trait_display[
            "champion_median_percentile"
        ].round(1)
    )

    trait_display["Champion Seasons"] = (
        trait_display[
            "champion_seasons_available"
        ].astype(int)
    )

    trait_display["Top-Quartile Champions"] = (
        trait_display[
            "champions_top_3"
        ].astype(int)
    )

    st.dataframe(
        trait_display[
            [
                "Trait",
                "Average Champion Percentile",
                "Median Champion Percentile",
                "Top-Quartile Champions",
                "Champion Seasons",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )

    c1, c2, c3 = st.columns(3)

    winning_trait = traits[
        traits["trait"].eq("Winning")
    ].iloc[0]

    scoring_trait = traits[
        traits["trait"].eq("Scoring")
    ].iloc[0]

    efficiency_trait = traits[
        traits["trait"].eq("Lineup Efficiency")
    ].iloc[0]

    c1.metric(
        "Average Winning Percentile",
        f"{winning_trait['champion_average_percentile']:.1f}",
    )

    c2.metric(
        "Average Scoring Percentile",
        f"{scoring_trait['champion_average_percentile']:.1f}",
    )

    c3.metric(
        "Average Efficiency Percentile",
        f"{efficiency_trait['champion_average_percentile']:.1f}",
    )


    # ========================================================
    # CHAMPIONS VS LEAGUE
    # ========================================================

    st.divider()

    st.subheader("⚖️ Champions vs Everyone Else")

    st.caption(
        "Standardized Gap puts unlike statistics on a comparable "
        "scale. Positive means champions performed better on that "
        "trait; negative means they performed worse."
    )

    comparison_display = comparison.copy()

    comparison_display["Trait"] = (
        comparison_display["metric"]
    )

    comparison_display["Champion Average"] = (
        comparison_display[
            "champion_mean"
        ].round(2)
    )

    comparison_display["Non-Champion Average"] = (
        comparison_display[
            "nonchampion_mean"
        ].round(2)
    )

    comparison_display["Standardized Gap"] = (
        comparison_display[
            "favorable_standardized_gap"
        ].round(2)
    )

    comparison_display["Champion Seasons"] = (
        comparison_display[
            "champion_n"
        ].astype(int)
    )

    st.dataframe(
        comparison_display[
            [
                "Trait",
                "Champion Average",
                "Non-Champion Average",
                "Standardized Gap",
                "Champion Seasons",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )

    st.info(
        "2018 Waiver Value is intentionally unavailable because "
        "the 2018 transaction history is missing. It is treated "
        "as N/A, never as zero."
    )


    # ========================================================
    # CHAMPION-BY-CHAMPION
    # ========================================================

    st.divider()

    st.subheader("👑 Championship Profiles")

    champion_display = (
        champions
        .sort_values("year")
        .copy()
    )

    champion_display["Year"] = (
        champion_display["year"].astype(int)
    )

    champion_display["Champion"] = (
        champion_display["team"]
    )

    champion_display["Record"] = (
        champion_display.apply(
            lambda row:
                f"{int(row['wins'])}-"
                f"{int(row['losses'])}",
            axis=1,
        )
    )

    champion_display["Scoring Rank"] = (
        champion_display[
            "scoring_rank"
        ].astype(int)
    )

    champion_display["Efficiency Rank"] = (
        champion_display[
            "efficiency_rank"
        ].astype(int)
    )

    champion_display["Draft Rank"] = (
        champion_display[
            "draft_class_rank"
        ].astype(int)
    )

    champion_display["Waiver Rank"] = (
        champion_display[
            "waiver_rank"
        ].apply(
            lambda value:
                "N/A"
                if pd.isna(value)
                else str(int(value))
        )
    )

    st.dataframe(
        champion_display[
            [
                "Year",
                "Champion",
                "Record",
                "Scoring Rank",
                "Efficiency Rank",
                "Draft Rank",
                "Waiver Rank",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


    # ========================================================
    # CHAMPION EXPLORER
    # ========================================================

    st.divider()

    st.subheader("🔎 Champion Explorer")

    champion_options = (
        champions
        .sort_values(
            "year",
            ascending=False,
        )
        .apply(
            lambda row:
                f"{int(row['year'])} — {row['team']}",
            axis=1,
        )
        .tolist()
    )

    selected_champion_label = st.selectbox(
        "Championship Season",
        champion_options,
        key="championship_dna_champion",
    )

    selected_year = int(
        selected_champion_label.split(
            " — ",
            1,
        )[0]
    )

    champ_row = (
        champions[
            champions["year"].eq(
                selected_year
            )
        ]
        .iloc[0]
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Regular-Season Wins",
        f"{champ_row['wins']:.0f}",
        f"Rank #{int(champ_row['win_rank'])}",
    )

    c2.metric(
        "Points / Game",
        f"{champ_row['points_per_game']:.1f}",
        f"Rank #{int(champ_row['scoring_rank'])}",
    )

    c3.metric(
        "Lineup Efficiency",
        f"{champ_row['season_efficiency_pct']:.1f}%",
        f"Rank #{int(champ_row['efficiency_rank'])}",
    )

    c4.metric(
        "Draft Value / Pick",
        f"{champ_row['avg_draft_value']:+.1f}",
        f"Rank #{int(champ_row['draft_class_rank'])}",
    )

    # --------------------------------------------------------
    # PERCENTILE PROFILE
    # --------------------------------------------------------

    st.markdown("#### Championship Trait Percentiles")

    profile_rows = [
        {
            "Trait": "Winning",
            "Percentile":
                champ_row["winning_percentile"],
        },
        {
            "Trait": "Scoring",
            "Percentile":
                champ_row["scoring_percentile"],
        },
        {
            "Trait": "Lineup Efficiency",
            "Percentile":
                champ_row["efficiency_percentile"],
        },
        {
            "Trait": "Bench Management",
            "Percentile":
                champ_row[
                    "bench_management_percentile"
                ],
        },
        {
            "Trait": "Draft",
            "Percentile":
                champ_row["draft_percentile"],
        },
        {
            "Trait": "Waivers",
            "Percentile":
                champ_row["waiver_percentile"],
        },
    ]

    profile = pd.DataFrame(profile_rows)

    profile["Percentile"] = (
        profile["Percentile"].round(1)
    )

    profile["League Rank Tier"] = (
        profile["Percentile"]
        .apply(
            lambda value:
                "N/A"
                if pd.isna(value)
                else (
                    "Elite"
                    if value >= 83.33
                    else (
                        "Strong"
                        if value >= 66.67
                        else (
                            "Middle"
                            if value >= 33.33
                            else "Weak"
                        )
                    )
                )
        )
    )

    st.dataframe(
        profile,
        hide_index=True,
        use_container_width=True,
    )


    # ========================================================
    # DIFFERENT WAYS TO WIN
    # ========================================================

    st.divider()

    st.subheader("🛠️ Different Ways to Win")

    st.markdown(
        """
        The championship history does **not** show one universal
        construction formula. Several titles came from very
        different strengths.
        """
    )

    archetype_rows = []

    for row in champions.itertuples():

        traits_available = {
            "Scoring":
                row.scoring_percentile,
            "Lineup Efficiency":
                row.efficiency_percentile,
            "Bench Management":
                row.bench_management_percentile,
            "Draft":
                row.draft_percentile,
            "Waivers":
                row.waiver_percentile,
        }

        valid_traits = {
            name: value
            for name, value
            in traits_available.items()
            if pd.notna(value)
        }

        strongest_trait = max(
            valid_traits,
            key=valid_traits.get,
        )

        strongest_value = (
            valid_traits[strongest_trait]
        )

        weakest_trait = min(
            valid_traits,
            key=valid_traits.get,
        )

        weakest_value = (
            valid_traits[weakest_trait]
        )

        archetype_rows.append({
            "Year": int(row.year),
            "Champion": row.team,
            "Primary Strength": strongest_trait,
            "Strength Percentile":
                round(strongest_value, 1),
            "Weakest Area": weakest_trait,
            "Weakness Percentile":
                round(weakest_value, 1),
        })

    archetypes = pd.DataFrame(
        archetype_rows
    )

    st.dataframe(
        archetypes,
        hide_index=True,
        use_container_width=True,
    )

    st.caption(
        "Primary Strength identifies the champion's highest "
        "season-relative percentile among scoring, lineup "
        "efficiency, bench management, drafting, and waivers. "
        "It is descriptive, not a categorical model."
    )


    # ========================================================
    # HISTORICAL EXAMPLES
    # ========================================================

    st.markdown("#### What the history shows")

    st.markdown(
        """
        - **2018 Pop Lockett Drop it** combined the league's
          #1 scoring offense with the #1 lineup-efficiency season.

        - **2022 malle_dips_pouches** won with the league's
          #1 draft class despite ranking near the bottom in
          lineup efficiency and waiver performance.

        - **2024 Post Mahomes** paired the #1 scoring offense
          with the #1 lineup-efficiency season despite an
          #11-ranked draft class.

        - **Voldemort's 2019 and 2021 titles** both came with
          the #11 draft class, further showing that draft success
          is not a requirement for a championship.
        """
    )


    # ========================================================
    # METHODOLOGY
    # ========================================================

    st.divider()

    with st.expander(
        "How Championship DNA is calculated"
    ):

        st.markdown(
            """
            **Regular-season performance**

            Winning percentage and scoring are calculated from the
            authoritative regular-season matchup history.

            **Lineup execution**

            Lineup Efficiency measures actual points relative to
            the best valid lineup that could have been started.
            Bench Management uses average weekly points left
            outside the optimal lineup.

            **Drafting**

            Draft performance uses the existing Draft Value model,
            which compares a player's season outcome with the
            expected positional outcome for that draft slot.

            **Waivers**

            Waiver performance uses the existing Waiver Value
            model based on production after acquisition. 2018 is
            unavailable because the transaction history for that
            season is missing.

            **Season percentiles**

            Each trait is converted to a percentile within its
            season. This keeps comparisons meaningful across years
            with different scoring environments.

            **Champions vs non-champions**

            Standardized Gap measures how far the champion average
            sits from the non-champion average relative to the
            overall historical standard deviation.

            A positive value means the trait favored champions.

            **No Championship DNA score**

            These traits are intentionally **not combined into a
            weighted composite score**. The historical results show
            that championship teams were built in different ways,
            and assigning arbitrary weights would imply a precision
            that the data does not support.

            Championship DNA is therefore a descriptive analysis of
            recurring traits — not a formula for determining who
            "deserved" a championship.
            """
        )



elif analysis_choice == "🏟️ Positional Advantage":

    st.title("🏟️ Positional Advantage")

    st.caption(
        "Where each franchise has historically gained — or lost — "
        "points at QB, RB, WR, and TE."
    )

    POSITIONAL_EDGE_DIR = Path("data/analysis")

    POSITIONAL_TEAM_WEEK_PATH = (
        POSITIONAL_EDGE_DIR /
        "positional_edge_team_week.csv"
    )

    POSITIONAL_SEASON_PATH = (
        POSITIONAL_EDGE_DIR /
        "positional_edge_season.csv"
    )

    POSITIONAL_FRANCHISE_PATH = (
        POSITIONAL_EDGE_DIR /
        "positional_edge_franchise.csv"
    )

    POSITIONAL_EXTREMES_PATH = (
        POSITIONAL_EDGE_DIR /
        "positional_edge_extremes.csv"
    )

    POSITIONAL_PLAYER_PATH = (
        POSITIONAL_EDGE_DIR /
        "positional_edge_player_contributions.csv"
    )

    required_positional_files = [
        POSITIONAL_TEAM_WEEK_PATH,
        POSITIONAL_SEASON_PATH,
        POSITIONAL_FRANCHISE_PATH,
        POSITIONAL_EXTREMES_PATH,
        POSITIONAL_PLAYER_PATH,
    ]

    missing_positional_files = [
        str(path)
        for path in required_positional_files
        if not path.exists()
    ]

    if missing_positional_files:

        st.error(
            "Positional Advantage data is missing. "
            "Run `python build_positional_edge_analysis.py` first."
        )

        st.code(
            "\n".join(
                missing_positional_files
            )
        )

        st.stop()


    # ========================================================
    # LOAD DATA
    # ========================================================

    positional_team_week = pd.read_csv(
        POSITIONAL_TEAM_WEEK_PATH
    )

    positional_season = pd.read_csv(
        POSITIONAL_SEASON_PATH
    )

    positional_franchise = pd.read_csv(
        POSITIONAL_FRANCHISE_PATH
    )

    positional_extremes = pd.read_csv(
        POSITIONAL_EXTREMES_PATH
    )

    positional_players = pd.read_csv(
        POSITIONAL_PLAYER_PATH
    )


    # ========================================================
    # INTRO
    # ========================================================

    st.markdown(
        """
        **Positional Edge** measures how many points a team's
        starters produced above or below the rest of the league
        at the same position.

        Each week, starter production at **QB, RB, WR, and TE**
        is compared with the average of the other 11 teams.
        FLEX production is credited to the player's actual
        fantasy position.

        A positive number means the franchise generated more
        production than the league baseline. A negative number
        means it generated less.
        """
    )

    with st.expander(
        "How to read Positional Edge"
    ):

        st.markdown(
            """
            If your RB starters score 30 points in a week while
            the other 11 teams average 20, your **RB Edge is
            +10 points**.

            If they score 16 while everyone else averages 20,
            your **RB Edge is −4 points**.

            Season totals add those weekly advantages together.

            **Edge / Week** is used for historical franchise
            comparisons so franchises with different numbers
            of seasons can be compared fairly.

            Kicker and defense are intentionally excluded from
            the primary analysis.
            """
        )


    # ========================================================
    # ALL-TIME POSITION LEADERS
    # ========================================================

    st.subheader("All-Time Position Leaders")

    st.caption(
        "Historical advantage per week. "
        "Use the position tabs to compare franchises directly."
    )

    position_config = {
        "QB": (
            "qb_edge_per_week",
            "Quarterback",
        ),
        "RB": (
            "rb_edge_per_week",
            "Running Back",
        ),
        "WR": (
            "wr_edge_per_week",
            "Wide Receiver",
        ),
        "TE": (
            "te_edge_per_week",
            "Tight End",
        ),
    }

    position_tabs = st.tabs(
        list(position_config.keys())
    )

    for tab, (
        position,
        (
            edge_col,
            position_name,
        ),
    ) in zip(
        position_tabs,
        position_config.items(),
    ):

        with tab:

            position_table = (
                positional_franchise[
                    [
                        "fantasy_team",
                        "seasons",
                        "weeks",
                        edge_col,
                    ]
                ]
                .copy()
                .sort_values(
                    edge_col,
                    ascending=False,
                )
                .reset_index(
                    drop=True
                )
            )

            position_table.insert(
                0,
                "Rank",
                range(
                    1,
                    len(position_table) + 1,
                ),
            )

            position_table = (
                position_table.rename(
                    columns={
                        "fantasy_team":
                            "Franchise",
                        "seasons":
                            "Seasons",
                        "weeks":
                            "Weeks",
                        edge_col:
                            "Edge / Week",
                    }
                )
            )

            leader = position_table.iloc[0]

            c1, c2, c3 = st.columns(3)

            c1.metric(
                f"Best {position_name} Franchise",
                leader["Franchise"],
            )

            c2.metric(
                "Edge / Week",
                f'{leader["Edge / Week"]:+.2f}',
            )

            c3.metric(
                "Seasons",
                int(
                    leader["Seasons"]
                ),
            )

            st.dataframe(
                position_table,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Rank":
                        st.column_config.NumberColumn(
                            "Rank",
                            format="%d",
                        ),
                    "Seasons":
                        st.column_config.NumberColumn(
                            "Seasons",
                            format="%d",
                        ),
                    "Weeks":
                        st.column_config.NumberColumn(
                            "Weeks",
                            format="%d",
                        ),
                    "Edge / Week":
                        st.column_config.NumberColumn(
                            "Edge / Week",
                            format="%+.2f",
                        ),
                },
            )


    # ========================================================
    # FRANCHISE POSITION PROFILES
    # ========================================================

    st.divider()

    st.subheader("Franchise Position Profiles")

    st.caption(
        "Average weekly advantage by position across each "
        "franchise's history."
    )

    profile = positional_franchise[
        [
            "fantasy_team",
            "seasons",
            "qb_edge_per_week",
            "rb_edge_per_week",
            "wr_edge_per_week",
            "te_edge_per_week",
            "strongest_position",
            "weakest_position",
        ]
    ].copy()

    profile = profile.rename(
        columns={
            "fantasy_team":
                "Franchise",
            "seasons":
                "Seasons",
            "qb_edge_per_week":
                "QB",
            "rb_edge_per_week":
                "RB",
            "wr_edge_per_week":
                "WR",
            "te_edge_per_week":
                "TE",
            "strongest_position":
                "Strongest",
            "weakest_position":
                "Weakest",
        }
    )

    # Sort by franchise name rather than a synthetic overall
    # positional ranking. Raw position edges are intentionally
    # kept separate because scoring volume differs by position.
    profile = profile.sort_values(
        "Franchise"
    )

    st.dataframe(
        profile,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Seasons":
                st.column_config.NumberColumn(
                    "Seasons",
                    format="%d",
                ),
            "QB":
                st.column_config.NumberColumn(
                    "QB Edge / Wk",
                    format="%+.2f",
                ),
            "RB":
                st.column_config.NumberColumn(
                    "RB Edge / Wk",
                    format="%+.2f",
                ),
            "WR":
                st.column_config.NumberColumn(
                    "WR Edge / Wk",
                    format="%+.2f",
                ),
            "TE":
                st.column_config.NumberColumn(
                    "TE Edge / Wk",
                    format="%+.2f",
                ),
        },
    )


    # ========================================================
    # FRANCHISE EXPLORER
    # ========================================================

    st.divider()

    st.subheader("Franchise Explorer")

    franchise_options = sorted(
        positional_season[
            "fantasy_team"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    selected_franchise = st.selectbox(
        "Choose a franchise",
        franchise_options,
        key="positional_edge_franchise",
    )

    franchise_history = (
        positional_season[
            positional_season[
                "fantasy_team"
            ].eq(
                selected_franchise
            )
        ]
        .copy()
        .sort_values(
            "year",
            ascending=False,
        )
    )

    franchise_summary = (
        positional_franchise[
            positional_franchise[
                "fantasy_team"
            ].eq(
                selected_franchise
            )
        ]
        .iloc[0]
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Strongest Position",
        franchise_summary[
            "strongest_position"
        ],
    )

    c2.metric(
        "Weakest Position",
        franchise_summary[
            "weakest_position"
        ],
    )

    c3.metric(
        "Seasons",
        int(
            franchise_summary[
                "seasons"
            ]
        ),
    )

    history_display = franchise_history[
        [
            "year",
            "qb_edge",
            "rb_edge",
            "wr_edge",
            "te_edge",
            "best_position",
            "worst_position",
        ]
    ].copy()

    history_display = history_display.rename(
        columns={
            "year":
                "Year",
            "qb_edge":
                "QB Edge",
            "rb_edge":
                "RB Edge",
            "wr_edge":
                "WR Edge",
            "te_edge":
                "TE Edge",
            "best_position":
                "Best",
            "worst_position":
                "Worst",
        }
    )

    st.dataframe(
        history_display,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Year":
                st.column_config.NumberColumn(
                    "Year",
                    format="%d",
                ),
            "QB Edge":
                st.column_config.NumberColumn(
                    "QB Edge",
                    format="%+.1f",
                ),
            "RB Edge":
                st.column_config.NumberColumn(
                    "RB Edge",
                    format="%+.1f",
                ),
            "WR Edge":
                st.column_config.NumberColumn(
                    "WR Edge",
                    format="%+.1f",
                ),
            "TE Edge":
                st.column_config.NumberColumn(
                    "TE Edge",
                    format="%+.1f",
                ),
        },
    )


    # ========================================================
    # BEST / WORST POSITIONAL SEASONS
    # ========================================================

    st.divider()

    st.subheader("Historical Extremes")

    st.caption(
        "Key Contributors shows the starters most responsible "
        "for each positional advantage or disadvantage."
    )


    # --------------------------------------------------------
    # FORMAT KEY CONTRIBUTORS
    # --------------------------------------------------------

    def positional_key_contributors(
        year,
        fantasy_team,
        edge_position,
        positive=True,
        limit=3,
    ):

        rows = positional_players[
            positional_players[
                "year"
            ].eq(year)
            &
            positional_players[
                "fantasy_team"
            ].eq(fantasy_team)
            &
            positional_players[
                "edge_position"
            ].eq(edge_position)
        ].copy()

        if rows.empty:
            return "—"

        rows = rows.sort_values(
            "player_edge_contribution",
            ascending=not positive,
        )

        if positive:

            rows = rows[
                rows[
                    "player_edge_contribution"
                ] > 0
            ]

        else:

            rows = rows[
                rows[
                    "player_edge_contribution"
                ] < 0
            ]

        rows = rows.head(limit)

        if rows.empty:
            return "—"

        return " · ".join(
            f'{row["player"]} '
            f'{row["player_edge_contribution"]:+.1f}'
            for _, row in rows.iterrows()
        )


    best_tab, worst_tab = st.tabs(
        [
            "🔥 Best Positional Seasons",
            "🧊 Worst Positional Seasons",
        ]
    )

    extreme_columns = [
        "year",
        "fantasy_team",
        "edge_position",
        "starter_points",
        "positional_edge",
        "edge_per_week",
        "position_rank",
    ]

    completed_positional_extremes = positional_extremes[
        pd.to_numeric(positional_extremes["year"], errors="coerce")
        .le(LAST_COMPLETED_SEASON)
    ].copy()


    # ========================================================
    # BEST
    # ========================================================

    with best_tab:

        best_seasons = (
            completed_positional_extremes[
                completed_positional_extremes[
                    "extreme_type"
                ].eq(
                    "Best Positional Season"
                )
            ][
                extreme_columns
            ]
            .copy()
            .sort_values(
                "positional_edge",
                ascending=False,
            )
        )

        best_seasons[
            "key_contributors"
        ] = best_seasons.apply(
            lambda row:
                positional_key_contributors(
                    row["year"],
                    row["fantasy_team"],
                    row["edge_position"],
                    positive=True,
                    limit=3,
                ),
            axis=1,
        )

        best_seasons = best_seasons.rename(
            columns={
                "year":
                    "Year",
                "fantasy_team":
                    "Franchise",
                "edge_position":
                    "Position",
                "starter_points":
                    "Starter Points",
                "positional_edge":
                    "Season Edge",
                "edge_per_week":
                    "Edge / Week",
                "position_rank":
                    "Position Rank",
                "key_contributors":
                    "Key Contributors",
            }
        )

        st.dataframe(
            best_seasons,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Year":
                    st.column_config.NumberColumn(
                        "Year",
                        format="%d",
                    ),
                "Starter Points":
                    st.column_config.NumberColumn(
                        "Starter Points",
                        format="%.1f",
                    ),
                "Season Edge":
                    st.column_config.NumberColumn(
                        "Season Edge",
                        format="%+.1f",
                    ),
                "Edge / Week":
                    st.column_config.NumberColumn(
                        "Edge / Week",
                        format="%+.2f",
                    ),
                "Position Rank":
                    st.column_config.NumberColumn(
                        "Position Rank",
                        format="%.0f",
                    ),
                "Key Contributors":
                    st.column_config.TextColumn(
                        "Key Contributors",
                        width="large",
                        help=(
                            "Top three player Edge Contributions "
                            "to the positional advantage."
                        ),
                    ),
            },
        )


    # ========================================================
    # WORST
    # ========================================================

    with worst_tab:

        worst_seasons = (
            completed_positional_extremes[
                completed_positional_extremes[
                    "extreme_type"
                ].eq(
                    "Worst Positional Season"
                )
            ][
                extreme_columns
            ]
            .copy()
            .sort_values(
                "positional_edge",
                ascending=True,
            )
        )

        worst_seasons[
            "key_contributors"
        ] = worst_seasons.apply(
            lambda row:
                positional_key_contributors(
                    row["year"],
                    row["fantasy_team"],
                    row["edge_position"],
                    positive=False,
                    limit=3,
                ),
            axis=1,
        )

        worst_seasons = worst_seasons.rename(
            columns={
                "year":
                    "Year",
                "fantasy_team":
                    "Franchise",
                "edge_position":
                    "Position",
                "starter_points":
                    "Starter Points",
                "positional_edge":
                    "Season Edge",
                "edge_per_week":
                    "Edge / Week",
                "position_rank":
                    "Position Rank",
                "key_contributors":
                    "Key Contributors",
            }
        )

        st.dataframe(
            worst_seasons,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Year":
                    st.column_config.NumberColumn(
                        "Year",
                        format="%d",
                    ),
                "Starter Points":
                    st.column_config.NumberColumn(
                        "Starter Points",
                        format="%.1f",
                    ),
                "Season Edge":
                    st.column_config.NumberColumn(
                        "Season Edge",
                        format="%+.1f",
                    ),
                "Edge / Week":
                    st.column_config.NumberColumn(
                        "Edge / Week",
                        format="%+.2f",
                    ),
                "Position Rank":
                    st.column_config.NumberColumn(
                        "Position Rank",
                        format="%.0f",
                    ),
                "Key Contributors":
                    st.column_config.TextColumn(
                        "Key Contributors",
                        width="large",
                        help=(
                            "Top three player Edge Contributions "
                            "to the positional disadvantage."
                        ),
                    ),
            },
        )


    # ========================================================
    # SEASON EXPLORER
    # ========================================================

    st.divider()

    st.subheader("Season Explorer")

    season_years = sorted(
        positional_season[
            "year"
        ]
        .dropna()
        .astype(int)
        .unique()
        .tolist(),
        reverse=True,
    )

    selected_year = st.selectbox(
        "Choose a season",
        season_years,
        key="positional_edge_year",
    )

    year_table = (
        positional_season[
            positional_season[
                "year"
            ].eq(
                selected_year
            )
        ][
            [
                "fantasy_team",
                "qb_edge",
                "rb_edge",
                "wr_edge",
                "te_edge",
                "best_position",
                "worst_position",
            ]
        ]
        .copy()
        .sort_values(
            "fantasy_team"
        )
    )

    year_table = year_table.rename(
        columns={
            "fantasy_team":
                "Franchise",
            "qb_edge":
                "QB Edge",
            "rb_edge":
                "RB Edge",
            "wr_edge":
                "WR Edge",
            "te_edge":
                "TE Edge",
            "best_position":
                "Best",
            "worst_position":
                "Worst",
        }
    )

    st.dataframe(
        year_table,
        hide_index=True,
        use_container_width=True,
        column_config={
            "QB Edge":
                st.column_config.NumberColumn(
                    "QB Edge",
                    format="%+.1f",
                ),
            "RB Edge":
                st.column_config.NumberColumn(
                    "RB Edge",
                    format="%+.1f",
                ),
            "WR Edge":
                st.column_config.NumberColumn(
                    "WR Edge",
                    format="%+.1f",
                ),
            "TE Edge":
                st.column_config.NumberColumn(
                    "TE Edge",
                    format="%+.1f",
                ),
        },
    )


    # ========================================================
    # METHODOLOGY
    # ========================================================

    st.divider()

    with st.expander(
        "Methodology & limitations"
    ):

        st.markdown(
            """
            ### Method

            For every regular-season team-week:

            1. Identify the team's actual starters.
            2. Assign every starter to QB, RB, WR, or TE.
            3. Attribute W/R/T starters to their underlying
               fantasy position.
            4. Sum starter fantasy points at each position.
            5. Compare that production with the average of the
               **other 11 teams** at the same position that week.

            `Positional Edge = Team Starter Points − Other-Team Average`

            Weekly edges are summed for season totals.

            Historical franchise comparisons use **Edge / Week**
            because franchises have participated in different
            numbers of seasons.

            ### What this measures

            Positional Edge describes the production a franchise
            actually received from the starters it used at each
            position.

            It reflects a combination of roster construction,
            player performance, injuries, acquisitions, and
            lineup choices.

            ### What this does not measure

            Positional Edge is **not** a causal manager-skill
            score. A manager can make a reasonable decision and
            still receive poor production.

            The four positions are also **not combined into an
            overall manager ranking** because RB and WR naturally
            account for more starting slots and scoring volume
            than QB and TE.

            Kicker and defense are excluded from the primary
            analysis.
            """
        )


elif analysis_choice == "🧠 Manager Skill":

    # ========================================================
    # LOAD DATA
    # ========================================================

    manager_team_season_path = (
        "data/analysis/management_index_team_season.csv"
    )

    manager_franchise_path = (
        "data/analysis/management_index_franchise.csv"
    )

    manager_extremes_path = (
        "data/analysis/management_index_extremes.csv"
    )

    manager_profiles_path = (
        "data/analysis/management_index_profiles.csv"
    )

    manager_team_season = pd.read_csv(
        manager_team_season_path
    )

    manager_franchise = pd.read_csv(
        manager_franchise_path
    )

    manager_extremes = pd.read_csv(
        manager_extremes_path
    )

    manager_profiles = pd.read_csv(
        manager_profiles_path
    )


    # ========================================================
    # HERO
    # ========================================================

    st.title("🧠 Manager Skill")

    st.markdown(
        """
        ### Management Index

        The **Management Index** measures the parts of fantasy
        football management we can observe directly:

        **50% Lineup Execution + 25% Draft Value + 25% Waiver Value**

        Each component is converted to a percentile within that
        season before the three pieces are combined.

        The goal is not to reward managers simply for winning.
        Wins, scoring, championships, schedule luck, and roster
        strength are treated as outcomes or context rather than
        ingredients in the score.
        """
    )

    st.info(
        "2018 does not receive a Management Index because complete "
        "waiver transaction history is unavailable. Available 2018 "
        "lineup and draft results remain part of their individual "
        "analysis pages, but no incomplete Management Index is created."
    )


    # ========================================================
    # OFFICIAL LEADERBOARD
    # ========================================================

    st.subheader("🏆 All-Time Management Index")

    official = (
        manager_franchise[
            manager_franchise["official"] == True
        ]
        .copy()
        .sort_values(
            "management_rank"
        )
    )

    limited = (
        manager_franchise[
            manager_franchise["official"] == False
        ]
        .copy()
        .sort_values(
            "management_index",
            ascending=False,
        )
    )

    leader = official.iloc[0]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "All-Time Leader",
        leader["team"],
    )

    c2.metric(
        "Management Index",
        f'{leader["management_index"]:.2f}',
    )

    c3.metric(
        "Measured Seasons",
        int(leader["measured_seasons"]),
    )

    c4.metric(
        "Championships",
        int(leader["championships"]),
    )

    leaderboard = official[
        [
            "management_rank",
            "team",
            "measured_seasons",
            "management_index",
            "lineup_index",
            "draft_index",
            "waiver_index",
            "winning_percentile",
            "championships",
        ]
    ].copy()

    leaderboard.columns = [
        "Rank",
        "Franchise",
        "Measured Seasons",
        "Management Index",
        "Lineup",
        "Draft",
        "Waivers",
        "Winning",
        "Championships",
    ]

    for col in [
        "Management Index",
        "Lineup",
        "Draft",
        "Waivers",
        "Winning",
    ]:
        leaderboard[col] = (
            leaderboard[col]
            .round(2)
        )

    leaderboard["Rank"] = (
        leaderboard["Rank"]
        .astype(int)
    )

    st.dataframe(
        leaderboard,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Official all-time ranking requires at least "
        "5 fully measured seasons."
    )


    # ========================================================
    # MANAGEMENT PROFILES
    # ========================================================

    st.subheader("🎯 Management Profiles")

    st.markdown(
        """
        A manager can reach a similar overall score in very different
        ways. This table shows each franchise's strongest and weakest
        historical management area.
        """
    )

    profiles = (
        manager_profiles[
            manager_profiles["official"] == True
        ]
        .copy()
        .sort_values(
            "management_rank"
        )
    )

    profile_table = profiles[
        [
            "management_rank",
            "team",
            "management_index",
            "lineup_index",
            "draft_index",
            "waiver_index",
            "strongest_area",
            "weakest_area",
        ]
    ].copy()

    profile_table.columns = [
        "Rank",
        "Franchise",
        "Index",
        "Lineup",
        "Draft",
        "Waivers",
        "Strongest Area",
        "Weakest Area",
    ]

    profile_table["Rank"] = (
        profile_table["Rank"]
        .astype(int)
    )

    for col in [
        "Index",
        "Lineup",
        "Draft",
        "Waivers",
    ]:
        profile_table[col] = (
            profile_table[col]
            .round(2)
        )

    st.dataframe(
        profile_table,
        use_container_width=True,
        hide_index=True,
    )


    # ========================================================
    # LIMITED SAMPLE
    # ========================================================

    if not limited.empty:

        with st.expander(
            "Limited-Sample Franchises"
        ):

            st.markdown(
                """
                These franchises do not have the five fully measured
                seasons required for the official all-time ranking.
                Their Management Index is shown for context only.
                """
            )

            limited_table = limited[
                [
                    "team",
                    "measured_seasons",
                    "management_index",
                    "lineup_index",
                    "draft_index",
                    "waiver_index",
                ]
            ].copy()

            limited_table.columns = [
                "Franchise",
                "Measured Seasons",
                "Management Index",
                "Lineup",
                "Draft",
                "Waivers",
            ]

            for col in [
                "Management Index",
                "Lineup",
                "Draft",
                "Waivers",
            ]:
                limited_table[col] = (
                    limited_table[col]
                    .round(2)
                )

            st.dataframe(
                limited_table,
                use_container_width=True,
                hide_index=True,
            )


    # ========================================================
    # BEST / WORST MANAGEMENT SEASONS
    # ========================================================

    st.subheader("📅 Best & Worst Management Seasons")

    best_tab, worst_tab = st.tabs(
        [
            "Best Seasons",
            "Worst Seasons",
        ]
    )

    season_cols = [
        "year",
        "team",
        "management_index",
        "management_rank",
        "lineup_index",
        "draft_index",
        "waiver_index",
        "winning_percentile",
        "scoring_percentile",
        "is_champion",
    ]

    with best_tab:

        best = (
            manager_team_season[
                manager_team_season[
                    "fully_measured"
                ] == True
            ][season_cols]
            .sort_values(
                "management_index",
                ascending=False,
            )
            .head(20)
            .copy()
        )

        best.columns = [
            "Year",
            "Franchise",
            "Management Index",
            "Season Rank",
            "Lineup",
            "Draft",
            "Waivers",
            "Winning",
            "Scoring",
            "Champion",
        ]

        for col in [
            "Management Index",
            "Lineup",
            "Draft",
            "Waivers",
            "Winning",
            "Scoring",
        ]:
            best[col] = (
                best[col]
                .round(2)
            )

        best["Season Rank"] = (
            best["Season Rank"]
            .astype(int)
        )

        st.dataframe(
            best,
            use_container_width=True,
            hide_index=True,
        )

    with worst_tab:

        worst = (
            manager_team_season[
                manager_team_season[
                    "fully_measured"
                ] == True
            ][season_cols]
            .sort_values(
                "management_index",
                ascending=True,
            )
            .head(20)
            .copy()
        )

        worst.columns = [
            "Year",
            "Franchise",
            "Management Index",
            "Season Rank",
            "Lineup",
            "Draft",
            "Waivers",
            "Winning",
            "Scoring",
            "Champion",
        ]

        for col in [
            "Management Index",
            "Lineup",
            "Draft",
            "Waivers",
            "Winning",
            "Scoring",
        ]:
            worst[col] = (
                worst[col]
                .round(2)
            )

        worst["Season Rank"] = (
            worst["Season Rank"]
            .astype(int)
        )

        st.dataframe(
            worst,
            use_container_width=True,
            hide_index=True,
        )


    # ========================================================
    # FRANCHISE EXPLORER
    # ========================================================

    st.subheader("🔎 Franchise Management Explorer")

    manager_options = sorted(
        manager_team_season[
            "team"
        ].dropna().unique()
    )

    selected_manager = st.selectbox(
        "Choose a franchise",
        manager_options,
        key="manager_skill_franchise",
    )

    manager_history = (
        manager_team_season[
            manager_team_season["team"]
            == selected_manager
        ]
        .copy()
        .sort_values("year")
    )

    measured_history = manager_history[
        manager_history["fully_measured"] == True
    ]

    if not measured_history.empty:

        avg_index = (
            measured_history[
                "management_index"
            ].mean()
        )

        best_row = (
            measured_history
            .sort_values(
                "management_index",
                ascending=False,
            )
            .iloc[0]
        )

        worst_row = (
            measured_history
            .sort_values(
                "management_index",
                ascending=True,
            )
            .iloc[0]
        )

        h1, h2, h3, h4 = st.columns(4)

        h1.metric(
            "Career Index",
            f"{avg_index:.2f}",
        )

        h2.metric(
            "Measured Seasons",
            len(measured_history),
        )

        h3.metric(
            "Best Season",
            f'{int(best_row["year"])} — '
            f'{best_row["management_index"]:.2f}',
        )

        h4.metric(
            "Worst Season",
            f'{int(worst_row["year"])} — '
            f'{worst_row["management_index"]:.2f}',
        )


    history_table = manager_history[
        [
            "year",
            "management_index",
            "management_rank",
            "lineup_index",
            "draft_index",
            "waiver_index",
            "winning_percentile",
            "scoring_percentile",
            "is_champion",
        ]
    ].copy()

    history_table.columns = [
        "Year",
        "Management Index",
        "Season Rank",
        "Lineup",
        "Draft",
        "Waivers",
        "Winning",
        "Scoring",
        "Champion",
    ]

    for col in [
        "Management Index",
        "Season Rank",
        "Lineup",
        "Draft",
        "Waivers",
        "Winning",
        "Scoring",
    ]:
        history_table[col] = (
            pd.to_numeric(
                history_table[col],
                errors="coerce",
            )
            .round(2)
        )

    st.dataframe(
        history_table,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "2018 Management Index is intentionally blank because "
        "complete waiver data is unavailable."
    )


    # ========================================================
    # MANAGEMENT VS RESULTS
    # ========================================================

    st.subheader("⚖️ Management vs Results")

    st.markdown(
        """
        Strong management helps, but it does not guarantee wins.

        A team's record also depends on roster quality, weekly scoring
        variance, injuries, and which opponents happen to appear on
        the schedule.
        """
    )

    measured_results = (
        manager_team_season[
            manager_team_season[
                "fully_measured"
            ] == True
        ]
        .copy()
    )

    corr_wins = (
        measured_results[
            [
                "management_index",
                "winning_percentile",
            ]
        ]
        .corr()
        .iloc[0, 1]
    )

    corr_scoring = (
        measured_results[
            [
                "management_index",
                "scoring_percentile",
            ]
        ]
        .corr()
        .iloc[0, 1]
    )

    r1, r2, r3 = st.columns(3)

    r1.metric(
        "Measured Team-Seasons",
        len(measured_results),
    )

    r2.metric(
        "Correlation with Winning",
        f"{corr_wins:.3f}",
    )

    r3.metric(
        "Correlation with Scoring",
        f"{corr_scoring:.3f}",
    )

    st.markdown(
        """
        The Index is intentionally **not** a disguised standings table.
        A moderate relationship with wins and scoring is desirable:
        management decisions matter, but they are only one part of
        fantasy football outcomes.
        """
    )


    # ========================================================
    # INTERESTING CONTRASTS
    # ========================================================

    st.subheader("🧪 When Management and Results Disagree")

    contrast = (
        measured_results[
            [
                "year",
                "team",
                "management_index",
                "winning_percentile",
                "scoring_percentile",
                "is_champion",
            ]
        ]
        .copy()
    )

    contrast["management_minus_winning"] = (
        contrast["management_index"]
        -
        contrast["winning_percentile"]
    )

    unlucky_management = (
        contrast.sort_values(
            "management_minus_winning",
            ascending=False,
        )
        .head(10)
        .copy()
    )

    results_over_management = (
        contrast.sort_values(
            "management_minus_winning",
            ascending=True,
        )
        .head(10)
        .copy()
    )

    ctab1, ctab2 = st.tabs(
        [
            "Strong Management, Weak Results",
            "Results Above Management",
        ]
    )

    with ctab1:

        table = unlucky_management[
            [
                "year",
                "team",
                "management_index",
                "winning_percentile",
                "scoring_percentile",
                "management_minus_winning",
            ]
        ].copy()

        table.columns = [
            "Year",
            "Franchise",
            "Management Index",
            "Winning",
            "Scoring",
            "Mgmt − Winning",
        ]

        for col in [
            "Management Index",
            "Winning",
            "Scoring",
            "Mgmt − Winning",
        ]:
            table[col] = table[col].round(2)

        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
        )

    with ctab2:

        table = results_over_management[
            [
                "year",
                "team",
                "management_index",
                "winning_percentile",
                "scoring_percentile",
                "management_minus_winning",
            ]
        ].copy()

        table.columns = [
            "Year",
            "Franchise",
            "Management Index",
            "Winning",
            "Scoring",
            "Mgmt − Winning",
        ]

        for col in [
            "Management Index",
            "Winning",
            "Scoring",
            "Mgmt − Winning",
        ]:
            table[col] = table[col].round(2)

        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
        )


    # ========================================================
    # METHODOLOGY
    # ========================================================

    with st.expander("Methodology"):

        st.markdown(
            """
            **Management Index formula**

            - **50% Lineup Execution**
              - Season lineup efficiency relative to the other
                managers that year.
              - Measures how much of the available roster scoring
                potential actually made it into the starting lineup.

            - **25% Draft Value**
              - Draft outcome relative to the expected positional
                result for the pick.
              - Each team's season is converted to a percentile
                within that fantasy season.

            - **25% Waiver Value**
              - Production and positional value generated by
                meaningful waiver/free-agent acquisitions.
              - Each team's season is converted to a percentile
                within that fantasy season.

            **Why percentiles?**

            Scoring environments, NFL seasons, and league conditions
            change over time. Comparing each manager to the other
            managers in the same season makes the components
            comparable across league history.

            **2018**

            Complete historical waiver transaction data is not
            available for 2018. Rather than redistribute the missing
            25% weight or treat missing waiver performance as zero,
            the Management Index is left blank for that season.

            **Official all-time ranking**

            A franchise needs at least **5 fully measured seasons**
            to qualify for the official leaderboard.

            **What is intentionally excluded**

            Wins, championships, points scored, roster strength,
            Schedule Swap results, Bad Beat results, and other luck
            measures are not part of the Management Index.

            Those are outcomes and context. Keeping them separate
            allows the analysis to identify seasons where strong
            management produced poor results — or where weak
            management still produced a strong record.

            **Bench Decisions**

            The separate Bench Decisions analysis is not used in the
            Management Index.
            """
        )


elif analysis_choice == "🪑 Bench Decisions":

    st.header("🪑 Bench Decisions")

    st.caption(
        "How many points were left outside the optimal lineup — "
        "and how often did those lineup decisions actually change "
        "the outcome of a matchup?"
    )

    bench_dir = Path("data/analysis")

    team_week_path = (
        bench_dir
        / "bench_decisions_team_week.csv"
    )

    franchise_path = (
        bench_dir
        / "bench_decisions_franchise.csv"
    )

    season_path = (
        bench_dir
        / "bench_decisions_season.csv"
    )

    avoidable_path = (
        bench_dir
        / "bench_decisions_avoidable_losses.csv"
    )

    misses_path = (
        bench_dir
        / "bench_decisions_biggest_misses.csv"
    )

    required_files = [
        team_week_path,
        franchise_path,
        season_path,
        avoidable_path,
        misses_path,
    ]

    missing_files = [
        str(path)
        for path in required_files
        if not path.exists()
    ]

    if missing_files:

        st.error(
            "Bench Decisions analysis files are missing. "
            "Run `python build_bench_decisions_analysis.py` "
            "before loading this analysis."
        )

        with st.expander("Missing files"):
            for path in missing_files:
                st.code(path)

        st.stop()


    # ========================================================
    # LOAD DATA
    # ========================================================

    bench_week = pd.read_csv(
        team_week_path
    )

    bench_franchise = pd.read_csv(
        franchise_path
    )

    bench_season = pd.read_csv(
        season_path
    )

    avoidable_losses = pd.read_csv(
        avoidable_path
    )

    biggest_misses = pd.read_csv(
        misses_path
    )


    # ========================================================
    # LEAGUE VERDICT
    # ========================================================

    total_losses = int(
        bench_week["actual_loss"].sum()
    )

    manager_losses = int(
        bench_week[
            "manager_caused_loss"
        ].sum()
    )

    avoidable_pct = (
        manager_losses
        / total_losses
        * 100
        if total_losses
        else 0
    )

    avg_points_left = float(
        bench_week[
            "points_left_on_bench"
        ].mean()
    )

    total_points_left = float(
        bench_week[
            "points_left_on_bench"
        ].sum()
    )

    st.info(
        "### League Verdict: Lineup Decisions Matter\n\n"
        f"Across league history, **{manager_losses:,} losses "
        f"({avoidable_pct:.1f}% of all losses)** could have become "
        "wins with the calculated optimal lineup. "
        "But not every bench mistake changed a result — some merely "
        "left extra points behind in games that were already won or "
        "could not realistically be saved."
    )


    # ========================================================
    # HEADLINE METRICS
    # ========================================================

    most_manager_losses = (
        bench_franchise
        .sort_values(
            [
                "manager_caused_losses",
                "manager_caused_loss_rate",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .iloc[0]
    )

    highest_loss_rate = (
        bench_franchise[
            bench_franchise[
                "actual_losses"
            ] > 0
        ]
        .sort_values(
            "manager_caused_loss_rate",
            ascending=False,
        )
        .iloc[0]
    )

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric(
            "Manager-Caused Losses",
            f"{manager_losses:,}",
            help=(
                "Losses where the actual lineup lost but the "
                "calculated optimal lineup would have won."
            ),
        )

    with m2:
        st.metric(
            "Losses That Were Flippable",
            f"{avoidable_pct:.1f}%",
            help=(
                "Share of all historical losses where the "
                "calculated optimal lineup would have won."
            ),
        )

    with m3:
        st.metric(
            "Avg Points Left / Week",
            f"{avg_points_left:.2f}",
            help=(
                "Average difference between actual score and "
                "calculated optimal score."
            ),
        )

    with m4:
        st.metric(
            "Most Flippable Losses",
            f"{int(most_manager_losses['manager_caused_losses'])}",
            help=(
                "Highest franchise total of manager-caused losses. "
                "Multiple franchises may be tied."
            ),
        )

    st.caption(
        f"The league left **{total_points_left:,.2f} total points** "
        "outside its calculated optimal lineups over the period studied."
    )


    # ========================================================
    # WHAT COUNTS AS A MANAGER-CAUSED LOSS?
    # ========================================================

    st.subheader("What Counts as a Manager-Caused Loss?")

    st.write(
        "A manager-caused loss is a historical matchup where the "
        "team's **actual starting lineup lost**, but the optimizer "
        "found a **legal lineup from that week's roster that would "
        "have beaten the actual opponent score**."
    )

    st.write(
        "This is intentionally stricter than simply counting bench "
        "points. Leaving 30 points outside the optimal lineup in a "
        "50-point loss did not change the outcome. Leaving 8 points "
        "outside the optimal lineup in a 3-point loss might have."
    )


    # ========================================================
    # FRANCHISE MANAGEMENT TABLE
    # ========================================================

    st.subheader("Franchise Lineup Management")

    st.caption(
        "Manager-caused losses measure outcome-changing lineup "
        "decisions. Efficiency measures how closely each franchise's "
        "actual lineups approached its calculated optimal lineups."
    )

    franchise_view = (
        bench_franchise[
            [
                "canonical_team",
                "team_weeks",
                "actual_losses",
                "manager_caused_losses",
                "manager_caused_loss_rate",
                "avg_points_left_per_week",
                "avg_lineup_efficiency_pct",
                "worst_week_points_left",
            ]
        ]
        .copy()
        .sort_values(
            [
                "manager_caused_losses",
                "manager_caused_loss_rate",
            ],
            ascending=[
                False,
                False,
            ],
        )
    )

    franchise_view[
        "manager_caused_loss_rate"
    ] = (
        franchise_view[
            "manager_caused_loss_rate"
        ]
        * 100
    )

    franchise_view = franchise_view.rename(
        columns={
            "canonical_team": "Franchise",
            "team_weeks": "Team Weeks",
            "actual_losses": "Losses",
            "manager_caused_losses":
                "Flippable Losses",
            "manager_caused_loss_rate":
                "% of Losses Flippable",
            "avg_points_left_per_week":
                "Avg Points Left",
            "avg_lineup_efficiency_pct":
                "Avg Efficiency",
            "worst_week_points_left":
                "Worst Week",
        }
    )

    st.dataframe(
        franchise_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Franchise":
                st.column_config.TextColumn(
                    "Franchise"
                ),
            "Team Weeks":
                st.column_config.NumberColumn(
                    "Team Weeks",
                    format="%d",
                ),
            "Losses":
                st.column_config.NumberColumn(
                    "Losses",
                    format="%d",
                ),
            "Flippable Losses":
                st.column_config.NumberColumn(
                    "Flippable Losses",
                    format="%d",
                ),
            "% of Losses Flippable":
                st.column_config.NumberColumn(
                    "% of Losses Flippable",
                    format="%.1f%%",
                ),
            "Avg Points Left":
                st.column_config.NumberColumn(
                    "Avg Points Left",
                    format="%.2f",
                ),
            "Avg Efficiency":
                st.column_config.NumberColumn(
                    "Avg Efficiency",
                    format="%.1f%%",
                ),
            "Worst Week":
                st.column_config.NumberColumn(
                    "Worst Week",
                    format="%.2f",
                ),
        },
    )


    # ========================================================
    # MOST VULNERABLE FRANCHISE
    # ========================================================

    st.subheader("Who Paid the Highest Price?")

    c1, c2 = st.columns(2)

    with c1:

        st.markdown(
            "#### Most Manager-Caused Losses"
        )

        max_losses = int(
            bench_franchise[
                "manager_caused_losses"
            ].max()
        )

        tied_most = (
            bench_franchise[
                bench_franchise[
                    "manager_caused_losses"
                ] == max_losses
            ][
                "canonical_team"
            ]
            .tolist()
        )

        st.metric(
            "Flippable Losses",
            f"{max_losses}",
        )

        st.write(
            ", ".join(tied_most)
        )

        st.caption(
            "These franchises share the highest raw total of "
            "losses that the calculated optimal lineup would "
            "have turned into wins."
        )

    with c2:

        st.markdown(
            "#### Highest Flippable-Loss Rate"
        )

        st.metric(
            str(
                highest_loss_rate[
                    "canonical_team"
                ]
            ),
            (
                f"{highest_loss_rate['manager_caused_loss_rate'] * 100:.1f}%"
            ),
        )

        st.write(
            f"{int(highest_loss_rate['manager_caused_losses'])} "
            f"of {int(highest_loss_rate['actual_losses'])} losses"
        )

        st.caption(
            "This measures the share of a franchise's losses "
            "that could have become wins with its calculated "
            "optimal lineup."
        )


    # ========================================================
    # ULTIMATE BENCH DISASTER
    # ========================================================

    st.subheader("The Ultimate Lineup Disaster")

    worst_flippable = (
        avoidable_losses
        .sort_values(
            [
                "points_left_on_bench",
                "would_have_won_by",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .iloc[0]
    )

    w1, w2, w3, w4 = st.columns(4)

    with w1:
        st.metric(
            "Team",
            str(
                worst_flippable[
                    "canonical_team"
                ]
            ),
        )

    with w2:
        st.metric(
            "Actual Score",
            f"{worst_flippable['actual_score']:.2f}",
        )

    with w3:
        st.metric(
            "Optimal Score",
            f"{worst_flippable['optimal_score']:.2f}",
        )

    with w4:
        st.metric(
            "Would Have Won By",
            f"{worst_flippable['would_have_won_by']:.2f}",
        )

    st.write(
        f"**{int(worst_flippable['year'])} Week "
        f"{int(worst_flippable['week'])}:** "
        f"{worst_flippable['canonical_team']} scored "
        f"**{worst_flippable['actual_score']:.2f}** against "
        f"{worst_flippable['canonical_opponent']}'s "
        f"**{worst_flippable['opponent_score']:.2f}**. "
        "The calculated optimal lineup would have scored "
        f"**{worst_flippable['optimal_score']:.2f}**, turning "
        "the loss into a win."
    )

    st.markdown("**Should Have Benched**")
    st.write(
        worst_flippable[
            "should_have_benched"
        ]
    )

    st.markdown("**Should Have Started**")
    st.write(
        worst_flippable[
            "should_have_started"
        ]
    )


    # ========================================================
    # HALL OF REGRET
    # ========================================================

    st.subheader("Hall of Regret")

    st.caption(
        "The biggest historical lineup mistakes that actually "
        "changed a potential win into a loss."
    )

    regret_view = (
        avoidable_losses
        .head(15)[
            [
                "year",
                "week",
                "canonical_team",
                "canonical_opponent",
                "actual_score",
                "opponent_score",
                "optimal_score",
                "points_left_on_bench",
                "would_have_won_by",
            ]
        ]
        .copy()
    )

    regret_view = regret_view.rename(
        columns={
            "year": "Year",
            "week": "Week",
            "canonical_team": "Team",
            "canonical_opponent": "Opponent",
            "actual_score": "Actual",
            "opponent_score": "Opponent Score",
            "optimal_score": "Optimal",
            "points_left_on_bench":
                "Points Left",
            "would_have_won_by":
                "Would Win By",
        }
    )

    st.dataframe(
        regret_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Year":
                st.column_config.NumberColumn(
                    "Year",
                    format="%d",
                ),
            "Week":
                st.column_config.NumberColumn(
                    "Week",
                    format="%d",
                ),
            "Team":
                st.column_config.TextColumn(
                    "Team"
                ),
            "Opponent":
                st.column_config.TextColumn(
                    "Opponent"
                ),
            "Actual":
                st.column_config.NumberColumn(
                    "Actual",
                    format="%.2f",
                ),
            "Opponent Score":
                st.column_config.NumberColumn(
                    "Opponent Score",
                    format="%.2f",
                ),
            "Optimal":
                st.column_config.NumberColumn(
                    "Optimal",
                    format="%.2f",
                ),
            "Points Left":
                st.column_config.NumberColumn(
                    "Points Left",
                    format="%.2f",
                ),
            "Would Win By":
                st.column_config.NumberColumn(
                    "Would Win By",
                    format="%.2f",
                ),
        },
    )


    # ========================================================
    # BIGGEST BENCH MISSES
    # ========================================================

    st.subheader("Biggest Optimization Gaps")

    st.caption(
        "These are the largest differences between actual and "
        "calculated optimal score. A huge optimization gap does "
        "not necessarily mean the decision changed the matchup."
    )

    misses_view = (
        biggest_misses
        .head(15)[
            [
                "year",
                "week",
                "canonical_team",
                "actual_score",
                "optimal_score",
                "points_left_on_bench",
                "actual_win",
                "manager_caused_loss",
            ]
        ]
        .copy()
    )

    misses_view[
        "Result"
    ] = np.where(
        misses_view["actual_win"] == 1,
        "Win",
        "Loss",
    )

    misses_view[
        "Changed Outcome"
    ] = np.where(
        misses_view[
            "manager_caused_loss"
        ] == 1,
        "Yes",
        "No",
    )

    misses_view = misses_view[
        [
            "year",
            "week",
            "canonical_team",
            "actual_score",
            "optimal_score",
            "points_left_on_bench",
            "Result",
            "Changed Outcome",
        ]
    ]

    misses_view = misses_view.rename(
        columns={
            "year": "Year",
            "week": "Week",
            "canonical_team": "Team",
            "actual_score": "Actual",
            "optimal_score": "Optimal",
            "points_left_on_bench":
                "Points Left",
        }
    )

    st.dataframe(
        misses_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Year":
                st.column_config.NumberColumn(
                    "Year",
                    format="%d",
                ),
            "Week":
                st.column_config.NumberColumn(
                    "Week",
                    format="%d",
                ),
            "Team":
                st.column_config.TextColumn(
                    "Team"
                ),
            "Actual":
                st.column_config.NumberColumn(
                    "Actual",
                    format="%.2f",
                ),
            "Optimal":
                st.column_config.NumberColumn(
                    "Optimal",
                    format="%.2f",
                ),
            "Points Left":
                st.column_config.NumberColumn(
                    "Points Left",
                    format="%.2f",
                ),
            "Result":
                st.column_config.TextColumn(
                    "Result"
                ),
            "Changed Outcome":
                st.column_config.TextColumn(
                    "Changed Outcome"
                ),
        },
    )


    # ========================================================
    # SEASON HISTORY
    # ========================================================

    st.subheader("Management by Season")

    st.caption(
        "Season-level lineup efficiency and manager-caused losses."
    )

    season_view = (
        bench_season[
            [
                "year",
                "canonical_team",
                "weeks",
                "actual_losses",
                "manager_caused_losses",
                "manager_caused_loss_rate",
                "avg_points_left_per_week",
                "avg_lineup_efficiency_pct",
            ]
        ]
        .copy()
        .sort_values(
            [
                "year",
                "manager_caused_losses",
            ],
            ascending=[
                False,
                False,
            ],
        )
    )

    season_view[
        "manager_caused_loss_rate"
    ] = (
        season_view[
            "manager_caused_loss_rate"
        ]
        * 100
    )

    season_view = season_view.rename(
        columns={
            "year": "Year",
            "canonical_team": "Franchise",
            "weeks": "Weeks",
            "actual_losses": "Losses",
            "manager_caused_losses":
                "Flippable Losses",
            "manager_caused_loss_rate":
                "% Losses Flippable",
            "avg_points_left_per_week":
                "Avg Points Left",
            "avg_lineup_efficiency_pct":
                "Avg Efficiency",
        }
    )

    st.dataframe(
        season_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Year":
                st.column_config.NumberColumn(
                    "Year",
                    format="%d",
                ),
            "Franchise":
                st.column_config.TextColumn(
                    "Franchise"
                ),
            "Weeks":
                st.column_config.NumberColumn(
                    "Weeks",
                    format="%d",
                ),
            "Losses":
                st.column_config.NumberColumn(
                    "Losses",
                    format="%d",
                ),
            "Flippable Losses":
                st.column_config.NumberColumn(
                    "Flippable Losses",
                    format="%d",
                ),
            "% Losses Flippable":
                st.column_config.NumberColumn(
                    "% Losses Flippable",
                    format="%.1f%%",
                ),
            "Avg Points Left":
                st.column_config.NumberColumn(
                    "Avg Points Left",
                    format="%.2f",
                ),
            "Avg Efficiency":
                st.column_config.NumberColumn(
                    "Avg Efficiency",
                    format="%.1f%%",
                ),
        },
    )


    # ========================================================
    # METHODOLOGY
    # ========================================================

    with st.expander(
        "📖 Methodology & Definitions",
        expanded=False,
    ):

        st.markdown(
            """
            **Optimal Lineup**  
            The highest-scoring legal starting lineup that could
            have been constructed from the players on that team's
            Yahoo roster for that week.

            **Points Left on the Bench**  
            Calculated optimal score minus actual Yahoo team score.
            This measures the optimization gap, not literally only
            players whose Yahoo lineup slot was BN.

            **Manager-Caused Loss / Flippable Loss**  
            A matchup the actual lineup lost where the calculated
            optimal lineup would have scored strictly more than the
            opponent.

            **Lineup Efficiency**  
            Actual team score divided by calculated optimal score.
            Higher values indicate the actual lineup came closer to
            the model's best possible legal lineup.

            **Important Caveat**  
            This is a hindsight-based lineup optimization analysis.
            It shows what was mathematically possible after the games
            were played. It does not account for information managers
            had before kickoff, projections, injuries announced after
            lineup decisions, risk preferences, or reasonable
            uncertainty at the time.

            A "manager-caused loss" therefore means the historical
            result was **flippable by the model's optimal lineup**.
            It is not proof that the manager made an irrational
            decision at the time.
            """
        )