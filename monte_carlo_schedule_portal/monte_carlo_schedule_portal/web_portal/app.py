"""
Interactive Web Portal for the Monte Carlo Project Schedule Risk Simulator
--------------------------------------------------------------------------
Launch with:
    python web_portal/app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import os
import sys
from typing import List
import numpy as np
from flask import Flask, jsonify, render_template, request

# Ensure parent project root is importable
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from simulator import (
    CrashingSpec,
    WorkPackage,
    default_work_packages,
    lognormal_params_from_mean_std,
    simulate_project_schedule,
    validate_normal_sum_analytical,
    run_convergence_comparison,
    simulate_sequential_vs_parallel,
    evaluate_crashing_grid,
)

app = Flask(__name__, template_folder="templates", static_folder="static")


def _parse_packages(payload_packages: list) -> List[WorkPackage]:
    if not payload_packages:
        return default_work_packages()
    parsed: List[WorkPackage] = []
    for item in payload_packages:
        mean_d = max(0.1, float(item.get("delay_mean_days", 2.5)))
        std_d = max(0.1, float(item.get("delay_std_days", 1.8)))
        mu, sigma = lognormal_params_from_mean_std(mean_d, std_d)
        a = float(item["optimistic"])
        c = max(a, float(item["most_likely"]))
        b = max(c, float(item["pessimistic"]))
        parsed.append(
            WorkPackage(
                name=str(item["name"]),
                optimistic=a,
                most_likely=c,
                pessimistic=b,
                delay_rate=max(0.0, float(item["delay_rate"])),
                delay_mu=mu,
                delay_sigma=sigma,
            )
        )
    return parsed


def _histogram_and_cdf(samples: np.ndarray, bins: int = 55) -> dict:
    counts, edges = np.histogram(samples, bins=bins, density=True)
    centers = 0.5 * (edges[:-1] + edges[1:])

    sorted_s = np.sort(samples)
    step = max(1, len(sorted_s) // 250)
    cdf_x = sorted_s[::step]
    cdf_y = (np.arange(1, len(sorted_s) + 1) / len(sorted_s))[::step] * 100.0

    return {
        "hist_x": [round(float(x), 2) for x in centers],
        "hist_y": [round(float(y), 5) for y in counts],
        "cdf_x": [round(float(x), 2) for x in cdf_x],
        "cdf_y": [round(float(y), 2) for y in cdf_y],
    }


@app.route("/")
def index():
    defaults = []
    # Include human-readable delay mean & std alongside internal params
    delay_defaults = [
        (2.0, 1.5),
        (3.5, 2.5),
        (4.0, 3.0),
        (2.0, 1.5),
        (3.5, 2.5),
        (2.0, 1.5),
    ]
    for wp, (dm, ds) in zip(default_work_packages(), delay_defaults):
        d = wp.to_dict()
        d["delay_mean_days"] = dm
        d["delay_std_days"] = ds
        defaults.append(d)
    return render_template("index.html", default_packages=defaults)


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    data = request.get_json(force=True) or {}
    packages = _parse_packages(data.get("packages", []))
    n_trials = min(200_000, max(1_000, int(data.get("n_trials", 50_000))))
    target_days = float(data.get("target_days", 75.0))
    seed = int(data.get("seed", 42))

    # 1. Sequential simulation
    seq_res = simulate_project_schedule(
        packages=packages, n_trials=n_trials, target_days=target_days, seed=seed, include_samples=True
    )
    seq_curves = _histogram_and_cdf(seq_res.pop("samples"))

    # 2. Parallel PERT/CPM comparison
    net_res = simulate_sequential_vs_parallel(
        packages=packages, n_trials=n_trials, target_days=target_days, seed=seed, include_samples=True
    )
    par_curves = _histogram_and_cdf(net_res["parallel"].pop("samples"))
    net_res["sequential"].pop("samples", None)

    return jsonify({
        "sequential": seq_res,
        "sequential_curves": seq_curves,
        "network": net_res,
        "parallel_curves": par_curves,
    })


@app.route("/api/crashing", methods=["POST"])
def api_crashing():
    data = request.get_json(force=True) or {}
    packages = _parse_packages(data.get("packages", []))
    n_trials = min(150_000, max(2_000, int(data.get("n_trials", 40_000))))
    target_days = float(data.get("target_days", 75.0))
    seed = int(data.get("seed", 42))

    wp3_spec = CrashingSpec(
        max_crash_days=min(10, max(1, int(data.get("wp3_max_crash", 6)))),
        cost_per_day=max(0.0, float(data.get("wp3_cost_per_day", 2500.0))),
    )
    wp4_spec = CrashingSpec(
        max_crash_days=min(8, max(1, int(data.get("wp4_max_crash", 4)))),
        cost_per_day=max(0.0, float(data.get("wp4_cost_per_day", 1800.0))),
    )

    crash_res = evaluate_crashing_grid(
        packages=packages,
        wp3_crash=wp3_spec,
        wp4_crash=wp4_spec,
        n_trials=n_trials,
        target_days=target_days,
        seed=seed,
    )
    return jsonify(crash_res)


@app.route("/api/validate", methods=["POST"])
def api_validate():
    data = request.get_json(force=True) or {}
    packages = _parse_packages(data.get("packages", []))
    n_trials = min(150_000, max(2_000, int(data.get("n_trials", 50_000))))
    threshold = float(data.get("threshold", 65.0))
    seed = int(data.get("seed", 42))

    # Closed-form Normal benchmark using modes as means and (b-a)/6 as stds
    means = [wp.most_likely for wp in packages]
    stds = [max(0.5, (wp.pessimistic - wp.optimistic) / 4.0) for wp in packages]

    val_res = validate_normal_sum_analytical(
        means=means, stds=stds, threshold=threshold, n_trials=n_trials, seed=seed, include_samples=False
    )

    # LHS vs CMC convergence grid (fast web-sized grid)
    sample_grid = [100, 250, 500, 1_000, 2_500, 5_000, 10_000, 25_000]
    lhs_res = run_convergence_comparison(
        packages=packages,
        sample_sizes=sample_grid,
        n_replicates=12,
        target_days=float(data.get("target_days", 75.0)),
        reference_trials=60_000,
    )

    return jsonify({
        "analytical": val_res,
        "convergence": lhs_res,
    })


if __name__ == "__main__":
    print("Starting Monte Carlo Schedule Risk Web Portal at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
