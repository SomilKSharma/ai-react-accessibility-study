#!/usr/bin/env python3
"""Generate the trimmed, file-level derived dataset that the dynamics analysis
consumes, so the replication package is runnable from a bare `git clone` without
shipping the full ~124 MB `repos.db` (which is archived on Zenodo instead).

This extracts ONLY the columns `dynamics_analysis.py` reads:

  data/file_diffs.csv      one row per (repo, snapshot-month, component file):
                           repo_id, full_name, snapshot_month, component_file,
                           violations_total, renderable
  data/matched_pairs.csv   rank-1 propensity-matched treated/control repo ids
  data/treatment_dates.csv per-repo treatment_date for TREATED repos

These three files reproduce `build_panel()` and `compute_deltas()` bit-for-bit:
the regime (pre/post) and treated/control labels are RE-DERIVED from
matched_pairs + treatment_dates exactly as the DB-backed path does — we do NOT
ship the DB's precomputed `snapshots.is_post`/`treatment_date` columns, which
differ from the panel-construction logic (controls inherit their matched
treated repo's date).

Run once against repos.db to (re)generate the shipped CSVs:
    python build_file_diffs.py --db repos.db --out data/
"""
import argparse
import sqlite3
from pathlib import Path

import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="repos.db")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(exist_ok=True)
    conn = sqlite3.connect(args.db)

    # File-level axe rows joined to their snapshot's repo + month. This single
    # table is enough to rebuild both the per-snapshot aggregates (component_count,
    # renderable_count, violations_total) and the per-file month-to-month deltas.
    fl = pd.read_sql_query(
        "SELECT s.repo_id, s.full_name, s.snapshot_month, "
        "a.component_file, a.violations_total, a.renderable "
        "FROM axe_results a JOIN snapshots s ON a.snapshot_id = s.id "
        "ORDER BY s.repo_id, s.snapshot_month, a.component_file", conn)

    # Normalise component_file to a REPO-RELATIVE path. The raw DB stores absolute
    # local scan paths (.../repos_workspace/worker_N_<Owner>__<repo>/<rel-path>),
    # which leak the collecting machine's filesystem layout. component_file is only
    # ever used as a per-repo diffing key, so stripping the constant per-repo
    # prefix is information-preserving (same file -> same key across months).
    fl["component_file"] = fl["component_file"].str.replace(
        r"^.*?/repos_workspace/worker_\d+_[^/]+/", "", regex=True)
    fl.to_csv(out / "file_diffs.csv", index=False)
    print(f"[file_diffs.csv] {len(fl)} file-rows, "
          f"{fl.repo_id.nunique()} repos, "
          f"{fl.groupby(['repo_id','snapshot_month']).ngroups} repo-months")

    pairs = pd.read_sql_query(
        "SELECT treated_repo_id, control_repo_id FROM matched_pairs "
        "WHERE match_rank = 1 ORDER BY treated_repo_id", conn)
    pairs.to_csv(out / "matched_pairs.csv", index=False)
    print(f"[matched_pairs.csv] {len(pairs)} rank-1 pairs")

    qual = pd.read_sql_query(
        "SELECT repo_id, treatment_date FROM repo_qualification "
        "WHERE treatment_date IS NOT NULL ORDER BY repo_id", conn)
    qual.to_csv(out / "treatment_dates.csv", index=False)
    print(f"[treatment_dates.csv] {len(qual)} repos with a treatment_date")


if __name__ == "__main__":
    main()
