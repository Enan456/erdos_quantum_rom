"""
QROM parameter sweep engine.

Usage:
    python -m autoqrom.sweep              # full sweep n,d in [2,8]
    python -m autoqrom.sweep --small      # quick test: n,d in [2,3]
"""

import csv
import math
import sys
import time
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quantum_rom import quantum_rom
from autoqrom.config import SweepConfig
from autoqrom.functions import get_test_functions
from autoqrom.metrics import extract_metrics, metrics_to_row
from autoqrom.verify import verify_circuit


TSV_COLUMNS = [
    "n", "d", "method", "lam", "func_name",
    "total_qubits", "raw_depth", "decomp_depth",
    "cnot_count", "t_count_estimate",
    "unique_2q_pairs", "max_2q_pairs", "connectivity_density", "max_fanout",
    "verified", "verification_passed",
    "build_time_s", "transpile_time_s", "verify_time_s",
    "error",
]


def generate_grid(config):
    """
    Generate all (n, d, method, lam, func_name, func) configurations.

    For each (n, d):
      - 1 naive config (lam=None) x 3 functions
      - (n+1) selectswap configs (lam = 1, 2, 4, ..., 2^n) x 3 functions
    """
    configs = []
    for n in config.n_range:
        for d in config.d_range:
            funcs = get_test_functions(n, d)
            N = 1 << n

            # Naive
            for fname, func in funcs:
                configs.append((n, d, "naive", None, fname, func))

            # SelectSwap: lam = 1, 2, 4, ..., 2^n
            lam = 1
            while lam <= N:
                for fname, func in funcs:
                    configs.append((n, d, "selectswap", lam, fname, func))
                lam *= 2

    return configs


def load_completed(tsv_path):
    """Load already-completed config keys from TSV for crash resilience."""
    completed = set()
    if not tsv_path.exists():
        return completed
    with open(tsv_path, "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            key = (
                int(row["n"]), int(row["d"]),
                row["method"], int(row["lam"]),
                row["func_name"],
            )
            completed.add(key)
    return completed


def config_key(n, d, method, lam, func_name):
    return (n, d, method, lam if lam is not None else 0, func_name)


def run_sweep(config=None):
    """Execute the full parameter sweep."""
    if config is None:
        config = SweepConfig()

    config.results_dir.mkdir(parents=True, exist_ok=True)
    grid = generate_grid(config)
    total = len(grid)
    completed = load_completed(config.tsv_path)

    print(f"QROM Parameter Sweep")
    print(f"  n range: {list(config.n_range)}")
    print(f"  d range: {list(config.d_range)}")
    print(f"  Total configs: {total}")
    print(f"  Already completed: {len(completed)}")
    print(f"  Output: {config.tsv_path}")
    print()

    # Open TSV for incremental writes
    write_header = not config.tsv_path.exists() or config.tsv_path.stat().st_size == 0
    tsv_file = open(config.tsv_path, "a", newline="")
    writer = csv.DictWriter(tsv_file, fieldnames=TSV_COLUMNS, delimiter="\t")
    if write_header:
        writer.writeheader()
        tsv_file.flush()

    sweep_start = time.time()
    done = len(completed)

    for i, (n, d, method, lam, fname, func) in enumerate(grid):
        key = config_key(n, d, method, lam, fname)
        if key in completed:
            continue

        done += 1
        t0 = time.time()

        # Extract metrics (build + transpile + connectivity)
        try:
            m = extract_metrics(n, d, method, lam, fname, func, config)
        except Exception as e:
            from autoqrom.metrics import CircuitMetrics
            m = CircuitMetrics(n=n, d=d, method=method,
                               lam=lam if lam else 0,
                               func_name=fname, error=str(e))

        # Verification (statevector sim if within qubit limit)
        if not m.error and m.total_qubits <= config.max_sim_qubits:
            try:
                kwargs = {"lam": lam} if method == "selectswap" else {}
                qc = quantum_rom(func, n, d, method=method, **kwargs)
                passed, vtime = verify_circuit(qc, func, n, d, config.max_sim_qubits)
                m.verified = passed is not None
                m.verification_passed = bool(passed) if passed is not None else False
                m.verify_time_s = vtime
            except Exception as e:
                m.error = f"verify: {e}"

        elapsed = time.time() - t0
        lam_str = f"lam={lam}" if lam is not None else "     "
        status = ""
        if m.error:
            status = f"  ERR: {m.error[:40]}"
        elif m.verified and not m.verification_passed:
            status = "  VERIFY FAILED"

        print(
            f"[{done:>4}/{total}] n={n} d={d} {method:<10} {lam_str:<8} "
            f"{fname:<10} qubits={m.total_qubits:<4} depth={m.decomp_depth:<6} "
            f"cnot={m.cnot_count:<6} ({elapsed:.1f}s){status}"
        )

        # Write row
        row = metrics_to_row(m)
        writer.writerow(row)
        tsv_file.flush()

    tsv_file.close()
    total_time = time.time() - sweep_start
    print(f"\nSweep complete in {total_time:.0f}s. Results: {config.tsv_path}")


def main():
    config = SweepConfig()

    if "--small" in sys.argv:
        config.n_range = range(2, 4)
        config.d_range = range(2, 4)
        print("Running small sweep (n,d in [2,3])...\n")

    run_sweep(config)


if __name__ == "__main__":
    main()
