"""Recover exact program versions and run bounded resource checks, no Agent/model.

This harness is not an OpenClaw replacement. It executes only named, manually
read resources in the previously fixed image, without network or credentials.
"""
from pathlib import Path, PurePosixPath
import argparse, ast, hashlib, json, shutil, subprocess, time

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / 'output/20261030_wrd_gap08/semantic_root'
FIRST = ROOT / 'output/20261030_wrd_gap08/corpus/first6'
IMAGE = 'sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'


def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def pin(p): return {'path':str(p.resolve()), 'bytes':p.stat().st_size, 'sha256':sha(p)}


def text(m):
    c=m.get('content', [])
    return c if isinstance(c, str) else '\n'.join(b.get('text','') for b in c if isinstance(b,dict))


def prepare():
    WORK.mkdir(parents=True, exist_ok=True)
    ws=WORK/'qa/workspace'
    assert not ws.exists(), 'preserve earlier checks'
    ws.mkdir(parents=True)
    (ws/'outputs').mkdir(); (ws/'tmp').mkdir(); (ws/'versions').mkdir()
    manifest=load(FIRST/'FIRST6_ACTUAL_GROUPS.json')
    refs=[]; transitions=[]; groups={}
    for ref in manifest['groups']:
        ep=ref['episode_id']; g=load(FIRST/ep/'GROUP.json');groups[ep]=g
        for target in g['original_targets_with_feedback']:
            source=Path(target['original_code_file']['path'])
            assert sha(source)==target['original_code_file']['sha256']
            path=PurePosixPath(target['native_path'])
            assert path.is_absolute() and path.parts[1]=='workspace' and '..' not in path.parts
            destination=ws.joinpath(*path.parts[2:]);destination.parent.mkdir(parents=True,exist_ok=True)
            code=source.read_text(encoding='utf-8')
            call=next(b for b in target['original_message']['content'] if b.get('id')==target['tool_call_id'])
            assert call['arguments']['content']==code and call['arguments']['path']==str(path)
            assert all(x['message'].get('isError') is False for x in target['actual_feedback'])
            destination.write_bytes(source.read_bytes())
            (ws/'versions'/f"{target['original_target_id']}{source.suffix}").write_bytes(source.read_bytes())
            refs.append({'episode':ep,'target':target['original_target_id'],'native_path':str(path),
                         'original_code':pin(source),'workspace_file':str(destination.relative_to(ws))})
    selected={
        'ep_4aadd96d99f2c07543c7':{'/workspace/outputs/contra.html'},
        'ep_4d412dca2c57480536e7':{'/workspace/tmp/archery/compose.py','/workspace/tmp/archery/render_overlays.py'},
    }
    for ep, paths in selected.items():
        messages=groups[ep]['original_context']['messages']
        for index,m in enumerate(messages):
            for call in m.get('content',[]) if isinstance(m.get('content'),list) else []:
                if call.get('type')!='toolCall' or call.get('name')!='edit':continue
                args=call['arguments'];native=args.get('path')
                if native not in paths:continue
                obs=next((x for x in messages[index+1:] if x.get('toolCallId')==call['id']),None)
                assert obs and obs.get('isError') is False
                p=ws.joinpath(*PurePosixPath(native).parts[2:]);old=p.read_text(encoding='utf-8')
                new=old
                for edit in args['edits']:
                    assert new.count(edit['oldText'])==1
                    new=new.replace(edit['oldText'],edit['newText'],1)
                before=ws/'versions'/f'{ep}_{index}_before{p.suffix}'
                after=ws/'versions'/f'{ep}_{index}_after{p.suffix}'
                before.write_text(old,encoding='utf-8');after.write_text(new,encoding='utf-8')
                p.write_text(new,encoding='utf-8')
                transitions.append({'episode':ep,'index':index,'call_id':call['id'],'arguments':args,
                                    'before':pin(before),'after':pin(after),'actual_observation':obs,
                                    'version_reconstruction':'EXACT_RECORDED_SUCCESSFUL_EDIT_NOT_NEW_TEACHER_CALL'})
    # The real test-harness correction was issued as two shell commands, not
    # as native edit. Preserve both the invalid intermediate and valid result.
    game=groups['ep_4aadd96d99f2c07543c7']['original_context']['messages']
    script=ws/'tmp/test_game.js';v0=script.read_text(encoding='utf-8')
    assert "chromium.launch is not a function" in text(game[12])
    assert 'Identifier' in text(game[16]) and "already been declared" in text(game[16])
    line="try{chromium=require('playwright');}catch(e){chromium=require('/usr/lib/node_modules/playwright');}"
    assert v0.count(line)==1
    v1=v0.replace(line,"const chromium=require('playwright').chromium;")
    assert v1.splitlines()[1]=='let chromium;'
    v2='\n'.join(v1.splitlines()[:1]+v1.splitlines()[2:])+'\n'
    for name,body in [('game_test_v0.js',v0),('game_test_v1.js',v1),('game_test_v2.js',v2)]:
        (ws/'versions'/name).write_text(body,encoding='utf-8')
    script.write_text(v2,encoding='utf-8')
    save(WORK/'PROGRAM_VERSION_RECOVERY.json',{'status':'EXACT_ORIGINAL_PROGRAMS_AND_RECORDED_EDITS_RECOVERED_NOT_ADMISSION',
        'programs':refs,'actual_native_edit_transitions':transitions,'test_harness_versions':[
            pin(ws/'versions'/n) for n in ['game_test_v0.js','game_test_v1.js','game_test_v2.js']],
        'original_failure_and_retest_indices':[12,16,18,34], 'new_model_calls':0,'training_started':False})
    print(json.dumps({'programs':len(refs),'edit_transitions':len(transitions),'workspace':str(ws)}))


DRIVER = r'''from pathlib import Path
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
'''


def run_qa():
    ws=WORK/'qa/workspace';assert ws.exists()
    script=ws/'qa_driver.py';script.write_text(DRIVER,encoding='utf-8')
    images=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',IMAGE],text=True).strip()
    assert images==IMAGE
    argv=['docker','run','--rm','--network','none','--memory','6g','--cpus','4','--shm-size','1g',
          '--mount',f'type=bind,source={ws.resolve()},target=/workspace','--workdir','/workspace',
          '--entrypoint','/opt/eval-venv/bin/python',IMAGE,'/workspace/qa_driver.py']
    start=time.monotonic();p=subprocess.run(argv,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
    (WORK/'qa/container.stdout.txt').write_text(p.stdout,encoding='utf-8')
    (WORK/'qa/container.stderr.txt').write_text(p.stderr,encoding='utf-8')
    save(WORK/'qa/EXECUTION_RECEIPT.json',{'argv':argv,'fixed_image':images,'exit_code':p.returncode,
         'wall_seconds':time.monotonic()-start,'script_sha256':sha(Path(__file__)),
         'new_model_calls':0,'OpenClaw_Agent_loop_executed':False,'training_started':False,
         'pure_resource_CPU_check_not_Agent_demonstration':True})
    print(p.stdout.strip());print('container_exit',p.returncode)
    return p.returncode


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['prepare','qa']);a=ap.parse_args()
    if a.operation=='prepare':prepare()
    else:raise SystemExit(run_qa())
