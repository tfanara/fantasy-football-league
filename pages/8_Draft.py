import streamlit as st
import pandas as pd


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Draft",
    page_icon="🏈",
    layout="wide",
)


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.title("🏈 Draft Archive")

st.caption(
    "Every draft since 2017 — the order, the picks, "
    "and the decisions everyone wishes they could take back."
)

st.divider()


# ---------------------------------------------------------
# SAMPLE DRAFT ORDER
# ---------------------------------------------------------

draft_orders = {

    2026: [
        "Team Alpha",
        "Team Bravo",
        "Team Charlie",
        "Team Delta",
        "Team Echo",
        "Team Foxtrot",
        "Team Golf",
        "Team Hotel",
        "Team India",
        "Team Juliet",
        "Team Kilo",
        "Team Lima",
    ],

    2025: [
        "Team Lima",
        "Team Kilo",
        "Team Juliet",
        "Team India",
        "Team Hotel",
        "Team Golf",
        "Team Foxtrot",
        "Team Echo",
        "Team Delta",
        "Team Charlie",
        "Team Bravo",
        "Team Alpha",
    ],

}


# ---------------------------------------------------------
# SAMPLE DRAFT RESULTS
# ---------------------------------------------------------

draft_results = [

    # 2026
    {
        "year": 2026,
        "round": 1,
        "pick": 1,
        "team": "Team Alpha",
        "owner": "Owner Alpha",
        "player": "Player One",
        "position": "RB",
    },
    {
        "year": 2026,
        "round": 1,
        "pick": 2,
        "team": "Team Bravo",
        "owner": "Owner Bravo",
        "player": "Player Two",
        "position": "WR",
    },
    {
        "year": 2026,
        "round": 1,
        "pick": 3,
        "team": "Team Charlie",
        "owner": "Owner Charlie",
        "player": "Player Three",
        "position": "RB",
    },
    {
        "year": 2026,
        "round": 1,
        "pick": 4,
        "team": "Team Delta",
        "owner": "Owner Delta",
        "player": "Player Four",
        "position": "WR",
    },
    {
        "year": 2026,
        "round": 1,
        "pick": 5,
        "team": "Team Echo",
        "owner": "Owner Echo",
        "player": "Player Five",
        "position": "RB",
    },
    {
        "year": 2026,
        "round": 1,
        "pick": 6,
        "team": "Team Foxtrot",
        "owner": "Owner Foxtrot",
        "player": "Player Six",
        "position": "WR",
    },

    # 2025
    {
        "year": 2025,
        "round": 1,
        "pick": 1,
        "team": "Team Lima",
        "owner": "Owner Lima",
        "player": "Player Seven",
        "position": "RB",
    },
    {
        "year": 2025,
        "round": 1,
        "pick": 2,
        "team": "Team Kilo",
        "owner": "Owner Kilo",
        "player": "Player Eight",
        "position": "WR",
    },
    {
        "year": 2025,
        "round": 1,
        "pick": 3,
        "team": "Team Juliet",
        "owner": "Owner Juliet",
        "player": "Player Nine",
        "position": "RB",
    },
    {
        "year": 2025,
        "round": 1,
        "pick": 4,
        "team": "Team India",
        "owner": "Owner India",
        "player": "Player Ten",
        "position": "WR",
    },
]


draft_df = pd.DataFrame(draft_results)


# ---------------------------------------------------------
# YEAR SELECTOR
# ---------------------------------------------------------

available_years = sorted(
    set(draft_orders.keys())
    | set(draft_df["year"].unique()),
    reverse=True,
)


selected_year = st.selectbox(
    "Select a season",
    available_years,
)


# ---------------------------------------------------------
# DRAFT ORDER
# ---------------------------------------------------------

st.header(f"📋 {selected_year} Draft Order")

order = draft_orders.get(
    selected_year,
    []
)


