from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import streamlit as st

from src.clipboard import decode_paste, paste_image
from src.image_io import load_image
from src.config import ROOT, RESULTS_ROOT
from src.ocr.archive import save_run
from src.ocr.engine import OCREngine
from src.ocr.export import annotated_image, json_text, png_bytes

st.set_page_config(page_title="Đọc chữ tiếng Việt từ ảnh", page_icon="📄", layout="wide")
st.title("Đọc chữ tiếng Việt từ ảnh")
st.write("Dán hoặc tải ảnh, kiểm tra vùng chữ và xem nội dung đã nhận dạng.")
st.caption("Phạm vi: chữ in tiếng Việt, bố cục một cột. Kết quả được tự động lưu sau mỗi lần nhận dạng.")


@st.cache_resource
def get_engine(model_size, backend, revision="cached-decoder-v1"):
    return OCREngine(model_size=model_size, backend=backend)


source = st.radio("Nguồn ảnh", ["Dán ảnh", "Tải ảnh", "Ảnh mẫu"], horizontal=True, key="image_source")
data, source_name = None, None
if source == "Dán ảnh":
    pasted = paste_image()
    try:
        decoded = decode_paste(pasted)
        if decoded:
            data, source_name = decoded
    except ValueError as exc:
        st.error(str(exc))
elif source == "Tải ảnh":
    uploaded = st.file_uploader("Chọn ảnh tài liệu", type=["png", "jpg", "jpeg", "webp", "bmp"])
    if uploaded:
        data, source_name = uploaded.getvalue(), uploaded.name
else:
    sample = ROOT / "samples" / "demo_tieng_viet.png"
    if sample.is_file():
        data, source_name = sample.read_bytes(), sample.name
    else:
        st.error("Chưa có ảnh mẫu. Hãy chạy scripts/make_demo.py theo README.")

with st.form("recognize"):
    backend = st.selectbox("Bộ nhận dạng chữ", ["hybrid", "ppocrv6"],
                           format_func=lambda value: {"hybrid": "Tiếng Việt — VietOCR + vùng chữ PP-OCRv6",
                                                     "ppocrv6": "Đa ngôn ngữ — PP-OCRv6 đầy đủ"}[value])
    model_size = st.selectbox("Mô hình OCR", ["small", "tiny", "medium"],
                              format_func=lambda value: {"small": "PP-OCRv6 Small — cân bằng",
                                "tiny": "PP-OCRv6 Tiny — mô hình nhẹ",
                                "medium": "PP-OCRv6 Medium — mô hình lớn"}[value])
    options = st.columns(2)
    rotation = options[0].selectbox("Xoay ảnh theo chiều kim đồng hồ", [0, 90, 180, 270],
                                    format_func=lambda value: f"{value}°")
    min_score = options[1].slider("Ngưỡng điểm OCR", 0.0, 1.0, 0.5, 0.05,
                                  help="Tăng ngưỡng để bỏ vùng chữ có điểm thấp; có thể làm mất chữ.")
    submitted = st.form_submit_button("Nhận dạng văn bản", type="primary")

if data is None:
    st.session_state.pop("ocr_output", None)
    if submitted:
        st.warning("Hãy chọn một ảnh hoặc dán ảnh trước khi nhận dạng.")
    st.info("Dán ảnh bằng Ctrl+V trong ô phía trên, tải tệp hoặc chọn Ảnh mẫu.")
    st.stop()

signature = (sha256(data).hexdigest(), rotation, min_score, source_name, model_size, backend)
saved = st.session_state.get("ocr_output")
if saved and saved["signature"] != signature:
    st.session_state.pop("ocr_output", None)
try:
    image = load_image(data, rotation)
except ValueError as exc:
    st.session_state.pop("ocr_output", None)
    st.error(str(exc))
    st.stop()

