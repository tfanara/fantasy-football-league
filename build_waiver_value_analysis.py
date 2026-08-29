from pathlib import Path
import re
import unicodedata

import nflreadpy as nfl
import pandas as pd
import numpy as np


# ============================================================
# CONFIG
# ============================================================

TX_FILE = Path("data/transactions/all_transactions.csv")

LINEUP_FILE = Path(
    "data/matchups/player_week_stats/"
    "all_weekly_lineups_2017_2025.csv"
)

PLAYER_TEAM_FILE = Path(
    "data/nfl/player_week_teams.csv"
)

OUT_DIR = Path("data/analysis")
OUT_DIR.mkdir(parents=True, exist_ok=True)

STINT_FILE = OUT_DIR / "waiver_stints.csv"
STINT_WEEK_FILE = OUT_DIR / "waiver_stint_weeks.csv"
AUDIT_FILE = OUT_DIR / "waiver_stint_audit.csv"

YEARS = [
    2017,
    2019,
    2020,
    2021,
    2022,
    2023,
    2024,
    2025,
]

REGULAR_SEASON_END = {
    2017: 13,
    2019: 13,
    2020: 13,
    2021: 14,
    2022: 14,
    2023: 14,
    2024: 14,
    2025: 14,
}

TEAM_ALIASES = {
    "PickUpYourBratsMalle": "ThreatLevelMidnight",
    "Little Red Fournette": "Post Mahomes",
    "Ur The Best Bellows": "Joe Mantegna",
    "You Better Park It": "Buttermilk Puuump",
    "Buttermilk Pump": "Buttermilk Puuump",
}

SKILL_POSITIONS = {"QB", "RB", "WR", "TE"}


# ============================================================
# HELPERS
# ============================================================

def canonical_team(value):
    if pd.isna(value):
        return ""

    value = str(value).strip()
    return TEAM_ALIASES.get(value, value)


def norm_name(value):
    if pd.isna(value):
        return ""

    value = unicodedata.normalize(
        "NFKD",
        str(value),
    )

    value = "".join(
        c for c in value
        if not unicodedata.combining(c)
    )

    value = value.lower().replace("’", "'")

    value = re.sub(
        r"\b(jr|sr|ii|iii|iv)\b\.?",
        "",
        value,
    )

    value = re.sub(
        r"[^a-z0-9]+",
        "",
        value,
    )

    return value


def parse_transaction_datetime(row):
    """
    Yahoo displays transaction month/day/time while season year
    is stored separately in our transaction file.

    January/February following a fantasy season belong to the
    next calendar year.
    """

    raw = str(row["date"]).strip()
    season = int(row["year"])

    dt = pd.to_datetime(
        f"{raw} {season}",
        format="mixed",
        errors="coerce",
    )

    if (
        pd.notna(dt)
        and dt.month <= 2
    ):
        dt = dt.replace(
            year=season + 1
        )

    return dt


# ============================================================
# LOAD
# ============================================================

print("=" * 90)
print("WAIVER VALUE — TRANSACTION-AUTHORITATIVE BUILDER")
print("=" * 90)

tx = pd.read_csv(TX_FILE)
lu = pd.read_csv(LINEUP_FILE)
pt = pd.read_csv(PLAYER_TEAM_FILE)

tx = tx[
    tx["year"].isin(YEARS)
].copy()

lu = lu[
    lu["year"].isin(YEARS)
].copy()

pt = pt[
    pt["year"].isin(YEARS)
].copy()


# ============================================================
# NORMALIZE TRANSACTIONS
# ============================================================

tx["canonical_team"] = (
    tx["team"]
    .map(canonical_team)
)

tx["added_key"] = (
    tx["added_player"]
    .map(norm_name)
)

tx["dropped_key"] = (
    tx["dropped_player"]
    .map(norm_name)
)

tx["transaction_datetime"] = (
    tx.apply(
        parse_transaction_datetime,
        axis=1,
    )
)

if tx["transaction_datetime"].isna().any():
    bad = tx[
        tx["transaction_datetime"].isna()
    ]

    raise RuntimeError(
        "Unparsed transaction dates:\n"
        + bad.to_string(index=False)
    )

tx["source_order"] = range(len(tx))


# ============================================================
# NFL CALENDAR
# ============================================================

print("\nLoading NFL schedule...")

sched = nfl.load_schedules(
    seasons=list(range(2017, 2026))
)

if hasattr(sched, "to_pandas"):
    sched = sched.to_pandas()

sched = sched[
    sched["game_type"]
    .astype(str)
    .str.upper()
    .eq("REG")
].copy()

sched["gameday"] = pd.to_datetime(
    sched["gameday"],
    errors="coerce",
)

week_calendar = (
    sched
    .groupby(
        ["season", "week"],
        as_index=False,
    )
    .agg(
        first_game=("gameday", "min"),
        last_game=("gameday", "max"),
    )
    .rename(
        columns={"season": "year"}
    )
)

week_calendar = week_calendar[
    week_calendar.apply(
        lambda r: (
            int(r["year"])
            in REGULAR_SEASON_END
            and int(r["week"])
            <= REGULAR_SEASON_END[
                int(r["year"])
            ]
        ),
        axis=1,
    )
].copy()


def calendar_week(year, dt):
    """
    Map transaction date to the fantasy week it affects.

    Between weeks -> upcoming week.
    During game window -> current NFL week.

    Player-specific kickoff eligibility will be handled
    separately after ownership reconstruction.
    """

    if pd.isna(dt):
        return pd.NA

    cal = (
        week_calendar[
            week_calendar["year"].eq(year)
        ]
        .sort_values("week")
        .reset_index(drop=True)
    )

    if cal.empty:
        return pd.NA

    date = dt.normalize()

    first = cal.iloc[0]

    if date <= first["last_game"]:
        return int(first["week"])

    for i in range(len(cal)):

        row = cal.iloc[i]

        if (
            row["first_game"]
            <= date
            <= row["last_game"]
        ):
            return int(row["week"])

        if i + 1 < len(cal):
            nxt = cal.iloc[i + 1]

            if (
                row["last_game"]
                < date
                < nxt["first_game"]
            ):
                return int(nxt["week"])

    return pd.NA


# ============================================================
# BUILD PLAYER EVENTS
# ============================================================

events = []

