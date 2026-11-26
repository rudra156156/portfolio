from typing import Dict, Optional
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats


def _apply_clean_plot_style() -> None:
    plt.rcParams.update({
        "font.sans-serif": "DejaVu Sans",
        "axes.edgecolor": "#CCCCCC",
        "axes.linewidth": 0.8,
    })


def plot_schedule_risk_dashboard(
    results: Dict[str, object],
    save_path: Optional[str] = None,
    show: bool = False,
) -> plt.Figure:
    """Three-panel dashboard: Completion Histogram, S-Curve (CDF), and Tornado Chart."""
    _apply_clean_plot_style()

    samples = np.asarray(results["samples"])
    target_days = float(results["target_days"])
    baseline = float(results["deterministic_baseline"])
    p50 = float(results["percentiles"]["P50"])
    p95 = float(results["percentiles"]["P95"])
    mean_val = float(results["mean"])
    prob_exceed = float(results["prob_exceed_target"])
    sensitivities = dict(results["spearman_sensitivity"])

    fig = plt.figure(figsize=(14, 9), dpi=150)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 0.85], hspace=0.35, wspace=0.22)

    ax_hist = fig.add_subplot(gs[0, 0])
    ax_cdf = fig.add_subplot(gs[0, 1])
    ax_tornado = fig.add_subplot(gs[1, :])

    c_primary = "#2B5C8F"
    c_baseline = "#6C757D"
    c_p50 = "#198754"
    c_p95 = "#D97706"
    c_target = "#DC2626"

    _, bin_edges, patches = ax_hist.hist(
        samples, bins=85, density=True, color=c_primary, alpha=0.72, edgecolor="white", linewidth=0.4
    )
    for patch, left_edge in zip(patches, bin_edges[:-1]):
        if left_edge >= target_days:
            patch.set_facecolor(c_target)
            patch.set_alpha(0.55)

    ax_hist.axvline(baseline, color=c_baseline, linestyle=":", linewidth=1.6, label=f"Baseline ({baseline:.1f}d)")
    ax_hist.axvline(p50, color=c_p50, linestyle="--", linewidth=1.8, label=f"P50 Median ({p50:.1f}d)")
    ax_hist.axvline(p95, color=c_p95, linestyle="-.", linewidth=1.8, label=f"P95 VaR ({p95:.1f}d)")
    ax_hist.axvline(target_days, color=c_target, linestyle="-", linewidth=2.0,
                    label=f"Target ({target_days:.0f}d | P>T: {prob_exceed:.1%})")

    ax_hist.set_title("Project Completion Time Distribution", fontsize=11.5, fontweight="bold", pad=10)
    ax_hist.set_xlabel("Total Project Duration (Days)", fontsize=10)
    ax_hist.set_ylabel("Probability Density", fontsize=10)
    ax_hist.grid(axis="y", linestyle="--", alpha=0.35)
    ax_hist.spines["top"].set_visible(False)
    ax_hist.spines["right"].set_visible(False)
    ax_hist.legend(frameon=True, facecolor="white", framealpha=0.92, fontsize=8.5, loc="upper right")

    sorted_samples = np.sort(samples)
    cdf_y = np.arange(1, len(sorted_samples) + 1) / len(sorted_samples)
    step = max(1, len(sorted_samples) // 2000)

    ax_cdf.plot(sorted_samples[::step], cdf_y[::step] * 100.0, color=c_primary, linewidth=2.2)

    prob_on_time = (1.0 - prob_exceed) * 100.0
    ax_cdf.axhline(50, color=c_p50, linestyle="--", linewidth=1.1, alpha=0.7)
    ax_cdf.axvline(p50, color=c_p50, linestyle="--", linewidth=1.3)
    ax_cdf.scatter([p50], [50], color=c_p50, zorder=5, s=35)
    ax_cdf.annotate(f"P50: {p50:.1f}d", xy=(p50, 50), xytext=(p50 - 9, 57), fontsize=8.5, fontweight="bold", color=c_p50)

    ax_cdf.axhline(95, color=c_p95, linestyle="-.", linewidth=1.1, alpha=0.7)
    ax_cdf.axvline(p95, color=c_p95, linestyle="-.", linewidth=1.3)
    ax_cdf.scatter([p95], [95], color=c_p95, zorder=5, s=35)
    ax_cdf.annotate(f"P95: {p95:.1f}d", xy=(p95, 95), xytext=(p95 + 1.5, 88), fontsize=8.5, fontweight="bold", color=c_p95)

    ax_cdf.axvline(target_days, color=c_target, linestyle="-", linewidth=1.6)
    ax_cdf.scatter([target_days], [prob_on_time], color=c_target, zorder=6, s=45)
    ax_cdf.annotate(
        f"Target: {target_days:.0f}d\n({prob_on_time:.1f}% on-time)",
        xy=(target_days, prob_on_time),
        xytext=(target_days + 2.0, max(12.0, prob_on_time - 16.0)),
        fontsize=8.5, fontweight="bold", color=c_target,
        arrowprops=dict(arrowstyle="->", color=c_target, lw=1.0),
    )

    ax_cdf.set_title("Cumulative Probability S-Curve (CDF)", fontsize=11.5, fontweight="bold", pad=10)
    ax_cdf.set_xlabel("Total Project Duration (Days)", fontsize=10)
    ax_cdf.set_ylabel("Cumulative Probability (%)", fontsize=10)
    ax_cdf.set_ylim(0, 102)
    ax_cdf.grid(True, linestyle="--", alpha=0.35)
    ax_cdf.spines["top"].set_visible(False)
    ax_cdf.spines["right"].set_visible(False)

    sorted_items = sorted(sensitivities.items(), key=lambda item: item[1])
    labels = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    bar_colors = ["#1F4E78" if i == len(values) - 1 else "#5B8DB8" for i in range(len(values))]
    bars = ax_tornado.barh(labels, values, color=bar_colors, height=0.62, edgecolor="none")

    max_rho = max(values) if values else 1.0
    ax_tornado.set_xlim(0, min(1.05, max_rho * 1.18))

    for bar, rho in zip(bars, values):
        ax_tornado.text(
            rho + 0.012, bar.get_y() + bar.get_height() / 2.0, f"ρ = {rho:.3f}",
            va="center", ha="left", fontsize=9, fontweight="bold" if rho == max_rho else "normal", color="#222222"
        )

    ax_tornado.set_title(
        "Schedule Risk Sensitivity — Tornado Chart (Spearman Rank Correlation with Total Duration)",
        fontsize=11.5, fontweight="bold", pad=10,
    )
    ax_tornado.set_xlabel("Spearman Rank Correlation Coefficient (ρ)", fontsize=10)
    ax_tornado.grid(axis="x", linestyle="--", alpha=0.35)
    ax_tornado.spines["top"].set_visible(False)
    ax_tornado.spines["right"].set_visible(False)

    fig.suptitle(
        f"Monte Carlo Schedule Risk Simulation ({results['n_trials']:,} Trials | "
        f"Mean: {mean_val:.1f}d | CVaR 95%: {results['cvar_95_total']:.1f}d)",
        fontsize=13, fontweight="bold", y=0.97,
    )

    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=300)
    if show:
        plt.show()
    plt.close(fig)
    return fig


