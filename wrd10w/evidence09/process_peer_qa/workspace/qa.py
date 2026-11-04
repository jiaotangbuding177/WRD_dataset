"""Read-reviewed local resources only. Separate generation from business credit."""
from pathlib import Path
import asyncio, hashlib, json, math, runpy, subprocess, sys, time, traceback

ROOT=Path('/workspace');OUT=ROOT/'qa_outputs'
checks=[];failures=[]

def check(name,condition,details=None):
 checks.append({'check':name,'pass':bool(condition),'details':details})
 if not condition:failures.append(name)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def run(name,path,timeout):
 start=time.monotonic()
 try:
  result=subprocess.run([sys.executable,path],capture_output=True,text=True,timeout=timeout)
  (OUT/(name+'.stdout.txt')).write_text(result.stdout,encoding='utf-8')
  (OUT/(name+'.stderr.txt')).write_text(result.stderr,encoding='utf-8')
  check(name+'_program_exit',result.returncode==0,{'returncode':result.returncode,'elapsed':round(time.monotonic()-start,3)})
  return result.returncode==0
 except subprocess.TimeoutExpired:
  check(name+'_program_exit',False,{'timeout':timeout});return False

def contrast(a,b):
 def L(h):
  c=[int(h[i:i+2],16)/255 for i in(1,3,5)]
  c=[v/12.92 if v<=.04045 else((v+.055)/1.055)**2.4 for v in c]
  return sum(x*y for x,y in zip(c,[.2126,.7152,.0722]))
 return(max(L(a),L(b))+.05)/(min(L(a),L(b))+.05)

async def browser_checks(slides_available):
 from playwright.async_api import async_playwright
 async with async_playwright()as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1200,'height':1000})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  states=[]
  for version in['before','after']:
   await page.goto('file:///workspace/tmp/friction_'+version+'.html')
   await page.wait_for_timeout(120)
   states.append(await page.locator('.stat').all_text_contents())
  check('real_edit_only_stray_b_removed',all(' b' not in t for t in states[1])and sum(' b' in t for t in states[0])==5,states)
  before=(ROOT/'tmp/friction_before.html').read_text(encoding='utf-8');after=(ROOT/'tmp/friction_after.html').read_text(encoding='utf-8')
  check('real_edit_preserves_entire_script',before.split('<script>')[1]==after.split('<script>')[1])
  check('real_edit_page_load',not errors,errors)
  check('real_edit_not_physics_approval',True,{'draw_calls_physics_still_present':'const ph = physics(i, 1/120);'in after,'static_friction_wrong_arrow_still_present':'else arrow(fx, fy, fx + f*SCALE' in after})
  if slides_available:
   # Execute only definitions already reviewed, excluding the final render call.
   code=(ROOT/'tmp/gen_slides.py').read_text(encoding='utf-8')
   namespace={'__name__':'resource_definitions'}
   exec(compile(code.rsplit('asyncio.run(main())',1)[0],'<reviewed-slide-definitions>','exec'),namespace)
   check('slide_definition_ids_complete',sorted(namespace['PAGES'])==list(range(1,37)))
   await page.set_viewport_size({'width':3840,'height':2160})
   clips=[]
   for n,html in namespace['PAGES'].items():
    await page.set_content(html,wait_until='domcontentloaded')
    bad=await page.evaluate('''()=>{let t=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT),n,out=[];while(n=t.nextNode()){if(!n.textContent.trim())continue;let r=document.createRange();r.selectNodeContents(n);let b=r.getBoundingClientRect();if(b.width&&b.height&&(b.left<-.5||b.top<-.5||b.right>3840.5||b.bottom>2160.5))out.push({text:n.textContent.trim(),x:b.x,y:b.y,width:b.width,height:b.height});}return out;}''')
    if bad:clips.append({'page':n,'clipped_text':bad})
    if n in[19,24]:await page.screenshot(path=str(OUT/f'slide_{n}.png'))
   save('SLIDE_TEXT_BOUNDS.json',{'clipped_pages':clips})
   check('slides_text_bounds_within_viewport',not clips,{'clipped_page_ids':[r['page']for r in clips]})
   await page.set_content(namespace['PAGES'][24],wait_until='domcontentloaded')
   style=await page.locator('.pyr .layer').first.evaluate('(e)=>({color:getComputedStyle(e).color,background:getComputedStyle(e).backgroundImage,fontSize:getComputedStyle(e).fontSize,text:e.textContent})')
   values={'white_on_cyan_00b8cf':contrast('#ffffff','#00b8cf'),'white_on_cyan_3fc9dc':contrast('#ffffff','#3fc9dc')}
   check('slide24_known_contrast_failure_reproduced',style['color']=='rgb(255, 255, 255)'and all(v<3 for v in values.values()),{'computed_style':style,'contrast':values,'semantic_result':'FAIL_CONTENT_STYLE_NOT_FULL_POSITIVE'})
  await browser.close()

