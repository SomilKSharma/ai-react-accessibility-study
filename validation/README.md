# Construct-Validation Materials (Appendix D)

Multi-rater validation of the AST semantic-HTML score against independent expert
judgement. Reproduces every number in **Appendix D** and **Section 8.3** of the
manuscript.

## Files

| File | Description |
|---|---|
| `ratings.csv` | The four raters' 1–5 scores for all 53 sampled components, plus each component's automated `ast_score`. Raters are anonymised **R1–R4** (`my_rating` = R1, the originating rater; `rater_2yr`/`rater_6yr`/`rater_10yr` = R2/R3/R4, with 2/6/10 years' React/TypeScript experience). No names, emails, or free-text notes — PII-free by construction. |
| `components.csv` | The 53 sampled components: rating `id`, AST-score band, automated `ast_score`, source repo (public), source path, commit SHA, and snapshot month. This is the stratified sample (8–9 per band across the six AST-score bands). |
| `analyze_raters.py` | Recomputes Krippendorff's α (ordinal), pairwise quadratic-weighted Cohen's κ, per-rater and pooled Spearman ρ / Kendall τ vs. the AST score, band monotonicity, and exact/within-1 agreement. Fixed bootstrap seed (`20260625`, 2,000 replicates). |

## Run

```bash
python validation/analyze_raters.py        # run from the repo root
# or:  cd validation && python analyze_raters.py
```

Requires `krippendorff` (in `requirements.txt`).

## Expected output (matches Appendix D / Table D1–D2)

```
Krippendorff's alpha (ordinal, 4 raters): 0.870  95% CI [0.776, 0.923]
mean pairwise quadratic-weighted kappa:   0.897   (range 0.867–0.934)
per-rater Spearman rho range:             [0.670, 0.751]
pooled mean-rating Spearman rho:          0.733  (p=4.4e-10) 95% CI [0.553, 0.845]
Kendall tau (pooled):                     0.568
band monotonicity:                        monotonic, no reversals
all-4 identical: 51% of items;            within-1-point: 100% of items
```

## Column dictionary — `ratings.csv`

| Column | Meaning |
|---|---|
| `id` | Component id (1–53), keys to `components.csv`. |
| `ast_score` | Automated AST semantic-HTML score in [0, 1]. |
| `my_rating` | R1 (originating rater, 3 yrs) 1–5 semantic-HTML rating. |
| `rater_2yr` | R2 (2 yrs) 1–5 rating. |
| `rater_6yr` | R3 (6 yrs) 1–5 rating. |
| `rater_10yr` | R4 (10 yrs) 1–5 rating. |

## Column dictionary — `components.csv`

| Column | Meaning |
|---|---|
| `id` | Component id (1–53). |
| `ast_band` | One of the six stratification bands (0.00–0.50 … 0.99–1.00). |
| `ast_score` | Automated AST semantic-HTML score. |
| `total_interactive` | Count of interactive elements found by the AST parser. |
| `deductions` | Number of semantic-HTML deductions applied. |
| `repo` | Source GitHub repository (`owner/name`, public). |
| `source_path` | Path to the component within the source repo. |
| `commit_sha` | Commit the component was sampled at. |
| `snapshot_month` | Snapshot month of the sample. |

The 1–5 rating rubric (identical across raters) is reproduced verbatim in
Appendix D.2 of the manuscript and in `rater-study-protocol` material; raters
scored components blind to the automated AST score and to one another.
