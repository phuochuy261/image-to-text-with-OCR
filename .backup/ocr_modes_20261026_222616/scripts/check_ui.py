"""Kiểm tra giao diện và chạy OCR thật qua nút ảnh mẫu (cần mô hình)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

app = AppTest.from_file(str(ROOT / "ui.py"), default_timeout=120).run()
assert not app.exception, [e.message for e in app.exception]
app.button[0].click().run()
assert not app.exception
assert any("chọn một ảnh" in item.value for item in app.warning)
app.radio[0].set_value("Ảnh mẫu").run()
app.button[0].click().run(timeout=120)
assert not app.exception, [e.message for e in app.exception]
assert not app.error, [e.value for e in app.error]
assert "TIẾNG VIỆT" in app.text_area[0].value
assert len(app.get("download_button")) == 3
saved = app.session_state["ocr_output"]
directory = saved["directory"]
assert directory.is_dir(), "UI did not archive OCR"
assert (directory / "input.png").is_file()
assert (directory / "text.txt").read_text(encoding="utf-8") == app.text_area[0].value
run_id = saved["run_id"]
app.checkbox[0].uncheck().run()
assert not app.exception
assert app.session_state["ocr_output"]["run_id"] == run_id, "Toggle repeated OCR"
assert app.session_state["ocr_output"]["directory"] == directory, "Toggle created another archive"
app.checkbox[0].check().run()
assert app.session_state["ocr_output"]["run_id"] == run_id
# Đổi cấu hình phải bỏ kết quả cũ, không hiển thị nhầm ảnh/văn bản.
app.selectbox[1].select("tiny")
app.button[0].click().run(timeout=120)
assert not app.exception
assert not app.error
assert "VĂN BẢN" in app.text_area[0].value
assert app.session_state["ocr_output"]["directory"] != directory
app.radio[0].set_value("Dán ảnh").run()
assert "ocr_output" not in app.session_state, "Source switch retained stale OCR"
print("UI real OCR, auto archive, region toggle, downloads and source/model switches: PASS")
