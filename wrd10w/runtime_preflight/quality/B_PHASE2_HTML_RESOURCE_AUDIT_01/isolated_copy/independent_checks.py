from pathlib import Path
import json,subprocess,sys
W=Path('/workspace');S=W/'outputs/skill';O=W/'independent_results';O.mkdir(exist_ok=True)
rows=[]
def run(label,args):
 r=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 rows.append({'label':label,'argv':list(map(str,args)),'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 return r
def gen(label,cfg,topic,out):
 return run(label,[sys.executable,S/'scripts/gen_animation.py','--config',cfg,'--topic',topic,'--scaffold',S/'assets/scaffold.js','--out',out])
def verify(label,page):
 return run(label,['node',S/'scripts/verify_animation.mjs',page,'--out',O/(label+'.json'),'--screenshot',O/(label+'.png')])
gen('REGENERATE_MAKER',W/'outputs/fixtures/skating/config.json',W/'outputs/fixtures/skating/topic.js',O/'maker.html')
verify('EXACT_PUBLIC_MAKER_VERIFY',O/'maker.html')
gen('REGENERATE_SYNTHETIC_BALL',S/'examples/ball_bounce/config.json',S/'examples/ball_bounce/topic.js',O/'ball.html')
verify('EXACT_PUBLIC_BALL_VERIFY',O/'ball.html')
# This declared synthetic canary intentionally disables only the resume click.
# Original B assets and fixtures are not modified. A real verifier should fail.
canary=(O/'ball.html').read_text().replace('</body>',r"""<script>
{let n=0;document.querySelector('.wrd-btn-toggle').addEventListener('click',function(e){if(++n>=2){e.stopImmediatePropagation();e.preventDefault();}},true);}
</script></body>""")
(O/'resume_disabled_canary.html').write_text(canary)
verify('VERIFIER_FALSE_RESUME_CANARY',O/'resume_disabled_canary.html')
cfg=json.loads((S/'examples/ball_bounce/config.json').read_text());cfg['subtitle']=42
(O/'subtitle_nonstring.json').write_text(json.dumps(cfg))
gen('BAD_OPTIONAL_SUBTITLE_TYPE',O/'subtitle_nonstring.json',S/'examples/ball_bounce/topic.js',O/'bad_subtitle.html')
(O/'ACTUAL_COMMANDS.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'commands':len(rows),'actual_returncodes':{r['label']:r['rc'] for r in rows}}))
