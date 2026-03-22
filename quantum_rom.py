"""
Quantum Read-Only Memory (QROM) Implementation
===============================================

Based on: "Trading T gates for dirty qubits in state preparation and unitary synthesis"
by Guang Hao Low, Vadym Kliuchnikov, and Luke Schaeffer (arXiv:1812.00954v2)

Implements a quantum circuit U such that:
    U |x⟩_n |0⟩_d = |x⟩_n |f(x)⟩_d

for any classical function f : F_2^n → F_2^d.

Two implementations provided:
1. naive_quantum_rom: Direct multiplexer using multi-controlled X gates.
   - No ancillas needed.
   - Gate count: O(2^n * d) multi-controlled gates.

2. selectswap_quantum_rom: SelectSwap network from the paper (Section 2).
   - Uses O(λ*d) ancilla qubits.
   - T-count: O(2^n/λ + λ*d), optimized at λ = O(sqrt(2^n / d)).
   - Achieves quadratic improvement over naive in T-count.

Date: February 27, 2026
"""

import math
from qiskit import QuantumCircuit, QuantumRegister


def _function_to_table(f, n, d):
    """
    Convert a function f : F_2^n → F_2^d to a lookup table.

    Args:
        f: Callable mapping int -> int, or a dict/list.
        n: Number of input bits.
        d: Number of output bits.

    Returns:
        List of 2^n integers, each in [0, 2^d).
    """
    N = 1 << n
    table = []
    for x in range(N):
        if callable(f):
            val = f(x)
        elif isinstance(f, dict):
            val = f[x]
        else:
            val = f[x]
        assert 0 <= val < (1 << d), f"f({x}) = {val} out of range for {d} bits"
        table.append(val)
    return table


# =============================================================================
# 1. Naive QROM (Select-only multiplexer)
# =============================================================================

def naive_quantum_rom(f, n, d):
    """
    Naive QROM implementation using multi-controlled X gates.

    For each x in {0, ..., 2^n - 1}, applies X^{f(x)} to the output register
    controlled on the address register being |x⟩.

    Circuit structure (Select operator, Eq. 6 of the paper):
        Select = Σ_{x=0}^{N-1} |x⟩⟨x| ⊗ X^{f(x)}

    Each term |x⟩⟨x| ⊗ X^{f(x)} is implemented by:
    1. Flip address qubits where x has bit 0 (creating an all-1 control pattern)
    2. Apply multi-controlled X to output bits where f(x) has bit 1
    3. Undo the flips

    Complexity:
        - Qubits: n + d (no ancillas)
        - Gates: O(2^n) multi-controlled X gates, each on n controls
        - T-count: O(2^n * d) after decomposition

    Args:
        f: Function f : F_2^n → F_2^d (callable, dict, or list).
        n: Number of input (address) qubits.
        d: Number of output (data) qubits.

    Returns:
        QuantumCircuit with registers addr[n] and data[d].
    """
    N = 1 << n
    table = _function_to_table(f, n, d)

    addr = QuantumRegister(n, 'addr')
    data = QuantumRegister(d, 'data')
    qc = QuantumCircuit(addr, data)

    for x in range(N):
        fx = table[x]
        if fx == 0:
            continue

        # Flip address qubits to create |1...1⟩ control pattern for state |x⟩
        for bit in range(n):
            if not (x >> bit) & 1:
                qc.x(addr[bit])

        # Apply multi-controlled X to each output bit where f(x) has a 1
        for bit in range(d):
            if (fx >> bit) & 1:
                if n == 1:
                    qc.cx(addr[0], data[bit])
                elif n == 2:
                    qc.ccx(addr[0], addr[1], data[bit])
                else:
                    qc.mcx(list(addr), data[bit])

        # Undo address flips
        for bit in range(n):
            if not (x >> bit) & 1:
                qc.x(addr[bit])

    return qc


# =============================================================================
# 2. SelectSwap QROM (Paper's main contribution)
# =============================================================================

