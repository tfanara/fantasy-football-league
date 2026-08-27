from __future__ import annotations

from pathlib import Path

from collections import defaultdict

from itertools import combinations

import pandas as pd



# =============================================================================

# SETTINGS

# =============================================================================

START_YEAR = 2018

END_YEAR = 2025

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data" / "matchups" / "player_week_stats"

MASTER_LINEUPS_FILE = (

    DATA_DIR

    / f"all_weekly_lineups_{START_YEAR}_{END_YEAR}.csv"

)

OUTPUT_DIR = DATA_DIR / "analysis"

TEAM_WEEK_OUTPUT = OUTPUT_DIR / "lineup_efficiency_team_week.csv"

SEASON_OUTPUT = OUTPUT_DIR / "lineup_efficiency_season.csv"

ALL_TIME_OUTPUT = OUTPUT_DIR / "lineup_efficiency_all_time.csv"

DECISIONS_OUTPUT = OUTPUT_DIR / "lineup_efficiency_decisions.csv"



# =============================================================================

# LINEUP RULES

# =============================================================================

#

# Validated historical starting lineup:

# QB, WR, WR, RB, RB, TE, W/R/T, K, DEF

#

# W/R/T may be filled by WR, RB, or TE.

#

FIXED_SLOT_REQUIREMENTS = {

    "QB": 1,

    "WR": 2,

    "RB": 2,

    "TE": 1,

    "K": 1,

    "DEF": 1,

}

FLEX_SLOT = "W/R/T"

FLEX_ELIGIBLE = {"WR", "RB", "TE"}



# =============================================================================

# HELPERS

# =============================================================================

def banner(title: str):

    print()

    print("=" * 96)

    print(title)

    print("=" * 96)



def normalize_bool(series: pd.Series) -> pd.Series:

    if series.dtype == bool:

        return series

    return (

        series.astype(str)

        .str.strip()

        .str.lower()

        .map(

            {

                "true": True,

                "false": False,

                "1": True,

                "0": False,

            }

        )

        .fillna(False)

        .astype(bool)

    )



def normalize_position(value) -> str:

    """

    Normalize Yahoo position text.

    Historical Yahoo rows may contain values such as:

        "NE - QB"

        "Min - WR"

        "DEF"

        "D/ST"

    Return only the fantasy position token.

    """

    if pd.isna(value):

        return ""

    text = str(value).strip().upper()

    if not text:

        return ""

    if text in {"DST", "D/ST"}:

        return "DEF"

    # Direct clean position.

    if text in {"QB", "WR", "RB", "TE", "K", "DEF"}:

        return text

    # Extract the final recognizable Yahoo fantasy position token.

    import re

    match = re.search(

        r"(?:^|[\s**\-**/,])"

        r"(QB|WR|RB|TE|K|DEF|DST|D/ST)"

        r"(?:$|[\s,;/])",

        text,

    )

    if match:

        pos = match.group(1)

        if pos in {"DST", "D/ST"}:

            return "DEF"

        return pos

    return ""



def scoring_value(value) -> float:

    """

    Missing fantasy points are treated as 0.00.

    This is consistent with the validated historical data where blank starter

    values still reconcile exactly to Yahoo team totals.

    """

    if pd.isna(value):

        return 0.0

    return float(value)



def player_label(row: pd.Series) -> str:

    player = str(row.get("player", "")).strip()

    pos = str(row.get("player_position", "")).strip()

    if pos:

        return f"{player} ({pos})"

    return player



def build_historical_position_lookup(df: pd.DataFrame) -> dict[str, str]:

    """

    Build a player -> position lookup from fixed starting slots across the full

    2018-2025 history.

    Bench rows often only say BN, but the same player usually appears in a

    fixed starting slot (QB/RB/WR/TE/K/DEF) in another week. We use those

    fixed-slot appearances as the authoritative position source.

    """

    fixed_positions = {

        "QB",

        "WR",

        "RB",

        "TE",

        "K",

        "DEF",

    }

    rows = []

    for _, row in df.iterrows():

        player = str(

            row.get("player", "")

        ).strip()

        if not player or player == "(Empty)":

            continue

        slot = normalize_position(

            row.get("lineup_slot")

        )

        if slot in fixed_positions:

            rows.append(

                {

                    "player": player,

                    "position": slot,

                }

            )

    if not rows:

        return {}

    fixed_df = pd.DataFrame(rows)

    counts = (

        fixed_df.groupby(

            [

                "player",

                "position",

            ]

        )

        .size()

        .reset_index(

            name="appearances"

        )

    )

    counts = counts.sort_values(

        [

            "player",

            "appearances",

            "position",

        ],

        ascending=[

            True,

            False,

            True,

        ],

    )

    best = counts.drop_duplicates(

        subset=["player"],

        keep="first",

    )

    return dict(

        zip(

            best["player"],

            best["position"],

        )

    )



