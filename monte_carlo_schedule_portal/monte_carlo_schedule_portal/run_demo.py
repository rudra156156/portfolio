"""
CLI Demo Runner for the Monte Carlo Project Schedule Risk Simulator Suite
-------------------------------------------------------------------------
Executes all four simulation experiments and exports high-resolution PNG figures
to the `outputs/` directory:
  1. Sequential 100,000-trial Monte Carlo risk analysis & tornado dashboard
  2. Closed-form Normal analytical validation & O(1/sqrt(N)) convergence plot
  3. Crude Monte Carlo vs. Latin Hypercube Sampling (LHS) variance reduction benchmark
  4. Sequential vs. Parallel PERT/CPM network merge bias & WP3/WP4 crashing Pareto frontier
"""

import os
from simulator import (
    CrashingSpec,
    default_work_packages,
    simulate_project_schedule,
    validate_normal_sum_analytical,
    run_convergence_comparison,
    simulate_sequential_vs_parallel,
    evaluate_crashing_grid,
    plot_schedule_risk_dashboard,
    plot_analytical_validation_and_convergence,
    plot_lhs_vs_cmc_convergence,
    plot_sequential_vs_parallel_comparison,
    plot_crashing_pareto_frontier,
)


def main() -> None:
    os.makedirs("outputs", exist_ok=True)
    packages = default_work_packages()

    print("=" * 72)
    print("1. SEQUENTIAL MONTE CARLO SCHEDULE RISK ANALYSIS (100,000 TRIALS)")
    print("=" * 72)
    sim_res = simulate_project_schedule(packages, n_trials=100_000, target_days=75.0, seed=42)
    print(f"Deterministic Baseline: {sim_res['deterministic_baseline']:.2f}d | "
          f"Simulated Mean: {sim_res['mean']:.2f}d (95% CI: [{sim_res['ci_95_mean'][0]:.2f}, {sim_res['ci_95_mean'][1]:.2f}])")
    print(f"Median (P50): {sim_res['median']:.2f}d | P95 VaR: {sim_res['var_95_total']:.2f}d | "
          f"CVaR 95%: {sim_res['cvar_95_total']:.2f}d | P(T > 75d): {sim_res['prob_exceed_target']:.2%}")
    plot_schedule_risk_dashboard(sim_res, save_path="outputs/01_schedule_risk_dashboard.png")

    print("
" + "=" * 72)
    print("2. ANALYTICAL GAUSSIAN VALIDATION BENCHMARK")
    print("=" * 72)
    val_res = validate_normal_sum_analytical(
        means=[10.0, 12.0, 15.0, 9.0, 8.0, 4.0],
        stds=[2.0, 2.5, 3.0, 1.5, 2.0, 1.0],
        threshold=65.0,
        n_trials=100_000,
        seed=42,
    )
    for k, v in val_res["table"].items():
        print(f"  {k:<14}: Analytical = {v['Analytical']:8.4f} | Simulated = {v['Simulated']:8.4f} | |Err| = {v['Abs_Error']:.5f}")
    plot_analytical_validation_and_convergence(val_res, save_path="outputs/02_analytical_validation.png")

    print("
" + "=" * 72)
    print("3. CRUDE MONTE CARLO VS. LATIN HYPERCUBE SAMPLING (LHS) CONVERGENCE")
    print("=" * 72)
    sample_grid = [100, 250, 500, 1_000, 2_500, 5_000, 10_000, 25_000, 50_000, 100_000]
    lhs_comp = run_convergence_comparison(packages, sample_sizes=sample_grid, n_replicates=20, reference_trials=200_000)
    for i, n in enumerate(sample_grid):
        print(f"  N = {n:>7,} | CMC Mean RMSE: {lhs_comp['cmc']['mean_rmse'][i]:.4f}d | "
              f"LHS Mean RMSE: {lhs_comp['lhs']['mean_rmse'][i]:.4f}d | VRF: {lhs_comp['lhs']['mean_vrf'][i]:.2f}x")
    plot_lhs_vs_cmc_convergence(lhs_comp, save_path="outputs/03_lhs_vs_cmc_convergence.png")

    print("
" + "=" * 72)
    print("4. SEQUENTIAL VS. PARALLEL PERT/CPM & WP3/WP4 CRASHING FRONTIER")
    print("=" * 72)
    net_comp = simulate_sequential_vs_parallel(packages, n_trials=100_000, target_days=75.0, seed=42)
    print(f"  Sequential Mean: {net_comp['sequential']['mean']:.2f}d | Parallel CPM Mean: {net_comp['parallel']['mean']:.2f}d | "
          f"Pure Merge Bias: +{net_comp['merge_bias']['pure_merge_bias_days']:.2f}d")
    plot_sequential_vs_parallel_comparison(net_comp, save_path="outputs/04_sequential_vs_parallel.png")

    crash_res = evaluate_crashing_grid(
        packages,
        wp3_crash=CrashingSpec(max_crash_days=6, cost_per_day=2_500.0),
        wp4_crash=CrashingSpec(max_crash_days=4, cost_per_day=1_800.0),
        n_trials=100_000,
        target_days=75.0,
        seed=42,
    )
    print(f"  Evaluated {len(crash_res['all_policies'])} policies -> {len(crash_res['pareto_frontier'])} Pareto-efficient solutions.")
    plot_crashing_pareto_frontier(crash_res, save_path="outputs/05_crashing_pareto_frontier.png")
    print("
All figures saved in ./outputs/")


if __name__ == "__main__":
    main()
