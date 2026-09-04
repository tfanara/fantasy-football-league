"""
Central season/update-state configuration for the fantasy league project.

There are intentionally THREE different data horizons:

1. Draft-current
   A completed draft may be used immediately, even before games are played.

2. Weekly-current
   Standings, records, streaks, H2H, luck, bad beats, schedule swap,
   lineup efficiency, waiver value, stacks, positional edge, and other
   matchup/player-week analyses may include the current season THROUGH
   the latest structurally complete regular-season week.

3. Season-final
   Championship DNA, official Management Index season results, player
   championship pedigree, and other final-season outcome analyses may
   include the current season only after the season is marked complete.

Normal maintenance should require changing CURRENT_SEASON / phase only at
major season transitions. The latest completed weekly horizon is detected
from validated matchup data rather than typed manually each week.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


CURRENT_SEASON = 2026
CURRENT_SEASON_PHASE = "post_draft"

VALID_SEASON_PHASES = {
    "pre_draft",
    "post_draft",
    "in_season",
    "complete",
}

if CURRENT_SEASON_PHASE not in VALID_SEASON_PHASES:
    raise ValueError(
        f"Invalid CURRENT_SEASON_PHASE: {CURRENT_SEASON_PHASE!r}. "
        f"Expected one of {sorted(VALID_SEASON_PHASES)}."
    )


# -------------------------------------------------------------------
# STATIC / MAJOR-TRANSITION CUTOFFS
# -------------------------------------------------------------------

# Fully completed seasons only.
LAST_COMPLETED_SEASON = (
    CURRENT_SEASON
    if CURRENT_SEASON_PHASE == "complete"
    else CURRENT_SEASON - 1
)

# Draft-selection analysis can use the current season once the draft exists.
LAST_COMPLETED_DRAFT_SEASON = (
    CURRENT_SEASON
    if CURRENT_SEASON_PHASE in {"post_draft", "in_season", "complete"}
    else CURRENT_SEASON - 1
)


# Yahoo league IDs. 2017 is preserved for historical recovery; the normal
# authenticated Yahoo account history begins in 2018.
YAHOO_LEAGUE_IDS = {
    2017: "1121308",
    2018: "941496",
    2019: "322794",
    2020: "510142",
    2021: "410355",
    2022: "854563",
    2023: "684195",
    2024: "673480",
    2025: "637567",
    2026: "742546",
}

# Audited regular-season lengths. Add the next season here only after Yahoo's
# schedule format is confirmed for that season.
REGULAR_SEASON_END_WEEK = {
    2017: 13,
    2018: 13,
    2019: 13,
    2020: 13,
    2021: 14,
    2022: 14,
    2023: 14,
    2024: 14,
    2025: 14,
    2026: 14,
}

def regular_season_end_week(year: int) -> int:
    year = int(year)
    if year not in REGULAR_SEASON_END_WEEK:
        raise KeyError(
            f"No audited regular-season end week configured for {year}."
        )
    return REGULAR_SEASON_END_WEEK[year]


# -------------------------------------------------------------------
# WEEKLY-CURRENT STATE
# -------------------------------------------------------------------

@dataclass(frozen=True)
class WeeklyState:
    current_season: int
    latest_completed_week: int
    completed_games_current_season: int
    completed_team_weeks_current_season: int

    @property
    def has_current_season_results(self) -> bool:
        return self.latest_completed_week > 0


def _truthy_playoff_mask(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes", "y"})
    )


def detect_latest_completed_week(
    matchups: pd.DataFrame,
    *,
    year_col: str = "year",
    week_col: str = "week",
    team_1_col: str = "team_1",
    team_2_col: str = "team_2",
    score_1_col: str = "team_1_score",
    score_2_col: str = "team_2_score",
    playoff_col: Optional[str] = "is_playoffs",
    expected_teams: int = 12,
    expected_games: int = 6,
) -> WeeklyState:
    """
    Detect the latest STRUCTURALLY COMPLETE current-season regular-season week.

    A week counts only when it has:
      - exactly expected_games matchup rows,
      - exactly expected_teams unique teams,
      - both team scores present for every matchup.

    Weeks must be contiguous from Week 1. If Week 1-4 are complete but
    Week 5 is incomplete, the weekly horizon is Week 4 even if stray Week 6
    rows already exist.
    """
    required = {
        year_col,
        week_col,
        team_1_col,
        team_2_col,
        score_1_col,
        score_2_col,
    }
    missing = required - set(matchups.columns)
    if missing:
        raise KeyError(
            "Cannot detect completed week; missing matchup columns: "
            + ", ".join(sorted(missing))
        )

    df = matchups.copy()

    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    df[week_col] = pd.to_numeric(df[week_col], errors="coerce")
    df[score_1_col] = pd.to_numeric(df[score_1_col], errors="coerce")
    df[score_2_col] = pd.to_numeric(df[score_2_col], errors="coerce")

    df = df[df[year_col] == CURRENT_SEASON].copy()

    if playoff_col and playoff_col in df.columns:
        df = df[~_truthy_playoff_mask(df[playoff_col])].copy()

    if df.empty:
        return WeeklyState(
            current_season=CURRENT_SEASON,
            latest_completed_week=0,
            completed_games_current_season=0,
            completed_team_weeks_current_season=0,
        )

    completed_weeks = []

    for week in sorted(
        int(w)
        for w in df[week_col].dropna().unique()
        if int(w) >= 1
    ):
        g = df[df[week_col] == week].copy()

        teams = pd.concat(
            [
                g[team_1_col].astype(str),
                g[team_2_col].astype(str),
            ],
            ignore_index=True,
        )

        complete = (
            len(g) == expected_games
            and teams.nunique() == expected_teams
            and g[score_1_col].notna().all()
            and g[score_2_col].notna().all()
        )

        if complete:
            completed_weeks.append(week)

    latest_contiguous = 0
    for expected_week in range(1, max(completed_weeks, default=0) + 1):
        if expected_week not in completed_weeks:
            break
        latest_contiguous = expected_week

    completed_games = int(
        len(
            df[
                pd.to_numeric(df[week_col], errors="coerce")
                .between(1, latest_contiguous)
            ]
        )
    ) if latest_contiguous else 0

    return WeeklyState(
        current_season=CURRENT_SEASON,
        latest_completed_week=latest_contiguous,
        completed_games_current_season=completed_games,
        completed_team_weeks_current_season=completed_games * 2,
    )


def filter_weekly_current_matchups(
    matchups: pd.DataFrame,
    *,
    weekly_state: Optional[WeeklyState] = None,
    year_col: str = "year",
    week_col: str = "week",
    playoff_col: Optional[str] = "is_playoffs",
) -> pd.DataFrame:
    """
    Return the authoritative REGULAR-SEASON matchup universe for weekly-current
    analytics:

      - every row through LAST_COMPLETED_SEASON
      - plus CURRENT_SEASON Weeks 1..latest_completed_week

    Future/incomplete current-season weeks are excluded automatically.
    """
    df = matchups.copy()
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    df[week_col] = pd.to_numeric(df[week_col], errors="coerce")

    if df[year_col].isna().any():
        raise RuntimeError("Weekly matchup input contains invalid year values.")

    if playoff_col and playoff_col in df.columns:
        df = df[~_truthy_playoff_mask(df[playoff_col])].copy()

    if weekly_state is None:
        weekly_state = detect_latest_completed_week(
            df,
            year_col=year_col,
            week_col=week_col,
            playoff_col=playoff_col,
        )

    historical = df[df[year_col] <= LAST_COMPLETED_SEASON].copy()

    current = df[
        (df[year_col] == CURRENT_SEASON)
        & (df[week_col] >= 1)
        & (df[week_col] <= weekly_state.latest_completed_week)
    ].copy()

    out = pd.concat([historical, current], ignore_index=True)

    if (out[year_col] > CURRENT_SEASON).any():
        raise RuntimeError("Future season leaked into weekly-current matchup data.")

    if (
        (out[year_col] == CURRENT_SEASON)
        & (out[week_col] > weekly_state.latest_completed_week)
    ).any():
        raise RuntimeError(
            "Incomplete current-season week leaked into weekly-current matchup data."
        )

    return out


# -------------------------------------------------------------------
# HORIZON HELPERS
# -------------------------------------------------------------------

def outcome_analysis_through_year() -> int:
    """Latest FULL season allowed in season-final outcome analysis."""
    return LAST_COMPLETED_SEASON


def draft_analysis_through_year() -> int:
    """Latest season allowed in completed-draft analysis."""
    return LAST_COMPLETED_DRAFT_SEASON


def season_is_complete(year: int) -> bool:
    return int(year) <= LAST_COMPLETED_SEASON


def draft_is_complete(year: int) -> bool:
    return int(year) <= LAST_COMPLETED_DRAFT_SEASON


def season_status_label() -> str:
    labels = {
        "pre_draft": "Pre-Draft",
        "post_draft": "Draft Complete / Season Not Started",
        "in_season": "Season In Progress",
        "complete": "Season Complete",
    }
    return labels[CURRENT_SEASON_PHASE]


def print_season_config(
    weekly_state: Optional[WeeklyState] = None,
) -> None:
    base = (
        f"Season config: current={CURRENT_SEASON}, "
        f"phase={CURRENT_SEASON_PHASE}, "
        f"season_final_through={LAST_COMPLETED_SEASON}, "
        f"drafts_through={LAST_COMPLETED_DRAFT_SEASON}"
    )

    if weekly_state is None:
        print(base)
        return

    print(
        base
        + f", weekly_through="
        + (
            f"{CURRENT_SEASON} W{weekly_state.latest_completed_week}"
            if weekly_state.latest_completed_week
            else f"{LAST_COMPLETED_SEASON} final"
        )
    )