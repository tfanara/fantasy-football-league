import streamlit as st
import pandas as pd


st.set_page_config(
    page_title="2026 Standings",
    page_icon="🏆",
    layout="wide",
)


st.title("🏆 2026 Standings")

st.caption(
    "The standings are fake for now. "
    "Eventually Yahoo will provide the numbers."
)


teams = [
    ["The Fighting Mongooses", "Steve", 8, 2, 1245.7, 1087.3],
    ["Team Suck It", "Dave", 7, 3, 1212.4, 1121.8],
    ["The Winners", "Mike", 6, 4, 1198.6, 1143.2],
    ["Sunday Scaries", "Chris", 5, 5, 1172.1, 1168.4],
    ["Gridiron Idiots", "Jeff", 5, 5, 1103.8, 1187.5],
    ["Fourth and Drunk", "Matt", 4, 6, 1088.2, 1192.7],
    ["Waiver Wire Warriors", "Tom", 4, 6, 1064.5, 1201.3],
    ["Points Are Overrated", "Ryan", 3, 7, 1011.6, 1234.9],
    ["Bye Week Bandits", "Jason", 3, 7, 998.3, 1251.8],
    ["Auto Draft Heroes", "Kevin", 2, 8, 941.2, 1278.6],
    ["Commissioner's Mistake", "Malle", 2, 8, 921.7, 1302.4],
    ["Participation Trophy", "Alex", 1, 9, 876.4, 1331.7],
]


df = pd.DataFrame(
    teams,
    columns=[
        "Team",
        "Owner",
        "Wins",
        "Losses",
        "Points For",
        "Points Against",
    ],
)


df.insert(0, "Rank", range(1, len(df) + 1))


st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
)


st.divider()


st.subheader("🔥 Power Rankings")

rankings = [
    ("The Fighting Mongooses", "Unfortunately competent."),
    ("Team Suck It", "Suspiciously good."),
    ("The Winners", "The name is doing a lot of work."),
    ("Sunday Scaries", "Terrified of Monday."),
    ("Gridiron Idiots", "At least the branding is honest."),
    ("Fourth and Drunk", "Consistency is important."),
    ("Waiver Wire Warriors", "Still searching for a quarterback."),
    ("Points Are Overrated", "They've certainly embraced the philosophy."),
    ("Bye Week Bandits", "The bye weeks are winning."),
    ("Auto Draft Heroes", "Alexa is apparently managing the team."),
    ("Commissioner's Mistake", "The mistake was allowing Malle to compete."),
    ("Participation Trophy", "Congratulations on showing up."),
]


for number, (team, comment) in enumerate(rankings, 1):

    col1, col2, col3 = st.columns([1, 4, 6])

    with col1:
        st.write(f"**#{number}**")

    with col2:
        st.write(f"**{team}**")

    with col3:
        st.write(comment)