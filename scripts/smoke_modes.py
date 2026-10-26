"""Run each supported OCR configuration once and keep comparable outputs."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.image_io import load_image_file
from src.ocr.engine import OCREngine
from src.ocr.export import save_result
from src.ocr.options import CONFIGURATIONS


def main():
    image = load_image_file(ROOT / "samples" / "demo_tieng_viet.png")
    output = ROOT / "outputs" / "mode_validation"
    output.mkdir(parents=True, exist_ok=True)
    summary = []
    for name, (_, backend, size) in CONFIGURATIONS.items():
        sets = ("fast", "best", "standard") if backend.startswith("tesseract") else ("best",)
        for weights in sets:
            key = name + ("_" + weights if backend.startswith("tesseract") else "")
            try:
                result = OCREngine(size, backend, weights).recognize(image, "demo_tieng_viet.png", 0)
                assert result.lines, "No text detected"
                save_result(image, result, output / key)
                record = dict(mode=key, status="ok", seconds=round(result.elapsed_seconds, 3),
                              regions=len(result.lines), detection=result.detection_model,
                              recognition=result.recognition_model)
            except Exception as error:
                record = dict(mode=key, status="failed", error=str(error))
            summary.append(record)
            print(json.dumps(record, ensure_ascii=True), flush=True)
            (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return int(any(record["status"] != "ok" for record in summary))


if __name__ == "__main__":
    raise SystemExit(main())
