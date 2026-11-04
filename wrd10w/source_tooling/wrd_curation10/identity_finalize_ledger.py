"""Second bounded path/index lookup and final 7357 work-item identity overlay.

No semantic labels or positive loss are assigned. New root-native entities
are accounted separately from old owner reclassification.
"""
from pathlib import Path
from collections import Counter,defaultdict
import importlib.util,json,re

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation10/identity'
s=importlib.util.spec_from_file_location('identity10final',ROOT/'research/data_prep/wrd_curation10/identity_recover.py')
a=importlib.util.module_from_spec(s);s.loader.exec_module(a)

def scalar_source_ids(value):
 result=set()
 if isinstance(value,dict):
  for k,v in value.items():
   if k.lower()in {'source_id','source_ids','session_id','source_session_id','source_session_ids','conversation_id','conversation_ids'}:
    result.update(re.findall(r'conv_[0-9a-f]{12}',a.js(v)))
   if isinstance(v,(dict,list)):result.update(scalar_source_ids(v))
 elif isinstance(value,list):
  for v in value:
   if isinstance(v,(dict,list)):result.update(scalar_source_ids(v))
 return result

def main():
 assert not (OUT/'FINAL_IDENTITY_QA.json').exists()
 first=list(a.rows(OUT/'OWNER7357_IDENTITY_FIRST_PASS.metadata.jsonl.gz'));assert len(first)==7357
 epmeta={e['episode_id']:e for e in a.load(OUT/'EPISODE_IDENTITY_RECOVERED.metadata.json')['episodes']}
 current={r['canonical_owner_id']:r for r in a.rows(a.OVER)}
 scope={r['source_id']:r for r in a.rows(a.MAIN/'clean_inputs/source_scope.metadata.jsonl.gz')}
 fixed={json.loads(l)['session_id']for l in (ROOT/'benchmark/enterprise_input_closed_v11_20261012/contracts/evaluation.jsonl').read_text(encoding='utf-8').splitlines()if l.strip()}
 h12=set(re.findall('conv_[0-9a-f]{12}',a.js(a.load(ROOT/'output/20261026_ablation_v2/holdout_registry.json'))))
 old=a.load(ROOT/'output/20261031_wrd_curation09/holdout/holdout_reservation.json')
 rev=a.load(ROOT/'output/20261031_wrd_curation09/holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json')
 newp=ROOT/'output/20261031_wrd_curation10/parent_inputs/reservation.json';new=a.load(newp)
 reserved=set(old['reserved_source_ids']);reserved_groups=set(old['reserved_source_scope_components'])
 newids=set(re.findall('conv_[0-9a-f]{12}',a.js(new)));newgroups=set(re.findall('v10_group_[0-9a-f]{20}',a.js(new)))
 def status(sid):
  if sid in fixed:return 'ORIGINAL226_PROTECTED'
  if sid in h12:return 'H12_PROTECTED'
  co=scope.get(sid,{}).get('component_id')
  if sid in rev['revoke_source_ids']or co in rev['revoke_source_scope_component_ids']:return 'CONTENT_ALIAS_PROTECTED09'
  if sid in newids or co in newgroups:return 'RESERVED_PARENT_INPUT10'
  if sid in reserved or co in reserved_groups:return 'RESERVED_HOLDOUT09'
  return scope.get(sid,{}).get('status','MISSING_CURRENT_SOURCE_SCOPE')
 # Round two is limited to each recorded native's exact request/capture parent
 # and exact startup JSON resource paths. No recursive filesystem search.
 unknown_eps={r['episode_id']for r in first if not r['identity10_source_ids']}
 lookups={}
 for eid in sorted(unknown_eps):
  e=epmeta[eid];native=Path(e['original_path']or e['source_native']['path']);paths=[native.parent.parent/'request.json']
  capture=native.parent.parent/'capture.json'
  if capture.is_file():
   cd=a.load(capture);sp=cd.get('source_pin',{}).get('path')
   if isinstance(sp,str):paths.append(Path(sp).parent.parent/'request.json')
  trace=[];ids=set()
  for reqp in dict.fromkeys(paths):
   trace.append({'attempted_path':str(reqp),'exists':reqp.is_file(),'purpose':'EXACT_RECORDED_NATIVE_REQUEST_PARENT'})
   if not reqp.is_file():continue
   req=a.load(reqp);trace[-1]['pin']=a.pin(reqp)
   ids.update(scalar_source_ids(req))
   for ref in req.get('resources',[]):
    if not isinstance(ref,dict):continue
    mount=ref.get('mount','');rp=Path(ref.get('path',''))
    if not isinstance(mount,str):continue
    explicit=set(re.findall(r'(?:conversations|user_requests)/(conv_[0-9a-f]{12})',mount.replace('\\','/')))
    ids.update(explicit)
    # Parse only actual startup identity containers; never grading payloads,
    # full business feedback, model config, credentials or arbitrary files.
    basename=Path(mount).name.casefold()
    if rp.is_file()and basename in {'task.json','case.json','conversation.json','source_bindings.json','task_sources.json','original_task.json'}:
     rd=a.load(rp);refs=scalar_source_ids(rd);ids.update(refs)
     trace.append({'path':str(rp),'pin':a.pin(rp),'native_mount':mount,'actual_source_field_ids':sorted(refs),
        'role':'STARTUP_IDENTITY_ONLY_NOT_ACTUAL_BODY_DELIVERY'})
  lookups[eid]={'episode_id':eid,'exact_path_attempts':trace,'startup_source_field_ids':sorted(ids),'second_targeted_pass_completed':True}
 # Reconcile old actual-read graph by event boundary, keeping its unknowns.
 rs_path=ROOT/'output/20261026_wrd_dataset_v9/outcomes/recomputed_scope_overlay/resource_scope.jsonl.gz'
 resource=defaultdict(list)
 for r in a.rows(rs_path):
  if r['episode_id']in epmeta:resource[r['episode_id']].append(r)
 final=[]
 for r in first:
  eid=r['episode_id'];i=r['source_message_index'];ids=sorted(set(r['identity10_source_ids'])|set(lookups.get(eid,{}).get('startup_source_field_ids',[])))
  statuses={sid:status(sid)for sid in ids};prior=[x for x in resource[eid]if x['observed_after_assistant_message_index']<i]
  unknown=[x for x in prior if x.get('unknown_reasons')]
  # Do not turn a source-ID mention in a tool result into proof of private
  # body exposure. The existing resource scope evidence is retained as-is.
  prior_bad=[x for x in prior if x.get('protected_source_ids')or any(status(z)!='TRAIN'for z in x.get('source_ids',[]))]
  if r['09_effective_queue']=='lineage63_method_equivalent_but_protected_producer_and_no_frozen_merge':verdict='ISOLATED_PREVIOUSLY_PROVEN_METHOD_PRODUCER'
  elif any(s=='RESERVED_PARENT_INPUT10'for s in statuses.values()):verdict='ISOLATED_NEW_PARENT_HOLDOUT10'
  elif any(s!='TRAIN'for s in statuses.values()):verdict='NAMED_NONTRAIN_OR_MISSING_SOURCE_SCOPE_HOLD'
  elif ids and not unknown and not prior_bad:verdict='SOURCE_IDENTITY_RECOVERED_WITH_KNOWN_GRAPH_CLEAR_PENDING_ACTUAL_RESOURCE_AND_CONTENT_REVIEW'
  elif ids:verdict='SOURCE_IDENTITY_RECOVERED_PRIOR_RESOURCE_ANCESTRY_STILL_HOLD'
  elif epmeta[eid].get('stage')in {'technical','technical_native_child_capture_probe'}:verdict='PUBLIC_TECHNICAL_NOT_ENTERPRISE_PIPELINE_SAMPLE'
  else:verdict='SOURCE_IDENTITY_UNRESOLVED_AFTER_TWO_BOUNDED_LOOKUPS'
  row={**r,'identity10_final_source_ids':ids,'identity10_final_source_statuses':statuses,'identity10_final_disposition':verdict,
    'identity10_second_path_lookup':lookups.get(eid),
    'identity10_prior_original_resource_rows':len(prior),'identity10_prior_unknown_reason_counts':dict(Counter(z for x in unknown for z in x['unknown_reasons'])),
    'identity10_prior_resource_graph_unknowns':[{'node_id':x['node_id'],'native_path':x['native_path'],
       'observed_after_assistant_message_index':x['observed_after_assistant_message_index'],'file_identity':x['file_identity'],
       'source_ids':x['source_ids'],'protected_source_ids':x['protected_source_ids'],'unknown_reasons':x['unknown_reasons'],
       'scope_proof_id':x['scope_proof_id']}for x in unknown],
    'identity10_known_graph_clear_does_not_prove_unrecorded_ancestry_or_semantic_quality':True,
    'identity10_training_admitted':False,'identity10_positive_loss':0}
  final.append(row)
 a.gz(OUT/'OWNER7357_IDENTITY_FINAL.metadata.jsonl.gz',final)
 a.save(OUT/'SECOND_BOUNDED_LOOKUPS.metadata.json',{'lookups':list(lookups.values()),
    'new_parent_reservation':a.pin(newp),'only_known_native_parent_or_explicit_startup_identity_files_read':True})
 # Reopening old specific semantic HOLD requires a genuinely new intersecting
 # native/resource version, not a second spelling of its existing evidence.
 holds=[x for x in current.values()if x['09_final_disposition']=='HOLD_SPECIFIC_CONTENT_OR_EVIDENCE_DEFECT']
 discovery=a.load(OUT/'ORIGINAL_ROOT_DISCOVERY.metadata.json')['entries']
 newnative={x['native_session_id']for x in discovery if x['is_new_native_entity']}
 a.gz(OUT/'PREVIOUS139_SPECIFIC_HOLD_STATUS.metadata.jsonl.gz',[
   {'owner_id':x['canonical_owner_id'],'episode_id':x['episode_id'],'source_ids':x['source_ids'],
    'prior_disposition':x['09_final_disposition'],'previous_specific_note':x.get('09_final_note'),
    'new_source_native_entity_same_session_found':x.get('native_session_id')in newnative,
    'reopened_for_positive_loss':False,'reason':'No new exact evidence for this previously reviewed owner established by this identity recovery; preserved HOLD.'}
   for x in holds])
 qr=a.load(OUT/'ORIGINAL_ROOT_DISCOVERY_QA.json')
 graph_groups=defaultdict(set)
 for r in final:
  for p in r['identity10_prior_resource_graph_unknowns']:
   fid=p.get('file_identity')or{};key=(p['native_path'],fid.get('sha256'))
   graph_groups[key].add(r['canonical_owner_id'])
 group_rows=[{'native_path':k[0],'exact_sha256_if_known':k[1],'affected_owner_count':len(v),'owner_ids':sorted(v),
    'this_is_shared_dependency_workload_not_independent_sample_count':True}for k,v in sorted(graph_groups.items(),key=lambda kv:(-len(kv[1]),str(kv[0])))]
 a.save(OUT/'SHARED_RESOURCE_ANCESTRY_WORKLOAD.metadata.json',{'groups':group_rows,'resource_scope_pin':a.pin(rs_path)})
 qa={'status':'PASS_7357_FINAL_IDENTITY_LEDGER_AND_SEPARATE_NEW_NATIVE_CORPUS_NO_ADMISSION',
   'old_conditional_owner_rows':len(final),'unique_old_owner_rows':len({x['canonical_owner_id']for x in final}),
   'final_dispositions':dict(Counter(x['identity10_final_disposition']for x in final)),
   'new_named_source_identity_owners_after_second_pass':sum(set(r['identity10_final_source_ids'])!=set(r['identity10_source_ids'])for r in final),
   'second_pass_episodes':len(lookups),'original_root_new_native_entities':qr['new_native_entities'],
   'original_root_new_assistant_owners':qr['new_original_owner_rows'],'new_owner_not_counted_as_7357_reclassification':True,
   'old139_specific_HOLD_rows_preserved':len(holds),'old139_reopened_for_loss':0,
   'new_parent_reserved_ids':sorted(newids),'new_parent_reserved_scope_components':sorted(newgroups),
   'new_training_targets':0,'new_TRAIN_source_assignments':0,'new_business_calls':0,'weights_loaded':False,'training_started':False,
   'current09_manifest_unchanged':a.digest(a.MAIN/'TRAINING_MANIFEST.json')=='01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42',
   'inputs':[a.pin(OUT/'OWNER7357_IDENTITY_FIRST_PASS.metadata.jsonl.gz'),a.pin(rs_path),a.pin(newp)],'script_pin':a.pin(__file__)}
 assert len(final)==len({r['canonical_owner_id']for r in final})==7357
 a.save(OUT/'FINAL_IDENTITY_QA.json',qa)
 print(a.js(qa))

if __name__=='__main__':main()
