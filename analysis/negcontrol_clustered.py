"""Re-run the negative control (component-count/repo-size dynamics) with the SAME
repo-level block bootstrap used elsewhere, instead of an unclustered chi-square.
The thesis of the paper is 'don't trust unclustered tests on this panel', so the
negative control must obey the same rule. We bootstrap the homogeneity LR's
sampling distribution by resampling whole repos, and report a cluster-robust
exceedance rate (Section 5.6).

Reads the trimmed data/ CSVs by default; pass --db repos.db to use the full DB.
Run from the repo root:
    python analysis/negcontrol_clustered.py
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import dynamics_analysis as da

ap = argparse.ArgumentParser()
ap.add_argument("--db", nargs="?", const=str(ROOT / "repos.db"), default=None)
ap.add_argument("--data-dir", default=str(ROOT / "data"))
args = ap.parse_args()

RNG = np.random.default_rng(20260625); NB = 2000
src = da.Source(db_path=args.db, data_dir=args.data_dir)
panel = da.build_panel(src)

# state = repo-size (component_count) quartile, as in the paper's negative control
def cc_states(df):
    d = df.copy()
    d["state"] = pd.qcut(d.component_count.rank(method="first"), 4, labels=False).astype(int)
    return d
def obs_LR(df):
    seqs = da.regime_sequences(cc_states(df))
    Npre = da.count_transitions(seqs["pre"], 4); Npost = da.count_transitions(seqs["post"], 4)
    return da.homogeneity_lr(Npre, Npost)

stat, df_, p_chi2 = obs_LR(panel)
print(f"observed homogeneity LR={stat:.2f} df={df_} unclustered chi2 p={p_chi2:.4f}")

# Cluster-robust check via repo-resample: bootstrap the LR statistic's sampling
# distribution by resampling whole repos with replacement. If the unclustered
# chi2 critical value sits inside the bootstrap spread, the nominal significance
# is an artifact of ignoring clustering.
repos = panel.repo_id.unique()
def boot_LR():
    samp = RNG.choice(repos, size=len(repos), replace=True)
    parts = []
    for newid, r in enumerate(samp):
        g = panel[panel.repo_id == r].copy(); g["repo_id"] = 10_000_000 + newid; parts.append(g)
    dd = pd.concat(parts, ignore_index=True)
    try: return obs_LR(dd)[0]
    except Exception: return np.nan

boot = np.array([boot_LR() for _ in range(NB)])
boot = boot[~np.isnan(boot)]
lo, hi = np.percentile(boot, [2.5, 97.5]); med = np.median(boot)
crit = chi2.ppf(0.95, df_)
exceed = np.mean(boot >= crit)
print(f"bootstrap LR: median={med:.2f} 95%CI=[{lo:.2f},{hi:.2f}]  (chi2 .95 crit={crit:.2f}, df={df_})")
print(f"fraction of repo-resampled LRs exceeding the naive chi2 critical: {exceed:.3f}")
print("Interpretation: if the unclustered test were valid, this fraction ~0.05;")
print(f"a fraction of {exceed:.3f} quantifies how anti-conservative the naive chi2 is here.")
