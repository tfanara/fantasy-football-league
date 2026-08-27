from pathlib import Path
import re
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data" / "matchups" / "player_week_stats"
SEASONS = range(2019, 2024)

RECAP_RE = re.compile(r"^\s*Week\s+\d+\s+Recap\s+\((?:Won|Lost)\)\s*$", re.I)


def banner(text):
    print("\n" + "=" * 100)
    print(text)
    print("=" * 100)


def is_recap(value):
    return bool(RECAP_RE.match(str(value).strip()))


def score_key(a, b):
    try:
        vals = sorted([round(float(a), 2), round(float(b), 2)])
        return tuple(vals)
    except Exception:
        return None


def find_first(columns, candidates):
    lookup = {str(c).lower(): c for c in columns}
    for c in candidates:
        if c.lower() in lookup:
            return lookup[c.lower()]
    return None


def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def matchup_columns(df):
    return {
        "week": find_first(df.columns, ["week"]),
        "id": find_first(df.columns, ["matchup_id", "id"]),
        "left_team": find_first(df.columns, ["left_team", "team_1", "team1"]),
        "right_team": find_first(df.columns, ["right_team", "team_2", "team2"]),
        "left_score": find_first(df.columns, ["left_score", "team_1_score", "team1_score"]),
        "right_score": find_first(df.columns, ["right_score", "team_2_score", "team2_score"]),
    }


def require_matchup_columns(cols, df):
    missing = [k for k, v in cols.items() if k != "id" and v is None]
    if missing:
        raise KeyError(
            f"Missing required matchup fields {missing}. "
            f"Available columns: {list(df.columns)}"
        )


def lineup_columns(df):
    return {
        "week": find_first(df.columns, ["week"]),
        "matchup_id": find_first(df.columns, ["matchup_id"]),
        "team": find_first(df.columns, ["fantasy_team", "team", "team_name"]),
        "opponent": find_first(df.columns, ["opponent", "opponent_team"]),
        "player": find_first(df.columns, ["player", "player_name"]),
        "slot": find_first(df.columns, ["lineup_slot", "slot"]),
        "points": find_first(df.columns, ["fantasy_points", "points"]),
        "team_score": find_first(df.columns, ["team_score", "fantasy_team_score"]),
    }


