import streamlit as st
import pandas as pd
from pathlib import Path

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


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Malle Is The Worst Commissioner",
    page_icon="🏈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).resolve().parent

CURRENT_SEASON = 2026

CURRENT_TEAMS = [
    "malle_dips_pouches",
    "Patty Primetimes",
    "Joe Mantegna",
    "Malle ❤️ 🐸",
    "Buttermilk Puuump",
    "ThreatLevelMidnight",
    "The Big Gronkowski",
    "Pop Lockett Drop it",
    "Voldemort",
    "Post Mahomes",
    "Uncle Rico",
    "Ginger FC",
]

STANDINGS_FILE = BASE_DIR / "data" / "all_standings.csv"
MATCHUPS_FILE = BASE_DIR / "data" / "all_matchups_clean_2017_2025.csv"
CHAMPIONSHIPS_FILE = BASE_DIR / "data" / "playoffs" / "championships.csv"


# ---------------------------------------------------------
# DATA HELPERS
# ---------------------------------------------------------

@st.cache_data
def load_csv(path):
    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def normalize_team_columns(df):
    df = df.copy()

    for col in [
        "team",
        "fantasy_team",
        "opponent",
        "champion",
        "runner_up",
    ]:
        if col in df.columns:
            df[col] = df[col].apply(canonical_team)

    return df


def current_standings():
    # 2026 has not started yet. Show the real league field at 0-0
    # instead of attempting to interpret incomplete/future standings rows.
    return pd.DataFrame(
        {
            "Rank": range(1, len(CURRENT_TEAMS) + 1),
            "Team": CURRENT_TEAMS,
            "W": 0,
            "L": 0,
            "T": 0,
            "PF": 0.0,
            "PA": 0.0,
        }
    )


def latest_completed_standings():
    standings = normalize_team_columns(load_csv(STANDINGS_FILE))

    if standings.empty or "year" not in standings.columns:
        return pd.DataFrame(), None

    standings["year"] = pd.to_numeric(
        standings["year"],
        errors="coerce",
    )

    completed = standings[
        standings["year"] < CURRENT_SEASON
    ].copy()

    if completed.empty:
        return pd.DataFrame(), None

    year = int(completed["year"].max())
    latest = completed[completed["year"] == year].copy()

    if "rank" in latest.columns:
        latest["rank"] = pd.to_numeric(
            latest["rank"],
            errors="coerce",
        )
        latest = latest.sort_values(
            ["rank", "team"],
            ascending=[True, True],
        )
    elif {"wins", "points_for"}.issubset(latest.columns):
        latest["wins"] = pd.to_numeric(
            latest["wins"],
            errors="coerce",
        )
        latest["points_for"] = pd.to_numeric(
            latest["points_for"],
            errors="coerce",
        )
        latest = latest.sort_values(
            ["wins", "points_for"],
            ascending=[False, False],
        )

    return latest.reset_index(drop=True), year


def league_records():
    games = normalize_team_columns(load_csv(MATCHUPS_FILE))

    if games.empty:
        return None

    # Support either team-row or matchup-row clean schemas.
    if {"team_score", "opponent_score"}.issubset(games.columns):
        team_score = pd.to_numeric(
            games["team_score"],
            errors="coerce",
        )
        opp_score = pd.to_numeric(
            games["opponent_score"],
            errors="coerce",
        )

        scores = team_score.dropna()
        margins = (team_score - opp_score).abs().dropna()

    elif {"team_1_score", "team_2_score"}.issubset(games.columns):
        s1 = pd.to_numeric(
            games["team_1_score"],
            errors="coerce",
        )
        s2 = pd.to_numeric(
            games["team_2_score"],
            errors="coerce",
        )

        scores = pd.concat([s1, s2]).dropna()
        margins = (s1 - s2).abs().dropna()

    else:
        return None

    if scores.empty or margins.empty:
        return None

    return {
        "high": float(scores.max()),
        "low": float(scores.min()),
        "blowout": float(margins.max()),
    }


standings = current_standings()
latest_standings, latest_year = latest_completed_standings()
records = league_records()


# ---------------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------------

