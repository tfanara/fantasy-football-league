from pathlib import Path
import pandas as pd
import re

YEAR = 2018
REGULAR_WEEKS = list(range(1, 14))

BASE_DIR = Path(__file__).resolve().parent
PLAYER_DIR = BASE_DIR / "data" / "matchups" / "player_week_stats"

MATCHUPS_FILE = PLAYER_DIR / "2018_matchups.csv"
SOURCE_FILE = BASE_DIR / "data" / "all_matchups_clean.csv"

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

def pair_key(a, b):
    return tuple(sorted([clean(a), clean(b)]))

def banner(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)

def main():
    source = pd.read_csv(SOURCE_FILE)
    collected = pd.read_csv(MATCHUPS_FILE)

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
        lambda r: pair_key(r["team_a"], r["team_b"]),
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

    collected = collected[
        pd.to_numeric(collected["week"], errors="coerce").isin(REGULAR_WEEKS)
    ].copy()

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
            t for t in [clean(row["left_team"]), clean(row["right_team"])]
            if t and not is_recap(t)
        }

        if visible:
            candidates2 = candidates[
                candidates.apply(
                    lambda r: bool(
                        visible & {clean(r["team_a"]), clean(r["team_b"])}
                    ),
                    axis=1,
                )
            ]
            if not candidates2.empty:
                candidates = candidates2

        if len(candidates) != 1:
            continue

        a = candidates.iloc[0]

        resolved.append(
            {
                "week": week,
                "matchup_id": clean(row["matchup_id"]),
                "auth_pair_key": pair_key(a["team_a"], a["team_b"]),
                "score_key": skey,
                "raw_left_team": clean(row["left_team"]),
                "raw_right_team": clean(row["right_team"]),
                "left_score": lscore,
                "right_score": rscore,
            }
        )

    resolved_df = pd.DataFrame(resolved)

    resolved_unique = (
        resolved_df
        .drop_duplicates(
            subset=["week", "auth_pair_key", "score_key"],
            keep="first",
        )
        .copy()
    )

    auth_keys = set(
        (
            int(r["week"]),
            r["pair_key"],
            r["score_key"],
        )
        for _, r in auth.iterrows()
    )

    resolved_keys = set(
        (
            int(r["week"]),
            r["auth_pair_key"],
            r["score_key"],
        )
        for _, r in resolved_unique.iterrows()
    )

    missing = auth_keys - resolved_keys

    banner("MISSING AUTHORITATIVE MATCHUP(S)")

    if not missing:
        print("None.")
    else:
        for week, pkey, skey in sorted(missing):
            row = auth[
                (auth["week"] == week)
                & (auth["pair_key"] == pkey)
                & (auth["score_key"] == skey)
            ].iloc[0]

            print(
                f"Week {week}: "
                f"{row['team_a']} {row['score_a']} vs "
                f"{row['team_b']} {row['score_b']}"
            )

            print()
            print("Collected rows in that week with same score pair:")

            same_score = collected[
                (pd.to_numeric(collected["week"], errors="coerce") == week)
                & collected.apply(
                    lambda r: score_key(
                        r["left_score"],
                        r["right_score"],
                    ) == skey,
                    axis=1,
                )
            ]

            if same_score.empty:
                print("  NONE")
            else:
                print(
                    same_score[
                        [
                            "matchup_id",
                            "left_team",
                            "right_team",
                            "left_score",
                            "right_score",
                            "yahoo_team_id_used",
                        ]
                    ].to_string(index=False)
                )

    banner("AUTHORITATIVE PAIRS RESOLVED MORE THAN ONCE")

    counts = (
        resolved_df.groupby(
            ["week", "auth_pair_key", "score_key"]
        )
        .size()
        .reset_index(name="views")
    )

    repeated = counts[counts["views"] > 1].copy()

    if repeated.empty:
        print("None.")
    else:
        print(repeated.to_string(index=False))

    print()
    print("Resolved authoritative unique matchups:", len(resolved_unique))
    print("Expected:", len(auth))

if __name__ == "__main__":
    main()