for row in tx.itertuples(index=False):

    if row.added_key:

        events.append({
            "year": int(row.year),
            "team": row.canonical_team,
            "player": row.added_player,
            "name_key": row.added_key,
            "datetime":
                row.transaction_datetime,
            "event": "ADD",
            "acquisition_type":
                row.acquisition_type,
            "source_order":
                row.source_order,
        })

    if row.dropped_key:

        events.append({
            "year": int(row.year),
            "team": row.canonical_team,
            "player": row.dropped_player,
            "name_key": row.dropped_key,
            "datetime":
                row.transaction_datetime,
            "event": "DROP",
            "acquisition_type":
                row.acquisition_type,
            "source_order":
                row.source_order,
        })

events = pd.DataFrame(events)

events = events.sort_values(
    [
        "year",
        "team",
        "name_key",
        "datetime",
        "source_order",
    ]
).reset_index(drop=True)


# ============================================================
# RECONSTRUCT WAIVER / FREE-AGENT STINTS
# ============================================================

print("Reconstructing acquisition stints...")

stints = []
redundant_adds = []

stint_counter = 0

for (year, team, key), g in events.groupby(
    ["year", "team", "name_key"],
    sort=False,
):

    g = g.sort_values(
        ["datetime", "source_order"]
    )

    currently_owned = False
    current = None

    for row in g.itertuples(index=False):

        if row.event == "ADD":

            # Duplicate Yahoo ADD while already owned:
            # do NOT create another acquisition.
            if currently_owned:

                redundant_adds.append({
                    "year": year,
                    "team": team,
                    "player": row.player,
                    "datetime": row.datetime,
                    "acquisition_type":
                        row.acquisition_type,
                })

                continue

            currently_owned = True

            # Only Waiver / Free Agent acquisitions
            # qualify as Waiver Value stints.
            qualifying = (
                row.acquisition_type
                in {"Waiver", "Free Agent"}
            )

            if qualifying:

                stint_counter += 1

                current = {
                    "stint_id":
                        f"W{stint_counter:05d}",
                    "year": year,
                    "team": team,
                    "player": row.player,
                    "name_key": key,
                    "acquisition_type":
                        row.acquisition_type,
                    "acquisition_datetime":
                        row.datetime,
                    "drop_datetime": pd.NaT,
                }

            else:
                current = None

        elif row.event == "DROP":

            if currently_owned:

                if current is not None:
                    current["drop_datetime"] = (
                        row.datetime
                    )

                    stints.append(current)

                currently_owned = False
                current = None

            else:
                # Expected for drafted / initial-roster
                # players whose ADD predates transaction data.
                continue

    # Still owned at end of transaction history.
    if (
        currently_owned
        and current is not None
    ):
        stints.append(current)


stints = pd.DataFrame(stints)

if stints.empty:
    raise RuntimeError(
        "No waiver/free-agent stints created."
    )

print(
    "Qualifying acquisition stints:",
    f"{len(stints):,}"
)

print(
    "Redundant ADDs ignored:",
    f"{len(redundant_adds):,}"
)


# ============================================================
# ACQUISITION / DROP WEEK
# ============================================================

stints["acquisition_week"] = (
    stints.apply(
        lambda r: calendar_week(
            int(r["year"]),
            r["acquisition_datetime"],
        ),
        axis=1,
    )
)

stints["drop_week"] = (
    stints.apply(
        lambda r: (
            calendar_week(
                int(r["year"]),
                r["drop_datetime"],
            )
            if pd.notna(
                r["drop_datetime"]
            )
            else pd.NA
        ),
        axis=1,
    )
)


# ============================================================
# PLAYER POSITION
# ============================================================

pt["name_key"] = (
    pt["player"]
    .map(norm_name)
)

position_lookup = (
    pt[
        pt["player_position"]
        .isin(SKILL_POSITIONS)
    ]
    .groupby(
        ["year", "name_key"],
        as_index=False,
    )
    .agg(
        player_position=(
            "player_position",
            lambda s: (
                s.mode().iloc[0]
                if not s.mode().empty
                else pd.NA
            ),
        )
    )
)

stints = stints.merge(
    position_lookup,
    on=["year", "name_key"],
    how="left",
)

stints["primary_eligible"] = (
    stints["player_position"]
    .isin(SKILL_POSITIONS)
)


# ============================================================
# PLAYER-WEEK NFLVERSE PRODUCTION TABLE
# ============================================================
#
# OWNERSHIP AUTHORITY:
#   Yahoo transactions
#
# PRODUCTION AUTHORITY:
#   nflverse weekly player statistics
#
# Historical Yahoo scoring reconstruction:
#
#   nflverse fantasy_points
#   + 2 points per passing TD
#   + 1 point per passing interception
#   + 0.5 points per reception for 2020+
#
# Therefore:
#
#   2017-2019:
#       non-PPR
#       6-point passing TD
#       -1 passing interception
#
#   2020-2025:
#       half-PPR
#       6-point passing TD
#       -1 passing interception
#
# Validation against the historical Yahoo data:
#   8,423 matched QB/RB/WR/TE player-weeks
#   99.70% exact within 0.01 points
# ============================================================

print(
    "Loading nflverse weekly player production..."
)

nfl_stats = nfl.load_player_stats(
    seasons=list(YEARS),
    summary_level="week",
)

if hasattr(nfl_stats, "to_pandas"):
    nfl_stats = nfl_stats.to_pandas()

nfl_stats = nfl_stats.copy()


# ------------------------------------------------------------
# REGULAR SEASON ONLY
# ------------------------------------------------------------

if "season_type" in nfl_stats.columns:

    nfl_stats = nfl_stats[
        nfl_stats["season_type"].eq("REG")
    ].copy()


# ------------------------------------------------------------
# NORMALIZE
# ------------------------------------------------------------

nfl_stats["season"] = pd.to_numeric(
    nfl_stats["season"],
    errors="coerce",
)

nfl_stats["week"] = pd.to_numeric(
    nfl_stats["week"],
    errors="coerce",
)

nfl_stats = nfl_stats[
    nfl_stats["season"].isin(YEARS)
    &
    nfl_stats["week"].notna()
].copy()

nfl_stats["name_key"] = (
    nfl_stats["player_display_name"]
    .map(norm_name)
)

for col in [
    "fantasy_points",
    "passing_tds",
    "passing_interceptions",
    "receptions",
]:

    nfl_stats[col] = pd.to_numeric(
        nfl_stats[col],
        errors="coerce",
    ).fillna(0.0)


# ------------------------------------------------------------
# RECONSTRUCT YAHOO SCORING
# ------------------------------------------------------------

