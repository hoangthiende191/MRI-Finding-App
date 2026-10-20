"""
Phase 4.2 - Query Processing & Optimization : TEST (benchmark)

One command measures every application query (Q1-Q5) in two states:
    A_no_index : copy of the data in mri_42_noindex, no keys / no indexes
    B_indexed  : the real schema (mri_radiology_db) with the schema.sql indexes
and, for Q1, Q2 and Q4, both the ORIGINAL query and the REWRITTEN query
(the SELECT bodies of get_*_opt in 4_2_setup.sql).

For each case it
  * checks that the rewritten query returns the same data as the original,
  * runs the query N times through mysql-connector (the way the Flask app
    calls it) and reports median / p95 time and bytes returned,
  * dumps EXPLAIN ANALYZE of every statement.

Usage (project root, virtual environment active, MySQL running, .env filled):
    python 4issue/4.2QueryOptimization/4_2_benchmark.py
Options:
    --patient 0230 --sequence T2 --orientation SAG --repeat 200

Output (next to this script):
    4_2_results.csv   timing table
    4_2_plans.txt     EXPLAIN ANALYZE output of every statement
The helper database mri_42_noindex is created at the start and dropped at
the end, so nothing is left behind in the real schema.
"""
import argparse
import csv
import os
import statistics
import time
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parents[1] / ".env")          # <project root>/.env

REAL_DB = os.getenv("DATABASE_NAME", "mri_radiology_db")
NOINDEX_DB = "mri_42_noindex"
TABLES = ["patient", "radiology_report", "study", "series", "mri_image", "image_feature"]

# --------------------------------------------------------------------- Q1
Q1_ORIGINAL = ("""
SELECT p.patient_id, rr.report_id, rr.clinician_notes,
       s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM patient p
LEFT JOIN radiology_report rr ON p.patient_id = rr.patient_id
LEFT JOIN study s             ON p.patient_id = s.patient_id
LEFT JOIN series se           ON s.study_id   = se.study_id
LEFT JOIN mri_image i         ON se.series_id = i.series_id
WHERE p.patient_id = %(pid)s
ORDER BY s.study_date, se.series_id, i.image_id
""",)

Q1_REWRITTEN = ("""
SELECT p.patient_id, rr.report_id, rr.clinician_notes
FROM patient p
LEFT JOIN radiology_report rr ON rr.patient_id = p.patient_id
WHERE p.patient_id = %(pid)s
""", """
SELECT s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM study s
JOIN series se   ON se.study_id = s.study_id
JOIN mri_image i ON i.series_id = se.series_id
WHERE s.patient_id = %(pid)s
ORDER BY s.study_date, se.series_id, i.image_id
""")

# --------------------------------------------------------------------- Q2
Q2_ORIGINAL = ("""
SELECT p.patient_id, rr.report_id, rr.clinician_notes,
       s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM patient p
JOIN study s                  ON p.patient_id = s.patient_id
JOIN series se                ON s.study_id   = se.study_id
JOIN mri_image i              ON se.series_id = i.series_id
LEFT JOIN radiology_report rr ON p.patient_id = rr.patient_id
WHERE p.patient_id = %(pid)s
  AND se.sequence_type = %(seq)s
  AND se.orientation   = %(ori)s
ORDER BY s.study_date, se.series_id, i.image_id
""",)

Q2_REWRITTEN = ("""
SELECT p.patient_id, rr.report_id, rr.clinician_notes
FROM patient p
LEFT JOIN radiology_report rr ON rr.patient_id = p.patient_id
WHERE p.patient_id = %(pid)s
""", """
SELECT s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM study s
JOIN series se   ON se.study_id = s.study_id
JOIN mri_image i ON i.series_id = se.series_id
WHERE s.patient_id     = %(pid)s
  AND se.sequence_type = %(seq)s
  AND se.orientation   = %(ori)s
ORDER BY s.study_date, se.series_id, i.image_id
""")

# --------------------------------------------------------------------- Q3
Q3_ORIGINAL = ("""
SELECT i.image_id, i.file_name, i.file_path,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       s.study_id, s.study_name, s.study_date, s.patient_id
FROM mri_image i
JOIN series se ON se.series_id = i.series_id
JOIN study s   ON s.study_id   = se.study_id
WHERE i.image_id = %(img)s
""",)

# --------------------------------------------------------------------- Q4
Q4_ORIGINAL = ("""
SELECT i.image_id, i.file_name, i.file_path,
       se.series_name, se.sequence_type, se.orientation,
       s.study_name, s.patient_id
FROM mri_image i
JOIN series se ON se.series_id = i.series_id
JOIN study s   ON s.study_id   = se.study_id
WHERE i.image_id <> %(img)s
  AND (%(seq)s IS NULL OR se.sequence_type = %(seq)s)
  AND (%(ori)s IS NULL OR se.orientation   = %(ori)s)
LIMIT %(lim)s
""",)

