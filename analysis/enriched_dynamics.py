"""
Event study + dynamics battery on the ENRICHED matched panel.
Produces (on the new 181-repo / 5,956 repo-month data):
  - event-study coefficients k=-12..+12 for semantic axis (Fig 1 pre-trend, Fig 2 dynamic)
  - joint pre-trend F-test
  - Markov transition homogeneity LR (df-corrected for occupied support)
  - Brown-Forsythe volatility test
  - tail-exceedance DiD (naive pooled vs cluster-robust treated-vs-control)
All on the primary outcome (semantic_score) and wcag_total_dens. Pure numpy.
"""
import os, json, math
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(_HERE, "..", "data") + os.sep
FIG = os.path.join(_HERE, "..", "figures") + os.sep
p = pd.read_csv(DIR + "enriched_panel.csv")
SEED = 20260629
out = {}

def ncdf(z): return 0.5*(1+math.erf(z/math.sqrt(2)))

# ── absorbed (within) event study: demean repo+month, regress on rel-month dummies
def event_study(df, y, kmin=-12, kmax=12):
    d = df.dropna(subset=[y]).copy()
    d = d[(d.rel_month >= kmin) & (d.rel_month <= kmax)]
    # treated-only event-time dummies; controls are the (rel-month NaN-equivalent) baseline
    d["k"] = np.where(d.is_treated == 1, d.rel_month.clip(kmin, kmax), -999).astype(int)
    ks = [k for k in range(kmin, kmax+1) if k != -1]   # ref = -1
    rc, _ = pd.factorize(d.repo_id); mc, _ = pd.factorize(d.month_int)
    nR, nM = rc.max()+1, mc.max()+1
    def absorb(v):
        v = v.astype(float).copy()
        for _ in range(40):
            v -= (np.bincount(rc, v, nR)/np.maximum(np.bincount(rc, None, nR), 1))[rc]
            v -= (np.bincount(mc, v, nM)/np.maximum(np.bincount(mc, None, nM), 1))[mc]
        return v
    yv = absorb(d[y].to_numpy(float))
    cols, labels = [], []
    for k in ks:
        cols.append(absorb((d.k == k).astype(float).to_numpy())); labels.append(k)
    X = np.column_stack(cols)
    b = np.linalg.pinv(X.T@X) @ (X.T@yv)
    resid = yv - X@b
    # repo-clustered SE
    cl = d.repo_id.to_numpy(); uc = np.unique(cl); G = len(uc); n = len(yv); kk = X.shape[1]
    XtX_inv = np.linalg.pinv(X.T@X); meat = np.zeros((kk, kk))
    for g in uc:
        m = cl == g; sc = X[m].T@resid[m]; meat += np.outer(sc, sc)
    V = (G/(G-1))*((n-1)/(n-kk))*(XtX_inv@meat@XtX_inv)
    se = np.sqrt(np.maximum(np.diag(V), 1e-18))
    coef = dict(zip(labels, b)); cse = dict(zip(labels, se))
    # joint pre-trend F on k in {-6,-3,-2}
    pre = [k for k in [-6, -3, -2] if k in coef]
    idx = [labels.index(k) for k in pre]
    bsub = b[idx]; Vsub = V[np.ix_(idx, idx)]
    F = float(bsub @ np.linalg.pinv(Vsub) @ bsub / len(pre))
    return coef, cse, F, len(pre)

