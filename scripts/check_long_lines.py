"""Reproduce long-line truncation on generated text, without changing source images."""
import json
from dataclasses import replace
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.metrics import evaluate_text
from src.ocr.engine import HybridOCREngine
from src.ocr.export import save_result
from src.ocr.long_lines import recognize_line, split_line
from src.ocr.result import parse_lines
from src.ocr.vietnamese import create_recognizer


LINES = [
    "Tóc bạc thường được xem là dấu hiệu của tuổi tác, khiến nhiều phụ nữ lựa chọn",
    "nhuộm đen để lấy lại vẻ ngoài trẻ trung. Thế nhưng, không ít người nhận ra rằng mái",
    "tóc đen tuyền đôi khi khiến gương mặt trông cứng nhắc, thiếu tự nhiên, trong khi",
    "những lọn tóc bạc được chăm sóc chỉn chu lại tạo nên vẻ thanh lịch, hiện đại. Bí",
    'quyết không nằm ở việc tóc bạc có khả năng "trẻ hóa" diện mạo, mà ở cách màu tóc',
    "hài hòa với làn da, đường nét gương mặt và phong cách cá nhân. Dưới đây là những",
    "lý do khiến tóc bạc tự nhiên đôi khi trở thành lựa chọn đáng thử hơn việc nhuộm đen",
    "toàn bộ mái tóc.",
]


def render_line(text, font):
    bounds = font.getbbox(text)
    image = Image.new("RGB", (bounds[2] - bounds[0] + 8, bounds[3] - bounds[1] + 8), "white")
    ImageDraw.Draw(image).text((4 - bounds[0], 4 - bounds[1]), text, font=font, fill="black")
    return image


def main():
    from vietocr.tool.translate import process_input, translate

    output = ROOT / "outputs" / "long_lines"
    output.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/times.ttf", 24)
    images = [render_line(text, font) for text in LINES]
    page = Image.new("RGB", (max(image.width for image in images) + 60, 60 + 44 * len(images)), "white")
    for index, image in enumerate(images):
        page.paste(image, (30, 30 + index * 44))
    page.save(output / "generated_page.png")
    (output / "reference.txt").write_text("\n".join(LINES), encoding="utf-8")
    recognizer = create_recognizer()
    rows = []
    cases = list(zip(LINES, images))
    # Exceeds translate()'s default 128-character decoding limit in one image.
    extended = " ".join(LINES[:3])
    cases.append((extended, render_line(extended, font)))
    for index, (reference, image) in enumerate(cases, 1):
        started = perf_counter()
        recognizer.config["dataset"]["image_max_width"] = 1024
        baseline, score = recognizer.predict(image, return_prob=True)
        row = {"line": index, "reference": reference, "crop_size": image.size,
               "baseline": baseline, "baseline_score": float(score),
               "baseline_metrics": evaluate_text(reference, baseline)}
        if index == 1:
            image.save(output / "first_line.png")
            tensor = process_input(image, 32, 32, 1024).to(recognizer.device)
            tokens, _ = translate(tensor, recognizer.model, max_seq_length=256)
            row.update({"input_width": tensor.shape[-1], "decode_limit_256": recognizer.vocab.decode(tokens[0].tolist()),
                        "end_token_seen": bool(np.any(tokens[0] == 2)), "decoded_steps": int(tokens.shape[-1] - 1)})
        recognizer.config["dataset"]["image_max_width"] = 512
        row["width_cap_512"] = recognizer.predict(image)
        fixed, fixed_score = recognize_line(recognizer, image)
        parts = split_line(image)
        for part_index, part in enumerate(parts, 1):
            part.save(output / f"line_{index}_part_{part_index}.png")
        row.update({"fixed": fixed, "fixed_score": fixed_score, "parts": len(parts),
                    "fixed_metrics": evaluate_text(reference, fixed)})
        rows.append(row)
        print(json.dumps({"line": index, "baseline_cer": row["baseline_metrics"]["cer"],
                          "fixed_cer": row["fixed_metrics"]["cer"], "parts": len(parts),
                          "seconds": round(perf_counter() - started, 2)}, ensure_ascii=True), flush=True)
    # Compare complete pipelines on the SAME detected quadrilaterals.
    engine = HybridOCREngine()
    engine._recognizer = recognizer
    fixed_document = engine.recognize(page, "generated_page.png")
    save_result(page, fixed_document, output / "hybrid_page")
    polygons = [line.polygon for line in fixed_document.lines]
    recognizer.config["dataset"]["image_max_width"] = 1024
    started = perf_counter()
    baseline_results = [recognizer.predict(engine._crop_line(page, polygon), return_prob=True)
                        for polygon in polygons]
    baseline_document = replace(
        fixed_document,
        lines=parse_lines({"rec_texts": [text for text, _ in baseline_results],
                           "rec_scores": [float(score) for _, score in baseline_results],
                           "rec_polys": polygons}, 0.5),
        elapsed_seconds=perf_counter() - started,
    )
    save_result(page, baseline_document, output / "baseline_page")
    reference = "\n".join(LINES)
    pipeline_metrics = {"baseline": evaluate_text(reference, baseline_document.text),
                        "fixed": evaluate_text(reference, fixed_document.text),
                        "detected_lines": len(polygons)}
    (output / "hybrid_page" / "metrics.json").write_text(
        json.dumps(pipeline_metrics["fixed"], ensure_ascii=False, indent=2), encoding="utf-8")
    report = {"kind": "generated_fixture_not_original_screenshot", "rows": rows,
              "configurations": {"baseline": "width 1024; one prediction per line",
                                 "width_cap_512": "width 512; one prediction per line",
                                 "fixed": "width 512; split at whitespace; minimum part score"},
              "pipeline_metrics": pipeline_metrics,
              "baseline_metrics": evaluate_text("\n".join(LINES), "\n".join(row["baseline"] for row in rows[:8])),
              "fixed_metrics": evaluate_text("\n".join(LINES), "\n".join(row["fixed"] for row in rows[:8]))}
    (output / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("baseline_metrics", "fixed_metrics", "pipeline_metrics")}), flush=True)
    assert rows[0]["fixed"] == LINES[0], "First line lost or changed characters"
    assert report["fixed_metrics"]["cer"] < 0.02, "Generated line regression"
    assert rows[-1]["fixed_metrics"]["cer"] < 0.02, "Extended line regression"
    assert len(polygons) == len(LINES), "Generated page lost detected lines"
    assert pipeline_metrics["fixed"]["cer"] < 0.02, "Generated page regression"
    print("Long-line real-model checks: PASS", flush=True)


if __name__ == "__main__":
    main()
