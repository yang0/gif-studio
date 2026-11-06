"""v1.4/v1.5 regression tests using real synthetic GIF files.

These tests do not prove semantic quality or actual GPT GIF model availability.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
from approve_shot import approve
from director_plan import validate_director
from build_gif_prompts import compile_project,build_prompt
from review_gif_attempt import reject
from inspect_gif import inspect
from production_contract import asset_status, production_preflight, register
from qa_gate import shot_quality

FLAGS = {"semantic":True, "motion":True, "style":True, "composition":True}

def make_gif(path, colors):
    frames = [Image.new("RGB", (270, 480), c) for c in (list(colors)+list(colors)[:2])]
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=[180]*len(frames), loop=0)

def make_project(root, count=2):
    root = Path(root)
    for dirname in ("gifs","prompts","qa"):
        (root/dirname).mkdir(parents=True, exist_ok=True)
    shots, plans = [], []
    for i in range(count):
        sid = f"shot-{i+1:02d}"
        narration = f"第{i+1}段：这个视觉事件解释知识的原因。"
        shots.append({"id":sid,"duration_sec":1.2,"narration":narration,
                      "visual_goal":f"知识点 {i+1}", "visual_mode":"visual_metaphor",
                      "motion_plan":["状态建立","可见变化","结尾保持"]})
        plans.append({
            "id":sid,
            "spoken_point":f"说明第{i+1}段原因",
            "source_anchor":f"第{i+1}段",
            "visual_proof":f"观众明确看见第{i+1}个知识关系",
            "start_state":f"进入第{i+1}个问题",
            "change_event":f"主体通过清楚可见的动作展现第{i+1}个因果过程",
            "end_state":f"问题{i+1}得到展示",
            "composition":f"第{i+1}镜采取特定景别和主体构图",
            "entry_transition":"承接上一段的因果",
            "exit_transition":"自然交给下一段的动作",
            "asset_policy":"new_gpt_gif",
            "must_show":[f"具体第{i+1}个知识事件中的人物",f"第{i+1}个因果变化必须发生"],
            "must_not_show":["无关的大脑和灯泡图标"]
        })
        colors = ("#eac250","#d75346","#3f769e","#23644d") if i==0 else (
                  "#a753bb","#556fa2","#e67c3e","#2d9147")
        make_gif(root/"gifs"/(sid+".gif"), colors)
        (root/"prompts"/(sid+".txt")).write_text("actual generation instructions "+sid,
                                                  encoding="utf-8")
    board={"project_title":"test","width":180,"height":320,"fps":24,"shots":shots}
    director={"version":1,"creative_thesis":"因果关系通过连续视觉变化表达", "shots":plans}
    (root/"storyboard.json").write_text(json.dumps(board,ensure_ascii=False),encoding="utf-8")
    (root/"director-plan.json").write_text(json.dumps(director,ensure_ascii=False),encoding="utf-8")
    (root/"style-lock.json").write_text(json.dumps({"style_id":"hand-drawn"}),encoding="utf-8")
    return board, director

def register_and_review(root, board):
    for shot in board["shots"]:
        sid = shot["id"]
        register(root,board,sid,"gpt_gif","codex-gif-tool","artifact-"+sid,
                 root/"prompts"/(sid+".txt"), prompt_delivery="explicit_tool_argument")
        result = inspect(root/"gifs"/(sid+".gif"),1.2,.6,root/"qa"/(sid+"-sheet.jpg"))
        assert result["pass"], result
        (root/"qa"/(sid+".json")).write_text(json.dumps(result),encoding="utf-8")
        approve(root,sid,"reviewer",f"Viewed sheet for {sid}, checked objects and sequence",
                board,FLAGS)

class DirectorProductionTests(unittest.TestCase):
    def test_prompt_compiler_is_shot_specific(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,plan=make_project(root)
            paths=compile_project(root,root/"storyboard.json")
            self.assertEqual(2,len(paths))
            a=Path(paths["shot-01"]).read_text(encoding="utf-8")
            b=Path(paths["shot-02"]).read_text(encoding="utf-8")
            self.assertNotEqual(a,b)
            self.assertIn("第1个因果变化必须发生",a)
            self.assertIn("无关的大脑和灯泡",a)
            self.assertIn("hand-drawn",a)
            self.assertIn("第2个因果变化必须发生",b)

    def test_failed_gif_gets_one_focused_retry_then_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,_=make_project(root,1)
            compile_project(root,root/"storyboard.json")
            result=reject(root,"shot-01","generic_symbols",
                          "画面只有大脑和灯泡，并没有描述的具体因果行为",
                          "actual reviewer",root/"storyboard.json")
            self.assertEqual("retry_ready",result["status"])
            retry=(root/"prompts/shot-01.retry-2.txt").read_text(encoding="utf-8")
            self.assertIn("画面只有大脑和灯泡",retry)
            self.assertEqual("rejected",shot_quality(root,"shot-01",board)[0])
            with self.assertRaisesRegex(ValueError,"same failed GIF"):
                reject(root,"shot-01","wrong_subject",
                       "画面不包含叙事需要的主要角色与事件",
                       "actual reviewer",root/"storyboard.json")
            make_gif(root/"gifs/shot-01.gif",("#123456","#654321","#abcdef","#fedcba"))
            result=reject(root,"shot-01","wrong_action",
                          "新的 GIF 仍然没有把开始状态连接到结束状态",
                          "actual reviewer",root/"storyboard.json")
            self.assertEqual("blocked_replan",result["status"])
            self.assertEqual("blocked_replan",shot_quality(root,"shot-01",board)[0])

    def test_compile_rejects_ambiguous_director(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,plan=make_project(root,1)
            plan["shots"][0]["must_show"]=[]
            problems,_=validate_director(plan,board)
            self.assertTrue(any("must_show" in x for x in problems))

    def test_complete_production_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,plan=make_project(root)
            issues,warnings=validate_director(plan,board)
            self.assertEqual([],issues)
            register_and_review(root,board)
            self.assertEqual([], production_preflight(root,board))
            for s in board["shots"]:
                self.assertEqual("ready",shot_quality(root,s["id"],board)[0])

    def test_missing_plan_and_tool_metadata_block(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,_=make_project(root,1)
            (root/"director-plan.json").unlink()
            self.assertEqual("stale",asset_status(root,board,"shot-01")[0])
            self.assertTrue(production_preflight(root,board))
            self.assertNotEqual("ready",shot_quality(root,"shot-01",board)[0])

    def test_no_silent_programmatic_substitution(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,_=make_project(root,1)
            with self.assertRaisesRegex(ValueError,"does not match director"):
                register(root,board,"shot-01","programmatic","local","build-output")

    def test_duplicate_gif_rejected_even_with_reports(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,_=make_project(root)
            shutil.copyfile(root/"gifs/shot-01.gif",root/"gifs/shot-02.gif")
            register_and_review(root,board)
            issues=production_preflight(root,board)
            self.assertTrue(any("Duplicate GIF" in problem for problem in issues),issues)

    def test_gpt_only_rejects_programmatic(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,plan=make_project(root,1)
            plan["shots"][0]["asset_policy"]="programmatic"
            plan["shots"][0]["programmatic_reason"]="vector fallback not permitted"
            (root/"director-plan.json").write_text(json.dumps(plan,ensure_ascii=False),encoding="utf-8")
            register(root,board,"shot-01","programmatic","python","test-output")
            self.assertTrue(any("programmatic" in x for x in production_preflight(root,board)))
            self.assertEqual([],production_preflight(root,board,gpt_only=False))

    def test_landscape_gif_cannot_be_approved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,_=make_project(root,1)
            frames=[Image.new("RGB",(480,270),c) for c in ("red","green","blue","yellow")]
            gif=root/"gifs/shot-01.gif"
            frames[0].save(gif,format="GIF",save_all=True,
                           append_images=frames[1:],duration=[180]*4,loop=0)
            register(root,board,"shot-01","gpt_gif","codex-gif-tool",
                     "artifact-landscape",root/"prompts/shot-01.txt", prompt_delivery="explicit_tool_argument")
            report=inspect(gif,1.2,.6,root/"qa/shot-01-sheet.jpg")
            (root/"qa/shot-01.json").write_text(json.dumps(report),encoding="utf-8")
            self.assertEqual("rejected_technical",shot_quality(root,"shot-01",board)[0])
            with self.assertRaisesRegex(ValueError,"Strict GIF"):
                approve(root,"shot-01","reviewer","Actually reviewed frames",board,FLAGS)

    def test_context_only_delivery_is_not_formal_ready(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,_=make_project(root,1)
            register(root,board,"shot-01","gpt_gif","context-image-tool",
                     "actual-generation-reference",root/"prompts/shot-01.txt",
                     prompt_delivery="context_only_unverified")
            status,why=asset_status(root,board,"shot-01")
            self.assertEqual("stale",status)
            self.assertIn("context-only",why)
            self.assertTrue(production_preflight(root,board))

    def test_tampering_invalidates_provenance_and_review(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,_=make_project(root,1)
            register_and_review(root,board)
            (root/"prompts/shot-01.txt").write_text("changed",encoding="utf-8")
            self.assertEqual("stale",shot_quality(root,"shot-01",board)[0])
            (root/"prompts/shot-01.txt").write_text("actual generation instructions shot-01",
                                                   encoding="utf-8")
            board["shots"][0]["visual_goal"]="changed"
            self.assertEqual("stale",shot_quality(root,"shot-01",board)[0])

    def test_director_rejects_generic_layout_and_broken_anchor(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,plan=make_project(root,1)
            plan["shots"][0]["composition"]="fixed card layout"
            plan["shots"][0]["source_anchor"]="不在原稿里"
            issues,_=validate_director(plan,board)
            self.assertTrue(any("source_anchor" in x for x in issues))
            self.assertTrue(any("template" in x for x in issues))

    def test_intentional_reuse_is_explicitly_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,plan=make_project(root)
            shutil.copyfile(root/"gifs/shot-01.gif",root/"gifs/shot-02.gif")
            plan["shots"][1]["asset_policy"]="intentional_reuse"
            plan["shots"][1]["reuse_source_id"]="shot-01"
            plan["shots"][1]["reuse_justification"]="回扣开头镜头，首尾闭环"
            (root/"director-plan.json").write_text(json.dumps(plan,ensure_ascii=False),
                                                    encoding="utf-8")
            register(root,board,"shot-01","gpt_gif","codex-gif-tool","artifact-01",
                     root/"prompts/shot-01.txt", prompt_delivery="explicit_tool_argument")
            register(root,board,"shot-02","intentional_reuse","file-copy",
                     "reuse-previous-approved-gif")
            self.assertEqual([],production_preflight(root,board))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg unavailable")
    def test_composition_requires_formal_approval(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            board,_=make_project(root,1)
            cmd=[sys.executable,str(ROOT/"scripts/compose_video.py"),
                 "--project",str(root),"--storyboard",str(root/"storyboard.json"),
                 "--out",str(root/"final.mp4")]
            result=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            register_and_review(root,board)
            subprocess.run(cmd,check=True)
            report=json.loads((root/"build/delivery-report.json").read_text(encoding="utf-8"))
            self.assertTrue(report["qa_enforced"])
            self.assertEqual("qa_reviewed_silent_preview",report["delivery_class"])

if __name__=="__main__":
    unittest.main()
