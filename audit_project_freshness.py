from pathlib import Path
import json
import sys

import pandas as pd

from season_config import CURRENT_SEASON


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SEASON = int(CURRENT_SEASON)

FAILURES = []
WARNINGS = []


# ============================================================
# OUTPUT HELPERS
# ============================================================

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def passed(message):
    print(f"[PASS] {message}")


def warn(message):
    WARNINGS.append(message)
    print(f"[WARN] {message}")


def fail(message):
    FAILURES.append(message)
    print(f"[FAIL] {message}")


def numeric(series):
    return pd.to_numeric(series, errors="coerce")


def read_csv(relative_path):
    path = ROOT / relative_path

    if not path.exists():
        fail(f"Missing file: {relative_path}")
        return None

    try:
        return pd.read_csv(path)
    except Exception as exc:
        fail(
            f"Could not read {relative_path}: "
            f"{type(exc).__name__}: {exc}"
        )
        return None


# ============================================================
# DETERMINE AUTHORITATIVE COMPLETED WEEK
# ============================================================

MATCHUPS_PATH = (
    "data/matchups/player_week_stats/all_matchups.csv"
)

matchups = read_csv(MATCHUPS_PATH)

if matchups is None:
    raise SystemExit(1)

required = {
    "year",
    "week",
    "left_team",
    "right_team",
    "left_score",
    "right_score",
}

missing = required - set(matchups.columns)

if missing:
    raise RuntimeError(
        "Canonical matchup data is missing required columns: "
        + ", ".join(sorted(missing))
    )

matchup_years = numeric(matchups["year"])
matchup_weeks = numeric(matchups["week"])

current_matchups = matchups[
    matchup_years.eq(SEASON)
].copy()

if current_matchups.empty:
    raise RuntimeError(
        f"No completed canonical matchups exist for {SEASON}."
    )

valid_weeks = numeric(
    current_matchups["week"]
).dropna()

if valid_weeks.empty:
    raise RuntimeError(
        f"No valid completed matchup weeks exist for {SEASON}."
    )

LATEST_WEEK = int(valid_weeks.max())

passed(
    f"Latest completed week detected from canonical "
    f"matchups: {SEASON} Week {LATEST_WEEK}"
)


# ============================================================
# GENERIC VALIDATORS
# ============================================================

def validate_team_week(
    label,
    path,
    *,
    team_column="fantasy_team",
):
    df = read_csv(path)

    if df is None:
        return

    required = {
        "year",
        "week",
        team_column,
    }

    missing = required - set(df.columns)

    if missing:
        fail(
            f"{label}: missing required columns "
            f"{sorted(missing)}"
        )
        return

    years = numeric(df["year"])
    weeks = numeric(df["week"])

    current = df[
        years.eq(SEASON)
        & weeks.eq(LATEST_WEEK)
    ].copy()

    if current.empty:
        fail(
            f"{label}: no rows for "
            f"{SEASON} Week {LATEST_WEEK}"
        )
        return

    teams = current[team_column].dropna().nunique()

    if teams != 12:
        fail(
            f"{label}: {SEASON} Week {LATEST_WEEK} "
            f"contains {teams} teams; expected 12"
        )
        return

    passed(
        f"{label}: {SEASON} Week {LATEST_WEEK}, "
        "12-team coverage"
    )


def validate_current_season(
    label,
    path,
    *,
    expected_teams=None,
    team_column="team",
):
    df = read_csv(path)

    if df is None:
        return

    if "year" not in df.columns:
        fail(f"{label}: missing year column")
        return

    years = numeric(df["year"])

    current = df[years.eq(SEASON)].copy()

    if current.empty:
        fail(f"{label}: no {SEASON} rows")
        return

    if expected_teams is not None:
        if team_column not in current.columns:
            fail(
                f"{label}: missing {team_column} column"
            )
            return

        teams = current[team_column].dropna().nunique()

        if teams != expected_teams:
            fail(
                f"{label}: contains {teams} {SEASON} teams; "
                f"expected {expected_teams}"
            )
            return

    passed(
        f"{label}: contains current-season {SEASON} data"
    )