nfl_stats["yahoo_points"] = (
    nfl_stats["fantasy_points"]
    + (
        2.0
        * nfl_stats["passing_tds"]
    )
    + (
        1.0
        * nfl_stats[
            "passing_interceptions"
        ]
    )
)

half_ppr = (
    nfl_stats["season"] >= 2020
)

nfl_stats.loc[
    half_ppr,
    "yahoo_points",
] = (
    nfl_stats.loc[
        half_ppr,
        "yahoo_points",
    ]
    + (
        0.5
        * nfl_stats.loc[
            half_ppr,
            "receptions",
        ]
    )
)


# ------------------------------------------------------------
# AUDIT DUPLICATE NORMALIZED PLAYER-WEEKS
# ------------------------------------------------------------

duplicate_mask = (
    nfl_stats.duplicated(
        [
            "season",
            "week",
            "name_key",
            "position",
        ],
        keep=False,
    )
)

duplicate_player_weeks = (
    nfl_stats.loc[
        duplicate_mask,
        [
            "season",
            "week",
            "name_key",
            "position",
        ],
    ]
    .drop_duplicates()
)

print(
    "Duplicate normalized nflverse player-weeks:",
    f"{len(duplicate_player_weeks):,}",
)


# ------------------------------------------------------------
# PRODUCTION LOOKUP
# ------------------------------------------------------------

production = (
    nfl_stats[
        [
            "season",
            "week",
            "name_key",
            "player_display_name",
            "position",
            "team",
            "yahoo_points",
        ]
    ]
    .rename(
        columns={
            "season":
                "year",
            "player_display_name":
                "player",
            "position":
                "nfl_position",
            "team":
                "production_nfl_team",
        }
    )
    .sort_values(
        [
            "year",
            "week",
            "name_key",
        ]
    )
    .drop_duplicates(
        [
            "year",
            "week",
            "name_key",
            "nfl_position",
        ],
        keep="first",
    )
    .copy()
)

# Primary lookup is position-aware. This prevents different
# NFL players with the same normalized name from colliding
# when their positions differ (for example, the two
# Chris Thompsons in 2017).

production_lookup = {

    (
        int(r.year),
        int(r.week),
        r.name_key,
        str(r.nfl_position),
    ):
    float(r.yahoo_points)

    for r in production.itertuples(
        index=False
    )
}

production_row_lookup = set(
    production_lookup
)

print(
    "nflverse production player-weeks:",
    f"{len(production):,}",
)


# ============================================================
# NFL TEAM / GAME DATE LOOKUP
# ============================================================

player_week_team = (
    pt[
        [
            "year",
            "week",
            "name_key",
            "nfl_team",
        ]
    ]
    .dropna(
        subset=["name_key"]
    )
    .drop_duplicates(
        ["year", "week", "name_key"]
    )
)

team_lookup = {
    (
        int(r.year),
        int(r.week),
        r.name_key,
    ): r.nfl_team
    for r in player_week_team.itertuples(
        index=False
    )
}


# Each NFL team plays at most once in a normal NFL week.
team_games = []

for row in sched.itertuples(index=False):

    for team in [
        row.home_team,
        row.away_team,
    ]:

        team_games.append({
            "year": int(row.season),
            "week": int(row.week),
            "nfl_team": team,
            "gameday": row.gameday,
            "gametime": row.gametime,
        })

team_games = pd.DataFrame(team_games)


# ------------------------------------------------------------
# SEASON-LEVEL NFL TEAM FALLBACK
# ------------------------------------------------------------
#
# player_week_teams may stop emitting rows when a player is
# injured/inactive. Transactions still establish fantasy
# ownership, so an absent exact-week NFL-team row does not mean
# the player became teamless.
#
# We use a season-level fallback ONLY when all observed rows for
# that player-season point to exactly one NFL team. Players who
# appeared for multiple NFL teams remain unresolved when their
# exact-week team is missing.

season_team_sets = (
    player_week_team
    .dropna(
        subset=["nfl_team"]
    )
    .groupby(
        [
            "year",
            "name_key",
        ]
    )["nfl_team"]
    .agg(
        lambda s:
            tuple(
                sorted(
                    set(
                        str(x)
                        for x in s
                        if pd.notna(x)
                    )
                )
            )
    )
)

season_team_lookup = {

    (
        int(year),
        name_key,
    ):
    teams[0]

    for (
        year,
        name_key,
    ), teams in season_team_sets.items()

    if len(teams) == 1
}

season_team_ambiguous = {

    (
        int(year),
        name_key,
    )

    for (
        year,
        name_key,
    ), teams in season_team_sets.items()

    if len(teams) > 1
}

print(
    "Single-team player-seasons available for fallback:",
    f"{len(season_team_lookup):,}",
)

print(
    "Multi-team player-seasons protected from fallback:",
    f"{len(season_team_ambiguous):,}",
)


game_lookup = {
    (
        int(r.year),
        int(r.week),
        r.nfl_team,
    ): r.gameday
    for r in team_games.itertuples(
        index=False
    )
}


# ============================================================
# PLAYER-SPECIFIC ACQUISITION-WEEK ELIGIBILITY
# ============================================================

def first_week_eligible(
    year,
    acquisition_dt,
    acquisition_week,
    name_key,
):
    """
    If player is added after his NFL game has already occurred
    that week, his first eligible fantasy-production week is
    the following week.

    We only have date-level kickoff here, not timezone-aware
    exact kickoff timestamps. Same-date acquisitions remain
    assigned to that week for now and are flagged separately.
    """

    if pd.isna(acquisition_week):
        return pd.NA, "OUTSIDE_REGULAR_SEASON"

    week = int(acquisition_week)

    team = team_lookup.get(
        (year, week, name_key)
    )

    if pd.isna(team) or not team:
        return week, "NO_NFL_TEAM_MATCH"

    game_date = game_lookup.get(
        (year, week, team)
    )

    if pd.isna(game_date):
        # Bye week: next week is first scoring opportunity.
        next_week = week + 1

        if (
            next_week
            <= REGULAR_SEASON_END[year]
        ):
            return next_week, "BYE_ACQUISITION_WEEK"

        return pd.NA, "BYE_AFTER_REGULAR_SEASON"

    acq_date = acquisition_dt.normalize()

    if acq_date > game_date:
        next_week = week + 1

        if (
            next_week
            <= REGULAR_SEASON_END[year]
        ):
            return (
                next_week,
                "ADDED_AFTER_GAME_DATE",
            )

        return (
            pd.NA,
            "ADDED_AFTER_FINAL_GAME_DATE",
        )

    if acq_date == game_date:
        return week, "SAME_DAY_AS_GAME"

    return week, "BEFORE_GAME_DATE"


