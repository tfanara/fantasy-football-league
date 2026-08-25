from pathlib import Path
import re
import unicodedata

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

BACKUP_FILE = (
    BASE_DIR
    / "data"
    / "drafts"
    / "all_drafts_before_positions.csv"
)

UNMATCHED_FILE = (
    BASE_DIR
    / "data"
    / "drafts"
    / "unmatched_player_positions.csv"
)


# ============================================================
# NFLVERSE PLAYER DATA
# ============================================================

NFLVERSE_URL = (
    "https://github.com/nflverse/"
    "nflverse-data/releases/download/"
    "players/players.csv"
)


# ============================================================
# TEAM DEFENSE NAMES
# ============================================================

DEFENSE_NAMES = {
    "49ers",
    "Bears",
    "Bengals",
    "Bills",
    "Broncos",
    "Browns",
    "Buccaneers",
    "Cardinals",
    "Chargers",
    "Chiefs",
    "Colts",
    "Commanders",
    "Cowboys",
    "Dolphins",
    "Eagles",
    "Falcons",
    "Giants",
    "Jaguars",
    "Jets",
    "Lions",
    "Packers",
    "Panthers",
    "Patriots",
    "Raiders",
    "Rams",
    "Ravens",
    "Saints",
    "Seahawks",
    "Steelers",
    "Texans",
    "Titans",
    "Vikings",

    # Historical names
    "Redskins",
    "Football Team",
}


# ============================================================
# MANUAL NAME ALIASES
# ============================================================

MANUAL_ALIASES = {
    # Add future Yahoo/nflverse naming differences here.
    #
    # Example:
    # "gabe davis": "gabriel davis",
}


# ============================================================
# MANUAL POSITION OVERRIDES
# ============================================================

MANUAL_POSITION_OVERRIDES = {
    "Alex Smith": "QB",
    "Anthony Miller": "WR",
    "Ben Watson": "TE",
    "Chris Thompson": "RB",
    "David Johnson": "RB",
    "Hollywood Brown": "WR",
    "James Robinson": "RB",
    "Joshua Palmer": "WR",
    "Mark Ingram II": "RB",
    "Michael Badgley": "K",
    "Michael Pittman Jr.": "WR",
    "Mike Williams": "WR",
    "Nyheim Miller-Hines": "RB",
    "Travis Hunter": "WR",
}


# ============================================================
# POSITION NORMALIZATION
# ============================================================

def normalize_position(position):

    if pd.isna(position):
        return None

    position = str(position).strip().upper()

    mapping = {
        "QB": "QB",

        "RB": "RB",
        "HB": "RB",
        "FB": "RB",

        "WR": "WR",

        "TE": "TE",

        "K": "K",
        "PK": "K",
    }

    return mapping.get(
        position,
        position,
    )


# ============================================================
# NAME NORMALIZATION
# ============================================================

def normalize_name(name):

    if pd.isna(name):
        return ""

    name = str(name).strip()

    # Remove accents
    name = unicodedata.normalize(
        "NFKD",
        name,
    )

    name = "".join(
        character
        for character in name
        if not unicodedata.combining(character)
    )

    name = name.lower()

    name = name.replace(
        "’",
        "'",
    )

    # Remove punctuation
    name = re.sub(
        r"[^a-z0-9 ]",
        "",
        name,
    )

    name = re.sub(
        r"\s+",
        " ",
        name,
    ).strip()

    return name


# ============================================================
# NAME WITHOUT SUFFIX
# ============================================================

def normalize_name_without_suffix(name):

    normalized = normalize_name(
        name
    )

    normalized = re.sub(
        r"\s+(jr|sr|ii|iii|iv|v)$",
        "",
        normalized,
    )

    return normalized.strip()


# ============================================================
# LOAD DRAFT DATA
# ============================================================

print()
print("=" * 80)
print("DRAFT POSITION ENRICHMENT")
print("=" * 80)

drafts = pd.read_csv(
    DRAFT_FILE
)

print()
print(
    f"Loaded {len(drafts)} draft selections."
)


