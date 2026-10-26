"""Bộ chuyển đổi PaddleOCR -> OCRDocument, nạp mô hình khi thực sự cần."""
from pathlib import Path
from threading import Lock
from time import perf_counter

import numpy as np
from PIL import Image, ImageOps

from src.config import RECOGNITION_MODEL, configure_runtime
from src.ocr.long_lines import recognize_lines
from src.ocr.result import OCRDocument, parse_lines


class HybridOCREngine:
    def __init__(self, model_size: str = "small", detection_model: str | None = None):
        self.detection_model = detection_model or f"PP-OCRv6_{model_size}_det"
        self._pipeline = None
        self._recognizer = None
        self._lock = Lock()

    def _get_pipeline(self):
        if self._pipeline is None:
            configure_runtime()
            from paddleocr import TextDetection
            self._pipeline = TextDetection(
                model_name=self.detection_model,
                device="cpu",
                enable_mkldnn=False,
                cpu_threads=4,
            )
        return self._pipeline

    def _get_recognizer(self):
        if self._recognizer is None:
            from src.ocr.vietnamese import create_recognizer
            self._recognizer = create_recognizer()
        return self._recognizer

    @staticmethod
    def _crop_line(image: Image.Image, polygon, rgb_pixels=None) -> Image.Image:
        import cv2
        points = np.asarray(polygon, dtype=np.float32)
        width = max(2, round(max(np.linalg.norm(points[1] - points[0]),
                                 np.linalg.norm(points[2] - points[3]))))
        height = max(2, round(max(np.linalg.norm(points[3] - points[0]),
                                  np.linalg.norm(points[2] - points[1]))))
        destination = np.array([[0, 0], [width-1, 0], [width-1, height-1],
                                [0, height-1]], dtype=np.float32)
        transform = cv2.getPerspectiveTransform(points, destination)
        if rgb_pixels is None:
            rgb_pixels = np.asarray(image.convert("RGB"))
        crop = cv2.warpPerspective(rgb_pixels, transform,
                                   (width, height), borderValue=(255, 255, 255))
        return ImageOps.expand(Image.fromarray(crop), border=2, fill="white")

    def recognize(self, image: Image.Image, source_name: str = "image.png",
                  min_score: float = 0.5) -> OCRDocument:
        if not 0 <= min_score <= 1:
            raise ValueError("Ngưỡng điểm OCR phải nằm trong [0, 1].")
        started = perf_counter()
        timings = {}
        # PaddleOCR đọc ndarray ở thứ tự BGR; PIL dùng RGB.
        rgb_pixels = np.asarray(image.convert("RGB"))
        pixels = rgb_pixels[:, :, ::-1].copy()
        wait_started = perf_counter()
        with self._lock:
            timings["queue"] = perf_counter() - wait_started
            stage = perf_counter()
            pipeline = self._get_pipeline()
            timings["detector_load"] = perf_counter() - stage
            stage = perf_counter()
            pages = list(pipeline.predict(pixels))
            timings["detection"] = perf_counter() - stage
            if len(pages) != 1:
                raise RuntimeError(f"Dự kiến một ảnh, nhưng OCR trả về {len(pages)} trang.")
            polygons = pages[0]["dt_polys"]
            texts, scores = [], []
            part_count = 0
            if len(polygons):
                stage = perf_counter()
                recognizer = self._get_recognizer()
                timings["recognizer_load"] = perf_counter() - stage
                stage = perf_counter()
                crops = [self._crop_line(image, polygon, rgb_pixels) for polygon in polygons]
                timings["crop"] = perf_counter() - stage
                stage = perf_counter()
                predictions, part_count = recognize_lines(recognizer, crops)
                timings["recognition"] = perf_counter() - stage
                texts = [text for text, _ in predictions]
                scores = [float(score) for _, score in predictions]
        lines = parse_lines({"rec_texts": texts, "rec_scores": scores,
                             "rec_polys": polygons}, min_score)
        return OCRDocument(
            source_name=Path(source_name).name,
            width=image.width, height=image.height, lines=lines,
            min_score=min_score, elapsed_seconds=perf_counter() - started,
            detection_model=self.detection_model, recognition_model=RECOGNITION_MODEL,
            timings=timings, recognition_parts=part_count,
        )


class OCREngine:
    """API chung: mặc định v6 tìm vùng chữ + VietOCR nhận dạng tiếng Việt."""
    def __init__(self, model_size: str = "small", backend: str = "hybrid",
                 tessdata_set: str = "best", psm: int = 3):
        if model_size not in {"tiny", "small", "medium"}:
            raise ValueError("Kích thước mô hình phải là tiny, small hoặc medium.")
        if backend not in {"ppocrv6", "hybrid", "hybrid_v5", "ppocrv5", "ppocrv3",
                           "tesseract", "tesseract_vietocr"}:
            raise ValueError("Backend OCR không hợp lệ.")
        self.model_size = model_size
        self.backend = backend
        self._pipeline = None
        self._hybrid = HybridOCREngine(model_size) if backend == "hybrid" else None
        if backend == "hybrid_v5":
            self._hybrid = HybridOCREngine(model_size, "PP-OCRv5_server_det")
        if backend in {"tesseract", "tesseract_vietocr"}:
            from src.ocr.tesseract import TesseractOCREngine
            self._hybrid = TesseractOCREngine(tessdata_set, psm, backend == "tesseract_vietocr")
        self._lock = Lock()

    def _get_pipeline(self):
        if self._pipeline is None:
            configure_runtime()
            from paddleocr import PaddleOCR
            detection, recognition = self.model_names()
            self._pipeline = PaddleOCR(
                text_detection_model_name=detection,
                text_recognition_model_name=recognition,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                device="cpu", enable_mkldnn=False, cpu_threads=4,
                text_rec_score_thresh=0.0,
            )
        return self._pipeline

    def model_names(self):
        if self.backend == "ppocrv3":
            return "PP-OCRv3_mobile_det", "latin_PP-OCRv3_mobile_rec"
        if self.backend == "ppocrv5":
            return "PP-OCRv5_server_det", "latin_PP-OCRv5_mobile_rec"
        return f"PP-OCRv6_{self.model_size}_det", f"PP-OCRv6_{self.model_size}_rec"

    def recognize(self, image: Image.Image, source_name: str = "image.png",
                  min_score: float = 0.5) -> OCRDocument:
        if self._hybrid is not None:
            return self._hybrid.recognize(image, source_name, min_score)
        if not 0 <= min_score <= 1:
            raise ValueError("Ngưỡng điểm OCR phải nằm trong [0, 1].")
        started = perf_counter()
        pixels = np.asarray(image.convert("RGB"))[:, :, ::-1].copy()
        timings = {}
        wait_started = perf_counter()
        with self._lock:
            timings["queue"] = perf_counter() - wait_started
            stage = perf_counter()
            pipeline = self._get_pipeline()
            timings["pipeline_load"] = perf_counter() - stage
            stage = perf_counter()
            pages = list(pipeline.predict(pixels))
            timings["pipeline_inference"] = perf_counter() - stage
        if len(pages) != 1:
            raise RuntimeError(f"Dự kiến một ảnh, nhưng OCR trả về {len(pages)} trang.")
        return OCRDocument(
            source_name=Path(source_name).name, width=image.width, height=image.height,
            lines=parse_lines(pages[0], min_score), min_score=min_score,
            elapsed_seconds=perf_counter() - started,
            detection_model=self.model_names()[0],
            recognition_model=self.model_names()[1],
            timings=timings,
        )
