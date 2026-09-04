from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd

from season_config import (
    LAST_COMPLETED_DRAFT_SEASON,
    print_season_config,
)


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

NFL_PLAYER_FILE = (
    BASE_DIR
    / "data"
    / "nfl"
    / "player_week_teams.csv"
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
# PLAYER NAME NORMALIZATION
# ============================================================

def norm_name(value):
    if pd.isna(value):
        return ""

    s = unicodedata.normalize("NFKD", str(value).strip())
    s = "".join(
        c for c in s
        if not unicodedata.combining(c)
    )
    s = s.lower()
    s = s.replace("’", "'")
    s = s.replace(".", "")
    s = s.replace("'", "")
    s = s.replace("-", " ")
    s = re.sub(r"\bdef\b$", "", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


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

print_season_config()

print()
print(
    f"Loaded {len(drafts)} draft selections."
)

drafts = drafts[
    pd.to_numeric(
        drafts["year"],
        errors="coerce",
    ) <= LAST_COMPLETED_DRAFT_SEASON
].copy()

print(
    f"Using {len(drafts)} selections through "
    f"{LAST_COMPLETED_DRAFT_SEASON} for draft-strategy analysis."
)


# ============================================================
# VALIDATE REQUIRED COLUMNS
# ============================================================

required_columns = {
    "year",
    "team",
    "player",
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


# Position is optional in the draft master. Prefer it when present,
# then enrich unresolved players from the NFL player-week position file.
if "position" not in drafts.columns:
    drafts["position"] = ""

drafts["position"] = (
    drafts["position"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.upper()
)

drafts["name_key"] = drafts["player"].map(norm_name)

if NFL_PLAYER_FILE.exists():
    nfl = pd.read_csv(NFL_PLAYER_FILE)

    required_nfl_columns = {
        "year",
        "player",
        "nfl_position",
    }
    missing_nfl = required_nfl_columns - set(nfl.columns)

    if missing_nfl:
        raise RuntimeError(
            "Missing required columns from player_week_teams.csv: "
            + ", ".join(sorted(missing_nfl))
        )

    nfl["year"] = pd.to_numeric(
        nfl["year"],
        errors="coerce",
    )
    nfl["name_key"] = nfl["player"].map(norm_name)
    nfl["nfl_position"] = (
        nfl["nfl_position"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    position_lookup = (
        nfl[
            nfl["nfl_position"].isin(
                set(POSITION_SLOTS.keys())
            )
        ]
        .groupby(
            ["year", "name_key"]
        )["nfl_position"]
        .agg(
            lambda s:
                s.mode().iloc[0]
                if not s.mode().empty
                else ""
        )
        .reset_index()
    )

    drafts = drafts.merge(
        position_lookup,
        on=["year", "name_key"],
        how="left",
    )

    unresolved_mask = ~drafts["position"].isin(
        set(POSITION_SLOTS.keys())
    )

    drafts.loc[
        unresolved_mask,
        "position",
    ] = (
        drafts.loc[
            unresolved_mask,
            "nfl_position",
        ]
        .fillna("")
    )

    drafts = drafts.drop(
        columns=["nfl_position"]
    )
else:
    print()
    print(
        "WARNING: NFL player-position file not found: "
        f"{NFL_PLAYER_FILE}"
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


unresolved = drafts[
    ~drafts["position"].isin(
        expected_positions
    )
].copy()

if not unresolved.empty:
    print()
    print("=" * 80)
    print("UNRESOLVED DRAFT POSITIONS")
    print("=" * 80)
    print(
        unresolved[
            [
                "year",
                "overall_pick",
                "team",
                "player",
                "position",
            ]
        ]
        .sort_values(
            ["year", "overall_pick"]
        )
        .to_string(index=False)
    )

    raise RuntimeError(
        f"{len(unresolved)} draft selections have unresolved "
        "positions. Strategy output was not written."
    )

print()
print(
    f"PASS — positions resolved for all {len(drafts):,} "
    "draft selections used in strategy analysis."
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