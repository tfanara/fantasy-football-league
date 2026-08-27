from __future__ import annotations

from pathlib import Path
import re
import shutil

import pandas as pd


SCRIPT_VERSION = "2018-clean-matchups-v4-with-rescue"

YEAR = 2018
REGULAR_WEEKS = list(range(1, 14))

BASE_DIR = Path(__file__).resolve().parent
PLAYER_DIR = BASE_DIR / "data" / "matchups" / "player_week_stats"

LINEUPS_FILE = PLAYER_DIR / "2018_weekly_lineups.csv"
MATCHUPS_FILE = PLAYER_DIR / "2018_matchups.csv"
RESCUE_FILE = PLAYER_DIR / "2018_week09_missing_matchup_rescue.csv"

SOURCE_FILE = BASE_DIR / "data" / "all_matchups_clean.csv"

LINEUPS_BACKUP = PLAYER_DIR / "2018_weekly_lineups_before_final_repair.csv"
MATCHUPS_BACKUP = PLAYER_DIR / "2018_matchups_before_final_repair.csv"

RECAP_RE = re.compile(
    r"^Week\s+\d+\s+Recap\s+\((Won|Lost)\)$",
    re.IGNORECASE,
)


def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def is_recap(value):
    return bool(RECAP_RE.match(clean(value)))


def score_key(a, b):
    return tuple(
        sorted(
            [
                round(float(a), 2),
                round(float(b), 2),
            ]
        )
    )


