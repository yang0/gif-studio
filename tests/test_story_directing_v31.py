"""Director planning rules are semantic contracts, not synthetic film quality scores."""
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from character_performance import validate as check_actor
from broll_strategy import review as check_broll
from editorial_engine import recommend

class DirectingTests(unittest.TestCase):
    def setUp(self):
        self.audio={"segments":[
            {"id":"s1","start_ms":0,"end_ms":1400,"text":"Interrupt"},
            {"id":"s2","start_ms":1400,"end_ms":3700,"text":"Cause"},
            {"id":"s3","start_ms":3700,"end_ms":6000,"text":"Result"}]}
        self.visual={"shots":[
            {"id":"v1","start_ms":0,"end_ms":1400,"audio_segment_ids":["s1"],"roll":"A"},
            {"id":"v2","start_ms":1400,"end_ms":3700,"audio_segment_ids":["s2"],"roll":"B"},
            {"id":"v3","start_ms":3700,"end_ms":6000,"audio_segment_ids":["s3"],"roll":"B"}]}
        self.director={"shots":[
            {"shot_id":"v1","visual_strategy":"scene_acting","viewpoint":"main_character",
             "visual_subject":"Person at desk","initial_state":"Focused work",
             "trigger_event":"Phone notification","final_state":"Looking away",
             "new_information":"Behavior shifts","movement_type":"physical_action",
             "cut_reason":"Focus to diversion","performance":{
                 "character_id":"worker-a","intention":"Finish task","action":"Put phone down",
                 "emotion_change":"Calm to surprise","prop_interaction":"Phone",
                 "appearance_lock":{"face":"round","clothing":"blue jacket"},
                 "action_beats":{"setup":"Look at book","action":"Turn to phone",
                                  "reaction":"Pause writing","resolution":"Put device away"}}},
            {"shot_id":"v2","visual_strategy":"causal_visualization",
             "visual_subject":"Attention graph","initial_state":"Connected nodes",
             "trigger_event":"Alert appears","final_state":"Broken path",
             "new_information":"Previous context must be recovered",
             "preferred_media":"original_animation","movement_type":"visible_cause_effect",
             "cut_reason":"Explain attention shift","cut_cue":{"event":"reveal","at_ms":1600}},
            {"shot_id":"v3","visual_strategy":"comparison_experiment",
             "visual_subject":"Two task timelines","initial_state":"Unbroken workflow",
             "trigger_event":"Interruption introduces extra step",
             "final_state":"Interrupted workflow has resumption stage",
             "new_information":"Concrete visual contrast","comparison_basis":"Same task and same start point",
             "preferred_media":"data_motion","data_provenance":"illustrative",
             "movement_type":"meaningful_data_change","cut_reason":"Proof of difference",
             "cut_cue":{"event":"contrast","at_ms":4200}}]}
    def test_actor_and_broll_contracts(self):
        self.assertFalse(check_actor(self.director,self.visual)["errors"])
        out=check_broll(self.director,self.visual)
        self.assertFalse(out["errors"])
        self.assertTrue(any(x["kind"]=="illustrative_data" for x in out["risks"]))
    def test_performance_identity_mismatch_is_review_risk(self):
        d=copy.deepcopy(self.director)
        second=copy.deepcopy(d["shots"][0])
        second["shot_id"]="v4"
        second["performance"]["appearance_lock"]["clothing"]="red jacket"
        d["shots"].append(second)
        self.visual["shots"].append({"id":"v4","roll":"A"})
        res=check_actor(d,self.visual)
        self.assertEqual("NEEDS_REAL_FOOTAGE_REVIEW",res["status"])
        self.assertTrue(res["manual_continuity_risks"])
    def test_semantic_cuts_preserve_grounded_time(self):
        res=recommend(self.director,self.audio,self.visual)
        self.assertEqual(3,len(res["decisions"]))
        self.assertEqual(1600,res["decisions"][1]["cut_at_ms"])
        self.assertEqual("director_explicit_event",res["decisions"][1]["cue_provenance"])
        self.assertTrue(any(x["kind"]=="missing_cut_cue" for x in res["risks"]))
    def test_cut_cue_outside_real_audio_fails(self):
        d=copy.deepcopy(self.director)
        d["shots"][1]["cut_cue"]["at_ms"]=29000
        with self.assertRaisesRegex(ValueError,"real visual shot"):
            recommend(d,self.audio,self.visual)
    def test_broll_ungrounded_data_fails(self):
        d=copy.deepcopy(self.director)
        d["shots"][2]["data_provenance"]=""
        self.assertTrue(check_broll(d,self.visual)["errors"])
    def test_fake_point_of_view_blocked(self):
        d=copy.deepcopy(self.director)
        d["shots"][0]["viewpoint"]="first_person"
        self.assertTrue(any("first-person" in x for x in
                            check_actor(d,self.visual)["errors"]))
if __name__=="__main__":
    unittest.main()
