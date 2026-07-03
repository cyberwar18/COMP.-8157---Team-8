"""Thin, uniform wrappers around the MySQL and DuckDB drivers so the rest of
the harness can execute SQL and read back rows without caring which engine
it's talking to.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterable

import duckdb
import mysql.connector
import yaml


def load_config(path: str = "config/config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


@dataclass
class QueryResult:
    rows: list
    elapsed_seconds: float


class MySQLConnector:
    """Wraps mysql-connector-python with timing and a fixed InnoDB config."""

    def __init__(self, cfg: dict):
        self.cfg = cfg["mysql"]
        self._conn = None

    def connect(self):
        self._conn = mysql.connector.connect(
            host=self.cfg["host"],
            port=self.cfg["port"],
            user=self.cfg["user"],
            password=self.cfg["password"],
            database=self.cfg["database"],
            autocommit=True,
            allow_local_infile=True,   # required for LOAD DATA LOCAL INFILE (client side)
        )
        cur = self._conn.cursor()
        # Server also needs local_infile enabled; harmless if already on.
        cur.execute("SET GLOBAL local_infile = 1;")
        if self.cfg.get("disable_binlog"):
            cur.execute("SET sql_log_bin = 0;")
        cur.close()
        return self

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> QueryResult:
        cur = self._conn.cursor()
        start = time.perf_counter()
        cur.execute(sql, params or ())
        rows = cur.fetchall() if cur.with_rows else []
        elapsed = time.perf_counter() - start
        cur.close()
        return QueryResult(rows=rows, elapsed_seconds=elapsed)

    def executemany_from_csv(self, table: str, csv_path: str, columns: list[str]):
        """Bulk load via LOAD DATA LOCAL INFILE (fast path for population)."""
        cur = self._conn.cursor()
        col_list = ", ".join(columns)
        csv_path = csv_path.replace("\\", "/")  # avoid MySQL string-escaping mangling Windows paths (e.g. \r in \raw\)
        cur.execute(
            f"""LOAD DATA LOCAL INFILE '{csv_path}'
                INTO TABLE {table}
                FIELDS TERMINATED BY '|'
                LINES TERMINATED BY '\\n'
                ({col_list});"""
        )
        cur.close()

    def storage_bytes(self, table: str) -> int:
        cur = self._conn.cursor()
        cur.execute(
            """SELECT (data_length + index_length) AS bytes
               FROM information_schema.tables
               WHERE table_schema = %s AND table_name = %s""",
            (self.cfg["database"], table),
        )
        row = cur.fetchone()
        cur.close()
        return int(row[0]) if row and row[0] is not None else 0

    def close(self):
        if self._conn:
            self._conn.close()


class DuckDBConnector:
    """Wraps duckdb's Python API with timing and memory/thread limits applied."""

    def __init__(self, cfg: dict):
        self.cfg = cfg["duckdb"]
        self._conn = None

    def connect(self):
        self._conn = duckdb.connect(self.cfg["database_path"])
        self._conn.execute(f"SET memory_limit='{self.cfg['memory_limit_gb']}GB';")
        self._conn.execute(f"SET threads={self.cfg['threads']};")
        return self

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> QueryResult:
        start = time.perf_counter()
        rel = self._conn.execute(sql, params or [])
        try:
            rows = rel.fetchall()
        except duckdb.Error:
            rows = []
        elapsed = time.perf_counter() - start
        return QueryResult(rows=rows, elapsed_seconds=elapsed)

    def load_csv(self, table: str, csv_path: str):
        # dbgen's .tbl files end every line with a trailing '|', which read_csv
        # sees as one extra (empty) phantom column beyond the table's real
        # columns. A plain COPY fails on that column-count mismatch, so read
        # positionally as all-varchar and insert only the real columns.
        #
        # DuckDB auto-names positional columns column0, column1, ... but
        # zero-pads the index to match the width of the largest index (e.g.
        # a 16-column table gets column00..column15, a 9-column table gets
        # column0..column8). Compute that width instead of hardcoding it.
        cols = [row[0] for row in self._conn.execute(f"DESCRIBE {table}").fetchall()]
        col_list = ", ".join(cols)
        width = len(str(len(cols) - 1))
        select_list = ", ".join(f"column{i:0{width}d}" for i in range(len(cols)))
        self._conn.execute(f"""
            INSERT INTO {table} ({col_list})
            SELECT {select_list}
            FROM read_csv('{csv_path}', delim='|', header=false, all_varchar=true)
        """)

    def storage_bytes(self, table: str) -> int:
        # Approximate via DuckDB's database_size pragma; per-table sizing needs
        # 'PRAGMA storage_info(table)' summed over segments.
        rows = self._conn.execute(
            f"SELECT SUM(segment_size) FROM pragma_storage_info('{table}')"
        ).fetchall()
        return int(rows[0][0]) if rows and rows[0][0] is not None else 0

    def close(self):
        if self._conn:
            self._conn.close()


@contextmanager
def connect_engine(engine: str, cfg: dict):
    """engine in {'mysql', 'duckdb'} -> yields a connected connector, closes on exit."""
    if engine == "mysql":
        conn = MySQLConnector(cfg).connect()
    elif engine == "duckdb":
        conn = DuckDBConnector(cfg).connect()
    else:
        raise ValueError(f"Unknown engine: {engine}")
    try:
        yield conn
    finally:
        conn.close()