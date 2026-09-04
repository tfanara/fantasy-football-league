from pathlib import Path
import pandas as pd
import numpy as np

from season_config import (
    LAST_COMPLETED_SEASON,
    print_season_config,
)


INPUT = Path("data/analysis/championship_dna_team_season.csv")
OUTPUT_DIR = Path("data/analysis")

TEAM_SEASON_OUT = OUTPUT_DIR / "management_index_team_season.csv"
FRANCHISE_OUT = OUTPUT_DIR / "management_index_franchise.csv"
EXTREMES_OUT = OUTPUT_DIR / "management_index_extremes.csv"
PROFILE_OUT = OUTPUT_DIR / "management_index_profiles.csv"


# ============================================================
# SETTINGS
# ============================================================

LINEUP_WEIGHT = 0.50
DRAFT_WEIGHT = 0.25
WAIVER_WEIGHT = 0.25

MIN_OFFICIAL_SEASONS = 5


# ============================================================
# HELPERS
# ============================================================

def pct_high(series):
    """
    Higher value = better.

    Percentile is calculated within each fantasy season.
    """
    return (
        series.rank(
            method="average",
            pct=True,
            ascending=True,
        ) * 100
    )


# ============================================================
# LOAD
# ============================================================

if not INPUT.exists():
    raise FileNotFoundError(INPUT)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

df = pd.read_csv(INPUT)

print_season_config()

if "year" not in df.columns:
    raise RuntimeError("Input is missing required column: year")

df["year"] = pd.to_numeric(
    df["year"],
    errors="coerce",
)

if df["year"].isna().any():
    raise RuntimeError(
        f"Input contains {int(df['year'].isna().sum())} rows with invalid years."
    )

df["year"] = df["year"].astype(int)

future_rows = df[
    df["year"] > LAST_COMPLETED_SEASON
].copy()

if not future_rows.empty:
    print(
        f"Excluding {len(future_rows):,} team-season rows after "
        f"LAST_COMPLETED_SEASON={LAST_COMPLETED_SEASON}."
    )

df = df[
    df["year"] <= LAST_COMPLETED_SEASON
].copy()


required = [
    "year",
    "team",
    "season_efficiency_pct",
    "avg_draft_value",
    "avg_waiver_value",
    "winning_percentile",
    "scoring_percentile",
    "is_champion",
]

missing = [
    col for col in required
    if col not in df.columns
]

if missing:
    raise RuntimeError(
        f"Missing required columns: {missing}"
    )


# ============================================================
# BASIC VALIDATION
# ============================================================

season_counts = (
    df.groupby("year")
    .size()
    .sort_index()
)

bad_season_counts = season_counts[
    season_counts != 12
]

if not bad_season_counts.empty:
    raise RuntimeError(
        "Expected 12 team-seasons in every completed season. "
        f"Found: {bad_season_counts.to_dict()}"
    )

duplicates = df.duplicated(
    ["year", "team"]
).sum()

if duplicates:
    raise RuntimeError(
        f"Duplicate year/team rows: {duplicates}"
    )


# ============================================================
# SEASON-RELATIVE COMPONENTS
# ============================================================

df["lineup_index"] = (
    df.groupby("year")[
        "season_efficiency_pct"
    ]
    .transform(pct_high)
)

df["draft_index"] = (
    df.groupby("year")[
        "avg_draft_value"
    ]
    .transform(pct_high)
)

df["waiver_index"] = (
    df.groupby("year")[
        "avg_waiver_value"
    ]
    .transform(pct_high)
)


# ============================================================
# MANAGEMENT INDEX
#
# All three components are required.
#
# We DO NOT redistribute missing weights.
# Therefore 2018 receives no Management Index because
# historical waiver transaction data is unavailable.
# ============================================================

df["fully_measured"] = (
    df[
        [
            "lineup_index",
            "draft_index",
            "waiver_index",
        ]
    ]
    .notna()
    .all(axis=1)
)

df["management_index"] = np.nan

mask = df["fully_measured"]

df.loc[
    mask,
    "management_index",
] = (
    LINEUP_WEIGHT
    * df.loc[mask, "lineup_index"]
    +
    DRAFT_WEIGHT
    * df.loc[mask, "draft_index"]
    +
    WAIVER_WEIGHT
    * df.loc[mask, "waiver_index"]
)


# ============================================================
# SEASON RANK
# ============================================================

df["management_rank"] = np.nan

df.loc[
    mask,
    "management_rank",
] = (
    df.loc[mask]
    .groupby("year")[
        "management_index"
    ]
    .rank(
        method="min",
        ascending=False,
    )
)


# ============================================================
# VALIDATE COVERAGE
# ============================================================

coverage = (
    df.groupby("year")[
        "management_index"
    ]
    .count()
)

expected = {
    year: (
        0
        if year == 2018
        else 12
    )
    for year in sorted(
        df["year"].unique()
    )
}

for year, count in expected.items():

    actual = int(
        coverage.get(year, 0)
    )

    if actual != count:
        raise RuntimeError(
            f"{year}: expected {count} "
            f"Management Index rows, found {actual}"
        )


measured = df[
    df["fully_measured"]
].copy()

expected_measured = sum(
    expected.values()
)

if len(measured) != expected_measured:
    raise RuntimeError(
        f"Expected {expected_measured} fully measured team-seasons, "
        f"found {len(measured)}"
    )


# ============================================================
# FRANCHISE SUMMARY
#
# IMPORTANT:
# Component averages use ONLY fully measured seasons so
# every displayed component covers exactly the same seasons
# as the Management Index.
# ============================================================

