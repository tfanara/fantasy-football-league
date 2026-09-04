import streamlit as st
import pandas as pd
from pathlib import Path

from season_config import CURRENT_SEASON, LAST_COMPLETED_SEASON


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="History | Malle's League",
    page_icon="📚",
    layout="wide",
)

st.title("📚 League History")
st.caption(
    "Regular-season records, playoff failures, championships, "
    "and years of receipts."
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

HISTORY_DIR = BASE_DIR / "data" / "history"
PLAYOFF_DIR = BASE_DIR / "data" / "playoffs"

SEASON_RECORDS_FILE = HISTORY_DIR / "season_records.csv"
ALL_TIME_FILE = HISTORY_DIR / "all_time_records.csv"
TEAM_GAMES_FILE = HISTORY_DIR / "team_games.csv"

CHAMPIONSHIPS_FILE = PLAYOFF_DIR / "championships.csv"
PLAYOFF_RECORDS_FILE = PLAYOFF_DIR / "playoff_records.csv"
PLAYOFF_APPEARANCES_FILE = PLAYOFF_DIR / "playoff_appearances.csv"


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data():

    season_records = pd.read_csv(SEASON_RECORDS_FILE)
    all_time = pd.read_csv(ALL_TIME_FILE)
    team_games = pd.read_csv(TEAM_GAMES_FILE)

    championships = pd.read_csv(CHAMPIONSHIPS_FILE)
    playoff_records = pd.read_csv(PLAYOFF_RECORDS_FILE)
    playoff_appearances = pd.read_csv(PLAYOFF_APPEARANCES_FILE)

    return (
        season_records,
        all_time,
        team_games,
        championships,
        playoff_records,
        playoff_appearances,
    )


try:

    (
        season_records,
        all_time,
        team_games,
        championships,
        playoff_records,
        playoff_appearances,
    ) = load_data()

except FileNotFoundError:

    st.error(
        "Historical files are missing. Run:\n\n"
        "`python build_league_history.py`\n\n"
        "and\n\n"
        "`python build_playoff_history.py`"
    )

    st.stop()


# ============================================================
# CLEAN TYPES
# ============================================================

for df in [
    season_records,
    all_time,
    team_games,
    championships,
    playoff_records,
    playoff_appearances,
]:

    for col in [
        "year",
        "games",
        "wins",
        "losses",
        "ties",
        "points_for",
        "points_against",
        "win_pct",
        "point_diff",
        "championships",
        "runner_ups",
        "championship_appearances",
        "playoff_seasons",
        "champion_score",
        "runner_up_score",
        "margin",
    ]:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )


# ============================================================
# HELPERS
# ============================================================

def format_record(row):

    wins = int(row["wins"])
    losses = int(row["losses"])

    ties = (
        int(row["ties"])
        if "ties" in row
        and not pd.isna(row["ties"])
        else 0
    )

    if ties:
        return f"{wins}-{losses}-{ties}"

    return f"{wins}-{losses}"


# ============================================================
# OVERVIEW
# ============================================================

st.divider()

st.header("League Overview")


seasons = sorted(
    season_records["year"]
    .dropna()
    .astype(int)
    .unique()
)

franchises = sorted(
    all_time["team"]
    .dropna()
    .unique()
)

total_games = int(
    season_records["games"].sum() / 2
)

total_titles = len(championships)


c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Seasons Tracked",
    len(seasons),
)

c2.metric(
    "Historical Franchises",
    len(franchises),
)

c3.metric(
    "Regular-Season Games",
    total_games,
)

c4.metric(
    "Championships Awarded",
    total_titles,
)


# ============================================================
# CHAMPIONS
# ============================================================

st.divider()

st.header("🏆 Champions")


championship_display = (
    championships
    .sort_values(
        "year",
        ascending=False,
    )
    .copy()
)


championship_display["Score"] = (
    championship_display.apply(
        lambda row:
            f"{row['champion_score']:.2f} – "
            f"{row['runner_up_score']:.2f}",
        axis=1,
    )
)


championship_display = championship_display[
    [
        "year",
        "champion",
        "runner_up",
        "Score",
        "margin",
    ]
].rename(
    columns={
        "year": "Season",
        "champion": "Champion",
        "runner_up": "Runner-Up",
        "margin": "Margin",
    }
)


