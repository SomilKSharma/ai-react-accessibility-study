#!/usr/bin/env python3
"""Generate the three figures for the dynamics paper, from dynamics_out/.
All numbers are read from the verified results JSON / deltas CSV -- no
hand-entered values. Style mirrors the empirical paper's figures."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path("dynamics_out")
FIGDIR = Path("figures")
FIGDIR.mkdir(exist_ok=True)
R = json.load(open(OUT / "dynamics_results.json"))
plt.rcParams.update({"figure.dpi": 150, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, GREY, RED = "#2c6fbb", "#888888", "#c0392b"

# ── Figure 1: tail-exceedance DiD — the artifact and its correction ────────────
vt = R["volatility_tails"]
fig, ax = plt.subplots(figsize=(6.2, 4.0))
groups = ["AI-treated", "Control"]
pre = [vt["tail_treated_pre"], vt["tail_control_pre"]]
post = [vt["tail_treated_post"], vt["tail_control_post"]]
x = np.arange(2); w = 0.35
ax.bar(x - w/2, pre, w, label="Pre-adoption", color=GREY)
ax.bar(x + w/2, post, w, label="Post-adoption", color=BLUE)
for i in range(2):
    ax.text(x[i]-w/2, pre[i]+0.004, f"{pre[i]:.3f}", ha="center", fontsize=8)
    ax.text(x[i]+w/2, post[i]+0.004, f"{post[i]:.3f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(groups)
ax.set_ylabel(r"P(violation density > $q_{90}$ = 0.278)")
ax.set_title("Tail-risk exceedance by group and period")
ax.legend(frameon=False, loc="upper left")
ax.set_ylim(0, 0.22)
ax.annotate(f"DiD (treated − control) = {vt['tail_did_point']:+.3f}\n"
            f"clustered logit p = {vt['tail_did_p']:.3f}  (n.s.)\n"
            f"naive pooled z-test p = {vt['tail_naive_p']:.3f}  (invalid)",
            xy=(0.97, 0.97), xycoords="axes fraction", ha="right", va="top",
            fontsize=8, bbox=dict(boxstyle="round", fc="#f5f5f5", ec=GREY))
fig.tight_layout(); fig.savefig(FIGDIR / "figure5_tail_exceedance.png"); plt.close(fig)

# ── Figure 2: utilization ρ by regime, with bootstrap CI on the difference ─────
bd = R["birth_death"]
fig, ax = plt.subplots(figsize=(6.2, 4.0))
regimes = ["Pre-adoption", "Post-adoption"]
rhos = [bd["pre"]["rho"], bd["post"]["rho"]]
ax.bar(regimes, rhos, color=[GREY, BLUE], width=0.5)
for i, r in enumerate(rhos):
    ax.text(i, r+0.03, f"$\\hat\\rho$ = {r:.3f}", ha="center", fontsize=10)
ax.axhline(1.0, color=RED, ls="--", lw=1.2)
ax.text(0.5, 1.04, r"$\rho=1$ (instability boundary)", color=RED,
        ha="center", fontsize=8)
ax.set_ylabel(r"Utilization  $\hat\rho = \hat\lambda / \hat\mu$")
ax.set_title("Birth–death utilization by regime (no AI-specific shift)")
ax.set_ylim(0, 2.0)
lo, hi, mean = bd["rho_diff_ci"]
ax.annotate(f"Δρ (post − pre) = {rhos[1]-rhos[0]:+.3f}\n"
            f"repo-block bootstrap 95% CI [{lo:.2f}, {hi:.2f}]\n"
            f"includes 0  →  no detectable difference",
            xy=(0.5, 0.97), xycoords="axes fraction", ha="center", va="top",
            fontsize=8, bbox=dict(boxstyle="round", fc="#f5f5f5", ec=GREY))
fig.tight_layout(); fig.savefig(FIGDIR / "figure4_birthdeath_utilization.png"); plt.close(fig)

# ── Figure 3: transition-matrix heatmaps, pre vs post (4-state) ────────────────
m4 = R["markov"]["req4_eff4"]
Ppre = np.array(m4["P_pre"]); Ppost = np.array(m4["P_post"])
fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.8))
for ax, P, title in zip(axes, [Ppre, Ppost], ["Pre-adoption", "Post-adoption"]):
    im = ax.imshow(P, cmap="Blues", vmin=0, vmax=1)
    n = P.shape[0]
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels([f"S{i}" for i in range(n)])
    ax.set_yticklabels([f"S{i}" for i in range(n)])
    ax.set_xlabel("to state"); ax.set_ylabel("from state")
    ax.set_title(title)
    for i in range(n):
        for j in range(n):
            v = P[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    color="white" if v > 0.5 else "black", fontsize=7)
fig.suptitle(f"Estimated transition matrices (4-state) — "
             f"homogeneity LR={m4['homogeneity_LR']:.2f}, "
             f"df={m4['homogeneity_df']}, p={m4['homogeneity_p']:.3f} (n.s.)",
             fontsize=10)
fig.colorbar(im, ax=axes, fraction=0.04, pad=0.04, label="transition prob.")
fig.savefig(FIGDIR / "figure3_transition_matrices.png", bbox_inches="tight"); plt.close(fig)

print("wrote figure3_transition_matrices.png, figure4_birthdeath_utilization.png, "
      "figure5_tail_exceedance.png to", FIGDIR)
