from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# PATHS
# ============================================================

MATCHUPS = Path(
    "data/all_matchups_clean_2017_2025.csv"
)

EFFICIENCY = Path(
    "data/matchups/player_week_stats/analysis/"
    "lineup_efficiency_season.csv"
)

DRAFT = Path(
    "data/analysis/draft_value_team_season.csv"
)

WAIVER = Path(
    "data/analysis/waiver_value_team_season.csv"
)

CHAMP_ROSTERS = Path(
    "data/playoffs/player_championship_rosters.csv"
)

OUT_DIR = Path("data/analysis")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TEAM_SEASON_OUT = (
    OUT_DIR / "championship_dna_team_season.csv"
)

CHAMPIONS_OUT = (
    OUT_DIR / "championship_dna_champions.csv"
)

COMPARISON_OUT = (
    OUT_DIR / "championship_dna_comparison.csv"
)

TRAITS_OUT = (
    OUT_DIR / "championship_dna_traits.csv"
)


# ============================================================
# TEAM ALIASES
# ============================================================

ALIASES = {
    "PickUpYourBratsMalle":
        "ThreatLevelMidnight",
    "Little Red Fournette":
        "Post Mahomes",
    "Ur The Best Bellows":
        "Joe Mantegna",
    "You Better Park It":
        "Buttermilk Puuump",
    "Buttermilk Pump":
        "Buttermilk Puuump",
}


def canon(team):
    return ALIASES.get(team, team)


# ============================================================
# LOAD
# ============================================================

print("=" * 90)
print("CHAMPIONSHIP DNA")
print("=" * 90)

games = pd.read_csv(MATCHUPS)
eff = pd.read_csv(EFFICIENCY)
draft = pd.read_csv(DRAFT)
waiver = pd.read_csv(WAIVER)
champ_rosters = pd.read_csv(CHAMP_ROSTERS)


# ============================================================
# CHAMPIONS
# ============================================================

champions = (
    champ_rosters[
        ["year", "champion"]
    ]
    .drop_duplicates()
    .copy()
)

champions["team"] = (
    champions["champion"].map(canon)
)

champions = champions[
    ["year", "team"]
].copy()

if len(champions) != 9:
    raise RuntimeError(
        f"Expected 9 champions; found {len(champions)}."
    )

if champions["year"].duplicated().any():
    raise RuntimeError(
        "Multiple champions found in a season."
    )


# ============================================================
# MATCHUPS -> TEAM WEEK
# ============================================================

a = pd.DataFrame({
    "year": games["year"],
    "week": games["week"],
    "team": games["team_1"].map(canon),
    "opponent": games["team_2"].map(canon),
    "points": games["team_1_score"],
    "points_against": games["team_2_score"],
})

b = pd.DataFrame({
    "year": games["year"],
    "week": games["week"],
    "team": games["team_2"].map(canon),
    "opponent": games["team_1"].map(canon),
    "points": games["team_2_score"],
    "points_against": games["team_1_score"],
})

team_week = pd.concat(
    [a, b],
    ignore_index=True,
)

duplicate_team_weeks = (
    team_week
    .duplicated(
        ["year", "week", "team"]
    )
    .sum()
)

if duplicate_team_weeks:
    raise RuntimeError(
        f"Duplicate team-weeks: {duplicate_team_weeks}"
    )

team_week["win"] = (
    team_week["points"]
    > team_week["points_against"]
).astype(float)

team_week["tie"] = (
    team_week["points"]
    == team_week["points_against"]
).astype(float)

team_week["win_equivalent"] = (
    team_week["win"]
    + 0.5 * team_week["tie"]
)


# ============================================================
# BASE TEAM-SEASON
# ============================================================

dna = (
    team_week
    .groupby(
        ["year", "team"],
        as_index=False,
    )
    .agg(
        games=("week", "nunique"),
        wins=("win_equivalent", "sum"),
        points_for=("points", "sum"),
        points_against=("points_against", "sum"),
    )
)

