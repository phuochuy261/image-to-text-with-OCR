import unittest

import numpy as np
from PIL import Image, ImageDraw

from src.ocr.engine import HybridOCREngine
from src.ocr.long_lines import split_line


def long_crop():
    image = Image.new("RGB", (760, 32), "white")
    draw = ImageDraw.Draw(image)
    for start in (10, 110, 210, 310, 410, 510, 610, 710):
        draw.rectangle((start, 8, start + 35, 26), fill="black")
        draw.rectangle((start + 38, 8, start + 40, 26), fill="black")
    return image


class LongLineTests(unittest.TestCase):
    def test_partitions_keep_all_ink_and_do_not_cut_letters(self):
        image = long_crop()
        parts = split_line(image)
        self.assertGreater(len(parts), 1)
        count_ink = lambda value: int(np.count_nonzero(np.asarray(value.convert("L")) < 128))
        self.assertEqual(sum(count_ink(part) for part in parts), count_ink(image))
        for part in parts:
            self.assertLessEqual(part.width * 32 / part.height, 512)
            pixels = np.asarray(part.convert("L"))
            self.assertTrue(np.all(pixels[:, :3] == 255))
            self.assertTrue(np.all(pixels[:, -3:] == 255))

    def test_short_or_unbroken_line_keeps_original_crop(self):
        short = long_crop().crop((0, 0, 260, 32))
        self.assertIs(split_line(short)[0], short)
        unbroken = Image.new("RGB", (900, 32), "black")
        self.assertEqual(split_line(unbroken), [unbroken])

    def test_hybrid_joins_parts_under_original_polygon_and_weakest_score(self):
        image = long_crop()
        polygon = [[0, 0], [759, 0], [759, 31], [0, 31]]

        class Detector:
            def predict(self, pixels):
                return [{"dt_polys": [polygon]}]

        class Recognizer:
            config = {"dataset": {"image_height": 32, "image_max_width": 512}}

            def __init__(self):
                self.calls = 0

            def predict(self, crop, return_prob=False):
                outputs = [("Đầu dòng", 0.98), ("và cuối dòng.", 0.65)]
                result = outputs[self.calls]
                self.calls += 1
                return result

        engine = HybridOCREngine()
        engine._pipeline = Detector()
        engine._recognizer = Recognizer()
        document = engine.recognize(image)
        self.assertEqual(engine._recognizer.calls, 2)
        self.assertEqual(len(document.lines), 1)
        self.assertEqual(document.text, "Đầu dòng và cuối dòng.")
        self.assertEqual(document.lines[0].polygon, polygon)
        self.assertEqual(document.lines[0].score, 0.65)


if __name__ == "__main__":
    unittest.main()
