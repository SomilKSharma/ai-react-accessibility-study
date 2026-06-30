"""Headline figures for the enriched multi-axis study:
   Fig A — forest plot of per-axis ATTs (matched + full) with 95% CIs at zero.
   Fig B — equivalence bounds per axis (tightest certifiable SESOI)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(_HERE, "..", "data") + os.sep
FIG = os.path.join(_HERE, "..", "figures") + os.sep
rm = pd.read_csv(DIR+"enriched_results_matched.csv")
rf = pd.read_csv(DIR+"enriched_results_full.csv")

LABEL = {"semantic_score": "Semantic HTML", "keyboard_score": "Keyboard/focus",
         "wcag_total_dens": "WCAG total", "wcag_operable_dens": "WCAG operable",
         "severity_weighted_dens": "Severity-weighted"}
axes = list(LABEL)

# ---- Fig A: forest plot (standardised: ATT / pre-treated baseline, so axes comparable)
fig, ax = plt.subplots(figsize=(7.2, 4.4))
y = np.arange(len(axes))[::-1]
for off, r, col, lab in [(-0.15, rm, "#2c6fbb", "Matched (181 repos)"),
                          (0.15, rf, "#c0392b", "Full (446 repos)")]:
    rr = r.set_index("axis")
    rel = [rr.loc[a, "beta"]/abs(rr.loc[a, "base"])*100 if rr.loc[a, "base"] else 0 for a in axes]
    lo = [(rr.loc[a, "ci_lo"])/abs(rr.loc[a, "base"])*100 if rr.loc[a, "base"] else 0 for a in axes]
    hi = [(rr.loc[a, "ci_hi"])/abs(rr.loc[a, "base"])*100 if rr.loc[a, "base"] else 0 for a in axes]
    err = [np.array(rel)-np.array(lo), np.array(hi)-np.array(rel)]
    ax.errorbar(rel, y+off, xerr=err, fmt="o", color=col, capsize=3, label=lab, ms=5)
ax.axvline(0, color="grey", ls="--", lw=1)
ax.axvspan(-5, 5, color="#e8f0e8", alpha=0.5, zorder=0)
ax.set_yticks(y); ax.set_yticklabels([LABEL[a] for a in axes])
ax.set_xlabel("ATT as % of pre-treatment baseline (95% CI)")
ax.set_title("AI-tool adoption effect on four measured accessibility axes: a comprehensive null\n"
             "(all CIs span zero; shaded band = ±5% equivalence region)")
ax.legend(frameon=False, fontsize=9, loc="lower right")
fig.tight_layout(); fig.savefig(FIG+"fig7_axes_forest.png", dpi=150); fig.savefig(FIG+"fig7_axes_forest.pdf")
plt.close(fig)
print("wrote fig7_axes_forest")