st.dataframe(
    championship_display,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Season": st.column_config.NumberColumn(
            format="%d"
        ),
        "Margin": st.column_config.NumberColumn(
            format="%.2f"
        ),
    },
)


# ============================================================
# TITLE LEADERBOARD
# ============================================================

st.subheader("Championship Leaderboard")


title_counts = (
    championships[
        "champion"
    ]
    .value_counts()
    .rename_axis("Franchise")
    .reset_index(
        name="Championships"
    )
)


runner_up_counts = (
    championships[
        "runner_up"
    ]
    .value_counts()
    .rename_axis("Franchise")
    .reset_index(
        name="Runner-Ups"
    )
)


title_table = (
    pd.merge(
        title_counts,
        runner_up_counts,
        on="Franchise",
        how="outer",
    )
    .fillna(0)
)


title_table[
    [
        "Championships",
        "Runner-Ups",
    ]
] = (
    title_table[
        [
            "Championships",
            "Runner-Ups",
        ]
    ]
    .astype(int)
)


title_table["Finals"] = (
    title_table["Championships"]
    + title_table["Runner-Ups"]
)


title_table = title_table.sort_values(
    [
        "Championships",
        "Finals",
        "Runner-Ups",
    ],
    ascending=[
        False,
        False,
        False,
    ],
).reset_index(drop=True)


title_table.insert(
    0,
    "Rank",
    range(
        1,
        len(title_table) + 1,
    )
)


st.dataframe(
    title_table,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# CHAMPIONSHIP SUPERLATIVES
# ============================================================

biggest_title_game = (
    championships
    .sort_values(
        "margin",
        ascending=False,
    )
    .iloc[0]
)

closest_title_game = (
    championships
    .sort_values(
        "margin",
        ascending=True,
    )
    .iloc[0]
)


c1, c2 = st.columns(2)


with c1:

    st.metric(
        "Largest Championship Blowout",
        f"{biggest_title_game['margin']:.2f}",
        biggest_title_game["champion"],
    )

    st.caption(
        f"{int(biggest_title_game['year'])}: "
        f"{biggest_title_game['champion']} "
        f"{biggest_title_game['champion_score']:.2f} – "
        f"{biggest_title_game['runner_up']} "
        f"{biggest_title_game['runner_up_score']:.2f}"
    )


with c2:

    st.metric(
        "Closest Championship",
        f"{closest_title_game['margin']:.2f}",
        closest_title_game["champion"],
    )

    st.caption(
        f"{int(closest_title_game['year'])}: "
        f"{closest_title_game['champion']} "
        f"{closest_title_game['champion_score']:.2f} – "
        f"{closest_title_game['runner_up']} "
        f"{closest_title_game['runner_up_score']:.2f}"
    )


# ============================================================
# SEASON SELECTOR
# ============================================================

st.divider()

st.header("Season-by-Season")


selected_year = st.selectbox(
    "Choose a season",
    seasons,
    index=len(seasons) - 1,
)


season = (
    season_records[
        season_records["year"]
        == selected_year
    ]
    .copy()
)


season["Record"] = (
    season.apply(
        format_record,
        axis=1,
    )
)

season["Win %"] = (
    season["win_pct"] * 100
).round(1)

season["PF"] = (
    season["points_for"]
    .round(2)
)

season["PA"] = (
    season["points_against"]
    .round(2)
)

season["Diff"] = (
    season["point_diff"]
    .round(2)
)


season = season.sort_values(
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


season.insert(
    0,
    "Rank",
    range(
        1,
        len(season) + 1,
    )
)


# ------------------------------------------------------------
# CHAMPION CARD FOR SELECTED YEAR
# ------------------------------------------------------------

year_title = (
    championships[
        championships["year"]
        == selected_year
    ]
)


if not year_title.empty:

    title = year_title.iloc[0]

    st.success(
        f"🏆 {int(selected_year)} Champion: "
        f"**{title['champion']}** — defeated "
        f"**{title['runner_up']}** "
        f"{title['champion_score']:.2f}–"
        f"{title['runner_up_score']:.2f}"
    )


# ------------------------------------------------------------
# STANDINGS
# ------------------------------------------------------------

display_season = season[
    [
        "Rank",
        "team",
        "Record",
        "Win %",
        "PF",
        "PA",
        "Diff",
    ]
].rename(
    columns={
        "team": "Franchise",
    }
)


st.dataframe(
    display_season,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Rank": st.column_config.NumberColumn(
            format="%d"
        ),
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
# SEASON SUPERLATIVES
# ============================================================

st.subheader(
    f"{selected_year} Superlatives"
)


best_team = season.iloc[0]
worst_team = season.iloc[-1]

highest_scoring = (
    season
    .sort_values(
        "points_for",
        ascending=False,
    )
    .iloc[0]
)

lowest_scoring = (
    season
    .sort_values(
        "points_for",
        ascending=True,
    )
    .iloc[0]
)


c1, c2, c3, c4 = st.columns(4)


c1.metric(
    "Best Record",
    format_record(best_team),
    best_team["team"],
)

c2.metric(
    "Worst Record",
    format_record(worst_team),
    worst_team["team"],
)

c3.metric(
    "Most Points",
    f"{highest_scoring['points_for']:.2f}",
    highest_scoring["team"],
)

c4.metric(
    "Fewest Points",
    f"{lowest_scoring['points_for']:.2f}",
    lowest_scoring["team"],
)


# ============================================================
# ALL-TIME PLAYOFF RECORDS
# ============================================================

st.divider()

st.header("🏟️ All-Time Playoff Records")


playoff_display = (
    playoff_records
    .copy()
)


playoff_display["Record"] = (
    playoff_display.apply(
        lambda row:
            f"{int(row['wins'])}-"
            f"{int(row['losses'])}",
        axis=1,
    )
)


playoff_display = playoff_display[
    [
        "team",
        "playoff_seasons",
        "Record",
        "win_pct",
        "championships",
        "runner_ups",
        "championship_appearances",
    ]
].rename(
    columns={
        "team": "Franchise",
        "playoff_seasons": "Playoff Seasons",
        "win_pct": "Win %",
        "championships": "Titles",
        "runner_ups": "Runner-Ups",
        "championship_appearances": "Finals",
    }
)


st.dataframe(
    playoff_display,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Win %": st.column_config.NumberColumn(
            format="%.1f%%"
        ),
    },
)


