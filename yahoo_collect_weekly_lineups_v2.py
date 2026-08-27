from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from playwright.sync_api import sync_playwright, Page


# =============================================================================
# SETTINGS — VALIDATION RUN V2
# =============================================================================

YEAR = 2025
WEEK = 1

LEAGUE_ID = "637567"
BASE_URL = f"https://football.fantasysports.yahoo.com/{YEAR}/f1/{LEAGUE_ID}"
CDP_URL = "http://127.0.0.1:9222"

OUTPUT_DIR = (
    Path(__file__).resolve().parent
    / "data"
    / "matchups"
    / "player_week_stats"
)

RAW_DIR = OUTPUT_DIR / "raw"

OUTPUT_CSV = OUTPUT_DIR / f"{YEAR}_week_{WEEK:02d}_v2.csv"
OUTPUT_JSON = OUTPUT_DIR / f"{YEAR}_week_{WEEK:02d}_v2.json"
DIAGNOSTIC_JSON = RAW_DIR / f"{YEAR}_week_{WEEK:02d}_v2_diagnostic.json"
PAGE_HTML = RAW_DIR / f"{YEAR}_week_{WEEK:02d}_v2_page.html"


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


def get_table_headers(table) -> list[str]:
    try:
        return [
            clean_text(x)
            for x in table.locator("thead th").all_inner_texts()
        ]
    except Exception:
        return []


def get_row_cells(row) -> list[str]:
    cells = row.locator("th, td")

    return [
        clean_text(cells.nth(i).inner_text())
        for i in range(cells.count())
    ]


def strip_yahoo_player_extras(text: str) -> str:
    """
    Turn:
      Joe BurrowVideo Forecast Final W 17-16 @ Cle
    into:
      Joe Burrow
    """

    text = clean_text(text)

    cut_markers = [
        "Video",
        "Forecast",
        "Final ",
        "Live ",
        "Bye",
    ]

    positions = []

    for marker in cut_markers:
        idx = text.find(marker)
        if idx > 0:
            positions.append(idx)

    if positions:
        text = text[:min(positions)]

    # Remove keeper/icon artifacts if any leak into text.
    text = text.replace("", "").strip()

    return text


def infer_player_position_from_slot(slot: str) -> str:
    slot = clean_text(slot).upper()

    if slot in {"QB", "RB", "WR", "TE", "K"}:
        return slot

    if slot in {"DEF", "D/ST"}:
        return "DEF"

    return ""


def parse_side(
    cells: list[str],
    *,
    side: str,
    table_index: int,
    row_index: int,
    lineup_slot: str,
) -> dict[str, Any]:
    """
    Yahoo matchup roster rows are side-by-side.

    Confirmed structure:
      LEFT:
        0 stats
        1 player
        2 projection
        3 fantasy points
        4 position / lineup slot

      MIDDLE:
        5 position label
        6 position / lineup slot

      RIGHT:
        7 fantasy points
        8 projection
        9 player
        10 stats
    """

    if len(cells) < 11:
        raise ValueError(
            f"Expected at least 11 cells, found {len(cells)}"
        )

    if side == "left":
        stat_summary = cells[0]
        player_text = cells[1]
        projected_points = safe_float(cells[2])
        fantasy_points = safe_float(cells[3])
        raw_position = cells[4]
    else:
        fantasy_points = safe_float(cells[7])
        projected_points = safe_float(cells[8])
        player_text = cells[9]
        stat_summary = cells[10]
        raw_position = cells[6]

    player = strip_yahoo_player_extras(player_text)

    normalized_slot = clean_text(lineup_slot).upper()

    is_bench = normalized_slot in {"BN", "BENCH"}
    is_ir = normalized_slot == "IR"
    is_starter = bool(normalized_slot) and not is_bench and not is_ir

    return {
        "year": YEAR,
        "week": WEEK,
        "table_index": table_index,
        "row_index": row_index,
        "side": side,
        "fantasy_team": "",
        "opponent": "",
        "matchup_id": "",
        "player": player,
        "player_position": infer_player_position_from_slot(raw_position),
        "lineup_slot": normalized_slot,
        "is_starter": is_starter,
        "is_bench": is_bench,
        "is_ir": is_ir,
        "projected_points": projected_points,
        "fantasy_points": fantasy_points,
        "stat_summary": clean_text(stat_summary),
        "raw_player_text": clean_text(player_text),
        "raw_position": clean_text(raw_position),
        "raw_cells": json.dumps(
            cells,
            ensure_ascii=False,
        ),
    }


def is_matchup_roster_table(headers: list[str], row_count: int) -> bool:
    normalized = [h.lower() for h in headers]

    return (
        row_count > 0
        and len(headers) >= 9
        and normalized.count("player") >= 2
        and normalized.count("fan pts") >= 2
        and normalized.count("proj") >= 2
    )


