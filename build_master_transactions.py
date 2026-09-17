from pathlib import Path
import pandas as pd

from season_config import CURRENT_SEASON


BASE_DIR = Path(__file__).resolve().parent

MASTER_FILE = BASE_DIR / "data" / "transactions" / "all_transactions.csv"
MASTER_JSON = BASE_DIR / "data" / "transactions" / "all_transactions.json"

CURRENT_FILE = (
    BASE_DIR
    / "data"
    / str(CURRENT_SEASON)
    / "transactions.csv"
)

CANONICAL_COLUMNS = [
    "year",
    "date",
    "team",
    "added_player",
    "acquisition_type",
    "dropped_player",
    "raw_text",
]


def clean_string(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_current_transactions(df):
    """
    Convert the API current-season transaction schema to the historical
    canonical transaction schema used by downstream analysis.
    """
    required = {
        "year",
        "date",
        "team",
        "added_player",
        "acquisition_type",
        "dropped_player",
    }

    missing = required - set(df.columns)

    if missing:
        raise RuntimeError(
            "Current-season transaction file is missing required columns: "
            + ", ".join(sorted(missing))
        )

    out = pd.DataFrame()

    out["year"] = pd.to_numeric(
        df["year"],
        errors="raise",
    ).astype(int)

    out["date"] = df["date"].apply(clean_string)
    out["team"] = df["team"].apply(clean_string)
    out["added_player"] = df["added_player"].apply(clean_string)
    out["acquisition_type"] = df["acquisition_type"].apply(clean_string)
    out["dropped_player"] = df["dropped_player"].apply(clean_string)

    # Preserve a readable audit description without requiring downstream
    # code to understand the richer Yahoo API schema.
    def make_raw_text(row):
        parts = []

        if row["added_player"]:
            parts.append(
                f"ADD {row['added_player']} "
                f"({row['acquisition_type'] or 'unknown'})"
            )

        if row["dropped_player"]:
            parts.append(
                f"DROP {row['dropped_player']}"
            )

        return " | ".join(parts)

    out["raw_text"] = out.apply(make_raw_text, axis=1)

    return out[CANONICAL_COLUMNS]


def main():
    print("=" * 80)
    print("BUILDING MASTER TRANSACTIONS")
    print("=" * 80)
    print()

    if not MASTER_FILE.exists():
        raise FileNotFoundError(
            f"Historical transaction master not found: {MASTER_FILE}"
        )

    if not CURRENT_FILE.exists():
        raise FileNotFoundError(
            f"Current-season API transaction file not found: {CURRENT_FILE}"
        )

    historical = pd.read_csv(
        MASTER_FILE,
        dtype=str,
        keep_default_na=False,
    )

    current_raw = pd.read_csv(
        CURRENT_FILE,
        dtype=str,
        keep_default_na=False,
    )

    missing_master = set(CANONICAL_COLUMNS) - set(historical.columns)

    if missing_master:
        raise RuntimeError(
            "Historical transaction master is missing columns: "
            + ", ".join(sorted(missing_master))
        )

    historical = historical[CANONICAL_COLUMNS].copy()

    historical["year"] = pd.to_numeric(
        historical["year"],
        errors="coerce",
    )

    if historical["year"].isna().any():
        raise RuntimeError(
            "Historical transaction master contains invalid year values."
        )

    historical["year"] = historical["year"].astype(int)

    current = normalize_current_transactions(current_raw)

    current = current[
        current["year"] == int(CURRENT_SEASON)
    ].copy()

    if current.empty:
        print(
            f"[WARN] No successful player transactions found for "
            f"{CURRENT_SEASON}."
        )

    # Critical behavior:
    # keep every historical season exactly as-is and replace only the
    # current season with the authoritative API-derived records.
    historical_without_current = historical[
        historical["year"] != int(CURRENT_SEASON)
    ].copy()

    combined = pd.concat(
        [
            historical_without_current,
            current,
        ],
        ignore_index=True,
    )

    # Prevent duplicate normalized transaction rows.
    dedupe_columns = [
        "year",
        "date",
        "team",
        "added_player",
        "acquisition_type",
        "dropped_player",
    ]

    combined = combined.drop_duplicates(
        subset=dedupe_columns,
        keep="last",
    )

    combined = combined.sort_values(
        ["year", "date", "team"],
        kind="stable",
    ).reset_index(drop=True)

    MASTER_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    combined.to_csv(
        MASTER_FILE,
        index=False,
    )

    combined.to_json(
        MASTER_JSON,
        orient="records",
        indent=2,
        force_ascii=False,
    )

    current_count = int(
        (combined["year"] == int(CURRENT_SEASON)).sum()
    )

    historical_count = int(
        (combined["year"] < int(CURRENT_SEASON)).sum()
    )

    print(
        f"[PASS] Historical transactions preserved: "
        f"{historical_count:,}"
    )

    print(
        f"[PASS] {CURRENT_SEASON} API transactions: "
        f"{current_count:,}"
    )

    print(
        f"[PASS] Master transactions: "
        f"{len(combined):,}"
    )

    print()
    print(f"[PASS] Wrote {MASTER_FILE.relative_to(BASE_DIR)}")
    print(f"[PASS] Wrote {MASTER_JSON.relative_to(BASE_DIR)}")

    print()
    print("MASTER TRANSACTION BUILD COMPLETE")


if __name__ == "__main__":
    main()
