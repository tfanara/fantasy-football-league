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
    Send the complete authoritative packet, but put the ranked story desk first so
    Gemini sees Python's editorial synthesis before the supporting evidence.
    """
    story_engine = packet.get("weekly_story_engine", {})
    editorial_packet = {
        "editorial_assignment_desk": {
            "story_candidates": story_engine.get("story_candidates", []),
            "compound_stories": story_engine.get("compound_stories", []),
        },
        "authoritative_weekly_intelligence": packet,
    }
    return json.dumps(
        editorial_packet,
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
22. MANAGEMENT CAUSALITY IS STRICT:
    - "manager_blew_game" means validated lineup optimization was sufficient to reverse
      the result. Only this kind of evidence supports language such as "cost the game",
      "left a win on the bench", "blew the win", or equivalent outcome-changing claims.
    - "multiple_managerial_mistakes", low lineup efficiency, or many unused points can
      support roasting bad lineup execution, but DO NOT say it cost a win unless the
      supplied evidence explicitly shows the optimized score would have beaten the opponent.
    - A losing team's optimized score remaining below the opponent's actual score means
      the manager still would have lost. State or imply that distinction when relevant.
23. CAUSAL VERBS ARE EVIDENCE-DEPENDENT. Do not say a player/DEF/kicker "saved",
    "rescued", "stole", "caused", "delivered", or was "the difference" in a result merely
    because they scored well. Use those causal formulations only when the supplied
    compound evidence mathematically connects the contribution to the game margin.
24. Do not call a lineup "optimal", "nearly optimal", "clean", or equivalent unless the
    supplied lineup-efficiency/optimization evidence reasonably supports that description.
    Prefer the exact efficiency or unused-points fact when in doubt.
25. H2H RECORD INTERPRETATION IS MATHEMATICAL:
    - If the named team's record is W-L-T and W > L, that named team holds the historical edge.
    - If W < L, the OPPONENT holds the historical edge. Never say the named team holds it.
    - If W = L, the series is even; history favors neither side.
    - A record such as 4-7 is a historical deficit, never a historical edge.
26. Do not call a projected matchup a "toss-up", "coin flip", "dead even", or equivalent
    unless the supplied projection gap is 2.00 points or less. Otherwise state the actual
    projected edge without upgrading it into a certainty.
27. RANK DIRECTION IS LITERAL. A weekly_score_rank of 1 means highest-scoring team,
    2 means second-highest, etc. Never convert "7th-highest" into "7th-worst" or otherwise
    reverse an ordinal. If the direction is not explicit enough to state safely, omit the
    ordinal and use the supplied score/all-play/expected-win evidence instead.
28. Historical matchup records in future_matchups are HEAD-TO-HEAD records. Never
    call a historical H2H record an "all-play" record.
29. If a losing team's validated optimal_score still trails the winner's actual score,
    lineup mistakes may be mocked as wasted points or poor execution, but they did NOT
    change the winner. Do not say they cost the game, left a win on the bench, turned
    a winnable game into the loss, or otherwise caused the result.

EDITORIAL ASSIGNMENT DESK:
- Python has already ranked and synthesized the week's strongest factual story angles
  in editorial_assignment_desk.story_candidates.
- Treat that ranked list as your assignment desk, NOT as another section to summarize.
- Start with the highest-ranked compound stories when choosing the issue headline,
  lead story, and major angles.
- Ranking is strong editorial guidance, not a requirement to mechanically write
  candidate #1, then #2, then #3.
- compound_derived_fact candidates are especially valuable because they connect
  multiple verified facts into one supported story. Preserve those relationships.
- A candidate's headline_fact is factual scaffolding, NOT publication-ready prose.
  Rewrite it with personality rather than copying it verbatim.
- Do not decompose a strong compound story back into weaker isolated facts when the
  compound relationship is the interesting part.
- Use lower-ranked candidates when they give another matchup or section a distinctive
  angle, but do not crowd out stronger stories merely to mention every candidate.
- story_candidates are NOT additional facts. Every factual statement still comes
  from the authoritative intelligence packet embedded below.
- Do not mention "story candidates", "importance", "compound stories", "the packet",
  "the data", or the editorial assignment desk in the published article.
- Do not turn deterministic labels such as manager_blew_game, opponent_contrast,
  carry_job_in_loss, or special_teams_game_swing into visible newspaper terminology.
  Those are internal classifications; write natural prose.
- When a compound story says validated lineup optimization was enough to flip a game,
  you may roast the lineup decision as consequential. Do not generalize that into
  unsupported claims about the manager's overall competence or preparation.
- Internal story types are semantically meaningful. In particular:
  manager_blew_game = management could mathematically reverse the result;
  multiple_managerial_mistakes = bad lineup execution that may NOT have changed the winner.
  Never merge those two ideas merely because both are funny.
- A high-ranked story may appear in both the lead and its natural specialist section,
  but the lead should establish the theme while the specialist section supplies the
  detailed autopsy. Do not repeat the same numbers and joke twice.

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
- Select the lead story from the strongest ranked assignment-desk material based
  on genuine newsworthiness. It does not have to be the week's highest score or
  automatically candidate #1.
- Prefer a lead with consequence, contradiction, absurdity, or a game-changing
  relationship over a merely large standalone player score.
- The issue headline and deck should sell the same central story/theme as the lead,
  rather than introducing an unrelated fact.
- Use bad-beat/all-play facts when they reveal misleading wins or losses.
- Use managerial-decision facts to identify strong or disastrous lineup choices.
- Use player facts and position leaders selectively rather than dumping a table.
- Use records/milestones when they are actually interesting.
- Preview all six upcoming matchups when future_matchups is available.
- Historical H2H and Yahoo projections should enrich previews, not turn them
  into spreadsheet prose.
- Vary preview syntax. Do not write six versions of "Team X holds record Y and the
  projection model favors Team Z." Express the supported relationship naturally.
- closing_shot should pay off a verified Week-specific absurdity already established
  in the article. It must not invent a new factual setup.
- Do not manufacture awards that imply unsupported factual criteria.
- Give every matchup recap its own angle instead of forcing identical templates.
- Headlines should sound like THIS league's newspaper. Avoid generic headlines
  such as "A Classic Clash", "Heavyweights Collide", "Offensive Fireworks",
  "Comfortable Win", or "Looking to Bounce Back" when a specific joke or
  statistical contradiction is available.
- Avoid generic filler and stock fantasy/sports clichés. In particular, avoid
  "statement win", "occupational hazard", "desperately needs", "sent a message",
  "drafted with a blindfold", "anything can happen", "fantasy gods", "buzzsaw",
  "flip the script", "snatch defeat from the jaws of victory", "points on the pine",
  "masterclass", "self-sabotage", "search for traction", "shake it off", and
  "looking to bounce back" unless the phrase is genuinely transformed into a specific,
  original joke that could only apply to this league and this week.
- Build humor from the numerical absurdity itself: tiny margins, huge bench gaps,
  disproportionate scoring shares, contradictory luck, recent acquisitions, and
  specific start/sit decisions. Specificity is funnier than a stock metaphor.
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
- Before writing each preview, interpret the historical record from the perspective
  of the explicit team field that owns that W-L-T record. Check the arithmetic:
  more wins = that team has the edge; more losses = its opponent has the edge;
  equal wins/losses = even series.
- After establishing which side owns the historical edge, keep ALL later wording
  consistent with it. Do not later call that same team the historical underdog, say it
  faces a historical deficit, or otherwise contradict the record indirectly.
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

EDITORIALLY ORDERED WEEKLY NEWS INTELLIGENCE:
The JSON below begins with editorial_assignment_desk, followed by the complete
authoritative_weekly_intelligence evidence packet. The latter remains the sole
authority for league facts.

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



def validate_preview_h2h_language(article, packet):
    """
    Catch the clearest H2H-direction mistakes in generated Week+1 previews.

    This deliberately validates only explicit "historical edge/favors" language.
    It does not attempt to fact-check arbitrary prose.
    """
    future = packet.get("future_matchups", {})
    if not future.get("available"):
        return True

    source_by_pair = {}
    for matchup in future.get("matchups", []):
        pair = (matchup.get("team_1"), matchup.get("team_2"))
        source_by_pair[pair] = matchup

    edge_patterns = (
        r"\bholds? (?:a |the )?(?:historical )?edge\b",
        r"\bhistory favors\b",
        r"\bhistorical advantage\b",
        r"\bhistorical dominance\b",
    )

    for preview in article.get("next_week", {}).get("previews", []):
        team_1 = preview.get("team_1")
        team_2 = preview.get("team_2")
        source = source_by_pair.get((team_1, team_2))
        if not source:
            continue

        combined = f"{preview.get('headline', '')} {preview.get('body', '')}"
        lowered = combined.casefold()

        # Collect any explicit historical_h2h object(s) attached to this matchup.
        h2h_objects = []

        def walk(value):
            if isinstance(value, dict):
                if (
                    isinstance(value.get("team"), str)
                    and isinstance(value.get("wins"), (int, float))
                    and isinstance(value.get("losses"), (int, float))
                ):
                    h2h_objects.append(value)
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(source)

        for h2h in h2h_objects:
            team = h2h["team"]
            wins = h2h["wins"]
            losses = h2h["losses"]

            if wins == losses:
                # If an even series is explicitly described as favoring either side,
                # reject it. Generic "history" wording without an edge claim is fine.
                if any(re.search(p, lowered) for p in edge_patterns):
                    raise RuntimeError(
                        f"Preview {team_1} vs {team_2} describes an even historical "
                        f"series ({wins}-{losses}) as having an edge."
                    )
                continue

            opponent = team_2 if team == team_1 else team_1 if team == team_2 else None
            if not opponent:
                continue

            favored = team if wins > losses else opponent
            unfavored = opponent if wins > losses else team

            # Detect explicit constructions such as
            # "Malle holds a 4-7 historical edge" or "history favors Malle".
            escaped_unfavored = re.escape(unfavored.casefold())
            bad_patterns = (
                rf"{escaped_unfavored}.{{0,45}}(?:historical )?edge",
                rf"{escaped_unfavored}.{{0,45}}historical advantage",
                rf"history favors.{{0,20}}{escaped_unfavored}",
                rf"historical dominance.{{0,25}}{escaped_unfavored}",
            )
            if any(re.search(p, lowered) for p in bad_patterns):
                raise RuntimeError(
                    f"Preview {team_1} vs {team_2} assigns the historical edge to "
                    f"{unfavored}, but the supplied H2H record favors {favored}."
                )

            # Catch indirect contradictions such as:
            # "History favors Voldemort..." followed by "despite the historical deficit".
            escaped_favored = re.escape(favored.casefold())
            contradiction_patterns = (
                rf"{escaped_favored}.{{0,80}}historical (?:deficit|underdog)",
                rf"historical (?:deficit|underdog).{{0,80}}{escaped_favored}",
            )
            if any(re.search(p, lowered) for p in contradiction_patterns):
                raise RuntimeError(
                    f"Preview {team_1} vs {team_2} contradicts the supplied H2H record "
                    f"by describing historically favored {favored} as disadvantaged."
                )

    return True



def validate_score_rank_language(article, packet):
    """
    Catch reversed weekly-score ordinals such as calling weekly_score_rank=7
    the '7th-worst' score. Packet score ranks are descending: rank 1 is highest.
    """
    rank_by_team = {}

    def walk(value):
        if isinstance(value, dict):
            team = value.get("team")
            rank = value.get("weekly_score_rank")
            if isinstance(team, str) and isinstance(rank, int):
                rank_by_team[team] = rank
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(packet)

    blob = article_text_blob(article).casefold()
    for team, rank in rank_by_team.items():
        ordinal = (
            f"{rank}th" if 10 <= rank % 100 <= 20
            else f"{rank}{ {1:'st', 2:'nd', 3:'rd'}.get(rank % 10, 'th') }"
        )
        team_cf = team.casefold()
        bad = (
            rf"{re.escape(team_cf)}.{{0,100}}\b{re.escape(ordinal)}[- ](?:worst|lowest)\b",
            rf"\b{re.escape(ordinal)}[- ](?:worst|lowest)\b.{{0,100}}{re.escape(team_cf)}",
        )
        if any(re.search(p, blob) for p in bad):
            raise RuntimeError(
                f"Generated prose reverses weekly_score_rank for {team}: rank {rank} "
                f"is {ordinal}-highest, not {ordinal}-worst/lowest."
            )
    return True


def build_copy_edit_prompt(packet, article):
    """
    Second-pass editorial polish. Facts and JSON structure are locked; the task is
    purely to improve voice, specificity, rhythm, and originality.
    """
    return f"""
