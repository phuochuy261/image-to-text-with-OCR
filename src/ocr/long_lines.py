"""Read long lines in smaller images, splitting only at visible whitespace."""
from math import ceil

import numpy as np
from PIL import Image, ImageOps


def split_line(image: Image.Image, image_height: int = 32,
               max_width: int = 512) -> list[Image.Image]:
    """Keep short lines intact; partition long lines at gaps between words.

    Limits refer to the width after VietOCR scales the image to image_height.
    Every source column belongs to exactly one part. If there is no safe gap,
    leave the remaining image intact for the recognizer's normal resize.
    """
    if image_height <= 0 or max_width <= 0:
        raise ValueError("Kích thước ảnh nhận dạng phải lớn hơn 0.")
    width_limit = max(1, int(max_width * image.height / image_height) - 4)
    if image.width <= width_limit:
        return [image]

    import cv2
    gray = np.asarray(image.convert("L"))
    _, foreground = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    if np.count_nonzero(foreground) > foreground.size / 2:
        foreground = 255 - foreground
    occupied = np.any(foreground, axis=0)
    ink = np.flatnonzero(occupied)
    if not len(ink):
        return [image]
    # Ignore narrow inter-letter spaces and the white margins of the crop.
    min_gap = max(2, ceil(image.height * 0.15))
    changes = np.diff(np.r_[False, ~occupied, False].astype(np.int8))
    gaps = [(int(start), int(end)) for start, end in
            zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1))
            if end - start >= min_gap and start > ink[0] and end <= ink[-1]]
    cuts = [0]
    while image.width - cuts[-1] > width_limit:
        left = cuts[-1]
        remaining = image.width - left
        target = left + remaining / ceil(remaining / width_limit)
        candidates = [(start + end) // 2 for start, end in gaps
                      if left + width_limit * 0.25 < (start + end) // 2 <= left + width_limit]
        if not candidates:
            break
        cuts.append(min(candidates, key=lambda cut: abs(cut - target)))
    cuts.append(image.width)
    if len(cuts) == 2:
        return [image]
    return [ImageOps.expand(image.crop((left, 0, right, image.height)), border=2, fill="white")
            for left, right in zip(cuts, cuts[1:])]


def recognize_line(recognizer, image: Image.Image) -> tuple[str, float]:
    """Join adjacent parts into one detected line; retain the weakest score."""
    dataset = recognizer.config["dataset"]
    parts = split_line(image, dataset["image_height"], dataset["image_max_width"])
    results = [recognizer.predict(part, return_prob=True) for part in parts]
    return join_predictions(results)


def join_predictions(results) -> tuple[str, float]:
    text = " ".join(value.strip() for value, _ in results if value.strip())
    return text, min(float(score) for _, score in results)


def recognize_lines(recognizer, crops: list[Image.Image]):
    """Batch same-sized parts, then restore the detector's original line order."""
    dataset = recognizer.config["dataset"]
    groups = [split_line(crop, dataset["image_height"], dataset["image_max_width"]) for crop in crops]
    parts = [part for group in groups for part in group]
    if not parts:
        return [], 0
    if hasattr(recognizer, "predict_batch"):
        texts, scores = recognizer.predict_batch(parts, return_prob=True)
        predictions = list(zip(texts, scores))
    else:
        predictions = [recognizer.predict(part, return_prob=True) for part in parts]
    lines, offset = [], 0
    for group in groups:
        lines.append(join_predictions(predictions[offset:offset + len(group)]))
        offset += len(group)
    return lines, len(parts)
