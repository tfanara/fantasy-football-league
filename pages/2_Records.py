import streamlit as st


st.set_page_config(
    page_title="League Records",
    page_icon="📊",
    layout="wide",
)


st.title("📊 League Records")

st.caption(
    "The most impressive accomplishments in league history. "
    "And some of the most embarrassing."
)


st.subheader("🏆 The Good")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Most Wins — Season",
        "12",
    )

with col2:
    st.metric(
        "Highest Score",
        "214.82",
    )

with col3:
    st.metric(
        "Largest Win",
        "103.41 pts",
    )


st.divider()


st.subheader("💀 The Bad")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Lowest Score",
        "51.34",
    )

with col2:
    st.metric(
        "Worst Record",
        "1–12",
    )

with col3:
    st.metric(
        "Largest Loss",
        "101.72 pts",
    )


st.divider()


st.subheader("🤡 The Hall of Shame")

shame = [
    ["Most Points Left on Bench", "237.4", "Someone who refuses to start good players"],
    ["Worst Draft Pick", "1st Round", "A running back who immediately got injured"],
    ["Longest Losing Streak", "9 games", "A remarkable display of consistency"],
    ["Most Questionable Trade", "2021", "Still under investigation"],
    ["Worst Lineup Decision", "Week 8", "Started a player on a bye"],
]

st.table(
    {
        "Record": [x[0] for x in shame],
        "Value": [x[1] for x in shame],
        "Details": [x[2] for x in shame],
    }
)