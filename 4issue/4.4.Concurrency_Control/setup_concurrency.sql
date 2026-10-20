-- Phase 4.4 : Concurrency control
USE mri_radiology_db;

-- PART 0: Initial Data setup
--1.
SELECT @@transaction_isolation AS default_isolation_level,
       @@innodb_lock_wait_timeout AS lock_wait_timeout_seconds;
--2.
UPDATE radiology_report 
SET clinician_notes = 'INITIAL: Patient presenting with mild L4-L5 lumbar disc degeneration.'
WHERE patient_id = '0001';
-- 3.Confirm initial state before running tests
SELECT patient_id, report_id, clinician_notes 
FROM radiology_report 
WHERE patient_id = '0001';