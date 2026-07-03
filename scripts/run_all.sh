#!/usr/bin/env bash
# Runs the full benchmarking pipeline end to end for a single scale factor.
# Usage: bash scripts/run_all.sh [scale_factor]

set -euo pipefail
SF="${1:-1}"

echo "== 1/6 generate TPC-H data (SF-${SF}) =="
bash scripts/generate_tpch_data.sh "${SF}"

echo "== 2/6 load OLTP schema =="
python -m src.schema_loader --engine both --schema oltp

echo "== 3/6 populate OLTP tables =="
python -m src.data_populator --engine both --scale-factor "${SF}"

echo "== 4/6 run OLTP-to-OLAP transformation =="
python -m src.transformation_executor --engine both

echo "== 5/6 run query matrix (OLTP + OLAP layers) =="
python -m src.query_executor --engine both --schema-layer both

echo "== 6/6 analyze results =="
python -m src.result_analyzer --input results/raw_metrics.csv

echo "Done. See results/median_latency_by_config.csv, results/crossover_thresholds.csv, results/charts/"
