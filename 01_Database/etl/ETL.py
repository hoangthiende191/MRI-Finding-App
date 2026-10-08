from extract import extract_radiology_reports, extract_mri_data
from transform import transform_reports, transform_mri_records
from load import get_connection, load_patients_and_reports, load_mri_data
from pathlib import Path

import os
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parents[2]

# Extract
def run_etl():
    reports_df = extract_radiology_reports(
        BASE_DIR / "Data Raw" / "Radiologists Report.xlsx"
    )

    mri_raw = extract_mri_data(
        BASE_DIR / "Data Raw" / "01_MRI_Data"
    )


    # Transform
    reports = transform_reports(
        reports_df
    )

    mri_records = transform_mri_records(
        mri_raw
    )

    # Connect DB

    conn = get_connection(
        host=os.getenv("HOST"),
        user=os.getenv("USER"),
        password= os.getenv("PASSWORD"),
        database= os.getenv("DATABASE_NAME"),
        port = os.getenv("PORT")
    )


    # Load
    load_patients_and_reports(
        conn,
        reports
    )

    load_mri_data(
        conn,
        mri_records
    )


    conn.close()

    print("Pipeline finished")
if __name__ == "__main__":
    run_etl()