import json
import os
import re
import sys
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
NEWS = DATA / "news"

DEFAULT_MODEL = "gemini-2.5-flash-lite"
EXPECTED_SCHEMA_VERSION = 4


def load_season_config():
    try:
        from season_config import CURRENT_SEASON
        return int(CURRENT_SEASON)
    except Exception:
        return 2026


def get_client():
    """
    Reuse the project's existing Gemini credential convention.

    Local/Streamlit:
        .streamlit/secrets.toml -> GEMINI_API_KEY

    Optional non-Streamlit fallback:
        GEMINI_API_KEY environment variable
    """
    api_key = None

    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass

    api_key = api_key or os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Add it to the existing "
            ".streamlit/secrets.toml used by the League Historian."
        )

    return genai.Client(api_key=api_key)


def get_model():
    try:
        return st.secrets.get("GEMINI_MODEL", DEFAULT_MODEL)
    except Exception:
        return os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)


def load_context(year, week):
    path = NEWS / str(year) / f"week_{week:02d}_context.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Weekly intelligence packet not found: {path}"
        )

    packet = json.loads(path.read_text(encoding="utf-8"))

    if packet.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        raise RuntimeError(
            f"Article generator requires Weekly News Intelligence schema "
            f"v{EXPECTED_SCHEMA_VERSION}; found "
            f"v{packet.get('schema_version')}."
        )

    if packet.get("season") != year or packet.get("week") != week:
        raise RuntimeError(
            "Weekly intelligence packet season/week does not match the "
            "requested article."
        )

    if len(packet.get("matchups", [])) != 6:
        raise RuntimeError(
            f"Expected 6 completed matchup stories; found "
            f"{len(packet.get('matchups', []))}."
        )

    return path, packet


