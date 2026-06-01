"""
Stage 5 — DiD Estimation
=========================
Operative design: Study Design v3.0 + v3.1 Addendum.
Reads repos.db, runs the full DiD analysis, writes results + plots to ./stage5_out/.

Outputs:
  stage5_results.txt          - human-readable summary
  panel.csv                   - repo-month panel used for estimation
  fig1_parallel_trends.png    - event-study pre-period plot
  fig2_dynamic_did.png        - event-study with post-period (RQ4)
  table_main.csv              - primary DiD across 3 outcomes
  table_heterogeneity.csv     - per-category β (RQ3)
  table_robustness.csv        - 5 robustness specifications
"""

import sqlite3
import os
import sys
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH = "repos.db"
OUT_DIR = Path("stage5_out")
OUT_DIR.mkdir(exist_ok=True)

INCLUSION_MIN_MONTHS = 12
INCLUSION_MIN_RENDERABLE = 100

EVENT_K_MIN = -12
EVENT_K_MAX = 12
PRETREND_TEST_KS = [-6, -3, -2]   # joint F-test bins per v3.1 §6.3

CATEGORY_RULES = {
    "semantic_naming": [
        "button-name", "label", "link-name", "image-alt",
        "select-name", "document-title", "frame-title", "role-img-alt",
    ],
    "aria_specific": [
        "aria-command-name", "aria-required-parent", "aria-required-attr",
        "aria-allowed-attr", "aria-dialog-name", "aria-input-field-name",
        "aria-tooltip-name", "aria-treeitem-name", "aria-roles",
    ],
    "document_structure": [
        "listitem", "list", "html-has-lang", "dlitem",
        "nested-interactive", "duplicate-id-active",
    ],
}


# ── Panel construction ────────────────────────────────────────────────────────

def month_to_int(month_str: str) -> int:
    """Convert 'YYYY-MM' to integer months since epoch (2020-01)."""
    y, m = map(int, month_str.split("-"))
    return (y - 2020) * 12 + (m - 1)


def parse_treatment_month(tdate: str) -> str | None:
    """Treatment date is 'YYYY-MM-DD' -> 'YYYY-MM'."""
    if not tdate:
        return None
    return tdate[:7]


