import pandas as pd
import streamlit as st
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Trade Center",
    page_icon="🔄",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parents[1]
TRADE_DIR = BASE_DIR / "data" / "trades"
ANALYSIS_DIR = TRADE_DIR / "analysis"

RESULTS_FILE = ANALYSIS_DIR / "trade_results.csv"
FRANCHISE_FILE = ANALYSIS_DIR / "trade_franchise_summary.csv"
ACTIVITY_FILE = ANALYSIS_DIR / "trade_activity.csv"
PLAYER_FILE = ANALYSIS_DIR / "trade_player_value.csv"
SIDE_FILE = ANALYSIS_DIR / "trade_side_value.csv"


@st.cache_data
def load_csv(path):
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


results = load_csv(RESULTS_FILE)
franchise = load_csv(FRANCHISE_FILE)
activity = load_csv(ACTIVITY_FILE)
players = load_csv(PLAYER_FILE)
sides = load_csv(SIDE_FILE)


# ============================================================
# HELPERS
# ============================================================

def fmt_number(value, digits=1):
    if pd.isna(value):
        return "—"
    return f"{float(value):,.{digits}f}"


def fmt_signed(value, digits=1):
    if pd.isna(value):
        return "—"
    value = float(value)
    return f"{value:+,.{digits}f}"


def trade_label(row):
    left = row.get("team_1", "")
    right = row.get("team_2", "")
    year = int(row.get("year", 0))
    trade_id = row.get("trade_id", "")
    return f"{year} — {left} ↔ {right} ({trade_id})"


# ============================================================
# HEADER
# ============================================================

st.title("🔄 Trade Center")

st.caption(
    "Every recorded league trade, evaluated by the value players produced "
    "for their new teams after the deal."
)

if results.empty:
    st.error(
        "Trade analysis data is unavailable. "
        "Run build_trade_analysis.py first."
    )
    st.stop()


# ============================================================
# LEAGUE OVERVIEW
# ============================================================

total_trades = len(results)

if "year" in results.columns:
    first_year = int(pd.to_numeric(results["year"], errors="coerce").min())
    last_year = int(pd.to_numeric(results["year"], errors="coerce").max())
else:
    first_year = None
    last_year = None

decisive = results[
    results["winner"].notna()
].copy() if "winner" in results.columns else pd.DataFrame()

