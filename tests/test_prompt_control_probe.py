import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from probe_gif_prompt_control import probe

def mk(path,kind):
    frames=[]
    for step in range(6):
        image=Image.new("RGB",(270,480),"#f2e9db")
        draw=ImageDraw.Draw(image)
        if kind=="square":
            draw.rectangle((10+step,10,225,225),fill="#19293a")
        else:
            draw.ellipse((30,30+step,245,245),fill="#9a4521")
        frames.append(image)
    frames[0].save(path,format="GIF",save_all=True,
                   append_images=frames[1:],duration=140,loop=0)

class PromptControlTests(unittest.TestCase):
    def test_same_visual_content_warns(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/"a.gif",Path(d)/"b.gif"
            mk(a,"square");mk(b,"square")
            self.assertTrue(probe(a,b)["prompt_control_suspect"])

    def test_different_visual_content_less_similar(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/"a.gif",Path(d)/"b.gif"
            mk(a,"square");mk(b,"round")
            self.assertLess(probe(a,b)["midframe_ahash_agreement"],0.9)
