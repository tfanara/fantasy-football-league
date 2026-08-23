from pathlib import Path
import json

import pandas as pd
from playwright.sync_api import sync_playwright


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

LEAGUE_ID = "742546"

LEAGUE_URL = (
    f"https://football.fantasysports.yahoo.com/"
    f"f1/{LEAGUE_ID}?lhst=stand#leaguehomestandings"
)

PROFILE_DIR = Path("yahoo_browser_profile")
DATA_DIR = Path("data")

DATA_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------
# OPEN YAHOO
# ---------------------------------------------------------

with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )

    page = context.pages[0] if context.pages else context.new_page()

    print()
    print("Opening Yahoo league standings...")

    page.goto(
        LEAGUE_URL,
        wait_until="domcontentloaded",
    )

    # Wait for Yahoo to render the standings table
    page.locator("table").first.wait_for(
        state="visible",
        timeout=30000,
    )

    print("Page title:")
    print(page.title())

    print()


    # -----------------------------------------------------
    # FIND STANDINGS TABLE
    # -----------------------------------------------------

    tables = page.locator("table")

    print(f"Found {tables.count()} tables.")

    standings_table = None

    for i in range(tables.count()):

        table = tables.nth(i)
        text = table.inner_text()

        if (
            "Rank" in text
            and "Team" in text
            and "W-L-T" in text
            and "PF" in text
        ):
            standings_table = table
            break


    if standings_table is None:
        raise RuntimeError(
            "Could not find Yahoo standings table."
        )


    # -----------------------------------------------------
    # READ TABLE
    # -----------------------------------------------------

    rows = standings_table.locator("tr")

    standings = []

    for row_number in range(1, rows.count()):

        row = rows.nth(row_number)

        cells = row.locator("th, td")

        values = [
            cells.nth(i).inner_text().strip()
            for i in range(cells.count())
        ]

        if len(values) < 8:
            continue

        standings.append(
            {
                "rank": values[0],
                "team": values[1],
                "record": values[2],
                "points_for": values[3],
                "points_against": values[4],
                "streak": values[5],
                "waiver": values[6],
                "moves": values[7],
            }
        )


    # -----------------------------------------------------
    # CLEAN DATA
    # -----------------------------------------------------

    for team in standings:

        # Remove Yahoo playoff marker
        team["rank"] = (
            team["rank"]
            .replace("*", "")
            .strip()
        )

        # Yahoo sometimes includes odd icon characters
        team["team"] = (
            team["team"]
            .replace("", "")
            .strip()
        )


    # -----------------------------------------------------
    # SAVE JSON
    # -----------------------------------------------------

    json_path = DATA_DIR / "standings_2025.json"

    with open(json_path, "w") as f:
        json.dump(
            standings,
            f,
            indent=2,
        )


    # -----------------------------------------------------
    # SAVE CSV
    # -----------------------------------------------------

    df = pd.DataFrame(standings)

    csv_path = DATA_DIR / "standings_2025.csv"

    df.to_csv(
        csv_path,
        index=False,
    )


    # -----------------------------------------------------
    # DISPLAY RESULT
    # -----------------------------------------------------

    print()
    print("=" * 60)
    print("2025 STANDINGS")
    print("=" * 60)

    print(df.to_string(index=False))

    print()
    print(f"Saved JSON: {json_path}")
    print(f"Saved CSV:  {csv_path}")

    input("\nPress ENTER to close Yahoo: ")

    context.close()