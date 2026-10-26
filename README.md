# Nhận dạng văn bản tiếng Việt từ ảnh

Đây là bài tập nhỏ học phần NLP, triển khai theo hai giai đoạn:

1. **OCR (đang triển khai):** ảnh chữ in tiếng Việt → nội dung văn bản và các vùng chữ.
2. **Phân loại chủ đề (chưa triển khai):** nhận văn bản từ giai đoạn 1 → dự đoán chủ đề bằng mô hình huấn luyện trên VNTC.

Giai đoạn 1 dùng mô hình có sẵn; không huấn luyện lại OCR. Mặc định **PP-OCRv6 Small tìm vùng chữ + VietOCR Transformer đọc tiếng Việt**. Có thể chuyển sang PP-OCRv6 đầy đủ (tiny/small/medium) để đối chiếu. Ứng dụng chạy CPU, một ảnh mỗi lần, chữ in, bố cục một cột. Chưa cam kết chất lượng trên chữ viết tay, nhiều cột, bảng biểu hoặc ảnh chụp mờ. Không tự sửa chính tả hay suy diễn nội dung.

## Bắt đầu trên Windows

Cần Python 3.10–3.12 (đã kiểm tra với Python 3.12). Mở PowerShell tại `E:\Study\NLP\image-to-text-with-OCR-main`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\make_demo.py
.\.venv\Scripts\python.exe app.py
```

Mở địa chỉ localhost do Streamlit in ra. Chọn nguồn **Dán ảnh**, bấm vào ô dán rồi **Ctrl+V** (ảnh chụp màn hình hoặc thao tác Sao chép hình ảnh). Có thể chọn **Tải ảnh** hoặc **Ảnh mẫu**. Bấm **Nhận dạng văn bản** để xử lý. Trong kết quả, bật **Vùng chữ** để xem khung, tắt để xem ảnh gốc đã áp dụng góc xoay. Nút này không chạy lại OCR. Vẫn có thể tải TXT, JSON và ảnh đánh dấu về trình duyệt.

## Lưu kết quả từng lần chạy

Mỗi lần bấm Nhận dạng thành công, ứng dụng tự tạo thư mục riêng tại `outputs/runs/YYYY-MM-DD/`. Thời gian trong tên thư mục theo giờ Việt Nam (+07:00):

```text
YYYYMMDD_HHMMSS_mmm__backend__det-v6-size__rec-recognizer__ten-anh__id
```

Ví dụ tên thư mục cho ảnh dán, bộ kết hợp Small:

```text
20261026_140722_092__hybrid__det-v6-small__rec-vietocr-transformer__clipboard__9ea35b82
```

Với PP-OCRv6 Tiny đầy đủ, phần nhận dạng sẽ là `rec-ppocrv6-tiny`. Tên ảnh được chuyển thành chữ không dấu; mã cuối phân biệt các lượt trùng thời điểm hoặc tên ảnh. Không ghi đè lượt trước. Mỗi thư mục gồm:

- `input.png`: ảnh thực sự đưa vào OCR sau khi áp dụng EXIF/góc xoay.
- `annotated.png`: ảnh có khung và số vùng chữ.
- `text.txt`: nội dung nhận dạng UTF-8.
- `result.json`: vùng chữ, điểm, mô hình và thời gian từng bước.
- `run.json`: thời điểm, bộ nhận dạng, cấu hình và SHA-256 dữ liệu ảnh đầu vào để đối chiếu.

Đường dẫn lưu xuất hiện dưới kết quả trên web. Đổi Vùng chữ hoặc bấm tải tệp không tạo thư mục mới. Khi sao chép tệp ảnh bằng Explorer mà clipboard chưa chứa dữ liệu hình ảnh, dùng Tải ảnh thay thế.

Lần OCR đầu tiên cần mạng để tải mô hình về `.cache`: mô hình phát hiện chính thức của PaddleOCR và trọng số nhận dạng từ tác giả VietOCR. Mỗi kích thước v6 được chọn sẽ tải mô hình tương ứng một lần. Không cần tài khoản hoặc API key. Các lần tiếp theo sử dụng lại mô hình đã tải. Nếu tải thất bại, kiểm tra mạng rồi thử lại; không tắt xác thực HTTPS.

Có thể thay các bước thiết lập bằng `setup.ps1 -PythonExe <đường dẫn python.exe>`. `setup.ps1` tạo môi trường và cài thư viện; `RUN_OCR.ps1` chỉ gọi entry point Python, không thiết lập môi trường. Chạy trực tiếp bằng Python như trên luôn được.

Nếu PowerShell chặn chạy script, dùng `powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1`. Các tệp `.ps1` có tiếng Việt cần giữ mã hóa **UTF-8 with BOM** để Windows PowerShell 5.1 đọc đúng; UTF-8 không có BOM có thể gây `ParserError`. Thiết lập `PYTHONUTF8` chỉ tác động đến Python, không thay đổi cách PowerShell đọc script. Hai script đã bật UTF-8 cho Python khi chạy.

## Chạy OCR bằng lệnh

```powershell
.\.venv\Scripts\python.exe -X utf8 app.py ocr samples\demo_tieng_viet.png
.\.venv\Scripts\python.exe app.py ocr samples\demo_tieng_viet.png --out outputs\demo
.\.venv\Scripts\python.exe app.py ocr "D:\anh cua toi.jpg" --out outputs\anh_thu --min-score 0.5 --rotate 0
.\.venv\Scripts\python.exe app.py ocr samples\demo_tieng_viet.png --backend ppocrv6 --model-size small --out outputs\v6_small
```

CLI không có `--out` cũng tạo thư mục theo từng lượt tại `KetQua/OCR` như giao diện. Khi chỉ định `--out`, giữ cách xuất trực tiếp vào thư mục đã chọn, gồm:

- `text.txt`: nội dung nhận dạng, UTF-8, giữ dấu và xuống dòng.
- `result.json`: `schema_version`, `text`, các dòng kèm `score` và `polygon`, cấu hình mô hình.
- `annotated.png`: ảnh đã áp dụng EXIF/xoay thủ công, đánh số vùng chữ khớp thứ tự JSON.

Nếu dùng lại cùng `--out`, ba tệp này được cập nhật. `--backend hybrid` là mặc định; `--model-size` chọn bộ tìm vùng chữ v6. Với `--backend ppocrv6`, kích thước áp dụng cho cả phát hiện và nhận dạng. Điểm OCR là điểm mô hình, không phải xác suất đúng đã được hiệu chuẩn; điểm của hai bộ nhận dạng cũng không được coi là tương đương. Tăng `--min-score` có thể làm mất chữ; không đồng nghĩa tự động tăng độ chính xác.

### Dòng chữ dài

VietOCR dùng chiều cao 32, chiều rộng tối đa 512 theo cấu hình gốc. Dòng quá dài được chia tại khoảng trắng giữa các từ, đọc từng phần rồi ghép về một dòng và giữ khung PP-OCR ban đầu. Điểm của dòng là điểm thấp nhất trong các phần. Nếu không tìm được khoảng trắng an toàn, giữ ảnh còn lại để VietOCR đổi kích thước như bình thường; trường hợp này vẫn có thể giảm chất lượng khi dòng quá dài.

Không tự tăng `image_max_width` lên 1024 để đọc thêm chữ: trên ảnh thử, cách này khiến mô hình phát ký hiệu kết thúc sớm dù điểm cao. `transformer.max_seq_length=1024` là giới hạn mã hóa vị trí; giới hạn giải mã mặc định vẫn là 128. Hai tham số này khác nhau. Chia dòng giúp giảm cả chiều rộng lẫn độ dài chuỗi mỗi lượt đọc.

Sau khi cập nhật mã, dừng ứng dụng bằng Ctrl+C rồi mở lại để bỏ mô hình đã lưu trong bộ nhớ. Chạy kiểm tra dòng dài bằng `.\.venv\Scripts\python.exe -X utf8 scripts\check_long_lines.py`. Ảnh thử và bản so sánh được lưu tại `outputs/long_lines`; đây là ảnh tạo bằng chương trình, không phải ảnh gốc người dùng.

### Thời gian xử lý

VietOCR Transformer đọc từng ký tự trên CPU. Bản hiện tại giữ lại tính toán attention giữa các ký tự, xử lý chung các ảnh dòng có cùng chiều rộng và dùng lại bộ nhận dạng khi đổi kích thước bộ phát hiện. Xem **Thời gian xử lý** dưới kết quả để phân biệt nạp mô hình, phát hiện, cắt vùng và đọc chữ. Trong chế độ hybrid, Tiny/Small/Medium chỉ đổi bộ tìm vùng; VietOCR vẫn là cùng bộ đọc chữ. Chi tiết phép đo và hướng tối ưu tiếp theo ở `PERFORMANCE.md`.

## Kiểm tra và đánh giá

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe app.py evaluate --reference samples\demo_tieng_viet.txt --prediction outputs\demo\text.txt
.\.venv\Scripts\python.exe scripts\check_ui.py
.\.venv\Scripts\python.exe scripts\compare_v6.py
```

