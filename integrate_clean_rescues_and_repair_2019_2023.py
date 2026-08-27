from __future__ import annotations

from pathlib import Path
import re
import shutil
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data" / "matchups" / "player_week_stats"
AUTH_FILE = BASE / "data" / "all_matchups_clean.csv"

RESCUE_DIR = DATA_DIR / "historical_rescues" / "clean"
RESCUE_SUMMARY = RESCUE_DIR / "clean_rescue_summary_2019_2023.csv"

SEASON_WEEKS = {
    2019: 13,
    2020: 13,
    2021: 14,
    2022: 14,
    2023: 14,
}

RECAP_RE = re.compile(
    r"^\s*Week\s+\d+\s+Recap\s+\((?:Won|Lost)\)\s*$",
    re.I,
)


def banner(text):
    print()
    print("=" * 100)
    print(text)
    print("=" * 100)


def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def is_recap(value):
    return bool(RECAP_RE.match(clean(value)))


def normalize_bool(series):
    if series.dtype == bool:
        return series
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes"])
    )


def pair_key(a, b):
    return tuple(sorted([clean(a), clean(b)]))


def score_key(a, b):
    return tuple(sorted([
        round(float(a), 2),
        round(float(b), 2),
    ]))


def build_authoritative(auth_all, year, final_week):
    df = auth_all[
        (pd.to_numeric(auth_all["year"], errors="coerce") == year)
        & (
            pd.to_numeric(
                auth_all["week"],
                errors="coerce",
            ).between(1, final_week)
        )
    ].copy()

    required = [
        "week",
        "team_1",
        "team_1_score",
        "team_2",
        "team_2_score",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise KeyError(
            f"Authoritative file missing columns: {missing}"
        )

    df = df[required].rename(
        columns={
            "team_1": "team_a",
            "team_1_score": "score_a",
            "team_2": "team_b",
            "team_2_score": "score_b",
        }
    )

    df["week"] = pd.to_numeric(
        df["week"],
        errors="raise",
    ).astype(int)

    df["score_a"] = pd.to_numeric(
        df["score_a"],
        errors="raise",
    )

    df["score_b"] = pd.to_numeric(
        df["score_b"],
        errors="raise",
    )

    df["team_a"] = df["team_a"].map(clean)
    df["team_b"] = df["team_b"].map(clean)

    df["pair_key"] = df.apply(
        lambda r: pair_key(
            r["team_a"],
            r["team_b"],
        ),
        axis=1,
    )

    df["score_key"] = df.apply(
        lambda r: score_key(
            r["score_a"],
            r["score_b"],
        ),
        axis=1,
    )

    df = (
        df.drop_duplicates(
            ["week", "pair_key", "score_key"]
        )
        .sort_values(
            ["week", "team_a", "team_b"]
        )
        .reset_index(drop=True)
    )

    return df


def resolve_raw_matchup(row, auth):
    week = int(row["week"])
    left_score = round(
        float(row["left_score"]),
        2,
    )
    right_score = round(
        float(row["right_score"]),
        2,
    )

    skey = score_key(
        left_score,
        right_score,
    )

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

    if visible and len(candidates) > 1:
        narrowed = candidates[
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

        if not narrowed.empty:
            candidates = narrowed

    if len(candidates) != 1:
        return None

    auth_row = candidates.iloc[0]

    team_a = clean(auth_row["team_a"])
    team_b = clean(auth_row["team_b"])

    score_a = round(
        float(auth_row["score_a"]),
        2,
    )
    score_b = round(
        float(auth_row["score_b"]),
        2,
    )

    if (
        left_score == score_a
        and right_score == score_b
    ):
        left_team = team_a
        right_team = team_b
    elif (
        left_score == score_b
        and right_score == score_a
    ):
        left_team = team_b
        right_team = team_a
    else:
        return None

    return {
        "week": week,
        "left_team": left_team,
        "right_team": right_team,
        "left_score": left_score,
        "right_score": right_score,
        "pair_key": pair_key(
            left_team,
            right_team,
        ),
        "score_key": skey,
        "source_matchup_id": str(
            row.get("matchup_id", "")
        ),
        "raw_row": row,
    }


def load_clean_rescues():
    if not RESCUE_SUMMARY.exists():
        raise FileNotFoundError(
            f"Missing clean rescue summary: {RESCUE_SUMMARY}"
        )

    summary = pd.read_csv(
        RESCUE_SUMMARY
    )

    required = {
        "year",
        "week",
        "team_1",
        "team_1_score",
        "team_2",
        "team_2_score",
        "clean_file",
    }

    missing = required - set(
        summary.columns
    )

    if missing:
        raise KeyError(
            f"Clean rescue summary missing: "
            f"{sorted(missing)}"
        )

    rescue_map = {}

    for _, row in summary.iterrows():
        year = int(row["year"])
        week = int(row["week"])

        team1 = clean(row["team_1"])
        team2 = clean(row["team_2"])

        score1 = round(
            float(row["team_1_score"]),
            2,
        )
        score2 = round(
            float(row["team_2_score"]),
            2,
        )

        key = (
            year,
            week,
            pair_key(team1, team2),
            score_key(score1, score2),
        )

        file_path = Path(
            clean(row["clean_file"])
        )

        if not file_path.is_absolute():
            file_path = BASE / file_path

        if not file_path.exists():
            raise FileNotFoundError(
                f"Missing clean rescue file: "
                f"{file_path}"
            )

        rescue_df = pd.read_csv(
            file_path
        )

        rescue_map[key] = {
            "df": rescue_df,
            "team1": team1,
            "team2": team2,
            "score1": score1,
            "score2": score2,
            "file": file_path,
        }

    return rescue_map


def build_clean_matchups(
    year,
    final_week,
    raw_matchups,
    auth,
):
    resolved_rows = []
    unresolved = []

    for _, row in raw_matchups.iterrows():
        resolved = resolve_raw_matchup(
            row,
            auth,
        )

        if resolved is None:
            unresolved.append(row)
            continue

        resolved_rows.append(
            resolved
        )

    if unresolved:
        print(
            f"Unresolved raw matchup rows: "
            f"{len(unresolved)}"
        )

        for row in unresolved[:20]:
            print(
                f"  Week {row['week']} | "
                f"{row['left_team']} "
                f"{row['left_score']} vs "
                f"{row['right_team']} "
                f"{row['right_score']}"
            )

    # Keep only one Yahoo view per real authoritative game.
    seen = set()
    clean_rows = []
    source_ids = {}

    for resolved in resolved_rows:
        key = (
            resolved["week"],
            resolved["pair_key"],
            resolved["score_key"],
        )

        if key in seen:
            continue

        seen.add(key)

        raw = resolved["raw_row"].copy()

        raw["left_team"] = (
            resolved["left_team"]
        )
        raw["right_team"] = (
            resolved["right_team"]
        )
        raw["left_score"] = (
            resolved["left_score"]
        )
        raw["right_score"] = (
            resolved["right_score"]
        )

        clean_rows.append(raw)

        source_ids[key] = (
            resolved["source_matchup_id"]
        )

    clean_df = pd.DataFrame(
        clean_rows
    )

    return (
        clean_df,
        seen,
        source_ids,
    )


def rebuild_existing_lineups(
    raw_lineups,
    clean_matchups,
    source_ids,
):
    parts = []

    for _, matchup in clean_matchups.iterrows():
        week = int(matchup["week"])

        left_team = clean(
            matchup["left_team"]
        )
        right_team = clean(
            matchup["right_team"]
        )

        skey = score_key(
            matchup["left_score"],
            matchup["right_score"],
        )

        pkey = pair_key(
            left_team,
            right_team,
        )

        key = (
            week,
            pkey,
            skey,
        )

        source_id = source_ids.get(
            key
        )

        if not source_id:
            continue

        part = raw_lineups[
            raw_lineups[
                "matchup_id"
            ]
            .astype(str)
            .eq(str(source_id))
        ].copy()

        if part.empty:
            continue

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
            left_mask,
            "team_score",
        ] = float(
            matchup["left_score"]
        )

        part.loc[
            left_mask,
            "opponent_score",
        ] = float(
            matchup["right_score"]
        )

        part.loc[
            right_mask,
            "fantasy_team",
        ] = right_team

        part.loc[
            right_mask,
            "opponent",
        ] = left_team

        part.loc[
            right_mask,
            "team_score",
        ] = float(
            matchup["right_score"]
        )

        part.loc[
            right_mask,
            "opponent_score",
        ] = float(
            matchup["left_score"]
        )

        parts.append(part)

    if not parts:
        return pd.DataFrame(
            columns=raw_lineups.columns
        )

    return pd.concat(
        parts,
        ignore_index=True,
        sort=False,
    )


def rescue_to_matchup_row(
    year,
    rescue,
    template_columns,
):
    team1 = rescue["team1"]
    team2 = rescue["team2"]
    score1 = rescue["score1"]
    score2 = rescue["score2"]

    row = {
        "year": year,
        "week": int(
            rescue["df"]["week"].iloc[0]
        ),
        "left_team": team1,
        "right_team": team2,
        "left_score": score1,
        "right_score": score2,
    }

    if "winner" in template_columns:
        row["winner"] = (
            team1
            if score1 > score2
            else team2
        )

    if "loser" in template_columns:
        row["loser"] = (
            team2
            if score1 > score2
            else team1
        )

    if "margin" in template_columns:
        row["margin"] = round(
            abs(score1 - score2),
            2,
        )

    return row


def conform_rescue_lineups(
    rescue_df,
    year,
    matchup_columns,
    lineup_columns,
):
    df = rescue_df.copy()

    for col in lineup_columns:
        if col not in df.columns:
            df[col] = pd.NA

    df["year"] = year

    return df[
        lineup_columns
    ].copy()


def assign_matchup_ids(
    year,
    matchups,
    lineups,
):
    matchups = matchups.copy()
    lineups = lineups.copy()

    matchups = matchups.sort_values(
        [
            "week",
            "left_team",
            "right_team",
        ]
    ).reset_index(drop=True)

    id_lookup = {}

    for week, group in matchups.groupby(
        "week",
        sort=True,
    ):
        for number, idx in enumerate(
            group.index,
            start=1,
        ):
            new_id = (
                f"{year}-W{int(week):02d}"
                f"-M{number:02d}"
            )

            matchups.at[
                idx,
                "matchup_id",
            ] = new_id

            if (
                "matchup_number"
                in matchups.columns
            ):
                matchups.at[
                    idx,
                    "matchup_number",
                ] = number

            key = (
                int(matchups.at[idx, "week"]),
                pair_key(
                    matchups.at[
                        idx,
                        "left_team",
                    ],
                    matchups.at[
                        idx,
                        "right_team",
                    ],
                ),
                score_key(
                    matchups.at[
                        idx,
                        "left_score",
                    ],
                    matchups.at[
                        idx,
                        "right_score",
                    ],
                ),
            )

            id_lookup[key] = (
                new_id,
                number,
            )

    for idx, row in lineups.iterrows():
        key = (
            int(row["week"]),
            pair_key(
                row["fantasy_team"],
                row["opponent"],
            ),
            score_key(
                row["team_score"],
                row["opponent_score"],
            ),
        )

        if key not in id_lookup:
            continue

        new_id, number = (
            id_lookup[key]
        )

        lineups.at[
            idx,
            "matchup_id",
        ] = new_id

        if (
            "matchup_number"
            in lineups.columns
        ):
            lineups.at[
                idx,
                "matchup_number",
            ] = number

    return (
        matchups,
        lineups,
    )


def validate(
    year,
    final_week,
    auth,
    matchups,
    lineups,
):
    problems = []

    expected_matchups = (
        final_week * 6
    )

    expected_team_weeks = (
        final_week * 12
    )

    expected_starters = (
        expected_team_weeks * 9
    )

    if len(matchups) != expected_matchups:
        problems.append(
            f"matchups {len(matchups)} "
            f"!= {expected_matchups}"
        )

    week_counts = (
        matchups.groupby(
            "week"
        )
        .size()
        .reindex(
            range(
                1,
                final_week + 1,
            ),
            fill_value=0,
        )
    )

    if not (
        week_counts == 6
    ).all():
        problems.append(
            "not every week has "
            "6 matchups"
        )

    teams_long = pd.concat(
        [
            matchups[
                ["week", "left_team"]
            ].rename(
                columns={
                    "left_team": "team"
                }
            ),
            matchups[
                ["week", "right_team"]
            ].rename(
                columns={
                    "right_team": "team"
                }
            ),
        ],
        ignore_index=True,
    )

    team_counts = (
        teams_long.groupby(
            "week"
        )["team"]
        .nunique()
        .reindex(
            range(
                1,
                final_week + 1,
            ),
            fill_value=0,
        )
    )

    if not (
        team_counts == 12
    ).all():
        problems.append(
            "not every week has "
            "12 unique teams"
        )

    recap_matchups = int(
        (
            matchups[
                "left_team"
            ].map(is_recap)
            | matchups[
                "right_team"
            ].map(is_recap)
        ).sum()
    )

    recap_lineups = int(
        (
            lineups[
                "fantasy_team"
            ].map(is_recap)
            | lineups[
                "opponent"
            ].map(is_recap)
        ).sum()
    )

    if recap_matchups:
        problems.append(
            f"{recap_matchups} recap "
            f"matchup labels remain"
        )

    if recap_lineups:
        problems.append(
            f"{recap_lineups} recap "
            f"lineup labels remain"
        )

    starters = lineups[
        normalize_bool(
            lineups["is_starter"]
        )
    ].copy()

    starter_counts = (
        starters.groupby(
            [
                "week",
                "fantasy_team",
            ]
        )
        .size()
        .reset_index(
            name="count"
        )
    )

    if (
        len(starter_counts)
        != expected_team_weeks
    ):
        problems.append(
            f"starter team-weeks "
            f"{len(starter_counts)} "
            f"!= {expected_team_weeks}"
        )

    bad_starters = (
        starter_counts[
            starter_counts[
                "count"
            ] != 9
        ]
    )

    if not bad_starters.empty:
        problems.append(
            f"{len(bad_starters)} "
            f"team-weeks do not "
            f"have 9 starters"
        )

    if len(starters) != expected_starters:
        problems.append(
            f"starter rows "
            f"{len(starters)} "
            f"!= {expected_starters}"
        )

    starters[
        "_calc_points"
    ] = pd.to_numeric(
        starters[
            "fantasy_points"
        ],
        errors="coerce",
    ).fillna(0.0)

    score_check = (
        starters.groupby(
            [
                "week",
                "fantasy_team",
            ],
            as_index=False,
        )
        .agg(
            calculated=(
                "_calc_points",
                "sum",
            ),
            yahoo_score=(
                "team_score",
                "first",
            ),
        )
    )

    score_check[
        "difference"
    ] = (
        score_check[
            "calculated"
        ]
        - pd.to_numeric(
            score_check[
                "yahoo_score"
            ],
            errors="coerce",
        )
    ).abs()

    bad_scores = (
        score_check[
            score_check[
                "difference"
            ] > 0.011
        ]
    )

    if not bad_scores.empty:
        problems.append(
            f"{len(bad_scores)} "
            f"starter-score mismatches"
        )

    auth_keys = {
        (
            int(r["week"]),
            r["pair_key"],
            r["score_key"],
        )
        for _, r in auth.iterrows()
    }

    repaired_keys = {
        (
            int(r["week"]),
            pair_key(
                r["left_team"],
                r["right_team"],
            ),
            score_key(
                r["left_score"],
                r["right_score"],
            ),
        )
        for _, r in matchups.iterrows()
    }

    missing_auth = (
        auth_keys - repaired_keys
    )

    extra_repaired = (
        repaired_keys - auth_keys
    )

    if missing_auth:
        problems.append(
            f"{len(missing_auth)} "
            f"authoritative matchups missing"
        )

    if extra_repaired:
        problems.append(
            f"{len(extra_repaired)} "
            f"non-authoritative matchups present"
        )

    print(
        f"{year}: "
        f"{len(matchups)}/{expected_matchups} matchups · "
        f"{len(starter_counts)}/{expected_team_weeks} team-weeks · "
        f"{len(starters)}/{expected_starters} starters · "
        f"{len(bad_scores)} score mismatches · "
        f"{recap_matchups + recap_lineups} recap labels"
    )

    if problems:
        for p in problems:
            print(
                f"  [FAIL] {p}"
            )
        return False

    print(
        "  [PASS] all safety checks"
    )

    return True


def main():
    banner(
        "FINAL 2019-2023 HISTORICAL REPAIR "
        "WITH CLEAN RESCUES"
    )

    if not AUTH_FILE.exists():
        raise FileNotFoundError(
            AUTH_FILE
        )

    auth_all = pd.read_csv(
        AUTH_FILE
    )

    rescue_map = (
        load_clean_rescues()
    )

    repaired = {}
    all_pass = True

    for year, final_week in (
        SEASON_WEEKS.items()
    ):
        banner(str(year))

        lineup_path = (
            DATA_DIR
            / f"{year}_weekly_lineups.csv"
        )

        matchup_path = (
            DATA_DIR
            / f"{year}_matchups.csv"
        )

        raw_lineups = pd.read_csv(
            lineup_path
        )

        raw_matchups = pd.read_csv(
            matchup_path
        )

        raw_lineups[
            "week"
        ] = pd.to_numeric(
            raw_lineups[
                "week"
            ],
            errors="raise",
        ).astype(int)

        raw_matchups[
            "week"
        ] = pd.to_numeric(
            raw_matchups[
                "week"
            ],
            errors="raise",
        ).astype(int)

        raw_lineups = raw_lineups[
            raw_lineups[
                "week"
            ].between(
                1,
                final_week,
            )
        ].copy()

        raw_matchups = raw_matchups[
            raw_matchups[
                "week"
            ].between(
                1,
                final_week,
            )
        ].copy()

        auth = build_authoritative(
            auth_all,
            year,
            final_week,
        )

        (
            clean_matchups,
            seen_keys,
            source_ids,
        ) = build_clean_matchups(
            year,
            final_week,
            raw_matchups,
            auth,
        )

        clean_lineups = (
            rebuild_existing_lineups(
                raw_lineups,
                clean_matchups,
                source_ids,
            )
        )

        # Add rescues for authoritative games that were never present
        # in the original Yahoo season files.
        auth_keys = {
            (
                year,
                int(r["week"]),
                r["pair_key"],
                r["score_key"],
            )
            for _, r in auth.iterrows()
        }

        current_keys = {
            (
                year,
                int(r["week"]),
                pair_key(
                    r["left_team"],
                    r["right_team"],
                ),
                score_key(
                    r["left_score"],
                    r["right_score"],
                ),
            )
            for _, r in clean_matchups.iterrows()
        }

        missing_keys = (
            auth_keys - current_keys
        )

        print(
            f"Missing authoritative games "
            f"before rescue: {len(missing_keys)}"
        )

        rescue_matchup_rows = []
        rescue_lineup_parts = []

        for key in sorted(
            missing_keys,
            key=lambda x: (
                x[1],
                x[2],
            ),
        ):
            if key not in rescue_map:
                print(
                    f"[FAIL] no clean rescue "
                    f"for {key}"
                )
                all_pass = False
                continue

            rescue = (
                rescue_map[key]
            )

            rescue_matchup_rows.append(
                rescue_to_matchup_row(
                    year,
                    rescue,
                    clean_matchups.columns,
                )
            )

            rescue_lineup_parts.append(
                conform_rescue_lineups(
                    rescue["df"],
                    year,
                    clean_matchups.columns,
                    raw_lineups.columns,
                )
            )

            print(
                f"[RESCUE] Week {key[1]} · "
                f"{rescue['team1']} vs "
                f"{rescue['team2']}"
            )

        if rescue_matchup_rows:
            rescue_matchups_df = (
                pd.DataFrame(
                    rescue_matchup_rows
                )
            )

            for col in (
                clean_matchups.columns
            ):
                if (
                    col
                    not in rescue_matchups_df.columns
                ):
                    rescue_matchups_df[
                        col
                    ] = pd.NA

            rescue_matchups_df = (
                rescue_matchups_df[
                    clean_matchups.columns
                ]
            )

            clean_matchups = pd.concat(
                [
                    clean_matchups,
                    rescue_matchups_df,
                ],
                ignore_index=True,
                sort=False,
            )

        if rescue_lineup_parts:
            clean_lineups = pd.concat(
                [
                    clean_lineups,
                    *rescue_lineup_parts,
                ],
                ignore_index=True,
                sort=False,
            )

        (
            clean_matchups,
            clean_lineups,
        ) = assign_matchup_ids(
            year,
            clean_matchups,
            clean_lineups,
        )

        passed = validate(
            year,
            final_week,
            auth,
            clean_matchups,
            clean_lineups,
        )

        if not passed:
            all_pass = False
            continue

        repaired[year] = {
            "lineups": clean_lineups,
            "matchups": clean_matchups,
            "lineup_path": lineup_path,
            "matchup_path": matchup_path,
        }

    banner("FINAL SAFETY RESULT")

    if (
        not all_pass
        or len(repaired)
        != len(SEASON_WEEKS)
    ):
        print(
            "REPAIR NOT APPLIED. "
            "At least one season failed."
        )
        print(
            "Original files were NOT overwritten."
        )
        return

    print(
        "All five seasons passed."
    )
    print(
        "Creating backups and writing repaired files."
    )

    for year, data in (
        repaired.items()
    ):
        lineup_backup = (
            DATA_DIR
            / f"{year}_weekly_lineups_before_final_recap_repair.csv"
        )

        matchup_backup = (
            DATA_DIR
            / f"{year}_matchups_before_final_recap_repair.csv"
        )

        if not lineup_backup.exists():
            shutil.copy2(
                data["lineup_path"],
                lineup_backup,
            )

        if not matchup_backup.exists():
            shutil.copy2(
                data["matchup_path"],
                matchup_backup,
            )

        data["lineups"].to_csv(
            data["lineup_path"],
            index=False,
        )

        data["matchups"].to_csv(
            data["matchup_path"],
            index=False,
        )

        print(
            f"[SAVED] {year}"
        )

    banner("REPAIR COMPLETE")
    print(
        "2019-2023 season files repaired."
    )
    print(
        "Next run validate_weekly_lineups.py "
        "for 2019, 2020, 2021, 2022, and 2023."
    )


if __name__ == "__main__":
    main()