"""Offline original-record recovery and fieldwise producer linkage; never train."""
from pathlib import Path
from collections import defaultdict, Counter
import gzip,hashlib,json,re,sys
R=Path('D:/skillloop'); O=Path(__file__).parent
REMAINING='--remaining76' in sys.argv
if REMAINING:O=O.parent/'remaining76'
V9=R/'output/20261026_wrd_dataset_v9'; REC=R/'output/20261029_wrd_v9_missing_evidence_recovery'
def h(b):return hashlib.sha256(b).hexdigest()
def can(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':h(b)}
def rows(p):return list(map(json.loads,gzip.open(p,'rt',encoding='utf-8-sig')))
def save(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def zr(n,d):
 with (O/n).open('wb') as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as g:
   for x in d:g.write(json.dumps(x,ensure_ascii=False,separators=(',',':')).encode()+b'\n')
def messages(p):
 out=[]
 for ln,l in enumerate(Path(p).read_text(encoding='utf-8-sig').splitlines(),1):
  e=json.loads(l);m=e.get('message')
  if isinstance(m,dict):out.append({'event_line':ln,'message':m})
 return out
def txt(m):
 c=m.get('content',[])
 if isinstance(c,str):return c
 return '\n'.join(x.get('text','') for x in c if isinstance(x,dict))
def blocks(m):return m.get('content',[]) if isinstance(m.get('content'),list) else []
def calls(m):return [x for x in blocks(m) if x.get('type')=='toolCall']
def args(c):
 a=c.get('arguments',{});return json.loads(a) if isinstance(a,str) else a
def walk(v,path='$'):
 if isinstance(v,dict):
  if isinstance(v.get('id'),str):yield path,v
  for k,x in v.items():yield from walk(x,path+'.'+k)
 elif isinstance(v,list):
  for i,x in enumerate(v):yield from walk(x,path+'['+str(i)+']')
def strings(v,path='$'):
 if isinstance(v,str):yield path,v
 elif isinstance(v,dict):
  for k,x in v.items():yield from strings(x,path+'.'+k)
 elif isinstance(v,list):
  for i,x in enumerate(v):yield from strings(x,path+'['+str(i)+']')
def main():
 O.mkdir(parents=True,exist_ok=True); (O/'objects').mkdir(exist_ok=True)
 scope=json.loads((R/'research/plans/20261029_wrd_next_data/PLANNED_SCOPE.json').read_text())
 if REMAINING:
  firstids={x['episode_id'] for x in scope['first_batch']}
  protected={x['id'] for x in json.loads((R/'output/20261029_wrd_v9_missing_evidence_update02/ANCESTRY_CORRECTION_OVERLAY.json').read_text(encoding='utf-8'))['target_overlays']}
  chosen=[]
  for x in rows(REC/'MAKE_100_EPISODE_CLUSTERS.metadata.jsonl.gz'):
   if x['episode_id'] in firstids:continue
   ids=[t for t in x['held_target_ids'] if t not in protected]
   chosen.append({'episode_id':x['episode_id'],'route_id':x['route_id'],'positions_to_resolve':len(ids),'candidate_target_ids':ids})
  assert len(chosen)==76 and sum(x['positions_to_resolve'] for x in chosen)==590
 else:
  chosen=[x for x in scope['first_batch'] if x['route_id'] not in ['scheduled-task-config','remotion-explainer-video']]
  assert len(chosen)==17 and sum(x['positions_to_resolve'] for x in chosen)==269
 eps={x['episode_id']:x for x in rows(V9/'recovery/episodes.metadata.jsonl.gz')}
 targets=rows(V9/'outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz'); tx={(x['episode_id'],x['source_message_index']):x for x in targets}
 clusters={x['episode_id']:x for x in rows(REC/'MAKE_100_EPISODE_CLUSTERS.metadata.jsonl.gz')}
 held={x['id']:x for x in rows(REC/'HOLD_TARGETS_9096.metadata.jsonl.gz')}
 chosenids={x['episode_id'] for x in chosen}; canonical={}
 for x in rows(R/'output/20261025_wrd_training_dataset/bundle/canonical/native_episodes.jsonl.gz'):
  if x['episode_id'] in chosenids:canonical[x['episode_id']]=x
 native={}; inputs={}; wanted={x['route_id'] for x in chosen}; route_by_id=defaultdict(list)
 copied=[]
 def copy(p,expected=None):
  b=Path(p).read_bytes();s=h(b)
  if expected:assert s==expected,(str(p),s,expected)
  q=O/'objects'/s
  if not q.exists():q.write_bytes(b)
  z={'original':pin(p),'copied':pin(q)};copied.append(z);return z
 # Recover complete originals without filtering wrong / failed / thinking turns.
 for c in chosen:
  eid=c['episode_id'];e=eps[eid];src=e['source_native']; p=Path(src['path']); copy(p,src['sha256']);native[eid]=messages(p)
  orig=Path(e['source_original_path'])
  if h(orig.read_bytes())!=src['sha256']:copy(orig)
  base=orig.parents[1]/'workspace/inputs'
  rs=[]
  for name in ['route_card.json','route.json','new_route.json']:
   q=base/name
   if not q.is_file():continue
   v=json.loads(q.read_text(encoding='utf-8-sig'));cp=copy(q)
   rs.append({'name':name,'value':v,'carrier':cp})
  inputs[eid]=rs
 # Search actual written JSONs, blind comparisons only for protected producers.
 producer_count=0
 for eid,e in eps.items():
  if e.get('stage') not in ['screen','generation','prepare']:continue
  p=Path(e['source_native']['path'])
  if not p.is_file():continue
  assert h(p.read_bytes())==e['source_native']['sha256']
  ms=messages(p)
  for i,z in enumerate(ms):
   m=z['message']
   if m.get('role')!='assistant':continue
   for call in calls(m):
    a=args(call)
    if call.get('name')!='write' or not isinstance(a.get('content'),str):continue
    try:v=json.loads(a['content'])
    except (ValueError,TypeError):continue
    ack=next(((j,q) for j,q in enumerate(ms[i+1:],i+1) if q['message'].get('toolCallId')==call.get('id')),None)
    if not ack or ack[1]['message'].get('isError') is not False:continue
    for path,obj in walk(v):
     if obj['id'] not in wanted:continue
     producer_count+=1
     proof=tx.get((eid,i))
     route_by_id[obj['id']].append({'object':obj,'episode_id':eid,'message_index':i,'event_line':z['event_line'],'json_object_path':path,
      'write_path':a.get('path'),'write_content_sha256':h(a['content'].encode()),'object_canonical_sha256':h(can(obj)),
      'native':e['source_native'],'tool_call_id':call.get('id'),'ack_message_index':ack[0],
      'ack_message_sha256':h(can(ack[1]['message'])),'producer_scope':proof})
 save('SCREEN_PRODUCER_IDENTITY_INDEX.json',{'actual_success_ack_JSON_route_records':producer_count,'route_counts':dict(Counter(k for k,v in route_by_id.items() for _ in v)),
  'records':[{k:v for k,v in p.items() if k!='object'} for values in route_by_id.values() for p in values],
  'protected_bodies_used_for_semantic_labels':False})
 reports=[]; finaltargets=[];flat=[]
 for c in chosen:
  eid=c['episode_id'];ms=native[eid];links=[]
  for inp in inputs[eid]:
   v=inp['value']; stripped={k:x for k,x in v.items() if k!='candidate_gate'};matches=[]
   for p in route_by_id.get(c['route_id'],[]):
    obj=p['object']; keys=set(stripped)&set(obj)
    equal=[k for k in keys if stripped[k]==obj[k]]
    mode='EXACT_ALL_ORIGINAL_FIELDS_PLUS_CANDIDATE_GATE' if stripped==obj else 'ALL_INPUT_FIELDS_EXACT_IN_PRODUCER' if keys==set(stripped) and len(equal)==len(stripped) else None
    if mode is None and set(stripped)==set(obj)|{'conflicts'} and stripped.get('conflicts')==[] and all(stripped[k]==x for k,x in obj.items()):
     mode='EXACT_ORIGINAL_OBJECT_PLUS_EMPTY_CONFLICTS_DEFAULT'
    if mode is None and set(stripped)=={'id','name','category','source_ids','steps','route_signature','value_plan'} and all(stripped[k]==obj.get(k) for k in ['id','name','category','source_ids','route_signature','value_plan']) and stripped['steps']==obj.get('route_signature',{}).get('steps'):
     mode='EXACT_SIX_ORIGINAL_FIELDS_PLUS_STEPS_COPIED_FROM_ROUTE_SIGNATURE'
    if mode:
     matches.append({k:x for k,x in p.items() if k!='object'}|{'match_mode':mode,'matching_field_names':sorted(equal),
      'original_object_field_value_sha256':{k:h(can(x)) for k,x in obj.items()}})
   # Determine actual delivered receipt from native observation, no file-open inference.
   receipts=[]; raw=Path(inp['carrier']['original']['path']).read_bytes(); rv=raw.decode('utf-8-sig')
   for i,z in enumerate(ms):
    for call in calls(z['message']):
     a=args(call); command=a.get('command','');readpath=a.get('path',a.get('file_path',''))
     if '/workspace/inputs/'+inp['name']!=readpath and '/workspace/inputs/'+inp['name'] not in command:continue
     ack=next(((j,q) for j,q in enumerate(ms[i+1:],i+1) if q['message'].get('toolCallId')==call.get('id')),None)
     if not ack:continue
     obs=txt(ack[1]['message']); norm=obs.replace('\r\n','\n');rnorm=rv.replace('\r\n','\n')
     ok=rv in obs; normalized=rnorm.strip() in norm
     original_scalar_receipts=[]
     for producer in route_by_id.get(c['route_id'],[]):
      if not any(x['episode_id']==producer['episode_id'] and x['message_index']==producer['message_index'] for x in matches):continue
      for path,value in strings(producer['object']):
       if len(value)<32:continue
       encoded=json.dumps(value,ensure_ascii=False)
       start=norm.find(encoded)
       if start>=0 and encoded in rnorm:
        original_scalar_receipts.append({'producer_episode_id':producer['episode_id'],'producer_message_index':producer['message_index'],
          'original_field_path':path,'scalar_UTF8_sha256':h(value.encode()),'quoted_scalar_characters':len(encoded),
          'normalized_observation_character_start':start,'normalized_observation_character_end':start+len(encoded),
          'quoted_scalar_sha256':h(encoded.encode()),'method':'EXACT_JSON_QUOTED_ORIGINAL_SCALAR_PRESENT_IN_INPUT_AND_ACTUAL_TOOL_OBSERVATION'})
     # JSON-rendering read may be exact whole bytes or interior to concatenated stdout.
     receipts.append({'call_message_index':i,'observation_message_index':ack[0],'tool_call_id':call.get('id'),
      'entire_original_file_text_contiguous_in_actual_observation':ok,'observation_text_sha256':h(obs.encode()),
      'entire_file_after_CRLF_to_LF_and_outer_whitespace_normalization_contiguous':normalized,
      'received_protected_original_scalar_proofs':original_scalar_receipts,
      'observation_message_sha256':h(can(ack[1]['message']))})
   protected=[p for p in matches if p['producer_scope'] and p['producer_scope']['source_admission']=='HOLD_PROTECTED']
   protected_producer_keys={(p['episode_id'],p['message_index']) for p in protected}
   provedobs=[q['observation_message_index'] for q in receipts if q['entire_original_file_text_contiguous_in_actual_observation'] or q['entire_file_after_CRLF_to_LF_and_outer_whitespace_normalization_contiguous'] or any((p['producer_episode_id'],p['producer_message_index']) in protected_producer_keys for p in q['received_protected_original_scalar_proofs'])]
   boundary=min(provedobs) if protected and provedobs else None
   links.append({'input_carrier':inp['carrier'],'input_name':inp['name'],'id':v.get('id'),'field_names':sorted(v),
    'canonical_input_sha256':h(can(v)),'producer_matches':matches,'actual_receipts':receipts,
    'earliest_proven_protected_exposure_observation_index':boundary})
  boundary=min((x['earliest_proven_protected_exposure_observation_index'] for x in links if x['earliest_proven_protected_exposure_observation_index'] is not None),default=None)
  for tid in c['candidate_target_ids']:
   t=held[tid];i=t['source_message_index'];m=ms[i]['message'];cm=canonical[eid]['messages'][i]
   assert h(json.dumps(cm,ensure_ascii=False,separators=(',',':')).encode())==t['source_message_sha256']
   assert cm.get('content')==m.get('content') and canonical[eid]['source_event_lines'][i]==ms[i]['event_line']
   protected=boundary is not None and i>boundary
   decision='HOLD_PROTECTED_ACTUAL_ROUTE_PRODUCER' if protected else 'HOLD_ANCESTRY_NOT_CLOSED'
   nextobs=[]
   for call in calls(m):
    found=next(((j,q) for j,q in enumerate(ms[i+1:],i+1) if q['message'].get('toolCallId')==call.get('id')),None)
    if found:nextobs.append({'message_index':found[0],'event_line':found[1]['event_line'],'message_sha256':h(can(found[1]['message'])),'message':found[1]['message']})
   finaltargets.append({'id':tid,'episode_id':eid,'route_id':c['route_id'],'source_message_index':i,'source_event_line':ms[i]['event_line'],
    'original_message_sha256':h(can(m)),'original_message':m,'canonical_metadata_message_sha256':t['source_message_sha256'],
    'canonical_original_content_and_event_line_exact_match':True,'actual_tool_feedback':nextobs,'original_target_metadata':t,
    'current_decision':decision,'positive_loss':0,'scope_is_not_content_correctness':True,
    'protected_dependency_observation_index':boundary,'new_author_target':None})
  for i,z in enumerate(ms):flat.append({'episode_id':eid,'message_index':i,'event_line':z['event_line'],'message_sha256':h(can(z['message'])),'original_message':z['message'],'audit_only':True})
  reports.append({'episode_id':eid,'route_id':c['route_id'],'scope_targets':len(c['candidate_target_ids']),'messages_recovered':len(ms),
   'native':clusters[eid]['source_native'],'route_links':links,'proven_protected_boundary':boundary,
   'current_decisions':dict(Counter(x['current_decision'] for x in finaltargets if x['episode_id']==eid)),
   'full_chain_trainable':False,'original_thinking_preserved':True})
 zr('ORIGINAL_EPISODE_MESSAGES.jsonl.gz',flat);zr('TARGET_DECISIONS_AND_ORIGINAL_BODIES.jsonl.gz',finaltargets)
 save('ROUTE_PRODUCER_CLOSURE.json',{'episodes':reports,'not_training_admission':True})
 # Preserve the exact frozen byte carriers already resolved by prior recovery,
 # without treating final resources as earlier versions or as positive examples.
 resource_refs=[]
 for res in rows(REC/'MAKE_PRIOR_RESOURCES.metadata.jsonl.gz'):
  if res['episode_id'] not in chosenids:continue
  d={'episode_id':res['episode_id'],'node_id':res['node_id'],'native_path':res['native_path'],
     'observed_after_assistant_message_index':res['observed_after_assistant_message_index'],'file_identity':res['file_identity'],
     'unknown_reasons':res['unknown_reasons'],'role':'AUDIT_ONLY_NO_POSITIVE_LOSS','recovered_carrier':None}
  f=res['file_identity']
  if f:
   for carrier in res['carriers']:
    p=Path(carrier['path'])
    if p.is_file() and h(p.read_bytes())==f['sha256']:
     d['recovered_carrier']=copy(p,f['sha256']);break
  resource_refs.append(d)
 final_resources=[]
 for eid in chosenids:
  for f in clusters[eid]['final_snapshot_files']:
   cp=None
   for carrier in f['carriers']:
    p=Path(carrier['path'])
    if p.is_file() and h(p.read_bytes())==f['sha256']:cp=copy(p,f['sha256']);break
   final_resources.append({'episode_id':eid,'relative_path':f['relative_path'],'sha256':f['sha256'],'recovered_carrier':cp,
    'role':'AUDIT_ONLY_FINAL_VERSION_NOT_EARLIER_INPUT_OR_SEMANTIC_PASS'})
 for p in {x['native']['path']:x['native']['sha256'] for report in reports for link in report['route_links'] for x in link['producer_matches']}.items():copy(*p)
 zr('ACTUAL_RESOURCE_CARRIERS.jsonl.gz',resource_refs);zr('FINAL_RESOURCE_CARRIERS.jsonl.gz',final_resources)
 save('RECOVERY_SUMMARY.json',{'episodes':len(chosen),'targets':len(finaltargets),'full_original_native_objects':len(chosen),'messages_recovered':len(flat),
  'current_decisions':dict(Counter(x['current_decision'] for x in finaltargets)),'new_admitted_targets':0,
  'actual_calls':sum(len(calls(x['original_message'])) for x in flat),'original_reasoning_blocks':dict(Counter(b.get('type') for x in flat for b in blocks(x['original_message']) if b.get('type') in ['thinking','reasoning'])),
  'known_prior_resource_refs':len(resource_refs),'frozen_prior_carriers_recovered':sum(x['recovered_carrier'] is not None for x in resource_refs),
  'final_resource_refs':len(final_resources),'final_carriers_recovered':sum(x['recovered_carrier'] is not None for x in final_resources),
  'new_training_or_native_runs':0,'objects_copied':len({x['copied']['sha256'] for x in copied}),'copied_objects':copied,
  'upstream_files_not_modified':True,'unknown_ancestry_does_not_prove_no_training_value':True})
 print(json.dumps({'episodes':len(chosen),'targets':len(finaltargets),'messages':len(flat),'decisions':dict(Counter(x['current_decision'] for x in finaltargets))}))
if __name__=='__main__':main()
