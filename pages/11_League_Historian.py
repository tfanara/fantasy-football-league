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
    "Ask about league history, manager profiles, seasons, players, drafts, "
    "waivers, luck, positional strengths, championships, rivalries, and more."
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
TRANSACTION_DIR = DATA_DIR / "transactions"
PLAYER_WEEK_DIR = DATA_DIR / "matchups" / "player_week_stats"

# Older weekly analytics live beside the player-week master.
LEGACY_ANALYSIS_DIR = PLAYER_WEEK_DIR / "analysis"

# Newer league-wide analyses live here.
ANALYSIS_DIR = DATA_DIR / "analysis"


def first_existing(*paths):
    """Return the first existing path, otherwise the first candidate."""
    for path in paths:
        if path.exists():
            return path
    return paths[0]


FILES = {
    # Core franchise / matchup history
    "all_time_records": HISTORY_DIR / "all_time_records.csv",
    "season_records": HISTORY_DIR / "season_records.csv",
    "team_games": HISTORY_DIR / "team_games.csv",
    "head_to_head": HISTORY_DIR / "head_to_head.csv",
    "highest_scores": HISTORY_DIR / "highest_scores.csv",
    "lowest_scores": HISTORY_DIR / "lowest_scores.csv",
    "biggest_blowouts": HISTORY_DIR / "biggest_blowouts.csv",
    "closest_games": HISTORY_DIR / "closest_games.csv",
    "clean_matchups": first_existing(
        DATA_DIR / "all_matchups_clean_2017_2025.csv",
        PLAYER_WEEK_DIR / "all_matchups_2017_2025.csv",
        PLAYER_WEEK_DIR / "all_matchups_2018_2025.csv",
    ),

    # Playoffs / championships
    "championships": PLAYOFF_DIR / "championships.csv",
    "playoff_records": PLAYOFF_DIR / "playoff_records.csv",
    "playoff_appearances": PLAYOFF_DIR / "playoff_appearances.csv",
    "player_championship_pedigree": PLAYOFF_DIR / "player_championship_pedigree.csv",
    "player_championship_rosters": PLAYOFF_DIR / "player_championship_rosters.csv",

    # Drafts / keepers / transactions
    "keeper_history": KEEPER_DIR / "keeper_history.csv",
    "draft_position_strategy": DRAFT_DIR / "draft_position_strategy.csv",
    "all_drafts": DRAFT_DIR / "all_drafts.csv",
    "transactions": TRANSACTION_DIR / "all_transactions.csv",

    # Weekly lineup history
    "weekly_lineups": first_existing(
        PLAYER_WEEK_DIR / "all_weekly_lineups_2017_2025.csv",
        PLAYER_WEEK_DIR / "all_weekly_lineups_2018_2025.csv",
    ),

    # Lineup efficiency + luck (legacy analysis location)
    "luck_team_week": first_existing(
        LEGACY_ANALYSIS_DIR / "luck_team_week.csv",
        ANALYSIS_DIR / "luck_team_week.csv",
    ),
    "luck_season": first_existing(
        LEGACY_ANALYSIS_DIR / "luck_season.csv",
        ANALYSIS_DIR / "luck_season.csv",
    ),
    "luck_all_time": first_existing(
        LEGACY_ANALYSIS_DIR / "luck_all_time.csv",
        ANALYSIS_DIR / "luck_all_time.csv",
    ),
    "lineup_efficiency_season": first_existing(
        LEGACY_ANALYSIS_DIR / "lineup_efficiency_season.csv",
        ANALYSIS_DIR / "lineup_efficiency_season.csv",
    ),
    "lineup_efficiency_all_time": first_existing(
        LEGACY_ANALYSIS_DIR / "lineup_efficiency_all_time.csv",
        ANALYSIS_DIR / "lineup_efficiency_all_time.csv",
    ),
    "lineup_efficiency_team_week": first_existing(
        LEGACY_ANALYSIS_DIR / "lineup_efficiency_team_week.csv",
        ANALYSIS_DIR / "lineup_efficiency_team_week.csv",
    ),

    # Draft Value
    "draft_value_picks": ANALYSIS_DIR / "draft_value_picks.csv",
    "draft_value_franchise": ANALYSIS_DIR / "draft_value_franchise.csv",
    "draft_value_team_season": ANALYSIS_DIR / "draft_value_team_season.csv",
    "draft_value_first_round": ANALYSIS_DIR / "draft_value_first_round.csv",
    "draft_value_late_round_steals": ANALYSIS_DIR / "draft_value_late_round_steals.csv",

    # Waiver Value
    "waiver_value_acquisitions": ANALYSIS_DIR / "waiver_value_acquisitions.csv",
    "waiver_value_franchise": ANALYSIS_DIR / "waiver_value_franchise.csv",
    "waiver_value_team_season": ANALYSIS_DIR / "waiver_value_team_season.csv",
    "waiver_value_hall_of_fame": ANALYSIS_DIR / "waiver_value_hall_of_fame.csv",

    # Management Index
    "management_index_team_season": ANALYSIS_DIR / "management_index_team_season.csv",
    "management_index_franchise": ANALYSIS_DIR / "management_index_franchise.csv",
    "management_index_extremes": ANALYSIS_DIR / "management_index_extremes.csv",
    "management_index_profiles": ANALYSIS_DIR / "management_index_profiles.csv",

    # Bad Beats
    "bad_beat_team_week": ANALYSIS_DIR / "bad_beat_team_week.csv",
    "bad_beat_season": ANALYSIS_DIR / "bad_beat_season.csv",
    "bad_beat_franchise": ANALYSIS_DIR / "bad_beat_franchise.csv",
    "bad_beat_history": ANALYSIS_DIR / "bad_beat_history.csv",
    "lucky_win_history": ANALYSIS_DIR / "lucky_win_history.csv",

    # Schedule Swap
    "schedule_swap_season": ANALYSIS_DIR / "schedule_swap_season.csv",
    "schedule_swap_franchise": ANALYSIS_DIR / "schedule_swap_franchise.csv",
    "schedule_swap_extremes": ANALYSIS_DIR / "schedule_swap_extremes.csv",
    "schedule_swap_matrix_long": ANALYSIS_DIR / "schedule_swap_matrix_long.csv",

    # Positional Edge
    "positional_edge_team_week": ANALYSIS_DIR / "positional_edge_team_week.csv",
    "positional_edge_season": ANALYSIS_DIR / "positional_edge_season.csv",
    "positional_edge_franchise": ANALYSIS_DIR / "positional_edge_franchise.csv",
    "positional_edge_extremes": ANALYSIS_DIR / "positional_edge_extremes.csv",
    "positional_edge_player_contributions": ANALYSIS_DIR / "positional_edge_player_contributions.csv",

    # Championship DNA
    "championship_dna_team_season": ANALYSIS_DIR / "championship_dna_team_season.csv",
    "championship_dna_champions": ANALYSIS_DIR / "championship_dna_champions.csv",
    "championship_dna_comparison": ANALYSIS_DIR / "championship_dna_comparison.csv",
    "championship_dna_traits": ANALYSIS_DIR / "championship_dna_traits.csv",

    # QB/WR stacking
    "stack_summary": ANALYSIS_DIR / "qb_wr_stack_summary.csv",
    "stack_team_season": ANALYSIS_DIR / "qb_wr_stack_team_season.csv",
    "stack_by_franchise": ANALYSIS_DIR / "qb_wr_stack_by_franchise.csv",
    "stack_pairs": ANALYSIS_DIR / "qb_wr_stack_pairs.csv",
}


