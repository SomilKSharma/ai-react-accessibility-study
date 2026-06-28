#!/usr/bin/env python3
"""
Dynamics analysis for the second paper:
"Beyond the Mean: Stochastic Dynamics of Accessibility Quality in
AI-Assisted React Development."

Reuses the EXACT panel of stage5_did.py (74 repos, 41 treated / 33 control)
and the same treatment-date / regime logic. Adds the per-file-keyed
month-to-month diffing that the empirical paper never computed, then:

  1. State discretization (pooled quantiles; 3/4/5-state sensitivity)
  2. Discrete-time Markov transition matrices P^pre, P^post (MLE)
  3. Stationary distribution, dwell/return times, spectral gap
  4. Markov-order LR test (1st vs 2nd), pre/post homogeneity LR test
  5. Monthly discrete-time birth-death: lambda, mu, rho per regime
  6. Volatility (Levene / Brown-Forsythe) + upper-tail comparison
  7. Repo-level block bootstrap CIs for all regime contrasts
  8. Negative control on a stylistic metric (component_count growth)

All numbers print to stdout AND dump to dynamics_out/ as JSON + CSV so the
paper can cite them verbatim. No fabrication: if the thesis fails, it fails.

DATA SOURCE
-----------
By default this reads the trimmed, file-level CSVs shipped in data/ (generated
by build_file_diffs.py); pass --db repos.db to read the full SQLite database
instead. Both paths are bit-for-bit identical: the trimmed CSVs carry exactly
the columns build_panel()/compute_deltas() consume, and the pre/post regime and
treated/control labels are RE-DERIVED from matched_pairs + treatment_dates the
same way under either source. repos.db is archived on Zenodo (see README).
"""
import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.linalg import eig

DATA_DIR = Path("data")
DB_PATH = "repos.db"
OUT = Path("dynamics_out")
OUT.mkdir(exist_ok=True)

INCLUSION_MIN_MONTHS = 12
INCLUSION_MIN_RENDERABLE = 100
RNG = np.random.default_rng(20260625)   # fixed seed; no Date/random nondeterminism
N_BOOT = 2000


# ── Data source: trimmed CSV (default) or full SQLite DB (--db) ─────────────────

