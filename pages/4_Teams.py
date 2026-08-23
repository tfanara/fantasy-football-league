import streamlit as st
import pandas as pd
from pathlib import Path


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Teams | Malle's League",
    page_icon="🏈",
    layout="wide",
)

st.title("🏈 Franchise Profiles")
st.caption("Career records, playoff history, scoring highs, and long-term evidence.")


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

HISTORY_DIR = BASE_DIR / "data" / "history"
PLAYOFF_DIR = BASE_DIR / "data" / "playoffs"

TEAM_GAMES_FILE = HISTORY_DIR / "team_games.csv"
SEASON_RECORDS_FILE = HISTORY_DIR / "season_records.csv"
ALL_TIME_FILE = HISTORY_DIR / "all_time_records.csv"

PLAYOFF_RECORDS_FILE = PLAYOFF_DIR / "playoff_records.csv"
PLAYOFF_APPEARANCES_FILE = PLAYOFF_DIR / "playoff_appearances.csv"
CHAMPIONSHIPS_FILE = PLAYOFF_DIR / "championships.csv"


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data():

    team_games = pd.read_csv(TEAM_GAMES_FILE)
    season_records = pd.read_csv(SEASON_RECORDS_FILE)
    all_time = pd.read_csv(ALL_TIME_FILE)

    playoff_records = pd.read_csv(PLAYOFF_RECORDS_FILE)
    playoff_appearances = pd.read_csv(PLAYOFF_APPEARANCES_FILE)
    championships = pd.read_csv(CHAMPIONSHIPS_FILE)

    return (
        team_games,
        season_records,
        all_time,
        playoff_records,
        playoff_appearances,
        championships,
    )


try:

    (
        team_games,
        season_records,
        all_time,
        playoff_records,
        playoff_appearances,
        championships,
    ) = load_data()

except FileNotFoundError:

    st.error(
        "Historical data files are missing. Run the history build scripts first."
    )

    st.stop()


# ============================================================
# HELPERS
# ============================================================

def format_record(wins, losses, ties=0):

    wins = int(wins)
    losses = int(losses)
    ties = int(ties)

    if ties:
        return f"{wins}-{losses}-{ties}"

    return f"{wins}-{losses}"


# ============================================================
# TEAM SELECTOR
# ============================================================

teams = sorted(
    all_time["team"]
    .dropna()
    .unique()
)


selected_team = st.selectbox(
    "Choose a franchise",
    teams,
)


# ============================================================
# FILTER DATA
# ============================================================

team_all_time = (
    all_time[
        all_time["team"] == selected_team
    ]
    .iloc[0]
)

team_games_df = (
    team_games[
        team_games["team"] == selected_team
    ]
    .copy()
)

team_seasons = (
    season_records[
        season_records["team"] == selected_team
    ]
    .copy()
    .sort_values("year")
)

team_playoffs = (
    playoff_records[
        playoff_records["team"] == selected_team
    ]
)

team_appearances = (
    playoff_appearances[
        playoff_appearances["team"] == selected_team
    ]
    .copy()
    .sort_values("year")
)


# ============================================================
# TOP SUMMARY
# ============================================================

st.divider()

st.header(selected_team)


regular_record = format_record(
    team_all_time["wins"],
    team_all_time["losses"],
    team_all_time["ties"],
)

regular_win_pct = (
    team_all_time["win_pct"] * 100
)


if not team_playoffs.empty:

    p = team_playoffs.iloc[0]

    playoff_record = format_record(
        p["wins"],
        p["losses"],
        p.get("ties", 0),
    )

    playoff_seasons = int(
        p["playoff_seasons"]
    )

    titles = int(
        p["championships"]
    )

    finals = int(
        p["championship_appearances"]
    )

else:

    playoff_record = "0-0"
    playoff_seasons = 0
    titles = 0
    finals = 0


c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Regular-Season Record",
    regular_record,
)

c2.metric(
    "Win %",
    f"{regular_win_pct:.1f}%",
)

c3.metric(
    "Playoff Record",
    playoff_record,
)

c4.metric(
    "Championships",
    titles,
)

c5.metric(
    "Finals",
    finals,
)


# ============================================================
# CAREER SCORING
# ============================================================

st.subheader("Career Scoring")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Points For",
    f"{team_all_time['points_for']:,.2f}",
)

c2.metric(
    "Points Against",
    f"{team_all_time['points_against']:,.2f}",
)

c3.metric(
    "Average Score",
    f"{team_all_time['avg_points']:.2f}",
)