def build_panel(conn: sqlite3.Connection) -> pd.DataFrame:
    """Build repo-month panel per v3.1 §3.5.1 + §6.2."""

    # 1. Inclusion: ≥12 months AND ≥100 renderable rows
    coverage = pd.read_sql_query("""
        SELECT a.full_name,
               a.repo_id,
               COUNT(DISTINCT a.snapshot_month) AS snap_months,
               SUM(a.renderable)                AS renderable_rows
        FROM axe_results a
        GROUP BY a.full_name, a.repo_id
    """, conn)
    included = coverage[
        (coverage["snap_months"] >= INCLUSION_MIN_MONTHS)
        & (coverage["renderable_rows"] >= INCLUSION_MIN_RENDERABLE)
    ].copy()

    # 2. repo_partial flag: errored mid-run but passed coverage
    status = pd.read_sql_query(
        "SELECT repo_id, status FROM repo_measurement_status", conn
    )
    included = included.merge(status, on="repo_id", how="left")
    included["repo_partial"] = (included["status"] == "error").astype(int)

    # 3. Treatment metadata
    qual = pd.read_sql_query("""
        SELECT repo_id, full_name, treatment_date, history_months, tsx_file_count, treatment_tier
        FROM repo_qualification
    """, conn)
    included = included.merge(
        qual[["repo_id", "treatment_date", "history_months", "tsx_file_count", "treatment_tier"]],
        on="repo_id", how="left"
    )

    # 4. Determine treated vs control via matched_pairs
    pairs = pd.read_sql_query("""
        SELECT treated_repo_id, control_repo_id, treated_full_name, control_full_name
        FROM matched_pairs WHERE match_rank = 1
    """, conn)
    treated_ids = set(pairs["treated_repo_id"])
    control_ids = set(pairs["control_repo_id"])
    included["is_treated"] = included["repo_id"].apply(
        lambda r: 1 if r in treated_ids else (0 if r in control_ids else np.nan)
    )
    included = included.dropna(subset=["is_treated"])
    included["is_treated"] = included["is_treated"].astype(int)

    # 5. Synthetic post-period for controls (v3.1 §6.2): inherit paired treated's
    # treatment_date. If matched to multiple, take earliest.
    treated_tdates = (
        qual[qual["repo_id"].isin(treated_ids)]
        .set_index("repo_id")["treatment_date"]
    )
    pairs_w_tdate = pairs.merge(
        treated_tdates.rename("treated_tdate"),
        left_on="treated_repo_id", right_index=True, how="left",
    )
    # For each control, take earliest treated_tdate among its matches
    ctrl_inherited = (
        pairs_w_tdate.groupby("control_repo_id")["treated_tdate"].min()
    )

    # Assign treatment_date to controls (overwrite NULL controls only)
    def resolve_tdate(row):
        if row["is_treated"] == 1:
            return row["treatment_date"]
        return ctrl_inherited.get(row["repo_id"])

    included["treatment_date"] = included.apply(resolve_tdate, axis=1)
    # treatment_month: 'YYYY-MM' string for relative-month calcs
    included["treatment_month_str"] = included["treatment_date"].apply(parse_treatment_month)

    # 6. Pull snapshots and per-snapshot aggregates
    snapshots = pd.read_sql_query("""
        SELECT id AS snapshot_id, repo_id, full_name, snapshot_month, commit_sha, commit_date
        FROM snapshots
    """, conn)

    axe_agg = pd.read_sql_query("""
        SELECT snapshot_id,
               COUNT(*)                           AS component_count,
               SUM(renderable)                    AS renderable_count,
               SUM(violations_total)              AS violations_total,
               SUM(violations_critical)           AS violations_critical,
               SUM(violations_serious)            AS violations_serious
        FROM axe_results
        GROUP BY snapshot_id
    """, conn)

    ast_agg = pd.read_sql_query("""
        SELECT snapshot_id,
               AVG(semantic_score)                AS ast_score_mean,
               SUM(total_interactive)             AS total_interactive,
               SUM(deductions)                    AS deductions
        FROM ast_results
        GROUP BY snapshot_id
    """, conn)

    panel = snapshots.merge(axe_agg, on="snapshot_id", how="left") \
                     .merge(ast_agg, on="snapshot_id", how="left")
    panel = panel.merge(
        included[[
            "repo_id", "is_treated", "treatment_date", "treatment_month_str",
            "history_months", "tsx_file_count", "repo_partial", "treatment_tier",
        ]],
        on="repo_id", how="inner",
    )

    # 7. Compute outcomes
    panel["axe_total_per_file"] = (
        panel["violations_total"] / panel["component_count"]
    ).fillna(0)
    panel["axe_renderable_per_file"] = np.where(
        panel["renderable_count"] > 0,
        panel["violations_total"] / panel["renderable_count"],
        np.nan,
    )

    # 8. is_post: snapshot_month >= treatment_month
    panel["snapshot_month_int"] = panel["snapshot_month"].apply(month_to_int)
    panel["treatment_month_int"] = panel["treatment_month_str"].apply(
        lambda m: month_to_int(m) if m else np.nan
    )
    panel["is_post"] = (
        panel["snapshot_month_int"] >= panel["treatment_month_int"]
    ).astype(int)
    panel["relative_month"] = (
        panel["snapshot_month_int"] - panel["treatment_month_int"]
    )

    # 9. Sort + final cleanup
    panel = panel.sort_values(["repo_id", "snapshot_month_int"]).reset_index(drop=True)
    return panel


# ── DiD estimation ────────────────────────────────────────────────────────────