def markov_homogeneity(df, y, nstates=4):
    d = df.dropna(subset=[y]).sort_values(["repo_id", "month_int"])
    vals = d[y].to_numpy()
    qs = np.unique(np.quantile(vals, np.linspace(0, 1, nstates+1)))
    state = np.digitize(vals, qs[1:-1])
    d = d.assign(state=state)
    def trans(sub):
        N = np.zeros((len(qs)-1, len(qs)-1))
        for _, g in sub.groupby("repo_id"):
            s = g.state.values; mi = g.month_int.values
            for a, bb, m1, m2 in zip(s, s[1:], mi, mi[1:]):
                if m2-m1 == 1: N[a, bb] += 1
        return N
    Npre = trans(d[d.is_post == 0]); Npost = trans(d[d.is_post == 1])
    def ll(N):
        P = np.divide(N, N.sum(1, keepdims=True), out=np.zeros_like(N), where=N.sum(1, keepdims=True) > 0)
        m = N > 0; return np.sum(N[m]*np.log(P[m]))
    Npool = Npre+Npost
    Pp = np.divide(Npool, Npool.sum(1, keepdims=True), out=np.zeros_like(Npool), where=Npool.sum(1, keepdims=True) > 0)
    ll0 = sum(np.sum(N[(N > 0) & (Pp > 0)]*np.log(Pp[(N > 0) & (Pp > 0)])) for N in (Npre, Npost))
    LR = 2*((ll(Npre)+ll(Npost))-ll0)
    df_ = sum(max(int((Npool[i] > 0).sum())-1, 0) for i in range(Npool.shape[0])
              if Npre[i].sum() > 0 and Npost[i].sum() > 0)
    df_ = max(df_, 1)
    # chi2 sf via series-free approx: use Wilson-Hilferty
    x = LR/df_; z = (x**(1/3) - (1-2/(9*df_)))/math.sqrt(2/(9*df_))
    return LR, df_, 1-ncdf(z)

def volatility(df, y):
    pre = df[(df.is_post == 0)][y].dropna(); post = df[(df.is_post == 1)][y].dropna()
    # Brown-Forsythe (Levene on medians)
    zp = np.abs(pre-pre.median()); zq = np.abs(post-post.median())
    n1, n2 = len(zp), len(zq); m1, m2 = zp.mean(), zq.mean(); mg = np.concatenate([zp, zq]).mean()
    num = (n1*(m1-mg)**2 + n2*(m2-mg)**2)
    den = (np.sum((zp-m1)**2)+np.sum((zq-m2)**2))/(n1+n2-2)
    W = num/den if den > 0 else 0
    return pre.var(), post.var(), W

def tail_did(df, y, q=0.90):
    d = df.dropna(subset=[y])
    thr = d[y].quantile(q)
    d = d.assign(exc=(d[y] > thr).astype(int))
    # naive pooled pre/post
    pre, post = d[d.is_post == 0].exc, d[d.is_post == 1].exc
    p1, p2 = pre.mean(), post.mean(); n1, n2 = len(pre), len(post)
    pb = (pre.sum()+post.sum())/(n1+n2); se = math.sqrt(pb*(1-pb)*(1/n1+1/n2)) if pb > 0 else 1
    znaive = (p2-p1)/se; pnaive = 2*(1-ncdf(abs(znaive)))
    # cluster-robust DiD on exceedance (LPM treated*post, repo-clustered)
    X = np.column_stack([np.ones(len(d)), d.is_treated, d.is_post, d.is_treated*d.is_post])
    XtX_inv = np.linalg.pinv(X.T@X); b = XtX_inv@(X.T@d.exc.to_numpy(float))
    r = d.exc.to_numpy(float)-X@b; cl = d.repo_id.to_numpy(); uc = np.unique(cl)
    meat = np.zeros((4, 4))
    for g in uc:
        m = cl == g; sc = X[m].T@r[m]; meat += np.outer(sc, sc)
    G = len(uc); n = len(d); V = (G/(G-1))*((n-1)/(n-4))*(XtX_inv@meat@XtX_inv)
    sed = math.sqrt(max(V[3, 3], 1e-18)); pdid = 2*(1-ncdf(abs(b[3]/sed)))
    return dict(p_naive=pnaive, did=b[3], p_did=pdid,
                rates=dict(t_pre=d[(d.is_treated==1)&(d.is_post==0)].exc.mean(),
                           t_post=d[(d.is_treated==1)&(d.is_post==1)].exc.mean(),
                           c_pre=d[(d.is_treated==0)&(d.is_post==0)].exc.mean(),
                           c_post=d[(d.is_treated==0)&(d.is_post==1)].exc.mean()))

