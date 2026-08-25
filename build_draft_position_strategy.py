from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DRAFT_FILE = (
    BASE_DIR
    / "data"
    / "drafts"
    / "all_drafts.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "drafts"
)

OUTPUT_CSV = (
    OUTPUT_DIR
    / "draft_position_strategy.csv"
)

OUTPUT_JSON = (
    OUTPUT_DIR
    / "draft_position_strategy.json"
)


# ============================================================
# POSITION SLOT SETTINGS
# ============================================================

POSITION_SLOTS = {
    "QB": 2,
    "RB": 3,
    "WR": 3,
    "TE": 1,
    "K": 1,
    "DEF": 1,
}


SLOT_NAMES = {
    1: "first",
    2: "second",
    3: "third",
}


# ============================================================
# LOAD DRAFT DATA
# ============================================================

print()
print("=" * 80)
print("BUILDING DRAFT POSITION STRATEGY")
print("=" * 80)

drafts = pd.read_csv(
    DRAFT_FILE
)

print()
print(
    f"Loaded {len(drafts)} draft selections."
)


# ============================================================
# VALIDATE REQUIRED COLUMNS
# ============================================================

required_columns = {
    "year",
    "team",
    "player",
    "position",
    "round",
    "pick_in_round",
    "overall_pick",
}


missing_columns = (
    required_columns
    - set(drafts.columns)
)


if missing_columns:

    raise RuntimeError(
        "Missing required columns from all_drafts.csv: "
        + ", ".join(
            sorted(missing_columns)
        )
    )


# ============================================================
# NORMALIZE DATA
# ============================================================

for column in [
    "year",
    "round",
    "pick_in_round",
    "overall_pick",
]:

    drafts[column] = pd.to_numeric(
        drafts[column],
        errors="coerce",
    )


