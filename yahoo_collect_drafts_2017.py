from pathlib import Path
import json
import re

import pandas as pd
from playwright.sync_api import sync_playwright

from team_aliases import canonical_team


PROFILE_DIR = Path("yahoo_browser_profile")
OUTPUT_DIR = Path("data/drafts")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


LEAGUE_IDS = {
    2017: "1121308",
}


# ============================================================
# TEAM NAME FIXES
# ============================================================

KNOWN_TEAMS = [
    "Big Sack Jack",
    "Buttermilk Puuump",
    "Dillon Panthers",
    "Ginger FC",
    "Joe Mantegna",
    "Malle ❤️ 🐸",
    "Patty Primetimes",
    "PickUpYourBratsMalle",
    "Pop Lockett Drop it",
    "Post Mahomes",
    "The Big Gronkowski",
    "ThreatLevelMidnight",
    "Uncle Rico",
    "Voldemort",
    "You Better Park It",
    "malle_dips_pouches",
]


def normalize_team_name(raw_name):

    raw_name = raw_name.strip()

    # Exact match
    if raw_name in KNOWN_TEAMS:
        return canonical_team(raw_name)

    # Yahoo often truncates team names visually with ...
    if raw_name.endswith("..."):

        prefix = raw_name[:-3].strip()

        matches = [
            team
            for team in KNOWN_TEAMS
            if team.startswith(prefix)
        ]

        if len(matches) == 1:
            return canonical_team(matches[0])

    return canonical_team(raw_name)


# ============================================================
# PARSE ONE ROUND TABLE
# ============================================================

def parse_round_table(table, year):

    rows = table.locator("tr")

    if rows.count() < 2:
        return []

    heading = rows.nth(0).inner_text().strip()

    match = re.search(
        r"Round\s+(\d+)",
        heading,
        re.IGNORECASE,
    )

    if not match:
        return []

    round_number = int(
        match.group(1)
    )

    picks = []

    for i in range(
        1,
        rows.count(),
    ):

        row = rows.nth(i)

        try:
            text = row.inner_text().strip()
        except Exception:
            continue

        if not text:
            continue


        # ====================================================
        # DETECT KEEPER
        # ====================================================

        keeper = False

        try:

            keeper_markers = row.locator(
                '[title="This player is a keeper."]'
            )

            keeper = (
                keeper_markers.count()
                > 0
            )

        except Exception:

            # Fallback to raw HTML
            try:

                html = row.evaluate(
                    "(el) => el.outerHTML"
                )

                keeper = (
                    'title="This player is a keeper."'
                    in html
                )

            except Exception:
                keeper = False


        # ====================================================
        # GET CELLS DIRECTLY
        # ====================================================

        cells = row.locator("td")

        if cells.count() < 3:
            continue


        # ----------------------------------------------------
        # PICK NUMBER
        # ----------------------------------------------------

        pick_text = (
            cells.nth(0)
            .inner_text()
            .strip()
        )

        pick_match = re.search(
            r"(\d+)",
            pick_text,
        )

        if not pick_match:
            continue

        pick_in_round = int(
            pick_match.group(1)
        )


        # ----------------------------------------------------
        # PLAYER
        # ----------------------------------------------------

        player_cell = cells.nth(1)

        player_links = player_cell.locator(
            "a.name"
        )

        if player_links.count() > 0:

            player = (
                player_links
                .first
                .inner_text()
                .strip()
            )

        else:

            player = (
                player_cell
                .inner_text()
                .strip()
            )

            # Remove Yahoo icon glyphs if needed
            player = re.sub(
                r"[-]",
                "",
                player,
            ).strip()


        # ----------------------------------------------------
        # TEAM
        # ----------------------------------------------------

        team_cell = cells.nth(2)

        # Yahoo provides the FULL team name in title=""
        raw_team = (
            team_cell.get_attribute(
                "title"
            )
        )

        if not raw_team:

            raw_team = (
                team_cell
                .inner_text()
                .strip()
            )

        team = normalize_team_name(
            raw_team
        )


        # ----------------------------------------------------
        # OVERALL PICK
        # ----------------------------------------------------

        overall_pick = (
            (round_number - 1)
            * 12
            + pick_in_round
        )


        # ----------------------------------------------------
        # SAVE PICK
        # ----------------------------------------------------

        picks.append({
            "year": year,
            "round": round_number,
            "pick_in_round": pick_in_round,
            "overall_pick": overall_pick,
            "team": team,
            "player": player,
            "keeper": keeper,
        })

    return picks