eligibility = stints.apply(
    lambda r: first_week_eligible(
        int(r["year"]),
        r["acquisition_datetime"],
        r["acquisition_week"],
        r["name_key"],
    ),
    axis=1,
)

stints["first_eligible_week"] = [
    x[0] for x in eligibility
]

stints["eligibility_reason"] = [
    x[1] for x in eligibility
]


# ============================================================
# BUILD STINT-WEEK TABLE
# ============================================================

print("Attaching player-week production...")

week_records = []

for row in stints.itertuples(index=False):

    if pd.isna(
        row.first_eligible_week
    ):
        continue

    start_week = int(
        row.first_eligible_week
    )

    max_week = REGULAR_SEASON_END[
        int(row.year)
    ]

    # If dropped during a week, keep that week in the
    # candidate interval for now. Exact drop/game ordering
    # will be audited separately.
    if pd.notna(row.drop_week):

        end_week = min(
            max_week,
            int(row.drop_week),
        )

    else:
        end_week = max_week

    if start_week > end_week:
        continue

    for week in range(
        start_week,
        end_week + 1,
    ):

        production_key = (
            int(row.year),
            week,
            row.name_key,
            str(row.player_position),
        )

        points = production_lookup.get(
            production_key,
            pd.NA,
        )

        stats_row_observed = (
            production_key
            in production_row_lookup
        )

        exact_week_nfl_team = team_lookup.get(
            (
                int(row.year),
                week,
                row.name_key,
            ),
            pd.NA,
        )

        if pd.notna(
            exact_week_nfl_team
        ):

            nfl_team = (
                exact_week_nfl_team
            )

            nfl_team_source = (
                "EXACT_WEEK"
            )

        else:

            fallback_team = (
                season_team_lookup.get(
                    (
                        int(row.year),
                        row.name_key,
                    ),
                    pd.NA,
                )
            )

            if pd.notna(
                fallback_team
            ):

                nfl_team = (
                    fallback_team
                )

                nfl_team_source = (
                    "SEASON_SINGLE_TEAM"
                )

            else:

                nfl_team = pd.NA

                if (
                    int(row.year),
                    row.name_key,
                ) in season_team_ambiguous:

                    nfl_team_source = (
                        "MULTI_TEAM_AMBIGUOUS"
                    )

                else:

                    nfl_team_source = (
                        "NO_TEAM_MATCH"
                    )

        game_date = (
            game_lookup.get(
                (
                    int(row.year),
                    week,
                    nfl_team,
                )
            )
            if pd.notna(nfl_team)
            else pd.NaT
        )

        # nflverse has no row for many players who played
        # zero statistical snaps / produced no fantasy stats.
        #
        # If the player's NFL team is known and that team had
        # a game this week, a missing stat row is a legitimate
        # zero-point player-week.
        #
        # If NFL team/game context cannot be established, the
        # score remains unresolved rather than being silently
        # converted to zero.

        team_known = (
            pd.notna(nfl_team)
        )

        scheduled_game_known = (
            team_known
            and pd.notna(game_date)
        )

        # If the team is known but there is no scheduled game
        # in this regular-season week, this is a verified bye.
        #
        # Bye weeks are not fantasy-production opportunities
        # and therefore must not enter the Waiver Value
        # opportunity denominator.

        verified_bye = (
            team_known
            and not scheduled_game_known
        )

        production_resolved = (
            stats_row_observed
            or scheduled_game_known
        )

        if stats_row_observed:

            resolved_points = float(
                points
            )

            production_resolution = (
                "NFLVERSE_STAT_ROW"
            )

        elif scheduled_game_known:

            resolved_points = 0.0

            production_resolution = (
                "SCHEDULED_GAME_ZERO"
            )

        elif verified_bye:

            resolved_points = pd.NA

            production_resolution = (
                "BYE_WEEK"
            )

        else:

            resolved_points = pd.NA

            production_resolution = (
                "UNRESOLVED"
            )

        week_records.append({
            "stint_id": row.stint_id,
            "year": int(row.year),
            "week": week,
            "team": row.team,
            "player": row.player,
            "name_key": row.name_key,
            "player_position":
                row.player_position,
            "acquisition_type":
                row.acquisition_type,
            "acquisition_datetime":
                row.acquisition_datetime,
            "drop_datetime":
                row.drop_datetime,

            "drop_week":
                row.drop_week,
            "acquisition_week":
                row.acquisition_week,
            "first_eligible_week":
                row.first_eligible_week,
            "eligibility_reason":
                row.eligibility_reason,
            "nfl_team":
                nfl_team,

            "nfl_team_source":
                nfl_team_source,

            "game_date":
                game_date,
            "fantasy_points":
                resolved_points,

            # True only when nflverse contained an actual
            # statistical player-week row.
            "score_observed":
                stats_row_observed,

            # True when we can establish the player's fantasy
            # production, including a verified zero.
            "production_resolved":
                production_resolved,

            "verified_bye":
                verified_bye,

            "production_resolution":
                production_resolution,
        })


stint_weeks = pd.DataFrame(
    week_records
)


# ============================================================
# DROP-WEEK ELIGIBILITY
# ============================================================

def retained_for_drop_week(row):
    """
    Determine whether player was still owned on his NFL game
    date in the week he was dropped.

    Date-level only. Same-date situations are flagged for
    review rather than silently deciding exact time order.
    """

    if pd.isna(row["drop_datetime"]):
        return True, "NO_DROP"

    if pd.isna(row["game_date"]):
        return False, "NO_GAME_OR_BYE"

    drop_date = row[
        "drop_datetime"
    ].normalize()

    game_date = pd.Timestamp(
        row["game_date"]
    ).normalize()

    if drop_date < game_date:
        return False, "DROPPED_BEFORE_GAME_DATE"

    if drop_date > game_date:
        return True, "DROPPED_AFTER_GAME_DATE"

    return True, "DROP_SAME_DAY_AS_GAME"