clear_wins = (
    int(results["result_class"].eq("Clear Win").sum())
    if "result_class" in results.columns
    else 0
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Trades", f"{total_trades:,}")
c2.metric(
    "Seasons",
    f"{first_year}–{last_year}"
    if first_year is not None
    else "—",
)
c3.metric("Decisive Trades", f"{len(decisive):,}")
c4.metric("Clear Wins", f"{clear_wins:,}")

st.divider()


# ============================================================
# TABS
# ============================================================

tab_leaders, tab_history, tab_trade, tab_team = st.tabs(
    [
        "🏆 Leaderboard",
        "📜 Trade History",
        "🔎 Trade Breakdown",
        "👤 Franchise Profiles",
    ]
)


# ============================================================
# LEADERBOARD
# ============================================================

with tab_leaders:

    st.subheader("All-Time Trade Leaderboard")

    if franchise.empty:
        st.info("Franchise trade summary is unavailable.")
    else:
        leaderboard = franchise.copy()

        numeric_cols = [
            "trades",
            "wins",
            "losses",
            "even",
            "decisive_trades",
            "win_pct",
            "total_value_received",
            "total_opponent_value",
            "total_value_advantage",
            "avg_trade_advantage",
            "best_trade_margin",
            "worst_trade_margin",
        ]

        for col in numeric_cols:
            if col in leaderboard.columns:
                leaderboard[col] = pd.to_numeric(
                    leaderboard[col],
                    errors="coerce",
                )

        display_cols = [
            "team",
            "trades",
            "wins",
            "losses",
            "even",
            "win_pct",
            "total_value_advantage",
            "avg_trade_advantage",
        ]

        display_cols = [
            c for c in display_cols
            if c in leaderboard.columns
        ]

        board = leaderboard[display_cols].copy()

        rename = {
            "team": "TEAM",
            "trades": "TRADES",
            "wins": "W",
            "losses": "L",
            "even": "EVEN",
            "win_pct": "WIN %",
            "total_value_advantage": "TOTAL VALUE +/-",
            "avg_trade_advantage": "AVG VALUE +/-",
        }

        board = board.rename(columns=rename)

        if "TOTAL VALUE +/-" in board.columns:
            board = board.sort_values(
                ["TOTAL VALUE +/-", "TRADES"],
                ascending=[False, False],
                kind="stable",
            )

        st.dataframe(
            board,
            use_container_width=True,
            hide_index=True,
            column_config={
                "WIN %": st.column_config.NumberColumn(
                    format="%.1f%%"
                ),
                "TOTAL VALUE +/-": st.column_config.NumberColumn(
                    format="%+.2f"
                ),
                "AVG VALUE +/-": st.column_config.NumberColumn(
                    format="%+.2f"
                ),
            },
        )

        st.caption(
            "Win percentage includes only trades classified with a winner; "
            "even trades are shown separately."
        )

        st.markdown("### League Superlatives")

        s1, s2, s3 = st.columns(3)

        eligible = leaderboard[
            leaderboard["decisive_trades"].fillna(0) > 0
        ].copy()

        if not eligible.empty:
            best_pct = eligible.sort_values(
                ["win_pct", "decisive_trades"],
                ascending=[False, False],
            ).iloc[0]

            s1.metric(
                "Best Trade Win %",
                best_pct["team"],
                f"{fmt_number(best_pct['win_pct'])}%",
            )

        if "total_value_advantage" in leaderboard.columns:
            value_king = leaderboard.sort_values(
                "total_value_advantage",
                ascending=False,
            ).iloc[0]

            s2.metric(
                "Most Total Value Gained",
                value_king["team"],
                fmt_signed(
                    value_king["total_value_advantage"],
                    2,
                ),
            )

        if "trades" in leaderboard.columns:
            most_active = leaderboard.sort_values(
                "trades",
                ascending=False,
            ).iloc[0]

            s3.metric(
                "Most Trades",
                most_active["team"],
                f"{int(most_active['trades'])} trades",
            )

        st.markdown("### Biggest Trade Wins")

        biggest = results[
            results["winner"].notna()
        ].copy()

        if not biggest.empty:
            biggest["winner_margin"] = pd.to_numeric(
                biggest["winner_margin"],
                errors="coerce",
            )

            biggest = biggest.sort_values(
                "winner_margin",
                ascending=False,
            ).head(10)

            cols = [
                "year",
                "winner",
                "loser",
                "winner_margin",
                "result_class",
                "trade_id",
            ]

            cols = [c for c in cols if c in biggest.columns]

            biggest_display = biggest[cols].rename(
                columns={
                    "year": "YEAR",
                    "winner": "WINNER",
                    "loser": "LOSER",
                    "winner_margin": "VALUE MARGIN",
                    "result_class": "RESULT",
                    "trade_id": "TRADE",
                }
            )

            st.dataframe(
                biggest_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "VALUE MARGIN":
                        st.column_config.NumberColumn(
                            format="+%.2f"
                        )
                },
            )


# ============================================================
# HISTORY
# ============================================================