def _states(df, y, nstates=4):
    d = df.dropna(subset=[y]).sort_values(["repo_id", "month_int"]).copy()
    vals = d[y].to_numpy()
    qs = np.unique(np.quantile(vals, np.linspace(0, 1, nstates+1)))
    d["state"] = np.digitize(vals, qs[1:-1])
    return d, len(qs)-1

def _transmat(d, k):
    N = np.zeros((k, k))
    for _, g in d.groupby("repo_id"):
        s = g.state.values; mi = g.month_int.values
        for a, b, m1, m2 in zip(s, s[1:], mi, mi[1:]):
            if m2-m1 == 1: N[a, b] += 1
    R = N.sum(1, keepdims=True)
    return N, np.divide(N, R, out=np.zeros_like(N), where=R > 0)

def _gap(P):
    ev = np.sort(np.abs(np.linalg.eigvals(P)))[::-1]
    return float(1 - ev[1]) if len(ev) > 1 else float("nan")

def persistence(df, y, nstates=4, B=2000, seed=SEED):
    """Spectral gap (1-|lambda2|) pre vs post + repo-level block-bootstrap CI on the
    gap difference, and the self-transition diagonals. Computed on the named density
    state variable y."""
    d, k = _states(df, y, nstates)
    _, Ppre = _transmat(d[d.is_post == 0], k)
    _, Ppost = _transmat(d[d.is_post == 1], k)
    gpre, gpost = _gap(Ppre), _gap(Ppost)
    rng = np.random.default_rng(seed)
    repos = d.repo_id.unique(); diffs = []
    for _ in range(B):
        samp = set(rng.choice(repos, len(repos), replace=True))
        sub = d[d.repo_id.isin(samp)]
        _, Pa = _transmat(sub[sub.is_post == 0], k)
        _, Pb = _transmat(sub[sub.is_post == 1], k)
        diffs.append(_gap(Pb) - _gap(Pa))
    diffs = np.array(diffs); lo, hi = np.percentile(diffs, [2.5, 97.5])
    return dict(gap_pre=gpre, gap_post=gpost, gap_diff=gpost-gpre,
                ci_lo=float(lo), ci_hi=float(hi),
                diag_pre=list(np.diag(Ppre)), diag_post=list(np.diag(Ppost)),
                states=k)

# ── run ───────────────────────────────────────────────────────────────────────
# Primary dynamics STATE VARIABLE is the WCAG violation-density axis (Section 5.2).
STATE_AXIS = "wcag_total_dens"

print("=== ZERO-INFLATION (enriched matched panel) ===")
zi = {a: float((p[a] == 0).mean()) for a in
      ["wcag_total_dens", "wcag_operable_dens", "wcag_perceivable_dens",
       "severity_weighted_dens", "semantic_score"] if a in p.columns}
out["zero_inflation"] = zi
for a, z in zi.items(): print(f"  {a:26} {z*100:.1f}% exactly zero")

print(f"\n=== PERSISTENCE / SPECTRAL GAP ({STATE_AXIS}, 4-state) ===")
per = persistence(p, STATE_AXIS, 4)
out["persistence"] = per
print(f"  gap pre={per['gap_pre']:.4f} post={per['gap_post']:.4f} "
      f"diff={per['gap_diff']:+.4f}  95%CI[{per['ci_lo']:+.4f},{per['ci_hi']:+.4f}]")
print(f"  diag pre ={np.round(per['diag_pre'],3)}")
print(f"  diag post={np.round(per['diag_post'],3)}")

print(f"\n=== MARKOV HOMOGENEITY ({STATE_AXIS}, 4-state) ===")
LRd, dfd, pvd = markov_homogeneity(p, STATE_AXIS, 4)
out["markov_density"] = dict(LR=LRd, df=dfd, p=pvd)
print(f"  LR={LRd:.2f} df={dfd} p={pvd:.3f}")