def infer_player_position(

    row: pd.Series,

    historical_lookup: dict[str, str] | None = None,

) -> str:

    """

    Determine a player's fantasy position.

    Priority:

      1. Explicit player/raw Yahoo position fields.

      2. Historical fixed-slot lookup for this player.

      3. This row's own fixed lineup slot.

    Bench rows usually have lineup_slot == BN, so the historical lookup is the

    key fallback for old Yahoo seasons.

    """

    for field in [

        "player_position",

        "raw_position",

        "raw_player_text",

        "raw_cells",

    ]:

        pos = normalize_position(

            row.get(field)

        )

        if pos:

            return pos

    player = str(

        row.get("player", "")

    ).strip()

    if (

        historical_lookup

        and player

        and player in historical_lookup

    ):

        return historical_lookup[

            player

        ]

    slot = normalize_position(

        row.get("lineup_slot")

    )

    if slot in {

        "QB",

        "WR",

        "RB",

        "TE",

        "K",

        "DEF",

    }:

        return slot

    return ""



def eligible_for_slot(

    position: str,

    slot: str,

) -> bool:

    if slot == FLEX_SLOT:

        return position in FLEX_ELIGIBLE

    return position == slot



def build_optimal_lineup(

    roster: pd.DataFrame,

    historical_lookup: dict[str, str],

) -> tuple[pd.DataFrame, float]:

    """

    Find the best legal 9-player lineup.

    Brute-force is feasible because fantasy rosters are small. We enumerate

    candidate players by slot eligibility and search combinations for the

    fixed positional counts + one flex.

    """

    roster = roster.copy()

    roster["opt_position"] = roster.apply(

        lambda row: infer_player_position(

            row,

            historical_lookup,

        ),

        axis=1,

    )

    roster["opt_points"] = roster[

        "fantasy_points"

    ].apply(

        scoring_value

    )

    # Exclude empty roster placeholders.

    roster = roster[

        ~roster["player"]

        .astype(str)

        .str.strip()

        .eq("(Empty)")

    ].copy()

    # Exclude rows with no usable positional information.

    roster = roster[

        roster["opt_position"].ne("")

    ].copy()

    # Candidate lists by fixed slot.

    candidates = {

        slot: roster[

            roster["opt_position"].eq(slot)

        ].index.tolist()

        for slot in FIXED_SLOT_REQUIREMENTS

    }

    # Defensive checks.

    for slot, needed in FIXED_SLOT_REQUIREMENTS.items():

        if len(candidates[slot]) < needed:

            raise RuntimeError(

                f"Not enough eligible {slot} players to build a legal lineup."

            )

    best_indices = None

    best_score = float("-inf")

    qb_combos = combinations(

        candidates["QB"],

        FIXED_SLOT_REQUIREMENTS["QB"],

    )

    for qb in qb_combos:

        for wr in combinations(

            candidates["WR"],

            FIXED_SLOT_REQUIREMENTS["WR"],

        ):

            for rb in combinations(

                candidates["RB"],

                FIXED_SLOT_REQUIREMENTS["RB"],

            ):

                for te in combinations(

                    candidates["TE"],

                    FIXED_SLOT_REQUIREMENTS["TE"],

                ):

                    for k in combinations(

                        candidates["K"],

                        FIXED_SLOT_REQUIREMENTS["K"],

                    ):

                        for deff in combinations(

                            candidates["DEF"],

                            FIXED_SLOT_REQUIREMENTS["DEF"],

                        ):

                            fixed = set(

                                qb

                                + wr

                                + rb

                                + te

                                + k

                                + deff

                            )

                            flex_candidates = roster[

                                roster.index.map(

                                    lambda idx: (

                                        idx not in fixed

                                        and roster.at[

                                            idx,

                                            "opt_position",

                                        ]

                                        in FLEX_ELIGIBLE

                                    )

                                )

                            ]

                            if flex_candidates.empty:

                                continue

                            flex_idx = (

                                flex_candidates[

                                    "opt_points"

                                ]

                                .idxmax()

                            )

                            lineup_indices = list(

                                fixed

                            ) + [flex_idx]

                            score = float(

                                roster.loc[

                                    lineup_indices,

                                    "opt_points",

                                ].sum()

                            )

                            if score > best_score:

                                best_score = score

                                best_indices = lineup_indices

    if best_indices is None:

        raise RuntimeError(

            "Could not build a legal optimal lineup."

        )

    optimal = roster.loc[

        best_indices

    ].copy()

    return optimal, best_score



