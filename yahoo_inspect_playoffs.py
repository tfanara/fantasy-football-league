from pathlib import Path
import re
import time

from playwright.sync_api import sync_playwright


PROFILE_DIR = Path("yahoo_browser_profile")

TARGET_YEAR = 2021
TARGET_WEEK = 15


with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )

    print()
    print("=" * 75)
    print("YAHOO PLAYOFF INSPECTOR")
    print("=" * 75)

    print()
    print("Navigate manually in Chromium to:")
    print()
    print(f"    Malle's League")
    print(f"    {TARGET_YEAR} season")
    print(f"    Week {TARGET_WEEK}")
    print()
    print("Make sure the matchup cards are visible.")
    print()
    print("The script will detect the page automatically.")
    print()


    target_page = None
    target_heading = None


    while target_page is None:

        for page in reversed(context.pages):

            try:

                headings = page.get_by_text(
                    re.compile(
                        rf"Week\s+{TARGET_WEEK}\s+Matchups"
                    )
                )

                if headings.count() > 0:

                    target_page = page
                    target_heading = headings.first
                    break

            except Exception:
                pass

        if target_page is None:
            time.sleep(1)


    page = target_page
    heading = target_heading


    print()
    print("=" * 75)
    print("PLAYOFF PAGE DETECTED")
    print("=" * 75)

    print()
    print("URL:")
    print(page.url)

    print()
    print("Title:")
    print(page.title())


    # -----------------------------------------------------
    # FIND MATCHUP CONTAINER
    # -----------------------------------------------------

    container = (
        heading
        .locator("..")
        .locator("..")
        .locator("..")
    )


    print()
    print("=" * 75)
    print("FULL WEEK MATCHUP TEXT")
    print("=" * 75)

    print(
        container.inner_text()[:15000]
    )


    # -----------------------------------------------------
    # INSPECT EACH VS / BYE CARD
    # -----------------------------------------------------

    print()
    print("=" * 75)
    print("INDIVIDUAL MATCHUP CARDS")
    print("=" * 75)


    vs_elements = container.get_by_text(
        "vs",
        exact=True,
    )

    print()
    print(
        f"VS cards found: {vs_elements.count()}"
    )


    for i in range(vs_elements.count()):

        vs = vs_elements.nth(i)

        card = (
            vs
            .locator("..")
            .locator("..")
        )

        print()
        print(f"--- VS CARD {i + 1} ---")
        print(card.inner_text())


    # -----------------------------------------------------
    # LOOK FOR BYES
    # -----------------------------------------------------

    bye_elements = container.get_by_text(
        "Bye",
        exact=True,
    )

    print()
    print(
        f"Bye elements found: {bye_elements.count()}"
    )


    for i in range(bye_elements.count()):

        bye = bye_elements.nth(i)

        card = (
            bye
            .locator("..")
            .locator("..")
        )

        print()
        print(f"--- BYE CARD {i + 1} ---")
        print(card.inner_text())


    # -----------------------------------------------------
    # SEARCH PAGE FOR PLAYOFF LABELS
    # -----------------------------------------------------

    print()
    print("=" * 75)
    print("PLAYOFF-RELATED PAGE TEXT")
    print("=" * 75)

    body = page.locator("body").inner_text()

    keywords = [
        "playoff",
        "championship",
        "semifinal",
        "quarterfinal",
        "consolation",
        "5th place",
        "7th place",
        "9th place",
        "11th place",
    ]

    for line in body.splitlines():

        clean = line.strip()

        if not clean:
            continue

        lower = clean.lower()

        if any(
            keyword in lower
            for keyword in keywords
        ):
            print(clean)


    input(
        "\nPress ENTER to close Chromium: "
    )

    context.close()
