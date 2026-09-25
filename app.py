import streamlit as st
import pandas as pd
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
            "Ginger FC": "Ginger FC 🏆🏆",
            "Ginger FC Trophy Trophy": "Ginger FC 🏆🏆",
        }
        return aliases.get(str(name).strip(), str(name).strip())


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Malle Is The Worst Commissioner",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

STANDINGS_FILE = DATA_DIR / "all_standings.csv"
MATCHUPS_FILE = DATA_DIR / "all_matchups_clean.csv"

POWER_FILE = (
    DATA_DIR
    / "analysis"
    / "power_rankings_current.csv"
)

UPCOMING_FILE = (
    DATA_DIR
    / str(CURRENT_SEASON)
    / "upcoming_matchups.csv"
)

CHAMPIONSHIPS_FILE = (
    DATA_DIR
    / "playoffs"
    / "championships.csv"
)


# ============================================================
# DATA HELPERS
# ============================================================

@st.cache_data
def load_csv(path):
    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def normalize_team(value):
    if pd.isna(value):
        return value

    return canonical_team(
        str(value).strip()
    )


def normalize_team_columns(df):
    df = df.copy()

    team_columns = [
        "team",
        "fantasy_team",
        "opponent",
        "team_1",
        "team_2",
        "left_team",
        "right_team",
        "winner",
        "loser",
        "champion",
        "runner_up",
    ]

    for col in team_columns:
        if col in df.columns:
            df[col] = df[col].apply(
                normalize_team
            )

    return df


def numeric(series):
    return pd.to_numeric(
        series,
        errors="coerce",
    )


# ============================================================
# LATEST COMPLETED WEEK
# ============================================================

def get_latest_completed_week():
    games = normalize_team_columns(
        load_csv(MATCHUPS_FILE)
    )

    if games.empty:
        return None

    if not {"year", "week"}.issubset(
        games.columns
    ):
        return None

    games["year"] = numeric(
        games["year"]
    )

    games["week"] = numeric(
        games["week"]
    )

    current = games[
        games["year"].eq(
            CURRENT_SEASON
        )
    ].copy()

    if current.empty:
        return None

    # Canonical matchup master only contains
    # completed current-season games.
    counts = (
        current
        .dropna(subset=["week"])
        .groupby("week")
        .size()
    )

    complete = counts[
        counts >= 6
    ]

    if complete.empty:
        return None

    return int(
        complete.index.max()
    )


# ============================================================
# CURRENT STANDINGS
# ============================================================

def get_current_standings():
    standings = normalize_team_columns(
        load_csv(STANDINGS_FILE)
    )

    if standings.empty:
        return pd.DataFrame()

    if "year" not in standings.columns:
        return pd.DataFrame()

    standings["year"] = numeric(
        standings["year"]
    )

    current = standings[
        standings["year"].eq(
            CURRENT_SEASON
        )
    ].copy()

    if current.empty:
        return pd.DataFrame()

    if "rank" in current.columns:
        current["rank"] = numeric(
            current["rank"]
        )

        current = current.sort_values(
            ["rank", "team"],
            kind="stable",
        )

    return current.reset_index(
        drop=True
    )


# ============================================================
# WEEKLY SNAPSHOT
# ============================================================

