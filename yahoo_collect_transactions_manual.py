from pathlib import Path
import json
import re

import pandas as pd
from playwright.sync_api import sync_playwright

from team_aliases import canonical_team


PROFILE_DIR = Path("yahoo_browser_profile")
OUTPUT_DIR = Path("data/transactions")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# SEASONS TO RECOLLECT
# ============================================================

LEAGUE_IDS = {
    2025: "637567",
}

# Existing season files that should ultimately be included
# in the master transaction dataset.
MASTER_YEARS = range(2019, 2026)


# ============================================================
# CLEAN PLAYER NAME
# ============================================================

def clean_player_name(text):

    text = text.strip()

    # Remove Yahoo private-use icon characters.
    text = re.sub(
        r"[\ue000-\uf8ff]",
        "",
        text,
    ).strip()

    # Example:
    #
    #   Sam LaPorta Det - TE Q
    #
    # becomes:
    #
    #   Sam LaPorta

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
            parts[acquisition_index - 1]
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
            parts[drop_index - 1]
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

        if date_pattern.match(parts[i]):

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
            parts[date_index - 1]
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

def scrape_current_page(page, year):

    rows = page.locator("table tr")

    transactions = []

    for i in range(rows.count()):

        transaction = parse_transaction_row(
            rows.nth(i),
            year,
        )

        if transaction:
            transactions.append(transaction)

    return transactions


# ============================================================
# UNIQUE TRANSACTION KEY
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
# VERIFY TRANSACTION PAGE
#
# Do NOT rely on page.url.
# Yahoo/Chromium has sometimes reported about:blank or a
# stale URL even when the correct transaction page is visible.
# ============================================================

def verify_transaction_page(page, year):

    try:

        title = page.title()

        body = (
            page
            .locator("body")
            .inner_text()
        )

        row_count = (
            page
            .locator("table tr")
            .count()
        )

    except Exception as e:

        print()
        print("Could not read the Yahoo page:")
        print(e)

        return False


    has_transaction_title = (
        "Transactions" in title
    )

    has_transaction_body = (
        "Recent Transactions" in body
        or "All Transactions" in body
    )

    has_filters = (
        "Added Players" in body
        and "Dropped Players" in body
        and "Trades" in body
    )

    has_rows = (
        row_count > 0
    )


    if (
        (has_transaction_title or has_transaction_body)
        and has_filters
        and has_rows
    ):

        print()
        print(
            f"Yahoo transaction page detected "
            f"for the season you selected ({year})."
        )

        return True


    print()
    print("!" * 80)
    print("TRANSACTION PAGE NOT DETECTED")
    print("!" * 80)

    print()
    print(
        f"The script is waiting for the {year} "
        f"Yahoo Transactions page."
    )

    print()
    print(
        "Make sure Recent Transactions are "
        "visibly loaded in Chromium."
    )

    print()
    print("Playwright title:")
    print(title)

    return False


# ============================================================
# CHECK FOR NEXT 25
# ============================================================

def has_next_25(page):

    try:

        next_links = page.get_by_text(
            "Next 25",
            exact=True,
        )

        return next_links.count() > 0

    except Exception:

        return False


# ============================================================
# PAGE FINGERPRINT
#
# We compare the actual transactions rather than the URL.
# ============================================================

def page_fingerprint(transactions):

    return tuple(
        transaction_key(transaction)
        for transaction in transactions
    )


# ============================================================
# CHECKPOINT SAVE
#
# THIS IS THE IMPORTANT CHANGE.
#
# The season is saved after EVERY successfully scraped page.
# ============================================================

def checkpoint_save(
    year,
    transactions,
):

    csv_path = (
        OUTPUT_DIR
        / f"{year}.csv"
    )

    json_path = (
        OUTPUT_DIR
        / f"{year}.json"
    )


    df = pd.DataFrame(
        transactions
    )


    if not df.empty:

        df = (
            df
            .drop_duplicates(
                subset=[
                    "year",
                    "date",
                    "team",
                    "added_player",
                    "acquisition_type",
                    "dropped_player",
                ],
                keep="first",
            )
            .reset_index(
                drop=True
            )
        )


    # Write CSV.
    df.to_csv(
        csv_path,
        index=False,
    )


    # Convert NaN to None for JSON.
    json_records = (
        df
        .where(
            pd.notnull(df),
            None,
        )
        .to_dict(
            orient="records"
        )
    )


    with open(
        json_path,
        "w",
    ) as f:

        json.dump(
            json_records,
            f,
            indent=2,
        )


    print()
    print(
        f"CHECKPOINT SAVED: "
        f"{year} = {len(df)} transactions"
    )

    print(
        f"  {csv_path}"
    )


    return df


