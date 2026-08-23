from pathlib import Path
import json

import pandas as pd
from pandas.errors import EmptyDataError


DATA_DIR = Path("data")

YEARS = range(2018, 2026)

EXPECTED_MAX_WEEK = {
    2018: 13,
    2019: 13,
    2020: 13,
    2021: 14,
    2022: 14,
    2023: 14,
    2024: 14,
    2025: 14,
}

all_rows = []


def load_csv_if_valid(path):
    if not path.exists():
        print(f"Not found: {path}")
        return None

    if path.stat().st_size == 0:
        print(f"Skipping empty file: {path}")
        return None

    try:
        df = pd.read_csv(path)
    except EmptyDataError:
        print(f"Skipping empty CSV: {path}")
        return None

    if df.empty:
        print(f"Skipping file with no rows: {path}")
        return None

    print(f"Loading: {path} ({len(df)} rows)")
    return df


for year in YEARS:

    print()
    print("=" * 70)
    print(f"PROCESSING {year}")
    print("=" * 70)

    year_dir = DATA_DIR / str(year)

    files_to_check = [
        year_dir / "matchups.csv",
        year_dir / "matchups_manual.csv",
        year_dir / "matchups_week14.csv",
    ]

    season_frames = []

    for file in files_to_check:
        df = load_csv_if_valid(file)

        if df is not None:
            season_frames.append(df)

    if not season_frames:
        print(f"WARNING: No usable matchup data found for {year}")
        continue

    season_df = pd.concat(
        season_frames,
        ignore_index=True,
    )

    # -----------------------------------------------------
    # CLEAN YEAR / WEEK
    # -----------------------------------------------------

    season_df["year"] = pd.to_numeric(
        season_df["year"],
        errors="coerce",
    )

    season_df["week"] = pd.to_numeric(
        season_df["week"],
        errors="coerce",
    )

    season_df = season_df.dropna(
        subset=[
            "year",
            "week",
            "team_1",
            "team_2",
        ]
    )

    season_df["year"] = season_df["year"].astype(int)
    season_df["week"] = season_df["week"].astype(int)

    # -----------------------------------------------------
    # KEEP ONLY CORRECT REGULAR-SEASON WEEKS
    # -----------------------------------------------------

    max_week = EXPECTED_MAX_WEEK[year]

    before = len(season_df)

    season_df = season_df[
        season_df["week"] <= max_week
    ].copy()

    removed = before - len(season_df)

    if removed:
        print(f"Removed {removed} postseason rows.")

    # -----------------------------------------------------
    # DEDUPLICATE
    # -----------------------------------------------------

    season_df["matchup_key"] = season_df.apply(
        lambda row: (
            f"{row['year']}-"
            f"{row['week']}-"
            f"{'|'.join(sorted([
                str(row['team_1']).strip(),
                str(row['team_2']).strip()
            ]))}"
        ),
        axis=1,
    )

    before_dedupe = len(season_df)

    season_df = (
        season_df
        .drop_duplicates(
            subset="matchup_key",
            keep="last",
        )
        .copy()
    )

    duplicates_removed = (
        before_dedupe - len(season_df)
    )

    if duplicates_removed:
        print(
            f"Removed {duplicates_removed} duplicate games."
        )

    season_df = season_df.drop(
        columns=["matchup_key"]
    )

    # -----------------------------------------------------
    # VERIFY WEEK COUNTS
    # -----------------------------------------------------

    weekly_counts = (
        season_df
        .groupby("week")
        .size()
    )

    print()
    print("Games by week:")

    for week in range(1, max_week + 1):

        count = int(
            weekly_counts.get(
                week,
                0,
            )
        )

        status = "OK" if count == 6 else "CHECK"

        print(
            f"  Week {week:2}: "
            f"{count} games [{status}]"
        )

    # -----------------------------------------------------
    # SAVE CLEAN SEASON FILES
    # -----------------------------------------------------

    season_df = season_df.sort_values(
        [
            "week",
            "team_1",
        ]
    )

    clean_csv = (
        year_dir / "matchups_clean.csv"
    )

    clean_json = (
        year_dir / "matchups_clean.json"
    )

    season_df.to_csv(
        clean_csv,
        index=False,
    )

    with open(
        clean_json,
        "w",
    ) as f:

        json.dump(
            season_df.to_dict(
                orient="records"
            ),
            f,
            indent=2,
        )

    expected_games = max_week * 6

    status = (
        "OK"
        if len(season_df) == expected_games
        else "CHECK"
    )

    print()
    print(
        f"{year}: "
        f"{len(season_df)} games "
        f"[{status}]"
    )

    all_rows.append(season_df)


# ---------------------------------------------------------
# MASTER DATASET
# ---------------------------------------------------------

if not all_rows:
    raise RuntimeError(
        "No matchup data found."
    )

master_df = pd.concat(
    all_rows,
    ignore_index=True,
)

master_df = master_df.sort_values(
    [
        "year",
        "week",
        "team_1",
    ]
)


# ---------------------------------------------------------
# SAVE MASTER
# ---------------------------------------------------------

master_csv = (
    DATA_DIR / "all_matchups_clean.csv"
)

master_json = (
    DATA_DIR / "all_matchups_clean.json"
)

master_df.to_csv(
    master_csv,
    index=False,
)

with open(
    master_json,
    "w",
) as f:

    json.dump(
        master_df.to_dict(
            orient="records"
        ),
        f,
        indent=2,
    )


# ---------------------------------------------------------
# FINAL SUMMARY
# ---------------------------------------------------------

print()
print("=" * 70)
print("FINAL MATCHUP DATASET")
print("=" * 70)
print()

for year in YEARS:

    games = len(
        master_df[
            master_df["year"] == year
        ]
    )

    expected = (
        EXPECTED_MAX_WEEK[year] * 6
    )

    status = (
        "OK"
        if games == expected
        else "CHECK"
    )

    print(
        f"{year}: "
        f"{games} / {expected} "
        f"[{status}]"
    )

print()
print(
    f"TOTAL GAMES: {len(master_df)}"
)

print()
print(
    f"Master CSV:  {master_csv}"
)

print(
    f"Master JSON: {master_json}"
)