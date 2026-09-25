from pathlib import Path

import numpy as np
import pandas as pd

from team_aliases import canonical_team


ROOT = Path(__file__).resolve().parent

TRADES_FILE = ROOT / "data" / "trades" / "trades.csv"
ASSETS_FILE = ROOT / "data" / "trades" / "trade_assets.csv"
LINEUPS_FILE = (
    ROOT
    / "data"
    / "matchups"
    / "player_week_stats"
    / "all_weekly_lineups.csv"
)

NFL_FILE = (
    ROOT
    / "data"
    / "nfl"
    / "player_week_teams.csv"
)

POSITIONS = ["QB", "RB", "WR", "TE"]

OUT_DIR = ROOT / "data" / "trades" / "analysis"

PLAYER_OUT = OUT_DIR / "trade_player_performance.csv"
SIDE_OUT = OUT_DIR / "trade_side_performance.csv"
ACTIVITY_OUT = OUT_DIR / "trade_activity.csv"

PLAYER_VALUE_OUT = OUT_DIR / "trade_player_value.csv"
SIDE_VALUE_OUT = OUT_DIR / "trade_side_value.csv"
RESULTS_OUT = OUT_DIR / "trade_results.csv"
FRANCHISE_OUT = OUT_DIR / "trade_franchise_summary.csv"


def fail(message):
    raise RuntimeError(message)


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_player(value):
    value = clean_text(value)

    replacements = {
        "Robbie Anderson": "Robbie Chosen",
    }

    return replacements.get(value, value)


def build_historical_position_lookup(lineups):
    fixed = lineups[
        lineups["is_starter"].eq(True)
        & lineups["lineup_slot"].isin(POSITIONS)
    ][
        [
            "player_clean",
            "lineup_slot",
        ]
    ].copy()

    fixed = fixed[
        fixed["player_clean"].ne("")
        & fixed["player_clean"].ne("(Empty)")
    ]

    counts = (
        fixed.groupby(
            [
                "player_clean",
                "lineup_slot",
            ]
        )
        .size()
        .reset_index(name="appearances")
    )

    best = (
        counts.sort_values(
            [
                "player_clean",
                "appearances",
                "lineup_slot",
            ],
            ascending=[
                True,
                False,
                True,
            ],
        )
        .drop_duplicates("player_clean")
    )

    return dict(
        zip(
            best["player_clean"],
            best["lineup_slot"],
        )
    )


def build_nfl_position_lookup(nfl):
    work = nfl[
        [
            "year",
            "week",
            "player",
            "nfl_position",
        ]
    ].copy()

    work["year"] = pd.to_numeric(
        work["year"],
        errors="coerce",
    )

    work["week"] = pd.to_numeric(
        work["week"],
        errors="coerce",
    )

    work["player_clean"] = (
        work["player"]
        .map(clean_player)
    )

    work = (
        work.dropna(
            subset=[
                "year",
                "week",
                "player_clean",
                "nfl_position",
            ]
        )
        .drop_duplicates(
            [
                "year",
                "week",
                "player_clean",
            ]
        )
    )

    return {
        (
            int(row.year),
            int(row.week),
            row.player_clean,
        ): str(row.nfl_position).strip().upper()
        for row in work.itertuples(index=False)
    }


AUDITED_POSITION_FALLBACKS = {
    "DK Metcalf": "WR",
    "AJ Dillon": "RB",
    "Jeff Wilson Jr.": "RB",
    "Michael Carter": "RB",
    "Michael Thomas": "WR",
    "Jalen Coker": "WR",
    "Kendall Hinton": "WR",
}


