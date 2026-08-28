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
PLAYER_CHAMPIONSHIP_PEDIGREE_FILE = (
    PLAYOFF_DIR / "player_championship_pedigree.csv"
)
PLAYER_CHAMPIONSHIP_ROSTERS_FILE = (
    PLAYOFF_DIR / "player_championship_rosters.csv"
)

PLAYER_WEEK_DIR = (
    BASE_DIR
    / "data"
    / "matchups"
    / "player_week_stats"
)

WEEKLY_LINEUPS_FILE = (
    PLAYER_WEEK_DIR
    / "all_weekly_lineups_2017_2025.csv"
)

LUCK_DIR = PLAYER_WEEK_DIR / "analysis"

LUCK_SEASON_FILE = LUCK_DIR / "luck_season.csv"
LUCK_ALL_TIME_FILE = LUCK_DIR / "luck_all_time.csv"


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
    player_championship_pedigree = pd.read_csv(
        PLAYER_CHAMPIONSHIP_PEDIGREE_FILE
    )
    player_championship_rosters = pd.read_csv(
        PLAYER_CHAMPIONSHIP_ROSTERS_FILE
    )
    weekly_lineups = pd.read_csv(WEEKLY_LINEUPS_FILE)
    luck_season = pd.read_csv(LUCK_SEASON_FILE)
    luck_all_time = pd.read_csv(LUCK_ALL_TIME_FILE)

    return (
        team_games,
        season_records,
        all_time,
        playoff_records,
        playoff_appearances,
        championships,
        player_championship_pedigree,
        player_championship_rosters,
        weekly_lineups,
        luck_season,
        luck_all_time,
    )


