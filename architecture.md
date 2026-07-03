# Architecture

## Overview

The benchmarking system is organized into five layers, matching the design
in the project proposal (Section V): data ingestion, OLTP-to-OLAP
transformation, workload generation, execution control, and measurement
collection. Each layer is engine-agnostic at the interface level — the same
Python code drives both MySQL and DuckDB, with engine-specific behavior
isolated to `src/utils/db_connectors.py` and the per-engine SQL files under
`sql/`.

```
                    config/config.yaml
                           |
                           v
   sql/{mysql,duckdb}/oltp_schema.sql
                           |
                           v
              +-------------------------+
              |   schema_loader.py      |   Phase 1-2
              +-------------------------+
                           |
                           v
              +-------------------------+
              |   data_populator.py     |   Phase 2
              +-------------------------+   reads data/raw/sf{N}/*.tbl
                           |
                           v
   sql/{mysql,duckdb}/olap_schema.sql
                           |
                           v
              +-------------------------+
              | transformation_executor |   Phase 3
              +-------------------------+
                           |
                           v
    queries/query_matrix.yaml
                           |
                           v
              +-------------------------+
              |   query_executor.py     |   Phase 4-5
              +-------------------------+   -> results/raw_metrics.csv
                           |
                           v
              +-------------------------+
              |   result_analyzer.py    |   Phase 6
              +-------------------------+   -> crossover thresholds, charts
```

All engine access flows through `src/utils/db_connectors.py`, which exposes
a uniform `MySQLConnector` / `DuckDBConnector` interface (`connect()`,
`execute()`, `storage_bytes()`, `close()`) so the rest of the pipeline never
branches on engine type directly — it calls `connect_engine(engine, cfg)`
and gets back an object with the same shape either way.

## Layer 1-2: Schema + Data Ingestion

**Files:** `src/schema_loader.py`, `src/data_populator.py`,
`sql/{mysql,duckdb}/oltp_schema.sql`

Both engines are loaded with the same logical TPC-H schema (8 tables:
`region`, `nation`, `customer`, `supplier`, `part`, `partsupp`, `orders`,
`lineitem`), but with engine-appropriate physical design:

- **MySQL**: InnoDB tables with a clustered primary-key B-Tree plus
  secondary indexes on high-cardinality foreign-key and filter columns
  (`c_nationkey`, `s_nationkey`, `o_custkey`, `o_orderdate`, `l_partkey`,
  `l_suppkey`, `l_shipdate`). Foreign key constraints are enforced.
- **DuckDB**: no manual indexes. DuckDB relies on native zone-map (min/max)
  metadata per column block for predicate pushdown, per its columnar design.

`data_populator.py` loads raw TPC-H `.tbl` files (dbgen output, pipe-delimited)
in dependency order — parent/dimension tables before tables holding foreign
keys into them — so MySQL's FK constraints don't reject out-of-order inserts:
`region → nation → customer/supplier → part → partsupp → orders → lineitem`.

MySQL loading uses `LOAD DATA LOCAL INFILE` for bulk-load speed. DuckDB
loading reads each `.tbl` file positionally via `read_csv(..., all_varchar=true)`
rather than a plain `COPY`, because dbgen's trailing per-line delimiter
produces one phantom extra column that a direct `COPY` rejects on a
column-count mismatch.

## Layer 3: OLTP-to-OLAP Transformation

**Files:** `src/transformation_executor.py`, `sql/{mysql,duckdb}/olap_schema.sql`

This is the project's core methodological contribution: the transformation
step is measured explicitly rather than treated as invisible setup.

The transformation builds:
- **`fact_lineitem_orders`** — one row per lineitem, pre-joined to its order
  (avoids a JOIN at query time for the most common access pattern)
- **`dim_customer`**, **`dim_supplier`** — denormalized, with nation and
  region flattened in directly (no need to join through `nation`/`region`
  again at query time)
- **`dim_part`**
- **`analytical_wide_view`** — a fully denormalized view joining the fact
  table to all dimensions, representing the flattened wide-table access
  pattern typical of columnar analytical workloads

`transformation_executor.py` records wall-clock transformation time and the
storage footprint before/after (via `storage_bytes()` on the connector) to
`results/transformation_metrics.csv`. This is the data source for the
proposal's "transformation time and storage footprint change" deliverable.

## Layer 4-5: Workload Generation + Execution Control

**Files:** `src/query_executor.py`, `queries/query_matrix.yaml`,
`src/utils/metrics.py`

The query matrix is a 3-dimensional grid: dataset scale (SF-1/5/10) ×
aggregation depth (single group-by, multi-column group-by, nested subquery)
× index utilization mode (full scan, indexed point lookup, range scan).
Each cell is executed `repetitions_per_config` times (default 5) to get a
stable median latency.

`query_matrix.yaml` holds one SQL template per aggregation depth, per schema
layer (`oltp` targets the raw tables, `olap` targets the star schema /
`analytical_wide_view`). `query_executor.py` substitutes the index-mode
predicate into each template at run time and dispatches it against
whichever engine/layer combination is being tested.

`metrics.py`'s `ResourceSampler` runs a background thread that polls
CPU% and RSS memory at a fixed interval (default 50ms) for the duration of
each query, giving peak memory and mean CPU alongside latency. Note: for
MySQL, this samples the Python client process, not the `mysqld` server
process — a known limitation worth resolving before the memory/CPU numbers
are presented as engine comparisons, since MySQL's actual work happens in a
separate server process.

## Layer 6: Measurement Collection + Analysis

**Files:** `src/result_analyzer.py`

Reads `results/raw_metrics.csv`, computes median latency per configuration
cell, and identifies crossover points — the scale factor at which the
faster engine flips, per (schema layer, aggregation depth, index mode)
combination. Outputs `results/median_latency_by_config.csv`,
`results/crossover_thresholds.csv`, and per-configuration latency-vs-scale
charts in `results/charts/`.

## Design decisions worth knowing about

- **Config-driven, not hardcoded.** All connection details, scale factors,
  aggregation depths, index modes, and repetition counts live in
  `config/config.yaml`, so running a wider or narrower experiment doesn't
  require code changes.
- **Same Python code, both engines.** The connector abstraction means
  `schema_loader.py`, `data_populator.py`, `transformation_executor.py`, and
  `query_executor.py` never contain `if engine == "mysql"` branches — engine
  differences live entirely in `db_connectors.py` and the per-engine SQL files.
- **Trailing-pipe and LOCAL INFILE handling in `db_connectors.py`** exist
  because of real failures encountered generating and loading actual TPC-H
  data (dbgen's line format, MySQL 8's default-disabled LOCAL INFILE) — not
  speculative edge cases.
