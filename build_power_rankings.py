from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
ANALYSIS_DIR = BASE_DIR / "data" / "matchups" / "player_week_stats" / "analysis"
LUCK_FILE = ANALYSIS_DIR / "luck_team_week.csv"
EFFICIENCY_FILE = ANALYSIS_DIR / "lineup_efficiency_team_week.csv"
OUTPUT_DIR = BASE_DIR / "data" / "analysis"
WEEKLY_OUT = OUTPUT_DIR / "power_rankings_weekly.csv"
CURRENT_OUT = OUTPUT_DIR / "power_rankings_current.csv"

RECENT_WEEKS = 3
WEIGHT_SCORING = 0.40
WEIGHT_ALL_PLAY = 0.35
WEIGHT_EFFICIENCY = 0.15
WEIGHT_RESULTS = 0.10

FRANCHISE_ALIASES = {
    "PickUpYourBratsMalle": "ThreatLevelMidnight",
    "Little Red Fournette": "Post Mahomes",
    "Ur The Best Bellows": "Joe Mantegna",
    "You Better Park It": "Buttermilk Puuump",
    "Buttermilk Pump": "Buttermilk Puuump",
}

def normalize_name(v):
    if pd.isna(v):
        return v
    v = str(v).strip()
    return FRANCHISE_ALIASES.get(v, v)

def normalize(df):
    out = df.copy()
    for c in ["team", "fantasy_team", "opponent"]:
        if c in out.columns:
            out[c] = out[c].map(normalize_name)
    return out

def numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

def strength(s):
    s = pd.to_numeric(s, errors="coerce")
    if s.notna().sum() <= 1:
        return pd.Series(50.0, index=s.index)
    return s.rank(method="average", pct=True) * 100

def rank_desc(s):
    return pd.to_numeric(s, errors="coerce").rank(
        method="min", ascending=False
    ).astype("Int64")

def completed_weeks(luck, year):
    s = luck[luck.year.eq(year)]
    counts = s.groupby("week")["fantasy_team"].nunique()
    return sorted(int(w) for w, n in counts.items() if int(n) == 12)

def build_snapshot(luck, efficiency, year, week):
    s = luck[(luck.year == year) & (luck.week <= week)].copy()
    recent_start = max(1, week - RECENT_WEEKS + 1)
    r = s[s.week >= recent_start].copy()

    w = s.groupby("fantasy_team", as_index=False).agg(
        games=("week", "count"),
        wins=("actual_win", "sum"),
        losses=("actual_loss", "sum"),
        ties=("actual_tie", "sum"),
        actual_win_value=("actual_win_value", "sum"),
        points_for=("team_score", "sum"),
        avg_points=("team_score", "mean"),
        all_play_wins=("all_play_wins", "sum"),
        all_play_losses=("all_play_losses", "sum"),
        all_play_ties=("all_play_ties", "sum"),
        expected_wins=("expected_win_value", "sum"),
        schedule_luck=("weekly_schedule_luck", "sum"),
    )
    w["actual_win_pct"] = w.actual_win_value / w.games
    apg = w.all_play_wins + w.all_play_losses + w.all_play_ties
    w["all_play_pct"] = (
        w.all_play_wins + 0.5 * w.all_play_ties
    ) / apg

    rr = r.groupby("fantasy_team", as_index=False).agg(
        recent_games=("week", "count"),
        recent_avg_points=("team_score", "mean"),
        recent_all_play_wins=("all_play_wins", "sum"),
        recent_all_play_losses=("all_play_losses", "sum"),
        recent_all_play_ties=("all_play_ties", "sum"),
    )
    rapg = (
        rr.recent_all_play_wins
        + rr.recent_all_play_losses
        + rr.recent_all_play_ties
    )
    rr["recent_all_play_pct"] = (
        rr.recent_all_play_wins + 0.5 * rr.recent_all_play_ties
    ) / rapg
    w = w.merge(
        rr[["fantasy_team", "recent_games", "recent_avg_points",
            "recent_all_play_pct"]],
        on="fantasy_team", how="left"
    )

    e = efficiency[
        (efficiency.year == year) & (efficiency.week <= week)
    ]
    if not e.empty:
        ee = e.groupby("fantasy_team", as_index=False).agg(
            lineup_efficiency_pct=("lineup_efficiency_pct", "mean"),
            points_left_on_bench=("points_left_on_bench", "sum"),
        )
        w = w.merge(ee, on="fantasy_team", how="left")
    else:
        w["lineup_efficiency_pct"] = np.nan
        w["points_left_on_bench"] = np.nan

    # Missing efficiency is neutral, not rewarded or punished.
    median_eff = w["lineup_efficiency_pct"].median()
    w["lineup_efficiency_pct"] = w["lineup_efficiency_pct"].fillna(
        median_eff if pd.notna(median_eff) else 50.0
    )

    w["season_scoring_strength"] = strength(w.avg_points)
    w["recent_scoring_strength"] = strength(w.recent_avg_points)
    w["season_all_play_strength"] = strength(w.all_play_pct)
    w["recent_all_play_strength"] = strength(w.recent_all_play_pct)

    if week <= RECENT_WEEKS:
        w["scoring_strength"] = w.season_scoring_strength
        w["all_play_strength"] = w.season_all_play_strength
    else:
        w["scoring_strength"] = (
            0.70 * w.season_scoring_strength
            + 0.30 * w.recent_scoring_strength
        )
        w["all_play_strength"] = (
            0.70 * w.season_all_play_strength
            + 0.30 * w.recent_all_play_strength
        )

    w["efficiency_strength"] = strength(w.lineup_efficiency_pct)
    w["results_strength"] = strength(w.actual_win_pct)
    w["power_score"] = (
        WEIGHT_SCORING * w.scoring_strength
        + WEIGHT_ALL_PLAY * w.all_play_strength
        + WEIGHT_EFFICIENCY * w.efficiency_strength
        + WEIGHT_RESULTS * w.results_strength
    )
    w["power_rank"] = rank_desc(w.power_score)
    w["scoring_rank"] = rank_desc(w.avg_points)
    w["all_play_rank"] = rank_desc(w.all_play_pct)
    w["efficiency_rank"] = rank_desc(w.lineup_efficiency_pct)
    w["record"] = w.apply(
        lambda x: f"{int(x.wins)}-{int(x.losses)}-{int(x.ties)}", axis=1
    )
    w.insert(0, "year", int(year))
    w.insert(1, "through_week", int(week))
    return w.sort_values(["power_rank", "power_score"],
                         ascending=[True, False]).reset_index(drop=True)


