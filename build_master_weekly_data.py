from pathlib import Path
import pandas as pd

START_YEAR = 2018
END_YEAR = 2025

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "matchups" / "player_week_stats"

LINEUPS_OUT = DATA_DIR / f"all_weekly_lineups_{START_YEAR}_{END_YEAR}.csv"
MATCHUPS_OUT = DATA_DIR / f"all_matchups_{START_YEAR}_{END_YEAR}.csv"

# Regular-season weeks used by the validated historical files.
REGULAR_SEASON_WEEKS = {
    2018: 13,
    2019: 13,
    2020: 13,
    2021: 14,
    2022: 14,
    2023: 14,
    2024: 14,
    2025: 14,
}

TEAMS = 12
STARTERS_PER_TEAM = 9
MATCHUPS_PER_WEEK = TEAMS // 2


def banner(title):
    print()
    print("=" * 96)
    print(title)
    print("=" * 96)


def fail(message):
    raise RuntimeError(message)


def truthy(series):
    return series.astype(str).str.strip().str.lower().isin(
        ["true", "1", "yes"]
    )


def main():
    banner("BUILDING MASTER WEEKLY LINEUP + MATCHUP DATASETS")
    print(f"Seasons: {START_YEAR}-{END_YEAR}")
    print(f"Folder:  {DATA_DIR}")

    lineup_frames = []
    matchup_frames = []

    banner("1. LOADING VALIDATED SEASON FILES")

    for year in range(START_YEAR, END_YEAR + 1):
        lineup_file = DATA_DIR / f"{year}_weekly_lineups.csv"
        matchup_file = DATA_DIR / f"{year}_matchups.csv"

        if not lineup_file.exists():
            fail(f"Missing lineup file: {lineup_file}")

        if not matchup_file.exists():
            fail(f"Missing matchup file: {matchup_file}")

        lineups = pd.read_csv(lineup_file)
        matchups = pd.read_csv(matchup_file)

        if lineups.empty:
            fail(f"{year} lineup file is empty.")

        if matchups.empty:
            fail(f"{year} matchup file is empty.")

        # Keep only validated regular-season weeks for this season.
        # Older master files may still physically contain playoff weeks
        # (for example, 2020 Week 14), but those should not enter the
        # combined regular-season dataset.
        final_week = REGULAR_SEASON_WEEKS[year]

        lineups["week"] = pd.to_numeric(
            lineups["week"],
            errors="raise",
        ).astype(int)

        matchups["week"] = pd.to_numeric(
            matchups["week"],
            errors="raise",
        ).astype(int)

        lineups = lineups[
            lineups["week"].between(
                1,
                final_week,
            )
        ].copy()

        matchups = matchups[
            matchups["week"].between(
                1,
                final_week,
            )
        ].copy()

        if "year" not in lineups.columns:
            lineups["year"] = year

        if "year" not in matchups.columns:
            matchups["year"] = year

        lineups["year"] = pd.to_numeric(
            lineups["year"], errors="raise"
        ).astype(int)

        matchups["year"] = pd.to_numeric(
            matchups["year"], errors="raise"
        ).astype(int)

        if set(lineups["year"].unique()) != {year}:
            fail(
                f"{year} lineup file contains unexpected year values: "
                f"{sorted(lineups['year'].unique())}"
            )

        if set(matchups["year"].unique()) != {year}:
            fail(
                f"{year} matchup file contains unexpected year values: "
                f"{sorted(matchups['year'].unique())}"
            )

        lineup_frames.append(lineups)
        matchup_frames.append(matchups)

        print(
            f"{year}: "
            f"{len(lineups):,} regular-season lineup rows · "
            f"{len(matchups):,} regular-season matchups "
            f"(Weeks 1-{final_week})"
        )

    all_lineups = pd.concat(
        lineup_frames,
        ignore_index=True,
        sort=False,
    )

    all_matchups = pd.concat(
        matchup_frames,
        ignore_index=True,
        sort=False,
    )

    banner("2. MASTER DATASET SHAPE")
    print(f"Lineup rows:  {len(all_lineups):,}")
    print(f"Matchup rows: {len(all_matchups):,}")

    expected_matchups = sum(
        weeks * MATCHUPS_PER_WEEK
        for weeks in REGULAR_SEASON_WEEKS.values()
    )

    if len(all_matchups) != expected_matchups:
        fail(
            f"Master matchup count is {len(all_matchups)}, "
            f"expected {expected_matchups}."
        )

    print(f"[PASS] Expected matchup total: {expected_matchups}")

    banner("3. SEASON + WEEK COVERAGE")

    for year, final_week in REGULAR_SEASON_WEEKS.items():
        expected_weeks = list(range(1, final_week + 1))

        lineup_weeks = sorted(
            pd.to_numeric(
                all_lineups.loc[
                    all_lineups["year"] == year,
                    "week",
                ],
                errors="raise",
            )
            .astype(int)
            .unique()
            .tolist()
        )

        matchup_weeks = sorted(
            pd.to_numeric(
                all_matchups.loc[
                    all_matchups["year"] == year,
                    "week",
                ],
                errors="raise",
            )
            .astype(int)
            .unique()
            .tolist()
        )

        if lineup_weeks != expected_weeks:
            fail(
                f"{year} lineup weeks are {lineup_weeks}; "
                f"expected {expected_weeks}."
            )

        if matchup_weeks != expected_weeks:
            fail(
                f"{year} matchup weeks are {matchup_weeks}; "
                f"expected {expected_weeks}."
            )

        print(f"[PASS] {year}: weeks 1-{final_week}")

    banner("4. SIX MATCHUPS PER WEEK")

    matchup_counts = (
        all_matchups
        .groupby(["year", "week"])
        .size()
        .reset_index(name="matchups")
    )

    bad_matchup_counts = matchup_counts[
        matchup_counts["matchups"] != MATCHUPS_PER_WEEK
    ]

    if not bad_matchup_counts.empty:
        print(bad_matchup_counts.to_string(index=False))
        fail("At least one season-week does not contain 6 matchups.")

    print(
        f"[PASS] All {len(matchup_counts)} season-weeks "
        "contain exactly 6 matchups."
    )

    banner("5. TEAM COVERAGE")

    team_counts = (
        all_lineups
        .groupby(["year", "week"])["fantasy_team"]
        .nunique()
        .reset_index(name="teams")
    )

    bad_team_counts = team_counts[
        team_counts["teams"] != TEAMS
    ]

    if not bad_team_counts.empty:
        print(bad_team_counts.to_string(index=False))
        fail("At least one season-week does not contain 12 teams.")

    print(
        f"[PASS] All {len(team_counts)} season-weeks "
        "contain exactly 12 fantasy teams."
    )

    banner("6. STARTER COUNTS")

    if "is_starter" not in all_lineups.columns:
        fail("Master lineup data has no is_starter column.")

    starters = all_lineups[truthy(all_lineups["is_starter"])].copy()

    starter_counts = (
        starters
        .groupby(["year", "week", "fantasy_team"])
        .size()
        .reset_index(name="starters")
    )

    bad_starters = starter_counts[
        starter_counts["starters"] != STARTERS_PER_TEAM
    ]

    if not bad_starters.empty:
        print(bad_starters.to_string(index=False))
        fail("At least one team-week does not contain exactly 9 starters.")

    expected_team_weeks = sum(
        weeks * TEAMS
        for weeks in REGULAR_SEASON_WEEKS.values()
    )

    if len(starter_counts) != expected_team_weeks:
        fail(
            f"Found {len(starter_counts)} starter team-weeks; "
            f"expected {expected_team_weeks}."
        )

    expected_starters = expected_team_weeks * STARTERS_PER_TEAM

    if len(starters) != expected_starters:
        fail(
            f"Found {len(starters)} starter rows; "
            f"expected {expected_starters}."
        )

    print(
        f"[PASS] {expected_team_weeks:,} team-weeks with "
        f"{expected_starters:,} starter rows."
    )

    banner("7. DUPLICATE CHECKS")

    lineup_key = [
        c for c in [
            "year",
            "week",
            "fantasy_team",
            "player",
            "lineup_slot",
        ]
        if c in all_lineups.columns
    ]

    lineup_dupes = all_lineups.duplicated(
        subset=lineup_key,
        keep=False,
    )

    # Repeated literal "(Empty)" slots can be legitimate, so only fail
    # duplicates for actual named players.
    if "player" in all_lineups.columns:
        named_dupes = (
            lineup_dupes
            & ~all_lineups["player"]
            .astype(str)
            .str.strip()
            .eq("(Empty)")
        )
    else:
        named_dupes = lineup_dupes

    if named_dupes.any():
        print(
            all_lineups.loc[named_dupes, lineup_key]
            .sort_values(lineup_key)
            .head(50)
            .to_string(index=False)
        )
        fail("Duplicate named player/team/week/slot rows found.")

    print("[PASS] No duplicate named player-week lineup records.")

    if "matchup_id" in all_matchups.columns:
        matchup_dupes = all_matchups.duplicated(
            subset=["year", "matchup_id"],
            keep=False,
        )

        if matchup_dupes.any():
            print(
                all_matchups.loc[
                    matchup_dupes,
                    ["year", "week", "matchup_id"],
                ]
                .sort_values(["year", "week", "matchup_id"])
                .to_string(index=False)
            )
            fail("Duplicate matchup IDs found.")

        print("[PASS] No duplicate matchup IDs.")

    banner("8. ROW-COUNT RECONCILIATION")

    source_lineup_rows = sum(len(df) for df in lineup_frames)
    source_matchup_rows = sum(len(df) for df in matchup_frames)

    if len(all_lineups) != source_lineup_rows:
        fail("Lineup row count changed during concatenation.")

    if len(all_matchups) != source_matchup_rows:
        fail("Matchup row count changed during concatenation.")

    print(
        f"[PASS] Lineups: {len(all_lineups):,} master rows = "
        f"{source_lineup_rows:,} source rows."
    )
    print(
        f"[PASS] Matchups: {len(all_matchups):,} master rows = "
        f"{source_matchup_rows:,} source rows."
    )

    banner("9. SAVING MASTER FILES")

    sort_lineups = [
        c for c in [
            "year",
            "week",
            "matchup_id",
            "fantasy_team",
            "lineup_slot",
        ]
        if c in all_lineups.columns
    ]

    sort_matchups = [
        c for c in [
            "year",
            "week",
            "matchup_id",
        ]
        if c in all_matchups.columns
    ]

    all_lineups = all_lineups.sort_values(
        sort_lineups,
        kind="stable",
    ).reset_index(drop=True)

    all_matchups = all_matchups.sort_values(
        sort_matchups,
        kind="stable",
    ).reset_index(drop=True)

    all_lineups.to_csv(LINEUPS_OUT, index=False)
    all_matchups.to_csv(MATCHUPS_OUT, index=False)

    print(LINEUPS_OUT)
    print(MATCHUPS_OUT)

    banner("MASTER DATASET BUILD COMPLETE")
    print(f"Seasons:       {START_YEAR}-{END_YEAR}")
    print(f"Lineup rows:   {len(all_lineups):,}")
    print(f"Matchups:      {len(all_matchups):,}")
    print(f"Team-weeks:    {expected_team_weeks:,}")
    print(f"Starter rows:  {len(starters):,}")
    print()
    print("The original season files were not modified.")


if __name__ == "__main__":
    main()