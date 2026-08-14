import streamlit as st
import pandas as pd


st.set_page_config(
    page_title="Head-to-Head",
    page_icon="⚔️",
    layout="wide",
)


st.title("⚔️ Head-to-Head History")

st.caption(
    "Because nothing says friendship like keeping a permanent record "
    "of every time someone beat you."
)


# ---------------------------------------------------------
# SAMPLE DATA
# ---------------------------------------------------------

teams = [
    "The Fighting Mongooses",
    "Team Suck It",
    "The Winners",
    "Sunday Scaries",
    "Gridiron Idiots",
    "Fourth and Drunk",
    "Waiver Wire Warriors",
    "Points Are Overrated",
    "Bye Week Bandits",
    "Auto Draft Heroes",
    "Commissioner's Mistake",
    "Participation Trophy",
]


# Sample head-to-head records.
#
# The format is:
#
# team -> opponent -> [wins, losses]

head_to_head = {
    "The Fighting Mongooses": {
        "Team Suck It": [8, 4],
        "The Winners": [6, 5],
        "Sunday Scaries": [7, 3],
        "Gridiron Idiots": [9, 2],
        "Fourth and Drunk": [10, 3],
        "Waiver Wire Warriors": [8, 4],
        "Points Are Overrated": [11, 1],
        "Bye Week Bandits": [9, 2],
        "Auto Draft Heroes": [7, 1],
        "Commissioner's Mistake": [12, 2],
        "Participation Trophy": [10, 1],
    },

    "Team Suck It": {
        "The Fighting Mongooses": [4, 8],
        "The Winners": [7, 6],
        "Sunday Scaries": [6, 5],
        "Gridiron Idiots": [7, 4],
        "Fourth and Drunk": [8, 5],
        "Waiver Wire Warriors": [6, 4],
        "Points Are Overrated": [9, 3],
        "Bye Week Bandits": [7, 2],
        "Auto Draft Heroes": [8, 1],
        "Commissioner's Mistake": [9, 5],
        "Participation Trophy": [10, 2],
    },

    "The Winners": {
        "The Fighting Mongooses": [5, 6],
        "Team Suck It": [6, 7],
        "Sunday Scaries": [7, 4],
        "Gridiron Idiots": [8, 3],
        "Fourth and Drunk": [6, 5],
        "Waiver Wire Warriors": [7, 3],
        "Points Are Overrated": [8, 2],
        "Bye Week Bandits": [6, 3],
        "Auto Draft Heroes": [7, 2],
        "Commissioner's Mistake": [8, 4],
        "Participation Trophy": [9, 1],
    },

    "Sunday Scaries": {},
    "Gridiron Idiots": {},
    "Fourth and Drunk": {},
    "Waiver Wire Warriors": {},
    "Points Are Overrated": {},
    "Bye Week Bandits": {},
    "Auto Draft Heroes": {},
    "Commissioner's Mistake": {},
    "Participation Trophy": {},
}


# ---------------------------------------------------------
# HEAD-TO-HEAD MATRIX
# ---------------------------------------------------------

st.subheader("📊 All-Time Matchup Matrix")

st.write(
    """
    Each cell shows the selected team's all-time record against
    the opponent.

    **W–L**
    """
)


matrix = []

for team in teams:

    row = []

    for opponent in teams:

        if team == opponent:

            row.append("—")

        elif opponent in head_to_head.get(team, {}):

            record = head_to_head[team][opponent]

            row.append(
                f"{record[0]}–{record[1]}"
            )

        else:

            row.append("—")

    matrix.append(row)


matrix_df = pd.DataFrame(
    matrix,
    index=teams,
    columns=teams,
)


st.dataframe(
    matrix_df,
    use_container_width=True,
)


# ---------------------------------------------------------
# SELECT A TEAM
# ---------------------------------------------------------

st.divider()

st.subheader("🔎 Explore a Rivalry")

selected_team = st.selectbox(
    "Choose a team",
    teams,
)


if selected_team:

    st.markdown(
        f"### {selected_team}"
    )

    records = []

    for opponent in teams:

        if opponent == selected_team:
            continue

        if opponent in head_to_head.get(selected_team, {}):

            wins, losses = head_to_head[
                selected_team
            ][opponent]

            games = wins + losses

            win_percentage = (
                wins / games * 100
            )

            records.append(
                {
                    "Opponent": opponent,
                    "Wins": wins,
                    "Losses": losses,
                    "Win %": round(
                        win_percentage,
                        1,
                    ),
                }
            )


    if records:

        rivalry_df = pd.DataFrame(
            records
        )

        rivalry_df = rivalry_df.sort_values(
            "Win %",
            ascending=False,
        )


        st.dataframe(
            rivalry_df,
            use_container_width=True,
            hide_index=True,
        )


# ---------------------------------------------------------
# BIGGEST RIVALRY
# ---------------------------------------------------------

st.divider()

st.subheader("🔥 Notable Rivalry")

st.info(
    """
    ### The Fighting Mongooses vs. Commissioner's Mistake

    **All-Time Record:**

    The Fighting Mongooses — **12–2**

    Commissioner's Mistake — **2–12**

    Analysts have determined that this is less of a rivalry
    and more of an annual public service.
    """
)


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    "All statistics are currently fictional. "
    "Yahoo historical data will eventually replace these numbers."
)