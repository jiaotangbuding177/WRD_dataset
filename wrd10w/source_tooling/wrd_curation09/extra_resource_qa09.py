"""Named root-read SVG/PPT resource checks in the fixed CPU image only."""
from pathlib import Path
import json,hashlib,shutil,subprocess
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation09/extra_resource_qa';SRC=ROOT/'output/20261031_wrd_curation09/writers/code'
IMAGE='sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
NAMES=['215439ffa54ad7c5a9aa8502.html','257f6602661ce6bd0135926b.html','addbee2f3bff0cbfae1bb183.html','b4c79fa37d65f5e447fbb9fc.py']
DRIVER=r'''from pathlib import Path
import json,subprocess,hashlib,re
from pptx import Presentation
from PIL import Image
from playwright.sync_api import sync_playwright
R=Path('/workspace');O=R/'qa_outputs';O.mkdir();checks=[]
def add(n,p,**k):checks.append(dict(name=n,PASS=bool(p),**k))
with sync_playwright()as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1080,'height':600})
 for owner in ['215439ffa54ad7c5a9aa8502','257f6602661ce6bd0135926b','addbee2f3bff0cbfae1bb183']:
  errors=[];page.on('pageerror',lambda e:errors.append(type(e).__name__));page.goto((R/'code'/f'{owner}.html').as_uri());page.wait_for_timeout(100)
  bounds=page.locator('svg').evaluate('e=>({w:e.width.baseVal.value,h:e.height.baseVal.value})');texts=page.locator('svg text').all_text_contents()
  page.screenshot(path=str(O/f'{owner}.png'));im=Image.open(O/f'{owner}.png')
  add('svg_'+owner,bounds=={'w':1080,'h':600}and im.size==(1080,600)and not errors,text_elements=len(texts),js_errors=errors,scope='offline render, source text/diagram layout only; no external-security-facts gold')
 b.close()
p=subprocess.run(['python',str(R/'code/b4c79fa37d65f5e447fbb9fc.py')],capture_output=True,text=True,timeout=90);(O/'ppt.stdout.txt').write_text(p.stdout);(O/'ppt.stderr.txt').write_text(p.stderr);add('ppt_export',p.returncode==0,exit_code=p.returncode)
path=R/'outputs/Agent安全真实案例三页PPT.pptx';prs=Presentation(path);add('pptx_three_pages',len(prs.slides)==3)
shapes=[]
for i,slide in enumerate(prs.slides):
 bad=[j for j,s in enumerate(slide.shapes)if s.left<0 or s.top<0 or s.left+s.width>prs.slide_width or s.top+s.height>prs.slide_height];shapes.append({'slide':i,'outside':bad})
add('ppt_shape_geometry',all(not x['outside']for x in shapes),slides=shapes,not_text_fit_proof=True)
p=subprocess.run(['libreoffice','-env:UserInstallation=file:///workspace/tmp/lo','--headless','--convert-to','pdf','--outdir',str(O),str(path)],capture_output=True,text=True,timeout=120);(O/'lo.stdout.txt').write_text(p.stdout);(O/'lo.stderr.txt').write_text(p.stderr);pdf=O/(path.stem+'.pdf');add('pdf_render',p.returncode==0 and pdf.exists())
if pdf.exists():
 p=subprocess.run(['pdftotext','-layout',str(pdf),str(O/'ppt.txt')],capture_output=True,text=True,timeout=30);text=(O/'ppt.txt').read_text()if(O/'ppt.txt').exists()else''
 normalize=lambda s:re.sub(r'\s+','',s)
 expected=['环境层才是最后防线','蜜罐标记','两个最严重的事故','当所有概率性防御都失效时的兜底']
 add('pdf_key_tail_text_visible',p.returncode==0 and all(normalize(x)in normalize(text)for x in expected),missing=[x for x in expected if normalize(x)not in normalize(text)],scope='selected tail strings; not all line fits')
 p=subprocess.run(['pdftoppm','-scale-to','1200','-png',str(pdf),str(O/'ppt_page')],capture_output=True,text=True,timeout=90);add('ppt_png_render',p.returncode==0)
res={'status':'PASS_SCOPED_RENDER_CHECKS'if all(c['PASS']for c in checks)else'FAIL_SCOPED_RENDER_CHECKS','checks':checks,'business_Agent_calls':0,'training_started':False,'not_whole_skill_or_business_factual_Q':True};(R/'RESULT.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':res['status'],'checks':len(checks),'failures':[c['name']for c in checks if not c['PASS']]}))
'''
def main():
 ws=WORK/'workspace';ws.mkdir(parents=True,exist_ok=False)
 for n in ['code','outputs','tmp']:(ws/n).mkdir()
 refs=[]
 for n in NAMES:
  p=SRC/n;shutil.copyfile(p,ws/'code'/n);refs.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 (ws/'driver.py').write_bytes(DRIVER.encode());cmd=['docker','run','--rm','--network','none','--cpus','4','--memory','6g','--shm-size','1g','-v',str(ws.resolve())+':/workspace','--entrypoint','python',IMAGE,'/workspace/driver.py']
 r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=450);(WORK/'stdout.txt').write_text(r.stdout,encoding='utf-8');(WORK/'stderr.txt').write_text(r.stderr,encoding='utf-8');(WORK/'EXECUTION.json').write_text(json.dumps({'image':IMAGE,'command':cmd,'exit_code':r.returncode,'source_pins':refs,'business_Agent_calls':0,'training_started':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'exit_code':r.returncode,'stdout':r.stdout[-1600:]}));assert r.returncode==0
if __name__=='__main__':main()
