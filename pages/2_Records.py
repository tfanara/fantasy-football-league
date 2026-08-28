import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

st.set_page_config(page_title='League Records', page_icon='🏅', layout='wide')

BASE_DIR = Path(__file__).resolve().parents[1]
HISTORY_DIR = BASE_DIR / 'data' / 'history'
PLAYOFF_DIR = BASE_DIR / 'data' / 'playoffs'
PLAYER_WEEK_DIR = BASE_DIR / 'data' / 'matchups' / 'player_week_stats'
ANALYSIS_DIR = PLAYER_WEEK_DIR / 'analysis'

FILES = {
    'team_games': HISTORY_DIR / 'team_games.csv',
    'season_records': HISTORY_DIR / 'season_records.csv',
    'all_time_records': HISTORY_DIR / 'all_time_records.csv',
    'championships': PLAYOFF_DIR / 'championships.csv',
    'playoff_records': PLAYOFF_DIR / 'playoff_records.csv',
    'playoff_games': PLAYOFF_DIR / 'playoff_games.csv',
    'playoff_appearances': PLAYOFF_DIR / 'playoff_appearances.csv',
    'player_pedigree': PLAYOFF_DIR / 'player_championship_pedigree.csv',
    'weekly_lineups': PLAYER_WEEK_DIR / 'all_weekly_lineups_2017_2025.csv',
    'luck_team_week': ANALYSIS_DIR / 'luck_team_week.csv',
    'luck_season': ANALYSIS_DIR / 'luck_season.csv',
    'efficiency_season': ANALYSIS_DIR / 'lineup_efficiency_season.csv',
}

st.markdown('''
<style>
.block-container{max-width:1500px;padding-top:1.5rem;padding-bottom:3rem}
.records-hero{padding:1.6rem 1.8rem;border-radius:18px;background:linear-gradient(135deg,rgba(30,41,59,.98),rgba(15,23,42,.98));color:white;margin-bottom:1.2rem}
.records-hero h1{margin:0;font-size:2.25rem;font-weight:800}
.records-hero p{margin:.4rem 0 0 0;color:#cbd5e1}
div[data-testid="stMetric"]{background:rgba(148,163,184,.08);border:1px solid rgba(148,163,184,.18);padding:.85rem;border-radius:14px}
</style>
''', unsafe_allow_html=True)

@st.cache_data
def load_data():
    out = {}
    for name, path in FILES.items():
        try:
            out[name] = pd.read_csv(path) if path.exists() else pd.DataFrame()
        except Exception:
            out[name] = pd.DataFrame()
    return out

data = load_data()
team_games = data['team_games'].copy()
season_records = data['season_records'].copy()
all_time = data['all_time_records'].copy()
championships = data['championships'].copy()
playoff_records = data['playoff_records'].copy()
playoff_games = data['playoff_games'].copy()
playoff_appearances = data['playoff_appearances'].copy()
player_pedigree = data['player_pedigree'].copy()
weekly_lineups = data['weekly_lineups'].copy()
luck_team_week = data['luck_team_week'].copy()
luck_season = data['luck_season'].copy()
efficiency_season = data['efficiency_season'].copy()

def numeric(df, cols):
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

numeric(team_games, ['year','week','points_for','points_against','margin'])
numeric(season_records, ['year','wins','losses','ties','win_pct','points_for','points_against','point_diff'])
numeric(all_time, ['wins','losses','ties','win_pct','points_for','points_against','point_diff','games','seasons'])
numeric(weekly_lineups, ['year','week','fantasy_points'])

def team_col(df):
    for col in ['team','fantasy_team','franchise']:
        if col in df.columns:
            return col
    return None


# ============================================================
# FRANCHISE IDENTITY NORMALIZATION
# ============================================================

FRANCHISE_ALIASES = {
    "PickUpYourBratsMalle": "ThreatLevelMidnight",
    "You Better Park It": "Buttermilk Puuump",
    "Buttermilk Pump": "Buttermilk Puuump",
}


def normalize_franchise_name(value):
    if pd.isna(value):
        return value

    name = str(value).strip()
    return FRANCHISE_ALIASES.get(name, name)


def normalize_franchise_columns(df):
    """
    Normalize historical team-name aliases before any career/record math.
    This prevents one franchise from being split across multiple names.
    """
    if df is None or df.empty:
        return df

    out = df.copy()

    franchise_columns = [
        "team",
        "fantasy_team",
        "franchise",
        "opponent",
        "team_1",
        "team_2",
        "left_team",
        "right_team",
        "team_a",
        "team_b",
        "champion",
        "runner_up",
        "winner",
        "loser",
    ]

    for col in franchise_columns:
        if col in out.columns:
            out[col] = out[col].map(
                normalize_franchise_name
            )

    return out


# Normalize every franchise-bearing dataset before record calculations.
team_games = normalize_franchise_columns(team_games)
season_records = normalize_franchise_columns(season_records)
all_time = normalize_franchise_columns(all_time)
championships = normalize_franchise_columns(championships)
playoff_records = normalize_franchise_columns(playoff_records)
playoff_games = normalize_franchise_columns(playoff_games)
playoff_appearances = normalize_franchise_columns(playoff_appearances)
player_pedigree = normalize_franchise_columns(player_pedigree)
weekly_lineups = normalize_franchise_columns(weekly_lineups)
luck_team_week = normalize_franchise_columns(luck_team_week)
luck_season = normalize_franchise_columns(luck_season)
efficiency_season = normalize_franchise_columns(efficiency_season)

def top_table(df, sort_col, ascending=False, columns=None, rename=None, n=10):
    if df.empty or sort_col not in df.columns:
        st.info('No data available.')
        return
    work = df.sort_values(sort_col, ascending=ascending).head(n).copy()
    work.insert(0, 'Rank', range(1, len(work)+1))
    if columns:
        work = work[['Rank'] + [c for c in columns if c in work.columns]]
    if rename:
        work = work.rename(columns=rename)
    st.dataframe(work, hide_index=True, use_container_width=True)

st.markdown('''
<div class="records-hero">
<h1>🏅 League Record Book</h1>
<p>The best, worst, longest, biggest, smallest, and most ridiculous performances in league history.</p>
</div>
''', unsafe_allow_html=True)

st.caption('Regular-season team and matchup records come from clean historical game data. Roster records use validated weekly player data where available.')

(tab_league, tab_season, tab_matchup, tab_roster, tab_streaks, tab_milestones) = st.tabs([
    '🏛️ League','📅 Season','⚔️ Matchup','🧍 Roster','🔥 Streaks','🎯 Milestones'
])