if not stint_weeks.empty:

    drop_eval = stint_weeks.apply(
        retained_for_drop_week,
        axis=1,
    )

    stint_weeks["owned_for_week"] = [
        x[0] for x in drop_eval
    ]

    stint_weeks["drop_week_reason"] = [
        x[1] for x in drop_eval
    ]

    # Drop logic only matters in the actual drop week.
    #
    # Build the drop-week series separately and coerce missing
    # values to NaN so pandas never has to evaluate pd.NA as
    # a boolean during the comparison.
    drop_week_values = (
        stint_weeks["drop_datetime"]
        .apply(
            lambda x: (
                calendar_week(
                    x.year,
                    x,
                )
                if pd.notna(x)
                else pd.NA
            )
        )
    )

    drop_week_numeric = pd.to_numeric(
        drop_week_values,
        errors="coerce",
    )

    same_as_drop_week = (
        drop_week_numeric.notna()
        &
        stint_weeks["week"].eq(
            drop_week_numeric
        )
    )

    not_drop_week = ~same_as_drop_week

    stint_weeks.loc[
        not_drop_week,
        "owned_for_week",
    ] = True

    stint_weeks.loc[
        not_drop_week,
        "drop_week_reason",
    ] = "NOT_DROP_WEEK"


# ============================================================
# CREDIT RESOLVED PRODUCTION
# ============================================================
#
# fantasy_points now has three states:
#
#   NFLVERSE_STAT_ROW
#       reconstructed Yahoo fantasy score
#
#   SCHEDULED_GAME_ZERO
#       verified NFL game, no statistical row, 0 points
#
#   UNRESOLVED
#       insufficient NFL team/game context
#
# Unresolved production MUST remain NA.
# ============================================================

stint_weeks["credited_points"] = (
    pd.to_numeric(
        stint_weeks["fantasy_points"],
        errors="coerce",
    )
)

# If exact drop/game logic determines the player was no
# longer owned, the stint receives no credit for that week.

stint_weeks.loc[
    ~stint_weeks["owned_for_week"],
    "credited_points",
] = 0.0


# Resolution statistics should use weeks actually owned,
# rather than the broader candidate interval.

# A player may be transaction-owned during an NFL bye, but a
# bye is not a production opportunity. Keep both concepts:
#
#   transaction_owned_week
#       manager owned the player
#
#   opportunity_week
#       manager owned the player AND player's NFL team played
#
# Waiver Value uses opportunity_week.

stint_weeks["transaction_owned_week"] = (
    stint_weeks["owned_for_week"]
)

stint_weeks["owned_bye_week"] = (
    stint_weeks["owned_for_week"]
    &
    stint_weeks["verified_bye"]
)

stint_weeks["opportunity_week"] = (
    stint_weeks["owned_for_week"]
    &
    ~stint_weeks["verified_bye"]
)

stint_weeks["resolved_owned_week"] = (
    stint_weeks["opportunity_week"]
    &
    stint_weeks["production_resolved"]
)

stint_weeks["unresolved_owned_week"] = (
    stint_weeks["opportunity_week"]
    &
    ~stint_weeks["production_resolved"]
)


# ============================================================
# SUMMARIZE STINTS
# ============================================================

weekly_summary = (
    stint_weeks
    .groupby(
        "stint_id",
        as_index=False,
    )
    .agg(
        eligible_weeks=(
            "week",
            "nunique",
        ),

        transaction_owned_weeks=(
            "transaction_owned_week",
            "sum",
        ),

        bye_weeks=(
            "owned_bye_week",
            "sum",
        ),

        owned_weeks=(
            "opportunity_week",
            "sum",
        ),

        score_rows_observed=(
            "score_observed",
            "sum",
        ),

        resolved_owned_weeks=(
            "resolved_owned_week",
            "sum",
        ),

        unresolved_owned_weeks=(
            "unresolved_owned_week",
            "sum",
        ),

        production_points=(
            "credited_points",
            "sum",
        ),

        weeks_with_points=(
            "credited_points",
            lambda s:
                (s > 0).sum(),
        ),
    )
)

stints = stints.merge(
    weekly_summary,
    on="stint_id",
    how="left",
)

for col in [
    "eligible_weeks",
    "transaction_owned_weeks",
    "bye_weeks",
    "owned_weeks",
    "score_rows_observed",
    "resolved_owned_weeks",
    "unresolved_owned_weeks",
    "production_points",
    "weeks_with_points",
]:

    stints[col] = (
        stints[col]
        .fillna(0)
    )


stints["production_resolution_rate"] = (
    stints["resolved_owned_weeks"]
    /
    stints["owned_weeks"]
    .replace(0, pd.NA)
)


# ============================================================
# SAVE
# ============================================================

stints.to_csv(
    STINT_FILE,
    index=False,
)

stint_weeks.to_csv(
    STINT_WEEK_FILE,
    index=False,
)


audit_cols = [
    "stint_id",
    "year",
    "team",
    "player",
    "player_position",
    "acquisition_type",
    "acquisition_datetime",
    "drop_datetime",
    "acquisition_week",
    "first_eligible_week",
    "eligibility_reason",
    "eligible_weeks",
    "transaction_owned_weeks",
    "bye_weeks",
    "owned_weeks",
    "score_rows_observed",
    "resolved_owned_weeks",
    "unresolved_owned_weeks",
    "production_resolution_rate",
    "production_points",
    "weeks_with_points",
    "primary_eligible",
]

stints[
    audit_cols
].to_csv(
    AUDIT_FILE,
    index=False,
)


# ============================================================
# VALIDATION
# ============================================================

print("\n" + "=" * 90)
print("VALIDATION")
print("=" * 90)

print(
    "Stints:",
    f"{len(stints):,}",
)

print(
    "Unique stint IDs:",
    f"{stints['stint_id'].nunique():,}",
)

print(
    "Duplicate stint IDs:",
    stints["stint_id"]
    .duplicated()
    .sum(),
)

print(
    "Redundant ADDs ignored:",
    len(redundant_adds),
)

print(
    "Outside regular season:",
    stints["acquisition_week"]
    .isna()
    .sum(),
)

eligible = stints[
    stints["primary_eligible"]
].copy()

print(
    "Eligible QB/RB/WR/TE stints:",
    f"{len(eligible):,}",
)

print(
    "Eligible in regular season:",
    f"{eligible['first_eligible_week'].notna().sum():,}",
)


# ============================================================
# ELIGIBILITY REASONS
# ============================================================

print("\n" + "=" * 90)
print("ACQUISITION-WEEK ELIGIBILITY")
print("=" * 90)

