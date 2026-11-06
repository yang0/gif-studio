import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from verify_gif_asset import validate

def make_gif(path,size):
    frames=[Image.new("RGB",size,c) for c in ("red","blue","green","yellow","purple","orange")]
    frames[0].save(path,format="GIF",save_all=True,append_images=frames[1:],duration=120,loop=0)

class VerifyAssetTests(unittest.TestCase):
    def test_portrait_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"shot.gif"
            make_gif(p,(270,480))
            report=validate(p)
            self.assertTrue(report["pass"], report)

    def test_landscape_fails_even_if_gif_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"shot.gif"
            make_gif(p,(480,270))
            report=validate(p)
            self.assertFalse(report["pass"])
            self.assertTrue(any("Aspect mismatch" in x for x in report["issues"]))

    def test_static_or_tiny_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"shot.gif"
            frames=[Image.new("RGB",(90,160),"blue") for _ in range(6)]
            frames[0].save(p,format="GIF",save_all=True,append_images=frames[1:],duration=120)
            self.assertFalse(validate(p)["pass"])
