import streamlit as st


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="League Rules",
    page_icon="📜",
    layout="wide",
)


# ---------------------------------------------------------
# PAGE HEADER
# ---------------------------------------------------------

st.title("📜 The Rules")

st.caption(
    "The legally binding document governing the league, "
    "except when the commissioner decides it doesn't."
)


st.divider()


# ---------------------------------------------------------
# LEAGUE BASICS
# ---------------------------------------------------------

st.header("🏈 League Basics")

st.markdown(
    """
    ### League Name

    **Malle Is The Worst Commissioner**

    ### Founded

    **2017**

    ### Number of Teams

    **12**

    ### Current Season

    **2026**

    ### League Type

    **Fantasy Football**
    """
)


# ---------------------------------------------------------
# GENERAL RULES
# ---------------------------------------------------------

st.header("📋 General Rules")

rules = [
    (
        "1. Set Your Lineup",
        """
        Managers are responsible for setting their lineups before
        the applicable game deadlines.

        If you start an injured player who has been ruled OUT,
        that is your problem.
        """,
    ),

    (
        "2. Check Your Bye Weeks",
        """
        If half your lineup is on a bye week, nobody is going to
        feel sorry for you.

        The NFL schedule has been publicly available for decades.
        """,
    ),

    (
        "3. Trades",
        """
        Trades are permitted during the designated trading period.

        Managers are encouraged to negotiate in good faith.

        Managers are also encouraged to remember that nobody is
        obligated to accept your terrible offer.
        """,
    ),

    (
        "4. Waiver Wire",
        """
        The waiver wire is available to all managers according
        to the league's Yahoo settings.

        "I didn't know he was available" is not an acceptable excuse.
        """,
    ),

    (
        "5. Playoffs",
        """
        The league playoffs will be determined according to the
        official Yahoo league settings.

        Regular-season records determine playoff qualification.

        Therefore, winning games is generally considered helpful.
        """,
    ),

    (
        "6. Tanking",
        """
        Deliberately fielding an inferior lineup may result in
        public ridicule.

        Public ridicule is not technically a league penalty,
        but it is strongly encouraged.
        """,
    ),
]


for title, text in rules:

    with st.expander(title, expanded=True):

        st.markdown(text)


# ---------------------------------------------------------
# COMMISSIONER POWERS
# ---------------------------------------------------------

st.header("👑 Commissioner Powers")

st.warning(
    """
    ### Commissioner Authority

    The commissioner is responsible for maintaining the league,
    managing settings, resolving disputes, and generally making
    everyone's life more difficult.

    However:

    **Commissioner authority does not automatically make the
    commissioner correct.**

    In fact, historical evidence suggests the opposite.
    """
)


# ---------------------------------------------------------
# DISPUTE RESOLUTION
# ---------------------------------------------------------

st.header("⚖️ Disputes")

st.markdown(
    """
    ### Step 1

    Bring the issue to the commissioner.

    ### Step 2

    Argue about it in the league group chat.

    ### Step 3

    Get increasingly angry.

    ### Step 4

    Accuse someone of cheating.

    ### Step 5

    Eventually realize the Yahoo rules were correct.

    ### Step 6

    Pretend the argument never happened.
    """
)


# ---------------------------------------------------------
# TRASH TALK
# ---------------------------------------------------------

st.header("🔥 Trash Talk Policy")

st.markdown(
    """
    Trash talk is **strongly encouraged**.

    Managers are permitted to criticize:

    - Draft decisions
    - Lineup decisions
    - Trades
    - Waiver claims
    - Coaching decisions
    - Fantasy football knowledge
    - General decision-making ability

    Managers may **not** use personal attacks that go beyond
    normal league trash talk.

    The goal is to make the league entertaining, not ruin
    friendships.
    """
)


# ---------------------------------------------------------
# COMMISSIONER DISCLAIMER
# ---------------------------------------------------------

st.divider()

st.error(
    """
    ## ⚠️ Commissioner Disclaimer

    The commissioner reserves the right to interpret these rules.

    The league reserves the right to question the commissioner's
    interpretation.

    The commissioner reserves the right to ignore those questions.

    The league reserves the right to complain about it forever.

    **This document is not legally binding.**

    Unless Malle says otherwise.
    """
)


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    "Malle Is The Worst Commissioner • Est. 2017"
)