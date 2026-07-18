from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


class AtlasDB:
    def __init__(self, path: str | Path, schema_path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(self.path))
        self.con.execute(Path(schema_path).read_text(encoding="utf-8"))

    def close(self) -> None:
        self.con.close()

    def execute(self, sql: str, params: list[Any] | None = None):
        return self.con.execute(sql, params or [])

    def replace_df(self, table: str, df: pd.DataFrame) -> None:
        self.con.register("_incoming_df", df)
        self.con.execute(f"DELETE FROM {table}")
        self.con.execute(f"INSERT INTO {table} SELECT * FROM _incoming_df")
        self.con.unregister("_incoming_df")

    def append_df(self, table: str, df: pd.DataFrame) -> None:
        if df.empty:
            return
        self.con.register("_incoming_df", df)
        cols = [r[1] for r in self.con.execute(f"PRAGMA table_info('{table}')").fetchall()]
        available = [c for c in cols if c in df.columns]
        selected = ",".join(f'"{c}"' for c in available)
        self.con.execute(f"INSERT INTO {table} ({selected}) SELECT {selected} FROM _incoming_df")
        self.con.unregister("_incoming_df")

    def upsert_df(self, table: str, df: pd.DataFrame, key: str) -> None:
        if df.empty:
            return
        self.con.register("_incoming_df", df)
        self.con.execute(f"DELETE FROM {table} WHERE {key} IN (SELECT {key} FROM _incoming_df)")
        self.append_df(table, df)
        try:
            self.con.unregister("_incoming_df")
        except Exception:
            pass

    def dataframe(self, sql: str) -> pd.DataFrame:
        return self.con.execute(sql).df()
