# Kiểm thử thực tế — 26/10/2026

Môi trường: Windows, Python 3.12, CPU. Phiên bản chính và phụ thuộc cụ thể ở requirements-lock.txt.

## Những gì đã chạy

- 12 kiểm thử dữ liệu, xuất kết quả, lưu từng lượt, clipboard và decoder: thành công ở bản hiện tại.
- CLI OCR: đã chạy mô hình thật trên ảnh chữ in tiếng Việt tạo bằng chương trình.
- Ảnh trắng: 0 vùng chữ, văn bản rỗng; không phát sinh nội dung giả.
- Streamlit AppTest: hiển thị ban đầu, báo khi chưa chọn ảnh, nhận dạng thật bằng ảnh mẫu, ba nút tải kết quả và đổi kích thước mô hình: thành công.
- PP-OCRv6 tiny/small/medium: đã tải và chạy thật cả phát hiện lẫn nhận dạng.

## Tăng tốc, lưu kết quả và cập nhật giao diện — 26/10/2026

- Đối chiếu decoder giữ attention với decoder gốc trên mô hình nhỏ theo cùng quy tắc causal: token và điểm khớp trong sai số số thực.
- Đối chiếu mô hình VietOCR thật trên 15 phần dòng, cùng trọng số và 4 luồng CPU: nội dung giống nhau; chênh điểm tối đa `1.49e-7`. Trung vị 3 lượt giảm từ 5.394 xuống 2.350 giây cho phần đọc. Số đo, phạm vi và giới hạn nằm trong `PERFORMANCE.md`.
- AppTest thực hiện OCR thật, kiểm tra tự lưu đủ ảnh/TXT/JSON, đổi Vùng chữ không chạy lại OCR hoặc tạo thư mục khác, đổi mô hình tạo lượt riêng và đổi nguồn bỏ kết quả cũ: thành công.
- Đã thử trên **Edge thật**, dán ảnh PNG từ clipboard bằng Ctrl+V, chạy OCR, thấy nội dung và đường dẫn lưu. Đã bật/tắt Vùng chữ, xác nhận ảnh hiển thị thay đổi nhưng đường dẫn lượt chạy giữ nguyên. Clipboard đã được khôi phục sau thử nghiệm.
- Thư mục kết quả mặc định: `G:\NLP\KetQua\OCR\YYYY-MM-DD\`; mỗi lượt có thời gian Việt Nam, bộ phát hiện, bộ nhận dạng, tên ảnh và mã riêng. Kiểm thử xác nhận không ghi đè lượt trước.
- CLI thật với `--backend ppocrv6 --model-size tiny` không có `--out`: đã tạo đủ thư mục mang tên `ppocrv6`, `det-v6-tiny`, `rec-ppocrv6-tiny`, kèm ảnh/TXT/JSON. Nội dung vẫn có lỗi dấu như đối chứng PP-OCRv6 trước đó.
- PNG xác nhận giao diện: `outputs/performance/ui_verified.png`. Chưa đo bộ ảnh độc lập gồm các ảnh người dùng báo mất 20–100 giây.

## Sửa lỗi mất phần cuối dòng dài — 26/10/2026

Đã kiểm tra mã và tái hiện bằng ảnh Times New Roman 24 px tạo từ 8 dòng nội dung "Tóc bạc thường được xem…" trong ảnh minh họa. Đây **không phải ảnh gốc đính kèm**. Ảnh, bản chép chuẩn, các ảnh cắt và báo cáo có tại `outputs/long_lines/`.

Nguyên nhân tái hiện được nằm ở bước nhận dạng: dự án đã đặt `dataset.image_max_width=1024`, trong khi cấu hình gốc VietOCR là 512. Dòng đầu dựng lại có 77 ký tự, đầu vào sau resize rộng 740; mô hình đọc 55 ký tự rồi phát EOS, điểm khoảng 0.933. Gọi `translate(..., max_seq_length=256)` vẫn ra cùng nội dung, EOS ở bước 56, nên lỗi này không phải chạm giới hạn giải mã 128. Chỉ đổi chiều rộng về 512 đã giúp dòng đầu đọc đủ. Điều này cho thấy tăng chiều rộng đầu vào đơn thuần không mở rộng khả năng đọc của trọng số đã huấn luyện.

Bản sửa đưa chiều rộng về 512 và chia dòng dài tại khoảng trắng; đọc từng phần, ghép đúng thứ tự, giữ một dòng cùng khung phát hiện ban đầu. Điểm dòng lấy theo phần có điểm thấp nhất. Khi không có khoảng trắng an toàn, giữ ảnh còn lại để resize; chưa bảo đảm đọc đủ dòng quá dài không có khoảng trắng.

| Kiểm tra bằng mô hình thật | Trước sửa | Sau sửa |
|---|---:|---:|
| Cùng 8 khung PP-OCR, 586 ký tự chuẩn hóa | 195 phép sửa, CER 33.28% | 0 phép sửa, CER 0.00% |
| 8 ảnh dòng cắt sát bằng chương trình, khác khung PP-OCR | 196 phép sửa, CER 33.45% | 3 phép sửa dấu, CER 0.51% |
| Một dòng kéo dài 242 ký tự | CER 50.41% | CER 0.83%, đọc tới cuối dòng |

Kết quả còn nhạy với cách cắt và dấu tiếng Việt. CER 0% ở ảnh dựng lại không chứng minh chất lượng trên ảnh gốc hay ảnh khác. Không dùng bản chép chuẩn để sửa nội dung OCR.

- 9 kiểm thử dữ liệu, xuất kết quả và xử lý dòng dài: thành công.
- `scripts/check_long_lines.py`: mô hình thật, đối chiếu trước/sau trên cùng khung, cả dòng dài hơn 128 ký tự: thành công.
- `scripts/check_ui.py`: hiển thị, OCR thật, tải kết quả và đổi mô hình: thành công sau sửa.
- So sánh: `outputs/long_lines/validation.json`; TXT trước/sau: `baseline_page/text.txt`, `hybrid_page/text.txt`.

Nguồn đối chiếu: [cấu hình gốc VietOCR](https://github.com/pbcquoc/vietocr/blob/master/config/base.yml), [Predictor](https://github.com/pbcquoc/vietocr/blob/master/vietocr/tool/predictor.py), [resize, giải mã và điểm nhận dạng](https://github.com/pbcquoc/vietocr/blob/master/vietocr/tool/translate.py). Đã đối chiếu cả mã VietOCR 0.3.13 cài tại máy.

Chạy lại từ thư mục dự án:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\check_long_lines.py
```

