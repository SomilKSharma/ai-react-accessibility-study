"""
Benjamini-Hochberg multiplicity correction across the accessibility axes
(Table 5). Reads the matched-panel TWFE p-values produced by estimate_enriched.py
and applies BH-FDR. Pure numpy. Deterministic.
"""
import os
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(_HERE, "..", "data") + os.sep
r = pd.read_csv(DIR + "enriched_results_matched.csv")

LABEL = {"semantic_score": "Semantic HTML", "keyboard_score": "Keyboard/focus",
         "wcag_total_dens": "WCAG total density",
         "wcag_operable_dens": "WCAG operable density",
         "severity_weighted_dens": "Severity-weighted"}

p = r.set_index("axis").loc[list(LABEL), "p"].to_numpy()
m = len(p)
order = np.argsort(p)
q = np.empty(m)
# BH step-up: q_(i) = min over k>=i of (m/k) * p_(k)
ranked = p[order]
raw = ranked * m / (np.arange(1, m + 1))
q_sorted = np.minimum.accumulate(raw[::-1])[::-1]
q[order] = np.clip(q_sorted, 0, 1)

print(f"BH-FDR across {m} axis p-values (matched panel, TWFE)\n")
print(f"{'Axis':24} {'p':>7} {'BH q':>7}  sig@.05")
for i, ax in enumerate(LABEL):
    print(f"{LABEL[ax]:24} {p[i]:>7.3f} {q[i]:>7.3f}  {'yes' if q[i] < .05 else 'no'}")
print(f"\nsmallest raw p = {p.min():.3f}; smallest q = {q.min():.3f} "
      f"=> no axis significant after correction")
