from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
import numpy as np
from scipy import stats


@dataclass
class WorkPackage:
    name: str
    optimistic: float      # Triangular min (a)
    most_likely: float     # Triangular mode (c)
    pessimistic: float     # Triangular max (b)
    delay_rate: float      # Poisson lambda (expected number of delay events)
    delay_mu: float        # Lognormal underlying normal mean (mu)
    delay_sigma: float     # Lognormal underlying normal std dev (sigma)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class CrashingSpec:
    max_crash_days: int
    cost_per_day: float


def lognormal_params_from_mean_std(mean: float, std: float) -> Tuple[float, float]:
    """
    Converts real-world delay mean and standard deviation (in days) into
    underlying normal parameters (mu, sigma) required by np.random.lognormal.
    """
    if mean <= 0 or std <= 0:
        raise ValueError("Delay mean and std must be strictly positive.")
    variance = std ** 2
    sigma_sq = np.log(1.0 + variance / (mean ** 2))
    mu = np.log(mean) - 0.5 * sigma_sq
    return float(mu), float(np.sqrt(sigma_sq))


def default_work_packages() -> List[WorkPackage]:
    """Returns the standard 6-package project configuration."""
    mu_1, sig_1 = lognormal_params_from_mean_std(mean=2.0, std=1.5)
    mu_2, sig_2 = lognormal_params_from_mean_std(mean=3.5, std=2.5)
    mu_3, sig_3 = lognormal_params_from_mean_std(mean=4.0, std=3.0)

    return [
        WorkPackage("WP1: Requirements & Design",   8.0, 10.0, 14.0, delay_rate=0.4, delay_mu=mu_1, delay_sigma=sig_1),
        WorkPackage("WP2: Core Architecture",      10.0, 12.0, 17.0, delay_rate=0.6, delay_mu=mu_2, delay_sigma=sig_2),
        WorkPackage("WP3: Backend Development",    12.0, 15.0, 22.0, delay_rate=0.8, delay_mu=mu_3, delay_sigma=sig_3),
        WorkPackage("WP4: Frontend Integration",    7.0,  9.0, 13.0, delay_rate=0.5, delay_mu=mu_1, delay_sigma=sig_1),
        WorkPackage("WP5: QA & Security Testing",   6.0,  8.0, 13.0, delay_rate=0.7, delay_mu=mu_2, delay_sigma=sig_2),
        WorkPackage("WP6: Deployment & Handover",   3.0,  4.0,  7.0, delay_rate=0.3, delay_mu=mu_1, delay_sigma=sig_1),
    ]


def simulate_project_schedule(
    packages: List[WorkPackage],
    n_trials: int = 100_000,
    target_days: float = 75.0,
    seed: int = 42,
    include_samples: bool = True,
) -> Dict[str, object]:
    """
    Runs a vectorized Monte Carlo simulation across sequential work packages
    with Triangular baseline durations and Compound Poisson-Lognormal delays.
    """
    rng = np.random.default_rng(seed)
    n_packages = len(packages)

    baseline_durations = np.zeros((n_trials, n_packages))
    delay_durations = np.zeros((n_trials, n_packages))

    for i, wp in enumerate(packages):
        baseline_durations[:, i] = rng.triangular(
            left=wp.optimistic,
            mode=wp.most_likely,
            right=wp.pessimistic,
            size=n_trials,
        )

        if wp.delay_rate > 0:
            event_counts = rng.poisson(lam=wp.delay_rate, size=n_trials)
            max_events = int(event_counts.max())

            if max_events > 0:
                raw_shocks = rng.lognormal(
                    mean=wp.delay_mu,
                    sigma=wp.delay_sigma,
                    size=(n_trials, max_events),
                )
                valid_mask = np.arange(max_events)[None, :] < event_counts[:, None]
                delay_durations[:, i] = np.where(valid_mask, raw_shocks, 0.0).sum(axis=1)

    package_totals = baseline_durations + delay_durations
    total_duration = package_totals.sum(axis=1)

    mean_duration = float(np.mean(total_duration))
    std_duration = float(np.std(total_duration, ddof=1))
    se_mean = std_duration / np.sqrt(n_trials)
    ci_95 = [float(mean_duration - 1.96 * se_mean), float(mean_duration + 1.96 * se_mean)]

    p10, median_duration, p80, p90, p95, p99 = np.percentile(
        total_duration, [10, 50, 80, 90, 95, 99]
    )

    deterministic_baseline = float(sum(wp.most_likely for wp in packages))
    var_95_overrun_target = max(0.0, float(p95 - target_days))
    var_95_overrun_baseline = float(p95 - deterministic_baseline)
    cvar_95 = float(total_duration[total_duration >= p95].mean())
    prob_exceed_target = float(np.mean(total_duration > target_days))

    sensitivities = {
        wp.name: float(stats.spearmanr(package_totals[:, i], total_duration).statistic)
        for i, wp in enumerate(packages)
    }

    result: Dict[str, object] = {
        "n_trials": n_trials,
        "target_days": float(target_days),
        "deterministic_baseline": deterministic_baseline,
        "mean": mean_duration,
        "std": std_duration,
        "ci_95_mean": ci_95,
        "median": float(median_duration),
        "percentiles": {
            "P10": float(p10),
            "P50": float(median_duration),
            "P80": float(p80),
            "P90": float(p90),
            "P95": float(p95),
            "P99": float(p99),
        },
        "prob_exceed_target": prob_exceed_target,
        "var_95_total": float(p95),
        "var_95_overrun_vs_target": var_95_overrun_target,
        "var_95_overrun_vs_baseline": var_95_overrun_baseline,
        "cvar_95_total": cvar_95,
        "spearman_sensitivity": sensitivities,
    }
    if include_samples:
        result["samples"] = total_duration
    return result


