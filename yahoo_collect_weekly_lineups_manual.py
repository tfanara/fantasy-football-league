from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from playwright.sync_api import sync_playwright, Page


# =============================================================================
# SETTINGS — FIRST VALIDATION RUN
# =============================================================================

YEAR = 2025
WEEK = 1

LEAGUE_ID = "637567"
BASE_URL = f"https://football.fantasysports.yahoo.com/{YEAR}/f1/{LEAGUE_ID}"

# This matches the Chromium remote-debugging workflow used by the other
# Yahoo browser collectors/inspectors in this project.
CDP_URL = "http://127.0.0.1:9222"

OUTPUT_DIR = (
    Path(__file__).resolve().parent
    / "data"
    / "matchups"
    / "player_week_stats"
)

RAW_DIR = OUTPUT_DIR / "raw"

OUTPUT_CSV = OUTPUT_DIR / f"{YEAR}_week_{WEEK:02d}.csv"
OUTPUT_JSON = OUTPUT_DIR / f"{YEAR}_week_{WEEK:02d}.json"
DIAGNOSTIC_JSON = RAW_DIR / f"{YEAR}_week_{WEEK:02d}_diagnostic.json"
PAGE_HTML = RAW_DIR / f"{YEAR}_week_{WEEK:02d}_page.html"


# =============================================================================
# HELPERS
# =============================================================================

def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


def safe_float(value: Any):
    text = clean_text(value)

    if not text:
        return None

    text = text.replace(",", "")

    # Common Yahoo placeholders.
    if text in {"-", "--", "—", "N/A"}:
        return None

    match = re.search(r"-?\d+(?:\.\d+)?", text)

    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def print_banner(title: str):
    print()
    print("=" * 88)
    print(title)
    print("=" * 88)


def choose_yahoo_page(browser) -> Page:
    pages = []

    for context in browser.contexts:
        pages.extend(context.pages)

    yahoo_pages = [
        page
        for page in pages
        if "football.fantasysports.yahoo.com" in page.url
    ]

    if yahoo_pages:
        # Prefer this league if already open.
        league_pages = [
            page
            for page in yahoo_pages
            if f"/f1/{LEAGUE_ID}" in page.url
        ]

        if league_pages:
            return league_pages[-1]

        return yahoo_pages[-1]

    if not browser.contexts:
        raise RuntimeError(
            "Chromium is connected, but no browser context is available."
        )

    return browser.contexts[0].new_page()


def get_table_snapshot(page: Page) -> list[dict[str, Any]]:
    tables = page.locator("table")
    table_count = tables.count()

    snapshots = []

    for i in range(table_count):
        table = tables.nth(i)

        try:
            html = table.evaluate("(el) => el.outerHTML")
        except Exception:
            html = ""

        try:
            text = clean_text(table.inner_text())
        except Exception:
            text = ""

        try:
            headers = [
                clean_text(x)
                for x in table.locator("thead th").all_inner_texts()
            ]
        except Exception:
            headers = []

        try:
            row_count = table.locator("tbody tr").count()
        except Exception:
            row_count = 0

        snapshots.append(
            {
                "table_index": i,
                "headers": headers,
                "row_count": row_count,
                "text": text,
                "html": html,
            }
        )

    return snapshots


def get_row_cells(row) -> list[str]:
    cells = row.locator("th, td")

    return [
        clean_text(cells.nth(i).inner_text())
        for i in range(cells.count())
    ]


def inspect_row_attributes(row) -> dict[str, Any]:
    return row.evaluate(
        """
        (el) => {
            const attrs = {};
            for (const attr of el.attributes) {
                attrs[attr.name] = attr.value;
            }

            return {
                tag: el.tagName,
                className: el.className || "",
                attrs,
                html: el.outerHTML
            };
        }
        """
    )


def detect_lineup_slot(cells: list[str]) -> str:
    if not cells:
        return ""

    known_slots = {
        "QB",
        "RB",
        "WR",
        "TE",
        "W/R/T",
        "W/R",
        "R/W/T",
        "FLEX",
        "K",
        "DEF",
        "D/ST",
        "BN",
        "BENCH",
        "IR",
    }

    for cell in cells[:3]:
        upper = cell.upper().strip()

        if upper in known_slots:
            return upper

    return ""


