"""
M5 fix: simulate the Result-2 claim instead of arguing it verbally.

An EARLIER version of this paper claimed (Result 2) that a birth-death utilization
rho = lambda/mu estimated from MONTHLY NET file diffs is biased upward in LEVEL but
UNBIASED in the pre/post CONTRAST, on the verbal argument that the within-month
truncation is a multiplicative factor that cancels in the ratio-of-ratios.

The referee correctly noted that the paper's own ethos -- simulate the null, do
not trust a clean cancellation argued only verbally -- demands this be tested. We
built the test, and IT REFUTES THE CLAIM. We keep the simulation precisely because
it overturns our own conjecture: the truncation factor depends on the regime's
event rate, so it does NOT cancel, and the contrast is biased too. We therefore
WITHDRAW the contrast-unbiased claim and drop snapshot-cadence utilization from the
substantive analysis. This script documents the refutation.

We build a synthetic continuous-time birth-death process per repo-month with a
KNOWN ground-truth lambda and mu, observe it only through monthly net snapshots
(exactly as the real pipeline does), and show:
  (a) the monthly-snapshot rho-hat is biased upward vs the true rho (LEVEL bias);
  (b) the pre/post CONTRAST rho_post - rho_pre is ALSO biased and does NOT recover
      the true contrast, across a sweep of the within-month event rate -- refuting
      the original cancellation conjecture.

Pure numpy. Fixed seed -> deterministic. Outputs a figure parallel to the
tail-test Monte Carlo (fig6) and a JSON.
"""
import json
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


def simulate_repo_month(rng, lam_true, mu_true, events_per_month, n_files=40):
    """
    Simulate one repo-month of file-level violation dynamics as a continuous-time
    birth-death process, then observe ONLY the net change per file between the
    month-start and month-end snapshots (the real pipeline's monthly net diff).

    lam_true : true per-file introduction intensity (births per file per month)
    mu_true  : true per-file removal intensity (deaths per file per month, on files
               that currently carry >=1 violation)
    events_per_month : granularity of the within-month process (how many sub-steps
               we resolve). Higher = more within-month introduce-fix churn that
               nets to zero and is invisible to the monthly snapshot.

    Returns observed (introduced, removed) summed over files from the NET diff,
    and the true (births, deaths) actually occurring.
    """
    start = rng.poisson(0.5, size=n_files).astype(int)   # initial backlog per file
    cur = start.copy()
    true_births = 0
    true_deaths = 0
    dt = 1.0 / events_per_month
    for _ in range(events_per_month):
        # births: each file gains a violation w.p. lam_true*dt
        b = rng.random(n_files) < (lam_true * dt)
        true_births += int(b.sum())
        cur = cur + b.astype(int)
        # deaths: each file with >=1 violation loses one w.p. mu_true*dt
        elig = cur > 0
        d = elig & (rng.random(n_files) < (mu_true * dt))
        true_deaths += int(d.sum())
        cur = cur - d.astype(int)
    net = cur - start                      # what the monthly snapshot sees
    introduced = int(net[net > 0].sum())   # files whose count rose -> counted in lambda
    removed = int((-net[net < 0]).sum())   # files whose count fell -> counted in mu
    return introduced, removed, true_births, true_deaths