def validate_season_games(
    label,
    path,
):
    df = read_csv(path)

    if df is None:
        return

    required = {
        "year",
        "team",
        "games",
    }

    missing = required - set(df.columns)

    if missing:
        fail(
            f"{label}: missing required columns "
            f"{sorted(missing)}"
        )
        return

    years = numeric(df["year"])

    current = df[years.eq(SEASON)].copy()

    if current.empty:
        fail(f"{label}: no {SEASON} rows")
        return

    teams = current["team"].dropna().nunique()

    if teams != 12:
        fail(
            f"{label}: contains {teams} teams; expected 12"
        )
        return

    games = numeric(current["games"])

    if games.isna().any():
        fail(f"{label}: invalid games values")
        return

    if not games.eq(LATEST_WEEK).all():
        found = sorted(
            games.dropna().astype(int).unique().tolist()
        )

        fail(
            f"{label}: season-game horizon {found}; "
            f"expected {LATEST_WEEK}"
        )
        return

    passed(
        f"{label}: 12 teams through "
        f"{LATEST_WEEK} completed game(s)"
    )


# ============================================================
# CORE WEEKLY DATA
# ============================================================

banner("PROJECT DATA FRESHNESS AUDIT")

print(f"Current season:        {SEASON}")
print(f"Latest completed week: {LATEST_WEEK}")


banner("CORE WEEKLY DATA")


# Canonical matchups are one row per game, not one row per team.

week_matchups = current_matchups[
    numeric(current_matchups["week"]).eq(LATEST_WEEK)
].copy()

if len(week_matchups) != 6:
    fail(
        f"Canonical Matchups: {SEASON} Week {LATEST_WEEK} "
        f"contains {len(week_matchups)} games; expected 6"
    )
else:
    teams = set(
        week_matchups["left_team"].dropna().astype(str)
    ) | set(
        week_matchups["right_team"].dropna().astype(str)
    )

    if len(teams) != 12:
        fail(
            f"Canonical Matchups: {SEASON} Week "
            f"{LATEST_WEEK} represents {len(teams)} teams; "
            "expected 12"
        )
    elif (
        week_matchups["left_score"].isna().any()
        or week_matchups["right_score"].isna().any()
    ):
        fail(
            f"Canonical Matchups: {SEASON} Week "
            f"{LATEST_WEEK} contains missing scores"
        )
    else:
        passed(
            f"Canonical Matchups: {SEASON} Week "
            f"{LATEST_WEEK}, 6 completed games / 12 teams"
        )


validate_team_week(
    "Canonical Weekly Lineups",
    "data/matchups/player_week_stats/"
    "all_weekly_lineups.csv",
)


validate_current_season(
    "Standings",
    "data/all_standings.csv",
    expected_teams=12,
    team_column="team",
)

# The website reads data/all_standings.csv rather than the
# season-specific Yahoo file. Merely finding 12 rows labeled
# with the current season is insufficient: stale standings
# from an earlier week would otherwise pass.
#
# Require the page-facing current-season rows to agree with
# the authoritative Yahoo current-season standings.

standings_master = read_csv(
    "data/all_standings.csv"
)

standings_current = read_csv(
    f"data/{SEASON}/standings.csv"
)

