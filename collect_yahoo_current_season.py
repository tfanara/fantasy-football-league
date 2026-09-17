from __future__ import annotations

"""
Authenticated Yahoo current-season collector.

Yahoo is authoritative for the active season. Historical 2017-2025 data is
never touched here. The collector writes only current-season source files;
the existing merge/build layer decides which completed weeks enter canonical
analytics.

Requires the already-authorized local yahoofantasy Context().
"""

from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

import pandas as pd
from yahoofantasy import Context

try:
    from team_aliases import canonical_team as shared_canonical_team
except ImportError:
    shared_canonical_team = None

from season_config import (
    CURRENT_SEASON,
    YAHOO_LEAGUE_IDS,
    REGULAR_SEASON_END_WEEK,
)

ROOT = Path(__file__).resolve().parent
YEAR_DIR = ROOT / "data" / str(CURRENT_SEASON)
PLAYER_WEEK_DIR = ROOT / "data" / "matchups" / "player_week_stats"

EXPECTED_TEAMS = 12
EXPECTED_MATCHUPS_PER_WEEK = 6
EXPECTED_MATCHUPS = 6

# Yahoo's 2026 NFL game key was verified directly from the authenticated API.
# Future seasons are discovered dynamically from Yahoo rather than guessed.
KNOWN_GAME_KEYS = {2026: "470"}

TEAM_ALIASES = {
    "Ginger FC": "Ginger FC 🏆🏆",
    "Ginger FC 🏆🏆": "Ginger FC 🏆🏆",
    "PickUpYourBratsMalle": "ThreatLevelMidnight",
    "Little Red Fournette": "Post Mahomes",
    "Ur The Best Bellows": "Joe Mantegna",
    "You Better Park It": "Buttermilk Puuump",
    "Buttermilk Pump": "Buttermilk Puuump",
}

NS = {"f": "http://fantasysports.yahooapis.com/fantasy/v2/base.rng"}


def fail(message: str):
    raise RuntimeError(message)


def canon_team(name: str) -> str:
    name = str(name).strip()
    if shared_canonical_team is not None:
        name = str(shared_canonical_team(name)).strip()
    return TEAM_ALIASES.get(name, name)


def text(node, path: str, default=None):
    found = node.find(path, NS)
    if found is None or found.text is None:
        return default
    return found.text.strip()


def as_float(value):
    if value in (None, ""):
        return None
    return float(value)


def as_int(value):
    if value in (None, ""):
        return None
    return int(value)


def parse_xml(payload: str) -> ET.Element:
    if not isinstance(payload, str) or "<fantasy_content" not in payload:
        fail("Yahoo returned an unexpected non-XML response.")
    return ET.fromstring(payload)


def discover_game_key(ctx: Context, season: int) -> str:
    if season in KNOWN_GAME_KEYS:
        return KNOWN_GAME_KEYS[season]

    root = parse_xml(ctx.make_request("games;game_codes=nfl"))
    for game in root.findall(".//f:game", NS):
        if text(game, "f:season") == str(season):
            key = text(game, "f:game_key")
            if key:
                return key
    fail(f"Yahoo did not return an NFL game key for {season}.")


def parse_scoreboard(root: ET.Element, week: int) -> list[dict]:
    league_season = text(root, ".//f:league/f:season")
    if league_season != str(CURRENT_SEASON):
        fail(f"Yahoo scoreboard season is {league_season}; expected {CURRENT_SEASON}.")

    matchups = root.findall(".//f:scoreboard/f:matchups/f:matchup", NS)
    rows = []

    for idx, matchup in enumerate(matchups, start=1):
        status = text(matchup, "f:status")
        is_playoffs = text(matchup, "f:is_playoffs", "0")
        teams = matchup.findall("f:teams/f:team", NS)
        if len(teams) != 2:
            fail(f"Week {week} matchup {idx} returned {len(teams)} teams; expected 2.")

        parsed = []
        for team in teams:
            parsed.append({
                "key": text(team, "f:team_key"),
                "name": canon_team(text(team, "f:name", "")),
                "score": as_float(text(team, "f:team_points/f:total")),
                "projected": as_float(text(team, "f:team_projected_points/f:total")),
            })

        winner_key = text(matchup, "f:winner_team_key")
        tied = text(matchup, "f:is_tied", "0") == "1"

        if tied:
            winner = loser = None
        elif winner_key:
            winner = next((t["name"] for t in parsed if t["key"] == winner_key), None)
            loser = next((t["name"] for t in parsed if t["key"] != winner_key), None)
        else:
            winner = loser = None

        s1, s2 = parsed[0]["score"], parsed[1]["score"]
        margin = abs(s1 - s2) if s1 is not None and s2 is not None else None

        rows.append({
            "year": CURRENT_SEASON,
            "week": week,
            "team_1": parsed[0]["name"],
            "team_2": parsed[1]["name"],
            "team_1_score": s1,
            "team_2_score": s2,
            "team_1_projected": parsed[0]["projected"],
            "team_2_projected": parsed[1]["projected"],
            "winner": winner,
            "loser": loser,
            "margin": margin,
            "is_tied": tied,
            "is_playoffs": str(is_playoffs) == "1",
            "status": status,
        })
    return rows