# ============================================================
# PARSE CURRENT DRAFT PAGE
# ============================================================

def scrape_current_page(
    page,
    year,
):

    tables = page.locator(
        "table"
    )

    all_picks = []

    for i in range(
        tables.count()
    ):

        table = tables.nth(i)

        try:

            picks = parse_round_table(
                table,
                year,
            )

        except Exception as e:

            print(
                f"WARNING parsing table "
                f"{i}: {e}"
            )

            continue

        all_picks.extend(
            picks
        )

    return all_picks


# ============================================================
# SAVE SEASON
# ============================================================

def save_season(
    year,
    picks,
):

    year_csv = (
        OUTPUT_DIR
        / f"{year}.csv"
    )

    year_json = (
        OUTPUT_DIR
        / f"{year}.json"
    )

    df = pd.DataFrame(
        picks
    )

    df = df.sort_values(
        "overall_pick"
    )

    df.to_csv(
        year_csv,
        index=False,
    )

    with open(
        year_json,
        "w",
    ) as f:

        json.dump(
            df.to_dict(
                orient="records"
            ),
            f,
            indent=2,
        )

    return df


# ============================================================
# MAIN
# ============================================================

all_drafts = []


with sync_playwright() as p:

    browser = p.chromium.connect_over_cdp(
        "http://127.0.0.1:9222"
    )

    if not browser.contexts:
        raise RuntimeError(
            "Could not find the existing Yahoo browser context."
        )

    context = browser.contexts[0]

    candidates = []

    print()
    print("YAHOO DRAFT PAGE TARGETS")
    print()

    for i, candidate in enumerate(context.pages):
        try:
            url = candidate.url
            title = candidate.title()

            try:
                body = candidate.locator("body").inner_text(
                    timeout=5000
                )
            except Exception:
                body = ""

            if "football.fantasysports.yahoo.com" in url:
                print(
                    f"Target {i}: "
                    f"title={title!r}, "
                    f"body={len(body):,}"
                )
                print(f"          {url}")

                candidates.append(
                    (
                        len(body),
                        candidate,
                    )
                )

        except Exception:
            continue

    if not candidates:
        raise RuntimeError(
            "No Yahoo Fantasy pages are visible to Playwright."
        )

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    body_size, page = candidates[0]

    if body_size < 1000:
        raise RuntimeError(
            "Yahoo Draft Results is not exposed as a rendered page. "
            "Make sure the completed 2017 Draft Results page is visibly "
            "open in Chrome for Testing before running this script."
        )

    print()
    print("CONNECTED TO 2017 DRAFT PAGE")
    print("Title:", page.title())
    print("URL:  ", page.url)
    print("Body characters:", body_size)
    print()


    print()
    print("=" * 80)
    print(
        "YAHOO HISTORICAL DRAFT + "
        "KEEPER COLLECTOR"
    )
    print("=" * 80)

    print()
    print(
        "This script will NOT "
        "navigate Yahoo for you."
    )

    print()
    print(
        "For each season, paste "
        "the Draft Results URL "
        "into the SAME Chromium tab."
    )

    print()
    print(
        "Keeper selections will be "
        "detected automatically."
    )

    print()


    # ========================================================
    # EACH SEASON
    # ========================================================

    for year, league_id in (
        LEAGUE_IDS.items()
    ):

        expected_url = (
            "https://football."
            "fantasysports.yahoo.com/"
            f"{year}/f1/"
            f"{league_id}/draftresults"
        )


        print()
        print("=" * 80)
        print(
            f"{year} DRAFT"
        )
        print("=" * 80)

        print()
        print(
            "Paste this into Chromium:"
        )

        print()
        print(
            expected_url
        )

        print()
        print(
            "Wait until the completed "
            "draft results are visibly loaded."
        )

        print()


        input(
            f"Press ENTER when "
            f"{year} Draft Results "
            f"are visible: "
        )


        print()
        print(
            "Current page:"
        )
        print(
            page.url
        )

        print()
        print(
            "Title:"
        )
        print(
            page.title()
        )

        print()


        # ====================================================
        # SCRAPE
        # ====================================================

        picks = scrape_current_page(
            page,
            year,
        )


        if not picks:

            print(
                f"ERROR: No draft picks "
                f"found for {year}."
            )

            print(
                "Do not continue yet."
            )

            input(
                "Press ENTER after "
                "checking the page: "
            )

            continue


        # ====================================================
        # SAVE SEASON
        # ====================================================

        df = save_season(
            year,
            picks,
        )


        print(
            f"Found {len(df)} "
            f"draft picks."
        )


        print(
            f"Rounds found: "
            f"{sorted(df['round'].unique())}"
        )


        print(
            f"Teams found: "
            f"{df['team'].nunique()}"
        )


        # ====================================================
        # KEEPER SUMMARY
        # ====================================================

        keeper_count = int(
            df["keeper"].sum()
        )


        print()
        print(
            f"Keepers found: "
            f"{keeper_count}"
        )


        if keeper_count > 0:

            print()
            print(
                "Keeper selections:"
            )

            keepers = (
                df[
                    df["keeper"]
                ][
                    [
                        "round",
                        "pick_in_round",
                        "overall_pick",
                        "team",
                        "player",
                    ]
                ]
                .copy()
            )

            print()

            print(
                keepers.to_string(
                    index=False
                )
            )


        # ====================================================
        # ROUND VALIDATION
        # ====================================================

        round_counts = (
            df
            .groupby(
                "round"
            )
            .size()
        )


        print()
        print(
            "Picks by round:"
        )


        bad_rounds = []


        for (
            round_number,
            count,
        ) in round_counts.items():

            status = (
                "OK"
                if count == 12
                else "CHECK"
            )

            print(
                f"  Round "
                f"{int(round_number):2}: "
                f"{count} picks "
                f"[{status}]"
            )


            if count != 12:

                bad_rounds.append(
                    int(
                        round_number
                    )
                )


        if bad_rounds:

            print()
            print(
                "WARNING: One or more "
                "rounds did not contain "
                "12 picks."
            )

            print(
                "Check before moving "
                "to the next season."
            )

            input(
                "Press ENTER to "
                "continue anyway: "
            )


        # ====================================================
        # ADD TO MASTER
        # ====================================================

        all_drafts.extend(
            df.to_dict(
                orient="records"
            )
        )


    # ========================================================
    # SAVE MASTER DATASET
    # ========================================================

    master = pd.DataFrame(
        all_drafts
    )


    master = (
        master
        .sort_values(
            [
                "year",
                "overall_pick",
            ]
        )
        .reset_index(
            drop=True
        )
    )


    master_csv = (
        OUTPUT_DIR
        / "all_drafts.csv"
    )

    master_json = (
        OUTPUT_DIR
        / "all_drafts.json"
    )


    master.to_csv(
        master_csv,
        index=False,
    )


    with open(
        master_json,
        "w",
    ) as f:

        json.dump(
            master.to_dict(
                orient="records"
            ),
            f,
            indent=2,
        )


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 80)
    print(
        "DRAFT + KEEPER "
        "COLLECTION COMPLETE"
    )
    print("=" * 80)


    print()
    print(
        f"Total picks saved: "
        f"{len(master)}"
    )


    print(
        f"Total keepers found: "
        f"{int(master['keeper'].sum())}"
    )


    print()
    print(
        "Keepers by season:"
    )


    keeper_by_year = (
        master
        .groupby(
            "year"
        )["keeper"]
        .sum()
    )


    for (
        year,
        count,
    ) in keeper_by_year.items():

        print(
            f"  {int(year)}: "
            f"{int(count)}"
        )


    print()
    print(
        f"Master CSV: "
        f"{master_csv}"
    )

    print(
        f"Master JSON: "
        f"{master_json}"
    )


    print()

    input(
        "Press ENTER to close Chromium: "
    )


    context.close()
