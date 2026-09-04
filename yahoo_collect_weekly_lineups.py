from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from playwright.sync_api import sync_playwright, Page

from season_config import CURRENT_SEASON, YAHOO_LEAGUE_IDS, REGULAR_SEASON_END_WEEK


# =============================================================================
# SETTINGS — VALIDATION RUN V2
# =============================================================================

KNOWN_LEAGUE_IDS = {
    year: league_id
    for year, league_id in YAHOO_LEAGUE_IDS.items()
    if 2017 <= year <= CURRENT_SEASON
}


print()
print("Yahoo lineup season collector")
print()

while True:
    raw_year = input("Season to collect (for example 2024): ").strip()

    try:
        YEAR = int(raw_year)
    except ValueError:
        print("Enter a four-digit season such as 2024.")
        continue

    if 2017 <= YEAR <= CURRENT_SEASON:
        break

    print(f"Enter a season from 2017 through {CURRENT_SEASON}.")


LEAGUE_ID = KNOWN_LEAGUE_IDS.get(YEAR)

if not LEAGUE_ID:
    print()
    print(f"Open your {YEAR} Yahoo Fantasy league page.")
    print(
        f"The URL should look like: "
        f"https://football.fantasysports.yahoo.com/{YEAR}/f1/123456"
    )
    print("The digits after /f1/ are the league ID.")
    print()

    while True:
        LEAGUE_ID = input(
            f"Enter the {YEAR} Yahoo league ID: "
        ).strip()

        if LEAGUE_ID.isdigit():
            break

        print("Enter digits only for the Yahoo league ID.")


REGULAR_SEASON_END = REGULAR_SEASON_END_WEEK


START_WEEK = 1
END_WEEK = REGULAR_SEASON_END[YEAR]

BASE_URL = f"https://football.fantasysports.yahoo.com/{YEAR}/f1/{LEAGUE_ID}"
CDP_URL = "http://127.0.0.1:9222"

OUTPUT_DIR = (
    Path(__file__).resolve().parent
    / "data"
    / "matchups"
    / "player_week_stats"
)

RAW_DIR = OUTPUT_DIR / "raw"

SEASON_OUTPUT_CSV = OUTPUT_DIR / f"{YEAR}_weekly_lineups.csv"
SEASON_OUTPUT_JSON = OUTPUT_DIR / f"{YEAR}_weekly_lineups.json"
SEASON_MATCHUPS_CSV = OUTPUT_DIR / f"{YEAR}_matchups.csv"
SEASON_MATCHUPS_JSON = OUTPUT_DIR / f"{YEAR}_matchups.json"


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


def choose_existing_yahoo_page(browser) -> Page:
    """
    Let the user choose the REAL Yahoo Fantasy tab BEFORE navigation.

    Yahoo exposes temporary ad/background targets that can share the same URL,
    so automatic selection is unreliable. Selecting the visible fantasy tab
    first and then keeping that exact Page object is the safest workflow.
    """

    pages = []

    for context in browser.contexts:
        for page in context.pages:
            try:
                if not page.is_closed():
                    pages.append(page)
            except Exception:
                continue

    if not pages:
        raise RuntimeError(
            "Chrome is connected, but no tabs are available."
        )

    print_banner("CHOOSE THE YAHOO FANTASY TAB")

    for i, page in enumerate(pages):
        try:
            title = page.title()
        except Exception:
            title = "(title unavailable)"

        try:
            url = page.url
        except Exception:
            url = "(URL unavailable)"

        print()
        print(f"TAB {i}")
        print(f"Title: {title}")
        print(f"URL:   {url}")

    print()
    print(
        "Choose the tab that you can visibly see as the normal Yahoo Fantasy page."
    )
    print(
        "Do NOT choose a tab titled Advertisement, Pixels, 970x250, or similar."
    )

    while True:
        choice = input("Tab number: ").strip()

        try:
            index = int(choice)
        except ValueError:
            print("Enter one of the tab numbers shown above.")
            continue

        if 0 <= index < len(pages):
            return pages[index]

        print("Enter one of the tab numbers shown above.")


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
        "week": None,
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


