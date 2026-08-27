from __future__ import annotations

from pathlib import Path
import re
import shutil
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data" / "matchups" / "player_week_stats"
AUTH_FILE = BASE / "data" / "all_matchups_clean.csv"

SEASON_WEEKS = {
    2019: 13,
    2020: 13,
    2021: 14,
    2022: 14,
    2023: 14,
}

RECAP_RE = re.compile(r"^\s*Week\s+\d+\s+Recap\s+\((?:Won|Lost)\)\s*$", re.I)


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


def score_key(a, b):
    return tuple(sorted([round(float(a), 2), round(float(b), 2)]))


def pair_key(a, b):
    return tuple(sorted([clean(a), clean(b)]))


def normalize_bool(series):
    if series.dtype == bool:
        return series
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes"])
    )


def build_authoritative(auth, year, final_week):
    required = {
        "year", "week",
        "team_1", "team_1_score",
        "team_2", "team_2_score",
    }
    missing = required - set(auth.columns)
    if missing:
        raise KeyError(
            f"Authoritative file missing columns: {sorted(missing)}"
        )

    df = auth[
        (pd.to_numeric(auth["year"], errors="coerce") == year)
        & (pd.to_numeric(auth["week"], errors="coerce").between(1, final_week))
    ].copy()

    df = df[
        ["week", "team_1", "team_1_score", "team_2", "team_2_score"]
    ].rename(
        columns={
            "team_1": "team_a",
            "team_1_score": "score_a",
            "team_2": "team_b",
            "team_2_score": "score_b",
        }
    )

    df["week"] = pd.to_numeric(df["week"], errors="raise").astype(int)
    df["score_a"] = pd.to_numeric(df["score_a"], errors="raise")
    df["score_b"] = pd.to_numeric(df["score_b"], errors="raise")
    df["team_a"] = df["team_a"].map(clean)
    df["team_b"] = df["team_b"].map(clean)

    df["pair_key"] = df.apply(
        lambda r: pair_key(r["team_a"], r["team_b"]), axis=1
    )
    df["score_key"] = df.apply(
        lambda r: score_key(r["score_a"], r["score_b"]), axis=1
    )

    df = (
        df.sort_values(["week", "pair_key"])
        .drop_duplicates(["week", "pair_key", "score_key"])
        .reset_index(drop=True)
    )

    return df


def resolve_matchup_row(row, auth):
    week = int(row["week"])
    lscore = round(float(row["left_score"]), 2)
    rscore = round(float(row["right_score"]), 2)
    skey = score_key(lscore, rscore)

    candidates = auth[
        (auth["week"] == week)
        & (auth["score_key"] == skey)
    ].copy()

    visible = {
        t for t in [clean(row["left_team"]), clean(row["right_team"])]
        if t and not is_recap(t)
    }

    if visible and len(candidates) > 1:
        narrowed = candidates[
            candidates.apply(
                lambda r: bool(
                    visible & {clean(r["team_a"]), clean(r["team_b"])}
                ),
                axis=1,
            )
        ]
        if not narrowed.empty:
            candidates = narrowed

    if len(candidates) != 1:
        return None

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
        return None

    out = row.copy()
    out["left_team"] = left_team
    out["right_team"] = right_team
    out["_pair_key"] = pair_key(left_team, right_team)
    out["_score_key"] = skey
    return out


def rebuild_lineups(lineups, kept_matchups):
    parts = []

    lookup = {
        str(r["matchup_id"]): (clean(r["left_team"]), clean(r["right_team"]))
        for _, r in kept_matchups.iterrows()
    }

    for matchup_id, (left_team, right_team) in lookup.items():
        part = lineups[
            lineups["matchup_id"].astype(str).eq(matchup_id)
        ].copy()

        if part.empty:
            continue

        left_mask = part["side"].astype(str).str.lower().eq("left")
        right_mask = part["side"].astype(str).str.lower().eq("right")

        part.loc[left_mask, "fantasy_team"] = left_team
        part.loc[left_mask, "opponent"] = right_team

        part.loc[right_mask, "fantasy_team"] = right_team
        part.loc[right_mask, "opponent"] = left_team

        parts.append(part)

    if not parts:
        return pd.DataFrame(columns=lineups.columns)

    return pd.concat(parts, ignore_index=True, sort=False)