CER là số phép chèn/xóa/thay ký tự chia cho số ký tự trong bản chuẩn. Chuẩn hóa Unicode NFC và gộp khoảng trắng, vẫn giữ dấu và phân biệt hoa/thường. `whitespace_token_error_rate` tính theo token cách nhau bởi khoảng trắng, **không phải WER đã tách từ tiếng Việt**. CER có thể lớn hơn 1 khi chèn quá nhiều ký tự.

Ảnh trong `samples` là dữ liệu chữ in tạo bằng chương trình, dùng kiểm tra luồng hoạt động. Kết quả tốt trên ảnh này không chứng minh chất lượng trên ảnh chụp điện thoại. Để đánh giá thực tế, chuẩn bị thêm ảnh độc lập có bản chép đúng, tách tập phát triển và kiểm tra. VNTC dùng để huấn luyện phần phân loại, không phải dữ liệu ảnh OCR.

## Sơ đồ mã nguồn

| Đường dẫn | Trách nhiệm |
|---|---|
| `app.py` | Entry point: UI, OCR CLI hoặc đánh giá |
| `ui.py` | Giao diện tải ảnh và tải kết quả |
| `src/clipboard.py`, `src/clipboard_component/` | Nhận ảnh từ thao tác Ctrl+V trong trình duyệt |
| `src/config.py` | Đường dẫn cache và tên mô hình |
| `src/image_io.py` | Đọc ảnh, EXIF, xoay và giới hạn kích thước |
| `src/ocr/engine.py` | Hai backend: PP-OCRv6 đầy đủ hoặc kết hợp VietOCR |
| `src/ocr/vietnamese.py` | Cấu hình và nạp bộ nhận dạng tiếng Việt có sẵn |
| `src/ocr/long_lines.py` | Chia dòng dài tại khoảng trắng, nhận dạng và ghép lại |
| `src/ocr/fast_decode.py` | Giải mã VietOCR với bộ nhớ attention và gom ảnh dòng cùng kích thước |
| `src/ocr/archive.py` | Tạo thư mục riêng theo thời gian, mô hình và ảnh đầu vào |
| `src/ocr/result.py` | Kiểu dữ liệu và chuyển kết quả OCR sang định dạng chung |
| `src/ocr/export.py` | Xuất TXT/JSON/ảnh đánh dấu |
| `src/metrics.py` | Đánh giá lỗi OCR |
| `scripts/make_demo.py` | Tạo ảnh mẫu có bản chép chuẩn |
| `scripts/check_long_lines.py` | Tái hiện lỗi mất đuôi dòng và đối chiếu trước/sau bằng mô hình thật |
| `tests/` | Kiểm tra xử lý dữ liệu và xuất kết quả |