def compact_packet(packet):
    """
    Send the complete current Weekly News Intelligence packet. It is already
    curated specifically for editorial use and is the sole league-fact evidence source.
    """
    return json.dumps(
        packet,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def build_prompt(packet):
    league_data = compact_packet(packet)
    year = packet["season"]
    week = packet["week"]

    return f"""
You are the WEEKLY COLUMNIST for a private fantasy football league.

Write the publication-ready Week {week} issue for the {year} season.

PUBLICATION IDENTITY:
- publication_title MUST be exactly "The Commissioner’s Mistake".
- Do not rename the publication from week to week.
- issue_headline is the changing front-page headline.

VOICE:
- Ruthless, funny, confident fantasy-football satire.
- Write like a sharp league columnist, not a corporate recap bot.
- Roast fantasy-football performance, lineup decisions, luck, collapses,
  rivalries, and statistical absurdity.
- Never insult a real person outside the context of fantasy football.
- Do not force a joke into every sentence.
- Vary the comedy. Avoid repeating the same joke construction for every team.
- Strong headlines and concise punchlines are encouraged.
- The facts should make the jokes land.

ABSOLUTE FACTUAL RULES:
1. WEEKLY NEWS INTELLIGENCE below is the ONLY source for league-specific facts.
2. Never invent or alter a score, player, projection, record, streak, ranking,
   lineup decision, milestone, historical result, or statistic.
3. Never invent an injury, NFL news event, quote, transaction, owner statement,
   motive, emotion, or real-world event.
4. You may make obviously comedic editorial observations, but they must not
   masquerade as new factual claims.
5. A historical_h2h record belongs to the explicit "team" field in that object.
6. Treat {year} as an active partial season. Do not imply final standings,
   playoff qualification, elimination, championships, or completed-season
   conclusions.
7. Upcoming matchup projections are projections, not results or guarantees.
8. Distinguish lineup execution from luck. Do not call a lucky win good
   management merely because the team won.
9. If a data module is unavailable, omit it rather than filling the gap.
10. Use exact numbers when they strengthen the story, normally to 1-2 decimals.
11. Preserve franchise names exactly as supplied, including emoji and casing.
12. Every completed matchup must receive exactly one recap.
13. Never call a result a "bad beat", "lucky win", "fraudulent win", or similar
    unless the supplied intelligence explicitly supports that characterization.
14. Do not predict regression, a blowout, an inevitable result, or what "reality"
    will do unless that conclusion is explicitly supported by supplied evidence.
15. Yahoo projections are authoritative only as projections. You may joke about
    them, but do not replace them with your own unsupported forecast.
16. Avoid unsupported claims about draft preparation, offseason behavior,
    desperation, roster construction, or what a manager "needs" to prove.
17. Prefer specific league evidence over generic sports-writing filler.
18. Completed-game historical_h2h_before_game values are PRE-GAME records.
    Never claim the completed result changed the series to that supplied record.
19. Preserve EVERY franchise and player name exactly as it appears in WEEKLY NEWS
    INTELLIGENCE. Never blend, abbreviate, autocorrect, parody, or mutate a proper
    name. A joke may surround a name, but the name itself is immutable.
20. Historical H2H describes what happened in prior meetings; it is not a forecast.
    Say "history favors", "holds a historical edge", or equivalent. Do not say
    "history says Team X will win" or otherwise turn past results into a prediction.
21. Aggregate H2H wins/losses and total points do NOT prove the individual games
    were blowouts, close games, dominant performances, or collapses. Only make such
    claims when the supplied evidence explicitly establishes them.

EDITORIAL OWNERSHIP / ANTI-REPETITION:
Each major fact has a primary editorial home, but this is a NEWSPAPER, not a
database report. Keep the facts organized without draining the personality.
- LEAD STORY: establish only the 2-3 most important themes of the week.
- MATCHUP RECAPS: tell what happened in each game with a distinct angle and a
  fresh joke. A recap MAY briefly reference a player performance, lineup mistake,
  or luck angle when it explains the game, but do not dump the detailed numbers.
- MANAGERIAL DESK: owns the detailed lineup-efficiency and start/sit autopsy.
- LUCK REPORT: owns the detailed all-play, expected-win, bad-beat, and luck case.
- PLAYERS OF THE WEEK: owns the detailed individual and positional leaderboard.
- RECORD BOOK: owns the detailed records, streaks, milestones, and history.
- NEXT WEEK: owns upcoming projections and pregame H2H history.

Do NOT remove humor merely to avoid repetition. Remove repeated FACTS and write
NEW jokes about the facts that belong in each section. A major story may be
teased in a recap and then examined in its specialist section, but do not repeat
the same statistic, phrasing, metaphor, or punchline.

Example of the desired relationship:
- Recap: briefly note that a manager's bench became part of the loss and tease
  that the Managerial Desk has the autopsy.
- Managerial Desk: give the exact points left behind and the actual start/sit
  decisions, with a different joke.

EDITORIAL PRIORITIES:
- Select the lead story based on genuine newsworthiness in the supplied packet.
  It does not have to be the highest score.
- Use bad-beat/all-play facts when they reveal misleading wins or losses.
- Use managerial-decision facts to identify strong or disastrous lineup choices.
- Use player facts and position leaders selectively rather than dumping a table.
- Use records/milestones when they are actually interesting.
- Preview all six upcoming matchups when future_matchups is available.
- Historical H2H and Yahoo projections should enrich previews, not turn them
  into spreadsheet prose.
- Do not manufacture awards that imply unsupported factual criteria.
- Give every matchup recap its own angle instead of forcing identical templates.
- Headlines should sound like THIS league's newspaper. Avoid generic headlines
  such as "A Classic Clash", "Heavyweights Collide", "Offensive Fireworks",
  "Comfortable Win", or "Looking to Bounce Back" when a specific joke or
  statistical contradiction is available.
- Avoid generic filler such as "statement win", "occupational hazard",
  "desperately needs", "sent a message", "drafted with a blindfold", or
  "anything can happen" unless a fresh, league-specific joke makes it worthwhile.
- Use fewer facts better. A paragraph does not need every available statistic.
- Ruthless does not mean repetitive: vary between dry sarcasm, absurd comparison,
  understated mockery, and direct statistical indictment.
- Prefer jokes that could only have been written after reading this week's data.
- Do not explain a joke after making it.

COMPLETED-GAME H2H RULE:
- historical_h2h_before_game is PRE-GAME history.
- Never describe that record as the series record after the completed Week result.
- Never say a Week result "evened", "extended", "improved", "moved", or "pushed"
  a historical series to the supplied pre-game record.
- If used in a completed recap, explicitly frame it as entering-the-week history
  (for example: "entered the week 6-7 against...").
- Prefer saving H2H detail for NEXT WEEK unless it materially improves the recap.

NEXT-WEEK STORYTELLING:
- Do more than list H2H records and Yahoo projections.
- Look for SUPPORTED tension between the two: historical dominance versus a close
  projection, a historical underdog projected to win, or a dead-even rivalry
  with a meaningful projection gap.
- When such a contradiction exists, make THAT the preview angle.
- Never resolve the contradiction yourself or invent a prediction.
- Example logic: if Team A is 8-2 historically but Yahoo projects Team B ahead,
  frame it as history versus the model, not as proof either side will win.

OUTPUT:
Return ONLY valid JSON. No Markdown fences and no commentary outside JSON.

Use exactly this top-level structure:
{{
  "schema_version": 1,
  "season": {year},
  "week": {week},
  "publication_title": "The Commissioner’s Mistake",
  "issue_headline": "string",
  "issue_deck": "string",
  "lead_story": {{
    "headline": "string",
    "body": ["paragraph", "paragraph"]
  }},
  "matchup_recaps": [
    {{
      "winner": "exact franchise name",
      "loser": "exact franchise name",
      "headline": "string",
      "body": "string"
    }}
  ],
  "managerial_desk": {{
    "headline": "string",
    "body": "string"
  }},
  "luck_report": {{
    "headline": "string",
    "body": "string"
  }},
  "players_of_the_week": {{
    "headline": "string",
    "body": "string"
  }},
  "record_book": {{
    "headline": "string",
    "body": "string"
  }},
  "next_week": {{
    "headline": "string",
    "previews": [
      {{
        "team_1": "exact franchise name",
        "team_2": "exact franchise name",
        "headline": "string",
        "body": "string"
      }}
    ]
  }},
  "closing_shot": "string"
}}

If a non-matchup optional section lacks usable evidence, use an empty headline
and body rather than inventing material.

WEEKLY NEWS INTELLIGENCE:
{league_data}
"""


def extract_json(text):
    if not text:
        raise RuntimeError("Gemini returned an empty response.")

    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Gemini did not return valid JSON. No article file was written."
        ) from exc



