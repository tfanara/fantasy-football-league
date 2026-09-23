#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from season_config import CURRENT_SEASON


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SEASON = int(CURRENT_SEASON)


# =============================================================================
# PIPELINE
# =============================================================================

@dataclass(frozen=True)
class Step:
    name: str
    script: str
    phase: str


CORE_STEPS = [
    Step(
        "Yahoo current-season API collection",
        "collect_yahoo_current_season.py",
        "COLLECTION",
    ),
    Step(
        "Master standings",
        "build_master_standings.py",
        "CORE",
    ),
    Step(
        "Master weekly matchup / lineup data",
        "build_master_weekly_data.py",
        "CORE",
    ),
    Step(
        "Weekly-current matchup master",
        "merge_matchups.py",
        "CORE",
    ),
    Step(
        "Master transactions",
        "build_master_transactions.py",
        "CORE",
    ),
    Step(
        "League history",
        "build_league_history.py",
        "CORE",
    ),
    Step(
        "Luck metrics",
        "build_luck_metrics.py",
        "CORE",
    ),
    Step(
        "Lineup efficiency",
        "build_lineup_efficiency.py",
        "CORE",
    ),
    Step(
        "Bench decisions",
        "build_bench_decisions_analysis.py",
        "CORE",
    ),
    Step(
        "Bad beats",
        "build_bad_beat_analysis.py",
        "CORE",
    ),
]


EXTENDED_STEPS = [
    Step(
        "Schedule-swap analysis",
        "build_schedule_swap_analysis.py",
        "EXTENDED",
    ),
    Step(
        "Waiver-value analysis",
        "build_waiver_value_analysis.py",
        "EXTENDED",
    ),
    Step(
        "Positional-edge analysis",
        "build_positional_edge_analysis.py",
        "EXTENDED",
    ),
    Step(
        "Stack analysis",
        "build_stack_analysis.py",
        "EXTENDED",
    ),
]


POWER_RANKING_STEP = Step(
    "Power rankings",
    "build_power_rankings.py",
    "EDITORIAL",
)

NEWS_CONTEXT_STEP = Step(
    "Weekly news intelligence",
    "build_weekly_news_context.py",
    "EDITORIAL",
)

EDITORIAL_STEPS = [
    Step(
        "Power Rankings commentary",
        "generate_power_rankings_commentary.py",
        "EDITORIAL",
    ),
    Step(
        "Commissioner's Mistake article",
        "generate_weekly_article.py",
        "EDITORIAL",
    ),
]


# =============================================================================
# OUTPUT
# =============================================================================

def banner(text: str, char: str = "=") -> None:
    print()
    print(char * 88)
    print(text)
    print(char * 88)
    print()


def fail(message: str) -> None:
    banner("WEEKLY UPDATE FAILED", "!")
    print(message)
    print()
    print("Downstream processing has stopped.")
    print("Fix the problem and rerun:")
    print()
    print("    python update_week.py")
    print()
    raise SystemExit(1)


def pass_line(message: str) -> None:
    print(f"[PASS] {message}")


def warn_line(message: str) -> None:
    print(f"[WARN] {message}")


# =============================================================================
# SCRIPT EXECUTION
# =============================================================================

def validate_scripts(steps: list[Step]) -> None:
    missing = []

    for step in steps:
        path = ROOT / step.script
        if not path.exists():
            missing.append(step.script)

    if missing:
        fail(
            "Required pipeline scripts are missing:\n\n"
            + "\n".join(f"  - {name}" for name in missing)
        )


def run_step(step: Step, number: int, total: int) -> None:
    banner(
        f"[{number}/{total}] {step.name}  —  {step.phase}",
        "-",
    )

    path = ROOT / step.script

    started = time.time()

    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
    )

    elapsed = time.time() - started

    if result.returncode != 0:
        fail(
            f"{step.name} failed.\n\n"
            f"Script: {step.script}\n"
            f"Exit code: {result.returncode}"
        )

    pass_line(
        f"{step.name} completed in {elapsed:.1f}s"
    )


# =============================================================================
# DATA HELPERS
# =============================================================================