def plot_analytical_validation_and_convergence(
    val_results: Dict[str, object],
    save_path: Optional[str] = None,
    show: bool = False,
) -> plt.Figure:
    """Two-panel analytical normal benchmark and O(N^-1/2) standard error convergence plot."""
    _apply_clean_plot_style()

    sim_total = np.asarray(val_results["samples"])
    n_trials = int(val_results["n_trials"])
    exact_mean = float(val_results["exact_mean"])
    exact_std = float(val_results["exact_std"])
    exact_p95 = float(val_results["exact_p95"])
    exact_prob_exceed = float(val_results["exact_prob_exceed"])
    sim_mean = float(val_results["sim_mean"])
    sim_p95 = float(val_results["sim_p95"])
    sim_prob_exceed = float(val_results["sim_prob_exceed"])
    threshold = float(val_results["threshold"])

    n_grid = np.unique(np.geomspace(100, n_trials, num=60).astype(int))
    cumsum = np.cumsum(sim_total)
    cumsum_sq = np.cumsum(sim_total ** 2)

    running_means = cumsum[n_grid - 1] / n_grid
    running_vars = (cumsum_sq[n_grid - 1] - (cumsum[n_grid - 1] ** 2) / n_grid) / (n_grid - 1)
    running_se = np.sqrt(np.maximum(running_vars, 0.0)) / np.sqrt(n_grid)
    abs_mean_error = np.abs(running_means - exact_mean)

    theoretical_se = exact_std / np.sqrt(n_grid)
    theoretical_ci95_bound = 1.96 * theoretical_se

    fig, (ax_pdf, ax_conv) = plt.subplots(1, 2, figsize=(14, 5.6), dpi=150)
    plt.subplots_adjust(wspace=0.24)

    c_sim = "#2B5C8F"
    c_exact = "#111827"
    c_p95 = "#D97706"
    c_thresh = "#DC2626"
    c_conv = "#198754"

    ax_pdf.hist(
        sim_total, bins=85, density=True, color=c_sim, alpha=0.55, edgecolor="white", linewidth=0.35,
        label=f"Simulated ({n_trials:,} trials)"
    )

    x_grid = np.linspace(exact_mean - 4.2 * exact_std, exact_mean + 4.2 * exact_std, 600)
    pdf_exact = stats.norm.pdf(x_grid, loc=exact_mean, scale=exact_std)
    ax_pdf.plot(x_grid, pdf_exact, color=c_exact, linewidth=2.2, label=f"Analytical N({exact_mean:.1f}, {exact_std:.2f}²)")

    tail_mask = x_grid >= threshold
    ax_pdf.fill_between(
        x_grid[tail_mask], 0, pdf_exact[tail_mask], color=c_thresh, alpha=0.32,
        label=f"P(T > {threshold:.0f}d): Exact {exact_prob_exceed:.2%} | Sim {sim_prob_exceed:.2%}"
    )

    ax_pdf.axvline(exact_mean, color=c_exact, linestyle="--", linewidth=1.3,
                   label=f"Mean: Exact {exact_mean:.2f}d | Sim {sim_mean:.2f}d")
    ax_pdf.axvline(exact_p95, color=c_p95, linestyle="-.", linewidth=1.6,
                   label=f"P95: Exact {exact_p95:.2f}d | Sim {sim_p95:.2f}d")

    ax_pdf.set_title("Analytical Normal Benchmark vs. Simulation", fontsize=11.5, fontweight="bold", pad=10)
    ax_pdf.set_xlabel("Total Duration (Days)", fontsize=10)
    ax_pdf.set_ylabel("Probability Density", fontsize=10)
    ax_pdf.grid(axis="y", linestyle="--", alpha=0.35)
    ax_pdf.spines["top"].set_visible(False)
    ax_pdf.spines["right"].set_visible(False)
    ax_pdf.legend(frameon=True, facecolor="white", framealpha=0.93, fontsize=8.2, loc="upper left")

    ax_conv.loglog(n_grid, theoretical_ci95_bound, color="#9CA3AF", linestyle=":", linewidth=1.5,
                   label=r"95% Error Bound ($1.96\,\sigma / \sqrt{N}$)")
    ax_conv.loglog(n_grid, theoretical_se, color=c_exact, linestyle="--", linewidth=2.0,
                   label=r"Theoretical Std. Error ($\sigma / \sqrt{N}$)")
    ax_conv.loglog(n_grid, running_se, color=c_conv, linewidth=2.0, alpha=0.85,
                   label=r"Simulated Std. Error ($s_N / \sqrt{N}$)")
    ax_conv.loglog(n_grid, abs_mean_error, color=c_sim, marker="o", markersize=3.5, linewidth=1.1, alpha=0.8,
                   label=r"Observed Mean Error ($|ar{T}_N - \mu|$)")

    final_se = running_se[-1]
    final_err = abs_mean_error[-1]
    ax_conv.annotate(
        f"N = {n_trials:,}\nSE = {final_se:.4f}d\n|Err| = {final_err:.4f}d",
        xy=(n_trials, final_se), xytext=(n_trials * 0.14, final_se * 0.28),
        fontsize=8.5, fontweight="bold", color="#1F2937",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#F9FAFB", edgecolor="#D1D5DB"),
        arrowprops=dict(arrowstyle="->", color="#4B5563", lw=1.0),
    )

    ax_conv.set_title(r"Monte Carlo Convergence Rate ($\mathcal{O}(N^{-1/2})$)", fontsize=11.5, fontweight="bold", pad=10)
    ax_conv.set_xlabel("Number of Simulation Trials (N, log scale)", fontsize=10)
    ax_conv.set_ylabel("Error / Standard Error in Days (log scale)", fontsize=10)
    ax_conv.grid(True, which="both", linestyle="--", alpha=0.32)
    ax_conv.spines["top"].set_visible(False)
    ax_conv.spines["right"].set_visible(False)
    ax_conv.legend(frameon=True, facecolor="white", framealpha=0.93, fontsize=8.3, loc="lower left")

    fig.suptitle(
        "Monte Carlo Engine Verification: Closed-Form Gaussian Check & Standard Error Decay",
        fontsize=13, fontweight="bold", y=1.01,
    )

    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=300)
    if show:
        plt.show()
    plt.close(fig)
    return fig


