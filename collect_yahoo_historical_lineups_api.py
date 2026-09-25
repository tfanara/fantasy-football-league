from __future__ import annotations

"""
Rebuild historical Yahoo weekly lineup data directly from the authenticated
Yahoo Fantasy API.

This script intentionally DOES NOT overwrite production historical lineup
files. Rebuilt files are written to:

    data/matchups/player_week_stats/api_rebuild/

Seasons rebuilt:
    2018-2025

2017 is intentionally excluded.

The purpose of this collector is to replace historical lineup ownership data
originally produced by the legacy HTML/Chromium scraper.
"""

from pathlib import Path
import argparse
import time
import xml.etree.ElementTree as ET

import pandas as pd
from yahoofantasy import Context

from team_aliases import canonical_team


ROOT = Path(__file__).resolve().parent

OUTPUT_DIR = (
    ROOT
    / "data"
    / "matchups"
    / "player_week_stats"
    / "api_rebuild"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# VERIFIED HISTORICAL YAHOO LEAGUES
# ---------------------------------------------------------------------

SEASONS = {
    2018: {
        "game_key": "380",
        "league_id": "941496",
    },
    2019: {
        "game_key": "390",
        "league_id": "322794",
    },
    2020: {
        "game_key": "399",
        "league_id": "510142",
    },
    2021: {
        "game_key": "406",
        "league_id": "410355",
    },
    2022: {
        "game_key": "414",
        "league_id": "854563",
    },
    2023: {
        "game_key": "423",
        "league_id": "684195",
    },
    2024: {
        "game_key": "449",
        "league_id": "673480",
    },
    2025: {
        "game_key": "461",
        "league_id": "637567",
    },
}


EXPECTED_TEAMS = 12
EXPECTED_MATCHUPS = 6

NS = {
    "f": "http://fantasysports.yahooapis.com/fantasy/v2/base.rng"
}


def fail(message: str):
    raise RuntimeError(message)


def canon_team(name) -> str:
    if name is None:
        return ""

    name = str(name).strip()
    return str(canonical_team(name)).strip()


def text(node, path: str, default=None):
    found = node.find(path, NS)

    if found is None or found.text is None:
        return default

    return found.text.strip()


def as_float(value):
    if value in (None, ""):
        return None

    return float(value)


def parse_xml(payload: str) -> ET.Element:
    if not isinstance(payload, str):
        fail("Yahoo returned a non-string response.")

    if "<fantasy_content" not in payload:
        fail("Yahoo returned an unexpected non-XML response.")

    return ET.fromstring(payload)


# =====================================================================
# LEAGUE TEAMS
# =====================================================================

def collect_league_teams(
    ctx: Context,
    league_key: str,
) -> pd.DataFrame:

    root = parse_xml(
        ctx.make_request(
            f"league/{league_key}/teams"
        )
    )

    rows = []

    for team in root.findall(
        ".//f:league/f:teams/f:team",
        NS,
    ):
        team_key = text(team, "f:team_key")
        team_id = text(team, "f:team_id")
        name = text(team, "f:name")

        if not team_key or not name:
            continue

        rows.append(
            {
                "team_key": team_key,
                "team_id": team_id,
                "fantasy_team": canon_team(name),
                "yahoo_team_name": name,
            }
        )

    out = (
        pd.DataFrame(rows)
        .drop_duplicates("team_key")
        .reset_index(drop=True)
    )

    if len(out) != EXPECTED_TEAMS:
        fail(
            f"{league_key}: Yahoo returned {len(out)} teams; "
            f"expected {EXPECTED_TEAMS}."
        )

    if out["fantasy_team"].nunique() != EXPECTED_TEAMS:
        fail(
            f"{league_key}: canonical team names are not unique:\n"
            + out[
                [
                    "team_key",
                    "yahoo_team_name",
                    "fantasy_team",
                ]
            ].to_string(index=False)
        )

    return out


# =====================================================================
# SCOREBOARD / MATCHUPS
# =====================================================================

def scoreboard_request(
    ctx: Context,
    league_key: str,
    week: int,
) -> ET.Element:

    return parse_xml(
        ctx.make_request(
            f"league/{league_key}/scoreboard;week={week}"
        )
    )


def parse_scoreboard(
    root: ET.Element,
    *,
    year: int,
    week: int,
) -> list[dict]:

    rows = []

    matchups = root.findall(
        ".//f:scoreboard/f:matchups/f:matchup",
        NS,
    )

    for matchup_number, matchup in enumerate(
        matchups,
        start=1,
    ):
        teams = matchup.findall(
            "./f:teams/f:team",
            NS,
        )

        if len(teams) != 2:
            continue

        parsed = []

        for team in teams:
            team_key = text(team, "f:team_key")
            team_name = text(team, "f:name")
            score = as_float(
                text(
                    team,
                    "f:team_points/f:total",
                )
            )

            parsed.append(
                {
                    "team_key": team_key,
                    "team": canon_team(team_name),
                    "yahoo_team_name": team_name,
                    "score": score,
                }
            )

        if len(parsed) != 2:
            continue

        if (
            not parsed[0]["team"]
            or not parsed[1]["team"]
        ):
            continue

        if (
            parsed[0]["score"] is None
            or parsed[1]["score"] is None
        ):
            continue

        rows.append(
            {
                "year": year,
                "week": week,
                "matchup_number": matchup_number,
                "team_1": parsed[0]["team"],
                "team_2": parsed[1]["team"],
                "team_1_score": parsed[0]["score"],
                "team_2_score": parsed[1]["score"],
                "team_1_key": parsed[0]["team_key"],
                "team_2_key": parsed[1]["team_key"],
            }
        )

    return rows


def collect_completed_matchups(
    ctx: Context,
    league_key: str,
    year: int,
) -> pd.DataFrame:

    all_rows = []

    # Historical leagues can differ in playoff structure.
    # Probe through Week 18 and stop after Yahoo stops returning
    # complete six-game league scoreboards.
    for week in range(1, 19):

        root = scoreboard_request(
            ctx,
            league_key,
            week,
        )

        rows = parse_scoreboard(
            root,
            year=year,
            week=week,
        )

        if len(rows) != EXPECTED_MATCHUPS:
            if all_rows:
                print(
                    f"[INFO] {year} Week {week}: "
                    f"{len(rows)} complete matchup(s); "
                    "stopping completed-week collection."
                )
                break

            fail(
                f"{year} Week {week}: Yahoo returned "
                f"{len(rows)} complete matchups; expected 6."
            )

        week_df = pd.DataFrame(rows)

        teams = set(
            week_df["team_1"].tolist()
            + week_df["team_2"].tolist()
        )

        if len(teams) != EXPECTED_TEAMS:
            fail(
                f"{year} Week {week}: scoreboard contains "
                f"{len(teams)} teams; expected 12."
            )

        all_rows.extend(rows)

        print(
            f"[PASS] {year} Week {week}: "
            "6 matchups / 12 teams"
        )

    if not all_rows:
        fail(
            f"{year}: no completed Yahoo matchups collected."
        )

    return pd.DataFrame(all_rows)


# =====================================================================
# ROSTERS
# =====================================================================

def roster_request(
    ctx: Context,
    team_key: str,
    week: int,
) -> ET.Element:

    # --------------------------------------------------------
    # PRIMARY ROUTE
    #
    # Yahoo normally allows roster + player stats in a single
    # request. Historical endpoints occasionally return either
    # transient server errors or "Request denied", so retry
    # before using the API-only fallback below.
    # --------------------------------------------------------

    stats_uri = (
        f"team/{team_key}/"
        f"roster;week={week}/players;out=stats"
    )

    max_attempts = 5
    last_error = "unknown error"

    for attempt in range(1, max_attempts + 1):

        try:
            payload = ctx.make_request(stats_uri)

            if (
                isinstance(payload, str)
                and "<fantasy_content" in payload
            ):
                root = parse_xml(payload)

                players = root.findall(
                    ".//f:roster/f:players/f:player",
                    NS,
                )

                if players:
                    return root

                last_error = (
                    "response contained no roster players"
                )

            else:
                preview = repr(payload[:200]) if isinstance(
                    payload,
                    str,
                ) else repr(payload)

                last_error = (
                    "non-XML response: "
                    f"{preview}"
                )

                # "Request denied" is not transient. There is
                # no value waiting through all five retries.
                if (
                    isinstance(payload, str)
                    and "Request denied" in payload
                ):
                    break

        except Exception as exc:
            last_error = (
                f"{type(exc).__name__}: {exc}"
            )

        if attempt < max_attempts:
            wait_seconds = attempt * 2

            print(
                f"[RETRY] {team_key} Week {week}: "
                "Yahoo roster+stats request failed "
                f"(attempt {attempt}/{max_attempts}): "
                f"{last_error}"
            )

            print(
                f"        waiting {wait_seconds}s..."
            )

            time.sleep(wait_seconds)

    # --------------------------------------------------------
    # FALLBACK
    #
    # Keep the entire reconstruction API-only:
    #
    #   1. Get roster / ownership / selected positions.
    #   2. Get weekly player stats in one league-scoped batch.
    #   3. Insert player_points into the roster XML.
    #
    # parse_roster_players() and the existing team-score
    # reconciliation can then operate normally.
    # --------------------------------------------------------

    print(
        f"[FALLBACK] {team_key} Week {week}: "
        "using roster + league-scoped batch player stats"
    )

    roster_uri = (
        f"team/{team_key}/"
        f"roster;week={week}/players"
    )

    roster_root = parse_xml(
        ctx.make_request(roster_uri)
    )

    roster_players = roster_root.findall(
        ".//f:roster/f:players/f:player",
        NS,
    )

    if not roster_players:
        fail(
            f"{team_key} Week {week}: "
            "fallback roster request returned no players."
        )

    player_keys = []

    for player in roster_players:
        player_key = text(
            player,
            "f:player_key",
            "",
        )

        if player_key:
            player_keys.append(player_key)

    if not player_keys:
        fail(
            f"{team_key} Week {week}: "
            "fallback roster contained no player keys."
        )

    # team_key format:
    #     461.l.637567.t.3
    #
    # league_key becomes:
    #     461.l.637567
    parts = team_key.split(".t.")

    if len(parts) != 2:
        fail(
            f"Could not derive league key from "
            f"Yahoo team key {team_key!r}."
        )

    league_key = parts[0]

    keys = ",".join(player_keys)

    batch_uri = (
        f"league/{league_key}/"
        f"players;player_keys={keys}/"
        f"stats;type=week;week={week}"
    )

    batch_root = parse_xml(
        ctx.make_request(batch_uri)
    )

    batch_players = batch_root.findall(
        ".//f:player",
        NS,
    )

    if not batch_players:
        fail(
            f"{team_key} Week {week}: "
            "batch stats request returned no players."
        )

    # Build:
    #     player_key -> fantasy-point total
    #
    # Use the league-scoped endpoint because the unscoped
    # players endpoint returns player records but does not
    # provide league-specific fantasy points.
    points_by_key = {}

    for player in batch_players:

        player_key = text(
            player,
            "f:player_key",
            "",
        )

        points = text(
            player,
            "f:player_points/f:total",
        )

        if player_key:
            points_by_key[player_key] = points

    missing_keys = [
        key
        for key in player_keys
        if key not in points_by_key
    ]

    if missing_keys:
        fail(
            f"{team_key} Week {week}: "
            "batch stats response omitted player keys: "
            f"{missing_keys}"
        )

    # --------------------------------------------------------
    # Inject <player_points><total>...</total></player_points>
    # into each roster player.
    #
    # ElementTree requires the Yahoo namespace on newly created
    # nodes so the existing namespace-aware parser can find them.
    # --------------------------------------------------------

    namespace = (
        "http://fantasysports.yahooapis.com/"
        "fantasy/v2/base.rng"
    )

    for player in roster_players:

        player_key = text(
            player,
            "f:player_key",
            "",
        )

        if not player_key:
            continue

        points = points_by_key.get(player_key)

        # Remove an existing player_points node if Yahoo ever
        # includes one in the non-expanded roster response.
        existing = player.find(
            "f:player_points",
            NS,
        )

        if existing is not None:
            player.remove(existing)

        player_points = ET.SubElement(
            player,
            f"{{{namespace}}}player_points",
        )

        total = ET.SubElement(
            player_points,
            f"{{{namespace}}}total",
        )

        if points is not None:
            total.text = str(points)

    return roster_root


def parse_roster_players(
    root: ET.Element,
    *,
    year: int,
    week: int,
    fantasy_team: str,
    opponent: str,
    matchup_id: str,
    matchup_number: int,
    team_score: float,
    opponent_score: float,
) -> list[dict]:

    rows = []

    for idx, player in enumerate(
        root.findall(
            ".//f:roster/f:players/f:player",
            NS,
        ),
        start=1,
    ):
        player_name = text(
            player,
            "f:name/f:full",
            "",
        )

        if not player_name:
            continue

        lineup_slot = (
            text(
                player,
                "f:selected_position/f:position",
                "",
            )
            or text(
                player,
                "f:display_position",
                "",
            )
        ).upper()

        is_bench = lineup_slot in {
            "BN",
            "BENCH",
        }

        is_ir = lineup_slot in {
            "IR",
            "IR+",
            "NA",
        }

        is_starter = (
            bool(lineup_slot)
            and not is_bench
            and not is_ir
        )

        fantasy_points = as_float(
            text(
                player,
                "f:player_points/f:total",
            )
        )

        projected_points = as_float(
            text(
                player,
                "f:player_projected_points/f:total",
            )
        )

        rows.append(
            {
                "year": year,
                "week": week,
                "table_index": None,
                "row_index": idx,
                "side": "api",
                "fantasy_team": canon_team(
                    fantasy_team
                ),
                "opponent": canon_team(
                    opponent
                ),
                "matchup_id": matchup_id,
                "matchup_number": matchup_number,
                "team_score": team_score,
                "opponent_score": opponent_score,
                "player": player_name,
                "player_position": text(
                    player,
                    "f:display_position",
                    "",
                ),
                "lineup_slot": lineup_slot,
                "is_starter": is_starter,
                "is_bench": is_bench,
                "is_ir": is_ir,
                "projected_points": projected_points,
                "fantasy_points": fantasy_points,
                "stat_summary": "",
                "raw_player_text": player_name,
                "raw_position": text(
                    player,
                    "f:display_position",
                    "",
                ),
                "raw_cells": "",
                "player_key": text(
                    player,
                    "f:player_key",
                ),
                "player_id": text(
                    player,
                    "f:player_id",
                ),
                "nfl_team": text(
                    player,
                    "f:editorial_team_abbr",
                    "",
                ),
                "source": "yahoo_fantasy_api",
            }
        )

    return rows


# =====================================================================
# WEEKLY LINEUPS
# =====================================================================

def collect_weekly_lineups(
    ctx: Context,
    league_key: str,
    year: int,
    matchups: pd.DataFrame,
) -> pd.DataFrame:

    teams = collect_league_teams(
        ctx,
        league_key,
    )

    team_key_by_name = dict(
        zip(
            teams["fantasy_team"],
            teams["team_key"],
        )
    )

    all_rows = []

    weeks = sorted(
        int(x)
        for x in matchups["week"].unique()
    )

    for week in weeks:

        week_games = matchups[
            matchups["week"].eq(week)
        ].copy()

        opponent_by_team = {}
        matchup_by_team = {}
        matchup_number_by_team = {}
        score_by_team = {}

        for _, row in week_games.iterrows():

            team_1 = canon_team(
                row["team_1"]
            )

            team_2 = canon_team(
                row["team_2"]
            )

            matchup_no = int(
                row["matchup_number"]
            )

            matchup_id = (
                f"{year}-W{week:02d}-"
                f"{matchup_no:02d}"
            )

            opponent_by_team[team_1] = team_2
            opponent_by_team[team_2] = team_1

            matchup_by_team[team_1] = matchup_id
            matchup_by_team[team_2] = matchup_id

            matchup_number_by_team[
                team_1
            ] = matchup_no

            matchup_number_by_team[
                team_2
            ] = matchup_no

            score_by_team[team_1] = float(
                row["team_1_score"]
            )

            score_by_team[team_2] = float(
                row["team_2_score"]
            )

        if (
            len(opponent_by_team)
            != EXPECTED_TEAMS
        ):
            fail(
                f"{year} Week {week}: "
                "matchup source mapped "
                f"{len(opponent_by_team)} teams; "
                "expected 12."
            )

        week_rows = []

        for fantasy_team in sorted(
            opponent_by_team
        ):
            team_key = team_key_by_name.get(
                fantasy_team
            )

            if not team_key:
                fail(
                    f"{year} Week {week}: "
                    "no Yahoo team key found for "
                    f"{fantasy_team!r}."
                )

            root = roster_request(
                ctx,
                team_key,
                week,
            )

            rows = parse_roster_players(
                root,
                year=year,
                week=week,
                fantasy_team=fantasy_team,
                opponent=opponent_by_team[
                    fantasy_team
                ],
                matchup_id=matchup_by_team[
                    fantasy_team
                ],
                matchup_number=(
                    matchup_number_by_team[
                        fantasy_team
                    ]
                ),
                team_score=score_by_team[
                    fantasy_team
                ],
                opponent_score=score_by_team[
                    opponent_by_team[
                        fantasy_team
                    ]
                ],
            )

            if not rows:
                fail(
                    f"{year} Week {week}: "
                    "Yahoo API returned no roster "
                    f"players for {fantasy_team}."
                )

            week_rows.extend(rows)

        week_df = pd.DataFrame(
            week_rows
        )

        if (
            week_df["fantasy_team"].nunique()
            != EXPECTED_TEAMS
        ):
            fail(
                f"{year} Week {week}: API lineup "
                "rows contain "
                f"{week_df['fantasy_team'].nunique()} "
                "teams; expected 12."
            )

        starter_counts = (
            week_df[
                week_df["is_starter"]
            ]
            .groupby("fantasy_team")
            .size()
            .reindex(
                sorted(opponent_by_team),
                fill_value=0,
            )
        )

        # Historical Yahoo rosters can legitimately contain an
        # unfilled starting slot. Do not require exactly nine occupied
        # starters. Yahoo's authoritative team score is reconciled below,
        # which is the stronger integrity check.
        #
        # More than nine occupied starters would still indicate malformed
        # roster data and must fail.
        too_many_starters = starter_counts[
            starter_counts > 9
        ]

        if not too_many_starters.empty:
            fail(
                f"{year} Week {week}: Yahoo API returned "
                "more than 9 occupied starters for one or more teams: "
                f"{too_many_starters.to_dict()}"
            )

        short_lineups = starter_counts[
            starter_counts < 9
        ]

        if not short_lineups.empty:
            print(
                f"[INFO] {year} Week {week}: "
                "unfilled starting slot(s): "
                f"{short_lineups.to_dict()}"
            )

        missing_points = week_df[
            week_df["is_starter"]
            & week_df[
                "fantasy_points"
            ].isna()
        ]

        if not missing_points.empty:
            missing = missing_points[
                [
                    "fantasy_team",
                    "player",
                    "lineup_slot",
                ]
            ].to_dict("records")

            fail(
                f"{year} Week {week}: "
                "Yahoo roster API omitted "
                "fantasy points for starters: "
                f"{missing[:12]}"
            )

        starter_totals = (
            week_df[
                week_df["is_starter"]
            ]
            .groupby(
                "fantasy_team"
            )["fantasy_points"]
            .sum()
        )

        score_errors = {}

        for team, expected_score in (
            score_by_team.items()
        ):
            actual = float(
                starter_totals.get(
                    team,
                    float("nan"),
                )
            )

            if (
                pd.isna(actual)
                or abs(
                    actual
                    - expected_score
                )
                > 0.011
            ):
                score_errors[team] = {
                    "starter_sum": (
                        None
                        if pd.isna(actual)
                        else round(actual, 3)
                    ),
                    "yahoo_score": round(
                        expected_score,
                        3,
                    ),
                }

        if score_errors:
            fail(
                f"{year} Week {week}: "
                "starter fantasy-point "
                "reconciliation failed: "
                f"{score_errors}"
            )

        all_rows.extend(
            week_rows
        )

        print(
            f"[PASS] {year} Week {week}: "
            f"{len(week_df)} roster rows / "
            "12 teams / "
            f"{int(week_df['is_starter'].sum())} "
            "starters"
        )

    out = pd.DataFrame(
        all_rows
    )

    duplicate_cols = [
        "year",
        "week",
        "fantasy_team",
        "player",
        "lineup_slot",
    ]

    named = out[
        out["player"]
        .astype(str)
        .str.strip()
        .ne("")
    ].copy()

    duplicates = named.duplicated(
        duplicate_cols,
        keep=False,
    )

    if duplicates.any():
        sample = (
            named.loc[
                duplicates,
                duplicate_cols,
            ]
            .head(20)
            .to_dict("records")
        )

        fail(
            "Duplicate Yahoo API "
            "player-week rows detected: "
            f"{sample}"
        )

    return out


# =====================================================================
# OUTPUT
# =====================================================================

def save_season(
    year: int,
    matchups: pd.DataFrame,
    lineups: pd.DataFrame,
):

    matchup_file = (
        OUTPUT_DIR
        / f"{year}_matchups.csv"
    )

    lineup_file = (
        OUTPUT_DIR
        / f"{year}_weekly_lineups.csv"
    )

    matchups.to_csv(
        matchup_file,
        index=False,
    )

    lineups.to_csv(
        lineup_file,
        index=False,
    )

    print()
    print(
        f"[PASS] Saved {matchup_file}"
    )
    print(
        f"[PASS] Saved {lineup_file}"
    )


# =====================================================================
# MAIN
# =====================================================================

def main():

    parser = argparse.ArgumentParser(
        description="Rebuild historical Yahoo weekly lineups through the API."
    )
    parser.add_argument(
        "--year",
        type=int,
        choices=sorted(SEASONS),
        help="Rebuild only one season. Default: rebuild all configured seasons.",
    )
    args = parser.parse_args()

    seasons_to_run = (
        {args.year: SEASONS[args.year]}
        if args.year is not None
        else SEASONS
    )

    print("=" * 88)
    print(
        "HISTORICAL YAHOO LINEUP API REBUILD"
    )
    print("=" * 88)
    print(
        "Production historical lineup files "
        "will NOT be modified."
    )
    print()

    ctx = Context()

    summary = []

    for year, config in seasons_to_run.items():

        game_key = config["game_key"]
        league_id = config["league_id"]

        league_key = (
            f"{game_key}.l.{league_id}"
        )

        print()
        print("=" * 88)
        print(year)
        print("=" * 88)
        print(
            f"Yahoo game key:   {game_key}"
        )
        print(
            f"Yahoo league key: {league_key}"
        )

        teams = collect_league_teams(
            ctx,
            league_key,
        )

        print(
            f"[PASS] League teams: {len(teams)}"
        )

        matchups = (
            collect_completed_matchups(
                ctx,
                league_key,
                year,
            )
        )

        lineups = collect_weekly_lineups(
            ctx,
            league_key,
            year,
            matchups,
        )

        save_season(
            year,
            matchups,
            lineups,
        )

        summary.append(
            {
                "year": year,
                "weeks": int(
                    matchups["week"].nunique()
                ),
                "matchups": len(matchups),
                "lineup_rows": len(lineups),
                "teams": int(
                    lineups[
                        "fantasy_team"
                    ].nunique()
                ),
            }
        )

    print()
    print("=" * 88)
    print("REBUILD SUMMARY")
    print("=" * 88)

    summary_df = pd.DataFrame(
        summary
    )

    print(
        summary_df.to_string(
            index=False
        )
    )

    print()
    print(
        "HISTORICAL API REBUILD COMPLETE"
    )
    print(
        "No production historical lineup "
        "files were overwritten."
    )


if __name__ == "__main__":
    main()
