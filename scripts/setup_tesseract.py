"""Download the official Vietnamese/English Tesseract model sets locally."""
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT


def main():
    for name, repository in (("fast", "tessdata_fast"), ("best", "tessdata_best"), ("standard", "tessdata")):
        folder = ROOT / ".cache" / "tessdata" / name
        folder.mkdir(parents=True, exist_ok=True)
        for language in ("vie", "eng"):
            target = folder / f"{language}.traineddata"
            if target.is_file():
                continue
            temporary = target.with_suffix(".part")
            urllib.request.urlretrieve(f"https://raw.githubusercontent.com/tesseract-ocr/{repository}/main/{language}.traineddata", temporary)
            temporary.replace(target)
            print(f"Downloaded {name}/{language}")


if __name__ == "__main__":
    main()