def plot_lhs_vs_cmc_convergence(
    comp: Dict[str, object],
    save_path: Optional[str] = None,
    show: bool = False,
) -> plt.Figure:
    """Three-panel log-log RMSE convergence comparing Crude MC vs. Latin Hypercube Sampling."""
    _apply_clean_plot_style()

    n_arr = np.asarray(comp["sample_sizes"], dtype=float)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), dpi=150)
    plt.subplots_adjust(wspace=0.25)

    panels = [
        ("mean_rmse", "Mean Duration RMSE (Days)", "Estimator Error: Sample Mean"),
        ("p95_rmse", "P95 VaR RMSE (Days)", "Estimator Error: 95th Percentile (VaR)"),
        ("prob_rmse", "Exceedance Prob. RMSE", "Estimator Error: P(T > 75 Days)"),
    ]

    c_cmc = "#2B5C8F"
    c_lhs = "#D97706"

    for ax, (key, ylabel, title) in zip(axes, panels):
        cmc_err = np.asarray(comp["cmc"][key])
        lhs_err = np.asarray(comp["lhs"][key])

        ax.loglog(n_arr, cmc_err, "o-", color=c_cmc, linewidth=2.0, markersize=5, label="Crude Monte Carlo (CMC)")
        ax.loglog(n_arr, lhs_err, "s-", color=c_lhs, linewidth=2.0, markersize=5, label="Latin Hypercube (LHS)")

        ref_slope = cmc_err[0] * np.sqrt(n_arr[0] / n_arr)
        ax.loglog(n_arr, ref_slope, ":", color="#6B7280", linewidth=1.4, label=r"$\mathcal{O}(N^{-1/2})$ Reference")

        vrf = (cmc_err[-1] / lhs_err[-1]) ** 2 if lhs_err[-1] > 0 else np.nan
        ax.annotate(
            f"VRF at N={int(n_arr[-1]):,}:\n{vrf:.1f}x variance reduction",
            xy=(n_arr[-1], lhs_err[-1]), xytext=(n_arr[max(0, len(n_arr) - 3)], lhs_err[-1] * 0.45),
            fontsize=8.2, fontweight="bold", color="#92400E",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#FFFBEB", edgecolor="#FCD34D"),
            arrowprops=dict(arrowstyle="->", color="#D97706", lw=1.0),
        )

        ax.set_title(title, fontsize=11, fontweight="bold", pad=10)
        ax.set_xlabel("Sample Size N (log scale)", fontsize=9.5)
        ax.set_ylabel(ylabel, fontsize=9.5)
        ax.grid(True, which="both", linestyle="--", alpha=0.32)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(frameon=True, facecolor="white", framealpha=0.92, fontsize=8.0, loc="lower left")

    fig.suptitle(
        f"Variance Reduction Benchmark: Crude Monte Carlo vs. Latin Hypercube ({comp['n_replicates']} Replicates/Size)",
        fontsize=12.5, fontweight="bold", y=1.02,
    )

    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=300)
    if show:
        plt.show()
    plt.close(fig)
    return fig