You are the COPY EDITOR for The Commissioner’s Mistake, a private fantasy-football
league newspaper.

The article below has ALREADY passed deterministic factual/structural validation.
Your job is to improve the prose WITHOUT changing its facts.

COPY-EDIT MISSION:
- Make the article sound specific to this league and this week.
- You MAY substantially rewrite STYLE: sentence structure, jokes, headlines, rhythm,
  transitions, and paragraph flow. The facts are locked; the wording is not.
- Sharpen jokes, headlines, rhythm, and transitions.
- Remove generic sportswriter/fantasy clichés and repeated joke constructions.
- Prefer dry specificity, numerical absurdity, understated mockery, and fresh images
  that arise directly from the supplied facts.
- Keep the ruthless tone, but do not make every sentence shout.
- Preserve useful jokes that are already specific and effective.
- Do not add a new story merely because you see unused facts in the packet.

LOCKED FACTUAL RULES:
1. Return ONLY the complete JSON article, with exactly the same schema and section structure.
2. Do not change any winner, loser, team_1, team_2, franchise name, player name, score,
   projection, percentage, record, rank, transaction, lineup decision, or other factual value.
3. Do not add any league-specific factual claim that is absent from the authoritative packet.
4. Do not turn bad management into a manager-caused loss unless validated optimization
   explicitly shows the result could flip.
