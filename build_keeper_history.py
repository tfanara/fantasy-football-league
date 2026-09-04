from pathlib import Path
import re

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DRAFT_FILE = (
    BASE_DIR
    / "data"
    / "drafts"
    / "all_drafts.csv"
)

TRANSACTION_FILE = (
    BASE_DIR
    / "data"
    / "transactions"
    / "all_transactions.csv"
)

KEEPER_DIR = (
    BASE_DIR
    / "data"
    / "keepers"
)

KEEPER_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_CSV = (
    KEEPER_DIR
    / "keeper_history.csv"
)

OUTPUT_JSON = (
    KEEPER_DIR
    / "keeper_history.json"
)

END_OF_SEASON_OWNERSHIP_FILE = (
    KEEPER_DIR
    / "end_of_season_ownership.csv"
)

ELIGIBILITY_2026_CSV = (
    KEEPER_DIR
    / "keeper_eligibility_2026.csv"
)

ELIGIBILITY_2026_JSON = (
    KEEPER_DIR
    / "keeper_eligibility_2026.json"
)


# ============================================================
# LEAGUE RULES
# ============================================================

ROUND_ADVANCE_PER_YEAR = 1
WAIVER_KEEPER_ROUND = 10

# Known historical cases where Yahoo's actual keeper round
# does not match the normal rule progression and the available
# transaction history does not explain the difference.
KNOWN_ROUND_EXCEPTIONS = {
    (2020, "Joe Mantegna", "Miles Sanders"),
    (2024, "Malle ❤️ 🐸", "Adam Thielen"),
}

# Keeper-rights succession is deliberately NOT a historical team alias.
# Big Sack Jack remains a separate franchise in historical statistics.
# Buttermilk Puuump inherited Big Sack Jack's roster/keeper rights after 2022.
KEEPER_FRANCHISE_SUCCESSIONS = {
    (2022, "Big Sack Jack", "Buttermilk Puuump"),
}

# Authoritative corrections for cases where the collected ownership sources
# are incomplete or internally inconsistent.
END_OF_SEASON_OWNERSHIP_OVERRIDES = {
    (2020, "Josh Allen"): "Patty Primetimes",
    (2020, "Justin Jefferson"): "Voldemort",
    (2024, "Malik Nabers"): "Joe Mantegna",
}


# ============================================================
# LOAD DATA
# ============================================================

print()
print("=" * 80)
print("BUILDING FINAL KEEPER HISTORY")
print("=" * 80)

drafts = pd.read_csv(
    DRAFT_FILE
)

transactions = pd.read_csv(
    TRANSACTION_FILE
)

if not END_OF_SEASON_OWNERSHIP_FILE.exists():
    raise FileNotFoundError(
        "Missing end-of-season ownership file: "
        f"{END_OF_SEASON_OWNERSHIP_FILE}\n"
        "Run build_keeper_end_of_season_eligibility.py first."
    )

end_of_season_ownership = pd.read_csv(
    END_OF_SEASON_OWNERSHIP_FILE
)

print()
print(
    f"Loaded {len(drafts)} draft selections."
)

print(
    f"Loaded {len(transactions)} transactions."
)

print(
    f"Loaded {len(end_of_season_ownership)} end-of-season ownership rows."
)


# ============================================================
# NORMALIZE DRAFT DATA
# ============================================================

for column in [
    "year",
    "round",
    "pick_in_round",
    "overall_pick",
]:

    drafts[column] = pd.to_numeric(
        drafts[column],
        errors="coerce",
    )


if drafts["keeper"].dtype == object:

    drafts["keeper"] = (
        drafts["keeper"]
        .astype(str)
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
            }
        )
        .fillna(False)
    )

else:

    drafts["keeper"] = (
        drafts["keeper"]
        .fillna(False)
        .astype(bool)
    )