def plot_sequential_vs_parallel_comparison(
    comp: Dict[str, object],
    save_path: Optional[str] = None,
    show: bool = False,
) -> plt.Figure:
    """Overlays Sequential vs. Parallel PERT/CPM distributions, S-curves, and Criticality Index."""
    _apply_clean_plot_style()

    seq = comp["sequential"]
    par = comp["parallel"]
    target_days = float(comp["target_days"])
    mb = comp["merge_bias"]

    s_seq = np.asarray(seq["samples"])
    s_par = np.asarray(par["samples"])

    fig = plt.figure(figsize=(14.5, 9), dpi=150)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 0.85], hspace=0.36, wspace=0.22)

    ax_hist = fig.add_subplot(gs[0, 0])
    ax_cdf = fig.add_subplot(gs[0, 1])
    ax_crit = fig.add_subplot(gs[1, :])

    c_seq = "#2B5C8F"
    c_par = "#0D9488"
    c_target = "#DC2626"

    bins = np.linspace(min(s_par.min(), s_seq.min()), max(s_par.max(), s_seq.max()), 95)
    ax_hist.hist(s_par, bins=bins, density=True, color=c_par, alpha=0.55,
                 label=f"Parallel CPM (Mean: {par['mean']:.1f}d | P95: {par['p95']:.1f}d)")
    ax_hist.hist(s_seq, bins=bins, density=True, color=c_seq, alpha=0.50,
                 label=f"Sequential (Mean: {seq['mean']:.1f}d | P95: {seq['p95']:.1f}d)")

    ax_hist.axvline(par["mean"], color=c_par, linestyle="--", linewidth=1.8)
    ax_hist.axvline(seq["mean"], color=c_seq, linestyle="--", linewidth=1.8)
    ax_hist.axvline(target_days, color=c_target, linestyle="-", linewidth=2.0, label=f"Target ({target_days:.0f}d)")

    y_top = ax_hist.get_ylim()[1]
    ax_hist.annotate("", xy=(par["mean"], y_top * 0.82), xytext=(seq["mean"], y_top * 0.82),
                     arrowprops=dict(arrowstyle="<->", color="#111827", lw=1.5))
    ax_hist.text(
        0.5 * (par["mean"] + seq["mean"]), y_top * 0.85,
        f"Mean Savings:\n-{comp['time_savings']['mean_days']:.1f}d",
        ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#111827",
    )

    ax_hist.set_title("Sequential vs. Parallel PERT/CPM Duration Distributions", fontsize=11.5, fontweight="bold", pad=10)
    ax_hist.set_xlabel("Total Project Duration (Days)", fontsize=10)
    ax_hist.set_ylabel("Probability Density", fontsize=10)
    ax_hist.grid(axis="y", linestyle="--", alpha=0.35)
    ax_hist.spines["top"].set_visible(False)
    ax_hist.spines["right"].set_visible(False)
    ax_hist.legend(frameon=True, facecolor="white", framealpha=0.92, fontsize=8.3, loc="upper right")

    step = max(1, len(s_par) // 2000)
    cdf_y = (np.arange(1, len(s_par) + 1) / len(s_par))[::step] * 100.0

    ax_cdf.plot(np.sort(s_par)[::step], cdf_y, color=c_par, linewidth=2.3,
                label=f"Parallel S-Curve (P>75d: {par['prob_exceed_target']:.1%})")
    ax_cdf.plot(np.sort(s_seq)[::step], cdf_y, color=c_seq, linewidth=2.3,
                label=f"Sequential S-Curve (P>75d: {seq['prob_exceed_target']:.1%})")

    ax_cdf.axvline(target_days, color=c_target, linestyle="-", linewidth=1.8)
    ax_cdf.axhline(95, color="#D97706", linestyle=":", linewidth=1.2, label="95th Percentile (VaR 95%)")

    ax_cdf.text(
        0.04, 0.74,
        f"Merge Bias Diagnostics (Parallel):\n"
        f"• Deterministic CPM: {par['deterministic_baseline']:.2f}d\n"
        f"• Naive PERT Mean:   {mb['naive_pert_mean']:.2f}d\n"
        f"• Simulated Mean:    {mb['simulated_parallel_mean']:.2f}d\n"
        f"• Pure Merge Bias:   +{mb['pure_merge_bias_days']:.2f}d",
        transform=ax_cdf.transAxes, fontsize=8.3, verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#F0FDFA", edgecolor="#5EEAD4"),
    )

    ax_cdf.set_title("Cumulative Probability S-Curves & Merge Bias", fontsize=11.5, fontweight="bold", pad=10)
    ax_cdf.set_xlabel("Total Project Duration (Days)", fontsize=10)
    ax_cdf.set_ylabel("Cumulative Probability (%)", fontsize=10)
    ax_cdf.set_ylim(0, 102)
    ax_cdf.grid(True, linestyle="--", alpha=0.35)
    ax_cdf.spines["top"].set_visible(False)
    ax_cdf.spines["right"].set_visible(False)
    ax_cdf.legend(frameon=True, facecolor="white", framealpha=0.92, fontsize=8.3, loc="lower right")

    wp_names = list(comp["criticality_index"].keys())[::-1]
    ci_vals = [comp["criticality_index"][k] * 100.0 for k in wp_names]
    rho_vals = [comp["parallel_sensitivity"][k] * 100.0 for k in wp_names]

    y_pos = np.arange(len(wp_names))
    height = 0.36

    bars_ci = ax_crit.barh(y_pos + height / 2, ci_vals, height=height, color="#0D9488", label="Criticality Index (% on Critical Path)")
    bars_rho = ax_crit.barh(y_pos - height / 2, rho_vals, height=height, color="#5B8DB8", label="Spearman Sensitivity (ρ × 100)")

    for bar, val in zip(bars_ci, ci_vals):
        ax_crit.text(val + 1.2, bar.get_y() + bar.get_height() / 2, f"{val:.1f}%", va="center", fontsize=8.5, fontweight="bold", color="#0F766E")
    for bar, val in zip(bars_rho, rho_vals):
        ax_crit.text(val + 1.2, bar.get_y() + bar.get_height() / 2, f"ρ={val/100:.2f}", va="center", fontsize=8.2, color="#1E3A8A")

    ax_crit.set_yticks(y_pos)
    ax_crit.set_yticklabels(wp_names, fontsize=9.5)
    ax_crit.set_xlim(0, 114)
    ax_crit.set_xlabel("Percentage / Scaled Rank Correlation (%)", fontsize=10)
    ax_crit.set_title("Parallel Network Risk Drivers: Criticality Index vs. Spearman Sensitivity", fontsize=11.5, fontweight="bold", pad=10)
    ax_crit.grid(axis="x", linestyle="--", alpha=0.35)
    ax_crit.spines["top"].set_visible(False)
    ax_crit.spines["right"].set_visible(False)
    ax_crit.legend(frameon=True, facecolor="white", framealpha=0.92, fontsize=8.5, loc="lower right")

    fig.suptitle(
        f"Sequential vs. Parallel PERT/CPM Schedule Comparison ({comp['n_trials']:,} Trials)",
        fontsize=13, fontweight="bold", y=0.97,
    )

    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=300)
    if show:
        plt.show()
    plt.close(fig)
    return fig


