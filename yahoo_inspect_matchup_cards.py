from pathlib import Path
from playwright.sync_api import sync_playwright


PROFILE_DIR = Path("yahoo_browser_profile")

YEAR = 2025
LEAGUE_ID = "637567"
WEEK = 1

URL = (
    f"https://football.fantasysports.yahoo.com/"
    f"{YEAR}/f1/{LEAGUE_ID}"
    f"?module=standings&lhst=sched&week={WEEK}"
    f"#lhstsched"
)


with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )

    page = context.pages[0] if context.pages else context.new_page()

    page.goto(
        URL,
        wait_until="domcontentloaded",
        timeout=60000,
    )

    print()
    print("=" * 70)
    print("LOOKING FOR WEEK 1 MATCHUP SECTION")
    print("=" * 70)

    # -----------------------------------------------------
    # Find element containing "Week 1 Matchups"
    # -----------------------------------------------------

    matches = page.get_by_text(
        "Week 1 Matchups",
        exact=False,
    )

    print()
    print("Elements matching 'Week 1 Matchups':", matches.count())


    # -----------------------------------------------------
    # Print parents around the matchup heading
    # -----------------------------------------------------

    for i in range(matches.count()):

        element = matches.nth(i)

        print()
        print(f"--- MATCH {i} ---")

        try:
            print("TEXT:")
            print(element.inner_text())
        except:
            pass

        # Walk upward through parent containers.
        current = element

        for level in range(1, 7):

            try:
                current = current.locator("..")

                text = current.inner_text().strip()

                print()
                print(f"PARENT LEVEL {level}")
                print("-" * 50)
                print(text[:10000])

            except Exception:
                break


    # -----------------------------------------------------
    # Search for elements containing "Final results"
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("FINAL RESULTS ELEMENTS")
    print("=" * 70)

    final_elements = page.get_by_text(
        "Final results",
        exact=False,
    )

    print("Count:", final_elements.count())

    for i in range(final_elements.count()):

        element = final_elements.nth(i)

        try:
            parent = element.locator("..")
            print()
            print(f"--- FINAL RESULT {i} ---")
            print(parent.inner_text()[:5000])

        except Exception:
            pass


    input("\nPress ENTER to close Yahoo: ")

    context.close()