class Source:
    """Provides the raw frames build_panel()/compute_deltas() need, from either
    the trimmed file-level CSVs (default) or the full repos.db (--db)."""

    def __init__(self, db_path=None, data_dir=DATA_DIR):
        self.db_path = db_path
        self.data_dir = Path(data_dir)
        if db_path:
            self.conn = sqlite3.connect(db_path)
            self._fl = None
        else:
            self.conn = None
            fl = self.data_dir / "file_diffs.csv"
            if not fl.exists():
                raise FileNotFoundError(
                    f"{fl} not found. Either generate it with "
                    f"`python build_file_diffs.py --db repos.db` (repos.db is on "
                    f"Zenodo, see README), or run with `--db repos.db`.")
            self._fl = pd.read_csv(fl)
            self._pairs = pd.read_csv(self.data_dir / "matched_pairs.csv")
            self._tdates = pd.read_csv(self.data_dir / "treatment_dates.csv")

    # Coverage per repo: distinct months and total renderable files.
    def coverage(self):
        if self.conn is not None:
            return pd.read_sql_query(
                "SELECT a.repo_id, COUNT(DISTINCT a.snapshot_month) AS m, "
                "SUM(a.renderable) AS rr FROM axe_results a GROUP BY a.repo_id",
                self.conn)
        g = self._fl.groupby("repo_id")
        return pd.DataFrame({"m": g.snapshot_month.nunique(),
                             "rr": g.renderable.sum()}).reset_index()

    def matched_pairs(self):
        if self.conn is not None:
            return pd.read_sql_query(
                "SELECT treated_repo_id, control_repo_id FROM matched_pairs "
                "WHERE match_rank=1", self.conn)
        return self._pairs.copy()

    def treatment_dates(self):
        if self.conn is not None:
            return pd.read_sql_query(
                "SELECT repo_id, treatment_date FROM repo_qualification", self.conn)
        return self._tdates.copy()

    # Per-snapshot aggregates (one row per repo-month).
    def snapshot_aggregates(self):
        if self.conn is not None:
            snaps = pd.read_sql_query(
                "SELECT id AS snapshot_id, repo_id, snapshot_month FROM snapshots",
                self.conn)
            axe_agg = pd.read_sql_query(
                "SELECT snapshot_id, COUNT(*) AS component_count, "
                "SUM(renderable) AS renderable_count, "
                "SUM(violations_total) AS violations_total "
                "FROM axe_results GROUP BY snapshot_id", self.conn)
            return snaps.merge(axe_agg, on="snapshot_id", how="left")
        g = self._fl.groupby(["repo_id", "snapshot_month"])
        agg = g.agg(component_count=("component_file", "count"),
                    renderable_count=("renderable", "sum"),
                    violations_total=("violations_total", "sum")).reset_index()
        return agg

    # File-level rows for the per-file month-to-month deltas.
    def file_level(self, repo_ids):
        if self.conn is not None:
            qmarks = ",".join("?" * len(repo_ids))
            return pd.read_sql_query(
                f"SELECT s.repo_id, s.snapshot_month, a.component_file, "
                f"a.violations_total FROM axe_results a "
                f"JOIN snapshots s ON a.snapshot_id=s.id "
                f"WHERE s.repo_id IN ({qmarks})", self.conn, params=repo_ids)
        return self._fl[self._fl.repo_id.isin(repo_ids)][
            ["repo_id", "snapshot_month", "component_file", "violations_total"]].copy()


def month_to_int(month_str: str) -> int:
    y, m = map(int, month_str.split("-"))
    return (y - 2020) * 12 + (m - 1)


# ── Panel (identical inclusion/treatment logic to stage5_did.py) ───────────────

def build_panel(src):
    cov = src.coverage()
    inc = cov[(cov.m >= INCLUSION_MIN_MONTHS) & (cov.rr >= INCLUSION_MIN_RENDERABLE)].copy()

    pairs = src.matched_pairs()
    treated_ids, control_ids = set(pairs.treated_repo_id), set(pairs.control_repo_id)
    inc = inc[inc.repo_id.isin(treated_ids | control_ids)].copy()
    inc["is_treated"] = inc.repo_id.apply(lambda r: 1 if r in treated_ids else 0)

    qual = src.treatment_dates()
    treated_tdates = qual[qual.repo_id.isin(treated_ids)].set_index("repo_id")["treatment_date"]
    pw = pairs.merge(treated_tdates.rename("td"), left_on="treated_repo_id",
                     right_index=True, how="left")
    ctrl_inherited = pw.groupby("control_repo_id")["td"].min()
    tdmap = qual.set_index("repo_id")["treatment_date"]

    def resolve(r):
        if r in treated_ids:
            return tdmap.get(r)
        return ctrl_inherited.get(r)
    inc["treatment_date"] = inc.repo_id.apply(resolve)
    inc["treatment_month_str"] = inc.treatment_date.apply(
        lambda t: t[:7] if isinstance(t, str) else None)
    inc = inc.dropna(subset=["treatment_month_str"])

    panel = src.snapshot_aggregates().merge(
        inc[["repo_id", "is_treated", "treatment_month_str"]], on="repo_id", how="inner")
    panel["axe_renderable_per_file"] = np.where(
        panel.renderable_count > 0, panel.violations_total / panel.renderable_count, np.nan)
    panel["month_int"] = panel.snapshot_month.apply(month_to_int)
    panel["t_month_int"] = panel.treatment_month_str.apply(month_to_int)
    panel["is_post"] = (panel.month_int >= panel.t_month_int).astype(int)
    panel["rel_month"] = panel.month_int - panel.t_month_int
    panel = panel.dropna(subset=["axe_renderable_per_file"])
    panel = panel.sort_values(["repo_id", "month_int"]).reset_index(drop=True)
    return panel