def extract_matchup_teams_and_scores(page: Page) -> tuple[str, str, float | None, float | None]:
    """
    Extract the two fantasy team names and matchup scores from the visible
    matchup page.

    Yahoo's matchup page contains a compact score summary table above the
    roster tables. We use the surrounding visible text and links rather than
    hard-coding one fragile CSS class.
    """

    # Try likely team links first.
    team_candidates = []

    links = page.locator('a[href*="/team?"], a[href*="/team/"], a[href*="/f1/"]')

    try:
        link_count = links.count()
    except Exception:
        link_count = 0

    for i in range(link_count):
        link = links.nth(i)

        try:
            txt = clean_text(link.inner_text())
            href = link.get_attribute("href") or ""
        except Exception:
            continue

        if not txt:
            continue

        # Exclude obvious navigation/non-team labels.
        if txt.lower() in {
            "overview",
            "league",
            "my team",
            "matchups",
            "players",
            "draft results",
            "fantasy",
            "network",
            "standings",
        }:
            continue

        if "/f1/" in href:
            team_candidates.append(txt)

    # De-duplicate while preserving order.
    deduped = []
    seen = set()

    for name in team_candidates:
        if name not in seen:
            seen.add(name)
            deduped.append(name)

    # The score summary table is the strongest signal for scores.
    score_left = None
    score_right = None

    tables = page.locator("table")

    try:
        table_count = tables.count()
    except Exception:
        table_count = 0

    for i in range(table_count):
        table = tables.nth(i)

        try:
            txt = clean_text(table.inner_text())
        except Exception:
            continue

        # In the validated Week 1 page, the matchup summary includes:
        # "<left score> Points <right score> <left proj> Orig Proj <right proj>"
        if " Points " in f" {txt} " and "Orig Proj" in txt:
            nums = re.findall(r"-?\d+(?:\.\d+)?", txt)

            if len(nums) >= 2:
                score_left = safe_float(nums[0])
                score_right = safe_float(nums[1])

            break

    # Try page headings/text for team names if link extraction was noisy.
    body_text = ""

    try:
        body_text = clean_text(page.locator("body").inner_text())
    except Exception:
        pass

    # Filter likely team names against the known league franchises when possible.
    known_teams = [
        "malle_dips_pouches",
        "Patty Primetimes",
        "Joe Mantegna",
        "Malle ❤️ 🐸",
        "Buttermilk Puuump",
        "ThreatLevelMidnight",
        "The Big Gronkowski",
        "Pop Lockett Drop it",
        "Voldemort",
        "Post Mahomes",
        "Uncle Rico",
        "Ginger FC",
    ]

    visible_known = [
        team
        for team in known_teams
        if team in body_text
    ]

    # Prefer the two known franchise names visible on the matchup page.
    if len(visible_known) >= 2:
        left_team = visible_known[0]
        right_team = visible_known[1]

    elif len(deduped) >= 2:
        left_team = deduped[0]
        right_team = deduped[1]

    else:
        left_team = ""
        right_team = ""

    return left_team, right_team, score_left, score_right


def matchup_id_for_week(year: int, week: int, pair_index: int) -> str:
    return f"{year}-W{week:02d}-M{pair_index:02d}"


