from pathlib import Path
import re
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


def build_authoritative(auth, year, final_week):
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

    return (
        df.drop_duplicates(["week", "pair_key", "score_key"])
        .reset_index(drop=True)
    )


def resolve_row(row, auth):
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
    return {
        "week": week,
        "auth_pair_key": pair_key(a["team_a"], a["team_b"]),
        "score_key": skey,
        "raw_matchup_id": row.get("matchup_id", ""),
        "raw_left_team": clean(row["left_team"]),
        "raw_right_team": clean(row["right_team"]),
        "left_score": lscore,
        "right_score": rscore,
    }


def main():
    banner("MISSING AUTHORITATIVE GAME DIAGNOSTIC — 2019-2023")
    print("READ-ONLY. No files will be changed.")

    auth_all = pd.read_csv(AUTH_FILE)

    for year, final_week in SEASON_WEEKS.items():
        banner(str(year))

        raw = pd.read_csv(DATA_DIR / f"{year}_matchups.csv")
        raw["week"] = pd.to_numeric(raw["week"], errors="raise").astype(int)
        raw = raw[raw["week"].between(1, final_week)].copy()

        auth = build_authoritative(auth_all, year, final_week)

        resolved = []
        unresolved = []

        for _, row in raw.iterrows():
            r = resolve_row(row, auth)
            if r is None:
                unresolved.append(row)
            else:
                resolved.append(r)

        resolved_df = pd.DataFrame(resolved)

        if resolved_df.empty:
            unique_resolved = resolved_df
        else:
            unique_resolved = resolved_df.drop_duplicates(
                ["week", "auth_pair_key", "score_key"]
            )

        auth_keys = {
            (int(r["week"]), r["pair_key"], r["score_key"])
            for _, r in auth.iterrows()
        }

        resolved_keys = {
            (int(r["week"]), r["auth_pair_key"], r["score_key"])
            for _, r in unique_resolved.iterrows()
        }

        missing = sorted(auth_keys - resolved_keys)

        print(f"Authoritative games:      {len(auth)}")
        print(f"Resolved unique games:    {len(unique_resolved)}")
        print(f"Missing real games:       {len(missing)}")
        print(f"Unresolved raw rows:      {len(unresolved)}")

        for week, pkey, skey in missing:
            a = auth[
                (auth["week"] == week)
                & (auth["pair_key"] == pkey)
                & (auth["score_key"] == skey)
            ].iloc[0]

            print()
            print(
                f"MISSING — Week {week}: "
                f"{a['team_a']} {a['score_a']:.2f} vs "
                f"{a['team_b']} {a['score_b']:.2f}"
            )
            print(f"Score key: {skey}")

            same_week = raw[raw["week"] == week].copy()
            same_score = same_week[
                same_week.apply(
                    lambda r: score_key(
                        r["left_score"], r["right_score"]
                    ) == skey,
                    axis=1,
                )
            ]

            print("Raw rows with same score pair:")
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
                        ]
                    ].to_string(index=False)
                )

            print("All raw matchups in that week:")
            print(
                same_week[
                    [
                        "matchup_id",
                        "left_team",
                        "right_team",
                        "left_score",
                        "right_score",
                    ]
                ].to_string(index=False)
            )

        if unresolved:
            print()
            print("UNRESOLVED RAW ROWS:")
            for row in unresolved[:30]:
                print(
                    f"  Week {row['week']} | "
                    f"{row['left_team']} {row['left_score']} vs "
                    f"{row['right_team']} {row['right_score']}"
                )

    banner("NEXT")
    print(
        "Send me this terminal output. "
        "The repair script will then be adjusted only for the exact collision pattern found."
    )


if __name__ == "__main__":
    main()