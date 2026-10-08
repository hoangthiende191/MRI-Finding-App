from pathlib import Path

import numpy as np
import pydicom
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent.parent.parent


def create_image_feature(file_path):
    path = Path(file_path)

    if not path.is_absolute():
        path = BASE_DIR / path

    ds = pydicom.dcmread(str(path))
    arr = ds.pixel_array.astype(np.float32)

    min_value = arr.min()
    max_value = arr.max()

    if max_value > min_value:
        arr = (arr - min_value) / (max_value - min_value)
    else:
        arr = np.zeros_like(arr)

    image = Image.fromarray(arr)
    image = image.resize((64, 64), Image.Resampling.BILINEAR)

    feature = np.asarray(image, dtype=np.float32)
    feature = feature.flatten()

    return feature.tolist()