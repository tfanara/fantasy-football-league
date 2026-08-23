from pathlib import Path
import time

import pandas as pd
from playwright.sync_api import sync_playwright


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

PROFILE_DIR = Path("yahoo_browser_profile")

TARGET_YEAR = 2021
TARGET_WEEK = 7


# ---------------------------------------------------------
# PARSE ONE MATCHUP
# ---------------------------------------------------------

def parse_matchup(text):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # Ignore playoff/consolation bye cards
    if "Bye" in lines:
        return None

    # Expected structure:
    #
    # Team 1
    # Record 1
    # Actual score 1
    # Projected score 1
    # vs
    # Actual score 2
    # Projected score 2
    # Team 2
    # Record 2

    if len(lines) < 9:
        raise ValueError(
            f"Unexpected matchup structure:\n{text}"
        )

    team_1 = lines[0]
    record_1 = lines[1]

    score_1 = float(lines[2])
    projected_1 = float(lines[3])

    score_2 = float(lines[5])
    projected_2 = float(lines[6])

    team_2 = lines[7]
    record_2 = lines[8]

    if score_1 > score_2:
        winner = team_1
        loser = team_2

    elif score_2 > score_1:
        winner = team_2
        loser = team_1

    else:
        winner = "Tie"
        loser = "Tie"

    margin = round(
        abs(score_1 - score_2),
        2,
    )

    return {
        "year": TARGET_YEAR,
        "week": TARGET_WEEK,

        "team_1": team_1,
        "team_1_record": record_1,
        "team_1_score": score_1,
        "team_1_projected": projected_1,

        "team_2": team_2,
        "team_2_record": record_2,
        "team_2_score": score_2,
        "team_2_projected": projected_2,

        "winner": winner,
        "loser": loser,
        "margin": margin,
    }


# ---------------------------------------------------------
# START PLAYWRIGHT
# ---------------------------------------------------------

with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )

    print()
    print("=" * 75)
    print("YAHOO MANUAL MATCHUP READER")
    print("=" * 75)

    print()
    print("The script will NOT navigate Yahoo.")
    print()
    print("In the Chromium window, manually navigate to:")
    print()
    print(f"    Malle's League")
    print(f"    {TARGET_YEAR} season")
    print(f"    Week {TARGET_WEEK}")
    print()
    print(
        f"Make sure you can actually see "
        f"'Week {TARGET_WEEK} Matchups' and the six games."
    )

    print()
    print(
        "You do NOT need to return here and press ENTER."
    )

    print()
    print(
        "The script is watching the Chromium tabs automatically..."
    )

    print()


    # -----------------------------------------------------
    # WATCH ALL OPEN TABS
    # -----------------------------------------------------

    target_page = None
    last_status = None

    while target_page is None:

        pages = context.pages

        status = []

        for i, page in enumerate(pages):

            try:

                title = page.title()
                url = page.url

                status.append(
                    f"TAB {i}: {title} | {url}"
                )

                # Look specifically for Week 7 Matchups
                heading = page.get_by_text(
                    f"Week {TARGET_WEEK} Matchups",
                    exact=False,
                )

                if heading.count() > 0:

                    target_page = page

                    break

            except Exception:
                pass


        # Only print tab status when it changes
        current_status = "\n".join(status)

        if (
            current_status
            and current_status != last_status
        ):

            print()
            print("-" * 75)
            print("CURRENT PLAYWRIGHT TABS")
            print("-" * 75)

            print(current_status)

            print()

            last_status = current_status


        if target_page is None:
            time.sleep(1)


    # -----------------------------------------------------
    # PAGE FOUND
    # -----------------------------------------------------

    page = target_page

    print()
    print("=" * 75)
    print("MATCHUP PAGE DETECTED!")
    print("=" * 75)

    print()
    print("URL:")
    print(page.url)

    print()
    print("Title:")
    print(page.title())


    # -----------------------------------------------------
    # FIND MATCHUP HEADING
    # -----------------------------------------------------

    matchup_heading = page.get_by_text(
        f"Week {TARGET_WEEK} Matchups",
        exact=False,
    ).first


    print()
    print("Found:")
    print(matchup_heading.inner_text())


    # -----------------------------------------------------
    # FIND MATCHUP CONTAINER
    # -----------------------------------------------------

    container = (
        matchup_heading
        .locator("..")
        .locator("..")
        .locator("..")
    )


    # -----------------------------------------------------
    # FIND MATCHUP CARDS
    # -----------------------------------------------------

    vs_elements = container.get_by_text(
        "vs",
        exact=True,
    )

    print()
    print(
        f"Found {vs_elements.count()} matchup card(s)."
    )


    # -----------------------------------------------------
    # PARSE MATCHUPS
    # -----------------------------------------------------

    matchups = []

    for i in range(vs_elements.count()):

        vs = vs_elements.nth(i)

        matchup_card = (
            vs
            .locator("..")
            .locator("..")
        )

        text = matchup_card.inner_text()

        try:

            matchup = parse_matchup(text)

            if matchup:
                matchups.append(matchup)

        except Exception as e:

            print()
            print(
                f"WARNING: Could not parse matchup {i + 1}"
            )

            print(e)


    # -----------------------------------------------------
    # DISPLAY RESULTS
    # -----------------------------------------------------

    df = pd.DataFrame(matchups)

    print()
    print("=" * 90)
    print(
        f"{TARGET_YEAR} WEEK {TARGET_WEEK} MATCHUPS"
    )
    print("=" * 90)


    if df.empty:

        print()
        print("No games were successfully parsed.")

    else:

        print()

        print(
            df[
                [
                    "team_1",
                    "team_1_score",
                    "team_2",
                    "team_2_score",
                    "winner",
                    "margin",
                ]
            ].to_string(
                index=False
            )
        )

        print()

        print(
            f"Successfully parsed "
            f"{len(df)} matchup(s)."
        )


    # -----------------------------------------------------
    # KEEP BROWSER OPEN
    # -----------------------------------------------------

    print()

    input(
        "Press ENTER when you're ready to close Chromium: "
    )

    context.close()