"""The library stores alternatives; production must consciously select one."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from candidate_pool import add, select, selection_status, read
from inspect_gif import digest

def gif(path,colors):
    frames=[Image.new("RGB",(270,480),c) for c in colors]
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=150,loop=0)

class CandidatePoolTests(unittest.TestCase):
    def test_multiple_candidates_and_switch_invalidate_qa(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            prompt=p/"prompt.txt"
            prompt.write_text("Exact shot prompt",encoding="utf-8")
            a,b=p/"a.gif",p/"b.gif"
            gif(a,["red","green","blue","yellow","purple","orange"])
            gif(b,["orange","purple","yellow","blue","green","red"])
            add(p,"shot-01","take-a",a,prompt,"gpt-image","run-a","Wide coverage")
            add(p,"shot-01","take-b",b,prompt,"gpt-image","run-b","Close-up coverage")
            self.assertEqual(2,len(read(p)["candidates"]))
            select(p,"shot-01","take-a","Clear first visual action")
            self.assertEqual(digest(a),digest(p/"gifs/shot-01.gif"))
            self.assertTrue(selection_status(p,"shot-01")[0])
            (p/"qa").mkdir()
            (p/"qa/shot-01.visual.json").write_text('{"approved":true}',encoding="utf-8")
            with self.assertRaises(FileExistsError):
                select(p,"shot-01","take-b","Better camera coverage")
            select(p,"shot-01","take-b","Better camera coverage",overwrite=True)
            self.assertEqual(digest(b),digest(p/"gifs/shot-01.gif"))
            self.assertFalse((p/"qa/shot-01.visual.json").exists())
            self.assertTrue(selection_status(p,"shot-01")[0])
            self.assertTrue((p/"library/candidates/shot-01/take-a.gif").is_file())

    def test_corrupt_selected_clip_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            prompt=p/"prompt.txt";prompt.write_text("prompt",encoding="utf-8")
            source=p/"a.gif";gif(source,["red","blue","green","yellow","purple","orange"])
            add(p,"shot-01","take-a",source,prompt,"gpt-image","run-a","Real output")
            select(p,"shot-01","take-a","Matches the narrated event")
            with (p/"gifs/shot-01.gif").open("ab") as f:
                f.write(b"changed")
            self.assertFalse(selection_status(p,"shot-01")[0])

    def test_id_cannot_traverse(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            prompt=p/"prompt.txt";prompt.write_text("prompt",encoding="utf-8")
            source=p/"a.gif";gif(source,["red","blue","green","yellow","purple","orange"])
            with self.assertRaises(ValueError):
                add(p,"../shot","take-a",source,prompt,"gpt-image","run-a","Real output")
