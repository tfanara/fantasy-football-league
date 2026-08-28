import streamlit as st
import pandas as pd
from pathlib import Path
import re

try:
    from google import genai
    from google.genai import types
except ImportError:
    st.error(
        "The Google Gemini SDK is not installed. "
        "Add `google-genai` to requirements.txt."
    )
    st.stop()


# -----------------------------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="League Historian | Malle's League",
    page_icon="📚",
    layout="wide",
)

st.title("📚 The League Historian")
st.caption(
    "Ask about league history, records, luck, championships, head-to-head "
    "results, player scoring, lineup decisions, drafts, and more."
)


# -----------------------------------------------------------------------------
# PATHS
# -----------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
HISTORY_DIR = DATA_DIR / "history"
PLAYOFF_DIR = DATA_DIR / "playoffs"
DRAFT_DIR = DATA_DIR / "drafts"
KEEPER_DIR = DATA_DIR / "keepers"
PLAYER_WEEK_DIR = DATA_DIR / "matchups" / "player_week_stats"
ANALYSIS_DIR = PLAYER_WEEK_DIR / "analysis"

FILES = {
    "all_time_records": HISTORY_DIR / "all_time_records.csv",
    "season_records": HISTORY_DIR / "season_records.csv",
    "team_games": HISTORY_DIR / "team_games.csv",
    "head_to_head": HISTORY_DIR / "head_to_head.csv",
    "highest_scores": HISTORY_DIR / "highest_scores.csv",
    "lowest_scores": HISTORY_DIR / "lowest_scores.csv",
    "biggest_blowouts": HISTORY_DIR / "biggest_blowouts.csv",
    "closest_games": HISTORY_DIR / "closest_games.csv",
    "championships": PLAYOFF_DIR / "championships.csv",
    "playoff_records": PLAYOFF_DIR / "playoff_records.csv",
    "playoff_appearances": PLAYOFF_DIR / "playoff_appearances.csv",
    "player_championship_pedigree": PLAYOFF_DIR / "player_championship_pedigree.csv",
    "keeper_history": KEEPER_DIR / "keeper_history.csv",
    "draft_position_strategy": DRAFT_DIR / "draft_position_strategy.csv",
    "all_drafts": DRAFT_DIR / "all_drafts.csv",
    "luck_season": ANALYSIS_DIR / "luck_season.csv",
    "luck_all_time": ANALYSIS_DIR / "luck_all_time.csv",
    "lineup_efficiency_season": ANALYSIS_DIR / "lineup_efficiency_season.csv",
    "lineup_efficiency_all_time": ANALYSIS_DIR / "lineup_efficiency_all_time.csv",
    "lineup_efficiency_team_week": ANALYSIS_DIR / "lineup_efficiency_team_week.csv",
    "weekly_lineups": PLAYER_WEEK_DIR / "all_weekly_lineups_2017_2025.csv",
}


# -----------------------------------------------------------------------------
# LOAD DATA
# -----------------------------------------------------------------------------

@st.cache_data
def load_datasets():
    data = {}

    for name, path in FILES.items():
        if path.exists():
            try:
                data[name] = pd.read_csv(path)
            except Exception:
                pass

    return data


data = load_datasets()


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def clean_text(value):
    return str(value or "").strip()


def dataframe_to_context(df, max_rows=30, max_cols=12):
    if df is None or df.empty:
        return "No matching rows."

    work = df.copy()

    if len(work.columns) > max_cols:
        work = work.iloc[:, :max_cols]

    if len(work) > max_rows:
        work = work.head(max_rows)

    return work.to_csv(index=False)


def get_known_teams():
    teams = set()

    for dataset_name in [
        "all_time_records",
        "season_records",
        "team_games",
        "luck_season",
        "lineup_efficiency_season",
    ]:
        df = data.get(dataset_name)

        if df is None:
            continue

        for col in ["team", "fantasy_team"]:
            if col in df.columns:
                teams.update(
                    df[col]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .tolist()
                )

    return sorted(teams, key=len, reverse=True)


KNOWN_TEAMS = get_known_teams()


def mentioned_teams(question):
    q = question.lower()
    found = []

    for team in KNOWN_TEAMS:
        if team.lower() in q:
            found.append(team)

    return found


def mentioned_years(question):
    return sorted(
        {
            int(x)
            for x in re.findall(r"\b(20(?:1[8-9]|2[0-6]))\b", question)
        }
    )


def player_leaders_for_team(team):
    df = data.get("weekly_lineups")

    if df is None or df.empty:
        return pd.DataFrame()

    work = df[
        df["fantasy_team"].astype(str).str.strip().eq(team)
    ].copy()

    if work.empty:
        return work

    if "is_starter" in work.columns:
        starter = (
            work["is_starter"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "yes"])
        )
        work = work[starter].copy()

    work = work[
        work["player"].astype(str).str.strip().ne("(Empty)")
    ].copy()

    work["fantasy_points"] = pd.to_numeric(
        work["fantasy_points"],
        errors="coerce",
    )

    return (
        work.groupby("player", as_index=False)
        .agg(
            career_points=("fantasy_points", "sum"),
            starts=("player", "size"),
            seasons=("year", "nunique"),
            best_game=("fantasy_points", "max"),
        )
        .sort_values(
            ["career_points", "starts"],
            ascending=[False, False],
        )
        .head(20)
    )


