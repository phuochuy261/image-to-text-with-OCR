from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from src.image_io import load_image
from src.metrics import evaluate_text
from src.ocr.export import save_result
from src.ocr.result import OCRDocument, parse_lines


def box(y):
    return [[10, y], [180, y], [180, y + 20], [10, y + 20]]


class OCRContractTests(unittest.TestCase):
    def test_alignment_threshold_order_and_unicode(self):
        lines = parse_lines({
            "rec_texts": ["Dòng cuối", "  Tiếng Việt  ", "nhiễu"],
            "rec_scores": [0.91, 0.95, 0.2],
            "rec_polys": [box(70), box(10), box(40)],
        }, 0.5)
        self.assertEqual([line.text for line in lines], ["Tiếng Việt", "Dòng cuối"])
        self.assertEqual(lines[0].polygon, box(10))

    def test_rejects_mismatched_backend_arrays(self):
        with self.assertRaises(ValueError):
            parse_lines({"rec_texts": ["chữ"], "rec_scores": [], "rec_polys": []}, 0.5)

    def test_empty_image_result_is_valid(self):
        self.assertEqual(parse_lines({"rec_texts": [], "rec_scores": [], "rec_polys": []}, 0.5), [])

    def test_rotation_changes_dimensions_and_corrupt_input_is_rejected(self):
        buffer = BytesIO()
        Image.new("RGB", (200, 100)).save(buffer, format="PNG")
        self.assertEqual(load_image(buffer.getvalue(), 90).size, (100, 200))
        with self.assertRaises(ValueError):
            load_image(b"not an image")

    def test_exports_keep_diacritics_and_coordinates(self):
        lines = parse_lines({"rec_texts": ["Sức khỏe"], "rec_scores": [0.95],
                             "rec_polys": [box(10)]}, 0.5)
        doc = OCRDocument("ảnh.png", 200, 100, lines, 0.5, 1.0, "det", "rec")
        with TemporaryDirectory() as directory:
            target = Path(directory)
            save_result(Image.new("RGB", (200, 100)), doc, target)
            data = json.loads((target / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(data["text"], "Sức khỏe")
            self.assertEqual(data["lines"][0]["polygon"], box(10))
            self.assertEqual((target / "text.txt").read_text(encoding="utf-8"), data["text"])
            with Image.open(target / "annotated.png") as rendered:
                self.assertEqual(rendered.size, (200, 100))

    def test_metrics_count_real_errors_and_normalize_unicode(self):
        self.assertEqual(evaluate_text("Tiếng Việt", "Tiếng Việt")["cer"], 0)
        result = evaluate_text("abc", "adc!")
        self.assertEqual(result["character_edits"], 2)
        self.assertAlmostEqual(result["cer"], 2/3)
        with self.assertRaises(ValueError):
            evaluate_text("", "abc")


if __name__ == "__main__":
    unittest.main()
