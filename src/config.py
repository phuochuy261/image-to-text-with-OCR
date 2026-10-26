"""Thiết lập đường dẫn trước khi import PaddleOCR."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_ROOT = ROOT / "outputs" / "runs"
DETECTION_MODEL = "PP-OCRv6_small_det"
RECOGNITION_MODEL = "vietocr_vgg_transformer"
MAX_PIXELS = 20_000_000
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def configure_runtime() -> None:
    # Mô hình tải lần đầu được giữ cùng dự án, không cần tải mỗi lần chạy.
    cache = ROOT / ".cache"
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(cache / "paddlex"))
    os.environ.setdefault("PADDLE_HOME", str(cache / "paddle"))
    os.environ.setdefault("TORCH_HOME", str(cache / "torch"))
    # Bỏ bước thăm dò tất cả máy chủ; tải mô hình vẫn xác thực HTTPS bình thường.
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
