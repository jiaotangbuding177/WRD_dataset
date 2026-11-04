"""A newly observed screenshot-viewport repair, explicitly new authorship.

Preserves the real historical renderer and the first failed resource QA.
Only a local PNG renderer is executed; no Agent or model call occurs.
"""
from pathlib import Path
import hashlib,json,subprocess,time
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/20261030_wrd_gap08/semantic_root'
OUT=BASE/'overlay_viewport_repair'
IMAGE='sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pin(p):return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}

def main():
 OUT.mkdir(exist_ok=False);ws=OUT/'workspace';r=ws/'tmp/archery';r.mkdir(parents=True)
 original=BASE/'qa/workspace/tmp/archery/render_overlays.py'
 before=original.read_text(encoding='utf-8')
 old='            h = 520 if len(text) <= 5 else 300\n            await page.set_content'
 new='            h = 520 if len(text) <= 5 else 300\n            await page.set_viewport_size({"width": 2000, "height": h})\n            await page.set_content'
 assert before.count(old)==1
 after=before.replace(old,new,1)
 (OUT/'before.py').write_text(before,encoding='utf-8')
 (r/'render_overlays.py').write_text(after,encoding='utf-8')
 original_png=BASE/'qa/workspace/tmp/archery/win.png'
 (OUT/'before_win.png').write_bytes(original_png.read_bytes())
 args={'path':'/workspace/tmp/archery/render_overlays.py','edits':[{'oldText':old,'newText':new}]}
 save(OUT/'NEW_NATIVE_EDIT_ARGUMENTS.json',args)
 driver=ws/'qa.py';driver.write_text('''from pathlib import Path
import subprocess,json
from PIL import Image
p=subprocess.run(['/opt/eval-venv/bin/python','/workspace/tmp/archery/render_overlays.py'],capture_output=True,text=True)
sizes={n:Image.open('/workspace/tmp/archery/'+n+'.png').size for n in ['title1','win','end']}
ok=p.returncode==0 and sizes=={'title1':(2000,300),'win':(2000,520),'end':(2000,300)}
out={'status':'PASS_LOCAL_VIEWPORT_REPAIR' if ok else 'FAIL','exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'sizes':sizes,'new_model_calls':0,'not_historical_Teacher_repair':True}
Path('/workspace/RESULT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if ok else 1)
''',encoding='utf-8')
 argv=['docker','run','--rm','--network','none','--memory','6g','--cpus','4','--shm-size','1g','--mount',f'type=bind,source={ws.resolve()},target=/workspace','--workdir','/workspace','--entrypoint','/opt/eval-venv/bin/python',IMAGE,'/workspace/qa.py']
 start=time.monotonic();p=subprocess.run(argv,capture_output=True,text=True,timeout=90)
 save(OUT/'EXECUTION_RECEIPT.json',{'argv':argv,'exit_code':p.returncode,'wall_seconds':time.monotonic()-start,'stdout':p.stdout,'stderr':p.stderr,'script_sha256':sha(__file__),'new_model_calls':0,'training_started':False})
 assert p.returncode==0
 result=json.loads((ws/'RESULT.json').read_bytes());assert result['status']=='PASS_LOCAL_VIEWPORT_REPAIR'
 save(OUT/'REPAIR_EVIDENCE.json',{'status':'NEW_AUTHORED_ACTUAL_LOCAL_REPAIR_PENDING_PEER','source_ids':['conv_2f75e4f55a18'],
  'original_recorded_renderer_after_edit83':pin(original),'before_actual_bad_size_PNG':pin(OUT/'before_win.png'),
  'before_actual_size':[2000,500],'intended_clip_size':[2000,520],
  'failure_receipt':pin(BASE/'qa/workspace/qa_outputs/RESULT.json'),'before':pin(OUT/'before.py'),
  'actual_new_edit':pin(OUT/'NEW_NATIVE_EDIT_ARGUMENTS.json'),'actual_new_resource':pin(r/'render_overlays.py'),
  'retest':pin(ws/'RESULT.json'),'original_reasoning_recovered':False,'new_rationale_author':'Codex silver data curation',
  'native_OpenClaw_dispatch_performed':False,'pure_resource_check_not_Agent_trajectory':True,
  'qualified_skill_or_whole_video_quality_proven':False,'training_started':False})
 print(json.dumps({'status':result['status'],'before_win_height':500,'after_win_height':520,'new_Agent_calls':0}))

if __name__=='__main__':main()
