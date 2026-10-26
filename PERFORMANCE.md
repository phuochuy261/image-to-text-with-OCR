# Thời gian OCR và các thay đổi — 26/10/2026

Đã đo tại máy Windows này: Python 3.12, PyTorch `2.8.0+cpu`, 12 CPU logic; Paddle và Torch dùng 4 luồng. `torch.cuda.is_available()` trả về False. Đây là phép đo trên ảnh tạo bằng chương trình, không phải ảnh chụp gốc có thời gian 20–100 giây mà người dùng nêu.

## Vì sao tăng theo lượng văn bản

1. **VietOCR Transformer giải mã tự hồi quy:** mỗi lần sinh một ký tự; mã gốc chạy lại decoder trên toàn bộ tiền tố đã đọc ở mỗi bước. Càng nhiều chữ, càng nhiều lượt tính toán. Bản cũ đọc từng dòng, từng phần nối tiếp nhau.
2. **Lượt đầu gồm import và nạp hai mô hình:** trong phép đo này, riêng nạp bộ phát hiện và bộ nhận dạng khoảng 5,7 giây khi trọng số đã có sẵn trên ổ đĩa. Tải trọng số lần đầu qua mạng còn tốn thêm thời gian.
3. **Tiny không đổi bộ đọc khi dùng hybrid:** Tiny/Small/Medium chỉ đổi PP-OCR tìm vùng. Phần VietOCR đọc ký tự vẫn như nhau, nên đổi Tiny không giải quyết phần chậm chính.
4. **Số phần dòng cũng ảnh hưởng:** chia dòng dài cần thiết để tránh mất đuôi chữ, nhưng làm tăng số ảnh cần đọc. Ảnh thử có 8 vùng, được chia thành 15 phần.
5. **CPU và tải máy:** không có CUDA trong môi trường hiện tại. Thời gian từng lượt đã dao động đáng kể; không thể suy ra mọi ảnh sẽ có cùng mức tăng tốc. Điểm OCR được lọc sau nhận dạng, nên tăng ngưỡng điểm không tiết kiệm bước đọc chữ.

## Đã sửa

- `src/ocr/fast_decode.py` giữ khóa/giá trị attention của các ký tự trước, chỉ tính ký tự mới; giữ cả phần chiếu attention của ảnh đầu vào để dùng lại. Chạy trong `torch.inference_mode()`.
- Gom các phần ảnh có **cùng chiều rộng sau resize** vào một nhóm, tối đa 8 ảnh/lượt. Không thêm padding hay đổi kích thước để ép ảnh vào nhóm. Sau xử lý, khôi phục đúng thứ tự vùng và phần dòng.
- Giữ nguyên trọng số, bộ ký tự, quy tắc resize 32×tối đa 512 và cách chia dòng. Điểm dòng vẫn là điểm thấp nhất của các phần; dừng tại EOS cho từng ảnh trong nhóm.
- Dùng lại VietOCR đã nạp khi đổi Tiny/Small/Medium; bộ phát hiện vẫn được lưu riêng theo lựa chọn trên giao diện.
- Đọc mảng RGB của ảnh đầu vào một lần khi cắt nhiều vùng. Ảnh vùng chữ dùng cho hiển thị/tải về được giữ trong session, không vẽ lại khi bật/tắt.
- Ghi thời gian nạp, phát hiện, cắt vùng và đọc chữ trong `result.json`, `run.json` và mục Thời gian xử lý trên web. Tổng thời gian OCR không gồm thời gian ghi ảnh/TXT ra đĩa.

Không chỉnh thư viện trong `.venv`, không đổi sang Seq2Seq và không giảm nội dung đọc để lấy tốc độ.

## Phép đo đã chạy

So sánh trên **cùng 15 ảnh phần dòng**, mô hình đã nạp, 4 luồng CPU, khởi động nóng trước khi đo; trung vị của 3 lượt liên tiếp cho mỗi cách. Không tính phát hiện chữ hoặc ghi kết quả trong bảng này:

| Cách đọc | Trung vị |
|---|---:|
| Predictor gốc, từng ảnh | 5,394 giây |
| Decoder giữ attention, từng ảnh | 3,131 giây |
| Decoder giữ attention + nhóm cùng chiều rộng | 2,350 giây |

Phần đọc nhanh hơn khoảng **2,30 lần**, giảm khoảng **56%** ở bộ ảnh này. Nội dung 15 phần giống kết quả Predictor gốc; sai lệch điểm lớn nhất khoảng `1,49e-7`. Không dùng mức này để cam kết một ảnh 100 giây sẽ luôn giảm về một thời gian cố định.

Đo từng giai đoạn của ảnh 8 dòng, mỗi trạng thái chỉ một lượt:

| Bước ở lượt mô hình đã nạp | Trước sửa | Sau sửa |
|---|---:|---:|
| PP-OCR Small tìm vùng | 0,555 giây | 0,526 giây |
| Cắt ảnh vùng | 0,010 giây | 0,008 giây |
| Chia phần và đọc VietOCR | 7,488 giây | 3,841 giây |

Đây là hai phép đo khác bộ ảnh cắt/khối lượng thực hiện với bảng decoder, nên không trộn số liệu thành một benchmark. Các lượt khác có dao động lớn hơn; tải nền chưa được đo để kết luận nguồn dao động.

Tệp bằng chứng:

- `outputs/performance/decode_benchmark.json`: ba lần đo từng phương án và kiểm tra nội dung/điểm.
- `outputs/performance/stage_profile_before.json`, `stage_profile_after.json`: giai đoạn nạp và giai đoạn đã nạp.
- `outputs/long_lines/validation.json`: kiểm tra lại dòng dài và toàn bộ PP-OCR → VietOCR.
- `outputs/performance/ui_verified.png`: giao diện đã chạy với ảnh PNG dán thật từ clipboard.

## Nếu cần giảm thời gian thêm

Giữ ứng dụng chạy để dùng lại mô hình; xem bước nào tốn thời gian trong từng kết quả thật. Đóng các lượt OCR chạy đồng thời nếu chúng đang tranh CPU. Chọn Tiny có thể giảm bước phát hiện, nhưng không thay đổi bộ VietOCR trong hybrid.

GPU là hướng cần đánh giá riêng nếu máy có phần cứng phù hợp và cài bộ Paddle/PyTorch hỗ trợ GPU; chưa cài hoặc đo GPU trong lần này. Bộ nhận dạng khác có thể nhanh hơn nhưng cần đánh giá lại CER, đặc biệt dấu tiếng Việt; không tự đổi bộ đọc mặc định chỉ dựa vào thời gian.

Chạy lại từ `G:\NLP\PJ_PhanLoai`:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\benchmark_decode.py
.\.venv\Scripts\python.exe -X utf8 scripts\profile_ocr.py
.\.venv\Scripts\python.exe -X utf8 scripts\check_long_lines.py
.\.venv\Scripts\python.exe -X utf8 scripts\check_ui.py
```

Nguồn thuật toán: [VietOCR translate](https://github.com/pbcquoc/vietocr/blob/master/vietocr/tool/translate.py), [VietOCR Transformer](https://github.com/pbcquoc/vietocr/blob/master/vietocr/model/seqmodel/transformer.py). Phép đo và kết luận tốc độ dựa trên các lần chạy tại máy này.
