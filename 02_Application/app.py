from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from dotenv import load_dotenv
import os
import io

from db import (
    get_db_connection,
    search_patient_by_id,
    search_patient_by_condition,
    fetch_image_record,
    fetch_similarity_candidates,
    fetch_image_features,
)

from dicom_utils import dicom_to_png_bytes

import numpy as np

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "mri-demo-secret")


@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Application 1
# Retrieve radiology report + MRI images by patient ID
# ---------------------------------------------------------------------------
@app.route("/application/1", methods=["GET", "POST"])
def application_1():
    patient_id = (request.values.get("patient_id") or "").strip()
    data = None

    if patient_id:
        data = search_patient_by_id(patient_id)
        if data is None:
            flash(f"Patient {patient_id} was not found.", "warning")

    return render_template("application1.html", patient_id=patient_id, data=data)


# ---------------------------------------------------------------------------
# Application 2
# Retrieve MRI images by patient ID + sequence/orientation conditions
# ---------------------------------------------------------------------------
@app.route("/application/2", methods=["GET", "POST"])
def application_2():
    patient_id = (request.values.get("patient_id") or "").strip()
    sequence_type = (request.values.get("sequence_type") or "").strip()
    orientation = (request.values.get("orientation") or "").strip()

    rows = []
    if patient_id:
        rows = search_patient_by_condition(patient_id, sequence_type or None, orientation or None)
        if not rows:
            flash("No MRI images matched the selected conditions.", "warning")

    return render_template(
        "application2.html",
        patient_id=patient_id,
        sequence_type=sequence_type,
        orientation=orientation,
        rows=rows,
    )


# ---------------------------------------------------------------------------
# Application 3
# Similar-image search.
# Baseline implementation:
#   1. Restrict candidates using MRI metadata where possible.
#   2. Compare normalized DICOM pixel arrays using mean absolute difference.
#   3. Combine pixel similarity with sequence/orientation metadata similarity.
# ---------------------------------------------------------------------------
@app.route("/application/3", methods=["GET", "POST"])
def application_3():

    patient_id = (request.values.get("patient_id") or "").strip()
    selected_image_id = request.values.get("image_id", type=int)

    patient_data = None
    selected = None
    results = []

    # ---------------------------------------------------------
    # STEP 1: Find MRI images belonging to patient
    # ---------------------------------------------------------

    if patient_id:
        patient_data = search_patient_by_id(patient_id)

        if patient_data is None:
            flash(f"Patient {patient_id} was not found.", "warning")

    # ---------------------------------------------------------
    # STEP 2: User selected one MRI image
    # ---------------------------------------------------------

    if selected_image_id:

        selected = fetch_image_record(selected_image_id)

        if selected is None:
            flash("MRI image was not found.", "warning")

        else:

            # Get candidate images
            candidates = fetch_similarity_candidates(
                selected["image_id"],
                selected["sequence_type"],
                selected["orientation"],
                limit=50,
            )

            # Get all feature vectors in ONE database query
            candidate_ids = [
                candidate["image_id"]
                for candidate in candidates
            ]

            all_ids = [selected["image_id"]] + candidate_ids

            features = fetch_image_features(all_ids)

            selected_feature = features.get(
                selected["image_id"]
            )

            if selected_feature is not None:

                selected_vector = np.asarray(
                    selected_feature,
                    dtype=np.float32
                )

                scored = []

                for candidate in candidates:

                    candidate_feature = features.get(
                        candidate["image_id"]
                    )

                    if candidate_feature is None:
                        continue

                    candidate_vector = np.asarray(
                        candidate_feature,
                        dtype=np.float32
                    )

                    # Same similarity idea as the old implementation:
                    # normalized mean absolute difference.
                    distance = np.mean(
                        np.abs(
                            selected_vector -
                            candidate_vector
                        )
                    )

                    similarity = max(
                        0.0,
                        1.0 - float(distance)
                    )

                    candidate["similarity"] = round(
                        similarity * 100,
                        1
                    )

                    scored.append(candidate)

                scored.sort(
                    key=lambda x: x["similarity"],
                    reverse=True
                )

                results = scored[:12]

            else:
                flash(
                    "Feature vector for the selected MRI was not found.",
                    "warning"
                )

    return render_template(
        "application3.html",
        patient_id=patient_id,
        patient_data=patient_data,
        selected=selected,
        results=results,
        selected_image_id=selected_image_id,
    )


# ---------------------------------------------------------------------------
# Image endpoint
# Browser asks for /image/<id>; Flask reads the .ima/DICOM file and returns
# a PNG representation. The .ima path itself is never exposed to the user.
# ---------------------------------------------------------------------------
@app.route("/image/<int:image_id>")
def image(image_id):
    record = fetch_image_record(image_id)
    if not record:
        return "Image not found", 404

    try:
        png_bytes = dicom_to_png_bytes(record["file_path"])
    except Exception as exc:
        app.logger.exception("Unable to render DICOM image %s", image_id)
        return f"Unable to render MRI image: {exc}", 500

    return send_file(io.BytesIO(png_bytes), mimetype="image/png")


def start_app():
    app.run(
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", 5000)),
        debug=False
    )


if __name__ == "__main__":
    start_app()
