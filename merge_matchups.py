from pathlib import Path
import json

import pandas as pd
from pandas.errors import EmptyDataError

from season_config import (
    CURRENT_SEASON,
    REGULAR_SEASON_END_WEEK,
    detect_latest_completed_week,
    filter_weekly_current_matchups,
    print_season_config,
)

DATA_DIR = Path("data")
FROZEN_END_YEAR = 2025
FROZEN_BASE = DATA_DIR / "all_matchups_clean_2017_2025.csv"
TEAMS = 12
MATCHUPS_PER_WEEK = TEAMS // 2
EXPECTED_FROZEN_GAMES = 732


def fail(message: str):
    raise RuntimeError(message)


def load_csv_if_valid(path: Path):
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        df = pd.read_csv(path)
    except EmptyDataError:
        return None
    return None if df.empty else df


def matchup_key(df: pd.DataFrame) -> pd.Series:
    return df.apply(
        lambda r: (
            f"{int(r['year'])}-{int(r['week'])}-"
            f"{'|'.join(sorted([str(r['team_1']).strip(), str(r['team_2']).strip()]))}"
        ),
        axis=1,
    )


def validate_frozen_base(df: pd.DataFrame):
    required = {"year", "week", "team_1", "team_2", "team_1_score", "team_2_score"}
    missing = required - set(df.columns)
    if missing:
        fail(f"Frozen historical master missing columns: {sorted(missing)}")

    work = df.copy()
    work["year"] = pd.to_numeric(work["year"], errors="raise").astype(int)
    work["week"] = pd.to_numeric(work["week"], errors="raise").astype(int)

    if len(work) != EXPECTED_FROZEN_GAMES:
        fail(f"Frozen 2017-2025 master has {len(work)} games; expected 732.")
    if int(work["year"].min()) != 2017 or int(work["year"].max()) != 2025:
        fail("Frozen master must cover exactly 2017-2025.")

    for year in range(2017, 2026):
        expected_weeks = REGULAR_SEASON_END_WEEK[year]
        season = work[work["year"] == year]
        expected_games = expected_weeks * MATCHUPS_PER_WEEK
        if len(season) != expected_games:
            fail(f"Frozen {year}: found {len(season)} games; expected {expected_games}.")
        counts = season.groupby("week").size()
        teams = pd.concat([season["team_1"], season["team_2"]]).astype(str).str.strip().nunique()
        if teams != TEAMS:
            fail(f"Frozen {year}: found {teams} unique teams; expected 12.")
        for week in range(1, expected_weeks + 1):
            if int(counts.get(week, 0)) != MATCHUPS_PER_WEEK:
                fail(f"Frozen {year} Week {week}: expected 6 games; found {int(counts.get(week, 0))}.")

    if matchup_key(work).duplicated().any():
        fail("Frozen historical master contains duplicate matchup keys.")

    print("[PASS] Frozen 2017-2025 master: 732 games / 122 complete weeks")


def prepare_current_season() -> pd.DataFrame | None:
    year = CURRENT_SEASON
    year_dir = DATA_DIR / str(year)
    frames = []
    for path in [
        year_dir / "matchups.csv",
        year_dir / "matchups_manual.csv",
        year_dir / "matchups_week14.csv",
    ]:
        df = load_csv_if_valid(path)
        if df is not None:
            print(f"Loading current-season source: {path} ({len(df)} rows)")
            frames.append(df)

    if not frames:
        return None

    df = pd.concat(frames, ignore_index=True, sort=False)

    # Normalize the two legitimate Yahoo-era score naming conventions.
    rename = {}
    if "team_1_score" not in df.columns and "score_1" in df.columns:
        rename["score_1"] = "team_1_score"
    if "team_2_score" not in df.columns and "score_2" in df.columns:
        rename["score_2"] = "team_2_score"
    if "team_1_projected" not in df.columns and "projected_1" in df.columns:
        rename["projected_1"] = "team_1_projected"
    if "team_2_projected" not in df.columns and "projected_2" in df.columns:
        rename["projected_2"] = "team_2_projected"
    if rename:
        df = df.rename(columns=rename)

    required = {"year", "week", "team_1", "team_2", "team_1_score", "team_2_score"}
    missing = required - set(df.columns)
    if missing:
        fail(f"{year} matchup data missing columns: {sorted(missing)}")

    for col in ["year", "week", "team_1_score", "team_2_score"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=list(required)).copy()
    df["year"] = df["year"].astype(int)
    df["week"] = df["week"].astype(int)
    df = df[df["year"] == year].copy()
    df = df[df["week"].between(1, REGULAR_SEASON_END_WEEK[year])].copy()

    df["matchup_key"] = matchup_key(df)
    df = df.drop_duplicates("matchup_key", keep="last").drop(columns="matchup_key")
    return df.sort_values(["week", "team_1"], kind="stable").reset_index(drop=True)


