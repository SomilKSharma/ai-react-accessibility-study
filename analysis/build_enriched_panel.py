"""
Re-match controls to treated and build the enriched 5-axis repo-month panel
for the scaled study (497 repos: 193 treated, 304 control candidates).

Steps:
  1. Propensity score via logistic regression (pure numpy) on
     history_months, tsx_file_count, contributor_count (log-scaled).
  2. 1:1 nearest-neighbour matching with caliper on the PS logit.
  3. Each matched control inherits its treated pair's treatment_date (placebo),
     so it gets a pre/post split aligned to real adoption timing.
  4. Build repo-month panel: aggregate ast_results to repo-month for all axes,
     compute is_post, merge post-period activity covariates, apply inclusion gate.

Outputs:
  enriched_panel.csv        — the analysis panel
  enriched_matches.csv      — treated/control pairs + PS balance
Pure numpy/pandas. Deterministic (fixed seed).
"""
import os
import sqlite3
import numpy as np
import pandas as pd

# Paths resolve relative to the repo. repos.db (large; archived on Zenodo) is
# expected at the repo root; override with the REPOS_DB env var if elsewhere.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_ROOT, "data")
DB = os.environ.get("REPOS_DB", os.path.join(_ROOT, "repos.db"))
OUT_PANEL = os.path.join(_DATA, "enriched_panel.csv")
OUT_FULL = os.path.join(_DATA, "enriched_panel_full.csv")
OUT_MATCH = os.path.join(_DATA, "enriched_matches.csv")
SEED = 20260629
CALIPER = 0.20         # on PS logit SD units (slightly looser than 0.10 given 3 covariates)
MIN_MONTHS = 12
MIN_ROWS = 100

COVARS = ["history_months", "tsx_file_count", "contributor_count"]


def month_to_int(s):
    y, m = map(int, str(s).split("-")[:2])
    return (y - 2020) * 12 + (m - 1)


def logit_ps(X, y, iters=500, lr=0.1):
    """Logistic regression via gradient descent; returns fitted P(treated)."""
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-9)
    Xs = np.hstack([np.ones((len(Xs), 1)), Xs])
    w = np.zeros(Xs.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(Xs @ w)))
        w -= lr * (Xs.T @ (p - y)) / len(y)
    return 1 / (1 + np.exp(-(Xs @ w)))


def std_diff(t, c):
    sp = np.sqrt((t.var() + c.var()) / 2) + 1e-12
    return (t.mean() - c.mean()) / sp