def collect_matchups(ctx: Context, league_key: str) -> tuple[pd.DataFrame, int]:
    all_rows = []
    latest_complete = 0

    for week in range(1, REGULAR_SEASON_END_WEEK[CURRENT_SEASON] + 1):
        root = parse_xml(ctx.make_request(f"league/{league_key}/scoreboard;week={week}"))
        rows = parse_scoreboard(root, week)
        df = pd.DataFrame(rows)

        complete = (
            len(df) == EXPECTED_MATCHUPS
            and set(df["status"].astype(str)) == {"postevent"}
            and df["team_1_score"].notna().all()
            and df["team_2_score"].notna().all()
            and pd.concat([df["team_1"], df["team_2"]]).nunique() == EXPECTED_TEAMS
            and not df["is_playoffs"].astype(bool).any()
        )

        if not complete:
            break

        if week != latest_complete + 1:
            fail(f"Yahoo completed-week sequence is not contiguous at Week {week}.")
        latest_complete = week
        all_rows.extend(rows)

    columns = [
        "year", "week", "team_1", "team_2",
        "team_1_score", "team_2_score",
        "team_1_projected", "team_2_projected",
        "winner", "loser", "margin", "is_tied", "is_playoffs", "status",
    ]
    out = pd.DataFrame(all_rows, columns=columns)

    expected = latest_complete * EXPECTED_MATCHUPS
    if len(out) != expected:
        fail(f"Collected {len(out)} games; expected {expected}.")
    return out, latest_complete



def collect_upcoming_matchups(
    ctx: Context,
    league_key: str,
    latest_complete: int,
) -> pd.DataFrame:
    """
    Collect only the next unplayed regular-season matchup week from Yahoo.

    Upcoming games stay separate from completed matchups so they can never
    enter records, standings, luck, schedule-swap, or other completed-game
    analytics by accident.
    """
    next_week = latest_complete + 1
    regular_season_end = REGULAR_SEASON_END_WEEK[CURRENT_SEASON]

    columns = [
        "year", "week", "team_1", "team_2",
        "team_1_projected", "team_2_projected",
        "status", "is_playoffs", "source",
    ]

    if next_week > regular_season_end:
        return pd.DataFrame(columns=columns)

    root = parse_xml(
        ctx.make_request(
            f"league/{league_key}/scoreboard;week={next_week}"
        )
    )
    rows = parse_scoreboard(root, next_week)
    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=columns)

    if len(df) != EXPECTED_MATCHUPS_PER_WEEK:
        fail(
            f"Yahoo upcoming Week {next_week} returned {len(df)} matchups; "
            f"expected {EXPECTED_MATCHUPS_PER_WEEK}."
        )

    teams = pd.concat([df["team_1"], df["team_2"]], ignore_index=True)
    if teams.nunique() != EXPECTED_TEAMS:
        fail(
            f"Yahoo upcoming Week {next_week} returned "
            f"{teams.nunique()} unique teams; expected {EXPECTED_TEAMS}."
        )

    if df["is_playoffs"].astype(bool).any():
        fail(
            f"Yahoo upcoming Week {next_week} unexpectedly contains "
            "playoff matchups."
        )

    # This file is specifically for future schedule context. If Yahoo says the
    # next week is already postevent, do not mislabel it as upcoming.
    if set(df["status"].astype(str)) == {"postevent"}:
        fail(
            f"Yahoo Week {next_week} is already complete but was not included "
            "in the completed-week collection horizon."
        )

    out = df[
        [
            "year", "week", "team_1", "team_2",
            "team_1_projected", "team_2_projected",
            "status", "is_playoffs",
        ]
    ].copy()
    out["source"] = "yahoo_fantasy_api"

    return out[columns]

