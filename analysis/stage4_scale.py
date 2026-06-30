#!/usr/bin/env python3
"""
stage4_scale.py — smart, resumable, low-memory measurement runner (v3)
======================================================================
Scales the study by measuring the 509 fully-qualified-but-unmeasured repos
(plus optionally re-measuring the original 93) on a single consistent harness,
producing the enriched 5-axis accessibility data from a11y_analyzer.js.

WHY THIS EXISTS / WHAT IT FIXES (the pain points from the old stage4_measure.py):
  * Memory blowups  -> no jsdom / jest / full render at all. We use only
                       `git checkout` + a lightweight TypeScript-AST node pass
                       with a hard --max-old-space-size cap. This was the OOM
                       source; it is removed entirely.
  * Clone failures  -> shallow partial clone (--filter=blob:none --no-checkout
                       then sparse), retries with exponential backoff, and
                       skip-and-continue (a bad repo NEVER kills the batch).
  * Timeouts        -> per-clone, per-checkout, and per-AST-pass timeouts; a
                       per-repo wall-clock budget; slow snapshots are skipped,
                       not fatal.
  * Lost progress   -> fully resumable: status written to repo_measurement_status
                       after every repo; re-running skips completed repos and
                       resumes mid-batch.
  * Disk            -> one repo on disk at a time; rmtree in a finally block.

Enriched data: writes the 5-axis a11y_analyzer.js output to ast_results
(new columns added non-destructively via ALTER TABLE), plus post-period
activity covariates to a new repo_activity table.

Usage:
  python3 stage4_scale.py --max-repos 600 --max-months 36
  python3 stage4_scale.py --treated-only        # measure only unmeasured treated
  python3 stage4_scale.py --remeasure-existing  # also re-do the original 93
  (safe to Ctrl-C and re-run; it resumes.)

Requires: git, node (>=18), `npm install typescript` in cwd, python3 (stdlib only).
"""
import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
# repos.db (large; archived on Zenodo) is expected at the repo root.
# Override with the REPOS_DB env var if it lives elsewhere.
DB_PATH = os.environ.get("REPOS_DB", str((HERE / ".." / "repos.db").resolve()))
ANALYZER = str(HERE / "a11y_analyzer.js")
WORK_DIR = str(HERE / "scale_workspace")
NODE_MEM_MB = 1024          # hard cap on the node AST pass (your Mac OOM guard)
CLONE_TIMEOUT = 240         # s
CHECKOUT_TIMEOUT = 45       # s
AST_TIMEOUT = 90            # s per snapshot
REPO_WALL_BUDGET = 900      # s max per repo before we bank what we have and move on
CLONE_RETRIES = 3


def now():
    return datetime.now(timezone.utc).isoformat()


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ── DB setup: add enriched columns non-destructively ──────────────────────────
NEW_AST_COLS = [
    ("total_elements", "INTEGER"), ("wcag_perceivable", "INTEGER"),
    ("wcag_operable", "INTEGER"), ("wcag_understandable", "INTEGER"),
    ("wcag_robust", "INTEGER"), ("wcag_total", "INTEGER"),
    ("sev_critical", "INTEGER"), ("sev_serious", "INTEGER"),
    ("sev_moderate", "INTEGER"), ("severity_weighted", "INTEGER"),
    ("aria_score", "REAL"), ("aria_total_roles", "INTEGER"),
    ("aria_invalid_role", "INTEGER"), ("aria_missing_required", "INTEGER"),
    ("aria_redundant_role", "INTEGER"), ("keyboard_score", "REAL"),
    ("kbd_total_interactive_custom", "INTEGER"), ("kbd_click_no_keyboard", "INTEGER"),
    ("kbd_positive_tabindex", "INTEGER"), ("kbd_interactive_not_focusable", "INTEGER"),
    ("struct_heading_count", "INTEGER"),
]


