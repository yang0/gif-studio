#!/usr/bin/env python3
"""Build a static, local, read-only visual browser for REAL GPT GIF candidates.

The gallery displays declared origins and automated *technical* observations.
It does not award visual approval, edit catalog.json, or render substitute art.
"""
import argparse
import html
import json
from pathlib import Path
from PIL import Image
from candidate_pool import read, selection_status
from inspect_gif import digest
from verify_gif_asset import validate as validate_gif

def esc(value):
    return html.escape(str(value), quote=True)

def candidate_details(root, rec):
    source = root / rec["file"]
    prompt = root / rec["prompt"]
    issues = []
    if not source.is_file() or digest(source) != rec["sha256"]:
        issues.append("Candidate GIF is missing or modified")
    if not prompt.is_file() or digest(prompt) != rec["prompt_sha256"]:
        issues.append("Original prompt is missing or modified")
    info = validate_gif(source) if source.is_file() else {"pass": False, "issues":["No GIF"]}
    return issues, info

def make_html(project, storyboard=None, edit_plan=None):
    root=Path(project).resolve()
    catalog=read(root)
    shots = {}
    if storyboard:
        board=json.loads(Path(storyboard).read_text(encoding="utf-8"))
        shots={s["id"]:s for s in board["shots"]}
    plan = None
    if edit_plan and Path(edit_plan).is_file():
        plan=json.loads(Path(edit_plan).read_text(encoding="utf-8"))

    # Output lives inside library; links are relative to that directory.
    out=root/"library"/"review.html"
    out.parent.mkdir(parents=True,exist_ok=True)
    groups={}
    for key,rec in sorted(catalog["candidates"].items()):
        groups.setdefault(rec["shot_id"],[]).append(rec)

    sections=[]
    all_shots=list(dict.fromkeys(list(shots)+list(groups)))
    for sid in all_shots:
        shot=shots.get(sid,{})
        choices=groups.get(sid,[])
        selected=catalog["selections"].get(sid,{})
        current=selected.get("candidate_id")
        selection_ok,selection_reason=selection_status(root,sid)
        cards=[]
        for rec in choices:
            bad,meta=candidate_details(root,rec)
            is_selected=rec["candidate_id"]==current
            # Each path was made by candidate_pool (safe IDs + fixed layout).
            gif_ref="candidates/"+rec["shot_id"]+"/"+rec["candidate_id"]+".gif"
            prompt_ref="prompts/"+rec["shot_id"]+"/"+rec["candidate_id"]+".txt"
            label="SELECTED" if is_selected else "ALTERNATIVE"
            technical="TECHNICAL CHECK PASS" if meta.get("pass") and not bad else "NEEDS ATTENTION"
            issues=bad+meta.get("issues",[])
            cards.append(f"""
            <article class="candidate {'chosen' if is_selected else ''}">
              <div class="image"><img src="{esc(gif_ref)}" alt="{esc(rec['candidate_id'])} original animated GIF" loading="lazy"></div>
              <div class="info"><div class="smallcaps">{esc(label)} · {esc(technical)}</div>
              <h3>{esc(rec['candidate_id'])}</h3>
              <p>{esc(rec['notes'])}</p>
              <div class="meta">{esc(meta.get('width','?'))}×{esc(meta.get('height','?'))}
                · {esc(meta.get('frames','?'))} frames · {esc(meta.get('duration_sec','?'))}s</div>
              <div class="meta">Tool: {esc(rec['tool'])} · Ref: {esc(rec['reference'])}</div>
              <div class="meta">SHA: <code>{esc(rec['sha256'][:16])}…</code></div>
              {f'<p class="warning">{esc("; ".join(issues))}</p>' if issues else ''}
              <a href="{esc(prompt_ref)}" target="_blank">Read exact prompt</a>
              </div>
            </article>""")
        desc=shot.get("visual_goal") or "No storyboard description"
        sections.append(f"""<section class="shot">
          <div class="shothead"><h2>{esc(sid)}</h2>
          <p>{esc(desc)}</p>
          <p class="meta">Narration: {esc(shot.get('narration',''))}</p>
          <p class="meta">Selection: {esc(current or 'none')}
            {esc(' · '+selected.get('reason','') if current else '')}
            {esc(' · '+selection_reason if current and not selection_ok else '')}</p></div>
          <div class="cards">{''.join(cards) or '<p>No candidates yet.</p>'}</div>
        </section>""")
    timeline=""
    if plan:
        parts=[]
        for x in plan.get("shots",[]):
            sid=x.get("shot_id","")
            dur=float(x.get("duration_frames",0))/max(1,int(plan.get("fps",24)))
            parts.append(f"""<div class="segment" style="flex:{max(dur,0.2):.3f}"
              title="{esc(sid)} — {dur:.2f}s">
              <strong>{esc(sid)}</strong><span>{dur:.2f}s</span>
              <small>{esc(x.get('cut_reason',''))}</small></div>""")
        timeline=f"""<section class="timeline"><h2>Editorial timeline</h2>
          <p class="meta">Draft/reference timeline only. Review status: {esc(plan.get('review_status','unknown'))}.
          The preview MP4 must be checked separately.</p>
          <div class="segments">{''.join(parts)}</div>
          </section>"""
    page=f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>gif-studio · Candidate Review</title>
    <style>
      :root{{color-scheme:dark;font-family:system-ui,-apple-system,sans-serif;background:#10151e;color:#e8edf5}}
      *{{box-sizing:border-box}} body{{margin:0 auto;padding:32px 22px;max-width:1400px}}
      h1{{font-size:32px;letter-spacing:-1px}}h2{{margin:0 0 12px}}h3{{margin:0 0 10px}}
      p{{line-height:1.55}}.intro{{max-width:800px;color:#b0bece}}
      .shot,.timeline{{margin:26px 0;padding:22px;border:1px solid #334154;border-radius:18px}}
      .shothead{{margin-bottom:18px}}.shothead p{{margin:5px 0}}
      .cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}}
      .candidate{{border:1px solid #354358;border-radius:14px;overflow:hidden;background:#182232}}
      .candidate.chosen{{border:2px solid #8ebbea}}
      .image{{aspect-ratio:9/16;background:#0b1016;display:grid;place-items:center}}
      img{{width:100%;height:100%;object-fit:contain}}
      .info{{padding:14px}}.smallcaps{{font-size:11px;font-weight:750;letter-spacing:.8px;color:#a8d1ff}}
      .meta{{font-size:12px;color:#a8b6ca;overflow-wrap:anywhere}}
      .warning{{color:#ffad9a}}a{{color:#b2d7ff}}
      .segments{{display:flex;gap:5px;min-height:112px;overflow:auto}}
      .segment{{min-width:95px;background:#345076;border:1px solid #6e92bc;border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:9px}}
      .segment span,.segment small{{font-size:11px}}.segment small{{color:#d7e5fa}}
      footer{{color:#a8b6ca;font-size:12px;margin:28px 0}}
    </style></head><body>
    <h1>gif-studio · 素材挑选工作台</h1>
    <p class="intro">这是从原始 GPT GIF 候选生成的静态本地画廊。动图真实播放；
    自动检测仅验证格式和画幅，不代表视觉语义合格。选片需用命令行明确执行，不能在此页面伪造审批。</p>
    <p class="meta">Catalog: {len(catalog['candidates'])} candidates ·
    {len(catalog['selections'])} selected · {len(all_shots)} shot groups</p>
    {timeline}{''.join(sections)}
    <footer>Generated by gif-studio · No vector substitute footage · Read-only gallery</footer>
    </body></html>"""
    out.write_text(page,encoding="utf-8")
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--storyboard")
    p.add_argument("--edit-plan")
    a=p.parse_args()
    print(make_html(a.project,a.storyboard,a.edit_plan))

if __name__=="__main__":
    main()
