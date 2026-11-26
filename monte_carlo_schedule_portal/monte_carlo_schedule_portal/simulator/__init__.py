"""
Monte Carlo Project Schedule Risk Simulator Suite
===============================================
Provides vectorized Monte Carlo simulation, Latin Hypercube Sampling (LHS)
variance reduction, Sequential vs. Parallel PERT/CPM network modeling,
schedule crashing Pareto optimization, and Matplotlib reporting utilities.
"""

from .core import (
    WorkPackage,
    CrashingSpec,
    lognormal_params_from_mean_std,
    default_work_packages,
    simulate_project_schedule,
    validate_normal_sum_analytical,
)
from .variance_reduction import (
    simulate_schedule_batch,
    run_convergence_comparison,
)
from .network_crashing import (
    simulate_sequential_vs_parallel,
    evaluate_crashing_grid,
)
from .visualization import (
    plot_schedule_risk_dashboard,
    plot_analytical_validation_and_convergence,
    plot_lhs_vs_cmc_convergence,
    plot_sequential_vs_parallel_comparison,
    plot_crashing_pareto_frontier,
)

__all__ = [
    "WorkPackage",
    "CrashingSpec",
    "lognormal_params_from_mean_std",
    "default_work_packages",
    "simulate_project_schedule",
    "validate_normal_sum_analytical",
    "simulate_schedule_batch",
    "run_convergence_comparison",
    "simulate_sequential_vs_parallel",
    "evaluate_crashing_grid",
    "plot_schedule_risk_dashboard",
    "plot_analytical_validation_and_convergence",
    "plot_lhs_vs_cmc_convergence",
    "plot_sequential_vs_parallel_comparison",
    "plot_crashing_pareto_frontier",
]