# -----------------------------------------------------------------------------
# LOAD DATA
# -----------------------------------------------------------------------------

TEAM_ALIASES = {
    "PickUpYourBratsMalle": "ThreatLevelMidnight",
    "Little Red Fournette": "Post Mahomes",
    "Ur The Best Bellows": "Joe Mantegna",
    "You Better Park It": "Buttermilk Puuump",
    "Buttermilk Pump": "Buttermilk Puuump",
}

TEAM_COLUMNS = [
    "team",
    "fantasy_team",
    "canonical_team",
    "opponent",
    "team_1",
    "team_2",
    "team_a",
    "team_b",
    "left_team",
    "right_team",
    "champion",
    "runner_up",
    "winner",
    "loser",
    "franchise",
    "donor_team",
    "schedule_team",
]

PLAYER_COLUMNS = [
    "player",
    "qb",
    "wr",
    "keeper",
    "player_name",
]


def canonical_team(value):
    if pd.isna(value):
        return value
    value = str(value).strip()
    return TEAM_ALIASES.get(value, value)


def normalize_team_names(df):
    df = df.copy()

    for col in TEAM_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(canonical_team)

    return df


@st.cache_data
def load_datasets():
    loaded = {}

    for name, path in FILES.items():
        if not path.exists():
            continue

        try:
            df = pd.read_csv(path)
            loaded[name] = normalize_team_names(df)
        except Exception:
            # One bad optional analysis file should not take down the Historian.
            continue

    return loaded


data = load_datasets()


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def clean_text(value):
    return str(value or "").strip()


def dataframe_to_context(df, max_rows=30, max_cols=16):
    if df is None or df.empty:
        return "No matching rows."

    work = df.copy()

    if len(work.columns) > max_cols:
        work = work.iloc[:, :max_cols]

    if len(work) > max_rows:
        work = work.head(max_rows)

    return work.to_csv(index=False)


def contains_any(text, terms):
    return any(term in text for term in terms)


def get_known_teams():
    teams = set()

    for df in data.values():
        if df is None or df.empty:
            continue

        for col in TEAM_COLUMNS:
            if col in df.columns:
                teams.update(
                    canonical_team(value)
                    for value in df[col].dropna().astype(str)
                    if clean_text(value)
                )

    return sorted(
        {team for team in teams if clean_text(team)},
        key=len,
        reverse=True,
    )


def get_known_players():
    players = set()

    for dataset_name in [
        "weekly_lineups",
        "all_drafts",
        "keeper_history",
        "waiver_value_acquisitions",
        "player_championship_pedigree",
        "positional_edge_player_contributions",
    ]:
        df = data.get(dataset_name)

        if df is None or df.empty:
            continue

        for col in PLAYER_COLUMNS:
            if col in df.columns:
                players.update(
                    df[col]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .tolist()
                )

    players.discard("")
    players.discard("(Empty)")

    return sorted(players, key=len, reverse=True)


KNOWN_TEAMS = get_known_teams()
KNOWN_PLAYERS = get_known_players()


