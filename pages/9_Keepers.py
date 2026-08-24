import streamlit as st
import pandas as pd
from pathlib import Path


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Keeper History | Malle's League",
    page_icon="🔒",
    layout="wide",
)

st.title("🔒 Keeper History")

st.caption(
    "Who was worth keeping, who kept coming back, "
    "and what draft capital each franchise paid."
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

KEEPER_FILE = (
    BASE_DIR
    / "data"
    / "keepers"
    / "keeper_history.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_keeper_data():

    df = pd.read_csv(
        KEEPER_FILE
    )

    numeric_columns = [
        "year",
        "round_kept_in",
        "pick_in_round",
        "overall_pick",
        "keeper_number",
        "previous_year_round",
        "original_draft_year",
        "original_draft_round",
        "expected_round",
        "next_keeper_round",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df


try:

    keepers = load_keeper_data()

except FileNotFoundError:

    st.error(
        "Keeper history was not found. "
        "Run `python build_keeper_history.py` first."
    )

    st.stop()


if keepers.empty:

    st.warning(
        "No keeper selections were found."
    )

    st.stop()


# ============================================================
# BASIC VALUES
# ============================================================

years = sorted(
    keepers["year"]
    .dropna()
    .astype(int)
    .unique()
)

teams = sorted(
    keepers["team"]
    .dropna()
    .unique()
)

latest_year = max(years)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_round(value):

    if pd.isna(value):
        return "—"

    return int(value)


def clean_text(value):

    if pd.isna(value):
        return "—"

    text = str(value).strip()

    if not text:
        return "—"

    return text


def status_icon(status):

    if status == "1st-Year Keeper":
        return "🟢"

    if status == "2nd-Year Keeper — Final Year":
        return "🟡"

    if status == "Keeper Limit Exception":
        return "🔴"

    return "⚪"


def next_status_icon(status):

    status = str(status)

    if status.startswith("Eligible"):
        return "🟢"

    if "Must Return" in status:
        return "🔴"

    return "⚪"


# ============================================================
# OVERVIEW
# ============================================================

st.divider()

st.header("Keeper Overview")


c1, c2, c3, c4 = st.columns(4)


c1.metric(
    "Keeper Selections",
    len(keepers),
)


c2.metric(
    "Seasons With Keepers",
    keepers["year"].nunique(),
)


c3.metric(
    "Players Kept",
    keepers["player"].nunique(),
)


c4.metric(
    "Franchises With Keepers",
    keepers["team"].nunique(),
)


# ============================================================
# CURRENT KEEPER STATUS
# ============================================================

st.divider()

st.header(
    f"{latest_year} Keeper Status"
)

st.caption(
    "Current keeper status and next-season eligibility "
    "based on the league's keeper rules."
)


current = (
    keepers[
        keepers["year"] == latest_year
    ]
    .copy()
    .sort_values(
        [
            "team",
            "round_kept_in",
        ]
    )
)


current["Status"] = current[
    "keeper_status"
].apply(
    lambda x:
        f"{status_icon(x)} {x}"
)


current["Next Season"] = current[
    "next_season_status"
].apply(
    lambda x:
        f"{next_status_icon(x)} {x}"
)


current_display = (
    current[
        [
            "team",
            "player",
            "round_kept_in",
            "Status",
            "acquisition_basis",
            "Next Season",
        ]
    ]
    .rename(
        columns={
            "team":
                "Franchise",

            "player":
                "Player",

            "round_kept_in":
                "Round Kept In",

            "acquisition_basis":
                "Keeper Basis",
        }
    )
)


st.dataframe(
    current_display,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# CURRENT ELIGIBILITY SUMMARY
# ============================================================

eligible = current[
    current["next_season_status"]
    .astype(str)
    .str.startswith("Eligible")
]

must_return = current[
    current["next_season_status"]
    == "Must Return to Draft Pool"
]

limit_exceptions_current = current[
    current["keeper_status"]
    == "Keeper Limit Exception"
]


c1, c2, c3 = st.columns(3)


c1.metric(
    f"Eligible for {latest_year + 1}",
    len(eligible),
)


c2.metric(
    "Must Return to Draft Pool",
    len(must_return),
)


c3.metric(
    "Keeper Limit Exceptions",
    len(limit_exceptions_current),
)


# ============================================================
# NEXT SEASON ELIGIBILITY
# ============================================================

st.subheader(
    f"{latest_year + 1} Keeper Eligibility"
)


if eligible.empty:

    st.info(
        "No current keepers are eligible "
        "to be kept next season."
    )

else:

    eligibility_display = (
        eligible[
            [
                "team",
                "player",
                "next_keeper_round",
            ]
        ]
        .copy()
        .rename(
            columns={
                "team":
                    "Franchise",

                "player":
                    "Player",

                "next_keeper_round":
                    f"{latest_year + 1} Round",
            }
        )
    )

    eligibility_display[
        f"{latest_year + 1} Round"
    ] = (
        eligibility_display[
            f"{latest_year + 1} Round"
        ]
        .apply(clean_round)
    )

    st.dataframe(
        eligibility_display,
        hide_index=True,
        use_container_width=True,
    )


# ============================================================
# KEEPERS BY SEASON
# ============================================================

st.divider()

st.header("Keepers by Season")


selected_year = st.selectbox(
    "Choose a season",
    years,
    index=len(years) - 1,
)


year_keepers = (
    keepers[
        keepers["year"]
        == selected_year
    ]
    .copy()
    .sort_values(
        "overall_pick"
    )
)


if year_keepers.empty:

    st.info(
        f"No keeper selections were recorded in "
        f"{selected_year}."
    )

else:

    st.metric(
        f"{selected_year} Keepers",
        len(year_keepers),
    )


    year_keepers["Status"] = (
        year_keepers[
            "keeper_status"
        ]
        .apply(
            lambda x:
                f"{status_icon(x)} {x}"
        )
    )


    year_display = (
        year_keepers[
            [
                "team",
                "player",
                "round_kept_in",
                "Status",
                "acquisition_basis",
                "pick_in_round",
                "overall_pick",
            ]
        ]
        .rename(
            columns={
                "team":
                    "Franchise",

                "player":
                    "Player",

                "round_kept_in":
                    "Round Kept In",

                "acquisition_basis":
                    "Keeper Basis",

                "pick_in_round":
                    "Pick in Round",

                "overall_pick":
                    "Overall Pick",
            }
        )
    )


    st.dataframe(
        year_display,
        hide_index=True,
        use_container_width=True,
    )


# ============================================================
# KEEPER STATUS LEGEND
# ============================================================

with st.expander(
    "How keeper status works"
):

    st.markdown(
        """
**🟢 1st-Year Keeper**  
The player's first season being kept. If retained again,
the keeper moves up one round the following season.

**🟡 2nd-Year Keeper — Final Year**  
The player's second keeper season. The player must return
to the draft pool after this season.

**🔴 Keeper Limit Exception**  
The player was kept beyond the normal two-season keeper
limit.

### Keeper round rules

- A drafted player's keeper value moves up one round the
  following season.
- A later drop or waiver/free-agent acquisition does not
  erase an existing draft-round value.
- An undrafted waiver/free-agent acquisition begins with a
  Round 10 keeper value.
"""
    )


# ============================================================
# KEEPER USAGE BY SEASON
# ============================================================

st.subheader("Keeper Usage by Season")


keeper_counts = (
    keepers
    .groupby(
        "year"
    )
    .size()
    .reindex(
        years,
        fill_value=0,
    )
    .rename(
        "Keepers"
    )
    .to_frame()
)


st.bar_chart(
    keeper_counts
)


# ============================================================
# MOST-KEPT PLAYERS
# ============================================================

st.divider()

st.header("Most-Kept Players")


player_counts = (
    keepers
    .groupby(
        "player"
    )
    .agg(
        Times_Kept=(
            "year",
            "size",
        ),

        Seasons=(
            "year",
            "nunique",
        ),

        Franchises=(
            "team",
            "nunique",
        ),

        First_Kept=(
            "year",
            "min",
        ),

        Last_Kept=(
            "year",
            "max",
        ),

        Average_Round=(
            "round_kept_in",
            "mean",
        ),
    )
    .reset_index()
)


player_counts[
    "Average_Round"
] = (
    player_counts[
        "Average_Round"
    ]
    .round(1)
)


player_counts = (
    player_counts
    .sort_values(
        [
            "Times_Kept",
            "Seasons",
            "Average_Round",
        ],
        ascending=[
            False,
            False,
            False,
        ],
    )
)


player_display = (
    player_counts
    .rename(
        columns={
            "player":
                "Player",

            "Times_Kept":
                "Times Kept",

            "Seasons":
                "Keeper Seasons",

            "Franchises":
                "Different Franchises",

            "First_Kept":
                "First Kept",

            "Last_Kept":
                "Most Recent",

            "Average_Round":
                "Average Round Kept In",
        }
    )
)


st.dataframe(
    player_display,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# KEEPER LOYALTY
# ============================================================

st.divider()

st.header("Keeper Loyalty")


loyalty = (
    keepers
    .groupby(
        [
            "team",
            "player",
        ]
    )
    .agg(
        Times_Kept=(
            "year",
            "size",
        ),

        First_Kept=(
            "year",
            "min",
        ),

        Last_Kept=(
            "year",
            "max",
        ),

        Average_Round=(
            "round_kept_in",
            "mean",
        ),
    )
    .reset_index()
)


loyalty[
    "Average_Round"
] = (
    loyalty[
        "Average_Round"
    ]
    .round(1)
)


loyalty = (
    loyalty[
        loyalty["Times_Kept"]
        > 1
    ]
    .sort_values(
        [
            "Times_Kept",
            "Average_Round",
        ],
        ascending=[
            False,
            False,
        ],
    )
)


loyalty_display = (
    loyalty
    .rename(
        columns={
            "team":
                "Franchise",

            "player":
                "Player",

            "Times_Kept":
                "Times Kept",

            "First_Kept":
                "First Kept",

            "Last_Kept":
                "Most Recent",

            "Average_Round":
                "Average Round Kept In",
        }
    )
)


if loyalty_display.empty:

    st.info(
        "No player has been kept multiple times "
        "by the same franchise."
    )

else:

    st.dataframe(
        loyalty_display,
        hide_index=True,
        use_container_width=True,
    )


# ============================================================
# FRANCHISE KEEPER HISTORY
# ============================================================

st.divider()

st.header("Franchise Keeper History")


selected_team = st.selectbox(
    "Choose a franchise",
    teams,
    key="keeper_team",
)


team_keepers = (
    keepers[
        keepers["team"]
        == selected_team
    ]
    .copy()
    .sort_values(
        [
            "year",
            "round_kept_in",
        ],
        ascending=[
            False,
            True,
        ],
    )
)


if team_keepers.empty:

    st.info(
        f"No keeper selections are recorded for "
        f"{selected_team}."
    )

else:

    c1, c2, c3, c4 = st.columns(4)


    c1.metric(
        "Total Keepers",
        len(team_keepers),
    )


    c2.metric(
        "Keeper Seasons",
        team_keepers[
            "year"
        ].nunique(),
    )


    c3.metric(
        "Unique Players Kept",
        team_keepers[
            "player"
        ].nunique(),
    )


    c4.metric(
        "Average Round Kept In",
        f"{team_keepers['round_kept_in'].mean():.1f}",
    )


    team_keepers["Status"] = (
        team_keepers[
            "keeper_status"
        ]
        .apply(
            lambda x:
                f"{status_icon(x)} {x}"
        )
    )


    team_display = (
        team_keepers[
            [
                "year",
                "player",
                "round_kept_in",
                "Status",
                "acquisition_basis",
                "next_season_status",
            ]
        ]
        .rename(
            columns={
                "year":
                    "Season",

                "player":
                    "Player",

                "round_kept_in":
                    "Round Kept In",

                "acquisition_basis":
                    "Keeper Basis",

                "next_season_status":
                    "Following Season",
            }
        )
    )


    st.dataframe(
        team_display,
        hide_index=True,
        use_container_width=True,
    )


# ============================================================
# KEEPER USAGE BY FRANCHISE
# ============================================================

st.divider()

st.header("Keeper Usage by Franchise")


team_usage = (
    keepers
    .groupby(
        "team"
    )
    .agg(
        Total_Keepers=(
            "year",
            "size",
        ),

        Keeper_Seasons=(
            "year",
            "nunique",
        ),

        Unique_Players=(
            "player",
            "nunique",
        ),

        Average_Round=(
            "round_kept_in",
            "mean",
        ),
    )
    .reset_index()
)


team_usage[
    "Average_Round"
] = (
    team_usage[
        "Average_Round"
    ]
    .round(1)
)


team_usage = (
    team_usage
    .sort_values(
        [
            "Total_Keepers",
            "Keeper_Seasons",
        ],
        ascending=[
            False,
            False,
        ],
    )
)


team_usage_display = (
    team_usage
    .rename(
        columns={
            "team":
                "Franchise",

            "Total_Keepers":
                "Total Keepers",

            "Keeper_Seasons":
                "Keeper Seasons",

            "Unique_Players":
                "Unique Players",

            "Average_Round":
                "Average Round Kept In",
        }
    )
)


st.dataframe(
    team_usage_display,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# MOST EXPENSIVE KEEPERS
# ============================================================

st.divider()

st.header("Most Expensive Keepers")


expensive = (
    keepers
    .sort_values(
        [
            "round_kept_in",
            "overall_pick",
        ]
    )
    .head(20)
)


expensive_display = (
    expensive[
        [
            "year",
            "team",
            "player",
            "round_kept_in",
            "keeper_status",
        ]
    ]
    .rename(
        columns={
            "year":
                "Season",

            "team":
                "Franchise",

            "player":
                "Player",

            "round_kept_in":
                "Round Kept In",

            "keeper_status":
                "Keeper Status",
        }
    )
)


st.dataframe(
    expensive_display,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# LATE-ROUND KEEPER VALUES
# ============================================================

st.divider()

st.header("Late-Round Keeper Values")


cheap = (
    keepers
    .sort_values(
        [
            "round_kept_in",
            "overall_pick",
        ],
        ascending=[
            False,
            False,
        ],
    )
    .head(20)
)


cheap_display = (
    cheap[
        [
            "year",
            "team",
            "player",
            "round_kept_in",
            "keeper_status",
        ]
    ]
    .rename(
        columns={
            "year":
                "Season",

            "team":
                "Franchise",

            "player":
                "Player",

            "round_kept_in":
                "Round Kept In",

            "keeper_status":
                "Keeper Status",
        }
    )
)


st.dataframe(
    cheap_display,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# HISTORICAL ROUND EXCEPTIONS
# ============================================================

st.divider()

st.header("Keeper Rule Exceptions")


round_exceptions = (
    keepers[
        keepers[
            "rule_status"
        ].isin(
            [
                "Historical Round Exception",
                "Round Rule Exception",
            ]
        )
    ]
    .copy()
    .sort_values(
        "year",
        ascending=False,
    )
)


limit_exceptions = (
    keepers[
        keepers[
            "keeper_status"
        ]
        == "Keeper Limit Exception"
    ]
    .copy()
    .sort_values(
        "year",
        ascending=False,
    )
)


if (
    round_exceptions.empty
    and limit_exceptions.empty
):

    st.success(
        "No keeper rule exceptions are recorded."
    )

else:

    if not round_exceptions.empty:

        st.subheader(
            "Round Exceptions"
        )

        st.caption(
            "These keeper selections occurred at a "
            "different round than the standard keeper "
            "progression predicts."
        )


        round_exception_display = (
            round_exceptions[
                [
                    "year",
                    "team",
                    "player",
                    "previous_year_round",
                    "expected_round",
                    "round_kept_in",
                ]
            ]
            .copy()
            .rename(
                columns={
                    "year":
                        "Season",

                    "team":
                        "Franchise",

                    "player":
                        "Player",

                    "previous_year_round":
                        "Previous Round",

                    "expected_round":
                        "Expected Round",

                    "round_kept_in":
                        "Round Kept In",
                }
            )
        )


        for column in [
            "Previous Round",
            "Expected Round",
            "Round Kept In",
        ]:

            round_exception_display[
                column
            ] = (
                round_exception_display[
                    column
                ]
                .apply(clean_round)
            )


        st.dataframe(
            round_exception_display,
            hide_index=True,
            use_container_width=True,
        )


    if not limit_exceptions.empty:

        st.subheader(
            "Keeper Limit Exceptions"
        )

        st.caption(
            "These players were kept beyond the normal "
            "two-season keeper limit."
        )


        limit_exception_display = (
            limit_exceptions[
                [
                    "year",
                    "team",
                    "player",
                    "keeper_number",
                    "round_kept_in",
                ]
            ]
            .rename(
                columns={
                    "year":
                        "Season",

                    "team":
                        "Franchise",

                    "player":
                        "Player",

                    "keeper_number":
                        "Keeper Year",

                    "round_kept_in":
                        "Round Kept In",
                }
            )
        )


        st.dataframe(
            limit_exception_display,
            hide_index=True,
            use_container_width=True,
        )


# ============================================================
# KEEPER MATRIX
# ============================================================

st.divider()

st.header(
    "Keeper Count by Franchise and Season"
)


keeper_matrix = (
    keepers
    .groupby(
        [
            "team",
            "year",
        ]
    )
    .size()
    .unstack(
        fill_value=0
    )
)


for year in years:

    if year not in keeper_matrix.columns:

        keeper_matrix[
            year
        ] = 0


keeper_matrix = (
    keeper_matrix[
        sorted(
            keeper_matrix.columns
        )
    ]
)


keeper_matrix[
    "Total"
] = (
    keeper_matrix.sum(
        axis=1
    )
)


keeper_matrix.index.name = (
    "Franchise"
)


st.dataframe(
    keeper_matrix,
    use_container_width=True,
)


# ============================================================
# FOOTNOTE
# ============================================================

st.divider()

st.caption(
    "Keeper selections and Round Kept In come from Yahoo's "
    "historical Draft Results. Keeper status, eligibility, "
    "and expected keeper rounds are calculated from the "
    "league's keeper rules and historical transaction data."
)