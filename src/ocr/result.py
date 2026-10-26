"""Định dạng kết quả ổn định để giao diện, CLI và phần 2 cùng sử dụng."""
from dataclasses import asdict, dataclass, field
import unicodedata


@dataclass(frozen=True)
class TextLine:
    text: str
    score: float
    polygon: list[list[float]]


@dataclass
class OCRDocument:
    source_name: str
    width: int
    height: int
    lines: list[TextLine]
    min_score: float
    elapsed_seconds: float
    detection_model: str
    recognition_model: str
    timings: dict[str, float] = field(default_factory=dict)
    recognition_parts: int = 0

    @property
    def text(self) -> str:
        # Giữ dấu và xuống dòng. Không tự sửa nội dung OCR.
        return "\n".join(line.text for line in self.lines)

    def to_dict(self) -> dict:
        return {
            "schema_version": "1.0",
            "language": "vi",
            "source_name": self.source_name,
            "image": {"width": self.width, "height": self.height},
            "text": self.text,
            "lines": [asdict(line) for line in self.lines],
            "settings": {
                "min_score": self.min_score,
                "detection_model": self.detection_model,
                "recognition_model": self.recognition_model,
                "device": "cpu",
            },
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "timings_seconds": {name: round(value, 4) for name, value in self.timings.items()},
            "recognition_parts": self.recognition_parts,
        }


def parse_lines(result, min_score: float) -> list[TextLine]:
    if not 0 <= min_score <= 1:
        raise ValueError("Ngưỡng điểm OCR phải nằm trong [0, 1].")
    texts = result["rec_texts"]
    scores = result["rec_scores"]
    polygons = result["rec_polys"]
    if not (len(texts) == len(scores) == len(polygons)):
        raise ValueError("Kết quả OCR không nhất quán: số chữ, điểm và khung không khớp.")
    lines = []
    for text, score, polygon in zip(texts, scores, polygons):
        clean = unicodedata.normalize("NFC", str(text)).strip()
        if clean and float(score) >= min_score:
            points = [[float(x), float(y)] for x, y in polygon]
            if len(points) < 3:
                raise ValueError("Khung chữ OCR không hợp lệ.")
            lines.append(TextLine(clean, float(score), points))
    # Phạm vi phiên bản đầu: tài liệu một cột, đọc từ trên xuống dưới.
    return sorted(lines, key=lambda line: (
        min(point[1] for point in line.polygon),
        min(point[0] for point in line.polygon),
    ))
