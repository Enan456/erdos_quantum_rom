"""
Quantum ROM Demo for n = d = 3
================================

Demonstrates both the naive and SelectSwap QROM implementations
from quantum_rom.py on a sample function f : F_2^3 -> F_2^3.

Verifies correctness using statevector simulation: for every basis
state |x>, checks that U |x>|0> = |x>|f(x)>.

Based on: "Trading T gates for dirty qubits in state preparation
and unitary synthesis" (arXiv:1812.00954v2)
"""

import numpy as np
from qiskit.quantum_info import Statevector
from quantum_rom import naive_quantum_rom, selectswap_quantum_rom


def verify_qrom(qc, f, n, d, label=""):
    """
    Verify that circuit qc implements U |x>|0> = |x>|f(x)> for all x.

    Uses statevector simulation. The circuit may have ancilla qubits
    beyond the first n + d; these must return to |0>.

    Returns True if all 2^n inputs produce the correct output.
    """
    N = 1 << n
    total = qc.num_qubits
    num_ancilla = total - n - d
    all_pass = True

    print(f"\n  Verifying: {label}")
    print(f"  Qubits={total} (n={n} addr + d={d} data + {num_ancilla} ancilla), "
          f"depth={qc.depth()}")

    for x in range(N):
        # Prepare |x>|0>|0...0>
        init = [0] * total
        for bit in range(n):
            if (x >> bit) & 1:
                init[bit] = 1
        label_str = ''.join(str(init[total - 1 - i]) for i in range(total))
        sv = Statevector.from_label(label_str).evolve(qc)

        # Expected state index: addr=x, data=f(x), ancilla=0
        fx = f(x) if callable(f) else f[x]
        expected_idx = x
        for bit in range(d):
            if (fx >> bit) & 1:
                expected_idx |= (1 << (n + bit))

        prob = abs(sv.data[expected_idx]) ** 2
        ok = np.isclose(prob, 1.0, atol=1e-8)

        x_bin = format(x, f'0{n}b')
        fx_bin = format(fx, f'0{d}b')
        status = "OK" if ok else "FAIL"
        print(f"    |{x_bin}>|000> -> |{x_bin}>|{fx_bin}>  "
              f"f({x})={fx}  {status}")

        if not ok:
            all_pass = False
            probs = np.abs(sv.data) ** 2
            for idx in np.argsort(probs)[::-1][:3]:
                if probs[idx] > 1e-6:
                    print(f"      got idx={idx:0{total}b} prob={probs[idx]:.4f}")

    result = "PASSED" if all_pass else "FAILED"
    print(f"  -> {result}\n")
    return all_pass


def main():
    n, d = 3, 3
    N = 1 << n

    # ---- Define test functions ----
    f1 = lambda x: (2 * x + 1) % 8          # non-trivial bijection
    f2 = lambda x: x                         # identity
    f3 = lambda x: 5                         # constant

    print("=" * 60)
    print("QUANTUM ROM DEMO  (n=3, d=3)")
    print("Based on arXiv:1812.00954v2 (Low, Kliuchnikov, Schaeffer)")
    print("=" * 60)

    # Show the main test function
    print("\nFunction table for f(x) = (2x + 1) mod 8:")
    for x in range(N):
        print(f"  f({x}) = {f1(x):>2}   {format(x,'03b')} -> {format(f1(x),'03b')}")

    # ---- 1. Naive QROM (Select-only) ----
    print("\n" + "-" * 60)
    print("1. NAIVE QROM (Select-only multiplexer)")
    print("   O(2^n * d) multi-controlled gates, no ancillas")
    print("-" * 60)
    verify_qrom(naive_quantum_rom(f1, n, d), f1, n, d,
                "f(x) = (2x+1) mod 8")
    verify_qrom(naive_quantum_rom(f2, n, d), f2, n, d,
                "f(x) = x (identity)")
    verify_qrom(naive_quantum_rom(f3, n, d), f3, n, d,
                "f(x) = 5 (constant)")

    # ---- 2. SelectSwap QROM ----
    print("-" * 60)
    print("2. SELECTSWAP QROM (Paper's main contribution)")
    print("   T-count: O(N/lam + lam*d),  optimal lam ~ sqrt(N/d)")
    print("-" * 60)

    for lam in [2, 4]:
        print(f"\n  --- lambda = {lam} ---")
        verify_qrom(selectswap_quantum_rom(f1, n, d, lam=lam), f1, n, d,
                    f"f(x)=(2x+1)%8, lam={lam}")
        verify_qrom(selectswap_quantum_rom(f2, n, d, lam=lam), f2, n, d,
                    f"f(x)=x, lam={lam}")
        verify_qrom(selectswap_quantum_rom(f3, n, d, lam=lam), f3, n, d,
                    f"f(x)=5, lam={lam}")

    # ---- 3. Comparison table ----
    print("=" * 60)
    print("RESOURCE COMPARISON  f(x) = (2x+1) mod 8, n=d=3")
    print("=" * 60)
    print(f"  {'Method':<30} {'Qubits':>8} {'Depth':>8} {'Ancillas':>10}")
    print(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*10}")

    qn = naive_quantum_rom(f1, n, d)
    print(f"  {'Naive (Select-only)':<30} {qn.num_qubits:>8} "
          f"{qn.depth():>8} {0:>10}")

    for lam in [2, 4]:
        qs = selectswap_quantum_rom(f1, n, d, lam=lam)
        anc = qs.num_qubits - n - d
        name = f"SelectSwap (lam={lam})"
        print(f"  {name:<30} {qs.num_qubits:>8} "
              f"{qs.depth():>8} {anc:>10}")

    print("\n  The SelectSwap network trades ancilla qubits for reduced")
    print("  T-gate count. For large N, optimal lam = O(sqrt(N/d))")
    print("  yields a quadratic T-count improvement: O(sqrt(N*d)).")
    print()


if __name__ == '__main__':
    main()
