from pathlib import Path
import json
import re
import time

import pandas as pd
from playwright.sync_api import sync_playwright

from team_aliases import canonical_team


# ============================================================
# SETTINGS
# ============================================================

PROFILE_DIR = Path("yahoo_browser_profile")

DATA_DIR = Path("data")
PLAYOFF_DIR = DATA_DIR / "playoffs"

PLAYOFF_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ------------------------------------------------------------
# LEAGUE PLAYOFF SCHEDULE
# ------------------------------------------------------------

PLAYOFF_WEEKS = {
    2018: {
        14: "Quarterfinal",
        15: "Semifinal",
        16: "Championship",
    },
    2019: {
        14: "Quarterfinal",
        15: "Semifinal",
        16: "Championship",
    },
    2020: {
        14: "Quarterfinal",
        15: "Semifinal",
        16: "Championship",
    },
    2021: {
        15: "Quarterfinal",
        16: "Semifinal",
        17: "Championship",
    },
    2022: {
        15: "Quarterfinal",
        16: "Semifinal",
        17: "Championship",
    },
    2023: {
        15: "Quarterfinal",
        16: "Semifinal",
        17: "Championship",
    },
    2024: {
        15: "Quarterfinal",
        16: "Semifinal",
        17: "Championship",
    },
    2025: {
        15: "Quarterfinal",
        16: "Semifinal",
        17: "Championship",
    },
}


OUTPUT_CSV = PLAYOFF_DIR / "playoff_games.csv"
OUTPUT_JSON = PLAYOFF_DIR / "playoff_games.json"


# ============================================================
# PARSE ONE PLAYOFF MATCHUP
# ============================================================

def parse_matchup(text, year, week, round_name):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # Bye card: not an actual game.
    if "Bye" in lines:
        return None

    if len(lines) < 9:
        raise ValueError(
            f"Unexpected playoff matchup structure:\n{text}"
        )

    team_1 = canonical_team(lines[0])
    record_1 = lines[1]

    score_1 = float(lines[2])
    projected_1 = float(lines[3])

    score_2 = float(lines[5])
    projected_2 = float(lines[6])

    team_2 = canonical_team(lines[7])
    record_2 = lines[8]

    if score_1 > score_2:
        winner = team_1
        loser = team_2
        winner_score = score_1
        loser_score = score_2

    elif score_2 > score_1:
        winner = team_2
        loser = team_1
        winner_score = score_2
        loser_score = score_1

    else:
        winner = "Tie"
        loser = "Tie"
        winner_score = score_1
        loser_score = score_2

    margin = round(
        abs(score_1 - score_2),
        2,
    )

    return {
        "year": year,
        "week": week,
        "round": round_name,

        "team_1": team_1,
        "team_1_record": record_1,
        "team_1_score": score_1,
        "team_1_projected": projected_1,

        "team_2": team_2,
        "team_2_record": record_2,
        "team_2_score": score_2,
        "team_2_projected": projected_2,

        "winner": winner,
        "winner_score": winner_score,

        "loser": loser,
        "loser_score": loser_score,

        "margin": margin,

        "is_championship": (
            round_name == "Championship"
        ),
    }


# ============================================================
# FIND CURRENT PLAYOFF PAGE
# ============================================================

def detect_playoff_page(context):

    for page in reversed(context.pages):

        try:

            headings = page.get_by_text(
                re.compile(
                    r"Week\s+\d+\s+Matchups"
                )
            )

            if headings.count() == 0:
                continue

            heading = headings.first

            heading_text = (
                heading
                .inner_text()
                .strip()
            )

            match = re.search(
                r"Week\s+(\d+)\s+Matchups",
                heading_text,
            )

            if not match:
                continue

            week = int(
                match.group(1)
            )

            # Determine season from Yahoo URL
            url = page.url

            year_match = re.search(
                r"football\.fantasysports\.yahoo\.com/"
                r"(\d{4})/f1/",
                url,
            )

            if not year_match:
                continue

            year = int(
                year_match.group(1)
            )

            if year not in PLAYOFF_WEEKS:
                continue

            if week not in PLAYOFF_WEEKS[year]:
                continue

            return (
                page,
                heading,
                year,
                week,
            )

        except Exception:
            pass

    return None, None, None, None


# ============================================================
# FIND CHAMPIONSHIP BRACKET
# ============================================================

def get_championship_bracket(page, heading):

    # Main matchup container
    container = (
        heading
        .locator("..")
        .locator("..")
        .locator("..")
    )

    # Find the Championship Bracket text.
    bracket_label = container.get_by_text(
        "Championship Bracket",
        exact=True,
    )

    if bracket_label.count() == 0:
        raise RuntimeError(
            "Could not find Championship Bracket."
        )

    label = bracket_label.first

    # Yahoo puts the bracket's games in the next sibling
    # area beneath the label. We inspect upward until we
    # get a container that includes the championship games
    # but stops before the consolation section.

    current = label

    for _ in range(6):

        current = current.locator("..")

        text = current.inner_text()

        if (
            "Championship Bracket" in text
            and "Consolation Bracket" not in text
            and "vs" in text
        ):
            return current

    # Fallback:
    # use the overall container and extract only cards that
    # occur before the Consolation Bracket label.
    return container