dna["losses"] = (
    dna["games"] - dna["wins"]
)

dna["win_pct"] = (
    dna["wins"] / dna["games"]
)

dna["points_per_game"] = (
    dna["points_for"] / dna["games"]
)

dna["scoring_rank"] = (
    dna
    .groupby("year")["points_for"]
    .rank(
        method="min",
        ascending=False,
    )
    .astype(int)
)

dna["win_rank"] = (
    dna
    .groupby("year")["wins"]
    .rank(
        method="min",
        ascending=False,
    )
    .astype(int)
)


# ============================================================
# LINEUP EFFICIENCY
# ============================================================

eff = eff.copy()

eff["team"] = (
    eff["fantasy_team"].map(canon)
)

eff = eff[
    [
        "year",
        "team",
        "actual_points",
        "optimal_points",
        "points_left_on_bench",
        "avg_weekly_points_left",
        "avoidable_starts",
        "season_efficiency_pct",
    ]
].copy()

if eff.duplicated(
    ["year", "team"]
).any():
    raise RuntimeError(
        "Duplicate lineup-efficiency team-seasons."
    )

dna = dna.merge(
    eff,
    on=["year", "team"],
    how="left",
    validate="one_to_one",
)

dna["efficiency_rank"] = (
    dna
    .groupby("year")[
        "season_efficiency_pct"
    ]
    .rank(
        method="min",
        ascending=False,
    )
    .astype(int)
)


# ============================================================
# DRAFT VALUE
# ============================================================

draft = draft.copy()

draft["team"] = (
    draft["canonical_team"].map(canon)
)

draft = draft[
    [
        "year",
        "team",
        "rated_picks",
        "avg_draft_value",
        "total_draft_value",
        "steals",
        "elite_steals",
        "busts",
        "major_busts",
        "draft_class_rank",
    ]
].copy()

if draft.duplicated(
    ["year", "team"]
).any():
    raise RuntimeError(
        "Duplicate Draft Value team-seasons."
    )

dna = dna.merge(
    draft,
    on=["year", "team"],
    how="left",
    validate="one_to_one",
)


# ============================================================
# WAIVER VALUE
# ============================================================

waiver = waiver.copy()

waiver["team"] = (
    waiver["team"].map(canon)
)

waiver = waiver[
    [
        "year",
        "team",
        "meaningful_acquisitions",
        "avg_waiver_value",
        "total_positive_value",
        "good_rate",
        "elite_finds",
        "bust_rate",
        "production_points",
    ]
].copy()

if waiver.duplicated(
    ["year", "team"]
).any():
    raise RuntimeError(
        "Duplicate Waiver Value team-seasons."
    )

dna = dna.merge(
    waiver,
    on=["year", "team"],
    how="left",
    validate="one_to_one",
)

dna["waiver_rank"] = (
    dna
    .groupby("year")[
        "avg_waiver_value"
    ]
    .rank(
        method="min",
        ascending=False,
    )
)


# ============================================================
# CHAMPION FLAG
# ============================================================

champion_keys = set(
    zip(
        champions["year"],
        champions["team"],
    )
)

dna["is_champion"] = [
    (year, team) in champion_keys
    for year, team in zip(
        dna["year"],
        dna["team"],
    )
]


# ============================================================
# SEASON PERCENTILES
#
# These make unlike seasons comparable.
# 100 = best in league that season.
# ============================================================

def percentile_high(series):
    return (
        series.rank(
            method="average",
            pct=True,
            ascending=True,
        )
        * 100
    )


def percentile_low(series):
    return (
        series.rank(
            method="average",
            pct=True,
            ascending=False,
        )
        * 100
    )


dna["scoring_percentile"] = (
    dna
    .groupby("year")[
        "points_per_game"
    ]
    .transform(percentile_high)
)

dna["winning_percentile"] = (
    dna
    .groupby("year")[
        "win_pct"
    ]
    .transform(percentile_high)
)

