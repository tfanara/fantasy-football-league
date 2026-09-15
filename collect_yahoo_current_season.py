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

from season_config import (
    CURRENT_SEASON,
    YAHOO_LEAGUE_IDS,
    REGULAR_SEASON_END_WEEK,
)

ROOT = Path(__file__).resolve().parent
YEAR_DIR = ROOT / "data" / str(CURRENT_SEASON)
PLAYER_WEEK_DIR = ROOT / "data" / "matchups" / "player_week_stats"

EXPECTED_TEAMS = 12
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


def save_json(df: pd.DataFrame, path: Path):
    path.write_text(
        json.dumps(df.where(pd.notna(df), None).to_dict("records"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def collect_transactions_raw(ctx: Context, league_key: str):
    # Preserve the authenticated raw response for the transaction builder.
    # Do not force it into the historical transaction schema until that schema
    # is validated against the current project transaction collector.
    payload = ctx.make_request(f"league/{league_key}/transactions")
    (YEAR_DIR / "transactions_yahoo_raw.xml").write_text(payload, encoding="utf-8")


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

    standings = collect_standings(ctx, league_key, latest_week)
    standings.to_csv(YEAR_DIR / "standings.csv", index=False)
    save_json(standings, YEAR_DIR / "standings.json")
    print(f"[PASS] Standings: 12 teams synchronized through Week {latest_week}")

    collect_transactions_raw(ctx, league_key)
    print("[PASS] Transactions: authenticated raw Yahoo response saved")

    # Player-week collection is deliberately not fabricated here. The current
    # project requires a validated 9-starter/team schema before a week enters
    # build_master_weekly_data.py. Matchup-current analytics can advance now;
    # player-week analytics remain on their independently validated horizon.
    print(
        "[INFO] Player-week lineup horizon unchanged: "
        "no unvalidated roster schema was written."
    )

    if CURRENT_SEASON == 2026 and latest_week >= 1:
        if len(matchups[matchups["week"] == 1]) != 6:
            fail("2026 Week 1 regression failed: expected exactly 6 games.")
        print("[PASS] 2026 Week 1 regression: 6 games / 12 teams")

    print("COLLECTION COMPLETE")


if __name__ == "__main__":
    main()
