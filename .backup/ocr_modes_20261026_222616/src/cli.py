import argparse
import json
from pathlib import Path
import subprocess
import sys

from src.config import ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR văn bản in tiếng Việt — giai đoạn 1")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("ui", help="Mở giao diện tải ảnh")
    ocr = commands.add_parser("ocr", help="Đọc một ảnh, xuất TXT/JSON/PNG")
    ocr.add_argument("image", type=Path)
    ocr.add_argument("--out", type=Path, help="Thư mục chỉ định; bỏ trống để lưu từng lượt vào KetQua/OCR")
    ocr.add_argument("--min-score", type=float, default=0.5)
    ocr.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], default=0)
    ocr.add_argument("--model-size", choices=["tiny", "small", "medium"], default="small")
    ocr.add_argument("--backend", choices=["ppocrv6", "hybrid"], default="hybrid")
    evaluation = commands.add_parser("evaluate", help="So sánh văn bản OCR và bản chép chuẩn")
    evaluation.add_argument("--reference", type=Path, required=True)
    evaluation.add_argument("--prediction", type=Path, required=True)
    args = parser.parse_args()
    if args.command in (None, "ui"):
        return subprocess.call([
            sys.executable, "-m", "streamlit", "run", str(ROOT / "ui.py"),
            "--server.address", "127.0.0.1", "--browser.gatherUsageStats", "false",
        ], cwd=ROOT)
    try:
        if args.command == "evaluate":
            from src.metrics import evaluate_text
            metrics = evaluate_text(
                args.reference.read_text(encoding="utf-8-sig"),
                args.prediction.read_text(encoding="utf-8-sig"),
            )
            print(json.dumps(metrics, ensure_ascii=False, indent=2))
            return 0
        from src.image_io import load_image_file
        from src.ocr.engine import OCREngine
        from src.ocr.export import save_result
        from src.ocr.archive import save_run
        image = load_image_file(args.image, args.rotate)
        result = OCREngine(args.model_size, args.backend).recognize(image, args.image.name, args.min_score)
        if args.out is None:
            target = save_run(image, result, args.backend, args.model_size, args.image.read_bytes(), args.rotate)
        else:
            target = args.out
            save_result(image, result, target)
        print(result.text if result.text else "Không tìm thấy chữ đạt ngưỡng điểm đã chọn.")
        print(f"\nĐã lưu {len(result.lines)} vùng chữ tại: {target.resolve()}")
        return 0
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1
