from __future__ import annotations

from pathlib import Path
import re
import time
import pandas as pd

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise SystemExit("Playwright is required. Install with: pip install playwright")


BASE = Path(__file__).resolve().parent
RESCUE_DIR = BASE / "data" / "matchups" / "player_week_stats" / "historical_rescues"
SUMMARY_FILE = RESCUE_DIR / "rescue_summary_2019_2023.csv"
CLEAN_DIR = RESCUE_DIR / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

DEBUGGER = "127.0.0.1:9222"


def banner(text, char="="):
    print()
    print(char * 100)
    print(text)
    print(char * 100)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def as_float(value):
    try:
        return round(float(str(value).replace(",", "").strip()), 2)
    except Exception:
        return None


def clean_player_name(text):
    text = norm(text)

    # Remove Yahoo private-use icon glyphs.
    text = re.sub(r"[\ue000-\uf8ff]", "", text).strip()

    # Strip Yahoo game-status suffix.
    text = re.sub(
        r"\s+(Final|Pregame|Postponed|Delayed|Q[1-4]|Halftime)\b.*$",
        "",
        text,
        flags=re.I,
    ).strip()

    return text or "(Empty)"


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


def choose_page(browser):
    pages = all_pages(browser)

    banner("OPEN CHROME TABS", "-")

    for i, page in enumerate(pages):
        try:
            title = page.title()
        except Exception:
            title = ""

        print(f"TAB {i}: {title}")
        print(f"       {page.url}")

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


def parse_side(cells, side, table_kind):
    if len(cells) < 10:
        return None

    if side == "left":
        stat = cells[0]
        player = cells[1]
        projection = cells[2]
        fantasy_points = cells[3]
        slot = cells[4]
    else:
        slot = cells[6]
        fantasy_points = cells[7]
        projection = cells[8]
        player = cells[9]
        stat = cells[10] if len(cells) > 10 else ""

    slot = norm(slot).upper()

    if slot in {"TOTAL", "TOTALS", "POS", ""}:
        return None

    if table_kind == "starters":
        is_starter = True
        is_bench = False
        is_ir = False
    else:
        is_starter = False
        is_bench = True
        is_ir = False

    return {
        "side": side,
        "lineup_slot": slot,
        "player": clean_player_name(player),
        "projection": as_float(projection),
        "fantasy_points": as_float(fantasy_points),
        "stat_summary": norm(stat),
        "is_starter": is_starter,
        "is_bench": is_bench,
        "is_ir": is_ir,
    }


def parse_matchup(page, row):
    year = int(row["year"])
    week = int(row["week"])

    team1 = norm(row["team_1"])
    team2 = norm(row["team_2"])

    score1 = round(float(row["team_1_score"]), 2)
    score2 = round(float(row["team_2_score"]), 2)

    source_url = norm(row["source_url"])

    records = []

    for selector, kind in [
        ("#statTable1", "starters"),
        ("#statTable2", "bench"),
    ]:
        table = page.locator(selector)

        if table.count() == 0:
            raise RuntimeError(
                f"{selector} not found."
            )

        trs = table.locator("tr")

        for ri in range(1, trs.count()):
            cells = [
                norm(x)
                for x in trs.nth(ri)
                .locator("th,td")
                .all_inner_texts()
            ]

            if any(c.upper() == "TOTAL" for c in cells):
                continue

            for side in ["left", "right"]:
                parsed = parse_side(
                    cells,
                    side,
                    kind,
                )

                if parsed is None:
                    continue

                if side == "left":
                    fantasy_team = team1
                    opponent = team2
                    team_score = score1
                    opponent_score = score2
                else:
                    fantasy_team = team2
                    opponent = team1
                    team_score = score2
                    opponent_score = score1

                records.append({
                    "year": year,
                    "week": week,
                    "fantasy_team": fantasy_team,
                    "opponent": opponent,
                    "team_score": team_score,
                    "opponent_score": opponent_score,
                    "side": side,
                    "lineup_slot": parsed["lineup_slot"],
                    "player": parsed["player"],
                    "projection": parsed["projection"],
                    "fantasy_points": parsed["fantasy_points"],
                    "stat_summary": parsed["stat_summary"],
                    "is_starter": parsed["is_starter"],
                    "is_bench": parsed["is_bench"],
                    "is_ir": parsed["is_ir"],
                    "source_url": source_url,
                    "source_table": kind,
                    "source_row": ri,
                })

    df = pd.DataFrame(records)

    if df.empty:
        raise RuntimeError(
            "Zero player rows parsed."
        )

    starter_counts = (
        df[df["is_starter"]]
        .groupby("fantasy_team")
        .size()
        .to_dict()
    )

    expected_counts = {
        team1: 9,
        team2: 9,
    }

    if starter_counts != expected_counts:
        raise RuntimeError(
            f"Starter-count validation failed: "
            f"{starter_counts} != {expected_counts}"
        )

    starter_sums = (
        df[df["is_starter"]]
        .assign(
            calc=lambda x: pd.to_numeric(
                x["fantasy_points"],
                errors="coerce",
            ).fillna(0.0)
        )
        .groupby("fantasy_team")["calc"]
        .sum()
        .round(2)
        .to_dict()
    )

    expected_scores = {
        team1: score1,
        team2: score2,
    }

    for team, expected in expected_scores.items():
        actual = round(
            float(starter_sums.get(team, 0)),
            2,
        )

        if abs(actual - expected) > 0.011:
            raise RuntimeError(
                f"Score validation failed for {team}: "
                f"{actual:.2f} != {expected:.2f}"
            )

    return df, starter_sums


