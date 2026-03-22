"""Circuit metric extraction and connectivity analysis."""

import math
import time
from dataclasses import dataclass, field
from collections import defaultdict

from qiskit import transpile
from qiskit.circuit import QuantumCircuit

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from quantum_rom import quantum_rom

from .config import SweepConfig


@dataclass
class CircuitMetrics:
    """All metrics for a single QROM circuit configuration."""

    # Identity
    n: int = 0
    d: int = 0
    method: str = ""
    lam: int = 0  # 0 means N/A (naive)
    func_name: str = ""

    # Pre-decomposition
    total_qubits: int = 0
    raw_depth: int = 0
    raw_gate_counts: dict = field(default_factory=dict)

    # Post-decomposition
    decomp_depth: int = 0
    decomp_gate_counts: dict = field(default_factory=dict)
    cnot_count: int = 0

    # T-count (analytical estimate)
    t_count_estimate: int = 0

    # Connectivity
    unique_2q_pairs: int = 0
    max_2q_pairs: int = 0
    connectivity_density: float = 0.0
    max_fanout: int = 0

    # Verification
    verified: bool = False
    verification_passed: bool = False

    # Timing
    build_time_s: float = 0.0
    transpile_time_s: float = 0.0
    verify_time_s: float = 0.0

    # Error tracking
    error: str = ""


# ---- T-count estimation ----

def precompute_mcx_t_costs(max_controls=10):
    """
    Analytical T-count per MCX gate by number of controls.

    - 1 control (CX): 0 T-gates
    - 2 controls (CCX/Toffoli): 7 T-gates
    - n controls (n >= 3): Uses decomposition into 2(n-2) Toffolis -> 14*(n-2) T-gates
    """
    costs = {0: 0, 1: 0, 2: 7}
    for c in range(3, max_controls + 1):
        costs[c] = 14 * (c - 2)
    return costs


_MCX_T_COSTS = precompute_mcx_t_costs(10)


def estimate_t_count(qc):
    """
    Estimate T-count from a raw (pre-decomposition) circuit.

    Counts MCX gates by control count, CSWAP as 7 T-gates each.
    """
    t_total = 0
    for instruction in qc.data:
        name = instruction.operation.name
        num_qubits = instruction.operation.num_qubits
        if name == "mcx":
            n_controls = num_qubits - 1
            t_total += _MCX_T_COSTS.get(n_controls, 14 * (n_controls - 2))
        elif name == "ccx":
            t_total += 7
        elif name == "cswap":
            t_total += 7  # Fredkin = 1 Toffoli equivalent
    return t_total


# ---- Connectivity analysis ----

def extract_connectivity(transpiled_circuit):
    """
    Analyze 2-qubit gate connectivity in a transpiled circuit.

    Returns:
        (unique_pairs, max_possible_pairs, density, max_fanout)
    """
    n = transpiled_circuit.num_qubits
    if n < 2:
        return (0, 0, 0.0, 0)

    adjacency = defaultdict(set)
    for instruction in transpiled_circuit.data:
        if instruction.operation.num_qubits == 2:
            qubits = [transpiled_circuit.find_bit(q).index for q in instruction.qubits]
            q0, q1 = sorted(qubits)
            adjacency[q0].add(q1)
            adjacency[q1].add(q0)

    unique_pairs = sum(1 for q in adjacency for neighbor in adjacency[q] if neighbor > q)
    max_pairs = n * (n - 1) // 2
    density = unique_pairs / max_pairs if max_pairs > 0 else 0.0
    max_fanout = max((len(neighbors) for neighbors in adjacency.values()), default=0)

    return (unique_pairs, max_pairs, density, max_fanout)


# ---- Main extraction pipeline ----

def extract_metrics(n, d, method, lam, func_name, func, config):
    """
    Full metric extraction pipeline: build -> transpile -> analyze.

    Args:
        n, d: QROM parameters
        method: 'naive' or 'selectswap'
        lam: lambda parameter (ignored for naive)
        func_name: name string for the test function
        func: callable f(x) -> int
        config: SweepConfig instance

    Returns:
        CircuitMetrics with all fields populated
    """
    m = CircuitMetrics(
        n=n, d=d, method=method,
        lam=lam if method == "selectswap" else 0,
        func_name=func_name,
    )

    # Build circuit
    try:
        t0 = time.time()
        kwargs = {"lam": lam} if method == "selectswap" else {}
        qc = quantum_rom(func, n, d, method=method, **kwargs)
        m.build_time_s = time.time() - t0
    except Exception as e:
        m.error = f"build: {e}"
        return m

    m.total_qubits = qc.num_qubits
    m.raw_depth = qc.depth()
    m.raw_gate_counts = dict(qc.count_ops())
    m.t_count_estimate = estimate_t_count(qc)

    # Transpile
    try:
        t0 = time.time()
        tqc = transpile(
            qc,
            basis_gates=config.hardware_basis,
            optimization_level=config.opt_level,
        )
        m.transpile_time_s = time.time() - t0
    except Exception as e:
        m.error = f"transpile: {e}"
        return m

    m.decomp_depth = tqc.depth()
    m.decomp_gate_counts = dict(tqc.count_ops())
    m.cnot_count = m.decomp_gate_counts.get("cx", 0)

    # Connectivity
    try:
        pairs, max_p, density, fanout = extract_connectivity(tqc)
        m.unique_2q_pairs = pairs
        m.max_2q_pairs = max_p
        m.connectivity_density = density
        m.max_fanout = fanout
    except Exception as e:
        m.error = f"connectivity: {e}"

    return m


def metrics_to_row(m):
    """Convert CircuitMetrics to a flat dict for TSV output."""
    return {
        "n": m.n,
        "d": m.d,
        "method": m.method,
        "lam": m.lam,
        "func_name": m.func_name,
        "total_qubits": m.total_qubits,
        "raw_depth": m.raw_depth,
        "decomp_depth": m.decomp_depth,
        "cnot_count": m.cnot_count,
        "t_count_estimate": m.t_count_estimate,
        "unique_2q_pairs": m.unique_2q_pairs,
        "max_2q_pairs": m.max_2q_pairs,
        "connectivity_density": f"{m.connectivity_density:.4f}",
        "max_fanout": m.max_fanout,
        "verified": m.verified,
        "verification_passed": m.verification_passed,
        "build_time_s": f"{m.build_time_s:.3f}",
        "transpile_time_s": f"{m.transpile_time_s:.3f}",
        "verify_time_s": f"{m.verify_time_s:.3f}",
        "error": m.error,
    }
