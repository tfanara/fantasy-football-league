from __future__ import annotations

from pathlib import Path
import json
import re
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DRAFT_FILE = BASE_DIR / 'data' / 'drafts' / 'all_drafts.csv'
TRANSACTION_FILE = BASE_DIR / 'data' / 'transactions' / 'all_transactions.csv'
KEEPER_HISTORY_FILE = BASE_DIR / 'data' / 'keepers' / 'keeper_history.csv'
WEEKLY_CANDIDATES = [
    BASE_DIR / 'data' / 'matchups' / 'player_week_stats' / 'all_weekly_lineups_2017_2025.csv',
    BASE_DIR / 'data' / 'matchups' / 'player_week_stats' / 'all_weekly_lineups_2018_2025.csv',
]
OUTPUT_DIR = BASE_DIR / 'data' / 'keepers'
OWNERSHIP_CSV = OUTPUT_DIR / 'end_of_season_ownership.csv'
OWNERSHIP_JSON = OUTPUT_DIR / 'end_of_season_ownership.json'
AUDIT_CSV = OUTPUT_DIR / 'keeper_end_of_season_audit.csv'
AUDIT_JSON = OUTPUT_DIR / 'keeper_end_of_season_audit.json'

TEAM_ALIASES = {
    'PickUpYourBratsMalle': 'ThreatLevelMidnight',
    'Little Red Fournette': 'Post Mahomes',
    'Ur The Best Bellows': 'Joe Mantegna',
    'You Better Park It': 'Buttermilk Puuump',
    'Buttermilk Pump': 'Buttermilk Puuump',
}


def clean_text(value) -> str:
    if pd.isna(value):
        return ''
    return re.sub(r'\s+', ' ', str(value)).strip()


def canonical_team(value) -> str:
    value = clean_text(value)
    return TEAM_ALIASES.get(value, value)


def banner(text: str) -> None:
    print('\n' + '=' * 88)
    print(text)
    print('=' * 88)


def require(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f'Required file not found: {path}')


def load_drafts() -> pd.DataFrame:
    require(DRAFT_FILE)
    df = pd.read_csv(DRAFT_FILE)
    missing = {'year', 'team', 'player'} - set(df.columns)
    if missing:
        raise ValueError(f'Draft file missing columns: {sorted(missing)}')
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df = df.dropna(subset=['year']).copy()
    df['year'] = df['year'].astype(int)
    df['team'] = df['team'].apply(canonical_team)
    df['player'] = df['player'].apply(clean_text)
    return df


def load_transactions() -> pd.DataFrame:
    if not TRANSACTION_FILE.exists():
        return pd.DataFrame(columns=['year','date','team','added_player','dropped_player','acquisition_type'])
    df = pd.read_csv(TRANSACTION_FILE)
    for col in ['year','team','added_player','dropped_player','date','acquisition_type']:
        if col not in df.columns:
            df[col] = pd.NA
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df = df.dropna(subset=['year']).copy()
    df['year'] = df['year'].astype(int)
    df['team'] = df['team'].apply(canonical_team)
    df['added_player'] = df['added_player'].apply(clean_text)
    df['dropped_player'] = df['dropped_player'].apply(clean_text)
    return df


def load_weekly() -> pd.DataFrame:
    path = next((p for p in WEEKLY_CANDIDATES if p.exists()), None)
    if path is None:
        return pd.DataFrame()
    df = pd.read_csv(path)
    missing = {'year','week','fantasy_team','player'} - set(df.columns)
    if missing:
        raise ValueError(f'Weekly lineup file missing columns: {sorted(missing)}')
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df['week'] = pd.to_numeric(df['week'], errors='coerce')
    df = df.dropna(subset=['year','week']).copy()
    df['year'] = df['year'].astype(int)
    df['week'] = df['week'].astype(int)
    df['fantasy_team'] = df['fantasy_team'].apply(canonical_team)
    df['player'] = df['player'].apply(clean_text)
    return df


MONTH = {m:i for i,m in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], 1)}


def tx_sort_key(date_text: str, index: int):
    text = clean_text(date_text)
    m = re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s+(\d{1,2}):(\d{2})\s*(am|pm)$', text, re.I)
    if not m:
        return (13,32,24,60,index)
    mon, day, hour, minute, ampm = m.groups()
    hour = int(hour)
    if ampm.lower() == 'pm' and hour != 12:
        hour += 12
    elif ampm.lower() == 'am' and hour == 12:
        hour = 0
    return (MONTH[mon.title()], int(day), hour, int(minute), index)


