"""Verify the append-only, bounded extra-batch ancestry proof."""
from pathlib import Path
import json,gzip,hashlib,re
O=Path(__file__).parent;B=O.parent;R=Path('D:/skillloop')
def h(b):return hashlib.sha256(b).hexdigest()
def can(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return list(map(json.loads,gzip.open(p,'rt',encoding='utf-8-sig')))
def pin(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def parse(p):
 m=[]
 for line in Path(p).read_text(encoding='utf-8-sig').splitlines():
  e=json.loads(line)
  if e.get('type')=='message' and isinstance(e.get('message'),dict):m.append(e['message'])
 return m
def text(m):
 c=m.get('content',[]);return c if isinstance(c,str) else '\n'.join(x.get('text','') for x in c if isinstance(x,dict))
def at(v,p):
 for key,idx in re.findall(r'\.([^\.\[]+)|\[(\d+)\]',p[1:]):v=v[key] if key else v[int(idx)]
 return v
def main():
 d=load(O/'LATE_NATIVE_ROUTE_PRODUCER_CLOSURE.json');a=rows(d['fixed226_H12_scope_source']['path'])
 f={s for x in a for s in x['original226']};assert len(f)==226
 old=load(B/'remaining76/FINAL_MANIFEST.json')
 # Check every previously sealed file, including the old 249 count. This overlay
 # never rewrites it to 193 or silently changes old scope receipts.
 for row in Path(old['allowlist']['path']).read_text(encoding='utf-8').splitlines():
  p=json.loads(row);assert h(Path(p['path']).read_bytes())==p['sha256']
 targets={x['id']:x for x in rows(B/'remaining76/TARGET_DECISIONS_AND_ORIGINAL_BODIES.jsonl.gz')}
 eplinks=load(B/'remaining76/ROUTE_PRODUCER_CLOSURE.json')['episodes'];epby={x['episode_id']:x for x in eplinks}
 boundaries={};checked_scalars=0
 for link in d['links']:
  prod=link['producer'];nm=parse(prod['producer_native']['path']);assert h(Path(prod['producer_native']['path']).read_bytes())==prod['producer_native']['sha256']
  w=next(c for c in nm[prod['write_message_index']]['content'] if c.get('id')==prod['write_call_id']);wa=w['arguments']
  if isinstance(wa,str):wa=json.loads(wa)
  assert w['name']=='write' and h(wa['content'].encode())==prod['whole_write_content_sha256']
  card=at(json.loads(wa['content']),prod['card_json_pointer']);assert h(can(card))==prod['card_canonical_sha256']
  ack=nm[prod['ack_message_index']];assert ack['toolCallId']==w['id'] and ack.get('isError') is False
  protected_input=False
  for inp in prod['actual_input_receipts_before_write']:
   i=inp['observation_message_index'];obs=text(nm[i]);assert json.loads(obs)==load(prod['input_file']['path']) and i<prod['write_message_index']
   ids={p['source_id'] for x in json.loads(obs)['proposals'] for p in x['previews']}
   assert ids==set(inp['actually_received_source_ids'])
   if ids&f:protected_input=True
  assert protected_input and prod['proven_protected_before_write']
  current=load(link['input_file']['path']);assert all(current[k]==card[k] for k in ['value_plan','route_signature'])
  cm=parse(epby[link['episode_id']]['native']['path']);poss=[]
  for obs in link['actual_downstream_receipts']:
   m=cm[obs['observation_message_index']];s=text(m).replace('\r\n','\n');assert m['toolCallId']==obs['tool_call_id']
   if obs['entire_normalized_input_received']:assert Path(link['input_file']['path']).read_text(encoding='utf-8-sig').strip() in s
   for scalar in obs['original_scalar_receipts']:
    v=at(card,scalar['original_field_path']);q=json.dumps(v,ensure_ascii=False)
    assert s[scalar['normalized_observation_start']:scalar['normalized_observation_end']]==q and h(q.encode())==scalar['quoted_sha256']
    checked_scalars+=1
   poss.append(obs['observation_message_index'])
  assert link['protected_exposure_boundary']==min(poss)
  boundaries[link['episode_id']]=min(poss)
 for x in d['target_overlays']:
  t=targets[x['id']];assert t['current_decision']=='HOLD_ANCESTRY_NOT_CLOSED'
  assert x['source_message_index']==t['source_message_index'] and x['source_message_index']>boundaries[x['episode_id']]
 assert len(d['target_overlays'])==len({x['id'] for x in d['target_overlays']})==56
 assert d['remaining_unknown']==193 and d['old_pending']==249
 for p in (O/'objects').iterdir():assert h(p.read_bytes())==p.name
 q={'status':'PASS_ACTUAL_EXTRA_PRODUCER_INPUT_OUTPUT_AND_CONSUMER_RECEIPTS','new_protected':56,'old_pending':249,'remaining_unknown':193,
  'consumer_episodes':len(boundaries),'exact_scalar_receipts_checked':checked_scalars,'original76_allowlisted_files_all_unchanged':True,
  'full_original226_union_verified':len(f),'no_new_positive_loss_or_native_run':True,'closure':pin(O/'LATE_NATIVE_ROUTE_PRODUCER_CLOSURE.json'),'verifier':pin(__file__)}
 (O/'LOCAL_QA.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 files=[p for p in sorted(O.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name not in ['FINAL_ALLOWLIST.jsonl','FINAL_MANIFEST.json']]
 al=O/'FINAL_ALLOWLIST.jsonl';al.write_text(''.join(json.dumps({'relative':str(p.relative_to(O)).replace('\\','/'),**pin(p)},ensure_ascii=False,separators=(',',':'))+'\n' for p in files),encoding='utf-8')
 (O/'FINAL_MANIFEST.json').write_text(json.dumps({'status':'SEALED_APPEND_ONLY_LATE_PRODUCER_CLOSURE','files':len(files),'bytes':sum(p.stat().st_size for p in files),'allowlist':pin(al),'qa':pin(O/'LOCAL_QA.json'),'new_protected':56,'remaining_unknown':193,'new_training_samples':0,'new_native_or_training':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(q))
if __name__=='__main__':main()