# ============================================================
# BACKUP ORIGINAL FILE
# ============================================================

if not BACKUP_FILE.exists():

    drafts.to_csv(
        BACKUP_FILE,
        index=False,
    )

    print()
    print(
        "Backup created:"
    )

    print(
        BACKUP_FILE
    )

else:

    print()
    print(
        "Backup already exists:"
    )

    print(
        BACKUP_FILE
    )


# ============================================================
# LOAD NFLVERSE PLAYER REFERENCE
# ============================================================

print()
print("=" * 80)
print("LOADING NFLVERSE PLAYER REFERENCE")
print("=" * 80)

players = pd.read_csv(
    NFLVERSE_URL
)

print()
print(
    f"Loaded {len(players)} nflverse player records."
)


# ============================================================
# DETECT REQUIRED COLUMNS
# ============================================================

name_candidates = [
    "display_name",
    "player_display_name",
    "full_name",
]

position_candidates = [
    "position",
]


player_name_column = None

for column in name_candidates:

    if column in players.columns:

        player_name_column = column
        break


if player_name_column is None:

    raise RuntimeError(
        "Could not find a player-name column "
        "in the nflverse player dataset."
    )


position_column = None

for column in position_candidates:

    if column in players.columns:

        position_column = column
        break


if position_column is None:

    raise RuntimeError(
        "Could not find a position column "
        "in the nflverse player dataset."
    )


print()
print(
    f"Using player name column: "
    f"{player_name_column}"
)

print(
    f"Using position column: "
    f"{position_column}"
)


# ============================================================
# PREPARE PLAYER REFERENCE
# ============================================================

reference = players[
    [
        player_name_column,
        position_column,
    ]
].copy()


reference = reference.rename(
    columns={
        player_name_column:
            "reference_name",

        position_column:
            "reference_position",
    }
)


reference[
    "normalized_name"
] = (
    reference[
        "reference_name"
    ]
    .apply(
        normalize_name
    )
)


reference[
    "normalized_name_no_suffix"
] = (
    reference[
        "reference_name"
    ]
    .apply(
        normalize_name_without_suffix
    )
)


reference[
    "reference_position"
] = (
    reference[
        "reference_position"
    ]
    .apply(
        normalize_position
    )
)


reference = reference[
    reference[
        "normalized_name"
    ] != ""
].copy()


# ============================================================
# BUILD EXACT LOOKUP
# ============================================================

exact_lookup = {}


for _, row in reference.iterrows():

    normalized = row[
        "normalized_name"
    ]

    position = row[
        "reference_position"
    ]


    if pd.isna(position):
        continue


    if normalized not in exact_lookup:

        exact_lookup[
            normalized
        ] = set()


    exact_lookup[
        normalized
    ].add(
        position
    )


# ============================================================
# BUILD NO-SUFFIX LOOKUP
# ============================================================

suffix_lookup = {}


for _, row in reference.iterrows():

    normalized = row[
        "normalized_name_no_suffix"
    ]

    position = row[
        "reference_position"
    ]


    if pd.isna(position):
        continue


    if normalized not in suffix_lookup:

        suffix_lookup[
            normalized
        ] = set()


    suffix_lookup[
        normalized
    ].add(
        position
    )


# ============================================================
# RESOLVE ONE PLAYER
# ============================================================

