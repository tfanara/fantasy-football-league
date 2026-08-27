from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright


YEAR = 2018
WEEK = 9
LEAGUE_ID = input("Enter the 2018 Yahoo league ID: ").strip()
CDP_URL = "http://127.0.0.1:9222"

TARGET_TEAMS = {
    "Big Sack Jack",
    "malle_dips_pouches",
}

TARGET_SCORES = {
    104.76,
    88.24,
}

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "data" / "matchups" / "player_week_stats"
OUT_FILE = OUT_DIR / "2018_week09_missing_matchup_rescue.csv"


def clean_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def safe_float(value):
    text = clean_text(value).replace(",", "")
    if not text or text in {"-", "--", "—", "N/A"}:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    return float(m.group(0))


def choose_page(browser):
    pages = []
    for context in browser.contexts:
        for page in context.pages:
            try:
                if not page.is_closed():
                    pages.append(page)
            except Exception:
                pass

    print()
    print("OPEN CHROME TABS")
    print("=" * 80)

    for i, page in enumerate(pages):
        try:
            print(f"TAB {i}: {page.title()}")
            print(f"       {page.url}")
        except Exception:
            pass

    while True:
        raw = input("Choose the normal Yahoo Fantasy tab number: ").strip()
        try:
            idx = int(raw)
            if 0 <= idx < len(pages):
                return pages[idx]
        except ValueError:
            pass
        print("Enter one of the tab numbers shown above.")


def get_headers(table):
    try:
        return [clean_text(x) for x in table.locator("thead th").all_inner_texts()]
    except Exception:
        return []


def get_cells(row):
    cells = row.locator("th, td")
    return [clean_text(cells.nth(i).inner_text()) for i in range(cells.count())]


def strip_player(text):
    text = clean_text(text)
    for marker in ["Video", "Forecast", "Final ", "Live ", "Bye"]:
        idx = text.find(marker)
        if idx > 0:
            text = text[:idx]
    return text.replace("", "").strip()


def parse_players(page):
    players = []
    tables = page.locator("table")

    for ti in range(tables.count()):
        table = tables.nth(ti)
        headers = [h.lower() for h in get_headers(table)]

        if not (
            headers.count("player") >= 2
            and headers.count("fan pts") >= 2
            and headers.count("proj") >= 2
        ):
            continue

        rows = table.locator("tbody tr")

        for ri in range(rows.count()):
            cells = get_cells(rows.nth(ri))
            if len(cells) < 11:
                continue

            slot = clean_text(cells[5] or cells[4] or cells[6]).upper()

            for side in ["left", "right"]:
                if side == "left":
                    stat_summary = cells[0]
                    player_text = cells[1]
                    projected = safe_float(cells[2])
                    fantasy = safe_float(cells[3])
                else:
                    fantasy = safe_float(cells[7])
                    projected = safe_float(cells[8])
                    player_text = cells[9]
                    stat_summary = cells[10]

                player = strip_player(player_text)

                if player.upper() == "TOTAL":
                    continue

                players.append(
                    {
                        "year": YEAR,
                        "week": WEEK,
                        "side": side,
                        "lineup_slot": slot,
                        "player": player,
                        "is_starter": slot not in {"BN", "BENCH", "IR"},
                        "is_bench": slot in {"BN", "BENCH"},
                        "is_ir": slot == "IR",
                        "projected_points": projected,
                        "fantasy_points": fantasy,
                        "stat_summary": clean_text(stat_summary),
                    }
                )

    return players


def extract_teams_scores(page):
    body = clean_text(page.locator("body").inner_text())

    found_teams = [team for team in TARGET_TEAMS if team in body]

    scores = []
    for table in [page.locator("table").nth(i) for i in range(page.locator("table").count())]:
        try:
            txt = clean_text(table.inner_text())
        except Exception:
            continue

        if " Points " in f" {txt} " and "Orig Proj" in txt:
            nums = re.findall(r"-?\d+(?:\.\d+)?", txt)
            if len(nums) >= 2:
                scores = [float(nums[0]), float(nums[1])]
                break

    return found_teams, scores


def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as exc:
            print("Could not connect to Chrome for Testing on port 9222.")
            print(exc)
            sys.exit(1)

        page = choose_page(browser)

        for team_id in range(1, 13):
            url = (
                f"https://football.fantasysports.yahoo.com/"
                f"{YEAR}/f1/{LEAGUE_ID}/matchup?week={WEEK}&mid1={team_id}"
            )

            print()
            print("=" * 80)
            print(f"TRYING YAHOO TEAM ID {team_id}")
            print("=" * 80)
            print(url)

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(900)
            except Exception:
                print()
                print("Automatic navigation failed.")
                print("Paste this exact URL into the SAME Yahoo Fantasy tab:")
                print(url)
                input("Press ENTER when the matchup is visible: ")
                page.wait_for_timeout(900)

            teams, scores = extract_teams_scores(page)

            score_match = (
                len(scores) >= 2
                and {round(scores[0], 2), round(scores[1], 2)}
                == TARGET_SCORES
            )

            team_match = TARGET_TEAMS.issubset(set(teams))

            print(f"Detected target teams: {teams}")
            print(f"Detected scores: {scores}")

            if not (score_match or team_match):
                continue

            print()
            print("TARGET MATCHUP FOUND.")

            players = parse_players(page)

            if not players:
                print("No player rows parsed. Stopping without saving.")
                return

            left_score, right_score = scores[:2]

            # Use visible body order when possible.
            body = clean_text(page.locator("body").inner_text())
            left_team = None
            right_team = None

            # Infer orientation using score and known final score.
            if round(left_score, 2) == 104.76:
                left_team = "Big Sack Jack"
                right_team = "malle_dips_pouches"
            elif round(left_score, 2) == 88.24:
                left_team = "malle_dips_pouches"
                right_team = "Big Sack Jack"
            else:
                print("Could not infer left/right team orientation safely.")
                return

            for row in players:
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

                row["yahoo_team_id_used"] = team_id

            df = pd.DataFrame(players)
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            df.to_csv(OUT_FILE, index=False)

            print()
            print(f"Saved {len(df)} player rows to:")
            print(OUT_FILE)
            print()
            print("Send me this terminal output next.")
            return

        print()
        print("Target matchup was not found in Yahoo team IDs 1-12.")


if __name__ == "__main__":
    main()