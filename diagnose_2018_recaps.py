from pathlib import Path
import pandas as pd
import re

YEAR = 2018

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "matchups" / "player_week_stats"

LINEUPS_FILE = DATA_DIR / f"{YEAR}_weekly_lineups.csv"
MATCHUPS_FILE = DATA_DIR / f"{YEAR}_matchups.csv"

RECAP_RE = re.compile(r"^Week\\s+\\d+\\s+Recap\\s+\\((Won|Lost)\\)$", re.IGNORECASE)

def banner(title):
    print()
    print("=" * 96)
    print(title)
    print("=" * 96)

def is_recap(value):
    return bool(RECAP_RE.match(str(value).strip()))

def main():
    lineups = pd.read_csv(LINEUPS_FILE)
    matchups = pd.read_csv(MATCHUPS_FILE)

    banner("2018 RECAP-LABEL DIAGNOSTIC")

    bad_matchups = matchups[
        matchups["left_team"].map(is_recap)
        | matchups["right_team"].map(is_recap)
    ].copy()

    print(f"Matchup rows containing a recap label: {len(bad_matchups)}")

    if not bad_matchups.empty:
        print()
        print(
            bad_matchups[
                [
                    "week",
                    "matchup_id",
                    "matchup_number",
                    "yahoo_team_id_used",
                    "left_team",
                    "right_team",
                    "left_score",
                    "right_score",
                    "player_records",
                ]
            ]
            .sort_values(["week", "matchup_id"])
            .to_string(index=False)
        )

    banner("RECAP-LABELED LINEUP ROWS")

    bad_lineups = lineups[
        lineups["fantasy_team"].map(is_recap)
        | lineups["opponent"].map(is_recap)
    ].copy()

    print(f"Lineup rows involving recap labels: {len(bad_lineups)}")

    if not bad_lineups.empty:
        summary = (
            bad_lineups.groupby(
                ["week", "matchup_id", "fantasy_team", "opponent"],
                dropna=False,
            )
            .agg(
                rows=("player", "size"),
                starters=("is_starter", "sum"),
                bench=("is_bench", "sum"),
                ir=("is_ir", "sum"),
                team_score=("team_score", "first"),
                opponent_score=("opponent_score", "first"),
            )
            .reset_index()
            .sort_values(["week", "matchup_id", "fantasy_team"])
        )
        print()
        print(summary.to_string(index=False))

    banner("ALL MATCHUPS IN AFFECTED WEEKS")

    affected_weeks = sorted(
        set(
            bad_matchups["week"]
            .dropna()
            .astype(int)
            .tolist()
        )
    )

    print(f"Affected weeks: {affected_weeks}")

    for week in affected_weeks:
        print()
        print("-" * 96)
        print(f"WEEK {week}")
        print("-" * 96)

        week_matchups = matchups[matchups["week"] == week].copy()

        print(
            week_matchups[
                [
                    "matchup_id",
                    "yahoo_team_id_used",
                    "left_team",
                    "right_team",
                    "left_score",
                    "right_score",
                ]
            ]
            .sort_values("matchup_id")
            .to_string(index=False)
        )

    banner("POSSIBLE DUPLICATE SCORES")

    score_pairs = matchups.copy()

    score_pairs["score_key"] = score_pairs.apply(
        lambda row: tuple(
            sorted(
                [
                    round(float(row["left_score"]), 2),
                    round(float(row["right_score"]), 2),
                ]
            )
        ),
        axis=1,
    )

    duplicates = (
        score_pairs.groupby(["week", "score_key"], dropna=False)
        .filter(lambda g: len(g) > 1)
        .sort_values(["week", "score_key"])
    )

    if duplicates.empty:
        print("No repeated score pairs found.")
    else:
        print(
            duplicates[
                [
                    "week",
                    "matchup_id",
                    "left_team",
                    "right_team",
                    "left_score",
                    "right_score",
                    "score_key",
                ]
            ]
            .to_string(index=False)
        )

    banner("NEXT")
    print(
        "Send me this output. I will determine whether the recap-labeled rows "
        "can simply be removed as duplicate Yahoo views or whether a real team "
        "name needs to be restored before cleaning the 2018 files."
    )

if __name__ == "__main__":
    main()