def build_decision_rows(

    team_week: pd.DataFrame,

    optimal: pd.DataFrame,

    year: int,

    week: int,

    team: str,

    opponent: str,

) -> list[dict]:

    """

    Compare actual starters to optimal starters.

    This identifies players who should have been benched and players who

    should have started. It does not force artificial one-to-one positional

    pairing when several equivalent swaps are possible.

    """

    actual_starters = team_week[

        team_week["is_starter"]

    ].copy()

    actual_keys = set(

        actual_starters.index

    )

    optimal_keys = set(

        optimal.index

    )

    should_bench = actual_starters[

        actual_starters.index.isin(

            actual_keys - optimal_keys

        )

    ].copy()

    should_start = optimal[

        optimal.index.isin(

            optimal_keys - actual_keys

        )

    ].copy()

    rows = []

    for _, row in should_bench.iterrows():

        rows.append(

            {

                "year": year,

                "week": week,

                "fantasy_team": team,

                "opponent": opponent,

                "decision_type": "Should Have Benched",

                "player": row["player"],

                "player_position": row.get(

                    "player_position",

                    "",

                ),

                "lineup_slot": row.get(

                    "lineup_slot",

                    "",

                ),

                "fantasy_points": scoring_value(

                    row["fantasy_points"]

                ),

            }

        )

    for _, row in should_start.iterrows():

        rows.append(

            {

                "year": year,

                "week": week,

                "fantasy_team": team,

                "opponent": opponent,

                "decision_type": "Should Have Started",

                "player": row["player"],

                "player_position": row.get(

                    "player_position",

                    "",

                ),

                "lineup_slot": row.get(

                    "lineup_slot",

                    "",

                ),

                "fantasy_points": scoring_value(

                    row["fantasy_points"]

                ),

            }

        )

    return rows



# =============================================================================

# MAIN

# =============================================================================