def resolve_trade_player_position(
    year,
    player,
    stint,
    historical_position_map,
    nfl_position_map,
):
    # First preference: an actual fixed fantasy lineup slot
    # observed during this acquired stint.
    if not stint.empty:
        fixed = stint[
            stint["lineup_slot"].isin(POSITIONS)
        ]

        if not fixed.empty:
            counts = (
                fixed["lineup_slot"]
                .value_counts()
            )

            return (
                str(counts.index[0]),
                "acquired_stint_fixed_slot",
            )

    # Second preference: the player's historical fixed fantasy
    # position anywhere in league lineup history.
    historical = historical_position_map.get(
        player,
        "",
    )

    if historical in POSITIONS:
        return (
            historical,
            "historical_fixed_slot",
        )

    # Third preference: NFL player-week mapping. Prefer weeks
    # belonging to the acquired stint when available.
    if not stint.empty:
        for week in sorted(
            stint["week"]
            .dropna()
            .astype(int)
            .unique()
        ):
            position = nfl_position_map.get(
                (
                    int(year),
                    int(week),
                    player,
                ),
                "",
            )

            if position in POSITIONS:
                return (
                    position,
                    "nfl_player_week",
                )

    # If there is no acquired stint, or its weeks did not resolve,
    # inspect any player-week NFL position in that season.
    season_positions = [
        position
        for (
            map_year,
            map_week,
            map_player,
        ), position in nfl_position_map.items()
        if (
            map_year == int(year)
            and map_player == player
            and position in POSITIONS
        )
    ]

    if season_positions:
        counts = pd.Series(
            season_positions
        ).value_counts()

        return (
            str(counts.index[0]),
            "nfl_season_position",
        )

    fallback = AUDITED_POSITION_FALLBACKS.get(
        player,
        "",
    )

    if fallback:
        return (
            fallback,
            "audited_fallback",
        )

    return "", "unresolved"


def load_data():
    for path in (
        TRADES_FILE,
        ASSETS_FILE,
        LINEUPS_FILE,
        NFL_FILE,
    ):
        if not path.exists():
            fail(f"Missing required file: {path}")

    trades = pd.read_csv(TRADES_FILE)
    assets = pd.read_csv(ASSETS_FILE)
    lineups = pd.read_csv(LINEUPS_FILE)
    nfl = pd.read_csv(NFL_FILE)

    return trades, assets, lineups, nfl


def prepare_lineups(lineups):
    df = lineups.copy()

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    ).astype("Int64")

    df["week"] = pd.to_numeric(
        df["week"],
        errors="coerce",
    ).astype("Int64")

    df["fantasy_points"] = pd.to_numeric(
        df["fantasy_points"],
        errors="coerce",
    )

    df["projected_points"] = pd.to_numeric(
        df["projected_points"],
        errors="coerce",
    )

    df["player_clean"] = (
        df["player"]
        .map(clean_player)
    )

    df["fantasy_team_clean"] = (
        df["fantasy_team"]
        .map(clean_text)
    )

    for col in (
        "is_starter",
        "is_bench",
        "is_ir",
    ):
        if col in df.columns:
            if df[col].dtype != bool:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .map({
                        "true": True,
                        "false": False,
                        "1": True,
                        "0": False,
                    })
                    .fillna(False)
                )

    # Resolve historical franchise names to the same canonical names
    # used by the trade collector and the rest of the league site.
    df["fantasy_team_clean"] = (
        df["fantasy_team_clean"]
        .map(canonical_team)
    )

    return df


