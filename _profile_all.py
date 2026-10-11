"""Stage 0 — profile all three sources and save results as JSON for the EDA notebook."""
import pandas as pd
import sqlite3
import json

result = {}

# --- CUSTOMERS ---
cust = pd.read_csv('data/customers.csv')
result['customers'] = {
    'n_rows': len(cust),
    'columns': cust.columns.tolist(),
    'dtypes': {c: str(d) for c, d in cust.dtypes.items()},
    'churn_rate': float(cust['churned'].mean()),
    'churned_count': int(cust['churned'].sum()),
    'total_count': len(cust),
    'signup_min': str(cust['signup_date'].min()),
    'signup_max': str(cust['signup_date'].max()),
}

# Channels
ch = cust.groupby('acquisition_channel')['churned'].agg(['count', 'mean'])
result['customers']['channel_counts'] = {k: int(v) for k, v in ch['count'].items()}
result['customers']['channel_churn_rates'] = {k: float(v) for k, v in ch['mean'].items()}

# Regions
rg = cust.groupby('region')['churned'].agg(['count', 'mean'])
result['customers']['region_counts'] = {k: int(v) for k, v in rg['count'].items()}
result['customers']['region_churn_rates'] = {k: float(v) for k, v in rg['mean'].items()}

# Missingness
result['customers']['missing'] = {c: int(v) for c, v in cust.isna().sum().items()}

# --- TRANSACTIONS ---
conn = sqlite3.connect('data/transactions.db')
txns = pd.read_sql('SELECT * FROM transactions', conn)

result['transactions'] = {
    'n_rows': len(txns),
    'columns': txns.columns.tolist(),
    'dtypes': {c: str(d) for c, d in txns.dtypes.items()},
    'txn_timestamp_min': str(txns['txn_timestamp'].min()),
    'txn_timestamp_max': str(txns['txn_timestamp'].max()),
    'unique_customers': int(txns['customer_id'].nunique()),
    'missing': {c: int(v) for c, v in txns.isna().sum().items()},
}

# Numeric columns in transactions
for col in ['amount', 'quantity', 'is_returned']:
    s = txns[col]
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    lo = q1 - 1.5 * iqr
    hi = q3 + 1.5 * iqr
    n_out = int(((s < lo) | (s > hi)).sum())
    skew_dir = 'right' if s.mean() > s.median() else ('left' if s.mean() < s.median() else 'roughly symmetric')
    result['transactions'][f'{col}_stats'] = {
        'mean': float(round(s.mean(), 2)),
        'median': float(round(s.median(), 2)),
        'std': float(round(s.std(), 2)),
        'min': float(round(s.min(), 2)),
        'max': float(round(s.max(), 2)),
        'q25': float(round(q1, 2)),
        'q75': float(round(q3, 2)),
        'skew_direction': skew_dir,
        'outlier_rule': 'IQR 1.5x',
        'outlier_bound_low': float(round(lo, 2)),
        'outlier_bound_high': float(round(hi, 2)),
        'n_outliers': n_out,
    }

# Monthly volume from row-level
if 'txn_month' in txns.columns:
    monthly = txns.groupby('txn_month').agg(
        txn_count=('customer_id', 'count'),
        unique_customers=('customer_id', 'nunique'),
        total_amount=('amount', 'sum'),
    ).reset_index()
    monthly['txn_month'] = monthly['txn_month'].astype(str)
    result['transactions']['monthly_volume'] = monthly.to_dict(orient='records')

# Zero-activity customers
db_custs = set(pd.read_sql('SELECT DISTINCT customer_id FROM transactions', conn)['customer_id'].tolist())
all_custs = set(cust['customer_id'].tolist())
zero_act = sorted(all_custs - db_custs)
result['transactions']['zero_activity_customers'] = len(zero_act)
result['transactions']['zero_activity_ids'] = zero_act
conn.close()

