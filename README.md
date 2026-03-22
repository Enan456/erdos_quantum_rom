# Quantum ROM (QROM)

Implementation of a Quantum Read-Only Memory oracle based on the SelectSwap network from [arXiv:1812.00954v2](https://arxiv.org/abs/1812.00954v2) (Low, Kliuchnikov, Schaeffer).

Given any classical function **f : F₂ⁿ → F₂ᵈ**, builds a quantum circuit **U** such that:

```
U |x⟩ₙ |0⟩ᵈ = |x⟩ₙ |f(x)⟩ᵈ
```

## Two Implementations

### Naive (Select-only multiplexer)

For each address x, applies multi-controlled X gates to write f(x) into the output register. No ancillas needed.

- **Qubits:** n + d
- **T-count:** O(2ⁿ · d)

### SelectSwap (paper's main contribution)

Splits the address x = q·λ + r into quotient and remainder. **Select** (controlled by q) writes λ data values into λ ancilla registers simultaneously. **Swap** (controlled by r) routes the correct register to position 0. Uncomputation returns ancillas to |0⟩.

- **Qubits:** n + d + λ·d ancillas
- **T-count:** O(2ⁿ/λ + λ·d), optimized at λ = O(√(2ⁿ/d))
- **Optimal T-count:** O(√(2ⁿ · d)) — quadratic improvement

## Circuit Diagrams (n = d = 3)

### Naive QROM
![Naive QROM Circuit](circuit_naive.png)

### SelectSwap QROM (λ = 2)
![SelectSwap λ=2](circuit_selectswap_lam2.png)

### SelectSwap QROM (λ = 4)
![SelectSwap λ=4](circuit_selectswap_lam4.png)

## Usage

```python
from quantum_rom import quantum_rom

# Define any function f : {0,..,2^n-1} -> {0,..,2^d-1}
f = lambda x: (2 * x + 1) % 8

# Naive approach
circuit = quantum_rom(f, n=3, d=3, method='naive')

# SelectSwap approach (auto-selects optimal λ)
circuit = quantum_rom(f, n=3, d=3, method='selectswap')

# SelectSwap with explicit λ
circuit = quantum_rom(f, n=3, d=3, method='selectswap', lam=2)
```

The function `f` can be a callable, list, or dict.

## Verification

Run the demo to verify both implementations on three test functions (bijection, identity, constant) with statevector simulation:

```bash
python3 demo.py
```

All 18 test cases pass with probability 1.000000.

### Resource Comparison (n = d = 3, f(x) = (2x+1) mod 8)

| Method | Qubits | Depth | Ancillas |
|---|---|---|---|
| Naive (Select-only) | 6 | 28 | 0 |
| SelectSwap (λ=2) | 12 | 49 | 6 |
| SelectSwap (λ=4) | 18 | 51 | 12 |

## Requirements

- Python 3.9+
- Qiskit 2.x (`pip install qiskit`)
- qiskit-aer (`pip install qiskit-aer`) — for simulation
- matplotlib — for circuit diagrams

## Reference

G. H. Low, V. Kliuchnikov, L. Schaeffer, "Trading T gates for dirty qubits in state preparation and unitary synthesis," *Quantum* **8**, 2024. [arXiv:1812.00954v2](https://arxiv.org/abs/1812.00954v2)
