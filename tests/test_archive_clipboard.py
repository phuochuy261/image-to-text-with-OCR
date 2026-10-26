import base64
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from src.clipboard import decode_paste
from src.image_io import load_image
from src.ocr.archive import save_run
from src.ocr.result import OCRDocument


class ArchiveClipboardTests(unittest.TestCase):
    def test_archive_never_overwrites_and_identifies_models_and_input(self):
        image = Image.new("RGB", (20, 10), "white")
        document = OCRDocument("Ảnh thử.jpg", 20, 10, [], 0.5, 1.2, "PP-OCRv6_small_det", "vietocr_vgg_transformer")
        with TemporaryDirectory() as temp:
            first = save_run(image, document, "hybrid", "small", b"source", root=Path(temp))
            second = save_run(image, document, "ppocrv6", "tiny", b"source2", root=Path(temp))
            third = save_run(image, document, "hybrid", "small", b"source", root=Path(temp))
            self.assertNotEqual(first, third)
            self.assertIn("__hybrid__det-v6-small__rec-vietocr-transformer__anh-thu__", first.name)
            self.assertIn("__ppocrv6__det-v6-tiny__rec-ppocrv6-tiny__", second.name)
            self.assertEqual({p.name for p in first.iterdir()},
                             {"input.png", "annotated.png", "text.txt", "result.json", "run.json"})
            metadata = json.loads((first / "run.json").read_text(encoding="utf-8"))
            self.assertTrue(metadata["saved_at"].endswith("+07:00"))
            self.assertEqual(metadata["source_name"], "Ảnh thử.jpg")
            self.assertEqual(load_image((first / "input.png").read_bytes()).size, image.size)

    def test_paste_decodes_exact_image_and_rejects_invalid_payload(self):
        buffer = BytesIO()
        Image.new("RGB", (40, 30), "red").save(buffer, format="PNG")
        original = buffer.getvalue()
        value = {"data_url": "data:image/png;base64," + base64.b64encode(original).decode("ascii")}
        data, name = decode_paste(value)
        self.assertEqual(data, original)
        self.assertEqual(name, "clipboard.png")
        self.assertEqual(load_image(data).getpixel((0, 0)), (255, 0, 0))
        for invalid in ({}, {"data_url":"data:text/html;base64,PGgxPg=="},
                        {"data_url":"data:image/png;base64,@@@@"}):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                decode_paste(invalid)


if __name__ == "__main__":
    unittest.main()
