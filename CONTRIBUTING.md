# Contributing

Start with a reproducible question: what decision improves, under which assumptions, relative to which baseline?

1. Create an issue describing the hypothesis, input data, reference method and evaluation metrics.
2. Work in a branch and keep changes focused. Never commit credentials or raw downloads.
3. Install `python -m pip install -e ".[dev]"`, then run `python -m pytest -q` and `ruff check .`.
4. Add an independent correctness check for model changes: an analytical solution, conservation law, duality condition, or equivalent reference formulation. Avoid tests that merely repeat the implementation.
5. Run `gridopt run --quick --output results/runs/pr-check` for changes affecting experiments. Use the complete seasonal protocol before replacing reference results.
6. Include solver status, feasible bounds, numerical tolerances, environment versions and data hashes with new claims. Never report a time-limited incumbent as an exact optimum.
7. Open a pull request with the problem, changed behavior, validation and limitations. Explain whether a difference exceeds numerical and MIP-gap uncertainty.

Do not select hyperparameters using the held-out week, silently modify source data, fabricate runtime improvements, or imply theoretical novelty without a literature review. Data additions must include their source, immutable version or retrieval date, redistribution terms and transformation script.

Please keep figures legible without color alone, provide useful alternative text, support keyboard use in the report, and preserve the data-use notice.
