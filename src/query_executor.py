"""Query executor / execution control layer (Proposal Phase 4-5).
Owner: Nancy Bogati Collum

Dispatches the graduated query matrix (queries/query_matrix.yaml) against both
engines, both schema layers (oltp/olap), and every configured scale factor and
index mode. Each configuration cell is executed `repetitions_per_config` times;
wall-clock latency, peak RSS, and mean CPU% are captured per trial and appended
to results/raw_metrics.csv.
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import re
import statistics

import yaml

from src.utils.db_connectors import connect_engine, load_config
from src.utils.metrics import ResourceSampler, drop_os_page_cache

INDEX_MODE_PREDICATES = {
    "full_scan": "",
    "indexed_point_lookup": " AND l_orderkey = 1",
    "range_scan": " AND l_shipdate BETWEEN DATE '1996-01-01' AND DATE '1996-03-31'",
}


def load_query_matrix(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _apply_index_mode(sql: str, index_mode: str) -> str:
    predicate = INDEX_MODE_PREDICATES[index_mode]
    if not predicate:
        return sql
    # Anchor on the FIRST GROUP BY, which always belongs to the block that
    # actually scans the base fact/lineitem table in every query template
    # in this matrix (even nested_subquery's outer WHERE references columns
    # from the derived table, not the base table, so injecting there would
    # produce an unresolvable column reference). Only look for an existing
    # WHERE within that same block (before the first GROUP BY) - a WHERE
    # appearing later, in an outer/sibling scope, doesn't apply here.
    condition = predicate.strip()
    gb_match = re.search(r"\bGROUP BY\b", sql, re.IGNORECASE)
    if not gb_match:
        return sql
    prefix = sql[:gb_match.start()]
    if re.search(r"\bWHERE\b", prefix, re.IGNORECASE):
        return sql[:gb_match.start()] + f"{condition}\n" + sql[gb_match.start():]
    return sql[:gb_match.start()] + f"WHERE 1=1 {condition}\n" + sql[gb_match.start():]


# NOTE: cache-drop is only applied when configured (see drop_os_cache_between_trials
# in config.yaml) to isolate its effect on latency measurements per the proposal's risk mitigation plan.

def run_matrix(engine: str, schema_layer: str, cfg: dict, matrix: dict, out_path: pathlib.Path):
    exp_cfg = cfg["experiment"]
    is_new = not out_path.exists()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with connect_engine(engine, cfg) as conn, open(out_path, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow([
                "engine", "schema_layer", "scale_factor", "aggregation_depth", "index_mode",
                "repetition", "latency_seconds", "peak_rss_mb", "mean_cpu_pct",
            ])

        for scale_factor in exp_cfg["scale_factors"]:
            for agg_depth in exp_cfg["aggregation_depths"]:
                base_sql = matrix[agg_depth][schema_layer]
                for index_mode in exp_cfg["index_modes"]:
                    sql = _apply_index_mode(base_sql, index_mode)
                    latencies = []
                    for rep in range(1, exp_cfg["repetitions_per_config"] + 1):
                        if exp_cfg.get("drop_os_cache_between_trials"):
                            drop_os_page_cache()
                        with ResourceSampler(interval_seconds=0.05) as sampler:
                            result = conn.execute(sql)
                        peak_rss, mean_cpu = sampler.summary()
                        latencies.append(result.elapsed_seconds)
                        writer.writerow([
                            engine, schema_layer, scale_factor, agg_depth, index_mode, rep,
                            f"{result.elapsed_seconds:.6f}", f"{peak_rss / (1024 * 1024):.2f}",
                            f"{mean_cpu:.2f}",
                        ])
                    median_latency = statistics.median(latencies)
                    print(f"[{engine}/{schema_layer}] sf={scale_factor} agg={agg_depth} "
                          f"idx={index_mode} median_latency={median_latency:.4f}s")


def main():
    parser = argparse.ArgumentParser(description="Run the graduated query matrix")
    parser.add_argument("--engine", choices=["mysql", "duckdb", "both"], default="both")
    parser.add_argument("--schema-layer", choices=["oltp", "olap", "both"], default="both")
    parser.add_argument("--matrix", default="queries/query_matrix.yaml")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--out", default=None, help="overrides results.raw_metrics_csv from config")
    args = parser.parse_args()

    cfg = load_config(args.config)
    matrix = load_query_matrix(args.matrix)
    out_path = pathlib.Path(args.out or cfg["results"]["raw_metrics_csv"])

    engines = ["mysql", "duckdb"] if args.engine == "both" else [args.engine]
    layers = ["oltp", "olap"] if args.schema_layer == "both" else [args.schema_layer]

    for engine in engines:
        for layer in layers:
            run_matrix(engine, layer, cfg, matrix, out_path)


if __name__ == "__main__":
    main()
