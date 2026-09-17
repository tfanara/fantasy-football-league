#!/usr/bin/env python3
"""
Generate validated editorial commentary for weekly fantasy-football Power Rankings.

Inputs
------
data/analysis/power_rankings_weekly.csv
data/news/{year}/week_{week:02d}_context.json

Output
------
data/power_rankings/{year}/week_{week:02d}_commentary.json

Usage
-----
python generate_power_rankings_commentary.py
python generate_power_rankings_commentary.py 2026 1

The generator deliberately does NOT expose the Power Rankings formula to Gemini.
Ranking calculations remain deterministic and separate from editorial commentary.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
POWER_RANKINGS = DATA / "analysis" / "power_rankings_weekly.csv"

DEFAULT_MODEL = "gemini-3.5-flash-lite"
MAX_ATTEMPTS = 3


def clean(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    value = str(value).strip()
    return value or None


def number(value, digits=2):
    try:
        if pd.isna(value):
            return None
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def integer(value):
    try:
        if pd.isna(value):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def get_client():
    if "GEMINI_API_KEY" not in st.secrets:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured in .streamlit/secrets.toml."
        )
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


def latest_snapshot():
    if not POWER_RANKINGS.exists():
        raise FileNotFoundError(f"Missing required file: {POWER_RANKINGS}")

    df = pd.read_csv(POWER_RANKINGS)
    required = {"year", "through_week"}
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(
            f"{POWER_RANKINGS} is missing required columns: {sorted(missing)}"
        )

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["through_week"] = pd.to_numeric(df["through_week"], errors="coerce")
    df = df.dropna(subset=["year", "through_week"])

    if df.empty:
        raise RuntimeError("Power Rankings file contains no usable snapshots.")

    last = (
        df[["year", "through_week"]]
        .drop_duplicates()
        .sort_values(["year", "through_week"])
        .iloc[-1]
    )
    return int(last["year"]), int(last["through_week"])


def ranking_snapshot(year, week):
    df = pd.read_csv(POWER_RANKINGS)

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["through_week"] = pd.to_numeric(df["through_week"], errors="coerce")

    out = df[(df["year"] == year) & (df["through_week"] == week)].copy()

    if out.empty:
        raise RuntimeError(
            f"No Power Rankings snapshot found for {year} Week {week}."
        )

    team_col = "fantasy_team" if "fantasy_team" in out.columns else "team"
    if team_col not in out.columns:
        raise RuntimeError("Power Rankings file has no team column.")

    if "power_rank" not in out.columns:
        raise RuntimeError("Power Rankings file has no power_rank column.")

    out = out.sort_values("power_rank").reset_index(drop=True)

    if len(out) != 12:
        raise RuntimeError(
            f"Expected 12 Power Rankings teams; found {len(out)}."
        )

    if out[team_col].astype(str).duplicated().any():
        raise RuntimeError("Duplicate teams found in Power Rankings snapshot.")

    return out, team_col


def matchup_for_team(packet, team):
    for game in packet.get("matchups", []):
        winner = game.get("winner")
        loser = game.get("loser")
        if team == winner:
            return {
                "result": "win",
                "opponent": loser,
                "team_score": game.get("winner_score"),
                "opponent_score": game.get("loser_score"),
                "margin": game.get("margin"),
                "historical_h2h_before_game": game.get(
                    "historical_h2h_before_game"
                ),
            }
        if team == loser:
            return {
                "result": "loss",
                "opponent": winner,
                "team_score": game.get("loser_score"),
                "opponent_score": game.get("winner_score"),
                "margin": (
                    -float(game.get("margin"))
                    if game.get("margin") is not None
                    else None
                ),
                "historical_h2h_before_game": game.get(
                    "historical_h2h_before_game"
                ),
            }
    return None


def managerial_for_team(packet, team):
    section = packet.get("managerial_decisions", {})
    for row in section.get("decisions", []):
        if row.get("team") == team:
            return row
    return None


def luck_for_team(packet, team):
    section = packet.get("bad_beats", {})

    for row in section.get("bad_beats", []):
        if row.get("team") == team:
            return {"classification": "bad_beat", **row}

    for row in section.get("lucky_wins", []):
        if row.get("team") == team:
            return {"classification": "lucky_win", **row}

    return None


def transactions_for_team(packet, team):
    section = packet.get("recent_transactions", {})
    by_team = section.get("team_transactions", {})
    rows = by_team.get(team, [])
    return rows[-4:]


def milestones_for_team(packet, team):
    section = packet.get("records_and_milestones", {})
    found = []

    for key in [
        "records_broken",
        "records_tied",
        "near_records",
        "career_milestones",
    ]:
        for row in section.get(key, []):
            if isinstance(row, dict) and row.get("team") == team:
                found.append({"category": key, **row})

    for row in packet.get("streaks_snapped", []):
        if isinstance(row, dict) and row.get("team") == team:
            found.append({"category": "streak_snapped", **row})

    return found


def standings_for_team(packet, team):
    for row in packet.get("standings", []):
        if row.get("team") == team:
            return row
    return None


def season_context_for_team(packet, team):
    for row in packet.get("season_team_context", []):
        if row.get("team") == team:
            return row
    return None


def relevant_player_facts(packet, team):
    section = packet.get("player_facts", {})
    facts = []

    top = section.get("top_starter")
    if isinstance(top, dict) and top.get("team") == team:
        facts.append({"kind": "top_starter", **top})

    for row in section.get("top_starters", []):
        if isinstance(row, dict) and row.get("team") == team:
            facts.append({"kind": "top_starter_list", **row})

    leaders = section.get("position_leaders", {})
    if isinstance(leaders, dict):
        iterable = leaders.values()
    else:
        iterable = leaders if isinstance(leaders, list) else []

    for row in iterable:
        if isinstance(row, dict) and row.get("team") == team:
            facts.append({"kind": "position_leader", **row})

    # De-duplicate identical player/points facts.
    unique = []
    seen = set()
    for row in facts:
        key = (
            row.get("player"),
            row.get("team"),
            row.get("position"),
            row.get("points"),
        )
        if key not in seen:
            seen.add(key)
            unique.append(row)

    return unique[:5]


def build_team_evidence(rank_row, team_col, packet):
    team = str(rank_row[team_col])

    ranking = {
        "power_rank": integer(rank_row.get("power_rank")),
        "rank_change": integer(rank_row.get("rank_change")),
        "record": clean(rank_row.get("record")),
        "avg_points": number(rank_row.get("avg_points")),
        "scoring_rank": integer(rank_row.get("scoring_rank")),
        "all_play_rank": integer(rank_row.get("all_play_rank")),
        "efficiency_rank": integer(rank_row.get("efficiency_rank")),
        "lineup_efficiency_pct": number(
            rank_row.get("lineup_efficiency_pct")
        ),
    }

    # Intentionally omitted:
    # power_score, component weights, normalized component scores, and formula.
    return {
        "team": team,
        "ranking": ranking,
        "latest_matchup": matchup_for_team(packet, team),
        "player_facts": relevant_player_facts(packet, team),
        "managerial_decision": managerial_for_team(packet, team),
        "luck_context": luck_for_team(packet, team),
        "recent_transactions": transactions_for_team(packet, team),
        "milestones_and_streaks": milestones_for_team(packet, team),
        "standings": standings_for_team(packet, team),
        "season_context": season_context_for_team(packet, team),
    }


def build_evidence(year, week):
    rankings, team_col = ranking_snapshot(year, week)

    context_path = (
        DATA / "news" / str(year) / f"week_{week:02d}_context.json"
    )
    packet = load_json(context_path)

    if packet.get("schema_version") != 4:
        raise RuntimeError(
            "Power Rankings commentary requires weekly intelligence schema v4."
        )

    if int(packet.get("season")) != year or int(packet.get("week")) != week:
        raise RuntimeError(
            "Power Rankings snapshot and weekly intelligence packet do not match."
        )

    teams = [
        build_team_evidence(row, team_col, packet)
        for _, row in rankings.iterrows()
    ]

    return {
        "schema_version": 1,
        "season": year,
        "week": week,
        "editorial_guardrail": (
            "Commentary may add satire and opinion, but every factual claim "
            "must be supported by this evidence packet."
        ),
        "teams": teams,
    }


def response_schema():
    return {
        "type": "OBJECT",
        "properties": {
            "schema_version": {"type": "INTEGER"},
            "season": {"type": "INTEGER"},
            "week": {"type": "INTEGER"},
            "commentary": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "power_rank": {"type": "INTEGER"},
                        "team": {"type": "STRING"},
                        "commentary": {"type": "STRING"},
                        "evidence_tags": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                        },
                    },
                    "required": [
                        "power_rank",
                        "team",
                        "commentary",
                        "evidence_tags",
                    ],
                },
            },
        },
        "required": [
            "schema_version",
            "season",
            "week",
            "commentary",
        ],
    }


def prompt_for(evidence):
    return f"""