try:

    (
        team_games,
        season_records,
        all_time,
        playoff_records,
        playoff_appearances,
        championships,
        player_championship_pedigree,
        player_championship_rosters,
        weekly_lineups,
        luck_season,
        luck_all_time,
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


team_luck_seasons = (
    luck_season[
        luck_season["fantasy_team"] == selected_team
    ]
    .copy()
    .sort_values("year")
)


team_luck_all_time = (
    luck_all_time[
        luck_all_time["fantasy_team"] == selected_team
    ]
    .copy()
)


# Player scoring is based on points that actually counted:
# regular-season STARTERS only.
team_player_history = (
    weekly_lineups[
        weekly_lineups["fantasy_team"] == selected_team
    ]
    .copy()
)

if not team_player_history.empty:

    team_player_history["fantasy_points"] = pd.to_numeric(
        team_player_history["fantasy_points"],
        errors="coerce",
    )

    if "is_starter" in team_player_history.columns:

        starter_flag = (
            team_player_history["is_starter"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["true", "1", "yes"])
        )

        team_player_history = team_player_history[
            starter_flag
        ].copy()

    team_player_history = team_player_history[
        team_player_history["player"]
        .astype(str)
        .str.strip()
        .ne("(Empty)")
    ].copy()


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
# FRANCHISE PLAYER SCORING LEADERS
# ============================================================

st.divider()

st.header("Franchise Player Leaders")

st.caption(
    "Career player points are fantasy points that actually counted in this "
    "franchise's starting lineup during the regular season."
)


if team_player_history.empty:

    st.info(
        "No validated weekly player history is available for this franchise."
    )

else:

    player_leaders = (
        team_player_history
        .groupby("player", as_index=False)
        .agg(
            career_points=(
                "fantasy_points",
                "sum",
            ),
            starts=(
                "player",
                "size",
            ),
            seasons=(
                "year",
                "nunique",
            ),
            best_game=(
                "fantasy_points",
                "max",
            ),
        )
    )

    player_leaders["points_per_start"] = (
        player_leaders["career_points"]
        / player_leaders["starts"]
    )

    player_leaders = player_leaders.sort_values(
        [
            "career_points",
            "starts",
        ],
        ascending=[
            False,
            False,
        ],
    ).reset_index(drop=True)

    leading_scorer = player_leaders.iloc[0]

    most_starts = (
        player_leaders
        .sort_values(
            [
                "starts",
                "career_points",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .iloc[0]
    )

    best_single_game_player_row = (
        team_player_history
        .sort_values(
            "fantasy_points",
            ascending=False,
        )
        .iloc[0]
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "👑 All-Time Leading Scorer",
            leading_scorer["player"],
            f"{leading_scorer['career_points']:,.2f} points",
        )

        st.caption(
            f"{int(leading_scorer['starts'])} starts • "
            f"{leading_scorer['points_per_start']:.2f} pts/start • "
            f"{int(leading_scorer['seasons'])} seasons"
        )

    with c2:

        st.metric(
            "Most Starts",
            most_starts["player"],
            f"{int(most_starts['starts'])} starts",
        )

        st.caption(
            f"{most_starts['career_points']:,.2f} career points"
        )

    with c3:

        st.metric(
            "Best Player Game",
            best_single_game_player_row["player"],
            f"{best_single_game_player_row['fantasy_points']:.2f} points",
        )

        st.caption(
            f"{int(best_single_game_player_row['year'])} "
            f"Week {int(best_single_game_player_row['week'])} "
            f"vs {best_single_game_player_row['opponent']}"
        )


    st.subheader("All-Time Franchise Scoring Leaders")

    leaders_table = (
        player_leaders
        .head(10)
        .copy()
    )

    leaders_table.insert(
        0,
        "Rank",
        range(
            1,
            len(leaders_table) + 1,
        ),
    )

    leaders_table = leaders_table.rename(
        columns={
            "player": "Player",
            "career_points": "Career Points",
            "starts": "Starts",
            "seasons": "Seasons",
            "points_per_start": "Pts / Start",
            "best_game": "Best Game",
        }
    )

    st.dataframe(
        leaders_table[
            [
                "Rank",
                "Player",
                "Career Points",
                "Starts",
                "Seasons",
                "Pts / Start",
                "Best Game",
            ]
        ],
        hide_index=True,
        use_container_width=True,
        column_config={
            "Career Points": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "Pts / Start": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "Best Game": st.column_config.NumberColumn(
                format="%.2f",
            ),
        },
    )


# ============================================================
# LUCK + STRENGTH OF SCHEDULE
# ============================================================

st.divider()

st.header("🍀 Luck & Strength of Schedule")

st.caption(
    "Schedule luck compares actual wins to expected wins based on how each "
    "weekly score would have performed against all 11 other teams. Positive "
    "numbers mean the schedule helped; negative numbers mean the schedule hurt."
)


if team_luck_seasons.empty:

    st.info(
        "No luck metrics are available for this franchise."
    )

else:

    career_games = int(
        team_luck_seasons["games"].sum()
    )

    career_actual_win_value = float(
        team_luck_seasons["actual_win_value"].sum()
    )

    career_expected_wins = float(
        team_luck_seasons["expected_wins"].sum()
    )

    career_luck = (
        career_actual_win_value
        - career_expected_wins
    )

    career_all_play_wins = float(
        team_luck_seasons["all_play_wins"].sum()
    )

    career_all_play_losses = float(
        team_luck_seasons["all_play_losses"].sum()
    )

    career_all_play_ties = float(
        team_luck_seasons["all_play_ties"].sum()
    )

    career_all_play_games = (
        career_all_play_wins
        + career_all_play_losses
        + career_all_play_ties
    )

    career_all_play_pct = (
        (
            career_all_play_wins
            + 0.5 * career_all_play_ties
        )
        / career_all_play_games
        * 100
        if career_all_play_games
        else 0
    )

    weighted_sos = (
        (
            team_luck_seasons[
                "strength_of_schedule"
            ]
            * team_luck_seasons["games"]
        ).sum()
        / team_luck_seasons["games"].sum()
    )

    opponent_top3 = int(
        team_luck_seasons[
            "opponent_top_3_weeks"
        ].sum()
    )

    opponent_bottom3 = int(
        team_luck_seasons[
            "opponent_bottom_3_weeks"
        ].sum()
    )

    close_games_5 = int(
        team_luck_seasons[
            "close_games_5"
        ].sum()
    )

    close_game_5_win_value = float(
        team_luck_seasons[
            "close_game_5_win_value"
        ].sum()
    )

    close_game_5_pct = (
        close_game_5_win_value
        / close_games_5
        * 100
        if close_games_5
        else 0
    )

    if career_luck >= 2.5:
        luck_description = "Extremely Lucky"
        luck_icon = "🍀"
    elif career_luck >= 1.0:
        luck_description = "Lucky"
        luck_icon = "🍀"
    elif career_luck <= -2.5:
        luck_description = "Cursed"
        luck_icon = "💀"
    elif career_luck <= -1.0:
        luck_description = "Unlucky"
        luck_icon = "☔"
    else:
        luck_description = "Neutral"
        luck_icon = "⚖️"


    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            f"{luck_icon} Schedule Luck",
            f"{career_luck:+.2f} wins",
            luck_description,
        )

        st.caption(
            f"{career_actual_win_value:.1f} actual win value vs "
            f"{career_expected_wins:.2f} expected wins"
        )

    with c2:

        st.metric(
            "Expected Wins",
            f"{career_expected_wins:.2f}",
        )

        st.caption(
            "Based on weekly scoring against the entire league."
        )

    with c3:

        st.metric(
            "All-Play Win %",
            f"{career_all_play_pct:.1f}%",
        )

        st.caption(
            "Record if this team played all 11 opponents every week."
        )

    with c4:

        st.metric(
            "Avg Opponent Score",
            f"{weighted_sos:.2f}",
        )

        st.caption(
            "Career strength-of-schedule scoring average."
        )


    st.subheader("Schedule Profile")

    s1, s2, s3, s4 = st.columns(4)

    with s1:

        st.metric(
            "Opponent Top-3 Weeks",
            opponent_top3,
        )

        st.caption(
            "Weeks the scheduled opponent posted a top-3 league score."
        )

    with s2:

        st.metric(
            "Opponent Bottom-3 Weeks",
            opponent_bottom3,
        )

        st.caption(
            "Weeks the scheduled opponent posted a bottom-3 league score."
        )

    with s3:

        st.metric(
            "Games Decided by ≤ 5",
            close_games_5,
        )

        st.caption(
            "The fantasy equivalent of living dangerously."
        )

    with s4:

        st.metric(
            "Close-Game Win %",
            f"{close_game_5_pct:.1f}%",
        )

        st.caption(
            "Win value in games decided by five points or fewer."
        )


    luckiest_season = (
        team_luck_seasons
        .sort_values(
            "schedule_luck_wins",
            ascending=False,
        )
        .iloc[0]
    )

    unluckiest_season = (
        team_luck_seasons
        .sort_values(
            "schedule_luck_wins",
            ascending=True,
        )
        .iloc[0]
    )

    hardest_schedule = (
        team_luck_seasons
        .sort_values(
            "strength_of_schedule",
            ascending=False,
        )
        .iloc[0]
    )

    easiest_schedule = (
        team_luck_seasons
        .sort_values(
            "strength_of_schedule",
            ascending=True,
        )
        .iloc[0]
    )


    st.subheader("Luck Extremes")

    e1, e2, e3, e4 = st.columns(4)

    with e1:

        st.metric(
            "🍀 Luckiest Season",
            int(luckiest_season["year"]),
            f"{luckiest_season['schedule_luck_wins']:+.2f} wins",
        )

    with e2:

        st.metric(
            "💀 Unluckiest Season",
            int(unluckiest_season["year"]),
            f"{unluckiest_season['schedule_luck_wins']:+.2f} wins",
        )

    with e3:

        st.metric(
            "Hardest Schedule",
            int(hardest_schedule["year"]),
            f"{hardest_schedule['strength_of_schedule']:.2f} opp PPG",
        )

    with e4:

        st.metric(
            "Easiest Schedule",
            int(easiest_schedule["year"]),
            f"{easiest_schedule['strength_of_schedule']:.2f} opp PPG",
        )


    st.subheader("Luck by Season")

    luck_table = (
        team_luck_seasons[
            [
                "year",
                "wins",
                "expected_wins",
                "schedule_luck_wins",
                "strength_of_schedule",
                "sos_rank_hardest",
                "all_play_win_pct",
                "opponent_top_3_weeks",
                "opponent_bottom_3_weeks",
                "close_games_5",
                "close_game_5_win_pct",
            ]
        ]
        .copy()
        .sort_values(
            "year",
            ascending=False,
        )
    )

    luck_table = luck_table.rename(
        columns={
            "year": "Season",
            "wins": "Wins",
            "expected_wins": "Expected Wins",
            "schedule_luck_wins": "Luck",
            "strength_of_schedule": "Opp PPG",
            "sos_rank_hardest": "SOS Rank",
            "all_play_win_pct": "All-Play %",
            "opponent_top_3_weeks": "Opp Top-3",
            "opponent_bottom_3_weeks": "Opp Bottom-3",
            "close_games_5": "Close Games",
            "close_game_5_win_pct": "Close Win %",
        }
    )

    st.dataframe(
        luck_table,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Wins": st.column_config.NumberColumn(
                format="%.0f",
            ),
            "Expected Wins": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "Luck": st.column_config.NumberColumn(
                format="%+.2f",
            ),
            "Opp PPG": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "All-Play %": st.column_config.NumberColumn(
                format="%.1f%%",
            ),
            "Close Win %": st.column_config.NumberColumn(
                format="%.1f%%",
            ),
        },
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
# PLAYER CHAMPIONSHIP PEDIGREE
# ============================================================

st.divider()

st.header("🏆 Championship Pedigree")

st.caption(
    "Player title counts use each champion's final regular-season roster "
    "as the championship-roster proxy."
)


franchise_title_players = (
    player_championship_rosters[
        player_championship_rosters["champion"] == selected_team
    ]
    .copy()
)


if franchise_title_players.empty:

    st.write(
        "No championship-roster player history for this franchise."
    )

else:

    franchise_player_titles = (
        franchise_title_players
        .groupby(
            "player",
            as_index=False,
        )
        .agg(
            Championships=(
                "year",
                "nunique",
            ),
            Seasons=(
                "year",
                lambda s: ", ".join(
                    str(int(x))
                    for x in sorted(set(s))
                ),
            ),
        )
        .sort_values(
            [
                "Championships",
                "player",
            ],
            ascending=[
                False,
                True,
            ],
        )
        .reset_index(drop=True)
    )

    franchise_player_titles.insert(
        0,
        "Rank",
        franchise_player_titles[
            "Championships"
        ]
        .rank(
            method="min",
            ascending=False,
        )
        .astype(int),
    )

    franchise_player_titles = (
        franchise_player_titles.rename(
            columns={
                "player": "Player",
            }
        )
    )

    leader = franchise_player_titles.iloc[0]

    c1, c2 = st.columns([1, 2])

    with c1:

        st.metric(
            "Most Titles",
            leader["Player"],
            f"{int(leader['Championships'])} championship"
            + (
                "s"
                if int(leader["Championships"]) != 1
                else ""
            ),
        )

        st.caption(
            f"Title season(s): {leader['Seasons']}"
        )

    with c2:

        st.dataframe(
            franchise_player_titles.head(15),
            hide_index=True,
            use_container_width=True,
        )


with st.expander(
    "League-Wide Player Championship Leaders"
):

    league_titles = (
        player_championship_pedigree
        .sort_values(
            [
                "championships",
                "player",
            ],
            ascending=[
                False,
                True,
            ],
        )
        .head(25)
        .copy()
    )

    league_titles = league_titles.rename(
        columns={
            "championship_rank": "Rank",
            "player": "Player",
            "championships": "Championships",
            "championship_seasons": "Title Seasons",
            "champion_franchises": "Champion Franchises",
        }
    )

    st.dataframe(
        league_titles[
            [
                "Rank",
                "Player",
                "Championships",
                "Title Seasons",
                "Champion Franchises",
            ]
        ],
        hide_index=True,
        use_container_width=True,
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