5. Do not reverse H2H direction. W>L favors the named team; W<L favors its opponent;
   W=L is even.
6. weekly_score_rank is descending: rank 1 is highest. Never convert an Nth-highest
   rank into Nth-worst/Nth-lowest.
7. Avoid unsupported causal language such as saved, rescued, stole, caused, or
   difference-maker unless the supplied compound evidence supports that relationship.
8. Preserve the distinction between projections and results.
9. Historical matchup records are head-to-head records; never relabel them as all-play.
10. If validated optimal_score still trails the winner's actual score, lineup mistakes
    did not change the winner. Preserve that distinction.
11. Preserve the meaning of the draft. This is a COPY EDIT, not a rewrite from scratch.

STYLE CLEANUP:
Actively replace or remove stock phrases such as:
- masterclass
- self-sabotage
- points on the pine
- fantasy gods
- buzzsaw
- flip the script
- snatch defeat from the jaws of victory
- strapped the team to his back / put on a cape / heavy lifting
- clean ship
- train on the tracks
- within a whisker
- statement win
- looking to bounce back
- search for traction
- anything can happen

Do not merely swap one cliché for another. If a plain, specific sentence is funnier,
use the plain sentence.

- The six Week+1 previews must not all use the same history-plus-projection sentence
  template. Vary their construction while preserving every number and direction.
