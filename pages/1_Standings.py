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


st.set_page_config(
    page_title="2026 Standings",
    page_icon="🏆",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent.parent
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


@st.cache_data
def load_standings():
    if not STANDINGS_FILE.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(STANDINGS_FILE)
    except Exception:
        return pd.DataFrame()


def normalize_standings(df):
    df = df.copy()

    if "team" in df.columns:
        df["team"] = df["team"].apply(canonical_team)

    if "year" in df.columns:
        df["year"] = pd.to_numeric(
            df["year"],
            errors="coerce",
        )

    return df


all_standings = normalize_standings(load_standings())

st.title("🏆 2026 Standings")

current = pd.DataFrame(
    {
        "Rank": range(1, len(CURRENT_TEAMS) + 1),
        "Team": CURRENT_TEAMS,
        "Wins": 0,
        "Losses": 0,
    }
)

st.caption(
    "The 2026 regular season has not started yet. "
    "All 12 current franchises are shown at 0-0."
)

display_cols = [
    "Rank",
    "Team",
    "Wins",
    "Losses",
]

st.dataframe(
    current[display_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rank": st.column_config.NumberColumn(
            "Rank",
            format="%d",
            width="small",
        ),
        "Team": st.column_config.TextColumn(
            "Franchise",
            width="large",
        ),
        "Wins": st.column_config.NumberColumn(
            "W",
            format="%d",
            width="small",
        ),
        "Losses": st.column_config.NumberColumn(
            "L",
            format="%d",
            width="small",
        ),
    },
)

st.divider()

# ---------------------------------------------------------
# LATEST COMPLETED SEASON
# ---------------------------------------------------------

if not all_standings.empty and "year" in all_standings.columns:

    completed = all_standings[
        all_standings["year"] < CURRENT_SEASON
    ].copy()

    if not completed.empty:

        latest_year = int(completed["year"].max())

        latest = completed[
            completed["year"] == latest_year
        ].copy()

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

        st.subheader(
            f"📚 {latest_year} Final Regular-Season Standings"
        )

        st.caption(
            "The most recent completed season is shown for context "
            "until 2026 games begin."
        )

        latest = latest.rename(
            columns={
                "rank": "Rank",
                "team": "Team",
                "record": "Record",
                "wins": "Wins",
                "losses": "Losses",
                "ties": "Ties",
                "points_for": "Points For",
                "points_against": "Points Against",
            }
        )

        latest_cols = [
            col
            for col in [
                "Rank",
                "Team",
                "Record",
                "Wins",
                "Losses",
                "Ties",
                "Points For",
                "Points Against",
            ]
            if col in latest.columns
        ]

        st.dataframe(
            latest[latest_cols],
            use_container_width=True,
            hide_index=True,
        )