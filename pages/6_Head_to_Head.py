import streamlit as st
import pandas as pd
from pathlib import Path


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Head-to-Head | Malle's League",
    page_icon="⚔️",
    layout="wide",
)

st.title("⚔️ Head-to-Head")
st.caption("Settle the argument with actual evidence.")


# ============================================================
# LOAD DATA
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "history" / "team_games.csv"


@st.cache_data
def load_data():
    df = pd.read_csv(DATA_FILE)

    for col in ["year", "week", "points_for", "points_against"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


try:
    df = load_data()

except FileNotFoundError:
    st.error(
        "Could not find data/history/team_games.csv. "
        "Run `python build_league_history.py` first."
    )
    st.stop()


# ============================================================
# TEAM LIST
# ============================================================

teams = sorted(df["team"].dropna().unique())

if len(teams) < 2:
    st.error("Not enough teams found in team_games.csv.")
    st.stop()


# ============================================================
# TEAM SELECTORS
# ============================================================

col1, col2 = st.columns(2)

with col1:
    team_a = st.selectbox(
        "Team 1",
        teams,
        index=0,
        key="h2h_team_a",
    )

with col2:
    team_b = st.selectbox(
        "Team 2",
        teams,
        index=1,
        key="h2h_team_b",
    )


if team_a == team_b:
    st.warning("Pick two different teams.")
    st.stop()


# ============================================================
# FILTER MATCHUPS
# ============================================================

# team_games.csv contains one row from each team's perspective.
# We only need Team A's rows so each matchup appears once.

matchups = df[
    (df["team"] == team_a)
    & (df["opponent"] == team_b)
].copy()


if matchups.empty:
    st.info(
        f"No regular-season matchups were found between "
        f"{team_a} and {team_b}."
    )
    st.stop()


matchups = matchups.sort_values(
    ["year", "week"]
).reset_index(drop=True)


# ============================================================
# BASIC SERIES DATA
# ============================================================

wins_a = int((matchups["result"] == "W").sum())
losses_a = int((matchups["result"] == "L").sum())
ties = int((matchups["result"] == "T").sum())

wins_b = losses_a
losses_b = wins_a

games = len(matchups)

points_a = matchups["points_for"].sum()
points_b = matchups["points_against"].sum()

avg_a = matchups["points_for"].mean()
avg_b = matchups["points_against"].mean()

point_diff = points_a - points_b


# ============================================================
# SERIES LEADER
# ============================================================

if wins_a > wins_b:
    leader = team_a
    leader_wins = wins_a
    leader_losses = wins_b

elif wins_b > wins_a:
    leader = team_b
    leader_wins = wins_b
    leader_losses = wins_a

else:
    leader = None
    leader_wins = wins_a
    leader_losses = wins_b


# ============================================================
# ALL-TIME SERIES
# ============================================================

st.divider()

st.subheader("All-Time Series")

if leader:
    st.markdown(
        f"## {leader} leads {leader_wins}–{leader_losses}"
    )
else:
    st.markdown(
        f"## Dead Even: {wins_a}–{wins_b}"
    )

if ties:
    st.caption(
        f"{games} regular-season meetings • {ties} tie"
        f"{'s' if ties != 1 else ''}"
    )
else:
    st.caption(
        f"{games} regular-season meetings"
    )


# ============================================================
# TEAM COMPARISON
# ============================================================

st.divider()

left, middle, right = st.columns([5, 1, 5])


with left:
    st.subheader(team_a)

    a1, a2 = st.columns(2)

    with a1:
        st.metric(
            "Series Record",
            (
                f"{wins_a}-{losses_a}-{ties}"
                if ties
                else f"{wins_a}-{losses_a}"
            ),
        )

        st.metric(
            "Average Score",
            f"{avg_a:.2f}",
        )

    with a2:
        st.metric(
            "Total Points",
            f"{points_a:,.2f}",
        )

        st.metric(
            "Point Differential",
            f"{point_diff:+,.2f}",
        )


with middle:
    st.markdown("### VS")


with right:
    st.subheader(team_b)

    b1, b2 = st.columns(2)

    with b1:
        st.metric(
            "Series Record",
            (
                f"{wins_b}-{losses_b}-{ties}"
                if ties
                else f"{wins_b}-{losses_b}"
            ),
        )

        st.metric(
            "Average Score",
            f"{avg_b:.2f}",
        )

    with b2:
        st.metric(
            "Total Points",
            f"{points_b:,.2f}",
        )

        st.metric(
            "Point Differential",
            f"{-point_diff:+,.2f}",
        )


# ============================================================
# RIVALRY REPORT
# ============================================================

st.divider()

st.subheader("🔥 Rivalry Report")


def rivalry_commentary():

    difference = abs(wins_a - wins_b)

    if wins_a == wins_b:
        return (
            f"**{team_a}** and **{team_b}** are dead even at "
            f"**{wins_a}-{wins_b}**. After {games} meetings, "
            f"neither franchise has earned the right to talk much trash."
        )

    if wins_a > wins_b:
        better = team_a
        worse = team_b
        better_wins = wins_a
        worse_wins = wins_b

    else:
        better = team_b
        worse = team_a
        better_wins = wins_b
        worse_wins = wins_a

    if difference >= 6:
        return (
            f"This isn't much of a rivalry. **{better}** owns "
            f"**{worse}** with a **{better_wins}-{worse_wins}** "
            f"all-time record. At this point, {worse} should probably "
            f"stop calling these matchups competitive."
        )

    elif difference >= 4:
        return (
            f"**{better}** has established a pretty comfortable advantage "
            f"over **{worse}**, leading the series "
            f"**{better_wins}-{worse_wins}**. "
            f"{worse} still has time to fix it, but the historical "
            f"record isn't exactly flattering."
        )

    elif difference >= 2:
        return (
            f"**{better}** holds the edge over **{worse}**, "
            f"**{better_wins}-{worse_wins}**, but this rivalry is still "
            f"close enough that nobody should be printing championship "
            f"banners over it."
        )

    else:
        return (
            f"Almost nothing separates these two. **{better}** leads "
            f"**{worse}** just **{better_wins}-{worse_wins}**. "
            f"One good season could flip the entire rivalry."
        )


st.markdown(rivalry_commentary())


# ============================================================
# CALCULATE GAME STATS
# ============================================================

matchups["margin"] = (
    matchups["points_for"]
    - matchups["points_against"]
)

matchups["abs_margin"] = (
    matchups["margin"].abs()
)

matchups["combined_score"] = (
    matchups["points_for"]
    + matchups["points_against"]
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_winner(row):

    if row["points_for"] > row["points_against"]:
        return team_a

    elif row["points_against"] > row["points_for"]:
        return team_b

    return "Tie"


def get_loser(row):

    if row["points_for"] > row["points_against"]:
        return team_b

    elif row["points_against"] > row["points_for"]:
        return team_a

    return "Tie"


def winner_score(row):

    return max(
        row["points_for"],
        row["points_against"],
    )


def loser_score(row):

    return min(
        row["points_for"],
        row["points_against"],
    )


# ============================================================
# NOTABLE GAMES
# ============================================================

st.divider()

st.subheader("🏆 Notable Games")


biggest = matchups.loc[
    matchups["abs_margin"].idxmax()
]

closest = matchups.loc[
    matchups["abs_margin"].idxmin()
]

highest = matchups.loc[
    matchups["combined_score"].idxmax()
]


c1, c2, c3 = st.columns(3)


# ------------------------------------------------------------
# BIGGEST BEATDOWN
# ------------------------------------------------------------

with c1:

    st.markdown("#### 💥 Biggest Beatdown")

    st.metric(
        "Margin",
        f"{biggest['abs_margin']:.2f}",
    )

    winner = get_winner(biggest)
    loser = get_loser(biggest)

    if winner != "Tie":
        st.write(
            f"**{winner}** over **{loser}**"
        )
    else:
        st.write("Tie")

    st.write(
        f"**{winner_score(biggest):.2f} – "
        f"{loser_score(biggest):.2f}**"
    )

    st.caption(
        f"{int(biggest['year'])} • "
        f"Week {int(biggest['week'])}"
    )


# ------------------------------------------------------------
# CLOSEST GAME
# ------------------------------------------------------------

with c2:

    st.markdown("#### 😬 Closest Game")

    st.metric(
        "Margin",
        f"{closest['abs_margin']:.2f}",
    )

    winner = get_winner(closest)
    loser = get_loser(closest)

    if winner != "Tie":
        st.write(
            f"**{winner}** over **{loser}**"
        )
    else:
        st.write("Tie")

    st.write(
        f"**{winner_score(closest):.2f} – "
        f"{loser_score(closest):.2f}**"
    )

    st.caption(
        f"{int(closest['year'])} • "
        f"Week {int(closest['week'])}"
    )


# ------------------------------------------------------------
# HIGHEST-SCORING GAME
# ------------------------------------------------------------

with c3:

    st.markdown("#### 🚀 Highest-Scoring Game")

    st.metric(
        "Combined Points",
        f"{highest['combined_score']:.2f}",
    )

    winner = get_winner(highest)
    loser = get_loser(highest)

    if winner != "Tie":
        st.write(
            f"**{winner}** over **{loser}**"
        )
    else:
        st.write("Tie")

    st.write(
        f"**{winner_score(highest):.2f} – "
        f"{loser_score(highest):.2f}**"
    )

    st.caption(
        f"{int(highest['year'])} • "
        f"Week {int(highest['week'])}"
    )


# ============================================================
# CURRENT STREAK
# ============================================================

st.divider()

st.subheader("📈 Current Rivalry Streak")


chronological = matchups.sort_values(
    ["year", "week"]
)

latest_winner = get_winner(
    chronological.iloc[-1]
)

current_streak = 0

if latest_winner != "Tie":

    for _, row in chronological.iloc[::-1].iterrows():

        if get_winner(row) == latest_winner:
            current_streak += 1
        else:
            break

    st.metric(
        "Current Streak",
        f"{latest_winner} — {current_streak} straight",
    )

else:
    st.metric(
        "Current Streak",
        "Last meeting was a tie",
    )


# ============================================================
# LONGEST WINNING STREAK
# ============================================================

longest_team = None
longest_streak = 0

current_team = None
current_count = 0


for _, row in chronological.iterrows():

    winner = get_winner(row)

    if winner == "Tie":
        current_team = None
        current_count = 0
        continue

    if winner == current_team:
        current_count += 1

    else:
        current_team = winner
        current_count = 1

    if current_count > longest_streak:
        longest_streak = current_count
        longest_team = current_team


if longest_team:
    st.caption(
        f"Longest winning streak in the series: "
        f"{longest_team}, {longest_streak} straight."
    )


# ============================================================
# SEASON-BY-SEASON
# ============================================================

st.divider()

st.subheader("📅 Season-by-Season")


season_rows = []


for year, season in matchups.groupby("year"):

    a_wins = int(
        (season["result"] == "W").sum()
    )

    a_losses = int(
        (season["result"] == "L").sum()
    )

    season_ties = int(
        (season["result"] == "T").sum()
    )

    b_wins = a_losses
    b_losses = a_wins

    if a_wins > b_wins:
        season_winner = team_a

    elif b_wins > a_wins:
        season_winner = team_b

    else:
        season_winner = "Split"

    record_a = f"{a_wins}-{a_losses}"

    record_b = f"{b_wins}-{b_losses}"

    if season_ties:
        record_a += f"-{season_ties}"
        record_b += f"-{season_ties}"

    season_rows.append(
        {
            "Season": int(year),
            team_a: record_a,
            team_b: record_b,
            "Series Winner": season_winner,
            f"{team_a} Points": round(
                season["points_for"].sum(),
                2,
            ),
            f"{team_b} Points": round(
                season["points_against"].sum(),
                2,
            ),
        }
    )


season_df = pd.DataFrame(
    season_rows
).sort_values(
    "Season",
    ascending=False,
)


st.dataframe(
    season_df,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# COMPLETE MATCHUP HISTORY
# ============================================================

st.divider()

st.subheader("📜 Complete Matchup History")


history = matchups[
    [
        "year",
        "week",
        "points_for",
        "points_against",
    ]
].copy()


history["Winner"] = matchups.apply(
    get_winner,
    axis=1,
)

history["Margin"] = (
    matchups["abs_margin"]
)


history = history.rename(
    columns={
        "year": "Season",
        "week": "Week",
        "points_for": team_a,
        "points_against": team_b,
    }
)


history = history[
    [
        "Season",
        "Week",
        team_a,
        team_b,
        "Winner",
        "Margin",
    ]
]


history = history.sort_values(
    ["Season", "Week"],
    ascending=[False, False],
)


st.dataframe(
    history,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Season": st.column_config.NumberColumn(
            "Season",
            format="%d",
        ),
        "Week": st.column_config.NumberColumn(
            "Week",
            format="%d",
        ),
        team_a: st.column_config.NumberColumn(
            team_a,
            format="%.2f",
        ),
        team_b: st.column_config.NumberColumn(
            team_b,
            format="%.2f",
        ),
        "Margin": st.column_config.NumberColumn(
            "Margin",
            format="%.2f",
        ),
    },
)