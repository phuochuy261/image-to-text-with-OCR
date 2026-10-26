"""Đọc ảnh và thống nhất hệ tọa độ cho OCR lẫn ảnh hiển thị."""
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from src.config import MAX_PIXELS, MAX_UPLOAD_BYTES


def load_image(data: bytes, rotation: int = 0) -> Image.Image:
    if not data:
        raise ValueError("Tệp ảnh rỗng.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Vui lòng chọn ảnh không quá 20 MB.")
    if rotation not in (0, 90, 180, 270):
        raise ValueError("Góc xoay phải là 0, 90, 180 hoặc 270 độ.")
    try:
        with Image.open(BytesIO(data)) as original:
            if original.width * original.height > MAX_PIXELS:
                raise ValueError("Ảnh quá lớn. Vui lòng giảm xuống tối đa 20 triệu điểm ảnh.")
            image = ImageOps.exif_transpose(original).convert("RGB")
            if rotation:
                image = image.rotate(-rotation, expand=True)
            return image
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Không đọc được ảnh. Hãy thử ảnh PNG hoặc JPG hợp lệ.") from exc


def load_image_file(path: Path, rotation: int = 0) -> Image.Image:
    if path.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValueError("Vui lòng chọn ảnh không quá 20 MB.")
    return load_image(path.read_bytes(), rotation)