_Q4_COLS = """SELECT i.image_id, i.file_name, i.file_path,
       se.series_name, se.sequence_type, se.orientation,
       s.study_name, s.patient_id"""
_Q4_FROM_SERIES = """FROM series se
JOIN mri_image i ON i.series_id = se.series_id
JOIN study s     ON s.study_id  = se.study_id"""
Q4_REWRITTEN_BOTH = (f"""{_Q4_COLS}
{_Q4_FROM_SERIES}
WHERE se.sequence_type = %(seq)s AND se.orientation = %(ori)s
  AND i.image_id <> %(img)s
LIMIT %(lim)s
""",)
Q4_REWRITTEN_NONE = ("""SELECT i.image_id, i.file_name, i.file_path,
       se.series_name, se.sequence_type, se.orientation,
       s.study_name, s.patient_id
FROM mri_image i
JOIN series se ON se.series_id = i.series_id
JOIN study s   ON s.study_id   = se.study_id
WHERE i.image_id <> %(img)s
LIMIT %(lim)s
""",)

# Unlimited versions: used only to prove both Q4 forms select the same set.
Q4_SET_ORIGINAL = Q4_ORIGINAL[0].replace("LIMIT %(lim)s", "")
Q4_SET_REWRITTEN = Q4_REWRITTEN_BOTH[0].replace("LIMIT %(lim)s", "")

# --------------------------------------------------------------------- Q5
Q5_ORIGINAL_TMPL = "SELECT image_id, feature_vector FROM image_feature WHERE image_id IN ({ph})"


def q5(ids):
    return (Q5_ORIGINAL_TMPL.format(ph=",".join(f"%(f{k})s" for k in range(len(ids)))),)


# ======================================================================
def run_once(cur, stmts, params):
    rows_total = bytes_total = 0
    for sql in stmts:
        cur.execute(sql, params)
        rows = cur.fetchall()
        rows_total += len(rows)
        bytes_total += sum(len(str(v)) for r in rows for v in r if v is not None)
    return rows_total, bytes_total


def bench(cur, stmts, params, repeat, warmup=5):
    for _ in range(warmup):
        run_once(cur, stmts, params)
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        rows, size = run_once(cur, stmts, params)
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    return {
        "rows": rows, "bytes": size,
        "median_ms": round(statistics.median(times), 3),
        "p95_ms": round(times[max(int(len(times) * 0.95) - 1, 0)], 3),
        "mean_ms": round(statistics.mean(times), 3),
    }


def explain(cur, stmts, params, fh, header):
    fh.write("=" * 78 + "\n" + header + "\n" + "=" * 78 + "\n")
    for n, sql in enumerate(stmts, 1):
        cur.execute("EXPLAIN ANALYZE " + sql, params)
        text = "\n".join(r[0] for r in cur.fetchall())
        fh.write(f"-- statement {n}/{len(stmts)}\n{text}\n\n")


def fetch_set(cur, sql, params, col):
    cur.execute(sql, params)
    return sorted(r[col] for r in cur.fetchall() if r[col] is not None)


def connect(db=None):
    return mysql.connector.connect(
        host=os.getenv("HOST"), port=int(os.getenv("PORT", 3306)),
        user=os.getenv("USER"), password=os.getenv("PASSWORD"), database=db)


