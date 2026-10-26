"""Tesseract line detection, optionally read by the existing VietOCR pipeline."""
import csv
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from time import perf_counter

from src.config import ROOT, RECOGNITION_MODEL
from src.ocr.engine import HybridOCREngine
from src.ocr.long_lines import recognize_lines
from src.ocr.result import OCRDocument, parse_lines


def parse_tsv(table):
    groups = {}
    for row in csv.DictReader(table.splitlines(), delimiter="\t", quoting=csv.QUOTE_NONE):
        if row["level"] != "5" or not row["text"].strip() or float(row["conf"]) < 0:
            continue
        key = tuple(row[k] for k in ("page_num", "block_num", "par_num", "line_num"))
        x, y, w, h = (int(row[k]) for k in ("left", "top", "width", "height"))
        group = groups.setdefault(key, {"rect": [x, y, x+w, y+h], "texts": [], "scores": []})
        rect = group["rect"]
        rect[:] = [min(rect[0], x), min(rect[1], y), max(rect[2], x+w), max(rect[3], y+h)]
        group["texts"].append(row["text"])
        group["scores"].append(float(row["conf"]) / 100)
    return list(groups.values())


class TesseractOCREngine(HybridOCREngine):
    def __init__(self, tessdata_set="best", psm=3, use_vietocr=False):
        super().__init__()
        if tessdata_set not in {"fast", "best", "standard"} or psm not in {3, 4, 6, 7, 11}:
            raise ValueError("Bộ Tesseract hoặc PSM không hợp lệ.")
        self.tessdata_set = tessdata_set
        self.psm = psm
        self.use_vietocr = use_vietocr
        self.detection_model = f"tesseract-{tessdata_set}-psm{psm}"

    def recognize(self, image, source_name="image.png", min_score=0.5):
        if not 0 <= min_score <= 1:
            raise ValueError("Ngưỡng điểm OCR phải nằm trong [0, 1].")
        started = perf_counter()
        timings = {}
        executable = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        data_dir = ROOT / ".cache" / "tessdata" / self.tessdata_set
        if not all((data_dir / f"{language}.traineddata").is_file() for language in ("vie", "eng")):
            raise RuntimeError(f"Thiếu trọng số Tesseract tại {data_dir}. Chạy scripts/setup_tesseract.py.")
        wait = perf_counter()
        with self._lock:
            timings["queue"] = perf_counter() - wait
            stage = perf_counter()
            with tempfile.TemporaryDirectory(prefix="ocr_tesseract_") as temporary:
                input_path = Path(temporary) / "input.png"
                image.convert("RGB").save(input_path)
                result = subprocess.run([executable, str(input_path), "stdout", "--tessdata-dir", str(data_dir),
                                         "-l", "vie+eng", "--oem", "1", "--psm", str(self.psm),
                                         "-c", "tessedit_create_tsv=1"],
                                        capture_output=True, encoding="utf-8", errors="replace", timeout=120,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if result.returncode:
                    raise RuntimeError(result.stderr.strip())
            groups = parse_tsv(result.stdout)
            timings["detection" if self.use_vietocr else "pipeline_inference"] = perf_counter() - stage
            polygons = [[[x1,y1],[x2,y1],[x2,y2],[x1,y2]] for x1,y1,x2,y2 in (g["rect"] for g in groups)]
            part_count = 0
            if self.use_vietocr and groups:
                stage = perf_counter()
                recognizer = self._get_recognizer()
                timings["recognizer_load"] = perf_counter() - stage
                stage = perf_counter()
                crops = [self._crop_line(image, polygon) for polygon in polygons]
                timings["crop"] = perf_counter() - stage
                stage = perf_counter()
                predictions, part_count = recognize_lines(recognizer, crops)
                timings["recognition"] = perf_counter() - stage
                texts = [text for text, score in predictions]
                scores = [float(score) for text, score in predictions]
            else:
                texts = [" ".join(group["texts"]) for group in groups]
                scores = [sum(group["scores"])/len(group["scores"]) for group in groups]
        return OCRDocument(source_name=Path(source_name).name, width=image.width, height=image.height,
                           lines=parse_lines(dict(rec_texts=texts, rec_scores=scores, rec_polys=polygons), min_score),
                           min_score=min_score, elapsed_seconds=perf_counter()-started,
                           detection_model=self.detection_model,
                           recognition_model=RECOGNITION_MODEL if self.use_vietocr else f"tesseract-{self.tessdata_set}-vie-eng",
                           timings=timings, recognition_parts=part_count)
