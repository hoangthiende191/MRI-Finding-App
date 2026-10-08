# MRI Radiology Database Web Application

A Flask + MySQL web application implementing the three required MRI database applications.

## Applications

### Application 1 — Patient MRI & Report
Input a `patient_id` and retrieve:
- radiology report
- studies
- series
- MRI images

### Application 2 — Conditional MRI Search
Input:
- patient ID
- sequence type (T1/T2)
- orientation (SAG/TRA/COR)

The backend executes a relational query across `patient`, `study`, `series`, and `mri_image`.

### Application 3 — Similar MRI Search
Select an `image_id`. The application:
1. prefers candidate images with matching sequence/orientation;
2. reads the `.ima`/DICOM files with `pydicom`;
3. resizes normalized grayscale images to 64x64;
4. computes pixel similarity using mean absolute difference;
5. combines pixel similarity with sequence/orientation metadata;
6. displays the top 12 results.

This is a lightweight, reproducible similarity baseline for the course demo. It is not a clinical diagnostic or deep-learning similarity model.

## Architecture

```text
Browser
   |
   v
Flask Web Application
   |
   +---- MySQL: patient / radiology_report / study / series / mri_image
   |
   +---- Filesystem: original .ima MRI files
   |
   +---- pydicom + NumPy + Pillow: .ima -> PNG preview
```

The database stores the original MRI file path. The browser receives a PNG representation from `/image/<image_id>`; the `.ima` path is not exposed in the UI.

## Setup

1. Create the database using your existing `schema.sql`.
2. Make sure your ETL has loaded the patient/report/MRI metadata and `mri_image.file_path` points to the real `.ima` files.
3. Create a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\\Scripts\\activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Copy `.env.example` to `.env` and enter the same MySQL connection values used by the ETL.
6. Run:

```bash
python app.py
```

7. Open `http://localhost:5000`.

## Important path check

Before starting the web app, verify that the file paths stored in MySQL are accessible from the machine running Flask:

```sql
SELECT image_id, file_name, file_path
FROM mri_image
LIMIT 10;
```

The Flask process must be able to read those `.ima` files.

## DBMS demonstration

Application 1 and 2 are intentionally query-driven so they can be used in the DBMS presentation:

- Application 1: patient -> study -> series -> image retrieval
- Application 2: filtering by `patient_id`, `sequence_type`, and `orientation`
- Indexes in the provided schema support these access patterns
- Use `EXPLAIN` / `EXPLAIN ANALYZE` in your MySQL version to demonstrate query processing and indexing

Do not claim Application 3 is an AI medical-image model. Present it as a lightweight image-similarity baseline unless you later add a dedicated feature-extraction model.
