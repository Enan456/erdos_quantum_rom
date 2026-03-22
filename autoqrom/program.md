# QROM Auto-Research: LLM Exploration Program

## Objective

You are an autonomous research agent exploring optimizations for Quantum Read-Only Memory (QROM) circuits. The deterministic sweep (`autoqrom/sweep.py`) has already established baselines across `n,d ∈ [2,8]`, all valid lambda values, and 3 test functions. Your job is to search for novel optimizations that improve on these baselines.

**Optimization targets** (in priority order):
1. T-count (dominant cost for fault-tolerant quantum computing)
2. CNOT count (dominant cost for NISQ devices)
3. Circuit depth (determines execution time)
4. Qubit count (limited hardware resource)

## Setup

1. Read `autoqrom/results/sweep_results.tsv` to understand the baselines
2. Identify the worst-performing configurations (highest T-count, depth, CNOT for their n,d)
3. Read the paper reference in `quantum_rom.py` docstrings for theoretical context
4. Create a git branch: `git checkout -b exploration/<your-idea>`

## Exploration Tiers

### Tier 1: Transpiler Optimization (low risk, moderate reward)

These don't change the algorithm -- just how circuits are compiled to hardware gates.

- **Higher opt_level**: Try `opt_level=3` in Qiskit transpile. Measure depth/CNOT reduction vs compile time.
- **Custom PassManager**: Build a `PassManager` with commutation-aware gate reordering, especially for the Select operator where many MCX gates share address qubits.
- **Gate cancellation**: The Select→Copy→Select† pattern creates opportunities for gate cancellation at the boundaries. Check if Qiskit's optimizer catches these.
- **Basis gate alternatives**: Try `['cx', 'rz', 'sx', 'x']` (IBM Eagle basis) instead of the default basis.

### Tier 2: Decomposition Alternatives (moderate risk, high reward)

Replace the multi-controlled gate decompositions with more efficient alternatives.

- **Relative-phase Toffoli**: Replace CCX with a relative-phase variant (4 T-gates instead of 7). Valid when the Toffoli is later uncomputed (which it is in Select→Select†).
- **Dirty-ancilla MCX**: For `mcx(n)` with n≥3 controls, use the output register qubits as dirty ancillas during the Select phase. This can reduce MCX T-count from `14*(n-2)` to `8*(n-2)`.
- **Gray code ordering**: Reorder the `x` iteration in the Select operator to minimize X-gate flips between consecutive addresses. Currently iterates 0,1,2,...,N-1; Gray code ordering reduces X-gate overhead by ~50%.

### Tier 3: Algorithmic Improvements (high risk, high reward)

Modify the QROM algorithm structure itself.

- **Dirty-ancilla QROM variant**: The paper's Fig 1d shows a variant that uses dirty (non-zero) ancillas instead of clean ancillas. This eliminates the need for ancilla initialization but requires a more complex uncomputation step.
- **Hybrid lambda scheduling**: Instead of a single lambda for all quotient groups, use different lambda values for different parts of the address space. This can optimize for non-uniform function tables.
- **QROM with measurement-based uncomputation**: For cases where the ancillas don't need to be reused, measure-and-reset can replace the Select† uncomputation, halving the circuit.

## Experiment Loop

For each idea:

```
1. IMPLEMENT: Make the code change (new function or modified transpile pipeline)
2. RUN: Execute on a representative subset (e.g., n=3,4,5; d=2,4,6; bijection only)
3. COMPARE: Load baseline from sweep_results.tsv, compute improvement %
4. DECIDE: If improvement > 5% on any metric, KEEP. Otherwise, REVERT.
5. LOG: Append results to exploration_results.tsv
6. COMMIT: If keeping, commit with descriptive message
7. REPEAT: Move to next idea
```

## Output Format

Create `autoqrom/results/exploration_results.tsv` with columns:

```
commit_hash  idea_name  tier  n  d  method  lam  baseline_depth  new_depth  depth_improvement_pct  baseline_cnot  new_cnot  cnot_improvement_pct  baseline_tcount  new_tcount  tcount_improvement_pct  notes
```

## Constraints

- Do NOT modify `quantum_rom.py` or `demo.py` -- these are the reference implementations
- Create new files for alternative implementations (e.g., `quantum_rom_v2.py`)
- All experiments must be reproducible: commit code before recording results
- If an idea takes more than 30 minutes of compute time to evaluate, skip it and note why
- Verify correctness using `autoqrom/verify.py` before claiming improvements

## Success Criteria

- At least 3 ideas attempted across at least 2 tiers
- At least 1 idea showing >10% improvement on some metric
- All results logged in `exploration_results.tsv`
- Clear commit history documenting each experiment