def get_week_snapshot(week):
    if week is None:
        return None

    games = normalize_team_columns(
        load_csv(MATCHUPS_FILE)
    )

    required = {
        "year",
        "week",
        "team_1",
        "team_2",
        "team_1_score",
        "team_2_score",
    }

    if (
        games.empty
        or not required.issubset(
            games.columns
        )
    ):
        return None

    games["year"] = numeric(
        games["year"]
    )

    games["week"] = numeric(
        games["week"]
    )

    games["team_1_score"] = numeric(
        games["team_1_score"]
    )

    games["team_2_score"] = numeric(
        games["team_2_score"]
    )

    week_games = games[
        games["year"].eq(
            CURRENT_SEASON
        )
        & games["week"].eq(
            week
        )
    ].copy()

    week_games = week_games.dropna(
        subset=[
            "team_1_score",
            "team_2_score",
        ]
    )

    if week_games.empty:
        return None

    performances = []

    for row in week_games.itertuples():
        performances.append(
            {
                "team": row.team_1,
                "score": float(
                    row.team_1_score
                ),
            }
        )

        performances.append(
            {
                "team": row.team_2,
                "score": float(
                    row.team_2_score
                ),
            }
        )

    performances = pd.DataFrame(
        performances
    )

    high = performances.loc[
        performances["score"].idxmax()
    ]

    low = performances.loc[
        performances["score"].idxmin()
    ]

    week_games["margin"] = (
        week_games["team_1_score"]
        - week_games["team_2_score"]
    ).abs()

    closest = week_games.loc[
        week_games["margin"].idxmin()
    ]

    biggest = week_games.loc[
        week_games["margin"].idxmax()
    ]

    def winner_loser(row):
        if (
            row["team_1_score"]
            >= row["team_2_score"]
        ):
            return (
                row["team_1"],
                row["team_1_score"],
                row["team_2"],
                row["team_2_score"],
            )

        return (
            row["team_2"],
            row["team_2_score"],
            row["team_1"],
            row["team_1_score"],
        )

    biggest_result = winner_loser(
        biggest
    )

    return {
        "high_team": high["team"],
        "high_score": float(
            high["score"]
        ),
        "low_team": low["team"],
        "low_score": float(
            low["score"]
        ),
        "closest_team_1": closest[
            "team_1"
        ],
        "closest_score_1": float(
            closest["team_1_score"]
        ),
        "closest_team_2": closest[
            "team_2"
        ],
        "closest_score_2": float(
            closest["team_2_score"]
        ),
        "closest_margin": float(
            closest["margin"]
        ),
        "biggest_winner": biggest_result[
            0
        ],
        "biggest_winner_score": float(
            biggest_result[1]
        ),
        "biggest_loser": biggest_result[
            2
        ],
        "biggest_loser_score": float(
            biggest_result[3]
        ),
        "biggest_margin": float(
            biggest["margin"]
        ),
    }


# ============================================================
# POWER RANKINGS
# ============================================================

def get_power_rankings():
    power = normalize_team_columns(
        load_csv(POWER_FILE)
    )

    if power.empty:
        return pd.DataFrame()

    if "year" in power.columns:
        power["year"] = numeric(
            power["year"]
        )

        power = power[
            power["year"].eq(
                CURRENT_SEASON
            )
        ].copy()

    if power.empty:
        return pd.DataFrame()

    if "power_rank" in power.columns:
        power["power_rank"] = numeric(
            power["power_rank"]
        )

        power = power.sort_values(
            "power_rank"
        )

    return power.reset_index(
        drop=True
    )


# ============================================================
# UPCOMING MATCHUPS
# ============================================================

def get_upcoming_matchups(latest_week):
    upcoming = normalize_team_columns(
        load_csv(UPCOMING_FILE)
    )

    if upcoming.empty:
        return pd.DataFrame(), None

    if "year" in upcoming.columns:
        upcoming["year"] = numeric(
            upcoming["year"]
        )

        upcoming = upcoming[
            upcoming["year"].eq(
                CURRENT_SEASON
            )
        ].copy()

    if upcoming.empty:
        return pd.DataFrame(), None

    if "week" in upcoming.columns:
        upcoming["week"] = numeric(
            upcoming["week"]
        )

        if latest_week is not None:
            future = upcoming[
                upcoming["week"]
                > latest_week
            ].copy()
        else:
            future = upcoming.copy()

        if future.empty:
            return pd.DataFrame(), None

        next_week = int(
            future["week"].min()
        )

        future = future[
            future["week"].eq(
                next_week
            )
        ].copy()

        return (
            future.reset_index(
                drop=True
            ),
            next_week,
        )

    return (
        upcoming.reset_index(
            drop=True
        ),
        (
            latest_week + 1
            if latest_week
            is not None
            else None
        ),
    )