# ── File-keyed month-to-month deltas (introduced / removed violations) ─────────

def compute_deltas(src, panel):
    """For each repo, diff consecutive monthly snapshots at the FILE level to
    recover violations introduced (births) and removed (deaths). This is the
    derived quantity the empirical paper never produced."""
    repo_ids = panel.repo_id.unique().tolist()
    axe = src.file_level(repo_ids)
    axe["month_int"] = axe.snapshot_month.apply(month_to_int)

    rows = []
    meta = panel[["repo_id", "month_int", "is_treated", "is_post"]].drop_duplicates()
    meta_idx = meta.set_index(["repo_id", "month_int"])
    for rid, g in axe.groupby("repo_id"):
        months = sorted(g.month_int.unique())
        by_month = {mi: dict(zip(sub.component_file, sub.violations_total))
                    for mi, sub in g.groupby("month_int")}
        for prev, cur in zip(months, months[1:]):
            if cur - prev != 1:      # only adjacent calendar months → 1-step
                continue
            a, b = by_month[prev], by_month[cur]
            introduced = removed = 0
            for f in set(a) | set(b):
                d = b.get(f, 0) - a.get(f, 0)
                if d > 0:
                    introduced += d
                elif d < 0:
                    removed += -d
            try:
                m = meta_idx.loc[(rid, cur)]
            except KeyError:
                continue
            rows.append(dict(repo_id=rid, month_int=cur,
                             is_treated=int(m.is_treated), is_post=int(m.is_post),
                             introduced=introduced, removed=removed,
                             outstanding_prev=sum(a.values())))
    return pd.DataFrame(rows)


# ── State discretization + transition matrices ─────────────────────────────────

def assign_states(panel, n_states):
    vals = panel.axe_renderable_per_file.values
    qs = np.quantile(vals, np.linspace(0, 1, n_states + 1))
    qs[0], qs[-1] = -np.inf, np.inf
    qs = np.unique(qs)
    states = np.digitize(panel.axe_renderable_per_file.values, qs[1:-1])
    out = panel.copy()
    out["state"] = states
    return out, len(qs) - 1


def regime_sequences(df_states):
    """Yield (regime, list-of-state-sequences) where each sequence is one repo's
    contiguous monthly run within a single regime (pre or post)."""
    seqs = {"pre": [], "post": []}
    for rid, g in df_states.sort_values("month_int").groupby("repo_id"):
        g = g.reset_index(drop=True)
        for regime, sub in g.groupby("is_post"):
            sub = sub.sort_values("month_int")
            # split into runs of consecutive months
            mi = sub.month_int.values
            st = sub.state.values
            run = [st[0]]
            for k in range(1, len(mi)):
                if mi[k] - mi[k - 1] == 1:
                    run.append(st[k])
                else:
                    if len(run) >= 2:
                        seqs["post" if regime == 1 else "pre"].append(run)
                    run = [st[k]]
            if len(run) >= 2:
                seqs["post" if regime == 1 else "pre"].append(run)
    return seqs


def count_transitions(seqs, n):
    N = np.zeros((n, n))
    for s in seqs:
        for i, j in zip(s, s[1:]):
            N[i, j] += 1
    return N


def transition_matrix(N):
    row = N.sum(1, keepdims=True)
    P = np.divide(N, row, out=np.zeros_like(N), where=row > 0)
    return P


def stationary(P):
    w, v = eig(P.T)
    idx = np.argmin(np.abs(w - 1))
    pi = np.real(v[:, idx])
    pi = pi / pi.sum()
    return pi


def spectral_gap(P):
    w = np.sort(np.abs(eig(P)[0]))[::-1]
    lam2 = w[1] if len(w) > 1 else 0.0
    return 1 - lam2, lam2


