from pathlib import Path
import pandas as pd

from team_aliases import canonical_team


DATA_FILE = Path("data/all_matchups_clean_2017_2025.csv")
OUTPUT_DIR = Path("data/history")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(DATA_FILE)

print()
print("=" * 80)
print("BUILDING MALLE'S LEAGUE HISTORY")
print("=" * 80)
print()
print(f"Loaded {len(df)} games.")


# ============================================================
# CLEAN DATA TYPES
# ============================================================

df["year"] = pd.to_numeric(df["year"], errors="coerce")
df["week"] = pd.to_numeric(df["week"], errors="coerce")

df["team_1_score"] = pd.to_numeric(
    df["team_1_score"],
    errors="coerce"
)

df["team_2_score"] = pd.to_numeric(
    df["team_2_score"],
    errors="coerce"
)

df = df.dropna(
    subset=[
        "year",
        "week",
        "team_1",
        "team_2",
        "team_1_score",
        "team_2_score",
    ]
).copy()

df["year"] = df["year"].astype(int)
df["week"] = df["week"].astype(int)


# ============================================================
# APPLY FRANCHISE NAME MAPPING
# ============================================================

df["team_1_original"] = df["team_1"]
df["team_2_original"] = df["team_2"]

df["team_1"] = df["team_1"].apply(canonical_team)
df["team_2"] = df["team_2"].apply(canonical_team)


# ============================================================
# CREATE ONE ROW PER TEAM PER GAME
# ============================================================

team_games = []

for _, row in df.iterrows():

    year = row["year"]
    week = row["week"]

    team1 = row["team_1"]
    team2 = row["team_2"]

    score1 = row["team_1_score"]
    score2 = row["team_2_score"]

    if score1 > score2:
        result1 = "W"
        result2 = "L"

    elif score2 > score1:
        result1 = "L"
        result2 = "W"

    else:
        result1 = "T"
        result2 = "T"

    team_games.append({
        "year": year,
        "week": week,
        "team": team1,
        "opponent": team2,
        "points_for": score1,
        "points_against": score2,
        "result": result1,
        "margin": score1 - score2,
    })

    team_games.append({
        "year": year,
        "week": week,
        "team": team2,
        "opponent": team1,
        "points_for": score2,
        "points_against": score1,
        "result": result2,
        "margin": score2 - score1,
    })


games = pd.DataFrame(team_games)

games = games.sort_values(
    ["year", "week", "team"]
).reset_index(drop=True)


# ============================================================
# ALL-TIME TEAM RECORDS
# ============================================================

records = (
    games
    .groupby("team")
    .agg(
        seasons=("year", "nunique"),
        games=("result", "size"),
        wins=("result", lambda x: (x == "W").sum()),
        losses=("result", lambda x: (x == "L").sum()),
        ties=("result", lambda x: (x == "T").sum()),
        points_for=("points_for", "sum"),
        points_against=("points_against", "sum"),
    )
    .reset_index()
)

records["win_pct"] = (
    (records["wins"] + (records["ties"] * 0.5))
    / records["games"]
)

records["avg_points"] = (
    records["points_for"]
    / records["games"]
)

records["avg_points_against"] = (
    records["points_against"]
    / records["games"]
)

records["point_diff"] = (
    records["points_for"]
    - records["points_against"]
)

records = records.sort_values(
    ["win_pct", "wins"],
    ascending=[False, False]
).reset_index(drop=True)

records.insert(
    0,
    "rank",
    range(1, len(records) + 1)
)


# ============================================================
# HEAD-TO-HEAD RECORDS
# ============================================================

h2h = (
    games
    .groupby(["team", "opponent"])
    .agg(
        games=("result", "size"),
        wins=("result", lambda x: (x == "W").sum()),
        losses=("result", lambda x: (x == "L").sum()),
        ties=("result", lambda x: (x == "T").sum()),
        points_for=("points_for", "sum"),
        points_against=("points_against", "sum"),
    )
    .reset_index()
)

h2h["win_pct"] = (
    (h2h["wins"] + h2h["ties"] * 0.5)
    / h2h["games"]
)

h2h["point_diff"] = (
    h2h["points_for"]
    - h2h["points_against"]
)

h2h = h2h.sort_values(
    ["team", "opponent"]
)


# ============================================================
# SEASON RECORDS
# ============================================================

season_records = (
    games
    .groupby(["year", "team"])
    .agg(
        games=("result", "size"),
        wins=("result", lambda x: (x == "W").sum()),
        losses=("result", lambda x: (x == "L").sum()),
        ties=("result", lambda x: (x == "T").sum()),
        points_for=("points_for", "sum"),
        points_against=("points_against", "sum"),
    )
    .reset_index()
)

