-- =====================================================================
-- Phase 4.2 - Query Processing & Optimization : SETUP
--
-- Run this file ONCE on mri_radiology_db (after 01_Database/database/
-- schema.sql and procedures.sql have been loaded and the data imported).
-- It only CREATES objects; the experiments and measurements are in
-- 4_2_test.sql.
--
-- Scope: every query the application sends to MySQL
--   Q1  get_patient_mri(patient_id)                       (Application 1)
--   Q2  search_patient_mri(patient_id, sequence, orient)  (Application 1)
--   Q3  get_image_record(image_id)                        (Application 2)
--   Q4  get_similarity_candidates(image_id, seq, orient, limit)  (App 2)
--   Q5  SELECT ... FROM image_feature WHERE image_id IN (...)    (App 2)
--
-- What this file changes
--   * Indexes : none added. The primary/unique keys and the indexes created by
--     schema.sql (idx_study_patient, idx_study_date, idx_series_study,
--     idx_series_sequence_type, idx_series_orientation, idx_image_series)
--     already cover every join and filter of Q1-Q5; 4_2_test.sql proves this with EXPLAIN ANALYZE.
--     Adding more would only be a redundant index (extra write cost).
--   * Rewritten queries : get_patient_mri_opt and search_patient_mri_opt
--     (below). The original procedures are left untouched so before/after
--     can be compared side by side.
--   * Q3 and Q5 : primary-key lookups, already optimal -> no rewrite.
--   * Q4 : a rewrite (one branch per parameter combination instead of the
--     "(? IS NULL OR col = ?)" catch-all) was evaluated in 4_2_benchmark.py;
--     it gave no measurable gain (MySQL already folds the constant
--     parameters), so it is NOT adopted and get_similarity_candidates stays
--     as it is.
-- =====================================================================
USE mri_radiology_db;

DROP PROCEDURE IF EXISTS get_patient_mri_opt;
DROP PROCEDURE IF EXISTS search_patient_mri_opt;

DELIMITER //

-- ---------------------------------------------------------------------
-- Q1 rewrite : get_patient_mri_opt
-- Problem in the original: one 5-table LEFT JOIN repeats patient_id and
-- clinician_notes (a long text) on EVERY image row, and the LEFT JOINs
-- on patient/report add nothing to the image lookup.
-- Rewrite: two small result sets.
--   1) patient + report (0 or 1 row; no row = patient does not exist)
--   2) images, read through study -> series -> mri_image
-- The caller reads the report once instead of once per image.
-- ---------------------------------------------------------------------
CREATE PROCEDURE get_patient_mri_opt(
    IN p_patient_id VARCHAR(10)
)
BEGIN
    SELECT p.patient_id,
           rr.report_id,
           rr.clinician_notes
    FROM patient p
    LEFT JOIN radiology_report rr ON rr.patient_id = p.patient_id
    WHERE p.patient_id = p_patient_id;

    SELECT s.study_id, s.study_name, s.study_date,
           se.series_id, se.series_name, se.sequence_type, se.orientation,
           i.image_id, i.file_name, i.file_path
    FROM study s
    JOIN series se   ON se.study_id  = s.study_id
    JOIN mri_image i ON i.series_id  = se.series_id
    WHERE s.patient_id = p_patient_id
    ORDER BY s.study_date, se.series_id, i.image_id;
END //

-- ---------------------------------------------------------------------
-- Q2 rewrite : search_patient_mri_opt  (same idea as Q1)
-- ---------------------------------------------------------------------
CREATE PROCEDURE search_patient_mri_opt(
    IN p_patient_id    VARCHAR(10),
    IN p_sequence_type VARCHAR(50),
    IN p_orientation   VARCHAR(10)
)
BEGIN
    SELECT p.patient_id,
           rr.report_id,
           rr.clinician_notes
    FROM patient p
    LEFT JOIN radiology_report rr ON rr.patient_id = p.patient_id
    WHERE p.patient_id = p_patient_id;

    SELECT s.study_id, s.study_name, s.study_date,
           se.series_id, se.series_name, se.sequence_type, se.orientation,
           i.image_id, i.file_name, i.file_path
    FROM study s
    JOIN series se   ON se.study_id  = s.study_id
    JOIN mri_image i ON i.series_id  = se.series_id
    WHERE s.patient_id      = p_patient_id
      AND se.sequence_type  = p_sequence_type
      AND se.orientation    = p_orientation
    ORDER BY s.study_date, se.series_id, i.image_id;
END //

DELIMITER ;

-- Check
SELECT routine_name FROM information_schema.routines
WHERE routine_schema = 'mri_radiology_db' AND routine_name LIKE '%\_opt'
ORDER BY routine_name;