def resolve_position(player):

    player = str(
        player
    ).strip()


    # --------------------------------------------------------
    # MANUAL POSITION OVERRIDE
    # --------------------------------------------------------

    if player in MANUAL_POSITION_OVERRIDES:

        return {
            "position":
                MANUAL_POSITION_OVERRIDES[
                    player
                ],

            "match_source":
                "Manual Override",
        }


    # --------------------------------------------------------
    # TEAM DEFENSE
    # --------------------------------------------------------

    if player in DEFENSE_NAMES:

        return {
            "position":
                "DEF",

            "match_source":
                "Defense",
        }


    normalized = normalize_name(
        player
    )


    # --------------------------------------------------------
    # MANUAL NAME ALIAS
    # --------------------------------------------------------

    if normalized in MANUAL_ALIASES:

        normalized = normalize_name(
            MANUAL_ALIASES[
                normalized
            ]
        )


    # --------------------------------------------------------
    # EXACT MATCH
    # --------------------------------------------------------

    positions = exact_lookup.get(
        normalized
    )


    if positions:

        fantasy_positions = {
            position
            for position in positions
            if position in {
                "QB",
                "RB",
                "WR",
                "TE",
                "K",
            }
        }


        if len(
            fantasy_positions
        ) == 1:

            return {
                "position":
                    next(
                        iter(
                            fantasy_positions
                        )
                    ),

                "match_source":
                    "NFLverse Exact",
            }


    # --------------------------------------------------------
    # SUFFIX-INSENSITIVE MATCH
    # --------------------------------------------------------

    no_suffix = (
        normalize_name_without_suffix(
            player
        )
    )


    positions = suffix_lookup.get(
        no_suffix
    )


    if positions:

        fantasy_positions = {
            position
            for position in positions
            if position in {
                "QB",
                "RB",
                "WR",
                "TE",
                "K",
            }
        }


        if len(
            fantasy_positions
        ) == 1:

            return {
                "position":
                    next(
                        iter(
                            fantasy_positions
                        )
                    ),

                "match_source":
                    "NFLverse No Suffix",
            }


    # --------------------------------------------------------
    # UNMATCHED
    # --------------------------------------------------------

    return {
        "position":
            None,

        "match_source":
            "Unmatched",
    }


# ============================================================
# ENRICH DRAFT DATA
# ============================================================

results = (
    drafts[
        "player"
    ]
    .apply(
        resolve_position
    )
)


drafts[
    "position"
] = (
    results
    .apply(
        lambda result:
            result[
                "position"
            ]
    )
)


drafts[
    "position_match_source"
] = (
    results
    .apply(
        lambda result:
            result[
                "match_source"
            ]
    )
)


# ============================================================
# POSITION SUMMARY
# ============================================================

print()
print("=" * 80)
print("POSITION SUMMARY")
print("=" * 80)

print()

print(
    drafts[
        "position"
    ]
    .value_counts(
        dropna=False
    )
    .to_string()
)


# ============================================================
# MATCH SOURCE SUMMARY
# ============================================================

print()
print("=" * 80)
print("MATCH SOURCES")
print("=" * 80)

print()

print(
    drafts[
        "position_match_source"
    ]
    .value_counts()
    .to_string()
)


# ============================================================
# UNMATCHED PLAYERS
# ============================================================

unmatched = (
    drafts[
        drafts[
            "position"
        ].isna()
    ][
        [
            "player",
        ]
    ]
    .drop_duplicates()
    .sort_values(
        "player"
    )
)


print()
print("=" * 80)
print("UNMATCHED PLAYERS")
print("=" * 80)

print()


if unmatched.empty:

    print(
        "All drafted players were assigned positions."
    )

    # Remove stale unmatched file if one exists.
    if UNMATCHED_FILE.exists():

        UNMATCHED_FILE.unlink()

else:

    print(
        unmatched.to_string(
            index=False
        )
    )


    unmatched.to_csv(
        UNMATCHED_FILE,
        index=False,
    )


    print()
    print(
        "Unmatched file:"
    )

    print(
        UNMATCHED_FILE
    )


# ============================================================
# COVERAGE
# ============================================================

total = len(
    drafts
)

matched = (
    drafts[
        "position"
    ]
    .notna()
    .sum()
)

coverage = (
    matched
    / total
    * 100
)


print()
print("=" * 80)
print("COVERAGE")
print("=" * 80)

print()

print(
    f"Matched selections: "
    f"{matched} / {total}"
)

print(
    f"Coverage: "
    f"{coverage:.2f}%"
)


# ============================================================
# SAVE ENRICHED DATA
# ============================================================

drafts.to_csv(
    DRAFT_FILE,
    index=False,
)


print()
print("=" * 80)
print("FILE UPDATED")
print("=" * 80)

print()

print(
    DRAFT_FILE
)

print()
print(
    "Position enrichment complete."
)