# ============================================================
# LEAGUE
# ============================================================
with tab_league:
    st.header("🏛️ League Records")
    st.caption(
        "Choose a league-history record. Career totals track who has owned the "
        "record over time; single-game records track each time a new benchmark was set."
    )

    # ------------------------------------------------------------
    # DATA NORMALIZATION
    # ------------------------------------------------------------

    regular = team_games.copy()

    if not regular.empty:
        numeric(
            regular,
            [
                "year",
                "week",
                "points_for",
                "points_against",
                "margin",
            ],
        )

        if "margin" not in regular.columns:
            regular["margin"] = (
                regular["points_for"]
                - regular["points_against"]
            )

        regular["win_add"] = (
            regular["result"].eq("W").astype(int)
        )
        regular["loss_add"] = (
            regular["result"].eq("L").astype(int)
        )

    if not luck_team_week.empty:
        numeric(
            luck_team_week,
            [
                "year",
                "week",
                "all_play_wins",
                "all_play_losses",
            ],
        )

    if not playoff_games.empty:
        numeric(
            playoff_games,
            [
                "year",
                "week",
                "points_for",
                "points_against",
                "team_score",
                "opponent_score",
                "score",
            ],
        )

    if not playoff_appearances.empty:
        numeric(
            playoff_appearances,
            ["year"],
        )

    if not championships.empty:
        numeric(
            championships,
            ["year"],
        )


    # ------------------------------------------------------------
    # GENERIC HELPERS
    # ------------------------------------------------------------

    def find_first_col(
        df,
        candidates,
    ):
        for col in candidates:
            if col in df.columns:
                return col
        return None


    def league_period_label(
        year,
        week=None,
    ):
        if week is None or pd.isna(week):
            return str(int(year))

        return (
            f"{int(year)} Week {int(week)}"
        )


    def cumulative_record_from_events(
        events,
        *,
        team_field,
        value_field,
        year_field="year",
        week_field="week",
    ):
        """
        Build cumulative leader standings and reign history from event rows.

        Each event row contributes value_field to one franchise.  Events may be
        weekly (year/week) or yearly (year only).
        """
        if events.empty:
            return None

        work = events.copy()

        work[team_field] = (
            work[team_field]
            .astype(str)
            .str.strip()
        )

        work[value_field] = pd.to_numeric(
            work[value_field],
            errors="coerce",
        ).fillna(0)

        work[year_field] = pd.to_numeric(
            work[year_field],
            errors="coerce",
        )

        has_week = (
            week_field in work.columns
            and work[week_field].notna().any()
        )

        if has_week:
            work[week_field] = pd.to_numeric(
                work[week_field],
                errors="coerce",
            )

            work = work.dropna(
                subset=[
                    team_field,
                    year_field,
                    week_field,
                ]
            )

            period_cols = [
                year_field,
                week_field,
            ]
        else:
            work = work.dropna(
                subset=[
                    team_field,
                    year_field,
                ]
            )

            period_cols = [
                year_field,
            ]

        grouped = (
            work.groupby(
                period_cols + [team_field],
                as_index=False,
            )[value_field]
            .sum()
            .rename(
                columns={
                    value_field:
                        "value_add",
                    team_field:
                        "team",
                    year_field:
                        "year",
                }
            )
        )

        if has_week:
            grouped = grouped.rename(
                columns={
                    week_field:
                        "week",
                }
            )
        else:
            grouped["week"] = np.nan

        periods = (
            grouped[
                [
                    "year",
                    "week",
                ]
            ]
            .drop_duplicates()
            .sort_values(
                [
                    "year",
                    "week",
                ],
                na_position="last",
            )
            .reset_index(
                drop=True
            )
        )

        periods[
            "period_index"
        ] = range(
            len(periods)
        )

        teams = sorted(
            grouped[
                "team"
            ]
            .dropna()
            .astype(str)
            .unique()
        )

        grid = (
            periods.assign(
                _key=1
            )
            .merge(
                pd.DataFrame(
                    {
                        "team": teams,
                        "_key": 1,
                    }
                ),
                on="_key",
            )
            .drop(
                columns="_key"
            )
            .merge(
                grouped[
                    [
                        "year",
                        "week",
                        "team",
                        "value_add",
                    ]
                ],
                on=[
                    "year",
                    "week",
                    "team",
                ],
                how="left",
            )
            .sort_values(
                [
                    "team",
                    "period_index",
                ]
            )
        )

        grid[
            "value_add"
        ] = (
            grid[
                "value_add"
            ]
            .fillna(0)
        )

        grid[
            "career_value"
        ] = (
            grid.groupby(
                "team"
            )[
                "value_add"
            ]
            .cumsum()
        )

        snapshots = []

        for period_index, group in grid.groupby(
            "period_index",
            sort=True,
        ):
            max_value = (
                group[
                    "career_value"
                ]
                .max()
            )

            leaders = tuple(
                sorted(
                    group.loc[
                        np.isclose(
                            group[
                                "career_value"
                            ],
                            max_value,
                        ),
                        "team",
                    ]
                    .astype(str)
                    .tolist()
                )
            )

            first = group.iloc[0]

            snapshots.append(
                {
                    "period_index":
                        int(
                            period_index
                        ),
                    "year":
                        int(
                            first[
                                "year"
                            ]
                        ),
                    "week":
                        (
                            float(
                                first[
                                    "week"
                                ]
                            )
                            if pd.notna(
                                first[
                                    "week"
                                ]
                            )
                            else np.nan
                        ),
                    "leaders":
                        leaders,
                    "record_value":
                        float(
                            max_value
                        ),
                }
            )

        snapshots = pd.DataFrame(
            snapshots
        )

        reign_rows = []
        reign_start = 0

        for i in range(
            1,
            len(snapshots) + 1,
        ):
            changed = (
                i == len(snapshots)
                or snapshots.iloc[
                    i
                ]["leaders"]
                != snapshots.iloc[
                    reign_start
                ]["leaders"]
            )

            if changed:
                first = snapshots.iloc[
                    reign_start
                ]

                last = snapshots.iloc[
                    i - 1
                ]

                reign_rows.append(
                    {
                        "holders":
                            first[
                                "leaders"
                            ],
                        "start_year":
                            int(
                                first[
                                    "year"
                                ]
                            ),
                        "start_week":
                            first[
                                "week"
                            ],
                        "end_year":
                            int(
                                last[
                                    "year"
                                ]
                            ),
                        "end_week":
                            last[
                                "week"
                            ],
                        "weeks":
                            int(
                                last[
                                    "period_index"
                                ]
                                - first[
                                    "period_index"
                                ]
                                + 1
                            ),
                        "record_value":
                            float(
                                last[
                                    "record_value"
                                ]
                            ),
                        "is_current":
                            i
                            == len(
                                snapshots
                            ),
                    }
                )

                reign_start = i

        reigns = pd.DataFrame(
            reign_rows
        )

        latest = snapshots.iloc[-1]

        latest_grid = (
            grid[
                grid[
                    "period_index"
                ]
                == int(
                    latest[
                        "period_index"
                    ]
                )
            ]
            .copy()
        )

        latest_grid[
            "Rank"
        ] = (
            latest_grid[
                "career_value"
            ]
            .rank(
                method="min",
                ascending=False,
            )
            .astype(int)
        )

        standings = (
            latest_grid[
                [
                    "Rank",
                    "team",
                    "career_value",
                ]
            ]
            .sort_values(
                [
                    "career_value",
                    "team",
                ],
                ascending=[
                    False,
                    True,
                ],
            )
            .reset_index(
                drop=True
            )
        )

        all_holders = set()

        time_on_top = {}

        reign_count = {}

        for _, reign in reigns.iterrows():
            for holder in reign[
                "holders"
            ]:
                all_holders.add(
                    holder
                )

                time_on_top[
                    holder
                ] = (
                    time_on_top.get(
                        holder,
                        0,
                    )
                    + int(
                        reign[
                            "weeks"
                        ]
                    )
                )

                reign_count[
                    holder
                ] = (
                    reign_count.get(
                        holder,
                        0,
                    )
                    + 1
                )

        longest_reign = (
            reigns
            .sort_values(
                "weeks",
                ascending=False,
            )
            .iloc[0]
        )

        most_time_team = max(
            time_on_top,
            key=time_on_top.get,
        )

        return {
            "standings":
                standings,
            "reigns":
                reigns,
            "current_holders":
                tuple(
                    latest[
                        "leaders"
                    ]
                ),
            "current_value":
                float(
                    latest[
                        "record_value"
                    ]
                ),
            "current_reign":
                reigns.iloc[-1],
            "changed_hands":
                max(
                    len(reigns) - 1,
                    0,
                ),
            "all_time_holders":
                len(
                    all_holders
                ),
            "longest_reign":
                longest_reign,
            "most_time_team":
                most_time_team,
            "most_time_weeks":
                int(
                    time_on_top[
                        most_time_team
                    ]
                ),
            "most_time_reigns":
                int(
                    reign_count[
                        most_time_team
                    ]
                ),
        }


    def single_game_record(
        events,
        *,
        value_col,
        ascending=False,
        filter_mask=None,
    ):
        """
        Current single-game record plus leaderboard and chronological record
        progression.  A new timeline event is created only when the benchmark
        is beaten (or tied).
        """
        if events.empty:
            return None

        work = events.copy()

        if filter_mask is not None:
            work = work[
                filter_mask(
                    work
                )
            ].copy()

        work[value_col] = pd.to_numeric(
            work[value_col],
            errors="coerce",
        )

        work = work.dropna(
            subset=[
                "year",
                "week",
                "team",
                value_col,
            ]
        ).copy()

        work = work.sort_values(
            [
                "year",
                "week",
            ]
        )

        if work.empty:
            return None

        best_value = (
            work[
                value_col
            ]
            .min()
            if ascending
            else work[
                value_col
            ]
            .max()
        )

        holders = work[
            np.isclose(
                work[
                    value_col
                ],
                best_value,
            )
        ].copy()

        leaderboard = work.sort_values(
            value_col,
            ascending=ascending,
        ).head(25)

        progression = []
        standing_record = None

        for _, row in work.iterrows():
            value = float(
                row[
                    value_col
                ]
            )

            is_new = (
                standing_record is None
                or (
                    value
                    < standing_record
                    - 1e-9
                    if ascending
                    else value
                    > standing_record
                    + 1e-9
                )
            )

            is_tie = (
                standing_record is not None
                and np.isclose(
                    value,
                    standing_record,
                )
            )

            if is_new:
                standing_record = value

                progression.append(
                    {
                        "year":
                            int(
                                row[
                                    "year"
                                ]
                            ),
                        "week":
                            int(
                                row[
                                    "week"
                                ]
                            ),
                        "team":
                            row[
                                "team"
                            ],
                        "opponent":
                            row.get(
                                "opponent",
                                "",
                            ),
                        "value":
                            value,
                        "type":
                            "New Record",
                    }
                )

            elif is_tie:
                progression.append(
                    {
                        "year":
                            int(
                                row[
                                    "year"
                                ]
                            ),
                        "week":
                            int(
                                row[
                                    "week"
                                ]
                            ),
                        "team":
                            row[
                                "team"
                            ],
                        "opponent":
                            row.get(
                                "opponent",
                                "",
                            ),
                        "value":
                            value,
                        "type":
                            "Tied Record",
                    }
                )

        return {
            "value":
                float(
                    best_value
                ),
            "holders":
                holders,
            "leaderboard":
                leaderboard,
            "progression":
                pd.DataFrame(
                    progression
                ),
        }


    def render_cumulative_profile(
        record,
        *,
        title,
        label,
        description,
        value_format,
        duration_unit="week",
    ):
        current_reign = (
            record[
                "current_reign"
            ]
        )

        holder_text = (
            " & ".join(
                record[
                    "current_holders"
                ]
            )
        )

        start_label = (
            league_period_label(
                current_reign[
                    "start_year"
                ],
                current_reign[
                    "start_week"
                ],
            )
        )

        m1, m2, m3, m4 = st.columns(
            4
        )

        m1.metric(
            "👑 Current Reign",
            (
                f"{int(current_reign['weeks'])} "
                f"{duration_unit}"
                + (
                    "s"
                    if int(
                        current_reign[
                            "weeks"
                        ]
                    ) != 1
                    else ""
                )
            ),
            holder_text,
        )

        m1.caption(
            f"Since {start_label}"
        )

        m2.metric(
            "🤝 Changed Hands",
            (
                f"{record['changed_hands']} "
                "time"
                + (
                    "s"
                    if record[
                        "changed_hands"
                    ] != 1
                    else ""
                )
            ),
            (
                f"{record['all_time_holders']} "
                "all-time holders"
            ),
        )

        longest = (
            record[
                "longest_reign"
            ]
        )

        m3.metric(
            "🏆 Longest Reign",
            (
                f"{int(longest['weeks'])} "
                f"{duration_unit}"
                + (
                    "s"
                    if int(
                        longest[
                            "weeks"
                        ]
                    ) != 1
                    else ""
                )
            ),
            (
                " & ".join(
                    longest[
                        "holders"
                    ]
                )
            ),
        )

        m4.metric(
            "⭐ Most Time on Top",
            (
                f"{record['most_time_weeks']} "
                f"{duration_unit}"
                + (
                    "s"
                    if record[
                        "most_time_weeks"
                    ] != 1
                    else ""
                )
            ),
            record[
                "most_time_team"
            ],
        )

        st.markdown(
            (
                "<div style='text-align:center;padding:1rem 0 1.2rem 0;'>"
                f"<div style='font-size:4.5rem;font-weight:900;line-height:.95;'>"
                f"{value_format(record['current_value'])}</div>"
                f"<div style='font-size:1.4rem;font-weight:800;opacity:.62;"
                f"letter-spacing:.08em;margin-top:.35rem;'>{label}</div>"
                f"<div style='font-size:1.1rem;font-weight:750;margin-top:.75rem;'>"
                f"👑 {holder_text}</div>"
                f"<div style='opacity:.65;margin-top:.2rem;'>"
                f"Record held {start_label} – Present</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

        st.caption(
            description
        )

        left, right = st.columns(
            [
                1.20,
                .80,
            ],
            gap="large",
        )

        with left:
            st.subheader(
                "Current Record Standings"
            )

            standings = (
                record[
                    "standings"
                ]
                .copy()
                .rename(
                    columns={
                        "team":
                            "Franchise",
                        "career_value":
                            "Actual",
                    }
                )
            )

            standings[
                "Franchise"
            ] = standings[
                "Franchise"
            ].apply(
                lambda team:
                    (
                        f"🏆 {team}"
                        if team
                        in record[
                            "current_holders"
                        ]
                        else team
                    )
            )

            standings[
                "Actual"
            ] = standings[
                "Actual"
            ].apply(
                lambda x:
                    value_format(
                        float(x)
                    )
            )

            st.dataframe(
                standings[
                    [
                        "Rank",
                        "Franchise",
                        "Actual",
                    ]
                ],
                hide_index=True,
                use_container_width=True,
                height=520,
                column_config={
                    "Rank":
                        st.column_config.NumberColumn(
                            "Rank",
                            format="#%d",
                            width="small",
                        ),
                    "Franchise":
                        st.column_config.TextColumn(
                            "Franchise",
                            width="large",
                        ),
                    "Actual":
                        st.column_config.TextColumn(
                            label.title(),
                            width="medium",
                        ),
                },
            )

        with right:
            st.subheader(
                "Record Holder Timeline"
            )

            st.caption(
                "Each row is one uninterrupted reign at the top."
            )

            reigns = (
                record[
                    "reigns"
                ]
                .iloc[::-1]
                .reset_index(
                    drop=True
                )
            )

            for i, reign in reigns.iterrows():
                holders = (
                    " & ".join(
                        reign[
                            "holders"
                        ]
                    )
                )

                begin = (
                    league_period_label(
                        reign[
                            "start_year"
                        ],
                        reign[
                            "start_week"
                        ],
                    )
                )

                end = (
                    "Present"
                    if bool(
                        reign[
                            "is_current"
                        ]
                    )
                    else league_period_label(
                        reign[
                            "end_year"
                        ],
                        reign[
                            "end_week"
                        ],
                    )
                )

                duration = int(
                    reign[
                        "weeks"
                    ]
                )

                c1, c2, c3 = st.columns(
                    [
                        .10,
                        .68,
                        .22,
                    ],
                    vertical_alignment="top",
                )

                c1.markdown(
                    "### 🏆"
                    if i == 0
                    else "### 🔵"
                )

                c2.markdown(
                    f"**{holders}**"
                )

                c2.caption(
                    (
                        f"{begin} – {end}\n\n"
                        f"{duration} "
                        f"{duration_unit}"
                        + (
                            "s"
                            if duration != 1
                            else ""
                        )
                    )
                )

                c3.markdown(
                    (
                        "<div style='text-align:right;font-size:1.1rem;"
                        "font-weight:800;padding-top:.15rem;'>"
                        f"{value_format(float(reign['record_value']))}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

                if i < len(
                    reigns
                ) - 1:
                    st.divider()


    def render_single_game_profile(
        result,
        *,
        title,
        label,
        description,
        value_format,
    ):
        holders = result[
            "holders"
        ].sort_values(
            [
                "year",
                "week",
            ]
        )

        current = (
            holders.iloc[-1]
        )

        st.markdown(
            (
                "<div style='text-align:center;padding:1rem 0 1.2rem 0;'>"
                f"<div style='font-size:4.5rem;font-weight:900;line-height:.95;'>"
                f"{value_format(result['value'])}</div>"
                f"<div style='font-size:1.4rem;font-weight:800;opacity:.62;"
                f"letter-spacing:.08em;margin-top:.35rem;'>{label}</div>"
                f"<div style='font-size:1.1rem;font-weight:750;margin-top:.75rem;'>"
                f"🏆 {current['team']}</div>"
                f"<div style='opacity:.65;margin-top:.2rem;'>"
                f"{int(current['year'])} Week {int(current['week'])}"
                + (
                    f" vs {current['opponent']}"
                    if "opponent" in current.index
                    else ""
                )
                + "</div></div>"
            ),
            unsafe_allow_html=True,
        )

        st.caption(
            description
        )

        left, right = st.columns(
            [
                1.20,
                .80,
            ],
            gap="large",
        )

        with left:
            st.subheader(
                "Current Record Standings"
            )

            board = (
                result[
                    "leaderboard"
                ]
                .copy()
            )

            board[
                "Rank"
            ] = range(
                1,
                len(board) + 1,
            )

            display = pd.DataFrame(
                {
                    "Rank":
                        board[
                            "Rank"
                        ],
                    "Franchise":
                        board[
                            "team"
                        ],
                    "Actual":
                        board[
                            board.columns[
                                board.columns.get_loc(
                                    "RecordValue"
                                )
                            ]
                        ]
                        if "RecordValue"
                        in board.columns
                        else np.nan,
                }
            )

            # The caller stores the ranking metric in `_display_value`.
            display[
                "Actual"
            ] = board[
                "_display_value"
            ].apply(
                lambda x:
                    value_format(
                        float(x)
                    )
            )

            display[
                "Franchise"
            ] = np.where(
                np.isclose(
                    board[
                        "_display_value"
                    ],
                    result[
                        "value"
                    ],
                ),
                "🏆 "
                + board[
                    "team"
                ].astype(str),
                board[
                    "team"
                ].astype(str),
            )

            st.dataframe(
                display,
                hide_index=True,
                use_container_width=True,
                height=520,
                column_config={
                    "Rank":
                        st.column_config.NumberColumn(
                            "Rank",
                            format="#%d",
                            width="small",
                        ),
                    "Franchise":
                        st.column_config.TextColumn(
                            "Franchise",
                            width="large",
                        ),
                    "Actual":
                        st.column_config.TextColumn(
                            label.title(),
                            width="medium",
                        ),
                },
            )

        with right:
            st.subheader(
                "Record Progression"
            )

            prog = (
                result[
                    "progression"
                ]
                .iloc[::-1]
                .reset_index(
                    drop=True
                )
            )

            for i, row in prog.iterrows():
                c1, c2, c3 = st.columns(
                    [
                        .10,
                        .68,
                        .22,
                    ],
                    vertical_alignment="top",
                )

                c1.markdown(
                    "### 🏆"
                    if i == 0
                    else "### 🔵"
                )

                c2.markdown(
                    f"**{row['team']}**"
                )

                c2.caption(
                    (
                        f"{int(row['year'])} Week {int(row['week'])}"
                        + (
                            f" vs {row['opponent']}"
                            if row[
                                "opponent"
                            ]
                            else ""
                        )
                        + f"\n\n{row['type']}"
                    )
                )

                c3.markdown(
                    (
                        "<div style='text-align:right;font-size:1.1rem;"
                        "font-weight:800;padding-top:.15rem;'>"
                        f"{value_format(float(row['value']))}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

                if i < len(
                    prog
                ) - 1:
                    st.divider()



    def build_running_metric_record(
        source,
        *,
        team_field,
        value_field,
        aggregation="sum",
        high_is_record=True,
    ):
        """
        Build a historical record profile for a running SUM or running MEAN.

        Used for league-wide luck and strength-of-schedule records:
          - Luckiest: cumulative schedule luck, highest is record
          - Least Lucky: cumulative schedule luck, lowest is record
          - Hardest SOS: running average opponent score, highest is record
          - Easiest SOS: running average opponent score, lowest is record
        """
        if source.empty:
            return None

        work = source.copy()

        required = {
            "year",
            "week",
            team_field,
            value_field,
        }

        if not required.issubset(
            set(work.columns)
        ):
            return None

        work["year"] = pd.to_numeric(
            work["year"],
            errors="coerce",
        )

        work["week"] = pd.to_numeric(
            work["week"],
            errors="coerce",
        )

        work[value_field] = pd.to_numeric(
            work[value_field],
            errors="coerce",
        )

        work = work.dropna(
            subset=[
                "year",
                "week",
                team_field,
                value_field,
            ]
        ).copy()

        if work.empty:
            return None

        work["year"] = (
            work["year"]
            .astype(int)
        )

        work["week"] = (
            work["week"]
            .astype(int)
        )

        work["team"] = (
            work[team_field]
            .astype(str)
            .str.strip()
        )

        # One contribution per team/week.
        weekly = (
            work.groupby(
                [
                    "year",
                    "week",
                    "team",
                ],
                as_index=False,
            )[value_field]
            .mean()
            .rename(
                columns={
                    value_field:
                        "metric_value",
                }
            )
        )

        periods = (
            weekly[
                [
                    "year",
                    "week",
                ]
            ]
            .drop_duplicates()
            .sort_values(
                [
                    "year",
                    "week",
                ]
            )
            .reset_index(
                drop=True
            )
        )

        periods[
            "period_index"
        ] = range(
            len(periods)
        )

        teams = sorted(
            weekly[
                "team"
            ]
            .unique()
        )

        grid = (
            periods.assign(
                _key=1
            )
            .merge(
                pd.DataFrame(
                    {
                        "team":
                            teams,
                        "_key":
                            1,
                    }
                ),
                on="_key",
            )
            .drop(
                columns="_key"
            )
            .merge(
                weekly,
                on=[
                    "year",
                    "week",
                    "team",
                ],
                how="left",
            )
            .sort_values(
                [
                    "team",
                    "period_index",
                ]
            )
        )

        # Missing means the team had no contribution that period. For this
        # league-history dataset all active franchises should have a row, but
        # forward-compatible handling avoids corrupting historical averages.
        if aggregation == "sum":
            grid[
                "metric_value"
            ] = (
                grid[
                    "metric_value"
                ]
                .fillna(0.0)
            )

            grid[
                "career_value"
            ] = (
                grid.groupby(
                    "team"
                )[
                    "metric_value"
                ]
                .cumsum()
            )

        elif aggregation == "mean":
            grid[
                "_value_present"
            ] = (
                grid[
                    "metric_value"
                ]
                .notna()
                .astype(int)
            )

            grid[
                "_value_for_sum"
            ] = (
                grid[
                    "metric_value"
                ]
                .fillna(0.0)
            )

            grid[
                "_cum_sum"
            ] = (
                grid.groupby(
                    "team"
                )[
                    "_value_for_sum"
                ]
                .cumsum()
            )

            grid[
                "_cum_count"
            ] = (
                grid.groupby(
                    "team"
                )[
                    "_value_present"
                ]
                .cumsum()
            )

            grid[
                "career_value"
            ] = np.where(
                grid[
                    "_cum_count"
                ] > 0,
                grid[
                    "_cum_sum"
                ]
                / grid[
                    "_cum_count"
                ],
                np.nan,
            )

        else:
            raise ValueError(
                "aggregation must be 'sum' or 'mean'"
            )

        snapshots = []

        for period_index, group in grid.groupby(
            "period_index",
            sort=True,
        ):
            eligible = group.dropna(
                subset=[
                    "career_value",
                ]
            )

            if eligible.empty:
                continue

            record_value = (
                eligible[
                    "career_value"
                ]
                .max()
                if high_is_record
                else eligible[
                    "career_value"
                ]
                .min()
            )

            leaders = tuple(
                sorted(
                    eligible.loc[
                        np.isclose(
                            eligible[
                                "career_value"
                            ],
                            record_value,
                        ),
                        "team",
                    ]
                    .astype(str)
                    .tolist()
                )
            )

            first = eligible.iloc[
                0
            ]

            snapshots.append(
                {
                    "period_index":
                        int(
                            period_index
                        ),
                    "year":
                        int(
                            first[
                                "year"
                            ]
                        ),
                    "week":
                        int(
                            first[
                                "week"
                            ]
                        ),
                    "leaders":
                        leaders,
                    "record_value":
                        float(
                            record_value
                        ),
                }
            )

        snapshots = pd.DataFrame(
            snapshots
        )

        if snapshots.empty:
            return None

        reign_rows = []
        reign_start = 0

        for i in range(
            1,
            len(snapshots) + 1,
        ):
            changed = (
                i
                == len(
                    snapshots
                )
                or snapshots.iloc[
                    i
                ][
                    "leaders"
                ]
                != snapshots.iloc[
                    reign_start
                ][
                    "leaders"
                ]
            )

            if changed:
                first = snapshots.iloc[
                    reign_start
                ]

                last = snapshots.iloc[
                    i - 1
                ]

                reign_rows.append(
                    {
                        "holders":
                            first[
                                "leaders"
                            ],
                        "start_year":
                            int(
                                first[
                                    "year"
                                ]
                            ),
                        "start_week":
                            int(
                                first[
                                    "week"
                                ]
                            ),
                        "end_year":
                            int(
                                last[
                                    "year"
                                ]
                            ),
                        "end_week":
                            int(
                                last[
                                    "week"
                                ]
                            ),
                        "weeks":
                            int(
                                last[
                                    "period_index"
                                ]
                                - first[
                                    "period_index"
                                ]
                                + 1
                            ),
                        "record_value":
                            float(
                                last[
                                    "record_value"
                                ]
                            ),
                        "is_current":
                            i
                            == len(
                                snapshots
                            ),
                    }
                )

                reign_start = i

        reigns = pd.DataFrame(
            reign_rows
        )

        latest = snapshots.iloc[
            -1
        ]

        latest_grid = (
            grid[
                grid[
                    "period_index"
                ]
                == int(
                    latest[
                        "period_index"
                    ]
                )
            ]
            .dropna(
                subset=[
                    "career_value",
                ]
            )
            .copy()
        )

        latest_grid[
            "Rank"
        ] = (
            latest_grid[
                "career_value"
            ]
            .rank(
                method="min",
                ascending=(
                    not high_is_record
                ),
            )
            .astype(int)
        )

        standings = (
            latest_grid[
                [
                    "Rank",
                    "team",
                    "career_value",
                ]
            ]
            .sort_values(
                [
                    "career_value",
                    "team",
                ],
                ascending=[
                    not high_is_record,
                    True,
                ],
            )
            .reset_index(
                drop=True
            )
        )

        all_holders = set()
        time_on_top = {}
        reign_count = {}

        for _, reign in reigns.iterrows():
            for holder in reign[
                "holders"
            ]:
                all_holders.add(
                    holder
                )

                time_on_top[
                    holder
                ] = (
                    time_on_top.get(
                        holder,
                        0,
                    )
                    + int(
                        reign[
                            "weeks"
                        ]
                    )
                )

                reign_count[
                    holder
                ] = (
                    reign_count.get(
                        holder,
                        0,
                    )
                    + 1
                )

        longest_reign = (
            reigns
            .sort_values(
                "weeks",
                ascending=False,
            )
            .iloc[0]
        )

        most_time_team = max(
            time_on_top,
            key=time_on_top.get,
        )

        return {
            "standings":
                standings,
            "reigns":
                reigns,
            "current_holders":
                tuple(
                    latest[
                        "leaders"
                    ]
                ),
            "current_value":
                float(
                    latest[
                        "record_value"
                    ]
                ),
            "current_reign":
                reigns.iloc[-1],
            "changed_hands":
                max(
                    len(
                        reigns
                    )
                    - 1,
                    0,
                ),
            "all_time_holders":
                len(
                    all_holders
                ),
            "longest_reign":
                longest_reign,
            "most_time_team":
                most_time_team,
            "most_time_weeks":
                int(
                    time_on_top[
                        most_time_team
                    ]
                ),
            "most_time_reigns":
                int(
                    reign_count[
                        most_time_team
                    ]
                ),
        }


    # ------------------------------------------------------------
    # RECORD SELECTOR
    # ------------------------------------------------------------

    # ------------------------------------------------------------
    # COMPACT ALL-VISIBLE RECORD MENU
    # ------------------------------------------------------------

    record_groups = [
        (
            "Career",
            [
                "🏆 Total Wins",
                "💀 Total Losses",
                "📈 Total Points",
                "🛡️ Points Against",
                "🌐 All-Play Wins",
                "🌐 All-Play Losses",
            ],
        ),
        (
            "Single Game",
            [
                "🔥 Highest Single-Game Score",
                "🧊 Lowest Single-Game Score",
                "💥 Biggest Blowout Win",
                "🤏 Narrowest Win",
            ],
        ),
        (
            "Luck & Schedule",
            [
                "🍀 Luckiest",
                "☠️ Least Lucky",
                "🧱 Hardest Schedule",
                "🛋️ Easiest Schedule",
            ],
        ),
        (
            "Playoffs",
            [
                "🏟️ Playoff Wins",
                "🏟️ Playoff Losses",
                "🏟️ Playoff Points",
                "👑 Championships",
                "🎟️ Playoff Appearances",
            ],
        ),
    ]

    if "league_record_choice" not in st.session_state:
        st.session_state["league_record_choice"] = "🏆 Total Wins"

    short_labels = {
        "🏆 Total Wins": "🏆 Wins",
        "💀 Total Losses": "💀 Losses",
        "📈 Total Points": "📈 Points",
        "🛡️ Points Against": "🛡️ PA",
        "🌐 All-Play Wins": "🌐 AP Wins",
        "🌐 All-Play Losses": "🌐 AP Losses",
        "🔥 Highest Single-Game Score": "🔥 High Score",
        "🧊 Lowest Single-Game Score": "🧊 Low Score",
        "💥 Biggest Blowout Win": "💥 Blowout",
        "🤏 Narrowest Win": "🤏 Narrow Win",
        "🍀 Luckiest": "🍀 Luckiest",
        "☠️ Least Lucky": "☠️ Least Lucky",
        "🧱 Hardest Schedule": "🧱 Hardest SOS",
        "🛋️ Easiest Schedule": "🛋️ Easiest SOS",
        "🏟️ Playoff Wins": "🏟️ PO Wins",
        "🏟️ Playoff Losses": "🏟️ PO Losses",
        "🏟️ Playoff Points": "🏟️ PO Points",
        "👑 Championships": "👑 Titles",
        "🎟️ Playoff Appearances": "🎟️ Appearances",
    }

    def choose_league_record(record_name):
        st.session_state["league_record_choice"] = record_name

    for group_name, options in record_groups:
        label_col, *button_cols = st.columns(
            [0.72] + [1.0] * len(options),
            gap="small",
        )

        with label_col:
            st.markdown(
                f"<div style='padding-top:.45rem;"
                f"font-size:.78rem;font-weight:800;"
                f"opacity:.60;text-transform:uppercase;"
                f"letter-spacing:.06em;'>{group_name}</div>",
                unsafe_allow_html=True,
            )

        for col, option in zip(button_cols, options):
            with col:
                is_active = (
                    st.session_state["league_record_choice"]
                    == option
                )

                st.button(
                    (
                        f"● {short_labels[option]}"
                        if is_active
                        else short_labels[option]
                    ),
                    key=f"league_record_btn_{option}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                    on_click=choose_league_record,
                    args=(option,),
                )

    record_choice = st.session_state["league_record_choice"]

    st.divider()


    # ------------------------------------------------------------
    # REGULAR-SEASON CUMULATIVE RECORDS
    # ------------------------------------------------------------

    regular_configs = {
        "🏆 Total Wins": (
            "win_add",
            "WINS",
            "The franchise with the most regular-season victories in league history.",
            lambda x: f"{int(round(x)):,}",
        ),
        "💀 Total Losses": (
            "loss_add",
            "LOSSES",
            "The franchise with the most regular-season losses in league history.",
            lambda x: f"{int(round(x)):,}",
        ),
        "📈 Total Points": (
            "points_for",
            "POINTS",
            "The franchise with the most cumulative regular-season fantasy points.",
            lambda x: f"{x:,.2f}",
        ),
        "🛡️ Points Against": (
            "points_against",
            "POINTS AGAINST",
            "The franchise that has faced the most cumulative opponent scoring.",
            lambda x: f"{x:,.2f}",
        ),
    }

    if record_choice in regular_configs:
        value_col, label, description, fmt = (
            regular_configs[
                record_choice
            ]
        )

        events = regular[
            [
                "year",
                "week",
                "team",
                value_col,
            ]
        ].copy()

        record = cumulative_record_from_events(
            events,
            team_field="team",
            value_field=value_col,
        )

        render_cumulative_profile(
            record,
            title=record_choice,
            label=label,
            description=description,
            value_format=fmt,
        )


    # ------------------------------------------------------------
    # ALL-PLAY CUMULATIVE RECORDS
    # ------------------------------------------------------------

    elif record_choice in {
        "🌐 All-Play Wins",
        "🌐 All-Play Losses",
    }:
        if luck_team_week.empty:
            st.info(
                "All-play weekly data is missing. Run build_luck_metrics.py."
            )
        else:
            metric = (
                "all_play_wins"
                if record_choice
                == "🌐 All-Play Wins"
                else "all_play_losses"
            )

            events = luck_team_week[
                [
                    "year",
                    "week",
                    "fantasy_team",
                    metric,
                ]
            ].copy()

            record = cumulative_record_from_events(
                events,
                team_field="fantasy_team",
                value_field=metric,
            )

            render_cumulative_profile(
                record,
                title=record_choice,
                label=(
                    "ALL-PLAY WINS"
                    if metric
                    == "all_play_wins"
                    else "ALL-PLAY LOSSES"
                ),
                description=(
                    "Career all-play results compare each weekly score against "
                    "all 11 other franchises that week."
                ),
                value_format=lambda x:
                    f"{int(round(x)):,}",
            )


    # ------------------------------------------------------------
    # SINGLE-GAME RECORDS
    # ------------------------------------------------------------

    elif record_choice in {
        "🔥 Highest Single-Game Score",
        "🧊 Lowest Single-Game Score",
        "💥 Biggest Blowout Win",
        "🤏 Narrowest Win",
    }:
        if regular.empty:
            st.info(
                "Regular-season game history is missing."
            )
        else:
            single = regular.copy()

            if record_choice == "🔥 Highest Single-Game Score":
                value_col = "points_for"
                ascending = False
                filter_func = None
                label = "POINTS"
                description = (
                    "Highest score posted by one franchise in a single regular-season matchup."
                )
                fmt = lambda x: f"{x:.2f}"

            elif record_choice == "🧊 Lowest Single-Game Score":
                value_col = "points_for"
                ascending = True
                filter_func = None
                label = "POINTS"
                description = (
                    "Lowest score posted by one franchise in a single regular-season matchup."
                )
                fmt = lambda x: f"{x:.2f}"

            elif record_choice == "💥 Biggest Blowout Win":
                value_col = "margin"
                ascending = False
                filter_func = (
                    lambda df:
                        df[
                            "result"
                        ].eq("W")
                )
                label = "POINT MARGIN"
                description = (
                    "Largest regular-season margin of victory."
                )
                fmt = lambda x: f"+{x:.2f}"

            else:
                value_col = "margin"
                ascending = True
                filter_func = (
                    lambda df:
                        df[
                            "result"
                        ].eq("W")
                )
                label = "POINT MARGIN"
                description = (
                    "Smallest positive regular-season margin of victory."
                )
                fmt = lambda x: f"{x:.2f}"

            result = single_game_record(
                single,
                value_col=value_col,
                ascending=ascending,
                filter_mask=filter_func,
            )

            # Keep the actual ranking metric explicitly in the leaderboard.
            result[
                "leaderboard"
            ] = (
                result[
                    "leaderboard"
                ]
                .assign(
                    _display_value=lambda d:
                        d[
                            value_col
                        ]
                )
            )

            render_single_game_profile(
                result,
                title=record_choice,
                label=label,
                description=description,
                value_format=fmt,
            )


    # ------------------------------------------------------------
    # LUCK & STRENGTH OF SCHEDULE RECORDS
    # ------------------------------------------------------------

    elif record_choice in {
        "🍀 Luckiest",
        "☠️ Least Lucky",
        "🧱 Hardest Schedule",
        "🛋️ Easiest Schedule",
    }:
        if luck_team_week.empty:
            st.info(
                "Luck team-week data is missing. Run build_luck_metrics.py."
            )

        else:
            required_luck_cols = {
                "year",
                "week",
                "fantasy_team",
                "weekly_schedule_luck",
                "opponent_score",
            }

            missing_luck_cols = (
                required_luck_cols
                - set(
                    luck_team_week.columns
                )
            )

            if missing_luck_cols:
                st.error(
                    "Luck data is missing required columns: "
                    f"{sorted(missing_luck_cols)}"
                )

            else:
                if record_choice == "🍀 Luckiest":
                    record = build_running_metric_record(
                        luck_team_week,
                        team_field="fantasy_team",
                        value_field="weekly_schedule_luck",
                        aggregation="sum",
                        high_is_record=True,
                    )

                    label = "SCHEDULE LUCK WINS"
                    description = (
                        "Cumulative schedule luck. Positive values mean the "
                        "franchise has won more actual games than its weekly "
                        "all-play performance would predict."
                    )

                    fmt = (
                        lambda x:
                            f"{x:+.2f}"
                    )

                elif record_choice == "☠️ Least Lucky":
                    record = build_running_metric_record(
                        luck_team_week,
                        team_field="fantasy_team",
                        value_field="weekly_schedule_luck",
                        aggregation="sum",
                        high_is_record=False,
                    )

                    label = "SCHEDULE LUCK WINS"
                    description = (
                        "Lowest cumulative schedule luck. Negative values mean "
                        "the franchise has won fewer actual games than its weekly "
                        "all-play performance would predict."
                    )

                    fmt = (
                        lambda x:
                            f"{x:+.2f}"
                    )

                elif record_choice == "🧱 Hardest Schedule":
                    record = build_running_metric_record(
                        luck_team_week,
                        team_field="fantasy_team",
                        value_field="opponent_score",
                        aggregation="mean",
                        high_is_record=True,
                    )

                    label = "AVG OPPONENT SCORE"
                    description = (
                        "Career strength of schedule measured as the average "
                        "regular-season score posted by the franchise's opponents. "
                        "Higher means a harder schedule."
                    )

                    fmt = (
                        lambda x:
                            f"{x:.2f}"
                    )

                else:
                    record = build_running_metric_record(
                        luck_team_week,
                        team_field="fantasy_team",
                        value_field="opponent_score",
                        aggregation="mean",
                        high_is_record=False,
                    )

                    label = "AVG OPPONENT SCORE"
                    description = (
                        "Career strength of schedule measured as the average "
                        "regular-season score posted by the franchise's opponents. "
                        "Lower means an easier schedule."
                    )

                    fmt = (
                        lambda x:
                            f"{x:.2f}"
                    )

                if record is None:
                    st.info(
                        "No historical rows were available for this record."
                    )

                else:
                    render_cumulative_profile(
                        record,
                        title=record_choice,
                        label=label,
                        description=description,
                        value_format=fmt,
                    )


    # ------------------------------------------------------------
    # PLAYOFF GAME RECORDS
    # ------------------------------------------------------------

    elif record_choice in {
        "🏟️ Playoff Wins",
        "🏟️ Playoff Losses",
        "🏟️ Playoff Points",
    }:
        if playoff_games.empty:
            st.info(
                "Playoff game history is missing. Run build_playoff_history.py."
            )
        else:

            def normalize_playoff_games_to_team_rows(
                source,
            ):
                """
                Convert one-row-per-matchup playoff history into one row per team.

                Supports the historical schemas used across this project:
                  team_1 / team_1_score / team_2 / team_2_score
                  left_team / left_score / right_team / right_score
                  team_a / score_a / team_b / score_b
                  winner / winner_score / loser / loser_score
                """
                df = source.copy()

                # Find the matchup-side columns.
                schema_options = [
                    (
                        "team_1",
                        "team_1_score",
                        "team_2",
                        "team_2_score",
                    ),
                    (
                        "left_team",
                        "left_score",
                        "right_team",
                        "right_score",
                    ),
                    (
                        "team_a",
                        "score_a",
                        "team_b",
                        "score_b",
                    ),
                    (
                        "team1",
                        "team1_score",
                        "team2",
                        "team2_score",
                    ),
                    (
                        "winner",
                        "winner_score",
                        "loser",
                        "loser_score",
                    ),
                ]

                chosen = None

                for option in schema_options:
                    if all(
                        col in df.columns
                        for col in option
                    ):
                        chosen = option
                        break

                if chosen is None:
                    return (
                        pd.DataFrame(),
                        (
                            "Could not identify playoff matchup columns. "
                            f"Found columns: {list(df.columns)}"
                        ),
                    )

                t1_col, s1_col, t2_col, s2_col = (
                    chosen
                )

                # Determine an ordering field within each postseason.
                if "week" in df.columns:
                    playoff_period = pd.to_numeric(
                        df["week"],
                        errors="coerce",
                    )

                elif "playoff_week" in df.columns:
                    playoff_period = pd.to_numeric(
                        df["playoff_week"],
                        errors="coerce",
                    )

                elif "round" in df.columns:
                    # Round may be numeric or text such as "Semifinal".
                    numeric_round = pd.to_numeric(
                        df["round"],
                        errors="coerce",
                    )

                    if numeric_round.notna().any():
                        playoff_period = numeric_round
                    else:
                        # Preserve first-seen round order within each year.
                        playoff_period = (
                            df.groupby("year")["round"]
                            .transform(
                                lambda s:
                                    pd.factorize(
                                        s,
                                        sort=False,
                                    )[0]
                                    + 1
                            )
                        )

                elif "playoff_round" in df.columns:
                    numeric_round = pd.to_numeric(
                        df["playoff_round"],
                        errors="coerce",
                    )

                    if numeric_round.notna().any():
                        playoff_period = numeric_round
                    else:
                        playoff_period = (
                            df.groupby("year")["playoff_round"]
                            .transform(
                                lambda s:
                                    pd.factorize(
                                        s,
                                        sort=False,
                                    )[0]
                                    + 1
                            )
                        )

                else:
                    # Last-resort deterministic ordering.
                    playoff_period = (
                        df.groupby("year")
                        .cumcount()
                        + 1
                    )

                df["_playoff_period"] = (
                    pd.to_numeric(
                        playoff_period,
                        errors="coerce",
                    )
                )

                rows = []

                winner_loser_schema = (
                    t1_col == "winner"
                    and t2_col == "loser"
                )

                for _, row in df.iterrows():
                    try:
                        year = int(
                            float(
                                row["year"]
                            )
                        )
                    except Exception:
                        continue

                    team1 = str(
                        row[t1_col]
                    ).strip()

                    team2 = str(
                        row[t2_col]
                    ).strip()

                    if (
                        not team1
                        or not team2
                        or team1.lower() == "nan"
                        or team2.lower() == "nan"
                    ):
                        continue

                    score1 = pd.to_numeric(
                        pd.Series(
                            [row[s1_col]]
                        ),
                        errors="coerce",
                    ).iloc[0]

                    score2 = pd.to_numeric(
                        pd.Series(
                            [row[s2_col]]
                        ),
                        errors="coerce",
                    ).iloc[0]

                    if (
                        pd.isna(score1)
                        or pd.isna(score2)
                    ):
                        continue

                    period = row[
                        "_playoff_period"
                    ]

                    if pd.isna(period):
                        period = 1

                    period = int(
                        period
                    )

                    if winner_loser_schema:
                        result1 = "W"
                        result2 = "L"
                    else:
                        if score1 > score2:
                            result1 = "W"
                            result2 = "L"
                        elif score1 < score2:
                            result1 = "L"
                            result2 = "W"
                        else:
                            result1 = "T"
                            result2 = "T"

                    rows.extend(
                        [
                            {
                                "year":
                                    year,
                                "week":
                                    period,
                                "team":
                                    team1,
                                "opponent":
                                    team2,
                                "points_for":
                                    float(score1),
                                "points_against":
                                    float(score2),
                                "result":
                                    result1,
                            },
                            {
                                "year":
                                    year,
                                "week":
                                    period,
                                "team":
                                    team2,
                                "opponent":
                                    team1,
                                "points_for":
                                    float(score2),
                                "points_against":
                                    float(score1),
                                "result":
                                    result2,
                            },
                        ]
                    )

                normalized = pd.DataFrame(
                    rows
                )

                if normalized.empty:
                    return (
                        normalized,
                        (
                            "Playoff matchup columns were recognized, "
                            "but no valid matchup rows could be created."
                        ),
                    )

                # If multiple games share the same postseason period, that is fine:
                # cumulative_record_from_events groups by year/week/team.
                return normalized, None


            playoff_team_games, playoff_error = (
                normalize_playoff_games_to_team_rows(
                    playoff_games
                )
            )

            if playoff_error:
                st.error(
                    playoff_error
                )

            else:
                playoff_team_games[
                    "win_add"
                ] = (
                    playoff_team_games[
                        "result"
                    ]
                    .eq("W")
                    .astype(int)
                )

                playoff_team_games[
                    "loss_add"
                ] = (
                    playoff_team_games[
                        "result"
                    ]
                    .eq("L")
                    .astype(int)
                )

                playoff_configs = {
                    "🏟️ Playoff Wins": (
                        "win_add",
                        "PLAYOFF WINS",
                        (
                            "Career postseason victories from the "
                            "league's historical playoff game data."
                        ),
                        lambda x:
                            f"{int(round(x)):,}",
                    ),
                    "🏟️ Playoff Losses": (
                        "loss_add",
                        "PLAYOFF LOSSES",
                        (
                            "Career postseason losses from the "
                            "league's historical playoff game data."
                        ),
                        lambda x:
                            f"{int(round(x)):,}",
                    ),
                    "🏟️ Playoff Points": (
                        "points_for",
                        "PLAYOFF POINTS",
                        (
                            "Career fantasy points scored in postseason games."
                        ),
                        lambda x:
                            f"{x:,.2f}",
                    ),
                }

                (
                    value_col,
                    label,
                    description,
                    fmt,
                ) = playoff_configs[
                    record_choice
                ]

                events = playoff_team_games[
                    [
                        "year",
                        "week",
                        "team",
                        value_col,
                    ]
                ].copy()

                record = (
                    cumulative_record_from_events(
                        events,
                        team_field="team",
                        value_field=value_col,
                    )
                )

                if record is None:
                    st.info(
                        "No playoff record rows were available after normalization."
                    )
                else:
                    render_cumulative_profile(
                        record,
                        title=record_choice,
                        label=label,
                        description=description,
                        value_format=fmt,
                        duration_unit="playoff period",
                    )


    # ------------------------------------------------------------
    # CHAMPIONSHIPS
    # ------------------------------------------------------------

    elif record_choice == "👑 Championships":
        if championships.empty:
            st.info(
                "Championship history is missing."
            )
        else:
            champ_events = championships[
                [
                    "year",
                    "champion",
                ]
            ].copy()

            champ_events[
                "_value"
            ] = 1

            record = cumulative_record_from_events(
                champ_events,
                team_field="champion",
                value_field="_value",
            )

            render_cumulative_profile(
                record,
                title=record_choice,
                label="CHAMPIONSHIPS",
                description=(
                    "Career league championships won."
                ),
                value_format=lambda x:
                    f"{int(round(x)):,}",
                duration_unit="season",
            )


    # ------------------------------------------------------------
    # PLAYOFF APPEARANCES
    # ------------------------------------------------------------

    elif record_choice == "🎟️ Playoff Appearances":
        if playoff_appearances.empty:
            st.info(
                "Playoff appearance history is missing."
            )
        else:
            appearance_events = playoff_appearances[
                [
                    "year",
                    "team",
                ]
            ].drop_duplicates().copy()

            appearance_events[
                "_value"
            ] = 1

            record = cumulative_record_from_events(
                appearance_events,
                team_field="team",
                value_field="_value",
            )

            render_cumulative_profile(
                record,
                title=record_choice,
                label="PLAYOFF APPEARANCES",
                description=(
                    "Number of seasons in which the franchise appeared in the championship bracket."
                ),
                value_format=lambda x:
                    f"{int(round(x)):,}",
                duration_unit="season",
            )

# ============================================================
# SEASON
# ============================================================
with tab_season:
    st.header("📅 Season Records")
    st.caption(
        "Single-season records across league history. Each entry represents one "
        "franchise's performance in one season—not a career total."
    )

    if season_records.empty:
        st.info(
            "Season record data is not available. Run build_league_history.py."
        )
    else:
        season_work = normalize_franchise_columns(
            season_records.copy()
        )

        scol = team_col(
            season_work
        )

        if scol is None:
            st.error(
                "Could not identify the franchise column in season_records.csv."
            )
        else:
            numeric(
                season_work,
                [
                    "year",
                    "wins",
                    "losses",
                    "ties",
                    "points_for",
                    "points_against",
                    "win_pct",
                ],
            )

            # Bring in single-season all-play totals.
            if not luck_season.empty:
                luck_for_season = normalize_franchise_columns(
                    luck_season.copy()
                )

                numeric(
                    luck_for_season,
                    [
                        "year",
                        "all_play_wins",
                        "all_play_losses",
                    ],
                )

                if {
                    "year",
                    "fantasy_team",
                }.issubset(
                    luck_for_season.columns
                ):
                    keep_cols = [
                        "year",
                        "fantasy_team",
                    ]

                    for col in [
                        "all_play_wins",
                        "all_play_losses",
                    ]:
                        if col in luck_for_season.columns:
                            keep_cols.append(
                                col
                            )

                    luck_for_season = (
                        luck_for_season[
                            keep_cols
                        ]
                        .rename(
                            columns={
                                "fantasy_team":
                                    scol,
                            }
                        )
                    )

                    season_work = season_work.merge(
                        luck_for_season,
                        on=[
                            "year",
                            scol,
                        ],
                        how="left",
                    )

            # ------------------------------------------------------------
            # COMPACT RECORD MENU
            # ------------------------------------------------------------

            season_groups = [
                (
                    "Results",
                    [
                        "🏆 Most Wins",
                        "💀 Most Losses",
                    ],
                ),
                (
                    "Scoring",
                    [
                        "🔥 Most Points",
                        "🧊 Least Points",
                    ],
                ),
                (
                    "All-Play",
                    [
                        "🌐 Most All-Play Wins",
                        "🌐 Most All-Play Losses",
                    ],
                ),
            ]

            if "season_record_choice" not in st.session_state:
                st.session_state[
                    "season_record_choice"
                ] = "🏆 Most Wins"

            short_labels = {
                "🏆 Most Wins":
                    "🏆 Wins",
                "💀 Most Losses":
                    "💀 Losses",
                "🔥 Most Points":
                    "🔥 Points",
                "🧊 Least Points":
                    "🧊 Low Points",
                "🌐 Most All-Play Wins":
                    "🌐 AP Wins",
                "🌐 Most All-Play Losses":
                    "🌐 AP Losses",
            }

            def choose_season_record(
                record_name,
            ):
                st.session_state[
                    "season_record_choice"
                ] = record_name

            for group_name, options in season_groups:
                label_col, *button_cols = st.columns(
                    [0.72] + [1.0] * len(options),
                    gap="small",
                )

                with label_col:
                    st.markdown(
                        (
                            "<div style='padding-top:.45rem;"
                            "font-size:.78rem;font-weight:800;"
                            "opacity:.60;text-transform:uppercase;"
                            "letter-spacing:.06em;'>"
                            f"{group_name}</div>"
                        ),
                        unsafe_allow_html=True,
                    )

                for col, option in zip(
                    button_cols,
                    options,
                ):
                    with col:
                        active = (
                            st.session_state[
                                "season_record_choice"
                            ]
                            == option
                        )

                        st.button(
                            (
                                f"● {short_labels[option]}"
                                if active
                                else short_labels[
                                    option
                                ]
                            ),
                            key=(
                                "season_record_btn_"
                                + option
                            ),
                            use_container_width=True,
                            type=(
                                "primary"
                                if active
                                else "secondary"
                            ),
                            on_click=choose_season_record,
                            args=(option,),
                        )

            season_choice = st.session_state[
                "season_record_choice"
            ]

            st.divider()

            configs = {
                "🏆 Most Wins": {
                    "value_col":
                        "wins",
                    "ascending":
                        False,
                    "label":
                        "WINS",
                    "description":
                        "Most regular-season wins by one franchise in a single season.",
                    "format":
                        lambda x:
                            f"{int(round(x))}",
                },
                "💀 Most Losses": {
                    "value_col":
                        "losses",
                    "ascending":
                        False,
                    "label":
                        "LOSSES",
                    "description":
                        "Most regular-season losses by one franchise in a single season.",
                    "format":
                        lambda x:
                            f"{int(round(x))}",
                },
                "🔥 Most Points": {
                    "value_col":
                        "points_for",
                    "ascending":
                        False,
                    "label":
                        "POINTS",
                    "description":
                        "Most regular-season fantasy points scored by one franchise in a single season.",
                    "format":
                        lambda x:
                            f"{x:,.2f}",
                },
                "🧊 Least Points": {
                    "value_col":
                        "points_for",
                    "ascending":
                        True,
                    "label":
                        "POINTS",
                    "description":
                        "Fewest regular-season fantasy points scored by one franchise in a single season.",
                    "format":
                        lambda x:
                            f"{x:,.2f}",
                },
                "🌐 Most All-Play Wins": {
                    "value_col":
                        "all_play_wins",
                    "ascending":
                        False,
                    "label":
                        "ALL-PLAY WINS",
                    "description":
                        (
                            "Most all-play wins accumulated by one franchise in a "
                            "single season. Each weekly score is compared against "
                            "all 11 other teams."
                        ),
                    "format":
                        lambda x:
                            f"{int(round(x))}",
                },
                "🌐 Most All-Play Losses": {
                    "value_col":
                        "all_play_losses",
                    "ascending":
                        False,
                    "label":
                        "ALL-PLAY LOSSES",
                    "description":
                        "Most all-play losses accumulated by one franchise in a single season.",
                    "format":
                        lambda x:
                            f"{int(round(x))}",
                },
            }

            config = configs[
                season_choice
            ]

            value_col = config[
                "value_col"
            ]

            if value_col not in season_work.columns:
                st.info(
                    (
                        "All-play season data is unavailable. Run build_luck_metrics.py."
                        if value_col.startswith(
                            "all_play_"
                        )
                        else f"{value_col} is not available in season_records.csv."
                    )
                )
            else:
                record_rows = (
                    season_work[
                        [
                            "year",
                            scol,
                            value_col,
                        ]
                    ]
                    .dropna()
                    .copy()
                )

                record_rows[
                    "year"
                ] = pd.to_numeric(
                    record_rows[
                        "year"
                    ],
                    errors="coerce",
                ).astype(int)

                record_rows[
                    value_col
                ] = pd.to_numeric(
                    record_rows[
                        value_col
                    ],
                    errors="coerce",
                )

                record_rows = (
                    record_rows
                    .dropna(
                        subset=[
                            value_col,
                        ]
                    )
                    .sort_values(
                        [
                            value_col,
                            "year",
                            scol,
                        ],
                        ascending=[
                            config[
                                "ascending"
                            ],
                            True,
                            True,
                        ],
                    )
                    .reset_index(
                        drop=True
                    )
                )

                if record_rows.empty:
                    st.info(
                        "No season records are available for this metric."
                    )
                else:
                    best_value = float(
                        record_rows.iloc[
                            0
                        ][
                            value_col
                        ]
                    )

                    holders = record_rows[
                        np.isclose(
                            record_rows[
                                value_col
                            ],
                            best_value,
                        )
                    ].copy()

                    holder_text = (
                        " & ".join(
                            (
                                holders[
                                    scol
                                ]
                                .astype(str)
                                + " ("
                                + holders[
                                    "year"
                                ]
                                .astype(int)
                                .astype(str)
                                + ")"
                            )
                            .tolist()
                        )
                    )

                    first_record_year = int(
                        holders[
                            "year"
                        ]
                        .min()
                    )

                    latest_year = int(
                        season_work[
                            "year"
                        ]
                        .max()
                    )

                    years_held = max(
                        latest_year
                        - first_record_year,
                        0,
                    )

                    # ----------------------------------------------------
                    # BUILD RECORD PROGRESSION
                    # ----------------------------------------------------

                    progression_rows = []
                    standing_record = None

                    chronological = (
                        record_rows
                        .sort_values(
                            [
                                "year",
                                scol,
                            ]
                        )
                    )

                    for _, row in chronological.iterrows():
                        value = float(
                            row[
                                value_col
                            ]
                        )

                        if standing_record is None:
                            is_new = True
                            is_tie = False
                        else:
                            is_new = (
                                value
                                < standing_record
                                - 1e-9
                                if config[
                                    "ascending"
                                ]
                                else value
                                > standing_record
                                + 1e-9
                            )

                            is_tie = np.isclose(
                                value,
                                standing_record,
                            )

                        if is_new:
                            standing_record = value
                            event_type = (
                                "New Record"
                            )
                        elif is_tie:
                            event_type = (
                                "Tied Record"
                            )
                        else:
                            continue

                        progression_rows.append(
                            {
                                "year":
                                    int(
                                        row[
                                            "year"
                                        ]
                                    ),
                                "team":
                                    row[
                                        scol
                                    ],
                                "value":
                                    value,
                                "type":
                                    event_type,
                            }
                        )

                    progression = pd.DataFrame(
                        progression_rows
                    )

                    # ----------------------------------------------------
                    # RECORD HEADER
                    # ----------------------------------------------------

                    c1, c2, c3 = st.columns(
                        3
                    )

                    c1.metric(
                        "🏆 Current Record",
                        config[
                            "format"
                        ](
                            best_value
                        ),
                        holder_text,
                    )

                    c2.metric(
                        "📅 First Set",
                        str(
                            first_record_year
                        ),
                        (
                            f"{years_held} season"
                            + (
                                "s ago"
                                if years_held != 1
                                else " ago"
                            )
                            if years_held > 0
                            else "Current season"
                        ),
                    )

                    c3.metric(
                        "🤝 Record Holders",
                        str(
                            len(
                                holders
                            )
                        ),
                        (
                            "Including ties"
                            if len(
                                holders
                            ) > 1
                            else "Sole holder"
                        ),
                    )

                    st.markdown(
                        (
                            "<div style='text-align:center;"
                            "padding:1rem 0 1.2rem 0;'>"
                            "<div style='font-size:4.5rem;"
                            "font-weight:900;line-height:.95;'>"
                            f"{config['format'](best_value)}"
                            "</div>"
                            "<div style='font-size:1.4rem;"
                            "font-weight:800;opacity:.62;"
                            "letter-spacing:.08em;margin-top:.35rem;'>"
                            f"{config['label']}"
                            "</div>"
                            "<div style='font-size:1.1rem;"
                            "font-weight:750;margin-top:.75rem;'>"
                            f"🏆 {holder_text}"
                            "</div>"
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )

                    st.caption(
                        config[
                            "description"
                        ]
                    )

                    # ----------------------------------------------------
                    # STANDINGS + PROGRESSION
                    # ----------------------------------------------------

                    left, right = st.columns(
                        [
                            1.20,
                            .80,
                        ],
                        gap="large",
                    )

                    with left:
                        st.subheader(
                            "Current Record Standings"
                        )

                        standings = record_rows.copy()

                        standings[
                            "Rank"
                        ] = (
                            standings[
                                value_col
                            ]
                            .rank(
                                method="min",
                                ascending=config[
                                    "ascending"
                                ],
                            )
                            .astype(int)
                        )

                        standings[
                            "Season"
                        ] = (
                            standings[
                                "year"
                            ]
                            .astype(int)
                        )

                        standings[
                            "Franchise"
                        ] = standings.apply(
                            lambda row:
                                (
                                    "🏆 "
                                    + str(
                                        row[
                                            scol
                                        ]
                                    )
                                    if np.isclose(
                                        float(
                                            row[
                                                value_col
                                            ]
                                        ),
                                        best_value,
                                    )
                                    else str(
                                        row[
                                            scol
                                        ]
                                    )
                                ),
                            axis=1,
                        )

                        standings[
                            "Actual"
                        ] = standings[
                            value_col
                        ].apply(
                            lambda x:
                                config[
                                    "format"
                                ](
                                    float(x)
                                )
                        )

                        standings = (
                            standings
                            .sort_values(
                                [
                                    value_col,
                                    "year",
                                ],
                                ascending=[
                                    config[
                                        "ascending"
                                    ],
                                    True,
                                ],
                            )
                            [
                                [
                                    "Rank",
                                    "Season",
                                    "Franchise",
                                    "Actual",
                                ]
                            ]
                            .head(
                                25
                            )
                        )

                        st.dataframe(
                            standings,
                            hide_index=True,
                            use_container_width=True,
                            height=520,
                            column_config={
                                "Rank":
                                    st.column_config.NumberColumn(
                                        "Rank",
                                        format="#%d",
                                        width="small",
                                    ),
                                "Season":
                                    st.column_config.NumberColumn(
                                        "Season",
                                        format="%d",
                                        width="small",
                                    ),
                                "Franchise":
                                    st.column_config.TextColumn(
                                        "Franchise",
                                        width="large",
                                    ),
                                "Actual":
                                    st.column_config.TextColumn(
                                        config[
                                            "label"
                                        ].title(),
                                        width="medium",
                                    ),
                            },
                        )

                    with right:
                        st.subheader(
                            "Record Progression"
                        )

                        st.caption(
                            "Every time the single-season league benchmark was set or tied."
                        )

                        progression = (
                            progression
                            .iloc[::-1]
                            .reset_index(
                                drop=True
                            )
                        )

                        for i, row in progression.iterrows():
                            p1, p2, p3 = st.columns(
                                [
                                    .10,
                                    .68,
                                    .22,
                                ],
                                vertical_alignment="top",
                            )

                            p1.markdown(
                                "### 🏆"
                                if i == 0
                                else "### 🔵"
                            )

                            p2.markdown(
                                f"**{row['team']}**"
                            )

                            p2.caption(
                                (
                                    f"{int(row['year'])} Season"
                                    f"\n\n{row['type']}"
                                )
                            )

                            p3.markdown(
                                (
                                    "<div style='text-align:right;"
                                    "font-size:1.1rem;"
                                    "font-weight:800;"
                                    "padding-top:.15rem;'>"
                                    f"{config['format'](float(row['value']))}"
                                    "</div>"
                                ),
                                unsafe_allow_html=True,
                            )

                            if i < len(
                                progression
                            ) - 1:
                                st.divider()


# ============================================================
# MATCHUP
# ============================================================
with tab_matchup:
    st.header('⚔️ Matchup Records')
    st.caption('Records created in a single regular-season matchup.')

    if team_games.empty:
        st.info('Team game history is not available. Run build_league_history.py.')
    else:
        games = team_games.copy()
        games['combined_score'] = games['points_for'] + games['points_against']
        if 'margin' not in games.columns:
            games['margin'] = games['points_for'] - games['points_against']

        if 'matchup_id' in games.columns:
            unique_games = games.drop_duplicates(subset=['matchup_id']).copy()
        else:
            games['_pair'] = games.apply(lambda r: tuple(sorted([str(r['team']),str(r['opponent'])])), axis=1)
            unique_games = games.drop_duplicates(subset=['year','week','_pair']).copy()

        highest = games.sort_values('points_for',ascending=False).iloc[0]
        lowest = games.sort_values('points_for',ascending=True).iloc[0]
        biggest = games.sort_values('margin',ascending=False).iloc[0]
        closest = unique_games.loc[unique_games['margin'].abs().idxmin()]

        c1,c2,c3,c4 = st.columns(4)
        c1.metric('Highest Team Score',highest['team'],f"{highest['points_for']:.2f} · {int(highest['year'])} W{int(highest['week'])}")
        c2.metric('Lowest Team Score',lowest['team'],f"{lowest['points_for']:.2f} · {int(lowest['year'])} W{int(lowest['week'])}")
        c3.metric('Biggest Blowout',biggest['team'],f"+{biggest['margin']:.2f} vs {biggest['opponent']}")
        c4.metric('Closest Game',f"{closest['team']} vs {closest['opponent']}",f"{abs(closest['margin']):.2f} pts")

        st.subheader('Highest Individual Team Scores')
        top_table(games,'points_for',False,['year','week','team','opponent','points_for','points_against','result'],{
            'year':'Season','week':'Week','team':'Franchise','opponent':'Opponent','points_for':'Score','points_against':'Opp Score','result':'Result'
        },20)

        m1,m2 = st.columns(2)
        with m1:
            st.subheader('Highest Combined Scores')
            top_table(unique_games,'combined_score',False,['year','week','team','opponent','points_for','points_against','combined_score'],{
                'year':'Season','week':'Week','team':'Team 1','opponent':'Team 2','points_for':'Score 1','points_against':'Score 2','combined_score':'Combined'
            },10)
        with m2:
            st.subheader('Lowest Combined Scores')
            top_table(unique_games,'combined_score',True,['year','week','team','opponent','points_for','points_against','combined_score'],{
                'year':'Season','week':'Week','team':'Team 1','opponent':'Team 2','points_for':'Score 1','points_against':'Score 2','combined_score':'Combined'
            },10)

        if 'result' in games.columns:
            u1,u2 = st.columns(2)
            with u1:
                st.subheader('Highest Score in a Loss')
                losses = games[games['result']=='L']
                top_table(losses,'points_for',False,['year','week','team','opponent','points_for','points_against'],{
                    'year':'Season','week':'Week','team':'Franchise','opponent':'Opponent','points_for':'Score','points_against':'Opp Score'
                },10)
            with u2:
                st.subheader('Lowest Score in a Win')
                wins = games[games['result']=='W']
                top_table(wins,'points_for',True,['year','week','team','opponent','points_for','points_against'],{
                    'year':'Season','week':'Week','team':'Franchise','opponent':'Opponent','points_for':'Score','points_against':'Opp Score'
                },10)

# ============================================================
# ROSTER
# ============================================================
with tab_roster:
    st.header('🧍 Roster & Player Records')
    st.caption('Player records currently use validated 2018–2025 weekly lineup data.')

    if weekly_lineups.empty:
        st.info('Weekly player history is not available.')
    else:
        roster = weekly_lineups[weekly_lineups['player'].astype(str).str.strip().ne('(Empty)')].copy()
        if 'is_starter' in roster.columns:
            starter_mask = roster['is_starter'].astype(str).str.strip().str.lower().isin(['true','1','yes'])
        else:
            starter_mask = ~roster['lineup_slot'].astype(str).str.upper().isin(['BN','IR','IR+'])
        starters = roster[starter_mask].copy()
        bench = roster[~starter_mask].copy()
        starters['fantasy_points'] = pd.to_numeric(starters['fantasy_points'],errors='coerce')
        bench['fantasy_points'] = pd.to_numeric(bench['fantasy_points'],errors='coerce')

        career = starters.groupby('player',as_index=False).agg(
            counted_points=('fantasy_points','sum'),starts=('player','size'),seasons=('year','nunique'),best_game=('fantasy_points','max')
        )
        career['points_per_start'] = career['counted_points']/career['starts']
        career = career.sort_values('counted_points',ascending=False)

        best_game = starters.sort_values('fantasy_points',ascending=False).iloc[0]
        leader = career.iloc[0]
        starts_leader = career.sort_values('starts',ascending=False).iloc[0]

        c1,c2,c3,c4 = st.columns(4)
        c1.metric('Highest Player Week',best_game['player'],f"{best_game['fantasy_points']:.2f} pts · {int(best_game['year'])} W{int(best_game['week'])}")
        c2.metric('Most Counted Career Points',leader['player'],f"{leader['counted_points']:,.2f}")
        c3.metric('Most Career Starts',starts_leader['player'],f"{int(starts_leader['starts'])} starts")
        if not bench.empty and bench['fantasy_points'].notna().any():
            bench_bomb = bench.sort_values('fantasy_points',ascending=False).iloc[0]
            c4.metric('Highest Bench Score',bench_bomb['player'],f"{bench_bomb['fantasy_points']:.2f} pts · {int(bench_bomb['year'])} W{int(bench_bomb['week'])}")

        st.subheader('Career Starting-Lineup Scoring Leaders')
        top_table(career,'counted_points',False,['player','counted_points','starts','seasons','points_per_start','best_game'],{
            'player':'Player','counted_points':'Career Points','starts':'Starts','seasons':'Seasons','points_per_start':'Pts / Start','best_game':'Best Game'
        },25)

        st.subheader('Highest Single-Week Player Scores')
        top_table(starters,'fantasy_points',False,['year','week','player','fantasy_team','lineup_slot','fantasy_points'],{
            'year':'Season','week':'Week','player':'Player','fantasy_team':'Franchise','lineup_slot':'Slot','fantasy_points':'Points'
        },25)

        if not player_pedigree.empty and 'championships' in player_pedigree.columns:
            st.subheader('Most Championship Rosters')
            top_table(player_pedigree,'championships',False,['player','championships','championship_seasons','champion_franchises'],{
                'player':'Player','championships':'Championships','championship_seasons':'Title Seasons','champion_franchises':'Champion Franchises'
            },25)
            st.caption("Championship-roster counts use the champion's final regular-season roster as the historical roster proxy.")

# ============================================================
# STREAKS
# ============================================================
with tab_streaks:
    st.header('🔥 Streak Records')
    st.caption('Consecutive regular-season game streaks calculated chronologically.')

    if team_games.empty:
        st.info('Team game history is not available.')
    else:
        games = team_games.sort_values(['team','year','week']).copy()

        def streak_runs(df, condition_func):
            records = []
            for team, group in df.groupby('team'):
                group = group.sort_values(['year','week'])
                current, best = [], []
                for _, row in group.iterrows():
                    if condition_func(row):
                        current.append(row)
                    else:
                        if len(current) > len(best): best = current[:]
                        current = []
                if len(current) > len(best): best = current[:]
                if best:
                    records.append({
                        'team':team,'games':len(best),
                        'start_year':int(best[0]['year']),'start_week':int(best[0]['week']),
                        'end_year':int(best[-1]['year']),'end_week':int(best[-1]['week'])
                    })
            return pd.DataFrame(records)

        win_streaks = streak_runs(games,lambda r:r['result']=='W')
        loss_streaks = streak_runs(games,lambda r:r['result']=='L')
        hundred_streaks = streak_runs(games,lambda r:r['points_for']>=100)
        sub100_streaks = streak_runs(games,lambda r:r['points_for']<100)

        c1,c2,c3,c4 = st.columns(4)
        if not win_streaks.empty:
            r=win_streaks.sort_values('games',ascending=False).iloc[0]; c1.metric('Longest Win Streak',r['team'],f"{int(r['games'])} games")
        if not loss_streaks.empty:
            r=loss_streaks.sort_values('games',ascending=False).iloc[0]; c2.metric('Longest Losing Streak',r['team'],f"{int(r['games'])} games")
        if not hundred_streaks.empty:
            r=hundred_streaks.sort_values('games',ascending=False).iloc[0]; c3.metric('Longest 100+ Streak',r['team'],f"{int(r['games'])} games")
        if not sub100_streaks.empty:
            r=sub100_streaks.sort_values('games',ascending=False).iloc[0]; c4.metric('Longest Sub-100 Streak',r['team'],f"{int(r['games'])} games")

        def show_streak_table(title, df):
            st.subheader(title)
            if df.empty:
                st.info('No streak data.')
                return
            work=df.sort_values('games',ascending=False).head(15).copy()
            work['Start']=work['start_year'].astype(str)+' W'+work['start_week'].astype(str)
            work['End']=work['end_year'].astype(str)+' W'+work['end_week'].astype(str)
            work=work.rename(columns={'team':'Franchise','games':'Games'})
            st.dataframe(work[['Franchise','Games','Start','End']],hide_index=True,use_container_width=True)

        s1,s2=st.columns(2)
        with s1: show_streak_table('Longest Win Streaks',win_streaks)
        with s2: show_streak_table('Longest Losing Streaks',loss_streaks)
        s3,s4=st.columns(2)
        with s3: show_streak_table('Consecutive 100+ Point Games',hundred_streaks)
        with s4: show_streak_table('Consecutive Games Below 100',sub100_streaks)

# ============================================================
# MILESTONES
# ============================================================
with tab_milestones:
    st.header('🎯 Milestones')
    st.caption('Career achievements and the franchises/players that reached them.')

    if team_games.empty:
        st.info('Team game history is not available.')
    else:
        games=team_games.sort_values(['year','week','team']).copy()

        st.subheader('Franchise Win Clubs')
        win_levels=[25,50,75,100]
        rows=[]
        for team,group in games.groupby('team'):
            group=group.sort_values(['year','week']).copy()
            group['career_wins']=group['result'].eq('W').cumsum()
            for level in win_levels:
                hit=group[group['career_wins']>=level]
                if not hit.empty:
                    r=hit.iloc[0]
                    rows.append({'Milestone':f'{level} Wins','Franchise':team,'Reached':f"{int(r['year'])} Week {int(r['week'])}"})
        milestone_df=pd.DataFrame(rows)
        if not milestone_df.empty:
            for milestone in ['100 Wins','75 Wins','50 Wins','25 Wins']:
                club=milestone_df[milestone_df['Milestone']==milestone]
                if not club.empty:
                    st.markdown(f'**{milestone} Club**')
                    st.dataframe(club[['Franchise','Reached']],hide_index=True,use_container_width=True)

        st.subheader('Franchise Scoring Clubs')
        score_levels=[5000,10000,15000]
        score_rows=[]
        for team,group in games.groupby('team'):
            group=group.sort_values(['year','week']).copy()
            group['career_points']=group['points_for'].cumsum()
            for level in score_levels:
                hit=group[group['career_points']>=level]
                if not hit.empty:
                    r=hit.iloc[0]
                    score_rows.append({'Milestone':f'{level:,} Points','Franchise':team,'Reached':f"{int(r['year'])} Week {int(r['week'])}"})
        score_df=pd.DataFrame(score_rows)
        if not score_df.empty:
            st.dataframe(score_df,hide_index=True,use_container_width=True)

        if not weekly_lineups.empty:
            st.subheader('Player Career Milestones')
            roster=weekly_lineups[weekly_lineups['player'].astype(str).str.strip().ne('(Empty)')].copy()
            if 'is_starter' in roster.columns:
                starter_mask=roster['is_starter'].astype(str).str.strip().str.lower().isin(['true','1','yes'])
            else:
                starter_mask=~roster['lineup_slot'].astype(str).str.upper().isin(['BN','IR','IR+'])
            starters=roster[starter_mask].copy()
            starters['fantasy_points']=pd.to_numeric(starters['fantasy_points'],errors='coerce')
            player_career=starters.groupby('player',as_index=False).agg(career_points=('fantasy_points','sum'),starts=('player','size'),seasons=('year','nunique')).sort_values('career_points',ascending=False)
            p1,p2=st.columns(2)
            with p1:
                st.markdown('**1,000+ Counted Fantasy Points**')
                club=player_career[player_career['career_points']>=1000]
                st.dataframe(club.rename(columns={'player':'Player','career_points':'Career Points','starts':'Starts','seasons':'Seasons'}),hide_index=True,use_container_width=True)
            with p2:
                st.markdown('**100+ Career Starts**')
                club=player_career[player_career['starts']>=100]
                st.dataframe(club.rename(columns={'player':'Player','career_points':'Career Points','starts':'Starts','seasons':'Seasons'}),hide_index=True,use_container_width=True)

        if not championships.empty and 'champion' in championships.columns:
            st.subheader('Championship Milestones')
            titles=championships['champion'].value_counts().rename_axis('Franchise').reset_index(name='Championships')
            st.dataframe(titles,hide_index=True,use_container_width=True)

st.divider()
st.caption('League Record Book • Regular-season franchise/matchup records come from data/history/team_games.csv. Player records currently cover validated weekly lineup history from 2018–2025.')