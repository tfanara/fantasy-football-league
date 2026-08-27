from __future__ import annotations

from pathlib import Path

import pandas as pd


# =============================================================================
# SETTINGS
# =============================================================================

print()
print("Yahoo weekly lineup validator")
print()

while True:
    raw_year = input("Season to validate (for example 2024): ").strip()
    try:
        YEAR = int(raw_year)
    except ValueError:
        print("Enter a four-digit season such as 2024.")
        continue
    if 2017 <= YEAR <= 2025:
        break
    print("Enter a season from 2017 through 2025.")

REGULAR_SEASON_END = {
    2018: 13,
    2019: 13,
    2020: 13,
    2021: 14,
    2022: 14,
    2023: 14,
    2024: 14,
    2025: 14,
}

EXPECTED_WEEKS = list(
    range(
        1,
        REGULAR_SEASON_END[YEAR] + 1,
    )
)

EXPECTED_TEAMS = 12
EXPECTED_MATCHUPS_PER_WEEK = 6
EXPECTED_STARTERS_PER_TEAM_WEEK = 9

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "matchups" / "player_week_stats"

LINEUPS_FILE = DATA_DIR / f"{YEAR}_weekly_lineups.csv"
MATCHUPS_FILE = DATA_DIR / f"{YEAR}_matchups.csv"


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


def banner(title: str):
    print()
    print("=" * 92)
    print(title)
    print("=" * 92)


def result(status: str, label: str, detail: str = ""):
    suffix = f" — {detail}" if detail else ""
    print(f"[{status}] {label}{suffix}")


# =============================================================================
# LOAD
# =============================================================================

def load_data():
    if not LINEUPS_FILE.exists():
        raise FileNotFoundError(
            f"Missing lineup file: {LINEUPS_FILE}"
        )

    if not MATCHUPS_FILE.exists():
        raise FileNotFoundError(
            f"Missing matchup file: {MATCHUPS_FILE}"
        )

    lineups = pd.read_csv(
        LINEUPS_FILE,
    )

    matchups = pd.read_csv(
        MATCHUPS_FILE,
    )

    return lineups, matchups


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def normalize_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series

    return (
        series
        .astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
            }
        )
        .fillna(False)
        .astype(bool)
    )


def safe_numeric(df: pd.DataFrame, columns: list[str]):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )


def team_week_key_counts(
    lineups: pd.DataFrame,
    mask: pd.Series | None = None,
) -> pd.DataFrame:
    df = lineups.copy()

    if mask is not None:
        df = df[mask].copy()

    return (
        df.groupby(
            ["week", "fantasy_team"],
            dropna=False,
        )
        .size()
        .rename("count")
        .reset_index()
    )


def player_identity_column(lineups: pd.DataFrame) -> str:
    # Current collector uses player names.
    # This helper gives us one place to change later if Yahoo player IDs
    # are added to the collector.
    return "player"


# =============================================================================
# MAIN VALIDATION
# =============================================================================

