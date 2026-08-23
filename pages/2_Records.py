from pathlib import Path

import pandas as pd
import streamlit as st


# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------

st.set_page_config(
    page_title="Records | Malle Is The Worst Commissioner",
    page_icon="🏆",
    layout="wide",
)


# ---------------------------------------------------------
# FILE PATHS
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

HISTORY_DIR = BASE_DIR / "data" / "history"

ALL_TIME_FILE = HISTORY_DIR / "all_time_records.csv"
TEAM_GAMES_FILE = HISTORY_DIR / "team_games.csv"
HIGHEST_FILE = HISTORY_DIR / "highest_scores.csv"
LOWEST_FILE = HISTORY_DIR / "lowest_scores.csv"
BLOWOUT_FILE = HISTORY_DIR / "biggest_blowouts.csv"
CLOSEST_FILE = HISTORY_DIR / "closest_games.csv"


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

@st.cache_data
def load_data():

    all_time = pd.read_csv(ALL_TIME_FILE)
    team_games = pd.read_csv(TEAM_GAMES_FILE)
    highest = pd.read_csv(HIGHEST_FILE)
    lowest = pd.read_csv(LOWEST_FILE)
    blowouts = pd.read_csv(BLOWOUT_FILE)
    closest = pd.read_csv(CLOSEST_FILE)

    return (
        all_time,
        team_games,
        highest,
        lowest,
        blowouts,
        closest,
    )


try:

    (
        all_time,
        team_games,
        highest,
        lowest,
        blowouts,
        closest,
    ) = load_data()

except FileNotFoundError:

    st.error(
        "Historical record files were not found. "
        "Run `python build_league_history.py` first."
    )

    st.stop()


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def format_record(row):

    if row["ties"] > 0:
        return (
            f"{int(row['wins'])}-"
            f"{int(row['losses'])}-"
            f"{int(row['ties'])}"
        )

    return (
        f"{int(row['wins'])}-"
        f"{int(row['losses'])}"
    )


def score_display(row):

    return (
        f"{row['team']} "
        f"{row['points_for']:.2f} — "
        f"{row['opponent']} "
        f"{row['points_against']:.2f}"
    )


# ---------------------------------------------------------
# TITLE
# ---------------------------------------------------------

st.title("🏆 League Records")

st.caption(
    "Regular-season records from Yahoo Fantasy matchups, "
    "2018–2025."
)

st.divider()


# =========================================================
# LEAGUE RECORD CARDS
# =========================================================

highest_game = (
    team_games
    .sort_values(
        "points_for",
        ascending=False,
    )
    .iloc[0]
)

lowest_game = (
    team_games
    .sort_values(
        "points_for",
        ascending=True,
    )
    .iloc[0]
)

highest_loss = (
    team_games[
        team_games["result"] == "L"
    ]
    .sort_values(
        "points_for",
        ascending=False,
    )
    .iloc[0]
)

lowest_win = (
    team_games[
        team_games["result"] == "W"
    ]
    .sort_values(
        "points_for",
        ascending=True,
    )
    .iloc[0]
)


col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Highest Score",
        f"{highest_game['points_for']:.2f}",
        highest_game["team"],
    )

with col2:

    st.metric(
        "Lowest Score",
        f"{lowest_game['points_for']:.2f}",
        lowest_game["team"],
    )

with col3:

    st.metric(
        "Highest Score in a Loss",
        f"{highest_loss['points_for']:.2f}",
        highest_loss["team"],
    )

with col4:

    st.metric(
        "Lowest Winning Score",
        f"{lowest_win['points_for']:.2f}",
        lowest_win["team"],
    )


st.divider()


# =========================================================
# ALL-TIME STANDINGS
# =========================================================

st.header("All-Time Regular-Season Standings")


standings = all_time.copy()


# ---------------------------------------------------------
# RE-RANK USING:
#
# 1. Win percentage
# 2. Point differential
# 3. Points scored
#
# This fixes exact W-L ties such as
# Voldemort vs ThreatLevelMidnight.
# ---------------------------------------------------------

