from __future__ import annotations

from pathlib import Path
import re
import shutil
import pandas as pd

SCRIPT_VERSION = "2018-clean-matchups-v3-REAL"

YEAR = 2018
REGULAR_WEEKS = list(range(1, 14))

BASE_DIR = Path(__file__).resolve().parent
PLAYER_DIR = BASE_DIR / "data" / "matchups" / "player_week_stats"

LINEUPS_FILE = PLAYER_DIR / "2018_weekly_lineups.csv"
MATCHUPS_FILE = PLAYER_DIR / "2018_matchups.csv"

SOURCE_FILE = BASE_DIR / "data" / "all_matchups_clean.csv"

LINEUPS_BACKUP = PLAYER_DIR / "2018_weekly_lineups_before_clean_repair.csv"
MATCHUPS_BACKUP = PLAYER_DIR / "2018_matchups_before_clean_repair.csv"

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
    return tuple(sorted([round(float(a), 2), round(float(b), 2)]))


def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def main():
    print(f"SCRIPT VERSION: {SCRIPT_VERSION}")
    banner("2018 CLEAN-MATCHUP REPAIR")

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(f"Missing {SOURCE_FILE}")

    lineups = pd.read_csv(LINEUPS_FILE)
    collected = pd.read_csv(MATCHUPS_FILE)
    source = pd.read_csv(SOURCE_FILE)

    required = {
        "year",
        "week",
        "team_1",
        "team_1_score",
        "team_2",
        "team_2_score",
    }

    missing = required - set(source.columns)
    if missing:
        raise KeyError(
            f"Missing required columns: {sorted(missing)}\n"
            f"Available: {list(source.columns)}"
        )

    print("Detected authoritative columns:")
    print("  team_1")
    print("  team_1_score")
    print("  team_2")
    print("  team_2_score")

    auth = source[
        (pd.to_numeric(source["year"], errors="coerce") == YEAR)
        & (pd.to_numeric(source["week"], errors="coerce").isin(REGULAR_WEEKS))
    ].copy()

    auth = auth[
        ["week", "team_1", "team_1_score", "team_2", "team_2_score"]
    ].rename(
        columns={
            "team_1": "team_a",
            "team_1_score": "score_a",
            "team_2": "team_b",
            "team_2_score": "score_b",
        }
    )

    auth["week"] = pd.to_numeric(auth["week"], errors="coerce").astype(int)
    auth["score_a"] = pd.to_numeric(auth["score_a"], errors="coerce")
    auth["score_b"] = pd.to_numeric(auth["score_b"], errors="coerce")
    auth["team_a"] = auth["team_a"].map(clean)
    auth["team_b"] = auth["team_b"].map(clean)

    auth["pair_key"] = auth.apply(
        lambda r: tuple(sorted([r["team_a"], r["team_b"]])),
        axis=1,
    )
    auth["score_key"] = auth.apply(
        lambda r: score_key(r["score_a"], r["score_b"]),
        axis=1,
    )

    auth = (
        auth.sort_values(["week", "pair_key"])
        .drop_duplicates(
            subset=["week", "pair_key", "score_key"],
            keep="first",
        )
        .reset_index(drop=True)
    )

    banner("AUTHORITATIVE SOURCE CHECK")
    counts = auth.groupby("week").size().reindex(REGULAR_WEEKS, fill_value=0)
    print(counts.to_string())
    print(f"\nTotal authoritative matchups: {len(auth)}")

    if len(auth) != 78 or not (counts == 6).all():
        print("\nSTOP: authoritative source is not exactly 78 matchups / 6 per week.")
        print("Nothing was changed.")
        return

    collected = collected[
        pd.to_numeric(collected["week"], errors="coerce").isin(REGULAR_WEEKS)
    ].copy()

    resolved_rows = []
    unresolved = []

    for _, row in collected.iterrows():
        week = int(row["week"])
        left_score = round(float(row["left_score"]), 2)
        right_score = round(float(row["right_score"]), 2)
        skey = score_key(left_score, right_score)

        candidates = auth[
            (auth["week"] == week)
            & (auth["score_key"] == skey)
        ].copy()

        visible = {
            team
            for team in [clean(row["left_team"]), clean(row["right_team"])]
            if team and not is_recap(team)
        }

        if visible:
            candidates = candidates[
                candidates.apply(
                    lambda r: bool(
                        visible & {clean(r["team_a"]), clean(r["team_b"])}
                    ),
                    axis=1,
                )
            ]

        if len(candidates) != 1:
            unresolved.append(
                {
                    "week": week,
                    "matchup_id": clean(row["matchup_id"]),
                    "left_team": clean(row["left_team"]),
                    "right_team": clean(row["right_team"]),
                    "left_score": left_score,
                    "right_score": right_score,
                    "candidate_count": len(candidates),
                }
            )
            continue

        a = candidates.iloc[0]

        team_a = clean(a["team_a"])
        team_b = clean(a["team_b"])
        score_a = round(float(a["score_a"]), 2)
        score_b = round(float(a["score_b"]), 2)

        if left_score == score_a and right_score == score_b:
            resolved_left, resolved_right = team_a, team_b
        elif left_score == score_b and right_score == score_a:
            resolved_left, resolved_right = team_b, team_a
        else:
            unresolved.append(
                {
                    "week": week,
                    "matchup_id": clean(row["matchup_id"]),
                    "left_team": clean(row["left_team"]),
                    "right_team": clean(row["right_team"]),
                    "left_score": left_score,
                    "right_score": right_score,
                    "candidate_count": 1,
                }
            )
            continue

        new_row = row.copy()
        new_row["left_team"] = resolved_left
        new_row["right_team"] = resolved_right
        new_row["_pair_key"] = tuple(sorted([resolved_left, resolved_right]))
        new_row["_score_key"] = skey
        resolved_rows.append(new_row)

    if unresolved:
        banner("UNRESOLVED ROWS — NOTHING CHANGED")
        print(pd.DataFrame(unresolved).to_string(index=False))
        return

    resolved = pd.DataFrame(resolved_rows)

    kept = (
        resolved.sort_values(["week", "_pair_key", "matchup_id"])
        .drop_duplicates(
            subset=["week", "_pair_key", "_score_key"],
            keep="first",
        )
        .copy()
    )

    if len(kept) != 78:
        banner("SAFETY CHECK FAILED")
        print(f"Unique resolved matchups: {len(kept)} (expected 78)")
        print("Nothing was changed.")
        return

    old_ids = kept["matchup_id"].astype(str).tolist()
    team_lookup = {
        str(r["matchup_id"]): (clean(r["left_team"]), clean(r["right_team"]))
        for _, r in kept.iterrows()
    }

    id_map = {}
    kept = kept.sort_values(["week", "_pair_key"]).copy()

    for week, idxs in kept.groupby("week").groups.items():
        for n, idx in enumerate(idxs, start=1):
            old_id = str(kept.at[idx, "matchup_id"])
            new_id = f"2018-W{int(week):02d}-M{n:02d}"
            id_map[old_id] = new_id
            kept.at[idx, "matchup_id"] = new_id
            kept.at[idx, "matchup_number"] = n

    repaired_matchups = kept.drop(
        columns=["_pair_key", "_score_key"],
        errors="ignore",
    )

    parts = []

    for old_id in old_ids:
        part = lineups[
            lineups["matchup_id"].astype(str).eq(old_id)
        ].copy()

        if part.empty:
            continue

        left_team, right_team = team_lookup[old_id]

        left_mask = part["side"].astype(str).str.lower().eq("left")
        right_mask = part["side"].astype(str).str.lower().eq("right")

        part.loc[left_mask, "fantasy_team"] = left_team
        part.loc[left_mask, "opponent"] = right_team

        part.loc[right_mask, "fantasy_team"] = right_team
        part.loc[right_mask, "opponent"] = left_team

        new_id = id_map[old_id]
        part["matchup_id"] = new_id
        part["matchup_number"] = int(new_id.rsplit("-M", 1)[1])

        parts.append(part)

    repaired_lineups = pd.concat(parts, ignore_index=True)

    banner("POST-REPAIR CHECKS")

    matchup_counts = (
        repaired_matchups.groupby("week")
        .size()
        .reindex(REGULAR_WEEKS, fill_value=0)
    )

    teams = pd.concat(
        [
            repaired_matchups[["week", "left_team"]].rename(
                columns={"left_team": "team"}
            ),
            repaired_matchups[["week", "right_team"]].rename(
                columns={"right_team": "team"}
            ),
        ],
        ignore_index=True,
    )

    team_counts = (
        teams.groupby("week")["team"]
        .nunique()
        .reindex(REGULAR_WEEKS, fill_value=0)
    )

    starter_count = int(repaired_lineups["is_starter"].sum())

    recap_matchups = int(
        (
            repaired_matchups["left_team"].map(is_recap)
            | repaired_matchups["right_team"].map(is_recap)
        ).sum()
    )

    recap_lineups = int(
        (
            repaired_lineups["fantasy_team"].map(is_recap)
            | repaired_lineups["opponent"].map(is_recap)
        ).sum()
    )

    print("Matchups per week:")
    print(matchup_counts.to_string())

    print("\nUnique teams per week:")
    print(team_counts.to_string())

    print(f"\nTotal matchups:       {len(repaired_matchups)}")
    print(f"Starter records:      {starter_count}")
    print(f"Recap matchup labels: {recap_matchups}")
    print(f"Recap lineup labels:  {recap_lineups}")

    passed = (
        len(repaired_matchups) == 78
        and (matchup_counts == 6).all()
        and (team_counts == 12).all()
        and starter_count == 1404
        and recap_matchups == 0
        and recap_lineups == 0
    )

    if not passed:
        print("\nREPAIR CHECK FAILED. Nothing was overwritten.")
        return

    if not LINEUPS_BACKUP.exists():
        shutil.copy2(LINEUPS_FILE, LINEUPS_BACKUP)

    if not MATCHUPS_BACKUP.exists():
        shutil.copy2(MATCHUPS_FILE, MATCHUPS_BACKUP)

    repaired_lineups.to_csv(LINEUPS_FILE, index=False)
    repaired_matchups.to_csv(MATCHUPS_FILE, index=False)

    banner("2018 REPAIR COMPLETE")
    print("Repaired files passed all safety checks and were saved.")
    print("\nNow run:")
    print("python validate_weekly_lineups.py")
    print("and choose 2018.")


if __name__ == "__main__":
    main()