if order:

    order_data = []

    for pick, team in enumerate(order, start=1):

        order_data.append(
            {
                "Pick": pick,
                "Team": team,
            }
        )


    order_df = pd.DataFrame(order_data)


    # Display in three columns so the order doesn't
    # take up the entire page.

    col1, col2, col3 = st.columns(3)


    for index, row in order_df.iterrows():

        pick = row["Pick"]
        team = row["Team"]

        if pick <= 4:
            target_col = col1

        elif pick <= 8:
            target_col = col2

        else:
            target_col = col3


        with target_col:

            st.markdown(
                f"**{pick}.** {team}"
            )


else:

    st.info(
        "Draft order data for this season has not been entered yet."
    )


# ---------------------------------------------------------
# SNAKE DRAFT
# ---------------------------------------------------------

if order:

    st.subheader("🐍 Snake Draft Order")

    st.write(
        "The draft order alternates direction each round."
    )

    snake_rounds = []

    for round_number in range(1, 5):

        if round_number % 2 == 1:

            round_order = order

        else:

            round_order = list(
                reversed(order)
            )


        snake_rounds.append(
            {
                "Round": round_number,
                "Order": " → ".join(
                    str(i + 1)
                    for i in range(len(round_order))
                ),
            }
        )


    snake_df = pd.DataFrame(
        snake_rounds
    )


    st.dataframe(
        snake_df,
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------
# DRAFT RESULTS
# ---------------------------------------------------------

st.divider()

st.header(f"🏈 {selected_year} Draft Results")


season_draft = draft_df[
    draft_df["year"] == selected_year
].copy()


if not season_draft.empty:

    display_df = season_draft[
        [
            "round",
            "pick",
            "team",
            "owner",
            "player",
            "position",
        ]
    ].copy()


    display_df.columns = [
        "Round",
        "Pick",
        "Team",
        "Owner",
        "Player",
        "Position",
    ]


    display_df = display_df.sort_values(
        ["Round", "Pick"]
    )


    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )


else:

    st.info(
        "Draft results for this season have not been entered yet."
    )


# ---------------------------------------------------------
# ROUND-BY-ROUND VIEW
# ---------------------------------------------------------

if not season_draft.empty:

    st.divider()

    st.header("🔎 Round-by-Round")


    rounds = sorted(
        season_draft["round"].unique()
    )


    for round_number in rounds:

        round_data = season_draft[
            season_draft["round"] == round_number
        ].copy()


        with st.expander(
            f"Round {round_number}",
            expanded=(round_number == 1),
        ):

            round_display = round_data[
                [
                    "pick",
                    "team",
                    "player",
                    "position",
                ]
            ].copy()


            round_display.columns = [
                "Pick",
                "Team",
                "Player",
                "Position",
            ]


            st.dataframe(
                round_display,
                use_container_width=True,
                hide_index=True,
            )


# ---------------------------------------------------------
# TEAM DRAFT HISTORY
# ---------------------------------------------------------

st.divider()

st.header("👤 Team Draft History")

if not draft_df.empty:

    selected_team = st.selectbox(
        "Select a team",
        sorted(
            draft_df["team"].unique()
        ),
    )


    team_history = draft_df[
        draft_df["team"] == selected_team
    ].copy()


    team_history = team_history.sort_values(
        ["year", "pick"],
        ascending=[False, True],
    )


    team_display = team_history[
        [
            "year",
            "round",
            "pick",
            "player",
            "position",
        ]
    ].copy()


    team_display.columns = [
        "Season",
        "Round",
        "Pick",
        "Player",
        "Position",
    ]


    st.dataframe(
        team_display,
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------
# COMING SOON
# ---------------------------------------------------------

st.divider()

st.header("🔮 Coming Soon")

st.markdown(
    """
    Once Yahoo historical draft data is connected, this page will
    automatically contain the complete draft history from **2017
    through 2026**.

    We'll also be able to calculate:

    - 🏆 Best draft pick
    - 💩 Worst draft pick
    - 📈 Draft position vs. player performance
    - 🔥 Best draft class
    - 💀 Biggest draft bust
    - 🤦 Biggest reach
    - 🥇 Most successful draft position
    - 👑 Best drafter in league history
    """
)


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    "Malle Is The Worst Commissioner • Draft Archive"
)