def safe_filename(row):
    team1 = re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        norm(row["team_1"]),
    ).strip("_")

    team2 = re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        norm(row["team_2"]),
    ).strip("_")

    return (
        f"{int(row['year'])}_week_{int(row['week']):02d}_"
        f"{team1}_vs_{team2}_clean.csv"
    )


def main():
    banner("RE-PARSING EXISTING HISTORICAL RESCUES — 2019-2023")

    if not SUMMARY_FILE.exists():
        raise FileNotFoundError(
            f"Missing rescue summary: {SUMMARY_FILE}"
        )

    summary = pd.read_csv(SUMMARY_FILE)

    required = {
        "year",
        "week",
        "team_1",
        "team_1_score",
        "team_2",
        "team_2_score",
        "source_url",
    }

    missing = required - set(summary.columns)

    if missing:
        raise KeyError(
            f"Rescue summary missing columns: "
            f"{sorted(missing)}"
        )

    print(f"Existing rescue targets: {len(summary)}")
    print("No Yahoo team-ID searching will be performed.")
    print("No season CSV files will be modified.")

    playwright, browser = connect_chrome()
    page = choose_page(browser)

    results = []

    for i, row in summary.iterrows():
        banner(
            f"RESCUE {i + 1} OF {len(summary)} — "
            f"{int(row['year'])} WEEK {int(row['week'])}"
        )

        url = norm(row["source_url"])

        print(
            f"{row['team_1']} {float(row['team_1_score']):.2f} "
            f"vs {row['team_2']} {float(row['team_2_score']):.2f}"
        )
        print(url)

        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=15000,
            )
            time.sleep(1)
        except Exception:
            print(
                "Automatic navigation failed. "
                "Paste the URL above into the SAME Yahoo tab."
            )
            input(
                "Press ENTER once the matchup is visible: "
            )

        df, starter_sums = parse_matchup(
            page,
            row,
        )

        outfile = CLEAN_DIR / safe_filename(row)

        df.to_csv(
            outfile,
            index=False,
        )

        print(
            f"[PASS] {len(df)} validated player rows"
        )
        print(
            f"       {row['team_1']}: "
            f"{starter_sums[norm(row['team_1'])]:.2f}"
        )
        print(
            f"       {row['team_2']}: "
            f"{starter_sums[norm(row['team_2'])]:.2f}"
        )
        print(f"       {outfile}")

        results.append({
            "year": int(row["year"]),
            "week": int(row["week"]),
            "team_1": norm(row["team_1"]),
            "team_1_score": float(row["team_1_score"]),
            "team_2": norm(row["team_2"]),
            "team_2_score": float(row["team_2_score"]),
            "rows_saved": len(df),
            "clean_file": str(outfile),
            "source_url": url,
            "status": "PASS",
        })

    result_df = pd.DataFrame(results)

    result_file = (
        CLEAN_DIR
        / "clean_rescue_summary_2019_2023.csv"
    )

    result_df.to_csv(
        result_file,
        index=False,
    )

    try:
        playwright.stop()
    except Exception:
        pass

    banner("CLEAN RESCUE RE-PARSE COMPLETE")

    print(
        f"Validated rescues: "
        f"{len(result_df)}/{len(summary)}"
    )
    print(result_file)
    print()
    print(
        "No regular-season source files were modified."
    )
    print(
        "Next step: integrate these validated clean rescue "
        "files into the 2019-2023 repair."
    )


if __name__ == "__main__":
    main()