def detect_player_name(row, cells: list[str]) -> str:
    # Yahoo player rows frequently expose a player link.
    player_links = row.locator(
        'a[href*="sports.yahoo.com/nfl/players"], '
        'a[href*="/nfl/players/"]'
    )

    if player_links.count():
        name = clean_text(player_links.first.inner_text())

        if name:
            return name

    # Fall back to elements whose class suggests player/name.
    candidates = row.locator(
        '.player, .name, [class*="player"], [class*="Player"]'
    )

    for i in range(min(candidates.count(), 5)):
        name = clean_text(candidates.nth(i).inner_text())

        if name and len(name) <= 80:
            return name

    # Last resort: use a plausible non-slot text cell.
    slot = detect_lineup_slot(cells)

    for cell in cells:
        if (
            cell
            and cell.upper() != slot
            and not re.fullmatch(r"-?\d+(?:\.\d+)?", cell)
            and len(cell) <= 80
        ):
            return cell

    return ""


def detect_nfl_team_position(row) -> tuple[str, str]:
    text = clean_text(row.inner_text())

    # Yahoo commonly renders metadata similar to:
    # "KC - QB" or "KC QB".
    match = re.search(
        r"\b([A-Z]{2,3})\s*[-–]\s*(QB|RB|WR|TE|K)\b",
        text,
    )

    if match:
        return match.group(1), match.group(2)

    match = re.search(
        r"\b(QB|RB|WR|TE|K)\b",
        text,
    )

    if match:
        return "", match.group(1)

    # Team defenses.
    if re.search(r"\bDEF\b|\bD/ST\b", text, re.I):
        return "", "DEF"

    return "", ""


