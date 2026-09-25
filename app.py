import json
from pathlib import Path

import pandas as pd
import streamlit as st

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
        }
        return aliases.get(name, name)

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
POWER_FILE = DATA_DIR / "analysis" / "power_rankings_current.csv"
UPCOMING_FILE = DATA_DIR / str(CURRENT_SEASON) / "upcoming_matchups.csv"
NEWS_DIR = DATA_DIR / "news" / str(CURRENT_SEASON)

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
    for col in ["team", "fantasy_team", "opponent", "team_1", "team_2", "left_team", "right_team"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: canonical_team(x) if pd.notna(x) else x)
    return df


def latest_completed_week():
    games = normalize_team_columns(load_csv(MATCHUPS_FILE))
    if games.empty or not {"year", "week"}.issubset(games.columns):
        return None
    games["year"] = pd.to_numeric(games["year"], errors="coerce")
    games["week"] = pd.to_numeric(games["week"], errors="coerce")
    current = games[games["year"].eq(CURRENT_SEASON)].copy()
    if current.empty:
        return None
    # The canonical master contains completed games only.
    return int(current["week"].max())


def current_standings():
    df = normalize_team_columns(load_csv(STANDINGS_FILE))
    if df.empty or "year" not in df.columns:
        return pd.DataFrame()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    out = df[df["year"].eq(CURRENT_SEASON)].copy()
    if out.empty:
        return out
    if "rank" in out.columns:
        out["rank"] = pd.to_numeric(out["rank"], errors="coerce")
        out = out.sort_values(["rank", "team"], kind="stable")
    return out.reset_index(drop=True)


def current_week_games(week):
    df = normalize_team_columns(load_csv(MATCHUPS_FILE))
    if df.empty or week is None:
        return pd.DataFrame()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["week"] = pd.to_numeric(df["week"], errors="coerce")
    return df[df["year"].eq(CURRENT_SEASON) & df["week"].eq(week)].copy()


def week_snapshot(games):
    if games.empty or not {"team_1", "team_2", "team_1_score", "team_2_score"}.issubset(games.columns):
        return None
    g = games.copy()
    g["team_1_score"] = pd.to_numeric(g["team_1_score"], errors="coerce")