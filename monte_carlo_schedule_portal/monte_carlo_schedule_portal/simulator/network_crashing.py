from typing import Dict, List
import numpy as np
from scipy import stats
from .core import WorkPackage, CrashingSpec


def _compute_schedule_metrics(
    samples: np.ndarray,
    deterministic_baseline: float,
    target_days: float,
    include_samples: bool = True,
) -> Dict[str, object]:
    n_trials = len(samples)
    mean_val = float(np.mean(samples))
    std_val = float(np.std(samples, ddof=1))
    se_mean = std_val / np.sqrt(n_trials)
    ci_95 = [float(mean_val - 1.96 * se_mean), float(mean_val + 1.96 * se_mean)]

    p10, p50, p80, p90, p95, p99 = np.percentile(samples, [10, 50, 80, 90, 95, 99])
    cvar_95 = float(samples[samples >= p95].mean())
    prob_exceed = float(np.mean(samples > target_days))

    out: Dict[str, object] = {
        "deterministic_baseline": float(deterministic_baseline),
        "mean": mean_val,
        "std": std_val,
        "ci_95_mean": ci_95,
        "p10": float(p10),
        "p50": float(p50),
        "p80": float(p80),
        "p90": float(p90),
        "p95": float(p95),
        "p99": float(p99),
        "cvar_95": cvar_95,
        "prob_exceed_target": prob_exceed,
        "var_95_overrun_vs_target": max(0.0, float(p95 - target_days)),
        "var_95_overrun_vs_baseline": float(p95 - deterministic_baseline),
    }
    if include_samples:
        out["samples"] = samples
    return out


def simulate_sequential_vs_parallel(
    packages: List[WorkPackage],
    n_trials: int = 100_000,
    target_days: float = 75.0,
    seed: int = 42,
    include_samples: bool = True,
) -> Dict[str, object]:
    """
    Evaluates 6 work packages under both Sequential and Parallel PERT/CPM topologies:
      - Sequential: T_seq = WP1 + WP2 + WP3 + WP4 + WP5 + WP6
      - Parallel:   T_par = WP1 + max(WP2 + WP3, WP4) + WP5 + WP6
    """
    if len(packages) != 6:
        raise ValueError("Expected exactly 6 work packages (WP1 through WP6).")

    rng = np.random.default_rng(seed)
    package_totals = np.zeros((n_trials, 6))

    for i, wp in enumerate(packages):
        base = rng.triangular(wp.optimistic, wp.most_likely, wp.pessimistic, size=n_trials)
        delay = np.zeros(n_trials)

        if wp.delay_rate > 0:
            counts = rng.poisson(lam=wp.delay_rate, size=n_trials)
            max_events = int(counts.max())
            if max_events > 0:
                shocks = rng.lognormal(wp.delay_mu, wp.delay_sigma, size=(n_trials, max_events))
                mask = np.arange(max_events)[None, :] < counts[:, None]
                delay = np.where(mask, shocks, 0.0).sum(axis=1)

        package_totals[:, i] = base + delay

    wp1, wp2, wp3, wp4, wp5, wp6 = [package_totals[:, i] for i in range(6)]
    modes = [wp.most_likely for wp in packages]

    t_seq = package_totals.sum(axis=1)
    det_seq = float(sum(modes))
    seq_metrics = _compute_schedule_metrics(t_seq, det_seq, target_days, include_samples)

    branch_a = wp2 + wp3
    branch_b = wp4
    critical_branch = np.maximum(branch_a, branch_b)
    t_par = wp1 + critical_branch + wp5 + wp6

    det_branch_a = modes[1] + modes[2]
    det_branch_b = modes[3]
    det_par = float(modes[0] + max(det_branch_a, det_branch_b) + modes[4] + modes[5])
    par_metrics = _compute_schedule_metrics(t_par, det_par, target_days, include_samples)

    e_branch_a = float(np.mean(branch_a))
    e_branch_b = float(np.mean(branch_b))
    naive_mean_par = float(np.mean(wp1) + max(e_branch_a, e_branch_b) + np.mean(wp5) + np.mean(wp6))
    stochastic_merge_bias = float(par_metrics["mean"] - naive_mean_par)
    total_overrun_vs_det_cpm = float(par_metrics["mean"] - det_par)

    branch_a_critical = branch_a >= branch_b
    criticality_index = {
        packages[0].name: 1.0,
        packages[1].name: float(np.mean(branch_a_critical)),
        packages[2].name: float(np.mean(branch_a_critical)),
        packages[3].name: float(np.mean(~branch_a_critical)),
        packages[4].name: 1.0,
        packages[5].name: 1.0,
    }

    par_sensitivity = {
        packages[i].name: float(stats.spearmanr(package_totals[:, i], t_par).statistic)
        for i in range(6)
    }

    return {
        "n_trials": n_trials,
        "target_days": float(target_days),
        "sequential": seq_metrics,
        "parallel": par_metrics,
        "time_savings": {
            "deterministic_days": float(det_seq - det_par),
            "mean_days": float(seq_metrics["mean"] - par_metrics["mean"]),
            "p50_days": float(seq_metrics["p50"] - par_metrics["p50"]),
            "p95_days": float(seq_metrics["p95"] - par_metrics["p95"]),
            "cvar_95_days": float(seq_metrics["cvar_95"] - par_metrics["cvar_95"]),
        },
        "merge_bias": {
            "naive_pert_mean": naive_mean_par,
            "simulated_parallel_mean": float(par_metrics["mean"]),
            "pure_merge_bias_days": stochastic_merge_bias,
            "total_bias_vs_det_cpm_days": total_overrun_vs_det_cpm,
        },
        "criticality_index": criticality_index,
        "parallel_sensitivity": par_sensitivity,
    }


