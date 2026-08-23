from pathlib import Path
from playwright.sync_api import sync_playwright


PROFILE_DIR = Path("yahoo_browser_profile")

YAHOO_URL = "https://football.fantasysports.yahoo.com/"


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
    print("=" * 60)
    print("HISTORICAL LEAGUE DISCOVERY")
    print("=" * 60)
    print()
    print("In the Yahoo browser:")
    print()
    print("1. Find your Fantasy Profile.")
    print("2. Open your History / previous leagues.")
    print("3. Get to a page where you can see old Fantasy Football leagues.")
    print()
    print("Don't worry about selecting a particular year yet.")
    print()

    input("Press ENTER when you can see your league history: ")

    print()
    print("Current URL:")
    print(page.url)

    print()
    print("Current title:")
    print(page.title())

    print()
    print("=" * 60)
    print("FANTASY FOOTBALL LINKS")
    print("=" * 60)

    links = page.locator("a")

    results = []

    for i in range(links.count()):

        link = links.nth(i)

        try:
            text = link.inner_text().strip()
            href = link.get_attribute("href")

            if not href:
                continue

            # Look for Yahoo Fantasy Football league URLs
            if (
                "/f1/" in href
                or "football.fantasysports.yahoo.com" in href
            ):

                item = (text, href)

                if item not in results:
                    results.append(item)

        except Exception:
            pass


    for text, href in results:

        print()
        print("TEXT:", text)
        print("HREF:", href)


    print()
    print("=" * 60)
    print("YEARS VISIBLE ON PAGE")
    print("=" * 60)

    body = page.locator("body").inner_text()

    for year in range(2017, 2027):

        if str(year) in body:
            print(year)


    print()
    print("=" * 60)

    input("Press ENTER to close: ")

    context.close()