from pathlib import Path
import json
import re
import shutil
import unicodedata

import numpy as np
import pandas as pd

from season_config import (
    LAST_COMPLETED_DRAFT_SEASON,
    print_season_config,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DRAFT_PATH = (
    BASE_DIR
    / "data"
    / "drafts"
    / "all_drafts.csv"
)

DRAFT_JSON_PATH = (
    BASE_DIR
    / "data"
    / "drafts"
    / "all_drafts.json"
)

BACKUP_PATH = (
    BASE_DIR
    / "data"
    / "drafts"
    / "all_drafts_before_position_enrichment.csv"
)

LINEUP_DIR = (
    BASE_DIR
    / "data"
    / "matchups"
    / "player_week_stats"
)


# ============================================================
# SETTINGS
# ============================================================

VALID_POSITIONS = {
    "QB",
    "RB",
    "WR",
    "TE",
    "K",
    "DEF",
}

POSITION_NORMALIZATION = {
    "QB": "QB",
    "RB": "RB",
    "HB": "RB",
    "FB": "RB",
    "WR": "WR",
    "TE": "TE",
    "K": "K",
    "PK": "K",
}

DEFENSE_NAMES = {
    "49ers",
    "bears",
    "bengals",
    "bills",
    "broncos",
    "browns",
    "buccaneers",
    "cardinals",
    "chargers",
    "chiefs",
    "colts",
    "commanders",
    "cowboys",
    "dolphins",
    "eagles",
    "falcons",
    "football team",
    "giants",
    "jaguars",
    "jets",
    "lions",
    "packers",
    "panthers",
    "patriots",
    "raiders",
    "rams",
    "ravens",
    "redskins",
    "saints",
    "seahawks",
    "steelers",
    "texans",
    "titans",
    "vikings",
}

# These are only naming/metadata exceptions. They are not a substitute
# for normal automated matching.
MANUAL_POSITION_OVERRIDES = {
    "alex smith": "QB",
    "anthony miller": "WR",
    "ben watson": "TE",
    "chris thompson": "RB",
    "david johnson": "RB",
    "hollywood brown": "WR",
    "james robinson": "RB",
    "joshua palmer": "WR",
    "mark ingram": "RB",
    "michael badgley": "K",
    "michael pittman": "WR",
    "mike williams": "WR",
    "nyheim hines": "RB",
    "nyheim miller hines": "RB",
    "travis hunter": "WR",
}

NFLVERSE_ROSTER_URL = (
    "https://github.com/nflverse/nflverse-data/releases/"
    "download/rosters/roster_{year}.csv"
)


# ============================================================
# NORMALIZATION
# ============================================================

def norm_name(value):
    if pd.isna(value):
        return ""

    s = unicodedata.normalize(
        "NFKD",
        str(value).strip(),
    )

    s = "".join(
        c for c in s
        if not unicodedata.combining(c)
    )

    s = s.lower()
    s = s.replace("’", "'")
    s = s.replace(".", "")
    s = s.replace("'", "")
    s = s.replace("-", " ")

    # Yahoo/nflverse suffix differences should not prevent matching.
    s = re.sub(
        r"\b(jr|sr|ii|iii|iv|v)\b",
        "",
        s,
    )

    s = re.sub(
        r"[^a-z0-9]+",
        " ",
        s,
    )

    return re.sub(
        r"\s+",
        " ",
        s,
    ).strip()


def normalize_position(value):
    if pd.isna(value):
        return ""

    value = str(value).strip().upper()

    if value in VALID_POSITIONS:
        return value

    return POSITION_NORMALIZATION.get(
        value,
        "",
    )


# ============================================================
# HISTORICAL WEEKLY-LINEUP POSITION LOOKUP
# ============================================================

def find_lineup_master():
    preferred = [
        LINEUP_DIR
        / "all_weekly_lineups.csv",
        LINEUP_DIR
        / "all_weekly_lineups_2017_2025.csv",
    ]

    for path in preferred:
        if path.exists():
            return path

    candidates = list(
        LINEUP_DIR.glob(
            "all_weekly_lineups*.csv"
        )
    )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda p: p.stat().st_mtime,
    )


