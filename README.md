# Replication Materials — "Accessibility and Semantic Quality Regressions in AI-Assisted React Development"

> Somil Sharma · 2026
> Preprint: [Zenodo DOI](https://doi.org/10.5281/zenodo.20482307) · arXiv: [arXiv ID] (pending)

---

## Contents

| File | Description |
|---|---|
| `stage5_did.py` | Full DiD estimation pipeline — builds the panel, runs primary DiD, Tobit regression, event study, heterogeneity (RQ3), and robustness checks |
| `panel.csv` | Repo-month panel dataset used for all regressions (2,374 observations, 74 repositories) |

---

## panel.csv — Column Reference

| Column | Type | Description |
|---|---|---|
| `snapshot_id` | int | Unique snapshot identifier |
| `repo_id` | int | Repository identifier |
| `full_name` | str | GitHub full name (owner/repo) |
| `snapshot_month` | str | Month of snapshot (YYYY-MM) |
| `commit_sha` | str | Commit hash for snapshot |
| `commit_date` | str | Commit timestamp |
| `component_count` | float | Total React components analyzed |
| `renderable_count` | float | Components successfully rendered |
| `violations_total` | float | Total axe-core violations |
| `violations_critical` | float | Critical-severity violations |
| `violations_serious` | float | Serious-severity violations |
| `ast_score_mean` | float | Mean AST semantic score (0–1, right-censored at 1.0) |
| `total_interactive` | float | Total interactive elements |
| `deductions` | float | AST deduction count |
| `is_treated` | int | 1 = AI-adopting repo, 0 = control |
| `treatment_date` | str | Date of AI tool adoption (treated) or inherited synthetic date (control) |
| `treatment_month_str` | str | Treatment month as YYYY-MM |
| `history_months` | float | Months of commit history (covariate) |
| `tsx_file_count` | float | TSX file count at treatment (covariate) |
| `repo_partial` | int | 1 = repo errored mid-run but passed coverage inclusion |
| `treatment_tier` | float | Adoption signal tier for treated repos (NULL for controls — expected) |
| `axe_total_per_file` | float | Primary outcome: violations / component_count |
| `axe_renderable_per_file` | float | Primary outcome: violations / renderable_count (NaN if renderable_count = 0) |
| `snapshot_month_int` | int | Months since 2020-01 (integer encoding) |
| `treatment_month_int` | int | Treatment month as integer |
| `is_post` | int | 1 if snapshot_month >= treatment_month |
| `relative_month` | int | snapshot_month_int − treatment_month_int |

---

## Reproducing the Analysis

### Requirements

```bash
pip install pandas numpy statsmodels scipy matplotlib
```

### Running

The script reads from `repos.db` (the full SQLite database, not included due to
size — contains raw axe-core and AST scan results for all repositories).
`panel.csv` is the pre-built output and is sufficient to verify all regression
results independently.

```bash
python stage5_did.py   # requires repos.db
```

To replicate regressions directly from `panel.csv` without `repos.db`,
use the estimation functions (`run_did`, `run_tobit`, `run_event_study`)
with the panel loaded via pandas.

### Outputs

Running the script produces `stage5_out/` containing:

- `stage5_results.txt` — human-readable summary of all results
- `table_main.csv` — primary DiD across 3 outcomes
- `table_tobit.csv` — Tobit regression result
- `table_heterogeneity.csv` — per-category β (RQ3)
- `table_robustness.csv` — 5 robustness specifications
- `fig1_parallel_trends.png` — pre-period event study plot
- `fig2_dynamic_did.png` — full dynamic DiD plot

---

## Citation

```bibtex
@misc{sharma2026accessibility,
  title   = {Accessibility and Semantic Quality Regressions in
             AI-Assisted React Development: An Empirical Study},
  author  = {Sharma, Somil},
  year    = {2026},
  url     = {https://doi.org/10.5281/zenodo.20482307}
}
```

---

## License

Code: MIT
Data (`panel.csv`): CC BY 4.0
