from pathlib import Path
import json
import random
import time

import pandas as pd
from playwright.sync_api import sync_playwright


PROFILE_DIR = Path("yahoo_browser_profile")
DATA_DIR = Path("data")

DATA_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------
# HISTORICAL LEAGUES
# ---------------------------------------------------------

league_ids = {
    2017: "1121308",
}


# ---------------------------------------------------------
# FOR NOW: REGULAR SEASON ONLY
# ---------------------------------------------------------
#
# Your 2018-2020 results show that Week 14 already contains
# playoff/consolation byes.
#
# We'll scrape playoffs separately afterward.
# ---------------------------------------------------------

REGULAR_SEASON_WEEKS = [1]


def matchup_url(year, league_id, week):

    return (
        f"https://football.fantasysports.yahoo.com/"
        f"{year}/f1/{league_id}"
        f"?module=standings&lhst=sched&week={week}"
        f"#lhstsched"
    )


def parse_matchup(text, year, week):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # Ignore bye cards
    if "Bye" in lines:
        return None

    if len(lines) < 9:
        raise ValueError(
            f"Unexpected matchup structure:\n{text}"
        )

    team_1 = lines[0]
    team_1_record = lines[1]

    score_1 = float(lines[2])
    projected_1 = float(lines[3])

    score_2 = float(lines[5])
    projected_2 = float(lines[6])

    team_2 = lines[7]
    team_2_record = lines[8]

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
        "team_1_record": team_1_record,
        "team_1_score": score_1,
        "team_1_projected": projected_1,

        "team_2": team_2,
        "team_2_record": team_2_record,
        "team_2_score": score_2,
        "team_2_projected": projected_2,

        "winner": winner,
        "loser": loser,
        "margin": margin,

        "is_playoffs": False,
    }


def scrape_week(page, year, league_id, week):

    print()
    print(f"READING MANUALLY OPENED {year} WEEK {week}")
    print("URL:", page.url)

    try:
        print("Title:", page.title())
    except Exception:
        pass

    # IMPORTANT:
    # Do not navigate historical Yahoo pages with page.goto().
    # The user has already opened the correct week manually.

    page.wait_for_timeout(2000)

    try:
        body_text = page.locator("body").inner_text(
            timeout=10000
        )
    except Exception as e:
        raise RuntimeError(
            f"Could not read the currently open Yahoo page: {e}"
        )

    print("Body characters:", len(body_text))

    if len(body_text) < 1000:
        raise RuntimeError(
            "The selected Yahoo target does not contain the "
            "rendered fantasy page."
        )

    print()
    print("Searching rendered page for matchup cards...")

    # Yahoo matchup cards contain a visible VS element.
    vs_elements = page.get_by_text(
        "VS",
        exact=True,
    )

    print(
        f"Found {vs_elements.count()} VS elements."
    )

    matchups = []

    for i in range(vs_elements.count()):

        try:
            vs = vs_elements.nth(i)

            # Walk upward until we find a container containing
            # the complete matchup card.
            container = vs.locator("xpath=..")

            text = ""

            for _ in range(8):

                try:
                    candidate_text = (
                        container.inner_text(
                            timeout=3000
                        )
                    )
                except Exception:
                    candidate_text = ""

                lines = [
                    line.strip()
                    for line in candidate_text.splitlines()
                    if line.strip()
                ]

                # A real matchup card should contain enough
                # information for two teams and their scores.
                if (
                    "VS" in candidate_text
                    and len(lines) >= 8
                ):
                    text = candidate_text

                if (
                    "VS" in candidate_text
                    and len(lines) >= 9
                ):
                    break

                container = container.locator(
                    "xpath=.."
                )

            if not text:
                print(
                    f"  WARNING: Could not identify "
                    f"matchup card {i + 1}."
                )
                continue

            print()
            print("-" * 60)
            print(f"MATCHUP CARD {i + 1}")
            print("-" * 60)
            print(text[:1200])

            try:
                matchup = parse_matchup(
                    text,
                    year,
                    week,
                )

                if matchup is not None:
                    matchups.append(matchup)

            except Exception as e:
                print(
                    f"  WARNING parsing matchup "
                    f"{i + 1}: {e}"
                )

        except Exception as e:
            print(
                f"  WARNING reading matchup "
                f"{i + 1}: {e}"
            )

    return matchups


