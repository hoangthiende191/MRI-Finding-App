"""
Extract Module
--------------

This module extracts raw data from the source datasets:

1. Radiologists Report Excel file
2. MRI directory structure

The extracted data is returned in Python data structures
and passed to the transformation stage.
"""

import os
import pandas as pd


def extract_radiology_reports(file_path):
    """
    Extract radiology report data from the Excel file.

    Parameters
    ----------
    file_path : str
        Path to the Radiologists Report Excel file.

    Returns
    -------
    pandas.DataFrame
        Raw radiology report data.
    """

    df = pd.read_excel(file_path)

    # Normalize column names.
    df.columns = [column.strip() for column in df.columns]

    return df


def extract_mri_data(mri_root):
    """
    Extract raw metadata from the MRI directory structure.

    Expected structure:

        MRI_Data/
            Patient/
                Study/
                    Series/
                        Image files

    Returns
    -------
    list
        Raw MRI metadata records.
    """

    records = []

    for patient_id in sorted(os.listdir(mri_root)):

        patient_path = os.path.join(
            mri_root,
            patient_id
        )

        if not os.path.isdir(patient_path):
            continue

        for study_name in sorted(os.listdir(patient_path)):

            study_path = os.path.join(
                patient_path,
                study_name
            )

            if not os.path.isdir(study_path):
                continue

            for series_name in sorted(
                os.listdir(study_path)
            ):

                series_path = os.path.join(
                    study_path,
                    series_name
                )

                if not os.path.isdir(series_path):
                    continue

                for file_name in sorted(
                    os.listdir(series_path)
                ):

                    if not file_name.lower().endswith(".ima"):
                        continue

                    file_path = os.path.join(
                        series_path,
                        file_name
                    )

                    if not os.path.isfile(file_path):
                        continue

                    records.append({
                        "patient_id": patient_id,
                        "study_name": study_name,
                        "series_name": series_name,
                        "file_name": file_name,
                        "file_path": file_path
                    })

    return records