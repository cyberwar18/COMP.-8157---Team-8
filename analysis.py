import pandas as pd

df = pd.read_csv("results/raw_metrics.csv")

print(df.shape)
print(df.head())
print(df["engine"].unique())
print(df["scale_factor"].unique())


summary = df.groupby(
    ["engine", "schema_layer", "scale_factor", "aggregation_depth", "index_mode"]
)["latency_seconds"].median().reset_index()

summary = summary.rename(columns={"latency_seconds": "median_latency"})

print(summary.head(10))
print("Total configuration cells:", len(summary))

summary.to_csv("results/median_latency_summary.csv", index=False)
print("Saved summary to results/median_latency_summary.csv")

import matplotlib.pyplot as plt

# Filter down to just the one query shape/mode we want to plot,
# and just the OLTP layer
subset = summary[
    (summary["schema_layer"] == "oltp") &
    (summary["aggregation_depth"] == "multi_group_by") &
    (summary["index_mode"] == "full_scan")
]

print(subset)

fig, ax = plt.subplots(figsize=(7, 5))

for engine in ["duckdb", "mysql"]:
    engine_data = subset[subset["engine"] == engine].sort_values("scale_factor")
    ax.plot(engine_data["scale_factor"], engine_data["median_latency"], marker="o", label=engine)

ax.set_yscale("log")
ax.set_xlabel("Scale factor")
ax.set_ylabel("Median latency (seconds, log scale)")
ax.set_title("multi_group_by / full_scan — MySQL vs DuckDB")
ax.legend()
ax.grid(True, alpha=0.3)

fig.savefig("results/chart_multi_group_by_full_scan.png", bbox_inches="tight")
print("Saved chart to results/chart_multi_group_by_full_scan.png")

def plot_latency_vs_scale(aggregation_depth, index_mode, schema_layer="oltp"):
    subset = summary[
        (summary["schema_layer"] == schema_layer) &
        (summary["aggregation_depth"] == aggregation_depth) &
        (summary["index_mode"] == index_mode)
    ]

    fig, ax = plt.subplots(figsize=(7, 5))
    for engine in ["duckdb", "mysql"]:
        engine_data = subset[subset["engine"] == engine].sort_values("scale_factor")
        ax.plot(engine_data["scale_factor"], engine_data["median_latency"], marker="o", label=engine)

    ax.set_yscale("log")
    ax.set_xlabel("Scale factor")
    ax.set_ylabel("Median latency (seconds, log scale)")
    ax.set_title(f"{aggregation_depth} / {index_mode} ({schema_layer})")
    ax.legend()
    ax.grid(True, alpha=0.3)

    filename = f"results/chart_{schema_layer}_{aggregation_depth}_{index_mode}.png"
    fig.savefig(filename, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {filename}")


for depth in ["single_group_by", "multi_group_by", "nested_subquery"]:
    plot_latency_vs_scale(depth, "full_scan")


def compare_oltp_vs_olap(scale_factor=5):
    for engine in ["duckdb", "mysql"]:
        for depth in ["single_group_by", "multi_group_by", "nested_subquery"]:
            oltp = summary[
                (summary["engine"] == engine) &
                (summary["schema_layer"] == "oltp") &
                (summary["aggregation_depth"] == depth) &
                (summary["index_mode"] == "full_scan") &
                (summary["scale_factor"] == scale_factor)
            ]["median_latency"]

            olap = summary[
                (summary["engine"] == engine) &
                (summary["schema_layer"] == "olap") &
                (summary["aggregation_depth"] == depth) &
                (summary["index_mode"] == "full_scan") &
                (summary["scale_factor"] == scale_factor)
            ]["median_latency"]

            if len(oltp) and len(olap):
                speedup = oltp.values[0] / olap.values[0]
                verdict = "OLAP faster" if speedup > 1 else "OLTP faster"
                print(f"{engine:7} {depth:16} speedup={speedup:.2f}x  ({verdict})")



compare_oltp_vs_olap()


def plot_index_modes(engine="duckdb", aggregation_depth="multi_group_by",
                     scale_factor=5, schema_layer="oltp"):
    subset = summary[
        (summary["engine"] == engine) &
        (summary["schema_layer"] == schema_layer) &
        (summary["aggregation_depth"] == aggregation_depth) &
        (summary["scale_factor"] == scale_factor)
    ].sort_values("median_latency")

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(subset["index_mode"], subset["median_latency"])
    ax.set_yscale("log")
    ax.set_ylabel("Median latency (seconds, log scale)")
    ax.set_title(f"Index mode impact — {engine} / {aggregation_depth} (SF-{scale_factor})")
    ax.grid(True, axis="y", alpha=0.3)


    for i, val in enumerate(subset["median_latency"]):
        ax.text(i, val, f"{val:.4f}s", ha="center", va="bottom", fontsize=9)

    filename = f"results/chart_indexmode_{engine}_{aggregation_depth}_sf{scale_factor}.png"
    fig.savefig(filename, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {filename}")


plot_index_modes()


def plot_small_multiples(schema_layer="oltp", index_mode="full_scan"):
    shapes = ["single_group_by", "multi_group_by", "nested_subquery"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)

    for ax, depth in zip(axes, shapes):
        subset = summary[
            (summary["schema_layer"] == schema_layer) &
            (summary["aggregation_depth"] == depth) &
            (summary["index_mode"] == index_mode)
        ]
        for engine in ["duckdb", "mysql"]:
            engine_data = subset[subset["engine"] == engine].sort_values("scale_factor")
            ax.plot(engine_data["scale_factor"], engine_data["median_latency"],
                    marker="o", label=engine)
        ax.set_yscale("log")
        ax.set_xlabel("Scale factor")
        ax.set_title(depth)
        ax.grid(True, alpha=0.3)
        ax.set_xticks([1, 5, 10])

    axes[0].set_ylabel("Median latency (seconds, log scale)")
    axes[0].legend()

    filename = f"results/chart_smallmultiples_{schema_layer}_{index_mode}.png"
    fig.savefig(filename, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {filename}")


plot_small_multiples()


mem_summary = df.groupby(
    ["engine", "schema_layer", "scale_factor", "aggregation_depth", "index_mode"]
)["peak_rss_mb"].median().reset_index()

def plot_duckdb_memory(schema_layer="oltp", index_mode="full_scan"):
    subset = mem_summary[
        (mem_summary["engine"] == "duckdb") &
        (mem_summary["schema_layer"] == schema_layer) &
        (mem_summary["index_mode"] == index_mode)
    ]

    fig, ax = plt.subplots(figsize=(7, 5))
    for depth in ["single_group_by", "multi_group_by", "nested_subquery"]:
        depth_data = subset[subset["aggregation_depth"] == depth].sort_values("scale_factor")
        ax.plot(depth_data["scale_factor"], depth_data["peak_rss_mb"],
                marker="o", label=depth)

    ax.set_xlabel("Scale factor")
    ax.set_ylabel("Peak RSS (MB)")
    ax.set_title(f"DuckDB in-process peak memory ({schema_layer})")
    ax.set_xticks([1, 5, 10])
    ax.legend()
    ax.grid(True, alpha=0.3)

    filename = f"results/chart_memory_duckdb_{schema_layer}_{index_mode}.png"
    fig.savefig(filename, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {filename}")


plot_duckdb_memory()