dna["efficiency_percentile"] = (
    dna
    .groupby("year")[
        "season_efficiency_pct"
    ]
    .transform(percentile_high)
)

dna["bench_management_percentile"] = (
    dna
    .groupby("year")[
        "avg_weekly_points_left"
    ]
    .transform(percentile_low)
)

dna["draft_percentile"] = (
    dna
    .groupby("year")[
        "avg_draft_value"
    ]
    .transform(percentile_high)
)

dna["waiver_percentile"] = (
    dna
    .groupby("year")[
        "avg_waiver_value"
    ]
    .transform(percentile_high)
)


# ============================================================
# CHAMPION PROFILES
# ============================================================

champion_profiles = (
    dna[
        dna["is_champion"]
    ]
    .copy()
    .sort_values("year")
)


# ============================================================
# CHAMPION VS NON-CHAMPION COMPARISON
# ============================================================

metric_specs = [
    (
        "Winning",
        "win_pct",
        True,
    ),
    (
        "Scoring",
        "points_per_game",
        True,
    ),
    (
        "Lineup Efficiency",
        "season_efficiency_pct",
        True,
    ),
    (
        "Bench Management",
        "avg_weekly_points_left",
        False,
    ),
    (
        "Draft Value",
        "avg_draft_value",
        True,
    ),
    (
        "Waiver Value",
        "avg_waiver_value",
        True,
    ),
    (
        "Waiver Positive Value",
        "total_positive_value",
        True,
    ),
]

comparison_rows = []

for label, col, higher_better in metric_specs:

    champ_values = (
        dna.loc[
            dna["is_champion"],
            col,
        ]
        .dropna()
    )

    other_values = (
        dna.loc[
            ~dna["is_champion"],
            col,
        ]
        .dropna()
    )

    champion_mean = (
        champ_values.mean()
    )

    nonchampion_mean = (
        other_values.mean()
    )

    raw_difference = (
        champion_mean
        - nonchampion_mean
    )

    population_sd = (
        dna[col]
        .dropna()
        .std(ddof=0)
    )

    standardized_gap = (
        raw_difference
        / population_sd
        if population_sd > 0
        else np.nan
    )

    favorable_gap = (
        standardized_gap
        if higher_better
        else -standardized_gap
    )

    comparison_rows.append({
        "metric": label,
        "source_column": col,
        "higher_is_better": higher_better,
        "champion_mean": champion_mean,
        "nonchampion_mean": nonchampion_mean,
        "raw_difference": raw_difference,
        "favorable_standardized_gap":
            favorable_gap,
        "champion_n": len(champ_values),
        "nonchampion_n": len(other_values),
    })

comparison = pd.DataFrame(
    comparison_rows
).sort_values(
    "favorable_standardized_gap",
    ascending=False,
)


# ============================================================
# CHAMPIONSHIP TRAITS
#
# Descriptive only — NOT a composite championship score.
# ============================================================

trait_specs = [
    (
        "Winning",
        "winning_percentile",
    ),
    (
        "Scoring",
        "scoring_percentile",
    ),
    (
        "Lineup Efficiency",
        "efficiency_percentile",
    ),
    (
        "Bench Management",
        "bench_management_percentile",
    ),
    (
        "Draft",
        "draft_percentile",
    ),
    (
        "Waivers",
        "waiver_percentile",
    ),
]

trait_rows = []

for trait, col in trait_specs:

    values = (
        champion_profiles[col]
        .dropna()
    )

    trait_rows.append({
        "trait": trait,
        "champion_average_percentile":
            values.mean(),
        "champion_median_percentile":
            values.median(),
        "champion_seasons_available":
            len(values),
        "champions_top_3": (
            champion_profiles[
                col
            ]
            .ge(75)
            .sum()
        ),
    })

traits = (
    pd.DataFrame(trait_rows)
    .sort_values(
        "champion_average_percentile",
        ascending=False,
    )
)


