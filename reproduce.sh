#!/usr/bin/env bash
# Reproduce every table and figure in the manuscript from the shipped data.
#
#   ./reproduce.sh
#
# Runs entirely from the committed artifacts (panel.csv + data/*.csv +
# validation/*.csv) — repos.db is NOT required (it is archived on Zenodo and only
# needed to *rebuild* the derived data from scratch; pass --db to the scripts for
# that). Outputs land in results/ and figures/.
#
# Prerequisites: Python 3.12+ and `pip install -r requirements.txt`
# (ideally in a fresh virtualenv).
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python}"
mkdir -p results figures

echo "==> [1/4] Mean analysis (Section 4): stage5_did.py"
$PY stage5_did.py | tee results/stage5_results.txt

echo "==> [2/4] Dynamics analysis (Sections 5–6): dynamics_analysis.py"
$PY dynamics_analysis.py | tee results/dynamics_results.txt

echo "==> [3/4] Dynamics figures (Figures 3–5): dynamics_figures.py"
$PY dynamics_figures.py

echo "==> [4/4] Construct-validation (Appendix D): validation/analyze_raters.py"
$PY validation/analyze_raters.py | tee results/validation_results.txt

echo
echo "==> Supplementary reviewer analyses (Sections 4.2 power, 8.1 leave-out, 5.6 neg-control)"
echo "    (these run the repo-level block bootstrap and take a few minutes)"
$PY analysis/reviewer_analyses.py    | tee results/reviewer_analyses.txt
$PY analysis/negcontrol_clustered.py | tee results/negcontrol_clustered.txt

echo
echo "Done. Tables/logs in results/, figures in figures/."
echo "  results/stage5_results.txt        — mean DiD (Tables 4, 4b-input, 5, 6)"
echo "  results/dynamics_results.txt      — Markov / birth-death / tail (Tables 7, 8, 9)"
echo "  results/validation_results.txt    — Appendix D (Tables D1, D2)"
echo "  results/reviewer_analyses.txt     — power curve (Table 4b), control leave-out (8.1)"
echo "  results/negcontrol_clustered.txt  — negative-control cluster bootstrap (5.6)"
echo "  figures/figure1..5_*.png          — the five manuscript figures"