def _apply_select(qc, ctrl_qubits, registers, table, lam, d):
    """
    Select operator (Eq. 6, Fig. 1a).

    Applies: Select = Σ_{q} |q⟩⟨q| ⊗ (X^{data[qλ]} ⊗ ... ⊗ X^{data[qλ+λ-1]})

    For each quotient value q, XOR the appropriate data values into
    the λ ancilla registers.

    Args:
        qc: QuantumCircuit to append gates to.
        ctrl_qubits: List of control qubits encoding quotient q.
        registers: List of λ QuantumRegisters (each d qubits).
        table: Lookup table of function values.
        lam: Number of registers (λ).
        d: Bits per data entry.
    """
    n_ctrl = len(ctrl_qubits)
    num_groups = 1 << n_ctrl if n_ctrl > 0 else 1

    for q in range(num_groups):
        # Flip control qubits to match pattern for q
        if n_ctrl > 0:
            for bit in range(n_ctrl):
                if not (q >> bit) & 1:
                    qc.x(ctrl_qubits[bit])

        # XOR data[qλ + j] into register j
        for j in range(lam):
            idx = q * lam + j
            if idx >= len(table):
                break
            val = table[idx]
            if val == 0:
                continue
            for bit in range(d):
                if (val >> bit) & 1:
                    if n_ctrl == 0:
                        qc.x(registers[j][bit])
                    elif n_ctrl == 1:
                        qc.cx(ctrl_qubits[0], registers[j][bit])
                    elif n_ctrl == 2:
                        qc.ccx(ctrl_qubits[0], ctrl_qubits[1],
                               registers[j][bit])
                    else:
                        qc.mcx(ctrl_qubits, registers[j][bit])

        # Undo flips
        if n_ctrl > 0:
            for bit in range(n_ctrl):
                if not (q >> bit) & 1:
                    qc.x(ctrl_qubits[bit])


def _apply_swap(qc, index_qubits, registers, d):
    """
    Swap network (Eq. 7, Fig. 1b).

    Moves the b-qubit register indexed by the value encoded in index_qubits
    to position 0, using controlled-swap operations.

    For each bit j of the index:
      For each pair of registers (i, i + 2^j) with i % 2^{j+1} == 0:
        Apply CSWAP controlled by index bit j.

    Args:
        qc: QuantumCircuit to append gates to.
        index_qubits: List of qubits encoding the remainder r.
        registers: List of λ QuantumRegisters.
        d: Bits per register.
    """
    k = len(index_qubits)
    lam = len(registers)

    for j in range(k):
        step = 1 << (j + 1)
        offset = 1 << j
        for i in range(0, lam, step):
            partner = i + offset
            if partner >= lam:
                break
            for bit in range(d):
                qc.cswap(index_qubits[j],
                         registers[i][bit],
                         registers[partner][bit])


def _apply_swap_inv(qc, index_qubits, registers, d):
    """
    Inverse of the Swap network. Applies layers in reverse order.
    (Each CSWAP is self-inverse, so we just reverse the layer ordering.)
    """
    k = len(index_qubits)
    lam = len(registers)

    for j in range(k - 1, -1, -1):
        step = 1 << (j + 1)
        offset = 1 << j
        for i in range(0, lam, step):
            partner = i + offset
            if partner >= lam:
                break
            for bit in range(d):
                qc.cswap(index_qubits[j],
                         registers[i][bit],
                         registers[partner][bit])


