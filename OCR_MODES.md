# Các cấu hình OCR trong dự án mới

Chạy `.\.venv\Scripts\python.exe app.py` hoặc `RUN_OCR.ps1`.
Giao diện mặc định chọn **PP-OCRv6 Medium + VietOCR**. CLI giữ mặc định Hybrid Small để tương thích lệnh cũ.

| Cấu hình | Backend CLI | Tham số hoặc mô hình |
|---|---|---|
| Tesseract OCR | `tesseract` | `--tessdata-set fast/best/standard --psm 3` |
| Tesseract + VietOCR Transformer | `tesseract_vietocr` | `--tessdata-set fast/best/standard --psm 3` |
| PaddleOCR v5 + VietOCR Transformer | `hybrid_v5` | `PP-OCRv5_server_det` |
| PP-OCRv6 + VietOCR Transformer | `hybrid` | `--model-size tiny/small/medium` |
| PP-OCRv6 đầy đủ | `ppocrv6` | `--model-size tiny/small/medium` |
| PP-OCRv5 Latin đầy đủ | `ppocrv5` | `PP-OCRv5_server_det` + `latin_PP-OCRv5_mobile_rec` |
| PP-OCRv3 Latin đầy đủ | `ppocrv3` | `PP-OCRv3_mobile_det` + `latin_PP-OCRv3_mobile_rec` |

Ví dụ:

```powershell
.\.venv\Scripts\python.exe app.py ocr samples\demo_tieng_viet.png --backend tesseract_vietocr --tessdata-set best
.\.venv\Scripts\python.exe app.py ocr samples\demo_tieng_viet.png --backend ppocrv5
```

Tesseract dùng chương trình tại `C:\Program Files\Tesseract-OCR\tesseract.exe`, hoặc đường dẫn từ biến môi trường `TESSERACT_CMD`.
Trọng số Việt/Anh của ba bộ nằm ở `.cache/tessdata/{fast,best,standard}`.
Nếu thiếu, chạy `.\.venv\Scripts\python.exe scripts/setup_tesseract.py`.
Không cần cài thêm pytesseract.

Các mode kết hợp dùng Transformer, giải mã tối ưu và xử lý dòng dài của dự án mới, không dùng Seq2Seq từ giao diện cũ.
Tiny/Small/Medium trong mode kết hợp chỉ đổi bộ tìm vùng chữ. "PaddleOCR v5 + VietOCR" dùng detector v5 server.
Tesseract độc lập xuất vùng theo dòng, điểm là trung bình điểm các từ. Mode kết hợp dùng điểm VietOCR.
Điểm của các bộ không được coi là tương đương; tăng ngưỡng có thể làm mất chữ.

Kết quả tự động lưu trong dự án tại `outputs/runs/YYYY-MM-DD`, kèm mô hình thực tế trong `result.json` và `run.json`.
Thời gian trên giao diện gồm nạp mô hình ở lượt đầu; các lượt sau dùng lại mô hình.
Các mô hình Latin v3/v5 được giữ để đối chiếu, có thể đọc sai dấu tiếng Việt; không tự sửa chính tả.
