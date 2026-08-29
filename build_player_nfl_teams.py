from pathlib import Path
import re
import unicodedata

import pandas as pd
import nflreadpy as nfl


# ============================================================
# PATHS
# ============================================================

LINEUP_DIR = Path(
    "data/matchups/player_week_stats"
)

OUTPUT_DIR = Path("data/nfl")

OUTPUT_FILE = (
    OUTPUT_DIR / "player_week_teams.csv"
)

UNMATCHED_FILE = (
    OUTPUT_DIR / "player_week_teams_unmatched.csv"
)


# ============================================================
# FIND CURRENT LINEUP MASTER
# ============================================================

def find_lineup_master():

    stable = (
        LINEUP_DIR
        / "all_weekly_lineups.csv"
    )

    if stable.exists():
        return stable

    candidates = sorted(
        LINEUP_DIR.glob(
            "all_weekly_lineups_*.csv"
        )
    )

    if not candidates:
        raise FileNotFoundError(
            "Could not find weekly lineup master."
        )

    # Prefer the file with the largest ending year.
    def ending_year(path):

        years = re.findall(
            r"\d{4}",
            path.stem,
        )

        if not years:
            return 0

        return max(
            int(x)
            for x in years
        )

    return max(
        candidates,
        key=ending_year,
    )


# ============================================================
# CANONICAL NAME EXCEPTIONS
# ============================================================

#
# Both Yahoo and nflverse names pass through this mapping.
# The value is our internal canonical matching key.
#

NAME_EQUIVALENTS = {

    # Known alternate names
    "hollywood brown":
        "marquise brown",

    "joshua palmer":
        "josh palmer",

    "kenny gainwell":
        "kenneth gainwell",

    "robbie chosen":
        "robby anderson",

    "nyheim miller hines":
        "nyheim hines",

    "m valdes scantling":
        "marquez valdes scantling",


    # Initials / punctuation differences
    "dj moore":
        "d j moore",

    "dj chark":
        "d j chark",


    # Historical name change:
    # BOTH names resolve to the same canonical key.
    "deonte harris":
        "deonte harty",

    "deonte harty":
        "deonte harty",


    # Nickname difference
    "scotty miller":
        "scott miller",
}


# ============================================================
# NORMALIZE PLAYER NAME
# ============================================================

def normalize_player_name(name):

    if pd.isna(name):
        return ""

    name = str(name)

    # Unicode normalization
    name = unicodedata.normalize(
        "NFKD",
        name,
    )

    name = "".join(
        char
        for char in name
        if not unicodedata.combining(char)
    )


    # --------------------------------------------------------
    # YAHOO UI ARTIFACTS
    # --------------------------------------------------------

    name = re.sub(
        r"video\s*forecast",
        " ",
        name,
        flags=re.IGNORECASE,
    )

    name = re.sub(
        r"\s*bye\s*$",
        " ",
        name,
        flags=re.IGNORECASE,
    )


    # --------------------------------------------------------
    # STANDARDIZATION
    # --------------------------------------------------------

    name = name.lower()

    name = re.sub(
        r"[^a-z0-9\s]",
        " ",
        name,
    )

    name = re.sub(
        r"\s+",
        " ",
        name,
    ).strip()


    # --------------------------------------------------------
    # GENERATIONAL SUFFIX
    # --------------------------------------------------------

    parts = name.split()

    suffixes = {
        "jr",
        "sr",
        "ii",
        "iii",
        "iv",
        "v",
    }

    if (
        parts
        and parts[-1] in suffixes
    ):
        parts = parts[:-1]

    name = " ".join(parts)


    # --------------------------------------------------------
    # CANONICAL NAME
    # --------------------------------------------------------

    return NAME_EQUIVALENTS.get(
        name,
        name,
    )


# ============================================================
# LOAD YAHOO LINEUPS
# ============================================================

lineup_file = find_lineup_master()

print("=" * 80)
print("BUILDING PLAYER NFL TEAM HISTORY")
print("=" * 80)

print()
print(
    "Lineup source:",
    lineup_file,
)

lineups = pd.read_csv(
    lineup_file
)

years = sorted(
    int(year)
    for year in lineups["year"]
    .dropna()
    .unique()
)

print(
    "Seasons:",
    years,
)


# ============================================================
# YAHOO PLAYER-WEEKS
# ============================================================

