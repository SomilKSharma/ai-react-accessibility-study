# Analysis Plan

**Study:** *When Distributional Findings Deceive: A Methodology for Dynamic
Analysis of Clustered Software Panels, Demonstrated on the AI-Accessibility
Question*
**Author:** Somil Sharma · Independent Researcher, Gurugram, India
**Replication package:** https://github.com/SomilKSharma/ai-react-accessibility-study

## Status

This study was **not** lodged as a formal public pre-registration (OSF /
AsPredicted). It was conducted from a **written internal analysis plan fixed
before estimation**. This document reproduces that plan and states, in full,
every deviation from it, so that the analytic choices are auditable. It is
consistent with Appendix B ("Analysis-Plan Deviation Statement") of the
manuscript; where the two are read together, the manuscript is authoritative.

- **Plan finalised (before estimation):** 2026-05-01.
- **Data-collection period:** 2026-05-15 - 2026-05-31

The mean-effect questions (RQ1–RQ4) derive from the originating empirical study;
the dynamics question (RQ5) and the disposition of a null result were fixed in
advance as a co-equal axis.

---

## 1. Research questions

- **RQ1.** Does AI-tool adoption causally increase axe-core accessibility
  violation density in React/TypeScript repositories?
- **RQ2.** Does AI-tool adoption degrade AST-based semantic-HTML correctness?
- **RQ3.** Are post-treatment effects concentrated in specific violation
  categories (semantic naming, ARIA, document structure)?
- **RQ4.** Do accessibility violations accumulate or decay over time following
  AI-tool adoption?
- **RQ5.** Does AI-tool adoption reshape the *stochastic dynamics* of
  accessibility quality — its volatility, the persistence of degraded states,
  upper-tail risk, and the balance of violation introduction versus removal
  (the utilization ρ = λ/μ) — even where the mean is unchanged?

## 2. Dynamics hypothesis and its pre-specified null disposition

**H (dynamics hypothesis).** AI-tool adoption reshapes the stochastic dynamics
of accessibility quality even where the static mean is unchanged; concretely,
adoption raises the introduction rate relative to the removal rate, pushing the
queueing utilization ρ = λ/μ toward and past the instability boundary ρ = 1,
producing slow backlog accumulation visible to a dynamic analysis but invisible
to a difference-in-means.

**Null disposition (fixed in advance).** If ρ_post ≈ ρ_pre and the
volatility/persistence/tail moments are statistically indistinguishable across
regimes, **H is rejected, and that null is reported as a primary, publishable
result.** This disposition was committed before estimation specifically to guard
against constructing a positive narrative after seeing the data.

## 3. Identification and estimation — mean effects (RQ1–RQ4)

Two-way fixed-effects (TWFE) difference-in-differences:

    y_it = α_i + γ_t + β · (Treated_i × Post_it) + X_it·δ + ε_it

- **Fixed effects:** repository (α_i) and calendar-month (γ_t).
- **Time-varying controls X_it:** commit frequency, contributor count.
- **Inference:** standard errors clustered at the repository level.
- **Parallel-trends test (pre-specified):** joint F-test on pre-treatment
  event-study coefficients at k = −6, −3, −2 months.
- **Dynamic DiD (RQ4):** individual coefficients β_k for k ∈ [−12, +12] months
  relative to treatment, with k = −1 as the reference period.

## 4. Treatment-date assignment

A signal hierarchy:

- **Tier 1 (confidence 0.90):** first appearance of AI-tool config artifacts
  (`.cursor/`, `.cursorrules`, `.github/copilot-instructions.md`, or VSCode
  settings containing `github.copilot.*`).
- **Tier 2 (0.75):** first `Co-authored-by: copilot@github.com` commit trailer.
- **Tier 3 (0.40):** comment-density inflection — **excluded from all analyses.**

The primary analysis uses **Tier 1 repositories only**. Robustness to ±1-month
treatment-date shifts was specified in advance.