def estimate_rho(rng, lam_true, mu_true, events_per_month, n_repo_months=400):
    """Aggregate observed introduced/removed over many repo-months -> rho-hat,
    alongside the true rho = lam_true/mu_true."""
    intro = rem = 0
    for _ in range(n_repo_months):
        i, r, _, _ = simulate_repo_month(rng, lam_true, mu_true, events_per_month)
        intro += i
        rem += r
    rho_hat = intro / rem if rem > 0 else np.nan
    return rho_hat


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    results = {"sweep": []}

    # Ground truth: pick a true pre and post regime with a KNOWN contrast.
    # Both subcritical (rho<1); the post regime has slightly higher utilization.
    lam_pre, mu_pre = 0.30, 0.50      # true rho_pre = 0.60
    lam_post, mu_post = 0.39, 0.50    # true rho_post = 0.78
    true_rho_pre = lam_pre / mu_pre
    true_rho_post = lam_post / mu_post
    true_contrast = true_rho_post - true_rho_pre

    print("=== Result-2 simulation: monthly-net-diff rho bias ===")
    print(f"Ground truth: rho_pre={true_rho_pre:.3f}, rho_post={true_rho_post:.3f}, "
          f"true contrast={true_contrast:+.3f}\n")
    print(f"{'within-mo events':>16} {'rho_pre_hat':>11} {'rho_post_hat':>12} "
          f"{'level bias':>11} {'contrast_hat':>12} {'contrast err':>12}")

    for epm in [1, 2, 4, 8, 16, 32]:
        # fresh independent streams for pre and post
        rp = estimate_rho(np.random.default_rng(SEED + epm), lam_pre, mu_pre, epm)
        rq = estimate_rho(np.random.default_rng(SEED + 1000 + epm), lam_post, mu_post, epm)
        contrast_hat = rq - rp
        level_bias_pre = rp - true_rho_pre
        results["sweep"].append(dict(
            events_per_month=epm, rho_pre_hat=rp, rho_post_hat=rq,
            level_bias_pre=level_bias_pre, contrast_hat=contrast_hat,
            contrast_err=contrast_hat - true_contrast))
        print(f"{epm:>16} {rp:>11.3f} {rq:>12.3f} {level_bias_pre:>+11.3f} "
              f"{contrast_hat:>+12.3f} {contrast_hat - true_contrast:>+12.3f}")

    results["truth"] = dict(rho_pre=true_rho_pre, rho_post=true_rho_post,
                            contrast=true_contrast)
    with open(OUTDIR / "result2_simulation.json", "w") as f:
        json.dump(results, f, indent=2)

    # Figure: two panels.
    # (a) estimated level rho vs within-month event rate, with true levels (level bias grows)
    # (b) estimated contrast vs within-month event rate, with true contrast (contrast stays ~unbiased)
    sw = results["sweep"]
    xs = [s["events_per_month"] for s in sw]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))

    ax1.plot(xs, [s["rho_pre_hat"] for s in sw], "o-", color="#888888", label=r"$\hat\rho$ pre (observed)")
    ax1.plot(xs, [s["rho_post_hat"] for s in sw], "s-", color="#2c6fbb", label=r"$\hat\rho$ post (observed)")
    ax1.axhline(true_rho_pre, ls="--", color="#888888", lw=1, label=r"true $\rho$ pre = %.2f" % true_rho_pre)
    ax1.axhline(true_rho_post, ls="--", color="#2c6fbb", lw=1, label=r"true $\rho$ post = %.2f" % true_rho_post)
    ax1.set_xscale("log", base=2)
    ax1.set_xlabel("within-month introduce–fix events (granularity)")
    ax1.set_ylabel(r"utilization $\hat\rho$")
    ax1.set_title("(a) Level: monthly $\\hat\\rho$ biased upward\nas within-month churn rises")
    ax1.legend(frameon=False, fontsize=7.5)

    ax2.plot(xs, [s["contrast_hat"] for s in sw], "D-", color="#c0392b",
             label=r"$\hat\rho_{post}-\hat\rho_{pre}$ (observed)")
    ax2.axhline(true_contrast, ls="--", color="black", lw=1,
                label=r"true contrast = %.2f" % true_contrast)
    ax2.set_xscale("log", base=2)
    ax2.set_xlabel("within-month introduce–fix events (granularity)")
    ax2.set_ylabel(r"regime contrast $\Delta\hat\rho$")
    ax2.set_title("(b) Contrast: regime difference is\nALSO biased — cancellation fails")
    ax2.set_ylim(0, max(0.9, true_contrast + 0.2))
    ax2.legend(frameon=False, fontsize=8)

    fig.suptitle("Refuting our own conjecture: monthly net-diff utilization is biased in LEVEL "
                 "and in the pre/post CONTRAST\n(the within-month truncation factor differs by regime, "
                 "so it does not cancel)", fontsize=9.5)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(FIGDIR / "fig7_result2_sim.png", dpi=150)
    fig.savefig(FIGDIR / "fig7_result2_sim.pdf")
    print(f"\nSaved figure -> {FIGDIR/'fig7_result2_sim.png'} (+ .pdf)")
    print(f"Saved data    -> {OUTDIR/'result2_simulation.json'}")
