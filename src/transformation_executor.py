"""OLTP-to-OLAP transformation executor (Proposal Phase 3).
Owner: Purab Singh Mohan

Builds the star schema (fact_lineitem_orders + dim_customer/dim_supplier/dim_part/
dim_date) and the denormalized analytical_wide_view identically in both engines,
using sql/<engine>/olap_schema.sql. Records transformation time and the storage
footprint delta caused by the transform, which feeds result_analyzer.py.
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import time

from src.utils.db_connectors import connect_engine, load_config

SQL_DIR = pathlib.Path("sql")
FACT_TABLE = "fact_lineitem_orders"
SOURCE_TABLES = ["lineitem", "orders", "customer", "supplier", "part", "nation", "region"]
OLAP_TABLES = ["fact_lineitem_orders", "dim_customer", "dim_supplier", "dim_part", "dim_date"]


def _run_sql_file(conn, sql_path: pathlib.Path):
    for stmt in sql_path.read_text().split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt + ";")


def _total_storage_bytes(conn, tables: list[str]) -> int:
    total = 0
    for t in tables:
        try:
            total += conn.storage_bytes(t)
        except Exception as exc:  # table may not exist yet
            print(f"  (storage lookup skipped for {t}: {exc})")
    return total


def transform(engine: str, cfg: dict, log_path: pathlib.Path):
    sql_path = SQL_DIR / engine / "olap_schema.sql"
    with connect_engine(engine, cfg) as conn:
        pre_bytes = _total_storage_bytes(conn, SOURCE_TABLES)

        start = time.perf_counter()
        _run_sql_file(conn, sql_path)
        elapsed = time.perf_counter() - start

        post_bytes = _total_storage_bytes(conn, OLAP_TABLES)
        fact_rows = conn.execute(f"SELECT COUNT(*) FROM {FACT_TABLE};").rows[0][0]

    print(f"[{engine}] transformation complete in {elapsed:.2f}s | "
          f"fact rows={fact_rows} | oltp_bytes={pre_bytes} | olap_bytes={post_bytes}")

    _log_row(log_path, engine, elapsed, fact_rows, pre_bytes, post_bytes)


def _log_row(log_path: pathlib.Path, engine, elapsed, fact_rows, pre_bytes, post_bytes):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not log_path.exists()
    with open(log_path, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["engine", "transform_seconds", "fact_row_count", "oltp_bytes", "olap_bytes"])
        writer.writerow([engine, f"{elapsed:.4f}", fact_rows, pre_bytes, post_bytes])


def main():
    parser = argparse.ArgumentParser(description="Run OLTP->OLAP transformation")
    parser.add_argument("--engine", choices=["mysql", "duckdb", "both"], default="both")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--log", default="results/transformation_metrics.csv")
    args = parser.parse_args()

    cfg = load_config(args.config)
    engines = ["mysql", "duckdb"] if args.engine == "both" else [args.engine]
    for engine in engines:
        transform(engine, cfg, pathlib.Path(args.log))


if __name__ == "__main__":
    main()