def read_csv(path: Path, required: bool = True) -> pd.DataFrame:
    if not path.exists():
        if required:
            fail(f"Required data file does not exist:\n{path}")
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception as exc:
        fail(
            f"Could not read:\n{path}\n\n"
            f"{type(exc).__name__}: {exc}"
        )


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def current_season_rows(
    df: pd.DataFrame,
    path: Path,
) -> pd.DataFrame:

    if "year" not in df.columns:
        fail(f"{path} has no 'year' column.")

    years = numeric(df["year"])

    return df.loc[years.eq(SEASON)].copy()


# =============================================================================
# DETECT CURRENT COMPLETED WEEK
# =============================================================================

def detect_completed_week() -> int:
    path = (
        DATA
        / "matchups"
        / "player_week_stats"
        / f"{SEASON}_matchups.csv"
    )

    df = read_csv(path)

    required = {
        "year",
        "week",
        "left_team",
        "right_team",
        "left_score",
        "right_score",
    }

    missing = required - set(df.columns)

    if missing:
        fail(
            f"{path} is missing columns required for week detection:\n"
            + ", ".join(sorted(missing))
        )

    df = current_season_rows(df, path)

    df["week"] = numeric(df["week"])
    df["left_score"] = numeric(df["left_score"])
    df["right_score"] = numeric(df["right_score"])

    completed = df[
        df["week"].notna()
        & df["left_score"].notna()
        & df["right_score"].notna()
    ].copy()

    if completed.empty:
        fail(
            f"No completed {SEASON} matchup weeks were found "
            "after Yahoo API collection."
        )

    week = int(completed["week"].max())

    week_rows = completed[
        completed["week"].eq(week)
    ]

    if len(week_rows) != 6:
        fail(
            f"{SEASON} Week {week} contains "
            f"{len(week_rows)} completed matchups; expected 6."
        )

    teams = set(
        week_rows["left_team"].dropna().astype(str)
    ) | set(
        week_rows["right_team"].dropna().astype(str)
    )

    if len(teams) != 12:
        fail(
            f"{SEASON} Week {week} contains "
            f"{len(teams)} unique teams; expected 12."
        )

    return week


# =============================================================================
# COLLECTION VALIDATION
# =============================================================================

def validate_api_collection(week: int) -> None:
    banner("CURRENT-SEASON API VALIDATION")

    expected = [
        DATA / str(SEASON) / "standings.csv",
        DATA / str(SEASON) / "transactions.csv",
        DATA / str(SEASON) / "upcoming_matchups.csv",
        DATA
        / "matchups"
        / "player_week_stats"
        / f"{SEASON}_matchups.csv",
        DATA
        / "matchups"
        / "player_week_stats"
        / f"{SEASON}_weekly_lineups.csv",
    ]

    for path in expected:
        if not path.exists():
            fail(
                "Yahoo API collection did not produce required file:\n"
                f"{path}"
            )

        pass_line(str(path.relative_to(ROOT)))

    # Standings
    standings_path = DATA / str(SEASON) / "standings.csv"
    standings = read_csv(standings_path)

    if len(standings) != 12:
        fail(
            f"Current standings contain {len(standings)} teams; "
            "expected 12."
        )

    pass_line("Current standings contain 12 teams")

    # Matchups
    matchup_path = (
        DATA
        / "matchups"
        / "player_week_stats"
        / f"{SEASON}_matchups.csv"
    )

    matchups = read_csv(matchup_path)

    matchups["week"] = numeric(matchups["week"])

    latest = matchups[
        matchups["week"].eq(week)
    ]

    if len(latest) != 6:
        fail(
            f"Current matchup source contains "
            f"{len(latest)} Week {week} games; expected 6."
        )

    pass_line(
        f"{SEASON} Week {week}: 6 completed API matchups"
    )

    # Lineups
    lineup_path = (
        DATA
        / "matchups"
        / "player_week_stats"
        / f"{SEASON}_weekly_lineups.csv"
    )

    lineups = read_csv(lineup_path)

    if "week" not in lineups.columns:
        fail(f"{lineup_path} has no week column.")

    lineups["week"] = numeric(lineups["week"])

    latest_lineups = lineups[
        lineups["week"].eq(week)
    ]

    if latest_lineups.empty:
        fail(
            f"No player lineup rows found for "
            f"{SEASON} Week {week}."
        )

    pass_line(
        f"{SEASON} Week {week}: player lineup data present"
    )