def mentioned_teams(question):
    q = question.casefold()
    found = []

    # Accept both the canonical current name and the historical aliases.
    candidates = list(KNOWN_TEAMS) + list(TEAM_ALIASES.keys())

    for team in sorted(set(candidates), key=len, reverse=True):
        if team.casefold() in q:
            canonical = canonical_team(team)
            if canonical not in found:
                found.append(canonical)

    return found


def mentioned_players(question):
    q = question.casefold()
    found = []

    for player in KNOWN_PLAYERS:
        if player.casefold() in q:
            found.append(player)

        if len(found) >= 5:
            break

    return found


def mentioned_years(question):
    return sorted(
        {
            int(x)
            for x in re.findall(r"\b(20(?:1[7-9]|2[0-6]))\b", question)
        }
    )


def filter_entity_rows(df, teams=None, players=None, years=None):
    if df is None or df.empty:
        return df

    work = df.copy()

    if teams:
        team_mask = pd.Series(False, index=work.index)

        for col in TEAM_COLUMNS:
            if col in work.columns:
                team_mask = (
                    team_mask
                    | work[col].astype(str).isin(teams)
                )

        # Only apply the team filter when this dataset actually has team columns.
        if any(col in work.columns for col in TEAM_COLUMNS):
            work = work[team_mask].copy()

    if players:
        player_mask = pd.Series(False, index=work.index)

        for col in PLAYER_COLUMNS:
            if col in work.columns:
                player_mask = (
                    player_mask
                    | work[col].astype(str).isin(players)
                )

        if any(col in work.columns for col in PLAYER_COLUMNS):
            work = work[player_mask].copy()

    if years and "year" in work.columns:
        work = work[
            pd.to_numeric(
                work["year"],
                errors="coerce",
            ).isin(years)
        ].copy()

    return work


def sort_for_context(df):
    if df is None or df.empty:
        return df

    work = df.copy()

    sort_candidates = [
        ("year", False),
        ("week", False),
        ("rank", True),
        ("management_rank", True),
        ("draft_value_rank", True),
        ("waiver_value_rank", True),
        ("luck_rank", True),
        ("fantasy_points", False),
        ("points_for", False),
    ]

    cols = []
    ascending = []

    for col, asc in sort_candidates:
        if col in work.columns:
            cols.append(col)
            ascending.append(asc)

    if cols:
        try:
            work = work.sort_values(
                cols,
                ascending=ascending,
                na_position="last",
            )
        except Exception:
            pass

    return work


def player_leaders_for_team(team):
    df = data.get("weekly_lineups")

    if df is None or df.empty:
        return pd.DataFrame()

    if "fantasy_team" not in df.columns:
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

    if "player" not in work.columns or "fantasy_points" not in work.columns:
        return pd.DataFrame()

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


def league_player_leaders():
    df = data.get("weekly_lineups")

    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    if "is_starter" in work.columns:
        starter = (
            work["is_starter"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "yes"])
        )
        work = work[starter].copy()

    if "player" not in work.columns or "fantasy_points" not in work.columns:
        return pd.DataFrame()

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
            counted_points=("fantasy_points", "sum"),
            starts=("player", "size"),
            seasons=("year", "nunique"),
            best_game=("fantasy_points", "max"),
        )
        .sort_values(
            ["counted_points", "starts"],
            ascending=[False, False],
        )
        .head(30)
    )



def prior_conversation_messages(question):
    """
    Return recent messages before the current prompt.

    The UI appends the user's current question to session_state before
    ask_historian() runs, so strip that duplicate current-turn message.
    """
    messages = list(
        st.session_state.get(
            "historian_messages",
            [],
        )
    )

    if messages:
        last = messages[-1]
        if (
            last.get("role") == "user"
            and clean_text(last.get("content")) == clean_text(question)
        ):
            messages = messages[:-1]

    return messages[-8:]


def resolve_conversation_entities(question, prior_messages):
    """
    Resolve obvious follow-up references such as:
      - "his roster"
      - "that season"
      - "who were his best players?"
      - "what about the draft?"

    We only carry an entity forward when the current question does not
    already identify one. Ambiguous years remain unresolved so the model
    can either use the supplied multi-season roster table or ask a concise
    clarification.
    """
    teams = mentioned_teams(question)
    players = mentioned_players(question)
    years = mentioned_years(question)

    q = question.casefold()

    followup_language = contains_any(
        q,
        [
            "his ",
            "her ",
            "their ",
            "that ",
            "those ",
            "he ",
            "she ",
            "they ",
            "them ",
            "him ",
            "same ",
            "roster",
            "season",
            "year",
            "what about",
            "how about",
            "and ",
        ],
    )

    if not prior_messages or not followup_language:
        return teams, players, years, []

    # Team references are most reliably carried from the most recent
    # earlier USER message that named a franchise. If none exists,
    # fall back to the assistant's most recent named franchise.
    if not teams:
        for preferred_role in ["user", "assistant"]:
            for message in reversed(prior_messages):
                if message.get("role") != preferred_role:
                    continue

                found = mentioned_teams(
                    clean_text(message.get("content"))
                )

                if found:
                    teams = found[:2]
                    break

            if teams:
                break

    # Carry a player only when the current turn clearly uses a pronoun
    # or "that player" style follow-up and the earlier message has one
    # unambiguous player.
    if not players and contains_any(
        q,
        [
            "him",
            "his ",
            "that player",
            "the player",
            "he ",
        ],
    ):
        for message in reversed(prior_messages):
            found = mentioned_players(
                clean_text(message.get("content"))
            )

            if len(found) == 1:
                players = found
                break

    # A year is only auto-carried when the nearest relevant prior message
    # contains exactly one year. If the prior answer discussed 2020 AND
    # 2025, "that year" is genuinely ambiguous and we should not guess.
    year_candidates = []

    if not years and contains_any(
        q,
        [
            "that year",
            "that season",
            "same year",
            "same season",
            "that roster",
            "his roster",
            "their roster",
        ],
    ):
        for message in reversed(prior_messages):
            found = mentioned_years(
                clean_text(message.get("content"))
            )

            if found:
                year_candidates = found

                if len(found) == 1:
                    years = found

                break

    return teams, players, years, year_candidates


