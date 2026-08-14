import streamlit as st
import pandas as pd


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Malle Is The Worst Commissioner",
    page_icon="🏈",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------
# SAMPLE DATA
# ---------------------------------------------------------

teams = [
    {
        "Team": "The Fighting Mongooses",
        "Owner": "Steve",
        "W": 8,
        "L": 2,
        "PF": 1245.7,
        "PA": 1087.3,
    },
    {
        "Team": "Team Suck It",
        "Owner": "Dave",
        "W": 7,
        "L": 3,
        "PF": 1212.4,
        "PA": 1121.8,
    },
    {
        "Team": "The Winners",
        "Owner": "Mike",
        "W": 6,
        "L": 4,
        "PF": 1198.6,
        "PA": 1143.2,
    },
    {
        "Team": "Sunday Scaries",
        "Owner": "Chris",
        "W": 5,
        "L": 5,
        "PF": 1172.1,
        "PA": 1168.4,
    },
    {
        "Team": "Gridiron Idiots",
        "Owner": "Jeff",
        "W": 5,
        "L": 5,
        "PF": 1103.8,
        "PA": 1187.5,
    },
    {
        "Team": "Fourth and Drunk",
        "Owner": "Matt",
        "W": 4,
        "L": 6,
        "PF": 1088.2,
        "PA": 1192.7,
    },
    {
        "Team": "The Waiver Wire Warriors",
        "Owner": "Tom",
        "W": 4,
        "L": 6,
        "PF": 1064.5,
        "PA": 1201.3,
    },
    {
        "Team": "Points Are Overrated",
        "Owner": "Ryan",
        "W": 3,
        "L": 7,
        "PF": 1011.6,
        "PA": 1234.9,
    },
    {
        "Team": "The Bye Week Bandits",
        "Owner": "Jason",
        "W": 3,
        "L": 7,
        "PF": 998.3,
        "PA": 1251.8,
    },
    {
        "Team": "Auto Draft Heroes",
        "Owner": "Kevin",
        "W": 2,
        "L": 8,
        "PF": 941.2,
        "PA": 1278.6,
    },
    {
        "Team": "Commissioner's Mistake",
        "Owner": "Malle",
        "W": 2,
        "L": 8,
        "PF": 921.7,
        "PA": 1302.4,
    },
    {
        "Team": "Participation Trophy",
        "Owner": "Alex",
        "W": 1,
        "L": 9,
        "PF": 876.4,
        "PA": 1331.7,
    },
]


standings = pd.DataFrame(teams)

standings = standings.sort_values(
    by=["W", "PF"],
    ascending=[False, False]
).reset_index(drop=True)

standings.insert(0, "Rank", range(1, len(standings) + 1))


# ---------------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------------

