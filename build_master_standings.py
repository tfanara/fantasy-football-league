#!/usr/bin/env python3

from pathlib import Path

import pandas as pd

from season_config import CURRENT_SEASON


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

MASTER_FILE = DATA / "all_standings.csv"
CURRENT_FILE = DATA / str(CURRENT_SEASON) / "standings.csv"

TEAM_ALIASES = {
    "Ginger FC": "Ginger FC 🏆🏆",
    "Ginger FC 🏆🏆": "Ginger FC 🏆🏆",
    "PickUpYourBratsMalle": "ThreatLevelMidnight",
    "Little Red Fournette": "Post Mahomes",
    "Ur The Best Bellows": "Joe Mantegna",
    "You Better Park It": "Buttermilk Puuump",
    "Buttermilk Pump": "Buttermilk Puuump",
}


def fail(message):
    raise RuntimeError(message)


def main():

    print("=" * 80)
    print("BUILDING MASTER STANDINGS")
    print("=" * 80)

    if not MASTER_FILE.exists():
        fail(f"Missing standings master: {MASTER_FILE}")

    if not CURRENT_FILE.exists():
        fail(f"Missing current standings: {CURRENT_FILE}")

    master = pd.read_csv(MASTER_FILE)
    current = pd.read_csv(CURRENT_FILE)

    if "year" not in master.columns:
        fail("Master standings are missing year column.")

    required = {
        "team",
        "record",
        "points_for",
        "points_against",
    }

    missing = sorted(required - set(current.columns))

    if missing:
        fail(
            "Current standings missing required columns: "
            + ", ".join(missing)
        )

    if len(current) != 12:
        fail(
            f"{CURRENT_SEASON} standings contain "
            f"{len(current)} rows; expected 12."
        )

    current = current.copy()

    current["team"] = (
        current["team"]
        .astype(str)
        .str.strip()
        .replace(TEAM_ALIASES)
    )

    if current["team"].nunique() != 12:
        fail(
            f"{CURRENT_SEASON} standings do not contain "
            "12 unique teams."
        )

    current["year"] = CURRENT_SEASON

    # --------------------------------------------------------
    # Preserve historical schema
    # --------------------------------------------------------

    for column in master.columns:
        if column not in current.columns:
            current[column] = pd.NA

    extra = [
        column
        for column in current.columns
        if column not in master.columns
    ]

    if extra:
        print(
            "Ignoring current-season-only columns:",
            ", ".join(extra),
        )

    current = current[master.columns]

    master_year = pd.to_numeric(
        master["year"],
        errors="coerce",
    )

    historical = master[
        ~master_year.eq(CURRENT_SEASON)
    ].copy()

    # Historical standings are immutable here.
    before_historical = historical.copy()

    combined = pd.concat(
        [
            historical,
            current,
        ],
        ignore_index=True,
    )

    after_historical = combined[
        pd.to_numeric(
            combined["year"],
            errors="coerce",
        ).ne(CURRENT_SEASON)
    ].reset_index(drop=True)

    pd.testing.assert_frame_equal(
        before_historical.reset_index(drop=True),
        after_historical,
        check_dtype=False,
    )

    current_out = combined[
        pd.to_numeric(
            combined["year"],
            errors="coerce",
        ).eq(CURRENT_SEASON)
    ].copy()

    if len(current_out) != 12:
        fail(
            f"Master standings would contain "
            f"{len(current_out)} current-season rows; "
            "expected 12."
        )

    MASTER_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    combined.to_csv(
        MASTER_FILE,
        index=False,
    )

    print(
        f"[PASS] Historical standings preserved: "
        f"{len(historical):,} rows"
    )

    print(
        f"[PASS] {CURRENT_SEASON} standings replaced: "
        f"{len(current_out)} teams"
    )

    print(f"[PASS] Saved {MASTER_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