def main():
    rng = np.random.default_rng(SEED)
    conn = sqlite3.connect(DB)

    enr = pd.read_sql_query(
        "SELECT DISTINCT repo_id FROM ast_results WHERE wcag_total IS NOT NULL", conn)
    q = pd.read_sql_query(
        "SELECT repo_id, full_name, status, treatment_date, treatment_tier, "
        "history_months, tsx_file_count, contributor_count FROM repo_qualification", conn)
    d = enr.merge(q, on="repo_id", how="left").dropna(subset=COVARS)
    d["is_treated"] = (d.status == "treated").astype(int)
    treated = d[d.is_treated == 1].copy()
    control = d[d.is_treated == 0].copy()
    print(f"enriched repos: {len(d)} | treated {len(treated)} | control {len(control)}")

    # propensity score (log-scale the skewed covariates)
    Xfull = d[COVARS].copy()
    for c0 in COVARS:
        Xfull[c0] = np.log1p(Xfull[c0])
    d["ps"] = logit_ps(Xfull.to_numpy(float), d.is_treated.to_numpy(float))
    d["ps_logit"] = np.log(d.ps / (1 - d.ps + 1e-12) + 1e-12)
    treated = d[d.is_treated == 1].copy()
    control = d[d.is_treated == 0].copy()
    caliper = CALIPER * d.ps_logit.std()

    # 1:1 nearest-neighbour without replacement on PS logit, within caliper
    ctrl_avail = control.set_index("repo_id")["ps_logit"].to_dict()
    pairs = []
    used = set()
    for _, t in treated.sort_values("ps_logit").iterrows():
        best, bestd = None, np.inf
        for cid, cps in ctrl_avail.items():
            if cid in used:
                continue
            dd = abs(t.ps_logit - cps)
            if dd < bestd:
                best, bestd = cid, dd
        if best is not None and bestd <= caliper:
            used.add(best)
            pairs.append((t.repo_id, best, t.treatment_date, t.treatment_tier))
    pairs_df = pd.DataFrame(pairs, columns=["treated_repo_id", "control_repo_id",
                                            "treatment_date", "treated_tier"])
    print(f"matched pairs: {len(pairs_df)} (caliper={caliper:.3f} on PS logit)")

    # balance before/after
    matched_t = treated[treated.repo_id.isin(pairs_df.treated_repo_id)]
    matched_c = control[control.repo_id.isin(pairs_df.control_repo_id)]
    print("\nPSM balance (std diff):")
    print(f"{'covariate':18} {'pre':>8} {'post':>8}")
    for c0 in COVARS:
        pre = std_diff(np.log1p(treated[c0]), np.log1p(control[c0]))
        post = std_diff(np.log1p(matched_t[c0]), np.log1p(matched_c[c0]))
        print(f"{c0:18} {pre:>8.3f} {post:>8.3f}")
    pairs_df.to_csv(OUT_MATCH, index=False)

    # ── build the matched repo set with placebo dates for controls ────────────
    keep_treated = set(pairs_df.treated_repo_id)
    ctrl_date = dict(zip(pairs_df.control_repo_id, pairs_df.treatment_date))
    keep_control = set(pairs_df.control_repo_id)

    repo_meta = {}
    for _, r in treated.iterrows():
        if r.repo_id in keep_treated:
            repo_meta[r.repo_id] = (1, r.treatment_date, r.full_name, int(r.treatment_tier or 0),
                                    r.history_months, r.tsx_file_count, r.contributor_count)
    for _, r in control.iterrows():
        if r.repo_id in keep_control:
            repo_meta[r.repo_id] = (0, ctrl_date[r.repo_id], r.full_name, 0,
                                    r.history_months, r.tsx_file_count, r.contributor_count)

    # ── aggregate ast_results to repo-month across all 5 axes ─────────────────
    ids = tuple(repo_meta.keys())
    ast = pd.read_sql_query(
        f"SELECT repo_id, snapshot_month, "
        f"COUNT(*) n_components, "
        f"AVG(semantic_score) semantic_score, "
        f"AVG(aria_score) aria_score, "
        f"AVG(keyboard_score) keyboard_score, "
        f"SUM(wcag_perceivable)*1.0/SUM(total_elements) wcag_perceivable_dens, "
        f"SUM(wcag_operable)*1.0/SUM(total_elements) wcag_operable_dens, "
        f"SUM(wcag_understandable)*1.0/SUM(total_elements) wcag_understandable_dens, "
        f"SUM(wcag_robust)*1.0/SUM(total_elements) wcag_robust_dens, "
        f"SUM(wcag_total)*1.0/SUM(total_elements) wcag_total_dens, "
        f"SUM(severity_weighted)*1.0/SUM(total_elements) severity_weighted_dens, "
        f"SUM(total_elements) total_elements "
        f"FROM ast_results WHERE wcag_total IS NOT NULL AND repo_id IN {ids} "
        f"GROUP BY repo_id, snapshot_month", conn)
    print(f"\nrepo-month rows (pre-gate): {len(ast)}")

    # attach meta, compute is_post
    ast["is_treated"] = ast.repo_id.map(lambda r: repo_meta[r][0])
    ast["treatment_date"] = ast.repo_id.map(lambda r: repo_meta[r][1])
    ast["full_name"] = ast.repo_id.map(lambda r: repo_meta[r][2])
    ast["treated_tier"] = ast.repo_id.map(lambda r: repo_meta[r][3])
    ast["history_months"] = ast.repo_id.map(lambda r: repo_meta[r][4])
    ast["tsx_file_count"] = ast.repo_id.map(lambda r: repo_meta[r][5])
    ast["contributor_count"] = ast.repo_id.map(lambda r: repo_meta[r][6])
    ast["month_int"] = ast.snapshot_month.map(month_to_int)
    ast["t_month_int"] = ast.treatment_date.map(lambda s: month_to_int(s) if s else np.nan)
    ast = ast.dropna(subset=["t_month_int"])
    ast["is_post"] = (ast.month_int >= ast.t_month_int).astype(int)
    ast["rel_month"] = ast.month_int - ast.t_month_int

    # inclusion gate: >=12 months AND >=100 component-rows total
    cov = ast.groupby("repo_id").agg(m=("snapshot_month", "nunique"),
                                     rows=("n_components", "sum")).reset_index()
    keep = set(cov[(cov.m >= MIN_MONTHS) & (cov.rows >= MIN_ROWS)].repo_id)
    panel = ast[ast.repo_id.isin(keep)].copy()

    # merge post-period activity covariate
    act = pd.read_sql_query("SELECT repo_id, commits post_commits, distinct_authors post_authors, "
                            "span_days post_span FROM repo_activity WHERE window='post'", conn)
    panel = panel.merge(act, on="repo_id", how="left")

    nt = panel[panel.is_treated == 1].repo_id.nunique()
    nc = panel[panel.is_treated == 0].repo_id.nunique()
    print(f"\nFINAL ENRICHED PANEL: {panel.repo_id.nunique()} repos "
          f"({nt} treated / {nc} control), {len(panel)} repo-months")
    print(f"  Tier-1 treated (robustness subset): "
          f"{panel[(panel.is_treated==1)&(panel.treated_tier==1)].repo_id.nunique()}")
    panel.to_csv(OUT_PANEL, index=False)
    print(f"saved -> {OUT_PANEL}")

    # ── FULL unmatched panel (193 treated + 304 control) for TWFE robustness ──
    # Controls get a placebo treatment_date sampled from the treated date
    # distribution so the pre/post split is non-degenerate; repo+month FE absorb
    # the arm-level differences that matching otherwise handles.
    treated_dates = treated.treatment_date.dropna().tolist()
    meta_full = {}
    for _, r in treated.iterrows():
        meta_full[r.repo_id] = (1, r.treatment_date, r.full_name, int(r.treatment_tier or 0))
    for _, r in control.iterrows():
        meta_full[r.repo_id] = (0, rng.choice(treated_dates), r.full_name, 0)
    idsf = tuple(meta_full.keys())
    astf = pd.read_sql_query(
        f"SELECT repo_id, snapshot_month, COUNT(*) n_components, "
        f"AVG(semantic_score) semantic_score, AVG(aria_score) aria_score, "
        f"AVG(keyboard_score) keyboard_score, "
        f"SUM(wcag_total)*1.0/SUM(total_elements) wcag_total_dens, "
        f"SUM(wcag_operable)*1.0/SUM(total_elements) wcag_operable_dens, "
        f"SUM(severity_weighted)*1.0/SUM(total_elements) severity_weighted_dens, "
        f"SUM(total_elements) total_elements "
        f"FROM ast_results WHERE wcag_total IS NOT NULL AND repo_id IN {idsf} "
        f"GROUP BY repo_id, snapshot_month", conn)
    astf["is_treated"] = astf.repo_id.map(lambda r: meta_full[r][0])
    astf["treatment_date"] = astf.repo_id.map(lambda r: meta_full[r][1])
    astf["full_name"] = astf.repo_id.map(lambda r: meta_full[r][2])
    astf["treated_tier"] = astf.repo_id.map(lambda r: meta_full[r][3])
    astf["month_int"] = astf.snapshot_month.map(month_to_int)
    astf["t_month_int"] = astf.treatment_date.map(lambda s: month_to_int(s) if s else np.nan)
    astf = astf.dropna(subset=["t_month_int"])
    astf["is_post"] = (astf.month_int >= astf.t_month_int).astype(int)
    astf["rel_month"] = astf.month_int - astf.t_month_int
    covf = astf.groupby("repo_id").agg(m=("snapshot_month", "nunique"),
                                       rows=("n_components", "sum")).reset_index()
    keepf = set(covf[(covf.m >= MIN_MONTHS) & (covf.rows >= MIN_ROWS)].repo_id)
    full = astf[astf.repo_id.isin(keepf)].copy()
    full.to_csv(OUT_FULL, index=False)
    print(f"\nFULL panel: {full.repo_id.nunique()} repos "
          f"({full[full.is_treated==1].repo_id.nunique()} treated / "
          f"{full[full.is_treated==0].repo_id.nunique()} control), {len(full)} repo-months")
    print(f"saved -> {OUT_FULL}")
    conn.close()


if __name__ == "__main__":
    main()
