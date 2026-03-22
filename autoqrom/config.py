"""Sweep configuration for the QROM auto-research system."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SweepConfig:
    """All parameters controlling the QROM parameter sweep."""

    # Sweep grid
    n_range: range = field(default_factory=lambda: range(2, 9))
    d_range: range = field(default_factory=lambda: range(2, 9))
    methods: list = field(default_factory=lambda: ["naive", "selectswap"])

    # Transpilation
    hardware_basis: list = field(
        default_factory=lambda: ["cx", "u3", "u2", "u1", "id", "x", "h"]
    )
    opt_level: int = 1
    transpile_timeout: int = 120  # seconds

    # Simulation limits
    max_sim_qubits: int = 24  # 2^24 = 16M amplitudes, ~256MB

    # Output paths
    results_dir: Path = field(
        default_factory=lambda: Path(__file__).parent / "results"
    )

    @property
    def tsv_path(self) -> Path:
        return self.results_dir / "sweep_results.tsv"
