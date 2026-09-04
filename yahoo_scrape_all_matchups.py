from pathlib import Path
import json
import random
import time

import pandas as pd
from playwright.sync_api import sync_playwright

from season_config import CURRENT_SEASON, YAHOO_LEAGUE_IDS, REGULAR_SEASON_END_WEEK


PROFILE_DIR = Path("yahoo_browser_profile")
DATA_DIR = Path("data")

DATA_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------
# HISTORICAL LEAGUES
# ---------------------------------------------------------

league_ids = {
    year: league_id
    for year, league_id in YAHOO_LEAGUE_IDS.items()
    if 2018 <= year <= CURRENT_SEASON
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

# Per-season regular-season lengths come from season_config.py.


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

    url = matchup_url(
        year,
        league_id,
        week,
    )

    # Give Yahoo a couple chances to render the page.
    for attempt in range(1, 4):

        print(
            f"attempt {attempt}",
            end=" ",
            flush=True,
        )

        try:

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            # Give Yahoo's JavaScript time to render.
            page.wait_for_timeout(2500)

            heading = page.get_by_text(
                f"Week {week} Matchups",
                exact=False,
            )

            if heading.count() > 0:
                break

            print(
                f"[not found; title={page.title()}]",
                end=" ",
            )

        except Exception as e:

            print(
                f"[load error: {e}]",
                end=" ",
            )

        # Wait before retrying.
        time.sleep(
            random.uniform(4, 7)
        )

    else:

        print()
        print(
            f"  FAILED: {year} Week {week}"
        )

        print(
            f"  URL after failure: {page.url}"
        )

        print(
            f"  Title: {page.title()}"
        )

        return []


    heading = heading.first

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

        matchup_card = (
            vs
            .locator("..")
            .locator("..")
        )

        text = matchup_card.inner_text()

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
                f"  WARNING parsing matchup "
                f"{i + 1}: {e}"
            )

    return matchups


with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )

    page = context.pages[0] if context.pages else context.new_page()

    all_matchups = []

    for year, league_id in league_ids.items():

        print()
        print("=" * 70)
        print(f"SCRAPING {year}")
        print("=" * 70)

        season_matchups = []

        for week in range(1, REGULAR_SEASON_END_WEEK[year] + 1):

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

    context.close()