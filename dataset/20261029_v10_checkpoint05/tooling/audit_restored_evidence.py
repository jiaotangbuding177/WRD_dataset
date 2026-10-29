"""Independently reparse every restored native response and cost file pin."""
from pathlib import Path
from collections import Counter
import hashlib,json,argparse

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def audit(root):
 root=Path(root);manifest=load(root/'PAYLOAD_MANIFEST.json');bysha={}
 for ref in manifest['files']:bysha.setdefault(ref['sha256'],root/ref['path'])
 def get(h):
  p=bysha[h];assert digest(p)==h;return p
 census=load(root/'native_material05/RAW_HTTP_CENSUS.json');classes=Counter();R=0;seen=set();json_count=0
 for record in census['calls']:
  owner=(record['episode_id'],record['call_id']);assert owner not in seen;seen.add(owner)
  req=get(record['request_sha256']);json.loads(req.read_text(encoding='utf-8-sig'))
  text=get(record['response_sha256']).read_text(encoding='utf-8-sig')
  done=0;finish=[];chars=0;bad=[]
  if text.lstrip().startswith('{'):
   frame=json.loads(text);json_count+=1
   for choice in frame.get('choices',[]):
    if choice.get('index',0)!=0:continue
    msg=choice.get('message',{});chars+=len(msg.get('reasoning_content','')or'')
    if choice.get('finish_reason')is not None:finish.append(choice['finish_reason'])
  else:
   for block in text.replace('\r\n','\n').split('\n\n'):
    payload='\n'.join(l[5:].lstrip(' ')for l in block.splitlines()if l.startswith('data:'))
    if not payload:continue
    if payload=='[DONE]':done+=1;continue
    try:frame=json.loads(payload)
    except json.JSONDecodeError:bad.append(len(payload));continue
    for choice in frame.get('choices',[]):
     if choice.get('index',0)!=0:continue
     chars+=len(choice.get('delta',{}).get('reasoning_content','')or'')
     if choice.get('finish_reason')is not None:finish.append(choice['finish_reason'])
  assert chars==record['explicit_original_R_chars'],owner
  assert done==record['actual_DONE_count'] and finish==record['actual_finish_reasons'],owner
  assert not bad,owner
  if record['classification']=='supported_complete':
   assert finish and all(f in ['stop','tool_calls']for f in finish)
   assert done==1 or text.lstrip().startswith('{')
  elif record['classification']=='COMPLETE_length_not_stop':assert done==1 and finish==['length']
  else:assert done==0 and not finish
  classes[record['classification']]+=1;R+=chars
 assert len(seen)==339 and R==460514 and json_count==1
 assert dict(classes)==census['completion_classes']
 scope=load(root/'COST_ACCOUNTING_SCOPE.json')['latest_closed_native_collection_snapshot'];closed=Counter()
 for ref in scope['exact_closed_usage_files']:
  original=load(get(ref['usage_sha256']))
  assert isinstance(original,dict)
  if 'known_total_tokens'in original:assert original['known_total_tokens']==ref['known_total_tokens']
  closed.update(known_tokens=ref['known_total_tokens'],request_identities=ref['request_identities'],unknown_usage=ref['unknown_usage'])
 assert closed==Counter(known_tokens=22156371,request_identities=286,unknown_usage=3)
 return {'status':'PASS_RESTORED_ACTUAL_RAW_FRAMES_AND_CLOSED_USAGE_PINS',
  'native_HTTP_reparsed':len(seen),'SSE':338,'JSON_external_helper':json_count,
  'transport_class_counts':dict(classes),'original_R_characters_recounted':R,
  'closed_usage_files_re_read':len(scope['exact_closed_usage_files']),'cost':dict(closed),
  'partial_responses_or_length_not_given_fake_EOS':True,'old_CV_Q_and_decisions_not_automatically_admitted':True,
  'training_started':False,'weights_loaded':False,'script_sha256':digest(__file__)}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 r=audit(a.root);a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(r))
