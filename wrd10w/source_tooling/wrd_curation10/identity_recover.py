"""Offline next51 source identity recovery; preserve actual messages/feedback.

This does not admit targets, modify checkpoint09 or execute captured commands.
Identity references, delivered observations and semantic approval are separate.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse, gzip, hashlib, json, re, shutil

ROOT=Path('D:/skillloop')
OUT=ROOT/'output/20261031_wrd_curation10/identity'
CORPUS=ROOT/'output/20261030_wrd_gap08/corpus'
MAIN=ROOT/'output/20261027_wrd_main_v10'
OLD=ROOT/'output/20261031_wrd_next51_planning/gap_review/OLD8376_REBASED_OWNER_WORKLOAD.metadata.jsonl.gz'
OVER=ROOT/'output/20261031_wrd_curation09/process/batch02/coverage_overlay/CURRENT34616_OWNER_COVERAGE09_FINAL_OVERLAY.jsonl.gz'

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def h(b): return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def js(v,sort=False): return json.dumps(v,ensure_ascii=False,separators=(',',':'),sort_keys=sort)
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for line in f:
   if line.strip(): yield json.loads(line)
def pin(p): p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)}
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
def gz(p,rs):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('wb')as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)as f:
   for r in rs:f.write((js(r)+'\n').encode())
def blocks(m):
 c=m.get('content',[])
 return [{'type':'text','text':c}] if isinstance(c,str)else c
def text(m):return '\n'.join(b.get('text','')for b in blocks(m)if isinstance(b,dict)and b.get('type')=='text')
def calls(m):return [b for b in blocks(m)if isinstance(b,dict)and b.get('type')=='toolCall']
def args(c):
 a=c.get('arguments',{})
 try:return json.loads(a)if isinstance(a,str)else a
 except ValueError:return {}
def preserve(ref):
 p=Path(ref['path']); status={'original':ref,'exact_readback':'MISSING'}
 if p.is_file():
  assert p.stat().st_size==ref['bytes']and digest(p)==ref['sha256'],'SOURCE_PIN_CHANGED'
  target=OUT/'objects'/ref['sha256'];target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():shutil.copyfile(p,target)
  assert digest(target)==ref['sha256']
  status.update({'exact_readback':'PASS','preserved':pin(target)})
 return status

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 assert not (OUT/'RECOVERY_RECEIPT.json').exists(),'PRESERVE_PREVIOUS_RUN'
 old=list(rows(OLD)); assert len(old)==8376
 wanted=[r for r in old if r['next51_mutually_exclusive_metadata_workload']=='unlinked_conditional_prefix_not_admitted']
 assert len(wanted)==7357
 current={r['canonical_owner_id']:r for r in rows(OVER)}
 holds=[r for r in current.values()if r['09_final_disposition']=='HOLD_SPECIFIC_CONTENT_OR_EVIDENCE_DEFECT']
 assert len(holds)==139
 eps={r['episode_id']for r in wanted+holds}; contexts={}; context_inputs=[]
 for name in ['audit_inputs/native1843.contexts.original.jsonl.gz','EXTRA_NATIVE_CONTEXTS.original.jsonl.gz']:
  p=CORPUS/name;context_inputs.append(pin(p))
  for c in rows(p):
   if c['episode_id']in eps:
    assert c['episode_id']not in contexts;contexts[c['episode_id']]=c
 assert set(contexts)==eps
 scopepath=MAIN/'clean_inputs/source_scope.metadata.jsonl.gz'
 scope={r['source_id']:r for r in rows(scopepath)}
 bindpath=ROOT/'output/20261021_workflow_skill_library/source_bindings.json';bindings=load(bindpath)
 evalp=ROOT/'benchmark/enterprise_input_closed_v11_20261012/contracts/evaluation.jsonl'
 fixed={json.loads(l)['session_id']for l in evalp.read_text(encoding='utf-8').splitlines()if l.strip()};assert len(fixed)==226
 hp=ROOT/'output/20261026_ablation_v2/holdout_registry.json';h12=set(re.findall('conv_[0-9a-f]{12}',js(load(hp))));assert len(h12)==12
 reservationp=ROOT/'output/20261031_wrd_curation09/holdout/holdout_reservation.json';reservation=load(reservationp)
 reserved=set(reservation['reserved_source_ids'])
 closurep=ROOT/'output/20261031_wrd_curation09/holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json';closure=load(closurep)
 revoked=set(closure['revoke_source_ids'])
 reserved_groups=set(reservation['reserved_source_scope_components']);revoked_groups=set(closure['revoke_source_scope_component_ids'])
 def status(s):
  if s in fixed:return 'ORIGINAL226_PROTECTED'
  if s in h12:return 'H12_PROTECTED'
  if s in revoked or scope.get(s,{}).get('component_id')in revoked_groups:return 'CONTENT_ALIAS_PROTECTED09'
  if s in reserved or scope.get(s,{}).get('component_id')in reserved_groups:return 'RESERVED_HOLDOUT09'
  return scope.get(s,{}).get('status','MISSING_CURRENT_SOURCE_SCOPE')
 # Whole original source identities are verified only where actually named.
 all_initial_ids=set();episode_metadata={};source_preservation={};owner_out=[]
 for eid,c in sorted(contexts.items()):
  users=[(i,m)for i,m in enumerate(c['messages'])if m.get('role')=='user']
  initial=text(users[0][1])if users else ''
  initial_ids=sorted(set(re.findall('conv_[0-9a-f]{12}',initial)))
  initial_assignments=sorted(set(re.findall(r'/workspace/inputs/(?:conversations|user_requests)/(conv_[0-9a-f]{12})',initial)))
  # IDs in an artifact-directory notice are not source-body delivery.
  all_initial_ids.update(initial_ids)
  read_events=[];literal_resource_paths=[]
  for i,m in enumerate(c['messages']):
   if m.get('role')!='assistant':continue
   for call in calls(m):
    a=args(call);path=a.get('path',a.get('file_path'))
    feedback=[{'message_index':j,'event_line':c.get('source_event_lines',[None]*len(c['messages']))[j],
      'isError':z.get('isError'),'tool_name':z.get('toolName'),'message_sha256_sorted':h(js(z,True)),
      'text_sha256':h(text(z)),'characters':len(text(z))}
      for j,z in enumerate(c['messages'][i+1:],i+1)if z.get('role')=='toolResult'and z.get('toolCallId')==call.get('id')]
    if call.get('name')=='read'and isinstance(path,str):
     ids=sorted(set(re.findall('conv_[0-9a-f]{12}',path)))
     row={'assistant_message_index':i,'call_id':call.get('id'),'tool':'read','path':path,'source_id_literals':ids,
       'named_source_statuses':{s:status(s)for s in ids},'actual_feedback':feedback,
       'full_original_file_delivery_not_inferred_from_path_or_exit':True}
     literal_resource_paths.append(row)
     if ids:read_events.append(row)
  ep={'episode_id':eid,'native_session_id':c.get('native_session_id'),'stage':c.get('stage'),'route':c.get('route_id'),
    'original_path':c.get('source_original_path'),'source_native':c['source_native'],
    'initial_user_message_index':users[0][0]if users else None,'initial_user_sha256':h(initial),
    'initial_user_source_id_literals':initial_ids,'initial_explicit_conversation_path_assignments':initial_assignments,
    'source_statuses':{s:status(s)for s in initial_ids},'actual_read_receipts':read_events,
    'all_literal_read_resource_paths':literal_resource_paths,'known_late_protected_observation_index':c.get('late_protected_observation_index'),
    'system_capture_status':c.get('system_capture_status'),'same_episode_API_capture_count':c.get('same_episode_API_capture_count',0),
    'original_source_ids_metadata_not_prefix_truth':c.get('old_episode_source_ids_metadata',[]),
    'this_is_identity_recovery_not_full_resource_ancestry_or_semantic_admission':True}
  episode_metadata[eid]=ep
 for sid in sorted(all_initial_ids|{s for r in wanted for s in r['source_ids']}):
  if sid not in bindings:continue
  binding=bindings[sid];ref=binding['conversation'];p=Path(ref['path'])
  assert p.is_file()and p.stat().st_size==ref['bytes']and digest(p)==ref['sha256']
  c=load(p)
  source_preservation[sid]={'source_id':sid,'current_status':status(sid),'binding_conversation_pin':ref,
   'binding_source_record_sha256':binding.get('source_record_sha256'),'binding_physical_line':binding.get('physical_line'),
   'original_split':c.get('split'),'leakage_component_id':c.get('leakage_component_id'),
   'native_reply_to_verified':c.get('native_reply_to_verified'),'historical_event_identity_verified':c.get('historical_event_identity_verified'),
   'user_input_source_literals':sorted(set(re.findall('conv_[0-9a-f]{12}',js([m for m in c.get('messages',[])if m.get('role')=='user'])))),
   'material_metadata':[{k:m.get(k)for k in ['relative_path','sha256','synthetic','historical_bytes_certified','eligible_real_input','available']}for m in binding.get('materials',[])],
   'new_TRAIN_assignment_created':False}
 # Every work item receives an explicit updated identity outcome, not a label.
 for oldrow in wanted:
  oid=oldrow['canonical_owner_id'];orig=current[oid];c=contexts[oldrow['episode_id']];ep=episode_metadata[c['episode_id']];i=oldrow['source_message_index'];m=c['messages'][i]
  assert h(js(m,True))==orig['original_message_sha256_sorted']
  assert h(js(m))==orig['original_message_sha256_insertion_order']
  assigned=ep['initial_explicit_conversation_path_assignments']
  # General literal IDs can be assignment hints, never body exposure proof.
  ids=sorted(set(oldrow['source_ids'])|set(assigned))
  if not ids:ids=ep['initial_user_source_id_literals']
  ss={s:status(s)for s in ids}
  observed=[r for r in ep['actual_read_receipts']if any(f['message_index']<i for f in r['actual_feedback'])]
  observed_bad=[r for r in observed if any(status(s)!='TRAIN'for s in r['source_id_literals'])]
  initial_bad={s:t for s,t in ss.items()if t!='TRAIN'}
  if oldrow['09_effective_queue']=='lineage63_method_equivalent_but_protected_producer_and_no_frozen_merge':verdict='ISOLATED_PREVIOUSLY_PROVEN_METHOD_PRODUCER'
  elif initial_bad:verdict='IDENTITY_RECOVERED_NONTRAIN_OR_MISSING_SCOPE_HOLD'
  elif observed_bad:verdict='NAMED_NONTRAIN_RESOURCE_READ_BEFORE_TARGET_ISOLATE_PENDING_EXACT_DELIVERY'
  elif ids and all(t=='TRAIN'for t in ss.values()):verdict='IDENTITY_RECOVERED_TRAIN_NAMED_SOURCES_ANCESTRY_CONTENT_STILL_REQUIRED'
  elif c.get('stage')=='evaluation':verdict='EVALUATION_ROLE_WITHOUT_SOURCE_ID_HOLD_NEEDS_ORIGINAL_TASK_MAPPING'
  elif c.get('stage') in {'technical','technical_native_child_capture_probe'}:verdict='PUBLIC_TECHNICAL_NOT_ENTERPRISE_PIPELINE_SAMPLE'
  else:verdict='NO_VERIFIABLE_SOURCE_ASSIGNMENT_AFTER_FIRST_TARGETED_PASS'
  owner_out.append({**oldrow,'identity10_disposition':verdict,'identity10_source_ids':ids,'identity10_source_statuses':ss,
   'identity10_assignment_basis':'ORIGINAL_OWNER_SOURCE_PLUS_INITIAL_EXPLICIT_PATH'if assigned else'ORIGINAL_OWNER_OR_INITIAL_USER_SOURCE_ID_LITERAL_HINT_ONLY',
   'identity10_original_target_sha256_sorted':h(js(m,True)),'identity10_observed_read_receipts_before_target':observed,
   'identity10_target_event_line':c.get('source_event_lines',[None]*len(c['messages']))[i],
   'identity10_source_identity_is_not_whole_prefix_admission':True,'identity10_positive_loss':0})
 # Save source-only metadata for all tasks; bodies only for named TRAIN sources.
 save(OUT/'EPISODE_IDENTITY_RECOVERED.metadata.json',{'episodes':list(episode_metadata.values()),'new_business_calls':0,'new_training_rows':0})
 save(OUT/'SOURCE_IDENTITIES_RECOVERED.metadata.json',{'sources':list(source_preservation.values()),'new_TRAIN_assignments':0})
 gz(OUT/'OWNER7357_IDENTITY_FIRST_PASS.metadata.jsonl.gz',owner_out)
 candidates=[];owner_by_ep=defaultdict(list)
 for r in owner_out:owner_by_ep[r['episode_id']].append(r)
 # Generation is review-priority, not a semantic acceptance filter.
 for eid,c in sorted(contexts.items()):
  ep=episode_metadata[eid]
  rr=[r for r in owner_by_ep[eid]if r['identity10_disposition']=='IDENTITY_RECOVERED_TRAIN_NAMED_SOURCES_ANCESTRY_CONTENT_STILL_REQUIRED']
  if c.get('stage')!='generation' or not rr:continue
  # Keep all original messages/feedback; reviewer must inspect actual resource ancestry.
  d=OUT/'generation_review'/eid;d.mkdir(parents=True,exist_ok=True)
  gz(d/'CONTEXT.original.audit.jsonl.gz',[c])
  native=preserve(c['source_native'])
  sourcepins=[]
  for sid in ep['initial_explicit_conversation_path_assignments'] or ep['initial_user_source_id_literals']:
   if status(sid)=='TRAIN'and sid in bindings:
    sourcepins.append(preserve(bindings[sid]['conversation']))
  targets=[]
  for r in rr:
   i=r['source_message_index'];m=c['messages'][i];ca=calls(m);callids={a.get('id')for a in ca}
   following=[]
   for j,z in enumerate(c['messages'][i+1:],i+1):
    if z.get('role')=='assistant':break
    if z.get('role')=='toolResult'and z.get('toolCallId')in callids:following.append({'message_index':j,'message':z,'sha256_sorted':h(js(z,True))})
   names=[a.get('name')for a in ca];writechars=sum(len(args(a).get('content',''))for a in ca if isinstance(args(a).get('content'),str))
   hasr=any(b.get('type')in {'thinking','reasoning'}for b in blocks(m)if isinstance(b,dict))
   targets.append({'owner_id':r['canonical_owner_id'],'source_message_index':i,'source_ids':r['identity10_source_ids'],
    'original_target_message':m,'original_target_sha256_sorted':h(js(m,True)),
    'state_before_target_end_exclusive':i,'immediate_actual_tool_feedback':following,'actual_tool_names':names,
    'write_content_characters':writechars,'original_native_R_present':hasr,
    'following_messages_for_grading_only_not_input':True,'positive_loss':0,'semantic_or_complete_prefix_ancestry_approved':False})
  gz(d/'TARGETS.with_original_feedback.audit.jsonl.gz',targets)
  save(d/'IDENTITY_AND_RESOURCE_METADATA.json',{'episode':ep,'native':native,'actual_source_entities':sourcepins,
    'status':'SOURCE_NAMED_TRAIN_FOR_FULL_CONTENT_AND_ANCESTRY_REVIEW_NOT_ADMISSION',
    'targets':len(targets),'new_training_rows':0,'do_not_infer_positive_from_original_completed_or_KEEP':True})
  candidates.append({'episode_id':eid,'source_ids':ep['initial_explicit_conversation_path_assignments']or ep['initial_user_source_id_literals'],
   'target_count':len(targets),'write_content_characters':sum(t['write_content_characters']for t in targets),
   'native_R_targets':sum(t['original_native_R_present']for t in targets),'original_context':pin(d/'CONTEXT.original.audit.jsonl.gz'),
   'targets_with_actual_feedback':pin(d/'TARGETS.with_original_feedback.audit.jsonl.gz'),'identity_and_resources':pin(d/'IDENTITY_AND_RESOURCE_METADATA.json')})
 save(OUT/'GENERATION_CONTENT_REVIEW_INDEX.json',{'status':'EXACT_ORIGINAL_CONTENT_FOR_REVIEW_NOT_NEW_TRAINING','episodes':candidates})
 report={'status':'PASS_EXACT_IDENTITY_FIRST_PASS_NOT_SEMANTIC_ADMISSION','owners':len(owner_out),'episodes':len(contexts),
  'dispositions':dict(Counter(r['identity10_disposition']for r in owner_out)),
  'historical_queue_dispositions':{q:dict(Counter(r['identity10_disposition']for r in owner_out if r['09_effective_queue']==q))for q in sorted({r['09_effective_queue']for r in owner_out})},
  'generation_content_packets':len(candidates),'generation_review_owner_targets':sum(c['target_count']for c in candidates),
  'original_targets_both_SHA_verified':True,'new_TRAIN_assignments':0,'new_positive_targets':0,'new_business_calls':0,'training_started':False,
  'inputs':[pin(p)for p in [OLD,OVER,scopepath,bindpath,evalp,hp,reservationp,closurep]]+context_inputs,'script_pin':pin(__file__)}
 save(OUT/'RECOVERY_RECEIPT.json',report)
 print(json.dumps({k:v for k,v in report.items()if k not in ['inputs','script_pin']},ensure_ascii=False))

if __name__=='__main__':main()