def validate_season(year, final_week, auth, matchups, lineups):
    problems = []

    expected_matchups = final_week * 6
    expected_team_weeks = final_week * 12
    expected_starters = expected_team_weeks * 9

    if len(auth) != expected_matchups:
        problems.append(
            f"authoritative matchup count {len(auth)} != {expected_matchups}"
        )

    if len(matchups) != expected_matchups:
        problems.append(
            f"repaired matchup count {len(matchups)} != {expected_matchups}"
        )

    matchup_counts = (
        matchups.groupby("week").size()
        .reindex(range(1, final_week + 1), fill_value=0)
    )
    if not (matchup_counts == 6).all():
        problems.append("not every week has exactly 6 matchups")

    teams_long = pd.concat(
        [
            matchups[["week", "left_team"]].rename(columns={"left_team": "team"}),
            matchups[["week", "right_team"]].rename(columns={"right_team": "team"}),
        ],
        ignore_index=True,
    )
    team_counts = (
        teams_long.groupby("week")["team"].nunique()
        .reindex(range(1, final_week + 1), fill_value=0)
    )
    if not (team_counts == 12).all():
        problems.append("not every week has exactly 12 unique teams")

    recap_matchups = int(
        (
            matchups["left_team"].map(is_recap)
            | matchups["right_team"].map(is_recap)
        ).sum()
    )
    recap_lineups = int(
        (
            lineups["fantasy_team"].map(is_recap)
            | lineups["opponent"].map(is_recap)
        ).sum()
    )

    if recap_matchups:
        problems.append(f"{recap_matchups} recap-labeled matchup rows remain")
    if recap_lineups:
        problems.append(f"{recap_lineups} recap-labeled lineup rows remain")

    starter_mask = normalize_bool(lineups["is_starter"])
    starters = lineups[starter_mask].copy()

    starter_counts = (
        starters.groupby(["week", "fantasy_team"]).size()
        .reset_index(name="count")
    )

    if len(starter_counts) != expected_team_weeks:
        problems.append(
            f"starter team-week coverage {len(starter_counts)} != {expected_team_weeks}"
        )

    bad_starter_counts = starter_counts[starter_counts["count"] != 9]
    if not bad_starter_counts.empty:
        problems.append(
            f"{len(bad_starter_counts)} team-weeks do not have 9 starters"
        )

    if len(starters) != expected_starters:
        problems.append(
            f"starter row count {len(starters)} != {expected_starters}"
        )

    # Score reconciliation.
    starters["calc_points"] = pd.to_numeric(
        starters["fantasy_points"], errors="coerce"
    ).fillna(0.0)

    calc = (
        starters.groupby(["week", "fantasy_team"], as_index=False)
        .agg(
            calculated_starter_points=("calc_points", "sum"),
            yahoo_team_score=("team_score", "first"),
        )
    )

    calc["difference"] = (
        calc["calculated_starter_points"]
        - pd.to_numeric(calc["yahoo_team_score"], errors="coerce")
    ).abs()

    bad_scores = calc[calc["difference"] > 0.011]
    if not bad_scores.empty:
        problems.append(
            f"{len(bad_scores)} team-weeks fail starter-score reconciliation"
        )

    print(f"{year} validation:")
    print(f"  matchups:     {len(matchups)}/{expected_matchups}")
    print(f"  team-weeks:   {len(starter_counts)}/{expected_team_weeks}")
    print(f"  starters:     {len(starters)}/{expected_starters}")
    print(f"  recap matchup labels: {recap_matchups}")
    print(f"  recap lineup labels:  {recap_lineups}")
    print(f"  score mismatches:      {len(bad_scores)}")

    if problems:
        for p in problems:
            print(f"  [FAIL] {p}")
        return False

    print("  [PASS] all safety checks")
    return True