def parse_standings(root: ET.Element) -> pd.DataFrame:
    rows = []
    for team in root.findall(".//f:standings/f:teams/f:team", NS):
        wins = as_int(text(team, "f:team_standings/f:outcome_totals/f:wins", "0")) or 0
        losses = as_int(text(team, "f:team_standings/f:outcome_totals/f:losses", "0")) or 0
        ties = as_int(text(team, "f:team_standings/f:outcome_totals/f:ties", "0")) or 0
        rows.append({
            "rank": as_int(text(team, "f:team_standings/f:rank")),
            "team": canon_team(text(team, "f:name", "")),
            "record": f"{wins}-{losses}-{ties}",
            "points_for": as_float(text(team, "f:team_points/f:total")),
            "points_against": as_float(text(team, "f:team_standings/f:points_against")),
            "streak": text(team, "f:team_standings/f:streak/f:type"),
            "waiver": as_int(text(team, "f:waiver_priority")),
            "moves": as_int(text(team, "f:number_of_moves")),
            "year": CURRENT_SEASON,
            "league_id": str(YAHOO_LEAGUE_IDS[CURRENT_SEASON]),
        })
    out = pd.DataFrame(rows)
    if len(out) != EXPECTED_TEAMS or out["team"].nunique() != EXPECTED_TEAMS:
        fail(f"Yahoo standings returned {len(out)} rows / {out['team'].nunique()} unique teams; expected 12/12.")
    return out


def collect_standings(ctx: Context, league_key: str, latest_week: int) -> pd.DataFrame:
    root = parse_xml(ctx.make_request(f"league/{league_key}/standings"))
    out = parse_standings(root)

    games = out["record"].str.extract(r"^(\d+)-(\d+)-(\d+)$").astype(int).sum(axis=1)
    if not games.eq(latest_week).all():
        bad = out.loc[~games.eq(latest_week), ["team", "record"]].to_dict("records")
        fail(f"Yahoo standings are not synchronized to completed Week {latest_week}: {bad}")
    return out



def collect_league_teams(ctx: Context, league_key: str) -> pd.DataFrame:
    """Get the 12 current Yahoo team keys/names directly from the Fantasy API."""
    root = parse_xml(ctx.make_request(f"league/{league_key}/teams"))
    rows = []

    for team in root.findall(".//f:league/f:teams/f:team", NS):
        key = text(team, "f:team_key")
        name = canon_team(text(team, "f:name", ""))
        if key and name:
            rows.append({"team_key": key, "fantasy_team": name})

    out = pd.DataFrame(rows).drop_duplicates(subset=["team_key"])

    if len(out) != EXPECTED_TEAMS or out["fantasy_team"].nunique() != EXPECTED_TEAMS:
        fail(
            "Yahoo league teams endpoint returned "
            f"{len(out)} rows / {out['fantasy_team'].nunique() if not out.empty else 0} "
            "unique teams; expected 12/12."
        )

    return out


def roster_request(ctx: Context, team_key: str, week: int) -> ET.Element:
    """
    Retrieve a weekly roster through Yahoo's authenticated Fantasy API.

    Yahoo has exposed roster/player subresources slightly differently across
    versions, so try the richest API form first and fall back to the base
    weekly roster resource. No browser scraping is used.
    """
    candidates = [
        f"team/{team_key}/roster;week={week}/players;out=stats",
        f"team/{team_key}/roster;week={week}/players",
        f"team/{team_key}/roster;week={week}",
    ]

    errors = []
    for uri in candidates:
        try:
            root = parse_xml(ctx.make_request(uri))
            players = root.findall(".//f:roster/f:players/f:player", NS)
            if players:
                return root
            errors.append(f"{uri}: response contained no roster players")
        except Exception as exc:
            errors.append(f"{uri}: {type(exc).__name__}: {exc}")

    fail(
        f"Yahoo API did not return Week {week} roster players for {team_key}. "
        + " | ".join(errors)
    )