def player_trade_performance(
    assets,
    lineups,
    historical_position_map,
    nfl_position_map,
):
    assets = assets.copy()

    # Trade records and historical lineup records must use identical
    # franchise identities before player ownership is matched.
    for col in ("source_team", "destination_team"):
        if col in assets.columns:
            assets[col] = assets[col].map(canonical_team)
    rows = []

    for asset in assets.itertuples(index=False):
        year = int(asset.year)

        player = clean_player(asset.player)
        acquiring_team = clean_text(
            asset.destination_team
        )
        sending_team = clean_text(
            asset.source_team
        )

        player_year = lineups[
            lineups["year"].eq(year)
            & lineups["player_clean"].eq(player)
        ].copy()

        acquired_rows = player_year[
            player_year["fantasy_team_clean"].eq(
                acquiring_team
            )
        ].copy()

        acquired_rows = acquired_rows.sort_values(
            ["week"],
            kind="stable",
        )

        if acquired_rows.empty:
            stint = acquired_rows.copy()
            first_week = np.nan
            last_week = np.nan
            roster_weeks = 0
            starts = 0
            bench_weeks = 0
            ir_weeks = 0
            fantasy_points = 0.0
            started_points = 0.0
            bench_points = 0.0
            projected_points = 0.0

        else:
            first_week = int(
                acquired_rows["week"].min()
            )
            last_week = int(
                acquired_rows["week"].max()
            )

            # Only count the contiguous stint beginning
            # when the player first appears on the
            # acquiring franchise.
            #
            # If the player later leaves and somehow
            # returns, the later stint should not silently
            # be credited to this trade.
            weeks = sorted(
                acquired_rows["week"]
                .dropna()
                .astype(int)
                .unique()
            )

            contiguous = []

            if weeks:
                contiguous = [weeks[0]]

                for week in weeks[1:]:
                    if week == contiguous[-1] + 1:
                        contiguous.append(week)
                    else:
                        break

            stint = acquired_rows[
                acquired_rows["week"].isin(
                    contiguous
                )
            ].copy()

            if stint.empty:
                roster_weeks = 0
                starts = 0
                bench_weeks = 0
                ir_weeks = 0
                fantasy_points = 0.0
                started_points = 0.0
                bench_points = 0.0
                projected_points = 0.0

            else:
                first_week = int(
                    stint["week"].min()
                )
                last_week = int(
                    stint["week"].max()
                )

                roster_weeks = int(
                    stint["week"].nunique()
                )

                starts = int(
                    stint["is_starter"].sum()
                )

                bench_weeks = int(
                    stint["is_bench"].sum()
                )

                ir_weeks = int(
                    stint["is_ir"].sum()
                )

                fantasy_points = float(
                    stint["fantasy_points"]
                    .fillna(0)
                    .sum()
                )

                started_points = float(
                    stint.loc[
                        stint["is_starter"],
                        "fantasy_points",
                    ]
                    .fillna(0)
                    .sum()
                )

                bench_points = float(
                    stint.loc[
                        stint["is_bench"],
                        "fantasy_points",
                    ]
                    .fillna(0)
                    .sum()
                )

                projected_points = float(
                    stint["projected_points"]
                    .fillna(0)
                    .sum()
                )

        position, position_source = resolve_trade_player_position(
            year=year,
            player=player,
            stint=stint,
            historical_position_map=historical_position_map,
            nfl_position_map=nfl_position_map,
        )

        if roster_weeks == 0:
            attribution_status = "no_post_trade_roster_stint"
        else:
            attribution_status = "matched_post_trade_roster_stint"

        points_per_roster_week = (
            fantasy_points / roster_weeks
            if roster_weeks
            else 0.0
        )

        points_per_start = (
            started_points / starts
            if starts
            else 0.0
        )

        rows.append({
            "trade_id": asset.trade_id,
            "year": year,
            "date": asset.date,
            "player": player,
            "source_team": sending_team,
            "destination_team": acquiring_team,
            "position": position,
            "position_source": position_source,
            "attribution_status": attribution_status,
            "first_week_with_acquiring_team": first_week,
            "last_week_with_acquiring_team": last_week,
            "roster_weeks": roster_weeks,
            "starts": starts,
            "bench_weeks": bench_weeks,
            "ir_weeks": ir_weeks,
            "fantasy_points": round(
                fantasy_points,
                2,
            ),
            "started_points": round(
                started_points,
                2,
            ),
            "bench_points": round(
                bench_points,
                2,
            ),
            "projected_points": round(
                projected_points,
                2,
            ),
            "points_per_roster_week": round(
                points_per_roster_week,
                2,
            ),
            "points_per_start": round(
                points_per_start,
                2,
            ),
        })

    return pd.DataFrame(rows)