def team_season_player_summary(
    team,
    years=None,
    top_n_per_season=10,
):
    """
    Build a season-specific roster/player table from weekly lineup history.

    `starter_points` = fantasy points that actually counted in the starting
    lineup for that franchise.
    `rostered_points` = fantasy points produced during weeks the player
    appeared anywhere on that fantasy roster, including bench weeks.

    This lets the Historian answer questions like:
      "Who were Uncle Rico's best players in 2025?"
      "Who carried them that season?"
      "Who was on his roster?"
    """
    df = data.get("weekly_lineups")

    if df is None or df.empty:
        return pd.DataFrame()

    required = {
        "fantasy_team",
        "year",
        "week",
        "player",
        "fantasy_points",
    }

    if not required.issubset(df.columns):
        return pd.DataFrame()

    work = df[
        df["fantasy_team"]
        .astype(str)
        .str.strip()
        .eq(team)
    ].copy()

    if work.empty:
        return work

    work["year"] = pd.to_numeric(
        work["year"],
        errors="coerce",
    )
    work["week"] = pd.to_numeric(
        work["week"],
        errors="coerce",
    )
    work["fantasy_points"] = pd.to_numeric(
        work["fantasy_points"],
        errors="coerce",
    )

    if years:
        work = work[
            work["year"].isin(years)
        ].copy()

    work = work[
        work["player"]
        .astype(str)
        .str.strip()
        .ne("(Empty)")
    ].copy()

    if work.empty:
        return work

    if "is_starter" in work.columns:
        work["_starter"] = (
            work["is_starter"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "yes"])
        )
    else:
        bench_slots = {"BN", "IR", "IR+"}
        if "lineup_slot" in work.columns:
            work["_starter"] = ~(
                work["lineup_slot"]
                .astype(str)
                .str.upper()
                .isin(bench_slots)
            )
        else:
            work["_starter"] = True

    work["_starter_points"] = work[
        "fantasy_points"
    ].where(
        work["_starter"],
        0.0,
    )

    work["_starter_game"] = work[
        "fantasy_points"
    ].where(
        work["_starter"],
        pd.NA,
    )

    position_col = None
    for candidate in [
        "fantasy_position",
        "position",
        "player_position",
    ]:
        if candidate in work.columns:
            position_col = candidate
            break

    group_cols = [
        "year",
        "player",
    ]

    summary = (
        work.groupby(
            group_cols,
            as_index=False,
        )
        .agg(
            rostered_weeks=("week", "nunique"),
            starts=("_starter", "sum"),
            starter_points=("_starter_points", "sum"),
            rostered_points=("fantasy_points", "sum"),
            best_started_game=("_starter_game", "max"),
        )
    )

    summary["starts"] = pd.to_numeric(
        summary["starts"],
        errors="coerce",
    ).fillna(0).astype(int)

    summary["starter_points"] = pd.to_numeric(
        summary["starter_points"],
        errors="coerce",
    ).fillna(0)

    summary["rostered_points"] = pd.to_numeric(
        summary["rostered_points"],
        errors="coerce",
    ).fillna(0)

    summary["starter_ppg"] = (
        summary["starter_points"]
        / summary["starts"].replace(0, pd.NA)
    )

    if position_col:
        positions = (
            work.dropna(subset=[position_col])
            .assign(
                _position=lambda x: (
                    x[position_col]
                    .astype(str)
                    .str.strip()
                )
            )
            .groupby(
                ["year", "player"]
            )["_position"]
            .agg(
                lambda values: (
                    values.mode().iloc[0]
                    if not values.mode().empty
                    else values.iloc[0]
                )
            )
            .reset_index()
            .rename(
                columns={
                    "_position": "position",
                }
            )
        )

        summary = summary.merge(
            positions,
            on=["year", "player"],
            how="left",
        )

    summary = summary.sort_values(
        [
            "year",
            "starter_points",
            "starts",
            "rostered_points",
        ],
        ascending=[
            False,
            False,
            False,
            False,
        ],
    )

    # Keep the best N players for EACH season instead of letting one
    # season crowd all the others out when a follow-up year is ambiguous.
    summary = (
        summary.groupby(
            "year",
            group_keys=False,
        )
        .head(top_n_per_season)
        .reset_index(drop=True)
    )

    return summary