# --- MONTHLY AGG PARQUET ---
agg = pd.read_parquet('data/transactions_monthly_agg.parquet')
result['monthly_agg'] = {
    'n_rows': len(agg),
    'columns': agg.columns.tolist(),
    'dtypes': {c: str(d) for c, d in agg.dtypes.items()},
    'txn_month_min': str(agg['txn_month'].min()),
    'txn_month_max': str(agg['txn_month'].max()),
    'unique_customers': int(agg['customer_id'].nunique()),
    'unique_months': int(agg['txn_month'].nunique()),
    'missing': {c: int(v) for c, v in agg.isna().sum().items()},
    'sample': agg.head(10).to_dict(orient='records'),
}

# Reaggregate row-level to same grain for comparison
row_monthly = txns.groupby(['customer_id', 'txn_month']).agg(
    txn_count=('customer_id', 'count'),
    total_amount=('amount', 'sum'),
    returned_count=('is_returned', 'sum'),
).reset_index()
row_monthly['txn_month'] = row_monthly['txn_month'].astype(str)

parquet_monthly = agg.copy()
parquet_monthly['txn_month'] = parquet_monthly['txn_month'].astype(str)

# Merge for comparison
merged = pd.merge(
    row_monthly, parquet_monthly,
    on=['customer_id', 'txn_month'],
    how='outer', suffixes=('_row', '_agg'), indicator=True
)

left_only = len(merged[merged['_merge'] == 'left_only'])
right_only = len(merged[merged['_merge'] == 'right_only'])
both = len(merged[merged['_merge'] == 'both'])
amount_diff = merged[merged['_merge'] == 'both']['total_amount_row'] - merged[merged['_merge'] == 'both']['total_amount']
mean_abs_diff = float(amount_diff.abs().mean())
max_abs_diff = float(amount_diff.abs().max())

result['multi_source_comparison'] = {
    'rows_in_row_agg': len(row_monthly),
    'rows_in_parquet': len(parquet_monthly),
    'matched_both': int(both),
    'left_only_row_source': int(left_only),
    'right_only_parquet_source': int(right_only),
    'mean_abs_amount_diff': round(mean_abs_diff, 4),
    'max_abs_amount_diff': round(max_abs_diff, 4),
}

# Now compute churned/not-churned transaction stats
conn = sqlite3.connect('data/transactions.db')
txns_with_churn = pd.read_sql("""
    SELECT t.*, c.churned
    FROM transactions t
    JOIN customers c ON t.customer_id = c.customer_id
""", conn)
conn.close()

result['churned_vs_not'] = {}
for grp, label in [(0, 'not_churned'), (1, 'churned')]:
    subset = txns_with_churn[txns_with_churn['churned'] == grp]
    result['churned_vs_not'][label] = {
        'n_customers': int(subset['customer_id'].nunique()),
        'n_transactions': len(subset),
        'avg_amount_per_txn': float(round(subset['amount'].mean(), 2)),
        'median_amount_per_txn': float(round(subset['amount'].median(), 2)),
        'total_amount': float(round(subset['amount'].sum(), 2)),
        'avg_quantity': float(round(subset['quantity'].mean(), 2)),
        'return_rate': float(round(subset['is_returned'].mean(), 4)),
    }

with open('_profile_results.json', 'w') as f:
    json.dump(result, f, indent=2, default=str)

print('Profile complete.')
print(f'Churn rate: {result["customers"]["churn_rate"]:.4f}')
print(f'Zero-activity customers: {result["transactions"]["zero_activity_customers"]}')
print(f'Transactions rows: {result["transactions"]["n_rows"]}')
print(f'Monthly agg rows: {result["monthly_agg"]["n_rows"]}')
print(f'Multi-source matched: {result["multi_source_comparison"]["matched_both"]}, '
      f'left-only: {result["multi_source_comparison"]["left_only_row_source"]}, '
      f'right-only: {result["multi_source_comparison"]["right_only_parquet_source"]}')
print(f'Mean abs amount diff: {result["multi_source_comparison"]["mean_abs_amount_diff"]}')