c4.metric(
    "Point Differential",
    f"{team_all_time['point_diff']:+,.2f}",
)


# ============================================================
# BEST / WORST SEASON
# ============================================================

st.divider()

st.header("Season Extremes")


best_season = (
    team_seasons
    .sort_values(
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
    )
    .iloc[0]
)


worst_season = (
    team_seasons
    .sort_values(
        [
            "win_pct",
            "point_diff",
            "points_for",
        ],
        ascending=[
            True,
            True,
            True,
        ],
    )
    .iloc[0]
)


c1, c2 = st.columns(2)


with c1:

    st.subheader("👑 Best Season")

    st.metric(
        "Season",
        int(best_season["year"]),
    )

    st.metric(
        "Record",
        format_record(
            best_season["wins"],
            best_season["losses"],
            best_season["ties"],
        ),
    )

    st.caption(
        f"{best_season['points_for']:.2f} PF • "
        f"{best_season['point_diff']:+.2f} differential"
    )


with c2:

    st.subheader("🗑️ Worst Season")

    st.metric(
        "Season",
        int(worst_season["year"]),
    )

    st.metric(
        "Record",
        format_record(
            worst_season["wins"],
            worst_season["losses"],
            worst_season["ties"],
        ),
    )

    st.caption(
        f"{worst_season['points_for']:.2f} PF • "
        f"{worst_season['point_diff']:+.2f} differential"
    )


# ============================================================
# SINGLE-GAME EXTREMES
# ============================================================

st.divider()

st.header("Single-Game Extremes")


highest_game = (
    team_games_df
    .sort_values(
        "points_for",
        ascending=False,
    )
    .iloc[0]
)

lowest_game = (
    team_games_df
    .sort_values(
        "points_for",
        ascending=True,
    )
    .iloc[0]
)

biggest_win = (
    team_games_df[
        team_games_df["result"] == "W"
    ]
    .sort_values(
        "margin",
        ascending=False,
    )
    .iloc[0]
)

biggest_loss = (
    team_games_df[
        team_games_df["result"] == "L"
    ]
    .sort_values(
        "margin",
        ascending=True,
    )
    .iloc[0]
)


c1, c2, c3, c4 = st.columns(4)


with c1:

    st.metric(
        "Highest Score",
        f"{highest_game['points_for']:.2f}",
    )

    st.caption(
        f"{int(highest_game['year'])} Week {int(highest_game['week'])} "
        f"vs {highest_game['opponent']}"
    )


with c2:

    st.metric(
        "Lowest Score",
        f"{lowest_game['points_for']:.2f}",
    )

    st.caption(
        f"{int(lowest_game['year'])} Week {int(lowest_game['week'])} "
        f"vs {lowest_game['opponent']}"
    )


with c3:

    st.metric(
        "Biggest Win",
        f"{biggest_win['margin']:+.2f}",
    )

    st.caption(
        f"{int(biggest_win['year'])} Week {int(biggest_win['week'])} "
        f"vs {biggest_win['opponent']}"
    )


with c4:

    st.metric(
        "Biggest Loss",
        f"{biggest_loss['margin']:.2f}",
    )

    st.caption(
        f"{int(biggest_loss['year'])} Week {int(biggest_loss['week'])} "
        f"vs {biggest_loss['opponent']}"
    )


# ============================================================
# SEASON-BY-SEASON
# ============================================================

st.divider()

st.header("Season-by-Season")


season_table = team_seasons.copy()


season_table["Record"] = season_table.apply(
    lambda row:
        format_record(
            row["wins"],
            row["losses"],
            row["ties"],
        ),
    axis=1,
)


season_table["Win %"] = (
    season_table["win_pct"] * 100
).round(1)

season_table["PF"] = (
    season_table["points_for"]
    .round(2)
)

season_table["PA"] = (
    season_table["points_against"]
    .round(2)
)

season_table["Diff"] = (
    season_table["point_diff"]
    .round(2)
)


finish_lookup = (
    team_appearances[
        [
            "year",
            "finish",
        ]
    ]
    .rename(
        columns={
            "finish": "Postseason",
        }
    )
)


season_table = (
    season_table
    .merge(
        finish_lookup,
        on="year",
        how="left",
    )
)


season_table["Postseason"] = (
    season_table["Postseason"]
    .fillna("Missed Playoffs")
)


season_table = season_table[
    [
        "year",
        "Record",
        "Win %",
        "PF",
        "PA",
        "Diff",
        "Postseason",
    ]
].rename(
    columns={
        "year": "Season",
    }
)