with sync_playwright() as p:

    browser = p.chromium.connect_over_cdp(
        "http://127.0.0.1:9222"
    )

    if not browser.contexts:
        raise RuntimeError(
            "Could not find the existing Yahoo browser context."
        )

    context = browser.contexts[0]

    # Yahoo exposes ad/tracking targets with the same fantasy URL.
    # Choose the Yahoo Fantasy target with the largest rendered body.
    candidates = []

    print()
    print("YAHOO FANTASY TARGETS")
    print()

    for i, candidate in enumerate(context.pages):
        try:
            url = candidate.url

            if "football.fantasysports.yahoo.com" not in url:
                continue

            try:
                title = candidate.title()
            except Exception:
                title = ""

            try:
                body = candidate.locator("body").inner_text(
                    timeout=3000
                )
            except Exception:
                body = ""

            print(
                f"Target {i}: "
                f"title={title!r} "
                f"body={len(body):,}"
            )
            print(f"          {url}")

            candidates.append(
                (
                    len(body),
                    candidate,
                    title,
                    url,
                )
            )

        except Exception:
            continue

    if not candidates:
        raise RuntimeError(
            "Could not find an open Yahoo Fantasy target."
        )

    candidates.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    body_size, page, page_title, page_url = candidates[0]

    if body_size < 1000:
        raise RuntimeError(
            "Yahoo Fantasy targets were found, but none contains "
            "the fully rendered fantasy page."
        )

    print()
    print("CONNECTED TO EXISTING YAHOO BROWSER")
    print("Selected title:", page_title)
    print("Selected URL:  ", page_url)
    print("Body characters:", body_size)
    print()

    all_matchups = []

    for year, league_id in league_ids.items():

        print()
        print("=" * 70)
        print(f"SCRAPING {year}")
        print("=" * 70)

        season_matchups = []

        for week in REGULAR_SEASON_WEEKS:

            print(
                f"Week {week}... ",
                end="",
                flush=True,
            )

            week_matchups = scrape_week(
                page,
                year,
                league_id,
                week,
            )

            print(
                f"=> {len(week_matchups)} matchups"
            )

            season_matchups.extend(
                week_matchups
            )

            all_matchups.extend(
                week_matchups
            )

            # Slow down between pages.
            delay = random.uniform(
                2.5,
                4.5,
            )

            time.sleep(delay)


        # SAVE EACH SEASON

        year_dir = DATA_DIR / str(year)

        year_dir.mkdir(
            exist_ok=True
        )

        with open(
            year_dir / "matchups.json",
            "w",
        ) as f:

            json.dump(
                season_matchups,
                f,
                indent=2,
            )

        season_df = pd.DataFrame(
            season_matchups
        )

        season_df.to_csv(
            year_dir / "matchups.csv",
            index=False,
        )

        print()
        print(
            f"{year}: saved "
            f"{len(season_matchups)} "
            f"regular-season matchups."
        )

        # Give Yahoo a longer break between seasons.
        time.sleep(
            random.uniform(8, 12)
        )


    # MASTER FILES

    with open(
        DATA_DIR / "all_matchups.json",
        "w",
    ) as f:

        json.dump(
            all_matchups,
            f,
            indent=2,
        )

    master_df = pd.DataFrame(
        all_matchups
    )

    master_df.to_csv(
        DATA_DIR / "all_matchups.csv",
        index=False,
    )


    print()
    print("=" * 70)
    print("REGULAR-SEASON SCRAPE COMPLETE")
    print("=" * 70)

    print(
        f"Total games: {len(all_matchups)}"
    )

    input(
        "\nPress ENTER to close Yahoo: "
    )

    # Shared Yahoo browser intentionally left open.