if (
    standings_master is not None
    and standings_current is not None
):

    master_year = numeric(
        standings_master["year"]
    )

    master_current = standings_master[
        master_year.eq(SEASON)
    ].copy()

    aliases = {
        "Ginger FC": "Ginger FC 🏆🏆",
        "Ginger FC 🏆🏆": "Ginger FC 🏆🏆",
        "PickUpYourBratsMalle": "ThreatLevelMidnight",
        "Little Red Fournette": "Post Mahomes",
        "Ur The Best Bellows": "Joe Mantegna",
        "You Better Park It": "Buttermilk Puuump",
        "Buttermilk Pump": "Buttermilk Puuump",
    }

    for frame in (
        master_current,
        standings_current,
    ):
        frame["team"] = (
            frame["team"]
            .astype(str)
            .str.strip()
            .replace(aliases)
        )

    compare_columns = [
        "team",
        "record",
        "points_for",
        "points_against",
    ]

    missing_master = [
        col
        for col in compare_columns
        if col not in master_current.columns
    ]

    missing_current = [
        col
        for col in compare_columns
        if col not in standings_current.columns
    ]

    if missing_master or missing_current:

        fail(
            "Standings freshness comparison is missing "
            "required columns."
        )

    master_compare = (
        master_current[compare_columns]
        .sort_values("team")
        .reset_index(drop=True)
    )

    current_compare = (
        standings_current[compare_columns]
        .sort_values("team")
        .reset_index(drop=True)
    )

    for col in (
        "points_for",
        "points_against",
    ):
        master_compare[col] = numeric(
            master_compare[col]
        )

        current_compare[col] = numeric(
            current_compare[col]
        )

    try:

        pd.testing.assert_frame_equal(
            master_compare,
            current_compare,
            check_dtype=False,
            check_exact=False,
            atol=0.001,
            rtol=0.0,
        )

    except AssertionError as exc:

        fail(
            "Home / Standings master is stale relative "
            "to current Yahoo standings. "
            f"{exc}"
        )

    else:

        passed(
            "Page-facing standings exactly match "
            f"Yahoo {SEASON} standings"
        )


validate_current_season(
    "Master Transactions",
    "data/transactions/all_transactions.csv",
)


# Upcoming matchups represent the next scheduled week.

upcoming = read_csv(
    f"data/{SEASON}/upcoming_matchups.csv"
)

if upcoming is not None:
    if upcoming.empty:
        warn("Upcoming Matchups: file is empty")
    else:
        if "week" in upcoming.columns:
            weeks = numeric(upcoming["week"]).dropna()

            if weeks.empty:
                warn(
                    "Upcoming Matchups: no valid week values"
                )
            else:
                upcoming_week = int(weeks.max())

                if upcoming_week < LATEST_WEEK + 1:
                    fail(
                        "Upcoming Matchups: latest scheduled "
                        f"week is {upcoming_week}; expected at "
                        f"least {LATEST_WEEK + 1}"
                    )
                else:
                    passed(
                        "Upcoming Matchups: schedule available "
                        f"through Week {upcoming_week}"
                    )
        else:
            passed(
                "Upcoming Matchups: current-season "
                "schedule file available"
            )


# ============================================================
# WEEKLY ANALYSIS PRODUCTS
# ============================================================

banner("WEEKLY ANALYSIS PRODUCTS")


validate_team_week(
    "Luck",
    "data/matchups/player_week_stats/analysis/"
    "luck_team_week.csv",
)


validate_team_week(
    "Lineup Efficiency",
    "data/matchups/player_week_stats/analysis/"
    "lineup_efficiency_team_week.csv",
)


validate_team_week(
    "Bench Decisions",
    "data/analysis/bench_decisions_team_week.csv",
)


validate_team_week(
    "Bad Beats",
    "data/analysis/bad_beat_team_week.csv",
)


validate_team_week(
    "Positional Edge",
    "data/analysis/positional_edge_team_week.csv",
)


validate_team_week(
    "QB/WR Stack Analysis",
    "data/analysis/qb_wr_stacks.csv",
)


# Schedule Swap is season-grain. The games column is its
# effective freshness horizon.

validate_season_games(
    "Schedule Swap",
    "data/analysis/schedule_swap_season.csv",
)


# ============================================================
# WAIVER VALUE
# ============================================================

banner("WAIVER VALUE")

