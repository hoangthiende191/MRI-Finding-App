import io
import os
import numpy as np
import pydicom
from PIL import Image
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
def _read_pixels(path):
    path = Path(path)

    if not path.is_absolute():
        path = BASE_DIR / path

    ds = pydicom.dcmread(str(path))
    arr = ds.pixel_array.astype(np.float32)

    if arr.ndim > 2:
        arr = arr[0]

    if getattr(ds, "PhotometricInterpretation", "") == "MONOCHROME1":
        arr = arr.max() - arr

    return ds, arr


def normalize_to_uint8(arr):
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    low, high = np.percentile(arr, [1, 99])
    if high <= low:
        low, high = float(arr.min()), float(arr.max())
    if high <= low:
        return np.zeros(arr.shape, dtype=np.uint8)
    arr = np.clip((arr - low) / (high - low), 0, 1)
    return (arr * 255).astype(np.uint8)


def dicom_to_png_bytes(path):
    _, arr = _read_pixels(path)
    image = Image.fromarray(normalize_to_uint8(arr), mode="L")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _normalized_vector(path, size=(64, 64)):
    _, arr = _read_pixels(path)
    arr = normalize_to_uint8(arr)
    image = Image.fromarray(arr, mode="L").resize(size, Image.Resampling.BILINEAR)
    vec = np.asarray(image, dtype=np.float32) / 255.0
    return vec


