from pathlib import Path
import re

import numpy as np
import pandas as pd

from team_aliases import canonical_team


# ============================================================
# PATHS
# ============================================================

LINEUP_DIR = Path(
    "data/matchups/player_week_stats"
)

NFL_TEAM_FILE = Path(
    "data/nfl/player_week_teams.csv"
)

OUTPUT_DIR = Path(
    "data/analysis"
)

DETAIL_FILE = (
    OUTPUT_DIR / "qb_wr_stacks.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "qb_wr_stack_summary.csv"
)

TEAM_SEASON_FILE = (
    OUTPUT_DIR / "qb_wr_stack_team_season.csv"
)

WITHIN_SUMMARY_FILE = (
    OUTPUT_DIR / "qb_wr_stack_within_summary.csv"
)

SEASON_RESULTS_FILE = (
    OUTPUT_DIR / "qb_wr_stack_by_season.csv"
)

FRANCHISE_RESULTS_FILE = (
    OUTPUT_DIR / "qb_wr_stack_by_franchise.csv"
)

PAIR_RESULTS_FILE = (
    OUTPUT_DIR / "qb_wr_stack_pairs.csv"
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
# LOAD DATA
# ============================================================

print("=" * 80)
print("BUILDING QB/WR STACK ANALYSIS")
print("=" * 80)

lineup_file = find_lineup_master()

print()
print(
    "Lineup source:",
    lineup_file,
)

print(
    "NFL team source:",
    NFL_TEAM_FILE,
)


lineups = pd.read_csv(
    lineup_file
)

nfl = pd.read_csv(
    NFL_TEAM_FILE
)


# ============================================================
# BASIC CLEANUP
# ============================================================

for column in [
    "year",
    "week",
]:

    lineups[column] = pd.to_numeric(
        lineups[column],
        errors="coerce",
    )

    nfl[column] = pd.to_numeric(
        nfl[column],
        errors="coerce",
    )


lineups["fantasy_points"] = pd.to_numeric(
    lineups["fantasy_points"],
    errors="coerce",
)

lineups["team_score"] = pd.to_numeric(
    lineups["team_score"],
    errors="coerce",
)

lineups["opponent_score"] = pd.to_numeric(
    lineups["opponent_score"],
    errors="coerce",
)


# ============================================================
# JOIN NFL TEAM/POSITION TO EVERY LINEUP ROW
# ============================================================

nfl_lookup = (
    nfl[
        [
            "year",
            "week",
            "player",
            "nfl_name",
            "nfl_team",
            "nfl_position",
            "gsis_id",
            "yahoo_id",
            "match_method",
        ]
    ]
    .drop_duplicates(
        [
            "year",
            "week",
            "player",
        ]
    )
)


players = lineups.merge(
    nfl_lookup,
    on=[
        "year",
        "week",
        "player",
    ],
    how="left",
)


# ============================================================
# STARTERS
# ============================================================

starters = players[
    players["is_starter"].eq(True)
].copy()


# IMPORTANT:
#
# We use nfl_position when available.
#
# This means a WR started in FLEX still counts as a WR,
# which is exactly what we want for stack analysis.

starters["analysis_position"] = (
    starters["nfl_position"]
    .fillna(
        starters["player_position"]
    )
)


# ============================================================
# QB / WR STARTERS
# ============================================================

# ============================================================
# TRUE STARTING QB
# ============================================================
#
# QB is defined by the Yahoo lineup slot, NOT merely by
# nflverse position.
#
# This prevents special-eligibility players such as
# Taysom Hill, Kendall Hinton, or Ryan Griffin from being
# treated as a second starting quarterback when they were
# actually started at another fantasy position.
#

qbs = starters[
    starters["lineup_slot"]
    .astype(str)
    .str.upper()
    .eq("QB")
].copy()


# ============================================================
# STARTING WRS
# ============================================================
#
# WR is intentionally defined by nflverse position when
# available. This allows a true NFL WR started in FLEX to
# count toward a QB/WR stack.
#

wrs = starters[
    starters["analysis_position"]
    .eq("WR")
].copy()


# ============================================================
# VALIDATE QB COVERAGE
# ============================================================

qb_missing = qbs[
    qbs["nfl_team"].isna()
]

wr_missing = wrs[
    wrs["nfl_team"].isna()
]


print()
print("=" * 80)
print("NFL TEAM COVERAGE")
print("=" * 80)

print(
    f"Starting QB rows: {len(qbs):,}"
)

print(
    f"QB missing NFL team: "
    f"{len(qb_missing):,}"
)

print(
    f"Starting WR rows: {len(wrs):,}"
)

print(
    f"WR missing NFL team: "
    f"{len(wr_missing):,}"
)


if len(qb_missing) > 0:

    raise RuntimeError(
        "Starting QB NFL-team coverage "
        "is incomplete."
    )


if len(wr_missing) > 0:

    raise RuntimeError(
        "Starting WR NFL-team coverage "
        "is incomplete."
    )


# ============================================================
# TEAM-WEEK BASE
# ============================================================

#
# Every fantasy team should have one team_score and
# opponent_score for the week. We collapse repeated player
# rows down to one fantasy-team/week.
#

team_weeks = (
    lineups[
        [
            "year",
            "week",
            "fantasy_team",
            "opponent",
            "team_score",
            "opponent_score",
        ]
    ]
    .drop_duplicates()
)


# Safety check for accidental duplicate score records.

duplicate_team_weeks = (
    team_weeks
    .groupby(
        [
            "year",
            "week",
            "fantasy_team",
        ]
    )
    .size()
)

duplicate_team_weeks = (
    duplicate_team_weeks[
        duplicate_team_weeks > 1
    ]
)

if not duplicate_team_weeks.empty:

    print()
    print(
        "WARNING: duplicate team-week "
        "score records detected:"
    )

    print(
        duplicate_team_weeks
        .head(20)
        .to_string()
    )


team_weeks = (
    team_weeks
    .sort_values(
        [
            "year",
            "week",
            "fantasy_team",
        ]
    )
    .drop_duplicates(
        [
            "year",
            "week",
            "fantasy_team",
        ]
    )
)


# ============================================================
# GAME RESULT
# ============================================================

team_weeks["margin"] = (
    team_weeks["team_score"]
    - team_weeks["opponent_score"]
)


team_weeks["result"] = np.select(
    [
        team_weeks["margin"] > 0,
        team_weeks["margin"] < 0,
    ],
    [
        "W",
        "L",
    ],
    default="T",
)


team_weeks["win"] = (
    team_weeks["result"]
    .eq("W")
    .astype(int)
)


# ============================================================
# QB INFORMATION BY TEAM-WEEK
# ============================================================

#
# In a normal lineup there should be exactly one starting QB.
# We still aggregate safely instead of assuming.
#

qb_info = (
    qbs
    .groupby(
        [
            "year",
            "week",
            "fantasy_team",
        ],
        as_index=False,
    )
    .agg(
        starting_qb=(
            "player",
            lambda x:
                " | ".join(
                    sorted(
                        set(
                            x.dropna()
                            .astype(str)
                        )
                    )
                ),
        ),
        qb_nfl_team=(
            "nfl_team",
            lambda x:
                " | ".join(
                    sorted(
                        set(
                            x.dropna()
                            .astype(str)
                        )
                    )
                ),
        ),
        qb_points=(
            "fantasy_points",
            "sum",
        ),
        starting_qb_count=(
            "player",
            "nunique",
        ),
    )
)


# ============================================================
# WR INFORMATION BY TEAM-WEEK
# ============================================================

wr_info = (
    wrs
    .groupby(
        [
            "year",
            "week",
            "fantasy_team",
        ],
        as_index=False,
    )
    .agg(
        starting_wrs=(
            "player",
            lambda x:
                " | ".join(
                    sorted(
                        set(
                            x.dropna()
                            .astype(str)
                        )
                    )
                ),
        ),
        starting_wr_count=(
            "player",
            "nunique",
        ),
        starting_wr_points=(
            "fantasy_points",
            "sum",
        ),
    )
)


# ============================================================
# FIND ACTUAL QB/WR STACK PAIRS
# ============================================================

#
# Join each starting QB to every starting WR on that same
# fantasy team/week, then compare their NFL teams.
#

pairs = qbs[
    [
        "year",
        "week",
        "fantasy_team",
        "player",
        "nfl_team",
        "fantasy_points",
    ]
].rename(
    columns={
        "player": "qb",
        "nfl_team": "qb_nfl_team",
        "fantasy_points":
            "qb_fantasy_points",
    }
)


wr_pairs = wrs[
    [
        "year",
        "week",
        "fantasy_team",
        "player",
        "nfl_team",
        "fantasy_points",
        "lineup_slot",
    ]
].rename(
    columns={
        "player": "wr",
        "nfl_team": "wr_nfl_team",
        "fantasy_points":
            "wr_fantasy_points",
        "lineup_slot":
            "wr_lineup_slot",
    }
)


pairs = pairs.merge(
    wr_pairs,
    on=[
        "year",
        "week",
        "fantasy_team",
    ],
    how="inner",
)


pairs["is_stack_pair"] = (
    pairs["qb_nfl_team"]
    .eq(
        pairs["wr_nfl_team"]
    )
)


stack_pairs = pairs[
    pairs["is_stack_pair"]
].copy()


# ============================================================
# STACK DETAILS BY TEAM-WEEK
# ============================================================

if not stack_pairs.empty:

    stack_pairs["stack_pair"] = (
        stack_pairs["qb"]
        + " + "
        + stack_pairs["wr"]
    )


    stack_info = (
        stack_pairs
        .groupby(
            [
                "year",
                "week",
                "fantasy_team",
            ],
            as_index=False,
        )
        .agg(
            stack_pairs=(
                "stack_pair",
                lambda x:
                    " | ".join(
                        sorted(
                            set(
                                x.dropna()
                                .astype(str)
                            )
                        )
                    ),
            ),
            stack_nfl_teams=(
                "qb_nfl_team",
                lambda x:
                    " | ".join(
                        sorted(
                            set(
                                x.dropna()
                                .astype(str)
                            )
                        )
                    ),
            ),
            stacked_wr_count=(
                "wr",
                "nunique",
            ),
            stacked_wr_points=(
                "wr_fantasy_points",
                "sum",
            ),
        )
    )

else:

    stack_info = pd.DataFrame(
        columns=[
            "year",
            "week",
            "fantasy_team",
            "stack_pairs",
            "stack_nfl_teams",
            "stacked_wr_count",
            "stacked_wr_points",
        ]
    )


# ============================================================
# COMBINE TEAM-WEEK DATA
# ============================================================

analysis = (
    team_weeks
    .merge(
        qb_info,
        on=[
            "year",
            "week",
            "fantasy_team",
        ],
        how="left",
    )
    .merge(
        wr_info,
        on=[
            "year",
            "week",
            "fantasy_team",
        ],
        how="left",
    )
    .merge(
        stack_info,
        on=[
            "year",
            "week",
            "fantasy_team",
        ],
        how="left",
    )
)


analysis["has_qb_wr_stack"] = (
    analysis["stacked_wr_count"]
    .fillna(0)
    .gt(0)
)


analysis["stacked_wr_count"] = (
    analysis["stacked_wr_count"]
    .fillna(0)
    .astype(int)
)


analysis["stacked_wr_points"] = (
    analysis["stacked_wr_points"]
    .fillna(0)
)


analysis["stack_pairs"] = (
    analysis["stack_pairs"]
    .fillna("")
)


analysis["stack_nfl_teams"] = (
    analysis["stack_nfl_teams"]
    .fillna("")
)


# ============================================================
# TEAM BASELINE
# ============================================================

#
# Compare each team-week to that fantasy franchise's
# average score across the entire historical dataset.
#
# This gives us a simple control for naturally stronger
# fantasy teams.
#

team_baseline = (
    analysis
    .groupby(
        "fantasy_team",
        as_index=False,
    )
    .agg(
        team_avg_score=(
            "team_score",
            "mean",
        )
    )
)


analysis = analysis.merge(
    team_baseline,
    on="fantasy_team",
    how="left",
)


analysis[
    "score_vs_team_average"
] = (
    analysis["team_score"]
    - analysis["team_avg_score"]
)


# ============================================================
# SEASON-TEAM BASELINE
# ============================================================

#
# This is even more useful because fantasy teams change
# strength dramatically from season to season.
#

season_team_baseline = (
    analysis
    .groupby(
        [
            "year",
            "fantasy_team",
        ],
        as_index=False,
    )
    .agg(
        season_team_avg_score=(
            "team_score",
            "mean",
        )
    )
)


analysis = analysis.merge(
    season_team_baseline,
    on=[
        "year",
        "fantasy_team",
    ],
    how="left",
)


analysis[
    "score_vs_season_team_average"
] = (
    analysis["team_score"]
    - analysis[
        "season_team_avg_score"
    ]
)


# ============================================================
# HIGH-SCORE FLAGS
# ============================================================

#
# Top 25% score within each season.
# Useful as a simple ceiling metric.
#

analysis[
    "season_score_percentile"
] = (
    analysis
    .groupby("year")[
        "team_score"
    ]
    .rank(
        pct=True,
        method="average",
    )
)


analysis[
    "top_quartile_score"
] = (
    analysis[
        "season_score_percentile"
    ] >= 0.75
)


# ============================================================
# ORDER OUTPUT
# ============================================================

analysis = (
    analysis
    .sort_values(
        [
            "year",
            "week",
            "fantasy_team",
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# OVERALL SUMMARY
# ============================================================

summary = (
    analysis
    .groupby(
        "has_qb_wr_stack",
        as_index=False,
    )
    .agg(
        team_weeks=(
            "fantasy_team",
            "size",
        ),
        wins=(
            "win",
            "sum",
        ),
        win_rate=(
            "win",
            "mean",
        ),
        avg_score=(
            "team_score",
            "mean",
        ),
        median_score=(
            "team_score",
            "median",
        ),
        avg_margin=(
            "margin",
            "mean",
        ),
        avg_vs_team_baseline=(
            "score_vs_team_average",
            "mean",
        ),
        avg_vs_season_team_baseline=(
            "score_vs_season_team_average",
            "mean",
        ),
        top_quartile_rate=(
            "top_quartile_score",
            "mean",
        ),
    )
)


summary[
    "stack_status"
] = np.where(
    summary["has_qb_wr_stack"],
    "QB/WR Stack",
    "No QB/WR Stack",
)


summary = summary[
    [
        "stack_status",
        "team_weeks",
        "wins",
        "win_rate",
        "avg_score",
        "median_score",
        "avg_margin",
        "avg_vs_team_baseline",
        "avg_vs_season_team_baseline",
        "top_quartile_rate",
    ]
]



# ============================================================
# CANONICAL FANTASY FRANCHISE
# ============================================================
#
# Historical fantasy-team names are rolled into the
# franchise's current/final canonical name using the same
# alias system used elsewhere on the website.
#

analysis["canonical_team"] = (
    analysis["fantasy_team"]
    .apply(canonical_team)
)


# ============================================================
# WITHIN TEAM-SEASON COMPARISON
# ============================================================
#
# This is our most useful apples-to-apples comparison.
#
# Only include fantasy team-seasons that had BOTH:
#   - at least one stack week
#   - at least one non-stack week
#
# We then calculate how that same team performed when
# stacking versus when it did not stack.
#

comparison_rows = []

for (
    year,
    fantasy_team,
), group in analysis.groupby(
    [
        "year",
        "fantasy_team",
    ]
):

    stacked = group[
        group["has_qb_wr_stack"]
    ]

    nonstacked = group[
        ~group["has_qb_wr_stack"]
    ]

    if (
        stacked.empty
        or nonstacked.empty
    ):
        continue

    comparison_rows.append(
        {
            "year": int(year),
            "fantasy_team":
                fantasy_team,

            "stack_weeks":
                len(stacked),

            "nonstack_weeks":
                len(nonstacked),

            "stack_avg_score":
                stacked[
                    "team_score"
                ].mean(),

            "nonstack_avg_score":
                nonstacked[
                    "team_score"
                ].mean(),

            "score_difference":
                stacked[
                    "team_score"
                ].mean()
                -
                nonstacked[
                    "team_score"
                ].mean(),

            "stack_win_rate":
                stacked[
                    "win"
                ].mean(),

            "nonstack_win_rate":
                nonstacked[
                    "win"
                ].mean(),

            "win_rate_difference":
                stacked[
                    "win"
                ].mean()
                -
                nonstacked[
                    "win"
                ].mean(),

            "stack_avg_margin":
                stacked[
                    "margin"
                ].mean(),

            "nonstack_avg_margin":
                nonstacked[
                    "margin"
                ].mean(),

            "margin_difference":
                stacked[
                    "margin"
                ].mean()
                -
                nonstacked[
                    "margin"
                ].mean(),

            "stack_top_quartile_rate":
                stacked[
                    "top_quartile_score"
                ].mean(),

            "nonstack_top_quartile_rate":
                nonstacked[
                    "top_quartile_score"
                ].mean(),

            "top_quartile_difference":
                stacked[
                    "top_quartile_score"
                ].mean()
                -
                nonstacked[
                    "top_quartile_score"
                ].mean(),
        }
    )


team_season_comparison = pd.DataFrame(
    comparison_rows
)


# ============================================================
# AGGREGATE WITHIN TEAM-SEASON RESULT
# ============================================================

if not team_season_comparison.empty:

    within_summary = pd.DataFrame(
        [
            {
                "team_seasons":
                    len(
                        team_season_comparison
                    ),

                "stack_weeks":
                    team_season_comparison[
                        "stack_weeks"
                    ].sum(),

                "nonstack_weeks":
                    team_season_comparison[
                        "nonstack_weeks"
                    ].sum(),

                # Each team-season gets equal weight.
                "mean_team_season_score_difference":
                    team_season_comparison[
                        "score_difference"
                    ].mean(),

                "median_team_season_score_difference":
                    team_season_comparison[
                        "score_difference"
                    ].median(),

                "team_seasons_stack_scored_more":
                    (
                        team_season_comparison[
                            "score_difference"
                        ] > 0
                    ).sum(),

                "pct_team_seasons_stack_scored_more":
                    (
                        team_season_comparison[
                            "score_difference"
                        ] > 0
                    ).mean(),

                "mean_team_season_win_rate_difference":
                    team_season_comparison[
                        "win_rate_difference"
                    ].mean(),

                "mean_team_season_margin_difference":
                    team_season_comparison[
                        "margin_difference"
                    ].mean(),

                "mean_team_season_top_quartile_difference":
                    team_season_comparison[
                        "top_quartile_difference"
                    ].mean(),
            }
        ]
    )

else:

    within_summary = pd.DataFrame()


# ============================================================
# RESULTS BY SEASON
# ============================================================

season_results = (
    analysis
    .groupby(
        [
            "year",
            "has_qb_wr_stack",
        ],
        as_index=False,
    )
    .agg(
        team_weeks=(
            "fantasy_team",
            "size",
        ),
        win_rate=(
            "win",
            "mean",
        ),
        avg_score=(
            "team_score",
            "mean",
        ),
        median_score=(
            "team_score",
            "median",
        ),
        avg_margin=(
            "margin",
            "mean",
        ),
        top_quartile_rate=(
            "top_quartile_score",
            "mean",
        ),
    )
)


season_results[
    "stack_status"
] = np.where(
    season_results[
        "has_qb_wr_stack"
    ],
    "QB/WR Stack",
    "No QB/WR Stack",
)


# ============================================================
# FANTASY FRANCHISE STACK RESULTS
# ============================================================
#
# This currently uses the fantasy_team name stored in the
# historical lineup master. Franchise alias consolidation
# can be layered on separately.
#

franchise_stack_results = (
    analysis[
        analysis[
            "has_qb_wr_stack"
        ]
    ]
    .groupby(
        "canonical_team",
        as_index=False,
    )
    .agg(
        stack_weeks=(
            "canonical_team",
            "size",
        ),
        stack_wins=(
            "win",
            "sum",
        ),
        stack_win_rate=(
            "win",
            "mean",
        ),
        stack_avg_score=(
            "team_score",
            "mean",
        ),
        stack_avg_margin=(
            "margin",
            "mean",
        ),
        stack_top_quartile_rate=(
            "top_quartile_score",
            "mean",
        ),
    )
    .sort_values(
        [
            "stack_weeks",
            "stack_avg_score",
        ],
        ascending=[
            False,
            False,
        ],
    )
)


# Add total historical team-weeks so stack usage can be
# compared fairly across franchises.

franchise_totals = (
    analysis
    .groupby(
        "canonical_team",
        as_index=False,
    )
    .agg(
        total_team_weeks=(
            "canonical_team",
            "size",
        )
    )
)

franchise_stack_results = (
    franchise_stack_results
    .merge(
        franchise_totals,
        on="canonical_team",
        how="left",
    )
)

franchise_stack_results[
    "stack_rate"
] = (
    franchise_stack_results[
        "stack_weeks"
    ]
    /
    franchise_stack_results[
        "total_team_weeks"
    ]
)


# ============================================================
# INDIVIDUAL QB/WR STACK PAIR PERFORMANCE
# ============================================================

if not stack_pairs.empty:

    pair_week_results = (
        stack_pairs
        .merge(
            analysis[
                [
                    "year",
                    "week",
                    "fantasy_team",
                    "team_score",
                    "opponent_score",
                    "margin",
                    "win",
                    "top_quartile_score",
                ]
            ],
            on=[
                "year",
                "week",
                "fantasy_team",
            ],
            how="left",
        )
    )


    pair_results = (
        pair_week_results
        .groupby(
            [
                "qb",
                "wr",
                "qb_nfl_team",
            ],
            as_index=False,
        )
        .agg(
            stack_weeks=(
                "week",
                "size",
            ),
            wins=(
                "win",
                "sum",
            ),
            win_rate=(
                "win",
                "mean",
            ),
            avg_team_score=(
                "team_score",
                "mean",
            ),
            avg_margin=(
                "margin",
                "mean",
            ),
            top_quartile_rate=(
                "top_quartile_score",
                "mean",
            ),
            avg_qb_points=(
                "qb_fantasy_points",
                "mean",
            ),
            avg_wr_points=(
                "wr_fantasy_points",
                "mean",
            ),
        )
    )


    pair_results[
        "avg_stack_player_points"
    ] = (
        pair_results[
            "avg_qb_points"
        ]
        +
        pair_results[
            "avg_wr_points"
        ]
    )


    pair_results = (
        pair_results
        .sort_values(
            [
                "stack_weeks",
                "avg_team_score",
            ],
            ascending=[
                False,
                False,
            ],
        )
    )

else:

    pair_results = pd.DataFrame()


# ============================================================
# STACK USAGE BY SEASON
# ============================================================

stack_by_season = (
    analysis
    .groupby(
        "year",
        as_index=False,
    )
    .agg(
        team_weeks=(
            "fantasy_team",
            "size",
        ),
        stack_weeks=(
            "has_qb_wr_stack",
            "sum",
        ),
    )
)


stack_by_season[
    "stack_rate"
] = (
    stack_by_season[
        "stack_weeks"
    ]
    /
    stack_by_season[
        "team_weeks"
    ]
)


# ============================================================
# WRITE OUTPUTS
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


analysis.to_csv(
    DETAIL_FILE,
    index=False,
)


summary.to_csv(
    SUMMARY_FILE,
    index=False,
)

team_season_comparison.to_csv(
    TEAM_SEASON_FILE,
    index=False,
)

within_summary.to_csv(
    WITHIN_SUMMARY_FILE,
    index=False,
)

season_results.to_csv(
    SEASON_RESULTS_FILE,
    index=False,
)

franchise_stack_results.to_csv(
    FRANCHISE_RESULTS_FILE,
    index=False,
)

pair_results.to_csv(
    PAIR_RESULTS_FILE,
    index=False,
)


# ============================================================
# VALIDATION
# ============================================================

print()
print("=" * 80)
print("TEAM-WEEK VALIDATION")
print("=" * 80)

print(
    f"Team-weeks: "
    f"{len(analysis):,}"
)

print(
    f"Years: "
    f"{int(analysis['year'].min())}"
    f"–"
    f"{int(analysis['year'].max())}"
)


expected_team_weeks = (
    analysis[
        [
            "year",
            "week",
            "fantasy_team",
        ]
    ]
    .drop_duplicates()
)

if len(expected_team_weeks) == len(analysis):

    print(
        "PASS — one row per "
        "fantasy team-week."
    )

else:

    print(
        "FAIL — duplicate "
        "fantasy team-weeks."
    )


# ============================================================
# QB VALIDATION
# ============================================================

print()
print("=" * 80)
print("QB VALIDATION")
print("=" * 80)

qb_counts = (
    analysis[
        "starting_qb_count"
    ]
    .value_counts(
        dropna=False
    )
    .sort_index()
)

print(
    qb_counts.to_string()
)


# ============================================================
# STACK RESULTS
# ============================================================

print()
print("=" * 80)
print("QB/WR STACK RESULTS")
print("=" * 80)

display_summary = (
    summary.copy()
)

for column in [
    "win_rate",
    "top_quartile_rate",
]:

    display_summary[column] = (
        display_summary[column]
        * 100
    ).round(2)


for column in [
    "avg_score",
    "median_score",
    "avg_margin",
    "avg_vs_team_baseline",
    "avg_vs_season_team_baseline",
]:

    display_summary[column] = (
        display_summary[column]
        .round(2)
    )


print(
    display_summary
    .to_string(index=False)
)


# ============================================================
# STACK FREQUENCY BY SEASON
# ============================================================

print()
print("=" * 80)
print("STACK FREQUENCY BY SEASON")
print("=" * 80)

season_stack = (
    analysis
    .groupby("year")
    .agg(
        team_weeks=(
            "fantasy_team",
            "size",
        ),
        stack_weeks=(
            "has_qb_wr_stack",
            "sum",
        ),
    )
)

season_stack[
    "stack_rate"
] = (
    season_stack[
        "stack_weeks"
    ]
    / season_stack[
        "team_weeks"
    ]
)


print(
    season_stack.to_string()
)


# ============================================================
# MOST COMMON STACK PAIRS
# ============================================================

print()
print("=" * 80)
print("MOST COMMON QB/WR STACK PAIRS")
print("=" * 80)

if stack_pairs.empty:

    print(
        "No stacks found."
    )

else:

    pair_counts = (
        stack_pairs
        .groupby(
            [
                "qb",
                "wr",
                "qb_nfl_team",
            ]
        )
        .size()
        .reset_index(
            name="weeks"
        )
        .sort_values(
            "weeks",
            ascending=False,
        )
        .head(25)
    )

    print(
        pair_counts.to_string(
            index=False
        )
    )



# ============================================================
# WITHIN TEAM-SEASON RESULTS
# ============================================================

print()
print("=" * 80)
print("WITHIN TEAM-SEASON COMPARISON")
print("=" * 80)

if within_summary.empty:

    print(
        "No qualifying team-seasons."
    )

else:

    r = within_summary.iloc[0]

    print(
        f"Qualifying team-seasons: "
        f"{int(r['team_seasons']):,}"
    )

    print(
        f"Stack weeks: "
        f"{int(r['stack_weeks']):,}"
    )

    print(
        f"Comparable non-stack weeks: "
        f"{int(r['nonstack_weeks']):,}"
    )

    print()

    print(
        "Average scoring difference "
        "(stack - non-stack): "
        f"{r['mean_team_season_score_difference']:+.2f}"
    )

    print(
        "Median scoring difference: "
        f"{r['median_team_season_score_difference']:+.2f}"
    )

    print(
        "Team-seasons where stack weeks "
        "scored more: "
        f"{int(r['team_seasons_stack_scored_more'])}"
        f"/{int(r['team_seasons'])} "
        f"("
        f"{r['pct_team_seasons_stack_scored_more']:.1%}"
        f")"
    )

    print(
        "Average win-rate difference: "
        f"{r['mean_team_season_win_rate_difference']:+.1%}"
    )

    print(
        "Average margin difference: "
        f"{r['mean_team_season_margin_difference']:+.2f}"
    )

    print(
        "Average top-quartile difference: "
        f"{r['mean_team_season_top_quartile_difference']:+.1%}"
    )


print()
print("=" * 80)
print("BEST / WORST TEAM-SEASON STACK EFFECTS")
print("=" * 80)

if not team_season_comparison.empty:

    display_cols = [
        "year",
        "fantasy_team",
        "stack_weeks",
        "nonstack_weeks",
        "stack_avg_score",
        "nonstack_avg_score",
        "score_difference",
    ]

    print()
    print("BEST:")
    print(
        team_season_comparison
        .sort_values(
            "score_difference",
            ascending=False,
        )
        .head(10)[
            display_cols
        ]
        .round(2)
        .to_string(index=False)
    )

    print()
    print("WORST:")
    print(
        team_season_comparison
        .sort_values(
            "score_difference",
            ascending=True,
        )
        .head(10)[
            display_cols
        ]
        .round(2)
        .to_string(index=False)
    )


print()
print("=" * 80)
print("TOP STACK PAIRS BY USAGE")
print("=" * 80)

if pair_results.empty:

    print("No stack pairs.")

else:

    pair_display = (
        pair_results
        .head(20)
        .copy()
    )

    for col in [
        "win_rate",
        "top_quartile_rate",
    ]:
        pair_display[col] = (
            pair_display[col]
            * 100
        ).round(1)

    for col in [
        "avg_team_score",
        "avg_margin",
        "avg_qb_points",
        "avg_wr_points",
        "avg_stack_player_points",
    ]:
        pair_display[col] = (
            pair_display[col]
            .round(2)
        )

    print(
        pair_display.to_string(
            index=False
        )
    )


# ============================================================
# OUTPUTS
# ============================================================

print()
print("=" * 80)
print("OUTPUTS")
print("=" * 80)

print(DETAIL_FILE)
print(SUMMARY_FILE)
print(TEAM_SEASON_FILE)
print(WITHIN_SUMMARY_FILE)
print(SEASON_RESULTS_FILE)
print(FRANCHISE_RESULTS_FILE)
print(PAIR_RESULTS_FILE)

print()
print("Done.")