def homogeneity_lr(Npre, Npost):
    """LR test H0: P^pre == P^post. Pooled vs separate multinomial rows."""
    Npool = Npre + Npost
    ll = 0.0
    for N in (Npre, Npost):
        P = transition_matrix(N)
        mask = N > 0
        ll += np.sum(N[mask] * np.log(P[mask]))
    Ppool = transition_matrix(Npool)
    ll0 = 0.0
    for N in (Npre, Npost):
        mask = (N > 0) & (Ppool > 0)
        ll0 += np.sum(N[mask] * np.log(Ppool[mask]))
    stat = 2 * (ll - ll0)
    # df from OCCUPIED support only: zero-inflation creates a phantom empty
    # state and sparse rows, so the textbook n*(n-1) over-counts free params.
    # Correct df = sum over "from" states present in BOTH matrices of
    # (number of reachable "to" columns - 1).
    Npool = Npre + Npost
    df = 0
    for i in range(Npool.shape[0]):
        if Npre[i].sum() > 0 and Npost[i].sum() > 0:
            reach = int(np.count_nonzero(Npool[i] > 0))
            df += max(reach - 1, 0)
    df = max(df, 1)
    p = stats.chi2.sf(stat, df)
    return stat, df, p


def markov_order_lr(seqs, n):
    """LR test H0: 1st-order vs H1: 2nd-order Markov (pooled within regime)."""
    N1 = count_transitions(seqs, n)
    P1 = transition_matrix(N1)
    N2 = {}                       # (i,j) -> count vector over k
    for s in seqs:
        for i, j, k in zip(s, s[1:], s[2:]):
            N2.setdefault((i, j), np.zeros(n))[k] += 1
    ll1 = ll2 = 0.0
    df = 0
    for (i, j), vec in N2.items():
        tot = vec.sum()
        if tot == 0:
            continue
        P2 = vec / tot
        # free params added by conditioning on i (beyond the 1st-order row j):
        # (#reachable k under this (i,j) lag-pair) - 1, but only where the
        # 1st-order row j also has support on those k.
        reach = int(np.count_nonzero(vec > 0))
        df += max(reach - 1, 0)
        for k in range(n):
            if vec[k] > 0:
                ll2 += vec[k] * np.log(P2[k])
                if P1[j, k] > 0:
                    ll1 += vec[k] * np.log(P1[j, k])
    stat = 2 * (ll2 - ll1)
    df = max(df, 1)
    p = stats.chi2.sf(stat, df)
    return stat, df, p


# ── Birth-death (monthly discrete-time) ────────────────────────────────────────

def birth_death_rates(deltas, regime_post):
    d = deltas[deltas.is_post == regime_post]
    months = len(d)
    intro = d.introduced.sum()
    rem = d.removed.sum()
    # λ and μ MUST share the same exposure (all repo-months) for ρ=λ/μ to be a
    # well-defined rate ratio. Conditioning μ on backlog>0 (as an earlier
    # version did) used a different denominator than λ and inflated μ unevenly
    # across regimes, manufacturing a spurious ρ crossover. Fixed.
    lam = intro / months                      # mean introduced / repo-month
    mu = rem / months                         # mean removed  / repo-month
    rho = lam / mu if mu > 0 else np.inf
    return dict(months=int(months), introduced=int(intro), removed=int(rem),
                lam=float(lam), mu=float(mu), rho=float(rho))


# ── Repo-level block bootstrap ────────────────────────────────────────────────

def block_bootstrap_rho(deltas):
    repos = deltas.repo_id.unique()
    diffs = []
    for _ in range(N_BOOT):
        samp = RNG.choice(repos, size=len(repos), replace=True)
        d = pd.concat([deltas[deltas.repo_id == r] for r in samp], ignore_index=True)
        try:
            rp = birth_death_rates(d, 0)["rho"]
            rq = birth_death_rates(d, 1)["rho"]
            if np.isfinite(rp) and np.isfinite(rq):
                diffs.append(rq - rp)
        except Exception:
            pass
    diffs = np.array(diffs)
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5)), float(np.mean(diffs))


