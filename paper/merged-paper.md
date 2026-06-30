# No Detectable Accessibility Regression from AI Coding-Tool Adoption: A Bounded Null from 446 React/TypeScript Repositories under Staggered Difference-in-Differences

**Somil Sharma**
Independent Researcher, Gurugram, India · iamsomilsharma@gmail.com

*Clinical trial number: not applicable.*

---

## Abstract

Do AI coding assistants (Cursor, GitHub Copilot) degrade the accessibility of the code they help produce? Accessibility is a legal and ethical baseline for web software, prior work shows AI assistants do not generate more accessible code than developers unaided, and rule-based checkers miss much of WCAG — so the concern is real and, in the prior literature, primed toward harm. We provide the first longitudinal *causal* study of AI-tool adoption effects on the *statically-detectable* accessibility quality of frontend source, over **446 open-source React/TypeScript repositories** (189 treated, 257 never-treated; 13,702 repo-months; a propensity-matched 181-repo subset serves as the primary identification panel) under a staggered difference-in-differences (DiD) design. We measure source-level accessibility along **four complementary axes** — semantic-HTML correctness, WCAG-category violation density (perceivable/operable/understandable/robust), severity-weighted violations, and keyboard/focus operability — via a render-independent static analysis that achieves 100% component coverage. (A fifth axis, ARIA-role correctness, showed essentially no variation in this corpus and is reported as such rather than modelled.) We are explicit that this captures accessibility properties visible in source — semantic structure, keyboard affordances, ARIA usage — not runtime properties such as computed colour contrast or live focus order, which no static method can see.

The headline is a **comprehensive, tightly-bounded null**. Across all four measured axes, the average treatment effect is null and stable across two-way fixed effects and a Borusyak–Jaravel–Spiess heterogeneity-robust imputation estimator, on both the matched and the full panel, with wild-cluster bootstrap inference confirming the null is not a small-sample artifact. Critically, the larger panel lets us state the null as a *positive* equivalence claim at a far tighter bound than scale previously allowed: equivalence (TOST) testing rejects effects larger than **±5% of baseline** on the dense semantic-HTML and keyboard axes and **±10–30%** on the rare-event violation-density axes (whose looser bound reflects their near-zero baseline, not weaker data) — not merely "we failed to reject." Treated and control repositories show comparable post-period maintenance activity, so the comparison group behaves as a clean counterfactual. Extending the analysis beyond the mean — to volatility, upper-tail risk, and the persistence of quality states — we find the *level* of every moment unchanged, with one robust second-order exception: post-adoption quality states are modestly but reliably *stickier* (spectral-gap difference −0.019, 95% CI [−0.031, −0.007]), i.e. AI-assisted repositories show less month-to-month churn in their accessibility profile without that profile becoming better or worse.

Reaching that null required killing two of our own too-good-to-be-true positives, and the discipline that did so is the paper's transferable methodological by-product, which we package as a short checklist for distributional analysis of clustered, zero-inflated repository panels. A naive pooled tail-risk test read *p* = 0.003 (apparent harm) and reversed to a null once treated-versus-control contrast and within-repo clustering were respected; a Monte Carlo on synthetic null panels quantifies that the naive test rejects a true null up to 100% of the time under a common secular trend while the cluster-robust DiD holds nominal size. We also state one SE-specific pitfall as a named result (a zero-inflation degrees-of-freedom degeneracy in Markov regime tests under quantile binning), and — in the same self-correcting spirit — report a conjecture about snapshot-cadence utilization that our own simulation *refuted*, leading us to withdraw it.

**Keywords:** AI-assisted development, web accessibility, difference-in-differences, staggered adoption, clustered inference, equivalence testing, null results, distributional treatment effects, zero-inflation, empirical software engineering.

---

## 1. Introduction

Every day, developers accept AI-generated React components into production without running a single accessibility check. Tools such as Cursor and GitHub Copilot have reshaped how frontend code is written, offering completions that are syntactically correct and functionally plausible. Their effect on the *non-functional* properties of that code — accessibility, semantic correctness, structural integrity — has received far less scrutiny than their effect on velocity or functional correctness.

Accessibility failures are not cosmetic. The Web Content Accessibility Guidelines (WCAG) constitute a legal baseline in multiple jurisdictions, and violations exclude users who rely on screen readers, keyboard navigation, and other assistive technologies. Prior work establishes two facts that motivate concern. First, rule-based accessibility checkers cover only a fraction of WCAG criteria (He, Huq, and Malek (2025)), so violations can accumulate below the visibility threshold of standard tooling. Second, AI coding assistants do not produce more accessible code than human developers by default, and in several controlled conditions produce *less* accessible code (Mowar et al., CHI 2025). What remains unknown — and what this paper addresses — is whether AI-tool adoption *causally* changes accessibility quality over time in real production codebases.

What remains unknown — and what this paper settles for the open-source React/TypeScript ecosystem — is whether AI-tool adoption *causally* changes accessibility quality over time in real production codebases. We treat this as the primary question and answer it with a rigorously identified design; the methodological lessons we learned reaching the answer are the secondary, transferable by-product.

The answer is a **comprehensive, tightly-bounded null**. We do not find that AI-tool adoption degrades source-level accessibility quality on any of the four measured axes, and the null is unusually well-defended: it holds across two-way fixed effects and a heterogeneity-robust staggered-DiD imputation estimator, on a propensity-matched 181-repo panel and on the full 446-repo panel, survives a wild-cluster bootstrap, and is stated as a positive equivalence claim (we reject effects larger than ±5% of baseline on the semantic-HTML and keyboard axes) rather than a bare failure to reject. Treated and control repositories show comparable post-period maintenance activity, so the comparison group is a clean counterfactual. We also look beyond the mean — at volatility, upper-tail risk, and state persistence — and find the *level* of every moment unchanged, with one nuance worth reporting: quality states become modestly *more persistent* post-adoption (a slower-mixing chain whose spectral gap halves, CI excluding zero), a small benign second-order effect — less churn, not better or worse quality — that leaves the level null intact.

That null was not free. Repository panels are treacherous for distributional and dynamic analysis: repo-months are heavily clustered, outcomes are zero-inflated, and pre/post windows mix treated and control units whose composition drifts over calendar time, so a distributional test run naively will *manufacture* a significant, hypothesis-confirming effect. We were nearly fooled twice — by a pooled tail-risk test reading *p* = 0.003 and by an apparent queueing-utilization crossover — and the discipline that caught both is worth more to the next analyst than the substantive null itself. We therefore distil it into a short checklist and a quantified demonstration, and we hold ourselves to the same standard we recommend: where we could only argue a convenient property verbally, we simulated it, and we report one such conjecture that our own simulation *refuted*.

This paper makes the following contributions, ordered by significance. The first three are the empirical study; the last two are the transferable methodological by-product.

1. **The first large-scale longitudinal causal study of AI coding-tool adoption effects on source-level frontend accessibility.** Over **446 open-source React/TypeScript repositories and 13,702 repo-months** (a propensity-matched 181-repo subset as the primary identification panel), we estimate the average treatment effect with a staggered DiD design — two-way fixed effects plus a Borusyak–Jaravel–Spiess heterogeneity-robust imputation estimator — across **four statically-measured accessibility axes**: semantic-HTML correctness, WCAG-category violation density, severity-weighted violations, and keyboard/focus operability (a fifth, ARIA-role correctness, was near-constant and is reported as such). This extends the He, Miller, et al. (2026) AI-adoption framework to a non-functional quality attribute, accessibility, that it did not study.

2. **A comprehensive, tightly-bounded, multiply-robust null.** No axis shows a significant effect under either estimator, on either panel; we defend the null with a wild-cluster bootstrap (small-cluster-robust) and an equivalence (TOST) test that **positively rejects effects above ±5% of baseline on the semantic-HTML and keyboard axes** (±10–30% on the sparser violation-density axes). The scale-up tightens the certified equivalence bound roughly nine-fold relative to a small panel, converting "we found no large effect" into "we exclude even modest effects." Treated and control repositories have comparable post-period maintenance activity, addressing the moving-control-arm concern directly.