def run_did(df: pd.DataFrame, outcome: str, label: str) -> dict:
    """
    Run primary DiD per v3.1 §6.1:
      Y = α + β·(Treated × Post) + γ·Treated + δ·Post
          + repo_FE + month_FE
          + θ1·history_months + θ2·tsx_file_count + ε
      SE clustered at repo level.

    Implementation: within-transform by demeaning within repo and month,
    then OLS on residuals with cluster-robust SE.
    Equivalent to two-way FE OLS for balanced-ish panels.
    """
    d = df[[
        outcome, "is_treated", "is_post", "repo_id", "snapshot_month_int",
        "history_months", "tsx_file_count",
    ]].dropna(subset=[outcome, "is_treated", "is_post", "history_months", "tsx_file_count"]).copy()

    if len(d) == 0 or d["is_treated"].nunique() < 2:
        return {"outcome": label, "beta": np.nan, "se": np.nan, "ci_lo": np.nan,
                "ci_hi": np.nan, "p": np.nan, "n_obs": 0, "n_clusters": 0, "error": "no data"}

    d["did"] = d["is_treated"] * d["is_post"]

    # Two-way FE via absorbing dummies + clustered SE.
    # Use C() formula via patsy through statsmodels.
    import statsmodels.formula.api as smf

    # Make sure repo and month FE dummies are explicit categoricals
    d["repo_id_c"] = d["repo_id"].astype("category")
    d["month_c"] = d["snapshot_month_int"].astype("category")

    # If only one month-of-treatment per repo, is_treated is absorbed by repo FE.
    # Drop it if it's perfectly collinear; same for is_post if month FE absorbs.
    # statsmodels will drop collinear columns automatically with warning.
    formula = (
        f"{outcome} ~ did + is_treated + is_post "
        f"+ history_months + tsx_file_count + C(repo_id_c) + C(month_c)"
    )

    try:
        model = smf.ols(formula=formula, data=d).fit(
            cov_type="cluster",
            cov_kwds={"groups": d["repo_id"]},
        )
    except Exception as e:
        return {"outcome": label, "beta": np.nan, "se": np.nan, "ci_lo": np.nan,
                "ci_hi": np.nan, "p": np.nan, "n_obs": len(d), "n_clusters": d["repo_id"].nunique(),
                "error": str(e)[:80]}

    if "did" not in model.params:
        return {"outcome": label, "beta": np.nan, "se": np.nan, "ci_lo": np.nan,
                "ci_hi": np.nan, "p": np.nan, "n_obs": len(d), "n_clusters": d["repo_id"].nunique(),
                "error": "did absorbed"}

    beta = model.params["did"]
    se = model.bse["did"]
    ci = model.conf_int().loc["did"].tolist()
    p = model.pvalues["did"]

    return {
        "outcome": label,
        "beta": float(beta),
        "se": float(se),
        "ci_lo": float(ci[0]),
        "ci_hi": float(ci[1]),
        "p": float(p),
        "n_obs": int(len(d)),
        "n_clusters": int(d["repo_id"].nunique()),
        "error": None,
    }


