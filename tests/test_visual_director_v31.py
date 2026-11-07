"""Semantic storyboard QA: rejects empty visual motion and identical candidate stories."""
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from visual_director import propose,validate,compare
from visual_plan import sha256_json

class VisualDirectorTests(unittest.TestCase):
    def setUp(self):
        self.timeline={"version":1,"duration_ms":5000,"segments":[
           {"id":"s1","start_ms":0,"end_ms":2200,"text":"A question"},
           {"id":"s2","start_ms":2200,"end_ms":5000,"text":"An explanation"}]}
        self.visual={"version":1,"shots":[
           {"id":"v1","roll":"A","start_ms":0,"end_ms":2200},
           {"id":"v2","roll":"B","start_ms":2200,"end_ms":5000}]}
        self.briefs={
          "v1":{"narrative_function":"hook","visual_strategy":"scene_acting",
             "viewer_takeaway":"A person loses their train of thought",
             "scene_intent":"Show the emotional interruption",
             "visual_subject":"Worker at desk with ringing phone",
             "initial_state":"Working without interruption",
             "trigger_event":"Phone lights up and attracts gaze",
             "final_state":"Worker stops reading and picks up phone",
             "new_information":"Attention is redirected by a real event",
             "cut_reason":"Interrupt an established focused action",
             "movement_type":"physical_action","source_policy":"create_original",
             "preferred_media":"gpt_gif",
             "performance":{"character_id":"worker01","intention":"Finish report",
              "action":"Notice phone and pause","emotion_change":"Focus to confusion",
              "prop_interaction":"Grabs phone"},
             "alternatives":{"explanatory":{
                "visual_strategy":"visual_metaphor",
                "visual_subject":"Person drops pieces of a puzzle",
                "initial_state":"Pieces fitting together",
                "trigger_event":"Notification pulls hands aside",
                "final_state":"Puzzle pieces scatter on desk"}}},
          "v2":{"narrative_function":"explain_cause",
             "visual_strategy":"causal_visualization",
             "viewer_takeaway":"Recovery requires rebuilding previous context",
             "scene_intent":"Visualize lost state and context reconstruction",
             "visual_subject":"Two interrupted strands of a task path",
             "initial_state":"Task path continuing straight",
             "trigger_event":"New phone notification crosses path",
             "final_state":"Path broken and reconstructed from prior checkpoint",
             "new_information":"Resumption requires finding the last completed step",
             "cut_reason":"Shift from person to the cognitive mechanism",
             "movement_type":"visible_cause_effect","source_policy":"create_original",
             "preferred_media":"original_animation",
             "alternatives":{"explanatory":{
                "visual_strategy":"product_demonstration",
                "visual_subject":"Real UI shows switching windows and reopening last step",
                "initial_state":"Original window holds ongoing task",
                "trigger_event":"A notification redirects to another app",
                "final_state":"User reopens and searches for original task location",
                "movement_type":"real_demonstration",
                "preferred_media":"screen_recording",
                "source_policy":"record_actual"}}}}
    def test_valid_distinct_directing_variants(self):
        dramatic=propose(self.visual,self.timeline,self.briefs,"dramatic")
        explanatory=propose(self.visual,self.timeline,self.briefs,"explanatory")
        self.assertEqual([],validate(dramatic,self.timeline,self.visual))
        self.assertEqual([],validate(explanatory,self.timeline,self.visual))
        c=compare(dramatic,explanatory)
        self.assertEqual(2,c["distinct_shots"])
        self.assertTrue(c["meaningfully_different"])
        self.assertEqual("DIRECTOR_DRAFT_UNREVIEWED",dramatic["status"])
    def test_reject_empty_information_and_repeated_unchanged_frame(self):
        x=propose(self.visual,self.timeline,self.briefs,"dramatic")
        x["shots"][0]["new_information"]=""
        x["shots"][1]["final_state"]=x["shots"][1]["initial_state"]
        issues=validate(x,self.timeline,self.visual)
        self.assertTrue(any("new_information" in a for a in issues))
        self.assertTrue(any("state does not actually change" in a for a in issues))
    def test_stale_audio_or_visual_plan_blocks(self):
        x=propose(self.visual,self.timeline,self.briefs,"dramatic")
        new=copy.deepcopy(self.timeline)
        new["segments"][0]["text"]="A changed message"
        self.assertTrue(any("audio timeline changed" in a for a in validate(x,new,self.visual)))
        modified=copy.deepcopy(self.visual)
        modified["shots"][0]["end_ms"]=1000
        self.assertTrue(any("visual plan changed" in a for a in validate(x,self.timeline,modified)))
    def test_missing_real_character_performance_blocks(self):
        x=propose(self.visual,self.timeline,self.briefs,"dramatic")
        del x["shots"][0]["performance"]["prop_interaction"]
        self.assertTrue(any("performance" in a or "character/action" in a for a in
                            validate(x,self.timeline,self.visual)))
    def test_alternatives_are_not_invented_by_code(self):
        b=copy.deepcopy(self.briefs)
        del b["v2"]
        with self.assertRaisesRegex(ValueError,"supplied semantic brief"):
            propose(self.visual,self.timeline,b,"dramatic")

if __name__=="__main__":
    unittest.main()
