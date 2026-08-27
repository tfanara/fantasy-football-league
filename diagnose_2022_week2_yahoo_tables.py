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
OUT_DIR = BASE / "data" / "matchups" / "player_week_stats" / "historical_rescues" / "diagnostics"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEBUGGER = "127.0.0.1:9222"

YEAR = 2022
WEEK = 2
TEAM_1 = "Uncle Rico"
SCORE_1 = 95.50
TEAM_2 = "malle_dips_pouches"
SCORE_2 = 168.52


def banner(text, char="="):
    print()
    print(char * 100)
    print(text)
    print(char * 100)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def connect_chrome():
    playwright = sync_playwright().start()
    browser = playwright.chromium.connect_over_cdp(f"http://{DEBUGGER}")
    return playwright, browser


def all_pages(browser):
    pages = []
    for context in browser.contexts:
        pages.extend(context.pages)
    return pages


def choose_tab(browser):
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
        raw = input("\nChoose the normal Yahoo Fantasy tab number: ").strip()
        try:
            n = int(raw)
            if 0 <= n < len(pages):
                return pages[n]
        except ValueError:
            pass
        print("Invalid tab number.")


def score_pair_present(text):
    nums = []
    for m in re.findall(r"(?<!\d)(\d{1,3}\.\d{1,2})(?!\d)", text or ""):
        try:
            nums.append(round(float(m), 2))
        except ValueError:
            pass

    return (
        any(abs(x - SCORE_1) < .011 for x in nums)
        and any(abs(x - SCORE_2) < .011 for x in nums)
    )


def find_target(page, league_id):
    banner(
        f"FINDING {YEAR} WEEK {WEEK}: "
        f"{TEAM_1} {SCORE_1:.2f} vs {TEAM_2} {SCORE_2:.2f}"
    )

    for team_id in range(1, 21):
        url = (
            f"https://football.fantasysports.yahoo.com/{YEAR}/f1/"
            f"{league_id}/matchup?week={WEEK}&mid1={team_id}"
        )

        print(f"\nTrying Yahoo team ID {team_id}:")
        print(url)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(1)
        except Exception:
            print("Automatic navigation failed.")
            print("Paste this exact URL into the SAME Yahoo Fantasy tab:")
            print(url)
            input("Press ENTER when the matchup is visible: ")

        try:
            body = page.locator("body").inner_text()
        except Exception:
            body = ""

        scores = score_pair_present(body)
        t1 = TEAM_1.lower() in body.lower()
        t2 = TEAM_2.lower() in body.lower()

        print(
            f"Target score pair: {'YES' if scores else 'no'} | "
            f"{TEAM_1}: {'YES' if t1 else 'no'} | "
            f"{TEAM_2}: {'YES' if t2 else 'no'}"
        )

        if scores:
            print("\nTARGET MATCHUP FOUND.")
            return url, team_id

    return None, None


