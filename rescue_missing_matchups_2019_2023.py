from __future__ import annotations

from pathlib import Path
import json
import re
import time
import urllib.request

import pandas as pd

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise SystemExit(
        "Playwright is required. Install with: pip install playwright"
    )


BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "data" / "matchups" / "player_week_stats" / "historical_rescues"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEBUGGER = "127.0.0.1:9222"

TARGETS = [
    (2019, 9, "Uncle Rico", 73.20, "malle_dips_pouches", 75.54),
    (2020, 8, "Uncle Rico", 79.02, "malle_dips_pouches", 86.36),
    (2020, 9, "Uncle Rico", 73.40, "Patty Primetimes", 51.94),
    (2021, 8, "Uncle Rico", 73.96, "malle_dips_pouches", 107.60),
    (2021, 9, "Uncle Rico", 102.94, "Patty Primetimes", 110.76),
    (2022, 1, "malle_dips_pouches", 106.32, "Patty Primetimes", 104.70),
    (2022, 2, "Uncle Rico", 95.50, "malle_dips_pouches", 168.52),
    (2022, 3, "Uncle Rico", 114.08, "Patty Primetimes", 89.66),
    (2022, 12, "malle_dips_pouches", 142.66, "Patty Primetimes", 72.00),
    (2022, 13, "Uncle Rico", 128.12, "malle_dips_pouches", 93.44),
    (2022, 14, "Uncle Rico", 135.58, "Patty Primetimes", 95.90),
    (2023, 1, "Uncle Rico", 52.38, "malle_dips_pouches", 80.64),
    (2023, 3, "Uncle Rico", 116.06, "Patty Primetimes", 122.66),
    (2023, 5, "malle_dips_pouches", 112.96, "Patty Primetimes", 110.92),
    (2023, 12, "Uncle Rico", 89.68, "malle_dips_pouches", 90.26),
    (2023, 14, "Uncle Rico", 75.22, "Patty Primetimes", 85.80),
]


def banner(text, char="="):
    print()
    print(char * 100)
    print(text)
    print(char * 100)


def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def money_float(x):
    try:
        return round(float(str(x).replace(",", "").strip()), 2)
    except Exception:
        return None


def extract_numbers(text):
    vals = []
    for m in re.findall(r"(?<!\d)(\d{1,3}\.\d{1,2})(?!\d)", text or ""):
        v = money_float(m)
        if v is not None:
            vals.append(v)
    return vals


def score_pair_present(text, a, b):
    nums = extract_numbers(text)
    return any(abs(x-a) < .011 for x in nums) and any(abs(x-b) < .011 for x in nums)


def connect_chrome():
    playwright = sync_playwright().start()
    browser = playwright.chromium.connect_over_cdp(
        f"http://{DEBUGGER}"
    )
    return playwright, browser


def all_pages(browser):
    pages = []
    for context in browser.contexts:
        pages.extend(context.pages)
    return pages


def list_tabs(browser):
    banner("OPEN CHROME TABS", "-")
    pages = all_pages(browser)

    for i, page in enumerate(pages):
        try:
            title = page.title()
        except Exception:
            title = ""

        try:
            url = page.url
        except Exception:
            url = ""

        print(f"TAB {i}: {title}")
        print(f"       {url}")

    return pages


def choose_tab(browser):
    pages = list_tabs(browser)

    while True:
        raw = input(
            "\nChoose the normal Yahoo Fantasy tab number: "
        ).strip()

        try:
            n = int(raw)

            if 0 <= n < len(pages):
                return pages[n]

        except ValueError:
            pass

        print("Invalid tab number.")


def season_league_id(page, year):
    # If currently on that season, extract it.
    m = re.search(rf"/{year}/f1/(\d+)", page.url)
    if m:
        return m.group(1)

    banner(f"{year} LEAGUE ID")
    return input(f"Enter the {year} Yahoo league ID: ").strip()


def wait_manual(page, url):
    try:
        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=15000,
        )
        time.sleep(1)
        return
    except Exception:
        print("\nAutomatic navigation failed.")

    print("\nPaste this exact URL into the SAME Yahoo Fantasy tab:")
    print(url)

    input(
        "\nPress ENTER when the matchup is visible: "
    )


def page_text(page):
    try:
        return page.locator("body").inner_text()
    except Exception:
        return ""


def find_target_page(page, league_id, target):
    year, week, team1, score1, team2, score2 = target

    banner(
        f"{year} WEEK {week}: {team1} {score1:.2f} vs {team2} {score2:.2f}"
    )

    for team_id in range(1, 21):
        url = (
            f"https://football.fantasysports.yahoo.com/{year}/f1/"
            f"{league_id}/matchup?week={week}&mid1={team_id}"
        )

        print(f"\nTrying Yahoo team ID {team_id}:")
        print(url)

        wait_manual(page, url)
        time.sleep(1)

        text = page_text(page)
        has_scores = score_pair_present(text, score1, score2)
        has_team1 = team1.lower() in text.lower()
        has_team2 = team2.lower() in text.lower()

        print(
            f"Target score pair: {'YES' if has_scores else 'no'} | "
            f"{team1}: {'YES' if has_team1 else 'no'} | "
            f"{team2}: {'YES' if has_team2 else 'no'}"
        )

        # Scores are the strongest identifier because recap labels can replace
        # one or both team names in the broken Yahoo view.
        if has_scores:
            print("\nTARGET MATCHUP FOUND.")
            return url, team_id

    return None, None


