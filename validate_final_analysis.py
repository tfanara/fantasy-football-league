from pathlib import Path
import re
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data" / "matchups" / "player_week_stats"
ANALYSIS_DIR = DATA_DIR / "analysis"

LINEUPS = DATA_DIR / "all_weekly_lineups_2017_2025.csv"
MATCHUPS = DATA_DIR / "all_matchups_2017_2025.csv"
TEAM_WEEK = ANALYSIS_DIR / "lineup_efficiency_team_week.csv"
SEASON = ANALYSIS_DIR / "lineup_efficiency_season.csv"
ALL_TIME = ANALYSIS_DIR / "lineup_efficiency_all_time.csv"

RECAP_RE = re.compile(r"Recap\s+\((?:Won|Lost)\)", re.I)


def banner(text):
    print()
    print("=" * 96)
    print(text)
    print("=" * 96)


def fail(msg):
    raise RuntimeError(msg)


def has_recap(series):
    return series.astype(str).str.contains(RECAP_RE, na=False)


def main():
    banner("FINAL HISTORICAL ANALYSIS VALIDATION")

    for path in [LINEUPS, MATCHUPS, TEAM_WEEK, SEASON, ALL_TIME]:
        if not path.exists():
            fail(f"Missing file: {path}")

    lineups = pd.read_csv(LINEUPS)
    matchups = pd.read_csv(MATCHUPS)
    team_week = pd.read_csv(TEAM_WEEK)
    season = pd.read_csv(SEASON)
    all_time = pd.read_csv(ALL_TIME)

    banner("1. MASTER DATASET COUNTS")

    if len(matchups) != 732:
        fail(f"Expected 732 matchups, found {len(matchups)}")

    if team_week.shape[0] != 1464:
        fail(f"Expected 1,464 efficiency team-weeks, found {len(team_week)}")

    print(f"[PASS] Matchups: {len(matchups):,}")
    print(f"[PASS] Efficiency team-weeks: {len(team_week):,}")
    print(f"[PASS] Master lineup rows: {len(lineups):,}")

    banner("2. RECAP LABEL CHECK")

    recap_hits = []

    checks = [
        ("lineups.fantasy_team", lineups, "fantasy_team"),
        ("lineups.opponent", lineups, "opponent"),
        ("matchups.left_team", matchups, "left_team"),
        ("matchups.right_team", matchups, "right_team"),
        ("team_week.fantasy_team", team_week, "fantasy_team"),
        ("team_week.opponent", team_week, "opponent"),
        ("season.fantasy_team", season, "fantasy_team"),
        ("all_time.fantasy_team", all_time, "fantasy_team"),
    ]

    for label, df, col in checks:
        if col not in df.columns:
            continue
        count = int(has_recap(df[col]).sum())
        print(f"{label}: {count}")
        if count:
            recap_hits.append((label, count))

    if recap_hits:
        fail(f"Recap pseudo-team labels still remain: {recap_hits}")

    print("[PASS] Zero Recap pseudo-team labels remain.")

    banner("3. TEAM-WEEK STRUCTURE")

    team_counts = (
        lineups.groupby(["year", "week"])["fantasy_team"]
        .nunique()
        .reset_index(name="teams")
    )

    bad = team_counts[team_counts["teams"] != 12]
    if not bad.empty:
        print(bad.to_string(index=False))
        fail("At least one season-week does not contain 12 teams.")

    print(f"[PASS] All {len(team_counts)} season-weeks contain 12 teams.")

    banner("4. LINEUP EFFICIENCY SANITY")

    if (team_week["points_left_on_bench"] < -0.011).any():
        bad = team_week[team_week["points_left_on_bench"] < -0.011]
        print(bad.to_string(index=False))
        fail("Negative points-left-on-bench values found.")

    if ((team_week["lineup_efficiency_pct"] < 0) |
        (team_week["lineup_efficiency_pct"] > 100.011)).any():
        fail("Lineup efficiency outside 0-100% found.")

    print("[PASS] No negative points-left-on-bench values.")
    print("[PASS] Lineup efficiency values are within 0-100%.")

    banner("5. SEASON SUMMARY SHAPE")

    expected_by_year = {
        2017: 12,
        2018: 12,
        2019: 12,
        2020: 12,
        2021: 12,
        2022: 12,
        2023: 12,
        2024: 12,
        2025: 12,
    }

    season_counts = season.groupby("year")["fantasy_team"].nunique()

    for year, expected in expected_by_year.items():
        found = int(season_counts.get(year, 0))
        if found != expected:
            fail(f"{year}: expected 12 teams in season summary, found {found}")
        print(f"[PASS] {year}: 12 teams")

    banner("6. TOP / BOTTOM ALL-TIME EFFICIENCY")

    display_cols = [
        c for c in [
            "fantasy_team",
            "team_weeks",
            "all_time_efficiency_pct",
            "points_left_on_bench",
            "avg_weekly_points_left",
            "efficiency_rank",
        ]
        if c in all_time.columns
    ]

    ordered = all_time.sort_values(
        ["efficiency_rank", "fantasy_team"]
        if "efficiency_rank" in all_time.columns
        else ["all_time_efficiency_pct"],
        ascending=True,
    )

    print(ordered[display_cols].to_string(index=False))

    banner("FINAL RESULT")
    print("FINAL ANALYSIS VALIDATION PASSED.")
    print("The historical lineup-efficiency data is ready for Streamlit.")


if __name__ == "__main__":
    main()