with tab_history:

    st.subheader("Trade History")

    st.caption(
        "Lineup Impact measures the value acquired players produced "
        "above replacement level for their new team after the trade."
    )

    years = sorted(
        pd.to_numeric(
            results["year"],
            errors="coerce",
        )
        .dropna()
        .astype(int)
        .unique()
        .tolist(),
        reverse=True,
    )

    year_choice = st.selectbox(
        "Season",
        ["All Seasons"] + years,
        key="trade_history_year",
    )

    history = results.copy()

    if year_choice != "All Seasons":
        history = history[
            pd.to_numeric(
                history["year"],
                errors="coerce",
            ).eq(year_choice)
        ].copy()

    history["date"] = pd.to_datetime(
        history["date"],
        errors="coerce",
        utc=True,
    )

    history = history.sort_values(
        "date",
        ascending=False,
    )

    for _, row in history.iterrows():

        trade_id = str(row.get("trade_id", ""))

        date_text = (
            row["date"].strftime("%b %d, %Y")
            if pd.notna(row["date"])
            else str(row.get("year", ""))
        )

        winner = row.get("winner")
        result_class = row.get("result_class", "Even")

        if pd.notna(winner):
            result_text = (
                f"{result_class.upper()} — {winner} • "
                f"+{fmt_number(row.get('winner_margin'), 2)} "
                f"lineup-value advantage"
            )
        else:
            result_text = (
                f"{str(result_class).upper()} — "
                "No meaningful lineup-value advantage"
            )

        trade_player_rows = players[
            players["trade_id"]
            .astype(str)
            .eq(trade_id)
        ].copy()

        with st.expander(
            f"{date_text} — "
            f"{row.get('team_1', '')} ↔ "
            f"{row.get('team_2', '')} — "
            f"{result_class}"
        ):

            left, middle, right = st.columns(
                [5, 1, 5]
            )

            for column, team_key, player_key in [
                (
                    left,
                    "team_1",
                    "team_1_players",
                ),
                (
                    right,
                    "team_2",
                    "team_2_players",
                ),
            ]:

                team = row.get(team_key, "")

                acquired = trade_player_rows[
                    trade_player_rows[
                        "destination_team"
                    ]
                    .astype(str)
                    .eq(str(team))
                ].copy()

                with column:

                    st.markdown(
                        f"### {team}"
                    )

                    st.caption("RECEIVED")

                    if acquired.empty:
                        st.markdown(
                            f"**{row.get(player_key, '—')}**"
                        )

                        st.metric(
                            "Lineup Impact",
                            fmt_signed(
                                row.get(
                                    "team_1_value"
                                    if team_key == "team_1"
                                    else "team_2_value"
                                ),
                                2,
                            ),
                        )

                    else:

                        for player_num, (
                            _,
                            player,
                        ) in enumerate(
                            acquired.iterrows()
                        ):

                            if player_num:
                                st.markdown("---")

                            position = str(
                                player.get(
                                    "position",
                                    "",
                                )
                            ).strip()

                            player_heading = (
                                f"**{player['player']}**"
                                + (
                                    f" · {position}"
                                    if position
                                    and position != "nan"
                                    else ""
                                )
                            )

                            st.markdown(
                                player_heading
                            )

                            roster_weeks = int(
                                player.get(
                                    "roster_weeks",
                                    0,
                                )
                                or 0
                            )

                            starts = int(
                                player.get(
                                    "starts",
                                    0,
                                )
                                or 0
                            )

                            started_points = float(
                                player.get(
                                    "started_points",
                                    0,
                                )
                                or 0
                            )

                            points_per_start = float(
                                player.get(
                                    "points_per_start",
                                    0,
                                )
                                or 0
                            )

                            expected = float(
                                player.get(
                                    "expected_replacement_started_points",
                                    0,
                                )
                                or 0
                            )

                            starter_value = float(
                                player.get(
                                    "starter_value",
                                    0,
                                )
                                or 0
                            )

                            bench_value = float(
                                player.get(
                                    "bench_value",
                                    0,
                                )
                                or 0
                            )

                            trade_value = float(
                                player.get(
                                    "trade_value",
                                    0,
                                )
                                or 0
                            )

                            per_start = float(
                                player.get(
                                    "start_value_per_start",
                                    0,
                                )
                                or 0
                            )

                            st.caption(
                                f"{starts} starts / "
                                f"{roster_weeks} roster weeks"
                            )

                            p1, p2 = st.columns(2)

                            p1.metric(
                                "Starter Points",
                                fmt_number(
                                    started_points,
                                    1,
                                ),
                            )

                            p2.metric(
                                "Pts / Start",
                                fmt_number(
                                    points_per_start,
                                    1,
                                ),
                            )

                            st.markdown(
                                "**LINEUP IMPACT**"
                            )

                            impact1, impact2 = (
                                st.columns(2)
                            )

                            impact1.metric(
                                "Total Value",
                                fmt_signed(
                                    trade_value,
                                    2,
                                ),
                            )

                            impact2.metric(
                                "Value / Start",
                                fmt_signed(
                                    per_start,
                                    2,
                                ),
                            )

                            st.caption(
                                f"Expected replacement starter "
                                f"production: "
                                f"{expected:.1f} pts • "
                                f"Starter value above replacement: "
                                f"{starter_value:+.1f}"
                            )

                            if bench_value > 0:
                                st.caption(
                                    f"Bench/depth value: "
                                    f"+{bench_value:.1f}"
                                )

            with middle:
                st.markdown("### TRADE")

            st.divider()

            if pd.notna(winner):
                st.markdown(
                    f"### 🏆 {result_text}"
                )
            else:
                st.markdown(
                    f"### {result_text}"
                )


