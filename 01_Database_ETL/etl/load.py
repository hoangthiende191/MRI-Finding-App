"""
Load Module
-----------

This module loads transformed data into the MySQL database.

The database schema must be created before executing this module.
"""

import mysql.connector
from mysql.connector import Error


def get_connection(
    host,
    user,
    password,
    database,
    port=3306
):
    """
    Establish a connection to the MySQL database.
    """

    return mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        autocommit=False
    )


def load_patients_and_reports(
    conn,
    reports
):
    """
    Load patient and radiology report records.
    """

    cursor = conn.cursor()

    for record in reports:

        patient_id = record["patient_id"]
        clinician_notes = record[
            "clinician_notes"
        ]

        cursor.execute(
            """
            INSERT IGNORE INTO patient
                (patient_id)
            VALUES
                (%s)
            """,
            (patient_id,)
        )

        cursor.execute(
            """
            INSERT INTO radiology_report
                (
                    patient_id,
                    clinician_notes
                )
            VALUES
                (%s, %s)
            ON DUPLICATE KEY UPDATE
                clinician_notes =
                    VALUES(clinician_notes)
            """,
            (
                patient_id,
                clinician_notes
            )
        )

    conn.commit()
    cursor.close()


def load_mri_data(
    conn,
    records
):
    """
    Load transformed MRI records into the database.

    The function maintains the following hierarchy:

        PATIENT
            -> STUDY
                -> SERIES
                    -> MRI_IMAGE
    """

    cursor = conn.cursor()

    for record in records:

        patient_id = record["patient_id"]

        # ---------------------------------------------------------
        # PATIENT
        # ---------------------------------------------------------

        cursor.execute(
            """
            INSERT IGNORE INTO patient
                (patient_id)
            VALUES
                (%s)
            """,
            (patient_id,)
        )

        # ---------------------------------------------------------
        # STUDY
        # ---------------------------------------------------------

        cursor.execute(
            """
            INSERT INTO study
                (
                    patient_id,
                    study_name,
                    study_date
                )
            VALUES
                (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                study_date =
                    VALUES(study_date)
            """,
            (
                patient_id,
                record["study_name"],
                record["study_date"]
            )
        )

        cursor.execute(
            """
            SELECT study_id
            FROM study
            WHERE patient_id = %s
              AND study_name = %s
            """,
            (
                patient_id,
                record["study_name"]
            )
        )

        study_id = cursor.fetchone()[0]

        # ---------------------------------------------------------
        # SERIES
        # ---------------------------------------------------------

        cursor.execute(
            """
            INSERT INTO series
                (
                    study_id,
                    series_name,
                    sequence_type,
                    orientation
                )
            VALUES
                (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                sequence_type =
                    VALUES(sequence_type),
                orientation =
                    VALUES(orientation)
            """,
            (
                study_id,
                record["series_name"],
                record["sequence_type"],
                record["orientation"]
            )
        )

        cursor.execute(
            """
            SELECT series_id
            FROM series
            WHERE study_id = %s
              AND series_name = %s
            """,
            (
                study_id,
                record["series_name"]
            )
        )

        series_id = cursor.fetchone()[0]

        # ---------------------------------------------------------
        # MRI IMAGE
        # ---------------------------------------------------------

        cursor.execute(
            """
            INSERT IGNORE INTO mri_image
                (
                    series_id,
                    file_name,
                    file_path
                )
            VALUES
                (%s, %s, %s)
            """,
            (
                series_id,
                record["file_name"],
                record["file_path"]
            )
        )

    conn.commit()
    cursor.close()