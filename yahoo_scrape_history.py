from pathlib import Path
import json
import pandas as pd
from playwright.sync_api import sync_playwright


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

PROFILE_DIR = Path("yahoo_browser_profile")
DATA_DIR = Path("data")

DATA_DIR.mkdir(exist_ok=True)


# Yahoo league IDs discovered from your Fantasy Profile
league_ids = {
    2018: "941496",
    2019: "322794",
    2020: "510142",
    2021: "410355",
    2022: "854563",
    2023: "684195",
    2024: "673480",
    2025: "637567",
    2026: "742546",
}


# ---------------------------------------------------------
# BUILD LEAGUE URL
# ---------------------------------------------------------

def get_league_url(year, league_id):

    if year == 2026:
        return (
            f"https://football.fantasysports.yahoo.com/"
            f"f1/{league_id}?lhst=stand#leaguehomestandings"
        )

    return (
        f"https://football.fantasysports.yahoo.com/"
        f"{year}/f1/{league_id}"
        f"?lhst=stand#leaguehomestandings"
    )


# ---------------------------------------------------------
# FIND STANDINGS TABLE
# ---------------------------------------------------------

def find_standings_table(page):

    tables = page.locator("table")

    for i in range(tables.count()):

        table = tables.nth(i)

        try:
            text = table.inner_text()

            if (
                "Rank" in text
                and "Team" in text
                and "W-L-T" in text
                and "PF" in text
            ):
                return table

        except Exception:
            pass

    return None


# ---------------------------------------------------------
# PARSE STANDINGS
# ---------------------------------------------------------

def parse_standings(table):

    rows = table.locator("tr")

    standings = []

    for row_number in range(1, rows.count()):

        row = rows.nth(row_number)

        cells = row.locator("th, td")

        values = [
            cells.nth(i).inner_text().strip()
            for i in range(cells.count())
        ]

        if len(values) < 5:
            continue

        # Yahoo's standings table generally begins:
        #
        # Rank | Team | W-L-T | PF | PA
        #
        # Additional columns vary slightly by year.

        record = {
            "rank": values[0],
            "team": values[1],
            "record": values[2],
            "points_for": values[3],
            "points_against": values[4],
        }

        if len(values) > 5:
            record["streak"] = values[5]

        if len(values) > 6:
            record["waiver"] = values[6]

        if len(values) > 7:
            record["moves"] = values[7]

        standings.append(record)

    return standings


# ---------------------------------------------------------
# CLEAN YAHOO TEXT
# ---------------------------------------------------------

def clean_standings(standings):

    for team in standings:

        # Playoff marker
        team["rank"] = (
            team["rank"]
            .replace("*", "")
            .strip()
        )

        # Yahoo sometimes embeds icon characters
        team["team"] = (
            team["team"]
            .replace("", "")
            .strip()
        )

    return standings


# ---------------------------------------------------------
# SCRAPE ALL SEASONS
# ---------------------------------------------------------

with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )

    page = context.pages[0] if context.pages else context.new_page()

    all_standings = []

    for year, league_id in league_ids.items():

        print()
        print("=" * 60)
        print(f"SCRAPING {year}")
        print("=" * 60)

        url = get_league_url(
            year,
            league_id,
        )

        print(url)

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        try:
            page.locator("table").first.wait_for(
                state="visible",
                timeout=30000,
            )

        except Exception:
            print(f"WARNING: No tables loaded for {year}")
            continue


        standings_table = find_standings_table(page)


        if standings_table is None:

            print(
                f"WARNING: Could not find "
                f"standings table for {year}"
            )

            continue


        standings = parse_standings(
            standings_table
        )

        standings = clean_standings(
            standings
        )


        # Add season information
        for team in standings:

            team["year"] = year
            team["league_id"] = league_id

            all_standings.append(
                team.copy()
            )


        # -------------------------------------------------
        # SAVE INDIVIDUAL SEASON
        # -------------------------------------------------

        year_dir = DATA_DIR / str(year)

        year_dir.mkdir(
            exist_ok=True
        )


        json_path = (
            year_dir / "standings.json"
        )

        with open(json_path, "w") as f:

            json.dump(
                standings,
                f,
                indent=2,
            )


        df = pd.DataFrame(
            standings
        )

        csv_path = (
            year_dir / "standings.csv"
        )

        df.to_csv(
            csv_path,
            index=False,
        )


        print()
        print(
            f"Found {len(standings)} teams."
        )

        print(
            df[
                [
                    "rank",
                    "team",
                    "record",
                    "points_for",
                ]
            ].to_string(index=False)
        )


    # -----------------------------------------------------
    # SAVE MASTER HISTORICAL FILE
    # -----------------------------------------------------

    master_json = (
        DATA_DIR / "all_standings.json"
    )

    with open(master_json, "w") as f:

        json.dump(
            all_standings,
            f,
            indent=2,
        )


    master_df = pd.DataFrame(
        all_standings
    )

    master_csv = (
        DATA_DIR / "all_standings.csv"
    )

    master_df.to_csv(
        master_csv,
        index=False,
    )


    print()
    print("=" * 60)
    print("HISTORICAL SCRAPE COMPLETE")
    print("=" * 60)

    print()
    print(
        f"Total standings rows: "
        f"{len(all_standings)}"
    )

    print()
    print(
        f"Master JSON: {master_json}"
    )

    print(
        f"Master CSV:  {master_csv}"
    )

    input(
        "\nPress ENTER to close Yahoo: "
    )

    context.close()