standings = standings.sort_values(
    [
        "win_pct",
        "point_diff",
        "points_for",
    ],
    ascending=[
        False,
        False,
        False,
    ],
).reset_index(drop=True)


standings["Rank"] = (
    standings.index + 1
)

standings["Record"] = (
    standings.apply(
        format_record,
        axis=1,
    )
)

standings["Win %"] = (
    standings["win_pct"] * 100
).round(1)

standings["PF"] = (
    standings["points_for"]
    .round(2)
)

standings["PA"] = (
    standings["points_against"]
    .round(2)
)

standings["Diff"] = (
    standings["point_diff"]
    .round(2)
)

standings["PPG"] = (
    standings["avg_points"]
    .round(2)
)


display_standings = standings[
    [
        "Rank",
        "team",
        "seasons",
        "Record",
        "Win %",
        "PF",
        "PA",
        "Diff",
        "PPG",
    ]
].rename(
    columns={
        "team": "Franchise",
        "seasons": "Seasons",
    }
)


st.dataframe(
    display_standings,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Rank": st.column_config.NumberColumn(
            "Rank",
            format="%d",
        ),
        "Seasons": st.column_config.NumberColumn(
            "Seasons",
            format="%d",
        ),
        "Win %": st.column_config.NumberColumn(
            "Win %",
            format="%.1f%%",
        ),
        "PF": st.column_config.NumberColumn(
            "Points For",
            format="%.2f",
        ),
        "PA": st.column_config.NumberColumn(
            "Points Against",
            format="%.2f",
        ),
        "Diff": st.column_config.NumberColumn(
            "Point Diff",
            format="%.2f",
        ),
        "PPG": st.column_config.NumberColumn(
            "PPG",
            format="%.2f",
        ),
    },
)


st.caption(
    "Historical team-name changes are grouped by franchise. "
    "Replacement owners remain separate franchises."
)


st.divider()


# =========================================================
# SINGLE-GAME RECORDS
# =========================================================

st.header("Single-Game Records")


left, right = st.columns(2)


with left:

    st.subheader("🔥 Highest Scores")

    highest_display = (
        highest
        .head(10)
        .copy()
    )

    highest_display["Score"] = (
        highest_display["points_for"]
        .round(2)
    )

    highest_display["Opponent Score"] = (
        highest_display["points_against"]
        .round(2)
    )

    highest_display = highest_display[
        [
            "year",
            "week",
            "team",
            "Score",
            "opponent",
            "Opponent Score",
            "result",
        ]
    ].rename(
        columns={
            "year": "Year",
            "week": "Week",
            "team": "Team",
            "opponent": "Opponent",
            "result": "Result",
        }
    )

    st.dataframe(
        highest_display,
        hide_index=True,
        use_container_width=True,
    )


with right:

    st.subheader("🧊 Lowest Scores")

    lowest_display = (
        lowest
        .head(10)
        .copy()
    )

    lowest_display["Score"] = (
        lowest_display["points_for"]
        .round(2)
    )

    lowest_display["Opponent Score"] = (
        lowest_display["points_against"]
        .round(2)
    )

    lowest_display = lowest_display[
        [
            "year",
            "week",
            "team",
            "Score",
            "opponent",
            "Opponent Score",
            "result",
        ]
    ].rename(
        columns={
            "year": "Year",
            "week": "Week",
            "team": "Team",
            "opponent": "Opponent",
            "result": "Result",
        }
    )

    st.dataframe(
        lowest_display,
        hide_index=True,
        use_container_width=True,
    )


st.divider()


# =========================================================
# PAINFUL LOSSES
# =========================================================

st.header("Painful Ways to Lose")


col1, col2 = st.columns(2)


