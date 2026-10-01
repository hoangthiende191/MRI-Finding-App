from extract import extract_radiology_reports, extract_mri_data
from transform import transform_reports, transform_mri_records
from load import get_connection, load_patients_and_reports, load_mri_data

import os
from dotenv import load_dotenv

load_dotenv()
# Extract
reports_df = extract_radiology_reports(
    r"Data Raw/Radiologists Report.xlsx"
)

mri_raw = extract_mri_data(
    r"Data Raw/01_MRI_Data"
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