def build_commentary(row):
    """Return one short, deterministic, evidence-based ranking blurb."""
    rank = int(row["power_rank"])
    scoring_rank = int(row["scoring_rank"])
    all_play_rank = int(row["all_play_rank"])
    efficiency_rank = int(row["efficiency_rank"])
    games = int(row["games"])
    wins = int(row["wins"])
    losses = int(row["losses"])
    avg_points = float(row["avg_points"])
    all_play_pct = float(row["all_play_pct"])
    efficiency = float(row["lineup_efficiency_pct"])
    change = int(row.get("rank_change", 0) or 0)
    week = int(row["through_week"])

    # Rank movement becomes meaningful after the opening week.
    if week > 1 and change >= 3:
        return (
            f"Up {change} spots after a strong stretch; the underlying performance "
            f"is finally showing up in the rankings."
        )
    if week > 1 and change <= -3:
        return (
            f"Down {abs(change)} spots as the recent numbers cool off; this team "
            f"needs a response before the slide becomes a trend."
        )

    # Clear top-end profiles.
    if rank == 1 and scoring_rank == 1 and all_play_rank == 1:
        if efficiency_rank == 1:
            return (
                "No debate at the top: league-best scoring, dominant all-play "
                "performance, and flawless lineup execution."
            )
        return (
            "The league's strongest scoring and all-play profile earns the top spot."
        )
    if rank <= 3 and scoring_rank <= 3 and all_play_rank <= 3:
        return (
            f"An elite scoring profile ({avg_points:.2f} per week) and top-tier "
            "all-play results make this team an early heavyweight."
        )

    # Record versus underlying performance.
    if losses > wins and rank <= 6:
        return (
            f"The {wins}-{losses} record undersells the performance; the underlying "
            "numbers see a stronger team than the standings do."
        )
    if wins > losses and scoring_rank >= 9 and all_play_rank >= 9:
        beaten = round((1.0 - all_play_pct) * 11)
        if games == 1:
            return (
                f"The win counts, but roughly {beaten} of the other 11 teams would "
                "have beaten this Week 1 score."
            )
        return (
            "The record is doing more work than the underlying weekly performance; "
            "the power meter remains skeptical."
        )

    # Extreme lineup management.
    if efficiency_rank == 1:
        return (
            f"Elite lineup execution ({efficiency:.1f}%) is squeezing nearly every "
            "available point out of the roster."
        )
    if efficiency_rank >= 11:
        return (
            f"Lineup execution has been a drag at {efficiency:.1f}%; too much usable "
            "production is being left on the bench."
        )

    # Strong/weak scoring and all-play combinations.
    if scoring_rank <= 4 and all_play_rank <= 4:
        return (
            f"Scoring and all-play performance both sit in the league's top four; "
            "the profile looks legitimately strong."
        )
    if scoring_rank >= 10 and all_play_rank >= 10:
        return (
            f"Bottom-three scoring and all-play results leave very little for the "
            "power meter to defend."
        )

    # General middle-of-table fallback.
    if rank <= 6:
        return (
            "A solid underlying profile keeps this team in the upper half, with "
            "room to climb if the strongest indicators hold."
        )
    return (
        "The underlying profile remains uneven; stronger weekly production is "
        "needed to make a meaningful move up the board."
    )

