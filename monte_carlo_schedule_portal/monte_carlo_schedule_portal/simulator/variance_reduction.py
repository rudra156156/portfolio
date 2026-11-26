from typing import Dict, List
import numpy as np
from scipy import stats
from scipy.stats import qmc
from .core import WorkPackage


def _triangular_ppf(u: np.ndarray, a: float, c: float, b: float) -> np.ndarray:
    """Vectorized inverse CDF for Triangular(a, c, b)."""
    if b == a:
        return np.full_like(u, a)
    fc = (c - a) / (b - a)
    return np.where(
        u < fc,
        a + np.sqrt(np.maximum(0.0, u * (b - a) * (c - a))),
        b - np.sqrt(np.maximum(0.0, (1.0 - u) * (b - a) * (b - c))),
    )


def simulate_schedule_batch(
    packages: List[WorkPackage],
    n_trials: int,
    method: str = "cmc",
    seed: int = 42,
    max_shock_cols: int = 8,
) -> np.ndarray:
    """
    Simulates total project completion times using either:
      - 'cmc': Standard Crude Monte Carlo pseudorandom sampling
      - 'lhs': Latin Hypercube Sampling via inverse-CDF transformation
    """
    n_packages = len(packages)
    dims_per_pkg = 2 + max_shock_cols
    total_dims = n_packages * dims_per_pkg

    if method == "lhs":
        sampler = qmc.LatinHypercube(d=total_dims, scramble=True, seed=seed)
        u_matrix = np.clip(sampler.random(n=n_trials), 1e-12, 1.0 - 1e-12)
    elif method == "cmc":
        rng = np.random.default_rng(seed)
        u_matrix = np.clip(rng.random((n_trials, total_dims)), 1e-12, 1.0 - 1e-12)
    else:
        raise ValueError("method must be 'cmc' or 'lhs'")

    total_duration = np.zeros(n_trials)

    for i, wp in enumerate(packages):
        col_offset = i * dims_per_pkg
        u_base = u_matrix[:, col_offset]
        u_count = u_matrix[:, col_offset + 1]
        u_shocks = u_matrix[:, col_offset + 2 : col_offset + dims_per_pkg]

        base_dur = _triangular_ppf(u_base, wp.optimistic, wp.most_likely, wp.pessimistic)

        delay_dur = np.zeros(n_trials)
        if wp.delay_rate > 0:
            counts = stats.poisson.ppf(u_count, mu=wp.delay_rate).astype(int)
            z_shocks = stats.norm.ppf(u_shocks)
            lognorm_shocks = np.exp(wp.delay_mu + wp.delay_sigma * z_shocks)

            valid_mask = np.arange(max_shock_cols)[None, :] < counts[:, None]
            delay_dur = np.where(valid_mask, lognorm_shocks, 0.0).sum(axis=1)

            overflow = counts - max_shock_cols
            if np.any(overflow > 0):
                overflow_rng = np.random.default_rng(seed + 10_000 + i)
                for idx in np.where(overflow > 0)[0]:
                    extra = overflow_rng.lognormal(
                        mean=wp.delay_mu, sigma=wp.delay_sigma, size=int(overflow[idx])
                    )
                    delay_dur[idx] += extra.sum()

        total_duration += base_dur + delay_dur

    return total_duration


def run_convergence_comparison(
    packages: List[WorkPackage],
    sample_sizes: List[int],
    n_replicates: int = 25,
    target_days: float = 75.0,
    reference_trials: int = 250_000,
) -> Dict[str, object]:
    """
    Evaluates estimator RMSE across replicate runs for Crude Monte Carlo (CMC)
    vs. Latin Hypercube Sampling (LHS).
    """
    ref_samples = simulate_schedule_batch(
        packages, n_trials=reference_trials, method="lhs", seed=999
    )
    ref_mean = float(np.mean(ref_samples))
    ref_p95 = float(np.percentile(ref_samples, 95))
    ref_prob_exceed = float(np.mean(ref_samples > target_days))

    metrics: Dict[str, object] = {
        "sample_sizes": [int(n) for n in sample_sizes],
        "n_replicates": int(n_replicates),
        "ref_mean": ref_mean,
        "ref_p95": ref_p95,
        "ref_prob_exceed": ref_prob_exceed,
        "cmc": {"mean_rmse": [], "p95_rmse": [], "prob_rmse": [], "mean_vrf": []},
        "lhs": {"mean_rmse": [], "p95_rmse": [], "prob_rmse": [], "mean_vrf": []},
    }

    for n in sample_sizes:
        for method in ("cmc", "lhs"):
            est_means = np.zeros(n_replicates)
            est_p95s = np.zeros(n_replicates)
            est_probs = np.zeros(n_replicates)

            for r in range(n_replicates):
                seed = 1000 * r + n
                samples = simulate_schedule_batch(
                    packages, n_trials=n, method=method, seed=seed
                )
                est_means[r] = np.mean(samples)
                est_p95s[r] = np.percentile(samples, 95)
                est_probs[r] = np.mean(samples > target_days)

            metrics[method]["mean_rmse"].append(
                float(np.sqrt(np.mean((est_means - ref_mean) ** 2)))
            )
            metrics[method]["p95_rmse"].append(
                float(np.sqrt(np.mean((est_p95s - ref_p95) ** 2)))
            )
            metrics[method]["prob_rmse"].append(
                float(np.sqrt(np.mean((est_probs - ref_prob_exceed) ** 2)))
            )

        c_rmse = metrics["cmc"]["mean_rmse"][-1]
        l_rmse = metrics["lhs"]["mean_rmse"][-1]
        vrf = float((c_rmse / l_rmse) ** 2) if l_rmse > 0 else 1.0
        metrics["lhs"]["mean_vrf"].append(vrf)
        metrics["cmc"]["mean_vrf"].append(1.0)

    return metrics
