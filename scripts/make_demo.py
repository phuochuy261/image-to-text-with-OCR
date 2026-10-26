"""Tạo ảnh chữ in có bản chép chuẩn; không phải ảnh chụp thực tế."""
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    sample_dir = ROOT / "samples"
    sample_dir.mkdir(exist_ok=True)
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    if len(sys.argv) > 1:
        font_path = Path(sys.argv[1])
    font = ImageFont.truetype(str(font_path), 32)
    lines = [
        "NHẬN DẠNG VĂN BẢN TIẾNG VIỆT",
        "Đội tuyển bóng đá chuẩn bị tham dự giải đấu mới.",
        "Huấn luyện viên công bố danh sách các cầu thủ.",
        "Ứng dụng chuyển hình ảnh thành văn bản có dấu.",
        "Giữ nguyên nội dung để phân loại chủ đề ở bước sau.",
    ]
    image = Image.new("RGB", (1200, 440), "white")
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        draw.text((40, 35 + index * 75), line, font=font, fill="black")
    image.save(sample_dir / "demo_tieng_viet.png")
    (sample_dir / "demo_tieng_viet.txt").write_text("\n".join(lines), encoding="utf-8")
    Image.new("RGB", (800, 400), "white").save(sample_dir / "blank.png")
    print(f"Đã tạo ảnh và bản chép chuẩn tại {sample_dir}")


if __name__ == "__main__":
    main()