season_records["win_pct"] = (
    (season_records["wins"] + season_records["ties"] * 0.5)
    / season_records["games"]
)

season_records["point_diff"] = (
    season_records["points_for"]
    - season_records["points_against"]
)

season_records = season_records.sort_values(
    ["year", "win_pct", "points_for"],
    ascending=[True, False, False]
)


# ============================================================
# SINGLE-GAME RECORDS
# ============================================================

highest_scores = (
    games
    .sort_values(
        "points_for",
        ascending=False
    )
    .head(25)
    [
        [
            "year",
            "week",
            "team",
            "opponent",
            "points_for",
            "points_against",
            "result",
        ]
    ]
)

lowest_scores = (
    games
    .sort_values(
        "points_for",
        ascending=True
    )
    .head(25)
    [
        [
            "year",
            "week",
            "team",
            "opponent",
            "points_for",
            "points_against",
            "result",
        ]
    ]
)


# ============================================================
# UNIQUE GAME VIEW
# ============================================================

unique_games = df.copy()

unique_games["margin"] = (
    unique_games["team_1_score"]
    - unique_games["team_2_score"]
).abs()

unique_games["winner"] = unique_games.apply(
    lambda row:
        row["team_1"]
        if row["team_1_score"] > row["team_2_score"]
        else (
            row["team_2"]
            if row["team_2_score"] > row["team_1_score"]
            else "Tie"
        ),
    axis=1
)

unique_games["loser"] = unique_games.apply(
    lambda row:
        row["team_2"]
        if row["team_1_score"] > row["team_2_score"]
        else (
            row["team_1"]
            if row["team_2_score"] > row["team_1_score"]
            else "Tie"
        ),
    axis=1
)


# ============================================================
# BIGGEST BLOWOUTS
# ============================================================

biggest_blowouts = (
    unique_games
    .sort_values(
        "margin",
        ascending=False
    )
    .head(25)
    [
        [
            "year",
            "week",
            "winner",
            "loser",
            "team_1_score",
            "team_2_score",
            "margin",
        ]
    ]
)


# ============================================================
# CLOSEST GAMES
# ============================================================

closest_games = (
    unique_games
    .sort_values(
        "margin",
        ascending=True
    )
    .head(25)
    [
        [
            "year",
            "week",
            "team_1",
            "team_1_score",
            "team_2",
            "team_2_score",
            "winner",
            "margin",
        ]
    ]
)


# ============================================================
# SAVE EVERYTHING
# ============================================================

games.to_csv(
    OUTPUT_DIR / "team_games.csv",
    index=False
)

records.to_csv(
    OUTPUT_DIR / "all_time_records.csv",
    index=False
)

h2h.to_csv(
    OUTPUT_DIR / "head_to_head.csv",
    index=False
)

season_records.to_csv(
    OUTPUT_DIR / "season_records.csv",
    index=False
)

highest_scores.to_csv(
    OUTPUT_DIR / "highest_scores.csv",
    index=False
)

lowest_scores.to_csv(
    OUTPUT_DIR / "lowest_scores.csv",
    index=False
)

biggest_blowouts.to_csv(
    OUTPUT_DIR / "biggest_blowouts.csv",
    index=False
)

closest_games.to_csv(
    OUTPUT_DIR / "closest_games.csv",
    index=False
)


# ============================================================
# PRINT RESULTS
# ============================================================

print()
print("=" * 80)
print("ALL-TIME REGULAR-SEASON RECORDS")
print("=" * 80)
print()

display_records = records.copy()

display_records["win_pct"] = (
    display_records["win_pct"] * 100
).round(1)

display_records["points_for"] = (
    display_records["points_for"].round(2)
)

display_records["points_against"] = (
    display_records["points_against"].round(2)
)

display_records["avg_points"] = (
    display_records["avg_points"].round(2)
)

display_records["point_diff"] = (
    display_records["point_diff"].round(2)
)

print(
    display_records[
        [
            "rank",
            "team",
            "seasons",
            "games",
            "wins",
            "losses",
            "ties",
            "win_pct",
            "points_for",
            "points_against",
            "point_diff",
            "avg_points",
        ]
    ].to_string(index=False)
)


print()
print("=" * 80)
print("TOP 10 HIGHEST SCORES")
print("=" * 80)
print()

print(
    highest_scores.head(10).to_string(
        index=False
    )
)


print()
print("=" * 80)
print("TOP 10 BIGGEST BLOWOUTS")
print("=" * 80)
print()

print(
    biggest_blowouts.head(10).to_string(
        index=False
    )
)


print()
print("=" * 80)
print("FILES CREATED")
print("=" * 80)

for file in sorted(OUTPUT_DIR.glob("*.csv")):
    print(file)

print()
print("League history build complete.")