# ============================================================
# CHAMPION
# ============================================================

def get_latest_champion():
    championships = normalize_team_columns(
        load_csv(CHAMPIONSHIPS_FILE)
    )

    if (
        championships.empty
        or not {
            "year",
            "champion",
        }.issubset(
            championships.columns
        )
    ):
        return None, None

    championships["year"] = numeric(
        championships["year"]
    )

    championships = (
        championships
        .dropna(
            subset=[
                "year",
                "champion",
            ]
        )
        .sort_values(
            "year"
        )
    )

    if championships.empty:
        return None, None

    latest = championships.iloc[-1]

    return (
        int(latest["year"]),
        latest["champion"],
    )


# ============================================================
# LOAD CURRENT STATE
# ============================================================

latest_week = (
    get_latest_completed_week()
)

standings = (
    get_current_standings()
)

snapshot = (
    get_week_snapshot(
        latest_week
    )
)

power = (
    get_power_rankings()
)

upcoming, upcoming_week = (
    get_upcoming_matchups(
        latest_week
    )
)

champion_year, champion = (
    get_latest_champion()
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1400px;
    }

    .league-title {
        font-size: 2.45rem;
        font-weight: 900;
        text-align: center;
        margin-bottom: 0.15rem;
    }

    .league-subtitle {
        text-align: center;
        font-size: 1.05rem;
        opacity: 0.72;
        margin-bottom: 0.4rem;
    }

    .week-label {
        text-align: center;
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 1.6rem;
    }

    .section-title {
        font-size: 1.55rem;
        font-weight: 850;
        margin-top: 1.6rem;
        margin-bottom: 0.7rem;
    }

    .story-card {
        border: 1px solid rgba(
            128,
            128,
            128,
            0.28
        );
        border-radius: 0.65rem;
        padding: 1rem;
        margin-bottom: 0.7rem;
    }

    .story-title {
        font-weight: 800;
        font-size: 1.02rem;
        margin-bottom: 0.25rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("🏈 League Menu")

    st.markdown("---")

    st.markdown("### Current Season")
    st.markdown(
        f"**{CURRENT_SEASON}**"
    )

    if latest_week is not None:
        st.caption(
            f"Current through Week "
            f"{latest_week}"
        )

    st.markdown("---")

    st.markdown("### League History")
    st.markdown(
        f"2017 → {CURRENT_SEASON}"
    )

    st.markdown("---")

    st.caption(
        "An unofficial archive of the "
        "greatest fantasy football league "
        "ever assembled."
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="league-title">'
    '🏈 MALLE IS THE WORST COMMISSIONER'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="league-subtitle">'
    'League HQ'
    '</div>',
    unsafe_allow_html=True,
)

if latest_week is not None:
    st.markdown(
        f'<div class="week-label">'
        f'{CURRENT_SEASON} • '
        f'Through Week {latest_week}'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="week-label">'
        f'{CURRENT_SEASON}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# LEAGUE AT A GLANCE
# ============================================================

leader = None
points_leader = None
power_leader = None

if not standings.empty:
    leader = standings.iloc[0]

    if "points_for" in standings.columns:
        temp = standings.copy()

        temp["points_for"] = numeric(
            temp["points_for"]
        )

        valid = temp.dropna(
            subset=["points_for"]
        )

        if not valid.empty:
            points_leader = valid.loc[
                valid["points_for"].idxmax()
            ]

if not power.empty:
    power_leader = power.iloc[0]


metric1, metric2, metric3, metric4 = (
    st.columns(4)
)

if leader is not None:
    metric1.metric(
        "League Leader",
        str(leader["team"]),
        (
            str(leader["record"])
            if "record"
            in leader.index
            else None
        ),
    )
else:
    metric1.metric(
        "League Leader",
        "—",
    )

if points_leader is not None:
    metric2.metric(
        "Points Leader",
        str(
            points_leader["team"]
        ),
        f"{float(points_leader['points_for']):.2f} PF",
    )
else:
    metric2.metric(
        "Points Leader",
        "—",
    )

if power_leader is not None:
    metric3.metric(
        "Power #1",
        str(
            power_leader[
                "fantasy_team"
            ]
        ),
        (
            f"{float(power_leader['power_score']):.2f} score"
            if "power_score"
            in power_leader.index
            else None
        ),
    )
else:
    metric3.metric(
        "Power #1",
        "—",
    )

if snapshot is not None:
    metric4.metric(
        f"Week {latest_week} High",
        snapshot[
            "high_team"
        ],
        f"{snapshot['high_score']:.2f} pts",
    )
elif champion is not None:
    metric4.metric(
        f"{champion_year} Champion",
        champion,
    )
else:
    metric4.metric(
        "Latest Champion",
        "—",
    )


st.divider()


# ============================================================
# CURRENT STANDINGS
# ============================================================

st.markdown(
    f'<div class="section-title">'
    f'🏆 {CURRENT_SEASON} Standings'
    f'</div>',
    unsafe_allow_html=True,
)

if standings.empty:
    st.warning(
        "Current-season standings "
        "are not available."
    )
else:
    display = standings.copy()

    rename_map = {
        "rank": "RK",
        "team": "TEAM",
        "record": "RECORD",
        "points_for": "PF",
    }

    display = display.rename(
        columns={
            key: value
            for key, value
            in rename_map.items()
            if key in display.columns
        }
    )

    wanted = [
        col
        for col in [
            "RK",
            "TEAM",
            "RECORD",
            "PF",
        ]
        if col in display.columns
    ]

    display = display[
        wanted
    ].copy()

    if "RK" in display.columns:
        display["RK"] = (
            numeric(
                display["RK"]
            )
            .astype("Int64")
        )

    if "PF" in display.columns:
        display["PF"] = (
            numeric(
                display["PF"]
            )
            .round(2)
        )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Full standings and additional "
        "season detail are available on "
        "the Standings page."
    )


# ============================================================
# WEEK SNAPSHOT
# ============================================================

if snapshot is not None:
    st.markdown(
        f'<div class="section-title">'
        f'🔥 Week {latest_week} Snapshot'
        f'</div>',
        unsafe_allow_html=True,
    )

    snap1, snap2, snap3, snap4 = (
        st.columns(4)
    )

    snap1.metric(
        "High Score",
        snapshot[
            "high_team"
        ],
        f"{snapshot['high_score']:.2f}",
    )

    snap2.metric(
        "Low Score",
        snapshot[
            "low_team"
        ],
        f"{snapshot['low_score']:.2f}",
    )

    snap3.metric(
        "Closest Game",
        f"{snapshot['closest_margin']:.2f} pts",
        (
            f"{snapshot['closest_team_1']} "
            f"{snapshot['closest_score_1']:.2f} – "
            f"{snapshot['closest_team_2']} "
            f"{snapshot['closest_score_2']:.2f}"
        ),
    )

    snap4.metric(
        "Biggest Win",
        snapshot[
            "biggest_winner"
        ],
        (
            f"+{snapshot['biggest_margin']:.2f} "
            f"vs {snapshot['biggest_loser']}"
        ),
    )


# ============================================================
# POWER RANKINGS
# ============================================================

st.markdown(
    '<div class="section-title">'
    '⚡ Power Rankings'
    '</div>',
    unsafe_allow_html=True,
)

if power.empty:
    st.caption(
        "Current power rankings "
        "are not available."
    )
else:
    top_power = power.head(
        5
    ).copy()

    rows = []

    for row in top_power.itertuples():
        rank = int(
            row.power_rank
        )

        previous = getattr(
            row,
            "previous_rank",
            None,
        )

        change = getattr(
            row,
            "rank_change",
            0,
        )

        if pd.isna(change):
            change = 0

        change = int(change)

        if change > 0:
            movement = f"▲ {change}"
        elif change < 0:
            movement = f"▼ {abs(change)}"
        else:
            movement = "—"

        rows.append(
            {
                "RK": rank,
                "TEAM": row.fantasy_team,
                "MOVE": movement,
                "RECORD": getattr(
                    row,
                    "record",
                    "",
                ),
                "SCORE": round(
                    float(
                        getattr(
                            row,
                            "power_score",
                            0,
                        )
                    ),
                    2,
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

    if (
        "through_week"
        in power.columns
        and not power.empty
    ):
        power_week = int(
            numeric(
                power[
                    "through_week"
                ]
            ).max()
        )

        st.caption(
            f"Power Rankings current "
            f"through Week {power_week}. "
            f"See the full Power Rankings "
            f"page for all 12 teams."
        )


# ============================================================
# AROUND THE LEAGUE
# ============================================================

if snapshot is not None:
    st.markdown(
        '<div class="section-title">'
        '📰 Around the League'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="story-card">
            <div class="story-title">
                🏁 Game of the Week
            </div>
            {snapshot['closest_team_1']}
            {snapshot['closest_score_1']:.2f}
            and
            {snapshot['closest_team_2']}
            {snapshot['closest_score_2']:.2f}
            were separated by only
            <b>{snapshot['closest_margin']:.2f}
            points</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="story-card">
            <div class="story-title">
                💥 Biggest Beatdown
            </div>
            <b>{snapshot['biggest_winner']}</b>
            beat
            {snapshot['biggest_loser']}
            {snapshot['biggest_winner_score']:.2f}
            –
            {snapshot['biggest_loser_score']:.2f},
            a margin of
            <b>{snapshot['biggest_margin']:.2f}
            points</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if (
        leader is not None
        and points_leader is not None
    ):
        st.markdown(
            f"""
            <div class="story-card">
                <div class="story-title">
                    📈 Early Season Check
                </div>
                <b>{leader['team']}</b>
                currently sits atop the
                standings, while
                <b>{points_leader['team']}</b>
                leads the league with
                <b>{float(points_leader['points_for']):.2f}
                points</b>.
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# UPCOMING MATCHUPS
# ============================================================

if not upcoming.empty:
    title_week = (
        upcoming_week
        if upcoming_week is not None
        else "Upcoming"
    )

    st.markdown(
        f'<div class="section-title">'
        f'📅 Week {title_week} Matchups'
        f'</div>',
        unsafe_allow_html=True,
    )

    left_col = None
    right_col = None

    for candidate in [
        "team_1",
        "left_team",
        "team1",
        "team_a",
    ]:
        if candidate in upcoming.columns:
            left_col = candidate
            break

    for candidate in [
        "team_2",
        "right_team",
        "team2",
        "team_b",
    ]:
        if candidate in upcoming.columns:
            right_col = candidate
            break

    if (
        left_col is not None
        and right_col is not None
    ):
        matchup_rows = []

        for row in upcoming.itertuples(
            index=False
        ):
            row_dict = row._asdict()

            matchup_rows.append(
                {
                    "MATCHUP": (
                        f"{row_dict[left_col]}"
                        f"  vs.  "
                        f"{row_dict[right_col]}"
                    )
                }
            )

        st.dataframe(
            pd.DataFrame(
                matchup_rows
            ),
            use_container_width=True,
            hide_index=True,
        )

    else:
        # If Yahoo changes the column names,
        # still show the collected upcoming data
        # rather than failing the homepage.
        st.dataframe(
            upcoming,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

footer_text = (
    f"Malle Is The Worst Commissioner "
    f"• Est. 2017 • {CURRENT_SEASON}"
)

if latest_week is not None:
    footer_text += (
        f" data current through "
        f"Week {latest_week}"
    )

st.caption(
    footer_text
)
