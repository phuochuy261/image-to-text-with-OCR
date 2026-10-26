"""Compare cached decoding against upstream Predictor on identical line crops."""
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ocr.fast_decode import CachedVietOCR
from src.ocr.vietnamese import create_recognizer


def main():
    import torch
    predictor = create_recognizer(optimized=False)
    fast = CachedVietOCR(predictor)
    paths = sorted((ROOT / "outputs/long_lines").glob("line_[1-8]_part_*.png"))
    images = [Image.open(path).convert("RGB") for path in paths]
    report = {"images":len(images), "runs":[]}
    baseline = None
    for name, recognizer, threads in [("upstream",predictor,4), ("cached",fast,4),
                                      ("cached_batch",fast,4)]:
        torch.set_num_threads(threads)
        recognizer.predict(images[0])  # Warm up outside the timed region.
        seconds = []
        for _ in range(3):
            started = perf_counter()
            if name == "cached_batch":
                texts, scores = recognizer.predict_batch(images,return_prob=True)
                results = list(zip(texts,scores))
            else:
                results = [recognizer.predict(image,return_prob=True) for image in images]
            seconds.append(perf_counter()-started)
        if baseline is None:
            baseline = results
        row = {"method":name,"threads":threads,"seconds":seconds,"median_seconds":statistics.median(seconds),
               "texts_equal":all(a[0]==b[0] for a,b in zip(baseline,results)),
               "max_score_difference":max(abs(a[1]-b[1]) for a,b in zip(baseline,results))}
        report["runs"].append(row)
        print(json.dumps(row),flush=True)
        assert row["texts_equal"], "Decoding changed fixture text"
        assert row["max_score_difference"] < 0.0001, "Confidence calculation differs"
    output = ROOT/"outputs/performance"
    output.mkdir(parents=True,exist_ok=True)
    (output/"decode_benchmark.json").write_text(json.dumps(report,indent=2),encoding="utf-8")


if __name__ == "__main__":
    main()