def parse_candidate_player_rows(
    page: Page,
    tables: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    First-pass parser.

    We intentionally keep raw cell values and row HTML. Once the Week 1
    Yahoo structure is confirmed, this can be tightened without losing data.
    """

    parsed = []

    table_locator = page.locator("table")

    for table_info in tables:
        table_index = table_info["table_index"]

        table = table_locator.nth(table_index)
        rows = table.locator("tbody tr")

        for row_index in range(rows.count()):
            row = rows.nth(row_index)

            try:
                cells = get_row_cells(row)
            except Exception:
                continue

            if not cells:
                continue

            lineup_slot = detect_lineup_slot(cells)
            player_name = detect_player_name(row, cells)

            # Strongest signal: recognized lineup slot.
            # Secondary signal: player link exists in row.
            has_player_link = (
                row.locator(
                    'a[href*="sports.yahoo.com/nfl/players"], '
                    'a[href*="/nfl/players/"]'
                ).count()
                > 0
            )

            if not lineup_slot and not has_player_link:
                continue

            nfl_team, player_position = detect_nfl_team_position(row)

            try:
                row_meta = inspect_row_attributes(row)
            except Exception:
                row_meta = {
                    "className": "",
                    "attrs": {},
                    "html": "",
                }

            is_bench = lineup_slot in {"BN", "BENCH"}
            is_starter = bool(lineup_slot) and not is_bench and lineup_slot != "IR"

            numeric_cells = [
                safe_float(cell)
                for cell in cells
            ]

            parsed.append(
                {
                    "year": YEAR,
                    "week": WEEK,
                    "table_index": table_index,
                    "row_index": row_index,
                    "fantasy_team": "",
                    "opponent": "",
                    "matchup_id": "",
                    "player": player_name,
                    "nfl_team": nfl_team,
                    "player_position": player_position,
                    "lineup_slot": lineup_slot,
                    "is_starter": is_starter,
                    "is_bench": is_bench,
                    "fantasy_points": None,
                    "projected_points": None,
                    "raw_cells": json.dumps(
                        cells,
                        ensure_ascii=False,
                    ),
                    "raw_numeric_cells": json.dumps(
                        numeric_cells,
                        ensure_ascii=False,
                    ),
                    "row_class": clean_text(
                        row_meta.get("className")
                    ),
                    "row_attributes": json.dumps(
                        row_meta.get("attrs", {}),
                        ensure_ascii=False,
                    ),
                    "row_html": row_meta.get("html", ""),
                }
            )

    return parsed


def save_diagnostics(
    page: Page,
    tables: list[dict[str, Any]],
    parsed_rows: list[dict[str, Any]],
):
    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    PAGE_HTML.write_text(
        page.content(),
        encoding="utf-8",
    )

    diagnostic = {
        "year": YEAR,
        "week": WEEK,
        "url": page.url,
        "title": page.title(),
        "table_count": len(tables),
        "tables": tables,
        "candidate_player_row_count": len(parsed_rows),
    }

    DIAGNOSTIC_JSON.write_text(
        json.dumps(
            diagnostic,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# =============================================================================
# MAIN
# =============================================================================

def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print_banner("YAHOO WEEKLY LINEUP COLLECTOR — VALIDATION RUN")

    print(f"Season: {YEAR}")
    print(f"Week:   {WEEK}")
    print()
    print(
        "This first version is intentionally limited to one historical week."
    )
    print(
        "It will inspect Yahoo's matchup/lineup HTML before we scale collection."
    )

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(
                CDP_URL,
            )
        except Exception as exc:
            print()
            print("ERROR: Could not connect to Chromium.")
            print()
            print(
                "Start the same remote-debugging Chromium session used by your "
                "other Yahoo collectors, sign in to Yahoo, then run this script again."
            )
            print()
            print(f"Technical error: {exc}")
            sys.exit(1)

        page = choose_yahoo_page(browser)

        # Yahoo historical pages can block automated navigation.
        # Use the same reliable workflow as the existing draft/transaction
        # inspectors: navigate manually in the connected browser, then inspect
        # the page that is already visible.
        matchup_url = f"{BASE_URL}/matchup?week={WEEK}"

        print_banner("MANUAL NAVIGATION REQUIRED")
        print()
        print("In the Chrome for Testing window, paste this URL:")
        print()
        print(matchup_url)
        print()
        print("Wait until the 2025 Week 1 matchup page is fully visible.")
        print("Then come back to this Terminal window.")
        print()

        input("Press ENTER when the Week 1 matchup page is visible: ")

        page.wait_for_timeout(1000)

        # Re-scan open pages after manual navigation in case Yahoo opened
        # or switched tabs while the user navigated.
        page = choose_yahoo_page(browser)

        print()
        print(f"Title: {page.title()}")
        print(f"URL:   {page.url}")

        body_text = clean_text(
            page.locator("body").inner_text()
        )

        if (
            "request denied" in body_text.lower()
            or "sign in" in body_text.lower()
            and "fantasy football" not in body_text.lower()
        ):
            print()
            print(
                "Yahoo did not appear to return the expected authenticated "
                "fantasy page."
            )
            print(
                "Make sure the connected Chromium window is signed in and "
                "can manually view the league."
            )

        print_banner("PAGE TABLE INVENTORY")

        tables = get_table_snapshot(page)

        print(f"Tables found: {len(tables)}")

        for table in tables:
            print()
            print(
                f"TABLE {table['table_index']} — "
                f"{table['row_count']} body rows"
            )

            if table["headers"]:
                print(
                    "Headers:",
                    " | ".join(table["headers"]),
                )

            preview = table["text"][:500]

            if preview:
                print("Preview:")
                print(preview)

        print_banner("FIRST-PASS PLAYER ROW PARSE")

        parsed_rows = parse_candidate_player_rows(
            page,
            tables,
        )

        print(
            f"Candidate player rows found: {len(parsed_rows)}"
        )

        if parsed_rows:
            preview_df = pd.DataFrame(parsed_rows)[
                [
                    "table_index",
                    "row_index",
                    "lineup_slot",
                    "player",
                    "nfl_team",
                    "player_position",
                    "is_starter",
                    "is_bench",
                    "raw_cells",
                ]
            ]

            print()
            print(
                preview_df
                .head(50)
                .to_string(index=False)
            )

        save_diagnostics(
            page,
            tables,
            parsed_rows,
        )

        output_df = pd.DataFrame(parsed_rows)

        if not output_df.empty:
            output_df.to_csv(
                OUTPUT_CSV,
                index=False,
            )

            OUTPUT_JSON.write_text(
                output_df.to_json(
                    orient="records",
                    indent=2,
                    force_ascii=False,
                ),
                encoding="utf-8",
            )

        else:
            # Still write predictable empty outputs with the intended schema.
            columns = [
                "year",
                "week",
                "table_index",
                "row_index",
                "fantasy_team",
                "opponent",
                "matchup_id",
                "player",
                "nfl_team",
                "player_position",
                "lineup_slot",
                "is_starter",
                "is_bench",
                "fantasy_points",
                "projected_points",
                "raw_cells",
                "raw_numeric_cells",
                "row_class",
                "row_attributes",
                "row_html",
            ]

            output_df = pd.DataFrame(
                columns=columns,
            )

            output_df.to_csv(
                OUTPUT_CSV,
                index=False,
            )

            OUTPUT_JSON.write_text(
                "[]",
                encoding="utf-8",
            )

        print_banner("FILES CREATED")

        print(OUTPUT_CSV)
        print(OUTPUT_JSON)
        print(DIAGNOSTIC_JSON)
        print(PAGE_HTML)

        print()
        print("NEXT:")
        print(
            "Run this script once, then send me the terminal output. "
            "The table inventory and parsed rows will tell us exactly how "
            "Yahoo represents starters, bench players, fantasy points, "
            "projections, and stat columns."
        )


if __name__ == "__main__":
    main()