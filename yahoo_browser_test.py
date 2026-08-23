from pathlib import Path
from playwright.sync_api import sync_playwright

YAHOO_URL = "https://football.fantasysports.yahoo.com/"
PROFILE_DIR = Path("yahoo_browser_profile")

with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )

    page = context.pages[0] if context.pages else context.new_page()

    page.goto(
        YAHOO_URL,
        wait_until="domcontentloaded",
    )

    print()
    print("Yahoo opened.")
    print("Navigate to Malle's League.")
    print("Then click League -> Standings.")
    print()

    input("Press ENTER when you can see the standings: ")

    print()
    print("=" * 60)
    print("PAGE INFORMATION")
    print("=" * 60)

    print("URL:")
    print(page.url)

    print()
    print("TITLE:")
    print(page.title())

    print()
    print("=" * 60)
    print("TABLES FOUND")
    print("=" * 60)

    tables = page.locator("table")

    print("Number of tables:", tables.count())

    for i in range(tables.count()):
        print()
        print(f"--- TABLE {i} ---")
        print(tables.nth(i).inner_text()[:5000])

    print()
    print("=" * 60)
    print("LINKS CONTAINING 'STAND'")
    print("=" * 60)

    links = page.locator("a")

    for i in range(links.count()):
        link = links.nth(i)

        try:
            text = link.inner_text().strip()
            href = link.get_attribute("href")

            if "stand" in text.lower() or (
                href and "stand" in href.lower()
            ):
                print("TEXT:", text)
                print("HREF:", href)
                print()
        except:
            pass

    input("Press ENTER to close: ")

    context.close()