def main():

    banner("BUILDING LINEUP EFFICIENCY ANALYSIS")

    if not MASTER_LINEUPS_FILE.exists():

        raise FileNotFoundError(

            f"Missing master lineup file: {MASTER_LINEUPS_FILE}"

        )

    df = pd.read_csv(

        MASTER_LINEUPS_FILE

    )

    required = {

        "year",

        "week",

        "fantasy_team",

        "opponent",

        "player",

        "lineup_slot",

        "fantasy_points",

        "is_starter",

        "is_bench",

        "is_ir",

    }

    missing = required - set(df.columns)

    if missing:

        raise KeyError(

            f"Missing required columns: {sorted(missing)}"

        )

    for col in [

        "is_starter",

        "is_bench",

        "is_ir",

    ]:

        df[col] = normalize_bool(

            df[col]

        )

    for col in [

        "year",

        "week",

        "fantasy_points",

        "team_score",

        "opponent_score",

    ]:

        if col in df.columns:

            df[col] = pd.to_numeric(

                df[col],

                errors="coerce",

            )

    historical_position_lookup = (

        build_historical_position_lookup(

            df

        )

    )

    print(

        f"Historical player-position lookup: "

        f"{len(historical_position_lookup):,} players"

    )

    df["player_position"] = df.apply(

        lambda row: infer_player_position(

            row,

            historical_position_lookup,

        ),

        axis=1,

    )

    OUTPUT_DIR.mkdir(

        parents=True,

        exist_ok=True,

    )

    banner("POSITION PARSING CHECK")

    parsed_position_counts = (

        df["player_position"]

        .replace("", pd.NA)

        .value_counts(dropna=False)

    )

    print(

        parsed_position_counts.to_string()

    )

    unresolved_position_rows = df[

        df["player_position"].eq("")

        & ~df["player"].astype(str).str.strip().eq("(Empty)")

        & ~df["is_ir"]

    ]

    print()

    print(

        f"Rows without a usable position: "

        f"{len(unresolved_position_rows):,}"

    )

    if not unresolved_position_rows.empty:

        print()

        print(

            unresolved_position_rows[

                [

                    c for c in [

                        "year",

                        "week",

                        "fantasy_team",

                        "lineup_slot",

                        "player",

                        "raw_position",

                        "raw_player_text",

                    ]

                    if c in unresolved_position_rows.columns

                ]

            ]

            .head(30)

            .to_string(index=False)

        )

    team_week_rows = []

    decision_rows = []

    skipped = []

    grouped = df.groupby(

        [

            "year",

            "week",

            "fantasy_team",

        ],

        sort=True,

    )

    banner("CALCULATING TEAM-WEEK EFFICIENCY")

    for (

        year,

        week,

        team,

    ), team_week in grouped:

        team_week = team_week.copy()

        opponent = (

            team_week["opponent"]

            .dropna()

            .astype(str)

            .iloc[0]

        )

        actual_starters = team_week[

            team_week["is_starter"]

        ].copy()

        if len(actual_starters) != 9:

            skipped.append(

                (

                    year,

                    week,

                    team,

                    f"{len(actual_starters)} starters",

                )

            )

            continue

        actual_score = float(

            actual_starters[

                "fantasy_points"

            ]

            .apply(

                scoring_value

            )

            .sum()

        )

        yahoo_team_score = (

            team_week["team_score"]

            .dropna()

            .iloc[0]

            if "team_score" in team_week.columns

            and not team_week[

                "team_score"

            ].dropna().empty

            else actual_score

        )

        roster = team_week[

            ~team_week["is_ir"]

        ].copy()

        try:

            optimal, optimal_score = (

                build_optimal_lineup(

                    roster,

                    historical_position_lookup,

                )

            )

        except Exception as exc:

            skipped.append(

                (

                    year,

                    week,

                    team,

                    str(exc),

                )

            )

            continue

        points_left = round(

            optimal_score

            - actual_score,

            2,

        )

        efficiency = (

            actual_score

            / optimal_score

            * 100

            if optimal_score > 0

            else 100.0

        )

        actual_players = set(

            actual_starters.index

        )

        optimal_players = set(

            optimal.index

        )

        bad_starts = actual_starters[

            actual_starters.index.isin(

                actual_players

                - optimal_players

            )

        ]

        missed_starts = optimal[

            optimal.index.isin(

                optimal_players

                - actual_players

            )

        ]

        team_week_rows.append(

            {

                "year": int(year),

                "week": int(week),

                "fantasy_team": team,

                "opponent": opponent,

                "actual_score": round(

                    actual_score,

                    2,

                ),

                "yahoo_team_score": round(

                    float(yahoo_team_score),

                    2,

                ),

                "optimal_score": round(

                    optimal_score,

                    2,

                ),

                "points_left_on_bench": points_left,

                "lineup_efficiency_pct": round(

                    efficiency,

                    2,

                ),

                "avoidable_start_count": len(

                    bad_starts

                ),

                "missed_start_count": len(

                    missed_starts

                ),

                "should_have_benched": " | ".join(

                    player_label(row)

                    for _, row in bad_starts.iterrows()

                ),

                "should_have_started": " | ".join(

                    player_label(row)

                    for _, row in missed_starts.iterrows()

                ),

            }

        )

        decision_rows.extend(

            build_decision_rows(

                team_week=team_week,

                optimal=optimal,

                year=int(year),

                week=int(week),

                team=team,

                opponent=opponent,

            )

        )

    team_week_df = pd.DataFrame(

        team_week_rows

    )

    decisions_df = pd.DataFrame(

        decision_rows

    )

    banner("VALIDATION")

    expected_team_weeks = (

        df.groupby(

            [

                "year",

                "week",

                "fantasy_team",

            ]

        )

        .ngroups

    )

    print(

        f"Team-weeks expected:   "

        f"{expected_team_weeks:,}"

    )

    print(

        f"Team-weeks calculated: "

        f"{len(team_week_df):,}"

    )

    if skipped:

        print()

        print(

            f"Skipped team-weeks: {len(skipped)}"

        )

        for item in skipped[:50]:

            print(item)

        raise RuntimeError(

            "Some team-weeks could not be optimized."

        )

    if len(team_week_df) != expected_team_weeks:

        raise RuntimeError(

            "Team-week output count does not match master data."

        )

    score_diff = (

        team_week_df[

            "actual_score"

        ]

        - team_week_df[

            "yahoo_team_score"

        ]

    ).abs()

    bad_score_rows = team_week_df[

        score_diff > 0.011

    ]

    if not bad_score_rows.empty:

        print(

            bad_score_rows[

                [

                    "year",

                    "week",

                    "fantasy_team",

                    "actual_score",

                    "yahoo_team_score",

                ]

            ].to_string(

                index=False

            )

        )

        raise RuntimeError(

            "Actual starter score does not reconcile to Yahoo."

        )

    negative_optimal_rows = team_week_df[
        team_week_df["points_left_on_bench"] < -0.011
    ].copy()

    if not negative_optimal_rows.empty:
        banner("DIAGNOSTIC: OPTIMAL SCORE LOWER THAN ACTUAL")
        diagnostic_rows = negative_optimal_rows.sort_values(
            ["year", "week", "fantasy_team"]
        )
        print(diagnostic_rows[
            ["year", "week", "fantasy_team", "opponent",
             "actual_score", "optimal_score", "points_left_on_bench"]
        ].to_string(index=False))

        for _, problem in diagnostic_rows.iterrows():
            year = int(problem["year"])
            week = int(problem["week"])
            team = problem["fantasy_team"]
            team_week = df[
                (df["year"] == year) & (df["week"] == week)
                & (df["fantasy_team"] == team)
            ].copy()
            roster = team_week[~team_week["is_ir"]].copy()
            optimal, _ = build_optimal_lineup(roster, historical_position_lookup)
            actual_starters = team_week[team_week["is_starter"]].copy()
            actual_starters["diagnostic_position"] = actual_starters.apply(
                lambda row: infer_player_position(row, historical_position_lookup),
                axis=1,
            )
            actual_starters["diagnostic_points"] = actual_starters[
                "fantasy_points"
            ].apply(scoring_value)

            print()
            print("-" * 96)
            print(
                f"{year} Week {week} | {team} | "
                f"Actual {problem['actual_score']:.2f} | "
                f"Optimal {problem['optimal_score']:.2f} | "
                f"Difference {problem['points_left_on_bench']:.2f}"
            )
            print("-" * 96)
            print("\nACTUAL STARTERS")
            print(actual_starters[
                ["lineup_slot", "player", "diagnostic_position", "diagnostic_points"]
            ].to_string(index=False))
            print("\nOPTIMIZER SELECTED")
            print(optimal[
                ["lineup_slot", "player", "opt_position", "opt_points"]
            ].to_string(index=False))

            actual_indices = set(actual_starters.index)
            optimal_indices = set(optimal.index)
            actual_only = actual_starters[
                actual_starters.index.isin(actual_indices - optimal_indices)
            ]
            optimal_only = optimal[
                optimal.index.isin(optimal_indices - actual_indices)
            ]
            print("\nACTUAL-ONLY PLAYERS")
            print("NONE" if actual_only.empty else actual_only[
                ["lineup_slot", "player", "diagnostic_position", "diagnostic_points"]
            ].to_string(index=False))
            print("\nOPTIMAL-ONLY PLAYERS")
            print("NONE" if optimal_only.empty else optimal_only[
                ["lineup_slot", "player", "opt_position", "opt_points"]
            ].to_string(index=False))

        raise RuntimeError(
            "Optimal score is lower than actual score. See the diagnostic output above."
        )

    print(

        "[PASS] All actual lineup scores "

        "reconcile to Yahoo."

    )

    print(

        "[PASS] Optimal score is never "

        "below actual score."

    )

    # -------------------------------------------------------------------------

    # Season summary

    # -------------------------------------------------------------------------

    banner("BUILDING SEASON SUMMARY")

    season_df = (

        team_week_df.groupby(

            [

                "year",

                "fantasy_team",

            ],

            as_index=False,

        )

        .agg(

            weeks=(

                "week",

                "nunique",

            ),

            actual_points=(

                "actual_score",

                "sum",

            ),

            optimal_points=(

                "optimal_score",

                "sum",

            ),

            points_left_on_bench=(

                "points_left_on_bench",

                "sum",

            ),

            avg_weekly_points_left=(

                "points_left_on_bench",

                "mean",

            ),

            avg_lineup_efficiency_pct=(

                "lineup_efficiency_pct",

                "mean",

            ),

            worst_week_points_left=(

                "points_left_on_bench",

                "max",

            ),

            avoidable_starts=(

                "avoidable_start_count",

                "sum",

            ),

        )

    )

    season_df[

        "season_efficiency_pct"

    ] = (

        season_df[

            "actual_points"

        ]

        / season_df[

            "optimal_points"

        ]

        * 100

    ).round(2)

    numeric_cols = [

        "actual_points",

        "optimal_points",

        "points_left_on_bench",

        "avg_weekly_points_left",

        "avg_lineup_efficiency_pct",

        "worst_week_points_left",

    ]

    season_df[

        numeric_cols

    ] = season_df[

        numeric_cols

    ].round(2)

    # -------------------------------------------------------------------------

    # All-time summary

    # -------------------------------------------------------------------------

    banner("BUILDING ALL-TIME SUMMARY")

    all_time_df = (

        team_week_df.groupby(

            "fantasy_team",

            as_index=False,

        )

        .agg(

            team_weeks=(

                "week",

                "size",

            ),

            actual_points=(

                "actual_score",

                "sum",

            ),

            optimal_points=(

                "optimal_score",

                "sum",

            ),

            points_left_on_bench=(

                "points_left_on_bench",

                "sum",

            ),

            avg_weekly_points_left=(

                "points_left_on_bench",

                "mean",

            ),

            avg_lineup_efficiency_pct=(

                "lineup_efficiency_pct",

                "mean",

            ),

            worst_week_points_left=(

                "points_left_on_bench",

                "max",

            ),

            avoidable_starts=(

                "avoidable_start_count",

                "sum",

            ),

        )

    )

    all_time_df[

        "all_time_efficiency_pct"

    ] = (

        all_time_df[

            "actual_points"

        ]

        / all_time_df[

            "optimal_points"

        ]

        * 100

    ).round(2)

    all_time_df[

        [

            "actual_points",

            "optimal_points",

            "points_left_on_bench",

            "avg_weekly_points_left",

            "avg_lineup_efficiency_pct",

            "worst_week_points_left",

        ]

    ] = all_time_df[

        [

            "actual_points",

            "optimal_points",

            "points_left_on_bench",

            "avg_weekly_points_left",

            "avg_lineup_efficiency_pct",

            "worst_week_points_left",

        ]

    ].round(2)

    # Rankings: lower points-left is better.

    all_time_df[

        "efficiency_rank"

    ] = (

        all_time_df[

            "all_time_efficiency_pct"

        ]

        .rank(

            ascending=False,

            method="min",

        )

        .astype(int)

    )

    all_time_df = all_time_df.sort_values(

        [

            "efficiency_rank",

            "fantasy_team",

        ]

    )

    # -------------------------------------------------------------------------

    # Save

    # -------------------------------------------------------------------------

    banner("SAVING FILES")

    team_week_df.to_csv(

        TEAM_WEEK_OUTPUT,

        index=False,

    )

    season_df.to_csv(

        SEASON_OUTPUT,

        index=False,

    )

    all_time_df.to_csv(

        ALL_TIME_OUTPUT,

        index=False,

    )

    decisions_df.to_csv(

        DECISIONS_OUTPUT,

        index=False,

    )

    print(TEAM_WEEK_OUTPUT)

    print(SEASON_OUTPUT)

    print(ALL_TIME_OUTPUT)

    print(DECISIONS_OUTPUT)

    banner("LINEUP EFFICIENCY BUILD COMPLETE")

    print(

        f"Team-weeks: "

        f"{len(team_week_df):,}"

    )

    print(

        f"Decision rows: "

        f"{len(decisions_df):,}"

    )

    print()

    print(

        "Next: review the all-time and season summaries "

        "before adding lineup-efficiency sections to Streamlit."

    )



if __name__ == "__main__":

    main()