# ============================================================
# SCRAPE CHAMPIONSHIP BRACKET
# ============================================================

def scrape_playoff_week(
    page,
    heading,
    year,
    week,
):

    round_name = (
        PLAYOFF_WEEKS[year][week]
    )

    container = (
        heading
        .locator("..")
        .locator("..")
        .locator("..")
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Yahoo's first cards belong to Championship Bracket.
    #
    # Quarterfinal:
    #   4 championship cards
    #   2 actual games + 2 byes
    #
    # Semifinal:
    #   2 championship games
    #
    # Championship:
    #   1 championship game
    # --------------------------------------------------------

    expected_cards = {
        "Quarterfinal": 4,
        "Semifinal": 2,
        "Championship": 1,
    }

    championship_card_count = (
        expected_cards[round_name]
    )

    vs_elements = container.get_by_text(
        "vs",
        exact=True,
    )

    games = []

    for i in range(
        min(
            championship_card_count,
            vs_elements.count(),
        )
    ):

        vs = vs_elements.nth(i)

        card = (
            vs
            .locator("..")
            .locator("..")
        )

        text = card.inner_text()

        try:

            game = parse_matchup(
                text,
                year,
                week,
                round_name,
            )

            if game is not None:
                games.append(game)

        except Exception as e:

            print()
            print(
                f"WARNING parsing playoff card "
                f"{i + 1}:"
            )

            print(e)

    return games


# ============================================================
# SAVE
# ============================================================

def save_games(games):

    games = sorted(
        games,
        key=lambda x: (
            x["year"],
            x["week"],
            x["team_1"],
        ),
    )

    with open(
        OUTPUT_JSON,
        "w",
    ) as f:

        json.dump(
            games,
            f,
            indent=2,
        )

    pd.DataFrame(
        games
    ).to_csv(
        OUTPUT_CSV,
        index=False,
    )


# ============================================================
# MAIN COLLECTOR
# ============================================================

with sync_playwright() as p:

    context = (
        p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
        )
    )

    print()
    print("=" * 80)
    print("YAHOO CHAMPIONSHIP PLAYOFF COLLECTOR")
    print("=" * 80)

    print()
    print(
        "Navigate Yahoo manually."
    )

    print()
    print(
        "The collector watches for playoff pages "
        "from 2018 through 2025."
    )

    print()
    print(
        "For each season, navigate through:"
    )

    print()
    print(
        "Quarterfinal → Semifinal → Championship"
    )

    print()
    print(
        "The script will save Championship Bracket "
        "games automatically."
    )

    print()
    print(
        "Consolation games will NOT be counted."
    )

    print()

    all_games = []

    collected = set()

    last_page_key = None


    while True:

        (
            page,
            heading,
            year,
            week,
        ) = detect_playoff_page(
            context
        )

        if year is None:
            time.sleep(1)
            continue


        key = (
            year,
            week,
        )


        if key == last_page_key:
            time.sleep(1)
            continue


        last_page_key = key


        round_name = (
            PLAYOFF_WEEKS[year][week]
        )


        print()
        print("-" * 80)
        print(
            f"Detected {year} "
            f"{round_name} "
            f"(Week {week})"
        )
        print("-" * 80)


        if key in collected:

            print(
                "Already collected."
            )

            time.sleep(1)
            continue


        games = scrape_playoff_week(
            page,
            heading,
            year,
            week,
        )


        expected_games = {
            "Quarterfinal": 2,
            "Semifinal": 2,
            "Championship": 1,
        }[round_name]


        print()
        print(
            f"Found {len(games)} "
            f"Championship Bracket game(s)."
        )


        if len(games) != expected_games:

            print()
            print(
                f"WARNING: Expected "
                f"{expected_games} games."
            )

            print(
                "Not saving this page yet."
            )

            continue


        all_games.extend(
            games
        )

        collected.add(
            key
        )

        save_games(
            all_games
        )


        print()
        print(
            f"Saved {year} {round_name}."
        )

        print()
        print(
            f"Total playoff games saved: "
            f"{len(all_games)}"
        )


        # ----------------------------------------------------
        # CHECK COMPLETION
        # ----------------------------------------------------

        required = {
            (
                year,
                week,
            )
            for year, weeks
            in PLAYOFF_WEEKS.items()
            for week in weeks
        }


        remaining = (
            required
            - collected
        )


        print()
        print(
            f"Rounds remaining: "
            f"{len(remaining)}"
        )


        if not remaining:

            print()
            print("=" * 80)
            print(
                "PLAYOFF COLLECTION COMPLETE"
            )
            print("=" * 80)

            break


        time.sleep(1)


    input(
        "\nPress ENTER to close Chromium: "
    )

    context.close()
