"""So sánh smoke test trên cùng ảnh; không phải benchmark ảnh chụp thực tế."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.image_io import load_image_file
from src.metrics import evaluate_text
from src.ocr.engine import OCREngine
from src.ocr.export import save_result


def main():
    image_path = ROOT / "samples" / "demo_tieng_viet.png"
    image = load_image_file(image_path)
    reference = image_path.with_suffix(".txt").read_text(encoding="utf-8")
    rows = []
    for size in ("tiny", "small", "medium"):
        engine = OCREngine(model_size=size, backend="ppocrv6")
        result = engine.recognize(image, image_path.name)
        save_result(image, result, ROOT / "outputs" / f"v6_{size}")
        # Đo lại khi đã nạp mô hình, không tính thời gian tải từ mạng.
        warm = engine.recognize(image, image_path.name)
        metrics = evaluate_text(reference, result.text)
        row = {"model": f"PP-OCRv6_{size}", **metrics,
               "warm_seconds": round(warm.elapsed_seconds, 3), "lines": len(result.lines)}
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    target = ROOT / "outputs" / "v6_comparison.json"
    target.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
