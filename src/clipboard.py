"""Local Streamlit image-paste component and validation of its image payload."""
import base64
import binascii
from pathlib import Path

import streamlit.components.v1 as components

from src.config import MAX_UPLOAD_BYTES

_paste = components.declare_component("paste_image", path=str(Path(__file__).parent / "clipboard_component"))


def paste_image(key="clipboard_image"):
    return _paste(max_bytes=MAX_UPLOAD_BYTES, key=key, default=None)


def decode_paste(value) -> tuple[bytes, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or not isinstance(value.get("data_url"), str):
        raise ValueError("Dữ liệu ảnh dán không hợp lệ. Hãy dán lại ảnh.")
    url = value["data_url"]
    if len(url) > MAX_UPLOAD_BYTES * 4 // 3 + 1024:
        raise ValueError("Vui lòng chọn ảnh không quá 20 MB.")
    header, separator, encoded = url.partition(",")
    extensions = {"data:image/png;base64": "png", "data:image/jpeg;base64": "jpg",
                  "data:image/webp;base64": "webp", "data:image/bmp;base64": "bmp"}
    if not separator or header not in extensions:
        raise ValueError("Clipboard phải chứa ảnh PNG, JPG, WEBP hoặc BMP.")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Dữ liệu ảnh dán bị lỗi. Hãy dán lại ảnh.") from exc
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Ảnh dán rỗng hoặc vượt quá 20 MB.")
    return data, "clipboard." + extensions[header]