drafts["position"] = (
    drafts["position"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.upper()
)


drafts["team"] = (
    drafts["team"]
    .fillna("")
    .astype(str)
    .str.strip()
)


drafts["player"] = (
    drafts["player"]
    .fillna("")
    .astype(str)
    .str.strip()
)


# ============================================================
# VALIDATE POSITIONS
# ============================================================

expected_positions = set(
    POSITION_SLOTS.keys()
)


unknown_positions = sorted(
    set(
        drafts[
            "position"
        ].unique()
    )
    - expected_positions
    - {""}
)


if unknown_positions:

    print()
    print(
        "WARNING: Unexpected positions found:"
    )

    for position in unknown_positions:

        print(
            f"  {position}"
        )


# ============================================================
# BUILD ONE RECORD PER TEAM / SEASON
# ============================================================

records = []


team_seasons = (
    drafts[
        [
            "year",
            "team",
        ]
    ]
    .drop_duplicates()
    .sort_values(
        [
            "year",
            "team",
        ]
    )
)


for _, team_season in team_seasons.iterrows():

    year = int(
        team_season[
            "year"
        ]
    )

    team = (
        team_season[
            "team"
        ]
    )


    team_draft = (
        drafts[
            (drafts["year"] == year)
            & (drafts["team"] == team)
        ]
        .copy()
        .sort_values(
            "overall_pick"
        )
    )


    record = {
        "year":
            year,

        "team":
            team,

        "total_draft_picks":
            len(team_draft),
    }


    # ========================================================
    # POSITION-BY-POSITION
    # ========================================================

    for position, slots_to_track in (
        POSITION_SLOTS.items()
    ):

        position_picks = (
            team_draft[
                team_draft[
                    "position"
                ] == position
            ]
            .copy()
            .sort_values(
                "overall_pick"
            )
            .reset_index(
                drop=True
            )
        )


        # ----------------------------------------------------
        # TOTAL COUNT DRAFTED AT POSITION
        # ----------------------------------------------------

        record[
            f"{position.lower()}_count"
        ] = len(
            position_picks
        )


        # ----------------------------------------------------
        # TRACK EACH REQUESTED SLOT
        # ----------------------------------------------------

        for slot_number in range(
            1,
            slots_to_track + 1,
        ):

            slot_name = (
                SLOT_NAMES[
                    slot_number
                ]
            )

            prefix = (
                f"{slot_name}_"
                f"{position.lower()}"
            )


            if (
                len(position_picks)
                < slot_number
            ):

                record[
                    f"{prefix}_player"
                ] = None

                record[
                    f"{prefix}_overall"
                ] = None

                record[
                    f"{prefix}_round"
                ] = None

                record[
                    f"{prefix}_pick_in_round"
                ] = None

                continue


            selection = (
                position_picks
                .iloc[
                    slot_number - 1
                ]
            )


            record[
                f"{prefix}_player"
            ] = (
                selection[
                    "player"
                ]
            )


            record[
                f"{prefix}_overall"
            ] = int(
                selection[
                    "overall_pick"
                ]
            )


            record[
                f"{prefix}_round"
            ] = int(
                selection[
                    "round"
                ]
            )


            record[
                f"{prefix}_pick_in_round"
            ] = int(
                selection[
                    "pick_in_round"
                ]
            )


    records.append(
        record
    )


# ============================================================
# CREATE DATAFRAME
# ============================================================

strategy = pd.DataFrame(
    records
)


strategy = (
    strategy
    .sort_values(
        [
            "year",
            "team",
        ]
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# TEAM-SEASON SUMMARY
# ============================================================

print()
print("=" * 80)
print("TEAM-SEASON SUMMARY")
print("=" * 80)

print()

print(
    f"Team-seasons: "
    f"{len(strategy)}"
)

print(
    f"Seasons: "
    f"{strategy['year'].nunique()}"
)

print(
    f"Franchises: "
    f"{strategy['team'].nunique()}"
)


print()
print(
    "Team-seasons by year:"
)

print()

print(
    strategy
    .groupby(
        "year"
    )
    .size()
    .to_string()
)


# ============================================================
# COVERAGE FOR EACH POSITION SLOT
# ============================================================

print()
print("=" * 80)
print("POSITION SLOT COVERAGE")
print("=" * 80)

print()


coverage_rows = []


for position, slots_to_track in (
    POSITION_SLOTS.items()
):

    for slot_number in range(
        1,
        slots_to_track + 1,
    ):

        slot_name = (
            SLOT_NAMES[
                slot_number
            ]
        )

        column = (
            f"{slot_name}_"
            f"{position.lower()}_overall"
        )


        found = (
            strategy[
                column
            ]
            .notna()
            .sum()
        )


        missing = (
            len(strategy)
            - found
        )


        coverage_rows.append(
            {
                "Slot":
                    (
                        f"{slot_name.title()} "
                        f"{position}"
                    ),

                "Team-Seasons Found":
                    found,

                "Missing":
                    missing,

                "Coverage":
                    (
                        found
                        / len(strategy)
                        * 100
                    ),
            }
        )


coverage = pd.DataFrame(
    coverage_rows
)


coverage[
    "Coverage"
] = (
    coverage[
        "Coverage"
    ]
    .map(
        lambda value:
            f"{value:.1f}%"
    )
)


print(
    coverage.to_string(
        index=False
    )
)


# ============================================================
# LEAGUE-WIDE AVERAGE PICK BY SLOT
# ============================================================

print()
print("=" * 80)
print("LEAGUE-WIDE AVERAGE POSITION PICKS")
print("=" * 80)

print()


average_rows = []


for position, slots_to_track in (
    POSITION_SLOTS.items()
):

    for slot_number in range(
        1,
        slots_to_track + 1,
    ):

        slot_name = (
            SLOT_NAMES[
                slot_number
            ]
        )

        overall_column = (
            f"{slot_name}_"
            f"{position.lower()}_overall"
        )

        round_column = (
            f"{slot_name}_"
            f"{position.lower()}_round"
        )


        average_overall = (
            strategy[
                overall_column
            ]
            .mean()
        )


        average_round = (
            strategy[
                round_column
            ]
            .mean()
        )


        average_rows.append(
            {
                "Slot":
                    (
                        f"{slot_name.title()} "
                        f"{position}"
                    ),

                "Average Overall Pick":
                    (
                        round(
                            average_overall,
                            1,
                        )
                        if pd.notna(
                            average_overall
                        )
                        else None
                    ),

                "Average Round":
                    (
                        round(
                            average_round,
                            1,
                        )
                        if pd.notna(
                            average_round
                        )
                        else None
                    ),
            }
        )


averages = pd.DataFrame(
    average_rows
)


print(
    averages.to_string(
        index=False
    )
)


# ============================================================
# FRANCHISE AVERAGES
# ============================================================

print()
print("=" * 80)
print("FRANCHISE AVERAGE POSITION PICKS")
print("=" * 80)

print()


franchise_columns = {}


for position, slots_to_track in (
    POSITION_SLOTS.items()
):

    for slot_number in range(
        1,
        slots_to_track + 1,
    ):

        slot_name = (
            SLOT_NAMES[
                slot_number
            ]
        )

        source_column = (
            f"{slot_name}_"
            f"{position.lower()}_overall"
        )

        display_name = (
            f"{slot_name.title()} "
            f"{position}"
        )

        franchise_columns[
            source_column
        ] = (
            display_name
        )


franchise_averages = (
    strategy
    .groupby(
        "team"
    )[
        list(
            franchise_columns.keys()
        )
    ]
    .mean()
    .rename(
        columns=franchise_columns
    )
    .round(1)
)


franchise_averages.index.name = (
    "Franchise"
)


print(
    franchise_averages
    .to_string()
)


# ============================================================
# LATEST-SEASON EXAMPLE
# ============================================================

latest_year = int(
    strategy[
        "year"
    ].max()
)


print()
print("=" * 80)
print(
    f"{latest_year} POSITION DRAFT STRATEGY"
)
print("=" * 80)

print()


latest = (
    strategy[
        strategy[
            "year"
        ] == latest_year
    ]
    .copy()
)


display_columns = [
    "team",
]

rename_columns = {
    "team":
        "Franchise",
}


for position, slots_to_track in (
    POSITION_SLOTS.items()
):

    for slot_number in range(
        1,
        slots_to_track + 1,
    ):

        slot_name = (
            SLOT_NAMES[
                slot_number
            ]
        )

        player_column = (
            f"{slot_name}_"
            f"{position.lower()}_player"
        )

        overall_column = (
            f"{slot_name}_"
            f"{position.lower()}_overall"
        )


        display_columns.extend(
            [
                player_column,
                overall_column,
            ]
        )


        rename_columns[
            player_column
        ] = (
            f"{slot_name.title()} "
            f"{position} Player"
        )


        rename_columns[
            overall_column
        ] = (
            f"{slot_name.title()} "
            f"{position} Pick"
        )


latest_display = (
    latest[
        display_columns
    ]
    .rename(
        columns=rename_columns
    )
)


print(
    latest_display.to_string(
        index=False
    )
)


# ============================================================
# SAVE FILES
# ============================================================

strategy.to_csv(
    OUTPUT_CSV,
    index=False,
)


strategy.to_json(
    OUTPUT_JSON,
    orient="records",
    indent=2,
)


print()
print("=" * 80)
print("FILES CREATED")
print("=" * 80)

print()
print(
    OUTPUT_CSV
)

print(
    OUTPUT_JSON
)

print()
print(
    f"Total team-season records: "
    f"{len(strategy)}"
)

print()
print(
    "Draft position strategy build complete."
)