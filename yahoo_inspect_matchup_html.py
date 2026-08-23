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

    # -----------------------------------------------------
    # FIND WEEK MATCHUP CONTAINER
    # -----------------------------------------------------

    heading = page.get_by_text(
        f"Week {WEEK} Matchups",
        exact=False,
    ).first

    # Based on our previous inspection,
    # three parent levels gives us the matchup container.
    container = heading.locator("..").locator("..").locator("..")

    print()
    print("=" * 70)
    print("MATCHUP CONTAINER FOUND")
    print("=" * 70)

    print(container.inner_text()[:3000])

    # -----------------------------------------------------
    # INSPECT DIRECT CHILDREN
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("DIRECT CHILDREN")
    print("=" * 70)

    children = container.locator(":scope > *")

    print("Child count:", children.count())

    for i in range(children.count()):

        child = children.nth(i)

        try:
            tag = child.evaluate(
                "(el) => el.tagName"
            )

            class_name = child.get_attribute("class")

            text = child.inner_text().strip()

            print()
            print(f"--- CHILD {i} ---")
            print("TAG:", tag)
            print("CLASS:", class_name)
            print("TEXT:")
            print(text[:2500])

        except Exception as e:
            print("Could not inspect child:", e)

    # -----------------------------------------------------
    # LOOK FOR ELEMENTS CONTAINING "vs"
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("ELEMENTS CONTAINING VS")
    print("=" * 70)

    vs_elements = container.get_by_text(
        "vs",
        exact=True,
    )

    print("Count:", vs_elements.count())

    for i in range(vs_elements.count()):

        vs = vs_elements.nth(i)

        print()
        print(f"--- VS {i} ---")

        current = vs

        for level in range(1, 5):

            try:
                current = current.locator("..")

                print()
                print(f"PARENT {level}:")
                print(current.inner_text()[:2000])

            except Exception:
                break

    input("\nPress ENTER to close Yahoo: ")

    context.close()