def build_lineup_lookup():
    path = find_lineup_master()

    if path is None:
        print(
            "Historical lineup position source: "
            "not found; continuing with nflverse."
        )
        return {}

    print(
        "Historical lineup position source:",
        path,
    )

    lineups = pd.read_csv(path)

    required = {
        "year",
        "player",
    }

    if not required.issubset(
        lineups.columns
    ):
        print(
            "WARNING: lineup master lacks year/player; "
            "skipping lineup position lookup."
        )
        return {}

    lineups["year"] = pd.to_numeric(
        lineups["year"],
        errors="coerce",
    )

    lineups["name_key"] = (
        lineups["player"]
        .map(norm_name)
    )

    position_values = pd.Series(
        "",
        index=lineups.index,
        dtype="object",
    )

    if "player_position" in lineups.columns:
        position_values = (
            lineups["player_position"]
            .map(normalize_position)
        )

    if "lineup_slot" in lineups.columns:
        slot_values = (
            lineups["lineup_slot"]
            .map(normalize_position)
        )

        position_values = (
            position_values
            .where(
                position_values.isin(
                    VALID_POSITIONS
                ),
                slot_values,
            )
        )

    temp = pd.DataFrame({
        "year": lineups["year"],
        "name_key": lineups["name_key"],
        "position": position_values,
    })

    temp = temp[
        temp["position"].isin(
            VALID_POSITIONS
        )
    ].copy()

    if temp.empty:
        return {}

    grouped = (
        temp
        .groupby(
            ["year", "name_key"]
        )["position"]
        .agg(
            lambda s:
                s.mode().iloc[0]
                if not s.mode().empty
                else ""
        )
    )

    return grouped.to_dict()


# ============================================================
# NFLVERSE ROSTER LOOKUP
# ============================================================

def choose_column(
    df,
    candidates,
):
    lower = {
        str(c).lower(): c
        for c in df.columns
    }

    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[
                candidate.lower()
            ]

    return None


def download_rosters(
    start_year,
    end_year,
):
    records = []

    print()
    print(
        "Downloading nflverse roster metadata "
        f"for {start_year}-{end_year}..."
    )

    for year in range(
        start_year,
        end_year + 1,
    ):
        url = NFLVERSE_ROSTER_URL.format(
            year=year
        )

        try:
            roster = pd.read_csv(url)
        except Exception as exc:
            print(
                f"WARNING: could not load "
                f"nflverse roster {year}: {exc}"
            )
            continue

        name_col = choose_column(
            roster,
            [
                "full_name",
                "player_name",
                "display_name",
                "football_name",
                "name",
            ],
        )

        position_col = choose_column(
            roster,
            [
                "position",
                "pos",
            ],
        )

        if (
            name_col is None
            or position_col is None
        ):
            print(
                f"WARNING: roster {year} does not "
                "contain a recognized player-name/"
                "position schema."
            )
            continue

        temp = pd.DataFrame({
            "year": year,
            "name_key":
                roster[name_col].map(
                    norm_name
                ),
            "position":
                roster[position_col].map(
                    normalize_position
                ),
        })

        temp = temp[
            temp["name_key"].ne("")
            & temp["position"].isin(
                VALID_POSITIONS
            )
        ].copy()

        records.append(temp)

        print(
            f"  {year}: "
            f"{len(temp):,} usable roster rows"
        )

    if not records:
        return pd.DataFrame(
            columns=[
                "year",
                "name_key",
                "position",
            ]
        )

    return pd.concat(
        records,
        ignore_index=True,
    )


