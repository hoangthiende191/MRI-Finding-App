-- =====================================================================
-- Phase 4.2 - Query Processing & Optimization : TEST
--
-- Run 4_2_setup.sql first. This file only reads data (plus one throw-away
-- helper database, dropped in section 7).
-- Requires MySQL 8.0.18+ (EXPLAIN ANALYZE).
--
-- How to use (MySQL Workbench): run ONE block at a time (select it, then
-- Ctrl+Enter). Each EXPLAIN ANALYZE returns a single text cell: right-click
-- it -> Copy Field. Run each EXPLAIN ANALYZE twice and keep the second run
-- (data already in the buffer pool). A faster alternative that measures
-- all queries repeatedly is 4_2_benchmark.py.
--
-- Queries tested (the SELECT bodies of the application's stored procedures,
-- because EXPLAIN ANALYZE does not accept CALL):
--   Q1 get_patient_mri       Q2 search_patient_mri     Q3 get_image_record
--   Q4 get_similarity_candidates                       Q5 image_feature lookup
-- States: A = no index (helper copy mri_42_noindex)
--         B = real schema with the Phase 4.1 indexes (mri_radiology_db)
-- =====================================================================

-- =====================================================================
-- 0. Environment and test parameters
-- =====================================================================

USE mri_radiology_db;
SELECT VERSION();                       -- must be >= 8.0.18

SELECT 'patient' AS tbl, COUNT(*) AS n FROM patient
UNION ALL SELECT 'radiology_report', COUNT(*) FROM radiology_report
UNION ALL SELECT 'study',            COUNT(*) FROM study
UNION ALL SELECT 'series',           COUNT(*) FROM series
UNION ALL SELECT 'mri_image',        COUNT(*) FROM mri_image
UNION ALL SELECT 'image_feature',    COUNT(*) FROM image_feature;

-- Existing indexes (read-only listing)
SELECT table_name, index_name,
       GROUP_CONCAT(column_name ORDER BY seq_in_index) AS cols
FROM information_schema.statistics
WHERE table_schema = 'mri_radiology_db'
GROUP BY table_name, index_name
ORDER BY table_name, index_name;

ANALYZE TABLE patient, radiology_report, study, series, mri_image, image_feature;

SET @pid = '0230', @seq = 'T2', @ori = 'SAG';           -- edit if needed
SELECT MIN(i.image_id) INTO @img                        -- an image of that patient
FROM study s JOIN series se ON se.study_id = s.study_id
JOIN mri_image i ON i.series_id = se.series_id
WHERE s.patient_id = @pid;
SELECT @pid, @seq, @ori, @img;

-- =====================================================================
-- 1. State A: copy of the data without any key or index
-- =====================================================================

DROP DATABASE IF EXISTS mri_42_noindex;
CREATE DATABASE mri_42_noindex CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE TABLE mri_42_noindex.patient          AS SELECT * FROM mri_radiology_db.patient;
CREATE TABLE mri_42_noindex.radiology_report AS SELECT * FROM mri_radiology_db.radiology_report;
CREATE TABLE mri_42_noindex.study            AS SELECT * FROM mri_radiology_db.study;
CREATE TABLE mri_42_noindex.series           AS SELECT * FROM mri_radiology_db.series;
CREATE TABLE mri_42_noindex.mri_image        AS SELECT * FROM mri_radiology_db.mri_image;
CREATE TABLE mri_42_noindex.image_feature    AS SELECT * FROM mri_radiology_db.image_feature;
ANALYZE TABLE mri_42_noindex.patient, mri_42_noindex.radiology_report,
              mri_42_noindex.study, mri_42_noindex.series,
              mri_42_noindex.mri_image, mri_42_noindex.image_feature;

-- =====================================================================
-- 2. Q1 get_patient_mri - ORIGINAL
-- =====================================================================
-- State A (no index)
USE mri_42_noindex;
EXPLAIN ANALYZE
SELECT p.patient_id, rr.report_id, rr.clinician_notes,
       s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM patient p
LEFT JOIN radiology_report rr ON p.patient_id = rr.patient_id
LEFT JOIN study s             ON p.patient_id = s.patient_id
LEFT JOIN series se           ON s.study_id   = se.study_id
LEFT JOIN mri_image i         ON se.series_id = i.series_id
WHERE p.patient_id = @pid
ORDER BY s.study_date, se.series_id, i.image_id;

-- State B (Phase 4.1 indexes)
USE mri_radiology_db;
EXPLAIN ANALYZE
SELECT p.patient_id, rr.report_id, rr.clinician_notes,
       s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM patient p
