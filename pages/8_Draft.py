import streamlit as st
import pandas as pd
from pathlib import Path


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


draft_order_2026 = pd.DataFrame(
    {
        "Draft Position": range(1, len(DRAFT_ORDER_2026) + 1),
        "Franchise": DRAFT_ORDER_2026,
    }
)


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
    "The official 2026 first-round draft order. "
    "The 2026 draft itself has not taken place yet."
)

st.dataframe(
    draft_order_2026,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Draft Position":
            st.column_config.NumberColumn(
                "Draft Position",
                format="%d",
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


st.dataframe(
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


    st.dataframe(
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


    st.dataframe(
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


st.dataframe(
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


st.dataframe(
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


st.dataframe(
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


st.dataframe(
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


st.dataframe(
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


st.dataframe(
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


st.dataframe(
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


st.dataframe(
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
# FOOTNOTE
# ============================================================

st.divider()

st.caption(
    "Completed draft history covers 2018–2025. The official "
    "2026 draft order is posted separately and is included in "
    "Draft Position History, but not in historical performance "
    "statistics. Historical team-name changes are grouped by franchise."
)