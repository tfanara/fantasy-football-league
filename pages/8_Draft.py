import streamlit as st
import pandas as pd
from pathlib import Path

try:
    from team_aliases import canonical_team
except ImportError:
    def canonical_team(name):
        return name


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Draft History | Malle's League",
    page_icon="📝",
    layout="wide",
)

st.title("📝 Draft History")
st.caption(
    "Every pick from every completed draft, plus the official 2026 draft order."
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DRAFT_FILE = BASE_DIR / "data" / "drafts" / "all_drafts.csv"
STRATEGY_FILE = BASE_DIR / "data" / "drafts" / "draft_position_strategy.csv"
ALL_STANDINGS_FILE = BASE_DIR / "data" / "all_standings.csv"


# ============================================================
# COMPACT / MOBILE-FRIENDLY TABLES
# ============================================================

COMPACT_TABLE_ROW_HEIGHT = 26
COMPACT_TABLE_MAX_VISIBLE_ROWS = 12
COMPACT_TABLE_HEADER_HEIGHT = 38


def compact_dataframe(
    data,
    *,
    hide_index=False,
    use_container_width=True,
    column_config=None,
    height=None,
    max_visible_rows=COMPACT_TABLE_MAX_VISIBLE_ROWS,
    **kwargs,
):
    """
    Mobile-friendly Streamlit dataframe wrapper.

    - Uses shorter rows so more data fits on screen.
    - Tables with 12 or fewer rows display all rows without
      vertical scrolling.
    - Larger tables display up to 12 rows before scrolling.
    """

    try:
        row_count = len(data)
    except TypeError:
        row_count = max_visible_rows

    if height is None:
        visible_rows = min(max(row_count, 1), max_visible_rows)
        height = (
            COMPACT_TABLE_HEADER_HEIGHT
            + (visible_rows * COMPACT_TABLE_ROW_HEIGHT)
            + 4
        )

    dataframe_kwargs = dict(
        hide_index=hide_index,
        use_container_width=use_container_width,
        height=height,
        column_config=column_config,
        **kwargs,
    )

    # row_height is supported by current Streamlit versions.
    # The fallback prevents an older Streamlit install from
    # breaking the page.
    try:
        return st.dataframe(
            data,
            row_height=COMPACT_TABLE_ROW_HEIGHT,
            **dataframe_kwargs,
        )
    except TypeError:
        return st.dataframe(
            data,
            **dataframe_kwargs,
        )


# ============================================================
# 2026 DRAFT ORDER
# ============================================================

DRAFT_ORDER_2026 = [
    "malle_dips_pouches",
    "Patty Primetimes",
    "Joe Mantegna",
    "Malle ❤️ 🐸",
    "Buttermilk Puuump",
    "ThreatLevelMidnight",
    "The Big Gronkowski",
    "Pop Lockett Drop it",
    "Voldemort",
    "Post Mahomes",
    "Uncle Rico",
    "Ginger FC",
]


KEEPERS_2026 = {
    "Patty Primetimes": {
        "player": "Colston Loveland",
        "round": 10,
        "status": "🟢 1st-Year Keeper",
        "acquisition": "Drafted — Round 11",
    },
    "Joe Mantegna": {
        "player": "Tyler Warren",
        "round": 9,
        "status": "🟢 1st-Year Keeper",
        "acquisition": "Drafted — Round 10",
    },
    "ThreatLevelMidnight": {
        "player": "Rashee Rice",
        "round": 6,
        "status": "🟢 1st-Year Keeper",
        "acquisition": "Drafted — Round 7",
    },
    "The Big Gronkowski": {
        "player": "Drake Maye",
        "round": 8,
        "status": "🟢 1st-Year Keeper",
        "acquisition": "Drafted — Round 9",
    },
    "Pop Lockett Drop it": {
        "player": "Kenneth Walker III",
        "round": 1,
        "status": "🟢 1st-Year Keeper",
        "acquisition": "Drafted — Round 2",
    },
    "Voldemort": {
        "player": "Jaxon Smith-Njigba",
        "round": 2,
        "status": "🟢 1st-Year Keeper",
        "acquisition": "Drafted — Round 3",
    },
    "Uncle Rico": {
        "player": "Jonathan Taylor",
        "round": 1,
        "status": "🟢 1st-Year Keeper",
        "acquisition": "Drafted — Round 2",
    },
}


draft_order_2026 = pd.DataFrame(
    {
        "Draft Position": range(1, len(DRAFT_ORDER_2026) + 1),
        "Franchise": DRAFT_ORDER_2026,
    }
)


draft_order_2026["2026 Keeper"] = (
    draft_order_2026["Franchise"]
    .map(
        lambda team: KEEPERS_2026.get(
            team,
            {},
        ).get(
            "player",
            "—",
        )
    )
)


draft_order_2026["Keeper Round"] = (
    draft_order_2026["Franchise"]
    .map(
        lambda team: KEEPERS_2026.get(
            team,
            {},
        ).get(
            "round",
            pd.NA,
        )
    )
    .astype("Int64")
)


draft_order_2026["Keeper Status"] = (
    draft_order_2026["Franchise"]
    .map(
        lambda team: KEEPERS_2026.get(
            team,
            {},
        ).get(
            "status",
            "—",
        )
    )
)


draft_order_2026["2025 Acquisition"] = (
    draft_order_2026["Franchise"]
    .map(
        lambda team: KEEPERS_2026.get(
            team,
            {},
        ).get(
            "acquisition",
            "—",
        )
    )
)


draft_order_2026 = draft_order_2026[
    [
        "Draft Position",
        "Franchise",
        "2026 Keeper",
        "2025 Acquisition",
        "Keeper Round",
        "Keeper Status",
    ]
]


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_drafts():

    df = pd.read_csv(DRAFT_FILE)

    for col in [
        "year",
        "round",
        "pick_in_round",
        "overall_pick",
    ]:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    return df


try:

    drafts = load_drafts()

except FileNotFoundError:

    st.error(
        "Draft data not found. Run "
        "`python yahoo_collect_drafts.py` first."
    )

    st.stop()


# ============================================================
# SUMMARY DATA
# ============================================================

years = sorted(
    drafts["year"]
    .dropna()
    .astype(int)
    .unique()
)

teams = sorted(
    drafts["team"]
    .dropna()
    .unique()
)

players = sorted(
    drafts["player"]
    .dropna()
    .unique()
)


# ============================================================
# SUMMARY CARDS
# ============================================================

st.divider()

c1, c2, c3, c4 = st.columns(4)


c1.metric(
    "Drafts Tracked",
    len(years),
)


c2.metric(
    "Total Picks",
    len(drafts),
)


c3.metric(
    "Franchises",
    len(teams),
)


c4.metric(
    "Unique Players Drafted",
    drafts["player"].nunique(),
)


# ============================================================
# 2026 DRAFT ORDER
# ============================================================

st.divider()

st.header("🏈 2026 Draft Order")

st.caption(
    "The official 2026 first-round draft order, including keeper selections "
    "that have already been submitted. The 2026 draft itself has not taken place yet."
)

compact_dataframe(
    draft_order_2026,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Draft Position":
            st.column_config.NumberColumn(
                "Pos",
                format="%d",
                width="small",
            ),

        "Franchise":
            st.column_config.TextColumn(
                "Franchise",
                width="medium",
            ),

        "2026 Keeper":
            st.column_config.TextColumn(
                "Keeper",
                width="medium",
            ),

        "2025 Acquisition":
            st.column_config.TextColumn(
                "Acquired",
                width="medium",
            ),

        "Keeper Round":
            st.column_config.NumberColumn(
                "Rd",
                format="%d",
                width="small",
            ),

        "Keeper Status":
            st.column_config.TextColumn(
                "Status",
                width="medium",
            ),
    },
)


