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

YEAR = 2021
LEAGUE_ID = "410355"

START_URL = (
    "https://football.fantasysports.yahoo.com/"
    f"{YEAR}/f1/{LEAGUE_ID}/transactions"
)


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
# PARSE TRANSACTION ROW
# ============================================================

def parse_transaction_row(row):

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
        "year": YEAR,
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

def scrape_current_page(page):

    rows = page.locator(
        "table tr"
    )

    transactions = []

    for i in range(
        rows.count()
    ):

        transaction = (
            parse_transaction_row(
                rows.nth(i)
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
# FIND NEXT PAGE
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


    # Yahoo sometimes renders the navigation
    # more than once. They generally point
    # to the same location.
    return candidates[0]


# ============================================================
# MAIN
# ============================================================

with sync_playwright() as p:

    context = (
        p.chromium
        .launch_persistent_context(
            user_data_dir=str(
                PROFILE_DIR
            ),
            headless=False,
        )
    )

    pages = context.pages

    if pages:
        page = pages[0]
    else:
        page = context.new_page()


    print()
    print("=" * 80)
    print("2021 YAHOO TRANSACTION COLLECTOR")
    print("=" * 80)

    print()
    print(
        "Paste this URL into the SAME Chromium tab:"
    )

    print()
    print(
        START_URL
    )

    print()
    print(
        "Wait until the 2021 transaction page "
        "is visibly loaded."
    )

    print()

    input(
        "Press ENTER when the 2021 transactions are visible: "
    )


    # ========================================================
    # IMPORTANT:
    # Read the page you manually loaded FIRST.
    # We do not navigate anywhere yet.
    # ========================================================

    all_transactions = []

    seen_transactions = set()

    seen_pages = set()

    page_number = 1


    while True:

        print()
        print("=" * 80)
        print(
            f"TRANSACTION PAGE {page_number}"
        )
        print("=" * 80)

        print()
        print(
            "URL:"
        )
        print(
            page.url
        )


        # ----------------------------------------------------
        # SCRAPE CURRENT PAGE
        # ----------------------------------------------------

        transactions = (
            scrape_current_page(
                page
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
        # FIND YAHOO'S ACTUAL NEXT LINK
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
                "Reached the end of the "
                "transaction history."
            )

            break


        print()
        print(
            "Yahoo Next 25 URL:"
        )
        print(
            next_url
        )


        # Prevent loops
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


        # ----------------------------------------------------
        # NAVIGATE USING YAHOO'S ACTUAL LINK
        # ----------------------------------------------------

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


    # ========================================================
    # SAVE CORRECTED 2021 DATA
    # ============================================================

    df = pd.DataFrame(
        all_transactions
    )


    csv_path = (
        OUTPUT_DIR
        / "2021.csv"
    )

    json_path = (
        OUTPUT_DIR
        / "2021.json"
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
            all_transactions,
            f,
            indent=2,
        )


    # ========================================================
    # SUMMARY
    # ============================================================

    print()
    print("=" * 80)
    print("2021 TRANSACTION COLLECTION COMPLETE")
    print("=" * 80)

    print()
    print(
        f"Total transactions: "
        f"{len(df)}"
    )


    if not df.empty:

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
            "First few dates:"
        )

        print()

        print(
            df[
                "date"
            ]
            .head(10)
            .to_string(
                index=False
            )
        )


        print()
        print(
            "Last few dates:"
        )

        print()

        print(
            df[
                "date"
            ]
            .tail(10)
            .to_string(
                index=False
            )
        )


    print()
    print(
        f"Saved: {csv_path}"
    )

    print(
        f"Saved: {json_path}"
    )


    input(
        "\nPress ENTER to close Chromium: "
    )

    context.close()
