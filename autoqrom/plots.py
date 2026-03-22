"""
Visualization module for QROM sweep results.

Usage:
    python -m autoqrom.plots                    # generate all plots
    python -m autoqrom.plots --tsv path.tsv     # custom TSV path
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from autoqrom.config import SweepConfig


def load_results(tsv_path):
    """Load sweep results TSV into a list of dicts with typed values."""
    rows = []
    int_cols = {
        "n", "d", "lam", "total_qubits", "raw_depth", "decomp_depth",
        "cnot_count", "t_count_estimate", "unique_2q_pairs", "max_2q_pairs",
        "max_fanout",
    }
    float_cols = {"connectivity_density", "build_time_s", "transpile_time_s", "verify_time_s"}
    bool_cols = {"verified", "verification_passed"}

    with open(tsv_path, "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            typed = {}
            for k, v in row.items():
                if k in int_cols:
                    typed[k] = int(v) if v else 0
                elif k in float_cols:
                    typed[k] = float(v) if v else 0.0
                elif k in bool_cols:
                    typed[k] = v == "True"
                else:
                    typed[k] = v
            rows.append(typed)
    return rows


def filter_rows(rows, **kwargs):
    """Filter rows by exact field matches."""
    result = rows
    for key, val in kwargs.items():
        result = [r for r in result if r.get(key) == val]
    return result


# ---- Plot 1: Depth vs n ----

def plot_depth_vs_n(rows, results_dir):
    """Lines of decomp_depth vs n, paneled by d, for bijection function."""
    data = filter_rows(rows, func_name="bijection")
    if not data:
        return

    d_values = sorted(set(r["d"] for r in data))
    # Pick up to 4 representative d values
    d_show = [d for d in [2, 4, 6, 8] if d in d_values]
    if not d_show:
        d_show = d_values[:4]

    fig, axes = plt.subplots(1, len(d_show), figsize=(5 * len(d_show), 4), squeeze=False)
    fig.suptitle("Decomposed Depth vs n (bijection)", fontsize=14)

    for ax, d_val in zip(axes[0], d_show):
        sub = filter_rows(data, d=d_val)

        # Naive
        naive = filter_rows(sub, method="naive")
        ns = sorted(set(r["n"] for r in naive))
        depths = [next(r["decomp_depth"] for r in naive if r["n"] == n_) for n_ in ns]
        ax.plot(ns, depths, "k-o", label="naive", linewidth=2)

        # SelectSwap by lambda
        ss = filter_rows(sub, method="selectswap")
        lam_vals = sorted(set(r["lam"] for r in ss))
        for lv in lam_vals:
            subset = filter_rows(ss, lam=lv)
            ns_ss = sorted(set(r["n"] for r in subset))
            depths_ss = [next(r["decomp_depth"] for r in subset if r["n"] == n_) for n_ in ns_ss]
            ax.plot(ns_ss, depths_ss, "-s", label=f"ss lam={lv}", markersize=4)

        ax.set_title(f"d={d_val}")
        ax.set_xlabel("n (address qubits)")
        ax.set_ylabel("Decomposed depth")
        ax.set_yscale("log")
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(results_dir / "depth_vs_n.png", dpi=150)
    plt.close(fig)
    print("  Saved depth_vs_n.png")


# ---- Plot 2: CNOT count vs n ----

def plot_cnot_vs_n(rows, results_dir):
    """CNOT count vs n, paneled by d, bijection."""
    data = filter_rows(rows, func_name="bijection")
    if not data:
        return

    d_values = sorted(set(r["d"] for r in data))
    d_show = [d for d in [2, 4, 6, 8] if d in d_values] or d_values[:4]

    fig, axes = plt.subplots(1, len(d_show), figsize=(5 * len(d_show), 4), squeeze=False)
    fig.suptitle("CNOT Count vs n (bijection)", fontsize=14)

    for ax, d_val in zip(axes[0], d_show):
        sub = filter_rows(data, d=d_val)

        naive = filter_rows(sub, method="naive")
        ns = sorted(set(r["n"] for r in naive))
        cnots = [next(r["cnot_count"] for r in naive if r["n"] == n_) for n_ in ns]
        ax.plot(ns, cnots, "k-o", label="naive", linewidth=2)

        ss = filter_rows(sub, method="selectswap")
        lam_vals = sorted(set(r["lam"] for r in ss))
        for lv in lam_vals:
            subset = filter_rows(ss, lam=lv)
            ns_ss = sorted(set(r["n"] for r in subset))
            cnots_ss = [next(r["cnot_count"] for r in subset if r["n"] == n_) for n_ in ns_ss]
            ax.plot(ns_ss, cnots_ss, "-s", label=f"ss lam={lv}", markersize=4)

        ax.set_title(f"d={d_val}")
        ax.set_xlabel("n")
        ax.set_ylabel("CNOT count")
        ax.set_yscale("log")
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(results_dir / "cnot_vs_n.png", dpi=150)
    plt.close(fig)
    print("  Saved cnot_vs_n.png")


# ---- Plot 3: T-count vs n ----

def plot_tcount_vs_n(rows, results_dir):
    """Analytical T-count estimate vs n, paneled by d, bijection."""
    data = filter_rows(rows, func_name="bijection")
    if not data:
        return

    d_values = sorted(set(r["d"] for r in data))
    d_show = [d for d in [2, 4, 6, 8] if d in d_values] or d_values[:4]

    fig, axes = plt.subplots(1, len(d_show), figsize=(5 * len(d_show), 4), squeeze=False)
    fig.suptitle("T-count Estimate vs n (bijection)", fontsize=14)

    for ax, d_val in zip(axes[0], d_show):
        sub = filter_rows(data, d=d_val)

        naive = filter_rows(sub, method="naive")
        ns = sorted(set(r["n"] for r in naive))
        tc = [next(r["t_count_estimate"] for r in naive if r["n"] == n_) for n_ in ns]
        ax.plot(ns, tc, "k-o", label="naive", linewidth=2)

        ss = filter_rows(sub, method="selectswap")
        lam_vals = sorted(set(r["lam"] for r in ss))
        for lv in lam_vals:
            subset = filter_rows(ss, lam=lv)
            ns_ss = sorted(set(r["n"] for r in subset))
            tc_ss = [next(r["t_count_estimate"] for r in subset if r["n"] == n_) for n_ in ns_ss]
            ax.plot(ns_ss, tc_ss, "-s", label=f"ss lam={lv}", markersize=4)

        ax.set_title(f"d={d_val}")
        ax.set_xlabel("n")
        ax.set_ylabel("T-count (estimate)")
        ax.set_yscale("log")
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(results_dir / "tcount_vs_n.png", dpi=150)
    plt.close(fig)
    print("  Saved tcount_vs_n.png")


# ---- Plot 4: Qubit count vs n ----

def plot_qubits_vs_n(rows, results_dir):
    """Total qubit count vs n, paneled by d, bijection."""
    data = filter_rows(rows, func_name="bijection")
    if not data:
        return

    d_values = sorted(set(r["d"] for r in data))
    d_show = [d for d in [2, 4, 6, 8] if d in d_values] or d_values[:4]

    fig, axes = plt.subplots(1, len(d_show), figsize=(5 * len(d_show), 4), squeeze=False)
    fig.suptitle("Qubit Count vs n (bijection)", fontsize=14)

    for ax, d_val in zip(axes[0], d_show):
        sub = filter_rows(data, d=d_val)

        naive = filter_rows(sub, method="naive")
        ns = sorted(set(r["n"] for r in naive))
        qs = [next(r["total_qubits"] for r in naive if r["n"] == n_) for n_ in ns]
        ax.plot(ns, qs, "k-o", label="naive", linewidth=2)

        ss = filter_rows(sub, method="selectswap")
        lam_vals = sorted(set(r["lam"] for r in ss))
        for lv in lam_vals:
            subset = filter_rows(ss, lam=lv)
            ns_ss = sorted(set(r["n"] for r in subset))
            qs_ss = [next(r["total_qubits"] for r in subset if r["n"] == n_) for n_ in ns_ss]
            ax.plot(ns_ss, qs_ss, "-s", label=f"ss lam={lv}", markersize=4)

        ax.set_title(f"d={d_val}")
        ax.set_xlabel("n")
        ax.set_ylabel("Total qubits")
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(results_dir / "qubits_vs_n.png", dpi=150)
    plt.close(fig)
    print("  Saved qubits_vs_n.png")


# ---- Plot 5: Pareto front (depth vs qubits) ----

def plot_pareto_depth_qubits(rows, results_dir):
    """Scatter of decomp_depth vs total_qubits, Pareto front highlighted."""
    data = filter_rows(rows, func_name="bijection")
    if not data:
        return

    fig, ax = plt.subplots(figsize=(8, 6))

    for method, color, marker in [("naive", "tab:blue", "o"), ("selectswap", "tab:orange", "s")]:
        sub = filter_rows(data, method=method)
        x = [r["total_qubits"] for r in sub]
        y = [r["decomp_depth"] for r in sub]
        ax.scatter(x, y, c=color, marker=marker, alpha=0.5, label=method, s=20)

    # Pareto front (minimize both)
    points = [(r["total_qubits"], r["decomp_depth"]) for r in data]
    points.sort()
    pareto = []
    min_y = float("inf")
    for px, py in points:
        if py < min_y:
            pareto.append((px, py))
            min_y = py
    if pareto:
        px, py = zip(*pareto)
        ax.step(px, py, "r-", linewidth=2, label="Pareto front", where="post")

    ax.set_xlabel("Total qubits")
    ax.set_ylabel("Decomposed depth")
    ax.set_yscale("log")
    ax.set_title("Pareto: Depth vs Qubits (bijection)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(results_dir / "pareto_depth_qubits.png", dpi=150)
    plt.close(fig)
    print("  Saved pareto_depth_qubits.png")


# ---- Plot 6: Pareto front (depth vs CNOT) ----

def plot_pareto_depth_cnot(rows, results_dir):
    """Scatter of decomp_depth vs cnot_count, Pareto front highlighted."""
    data = filter_rows(rows, func_name="bijection")
    if not data:
        return

    fig, ax = plt.subplots(figsize=(8, 6))

    for method, color, marker in [("naive", "tab:blue", "o"), ("selectswap", "tab:orange", "s")]:
        sub = filter_rows(data, method=method)
        x = [r["cnot_count"] for r in sub]
        y = [r["decomp_depth"] for r in sub]
        ax.scatter(x, y, c=color, marker=marker, alpha=0.5, label=method, s=20)

    points = [(r["cnot_count"], r["decomp_depth"]) for r in data]
    points.sort()
    pareto = []
    min_y = float("inf")
    for px, py in points:
        if py < min_y:
            pareto.append((px, py))
            min_y = py
    if pareto:
        px, py = zip(*pareto)
        ax.step(px, py, "r-", linewidth=2, label="Pareto front", where="post")

    ax.set_xlabel("CNOT count")
    ax.set_ylabel("Decomposed depth")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title("Pareto: Depth vs CNOT Count (bijection)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(results_dir / "pareto_depth_cnot.png", dpi=150)
    plt.close(fig)
    print("  Saved pareto_depth_cnot.png")


# ---- Plot 7: Optimal lambda heatmap ----

def plot_optimal_lambda(rows, results_dir):
    """Heatmap of (n,d) showing lambda that minimizes depth."""
    data = filter_rows(rows, func_name="bijection", method="selectswap")
    if not data:
        return

    ns = sorted(set(r["n"] for r in data))
    ds = sorted(set(r["d"] for r in data))

    grid = np.full((len(ds), len(ns)), np.nan)
    for i, d_val in enumerate(ds):
        for j, n_val in enumerate(ns):
            sub = [r for r in data if r["n"] == n_val and r["d"] == d_val]
            if sub:
                best = min(sub, key=lambda r: r["decomp_depth"])
                grid[i, j] = np.log2(best["lam"]) if best["lam"] > 0 else 0

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(grid, aspect="auto", origin="lower", cmap="viridis")
    ax.set_xticks(range(len(ns)))
    ax.set_xticklabels(ns)
    ax.set_yticks(range(len(ds)))
    ax.set_yticklabels(ds)
    ax.set_xlabel("n (address qubits)")
    ax.set_ylabel("d (data qubits)")
    ax.set_title("Optimal log2(lambda) minimizing depth (bijection)")

    # Annotate cells
    for i in range(len(ds)):
        for j in range(len(ns)):
            if not np.isnan(grid[i, j]):
                ax.text(j, i, f"{int(grid[i,j])}", ha="center", va="center",
                        color="white", fontsize=9, fontweight="bold")

    plt.colorbar(im, ax=ax, label="log2(lambda)")
    plt.tight_layout()
    fig.savefig(results_dir / "optimal_lambda.png", dpi=150)
    plt.close(fig)
    print("  Saved optimal_lambda.png")


# ---- Plot 8: Connectivity density heatmap ----

def plot_connectivity_density(rows, results_dir):
    """Side-by-side heatmaps of connectivity density: naive vs best selectswap."""
    data = filter_rows(rows, func_name="bijection")
    if not data:
        return

    ns = sorted(set(r["n"] for r in data))
    ds = sorted(set(r["d"] for r in data))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Connectivity Density (bijection)", fontsize=14)

    for ax, method, title in zip(axes, ["naive", "selectswap"], ["Naive", "SelectSwap (best lam)"]):
        grid = np.full((len(ds), len(ns)), np.nan)
        sub = filter_rows(data, method=method)
        for i, d_val in enumerate(ds):
            for j, n_val in enumerate(ns):
                matches = [r for r in sub if r["n"] == n_val and r["d"] == d_val]
                if matches:
                    if method == "selectswap":
                        best = min(matches, key=lambda r: r["decomp_depth"])
                        grid[i, j] = best["connectivity_density"]
                    else:
                        grid[i, j] = matches[0]["connectivity_density"]

        im = ax.imshow(grid, aspect="auto", origin="lower", cmap="YlOrRd", vmin=0, vmax=1)
        ax.set_xticks(range(len(ns)))
        ax.set_xticklabels(ns)
        ax.set_yticks(range(len(ds)))
        ax.set_yticklabels(ds)
        ax.set_xlabel("n")
        ax.set_ylabel("d")
        ax.set_title(title)

        for i_r in range(len(ds)):
            for j_c in range(len(ns)):
                if not np.isnan(grid[i_r, j_c]):
                    ax.text(j_c, i_r, f"{grid[i_r,j_c]:.2f}", ha="center", va="center",
                            fontsize=7)

    plt.colorbar(im, ax=axes, label="Density")
    plt.tight_layout()
    fig.savefig(results_dir / "connectivity_density.png", dpi=150)
    plt.close(fig)
    print("  Saved connectivity_density.png")


# ---- Plot 9: Scaling validation (log-log) ----

def plot_scaling_validation(rows, results_dir):
    """Log-log CNOT vs N=2^n with O(N*d) and O(sqrt(N*d)) reference lines."""
    data = filter_rows(rows, func_name="bijection")
    if not data:
        return

    d_values = sorted(set(r["d"] for r in data))
    d_show = [d for d in [2, 4, 8] if d in d_values] or d_values[:3]

    fig, axes = plt.subplots(1, len(d_show), figsize=(5 * len(d_show), 4), squeeze=False)
    fig.suptitle("CNOT Scaling Validation (log-log, bijection)", fontsize=14)

    for ax, d_val in zip(axes[0], d_show):
        sub = filter_rows(data, d=d_val)

        # Naive
        naive = filter_rows(sub, method="naive")
        ns = sorted(set(r["n"] for r in naive))
        Ns = [2**n_ for n_ in ns]
        cnots = [next(r["cnot_count"] for r in naive if r["n"] == n_) for n_ in ns]
        if cnots and any(c > 0 for c in cnots):
            ax.loglog(Ns, cnots, "k-o", label="naive", linewidth=2)

        # Best selectswap (min depth per n)
        ss = filter_rows(sub, method="selectswap")
        ns_ss = sorted(set(r["n"] for r in ss))
        Ns_ss = [2**n_ for n_ in ns_ss]
        best_cnots = []
        for n_ in ns_ss:
            matches = [r for r in ss if r["n"] == n_]
            best_cnots.append(min(r["cnot_count"] for r in matches))
        if best_cnots and any(c > 0 for c in best_cnots):
            ax.loglog(Ns_ss, best_cnots, "r-s", label="selectswap (best)", linewidth=2)

        # Reference lines
        N_ref = np.array([2**n_ for n_ in range(min(ns), max(ns) + 1)])
        if len(N_ref) > 1 and cnots and cnots[0] > 0:
            c_linear = cnots[0] / (Ns[0] * d_val)
            ax.loglog(N_ref, c_linear * N_ref * d_val, "b--", alpha=0.4, label="O(N*d)")
            c_sqrt = cnots[0] / np.sqrt(Ns[0] * d_val)
            ax.loglog(N_ref, c_sqrt * np.sqrt(N_ref * d_val), "g--", alpha=0.4, label="O(sqrt(N*d))")

        ax.set_title(f"d={d_val}")
        ax.set_xlabel("N = 2^n")
        ax.set_ylabel("CNOT count")
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(results_dir / "scaling_validation.png", dpi=150)
    plt.close(fig)
    print("  Saved scaling_validation.png")


# ---- Main entry ----

def generate_all_plots(tsv_path=None, results_dir=None):
    """Generate all plots from sweep results."""
    config = SweepConfig()
    if tsv_path is None:
        tsv_path = config.tsv_path
    if results_dir is None:
        results_dir = config.results_dir

    tsv_path = Path(tsv_path)
    results_dir = Path(results_dir)

    if not tsv_path.exists():
        print(f"No results file found at {tsv_path}")
        print("Run the sweep first: python -m autoqrom.sweep")
        return

    print(f"Loading results from {tsv_path}")
    rows = load_results(tsv_path)
    print(f"  {len(rows)} data points loaded\n")

    print("Generating plots:")
    plot_depth_vs_n(rows, results_dir)
    plot_cnot_vs_n(rows, results_dir)
    plot_tcount_vs_n(rows, results_dir)
    plot_qubits_vs_n(rows, results_dir)
    plot_pareto_depth_qubits(rows, results_dir)
    plot_pareto_depth_cnot(rows, results_dir)
    plot_optimal_lambda(rows, results_dir)
    plot_connectivity_density(rows, results_dir)
    plot_scaling_validation(rows, results_dir)
    print("\nAll plots generated.")


def main():
    tsv_path = None
    if "--tsv" in sys.argv:
        idx = sys.argv.index("--tsv")
        if idx + 1 < len(sys.argv):
            tsv_path = sys.argv[idx + 1]
    generate_all_plots(tsv_path=tsv_path)


if __name__ == "__main__":
    main()