#
# Waiver Value has two different concepts of freshness:
#
#   1. Acquisition/stint recognition
#   2. Final scored Waiver Value
#
# A current-season acquisition can legitimately have no final
# Waiver Value row yet if it has not produced fantasy points
# during an eligible completed week.
#
# Therefore freshness is validated against waiver_stints.csv,
# not against waiver_value_acquisitions.csv.
#

waiver_stints = read_csv(
    "data/analysis/waiver_stints.csv"
)

waiver_stint_weeks = read_csv(
    "data/analysis/waiver_stint_weeks.csv"
)

waiver_scored = read_csv(
    "data/analysis/waiver_value_acquisitions.csv"
)

if waiver_stints is not None:

    if "year" not in waiver_stints.columns:
        fail("Waiver Value: waiver_stints.csv missing year column")

    else:
        years = numeric(waiver_stints["year"])

        current_stints = waiver_stints[
            years.eq(SEASON)
        ].copy()

        if current_stints.empty:

            warn(
                f"Waiver Value: no qualifying {SEASON} "
                "acquisition stints exist yet."
            )

        else:

            stint_count = len(current_stints)

            # -----------------------------------------------
            # Validate eligible completed-week coverage
            # -----------------------------------------------

            eligible_count = 0

            if waiver_stint_weeks is not None:

                if "year" not in waiver_stint_weeks.columns:
                    fail(
                        "Waiver Value: waiver_stint_weeks.csv "
                        "missing year column"
                    )

                else:
                    stint_week_years = numeric(
                        waiver_stint_weeks["year"]
                    )

                    current_stint_weeks = waiver_stint_weeks[
                        stint_week_years.eq(SEASON)
                    ].copy()

                    eligible_count = len(
                        current_stint_weeks
                    )

                    if "week" in current_stint_weeks.columns:

                        bad_future = current_stint_weeks[
                            numeric(
                                current_stint_weeks["week"]
                            ) > LATEST_WEEK
                        ]

                        if not bad_future.empty:
                            fail(
                                "Waiver Value: stint-week output "
                                "contains future weeks beyond "
                                f"completed Week {LATEST_WEEK}"
                            )

            # -----------------------------------------------
            # Count currently scored acquisitions
            # -----------------------------------------------

            scored_count = 0

            if (
                waiver_scored is not None
                and "year" in waiver_scored.columns
            ):
                scored_years = numeric(
                    waiver_scored["year"]
                )

                scored_count = len(
                    waiver_scored[
                        scored_years.eq(SEASON)
                    ]
                )

            passed(
                f"Waiver Value: {stint_count} qualifying "
                f"{SEASON} acquisition stint(s); "
                f"{eligible_count} stint-week(s) eligible "
                f"through Week {LATEST_WEEK}; "
                f"{scored_count} currently scored acquisition(s)"
            )

# ============================================================
# PAGE DATA
# ============================================================

banner("PAGE DATA")


validate_current_season(
    "Home / Standings",
    "data/all_standings.csv",
    expected_teams=12,
    team_column="team",
)


validate_team_week(
    "Records / History / Teams",
    "data/history/team_games.csv",
    team_column="team",
)


validate_current_season(
    "Draft",
    "data/drafts/all_drafts.csv",
)


# Keeper history is event-driven rather than weekly.
# A keeper season may not exist until keepers are declared /
# finalized and the keeper builder is run.

keepers = read_csv(
    "data/keepers/keeper_history.csv"
)

if keepers is not None:

    if "year" not in keepers.columns:
        fail("Keepers: missing year column")

    else:
        keeper_years = numeric(keepers["year"]).dropna()

        if keeper_years.empty:
            warn("Keepers: no valid season values")
        else:
            keeper_latest = int(keeper_years.max())

            if keeper_latest >= SEASON:
                passed(
                    f"Keepers: current through {keeper_latest}"
                )
            else:
                warn(
                    f"Keepers: latest finalized keeper "
                    f"history is {keeper_latest}. "
                    "Keeper history is event-driven and "
                    "does not block weekly updates."
                )