## Điểm tích hợp giai đoạn 2

```python
document = engine.recognize(image)
text_for_classifier = document.text
# classifier.predict([text_for_classifier]) sẽ được bổ sung ở giai đoạn 2.
```

Giữ nguyên văn bản OCR để có thể so sánh phân loại trên văn bản chuẩn và văn bản OCR. Bộ phân loại sẽ ở module riêng; không ghép huấn luyện VNTC vào bộ nhận dạng ảnh.

## Mô hình và phiên bản

- PaddleOCR 3.7.0, PaddlePaddle CPU 3.3.0. Phiên bản thư viện 3.7 khác với thế hệ mô hình PP-OCRv6.
- Phát hiện chữ mặc định: `PP-OCRv6_small_det`.
- Nhận dạng chữ mặc định: VietOCR `vgg_transformer`, có bộ ký tự tiếng Việt đầy đủ.
- Backend đối chiếu: `PP-OCRv6_{tiny,small,medium}_det` + `PP-OCRv6_{tiny,small,medium}_rec`.
- Giữ NumPy 1.26 và các phiên bản phụ thuộc tương thích với VietOCR trong requirements; không nâng riêng lẻ NumPy/OpenCV/Pillow khi chưa kiểm tra.
- Tắt MKL-DNN trong cấu hình mặc định để ưu tiên tương thích Windows CPU.
- Các phiên bản phụ thuộc thực tế sau khi kiểm thử được lưu trong `requirements-lock.txt` nếu đã tạo.

Nguồn: [PaddleOCR pipeline](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html), [PP-OCRv6](https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv6/PP-OCRv6.html), [VietOCR](https://github.com/pbcquoc/vietocr), [VNTC](https://github.com/duyvuleo/VNTC).

Xem `VALIDATION.md` để biết những gì đã chạy thực tế và giới hạn còn lại.


Updated local OCR modes: see [OCR_MODES.md](OCR_MODES.md).
