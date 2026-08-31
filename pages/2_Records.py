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
    "Little Red Fournette": "Post Mahomes",
    "Ur The Best Bellows": "Joe Mantegna",
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

st.caption('Regular-season records come from clean historical game data. Roster records use validated weekly player data where available.')

(tab_league, tab_season, tab_roster, tab_streaks, tab_milestones) = st.tabs([
    '🏛️ League','📅 Season','🧍 Roster','🔥 Streaks','🎯 Milestones'
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
# ROSTER
# ============================================================
with tab_roster:
    st.header("🧍 Roster & Player Records")

    if weekly_lineups.empty:
        st.info("Weekly player history is not available.")
    else:
        roster = weekly_lineups[
            weekly_lineups["player"].astype(str).str.strip().ne("(Empty)")
        ].copy()
        numeric(roster, ["year", "week", "fantasy_points"])
        roster = roster.dropna(subset=["player", "year", "week"]).copy()
        roster["year"] = roster["year"].astype(int)
        roster["week"] = roster["week"].astype(int)

        if "is_starter" in roster.columns:
            starter_mask = (
                roster["is_starter"].astype(str).str.strip().str.lower()
                .isin(["true", "1", "yes"])
            )
        else:
            starter_mask = ~roster["lineup_slot"].astype(str).str.upper().isin(
                ["BN", "IR", "IR+"]
            )

        starters = roster[starter_mask].copy()
        bench = roster[~starter_mask].copy()
        starters["fantasy_points"] = pd.to_numeric(
            starters["fantasy_points"], errors="coerce"
        )
        bench["fantasy_points"] = pd.to_numeric(
            bench["fantasy_points"], errors="coerce"
        )

        min_year = int(roster["year"].min()) if not roster.empty else None
        max_year = int(roster["year"].max()) if not roster.empty else None
        if min_year is not None and max_year is not None:
            st.caption(
                f"Choose a player-history record. Weekly lineup records use validated "
                f"{min_year}–{max_year} player data; career totals count starting-lineup production."
            )

        # ------------------------------------------------------------
        # CAREER DATA
        # ------------------------------------------------------------
        career_week = (
            starters.dropna(subset=["fantasy_points"])
            .groupby(["player", "year", "week"], as_index=False)
            .agg(
                week_points=("fantasy_points", "sum"),
                starts=("player", "size"),
            )
            .sort_values(["player", "year", "week"])
        )
        if not career_week.empty:
            career_week["career_points"] = career_week.groupby("player")[
                "week_points"
            ].cumsum()
            career_week["career_starts"] = career_week.groupby("player")[
                "starts"
            ].cumsum()

        career = (
            starters.dropna(subset=["fantasy_points"])
            .groupby("player", as_index=False)
            .agg(
                counted_points=("fantasy_points", "sum"),
                starts=("player", "size"),
                seasons=("year", "nunique"),
                best_game=("fantasy_points", "max"),
            )
        )
        if not career.empty:
            career["points_per_start"] = (
                career["counted_points"] / career["starts"]
            )

        # ------------------------------------------------------------
        # RECORD MENU
        # ------------------------------------------------------------
        roster_configs = {
            "🔥 Highest Starter Score": {
                "short": "🔥 Starter Week",
                "group": "Single Week",
                "kind": "starter_week",
                "label": "POINTS",
                "format": lambda x: f"{x:.2f}",
                "description": "Highest fantasy score by a player used in a starting lineup in one week.",
            },
            "🪑 Highest Bench Score": {
                "short": "🪑 Bench Week",
                "group": "Single Week",
                "kind": "bench_week",
                "label": "BENCH POINTS",
                "format": lambda x: f"{x:.2f}",
                "description": "Highest fantasy score left on a fantasy bench in one week.",
            },
            "📚 Most Career Starter Points": {
                "short": "📚 Career Points",
                "group": "Career",
                "kind": "career_points",
                "label": "CAREER STARTER POINTS",
                "format": lambda x: f"{x:,.2f}",
                "description": "Most fantasy points accumulated while appearing in a starting lineup.",
            },
            "🎬 Most Career Starts": {
                "short": "🎬 Starts",
                "group": "Career",
                "kind": "career_starts",
                "label": "CAREER STARTS",
                "format": lambda x: f"{int(round(x)):,}",
                "description": "Most starting-lineup appearances by a player in league history.",
            },
            "💍 Most Championship Rosters": {
                "short": "💍 Titles",
                "group": "Championships",
                "kind": "championships",
                "label": "CHAMPIONSHIP ROSTERS",
                "format": lambda x: f"{int(round(x))}",
                "description": "Most league championship rosters featuring the same player. Final regular-season rosters are used as the historical roster proxy.",
            },
        }

        roster_groups = [
            ("Single Week", ["🔥 Highest Starter Score", "🪑 Highest Bench Score"]),
            ("Career", ["📚 Most Career Starter Points", "🎬 Most Career Starts"]),
            ("Championships", ["💍 Most Championship Rosters"]),
        ]

        if "roster_record_choice" not in st.session_state:
            st.session_state["roster_record_choice"] = "🔥 Highest Starter Score"

        for group_name, choices in roster_groups:
            st.markdown(f"**{group_name}**")
            cols = st.columns(len(choices))
            for col, choice in zip(cols, choices):
                with col:
                    button_type = (
                        "primary"
                        if st.session_state["roster_record_choice"] == choice
                        else "secondary"
                    )
                    if st.button(
                        roster_configs[choice]["short"],
                        key=f"roster_record_{choice}",
                        use_container_width=True,
                        type=button_type,
                    ):
                        st.session_state["roster_record_choice"] = choice
                        st.rerun()

        choice = st.session_state["roster_record_choice"]
        config = roster_configs[choice]
        kind = config["kind"]

        st.divider()
        st.subheader(choice)

        # ------------------------------------------------------------
        # BUILD STANDINGS + PROGRESSION
        # ------------------------------------------------------------
        standings = pd.DataFrame()
        progression_rows = []

        if kind in {"starter_week", "bench_week"}:
            source = starters if kind == "starter_week" else bench
            source = source.dropna(subset=["fantasy_points"]).copy()
            source = source.sort_values(
                ["fantasy_points", "year", "week", "player"],
                ascending=[False, True, True, True],
            )
            if not source.empty:
                standings = source[[
                    "year", "week", "player", "fantasy_team",
                    "lineup_slot", "fantasy_points"
                ]].copy()
                standings = standings.rename(columns={"fantasy_points": "value"})

                standing_record = None
                for _, row in source.sort_values(
                    ["year", "week", "player"]
                ).iterrows():
                    value = float(row["fantasy_points"])
                    if standing_record is None or value > standing_record + 1e-9:
                        standing_record = value
                        event_type = "New Record"
                    elif np.isclose(value, standing_record):
                        event_type = "Tied Record"
                    else:
                        continue
                    progression_rows.append({
                        "year": int(row["year"]),
                        "week": int(row["week"]),
                        "player": row["player"],
                        "value": value,
                        "type": event_type,
                    })

        elif kind in {"career_points", "career_starts"}:
            value_col = "counted_points" if kind == "career_points" else "starts"
            history_col = "career_points" if kind == "career_points" else "career_starts"
            if not career.empty:
                standings = career[[
                    "player", "counted_points", "starts", "seasons", "best_game"
                ]].copy()
                standings["value"] = standings[value_col]
                standings = standings.sort_values(
                    ["value", "player"], ascending=[False, True]
                )

            if not career_week.empty:
                standing_record = None
                for _, row in career_week.sort_values(
                    ["year", "week", "player"]
                ).iterrows():
                    value = float(row[history_col])
                    if standing_record is None or value > standing_record + 1e-9:
                        standing_record = value
                        event_type = "New Record"
                    elif np.isclose(value, standing_record):
                        event_type = "Tied Record"
                    else:
                        continue
                    progression_rows.append({
                        "year": int(row["year"]),
                        "week": int(row["week"]),
                        "player": row["player"],
                        "value": value,
                        "type": event_type,
                    })

        elif kind == "championships":
            if not player_pedigree.empty and "championships" in player_pedigree.columns:
                ped = player_pedigree.copy()
                ped["championships"] = pd.to_numeric(
                    ped["championships"], errors="coerce"
                )
                ped = ped.dropna(subset=["player", "championships"])
                standings = ped[[
                    c for c in [
                        "player", "championships", "championship_seasons",
                        "champion_franchises"
                    ] if c in ped.columns
                ]].copy()
                standings["value"] = standings["championships"]
                standings = standings.sort_values(
                    ["value", "player"], ascending=[False, True]
                )

                # Reconstruct title-count progression from the stored title seasons.
                title_events = []
                if "championship_seasons" in ped.columns:
                    for _, row in ped.iterrows():
                        seasons = pd.Series(
                            str(row.get("championship_seasons", ""))
                            .replace("[", " ").replace("]", " ")
                            .replace("'", " ").replace('"', " ")
                            .replace(";", ",").split(",")
                        ).astype(str).str.extract(r"(20\d{2})", expand=False).dropna()
                        for year_text in seasons:
                            title_events.append({
                                "year": int(year_text),
                                "player": row["player"],
                            })

                if title_events:
                    title_events = pd.DataFrame(title_events).sort_values(
                        ["year", "player"]
                    )
                    counts = {}
                    standing_record = 0
                    for _, row in title_events.iterrows():
                        player = row["player"]
                        counts[player] = counts.get(player, 0) + 1
                        value = counts[player]
                        if value > standing_record:
                            standing_record = value
                            event_type = "New Record"
                        elif value == standing_record:
                            event_type = "Tied Record"
                        else:
                            continue
                        progression_rows.append({
                            "year": int(row["year"]),
                            "week": np.nan,
                            "player": player,
                            "value": float(value),
                            "type": event_type,
                        })

        progression = pd.DataFrame(progression_rows)

        if standings.empty:
            st.info("No player records are available for this metric.")
        else:
            best_value = float(standings.iloc[0]["value"])
            holders = standings[np.isclose(standings["value"], best_value)].copy()
            holder_text = " & ".join(holders["player"].astype(str).tolist())

            if not progression.empty:
                record_hits = progression[np.isclose(progression["value"], best_value)]
                first_set_year = int(record_hits["year"].min()) if not record_hits.empty else None
                latest_year = int(roster["year"].max())
                years_held = max(latest_year - first_set_year, 0) if first_set_year else 0
            else:
                first_set_year = None
                years_held = 0

            c1, c2, c3 = st.columns(3)
            c1.metric(
                "🏆 Current Record",
                config["format"](best_value),
                holder_text,
            )
            c2.metric(
                "📅 First Set",
                str(first_set_year) if first_set_year else "—",
                (
                    f"{years_held} season{'s' if years_held != 1 else ''} ago"
                    if first_set_year and years_held > 0
                    else "Current record"
                ),
            )
            c3.metric(
                "🤝 Record Holders",
                str(len(holders)),
                "Including ties" if len(holders) > 1 else "Sole holder",
            )

            st.markdown(
                (
                    "<div style='text-align:center;padding:1rem 0 1.2rem 0;'>"
                    "<div style='font-size:4.5rem;font-weight:900;line-height:.95;'>"
                    f"{config['format'](best_value)}"
                    "</div>"
                    "<div style='font-size:1.4rem;font-weight:800;opacity:.62;"
                    "letter-spacing:.08em;margin-top:.35rem;'>"
                    f"{config['label']}"
                    "</div>"
                    "<div style='font-size:1.1rem;font-weight:750;margin-top:.75rem;'>"
                    f"🏆 {holder_text}"
                    "</div></div>"
                ),
                unsafe_allow_html=True,
            )
            st.caption(config["description"])

            left, right = st.columns([1.08, .92], gap="medium")

            with left:
                st.subheader("Current Record Standings")
                board = standings.copy().head(12)
                board.insert(0, "Rank", range(1, len(board) + 1))
                board["Player"] = board["player"].apply(
                    lambda p: f"🏆 {p}" if str(p) in set(holders["player"].astype(str)) else str(p)
                )

                if kind in {"starter_week", "bench_week"}:
                    board["Season"] = board["year"].astype(int)
                    board["Week"] = board["week"].astype(int)
                    board["Franchise"] = board["fantasy_team"].astype(str)
                    board["Score"] = board["value"].apply(lambda x: f"{float(x):.2f}")
                    display_cols = ["Rank", "Season", "Week", "Player", "Franchise", "Score"]
                elif kind == "career_points":
                    board["Career Points"] = board["value"].apply(lambda x: f"{float(x):,.2f}")
                    board["Starts"] = board["starts"].astype(int)
                    board["Seasons"] = board["seasons"].astype(int)
                    board["Pts / Start"] = board["points_per_start"].apply(lambda x: f"{float(x):.2f}") if "points_per_start" in board.columns else "—"
                    display_cols = ["Rank", "Player", "Career Points", "Starts", "Seasons"]
                elif kind == "career_starts":
                    board["Starts"] = board["value"].astype(int)
                    board["Career Points"] = board["counted_points"].apply(lambda x: f"{float(x):,.2f}")
                    board["Seasons"] = board["seasons"].astype(int)
                    display_cols = ["Rank", "Player", "Starts", "Career Points", "Seasons"]
                else:
                    board["Championships"] = board["value"].astype(int)
                    if "championship_seasons" in board.columns:
                        board["Title Seasons"] = board["championship_seasons"].astype(str)
                    if "champion_franchises" in board.columns:
                        board["Champion Franchises"] = board["champion_franchises"].astype(str)
                    display_cols = [
                        c for c in ["Rank", "Player", "Championships", "Title Seasons", "Champion Franchises"]
                        if c in board.columns
                    ]

                st.dataframe(
                    board[display_cols],
                    hide_index=True,
                    use_container_width=True,
                    height=min(350, 34 + 29 * len(board)),
                    row_height=29,
                    column_config={
                        "Rank": st.column_config.NumberColumn("Rank", format="#%d", width="small"),
                        "Season": st.column_config.NumberColumn("Yr", format="%d", width="small"),
                        "Week": st.column_config.NumberColumn("Wk", format="%d", width="small"),
                        "Player": st.column_config.TextColumn("Player", width="medium"),
                        "Franchise": st.column_config.TextColumn("Franchise", width="medium"),
                        "Score": st.column_config.TextColumn("Pts", width="small"),
                        "Career Points": st.column_config.TextColumn("Points", width="small"),
                        "Starts": st.column_config.NumberColumn("Starts", format="%d", width="small"),
                        "Seasons": st.column_config.NumberColumn("Yrs", format="%d", width="small"),
                        "Championships": st.column_config.NumberColumn("Titles", format="%d", width="small"),
                        "Title Seasons": st.column_config.TextColumn("Seasons", width="medium"),
                        "Champion Franchises": st.column_config.TextColumn("Franchises", width="medium"),
                    },
                )

            with right:
                st.subheader("Record Progression")
                st.caption("Every time the league's player benchmark was set or tied.")

                if progression.empty:
                    st.caption("Historical progression is not available for this record.")
                else:
                    prog = progression.iloc[::-1].reset_index(drop=True)
                    for i, row in prog.iterrows():
                        p1, p2, p3 = st.columns([.10, .68, .22], vertical_alignment="top")
                        p1.markdown("### 🏆" if i == 0 else "### 🔵")
                        p2.markdown(f"**{row['player']}**")
                        period = f"{int(row['year'])}"
                        if pd.notna(row.get("week")):
                            period += f" · W{int(row['week'])}"
                        p2.caption(f"{period}\n\n{row['type']}")
                        p3.markdown(
                            (
                                "<div style='text-align:right;font-size:1.1rem;"
                                "font-weight:800;padding-top:.15rem;'>"
                                f"{config['format'](float(row['value']))}"
                                "</div>"
                            ),
                            unsafe_allow_html=True,
                        )
                        if i < len(prog) - 1:
                            st.divider()

        if kind == "championships":
            st.caption(
                "Championship-roster counts use the champion's final regular-season roster "
                "as the historical roster proxy."
            )

# ============================================================
# STREAKS
# ============================================================
with tab_streaks:
    st.header("🔥 Streak Records")
    st.caption(
        "Game streaks use regular-season matchups only. Season qualification streaks "
        "and postseason game streaks are measured separately so playoff games are never "
        "mixed into regular-season runs."
    )

    games = normalize_franchise_columns(team_games.copy())
    numeric(games, ["year", "week", "points_for"])
    if not games.empty:
        games = (
            games.dropna(subset=["team", "year", "week"])
            .sort_values(["team", "year", "week"])
            .copy()
        )
        games["year"] = games["year"].astype(int)
        games["week"] = games["week"].astype(int)

        # Weekly context for era-resistant streaks.
        games["weekly_rank"] = (
            games.groupby(["year", "week"])["points_for"]
            .rank(method="min", ascending=False)
        )
        games["weekly_median"] = (
            games.groupby(["year", "week"])["points_for"]
            .transform("median")
        )

    def build_game_streak_history(df, condition_func):
        """Every maximal game streak plus chronological league-record progression."""
        run_rows = []
        progression_rows = []
        if df.empty:
            return pd.DataFrame(), pd.DataFrame()

        for team, group in df.groupby("team"):
            group = group.sort_values(["year", "week"])
            current = []
            for _, row in group.iterrows():
                if condition_func(row):
                    current.append(row)
                else:
                    if current:
                        run_rows.append({
                            "team": team,
                            "length": len(current),
                            "start_year": int(current[0]["year"]),
                            "start_week": int(current[0]["week"]),
                            "end_year": int(current[-1]["year"]),
                            "end_week": int(current[-1]["week"]),
                        })
                    current = []
            if current:
                run_rows.append({
                    "team": team,
                    "length": len(current),
                    "start_year": int(current[0]["year"]),
                    "start_week": int(current[0]["week"]),
                    "end_year": int(current[-1]["year"]),
                    "end_week": int(current[-1]["week"]),
                })

        counters = {}
        standing_record = 0
        for _, row in df.sort_values(["year", "week", "team"]).iterrows():
            team = row["team"]
            if condition_func(row):
                counters[team] = counters.get(team, 0) + 1
                value = int(counters[team])
                if value > standing_record:
                    standing_record = value
                    progression_rows.append({
                        "year": int(row["year"]), "week": int(row["week"]),
                        "team": team, "value": value, "type": "New Record",
                    })
                elif value == standing_record and value > 0:
                    progression_rows.append({
                        "year": int(row["year"]), "week": int(row["week"]),
                        "team": team, "value": value, "type": "Tied Record",
                    })
            else:
                counters[team] = 0

        return pd.DataFrame(run_rows), pd.DataFrame(progression_rows)

    def build_season_streak_history(season_df, condition_col):
        """Consecutive qualifying active seasons; gaps in participation break a streak."""
        run_rows = []
        progression_rows = []
        if season_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        for team, group in season_df.groupby("team"):
            group = group.sort_values("year")
            current = []
            previous_year = None
            for _, row in group.iterrows():
                year = int(row["year"])
                qualifies = bool(row[condition_col])
                consecutive = previous_year is None or year == previous_year + 1
                if qualifies and consecutive:
                    current.append(row)
                elif qualifies:
                    if current:
                        run_rows.append({
                            "team": team, "length": len(current),
                            "start_year": int(current[0]["year"]),
                            "end_year": int(current[-1]["year"]),
                        })
                    current = [row]
                else:
                    if current:
                        run_rows.append({
                            "team": team, "length": len(current),
                            "start_year": int(current[0]["year"]),
                            "end_year": int(current[-1]["year"]),
                        })
                    current = []
                previous_year = year
            if current:
                run_rows.append({
                    "team": team, "length": len(current),
                    "start_year": int(current[0]["year"]),
                    "end_year": int(current[-1]["year"]),
                })

        counters = {}
        last_year = {}
        standing_record = 0
        for _, row in season_df.sort_values(["year", "team"]).iterrows():
            team = row["team"]
            year = int(row["year"])
            if bool(row[condition_col]):
                counters[team] = (
                    counters.get(team, 0) + 1
                    if last_year.get(team) == year - 1
                    else 1
                )
                value = counters[team]
                if value > standing_record:
                    standing_record = value
                    progression_rows.append({
                        "year": year, "team": team, "value": value,
                        "type": "New Record",
                    })
                elif value == standing_record and value > 0:
                    progression_rows.append({
                        "year": year, "team": team, "value": value,
                        "type": "Tied Record",
                    })
            else:
                counters[team] = 0
            last_year[team] = year

        return pd.DataFrame(run_rows), pd.DataFrame(progression_rows)

    # Build one row per active franchise-season from authoritative regular-season games.
    season_streaks = pd.DataFrame()
    if not games.empty:
        season_streaks = (
            games.groupby(["team", "year"], as_index=False)
            .agg(
                wins=("result", lambda s: int((s == "W").sum())),
                losses=("result", lambda s: int((s == "L").sum())),
                ties=("result", lambda s: int((s == "T").sum())),
            )
        )
        season_streaks["games_played"] = (
            season_streaks["wins"] + season_streaks["losses"] + season_streaks["ties"]
        )
        season_streaks["win_value"] = season_streaks["wins"] + 0.5 * season_streaks["ties"]
        season_streaks["winning_season"] = (
            season_streaks["win_value"] > season_streaks["games_played"] / 2
        )
        season_streaks["losing_season"] = (
            season_streaks["win_value"] < season_streaks["games_played"] / 2
        )

        playoff_keys = set()
        if not playoff_appearances.empty:
            po = normalize_franchise_columns(playoff_appearances.copy())
            numeric(po, ["year"])
            po_team_col = team_col(po)
            if po_team_col and "year" in po.columns:
                playoff_keys = set(
                    zip(
                        po[po_team_col].astype(str),
                        pd.to_numeric(po["year"], errors="coerce"),
                    )
                )

        season_streaks["made_playoffs"] = season_streaks.apply(
            lambda r: (str(r["team"]), float(r["year"])) in playoff_keys,
            axis=1,
        )
        season_streaks["missed_playoffs"] = ~season_streaks["made_playoffs"]

    # Normalize postseason matchup history locally for streaks.  Do not depend on
    # the League-tab helper because that function is defined only when the user
    # selects one of the League playoff-game records.
    def normalize_playoff_streak_games(source):
        if source is None or source.empty:
            return pd.DataFrame()

        df = normalize_franchise_columns(source.copy())
        schema_options = [
            ("team_1", "team_1_score", "team_2", "team_2_score"),
            ("left_team", "left_score", "right_team", "right_score"),
            ("team_a", "score_a", "team_b", "score_b"),
            ("team1", "team1_score", "team2", "team2_score"),
            ("winner", "winner_score", "loser", "loser_score"),
        ]

        chosen = next(
            (option for option in schema_options if all(col in df.columns for col in option)),
            None,
        )
        if chosen is None or "year" not in df.columns:
            return pd.DataFrame()

        t1_col, s1_col, t2_col, s2_col = chosen

        if "week" in df.columns:
            period = pd.to_numeric(df["week"], errors="coerce")
        elif "playoff_week" in df.columns:
            period = pd.to_numeric(df["playoff_week"], errors="coerce")
        elif "round" in df.columns:
            numeric_round = pd.to_numeric(df["round"], errors="coerce")
            period = (
                numeric_round
                if numeric_round.notna().any()
                else df.groupby("year")["round"].transform(
                    lambda s: pd.factorize(s, sort=False)[0] + 1
                )
            )
        elif "playoff_round" in df.columns:
            numeric_round = pd.to_numeric(df["playoff_round"], errors="coerce")
            period = (
                numeric_round
                if numeric_round.notna().any()
                else df.groupby("year")["playoff_round"].transform(
                    lambda s: pd.factorize(s, sort=False)[0] + 1
                )
            )
        else:
            period = df.groupby("year").cumcount() + 1

        df["_playoff_period"] = pd.to_numeric(period, errors="coerce")
        winner_loser_schema = t1_col == "winner" and t2_col == "loser"
        rows = []

        for _, row in df.iterrows():
            year = pd.to_numeric(pd.Series([row.get("year")]), errors="coerce").iloc[0]
            score1 = pd.to_numeric(pd.Series([row.get(s1_col)]), errors="coerce").iloc[0]
            score2 = pd.to_numeric(pd.Series([row.get(s2_col)]), errors="coerce").iloc[0]
            if pd.isna(year) or pd.isna(score1) or pd.isna(score2):
                continue

            team1 = normalize_franchise_name(row.get(t1_col))
            team2 = normalize_franchise_name(row.get(t2_col))
            if pd.isna(team1) or pd.isna(team2):
                continue
            team1, team2 = str(team1).strip(), str(team2).strip()
            if not team1 or not team2 or team1.lower() == "nan" or team2.lower() == "nan":
                continue

            playoff_period = row.get("_playoff_period")
            playoff_period = 1 if pd.isna(playoff_period) else int(playoff_period)

            if winner_loser_schema:
                result1, result2 = "W", "L"
            elif score1 > score2:
                result1, result2 = "W", "L"
            elif score1 < score2:
                result1, result2 = "L", "W"
            else:
                result1 = result2 = "T"

            rows.extend([
                {
                    "year": int(year), "week": playoff_period, "team": team1,
                    "opponent": team2, "points_for": float(score1),
                    "points_against": float(score2), "result": result1,
                },
                {
                    "year": int(year), "week": playoff_period, "team": team2,
                    "opponent": team1, "points_for": float(score2),
                    "points_against": float(score1), "result": result2,
                },
            ])

        if not rows:
            return pd.DataFrame()

        return (
            pd.DataFrame(rows)
            .sort_values(["team", "year", "week"])
            .reset_index(drop=True)
        )

    playoff_streak_games = normalize_playoff_streak_games(playoff_games)

    # Finals appearances come directly from the authoritative championships file:
    # both champion and runner-up reached the league final in that season.
    finals_keys = set()
    if not championships.empty and "year" in championships.columns:
        finals_source = normalize_franchise_columns(championships.copy())
        numeric(finals_source, ["year"])
        for _, row in finals_source.dropna(subset=["year"]).iterrows():
            year = int(row["year"])
            for col in ("champion", "runner_up"):
                if col in finals_source.columns and pd.notna(row.get(col)):
                    team = normalize_franchise_name(row.get(col))
                    if pd.notna(team) and str(team).strip():
                        finals_keys.add((str(team).strip(), year))

    if not season_streaks.empty:
        season_streaks["made_finals"] = season_streaks.apply(
            lambda r: (str(r["team"]), int(r["year"])) in finals_keys,
            axis=1,
        )

    streak_configs = {
        "🏆 Longest Win Streak": {
            "short": "🏆 Wins", "group": "Game Results", "kind": "regular",
            "condition": lambda r: r["result"] == "W",
            "label": "CONSECUTIVE WINS",
            "description": "Most consecutive regular-season victories by one franchise.",
        },
        "💀 Longest Losing Streak": {
            "short": "💀 Losses", "group": "Game Results", "kind": "regular",
            "condition": lambda r: r["result"] == "L",
            "label": "CONSECUTIVE LOSSES",
            "description": "Most consecutive regular-season losses by one franchise.",
        },
        "📈 Consecutive Winning Seasons": {
            "short": "📈 Winning Yrs", "group": "Season Results", "kind": "season",
            "condition_col": "winning_season", "label": "CONSECUTIVE WINNING SEASONS",
            "description": "Most consecutive active seasons finishing above .500. A .500 season breaks the streak.",
        },
        "📉 Consecutive Losing Seasons": {
            "short": "📉 Losing Yrs", "group": "Season Results", "kind": "season",
            "condition_col": "losing_season", "label": "CONSECUTIVE LOSING SEASONS",
            "description": "Most consecutive active seasons finishing below .500. A .500 season breaks the streak.",
        },
        "🔥 Longest 100+ Point Streak": {
            "short": "🔥 100+", "group": "Scoring", "kind": "regular",
            "condition": lambda r: pd.notna(r["points_for"]) and r["points_for"] >= 100,
            "label": "CONSECUTIVE 100+ GAMES",
            "description": "Most consecutive regular-season games scoring at least 100 fantasy points.",
        },
        "💥 Longest 120+ Point Streak": {
            "short": "💥 120+", "group": "Scoring", "kind": "regular",
            "condition": lambda r: pd.notna(r["points_for"]) and r["points_for"] >= 120,
            "label": "CONSECUTIVE 120+ GAMES",
            "description": "Most consecutive regular-season games scoring at least 120 fantasy points.",
        },
        "🧊 Longest Sub-100 Point Streak": {
            "short": "🧊 Sub-100", "group": "Scoring", "kind": "regular",
            "condition": lambda r: pd.notna(r["points_for"]) and r["points_for"] < 100,
            "label": "CONSECUTIVE SUB-100 GAMES",
            "description": "Most consecutive regular-season games scoring fewer than 100 fantasy points.",
        },
        "🥶 Longest Sub-80 Point Streak": {
            "short": "🥶 Sub-80", "group": "Scoring", "kind": "regular",
            "condition": lambda r: pd.notna(r["points_for"]) and r["points_for"] < 80,
            "label": "CONSECUTIVE SUB-80 GAMES",
            "description": "Most consecutive regular-season games scoring fewer than 80 fantasy points.",
        },
        "🥇 Consecutive Weekly Top-3 Scores": {
            "short": "🥇 Top 3", "group": "Weekly Rank", "kind": "regular",
            "condition": lambda r: pd.notna(r["weekly_rank"]) and r["weekly_rank"] <= 3,
            "label": "CONSECUTIVE TOP-3 WEEKS",
            "description": "Most consecutive regular-season weeks finishing among the league's three highest scores.",
        },
        "⬆️ Consecutive Above-Median Weeks": {
            "short": "⬆️ Above Med", "group": "Weekly Rank", "kind": "regular",
            "condition": lambda r: pd.notna(r["points_for"]) and pd.notna(r["weekly_median"]) and r["points_for"] > r["weekly_median"],
            "label": "CONSECUTIVE ABOVE-MEDIAN WEEKS",
            "description": "Most consecutive regular-season weeks scoring strictly above that week's league median.",
        },
        "🎟️ Consecutive Playoff Seasons": {
            "short": "🎟️ Made", "group": "Playoffs", "kind": "season",
            "condition_col": "made_playoffs", "label": "CONSECUTIVE PLAYOFF SEASONS",
            "description": "Most consecutive active seasons in which a franchise made the championship bracket.",
        },
        "🚫 Consecutive Missed Playoffs": {
            "short": "🚫 Missed", "group": "Playoffs", "kind": "season",
            "condition_col": "missed_playoffs", "label": "CONSECUTIVE MISSED PLAYOFFS",
            "description": "Most consecutive active seasons in which a franchise missed the championship bracket.",
        },
        "🏆 Consecutive Finals Appearances": {
            "short": "🏆 Finals", "group": "Playoffs", "kind": "season",
            "condition_col": "made_finals", "label": "CONSECUTIVE FINALS APPEARANCES",
            "description": "Most consecutive seasons reaching the league championship game, whether as champion or runner-up.",
        },
        "🏟️ Consecutive Playoff Wins": {
            "short": "🏟️ PO Wins", "group": "Playoffs", "kind": "playoff",
            "condition": lambda r: r["result"] == "W", "label": "CONSECUTIVE PLAYOFF WINS",
            "description": "Most consecutive postseason game victories. Regular-season games are excluded.",
        },
        "☠️ Consecutive Playoff Losses": {
            "short": "☠️ PO Losses", "group": "Playoffs", "kind": "playoff",
            "condition": lambda r: r["result"] == "L", "label": "CONSECUTIVE PLAYOFF LOSSES",
            "description": "Most consecutive postseason game losses. Regular-season games are excluded.",
        },
    }

    streak_groups = [
        ("Game Results", ["🏆 Longest Win Streak", "💀 Longest Losing Streak"]),
        ("Season Results", ["📈 Consecutive Winning Seasons", "📉 Consecutive Losing Seasons"]),
        ("Scoring", [
            "🔥 Longest 100+ Point Streak", "💥 Longest 120+ Point Streak",
            "🧊 Longest Sub-100 Point Streak", "🥶 Longest Sub-80 Point Streak",
        ]),
        ("Weekly Rank", ["🥇 Consecutive Weekly Top-3 Scores", "⬆️ Consecutive Above-Median Weeks"]),
        ("Playoffs", [
            "🎟️ Consecutive Playoff Seasons", "🚫 Consecutive Missed Playoffs",
            "🏆 Consecutive Finals Appearances", "🏟️ Consecutive Playoff Wins",
            "☠️ Consecutive Playoff Losses",
        ]),
    ]

    if "streak_record_choice" not in st.session_state:
        st.session_state["streak_record_choice"] = "🏆 Longest Win Streak"

    def choose_streak_record(record_name):
        st.session_state["streak_record_choice"] = record_name

    for group_name, options in streak_groups:
        label_col, *button_cols = st.columns([0.72] + [1.0] * len(options), gap="small")
        with label_col:
            st.markdown(
                "<div style='padding-top:.45rem;font-size:.78rem;font-weight:800;"
                "opacity:.60;text-transform:uppercase;letter-spacing:.06em;'>"
                f"{group_name}</div>",
                unsafe_allow_html=True,
            )
        for col, option in zip(button_cols, options):
            with col:
                active = st.session_state["streak_record_choice"] == option
                st.button(
                    f"● {streak_configs[option]['short']}" if active else streak_configs[option]["short"],
                    key=f"streak_record_btn_{option}", use_container_width=True,
                    type="primary" if active else "secondary",
                    on_click=choose_streak_record, args=(option,),
                )

    streak_choice = st.session_state["streak_record_choice"]
    st.divider()
    config = streak_configs[streak_choice]
    kind = config["kind"]

    if kind == "season":
        runs, progression = build_season_streak_history(season_streaks, config["condition_col"])
        unit = "seasons"
    elif kind == "playoff":
        runs, progression = build_game_streak_history(playoff_streak_games, config["condition"])
        unit = "games"
    else:
        runs, progression = build_game_streak_history(games, config["condition"])
        unit = "games"

    if runs.empty:
        st.info("No streak data is available for this record.")
    else:
        sort_cols = ["length", "end_year", "team"] if kind == "season" else ["length", "end_year", "end_week", "team"]
        sort_asc = [False, True, True] if kind == "season" else [False, True, True, True]
        runs = runs.sort_values(sort_cols, ascending=sort_asc).reset_index(drop=True)
        best_value = int(runs["length"].max())
        holders = runs[runs["length"] == best_value].copy()
        holder_sort = ["end_year", "team"] if kind == "season" else ["end_year", "end_week", "team"]
        first_record = holders.sort_values(holder_sort).iloc[0]
        latest_record = holders.sort_values(holder_sort).iloc[-1]
        holder_text = " & ".join(holders["team"].drop_duplicates().astype(str).tolist())

        c1, c2, c3 = st.columns(3)
        c1.metric("🏆 Current Record", f"{best_value} {unit}", holder_text)
        first_when = str(int(first_record["end_year"])) if kind == "season" else f"{int(first_record['end_year'])} W{int(first_record['end_week'])}"
        c2.metric("📅 First Set", first_when, str(first_record["team"]))
        c3.metric(
            "🤝 Record Streaks", str(len(holders)),
            f"{holders['team'].nunique()} franchise" + ("s" if holders["team"].nunique() != 1 else ""),
        )

        latest_when = str(int(latest_record["end_year"])) if kind == "season" else f"{int(latest_record['end_year'])} Week {int(latest_record['end_week'])}"
        st.markdown(
            "<div style='text-align:center;padding:1rem 0 1.2rem 0;'>"
            f"<div style='font-size:4.5rem;font-weight:900;line-height:.95;'>{best_value}</div>"
            "<div style='font-size:1.4rem;font-weight:800;opacity:.62;letter-spacing:.08em;margin-top:.35rem;'>"
            f"{config['label']}</div>"
            f"<div style='font-size:1.1rem;font-weight:750;margin-top:.75rem;'>🏆 {holder_text}</div>"
            f"<div style='opacity:.65;margin-top:.2rem;'>Most recent record streak ended {latest_when}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption(config["description"])

        # ------------------------------------------------------------
        # RECORD WATCH
        # ------------------------------------------------------------
        st.divider()
        st.subheader("👀 Record Watch")
        st.caption(
            "Active streaks that are still alive and closest to the all-time record. "
            "A streak must belong to the latest league season/playoff period to appear here."
        )

        watch_rows = []
        if kind == "season" and not season_streaks.empty:
            latest_year = int(season_streaks["year"].max())
            for team, group in season_streaks.groupby("team"):
                group = group.sort_values("year")
                last = group.iloc[-1]
                if int(last["year"]) != latest_year or not bool(last[config["condition_col"]]):
                    continue
                current = 0
                expected_year = latest_year
                for _, srow in group.iloc[::-1].iterrows():
                    if int(srow["year"]) != expected_year or not bool(srow[config["condition_col"]]):
                        break
                    current += 1
                    expected_year -= 1
                watch_rows.append({"member": team, "current": current})

        elif kind in {"regular", "playoff"}:
            source_watch = games if kind == "regular" else playoff_streak_games
            if not source_watch.empty:
                latest_year = int(source_watch["year"].max())
                latest_week = int(source_watch[source_watch["year"].eq(latest_year)]["week"].max())
                for team, group in source_watch.groupby("team"):
                    group = group.sort_values(["year", "week"])
                    last = group.iloc[-1]
                    # Regular-season watch requires the team's final game to be in the
                    # latest league period. Playoff watch requires the latest playoff year.
                    current_period = (
                        int(last["year"]) == latest_year
                        and (kind == "playoff" or int(last["week"]) == latest_week)
                    )
                    if not current_period or not config["condition"](last):
                        continue
                    current = 0
                    for _, grow in group.iloc[::-1].iterrows():
                        if not config["condition"](grow):
                            break
                        current += 1
                    watch_rows.append({"member": team, "current": current})

        if watch_rows:
            watch = pd.DataFrame(watch_rows)
            watch["record"] = best_value
            watch["away"] = (watch["record"] - watch["current"]).clip(lower=0)
            watch["progress"] = np.where(
                watch["record"] > 0,
                watch["current"] / watch["record"],
                0.0,
            )
            watch = (
                watch.sort_values(["away", "current", "member"], ascending=[True, False, True])
                .head(8)
                .reset_index(drop=True)
            )
            watch["Franchise"] = watch["member"]
            watch["Current"] = watch["current"].astype(int)
            watch["Record"] = watch["record"].astype(int)
            watch["Away"] = watch["away"].astype(int)
            watch["Progress"] = watch["progress"].apply(lambda x: f"{x:.0%}")
            st.dataframe(
                watch[["Franchise", "Current", "Record", "Away", "Progress"]],
                hide_index=True,
                use_container_width=True,
                height=38 + 35 * len(watch),
                column_config={
                    "Franchise": st.column_config.TextColumn("Franchise", width="large"),
                    "Current": st.column_config.NumberColumn("Current", format="%d", width="small"),
                    "Record": st.column_config.NumberColumn("Record", format="%d", width="small"),
                    "Away": st.column_config.NumberColumn("Away", format="%d", width="small"),
                    "Progress": st.column_config.TextColumn("Progress", width="small"),
                },
            )
        else:
            st.caption("No active streaks currently qualify for record watch.")


        left, right = st.columns([1.20, .80], gap="large")
        with left:
            st.subheader("Current Record Standings")
            board = runs.copy()
            board["#"] = board["length"].rank(method="min", ascending=False).astype(int)
            board["Franchise"] = np.where(
                board["length"].eq(best_value),
                "🏆 " + board["team"].astype(str), board["team"].astype(str),
            )
            length_label = "Years" if kind == "season" else "Games"
            board[length_label] = board["length"].astype(int)
            if kind == "season":
                board["Span"] = np.where(
                    board["start_year"].eq(board["end_year"]),
                    board["start_year"].astype(int).astype(str),
                    board["start_year"].astype(int).astype(str) + "–" + board["end_year"].astype(int).astype(str),
                )
            else:
                board["Span"] = (
                    board["start_year"].astype(int).astype(str) + " W" + board["start_week"].astype(int).astype(str)
                    + " – " + board["end_year"].astype(int).astype(str) + " W" + board["end_week"].astype(int).astype(str)
                )
            display_board = board[["#", "Franchise", length_label, "Span"]].head(12)
            st.dataframe(
                display_board, hide_index=True, use_container_width=True,
                height=38 + 35 * len(display_board),
                column_config={
                    "#": st.column_config.NumberColumn("#", format="#%d", width="small"),
                    "Franchise": st.column_config.TextColumn("Franchise", width="medium"),
                    length_label: st.column_config.NumberColumn(length_label, format="%d", width="small"),
                    "Span": st.column_config.TextColumn("Span", width="medium"),
                },
            )
            if len(board) > 12:
                st.caption("Showing the top 12 streaks.")

        with right:
            st.subheader("Record Progression")
            st.caption(
                "Every season the all-time streak benchmark was set or tied."
                if kind == "season"
                else "Every game the all-time streak benchmark was set or tied."
            )
            if progression.empty:
                st.info("No record progression is available.")
            else:
                prog = progression.iloc[::-1].reset_index(drop=True)
                for i, row in prog.iterrows():
                    p1, p2, p3 = st.columns([.10, .68, .22], vertical_alignment="top")
                    p1.markdown("### 🏆" if i == 0 else "### 🔵")
                    p2.markdown(f"**{row['team']}**")
                    when = str(int(row["year"])) if kind == "season" else f"{int(row['year'])} Week {int(row['week'])}"
                    p2.caption(f"{when}\n\n{row['type']}")
                    p3.markdown(
                        "<div style='text-align:right;font-size:1.1rem;font-weight:800;padding-top:.15rem;'>"
                        f"{int(row['value'])}</div>",
                        unsafe_allow_html=True,
                    )
                    if i < len(prog) - 1:
                        st.divider()



# ============================================================
# MILESTONES
# ============================================================
with tab_milestones:
    st.header("🎯 Milestones")
    st.caption(
        "Choose a career milestone to see who reached the club, who got there first, "
        "and the chronological history of every member."
    )

    milestone_configs = {
        "🏆 25 Wins": {
            "short": "🏆 25 Wins",
            "group": "Franchise Wins",
            "kind": "team_wins",
            "threshold": 25,
            "label": "WIN CLUB",
            "description": "Franchises that reached 25 regular-season career wins.",
        },
        "🏆 50 Wins": {
            "short": "🏆 50 Wins",
            "group": "Franchise Wins",
            "kind": "team_wins",
            "threshold": 50,
            "label": "WIN CLUB",
            "description": "Franchises that reached 50 regular-season career wins.",
        },
        "🏆 75 Wins": {
            "short": "🏆 75 Wins",
            "group": "Franchise Wins",
            "kind": "team_wins",
            "threshold": 75,
            "label": "WIN CLUB",
            "description": "Franchises that reached 75 regular-season career wins.",
        },
        "🏆 100 Wins": {
            "short": "🏆 100 Wins",
            "group": "Franchise Wins",
            "kind": "team_wins",
            "threshold": 100,
            "label": "WIN CLUB",
            "description": "Franchises that reached 100 regular-season career wins.",
        },
        "📈 5,000 Points": {
            "short": "📈 5K",
            "group": "Franchise Points",
            "kind": "team_points",
            "threshold": 5000,
            "label": "POINT CLUB",
            "description": "Franchises that reached 5,000 regular-season career fantasy points.",
        },
        "📈 10,000 Points": {
            "short": "📈 10K",
            "group": "Franchise Points",
            "kind": "team_points",
            "threshold": 10000,
            "label": "POINT CLUB",
            "description": "Franchises that reached 10,000 regular-season career fantasy points.",
        },
        "📈 15,000 Points": {
            "short": "📈 15K",
            "group": "Franchise Points",
            "kind": "team_points",
            "threshold": 15000,
            "label": "POINT CLUB",
            "description": "Franchises that reached 15,000 regular-season career fantasy points.",
        },
        "👑 1 Championship": {
            "short": "👑 1 Title",
            "group": "Championships",
            "kind": "titles",
            "threshold": 1,
            "label": "CHAMPIONSHIP CLUB",
            "description": "Franchises that won their first league championship.",
        },
        "👑 2 Championships": {
            "short": "👑 2 Titles",
            "group": "Championships",
            "kind": "titles",
            "threshold": 2,
            "label": "CHAMPIONSHIP CLUB",
            "description": "Franchises that reached two league championships.",
        },
        "⭐ 1,000 Player Points": {
            "short": "⭐ 1K Pts",
            "group": "Players",
            "kind": "player_points",
            "threshold": 1000,
            "label": "COUNTED POINT CLUB",
            "description": "Players who reached 1,000 fantasy points while in a starting lineup.",
        },
        "🧍 100 Player Starts": {
            "short": "🧍 100 Starts",
            "group": "Players",
            "kind": "player_starts",
            "threshold": 100,
            "label": "START CLUB",
            "description": "Players who reached 100 career fantasy starts in validated lineup history.",
        },
    }

    milestone_groups = [
        (
            "Franchise Wins",
            [
                "🏆 25 Wins",
                "🏆 50 Wins",
                "🏆 75 Wins",
                "🏆 100 Wins",
            ],
        ),
        (
            "Franchise Points",
            [
                "📈 5,000 Points",
                "📈 10,000 Points",
                "📈 15,000 Points",
            ],
        ),
        (
            "Championships",
            [
                "👑 1 Championship",
                "👑 2 Championships",
            ],
        ),
        (
            "Players",
            [
                "⭐ 1,000 Player Points",
                "🧍 100 Player Starts",
            ],
        ),
    ]

    if "milestone_choice" not in st.session_state:
        st.session_state["milestone_choice"] = "🏆 50 Wins"

    def choose_milestone(record_name):
        st.session_state["milestone_choice"] = record_name

    for group_name, options in milestone_groups:
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

        for col, option in zip(button_cols, options):
            with col:
                active = (
                    st.session_state["milestone_choice"]
                    == option
                )

                st.button(
                    (
                        f"● {milestone_configs[option]['short']}"
                        if active
                        else milestone_configs[option]["short"]
                    ),
                    key=f"milestone_btn_{option}",
                    use_container_width=True,
                    type="primary" if active else "secondary",
                    on_click=choose_milestone,
                    args=(option,),
                )

    milestone_choice = st.session_state["milestone_choice"]
    st.divider()

    config = milestone_configs[milestone_choice]
    threshold = config["threshold"]
    kind = config["kind"]

    milestone_rows = []
    milestone_watch_rows = []
    member_label = "Franchise"
    value_label = "Career Total"

    if kind in {"team_wins", "team_points"}:
        if team_games.empty:
            st.info("Team game history is not available.")
        else:
            source = normalize_franchise_columns(team_games.copy())
            numeric(source, ["year", "week", "points_for"])
            source = source.sort_values(
                ["team", "year", "week"]
            )

            for team, group in source.groupby("team"):
                group = group.sort_values(
                    ["year", "week"]
                ).copy()

                if kind == "team_wins":
                    group["_career_value"] = (
                        group["result"].eq("W").cumsum()
                    )
                    final_value = int(
                        group["_career_value"].iloc[-1]
                    )
                    value_label = "Career Wins"
                else:
                    group["_career_value"] = (
                        pd.to_numeric(
                            group["points_for"],
                            errors="coerce",
                        )
                        .fillna(0)
                        .cumsum()
                    )
                    final_value = float(
                        group["_career_value"].iloc[-1]
                    )
                    value_label = "Career Points"

                hit = group[group["_career_value"] >= threshold]

                if not hit.empty:
                    hit_index = int(np.flatnonzero(group["_career_value"].to_numpy() >= threshold)[0])
                    row = group.iloc[hit_index]
                    seasons_to_reach = int(group.iloc[: hit_index + 1]["year"].nunique())
                    milestone_rows.append({
                        "member": team,
                        "year": int(row["year"]),
                        "week": int(row["week"]),
                        "career_total": final_value,
                        "opportunities_to_reach": hit_index + 1,
                        "seasons_to_reach": seasons_to_reach,
                    })
                else:
                    milestone_watch_rows.append({
                        "member": team,
                        "current": final_value,
                        "remaining": max(float(threshold) - float(final_value), 0.0),
                        "progress": min(float(final_value) / float(threshold), 1.0) if threshold else 0.0,
                    })

    elif kind == "titles":
        if championships.empty or "champion" not in championships.columns:
            st.info("Championship history is not available.")
        else:
            source = normalize_franchise_columns(
                championships.copy()
            )
            numeric(source, ["year"])
            source = (
                source.dropna(subset=["year", "champion"])
                .sort_values(["year", "champion"])
            )

            title_counts = source["champion"].value_counts()

            for team, group in source.groupby("champion"):
                group = group.sort_values("year").reset_index(
                    drop=True
                )

                total_titles = int(title_counts.get(team, 0))
                if len(group) >= threshold:
                    row = group.iloc[threshold - 1]
                    hit_year = int(row["year"])
                    active_years = []
                    if not team_games.empty:
                        team_history = normalize_franchise_columns(team_games.copy())
                        numeric(team_history, ["year"])
                        active_years = sorted(
                            team_history.loc[
                                team_history["team"].astype(str).eq(str(team))
                                & team_history["year"].le(hit_year),
                                "year",
                            ].dropna().astype(int).unique().tolist()
                        )
                    seasons_to_reach = len(active_years) if active_years else np.nan
                    milestone_rows.append({
                        "member": team,
                        "year": hit_year,
                        "week": np.nan,
                        "career_total": total_titles,
                        "opportunities_to_reach": np.nan,
                        "seasons_to_reach": seasons_to_reach,
                    })
                else:
                    milestone_watch_rows.append({
                        "member": team,
                        "current": total_titles,
                        "remaining": max(int(threshold) - total_titles, 0),
                        "progress": min(total_titles / float(threshold), 1.0) if threshold else 0.0,
                    })

            # Include active franchises with zero championships in Milestone Watch.
            if not team_games.empty:
                active_teams = set(
                    normalize_franchise_columns(team_games.copy())["team"]
                    .dropna().astype(str).unique()
                )
                known = {str(row["member"]) for row in milestone_watch_rows}
                reached = {str(row["member"]) for row in milestone_rows}
                for team in sorted(active_teams - known - reached):
                    milestone_watch_rows.append({
                        "member": team,
                        "current": 0,
                        "remaining": float(threshold),
                        "progress": 0.0,
                    })

            value_label = "Championships"

    elif kind in {"player_points", "player_starts"}:
        member_label = "Player"

        if weekly_lineups.empty:
            st.info("Weekly player history is not available.")
        else:
            roster = weekly_lineups[
                weekly_lineups["player"]
                .astype(str)
                .str.strip()
                .ne("(Empty)")
            ].copy()

            if "is_starter" in roster.columns:
                starter_mask = (
                    roster["is_starter"]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .isin(["true", "1", "yes"])
                )
            else:
                starter_mask = ~(
                    roster["lineup_slot"]
                    .astype(str)
                    .str.upper()
                    .isin(["BN", "IR", "IR+"])
                )

            starters = roster[
                starter_mask
            ].copy()

            numeric(
                starters,
                ["year", "week", "fantasy_points"],
            )

            starters = starters.dropna(
                subset=["player", "year", "week"]
            ).sort_values(
                ["player", "year", "week"]
            )

            for player, group in starters.groupby("player"):
                group = group.sort_values(
                    ["year", "week"]
                ).copy()

                if kind == "player_points":
                    group["_career_value"] = (
                        pd.to_numeric(
                            group["fantasy_points"],
                            errors="coerce",
                        )
                        .fillna(0)
                        .cumsum()
                    )
                    final_value = float(
                        group["_career_value"].iloc[-1]
                    )
                    value_label = "Counted Points"
                else:
                    group["_career_value"] = range(
                        1,
                        len(group) + 1,
                    )
                    final_value = int(len(group))
                    value_label = "Career Starts"

                hit = group[group["_career_value"] >= threshold]

                if not hit.empty:
                    hit_index = int(np.flatnonzero(group["_career_value"].to_numpy() >= threshold)[0])
                    row = group.iloc[hit_index]
                    seasons_to_reach = int(group.iloc[: hit_index + 1]["year"].nunique())
                    milestone_rows.append({
                        "member": player,
                        "year": int(row["year"]),
                        "week": int(row["week"]),
                        "career_total": final_value,
                        "opportunities_to_reach": hit_index + 1,
                        "seasons_to_reach": seasons_to_reach,
                    })
                else:
                    milestone_watch_rows.append({
                        "member": player,
                        "current": final_value,
                        "remaining": max(float(threshold) - float(final_value), 0.0),
                        "progress": min(float(final_value) / float(threshold), 1.0) if threshold else 0.0,
                    })

    milestone_df = pd.DataFrame(milestone_rows)

    if milestone_df.empty:
        st.info(
            "No one has reached this milestone yet."
        )
    else:
        milestone_df = (
            milestone_df.sort_values(
                ["year", "week", "member"],
                na_position="last",
            )
            .reset_index(drop=True)
        )

        milestone_df["Member #"] = range(
            1,
            len(milestone_df) + 1,
        )

        first = milestone_df.iloc[0]
        latest = milestone_df.iloc[-1]

        def milestone_period(row):
            if pd.notna(row["week"]):
                return (
                    f"{int(row['year'])} "
                    f"Week {int(row['week'])}"
                )
            return str(int(row["year"]))

        threshold_text = (
            f"{threshold:,}"
            if isinstance(threshold, (int, np.integer))
            else f"{threshold}"
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "🎯 Club Size",
            str(len(milestone_df)),
            (
                f"{member_label.lower()}"
                + ("s" if len(milestone_df) != 1 else "")
            ),
        )

        c2.metric(
            "🥇 First to Reach",
            str(first["member"]),
            milestone_period(first),
        )

        speed_df = milestone_df.copy()
        if kind == "titles":
            speed_df = speed_df.dropna(subset=["seasons_to_reach"])
            fastest = speed_df.sort_values(["seasons_to_reach", "year", "member"]).iloc[0]
            fastest_value = f"{int(fastest['seasons_to_reach'])} seasons"
        else:
            speed_df = speed_df.dropna(subset=["opportunities_to_reach"])
            fastest = speed_df.sort_values(
                ["opportunities_to_reach", "seasons_to_reach", "year", "member"]
            ).iloc[0]
            opportunity_label = "starts" if kind in {"player_points", "player_starts"} else "games"
            fastest_value = f"{int(fastest['opportunities_to_reach'])} {opportunity_label}"
            if pd.notna(fastest.get("seasons_to_reach")):
                fastest_value += f" / {int(fastest['seasons_to_reach'])} seasons"

        c3.metric(
            "⚡ Fastest to Reach",
            str(fastest["member"]),
            fastest_value,
        )

        c4.metric(
            "🆕 Most Recent",
            str(latest["member"]),
            milestone_period(latest),
        )

        st.markdown(
            (
                "<div style='text-align:center;padding:1rem 0 1.2rem 0;'>"
                "<div style='font-size:4.5rem;font-weight:900;line-height:.95;'>"
                f"{threshold_text}</div>"
                "<div style='font-size:1.4rem;font-weight:800;opacity:.62;"
                "letter-spacing:.08em;margin-top:.35rem;'>"
                f"{config['label']}</div>"
                "<div style='font-size:1.1rem;font-weight:750;margin-top:.75rem;'>"
                f"🥇 {first['member']}</div>"
                "<div style='opacity:.65;margin-top:.2rem;'>"
                f"First reached {milestone_period(first)}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

        st.caption(config["description"])

        st.divider()
        st.subheader("👀 Milestone Watch")
        st.caption(
            "The closest members who have not reached this milestone yet. "
            "This is current progress only — no projections are being invented."
        )

        watch_df = pd.DataFrame(milestone_watch_rows)
        if watch_df.empty:
            st.caption("Everyone in the tracked history has already reached this milestone, or no eligible candidates are available.")
        else:
            watch_df = (
                watch_df.sort_values(["progress", "remaining", "member"], ascending=[False, True, True])
                .head(10)
                .reset_index(drop=True)
            )
            watch_df[member_label] = watch_df["member"]
            if kind in {"team_points", "player_points"}:
                watch_df["Current"] = watch_df["current"].apply(lambda x: f"{float(x):,.2f}")
                watch_df["To Go"] = watch_df["remaining"].apply(lambda x: f"{float(x):,.2f}")
            else:
                watch_df["Current"] = watch_df["current"].apply(lambda x: f"{int(round(x)):,}")
                watch_df["To Go"] = watch_df["remaining"].apply(lambda x: f"{int(round(x)):,}")
            watch_df["Progress"] = watch_df["progress"].apply(lambda x: f"{x:.0%}")

            st.dataframe(
                watch_df[[member_label, "Current", "To Go", "Progress"]],
                hide_index=True,
                use_container_width=True,
                height=38 + 35 * len(watch_df),
                column_config={
                    member_label: st.column_config.TextColumn(member_label, width="large"),
                    "Current": st.column_config.TextColumn(value_label, width="medium"),
                    "To Go": st.column_config.TextColumn("To Go", width="medium"),
                    "Progress": st.column_config.TextColumn("Progress", width="small"),
                },
            )

        left, right = st.columns(
            [1.20, .80],
            gap="large",
        )

        with left:
            st.subheader("Milestone Members")

            board = milestone_df.copy()
            board["Rank"] = board["Member #"]
            board[member_label] = board["member"]
            board["Reached"] = board.apply(
                milestone_period,
                axis=1,
            )

            def milestone_speed_text(row):
                if kind == "titles":
                    return (
                        f"{int(row['seasons_to_reach'])} seasons"
                        if pd.notna(row.get("seasons_to_reach"))
                        else "—"
                    )
                opportunities = row.get("opportunities_to_reach")
                seasons = row.get("seasons_to_reach")
                if pd.isna(opportunities):
                    return "—"
                opportunity_label = "starts" if kind in {"player_points", "player_starts"} else "games"
                result = f"{int(opportunities)} {opportunity_label}"
                if pd.notna(seasons):
                    result += f" / {int(seasons)} seasons"
                return result

            board["Speed"] = board.apply(milestone_speed_text, axis=1)

            if kind in {"team_points", "player_points"}:
                board["Current"] = board[
                    "career_total"
                ].apply(
                    lambda x: f"{float(x):,.2f}"
                )
            else:
                board["Current"] = board[
                    "career_total"
                ].apply(
                    lambda x: f"{int(round(x)):,}"
                )

            board.loc[
                board["Rank"].eq(1),
                member_label,
            ] = (
                "🥇 "
                + board.loc[
                    board["Rank"].eq(1),
                    member_label,
                ].astype(str)
            )

            st.dataframe(
                board[
                    [
                        "Rank",
                        member_label,
                        "Reached",
                        "Speed",
                        "Current",
                    ]
                ],
                hide_index=True,
                use_container_width=True,
                height=520,
                column_config={
                    "Rank": st.column_config.NumberColumn(
                        "Rank",
                        format="#%d",
                        width="small",
                    ),
                    member_label: st.column_config.TextColumn(
                        member_label,
                        width="large",
                    ),
                    "Reached": st.column_config.TextColumn(
                        "Reached",
                        width="medium",
                    ),
                    "Speed": st.column_config.TextColumn(
                        "Speed to Milestone",
                        width="medium",
                    ),
                    "Current": st.column_config.TextColumn(
                        value_label,
                        width="medium",
                    ),
                },
            )

        with right:
            st.subheader("Milestone Timeline")
            st.caption(
                "Members are listed in the order they entered the club."
            )

            timeline = (
                milestone_df.iloc[::-1]
                .reset_index(drop=True)
            )

            for i, row in timeline.iterrows():
                t1, t2, t3 = st.columns(
                    [.10, .68, .22],
                    vertical_alignment="top",
                )

                is_first = int(row["Member #"]) == 1

                t1.markdown(
                    "### 🥇"
                    if is_first
                    else "### 🎯"
                )

                t2.markdown(
                    f"**{row['member']}**"
                )

                t2.caption(
                    (
                        f"{milestone_period(row)}"
                        f"\n\nMember #{int(row['Member #'])}"
                    )
                )

                t3.markdown(
                    (
                        "<div style='text-align:right;"
                        "font-size:1.1rem;font-weight:800;"
                        "padding-top:.15rem;'>"
                        f"#{int(row['Member #'])}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

                if i < len(timeline) - 1:
                    st.divider()



st.divider()
st.caption('League Record Book • Regular-season franchise/matchup records come from data/history/team_games.csv. Player records currently cover validated weekly lineup history from 2017–2025.')