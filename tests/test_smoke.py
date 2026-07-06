"""Sanity checks to run before committing to a full benchmark run.
`pytest tests/test_smoke.py` — does not require MySQL; DuckDB tests run in-memory.
"""
import pathlib

import duckdb
import yaml


def test_config_loads():
    cfg_path = pathlib.Path("config/config.yaml")
    assert cfg_path.exists(), "config/config.yaml is missing"
    cfg = yaml.safe_load(cfg_path.read_text())
    assert "mysql" in cfg and "duckdb" in cfg and "experiment" in cfg


def test_duckdb_oltp_schema_applies_in_memory():
    ddl = pathlib.Path("sql/duckdb/oltp_schema.sql").read_text()
    conn = duckdb.connect(":memory:")
    for stmt in ddl.split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt + ";")
    tables = {r[0] for r in conn.execute("SHOW TABLES;").fetchall()}
    assert {"region", "nation", "customer", "supplier", "part", "partsupp", "orders", "lineitem"} <= tables


def test_query_matrix_yaml_is_well_formed():
    matrix = yaml.safe_load(pathlib.Path("queries/query_matrix.yaml").read_text())
    for depth in ("single_group_by", "multi_group_by", "nested_subquery"):
        assert depth in matrix
        assert "oltp" in matrix[depth] and "olap" in matrix[depth]