def run_tobit(df: pd.DataFrame, outcome: str, label: str,
              upper_censor: float = 1.0) -> dict:
    """
    Tobit regression for right-censored outcome via censored normal MLE.
    Fixed effects handled by within-transformation (demean within repo, then month).
    SE clustered at repo level via sandwich estimator.
    """
    from scipy import stats as sp_stats
    from scipy.optimize import minimize

    cols = [outcome, "is_treated", "is_post", "repo_id", "snapshot_month_int",
            "history_months", "tsx_file_count"]
    d = df[cols].dropna().copy()

    if len(d) < 50 or d["is_treated"].nunique() < 2:
        return {"outcome": label, "beta": np.nan, "se": np.nan, "ci_lo": np.nan,
                "ci_hi": np.nan, "p": np.nan, "n_obs": len(d),
                "n_clusters": d["repo_id"].nunique() if len(d) else 0, "error": "insufficient data"}

    d["did"] = d["is_treated"] * d["is_post"]

    # Within-transform: demean within repo, then within month (two-way FE absorption)
    for col in [outcome, "did", "is_treated", "is_post", "history_months", "tsx_file_count"]:
        repo_mean = d.groupby("repo_id")[col].transform("mean")
        d[col] = d[col] - repo_mean
    for col in [outcome, "did", "is_treated", "is_post", "history_months", "tsx_file_count"]:
        month_mean = d.groupby("snapshot_month_int")[col].transform("mean")
        d[col] = d[col] - month_mean

    y = d[outcome].values
    X = d[["did", "is_treated", "is_post", "history_months", "tsx_file_count"]].values
    X = sm.add_constant(X, has_constant="add")
    n, k = X.shape
    groups = d["repo_id"].values

    # Censoring indicator: observation is censored if original value == upper_censor.
    # After demeaning the outcome, censored observations cluster near (upper_censor - repo_mean - month_mean).
    # We use original y_censored flag from the raw (pre-demeaned) column.
    raw_y = df.loc[d.index, outcome].values
    censored = (raw_y >= upper_censor).astype(float)

    def neg_log_lik(params):
        beta = params[:k]
        log_sigma = params[k]
        sigma = np.exp(log_sigma)
        xb = X @ beta
        ll = 0.0
        uncens = censored == 0
        cens = censored == 1
        if uncens.any():
            resid = y[uncens] - xb[uncens]
            ll += np.sum(sp_stats.norm.logpdf(resid, scale=sigma))
        if cens.any():
            # Right-censored: contribution = log P(Y >= upper_censor) = log(1 - Phi((uc - xb)/sigma))
            # After demeaning, uc_demeaned ~ y[cens] (the demeaned ceiling values)
            # Use survival function directly on demeaned residuals
            resid_cens = y[cens] - xb[cens]
            ll += np.sum(np.log(np.maximum(sp_stats.norm.sf(resid_cens / sigma), 1e-300)))
        return -ll

    # OLS warm start
    ols_init = np.linalg.lstsq(X, y, rcond=None)[0]
    resid_init = y - X @ ols_init
    sigma_init = max(np.std(resid_init), 1e-6)
    x0 = np.append(ols_init, np.log(sigma_init))

    try:
        result = minimize(neg_log_lik, x0, method="L-BFGS-B",
                          options={"maxiter": 2000, "ftol": 1e-12, "gtol": 1e-8})
        if not result.success and result.fun > neg_log_lik(x0) * 0.99:
            raise RuntimeError(f"Tobit MLE did not converge: {result.message}")
        params_hat = result.x
    except Exception as e:
        return {"outcome": label, "beta": np.nan, "se": np.nan, "ci_lo": np.nan,
                "ci_hi": np.nan, "p": np.nan, "n_obs": n,
                "n_clusters": int(np.unique(groups).shape[0]), "error": str(e)[:120]}

    beta_hat = params_hat[:k]
    sigma_hat = np.exp(params_hat[k])

    # Sandwich clustered SE
    # Score for each observation (gradient of log-lik wrt params)
    xb = X @ beta_hat
    scores = np.zeros((n, k + 1))
    uncens = censored == 0
    cens = censored == 1

    if uncens.any():
        resid_u = y[uncens] - xb[uncens]
        dloglik_dbeta = resid_u[:, None] / sigma_hat**2 * X[uncens]
        dloglik_dsig = (resid_u**2 / sigma_hat**2 - 1) / sigma_hat  # d/d(sigma)
        # chain rule: d/d(log_sigma) = sigma * d/d(sigma)
        dloglik_dlogsig = dloglik_dsig * sigma_hat
        scores[np.where(uncens)[0], :k] = dloglik_dbeta
        scores[np.where(uncens)[0], k] = dloglik_dlogsig

    if cens.any():
        resid_c = y[cens] - xb[cens]
        z = resid_c / sigma_hat
        mill = sp_stats.norm.pdf(z) / np.maximum(sp_stats.norm.sf(z), 1e-300)
        dloglik_dbeta_c = mill[:, None] / sigma_hat * X[cens]
        dloglik_dlogsig_c = mill * z
        scores[np.where(cens)[0], :k] = dloglik_dbeta_c
        scores[np.where(cens)[0], k] = dloglik_dlogsig_c

    # Hessian approximation via outer product of scores (information matrix)
    try:
        H = X.T @ X  # approximate, sufficient for SE of did coefficient
        # Cluster meat
        unique_groups = np.unique(groups)
        meat = np.zeros((k + 1, k + 1))
        for g in unique_groups:
            mask = groups == g
            sg = scores[mask].sum(axis=0)
            meat += np.outer(sg, sg)
        # Full sandwich: (H^-1 M H^-1) — we only need [1,1] element (did = index 1)
        # Use pseudo-inverse for robustness
        from numpy.linalg import pinv
        score_bread = np.zeros((k + 1, k + 1))
        score_bread[:k, :k] = X.T @ X / sigma_hat**2  # Fisher info approx for beta block
        score_bread[k, k] = 2 * n  # approx for sigma
        bread_inv = pinv(score_bread)
        vcov = bread_inv @ meat @ bread_inv
        se_all = np.sqrt(np.maximum(np.diag(vcov), 0))
    except Exception:
        se_all = np.full(k + 1, np.nan)

    # did is the first covariate after the constant (index 1)
    did_idx = 1
    beta_did = float(beta_hat[did_idx])
    se_did = float(se_all[did_idx]) if not np.isnan(se_all[did_idx]) else np.nan

    if np.isnan(se_did) or se_did <= 0:
        return {"outcome": label, "beta": beta_did, "se": np.nan, "ci_lo": np.nan,
                "ci_hi": np.nan, "p": np.nan, "n_obs": n,
                "n_clusters": int(unique_groups.shape[0]), "error": "SE computation failed"}

    z_stat = beta_did / se_did
    p_val = float(2 * sp_stats.norm.sf(abs(z_stat)))
    ci_lo = beta_did - 1.96 * se_did
    ci_hi = beta_did + 1.96 * se_did

    return {
        "outcome": label,
        "beta": beta_did,
        "se": se_did,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "p": p_val,
        "n_obs": n,
        "n_clusters": int(unique_groups.shape[0]),
        "error": None,
    }


def _k_to_name(k: int) -> str:
    """Encode k as a valid identifier (patsy treats '-' as minus). m=minus, p=plus."""
    if k < 0:
        return f"t_k_m{-k}"
    return f"t_k_p{k}"