def collect_authoritative_names(packet):
    """
    Collect exact franchise/player names from the intelligence packet itself.
    These sets are used only as deterministic identity guardrails; they do not
    create new article facts.
    """
    teams = set()
    players = set()

    team_keys = {
        "team", "opponent", "winner", "loser", "team_1", "team_2",
        "fantasy_team", "franchise", "champion", "runner_up",
    }
    player_keys = {"player"}

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in team_keys and isinstance(item, str) and item.strip():
                    teams.add(item.strip())
                if key in player_keys and isinstance(item, str) and item.strip():
                    players.add(item.strip())
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(packet)
    return teams, players


def article_text_blob(article):
    """Flatten generated prose fields for deterministic proper-name checks."""
    parts = []

    def walk(value):
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            for key, item in value.items():
                # Structural identity fields are validated separately.
                if key not in {"winner", "loser", "team_1", "team_2"}:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(article)
    return "\n".join(parts)


def validate_proper_name_integrity(article, packet):
    """
    Catch likely Gemini mutations of franchise/player names in prose.

    Exact authoritative names are temporarily removed from the article text.
    Remaining underscore-style identifiers are especially suspicious because
    league franchise names such as malle_dips_pouches must never be mutated into
    constructions such as jalen_dips_pouches.
    """
    teams, players = collect_authoritative_names(packet)
    text = article_text_blob(article)

    # Remove legitimate exact names first, longest-first to avoid partial overlap.
    scrubbed = text
    for name in sorted(teams | players, key=len, reverse=True):
        scrubbed = scrubbed.replace(name, " ")

    suspicious_identifiers = set(
        re.findall(r"(?<!\w)[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+(?!\w)", scrubbed)
    )
    if suspicious_identifiers:
        raise RuntimeError(
            "Generated prose contains non-authoritative underscore-style proper "
            f"name(s): {sorted(suspicious_identifiers)}. Preserve franchise/player "
            "names exactly as supplied in WEEKLY NEWS INTELLIGENCE."
        )

    return True