def plot_crashing_pareto_frontier(
    crash_results: Dict[str, object],
    save_path: Optional[str] = None,
    show: bool = False,
) -> plt.Figure:
    """Two-panel Cost vs. 95% VaR Pareto efficient frontier and exceedance probability."""
    _apply_clean_plot_style()

    all_p = crash_results["all_policies"]
    pareto = crash_results["pareto_frontier"]
    target_days = float(crash_results["target_days"])
    dominated = [p for p in all_p if not p["is_pareto"]]

    fig, (ax_pareto, ax_prob) = plt.subplots(1, 2, figsize=(14.5, 5.8), dpi=150)
    plt.subplots_adjust(wspace=0.24)

    c_dom = "#94A3B8"
    c_par = "#0D9488"
    c_target = "#DC2626"

    ax_pareto.scatter(
        [p["cost"] / 1000.0 for p in dominated], [p["var_95"] for p in dominated],
        color=c_dom, alpha=0.65, s=42, label="Dominated Crashing Policies", zorder=2
    )

    p_costs = [p["cost"] / 1000.0 for p in pareto]
    p_vars = [p["var_95"] for p in pareto]

    ax_pareto.plot(p_costs, p_vars, color=c_par, linestyle="-", linewidth=2.2, zorder=3, label="Pareto Efficient Frontier")
    ax_pareto.scatter(p_costs, p_vars, color=c_par, edgecolor="#0F766E", linewidth=1.2, s=68, zorder=4)
    ax_pareto.axhline(target_days, color=c_target, linestyle="--", linewidth=1.6, label=f"Target Deadline ({target_days:.0f}d)")

    for idx, p in enumerate(pareto):
        if idx in (0, len(pareto) - 1) or idx % 2 == 0:
            ax_pareto.annotate(
                f"{p['label']}\n(${p['cost']/1000:.1f}k, {p['var_95']:.1f}d)",
                xy=(p["cost"] / 1000.0, p["var_95"]),
                xytext=(6, 6 if idx % 2 == 0 else -22),
                textcoords="offset points", fontsize=7.8, fontweight="bold", color="#111827",
            )

    ax_pareto.set_title("Schedule Crashing: Cost vs. 95% VaR Pareto Frontier", fontsize=11.5, fontweight="bold", pad=10)
    ax_pareto.set_xlabel("Crashing Budget ($ Thousands)", fontsize=10)
    ax_pareto.set_ylabel("95th Percentile Completion Time — VaR 95% (Days)", fontsize=10)
    ax_pareto.grid(True, linestyle="--", alpha=0.35)
    ax_pareto.spines["top"].set_visible(False)
    ax_pareto.spines["right"].set_visible(False)
    ax_pareto.legend(frameon=True, facecolor="white", framealpha=0.92, fontsize=8.5, loc="upper right")

    ax_prob.scatter(
        [p["cost"] / 1000.0 for p in dominated], [p["prob_exceed_target"] * 100.0 for p in dominated],
        color=c_dom, alpha=0.65, s=42, label="Dominated Policies"
    )
    ax_prob.plot(p_costs, [p["prob_exceed_target"] * 100.0 for p in pareto], "o-", color="#2B5C8F",
                 linewidth=2.2, markersize=6.5, label="Pareto Frontier Policies")

    compliant = [p for p in pareto if p["var_95"] <= target_days]
    if compliant:
        opt = compliant[0]
        ax_prob.scatter([opt["cost"] / 1000.0], [opt["prob_exceed_target"] * 100.0], color="#D97706", s=110, zorder=5,
                        label=f"Min-Cost 95% Compliant: {opt['label']}")
        ax_prob.annotate(
            f"Meets VaR ≤ {target_days:.0f}d:\n{opt['label']} (${opt['cost']/1000:.1f}k)",
            xy=(opt["cost"] / 1000.0, opt["prob_exceed_target"] * 100.0),
            xytext=(opt["cost"] / 1000.0 + 1.2, opt["prob_exceed_target"] * 100.0 + 6.5),
            fontsize=8.3, fontweight="bold", color="#92400E",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFFBEB", edgecolor="#FCD34D"),
            arrowprops=dict(arrowstyle="->", color="#D97706", lw=1.0),
        )

    ax_prob.set_title(f"Tail Exceedance Risk P(T > {target_days:.0f}d) vs. Crashing Cost", fontsize=11.5, fontweight="bold", pad=10)
    ax_prob.set_xlabel("Crashing Budget ($ Thousands)", fontsize=10)
    ax_prob.set_ylabel(f"Probability of Exceeding {target_days:.0f} Days (%)", fontsize=10)
    ax_prob.grid(True, linestyle="--", alpha=0.35)
    ax_prob.spines["top"].set_visible(False)
    ax_prob.spines["right"].set_visible(False)
    ax_prob.legend(frameon=True, facecolor="white", framealpha=0.92, fontsize=8.5, loc="upper right")

    fig.suptitle(
        f"Parallel PERT/CPM Crashing Optimization on WP3 & WP4 ({crash_results['n_trials']:,} CRN Trials)",
        fontsize=13, fontweight="bold", y=1.01,
    )

    if save_path:
        fig.savefig(save_path, bbox_inches="tight", dpi=300)
    if show:
        plt.show()
    plt.close(fig)
    return fig
