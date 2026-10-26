"""Xuất văn bản UTF-8, JSON và ảnh đánh số vùng chữ."""
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw

from src.ocr.result import OCRDocument


def annotated_image(image: Image.Image, document: OCRDocument) -> Image.Image:
    result = image.copy().convert("RGB")
    draw = ImageDraw.Draw(result)
    for index, line in enumerate(document.lines, start=1):
        points = [(int(x), int(y)) for x, y in line.polygon]
        draw.line(points + [points[0]], fill="#007f73", width=2)
        x, y = points[0]
        draw.text((max(0, x), max(0, y - 14)), str(index), fill="#b52217")
    return result


def json_text(document: OCRDocument) -> str:
    return json.dumps(document.to_dict(), ensure_ascii=False, indent=2)


def png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def save_result(image: Image.Image, document: OCRDocument, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "text.txt").write_text(document.text, encoding="utf-8")
    (directory / "result.json").write_text(json_text(document), encoding="utf-8")
    annotated_image(image, document).save(directory / "annotated.png")