def filter_team_rows(df, teams):
    if df is None or df.empty or not teams:
        return df

    possible_cols = [
        "team",
        "fantasy_team",
        "team_1",
        "team_2",
        "champion",
        "runner_up",
        "winner",
        "loser",
        "opponent",
    ]

    mask = pd.Series(False, index=df.index)

    for col in possible_cols:
        if col in df.columns:
            mask = mask | df[col].astype(str).isin(teams)

    return df[mask].copy()


def filter_year_rows(df, years):
    if df is None or df.empty or not years:
        return df

    if "year" not in df.columns:
        return df

    return df[
        pd.to_numeric(df["year"], errors="coerce").isin(years)
    ].copy()


def build_evidence(question):
    q = question.lower()
    teams = mentioned_teams(question)
    years = mentioned_years(question)

    packets = []

    def add(name, df, max_rows=30):
        if df is None or df.empty:
            return

        filtered = filter_team_rows(df, teams)
        filtered = filter_year_rows(filtered, years)

        if filtered is None or filtered.empty:
            return

        packets.append(
            f"\n### {name}\n"
            + dataframe_to_context(filtered, max_rows=max_rows)
        )

    # Always include basic franchise records when a team is named.
    if teams:
        add("ALL-TIME FRANCHISE RECORDS", data.get("all_time_records"), 20)
        add("SEASON RECORDS", data.get("season_records"), 40)

        for team in teams:
            leaders = player_leaders_for_team(team)
            if not leaders.empty:
                packets.append(
                    f"\n### STARTING-LINEUP PLAYER SCORING LEADERS — {team}\n"
                    + dataframe_to_context(leaders, max_rows=20)
                )

    # Intent-driven evidence.
    if any(word in q for word in ["luck", "lucky", "unlucky", "cursed", "schedule", "expected win", "all-play", "all play"]):
        add("SEASON LUCK METRICS", data.get("luck_season"), 60)
        add("ALL-TIME LUCK METRICS", data.get("luck_all_time"), 40)

    if any(word in q for word in ["champion", "championship", "title", "trophy", "runner-up", "runner up"]):
        add("CHAMPIONSHIPS", data.get("championships"), 40)
        add("PLAYOFF RECORDS", data.get("playoff_records"), 30)
        add("PLAYER CHAMPIONSHIP PEDIGREE", data.get("player_championship_pedigree"), 40)

    if any(word in q for word in ["playoff", "postseason", "finals"]):
        add("PLAYOFF RECORDS", data.get("playoff_records"), 30)
        add("PLAYOFF APPEARANCES", data.get("playoff_appearances"), 40)
        add("CHAMPIONSHIPS", data.get("championships"), 40)

    if any(word in q for word in ["head to head", "head-to-head", "against", "record vs", "versus", " vs "]):
        add("HEAD-TO-HEAD", data.get("head_to_head"), 50)
        add("TEAM GAME HISTORY", data.get("team_games"), 50)

    if any(word in q for word in ["highest score", "lowest score", "blowout", "closest", "margin", "game ever", "matchup ever"]):
        add("HIGHEST SCORES", data.get("highest_scores"), 30)
        add("LOWEST SCORES", data.get("lowest_scores"), 30)
        add("BIGGEST BLOWOUTS", data.get("biggest_blowouts"), 30)
        add("CLOSEST GAMES", data.get("closest_games"), 30)

    if any(word in q for word in ["lineup", "bench", "efficiency", "should have started", "should've started", "points left"]):
        add("SEASON LINEUP EFFICIENCY", data.get("lineup_efficiency_season"), 50)
        add("ALL-TIME LINEUP EFFICIENCY", data.get("lineup_efficiency_all_time"), 40)
        add("WEEKLY LINEUP EFFICIENCY", data.get("lineup_efficiency_team_week"), 50)

    if any(word in q for word in ["draft", "pick", "round", "drafted"]):
        add("DRAFT POSITION STRATEGY", data.get("draft_position_strategy"), 50)
        add("DRAFT HISTORY", data.get("all_drafts"), 50)

    if any(word in q for word in ["keeper", "kept"]):
        add("KEEPER HISTORY", data.get("keeper_history"), 50)

    if any(word in q for word in ["leading scorer", "scorer", "player points", "best player", "most points"]):
        if teams:
            pass
        else:
            # For league-wide player questions, build a compact top list from all starters.
            df = data.get("weekly_lineups")
            if df is not None and not df.empty:
                work = df.copy()

                if "is_starter" in work.columns:
                    starter = (
                        work["is_starter"]
                        .astype(str)
                        .str.lower()
                        .isin(["true", "1", "yes"])
                    )
                    work = work[starter]

                work["fantasy_points"] = pd.to_numeric(
                    work["fantasy_points"],
                    errors="coerce",
                )

                leaders = (
                    work[
                        work["player"].astype(str).str.strip().ne("(Empty)")
                    ]
                    .groupby("player", as_index=False)
                    .agg(
                        counted_points=("fantasy_points", "sum"),
                        starts=("player", "size"),
                    )
                    .sort_values("counted_points", ascending=False)
                    .head(30)
                )

                packets.append(
                    "\n### LEAGUE-WIDE COUNTED STARTER POINTS BY PLAYER\n"
                    + dataframe_to_context(leaders, 30)
                )

    # Generic fallback: enough context to answer broad league questions.
    if not packets:
        add("ALL-TIME FRANCHISE RECORDS", data.get("all_time_records"), 30)
        add("CHAMPIONSHIPS", data.get("championships"), 30)
        add("ALL-TIME LUCK METRICS", data.get("luck_all_time"), 30)
        add("ALL-TIME LINEUP EFFICIENCY", data.get("lineup_efficiency_all_time"), 30)

    return "\n".join(packets), teams, years