def validate_article(article, packet):
    required = {
        "schema_version",
        "season",
        "week",
        "publication_title",
        "issue_headline",
        "issue_deck",
        "lead_story",
        "matchup_recaps",
        "managerial_desk",
        "luck_report",
        "players_of_the_week",
        "record_book",
        "next_week",
        "closing_shot",
    }

    missing = required - set(article)
    if missing:
        raise RuntimeError(
            f"Generated article is missing fields: {sorted(missing)}"
        )

    if article["schema_version"] != 1:
        raise RuntimeError("Generated article schema_version must be 1.")

    if article.get("publication_title") != "The Commissioner’s Mistake":
        raise RuntimeError(
            'publication_title must be exactly "The Commissioner’s Mistake".'
        )

    if article["season"] != packet["season"] or article["week"] != packet["week"]:
        raise RuntimeError("Generated article season/week changed.")

    source_games = {
        (x["winner"], x["loser"])
        for x in packet["matchups"]
    }

    recaps = article.get("matchup_recaps", [])
    if len(recaps) != 6:
        raise RuntimeError(
            f"Generated article must contain exactly 6 matchup recaps; "
            f"found {len(recaps)}."
        )

    generated_games = [
        (x.get("winner"), x.get("loser"))
        for x in recaps
    ]

    if len(set(generated_games)) != 6:
        raise RuntimeError("Generated article contains duplicate matchup recaps.")

    if set(generated_games) != source_games:
        raise RuntimeError(
            "Generated matchup recap teams do not exactly match the "
            "intelligence packet."
        )

    future = packet.get("future_matchups", {})
    previews = article.get("next_week", {}).get("previews", [])

    if future.get("available"):
        source_future = {
            (x["team_1"], x["team_2"])
            for x in future.get("matchups", [])
        }
        generated_future = [
            (x.get("team_1"), x.get("team_2"))
            for x in previews
        ]

        if len(generated_future) != 6:
            raise RuntimeError(
                f"Generated article must contain exactly 6 Week "
                f"{packet['week'] + 1} previews; found "
                f"{len(generated_future)}."
            )

        if len(set(generated_future)) != 6:
            raise RuntimeError("Generated article contains duplicate previews.")

        if set(generated_future) != source_future:
            raise RuntimeError(
                "Generated preview teams do not exactly match the "
                "authoritative upcoming-matchup packet."
            )
    elif previews:
        raise RuntimeError(
            "Generated article invented next-week previews although future "
            "matchup data was unavailable."
        )

    # Basic text sanity checks.
    text_fields = [
        article.get("publication_title"),
        article.get("issue_headline"),
        article.get("issue_deck"),
        article.get("closing_shot"),
    ]
    if any(not isinstance(x, str) for x in text_fields):
        raise RuntimeError("Generated article contains invalid headline text.")

    validate_proper_name_integrity(article, packet)

    return True



MAX_GENERATION_ATTEMPTS = 3


def article_validation_error(article, packet):
    """
    Return None when valid; otherwise return the validator's exact failure
    message so Gemini can repair the draft.
    """
    try:
        validate_article(article, packet)
        return None
    except RuntimeError as exc:
        return str(exc)


def required_matchup_manifest(packet):
    completed = [
        {
            "winner": x["winner"],
            "loser": x["loser"],
        }
        for x in packet["matchups"]
    ]

    future = packet.get("future_matchups", {})
    upcoming = []
    if future.get("available"):
        upcoming = [
            {
                "team_1": x["team_1"],
                "team_2": x["team_2"],
            }
            for x in future.get("matchups", [])
        ]

    return {
        "required_completed_matchups": completed,
        "required_upcoming_matchups": upcoming,
    }