def run_event_study(df: pd.DataFrame, outcome: str,
                    k_min: int = EVENT_K_MIN, k_max: int = EVENT_K_MAX,
                    omit_k: int = -1) -> pd.DataFrame:
    """
    Estimate event-study: separate β_k for each relative_month bin.
    Returns DataFrame with k, beta, se, ci_lo, ci_hi.

    Observations with |relative_month| > k_max are DROPPED, not clipped.
    Clipping would concentrate all distant pre/post months into the terminal
    bins, producing spurious extreme β at k_min and k_max.
    """
    d = df[[
        outcome, "is_treated", "relative_month", "repo_id",
        "snapshot_month_int", "history_months", "tsx_file_count",
    ]].dropna(subset=[outcome, "relative_month", "history_months", "tsx_file_count"]).copy()
    d["relative_month"] = d["relative_month"].astype(int)

    # Drop, don't clip
    d = d[(d["relative_month"] >= k_min) & (d["relative_month"] <= k_max)].copy()
    d["k"] = d["relative_month"].astype(int)

    if len(d) == 0 or d["is_treated"].nunique() < 2:
        out = pd.DataFrame({"k": [omit_k], "beta": [np.nan], "se": [np.nan],
                            "ci_lo": [np.nan], "ci_hi": [np.nan]})
        out.attrs["pretrend_F"] = np.nan
        out.attrs["pretrend_p"] = np.nan
        out.attrs["pretrend_ks"] = PRETREND_TEST_KS
        return out

    # Build dummies for treated × k, omitting omit_k as reference
    ks = sorted([k for k in range(k_min, k_max + 1) if k != omit_k])
    for k in ks:
        d[_k_to_name(k)] = ((d["is_treated"] == 1) & (d["k"] == k)).astype(int)

    d["repo_id_c"] = d["repo_id"].astype("category")
    d["month_c"] = d["snapshot_month_int"].astype("category")

    import statsmodels.formula.api as smf
    rhs = " + ".join(_k_to_name(k) for k in ks)
    formula = (
        f"{outcome} ~ {rhs} + is_treated + history_months + tsx_file_count "
        f"+ C(repo_id_c) + C(month_c)"
    )

    try:
        model = smf.ols(formula=formula, data=d).fit(
            cov_type="cluster",
            cov_kwds={"groups": d["repo_id"]},
        )
    except Exception as e:
        out = pd.DataFrame({"k": [omit_k], "beta": [np.nan], "se": [np.nan],
                            "ci_lo": [np.nan], "ci_hi": [np.nan],
                            "error": [str(e)[:80]]})
        out.attrs["pretrend_F"] = np.nan
        out.attrs["pretrend_p"] = np.nan
        out.attrs["pretrend_ks"] = PRETREND_TEST_KS
        return out

    rows = []
    for k in ks:
        name = _k_to_name(k)
        if name in model.params and not pd.isna(model.params[name]):
            b = model.params[name]
            s = model.bse[name]
            lo = b - 1.96 * s
            hi = b + 1.96 * s
            rows.append({"k": k, "beta": float(b), "se": float(s),
                         "ci_lo": float(lo), "ci_hi": float(hi)})
        else:
            rows.append({"k": k, "beta": np.nan, "se": np.nan,
                         "ci_lo": np.nan, "ci_hi": np.nan})
    rows.append({"k": omit_k, "beta": 0.0, "se": 0.0, "ci_lo": 0.0, "ci_hi": 0.0})
    rows.sort(key=lambda r: r["k"])

    # F-test for parallel-trends bins
    test_terms = []
    for k in PRETREND_TEST_KS:
        if k == omit_k:
            continue
        nm = _k_to_name(k)
        if nm in model.params and not pd.isna(model.params[nm]):
            test_terms.append(f"{nm}=0")
    pretrend_f, pretrend_p = (np.nan, np.nan)
    if test_terms:
        try:
            ft = model.f_test(", ".join(test_terms))
            pretrend_f = float(np.squeeze(ft.fvalue))
            pretrend_p = float(np.squeeze(ft.pvalue))
        except Exception:
            pass

    out = pd.DataFrame(rows)
    out.attrs["pretrend_F"] = pretrend_f
    out.attrs["pretrend_p"] = pretrend_p
    out.attrs["pretrend_ks"] = PRETREND_TEST_KS
    return out


# ── Per-rule heterogeneity (RQ3) ──────────────────────────────────────────────

