"""Independent finite resource QA; no OpenClaw/business agent or model calls."""
from pathlib import Path
import gzip, hashlib, json, subprocess, time, ast

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
PROCESS=ROOT/'output/20261031_wrd_curation09/process'
IMAGE='sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'

def hs(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
 work=OUT/'workspace';work.mkdir(exist_ok=False)
 (work/'tmp').mkdir();(work/'outputs').mkdir();(work/'qa_outputs').mkdir()
 rows=[json.loads(l)for l in gzip.open(PROCESS/'FUNCTIONAL_CANDIDATES05.jsonl.gz','rt',encoding='utf-8')if l.strip()]
 ranges=[];manifest=[]
 originals=json.loads((PROCESS/'INLINE_PROGRAM_INDEX.json').read_text(encoding='utf-8'))['programs']
 for row in rows:
  call=row['messages'][-1]['tool_calls'][0];args=call['function']['arguments'];owner=row['owner_id']
  if call['function']['name']=='write':
   code=args['content'];ast.parse(code)
   assert hs(code)==row['target_original_code_sha256']
   original=next(r for r in originals if r['owner_id']==owner and r['text_sha256']==hs(code))
   assert Path(original['path']).read_bytes()==code.encode('utf-8')
   p=work/args['path'].removeprefix('/workspace/');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(code.encode('utf-8'))
   for r in row['target_code_unicode_exclusions']:
    assert hs(code[r['start']:r['end']])==r['text_sha256']
    ranges.append({'owner_id':owner,**r})
   manifest.append({'owner_id':owner,'path':args['path'],'sha256':hs(code),'stage':row['stage']})
  else:
   assert call['function']['name']=='edit'
   directory=PROCESS/'real_edit'/owner
   before=(directory/'before.html').read_text(encoding='utf-8')
   after=before
   for edit in args['edits']:
    assert after.count(edit['oldText'])==1
    after=after.replace(edit['oldText'],edit['newText'],1)
   assert after.encode('utf-8')==(directory/'after.html').read_bytes()
   assert len(before)-len(after)==5
   (work/'tmp/friction_before.html').write_bytes(before.encode('utf-8'))
   (work/'tmp/friction_after.html').write_bytes(after.encode('utf-8'))
   manifest.append({'owner_id':owner,'path':'/workspace/tmp/friction_after.html','before_sha256':hs(before),'sha256':hs(after),'stage':row['stage']})
 assert len(rows)==5 and len(ranges)==108
 save(work/'QA_INPUTS.json',manifest)
 save(OUT/'INDEPENDENT_108_RANGE_CHECK.json',{'status':'ALL108_CODE_CHARACTER_RANGES_MATCH_EXACT_ORIGINAL_PROGRAM','ranges':ranges,'does_not_claim_token_mask_qa':True})
 # Copy an independently authored harness only, never a historical agent loop.
 (work/'qa.py').write_bytes((OUT/'qa_inner.py').read_bytes())
 command=['docker','run','--rm','--network','none','--memory','6g','--cpus','4','--shm-size','1g',
          '-v',str(work.resolve())+':/workspace','-w','/workspace','--entrypoint','/bin/bash',IMAGE,
          '-lc','PYTHONDONTWRITEBYTECODE=1 /opt/eval-venv/bin/python /workspace/qa.py']
 start=time.time()
 try:
  result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=420)
  (OUT/'docker_stdout.txt').write_text(result.stdout,encoding='utf-8')
  (OUT/'docker_stderr.txt').write_text(result.stderr,encoding='utf-8')
  receipt={'exit_code':result.returncode,'elapsed_seconds':round(time.time()-start,3),'command':command,
           'image':IMAGE,'new_business_Teacher_Actor_calls':0,'model_weights_loaded':False,'training_started':False,
           'ai_cpu_resource_qa_cost':'UNKNOWN_NOT_ZERO'}
 except subprocess.TimeoutExpired as e:
  (OUT/'docker_stdout.txt').write_bytes(e.stdout or b'');(OUT/'docker_stderr.txt').write_bytes(e.stderr or b'')
  receipt={'status':'HOST_RESOURCE_QA_TIMEOUT','elapsed_seconds':round(time.time()-start,3),'command':command}
 save(OUT/'DOCKER_RECEIPT.json',receipt)
 print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