def build_trade_sides(player_perf):
    rows = []

    grouped = player_perf.groupby(
        [
            "trade_id",
            "year",
            "date",
            "destination_team",
        ],
        dropna=False,
    )

    for (
        trade_id,
        year,
        date,
        team,
    ), group in grouped:

        players = (
            group["player"]
            .astype(str)
            .tolist()
        )

        rows.append({
            "trade_id": trade_id,
            "year": int(year),
            "date": date,
            "team": team,
            "players_received": " | ".join(players),
            "players_received_count": len(players),
            "roster_weeks": int(
                group["roster_weeks"].sum()
            ),
            "starts": int(
                group["starts"].sum()
            ),
            "bench_weeks": int(
                group["bench_weeks"].sum()
            ),
            "ir_weeks": int(
                group["ir_weeks"].sum()
            ),
            "fantasy_points": round(
                group["fantasy_points"].sum(),
                2,
            ),
            "started_points": round(
                group["started_points"].sum(),
                2,
            ),
            "bench_points": round(
                group["bench_points"].sum(),
                2,
            ),
            "projected_points": round(
                group["projected_points"].sum(),
                2,
            ),
        })

    sides = pd.DataFrame(rows)

    counts = (
        sides.groupby("trade_id")
        .size()
    )

    bad = counts[counts.ne(2)]

    if not bad.empty:
        fail(
            "Expected exactly two evaluated sides "
            f"per trade: {bad.to_dict()}"
        )

    return sides



def build_replacement_baselines(lineups):
    """
    Build season/position replacement baselines from this
    league's actual fixed-slot starters.

    Replacement starter = 40th percentile.
    Replacement bench/depth = 25th percentile.
    """

    starters = lineups[
        lineups["is_starter"].eq(True)
        & lineups["lineup_slot"].isin(POSITIONS)
    ].copy()

    starters["fantasy_points"] = pd.to_numeric(
        starters["fantasy_points"],
        errors="coerce",
    ).fillna(0.0)

    baseline = (
        starters.groupby(
            [
                "year",
                "lineup_slot",
            ]
        )["fantasy_points"]
        .agg(
            starter_appearances="size",
            starter_mean="mean",
            starter_median="median",
            replacement_p25=lambda x: x.quantile(0.25),
            replacement_p40=lambda x: x.quantile(0.40),
        )
        .reset_index()
        .rename(
            columns={
                "lineup_slot": "position",
            }
        )
    )

    numeric_cols = [
        "starter_mean",
        "starter_median",
        "replacement_p25",
        "replacement_p40",
    ]

    baseline[numeric_cols] = (
        baseline[numeric_cols]
        .round(4)
    )

    return baseline


