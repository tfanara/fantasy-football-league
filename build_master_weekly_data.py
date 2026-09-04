from pathlib import Path
import pandas as pd

from season_config import CURRENT_SEASON, LAST_COMPLETED_SEASON, REGULAR_SEASON_END_WEEK, print_season_config

START_YEAR = 2017
END_YEAR = CURRENT_SEASON

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "matchups" / "player_week_stats"

LINEUPS_OUT = DATA_DIR / f"all_weekly_lineups_{START_YEAR}_{END_YEAR}.csv"
MATCHUPS_OUT = DATA_DIR / f"all_matchups_{START_YEAR}_{END_YEAR}.csv"

# Regular-season weeks used by the validated historical files.
REGULAR_SEASON_WEEKS = {
    year: REGULAR_SEASON_END_WEEK[year]
    for year in range(START_YEAR, LAST_COMPLETED_SEASON + 1)
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
    global REGULAR_SEASON_WEEKS
    banner("BUILDING MASTER WEEKLY LINEUP + MATCHUP DATASETS")
    print_season_config()
    print(f"Seasons: {START_YEAR}-{END_YEAR}")
    print(f"Folder:  {DATA_DIR}")

    lineup_frames = []
    matchup_frames = []

    banner("1. LOADING VALIDATED SEASON FILES")

    included_weeks = dict(REGULAR_SEASON_WEEKS)

    for year in range(START_YEAR, END_YEAR + 1):
        lineup_file = DATA_DIR / f"{year}_weekly_lineups.csv"
        matchup_file = DATA_DIR / f"{year}_matchups.csv"

        if not lineup_file.exists() or not matchup_file.exists():
            if year <= LAST_COMPLETED_SEASON:
                fail(f"Missing validated season files for completed season {year}.")
            print(f"{year}: current-season player-week files not available yet; skipping.")
            continue

        lineups = pd.read_csv(lineup_file)
        matchups = pd.read_csv(matchup_file)
        if lineups.empty or matchups.empty:
            if year <= LAST_COMPLETED_SEASON:
                fail(f"{year} validated season file is empty.")
            print(f"{year}: current-season player-week files are empty; skipping.")
            continue

        lineups["week"] = pd.to_numeric(lineups["week"], errors="raise").astype(int)
        matchups["week"] = pd.to_numeric(matchups["week"], errors="raise").astype(int)
        if "year" not in lineups.columns:
            lineups["year"] = year
        if "year" not in matchups.columns:
            matchups["year"] = year
        lineups["year"] = pd.to_numeric(lineups["year"], errors="raise").astype(int)
        matchups["year"] = pd.to_numeric(matchups["year"], errors="raise").astype(int)
        if set(lineups["year"].unique()) != {year}:
            fail(f"{year} lineup file contains unexpected year values: {sorted(lineups['year'].unique())}")
        if set(matchups["year"].unique()) != {year}:
            fail(f"{year} matchup file contains unexpected year values: {sorted(matchups['year'].unique())}")

        if year <= LAST_COMPLETED_SEASON:
            final_week = REGULAR_SEASON_WEEKS[year]
        else:
            # Player-week analytics use their own validated horizon. A current
            # week is eligible only when the collector produced 6 matchups,
            # 12 teams, and exactly 9 starters for every team.
            complete = []
            for week in range(1, REGULAR_SEASON_END_WEEK[year] + 1):
                mw = matchups[matchups["week"] == week]
                lw = lineups[lineups["week"] == week]
                if len(mw) != MATCHUPS_PER_WEEK or lw.empty:
                    continue
                if "fantasy_team" not in lw.columns or lw["fantasy_team"].nunique() != TEAMS:
                    continue
                if "is_starter" not in lw.columns:
                    continue
                sc = (
                    lw[truthy(lw["is_starter"])]
                    .groupby("fantasy_team")
                    .size()
                )
                if len(sc) == TEAMS and (sc == STARTERS_PER_TEAM).all():
                    complete.append(week)
            final_week = 0
            for week in range(1, max(complete, default=0) + 1):
                if week not in complete:
                    break
                final_week = week
            if final_week == 0:
                print(f"{year}: no validated player-week is complete yet; skipping.")
                continue
            included_weeks[year] = final_week

        lineups = lineups[lineups["week"].between(1, final_week)].copy()
        matchups = matchups[matchups["week"].between(1, final_week)].copy()
        lineup_frames.append(lineups)
        matchup_frames.append(matchups)
        print(
            f"{year}: {len(lineups):,} lineup rows · {len(matchups):,} matchups "
            f"(validated Weeks 1-{final_week})"
        )

    if not lineup_frames or not matchup_frames:
        fail("No validated weekly player data found.")

    REGULAR_SEASON_WEEKS = included_weeks

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

    # Stable canonical aliases let downstream builders stop depending on a
    # year embedded in the filename during the Layer-2 migration.
    canonical_lineups = DATA_DIR / "all_weekly_lineups.csv"
    canonical_matchups = DATA_DIR / "all_matchups.csv"
    all_lineups.to_csv(canonical_lineups, index=False)
    all_matchups.to_csv(canonical_matchups, index=False)

    print(LINEUPS_OUT)
    print(MATCHUPS_OUT)
    print(canonical_lineups)
    print(canonical_matchups)

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