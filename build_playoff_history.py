from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PLAYOFF_DIR = Path("data/playoffs")

INPUT_FILE = PLAYOFF_DIR / "playoff_games.csv"

CHAMPIONSHIPS_FILE = PLAYOFF_DIR / "championships.csv"
PLAYOFF_RECORDS_FILE = PLAYOFF_DIR / "playoff_records.csv"
PLAYOFF_APPEARANCES_FILE = PLAYOFF_DIR / "playoff_appearances.csv"


# ============================================================
# TEAM ALIASES
# ============================================================

try:
    from team_aliases import canonical_team
except ImportError:
    def canonical_team(team):
        return team


# ============================================================
# LOAD DATA
# ============================================================

print()
print("=" * 80)
print("BUILDING PLAYOFF HISTORY")
print("=" * 80)

df = pd.read_csv(INPUT_FILE)

print()
print(f"Loaded {len(df)} playoff games.")


# ============================================================
# CLEAN TEAM NAMES
# ============================================================

for col in [
    "team_1",
    "team_2",
    "winner",
    "loser",
]:
    df[col] = df[col].apply(canonical_team)


# ============================================================
# VALIDATE EXPECTED STRUCTURE
# ============================================================

print()
print("=" * 80)
print("VALIDATING PLAYOFF DATA")
print("=" * 80)

expected_rounds = {
    "Quarterfinal": 2,
    "Semifinal": 2,
    "Championship": 1,
}

validation_errors = []


for year in sorted(df["year"].unique()):

    year_df = df[
        df["year"] == year
    ]

    print()
    print(year)

    for round_name, expected in expected_rounds.items():

        count = len(
            year_df[
                year_df["round"] == round_name
            ]
        )

        status = (
            "OK"
            if count == expected
            else "ERROR"
        )

        print(
            f"  {round_name:15} "
            f"{count} / {expected} [{status}]"
        )

        if count != expected:
            validation_errors.append(
                (
                    year,
                    round_name,
                    count,
                    expected,
                )
            )


if validation_errors:

    print()
    print("=" * 80)
    print("VALIDATION FAILED")
    print("=" * 80)

    for (
        year,
        round_name,
        count,
        expected,
    ) in validation_errors:

        print(
            f"{year} {round_name}: "
            f"found {count}, expected {expected}"
        )

    raise SystemExit(
        "\nFix the playoff data before continuing."
    )


print()
print("All playoff rounds validated successfully.")


# ============================================================
# CHAMPIONSHIP HISTORY
# ============================================================

championship_games = (
    df[
        df["round"] == "Championship"
    ]
    .copy()
    .sort_values("year")
)


championships = pd.DataFrame({
    "year": championship_games["year"],
    "champion": championship_games["winner"],
    "runner_up": championship_games["loser"],
    "champion_score": championship_games["winner_score"],
    "runner_up_score": championship_games["loser_score"],
    "margin": championship_games["margin"],
})


championships.to_csv(
    CHAMPIONSHIPS_FILE,
    index=False,
)


print()
print("=" * 80)
print("CHAMPIONSHIP HISTORY")
print("=" * 80)
print()

print(
    championships.to_string(
        index=False
    )
)


# ============================================================
# BUILD TEAM-GAME FORMAT
# ============================================================

rows = []


for _, game in df.iterrows():

    team_1 = game["team_1"]
    team_2 = game["team_2"]

    score_1 = game["team_1_score"]
    score_2 = game["team_2_score"]

    if score_1 > score_2:
        result_1 = "W"
        result_2 = "L"

    elif score_2 > score_1:
        result_1 = "L"
        result_2 = "W"

    else:
        result_1 = "T"
        result_2 = "T"


    rows.append({
        "year": game["year"],
        "week": game["week"],
        "round": game["round"],
        "team": team_1,
        "opponent": team_2,
        "points_for": score_1,
        "points_against": score_2,
        "result": result_1,
    })


    rows.append({
        "year": game["year"],
        "week": game["week"],
        "round": game["round"],
        "team": team_2,
        "opponent": team_1,
        "points_for": score_2,
        "points_against": score_1,
        "result": result_2,
    })


team_games = pd.DataFrame(rows)


# ============================================================
# PLAYOFF RECORDS
# ============================================================

records = []