def main():
    banner("YAHOO WEEKLY LINEUP DATA VALIDATOR")

    print(f"Season: {YEAR}")
    print(f"Lineups:  {LINEUPS_FILE}")
    print(f"Matchups: {MATCHUPS_FILE}")

    lineups, matchups = load_data()

    # Keep only the configured regular-season weeks for this season.
    # This prevents playoff/consolation weeks from contaminating validation.
    lineups = lineups[
        lineups["week"].isin(EXPECTED_WEEKS)
    ].copy()

    matchups = matchups[
        matchups["week"].isin(EXPECTED_WEEKS)
    ].copy()

    # Normalize types.
    safe_numeric(
        lineups,
        [
            "year",
            "week",
            "matchup_number",
            "yahoo_team_id_used",
            "team_score",
            "opponent_score",
            "projected_points",
            "fantasy_points",
        ],
    )

    safe_numeric(
        matchups,
        [
            "year",
            "week",
            "matchup_number",
            "yahoo_team_id_used",
            "left_score",
            "right_score",
            "player_records",
            "roster_tables",
        ],
    )

    for col in [
        "is_starter",
        "is_bench",
        "is_ir",
    ]:
        if col in lineups.columns:
            lineups[col] = normalize_bool(
                lineups[col]
            )

    failures = 0
    warnings = 0

    # -------------------------------------------------------------------------
    # 1. BASIC SHAPE
    # -------------------------------------------------------------------------

    banner("1. BASIC DATASET SHAPE")

    result(
        PASS if len(lineups) > 0 else FAIL,
        "Lineup dataset is non-empty",
        f"{len(lineups):,} rows",
    )

    if len(lineups) == 0:
        failures += 1

    result(
        PASS if len(matchups) > 0 else FAIL,
        "Matchup dataset is non-empty",
        f"{len(matchups):,} rows",
    )

    if len(matchups) == 0:
        failures += 1

    expected_matchups = (
        len(EXPECTED_WEEKS)
        * EXPECTED_MATCHUPS_PER_WEEK
    )

    status = (
        PASS
        if len(matchups) == expected_matchups
        else FAIL
    )

    result(
        status,
        "Season matchup count",
        f"{len(matchups)} found / {expected_matchups} expected",
    )

    if status == FAIL:
        failures += 1

    # -------------------------------------------------------------------------
    # 2. WEEK COVERAGE
    # -------------------------------------------------------------------------

    banner("2. WEEK COVERAGE")

    lineup_weeks = sorted(
        lineups["week"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    matchup_weeks = sorted(
        matchups["week"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    expected_week_set = set(
        EXPECTED_WEEKS
    )

    for label, weeks in [
        ("Lineup weeks", lineup_weeks),
        ("Matchup weeks", matchup_weeks),
    ]:
        status = (
            PASS
            if set(weeks) == expected_week_set
            else FAIL
        )

        result(
            status,
            label,
            f"{weeks}",
        )

        if status == FAIL:
            failures += 1

    # -------------------------------------------------------------------------
    # 3. MATCHUPS PER WEEK
    # -------------------------------------------------------------------------

    banner("3. MATCHUPS PER WEEK")

    matchups_per_week = (
        matchups.groupby("week")
        .size()
    )

    for week in EXPECTED_WEEKS:
        count = int(
            matchups_per_week.get(
                week,
                0,
            )
        )

        status = (
            PASS
            if count == EXPECTED_MATCHUPS_PER_WEEK
            else FAIL
        )

        result(
            status,
            f"Week {week}",
            f"{count} matchups",
        )

        if status == FAIL:
            failures += 1

    # -------------------------------------------------------------------------
    # 4. TEAM COVERAGE PER WEEK
    # -------------------------------------------------------------------------

    banner("4. TEAM COVERAGE PER WEEK")

    matchup_team_rows = pd.concat(
        [
            matchups[
                ["week", "left_team"]
            ].rename(
                columns={
                    "left_team": "team",
                }
            ),
            matchups[
                ["week", "right_team"]
            ].rename(
                columns={
                    "right_team": "team",
                }
            ),
        ],
        ignore_index=True,
    )

    team_counts = (
        matchup_team_rows
        .dropna(subset=["team"])
        .groupby("week")["team"]
        .nunique()
    )

    for week in EXPECTED_WEEKS:
        count = int(
            team_counts.get(
                week,
                0,
            )
        )

        status = (
            PASS
            if count == EXPECTED_TEAMS
            else FAIL
        )

        result(
            status,
            f"Week {week}",
            f"{count} unique teams",
        )

        if status == FAIL:
            failures += 1

    # -------------------------------------------------------------------------
    # 5. STARTER COUNTS
    # -------------------------------------------------------------------------

    banner("5. STARTER COUNTS PER TEAM/WEEK")

    starter_counts = team_week_key_counts(
        lineups,
        lineups["is_starter"],
    )

    bad_starter_counts = starter_counts[
        starter_counts["count"]
        != EXPECTED_STARTERS_PER_TEAM_WEEK
    ]

    if bad_starter_counts.empty:
        result(
            PASS,
            "Every team-week has exactly 9 starters",
            f"{len(starter_counts)} team-week combinations checked",
        )
    else:
        result(
            FAIL,
            "Starter count problems found",
            f"{len(bad_starter_counts)} team-weeks",
        )

        print()
        print(
            bad_starter_counts
            .sort_values(
                ["week", "fantasy_team"]
            )
            .to_string(index=False)
        )

        failures += 1

    expected_team_weeks = (
        len(EXPECTED_WEEKS)
        * EXPECTED_TEAMS
    )

    status = (
        PASS
        if len(starter_counts) == expected_team_weeks
        else FAIL
    )

    result(
        status,
        "Starter team-week coverage",
        f"{len(starter_counts)} found / {expected_team_weeks} expected",
    )

    if status == FAIL:
        failures += 1

    # -------------------------------------------------------------------------
    # 6. LINEUP SLOT INTEGRITY
    # -------------------------------------------------------------------------

    banner("6. LINEUP SLOT INTEGRITY")

    mutually_conflicting = lineups[
        (
            lineups["is_starter"].astype(int)
            + lineups["is_bench"].astype(int)
            + lineups["is_ir"].astype(int)
        )
        > 1
    ]

    if mutually_conflicting.empty:
        result(
            PASS,
            "No row is simultaneously starter/bench/IR",
        )
    else:
        result(
            FAIL,
            "Conflicting lineup classifications",
            f"{len(mutually_conflicting)} rows",
        )
        failures += 1

    unclassified = lineups[
        ~(
            lineups["is_starter"]
            | lineups["is_bench"]
            | lineups["is_ir"]
        )
    ]

    if unclassified.empty:
        result(
            PASS,
            "Every player row is classified",
        )
    else:
        result(
            WARN,
            "Unclassified player rows",
            f"{len(unclassified)} rows",
        )
        warnings += 1

        print()
        print(
            unclassified[
                [
                    "week",
                    "fantasy_team",
                    "player",
                    "lineup_slot",
                ]
            ]
            .head(30)
            .to_string(index=False)
        )

    # -------------------------------------------------------------------------
    # 7. DUPLICATES
    # -------------------------------------------------------------------------

    banner("7. DUPLICATE PLAYER-WEEK RECORDS")

    identity_col = player_identity_column(
        lineups
    )

    duplicate_key = [
        "year",
        "week",
        "fantasy_team",
        identity_col,
        "lineup_slot",
    ]

    duplicate_source = lineups[
        ~(
            lineups[identity_col]
            .astype(str)
            .str.strip()
            .eq("(Empty)")
        )
    ].copy()

    duplicates = duplicate_source[
        duplicate_source.duplicated(
            subset=duplicate_key,
            keep=False,
        )
    ].sort_values(
        duplicate_key
    )

    if duplicates.empty:
        result(
            PASS,
            "No duplicate player/team/week/slot records",
        )
    else:
        result(
            FAIL,
            "Duplicate player records found",
            f"{len(duplicates)} rows involved",
        )

        print()
        print(
            duplicates[
                duplicate_key
                + [
                    "fantasy_points",
                    "matchup_id",
                ]
            ]
            .head(50)
            .to_string(index=False)
        )

        failures += 1

    # -------------------------------------------------------------------------
    # 8. MISSING VALUES
    # -------------------------------------------------------------------------

    banner("8. REQUIRED FIELD COMPLETENESS")

    required_columns = [
        "year",
        "week",
        "matchup_id",
        "fantasy_team",
        "opponent",
        "player",
        "lineup_slot",
        "fantasy_points",
    ]

    for col in required_columns:
        if col not in lineups.columns:
            result(
                FAIL,
                f"Required column missing: {col}",
            )
            failures += 1
            continue

        missing_mask = (
            lineups[col].isna()
            | (
                lineups[col]
                .astype(str)
                .str.strip()
                == ""
            )
        )

        missing = int(
            missing_mask.sum()
        )

        if col == "fantasy_points":
            starter_missing = int(
                (
                    missing_mask
                    & lineups["is_starter"]
                ).sum()
            )

            nonstarter_missing = (
                missing
                - starter_missing
            )

            if starter_missing > 0:
                result(
                    WARN,
                    col,
                    (
                        f"{missing} missing total; {starter_missing} starters. "
                        "These starter blanks are accepted only if the starter-point "
                        "reconciliation check below still matches Yahoo exactly."
                    ),
                )
                warnings += 1

            elif missing > 0:
                result(
                    WARN,
                    col,
                    f"{missing} missing values, all bench/IR/empty slots",
                )
                warnings += 1

            else:
                result(
                    PASS,
                    col,
                    "0 missing values",
                )

            continue

        status = (
            PASS
            if missing == 0
            else WARN
        )

        result(
            status,
            col,
            f"{missing} missing values",
        )

        if status == WARN:
            warnings += 1

    # -------------------------------------------------------------------------
    # 9. STARTER SCORE RECONCILIATION
    # -------------------------------------------------------------------------

    banner("9. STARTER POINTS VS YAHOO TEAM SCORE")

    starters = lineups[
        lineups["is_starter"]
    ].copy()

    starter_score_check = (
        starters.groupby(
            [
                "week",
                "fantasy_team",
                "matchup_id",
            ],
            as_index=False,
        )
        .agg(
            calculated_starter_points=(
                "fantasy_points",
                "sum",
            ),
            yahoo_team_score=(
                "team_score",
                "first",
            ),
        )
    )

    starter_score_check[
        "difference"
    ] = (
        starter_score_check[
            "calculated_starter_points"
        ]
        - starter_score_check[
            "yahoo_team_score"
        ]
    ).round(6)

    # Floating-point tolerance.
    bad_scores = starter_score_check[
        starter_score_check[
            "difference"
        ].abs()
        > 0.011
    ].copy()

    if bad_scores.empty:
        result(
            PASS,
            "Starter fantasy points reconcile to Yahoo team scores",
            (
                f"{len(starter_score_check)} team-weeks checked; "
                "any blank starter scores therefore contribute 0.00"
            ),
        )
    else:
        result(
            FAIL,
            "Starter-point mismatches",
            f"{len(bad_scores)} team-weeks",
        )

        print()
        print(
            bad_scores[
                [
                    "week",
                    "fantasy_team",
                    "calculated_starter_points",
                    "yahoo_team_score",
                    "difference",
                ]
            ]
            .sort_values(
                [
                    "week",
                    "fantasy_team",
                ]
            )
            .to_string(index=False)
        )

        failures += 1

    # -------------------------------------------------------------------------
    # 10. MATCHUP SCORE CONSISTENCY
    # -------------------------------------------------------------------------

    banner("10. MATCHUP SCORE CONSISTENCY")

    lineup_scores = (
        lineups.groupby(
            [
                "week",
                "matchup_id",
                "fantasy_team",
            ],
            as_index=False,
        )
        .agg(
            team_score=(
                "team_score",
                "first",
            ),
            opponent=(
                "opponent",
                "first",
            ),
            opponent_score=(
                "opponent_score",
                "first",
            ),
        )
    )

    bad_opponent_links = []

    for row in lineup_scores.itertuples(
        index=False
    ):
        opponent_row = lineup_scores[
            (lineup_scores["week"] == row.week)
            & (
                lineup_scores["matchup_id"]
                == row.matchup_id
            )
            & (
                lineup_scores["fantasy_team"]
                == row.opponent
            )
        ]

        if len(opponent_row) != 1:
            bad_opponent_links.append(
                (
                    row.week,
                    row.matchup_id,
                    row.fantasy_team,
                    "missing/duplicate opponent row",
                )
            )
            continue

        opponent_row = opponent_row.iloc[0]

        if abs(
            float(row.opponent_score)
            - float(opponent_row["team_score"])
        ) > 0.011:
            bad_opponent_links.append(
                (
                    row.week,
                    row.matchup_id,
                    row.fantasy_team,
                    "opponent score mismatch",
                )
            )

    if not bad_opponent_links:
        result(
            PASS,
            "Opponent/team score links are internally consistent",
            f"{len(lineup_scores)} team-matchup rows checked",
        )
    else:
        result(
            FAIL,
            "Matchup score linkage problems",
            f"{len(bad_opponent_links)} issues",
        )

        for issue in bad_opponent_links[:30]:
            print(issue)

        failures += 1

    # -------------------------------------------------------------------------
    # 11. BENCH / IR SUMMARY
    # -------------------------------------------------------------------------

    banner("11. BENCH / IR SUMMARY")

    bench_count = int(
        lineups["is_bench"].sum()
    )

    ir_count = int(
        lineups["is_ir"].sum()
    )

    starter_count = int(
        lineups["is_starter"].sum()
    )

    result(
        PASS,
        "Starter records",
        f"{starter_count:,}",
    )

    result(
        PASS,
        "Bench records",
        f"{bench_count:,}",
    )

    result(
        PASS,
        "IR records",
        f"{ir_count:,}",
    )

    bench_per_team_week = team_week_key_counts(
        lineups,
        lineups["is_bench"],
    )

    if not bench_per_team_week.empty:
        print()
        print(
            "Bench players per team-week:"
        )

        print(
            bench_per_team_week["count"]
            .value_counts()
            .sort_index()
            .rename_axis("bench_count")
            .rename("team_weeks")
            .to_string()
        )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    banner("FINAL VALIDATION RESULT")

    print(
        f"Failures: {failures}"
    )

    print(
        f"Warnings: {warnings}"
    )

    if failures == 0:
        if warnings == 0:
            print()
            print(
                f"VALIDATION PASSED: {YEAR} weekly lineup data passed all checks."
            )
        else:
            print()
            print(
                f"VALIDATION PASSED WITH WARNINGS: {YEAR} has no structural failures."
            )
    else:
        print()
        print(
            "VALIDATION FAILED: fix the issues above before using this collector "
            "for historical seasons."
        )


if __name__ == "__main__":
    main()