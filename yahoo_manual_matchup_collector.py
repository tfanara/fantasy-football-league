from pathlib import Path
import json
import re
import time

import pandas as pd
from playwright.sync_api import sync_playwright


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

PROFILE_DIR = Path("yahoo_browser_profile")
DATA_DIR = Path("data")

YEAR = 2025
WEEKS_TO_COLLECT = {14}

OUTPUT_DIR = DATA_DIR / str(YEAR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_JSON = OUTPUT_DIR / "matchups_week14.json"
OUTPUT_CSV = OUTPUT_DIR / "matchups_week14.csv"


# ---------------------------------------------------------
# PARSE ONE MATCHUP
# ---------------------------------------------------------

def parse_matchup(text, year, week):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if "Bye" in lines:
        return None

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
        "year": year,
        "week": week,

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

        "is_playoffs": False,
    }


# ---------------------------------------------------------
# FIND A MATCHUP PAGE
# ---------------------------------------------------------

def detect_week_page(context):

    for page in reversed(context.pages):

        try:

            headings = page.get_by_text(
                re.compile(r"Week \d+ Matchups"),
            )

            if headings.count() == 0:
                continue

            heading = headings.first

            text = heading.inner_text().strip()

            match = re.search(
                r"Week\s+(\d+)\s+Matchups",
                text,
            )

            if not match:
                continue

            week = int(match.group(1))

            return page, heading, week

        except Exception:
            pass

    return None, None, None


# ---------------------------------------------------------
# READ SIX MATCHUPS
# ---------------------------------------------------------

def scrape_current_week(page, heading, year, week):

    container = (
        heading
        .locator("..")
        .locator("..")
        .locator("..")
    )

    vs_elements = container.get_by_text(
        "vs",
        exact=True,
    )

    matchups = []

    for i in range(vs_elements.count()):

        vs = vs_elements.nth(i)

        card = (
            vs
            .locator("..")
            .locator("..")
        )

        text = card.inner_text()

        try:

            matchup = parse_matchup(
                text,
                year,
                week,
            )

            if matchup is not None:
                matchups.append(matchup)

        except Exception as e:

            print()
            print(
                f"WARNING parsing matchup "
                f"{i + 1}: {e}"
            )

    return matchups


# ---------------------------------------------------------
# SAVE DATA
# ---------------------------------------------------------

def save_data(matchups):

    matchups = sorted(
        matchups,
        key=lambda x: (
            x["week"],
            x["team_1"],
        ),
    )

    with open(
        OUTPUT_JSON,
        "w",
    ) as f:

        json.dump(
            matchups,
            f,
            indent=2,
        )

    df = pd.DataFrame(matchups)

    df.to_csv(
        OUTPUT_CSV,
        index=False,
    )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )

    print()
    print("=" * 75)
    print(f"{YEAR} MANUAL MATCHUP COLLECTOR")
    print("=" * 75)

    print()
    print(
        "Navigate Yahoo manually."
    )

    print()
    print(
        "Collecting these weeks:"
    )

    print(
        sorted(WEEKS_TO_COLLECT)
    )

    print()
    print(
        "Whenever you navigate to one of those "
        "Week X Matchups pages, Python will "
        "save it automatically."
    )

    print()
    print(
        "After a week is saved, manually navigate "
        "to the next week."
    )

    print()
    print(
        "Press Ctrl+C in Terminal when finished."
    )


    collected_weeks = set()
    all_matchups = []

    last_detected_week = None


    try:

        while True:

            page, heading, week = detect_week_page(
                context
            )

            if week is None:
                time.sleep(1)
                continue


            if week == last_detected_week:
                time.sleep(1)
                continue


            last_detected_week = week


            print()
            print("-" * 75)
            print(
                f"Detected Week {week}"
            )
            print("-" * 75)


            if week not in WEEKS_TO_COLLECT:

                print(
                    f"Week {week} is not in the "
                    f"collection list."
                )

                time.sleep(1)
                continue


            if week in collected_weeks:

                print(
                    f"Week {week} already saved."
                )

                time.sleep(1)
                continue


            week_matchups = scrape_current_week(
                page,
                heading,
                YEAR,
                week,
            )


            if len(week_matchups) != 6:

                print(
                    f"WARNING: Expected 6 games, "
                    f"found {len(week_matchups)}."
                )

                print(
                    "Not saving this week yet."
                )

                continue


            all_matchups.extend(
                week_matchups
            )

            collected_weeks.add(
                week
            )

            save_data(
                all_matchups
            )


            print()
            print(
                f"Saved Week {week}: "
                f"{len(week_matchups)} games."
            )

            print()
            print(
                "Completed weeks:"
            )

            print(
                sorted(collected_weeks)
            )

            remaining = (
                WEEKS_TO_COLLECT
                - collected_weeks
            )

            print()
            print(
                "Remaining:"
            )

            print(
                sorted(remaining)
            )


            if not remaining:

                print()
                print("=" * 75)
                print(
                    f"{YEAR} COLLECTION COMPLETE"
                )
                print("=" * 75)

                print()
                print(
                    f"Saved {len(all_matchups)} games."
                )

                print()
                print(
                    f"JSON: {OUTPUT_JSON}"
                )

                print(
                    f"CSV:  {OUTPUT_CSV}"
                )

                break


            time.sleep(1)


    except KeyboardInterrupt:

        print()
        print()
        print("Collector stopped.")

        if all_matchups:

            save_data(
                all_matchups
            )

            print(
                "Progress was saved."
            )


    input(
        "\nPress ENTER to close Chromium: "
    )

    context.close()