def build_player_value(
    player_perf,
    replacement_baselines,
):
    """
    Convert raw post-trade production into realized trade value.

    Starter value:
        positive points above the season/position P40
        replacement starter baseline.

    Bench/depth value:
        25% credit for positive bench production above the
        season/position P25 baseline.

    Negative starter value is preserved separately for
    descriptive analysis, but realized trade value is floored
    at zero so a bad start cannot make an acquired player worth
    less than an asset that never produced for the franchise.
    """

    df = player_perf.copy()

    baselines = replacement_baselines[
        [
            "year",
            "position",
            "replacement_p25",
            "replacement_p40",
        ]
    ].copy()

    df = df.merge(
        baselines,
        on=[
            "year",
            "position",
        ],
        how="left",
        validate="many_to_one",
    )

    missing = df[
        df["replacement_p40"].isna()
        | df["replacement_p25"].isna()
    ]

    if not missing.empty:
        cols = [
            "trade_id",
            "year",
            "player",
            "position",
        ]

        fail(
            "Missing replacement baseline for traded player(s):\n"
            + missing[cols].to_string(index=False)
        )

    df["expected_replacement_started_points"] = (
        df["starts"]
        * df["replacement_p40"]
    )

    df["raw_starter_value"] = (
        df["started_points"]
        - df["expected_replacement_started_points"]
    )

    df["starter_value"] = (
        df["raw_starter_value"]
        .clip(lower=0.0)
    )

    df["expected_replacement_bench_points"] = (
        df["bench_weeks"]
        * df["replacement_p25"]
    )

    df["raw_bench_value"] = (
        df["bench_points"]
        - df["expected_replacement_bench_points"]
    )

    df["bench_value"] = (
        df["raw_bench_value"]
        .clip(lower=0.0)
        * 0.25
    )

    df["trade_value"] = (
        df["starter_value"]
        + df["bench_value"]
    )

    df["start_value_per_start"] = np.where(
        df["starts"].gt(0),
        df["raw_starter_value"] / df["starts"],
        0.0,
    )

    df["starter_points_vs_replacement_pct"] = np.where(
        df["expected_replacement_started_points"].gt(0),
        (
            df["started_points"]
            / df["expected_replacement_started_points"]
            - 1.0
        )
        * 100.0,
        0.0,
    )

    round_cols = [
        "replacement_p25",
        "replacement_p40",
        "expected_replacement_started_points",
        "raw_starter_value",
        "starter_value",
        "expected_replacement_bench_points",
        "raw_bench_value",
        "bench_value",
        "trade_value",
        "start_value_per_start",
        "starter_points_vs_replacement_pct",
    ]

    df[round_cols] = df[round_cols].round(2)

    return df


def build_side_value(player_value):
    rows = []

    grouped = player_value.groupby(
        [
            "trade_id",
            "year",
            "date",
            "destination_team",
        ],
        dropna=False,
    )

    for (
        trade_id,
        year,
        date,
        team,
    ), group in grouped:

        players = (
            group["player"]
            .astype(str)
            .tolist()
        )

        positions = (
            group["position"]
            .astype(str)
            .tolist()
        )

        rows.append({
            "trade_id": trade_id,
            "year": int(year),
            "date": date,
            "team": team,
            "players_received": " | ".join(players),
            "positions_received": " | ".join(positions),
            "players_received_count": len(group),
            "roster_weeks": int(
                group["roster_weeks"].sum()
            ),
            "starts": int(
                group["starts"].sum()
            ),
            "bench_weeks": int(
                group["bench_weeks"].sum()
            ),
            "fantasy_points": round(
                group["fantasy_points"].sum(),
                2,
            ),
            "started_points": round(
                group["started_points"].sum(),
                2,
            ),
            "bench_points": round(
                group["bench_points"].sum(),
                2,
            ),
            "expected_replacement_started_points": round(
                group[
                    "expected_replacement_started_points"
                ].sum(),
                2,
            ),
            "raw_starter_value": round(
                group["raw_starter_value"].sum(),
                2,
            ),
            "starter_value": round(
                group["starter_value"].sum(),
                2,
            ),
            "bench_value": round(
                group["bench_value"].sum(),
                2,
            ),
            "trade_value": round(
                group["trade_value"].sum(),
                2,
            ),
            "unmatched_assets": int(
                group["attribution_status"]
                .eq("no_post_trade_roster_stint")
                .sum()
            ),
        })

    sides = pd.DataFrame(rows)

    counts = (
        sides.groupby("trade_id")
        .size()
    )

    bad = counts[counts.ne(2)]

    if not bad.empty:
        fail(
            "Expected exactly two valued sides per trade: "
            f"{bad.to_dict()}"
        )

    return sides


