"""Cross-check two explicitly identified original roots, no disk-wide crawl.

Recover missing native entities and exact startup resources for review only.
Neither native Agent sessions nor saved commands/programs are executed.
"""
from pathlib import Path
from collections import Counter,defaultdict
import importlib.util,json,re

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation10/identity'
s=importlib.util.spec_from_file_location('identity10roots',ROOT/'research/data_prep/wrd_curation10/identity_recover.py')
a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
ORIGINAL_ROOT=Path('E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/native_episodes')
REPAIRS=Path('E:/skillloop_runs/w4/native_episodes')

def parse_native(path):
 messages=[];lines=[];header=None;errors=[]
 for i,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
  try:r=json.loads(line)
  except ValueError:errors.append(i);continue
  if r.get('type')=='session'and header is None:header=r
  if r.get('type')=='message'and isinstance(r.get('message'),dict):messages.append(r['message']);lines.append(i)
 return header,messages,lines,errors

def main():
 assert not (OUT/'ORIGINAL_ROOT_DISCOVERY_QA.json').exists()
 baseline=list(a.rows(a.OVER));by_sid=defaultdict(list)
 for r in baseline:by_sid[r.get('native_session_id')].append(r)
 scope={r['source_id']:r for r in a.rows(a.MAIN/'clean_inputs/source_scope.metadata.jsonl.gz')}
 bindings=a.load(ROOT/'output/20261021_workflow_skill_library/source_bindings.json')
 fixed={json.loads(l)['session_id']for l in (ROOT/'benchmark/enterprise_input_closed_v11_20261012/contracts/evaluation.jsonl').read_text(encoding='utf-8').splitlines()if l.strip()}
 h12=set(re.findall('conv_[0-9a-f]{12}',a.js(a.load(ROOT/'output/20261026_ablation_v2/holdout_registry.json'))))
 oldres=a.load(ROOT/'output/20261031_wrd_curation09/holdout/holdout_reservation.json')
 rev=a.load(ROOT/'output/20261031_wrd_curation09/holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json')
 reserved=set(oldres['reserved_source_ids']);reserved_groups=set(oldres['reserved_source_scope_components'])
 newresp=ROOT/'output/20261031_wrd_curation10/parent_inputs/reservation.json';newres=a.load(newresp)
 newreserved=set(re.findall('conv_[0-9a-f]{12}',a.js(newres)));newgroups=set(re.findall('v10_group_[0-9a-f]{20}',a.js(newres)))
 def status(sid):
  if sid in fixed:return 'ORIGINAL226_PROTECTED'
  if sid in h12:return 'H12_PROTECTED'
  co=scope.get(sid,{}).get('component_id')
  if sid in rev['revoke_source_ids']or co in rev['revoke_source_scope_component_ids']:return 'CONTENT_ALIAS_PROTECTED09'
  if sid in reserved or co in reserved_groups:return 'RESERVED_HOLDOUT09'
  if sid in newreserved or co in newgroups:return 'RESERVED_PARENT_INPUT10'
  return scope.get(sid,{}).get('status','MISSING_CURRENT_SOURCE_SCOPE')
 dirs=sorted(d for d in ORIGINAL_ROOT.iterdir()if d.is_dir()and not d.is_symlink())
 dirs +=[REPAIRS/n for n in ['meeting-minutes-formatting__repair1','meeting-minutes-formatting__repair2']]
 inventory=[];newowners=[];contexts=[];review_index=[]
 for d in dirs:
  p=d/'openclaw_transport/session_events.jsonl'
  if not p.is_file():continue
  header,ms,lines,errors=parse_native(p);assert header and not errors
  sid=header['id'];old=by_sid.get(sid,[]);isnew=not old
  request=d/'request.json';req=a.load(request)if request.is_file()else{}
  planpath=d/'plan.json';plan=a.load(planpath)if planpath.is_file()else{}
  initial=a.text(next((m for m in ms if m.get('role')=='user'),{}))
  ids=set(re.findall(r'/workspace/inputs/(?:conversations|user_requests)/(conv_[0-9a-f]{12})',initial))
  for resource in req.get('resources',[]):
   if isinstance(resource,dict):
    mount=resource.get('mount','')
    if re.search(r'(?:^|/)(?:conversations|user_requests)/',mount):ids.update(re.findall('conv_[0-9a-f]{12}',mount))
  ids=sorted(ids)
  eid='native_recovered10_'+sid if isnew else old[0]['episode_id']
  native=a.pin(p);a.preserve(native)
  pin_index={str(Path(z['path'])):z for z in plan.get('input_and_skill_pins',[])if isinstance(z,dict)and isinstance(z.get('path'),str)}
  resource_rows=[]
  for resource in req.get('resources',[]):
   if not isinstance(resource,dict)or not isinstance(resource.get('path'),str):continue
   rp=Path(resource['path']);declared=pin_index.get(str(rp));found=rp.is_file()
   actual=a.pin(rp)if found else None
   exact=bool(found and declared and declared.get('sha256')==actual['sha256']and declared.get('bytes')==actual['bytes'])
   row={'native_mount':resource.get('mount'),'original_path':str(rp),'original_startup_pin':declared,'actual_pin_now':actual,
     'startup_current_bytes_match':exact,'recovered_file_is_not_independent_business_quality':True}
   if found and exact:row['preserved']=a.preserve(actual)['preserved']
   resource_rows.append(row)
  declared_ids=set(re.findall('conv_[0-9a-f]{12}',a.js(req)))
  read_rows=[]
  for i,m in enumerate(ms):
   if m.get('role')!='assistant':continue
   for call in a.calls(m):
    ar=a.args(call);path=ar.get('path',ar.get('file_path'))
    if call.get('name')!='read' or not isinstance(path,str):continue
    mount=path.removeprefix('/workspace/');found=next((r for r in resource_rows if r['native_mount']==mount),None)
    feedback=[{'message_index':j,'event_line':lines[j],'message_sha256_sorted':a.h(a.js(z,True)),
        'text_sha256':a.h(a.text(z)),'text_characters':len(a.text(z)),'isError':z.get('isError')}
      for j,z in enumerate(ms[i+1:],i+1)if z.get('role')=='toolResult'and z.get('toolCallId')==call.get('id')]
    read_rows.append({'assistant_message_index':i,'call_id':call.get('id'),'native_path':path,'original_startup_resource':found,
      'actual_original_tool_feedback':feedback,'exact_full_file_delivery_not_inferred':True})
  oldmax=max((r['source_message_index']for r in old),default=-1)
  known_old={(r['source_message_index'],r['original_message_sha256_sorted'])for r in old}
  existing_differences=[];tail=[]
  for i,m in enumerate(ms):
   if m.get('role')!='assistant':continue
   if i<=oldmax and(i,a.h(a.js(m,True)))not in known_old:existing_differences.append(i)
   if isnew or i>oldmax:
    oid=a.h(eid+':'+str(i))[:24]
    ca=a.calls(m);fb=[]
    for j,z in enumerate(ms[i+1:],i+1):
     if z.get('role')=='assistant':break
     if z.get('role')=='toolResult'and z.get('toolCallId')in {x.get('id')for x in ca}:fb.append({'message_index':j,'event_line':lines[j],'message':z,'sha256_sorted':a.h(a.js(z,True))})
    row={'canonical_owner_id':oid,'episode_id':eid,'native_session_id':sid,'source_message_index':i,'source_event_line':lines[i],
      'source_native':native,'original_message_sha256_sorted':a.h(a.js(m,True)),
      'source_ids':ids,'current_source_statuses':{s:status(s)for s in ids},
      'population':'NEW_ORIGINAL_NATIVE_ENTITY_RECOVERED10'if isnew else'PREVIOUS_SNAPSHOT_OMITTED_NATIVE_TAIL_RECOVERED10',
      'target_tool_names':[x.get('name')for x in ca],
      'native_readable_R_blocks':sum(b.get('type')in {'thinking','reasoning'}for b in a.blocks(m)if isinstance(b,dict)),
      'input_prefix_end_exclusive':i,'original_target_message':m,'immediate_actual_tool_feedback':fb,
      'original_target_identity_verified':True,'full_prefix_resource_ancestry_or_semantics_not_yet_admitted':True,
      'training_admitted':False,'positive_loss':0}
    newowners.append(row);tail.append(row)
  entry={'episode_id':eid,'native_session_id':sid,'original_directory':str(d),'native':native,
    'current34616_owner_count_same_native_session':len(old),'is_new_native_entity':isnew,
    'original_messages':len(ms),'original_assistant_messages':sum(m.get('role')=='assistant'for m in ms),
    'new_original_owner_count':len(tail),'old_owner_message_identity_mismatches':existing_differences,
    'request':a.pin(request)if request.is_file()else None,'stage':req.get('stage'),'task_id':req.get('task_id'),
    'source_ids_from_actual_initial_assignment':ids,'all_source_id_literals_in_request_not_delivery':sorted(declared_ids),
    'current_source_statuses':{s:status(s)for s in ids},
    'startup_resource_files':len(resource_rows),'startup_exact_current_files':sum(r['startup_current_bytes_match']for r in resource_rows),
    'resource_rows':resource_rows,'actual_read_events':read_rows,
    'execution_condition':{'image':plan.get('image_id'),'openclaw_version':plan.get('openclaw_version'),
      'declared_protocol':req.get('protocol'),'original_plan_pin_only_no_credential_content':a.pin(planpath)if planpath.is_file()else None},
    'resource_authorship_producer_not_inferred_from_source_ids':True,'training_admitted':False}
  inventory.append(entry)
  if isnew or d.parent==REPAIRS:
   co={'schema':'wrd10-recovered-original-native-context-not-admitted','episode_id':eid,'native_session_id':sid,
       'source_native':native,'source_original_path':str(p),'messages':ms,'source_event_lines':lines,
       'stage':req.get('stage'),'route_id':req.get('task_id'),'source_ids':ids,'source_statuses':entry['current_source_statuses'],
       'system_capture_status':'NOT_RECOVERED_BY_IDENTITY_SCRIPT','training_admitted':False,'positive_loss':0}
   contexts.append(co)
   packet=OUT/'recovered_native'/eid;packet.mkdir(parents=True,exist_ok=True)
   a.gz(packet/'CONTEXT.original.audit.jsonl.gz',[co]);a.gz(packet/'NEW_TARGETS.with_actual_feedback.audit.jsonl.gz',tail)
   a.save(packet/'RESOURCE_LINEAGE.metadata.json',entry)
   clean=bool(ids)and all(status(x)=='TRAIN'for x in ids)
   review_index.append({'episode_id':eid,'task_id':req.get('task_id'),'new_native_entity':isnew,'sources':ids,
       'source_statuses':entry['current_source_statuses'],'clean_named_sources_not_ancestry_clearance':clean,
       'new_owner_count':len(tail),'context':a.pin(packet/'CONTEXT.original.audit.jsonl.gz'),
       'new_targets':a.pin(packet/'NEW_TARGETS.with_actual_feedback.audit.jsonl.gz'),
       'resource_lineage':a.pin(packet/'RESOURCE_LINEAGE.metadata.json')})
 a.gz(OUT/'NEW_ORIGINAL_NATIVE_OWNERS.audit.jsonl.gz',newowners)
 a.gz(OUT/'NEW_ORIGINAL_NATIVE_CONTEXTS.audit.jsonl.gz',contexts)
 a.save(OUT/'ORIGINAL_ROOT_DISCOVERY.metadata.json',{'explicit_roots':[str(ORIGINAL_ROOT),str(REPAIRS)],'entries':inventory,
    'second_root_limited_to_exact_two_repair_directories':True,'no_workspace_or_disk_wide_scan':True})
 a.save(OUT/'RECOVERED_NATIVE_REVIEW_INDEX.json',{'entries':review_index,'training_admitted':0,'new_business_calls':0})
 qa={'status':'PASS_EXPLICIT_ORIGINAL_ROOT_NATIVE_IDENTITY_RECOVERY_NOT_ADMISSION','same_root_original_exports':len(dirs)-2,
     'original_exports_including_two_repairs':len(inventory),'new_native_entities':sum(r['is_new_native_entity']for r in inventory),
     'new_original_owner_rows':len(newowners),'new_owner_from_new_native':sum(r['population']=='NEW_ORIGINAL_NATIVE_ENTITY_RECOVERED10'for r in newowners),
     'additional_tail_owners_on_old_native':sum(r['population']=='PREVIOUS_SNAPSHOT_OMITTED_NATIVE_TAIL_RECOVERED10'for r in newowners),
     'old_owner_message_mismatches':sum(len(r['old_owner_message_identity_mismatches'])for r in inventory),
     'new_native_named_clean_source_entries':sum(r['new_native_entity']and r['clean_named_sources_not_ancestry_clearance']for r in review_index),
     'current09_manifest_unchanged':a.digest(a.MAIN/'TRAINING_MANIFEST.json')=='01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42',
     'new_parent_reservation_pin':a.pin(newresp),'new_training_targets':0,'new_TRAIN_source_assignments':0,
     'new_business_calls':0,'weights_loaded':False,'training_started':False,'script_pin':a.pin(__file__)}
 assert qa['old_owner_message_mismatches']==0
 a.save(OUT/'ORIGINAL_ROOT_DISCOVERY_QA.json',qa)
 print(a.js(qa));print(a.js({'new_review_entries':[{k:v for k,v in r.items()if k not in {'context','new_targets','resource_lineage'}}for r in review_index]}))

if __name__=='__main__':main()
