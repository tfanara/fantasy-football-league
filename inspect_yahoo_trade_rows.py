from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = Path("yahoo_browser_profile")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )

    page = context.pages[0] if context.pages else context.new_page()

    print()
    print("=" * 80)
    print("YAHOO TRADE ROW INSPECTOR")
    print("=" * 80)
    print()
    print("In the Chromium window:")
    print("1. Open a historical Yahoo league.")
    print("2. Open the Transactions page.")
    print("3. Find a page containing a trade if possible.")
    print("4. Return here and press ENTER.")
    print()

    input("Press ENTER when the transaction page is visible: ")

    print()
    print("PAGE:")
    print(page.url)
    print()
    print("TITLE:")
    print(page.title())

    rows = page.locator("table tr")

    print()
    print(f"TABLE ROWS FOUND: {rows.count()}")
    print()

    for i in range(rows.count()):
        row = rows.nth(i)

        try:
            text = row.inner_text().strip()
        except Exception:
            continue

        if not text:
            continue

        print("=" * 80)
        print(f"ROW {i}")
        print("=" * 80)
        print(text)
        print()

        try:
            print("HTML:")
            print(row.inner_html())
        except Exception as exc:
            print(f"Could not read HTML: {exc}")

        print()

    input("Press ENTER to close Chromium: ")
    context.close()
