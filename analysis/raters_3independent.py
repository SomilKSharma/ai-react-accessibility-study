"""
Construct-validity statistics for the THREE INDEPENDENT raters only (R2,R3,R4),
reported alongside the all-four numbers, per reviewer request: the originating
rater R1 designed the metric, so we show the validation does not rest on R1.

Also re-does the Appendix D bootstrap by resampling COMPONENTS (the unit the
statistic is computed over: 53 components), not repos, which is the correct
resampling unit for a component-level correlation. Pure numpy (no scipy/
krippendorff): Spearman via rank-Pearson; ordinal Krippendorff's alpha via the
standard coincidence-matrix formula with the interval/ordinal difference metric.
"""
import csv
import math
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent / "data"
OUTDIR = ROOT
rows = list(csv.DictReader(open(ROOT / "ratings.csv")))
ast = np.array([float(r["ast_score"]) for r in rows])
R1 = np.array([float(r["my_rating"]) for r in rows])
R2 = np.array([float(r["rater_2yr"]) for r in rows])
R3 = np.array([float(r["rater_6yr"]) for r in rows])
R4 = np.array([float(r["rater_10yr"]) for r in rows])
n = len(rows)


def rankdata(a):
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), float)
    sa = a[order]
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and sa[j + 1] == sa[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def spearman(x, y):
    rx, ry = rankdata(x), rankdata(y)
    rx -= rx.mean(); ry -= ry.mean()
    return float((rx @ ry) / math.sqrt((rx @ rx) * (ry @ ry)))


def krippendorff_ordinal(M):
    """M: items x raters matrix of ordinal scores (no missing). Ordinal alpha
    via coincidence matrix with the standard ordinal difference metric."""
    items, m = M.shape
    vals = sorted(set(M.flatten().tolist()))
    vidx = {v: i for i, v in enumerate(vals)}
    V = len(vals)
    # coincidence matrix
    coinc = np.zeros((V, V))
    for i in range(items):
        ri = M[i]
        mu = len(ri)
        for a in range(mu):
            for b in range(mu):
                if a != b:
                    coinc[vidx[ri[a]], vidx[ri[b]]] += 1.0 / (mu - 1)
    nc = coinc.sum(1)            # marginal counts
    N = nc.sum()
    # ordinal metric delta^2(c,k) = (sum_{g=c..k} n_g - (n_c+n_k)/2)^2
    def delta2(c, k):
        if c == k:
            return 0.0
        lo, hi = min(c, k), max(c, k)
        s = nc[lo:hi + 1].sum() - (nc[c] + nc[k]) / 2.0
        return s * s
    Do = 0.0
    for c in range(V):
        for k in range(V):
            Do += coinc[c, k] * delta2(c, k)
    De = 0.0
    for c in range(V):
        for k in range(V):
            De += nc[c] * nc[k] * delta2(c, k)
    De = De / (N - 1)
    if De == 0:
        return 1.0
    return float(1 - Do / De)


def boot_ci(fn, B=2000, seed=20260629):
    rng = np.random.default_rng(seed)
    vals = []
    idx = np.arange(n)
    for _ in range(B):
        s = rng.choice(idx, size=n, replace=True)
        try:
            vals.append(fn(s))
        except Exception:
            pass
    vals = np.array(vals)
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


if __name__ == "__main__":
    out = {}
    M_all = np.column_stack([R1, R2, R3, R4])
    M_ind = np.column_stack([R2, R3, R4])           # 3 independent raters
    pooled_all = M_all.mean(1)
    pooled_ind = M_ind.mean(1)

    a_all = krippendorff_ordinal(M_all)
    a_ind = krippendorff_ordinal(M_ind)
    rho_all = spearman(pooled_all, ast)
    rho_ind = spearman(pooled_ind, ast)
    rho_R1 = spearman(R1, ast)

    ci_a_ind = boot_ci(lambda s: krippendorff_ordinal(M_ind[s]))
    ci_rho_ind = boot_ci(lambda s: spearman(pooled_ind[s], ast[s]))
    ci_rho_all = boot_ci(lambda s: spearman(pooled_all[s], ast[s]))

    print("=== Construct validity: all 4 raters vs 3 INDEPENDENT (R2,R3,R4) ===")
    print(f"Krippendorff alpha  : all4={a_all:.3f}   ind3={a_ind:.3f}  CI{tuple(round(x,3) for x in ci_a_ind)}")
    print(f"Pooled Spearman rho : all4={rho_all:.3f} CI{tuple(round(x,3) for x in ci_rho_all)}"
          f"   ind3={rho_ind:.3f} CI{tuple(round(x,3) for x in ci_rho_ind)}")
    print(f"R1 (designer) rho   : {rho_R1:.3f}   (per-rater range incl R1)")
    for nm, r in [("R1", R1), ("R2", R2), ("R3", R3), ("R4", R4)]:
        print(f"   {nm} vs AST: rho={spearman(r, ast):.3f}")

    # band monotonicity, pooled over 3 independent raters
    bands = [(0,0.50),(0.50,0.70),(0.70,0.85),(0.85,0.95),(0.95,0.99),(0.99,1.0001)]
    print("\nBand monotonicity (3 independent raters, pooled mean):")
    band_means = []
    for lo, hi in bands:
        mask = (ast >= lo) & (ast < hi)
        if mask.sum() > 0:
            mval = pooled_ind[mask].mean()
            band_means.append(round(float(mval), 2))
            print(f"   [{lo:.2f},{hi:.2f}) n={int(mask.sum())} mean={mval:.2f}")
    # check non-decreasing
    nondecr = all(band_means[i] <= band_means[i+1] + 1e-9 for i in range(len(band_means)-1))
    print(f"   non-decreasing? {nondecr}  (note: 0.85-0.95 vs 0.95-0.99 tie in all-4 data)")

    out = dict(alpha_all4=a_all, alpha_ind3=a_ind, alpha_ind3_ci=ci_a_ind,
               rho_all4=rho_all, rho_all4_ci=ci_rho_all,
               rho_ind3=rho_ind, rho_ind3_ci=ci_rho_ind, rho_R1=rho_R1,
               per_rater={nm: spearman(r, ast) for nm, r in
                          [("R1",R1),("R2",R2),("R3",R3),("R4",R4)]},
               band_means_ind3=band_means)
    json.dump(out, open(OUTDIR / "raters_3independent.json", "w"), indent=2)
    print(f"\nSaved -> {OUTDIR/'raters_3independent.json'}")
