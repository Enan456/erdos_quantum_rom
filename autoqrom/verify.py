"""Statevector verification for QROM circuits."""

import time
import numpy as np
from qiskit.quantum_info import Statevector


def verify_circuit(qc, f, n, d, max_qubits=24):
    """
    Verify that circuit qc implements U|x>|0> = |x>|f(x)> for all x.

    Uses statevector simulation. Skips if circuit exceeds max_qubits.

    Args:
        qc: QuantumCircuit to verify
        f: callable f(x) -> int
        n: number of address qubits
        d: number of data qubits
        max_qubits: skip simulation above this qubit count

    Returns:
        (passed: bool, elapsed: float)
        passed is None if skipped due to qubit limit
    """
    total = qc.num_qubits
    if total > max_qubits:
        return (None, 0.0)

    N = 1 << n
    t0 = time.time()

    for x in range(N):
        # Prepare |x>|0...0>
        init = [0] * total
        for bit in range(n):
            if (x >> bit) & 1:
                init[bit] = 1
        label_str = "".join(str(init[total - 1 - i]) for i in range(total))
        sv = Statevector.from_label(label_str).evolve(qc)

        # Expected state: addr=x, data=f(x), ancilla=0
        fx = f(x)
        expected_idx = x
        for bit in range(d):
            if (fx >> bit) & 1:
                expected_idx |= 1 << (n + bit)

        prob = abs(sv.data[expected_idx]) ** 2
        if not np.isclose(prob, 1.0, atol=1e-8):
            return (False, time.time() - t0)

    return (True, time.time() - t0)