print(
    eligible[
        "eligibility_reason"
    ]
    .value_counts(
        dropna=False
    )
    .to_string()
)


# ============================================================
# PRODUCTION RESOLUTION
# ============================================================

print("\n" + "=" * 90)
print("PLAYER-WEEK PRODUCTION RESOLUTION")
print("=" * 90)

inseason = eligible[
    eligible["first_eligible_week"]
    .notna()
].copy()

total_candidate_weeks = int(
    inseason[
        "eligible_weeks"
    ].sum()
)

total_owned_weeks = int(
    inseason[
        "owned_weeks"
    ].sum()
)

total_stat_rows = int(
    inseason[
        "score_rows_observed"
    ].sum()
)

total_resolved = int(
    inseason[
        "resolved_owned_weeks"
    ].sum()
)

total_unresolved = int(
    inseason[
        "unresolved_owned_weeks"
    ].sum()
)

resolution_rate = (
    total_resolved
    / total_owned_weeks
    if total_owned_weeks
    else float("nan")
)

print(
    "Candidate stint-weeks:",
    f"{total_candidate_weeks:,}",
)

print(
    "Production opportunity weeks:",
    f"{total_owned_weeks:,}",
)

total_bye_weeks = int(
    inseason[
        "bye_weeks"
    ].sum()
)

print(
    "Verified bye weeks excluded:",
    f"{total_bye_weeks:,}",
)

print(
    "nflverse stat rows:",
    f"{total_stat_rows:,}",
)

print(
    "Resolved owned weeks:",
    f"{total_resolved:,}",
)

print(
    "Unresolved owned weeks:",
    f"{total_unresolved:,}",
)

print(
    "Overall production resolution:",
    f"{resolution_rate:.1%}",
)


# Accounting identity:
#
# transaction-owned weeks must equal production opportunity
# weeks plus owned bye weeks.

total_transaction_owned = int(
    inseason[
        "transaction_owned_weeks"
    ].sum()
)

total_owned_byes = int(
    inseason[
        "bye_weeks"
    ].sum()
)

if (
    total_transaction_owned
    !=
    total_owned_weeks
    + total_owned_byes
):
    raise RuntimeError(
        "Owned-week accounting failed: "
        f"{total_transaction_owned:,} transaction-owned != "
        f"{total_owned_weeks:,} opportunities + "
        f"{total_owned_byes:,} owned byes"
    )

print(
    "Owned-week accounting:",
    "PASS",
)


# ============================================================
# PRODUCTION RESOLUTION BY YEAR
# ============================================================

print("\n" + "=" * 90)
print("PRODUCTION RESOLUTION BY YEAR")
print("=" * 90)

by_year = (
    inseason
    .groupby("year")
    .agg(
        stints=(
            "stint_id",
            "size",
        ),

        candidate_weeks=(
            "eligible_weeks",
            "sum",
        ),

        transaction_owned_weeks=(
            "transaction_owned_weeks",
            "sum",
        ),

        bye_weeks=(
            "bye_weeks",
            "sum",
        ),

        opportunity_weeks=(
            "owned_weeks",
            "sum",
        ),

        stat_rows=(
            "score_rows_observed",
            "sum",
        ),

        resolved_weeks=(
            "resolved_owned_weeks",
            "sum",
        ),

        unresolved_weeks=(
            "unresolved_owned_weeks",
            "sum",
        ),

        production_points=(
            "production_points",
            "sum",
        ),
    )
)

by_year[
    "resolution_rate"
] = (
    by_year["resolved_weeks"]
    /
    by_year["opportunity_weeks"]
    .replace(0, pd.NA)
)

print(
    by_year.to_string()
)


# We permit unresolved production to remain visible rather
# than silently converting unknown player-weeks to zero.
#
# At this stage the expected historical exception is the
# 2017 Ben Watson identity/mapping case.

if total_unresolved > 0:

    unresolved_players = set(
        inseason.loc[
            inseason[
                "unresolved_owned_weeks"
            ] > 0,
            "player",
        ]
        .dropna()
        .astype(str)
    )

    print(
        "Unresolved production players:",
        ", ".join(
            sorted(
                unresolved_players
            )
        ),
    )

    unexpected_unresolved = (
        unresolved_players
        -
        {"Ben Watson"}
    )

    if unexpected_unresolved:
        raise RuntimeError(
            "Unexpected unresolved production players: "
            + ", ".join(
                sorted(
                    unexpected_unresolved
                )
            )
        )


# ============================================================
# UNRESOLVED ELIGIBLE STINTS
# ============================================================

print("\n" + "=" * 90)
print("UNRESOLVED ELIGIBLE STINTS")
print("=" * 90)

unresolved = inseason[
    inseason[
        "unresolved_owned_weeks"
    ] > 0
].copy()

print(
    "Count:",
    len(unresolved),
)

if not unresolved.empty:

    print(
        unresolved[
            [
                "year",
                "team",
                "player",
                "player_position",
                "acquisition_type",
                "acquisition_datetime",
                "drop_datetime",
                "first_eligible_week",
                "owned_weeks",
                "resolved_owned_weeks",
                "unresolved_owned_weeks",
                "production_resolution_rate",
                "production_points",
            ]
        ]
        .sort_values(
            [
                "year",
                "unresolved_owned_weeks",
                "team",
                "player",
            ],
            ascending=[
                True,
                False,
                True,
                True,
            ],
        )
        .head(100)
        .to_string(
            index=False
        )
    )


# ============================================================
# TOP RAW ACQUISITION PRODUCTION
# ============================================================

print("\n" + "=" * 90)
print("TOP RAW WAIVER / FREE-AGENT PRODUCTION")
print("=" * 90)

print(
    inseason[
        [
            "year",
            "team",
            "player",
            "player_position",
            "acquisition_type",
            "acquisition_datetime",
            "first_eligible_week",
            "eligible_weeks",
            "production_points",
        ]
    ]
    .sort_values(
        "production_points",
        ascending=False,
    )
    .head(50)
    .to_string(index=False)
)


# ============================================================
# SAME-DAY TIMING CASES
# ============================================================

print("\n" + "=" * 90)
print("SAME-DAY GAME TIMING CASES")
print("=" * 90)

same_day_add = inseason[
    inseason["eligibility_reason"]
    .eq("SAME_DAY_AS_GAME")
]

same_day_drop = stint_weeks[
    stint_weeks["drop_week_reason"]
    .eq("DROP_SAME_DAY_AS_GAME")
]