columns = [
    "year",
    "week",
    "player",
    "player_position",
]

yahoo = lineups[
    columns
].copy()


# Exclude empty roster slots.
yahoo = yahoo[
    yahoo["player"]
    .astype(str)
    .str.strip()
    .ne("(Empty)")
].copy()


# Exclude fantasy defenses.
yahoo = yahoo[
    ~yahoo["player"]
    .astype(str)
    .str.contains(
        " - DEF",
        regex=False,
    )
].copy()


# Prefer duplicate player-week rows
# containing Yahoo position data.

yahoo["_has_position"] = (
    yahoo["player_position"]
    .notna()
)

yahoo = (
    yahoo
    .sort_values(
        "_has_position",
        ascending=False,
    )
    .drop_duplicates(
        [
            "year",
            "week",
            "player",
        ]
    )
    .drop(
        columns="_has_position"
    )
    .reset_index(drop=True)
)


yahoo["match_player"] = (
    yahoo["player"]
    .apply(
        normalize_player_name
    )
)


# ============================================================
# LOAD NFLVERSE WEEKLY ROSTERS
# ============================================================

print()
print(
    "Loading nflverse weekly rosters..."
)

rosters = (
    nfl.load_rosters_weekly(
        years
    )
    .to_pandas()
)

print(
    f"NFL roster rows: "
    f"{len(rosters):,}"
)


# ============================================================
# PREP NFLVERSE
# ============================================================

nfl_players = rosters[
    [
        "season",
        "week",
        "full_name",
        "team",
        "position",
        "gsis_id",
        "yahoo_id",
    ]
].copy()


nfl_players = nfl_players.rename(
    columns={
        "season": "year",
        "full_name": "nfl_name",
        "team": "nfl_team",
        "position":
            "nfl_position",
    }
)


nfl_players["match_player"] = (
    nfl_players["nfl_name"]
    .apply(
        normalize_player_name
    )
)


# ============================================================
# SAFETY CHECK:
# SAME NORMALIZED PLAYER/WEEK -> MULTIPLE NFL PLAYERS
# ============================================================

collision_check = (
    nfl_players
    .groupby(
        [
            "year",
            "week",
            "match_player",
        ]
    )["gsis_id"]
    .nunique()
)

collisions = collision_check[
    collision_check > 1
]

if not collisions.empty:

    print()
    print(
        "WARNING: normalized-name "
        "collisions detected:"
    )

    print(
        collisions.head(20)
        .to_string()
    )


# One row per normalized player/week.

nfl_players = (
    nfl_players
    .sort_values(
        [
            "year",
            "week",
            "match_player",
        ]
    )
    .drop_duplicates(
        [
            "year",
            "week",
            "match_player",
        ]
    )
)


# ============================================================
# EXACT WEEK MATCH
# ============================================================

merged = yahoo.merge(
    nfl_players,
    on=[
        "year",
        "week",
        "match_player",
    ],
    how="left",
)


merged["match_method"] = pd.NA

merged.loc[
    merged["nfl_team"].notna(),
    "match_method",
] = "exact_week_normalized"


# ============================================================
# BUILD PLAYER-SEASON HISTORIES
# ============================================================

histories = {}

for (
    year,
    player,
), group in nfl_players.groupby(
    [
        "year",
        "match_player",
    ]
):

    histories[
        (
            int(year),
            player,
        )
    ] = (
        group
        .sort_values("week")
        .drop_duplicates("week")
    )


# ============================================================
# SAFE BYE / MISSING-WEEK INFERENCE
# ============================================================