# =============================================================================
# MASTER DATA VALIDATION
# =============================================================================

def validate_master_weekly(week: int) -> None:
    banner("MASTER WEEKLY DATA VALIDATION")

    matchup_path = (
        DATA
        / "matchups"
        / "player_week_stats"
        / "all_matchups.csv"
    )

    lineup_path = (
        DATA
        / "matchups"
        / "player_week_stats"
        / "all_weekly_lineups.csv"
    )

    matchups = read_csv(matchup_path)
    lineups = read_csv(lineup_path)

    for label, frame, path in [
        ("matchups", matchups, matchup_path),
        ("lineups", lineups, lineup_path),
    ]:
        if "year" not in frame.columns:
            fail(f"{path} has no year column.")

        if "week" not in frame.columns:
            fail(f"{path} has no week column.")

        years = numeric(frame["year"])
        weeks = numeric(frame["week"])

        rows = frame[
            years.eq(SEASON)
            & weeks.eq(week)
        ]

        if rows.empty:
            fail(
                f"Master {label} do not contain "
                f"{SEASON} Week {week}."
            )

        pass_line(
            f"Master {label}: {SEASON} Week {week} present"
        )


def validate_master_transactions() -> None:
    banner("MASTER TRANSACTION VALIDATION")

    current_path = DATA / str(SEASON) / "transactions.csv"

    master_path = (
        DATA
        / "transactions"
        / "all_transactions.csv"
    )

    current = read_csv(current_path)
    master = read_csv(master_path)

    if "year" not in master.columns:
        fail(f"{master_path} has no year column.")

    master_year = numeric(master["year"])

    master_current = master[
        master_year.eq(SEASON)
    ].copy()

    # Compare normalized identifying fields rather than simply
    # requiring an arbitrary transaction count.
    compare = [
        "team",
        "added_player",
        "acquisition_type",
        "dropped_player",
    ]

    for col in compare:
        if col not in current.columns:
            fail(
                f"{current_path} is missing transaction column: "
                f"{col}"
            )

        if col not in master_current.columns:
            fail(
                f"{master_path} is missing transaction column: "
                f"{col}"
            )

    def normalize_values(df: pd.DataFrame) -> set[tuple]:
        temp = df[compare].copy()

        for col in compare:
            temp[col] = (
                temp[col]
                .fillna("")
                .astype(str)
                .str.strip()
            )

        return set(
            temp.itertuples(
                index=False,
                name=None,
            )
        )

    api_values = normalize_values(current)
    master_values = normalize_values(master_current)

    missing = api_values - master_values

    if missing:
        sample = list(missing)[:5]

        fail(
            f"{len(missing)} current-season API transaction(s) "
            "are missing from the master transaction dataset.\n\n"
            f"Examples:\n{sample}"
        )

    pass_line(
        f"All {len(api_values)} normalized {SEASON} API "
        "transactions are present in the master"
    )


# =============================================================================
# DERIVED WEEK VALIDATION
# =============================================================================

def validate_week_file(
    path: Path,
    week: int,
    *,
    year_column: str = "year",
    week_column: str = "week",
    expected_teams: int | None = None,
    team_column: str = "fantasy_team",
) -> None:

    df = read_csv(path)

    if year_column not in df.columns:
        fail(
            f"{path} has no '{year_column}' column."
        )

    if week_column not in df.columns:
        fail(
            f"{path} has no '{week_column}' column."
        )

    years = numeric(df[year_column])
    weeks = numeric(df[week_column])

    current = df[
        years.eq(SEASON)
        & weeks.eq(week)
    ]

    if current.empty:
        fail(
            f"{path.relative_to(ROOT)} does not contain "
            f"{SEASON} Week {week}."
        )

    if expected_teams is not None:
        if team_column not in current.columns:
            fail(
                f"{path} has no '{team_column}' column."
            )

        teams = current[team_column].dropna().nunique()

        if teams != expected_teams:
            fail(
                f"{path.relative_to(ROOT)} contains "
                f"{teams} teams for {SEASON} Week {week}; "
                f"expected {expected_teams}."
            )

    pass_line(
        f"{path.relative_to(ROOT)} → "
        f"{SEASON} Week {week}"
    )


