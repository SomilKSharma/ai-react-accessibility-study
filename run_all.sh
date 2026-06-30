#!/usr/bin/env bash
# Reproduce every number, table, and figure in the manuscript from the shipped
# enriched-panel data. Runs entirely from the committed artifacts in data/ —
# the full SQLite database (repos.db) is NOT required and is only needed to
# *rebuild* the panels from scratch (build_enriched_panel.py / stage4_scale.py).
#
#   ./run_all.sh
#
# Prerequisites: Python 3.10+, `pip install -r requirements.txt`, and Node.js
# (only if you want to re-run the static accessibility analyzer; the panels are
# already shipped, so Node is optional for reproduction).
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

echo "==> [1/4] Mean effects, equivalence, wild-cluster, control-arm (Tables 4, 4a, 4b)"
$PY analysis/estimate_enriched.py

echo
echo "==> [2/4] Dynamics: zero-inflation, persistence/spectral-gap, homogeneity, tail (Tables 7, 9; Figs 1-3)"
$PY analysis/enriched_dynamics.py

echo
echo "==> [3/4] Multiplicity correction across axes (Table 5)"
$PY analysis/multiplicity.py

echo
echo "==> [4/4] Per-axis ATT forest plot (Figure 7)"
$PY analysis/fig_enriched.py

echo
echo "Done."
echo "  data/enriched_results_matched.csv  — primary mean-effect estimates (Tables 4, 4b)"
echo "  data/enriched_results_full.csv     — full-panel robustness (Table 4a)"
echo "  data/enriched_dynamics.json        — persistence, homogeneity, tail (Tables 7, 9)"
echo "  figures/fig1..8_*.png/pdf          — manuscript figures"
echo
echo "Optional, NOT run here (require repos.db, archived on Zenodo):"
echo "  analysis/build_enriched_panel.py   — rebuild panels from the SQLite DB"
echo "  analysis/stage4_scale.py           — re-measure repos with the AST analyzer"
echo "  analysis/a11y_analyzer.js          — the render-free static accessibility analyzer"
