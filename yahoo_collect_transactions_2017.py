from pathlib import Path
import json
import re
from urllib.parse import urljoin

import pandas as pd
from playwright.sync_api import sync_playwright

from team_aliases import canonical_team


PROFILE_DIR = Path("yahoo_browser_profile")
OUTPUT_DIR = Path("data/transactions")

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


LEAGUE_IDS = {
    2017: "1121308",
}


# ============================================================
# CLEAN PLAYER NAME
# ============================================================

def clean_player_name(text):

    text = text.strip()

    text = re.sub(
        r"[\ue000-\uf8ff]",
        "",
        text,
    ).strip()

    match = re.match(
        r"^(.*?)\s+[A-Za-z]{2,3}\s+-\s+"
        r"(QB|RB|WR|TE|K|DEF)\b",
        text,
        re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    return text


# ============================================================
# PARSE ONE TRANSACTION ROW
# ============================================================

def parse_transaction_row(row, year):

    try:
        raw_text = row.inner_text().strip()
    except Exception:
        return None

    if not raw_text:
        return None

    parts = [
        part.strip()
        for part in raw_text.splitlines()
        if part.strip()
    ]

    cleaned = []

    for part in parts:

        part = re.sub(
            r"[\ue000-\uf8ff]",
            "",
            part,
        ).strip()

        if part:
            cleaned.append(part)

    parts = cleaned

    if len(parts) < 3:
        return None


    # ========================================================
    # ACQUISITION
    # ========================================================

    acquisition_index = None
    acquisition_type = None

    for i, part in enumerate(parts):

        if part in [
            "Waiver",
            "Free Agent",
        ]:

            acquisition_index = i
            acquisition_type = part
            break


    added_player = None

    if (
        acquisition_index is not None
        and acquisition_index > 0
    ):

        added_player = clean_player_name(
            parts[
                acquisition_index - 1
            ]
        )


    # ========================================================
    # DROP
    # ========================================================

    drop_index = None

    for i, part in enumerate(parts):

        if part == "To Waivers":

            drop_index = i
            break


    dropped_player = None

    if (
        drop_index is not None
        and drop_index > 0
    ):

        dropped_player = clean_player_name(
            parts[
                drop_index - 1
            ]
        )


    if (
        added_player is None
        and dropped_player is None
    ):
        return None


    # ========================================================
    # DATE
    # ========================================================

    transaction_date = None
    date_index = None

    date_pattern = re.compile(
        r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s+\d{1,2},\s+"
        r"\d{1,2}:\d{2}\s+(am|pm)$",
        re.IGNORECASE,
    )

    for i in range(
        len(parts) - 1,
        -1,
        -1,
    ):

        if date_pattern.match(
            parts[i]
        ):

            transaction_date = parts[i]
            date_index = i
            break


    # ========================================================
    # TEAM
    # ========================================================

    team = None

    if (
        date_index is not None
        and date_index > 0
    ):

        team = canonical_team(
            parts[
                date_index - 1
            ]
        )


    return {
        "year": year,
        "date": transaction_date,
        "team": team,
        "added_player": added_player,
        "acquisition_type": acquisition_type,
        "dropped_player": dropped_player,
        "raw_text": raw_text,
    }


# ============================================================
# SCRAPE CURRENT PAGE
# ============================================================

def scrape_current_page(
    page,
    year,
):

    rows = page.locator(
        "table tr"
    )

    transactions = []

    for i in range(
        rows.count()
    ):

        transaction = (
            parse_transaction_row(
                rows.nth(i),
                year,
            )
        )

        if transaction:
            transactions.append(
                transaction
            )

    return transactions


# ============================================================
# DUPLICATE KEY
# ============================================================

def transaction_key(transaction):

    return (
        transaction["year"],
        transaction["date"],
        transaction["team"],
        transaction["added_player"],
        transaction["acquisition_type"],
        transaction["dropped_player"],
    )


# ============================================================
# FIND YAHOO'S ACTUAL NEXT 25 LINK
# ============================================================

def get_next_url(page):

    links = page.locator("a")

    candidates = []

    for i in range(
        links.count()
    ):

        link = links.nth(i)

        try:

            text = (
                link
                .inner_text()
                .strip()
            )

            href = (
                link
                .get_attribute("href")
            )

        except Exception:
            continue

        if not href:
            continue

        if text == "Next 25":

            full_url = urljoin(
                page.url,
                href,
            )

            candidates.append(
                full_url
            )


    if not candidates:
        return None


    return candidates[0]


# ============================================================
# COLLECT ONE SEASON
# ============================================================

def collect_season(
    page,
    year,
):

    all_transactions = []

    seen_transactions = set()
    seen_pages = set()

    page_number = 1


    while True:

        print()
        print("=" * 80)
        print(
            f"{year} TRANSACTION PAGE "
            f"{page_number}"
        )
        print("=" * 80)

        print()
        print("URL:")
        print(
            page.url
        )


        # ----------------------------------------------------
        # SCRAPE CURRENT PAGE
        # ----------------------------------------------------

        transactions = (
            scrape_current_page(
                page,
                year,
            )
        )


        print()
        print(
            f"Rows found: "
            f"{len(transactions)}"
        )


        new_count = 0


        for transaction in transactions:

            key = transaction_key(
                transaction
            )

            if key in seen_transactions:
                continue


            seen_transactions.add(
                key
            )


            all_transactions.append(
                transaction
            )


            new_count += 1


        print(
            f"New transactions: "
            f"{new_count}"
        )

        print(
            f"Running total: "
            f"{len(all_transactions)}"
        )


        # ----------------------------------------------------
        # FOLLOW YAHOO'S NEXT 25 LINK
        # ----------------------------------------------------

        next_url = get_next_url(
            page
        )


        if next_url is None:

            print()
            print(
                "No 'Next 25' link found."
            )

            print(
                "Reached end of season history."
            )

            break


        print()
        print(
            "Yahoo Next 25 URL:"
        )
        print(
            next_url
        )


        if next_url in seen_pages:

            print()
            print(
                "WARNING: Yahoo returned a "
                "previously visited page."
            )

            print(
                "Stopping to avoid a loop."
            )

            break


        seen_pages.add(
            next_url
        )


        try:

            page.goto(
                next_url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            page.wait_for_timeout(
                1200
            )

        except Exception as e:

            print()
            print(
                "Navigation error:"
            )

            print(
                e
            )

            break


        page_number += 1


    return all_transactions


# ============================================================
# SAVE SEASON
# ============================================================

def save_season(
    year,
    transactions,
):

    df = pd.DataFrame(
        transactions
    )


    csv_path = (
        OUTPUT_DIR
        / f"{year}.csv"
    )


    json_path = (
        OUTPUT_DIR
        / f"{year}.json"
    )


    df.to_csv(
        csv_path,
        index=False,
    )


    with open(
        json_path,
        "w",
    ) as f:

        json.dump(
            transactions,
            f,
            indent=2,
        )


    return df


# ============================================================
# MAIN
# ============================================================

all_transactions = []


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
    print("YAHOO TRANSACTION PAGE TARGETS")
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
            "The rendered 2017 Transactions page is not exposed "
            "to Playwright. Leave it visibly open in Chrome for "
            "Testing and run the collector again."
        )

    print()
    print("CONNECTED TO 2017 TRANSACTIONS PAGE")
    print("Title:", page.title())
    print("URL:  ", page.url)
    print("Body characters:", body_size)
    print()


    print()
    print("=" * 80)
    print(
        "YAHOO HISTORICAL "
        "TRANSACTION COLLECTOR"
    )
    print("=" * 80)

    print()
    print(
        "For each season, paste the "
        "Transactions URL into the SAME "
        "Chromium tab."
    )

    print()
    print(
        "After the first page is loaded, "
        "the script follows Yahoo's actual "
        "'Next 25' links automatically."
    )


    # ========================================================
    # LOOP THROUGH SEASONS
    # ========================================================

    for year, league_id in (
        LEAGUE_IDS.items()
    ):

        expected_url = (
            "https://football."
            "fantasysports.yahoo.com/"
            f"{year}/f1/"
            f"{league_id}/transactions"
        )


        print()
        print("=" * 80)
        print(
            f"{year} TRANSACTIONS"
        )
        print("=" * 80)


        print()
        print(
            "Paste this URL into Chromium:"
        )

        print()
        print(
            expected_url
        )

        print()
        print(
            "Wait until Recent Transactions "
            "are visibly loaded."
        )

        print()


        input(
            f"Press ENTER when "
            f"{year} Transactions "
            f"are visible: "
        )


        # ====================================================
        # DO NOT NAVIGATE YET
        #
        # First scrape the page the user manually loaded.
        # ====================================================

        print()
        print(
            "Page title:"
        )

        print(
            page.title()
        )


        transactions = (
            collect_season(
                page,
                year,
            )
        )


        if not transactions:

            print()
            print(
                f"ERROR: No transactions "
                f"collected for {year}."
            )

            input(
                "Press ENTER to continue: "
            )

            continue


        # ====================================================
        # SAVE SEASON
        # ====================================================

        df = save_season(
            year,
            transactions,
        )


        all_transactions.extend(
            transactions
        )


        # ====================================================
        # SUMMARY
        # ====================================================

        print()
        print("-" * 80)

        print(
            f"{year} COMPLETE"
        )


        print()
        print(
            f"Transactions: "
            f"{len(df)}"
        )


        if (
            "acquisition_type"
            in df.columns
        ):

            print()
            print(
                "Acquisition types:"
            )

            print()

            print(
                df[
                    "acquisition_type"
                ]
                .value_counts(
                    dropna=False
                )
                .to_string()
            )


        print()
        print(
            f"Saved: "
            f"{OUTPUT_DIR / f'{year}.csv'}"
        )


    # ========================================================
    # SAVE MASTER DATASET
    # ========================================================

    master = pd.DataFrame(
        all_transactions
    )


    master_csv = (
        OUTPUT_DIR
        / "all_transactions.csv"
    )


    master_json = (
        OUTPUT_DIR
        / "all_transactions.json"
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
            all_transactions,
            f,
            indent=2,
        )


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 80)
    print(
        "TRANSACTION COLLECTION COMPLETE"
    )
    print("=" * 80)


    print()
    print(
        f"Total transactions saved: "
        f"{len(master)}"
    )


    print()
    print(
        "Transactions by season:"
    )


    if not master.empty:

        season_counts = (
            master
            .groupby("year")
            .size()
        )

        for (
            year,
            count,
        ) in season_counts.items():

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


    input(
        "\nPress ENTER to close Chromium: "
    )


    # Shared Yahoo browser intentionally left open.
