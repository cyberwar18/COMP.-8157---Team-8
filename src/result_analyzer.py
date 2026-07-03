"""Result analyzer (Proposal Phase 6).
Owner: Sneha Gunturu

Reads results/raw_metrics.csv, computes median latency per configuration cell,
finds the crossover points where the faster engine flips as scale factor grows,
and renders comparison charts into results/charts/.
"""
from __future__ import annotations

import argparse
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def load_metrics(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def median_latency_table(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["engine", "schema_layer", "scale_factor", "aggregation_depth", "index_mode"])["latency_seconds"]
        .median()
        .reset_index()
        .rename(columns={"latency_seconds": "median_latency_seconds"})
    )


def find_crossovers(med: pd.DataFrame) -> pd.DataFrame:
    """For each (schema_layer, aggregation_depth, index_mode), find the scale factor
    at which the engine with the lower median latency switches, if it does."""
    rows = []
    group_cols = ["schema_layer", "aggregation_depth", "index_mode"]
    for keys, group in med.groupby(group_cols):
        pivot = group.pivot(index="scale_factor", columns="engine", values="median_latency_seconds").sort_index()
        if "mysql" not in pivot.columns or "duckdb" not in pivot.columns:
            continue
        pivot["faster"] = pivot.apply(lambda r: "mysql" if r["mysql"] < r["duckdb"] else "duckdb", axis=1)
        flips = pivot["faster"].ne(pivot["faster"].shift()).fillna(False)
        crossover_scale_factors = pivot.index[flips][1:].tolist()  # skip first row (not a real flip)
        rows.append({
            **dict(zip(group_cols, keys)),
            "crossover_scale_factors": crossover_scale_factors or "none",
            "faster_at_max_scale": pivot["faster"].iloc[-1],
        })
    return pd.DataFrame(rows)


def plot_latency_curves(med: pd.DataFrame, out_dir: pathlib.Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    for (layer, agg, idx_mode), group in med.groupby(["schema_layer", "aggregation_depth", "index_mode"]):
        fig, ax = plt.subplots(figsize=(6, 4))
        for engine, sub in group.groupby("engine"):
            sub = sub.sort_values("scale_factor")
            ax.plot(sub["scale_factor"], sub["median_latency_seconds"], marker="o", label=engine)
        ax.set_xlabel("Scale Factor")
        ax.set_ylabel("Median Latency (s)")
        ax.set_title(f"{layer} | {agg} | {idx_mode}")
        ax.legend()
        fig.tight_layout()
        fname = out_dir / f"latency_{layer}_{agg}_{idx_mode}.png"
        fig.savefig(fname, dpi=150)
        plt.close(fig)
        print(f"wrote {fname}")


def main():
    parser = argparse.ArgumentParser(description="Analyze benchmark results and find crossovers")
    parser.add_argument("--input", default="results/raw_metrics.csv")
    parser.add_argument("--charts-dir", default="results/charts")
    parser.add_argument("--crossover-out", default="results/crossover_thresholds.csv")
    args = parser.parse_args()

    df = load_metrics(args.input)
    med = median_latency_table(df)
    med.to_csv("results/median_latency_by_config.csv", index=False)

    crossovers = find_crossovers(med)
    crossovers.to_csv(args.crossover_out, index=False)
    print(crossovers.to_string(index=False))

    plot_latency_curves(med, pathlib.Path(args.charts_dir))


if __name__ == "__main__":
    main()