- Preview headlines should exploit the actual supported tension when one exists.
  Do not manufacture tension where none exists.
- The closing_shot must be anchored to one of THIS WEEK'S strongest verified absurdities
  already established in the article. Do not introduce a new factual premise merely
  to manufacture a final joke.

CURRENT VALIDATED ARTICLE:
{json.dumps(article, ensure_ascii=False, indent=2)}

AUTHORITATIVE WEEKLY INTELLIGENCE:
{compact_packet(packet)}
"""


def copy_edit_and_validate(client, model, packet, article):
    """
    Run one narrow prose-polish pass. If the copy edit fails deterministic validation,
    repair it once using the existing repair machinery. The original validated draft
    remains available as a safe fallback.
    """
    prompt = build_copy_edit_prompt(packet, article)
    print("Running second-pass copy edit...")

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.55,
            max_output_tokens=6500,
            response_mime_type="application/json",
        ),
    )

    try:
        edited = extract_json(response.text)
    except RuntimeError as exc:
        print(
            f"[WARN] Copy edit returned invalid JSON ({exc}); "
            "using the original validated draft."
        )
        return article

    edited, error = validate_with_deterministic_repairs(edited, packet)
    if error is None:
        print("[PASS] Copy-edited article validated")
        return edited

    print(f"Copy edit failed validation; attempting one repair: {error}")
    repair_prompt = build_repair_prompt(packet, edited, error)
    response = client.models.generate_content(
        model=model,
        contents=repair_prompt,
        config=types.GenerateContentConfig(
            temperature=0.10,
            max_output_tokens=6500,
            response_mime_type="application/json",
        ),
    )
    try:
        repaired = extract_json(response.text)
    except RuntimeError as exc:
        print(
            f"[WARN] Copy-edit repair returned invalid JSON ({exc}); "
            "using the original validated draft."
        )
        return article

    repaired, error = validate_with_deterministic_repairs(
        repaired, packet
    )
    if error is None:
        print("[PASS] Copy-edited article repaired and validated")
        return repaired

    print(
        "[WARN] Copy edit could not be validated after repair; "
        "using the original validated draft."
    )
    return article



def validate_franchise_name_mutations(article, packet):
    """Catch likely one-edit franchise-name typos in prose/headlines."""
    teams, _ = collect_authoritative_names(packet)
    text = article_text_blob(article)

    scrubbed = text
    for team in sorted(teams, key=len, reverse=True):
        scrubbed = re.sub(re.escape(team), " ", scrubbed, flags=re.I)

    def one_edit_apart(a, b):
        a, b = a.casefold(), b.casefold()
        if a == b or abs(len(a) - len(b)) > 1:
            return False
        if len(a) == len(b):
            return sum(x != y for x, y in zip(a, b)) == 1
        if len(a) > len(b):
            a, b = b, a
        i = j = edits = 0
        while i < len(a) and j < len(b):
            if a[i] == b[j]:
                i += 1
                j += 1
            else:
                edits += 1
                j += 1
                if edits > 1:
                    return False
        return True

    tokens = re.findall(r"[A-Za-z][A-Za-z']*", scrubbed)
    lowered = [x.casefold() for x in tokens]

    for team in teams:
        team_tokens = re.findall(r"[A-Za-z][A-Za-z']*", team)
        if len(team_tokens) < 2:
            continue
        team_lower = [x.casefold() for x in team_tokens]

        for i, token in enumerate(tokens):
            for j, target in enumerate(team_tokens):
                if len(target) < 5 or not one_edit_apart(token, target):
                    continue
                nearby = lowered[max(0, i - 4): i + 5]
                companions = [
                    x for k, x in enumerate(team_lower)
                    if k != j and len(x) >= 4
                ]
                if any(x in nearby for x in companions):
                    raise RuntimeError(
                        f"Generated prose contains likely franchise-name mutation "
                        f"'{token}' near authoritative franchise '{team}'. "
                        "Preserve franchise names exactly."
                    )
    return True




def validate_h2h_stat_labels(article, packet):
    """Future matchup historical records are H2H, never all-play records."""
    for preview in article.get("next_week", {}).get("previews", []):
        combined = f"{preview.get('headline', '')} {preview.get('body', '')}"
        if re.search(r"(?i)\ball[- ]play\b", combined):
            raise RuntimeError(
                f"Preview {preview.get('team_1')} vs {preview.get('team_2')} "
                "labels historical H2H evidence as all-play."
            )
    return True


def validate_management_causality(article, packet):
    """
    Prevent a losing team's lineup mistakes from being described as outcome-changing
    when its validated optimal score still would not have beaten the winner.
    """
    decisions = {
        x.get("team"): x
        for x in packet.get("managerial_decisions", {}).get("decisions", [])
        if isinstance(x, dict) and isinstance(x.get("team"), str)
    }

    games = {
        x.get("loser"): x
        for x in packet.get("matchups", [])
        if isinstance(x, dict) and isinstance(x.get("loser"), str)
    }

    # Phrases that imply lineup management changed the winner or created the result.
    causal_patterns = (
        r"\bcost (?:them|him|her|the team)? ?(?:the )?(?:game|win|victory)\b",
        r"\bleft (?:a|the) win on the bench\b",
        r"\bblew (?:the )?(?:game|win|victory)\b",
        r"\bthrew away (?:the )?(?:game|win|victory)\b",
        r"\bturned (?:a|the|what could have been).{0,80}\binto\b",
        r"\bchanged the outcome\b",
        r"\bflipped the result\b",
        r"\bwould have won\b",
    )

    management_terms = (
        "bench", "lineup", "start", "started", "starting", "manager",
        "management", "mismanaged", "miscue", "efficiency", "optimal"
    )

    # Check prose sentence-by-sentence so unrelated causal language elsewhere does not
    # get attributed to the wrong franchise.
    blob = article_text_blob(article)
    sentences = re.split(r"(?<=[.!?])\s+", blob)

    for team, decision in decisions.items():
        game = games.get(team)
        if not game:
            continue

        optimal = decision.get("optimal_score")
        winner_score = game.get("winner_score")
        if not isinstance(optimal, (int, float)) or not isinstance(winner_score, (int, float)):
            continue

        # If optimization could actually reverse the result, causal language is allowed.
        if optimal > winner_score:
            continue

        for sentence in sentences:
            lowered = sentence.casefold()
            if team.casefold() not in lowered:
                continue
            if not any(term in lowered for term in management_terms):
                continue
            if any(re.search(pattern, lowered) for pattern in causal_patterns):
                raise RuntimeError(
                    f"Management causality overstatement for {team}: validated optimal "
                    f"score {optimal:.2f} would still trail the opponent's "
                    f"{winner_score:.2f}. Lineup mistakes may be criticized, but cannot "
                    "be described as changing the winner."
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
    validate_franchise_name_mutations(article, packet)
    validate_preview_h2h_language(article, packet)
    validate_h2h_stat_labels(article, packet)
    validate_score_rank_language(article, packet)
    validate_management_causality(article, packet)

    return True



MAX_GENERATION_ATTEMPTS = 4


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
2. SURGICAL REPAIR ONLY: fix the specific VALIDATION ERROR above and any text that
   directly depends on that error. Do not rewrite unrelated headlines, sections,
   jokes, matchup recaps, previews, or prose.
3. Preserve the existing article's good prose verbatim wherever it does not need repair.
4. The final matchup_recaps array MUST contain exactly one entry for every
   required_completed_matchup above: exactly 6 total, no duplicates.
5. Each completed recap MUST preserve the exact winner and loser strings from
   the manifest. Never reverse, rename, omit, or invent a matchup.
6. If required_upcoming_matchups is non-empty, next_week.previews MUST contain
   exactly one entry for every listed matchup: exactly 6 total, no duplicates.
7. Preserve exact team_1/team_2 orientation for upcoming matchups.
8. Do not invent any league fact while repairing.
9. The authoritative_weekly_intelligence object below remains the sole factual
   source. editorial_assignment_desk only ranks/synthesizes facts already supported
   there and must not be treated as an independent source.
10. Keep schema_version=1 and preserve the requested season/week.
11. Keep exactly the same top-level article structure as the draft.
12. Preserve every franchise and player name EXACTLY as supplied in WEEKLY NEWS
    INTELLIGENCE. Never blend or mutate proper names while repairing prose.
13. Treat historical H2H as past evidence, never as a prediction, and do not infer
    individual-game blowouts/closeness from aggregate H2H totals alone.
14. A manager may be described as costing/blowing a win ONLY when supplied validated
    optimization explicitly shows the lineup change could reverse the result.
15. Interpret W-L-T H2H records from the named team's perspective: W>L favors that
    team, W<L favors its opponent, W=L favors neither side.
16. Avoid unsupported causal verbs such as saved/rescued/stole/caused/difference-maker.
17. weekly_score_rank is descending: rank 1 is highest. Never rewrite an Nth-highest
    rank as Nth-worst or Nth-lowest.
18. Keep every sentence in a preview consistent with the same H2H direction; do not
    correctly state an edge and then call that favored team historically disadvantaged.
19. When the validation error names one specific preview, leave all other previews
    unchanged unless they independently violate one of the factual rules above.
20. When the validation error concerns an even series, remove edge/favored/underdog
    language for that series. When it concerns a directional series, change only the
    contradictory historical wording; do not alter the supplied record or projections.
21. If validation identifies a likely franchise-name mutation, replace only the typo
    with the exact authoritative franchise name; do not rewrite the surrounding passage.
22. Do not repair a closing_shot by inventing a new factual premise. Anchor it to a fact
    already supported by the authoritative packet.
23. Historical H2H records must never be labeled all-play.
24. If a losing team's validated optimal score still trails the winner's actual score,
    preserve criticism of the lineup if warranted but remove any claim that management
    changed the winner or cost a victory.

CURRENT DRAFT:
{json.dumps(article, ensure_ascii=False, indent=2)}

WEEKLY NEWS INTELLIGENCE:
{compact_packet(packet)}
"""



