"""Keep a separate, named result folder for each completed UI/CLI run."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata
from uuid import uuid4

from PIL import Image

from src.config import RESULTS_ROOT
from src.ocr.export import save_result

VIETNAM_TIME = timezone(timedelta(hours=7))


def source_slug(name: str) -> str:
    value = unicodedata.normalize("NFKD", Path(name).stem.replace("đ", "d").replace("Đ", "D"))
    value = value.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")[:40] or "image"


def save_run(image: Image.Image, document, backend: str, model_size: str,
             source_bytes: bytes, rotation: int = 0, root: Path | None = None) -> Path:
    now = datetime.now(VIETNAM_TIME)
    recognition = "vietocr-transformer" if backend == "hybrid" else f"ppocrv6-{model_size}"
    detector = f"v6-{model_size}"
    if backend not in {"hybrid", "ppocrv6"}:
        recognition = source_slug(document.recognition_model)
        detector = source_slug(document.detection_model)
    name = (f"{now:%Y%m%d_%H%M%S}_{now.microsecond // 1000:03d}"
            f"__{backend}__det-{detector}__rec-{recognition}"
            f"__{source_slug(document.source_name)}__{uuid4().hex[:8]}")
    directory = (RESULTS_ROOT if root is None else Path(root)) / f"{now:%Y-%m-%d}" / name
    directory.mkdir(parents=True, exist_ok=False)
    save_result(image, document, directory)
    image.save(directory / "input.png")
    metadata = {"saved_at": now.isoformat(), "timezone": "Asia/Ho_Chi_Minh",
                "backend": backend, "model_size": model_size,
                "source_name": document.source_name, "source_sha256": sha256(source_bytes).hexdigest(),
                "rotation_clockwise": rotation, "min_score": document.min_score,
                "detection_model": document.detection_model, "recognition_model": document.recognition_model,
                "decoder": ("cached_greedy_batch" if backend in {"hybrid", "hybrid_v5", "tesseract_vietocr"}
                            else "tesseract_lstm" if backend == "tesseract" else "paddleocr"),
                "elapsed_seconds": document.elapsed_seconds, "timings_seconds": document.timings,
                "files": {"input": "input.png", "regions": "annotated.png", "text": "text.txt",
                          "result": "result.json"}}
    (directory / "run.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return directory
