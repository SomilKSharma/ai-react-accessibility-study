"""
Monte Carlo size-distortion study (reviewer 'good->great' item).

Demonstrates, on SYNTHETIC clustered, zero-inflated panels generated under a
KNOWN NULL (no treatment effect), that the naive pooled tail-risk z-test
rejects far above its nominal 5% rate, and that the cluster-robust treated-vs-
control DiD logit recovers ~5%. We sweep the false-positive rate as a function
of intra-class correlation (ICC) and zero-inflation, turning the paper's single
'we got fooled once' episode into a quantified size-distortion curve.

Pure numpy (no scipy). Normal CDF via math.erf. Fixed seed -> deterministic.
Outputs JSON + a matplotlib figure.
"""
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_ROOT = Path(__file__).resolve().parent.parent
OUTDIR = _ROOT / "data"
FIGDIR = _ROOT / "figures"
OUTDIR.mkdir(parents=True, exist_ok=True)
SEED = 20260629


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def two_sided_z_p(z):
    return 2.0 * (1.0 - norm_cdf(abs(z)))


def gen_panel(rng, n_repos=74, months=30, icc=0.5, zero_inflation=0.425,
              q90_frac=0.10, ctrl_drift=0.0):
    """
    Generate a null panel mimicking the real study's *clustered, zero-inflated*
    structure. NO treatment effect is injected; any rejection is a false positive.

      - n_repos repos, half treated / half control.
      - The exceedance (tail) event is CONCENTRATED within repos: each repo i
        draws a tail-propensity p_i from a Beta whose dispersion encodes the
        intra-class correlation. High-ICC -> a few 'heavy' repos own most of the
        exceedances (matching the real panel, where ~5 repos hold ~half the
        exceedances). This is what creates the large design effect the naive
        z-test ignores.
      - Outcome y is zero-inflated; positive mass is right-skewed.
      - `ctrl_drift` (better named: COMMON secular post-period trend): a
        calendar-time increase in the tail propensity that hits BOTH arms
        equally post-period. Parallel trends therefore HOLD and the true
        differential (treated) effect is exactly zero. This isolates the naive
        pooled test's failure: it has no treated-vs-control contrast, so it
        reads the common trend as a 'post' effect (false positive), whereas the
        DiD interaction nets the common trend out and stays at nominal size.
    """
    is_treated = np.array([1 if i < n_repos // 2 else 0 for i in range(n_repos)])
    adopt = rng.integers(months // 3, 2 * months // 3, size=n_repos)

    # Beta dispersion from ICC: higher ICC -> smaller concentration param ->
    # more between-repo variance in tail propensity (a few heavy repos).
    base_tail = q90_frac
    conc = max((1.0 - icc) / max(icc, 1e-3), 0.05) * 4.0   # Beta concentration
    a = base_tail * conc
    b = (1 - base_tail) * conc
    repo_tail_p = rng.beta(a, b, size=n_repos)

    rows_repo, rows_month, rows_treat, rows_post, rows_y = [], [], [], [], []
    for i in range(n_repos):
        for t in range(months):
            post = int(t >= adopt[i])
            p_i = repo_tail_p[i]
            # COMMON secular trend (both arms equally) -> parallel trends hold,
            # true differential effect is exactly zero
            if post == 1:
                p_i = min(1.0, p_i + ctrl_drift)
            if rng.random() < zero_inflation:
                y = 0.0
            elif rng.random() < p_i:
                y = 0.3 + abs(rng.normal(0, 0.15))    # tail (heavy) value
            else:
                y = abs(rng.normal(0, 0.05))          # ordinary positive value
            rows_repo.append(i)
            rows_month.append(t)
            rows_treat.append(is_treated[i])
            rows_post.append(post)
            rows_y.append(y)
    return (np.array(rows_repo), np.array(rows_month), np.array(rows_treat),
            np.array(rows_post), np.array(rows_y))


def naive_pooled_tail_z(y, post, q90_frac=0.10):
    """Two-proportion z-test on exceedance of the pooled (1-q90_frac) quantile,
    pre vs post, IGNORING clustering and treated/control split (the wrong test)."""
    q = np.quantile(y, 1 - q90_frac)
    exc = (y > q).astype(float)
    pre, pos = exc[post == 0], exc[post == 1]
    p1, p2 = pre.mean(), pos.mean()
    n1, n2 = len(pre), len(pos)
    pbar = (pre.sum() + pos.sum()) / (n1 + n2)
    se = math.sqrt(pbar * (1 - pbar) * (1 / n1 + 1 / n2)) if pbar > 0 else np.inf
    z = (p2 - p1) / se if se > 0 else 0.0
    return two_sided_z_p(z)


def cluster_robust_did_tail(repo, treat, post, y, q90_frac=0.10):
    """Correct test: DiD on tail exceedance (treated*post interaction) with a
    repo-clustered SE. Linear probability DiD via OLS + CR1 cluster SE on the
    interaction coefficient (logit and LPM agree on size under the null)."""
    q = np.quantile(y, 1 - q90_frac)
    exc = (y > q).astype(float)
    inter = treat * post
    X = np.column_stack([np.ones_like(exc), treat.astype(float),
                         post.astype(float), inter.astype(float)])
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ (X.T @ exc)
    resid = exc - X @ beta
    k = X.shape[1]
    clusters = np.unique(repo)
    G = len(clusters)
    meat = np.zeros((k, k))
    for g in clusters:
        m = repo == g
        sc = X[m].T @ resid[m]
        meat += np.outer(sc, sc)
    n = len(exc)
    dfc = (G / (G - 1.0)) * ((n - 1.0) / (n - k))
    V = dfc * (XtX_inv @ meat @ XtX_inv)
    se = math.sqrt(max(V[3, 3], 1e-12))
    z = beta[3] / se
    return two_sided_z_p(z)


def empirical_size(icc, zero_inflation, n_sims=500, alpha=0.05, seed=SEED,
                   ctrl_drift=0.0):
    rng = np.random.default_rng(seed + int(icc * 1000) + int(zero_inflation * 1000)
                                + int(ctrl_drift * 1000))
    naive_rej = robust_rej = ok = 0
    for _ in range(n_sims):
        repo, month, treat, post, y = gen_panel(rng, icc=icc,
                                                zero_inflation=zero_inflation,
                                                ctrl_drift=ctrl_drift)
        try:
            pn = naive_pooled_tail_z(y, post)
            pr = cluster_robust_did_tail(repo, treat, post, y)
        except Exception:
            continue
        ok += 1
        naive_rej += int(pn < alpha)
        robust_rej += int(pr < alpha)
    return naive_rej / ok, robust_rej / ok, ok


if __name__ == "__main__":
    results = {"alpha": 0.05, "grid": []}
    iccs = [0.1, 0.3, 0.5, 0.7]
    zis = [0.0, 0.2, 0.425, 0.6]

    print("=== Size of naive pooled tail test vs cluster-robust DiD (true null) ===")
    print("(A) tail-event concentration within repos (design effect), ctrl_drift=0")
    print(f"{'ICC':>5} {'zero-infl':>10} {'naive FPR':>10} {'robust FPR':>11}")
    for icc in iccs:
        nfpr, rfpr, ok = empirical_size(icc, 0.425, n_sims=400)
        results["grid"].append(dict(mechanism="concentration", icc=icc,
                                    zero_inflation=0.425, ctrl_drift=0.0,
                                    naive_fpr=nfpr, robust_fpr=rfpr, n=ok))
        print(f"{icc:>5.2f} {0.425:>10.3f} {nfpr:>10.3f} {rfpr:>11.3f}")

    print("\n(B) + COMMON secular trend, both arms equal (parallel, zero diff effect), ICC=0.5")
    print(f"{'trend':>6} {'naive FPR':>10} {'robust FPR':>11}")
    for drift in [0.05, 0.10, 0.15, 0.20]:
        nfpr, rfpr, ok = empirical_size(0.5, 0.425, n_sims=400, ctrl_drift=drift)
        results["grid"].append(dict(mechanism="ctrl_drift", icc=0.5,
                                    zero_inflation=0.425, ctrl_drift=drift,
                                    naive_fpr=nfpr, robust_fpr=rfpr, n=ok))
        print(f"{drift:>6.2f} {nfpr:>10.3f} {rfpr:>11.3f}")

    with open(OUTDIR / "size_distortion.json", "w") as f:
        json.dump(results, f, indent=2)

    # figure: two panels (A) FPR vs ICC, (B) FPR vs control drift
    subA = sorted([g for g in results["grid"] if g["mechanism"] == "concentration"],
                  key=lambda g: g["icc"])
    subB = sorted([g for g in results["grid"] if g["mechanism"] == "ctrl_drift"],
                  key=lambda g: g["ctrl_drift"])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))
    ax1.plot([g["icc"] for g in subA], [g["naive_fpr"] for g in subA], "o-",
             color="#c0392b", label="Naive pooled tail z-test")
    ax1.plot([g["icc"] for g in subA], [g["robust_fpr"] for g in subA], "s-",
             color="#2c7fb8", label="Cluster-robust DiD")
    ax1.axhline(0.05, ls="--", color="grey", lw=1, label="Nominal α = 0.05")
    ax1.set_xlabel("Within-repo tail concentration (ICC)")
    ax1.set_ylabel("False-positive rate (true null)")
    ax1.set_title("(a) Tail-event concentration")
    ax1.legend(frameon=False, fontsize=8)
    ax2.plot([g["ctrl_drift"] * 100 for g in subB], [g["naive_fpr"] for g in subB],
             "o-", color="#c0392b", label="Naive pooled tail z-test")
    ax2.plot([g["ctrl_drift"] * 100 for g in subB], [g["robust_fpr"] for g in subB],
             "s-", color="#2c7fb8", label="Cluster-robust DiD")
    ax2.axhline(0.05, ls="--", color="grey", lw=1)
    ax2.set_xlabel("Common secular trend (pp added to both arms post)")
    ax2.set_title("(b) Common secular trend (parallel; zero diff. effect)")
    ax2.legend(frameon=False, fontsize=8)
    for ax in (ax1, ax2):
        ax.set_ylim(0, 1.0)
    fig.suptitle("Size distortion of the naive pooled tail test under a true null\n"
                 "(synthetic zero-inflated, repo-clustered panels)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(FIGDIR / "fig6_size_distortion.png", dpi=150)
    fig.savefig(FIGDIR / "fig6_size_distortion.pdf")
    print(f"\nSaved figure -> {FIGDIR/'fig6_size_distortion.png'} (+ .pdf)")
    print(f"Saved data    -> {OUTDIR/'size_distortion.json'}")