st.dataframe(
    season_table,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# WIN TREND
# ============================================================

st.subheader("Wins by Season")


chart_data = (
    team_seasons[
        [
            "year",
            "wins",
        ]
    ]
    .set_index("year")
)


st.bar_chart(
    chart_data,
    y="wins",
)


# ============================================================
# HEAD-TO-HEAD VS EVERYONE
# ============================================================

st.divider()

st.header("Head-to-Head Against the League")


h2h_rows = []


for opponent, games in team_games_df.groupby("opponent"):

    wins = int(
        (games["result"] == "W").sum()
    )

    losses = int(
        (games["result"] == "L").sum()
    )

    ties = int(
        (games["result"] == "T").sum()
    )

    games_played = len(games)

    pct = (
        (
            wins + ties * 0.5
        )
        / games_played
        * 100
    )

    points_for = (
        games["points_for"].sum()
    )

    points_against = (
        games["points_against"].sum()
    )

    h2h_rows.append(
        {
            "Opponent": opponent,
            "Games": games_played,
            "Record": format_record(
                wins,
                losses,
                ties,
            ),
            "Win %": round(
                pct,
                1,
            ),
            "PF": round(
                points_for,
                2,
            ),
            "PA": round(
                points_against,
                2,
            ),
            "Diff": round(
                points_for
                - points_against,
                2,
            ),
        }
    )


h2h = pd.DataFrame(h2h_rows)


h2h = h2h.sort_values(
    [
        "Win %",
        "Diff",
    ],
    ascending=[
        False,
        False,
    ],
)


st.dataframe(
    h2h,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Win %": st.column_config.NumberColumn(
            format="%.1f%%"
        ),
        "PF": st.column_config.NumberColumn(
            format="%.2f"
        ),
        "PA": st.column_config.NumberColumn(
            format="%.2f"
        ),
        "Diff": st.column_config.NumberColumn(
            format="%.2f"
        ),
    },
)


# ============================================================
# BEST / WORST OPPONENT
# ============================================================

st.subheader("Favorite Victim / Personal Nightmare")


eligible = h2h[
    h2h["Games"] >= 3
].copy()


if not eligible.empty:

    favorite = (
        eligible
        .sort_values(
            [
                "Win %",
                "Diff",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .iloc[0]
    )

    nightmare = (
        eligible
        .sort_values(
            [
                "Win %",
                "Diff",
            ],
            ascending=[
                True,
                True,
            ],
        )
        .iloc[0]
    )


    c1, c2 = st.columns(2)


    with c1:

        st.metric(
            "Favorite Victim",
            favorite["Opponent"],
            favorite["Record"],
        )

        st.caption(
            f"{favorite['Win %']:.1f}% win rate • "
            f"{favorite['Diff']:+.2f} point differential"
        )


    with c2:

        st.metric(
            "Personal Nightmare",
            nightmare["Opponent"],
            nightmare["Record"],
        )

        st.caption(
            f"{nightmare['Win %']:.1f}% win rate • "
            f"{nightmare['Diff']:+.2f} point differential"
        )


# ============================================================
# CHAMPIONSHIP HISTORY
# ============================================================

st.divider()

st.header("Championship History")


team_titles = (
    championships[
        championships["champion"]
        == selected_team
    ]
    .copy()
)


team_runner_ups = (
    championships[
        championships["runner_up"]
        == selected_team
    ]
    .copy()
)


if team_titles.empty and team_runner_ups.empty:

    st.write(
        "No championship-game appearances. "
        "The trophy case remains aggressively spacious."
    )

else:

    finals_rows = []


    for _, row in team_titles.iterrows():

        finals_rows.append(
            {
                "Season": int(row["year"]),
                "Result": "🏆 Champion",
                "Opponent": row["runner_up"],
                "Score": (
                    f"{row['champion_score']:.2f} – "
                    f"{row['runner_up_score']:.2f}"
                ),
            }
        )


    for _, row in team_runner_ups.iterrows():

        finals_rows.append(
            {
                "Season": int(row["year"]),
                "Result": "Runner-Up",
                "Opponent": row["champion"],
                "Score": (
                    f"{row['runner_up_score']:.2f} – "
                    f"{row['champion_score']:.2f}"
                ),
            }
        )


    finals_df = (
        pd.DataFrame(finals_rows)
        .sort_values(
            "Season",
            ascending=False,
        )
    )


    st.dataframe(
        finals_df,
        hide_index=True,
        use_container_width=True,
    )