def _replace_h2h_edge_language_for_even_preview(preview, wins, losses, ties):
    """
    Deterministically neutralize historical-edge language for an even H2H series.
    Keep projections and unrelated preview prose intact.
    """
    record = f"{wins}-{losses}-{ties}"
    headline = preview.get("headline", "")
    body = preview.get("body", "")

    # Headline: replace common edge/dominance framing with neutral history framing.
    headline_patterns = (
        r"(?i)\bhistorical edge\b",
        r"(?i)\bhistory(?:'s)? edge\b",
        r"(?i)\bhistorical advantage\b",
        r"(?i)\bhistorical dominance\b",
        r"(?i)\bhistory favors\b",
    )
    for pattern in headline_patterns:
        headline = re.sub(pattern, "Even History", headline)

    # Body: neutralize explicit even-record edge constructions while preserving
    # the rest of the preview, especially projections.
    body = re.sub(
        rf"(?i)(?:[A-Za-z0-9_ ❤️🏆'.-]+\s+)?holds?\s+(?:a|the)?\s*"
        rf"{re.escape(record)}\s+(?:historical\s+)?(?:edge|advantage)",
        f"the historical series is even at {record}",
        body,
    )
    body = re.sub(
        rf"(?i)history\s+favors\s+[^,.]+(?:,|\s)+(?:with\s+)?(?:a\s+)?"
        rf"{re.escape(record)}(?:\s+(?:record|edge|advantage))?",
        f"the historical series is even at {record}",
        body,
    )
    body = re.sub(
        rf"(?i)(?:historical\s+)?(?:edge|advantage|dominance)\s+"
        rf"(?:at|of|with)\s+{re.escape(record)}",
        f"even historical series at {record}",
        body,
    )

    # If edge language survived but the exact record is present, replace the
    # offending sentence conservatively with a neutral statement.
    sentences = re.split(r"(?<=[.!?])\s+", body)
    repaired = []
    for sentence in sentences:
        lowered = sentence.casefold()
        if record in sentence and any(
            phrase in lowered
            for phrase in (
                "historical edge",
                "historical advantage",
                "historical dominance",
                "history favors",
            )
        ):
            repaired.append(f"The historical series is even at {record}.")
        else:
            repaired.append(sentence)
    body = " ".join(s for s in repaired if s)

    preview["headline"] = headline
    preview["body"] = body