def parse_matchup_tables(page: Page) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    table_locator = page.locator("table")
    parsed_players = []
    table_diagnostics = []

    for table_index in range(table_locator.count()):
        table = table_locator.nth(table_index)

        headers = get_table_headers(table)
        rows = table.locator("tbody tr")
        row_count = rows.count()

        try:
            table_text = clean_text(table.inner_text())
        except Exception:
            table_text = ""

        diagnostic = {
            "table_index": table_index,
            "headers": headers,
            "row_count": row_count,
            "is_matchup_roster_table": is_matchup_roster_table(
                headers,
                row_count,
            ),
            "preview": table_text[:700],
        }

        table_diagnostics.append(diagnostic)

        if not diagnostic["is_matchup_roster_table"]:
            continue

        for row_index in range(row_count):
            row = rows.nth(row_index)
            cells = get_row_cells(row)

            if len(cells) < 11:
                continue

            # The confirmed Yahoo structure repeats the lineup slot across
            # the three center position cells. Use the middle-most value
            # when possible, then fall back.
            lineup_slot = (
                cells[5]
                or cells[4]
                or cells[6]
            )

            left = parse_side(
                cells,
                side="left",
                table_index=table_index,
                row_index=row_index,
                lineup_slot=lineup_slot,
            )

            right = parse_side(
                cells,
                side="right",
                table_index=table_index,
                row_index=row_index,
                lineup_slot=lineup_slot,
            )

            parsed_players.extend(
                [
                    left,
                    right,
                ]
            )

    return parsed_players, table_diagnostics


def save_outputs(
    page: Page,
    players: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

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
        "parsed_player_rows": len(players),
        "tables": diagnostics,
    }

    DIAGNOSTIC_JSON.write_text(
        json.dumps(
            diagnostic,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    df = pd.DataFrame(players)

    df.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    OUTPUT_JSON.write_text(
        df.to_json(
            orient="records",
            indent=2,
            force_ascii=False,
        ),
        encoding="utf-8",
    )

    return df


# =============================================================================
# MAIN
# =============================================================================

def main():
    print_banner("YAHOO WEEKLY LINEUP COLLECTOR — V2")

    print(f"Season: {YEAR}")
    print(f"Week:   {WEEK}")
    print()
    print(
        "This version parses BOTH sides of Yahoo's matchup rows."
    )
    print(
        "It also separates starters from bench players and captures "
        "projection, fantasy points, and the visible stat summary."
    )

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(
                CDP_URL,
            )
        except Exception as exc:
            print()
            print("ERROR: Could not connect to Chrome for Testing.")
            print()
            print(
                "Start the Yahoo browser with remote debugging on port 9222, "
                "then run this script again."
            )
            print()
            print(f"Technical error: {exc}")
            sys.exit(1)

        page = choose_yahoo_page(browser)

        matchup_url = f"{BASE_URL}/matchup?week={WEEK}"

        print_banner("MANUAL NAVIGATION REQUIRED")

        print()
        print("In the Chrome for Testing window, open:")
        print()
        print(matchup_url)
        print()
        print("Wait until the Week 1 matchup page is fully visible.")
        print()

        input("Press ENTER when the matchup page is visible: ")

        page.wait_for_timeout(750)
        page = choose_yahoo_page(browser)

        print()
        print(f"Title: {page.title()}")
        print(f"URL:   {page.url}")

        print_banner("PARSING MATCHUP ROSTER TABLES")

        players, diagnostics = parse_matchup_tables(
            page,
        )

        df = save_outputs(
            page,
            players,
            diagnostics,
        )

        matchup_tables = [
            x
            for x in diagnostics
            if x["is_matchup_roster_table"]
        ]

        print(
            f"Roster tables found: {len(matchup_tables)}"
        )
        print(
            f"Player records parsed: {len(df)}"
        )

        if not df.empty:
            print()
            print(
                df[
                    [
                        "side",
                        "lineup_slot",
                        "player",
                        "projected_points",
                        "fantasy_points",
                        "is_starter",
                        "is_bench",
                        "stat_summary",
                    ]
                ]
                .to_string(index=False)
            )

        print_banner("SUMMARY")

        if not df.empty:
            print(
                f"Starters: {int(df['is_starter'].sum())}"
            )
            print(
                f"Bench:    {int(df['is_bench'].sum())}"
            )

            left_count = int(
                (df["side"] == "left").sum()
            )
            right_count = int(
                (df["side"] == "right").sum()
            )

            print(
                f"Left-side players:  {left_count}"
            )
            print(
                f"Right-side players: {right_count}"
            )

        print_banner("FILES CREATED")

        print(OUTPUT_CSV)
        print(OUTPUT_JSON)
        print(DIAGNOSTIC_JSON)
        print(PAGE_HTML)

        print()
        print(
            "NEXT: Send me this terminal output. "
            "If both sides and bench rows look correct, the next version "
            "will collect all six Week 1 matchups / all 12 franchises."
        )


if __name__ == "__main__":
    main()