def validate_normal_sum_analytical(
    means: List[float],
    stds: List[float],
    threshold: float = 65.0,
    n_trials: int = 100_000,
    seed: int = 42,
    include_samples: bool = True,
) -> Dict[str, object]:
    """
    Validates Monte Carlo accuracy against the exact closed-form solution
    for the sum of independent Normal variables:
        Sum(X_i) ~ N(Sum(mu_i), Sum(sigma_i^2))
    """
    rng = np.random.default_rng(seed)
    means_arr = np.asarray(means, dtype=float)
    stds_arr = np.asarray(stds, dtype=float)

    simulated_vars = rng.normal(
        loc=means_arr[None, :],
        scale=stds_arr[None, :],
        size=(n_trials, len(means_arr)),
    )
    sim_total = simulated_vars.sum(axis=1)

    exact_mean = float(means_arr.sum())
    exact_std = float(np.sqrt(np.sum(stds_arr ** 2)))
    exact_p95 = float(stats.norm.ppf(0.95, loc=exact_mean, scale=exact_std))
    exact_prob_exceed = float(stats.norm.sf(threshold, loc=exact_mean, scale=exact_std))

    sim_mean = float(np.mean(sim_total))
    sim_std = float(np.std(sim_total, ddof=1))
    sim_p95 = float(np.percentile(sim_total, 95))
    sim_prob_exceed = float(np.mean(sim_total > threshold))

    comparison_table = {
        "Mean": {
            "Analytical": exact_mean,
            "Simulated": sim_mean,
            "Abs_Error": abs(sim_mean - exact_mean),
        },
        "Std_Dev": {
            "Analytical": exact_std,
            "Simulated": sim_std,
            "Abs_Error": abs(sim_std - exact_std),
        },
        "P95": {
            "Analytical": exact_p95,
            "Simulated": sim_p95,
            "Abs_Error": abs(sim_p95 - exact_p95),
        },
        f"P(T > {threshold:.0f}d)": {
            "Analytical": exact_prob_exceed,
            "Simulated": sim_prob_exceed,
            "Abs_Error": abs(sim_prob_exceed - exact_prob_exceed),
        },
    }

    res: Dict[str, object] = {
        "table": comparison_table,
        "exact_mean": exact_mean,
        "exact_std": exact_std,
        "exact_p95": exact_p95,
        "exact_prob_exceed": exact_prob_exceed,
        "sim_mean": sim_mean,
        "sim_std": sim_std,
        "sim_p95": sim_p95,
        "sim_prob_exceed": sim_prob_exceed,
        "threshold": float(threshold),
        "n_trials": n_trials,
    }
    if include_samples:
        res["samples"] = sim_total
    return res
