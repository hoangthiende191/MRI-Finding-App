"""
Transform Module
----------------

This module transforms raw extracted data into a structured
format suitable for loading into the relational database.

Main operations:

1. Normalize patient identifiers.
2. Parse study dates.
3. Parse MRI sequence types and orientations.
4. Clean radiology report text.
"""

import re
from datetime import datetime

import pandas as pd


def transform_patient_id(value):
    """
    Normalize a patient ID to a four-digit string.

    Example:
        1     -> "0001"
        12    -> "0012"
        1234  -> "1234"
    """

    if pd.isna(value):
        return None

    return str(int(value)).zfill(4)


def transform_reports(df):
    """
    Transform the raw radiology report DataFrame.

    Returns
    -------
    list
        Structured patient and report records.
    """

    records = []

    for _, row in df.iterrows():

        patient_id = transform_patient_id(
            row["Patient ID"]
        )

        if not patient_id:
            continue

        notes = row.get("Clinician's Notes")

        if pd.isna(notes):
            notes = None
        else:
            notes = str(notes).strip()

        records.append({
            "patient_id": patient_id,
            "clinician_notes": notes
        })

    return records


def parse_study_date(study_name):
    """
    Extract a date in YYYYMMDD format from the study name.

    Example:
        L-SPINE_LSS_20160309_091629_240000
        -> 2016-03-09
    """

    match = re.search(
        r"(19|20)\d{6}",
        study_name
    )

    if not match:
        return None

    try:
        return datetime.strptime(
            match.group(0),
            "%Y%m%d"
        ).date()

    except ValueError:
        return None


def parse_series_info(series_name):
    """
    Extract sequence type and orientation from a series name.

    Examples
    --------
    T2_TSE_SAG_384_0002
        -> T2, SAG

    T1_TSE_TRA_0005
        -> T1, TRA

    LOCALIZER_0001
        -> None, None
    """

    tokens = series_name.split("_")

    sequence_type = None
    orientation = None

    if tokens:

        first_token = tokens[0].upper()

        if first_token in ("T1", "T2"):
            sequence_type = first_token

    for token in tokens:

        token = token.upper()

        if token in ("SAG", "TRA", "COR"):
            orientation = token
            break

    return sequence_type, orientation


def transform_mri_records(records):
    """
    Transform raw MRI metadata into structured records.

    The function adds:
        - study_date
        - sequence_type
        - orientation
    """

    transformed_records = []

    for record in records:

        study_date = parse_study_date(
            record["study_name"]
        )

        sequence_type, orientation = (
            parse_series_info(
                record["series_name"]
            )
        )

        transformed_records.append({
            "patient_id": record["patient_id"],
            "study_name": record["study_name"],
            "study_date": study_date,
            "series_name": record["series_name"],
            "sequence_type": sequence_type,
            "orientation": orientation,
            "file_name": record["file_name"],
            "file_path": record["file_path"]
        })

    return transformed_records