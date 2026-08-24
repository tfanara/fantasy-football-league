from pathlib import Path

from playwright.sync_api import sync_playwright


PROFILE_DIR = Path("yahoo_browser_profile")

DRAFT_URL = (
    "https://football.fantasysports.yahoo.com/"
    "2025/f1/637567/draftresults"
)


with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
    )

    pages = context.pages

    if pages:
        page = pages[0]
    else:
        page = context.new_page()

    print()
    print("=" * 80)
    print("YAHOO KEEPER MARKER INSPECTOR")
    print("=" * 80)

    print()
    print("Paste this URL into the SAME Chromium tab:")
    print()
    print(DRAFT_URL)
    print()
    print("Wait until the 2025 Draft Results are visible.")
    print()

    input("Press ENTER when Draft Results are visible: ")

    print()
    print("=" * 80)
    print("PAGE")
    print("=" * 80)

    print()
    print("Title:")
    print(page.title())

    print()
    print("URL:")
    print(page.url)

    # ========================================================
    # FIND ALL DRAFT ROWS
    # ========================================================

    rows = page.locator("tr")

    print()
    print("=" * 80)
    print("ROWS WITH POSSIBLE KEEPER MARKERS")
    print("=" * 80)

    marked_rows = []

    for i in range(rows.count()):

        row = rows.nth(i)

        try:
            text = row.inner_text().strip()
        except Exception:
            continue

        if not text:
            continue

        # The unusual Yahoo glyph we saw on several players
        if "" in text:

            marked_rows.append(row)

            print()
            print("-" * 80)
            print(f"ROW {i}")
            print("-" * 80)

            print()
            print("TEXT:")
            print(text)

            # ------------------------------------------------
            # RAW HTML
            # ------------------------------------------------

            try:
                html = row.evaluate(
                    "(el) => el.outerHTML"
                )

                print()
                print("HTML:")
                print(html[:10000])

            except Exception as e:
                print("Could not read HTML:", e)

            # ------------------------------------------------
            # CHILD ELEMENT ATTRIBUTES
            # ------------------------------------------------

            elements = row.locator("*")

            print()
            print("INTERESTING CHILD ELEMENTS:")

            for j in range(elements.count()):

                element = elements.nth(j)

                try:
                    tag = element.evaluate(
                        "(el) => el.tagName"
                    )

                    class_name = element.get_attribute(
                        "class"
                    )

                    title = element.get_attribute(
                        "title"
                    )

                    aria = element.get_attribute(
                        "aria-label"
                    )

                    data_tip = element.get_attribute(
                        "data-tooltip"
                    )

                    child_text = (
                        element
                        .inner_text()
                        .strip()
                    )

                except Exception:
                    continue

                combined = " ".join(
                    [
                        child_text or "",
                        class_name or "",
                        title or "",
                        aria or "",
                        data_tip or "",
                    ]
                ).lower()

                if (
                    "keeper" in combined
                    or "keep" in combined
                    or "" in child_text
                    or title
                    or aria
                ):

                    print()
                    print(f"  CHILD {j}")
                    print(f"  TAG:   {tag}")
                    print(f"  TEXT:  {child_text}")
                    print(f"  CLASS: {class_name}")
                    print(f"  TITLE: {title}")
                    print(f"  ARIA:  {aria}")
                    print(f"  TIP:   {data_tip}")

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print()
    print(
        f"Draft rows containing the special marker: "
        f"{len(marked_rows)}"
    )

    # ========================================================
    # SEARCH ENTIRE HTML FOR KEEPER
    # ========================================================

    print()
    print("=" * 80)
    print("HTML CONTAINING 'KEEP'")
    print("=" * 80)

    html = page.content()

    lower_html = html.lower()

    locations = []

    start = 0

    while True:

        pos = lower_html.find(
            "keep",
            start,
        )

        if pos == -1:
            break

        locations.append(pos)

        start = pos + 4

    print()
    print(
        f"Occurrences of 'keep' in page HTML: "
        f"{len(locations)}"
    )

    for pos in locations[:50]:

        snippet_start = max(
            0,
            pos - 300,
        )

        snippet_end = min(
            len(html),
            pos + 500,
        )

        print()
        print("-" * 80)
        print(
            html[
                snippet_start:
                snippet_end
            ]
        )

    input(
        "\nPress ENTER to close Chromium: "
    )

    context.close()