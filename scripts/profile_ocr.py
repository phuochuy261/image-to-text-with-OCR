"""Profile current OCR stages on local fixtures; keep cold and warm runs separate."""
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ocr.engine import HybridOCREngine
from src.ocr.long_lines import recognize_lines, split_line


def main():
    engine = HybridOCREngine()
    image = Image.open(ROOT / "outputs/long_lines/generated_page.png").convert("RGB")
    pixels = np.asarray(image)[:, :, ::-1].copy()
    rows = []
    for run in ("cold", "warm"):
        row = {"run": run}
        started = perf_counter()
        detector = engine._get_pipeline()
        row["detector_load_seconds"] = perf_counter() - started
        started = perf_counter()
        polygons = list(detector.predict(pixels))[0]["dt_polys"]
        row["detection_seconds"] = perf_counter() - started
        started = perf_counter()
        recognizer = engine._get_recognizer()
        row["recognizer_load_seconds"] = perf_counter() - started
        started = perf_counter()
        crops = [engine._crop_line(image, polygon) for polygon in polygons]
        row["crop_seconds"] = perf_counter() - started
        row["detected_lines"] = len(crops)
        row["recognition_parts"] = sum(len(split_line(crop)) for crop in crops)
        started = perf_counter()
        predictions, _ = recognize_lines(recognizer, crops)
        row["texts"] = [text for text, _ in predictions]
        row["recognition_seconds"] = perf_counter() - started
        rows.append(row)
        print(json.dumps({key:value for key,value in row.items() if key != "texts"}), flush=True)
    target = ROOT / "outputs/performance"
    target.mkdir(parents=True, exist_ok=True)
    (target / "stage_profile_after.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")


if __name__ == "__main__":
    main()