def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def main():
    print(f"SCRIPT VERSION: {SCRIPT_VERSION}")
    banner("2018 FINAL CLEAN-MATCHUP REPAIR")

    for required in [
        LINEUPS_FILE,
        MATCHUPS_FILE,
        RESCUE_FILE,
        SOURCE_FILE,
    ]:
        if not required.exists():
            raise FileNotFoundError(
                f"Missing required file: {required}"
            )

    lineups = pd.read_csv(LINEUPS_FILE)
    collected = pd.read_csv(MATCHUPS_FILE)
    rescue = pd.read_csv(RESCUE_FILE)
    source = pd.read_csv(SOURCE_FILE)

    required_source_columns = {
        "year",
        "week",
        "team_1",
        "team_1_score",
        "team_2",
        "team_2_score",
    }

    missing = required_source_columns - set(source.columns)

    if missing:
        raise KeyError(
            f"Missing source columns: {sorted(missing)}"
        )

    auth = source[
        (pd.to_numeric(source["year"], errors="coerce") == YEAR)
        & (pd.to_numeric(source["week"], errors="coerce").isin(REGULAR_WEEKS))
    ].copy()

    auth = auth[
        [
            "week",
            "team_1",
            "team_1_score",
            "team_2",
            "team_2_score",
        ]
    ].rename(
        columns={
            "team_1": "team_a",
            "team_1_score": "score_a",
            "team_2": "team_b",
            "team_2_score": "score_b",
        }
    )

    auth["week"] = pd.to_numeric(
        auth["week"],
        errors="coerce",
    ).astype(int)

    auth["score_a"] = pd.to_numeric(
        auth["score_a"],
        errors="coerce",
    )

    auth["score_b"] = pd.to_numeric(
        auth["score_b"],
        errors="coerce",
    )

    auth["team_a"] = auth["team_a"].map(clean)
    auth["team_b"] = auth["team_b"].map(clean)

    auth["pair_key"] = auth.apply(
        lambda r: tuple(
            sorted(
                [
                    r["team_a"],
                    r["team_b"],
                ]
            )
        ),
        axis=1,
    )

    auth["score_key"] = auth.apply(
        lambda r: score_key(
            r["score_a"],
            r["score_b"],
        ),
        axis=1,
    )

    auth = (
        auth.sort_values(
            ["week", "pair_key"]
        )
        .drop_duplicates(
            subset=[
                "week",
                "pair_key",
                "score_key",
            ],
            keep="first",
        )
        .reset_index(drop=True)
    )

    banner("AUTHORITATIVE SOURCE CHECK")

    auth_counts = (
        auth.groupby("week")
        .size()
        .reindex(
            REGULAR_WEEKS,
            fill_value=0,
        )
    )

    print(auth_counts.to_string())
    print()
    print(
        f"Total authoritative matchups: {len(auth)}"
    )

    if (
        len(auth) != 78
        or not (auth_counts == 6).all()
    ):
        print()
        print(
            "STOP: authoritative source is not 78 matchups / 6 per week."
        )
        return

    collected = collected[
        pd.to_numeric(
            collected["week"],
            errors="coerce",
        ).isin(REGULAR_WEEKS)
    ].copy()

    # ------------------------------------------------------------
    # Resolve all collected Yahoo matchup rows to authoritative games.
    # ------------------------------------------------------------

    resolved = []

    for _, row in collected.iterrows():
        week = int(row["week"])
        lscore = round(float(row["left_score"]), 2)
        rscore = round(float(row["right_score"]), 2)
        skey = score_key(lscore, rscore)

        candidates = auth[
            (auth["week"] == week)
            & (auth["score_key"] == skey)
        ].copy()

        visible = {
            team
            for team in [
                clean(row["left_team"]),
                clean(row["right_team"]),
            ]
            if team and not is_recap(team)
        }

        if visible:
            filtered = candidates[
                candidates.apply(
                    lambda r: bool(
                        visible
                        & {
                            clean(r["team_a"]),
                            clean(r["team_b"]),
                        }
                    ),
                    axis=1,
                )
            ]

            if not filtered.empty:
                candidates = filtered

        if len(candidates) != 1:
            continue

        a = candidates.iloc[0]

        team_a = clean(a["team_a"])
        team_b = clean(a["team_b"])
        score_a = round(float(a["score_a"]), 2)
        score_b = round(float(a["score_b"]), 2)

        if lscore == score_a and rscore == score_b:
            left_team, right_team = team_a, team_b
        elif lscore == score_b and rscore == score_a:
            left_team, right_team = team_b, team_a
        else:
            continue

        new_row = row.copy()
        new_row["left_team"] = left_team
        new_row["right_team"] = right_team
        new_row["_pair_key"] = tuple(
            sorted(
                [
                    left_team,
                    right_team,
                ]
            )
        )
        new_row["_score_key"] = skey

        resolved.append(new_row)

    resolved_df = pd.DataFrame(resolved)

    # Keep one Yahoo view per authoritative real matchup.
    kept = (
        resolved_df
        .sort_values(
            [
                "week",
                "_pair_key",
                "matchup_id",
            ]
        )
        .drop_duplicates(
            subset=[
                "week",
                "_pair_key",
                "_score_key",
            ],
            keep="first",
        )
        .copy()
    )

    # ------------------------------------------------------------
    # Add the rescued missing Week 9 matchup.
    # ------------------------------------------------------------

    rescue_required = {
        "side",
        "fantasy_team",
        "opponent",
        "team_score",
        "opponent_score",
    }

    missing_rescue_cols = (
        rescue_required
        - set(rescue.columns)
    )

    if missing_rescue_cols:
        raise KeyError(
            f"Rescue file missing columns: {sorted(missing_rescue_cols)}"
        )

    rescue_left = rescue[
        rescue["side"]
        .astype(str)
        .str.lower()
        .eq("left")
    ].iloc[0]

    rescue_right = rescue[
        rescue["side"]
        .astype(str)
        .str.lower()
        .eq("right")
    ].iloc[0]

    rescue_matchup_row = {
        "year": YEAR,
        "week": 9,
        "matchup_id": "2018-W09-RESCUE",
        "matchup_number": 999,
        "yahoo_team_id_used": int(
            rescue["yahoo_team_id_used"]
            .dropna()
            .iloc[0]
        ),
        "left_team": clean(
            rescue_left["fantasy_team"]
        ),
        "right_team": clean(
            rescue_right["fantasy_team"]
        ),
        "left_score": float(
            rescue_left["team_score"]
        ),
        "right_score": float(
            rescue_right["team_score"]
        ),
        "player_records": len(rescue),
        "roster_tables": 2,
        "url": "",
        "_pair_key": tuple(
            sorted(
                [
                    clean(
                        rescue_left[
                            "fantasy_team"
                        ]
                    ),
                    clean(
                        rescue_right[
                            "fantasy_team"
                        ]
                    ),
                ]
            )
        ),
        "_score_key": score_key(
            rescue_left["team_score"],
            rescue_right["team_score"],
        ),
    }

    rescue_matchup_df = pd.DataFrame(
        [rescue_matchup_row]
    )

    combined_matchups = pd.concat(
        [
            kept,
            rescue_matchup_df,
        ],
        ignore_index=True,
        sort=False,
    )

    combined_matchups = (
        combined_matchups
        .sort_values(
            [
                "week",
                "_pair_key",
                "matchup_id",
            ]
        )
        .drop_duplicates(
            subset=[
                "week",
                "_pair_key",
                "_score_key",
            ],
            keep="first",
        )
        .copy()
    )

    banner("RESOLVED MATCHUP COUNT")

    print(
        f"Resolved unique matchups including rescue: "
        f"{len(combined_matchups)}"
    )

    if len(combined_matchups) != 78:
        print()
        print(
            "STOP: Still not exactly 78 matchups. Nothing was changed."
        )
        return

    # ------------------------------------------------------------
    # Rebuild lineup rows using kept views + rescue.
    # ------------------------------------------------------------

    lineup_parts = []

    # Lookup resolved team names for retained Yahoo matchup IDs.
    team_lookup = {
        str(row["matchup_id"]): (
            clean(row["left_team"]),
            clean(row["right_team"]),
        )
        for _, row in kept.iterrows()
    }

    kept_old_ids = set(
        kept["matchup_id"]
        .astype(str)
        .tolist()
    )

    for old_id in kept_old_ids:
        part = lineups[
            lineups["matchup_id"]
            .astype(str)
            .eq(old_id)
        ].copy()

        if part.empty:
            continue

        left_team, right_team = team_lookup[
            old_id
        ]

        left_mask = (
            part["side"]
            .astype(str)
            .str.lower()
            .eq("left")
        )

        right_mask = (
            part["side"]
            .astype(str)
            .str.lower()
            .eq("right")
        )

        part.loc[
            left_mask,
            "fantasy_team",
        ] = left_team

        part.loc[
            left_mask,
            "opponent",
        ] = right_team

        part.loc[
            right_mask,
            "fantasy_team",
        ] = right_team

        part.loc[
            right_mask,
            "opponent",
        ] = left_team

        lineup_parts.append(part)

    rescue_part = rescue.copy()

    # Add columns expected by master file if missing.
    for col in lineups.columns:
        if col not in rescue_part.columns:
            rescue_part[col] = pd.NA

    rescue_part = rescue_part[
        lineups.columns
    ].copy()

    rescue_part["year"] = YEAR
    rescue_part["week"] = 9
    rescue_part["matchup_id"] = "2018-W09-RESCUE"
    rescue_part["matchup_number"] = 999

    lineup_parts.append(
        rescue_part
    )

    rebuilt_lineups = pd.concat(
        lineup_parts,
        ignore_index=True,
        sort=False,
    )

    # ------------------------------------------------------------
    # Renumber all matchups sequentially by week and update lineups.
    # ------------------------------------------------------------

    combined_matchups = combined_matchups.sort_values(
        [
            "week",
            "_pair_key",
        ]
    ).copy()

    id_map = {}

    for week, idxs in combined_matchups.groupby(
        "week"
    ).groups.items():

        for number, idx in enumerate(
            idxs,
            start=1,
        ):
            old_id = str(
                combined_matchups.at[
                    idx,
                    "matchup_id",
                ]
            )

            new_id = (
                f"{YEAR}-W{int(week):02d}"
                f"-M{number:02d}"
            )

            id_map[old_id] = new_id

            combined_matchups.at[
                idx,
                "matchup_id",
            ] = new_id

            combined_matchups.at[
                idx,
                "matchup_number",
            ] = number

    rebuilt_lineups[
        "matchup_id"
    ] = rebuilt_lineups[
        "matchup_id"
    ].astype(str).map(
        lambda x: id_map.get(
            x,
            x,
        )
    )

    rebuilt_lineups[
        "matchup_number"
    ] = rebuilt_lineups[
        "matchup_id"
    ].str.extract(
        r"-M(\d+)$"
    )[0].astype(int)

    repaired_matchups = (
        combined_matchups.drop(
            columns=[
                "_pair_key",
                "_score_key",
            ],
            errors="ignore",
        )
    )

    # ------------------------------------------------------------
    # Safety checks.
    # ------------------------------------------------------------

    banner("POST-REPAIR SAFETY CHECKS")

    matchup_counts = (
        repaired_matchups
        .groupby("week")
        .size()
        .reindex(
            REGULAR_WEEKS,
            fill_value=0,
        )
    )

    teams_long = pd.concat(
        [
            repaired_matchups[
                ["week", "left_team"]
            ].rename(
                columns={
                    "left_team": "team",
                }
            ),
            repaired_matchups[
                ["week", "right_team"]
            ].rename(
                columns={
                    "right_team": "team",
                }
            ),
        ],
        ignore_index=True,
    )

    team_counts = (
        teams_long
        .groupby("week")["team"]
        .nunique()
        .reindex(
            REGULAR_WEEKS,
            fill_value=0,
        )
    )

    starter_count = int(
        rebuilt_lineups[
            "is_starter"
        ].fillna(False).sum()
    )

    recap_matchups = int(
        (
            repaired_matchups[
                "left_team"
            ].map(is_recap)
            | repaired_matchups[
                "right_team"
            ].map(is_recap)
        ).sum()
    )

    recap_lineups = int(
        (
            rebuilt_lineups[
                "fantasy_team"
            ].map(is_recap)
            | rebuilt_lineups[
                "opponent"
            ].map(is_recap)
        ).sum()
    )

    print("Matchups per week:")
    print(
        matchup_counts.to_string()
    )

    print()
    print("Unique teams per week:")
    print(
        team_counts.to_string()
    )

    print()
    print(
        f"Total matchups:       "
        f"{len(repaired_matchups)}"
    )
    print(
        f"Starter records:      "
        f"{starter_count}"
    )
    print(
        f"Recap matchup labels: "
        f"{recap_matchups}"
    )
    print(
        f"Recap lineup labels:  "
        f"{recap_lineups}"
    )

    passed = (
        len(repaired_matchups) == 78
        and (matchup_counts == 6).all()
        and (team_counts == 12).all()
        and starter_count == 1404
        and recap_matchups == 0
        and recap_lineups == 0
    )

    if not passed:
        print()
        print(
            "REPAIR CHECK FAILED. Nothing was overwritten."
        )
        return

    # ------------------------------------------------------------
    # Save backups + repaired files.
    # ------------------------------------------------------------

    if not LINEUPS_BACKUP.exists():
        shutil.copy2(
            LINEUPS_FILE,
            LINEUPS_BACKUP,
        )

    if not MATCHUPS_BACKUP.exists():
        shutil.copy2(
            MATCHUPS_FILE,
            MATCHUPS_BACKUP,
        )

    rebuilt_lineups.to_csv(
        LINEUPS_FILE,
        index=False,
    )

    repaired_matchups.to_csv(
        MATCHUPS_FILE,
        index=False,
    )

    banner("2018 REPAIR COMPLETE")

    print(
        "2018 master files passed all safety checks "
        "and were replaced."
    )

    print()
    print("Next run:")
    print()
    print(
        "python validate_weekly_lineups.py"
    )
    print()
    print(
        "Choose 2018."
    )


if __name__ == "__main__":
    main()