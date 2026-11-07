#!/usr/bin/env python3
"""Local read-only A/B video inspection workspace with explicit issue export.

No fake automatic approvals. No HTTP server, network, or backend writes.
The browser can download a proposed defects.json only from a user click.
"""
import argparse
import html
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import quote
from audio_timeline import sha256
from visual_plan import sha256_json
from video_critic import check_report
from revision_planner import KINDS,SEVERITIES

def project_file(root,path):
    root=Path(root).resolve()
    file=Path(path).resolve()
    if root not in file.parents or not file.is_file():
        raise ValueError("Review assets must exist inside the selected project")
    return file

def generate(project,before,after,critic,plan,out):
    root=Path(project).resolve()
    primary=project_file(root,before)
    comparison=project_file(root,after)
    check_report(critic,primary,plan)
    if primary==comparison:
        raise ValueError("Compare two distinct actual videos")
    if sha256(primary)==sha256(comparison):
        raise ValueError("Videos have identical file bytes; no version contrast")
    dest=Path(out).resolve()
    if root not in dest.parents or dest.exists():
        raise ValueError("Workspace must use a new output path inside project")
    dest.parent.mkdir(parents=True,exist_ok=True)
    def url(path):
        return quote(os.path.relpath(path,dest.parent).replace(os.sep,"/"),safe="/.-_")
    sections=[]
    for c in plan.get("clips",[]):
        ms=round(c["start_frame"]*1000/plan["fps"])
        sid=html.escape(str(c.get("visual_plan_id",c["id"])))
        sections.append('<button class="marker" type="button" data-time="'+str(ms/1000)+'" data-shot="'+sid+'">'+
                        sid+' <small>'+str(ms/1000)+' s</small></button>')
    risk=[]
    for item in critic["risks"]:
        risk.append('<li><strong>'+html.escape(str(item["kind"]))+'</strong> · '+
                    html.escape(str(item.get("shot_id") or "whole film"))+'<p>'+
                    html.escape(str(item["evidence"]))+'</p></li>')
    base={"version":1,"critic_report_sha256":sha256_json(critic),
          "source_plan_sha256":sha256_json(plan),"issues":[]}
    serialized=json.dumps(base,ensure_ascii=False).replace("<","\\u003c")
    options="".join(f'<option value="{html.escape(k)}">{html.escape(k)}</option>' for k in sorted(KINDS))
    severity="".join(f'<option value="{html.escape(k)}">{html.escape(k)}</option>' for k in ("high","medium","critical","low"))
    shot_options='<option value="">Whole video</option>'+"".join(
        f'<option value="{html.escape(str(c.get("visual_plan_id",c["id"])))}">{html.escape(str(c.get("visual_plan_id",c["id"])))}</option>'
        for c in plan.get("clips",[]))
    page=r'''<!doctype html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>gif-studio · A/B quality review</title><style>
:root{font-family:system-ui,sans-serif;color-scheme:dark;background:#10141c;color:#edf4fa}
*{box-sizing:border-box}body{max-width:1400px;margin:auto;padding:28px}
h1{margin:0;font-size:28px}p,.sub{color:#bac6d4;line-height:1.5}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.viewer{background:#1a2331;border:1px solid #36485b;border-radius:14px;padding:16px}
video{width:100%;max-height:63vh;background:#070c12;border-radius:10px}
.controls{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0}
.marker{background:#223852;border:1px solid #648bb5;color:white;border-radius:8px;padding:10px;cursor:pointer}
.panel{background:#1a2331;border:1px solid #36485b;border-radius:14px;padding:18px;margin:20px 0}
.form{display:grid;grid-template-columns:1fr 1fr;gap:12px}
label{display:flex;flex-direction:column;gap:6px}input,select,textarea,button{padding:9px;background:#101a29;color:#fff;border:1px solid #54708d;border-radius:7px}
textarea{min-height:80px;grid-column:span 2}.span{grid-column:span 2}
button{cursor:pointer}button:hover{background:#2a4b70}li{margin:12px 0}
#issues{white-space:pre-wrap;word-break:break-word;font-size:12px;background:#111924;padding:12px;border-radius:10px}
@media(max-width:800px){.grid,.form{grid-template-columns:1fr}.span,textarea{grid-column:span 1}}
</style></head><body>
<h1>对照审片 · 两个真实 MP4</h1>
<p>必须完整观看与听完两条影片。以下是人工问题记录工具，<b>不会自动判定通过或签署发布审批</b>。</p>
<div class="grid"><section class="viewer"><h2>原版（基准）</h2><video id="before" controls preload="metadata" src="__BEFORE__"></video></section>
<section class="viewer"><h2>修改版（待评审）</h2><video id="after" controls preload="metadata" src="__AFTER__"></video></section></div>
<div class="controls"><label><input id="sync" type="checkbox" checked> 同步进度（仅手动同步）</label>
<button id="play" type="button">同步播放</button><button id="pause" type="button">同步暂停</button></div>
<section class="panel"><h2>镜头定位</h2><div class="controls">__MARKERS__</div></section>
<section class="panel"><h2>自动检测的风险（需要人工复核）</h2><ul>__RISKS__</ul></section>
<section class="panel"><h2>记录真实观察并下载局部返工清单</h2>
<p>填写的每条问题必须说明实际看到了什么、怎样修改、如何复验。下载的 defects.json 可交给 revision_planner.py。</p>
<div class="form">
<label>缺陷类型<select id="kind">__KINDS__</select></label>
<label>严重程度<select id="severity">__SEVERITY__</select></label>
<label>镜头<select id="shot">__SHOTS__</select></label>
<label>问题编号<input id="id" value="ISSUE-001"></label>
<label class="span">实际观察依据<textarea id="evidence" placeholder="观察到的真实画面/时间点，至少12个字符"></textarea></label>
<label class="span">具体修改动作<textarea id="fix" placeholder="替换什么镜头，如何构造可理解的事件"></textarea></label>
<label class="span">复验方法<textarea id="verify" placeholder="如何在新视频检查动作、语义、音画"></textarea></label>
</div><div class="controls"><button id="add" type="button">加入返工项</button><button id="download" type="button">下载 defects.json</button></div>
<pre id="issues"></pre></section>
<script>
const before=document.getElementById('before'),after=document.getElementById('after'),sync=document.getElementById('sync');
const plan=__PLAN__;
const put=(id)=>document.getElementById(id);
function seek(time){before.currentTime=time;if(sync.checked)after.currentTime=time}
document.querySelectorAll('.marker').forEach(el=>el.addEventListener('click',()=>{seek(+el.dataset.time);put('shot').value=el.dataset.shot}));
put('play').addEventListener('click',()=>{if(sync.checked)after.currentTime=before.currentTime;before.play();if(sync.checked)after.play()});
put('pause').addEventListener('click',()=>{before.pause();after.pause()});
function update(){put('issues').textContent=JSON.stringify(plan.issues,null,2)}
put('add').addEventListener('click',()=>{
 const item={id:put('id').value.trim(),issue_type:put('kind').value,severity:put('severity').value,shot_id:put('shot').value||null,
 evidence:put('evidence').value.trim(),proposed_fix:put('fix').value.trim(),verification:put('verify').value.trim()};
 if(!item.id||[item.evidence,item.proposed_fix,item.verification].some(x=>x.length<12)||plan.issues.some(x=>x.id===item.id)){alert("编号不能重复，三项观察/修改/复验均需不少于12字");return}
 plan.issues.push(item);update();
});
put('download').addEventListener('click',()=>{
 if(!plan.issues.length){alert('请先添加实际观察的问题');return}
 const blob=new Blob([JSON.stringify(plan,null,2)],{type:'application/json;charset=utf-8'});
 const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='defects.json';a.click();
 setTimeout(()=>URL.revokeObjectURL(url),3000);
});update();
</script></body></html>'''
    for k,v in {"__BEFORE__":html.escape(url(primary),quote=True),
               "__AFTER__":html.escape(url(comparison),quote=True),
               "__MARKERS__":"".join(sections),"__RISKS__":"".join(risk) or "<li>No automatic risks detected</li>",
               "__KINDS__":options,"__SEVERITY__":severity,"__SHOTS__":shot_options,
               "__PLAN__":serialized}.items():
        page=page.replace(k,v)
    dest.write_text(page,encoding="utf-8")
    return {"workspace":str(dest),"baseline_sha256":sha256(primary),
            "comparison_sha256":sha256(comparison),"status":"READ_ONLY_USER_REVIEW"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True);p.add_argument("--before",required=True)
    p.add_argument("--after",required=True);p.add_argument("--critic",required=True)
    p.add_argument("--plan",required=True);p.add_argument("--out",required=True)
    a=p.parse_args()
    read=lambda p:json.loads(Path(p).read_text(encoding="utf-8"))
    print(json.dumps(generate(a.project,a.before,a.after,read(a.critic),read(a.plan),a.out),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
