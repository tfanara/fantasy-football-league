import streamlit as st
import pandas as pd


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Teams",
    page_icon="👥",
    layout="wide",
)


# ---------------------------------------------------------
# SAMPLE TEAM DATA
# ---------------------------------------------------------

teams = [
    {
        "team": "The Fighting Mongooses",
        "owner": "Steve",
        "championships": 2,
        "all_time_wins": 86,
        "all_time_losses": 72,
        "best_finish": "1st",
        "nickname": "The Mongooses",
    },
    {
        "team": "Team Suck It",
        "owner": "Dave",
        "championships": 1,
        "all_time_wins": 79,
        "all_time_losses": 79,
        "best_finish": "1st",
        "nickname": "Suck It",
    },
    {
        "team": "The Winners",
        "owner": "Mike",
        "championships": 1,
        "all_time_wins": 75,
        "all_time_losses": 83,
        "best_finish": "1st",
        "nickname": "The Winners",
    },
    {
        "team": "Sunday Scaries",
        "owner": "Chris",
        "championships": 1,
        "all_time_wins": 71,
        "all_time_losses": 87,
        "best_finish": "1st",
        "nickname": "Scaries",
    },
    {
        "team": "Gridiron Idiots",
        "owner": "Jeff",
        "championships": 0,
        "all_time_wins": 68,
        "all_time_losses": 90,
        "best_finish": "2nd",
        "nickname": "Idiots",
    },
    {
        "team": "Fourth and Drunk",
        "owner": "Matt",
        "championships": 0,
        "all_time_wins": 63,
        "all_time_losses": 95,
        "best_finish": "3rd",
        "nickname": "Drunk",
    },
    {
        "team": "Waiver Wire Warriors",
        "owner": "Tom",
        "championships": 0,
        "all_time_wins": 61,
        "all_time_losses": 97,
        "best_finish": "3rd",
        "nickname": "Warriors",
    },
    {
        "team": "Points Are Overrated",
        "owner": "Ryan",
        "championships": 0,
        "all_time_wins": 58,
        "all_time_losses": 100,
        "best_finish": "4th",
        "nickname": "Overrated",
    },
    {
        "team": "Bye Week Bandits",
        "owner": "Jason",
        "championships": 0,
        "all_time_wins": 54,
        "all_time_losses": 104,
        "best_finish": "5th",
        "nickname": "Bandits",
    },
    {
        "team": "Auto Draft Heroes",
        "owner": "Kevin",
        "championships": 0,
        "all_time_wins": 48,
        "all_time_losses": 110,
        "best_finish": "6th",
        "nickname": "Auto Draft",
    },
    {
        "team": "Commissioner's Mistake",
        "owner": "Malle",
        "championships": 0,
        "all_time_wins": 42,
        "all_time_losses": 116,
        "best_finish": "7th",
        "nickname": "Malle",
    },
    {
        "team": "Participation Trophy",
        "owner": "Alex",
        "championships": 0,
        "all_time_wins": 35,
        "all_time_losses": 123,
        "best_finish": "8th",
        "nickname": "Trophy",
    },
]


# ---------------------------------------------------------
# PAGE HEADER
# ---------------------------------------------------------

st.title("👥 The Franchises")

st.caption(
    "The 12 brave souls who have voluntarily subjected themselves "
    "to fantasy football since 2017."
)


# ---------------------------------------------------------
# TEAM SUMMARY
# ---------------------------------------------------------

total_championships = sum(
    team["championships"] for team in teams
)

most_wins = max(
    team["all_time_wins"] for team in teams
)

worst_wins = min(
    team["all_time_wins"] for team in teams
)


col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Teams",
        len(teams),
    )

with col2:
    st.metric(
        "Championships",
        total_championships,
    )

with col3:
    st.metric(
        "Best All-Time Wins",
        most_wins,
    )


st.divider()


# ---------------------------------------------------------
# TEAM DIRECTORY
# ---------------------------------------------------------

st.subheader("🏈 Team Directory")


for team in teams:

    st.markdown("---")

    col1, col2, col3 = st.columns([4, 2, 2])

    with col1:

        st.markdown(
            f"### {team['team']}"
        )

        st.write(
            f"**Owner:** {team['owner']}"
        )

        st.caption(
            f"Also known as: {team['nickname']}"
        )

    with col2:

        st.metric(
            "Championships",
            team["championships"],
        )

    with col3:

        record = (
            f"{team['all_time_wins']}-"
            f"{team['all_time_losses']}"
        )

        st.metric(
            "All-Time Record",
            record,
        )

    st.write(
        f"**Best Finish:** {team['best_finish']}"
    )


st.divider()


# ---------------------------------------------------------
# ALL-TIME WIN LEADERS
# ---------------------------------------------------------

st.subheader("📈 All-Time Win Leaders")


win_data = pd.DataFrame(
    [
        {
            "Team": team["team"],
            "Owner": team["owner"],
            "Wins": team["all_time_wins"],
            "Losses": team["all_time_losses"],
            "Win %": round(
                team["all_time_wins"]
                / (
                    team["all_time_wins"]
                    + team["all_time_losses"]
                )
                * 100,
                1,
            ),
        }
        for team in teams
    ]
)


win_data = win_data.sort_values(
    "Wins",
    ascending=False,
).reset_index(drop=True)


win_data.insert(
    0,
    "Rank",
    range(1, len(win_data) + 1),
)


st.dataframe(
    win_data,
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# COMMISSIONER SECTION
# ---------------------------------------------------------

st.divider()

st.subheader("🚨 Special Recognition")

st.error(
    """
    **Malle — Commissioner**

    All-time record: 42–116

    Championships: 0

    Best finish: 7th

    Despite these historically unimpressive numbers, Malle continues
    to insist that the league's problems are caused by everyone else.

    The league has formally rejected this explanation.
    """
)