def main():
    banner("2022 WEEK 2 YAHOO TABLE-STRUCTURE DIAGNOSTIC")
    print("READ ONLY: no existing CSV files will be modified.")
    print("This captures Yahoo's actual HTML/table structure for one broken rescue.")

    playwright, browser = connect_chrome()
    page = choose_tab(browser)

    m = re.search(rf"/{YEAR}/f1/(\d+)", page.url)
    if m:
        league_id = m.group(1)
    else:
        league_id = input(f"\nEnter the {YEAR} Yahoo league ID: ").strip()

    url, team_id = find_target(page, league_id)
    if not url:
        playwright.stop()
        raise RuntimeError("Target matchup could not be found.")

    input(
        "\nVerify BOTH teams' full starter/bench tables are visible. "
        "If needed, scroll the page once. Then press ENTER to capture: "
    )

    # Save complete rendered page HTML.
    html_path = OUT_DIR / "2022_week02_matchup_rendered.html"
    html_path.write_text(page.content(), encoding="utf-8")

    # Save body text for easier inspection.
    body_text = page.locator("body").inner_text()
    text_path = OUT_DIR / "2022_week02_body_text.txt"
    text_path.write_text(body_text, encoding="utf-8")

    tables = page.locator("table")
    table_count = tables.count()

    banner("TABLE INVENTORY")
    print(f"Tables found: {table_count}")

    table_rows = []
    cell_rows = []

    for ti in range(table_count):
        table = tables.nth(ti)

        try:
            table_text = norm(table.inner_text())
        except Exception:
            table_text = ""

        try:
            table_html = table.evaluate("(el) => el.outerHTML")
        except Exception:
            table_html = ""

        try:
            table_class = table.get_attribute("class") or ""
            table_id = table.get_attribute("id") or ""
        except Exception:
            table_class = ""
            table_id = ""

        trs = table.locator("tr")
        tr_count = trs.count()

        table_rows.append({
            "table_index": ti,
            "table_id": table_id,
            "table_class": table_class,
            "row_count": tr_count,
            "text_preview": table_text[:1000],
            "outer_html": table_html,
        })

        print()
        print("-" * 100)
        print(f"TABLE {ti}")
        print(f"id={table_id!r}")
        print(f"class={table_class!r}")
        print(f"rows={tr_count}")
        print("TEXT:")
        print(table_text[:1500])

        for ri in range(tr_count):
            tr = trs.nth(ri)

            try:
                row_text = norm(tr.inner_text())
            except Exception:
                row_text = ""

            cells = tr.locator("th,td")
            cell_count = cells.count()

            cell_texts = []
            for ci in range(cell_count):
                cell = cells.nth(ci)
                try:
                    txt = norm(cell.inner_text())
                except Exception:
                    txt = ""

                try:
                    tag = cell.evaluate("(el) => el.tagName")
                    cls = cell.get_attribute("class") or ""
                    data_pos = cell.get_attribute("data-pos") or ""
                except Exception:
                    tag = ""
                    cls = ""
                    data_pos = ""

                cell_texts.append(txt)
                cell_rows.append({
                    "table_index": ti,
                    "row_index": ri,
                    "cell_index": ci,
                    "tag": tag,
                    "class": cls,
                    "data_pos": data_pos,
                    "text": txt,
                })

            if row_text:
                print(f"  ROW {ri}: {cell_texts}")

    pd.DataFrame(table_rows).to_csv(
        OUT_DIR / "2022_week02_table_inventory.csv",
        index=False,
    )
    pd.DataFrame(cell_rows).to_csv(
        OUT_DIR / "2022_week02_cell_inventory.csv",
        index=False,
    )

    # Also inventory common Yahoo player-ish elements outside table parsing.
    selectors = [
        "[data-tst]",
        "[data-pos]",
        "[class*='player']",
        "[class*='Player']",
        "a[href*='/nfl/players/']",
        "a[href*='/player']",
    ]

    element_rows = []
    for selector in selectors:
        loc = page.locator(selector)
        try:
            count = loc.count()
        except Exception:
            count = 0

        print(f"\nSelector {selector!r}: {count} elements")

        for i in range(min(count, 500)):
            el = loc.nth(i)
            try:
                txt = norm(el.inner_text())
            except Exception:
                txt = ""
            try:
                tag = el.evaluate("(el) => el.tagName")
                cls = el.get_attribute("class") or ""
                href = el.get_attribute("href") or ""
                data_pos = el.get_attribute("data-pos") or ""
                data_tst = el.get_attribute("data-tst") or ""
            except Exception:
                tag = cls = href = data_pos = data_tst = ""

            element_rows.append({
                "selector": selector,
                "index": i,
                "tag": tag,
                "class": cls,
                "href": href,
                "data_pos": data_pos,
                "data_tst": data_tst,
                "text": txt,
            })

    pd.DataFrame(element_rows).to_csv(
        OUT_DIR / "2022_week02_element_inventory.csv",
        index=False,
    )

    banner("DIAGNOSTIC COMPLETE")
    print(f"Yahoo team ID: {team_id}")
    print(f"Source URL: {url}")
    print(f"Tables captured: {table_count}")
    print()
    print("Created:")
    for name in [
        "2022_week02_matchup_rendered.html",
        "2022_week02_body_text.txt",
        "2022_week02_table_inventory.csv",
        "2022_week02_cell_inventory.csv",
        "2022_week02_element_inventory.csv",
    ]:
        print(OUT_DIR / name)

    print()
    print("No existing season or rescue CSV files were modified.")
    print("Send me this terminal output next.")

    try:
        playwright.stop()
    except Exception:
        pass


if __name__ == "__main__":
    main()