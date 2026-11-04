from pathlib import Path
import subprocess,json
from PIL import Image
p=subprocess.run(['/opt/eval-venv/bin/python','/workspace/tmp/archery/render_overlays.py'],capture_output=True,text=True)
sizes={n:Image.open('/workspace/tmp/archery/'+n+'.png').size for n in ['title1','win','end']}
ok=p.returncode==0 and sizes=={'title1':(2000,300),'win':(2000,520),'end':(2000,300)}
out={'status':'PASS_LOCAL_VIEWPORT_REPAIR' if ok else 'FAIL','exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'sizes':sizes,'new_model_calls':0,'not_historical_Teacher_repair':True}
Path('/workspace/RESULT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if ok else 1)