# ============================================================
# POWER RANKINGS
# ============================================================

power = read_csv(
    "data/analysis/power_rankings_weekly.csv"
)

if power is not None:

    required = {
        "year",
        "through_week",
        "fantasy_team",
        "power_rank",
    }

    missing = required - set(power.columns)

    if missing:
        fail(
            "Power Rankings: missing required columns "
            f"{sorted(missing)}"
        )

    else:
        years = numeric(power["year"])
        weeks = numeric(power["through_week"])

        current = power[
            years.eq(SEASON)
            & weeks.eq(LATEST_WEEK)
        ].copy()

        teams = current[
            "fantasy_team"
        ].dropna().nunique()

        ranks = sorted(
            numeric(current["power_rank"])
            .dropna()
            .astype(int)
            .tolist()
        )

        if teams != 12:
            fail(
                "Power Rankings: expected 12 teams for "
                f"{SEASON} Week {LATEST_WEEK}"
            )

        elif ranks != list(range(1, 13)):
            fail(
                "Power Rankings: expected exactly "
                "ranks 1-12"
            )

        else:
            passed(
                f"Power Rankings: {SEASON} Week "
                f"{LATEST_WEEK}, 12 teams / ranks 1-12"
            )


# ============================================================
# WEEKLY NEWS INTELLIGENCE
# ============================================================

news_path = (
    DATA
    / "news"
    / str(SEASON)
    / f"week_{LATEST_WEEK:02d}_context.json"
)

if not news_path.exists():

    fail(
        "Weekly News Context: missing "
        f"{news_path.relative_to(ROOT)}"
    )

else:

    try:
        payload = json.loads(
            news_path.read_text(encoding="utf-8")
        )

        if int(payload.get("season", -1)) != SEASON:
            fail(
                "Weekly News Context: wrong season"
            )

        elif int(payload.get("week", -1)) != LATEST_WEEK:
            fail(
                "Weekly News Context: wrong week"
            )

        else:
            matchups_payload = payload.get(
                "matchups",
                [],
            )

            if len(matchups_payload) != 6:
                fail(
                    "Weekly News Context: expected "
                    "6 matchup stories"
                )
            else:
                passed(
                    f"Weekly News Context: {SEASON} "
                    f"Week {LATEST_WEEK}, 6 matchups"
                )

    except Exception as exc:
        fail(
            "Weekly News Context: invalid JSON: "
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================
# EDITORIAL
# ============================================================

banner("EDITORIAL / EVENT-DRIVEN")


article_path = (
    DATA
    / "news"
    / str(SEASON)
    / f"week_{LATEST_WEEK:02d}_article.json"
)

if article_path.exists():
    passed(
        f"Commissioner's Mistake: article exists for "
        f"{SEASON} Week {LATEST_WEEK}"
    )
else:
    warn(
        f"Commissioner's Mistake: no article exists for "
        f"{SEASON} Week {LATEST_WEEK}. Editorial generation "
        "may have been intentionally skipped."
    )


# ============================================================
# FINAL RESULT
# ============================================================

banner("AUDIT RESULT")


if WARNINGS:

    print()
    print("Non-blocking warnings:")

    for message in WARNINGS:
        print(f"  - {message}")


if FAILURES:

    print()
    print("Blocking failures:")

    for message in FAILURES:
        print(f"  - {message}")

    print()
    print(
        f"PROJECT FRESHNESS AUDIT FAILED "
        f"({len(FAILURES)} blocking failure(s), "
        f"{len(WARNINGS)} warning(s))"
    )

    sys.exit(1)


print()
print("PROJECT FRESHNESS AUDIT PASSED")

print(
    f"All deterministic weekly production data is "
    f"current through {SEASON} Week {LATEST_WEEK}."
)

if WARNINGS:
    print(
        f"{len(WARNINGS)} non-blocking event-driven/"
        "editorial warning(s) remain."
    )

sys.exit(0)
