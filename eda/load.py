"""
One loader function per source — pure I/O, no analysis logic.
"""

import pandas as pd
import sqlite3
from pathlib import Path


def load_customers(path: str | Path) -> pd.DataFrame:
    """Load customers.csv with parsed dates."""
    return pd.read_csv(path, parse_dates=["signup_date"])


def load_transactions(path: str | Path) -> pd.DataFrame:
    """Load transactions table from SQLite database."""
    conn = sqlite3.connect(str(path))
    df = pd.read_sql("SELECT * FROM transactions", conn, parse_dates=["txn_timestamp"])
    conn.close()
    return df


def load_monthly_agg(path: str | Path) -> pd.DataFrame:
    """Load the pre-aggregated parquet extract."""
    return pd.read_parquet(path)