def parse_roster_players(
    root: ET.Element,
    *,
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
        root.findall(".//f:roster/f:players/f:player", NS),
        start=1,
    ):
        player_name = text(player, "f:name/f:full", "")
        if not player_name:
            continue

        lineup_slot = (
            text(player, "f:selected_position/f:position", "")
            or text(player, "f:display_position", "")
        ).upper()

        is_bench = lineup_slot in {"BN", "BENCH"}
        is_ir = lineup_slot in {"IR", "IR+", "NA"}
        is_starter = bool(lineup_slot) and not is_bench and not is_ir

        fantasy_points = as_float(text(player, "f:player_points/f:total"))
        projected_points = as_float(
            text(player, "f:player_projected_points/f:total")
        )

        rows.append({
            "year": CURRENT_SEASON,
            "week": week,
            "table_index": None,
            "row_index": idx,
            "side": "api",
            "fantasy_team": canon_team(fantasy_team),
            "opponent": canon_team(opponent),
            "matchup_id": matchup_id,
            "matchup_number": matchup_number,
            "team_score": team_score,
            "opponent_score": opponent_score,
            "player": player_name,
            "player_position": text(player, "f:display_position", ""),
            "lineup_slot": lineup_slot,
            "is_starter": is_starter,
            "is_bench": is_bench,
            "is_ir": is_ir,
            "projected_points": projected_points,
            "fantasy_points": fantasy_points,
            "stat_summary": "",
            "raw_player_text": player_name,
            "raw_position": text(player, "f:display_position", ""),
            "raw_cells": "",
            "player_key": text(player, "f:player_key"),
            "player_id": text(player, "f:player_id"),
            "nfl_team": text(player, "f:editorial_team_abbr", ""),
            "source": "yahoo_fantasy_api",
        })

    return rows


def collect_weekly_lineups_api(
    ctx: Context,
    league_key: str,
    matchups: pd.DataFrame,
    latest_week: int,
) -> pd.DataFrame:
    """
    Collect every completed current-season weekly roster directly from Yahoo.

    The output intentionally matches the established <YEAR>_weekly_lineups.csv
    core schema so validate_weekly_lineups.py and build_master_weekly_data.py
    remain the gatekeepers.
    """
    if latest_week <= 0:
        return pd.DataFrame()

    teams = collect_league_teams(ctx, league_key)
    team_key_by_name = dict(
        zip(teams["fantasy_team"], teams["team_key"])
    )

    all_rows = []

    for week in range(1, latest_week + 1):
        week_games = matchups[matchups["week"] == week].copy()

        opponent_by_team = {}
        matchup_by_team = {}
        matchup_number_by_team = {}
        score_by_team = {}

        for matchup_number, row in week_games.reset_index(drop=True).iterrows():
            team_1 = canon_team(row["team_1"])
            team_2 = canon_team(row["team_2"])
            matchup_no = matchup_number + 1
            matchup_id = (
                f"{CURRENT_SEASON}-W{week:02d}-"
                f"{matchup_no:02d}"
            )

            opponent_by_team[team_1] = team_2
            opponent_by_team[team_2] = team_1
            matchup_by_team[team_1] = matchup_id
            matchup_by_team[team_2] = matchup_id
            matchup_number_by_team[team_1] = matchup_no
            matchup_number_by_team[team_2] = matchup_no
            score_by_team[team_1] = float(row["team_1_score"])
            score_by_team[team_2] = float(row["team_2_score"])

        if len(opponent_by_team) != EXPECTED_TEAMS:
            fail(
                f"Week {week}: matchup source mapped "
                f"{len(opponent_by_team)} teams; expected 12."
            )

        week_rows = []

        for fantasy_team in sorted(opponent_by_team):
            team_key = team_key_by_name.get(fantasy_team)
            if not team_key:
                fail(
                    f"Week {week}: no Yahoo team key found for "
                    f"{fantasy_team!r}."
                )

            root = roster_request(ctx, team_key, week)
            rows = parse_roster_players(
                root,
                week=week,
                fantasy_team=fantasy_team,
                opponent=opponent_by_team[fantasy_team],
                matchup_id=matchup_by_team[fantasy_team],
                matchup_number=matchup_number_by_team[fantasy_team],
                team_score=score_by_team[fantasy_team],
                opponent_score=score_by_team[
                    opponent_by_team[fantasy_team]
                ],
            )

            if not rows:
                fail(
                    f"Week {week}: Yahoo API returned no roster players "
                    f"for {fantasy_team}."
                )

            week_rows.extend(rows)

        week_df = pd.DataFrame(week_rows)

        # Structural validation before writing anything.
        if week_df["fantasy_team"].nunique() != EXPECTED_TEAMS:
            fail(
                f"Week {week}: API lineup rows contain "
                f"{week_df['fantasy_team'].nunique()} teams; expected 12."
            )

        starter_counts = (
            week_df[week_df["is_starter"]]
            .groupby("fantasy_team")
            .size()
            .reindex(sorted(opponent_by_team), fill_value=0)
        )

        if not starter_counts.eq(9).all():
            fail(
                f"Week {week}: Yahoo API starter counts are not 9/team: "
                f"{starter_counts.to_dict()}"
            )

        # A completed week is not allowed into the player pipeline unless
        # starter fantasy points are actually present and reconcile to Yahoo's
        # authoritative team scores.
        if week_df.loc[week_df["is_starter"], "fantasy_points"].isna().any():
            missing = week_df.loc[
                week_df["is_starter"] & week_df["fantasy_points"].isna(),
                ["fantasy_team", "player", "lineup_slot"],
            ].to_dict("records")
            fail(
                f"Week {week}: Yahoo roster API omitted fantasy points for "
                f"one or more starters: {missing[:12]}"
            )

        starter_totals = (
            week_df[week_df["is_starter"]]
            .groupby("fantasy_team")["fantasy_points"]
            .sum()
        )

        expected_scores = {}
        for _, row in week_games.iterrows():
            expected_scores[canon_team(row["team_1"])] = float(row["team_1_score"])
            expected_scores[canon_team(row["team_2"])] = float(row["team_2_score"])

        score_errors = {}
        for team, expected_score in expected_scores.items():
            actual = float(starter_totals.get(team, float("nan")))
            if pd.isna(actual) or abs(actual - expected_score) > 0.011:
                score_errors[team] = {
                    "starter_sum": None if pd.isna(actual) else round(actual, 3),
                    "yahoo_score": round(expected_score, 3),
                }

        if score_errors:
            fail(
                f"Week {week}: starter fantasy-point reconciliation failed: "
                f"{score_errors}"
            )

        all_rows.extend(week_rows)
        print(
            f"[PASS] Player lineups Week {week}: "
            f"{len(week_df)} roster rows / 12 teams / "
            f"{int(week_df['is_starter'].sum())} starters"
        )

    out = pd.DataFrame(all_rows)

    duplicate_cols = [
        "year", "week", "fantasy_team", "player", "lineup_slot"
    ]
    named = out[out["player"].astype(str).str.strip().ne("")].copy()
    duplicates = named.duplicated(duplicate_cols, keep=False)
    if duplicates.any():
        sample = named.loc[duplicates, duplicate_cols].head(20).to_dict("records")
        fail(f"Duplicate Yahoo API player-week rows detected: {sample}")

    return out