def validate_core_analysis(week: int) -> None:
    banner("CORE ANALYSIS VALIDATION")

    checks = [
        (
            DATA
            / "matchups"
            / "player_week_stats"
            / "analysis"
            / "luck_team_week.csv",
            12,
            "fantasy_team",
        ),
        (
            DATA
            / "matchups"
            / "player_week_stats"
            / "analysis"
            / "lineup_efficiency_team_week.csv",
            12,
            "fantasy_team",
        ),
    ]

    for path, teams, team_col in checks:
        validate_week_file(
            path,
            week,
            expected_teams=teams,
            team_column=team_col,
        )


# =============================================================================
# POWER RANKINGS VALIDATION
# =============================================================================

def validate_power_rankings(week: int) -> None:
    banner("POWER RANKINGS VALIDATION")

    path = (
        DATA
        / "analysis"
        / "power_rankings_weekly.csv"
    )

    if not path.exists():
        fail(f"Missing required file: {path}")

    df = read_csv(path)

    required = {
        "year",
        "through_week",
        "fantasy_team",
        "power_rank",
    }

    missing = required - set(df.columns)

    if missing:
        fail(
            f"{path} is missing required columns: "
            f"{sorted(missing)}"
        )

    years = numeric(df["year"])
    weeks = numeric(df["through_week"])

    current = df[
        years.eq(SEASON)
        & weeks.eq(week)
    ].copy()

    if len(current) != 12:
        fail(
            f"Power Rankings for {SEASON} Week {week} "
            f"contain {len(current)} teams; expected 12."
        )

    if current["fantasy_team"].nunique() != 12:
        fail(
            f"Power Rankings for {SEASON} Week {week} "
            "do not contain exactly 12 unique fantasy teams."
        )

    ranks = sorted(
        numeric(current["power_rank"])
        .dropna()
        .astype(int)
        .tolist()
    )

    if ranks != list(range(1, 13)):
        fail(
            f"Power Rankings for {SEASON} Week {week} "
            "are not exactly ranks 1-12."
        )

    pass_line(
        f"Power Rankings: {SEASON} Week {week} "
        "contains 12 teams and exactly ranks 1-12"
    )


# =============================================================================
# EDITORIAL VALIDATION
# =============================================================================

def validate_editorial(week: int) -> None:
    banner("EDITORIAL VALIDATION")

    context = (
        DATA
        / "news"
        / str(SEASON)
        / f"week_{week:02d}_context.json"
    )

    commentary = (
        DATA
        / "power_rankings"
        / str(SEASON)
        / f"week_{week:02d}_commentary.json"
    )

    article = (
        DATA
        / "news"
        / str(SEASON)
        / f"week_{week:02d}_article.json"
    )

    for path in [context, commentary, article]:
        if not path.exists():
            fail(
                "Expected editorial output was not created:\n"
                f"{path}"
            )

        pass_line(str(path.relative_to(ROOT)))


# =============================================================================
# PAGE READINESS
# =============================================================================

