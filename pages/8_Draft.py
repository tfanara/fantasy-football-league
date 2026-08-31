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


# ============================================================
# PAGE STYLE / LAYOUT TOGGLE
# ============================================================

draft_page_style = st.segmented_control(
    "Draft page style",
    options=[
        "Current",
        "Sports Dashboard",
        "Clean Minimal",
        "Mobile First",
    ],
    default="Current",
    key="draft_page_style",
)


if draft_page_style == "Sports Dashboard":

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.1rem;
            padding-bottom: 2rem;
            max-width: 1250px;
        }

        h1, h2, h3 {
            letter-spacing: -0.02em;
        }

        [data-testid="stMetric"] {
            border: 1px solid rgba(128,128,128,0.18);
            border-radius: 14px;
            padding: 0.75rem 0.85rem;
            background: rgba(128,128,128,0.035);
        }

        [data-testid="stDataFrame"] {
            border-radius: 14px;
            overflow: hidden;
        }

        .draft-hero {
            border: 1px solid rgba(128,128,128,0.18);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            margin: 0.65rem 0 0.8rem 0;
            background: linear-gradient(
                135deg,
                rgba(128,128,128,0.08),
                rgba(128,128,128,0.02)
            );
        }

        .draft-eyebrow {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            opacity: 0.65;
            margin-bottom: 0.2rem;
        }

        .draft-title {
            font-size: clamp(2rem, 5vw, 3.2rem);
            font-weight: 800;
            line-height: 1.0;
            letter-spacing: -0.045em;
            margin-bottom: 0.45rem;
        }

        .draft-subtitle {
            font-size: 0.95rem;
            opacity: 0.72;
            margin: 0;
        }

        @media (max-width: 700px) {
            .block-container {
                padding-left: 0.7rem;
                padding-right: 0.7rem;
            }

            [data-testid="stMetric"] {
                padding: 0.55rem 0.65rem;
            }
        }
        </style>

        <div class="draft-hero">
            <div class="draft-eyebrow">Malle's League · Draft Center</div>
            <div class="draft-title">📝 Draft History</div>
            <p class="draft-subtitle">
                Historical drafts, 2026 order, keeper costs, franchise history,
                and player draft history.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


elif draft_page_style == "Clean Minimal":

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
            max-width: 1080px;
        }

        h1 {
            font-size: clamp(2rem, 6vw, 3rem) !important;
            letter-spacing: -0.04em;
            margin-bottom: 0.2rem !important;
        }

        h2 {
            margin-top: 1.25rem !important;
            letter-spacing: -0.025em;
        }

        h3 {
            letter-spacing: -0.02em;
        }

        hr {
            margin-top: 1.1rem !important;
            margin-bottom: 1.1rem !important;
            opacity: 0.35;
        }

        [data-testid="stMetric"] {
            padding: 0.15rem 0;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.78rem;
            opacity: 0.65;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.55rem;
        }

        [data-testid="stDataFrame"] {
            border-top: 1px solid rgba(128,128,128,0.16);
            border-bottom: 1px solid rgba(128,128,128,0.16);
        }

        @media (max-width: 700px) {
            .block-container {
                padding-left: 0.65rem;
                padding-right: 0.65rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Draft History")
    st.caption(
        "2018–2025 completed drafts · official 2026 order · keeper submissions · "
        "franchise history · player history"
    )


elif draft_page_style == "Mobile First":

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 0.65rem;
            padding-bottom: 2rem;
            max-width: 980px;
        }

        h1 {
            font-size: 2rem !important;
            margin-bottom: 0.1rem !important;
        }

        h2 {
            font-size: 1.5rem !important;
            margin-top: 1rem !important;
        }

        h3 {
            font-size: 1.12rem !important;
        }

        [data-testid="stMetric"] {
            border-radius: 12px;
            border: 1px solid rgba(128,128,128,0.16);
            padding: 0.5rem 0.6rem;
        }

        [data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
        }

        .mobile-hero {
            padding: 0.25rem 0 0.65rem 0;
        }

        .mobile-kicker {
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            opacity: 0.6;
        }

        .mobile-title {
            font-size: 2rem;
            line-height: 1.05;
            font-weight: 800;
            letter-spacing: -0.04em;
            margin: 0.1rem 0 0.3rem 0;
        }

        .mobile-subtitle {
            font-size: 0.9rem;
            opacity: 0.72;
            margin: 0;
        }

        @media (max-width: 700px) {
            .block-container {
                padding-left: 0.45rem;
                padding-right: 0.45rem;
            }

            [data-testid="stHorizontalBlock"] {
                gap: 0.35rem;
            }

            [data-testid="stMetric"] {
                padding: 0.45rem 0.5rem;
            }

            [data-testid="stMetricLabel"] {
                font-size: 0.72rem;
            }

            [data-testid="stMetricValue"] {
                font-size: 1.25rem;
            }
        }
        </style>

        <div class="mobile-hero">
            <div class="mobile-kicker">Malle's League</div>
            <div class="mobile-title">2026 Draft Center</div>
            <p class="mobile-subtitle">
                Current order first. Historical draft data below.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


else:

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
# COMPACT / MOBILE-FRIENDLY TABLES
# ============================================================

if draft_page_style == "Mobile First":
    COMPACT_TABLE_ROW_HEIGHT = 24
    COMPACT_TABLE_HEADER_HEIGHT = 34
else:
    COMPACT_TABLE_ROW_HEIGHT = 26
    COMPACT_TABLE_HEADER_HEIGHT = 38

COMPACT_TABLE_MAX_VISIBLE_ROWS = 12


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
    "Buttermilk Puuump": {
        "player": "George Pickens",
        "round": 3,
        "status": "🟢 1st-Year Keeper",
        "acquisition": "Drafted — Round 4",
    },
    "Ginger FC": {
        "player": "Chris Olave",
        "round": 5,
        "status": "🟢 1st-Year Keeper",
        "acquisition": "Drafted — Round 6",
    },
    "Pop Lockett Drop it": {
        "player": "Javonte Williams",
        "round": 7,
        "status": "🟢 1st-Year Keeper",
        "acquisition": "Drafted — Round 8",
    },
    "Post Mahomes": {
        "player": "Cam Skattebo",
        "round": 9,
        "status": "🟢 1st-Year Keeper",
        "acquisition": "Drafted — Round 10",
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
# MOBILE-FIRST CURRENT-SEASON SPOTLIGHT
# ============================================================

if draft_page_style == "Mobile First":
    st.info(
        "The 2026 draft order and submitted keepers are shown immediately below "
        "the league summary. Tables use the tightest row spacing in this mode."
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

if draft_page_style == "Sports Dashboard":
    st.caption(
        "Draft Center · Season History · Franchise History · Player History · "
        "Draft Position History"
    )


# ============================================================
# 2026 DRAFT ORDER
# ============================================================

st.divider()

st.header("2026 Draft Order" if draft_page_style == "Clean Minimal" else "🏈 2026 Draft Order")

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
# FOOTNOTE
# ============================================================

st.divider()

st.caption(
    "Completed draft history covers 2018–2025. The official "
    "2026 draft order is included in Draft Position History without "
    "being treated as a completed draft. Historical team-name changes "
    "are grouped by franchise. Draft-performance and strategy analysis "
    "now lives on the Analysis page."
)