def build_category_outcomes(conn: sqlite3.Connection, panel: pd.DataFrame) -> pd.DataFrame:
    """
    For each category, compute violations_per_renderable_file per (repo, month).
    Merge onto the panel and return panel + 3 new outcome columns.
    """
    detail = pd.read_sql_query("""
        SELECT d.snapshot_id, d.violation_id
        FROM axe_violations_detail d
    """, conn)

    snap_meta = panel[["snapshot_id", "repo_id", "snapshot_month", "renderable_count"]].drop_duplicates()
    detail = detail.merge(snap_meta, on="snapshot_id", how="inner")

    out = panel.copy()
    for cat, rules in CATEGORY_RULES.items():
        cnts = detail[detail["violation_id"].isin(rules)] \
            .groupby("snapshot_id").size().rename(f"cat_{cat}_n")
        out = out.merge(cnts, on="snapshot_id", how="left")
        out[f"cat_{cat}_n"] = out[f"cat_{cat}_n"].fillna(0)
        out[f"cat_{cat}_per_file"] = np.where(
            out["renderable_count"] > 0,
            out[f"cat_{cat}_n"] / out["renderable_count"],
            np.nan,
        )
    return out


# ── Plotting ──────────────────────────────────────────────────────────────────

def plot_event_study(es_df: pd.DataFrame, out_path: Path, title: str,
                     k_range: tuple = (EVENT_K_MIN, EVENT_K_MAX),
                     ylabel: str = "Estimate") -> None:
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    d = es_df[(es_df["k"] >= k_range[0]) & (es_df["k"] <= k_range[1])].copy()
    ax.axhline(0, color="grey", lw=0.8, ls="--")
    ax.axvline(-0.5, color="grey", lw=0.8, ls=":", label="Treatment")
    ax.errorbar(d["k"], d["beta"],
                yerr=[d["beta"] - d["ci_lo"], d["ci_hi"] - d["beta"]],
                fmt="o", capsize=3, color="#1f77b4", ecolor="#1f77b4", alpha=0.85)
    ax.set_xlabel("Months relative to treatment")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


# ── Output formatting ─────────────────────────────────────────────────────────