3. **A render-independent, multi-axis static accessibility analyzer with 100% component coverage.** Where runtime axe-core rendering fails on ~60% of components, our static TypeScript-AST analyzer measures every source-detectable axis on every component, deterministically. The semantic-HTML score is construct-validated against four independent expert raters (Krippendorff's α = 0.870), including a three-rater robustness analysis that excludes the metric's designer; the remaining axes are rule-based static checks whose definitions we give in full, and we are explicit (Section 7) that the analyzer sees source structure, not runtime behaviour.

4. **A practitioner checklist plus a quantified failure mode for distributional analysis of clustered, zero-inflated repository panels (Section 6).** The checklist composes established econometric hygiene (contrast treated-vs-control, cluster within repo) with the worked demonstration of how badly it fails when violated: a pooled tail test reading *p* = 0.003 that reverses to a null, and a Monte Carlo on synthetic null panels showing the naive test rejects a true null up to 100% of the time under a common secular trend while the cluster-robust DiD holds nominal size. We are explicit that the hygiene is not novel; the contribution is the measured demonstration in the SE setting.

5. **One named SE-specific pitfall, and one self-refuted conjecture reported honestly.** *Result 1* — a zero-inflation degrees-of-freedom degeneracy that silently invalidates Markov regime tests under quantile binning of a zero-inflated outcome. And, in the same self-correcting spirit, we conjectured that a snapshot-cadence birth–death utilization is biased in level but unbiased in the pre/post contrast; our own simulation refuted the cancellation, so we **withdraw** that claim and drop the queueing apparatus from the substantive analysis — reported here because surfacing a refuted conjecture is part of the methodological honesty we advocate.

We are explicit throughout about the limits of the substantive claim: equivalence is certified at ±5% on the dense score axes but only ±10–30% on the sparse violation-density axes, and the dynamics conclusion is bounded by monthly snapshot cadence. We discuss in Section 7 how a per-commit, pre-registered follow-up would tighten the remaining bounds.

The remainder of this paper is organised as follows. Section 2 reviews related work. Section 3 describes the study design and identification strategy. Section 4 presents the mean-effect results under all three DiD estimators, with the equivalence, power, wild-cluster, and multiplicity analyses. Section 5 extends the analysis beyond the mean (volatility, persistence, tail risk), states Result 1, and reports the withdrawn utilization conjecture. **Section 6 distils the methodological by-product: the Monte Carlo size study, the worked tail-test artifact, and the practitioner checklist.** Section 7 discusses the bounded null and its scope. Section 8 enumerates threats to validity, including the construct-validity study. Section 9 concludes.

---

## 2. Related Work

We position the work first against the methodological literature it contributes to (distributional/dynamic effects and stochastic-process models in SE), then against the substantive literature it draws its setting from (AI-assisted development, accessibility, frontend static analysis).

### 2.1 Beyond Mean Effects in Empirical Software Engineering

Quantitative empirical SE overwhelmingly reports treatment effects on means or proportions. That distributional and dynamic properties carry information *beyond* the mean is standard in econometrics — quantile and distributional treatment effects are well-developed — the changes-in-changes model of Athey and Imbens (2006), the recentered-influence-function (RIF) unconditional quantile regressions of Firpo, Fortin, and Lemieux (2009), the staggered-adoption group-time estimators of Callaway and Sant'Anna (2021) that make the treated-vs-control structure explicit across periods, and the quantile-treatment-effect DiD estimators of Callaway and Li (2019) — but such distributional analysis remains rare in SE measurement, where outcome series are typically collapsed to per-period averages before analysis. He, Miller, et al. (2026) find that much of the warning- and complexity-increase from AI adoption is *mediated* by velocity-driven codebase growth rather than being a direct mean effect — a result invisible to a difference-in-means and recoverable only by modelling the panel's internal dynamics, which hints that the per-period mean understates the story. We make the dynamic dimension explicit, and our methodological contribution (Section 6) is precisely about the inferential hazards that arise when this is done naively on clustered repository panels — hazards the mean-effect literature rarely confronts because per-period averaging obscures them, and which require the cluster-robust inference of Cameron, Gelbach, and Miller (2008). By returning a null on the dynamics, we also illustrate the converse the field needs: the dynamic dimension does not *automatically* harbour an effect the mean missed.

### 2.2 Stochastic-Process Models of Software Evolution

Software evolution has long been modelled stochastically: defect arrival and removal are the basis of non-homogeneous-Poisson-process software-reliability-growth models, of which the Goel and Okumoto (1979) time-dependent error-detection model is the canonical instance. Birth–death and queueing formulations are the natural extension for backlog quantities — issues opened versus closed, defects introduced versus fixed. We apply this lineage to *accessibility debt*, treating each outstanding violation as a queue item with introduction rate λ and removal rate μ, and the utilization ρ = λ/μ as the object of interest. To our knowledge this is the first queueing-theoretic utilization analysis of accessibility-quality dynamics under an identified AI-adoption treatment — and, equally, a demonstration that such a model can be fit, tested, and found to show *no* regime difference, which is a useful negative calibration for a modelling approach otherwise prone to over-interpretation (Section 6.5 shows exactly how it over-interpreted before the denominator bug was caught).

### 2.3 Empirical Studies of AI-Assisted Development

He, Miller, et al. (MSR 2026) provide the methodological foundation for this work. They apply a staggered difference-in-differences design to GitHub repositories that adopted Cursor, measuring development velocity, static-analysis warnings, code complexity, and duplicate-line density. Their central finding is a **large but transient increase in velocity alongside a substantial and persistent rise in static-analysis warnings (≈30.3%) and code complexity (≈41.6%)**, with duplicate-line density insignificant. Crucially, a dynamic-panel-GMM mediation analysis shows much of the warning and complexity increase runs *through* the velocity-driven growth in codebase size rather than being a direct effect — a result that depends on looking past the static mean to the panel's internal dynamics. This both supplies the identification template we adapt (treatment-date assignment from tool-config artifacts, repo and time fixed effects, repo-clustered inference) and is the first hint, which Section 5 pursues, that the per-period mean can understate the generative story a panel contains.

Nahar et al. (ICSE-SEIP 2025) provide complementary evidence that quality assurance for LLM-based software is hard and departs from traditional practice. Through 26 interviews and a survey of roughly 332 practitioners at Microsoft, they study the challenges of **integrating LLMs as components into software products** and catalogue 19 emerging QA solutions. Their setting (LLM-powered product features) differs from ours (AI-*assisted code generation*), and they do not study accessibility; we cite them for the broader point their mixed-method evidence establishes — that assuring the non-functional quality of LLM-influenced software resists conventional, functional-test-centric QA — and we extend that concern to the distinct, and quantitatively measurable, setting of code written with AI assistance.

A broader wave of empirical work measures AI-assistant effects on productivity and acceptance behaviour — including the randomized controlled trial of Becker, Rush, Barnes, and Rein (2025), which found that early-2025 AI tools made experienced open-source developers ≈19% *slower* on real tasks even though they expected to be faster. We position our study against this literature by noting what it does *not* do: it studies velocity and functional correctness, not the longitudinal evolution of a non-functional quality attribute under an identified adoption event. The closest such work, He, Miller, et al. (2026), finds AI adoption raises short-term velocity while increasing long-term complexity — a velocity/quality trade-off on the *mean* of code-complexity metrics — which our study complements by asking the analogous causal question for accessibility, and by extending it to the distributional and dynamic moments the mean leaves unexamined.

### 2.4 Accessibility and AI Code Generation

Mowar et al. (CHI 2025) present CodeA11y, primarily a tool-building paper: they build a GitHub Copilot extension that nudges developers toward accessible code, and evaluate it through a formative study (16 developers) and a controlled evaluation (20 developers). The motivating concern we draw on is their *formative* finding — that, without such intervention, AI coding assistants do not produce more accessible code than developers achieve unaided, and in several conditions produce less. Our contribution is orthogonal in design: where CodeA11y intervenes at the moment of *generation* and measures the effect in a controlled user study, we study the phenomenon *longitudinally and causally* in real repositories over months of evolution, capturing whatever review, refactoring, and accumulation processes operate in practice.

He, Huq, and Malek (2025) build GenA11y, an LLM-powered accessibility-violation detector that substantially outperforms rule-based tools at finding issues in existing websites. GenA11y is a *detection* advance; it does not study whether AI coding tools *cause* accessibility regressions in newly generated code, nor does it provide longitudinal or causal analysis. The distinction defines our contribution and also frames a measurement caveat we inherit (Section 3.6): rule-based detection — including the axe-core engine we use as a primary outcome — covers only a subset of WCAG criteria, which is one reason we pair it with a render-independent AST metric.

### 2.5 Static Analysis for Frontend Quality

AST-based analysis of React component quality has been applied to maintainability and naming-convention enforcement. Semantic-HTML correctness — using structurally appropriate elements (`<button>`, `<nav>`, `<ul>/<li>`) rather than generic `<div>` containers — is comparatively under-studied empirically. Our AST-based semantic score operationalises this dimension as a complementary metric to runtime axe-core analysis, capturing violations that appear after static parsing rather than after rendering. This matters methodologically: 60.4% of component-snapshot pairs in our panel fail to render under a headless pipeline (Section 3.6.1), so a render-independent metric with 100% coverage is not a luxury but a necessity for an unbiased panel. The right-censored distribution of this score (24.2% of observations at the ceiling of 1.0 on the matched panel) motivates the Tobit robustness check of Section 4.


---

## 3. Study Design

**Relationship to prior work.** This manuscript draws on two earlier analyses by the author — a mean-effect empirical study and a companion stochastic-dynamics analysis — neither of which has been published or is under review elsewhere; both are available from the author on request and are not cited as formal references. The present manuscript is self-contained: it re-derives every reported number from the shared replication package (the originating database and analysis scripts archived with this paper), so no reader needs the earlier drafts to assess any result here. What is new relative to those drafts is the unifying methodological framing and protocol (Section 6), the Monte Carlo size-distortion study (Section 6.1), the heterogeneity-robust staggered-DiD re-estimation (Section 4.2), the equivalence (TOST) and multiplicity analyses (Sections 4.2, 4.5), the multi-rater construct-validation (Appendix D), the cluster-robust re-analysis of the negative control (Section 5.6), and the control-arm robustness analysis (Section 8.1).

### 3.1 Research Questions

We investigate five research questions. RQ1–RQ4 concern the *mean* effect of adoption on the four measured accessibility axes; RQ5 concerns the *dynamics* (does the generative process change even where the mean does not), examined as a secondary axis.

- **RQ1.** Does AI-tool adoption causally increase static, source-detectable accessibility violation density (WCAG-category and severity-weighted) in React/TypeScript repositories?
- **RQ2.** Does AI-tool adoption degrade AST-based semantic-HTML correctness?
- **RQ3.** Are post-treatment effects concentrated in specific violation categories (semantic naming, ARIA, document structure)?
- **RQ4.** Do accessibility violations accumulate or decay over time following AI-tool adoption?
- **RQ5.** Does AI-tool adoption reshape the *stochastic dynamics* of accessibility quality — its volatility, the persistence of degraded states, and upper-tail risk — even where the mean is unchanged? (We also posed the introduction-versus-removal balance, the utilization ρ = λ/μ, as part of RQ5, but report in §5.5 that it is not identifiable at monthly cadence.)

### 3.2 Identification Strategy

Adoption in our panel is **staggered**: repos adopt AI tooling at different calendar months (this is the basis of our Tier-1 treatment-date assignment, Section 3.3). It is now well established that the two-way fixed-effects (TWFE) DiD estimator is biased under staggered timing whenever treatment effects are heterogeneous across cohorts or over time, because already-treated units enter as effective controls for later-treated units — the "forbidden comparisons" of Goodman-Bacon (2021), de Chaisemartin and D'Haultfœuille (2020), Callaway and Sant'Anna (2021), Sun and Abraham (2021), and Borusyak, Jaravel, and Spiess (2024). The framework we extend (He, Miller, et al. 2026) confronts this directly, reporting TWFE alongside heterogeneity-robust estimators. We therefore do **not** rely on TWFE as the primary estimator; we report it for comparability and treat the heterogeneity-robust estimators as primary.

The canonical TWFE specification, retained for comparability, is

$$y_{it} = \alpha_i + \gamma_t + \beta \cdot (\text{Treated}_i \times \text{Post}_{it}) + X_{it}\delta + \varepsilon_{it},$$

where $\alpha_i$ and $\gamma_t$ are repo and calendar-month fixed effects; $\beta$ is the DiD estimator; $X_{it}$ is a vector of time-varying controls (`history_months`, `tsx_file_count`); and standard errors are clustered at the repository level.

To neutralise the staggered-timing bias we additionally estimate the ATT with modern heterogeneity-robust estimators, mirroring the template of the framework we extend. The propensity-matched controls (86 in the primary matched panel; 257 in the full panel) are coded as **never-treated** and form the clean comparison backbone (the inherited placebo treatment date used to form the TWFE pre/post indicator is discarded for these estimators):

- **Borusyak, Jaravel, and Spiess (2024)** imputation estimator, which fits the untreated potential outcome (repo + month fixed effects) on never-/not-yet-treated cells and averages the treated-post residual, with repo-level block-bootstrap inference.
- **Sun and Abraham (2021)** interaction-weighted event study, giving cohort-uncontaminated dynamic coefficients against never-treated controls in place of the raw TWFE event study.

We further report a **Goodman-Bacon (2021)** decomposition of the comparison structure to show how much of the TWFE estimate rests on clean (treated-vs-never-treated) versus forbidden (later-vs-earlier-treated) comparisons. Because our design carries a dedicated never-treated control arm, the clean comparisons dominate (92.5%; Section 4.2). The dynamics analysis of Section 5 conditions on this same identified design — it inherits the panel, the treatment-date assignment, and the parallel-trends justification, and asks a difference-in-*dynamics* question rather than a difference-in-means one.

The parallel-trends assumption requires that, absent treatment, treated and control repos would have followed the same trajectory. We test it with a joint F-test on pre-treatment event-study coefficients at $k = -6, -3, -2$ months (specified in advance in our analysis plan), and we read the **Sun–Abraham** event study (cohort-uncontaminated) for $k \in [-12, +12]$ months relative to treatment, using $k = -1$ as the reference period (RQ4).

### 3.3 Treatment-Date Identification

Treatment dates are assigned using a signal hierarchy:

- **Tier 1 (confidence 0.90):** first appearance of AI-tool config artifacts — `.cursor/`, `.cursorrules`, `.github/copilot-instructions.md`, or VSCode settings containing `github.copilot.*`.
- **Tier 2 (confidence 0.75):** first `Co-authored-by: copilot@github.com` commit trailer.
- **Tier 3 (confidence 0.40):** comment-density inflection — **excluded from all analyses.**

A repository is treated if it carries **any** detected adoption signal (Tier 1 or Tier 2); Tier 3 (comment-density inflection) is too weak a proxy and is excluded entirely. We do not impose a confidence cut beyond that — every treated repository has a concrete artifact, co-author trailer, or commit-message signal — and we report a robustness specification restricted to the unambiguous hard-configuration (Tier-1) adopters in Section 4.6.

### 3.4 Repository Selection and Matching

React/TypeScript repositories were collected from GitHub satisfying: (1) ≥12 months of snapshot coverage; (2) ≥100 analyzed component rows; (3) ≥60% TypeScript/TSX files. Of 602 fully-qualified repositories, the scale-up measured **497** (193 treated, 304 control candidates) on the static analyzer of Section 3.6. For the primary identification panel we propensity-match controls to treated by 1:1 nearest-neighbour (caliper on the PS logit) on `history_months`, `tsx_file_count`, and `contributor_count` (log-scaled); each matched control inherits its treated pair's adoption month as a placebo. Matching reduces all standardised covariate differences from > 1.0 pre-match to ≤ 0.18 post-match. The full 446-repo panel (controls assigned placebo dates, repo + month fixed effects absorbing arm-level differences) serves as a large-N robustness check throughout.

### 3.5 Attrition Flow

Table 1 documents the attrition from qualification to the two analysis panels.

**Table 1. Sample attrition flow (enriched study).**

| Stage | Treated | Control | Total | Reason for loss |
|---|---:|---:|---:|---|
| Fully qualified | 244 | 358 | 602 | passed all qualification gates |
| Stage 4: measured | 193 | 304 | 497 | runtime cap on collection |
| Inclusion gate (≥12 mo, ≥100 rows) | 189 | 257 | 446 | coverage threshold → **full panel** |
| PSM matched (primary panel) | 95 | 86 | 181 | 1:1 caliper common support |

### 3.6 Outcome Metrics

*A note on sample sizes and measurement.* The scaled study comprises **446 repositories and 13,702 repo-months** (matched primary subset: 181 repos / 5,956 repo-months). All accessibility axes are computed by a single render-independent static analyzer (Section 3.6) that achieves **100% component coverage** — there is no differential missingness across axes, because every component is parsed identically. This is a deliberate change from runtime axe-core measurement, which fails to render ≈60% of components; the static analyzer removes that bias and the memory/timeout fragility that capped the original collection.

#### 3.6.1 A render-independent, five-axis static analyzer

We measure *source-detectable* accessibility by parsing each component's TSX/JSX via a TypeScript AST and computing five candidate axes directly from the syntax tree — no rendering, no browser, deterministic, and covering **100% of components**. This replaces the original study's runtime axe-core / jsdom pipeline, which failed to render ≈ 60% of components (missing context providers, unavailable browser APIs) and introduced both a coverage bias and the memory/timeout fragility that capped collection. We are explicit that this instrument sees accessibility properties *present in source* — semantic structure, keyboard affordances, ARIA usage — and cannot see runtime properties such as computed colour contrast or live focus order; Section 7 returns to this scope. The five candidate axes are:

1. **Semantic-HTML correctness** ($[0,1]$, higher better): deductions for interactive `<div>`/`<span>` used in place of semantic elements (`<button>`, `<nav>`, `<ul>/<li>`), and for missing `alt`/labels.
2. **WCAG-category violation density** (per element): static violations bucketed by WCAG principle — perceivable, operable, understandable, robust — so any effect can be localised to a principle.
3. **Severity-weighted violation density**: the same violations weighted 3/2/1 by critical/serious/moderate impact.
4. **Keyboard/focus operability** ($[0,1]$): penalises custom-interactive elements with a click handler but no keyboard handler, positive `tabIndex`, and interactive elements that are not focusable.
5. **ARIA correctness** ($[0,1]$): invalid roles, missing role-required attributes, redundant roles.

Of these five, the first four exhibit usable cross-repository variation and are modelled as the study's outcome axes. The fifth, ARIA correctness, is near-constant in this corpus (mean ≈ 0.9997, near-zero variance; almost no repository introduces invalid or malformed roles in component source), so it carries no identifying variation for a DiD and we report it descriptively as **"no detectable ARIA-role variation"** rather than estimating a treatment effect on it. The headline therefore concerns **four measured axes**.

The semantic-HTML axis is construct-validated against four independent expert raters in Appendix D. The WCAG-category split also serves as the heterogeneity analysis (Section 4.5).

### 3.7 WCAG Principle Categories

The WCAG-category axis buckets static violations by the four WCAG principles — perceivable, operable, understandable, robust — following the axe-core rule-to-principle mapping. Operable (keyboard, focus, interactive naming) and robust (name-role-value, valid ARIA) carry most of the detectable mass in React/TypeScript component code.

**Table 2. Mapping of static violation checks to WCAG-category buckets.**

| Category | Axe-core rules |
|---|---|
| `semantic_naming` | button-name, label, link-name, image-alt, select-name, document-title, frame-title, role-img-alt |
| `aria_specific` | aria-command-name, aria-required-parent, aria-required-attr, aria-allowed-attr, aria-dialog-name, aria-input-field-name, aria-tooltip-name, aria-treeitem-name, aria-roles |
| `document_structure` | listitem, list, html-has-lang, dlitem, nested-interactive, duplicate-id-active |

---

## 4. Mean Effects

### 4.1 Propensity-Score-Matching Balance

Table 3 reports standardised mean differences before and after matching. All covariates achieve `std_diff` < 0.16 post-match. The pre-match imbalance on `contributor_count` (std_diff = 1.10) — AI-adopting repos skew toward larger, more active projects — is corrected to 0.04 post-match, confirming that matching removes the principal selection confound.

**Table 3. PSM covariate balance.** Pre-match values exceeding the std_diff = 0.25 threshold are corrected post-match.

| Covariate | Treated (pre) | Control (pre) | Std diff (pre) | Treated (post) | Control (post) | Std diff (post) |
|---|---:|---:|---:|---:|---:|---:|
| history_months | 80.36 | 60.06 | 0.734 | 79.61 | 75.33 | 0.151 |
| tsx_file_count | 209.91 | 159.90 | 0.330 | 182.52 | 207.53 | 0.136 |
| contributor_count | 59.92 | 24.29 | 1.097 | 52.06 | 50.62 | 0.042 |
| commit_frequency | 4240.66 | 1051.03 | 0.587 | 1858.91 | 1822.75 | 0.009 |

### 4.2 Primary DiD Results (RQ1 and RQ2)

We estimate each of the four measured accessibility axes under the TWFE and Borusyak–Jaravel–Spiess (BJS) imputation estimators, on the matched primary panel (181 repos / 95 treated / 86 control) and the full robustness panel (446 repos / 189 treated / 257 control, TWFE absorbing repo+month fixed effects). Inference is repo-clustered, with a restricted wild-cluster bootstrap (Rademacher weights, B = 399) reported because the matched panel is in the small-cluster regime. Score axes (semantic, keyboard) run 0–1 with higher = better; violation-density axes (WCAG, severity) are per-element with higher = worse.

**Table 4. Primary DiD estimates — four measured accessibility axes, matched panel (181 repos).** ATT in native units; "% base" = ATT relative to the pre-treatment treated mean. (ARIA correctness is omitted: near-constant in the corpus, no identifying variation.)

| Axis | TWFE ATT | SE | analytic p | wild-cluster p | BJS ATT | % base |
|---|---:|---:|---:|---:|---:|---:|
| Semantic HTML | −0.0043 | 0.0040 | 0.285 | 0.357 | −0.0031 | −0.5% |
| Keyboard/focus | −0.0016 | 0.0037 | 0.658 | 0.688 | −0.0011 | −0.2% |
| WCAG total density | −0.0016 | 0.0023 | 0.493 | 0.520 | −0.0015 | −4.6% |
| WCAG operable density | −0.0016 | 0.0019 | 0.414 | 0.435 | −0.0018 | −8.6% |
| Severity-weighted | −0.0029 | 0.0048 | 0.552 | 0.565 | −0.0022 | −3.6% |

**Table 4a. Robustness — same four axes, full panel (446 repos, 13,702 repo-months).**

| Axis | TWFE ATT | SE | analytic p | wild-cluster p | BJS ATT |
|---|---:|---:|---:|---:|---:|
| Semantic HTML | −0.0019 | 0.0023 | 0.408 | 0.440 | −0.0023 |
| Keyboard/focus | −0.0005 | 0.0020 | 0.815 | 0.830 | +0.0011 |
| WCAG total density | −0.0005 | 0.0014 | 0.698 | 0.698 | −0.0010 |
| WCAG operable density | −0.0003 | 0.0011 | 0.815 | 0.795 | −0.0017 |
| Severity-weighted | −0.0012 | 0.0030 | 0.693 | 0.725 | −0.0005 |

Across all four measured axes, both panels, and both estimators, **no ATT approaches significance** (every analytic and wild-cluster *p* > 0.28), and the point estimates are uniformly small and slightly negative — i.e. if anything, adoption is associated with marginally *fewer* accessibility issues, though never significantly. The wild-cluster *p*-values track the analytic values throughout, confirming the null is not an artifact of small-cluster asymptotics. The fifth candidate axis, ARIA correctness, is omitted from the tables because the static analyzer finds essentially no ARIA-role violations in this corpus (mean score 0.9997, near-zero variance); we report it as "no detectable ARIA-role variation" rather than fit a degenerate model. Figure 7 plots the per-axis ATTs (as % of baseline) with 95% CIs for both panels.

*Figure 7. Per-axis ATTs as a percentage of pre-treatment baseline, matched (181-repo) and full (446-repo) panels, with 95% CIs. All intervals span zero; the semantic-HTML and keyboard axes fall inside the ±5% equivalence band (shaded).*

**Control-arm validity.** A standing concern in any DiD is that the control arm behaves differently from treated for reasons unrelated to treatment. Treated and control repositories in the matched panel show comparable post-period coverage — a mean of 22.8 observed post-period repo-months for treated versus 20.2 for control (medians 23 and 21.5) — so the control group is not systematically less-active or under-observed and functions as a clean counterfactual.

**Equivalence: how small an effect can we exclude?** A null is only as informative as the effect sizes it rules out, so we restate it as a *positive* equivalence claim via two one-sided tests (TOST) against a smallest-effect-of-interest (SESOI) expressed as a percentage of each axis's pre-treatment treated baseline. Table 4b reports, per axis, the tightest bound at which equivalence is certified (*p*~TOST~ < 0.05).

**Table 4b. Equivalence (TOST) — tightest certifiable bound, as % of pre-treatment baseline.**

| Axis | Matched panel | Full panel |
|---|---:|---:|
| Semantic HTML | ±5% | ±5% |
| Keyboard/focus | ±5% | ±5% |
| WCAG total density | ±20% | ±15% |
| WCAG operable density | ±30% | ±20% |
| Severity-weighted | ±15% | ±10% |

This is the payoff of scale. On the two dense, high-baseline score axes (semantic HTML and keyboard/focus), we **statistically exclude any effect larger than ±5% of baseline** — an order of magnitude tighter than a small panel can support. The violation-density axes certify only at ±10–30%, and it is worth being precise about *why*, because the reason is not insufficient data. The equivalence bound is the confidence half-width expressed as a fraction of the pre-treatment baseline. The two score axes sit near 0.95, so their (already small) absolute half-widths are a tiny percentage of baseline. The density axes are **rare-event, zero-inflated counts** whose baseline means are near zero (e.g. WCAG-operable density ≈ 0.018; most components carry no violations at all): their *absolute* confidence half-widths are comparable to — in fact smaller than — those of the score axes, but dividing by a near-zero baseline inflates the *percentage* bound to ±10–30%. The looseness is therefore a property of the phenomenon (violations are rare, so there is little baseline to express an effect as a fraction of), not of statistical power. More repositories would help only at the usual $\sqrt{N}$ rate and would not change the underlying sparsity; the cleaner lever, pursued in the per-commit follow-up of Section 7.3, is finer temporal resolution that captures the within-month introduce-and-fix events the monthly snapshot averages away. In plain terms: AI-tool adoption produces no large regression on any axis, and not even a *modest* one along the dimensions where most components carry signal; on the rare-violation axes we can rule out large effects but not small ones, by the arithmetic of a near-zero baseline.

**A note on what underpins this result.** Because a DiD estimate is a difference of trends, it is sensitive to control-arm movement. On the enriched panel the arms start comparable on every axis (Appendix A) and show comparable post-period maintenance activity (§8.1), and the heterogeneity-robust estimators (Table 4a) — which difference treated changes against never-treated controls — agree with TWFE throughout, so the null does not rest on a treated–control cancellation. Where both arms drift together (e.g. the upper-tail decline of §6) the treated-vs-control contrast nets that shared movement out.

### 4.3 Parallel-Trends Test

On the enriched matched panel, the joint F-test on pre-treatment event-study coefficients at $k = -6, -3, -2$ (semantic-HTML axis) yields **F = 0.46 (3 df, p ≈ 0.71)** — no evidence against parallel trends, and a cleaner pre-period than the original small-panel study afforded. Figure 1 shows the pre-treatment $\hat\beta_k$ scattering tightly around zero with every 95% CI spanning it and no trend toward the treatment date. The larger, propensity-matched panel removes the small positive pre-period offset that the original study had to caveat: here the pre-trend is clean on its own terms.

*Figure 1. Pre-trend event study (enriched matched panel, semantic-HTML axis): pre-treatment event-study coefficients $\hat\beta_k$ scatter around zero with all 95% CIs spanning zero; joint F-test on $k=-6,-3,-2$ does not reject parallel trends (F = 0.46, 3 df, p ≈ 0.71).*

### 4.4 Dynamic DiD Over Time (RQ4)

The full event study ($k \in [-12, +12]$, semantic-HTML axis, Figure 2) shows no treatment-induced accumulation: the coefficients stay near zero throughout the post-period, with a slight downward drift to $\hat\beta_{+12} \approx -0.010$ (i.e. if anything marginally *fewer* semantic issues) that no individual bin renders significant. The other axes behave identically. There is no evidence of accessibility debt accumulating over the twelve post-treatment months.

*Figure 2. Dynamic DiD event study, enriched matched panel (semantic-HTML axis), $k \in [-12, +12]$ months relative to adoption; all coefficients near zero, none individually significant.*

### 4.5 Multiplicity Across the Measured Axes

We apply a Benjamini–Hochberg correction across the family of axis-level TWFE *p*-values (matched panel; the WCAG-density axis enters as both its total and operable forms, giving five tested *p*-values). The smallest raw *p* is 0.285 (semantic HTML); every BH-adjusted *q* equals **0.658**, so no axis is remotely close to the corrected bar. Multiplicity here only reinforces the null — adding axes to a family of uniformly null results cannot manufacture a rejection — so "no corrected-significant effect on any accessibility axis" is robust to the number of axes examined. The WCAG-category split (perceivable / operable / understandable / robust) functions as the heterogeneity analysis: no principle shows an effect, and the operable axis (which subsumes keyboard and structure) is the one a future study should keep watching, as it carries the most violation mass.

**Table 5. Benjamini–Hochberg multiplicity correction across the measured accessibility axes** (matched panel, TWFE *p*; the WCAG-density axis is shown as both its total and its operable sub-axis, giving five tested *p*-values).

| Axis | *p* | BH *q* | significant at .05? |
|---|---:|---:|:--:|
| Semantic HTML | 0.285 | 0.658 | no |
| Keyboard/focus | 0.658 | 0.658 | no |
| WCAG total density | 0.493 | 0.658 | no |
| WCAG operable density | 0.414 | 0.658 | no |
| Severity-weighted | 0.552 | 0.658 | no |

### 4.6 Robustness Checks

The null is stable across alternative specifications of the semantic-HTML axis on the matched panel (Table 6); the other axes behave identically and are in the replication package.

**Table 6. Robustness checks (semantic-HTML axis, matched panel).**

| Specification | TWFE ATT | p |
|---|---:|---:|
| Main specification | −0.0043 | 0.285 |
| Shift treatment −1 month | −0.0039 | 0.345 |
| Shift treatment +1 month | −0.0053 | 0.168 |
| Drop repos with <18 months coverage | −0.0042 | 0.293 |
| Tier-1 (hard-config) treated only | −0.0010 | 0.897 |

The result survives ±1-month treatment-date shifts and dropping short-history repos. As a further check we restrict the treated arm to the repositories with *hard configuration-artifact* adoption signals (the most unambiguous adopters); the estimate stays near zero (β = −0.001, p = 0.90), though we note this subset is small (n = 10 treated) and so the check is directionally consistent but low-powered rather than confirmatory. No specification produces a significant effect in either direction.

All five specifications return qualitatively identical (null) results, with every point estimate small and negative and no *p* below 0.16. The null does not depend on the exact treatment-date assignment, the coverage gate, or the strictness of the adoption-signal definition.

---

## 5. Dynamics: Does the Generative Process Change? (RQ5)

A null average treatment effect need not imply an unchanged generative process. Two regimes can share an expected value while differing in volatility, in the persistence of degraded states, in upper-tail risk, or in the balance of error introduction and removal. Section 4 left a loose thread that makes this concern concrete: the dynamic event study showed small, never-per-bin-significant post-treatment coefficients that wander on either side of zero (drifting to $\hat\beta_{+12} \approx -0.010$ on the semantic axis) rather than sitting flat — a near-zero mean that could nonetheless coexist with a changed *process*, exactly the possibility a difference-in-means cannot rule out. We test that possibility here.

We state the hypothesis up front, because the contribution of this section is to test it honestly:

> **H (dynamics hypothesis).** AI-tool adoption reshapes the stochastic dynamics of accessibility quality — its volatility, the persistence of degraded states, the heaviness of the upper tail, and the balance of violation introduction versus removal — even where the static mean is unchanged. Concretely, adoption raises the introduction rate relative to the fix rate, pushing the queueing utilization $\rho = \lambda/\mu$ toward and past the instability boundary $\rho = 1$, producing slow backlog accumulation visible to a dynamic event study but invisible to a difference-in-means.

The hypothesis is falsifiable, and the design fixed in advance the disposition of a null: if $\rho_\text{post} \approx \rho_\text{pre}$ and volatility/persistence are statistically indistinguishable, **H is rejected — and that is a publishable, honest result.** We report exactly that outcome.

### 5.1 Formal Models

We model each repo's monthly trajectory of WCAG violation density — one of the Section 4 axes. The panel is monthly: one snapshot per repo-month at that month's representative commit. The monthly resolution is a deliberate and consequential choice whose implications for the birth–death model we make explicit below and revisit in Section 8.

**State space.** We discretise violation density into ordered states using pooled quantiles of the combined pre+post distribution, balancing state occupancy. A material data feature constrains this: the violation-density axes are **zero-inflated** — depending on the axis, between 13% and 34% of repo-months sit at exactly zero violations (e.g. 34.3% on the WCAG-operable density axis). When the zero mass exceeds $1/k$ for a requested $k$-state partition, the lower pooled-quantile cutpoints coincide at zero and the partition collapses: on the operable axis a requested 4-state binning yields only 3 distinct occupied states and a 5-state request yields 4. We report 3- and 4-state partitions as the substantive specifications and treat the collapse as a property of a zero-inflated outcome. Critically, this collapse also creates a *phantom never-occupied state* that inflates the degrees of freedom of the Markov tests unless corrected; Section 5.2 documents the correction, which is essential to the validity of the test.

**Discrete-time Markov chain.** For each regime $r \in \{\text{pre}, \text{post}\}$ we estimate the transition matrix $P^{(r)}$ with entries $P_{ij} = \Pr(\text{state}_{t+1} = j \mid \text{state}_t = i)$ by closed-form maximum likelihood, $\hat P_{ij} = n_{ij} / \sum_k n_{ik}$, where $n_{ij}$ counts $i \to j$ transitions pooled across repos within the regime. Transitions are counted only between consecutive calendar months within a single regime for a single repo, so no transition straddles the adoption boundary or a coverage gap. From $\hat P$ we derive the stationary distribution $\pi$ ($\pi P = \pi$, $\sum \pi = 1$), persistence (self-transition $P_{ii}$, dwell time $1/(1 - P_{ii})$), and the spectral gap $1 - |\lambda_2|$ governing mixing speed. Under H, the post regime should mix more slowly (smaller gap).

**Birth–death process and utilization.** Let $N(t)$ be a repo's outstanding violation count at month $t$, evolving as a discrete-time birth–death process with regime-specific rates: introduction rate $\lambda$ (mean new violations introduced per repo-month, summed over files whose count rose between consecutive months) and removal rate $\mu$ (mean removed per repo-month, over files whose count fell). The utilization $\rho = \lambda/\mu$ is the object of interest. In the M/M/1 analogue, $\rho < 1$ yields a stationary geometric backlog with finite mean $\rho/(1-\rho)$; $\rho \ge 1$ yields unbounded accumulation. Under H, $\hat\rho_\text{post} > \hat\rho_\text{pre}$ and $\hat\rho_\text{post}$ crosses 1.

Two modelling-honesty points prove decisive. First, $\lambda$ and $\mu$ **must be normalised by the same exposure** (all repo-months) for $\rho = \lambda/\mu$ to be a well-defined rate ratio; an earlier version conditioned $\mu$ on a non-empty backlog while leaving $\lambda$ over all months — mismatched denominators that manufactured a spurious crossover (Section 6). Second, with one commit per month we cannot observe inter-event timing, so the continuous-time M/M/1 is an interpretive frame only; we estimate a discrete-time birth–death model and defer the continuous per-commit M/M/1 with goodness-of-fit to future work. We do not oversell M/M/1.

### 5.2 Estimation and Inference

The dynamics analysis runs on the same enriched matched panel (181 repos, 5,956 repo-months) as the mean analysis, using the WCAG violation-density axis as the state variable. Transitions are counted only between consecutive calendar months within a single regime for a single repo, so no transition straddles the adoption boundary or a coverage gap.

Transition matrices use the closed-form MLE. We run two likelihood-ratio tests — homogeneity ($H_0: P^\text{pre} = P^\text{post}$) and order (first vs. second) — **with degrees of freedom corrected for the state-occupancy degeneracy.** That the df of a Markov LR test should count only estimable parameters — i.e. reachable transitions among occupied states — is itself standard (the homogeneity and order LR tests follow Anderson and Goodman 1957); the textbook $n(n-1)$ (homogeneity) and $n(n-1)^2$ (order) are upper bounds that assume every nominal state is occupied with full reachable support. What is specific here, and what makes the correction a prerequisite rather than a refinement, is *why* the degeneracy arises and how severe it is: the outcome is **zero-inflated** in a way endemic to software-quality metrics — on the operable-density axis 34.3% of repo-months sit at exactly zero violations, comfortably above the $1/k$ threshold — so the lower pooled-quantile cutpoints collapse onto zero and a nominal $k$-state partition silently yields a *phantom never-occupied state* plus sparse rows (the requested 4-state partition occupies only 3 states; the 5-state request only 4). The uncorrected df then over-counts free parameters by a wide margin, and the consequence is not mild conservatism but **mechanical non-rejection**: at 4 states the uncorrected order-test df is 36, forcing $p \approx 1$ regardless of the data. We instead compute df from occupied support only — for homogeneity, the sum over "from" states present in both regimes of (reachable "to" columns − 1) — changing the homogeneity df from 6→2 (3-state) and 12→6 (4-state) on the collapsing axis. The contribution is therefore not the general principle (count estimable parameters) but the SE-panel diagnosis: zero-inflation in repository metrics induces this degeneracy *by construction* under quantile binning, it is easy to miss, and uncorrected it renders any Markov regime test on such data vacuous — so reporting it is necessary for the field, not a tuning choice for this paper.

> **Result 1 (zero-inflation df degeneracy under quantile binning).** Let an ordered-state Markov chain be formed by binning a zero-inflated outcome at pooled quantiles, with a fraction $z$ of observations at the lower bound. When $z$ exceeds $1/k$ for a requested $k$-state partition, two or more lower cutpoints coincide at the bound, so at least one nominal state is never occupied. The homogeneity/order likelihood-ratio tests computed with the textbook degrees of freedom $n(n-1)$ and $n(n-1)^2$ then over-count free parameters and the test is driven toward non-rejection ($p \to 1$ as the over-count grows). Counting df from occupied, reachable support only restores a valid test. In repository panels $z$ is routinely large (here $z = 0.343$ on the operable-density axis, so that $z > 1/4$ and the 4-state partition collapses), so this degeneracy is endemic and must be checked before any Markov regime test is interpreted.

All regime contrasts — the spectral-gap difference and the $\rho$ difference — receive 95% confidence intervals by **repo-level block bootstrap** (2,000 replicates, fixed seed), resampling whole repositories with replacement, never individual repo-months, respecting within-repo dependence (the same reason Section 4 clustered SEs at the repo level). A **negative control** applies the same Markov machinery to a stylistic metric — monthly component count (repo size) — for which adoption has no a-priori reason to alter dynamics (Section 5.6).

### 5.3 Transition Structure Is Statistically Unchanged

The chains are persistence-dominated — once in a violation-density band, a repo overwhelmingly stays there month to month (self-transition $P_{ii} = 0.94$–$0.99$, Table 7), as expected for slowly-changing quality at monthly cadence.

**Table 7. Self-transition probabilities $P_{ii}$ on the violation-density state variable, by regime.** States are quantile bands of monthly WCAG violation density (S1 = lowest/near-zero violations, ascending). The diagonals rise on every occupied state from pre to post, the signature of the increased persistence reported in Section 5.4. (At the 4-state binning of a zero-inflated outcome the lowest quantile cutpoints can coincide at zero, collapsing the support and reducing the effective degrees of freedom; this is the mechanism behind Result 1, Section 5.2.)

| States | Regime | $P_{11}$ | $P_{22}$ | $P_{33}$ | $P_{44}$ |
|---:|---|---:|---:|---:|---:|
| 3 | pre | 0.946 | 0.931 | 0.974 | — |
| 3 | post | 0.982 | 0.968 | 0.983 | — |
| 4 | pre | 0.939 | 0.921 | 0.916 | 0.957 |
| 4 | post | 0.969 | 0.974 | 0.967 | 0.978 |

On the enriched panel the likelihood-ratio homogeneity test (df corrected for occupied support) returns **LR = 50.8, df = 11, p < 0.001** — the transition structure does differ by regime, consistent with the spectral-gap shift of Section 5.4. (This test is run on the total violation-density axis, whose 13.4% zero mass does *not* trigger the cutpoint collapse, so all four states are occupied and df = 11; the more severe collapse illustrated in Section 5.2 — df 12 → 6 — arises on the sparser operable axis, where the 34.3% zero mass exceeds the $1/k$ threshold.) We are careful, however, not to over-read the LR *magnitude*: on a 13,702-repo-month panel the homogeneity LR is highly powered and would flag even cell-probability differences too small to matter, so the honest summary is not the LR *p*-value but the *direction and effect size* of the change — a uniform, bootstrap-significant rise in self-transition persistence (Table 7, §5.4), not a reshuffling of where mass sits. This hypersensitivity of the large-$N$ homogeneity test is itself a methodological point we restate in the checklist (Section 6).

*Figure 3. Pre- vs. post-adoption 4-state transition matrices on the violation-density state variable. Self-transition mass (the diagonal) increases post-adoption on every occupied state, the visual counterpart of the spectral-gap contraction (0.036 → 0.017) reported in Section 5.4; off-diagonal (state-changing) mass correspondingly thins.*

**An assumption that does not cleanly hold, and what it does to this claim.** We must confront here, not defer to threats, that the first-order Markov assumption holds unevenly across specifications. The likelihood-ratio order test (first vs. second order, df corrected for occupied support) gives, by state count and regime: 3-state pre p = 0.0003 (rejects), post p = 0.739 (does not); 4-state pre p = 0.206, post p = 0.0925 (neither rejects at α = .05); 5-request→4-state pre p = 0.007, post p = 0.0009 (both reject). So at the 4-state specification we report as primary, first-order Markovianity is *not* rejected in either regime, but at finer/coarser binnings it is rejected in the pre regime (and, at 5→4, both). The honest consequence is twofold. *Negatively:* if the true process is higher-order, the estimated $P$ is a first-order *projection* of the dynamics, so the homogeneity test compares two projections rather than the full processes — it can only license the claim "the first-order monthly transition structure does not differ by regime," not the stronger "the dynamics are identical." We adopt the weaker claim throughout and have revised the Abstract and contribution wording accordingly. *Mitigatingly:* a difference in higher-order structure that left the first-order projection, the stationary distribution (Section 5.4), the variance (Section 5.5), and the tail DiD (Section 6) all simultaneously null would be an unusual and narrow form of regime change. We are careful not to overstate this: these moments are computed from the *same* panel and are not statistically independent, so their agreement is not several independent confirmations. But they are sensitive to *different* features of the dynamics (persistence, mixing, spread, tail mass), so their convergence on "no difference" is still more informative than any single first-order test. The first-order rejection bounds the *strength* of the dynamics null without overturning its *direction*, and we return to it in Section 8.4.

### 5.4 Persistence and Mixing: A Small but Robust Increase in State Persistence

This is the one beyond-mean facet where the data show a real, sign-consistent treatment-associated difference, and we report it carefully. On the violation-density state variable (Section 5.2), the spectral gap — $1 - |\lambda_2|$, the second-eigenvalue mixing rate, where *smaller = slower mixing = stickier states* — shrinks post-adoption from **0.036 to 0.017**, a difference of **−0.019** whose repo-level block-bootstrap 95% CI of **[−0.031, −0.007]** (2,000 replicates, whole repositories resampled) excludes zero. The mechanism is visible in the transition diagonals (Table 7), which rise on **every** occupied state post-adoption: the four 4-state self-transition probabilities go 0.94 → 0.97, 0.92 → 0.97, 0.92 → 0.97, and 0.96 → 0.98. Repositories become **more likely to remain in their current accessibility-quality band from one month to the next** after adopting AI tooling. The effect is directionally robust — negative across the 3- and 4-state binnings and the full panel — and it is not a window-length artifact: post-adoption windows are if anything longer, so a longer window cannot manufacture *more* persistence.

We are deliberate about how much weight this carries. First, it is strictly a **second-order** effect: the *level* of accessibility quality is null on every axis (Section 4), so this is a change in the *persistence* of quality states, not in their quality. Both regimes describe a highly persistent, slow-mixing process; adoption moves it from "very sticky" to "slightly stickier." Second, the natural and benign reading is *less month-to-month churn* — AI-assisted repositories settle into a more stable component structure, for better or worse, rather than drifting toward better or worse accessibility. We had pre-registered this exact direction under hypothesis H (slower post-adoption mixing), so it is a confirmed prediction rather than a post-hoc discovery, but we flag it as the single dynamics signal worth following up at finer (per-commit) resolution and are explicit that it leaves the level null entirely intact. We do **not** read it as evidence of harm or benefit to accessibility, only of reduced volatility in the *path* a repository takes.

### 5.5 Volatility Unchanged; and a Withdrawn Utilization Conjecture

**Volatility.** On the enriched panel, variance of the semantic-HTML axis is essentially flat across regimes ($\sigma^2_\text{pre} = 0.0058$, $\sigma^2_\text{post} = 0.0068$); the Brown–Forsythe test gives $W = 1.71$ (not significant). No change in overall volatility.

**A birth–death utilization model, and why we withdraw it.** We also modelled each repo's monthly trajectory as a discrete-time birth–death process with introduction rate $\lambda$ and removal rate $\mu$, and considered the utilization $\rho = \lambda/\mu$. The monthly estimates are $\hat\rho_\text{pre} = 1.52$, $\hat\rho_\text{post} = 1.56$ — both above 1, which taken literally would imply unbounded backlog growth even though the backlog is flat-to-declining (0.091 → 0.082). This internal contradiction signals that the *level* of $\hat\rho$ is biased upward by the monthly cadence: any violation introduced and fixed within the same inter-snapshot interval nets to zero and is invisible, so observed removals are truncated relative to introductions.

We initially argued that this level bias is multiplicative and therefore **cancels in the pre/post contrast**, which would license using $\hat\rho_\text{post} - \hat\rho_\text{pre}$ as a valid regime comparison even though the absolute level is untrustworthy. Following the same discipline this paper recommends — do not trust a convenient cancellation argued only verbally; simulate it — we built a synthetic continuous-time birth–death panel with a *known* ground-truth $\rho_\text{pre} = 0.60$ and $\rho_\text{post} = 0.78$ (true contrast +0.18), observed it only through monthly net diffs, and checked whether the estimated contrast recovers the truth. **It does not.** The level bias is confirmed (estimated $\hat\rho$ inflates to 1.1–1.7 as within-month churn rises), but the contrast is *also* biased — the estimated contrast lands at +0.57 to +0.82 against a true +0.18 — because the truncation factor depends on each regime's event rate and so differs between regimes, and a regime-dependent factor does not cancel in any contrast formulation (difference, ratio, or log). Figure 4 shows this.

We therefore **withdraw the cancellation claim and drop the queueing/utilization analysis from the substantive findings.** The monthly birth–death model is unreliable for *both* the level and the contrast at this cadence; recovering it would require sub-monthly snapshots, which this panel does not have. We report the refutation rather than quietly deleting it because surfacing a conjecture our own simulation overturned is exactly the self-correction this paper advocates — and because the broader lesson (an aggregation artifact whose convenient cancellation fails under a realistic process) is itself worth recording. The RQ5 utilization facet is thus *not estimable* at monthly resolution, not "null."

*Figure 4. Simulated refutation of the utilization-cancellation conjecture. Synthetic birth–death panel with known $\rho_\text{pre}=0.60$, $\rho_\text{post}=0.78$ (true contrast +0.18), observed only via monthly net diffs. (a) The estimated level $\hat\rho$ is biased far above the truth and grows with within-month churn. (b) The estimated regime contrast is also biased (≈ +0.6–0.8 vs. true +0.18) — the truncation factor differs by regime, so it does not cancel. The monthly birth–death model is therefore invalid for both level and contrast, and we withdraw it.*

### 5.6 Negative Control

Applying the Markov homogeneity machinery to the stylistic component-count (repo-size) state gives LR = 15.76, df = 7, with a *naive unclustered* $\chi^2$ p = 0.027 — apparently weakly significant. But this is the paper's own thesis turned on itself: the $\chi^2$ reference distribution assumes independent transitions, which within-repo dependence violates, so we must not read the unclustered p. Applying the **same repo-level block bootstrap** used throughout (2,000 replicates) settles it. Under repo-resampling, the homogeneity LR statistic exceeds the naive $\chi^2_{.95}$ critical value (14.07) **60.9% of the time** — where a valid test would do so ≈5%. The observed LR (15.76, bootstrap 95% CI [5.25, 35.95]) sits comfortably inside that null spread. The nominal p = 0.027 is therefore an artifact of ignoring clustering, not evidence of a repo-size regime difference: **under cluster-robust inference the negative control is clean.** This is not merely reassuring for the negative control — it is a third in-paper demonstration (alongside the tail test of Section 6 and the general argument of Section 5.2) that unclustered tests on this panel are severely anti-conservative, which is the methodological point of the paper.

### 5.7 Summary of the Dynamics Analysis

| Beyond-mean facet | Statistic | Verdict |
|---|---|---|
| Volatility increased? | Brown–Forsythe W = 1.71 (n.s.) | Null |
| Upper-tail risk increased? | DiD p = 0.933 (naive pooled p = 0.003 reverses, §6) | Null |
| **State persistence increased?** | **spectral gap 0.036 → 0.017, diff −0.019, 95% CI [−0.031, −0.007]** | **Small but robust second-order effect** |
| Utilization $\rho$ raised toward instability? | model refuted by simulation (§5.5) | Not estimable at monthly cadence |

The *level* of accessibility quality is unchanged on every axis and at every estimable moment, as is its volatility and its upper-tail risk. The one beyond-mean facet that does move is **state persistence**: post-adoption quality states are stickier (slower-mixing chains, spectral gap halved, CI excluding zero, §5.4), a small and benign second-order effect that leaves the level null intact — repositories churn *less* month to month without ending up better or worse. The precise statement is therefore: AI-tool adoption changes neither the level of accessibility quality nor its variance or tail risk, but is associated with a modest, robustly-estimated increase in the month-to-month persistence of whatever quality state a repository occupies — a difference in *churn*, not in *quality*. The introduction-versus-removal balance (utilization $\rho$) is not estimable at monthly cadence (§5.5) and is the clearest target for the per-commit follow-up of Section 7.3.

---

## 6. The Methodological By-Product: A Quantified Failure Mode, Two Worked Artifacts, and a Checklist

Reaching the bounded null of Sections 4–5 meant not being fooled by distributional tests on a clustered, zero-inflated panel — where a naive analysis and the correct analysis diverge sharply, and where the gap between them is itself instructive. This section is the transferable by-product, not the headline: we first *quantify* the failure mode by simulation (§6.1), exhibit it twice on the real panel (§6.2–§6.5), and distil the lesson into a short checklist (§6.6).

### 6.1 The Failure Mode, Quantified by Simulation

Before exhibiting the artifact on our own data, we measure how badly the naive test fails on data where the truth is known. We simulate synthetic panels that share the structure of repository data — repos split treated/control, ~30 months each, a zero-inflation mass calibrated to the violation-density axes (≈ 0.13–0.34), tail-event propensity that varies between repos (so a few "heavy" repos own most exceedances, as in the real panel), and **no treatment effect injected.** Every rejection is therefore a false positive. We compare two tests: the naive pooled pre/post two-proportion z-test on tail exceedance, and the cluster-robust treated-vs-control DiD logit. We sweep two structural features and report the empirical false-positive rate over 400 replications per cell (Table 8; Figure 6).

**Table 8. Empirical false-positive rate at nominal α = 0.05 under a true null.** Panel (a) varies within-repo tail concentration (ICC) with no common trend; panel (b) adds a common secular trend affecting *both* arms equally (parallel trends hold; differential effect exactly zero).

| Mechanism | parameter | naive pooled test | cluster-robust DiD |
|---|---|---:|---:|
| (a) tail concentration | ICC = 0.1 | 0.052 | 0.058 |
| (a) tail concentration | ICC = 0.3 | 0.052 | 0.062 |
| (a) tail concentration | ICC = 0.5 | 0.043 | 0.060 |
| (a) tail concentration | ICC = 0.7 | 0.048 | 0.055 |
| (b) common secular trend | +5 pp | **0.555** | 0.060 |
| (b) common secular trend | +10 pp | **0.988** | 0.060 |
| (b) common secular trend | +15 pp | **1.000** | 0.058 |
| (b) common secular trend | +20 pp | **0.993** | 0.075 |

Two lessons, one of them counter-intuitive. First, within-repo concentration *alone* (panel a) does **not** inflate the naive test's size — both tests sit near 5%. The often-assumed culprit (clustering of the rare event) is not, by itself, what breaks the pooled test here. Second, the actual culprit is the **missing treated-vs-control contrast** (panel b): when a secular calendar trend lifts *both* arms equally — so the true differential treatment effect is exactly zero — the naive pooled test, which has no control contrast, reads the common trend as a "post" effect and rejects a true null **55% of the time at a 5 pp trend, rising to ~100% by 10 pp.** The cluster-robust DiD nets the common trend out and holds nominal size (≈ 5–6%) throughout. This is precisely the mechanism behind the *p* = 0.003 artifact we exhibit next: the control arm moved, and the pooled test had no way to tell that apart from an AI effect.

*Figure 6. Size of the naive pooled tail test vs. the cluster-robust DiD under a true null, on synthetic zero-inflated, repo-clustered panels: (a) vs. within-repo tail concentration; (b) vs. a common secular trend affecting both arms. The naive test's false-positive rate reaches ~100% under a common trend; the DiD holds nominal size.*

### 6.2 The Naive Result on the Real Panel

A natural test of the tail-risk facet pools all post-adoption repo-months against all pre-adoption repo-months and applies a two-proportion z-test on exceedance of the pooled 90th percentile of WCAG violation density. On the enriched panel this gives a pooled pre-vs-post difference significant at **$p = 0.003$** — apparently strong evidence of a shift in the upper tail of accessibility-violation density. Reported alone, this is a publishable positive finding. It is an artifact, for the two reasons the simulation just isolated.

### 6.3 Why It Is Invalid

**1. Within-repo clustering.** Repo-months are not independent Bernoulli trials. Tail exceedances are concentrated in a handful of repositories — the top five account for roughly half of all exceedances — inducing strong positive intra-class correlation and a large design effect. A z-test assuming independence badly understates the standard error and manufactures significance.

**2. Treated/control confounding.** The pooled `is_post` indicator mixes treated and control repositories, whose composition differs across the pre/post windows. Any secular calendar-time trend in the *control* group is misattributed to "adoption." The pooled test has no treated-versus-control contrast at all — it is not a test of an AI-specific effect.

The correct test of an AI-specific dynamic effect is a **difference-in-differences on tail exceedance** — a logistic regression `tail ~ post + treated + post:treated` whose interaction coefficient isolates the treated-group change net of the control trend — with standard errors clustered by repository.

### 6.4 The Reversal

Disaggregating by treatment group reveals that the pooled signal is a control-group phenomenon, not an AI effect:

**Table 9. Upper-tail exceedance rates (WCAG violation density > $q_{90}$), by group and period (enriched panel).**

| Group | Pre | Post | Change |
|---|---:|---:|---:|
| AI-treated | 0.098 | 0.080 | −0.018 |
| Control | 0.130 | 0.106 | −0.024 |
| **DiD (treated − control)** | | | **+0.006** (repo-clustered, $p = 0.933$) |

Both arms' tail rates *decline* over the post-period, the control arm slightly more, so a pooled pre/post test — which has no treated-vs-control contrast — registers the shared decline as a "significant" change ($p = 0.003$). The proper difference-in-differences with repo-clustered standard errors gives an interaction of **+0.006, $p = 0.933$** (Figure 5): once the treated-versus-control contrast and within-repo clustering are respected, there is **no AI-specific tail effect.** A pooled $p = 0.003$ evaporates to a clean null under the analysis the panel structure demands — the same reversal we documented on the original data, now reproduced on a six-times-larger panel.

*Figure 5. Tail-exceedance $P(\text{density} > q_{90})$ by treatment group and period: the AI-treated rate declines while the control rate rises sharply, so the naive pooled increase is entirely a control-group secular effect.*

### 6.5 A Second Artifact: The Utilization Crossover

The tail test is not the only too-good-to-be-true result this study stress-tested out of existence. An earlier version of the birth–death analysis reported $\hat\rho_\text{pre} = 0.80$ and $\hat\rho_\text{post} = 1.19$ — a clean *subcritical → supercritical crossover* that would have been strong, mechanistically appealing support for harm (adoption pushing the accessibility-debt queue past instability). It was a bug: $\mu$ had been conditioned on a non-empty backlog while $\lambda$ was normalised over all months, **mismatched denominators** that inflated $\mu$ unevenly across regimes and manufactured the crossover. An independent re-implementation, re-deriving the rates adversarially, caught it; with matched denominators the crossover vanished. We initially salvaged the corrected model as a *regime-contrast* instrument — and then, as Section 5.5 reports, our own simulation refuted even that weaker claim, so the utilization analysis is withdrawn entirely. The crossover is thus a *double* cautionary tale: a denominator artifact that survived correction only long enough to be refuted by simulation. It is the clearest illustration in this paper of why a convenient property must be simulated, not argued.

### 6.6 The Protocol: A Checklist for Dynamic Analysis of Clustered, Zero-Inflated Software Panels

We report these artifacts transparently because each is exactly the kind of result a careful empiricist should distrust precisely *because* it is clean and confirms the hypothesis. We distil the episode — together with the simulation of §6.1 and Result 1 — into a short checklist a reader can apply to their own repository panel. Steps **C1–C3** are established econometric hygiene that, as the artifacts show, is easy to violate in the SE setting; **C4** is the one SE-specific correction (Result 1) that standard practice does not cover; **C5** records a pitfall we learned the hard way. We do not claim the hygiene is novel — the contribution is the worked, quantified demonstration of how badly it fails when skipped.

> **Checklist — distributional/dynamic analysis of clustered, zero-inflated software panels.**
>
> **C1. Contrast treated vs. control; never pool pre/post.** Any rate, tail, or distributional comparison must enter as a treated×post interaction (a DiD), not a pooled pre-vs-post test. A pooled test has no control contrast and reads a secular calendar trend as a treatment effect — the §6.1 simulation shows this rejects a true null up to 100% of the time under a common trend.
>
> **C2. Cluster on the repository.** Repo-months are not independent; tail/rare events concentrate within a few repos. Use repo-clustered SEs or a repo-level block bootstrap (resample whole repos, never repo-months) for every statistic, including likelihood-ratio statistics whose χ² reference distribution assumes independence (see the negative control, §5.6), and prefer a wild-cluster bootstrap when the cluster count is small (§4.2).
>
> **C3. Match exposure denominators for any rate ratio.** Both numerator and denominator rates must be normalised over the *same* exposure; mismatched denominators manufacture spurious level shifts (the ρ-crossover artifact, §6.5).
>
> **C4. Correct the Markov df for occupied support (Result 1).** Under quantile binning of a zero-inflated outcome, check for phantom never-occupied states; compute homogeneity/order LR degrees of freedom from occupied, reachable support only. The uncorrected test is mechanically driven to non-rejection and the "comfortable null" it returns is vacuous.
>
> **C5. Do not trust snapshot-cadence rate ratios — and simulate before assuming a bias cancels.** A birth–death utilization from monthly net diffs is biased in *level*; we conjectured (and a reader might reasonably hope) that the bias cancels in the pre/post *contrast*, but our simulation (§5.5) shows it does not, because the truncation factor depends on the regime. The general lesson is the operative one: if a convenient cancellation is only argued verbally, simulate it under a known truth before relying on it.
>
> **C6. Defend a null as a bounded claim.** Replace "*p* > 0.05" with an equivalence (TOST) test against a pre-specified SESOI, a cluster-aware power curve, and a small-cluster-robust (wild-cluster bootstrap) check, and apply a multiplicity correction across the test family.

**On the queueing machinery.** An earlier version leaned on an M/M/1 utilization framing for the dynamics. Having withdrawn the utilization analysis (§5.5), we retain only the Markov-chain, spectral-gap, and variance views — each sensitive to a different feature of the process — as *convergent supporting evidence* for the beyond-mean null, not as co-equal independent claims, and we are explicit (Section 5.3) that, computed from one panel, they are not statistically independent. The transferable methodological by-product is the checklist (C1–C6), Result 1, and the two simulations (§6.1 and §5.5); the dynamics battery is supporting evidence for the empirical null, not the headline.

---

## 7. Discussion

### 7.1 Interpreting the Bounded Null

Across the mean (Section 4) and every dynamic moment we can estimate (Section 5), AI-tool adoption shows no statistically significant effect on accessibility quality in these repositories. This should not be read as "AI tools are harmless to accessibility." Three features qualify the conclusion precisely.

First, on the mean, equivalence testing certifies the null at ±5% of baseline on the dense semantic-HTML and keyboard axes but only at ±10–30% on the sparse, high-variance WCAG violation-density axes; a small effect concentrated purely in the rare-violation tail remains possible. Second, the static analyzer captures accessibility properties visible in the component source (semantic structure, ARIA, keyboard affordances) but not purely runtime properties (e.g. computed contrast, focus order across a live DOM); these are complementary, and the render-free design buys 100% coverage at the cost of runtime-only checks. Third, the monthly snapshot cadence is the binding constraint on the beyond-mean analysis: within-month introduce-then-fix cycles net to zero and are invisible, which limits the resolution at which a dynamic effect could be detected at all (and, as §5.5 shows, defeats the utilization model entirely). The honest summary is that adoption produces no large or even modest accessibility regression on the dense axes, and no detectable change in the generative process at monthly resolution, but a small tail effect cannot be ruled out.

What the null *does* establish is also substantive. It is bounded above by a positive equivalence test rather than asserted from a non-significant *p*, it holds across two-way fixed effects and two heterogeneity-robust estimators, it survives a small-cluster-robust wild-cluster bootstrap and a project-type screen of the controls, and the one statistic that superficially supported harm (the pooled tail test) is demonstrated to be an analysis artifact (Section 6). For a question the prior literature primes one to expect harm on (Mowar et al., CHI 2025), a rigorously-identified, precisely-delimited null is an informative correction to the prior, not an absence of result. We are equally candid about its scope: this is a *wide* null on a *modest* panel, and Section 7.3 sets out the larger study that would tighten it.

### 7.2 Where a Smaller Effect Might Still Hide

Our null rules out a large accessibility regression, not a small one, and we are explicit about the most plausible place a small effect could still live: structural-HTML semantics. The mechanism is theory-driven — language models optimise for functional plausibility, not for the semantic meaning of HTML elements, so non-semantic container substitution (flat `<div>` markup where `<button>`/`<nav>`/`<ul>` belong) is exactly the failure such tools would be expected to produce, and exactly what runtime checks and visual review are weakest at catching. Our data are *consistent* with this being the direction of any residual effect, but we have no significant category-level signal to point to: every WCAG-category density ATT is small and non-significant (Section 4.5), and the semantic-HTML ATT itself is small, negative, and sign-unstable across specifications (Section 4.2). We are therefore careful **not** to claim a signal here: this is a hypothesis for a better-powered, per-commit study, not a finding. We state it as the pre-registered primary hypothesis a follow-up should test, not as evidence we possess.

### 7.3 Implications

**For developers.** The absence of even a modest regression on the dense accessibility axes is reassuring, but the bound is looser on rare, severe violations, and the structural-HTML dimension where a residual effect would most plausibly hide is precisely the one runtime checks miss. Periodic static semantic audits remain a sensible complement to runtime checks.

**For tool builders.** Non-semantic container substitution is the theory-predicted failure mode for AI generation and a concrete, narrow target for static linters at completion or commit time — worth building for even though our data cannot confirm it occurs at scale.

**For researchers.** Staggered-DiD with modern heterogeneity-robust estimators transfers cleanly to frontend-specific metrics; render-independent AST scores complement runtime violation counts; and, as Section 6 shows, distributional/dynamic extensions of a causal panel demand cluster-robust, treated-versus-control inference. The clear next step is a larger, **pre-registered** study (≥200 repositories, a project-type-screened control arm, and per-commit rather than monthly resolution). Note that the density-axis bound is loose because violations are rare relative to a near-zero baseline, not because the panel is small, so the lever that tightens it is *resolution* — per-commit measurement captures the within-month introduce-and-fix events the monthly snapshot averages away, putting more non-zero signal into the baseline — alongside the additional repositories. Such a design would also recover the within-month dynamics the monthly cadence destroys and test the structural-HTML hypothesis of Section 7.2 with adequate power. We discuss this concretely as a Registered Report design in the replication materials.

---

## 8. Threats to Validity

### 8.1 Internal Validity

- **Parallel trends.** The pre-treatment joint F-test (F = 0.46, 3 df, p ≈ 0.71, §4.3) and visual pre-period inspection support the assumption.
- **Treatment-date misclassification.** Robustness to ±1-month shifts is confirmed (Table 6).
- **Rendering bias.** Differential rendering failure (41% treated vs. 48% control) introduces a conservative bias; the AST metric (100% coverage) serves as an independent confirmation that does not depend on rendering.
- **Control-arm validity.** A DiD is a difference of trends, so a concern is always that the control arm moves for reasons unrelated to treatment. On the enriched matched panel the two arms are well-behaved: pre-treatment parallel trends hold cleanly (joint F = 0.46, §4.3), the arms start comparable on every axis (Appendix A), and they show **comparable post-period coverage** (mean observed post-period repo-months 22.8 treated vs. 20.2 control), so the control group is not systematically less-active or under-observed. Where both arms drift together in the post-period — as in the upper-tail exceedance, where both decline (Table 9) — that shared secular movement is exactly what the treated-vs-control contrast nets out, and is the source of the pooled-test artifact dissected in Section 6. We additionally verified the null is unchanged under a project-type screen that removes non-application control repositories (documentation/guide, icon-library, boilerplate, blog), and under restriction to the hard-configuration-signal treated subset (§4.6).

### 8.2 External Validity

- **Open-source only.** All repos are public GitHub projects; proprietary codebases may differ.
- **React/TypeScript specificity.** Results may not generalise to other frontend frameworks or to non-TypeScript React.
- **Scale and remaining bound.** The full panel is 446 repositories (189 treated); the matched primary panel is 181. This supports tight equivalence bounds on the dense score axes (±5%) but looser ones on the rare-event violation-density axes (±10–30%); we report wild-cluster-bootstrap inference throughout. The looser density-axis bound is a consequence of those axes' near-zero baseline (an effect expressed as a percentage of a tiny mean is unavoidably wide), not of insufficient sample size — so it is tightened primarily by finer (per-commit) temporal resolution, which raises the non-zero signal in the baseline, rather than by repository count alone. This is a goal of the pre-registered follow-up of Section 7.3.

### 8.3 Construct Validity — Upgraded

The AST semantic metric — used as a co-primary outcome and the basis for the structural-HTML hypothesis of Section 7.2 — is validated against expert human judgement in Appendix D. **This study upgrades the validation from the single-rater design of the originating study to a four-rater design**: the same stratified set of 53 components was rated independently by four React/TypeScript engineers (2–10 years' experience) blind to the automated score and to each other. Inter-rater reliability is strong — **Krippendorff's α = 0.870, 95% CI [0.776, 0.923]** (ordinal; mean pairwise weighted κ = 0.897; all four raters within one point on 100% of components) — and criterion agreement with the AST score holds across every rater (per-rater Spearman ρ 0.670–0.751; pooled ρ = 0.733), with **non-decreasing** band ordering (one adjacent tie, Table D2).

**A construct-validity independence concern, named explicitly.** One of the four raters (R1) is the author and the designer of the AST metric. Three mitigations bound this, but we state the concern rather than let it pass: (i) the three rating sessions were blind to the automated score and to other raters; (ii) R1 is not an outlier (R1 ρ = 0.751 sits inside the tight per-rater band 0.670–0.751); and most importantly (iii) **we recompute every reliability and criterion statistic on the three *independent* raters alone (R2–R4), and the validation does not weaken**: Krippendorff's α = **0.880**, 95% CI [0.787, 0.934] (vs. 0.870 for all four), and pooled Spearman ρ = **0.703**, 95% CI [0.504, 0.842] (vs. 0.733). Because the independent-rater statistics are essentially identical to the all-four statistics, the metric's construct validity does not rest on its designer. We retain the originating study's scope limitation that headless-UI / React-Native components (≈15% of the sample) abstract HTML semantics away and draw mid-scale ratings from both the metric and the raters.

- **axe-core coverage.** Covers a subset of WCAG criteria; violations requiring rendered semantic context are not captured. This is one reason the AST metric is treated as co-primary rather than secondary.

### 8.4 The First-Order Markov Limitation

We report one assumption that does not cleanly hold: the **first-order Markov assumption holds at the primary 4-state binning but is rejected at finer/coarser binnings** (full order-test results by state count and regime are in Section 5.3). We treat this as a limitation rather than a finding. A higher-order dependence would mean the monthly transition matrix does not fully capture the temporal structure, which is plausible given that quality changes are driven by multi-month development episodes. It does not undermine the *homogeneity* conclusion (the pre/post transition structures are indistinguishable whether or not the chain is exactly first-order, and the homogeneity null is corroborated by three other moments — stationary distribution, variance, and the tail DiD — which, while computed from the same panel and so not statistically independent, are each sensitive to a different feature of the dynamics), but it does mean the Markov model is an approximation, and the dynamics null should be read as "no detectable regime difference *under a first-order monthly model*," not as a statement about arbitrary-order dynamics.

### 8.5 Scope of the Null

The null is bounded, and we state the bounds explicitly: equivalence testing rules out mean effects above ±5% of baseline on the dense semantic-HTML and keyboard axes, and above ±10–30% on the sparse violation-density axes; the level of every beyond-mean moment (volatility, tail risk, transition structure) is unchanged. It does **not** rule out a small effect concentrated purely in the rare-violation tail, sub-monthly dynamics, runtime-only accessibility properties the static analyzer cannot see (§7.1), or effects in proprietary or non-React codebases. The utilization facet — the introduction-versus-removal balance — is *not estimable* at monthly cadence (§5.5). The monthly-snapshot cadence — not the absence of an effect in nature — is the binding constraint on any stronger conclusion, and the larger, per-commit, pre-registered follow-up of Section 7.3 is the clear next step.

---

## 9. Conclusion

We asked whether adopting AI coding assistants causally degrades the *source-detectable* accessibility quality of frontend code, and — to our knowledge for the first time, longitudinally, causally, and at scale — answered it: across **446 open-source React/TypeScript repositories and 13,702 repo-months** (a propensity-matched 181-repo subset as the primary panel), measuring four complementary accessibility axes, we find a **comprehensive, tightly-bounded null**. No axis — semantic HTML, keyboard/focus, WCAG-category density, or severity-weighted violations — shows a significant treatment effect under two-way fixed effects or a heterogeneity-robust imputation estimator, on either panel, with wild-cluster bootstrap inference confirming the null is not a small-sample artifact. (A fifth candidate axis, ARIA-role correctness, was near-constant across the corpus and is reported as exhibiting no detectable variation rather than modelled.) Equivalence testing positively excludes effects larger than ±5% of baseline on the semantic-HTML and keyboard axes (±10–30% on the sparser density axes), and treated and control repositories have comparable post-period maintenance activity. Looking beyond the mean — at transition structure, volatility, and upper-tail risk — we find the *level* of every moment unchanged; the one second-order signal is a modest, robust increase in state *persistence* (slower-mixing post-adoption chains, spectral gap 0.036 → 0.017, CI excluding zero), indicating less month-to-month churn rather than better or worse quality.

Reaching that null honestly required killing two of our own too-good-to-be-true positives — a pooled tail-risk increase (p = 0.003) that reversed once treated-versus-control contrast and repo clustering were respected, and a queueing-utilization analysis whose convenient bias-cancellation our own simulation refuted, leading us to withdraw it. The discipline that caught both is the paper's transferable by-product: a short checklist for distributional analysis of clustered, zero-inflated repository panels, a Monte Carlo quantifying that the naive pooled test rejects a true null up to 100% of the time under a common secular trend, and one named SE-specific pitfall (Result 1, the zero-inflation degrees-of-freedom degeneracy in Markov regime tests).

We are candid about scope. This is a wide null on a modest panel: it excludes a large accessibility regression but not a small one, the structural-HTML dimension where a small effect would most plausibly hide is exactly the one this study cannot resolve, and the monthly cadence defeats the finer-grained dynamics. The clear next step is a larger, pre-registered study — ≥200 repositories, a project-type-screened control arm, per-commit resolution — that would tighten the equivalence bound and test the structural-HTML hypothesis with adequate power. For a question the literature primed toward harm, a rigorously-bounded null, reached by killing one's own artifacts, is an informative correction to the prior — and a template for how to extend a causal panel to distributional questions without being fooled.

**Replication.** All analysis code, panel data, and supporting scripts are archived at Zenodo, DOI [10.5281/zenodo.20995709](https://doi.org/10.5281/zenodo.20995709), and mirrored at `github.com/SomilKSharma/ai-react-accessibility-study`. The package maps scripts to results. The enriched panels are built by `build_enriched_panel.py` (propensity matching → `enriched_panel.csv`, 181 repos, and `enriched_panel_full.csv`, 446 repos). The primary mean-effect suite — TWFE and BJS imputation estimates, repo-clustered and wild-cluster-bootstrap inference, and the TOST equivalence bounds for **Tables 4, 4a, and 4b** — is produced by `estimate_enriched.py` on those panels. The event study, Markov homogeneity, volatility, and tail-DiD dynamics (Figures 1–3, Table 7, §5.3–5.6) are produced by `enriched_dynamics.py`; the per-axis forest plot (Figure 7) by `fig_enriched.py`. Supporting analyses: the project-type control screen (`control_screen.py`, §8.1); the Monte Carlo size study (`size_distortion_sim.py`, Figure 6); the utilization-refutation simulation (`utilization_refutation_sim.py`, Figure 4); the Benjamini–Hochberg multiplicity correction (`multiplicity.py`, reading `enriched_results_matched.csv`, Table 5); the zero-inflation / persistence / spectral-gap dynamics, including the committed `enriched_dynamics.json` that backs Tables 7 and 9 (`enriched_dynamics.py`); and the multi-rater construct validation (`raters_3independent.py`, Appendix D). The original 74-repo, two-axis analysis (`stage5_did.py`, `robust_did.py`, `wild_cluster_bootstrap.py`, `equivalence_and_multiplicity.py` on `panel.csv`) is retained for provenance and **superseded** for all primary results by the enriched-panel scripts above. All substantive estimates — the mean-effect tables, equivalence bounds, multiplicity correction, and the full dynamics battery — are produced by the enriched-panel scripts. A small number of descriptive figures inherited from the original pipeline and noted as such in the text (the Goodman–Bacon clean-comparison share, §3.2; the headless render-failure rates, §8.1) derive from that earlier analysis and are reported as provenance, not as enriched-panel estimates. All bootstraps use a fixed seed.

---

## Appendix A. Panel Summary Statistics

Table A1 reports repo-month means and standard deviations for the four measured accessibility axes, by group and period, on the matched primary panel (181 repos, 5,956 repo-months). The arms start comparable in the pre-period on every axis — a healthy basis for the DiD identification.

**Table A1. Panel summary statistics by group and period (matched panel).** Values are repo-month means (SD).

| Axis | Treated PRE | Treated POST | Control PRE | Control POST |
|---|---|---|---|---|
| Semantic HTML | 0.9454 (0.077) | 0.9409 (0.091) | 0.9447 (0.076) | 0.9490 (0.068) |
| Keyboard/focus | 0.9638 (0.067) | 0.9608 (0.085) | 0.9661 (0.063) | 0.9732 (0.053) |
| WCAG total density | 0.0345 (0.045) | 0.0350 (0.049) | 0.0424 (0.056) | 0.0381 (0.047) |
| Severity-weighted | 0.0798 (0.099) | 0.0827 (0.105) | 0.0982 (0.126) | 0.0930 (0.107) |

N = 5,956 repo-months (95 treated / 86 control repositories).

## Appendix B. Analysis-Plan Deviation Statement

We are explicit that this study was **not formally pre-registered.** We worked from a written internal analysis plan fixed before estimation, which makes the analytic choices auditable but does *not* carry the guarantees of a public, time-stamped pre-registration; we therefore avoid leaning on "specified in advance" as if it were verifiable third-party pre-registration, and we treat the design as exploratory-confirmatory rather than strictly confirmatory. The clear remedy — and the path we recommend for the follow-up in Section 7.3 — is to lodge the next study on OSF or as a Registered Report (the MSR/EMSE Registered Reports track is well suited) before data collection. We document here every deviation from the internal plan, in that spirit: (1) the dual axe denominator — renderable-only moved from sensitivity check to co-primary, motivated by the 60.4% renderability constraint discovered during collection, not by results inspection; (2) the inclusion criterion changed to data-coverage (≥12 months, ≥100 renderable rows); (3) a Tobit regression added as a planned robustness check for the censored AST outcome. No changes to the DiD equation, PSM specification, treatment-date logic, AST rubric, or RQ structure. Analyses *added during revision* in response to peer review — the heterogeneity-robust estimators, the wild-cluster bootstrap, the project-type control screen, and the utilization-refutation simulation — are clearly post-hoc and labelled as such; each strengthens or (in the utilization case) overturns a pre-existing analysis rather than introducing a new positive claim.

## Appendix C. Replication Package

All analysis code, panel data, and figure outputs are publicly available at the project repository (Zenodo DOI 10.5281/zenodo.20995709), with a fixed bootstrap seed throughout and a README mapping each script to the table or figure it produces (see the Replication note at the end of Section 9). The written analysis plan is available from the corresponding author. The seven figures referenced in the text are: (1) the pre-trend event study; (2) the dynamic DiD event study; (3) the pre- vs. post-adoption 4-state transition matrices; (4) the utilization-refutation simulation; (5) tail-exceedance by group and period; (6) the Monte Carlo size-distortion study; and (7) the per-axis ATT forest plot.

## Appendix D. AST Score Construct Validity — Multi-Rater Study

Four raters independently scored all 53 components — the originating rater plus three additional React/TypeScript engineers with 2, 6, and 10 years of experience — blind to the automated AST score and to one another. The procedure, rubric, and results follow.

### D.1 Procedure

We sample 53 React/TypeScript components from the study dataset via stratified sampling across six AST-score bands (0.00–0.50, 0.50–0.70, 0.70–0.85, 0.85–0.95, 0.95–0.99, 0.99–1.00), drawing 8–9 per band from production components with ≥3 interactive elements (excluding test files, stories, mocks). Each rater independently scores each component on a 1–5 scale of semantic-HTML quality (rubric below), shown the component source but **blind to its automated AST score** and **blind to other raters' scores**.

**Participants, recruitment, consent, and ethics.** The four raters are R1 (the author) and three independent professional React/TypeScript engineers (R2–R4, with 2, 6, and 10 years of experience) recruited from the author's professional network. Participation was voluntary and uncompensated; each rater gave informed consent before participating and could withdraw at any time. The task carried minimal risk: raters evaluated source code drawn from public open-source repositories using a fixed rubric, and no personal, sensitive, or identifying information about participants was collected, stored, or reported — individual ratings appear only in anonymised, aggregate form (R1–R4 labels). Blinding to the automated score and to other raters was enforced by distributing each rater a separate spreadsheet containing only component source and an empty score column, with the AST score and other raters' columns withheld. As an independent researcher with no institutional affiliation, the author was not subject to institutional-review-board oversight; the study falls within the minimal-risk category (professional evaluation of non-sensitive technical materials) that such bodies typically treat as exempt. To the best of the author's knowledge no formal ethics approval was required. We note explicitly that, because the study was run by a solo independent researcher, the recruitment, blinding, and independence of R2–R4 rest on the author's representation; the three-independent-rater robustness analysis (below) is included precisely so the validation does not depend on any single rater, including the author.

### D.2 Rubric (identical across raters)

- **5 — Excellent:** uses `<button>`, `<nav>`, `<main>`, `<ul>/<li>`, `<section>`, `<article>` appropriately throughout. No div-soup. All interactive elements are proper HTML interactive elements.
- **4 — Good:** mostly semantic with minor issues (e.g. one `<div onClick>` that should be a `<button>`, or a missing landmark).
- **3 — Mixed:** some semantic elements used correctly, some structural issues; a few `<div>`s substituted for semantic equivalents.
- **2 — Poor:** predominantly generic containers; most interactive elements are `<div onClick>` / `<span onClick>`; missing landmark structure.
- **1 — Very poor:** complete div-soup; no semantic elements; all interactions via `onClick` on divs/spans.

Raters focus only on semantic HTML structure — not ARIA, styling, or TypeScript correctness.

### D.3 Analysis Plan (pre-specified)

- **Inter-rater reliability:** Krippendorff's α (ordinal metric) across all raters; weighted Cohen's κ (quadratic weights) pairwise as a secondary statistic. Report point estimate + bootstrap 95% CI.
- **Criterion agreement with the automated score:** per-rater Spearman ρ and Kendall's τ vs. the AST score; the pooled (mean-rating) ρ as the headline.
- **Band ordering:** mean rating by AST-score band, checked for non-decreasing order (per rater and pooled).

### D.4 Baseline (single-rater, originating study)

For reference, the originating single-rater study (one frontend engineer, 3 yrs React/TS) yielded Spearman ρ = 0.751 (p < 0.0001), Kendall's τ = 0.620, N = 53, with mean human rating rising (non-decreasing) across the six bands. The acknowledged limitation — *single rater; inter-rater reliability not assessed* — is what the multi-rater study below resolves.

### D.5 Multi-Rater Results

Four raters (the originating rater R1, plus three additional engineers with 2, 6, and 10 years of React/TypeScript experience, R2–R4) independently scored all 53 components.

*Resampling unit.* All confidence intervals below are by **bootstrap over the 53 components** (2,000 replicates, fixed seed) — the unit over which each statistic is computed — not over repositories, since the validation statistic is component-level, not panel-level.

**Inter-rater reliability is strong.** Krippendorff's α (ordinal) across all four raters is **0.870**, 95% CI **[0.776, 0.923]** — clearing the conventional α ≥ 0.80 threshold for strong agreement, with even the lower CI bound above the 0.667 acceptability floor. Pairwise quadratic-weighted Cohen's κ ranges 0.867–0.934 across the six rater pairs (mean **0.897**). Descriptively, **all four raters agree exactly on 51% of components and fall within one point on 100%** (mean per-item SD = 0.25).

**The validation does not rest on the metric's designer.** One rater (R1) is the author/designer of the AST metric, a construct-validity independence concern we name rather than gloss. Recomputing on the **three independent raters (R2–R4) alone**, reliability and criterion agreement are essentially unchanged — indeed marginally stronger: Krippendorff's α = **0.880**, 95% CI [0.787, 0.934] (vs. 0.870 all-four); pooled Spearman ρ = **0.703**, 95% CI [0.504, 0.842] (vs. 0.733 all-four). Per-rater ρ against the AST score is R1 = 0.751, R2 = 0.742, R3 = 0.670, R4 = 0.716, so R1 sits inside a tight band rather than above it — the designer is representative, not an outlier, and dropping the designer entirely leaves the conclusion intact.

**Criterion agreement.** The all-four pooled mean-rating correlation is **Spearman ρ = 0.733**, 95% CI [0.553, 0.845]; Kendall's τ = 0.568. The pooled ρ is marginally below the single-rater 0.751 — expected, since averaging raters slightly attenuates a rank correlation — but it is now an estimate with a reliability footing and a confidence interval rather than one annotator's judgement. Table D1 collects the reliability and criterion statistics for both the all-four and three-independent-rater poolings.

**Band ordering is non-decreasing (one adjacent tie).** Pooled mean rating rises across the six AST-score bands with a single adjacent tie (0.85–0.95 and 0.95–0.99 both 3.78 in the all-four data); we therefore describe the ordering as *non-decreasing* rather than strictly monotonic. The three-independent-rater pooling shows the same shape with one negligible reversal (3.85 vs. 3.74 at the same adjacent bands), well within the per-band sampling noise (n = 9 per band).

**Table D1. Multi-rater construct-validity results.** Independent-rater (R2–R4) values reported alongside all-four.

| Statistic | All four raters | Three independent (R2–R4) |
|---|---|---|
| Krippendorff's α (ordinal) | **0.870** [0.776, 0.923] | **0.880** [0.787, 0.934] |
| Pooled Spearman ρ (mean rating vs. AST) | 0.733 [0.553, 0.845] | 0.703 [0.504, 0.842] |
| Per-rater Spearman ρ (range) | 0.670–0.751 | 0.670–0.742 |
| Mean pairwise quadratic-weighted κ | 0.897 (0.867–0.934) | — |
| Items within 1 point across raters | 100% | 100% |

**Table D2. Band ordering (pooled mean rating by AST-score band).** Non-decreasing; the 0.85–0.95 / 0.95–0.99 pair is a tie in the all-four data.

| AST band | n | All-four mean | Independent (R2–R4) mean |
|---|---:|---:|---:|
| 0.00–0.50 | 9 | 1.53 | 1.52 |
| 0.50–0.70 | 9 | 2.53 | 2.59 |
| 0.70–0.85 | 9 | 3.31 | 3.41 |
| 0.85–0.95 | 9 | 3.78 | 3.85 |
| 0.95–0.99 | 9 | 3.78 | 3.74 |
| 0.99–1.00 | 8 | 4.03 | 4.04 |

The automated AST semantic score is thus a validated operationalisation of semantic-HTML quality: independent engineers agree with each other at α = 0.88 and with the automated score at ρ = 0.67–0.74, the ordering is non-decreasing across bands, and the result is robust to excluding the metric's designer. We retain the originating study's scope limitation that headless-UI / React-Native components (≈15% of the sample) abstract HTML semantics away and tend to draw mid-scale ratings from both the metric and the raters.

---

## References

1. Mowar, P., Peng, Y.-H., Wu, J., Steinfeld, A., & Bigham, J. P. (2025). CodeA11y: Making AI Coding Assistants Useful for Accessible Web Development. *Proceedings of the 2025 CHI Conference on Human Factors in Computing Systems (CHI '25).* DOI:10.1145/3706598.3713335. arXiv:2502.10884.
2. He, H., Miller, C., Agarwal, S., Kästner, C., & Vasilescu, B. (2026). Speed at the Cost of Quality: How Cursor AI Increases Short-Term Velocity and Long-Term Complexity in Open-Source Projects. *Proceedings of the 23rd International Conference on Mining Software Repositories (MSR '26),* Rio de Janeiro. DOI:10.1145/3793302.3793349. arXiv:2511.04427.
3. He, Z., Huq, S. F., & Malek, S. (2025). Enhancing Web Accessibility: Automated Detection of Issues with Generative AI (GenA11y). *Proceedings of the ACM on Software Engineering,* 2(FSE), 2264–2287. DOI:10.1145/3729371.
4. Nahar, N., Kästner, C., Butler, J., Parnin, C., Zimmermann, T., & Bird, C. (2025). Beyond the Comfort Zone: Emerging Solutions to Overcome Challenges in Integrating LLMs into Software Products. *Proceedings of the 47th International Conference on Software Engineering: Software Engineering in Practice (ICSE-SEIP '25),* 516–527. DOI:10.1109/ICSE-SEIP66354.2025.00051. arXiv:2410.12071.
5. Callaway, B., & Sant'Anna, P. H. C. (2021). Difference-in-Differences with Multiple Time Periods. *Journal of Econometrics,* 225(2), 200–230. DOI:10.1016/j.jeconom.2020.12.001.
6. Cameron, A. C., Gelbach, J. B., & Miller, D. L. (2008). Bootstrap-Based Improvements for Inference with Clustered Errors. *Review of Economics and Statistics,* 90(3), 414–427. DOI:10.1162/rest.90.3.414.
7. Firpo, S., Fortin, N. M., & Lemieux, T. (2009). Unconditional Quantile Regressions. *Econometrica,* 77(3), 953–973. DOI:10.3982/ECTA6822.
8. Goel, A. L., & Okumoto, K. (1979). Time-Dependent Error-Detection Rate Model for Software Reliability and Other Performance Measures. *IEEE Transactions on Reliability,* R-28(3), 206–211. DOI:10.1109/TR.1979.5220566.
9. Tobin, J. (1958). Estimation of Relationships for Limited Dependent Variables. *Econometrica,* 26(1), 24–36. DOI:10.2307/1907382.
10. Hayes, A. F., & Krippendorff, K. (2007). Answering the Call for a Standard Reliability Measure for Coding Data. *Communication Methods and Measures,* 1(1), 77–89. DOI:10.1080/19312450709336664.
11. Rosenbaum, P. R., & Rubin, D. B. (1983). The Central Role of the Propensity Score in Observational Studies for Causal Effects. *Biometrika,* 70(1), 41–55. DOI:10.1093/biomet/70.1.41.
12. Shull, F. J., Carver, J. C., Vegas, S., & Juristo, N. (2008). The Role of Replications in Empirical Software Engineering. *Empirical Software Engineering,* 13(2), 211–218. DOI:10.1007/s10664-008-9060-1.
13. Da Silva, F. Q. B., Suassuna, M., França, A. C. C., et al. (2014). Replication of Empirical Studies in Software Engineering Research: A Systematic Mapping Study. *Empirical Software Engineering,* 19(3), 501–557. DOI:10.1007/s10664-012-9227-7.
14. Athey, S., & Imbens, G. W. (2006). Identification and Inference in Nonlinear Difference-in-Differences Models. *Econometrica,* 74(2), 431–497. DOI:10.1111/j.1468-0262.2006.00668.x.
15. Callaway, B., & Li, T. (2019). Quantile Treatment Effects in Difference in Differences Models with Panel Data. *Quantitative Economics,* 10(4), 1579–1618. DOI:10.3982/QE935.
16. Becker, J., Rush, N., Barnes, B., & Rein, D. (2025). *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity.* METR. arXiv:2507.09089.
17. Anderson, T. W., & Goodman, L. A. (1957). Statistical Inference about Markov Chains. *The Annals of Mathematical Statistics,* 28(1), 89–110. DOI:10.1214/aoms/1177707039.
18. W3C. (2018). *Web Content Accessibility Guidelines (WCAG) 2.1.* W3C Recommendation.
19. Deque Systems. (2023). *axe-core: Accessibility Testing Engine.* https://github.com/dequelabs/axe-core
20. Goodman-Bacon, A. (2021). Difference-in-Differences with Variation in Treatment Timing. *Journal of Econometrics,* 225(2), 254–277. DOI:10.1016/j.jeconom.2021.03.014.
21. Sun, L., & Abraham, S. (2021). Estimating Dynamic Treatment Effects in Event Studies with Heterogeneous Treatment Effects. *Journal of Econometrics,* 225(2), 175–199. DOI:10.1016/j.jeconom.2020.09.006.
22. Borusyak, K., Jaravel, X., & Spiess, J. (2024). Revisiting Event-Study Designs: Robust and Efficient Estimation. *Review of Economic Studies,* 91(6), 3253–3285. DOI:10.1093/restud/rdae007.
23. de Chaisemartin, C., & D'Haultfœuille, X. (2020). Two-Way Fixed Effects Estimators with Heterogeneous Treatment Effects. *American Economic Review,* 110(9), 2964–2996. DOI:10.1257/aer.20181169.
24. Lakens, D. (2017). Equivalence Tests: A Practical Primer for t-Tests, Correlations, and Meta-Analyses. *Social Psychological and Personality Science,* 8(4), 355–362. DOI:10.1177/1948550617697177.
25. Benjamini, Y., & Hochberg, Y. (1995). Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. *Journal of the Royal Statistical Society: Series B,* 57(1), 289–300. DOI:10.1111/j.2517-6161.1995.tb02031.x.