def selectswap_quantum_rom(f, n, d, lam=None):
    """
    SelectSwap QROM implementation (Section 2, Fig. 1c/d of the paper).

    The SelectSwap network splits the address x = q*λ + r into a quotient q
    and remainder r, then:
      1. Select (controlled by q): writes λ data values into λ ancilla registers
      2. Swap (controlled by r): routes the desired register to position 0

    For clean output (no garbage), we apply SelectSwap forward, copy the
    result to a dedicated output register, then apply SelectSwap† to
    uncompute the ancillas:

        |x⟩|0⟩_out|0⟩_anc → SelectSwap → |x⟩|0⟩_out|f(x)⟩_0|garb⟩
                            → CNOT copy → |x⟩|f(x)⟩_out|f(x)⟩_0|garb⟩
                            → SelectSwap† → |x⟩|f(x)⟩_out|0⟩_anc

    Complexity (Table 2 of the paper):
        - Qubits: n + d + λ*d ancillas
        - T-count: O(2^n/λ + λ*d), minimized at λ = O(sqrt(2^n / d))
        - Optimal T-count: O(sqrt(2^n * d))

    Args:
        f: Function f : F_2^n → F_2^d.
        n: Number of input (address) qubits.
        d: Number of output (data) qubits.
        lam: SelectSwap parameter λ (must be power of 2, ≤ 2^n).
             If None, automatically chosen to minimize T-count.

    Returns:
        QuantumCircuit with registers addr[n], out[d], and λ ancilla
        registers of d qubits each.
    """
    N = 1 << n
    table = _function_to_table(f, n, d)

    # Choose λ as a power of 2 to avoid quotient/remainder arithmetic
    if lam is None:
        lam_float = math.sqrt(N / max(d, 1))
        lam = max(1, min(N, 1 << round(math.log2(max(1, lam_float)))))
    lam = int(lam)

    assert lam >= 1 and lam <= N, f"λ={lam} must be in [1, {N}]"
    assert (lam & (lam - 1)) == 0, f"λ={lam} must be a power of 2"

    n_low = int(math.log2(lam)) if lam > 1 else 0   # bits for r
    n_high = n - n_low                                # bits for q

    # --- Allocate registers ---
    addr = QuantumRegister(n, 'addr')
    output = QuantumRegister(d, 'out')
    ancillas = [QuantumRegister(d, f'anc{j}') for j in range(lam)]

    qc = QuantumCircuit(addr, output, *ancillas)

    # Address decomposition: addr[0:n_low] = r, addr[n_low:n] = q
    high_bits = list(addr[n_low:n]) if n_high > 0 else []
    low_bits = list(addr[0:n_low]) if n_low > 0 else []

    # ---- Forward pass: SelectSwap ----
    qc.barrier(label='Select')
    _apply_select(qc, high_bits, ancillas, table, lam, d)

    if n_low > 0:
        qc.barrier(label='Swap')
        _apply_swap(qc, low_bits, ancillas, d)

    # ---- Copy result from ancilla register 0 to output ----
    qc.barrier(label='Copy')
    for bit in range(d):
        qc.cx(ancillas[0][bit], output[bit])

    # ---- Inverse pass: SelectSwap† (uncompute ancillas) ----
    if n_low > 0:
        qc.barrier(label='Swap†')
        _apply_swap_inv(qc, low_bits, ancillas, d)

    qc.barrier(label='Select†')
    # Select is self-inverse (XOR-based), so applying it again uncomputes
    _apply_select(qc, high_bits, ancillas, table, lam, d)

    return qc


# =============================================================================
# Unified API
# =============================================================================

def quantum_rom(f, n, d, method='selectswap', **kwargs):
    """
    Build a quantum circuit U such that U |x⟩_n |0⟩_d = |x⟩_n |f(x)⟩_d.

    Args:
        f: Function f : F_2^n → F_2^d (callable, dict, or list).
        n: Number of input qubits.
        d: Number of output qubits.
        method: 'naive' or 'selectswap' (default).
        **kwargs: Additional arguments (e.g., lam for selectswap).

    Returns:
        QuantumCircuit implementing the oracle.
    """
    if method == 'naive':
        return naive_quantum_rom(f, n, d)
    elif method == 'selectswap':
        return selectswap_quantum_rom(f, n, d, **kwargs)
    else:
        raise ValueError(f"Unknown method: {method}. Use 'naive' or 'selectswap'.")
