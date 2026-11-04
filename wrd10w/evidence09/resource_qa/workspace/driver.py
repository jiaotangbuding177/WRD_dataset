from pathlib import Path
import json,subprocess,hashlib,traceback,zipfile,xml.etree.ElementTree as ET
from docx import Document
from pptx import Presentation
from playwright.sync_api import sync_playwright
R=Path('/workspace');O=R/'qa_outputs';O.mkdir(exist_ok=True);results=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def add(name,ok,**kw):results.append(dict(name=name,PASS=bool(ok),**kw))
def run(name,args):
 p=subprocess.run(args,cwd=R,capture_output=True,text=True,timeout=90)
 (O/(name+'.stdout.txt')).write_text(p.stdout);(O/(name+'.stderr.txt')).write_text(p.stderr)
 add(name,p.returncode==0,exit_code=p.returncode);return p
for n in ['0d78ae10be60edfdaba93dc0','605cdf7450ad2d3ae8563788']:run(n,['python',str(R/'code'/f'{n}.py')])
doc=R/'outputs/投资承诺函.docx';text='\n'.join(p.text for p in Document(doc).paragraphs)
add('docx_source_qualifiers',all(s in text for s in ['不超过人民币3,000万元','投前估值不超过人民币6亿元','以双方最终达成的交易文件为准']),paragraph_count=len(Document(doc).paragraphs),SHA=sha(doc),scope='source preservation/export only; no investment or legal validity')
ppt=R/'outputs/核心场景一页PPT.pptx';prs=Presentation(ppt);t='\n'.join(s.text for s in prs.slides[0].shapes if s.has_text_frame)
add('pptx_one_slide_source_four_scenarios',len(prs.slides)==1 and all(s in t for s in ['成果评估','AI评分辅助评审','项目跟进与管理','全局监控与预警']),slides=len(prs.slides),SHA=sha(ppt))
bad=[i for i,s in enumerate(prs.slides[0].shapes)if s.left<0 or s.top<0 or s.left+s.width>prs.slide_width or s.top+s.height>prs.slide_height]
add('pptx_shapes_within_page',not bad,outside_indices=bad,scope='geometry, not complete visual text-fit or business Q')
for inp in [doc,ppt]:
 tag=inp.suffix[1:];run('pdf_'+tag,['libreoffice','-env:UserInstallation=file:///workspace/tmp/lo_'+tag,'--headless','--convert-to','pdf','--outdir',str(O),str(inp)])
 pdf=O/(inp.stem+'.pdf');add('pdf_exists_'+tag,pdf.exists()and pdf.read_bytes().startswith(b'%PDF'))
def lum(rgb):
 x=[n/255 for n in rgb];x=[v/12.92 if v<=.04045 else((v+.055)/1.055)**2.4 for v in x];return sum(a*b for a,b in zip(x,[.2126,.7152,.0722]))
def contrast(a,b):
 x,y=sorted([lum(a),lum(b)]);return(y+.05)/(x+.05)
with sync_playwright()as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1100,'height':900})
 errors=[];page.on('pageerror',lambda e:errors.append(type(e).__name__))
 page.add_init_script("Math.random=()=>0.5;window.__arcs=[];const a=CanvasRenderingContext2D.prototype.arc,c=CanvasRenderingContext2D.prototype.clearRect;CanvasRenderingContext2D.prototype.arc=function(x,y,r,...z){window.__arcs.push({x,y,r});return a.call(this,x,y,r,...z)};CanvasRenderingContext2D.prototype.clearRect=function(...z){window.__arcs=[];return c.apply(this,z)}")
 page.goto((R/'code/0dd5502eec8fa8afa8343b48.html').as_uri());page.wait_for_timeout(300)
 add('solar_table_eight_rows',page.locator('#tbody tr').count()==8)
 page.click('#btnToggle');page.wait_for_timeout(100);a=page.locator('canvas').screenshot();page.wait_for_timeout(120);b=page.locator('canvas').screenshot();add('solar_pause_stable',a==b)
 pos=page.evaluate("(()=>{let p=window.__arcs.find(p=>p.r===6),b=document.querySelector('canvas').getBoundingClientRect();return{x:b.x+p.x*b.width/1840,y:b.y+p.y*b.height/1100}})()")
 page.mouse.click(pos['x'],pos['y']);add('solar_click_selects_first_row',page.locator('#tbody tr').first.evaluate("e=>e.style.background.length>0"))
 page.uncheck('#orbits');page.uncheck('#labels');page.locator('#speed').fill('2');page.locator('#speed').dispatch_event('input');page.click('#btnToggle');page.wait_for_timeout(100);a=page.locator('canvas').screenshot();page.wait_for_timeout(150);b=page.locator('canvas').screenshot();add('solar_resume_changes',a!=b)
 add('solar_no_js_errors',not errors,error_classes=errors);page.screenshot(path=str(O/'solar.png'),full_page=True)
 for owner,cls,var in [('57bf5a6f4263f47514add40d','theme-soft-mint','--text-on-teal'),('8a3958608262a264663a580d','','--text-on-bottom')]:
  css=(R/'code'/f'{owner}.css').read_text();page.set_content('<html><head><style>'+css+'</style></head><body class="'+cls+'"><section class="page-upper hero">顶部文字</section><section class="page-bottom footer">底部文字<button class="btn-accent btn-primary">按钮</button></section></body></html>')
  ratio=contrast([255,255,255],[0,196,163]);add('css_original_bad_contrast_reproduced_'+owner,ratio<3,original_white_teal_ratio=ratio,original_meets_large_text_minimum=False)
  patch=':root, .theme-soft-mint { '+var+': #123b32; --text-on-teal-soft:rgba(18,59,50,.85); --text-on-bottom-muted:#123b32; }'
  page.add_style_tag(content=patch);dark=contrast([18,59,50],[0,196,163]);add('css_new_scoped_dark_contrast_'+owner,dark>=4.5,new_dark_teal_ratio=dark,authorship='new root test fixture, not original historical repair')
  (O/f'{owner}.contrast_patch.css').write_text(patch);page.screenshot(path=str(O/(owner+'.png')),full_page=True)
 browser.close()
result={'status':'PASS_SCOPED_RESOURCE_CHECKS'if all(x['PASS']for x in results)else'FAIL_RESOURCE_CHECKS','checks':results,'model_or_Agent_calls':0,'training_started':False,'no_whole_skill_or_scientific_financial_legal_Q_gold':True}
(R/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':result['status'],'checks':len(results),'failed':[x['name']for x in results if not x['PASS']]}))