# -----------------------------------------------------------------------------
# GEMINI
# -----------------------------------------------------------------------------

def get_client():
    if "GEMINI_API_KEY" not in st.secrets:
        return None

    return genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )


def ask_historian(question):
    evidence, teams, years = build_evidence(question)

    client = get_client()

    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured in Streamlit Secrets."
        )

    model = st.secrets.get(
        "GEMINI_MODEL",
        "gemini-2.5-flash-lite",
    )

    prompt = f"""
You are THE LEAGUE HISTORIAN for a private fantasy football league.

PERSONALITY:
- Knowledgeable, concise, confident, and entertaining.
- Light sarcasm is welcome when the numbers justify it.
- Do not force jokes into every answer.
- Never insult a real person outside the context of fantasy-football performance.

GROUNDING RULES:
1. Answer ONLY from the LEAGUE DATA supplied below.
2. Never invent a score, record, player, season, championship, ranking, or statistic.
3. If the supplied data is insufficient to answer the question, say exactly that.
4. When calculations are simple and directly supported by the supplied rows, you may calculate them.
5. Distinguish actual wins from expected wins when discussing luck.
6. "Player career points" means fantasy points that actually counted in that franchise's STARTING lineup unless the evidence says otherwise.
7. Championship-player counts use the champion's final regular-season roster as a proxy, not verified playoff-week rosters.
8. Regular-season weekly player history currently covers 2017-2025.
9. Use exact numbers when useful, usually rounded to 1-2 decimal places.
10. Do not mention Gemini, prompts, CSV files, or internal implementation details.

USER QUESTION:
{question}

MENTIONED TEAMS:
{teams}

MENTIONED YEARS:
{years}

LEAGUE DATA:
{evidence}

Answer the user's question directly. If there is a clear winner/loser/ranking, lead with it.
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.25,
            max_output_tokens=700,
        ),
    )

    return response.text


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

if "historian_messages" not in st.session_state:
    st.session_state.historian_messages = []


with st.expander("What can I ask?", expanded=False):
    st.markdown(
        """
Try questions like:

- **Who had the luckiest season ever?**
- **Who has the most championships?**
- **Who is Voldemort's all-time leading scorer?**
- **What is Joe Mantegna's record against Post Mahomes?**
- **Who had the hardest schedule in 2022?**
- **What was the worst lineup decision ever?**
- **Which players have been on the most championship teams?**
- **What is the highest score in league history?**
- **Who has the best all-time lineup efficiency?**
        """
    )


suggestions = [
    "Who had the luckiest season ever?",
    "Who has been on the most championship teams?",
    "What is the highest score in league history?",
    "Who has the best all-time lineup efficiency?",
]

cols = st.columns(4)

suggested_prompt = None

for col, suggestion in zip(cols, suggestions):
    with col:
        if st.button(
            suggestion,
            use_container_width=True,
        ):
            suggested_prompt = suggestion


for message in st.session_state.historian_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


typed_prompt = st.chat_input(
    "Ask the League Historian..."
)

prompt = typed_prompt or suggested_prompt

if prompt:
    st.session_state.historian_messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consulting the archives..."):
            try:
                answer = ask_historian(prompt)
            except Exception as exc:
                answer = (
                    "The archives are intact, but the Historian could not "
                    f"complete that request: `{exc}`"
                )

        st.markdown(answer)

    st.session_state.historian_messages.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )


with st.sidebar:
    st.subheader("League Historian")

    st.caption(
        "Answers are generated from the league's validated historical datasets."
    )

    if st.button("Clear Historian Chat"):
        st.session_state.historian_messages = []
        st.rerun()