with col1:

    st.subheader("💀 Highest Scores in a Loss")

    losing_scores = (
        team_games[
            team_games["result"] == "L"
        ]
        .sort_values(
            "points_for",
            ascending=False,
        )
        .head(10)
        .copy()
    )

    losing_scores["Score"] = (
        losing_scores["points_for"]
        .round(2)
    )

    losing_scores["Opponent Score"] = (
        losing_scores["points_against"]
        .round(2)
    )

    losing_scores = losing_scores[
        [
            "year",
            "week",
            "team",
            "Score",
            "opponent",
            "Opponent Score",
        ]
    ].rename(
        columns={
            "year": "Year",
            "week": "Week",
            "team": "Team",
            "opponent": "Opponent",
        }
    )

    st.dataframe(
        losing_scores,
        hide_index=True,
        use_container_width=True,
    )


with col2:

    st.subheader("🗑️ Lowest Scores That Somehow Won")

    ugly_wins = (
        team_games[
            team_games["result"] == "W"
        ]
        .sort_values(
            "points_for",
            ascending=True,
        )
        .head(10)
        .copy()
    )

    ugly_wins["Score"] = (
        ugly_wins["points_for"]
        .round(2)
    )

    ugly_wins["Opponent Score"] = (
        ugly_wins["points_against"]
        .round(2)
    )

    ugly_wins = ugly_wins[
        [
            "year",
            "week",
            "team",
            "Score",
            "opponent",
            "Opponent Score",
        ]
    ].rename(
        columns={
            "year": "Year",
            "week": "Week",
            "team": "Team",
            "opponent": "Opponent",
        }
    )

    st.dataframe(
        ugly_wins,
        hide_index=True,
        use_container_width=True,
    )


st.divider()


# =========================================================
# BIGGEST BLOWOUTS
# =========================================================

st.header("Ass-Kickings")


# Rebuild from team_games so winner score is
# explicitly paired with the winning franchise.

winning_games = (
    team_games[
        team_games["result"] == "W"
    ]
    .copy()
)

winning_games["margin"] = (
    winning_games["points_for"]
    - winning_games["points_against"]
)

winning_games = (
    winning_games
    .sort_values(
        "margin",
        ascending=False,
    )
    .head(15)
)

blowout_display = winning_games[
    [
        "year",
        "week",
        "team",
        "points_for",
        "opponent",
        "points_against",
        "margin",
    ]
].copy()

blowout_display.columns = [
    "Year",
    "Week",
    "Winner",
    "Winner Score",
    "Loser",
    "Loser Score",
    "Margin",
]

blowout_display[
    [
        "Winner Score",
        "Loser Score",
        "Margin",
    ]
] = (
    blowout_display[
        [
            "Winner Score",
            "Loser Score",
            "Margin",
        ]
    ]
    .round(2)
)


st.dataframe(
    blowout_display,
    hide_index=True,
    use_container_width=True,
)


worst = blowout_display.iloc[0]

st.caption(
    f"The current gold standard in humiliation: "
    f"{worst['Winner']} beat {worst['Loser']} by "
    f"{worst['Margin']:.2f} points in "
    f"{int(worst['Year'])} Week {int(worst['Week'])}."
)


st.divider()


# =========================================================
# CLOSEST GAMES
# =========================================================

st.header("Nail-Biters")


game_rows = []

for _, row in team_games.iterrows():

    # Only keep each game once.
    team_pair = tuple(
        sorted(
            [
                row["team"],
                row["opponent"],
            ]
        )
    )

    game_rows.append(
        {
            "year": row["year"],
            "week": row["week"],
            "team": row["team"],
            "opponent": row["opponent"],
            "team_score": row["points_for"],
            "opponent_score": row["points_against"],
            "margin": abs(
                row["points_for"]
                - row["points_against"]
            ),
            "game_key": (
                row["year"],
                row["week"],
                team_pair,
            ),
        }
    )


close_df = pd.DataFrame(game_rows)

close_df = (
    close_df
    .drop_duplicates(
        subset="game_key"
    )
    .sort_values(
        "margin",
        ascending=True,
    )
    .head(15)
    .copy()
)


