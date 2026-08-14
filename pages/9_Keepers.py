import streamlit as st
import pandas as pd


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Keeper History",
    page_icon="🛡️",
    layout="wide",
)


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.title("🛡️ Keeper History")

st.caption(
    "A permanent record of who was kept, who was kept again, "
    "and who has officially run out of chances."
)

st.divider()


# ---------------------------------------------------------
# SAMPLE KEEPER DATA
# ---------------------------------------------------------
#
# IMPORTANT:
#
# Each row represents ONE player being kept by ONE team
# for ONE season.
#
# keeper_year:
#   1 = first keeper season
#   2 = second/final keeper season
#
# This structure will eventually be replaced by Yahoo data.
# ---------------------------------------------------------

keeper_data = [

    # 2026
    {
        "year": 2026,
        "team": "Team Alpha",
        "owner": "Owner Alpha",
        "player": "Player One",
        "position": "RB",
        "keeper_year": 2,
    },

    {
        "year": 2026,
        "team": "Team Bravo",
        "owner": "Owner Bravo",
        "player": "Player Two",
        "position": "WR",
        "keeper_year": 1,
    },

    {
        "year": 2026,
        "team": "Team Charlie",
        "owner": "Owner Charlie",
        "player": "Player Three",
        "position": "RB",
        "keeper_year": 2,
    },

    {
        "year": 2026,
        "team": "Team Delta",
        "owner": "Owner Delta",
        "player": "Player Four",
        "position": "WR",
        "keeper_year": 1,
    },

    # 2025
    {
        "year": 2025,
        "team": "Team Alpha",
        "owner": "Owner Alpha",
        "player": "Player One",
        "position": "RB",
        "keeper_year": 1,
    },

    {
        "year": 2025,
        "team": "Team Bravo",
        "owner": "Owner Bravo",
        "player": "Player Five",
        "position": "RB",
        "keeper_year": 2,
    },

    {
        "year": 2025,
        "team": "Team Charlie",
        "owner": "Owner Charlie",
        "player": "Player Three",
        "position": "RB",
        "keeper_year": 1,
    },

    # 2024
    {
        "year": 2024,
        "team": "Team Bravo",
        "owner": "Owner Bravo",
        "player": "Player Five",
        "position": "RB",
        "keeper_year": 1,
    },

]


keepers_df = pd.DataFrame(keeper_data)


# ---------------------------------------------------------
# YEAR SELECTOR
# ---------------------------------------------------------

years = sorted(
    keepers_df["year"].unique(),
    reverse=True,
)

selected_year = st.selectbox(
    "Select a season",
    years,
)


# ---------------------------------------------------------
# CURRENT YEAR KEEPERS
# ---------------------------------------------------------

st.header(
    f"🛡️ {selected_year} Keepers"
)


season_keepers = keepers_df[
    keepers_df["year"] == selected_year
].copy()


if not season_keepers.empty:

    display_df = season_keepers[
        [
            "team",
            "owner",
            "player",
            "position",
            "keeper_year",
        ]
    ].copy()


    display_df.columns = [
        "Team",
        "Owner",
        "Player",
        "Position",
        "Keeper Year",
    ]


    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.info(
        "No keeper data is available for this season."
    )


# ---------------------------------------------------------
# KEEPER YEAR SUMMARY
# ---------------------------------------------------------

st.divider()

st.header("📊 Keeper Summary")


col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "Total Keepers",
        len(season_keepers),
    )


with col2:

    first_year = len(
        season_keepers[
            season_keepers["keeper_year"] == 1
        ]
    )

    st.metric(
        "First-Year Keepers",
        first_year,
    )


with col3:

    second_year = len(
        season_keepers[
            season_keepers["keeper_year"] == 2
        ]
    )

    st.metric(
        "Final-Year Keepers",
        second_year,
    )


# ---------------------------------------------------------
# PLAYER KEEPER HISTORY
# ---------------------------------------------------------

st.divider()

st.header("🔎 Player Keeper History")


players = sorted(
    keepers_df["player"].unique()
)


selected_player = st.selectbox(
    "Select a player",
    players,
)


player_history = keepers_df[
    keepers_df["player"] == selected_player
].copy()


player_history = player_history.sort_values(
    "year"
)


if not player_history.empty:

    st.subheader(
        f"{selected_player}"
    )


    for _, row in player_history.iterrows():

        if row["keeper_year"] == 1:

            status = "🟢 First Keeper Year"

        else:

            status = "🟠 Second / Final Keeper Year"


        st.markdown(
            f"""
            **{row['year']}** — {row['team']}  
            {row['position']} • {status}
            """
        )


    st.divider()

    keeper_count = len(
        player_history
    )


    if keeper_count >= 2:

        st.error(
            f"""
            🔴 **Keeper limit reached**

            {selected_player} has been kept **{keeper_count} times**
            and cannot be kept again under the current rules.
            """
        )

    else:

        st.success(
            f"""
            🟢 **Keeper eligible**

            {selected_player} has been kept **{keeper_count} time(s)**.
            """
        )


# ---------------------------------------------------------
# TEAM KEEPER HISTORY
# ---------------------------------------------------------

st.divider()

st.header("👤 Team Keeper History")


teams = sorted(
    keepers_df["team"].unique()
)


selected_team = st.selectbox(
    "Select a team",
    teams,
)


team_history = keepers_df[
    keepers_df["team"] == selected_team
].copy()


team_history = team_history.sort_values(
    ["year", "keeper_year"],
    ascending=[False, True],
)


team_display = team_history[
    [
        "year",
        "player",
        "position",
        "keeper_year",
    ]
].copy()


team_display.columns = [
    "Season",
    "Player",
    "Position",
    "Keeper Year",
]


st.dataframe(
    team_display,
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# KEEPER LIMIT
# ---------------------------------------------------------

st.divider()

st.header("⚖️ Keeper Limit")

st.info(
    """
    ### Current Rule

    A player may be kept for a maximum of **two seasons**.

    **Keeper Year 1** → Eligible to be kept again

    **Keeper Year 2** → Final keeper season

    **After Year 2** → Player must return to the draft pool
    """
)


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    "Keeper History • Malle Is The Worst Commissioner"
)