franchise = (
    measured.groupby("team")
    .agg(
        measured_seasons=(
            "year",
            "nunique",
        ),
        management_index=(
            "management_index",
            "mean",
        ),
        median_management_index=(
            "management_index",
            "median",
        ),
        best_management_index=(
            "management_index",
            "max",
        ),
        worst_management_index=(
            "management_index",
            "min",
        ),
        lineup_index=(
            "lineup_index",
            "mean",
        ),
        draft_index=(
            "draft_index",
            "mean",
        ),
        waiver_index=(
            "waiver_index",
            "mean",
        ),
        winning_percentile=(
            "winning_percentile",
            "mean",
        ),
        scoring_percentile=(
            "scoring_percentile",
            "mean",
        ),
        championships=(
            "is_champion",
            "sum",
        ),
    )
    .reset_index()
)

franchise["official"] = (
    franchise["measured_seasons"]
    >= MIN_OFFICIAL_SEASONS
)

franchise["management_rank"] = np.nan

official_mask = franchise["official"]

franchise.loc[
    official_mask,
    "management_rank",
] = (
    franchise.loc[
        official_mask,
        "management_index",
    ]
    .rank(
        method="min",
        ascending=False,
    )
)

franchise = franchise.sort_values(
    [
        "official",
        "management_rank",
        "management_index",
    ],
    ascending=[
        False,
        True,
        False,
    ],
)


# ============================================================
# MANAGEMENT STYLE / PROFILE
# ============================================================

profile = franchise[
    [
        "team",
        "measured_seasons",
        "management_index",
        "lineup_index",
        "draft_index",
        "waiver_index",
        "official",
        "management_rank",
    ]
].copy()


def strongest_area(row):

    values = {
        "Lineup Execution":
            row["lineup_index"],

        "Drafting":
            row["draft_index"],

        "Waivers":
            row["waiver_index"],
    }

    return max(
        values,
        key=values.get,
    )


def weakest_area(row):

    values = {
        "Lineup Execution":
            row["lineup_index"],

        "Drafting":
            row["draft_index"],

        "Waivers":
            row["waiver_index"],
    }

    return min(
        values,
        key=values.get,
    )


profile["strongest_area"] = profile.apply(
    strongest_area,
    axis=1,
)

profile["weakest_area"] = profile.apply(
    weakest_area,
    axis=1,
)


# ============================================================
# EXTREME SEASONS
# ============================================================

top = (
    measured.sort_values(
        "management_index",
        ascending=False,
    )
    .head(20)
    .copy()
)

top["extreme_type"] = (
    "Best Management Season"
)

bottom = (
    measured.sort_values(
        "management_index",
        ascending=True,
    )
    .head(20)
    .copy()
)

bottom["extreme_type"] = (
    "Worst Management Season"
)

extremes = pd.concat(
    [
        top,
        bottom,
    ],
    ignore_index=True,
)


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    TEAM_SEASON_OUT,
    index=False,
)

franchise.to_csv(
    FRANCHISE_OUT,
    index=False,
)

extremes.to_csv(
    EXTREMES_OUT,
    index=False,
)

profile.to_csv(
    PROFILE_OUT,
    index=False,
)


# ============================================================
# REGRESSION CHECKS
# ============================================================

if (df["year"] > LAST_COMPLETED_SEASON).any():
    raise RuntimeError(
        "Incomplete/future season leaked into Management Index output."
    )

official = franchise[
    franchise["official"]
].sort_values(
    "management_rank"
)

if len(official) != 12:
    raise RuntimeError(
        f"Expected 12 official franchises, "
        f"found {len(official)}"
    )


# Known result from methodology audit.
expected_leader = "Ginger FC"

actual_leader = (
    official.iloc[0]["team"]
)

if actual_leader != expected_leader:
    raise RuntimeError(
        "Management Index leader changed. "
        f"Expected {expected_leader}, "
        f"found {actual_leader}"
    )


best_season = measured.sort_values(
    "management_index",
    ascending=False,
).iloc[0]

if not (
    int(best_season["year"]) == 2022
    and
    best_season["team"] == "Big Sack Jack"
):
    raise RuntimeError(
        "Best management season regression failed."
    )


# ============================================================
# REPORT
# ============================================================

print("=" * 100)
print("MANAGEMENT INDEX")
print("=" * 100)

print()
print(
    "Formula: "
    "50% Lineup Execution + "
    "25% Draft Value + "
    "25% Waiver Value"
)

print(
    "Fully measured team-seasons:",
    len(measured),
)

print(
    "Official franchises:",
    len(official),
)

print()
print("=" * 100)
print("OFFICIAL ALL-TIME LEADERBOARD")
print("=" * 100)

print(
    official[
        [
            "management_rank",
            "team",
            "measured_seasons",
            "management_index",
            "lineup_index",
            "draft_index",
            "waiver_index",
            "winning_percentile",
            "championships",
        ]
    ]
    .round(2)
    .to_string(index=False)
)

print()
print("=" * 100)
print("BEST MANAGEMENT SEASONS")
print("=" * 100)

print(
    measured[
        [
            "year",
            "team",
            "management_index",
            "management_rank",
            "lineup_index",
            "draft_index",
            "waiver_index",
            "winning_percentile",
            "scoring_percentile",
            "is_champion",
        ]
    ]
    .sort_values(
        "management_index",
        ascending=False,
    )
    .head(10)
    .round(2)
    .to_string(index=False)
)

print()
print("=" * 100)
print("OUTPUTS")
print("=" * 100)

for path in [
    TEAM_SEASON_OUT,
    FRANCHISE_OUT,
    EXTREMES_OUT,
    PROFILE_OUT,
]:
    print(path)

print()
print(
    "PASS — MANAGEMENT INDEX BUILT"
)