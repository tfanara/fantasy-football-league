from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

LINEUPS_FILE = (
    BASE_DIR
    / "data"
    / "matchups"
    / "player_week_stats"
    / "all_weekly_lineups_2017_2025.csv"
)

CHAMPIONSHIPS_FILE = (
    BASE_DIR
    / "data"
    / "playoffs"
    / "championships.csv"
)

OUT_DIR = (
    BASE_DIR
    / "data"
    / "playoffs"
)

OUT_FILE = OUT_DIR / "player_championship_pedigree.csv"
DETAIL_FILE = OUT_DIR / "player_championship_rosters.csv"


def banner(text):
    print()
    print("=" * 100)
    print(text)
    print("=" * 100)


def normalize_bool(series):
    if series.dtype == bool:
        return series

    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes"])
    )


def main():
    banner("BUILDING PLAYER CHAMPIONSHIP PEDIGREE")

    if not LINEUPS_FILE.exists():
        raise FileNotFoundError(LINEUPS_FILE)

    if not CHAMPIONSHIPS_FILE.exists():
        raise FileNotFoundError(CHAMPIONSHIPS_FILE)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    lineups = pd.read_csv(LINEUPS_FILE)
    championships = pd.read_csv(CHAMPIONSHIPS_FILE)

    required_lineup = {
        "year",
        "week",
        "fantasy_team",
        "player",
        "lineup_slot",
    }

    missing = required_lineup - set(lineups.columns)

    if missing:
        raise KeyError(
            f"Lineup file missing columns: {sorted(missing)}"
        )

    required_champ = {
        "year",
        "champion",
    }

    missing = required_champ - set(championships.columns)

    if missing:
        raise KeyError(
            f"Championship file missing columns: {sorted(missing)}"
        )

    lineups["year"] = pd.to_numeric(
        lineups["year"],
        errors="raise",
    ).astype(int)

    lineups["week"] = pd.to_numeric(
        lineups["week"],
        errors="raise",
    ).astype(int)

    championships["year"] = pd.to_numeric(
        championships["year"],
        errors="raise",
    ).astype(int)

    # Championship data may include 2017, while weekly player data starts in 2018.
    available_years = set(
        lineups["year"].unique()
    )

    championships = championships[
        championships["year"].isin(
            available_years
        )
    ].copy()

    banner("1. CHAMPIONS")

    print(
        championships[
            ["year", "champion"]
        ]
        .sort_values("year")
        .to_string(index=False)
    )

    roster_rows = []

    for _, champ in championships.iterrows():

        year = int(champ["year"])
        champion = str(
            champ["champion"]
        ).strip()

        team_year = lineups[
            (lineups["year"] == year)
            & (
                lineups["fantasy_team"]
                .astype(str)
                .str.strip()
                .eq(champion)
            )
        ].copy()

        if team_year.empty:
            print(
                f"[WARN] {year}: no weekly lineup rows found for champion "
                f"{champion!r}"
            )
            continue

        final_week = int(
            team_year["week"].max()
        )

        final_roster = team_year[
            team_year["week"] == final_week
        ].copy()

        # Remove empty slots.
        final_roster = final_roster[
            final_roster["player"]
            .astype(str)
            .str.strip()
            .ne("(Empty)")
        ].copy()

        # De-duplicate the same player if Yahoo somehow repeats them.
        final_roster = final_roster.drop_duplicates(
            subset=["player"],
            keep="first",
        )

        print(
            f"[PASS] {year} {champion}: "
            f"{len(final_roster)} players from Week {final_week}"
        )

        for _, row in final_roster.iterrows():

            roster_rows.append({
                "year": year,
                "champion": champion,
                "final_regular_season_week": final_week,
                "player": row["player"],
                "lineup_slot": row["lineup_slot"],
                "was_starter_final_week": (
                    bool(row["is_starter"])
                    if "is_starter" in row.index
                    and not pd.isna(row["is_starter"])
                    else None
                ),
                "fantasy_points_final_week": (
                    row["fantasy_points"]
                    if "fantasy_points" in row.index
                    else None
                ),
            })

    detail = pd.DataFrame(roster_rows)

    if detail.empty:
        raise RuntimeError(
            "No championship roster rows were built."
        )

    banner("2. PLAYER TITLE COUNTS")

    pedigree = (
        detail
        .groupby(
            "player",
            as_index=False,
        )
        .agg(
            championships=(
                "year",
                "nunique",
            ),
            championship_seasons=(
                "year",
                lambda s: ", ".join(
                    str(int(x))
                    for x in sorted(
                        set(s)
                    )
                ),
            ),
            champion_franchises=(
                "champion",
                lambda s: ", ".join(
                    sorted(
                        set(
                            str(x)
                            for x in s
                        )
                    )
                ),
            ),
        )
    )

    pedigree["championship_rank"] = (
        pedigree["championships"]
        .rank(
            method="min",
            ascending=False,
        )
        .astype(int)
    )

    pedigree = pedigree.sort_values(
        [
            "championships",
            "player",
        ],
        ascending=[
            False,
            True,
        ],
    ).reset_index(drop=True)

    print(
        pedigree.head(30).to_string(
            index=False
        )
    )

    banner("3. VALIDATION")

    expected_seasons = championships["year"].nunique()
    captured_seasons = detail["year"].nunique()

    if captured_seasons != expected_seasons:
        raise RuntimeError(
            f"Captured championship rosters for {captured_seasons} seasons, "
            f"expected {expected_seasons}."
        )

    duplicate_rows = detail.duplicated(
        subset=[
            "year",
            "champion",
            "player",
        ],
        keep=False,
    )

    if duplicate_rows.any():
        raise RuntimeError(
            "Duplicate player rows found within a championship roster."
        )

    print(
        f"[PASS] Championship seasons captured: "
        f"{captured_seasons}/{expected_seasons}"
    )
    print(
        "[PASS] No duplicate player rows within a championship roster."
    )

    banner("4. SAVING FILES")

    detail.to_csv(
        DETAIL_FILE,
        index=False,
    )

    pedigree.to_csv(
        OUT_FILE,
        index=False,
    )

    print(DETAIL_FILE)
    print(OUT_FILE)

    banner("CHAMPIONSHIP PEDIGREE BUILD COMPLETE")

    print(
        "NOTE: 'Championship roster' uses the champion's final regular-season "
        "roster because historical playoff-week player lineup data is not "
        "currently available."
    )


if __name__ == "__main__":
    main()