# ============================================================
# PLAYOFF STORYLINES
# ============================================================

st.subheader("Playoff Storylines")


most_titles = (
    playoff_records
    .sort_values(
        [
            "championships",
            "championship_appearances",
        ],
        ascending=False,
    )
    .iloc[0]
)


most_finals_losses = (
    playoff_records
    .sort_values(
        [
            "runner_ups",
            "championship_appearances",
        ],
        ascending=False,
    )
    .iloc[0]
)


worst_playoff_pct = (
    playoff_records[
        playoff_records["games"]
        >= 4
    ]
    .sort_values(
        "win_pct"
    )
    .iloc[0]
)


c1, c2, c3 = st.columns(3)


c1.metric(
    "Most Championships",
    int(most_titles["championships"]),
    most_titles["team"],
)

c2.metric(
    "Most Runner-Up Finishes",
    int(most_finals_losses["runner_ups"]),
    most_finals_losses["team"],
)

c3.metric(
    "Worst Playoff Win %",
    f"{worst_playoff_pct['win_pct']:.1f}%",
    worst_playoff_pct["team"],
)


# ============================================================
# BEST AND WORST REGULAR SEASONS
# ============================================================

st.divider()

st.header("Best and Worst Regular Seasons Ever")

# Historical season superlatives must compare completed seasons only.
# The current season remains available above in Season-by-Season and below
# in Franchise History as completed weekly results accumulate.
completed_season_records = season_records[
    season_records["year"].le(LAST_COMPLETED_SEASON)
].copy()


best_seasons = (
    completed_season_records
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
    .head(10)
    .copy()
)


worst_seasons = (
    completed_season_records
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
    .head(10)
    .copy()
)