LEFT JOIN radiology_report rr ON p.patient_id = rr.patient_id
LEFT JOIN study s             ON p.patient_id = s.patient_id
LEFT JOIN series se           ON s.study_id   = se.study_id
LEFT JOIN mri_image i         ON se.series_id = i.series_id
WHERE p.patient_id = @pid
ORDER BY s.study_date, se.series_id, i.image_id;

-- =====================================================================
-- 2b. Q1 REWRITTEN (get_patient_mri_opt) - two statements
-- =====================================================================
-- Statement 1: patient + report (one row)
USE mri_radiology_db;
EXPLAIN ANALYZE
SELECT p.patient_id, rr.report_id, rr.clinician_notes
FROM patient p
LEFT JOIN radiology_report rr ON rr.patient_id = p.patient_id
WHERE p.patient_id = @pid;

-- Statement 2: images
EXPLAIN ANALYZE
SELECT s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM study s
JOIN series se   ON se.study_id = s.study_id
JOIN mri_image i ON i.series_id = se.series_id
WHERE s.patient_id = @pid
ORDER BY s.study_date, se.series_id, i.image_id;

-- =====================================================================
-- 3. Q2 search_patient_mri - ORIGINAL
-- =====================================================================
-- State A (no index)
USE mri_42_noindex;
EXPLAIN ANALYZE
SELECT p.patient_id, rr.report_id, rr.clinician_notes,
       s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM patient p
JOIN study s                  ON p.patient_id = s.patient_id
JOIN series se                ON s.study_id   = se.study_id
JOIN mri_image i              ON se.series_id = i.series_id
LEFT JOIN radiology_report rr ON p.patient_id = rr.patient_id
WHERE p.patient_id = @pid
  AND se.sequence_type = @seq
  AND se.orientation   = @ori
ORDER BY s.study_date, se.series_id, i.image_id;

-- State B (Phase 4.1 indexes)
USE mri_radiology_db;
EXPLAIN ANALYZE
SELECT p.patient_id, rr.report_id, rr.clinician_notes,
       s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM patient p
JOIN study s                  ON p.patient_id = s.patient_id
JOIN series se                ON s.study_id   = se.study_id
JOIN mri_image i              ON se.series_id = i.series_id
LEFT JOIN radiology_report rr ON p.patient_id = rr.patient_id
WHERE p.patient_id = @pid
  AND se.sequence_type = @seq
  AND se.orientation   = @ori
ORDER BY s.study_date, se.series_id, i.image_id;

-- =====================================================================
-- 3b. Q2 REWRITTEN (search_patient_mri_opt) - image statement
-- =====================================================================
USE mri_radiology_db;
EXPLAIN ANALYZE
SELECT s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM study s
JOIN series se   ON se.study_id = s.study_id
JOIN mri_image i ON i.series_id = se.series_id
WHERE s.patient_id     = @pid
  AND se.sequence_type = @seq
  AND se.orientation   = @ori
ORDER BY s.study_date, se.series_id, i.image_id;

-- =====================================================================
-- 4. Q3 get_image_record (primary-key lookup, no rewrite)
-- =====================================================================
-- State A (no index)
USE mri_42_noindex;
EXPLAIN ANALYZE
SELECT i.image_id, i.file_name, i.file_path,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       s.study_id, s.study_name, s.study_date, s.patient_id
FROM mri_image i
JOIN series se ON se.series_id = i.series_id
JOIN study s   ON s.study_id   = se.study_id
WHERE i.image_id = @img;

-- State B (Phase 4.1 indexes)
USE mri_radiology_db;
EXPLAIN ANALYZE
SELECT i.image_id, i.file_name, i.file_path,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       s.study_id, s.study_name, s.study_date, s.patient_id
FROM mri_image i
JOIN series se ON se.series_id = i.series_id
JOIN study s   ON s.study_id   = se.study_id
WHERE i.image_id = @img;

-- =====================================================================
-- 5. Q4 get_similarity_candidates (no rewrite adopted)
-- =====================================================================
-- State A (no index)
USE mri_42_noindex;
EXPLAIN ANALYZE
SELECT i.image_id, i.file_name, i.file_path,
       se.series_name, se.sequence_type, se.orientation,
       s.study_name, s.patient_id
