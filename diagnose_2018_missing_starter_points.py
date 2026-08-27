from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
FILE = (
    BASE_DIR
    / "data"
    / "matchups"
    / "player_week_stats"
    / "2018_weekly_lineups.csv"
)


def main():
    df = pd.read_csv(FILE)

    starters = df[
        df["is_starter"].astype(str).str.lower().isin(["true", "1"])
    ].copy()

    missing = starters[
        pd.to_numeric(
            starters["fantasy_points"],
            errors="coerce",
        ).isna()
    ].copy()

    print()
    print("=" * 96)
    print("2018 STARTERS WITH MISSING FANTASY POINTS")
    print("=" * 96)
    print()
    print(f"Rows found: {len(missing)}")
    print()

    cols = [
        "week",
        "matchup_id",
        "fantasy_team",
        "opponent",
        "side",
        "lineup_slot",
        "player",
        "fantasy_points",
        "team_score",
        "stat_summary",
    ]

    print(
        missing[
            [c for c in cols if c in missing.columns]
        ]
        .sort_values(
            ["week", "fantasy_team", "lineup_slot"]
        )
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()