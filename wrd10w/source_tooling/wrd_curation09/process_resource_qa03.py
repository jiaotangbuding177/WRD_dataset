"""Finite offline CPU resource replay, expressly authorized by root after review.

This executes no Agent loop, no model, no credentials and no external network.
"""
import gzip,json,shutil,subprocess,time
from pathlib import Path
from process_batch02_candidates import OUT,sha,h,dump,text

IMAGE='sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
QA=OUT/'resource_qa03'
INNER=r'''
import hashlib,json,re,subprocess
from pathlib import Path
def hs(b):return hashlib.sha256(b).hexdigest()
def extract(value):
 return [line.strip()for line in value.splitlines()if re.match(r'^(size \d+ \d+|#[0-9a-f]{6} \d+|(?:top|upper-mid|middle|lower|bottom) #[0-9a-f]{6})$',line.strip())]
inputs=json.loads(Path('/workspace/QA_INPUTS.json').read_text());results=[]
for row in inputs:
 owner=row['owner_id'];args=row['args']
 if row['tool']=='write':
  p=Path(args['path']);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(args['content'].encode('utf8'))
  data=p.read_bytes();assert data==args['content'].encode('utf8')
  result={'owner_id':owner,'operation':'write_exact_original_content_and_read_back','bytes':len(data),'sha256':hs(data),'readback_equal':True}
 else:
  run=subprocess.run(['/bin/bash','-lc',args['command']],capture_output=True,text=True,timeout=30)
  Path('/workspace/qa_outputs/'+owner+'.stdout.txt').write_text(run.stdout)
  Path('/workspace/qa_outputs/'+owner+'.stderr.txt').write_text(run.stderr)
  assert run.returncode==0,(owner,run.returncode,run.stderr)
  result={'owner_id':owner,'operation':'execute_exact_original_command','command_sha256':hs(args['command'].encode()),'exit_code':run.returncode}
  if owner=='66e542b63e52392b7e1dbfc2':
   actual=extract(run.stdout);expected=extract(row['original_feedback'])
   assert len(actual)==14 and actual==expected,(actual,expected)
   image=Path(row['material']['original_native_path']);assert hs(image.read_bytes())==row['material']['sha256']
   result.update(measurement_rows=actual,historical_measurements_match=True,image_sha256=hs(image.read_bytes()),scope='60x60 quantized counts and five1px representative colors; not arithmetic means, segmentation, CSS or readability gold')
  else:
   p=Path('/workspace/outputs/translation_c2.txt');data=p.read_bytes()
   expected=b'Room 2808, Science Gate, No. 1819 Zhongke Road, Pudong New Area, Shanghai'
   assert data==expected and run.stdout.encode()==expected
   result.update(bytes=len(data),sha256=hs(data),readback_equal=True)
 results.append(result)
out={'status':'PASS_FINITE_OFFLINE_RESOURCE_REPLAY_ONLY','results':results,'new_business_Teacher_Actor_calls':0,'training_started':False,'credentials_accessed':False,'network':'none','model_weights_loaded':False,'whole_business_quality_or_full_skill_success_claimed':False}
Path('/workspace/qa_outputs/RESULTS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
'''

def main():
    work=QA/'workspace';work.mkdir(parents=True,exist_ok=False)
    (work/'outputs').mkdir();(work/'qa_outputs').mkdir();(work/'tmp').mkdir()
    source=OUT/'SCOPED_ADDITIONAL_CANDIDATES03_v2.jsonl.gz'
    rows=list(map(json.loads,gzip.open(source,'rt',encoding='utf8')));inputs=[]
    for row in rows:
        call=row['messages'][2]['tool_calls'][0];args=json.loads(call['function']['arguments'])
        item={'owner_id':row['owner_id'],'tool':call['function']['name'],'args':args}
        if row['owner_id']=='66e542b63e52392b7e1dbfc2':
            material=row['execution_material_dependencies'][0]
            original=Path(material['restored_path']);assert sha(original)==material['sha256']
            dest=work/material['original_native_path'].removeprefix('/workspace/');dest.parent.mkdir(parents=True);shutil.copyfile(original,dest)
            packet=json.loads(Path(row['source_context']['path']).read_text(encoding='utf8'))
            item['original_feedback']='\n'.join(text(v['message'])for v in packet['owner']['immediate_original_tool_feedback'])
            item['material']=material
        inputs.append(item)
    dump(work/'QA_INPUTS.json',inputs);(work/'qa.py').write_text(INNER,encoding='utf8')
    command=['docker','run','--rm','--network','none','--memory','3g','--cpus','2','--shm-size','256m',
        '-v',str(work.resolve())+':/workspace','-w','/workspace','--entrypoint','/bin/bash',IMAGE,
        '-lc','PYTHONDONTWRITEBYTECODE=1 /opt/eval-venv/bin/python /workspace/qa.py']
    start=time.time();run=subprocess.run(command,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=120)
    (QA/'stdout.txt').write_text(run.stdout,encoding='utf8');(QA/'stderr.txt').write_text(run.stderr,encoding='utf8')
    receipt={'exit_code':run.returncode,'elapsed_seconds':round(time.time()-start,3),'command':command,'image':IMAGE,
        'candidate_input_sha256':sha(source),'new_business_Teacher_Actor_calls':0,'training_started':False,
        'credentials_mounted':False,'network':'none','GPUs_requested':False,'scope':'Finite CPU exact-action resource QA, no native Agent/model session','qa_cost':'UNKNOWN_NOT_ZERO','script_sha256':sha(__file__)}
    dump(QA/'EXECUTION.json',receipt);print(json.dumps(receipt,ensure_ascii=False))
    assert run.returncode==0,run.stderr

if __name__=='__main__':main()
