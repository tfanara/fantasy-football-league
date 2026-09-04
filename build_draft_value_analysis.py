from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd

from team_aliases import canonical_team
from season_config import (
    LAST_COMPLETED_SEASON,
    print_season_config,
)


# ============================================================
# PATHS
# ============================================================

DRAFT_PATH = Path(
    "data/drafts/all_drafts.csv"
)

# Draft Value is outcome-based, so its cutoff comes from season_config.py.
DRAFT_VALUE_THROUGH_YEAR = LAST_COMPLETED_SEASON

LINEUP_DIR = Path(
    "data/matchups/player_week_stats"
)

OUTPUT_DIR = Path(
    "data/analysis"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def find_lineup_master():

    stable = (
        LINEUP_DIR
        / "all_weekly_lineups.csv"
    )

    if stable.exists():
        return stable

    candidates = list(
        LINEUP_DIR.glob(
            "all_weekly_lineups*.csv"
        )
    )

    if not candidates:
        raise FileNotFoundError(
            "No weekly lineup master found."
        )

    return max(
        candidates,
        key=lambda p: p.stat().st_mtime,
    )


LINEUP_PATH = find_lineup_master()


# ============================================================
# NAME NORMALIZATION
# ============================================================

def norm_name(value):

    if pd.isna(value):
        return ""

    s = str(value).strip()

    s = unicodedata.normalize(
        "NFKD",
        s,
    )

    s = "".join(
        c for c in s
        if not unicodedata.combining(c)
    )

    s = s.lower()

    s = s.replace("’", "'")
    s = s.replace(".", "")
    s = s.replace("'", "")
    s = s.replace("-", " ")

    s = re.sub(
        r"\bdef\b$",
        "",
        s,
    )

    s = re.sub(
        r"\b(jr|sr|ii|iii|iv|v)\b",
        "",
        s,
    )

    s = re.sub(
        r"[^a-z0-9]+",
        " ",
        s,
    )

    return re.sub(
        r"\s+",
        " ",
        s,
    ).strip()


# ============================================================
# POSITION INFERENCE
# ============================================================

VALID_POSITIONS = {
    "QB",
    "RB",
    "WR",
    "TE",
    "K",
    "DEF",
}

SKILL_POSITIONS = {
    "QB",
    "RB",
    "WR",
    "TE",
}


def infer_position_from_rows(rows):

    if rows.empty:
        return np.nan

    # Explicit player position first.
    if "player_position" in rows.columns:

        vals = (
            rows["player_position"]
            .dropna()
            .astype(str)
            .str.upper()
            .str.strip()
        )

        vals = vals[
            vals.isin(
                VALID_POSITIONS
            )
        ]

        if not vals.empty:
            return vals.mode().iloc[0]

    # Fixed lineup slots next.
    slots = (
        rows["lineup_slot"]
        .dropna()
        .astype(str)
        .str.upper()
        .str.strip()
    )

    fixed = slots[
        slots.isin(
            VALID_POSITIONS
        )
    ]

    if not fixed.empty:
        return fixed.mode().iloc[0]

    return np.nan


# ============================================================
# LOAD
# ============================================================

print("=" * 80)
print("BUILDING DRAFT VALUE ANALYSIS")
print("=" * 80)

print("Draft master:", DRAFT_PATH)
print("Lineup master:", LINEUP_PATH)
print_season_config()

draft = pd.read_csv(
    DRAFT_PATH
)

lineups = pd.read_csv(
    LINEUP_PATH
)

print(
    f"\nLoaded {len(draft):,} draft picks."
)

print(
    f"Loaded {len(lineups):,} player-week rows."
)


# ============================================================
# BASIC CLEANING
# ============================================================

draft["name_key"] = (
    draft["player"]
    .map(norm_name)
)

lineups["name_key"] = (
    lineups["player"]
    .map(norm_name)
)

draft["canonical_team"] = (
    draft["team"]
    .map(canonical_team)
)

lineups["canonical_team"] = (
    lineups["fantasy_team"]
    .map(canonical_team)
)

draft["keeper"] = (
    draft["keeper"]
    .fillna(False)
    .astype(bool)
)

lineups["fantasy_points"] = (
    pd.to_numeric(
        lineups["fantasy_points"],
        errors="coerce",
    )
    .fillna(0.0)
)

lineups["is_starter"] = (
    lineups["is_starter"]
    .fillna(False)
    .astype(bool)
)


# ============================================================
# PLAYER-SEASON PRODUCTION
# ============================================================

season_prod = (
    lineups
    .groupby(
        [
            "year",
            "name_key",
        ],
        as_index=False,
    )
    .agg(
        season_points=(
            "fantasy_points",
            "sum",
        ),
        roster_weeks=(
            "week",
            "nunique",
        ),
    )
)


# ============================================================
# PRODUCTION CAPTURED BY EACH FRANCHISE
# ============================================================

team_prod = (
    lineups
    .groupby(
        [
            "year",
            "name_key",
            "canonical_team",
        ],
        as_index=False,
    )
    .agg(
        captured_points=(
            "fantasy_points",
            "sum",
        ),
        captured_weeks=(
            "week",
            "nunique",
        ),
    )
)


starter_rows = lineups[
    lineups["is_starter"]
].copy()

starter_prod = (
    starter_rows
    .groupby(
        [
            "year",
            "name_key",
            "canonical_team",
        ],
        as_index=False,
    )
    .agg(
        started_points=(
            "fantasy_points",
            "sum",
        ),
        starts=(
            "week",
            "nunique",
        ),
    )
)


# ============================================================
# POSITION LOOKUP
# ============================================================

position_records = []

for (
    year,
    name_key
), rows in lineups.groupby(
    [
        "year",
        "name_key",
    ]
):

    position_records.append(
        {
            "year": year,
            "name_key": name_key,
            "position":
                infer_position_from_rows(
                    rows
                ),
        }
    )

position_lookup = pd.DataFrame(
    position_records
)


# ============================================================
# JOIN DRAFT TO PRODUCTION
# ============================================================

picks = draft.merge(
    season_prod,
    on=[
        "year",
        "name_key",
    ],
    how="left",
)

picks = picks.merge(
    position_lookup,
    on=[
        "year",
        "name_key",
    ],
    how="left",
)

picks = picks.merge(
    team_prod,
    on=[
        "year",
        "name_key",
        "canonical_team",
    ],
    how="left",
)

picks = picks.merge(
    starter_prod,
    on=[
        "year",
        "name_key",
        "canonical_team",
    ],
    how="left",
)


for col in [
    "season_points",
    "roster_weeks",
    "captured_points",
    "captured_weeks",
    "started_points",
    "starts",
]:

    picks[col] = (
        pd.to_numeric(
            picks[col],
            errors="coerce",
        )
        .fillna(0)
    )


# ============================================================
# DEFENSE POSITION
# ============================================================

# Draft records store team defenses as team names.
# Any unresolved pick whose normalized name matches a defense
# appearing in the lineup history should be DEF.

defense_keys = set(
    lineups.loc[
        (
            lineups["player_position"]
            .astype(str)
            .str.upper()
            .eq("DEF")
        )
        |
        (
            lineups["lineup_slot"]
            .astype(str)
            .str.upper()
            .eq("DEF")
        ),
        "name_key",
    ]
)

def_mask = (
    picks["position"].isna()
    & picks["name_key"].isin(
        defense_keys
    )
)

picks.loc[
    def_mask,
    "position",
] = "DEF"


# ============================================================
# RETENTION / UTILIZATION
# ============================================================

picks["retention_rate"] = np.where(
    picks["season_points"] > 0,
    (
        picks["captured_points"]
        / picks["season_points"]
    ),
    np.nan,
)

picks["starter_capture_rate"] = np.where(
    picks["captured_points"] > 0,
    (
        picks["started_points"]
        / picks["captured_points"]
    ),
    np.nan,
)


# ============================================================
# PRIMARY ELIGIBILITY
# ============================================================

picks["draft_value_eligible"] = (
    (picks["year"] <= DRAFT_VALUE_THROUGH_YEAR)
    & (~picks["keeper"])
    & picks["position"].isin(
        SKILL_POSITIONS
    )
)

eligible = picks[
    picks["draft_value_eligible"]
].copy()


# ============================================================
# POSITIONAL OUTCOME PERCENTILE
#
# Raw fantasy points cannot be compared fairly across
# positions. Instead, grade every player-season relative to
# other fantasy players at the same position that season.
#
# 100 = best positional outcome
#  50 = median positional outcome
#   0 = worst positional outcome
# ============================================================

NFL_TEAM_PATH = Path(
    "data/nfl/player_week_teams.csv"
)

nfl_position_lookup = None

if NFL_TEAM_PATH.exists():

    nfl = pd.read_csv(
        NFL_TEAM_PATH
    )

    nfl["name_key"] = (
        nfl["player"]
        .map(norm_name)
    )

    nfl["nfl_position"] = (
        nfl["nfl_position"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    nfl_position_lookup = (
        nfl[
            nfl["nfl_position"].isin(
                SKILL_POSITIONS
            )
        ]
        .groupby(
            [
                "year",
                "name_key",
            ]
        )["nfl_position"]
        .agg(
            lambda s:
                s.mode().iloc[0]
                if not s.mode().empty
                else np.nan
        )
        .reset_index(
            name="nfl_position"
        )
    )

    picks = picks.merge(
        nfl_position_lookup,
        on=[
            "year",
            "name_key",
        ],
        how="left",
    )

    picks["position"] = (
        picks["position"]
        .where(
            picks["position"].isin(
                VALID_POSITIONS
            ),
            picks["nfl_position"],
        )
    )

    picks = picks.drop(
        columns=[
            "nfl_position",
        ]
    )


# Recalculate eligibility after NFL position enrichment.

picks["draft_value_eligible"] = (
    (picks["year"] <= DRAFT_VALUE_THROUGH_YEAR)
    & (~picks["keeper"])
    & picks["position"].isin(
        SKILL_POSITIONS
    )
)


# ============================================================
# PLAYER-SEASON POSITION POOL
# ============================================================

player_pool = (
    lineups
    .groupby(
        [
            "year",
            "name_key",
        ],
        as_index=False,
    )
    .agg(
        season_points=(
            "fantasy_points",
            "sum",
        )
    )
)

player_pool = player_pool.merge(
    position_lookup,
    on=[
        "year",
        "name_key",
    ],
    how="left",
)


if nfl_position_lookup is not None:

    player_pool = player_pool.merge(
        nfl_position_lookup,
        on=[
            "year",
            "name_key",
        ],
        how="left",
    )

    player_pool["position"] = (
        player_pool["position"]
        .where(
            player_pool["position"].isin(
                SKILL_POSITIONS
            ),
            player_pool["nfl_position"],
        )
    )

    player_pool = player_pool.drop(
        columns=[
            "nfl_position",
        ]
    )


player_pool = player_pool[
    player_pool["position"].isin(
        SKILL_POSITIONS
    )
].copy()


# ============================================================
# POSITIONAL PERCENTILE
#
# pct=True produces 0-1 ranks. Convert to 0-100.
# Higher fantasy production = higher percentile.
# ============================================================

player_pool[
    "position_percentile"
] = (
    player_pool
    .groupby(
        [
            "year",
            "position",
        ]
    )["season_points"]
    .rank(
        method="average",
        pct=True,
    )
    * 100
)


# ============================================================
# JOIN OUTCOME PERCENTILE TO PICKS
# ============================================================

pick_outcomes = (
    player_pool[
        [
            "year",
            "name_key",
            "position",
            "position_percentile",
        ]
    ]
    .drop_duplicates(
        [
            "year",
            "name_key",
        ]
    )
)

picks = picks.merge(
    pick_outcomes,
    on=[
        "year",
        "name_key",
        "position",
    ],
    how="left",
)


# A drafted player who never appears in the weekly roster
# history is a legitimate zero-production outcome.
#
# Assign the bottom of the positional scale.

zero_outcome = (
    picks["draft_value_eligible"]
    & (
        picks["season_points"]
        == 0
    )
    & (
        picks[
            "position_percentile"
        ].isna()
    )
)

picks.loc[
    zero_outcome,
    "position_percentile",
] = 0.0


eligible = picks[
    picks["draft_value_eligible"]
].copy()


# ============================================================
# EXPECTED POSITIONAL OUTCOME BY DRAFT CAPITAL
#
# For each pick, use selections within +/- 12 overall picks
# from OTHER seasons.
#
# This prevents the pick being graded from influencing its
# own expectation and provides a smooth draft-capital curve.
# ============================================================

PICK_WINDOW = 12

eligible[
    "expected_position_percentile"
] = np.nan

eligible[
    "comparison_sample"
] = 0


for idx, row in eligible.iterrows():

    peers = eligible[
        eligible[
            "overall_pick"
        ].between(
            max(
                1,
                int(
                    row[
                        "overall_pick"
                    ]
                )
                - PICK_WINDOW,
            ),
            min(
                180,
                int(
                    row[
                        "overall_pick"
                    ]
                )
                + PICK_WINDOW,
            ),
        )
        &
        (
            eligible["year"]
            != row["year"]
        )
        &
        (
            eligible[
                "position_percentile"
            ].notna()
        )
    ]

    if len(peers) >= 20:

        eligible.loc[
            idx,
            "expected_position_percentile",
        ] = (
            peers[
                "position_percentile"
            ]
            .median()
        )

        eligible.loc[
            idx,
            "comparison_sample",
        ] = len(peers)


# ============================================================
# DRAFT VALUE
#
# Positive = outperformed historical expectation for the
# draft capital spent.
#
# Negative = underperformed expectation.
#
# Units are percentile points, making positions directly
# comparable.
# ============================================================

eligible["draft_value"] = (
    eligible["position_percentile"]
    - eligible[
        "expected_position_percentile"
    ]
)

eligible[
    "value_above_expected"
] = eligible["draft_value"]


# ============================================================
# RETENTION / UTILIZATION
# ============================================================

eligible["capture_rate"] = np.where(
    eligible["season_points"] > 0,
    (
        eligible["captured_points"]
        / eligible["season_points"]
    ),
    np.nan,
)

eligible[
    "starter_utilization_rate"
] = np.where(
    eligible["captured_points"] > 0,
    (
        eligible["started_points"]
        / eligible["captured_points"]
    ),
    np.nan,
)


# ============================================================
# MERGE BACK TO FULL PICK TABLE
# ============================================================

value_cols = [
    "position_percentile",
    "expected_position_percentile",
    "comparison_sample",
    "draft_value",
    "value_above_expected",
    "capture_rate",
    "starter_utilization_rate",
]

for col in value_cols:

    if col not in picks.columns:
        picks[col] = np.nan


eligible_indexed = eligible.set_index(
    [
        "year",
        "overall_pick",
    ]
)


for idx, row in picks.iterrows():

    key = (
        row["year"],
        row["overall_pick"],
    )

    if key not in eligible_indexed.index:
        continue

    source = eligible_indexed.loc[
        key
    ]

    for col in value_cols:

        picks.loc[
            idx,
            col,
        ] = source[col]


# ============================================================
# COMPATIBILITY COLUMNS
#
# Temporary aliases so the existing reporting section can
# still run. These will be removed when the output schema is
# finalized.
# ============================================================

picks["expected_points"] = (
    picks[
        "expected_position_percentile"
    ]
)

picks["value_ratio"] = np.where(
    picks[
        "expected_position_percentile"
    ] > 0,
    (
        picks["position_percentile"]
        / picks[
            "expected_position_percentile"
        ]
    ),
    np.nan,
)

picks[
    "captured_value_above_expected"
] = (
    picks["draft_value"]
    * picks["capture_rate"].fillna(0)
)

picks[
    "captured_value_ratio"
] = picks["capture_rate"]

# ============================================================
# HIT / BUST CLASSIFICATION
#
# Draft Value is measured in positional-percentile points.
#
# +40 or more = Elite Steal
# +25 to +39.99 = Steal
# -24.99 to +24.99 = Near Expectation
# -25 to -39.99 = Bust
# -40 or worse = Major Bust
# ============================================================

picks["draft_result"] = "Not Rated"

rated = (
    picks["draft_value_eligible"]
    & picks["draft_value"].notna()
)

picks.loc[
    rated
    & (picks["draft_value"] >= 40),
    "draft_result",
] = "Elite Steal"

picks.loc[
    rated
    & (picks["draft_value"] >= 25)
    & (picks["draft_value"] < 40),
    "draft_result",
] = "Steal"

picks.loc[
    rated
    & (picks["draft_value"] > -25)
    & (picks["draft_value"] < 25),
    "draft_result",
] = "Near Expectation"

picks.loc[
    rated
    & (picks["draft_value"] <= -25)
    & (picks["draft_value"] > -40),
    "draft_result",
] = "Bust"

picks.loc[
    rated
    & (picks["draft_value"] <= -40),
    "draft_result",
] = "Major Bust"

# ============================================================
# FRANCHISE SUMMARY
# ============================================================

franchise_base = picks[
    picks["draft_value_eligible"]
    & picks["draft_value"].notna()
].copy()


def count_steals(series):
    return series.isin(
        [
            "Steal",
            "Elite Steal",
        ]
    ).sum()


def count_elite_steals(series):
    return (
        series == "Elite Steal"
    ).sum()


def count_busts(series):
    return series.isin(
        [
            "Bust",
            "Major Bust",
        ]
    ).sum()


def count_major_busts(series):
    return (
        series == "Major Bust"
    ).sum()


franchise = (
    franchise_base
    .groupby(
        "canonical_team",
        as_index=False,
    )
    .agg(
        rated_picks=(
            "player",
            "size",
        ),
        avg_draft_value=(
            "draft_value",
            "mean",
        ),
        median_draft_value=(
            "draft_value",
            "median",
        ),
        total_draft_value=(
            "draft_value",
            "sum",
        ),
        avg_actual_percentile=(
            "position_percentile",
            "mean",
        ),
        avg_expected_percentile=(
            "expected_position_percentile",
            "mean",
        ),
        steals=(
            "draft_result",
            count_steals,
        ),
        elite_steals=(
            "draft_result",
            count_elite_steals,
        ),
        busts=(
            "draft_result",
            count_busts,
        ),
        major_busts=(
            "draft_result",
            count_major_busts,
        ),
        avg_capture_rate=(
            "capture_rate",
            "mean",
        ),
        avg_starter_utilization=(
            "starter_utilization_rate",
            "mean",
        ),
    )
)


franchise["steal_rate"] = (
    franchise["steals"]
    / franchise["rated_picks"]
)

franchise["bust_rate"] = (
    franchise["busts"]
    / franchise["rated_picks"]
)

franchise["net_hits"] = (
    franchise["steals"]
    - franchise["busts"]
)


franchise = franchise.sort_values(
    [
        "avg_draft_value",
        "median_draft_value",
    ],
    ascending=[
        False,
        False,
    ],
).reset_index(
    drop=True
)


franchise["draft_value_rank"] = (
    franchise.index + 1
)


# ============================================================
# TEAM-SEASON DRAFT CLASSES
# ============================================================

team_season = (
    franchise_base
    .groupby(
        [
            "year",
            "canonical_team",
        ],
        as_index=False,
    )
    .agg(
        rated_picks=(
            "player",
            "size",
        ),
        avg_draft_value=(
            "draft_value",
            "mean",
        ),
        median_draft_value=(
            "draft_value",
            "median",
        ),
        total_draft_value=(
            "draft_value",
            "sum",
        ),
        avg_actual_percentile=(
            "position_percentile",
            "mean",
        ),
        avg_expected_percentile=(
            "expected_position_percentile",
            "mean",
        ),
        steals=(
            "draft_result",
            count_steals,
        ),
        elite_steals=(
            "draft_result",
            count_elite_steals,
        ),
        busts=(
            "draft_result",
            count_busts,
        ),
        major_busts=(
            "draft_result",
            count_major_busts,
        ),
        avg_capture_rate=(
            "capture_rate",
            "mean",
        ),
    )
)


team_season["steal_rate"] = (
    team_season["steals"]
    / team_season["rated_picks"]
)

team_season["bust_rate"] = (
    team_season["busts"]
    / team_season["rated_picks"]
)

team_season["net_hits"] = (
    team_season["steals"]
    - team_season["busts"]
)


team_season["draft_class_rank"] = (
    team_season
    .groupby("year")[
        "avg_draft_value"
    ]
    .rank(
        method="min",
        ascending=False,
    )
    .astype(int)
)

# ============================================================
# ROUND SUMMARY
# ============================================================

round_summary = (
    franchise_base
    .groupby(
        "round",
        as_index=False,
    )
    .agg(
        picks=(
            "player",
            "size",
        ),
        avg_season_points=(
            "season_points",
            "mean",
        ),
        median_season_points=(
            "season_points",
            "median",
        ),
        avg_expected_points=(
            "expected_points",
            "mean",
        ),
        avg_value_above_expected=(
            "value_above_expected",
            "mean",
        ),
        steal_rate=(
            "draft_result",
            lambda s:
                s.isin(
                    ["Steal", "Elite Steal"]
                ).mean(),
        ),
        bust_rate=(
            "draft_result",
            lambda s:
                s.isin(
                    ["Bust", "Major Bust"]
                ).mean(),
        ),
    )
)


# ============================================================
# PLAYER HISTORY TABLES
# ============================================================

best_picks = (
    franchise_base
    .sort_values(
        [
            "value_above_expected",
            "season_points",
        ],
        ascending=[
            False,
            False,
        ],
    )
    .copy()
)

biggest_busts = (
    franchise_base
    .sort_values(
        [
            "value_above_expected",
            "season_points",
        ],
        ascending=[
            True,
            True,
        ],
    )
    .copy()
)

late_round_steals = (
    franchise_base[
        franchise_base["round"] >= 8
    ]
    .sort_values(
        [
            "value_above_expected",
            "season_points",
        ],
        ascending=[
            False,
            False,
        ],
    )
    .copy()
)

first_round = (
    franchise_base[
        franchise_base["round"] == 1
    ]
    .sort_values(
        [
            "value_above_expected",
            "season_points",
        ],
        ascending=[
            True,
            True,
        ],
    )
    .copy()
)


# ============================================================
# WRITE OUTPUTS
# ============================================================

outputs = {
    "draft_value_picks.csv":
        picks,

    "draft_value_franchise.csv":
        franchise,

    "draft_value_team_season.csv":
        team_season,

    "draft_value_round.csv":
        round_summary,

    "draft_value_best_picks.csv":
        best_picks,

    "draft_value_biggest_busts.csv":
        biggest_busts,

    "draft_value_late_round_steals.csv":
        late_round_steals,

    "draft_value_first_round.csv":
        first_round,
}

for filename, df in outputs.items():

    path = OUTPUT_DIR / filename

    df.to_csv(
        path,
        index=False,
    )

    print(
        f"Wrote {path} "
        f"({len(df):,} rows)"
    )


# ============================================================
# VALIDATION
# ============================================================

print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)

if len(picks) != len(draft):
    raise ValueError(
        "Draft pick row count changed."
    )

print(
    f"PASS — {len(picks):,} draft picks preserved."
)

duplicate_picks = (
    picks
    .duplicated(
        [
            "year",
            "overall_pick",
        ]
    )
    .sum()
)

if duplicate_picks:
    raise ValueError(
        f"{duplicate_picks} duplicate draft picks."
    )

print(
    "PASS — year/overall pick is unique."
)

negative_capture = (
    picks["captured_points"] < 0
).sum()

if negative_capture:
    print(
        "NOTE — negative captured production exists "
        "because fantasy scoring can be negative."
    )

eligible_count = int(
    picks[
        "draft_value_eligible"
    ].sum()
)

rated_count = int(
    (
        picks["draft_value_eligible"]
        & picks["expected_points"].notna()
    ).sum()
)

future_rated = int(
    (
        (picks["year"] > DRAFT_VALUE_THROUGH_YEAR)
        & picks["draft_value"].notna()
    ).sum()
)

if future_rated:
    raise ValueError(
        f"{future_rated} picks after {DRAFT_VALUE_THROUGH_YEAR} "
        "were incorrectly assigned Draft Value."
    )

future_eligible = int(
    (
        (picks["year"] > DRAFT_VALUE_THROUGH_YEAR)
        & picks["draft_value_eligible"]
    ).sum()
)

if future_eligible:
    raise ValueError(
        f"{future_eligible} picks after {DRAFT_VALUE_THROUGH_YEAR} "
        "were incorrectly marked Draft Value eligible."
    )

print(
    f"PASS — Draft Value outcomes are frozen through "
    f"{DRAFT_VALUE_THROUGH_YEAR}."
)

print(
    f"Eligible skill-position non-keeper picks: "
    f"{eligible_count:,}"
)

print(
    f"Rated picks with historical expectation: "
    f"{rated_count:,}"
)

print(
    "Coverage: "
    f"{rated_count / eligible_count * 100:.1f}%"
    if eligible_count
    else "Coverage: N/A"
)


# ============================================================
# RESULTS
# ============================================================

print("\n" + "=" * 80)
print("TOP DRAFTING FRANCHISES")
print("=" * 80)

print(
    franchise[
        [
            "draft_value_rank",
            "canonical_team",
            "rated_picks",
            "avg_draft_value",
            "median_draft_value",
            "steals",
            "elite_steals",
            "busts",
            "major_busts",
            "steal_rate",
            "bust_rate",
            "avg_capture_rate",
        ]
    ]
    .to_string(
        index=False
    )
)


print("\n" + "=" * 80)
print("BIGGEST STEALS")
print("=" * 80)

print(
    franchise_base
    .sort_values(
        "draft_value",
        ascending=False,
    )[
        [
            "year",
            "round",
            "overall_pick",
            "canonical_team",
            "player",
            "position",
            "season_points",
            "position_percentile",
            "expected_position_percentile",
            "draft_value",
            "draft_result",
            "capture_rate",
        ]
    ]
    .head(20)
    .to_string(
        index=False
    )
)


print("\n" + "=" * 80)
print("BIGGEST BUSTS")
print("=" * 80)

print(
    franchise_base
    .sort_values(
        "draft_value",
        ascending=True,
    )[
        [
            "year",
            "round",
            "overall_pick",
            "canonical_team",
            "player",
            "position",
            "season_points",
            "position_percentile",
            "expected_position_percentile",
            "draft_value",
            "draft_result",
        ]
    ]
    .head(20)
    .to_string(
        index=False
    )
)


print("\n" + "=" * 80)
print("BEST DRAFT CLASSES")
print("=" * 80)

print(
    team_season
    .sort_values(
        "avg_draft_value",
        ascending=False,
    )[
        [
            "year",
            "canonical_team",
            "rated_picks",
            "avg_draft_value",
            "total_draft_value",
            "steals",
            "busts",
            "net_hits",
            "avg_capture_rate",
        ]
    ]
    .head(15)
    .to_string(
        index=False
    )
)


print("\n" + "=" * 80)
print("WORST DRAFT CLASSES")
print("=" * 80)

print(
    team_season
    .sort_values(
        "avg_draft_value",
        ascending=True,
    )[
        [
            "year",
            "canonical_team",
            "rated_picks",
            "avg_draft_value",
            "total_draft_value",
            "steals",
            "busts",
            "net_hits",
            "avg_capture_rate",
        ]
    ]
    .head(15)
    .to_string(
        index=False
    )
)