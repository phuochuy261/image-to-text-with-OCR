"""Nhận dạng dòng chữ bằng VietOCR, cấu hình và trọng số có sẵn của tác giả.

Nguồn cấu hình: github.com/pbcquoc/vietocr/config/base.yml và vgg-transformer.yml.
Giữ cấu hình tại chỗ để các lần chạy sau không cần tải lại cấu hình trên mạng.
"""
from pathlib import Path
from functools import lru_cache

from src.config import ROOT

WEIGHTS_URL = "https://vocr.vn/data/vietocr/vgg_transformer.pth"
VIETNAMESE_CHARACTERS = (
    "aAàÀảẢãÃáÁạẠăĂằẰẳẲẵẴắẮặẶâÂầẦẩẨẫẪấẤậẬbBcCdDđĐ"
    "eEèÈẻẺẽẼéÉẹẸêÊềỀểỂễỄếẾệỆfFgGhHiIìÌỉỈĩĨíÍịỊjJkKlLmMnN"
    "oOòÒỏỎõÕóÓọỌôÔồỒổỔỗỖốỐộỘơƠờỜởỞỡỠớỚợỢpPqQrRsS"
    "tTuUùÙủỦũŨúÚụỤưƯừỪửỬữỮứỨựỰvVwWxXyYỳỲỷỶỹỸýÝỵỴzZ"
    "0123456789!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ "
)


def get_weights() -> Path:
    path = ROOT / ".cache" / "vietocr" / "vgg_transformer.pth"
    if path.is_file():
        return path
    import requests
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".part")
    try:
        with requests.get(WEIGHTS_URL, stream=True, timeout=(15, 120)) as response:
            response.raise_for_status()
            with partial.open("wb") as destination:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        destination.write(chunk)
        partial.replace(path)
    except requests.RequestException as exc:
        raise RuntimeError("Chưa tải được trọng số VietOCR từ máy chủ tác giả. "
                           "Hãy kiểm tra mạng rồi thử lại.") from exc
    return path


@lru_cache(maxsize=2)
def create_recognizer(optimized: bool = True):
    import torch
    from vietocr.tool.predictor import Predictor
    torch.set_num_threads(4)
    config = {
        "vocab": VIETNAMESE_CHARACTERS,
        "device": "cpu",
        "weights": str(get_weights()),
        "backbone": "vgg19_bn",
        "cnn": {"pretrained": False, "ss": [[2, 2], [2, 2], [2, 1], [2, 1], [1, 1]],
                "ks": [[2, 2], [2, 2], [2, 1], [2, 1], [1, 1]], "hidden": 256},
        "seq_modeling": "transformer",
        "transformer": {"d_model": 256, "nhead": 8, "num_encoder_layers": 6,
                        "num_decoder_layers": 6, "dim_feedforward": 2048,
                        "max_seq_length": 1024, "pos_dropout": 0.1, "trans_dropout": 0.1},
        # Match the pretrained model's input range. Wider inputs can produce
        # an early EOS even with a high confidence score; split long lines first.
        "dataset": {"image_height": 32, "image_min_width": 32, "image_max_width": 512},
        "predictor": {"beamsearch": False},
    }
    predictor = Predictor(config)
    if optimized:
        from src.ocr.fast_decode import CachedVietOCR
        return CachedVietOCR(predictor)
    return predictor