print(
    "Acquisitions on player's game date:",
    len(same_day_add),
)

print(
    "Drops on player's game date:",
    len(same_day_drop),
)



# ============================================================
# FINAL WAIVER VALUE SCORING
# ============================================================

print()
print("=" * 90)
print("FINAL WAIVER VALUE SCORING")
print("=" * 90)

waiver_value = inseason.copy()

waiver_value["player_position"] = (
    waiver_value["player_position"]
    .astype(str)
    .str.upper()
)

waiver_value = waiver_value[
    waiver_value["player_position"].isin(
        {"QB", "RB", "WR", "TE"}
    )
    &
    waiver_value["first_eligible_week"].notna()
].copy()

waiver_value = waiver_value[
    waiver_value["year"].ne(2018)
].copy()

scoring_weeks = stint_weeks[
    stint_weeks["stint_id"].isin(
        waiver_value["stint_id"]
    )
    &
    stint_weeks["opportunity_week"].eq(True)
    &
    stint_weeks["production_resolved"].eq(True)
].copy()

scoring_weeks["fantasy_points"] = pd.to_numeric(
    scoring_weeks["fantasy_points"],
    errors="coerce",
).fillna(0.0)

production_scoring = (
    scoring_weeks
    .groupby("stint_id")
    .agg(
        scoring_opportunity_weeks=(
            "week",
            "count",
        ),
        scoring_production_points=(
            "fantasy_points",
            "sum",
        ),
        avg_points_per_week=(
            "fantasy_points",
            "mean",
        ),
        max_week_points=(
            "fantasy_points",
            "max",
        ),
    )
    .reset_index()
)

waiver_value = waiver_value.merge(
    production_scoring,
    on="stint_id",
    how="left",
    validate="one_to_one",
)

for col in [
    "scoring_opportunity_weeks",
    "scoring_production_points",
    "avg_points_per_week",
    "max_week_points",
]:
    waiver_value[col] = (
        pd.to_numeric(
            waiver_value[col],
            errors="coerce",
        )
        .fillna(0.0)
    )


def waiver_percentile_rank(series):
    if len(series) == 1:
        return pd.Series(
            [50.0],
            index=series.index,
        )

    return (
        series.rank(
            method="average",
            pct=True,
        )
        * 100.0
    )


waiver_value["rate_score"] = (
    waiver_value
    .groupby(
        [
            "year",
            "player_position",
        ]
    )["avg_points_per_week"]
    .transform(waiver_percentile_rank)
)

waiver_value["sustained_score"] = (
    waiver_value
    .groupby(
        [
            "year",
            "player_position",
        ]
    )["scoring_production_points"]
    .transform(waiver_percentile_rank)
)

waiver_value["waiver_score"] = (
    0.35
    * waiver_value["rate_score"]
    +
    0.65
    * waiver_value["sustained_score"]
)

waiver_value["waiver_value"] = (
    waiver_value["waiver_score"]
    - 50.0
)

waiver_value["meaningful_acquisition"] = (
    waiver_value[
        "scoring_opportunity_weeks"
    ].ge(2)
    |
    waiver_value[
        "scoring_production_points"
    ].ge(10.0)
)


def waiver_category(score):
    if score >= 92.0:
        return "Elite Find"
    if score >= 87.0:
        return "Great Pickup"
    if score >= 74.0:
        return "Good Pickup"
    if score >= 30.0:
        return "Ordinary"
    if score >= 12.0:
        return "Poor Pickup"
    return "Waiver Bust"


waiver_value["waiver_category"] = (
    waiver_value["waiver_score"]
    .map(waiver_category)
)

waiver_value["positive_pickup"] = (
    waiver_value["waiver_value"].gt(0.0)
)

waiver_value["good_pickup"] = (
    waiver_value["waiver_score"].ge(74.0)
)

waiver_value["great_pickup"] = (
    waiver_value["waiver_score"].ge(87.0)
)

waiver_value["elite_find"] = (
    waiver_value["waiver_score"].ge(92.0)
)

waiver_value["waiver_bust"] = (
    waiver_value["waiver_score"].lt(12.0)
)

waiver_value["team_canonical"] = (
    waiver_value["team"]
    .replace(TEAM_ALIASES)
)

meaningful_waiver = waiver_value[
    waiver_value["meaningful_acquisition"]
].copy()


def safe_pct(num, den):
    if den == 0:
        return np.nan
    return num / den * 100.0


manager_rows = []

for team, g in meaningful_waiver.groupby(
    "team_canonical"
):

    n = len(g)

    positive_count = int(
        g["positive_pickup"].sum()
    )

    good_count = int(
        g["good_pickup"].sum()
    )

    great_count = int(
        g["great_pickup"].sum()
    )

    elite_count = int(
        g["elite_find"].sum()
    )

    bust_count = int(
        g["waiver_bust"].sum()
    )

    manager_rows.append(
        {
            "team": team,
            "seasons_with_data":
                int(g["year"].nunique()),
            "meaningful_acquisitions":
                n,
            "avg_waiver_score":
                g["waiver_score"].mean(),
            "avg_waiver_value":
                g["waiver_value"].mean(),
            "median_waiver_value":
                g["waiver_value"].median(),
            "total_waiver_value":
                g["waiver_value"].sum(),
            "total_positive_value":
                g["waiver_value"]
                .clip(lower=0)
                .sum(),
            "positive_pickups":
                positive_count,
            "positive_rate":
                safe_pct(
                    positive_count,
                    n,
                ),
            "good_pickups":
                good_count,
            "good_rate":
                safe_pct(
                    good_count,
                    n,
                ),
            "great_pickups":
                great_count,
            "great_rate":
                safe_pct(
                    great_count,
                    n,
                ),
            "elite_finds":
                elite_count,
            "elite_find_rate":
                safe_pct(
                    elite_count,
                    n,
                ),
            "waiver_busts":
                bust_count,
            "bust_rate":
                safe_pct(
                    bust_count,
                    n,
                ),
            "production_points":
                g[
                    "scoring_production_points"
                ].sum(),
            "avg_opportunity_weeks":
                g[
                    "scoring_opportunity_weeks"
                ].mean(),
        }
    )

waiver_managers = pd.DataFrame(
    manager_rows
)

waiver_managers[
    "official_ranking_eligible"
] = (
    waiver_managers[
        "meaningful_acquisitions"
    ].ge(20)
)

waiver_managers[
    "official_rank"
] = np.nan