def apply_deterministic_article_repairs(article, packet, validation_error):
    """
    Repair only factual errors that have one deterministic interpretation.

    Returns (article, repaired_bool, message).
    """
    if not isinstance(validation_error, str):
        return article, False, None

    # Historical H2H evidence mislabeled as all-play.
    stat_label = re.search(
        r"Preview (.+?) vs (.+?) labels historical H2H evidence as all-play\.",
        validation_error,
    )
    if stat_label:
        team_1, team_2 = stat_label.groups()
        for preview in article.get("next_week", {}).get("previews", []):
            if preview.get("team_1") == team_1 and preview.get("team_2") == team_2:
                preview["headline"] = re.sub(
                    r"(?i)\ball[- ]play\b", "Head-to-Head", preview.get("headline", "")
                )
                preview["body"] = re.sub(
                    r"(?i)\ball[- ]play\b", "head-to-head", preview.get("body", "")
                )
                return (
                    article,
                    True,
                    f"corrected H2H/all-play terminology for {team_1} vs {team_2}",
                )

    # Directional H2H series assigned to the wrong team.
    directional = re.search(
        r"Preview (.+?) vs (.+?) assigns the historical edge to (.+?), "
        r"but the supplied H2H record favors (.+?)\.",
        validation_error,
    )
    if directional:
        team_1, team_2, unfavored, favored = directional.groups()

        source = None
        for matchup in packet.get("future_matchups", {}).get("matchups", []):
            if matchup.get("team_1") == team_1 and matchup.get("team_2") == team_2:
                source = matchup
                break

        record = None
        if source:
            h2h_objects = []

            def walk_directional(value):
                if isinstance(value, dict):
                    if (
                        isinstance(value.get("team"), str)
                        and isinstance(value.get("wins"), (int, float))
                        and isinstance(value.get("losses"), (int, float))
                    ):
                        h2h_objects.append(value)
                    for item in value.values():
                        walk_directional(item)
                elif isinstance(value, list):
                    for item in value:
                        walk_directional(item)

            walk_directional(source)

            for h2h in h2h_objects:
                team = h2h.get("team")
                wins = int(h2h.get("wins", 0))
                losses = int(h2h.get("losses", 0))
                ties = int(h2h.get("ties", 0) or 0)
                opponent = team_2 if team == team_1 else team_1 if team == team_2 else None
                if not opponent or wins == losses:
                    continue
                actual_favored = team if wins > losses else opponent
                if actual_favored == favored:
                    record = f"{wins}-{losses}-{ties}"
                    # If the record is stored from the unfavored team's perspective,
                    # reverse W/L so the neutral replacement is from favored's perspective.
                    if team != favored:
                        record = f"{losses}-{wins}-{ties}"
                    break

        for preview in article.get("next_week", {}).get("previews", []):
            if preview.get("team_1") != team_1 or preview.get("team_2") != team_2:
                continue

            headline = preview.get("headline", "")
            body = preview.get("body", "")

            # Replace only explicit wrong-edge clauses. Keep projections and other
            # matchup context untouched.
            wrong_name = re.escape(unfavored)
            favored_name = favored
            body = re.sub(
                rf"(?i){wrong_name}\s+holds?\s+(?:a|the)\s+"
                rf"(?:\d+-\d+(?:-\d+)?\s+)?(?:historical\s+)?"
                rf"(?:edge|advantage|dominance)",
                (
                    f"{favored_name} holds the historical edge"
                    if not record
                    else f"{favored_name} holds a {record} historical edge"
                ),
                body,
            )
            body = re.sub(
                rf"(?i)history\s+favors\s+{wrong_name}",
                f"history favors {favored_name}",
                body,
            )
            body = re.sub(
                rf"(?i){wrong_name}.{{0,35}}(?:historical\s+)?"
                rf"(?:edge|advantage|dominance)",
                (
                    f"{favored_name} holds the historical edge"
                    if not record
                    else f"{favored_name} holds a {record} historical edge"
                ),
                body,
            )

            # Headlines that explicitly assign history to the wrong side get a
            # neutral replacement; no need to manufacture a new joke in Python.
            if (
                unfavored.casefold() in headline.casefold()
                and any(
                    phrase in headline.casefold()
                    for phrase in ("historical edge", "history favors",
                                   "historical advantage", "historical dominance")
                )
            ):
                headline = "The Historical Ledger"

            preview["headline"] = headline
            preview["body"] = body
            return (
                article,
                True,
                f"corrected H2H edge direction for {team_1} vs {team_2}; "
                f"history favors {favored}",
            )

    # Even H2H series incorrectly described as having an edge.
    match = re.search(
        r"Preview (.+?) vs (.+?) describes an even historical series "
        r"\((\d+)-(\d+)\) as having an edge\.",
        validation_error,
    )
    if match:
        team_1, team_2 = match.group(1), match.group(2)
        wins, losses = int(match.group(3)), int(match.group(4))

        future = packet.get("future_matchups", {})
        source = None
        for matchup in future.get("matchups", []):
            if matchup.get("team_1") == team_1 and matchup.get("team_2") == team_2:
                source = matchup
                break

        ties = 0
        if source:
            h2h_objects = []

            def walk(value):
                if isinstance(value, dict):
                    if (
                        isinstance(value.get("team"), str)
                        and isinstance(value.get("wins"), (int, float))
                        and isinstance(value.get("losses"), (int, float))
                    ):
                        h2h_objects.append(value)
                    for item in value.values():
                        walk(item)
                elif isinstance(value, list):
                    for item in value:
                        walk(item)

            walk(source)
            for h2h in h2h_objects:
                if int(h2h.get("wins", -1)) == wins and int(h2h.get("losses", -1)) == losses:
                    ties = int(h2h.get("ties", 0) or 0)
                    break

        for preview in article.get("next_week", {}).get("previews", []):
            if preview.get("team_1") == team_1 and preview.get("team_2") == team_2:
                _replace_h2h_edge_language_for_even_preview(
                    preview, wins, losses, ties
                )
                return (
                    article,
                    True,
                    f"neutralized even-series H2H language for "
                    f"{team_1} vs {team_2} ({wins}-{losses}-{ties})",
                )

    return article, False, None