print(f"\n=== TAIL DiD ({STATE_AXIS}, q90 exceedance) ===")
td_d = tail_did(p, STATE_AXIS)
out["tail_density"] = td_d
print(f"  naive pooled p={td_d['p_naive']:.4f} | cluster-robust DiD={td_d['did']:+.4f} p={td_d['p_did']:.3f}")
print(f"  rates: {td_d['rates']}")

print("\n=== EVENT STUDY (semantic_score, enriched matched panel) ===")
coef, cse, F, npre = event_study(p, "semantic_score")
out["event_semantic"] = {str(k): [coef[k], cse[k]] for k in coef}
out["pretrend_F"] = F
print(f"  pre-trend joint F({npre}) = {F:.3f}")
for k in [-12, -6, -2, 0, 6, 12]:
    if k in coef: print(f"   k={k:+3d}: {coef[k]:+.4f} (se {cse[k]:.4f})")

print("\n=== MARKOV HOMOGENEITY (semantic, 4-state) ===")
LR, df_, pv = markov_homogeneity(p, "semantic_score", 4)
out["markov"] = dict(LR=LR, df=df_, p=pv)
print(f"  LR={LR:.2f} df={df_} p={pv:.3f}")

print("\n=== VOLATILITY (Brown-Forsythe, semantic) ===")
vpre, vpost, W = volatility(p, "semantic_score")
out["volatility"] = dict(var_pre=vpre, var_post=vpost, W=W)
print(f"  var_pre={vpre:.5f} var_post={vpost:.5f} BF W={W:.3f}")

print("\n=== TAIL DiD (semantic, q90 exceedance) ===")
td = tail_did(p, "semantic_score")
out["tail"] = td
print(f"  naive pooled p={td['p_naive']:.4f} | cluster-robust DiD={td['did']:+.4f} p={td['p_did']:.3f}")
print(f"  rates: {td['rates']}")

json.dump(out, open(DIR+"enriched_dynamics.json", "w"), indent=2, default=float)

# ── Fig 1: pre-trend event study (semantic) ───────────────────────────────────
ks = sorted(coef); xs = ks
fig, ax = plt.subplots(figsize=(7, 4))
b = [coef[k] for k in ks]; e = [1.96*cse[k] for k in ks]
ax.errorbar([k for k in ks if k < 0], [coef[k] for k in ks if k < 0],
            yerr=[1.96*cse[k] for k in ks if k < 0], fmt="o", color="#2c6fbb", capsize=2)
ax.axhline(0, ls="--", color="grey"); ax.axvline(-0.5, ls=":", color="grey")
ax.set_xlabel("months relative to adoption"); ax.set_ylabel(r"$\hat\beta_k$ (semantic, vs k=-1)")
ax.set_title(f"Pre-trend event study (enriched panel) — joint F={F:.2f}")
fig.tight_layout(); fig.savefig(FIG+"fig1_parallel_trends.png", dpi=150); fig.savefig(FIG+"fig1_parallel_trends.pdf"); plt.close(fig)

# ── Fig 2: full dynamic event study ───────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.5, 4))
ax.errorbar(xs, b, yerr=e, fmt="o-", color="#2c6fbb", capsize=2, ms=4)
ax.axhline(0, ls="--", color="grey"); ax.axvline(-0.5, ls=":", color="grey")
ax.set_xlabel("months relative to adoption"); ax.set_ylabel(r"$\hat\beta_k$ (semantic)")
ax.set_title("Dynamic DiD event study, enriched panel (k = -12 … +12)")
fig.tight_layout(); fig.savefig(FIG+"fig2_dynamic_did.png", dpi=150); fig.savefig(FIG+"fig2_dynamic_did.pdf"); plt.close(fig)
print("\nwrote fig1_parallel_trends, fig2_dynamic_did, enriched_dynamics.json")