drafts = (
    drafts
    .sort_values(
        [
            "year",
            "overall_pick",
        ]
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# NORMALIZE TRANSACTION DATA
# ============================================================

transactions["year"] = pd.to_numeric(
    transactions["year"],
    errors="coerce",
)

for column in [
    "team",
    "added_player",
    "dropped_player",
    "acquisition_type",
    "date",
]:

    if column in transactions.columns:

        transactions[column] = (
            transactions[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )


# ============================================================
# TRANSACTION DATE PARSER
# ============================================================

MONTH_NUMBERS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def parse_transaction_datetime(
    season_year,
    date_text,
):

    if not date_text:
        return pd.NaT

    match = re.match(
        r"^([A-Z][a-z]{2})\s+"
        r"(\d{1,2}),\s+"
        r"(\d{1,2}):(\d{2})\s+"
        r"(am|pm)$",
        date_text,
        re.IGNORECASE,
    )

    if not match:
        return pd.NaT

    month_text = (
        match.group(1)
        .title()
    )

    month = MONTH_NUMBERS.get(
        month_text
    )

    if month is None:
        return pd.NaT

    day = int(
        match.group(2)
    )

    hour = int(
        match.group(3)
    )

    minute = int(
        match.group(4)
    )

    am_pm = (
        match.group(5)
        .lower()
    )

    if am_pm == "pm" and hour != 12:
        hour += 12

    if am_pm == "am" and hour == 12:
        hour = 0

    calendar_year = int(
        season_year
    )

    if month <= 2:
        calendar_year += 1

    try:

        return pd.Timestamp(
            year=calendar_year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
        )

    except ValueError:

        return pd.NaT


transactions[
    "transaction_datetime"
] = transactions.apply(
    lambda row:
        parse_transaction_datetime(
            row["year"],
            row["date"],
        ),
    axis=1,
)


transactions = (
    transactions
    .sort_values(
        [
            "year",
            "transaction_datetime",
        ]
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# DRAFT LOOKUPS
# ============================================================

def get_draft_entry(
    player,
    year,
):

    result = drafts[
        (drafts["player"] == player)
        & (drafts["year"] == year)
    ]

    if result.empty:
        return None

    return (
        result
        .sort_values(
            "overall_pick"
        )
        .iloc[0]
    )


# ============================================================
# TRANSACTION LOOKUPS
# ============================================================

def get_player_transactions(
    player,
    year,
):

    result = transactions[
        (transactions["year"] == year)
        & (
            (transactions["added_player"] == player)
            |
            (transactions["dropped_player"] == player)
        )
    ].copy()

    return (
        result
        .sort_values(
            "transaction_datetime"
        )
        .reset_index(
            drop=True
        )
    )


def find_keeper_team_acquisition(
    player,
    prior_season,
    keeper_team,
):

    history = get_player_transactions(
        player,
        prior_season,
    )

    if history.empty:
        return None

    acquisitions = history[
        (history["added_player"] == player)
        & (history["team"] == keeper_team)
        & (
            history["acquisition_type"].isin(
                [
                    "Waiver",
                    "Free Agent",
                ]
            )
        )
    ].copy()

    if acquisitions.empty:
        return None

    return (
        acquisitions
        .sort_values(
            "transaction_datetime"
        )
        .iloc[-1]
    )


# ============================================================
# END-OF-SEASON OWNERSHIP / KEEPER ELIGIBILITY
# ============================================================

def get_end_of_season_owner(
    player,
    prior_season,
):

    override_key = (
        int(prior_season),
        player,
    )

    if override_key in END_OF_SEASON_OWNERSHIP_OVERRIDES:

        return {
            "owner":
                END_OF_SEASON_OWNERSHIP_OVERRIDES[
                    override_key
                ],

            "confidence":
                "Authoritative Override",

            "evidence":
                "Confirmed historical end-of-season ownership",
        }

    required_columns = {
        "year",
        "player",
        "final_owner",
    }

    missing_columns = (
        required_columns
        - set(
            end_of_season_ownership.columns
        )
    )

    if missing_columns:

        raise ValueError(
            "end_of_season_ownership.csv is missing required columns: "
            + ", ".join(
                sorted(
                    missing_columns
                )
            )
        )

    matches = end_of_season_ownership[
        (
            pd.to_numeric(
                end_of_season_ownership["year"],
                errors="coerce",
            )
            == prior_season
        )
        & (
            end_of_season_ownership["player"]
            .fillna("")
            .astype(str)
            .str.strip()
            == player
        )
    ].copy()

    if matches.empty:

        return {
            "owner": None,
            "confidence": "Unresolved",
            "evidence": "No end-of-season ownership record",
        }

    row = matches.iloc[0]

    owner = row.get(
        "final_owner"
    )

    if pd.isna(owner):

        owner = None

    elif str(owner).strip():

        owner = str(
            owner
        ).strip()

    else:

        owner = None

    confidence = row.get(
        "ownership_confidence",
        "Ownership File",
    )

    evidence = row.get(
        "ownership_evidence",
        "",
    )

    return {
        "owner": owner,
        "confidence": confidence,
        "evidence": evidence,
    }


def keeper_team_has_prior_roster_rights(
    prior_season,
    prior_owner,
    keeper_team,
):

    if prior_owner is None:

        return (
            False,
            None,
        )

    if prior_owner == keeper_team:

        return (
            True,
            "Same Franchise",
        )

    succession_key = (
        int(prior_season),
        prior_owner,
        keeper_team,
    )

    if (
        succession_key
        in KEEPER_FRANCHISE_SUCCESSIONS
    ):

        return (
            True,
            "Inherited Keeper Rights",
        )

    return (
        False,
        None,
    )


# ============================================================
# ROUND BASIS
#
# FINALIZED RULE:
#
# 1. If player was drafted / kept in prior year:
#       next keeper round = prior round - 1
#
#    Later waiver/free-agent activity does NOT override that.
#
# 2. If player was NOT drafted in prior year:
#       qualifying waiver/free-agent acquisition
#       by keeper franchise -> Round 10
#
# 3. Otherwise:
#       unknown
# ============================================================

def determine_round_basis(
    player,
    keeper_year,
    keeper_team,
):

    prior_year = (
        keeper_year - 1
    )

    prior_draft = (
        get_draft_entry(
            player,
            prior_year,
        )
    )

    # --------------------------------------------------------
    # PRIOR-YEAR DRAFT / KEEPER ALWAYS TAKES PRECEDENCE
    # --------------------------------------------------------

    if prior_draft is not None:

        prior_round = int(
            prior_draft["round"]
        )

        expected_round = max(
            1,
            prior_round
            - ROUND_ADVANCE_PER_YEAR,
        )

        if bool(
            prior_draft["keeper"]
        ):

            basis = (
                "Prior Keeper"
            )

        else:

            basis = (
                "Prior Draft"
            )

        return {
            "basis":
                basis,

            "expected_round":
                expected_round,

            "prior_draft":
                prior_draft,

            "waiver_acquisition":
                None,

            "waiver_baseline":
                False,
        }


    # --------------------------------------------------------
    # NO PRIOR-YEAR DRAFT ENTRY:
    # CHECK FOR WAIVER / FREE AGENT ACQUISITION
    # --------------------------------------------------------

    acquisition = (
        find_keeper_team_acquisition(
            player,
            prior_year,
            keeper_team,
        )
    )


    if acquisition is not None:

        return {
            "basis":
                "Waiver / Free Agent",

            "expected_round":
                WAIVER_KEEPER_ROUND,

            "prior_draft":
                None,

            "waiver_acquisition":
                acquisition,

            "waiver_baseline":
                True,
        }


    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    return {
        "basis":
            "Unknown",

        "expected_round":
            None,

        "prior_draft":
            None,

        "waiver_acquisition":
            None,

        "waiver_baseline":
            False,
    }


# ============================================================
# KEEPER CLOCK
#
# The clock is based on consecutive prior keeper seasons.
#
# Waiver/free-agent acquisition DOES NOT reset the clock.
# ============================================================

def count_consecutive_prior_keeper_years(
    player,
    keeper_year,
):

    count = 0

    year = (
        keeper_year - 1
    )

    while True:

        entry = get_draft_entry(
            player,
            year,
        )

        if entry is None:
            break

        if not bool(
            entry["keeper"]
        ):
            break

        count += 1

        year -= 1

    return count


# ============================================================
# ORIGINAL DRAFT
# ============================================================

def find_original_draft(
    player,
    keeper_year,
):

    year = (
        keeper_year - 1
    )

    minimum_year = int(
        drafts["year"].min()
    )

    while year >= minimum_year:

        entry = get_draft_entry(
            player,
            year,
        )

        if entry is None:

            year -= 1
            continue

        if not bool(
            entry["keeper"]
        ):

            return {
                "year":
                    int(
                        entry["year"]
                    ),

                "round":
                    int(
                        entry["round"]
                    ),

                "team":
                    entry["team"],
            }

        year -= 1

    return {
        "year": None,
        "round": None,
        "team": None,
    }


# ============================================================
# BUILD KEEPER RECORDS
# ============================================================

keeper_rows = []

keeper_drafts = (
    drafts[
        drafts["keeper"]
    ]
    .copy()
    .sort_values(
        [
            "year",
            "overall_pick",
        ]
    )
)


for _, keeper in keeper_drafts.iterrows():

    year = int(
        keeper["year"]
    )

    team = (
        keeper["team"]
    )

    player = (
        keeper["player"]
    )

    actual_round = int(
        keeper["round"]
    )


    # ========================================================
    # END-OF-SEASON OWNERSHIP ELIGIBILITY
    # ========================================================

    prior_season = (
        year - 1
    )

    ownership = (
        get_end_of_season_owner(
            player,
            prior_season,
        )
    )

    prior_season_end_owner = (
        ownership[
            "owner"
        ]
    )

    prior_ownership_confidence = (
        ownership[
            "confidence"
        ]
    )

    prior_ownership_evidence = (
        ownership[
            "evidence"
        ]
    )

    (
        end_of_season_eligible,
        keeper_rights_basis,
    ) = keeper_team_has_prior_roster_rights(
        prior_season,
        prior_season_end_owner,
        team,
    )

    if prior_season_end_owner is None:

        end_of_season_eligibility = (
            "Ownership Unresolved"
        )

    elif end_of_season_eligible:

        if (
            keeper_rights_basis
            == "Inherited Keeper Rights"
        ):

            end_of_season_eligibility = (
                "Eligible — Inherited Keeper Rights"
            )

        else:

            end_of_season_eligibility = (
                "Eligible — Held at End of Prior Season"
            )

    else:

        end_of_season_eligibility = (
            "INELIGIBLE — Different End-of-Season Owner"
        )


    # ========================================================
    # KEEPER CLOCK
    # ========================================================

    prior_keeper_years = (
        count_consecutive_prior_keeper_years(
            player,
            year,
        )
    )

    keeper_number = (
        prior_keeper_years + 1
    )


    if keeper_number == 1:

        keeper_status = (
            "1st-Year Keeper"
        )

        keeper_limit_status = (
            "Within Keeper Limit"
        )

    elif keeper_number == 2:

        keeper_status = (
            "2nd-Year Keeper — Final Year"
        )

        keeper_limit_status = (
            "Final Eligible Keeper Year"
        )

    else:

        keeper_status = (
            "Keeper Limit Exception"
        )

        keeper_limit_status = (
            "Exceeded Normal Keeper Limit"
        )


    # ========================================================
    # ROUND BASIS
    # ========================================================

    basis = (
        determine_round_basis(
            player,
            year,
            team,
        )
    )

    acquisition_basis = (
        basis[
            "basis"
        ]
    )

    expected_round = (
        basis[
            "expected_round"
        ]
    )

    prior_draft = (
        basis[
            "prior_draft"
        ]
    )

    waiver_acquisition = (
        basis[
            "waiver_acquisition"
        ]
    )

    waiver_baseline = bool(
        basis[
            "waiver_baseline"
        ]
    )


    # ========================================================
    # PRIOR-YEAR DETAILS
    # ========================================================

    previous_team = None
    previous_round = None
    previous_was_keeper = False

    if prior_draft is not None:

        previous_team = (
            prior_draft[
                "team"
            ]
        )

        previous_round = int(
            prior_draft[
                "round"
            ]
        )

        previous_was_keeper = bool(
            prior_draft[
                "keeper"
            ]
        )


    # ========================================================
    # WAIVER DETAILS
    # ========================================================

    waiver_acquisition_type = None
    waiver_acquisition_team = None
    waiver_acquisition_date = None

    if waiver_acquisition is not None:

        waiver_acquisition_type = (
            waiver_acquisition[
                "acquisition_type"
            ]
        )

        waiver_acquisition_team = (
            waiver_acquisition[
                "team"
            ]
        )

        waiver_acquisition_date = (
            waiver_acquisition[
                "date"
            ]
        )


    # ========================================================
    # ORIGINAL DRAFT
    # ========================================================

    original = (
        find_original_draft(
            player,
            year,
        )
    )

    original_draft_year = (
        original["year"]
    )

    original_draft_round = (
        original["round"]
    )

    original_draft_team = (
        original["team"]
    )


    # ========================================================
    # ROUND VALIDATION
    # ========================================================

    exception_key = (
        year,
        team,
        player,
    )

    known_exception = (
        exception_key
        in KNOWN_ROUND_EXCEPTIONS
    )


    if known_exception:

        round_matches_rule = False

        rule_status = (
            "Historical Round Exception"
        )

    elif expected_round is None:

        round_matches_rule = None

        rule_status = (
            "Cannot Determine Expected Round"
        )

    elif actual_round == expected_round:

        round_matches_rule = True

        rule_status = (
            "Matches Keeper Rule"
        )

    else:

        round_matches_rule = False

        rule_status = (
            "Round Rule Exception"
        )


    # ========================================================
    # NEXT-SEASON STATUS
    # ========================================================

    if not end_of_season_eligible:

        next_keeper_round = None

        if prior_season_end_owner is None:

            next_season_status = (
                "Ownership Unresolved"
            )

        else:

            next_season_status = (
                "Ineligible — Not Held at End of Prior Season"
            )

    elif keeper_number >= 2:

        next_keeper_round = None

        next_season_status = (
            "Must Return to Draft Pool"
        )

    else:

        next_keeper_round = max(
            1,
            actual_round
            - ROUND_ADVANCE_PER_YEAR,
        )

        next_season_status = (
            f"Eligible — Round "
            f"{next_keeper_round}"
        )


    # ========================================================
    # SAVE
    # ========================================================

    keeper_rows.append(
        {
            "year":
                year,

            "team":
                team,

            "player":
                player,

            "round_kept_in":
                actual_round,

            "pick_in_round":
                int(
                    keeper[
                        "pick_in_round"
                    ]
                ),

            "overall_pick":
                int(
                    keeper[
                        "overall_pick"
                    ]
                ),

            "keeper_number":
                keeper_number,

            "keeper_status":
                keeper_status,

            "keeper_limit_status":
                keeper_limit_status,

            "acquisition_basis":
                acquisition_basis,

            "waiver_baseline":
                waiver_baseline,

            "waiver_acquisition_type":
                waiver_acquisition_type,

            "waiver_acquisition_team":
                waiver_acquisition_team,

            "waiver_acquisition_date":
                waiver_acquisition_date,

            "previous_team":
                previous_team,

            "previous_year_round":
                previous_round,

            "previous_was_keeper":
                previous_was_keeper,

            "original_draft_year":
                original_draft_year,

            "original_draft_round":
                original_draft_round,

            "original_draft_team":
                original_draft_team,

            "expected_round":
                expected_round,

            "round_matches_rule":
                round_matches_rule,

            "known_round_exception":
                known_exception,

            "rule_status":
                rule_status,

            "prior_season":
                prior_season,

            "prior_season_end_owner":
                prior_season_end_owner,

            "prior_ownership_confidence":
                prior_ownership_confidence,

            "prior_ownership_evidence":
                prior_ownership_evidence,

            "keeper_rights_basis":
                keeper_rights_basis,

            "end_of_season_eligible":
                end_of_season_eligible,

            "end_of_season_eligibility":
                end_of_season_eligibility,

            "next_keeper_round":
                next_keeper_round,

            "next_season_status":
                next_season_status,
        }
    )


# ============================================================
# DATAFRAME
# ============================================================

keeper_history = pd.DataFrame(
    keeper_rows
)

keeper_history = (
    keeper_history
    .sort_values(
        [
            "year",
            "team",
            "round_kept_in",
        ]
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# BUILD 2026 KEEPER ELIGIBILITY POOL
#
# Every player held at the end of 2025 is evaluated.
#
# Hard gates:
#   1. Player must have a resolvable 2025 end-of-season owner.
#   2. Keeper clock may not already be exhausted.
#   3. Keeper round basis must be determinable.
#
# Round basis:
#   - 2025 drafted/kept player -> 2025 round - 1
#   - otherwise qualifying 2025 waiver/free-agent acquisition -> Round 10
# ============================================================

ELIGIBILITY_SEASON = 2026
PRIOR_ELIGIBILITY_SEASON = ELIGIBILITY_SEASON - 1

eligibility_rows = []

ownership_2025 = (
    end_of_season_ownership[
        pd.to_numeric(
            end_of_season_ownership["year"],
            errors="coerce",
        )
        == PRIOR_ELIGIBILITY_SEASON
    ]
    .copy()
)

for _, ownership_row in ownership_2025.iterrows():

    player = str(
        ownership_row["player"]
    ).strip()

    owner = ownership_row.get(
        "final_owner"
    )

    if pd.isna(owner) or not str(owner).strip():
        continue

    team = str(
        owner
    ).strip()

    ownership_confidence = ownership_row.get(
        "ownership_confidence",
        "",
    )

    ownership_evidence = ownership_row.get(
        "ownership_evidence",
        "",
    )

    basis = determine_round_basis(
        player,
        ELIGIBILITY_SEASON,
        team,
    )

    acquisition_basis = basis[
        "basis"
    ]

    keeper_round = basis[
        "expected_round"
    ]

    prior_draft = basis[
        "prior_draft"
    ]

    waiver_acquisition = basis[
        "waiver_acquisition"
    ]

    prior_keeper_years = (
        count_consecutive_prior_keeper_years(
            player,
            ELIGIBILITY_SEASON,
        )
    )

    keeper_number = (
        prior_keeper_years + 1
    )

    if keeper_number == 1:

        keeper_status = (
            "1st-Year Keeper"
        )

        keeper_limit_eligible = True

    elif keeper_number == 2:

        keeper_status = (
            "2nd-Year Keeper — Final Year"
        )

        keeper_limit_eligible = True

    else:

        keeper_status = (
            "Must Return to Draft Pool"
        )

        keeper_limit_eligible = False

    round_basis_resolved = (
        keeper_round is not None
    )

    eligible = bool(
        keeper_limit_eligible
        and round_basis_resolved
    )

    if not keeper_limit_eligible:

        eligibility_status = (
            "Ineligible — Keeper Limit Exhausted"
        )

    elif not round_basis_resolved:

        eligibility_status = (
            "Ineligible — Cannot Determine Keeper Round"
        )

    else:

        eligibility_status = (
            f"Eligible — Round {int(keeper_round)}"
        )

    prior_round = None
    prior_was_keeper = False
    prior_draft_team = None

    if prior_draft is not None:

        prior_round = int(
            prior_draft["round"]
        )

        prior_was_keeper = bool(
            prior_draft["keeper"]
        )

        prior_draft_team = (
            prior_draft["team"]
        )

    waiver_acquisition_type = None
    waiver_acquisition_date = None

    if waiver_acquisition is not None:

        waiver_acquisition_type = (
            waiver_acquisition[
                "acquisition_type"
            ]
        )

        waiver_acquisition_date = (
            waiver_acquisition[
                "date"
            ]
        )

    eligibility_rows.append(
        {
            "keeper_year":
                ELIGIBILITY_SEASON,

            "team":
                team,

            "player":
                player,

            "eligible":
                eligible,

            "eligibility_status":
                eligibility_status,

            "keeper_round":
                (
                    int(keeper_round)
                    if keeper_round is not None
                    else None
                ),

            "keeper_number":
                keeper_number,

            "keeper_status":
                keeper_status,

            "acquisition_basis":
                acquisition_basis,

            "prior_year_round":
                prior_round,

            "prior_was_keeper":
                prior_was_keeper,

            "prior_draft_team":
                prior_draft_team,

            "waiver_acquisition_type":
                waiver_acquisition_type,

            "waiver_acquisition_date":
                waiver_acquisition_date,

            "end_of_prior_season_owner":
                team,

            "ownership_confidence":
                ownership_confidence,

            "ownership_evidence":
                ownership_evidence,
        }
    )


keeper_eligibility_2026 = pd.DataFrame(
    eligibility_rows
)

keeper_eligibility_2026 = (
    keeper_eligibility_2026
    .sort_values(
        [
            "team",
            "eligible",
            "keeper_round",
            "player",
        ],
        ascending=[
            True,
            False,
            True,
            True,
        ],
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# 2026 CONFIRMED KEEPER VALIDATION
# ============================================================

CONFIRMED_KEEPERS_2026 = {
    "Patty Primetimes":
        ("James Cook III", 2),

    "Joe Mantegna":
        ("Tyler Warren", 9),

    "Malle ❤️ 🐸":
        ("D'Andre Swift", 4),

    "Buttermilk Puuump":
        ("George Pickens", 3),

    "ThreatLevelMidnight":
        ("Rashee Rice", 6),

    "The Big Gronkowski":
        ("Drake Maye", 8),

    "Pop Lockett Drop it":
        ("Javonte Williams", 7),

    "Voldemort":
        ("Jaxon Smith-Njigba", 2),

    "Post Mahomes":
        ("Cam Skattebo", 9),

    "Uncle Rico":
        ("Jonathan Taylor", 1),

    "Ginger FC":
        ("Chris Olave", 5),
}

confirmed_validation_rows = []

for team, (
    player,
    expected_round,
) in CONFIRMED_KEEPERS_2026.items():

    match = keeper_eligibility_2026[
        (
            keeper_eligibility_2026["team"]
            == team
        )
        & (
            keeper_eligibility_2026["player"]
            == player
        )
    ]

    if match.empty:

        confirmed_validation_rows.append(
            {
                "team": team,
                "player": player,
                "expected_round": expected_round,
                "actual_round": None,
                "status": "FAIL — Not in eligibility pool",
            }
        )

        continue

    row = match.iloc[0]

    actual_round = row[
        "keeper_round"
    ]

    if not bool(
        row["eligible"]
    ):

        status = (
            "FAIL — Marked ineligible"
        )

    elif int(
        actual_round
    ) != expected_round:

        status = (
            "FAIL — Wrong round"
        )

    else:

        status = "PASS"

    confirmed_validation_rows.append(
        {
            "team": team,
            "player": player,
            "expected_round": expected_round,
            "actual_round": actual_round,
            "status": status,
        }
    )


confirmed_validation = pd.DataFrame(
    confirmed_validation_rows
)

loveland_for_patty = (
    keeper_eligibility_2026[
        (
            keeper_eligibility_2026["team"]
            == "Patty Primetimes"
        )
        & (
            keeper_eligibility_2026["player"]
            == "Colston Loveland"
        )
        & (
            keeper_eligibility_2026["eligible"]
        )
    ]
)

# ============================================================
# SAVE
# ============================================================

keeper_history.to_csv(
    OUTPUT_CSV,
    index=False,
)

keeper_history.to_json(
    OUTPUT_JSON,
    orient="records",
    indent=2,
)

keeper_eligibility_2026.to_csv(
    ELIGIBILITY_2026_CSV,
    index=False,
)

keeper_eligibility_2026.to_json(
    ELIGIBILITY_2026_JSON,
    orient="records",
    indent=2,
)


# ============================================================
# 2026 ELIGIBILITY SUMMARY / VALIDATION
# ============================================================

print()
print("=" * 80)
print("2026 KEEPER ELIGIBILITY POOL")
print("=" * 80)
print()

print(
    f"End-of-2025 rostered players evaluated: "
    f"{len(keeper_eligibility_2026)}"
)

print(
    f"Eligible for 2026: "
    f"{int(keeper_eligibility_2026['eligible'].sum())}"
)

print(
    f"Ineligible / unresolved: "
    f"{int((~keeper_eligibility_2026['eligible']).sum())}"
)

print()
print("ELIGIBILITY STATUS:")
print()

print(
    keeper_eligibility_2026[
        "eligibility_status"
    ]
    .value_counts()
    .to_string()
)

print()
print("=" * 80)
print("CONFIRMED 2026 KEEPER VALIDATION")
print("=" * 80)
print()

print(
    confirmed_validation
    .to_string(
        index=False
    )
)

confirmed_failures = (
    confirmed_validation[
        confirmed_validation[
            "status"
        ] != "PASS"
    ]
)

print()

if confirmed_failures.empty:

    print(
        "PASS: all 11 confirmed 2026 keepers "
        "are eligible at the expected rounds."
    )

else:

    print(
        "FAIL: one or more confirmed 2026 keepers "
        "did not validate."
    )

print()

if loveland_for_patty.empty:

    print(
        "PASS: Colston Loveland is NOT eligible "
        "for Patty Primetimes."
    )

else:

    print(
        "FAIL: Colston Loveland incorrectly appears "
        "eligible for Patty Primetimes."
    )


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 80)
print("KEEPER STATUS SUMMARY")
print("=" * 80)

print()

print(
    keeper_history[
        "keeper_status"
    ]
    .value_counts()
    .to_string()
)


# ============================================================
# ROUND BASIS SUMMARY
# ============================================================

print()
print("=" * 80)
print("KEEPER ROUND BASIS")
print("=" * 80)

print()

print(
    keeper_history[
        "acquisition_basis"
    ]
    .value_counts()
    .to_string()
)


# ============================================================
# RULE EXCEPTIONS
# ============================================================

exceptions = (
    keeper_history[
        keeper_history[
            "rule_status"
        ].isin(
            [
                "Historical Round Exception",
                "Round Rule Exception",
            ]
        )
    ]
    .copy()
)


print()
print("=" * 80)
print("ROUND RULE EXCEPTIONS")
print("=" * 80)

print()

if exceptions.empty:

    print(
        "No round exceptions found."
    )

else:

    print(
        exceptions[
            [
                "year",
                "team",
                "player",
                "keeper_status",
                "acquisition_basis",
                "previous_year_round",
                "expected_round",
                "round_kept_in",
                "rule_status",
            ]
        ]
        .to_string(
            index=False
        )
    )


# ============================================================
# KEEPER LIMIT EXCEPTIONS
# ============================================================

limit_exceptions = (
    keeper_history[
        keeper_history[
            "keeper_number"
        ] > 2
    ]
    .copy()
)


print()
print("=" * 80)
print("KEEPER LIMIT EXCEPTIONS")
print("=" * 80)

print()

if limit_exceptions.empty:

    print(
        "No player exceeded the normal two-year keeper limit."
    )

else:

    print(
        limit_exceptions[
            [
                "year",
                "team",
                "player",
                "keeper_number",
                "round_kept_in",
                "keeper_status",
            ]
        ]
        .to_string(
            index=False
        )
    )


# ============================================================
# END-OF-SEASON ELIGIBILITY AUDIT
# ============================================================

print()
print("=" * 80)
print("END-OF-SEASON KEEPER ELIGIBILITY")
print("=" * 80)
print()

print(
    keeper_history[
        "end_of_season_eligibility"
    ]
    .value_counts(
        dropna=False
    )
    .to_string()
)

ownership_problems = (
    keeper_history[
        ~keeper_history[
            "end_of_season_eligible"
        ].fillna(False)
    ]
    .copy()
)

print()

if ownership_problems.empty:

    print(
        "PASS: every historical keeper satisfies "
        "end-of-season ownership eligibility."
    )

else:

    print(
        "REVIEW REQUIRED: keeper ownership exceptions/unresolved rows:"
    )

    print()

    print(
        ownership_problems[
            [
                "year",
                "team",
                "player",
                "prior_season_end_owner",
                "prior_ownership_confidence",
                "end_of_season_eligibility",
            ]
        ]
        .to_string(
            index=False
        )
    )


# ============================================================
# LATEST SEASON
# ============================================================

latest_year = int(
    keeper_history[
        "year"
    ].max()
)

latest = (
    keeper_history[
        keeper_history[
            "year"
        ] == latest_year
    ]
    .copy()
)


print()
print("=" * 80)
print(
    f"{latest_year} KEEPER STATUS"
)
print("=" * 80)

print()

print(
    latest[
        [
            "team",
            "player",
            "round_kept_in",
            "keeper_status",
            "acquisition_basis",
            "rule_status",
            "end_of_season_eligibility",
            "next_season_status",
        ]
    ]
    .to_string(
        index=False
    )
)


# ============================================================
# FILES
# ============================================================

print()
print("=" * 80)
print("FILES CREATED")
print("=" * 80)

print()
print(OUTPUT_CSV)
print(OUTPUT_JSON)
print(ELIGIBILITY_2026_CSV)
print(ELIGIBILITY_2026_JSON)

print()
print(
    f"Total keeper records: "
    f"{len(keeper_history)}"
)

print()
print(
    "Final keeper history build complete."
)