You are the editorial voice for a private fantasy-football league's weekly
POWER RANKINGS.

Write ONE short commentary blurb for EACH of the 12 ranked teams.

STYLE:
- Knowledgeable, punchy, entertaining, and concise.
- Light-to-ruthless fantasy-football satire is welcome when supported.
- Usually 1-2 sentences per team.
- Vary the angle from team to team.
- Write like a league columnist, not a statistics report.
- Do not force a joke when a strong football story is better.

WHAT TO TALK ABOUT:
Prioritize the most interesting supported story for each team. Good angles include:
- a player carrying the roster or a huge individual performance;
- an ugly or dominant team performance;
- a bad beat or lucky escape;
- a disastrous or excellent lineup decision;
- a recent pickup/drop when it is actually relevant;
- a streak, milestone, rivalry, or historical fact supplied in evidence;
- early-season momentum or concern supported by the current data.

CRITICAL POWER-RANKING RULE:
- NEVER explain, reveal, estimate, reverse-engineer, or mention the Power Rankings
  formula, weights, component math, normalization, or "power score."
- Do not say a team is ranked somewhere "because of the formula."
- The ranking is the editorial ordering. Discuss the football story behind the team.

GROUNDING:
1. Use ONLY factual claims contained in TEAM EVIDENCE below.
2. Do not invent injuries. Injury information is not supplied.
3. Do not invent transactions, player performances, league history, streaks,
   records, or matchup facts.