Sau khi sửa mã, dừng và mở lại Streamlit rồi nhận dạng lại ảnh; phiên đang chạy có thể giữ bộ nhận dạng và kết quả cũ trong bộ nhớ.

## Kiểm tra trên cùng một ảnh

Ảnh samples/demo_tieng_viet.png có 5 dòng, 223 ký tự sau khi chuẩn hóa NFC và gộp khoảng trắng. Bảng này là smoke test, không phải benchmark đại diện cho ảnh chụp thực tế. Ngưỡng điểm OCR 0.5.

| Cấu hình | Phép sửa ký tự | CER |
|---|---:|---:|
| V5 Latin (đối chứng ban đầu) | 34 | 15.25% |
| V5 + VietOCR Seq2Seq | 15 | 6.73% |
| V5 + VietOCR Transformer | 1 | 0.45% |
| V6 Small + VietOCR Transformer (mặc định) | 0 | 0.00% |
| PP-OCRv6_tiny đầy đủ | 41 | 18.39% |
| PP-OCRv6_small đầy đủ | 34 | 15.25% |
| PP-OCRv6_medium đầy đủ | 33 | 14.80% |

Kết quả v6 đầy đủ đọc mất một số ký tự tiếng Việt có dấu trong ảnh thử. Trong checkpoint PP-OCRv6_small_rec đã tải, kiểm tra PostProcess.character_dict không thấy một số ký tự dựng sẵn như ậ, ệ, ế, ộ, ự. Không suy rộng kết luận này sang mọi checkpoint hoặc mọi cách mã hóa ký tự.

Chọn tạm thời PP-OCRv6 Small cho phát hiện + VietOCR Transformer cho nhận dạng tiếng Việt, dựa trên thử nghiệm tại máy này. Giao diện và CLI vẫn hỗ trợ PP-OCRv6 đầy đủ để đối chiếu trên dữ liệu mới.

Thời gian warm của v6 đầy đủ (mỗi bản chỉ đo một lượt, 4 CPU threads, MKL-DNN tắt; không tính tải/nạp mô hình) nằm trong outputs/v6_comparison.json. Không coi đây là đo hiệu năng ổn định.

## Giới hạn và phần tiếp theo

- Chưa đánh giá ảnh chụp điện thoại độc lập, nhiều font, ánh sáng xấu, mờ, nghiêng hay tài liệu nhiều cột.
- Chưa đánh giá chữ viết tay; phạm vi hiện tại vẫn là chữ in một cột.
- AppTest kiểm tra OCR thật qua ảnh mẫu tích hợp; chưa thao tác tải tệp bằng trình duyệt thực tế.
- CER 0% trên ảnh mẫu không có nghĩa ứng dụng đạt 100% trên tài liệu bất kỳ.
- Giai đoạn 2: bộ phân loại VNTC chưa được huấn luyện/tích hợp. Dùng OCRDocument.text hoặc trường text trong JSON làm đầu vào sau này.

## Lệnh tái kiểm tra

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\check_ui.py
.\.venv\Scripts\python.exe scripts\compare_v6.py
.\.venv\Scripts\python.exe app.py ocr samples\demo_tieng_viet.png --out outputs\demo
.\.venv\Scripts\python.exe app.py evaluate --reference samples\demo_tieng_viet.txt --prediction outputs\demo\text.txt
```
