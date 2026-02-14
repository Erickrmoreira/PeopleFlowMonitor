import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd


class CountsRepository:
    """Camada de acesso a dados da tabela counts."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def fetch_counts_between(self, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(
                """
                SELECT direction, timestamp
                FROM counts
                WHERE timestamp >= ? AND timestamp < ?
                """,
                conn,
                params=(
                    start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