# ============================================================
# INDIVIDUAL TRADE BREAKDOWN
# ============================================================

with tab_trade:

    st.subheader("Trade Breakdown")

    trade_options = {
        trade_label(row): row["trade_id"]
        for _, row in results.sort_values(
            ["year", "date"],
            ascending=[False, False],
        ).iterrows()
    }

    selected_label = st.selectbox(
        "Select a trade",
        list(trade_options.keys()),
        key="selected_trade",
    )

    selected_id = trade_options[selected_label]

    trade = results[
        results["trade_id"].astype(str)
        .eq(str(selected_id))
    ].iloc[0]

    trade_sides = sides[
        sides["trade_id"].astype(str)
        .eq(str(selected_id))
    ].copy()

    trade_players = players[
        players["trade_id"].astype(str)
        .eq(str(selected_id))
    ].copy()

    st.markdown(
        f"### {trade.get('team_1', '')} ↔ "
        f"{trade.get('team_2', '')}"
    )

    if pd.notna(trade.get("winner")):
        st.success(
            f"{trade['winner']} won this trade by "
            f"{fmt_number(trade.get('winner_margin'), 2)} "
            f"value points — {trade.get('result_class', '')}."
        )
    else:
        st.info(
            f"This trade is classified as "
            f"{trade.get('result_class', 'Even')}."
        )

    if not trade_sides.empty:

        side_columns = st.columns(
            len(trade_sides)
        )

        for column, (_, side) in zip(
            side_columns,
            trade_sides.iterrows(),
        ):
            with column:
                st.markdown(
                    f"#### {side['team']} RECEIVED"
                )
                st.write(
                    side.get(
                        "players_received",
                        "",
                    )
                )

                st.metric(
                    "Trade Value",
                    fmt_number(
                        side.get("trade_value"),
                        2,
                    ),
                )

                a, b = st.columns(2)

                a.metric(
                    "Starts",
                    int(side.get("starts", 0)),
                )

                b.metric(
                    "Started Pts",
                    fmt_number(
                        side.get("started_points"),
                        1,
                    ),
                )

                st.caption(
                    "Starter value: "
                    + fmt_number(
                        side.get("starter_value"),
                        2,
                    )
                    + " • Bench value: "
                    + fmt_number(
                        side.get("bench_value"),
                        2,
                    )
                )

    st.markdown("### Player Contributions")

    if trade_players.empty:
        st.info(
            "No player-level value records are available "
            "for this trade."
        )
    else:
        player_cols = [
            "player",
            "source_team",
            "destination_team",
            "position",
            "roster_weeks",
            "starts",
            "started_points",
            "starter_value",
            "bench_value",
            "trade_value",
        ]

        player_cols = [
            c for c in player_cols
            if c in trade_players.columns
        ]

        detail = trade_players[
            player_cols
        ].copy()

        detail = detail.rename(
            columns={
                "player": "PLAYER",
                "source_team": "FROM",
                "destination_team": "TO",
                "position": "POS",
                "roster_weeks": "ROSTER WKS",
                "starts": "STARTS",
                "started_points": "STARTED PTS",
                "starter_value": "STARTER VALUE",
                "bench_value": "BENCH VALUE",
                "trade_value": "TRADE VALUE",
            }
        )

        st.dataframe(
            detail,
            use_container_width=True,
            hide_index=True,
            column_config={
                "STARTED PTS":
                    st.column_config.NumberColumn(
                        format="%.1f"
                    ),
                "STARTER VALUE":
                    st.column_config.NumberColumn(
                        format="%.2f"
                    ),
                "BENCH VALUE":
                    st.column_config.NumberColumn(
                        format="%.2f"
                    ),
                "TRADE VALUE":
                    st.column_config.NumberColumn(
                        format="%.2f"
                    ),
            },
        )


# ============================================================
# FRANCHISE PROFILE
# ============================================================