4. A transaction may be mentioned only if it appears under that team's
   recent_transactions.
5. Do not imply a pickup contributed points unless the evidence independently
   supports that player's performance.
6. Distinguish bad luck from bad management.
7. Do not call a loss a bad beat unless luck_context identifies it as one.
8. Do not call a win lucky unless luck_context identifies it as a lucky win.
9. Do not claim a historical rivalry fact unless it appears in supplied evidence.
10. 2026 is an active season. Do not imply the season is complete.
11. Avoid repeating the same statistic in multiple sentences just to fill space.
12. Team names and player names must be copied exactly from evidence.

EVIDENCE TAGS:
Every commentary object must include evidence_tags containing one or more of
these exact values:
- player_performance
- matchup
- luck
- lineup
- transaction
- milestone
- standings
- season_context

Tag ONLY evidence categories actually used in the written blurb. Do not add a
tag merely because that category exists in the evidence packet.

Examples:
- If you mention Caleb Williams scoring 41.26, tag player_performance.
- If you call a win lucky or a loss a bad beat, tag luck.
- If you criticize or praise lineup choices/bench management, tag lineup.
- If you mention an add/drop, tag transaction.
- If you mention a career record or snapped streak, tag milestone.
- If you mention the opponent, score, margin, win, or loss, tag matchup.

OUTPUT:
Return valid JSON only, matching the supplied response schema.
Return exactly 12 commentary objects, in Power Rankings order.
schema_version must be 1.
evidence_tags are internal validation metadata; do not refer to them in prose.

