from pathlib import Path
import pandas as pd
import numpy as np


LINEUPS = Path(
    "data/matchups/player_week_stats/"
    "all_weekly_lineups_2017_2025.csv"
)

NFL_MAP = Path(
    "data/nfl/player_week_teams.csv"
)

OUTPUT_DIR = Path("data/analysis")

TEAM_WEEK_OUT = OUTPUT_DIR / "positional_edge_team_week.csv"
SEASON_OUT = OUTPUT_DIR / "positional_edge_season.csv"
FRANCHISE_OUT = OUTPUT_DIR / "positional_edge_franchise.csv"
EXTREMES_OUT = OUTPUT_DIR / "positional_edge_extremes.csv"
PLAYER_OUT = OUTPUT_DIR / "positional_edge_player_contributions.csv"

POSITIONS = ["QB", "RB", "WR", "TE"]

TEAM_ALIASES = {
    "PickUpYourBratsMalle": "ThreatLevelMidnight",
    "Little Red Fournette": "Post Mahomes",
    "Ur The Best Bellows": "Joe Mantegna",
    "You Better Park It": "Buttermilk Puuump",
    "Buttermilk Pump": "Buttermilk Puuump",
}


# ============================================================
# HELPERS
# ============================================================

def clean_player(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def build_historical_lookup(df):

    fixed = df[
        (df["is_starter"] == True)
        &
        (df["lineup_slot"].isin(POSITIONS))
    ][
        [
            "player",
            "lineup_slot",
        ]
    ].copy()

    fixed["player"] = (
        fixed["player"]
        .map(clean_player)
    )

    fixed = fixed[
        (fixed["player"] != "")
        &
        (fixed["player"] != "(Empty)")
    ]

    counts = (
        fixed.groupby(
            [
                "player",
                "lineup_slot",
            ]
        )
        .size()
        .reset_index(
            name="appearances"
        )
    )

    # Most frequently observed fixed position wins.
    # Alphabetical position is only a deterministic tie-break.
    best = (
        counts.sort_values(
            [
                "player",
                "appearances",
                "lineup_slot",
            ],
            ascending=[
                True,
                False,
                True,
            ],
        )
        .drop_duplicates(
            "player"
        )
    )

    return dict(
        zip(
            best["player"],
            best["lineup_slot"],
        )
    )


# ============================================================
# LOAD
# ============================================================

df = pd.read_csv(LINEUPS)
nfl = pd.read_csv(NFL_MAP)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

df["player"] = (
    df["player"]
    .map(clean_player)
)

# Canonicalize historical franchise names before any
# team-week, season, or franchise aggregation.
df["fantasy_team"] = (
    df["fantasy_team"]
    .replace(TEAM_ALIASES)
)

df["opponent"] = (
    df["opponent"]
    .replace(TEAM_ALIASES)
)

df["fantasy_points"] = (
    pd.to_numeric(
        df["fantasy_points"],
        errors="coerce",
    )
    .fillna(0.0)
)


# ============================================================
# STARTERS
# ============================================================

starters = df[
    df["is_starter"] == True
].copy()

expected_starters = 1464 * 9

if len(starters) != expected_starters:
    raise RuntimeError(
        f"Expected {expected_starters:,} starter rows, "
        f"found {len(starters):,}"
    )


# ============================================================
# HISTORICAL POSITION LOOKUP
# ============================================================

historical = build_historical_lookup(df)

print(
    "Historical fixed-slot lookup:",
    f"{len(historical):,} players"
)


# ============================================================
# NFL PLAYER-WEEK POSITION LOOKUP
# ============================================================

nfl_lookup = nfl[
    [
        "year",
        "week",
        "player",
        "nfl_position",
    ]
].copy()

nfl_lookup["player"] = (
    nfl_lookup["player"]
    .map(clean_player)
)

nfl_lookup = (
    nfl_lookup.dropna(
        subset=[
            "year",
            "week",
            "player",
            "nfl_position",
        ]
    )
    .drop_duplicates(
        [
            "year",
            "week",
            "player",
        ]
    )
)

nfl_position_map = {
    (
        int(row.year),
        int(row.week),
        row.player,
    ): str(row.nfl_position).upper()
    for row in nfl_lookup.itertuples()
}


# ============================================================
# POSITION RESOLUTION
# ============================================================

def resolve_position(row):

    slot = str(
        row.get(
            "lineup_slot",
            "",
        )
    ).strip().upper()

    player = clean_player(
        row.get("player")
    )

    # Fixed starting slots are authoritative.
    if slot in POSITIONS:
        return slot, "fixed_slot"

    # We only need to resolve W/R/T beyond this point.
    if slot != "W/R/T":
        return "", "not_skill_position"

    if (
        not player
        or player == "(Empty)"
    ):
        return "", "empty_flex"

    # Historical fixed-slot appearances are preferred.
    historical_position = historical.get(
        player,
        "",
    )

    if historical_position in {
        "RB",
        "WR",
        "TE",
    }:
        return (
            historical_position,
            "historical_fixed_slot",
        )

    # Then use NFL player-week mapping.
    nfl_position = nfl_position_map.get(
        (
            int(row["year"]),
            int(row["week"]),
            player,
        ),
        "",
    )

    if nfl_position in {
        "RB",
        "WR",
        "TE",
    }:
        return (
            nfl_position,
            "nfl_player_week",
        )

    # --------------------------------------------------------
    # AUDITED HISTORICAL EXCEPTIONS
    #
    # These are only reached if the historical fixed-slot
    # lookup and NFL player-week map both fail.
    # --------------------------------------------------------

    fallback = {
        "DK Metcalf": "WR",
        "AJ Dillon": "RB",
        "Jeff Wilson Jr.": "RB",
        "Michael Carter": "RB",
        "Michael Thomas": "WR",

        # Yahoo allowed Kendall Hinton in W/R/T during the
        # unusual 2020 Week 12 Denver game. For fantasy
        # positional attribution he is treated as WR.
        "Kendall Hinton": "WR",
    }

    if player in fallback:
        return (
            fallback[player],
            "audited_fallback",
        )

    return "", "unresolved"


resolved = starters.apply(
    resolve_position,
    axis=1,
    result_type="expand",
)

resolved.columns = [
    "edge_position",
    "position_source",
]

starters[
    [
        "edge_position",
        "position_source",
    ]
] = resolved


# ============================================================
# POSITION RESOLUTION AUDIT
# ============================================================

flex = starters[
    starters["lineup_slot"] == "W/R/T"
].copy()

occupied_flex = flex[
    flex["player"] != "(Empty)"
].copy()

unresolved_flex = occupied_flex[
    ~occupied_flex[
        "edge_position"
    ].isin(
        [
            "RB",
            "WR",
            "TE",
        ]
    )
]

print()
print("=" * 100)
print("FLEX POSITION RESOLUTION")
print("=" * 100)

print(
    flex["position_source"]
    .value_counts(
        dropna=False
    )
    .to_string()
)

print()
print(
    "Total FLEX slots:",
    len(flex),
)

print(
    "Occupied FLEX slots:",
    len(occupied_flex),
)

print(
    "Empty FLEX slots:",
    (
        flex["player"]
        == "(Empty)"
    ).sum(),
)

print(
    "Unresolved occupied FLEX:",
    len(unresolved_flex),
)

if not unresolved_flex.empty:

    print(
        unresolved_flex[
            [
                "year",
                "week",
                "fantasy_team",
                "player",
                "fantasy_points",
            ]
        ].to_string(
            index=False
        )
    )

    raise RuntimeError(
        "Occupied FLEX starters remain unresolved."
    )


# ============================================================
# SKILL-POSITION STARTER PRODUCTION
# ============================================================

skill = starters[
    starters[
        "edge_position"
    ].isin(POSITIONS)
].copy()

team_position_week = (
    skill.groupby(
        [
            "year",
            "week",
            "fantasy_team",
            "edge_position",
        ],
        as_index=False,
    )
    .agg(
        starter_points=(
            "fantasy_points",
            "sum",
        ),
        starters_used=(
            "player",
            "count",
        ),
    )
)


# ============================================================
# CREATE COMPLETE TEAM-WEEK × POSITION GRID
#
# Important because an empty FLEX slot should not cause an
# entire team-position-week to disappear.
# ============================================================

team_weeks = (
    df[
        [
            "year",
            "week",
            "fantasy_team",
        ]
    ]
    .drop_duplicates()
)

position_df = pd.DataFrame(
    {
        "edge_position":
            POSITIONS
    }
)

team_weeks["_key"] = 1
position_df["_key"] = 1

grid = (
    team_weeks.merge(
        position_df,
        on="_key",
    )
    .drop(
        columns="_key"
    )
)

team_week = grid.merge(
    team_position_week,
    on=[
        "year",
        "week",
        "fantasy_team",
        "edge_position",
    ],
    how="left",
)

team_week[
    [
        "starter_points",
        "starters_used",
    ]
] = (
    team_week[
        [
            "starter_points",
            "starters_used",
        ]
    ]
    .fillna(0)
)


# ============================================================
# WEEKLY LEAGUE BASELINE
#
# Compare each team with the OTHER 11 teams.
# ============================================================

group_cols = [
    "year",
    "week",
    "edge_position",
]

team_week[
    "league_total_points"
] = (
    team_week.groupby(
        group_cols
    )[
        "starter_points"
    ]
    .transform("sum")
)

team_week[
    "teams_in_week"
] = (
    team_week.groupby(
        group_cols
    )[
        "fantasy_team"
    ]
    .transform("count")
)

team_week[
    "other_team_avg_points"
] = (
    (
        team_week[
            "league_total_points"
        ]
        -
        team_week[
            "starter_points"
        ]
    )
    /
    (
        team_week[
            "teams_in_week"
        ]
        - 1
    )
)

team_week["positional_edge"] = (
    team_week["starter_points"]
    -
    team_week["other_team_avg_points"]
)


# ============================================================
# PLAYER-LEVEL POSITIONAL EDGE ATTRIBUTION
#
# Attribute each team-position-week edge back to the players
# who generated that starter production.
#
# When the team-position produced nonzero points, allocate the
# weekly edge in proportion to each player's share of that
# team's starter points.
#
# When the team-position scored exactly zero, allocate the
# negative edge evenly across the occupied starters so the
# attribution still reconciles exactly.
# ============================================================

player_week = skill[
    [
        "year",
        "week",
        "fantasy_team",
        "player",
        "edge_position",
        "fantasy_points",
    ]
].copy()

player_week = player_week.merge(
    team_week[
        [
            "year",
            "week",
            "fantasy_team",
            "edge_position",
            "starter_points",
            "starters_used",
            "other_team_avg_points",
            "positional_edge",
        ]
    ],
    on=[
        "year",
        "week",
        "fantasy_team",
        "edge_position",
    ],
    how="left",
    validate="many_to_one",
)

if player_week[
    "positional_edge"
].isna().any():
    raise RuntimeError(
        "Player attribution failed to match some starter rows "
        "to team-week positional edge."
    )

nonzero_team_points = (
    player_week["starter_points"].abs() > 1e-12
)

player_week[
    "production_share"
] = 0.0

player_week.loc[
    nonzero_team_points,
    "production_share",
] = (
    player_week.loc[
        nonzero_team_points,
        "fantasy_points",
    ]
    /
    player_week.loc[
        nonzero_team_points,
        "starter_points",
    ]
)

zero_team_points = ~nonzero_team_points

player_week.loc[
    zero_team_points,
    "production_share",
] = (
    1.0
    /
    player_week.loc[
        zero_team_points,
        "starters_used",
    ].replace(0, float("nan"))
)

player_week[
    "player_edge_contribution"
] = (
    player_week[
        "positional_edge"
    ]
    *
    player_week[
        "production_share"
    ]
)


# ------------------------------------------------------------
# WEEKLY PLAYER ATTRIBUTION VALIDATION
# ------------------------------------------------------------

player_reconciliation = (
    player_week.groupby(
        [
            "year",
            "week",
            "fantasy_team",
            "edge_position",
        ],
        as_index=False,
    )
    .agg(
        attributed_edge=(
            "player_edge_contribution",
            "sum",
        )
    )
    .merge(
        team_week[
            [
                "year",
                "week",
                "fantasy_team",
                "edge_position",
                "positional_edge",
            ]
        ],
        on=[
            "year",
            "week",
            "fantasy_team",
            "edge_position",
        ],
        how="left",
        validate="one_to_one",
    )
)

player_reconciliation[
    "difference"
] = (
    player_reconciliation[
        "attributed_edge"
    ]
    -
    player_reconciliation[
        "positional_edge"
    ]
)

max_player_reconciliation_error = (
    player_reconciliation[
        "difference"
    ]
    .abs()
    .max()
)

if max_player_reconciliation_error > 1e-8:
    bad = (
        player_reconciliation[
            player_reconciliation[
                "difference"
            ].abs() > 1e-8
        ]
        .head(20)
    )

    print(
        bad.to_string(
            index=False
        )
    )

    raise RuntimeError(
        "Player edge attribution does not reconcile to "
        "team positional edge."
    )


# ------------------------------------------------------------
# PLAYER-SEASON SUMMARY
# ------------------------------------------------------------

player_contributions = (
    player_week.groupby(
        [
            "year",
            "fantasy_team",
            "edge_position",
            "player",
        ],
        as_index=False,
    )
    .agg(
        starts=(
            "week",
            "count",
        ),
        starter_points=(
            "fantasy_points",
            "sum",
        ),
        player_edge_contribution=(
            "player_edge_contribution",
            "sum",
        ),
    )
)

team_position_season_totals = (
    player_contributions.groupby(
        [
            "year",
            "fantasy_team",
            "edge_position",
        ]
    )[
        [
            "starter_points",
            "player_edge_contribution",
        ]
    ]
    .transform("sum")
)

player_contributions[
    "team_position_points"
] = (
    team_position_season_totals[
        "starter_points"
    ]
)

player_contributions[
    "team_positional_edge"
] = (
    team_position_season_totals[
        "player_edge_contribution"
    ]
)

player_contributions[
    "share_of_position_points"
] = (
    player_contributions[
        "starter_points"
    ]
    /
    player_contributions[
        "team_position_points"
    ].replace(
        0,
        float("nan"),
    )
)

player_contributions[
    "edge_contribution_per_start"
] = (
    player_contributions[
        "player_edge_contribution"
    ]
    /
    player_contributions[
        "starts"
    ]
)

player_contributions = (
    player_contributions.sort_values(
        [
            "year",
            "fantasy_team",
            "edge_position",
            "player_edge_contribution",
        ],
        ascending=[
            True,
            True,
            True,
            False,
        ],
    )
    .reset_index(
        drop=True
    )
)


# ------------------------------------------------------------
# SEASON PLAYER ATTRIBUTION VALIDATION
# ------------------------------------------------------------

season_player_check = (
    player_contributions.groupby(
        [
            "year",
            "fantasy_team",
            "edge_position",
        ],
        as_index=False,
    )[
        "player_edge_contribution"
    ]
    .sum()
    .merge(
        team_week.groupby(
            [
                "year",
                "fantasy_team",
                "edge_position",
            ],
            as_index=False,
        )[
            "positional_edge"
        ]
        .sum(),
        on=[
            "year",
            "fantasy_team",
            "edge_position",
        ],
        how="left",
        validate="one_to_one",
        suffixes=(
            "_players",
            "_team",
        ),
    )
)

season_player_check[
    "difference"
] = (
    season_player_check[
        "player_edge_contribution"
    ]
    -
    season_player_check[
        "positional_edge"
    ]
)

max_season_player_error = (
    season_player_check[
        "difference"
    ]
    .abs()
    .max()
)

if max_season_player_error > 1e-8:
    raise RuntimeError(
        "Season player attribution does not reconcile to "
        "season positional edge."
    )


# ============================================================
# WEEKLY VALIDATION
#
# Because every team is compared to the other teams rather
# than an inclusive mean, the edges still sum to zero apart
# from floating-point noise.
# ============================================================

weekly_balance = (
    team_week.groupby(
        group_cols
    )[
        "positional_edge"
    ]
    .sum()
    .abs()
)

max_weekly_imbalance = (
    weekly_balance.max()
)

if max_weekly_imbalance > 1e-8:
    raise RuntimeError(
        "Weekly positional edges do not balance. "
        f"Max imbalance: {max_weekly_imbalance}"
    )


# ============================================================
# SEASON SUMMARY
# ============================================================

season_long = (
    team_week.groupby(
        [
            "year",
            "fantasy_team",
            "edge_position",
        ],
        as_index=False,
    )
    .agg(
        starter_points=(
            "starter_points",
            "sum",
        ),
        positional_edge=(
            "positional_edge",
            "sum",
        ),
        weeks=(
            "week",
            "nunique",
        ),
    )
)

season_long[
    "edge_per_week"
] = (
    season_long[
        "positional_edge"
    ]
    /
    season_long[
        "weeks"
    ]
)

season_long[
    "position_rank"
] = (
    season_long.groupby(
        [
            "year",
            "edge_position",
        ]
    )[
        "positional_edge"
    ]
    .rank(
        method="min",
        ascending=False,
    )
)


# ============================================================
# WIDE SEASON TABLE
# ============================================================

edge_wide = (
    season_long.pivot(
        index=[
            "year",
            "fantasy_team",
        ],
        columns="edge_position",
        values="positional_edge",
    )
    .reset_index()
)

edge_wide.columns.name = None

edge_wide = edge_wide.rename(
    columns={
        "QB": "qb_edge",
        "RB": "rb_edge",
        "WR": "wr_edge",
        "TE": "te_edge",
    }
)

points_wide = (
    season_long.pivot(
        index=[
            "year",
            "fantasy_team",
        ],
        columns="edge_position",
        values="starter_points",
    )
    .reset_index()
)

points_wide.columns.name = None

points_wide = points_wide.rename(
    columns={
        "QB": "qb_points",
        "RB": "rb_points",
        "WR": "wr_points",
        "TE": "te_points",
    }
)

season = edge_wide.merge(
    points_wide,
    on=[
        "year",
        "fantasy_team",
    ],
    how="left",
)

edge_cols = [
    "qb_edge",
    "rb_edge",
    "wr_edge",
    "te_edge",
]

season[
    "total_positional_edge"
] = (
    season[edge_cols]
    .sum(axis=1)
)

season[
    "best_position"
] = (
    season[edge_cols]
    .idxmax(axis=1)
    .str.replace(
        "_edge",
        "",
        regex=False,
    )
    .str.upper()
)

season[
    "worst_position"
] = (
    season[edge_cols]
    .idxmin(axis=1)
    .str.replace(
        "_edge",
        "",
        regex=False,
    )
    .str.upper()
)

season[
    "overall_edge_rank"
] = (
    season.groupby("year")[
        "total_positional_edge"
    ]
    .rank(
        method="min",
        ascending=False,
    )
)


# ============================================================
# FRANCHISE SUMMARY
#
# Sum edge = cumulative historical advantage.
# Edge/week gives fair rate comparison for franchises with
# different numbers of seasons.
# ============================================================

franchise_long = (
    season_long.groupby(
        [
            "fantasy_team",
            "edge_position",
        ],
        as_index=False,
    )
    .agg(
        seasons=(
            "year",
            "nunique",
        ),
        weeks=(
            "weeks",
            "sum",
        ),
        starter_points=(
            "starter_points",
            "sum",
        ),
        positional_edge=(
            "positional_edge",
            "sum",
        ),
    )
)

franchise_long[
    "edge_per_week"
] = (
    franchise_long[
        "positional_edge"
    ]
    /
    franchise_long[
        "weeks"
    ]
)

franchise_long[
    "all_time_position_rank"
] = (
    franchise_long.groupby(
        "edge_position"
    )[
        "edge_per_week"
    ]
    .rank(
        method="min",
        ascending=False,
    )
)

franchise_wide = (
    franchise_long.pivot(
        index="fantasy_team",
        columns="edge_position",
        values="edge_per_week",
    )
    .reset_index()
)

franchise_wide.columns.name = None

franchise_wide = (
    franchise_wide.rename(
        columns={
            "QB": "qb_edge_per_week",
            "RB": "rb_edge_per_week",
            "WR": "wr_edge_per_week",
            "TE": "te_edge_per_week",
        }
    )
)

season_counts = (
    season.groupby(
        "fantasy_team"
    )[
        "year"
    ]
    .nunique()
    .rename("seasons")
)

week_counts = (
    team_weeks.groupby(
        "fantasy_team"
    )
    .size()
    .rename("weeks")
)

franchise = (
    franchise_wide
    .merge(
        season_counts,
        on="fantasy_team",
        how="left",
    )
    .merge(
        week_counts,
        on="fantasy_team",
        how="left",
    )
)

rate_cols = [
    "qb_edge_per_week",
    "rb_edge_per_week",
    "wr_edge_per_week",
    "te_edge_per_week",
]

franchise[
    "total_edge_per_week"
] = (
    franchise[rate_cols]
    .sum(axis=1)
)

franchise[
    "strongest_position"
] = (
    franchise[rate_cols]
    .idxmax(axis=1)
    .str.replace(
        "_edge_per_week",
        "",
        regex=False,
    )
    .str.upper()
)

franchise[
    "weakest_position"
] = (
    franchise[rate_cols]
    .idxmin(axis=1)
    .str.replace(
        "_edge_per_week",
        "",
        regex=False,
    )
    .str.upper()
)

franchise[
    "overall_rank"
] = (
    franchise[
        "total_edge_per_week"
    ]
    .rank(
        method="min",
        ascending=False,
    )
)

franchise = franchise.sort_values(
    "overall_rank"
)


# ============================================================
# EXTREMES
# ============================================================

best = (
    season_long.sort_values(
        "positional_edge",
        ascending=False,
    )
    .head(25)
    .copy()
)

best["extreme_type"] = (
    "Best Positional Season"
)

worst = (
    season_long.sort_values(
        "positional_edge",
        ascending=True,
    )
    .head(25)
    .copy()
)

worst["extreme_type"] = (
    "Worst Positional Season"
)

extremes = pd.concat(
    [
        best,
        worst,
    ],
    ignore_index=True,
)


# ============================================================
# FINAL VALIDATION
# ============================================================

if len(team_weeks) != 1464:
    raise RuntimeError(
        f"Expected 1,464 team-weeks, "
        f"found {len(team_weeks):,}"
    )

if len(team_week) != 1464 * 4:
    raise RuntimeError(
        f"Expected {1464 * 4:,} team-week-position rows, "
        f"found {len(team_week):,}"
    )

if len(season) != 108:
    raise RuntimeError(
        f"Expected 108 team-seasons, "
        f"found {len(season):,}"
    )

season_counts_check = (
    season.groupby("year")
    .size()
)

if not (
    season_counts_check == 12
).all():
    raise RuntimeError(
        "Expected 12 teams in every season."
    )


# ============================================================
# SAVE
# ============================================================

team_week.to_csv(
    TEAM_WEEK_OUT,
    index=False,
)

season.to_csv(
    SEASON_OUT,
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

player_contributions.to_csv(
    PLAYER_OUT,
    index=False,
)


# ============================================================
# REPORT
# ============================================================

print()
print("=" * 100)
print("POSITIONAL EDGE")
print("=" * 100)

print(
    "Team-weeks:",
    len(team_weeks),
)

print(
    "Team-week-position rows:",
    len(team_week),
)

print(
    "Team-seasons:",
    len(season),
)

print(
    "Max weekly balance error:",
    f"{max_weekly_imbalance:.12f}",
)

print()
print("=" * 100)
print("ALL-TIME OVERALL POSITIONAL EDGE")
print("=" * 100)

print(
    franchise[
        [
            "overall_rank",
            "fantasy_team",
            "seasons",
            "weeks",
            "total_edge_per_week",
            "qb_edge_per_week",
            "rb_edge_per_week",
            "wr_edge_per_week",
            "te_edge_per_week",
            "strongest_position",
            "weakest_position",
        ]
    ]
    .round(3)
    .to_string(index=False)
)

print()
print("=" * 100)
print("ALL-TIME POSITION LEADERS")
print("=" * 100)

for position in POSITIONS:

    temp = (
        franchise_long[
            franchise_long[
                "edge_position"
            ] == position
        ]
        .sort_values(
            "edge_per_week",
            ascending=False,
        )
        .head(10)
    )

    print()
    print(position)
    print("-" * 60)

    print(
        temp[
            [
                "fantasy_team",
                "seasons",
                "weeks",
                "positional_edge",
                "edge_per_week",
                "all_time_position_rank",
            ]
        ]
        .round(3)
        .to_string(index=False)
    )

print()
print("=" * 100)
print("BEST POSITIONAL SEASONS")
print("=" * 100)

print(
    season_long[
        [
            "year",
            "fantasy_team",
            "edge_position",
            "starter_points",
            "positional_edge",
            "edge_per_week",
            "position_rank",
        ]
    ]
    .sort_values(
        "positional_edge",
        ascending=False,
    )
    .head(20)
    .round(2)
    .to_string(index=False)
)

print()
print("=" * 100)
print("WORST POSITIONAL SEASONS")
print("=" * 100)

print(
    season_long[
        [
            "year",
            "fantasy_team",
            "edge_position",
            "starter_points",
            "positional_edge",
            "edge_per_week",
            "position_rank",
        ]
    ]
    .sort_values(
        "positional_edge"
    )
    .head(20)
    .round(2)
    .to_string(index=False)
)

print()
print("=" * 100)
print()
print("=" * 100)
print("PLAYER EDGE ATTRIBUTION")
print("=" * 100)

print(
    f"Player-season-position rows: "
    f"{len(player_contributions):,}"
)

print(
    f"Max weekly reconciliation error: "
    f"{max_player_reconciliation_error:.12f}"
)

print(
    f"Max season reconciliation error: "
    f"{max_season_player_error:.12f}"
)

print()
print("Top positive player-season contributions:")
print(
    player_contributions[
        [
            "year",
            "fantasy_team",
            "edge_position",
            "player",
            "starts",
            "starter_points",
            "player_edge_contribution",
        ]
    ]
    .sort_values(
        "player_edge_contribution",
        ascending=False,
    )
    .head(15)
    .round(2)
    .to_string(
        index=False
    )
)

print()
print("Top negative player-season contributions:")
print(
    player_contributions[
        [
            "year",
            "fantasy_team",
            "edge_position",
            "player",
            "starts",
            "starter_points",
            "player_edge_contribution",
        ]
    ]
    .sort_values(
        "player_edge_contribution",
        ascending=True,
    )
    .head(15)
    .round(2)
    .to_string(
        index=False
    )
)

print()
print("=" * 100)
print("OUTPUTS")
print("=" * 100)

for path in [
    TEAM_WEEK_OUT,
    SEASON_OUT,
    FRANCHISE_OUT,
    EXTREMES_OUT,
    PLAYER_OUT,
]:
    print(path)

print()
print("PASS — POSITIONAL EDGE BUILT")