def classify_slot(slot):
    s = norm(slot).upper()
    if s in {"BN", "BENCH"}:
        return False, True, False
    if s in {"IR", "IR+", "RES"}:
        return False, False, True
    return True, False, False


def parse_player_tables(page, target, source_url, yahoo_team_id):
    """
    Generic Yahoo matchup table parser using Playwright.
    """
    year, week, target_team1, target_score1, target_team2, target_score2 = target
    rows_out = []

    tables = page.locator("table")
    table_count = tables.count()

    print(f"Tables found: {table_count}")

    for table_index in range(table_count):
        table = tables.nth(table_index)

        try:
            trs = table.locator("tr")
            tr_count = trs.count()
        except Exception:
            continue

        for tr_index in range(tr_count):
            tr = trs.nth(tr_index)

            try:
                cells = [
                    norm(c)
                    for c in tr.locator("th,td").all_inner_texts()
                ]
            except Exception:
                continue

            cells = [c for c in cells if c]

            if len(cells) < 2:
                continue

            joined = " | ".join(cells)

            slot = None
            valid_slots = {
                "QB", "WR", "RB", "TE", "W/R/T", "W/R", "W/T",
                "FLEX", "K", "DEF", "D/ST", "BN", "IR", "IR+"
            }

            for c in cells[:4]:
                if c.upper() in valid_slots:
                    slot = c.upper()
                    break

            if slot is None:
                continue

            player = None

            for c in cells:
                if c.upper() == slot:
                    continue

                if re.fullmatch(
                    r"-?\d+(?:\.\d+)?",
                    c.replace(",", "")
                ):
                    continue

                if len(c) >= 2:
                    player = c
                    break

            if not player:
                player = "(Empty)"

            nums = extract_numbers(joined)
            fantasy_points = nums[-1] if nums else None

            is_starter, is_bench, is_ir = classify_slot(slot)

            rows_out.append({
                "year": year,
                "week": week,
                "target_team_1": target_team1,
                "target_team_1_score": target_score1,
                "target_team_2": target_team2,
                "target_team_2_score": target_score2,
                "yahoo_team_id": yahoo_team_id,
                "source_url": source_url,
                "table_index": table_index,
                "row_index": tr_index,
                "lineup_slot": slot,
                "player": player,
                "fantasy_points_best_effort": fantasy_points,
                "is_starter": is_starter,
                "is_bench": is_bench,
                "is_ir": is_ir,
                "raw_row_text": joined,
            })

    return pd.DataFrame(rows_out)


def main():
    banner("HISTORICAL MISSING-MATCHUP RESCUE — 2019-2023")
    print("Known missing games:", len(TARGETS))
    print("Existing season files will NOT be modified.")
    print("Each rescue is saved separately for review.")

    playwright, browser = connect_chrome()
    chosen_page = choose_tab(browser)

    league_ids = {}
    saved = []

    for i, target in enumerate(TARGETS, start=1):
        year = target[0]

        page = chosen_page

        if year not in league_ids:
            league_ids[year] = season_league_id(page, year)

        banner(f"TARGET {i} OF {len(TARGETS)}", "#")

        url, team_id = find_target_page(
            page, league_ids[year], target
        )

        if not url:
            print("\nNOT FOUND. Skipping without changing anything.")
            continue

        input(
            "\nVerify both teams' player tables/benches are visible, "
            "then press ENTER to capture: "
        )

        df = parse_player_tables(page, target, url, team_id)

        year, week, t1, s1, t2, s2 = target
        safe1 = re.sub(r"[^A-Za-z0-9]+", "_", t1).strip("_")
        safe2 = re.sub(r"[^A-Za-z0-9]+", "_", t2).strip("_")

        out = OUT_DIR / (
            f"{year}_week_{week:02d}_{safe1}_vs_{safe2}_rescue.csv"
        )
        df.to_csv(out, index=False)

        print(f"\nSaved {len(df)} candidate player rows:")
        print(out)

        saved.append({
            "year": year,
            "week": week,
            "team_1": t1,
            "team_1_score": s1,
            "team_2": t2,
            "team_2_score": s2,
            "yahoo_team_id": team_id,
            "source_url": url,
            "rows_saved": len(df),
            "file": str(out),
        })

    summary = pd.DataFrame(saved)
    summary_path = OUT_DIR / "rescue_summary_2019_2023.csv"
    summary.to_csv(summary_path, index=False)

    try:
        playwright.stop()
    except Exception:
        pass

    banner("RESCUE COLLECTION COMPLETE")
    print(f"Targets requested: {len(TARGETS)}")
    print(f"Targets saved:     {len(saved)}")
    print(f"Summary: {summary_path}")
    print()
    print("No original season files were modified.")
    print("Send me this terminal output before integrating the rescue rows.")


if __name__ == "__main__":
    main()