from pathlib import Path
import json

from playwright.sync_api import sync_playwright


PROFILE_DIR = Path("yahoo_browser_profile")

YEAR = 2025
LEAGUE_ID = "637567"


def schedule_url(year, league_id, week):
    return (
        f"https://football.fantasysports.yahoo.com/"
        f"{year}/f1/{league_id}"
        f"?module=standings&lhst=sched&week={week}"
        f"#lhstsched"
    )


with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )

    page = context.pages[0] if context.pages else context.new_page()

    # -----------------------------------------------------
    # TEST WEEK 1
    # -----------------------------------------------------

    week = 1

    url = schedule_url(
        YEAR,
        LEAGUE_ID,
        week,
    )

    print()
    print("=" * 70)
    print(f"OPENING {YEAR} - WEEK {week}")
    print("=" * 70)
    print()
    print(url)
    print()

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
        print("No tables appeared.")

    print()
    print("PAGE TITLE:")
    print(page.title())

    print()
    print("CURRENT URL:")
    print(page.url)

    # -----------------------------------------------------
    # PRINT TABLES
    # -----------------------------------------------------

    tables = page.locator("table")

    print()
    print("=" * 70)
    print("TABLES")
    print("=" * 70)

    print(f"Number of tables: {tables.count()}")

    for i in range(tables.count()):

        table = tables.nth(i)

        try:
            text = table.inner_text().strip()
        except Exception:
            continue

        print()
        print(f"--- TABLE {i} ---")
        print(text[:5000])

    # -----------------------------------------------------
    # LOOK FOR MATCHUP-RELATED TEXT
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("PAGE TEXT CONTAINING WEEK / SCORE")
    print("=" * 70)

    body = page.locator("body").inner_text()

    lines = body.splitlines()

    interesting = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        lower = line.lower()

        if (
            "week 1" in lower
            or "final" in lower
            or "matchup" in lower
        ):
            interesting.append(line)

    for line in interesting[:100]:
        print(line)

    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

    input("\nPress ENTER to close Yahoo: ")

    context.close()