# ============================================================
# VALIDATION
# ============================================================

print()
print("=" * 90)
print("VALIDATION")
print("=" * 90)

print(
    f"Team-seasons: {len(dna):,}"
)
print(
    f"Champion seasons: "
    f"{int(dna['is_champion'].sum())}"
)

print(
    "Missing lineup:",
    int(
        dna[
            "season_efficiency_pct"
        ].isna().sum()
    ),
)

print(
    "Missing draft:",
    int(
        dna[
            "avg_draft_value"
        ].isna().sum()
    ),
)

print(
    "Missing waiver:",
    int(
        dna[
            "avg_waiver_value"
        ].isna().sum()
    ),
)

if len(dna) != 108:
    raise RuntimeError(
        "Expected 108 team-seasons."
    )

if dna["is_champion"].sum() != 9:
    raise RuntimeError(
        "Expected 9 champion seasons."
    )

if dna[
    "season_efficiency_pct"
].isna().any():
    raise RuntimeError(
        "Incomplete lineup efficiency."
    )

if dna[
    "avg_draft_value"
].isna().any():
    raise RuntimeError(
        "Incomplete Draft Value."
    )

expected_missing_waiver = (
    dna["year"].eq(2018)
)

actual_missing_waiver = (
    dna[
        "avg_waiver_value"
    ].isna()
)

if not actual_missing_waiver.equals(
    expected_missing_waiver
):
    raise RuntimeError(
        "Waiver Value should be missing "
        "only for all 12 teams in 2018."
    )


# ============================================================
# REGRESSION CHECKS FROM AUDIT
# ============================================================

champ_comparison = (
    comparison
    .set_index("metric")
)

expected_order = [
    "Winning",
    "Lineup Efficiency",
    "Scoring",
    "Bench Management",
]

actual_top_four = (
    comparison[
        "metric"
    ]
    .head(4)
    .tolist()
)

print()
print(
    "Top-four championship traits:",
    actual_top_four,
)

if actual_top_four != expected_order:
    raise RuntimeError(
        "Championship trait regression "
        "does not match audited result."
    )

if not (
    champ_comparison.loc[
        "Waiver Value",
        "favorable_standardized_gap",
    ] < 0
):
    raise RuntimeError(
        "Expected Waiver Value champion gap "
        "to remain negative."
    )


# ============================================================
# OUTPUT
# ============================================================

dna.to_csv(
    TEAM_SEASON_OUT,
    index=False,
)

champion_profiles.to_csv(
    CHAMPIONS_OUT,
    index=False,
)

comparison.to_csv(
    COMPARISON_OUT,
    index=False,
)

traits.to_csv(
    TRAITS_OUT,
    index=False,
)


# ============================================================
# REPORT
# ============================================================

print()
print("=" * 90)
print("CHAMPIONSHIP DNA")
print("=" * 90)

print(
    comparison[
        [
            "metric",
            "champion_mean",
            "nonchampion_mean",
            "favorable_standardized_gap",
        ]
    ]
    .round(3)
    .to_string(index=False)
)

print()
print("=" * 90)
print("CHAMPION TRAIT PERCENTILES")
print("=" * 90)

print(
    traits
    .round(2)
    .to_string(index=False)
)

print()
print("=" * 90)
print("CHAMPION PROFILES")
print("=" * 90)

print(
    champion_profiles[
        [
            "year",
            "team",
            "wins",
            "scoring_rank",
            "efficiency_rank",
            "draft_class_rank",
            "waiver_rank",
        ]
    ]
    .sort_values("year")
    .to_string(index=False)
)

print()
print("=" * 90)
print("OUTPUTS")
print("=" * 90)

print(TEAM_SEASON_OUT)
print(CHAMPIONS_OUT)
print(COMPARISON_OUT)
print(TRAITS_OUT)

print()
print(
    "PASS — CHAMPIONSHIP DNA BUILT"
)