def build_player_pipeline_matchups(matchups: pd.DataFrame) -> pd.DataFrame:
    """
    Translate the authoritative current-season Yahoo matchup rows into the
    long-established player-week validator schema.

    This is a derived compatibility file, not a second source of truth.
    """
    rows = []

    for week, week_df in matchups.groupby("week", sort=True):
        week_df = week_df.reset_index(drop=True)

        for idx, row in week_df.iterrows():
            matchup_number = idx + 1
            rows.append({
                "year": CURRENT_SEASON,
                "week": int(week),
                "matchup_number": matchup_number,
                "left_team": canon_team(row["team_1"]),
                "right_team": canon_team(row["team_2"]),
                "left_score": float(row["team_1_score"]),
                "right_score": float(row["team_2_score"]),
                "matchup_id": (
                    f"{CURRENT_SEASON}-W{int(week):02d}-"
                    f"{matchup_number:02d}"
                ),
                "source": "yahoo_fantasy_api",
            })

    out = pd.DataFrame(rows)

    if not out.empty:
        counts = out.groupby("week").size()
        if not counts.eq(EXPECTED_MATCHUPS_PER_WEEK).all():
            fail(
                "Player-pipeline matchup compatibility file does not contain "
                f"6 matchups in every completed week: {counts.to_dict()}"
            )

        team_rows = pd.concat(
            [
                out[["week", "left_team"]].rename(
                    columns={"left_team": "team"}
                ),
                out[["week", "right_team"]].rename(
                    columns={"right_team": "team"}
                ),
            ],
            ignore_index=True,
        )
        team_counts = team_rows.groupby("week")["team"].nunique()
        if not team_counts.eq(EXPECTED_TEAMS).all():
            fail(
                "Player-pipeline matchup compatibility file does not contain "
                f"12 unique teams in every week: {team_counts.to_dict()}"
            )

    return out