eligible_manager_mask = (
    waiver_managers[
        "official_ranking_eligible"
    ]
)

waiver_managers.loc[
    eligible_manager_mask,
    "official_rank",
] = (
    waiver_managers.loc[
        eligible_manager_mask,
        "avg_waiver_value",
    ]
    .rank(
        method="min",
        ascending=False,
    )
)

waiver_managers[
    "sample_label"
] = np.where(
    waiver_managers[
        "official_ranking_eligible"
    ],
    "Official",
    "Limited Sample",
)

season_rows = []

for (year, team), g in meaningful_waiver.groupby(
    [
        "year",
        "team_canonical",
    ]
):

    n = len(g)

    season_rows.append(
        {
            "year": int(year),
            "team": team,
            "meaningful_acquisitions":
                n,
            "avg_waiver_value":
                g["waiver_value"].mean(),
            "total_waiver_value":
                g["waiver_value"].sum(),
            "total_positive_value":
                g["waiver_value"]
                .clip(lower=0)
                .sum(),
            "positive_rate":
                safe_pct(
                    int(
                        g[
                            "positive_pickup"
                        ].sum()
                    ),
                    n,
                ),
            "good_rate":
                safe_pct(
                    int(
                        g[
                            "good_pickup"
                        ].sum()
                    ),
                    n,
                ),
            "elite_finds":
                int(
                    g["elite_find"].sum()
                ),
            "bust_rate":
                safe_pct(
                    int(
                        g[
                            "waiver_bust"
                        ].sum()
                    ),
                    n,
                ),
            "production_points":
                g[
                    "scoring_production_points"
                ].sum(),
        }
    )

waiver_seasons = pd.DataFrame(
    season_rows
)

waiver_hall_of_fame = (
    meaningful_waiver
    .sort_values(
        [
            "waiver_score",
            "scoring_production_points",
            "scoring_opportunity_weeks",
        ],
        ascending=[
            False,
            False,
            False,
        ],
    )
    .copy()
)

print(
    "Scored skill-position acquisitions:",
    f"{len(waiver_value):,}",
)

print(
    "Meaningful acquisitions:",
    f"{len(meaningful_waiver):,}",
)

print(
    "Trivial acquisitions excluded from manager ranking:",
    f"{len(waiver_value) - len(meaningful_waiver):,}",
)

print(
    "Official-ranking franchises:",
    int(
        waiver_managers[
            "official_ranking_eligible"
        ].sum()
    ),
)

if len(waiver_value) != 817:
    raise RuntimeError(
        "Expected 817 scored skill-position acquisitions; "
        f"found {len(waiver_value)}."
    )

if len(meaningful_waiver) != 615:
    raise RuntimeError(
        "Expected 615 meaningful acquisitions; "
        f"found {len(meaningful_waiver)}."
    )

if waiver_value["stint_id"].duplicated().any():
    raise RuntimeError(
        "Duplicate stint_id found in final Waiver Value output."
    )

if waiver_value[
    [
        "rate_score",
        "sustained_score",
        "waiver_score",
        "waiver_value",
    ]
].isna().any().any():
    raise RuntimeError(
        "Missing final Waiver Value scores detected."
    )

if not waiver_value[
    "waiver_score"
].between(
    0.0,
    100.0,
    inclusive="both",
).all():
    raise RuntimeError(
        "Waiver Score outside expected 0-100 range."
    )

if not waiver_value[
    "waiver_value"
].between(
    -50.0,
    50.0,
    inclusive="both",
).all():
    raise RuntimeError(
        "Waiver Value outside expected -50 to +50 range."
    )

regression_targets = {
    (2017, "Alvin Kamara"),
    (2020, "James Robinson"),
    (2020, "Justin Herbert"),
    (2023, "Puka Nacua"),
    (2023, "Kyren Williams"),
    (2023, "Sam LaPorta"),
    (2024, "Bucky Irving"),
}

available_targets = set(
    zip(
        waiver_value["year"],
        waiver_value["player"],
    )
)

missing_targets = (
    regression_targets
    -
    available_targets
)

if missing_targets:
    raise RuntimeError(
        "Missing Waiver Value regression targets: "
        + str(
            sorted(missing_targets)
        )
    )

print(
    "Known elite acquisition regression targets: PASS"
)

official_manager_order = (
    waiver_managers[
        waiver_managers[
            "official_ranking_eligible"
        ]
    ]
    .sort_values(
        "official_rank"
    )["team"]
    .tolist()
)

expected_top_three = [
    "Post Mahomes",
    "ThreatLevelMidnight",
    "malle_dips_pouches",
]

if official_manager_order[:3] != expected_top_three:
    raise RuntimeError(
        "Unexpected official waiver manager top three: "
        + str(
            official_manager_order[:3]
        )
    )

print(
    "Official manager top-three regression check: PASS"
)

WAIVER_VALUE_FILE = (
    OUT_DIR
    / "waiver_value_acquisitions.csv"
)

WAIVER_MANAGER_FILE = (
    OUT_DIR
    / "waiver_value_franchise.csv"
)

WAIVER_SEASON_FILE = (
    OUT_DIR
    / "waiver_value_team_season.csv"
)

WAIVER_HOF_FILE = (
    OUT_DIR
    / "waiver_value_hall_of_fame.csv"
)

waiver_value.to_csv(
    WAIVER_VALUE_FILE,
    index=False,
)

waiver_managers.to_csv(
    WAIVER_MANAGER_FILE,
    index=False,
)

waiver_seasons.to_csv(
    WAIVER_SEASON_FILE,
    index=False,
)

waiver_hall_of_fame.to_csv(
    WAIVER_HOF_FILE,
    index=False,
)

print()
print("Final Waiver Value outputs:")
print(WAIVER_VALUE_FILE)
print(WAIVER_MANAGER_FILE)
print(WAIVER_SEASON_FILE)
print(WAIVER_HOF_FILE)

print()
print(
    "PASS — FINAL WAIVER VALUE MODEL BUILT"
)

print()

# ============================================================
# OUTPUTS
# ============================================================

print("\n" + "=" * 90)
print("OUTPUTS")
print("=" * 90)

print(STINT_FILE)
print(STINT_WEEK_FILE)
print(AUDIT_FILE)

print(
    "\nPASS — transaction-authoritative "
    "waiver foundation built."
)

print(
    "Do not calculate normalized Waiver Value "
    "until score-capture audit is reviewed."
)