def build_baseline():
    """Copy data into mri_42_noindex: CREATE TABLE ... AS SELECT keeps no keys/indexes."""
    conn = connect()
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {NOINDEX_DB}")
    cur.execute(f"CREATE DATABASE {NOINDEX_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    for t in TABLES:
        cur.execute(f"CREATE TABLE {NOINDEX_DB}.{t} AS SELECT * FROM {REAL_DB}.{t}")
    cur.execute("ANALYZE TABLE " + ", ".join(f"{NOINDEX_DB}.{t}" for t in TABLES))
    cur.fetchall()
    conn.close()


def drop_baseline():
    conn = connect()
    conn.cursor().execute(f"DROP DATABASE IF EXISTS {NOINDEX_DB}")
    conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patient", default="0230")
    ap.add_argument("--sequence", default="T2")
    ap.add_argument("--orientation", default="SAG")
    ap.add_argument("--limit", type=int, default=50, help="candidate limit used by app.py")
    ap.add_argument("--repeat", type=int, default=200)
    a = ap.parse_args()

    print("Building baseline copy (no indexes) ...")
    build_baseline()

    # parameters that depend on the data
    conn = connect(REAL_DB)
    cur = conn.cursor(dictionary=True)
    cur.execute("""SELECT i.image_id FROM study s JOIN series se ON se.study_id=s.study_id
                   JOIN mri_image i ON i.series_id=se.series_id
                   WHERE s.patient_id=%s ORDER BY i.image_id""", (a.patient,))
    ids = [r["image_id"] for r in cur.fetchall()]
    if not ids:
        raise SystemExit(f"patient {a.patient} has no images - use --patient with another id")
    img = ids[len(ids) // 2]
    cur.execute("SELECT image_id FROM image_feature ORDER BY image_id LIMIT 50")
    feat_ids = [r["image_id"] for r in cur.fetchall()] or ids[:50]
    conn.close()

    P = {"pid": a.patient, "seq": a.sequence, "ori": a.orientation, "img": img, "lim": a.limit}
    P_NULL = dict(P, seq=None, ori=None)
    P5 = {f"f{k}": v for k, v in enumerate(feat_ids)}

    cases = [  # (name, statements, params)
        ("Q1 original",           Q1_ORIGINAL,         P),
        ("Q1 rewritten",          Q1_REWRITTEN,        P),
        ("Q2 original",           Q2_ORIGINAL,         P),
        ("Q2 rewritten",          Q2_REWRITTEN,        P),
        ("Q3 original (no rewrite)", Q3_ORIGINAL,      P),
        ("Q4 original  seq+ori",  Q4_ORIGINAL,         P),
        ("Q4 rewritten seq+ori",  Q4_REWRITTEN_BOTH,   P),
        ("Q4 original  no filter", Q4_ORIGINAL,        P_NULL),
        ("Q4 rewritten no filter", Q4_REWRITTEN_NONE,  P_NULL),
        ("Q5 original (no rewrite)", q5(feat_ids),     P5),
    ]

    results = []
    with open(HERE / "4_2_plans.txt", "w", encoding="utf-8") as plans:
        plans.write(f"patient={a.patient} image_id={img} seq={a.sequence} ori={a.orientation} limit={a.limit}\n\n")
        for label, db in (("A_no_index", NOINDEX_DB), ("B_indexed", REAL_DB)):
            conn = connect(db)
            cur = conn.cursor()
            plain = conn.cursor(dictionary=True)

            # ---- correctness: rewritten == original -------------------
            if label == "B_indexed":
                print("\nCorrectness checks (original vs rewritten):")
                for name, o, r, col in (
                        ("Q1 images", Q1_ORIGINAL[0], Q1_REWRITTEN[1], "image_id"),
                        ("Q2 images", Q2_ORIGINAL[0], Q2_REWRITTEN[1], "image_id"),
                        ("Q4 candidate set", Q4_SET_ORIGINAL, Q4_SET_REWRITTEN, "image_id")):
                    same = fetch_set(plain, o, P, col) == fetch_set(plain, r, P, col)
                    print(f"  {name:18s}: {'OK - identical' if same else 'MISMATCH !!!'}")
                # report text returned once instead of once per image row
                plain.execute(Q1_ORIGINAL[0], P)
                o = plain.fetchall()
                plain.execute(Q1_REWRITTEN[0], P)
                rep = plain.fetchall()
                same_rep = {(r["report_id"], r["clinician_notes"]) for r in o} == \
                           {(r["report_id"], r["clinician_notes"]) for r in rep}
                print(f"  Q1 report text    : {'OK - identical' if same_rep else 'MISMATCH !!!'}")

            # ---- timing + plans --------------------------------------
            print(f"\n[{label}]  database={db}")
            for name, stmts, params in cases:
                if name.startswith("Q5") and label == "A_no_index" and not feat_ids:
                    continue
                # Q5 without a primary key scans the whole feature table on every
                # call, so fewer repetitions are used there (still enough for a median).
                reps = min(a.repeat, 10) if (name.startswith("Q5") and label == "A_no_index") else a.repeat
                print(f"  running {name} ({reps} runs) ...", flush=True)
                r = bench(cur, stmts, params, reps, warmup=1 if reps < a.repeat else 5)
                r["runs"] = reps
                r.update(state=label, query=name)
                results.append(r)
                print(f"  {name:26s} rows={r['rows']:6d} bytes={r['bytes']:8d} "
                      f"median={r['median_ms']:8.3f} ms  p95={r['p95_ms']:8.3f} ms")
                explain(cur, stmts, params, plans, f"[{label}] {name}")
            conn.close()

    with open(HERE / "4_2_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["state", "query", "runs", "rows", "bytes", "median_ms", "p95_ms", "mean_ms"])
        w.writeheader()
        w.writerows(results)

    drop_baseline()
    print("\nDone. Files written next to this script: 4_2_results.csv, 4_2_plans.txt")


if __name__ == "__main__":
    main()