with tab_team:

    st.subheader("Franchise Trade Profiles")

    if franchise.empty:
        st.info(
            "Franchise trade summary is unavailable."
        )
    else:

        teams = sorted(
            franchise["team"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_team = st.selectbox(
            "Franchise",
            teams,
            key="trade_franchise",
        )

        team_summary = franchise[
            franchise["team"].eq(selected_team)
        ].iloc[0]

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Trades",
            int(team_summary["trades"]),
        )

        c2.metric(
            "Record",
            f"{int(team_summary['wins'])}-"
            f"{int(team_summary['losses'])}-"
            f"{int(team_summary['even'])}",
        )

        c3.metric(
            "Trade Win %",
            (
                f"{float(team_summary['win_pct']):.1f}%"
                if pd.notna(team_summary["win_pct"])
                else "—"
            ),
        )

        c4.metric(
            "Total Value +/-",
            fmt_signed(
                team_summary[
                    "total_value_advantage"
                ],
                2,
            ),
        )

        left, right = st.columns(2)

        with left:
            st.markdown("#### Best Trade")
            st.write(
                team_summary.get(
                    "best_trade",
                    "—",
                )
            )
            st.metric(
                "Value Advantage",
                fmt_signed(
                    team_summary.get(
                        "best_trade_margin"
                    ),
                    2,
                ),
            )

        with right:
            st.markdown("#### Worst Trade")
            st.write(
                team_summary.get(
                    "worst_trade",
                    "—",
                )
            )
            st.metric(
                "Value Advantage",
                fmt_signed(
                    team_summary.get(
                        "worst_trade_margin"
                    ),
                    2,
                ),
            )

        st.markdown("### Complete Trade History")

        team_history = results[
            results["team_1"].eq(selected_team)
            | results["team_2"].eq(selected_team)
        ].copy()

        team_rows = []

        for _, trade in team_history.iterrows():

            if trade["team_1"] == selected_team:
                opponent = trade["team_2"]
                received = trade["team_1_players"]
                sent = trade["team_2_players"]
                team_value = trade["team_1_value"]
                opp_value = trade["team_2_value"]
            else:
                opponent = trade["team_1"]
                received = trade["team_2_players"]
                sent = trade["team_1_players"]
                team_value = trade["team_2_value"]
                opp_value = trade["team_1_value"]

            if trade.get("winner") == selected_team:
                verdict = "Win"
            elif trade.get("loser") == selected_team:
                verdict = "Loss"
            else:
                verdict = "Even"

            team_rows.append(
                {
                    "YEAR": trade["year"],
                    "TRADE": trade["trade_id"],
                    "OPPONENT": opponent,
                    "PLAYERS RECEIVED": received,
                    "PLAYERS SENT": sent,
                    "VALUE": team_value,
                    "OPP VALUE": opp_value,
                    "VALUE +/-": (
                        float(team_value)
                        - float(opp_value)
                    ),
                    "RESULT": verdict,
                }
            )

        history_df = pd.DataFrame(
            team_rows
        )

        if not history_df.empty:
            history_df = history_df.sort_values(
                ["YEAR", "TRADE"],
                ascending=[False, False],
            )

            st.dataframe(
                history_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "VALUE":
                        st.column_config.NumberColumn(
                            format="%.2f"
                        ),
                    "OPP VALUE":
                        st.column_config.NumberColumn(
                            format="%.2f"
                        ),
                    "VALUE +/-":
                        st.column_config.NumberColumn(
                            format="%+.2f"
                        ),
                },
            )


# ============================================================
# METHODOLOGY
# ============================================================

st.divider()

with st.expander("How trade value is calculated"):
    st.markdown(
        """
Trade value measures what each acquired player actually produced
for the team that acquired him after the trade.

The model emphasizes **replacement-adjusted starter production**.
Points generated while a player was started are compared with the
production expected from replacement-level players at the same
position. Bench contribution is tracked separately and receives
less weight than useful starter production.

This means a player does not automatically create trade value simply
by accumulating fantasy points. The analysis rewards production that
actually improved the acquiring team's lineup.

Trades with sufficiently large differences between the two sides are
classified with a winner and loser. Trades without a meaningful
difference are classified as even.
"""
    )

st.caption(
    "Trade data collected from Yahoo Fantasy API • "
    "Post-trade value calculated from historical league lineup data"
)