def reconstruct_from_draft_transactions(drafts: pd.DataFrame, tx: pd.DataFrame) -> pd.DataFrame:
    rows = []
    tx_years = set(tx['year'].unique()) if not tx.empty else set()
    for year in sorted(drafts['year'].unique()):
        owner = {}
        d = drafts[drafts['year'] == year]
        for _, r in d.iterrows():
            player, team = clean_text(r['player']), canonical_team(r['team'])
            if player and team:
                owner[player] = team

        if year in tx_years:
            t = tx[tx['year'] == year].copy().reset_index(drop=True)
            t['_sort'] = [tx_sort_key(r.get('date',''), i) for i,(_,r) in enumerate(t.iterrows())]
            t = t.sort_values('_sort')
            for _, r in t.iterrows():
                team = canonical_team(r['team'])
                dropped = clean_text(r['dropped_player'])
                added = clean_text(r['added_player'])
                if dropped and owner.get(dropped) == team:
                    owner.pop(dropped, None)
                if added:
                    owner[added] = team
            method = 'Draft + Transactions'
        else:
            method = 'Draft Only'

        for player, final_owner in owner.items():
            rows.append({'year': int(year), 'player': player, 'tx_final_owner': final_owner, 'tx_method': method})
    return pd.DataFrame(rows)


def final_week_snapshot(weekly: pd.DataFrame) -> pd.DataFrame:
    if weekly.empty:
        return pd.DataFrame(columns=['year','player','snapshot_owner','snapshot_week','snapshot_owner_count'])
    rows = []
    for year, ydf in weekly.groupby('year'):
        week = int(ydf['week'].max())
        final = ydf[(ydf['week'] == week) & ydf['player'].ne('') & ydf['player'].ne('(Empty)')].copy()
        grouped = final.groupby('player')['fantasy_team'].agg(lambda s: sorted(set(s)))
        for player, owners in grouped.items():
            rows.append({
                'year': int(year),
                'player': player,
                'snapshot_owner': owners[0] if len(owners) == 1 else 'MULTIPLE: ' + ' | '.join(owners),
                'snapshot_week': week,
                'snapshot_owner_count': len(owners),
            })
    return pd.DataFrame(rows)


def build_ownership(drafts: pd.DataFrame, tx: pd.DataFrame, weekly: pd.DataFrame) -> pd.DataFrame:
    recon = reconstruct_from_draft_transactions(drafts, tx)
    snap = final_week_snapshot(weekly)
    keys = pd.concat([recon[['year','player']], snap[['year','player']]], ignore_index=True).drop_duplicates()
    work = keys.merge(recon, on=['year','player'], how='left').merge(snap, on=['year','player'], how='left')
    tx_years = set(tx['year'].unique()) if not tx.empty else set()

    final_owner, confidence, evidence = [], [], []
    for _, r in work.iterrows():
        year = int(r['year'])
        tx_owner = clean_text(r.get('tx_final_owner'))
        snap_owner = clean_text(r.get('snapshot_owner'))
        snap_unique = snap_owner and not snap_owner.startswith('MULTIPLE:')

        if year not in tx_years and snap_unique:
            final_owner.append(snap_owner)
            confidence.append('Snapshot Fallback — No Transactions')
            evidence.append(f'Final regular-season roster snapshot (Week {int(r["snapshot_week"])})')
        elif tx_owner and snap_unique and tx_owner == snap_owner:
            final_owner.append(tx_owner)
            confidence.append('Verified Agreement')
            evidence.append(f'Draft + transactions agrees with Week {int(r["snapshot_week"])} roster snapshot')
        elif tx_owner:
            final_owner.append(tx_owner)
            confidence.append('Transaction Primary — Snapshot Differs' if snap_owner else 'Transaction Reconstruction')
            evidence.append(f'Draft + transactions; snapshot owner={snap_owner or "none"}')
        elif snap_unique:
            final_owner.append(snap_owner)
            confidence.append('Snapshot Only')
            evidence.append(f'Final regular-season roster snapshot (Week {int(r["snapshot_week"])})')
        else:
            final_owner.append('')
            confidence.append('Unresolved')
            evidence.append('Ownership unresolved')

    work['final_owner'] = [canonical_team(x) for x in final_owner]
    work['ownership_confidence'] = confidence
    work['ownership_evidence'] = evidence
    work = work[work['final_owner'].ne('')].copy()
    return work[['year','player','final_owner','ownership_confidence','ownership_evidence','snapshot_owner','snapshot_week']].sort_values(['year','final_owner','player']).reset_index(drop=True)