TEAM EVIDENCE:
{json.dumps(evidence, ensure_ascii=False, indent=2)}
""".strip()


def parse_response(response):
    raw = getattr(response, "text", None)
    if not raw:
        raise RuntimeError("Gemini returned an empty response.")

    raw = raw.strip()

    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)



ALLOWED_EVIDENCE_TAGS = {
    "player_performance",
    "matchup",
    "luck",
    "lineup",
    "transaction",
    "milestone",
    "standings",
    "season_context",
}


def available_evidence_tags(team_evidence):
    tags = set()

    if team_evidence.get("player_facts"):
        tags.add("player_performance")

    if team_evidence.get("latest_matchup"):
        tags.add("matchup")

    if team_evidence.get("luck_context"):
        tags.add("luck")

    if team_evidence.get("managerial_decision"):
        tags.add("lineup")

    if team_evidence.get("recent_transactions"):
        tags.add("transaction")

    if team_evidence.get("milestones_and_streaks"):
        tags.add("milestone")

    if team_evidence.get("standings"):
        tags.add("standings")

    if team_evidence.get("season_context"):
        tags.add("season_context")

    return tags


def validate_evidence_tags(row, team_evidence):
    team = row.get("team")
    tags = row.get("evidence_tags")

    if not isinstance(tags, list) or not tags:
        raise RuntimeError(
            f"Commentary for {team} must include at least one evidence tag."
        )

    if len(tags) != len(set(tags)):
        raise RuntimeError(
            f"Commentary for {team} contains duplicate evidence tags."
        )

    unknown = set(tags) - ALLOWED_EVIDENCE_TAGS
    if unknown:
        raise RuntimeError(
            f"Commentary for {team} contains unknown evidence tags: "
            f"{sorted(unknown)}"
        )

    available = available_evidence_tags(team_evidence)
    unsupported = set(tags) - available
    if unsupported:
        raise RuntimeError(
            f"Commentary for {team} claims unsupported evidence categories: "
            f"{sorted(unsupported)}. Available: {sorted(available)}"
        )

    # Targeted prose/category checks catch the most dangerous embellishments.
    body = row.get("commentary", "").lower()

    lineup_terms = [
        "bench", "benched", "lineup", "roster decision", "roster decisions",
        "managerial", "management", "left points", "points left",
        "stranded on the pine", "on the pine", "starting decision",
    ]
    if any(term in body for term in lineup_terms):
        if "lineup" not in tags:
            raise RuntimeError(
                f"Commentary for {team} discusses lineup management without "
                "the lineup evidence tag."
            )
        if "lineup" not in available:
            raise RuntimeError(
                f"Commentary for {team} discusses lineup management but no "
                "managerial-decision evidence exists."
            )

    luck_terms = [
        "lucky", "luck", "bad beat", "fortunate", "schedule lottery",
        "stole a win", "escaped with a win",
    ]
    if any(term in body for term in luck_terms):
        if "luck" not in tags or "luck" not in available:
            raise RuntimeError(
                f"Commentary for {team} uses luck language without supported "
                "luck evidence."
            )

    transaction_terms = [
        "pickup", "picked up", "add/drop", "added ", "waiver",
        "free agent", "dropped ",
    ]
    if any(term in body for term in transaction_terms):
        if "transaction" not in tags or "transaction" not in available:
            raise RuntimeError(
                f"Commentary for {team} mentions a transaction without "
                "supported transaction evidence."
            )

    milestone_terms = [
        "milestone", "career loss", "career win", "record book",
        "streak", "losing skid", "winning skid", "snapped",
    ]
    if any(term in body for term in milestone_terms):
        if "milestone" not in tags or "milestone" not in available:
            raise RuntimeError(
                f"Commentary for {team} mentions a milestone/streak without "
                "supported milestone evidence."
            )


def validate_output(article, evidence):
    if not isinstance(article, dict):
        raise RuntimeError("Commentary response is not a JSON object.")

    if article.get("schema_version") != 1:
        raise RuntimeError("Commentary schema_version must be 1.")

    if article.get("season") != evidence["season"]:
        raise RuntimeError("Commentary season does not match evidence.")

    if article.get("week") != evidence["week"]:
        raise RuntimeError("Commentary week does not match evidence.")

    rows = article.get("commentary")
    if not isinstance(rows, list):
        raise RuntimeError("commentary must be a list.")

    if len(rows) != 12:
        raise RuntimeError(
            f"Generated commentary must contain exactly 12 teams; found {len(rows)}."
        )

    expected = [
        (team["ranking"]["power_rank"], team["team"])
        for team in evidence["teams"]
    ]
    actual = [
        (row.get("power_rank"), row.get("team"))
        for row in rows
    ]

    if actual != expected:
        raise RuntimeError(
            "Generated commentary team/rank order does not exactly match "
            "the deterministic Power Rankings snapshot."
        )

    evidence_by_team = {
        team["team"]: team
        for team in evidence["teams"]
    }

    seen = set()
    forbidden_formula_terms = [
        "40%",
        "35%",
        "15%",
        "10%",
        "power score",
        "weighted formula",
        "ranking formula",
    ]

    for row in rows:
        team = row.get("team")
        body = row.get("commentary")

        if team in seen:
            raise RuntimeError(f"Duplicate commentary team: {team}")
        seen.add(team)

        if not isinstance(body, str) or not body.strip():
            raise RuntimeError(f"Empty commentary for {team}.")

        if len(body) > 650:
            raise RuntimeError(
                f"Commentary for {team} is too long ({len(body)} characters)."
            )

        validate_evidence_tags(row, evidence_by_team[team])

        lower = body.lower()
        for phrase in forbidden_formula_terms:
            if phrase in lower:
                raise RuntimeError(
                    f"Commentary for {team} reveals ranking methodology: {phrase}"
                )

    return True


def generate(year, week):
    evidence = build_evidence(year, week)
    client = get_client()
    model = st.secrets.get("GEMINI_MODEL", DEFAULT_MODEL)

    print("=" * 88)
    print(f"GENERATING POWER RANKINGS COMMENTARY — {year} WEEK {week}")
    print("=" * 88)
    print(f"Gemini model: {model}")
    print("[PASS] 12 deterministic ranking positions loaded")
    print("[PASS] Weekly intelligence schema v4 loaded")
    print("[PASS] Ranking formula withheld from editorial evidence")
    print()

    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"Generation attempt {attempt}/{MAX_ATTEMPTS}...")

        extra = ""
        if last_error:
            extra = f"""