def build_repair_prompt(packet, article, validation_error):
    """
    Ask Gemini to repair the entire JSON document while preserving good prose.
    The authoritative matchup manifest is repeated explicitly so omissions and
    accidental team substitutions are easy for the model to correct.
    """
    manifest = required_matchup_manifest(packet)

    return f"""
You are repairing a generated fantasy-football weekly article.

The draft failed deterministic validation.

VALIDATION ERROR:
{validation_error}

AUTHORITATIVE MATCHUP MANIFEST:
{json.dumps(manifest, ensure_ascii=False, indent=2)}

REPAIR RULES:
1. Return ONLY the complete corrected JSON article. No Markdown fences.
2. Preserve the existing article's good prose wherever it does not need repair.
3. The final matchup_recaps array MUST contain exactly one entry for every
   required_completed_matchup above: exactly 6 total, no duplicates.
4. Each completed recap MUST preserve the exact winner and loser strings from
   the manifest. Never reverse, rename, omit, or invent a matchup.
5. If required_upcoming_matchups is non-empty, next_week.previews MUST contain
   exactly one entry for every listed matchup: exactly 6 total, no duplicates.
6. Preserve exact team_1/team_2 orientation for upcoming matchups.
7. Do not invent any league fact while repairing.
8. WEEKLY NEWS INTELLIGENCE below remains the sole factual source.
9. Keep schema_version=1 and preserve the requested season/week.
10. Keep exactly the same top-level article structure as the draft.
11. Preserve every franchise and player name EXACTLY as supplied in WEEKLY NEWS
    INTELLIGENCE. Never blend or mutate proper names while repairing prose.
12. Treat historical H2H as past evidence, never as a prediction, and do not infer
    individual-game blowouts/closeness from aggregate H2H totals alone.

CURRENT DRAFT:
{json.dumps(article, ensure_ascii=False, indent=2)}

WEEKLY NEWS INTELLIGENCE:
{compact_packet(packet)}
"""


def generate_and_validate(client, model, packet):
    """
    Generate once, then automatically repair a structurally invalid draft up
    to MAX_GENERATION_ATTEMPTS total attempts. Nothing is written to disk until
    deterministic validation succeeds.
    """
    prompt = build_prompt(packet)
    last_error = None

    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        if attempt == 1:
            print(f"Generation attempt {attempt}/{MAX_GENERATION_ATTEMPTS}...")
        else:
            print(
                f"Repair attempt {attempt}/{MAX_GENERATION_ATTEMPTS} "
                f"after validation failure: {last_error}"
            )

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.70 if attempt == 1 else 0.25,
                max_output_tokens=6500,
                response_mime_type="application/json",
            ),
        )

        article = extract_json(response.text)
        last_error = article_validation_error(article, packet)

        if last_error is None:
            if attempt > 1:
                print(
                    f"[PASS] Article repaired successfully on attempt {attempt}"
                )
            return article

        if attempt < MAX_GENERATION_ATTEMPTS:
            prompt = build_repair_prompt(
                packet,
                article,
                last_error,
            )

    raise RuntimeError(
        "Article failed validation after "
        f"{MAX_GENERATION_ATTEMPTS} attempts. Last error: {last_error}. "
        "No article file was written."
    )

def generate_article(year, week):
    context_path, packet = load_context(year, week)

    print("=" * 88)
    print(f"GENERATING WEEKLY ARTICLE — {year} WEEK {week}")
    print("=" * 88)
    print()
    print(f"Context: {context_path.relative_to(ROOT)}")
    print(f"Intelligence schema: v{packet['schema_version']}")
    print("[PASS] 6 completed matchups loaded")
    print(
        "[PASS] Future matchups: "
        + (
            "available"
            if packet.get("future_matchups", {}).get("available")
            else "not available"
        )
    )

    client = get_client()
    model = get_model()

    print(f"Gemini model: {model}")
    print("Generating article with automatic validation/repair...")

    article = generate_and_validate(
        client=client,
        model=model,
        packet=packet,
    )

    print("[PASS] Gemini returned valid JSON")
    print("[PASS] Article schema validated")
    print("[PASS] All 6 completed matchup recaps validated")

    if packet.get("future_matchups", {}).get("available"):
        print("[PASS] All 6 upcoming matchup previews validated")

    out_dir = NEWS / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"week_{week:02d}_article.json"

    # Write only after every structural/factual-identity guardrail passes.
    out_path.write_text(
        json.dumps(article, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"[PASS] Wrote {out_path.relative_to(ROOT)}")
    print()
    print("ARTICLE GENERATION COMPLETE")

    return out_path


def main():
    year = load_season_config()

    if len(sys.argv) >= 2:
        week = int(sys.argv[1])
    else:
        week = int(input("Week to generate article for: ").strip())

    generate_article(year, week)


if __name__ == "__main__":
    main()