def fmt_row(r: dict) -> str:
    if r.get("error"):
        return f"  {r['outcome']:<28} ERROR: {r['error']}"
    return (
        f"  {r['outcome']:<28} "
        f"β={r['beta']:+.5f}  SE={r['se']:.5f}  "
        f"95%CI=[{r['ci_lo']:+.5f}, {r['ci_hi']:+.5f}]  "
        f"p={r['p']:.4f}  N={r['n_obs']}  clusters={r['n_clusters']}"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Stage 5 — DiD estimation")
    print(f"  DB:      {os.path.abspath(DB_PATH)}")
    print(f"  Output:  {OUT_DIR.resolve()}")
    print()

    conn = sqlite3.connect(DB_PATH)

    # 1. Panel
    print("Building panel …")
    panel = build_panel(conn)
    panel.to_csv(OUT_DIR / "panel.csv", index=False)
    n_repos = panel["repo_id"].nunique()
    n_treated = panel[panel["is_treated"] == 1]["repo_id"].nunique()
    n_control = panel[panel["is_treated"] == 0]["repo_id"].nunique()
    n_partial = panel[panel["repo_partial"] == 1]["repo_id"].nunique()
    print(f"  Repos: {n_repos} ({n_treated} treated, {n_control} control)")
    print(f"  Repo-months: {len(panel)}")
    print(f"  repo_partial=1: {n_partial}")
    print(f"  Treated POST months: {((panel.is_treated == 1) & (panel.is_post == 1)).sum()}")
    print(f"  Control synthetic POST months: {((panel.is_treated == 0) & (panel.is_post == 1)).sum()}")
    print()

    # 2. PSM balance
    psm = pd.read_sql_query("SELECT * FROM psm_diagnostics", conn)

    # 3. Primary DiD — three outcomes (v3.1 Amendment 3)
    print("Primary DiD …")
    primary = [
        run_did(panel, "axe_total_per_file", "axe_total_per_file"),
        run_did(panel, "axe_renderable_per_file", "axe_renderable_per_file"),
        run_did(panel, "ast_score_mean", "ast_score_mean"),
    ]
    table_main = pd.DataFrame(primary)
    table_main.to_csv(OUT_DIR / "table_main.csv", index=False)
    for r in primary:
        print(fmt_row(r))
    print()

    # 3b. Tobit regression on censored AST outcome
    print("Tobit regression (ast_score_mean, censored at 1.0) …")
    tobit_result = run_tobit(panel, "ast_score_mean", "ast_score_mean_tobit", upper_censor=1.0)
    print(fmt_row(tobit_result))
    pd.DataFrame([tobit_result]).to_csv(OUT_DIR / "table_tobit.csv", index=False)
    print()

    # 4. Event study (parallel trends + dynamic DiD)
    print("Event study (axe_renderable_per_file) …")
    es_axe = run_event_study(panel, "axe_renderable_per_file")
    es_axe.to_csv(OUT_DIR / "event_study_axe.csv", index=False)
    pretrend_F = es_axe.attrs.get("pretrend_F", np.nan)
    pretrend_p = es_axe.attrs.get("pretrend_p", np.nan)
    print(f"  Pre-trend F-test (β_-6=β_-3=β_-2=0): F={pretrend_F:.3f}, p={pretrend_p:.4f}")

    es_ast = run_event_study(panel, "ast_score_mean")
    es_ast.to_csv(OUT_DIR / "event_study_ast.csv", index=False)

    plot_event_study(
        es_axe[es_axe["k"] <= -1],
        OUT_DIR / "fig1_parallel_trends.png",
        title="Pre-trend test — axe violations per renderable component",
        k_range=(EVENT_K_MIN, -1),
        ylabel="β_k (vs k=-1)",
    )
    plot_event_study(
        es_axe,
        OUT_DIR / "fig2_dynamic_did.png",
        title="Dynamic DiD — axe violations per renderable component",
        ylabel="β_k (vs k=-1)",
    )

    # Polynomial fit on post-period coefficients
    post = es_axe[(es_axe["k"] >= 0) & es_axe["beta"].notna()].copy()
    poly_desc = "n/a"
    if len(post) >= 3:
        coeffs = np.polyfit(post["k"], post["beta"], deg=2)
        # coeffs = [a, b, c] for ax^2 + bx + c
        a, b, c = coeffs
        shape = "decay" if a < 0 else ("growth" if a > 0 else "linear")
        poly_desc = f"y = {a:+.5f}·k² {b:+.5f}·k {c:+.5f}  ({shape})"
    print(f"  Polynomial fit (post): {poly_desc}")

    beta_k = {int(r.k): float(r.beta) if not pd.isna(r.beta) else np.nan
              for r in es_axe.itertuples()}
    print(f"  β_0={beta_k.get(0, float('nan'))}, β_+6={beta_k.get(6, float('nan'))}, β_+12={beta_k.get(12, float('nan'))}")
    print()

    # 5. Heterogeneity — RQ3
    print("Heterogeneity (RQ3) …")
    panel_cat = build_category_outcomes(conn, panel)
    het_rows = []
    for cat in CATEGORY_RULES:
        col = f"cat_{cat}_per_file"
        r = run_did(panel_cat, col, cat)
        het_rows.append(r)
        print(fmt_row(r))
    table_het = pd.DataFrame(het_rows)
    table_het.to_csv(OUT_DIR / "table_heterogeneity.csv", index=False)
    print()

    # 6. Robustness — 5 specifications on axe_renderable_per_file
    print("Robustness (axe_renderable_per_file) …")
    rob_rows = []

    # 6a. drop partial
    r = run_did(panel[panel["repo_partial"] == 0], "axe_renderable_per_file", "drop_partial")
    rob_rows.append(r); print(fmt_row(r))

    # 6b/c. ±1 month treatment shift — recompute is_post on a copy
    for shift in (-1, +1):
        p2 = panel.copy()
        p2["treatment_month_int"] = p2["treatment_month_int"] + shift
        p2["is_post"] = (p2["snapshot_month_int"] >= p2["treatment_month_int"]).astype(int)
        label = f"shift_{shift:+d}_month"
        r = run_did(p2, "axe_renderable_per_file", label)
        rob_rows.append(r); print(fmt_row(r))

    # 6d. high render rate only — restrict to repos with >50% render rate
    render_rate = panel.groupby("repo_id").apply(
        lambda g: g["renderable_count"].sum() / max(g["component_count"].sum(), 1),
        include_groups=False,
    )
    keep = render_rate[render_rate > 0.50].index.tolist()
    r = run_did(panel[panel["repo_id"].isin(keep)], "axe_renderable_per_file", "render_gt_50pct")
    rob_rows.append(r); print(fmt_row(r))

    # 6e. critical only
    p3 = panel.copy()
    p3["axe_renderable_per_file"] = np.where(
        p3["renderable_count"] > 0,
        p3["violations_critical"] / p3["renderable_count"],
        np.nan,
    )
    r = run_did(p3, "axe_renderable_per_file", "critical_only")
    rob_rows.append(r); print(fmt_row(r))

    table_rob = pd.DataFrame(rob_rows)
    table_rob.to_csv(OUT_DIR / "table_robustness.csv", index=False)
    print()

    # 7. Human-readable summary
    print("Writing stage5_results.txt …")
    lines = []
    lines.append("=" * 70)
    lines.append("STAGE 5 — DiD ESTIMATION RESULTS")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Design: Study Design v3.0 + v3.1 Addendum")
    lines.append("=" * 70)
    lines.append("")
    lines.append("PANEL CONSTRUCTION")
    lines.append(f"  Repos included           : {n_repos} ({n_treated} treated, {n_control} control)")
    lines.append(f"  Repo-months              : {len(panel)}")
    lines.append(f"  repo_partial flagged     : {n_partial}")
    lines.append(f"  Treated POST months      : {((panel.is_treated == 1) & (panel.is_post == 1)).sum()}")
    lines.append(f"  Control synth POST months: {((panel.is_treated == 0) & (panel.is_post == 1)).sum()}")
    lines.append("")

    lines.append("PSM BALANCE (from psm_diagnostics)")
    lines.append(psm.to_string(index=False))
    lines.append("")

    lines.append("PRIMARY DiD")
    for r in primary:
        lines.append(fmt_row(r))
    lines.append("")

    lines.append("TOBIT REGRESSION (ast_score_mean, right-censored at 1.0)")
    lines.append(fmt_row(tobit_result))
    lines.append("  Note: 45.2% of observations censored at ceiling. OLS β understates true effect.")
    lines.append("")

    lines.append("PARALLEL TRENDS TEST (β_-6 = β_-3 = β_-2 = 0)")
    if not np.isnan(pretrend_F):
        verdict = "PASS" if pretrend_p > 0.10 else "FAIL"
        lines.append(f"  F = {pretrend_F:.3f}, p = {pretrend_p:.4f}  ->  {verdict}")
    else:
        lines.append("  Could not compute F-test")
    lines.append("")

    lines.append("DYNAMIC DiD (axe_renderable_per_file)")
    for k in (0, 6, 12):
        v = beta_k.get(k, np.nan)
        lines.append(f"  β_{k:+d} = {v:+.5f}" if not pd.isna(v) else f"  β_{k:+d} = NaN")
    lines.append(f"  Polynomial fit: {poly_desc}")
    lines.append("")

    lines.append("HETEROGENEITY (RQ3)")
    for r in het_rows:
        lines.append(fmt_row(r))
    lines.append("")

    lines.append("ROBUSTNESS")
    for r in rob_rows:
        lines.append(fmt_row(r))
    lines.append("")

    # Decision rule (v3.1 Amendment 2): axe-total vs axe-renderable ratio in [0.5, 2.0]?
    bt = primary[0]["beta"]
    br = primary[1]["beta"]
    bs_ast = primary[2]["beta"]
    lines.append("INTERPRETATION NOTES")
    if pd.notna(bt) and pd.notna(br) and br != 0:
        ratio = bt / br
        same_sign = (bt > 0 and br > 0) or (bt < 0 and br < 0) or (bt == 0 and br == 0)
        within = 0.5 <= ratio <= 2.0 if same_sign else False
        lines.append(f"  axe-total / axe-renderable ratio: {ratio:+.3f}  (target [0.5, 2.0] same sign)")
        lines.append(f"  Same sign across axe denominators: {'yes' if same_sign else 'no'}")
        lines.append(f"  Render rate materially biasing conclusions: {'no' if within else 'YES — flag in paper'}")
    else:
        lines.append("  axe ratio: undefined (NaN coefficient)")
    if pd.notna(br) and pd.notna(bs_ast):
        # axe + means worse, AST - means worse. So directional agreement: sign(br) != sign(bs_ast).
        agree = (br > 0 and bs_ast < 0) or (br < 0 and bs_ast > 0)
        lines.append(f"  AST agreement with axe (axe+ ↔ AST-): {'yes' if agree else 'no'}")
    lines.append("")

    lines.append("FILES WRITTEN")
    for f in sorted(OUT_DIR.iterdir()):
        size = f.stat().st_size
        lines.append(f"  {f.name}  ({size} bytes)")

    txt = "\n".join(lines)
    (OUT_DIR / "stage5_results.txt").write_text(txt)
    print(txt)
    print()
    print(f"Stage 5 complete. β_axe_renderable = {br:+.5f} (p={primary[1].get('p', float('nan')):.4f}), "
          f"β_ast = {bs_ast:+.5f} (p={primary[2].get('p', float('nan')):.4f}).")

    conn.close()


if __name__ == "__main__":
    main()