def classify_trade_result(
    winner_value,
    loser_value,
):
    """
    Classify the strength of the result.

    Uses both absolute margin and relative margin so tiny,
    low-value trades cannot become misleading 'fleeces'.
    """

    winner_value = float(winner_value)
    loser_value = float(loser_value)

    margin = winner_value - loser_value
    combined = winner_value + loser_value

    if combined <= 0:
        return "Even"

    margin_pct = margin / combined

    # Small absolute differences are treated as even regardless
    # of percentage.
    if margin < 5.0:
        return "Even"

    if margin_pct < 0.10:
        return "Even"

    if margin_pct < 0.25:
        return "Slight Win"

    if margin_pct < 0.50:
        return "Clear Win"

    if margin_pct < 0.75:
        return "Big Win"

    return "Fleece"


def build_trade_results(
    trades,
    side_value,
):
    rows = []

    trade_lookup = (
        trades
        .drop_duplicates("trade_id")
        .set_index("trade_id")
    )

    for trade_id, group in side_value.groupby(
        "trade_id"
    ):
        if len(group) != 2:
            fail(
                f"{trade_id}: expected exactly two sides, "
                f"found {len(group)}"
            )

        group = (
            group.sort_values(
                [
                    "trade_value",
                    "team",
                ],
                ascending=[
                    False,
                    True,
                ],
                kind="stable",
            )
            .reset_index(drop=True)
        )

        first = group.iloc[0]
        second = group.iloc[1]

        value_1 = float(first["trade_value"])
        value_2 = float(second["trade_value"])

        margin = abs(value_1 - value_2)
        combined = value_1 + value_2

        margin_pct = (
            margin / combined
            if combined > 0
            else 0.0
        )

        result_class = classify_trade_result(
            max(value_1, value_2),
            min(value_1, value_2),
        )

        if result_class == "Even":
            winner = ""
            loser = ""
        else:
            winner = first["team"]
            loser = second["team"]

        trade_row = trade_lookup.loc[trade_id]

        rows.append({
            "trade_id": trade_id,
            "year": int(first["year"]),
            "date": first["date"],
            "team_1": first["team"],
            "team_1_players": first["players_received"],
            "team_1_value": round(value_1, 2),
            "team_1_started_points": round(
                float(first["started_points"]),
                2,
            ),
            "team_1_raw_starter_value": round(
                float(first["raw_starter_value"]),
                2,
            ),
            "team_2": second["team"],
            "team_2_players": second["players_received"],
            "team_2_value": round(value_2, 2),
            "team_2_started_points": round(
                float(second["started_points"]),
                2,
            ),
            "team_2_raw_starter_value": round(
                float(second["raw_starter_value"]),
                2,
            ),
            "winner": winner,
            "loser": loser,
            "winner_margin": round(margin, 2),
            "winner_margin_pct": round(
                margin_pct * 100.0,
                1,
            ),
            "result_class": result_class,
            "total_trade_value": round(
                combined,
                2,
            ),
            "unmatched_assets": int(
                first["unmatched_assets"]
                + second["unmatched_assets"]
            ),
            "source": (
                trade_row["source"]
                if "source" in trade_row.index
                else ""
            ),
        })

    return (
        pd.DataFrame(rows)
        .sort_values(
            [
                "year",
                "date",
                "trade_id",
            ],
            ascending=[
                False,
                False,
                False,
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def build_franchise_summary(
    trade_results,
    activity,
):
    teams = sorted(
        set(trade_results["team_1"])
        | set(trade_results["team_2"])
    )

    rows = []

    for team in teams:
        involved = trade_results[
            trade_results["team_1"].eq(team)
            | trade_results["team_2"].eq(team)
        ].copy()

        wins = int(
            involved["winner"].eq(team).sum()
        )

        losses = int(
            involved["loser"].eq(team).sum()
        )

        evens = int(
            involved["result_class"].eq("Even").sum()
        )

        total_received = 0.0
        total_opponent = 0.0
        margins = []

        best_trade = ""
        worst_trade = ""
        best_margin = None
        worst_margin = None

        for row in involved.itertuples(index=False):
            if row.team_1 == team:
                own_value = float(row.team_1_value)
                opponent_value = float(row.team_2_value)
            else:
                own_value = float(row.team_2_value)
                opponent_value = float(row.team_1_value)

            advantage = own_value - opponent_value

            total_received += own_value
            total_opponent += opponent_value
            margins.append(advantage)

            if (
                best_margin is None
                or advantage > best_margin
            ):
                best_margin = advantage
                best_trade = row.trade_id

            if (
                worst_margin is None
                or advantage < worst_margin
            ):
                worst_margin = advantage
                worst_trade = row.trade_id

        decisive = wins + losses

        win_pct = (
            wins / decisive
            if decisive
            else 0.0
        )

        activity_row = activity[
            activity["team"].eq(team)
        ]

        first_trade_year = (
            int(activity_row["first_trade_year"].iloc[0])
            if not activity_row.empty
            else np.nan
        )

        last_trade_year = (
            int(activity_row["last_trade_year"].iloc[0])
            if not activity_row.empty
            else np.nan
        )

        rows.append({
            "team": team,
            "trades": len(involved),
            "wins": wins,
            "losses": losses,
            "even": evens,
            "decisive_trades": decisive,
            "win_pct": round(
                win_pct * 100.0,
                1,
            ),
            "total_value_received": round(
                total_received,
                2,
            ),
            "total_opponent_value": round(
                total_opponent,
                2,
            ),
            "total_value_advantage": round(
                total_received - total_opponent,
                2,
            ),
            "avg_trade_advantage": round(
                np.mean(margins)
                if margins
                else 0.0,
                2,
            ),
            "best_trade": best_trade,
            "best_trade_margin": round(
                best_margin
                if best_margin is not None
                else 0.0,
                2,
            ),
            "worst_trade": worst_trade,
            "worst_trade_margin": round(
                worst_margin
                if worst_margin is not None
                else 0.0,
                2,
            ),
            "first_trade_year": first_trade_year,
            "last_trade_year": last_trade_year,
        })

    return (
        pd.DataFrame(rows)
        .sort_values(
            [
                "total_value_advantage",
                "win_pct",
                "trades",
                "team",
            ],
            ascending=[
                False,
                False,
                False,
                True,
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def build_activity(trades, assets):
    participation = []

    for trade_id, group in assets.groupby(
        "trade_id"
    ):
        year = int(
            group["year"].iloc[0]
        )

        teams = (
            set(
                group["source_team"]
                .dropna()
                .astype(str)
            )
            | set(
                group["destination_team"]
                .dropna()
                .astype(str)
            )
        )

        for team in teams:
            participation.append({
                "trade_id": trade_id,
                "year": year,
                "team": team,
            })

    participation = pd.DataFrame(
        participation
    )

    activity = (
        participation.groupby("team")
        .agg(
            trades=("trade_id", "nunique"),
            first_trade_year=("year", "min"),
            last_trade_year=("year", "max"),
        )
        .reset_index()
        .sort_values(
            ["trades", "team"],
            ascending=[False, True],
        )
    )

    return activity


def validate(
    trades,
    assets,
    player_perf,
    sides,
):
    print()
    print("=" * 100)
    print("VALIDATION")
    print("=" * 100)

    if len(trades) != 30:
        fail(
            f"Expected 30 trades, found {len(trades)}"
        )

    if len(assets) != 92:
        fail(
            f"Expected 92 assets, found {len(assets)}"
        )

    if len(player_perf) != len(assets):
        fail(
            "Player performance rows do not match "
            "trade asset rows."
        )

    if len(sides) != len(trades) * 2:
        fail(
            f"Expected 60 trade sides, found {len(sides)}"
        )

    print("[PASS] 30 historical trades")
    print("[PASS] 92 trade assets")
    print("[PASS] 92 player performance rows")
    print("[PASS] 60 trade sides")

    missing = player_perf[
        player_perf["roster_weeks"].eq(0)
    ]

    print()
    print(
        "Trade assets with no matching post-trade "
        f"lineup stint: {len(missing)}"
    )

    if not missing.empty:
        print(
            missing[
                [
                    "trade_id",
                    "year",
                    "player",
                    "source_team",
                    "destination_team",
                ]
            ].to_string(
                index=False
            )
        )


def main():
    print("=" * 100)
    print("BUILDING TRADE PERFORMANCE ANALYSIS")
    print("=" * 100)

    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    trades, assets, lineups, nfl = load_data()

    lineups = prepare_lineups(
        lineups
    )

    historical_position_map = (
        build_historical_position_lookup(
            lineups
        )
    )

    nfl_position_map = (
        build_nfl_position_lookup(
            nfl
        )
    )

    print(
        f"[PASS] Historical position lookup: "
        f"{len(historical_position_map):,} players"
    )
    print(
        f"[PASS] NFL player-week position lookup: "
        f"{len(nfl_position_map):,} records"
    )

    player_perf = player_trade_performance(
        assets,
        lineups,
        historical_position_map,
        nfl_position_map,
    )

    sides = build_trade_sides(
        player_perf
    )

    activity = build_activity(
        trades,
        assets,
    )

    replacement_baselines = (
        build_replacement_baselines(
            lineups
        )
    )

    player_value = build_player_value(
        player_perf,
        replacement_baselines,
    )

    side_value = build_side_value(
        player_value
    )

    trade_results = build_trade_results(
        trades,
        side_value,
    )

    franchise_summary = build_franchise_summary(
        trade_results,
        activity,
    )

    validate(
        trades,
        assets,
        player_perf,
        sides,
    )

    player_perf.to_csv(
        PLAYER_OUT,
        index=False,
    )

    sides.to_csv(
        SIDE_OUT,
        index=False,
    )

    activity.to_csv(
        ACTIVITY_OUT,
        index=False,
    )

    player_value.to_csv(
        PLAYER_VALUE_OUT,
        index=False,
    )

    side_value.to_csv(
        SIDE_VALUE_OUT,
        index=False,
    )

    trade_results.to_csv(
        RESULTS_OUT,
        index=False,
    )

    franchise_summary.to_csv(
        FRANCHISE_OUT,
        index=False,
    )

    print()
    print("=" * 100)
    print("TRADE ACTIVITY")
    print("=" * 100)
    print(
        activity.to_string(
            index=False
        )
    )

    print()
    print("=" * 100)
    print("RAW TRADE SIDES")
    print("=" * 100)

    display = sides[
        [
            "trade_id",
            "team",
            "players_received",
            "roster_weeks",
            "starts",
            "fantasy_points",
            "started_points",
            "bench_points",
        ]
    ].copy()

    print(
        display.to_string(
            index=False
        )
    )

    print()
    print("=" * 100)
    print("TRADE RESULTS")
    print("=" * 100)

    result_display = trade_results[
        [
            "trade_id",
            "year",
            "team_1",
            "team_1_players",
            "team_1_value",
            "team_2",
            "team_2_players",
            "team_2_value",
            "winner",
            "winner_margin",
            "result_class",
        ]
    ].copy()

    print(
        result_display.to_string(
            index=False
        )
    )

    print()
    print("=" * 100)
    print("FRANCHISE TRADE SUMMARY")
    print("=" * 100)

    print(
        franchise_summary.to_string(
            index=False
        )
    )

    print()
    print("=" * 100)
    print("FILES WRITTEN")
    print("=" * 100)

    for path in (
        PLAYER_OUT,
        SIDE_OUT,
        ACTIVITY_OUT,
        PLAYER_VALUE_OUT,
        SIDE_VALUE_OUT,
        RESULTS_OUT,
        FRANCHISE_OUT,
    ):
        print(
            path.relative_to(ROOT)
        )

    print()
    print(
        "TRADE PERFORMANCE BUILD COMPLETE"
    )


if __name__ == "__main__":
    main()