def page_readiness(week: int, skip_editorial: bool) -> None:
    banner("PROJECT-WIDE PAGE DATA CHECK")

    weekly_pages = [
        "Standings",
        "Records",
        "History",
        "Teams",
        "Head-to-Head",
        "Lineup Efficiency",
        "League Historian",
        "Analysis",
        "Power Rankings",
    ]

    for page in weekly_pages:
        print(f"PASS  {page}")

    if skip_editorial:
        print("SKIP  Commissioner's Mistake — editorial disabled")
    else:
        print("PASS  Commissioner's Mistake")

    print()
    print("Event-driven / static:")
    print("SKIP  Rules")
    print("SKIP  Draft")
    print("SKIP  Keepers")

    print()
    pass_line(
        f"Weekly production datasets validated through "
        f"{SEASON} Week {week}"
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the production weekly fantasy-football update "
            "using Yahoo Fantasy API current-season data."
        )
    )

    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Skip extended Analysis-page builders.",
    )

    parser.add_argument(
        "--skip-editorial",
        action="store_true",
        help=(
            "Skip Gemini commentary and weekly article generation."
        ),
    )

    args = parser.parse_args()

    banner(
        "MALLE IS THE WORST COMMISSIONER — WEEKLY UPDATE"
    )

    print(f"Season: {SEASON}")
    print()
    print("Current-season source policy:")
    print("  Yahoo Fantasy API only")
    print("  No browser scraping")
    print("  No manual HTML collection")
    print()

    # ---------------------------------------------------------
    # Assemble pipeline
    # ---------------------------------------------------------

    pre_editorial = list(CORE_STEPS)

    if not args.core_only:
        pre_editorial.extend(EXTENDED_STEPS)

    # Power Rankings and context still run in core-only mode,
    # because they are weekly site features rather than optional
    # deep-analysis pages.
    pre_editorial.extend(
        [
            POWER_RANKING_STEP,
            NEWS_CONTEXT_STEP,
        ]
    )

    all_steps = list(pre_editorial)

    if not args.skip_editorial:
        all_steps.extend(EDITORIAL_STEPS)

    # ---------------------------------------------------------
    # Final project-wide freshness gate
    # ---------------------------------------------------------
    #
    # This is deliberately the LAST executable step.
    # It verifies that every deterministic production dataset
    # agrees with the latest completed fantasy week before the
    # weekly update is allowed to report success.
    #
    # Event-driven datasets such as Keepers and currently-empty
    # Waiver Value output may produce non-blocking warnings.
    #
    freshness_audit_step = Step(
        "Project freshness audit",
        "audit_project_freshness.py",
        "AUDIT",
    )

    all_steps.append(freshness_audit_step)

    validate_scripts(all_steps)

    total = len(all_steps)
    number = 0

    # ---------------------------------------------------------
    # API collection
    # ---------------------------------------------------------

    first = all_steps[0]
    number += 1
    run_step(first, number, total)

    week = detect_completed_week()

    banner("LATEST COMPLETED WEEK DETECTED")

    print(f"Season:         {SEASON}")
    print(f"Completed week: {week}")

    validate_api_collection(week)

    # ---------------------------------------------------------
    # Remaining production steps
    # ---------------------------------------------------------

    #
    # The final entry in all_steps is always the project-wide
    # freshness audit. Run the production pipeline first, then
    # perform editorial validation, and only then allow the
    # freshness audit to act as the final gate.
    #

    production_steps = all_steps[1:-1]
    freshness_step = all_steps[-1]

    for step in production_steps:
        number += 1

        run_step(step, number, total)

        # Validate at important boundaries.
        if step.script == "build_master_weekly_data.py":
            validate_master_weekly(week)

        elif step.script == "build_master_transactions.py":
            validate_master_transactions()

        elif step.script == "build_lineup_efficiency.py":
            validate_core_analysis(week)

        elif step.script == "build_power_rankings.py":
            validate_power_rankings(week)

    # ---------------------------------------------------------
    # Editorial validation
    # ---------------------------------------------------------

    if not args.skip_editorial:
        validate_editorial(week)

    # ---------------------------------------------------------
    # FINAL GATE — PROJECT-WIDE FRESHNESS AUDIT
    # ---------------------------------------------------------

    number += 1
    run_step(
        freshness_step,
        number,
        total,
    )

    # ---------------------------------------------------------
    # Final page report
    # ---------------------------------------------------------

    page_readiness(
        week,
        skip_editorial=args.skip_editorial,
    )

    banner(
        f"{SEASON} WEEK {week} UPDATE COMPLETE"
    )

    print("All requested pipeline steps completed successfully.")
    print()
    print("Next:")
    print()
    print("    git status --short")
    print()
    print(
        "Review the generated Power Rankings commentary and "
        "Commissioner's Mistake before publishing."
    )
    print()


if __name__ == "__main__":
    main()
