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
  utils/
    db_connectors.py        # shared MySQL/DuckDB connection wrappers
    metrics.py               # CPU/memory sampling during query trials
analysis.py                 # Phase 6 — crossover thresholds + charts (run from repo root)
scripts/
  generate_tpch_data.sh     # builds/generates TPC-H .tbl files via dbgen
  run_all.sh                 # full pipeline, one scale factor, end to end
tests/
  test_smoke.py              # smoke tests for query executor prerequisites
data/
  sample/                    # small (5,000 rows/table) TPC-H sample at SF-1, SF-5, SF-10 — committed for grader inspection
  raw/                        # full generated .tbl files — git-ignored, see Dataset section below
results/
  raw_metrics.csv                       # full per-trial benchmark results
  raw_metrics_backup_20260718.csv       # timestamped backup
  median_latency_summary.csv            # clean summary table, produced by analysis.py
  transformation_metrics.csv            # transformation time + storage footprint
  chart_*.png                            # summary charts, produced by analysis.py
external/
  tpch-dbgen/                 # NOT included in the repo — clone manually, see Setup step 4
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
use WSL, Git Bash, or a Linux server (e.g. your university's shared server)
rather than fighting native compilation:
```bash
git clone https://github.com/electrum/tpch-dbgen.git external/tpch-dbgen
cd external/tpch-dbgen
cp makefile.suite Makefile
# edit Makefile: CC = gcc, DATABASE = SQLSERVER, MACHINE = LINUX, WORKLOAD = TPCH
make
cd ../..
bash scripts/generate_tpch_data.sh 1
```
This drops `.tbl` files into `data/raw/sf1/`. Repeat with `5` and `10` as the
argument for the other scale factors. If you generated data on a remote
server, copy the `.tbl` files into that same local path (scp/sftp).

`external/tpch-dbgen` is intentionally **not** committed to this repository
(the generator itself, plus its compiled binaries, are excluded via
`.gitignore`) — always clone it fresh per the command above rather than
expecting it to appear after `git clone` of this repo.

## Dataset

This project uses the industry-standard TPC-H benchmark dataset at scale
factors SF-1, SF-5, and SF-10, generated via the official `tpch-dbgen` tool
(see Setup step 4 above).

- **`data/sample/`** (committed to this repo) — a 5,000-row-per-table sample
  of each table at each scale factor, so the data shape and structure can be
  inspected directly without downloading the full dataset.
- **Full dataset** (too large for GitHub — SF-10's `lineitem.tbl` alone is
  ~7.8GB, well over GitHub's 100MB per-file limit): **[FILL IN: Google
  Drive / Dropbox link here]**
- Alternatively, regenerate the full dataset locally at any scale factor
  using the commands in Setup step 4.

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
python3 analysis.py
```
Reads `results/raw_metrics.csv` and produces `results/median_latency_summary.csv`
plus the `results/chart_*.png` summary charts.

**Or all phases at once, for a given scale factor:**
```bash
bash scripts/run_all.sh 1
```

## Current status

- [x] Phase 1-2: OLTP schema + TPC-H SF-1 data loaded (MySQL + DuckDB)
- [x] Phase 3: OLTP-to-OLAP transformation complete (MySQL + DuckDB)
- [x] Phase 4-5: query matrix execution
  - [x] DuckDB, SF-1, OLTP + OLAP: complete
  - [x] DuckDB, SF-5, OLTP + OLAP: complete
  - [x] DuckDB, SF-10, OLTP + OLAP: complete
  - [x] MySQL, SF-1, OLTP + OLAP: complete
  - [x] MySQL, SF-5, OLTP + OLAP: complete (reduced repetitions — see benchmark
        results documentation, §2)
  - [ ] MySQL, SF-10, OLTP + OLAP: **not completed** — disk-capacity and
        bulk-load-duration limitation, documented in the benchmark results
        documentation, §5. Not a harness failure.
- [x] Phase 6: crossover analysis + charts

## Notes for contributors

- Windows users: `run_all.sh` and `generate_tpch_data.sh` are bash scripts —
  run them via WSL or Git Bash, not plain PowerShell.
- MySQL's `LOAD DATA LOCAL INFILE` needs `allow_local_infile=True` on the
  client connection and `local_infile=1` server-side — already handled in
  `db_connectors.py`, but worth knowing if you're debugging connection issues.
- TPC-H's `.tbl` files end each line with a trailing delimiter, which some
  naive CSV readers misinterpret as an extra column — also already handled
  in `db_connectors.py`'s DuckDB loader.
- `data/raw/`, `*.duckdb`, and `config/config.yaml` are git-ignored on
  purpose — regenerate full-scale data locally rather than trying to commit
  it (`lineitem.tbl` alone is ~750MB at SF-1 and ~7.8GB at SF-10, well over
  GitHub's file size limit). A small sample is committed at `data/sample/`
  for inspection — see the Dataset section above.
- `results/` **is** tracked and committed (not git-ignored) — it contains
  the benchmark output (`raw_metrics.csv`, `median_latency_summary.csv`,
  charts) that graders need to see.