for team, team_df in team_games.groupby("team"):

    wins = int(
        (team_df["result"] == "W").sum()
    )

    losses = int(
        (team_df["result"] == "L").sum()
    )

    ties = int(
        (team_df["result"] == "T").sum()
    )

    games = len(team_df)

    win_pct = (
        wins / games
        if games
        else 0
    )

    points_for = (
        team_df["points_for"].sum()
    )

    points_against = (
        team_df["points_against"].sum()
    )


    # Championships
    titles = int(
        (
            championships["champion"]
            == team
        ).sum()
    )


    # Championship appearances
    championship_appearances = int(
        (
            (
                championships["champion"]
                == team
            )
            |
            (
                championships["runner_up"]
                == team
            )
        ).sum()
    )


    runner_ups = (
        championship_appearances
        - titles
    )


    # Semifinal appearances
    semifinal_appearances = (
        team_df[
            team_df["round"]
            == "Semifinal"
        ]["year"]
        .nunique()
    )


    # Quarterfinal appearances
    quarterfinal_appearances = (
        team_df[
            team_df["round"]
            == "Quarterfinal"
        ]["year"]
        .nunique()
    )


    # A first-round bye means a team does not appear
    # in the quarterfinal game data. Anyone who reaches
    # a semifinal still made the playoffs.
    playoff_seasons = (
        team_df["year"]
        .nunique()
    )


    records.append({
        "team": team,
        "playoff_seasons": playoff_seasons,
        "games": games,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_pct": round(
            win_pct * 100,
            1,
        ),
        "points_for": round(
            points_for,
            2,
        ),
        "points_against": round(
            points_against,
            2,
        ),
        "championships": titles,
        "runner_ups": runner_ups,
        "championship_appearances": championship_appearances,
        "semifinal_appearances": semifinal_appearances,
        "quarterfinal_games": quarterfinal_appearances,
    })


playoff_records = pd.DataFrame(
    records
)


playoff_records = (
    playoff_records
    .sort_values(
        [
            "championships",
            "championship_appearances",
            "wins",
            "win_pct",
        ],
        ascending=[
            False,
            False,
            False,
            False,
        ],
    )
    .reset_index(drop=True)
)


playoff_records.insert(
    0,
    "rank",
    range(
        1,
        len(playoff_records) + 1,
    ),
)


playoff_records.to_csv(
    PLAYOFF_RECORDS_FILE,
    index=False,
)


# ============================================================
# PLAYOFF APPEARANCES BY YEAR
# ============================================================

appearance_rows = []


for year in sorted(df["year"].unique()):

    year_df = team_games[
        team_games["year"] == year
    ]

    teams = sorted(
        year_df["team"].unique()
    )

    for team in teams:

        team_year = year_df[
            year_df["team"] == team
        ]

        reached_qf = (
            "Quarterfinal"
            in team_year["round"].values
        )

        reached_sf = (
            "Semifinal"
            in team_year["round"].values
        )

        reached_final = (
            "Championship"
            in team_year["round"].values
        )

        won_title = (
            (
                championships["year"]
                == year
            )
            &
            (
                championships["champion"]
                == team
            )
        ).any()


        if won_title:
            finish = "Champion"

        elif reached_final:
            finish = "Runner-Up"

        elif reached_sf:
            finish = "Semifinal"

        else:
            finish = "Quarterfinal"


        appearance_rows.append({
            "year": year,
            "team": team,
            "finish": finish,
        })


appearances = pd.DataFrame(
    appearance_rows
)


appearances.to_csv(
    PLAYOFF_APPEARANCES_FILE,
    index=False,
)


# ============================================================
# PRINT PLAYOFF LEADERBOARD
# ============================================================

print()
print("=" * 80)
print("ALL-TIME PLAYOFF RECORDS")
print("=" * 80)
print()

columns = [
    "rank",
    "team",
    "playoff_seasons",
    "games",
    "wins",
    "losses",
    "win_pct",
    "championships",
    "runner_ups",
    "championship_appearances",
]

print(
    playoff_records[
        columns
    ].to_string(
        index=False
    )
)


# ============================================================
# TITLE COUNTS
# ============================================================

print()
print("=" * 80)
print("CHAMPIONSHIPS BY FRANCHISE")
print("=" * 80)
print()


title_counts = (
    championships[
        "champion"
    ]
    .value_counts()
    .rename_axis("team")
    .reset_index(
        name="championships"
    )
)


print(
    title_counts.to_string(
        index=False
    )
)


# ============================================================
# FILE SUMMARY
# ============================================================

print()
print("=" * 80)
print("FILES CREATED")
print("=" * 80)

print()
print(CHAMPIONSHIPS_FILE)
print(PLAYOFF_RECORDS_FILE)
print(PLAYOFF_APPEARANCES_FILE)

print()
print("Playoff history build complete.")
