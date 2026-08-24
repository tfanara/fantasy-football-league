from pathlib import Path

from playwright.sync_api import sync_playwright


PROFILE_DIR = Path("yahoo_browser_profile")


with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )

    print()
    print("=" * 75)
    print("YAHOO DRAFT RESULTS INSPECTOR")
    print("=" * 75)

    print()
    print("In Chromium, manually navigate to:")
    print()
    print("    Malle's League")
    print("    2025 season")
    print("    Draft Results")
    print()
    print("Do not return to Terminal until you can actually")
    print("see the completed draft results on the Yahoo page.")
    print()

    input("Press ENTER when Draft Results are visible: ")

    # ========================================================
    # SHOW ALL OPEN TABS
    # ========================================================

    pages = context.pages

    print()
    print("=" * 75)
    print("OPEN TABS")
    print("=" * 75)

    for i, page in enumerate(pages):

        try:
            title = page.title()
            url = page.url
        except Exception:
            title = "(could not read title)"
            url = "(could not read URL)"

        print()
        print(f"TAB {i}")
        print("Title:", title)
        print("URL:", url)

    # ========================================================
    # USER SELECTS TAB
    # ========================================================

    print()
    print("=" * 75)
    print("SELECT TAB")
    print("=" * 75)
    print()
    print(
        "Enter the number of the tab that is visibly showing "
        "Malle's League Draft Results."
    )
    print()

    while True:

        choice = input("Tab number: ").strip()

        try:
            tab_number = int(choice)

            if 0 <= tab_number < len(pages):
                break

        except ValueError:
            pass

        print("Invalid tab number. Try again.")

    page = pages[tab_number]

    # ========================================================
    # SELECTED TAB
    # ========================================================

    print()
    print("=" * 75)
    print("SELECTED TAB")
    print("=" * 75)

    print()
    print("Title:")
    print(page.title())

    print()
    print("URL:")
    print(page.url)

    # ========================================================
    # TABLES
    # ========================================================

    tables = page.locator("table")

    print()
    print("=" * 75)
    print("TABLES")
    print("=" * 75)

    print()
    print(f"Number of tables: {tables.count()}")

    for i in range(tables.count()):

        table = tables.nth(i)

        try:
            text = table.inner_text().strip()
        except Exception:
            continue

        if not text:
            continue

        print()
        print(f"--- TABLE {i} ---")
        print(text[:20000])

    # ========================================================
    # VISIBLE PAGE TEXT
    # ========================================================

    print()
    print("=" * 75)
    print("VISIBLE PAGE TEXT")
    print("=" * 75)

    body = page.locator("body").inner_text()

    lines = [
        line.strip()
        for line in body.splitlines()
        if line.strip()
    ]

    for i, line in enumerate(lines[:800]):
        print(f"{i:03}: {line}")

    # ========================================================
    # DRAFT-RELATED LINKS
    # ========================================================

    print()
    print("=" * 75)
    print("DRAFT LINKS")
    print("=" * 75)

    links = page.locator("a")

    for i in range(links.count()):

        link = links.nth(i)

        try:
            text = link.inner_text().strip()
            href = link.get_attribute("href")

            if not href:
                continue

            combined = (
                text.lower()
                + " "
                + href.lower()
            )

            if "draft" in combined:

                print()
                print("TEXT:", text)
                print("HREF:", href)

        except Exception:
            pass

    # ========================================================
    # TABLE ROWS
    # ========================================================

    print()
    print("=" * 75)
    print("TABLE ROWS")
    print("=" * 75)

    rows = page.locator("tr")

    print()
    print(f"Total TR elements: {rows.count()}")

    for i in range(rows.count()):

        row = rows.nth(i)

        try:
            text = row.inner_text().strip()
        except Exception:
            continue

        if not text:
            continue

        print()
        print(f"--- ROW {i} ---")
        print(text[:5000])

    input(
        "\nPress ENTER to close Chromium: "
    )

    context.close()