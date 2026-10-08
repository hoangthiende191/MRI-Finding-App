import os
import mysql.connector
import json
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("HOST", "localhost"),
        port=int(os.getenv("PORT", "3306")),
        user=os.getenv("USER", "root"),
        password=os.getenv("PASSWORD", ""),
        database=os.getenv("DATABASE_NAME", "mri_radiology_db"),
    )


def search_patient_by_id(patient_id):
    conn = get_db_connection()

    try:
        cur = conn.cursor(dictionary=True)

        cur.callproc(
            "get_patient_mri",
            (patient_id,)
        )

        rows = []

        for result in cur.stored_results():
            rows.extend(result.fetchall())

        if not rows:
            return None

        # Thông tin patient/report lấy từ row đầu tiên
        patient = {
            "patient_id": rows[0]["patient_id"],
            "report_id": rows[0]["report_id"],
            "clinician_notes": rows[0]["clinician_notes"]
        }

        # Các MRI images
        images = []

        for row in rows:
            images.append({
                "study_id": row["study_id"],
                "study_name": row["study_name"],
                "study_date": row["study_date"],
                "series_id": row["series_id"],
                "series_name": row["series_name"],
                "sequence_type": row["sequence_type"],
                "orientation": row["orientation"],
                "image_id": row["image_id"],
                "file_name": row["file_name"],
                "file_path": row["file_path"]
            })

        return {
            "patient": patient,
            "images": images
        }

    finally:
        conn.close()


def search_patient_by_condition(patient_id, sequence_type=None, orientation=None):
    conn = get_db_connection()

    try:
        cur = conn.cursor(dictionary=True)

        # Convert empty values to NULL
        if sequence_type == "":
            sequence_type = None

        if orientation == "":
            orientation = None

        cur.callproc(
            "search_patient_mri",
            (
                patient_id,
                sequence_type,
                orientation
            )
        )

        results = []

        for result in cur.stored_results():
            results.extend(result.fetchall())

        return results

    finally:
        conn.close()


def fetch_image_record(image_id):
    conn = get_db_connection()

    try:
        cur = conn.cursor(dictionary=True)

        cur.callproc(
            "get_image_record",
            (image_id,)
        )

        results = []

        for result in cur.stored_results():
            results.extend(result.fetchall())

        return results[0] if results else None

    finally:
        conn.close()


def fetch_similarity_candidates(
    image_id,
    sequence_type,
    orientation,
    limit=150
):
    conn = get_db_connection()

    try:
        cur = conn.cursor(dictionary=True)

        cur.callproc(
            "get_similarity_candidates",
            (
                image_id,
                sequence_type,
                orientation,
                limit
            )
        )

        results = []

        for result in cur.stored_results():
            results.extend(result.fetchall())

        return results

    finally:
        conn.close()

def fetch_image_features(image_ids):
    if not image_ids:
        return {}

    conn = get_db_connection()

    try:
        cur = conn.cursor(dictionary=True)

        placeholders = ",".join(["%s"] * len(image_ids))

        sql = f"""
            SELECT
                image_id,
                feature_vector
            FROM image_feature
            WHERE image_id IN ({placeholders})
        """

        cur.execute(sql, tuple(image_ids))

        results = {}

        for row in cur.fetchall():
            feature = row["feature_vector"]

            if isinstance(feature, str):
                feature = json.loads(feature)

            results[row["image_id"]] = feature

        return results

    finally:
        conn.close()