FROM mri_image i
JOIN series se ON se.series_id = i.series_id
JOIN study s   ON s.study_id   = se.study_id
WHERE i.image_id <> @img
  AND (@seq IS NULL OR se.sequence_type = @seq)
  AND (@ori IS NULL OR se.orientation   = @ori)
LIMIT 50;

-- State B (Phase 4.1 indexes)
USE mri_radiology_db;
EXPLAIN ANALYZE
SELECT i.image_id, i.file_name, i.file_path,
       se.series_name, se.sequence_type, se.orientation,
       s.study_name, s.patient_id
FROM mri_image i
JOIN series se ON se.series_id = i.series_id
JOIN study s   ON s.study_id   = se.study_id
WHERE i.image_id <> @img
  AND (@seq IS NULL OR se.sequence_type = @seq)
  AND (@ori IS NULL OR se.orientation   = @ori)
LIMIT 50;

-- Alternative evaluated and NOT adopted: plain predicates instead of the
-- "(? IS NULL OR col = ?)" catch-all. Same plan shape, no measurable gain.
USE mri_radiology_db;
EXPLAIN ANALYZE
SELECT i.image_id, i.file_name, i.file_path,
       se.series_name, se.sequence_type, se.orientation,
       s.study_name, s.patient_id
FROM series se
JOIN mri_image i ON i.series_id = se.series_id
JOIN study s     ON s.study_id  = se.study_id
WHERE se.sequence_type = @seq
  AND se.orientation   = @ori
  AND i.image_id <> @img
LIMIT 50;

-- =====================================================================
-- 6. Q5 image_feature lookup by primary key (no rewrite)
-- =====================================================================
USE mri_radiology_db;
EXPLAIN ANALYZE
SELECT image_id, feature_vector
FROM image_feature
WHERE image_id IN (@img, @img + 1, @img + 2, @img + 3, @img + 4);

-- =====================================================================
-- 7. Correctness: rewritten queries return the same rows as the originals
-- =====================================================================
USE mri_radiology_db;
SET SESSION group_concat_max_len = 100000000;

SELECT 'Q1 images' AS check_name,
       (SELECT COUNT(*) FROM (SELECT p.patient_id, rr.report_id, rr.clinician_notes,
       s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM patient p
LEFT JOIN radiology_report rr ON p.patient_id = rr.patient_id
LEFT JOIN study s             ON p.patient_id = s.patient_id
LEFT JOIN series se           ON s.study_id   = se.study_id
LEFT JOIN mri_image i         ON se.series_id = i.series_id
WHERE p.patient_id = @pid) o)  AS rows_original,
       (SELECT COUNT(*) FROM (SELECT s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM study s
JOIN series se   ON se.study_id = s.study_id
JOIN mri_image i ON i.series_id = se.series_id
WHERE s.patient_id = @pid) n)   AS rows_rewritten,
       IF((SELECT MD5(GROUP_CONCAT(image_id ORDER BY image_id)) FROM (SELECT p.patient_id, rr.report_id, rr.clinician_notes,
       s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM patient p
LEFT JOIN radiology_report rr ON p.patient_id = rr.patient_id
LEFT JOIN study s             ON p.patient_id = s.patient_id
LEFT JOIN series se           ON s.study_id   = se.study_id
LEFT JOIN mri_image i         ON se.series_id = i.series_id
WHERE p.patient_id = @pid) o WHERE image_id IS NOT NULL) =
          (SELECT MD5(GROUP_CONCAT(image_id ORDER BY image_id)) FROM (SELECT s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM study s
JOIN series se   ON se.study_id = s.study_id
JOIN mri_image i ON i.series_id = se.series_id
WHERE s.patient_id = @pid) n),
          'IDENTICAL', 'DIFFERENT') AS image_ids;

