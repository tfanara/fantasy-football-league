from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PLAYER_DIR = BASE_DIR / "data" / "matchups" / "player_week_stats"

LINEUPS_FILE = PLAYER_DIR / "2018_weekly_lineups.csv"
RESCUE_FILE = PLAYER_DIR / "2018_week09_missing_matchup_rescue.csv"

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)

def main():
    lineups = pd.read_csv(LINEUPS_FILE)
    rescue = pd.read_csv(RESCUE_FILE)

    banner("ORIGINAL 2018 STARTER COUNTS BY TEAM/WEEK")

    regular = lineups[lineups["week"].between(1, 13)].copy()

    starter_counts = (
        regular[regular["is_starter"] == True]
        .groupby(["week", "fantasy_team"])
        .size()
        .reset_index(name="starters")
    )

    bad = starter_counts[starter_counts["starters"] != 9].copy()

    if bad.empty:
        print("No abnormal starter counts in original file.")
    else:
        print(bad.to_string(index=False))

        for row in bad.itertuples(index=False):
            banner(f"WEEK {row.week} — {row.fantasy_team}")

            subset = regular[
                (regular["week"] == row.week)
                & (regular["fantasy_team"] == row.fantasy_team)
                & (regular["is_starter"] == True)
            ].copy()

            cols = [
                "matchup_id",
                "side",
                "lineup_slot",
                "player",
                "fantasy_points",
                "team_score",
                "opponent",
            ]

            print(
                subset[
                    [c for c in cols if c in subset.columns]
                ].to_string(index=False)
            )

    banner("RESCUE FILE STARTERS")

    rescue_starters = rescue[
        rescue["is_starter"] == True
    ].copy()

    print(f"Rescue starter rows: {len(rescue_starters)}")

    print(
        rescue_starters[
            [
                c for c in [
                    "side",
                    "fantasy_team",
                    "lineup_slot",
                    "player",
                    "fantasy_points",
                    "team_score",
                    "opponent",
                ]
                if c in rescue_starters.columns
            ]
        ].to_string(index=False)
    )

    banner("EMPTY STARTER ROWS IN ORIGINAL 2018")

    empty_starters = regular[
        (regular["is_starter"] == True)
        & (
            regular["player"]
            .astype(str)
            .str.strip()
            .eq("(Empty)")
        )
    ].copy()

    print(f"Empty starter rows: {len(empty_starters)}")

    if not empty_starters.empty:
        print(
            empty_starters[
                [
                    c for c in [
                        "week",
                        "matchup_id",
                        "fantasy_team",
                        "side",
                        "lineup_slot",
                        "player",
                        "fantasy_points",
                        "team_score",
                        "opponent",
                    ]
                    if c in empty_starters.columns
                ]
            ]
            .sort_values(
                ["week", "fantasy_team", "lineup_slot"]
            )
            .to_string(index=False)
        )

if __name__ == "__main__":
    main()