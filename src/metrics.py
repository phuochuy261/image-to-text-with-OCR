"""Đánh giá lỗi OCR, không bỏ dấu tiếng Việt khi so sánh."""
import unicodedata


def normalize_for_evaluation(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def edit_distance(reference, prediction) -> int:
    previous = list(range(len(prediction) + 1))
    for i, expected in enumerate(reference, start=1):
        current = [i]
        for j, actual in enumerate(prediction, start=1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (expected != actual)))
        previous = current
    return previous[-1]


def evaluate_text(reference: str, prediction: str) -> dict:
    reference = normalize_for_evaluation(reference)
    prediction = normalize_for_evaluation(prediction)
    if not reference:
        raise ValueError("Bản chép chuẩn phải có nội dung để tính tỷ lệ lỗi.")
    tokens = reference.split()
    return {
        "reference_characters": len(reference),
        "character_edits": edit_distance(reference, prediction),
        "cer": edit_distance(reference, prediction) / len(reference),
        "whitespace_token_error_rate": edit_distance(tokens, prediction.split()) / len(tokens),
        "normalization": "NFC; gộp khoảng trắng; giữ dấu và chữ hoa/thường",
    }