st.markdown(
    """
    <style>

    .main-title {
        font-size: 2.5rem;
        font-weight: 900;
        text-align: center;
        margin-bottom: 0;
    }

    .subtitle {
        text-align: center;
        font-size: 1.2rem;
        font-style: italic;
        margin-bottom: 2rem;
    }

    .section-title {
        font-size: 1.8rem;
        font-weight: 800;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }

    .news-card {
        padding: 1.2rem;
        border-radius: 10px;
        border: 1px solid rgba(128,128,128,.3);
        margin-bottom: 1rem;
    }

    .news-headline {
        font-size: 1.25rem;
        font-weight: 800;
    }

    .small-text {
        font-size: .9rem;
        opacity: .75;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:

    st.title("🏈 League Menu")

    st.markdown("---")

    st.markdown("### Current Season")
    st.markdown("**2026**")

    st.markdown("---")

    st.markdown("### League History")
    st.markdown("2017 → 2026")

    st.markdown("---")

    st.caption(
        "An unofficial archive of the greatest "
        "fantasy football league ever assembled."
    )


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.markdown(
    '<div class="main-title">🏈 MALLE IS THE WORST COMMISSIONER</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'The official unofficial history of a league that somehow survived since 2017.'
    '</div>',
    unsafe_allow_html=True,
)

st.divider()


# ---------------------------------------------------------
# TOP METRICS
# ---------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Teams",
        "12",
    )

with col2:
    st.metric(
        "Seasons",
        "10",
    )

with col3:
    st.metric(
        "Current Season",
        "2026",
    )

with col4:
    st.metric(
        "Commissioner Rating",
        "14/100",
        delta="-3",
    )


# ---------------------------------------------------------
# COMMISSIONER WATCH
# ---------------------------------------------------------

st.markdown(
    '<div class="section-title">🚨 COMMISSIONER WATCH</div>',
    unsafe_allow_html=True,
)

st.warning(
    """
    **Commissioner Malle has once again demonstrated a complete disregard
    for the well-being of the league.**

    League officials are currently investigating how someone with
    administrative privileges has managed to make the league worse every
    single year since 2017.

    **Current Commissioner Rating: 14/100**
    """
)


# ---------------------------------------------------------
# STANDINGS
# ---------------------------------------------------------

st.markdown(
    '<div class="section-title">🏆 2026 STANDINGS</div>',
    unsafe_allow_html=True,
)

display_standings = standings[
    ["Rank", "Team", "Owner", "W", "L", "PF", "PA"]
].copy()

display_standings["PF"] = display_standings["PF"].round(1)
display_standings["PA"] = display_standings["PA"].round(1)

st.dataframe(
    display_standings,
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# POWER RANKINGS
# ---------------------------------------------------------

st.markdown(
    '<div class="section-title">🔥 TOTALLY SCIENTIFIC POWER RANKINGS</div>',
    unsafe_allow_html=True,
)

power_rankings = [
    ("The Fighting Mongooses", "Probably legitimate."),
    ("Team Suck It", "Suspiciously competent."),
    ("The Winners", "Name checks out."),
    ("Sunday Scaries", "Terrified of Monday."),
    ("Gridiron Idiots", "The name is accurate."),
    ("Fourth and Drunk", "At least they're consistent."),
    ("Waiver Wire Warriors", "Living exclusively on hope."),
    ("Points Are Overrated", "They certainly seem to think so."),
    ("Bye Week Bandits", "They keep forgetting their players."),
    ("Auto Draft Heroes", "Technology is doing most of the work."),
    ("Commissioner's Mistake", "The mistake was letting Malle play."),
    ("Participation Trophy", "Congratulations on participating."),
]

for i, (team, commentary) in enumerate(power_rankings, start=1):

    col1, col2, col3 = st.columns([1, 4, 5])

    with col1:
        st.write(f"**#{i}**")

    with col2:
        st.write(f"**{team}**")

    with col3:
        st.write(commentary)


# ---------------------------------------------------------
# LEAGUE NEWS
# ---------------------------------------------------------

st.markdown(
    '<div class="section-title">📰 THE LEAGUE PRESS</div>',
    unsafe_allow_html=True,
)

news = [
    (
        "BREAKING: Local Manager Discovers the Waiver Wire",
        "After nine consecutive weeks of starting injured players, "
        "sources confirm that one manager has finally discovered "
        "the waiver wire. Scientists are calling it 'an unprecedented breakthrough.'",
    ),
    (
        "Commissioner Denies Any Wrongdoing",
        "Malle released a statement Tuesday insisting that every "
        "controversial league decision since 2017 was 'completely reasonable.' "
        "Nobody interviewed for this article agreed.",
    ),
    (
        "Team Owner Claims 3–7 Record Is Actually Encouraging",
        "The owner explained that the team is 'statistically better than "
        "the record suggests.' Experts have confirmed that this is "
        "something people say when their record is 3–7.",
    ),
]

for headline, article in news:

    st.markdown(
        f"""
        <div class="news-card">
            <div class="news-headline">{headline}</div>
            <p>{article}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# RECORDS
# ---------------------------------------------------------

st.markdown(
    '<div class="section-title">📊 LEAGUE RECORDS</div>',
    unsafe_allow_html=True,
)

record_col1, record_col2, record_col3 = st.columns(3)

with record_col1:
    st.metric(
        "Highest Single-Week Score",
        "214.82",
    )

with record_col2:
    st.metric(
        "Lowest Single-Week Score",
        "51.34",
    )

with record_col3:
    st.metric(
        "Biggest Blowout",
        "103.41 pts",
    )


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    "Malle Is The Worst Commissioner • Est. 2017 • "
    "Currently surviving against all odds"
)