def remove_total_rows(players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned = []

    for row in players:
        if clean_text(row.get("lineup_slot")).upper() == "TOTAL":
            continue

        if clean_text(row.get("player")).upper() == "TOTAL":
            continue

        cleaned.append(row)

    return cleaned

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
        "week": None,
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
    print_banner("YAHOO WEEKLY LINEUP COLLECTOR")

    print(f"Season: {YEAR}")
    print(f"Weeks:  {START_WEEK} through {END_WEEK}")
    print()
    print(
        "This run collects all unique matchups for the selected regular season, "
        "including starters, bench players, IR, projections, fantasy points, "
        "and visible stat summaries."
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    season_players = []
    season_matchups = []

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

        # Choose the real Yahoo Fantasy tab once and keep that exact Page object.
        page = choose_existing_yahoo_page(browser)

        print()
        print(
            "The collector will now try to navigate automatically inside the "
            "Yahoo Fantasy tab you selected."
        )
        print(
            "If Yahoo blocks a page, the script will print the exact URL and "
            "ask you to open it manually in that SAME tab."
        )

        for week in range(START_WEEK, END_WEEK + 1):

            print_banner(
                f"COLLECTING {YEAR} WEEK {week}"
            )

            week_players = []
            week_matchups = []
            seen_matchups = set()
            seen_teams = set()
            unique_matchup_number = 0

            for team_id in range(1, 13):

                if len(seen_matchups) >= 6 and len(seen_teams) >= 12:
                    break

                matchup_url = (
                    f"{BASE_URL}/matchup"
                    f"?week={week}"
                    f"&mid1={team_id}"
                )

                print()
                print(
                    f"Week {week} · Yahoo team ID {team_id} "
                    f"({len(seen_matchups)}/6 unique matchups collected)"
                )

                navigation_ok = False

                try:
                    page.goto(
                        matchup_url,
                        wait_until="domcontentloaded",
                        timeout=30_000,
                    )
                    page.wait_for_timeout(900)

                    # Validate that the real roster tables loaded.
                    _, diagnostics = parse_matchup_tables(
                        page,
                    )

                    roster_table_count = sum(
                        1
                        for d in diagnostics
                        if d.get("is_matchup_roster_table")
                    )

                    if roster_table_count >= 2:
                        navigation_ok = True

                except Exception:
                    navigation_ok = False

                if not navigation_ok:
                    print()
                    print(
                        "Yahoo blocked or failed this automatic navigation."
                    )
                    print()
                    print(
                        "Paste this exact URL into the SAME Yahoo Fantasy tab:"
                    )
                    print()
                    print(matchup_url)
                    print()
                    print(
                        "Wait until the starting lineups and benches are visible."
                    )
                    print()

                    input(
                        "Press ENTER when the matchup page is visible: "
                    )

                    page.wait_for_timeout(1000)

                try:
                    table_count = page.locator("table").count()
                except Exception:
                    table_count = 0

                if table_count == 0:
                    print(
                        "No tables found — skipping this Yahoo team ID."
                    )
                    continue

                players, diagnostics = parse_matchup_tables(
                    page,
                )

                players = remove_total_rows(players)

                roster_table_count = sum(
                    1
                    for d in diagnostics
                    if d.get("is_matchup_roster_table")
                )

                if roster_table_count < 2 or not players:
                    print(
                        "Roster tables were not detected correctly — skipping this Yahoo team ID."
                    )
                    continue

                left_team, right_team, left_score, right_score = (
                    extract_matchup_teams_and_scores(page)
                )

                if not left_team or not right_team:
                    print(
                        "Could not identify both fantasy teams — skipping this Yahoo team ID."
                    )
                    continue

                matchup_key = tuple(
                    sorted(
                        [left_team, right_team]
                    )
                )

                if matchup_key in seen_matchups:
                    print(
                        f"Duplicate: {matchup_key[0]} vs {matchup_key[1]} — skipped."
                    )
                    continue

                unique_matchup_number += 1

                matchup_id = matchup_id_for_week(
                    YEAR,
                    week,
                    unique_matchup_number,
                )

                for row in players:
                    row["week"] = week
                    row["matchup_id"] = matchup_id
                    row["matchup_number"] = unique_matchup_number
                    row["yahoo_team_id_used"] = team_id

                    if row["side"] == "left":
                        row["fantasy_team"] = left_team
                        row["opponent"] = right_team
                        row["team_score"] = left_score
                        row["opponent_score"] = right_score
                    else:
                        row["fantasy_team"] = right_team
                        row["opponent"] = left_team
                        row["team_score"] = right_score
                        row["opponent_score"] = left_score

                week_players.extend(players)

                week_matchups.append(
                    {
                        "year": YEAR,
                        "week": week,
                        "matchup_id": matchup_id,
                        "matchup_number": unique_matchup_number,
                        "yahoo_team_id_used": team_id,
                        "left_team": left_team,
                        "right_team": right_team,
                        "left_score": left_score,
                        "right_score": right_score,
                        "player_records": len(players),
                        "roster_tables": roster_table_count,
                        "url": page.url,
                    }
                )

                seen_matchups.add(matchup_key)
                seen_teams.update(
                    [left_team, right_team]
                )

                print(
                    f"Saved unique matchup {unique_matchup_number}/6: "
                    f"{left_team} vs {right_team} "
                    f"({left_score} - {right_score})"
                )

            # Save each week immediately so progress is preserved.
            week_player_df = pd.DataFrame(
                week_players
            )

            week_matchup_df = pd.DataFrame(
                week_matchups
            )

            week_csv = (
                OUTPUT_DIR
                / f"{YEAR}_week_{week:02d}.csv"
            )

            week_json = (
                OUTPUT_DIR
                / f"{YEAR}_week_{week:02d}.json"
            )

            week_matchups_csv = (
                OUTPUT_DIR
                / f"{YEAR}_week_{week:02d}_matchups.csv"
            )

            week_matchups_json = (
                OUTPUT_DIR
                / f"{YEAR}_week_{week:02d}_matchups.json"
            )

            week_player_df.to_csv(
                week_csv,
                index=False,
            )

            week_json.write_text(
                week_player_df.to_json(
                    orient="records",
                    indent=2,
                    force_ascii=False,
                ),
                encoding="utf-8",
            )

            week_matchup_df.to_csv(
                week_matchups_csv,
                index=False,
            )

            week_matchups_json.write_text(
                week_matchup_df.to_json(
                    orient="records",
                    indent=2,
                    force_ascii=False,
                ),
                encoding="utf-8",
            )

            season_players.extend(
                week_players
            )

            season_matchups.extend(
                week_matchups
            )

            print()
            print(
                f"WEEK {week} SUMMARY: "
                f"{len(seen_matchups)}/6 matchups, "
                f"{len(seen_teams)}/12 teams, "
                f"{len(week_players)} player records."
            )

            if len(seen_matchups) != 6 or len(seen_teams) != 12:
                print(
                    "WARNING: This week is incomplete. "
                    "The files were still saved so we can inspect exactly what is missing."
                )

        print_banner(f"SAVING FULL {YEAR} SEASON")

        season_player_df = pd.DataFrame(
            season_players
        )

        season_matchup_df = pd.DataFrame(
            season_matchups
        )

        season_player_df.to_csv(
            SEASON_OUTPUT_CSV,
            index=False,
        )

        SEASON_OUTPUT_JSON.write_text(
            season_player_df.to_json(
                orient="records",
                indent=2,
                force_ascii=False,
            ),
            encoding="utf-8",
        )

        season_matchup_df.to_csv(
            SEASON_MATCHUPS_CSV,
            index=False,
        )

        SEASON_MATCHUPS_JSON.write_text(
            season_matchup_df.to_json(
                orient="records",
                indent=2,
                force_ascii=False,
            ),
            encoding="utf-8",
        )

        print()
        print(
            f"Weeks attempted:       {END_WEEK - START_WEEK + 1}"
        )
        print(
            f"Matchups saved:        {len(season_matchup_df)}"
        )
        print(
            f"Player records saved:  {len(season_player_df)}"
        )

        if not season_player_df.empty:
            print(
                f"Starters:              {int(season_player_df['is_starter'].sum())}"
            )
            print(
                f"Bench:                 {int(season_player_df['is_bench'].sum())}"
            )
            if "is_ir" in season_player_df.columns:
                print(
                    f"IR:                    {int(season_player_df['is_ir'].sum())}"
                )

        print_banner("MASTER FILES CREATED")

        print(SEASON_OUTPUT_CSV)
        print(SEASON_OUTPUT_JSON)
        print(SEASON_MATCHUPS_CSV)
        print(SEASON_MATCHUPS_JSON)

        print()
        print(
            "NEXT: Send me the week summaries and final season summary. "
            "We will verify whether all regular-season weeks completed before "
            "building the historical multi-season collector."
        )


if __name__ == "__main__":
    main()