# ============================================================
# DRAFT BY SEASON
# ============================================================

st.divider()

st.header("Draft by Season")


selected_year = st.selectbox(
    "Choose a draft",
    years,
    index=len(years) - 1,
)


year_df = (
    drafts[
        drafts["year"]
        == selected_year
    ]
    .copy()
    .sort_values(
        "overall_pick"
    )
)


# ============================================================
# FIRST ROUND
# ============================================================

st.subheader(
    f"{selected_year} First Round"
)


first_round = (
    year_df[
        year_df["round"] == 1
    ]
    .copy()
)


first_round_display = (
    first_round[
        [
            "overall_pick",
            "team",
            "player",
        ]
    ]
    .rename(
        columns={
            "overall_pick": "Pick",
            "team": "Franchise",
            "player": "Player",
        }
    )
)


compact_dataframe(
    first_round_display,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# COMPLETE DRAFT
# ============================================================

st.subheader("Complete Draft")


view_mode = st.radio(
    "View draft by",
    [
        "Round",
        "Franchise",
    ],
    horizontal=True,
)


# ------------------------------------------------------------
# ROUND VIEW
# ------------------------------------------------------------

if view_mode == "Round":

    selected_round = st.selectbox(
        "Choose round",
        sorted(
            year_df[
                "round"
            ]
            .astype(int)
            .unique()
        ),
    )


    round_df = (
        year_df[
            year_df["round"]
            == selected_round
        ]
        .copy()
        .sort_values(
            "pick_in_round"
        )
    )


    round_display = (
        round_df[
            [
                "pick_in_round",
                "overall_pick",
                "team",
                "player",
            ]
        ]
        .rename(
            columns={
                "pick_in_round":
                    "Pick in Round",
                "overall_pick":
                    "Overall",
                "team":
                    "Franchise",
                "player":
                    "Player",
            }
        )
    )


    compact_dataframe(
        round_display,
        hide_index=True,
        use_container_width=True,
    )


# ------------------------------------------------------------
# FRANCHISE VIEW
# ------------------------------------------------------------

else:

    selected_team = st.selectbox(
        "Choose franchise",
        sorted(
            year_df[
                "team"
            ]
            .unique()
        ),
    )


    team_draft = (
        year_df[
            year_df["team"]
            == selected_team
        ]
        .copy()
        .sort_values(
            "overall_pick"
        )
    )


    team_display = (
        team_draft[
            [
                "round",
                "pick_in_round",
                "overall_pick",
                "player",
            ]
        ]
        .rename(
            columns={
                "round":
                    "Round",
                "pick_in_round":
                    "Pick in Round",
                "overall_pick":
                    "Overall",
                "player":
                    "Player",
            }
        )
    )


    compact_dataframe(
        team_display,
        hide_index=True,
        use_container_width=True,
    )


# ============================================================
# DRAFT ORDER
# ============================================================

st.divider()

st.header("Selected Season Draft Order")


draft_order = (
    first_round[
        [
            "pick_in_round",
            "team",
        ]
    ]
    .sort_values(
        "pick_in_round"
    )
    .rename(
        columns={
            "pick_in_round":
                "Draft Position",
            "team":
                "Franchise",
        }
    )
)


compact_dataframe(
    draft_order,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# FRANCHISE DRAFT HISTORY
# ============================================================

st.divider()

st.header("Franchise Draft History")


franchise = st.selectbox(
    "Choose a franchise",
    teams,
    key="draft_franchise",
)


franchise_history = (
    drafts[
        drafts["team"]
        == franchise
    ]
    .copy()
)


franchise_years = sorted(
    franchise_history[
        "year"
    ]
    .astype(int)
    .unique()
)


first_round_count = len(
    franchise_history[
        franchise_history[
            "round"
        ] == 1
    ]
)


c1, c2, c3 = st.columns(3)


c1.metric(
    "Drafts",
    len(franchise_years),
)


c2.metric(
    "Total Picks",
    len(franchise_history),
)


c3.metric(
    "First-Round Picks",
    first_round_count,
)


# ============================================================
# FRANCHISE FIRST-ROUND HISTORY
# ============================================================

st.subheader("First-Round History")


franchise_firsts = (
    franchise_history[
        franchise_history[
            "round"
        ] == 1
    ]
    .copy()
    .sort_values(
        "year",
        ascending=False,
    )
)


franchise_firsts_display = (
    franchise_firsts[
        [
            "year",
            "pick_in_round",
            "player",
        ]
    ]
    .rename(
        columns={
            "year":
                "Season",
            "pick_in_round":
                "Draft Position",
            "player":
                "Player",
        }
    )
)


compact_dataframe(
    franchise_firsts_display,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# FRANCHISE DRAFT POSITION METRICS
# ============================================================

if not franchise_firsts.empty:

    avg_position = (
        franchise_firsts[
            "pick_in_round"
        ]
        .mean()
    )


    best_position = (
        franchise_firsts[
            "pick_in_round"
        ]
        .min()
    )


    worst_position = (
        franchise_firsts[
            "pick_in_round"
        ]
        .max()
    )


    c1, c2, c3 = st.columns(3)


    c1.metric(
        "Average 1st-Round Slot",
        f"{avg_position:.1f}",
    )


    c2.metric(
        "Earliest Pick",
        int(best_position),
    )


    c3.metric(
        "Latest Pick",
        int(worst_position),
    )


# ============================================================
# PLAYER DRAFT HISTORY
# ============================================================

st.divider()

st.header("Player Draft History")


player_search = st.selectbox(
    "Choose a player",
    players,
)


player_history = (
    drafts[
        drafts["player"]
        == player_search
    ]
    .copy()
    .sort_values(
        "year",
        ascending=False,
    )
)


player_display = (
    player_history[
        [
            "year",
            "round",
            "overall_pick",
            "team",
        ]
    ]
    .rename(
        columns={
            "year":
                "Season",
            "round":
                "Round",
            "overall_pick":
                "Overall Pick",
            "team":
                "Franchise",
        }
    )
)


compact_dataframe(
    player_display,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# MOST FREQUENTLY DRAFTED PLAYERS
# ============================================================

st.divider()

st.header("Repeat Offenders")


repeat_players = (
    drafts
    .groupby(
        "player"
    )
    .agg(
        Times_Drafted=(
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
        Average_Pick=(
            "overall_pick",
            "mean",
        ),
    )
    .reset_index()
)


repeat_players = (
    repeat_players[
        repeat_players[
            "Times_Drafted"
        ] > 1
    ]
    .copy()
)


repeat_players[
    "Average_Pick"
] = (
    repeat_players[
        "Average_Pick"
    ]
    .round(1)
)


repeat_players = (
    repeat_players
    .sort_values(
        [
            "Times_Drafted",
            "Seasons",
            "Average_Pick",
        ],
        ascending=[
            False,
            False,
            True,
        ],
    )
    .head(25)
)


repeat_display = (
    repeat_players
    .rename(
        columns={
            "player":
                "Player",
            "Times_Drafted":
                "Times Drafted",
            "Seasons":
                "Seasons",
            "Franchises":
                "Different Franchises",
            "Average_Pick":
                "Average Overall Pick",
        }
    )
)


compact_dataframe(
    repeat_display,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# DRAFT LOYALTY
# ============================================================

st.divider()

st.header("Draft Loyalty")


loyalty = (
    drafts
    .groupby(
        [
            "team",
            "player",
        ]
    )
    .agg(
        Times_Drafted=(
            "year",
            "size",
        ),
        First_Season=(
            "year",
            "min",
        ),
        Last_Season=(
            "year",
            "max",
        ),
        Average_Pick=(
            "overall_pick",
            "mean",
        ),
    )
    .reset_index()
)


loyalty = (
    loyalty[
        loyalty[
            "Times_Drafted"
        ] > 1
    ]
    .copy()
)


loyalty[
    "Average_Pick"
] = (
    loyalty[
        "Average_Pick"
    ]
    .round(1)
)


loyalty = (
    loyalty
    .sort_values(
        [
            "Times_Drafted",
            "Average_Pick",
        ],
        ascending=[
            False,
            True,
        ],
    )
    .head(25)
)


loyalty_display = (
    loyalty
    .rename(
        columns={
            "team":
                "Franchise",
            "player":
                "Player",
            "Times_Drafted":
                "Times Drafted",
            "First_Season":
                "First Drafted",
            "Last_Season":
                "Most Recent",
            "Average_Pick":
                "Average Overall Pick",
        }
    )
)


compact_dataframe(
    loyalty_display,
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# DRAFT POSITION HISTORY
# ============================================================

st.divider()

st.header("Draft Position History")


position_history = (
    drafts[
        drafts["round"] == 1
    ][
        [
            "year",
            "pick_in_round",
            "team",
        ]
    ]
    .copy()
)


# Add the official 2026 order to draft-position history without
# adding fake draft picks to all_drafts.csv.
position_history_2026 = (
    draft_order_2026
    .rename(
        columns={
            "Draft Position": "pick_in_round",
            "Franchise": "team",
        }
    )
    .assign(year=2026)
    [
        [
            "year",
            "pick_in_round",
            "team",
        ]
    ]
)


position_history_with_2026 = pd.concat(
    [
        position_history,
        position_history_2026,
    ],
    ignore_index=True,
)


position_pivot = (
    position_history_with_2026
    .pivot(
        index="team",
        columns="year",
        values="pick_in_round",
    )
)


# Add average draft position across all known draft orders,
# including the posted 2026 order. Pandas ignores seasons in
# which a franchise did not participate.
position_pivot["Average"] = (
    position_pivot
    .mean(
        axis=1
    )
    .round(1)
)


# Rename index for cleaner display
position_pivot.index.name = (
    "Franchise"
)


# Sort franchises alphabetically
position_pivot = (
    position_pivot
    .sort_index()
)


compact_dataframe(
    position_pivot,
    use_container_width=True,
    column_config={
        "Average":
            st.column_config.NumberColumn(
                "Average",
                format="%.1f",
            ),
    },
)


st.caption(
    "Average is each franchise's mean first-round draft "
    "position across the seasons in which that franchise "
    "participated, including the posted 2026 order. "
    "Lower numbers mean an earlier average draft position."
)

# ============================================================
# CHAMPION DRAFT POSITION
# ============================================================

st.divider()

st.header("🏆 Where Did Champions Draft?")

CHAMPIONSHIPS_FILE = (
    BASE_DIR
    / "data"
    / "playoffs"
    / "championships.csv"
)

championships = pd.read_csv(
    CHAMPIONSHIPS_FILE
)

championships["year"] = pd.to_numeric(
    championships["year"],
    errors="coerce",
)


# First-round draft positions by season
first_round_positions = (
    drafts[
        drafts["round"] == 1
    ][
        [
            "year",
            "team",
            "pick_in_round",
        ]
    ]
    .copy()
)


# Match each champion with where they drafted
champion_draft_positions = (
    championships[
        [
            "year",
            "champion",
        ]
    ]
    .merge(
        first_round_positions,
        left_on=[
            "year",
            "champion",
        ],
        right_on=[
            "year",
            "team",
        ],
        how="left",
    )
)


champion_draft_positions = (
    champion_draft_positions
    .drop(
        columns=[
            "team",
        ]
    )
    .rename(
        columns={
            "year":
                "Season",
            "champion":
                "Champion",
            "pick_in_round":
                "Draft Position",
        }
    )
    .sort_values(
        "Season",
        ascending=False,
    )
)


# ============================================================
# AVERAGE CHAMPION DRAFT POSITION
# ============================================================

avg_champion_position = (
    champion_draft_positions[
        "Draft Position"
    ]
    .mean()
)


c1, c2, c3 = st.columns(3)


c1.metric(
    "Average Champion Draft Position",
    f"{avg_champion_position:.1f}",
)


earliest_champion = (
    champion_draft_positions
    .sort_values(
        "Draft Position"
    )
    .iloc[0]
)


latest_champion = (
    champion_draft_positions
    .sort_values(
        "Draft Position",
        ascending=False,
    )
    .iloc[0]
)


c2.metric(
    "Earliest-Drafting Champion",
    f"Pick {int(earliest_champion['Draft Position'])}",
    (
        f"{earliest_champion['Champion']} "
        f"({int(earliest_champion['Season'])})"
    ),
)


c3.metric(
    "Latest-Drafting Champion",
    f"Pick {int(latest_champion['Draft Position'])}",
    (
        f"{latest_champion['Champion']} "
        f"({int(latest_champion['Season'])})"
    ),
)


compact_dataframe(
    champion_draft_positions,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Season":
            st.column_config.NumberColumn(
                format="%d",
            ),
        "Draft Position":
            st.column_config.NumberColumn(
                format="%d",
            ),
    },
)


st.caption(
    "Draft position refers to the franchise's first-round "
    "draft slot in the season it won the championship."
)

# ============================================================
# DOES DRAFT POSITION MATTER?
# ============================================================

st.divider()

st.header("📊 Does Draft Position Matter?")

PLAYOFF_APPEARANCES_FILE = (
    BASE_DIR
    / "data"
    / "playoffs"
    / "playoff_appearances.csv"
)

playoff_appearances = pd.read_csv(
    PLAYOFF_APPEARANCES_FILE
)

playoff_appearances["year"] = pd.to_numeric(
    playoff_appearances["year"],
    errors="coerce",
)


# ------------------------------------------------------------
# FIRST-ROUND DRAFT POSITION FOR EVERY TEAM-SEASON
# ------------------------------------------------------------

team_season_positions = (
    drafts[
        drafts["round"] == 1
    ][
        [
            "year",
            "team",
            "pick_in_round",
        ]
    ]
    .copy()
    .rename(
        columns={
            "pick_in_round": "draft_position",
        }
    )
)


# ------------------------------------------------------------
# ADD CHAMPION / RUNNER-UP STATUS
# ------------------------------------------------------------

champion_lookup = (
    championships[
        [
            "year",
            "champion",
            "runner_up",
        ]
    ]
    .copy()
)


team_season_positions = (
    team_season_positions
    .merge(
        champion_lookup,
        on="year",
        how="left",
    )
)


team_season_positions["is_champion"] = (
    team_season_positions["team"]
    == team_season_positions["champion"]
)


team_season_positions["is_runner_up"] = (
    team_season_positions["team"]
    == team_season_positions["runner_up"]
)


# ------------------------------------------------------------
# ADD PLAYOFF STATUS
# ------------------------------------------------------------

playoff_lookup = (
    playoff_appearances[
        [
            "year",
            "team",
            "finish",
        ]
    ]
    .copy()
)


team_season_positions = (
    team_season_positions
    .merge(
        playoff_lookup,
        on=[
            "year",
            "team",
        ],
        how="left",
    )
)


team_season_positions["made_playoffs"] = (
    team_season_positions["finish"]
    .notna()
)


# ============================================================
# GROUP AVERAGES
# ============================================================

champion_avg = (
    team_season_positions[
        team_season_positions[
            "is_champion"
        ]
    ]["draft_position"]
    .mean()
)


runner_up_avg = (
    team_season_positions[
        team_season_positions[
            "is_runner_up"
        ]
    ]["draft_position"]
    .mean()
)


playoff_avg = (
    team_season_positions[
        team_season_positions[
            "made_playoffs"
        ]
    ]["draft_position"]
    .mean()
)


missed_avg = (
    team_season_positions[
        ~team_season_positions[
            "made_playoffs"
        ]
    ]["draft_position"]
    .mean()
)


c1, c2, c3, c4 = st.columns(4)


c1.metric(
    "Champions",
    f"{champion_avg:.1f}",
    help="Average first-round draft position of league champions.",
)


c2.metric(
    "Runner-Ups",
    f"{runner_up_avg:.1f}",
    help="Average first-round draft position of championship-game losers.",
)


c3.metric(
    "Playoff Teams",
    f"{playoff_avg:.1f}",
    help="Average draft position of all teams appearing in the Championship Bracket.",
)


c4.metric(
    "Missed Playoffs",
    f"{missed_avg:.1f}",
    help="Average draft position of teams that did not make the Championship Bracket.",
)


st.caption(
    "Lower numbers mean the franchise drafted earlier."
)


# ============================================================
# RESULTS BY DRAFT SLOT
# ============================================================

st.subheader("Results by Draft Position")


slot_stats = (
    team_season_positions
    .groupby(
        "draft_position"
    )
    .agg(
        Seasons=(
            "year",
            "size",
        ),
        Championships=(
            "is_champion",
            "sum",
        ),
        Finals=(
            "is_runner_up",
            "sum",
        ),
        Playoff_Appearances=(
            "made_playoffs",
            "sum",
        ),
    )
    .reset_index()
)


slot_stats["Finals"] = (
    slot_stats["Finals"]
    + slot_stats["Championships"]
)


slot_stats["Playoff %"] = (
    slot_stats[
        "Playoff_Appearances"
    ]
    / slot_stats[
        "Seasons"
    ]
    * 100
).round(1)


slot_stats["Championship %"] = (
    slot_stats[
        "Championships"
    ]
    / slot_stats[
        "Seasons"
    ]
    * 100
).round(1)


slot_stats = (
    slot_stats
    .rename(
        columns={
            "draft_position":
                "Draft Position",
            "Playoff_Appearances":
                "Playoff Appearances",
        }
    )
)


compact_dataframe(
    slot_stats,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Draft Position":
            st.column_config.NumberColumn(
                format="%d",
            ),
        "Seasons":
            st.column_config.NumberColumn(
                format="%d",
            ),
        "Championships":
            st.column_config.NumberColumn(
                format="%d",
            ),
        "Finals":
            st.column_config.NumberColumn(
                format="%d",
            ),
        "Playoff Appearances":
            st.column_config.NumberColumn(
                format="%d",
            ),
        "Playoff %":
            st.column_config.NumberColumn(
                format="%.1f%%",
            ),
        "Championship %":
            st.column_config.NumberColumn(
                format="%.1f%%",
            ),
    },
)


# ============================================================
# SIMPLE VISUAL
# ============================================================

st.subheader("Championships by Draft Position")


championship_chart = (
    slot_stats[
        [
            "Draft Position",
            "Championships",
        ]
    ]
    .set_index(
        "Draft Position"
    )
)


st.bar_chart(
    championship_chart,
    y="Championships",
)


# ============================================================
# QUICK TAKEAWAY
# ============================================================

best_slot = (
    slot_stats
    .sort_values(
        [
            "Championships",
            "Playoff %",
        ],
        ascending=[
            False,
            False,
        ],
    )
    .iloc[0]
)


st.info(
    f"Through {len(years)} seasons, draft position "
    f"#{int(best_slot['Draft Position'])} has produced the most "
    f"championships ({int(best_slot['Championships'])}). "
    f"Its playoff rate is {best_slot['Playoff %']:.1f}%."
)

# ============================================================
# DRAFT STRATEGY BY FINISH
# ============================================================

st.divider()

st.header("🧠 Draft Strategy by Finish")

st.caption(
    "Compare when teams addressed each roster-building milestone. "
    "Lower picks mean that position was addressed earlier in the draft."
)

strategy_view_mode = st.radio(
    "Show draft strategy as",
    [
        "Overall Pick",
        "Round & Pick",
    ],
    horizontal=True,
    key="draft_strategy_view_mode",
)


def format_round_pick(value):
    if pd.isna(value):
        return "—"

    value = float(value)
    round_number = int((value - 1) // 12) + 1
    pick_in_round = value - (round_number - 1) * 12

    if abs(pick_in_round - round(pick_in_round)) < 0.05:
        pick_text = str(int(round(pick_in_round)))
    else:
        pick_text = f"{pick_in_round:.1f}"

    return f"R{round_number}, P{pick_text}"


def format_strategy_difference(value):
    if pd.isna(value):
        return "—"
    return f"{value:+.1f} picks"


try:
    strategy = pd.read_csv(STRATEGY_FILE)
    strategy["year"] = pd.to_numeric(
        strategy["year"],
        errors="coerce",
    )
    strategy["team"] = strategy["team"].apply(canonical_team)

    strategy_columns = [
        "first_qb_overall",
        "second_qb_overall",
        "first_rb_overall",
        "second_rb_overall",
        "third_rb_overall",
        "first_wr_overall",
        "second_wr_overall",
        "third_wr_overall",
        "first_te_overall",
        "first_k_overall",
        "first_def_overall",
    ]

    for col in strategy_columns:
        strategy[col] = pd.to_numeric(
            strategy[col],
            errors="coerce",
        )

    standings_history = pd.read_csv(ALL_STANDINGS_FILE)
    standings_history["year"] = pd.to_numeric(
        standings_history["year"],
        errors="coerce",
    )
    standings_history["rank"] = pd.to_numeric(
        standings_history["rank"],
        errors="coerce",
    )
    standings_history["team"] = standings_history["team"].apply(canonical_team)

    championships_strategy = pd.read_csv(CHAMPIONSHIPS_FILE)
    championships_strategy["year"] = pd.to_numeric(
        championships_strategy["year"],
        errors="coerce",
    )
    championships_strategy["champion"] = championships_strategy["champion"].apply(canonical_team)
    championships_strategy["runner_up"] = championships_strategy["runner_up"].apply(canonical_team)

    playoff_strategy = pd.read_csv(PLAYOFF_APPEARANCES_FILE)
    playoff_strategy["year"] = pd.to_numeric(
        playoff_strategy["year"],
        errors="coerce",
    )
    playoff_strategy["team"] = playoff_strategy["team"].apply(canonical_team)

    # Only compare seasons for which a completed draft strategy exists.
    strategy_years = set(
        strategy["year"]
        .dropna()
        .astype(int)
        .unique()
    )

    # ------------------------------------------------------------
    # ADD OUTCOME FLAGS TO EACH TEAM-SEASON
    # ------------------------------------------------------------

    outcome = strategy.copy()

    champion_lookup_strategy = championships_strategy[
        ["year", "champion", "runner_up"]
    ].copy()

    outcome = outcome.merge(
        champion_lookup_strategy,
        on="year",
        how="left",
    )

    outcome["is_champion"] = (
        outcome["team"] == outcome["champion"]
    )
    outcome["is_runner_up"] = (
        outcome["team"] == outcome["runner_up"]
    )

    playoff_keys = (
        playoff_strategy[
            playoff_strategy["year"].isin(strategy_years)
        ][["year", "team"]]
        .drop_duplicates()
        .assign(made_playoffs=True)
    )

    outcome = outcome.merge(
        playoff_keys,
        on=["year", "team"],
        how="left",
    )
    outcome["made_playoffs"] = (
        outcome["made_playoffs"]
        .fillna(False)
        .astype(bool)
    )

    # Cellar Boy = worst regular-season winning percentage.
    # If teams are tied, the franchise with fewer points scored
    # loses the tiebreaker and becomes the Cellar Boy.
    standings_completed = standings_history[
        standings_history["year"].isin(strategy_years)
    ].copy()

    def parse_standings_record(record):
        try:
            parts = [int(x) for x in str(record).strip().split("-")]
            if len(parts) == 2:
                wins, losses = parts
                ties = 0
            elif len(parts) == 3:
                wins, losses, ties = parts
            else:
                return pd.Series({
                    "wins": pd.NA,
                    "losses": pd.NA,
                    "ties": pd.NA,
                    "win_pct": pd.NA,
                })

            games = wins + losses + ties
            win_pct = (wins + 0.5 * ties) / games if games else pd.NA

            return pd.Series({
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "win_pct": win_pct,
            })

        except Exception:
            return pd.Series({
                "wins": pd.NA,
                "losses": pd.NA,
                "ties": pd.NA,
                "win_pct": pd.NA,
            })

    standings_completed["points_for"] = pd.to_numeric(
        standings_completed["points_for"],
        errors="coerce",
    )

    record_parts = standings_completed["record"].apply(
        parse_standings_record
    )

    standings_completed = pd.concat(
        [standings_completed, record_parts],
        axis=1,
    )

    cellar_rows = (
        standings_completed
        .dropna(subset=["win_pct", "points_for"])
        .sort_values(
            ["year", "win_pct", "points_for"],
            ascending=[True, True, True],
        )
        .groupby("year", as_index=False)
        .first()[
            [
                "year",
                "team",
                "record",
                "points_for",
                "win_pct",
            ]
        ]
        .rename(columns={
            "team": "cellar_boy",
            "record": "cellar_record",
            "points_for": "cellar_points_for",
            "win_pct": "cellar_win_pct",
        })
    )

    outcome = outcome.merge(
        cellar_rows,
        on="year",
        how="left",
    )
    outcome["is_cellar_boy"] = (
        outcome["team"] == outcome["cellar_boy"]
    )

    # ------------------------------------------------------------
    # GROUP AVERAGES
    # ------------------------------------------------------------

    main_metrics = {
        "first_qb_overall": "1st QB",
        "second_qb_overall": "2nd QB",
        "first_rb_overall": "1st RB",
        "second_rb_overall": "2nd RB",
        "third_rb_overall": "3rd RB",
        "first_wr_overall": "1st WR",
        "second_wr_overall": "2nd WR",
        "third_wr_overall": "3rd WR",
        "first_te_overall": "1st TE",
    }

    def strategy_group_row(label, frame):
        row = {
            "Finish": label,
            "Team-Seasons": len(frame),
        }
        for source, display in main_metrics.items():
            row[display] = frame[source].mean()
        return row

    strategy_finish_table = pd.DataFrame([
        strategy_group_row(
            "Champions",
            outcome[outcome["is_champion"]],
        ),
        strategy_group_row(
            "Runner-Ups",
            outcome[outcome["is_runner_up"]],
        ),
        strategy_group_row(
            "Playoff Teams",
            outcome[outcome["made_playoffs"]],
        ),
        strategy_group_row(
            "Non-Playoff Teams",
            outcome[~outcome["made_playoffs"]],
        ),
        strategy_group_row(
            "Cellar Boy",
            outcome[outcome["is_cellar_boy"]],
        ),
        strategy_group_row(
            "League Average",
            outcome,
        ),
    ])

    for col in main_metrics.values():
        strategy_finish_table[col] = strategy_finish_table[col].round(1)

    st.subheader("Average Position-Building Picks")

    strategy_finish_display = strategy_finish_table.copy()

    if strategy_view_mode == "Round & Pick":
        for col in main_metrics.values():
            strategy_finish_display[col] = (
                strategy_finish_display[col]
                .apply(format_round_pick)
            )

        finish_column_config = {
            "Team-Seasons": st.column_config.NumberColumn(
                "Team-Seasons",
                format="%d",
            )
        }
    else:
        finish_column_config = {
            "Team-Seasons": st.column_config.NumberColumn(
                "Team-Seasons",
                format="%d",
            ),
            **{
                display: st.column_config.NumberColumn(
                    display,
                    format="%.1f",
                )
                for display in main_metrics.values()
            },
        }

    compact_dataframe(
        strategy_finish_display,
        hide_index=True,
        use_container_width=True,
        column_config=finish_column_config,
    )

    if strategy_view_mode == "Round & Pick":
        st.caption(
            "Values are converted from average overall pick to a 12-team "
            "round-and-pick equivalent. For example, an average of pick 68.1 "
            "is shown as R6, P8.1. Second-QB averages use only team-seasons "
            "in which a second quarterback was actually drafted."
        )
    else:
        st.caption(
            "Each value is the average overall pick where teams in that group "
            "drafted that positional slot. Second-QB averages use only team-seasons "
            "in which a second quarterback was actually drafted."
        )

    # ------------------------------------------------------------
    # KICKER + DEFENSE STRATEGY
    # ------------------------------------------------------------

    st.subheader("Kicker & Defense Strategy")

    special_rows = []

    for label, frame in [
        ("Champions", outcome[outcome["is_champion"]]),
        ("Runner-Ups", outcome[outcome["is_runner_up"]]),
        ("Playoff Teams", outcome[outcome["made_playoffs"]]),
        ("Non-Playoff Teams", outcome[~outcome["made_playoffs"]]),
        ("Cellar Boy", outcome[outcome["is_cellar_boy"]]),
        ("League Average", outcome),
    ]:
        special_rows.append({
            "Finish": label,
            "1st K": frame["first_k_overall"].mean(),
            "1st DEF": frame["first_def_overall"].mean(),
        })

    special_table = pd.DataFrame(special_rows)
    special_table[["1st K", "1st DEF"]] = (
        special_table[["1st K", "1st DEF"]].round(1)
    )

    special_display = special_table.copy()

    if strategy_view_mode == "Round & Pick":
        for col in ["1st K", "1st DEF"]:
            special_display[col] = special_display[col].apply(format_round_pick)
        special_column_config = {}
    else:
        special_column_config = {
            "1st K": st.column_config.NumberColumn(format="%.1f"),
            "1st DEF": st.column_config.NumberColumn(format="%.1f"),
        }

    compact_dataframe(
        special_display,
        hide_index=True,
        use_container_width=True,
        column_config=special_column_config,
    )

    # ------------------------------------------------------------
    # CELLAR BOY HISTORY
    # ------------------------------------------------------------

    with st.expander("Cellar Boy by Season"):
        cellar_display = (
            cellar_rows
            .rename(columns={
                "year": "Season",
                "cellar_boy": "Cellar Boy",
                "cellar_record": "Record",
                "cellar_points_for": "Points For",
                "cellar_win_pct": "Win %",
            })
            .sort_values("Season", ascending=False)
        )

        compact_dataframe(
            cellar_display,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Season": st.column_config.NumberColumn(format="%d"),
                "Points For": st.column_config.NumberColumn(format="%.2f"),
                "Win %": st.column_config.NumberColumn(format="%.3f"),
            },
        )

    # ============================================================
    # FRANCHISE DRAFT TENDENCIES
    # ============================================================

    st.divider()

    st.header("🏗️ Franchise Draft Tendencies")

    st.caption(
        "How each franchise historically built its roster, measured by the "
        "average overall pick used on each positional milestone."
    )

    strategy_teams = sorted(
        strategy["team"]
        .dropna()
        .unique()
    )

    strategy_team = st.selectbox(
        "Choose a franchise",
        strategy_teams,
        key="strategy_franchise",
    )

    franchise_strategy = (
        strategy[strategy["team"] == strategy_team]
        .copy()
        .sort_values("year")
    )

    league_strategy = strategy.copy()

    comparison_rows = []

    comparison_metrics = {
        "first_qb_overall": "1st QB",
        "second_qb_overall": "2nd QB",
        "first_rb_overall": "1st RB",
        "second_rb_overall": "2nd RB",
        "third_rb_overall": "3rd RB",
        "first_wr_overall": "1st WR",
        "second_wr_overall": "2nd WR",
        "third_wr_overall": "3rd WR",
        "first_te_overall": "1st TE",
        "first_k_overall": "1st K",
        "first_def_overall": "1st DEF",
    }

    for source, display in comparison_metrics.items():
        team_avg = franchise_strategy[source].mean()
        league_avg = league_strategy[source].mean()

        comparison_rows.append({
            "Position Slot": display,
            "Franchise Avg Pick": team_avg,
            "League Avg Pick": league_avg,
            "Difference": team_avg - league_avg,
        })

    franchise_comparison = pd.DataFrame(comparison_rows)
    franchise_comparison[
        ["Franchise Avg Pick", "League Avg Pick", "Difference"]
    ] = franchise_comparison[
        ["Franchise Avg Pick", "League Avg Pick", "Difference"]
    ].round(1)

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Drafts Analyzed",
        franchise_strategy["year"].nunique(),
    )

    first_qb_avg = franchise_strategy["first_qb_overall"].mean()
    first_rb_avg = franchise_strategy["first_rb_overall"].mean()

    c2.metric(
        "Average 1st QB Pick",
        (
            format_round_pick(first_qb_avg)
            if strategy_view_mode == "Round & Pick"
            else (f"{first_qb_avg:.1f}" if pd.notna(first_qb_avg) else "—")
        ),
    )

    c3.metric(
        "Average 1st RB Pick",
        (
            format_round_pick(first_rb_avg)
            if strategy_view_mode == "Round & Pick"
            else (f"{first_rb_avg:.1f}" if pd.notna(first_rb_avg) else "—")
        ),
    )

    st.subheader("Franchise vs. League")

    franchise_comparison_display = franchise_comparison.copy()

    if strategy_view_mode == "Round & Pick":
        for col in ["Franchise Avg Pick", "League Avg Pick"]:
            franchise_comparison_display[col] = (
                franchise_comparison_display[col]
                .apply(format_round_pick)
            )
        franchise_comparison_display["Difference"] = (
            franchise_comparison_display["Difference"]
            .apply(format_strategy_difference)
        )
        comparison_column_config = {}
    else:
        comparison_column_config = {
            "Franchise Avg Pick": st.column_config.NumberColumn(format="%.1f"),
            "League Avg Pick": st.column_config.NumberColumn(format="%.1f"),
            "Difference": st.column_config.NumberColumn(
                format="%+.1f",
                help="Negative means this franchise drafts the position earlier than league average; positive means later.",
            ),
        }

    compact_dataframe(
        franchise_comparison_display,
        hide_index=True,
        use_container_width=True,
        column_config=comparison_column_config,
    )

    st.caption(
        "Negative differences mean the franchise addressed that position "
        "earlier than the league average. Positive differences mean it waited longer."
    )

    # ------------------------------------------------------------
    # YEAR-BY-YEAR FRANCHISE STRATEGY
    # ------------------------------------------------------------

    st.subheader("Year-by-Year Draft Strategy")

    year_columns = {
        "year": "Season",
        "first_qb_overall": "1st QB",
        "second_qb_overall": "2nd QB",
        "first_rb_overall": "1st RB",
        "second_rb_overall": "2nd RB",
        "third_rb_overall": "3rd RB",
        "first_wr_overall": "1st WR",
        "second_wr_overall": "2nd WR",
        "third_wr_overall": "3rd WR",
        "first_te_overall": "1st TE",
        "first_k_overall": "1st K",
        "first_def_overall": "1st DEF",
    }

    year_by_year = (
        franchise_strategy[list(year_columns.keys())]
        .rename(columns=year_columns)
        .sort_values("Season", ascending=False)
    )

    year_by_year_display = year_by_year.copy()

    if strategy_view_mode == "Round & Pick":
        for col in year_columns.values():
            if col != "Season":
                year_by_year_display[col] = (
                    year_by_year_display[col]
                    .apply(format_round_pick)
                )
        year_column_config = {
            "Season": st.column_config.NumberColumn(format="%d"),
        }
    else:
        year_column_config = {
            "Season": st.column_config.NumberColumn(format="%d"),
            **{
                col: st.column_config.NumberColumn(format="%.0f")
                for col in year_columns.values()
                if col != "Season"
            },
        }

    compact_dataframe(
        year_by_year_display,
        hide_index=True,
        use_container_width=True,
        column_config=year_column_config,
    )

    # ------------------------------------------------------------
    # FRANCHISE AVERAGES: ALL TEAMS
    # ------------------------------------------------------------

    st.subheader("All-Franchise Strategy Averages")

    franchise_average_table = (
        strategy
        .groupby("team")[list(comparison_metrics.keys())]
        .mean()
        .rename(columns=comparison_metrics)
        .round(1)
        .reset_index()
        .rename(columns={"team": "Franchise"})
        .sort_values("Franchise")
    )

    franchise_average_display = franchise_average_table.copy()

    if strategy_view_mode == "Round & Pick":
        for col in comparison_metrics.values():
            franchise_average_display[col] = (
                franchise_average_display[col]
                .apply(format_round_pick)
            )
        franchise_average_column_config = {}
    else:
        franchise_average_column_config = {
            display: st.column_config.NumberColumn(format="%.1f")
            for display in comparison_metrics.values()
        }

    compact_dataframe(
        franchise_average_display,
        hide_index=True,
        use_container_width=True,
        column_config=franchise_average_column_config,
    )

except FileNotFoundError as exc:
    st.warning(
        "Draft strategy analysis is not available yet. Run "
        "`python build_draft_position_strategy.py` and make sure "
        "`data/all_standings.csv` exists."
    )

# ============================================================
# FOOTNOTE
# ============================================================

st.divider()

st.caption(
    "Completed draft history covers 2018–2025. The official "
    "2026 draft order is posted separately and is included in "
    "Draft Position History, but not in historical performance "
    "statistics. Historical team-name changes are grouped by franchise."
)