def init_db(conn):
    existing = {r[1] for r in conn.execute("PRAGMA table_info(ast_results)")}
    for col, typ in NEW_AST_COLS:
        if col not in existing:
            conn.execute(f"ALTER TABLE ast_results ADD COLUMN {col} {typ}")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS repo_activity (
            repo_id INTEGER, full_name TEXT, window TEXT,
            commits INTEGER, distinct_authors INTEGER, span_days INTEGER,
            PRIMARY KEY (repo_id, window)
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS repo_measurement_status (
            repo_id INTEGER PRIMARY KEY, full_name TEXT, status TEXT,
            snapshots_done INTEGER, started_at TEXT, completed_at TEXT, error TEXT
        )""")
    conn.commit()


# ── repo selection ────────────────────────────────────────────────────────────
def select_repos(conn, args):
    """Fully-qualified repos, prioritising unmeasured; treated first."""
    q = """
      SELECT repo_id, full_name, tsx_file_count, treatment_tier, treatment_date,
             CASE WHEN status='treated' THEN 1 ELSE 0 END AS is_treated
      FROM repo_qualification
      WHERE pass_history=1 AND pass_contributors=1 AND pass_tsx_count=1
            AND pass_pre_treatment=1 AND pass_post_treatment=1
    """
    rows = conn.execute(q).fetchall()
    done = {r[0] for r in conn.execute(
        "SELECT repo_id FROM repo_measurement_status WHERE status='done'")}
    measured = {r[0] for r in conn.execute("SELECT DISTINCT repo_id FROM axe_results")}

    repos = []
    for repo_id, full_name, tsx, tier, tdate, is_tr in rows:
        already = (repo_id in measured) or (repo_id in done)
        if already and not args.remeasure_existing:
            continue
        if args.treated_only and not is_tr:
            continue
        repos.append(dict(repo_id=repo_id, full_name=full_name, tsx=tsx or 0,
                          tier=tier, treatment_date=tdate, is_treated=is_tr))
    # treated first, then smaller repos first (faster, builds momentum, de-risks)
    repos.sort(key=lambda r: (-r["is_treated"], r["tsx"]))
    return repos[:args.max_repos]


# ── git helpers (robust clone) ────────────────────────────────────────────────
def _force_rm(path):
    """Remove a dir robustly even when overlay-fs leaves undeletable git objects."""
    if not os.path.exists(path):
        return
    shutil.rmtree(path, ignore_errors=True)
    if os.path.exists(path):
        subprocess.run(["rm", "-rf", path], capture_output=True, timeout=60)


def robust_clone(full_name, dest):
    """Shallow, blobless clone with retries into a FRESH path each attempt.

    Returns the actual clone path on success (which is moved to `dest`), or None.
    We never reuse a destination across attempts (the 'destination exists' bug),
    and we treat git *warnings* (non-zero only via check) as non-fatal by
    inspecting whether the .git dir actually materialised rather than trusting
    the return code alone.
    """
    url = f"https://github.com/{full_name}.git"
    _force_rm(dest)
    for attempt in range(1, CLONE_RETRIES + 1):
        tmp = f"{dest}.try{attempt}"
        _force_rm(tmp)
        try:
            r = subprocess.run(
                ["git", "clone", "--quiet", "--filter=blob:none", url, tmp],
                capture_output=True, timeout=CLONE_TIMEOUT)
            # success criterion: a usable repo exists, regardless of warnings
            if os.path.isdir(os.path.join(tmp, ".git")) and \
               subprocess.run(["git", "-C", tmp, "rev-parse", "HEAD"],
                              capture_output=True).returncode == 0:
                _force_rm(dest)
                os.rename(tmp, dest)
                return True
            err = (r.stderr or b"").decode("utf-8", "ignore").strip().splitlines()
            err = err[-1][:120] if err else f"rc={r.returncode}"
            log(f"    clone attempt {attempt}/{CLONE_RETRIES} {full_name}: {err}")
        except subprocess.TimeoutExpired:
            log(f"    clone timeout (attempt {attempt}/{CLONE_RETRIES}) {full_name}")
        finally:
            _force_rm(tmp)
        time.sleep(min(2 ** attempt, 8))
    return False


def monthly_commits(repo_path, max_months):
    """One commit per calendar month, newest `max_months`."""
    try:
        out = subprocess.run(
            ["git", "log", "--pretty=format:%H|%cI", "--date=iso"],
            cwd=repo_path, capture_output=True, text=True, timeout=60).stdout
    except subprocess.TimeoutExpired:
        return []
    by_month = {}
    for line in out.splitlines():
        if "|" not in line:
            continue
        sha, ciso = line.split("|", 1)
        month = ciso[:7]
        if month not in by_month:    # first seen = latest commit that month
            by_month[month] = (sha, ciso)
    months = sorted(by_month.keys(), reverse=True)[:max_months]
    return [dict(month=m, sha=by_month[m][0], date=by_month[m][1]) for m in sorted(months)]


def list_tsx(repo_path):
    out = []
    for root, _, files in os.walk(repo_path):
        if ".git" in root or "node_modules" in root:
            continue
        for f in files:
            if f.endswith((".tsx", ".jsx")):
                out.append(os.path.join(root, f))
    return out


def is_component(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            c = fh.read(4000)
    except Exception:
        return False
    return ("return" in c and "<" in c) or "=>" in c and "<" in c


def run_analyzer(files, repo_path):
    """Run the AST analyzer with a hard memory cap; returns list of records."""
    if not files:
        return []
    env = dict(os.environ, NODE_OPTIONS=f"--max-old-space-size={NODE_MEM_MB}")
    # batch to keep argv length sane
    recs = []
    for i in range(0, len(files), 200):
        batch = files[i:i + 200]
        try:
            r = subprocess.run(["node", ANALYZER] + batch, capture_output=True,
                               text=True, timeout=AST_TIMEOUT, env=env)
            if r.returncode == 0 and r.stdout.strip():
                recs.extend(json.loads(r.stdout))
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            continue
    return recs


def post_period_activity(repo_path, treatment_date):
    """Commits / distinct authors AFTER the treatment month — the covariate that
    rebuts 'never-treated repos are just less maintained' (reviewer #3)."""
    if not treatment_date:
        return None
    since = treatment_date[:10]
    try:
        out = subprocess.run(
            ["git", "log", f"--since={since}", "--pretty=format:%ae|%cI"],
            cwd=repo_path, capture_output=True, text=True, timeout=60).stdout
    except subprocess.TimeoutExpired:
        return None
    authors = set(); n = 0; dates = []
    for line in out.splitlines():
        if "|" in line:
            ae, ci = line.split("|", 1)
            authors.add(ae); n += 1; dates.append(ci[:10])
    span = 0
    if dates:
        span = (datetime.fromisoformat(max(dates)) - datetime.fromisoformat(min(dates))).days
    return dict(commits=n, distinct_authors=len(authors), span_days=span)


# ── per-repo processing ───────────────────────────────────────────────────────
def process_repo(conn, repo, max_months):
    rid = repo["repo_id"]; full = repo["full_name"]
    dest = os.path.join(WORK_DIR, full.replace("/", "__"))
    conn.execute("INSERT OR REPLACE INTO repo_measurement_status "
                 "(repo_id, full_name, status, started_at) VALUES (?,?,?,?)",
                 (rid, full, "in_progress", now()))
    conn.commit()
    start = time.time()
    snaps_done = 0
    try:
        if not robust_clone(full, dest):
            raise RuntimeError("clone failed after retries")
        commits = monthly_commits(dest, max_months)
        if not commits:
            raise RuntimeError("no commits")

        tdate = repo["treatment_date"]
        for snap in commits:
            if time.time() - start > REPO_WALL_BUDGET:
                log(f"    wall-budget hit; banking {snaps_done} snaps for {full}")
                break
            # resumable at snapshot level
            ex = conn.execute("SELECT id FROM snapshots WHERE repo_id=? AND snapshot_month=?",
                              (rid, snap["month"])).fetchone()
            if ex:
                continue
            try:
                subprocess.run(["git", "checkout", "--quiet", snap["sha"]],
                               cwd=dest, capture_output=True, timeout=CHECKOUT_TIMEOUT)
            except subprocess.TimeoutExpired:
                continue
            comps = [f for f in list_tsx(dest) if is_component(f)]
            if not comps:
                continue
            is_post = int(bool(tdate) and snap["date"][:7] >= tdate[:7]) if tdate else 0
            conn.execute("INSERT OR IGNORE INTO snapshots "
                         "(repo_id, full_name, snapshot_month, commit_sha, commit_date, "
                         "is_treated, is_post, treatment_date) VALUES (?,?,?,?,?,?,?,?)",
                         (rid, full, snap["month"], snap["sha"], snap["date"],
                          repo["is_treated"], is_post, tdate))
            conn.commit()
            sid = conn.execute("SELECT id FROM snapshots WHERE repo_id=? AND snapshot_month=?",
                               (rid, snap["month"])).fetchone()[0]
            recs = run_analyzer(comps, dest)
            for r in recs:
                if r.get("error"):
                    continue
                rel = os.path.relpath(r["file"], dest)
                conn.execute("""INSERT INTO ast_results
                    (snapshot_id, repo_id, full_name, snapshot_month, component_file,
                     total_interactive, deductions, semantic_score, div_onclick_no_role,
                     div_as_semantic, img_missing_alt, span_interactive,
                     total_elements, wcag_perceivable, wcag_operable, wcag_understandable,
                     wcag_robust, wcag_total, sev_critical, sev_serious, sev_moderate,
                     severity_weighted, aria_score, aria_total_roles, aria_invalid_role,
                     aria_missing_required, aria_redundant_role, keyboard_score,
                     kbd_total_interactive_custom, kbd_click_no_keyboard,
                     kbd_positive_tabindex, kbd_interactive_not_focusable, struct_heading_count)
                    VALUES (?,?,?,?,?, ?,?,?,?, ?,?,?, ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (sid, rid, full, snap["month"], rel,
                     r["total_interactive"], r["deductions"], r["semantic_score"],
                     r["div_onclick_no_role"], r["div_as_semantic"], r["img_missing_alt"],
                     r["span_interactive"], r["total_elements"], r["wcag_perceivable"],
                     r["wcag_operable"], r["wcag_understandable"], r["wcag_robust"],
                     r["wcag_total"], r["sev_critical"], r["sev_serious"], r["sev_moderate"],
                     r["severity_weighted"], r["aria_score"], r["aria_total_roles"],
                     r["aria_invalid_role"], r["aria_missing_required"], r["aria_redundant_role"],
                     r["keyboard_score"], r["kbd_total_interactive_custom"],
                     r["kbd_click_no_keyboard"], r["kbd_positive_tabindex"],
                     r["kbd_interactive_not_focusable"], r["struct_heading_count"]))
            conn.commit()
            snaps_done += 1

        # post-period activity covariate
        act = post_period_activity(dest, repo["treatment_date"])
        if act:
            conn.execute("INSERT OR REPLACE INTO repo_activity "
                         "(repo_id, full_name, window, commits, distinct_authors, span_days) "
                         "VALUES (?,?,?,?,?,?)",
                         (rid, full, "post", act["commits"], act["distinct_authors"], act["span_days"]))
        conn.execute("UPDATE repo_measurement_status SET status='done', snapshots_done=?, "
                     "completed_at=? WHERE repo_id=?", (snaps_done, now(), rid))
        conn.commit()
        log(f"  ✓ {full} — {snaps_done} snapshots")
        return True
    except Exception as e:
        conn.execute("UPDATE repo_measurement_status SET status='error', error=?, "
                     "completed_at=? WHERE repo_id=?", (str(e)[:200], now(), rid))
        conn.commit()
        log(f"  ✗ {full} — {e}")
        return False
    finally:
        _force_rm(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-repos", type=int, default=600)
    ap.add_argument("--max-months", type=int, default=36)
    ap.add_argument("--treated-only", action="store_true")
    ap.add_argument("--remeasure-existing", action="store_true")
    args = ap.parse_args()

    os.makedirs(WORK_DIR, exist_ok=True)
    if not os.path.exists(ANALYZER):
        sys.exit(f"analyzer not found: {ANALYZER}")
    conn = sqlite3.connect(DB_PATH, timeout=60)
    init_db(conn)
    repos = select_repos(conn, args)
    log(f"DB: {DB_PATH}")
    log(f"repos to process this run: {len(repos)} "
        f"(treated: {sum(r['is_treated'] for r in repos)}, "
        f"control: {sum(1-r['is_treated'] for r in repos)})")
    ok = 0
    for i, repo in enumerate(repos, 1):
        log(f"[{i}/{len(repos)}] {repo['full_name']} "
            f"(tsx={repo['tsx']}, {'treated' if repo['is_treated'] else 'control'})")
        ok += process_repo(conn, repo, args.max_months)
        # periodic disk sweep safety
        if i % 25 == 0:
            _force_rm(WORK_DIR); os.makedirs(WORK_DIR, exist_ok=True)
    log(f"done: {ok}/{len(repos)} succeeded this run")
    conn.close()


if __name__ == "__main__":
    main()