def save_json(df: pd.DataFrame, path: Path):
    path.write_text(
        json.dumps(df.where(pd.notna(df), None).to_dict("records"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def collect_transactions(ctx: Context, league_key: str) -> pd.DataFrame:
    """
    Collect and normalize successful current-season Yahoo player transactions.

    The authenticated raw XML is always preserved. Commissioner-only actions
    without player movement remain in the raw XML but are excluded from the
    normalized player transaction dataset.
    """
    payload = ctx.make_request(f"league/{league_key}/transactions")
    (YEAR_DIR / "transactions_yahoo_raw.xml").write_text(payload, encoding="utf-8")

    root = parse_xml(payload)
    rows = []

    for transaction in root.findall(".//f:transaction", NS):
        transaction_id = text(transaction, "f:transaction_id")
        transaction_key = text(transaction, "f:transaction_key")
        transaction_type = text(transaction, "f:type", "")
        status = text(transaction, "f:status", "")
        timestamp = as_int(text(transaction, "f:timestamp"))

        if status != "successful":
            continue

        players = transaction.findall("f:players/f:player", NS)
        if not players:
            continue

        added_player = None
        dropped_player = None
        team = None
        acquisition_type = None

        for player in players:
            player_name = text(player, "f:name/f:full", "")
            transaction_data = player.find("f:transaction_data", NS)
            if transaction_data is None:
                continue

            action = text(transaction_data, "f:type", "")
            source_type = text(transaction_data, "f:source_type", "")
            source_team_name = text(transaction_data, "f:source_team_name")
            destination_team_name = text(
                transaction_data, "f:destination_team_name"
            )

            if action == "add":
                added_player = player_name or None
                if destination_team_name:
                    team = canon_team(destination_team_name)

                if source_type == "waivers":
                    acquisition_type = "waiver"
                elif source_type == "freeagents":
                    acquisition_type = "free_agent"
                else:
                    acquisition_type = source_type or None

            elif action == "drop":
                dropped_player = player_name or None
                if team is None and source_team_name:
                    team = canon_team(source_team_name)

        if not team:
            fail(
                f"Yahoo transaction {transaction_id} contains player movement "
                "but no fantasy team could be identified."
            )

        rows.append({
            "year": CURRENT_SEASON,
            "transaction_id": as_int(transaction_id),
            "transaction_key": transaction_key,
            "timestamp": timestamp,
            "date": (
                pd.to_datetime(timestamp, unit="s", utc=True)
                .tz_convert("America/New_York")
                .isoformat()
                if timestamp is not None
                else None
            ),
            "team": team,
            "transaction_type": transaction_type,
            "added_player": added_player,
            "acquisition_type": acquisition_type,
            "dropped_player": dropped_player,
            "status": status,
            "source": "yahoo_fantasy_api",
        })

    columns = [
        "year", "transaction_id", "transaction_key", "timestamp", "date",
        "team", "transaction_type", "added_player", "acquisition_type",
        "dropped_player", "status", "source",
    ]
    out = pd.DataFrame(rows, columns=columns)

    if not out.empty:
        if out["transaction_id"].duplicated().any():
            duplicates = out.loc[
                out["transaction_id"].duplicated(keep=False),
                ["transaction_id", "team", "transaction_type"],
            ].to_dict("records")
            fail(f"Duplicate Yahoo transaction IDs detected: {duplicates}")

        out = out.sort_values(
            ["timestamp", "transaction_id"],
            ascending=[True, True],
        ).reset_index(drop=True)

    return out


def main():
    print("=" * 88)
    print(f"COLLECTING YAHOO CURRENT SEASON — {CURRENT_SEASON}")
    print("=" * 88)

    YEAR_DIR.mkdir(parents=True, exist_ok=True)
    PLAYER_WEEK_DIR.mkdir(parents=True, exist_ok=True)

    ctx = Context()
    game_key = discover_game_key(ctx, CURRENT_SEASON)
    league_key = f"{game_key}.l.{YAHOO_LEAGUE_IDS[CURRENT_SEASON]}"

    print(f"Yahoo game key:   {game_key}")
    print(f"Yahoo league key: {league_key}")

    matchups, latest_week = collect_matchups(ctx, league_key)
    matchups.to_csv(YEAR_DIR / "matchups.csv", index=False)
    save_json(matchups, YEAR_DIR / "matchups.json")
    print(f"[PASS] Matchups: {len(matchups)} games through completed Week {latest_week}")

    # Keep the next unplayed Yahoo matchup week in its own source file.
    upcoming = collect_upcoming_matchups(
        ctx,
        league_key,
        latest_week,
    )
    upcoming_csv = YEAR_DIR / "upcoming_matchups.csv"
    upcoming_json = YEAR_DIR / "upcoming_matchups.json"
    upcoming.to_csv(upcoming_csv, index=False)
    save_json(upcoming, upcoming_json)

    if upcoming.empty:
        print("[INFO] Upcoming matchups: no next regular-season week available")
    else:
        upcoming_week = int(upcoming["week"].iloc[0])
        print(
            f"[PASS] Upcoming matchups: {len(upcoming)} games for "
            f"Week {upcoming_week} from Yahoo API"
        )
        print(f"[PASS] Wrote {upcoming_csv.relative_to(ROOT)}")
        print(f"[PASS] Wrote {upcoming_json.relative_to(ROOT)}")

    standings = collect_standings(ctx, league_key, latest_week)
    standings.to_csv(YEAR_DIR / "standings.csv", index=False)
    save_json(standings, YEAR_DIR / "standings.json")
    print(f"[PASS] Standings: 12 teams synchronized through Week {latest_week}")

    transactions = collect_transactions(ctx, league_key)
    transactions_csv = YEAR_DIR / "transactions.csv"
    transactions_json = YEAR_DIR / "transactions.json"
    transactions.to_csv(transactions_csv, index=False)
    save_json(transactions, transactions_json)

    print(
        f"[PASS] Transactions: {len(transactions)} successful "
        "player transactions normalized"
    )
    print("[PASS] Raw Yahoo transaction response preserved")
    print(f"[PASS] Wrote {transactions_csv.relative_to(ROOT)}")
    print(f"[PASS] Wrote {transactions_json.relative_to(ROOT)}")

    # Create the matchup companion expected by validate_weekly_lineups.py.
    # It is derived from the same authoritative Yahoo API matchup dataframe.
    player_matchups = build_player_pipeline_matchups(matchups)
    player_matchup_csv = (
        PLAYER_WEEK_DIR / f"{CURRENT_SEASON}_matchups.csv"
    )
    player_matchup_json = (
        PLAYER_WEEK_DIR / f"{CURRENT_SEASON}_matchups.json"
    )
    player_matchups.to_csv(player_matchup_csv, index=False)
    save_json(player_matchups, player_matchup_json)

    print(
        f"[PASS] Player-pipeline matchups: {len(player_matchups)} games "
        f"through completed Week {latest_week}"
    )
    print(f"[PASS] Wrote {player_matchup_csv.relative_to(ROOT)}")
    print(f"[PASS] Wrote {player_matchup_json.relative_to(ROOT)}")

    # Collect completed-week player lineups from Yahoo's authenticated API.
    # These files still must pass validate_weekly_lineups.py before they enter
    # the canonical master/analytics pipeline.
    lineups = collect_weekly_lineups_api(
        ctx,
        league_key,
        matchups,
        latest_week,
    )

    lineup_csv = PLAYER_WEEK_DIR / f"{CURRENT_SEASON}_weekly_lineups.csv"
    lineup_json = PLAYER_WEEK_DIR / f"{CURRENT_SEASON}_weekly_lineups.json"

    lineups.to_csv(lineup_csv, index=False)
    save_json(lineups, lineup_json)

    print(
        f"[PASS] Player lineups: {len(lineups)} API roster rows "
        f"through completed Week {latest_week}"
    )
    print(f"[PASS] Wrote {lineup_csv.relative_to(ROOT)}")
    print(f"[PASS] Wrote {lineup_json.relative_to(ROOT)}")

    if CURRENT_SEASON == 2026 and latest_week >= 1:
        if len(matchups[matchups["week"] == 1]) != 6:
            fail("2026 Week 1 regression failed: expected exactly 6 games.")
        print("[PASS] 2026 Week 1 regression: 6 games / 12 teams")

    print("COLLECTION COMPLETE")


if __name__ == "__main__":
    main()