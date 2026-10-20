-- =====================================================================
-- MRI Radiology Database — Phase 4.3: Transactions (SETUP)
--
-- Creates the two transaction procedures used by Phase 4.3.
-- Run this file first, then 4_3_test.sql.
-- Safe to run again: each procedure is dropped and recreated.
--
--   add_patient_with_report  Scenario A: INSERT patient + INSERT radiology_report
--   amend_report_and_study   Scenario B: UPDATE radiology_report + UPDATE study
--
-- Both procedures wrap their steps in one transaction. An EXIT HANDLER
-- catches any SQL error, rolls back every step and re-raises the error.
-- =====================================================================

USE mri_radiology_db;


-- ---------------------------------------------------------------------
-- Scenario A: register a new patient together with their report
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS add_patient_with_report;
DELIMITER //
CREATE PROCEDURE add_patient_with_report(
    IN p_patient_id VARCHAR(10),
    IN p_notes      LONGTEXT      -- LONGTEXT so an oversize note reaches the INSERT and fails there
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;     -- undo every step of this transaction
        RESIGNAL;     -- pass the original error back to the caller
    END;

    START TRANSACTION;
        INSERT INTO patient (patient_id) VALUES (p_patient_id);
        INSERT INTO radiology_report (patient_id, clinician_notes)
        VALUES (p_patient_id, p_notes);
    COMMIT;
END //
DELIMITER ;


-- ---------------------------------------------------------------------
-- Scenario B: amend a report and correct its study
--   Validates that the study belongs to the patient, then updates both
--   tables. study_date is derived from the date inside study_name,
--   so both columns change together.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS amend_report_and_study;
DELIMITER //
CREATE PROCEDURE amend_report_and_study(
    IN p_patient_id VARCHAR(10),
    IN p_study_id   INT,
    IN p_new_notes  LONGTEXT,
    IN p_new_date   VARCHAR(20)     -- a string, so a bad date fails inside the UPDATE, not at CALL
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

        -- consistency rule: the study must belong to this patient
        IF NOT EXISTS (SELECT 1 FROM study
                        WHERE study_id = p_study_id AND patient_id = p_patient_id) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Study does not belong to this patient';
        END IF;

        -- step 1: amend the report
        UPDATE radiology_report
           SET clinician_notes = p_new_notes
         WHERE patient_id = p_patient_id;

        -- step 2: fix the study. study_name goes FIRST: MySQL applies SET left to right,
        -- so DATE_FORMAT(study_date, ...) must still read the old date
        UPDATE study
           SET study_name = REPLACE(study_name, DATE_FORMAT(study_date, '%Y%m%d'), REPLACE(p_new_date, '-', '')),
               study_date = p_new_date
         WHERE study_id = p_study_id AND patient_id = p_patient_id;

    COMMIT;
END //
DELIMITER ;