For control repositories, the regime boundary is the matched treated repo's
treatment date (controls inherit their matched partner's date).

## 5. Sample selection and matching

**Inclusion filters** (React/TypeScript repositories from GitHub):
1. ≥ 12 months of snapshot coverage;
2. ≥ 100 renderable component rows;
3. ≥ 60% TypeScript/TSX files;
4. `tsx_file_count` ≤ 500 (common-support region).

**Matching:** propensity-score matching, 1:1 nearest-neighbour, caliper 0.10, on
four pre-treatment covariates: `history_months`, `tsx_file_count`,
`contributor_count`, `commit_frequency`. Post-match covariate balance is
reported (target: standardised differences below the conventional threshold).

## 6. Outcome metrics

- **`axe_renderable_per_file` (primary):** combined critical + serious axe-core
  violations per successfully-rendered component file.
- **`axe_total_per_file` (co-primary denominator / rendering-bias check):**
  normalised by total component count.
- **`ast_score_mean`:** render-independent AST semantic-correctness score in
  [0, 1], right-censored at 1.0. A **Tobit specification** is a pre-specified
  robustness check for the censoring (corroborative only; not an independent
  inferential claim).

## 7. Dynamics analysis (RQ5)

State variable: monthly `axe_renderable_per_file` per repository.

- **State space:** ordered states via pooled quantiles of the combined pre+post
  distribution. The **3- and 4-state partitions are the substantive
  specifications**; a requested 5-state partition (which degenerates to 4
  occupied states under the zero-inflated outcome) is reported as a robustness
  point.
- **Discrete-time Markov chain:** transition matrices by closed-form MLE
  (P_ij = n_ij / Σ_k n_ik), pooled across repositories within a regime;
  transitions never straddle the adoption boundary or a coverage gap. Derived
  quantities: stationary distribution π, self-transition/dwell time, spectral
  gap (1 − |λ₂|).
- **Markov tests, with degrees of freedom corrected for occupied support
  (pre-specified):** a homogeneity LR test (H₀: P^pre = P^post) and a
  first-vs-second-order LR test. The df correction — counting only estimable
  (occupied, reachable) parameters — was specified in advance because the
  zero-inflated outcome (≈ 42% of repo-months at exactly zero) collapses lower
  quantile cutpoints onto zero and otherwise induces a phantom never-occupied
  state that mechanically forces non-rejection.
- **Birth–death / utilization:** introduction rate λ and removal rate μ per
  repo-month, with ρ = λ/μ. **λ and μ are normalised over the same exposure
  (all repo-months)** so that ρ is a well-defined rate ratio (pre-specified;
  mismatched denominators are explicitly disallowed). The discrete-time model is
  used for regime *contrast*; the absolute level of ρ at monthly cadence is not
  claimed.
- **Upper-tail risk:** the inferential test is a **difference-in-differences
  logistic regression** on exceedance of the pooled 90th percentile,
  `tail ~ post + treated + post:treated`, with repository-clustered standard
  errors; the interaction isolates the treated-group change net of the control
  trend. A pooled pre/post two-proportion z-test is explicitly **not** treated as
  a valid test of an AI-specific effect (it ignores clustering and the
  treated-vs-control contrast).
- **Volatility:** Brown–Forsythe test on the regime variances.
- **Uncertainty:** all regime contrasts (spectral-gap difference, ρ difference,
  etc.) receive 95% confidence intervals from a **repository-level block
  bootstrap** (2,000 replicates, fixed seed), resampling whole repositories —
  never individual repo-months.
- **Negative control:** the same Markov machinery applied to a stylistic metric
  (monthly component count / repository size), for which adoption has no a-priori
  reason to alter dynamics, with the same repo-level block bootstrap.

## 8. Power analysis

A **cluster-aware simulation** matched to the inference: inject a known additive
effect onto treated-post observations, resample whole repositories with
replacement (re-assigning cluster identifiers so the standard errors stay
honest), re-estimate the exact TWFE DiD with repo-clustered SEs, and record the
rejection rate at α = 0.05 over 400 simulations per effect size. The reported
power curve is an upper bound for a heterogeneous or gradually-accumulating
alternative.

## 9. Determinism

Every stochastic step (the dynamics block bootstrap, the power simulation, the
negative-control bootstrap, and the rater-reliability bootstrap) uses a single
fixed seed, `numpy.random.default_rng(20260625)`. Re-running yields identical
numbers.

## 10. Construct validation (AST semantic score)

The AST semantic score is validated against expert judgement by a multi-rater
study. Pre-specified analyses: Krippendorff's α (ordinal) across raters with a
bootstrap 95% CI; pairwise quadratic-weighted Cohen's κ as a secondary statistic;
per-rater and pooled Spearman ρ / Kendall τ against the automated score (pooled ρ
as the headline); and a band-monotonicity check (mean rating by AST-score band,
no reversals). Raters score component source blind to the automated score and to
one another.

---

## 11. Deviations from this plan

All deviations below were motivated by features discovered during data
collection, **not** by inspection of results.

1. **AST score elevated to a co-primary outcome**, motivated by the 60.4%
   renderability constraint discovered during data collection (a
   render-independent metric with full coverage was needed for an unbiased
   panel).
2. **Dual denominator:** the renderable-only axe rate was moved from a
   sensitivity check to co-primary alongside the total-count denominator.
3. **Inclusion criterion changed to a data-coverage rule** (≥ 12 months and
   ≥ 100 renderable rows).
4. **Tobit regression added** as a planned robustness check for the
   right-censored AST outcome.

**No changes** were made to: the DiD estimating equation, the PSM specification,
the treatment-date assignment logic, the AST scoring rubric, or the RQ
structure.

For the dynamics analysis (RQ5), the hypothesis and the disposition of a null
were fixed in advance (Sections 2 and 7 above); the degrees-of-freedom
correction for the zero-inflation degeneracy and the cluster-robust DiD tail
test were specified before estimation. Two analyses that were corrected during
the study — a pooled tail-risk test (later replaced by the clustered DiD logit)
and a birth–death utilization estimate with mismatched exposure denominators
(later corrected to matched denominators) — are reported transparently in the
manuscript alongside their corrected counterparts.

> *Note for a future study: lodging this plan on OSF or AsPredicted before data
> collection would let the work claim formal pre-registration.*