def main():
    banner("HISTORICAL YAHOO RECAP-LABEL DIAGNOSTIC")
    print("Seasons: 2019-2023")
    print(f"Folder:  {DATA_DIR}")
    print("\nREAD-ONLY diagnostic: no source files will be modified.")

    season_summary = []
    all_recap_matchups = []
    all_recap_lineups = []
    all_score_pairs = []

    for year in SEASONS:
        matchup_path = DATA_DIR / f"{year}_matchups.csv"
        lineup_path = DATA_DIR / f"{year}_weekly_lineups.csv"

        banner(f"{year}")
        matchups = load_csv(matchup_path)
        lineups = load_csv(lineup_path)

        mc = matchup_columns(matchups)
        lc = lineup_columns(lineups)
        require_matchup_columns(mc, matchups)

        if lc["week"] is None or lc["team"] is None:
            raise KeyError(
                f"{year} lineup file does not contain required week/team columns. "
                f"Available columns: {list(lineups.columns)}"
            )

        left_recap = matchups[mc["left_team"]].map(is_recap)
        right_recap = matchups[mc["right_team"]].map(is_recap)
        recap_m = matchups[left_recap | right_recap].copy()

        team_recap = lineups[lc["team"]].map(is_recap)
        opp_recap = (
            lineups[lc["opponent"]].map(is_recap)
            if lc["opponent"] is not None
            else pd.Series(False, index=lineups.index)
        )
        recap_l = lineups[team_recap | opp_recap].copy()

        recap_weeks = sorted(
            set(recap_m[mc["week"]].dropna().astype(int).tolist())
            | set(recap_l[lc["week"]].dropna().astype(int).tolist())
        )

        real_matchup_teams = set(
            pd.concat([matchups[mc["left_team"]], matchups[mc["right_team"]]])
            .dropna().astype(str)
        )
        real_matchup_teams = sorted(t for t in real_matchup_teams if not is_recap(t))

        print(f"Matchup rows:              {len(matchups):,}")
        print(f"Lineup rows:               {len(lineups):,}")
        print(f"Recap-labeled matchups:    {len(recap_m):,}")
        print(f"Recap-involved lineup rows:{len(recap_l):,}")
        print(f"Affected weeks:            {recap_weeks}")
        print(f"Non-recap team names seen: {len(real_matchup_teams)}")

        season_summary.append({
            "year": year,
            "matchup_rows": len(matchups),
            "lineup_rows": len(lineups),
            "recap_matchup_rows": len(recap_m),
            "recap_lineup_rows": len(recap_l),
            "affected_weeks": ",".join(map(str, recap_weeks)),
            "non_recap_team_names_seen": len(real_matchup_teams),
        })

        if not recap_m.empty:
            out = recap_m.copy()
            if "year" not in out.columns:
                out.insert(0, "year", year)
            else:
                out["year"] = year
            out["_score_key"] = [
                score_key(a, b)
                for a, b in zip(out[mc["left_score"]], out[mc["right_score"]])
            ]
            all_recap_matchups.append(out)

        if not recap_l.empty:
            out = recap_l.copy()
            if "year" not in out.columns:
                out.insert(0, "year", year)
            else:
                out["year"] = year
            all_recap_lineups.append(out)

        # Find score pairs that appear more than once in the same week.
        tmp = matchups.copy()
        tmp["_score_key"] = [
            score_key(a, b)
            for a, b in zip(tmp[mc["left_score"]], tmp[mc["right_score"]])
        ]
        tmp["_year"] = year

        for (week, skey), grp in tmp.groupby([mc["week"], "_score_key"], dropna=False):
            if len(grp) > 1:
                for _, row in grp.iterrows():
                    all_score_pairs.append({
                        "year": year,
                        "week": week,
                        "matchup_id": row[mc["id"]] if mc["id"] else "",
                        "left_team": row[mc["left_team"]],
                        "right_team": row[mc["right_team"]],
                        "left_score": row[mc["left_score"]],
                        "right_score": row[mc["right_score"]],
                        "score_key": skey,
                        "views_with_same_score_pair": len(grp),
                        "contains_recap_label": (
                            is_recap(row[mc["left_team"]])
                            or is_recap(row[mc["right_team"]])
                        ),
                    })

        if recap_weeks:
            banner(f"{year} — AFFECTED WEEK DETAIL")
            for week in recap_weeks:
                wk = matchups[matchups[mc["week"]] == week].copy()
                print(f"\nWEEK {week} — {len(wk)} collected matchup rows")
                display_cols = [
                    c for c in [
                        mc["id"], mc["left_team"], mc["left_score"],
                        mc["right_team"], mc["right_score"]
                    ] if c is not None
                ]
                print(wk[display_cols].to_string(index=False))

    banner("CROSS-SEASON SUMMARY")
    summary = pd.DataFrame(season_summary)
    print(summary.to_string(index=False))

    diagnostic_dir = DATA_DIR / "analysis" / "recap_diagnostic"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)

    summary_path = diagnostic_dir / "historical_recap_summary_2019_2023.csv"
    summary.to_csv(summary_path, index=False)

    if all_recap_matchups:
        recap_matchups = pd.concat(all_recap_matchups, ignore_index=True)
    else:
        recap_matchups = pd.DataFrame()
    recap_matchups_path = diagnostic_dir / "historical_recap_matchups_2019_2023.csv"
    recap_matchups.to_csv(recap_matchups_path, index=False)

    if all_recap_lineups:
        recap_lineups = pd.concat(all_recap_lineups, ignore_index=True)
    else:
        recap_lineups = pd.DataFrame()
    recap_lineups_path = diagnostic_dir / "historical_recap_lineups_2019_2023.csv"
    recap_lineups.to_csv(recap_lineups_path, index=False)

    duplicate_scores = pd.DataFrame(all_score_pairs)
    duplicate_scores_path = diagnostic_dir / "historical_duplicate_score_views_2019_2023.csv"
    duplicate_scores.to_csv(duplicate_scores_path, index=False)

    banner("FILES CREATED")
    for p in [
        summary_path,
        recap_matchups_path,
        recap_lineups_path,
        duplicate_scores_path,
    ]:
        print(p)

    banner("NEXT")
    print(
        "Send me the terminal output from this script. "
        "Do not repair or overwrite any season files yet."
    )


if __name__ == "__main__":
    main()