SELECT 'Q2 images' AS check_name,
       (SELECT COUNT(*) FROM (SELECT p.patient_id, rr.report_id, rr.clinician_notes,
       s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM patient p
JOIN study s                  ON p.patient_id = s.patient_id
JOIN series se                ON s.study_id   = se.study_id
JOIN mri_image i              ON se.series_id = i.series_id
LEFT JOIN radiology_report rr ON p.patient_id = rr.patient_id
WHERE p.patient_id = @pid
  AND se.sequence_type = @seq
  AND se.orientation   = @ori) o)  AS rows_original,
       (SELECT COUNT(*) FROM (SELECT s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM study s
JOIN series se   ON se.study_id = s.study_id
JOIN mri_image i ON i.series_id = se.series_id
WHERE s.patient_id     = @pid
  AND se.sequence_type = @seq
  AND se.orientation   = @ori) n)   AS rows_rewritten,
       IF((SELECT MD5(GROUP_CONCAT(image_id ORDER BY image_id)) FROM (SELECT p.patient_id, rr.report_id, rr.clinician_notes,
       s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM patient p
JOIN study s                  ON p.patient_id = s.patient_id
JOIN series se                ON s.study_id   = se.study_id
JOIN mri_image i              ON se.series_id = i.series_id
LEFT JOIN radiology_report rr ON p.patient_id = rr.patient_id
WHERE p.patient_id = @pid
  AND se.sequence_type = @seq
  AND se.orientation   = @ori) o WHERE image_id IS NOT NULL) =
          (SELECT MD5(GROUP_CONCAT(image_id ORDER BY image_id)) FROM (SELECT s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM study s
JOIN series se   ON se.study_id = s.study_id
JOIN mri_image i ON i.series_id = se.series_id
WHERE s.patient_id     = @pid
  AND se.sequence_type = @seq
  AND se.orientation   = @ori) n),
          'IDENTICAL', 'DIFFERENT') AS image_ids;

SELECT 'Q4 candidate set (no LIMIT)' AS check_name,
       (SELECT COUNT(*) FROM (SELECT i.image_id, i.file_name, i.file_path,
       se.series_name, se.sequence_type, se.orientation,
       s.study_name, s.patient_id
FROM mri_image i
JOIN series se ON se.series_id = i.series_id
JOIN study s   ON s.study_id   = se.study_id
WHERE i.image_id <> @img
  AND (@seq IS NULL OR se.sequence_type = @seq)
  AND (@ori IS NULL OR se.orientation   = @ori)) o)  AS rows_original,
       (SELECT COUNT(*) FROM (SELECT i.image_id, i.file_name, i.file_path,
       se.series_name, se.sequence_type, se.orientation,
       s.study_name, s.patient_id
FROM series se
JOIN mri_image i ON i.series_id = se.series_id
JOIN study s     ON s.study_id  = se.study_id
WHERE se.sequence_type = @seq
  AND se.orientation   = @ori
  AND i.image_id <> @img) n)   AS rows_rewritten,
       IF((SELECT MD5(GROUP_CONCAT(image_id ORDER BY image_id)) FROM (SELECT i.image_id, i.file_name, i.file_path,
       se.series_name, se.sequence_type, se.orientation,
       s.study_name, s.patient_id
FROM mri_image i
JOIN series se ON se.series_id = i.series_id
JOIN study s   ON s.study_id   = se.study_id
WHERE i.image_id <> @img
  AND (@seq IS NULL OR se.sequence_type = @seq)
  AND (@ori IS NULL OR se.orientation   = @ori)) o WHERE image_id IS NOT NULL) =
          (SELECT MD5(GROUP_CONCAT(image_id ORDER BY image_id)) FROM (SELECT i.image_id, i.file_name, i.file_path,
       se.series_name, se.sequence_type, se.orientation,
       s.study_name, s.patient_id
FROM series se
JOIN mri_image i ON i.series_id = se.series_id
JOIN study s     ON s.study_id  = se.study_id
WHERE se.sequence_type = @seq
  AND se.orientation   = @ori
  AND i.image_id <> @img) n),
          'IDENTICAL', 'DIFFERENT') AS image_ids;

-- Q1 report: original repeats it on every image row, rewritten returns it once
SELECT COUNT(*)                                   AS image_rows_in_original,
       COUNT(DISTINCT report_id)                  AS distinct_reports,
       MAX(LENGTH(clinician_notes))               AS report_bytes,
       COUNT(*) * MAX(LENGTH(clinician_notes))    AS report_bytes_sent_original,
       MAX(LENGTH(clinician_notes))               AS report_bytes_sent_rewritten
FROM (SELECT p.patient_id, rr.report_id, rr.clinician_notes,
       s.study_id, s.study_name, s.study_date,
       se.series_id, se.series_name, se.sequence_type, se.orientation,
       i.image_id, i.file_name, i.file_path
FROM patient p
LEFT JOIN radiology_report rr ON p.patient_id = rr.patient_id
LEFT JOIN study s             ON p.patient_id = s.patient_id
LEFT JOIN series se           ON s.study_id   = se.study_id
LEFT JOIN mri_image i         ON se.series_id = i.series_id
WHERE p.patient_id = @pid) t;

-- =====================================================================
-- 8. Cleanup
-- =====================================================================
DROP DATABASE IF EXISTS mri_42_noindex;
