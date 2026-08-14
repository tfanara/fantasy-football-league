import streamlit as st


st.set_page_config(
    page_title="League History",
    page_icon="🏆",
    layout="wide",
)


st.title("🏆 League History")

st.caption("A decade of questionable decisions.")


history = [
    {
        "year": 2017,
        "champion": "Team Alpha",
        "runner_up": "Team Beta",
        "story": "The league begins. Nobody knows what they're doing yet.",
    },
    {
        "year": 2018,
        "champion": "Team Bravo",
        "runner_up": "Team Charlie",
        "story": "Someone discovers the waiver wire.",
    },
    {
        "year": 2019,
        "champion": "Team Delta",
        "runner_up": "Team Alpha",
        "story": "A controversial trade divides the league.",
    },
    {
        "year": 2020,
        "champion": "Team Echo",
        "runner_up": "Team Bravo",
        "story": "Everyone pretends they understand fantasy football.",
    },
    {
        "year": 2021,
        "champion": "Team Alpha",
        "runner_up": "Team Foxtrot",
        "story": "The dynasty begins.",
    },
    {
        "year": 2022,
        "champion": "Team Golf",
        "runner_up": "Team Echo",
        "story": "An upset nobody saw coming.",
    },
    {
        "year": 2023,
        "champion": "Team Hotel",
        "runner_up": "Team Alpha",
        "story": "The commissioner makes another questionable decision.",
    },
    {
        "year": 2024,
        "champion": "Team Alpha",
        "runner_up": "Team Golf",
        "story": "Apparently some people never learn.",
    },
    {
        "year": 2025,
        "champion": "Team Juliet",
        "runner_up": "Team Hotel",
        "story": "A new champion emerges.",
    },
    {
        "year": 2026,
        "champion": "TBD",
        "runner_up": "TBD",
        "story": "The season is currently underway.",
    },
]


for season in history:

    st.markdown(f"## {season['year']}")

    col1, col2 = st.columns(2)

    with col1:
        st.write(f"🏆 **Champion:** {season['champion']}")

    with col2:
        st.write(f"🥈 **Runner-Up:** {season['runner_up']}")

    st.write(season["story"])

    st.divider()