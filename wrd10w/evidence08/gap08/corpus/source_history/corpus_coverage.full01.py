"""Offline corpus-owner reconciliation and preserved actor code evidence. No Agent loop."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,ast,gzip,hashlib,json,shutil
R=Path('D:/skillloop');O=R/'output/20261030_wrd_gap08/corpus';V9=R/'output/20261026_wrd_dataset_v9';M=R/'output/20261027_wrd_main_v10'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bh(b):return hashlib.sha256(b).hexdigest()
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def can(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def rows(p):
 op=gzip.open if str(p).endswith('.gz') else open
 with op(p,'rt',encoding='utf-8-sig') as f:
  for s in f:
   if s.strip():yield json.loads(s)
def pin(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def save(p,v):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def gzwrite(p,rs):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('wb') as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as g:
   for x in rs:g.write((js(x)+'\n').encode())
def tid(e,i):return bh((e+':'+str(i)).encode())[:24]
def calls(m):return [x for x in m.get('content',[]) if isinstance(x,dict) and x.get('type')=='toolCall'] if isinstance(m.get('content'),list) else []
def args(c):a=c.get('arguments',{});return json.loads(a) if isinstance(a,str) else a
def active_rows():
 man=json.loads((M/'TRAINING_MANIFEST.json').read_text(encoding='utf-8'))
 for f in man['actual_train_files']:
  p=M/f['path'];assert sha(p)==f['sha256']
  for row in rows(p):yield f,row
def first6():
 out=O/'first6';out.mkdir(parents=True,exist_ok=True);(out/'objects').mkdir(exist_ok=True)
 chosen={'ep_4aadd96d99f2c07543c7','ep_2493f463fdf84d1ba740','ep_42d23f25933caada98b1','ep_530653bde445b02636f4','ep_13db0415403c12c60e2b','ep_4d412dca2c57480536e7'}
 scopes={x['source_id']:x for x in rows(M/'clean_inputs/source_scope.metadata.jsonl.gz')}
 labelpath=V9/'outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz';labels={x['id']:x for x in rows(labelpath) if x['episode_id'] in chosen}
 resourcepath=V9/'outcomes/recomputed_scope_overlay/resource_scope.jsonl.gz';resources=defaultdict(list)
 for x in rows(resourcepath):
  if x['episode_id'] in chosen:resources[x['episode_id']].append(x)
 contexts={x['episode_id']:x for x in rows(V9/'recovery/episodes.contexts.jsonl.gz') if x['episode_id'] in chosen}
 positives=set()
 for f,row in active_rows():
  meta=row.get('original_record_metadata',{});owner=meta.get('target_owner') or {}
  for key in ['canonical_original_target_id','original_tool_call_id','canonical_original_action_owner_id']:
   if isinstance(owner.get(key),str):positives.add(owner[key]);positives.add(owner[key].split(':')[-1])
  for t in row.get('targets',[]):
   if t.get('supervised_tokens',0):
    for c in row['messages'][t['message_index']].get('tool_calls',[]):positives.add(c['id'])
 indexpath=R/'output/20261026_wrd_raw_census_v7/indexes/episode_files.all.jsonl.gz';fi=defaultdict(list)
 for x in rows(indexpath):
  if x['episode_id'] in chosen:fi[x['episode_id']].append(x)
 def copy(p,s):
  p=Path(p);assert p.is_file() and sha(p)==s
  q=out/'objects'/s
  if not q.exists():shutil.copyfile(p,q)
  return pin(q)
 groups=[]
 for eid in sorted(chosen):
  ep=contexts[eid];ms=ep['messages'];epsource=ep['source_native'];copy(epsource['path'],epsource['sha256'])
  groupdir=out/eid;groupdir.mkdir(exist_ok=True);selected=[];all_source_ids=set();extra_refs=[]
  for i,m in enumerate(ms):
   t=labels.get(tid(eid,i))
   if not t or t['source_admission']!='ADMIT' or not t['source_ids'] or not all(scopes.get(s,{}).get('status')=='TRAIN' for s in t['source_ids']):continue
   for c in calls(m):
    a=args(c);path=a.get('path',a.get('file_path'));code=a.get('content','')
    if c.get('name')!='write' or not isinstance(path,str) or Path(path).suffix.lower() not in ['.py','.js','.html','.css','.sh','.ts','.tsx'] or len(code)<300:continue
    if c['id'] in positives or t['id'] in positives:continue
    feedback=[{'message_index':j,'event_line':ep['source_event_lines'][j],'message':q} for j,q in enumerate(ms) if q.get('toolCallId')==c['id']]
    prior=[r for r in resources[eid] if r['observed_after_assistant_message_index']<i]
    prior_issues=[r for r in prior if r['unknown_reasons'] or r['protected_source_ids'] or any(scopes.get(s,{}).get('status')!='TRAIN' for s in r['source_ids'])]
    # Native full prefix is retained. Do not claim an old generic graph detects
    # every calculated path; store exact commands for independent read audit.
    static_prior_calls=[{'index':j,'call':q} for j,nm in enumerate(ms[:i]) for q in calls(nm)]
    reads_skill_before=any('SKILL.md' in js(z['call']) or '/workspace/inputs/previous_skill/' in js(z['call']) for z in static_prior_calls)
    syntax='NOT_PYTHON'
    if path.endswith('.py'):
     try:ast.parse(code);syntax='PYTHON_AST_PARSE_PASS_NOT_SEMANTIC_PASS'
     except SyntaxError as e:syntax='PYTHON_SYNTAX_ERROR:'+str(e)
    cp=groupdir/(t['id']+Path(path).suffix);cp.write_bytes(code.encode())
    selected.append({'original_target_id':t['id'],'message_index':i,'event_line':ep['source_event_lines'][i],'tool_call_id':c['id'],'native_path':path,
      'original_message':m,'original_code_file':pin(cp),'original_code_characters':len(code),'actual_feedback':feedback,
      'scope_at_exact_target':t,'all_current_source_statuses':{s:scopes[s]['status'] for s in t['source_ids']},
      'observed_prior_resource_records':prior,'prior_graph_issues':prior_issues,'actual_prior_calls':static_prior_calls,
      'actual_prior_call_mentions_skill_or_previous_skill':reads_skill_before,
      'scope_claim':'EXISTING_V9_PREFIX_SCOPE_PLUS_CURRENT_SOURCE_SCOPE_AND_SAVED_ACTUAL_PRIOR_CALLS_PENDING_INDEPENDENT_OMISSION_CHECK',
      'syntax_only':syntax,'original_tool_result_is_error':[f['message'].get('isError') for f in feedback],
      'semantic_quality_admitted':False,'positive_loss':0,'no_main_owner_or_tool_ID_collision':True})
    all_source_ids.update(t['source_ids'])
  frozen=[]
  for ref in fi[eid]:
   rel=ref['logical_path'].split('/workspace/',1)[-1]
   if '/workspace/' not in ref['logical_path'] or not (rel.startswith('inputs/') or rel.startswith('outputs/')):continue
   p=Path(ref['physical_frozen_CAS_path'])
   if p.is_file() and sha(p)==ref['stored_sha256']:
    frozen.append({'record':ref,'actual_copied_object':copy(p,ref['stored_sha256']),'role':'ORIGINAL_INPUT_OR_FINAL_OUTPUT_AUDIT_NOT_PRIOR_VERSION_SUBSTITUTE'})
  gzwrite(groupdir/'CONTEXT.original.jsonl.gz',[ep]);gzwrite(groupdir/'TARGETS.with_actual_feedback.jsonl.gz',selected)
  save(groupdir/'SCOPE_AND_RESOURCES.json',{'episode_id':eid,'route':ep['route_id'],'role':'ACTOR_EXECUTION_AUXILIARY_NOT_PIPELINE_CONTROLLER','source_ids':sorted(all_source_ids),
   'source_current_statuses':{s:scopes[s]['status'] for s in all_source_ids},'source_scope_pin':pin(M/'clean_inputs/source_scope.metadata.jsonl.gz'),
   'original_native':epsource,'original_system_status':ep['system_capture_status'],'original_tool_schema_provenance':ep['tool_schema_provenance'],
   'source_outcome_ledger_pin':pin(labelpath),'resource_scope_pin':pin(resourcepath),'resource_records':resources[eid],'frozen_input_final_output_objects':frozen,
   'failures_in_full_original_context_preserved_positive_loss0':True,'future_results_only_for_audit_credit_not_past_input':True,'semantic_admission_pending_root':True})
  groups.append({'episode_id':eid,'route':ep['route_id'],'sources':sorted(all_source_ids),'program_targets':len(selected),'program_chars':sum(x['original_code_characters'] for x in selected),
   'target_ids':[x['original_target_id'] for x in selected],'original_native':epsource,'actual_files':[pin(groupdir/n) for n in ['CONTEXT.original.jsonl.gz','TARGETS.with_actual_feedback.jsonl.gz','SCOPE_AND_RESOURCES.json']],
   'scope_graph_issue_target_count':sum(bool(x['prior_graph_issues']) for x in selected),'actual_prior_skill_read_mentions':sum(x['actual_prior_call_mentions_skill_or_previous_skill'] for x in selected),
   'copied_input_final_output_references':len(frozen),'not_semantic_or_full_skill_gold':True})
 save(out/'FIRST6_ACTUAL_GROUPS.json',{'status':'ACTUAL_ORIGINAL_CODE_AND_CONTEXT_FOR_ROOT_SEMANTIC_REVIEW_NOT_TRAINING_ADMISSION','groups':groups,'total_program_targets':sum(x['program_targets'] for x in groups),
   'script':pin(__file__),'main_manifest_unchanged':pin(M/'TRAINING_MANIFEST.json'),'no_old_commands_Agent_or_training_executed':True})
 print(js({'groups':6,'program_targets':sum(x['program_targets'] for x in groups),'scope_issues':sum(x['scope_graph_issue_target_count'] for x in groups),'out':str(out)}))
def parse_native(path):
 messages=[];lines=[];sid=None;errors=[]
 for ln,s in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(),1):
  try:e=json.loads(s)
  except ValueError:errors.append(ln);continue
  if e.get('type')=='session' and sid is None:sid=e.get('id')
  if e.get('type')=='message' and isinstance(e.get('message'),dict):messages.append(e['message']);lines.append(ln)
 return sid,messages,lines,errors

def parse_wire(path):
 text=Path(path).read_text(encoding='utf-8-sig');frames=[];errors=[];done=False
 for ln,s in enumerate(text.splitlines(),1):
  if not s.startswith('data:'):continue
  s=s[5:].strip()
  if s=='[DONE]':done=True;continue
  try:frames.append(json.loads(s))
  except ValueError:errors.append(ln)
 if not frames:
  try:frames=[json.loads(text)]
  except ValueError:pass
 rid=None;reasoning=[];content=[];tc={};finish=None
 for f in frames:
  rid=rid or f.get('id')
  for choice in f.get('choices',[]):
   finish=choice.get('finish_reason') or finish;d=choice.get('delta',choice.get('message',{}))
   for field,dest in [('reasoning_content',reasoning),('content',content)]:
    if isinstance(d.get(field),str):dest.append(d[field])
   for c in d.get('tool_calls',[]):
    j=c.get('index',0);a=tc.setdefault(j,{'id':'','name':'','arguments':''});fn=c.get('function',{})
    if c.get('id'):a['id']=c['id']
    if fn.get('name'):a['name']+=fn['name']
    if isinstance(fn.get('arguments'),str):a['arguments']+=fn['arguments']
 return {'response_id':rid,'reasoning_content':''.join(reasoning),'content':''.join(content),'tool_calls':list(tc.values()),'finish_reason':finish,'DONE':done,'json_errors':errors,'frames':len(frames)}

def full():
 O.mkdir(parents=True,exist_ok=True);audit=O/'audit_inputs';audit.mkdir(exist_ok=True)
 mf=M/'TRAINING_MANIFEST.json';baseline=mf.read_bytes();man=json.loads(baseline);assert man['actual_counts']['targets']==552
 save(O/'BASELINE_MANIFEST_552.json',man)
 inputs=[]
 def source(p):
  p=Path(p);d=pin(p);inputs.append(d);return d
 labelpath=V9/'outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz';source(labelpath)
 labels={x['id']:x for x in rows(labelpath)};assert len(labels)==32342
 eligpath=R/'output/20261025_wrd_training_preflight/prepared_gated/public/audit/eligibility.jsonl.gz';source(eligpath)
 elig={x['id']:x for x in rows(eligpath)};assert len(elig)==7117 and set(elig)<=set(labels)
 processpath=V9/'processed/targets.processing.jsonl.gz';source(processpath)
 processed={x['id']:x for x in rows(processpath)}
 scopespath=M/'clean_inputs/source_scope.metadata.jsonl.gz';source(scopespath);scopes={x['source_id']:x for x in rows(scopespath)}
 old81path=R/'output/20261029_wrd_v9_missing_evidence_update02/ANCESTRY_CORRECTION_OVERLAY.json';source(old81path)
 protected_overlay={x['id']:x for x in json.loads(old81path.read_text(encoding='utf-8'))['target_overlays']}
 overlaypath=R/'output/20261029_wrd_batch24/FINAL969_TARGET_OVERLAY.jsonl.gz';source(overlaypath)
 overlay={x['id']:x for x in rows(overlaypath)}
 for k,v in overlay.items():
  if v['original_classification']=='PROTECTED_ANCESTOR':protected_overlay[k]=v
 assert len(protected_overlay)==854
 direct405path=R/'output/20261029_wrd_maker405_recovery/TARGET_SCAN_405.jsonl.gz';source(direct405path)
 direct405={x.get('id',x.get('target_id')):x for x in rows(direct405path)}
 fixed226={s for x in labels.values() for s in x['original226']};h12={s for x in labels.values() for s in x['holdout12']};assert len(fixed226)==226 and len(h12)==12
 outerpath=R/'output/20261030_wrd_gap08/reasoning/OUTER100_RESPONSE_IDENTITY.metadata.jsonl.gz';outer={}
 if outerpath.exists():source(outerpath);outer={x['id']:x for x in rows(outerpath)}
 # Preserve exact original capture bodies once. Each ledger row points to its
 # context/message, rather than silently converting new states into natives.
 ctxpath=V9/'recovery/episodes.contexts.jsonl.gz';source(ctxpath)
 shutil.copyfile(ctxpath,audit/'native1843.contexts.original.jsonl.gz')
 providerpath=V9/'recovery/provider_pairs.original.jsonl.gz';source(providerpath)
 shutil.copyfile(providerpath,audit/'provider1536.pairs.original.jsonl.gz')
 allowners={};toolmap=defaultdict(set);ridmap=defaultdict(set);episode_info=[];programs=[];contexts_extra=[];capture_conflicts=[]
 def accept_episode(ep,pop):
  eid=ep['episode_id'];ms=ep['messages'];sourcepin=ep['source_native'];lines=ep.get('source_event_lines',[None]*len(ms));sid=ep.get('native_session_id')
  episode_info.append({'episode_id':eid,'native_session_id':sid,'population':pop,'source_native':sourcepin,'source_original_path':ep.get('source_original_path'),
   'stage':ep.get('stage'),'route_id':ep.get('route_id'),'system_capture_status':ep.get('system_capture_status','NOT_RECOVERED_HERE'),
   'messages':len(ms),'assistant_positions':sum(m.get('role')=='assistant' for m in ms),'raw_context_file':'audit_inputs/native1843.contexts.original.jsonl.gz' if pop.startswith('V9') else 'EXTRA_NATIVE_CONTEXTS.original.jsonl.gz'})
  for i,m in enumerate(ms):
   if m.get('role')!='assistant':continue
   oid=tid(eid,i);old=labels.get(oid);sids=(old or {}).get('source_ids',[]);statusmap={s:'ORIGINAL226_PROTECTED' if s in fixed226 else 'H12_PROTECTED' if s in h12 else scopes.get(s,{}).get('status','MISSING_CURRENT_SOURCE_SCOPE') for s in sids}
   scope='UNKNOWN_SUPPLEMENTAL_PREFIX_NOT_AUDITED'
   if old:
    if old['source_admission']=='HOLD_PROTECTED' or oid in protected_overlay:scope='ISOLATED_PROTECTED_ANCESTOR'
    elif any(v!='TRAIN' for v in statusmap.values()):scope='ISOLATED_CURRENT_SOURCE_OR_STATIC_BOUNDARY' if any(v.startswith('HOLD_') or v.endswith('_PROTECTED') for v in statusmap.values()) else 'HOLD_CURRENT_SOURCE_IDENTITY_MISSING'
    elif old['source_admission']=='HOLD_MISSING_EVIDENCE':scope='HOLD_ANCESTRY_UNRESOLVED'
    elif old['source_admission']=='ADMIT':scope='SCOPE_CLOSED_SEMANTIC_PENDING' if sids else 'PROTOCOL_PREFIX_NO_BUSINESS_SOURCE'
   if ep.get('late_protected_observation_index') is not None and i>ep['late_protected_observation_index']:scope='ISOLATED_PROTECTED_ANCESTOR'
   r={'canonical_owner_id':oid,'population':pop,'episode_id':eid,'native_session_id':sid,'source_message_index':i,'source_event_line':lines[i],
    'original_message_sha256_sorted':bh(can(m).encode()),'original_message_sha256_insertion_order':bh(js(m).encode()),'original_content_sha256_sorted':bh(can(m.get('content')).encode()),
    'source_native':sourcepin,'original_body_ref':{'context_episode_id':eid,'message_index':i,'context_file':'audit_inputs/native1843.contexts.original.jsonl.gz' if pop.startswith('V9') else 'EXTRA_NATIVE_CONTEXTS.original.jsonl.gz'},
    'historical_role':(old or {}).get('stage',ep.get('stage')),'route_id':(old or {}).get('route_id',ep.get('route_id')),'source_ids':sids,'current_source_statuses':statusmap,
    'source_disposition':scope,'old_source_admission':(old or {}).get('source_admission'),'old_source_scope_proof_id':(old or {}).get('scope_proof_id'),'late_protected_overlay':protected_overlay.get(oid),
    'old_preflight_eligibility':elig.get(oid),'v9_protocol_disposition':{k:v for k,v in processed.get(oid,{}).items() if k not in ['scope_and_outcome_label']},
    'maker405_static_byte_review':None if oid not in direct405 else {'review_file':str(direct405path),'quality_positive_admission':False},
    'original_system_capture_status':ep.get('system_capture_status','NOT_RECOVERED_HERE'),'target_call_ids':[c.get('id') for c in calls(m)],
    'native_response_id':m.get('responseId'),'native_readable_R_blocks':sum(b.get('type') in ['thinking','reasoning'] for b in m.get('content',[]) if isinstance(b,dict)) if isinstance(m.get('content'),list) else 0,
    'current_view_claims':[],'withdrawn_view_claims':[],'original_R_disposition':'NO_CURRENT_ORIGINAL_RANGE_ADMISSION_JOINED','original_A_disposition':'NO_CURRENT_ORIGINAL_RANGE_ADMISSION_JOINED',
    'semantics':'NOT_INFERRED_FROM_SOURCE_ADMIT_DONE_RETAIN_OR_EXIT0','no_new_positive_loss':True}
   if oid in outer:
    x=outer[oid];matched=x['native_message_SHA'] in [r['original_message_sha256_sorted'],r['original_message_sha256_insertion_order']]
    r['outer100_identity']={'file':str(outerpath),'owner_id_join':True,'native_message_SHA_match':matched,'exact_provider_crosswalk':x['exact_crosswalk_match'],'new_original_R_characters':x['new_original_R_characters'],'unproven_time_candidates_are_not_links':True}
   assert oid not in allowners;allowners[oid]=r
   if m.get('responseId'):ridmap[m['responseId']].add(oid)
   for c in calls(m):
    if c.get('id'):toolmap[c['id']].add(oid)
    a=args(c);path=a.get('path',a.get('file_path'));code=a.get('content','')
    if c.get('name')=='write' and isinstance(path,str) and Path(path).suffix.lower() in ['.py','.js','.ts','.tsx','.jsx','.html','.css','.sh'] and isinstance(code,str) and len(code)>=300:
     programs.append({'canonical_owner_id':oid,'population':pop,'episode_id':eid,'role':r['historical_role'],'route_id':r['route_id'],'source_ids':sids,'source_disposition':scope,
       'original_tool_call_id':c.get('id'),'native_path':path,'original_content_utf8_SHA256':bh(code.encode()),'characters':len(code),'whole_tool_write_content_recovered':True,
       'original_body_ref':r['original_body_ref'],'syntax_or_business_correctness_not_approved':True,'positive_loss':0,'full_code':code})
 for ep in rows(ctxpath):accept_episode(ep,'V9_OLD1763' if ep.get('old_canonical_episode_id') else 'V9_SUPPLEMENT80')
 assert len(allowners)==34239 and set(labels)<=set(allowners)
 assert sum(x['population']=='V9_OLD1763' for x in allowners.values())==32342
 # Add only explicitly located subsequent recordings, never recurse through
 # workspace skills/cache/junctions or dispatch any old command.
 extras={}
 late=R/'output/20261029_wrd_batch24/late_producer_closure/LATE_NATIVE_ROUTE_PRODUCER_CLOSURE.json'
 if late.exists():
  source(late);ld=json.loads(late.read_text(encoding='utf-8'))
  for b in ld['batches_checked']:
   known=[r['observation_message_index'] for r in b['actual_input_receipts'] if r['protected_or_static_sources']]
   extras[b['native']['path']]={'population':'LATE_OMITTED_ROUTE_BATCH','late_protected_observation_index':min(known) if known else None}
 scheduled=R/'output/20261029_wrd_batch24/scheduled/ANCESTRY_PROOF.json'
 if scheduled.exists():
  source(scheduled);sd=json.loads(scheduled.read_text(encoding='utf-8'));extras[sd['producer_native']['path']]={'population':'LATE_OMITTED_ROUTE_BATCH','late_protected_observation_index':sd['actual_producer_input']['observation_message_index']}
 for job in sorted((M/'runtime_preflight/episodes').iterdir()):
  if not job.is_dir() or job.is_symlink() or (hasattr(job,'is_junction') and job.is_junction()):continue
  p=job/'openclaw_transport/session_events.jsonl'
  if p.is_file():extras[str(p)]={'population':'POST_V9_NATIVE_DEVELOPMENT','job_id':job.name}
 seen_sid={x['native_session_id']:x for x in episode_info if x['native_session_id']}
 for p,detail in extras.items():
  sid,ms,lines,err=parse_native(p)
  if sid in seen_sid:
   capture_conflicts.append({'source':pin(p),'native_session_id':sid,'existing_episode':seen_sid[sid]['episode_id'],'not_added_as_independent_session':True,'reason':'Existing session identity; requires exact per-message alias check, not duplicate task counting.'});continue
  eid='native_extra_'+(str(sid) if sid else sha(p)[:24]);ep={'episode_id':eid,'native_session_id':sid,'source_native':pin(p),'source_original_path':p,'messages':ms,'source_event_lines':lines,
   'stage':detail.get('job_id','route_batch'),'route_id':detail.get('job_id',Path(p).parents[1].name),'system_capture_status':'NOT_RECOVERED_HERE','parse_errors':err,**detail}
  accept_episode(ep,detail['population']);contexts_extra.append(ep);seen_sid[sid]=episode_info[-1]
 gzwrite(O/'EXTRA_NATIVE_CONTEXTS.original.jsonl.gz',contexts_extra)
 # Immutable original provider groups remain a separate population. A candidate
 # shared response ID is recorded, not proof of equal request or internal CoT.
 providermeta={x['provider_response_id']:x for x in rows(R/'output/20261026_wrd_quality_v8/controlled/provider_responses.metadata.jsonl.gz')}
 providers=[]
 for pair in rows(providerpath):
  rid=pair['provider_response_id'];pmeta=providermeta.get(rid,{})
  providers.append({'canonical_provider_group_id':'provider:'+rid,'provider_response_id':rid,'response_message_sha256':pair['response_message_sha256'],'response_source':pair['response_source'],
   'body_ref':{'file':'audit_inputs/provider1536.pairs.original.jsonl.gz','provider_response_id':rid},'historical_execution_condition':pair.get('historical_execution_condition'),
   'original_R_characters':pmeta.get('reasoning_characters'),'prior_original226_scope':pmeta.get('original226_scope'),'scope_disposition':'PRESERVED_PENDING_CURRENT_PREFIX_ANCESTRY_JOIN',
   'native_shared_response_id_candidates':sorted(ridmap.get(rid,set())),'shared_response_id_is_not_complete_causal_equivalence':True,'current_view_claims':[],'no_new_positive_loss':True})
 # Current compatible captures bridge the admitted v10 native bodies/ranges to
 # actual response bytes. IDs plus actual native/tool signatures remain explicit.
 current_wire=[];wire_sha_to_native={};wire_rid_to_sha={}
 for job in sorted((M/'runtime_preflight/episodes').iterdir()):
  if not job.is_dir():continue
  for call in sorted((job/'api_audit').glob('*')):
   if not call.is_dir():continue
   for p in sorted(call.glob('response.raw.*')):
    if p.suffix not in ['.sse','.json']:continue
    d=parse_wire(p);wsha=sha(p);owners=sorted(ridmap.get(d['response_id'],set()))
    current_wire.append({'compatible_response_sha256':wsha,'job_id':job.name,'call_id':call.name,'source':pin(p),'parsed_original_response_fields':d,
      'native_response_id_matches':owners,'scope':'CURRENT_COMPATIBLE_CAPTURE_NOT_UNSEEN_BACKEND_REASONING_GUARANTEE','new_positive_loss':0})
    wire_sha_to_native[wsha]=owners
    if d['response_id']:wire_rid_to_sha[d['response_id']]=wsha
 gzwrite(O/'CURRENT_COMPAT_WIRE.with_body.jsonl.gz',current_wire)
 views=[];unjoined=[];receipts=[];external_owners={};provider_by_source_sha=defaultdict(list)
 for p in providers:provider_by_source_sha[p['response_source']['sha256']].append(p)
 def evidence_refs(meta):
  ev=meta.get('evidence') or {};return ev if isinstance(ev,dict) else {}
 def classify_view(meta,bank):
  ann=str(meta.get('annotation_provenance',''))
  if bank=='source_contract_main' or 'SOURCE_ONLY_DECISION' in ann or 'NEW_AUTHORED_REAL_STATE_COST_STOP' in str(meta.get('id','')):return 'NEW_AUTHORED_ANNOTATION'
  if 'NEW_AUTHORED' in ann or 'EXPLICIT_NEW_FUNCTIONAL_STATE' in ann or 'NEW_AUTHORED' in str(meta.get('new_input_identity','')):return 'NEW_STATE_OR_ACTION_PROJECTION'
  if meta.get('canonical_original_response_owner') or str(meta.get('owner_id','')).startswith('historical_R:'):return 'HISTORICAL_ORIGINAL_R_SCOPED_VIEW'
  if (meta.get('target_owner') or {}).get('canonical_original_R_owner_id'):return 'RECORDED_CUMULATIVE_R_EXCERPT_WITH_PROJECTED_A'
  return 'DECLARED_NATIVE_SCOPED_VIEW'
 def link_view(row,path,withdrawn=False):
  meta=row.get('original_record_metadata',row);owner=meta.get('target_owner') or {};ev=evidence_refs(meta);bank=row.get('bank',meta.get('bank'));kind=classify_view(meta,bank)
  raw_ids=set();reasons=[]
  for k in ['canonical_original_target_id']:
   if owner.get(k) in allowners:raw_ids.add(owner[k]);reasons.append('explicit canonical original target owner')
  eid=owner.get('original_episode_id');idx=owner.get('original_message_index')
  if isinstance(eid,str) and isinstance(idx,int) and tid(eid,idx) in allowners:raw_ids.add(tid(eid,idx));reasons.append('explicit original episode and index')
  for key in ['original_tool_call_id','tool_call_id']:
   if owner.get(key) in toolmap:raw_ids.update(toolmap[owner[key]]);reasons.append('explicit original tool call identity')
  for t in row.get('targets',[]):
   if not t.get('supervised_tokens'):continue
   for c in row.get('messages',[])[t['message_index']].get('tool_calls',[]):
    if c.get('id') in toolmap:raw_ids.update(toolmap[c['id']]);reasons.append('supervised native tool call identity')
  response=ev.get('response');resp_sha=ev.get('response_sha256',meta.get('actual_response_sha256'))
  source_response=meta.get('source_original_SSE') or {}
  if resp_sha in wire_sha_to_native:raw_ids.update(wire_sha_to_native[resp_sha]);reasons.append('exact saved compatible response SHA to native response identity')
  pclaims=provider_by_source_sha.get(source_response.get('sha256'),[])
  v={'view_id':row.get('id',meta.get('id')),'bank':bank,'compiled_file':str(path),'withdrawn_bank':withdrawn,'view_conditioning':kind,
    'source_ids':row.get('source_ids',meta.get('source_ids',[])),'source_group_id':row.get('source_group_id',meta.get('source_group_id')),
    'source_admission':meta.get('source_admission'),'training_admitted_claim':meta.get('training_admitted'),'annotation_provenance':meta.get('annotation_provenance'),
    'canonical_owner_claim':meta.get('owner_id'),'target_owner':owner,'historical_original_response_owner':meta.get('canonical_original_response_owner'),
    'approved_field_ranges':meta.get('approved_field_ranges',[]),'target_excluded_rendered_ranges':meta.get('target_excluded_rendered_ranges',[]),
    'actual_token_supervision_spans':row.get('supervision_spans',[]),'actual_supervised_tokens':row.get('supervised_tokens',0),
    'component_tokens':row.get('supervised_tokens_by_component',{}),'rendered_sha256':row.get('rendered_sha256'),
    'positive_target_messages':[{'message_index':t['message_index'],'original_declared_target_message':row['messages'][t['message_index']]} for t in row.get('targets',[]) if t.get('supervised_tokens')],
    'input_condition_ref':{'compiled_file':str(path),'view_id':row.get('id'),'full_messages_are_preserved_there':True},
    'native_owner_links':sorted(raw_ids),'link_evidence':sorted(set(reasons)),'original_provider_group_links':[p['canonical_provider_group_id'] for p in pclaims],
    'source_review':meta.get('new_semantic_review',meta.get('source_review_path',meta.get('semantic_review'))),
    'requires_external_root_admission':meta.get('requires_external_root_admission'),'new_state_does_not_clear_original_prefix':kind!='DECLARED_NATIVE_SCOPED_VIEW'}
  external=[]
  historical=meta.get('canonical_original_response_owner')
  if historical:external.append(('historical_response:'+historical,'ORIGINAL_HISTORICAL_RESPONSE_NOT_NATIVE_EQUIVALENT'))
  for k in ['original_pair_id','original_action_pair_id']:
   if owner.get(k):external.append(('historical_pair:'+owner[k],'RECORDED_HISTORICAL_ACTION_PAIR_WITH_NEW_PROJECTION'))
  if owner.get('source_original_response_owner'):external.append(('historical_response:'+owner['source_original_response_owner'],'ORIGINAL_RESPONSE_REUSED_FOR_NEW_RESOURCE_ACTION'))
  if owner.get('canonical_original_R_owner_id'):external.append((owner['canonical_original_R_owner_id'],'RECORDED_CUMULATIVE_ORIGINAL_R_EXCERPT_NOT_PER_TURN_NATIVE_R'))
  if owner.get('canonical_original_action_owner_id') and not external and not raw_ids:external.append((owner['canonical_original_action_owner_id'],'RECORDED_EXTERNAL_ACTION_ID_NOT_IN_NATIVE_UNIVERSE'))
  v['external_historical_owner_links']=[x[0] for x in external]
  v['new_authored_view_does_not_require_original_native_owner']=kind=='NEW_AUTHORED_ANNOTATION' or kind=='NEW_STATE_OR_ACTION_PROJECTION' and not external and not raw_ids
  if not withdrawn:views.append(v)
  summary={k:v[k] for k in ['view_id','bank','view_conditioning','actual_supervised_tokens','component_tokens','compiled_file']}
  summary['original_R_claimed']=kind in ['DECLARED_NATIVE_SCOPED_VIEW','HISTORICAL_ORIGINAL_R_SCOPED_VIEW','RECORDED_CUMULATIVE_R_EXCERPT_WITH_PROJECTED_A'] and v['component_tokens'].get('R',0)>0
  summary['original_A_claimed']=kind=='DECLARED_NATIVE_SCOPED_VIEW' and v['component_tokens'].get('A',0)>0
  for oid in raw_ids:
   allowners[oid]['withdrawn_view_claims' if withdrawn else 'current_view_claims'].append(summary)
   if not withdrawn:
    if summary['original_R_claimed']:allowners[oid]['original_R_disposition']='PARTIAL_CURRENT_SCOPED_ORIGINAL_R_RANGE_ADMITTED_NOT_WHOLE_RESPONSE'
    if summary['original_A_claimed']:allowners[oid]['original_A_disposition']='CURRENT_SCOPED_ORIGINAL_A_ADMITTED_NOT_WHOLE_TRAJECTORY'
  for p in pclaims:p['current_view_claims'].append(summary)
  for key,origin in external:
   e=external_owners.setdefault(key,{'canonical_external_owner_id':key,'recorded_population':'EXTERNAL_HISTORICAL_NOT_NATIVE_EQUIVALENT','origin_claim':origin,
    'current_view_claims':[],'withdrawn_view_claims':[],'original_source_record_pins':[],'whole_response_or_Autonomous_gold':False})
   e['withdrawn_view_claims' if withdrawn else 'current_view_claims'].append(summary)
   for field in ['source_request','source_original_SSE']:
    ref=meta.get(field)
    if isinstance(ref,dict) and ref.get('path'):
     record={'field':field,'expected_pin':ref,'actual_preserved_copy':None};p=Path(ref['path'])
     if p.is_file() and sha(p)==ref.get('sha256'):
      dest=audit/'external_historical_objects'/ref['sha256'];dest.parent.mkdir(exist_ok=True)
      if not dest.exists():shutil.copyfile(p,dest)
      record['actual_preserved_copy']=pin(dest)
     if record not in e['original_source_record_pins']:e['original_source_record_pins'].append(record)
  if not raw_ids and not pclaims and not external:unjoined.append({'view_id':v['view_id'],'bank':bank,'condition':kind,'withdrawn':withdrawn,'owner_claim':meta.get('owner_id'),'historical_response_owner':meta.get('canonical_original_response_owner'),
    'status':'NOT_A_NATIVE_OWNER_EXPECTED' if kind=='NEW_AUTHORED_ANNOTATION' else 'EXTERNAL_ORIGINAL_OR_NEW_STATE_OWNER_NEEDS_ADDITIONAL_ALIAS_MAPPING','known_evidence_refs':{'source_request':meta.get('source_request'),'source_original_SSE':source_response,'evidence':ev,'target_owner':owner}})
  return v
 for f,row in active_rows():link_view(row,M/f['path'])
 assert len(views)==552 and sum(x['actual_supervised_tokens'] for x in views)==150674
 withdrawn=[]
 for rel in man['withdrawn_local_banks']:
  d=M/rel
  if not d.is_dir():withdrawn.append({'bank_path':str(d),'status':'PATH_NOT_PRESENT_PRIOR_MANIFEST_CLAIM_PRESERVED'});continue
  for p in sorted(d.glob('*.jsonl.gz')):
   for row in rows(p):
    if 'supervision_spans' in row and 'messages' in row:withdrawn.append(link_view(row,p,True))
 for ref in man.get('external_root_admission_receipts',[]):
  if not isinstance(ref,dict):continue
  p=Path(ref.get('path',''));p=p if p.is_absolute() else M/p
  if p.is_file():receipts.append({'source':pin(p),'original_receipt':json.loads(p.read_text(encoding='utf-8-sig'))})
 for ref in man['active_compilation_reports']:
  p=M/ref['path'];assert sha(p)==ref['sha256'];receipts.append({'source':pin(p),'original_receipt':json.loads(p.read_text(encoding='utf-8-sig'))})
 # Per-owner final classification is factual source disposition plus explicit
 # current range/view claims. Lack of a new semantic receipt remains pending.
 for o in allowners.values():
  o['current_disposition']=o['source_disposition']
  if o['source_disposition'] in ['SCOPE_CLOSED_SEMANTIC_PENDING','PROTOCOL_PREFIX_NO_BUSINESS_SOURCE']:
   if any(x.get('original_A_claimed') or x.get('original_R_claimed') for x in o['current_view_claims']):o['current_disposition']='PARTIAL_ORIGINAL_RANGE_ADMITTED_REMAINDER_PENDING'
   elif o['current_view_claims']:o['current_disposition']='RELATED_NEW_STATE_VIEW_ADMITTED_ORIGINAL_CONTEXT_PENDING'
   elif o['maker405_static_byte_review']:o['current_disposition']='LOCAL_READONLY_BYTE_REVIEW_NO_COMPLEX_PROGRAM_IN_TARGET'
   elif o['v9_protocol_disposition'].get('supervision_tier'):o['current_disposition']='PROTOCOL_AUXILIARY_REVIEW_ONLY_COMPLEX_SEMANTICS_PENDING'
   else:o['current_disposition']='SOURCE_CLOSED_SEMANTIC_PENDING'
  # Keep historical prefix HOLD when a new conditioning projection is admitted.
  if o['current_view_claims'] and o['source_disposition'].startswith('HOLD_'):o['new_state_only_or_scoped_claim_does_not_resolve_original_hold']=True
 gzwrite(O/'CORPUS_OWNER_COVERAGE.native.jsonl.gz',allowners.values());gzwrite(O/'PROVIDER_OWNER_COVERAGE.jsonl.gz',providers)
 gzwrite(O/'CURRENT552_VIEW_COMPONENT_COVERAGE.jsonl.gz',views);gzwrite(O/'WITHDRAWN_VIEW_COMPONENT_COVERAGE.jsonl.gz',withdrawn)
 gzwrite(O/'EXTERNAL_HISTORICAL_OWNER_COVERAGE.jsonl.gz',external_owners.values())
 gzwrite(O/'SEMANTIC_AND_COMPILER_RECEIPTS.original.jsonl.gz',receipts);gzwrite(O/'UNJOINED_VIEW_OWNER_CLAIMS.jsonl.gz',unjoined)
 gzwrite(O/'EPISODE_CAPTURE_COVERAGE.jsonl.gz',episode_info);gzwrite(O/'RECOVERABLE_COMPLETE_NATIVE_WRITES.with_code.jsonl.gz',programs)
 save(O/'CAPTURE_ALIAS_CONFLICTS.json',capture_conflicts)
 groups=defaultdict(Counter)
 for o in allowners.values():groups[str(o['historical_role'])][o['current_disposition']]+=1
 oldrows=[o for o in allowners.values() if o['canonical_owner_id'] in labels];oldunrev=[o for o in oldrows if (o.get('old_preflight_eligibility') or {}).get('semantic_review')=='not_ai_semantically_reviewed'];assert len(oldunrev)==6692
 scopeprograms=[x for x in programs if x['source_disposition']=='SCOPE_CLOSED_SEMANTIC_PENDING']
 counts={'registered_native_owner_rows':len(allowners),'old_native_owner_rows':len(oldrows),'v9_expanded_native_owner_rows':34239,'provider_groups_separate_not_additive_tasks':len(providers),
  'registered_native_episodes':len(episode_info),'old6692_joined_by_exact_owner_ID':len(oldunrev),'current552_views':len(views),'current552_supervised_tokens':sum(x['actual_supervised_tokens'] for x in views),
  'current_view_native_linked':sum(bool(x['native_owner_links']) for x in views),'current_view_provider_linked':sum(bool(x['original_provider_group_links']) for x in views),
  'current_view_external_historical_linked':sum(bool(x['external_historical_owner_links']) for x in views),'current_new_authored_no_original_owner_expected':sum(x['new_authored_view_does_not_require_original_native_owner'] for x in views),
  'native_original_R_scoped_owners_linked':sum(o['original_R_disposition'].startswith('PARTIAL_') for o in allowners.values()),
  'native_original_A_same_condition_scoped_owners_linked':sum(o['original_A_disposition'].startswith('CURRENT_') for o in allowners.values()),
  'external_historical_owner_rows':len(external_owners),
  'unjoined_current_view_claims':sum(not x['withdrawn'] for x in unjoined),'withdrawn_compiled_view_rows':sum('view_id' in x for x in withdrawn),
  'native_dispositions':dict(Counter(o['current_disposition'] for o in allowners.values())),'old32342_dispositions':dict(Counter(o['current_disposition'] for o in oldrows)),
  'old6692_dispositions':dict(Counter(o['current_disposition'] for o in oldunrev)),'roles':{k:dict(v) for k,v in groups.items()},
  'full_native_code_write_targets_recovered':len(programs),'distinct_full_native_code_write_SHA':len({x['original_content_utf8_SHA256'] for x in programs}),
  'scope_closed_business_source_code_write_targets':len(scopeprograms),'scope_closed_business_source_code_distinct_SHA':len({x['original_content_utf8_SHA256'] for x in scopeprograms}),
  'recoverable_code_role_counts':dict(Counter(str(x['role']) for x in scopeprograms)),
  'note':'Write content recovery is exact bytes, not syntax/business/Q/cost success. Inline exec writes, edits and provider programs remain separately recoverable but not inflated into this full-write count.',
  'new_semantic_or_training_admissions':0,'training_started':False,'full_global_discovery_exhaustive':False}
 save(O/'SUMMARY.json',counts)
 save(O/'QA.json',{'status':'PASS_FIXED_POPULATION_OWNER_SCOPE_AND_VIEW_RECONCILIATION_WITH_EXPLICIT_UNJOINED_CASES','inputs':inputs,
  'canonical_old32342_all_joined':len(set(labels)&set(allowners))==32342,'all_7117_legacy_eligibility_owners_joined':set(elig)<=set(allowners),
  'new_state_not_native_or_original_R_by_default':True,'unknown_not_given_positive_loss':True,'main_manifest_start_sha256':bh(baseline),'main_manifest_end_sha256':sha(mf),
  'main_manifest_unchanged':sha(mf)==bh(baseline),'current_views_all552_actual_component_tokens_recounted':sum(x['actual_supervised_tokens'] for x in views)==150674,
  'script':pin(__file__),'no_legacy_Agent_or_model_training_executed':True})
 print(js(counts))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--first6',action='store_true');p.add_argument('--full',action='store_true');a=p.parse_args()
 if a.first6:first6()
 if a.full:full()