def validate_with_deterministic_repairs(article, packet, max_passes=4):
    """
    Validate, applying safe Python repairs when the validation error has exactly
    one factual interpretation. Revalidate after every repair.
    """
    for _ in range(max_passes):
        error = article_validation_error(article, packet)
        if error is None:
            return article, None

        article, repaired, message = apply_deterministic_article_repairs(
            article, packet, error
        )
        if not repaired:
            return article, error

        print(f"[FIX] Python repair: {message}")

    return article, article_validation_error(article, packet)


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
                temperature=0.70 if attempt == 1 else 0.10,
                max_output_tokens=6500,
                response_mime_type="application/json",
            ),
        )

        try:
            article = extract_json(response.text)
        except RuntimeError as exc:
            # Invalid JSON is a generation failure, not a reason to abort the whole run.
            # There is no usable draft to repair, so retry from the original generation
            # prompt on the next attempt.
            last_error = str(exc)
            if attempt < MAX_GENERATION_ATTEMPTS:
                print(
                    f"Generation attempt {attempt} returned invalid JSON; "
                    "retrying from the original article prompt."
                )
                prompt = build_prompt(packet)
                continue
            break

        article, last_error = validate_with_deterministic_repairs(
            article, packet
        )

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
    print("Generating article with automatic validation/repair + copy edit...")

    article = generate_and_validate(
        client=client,
        model=model,
        packet=packet,
    )

    # The first pass owns story selection and factual assembly. The second pass has
    # the narrower job of making the already-valid article sound like a newspaper.
    article = copy_edit_and_validate(
        client=client,
        model=model,
        packet=packet,
        article=article,
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