The previous attempt failed validation:
{last_error}

Repair the output. Return all 12 teams exactly once, use only supported evidence_tags, and obey every grounding rule.
"""

        response = client.models.generate_content(
            model=model,
            contents=prompt_for(evidence) + "\n\n" + extra,
            config=types.GenerateContentConfig(
                temperature=0.45,
                max_output_tokens=2400,
                response_mime_type="application/json",
                response_schema=response_schema(),
            ),
        )

        try:
            result = parse_response(response)
            print("[PASS] Gemini returned valid JSON")
            validate_output(result, evidence)
            print("[PASS] Commentary schema validated")
            print("[PASS] All 12 teams/ranks validated")
            print("[PASS] Evidence tags validated against team evidence")
            break
        except Exception as exc:
            last_error = str(exc)
            print(f"[RETRY] {last_error}")
    else:
        raise RuntimeError(
            "Power Rankings commentary generation failed after "
            f"{MAX_ATTEMPTS} attempts. Last error: {last_error}"
        )

    output_dir = DATA / "power_rankings" / str(year)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"week_{week:02d}_commentary.json"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[PASS] Wrote {output_path.relative_to(ROOT)}")
    print()
    print("POWER RANKINGS COMMENTARY COMPLETE")

    return result


def main():
    if len(sys.argv) >= 3:
        year = int(sys.argv[1])
        week = int(sys.argv[2])
    elif len(sys.argv) == 2:
        year, _ = latest_snapshot()
        week = int(sys.argv[1])
    else:
        year, week = latest_snapshot()

    generate(year, week)


if __name__ == "__main__":
    main()