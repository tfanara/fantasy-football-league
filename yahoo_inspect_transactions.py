from pathlib import Path

from playwright.sync_api import sync_playwright


PROFILE_DIR = Path("yahoo_browser_profile")

YEAR = 2025
LEAGUE_ID = "637567"

LEAGUE_URL = (
    f"https://football.fantasysports.yahoo.com/"
    f"{YEAR}/f1/{LEAGUE_ID}"
)


with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )

    pages = context.pages

    if pages:
        page = pages[0]
    else:
        page = context.new_page()

    print()
    print("=" * 80)
    print("YAHOO TRANSACTION INSPECTOR")
    print("=" * 80)

    print()
    print("We need to inspect Yahoo's transaction history.")
    print()
    print("In the Chromium window, navigate to:")
    print()
    print("    Malle's League")
    print(f"    {YEAR} season")
    print("    Transactions")
    print()
    print("If needed, start here:")
    print()
    print(LEAGUE_URL)
    print()
    print(
        "Leave the transaction/history page visible "
        "once you find it."
    )
    print()

    input(
        "Press ENTER when the transaction page is visible: "
    )

    # ========================================================
    # CURRENT PAGE
    # ========================================================

    print()
    print("=" * 80)
    print("CURRENT PAGE")
    print("=" * 80)

    print()
    print("Title:")
    print(page.title())

    print()
    print("URL:")
    print(page.url)

    # ========================================================
    # TRANSACTION-RELATED LINKS
    # ========================================================

    print()
    print("=" * 80)
    print("TRANSACTION-RELATED LINKS")
    print("=" * 80)

    links = page.locator("a")

    found_links = 0

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

            keywords = [
                "transaction",
                "waiver",
                "activity",
                "moves",
            ]

            if any(
                keyword in combined
                for keyword in keywords
            ):

                found_links += 1

                print()
                print("TEXT:", text)
                print("HREF:", href)

        except Exception:
            pass

    print()
    print(
        f"Relevant links found: {found_links}"
    )

    # ========================================================
    # TABLES
    # ========================================================

    print()
    print("=" * 80)
    print("TABLES")
    print("=" * 80)

    tables = page.locator("table")

    print()
    print(
        f"Number of tables: {tables.count()}"
    )

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
    # TABLE ROWS
    # ========================================================

    print()
    print("=" * 80)
    print("TABLE ROWS")
    print("=" * 80)

    rows = page.locator("tr")

    print()
    print(
        f"Total TR elements: {rows.count()}"
    )

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

    # ========================================================
    # LIST ITEMS
    # ========================================================

    print()
    print("=" * 80)
    print("POSSIBLE TRANSACTION LIST ITEMS")
    print("=" * 80)

    items = page.locator("li")

    print()
    print(
        f"Total LI elements: {items.count()}"
    )

    transaction_words = [
        "waiver",
        "free agent",
        "added",
        "dropped",
        "add",
        "drop",
        "trade",
    ]

    found_items = 0

    for i in range(items.count()):

        item = items.nth(i)

        try:
            text = item.inner_text().strip()
        except Exception:
            continue

        if not text:
            continue

        lower = text.lower()

        if any(
            word in lower
            for word in transaction_words
        ):

            found_items += 1

            print()
            print(f"--- LI {i} ---")
            print(text[:5000])

    print()
    print(
        f"Possible transaction items found: "
        f"{found_items}"
    )

    # ========================================================
    # VISIBLE PAGE TEXT
    # ========================================================

    print()
    print("=" * 80)
    print("VISIBLE PAGE TEXT")
    print("=" * 80)

    try:

        body = page.locator(
            "body"
        ).inner_text()

        lines = [
            line.strip()
            for line in body.splitlines()
            if line.strip()
        ]

        for i, line in enumerate(
            lines[:1200]
        ):
            print(
                f"{i:04}: {line}"
            )

    except Exception as e:

        print(
            "Could not read body:",
            e,
        )

    # ========================================================
    # HTML CLUES
    # ========================================================

    print()
    print("=" * 80)
    print("HTML ATTRIBUTE CLUES")
    print("=" * 80)

    selectors = [
        "[class*='transaction']",
        "[class*='Transaction']",
        "[class*='waiver']",
        "[class*='Waiver']",
        "[class*='activity']",
        "[class*='Activity']",
        "[data-test*='transaction']",
        "[data-test*='waiver']",
    ]

    for selector in selectors:

        try:

            elements = page.locator(
                selector
            )

            count = elements.count()

            if count == 0:
                continue

            print()
            print(
                f"{selector}: "
                f"{count} elements"
            )

            for i in range(
                min(count, 10)
            ):

                try:
                    text = (
                        elements
                        .nth(i)
                        .inner_text()
                        .strip()
                    )
                except Exception:
                    text = ""

                if text:
                    print()
                    print(
                        f"--- {selector} "
                        f"{i} ---"
                    )
                    print(
                        text[:3000]
                    )

        except Exception:
            pass

    print()
    print("=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)

    input(
        "\nPress ENTER to close Chromium: "
    )

    context.close()
