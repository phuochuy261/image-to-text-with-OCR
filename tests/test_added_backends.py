import unittest

from src.ocr.engine import OCREngine
from src.ocr.tesseract import parse_tsv


class AddedBackendTests(unittest.TestCase):
    def test_tesseract_merges_words_with_correct_line_and_confidence(self):
        header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        table = header + "5\t1\t1\t1\t1\t1\t10\t20\t30\t10\t90\tTiếng\n"
        table += "5\t1\t1\t1\t1\t2\t45\t20\t25\t11\t80\tViệt\n"
        table += "5\t1\t1\t1\t2\t1\t10\t50\t40\t10\t95\tDòng\n"
        lines = parse_tsv(table)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["texts"], ["Tiếng", "Việt"])
        self.assertEqual(lines[0]["rect"], [10, 20, 70, 31])
        self.assertEqual(lines[0]["scores"], [0.9, 0.8])

    def test_selected_models_are_not_silently_replaced(self):
        self.assertEqual(OCREngine(backend="ppocrv3").model_names()[1], "latin_PP-OCRv3_mobile_rec")
        self.assertEqual(OCREngine(backend="ppocrv5").model_names()[1], "latin_PP-OCRv5_mobile_rec")
        self.assertEqual(OCREngine(backend="hybrid_v5")._hybrid.detection_model, "PP-OCRv5_server_det")
        for weights in ("best", "fast", "standard"):
            engine = OCREngine(backend="tesseract_vietocr", tessdata_set=weights, psm=6)
            self.assertEqual(engine._hybrid.tessdata_set, weights)
            self.assertTrue(engine._hybrid.use_vietocr)


if __name__ == "__main__":
    unittest.main()
