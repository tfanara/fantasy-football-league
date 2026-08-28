from pathlib import Path
import json
import pandas as pd
from playwright.sync_api import sync_playwright


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

YEAR = 2017
LEAGUE_ID = "1121308"
CDP_URL = "http://" + "127.0.0.1:9222"

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------
# CONNECT TO EXISTING YAHOO BROWSER
# ---------------------------------------------------------

with sync_playwright() as p:

    browser = p.chromium.connect_over_cdp(CDP_URL)

    if not browser.contexts:
        raise RuntimeError("No Chromium browser context found.")

    context = browser.contexts[0]

    pages = []

    for candidate in context.pages:
        try:
            if not candidate.is_closed():
                pages.append(candidate)
        except Exception:
            continue

    print()
    print("OPEN BROWSER TABS")
    print()

    for i, candidate in enumerate(pages):
        try:
            title = candidate.title()
        except Exception:
            title = "(no title)"

        try:
            url = candidate.url
        except Exception:
            url = "(no URL)"

        print(f"TAB {i}")
        print(f"Title: {title}")
        print(f"URL:   {url}")
        print()

    while True:
        choice = input(
            "Enter the TAB NUMBER of the visible 2017 standings page: "
        ).strip()

        try:
            tab_number = int(choice)
        except ValueError:
            print("Enter one of the tab numbers shown above.")
            continue

        if 0 <= tab_number < len(pages):
            page = pages[tab_number]
            break

        print("Enter one of the tab numbers shown above.")

    page.wait_for_timeout(2000)

    try:
        body_text = page.locator("body").inner_text(timeout=10000)
    except Exception:
        body_text = ""

    print()
    print("Selected tab:")
    print("Title:", page.title())
    print("URL:  ", page.url)
    print("Body characters:", len(body_text))
    print()
    print()
    print("CONNECTED TO 2017 YAHOO LEAGUE")
    print("Title:", page.title())
    print("URL:  ", page.url)
    print(
        "Body characters:",
        len(page.locator("body").inner_text(timeout=3000)),
    )
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

    # Shared CDP browser intentionally left open.