st.markdown(
    """
    <style>

    .main-title {
        font-size: 2.5rem;
        font-weight: 900;
        text-align: center;
        margin-bottom: 0;
    }

    .subtitle {
        text-align: center;
        font-size: 1.2rem;
        font-style: italic;
        margin-bottom: 2rem;
    }

    .section-title {
        font-size: 1.8rem;
        font-weight: 800;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:

    st.title("🏈 League Menu")

    st.markdown("---")

    st.markdown("### Current Season")
    st.markdown(f"**{CURRENT_SEASON}**")

    st.markdown("---")

    st.markdown("### League History")
    st.markdown(f"2017 → {CURRENT_SEASON}")

    st.markdown("---")

    st.caption(
        "An unofficial archive of the greatest "
        "fantasy football league ever assembled."
    )


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.markdown(
    '<div class="main-title">🏈 MALLE IS THE WORST COMMISSIONER</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'The official unofficial history of a league that somehow survived since 2017.'
    '</div>',
    unsafe_allow_html=True,
)

st.divider()


# ---------------------------------------------------------
# TOP METRICS
# ---------------------------------------------------------

completed_seasons = (
    int(latest_year) - 2017 + 1
    if latest_year is not None
    else 0
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Teams", len(CURRENT_TEAMS))
col2.metric("Completed Seasons", completed_seasons)
col3.metric("Current Season", CURRENT_SEASON)

if latest_year is not None:
    championships = normalize_team_columns(load_csv(CHAMPIONSHIPS_FILE))
    latest_champion = "—"

    if (
        not championships.empty
        and {"year", "champion"}.issubset(championships.columns)
    ):
        championships["year"] = pd.to_numeric(
            championships["year"],
            errors="coerce",
        )
        row = championships[
            championships["year"] == latest_year
        ]

        if not row.empty:
            latest_champion = str(row.iloc[0]["champion"])

    col4.metric(
        f"{latest_year} Champion",
        latest_champion,
    )
else:
    col4.metric("Latest Champion", "—")


# ---------------------------------------------------------
# CURRENT STANDINGS
# ---------------------------------------------------------

st.markdown(
    f'<div class="section-title">🏆 {CURRENT_SEASON} STANDINGS</div>',
    unsafe_allow_html=True,
)

st.caption(
    "The 2026 regular season has not started yet. "
    "These are the actual 12 franchises, shown at 0-0."
)

display_cols = [
    col
    for col in ["Rank", "Team", "W", "L", "T", "PF", "PA"]
    if col in standings.columns
]

display_standings = standings[display_cols].copy()

for col in ["PF", "PA"]:
    if col in display_standings.columns:
        display_standings[col] = (
            pd.to_numeric(
                display_standings[col],
                errors="coerce",
            )
            .fillna(0)
            .round(1)
        )

st.dataframe(
    display_standings,
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# LATEST COMPLETED SEASON
# ---------------------------------------------------------

if not latest_standings.empty and latest_year is not None:

    st.markdown(
        f'<div class="section-title">📊 {latest_year} FINAL REGULAR-SEASON STANDINGS</div>',
        unsafe_allow_html=True,
    )

    latest_display = latest_standings.copy()

    rename_map = {
        "rank": "Rank",
        "team": "Team",
        "record": "Record",
        "wins": "W",
        "losses": "L",
        "ties": "T",
        "points_for": "PF",
        "points_against": "PA",
    }

    latest_display = latest_display.rename(
        columns={
            key: value
            for key, value in rename_map.items()
            if key in latest_display.columns
        }
    )

    wanted = [
        col
        for col in [
            "Rank",
            "Team",
            "Record",
            "W",
            "L",
            "T",
            "PF",
            "PA",
        ]
        if col in latest_display.columns
    ]

    st.dataframe(
        latest_display[wanted],
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------
# LEAGUE RECORDS
# ---------------------------------------------------------

st.markdown(
    '<div class="section-title">📊 LEAGUE RECORDS</div>',
    unsafe_allow_html=True,
)

if records is None:
    st.caption(
        "Historical matchup data is not available on this deployment."
    )
else:
    record_col1, record_col2, record_col3 = st.columns(3)

    record_col1.metric(
        "Highest Single-Week Score",
        f"{records['high']:.2f}",
    )

    record_col2.metric(
        "Lowest Single-Week Score",
        f"{records['low']:.2f}",
    )

    record_col3.metric(
        "Biggest Blowout",
        f"{records['blowout']:.2f} pts",
    )


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    "Malle Is The Worst Commissioner • Est. 2017 • "
    "Historical data updates from the league archive"
)