import streamlit as st
import pandas as pd
from pathlib import Path

from season_config import (
    CURRENT_SEASON,
    LAST_COMPLETED_SEASON,
)

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
    page_title=f"{CURRENT_SEASON} Standings",
    page_icon="🏆",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent.parent

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

st.title(f"🏆 {CURRENT_SEASON} Standings")

current = pd.DataFrame()

if not all_standings.empty and "year" in all_standings.columns:
    current = all_standings[
        all_standings["year"] == CURRENT_SEASON
    ].copy()

if not current.empty:
    if "rank" in current.columns:
        current["rank"] = pd.to_numeric(
            current["rank"],
            errors="coerce",
        )
        current = current.sort_values(
            ["rank", "team"],
            ascending=[True, True],
        )
    elif {"wins", "points_for"}.issubset(current.columns):
        current["wins"] = pd.to_numeric(
            current["wins"],
            errors="coerce",
        )
        current["points_for"] = pd.to_numeric(
            current["points_for"],
            errors="coerce",
        )
        current = current.sort_values(
            ["wins", "points_for"],
            ascending=[False, False],
        )

    current = current.rename(
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

    display_cols = [
        col
        for col in [
            "Rank", "Team", "Record", "Wins", "Losses",
            "Ties", "Points For", "Points Against",
        ]
        if col in current.columns
    ]

    st.caption(
        f"Live {CURRENT_SEASON} standings from the league standings data."
    )

    st.dataframe(
        current[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", format="%d", width="small"),
            "Team": st.column_config.TextColumn("Franchise", width="large"),
            "Wins": st.column_config.NumberColumn("W", format="%d", width="small"),
            "Losses": st.column_config.NumberColumn("L", format="%d", width="small"),
            "Ties": st.column_config.NumberColumn("T", format="%d", width="small"),
        },
    )
else:
    current = pd.DataFrame(
        {
            "Rank": range(1, len(CURRENT_TEAMS) + 1),
            "Team": CURRENT_TEAMS,
            "Wins": 0,
            "Losses": 0,
        }
    )

    st.caption(
        f"{CURRENT_SEASON} is the active league season. "
        "Yahoo has not supplied current-season standings yet, "
        "so the 12 active franchises are shown at 0-0 until standings data is available."
    )

    st.dataframe(
        current,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", format="%d", width="small"),
            "Team": st.column_config.TextColumn("Franchise", width="large"),
            "Wins": st.column_config.NumberColumn("W", format="%d", width="small"),
            "Losses": st.column_config.NumberColumn("L", format="%d", width="small"),
        },
    )