for table in [
    best_seasons,
    worst_seasons,
]:

    table["Record"] = table.apply(
        format_record,
        axis=1,
    )

    table["Win %"] = (
        table["win_pct"]
        * 100
    ).round(1)

    table["PF"] = (
        table["points_for"]
        .round(2)
    )

    table["Diff"] = (
        table["point_diff"]
        .round(2)
    )


left, right = st.columns(2)


with left:

    st.subheader(
        "👑 Best Regular Seasons"
    )

    st.dataframe(
        best_seasons[
            [
                "year",
                "team",
                "Record",
                "Win %",
                "PF",
                "Diff",
            ]
        ].rename(
            columns={
                "year": "Season",
                "team": "Franchise",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )


with right:

    st.subheader(
        "🗑️ Worst Regular Seasons"
    )

    st.dataframe(
        worst_seasons[
            [
                "year",
                "team",
                "Record",
                "Win %",
                "PF",
                "Diff",
            ]
        ].rename(
            columns={
                "year": "Season",
                "team": "Franchise",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )


# ============================================================
# FRANCHISE HISTORY
# ============================================================

st.divider()

st.header("Franchise History")


selected_team = st.selectbox(
    "Choose a franchise",
    franchises,
    key="history_franchise",
)


team_history = (
    season_records[
        season_records["team"]
        == selected_team
    ]
    .copy()
    .sort_values(
        "year"
    )
)


team_playoffs = (
    playoff_records[
        playoff_records["team"]
        == selected_team
    ]
)


titles = 0
runner_ups = 0
playoff_seasons = 0
playoff_record = "0-0"


if not team_playoffs.empty:

    p = team_playoffs.iloc[0]

    titles = int(
        p["championships"]
    )

    runner_ups = int(
        p["runner_ups"]
    )

    playoff_seasons = int(
        p["playoff_seasons"]
    )

    playoff_record = (
        f"{int(p['wins'])}-"
        f"{int(p['losses'])}"
    )


career_wins = int(
    team_history["wins"].sum()
)

career_losses = int(
    team_history["losses"].sum()
)


c1, c2, c3, c4, c5 = st.columns(5)


c1.metric(
    "Regular-Season Record",
    f"{career_wins}-{career_losses}",
)

c2.metric(
    "Playoff Record",
    playoff_record,
)

c3.metric(
    "Playoff Seasons",
    playoff_seasons,
)

c4.metric(
    "Championships",
    titles,
)

c5.metric(
    "Runner-Ups",
    runner_ups,
)


# ------------------------------------------------------------
# FRANCHISE SEASON TABLE
# ------------------------------------------------------------

team_history["Record"] = (
    team_history.apply(
        format_record,
        axis=1,
    )
)

team_history["Win %"] = (
    team_history["win_pct"]
    * 100
).round(1)

team_history["PF"] = (
    team_history["points_for"]
    .round(2)
)

team_history["PA"] = (
    team_history["points_against"]
    .round(2)
)


team_history_display = team_history[
    [
        "year",
        "Record",
        "Win %",
        "PF",
        "PA",
    ]
].rename(
    columns={
        "year": "Season",
    }
)


# Add postseason finish
finish_lookup = (
    playoff_appearances[
        playoff_appearances["team"]
        == selected_team
    ][
        [
            "year",
            "finish",
        ]
    ]
    .rename(
        columns={
            "year": "Season",
            "finish": "Postseason",
        }
    )
)


team_history_display = (
    team_history_display
    .merge(
        finish_lookup,
        on="Season",
        how="left",
    )
)


team_history_display[
    "Postseason"
] = (
    team_history_display[
        "Postseason"
    ]
    .fillna(
        "Missed Playoffs"
    )
)


st.dataframe(
    team_history_display,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# WINS BY SEASON
# ============================================================

st.subheader("Wins by Season")


chart_data = (
    team_history[
        [
            "year",
            "wins",
        ]
    ]
    .set_index(
        "year"
    )
)


st.bar_chart(
    chart_data,
    y="wins",
)


# ============================================================
# FINAL NOTE
# ============================================================

st.divider()

st.caption(
    "Regular-season records and Championship Bracket playoff "
    "results are tracked separately. Consolation games are not "
    "counted as playoff wins."
)