def audit_keepers(ownership: pd.DataFrame) -> pd.DataFrame:
    if not KEEPER_HISTORY_FILE.exists():
        return pd.DataFrame()
    k = pd.read_csv(KEEPER_HISTORY_FILE)
    missing = {'year','team','player'} - set(k.columns)
    if missing:
        raise ValueError(f'Keeper history missing columns: {sorted(missing)}')
    k['year'] = pd.to_numeric(k['year'], errors='coerce')
    k = k.dropna(subset=['year']).copy()
    k['year'] = k['year'].astype(int)
    k['team'] = k['team'].apply(canonical_team)
    k['player'] = k['player'].apply(clean_text)
    k['prior_season'] = k['year'] - 1

    prior = ownership.rename(columns={
        'year':'prior_season',
        'final_owner':'prior_season_end_owner',
        'ownership_confidence':'prior_ownership_confidence',
        'ownership_evidence':'prior_ownership_evidence',
    })[['prior_season','player','prior_season_end_owner','prior_ownership_confidence','prior_ownership_evidence']]

    audit = k.merge(prior, on=['prior_season','player'], how='left')
    def status(r):
        owner = canonical_team(r.get('prior_season_end_owner'))
        if not owner:
            return 'Ownership Unresolved'
        if owner == canonical_team(r['team']):
            return 'Eligible — Held at End of Prior Season'
        return 'INELIGIBLE — Different End-of-Season Owner'
    audit['end_of_season_eligibility'] = audit.apply(status, axis=1)
    audit['end_of_season_eligible'] = audit['end_of_season_eligibility'].eq('Eligible — Held at End of Prior Season')
    preferred = ['year','team','player','prior_season','prior_season_end_owner','end_of_season_eligible','end_of_season_eligibility','prior_ownership_confidence','prior_ownership_evidence','round_kept_in','keeper_status','acquisition_basis','rule_status']
    return audit[[c for c in preferred if c in audit.columns]].sort_values(['year','team','player']).reset_index(drop=True)


def write_json(df: pd.DataFrame, path: Path):
    path.write_text(json.dumps(df.where(pd.notna(df), None).to_dict(orient='records'), indent=2, ensure_ascii=False))


def main():
    banner('BUILDING END-OF-SEASON KEEPER OWNERSHIP')
    drafts = load_drafts()
    tx = load_transactions()
    weekly = load_weekly()
    print(f'Draft selections: {len(drafts):,}')
    print(f'Transactions: {len(tx):,}')
    print(f'Weekly roster rows: {len(weekly):,}' if not weekly.empty else 'Weekly roster rows: not available')

    ownership = build_ownership(drafts, tx, weekly)
    if ownership.empty:
        raise RuntimeError('Ownership build produced no rows.')
    dupes = ownership.groupby(['year','player'])['final_owner'].nunique()
    if (dupes > 1).any():
        raise RuntimeError('Multiple final owners detected:\n' + dupes[dupes > 1].to_string())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ownership.to_csv(OWNERSHIP_CSV, index=False)
    write_json(ownership, OWNERSHIP_JSON)

    banner('OWNERSHIP SUMMARY')
    print(f'Ownership rows: {len(ownership):,}')
    print(ownership['ownership_confidence'].value_counts(dropna=False).to_string())

    audit = audit_keepers(ownership)
    if not audit.empty:
        audit.to_csv(AUDIT_CSV, index=False)
        write_json(audit, AUDIT_JSON)
        banner('HISTORICAL KEEPER ELIGIBILITY AUDIT')
        print(audit['end_of_season_eligibility'].value_counts(dropna=False).to_string())

        bad = audit[audit['end_of_season_eligibility'].eq('INELIGIBLE — Different End-of-Season Owner')]
        unresolved = audit[audit['end_of_season_eligibility'].eq('Ownership Unresolved')]
        if not bad.empty:
            print('\nPOTENTIAL HISTORICAL VIOLATIONS')
            print(bad[[c for c in ['year','team','player','prior_season_end_owner','prior_ownership_confidence'] if c in bad.columns]].to_string(index=False))
        if not unresolved.empty:
            print('\nUNRESOLVED OWNERSHIP')
            print(unresolved[[c for c in ['year','team','player','prior_season'] if c in unresolved.columns]].to_string(index=False))

    banner('OUTPUTS')
    print(OWNERSHIP_CSV)
    print(OWNERSHIP_JSON)
    if not audit.empty:
        print(AUDIT_CSV)
        print(AUDIT_JSON)
    print('\nPASS: end-of-season ownership build completed.')
    print('Review any violations before changing historical keeper records.')


if __name__ == '__main__':
    main()