def main():
    banner("REPAIRING HISTORICAL YAHOO RECAP LABELS — 2019-2023")
    print("This script will NOT overwrite anything unless every season passes.")

    if not AUTH_FILE.exists():
        raise FileNotFoundError(
            f"Missing authoritative matchup file: {AUTH_FILE}"
        )

    auth_all = pd.read_csv(AUTH_FILE)

    repaired = {}
    all_pass = True

    for year, final_week in SEASON_WEEKS.items():
        banner(str(year))

        lineup_path = DATA_DIR / f"{year}_weekly_lineups.csv"
        matchup_path = DATA_DIR / f"{year}_matchups.csv"

        lineups = pd.read_csv(lineup_path)
        matchups = pd.read_csv(matchup_path)

        # Regular season only.
        lineups["week"] = pd.to_numeric(
            lineups["week"], errors="raise"
        ).astype(int)
        matchups["week"] = pd.to_numeric(
            matchups["week"], errors="raise"
        ).astype(int)

        lineups = lineups[
            lineups["week"].between(1, final_week)
        ].copy()
        matchups = matchups[
            matchups["week"].between(1, final_week)
        ].copy()

        auth = build_authoritative(auth_all, year, final_week)

        resolved_rows = []
        unresolved = []

        for _, row in matchups.iterrows():
            resolved = resolve_matchup_row(row, auth)
            if resolved is None:
                unresolved.append(row)
            else:
                resolved_rows.append(resolved)

        resolved_df = pd.DataFrame(resolved_rows)

        if unresolved:
            print(f"Unresolved matchup rows: {len(unresolved)}")
            for row in unresolved[:20]:
                print(
                    f"  Week {row['week']} | "
                    f"{row['left_team']} {row['left_score']} vs "
                    f"{row['right_team']} {row['right_score']}"
                )
            all_pass = False
            continue

        # Collapse mirrored Yahoo views by authoritative matchup identity.
        kept = (
            resolved_df
            .sort_values(["week", "_pair_key", "matchup_id"])
            .drop_duplicates(
                subset=["week", "_pair_key", "_score_key"],
                keep="first",
            )
            .copy()
        )

        rebuilt_lineups = rebuild_lineups(lineups, kept)

        # Renumber matchup IDs sequentially within each week.
        kept = kept.sort_values(["week", "_pair_key"]).copy()
        id_map = {}

        for week, idxs in kept.groupby("week").groups.items():
            for n, idx in enumerate(idxs, start=1):
                old_id = str(kept.at[idx, "matchup_id"])
                new_id = f"{year}-W{int(week):02d}-M{n:02d}"
                id_map[old_id] = new_id
                kept.at[idx, "matchup_id"] = new_id
                if "matchup_number" in kept.columns:
                    kept.at[idx, "matchup_number"] = n

        rebuilt_lineups["matchup_id"] = (
            rebuilt_lineups["matchup_id"]
            .astype(str)
            .map(lambda x: id_map.get(x, x))
        )

        if "matchup_number" in rebuilt_lineups.columns:
            rebuilt_lineups["matchup_number"] = (
                rebuilt_lineups["matchup_id"]
                .str.extract(r"-M(\d+)$")[0]
                .astype(int)
            )

        kept = kept.drop(columns=["_pair_key", "_score_key"], errors="ignore")

        passed = validate_season(
            year, final_week, auth, kept, rebuilt_lineups
        )

        if not passed:
            all_pass = False
            continue

        repaired[year] = {
            "lineups": rebuilt_lineups,
            "matchups": kept,
            "lineup_path": lineup_path,
            "matchup_path": matchup_path,
        }

    banner("FINAL SAFETY RESULT")

    if not all_pass or len(repaired) != len(SEASON_WEEKS):
        print(
            "REPAIR NOT APPLIED. At least one season failed validation. "
            "Original files were NOT overwritten."
        )
        return

    print("All five seasons passed. Creating backups and writing repaired files.")

    for year, data in repaired.items():
        lineup_path = data["lineup_path"]
        matchup_path = data["matchup_path"]

        lineup_backup = DATA_DIR / f"{year}_weekly_lineups_before_recap_repair.csv"
        matchup_backup = DATA_DIR / f"{year}_matchups_before_recap_repair.csv"

        if not lineup_backup.exists():
            shutil.copy2(lineup_path, lineup_backup)
        if not matchup_backup.exists():
            shutil.copy2(matchup_path, matchup_backup)

        data["lineups"].to_csv(lineup_path, index=False)
        data["matchups"].to_csv(matchup_path, index=False)

        print(f"[SAVED] {year}")

    banner("REPAIR COMPLETE")
    print("Next run each repaired season through validate_weekly_lineups.py.")
    print("Then rebuild the master files with build_master_weekly_data.py.")


if __name__ == "__main__":
    main()