def build_nflverse_lookups(
    roster_rows,
):
    if roster_rows.empty:
        return {}, {}

    same_year = (
        roster_rows
        .groupby(
            ["year", "name_key"]
        )["position"]
        .agg(
            lambda s:
                s.mode().iloc[0]
                if not s.mode().empty
                else ""
        )
        .to_dict()
    )

    all_years = (
        roster_rows
        .groupby(
            "name_key"
        )["position"]
        .agg(
            lambda s:
                s.mode().iloc[0]
                if not s.mode().empty
                else ""
        )
        .to_dict()
    )

    return (
        same_year,
        all_years,
    )


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 80)
    print("ENRICHING DRAFT PLAYER POSITIONS")
    print("=" * 80)

    print_season_config()

    if not DRAFT_PATH.exists():
        raise FileNotFoundError(
            f"Draft master not found: "
            f"{DRAFT_PATH}"
        )

    drafts = pd.read_csv(
        DRAFT_PATH
    )

    print()
    print(
        f"Loaded {len(drafts):,} draft picks."
    )

    required = {
        "year",
        "round",
        "pick_in_round",
        "overall_pick",
        "team",
        "player",
        "keeper",
    }

    missing = (
        required
        - set(drafts.columns)
    )

    if missing:
        raise RuntimeError(
            "Draft master is missing required "
            "columns: "
            + ", ".join(
                sorted(missing)
            )
        )

    drafts["year"] = pd.to_numeric(
        drafts["year"],
        errors="coerce",
    )

    bad_year = drafts["year"].isna()

    if bad_year.any():
        raise RuntimeError(
            f"{int(bad_year.sum())} draft rows "
            "have invalid years."
        )

    drafts["year"] = (
        drafts["year"].astype(int)
    )

    if (
        drafts["year"].max()
        > LAST_COMPLETED_DRAFT_SEASON
    ):
        raise RuntimeError(
            "Draft master contains a season after "
            f"LAST_COMPLETED_DRAFT_SEASON="
            f"{LAST_COMPLETED_DRAFT_SEASON}."
        )

    drafts["name_key"] = (
        drafts["player"]
        .map(norm_name)
    )

    if "position" not in drafts.columns:
        drafts["position"] = ""

    drafts["position"] = (
        drafts["position"]
        .map(normalize_position)
    )

    drafts["position_source"] = np.where(
        drafts["position"].isin(
            VALID_POSITIONS
        ),
        "Existing",
        "",
    )

    # --------------------------------------------------------
    # DEFENSES
    # --------------------------------------------------------

    defense_mask = (
        ~drafts["position"].isin(
            VALID_POSITIONS
        )
        & drafts["name_key"].isin(
            DEFENSE_NAMES
        )
    )

    drafts.loc[
        defense_mask,
        "position",
    ] = "DEF"

    drafts.loc[
        defense_mask,
        "position_source",
    ] = "Defense"

    # --------------------------------------------------------
    # HISTORICAL WEEKLY LINEUPS
    # --------------------------------------------------------

    lineup_lookup = (
        build_lineup_lookup()
    )

    unresolved_mask = (
        ~drafts["position"].isin(
            VALID_POSITIONS
        )
    )

    for idx in drafts.index[
        unresolved_mask
    ]:
        key = (
            int(drafts.at[idx, "year"]),
            drafts.at[idx, "name_key"],
        )

        position = (
            lineup_lookup.get(
                key,
                "",
            )
        )

        if position in VALID_POSITIONS:
            drafts.at[
                idx,
                "position",
            ] = position

            drafts.at[
                idx,
                "position_source",
            ] = "Weekly Lineup"

    # --------------------------------------------------------
    # NFLVERSE
    # --------------------------------------------------------

    roster_rows = download_rosters(
        int(drafts["year"].min()),
        int(
            min(
                drafts["year"].max(),
                LAST_COMPLETED_DRAFT_SEASON,
            )
        ),
    )

    (
        nfl_same_year,
        nfl_all_years,
    ) = build_nflverse_lookups(
        roster_rows
    )

    unresolved_mask = (
        ~drafts["position"].isin(
            VALID_POSITIONS
        )
    )

    for idx in drafts.index[
        unresolved_mask
    ]:
        key = (
            int(drafts.at[idx, "year"]),
            drafts.at[idx, "name_key"],
        )

        position = (
            nfl_same_year.get(
                key,
                "",
            )
        )

        if position in VALID_POSITIONS:
            drafts.at[
                idx,
                "position",
            ] = position

            drafts.at[
                idx,
                "position_source",
            ] = "NFLverse Exact"

    # Cross-season fallback is useful for players who were injured,
    # unsigned, or absent from the season roster snapshot.
    unresolved_mask = (
        ~drafts["position"].isin(
            VALID_POSITIONS
        )
    )

    for idx in drafts.index[
        unresolved_mask
    ]:
        name_key = (
            drafts.at[
                idx,
                "name_key",
            ]
        )

        position = (
            nfl_all_years.get(
                name_key,
                "",
            )
        )

        if position in VALID_POSITIONS:
            drafts.at[
                idx,
                "position",
            ] = position

            drafts.at[
                idx,
                "position_source",
            ] = "NFLverse Cross-Year"

    # --------------------------------------------------------
    # MANUAL NAMING EXCEPTIONS
    # --------------------------------------------------------

    unresolved_mask = (
        ~drafts["position"].isin(
            VALID_POSITIONS
        )
    )

    for idx in drafts.index[
        unresolved_mask
    ]:
        name_key = drafts.at[
            idx,
            "name_key",
        ]

        position = (
            MANUAL_POSITION_OVERRIDES.get(
                name_key,
                "",
            )
        )

        if position in VALID_POSITIONS:
            drafts.at[
                idx,
                "position",
            ] = position

            drafts.at[
                idx,
                "position_source",
            ] = "Manual Override"

    # --------------------------------------------------------
    # VALIDATE BEFORE WRITING
    # --------------------------------------------------------

    unresolved = drafts[
        ~drafts["position"].isin(
            VALID_POSITIONS
        )
    ].copy()

    print()
    print("=" * 80)
    print("POSITION ENRICHMENT SUMMARY")
    print("=" * 80)

    print()
    print(
        drafts["position"]
        .replace("", "(unresolved)")
        .value_counts()
        .to_string()
    )

    print()
    print("Sources:")
    print(
        drafts["position_source"]
        .replace("", "(unresolved)")
        .value_counts()
        .to_string()
    )

    if not unresolved.empty:
        print()
        print("=" * 80)
        print("UNRESOLVED PICKS — NOTHING WAS WRITTEN")
        print("=" * 80)
        print()
        print(
            unresolved[
                [
                    "year",
                    "overall_pick",
                    "team",
                    "player",
                ]
            ]
            .sort_values(
                [
                    "year",
                    "overall_pick",
                ]
            )
            .to_string(
                index=False
            )
        )

        raise RuntimeError(
            f"{len(unresolved)} draft picks still "
            "have unresolved positions. "
            "all_drafts.csv was left unchanged."
        )

    duplicate_picks = (
        drafts
        .duplicated(
            [
                "year",
                "overall_pick",
            ]
        )
        .sum()
    )

    if duplicate_picks:
        raise RuntimeError(
            f"{duplicate_picks} duplicate "
            "year/overall picks found. "
            "Nothing was written."
        )

    expected_rows = len(drafts)

    # --------------------------------------------------------
    # WRITE ONLY AFTER FULL VALIDATION
    # --------------------------------------------------------

    shutil.copy2(
        DRAFT_PATH,
        BACKUP_PATH,
    )

    output = drafts.drop(
        columns=[
            "name_key",
        ]
    )

    output.to_csv(
        DRAFT_PATH,
        index=False,
    )

    DRAFT_JSON_PATH.write_text(
        output.to_json(
            orient="records",
            indent=2,
            force_ascii=False,
        ),
        encoding="utf-8",
    )

    # Reload what was actually written.
    check = pd.read_csv(
        DRAFT_PATH
    )

    if len(check) != expected_rows:
        raise RuntimeError(
            "Post-write row-count validation "
            "failed."
        )

    if (
        ~check["position"].isin(
            VALID_POSITIONS
        )
    ).any():
        raise RuntimeError(
            "Post-write position validation "
            "failed."
        )

    print()
    print("=" * 80)
    print("VALIDATION")
    print("=" * 80)
    print(
        f"PASS — {len(check):,} draft picks "
        "preserved."
    )
    print(
        "PASS — every draft pick has one of "
        "QB/RB/WR/TE/K/DEF."
    )
    print(
        "PASS — year/overall pick remains unique."
    )
    print(
        f"PASS — draft position enrichment "
        f"covers through "
        f"{LAST_COMPLETED_DRAFT_SEASON}."
    )
    print()
    print(
        "Updated:",
        DRAFT_PATH,
    )
    print(
        "Updated:",
        DRAFT_JSON_PATH,
    )
    print(
        "Backup:",
        BACKUP_PATH,
    )


if __name__ == "__main__":
    main()