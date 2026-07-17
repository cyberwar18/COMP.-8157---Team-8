# OLTP-to-OLAP Transformation and Multi-Metric Performance Benchmarking: MySQL vs DuckDB

**Team 8 — COMP 8157, University of Windsor**
Rabiya Javed Farooq · Purab Singh Mohan · Nancy Bogati Collum · Sneha Gunturu

## What this project does

This project compares MySQL (row-oriented, OLTP-optimized) against DuckDB
(columnar, OLAP-optimized) across two dimensions most existing benchmarks skip:

1. **The transformation step itself.** We load raw TPC-H data in its native
   transactional form into both engines, then explicitly transform it into
   OLAP-ready structures (a star schema fact/dimension model plus a
   denormalized analytical view) — identically in both engines — and measure
   both layers separately.
2. **More than query latency.** Data loading time, on-disk storage footprint,
   memory consumption, CPU utilization, and query performance across
   aggregation types (single group-by, multi-column group-by, nested
   subqueries) at multiple scale factors (SF-1, SF-5, SF-10).

The goal is a practitioner-usable answer to: at what dataset scale and query
shape does each engine's architectural advantage break down?

## Repo structure

```
config/
  config.example.yaml     # copy to config.yaml and fill in your MySQL password
sql/
  mysql/, duckdb/          # oltp_schema.sql (Phase 1-2), olap_schema.sql (Phase 3)
queries/
  query_matrix.yaml        # graduated query matrix (Phase 5)
src/
  schema_loader.py          # Phase 1-2 — applies OLTP/OLAP DDL
  data_populator.py         # Phase 2 — bulk-loads TPC-H .tbl files
  transformation_executor.py # Phase 3 — builds star schema + wide view
  query_executor.py         # Phase 4-5 — runs the query matrix, captures metrics
  result_analyzer.py        # Phase 6 — crossover thresholds + charts
  utils/
    db_connectors.py        # shared MySQL/DuckDB connection wrappers
    metrics.py               # CPU/memory sampling during query trials
scripts/
  generate_tpch_data.sh     # builds/generates TPC-H .tbl files via dbgen
  run_all.sh                 # full pipeline, one scale factor, end to end
```

## Setup

**1. Install dependencies:**
```
pip install -r requirements.txt
```

**2. Set up MySQL 8.0** locally, and create the database:
```sql
CREATE DATABASE tpch;
```

**3. Configure credentials:**
```
cp config/config.example.yaml config/config.yaml
```
Edit `config/config.yaml` with your real MySQL password. This file is
git-ignored — never commit it.

**4. Generate TPC-H data.** Requires a C compiler (gcc/make). On Windows,
use WSL or a Linux server (e.g. your university's shared server) rather
than fighting native compilation:
```bash
git clone https://github.com/electrum/tpch-dbgen.git external/tpch-dbgen
cd external/tpch-dbgen
cp makefile.suite Makefile
# edit Makefile: CC = gcc, DATABASE = SQLSERVER, MACHINE = LINUX, WORKLOAD = TPCH
make
cd ../..
bash scripts/generate_tpch_data.sh 1
```
This drops `.tbl` files into `data/raw/sf1/`. If you generated data on a
remote server, copy the `.tbl` files into that same local path (scp/sftp).

## Running the pipeline

Each phase can be run independently, or all at once via `run_all.sh`.

**Phase 1-2 — schema + data:**
```bash
python -m src.schema_loader --engine both --schema oltp
python -m src.data_populator --engine both --scale-factor 1
```

**Phase 3 — OLTP-to-OLAP transformation:**
```bash
python -m src.transformation_executor --engine both
```
Builds `fact_lineitem_orders`, `dim_customer`, `dim_supplier`, `dim_part`,
`dim_date`, and `analytical_wide_view` on both engines. Logs transform time
and storage footprint delta to `results/transformation_metrics.csv`.

**Phase 4-5 — query matrix + metrics:**
```bash
python -m src.query_executor --engine both --schema-layer both
```

**Phase 6 — analysis:**
```bash
python -m src.result_analyzer --input results/raw_metrics.csv
```

**Or all phases at once, for a given scale factor:**
```bash
bash scripts/run_all.sh 1
```

## Current status

- [x] Phase 1-2: OLTP schema + TPC-H SF-1 data loaded (MySQL + DuckDB)
- [x] Phase 3: OLTP-to-OLAP transformation complete (MySQL + DuckDB)
- [ ] Phase 4-5: query matrix execution
  - [x] DuckDB, SF-1, OLTP + OLAP: complete
  - [x] DuckDB, SF-5, OLTP + OLAP: complete
  - [x] DuckDB, SF-10, OLTP + OLAP: complete
  - [x] MySQL, SF-1, OLTP + OLAP: complete
  - [x] MySQL, SF-5, OLTP + OLAP: complete
  - [ ] MySQL, SF-10, OLTP + OLAP: not started
- [ ] Phase 6: crossover analysis + charts

## Notes for contributors

- Windows users: `run_all.sh` and `generate_tpch_data.sh` are bash scripts —
  run them via WSL or Git Bash, not plain PowerShell.
- MySQL's `LOAD DATA LOCAL INFILE` needs `allow_local_infile=True` on the
  client connection and `local_infile=1` server-side — already handled in
  `db_connectors.py`, but worth knowing if you're debugging connection issues.
- TPC-H's `.tbl` files end each line with a trailing delimiter, which some
  naive CSV readers misinterpret as an extra column — also already handled
  in `db_connectors.py`'s DuckDB loader.
- `data/`, `*.duckdb`, and `config/config.yaml` are git-ignored on purpose —
  regenerate data locally rather than trying to commit it (lineitem.tbl alone
  is ~750MB at SF-1, well over GitHub's file size limit anyway).