def align_current_columns(current: pd.DataFrame, frozen_columns: list[str]) -> pd.DataFrame:
    out = current.copy()
    for col in frozen_columns:
        if col not in out.columns:
            out[col] = pd.NA
    # Preserve the audited canonical schema. Collector-only extras stay in the
    # season source file and do not silently alter the historical master schema.
    return out[frozen_columns].copy()


def save_json(df: pd.DataFrame, path: Path):
    with open(path, "w") as f:
        json.dump(df.where(pd.notna(df), None).to_dict(orient="records"), f, indent=2)


def main():
    print("=" * 80)
    print("BUILDING WEEKLY-CURRENT MATCHUP MASTER")
    print("=" * 80)
    print_season_config()

    if not FROZEN_BASE.exists():
        fail(f"Missing frozen authoritative history: {FROZEN_BASE}")

    frozen = pd.read_csv(FROZEN_BASE)
    validate_frozen_base(frozen)

    current_raw = prepare_current_season()
    if current_raw is None:
        print(f"{CURRENT_SEASON}: no matchup source yet; historical master remains unchanged.")
        combined = frozen.copy()
        state = detect_latest_completed_week(combined)
    else:
        state = detect_latest_completed_week(current_raw)
        current_complete = filter_weekly_current_matchups(current_raw, weekly_state=state)
        current_complete = current_complete[current_complete["year"] == CURRENT_SEASON].copy()
        current_complete = align_current_columns(current_complete, list(frozen.columns))
        combined = pd.concat([frozen, current_complete], ignore_index=True, sort=False)

    # Regression: the historical portion must remain row-for-row identical.
    historical_out = combined[combined["year"].between(2017, FROZEN_END_YEAR)].reset_index(drop=True)
    frozen_reset = frozen.reset_index(drop=True)
    try:
        pd.testing.assert_frame_equal(historical_out, frozen_reset, check_dtype=False)
    except AssertionError as exc:
        fail(f"Frozen 2017-2025 history changed during merge: {exc}")

    current_rows = combined[combined["year"] == CURRENT_SEASON]
    expected_current = state.latest_completed_week * MATCHUPS_PER_WEEK
    if len(current_rows) != expected_current:
        fail(
            f"{CURRENT_SEASON}: master contains {len(current_rows)} current-season games; "
            f"expected {expected_current} through Week {state.latest_completed_week}."
        )

    combined = combined.sort_values(["year", "week", "team_1"], kind="stable").reset_index(drop=True)

    canonical_csv = DATA_DIR / "all_matchups_clean.csv"
    canonical_json = DATA_DIR / "all_matchups_clean.json"
    snapshot_csv = DATA_DIR / f"all_matchups_clean_2017_{CURRENT_SEASON}.csv"
    snapshot_json = DATA_DIR / f"all_matchups_clean_2017_{CURRENT_SEASON}.json"

    combined.to_csv(canonical_csv, index=False)
    save_json(combined, canonical_json)
    combined.to_csv(snapshot_csv, index=False)
    save_json(combined, snapshot_json)

    print(f"[PASS] Frozen history preserved exactly: {len(frozen)} games")
    print(f"[PASS] {CURRENT_SEASON} completed games included: {len(current_rows)}")
    print(f"[PASS] Canonical matchup master: {len(combined)} games")
    print_season_config(state)
    print(f"Saved: {canonical_csv}")
    print(f"Saved: {snapshot_csv}")


if __name__ == "__main__":
    main()
