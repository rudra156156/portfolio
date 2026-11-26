# Monte Carlo Project Schedule Risk Simulator & Web Portal

A modular Python simulation suite and interactive Flask web portal for stochastic project schedule risk analysis.

## Project Structure

```text
monte_carlo_schedule_portal/
├── simulator/
│   ├── __init__.py             # Package exports
│   ├── core.py                 # Triangular + Compound Poisson-Lognormal engine & Normal verification
│   ├── variance_reduction.py   # Latin Hypercube Sampling (LHS) vs. Crude Monte Carlo benchmark
│   ├── network_crashing.py     # Sequential vs. Parallel PERT/CPM merge bias & WP3/WP4 crashing
│   └── visualization.py        # Publication-ready Matplotlib charts (300 DPI PNG export)
├── web_portal/
│   ├── app.py                  # Flask REST API & web server
│   └── templates/
│       └── index.html          # Interactive dashboard (Chart.js + live parameter editors)
├── docs/
│   └── methodology_and_crashing.tex  # Publication-ready LaTeX mathematical formulation
├── outputs/                    # Generated PNG plots from CLI demo
├── run_demo.py                 # Standalone CLI benchmark & chart generator
└── requirements.txt
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Launch the interactive Web Portal:**
   ```bash
   python web_portal/app.py
   ```
   Open `http://127.0.0.1:5000` in your browser to adjust work package parameters, run 100,000-trial simulations, explore the WP3/WP4 crashing Pareto frontier, and inspect the analytical Gaussian and LHS convergence checks.

3. **Run the standalone CLI demo & export PNG figures:**
   ```bash
   python run_demo.py
   ```
