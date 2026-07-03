"""Schema loader (Proposal Phase 1-2).
Owner: Rabiya Javed Farooq

Executes the raw OLTP DDL against MySQL and/or DuckDB. Run this before
data_populator.py. The OLAP DDL is applied later by transformation_executor.py.
"""
from __future__ import annotations

import argparse
import pathlib

from src.utils.db_connectors import connect_engine, load_config

SQL_DIR = pathlib.Path("sql")


def _run_sql_file(conn, sql_path: pathlib.Path):
    statements = sql_path.read_text().split(";")
    for stmt in statements:
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt + ";")


def load_schema(engine: str, schema: str, cfg: dict):
    sql_path = SQL_DIR / engine / f"{schema}_schema.sql"
    if not sql_path.exists():
        raise FileNotFoundError(f"No DDL file at {sql_path}")
    with connect_engine(engine, cfg) as conn:
        print(f"[{engine}] applying {schema} schema from {sql_path} ...")
        _run_sql_file(conn, sql_path)
        print(f"[{engine}] {schema} schema applied.")


def main():
    parser = argparse.ArgumentParser(description="Load OLTP/OLAP DDL into MySQL and/or DuckDB")
    parser.add_argument("--engine", choices=["mysql", "duckdb", "both"], default="both")
    parser.add_argument("--schema", choices=["oltp", "olap"], default="oltp")
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    engines = ["mysql", "duckdb"] if args.engine == "both" else [args.engine]
    for engine in engines:
        load_schema(engine, args.schema, cfg)


if __name__ == "__main__":
    main()
