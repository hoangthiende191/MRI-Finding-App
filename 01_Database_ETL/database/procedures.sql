
USE mri_radiology_db
DELIMITER //

CREATE PROCEDURE get_patient_mri(
    IN p_patient_id VARCHAR(10)
)
BEGIN

    SELECT
        p.patient_id,

        rr.report_id,
        rr.clinician_notes,

        s.study_id,
        s.study_name,
        s.study_date,

        se.series_id,
        se.series_name,
        se.sequence_type,
        se.orientation,

        i.image_id,
        i.file_name,
        i.file_path

    FROM patient p

    LEFT JOIN radiology_report rr
        ON p.patient_id = rr.patient_id

    LEFT JOIN study s
        ON p.patient_id = s.patient_id

    LEFT JOIN series se
        ON s.study_id = se.study_id

    LEFT JOIN mri_image i
        ON se.series_id = i.series_id

    WHERE p.patient_id = p_patient_id

    ORDER BY
        s.study_date,
        se.series_id,
        i.image_id;

END //


CREATE PROCEDURE search_patient_mri(
    IN p_patient_id VARCHAR(10),
    IN p_sequence_type VARCHAR(50),
    IN p_orientation VARCHAR(10)
)
BEGIN

    SELECT
        p.patient_id,

        rr.report_id,
        rr.clinician_notes,

        s.study_id,
        s.study_name,
        s.study_date,

        se.series_id,
        se.series_name,
        se.sequence_type,
        se.orientation,

        i.image_id,
        i.file_name,
        i.file_path

    FROM patient p

    JOIN study s
        ON p.patient_id = s.patient_id

    JOIN series se
        ON s.study_id = se.study_id

    JOIN mri_image i
        ON se.series_id = i.series_id

    LEFT JOIN radiology_report rr
        ON p.patient_id = rr.patient_id

    WHERE p.patient_id = p_patient_id
      AND se.sequence_type = p_sequence_type
      AND se.orientation = p_orientation

    ORDER BY
        s.study_date,
        se.series_id,
        i.image_id;
END //


CREATE PROCEDURE get_image_record(
    IN p_image_id INT
)
BEGIN
    SELECT
        i.image_id,
        i.file_name,
        i.file_path,

        se.series_id,
        se.series_name,
        se.sequence_type,
        se.orientation,

        s.study_id,
        s.study_name,
        s.study_date,
        s.patient_id

    FROM mri_image i

    JOIN series se
        ON se.series_id = i.series_id

    JOIN study s
        ON s.study_id = se.study_id

    WHERE i.image_id = p_image_id;
END //

CREATE PROCEDURE get_similarity_candidates(
    IN p_image_id INT,
    IN p_sequence_type VARCHAR(50),
    IN p_orientation VARCHAR(10),
    IN p_limit INT
)
BEGIN

    SELECT
        i.image_id,
        i.file_name,
        i.file_path,

        se.series_name,
        se.sequence_type,
        se.orientation,

        s.study_name,
        s.patient_id

    FROM mri_image i

    JOIN series se
        ON se.series_id = i.series_id

    JOIN study s
        ON s.study_id = se.study_id

    WHERE i.image_id <> p_image_id

      AND (
            p_sequence_type IS NULL
            OR se.sequence_type = p_sequence_type
          )

      AND (
            p_orientation IS NULL
            OR se.orientation = p_orientation
          )

    LIMIT p_limit;

END //
DELIMITER ;
