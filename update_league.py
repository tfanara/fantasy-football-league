"""
Project-wide update orchestrator for the fantasy league website.

Purpose
-------
Give routine maintenance one entry point and one PASS/FAIL summary.

This script intentionally does NOT guess how to drive authenticated Yahoo
browser collectors. Collection remains an explicit upstream step until each
collector has a stable non-interactive CLI.

Normal weekly use:
    1. Collect/update current Yahoo standings, matchups, transactions, and
       player-week lineups as appropriate.
    2. Run:
           python update_league.py --weekly
    3. Run the site locally and spot-check affected pages.
    4. Stage only intended files.

The task registry is deliberately declarative so builders can be added or
renamed in one place instead of duplicating update logic across shell notes.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from season_config import (
    CURRENT_SEASON,
    CURRENT_SEASON_PHASE,
    LAST_COMPLETED_SEASON,
    YAHOO_LEAGUE_IDS,
    detect_latest_completed_week,
    print_season_config,
)


ROOT = Path(__file__).resolve().parent

FROZEN_MATCHUP_BASE = ROOT / "data" / "all_matchups_clean_2017_2025.csv"
MATCHUP_CANDIDATES = [
    ROOT / "data" / f"all_matchups_clean_2017_{CURRENT_SEASON}.csv",
    ROOT / "data" / "all_matchups_clean.csv",
    FROZEN_MATCHUP_BASE,
]

STANDINGS_MASTER = ROOT / "data" / "all_standings.csv"
CURRENT_STANDINGS = ROOT / "data" / str(CURRENT_SEASON) / "standings.csv"


@dataclass(frozen=True)
class Task:
    label: str
    script: str
    horizon: str
    required: bool = True


# The dependency order matters.
SOURCE_TASKS = [
    Task("Merge authoritative matchups", "merge_matchups.py", "weekly-source"),
    Task("League history / records / streaks / H2H", "build_league_history.py", "weekly-source"),
    Task("Master weekly player data", "build_master_weekly_data.py", "weekly-source"),
]

WEEKLY_ANALYTIC_TASKS = [
    Task("Lineup Efficiency", "build_lineup_efficiency.py", "weekly"),
    Task("Luck", "build_luck_metrics.py", "weekly"),
    Task("Bad Beats", "build_bad_beat_analysis.py", "weekly"),
    Task("Schedule Swap", "build_schedule_swap_analysis.py", "weekly", required=False),
    Task("Waiver Value", "build_waiver_value_analysis.py", "weekly"),
    Task("QB/WR Stacks", "build_stack_analysis.py", "weekly", required=False),
    Task("Positional Edge", "build_positional_edge_analysis.py", "weekly", required=False),
]

SEASON_FINAL_TASKS = [
    Task("Championship DNA", "build_championship_dna.py", "season-final"),
    Task("Management Index", "build_manager_skill_analysis.py", "season-final"),
    Task(
        "Player Championship Pedigree",
        "build_player_championship_pedigree.py",
        "season-final",
        required=False,
    ),
]

DRAFT_TASKS = [
    Task("Draft position enrichment", "enrich_draft_positions.py", "draft"),
    Task("Draft position strategy", "build_draft_position_strategy.py", "draft"),
    Task("Draft Value", "build_draft_value_analysis.py", "draft-outcome"),
]


def _has_frozen_baseline(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        df = pd.read_csv(path, usecols=["year"])
        years = pd.to_numeric(df["year"], errors="coerce")
        historical = years.between(2017, 2025)
        return int(historical.sum()) == 732
    except Exception:
        return False


def find_matchup_source() -> Path | None:
    # Never let a stale/incomplete convenience file outrank the audited
    # 732-game historical baseline. Current snapshots are eligible only after
    # they prove they still contain that complete frozen history.
    for path in MATCHUP_CANDIDATES:
        if _has_frozen_baseline(path):
            return path
    return None


def current_week_state():
    source = find_matchup_source()

    if source is None:
        return None, None

    matchups = pd.read_csv(source)

    state = detect_latest_completed_week(matchups)

    return source, state


def rebuild_standings_master(*, dry_run: bool) -> tuple[str, str]:
    label = "Standings master"

    if dry_run:
        return "PLAN", (
            f"{label}: replace {CURRENT_SEASON} rows in data/all_standings.csv "
            f"from data/{CURRENT_SEASON}/standings.csv"
        )

    if not STANDINGS_MASTER.exists():
        return "FAIL", f"{label}: {STANDINGS_MASTER.relative_to(ROOT)} not found"

    if not CURRENT_STANDINGS.exists():
        return "FAIL", f"{label}: {CURRENT_STANDINGS.relative_to(ROOT)} not found"

    try:
        master = pd.read_csv(STANDINGS_MASTER)
        current = pd.read_csv(CURRENT_STANDINGS)

        if "year" not in master.columns:
            raise RuntimeError("master standings are missing the year column")

        required_current = {
            "team", "record", "points_for", "points_against",
        }
        missing = sorted(required_current - set(current.columns))
        if missing:
            raise RuntimeError(
                "current standings are missing columns: " + ", ".join(missing)
            )

        master["year"] = pd.to_numeric(master["year"], errors="coerce")
        historical = master[master["year"] != CURRENT_SEASON].copy()

        if len(current) != 12:
            raise RuntimeError(
                f"{CURRENT_SEASON} standings returned {len(current)} rows; expected 12"
            )

        current["team"] = (
            current["team"]
            .astype(str)
            .str.replace("🏆", "", regex=False)
            .str.replace("", "", regex=False)
            .str.strip()
        )

        aliases = {
            "PickUpYourBratsMalle": "ThreatLevelMidnight",
            "Little Red Fournette": "Post Mahomes",
            "Ur The Best Bellows": "Joe Mantegna",
            "You Better Park It": "Buttermilk Puuump",
            "Buttermilk Pump": "Buttermilk Puuump",
        }
        current["team"] = current["team"].replace(aliases)

        if current["team"].nunique() != 12:
            raise RuntimeError(
                f"{CURRENT_SEASON} standings do not contain 12 unique canonical teams"
            )

        current["year"] = CURRENT_SEASON
        current["league_id"] = YAHOO_LEAGUE_IDS[CURRENT_SEASON]

        # Cross-check Yahoo standings against the freshly rebuilt canonical
        # matchup horizon. During the regular season, every franchise should
        # have exactly one decision per completed fantasy week.
        matchup_source, weekly_state = current_week_state()
        if weekly_state is None:
            raise RuntimeError(
                "cannot validate current standings without an authoritative matchup source"
            )

        expected_games = int(weekly_state.latest_completed_week or 0)

        record_parts = (
            current["record"]
            .astype(str)
            .str.extract(r"^\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*$")
        )
        if record_parts.isna().any().any():
            bad_records = current.loc[
                record_parts.isna().any(axis=1), ["team", "record"]
            ].to_dict("records")
            raise RuntimeError(
                f"could not parse current standings records: {bad_records}"
            )

        games_played = record_parts.astype(int).sum(axis=1)
        if not games_played.eq(expected_games).all():
            bad = current.loc[
                ~games_played.eq(expected_games), ["team", "record"]
            ].copy()
            raise RuntimeError(
                f"{CURRENT_SEASON} standings do not match completed matchup "
                f"horizon Week {expected_games}: {bad.to_dict('records')}"
            )

        rebuilt = pd.concat(
            [historical, current],
            ignore_index=True,
            sort=False,
        )

        if len(rebuilt) != len(master):
            raise RuntimeError(
                f"master row count changed unexpectedly: {len(master)} -> {len(rebuilt)}"
            )

        # Frozen completed-season standings must survive byte-for-value at the
        # dataframe level: same rows and same values before the current season.
        historical_after = rebuilt[rebuilt["year"] != CURRENT_SEASON].copy()
        pd.testing.assert_frame_equal(
            historical.reset_index(drop=True),
            historical_after.reset_index(drop=True),
            check_dtype=False,
        )

        rebuilt.to_csv(STANDINGS_MASTER, index=False)

    except Exception as exc:
        return "FAIL", f"{label}: {exc}"

    return (
        "PASS",
        f"{label}: preserved {len(historical)} historical rows; "
        f"loaded 12 rows for {CURRENT_SEASON}",
    )


def run_task(task: Task, *, dry_run: bool) -> tuple[str, str]:
    script = ROOT / task.script

    if not script.exists():
        status = "MISSING" if task.required else "SKIP"
        return status, f"{task.label}: {task.script} not found"

    if dry_run:
        return "PLAN", f"{task.label}: python {task.script}"

    print()
    print("=" * 88)
    print(f"RUNNING — {task.label}")
    print("=" * 88)

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        check=False,
    )

    if result.returncode != 0:
        return "FAIL", f"{task.label}: exit code {result.returncode}"

    return "PASS", task.label


def run_group(
    title: str,
    tasks: Iterable[Task],
    *,
    dry_run: bool,
) -> list[tuple[str, str]]:
    print()
    print("#" * 88)
    print(title)
    print("#" * 88)

    results = []
    for task in tasks:
        status, detail = run_task(task, dry_run=dry_run)
        results.append((status, detail))
        print(f"{status:>7} — {detail}")

        if status == "FAIL":
            break
        if status == "MISSING" and task.required:
            break

    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources",
        action="store_true",
        help="Rebuild only the authoritative weekly source layer.",
    )
    parser.add_argument(
        "--weekly",
        action="store_true",
        help="Rebuild weekly-current source layer and analytics.",
    )
    parser.add_argument(
        "--season-final",
        action="store_true",
        help="Rebuild analyses that require a completed season.",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="Rebuild draft-side analytics.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run without executing builders.",
    )
    args = parser.parse_args()

    if not any([args.sources, args.weekly, args.season_final, args.draft]):
        parser.error("Choose --sources, --weekly, --season-final, or --draft.")

    print("=" * 88)
    print("FANTASY FOOTBALL PROJECT UPDATE")
    print("=" * 88)

    matchup_source, weekly_state = current_week_state()

    if weekly_state is not None:
        print_season_config(weekly_state)
        print(f"Matchup source: {matchup_source}")
        print(
            "Detected weekly horizon: "
            + (
                f"{CURRENT_SEASON} Week {weekly_state.latest_completed_week}"
                if weekly_state.latest_completed_week
                else f"no completed {CURRENT_SEASON} regular-season weeks"
            )
        )
    else:
        print_season_config()
        print("Matchup source: not found; weekly-state detection unavailable.")

    all_results = []

    if args.sources or args.weekly:
        source_results = run_group(
            "WEEKLY SOURCE LAYER",
            SOURCE_TASKS,
            dry_run=args.dry_run,
        )
        all_results.extend(source_results)

        source_failed = any(
            status in {"FAIL", "MISSING"}
            for status, _ in source_results
        )
        if source_failed:
            print("\nUPDATE FAILED / INCOMPLETE")
            return 1

        status, detail = rebuild_standings_master(dry_run=args.dry_run)
        all_results.append((status, detail))
        print()
        print("#" * 88)
        print("STANDINGS SOURCE LAYER")
        print("#" * 88)
        print(f"{status:>7} — {detail}")

        if status == "FAIL":
            print("\nUPDATE FAILED / INCOMPLETE")
            return 1

    if args.weekly:
        # Re-read the horizon after merge_matchups.py has rebuilt the
        # canonical matchup master.
        matchup_source, weekly_state = current_week_state()
        if weekly_state is None:
            print(
                "\nFAIL — weekly update requires an authoritative matchup source."
            )
            return 1

        print(
            "Validated post-merge weekly horizon: "
            + (
                f"{CURRENT_SEASON} Week {weekly_state.latest_completed_week}"
                if weekly_state.latest_completed_week
                else f"no completed {CURRENT_SEASON} regular-season weeks"
            )
        )

        all_results.extend(
            run_group(
                "WEEKLY-CURRENT ANALYTICS",
                WEEKLY_ANALYTIC_TASKS,
                dry_run=args.dry_run,
            )
        )

    if args.season_final:
        if CURRENT_SEASON_PHASE != "complete":
            print(
                "\nSKIP — season-final builders are gated until "
                "CURRENT_SEASON_PHASE='complete'."
            )
        else:
            all_results.extend(
                run_group(
                    "SEASON-FINAL BUILDERS",
                    SEASON_FINAL_TASKS,
                    dry_run=args.dry_run,
                )
            )

    if args.draft:
        all_results.extend(
            run_group(
                "DRAFT BUILDERS",
                DRAFT_TASKS,
                dry_run=args.dry_run,
            )
        )

    print()
    print("=" * 88)
    print("UPDATE SUMMARY")
    print("=" * 88)

    for status, detail in all_results:
        print(f"{status:>7} — {detail}")

    hard_fail = any(
        status in {"FAIL", "MISSING"}
        for status, _ in all_results
    )

    if hard_fail:
        print("\nUPDATE FAILED / INCOMPLETE")
        return 1

    print("\nUPDATE COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())