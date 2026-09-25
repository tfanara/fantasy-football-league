from pathlib import Path
import json
import xml.etree.ElementTree as ET

import pandas as pd
from yahoofantasy import Context

from season_config import (
    CURRENT_SEASON,
    YAHOO_LEAGUE_IDS,
)
from team_aliases import canonical_team


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "data" / "trades"

START_YEAR = 2018

NS = {
    "f": "http://fantasysports.yahooapis.com/fantasy/v2/base.rng"
}


def fail(message):
    raise RuntimeError(message)


def parse_xml(payload):
    return ET.fromstring(payload)


def text(element, path, default=None):
    found = element.find(path, NS)
    if found is None or found.text is None:
        return default
    value = found.text.strip()
    return value if value else default


def as_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def save_json(df, path):
    records = df.where(pd.notna(df), None).to_dict("records")
    path.write_text(
        json.dumps(
            records,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def discover_game_key(ctx, year):
    """
    Ask Yahoo for the NFL game key corresponding to a season.
    """
    payload = ctx.make_request(
        f"games;game_codes=nfl;seasons={year}"
    )

    root = parse_xml(payload)

    game = root.find(".//f:game", NS)
    if game is None:
        fail(
            f"{year}: Yahoo did not return an NFL game object."
        )

    game_key = text(game, "f:game_key")

    if not game_key:
        fail(
            f"{year}: Yahoo NFL game key could not be determined."
        )

    return game_key


def collect_year(ctx, year):
    """
    Return:
      trades      — one row per Yahoo trade
      assets      — one row per player movement within a trade
    """

    if year not in YAHOO_LEAGUE_IDS:
        fail(
            f"{year}: no Yahoo league ID exists in season_config.py"
        )

    game_key = discover_game_key(ctx, year)

    league_id = YAHOO_LEAGUE_IDS[year]
    league_key = f"{game_key}.l.{league_id}"

    print()
    print("=" * 88)
    print(f"{year}")
    print("=" * 88)
    print(f"Yahoo game key:   {game_key}")
    print(f"Yahoo league key: {league_key}")

    payload = ctx.make_request(
        f"league/{league_key}/transactions"
    )

    # Preserve the complete Yahoo response for auditing.
    raw_dir = OUT_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    raw_file = raw_dir / f"{year}_transactions.xml"
    raw_file.write_text(
        payload,
        encoding="utf-8",
    )

    root = parse_xml(payload)

    trade_rows = []
    asset_rows = []

    transaction_count = 0
    trade_count = 0

    for transaction in root.findall(
        ".//f:transaction",
        NS,
    ):
        transaction_count += 1

        transaction_id = text(
            transaction,
            "f:transaction_id",
        )

        transaction_key = text(
            transaction,
            "f:transaction_key",
        )

        transaction_type = (
            text(
                transaction,
                "f:type",
                "",
            )
            or ""
        ).strip().lower()

        status = (
            text(
                transaction,
                "f:status",
                "",
            )
            or ""
        ).strip().lower()

        timestamp = as_int(
            text(
                transaction,
                "f:timestamp",
            )
        )

        # Only successful Yahoo trades belong in the
        # canonical trade ledger.
        if transaction_type != "trade":
            continue

        if status != "successful":
            continue

        players = transaction.findall(
            "f:players/f:player",
            NS,
        )

        if not players:
            fail(
                f"{year}: trade {transaction_id} "
                "contains no player assets."
            )

        trade_count += 1

        trade_id = (
            f"{year}-"
            f"{transaction_id}"
        )

        date = (
            pd.to_datetime(
                timestamp,
                unit="s",
                utc=True,
            )
            .tz_convert(
                "America/New_York"
            )
            .isoformat()
            if timestamp is not None
            else None
        )

        participating_teams = set()
        asset_count = 0

        for player in players:
            player_name = text(
                player,
                "f:name/f:full",
                "",
            )

            player_key = text(
                player,
                "f:player_key",
            )

            player_id = text(
                player,
                "f:player_id",
            )

            transaction_data = player.find(
                "f:transaction_data",
                NS,
            )

            if transaction_data is None:
                fail(
                    f"{year}: trade {transaction_id}, "
                    f"player {player_name!r} has no "
                    "transaction_data."
                )

            action = (
                text(
                    transaction_data,
                    "f:type",
                    "",
                )
                or ""
            ).strip().lower()

            source_type = text(
                transaction_data,
                "f:source_type",
            )

            destination_type = text(
                transaction_data,
                "f:destination_type",
            )

            source_team_yahoo = text(
                transaction_data,
                "f:source_team_name",
            )

            destination_team_yahoo = text(
                transaction_data,
                "f:destination_team_name",
            )

            if (
                not source_team_yahoo
                or not destination_team_yahoo
            ):
                fail(
                    f"{year}: trade {transaction_id}, "
                    f"player {player_name!r} is missing "
                    "source or destination team."
                )

            source_team = canonical_team(
                source_team_yahoo
            )

            destination_team = canonical_team(
                destination_team_yahoo
            )

            if source_team == destination_team:
                fail(
                    f"{year}: trade {transaction_id}, "
                    f"player {player_name!r} has identical "
                    "source and destination franchises."
                )

            participating_teams.add(
                source_team
            )
            participating_teams.add(
                destination_team
            )

            asset_count += 1

            asset_rows.append({
                "trade_id": trade_id,
                "year": year,
                "transaction_id": as_int(
                    transaction_id
                ),
                "transaction_key": transaction_key,
                "timestamp": timestamp,
                "date": date,
                "player": player_name,
                "player_key": player_key,
                "player_id": as_int(
                    player_id
                ),
                "action": action,
                "source_type": source_type,
                "destination_type": destination_type,
                "source_team_yahoo": source_team_yahoo,
                "destination_team_yahoo": destination_team_yahoo,
                "source_team": source_team,
                "destination_team": destination_team,
                "status": status,
                "source": "yahoo_fantasy_api",
            })

        if len(participating_teams) < 2:
            fail(
                f"{year}: trade {transaction_id} "
                "contains fewer than two franchises."
            )

        trade_rows.append({
            "trade_id": trade_id,
            "year": year,
            "transaction_id": as_int(
                transaction_id
            ),
            "transaction_key": transaction_key,
            "timestamp": timestamp,
            "date": date,
            "status": status,
            "team_count": len(
                participating_teams
            ),
            "asset_count": asset_count,
            "teams": " | ".join(
                sorted(
                    participating_teams
                )
            ),
            "source": "yahoo_fantasy_api",
        })

    print(
        f"Yahoo transaction objects: "
        f"{transaction_count}"
    )
    print(
        f"Successful trades:          "
        f"{trade_count}"
    )

    return (
        pd.DataFrame(trade_rows),
        pd.DataFrame(asset_rows),
    )


def validate(trades, assets):
    print()
    print("=" * 88)
    print("VALIDATING TRADE DATA")
    print("=" * 88)

    if trades.empty:
        fail(
            "No successful Yahoo trades were collected."
        )

    if assets.empty:
        fail(
            "Trades were found but no trade assets "
            "were collected."
        )

    # One canonical row per Yahoo trade.
    if trades["trade_id"].duplicated().any():
        dupes = (
            trades.loc[
                trades["trade_id"].duplicated(
                    keep=False
                ),
                "trade_id",
            ]
            .tolist()
        )

        fail(
            f"Duplicate trade IDs detected: {dupes}"
        )

    # Every asset must belong to a known trade.
    unknown = set(
        assets["trade_id"]
    ) - set(
        trades["trade_id"]
    )

    if unknown:
        fail(
            "Trade assets reference unknown trades: "
            f"{sorted(unknown)}"
        )

    # Every trade should have at least two player assets.
    asset_counts = (
        assets.groupby(
            "trade_id"
        )
        .size()
    )

    bad_asset_counts = (
        asset_counts[
            asset_counts < 2
        ]
    )

    if not bad_asset_counts.empty:
        fail(
            "Trades with fewer than two player assets: "
            f"{bad_asset_counts.to_dict()}"
        )

    # Confirm each trade has at least two canonical teams.
    team_counts = {}

    for trade_id, group in assets.groupby(
        "trade_id"
    ):
        teams = set(
            group["source_team"]
        ) | set(
            group["destination_team"]
        )

        team_counts[trade_id] = len(
            teams
        )

    bad_teams = {
        trade_id: count
        for trade_id, count
        in team_counts.items()
        if count < 2
    }

    if bad_teams:
        fail(
            "Trades with fewer than two teams: "
            f"{bad_teams}"
        )

    # Historical regression from our API probe.
    #
    # We already established that 2018-2025 contains
    # 30 successful trades. If all eight completed
    # historical seasons are represented, protect
    # against silently losing any of them.
    historical = trades[
        trades["year"].between(
            2018,
            2025,
        )
    ]

    historical_years = set(
        historical["year"]
        .astype(int)
        .unique()
    )

    expected_years = set(
        range(
            2018,
            2026,
        )
    )

    if historical_years == expected_years:
        if len(historical) != 30:
            fail(
                "Historical trade regression failed: "
                f"expected 30 successful trades from "
                f"2018-2025, found {len(historical)}."
            )

        print(
            "[PASS] Historical regression: "
            "30 successful trades from 2018-2025"
        )

    print(
        f"[PASS] Canonical trades: "
        f"{len(trades)}"
    )

    print(
        f"[PASS] Trade asset movements: "
        f"{len(assets)}"
    )

    print(
        "[PASS] Every trade contains at least "
        "two franchises"
    )

    print(
        "[PASS] Every trade contains at least "
        "two player assets"
    )


def main():
    print("=" * 88)
    print("COLLECTING YAHOO TRADE HISTORY")
    print("=" * 88)

    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ctx = Context()

    all_trades = []
    all_assets = []

    # 2017 intentionally excluded.
    #
    # Historical Yahoo trade collection begins with
    # the 2018 league season.
    end_year = min(
        CURRENT_SEASON,
        max(YAHOO_LEAGUE_IDS),
    )

    for year in range(
        START_YEAR,
        end_year + 1,
    ):
        if year not in YAHOO_LEAGUE_IDS:
            print(
                f"[WARN] {year}: no Yahoo league ID; "
                "skipping"
            )
            continue

        try:
            trades, assets = collect_year(
                ctx,
                year,
            )

        except Exception as exc:
            # Current season may legitimately have no
            # trade data yet, but historical seasons
            # should not silently disappear.
            if year == CURRENT_SEASON:
                print(
                    f"[WARN] {year}: Yahoo trade "
                    f"collection unavailable: {exc}"
                )
                continue

            raise

        if not trades.empty:
            all_trades.append(
                trades
            )

        if not assets.empty:
            all_assets.append(
                assets
            )

    if not all_trades:
        fail(
            "No Yahoo trades were collected "
            "for any season."
        )

    trades = pd.concat(
        all_trades,
        ignore_index=True,
    )

    assets = pd.concat(
        all_assets,
        ignore_index=True,
    )

    trades = trades.sort_values(
        [
            "year",
            "timestamp",
            "transaction_id",
        ],
        kind="stable",
    ).reset_index(
        drop=True
    )

    assets = assets.sort_values(
        [
            "year",
            "timestamp",
            "transaction_id",
            "source_team",
            "player",
        ],
        kind="stable",
    ).reset_index(
        drop=True
    )

    validate(
        trades,
        assets,
    )

    trades_csv = (
        OUT_DIR
        / "trades.csv"
    )

    trades_json = (
        OUT_DIR
        / "trades.json"
    )

    assets_csv = (
        OUT_DIR
        / "trade_assets.csv"
    )

    assets_json = (
        OUT_DIR
        / "trade_assets.json"
    )

    trades.to_csv(
        trades_csv,
        index=False,
    )

    save_json(
        trades,
        trades_json,
    )

    assets.to_csv(
        assets_csv,
        index=False,
    )

    save_json(
        assets,
        assets_json,
    )

    print()
    print("=" * 88)
    print("TRADE HISTORY BY SEASON")
    print("=" * 88)

    summary = (
        trades.groupby("year")
        .agg(
            trades=(
                "trade_id",
                "size",
            ),
            assets=(
                "asset_count",
                "sum",
            ),
        )
        .reset_index()
    )

    print(
        summary.to_string(
            index=False
        )
    )

    print()
    print("=" * 88)
    print("FILES WRITTEN")
    print("=" * 88)

    for path in (
        trades_csv,
        trades_json,
        assets_csv,
        assets_json,
    ):
        print(
            path.relative_to(
                ROOT
            )
        )

    print()
    print(
        "TRADE COLLECTION COMPLETE"
    )


if __name__ == "__main__":
    main()