for idx in merged[
    merged["nfl_team"].isna()
].index:

    year = int(
        merged.at[
            idx,
            "year",
        ]
    )

    week = int(
        merged.at[
            idx,
            "week",
        ]
    )

    player = merged.at[
        idx,
        "match_player",
    ]

    history = histories.get(
        (
            year,
            player,
        )
    )

    if (
        history is None
        or history.empty
    ):
        continue


    before = history[
        history["week"] < week
    ]

    after = history[
        history["week"] > week
    ]


    prev_row = (
        before.iloc[-1]
        if not before.empty
        else None
    )

    next_row = (
        after.iloc[0]
        if not after.empty
        else None
    )


    chosen = None
    method = None


    # Safest inference:
    # same NFL team on both sides.

    if (
        prev_row is not None
        and next_row is not None
        and prev_row["nfl_team"]
        == next_row["nfl_team"]
    ):

        chosen = prev_row

        method = (
            "inferred_between_same_team"
        )


    # Beginning of season.

    elif (
        prev_row is None
        and next_row is not None
    ):

        chosen = next_row
        method = "inferred_next"


    # End of season.

    elif (
        next_row is None
        and prev_row is not None
    ):

        chosen = prev_row
        method = "inferred_previous"


    if chosen is None:
        continue


    for column in [
        "nfl_name",
        "nfl_team",
        "nfl_position",
        "gsis_id",
        "yahoo_id",
    ]:

        merged.at[
            idx,
            column,
        ] = chosen[column]


    merged.at[
        idx,
        "match_method",
    ] = method


# ============================================================
# FINAL STATUS
# ============================================================

merged["matched"] = (
    merged["nfl_team"]
    .notna()
)

merged["match_method"] = (
    merged["match_method"]
    .fillna("unmatched")
)


# ============================================================
# OUTPUT COLUMNS
# ============================================================

output_columns = [
    "year",
    "week",
    "player",
    "player_position",
    "match_player",
    "nfl_name",
    "nfl_team",
    "nfl_position",
    "gsis_id",
    "yahoo_id",
    "match_method",
]

output = (
    merged[
        output_columns
    ]
    .sort_values(
        [
            "year",
            "week",
            "player",
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# WRITE FILES
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

output.to_csv(
    OUTPUT_FILE,
    index=False,
)


unmatched = output[
    output["nfl_team"].isna()
].copy()

unmatched.to_csv(
    UNMATCHED_FILE,
    index=False,
)


# ============================================================
# VALIDATION REPORT
# ============================================================

print()
print("=" * 80)
print("MATCH COVERAGE")
print("=" * 80)

summary = (
    merged
    .groupby("year")
    .agg(
        player_weeks=(
            "player",
            "size",
        ),
        matched=(
            "matched",
            "sum",
        ),
    )
)

summary["unmatched"] = (
    summary["player_weeks"]
    - summary["matched"]
)

summary["match_rate"] = (
    summary["matched"]
    / summary["player_weeks"]
)

print(
    summary.to_string()
)


total = len(merged)

matched_count = int(
    merged["matched"].sum()
)

print()
print(
    f"Overall: "
    f"{matched_count:,}/{total:,} "
    f"({matched_count / total:.2%})"
)


# ============================================================
# STARTING QB/WR VALIDATION
# ============================================================

starter_keys = (
    lineups[
        lineups["is_starter"].eq(True)
        & lineups["player_position"]
        .isin(["QB", "WR"])
    ][
        [
            "year",
            "week",
            "player",
        ]
    ]
    .drop_duplicates()
)


starter_check = (
    starter_keys.merge(
        output[
            [
                "year",
                "week",
                "player",
                "nfl_team",
            ]
        ],
        on=[
            "year",
            "week",
            "player",
        ],
        how="left",
    )
)


starter_missing = (
    starter_check[
        starter_check[
            "nfl_team"
        ].isna()
    ]
)


print()
print("=" * 80)
print("STARTING QB/WR COVERAGE")
print("=" * 80)

print(
    f"Starting QB/WR rows: "
    f"{len(starter_check):,}"
)

print(
    f"Matched: "
    f"{starter_check['nfl_team'].notna().sum():,}"
)

print(
    f"Unmatched: "
    f"{len(starter_missing):,}"
)


if starter_missing.empty:

    print()
    print(
        "PASS — 100% of starting "
        "QB/WR rows have NFL teams."
    )

else:

    print()
    print(
        "WARNING — unmatched starting "
        "QB/WR rows:"
    )

    print(
        starter_missing
        .to_string(index=False)
    )


# ============================================================
# MATCH METHODS
# ============================================================

print()
print("=" * 80)
print("MATCH METHODS")
print("=" * 80)

print(
    output["match_method"]
    .value_counts()
    .to_string()
)


# ============================================================
# OUTPUTS
# ============================================================

print()
print("=" * 80)
print("OUTPUTS")
print("=" * 80)

print(OUTPUT_FILE)
print(UNMATCHED_FILE)

print()
print("Done.")
