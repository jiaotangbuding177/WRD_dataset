
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