def main():
 from PIL import Image,ImageStat
 from docx import Document
 from openpyxl import load_workbook
 inputs=json.loads((ROOT/'QA_INPUTS.json').read_text(encoding='utf-8'))
 manifest={r['owner_id']:r for r in inputs}
 for r in inputs:check('input_entity_sha_'+r['owner_id'],digest(Path(r['path']))==r['sha256'])
 # No financial/legal/organization statement receives business credit here.
 for owner,name in [('b1be5b288ae637de175154a5','org'),('43280ee97c7e5a3da3c9053c','xlsx'),('45444e97188d392abd301d94','docx')]:
  run(name,manifest[owner]['path'],90)
 org=ROOT/'tmp/org_chart.png'
 if org.exists():
  with Image.open(org)as im:check('org_image_reopen_nonblank',im.width>1000 and im.height>1000 and sum(ImageStat.Stat(im.convert('RGB')).stddev)>10,{'size':im.size})
 else:check('org_image_reopen_nonblank',False)
 book=ROOT/'outputs/BVI公司设立及香港银行证券账户计划表.xlsx'
 if book.exists():
  wb=load_workbook(book);ws=wb.active
  check('xlsx_reopen_grid',ws.max_column==5 and ws.max_row>=20,{'rows':ws.max_row,'columns':ws.max_column,'merged_ranges':len(ws.merged_cells.ranges)})
  check('xlsx_source_numbers_preserved',any('US$1,450'in str(c.value)for row in ws for c in row)and any('HK$10,000'in str(c.value)for row in ws for c in row))
  check('xlsx_no_formulas_or_external_links',not wb._external_links and not any(c.data_type=='f'for row in ws for c in row))
 else:check('xlsx_reopen_grid',False)
 doc=ROOT/'outputs/兼职合同.docx'
 if doc.exists():
  d=Document(doc);t='\n'.join(p.text for p in d.paragraphs)
  check('docx_reopen_mechanism',len(d.paragraphs)>40 and '兼职人员聘用合同'in t,{'paragraphs':len(d.paragraphs)})
  check('docx_legal_body_remains_not_gold',True,{'three_day_notice_unverified_or_wrong':'提前三日'in t,'business_credit':False})
 else:check('docx_reopen_mechanism',False)
 slides=run('slides',manifest['0f1603b601613eac2fecb014']['path'],240)
 files=sorted((ROOT/'outputs').glob('第*页.png'))
 check('slides_actual36_png',len(files)==36,{'count':len(files),'not_pptx':True})
 for p in files:
  with Image.open(p)as im:check('slide_dimensions_'+p.stem,im.size==(3840,2160))
 asyncio.run(browser_checks(slides))
 save('RESULT.json',{'status':'FINITE_RESOURCE_QA_COMPLETE_WITH_BUSINESS_LIMITS','checks':checks,'failed_check_names':failures,
      'all_resource_operations_pass':not failures,'whole_business_content_correct':False,
      'qualified_KEEP_or_full_autonomous_demonstration':False,'new_business_Teacher_Actor_calls':0,
      'training_started':False,'ai_cpu_cost':'UNKNOWN_NOT_ZERO'})
 print(json.dumps({'checks':len(checks),'failed':failures,'whole_business_gold':False}))

if __name__=='__main__':
 try:main()
 except Exception:
  save('HARNESS_EXCEPTION.json',{'traceback':traceback.format_exc()});raise
