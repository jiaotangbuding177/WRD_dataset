from pathlib import Path
import ast,json,subprocess,sys,wave,hashlib,traceback
from PIL import Image
from playwright.sync_api import sync_playwright
R=Path('/workspace'); results=[]
def run(name, argv, expected=0, timeout=90):
 p=subprocess.run(argv,cwd=R,capture_output=True,text=True,timeout=timeout)
 (R/'qa_outputs'/f'{name}.stdout.txt').write_text(p.stdout)
 (R/'qa_outputs'/f'{name}.stderr.txt').write_text(p.stderr)
 results.append({'name':name,'exit_code':p.returncode,'expected_exit':expected,'pass':p.returncode==expected})
 return p
(R/'qa_outputs').mkdir()
try:
 # Only scripts already read in full by the curator, no downloaded code/API.
 for name in ['gen_jd.py','gen_docs.py','gen_outline.py','make_docx.py']:
  run(name,['/opt/eval-venv/bin/python',str(R/'tmp'/name)])
 from docx import Document
 docs=[]
 for p in sorted((R/'outputs').glob('*.docx')):
  d=Document(p); paragraphs=[x.text for x in d.paragraphs]
  docs.append({'path':str(p),'paragraphs':len(paragraphs),'tables':len(d.tables),
               'text':'\n'.join(paragraphs),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 (R/'qa_outputs/docx_actual_content.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2))
 # Real old TypeError, real intermediate SyntaxError and corrected old harness.
 p=run('game_test_v0',['node',str(R/'versions/game_test_v0.js')],1)
 assert 'launch is not a function' in p.stderr
 p=run('game_test_v1',['node',str(R/'versions/game_test_v1.js')],1)
 assert 'already been declared' in p.stderr
 p=run('game_test_v2',['node',str(R/'versions/game_test_v2.js')],0)
 assert 'ERRORS: none' in p.stdout
 # Independent live input/state checks, rather than the original pixel average.
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  page=b.new_page(viewport={'width':1100,'height':760})
  errs=[];page.on('pageerror',lambda e:errs.append(str(e)))
  old=R/'versions/874f734c5198497a8a3cda31.html'
  new=R/'outputs/contra.html'
  spawn=[]
  for path in [old,new]:
   page.goto(path.as_uri());page.wait_for_timeout(100)
   spawn.append(page.evaluate('()=>{camX=0;enemies=[];spawnRunner(-1);return enemies.length}'))
  assert spawn==[0,1],spawn
  page.goto(new.as_uri());page.keyboard.press('Enter');page.wait_for_timeout(250)
  initial=page.evaluate('()=>({state,x:P.x})');assert initial['state']=='play'
  page.keyboard.down('ArrowRight');page.keyboard.down('j');page.wait_for_timeout(700)
  current=page.evaluate('()=>({state,x:P.x,pb:pbullets.length})')
  page.keyboard.up('ArrowRight');page.keyboard.up('j')
  assert current['state']=='play' and current['x']>initial['x']+20 and current['pb']>0,(initial,current)
  page.screenshot(path=str(R/'qa_outputs/game_live.png'))
  assert not errs,errs
  results.append({'name':'game_native_input_and_local_spawn_repair','pass':True,'spawn_v0_v1':spawn,'before':initial,'after':current})
  # Poster is explicitly partial: fabricated QR artwork is NOT validated.
  page.set_viewport_size({'width':1240,'height':1754})
  page.goto((R/'tmp/poster.html').as_uri());page.wait_for_timeout(250)
  page.screenshot(path=str(R/'qa_outputs/poster.png'))
  poster=page.evaluate('()=>({w:document.querySelector(".poster").offsetWidth,h:document.querySelector(".poster").offsetHeight,qrHasURL:!!document.querySelector(".qr a[href]")})')
  assert (poster['w'],poster['h'])==(1240,1754)
  results.append({'name':'poster_layout_only_not_QR_or_business_fact_gold','pass':True,'details':poster})
  b.close()
 # Compare the real broken FFmpeg filter to the real recorded repair using
 # explicitly synthetic tiny media. This is NOT historical audio/image replay.
 f=R/'tmp/archery';f.mkdir(exist_ok=True)
 Image.new('RGB',(1920,1080),(20,70,120)).save(f/'shot1.png')
 Image.new('RGBA',(100,80),(255,20,20,255)).save(f/'title1.png')
 with wave.open(str(f/'nar1.wav'),'wb')as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100);w.writeframes(b'\0'*4410*4)
 helper=R/'qa_outputs/one_clip.py'
 helper.write_text("from pathlib import Path\nimport ast,sys\np=Path(sys.argv[1]); tree=ast.parse(p.read_text()); tree.body=[n for n in tree.body if not(isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Name)and n.value.func.id=='main')];ns={'__name__':'finite_resource_probe'};exec(compile(tree,str(p),'exec'),ns);ns['build'](1,0.2,'title1.png','center','in')\n")
 before=R/'versions/ep_4d412dca2c57480536e7_65_before.py'
 after=R/'versions/ep_4d412dca2c57480536e7_65_after.py'
 p=run('compose_filter_before',[sys.executable,str(helper),str(before)],1)
 assert 'vbase' in p.stdout or 'vbase' in p.stderr
 p=run('compose_filter_after',[sys.executable,str(helper),str(after)],0)
 assert (f/'clip1.mp4').stat().st_size>0
 # Exact repaired overlay renderer, with the recorded SVG replacing tofu emoji.
 p=run('overlays_recorded_final',[sys.executable,str(f/'render_overlays.py')],0)
 sizes={n:Image.open(f/(n+'.png')).size for n in ['title1','win','end']}
 assert sizes['title1']==(2000,300) and sizes['win']==(2000,520) and sizes['end']==(2000,300),sizes
 results.append({'name':'overlay_renderer_sizes','pass':True,'sizes':sizes})
except Exception as e:
 results.append({'name':'harness_exception','pass':False,'error':str(e),'traceback':traceback.format_exc()})
finally:
 out={'status':'PASS_SCOPED_RESOURCE_CHECKS' if all(x['pass'] for x in results) else 'FAIL_PRESERVED',
      'results':results,'new_Agent_or_model_calls':0,'training_started':False,
      'business_quality_or_qualified_KEEP_proven':False,
      'compose_fixtures':'NEW_SYNTHETIC_LOCAL_FILTER_COUNTEREXAMPLE_NOT_ORIGINAL_TRIAL',
      'docx_visual_quality':'NOT_SCORED_BY_THIS_HARNESS','poster_QR_functionality':'NOT_VALIDATED_FABRICATED_ARTWORK_IS_NOT_POSITIVE_GOLD'}
 (R/'qa_outputs/RESULT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps({'status':out['status'],'checks':len(results),'failed':[x['name']for x in results if not x['pass']]}))
sys.exit(0 if out['status'].startswith('PASS') else 1)