def main():
    print("=" * 96)
    print("BUILDING FANTASY FOOTBALL POWER RANKINGS")
    print("=" * 96)
    for p in [LUCK_FILE, EFFICIENCY_FILE]:
        if not p.exists():
            raise FileNotFoundError(f"Required input file not found: {p}")

    luck = normalize(pd.read_csv(LUCK_FILE))
    eff = normalize(pd.read_csv(EFFICIENCY_FILE))
    numeric(luck, [
        "year", "week", "team_score", "actual_win", "actual_loss",
        "actual_tie", "actual_win_value", "all_play_wins",
        "all_play_losses", "all_play_ties", "expected_win_value",
        "weekly_schedule_luck"
    ])
    numeric(eff, [
        "year", "week", "lineup_efficiency_pct", "points_left_on_bench"
    ])

    print("\nFormula: 40% scoring + 35% all-play + "
          "15% lineup efficiency + 10% actual results")
    print("Recent form: 3-week window, blended 30% beginning Week 4")

    snapshots = []
    for year in sorted(int(x) for x in luck.year.dropna().unique()):
        for week in completed_weeks(luck, year):
            snap = build_snapshot(luck, eff, year, week)
            if len(snap) != 12 or snap.fantasy_team.nunique() != 12:
                raise RuntimeError(
                    f"{year} Week {week}: expected 12 unique teams; "
                    f"found {len(snap)} rows / {snap.fantasy_team.nunique()} teams"
                )
            snapshots.append(snap)

    weekly = pd.concat(snapshots, ignore_index=True)
    weekly = weekly.sort_values(
        ["year", "fantasy_team", "through_week"]
    )
    weekly["previous_rank"] = weekly.groupby(
        ["year", "fantasy_team"]
    )["power_rank"].shift(1)
    weekly["rank_change"] = weekly.previous_rank - weekly.power_rank
    weekly["rank_change"] = weekly.rank_change.fillna(0).astype("Int64")
    weekly["previous_rank"] = weekly.previous_rank.astype("Int64")
    weekly = weekly.sort_values(
        ["year", "through_week", "power_rank"]
    ).reset_index(drop=True)

    # Commentary is generated only after official rank and movement are final.
    weekly["commentary"] = weekly.apply(build_commentary, axis=1)

    if weekly.power_score.isna().any():
        raise RuntimeError("Missing Power Scores found.")
    if ((weekly.power_score < 0) | (weekly.power_score > 100)).any():
        raise RuntimeError("Power Score outside 0-100 found.")

    latest_year = int(weekly.year.max())
    latest_week = int(
        weekly.loc[weekly.year == latest_year, "through_week"].max()
    )
    current = weekly[
        (weekly.year == latest_year)
        & (weekly.through_week == latest_week)
    ].copy()

    # Yahoo standings are display-only and never affect Power Score.
    standings_file = BASE_DIR / "data" / str(latest_year) / "standings.csv"
    if standings_file.exists():
        ys = normalize(pd.read_csv(standings_file))
        ys = ys.rename(columns={
            "team": "fantasy_team",
            "rank": "yahoo_rank",
            "record": "yahoo_record",
            "points_for": "yahoo_points_for",
        })
        keep = [
            c for c in ["fantasy_team", "yahoo_rank",
                        "yahoo_record", "yahoo_points_for"]
            if c in ys.columns
        ]
        current = current.merge(
            ys[keep].drop_duplicates("fantasy_team"),
            on="fantasy_team", how="left"
        )

    round_cols = [
        "points_for", "avg_points", "actual_win_pct", "all_play_pct",
        "expected_wins", "schedule_luck", "recent_avg_points",
        "recent_all_play_pct", "lineup_efficiency_pct",
        "points_left_on_bench", "scoring_strength",
        "all_play_strength", "efficiency_strength",
        "results_strength", "power_score"
    ]
    for frame in [weekly, current]:
        for c in round_cols:
            if c in frame.columns:
                frame[c] = pd.to_numeric(
                    frame[c], errors="coerce"
                ).round(2)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    weekly.to_csv(WEEKLY_OUT, index=False)
    current.to_csv(CURRENT_OUT, index=False)

    print(f"\n[PASS] {len(weekly):,} ranking rows")
    print("[PASS] "
          f"{weekly[['year','through_week']].drop_duplicates().shape[0]:,} "
          "weekly snapshots")
    print(f"[PASS] Current snapshot: {latest_year} Week {latest_week}")

    cols = [
        "power_rank", "fantasy_team", "record", "power_score",
        "avg_points", "all_play_pct", "lineup_efficiency_pct",
        "scoring_rank", "all_play_rank", "efficiency_rank",
        "rank_change", "commentary"
    ]
    print("\n" + "=" * 96)
    print("CURRENT POWER RANKINGS")
    print("=" * 96)
    print(current[cols].to_string(index=False))

    print("\n" + "=" * 96)
    print("SAVING FILES")
    print("=" * 96)
    print(WEEKLY_OUT)
    print(CURRENT_OUT)
    print("\nPOWER RANKINGS BUILD COMPLETE")

if __name__ == "__main__":
    main()