def evaluate_crashing_grid(
    packages: List[WorkPackage],
    wp3_crash: CrashingSpec,
    wp4_crash: CrashingSpec,
    n_trials: int = 100_000,
    target_days: float = 75.0,
    seed: int = 42,
) -> Dict[str, object]:
    """
    Evaluates all (crash_wp3, crash_wp4) combinations on the parallel PERT/CPM
    network using Common Random Numbers (CRN) and extracts the Pareto frontier.
    """
    if len(packages) != 6:
        raise ValueError("Expected exactly 6 work packages (WP1 through WP6).")

    rng = np.random.default_rng(seed)

    base_durations = np.zeros((n_trials, 6))
    delay_durations = np.zeros((n_trials, 6))

    for i, wp in enumerate(packages):
        base_durations[:, i] = rng.triangular(
            wp.optimistic, wp.most_likely, wp.pessimistic, size=n_trials
        )
        if wp.delay_rate > 0:
            counts = rng.poisson(lam=wp.delay_rate, size=n_trials)
            max_events = int(counts.max())
            if max_events > 0:
                shocks = rng.lognormal(wp.delay_mu, wp.delay_sigma, size=(n_trials, max_events))
                mask = np.arange(max_events)[None, :] < counts[:, None]
                delay_durations[:, i] = np.where(mask, shocks, 0.0).sum(axis=1)

    wp1 = base_durations[:, 0] + delay_durations[:, 0]
    wp2 = base_durations[:, 1] + delay_durations[:, 1]
    wp5 = base_durations[:, 4] + delay_durations[:, 4]
    wp6 = base_durations[:, 5] + delay_durations[:, 5]
    fixed_serial = wp1 + wp5 + wp6

    wp3_mode = packages[2].most_likely
    wp4_mode = packages[3].most_likely

    policies: List[Dict[str, object]] = []

    for c3 in range(wp3_crash.max_crash_days + 1):
        scale3 = max(0.0, (wp3_mode - c3) / wp3_mode)
        wp3_crashed = base_durations[:, 2] * scale3 + delay_durations[:, 2]
        branch_a = wp2 + wp3_crashed

        for c4 in range(wp4_crash.max_crash_days + 1):
            scale4 = max(0.0, (wp4_mode - c4) / wp4_mode)
            wp4_crashed = base_durations[:, 3] * scale4 + delay_durations[:, 3]

            t_par = fixed_serial + np.maximum(branch_a, wp4_crashed)

            cost = c3 * wp3_crash.cost_per_day + c4 * wp4_crash.cost_per_day
            mean_dur = float(np.mean(t_par))
            p50 = float(np.percentile(t_par, 50))
            p95 = float(np.percentile(t_par, 95))
            cvar_95 = float(t_par[t_par >= p95].mean())
            prob_exceed = float(np.mean(t_par > target_days))
            crit_a = float(np.mean(branch_a >= wp4_crashed))

            policies.append({
                "label": f"(-{c3}d WP3, -{c4}d WP4)",
                "crash_wp3": int(c3),
                "crash_wp4": int(c4),
                "cost": float(cost),
                "mean": mean_dur,
                "p50": p50,
                "var_95": p95,
                "cvar_95": cvar_95,
                "prob_exceed_target": prob_exceed,
                "branch_a_criticality": crit_a,
                "is_pareto": False,
            })

    policies.sort(key=lambda p: (p["cost"], p["var_95"]))
    best_var_so_far = float("inf")
    pareto_frontier: List[Dict[str, object]] = []

    for p in policies:
        if p["var_95"] < best_var_so_far - 1e-9:
            p["is_pareto"] = True
            best_var_so_far = p["var_95"]
            pareto_frontier.append(p)

    return {
        "n_trials": n_trials,
        "target_days": float(target_days),
        "wp3_spec": {"max_crash_days": wp3_crash.max_crash_days, "cost_per_day": wp3_crash.cost_per_day},
        "wp4_spec": {"max_crash_days": wp4_crash.max_crash_days, "cost_per_day": wp4_crash.cost_per_day},
        "all_policies": policies,
        "pareto_frontier": pareto_frontier,
    }