def build_evidence(question, prior_messages=None):
    q = question.casefold()

    if prior_messages is None:
        prior_messages = prior_conversation_messages(question)

    teams, players, years, year_candidates = (
        resolve_conversation_entities(
            question,
            prior_messages,
        )
    )

    packets = []
    added_names = set()

    def add(
        label,
        dataset_name,
        max_rows=30,
        *,
        apply_entities=True,
    ):
        if dataset_name in added_names:
            return

        df = data.get(dataset_name)

        if df is None or df.empty:
            return

        work = df.copy()

        if apply_entities:
            work = filter_entity_rows(
                work,
                teams=teams,
                players=players,
                years=years,
            )

        if work is None or work.empty:
            return

        work = sort_for_context(work)

        packets.append(
            f"\n### {label}\n"
            + dataframe_to_context(
                work,
                max_rows=max_rows,
            )
        )
        added_names.add(dataset_name)

    # -----------------------------------------------------------------
    # Entity-specific context
    # -----------------------------------------------------------------

    if teams:
        add(
            "ALL-TIME FRANCHISE RECORDS",
            "all_time_records",
            25,
        )
        add(
            "SEASON RECORDS",
            "season_records",
            50,
        )

        for team in teams:
            leaders = player_leaders_for_team(team)

            if not leaders.empty:
                packets.append(
                    f"\n### STARTING-LINEUP PLAYER SCORING LEADERS — {team}\n"
                    + dataframe_to_context(
                        leaders,
                        max_rows=20,
                    )
                )

            # Always make season-level player production available for a
            # named franchise. This is what allows a follow-up such as
            # "who were his best players that year?" to be answered from
            # the actual weekly roster history.
            season_players = team_season_player_summary(
                team,
                years=years or None,
                top_n_per_season=10,
            )

            if not season_players.empty:
                label_year = (
                    ", ".join(str(year) for year in years)
                    if years
                    else "ALL AVAILABLE SEASONS"
                )

                packets.append(
                    f"\n### TEAM-SEASON PLAYER PRODUCTION — {team} — {label_year}\n"
                    + dataframe_to_context(
                        season_players,
                        max_rows=100,
                        max_cols=12,
                    )
                )

    if players:
        add(
            "PLAYER DRAFT HISTORY",
            "all_drafts",
            50,
        )
        add(
            "PLAYER KEEPER HISTORY",
            "keeper_history",
            30,
        )
        add(
            "PLAYER WAIVER ACQUISITIONS",
            "waiver_value_acquisitions",
            40,
        )
        add(
            "PLAYER CHAMPIONSHIP PEDIGREE",
            "player_championship_pedigree",
            30,
        )
        add(
            "PLAYER POSITIONAL EDGE CONTRIBUTIONS",
            "positional_edge_player_contributions",
            40,
        )
        add(
            "PLAYER WEEKLY LINEUP HISTORY",
            "weekly_lineups",
            60,
        )

    # -----------------------------------------------------------------
    # Intent routing
    # -----------------------------------------------------------------

    luck_terms = [
        "luck",
        "lucky",
        "unlucky",
        "cursed",
        "expected win",
        "expected wins",
        "all-play",
        "all play",
        "schedule strength",
        "sos",
    ]

    schedule_terms = [
        "schedule swap",
        "different schedule",
        "another schedule",
        "schedule luck",
        "schedule screwed",
        "schedule helped",
    ]

    bad_beat_terms = [
        "bad beat",
        "painful loss",
        "toughest loss",
        "worst loss",
        "unlucky loss",
        "top-3 loss",
        "top 3 loss",
        "lucky win",
    ]

    championship_terms = [
        "champion",
        "championship",
        "title",
        "trophy",
        "runner-up",
        "runner up",
        "finals",
    ]

    playoff_terms = [
        "playoff",
        "postseason",
        "semifinal",
        "quarterfinal",
        "finals",
    ]

    h2h_terms = [
        "head to head",
        "head-to-head",
        "against",
        "record vs",
        "versus",
        " vs ",
        "rivalry",
        "owns",
    ]

    scoring_terms = [
        "highest score",
        "lowest score",
        "blowout",
        "closest",
        "margin",
        "game ever",
        "matchup ever",
        "scoring record",
        "weekly score",
    ]

    lineup_terms = [
        "lineup",
        "bench",
        "efficiency",
        "should have started",
        "should've started",
        "points left",
        "optimal lineup",
        "lineup execution",
    ]

    draft_terms = [
        "draft",
        "pick",
        "round",
        "drafted",
        "drafter",
        "bust",
        "steal",
        "reach",
    ]

    waiver_terms = [
        "waiver",
        "free agent",
        "free-agent",
        "pickup",
        "pick up",
        "acquisition",
        "faab",
    ]

    manager_terms = [
        "manager",
        "management",
        "best managed",
        "best manager",
        "worst manager",
        "coaching",
        "skill",
    ]

    position_terms = [
        "positional",
        "position edge",
        "positional edge",
        "qb manager",
        "rb manager",
        "wr manager",
        "te manager",
        "best at qb",
        "best at rb",
        "best at wr",
        "best at te",
        "quarterback",
        "running back",
        "wide receiver",
        "tight end",
    ]

    stack_terms = [
        "stack",
        "stacking",
        "qb/wr",
        "qb wr",
    ]

    keeper_terms = [
        "keeper",
        "kept",
        "keeper value",
        "keeper history",
    ]

    player_terms = [
        "leading scorer",
        "scorer",
        "player points",
        "best player",
        "most points",
        "player history",
        "league history of",
    ]

    season_story_terms = [
        "tell me the story",
        "story of",
        "season recap",
        "recap",
        "what happened",
        "describe the season",
        "how did",
        "why was",
        "why were",
    ]

    champion_dna_terms = [
        "championship dna",
        "what do champions",
        "champions have in common",
        "winning formula",
        "title formula",
        "championship profile",
    ]

    comparison_terms = [
        "compare",
        "better",
        "best",
        "worst",
        "rank",
        "ranking",
        "versus",
        " vs ",
    ]

    if contains_any(q, luck_terms):
        add("SEASON LUCK METRICS", "luck_season", 70)
        add("ALL-TIME LUCK METRICS", "luck_all_time", 40)
        add("WEEKLY LUCK METRICS", "luck_team_week", 60)

    if contains_any(q, schedule_terms):
        add("SCHEDULE SWAP — FRANCHISE", "schedule_swap_franchise", 40)
        add("SCHEDULE SWAP — SEASON", "schedule_swap_season", 70)
        add("SCHEDULE SWAP — EXTREMES", "schedule_swap_extremes", 50)
        if len(teams) >= 1:
            add("SCHEDULE SWAP MATRIX", "schedule_swap_matrix_long", 80)

    if contains_any(q, bad_beat_terms):
        add("BAD BEAT — FRANCHISE", "bad_beat_franchise", 40)
        add("BAD BEAT — SEASON", "bad_beat_season", 60)
        add("BAD BEAT HISTORY", "bad_beat_history", 60)
        add("LUCKY WIN HISTORY", "lucky_win_history", 40)

    if contains_any(q, championship_terms):
        add("CHAMPIONSHIPS", "championships", 40)
        add("PLAYOFF RECORDS", "playoff_records", 40)
        add(
            "PLAYER CHAMPIONSHIP PEDIGREE",
            "player_championship_pedigree",
            40,
        )

    if contains_any(q, playoff_terms):
        add("PLAYOFF RECORDS", "playoff_records", 40)
        add("PLAYOFF APPEARANCES", "playoff_appearances", 50)
        add("CHAMPIONSHIPS", "championships", 40)

    if contains_any(q, h2h_terms):
        add("HEAD-TO-HEAD", "head_to_head", 60)
        add("TEAM GAME HISTORY", "team_games", 80)

    if contains_any(q, scoring_terms):
        add("HIGHEST SCORES", "highest_scores", 40)
        add("LOWEST SCORES", "lowest_scores", 40)
        add("BIGGEST BLOWOUTS", "biggest_blowouts", 40)
        add("CLOSEST GAMES", "closest_games", 40)
        add("TEAM GAME HISTORY", "team_games", 60)

    if contains_any(q, lineup_terms):
        add(
            "SEASON LINEUP EFFICIENCY",
            "lineup_efficiency_season",
            60,
        )
        add(
            "ALL-TIME LINEUP EFFICIENCY",
            "lineup_efficiency_all_time",
            40,
        )
        add(
            "WEEKLY LINEUP EFFICIENCY",
            "lineup_efficiency_team_week",
            70,
        )

    if contains_any(q, draft_terms):
        add("DRAFT POSITION STRATEGY", "draft_position_strategy", 60)
        add("DRAFT HISTORY", "all_drafts", 70)
        add("DRAFT VALUE — FRANCHISE", "draft_value_franchise", 40)
        add("DRAFT VALUE — TEAM SEASON", "draft_value_team_season", 70)
        add("DRAFT VALUE — PICKS", "draft_value_picks", 80)
        add(
            "DRAFT VALUE — LATE ROUND STEALS",
            "draft_value_late_round_steals",
            40,
        )
        add(
            "DRAFT VALUE — FIRST ROUND",
            "draft_value_first_round",
            40,
        )

    if contains_any(q, waiver_terms):
        add("WAIVER VALUE — FRANCHISE", "waiver_value_franchise", 40)
        add("WAIVER VALUE — TEAM SEASON", "waiver_value_team_season", 70)
        add(
            "WAIVER VALUE — ACQUISITIONS",
            "waiver_value_acquisitions",
            80,
        )
        add(
            "WAIVER VALUE — HALL OF FAME",
            "waiver_value_hall_of_fame",
            50,
        )

    if contains_any(q, manager_terms):
        add(
            "MANAGEMENT INDEX — FRANCHISE",
            "management_index_franchise",
            40,
        )
        add(
            "MANAGEMENT INDEX — TEAM SEASON",
            "management_index_team_season",
            70,
        )
        add(
            "MANAGEMENT INDEX — EXTREMES",
            "management_index_extremes",
            50,
        )
        add(
            "MANAGEMENT INDEX — PROFILES",
            "management_index_profiles",
            40,
        )
        add("ALL-TIME FRANCHISE RECORDS", "all_time_records", 30)
        add("CHAMPIONSHIPS", "championships", 30)

    if contains_any(q, position_terms):
        add(
            "POSITIONAL EDGE — FRANCHISE",
            "positional_edge_franchise",
            50,
        )
        add(
            "POSITIONAL EDGE — SEASON",
            "positional_edge_season",
            70,
        )
        add(
            "POSITIONAL EDGE — EXTREMES",
            "positional_edge_extremes",
            60,
        )
        add(
            "POSITIONAL EDGE — PLAYER CONTRIBUTIONS",
            "positional_edge_player_contributions",
            70,
        )

    if contains_any(q, stack_terms):
        add("QB/WR STACK — SUMMARY", "stack_summary", 20)
        add("QB/WR STACK — TEAM SEASON", "stack_team_season", 60)
        add("QB/WR STACK — FRANCHISE", "stack_by_franchise", 40)
        add("QB/WR STACK — PAIRS", "stack_pairs", 50)

    if contains_any(q, keeper_terms):
        add("KEEPER HISTORY", "keeper_history", 70)
        add("DRAFT HISTORY", "all_drafts", 60)
        add(
            "WAIVER VALUE — ACQUISITIONS",
            "waiver_value_acquisitions",
            50,
        )

    if contains_any(q, champion_dna_terms):
        add(
            "CHAMPIONSHIP DNA — TRAITS",
            "championship_dna_traits",
            40,
        )
        add(
            "CHAMPIONSHIP DNA — COMPARISON",
            "championship_dna_comparison",
            40,
        )
        add(
            "CHAMPIONSHIP DNA — CHAMPIONS",
            "championship_dna_champions",
            40,
        )
        add(
            "CHAMPIONSHIP DNA — TEAM SEASONS",
            "championship_dna_team_season",
            70,
        )

    if contains_any(q, player_terms) and not players:
        leaders = league_player_leaders()

        if not leaders.empty:
            packets.append(
                "\n### LEAGUE-WIDE COUNTED STARTER POINTS BY PLAYER\n"
                + dataframe_to_context(
                    leaders,
                    30,
                )
            )

    # -----------------------------------------------------------------
    # Cross-dataset questions
    # -----------------------------------------------------------------

    broad_team_question = bool(teams) and (
        contains_any(q, season_story_terms)
        or contains_any(q, comparison_terms)
        or contains_any(
            q,
            [
                "good",
                "bad",
                "successful",
                "profile",
                "describe",
                "strength",
                "weakness",
                "identity",
                "style",
            ],
        )
    )

    season_story = bool(years) and contains_any(q, season_story_terms)

    if broad_team_question or season_story:
        add("SEASON RECORDS", "season_records", 60)
        add("CHAMPIONSHIPS", "championships", 30)
        add("PLAYOFF APPEARANCES", "playoff_appearances", 40)
        add("SEASON LUCK METRICS", "luck_season", 60)
        add(
            "SEASON LINEUP EFFICIENCY",
            "lineup_efficiency_season",
            60,
        )
        add(
            "DRAFT VALUE — TEAM SEASON",
            "draft_value_team_season",
            60,
        )
        add(
            "WAIVER VALUE — TEAM SEASON",
            "waiver_value_team_season",
            60,
        )
        add(
            "MANAGEMENT INDEX — TEAM SEASON",
            "management_index_team_season",
            60,
        )
        add(
            "POSITIONAL EDGE — SEASON",
            "positional_edge_season",
            60,
        )
        add("BAD BEAT — SEASON", "bad_beat_season", 50)
        add(
            "SCHEDULE SWAP — SEASON",
            "schedule_swap_season",
            50,
        )

    # "Who is the best manager?" should explicitly separate management
    # quality from outcomes and luck.
    if contains_any(
        q,
        [
            "best manager",
            "greatest manager",
            "worst manager",
            "best franchise",
            "greatest franchise",
        ],
    ):
        add(
            "MANAGEMENT INDEX — FRANCHISE",
            "management_index_franchise",
            40,
        )
        add("ALL-TIME FRANCHISE RECORDS", "all_time_records", 40)
        add("CHAMPIONSHIPS", "championships", 40)
        add("DRAFT VALUE — FRANCHISE", "draft_value_franchise", 40)
        add("WAIVER VALUE — FRANCHISE", "waiver_value_franchise", 40)
        add(
            "ALL-TIME LINEUP EFFICIENCY",
            "lineup_efficiency_all_time",
            40,
        )
        add("ALL-TIME LUCK METRICS", "luck_all_time", 40)

    # Generic fallback.
    if not packets:
        add(
            "ALL-TIME FRANCHISE RECORDS",
            "all_time_records",
            30,
            apply_entities=False,
        )
        add(
            "CHAMPIONSHIPS",
            "championships",
            30,
            apply_entities=False,
        )
        add(
            "MANAGEMENT INDEX — FRANCHISE",
            "management_index_franchise",
            30,
            apply_entities=False,
        )
        add(
            "ALL-TIME LUCK METRICS",
            "luck_all_time",
            30,
            apply_entities=False,
        )
        add(
            "ALL-TIME LINEUP EFFICIENCY",
            "lineup_efficiency_all_time",
            30,
            apply_entities=False,
        )

    return (
        "\n".join(packets),
        teams,
        players,
        years,
        year_candidates,
    )


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
    prior_messages = prior_conversation_messages(question)

    (
        evidence,
        teams,
        players,
        years,
        year_candidates,
    ) = build_evidence(
        question,
        prior_messages=prior_messages,
    )

    client = get_client()

    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured in Streamlit Secrets."
        )

    model = st.secrets.get(
        "GEMINI_MODEL",
        "gemini-2.5-flash-lite",
    )

    # Give follow-up questions limited conversational continuity without
    # allowing prior chat text to override the current evidence packet.
    conversation_context = "\n".join(
        f"{message.get('role', '').upper()}: {message.get('content', '')}"
        for message in prior_messages
        if message.get("content")
    )

    prompt = f"""
You are THE LEAGUE HISTORIAN for a private fantasy football league.

PERSONALITY:
- Knowledgeable, concise, confident, and entertaining.
- Light sarcasm is welcome when the numbers justify it.
- Do not force jokes into every answer.
- Never insult a real person outside the context of fantasy-football performance.

CORE JOB:
- Treat the supplied league datasets as one connected historical knowledge base.
- When the question spans multiple concepts, combine the relevant evidence rather
  than answering from only one statistic.
- Explain what a metric means before drawing conclusions from it when necessary.
- Separate MANAGEMENT QUALITY, RESULTS, ROSTER PRODUCTION, and LUCK instead of
  treating them as interchangeable.

GROUNDING RULES:
1. Answer ONLY from the LEAGUE DATA supplied below.
2. Never invent a score, record, player, season, championship, ranking, transaction,
   keeper, draft result, or statistic.
3. If the supplied data is insufficient to answer the question, say so directly.
4. When calculations are simple and directly supported by supplied rows, you may
   calculate them.
5. Distinguish actual wins from expected wins and schedule luck.
6. Management Index is:
   50% Lineup Execution + 25% Draft Value + 25% Waiver Value.
   It intentionally excludes wins, championships, scoring, schedule luck, and
   Bad Beats. Do not call a luck metric manager skill.
7. Draft Value and Waiver Value are historical OUTCOME metrics, not perfect
   measurements of decision quality at the moment a decision was made.
8. Positional Edge measures starter production versus the same-week league
   baseline at QB/RB/WR/TE. Do not convert raw total positional edge into an
   overall manager ranking unless the supplied evidence explicitly does so.
9. Player Edge Contribution allocates a team-position's positional edge among
   its starters. It is descriptive contribution, not causal responsibility.
10. "Player career points" means fantasy points that actually counted in a
    franchise's STARTING lineup unless the evidence says otherwise.
11. Championship-player pedigree uses the champion's final regular-season roster
    as a proxy, not verified playoff-week rosters.
12. 2018 transaction history is unavailable. Do not fabricate 2018 waiver
    conclusions or an overall 2018 Management Index.
13. Historical franchise aliases have already been normalized in the evidence.
14. 2026 is the current/future draft season. Do not mix the posted 2026 draft
    order or keeper board into completed historical draft-performance results.
15. Use exact numbers when useful, usually rounded to 1-2 decimal places.
16. When asked "best" or "worst" and multiple definitions are reasonable, state
    the answer by category (for example management, results, drafting, luck)
    instead of pretending one metric settles every definition.
17. When asked for a season story or manager/franchise profile, synthesize the
    evidence into a short narrative: results, management, draft/waiver, lineup,
    positional strengths, and luck where those rows are supplied.
18. Resolve normal conversational follow-ups using RECENT CONVERSATION. For
    example, "his roster", "that season", "what about his draft?", and "who
    carried them?" should inherit the franchise/player from the preceding turn
    when it is clear.
19. TEAM-SEASON PLAYER PRODUCTION is season-specific weekly roster evidence:
    - starter_points = points that actually counted in that fantasy team's lineup.
    - starts = weeks that player was started.
    - rostered_points = fantasy production during weeks the player appeared
      anywhere on that fantasy roster, including bench weeks.
    - rostered_weeks = weeks the player appeared on the roster.
    Use starter_points/starts first when answering "best players" or "who carried
    the team," and mention rostered production only when helpful.
20. Do NOT say season-specific roster data is unavailable when TEAM-SEASON PLAYER
    PRODUCTION is supplied.
21. If "that year" or "that season" could genuinely refer to multiple seasons from
    the immediately preceding answer, do not invent a choice. Either:
    - infer the intended season only when the conversation clearly establishes
      one primary answer, or
    - ask one short clarification naming the competing seasons.
22. Do not mention Gemini, prompts, CSV files, pandas, evidence routing, or other
    implementation details.

USER QUESTION:
{question}

MENTIONED TEAMS:
{teams}

MENTIONED PLAYERS:
{players}

MENTIONED YEARS:
{years}

POSSIBLE PRIOR-YEAR REFERENCES:
{year_candidates}

RECENT CONVERSATION:
{conversation_context or "None"}

LEAGUE DATA:
{evidence}

Answer the user's question directly. If there is a clear winner, loser, ranking,
or conclusion, lead with it. When evidence gives competing interpretations,
explain the distinction rather than hiding it.
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.20,
            max_output_tokens=950,
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
The Historian can now combine multiple parts of league history. Try:

- **Who is the best manager in league history, and why?**
- **Describe Uncle Rico's management profile.**
- **Tell me about Uncle Rico's best season — then ask who his best players were.**
- **Tell me the story of the 2022 season.**
- **Was Voldemort actually good, lucky, or both?**
- **Who is the best drafting franchise?**
- **What was the best waiver pickup in league history?**
- **Which franchise has historically been strongest at RB?**
- **Tell me Christian McCaffrey's history in this league.**
- **What is Joe Mantegna's record against Post Mahomes?**
- **Who has suffered the worst bad beats?**
- **Whose record was helped most by the schedule?**
- **What do championship teams in this league have in common?**
- **Which QB/WR stacks worked best?**
        """
    )


suggestions = [
    "Who is the best manager in league history?",
    "Tell me the story of the 2022 season.",
    "Who is the best drafting franchise?",
    "What do champions have in common?",
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