if submitted:
    st.session_state.pop("ocr_output", None)
    try:
        with st.spinner("Đang đọc chữ… Lần đầu cần nạp mô hình."):
            document = get_engine(model_size, backend).recognize(image, source_name, min_score)
        rendered = png_bytes(annotated_image(image, document))
        saved = {"signature": signature, "document": document, "directory": None,
                 "annotated_png": rendered, "run_id": uuid4().hex}
        st.session_state["ocr_output"] = saved
        try:
            saved["directory"] = save_run(image, document, backend, model_size, data, rotation)
        except OSError as exc:
            st.warning(f"Đã nhận dạng xong nhưng chưa lưu được vào {RESULTS_ROOT}: {exc}")
    except Exception as exc:
        st.error("Chưa nhận dạng được ảnh. Xem chi tiết lỗi bên dưới để kiểm tra.")
        with st.expander("Chi tiết lỗi để kiểm tra"):
            st.code(str(exc))

left, right = st.columns(2)
saved = st.session_state.get("ocr_output")
with left:
    st.subheader("Ảnh và vùng chữ")
    show_regions = st.checkbox("Vùng chữ", value=True, disabled=saved is None,
                               help="Bật để xem khung chữ; tắt để xem ảnh gốc đã áp dụng góc xoay.")
    st.image(saved["annotated_png"] if saved and show_regions else image, width="stretch")
with right:
    st.subheader("Văn bản nhận dạng")
    if saved:
        document = saved["document"]
        if not document.lines:
            st.warning("Không tìm thấy chữ đạt ngưỡng. Hãy kiểm tra ảnh hoặc giảm ngưỡng điểm.")
        st.text_area("Nội dung OCR", value=document.text, height=360, disabled=True,
                     key="text_" + saved["run_id"])
        st.caption(f"{len(document.lines)} vùng chữ · {document.elapsed_seconds:.2f} giây "
                   "(bao gồm nạp mô hình nếu chưa có trong bộ nhớ)")
        stem = Path(source_name).stem
        buttons = st.columns(3)
        buttons[0].download_button("Tải TXT", document.text.encode("utf-8"),
                                    file_name=f"{stem}.txt", mime="text/plain", on_click="ignore")
        buttons[1].download_button("Tải JSON", json_text(document).encode("utf-8"),
                                    file_name=f"{stem}.json", mime="application/json", on_click="ignore")
        buttons[2].download_button("Tải ảnh vùng chữ", saved["annotated_png"],
                                    file_name=f"{stem}_regions.png", mime="image/png", on_click="ignore")
    else:
        st.write("Bấm Nhận dạng văn bản để xem kết quả.")

if saved:
    if saved["directory"]:
        st.caption("Đã lưu ảnh đầu vào, ảnh vùng chữ, TXT và JSON tại:")
        st.code(str(saved["directory"]), language=None)
    with st.expander("Thời gian xử lý"):
        labels = {"queue": "Chờ lượt xử lý", "detector_load": "Nạp mô hình tìm vùng chữ",
                  "detection": "Tìm vùng chữ", "recognizer_load": "Nạp mô hình đọc chữ",
                  "crop": "Cắt ảnh vùng chữ", "recognition": "Chia dòng và đọc chữ",
                  "pipeline_load": "Nạp mô hình PP-OCR", "pipeline_inference": "Tìm vùng và đọc chữ"}
        st.dataframe([{"Bước": labels.get(name, name), "Giây": round(seconds, 3)}
                      for name, seconds in saved["document"].timings.items()], hide_index=True)
        if saved["document"].recognition_parts:
            st.caption(f"VietOCR đã đọc {saved['document'].recognition_parts} phần dòng. "
                       "Đổi nút Vùng chữ chỉ thay ảnh hiển thị, không chạy lại OCR.")
    with st.expander("Đối chiếu từng vùng chữ"):
        st.dataframe([{"Vùng": i, "Nội dung": line.text, "Điểm OCR": round(line.score, 4)}
                      for i, line in enumerate(saved["document"].lines, start=1)], hide_index=True)
st.caption("Chữ viết tay, tài liệu nhiều cột và bảng biểu chưa thuộc phạm vi phiên bản này.")
