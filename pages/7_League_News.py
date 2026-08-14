import streamlit as st


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="League News",
    page_icon="📰",
    layout="wide",
)


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.title("📰 League News")

st.caption(
    "Breaking news, questionable analysis, and completely unnecessary "
    "personal attacks from around the league."
)


st.divider()


# ---------------------------------------------------------
# FEATURED STORY
# ---------------------------------------------------------

st.subheader("🚨 BREAKING NEWS")


st.markdown(
    """
    # MALLE STILL THINKS HE'S A GOOD COMMISSIONER

    **August 14, 2026**

    In a development that has surprised absolutely nobody,
    Malle has once again defended his record as commissioner.

    When presented with the fact that his team has never won a
    championship, Malle reportedly responded:

    > "That's completely unrelated to my performance as commissioner."

    League officials have confirmed that it is, in fact,
    extremely related.

    Sources close to the league say Malle is currently reviewing
    the league constitution for a rule that would allow him to
    retroactively award himself a championship.

    No such rule has been found.

    **The investigation continues.**
    """
)


st.divider()


# ---------------------------------------------------------
# LATEST STORIES
# ---------------------------------------------------------

st.header("📡 Latest Stories")


stories = [
    {
        "date": "August 14, 2026",
        "headline": "12 Managers Enter. One Will Pretend They Knew What They Were Doing.",
        "category": "2026 Preview",
        "text": """
        The 2026 season is officially underway.

        Twelve managers have once again convinced themselves that
        this is the year.

        Eleven of them are wrong.
        """,
    },

    {
        "date": "August 12, 2026",
        "headline": "Commissioner Announces Bold New Vision Nobody Asked For",
        "category": "Commissioner Watch",
        "text": """
        Malle has unveiled a bold new vision for the league.

        Unfortunately, nobody knows what the vision actually is.

        League sources describe it as "mostly emails."
        """,
    },

    {
        "date": "August 10, 2026",
        "headline": "Preseason Power Rankings Released",
        "category": "Power Rankings",
        "text": """
        The league's annual preseason power rankings have been
        released.

        Several managers have already complained about their ranking.

        Those managers are ranked near the bottom.
        """,
    },

    {
        "date": "August 5, 2026",
        "headline": "League Enters Tenth Year of Questionable Decision-Making",
        "category": "History",
        "text": """
        Founded in 2017, the league continues to survive despite
        numerous questionable trades, draft selections, and lineup
        decisions.

        Experts remain unsure how.
        """,
    },
]


for story in stories:

    with st.container():

        st.markdown(
            f"### {story['headline']}"
        )

        st.caption(
            f"{story['date']} • {story['category']}"
        )

        st.write(
            story["text"]
        )

        st.markdown("---")


# ---------------------------------------------------------
# COMMISSIONER WATCH
# ---------------------------------------------------------

st.header("🚨 Commissioner Watch")


col1, col2 = st.columns(2)


with col1:

    st.metric(
        "Commissioner Approval Rating",
        "12%",
        "-7%",
    )


with col2:

    st.metric(
        "Confidence in Commissioner",
        "Low",
        "Lower",
    )


st.error(
    """
    ### Current Commissioner Status

    🟥 **UNDER REVIEW**

    The league remains unconvinced that Malle should be allowed
    to continue making decisions.

    Unfortunately, nobody else wants the job.
    """
)


# ---------------------------------------------------------
# HOT TAKES
# ---------------------------------------------------------

st.header("🔥 League Hot Takes")


hot_takes = [
    "Someone will draft a player who is already injured.",
    "At least one manager will forget to set their lineup.",
    "Someone will complain about a trade they were offered and rejected.",
    "Malle will blame Yahoo.",
    "The team with the most confidence after the draft will finish terribly.",
    "Someone will claim they were 'busy' immediately after losing.",
]


for i, take in enumerate(hot_takes, start=1):

    st.markdown(
        f"**{i}.** {take}"
    )


# ---------------------------------------------------------
# HALL OF SHAME
# ---------------------------------------------------------

st.divider()

st.header("💀 Hall of Shame")


st.markdown(
    """
    ### Coming Soon

    Once historical Yahoo data is connected, this section will
    automatically identify the most embarrassing performances in
    league history.

    Potential categories include:

    - 💩 Worst Loss
    - 🤦 Worst Lineup Decision
    - 🥶 Lowest Score
    - 🔥 Biggest Choke
    - 💀 Worst Draft Pick
    - 🚑 Most Injured Team
    - 🧠 Worst Trade
    - 👑 Most Ridiculous Commissioner Decision
    """
)


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    "Malle Is The Worst Commissioner • Independent League Journalism Since 2017"
)