def block_bootstrap_gap(df_states, n):
    repos = df_states.repo_id.unique()
    diffs = []
    for _ in range(N_BOOT):
        samp = RNG.choice(repos, size=len(repos), replace=True)
        d = pd.concat([df_states[df_states.repo_id == r] for r in samp], ignore_index=True)
        seqs = regime_sequences(d)
        try:
            gp = spectral_gap(transition_matrix(count_transitions(seqs["pre"], n)))[0]
            gq = spectral_gap(transition_matrix(count_transitions(seqs["post"], n)))[0]
            diffs.append(gq - gp)
        except Exception:
            pass
    diffs = np.array(diffs)
    return float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5)), float(np.mean(diffs))


# ── Volatility & tails ─────────────────────────────────────────────────────────

def volatility_tails(panel):
    """Volatility (Brown-Forsythe) + tail-exceedance DiD with repo-clustered SEs.

    The naive pooled is_post two-proportion z-test is INVALID here: (a) repo-
    months are not independent (strong within-repo clustering), and (b) is_post
    pools treated and control, so a control/secular trend confounds the contrast.
    We therefore (1) keep the variance test, and (2) test the tail with a proper
    DiD logit  tail ~ post*treated  with SEs clustered by repo. The DiD
    interaction is the AI-specific dynamic effect; cluster-robust inference
    handles the non-independence."""
    import statsmodels.formula.api as smf

    pre = panel[panel.is_post == 0].axe_renderable_per_file.values
    post = panel[panel.is_post == 1].axe_renderable_per_file.values
    lev = stats.levene(pre, post, center="median")        # Brown-Forsythe

    thr = float(np.quantile(panel.axe_renderable_per_file.values, 0.90))
    d = panel.dropna(subset=["axe_renderable_per_file"]).copy()
    d["tail"] = (d.axe_renderable_per_file > thr).astype(int)
    d["post"] = d.is_post.astype(int)
    d["treated"] = d.is_treated.astype(int)

    # Descriptive cell rates
    def rate(t, p):
        s = d[(d.treated == t) & (d.post == p)]
        return float(s["tail"].mean()), int(len(s))
    tr_pre, n_tr_pre = rate(1, 0); tr_post, n_tr_post = rate(1, 1)
    ct_pre, n_ct_pre = rate(0, 0); ct_post, n_ct_post = rate(0, 1)
    did_point = (tr_post - tr_pre) - (ct_post - ct_pre)

    # Naive (invalid) pooled z-test, retained ONLY to report the gap vs corrected
    n1, n2 = len(pre), len(post)
    x1, x2 = int((pre > thr).sum()), int((post > thr).sum())
    p_pre, p_post = x1 / n1, x2 / n2
    pbar = (x1 + x2) / (n1 + n2)
    se = np.sqrt(pbar * (1 - pbar) * (1 / n1 + 1 / n2))
    z_naive = (p_post - p_pre) / se if se > 0 else 0.0
    p_naive = 2 * stats.norm.sf(abs(z_naive))

    # Corrected: DiD logit with repo-clustered SEs
    cl = smf.logit("tail ~ post + treated + post:treated", data=d).fit(
        disp=0, cov_type="cluster",
        cov_kwds={"groups": d["repo_id"].values})
    idx = list(cl.model.exog_names).index("post:treated")
    coef = float(cl.params.iloc[idx])
    pval = float(cl.pvalues.iloc[idx])
    z_did = float(cl.tvalues.iloc[idx])

    return dict(var_pre=float(np.var(pre, ddof=1)), var_post=float(np.var(post, ddof=1)),
                levene_W=float(lev.statistic), levene_p=float(lev.pvalue),
                tail_thr=thr,
                tail_treated_pre=tr_pre, tail_treated_post=tr_post,
                tail_control_pre=ct_pre, tail_control_post=ct_post,
                tail_did_point=float(did_point),
                tail_did_logit_coef=coef, tail_did_z=z_did, tail_did_p=pval,
                tail_naive_z=float(z_naive), tail_naive_p=float(p_naive),
                n_treated_pre=n_tr_pre, n_treated_post=n_tr_post,
                n_control_pre=n_ct_pre, n_control_post=n_ct_post)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", nargs="?", const=DB_PATH, default=None,
                    help="Read the full SQLite DB (default: repos.db) instead of "
                         "the trimmed data/ CSVs. repos.db is archived on Zenodo.")
    ap.add_argument("--data-dir", default=str(DATA_DIR),
                    help="Directory holding the trimmed CSVs (default: data/).")
    args = ap.parse_args()
    src = Source(db_path=args.db, data_dir=args.data_dir)
    print(f"[source] {'repos.db: ' + args.db if args.db else 'trimmed CSVs in ' + args.data_dir}")

    panel = build_panel(src)
    print(f"[panel] {panel.repo_id.nunique()} repos, {len(panel)} repo-months "
          f"({panel[panel.is_treated==1].repo_id.nunique()} treated / "
          f"{panel[panel.is_treated==0].repo_id.nunique()} control)")

    results = {"panel": {"n_repos": int(panel.repo_id.nunique()),
                         "n_obs": int(len(panel)),
                         "n_treated": int(panel[panel.is_treated == 1].repo_id.nunique()),
                         "n_control": int(panel[panel.is_treated == 0].repo_id.nunique())}}

    # Markov over 3/4/5 states
    results["markov"] = {}
    for n_req in (3, 4, 5):
        ds, n = assign_states(panel, n_req)
        seqs = regime_sequences(ds)
        Npre = count_transitions(seqs["pre"], n)
        Npost = count_transitions(seqs["post"], n)
        Ppre, Ppost = transition_matrix(Npre), transition_matrix(Npost)
        pi_pre, pi_post = stationary(Ppre), stationary(Ppost)
        gap_pre, l2_pre = spectral_gap(Ppre)
        gap_post, l2_post = spectral_gap(Ppost)
        hom = homogeneity_lr(Npre, Npost)
        order_pre = markov_order_lr(seqs["pre"], n)
        order_post = markov_order_lr(seqs["post"], n)
        gci = block_bootstrap_gap(ds, n) if n_req == 4 else None
        key = f"req{n_req}_eff{n}"   # avoid n=5->4 degeneracy overwriting n=4
        results["markov"][key] = dict(
            n_requested=n_req, n_states=n,
            P_pre=Ppre.round(4).tolist(), P_post=Ppost.round(4).tolist(),
            diag_pre=np.diag(Ppre).round(4).tolist(),
            diag_post=np.diag(Ppost).round(4).tolist(),
            dwell_pre=(1 / (1 - np.diag(Ppre))).round(3).tolist(),
            dwell_post=(1 / (1 - np.diag(Ppost))).round(3).tolist(),
            pi_pre=pi_pre.round(4).tolist(), pi_post=pi_post.round(4).tolist(),
            spectral_gap_pre=round(float(gap_pre), 4),
            spectral_gap_post=round(float(gap_post), 4),
            lambda2_pre=round(float(l2_pre), 4), lambda2_post=round(float(l2_post), 4),
            homogeneity_LR=round(float(hom[0]), 3), homogeneity_df=int(hom[1]),
            homogeneity_p=float(hom[2]),
            order_LR_pre=round(float(order_pre[0]), 3), order_p_pre=float(order_pre[2]),
            order_LR_post=round(float(order_post[0]), 3), order_p_post=float(order_post[2]),
            gap_diff_ci=gci,
            n_trans_pre=int(Npre.sum()), n_trans_post=int(Npost.sum()),
        )
        print(f"\n[markov req={n_req} eff_n={n}] homogeneity LR={hom[0]:.2f} df={hom[1]} p={hom[2]:.4f} | "
              f"gap_pre={gap_pre:.4f} gap_post={gap_post:.4f}")
        print(f"  diag_pre ={np.diag(Ppre).round(3).tolist()}")
        print(f"  diag_post={np.diag(Ppost).round(3).tolist()}")
        print(f"  order LR pre p={order_pre[2]:.4f} post p={order_post[2]:.4f}")
        if gci:
            print(f"  gap_diff(post-pre) 95% CI=[{gci[0]:.4f},{gci[1]:.4f}] mean={gci[2]:.4f}")

    # Birth-death
    deltas = compute_deltas(src, panel)
    deltas.to_csv(OUT / "deltas.csv", index=False)
    bd_pre = birth_death_rates(deltas, 0)
    bd_post = birth_death_rates(deltas, 1)
    rho_ci = block_bootstrap_rho(deltas)
    results["birth_death"] = dict(pre=bd_pre, post=bd_post,
                                  rho_diff_ci=rho_ci,
                                  n_repo_months=int(len(deltas)))
    print(f"\n[birth-death] PRE  lam={bd_pre['lam']:.4f} mu={bd_pre['mu']:.4f} rho={bd_pre['rho']:.4f}")
    print(f"[birth-death] POST lam={bd_post['lam']:.4f} mu={bd_post['mu']:.4f} rho={bd_post['rho']:.4f}")
    print(f"[birth-death] rho_diff(post-pre) 95% CI=[{rho_ci[0]:.4f},{rho_ci[1]:.4f}] mean={rho_ci[2]:.4f}")

    # Volatility & tails
    vt = volatility_tails(panel)
    results["volatility_tails"] = vt
    print(f"\n[volatility] var_pre={vt['var_pre']:.5f} var_post={vt['var_post']:.5f} "
          f"Levene W={vt['levene_W']:.3f} p={vt['levene_p']:.4f}")
    print(f"[tail rates] treated {vt['tail_treated_pre']:.4f}->{vt['tail_treated_post']:.4f} | "
          f"control {vt['tail_control_pre']:.4f}->{vt['tail_control_post']:.4f}")
    print(f"[tail NAIVE pooled z] z={vt['tail_naive_z']:.3f} p={vt['tail_naive_p']:.4f}  (INVALID: clustered+confounded)")
    print(f"[tail DiD logit, repo-clustered] interaction coef={vt['tail_did_logit_coef']:.3f} "
          f"z={vt['tail_did_z']:.3f} p={vt['tail_did_p']:.4f}  DiD_point={vt['tail_did_point']:.4f}")

    # Negative control: stylistic metric (monthly growth in component_count),
    # which has no a-priori reason to shift dynamics with AI adoption.
    cc = panel.copy()
    cc["cc_state"] = pd.qcut(cc.component_count.rank(method="first"), 4,
                             labels=False).astype(int)
    seqs = regime_sequences(cc.rename(columns={"cc_state": "state"}))
    Npre = count_transitions(seqs["pre"], 4)
    Npost = count_transitions(seqs["post"], 4)
    hom = homogeneity_lr(Npre, Npost)
    results["negative_control"] = dict(homogeneity_LR=round(float(hom[0]), 3),
                                       homogeneity_df=int(hom[1]),
                                       homogeneity_p=float(hom[2]))
    print(f"\n[neg-control component_count] homogeneity LR={hom[0]:.2f} p={hom[2]:.4f}")

    (OUT / "dynamics_results.json").write_text(json.dumps(results, indent=2))
    print(f"\n[done] wrote {OUT/'dynamics_results.json'} and {OUT/'deltas.csv'}")


if __name__ == "__main__":
    main()