def determine_winner(row):

    if row["team_score"] > row["opponent_score"]:
        return row["team"]

    if row["opponent_score"] > row["team_score"]:
        return row["opponent"]

    return "Tie"


close_df["winner"] = (
    close_df.apply(
        determine_winner,
        axis=1,
    )
)


close_display = close_df[
    [
        "year",
        "week",
        "team",
        "team_score",
        "opponent",
        "opponent_score",
        "winner",
        "margin",
    ]
].copy()

close_display.columns = [
    "Year",
    "Week",
    "Team 1",
    "Score 1",
    "Team 2",
    "Score 2",
    "Winner",
    "Margin",
]

close_display[
    [
        "Score 1",
        "Score 2",
        "Margin",
    ]
] = (
    close_display[
        [
            "Score 1",
            "Score 2",
            "Margin",
        ]
    ]
    .round(2)
)


st.dataframe(
    close_display,
    hide_index=True,
    use_container_width=True,
)


st.divider()


# =========================================================
# FRANCHISE RECORD EXPLORER
# =========================================================

st.header("Franchise Record Explorer")


teams = sorted(
    team_games["team"].unique()
)


selected_team = st.selectbox(
    "Choose a franchise",
    teams,
)


team_data = (
    team_games[
        team_games["team"]
        == selected_team
    ]
    .copy()
)


wins = (
    team_data["result"]
    == "W"
).sum()

losses = (
    team_data["result"]
    == "L"
).sum()

ties = (
    team_data["result"]
    == "T"
).sum()

games_played = len(
    team_data
)

win_pct = (
    (
        wins
        + ties * 0.5
    )
    / games_played
    * 100
)


c1, c2, c3, c4 = st.columns(4)


c1.metric(
    "Record",
    (
        f"{wins}-{losses}"
        if ties == 0
        else f"{wins}-{losses}-{ties}"
    ),
)

c2.metric(
    "Win %",
    f"{win_pct:.1f}%",
)

c3.metric(
    "Points / Game",
    f"{team_data['points_for'].mean():.2f}",
)

c4.metric(
    "Point Differential",
    f"{team_data['margin'].sum():+.2f}",
)


st.subheader(
    f"{selected_team} by Season"
)


team_by_year = (
    team_data
    .groupby("year")
    .agg(
        Games=("result", "size"),
        Wins=(
            "result",
            lambda x:
                (x == "W").sum()
        ),
        Losses=(
            "result",
            lambda x:
                (x == "L").sum()
        ),
        Ties=(
            "result",
            lambda x:
                (x == "T").sum()
        ),
        Points_For=(
            "points_for",
            "sum",
        ),
        Points_Against=(
            "points_against",
            "sum",
        ),
    )
    .reset_index()
)


team_by_year["Win %"] = (
    (
        team_by_year["Wins"]
        + team_by_year["Ties"] * 0.5
    )
    / team_by_year["Games"]
    * 100
).round(1)


team_by_year["Record"] = (
    team_by_year.apply(
        lambda row:
            (
                f"{int(row['Wins'])}-"
                f"{int(row['Losses'])}"
                if row["Ties"] == 0
                else
                f"{int(row['Wins'])}-"
                f"{int(row['Losses'])}-"
                f"{int(row['Ties'])}"
            ),
        axis=1,
    )
)


team_by_year["Points_For"] = (
    team_by_year["Points_For"]
    .round(2)
)

team_by_year["Points_Against"] = (
    team_by_year["Points_Against"]
    .round(2)
)


team_by_year = team_by_year[
    [
        "year",
        "Record",
        "Win %",
        "Points_For",
        "Points_Against",
    ]
].rename(
    columns={
        "year": "Season",
        "Points_For": "PF",
        "Points_Against": "PA",
    }
)


st.dataframe(
    team_by_year,
    hide_index=True,
    use_container_width=True,
)