# ============================================================
# REBUILD MASTER DATASET
# ============================================================

def rebuild_master():

    frames = []


    print()
    print("=" * 80)
    print("REBUILDING MASTER TRANSACTION DATASET")
    print("=" * 80)


    for year in MASTER_YEARS:

        csv_path = (
            OUTPUT_DIR
            / f"{year}.csv"
        )


        if not csv_path.exists():

            print(
                f"{year}: MISSING"
            )

            continue


        try:

            df = pd.read_csv(
                csv_path
            )

        except pd.errors.EmptyDataError:

            print(
                f"{year}: EMPTY"
            )

            continue


        print(
            f"{year}: "
            f"{len(df)} transactions"
        )


        frames.append(
            df
        )


    if not frames:

        print()
        print(
            "No transaction files found."
        )

        return


    master = pd.concat(
        frames,
        ignore_index=True,
    )


    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    duplicate_columns = [
        "year",
        "date",
        "team",
        "added_player",
        "acquisition_type",
        "dropped_player",
    ]


    available_columns = [
        column
        for column in duplicate_columns
        if column in master.columns
    ]


    before = len(master)


    master = (
        master
        .drop_duplicates(
            subset=available_columns,
            keep="first",
        )
        .reset_index(
            drop=True
        )
    )


    duplicates_removed = (
        before - len(master)
    )


    # ========================================================
    # SAVE MASTER
    # ========================================================

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


    json_records = (
        master
        .where(
            pd.notnull(master),
            None,
        )
        .to_dict(
            orient="records"
        )
    )


    with open(
        master_json,
        "w",
    ) as f:

        json.dump(
            json_records,
            f,
            indent=2,
        )


    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 80)
    print("MASTER TRANSACTION DATASET")
    print("=" * 80)

    print()
    print(
        f"Duplicates removed: "
        f"{duplicates_removed}"
    )

    print(
        f"Total transactions: "
        f"{len(master)}"
    )

    print()
    print(
        "Transactions by season:"
    )


    counts = (
        master
        .groupby("year")
        .size()
    )


    for year, count in counts.items():

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
    print("CHECKPOINT YAHOO TRANSACTION COLLECTOR")
    print("=" * 80)

    print()
    print(
        "This run recollects:"
    )

    print()
    print("    2024")
    print("    2025")

    print()
    print(
        "2019–2023 will not be recollected."
    )

    print()
    print(
        "IMPORTANT:"
    )

    print()
    print(
        "The season CSV and JSON are saved "
        "after EVERY transaction page."
    )

    print()
    print(
        "If Yahoo shows a bogus Next 25 link "
        "at the end, Ctrl+C will NOT lose "
        "the pages already collected."
    )


    # ========================================================
    # COLLECT 2024 + 2025
    # ========================================================

    for year, league_id in LEAGUE_IDS.items():


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
            "Paste this URL into the SAME "
            "Chromium tab:"
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


        # ====================================================
        # WAIT FOR FIRST PAGE
        # ====================================================

        while True:

            print()

            input(
                f"Press ENTER when "
                f"{year} is visibly loaded: "
            )


            if verify_transaction_page(
                page,
                year,
            ):

                break


            print()
            print(
                "Make sure the transaction page "
                "is visibly loaded in Chromium."
            )


        # ====================================================
        # START FRESH FOR THIS SEASON
        # ====================================================

        transactions = []

        seen_transactions = set()

        seen_fingerprints = set()

        page_number = 1


        # ====================================================
        # COLLECT PAGES
        # ====================================================

        while True:

            print()
            print("-" * 80)

            print(
                f"{year} — PAGE "
                f"{page_number}"
            )

            print("-" * 80)


            if not verify_transaction_page(
                page,
                year,
            ):

                print()
                print(
                    "Transaction page is not "
                    "currently readable."
                )

                input(
                    "Fix Chromium, then "
                    "press ENTER: "
                )

                continue


            # ------------------------------------------------
            # SCRAPE PAGE
            # ------------------------------------------------

            page_transactions = (
                scrape_current_page(
                    page,
                    year,
                )
            )


            fingerprint = (
                page_fingerprint(
                    page_transactions
                )
            )


            # ------------------------------------------------
            # SAME PAGE AGAIN
            # ------------------------------------------------

            if fingerprint in seen_fingerprints:

                print()
                print(
                    "This exact transaction page "
                    "has already been scraped."
                )

                print()
                print(
                    "If there really is another page, "
                    "click Next 25 and wait until the "
                    "rows visibly change."
                )

                print()
                print(
                    "If there are NO more transactions, "
                    "your latest checkpoint is already "
                    "safely saved."
                )

                print()
                print(
                    "You may use Ctrl+C at this point "
                    "without losing collected data."
                )


                input(
                    "\nPress ENTER after another "
                    "page is visible: "
                )

                continue


            seen_fingerprints.add(
                fingerprint
            )


            print()
            print(
                f"Rows found: "
                f"{len(page_transactions)}"
            )


            # ------------------------------------------------
            # ADD UNIQUE TRANSACTIONS
            # ------------------------------------------------

            new_count = 0


            for transaction in (
                page_transactions
            ):

                key = transaction_key(
                    transaction
                )


                if key in seen_transactions:
                    continue


                seen_transactions.add(
                    key
                )


                transactions.append(
                    transaction
                )


                new_count += 1


            print(
                f"New transactions: "
                f"{new_count}"
            )

            print(
                f"Running total: "
                f"{len(transactions)}"
            )


            # =================================================
            # CHECKPOINT SAVE AFTER EVERY PAGE
            # =================================================

            checkpoint_save(
                year,
                transactions,
            )


            # ------------------------------------------------
            # NEXT 25?
            # ------------------------------------------------

            next_exists = (
                has_next_25(
                    page
                )
            )


            if not next_exists:

                print()
                print(
                    "No Next 25 link detected."
                )

                print(
                    "Season appears complete."
                )

                break


            print()
            print(
                "Yahoo has a Next 25 link."
            )

            print()
            print(
                "In Chromium:"
            )

            print(
                "    1. Click Next 25"
            )

            print(
                "    2. Wait until the transaction "
                "rows visibly change"
            )

            print(
                "    3. Return here"
            )

            print()
            print(
                "NOTE: Yahoo may leave a Next 25 "
                "link visible even when there is "
                "nothing else."
            )

            print(
                "If that happens, your checkpoint "
                "has already been saved."
            )


            previous_fingerprint = (
                fingerprint
            )


            while True:

                print()

                input(
                    "Press ENTER after the next "
                    "page is visible: "
                )


                if not verify_transaction_page(
                    page,
                    year,
                ):

                    print()
                    print(
                        "Transaction page is not "
                        "fully visible yet."
                    )

                    continue


                next_transactions = (
                    scrape_current_page(
                        page,
                        year,
                    )
                )


                new_fingerprint = (
                    page_fingerprint(
                        next_transactions
                    )
                )


                if (
                    new_fingerprint
                    != previous_fingerprint
                ):

                    break


                print()
                print(
                    "The transaction rows have "
                    "not changed."
                )

                print()
                print(
                    "If there are more transactions, "
                    "click Next 25 and wait."
                )

                print()
                print(
                    "If there are NO more transactions, "
                    f"the current {year} checkpoint "
                    "is already saved."
                )

                print()
                print(
                    "You can safely Ctrl+C."
                )


            page_number += 1


        # ====================================================
        # FINAL SEASON SUMMARY
        # ====================================================

        df = checkpoint_save(
            year,
            transactions,
        )


        print()
        print("=" * 80)
        print(
            f"{year} COMPLETE"
        )
        print("=" * 80)

        print()
        print(
            f"Transactions collected: "
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


    # ========================================================
    # MASTER FILE
    # ========================================================

    rebuild_master()


    print()
    print("=" * 80)
    print(
        "COLLECTION COMPLETE"
    )
    print("=" * 80)


    input(
        "\nPress ENTER to close Chromium: "
    )


    context.close()