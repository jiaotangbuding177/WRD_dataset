"""Offline corpus-owner reconciliation and preserved actor code evidence. No Agent loop."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,ast,gzip,hashlib,json,shutil,tarfile
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
 if (O/'BASELINE01_FROZEN_FILES.json').exists():raise RuntimeError('Baseline01 is sealed. Append a new explicit overlay instead of rewriting its old classifications.')
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
 current_wire=[];wire_sha_to_native={};wire_rid_to_sha={};wire_by_sha={}
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
    wire_by_sha[wsha]=current_wire[-1]
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
  if not raw_ids and resp_sha in wire_by_sha:
   external.append(('compatible_wire:'+resp_sha,'ACTUAL_COMPATIBLE_WIRE_RESPONSE_WITHOUT_NATIVE_MESSAGE_ID_JOIN'))
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
    'status':'NOT_A_NATIVE_OWNER_EXPECTED' if v['new_authored_view_does_not_require_original_native_owner'] else 'EXTERNAL_ORIGINAL_OR_NEW_STATE_OWNER_NEEDS_ADDITIONAL_ALIAS_MAPPING','known_evidence_refs':{'source_request':meta.get('source_request'),'source_original_SSE':source_response,'evidence':ev,'target_owner':owner}})
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

def reasoning_residual():
 """Exact recorded R identity and char-range anti-join; no quality admission."""
 dest=O/'reasoning_residual';dest.mkdir(exist_ok=True)
 v4=R/'output/20261025_wrd_reasoning_recovery_v4/controlled'
 ins=[V9/'recovery/provider_pairs.original.jsonl.gz',R/'output/20261026_wrd_quality_v8/controlled/provider_responses.metadata.jsonl.gz',
  v4/'raw_pairs.all.jsonl.gz',v4/'sse_reasoning_pairs.all.jsonl.gz',v4/'raw_scope_review.by_run.jsonl.gz',v4/'sse_scope_review.by_pair.jsonl.gz',
  R/'output/20261026_wrd_lineage_v6/controlled/reasoning_pair_lineage_decisions.jsonl.gz',O/'CURRENT552_VIEW_COMPONENT_COVERAGE.jsonl.gz',O/'CORPUS_OWNER_COVERAGE.native.jsonl.gz',M/'clean_inputs/source_scope.metadata.jsonl.gz']
 providers={x['provider_response_id']:x for x in rows(ins[0])};pmeta={x['provider_response_id']:x for x in rows(ins[1])}
 original_raw=list(rows(ins[2]));original_sse=list(rows(ins[3]));raw_scope={x['run_path']:x for x in rows(ins[4])};sse_scope={x['pair_id']:x for x in rows(ins[5])};lineage={x['pair_id']:x for x in rows(ins[6])}
 views=list(rows(ins[7]));natives={x['canonical_owner_id']:x for x in rows(ins[8])};scopes={x['source_id']:x for x in rows(ins[9])}
 native_by_rid=defaultdict(list)
 for n in natives.values():
  if n['native_response_id']:native_by_rid[n['native_response_id']].append(n)
 raw_by_rid=defaultdict(list)
 for x in original_raw:raw_by_rid[x['original_response'].get('id')].append(x)
 def reason_fields(m):return {k:v for k,v in m.items() if k in ['reasoning','reasoning_content','thinking'] and isinstance(v,str) and v}
 def closure(x):
  d=lineage.get(x['id']);ids=d.get('observed_evolution_source_ids',[]) if d else []
  # v6 recorded compact insertion-order JSON, not sorted-key JSON. Preserve
  # its exact hash convention rather than label a representation mismatch as
  # missing ancestry.
  checks={'exact_original_request_sha':bool(d and bh(js(x['original_request']).encode())==d['original_request_canonical_sha256']),
    'v6_status_admit':bool(d and d['status']=='ADMIT'),'v6_resource_closure':bool(d and d['resource_closure_proven']),
    'no_original_protected_ancestor':bool(d and not d['protected_ancestor_present']),'nonempty_current_source_ids':bool(ids),
    'all_current_source_TRAIN':bool(ids and all(scopes.get(s,{}).get('status')=='TRAIN' for s in ids))}
  return {'strict_prefix_closure_and_current_TRAIN':all(checks.values()),'checks':checks,'source_ids':ids,
   'current_source_statuses':{s:scopes.get(s,{}).get('status','MISSING') for s in ids},'original_lineage_record':d}
 def complement(length,spans):
  ms=[]
  for a,b in sorted(spans):
   assert 0<=a<=b<=length
   if ms and a<=ms[-1][1]:ms[-1][1]=max(b,ms[-1][1])
   else:ms.append([a,b])
  gap=[];start=0
  for a,b in ms:
   if start<a:gap.append([start,a])
   start=b
  if start<length:gap.append([start,length])
  return ms,gap
 def ranges_for(original_fields,pair_id,rid):
  approvals=[];claimed=[];fail=[]
  for v in views:
   claim=v.get('historical_original_response_owner')==pair_id or v.get('target_owner',{}).get('canonical_original_R_owner_id')=='historical_cumulative_R:'+pair_id
   # Explicit same recorded owner only; shared response ID alone is not a positive range.
   if not claim:continue
   claimed.append(v['view_id'])
   for t in v['positive_target_messages']:
    msg=t['original_declared_target_message'];idx=t['message_index']
    for f,original in original_fields.items():
     target=msg.get(f)
     if not isinstance(target,str) or not target:continue
     offsets=[i for i in range(len(original)+1) if original.startswith(target,i)]
     if len(offsets)!=1:
      fail.append({'view_id':v['view_id'],'field':f,'mapping':'NO_UNIQUE_EXACT_TARGET_SUBSTRING','matches':len(offsets)});continue
     offset=offsets[0]
     for a in v['approved_field_ranges']:
      if a['field']!=f or a['message_index']!=idx:continue
      piece=target[a['start']:a['end']];valid=bh(piece.encode())==a['text_sha256']
      if not valid:fail.append({'view_id':v['view_id'],'field':f,'mapping':'APPROVED_TEXT_SHA_MISMATCH'});continue
      approvals.append({'view_id':v['view_id'],'field':f,'original_start':offset+a['start'],'original_end':offset+a['end'],
       'approved_target_start':a['start'],'approved_target_end':a['end'],'exact_target_substring_offset_in_original':offset,'text_sha256':a['text_sha256'],
       'original_range_text':piece,'range_hash_validated':True,'conditioning':v['view_conditioning']})
  result={}
  for f,txt in original_fields.items():
   merged,rest=complement(len(txt),[(a['original_start'],a['original_end']) for a in approvals if a['field']==f])
   result[f]={'original_characters':len(txt),'current_approved_original_char_ranges':merged,'current_approved_original_characters':sum(b-a for a,b in merged),
    'remaining_original_char_ranges':rest,'remaining_original_characters':sum(b-a for a,b in rest),'remaining_not_semantically_approved':True}
  return {'exact_current_owner_views':claimed,'current_range_proofs':approvals,'field_coverage':result,'mapping_failures':fail}
 results=[];raw_train_top=[]
 for rid,p in providers.items():
  rf=reason_fields(p['response'])
  if not rf:continue
  matches=[]
  for raw in raw_by_rid.get(rid,[]):
   msg=raw['original_response']['choices'][0]['message'];equal=can(msg)==can(p['response'])
   if not equal:continue
   cl=closure(raw);sc=raw_scope.get(raw['run_path'],{});top=sc.get('complete_semantic_source_evidence',{});sid=top.get('source_id')
   currenttrain=bool(top.get('verified_current_evolution_complete_source') and scopes.get(sid,{}).get('status')=='TRAIN')
   rr=ranges_for(rf,raw['id'],rid)
   matches.append({'original_pair_id':raw['id'],'exact_provider_ID_and_full_message_SHA':True,'original_request_canonical_SHA':bh(can(raw['original_request']).encode()),
    'original_response_source':raw['source_response'],'run_path':raw['run_path'],'original_R_pointer':raw.get('original_reasoning_pointer'),
    'current_scope_and_lineage':cl,'original_run_scope_review':sc,'current_TRAIN_top_source_only_not_prefix_closure':currenttrain,'current_R_range_anti_join':rr})
   if currenttrain:
    raw_train_top.append({'provider_response_id':rid,'original_pair':raw,'provider_original_pair':p,'identity_and_scope':matches[-1],
     'source_scope':scopes[sid],'positive_loss':0,'status':'CUMULATIVE_RECORDED_R_WITH_TRAIN_TOP_SOURCE_BUT_FINAL_REQUEST_LINEAGE_UNCLOSED'})
  natives_matching=native_by_rid.get(rid,[])
  strict=any(x['current_scope_and_lineage']['strict_prefix_closure_and_current_TRAIN'] for x in matches)
  disposition='STRICT_TRAIN_PREFIX_CLOSED_R_SEMANTICS_PENDING' if strict else 'UNRESOLVED_OR_EXCLUDED_NOT_POSITIVE'
  results.append({'provider_response_id':rid,'original_response_message_SHA256':bh(can(p['response']).encode()),
   'actual_response_message_SHA_matches_saved':bh(can(p['response']).encode())==p['response_message_sha256'],'original_provider_pair':p,'original_reasoning_fields':rf,
   'provider_prior_scope_metadata':pmeta[rid],'exact_historical_pair_matches':matches,
   'same_response_ID_native_candidates':[{'owner_id':n['canonical_owner_id'],'body_ref':n['original_body_ref'],'source_native':n['source_native'],
      'scope':n['source_disposition'],'source_ids':n['source_ids'],'role':n['historical_role'],'causal_request_equivalence_not_proven':True,'new_positive_loss':0} for n in natives_matching],
   'strict_TRAIN_prefix_closed':strict,'disposition':disposition,'semantics_admitted':False,'positive_loss':0})
 assert len(results)==257
 gzwrite(dest/'PROVIDER257_R_RESIDUAL.with_body.jsonl.gz',results)
 gzwrite(dest/'CURRENT_TRAIN_TOP_SOURCE_CUMULATIVE_R.with_original_pairs.jsonl.gz',raw_train_top)
 sse=[]
 for original in original_sse:
  msg=original['original_response']['choices'][0]['message'];rf=reason_fields(msg)
  if not rf:continue
  cl=closure(original);rr=ranges_for(rf,original['id'],original['original_response'].get('id'))
  sse.append({'historical_pair_id':original['id'],'actual_original_pair':original,'original_scope_review':sse_scope.get(original['id']),
   'exact_original_lineage_and_current_TRAIN':cl,'current_R_range_anti_join':rr,'provider1536_member_by_original_responseID':original['original_response'].get('id') in providers,
   'strict_TRAIN_prefix_closed':cl['strict_prefix_closure_and_current_TRAIN'],'remaining_characters_not_new_admission':True,'positive_loss':0})
 gzwrite(dest/'EXTERNAL_SSE67_R_CURRENT_RANGE_RESIDUAL.with_body.jsonl.gz',sse)
 summary={'registered_provider_groups':len(providers),'nonempty_original_R_provider_groups':len(results),
  'provider_R_exact_v4_pair_matches':sum(bool(x['exact_historical_pair_matches']) for x in results),
  'provider_R_same_ID_native_candidates':sum(bool(x['same_response_ID_native_candidates']) for x in results),
  'provider_R_same_ID_native_candidate_scopes':dict(Counter(n['scope'] for x in results for n in x['same_response_ID_native_candidates'])),
  'provider_R_strict_current_TRAIN_closed_prefix':sum(x['strict_TRAIN_prefix_closed'] for x in results),
  'provider_R_current_TRAIN_top_source_cumulative_but_prefix_unclosed':len(raw_train_top),
  'top_source_cumulative_R_original_characters':sum(sum(len(v) for v in reason_fields(x['original_pair']['original_response']['choices'][0]['message']).values()) for x in raw_train_top),
  'top_source_cumulative_R_current_approved_characters':sum(sum(f['current_approved_original_characters'] for f in x['identity_and_scope']['current_R_range_anti_join']['field_coverage'].values()) for x in raw_train_top),
  'top_source_cumulative_R_remaining_not_approved_characters':sum(sum(f['remaining_original_characters'] for f in x['identity_and_scope']['current_R_range_anti_join']['field_coverage'].values()) for x in raw_train_top),
  'external_original_SSE_R_pairs':len(sse),'external_SSE_strict_current_TRAIN_closed_prefix':sum(x['strict_TRAIN_prefix_closed'] for x in sse),
  'external_SSE_current_R_owner_covered':sum(bool(x['current_R_range_anti_join']['exact_current_owner_views']) for x in sse),
  'external_SSE_strict_TRAIN_uncovered_whole_owner':sum(x['strict_TRAIN_prefix_closed'] and not x['current_R_range_anti_join']['exact_current_owner_views'] for x in sse),
  'external_SSE_current_approved_original_chars':sum(sum(f['current_approved_original_characters'] for f in x['current_R_range_anti_join']['field_coverage'].values()) for x in sse),
  'external_SSE_strict_TRAIN_remaining_not_approved_chars':sum(sum(f['remaining_original_characters'] for f in x['current_R_range_anti_join']['field_coverage'].values()) for x in sse if x['strict_TRAIN_prefix_closed']),
  'range_mapping_failures':sum(len(x['current_R_range_anti_join']['mapping_failures']) for x in sse)+sum(len(x['identity_and_scope']['current_R_range_anti_join']['mapping_failures']) for x in raw_train_top),
  'provider1536_and_historical_SSE_populations_overlap_by_original_responseID':sum(x['provider1536_member_by_original_responseID'] for x in sse),
  'source_or_prefix_closure_is_not_R_quality_or_causality_gold':True,'new_positive_loss':0,'training_started':False,'inputs':[pin(p) for p in ins]}
 save(dest/'SUMMARY.json',summary);print(js(summary))

def supplement56_index():
 """Preserve provider/native identities and raw inputs, leaving scope to overlay."""
 out=O/'supplement56';out.mkdir(exist_ok=True);objects=out/'objects';objects.mkdir(exist_ok=True)
 source=O/'reasoning_residual/PROVIDER257_R_RESIDUAL.with_body.jsonl.gz'
 ps=[x for x in rows(source) if x['same_response_ID_native_candidates']]
 episodes=defaultdict(list)
 for x in ps:
  for n in x['same_response_ID_native_candidates']:episodes[n['body_ref']['context_episode_id']].append((x,n))
 wanted=set(episodes);ctx={x['episode_id']:x for x in rows(O/'audit_inputs/native1843.contexts.original.jsonl.gz') if x['episode_id'] in wanted}
 def copy(ref):
  p=Path(ref['path']);assert p.is_file() and sha(p)==ref['sha256'];d=objects/ref['sha256']
  if not d.exists():shutil.copyfile(p,d)
  return pin(d)
 indexed=[];eplist=[]
 for eid,xs in sorted(episodes.items()):
  ep=ctx[eid];epcopy=copy(ep['source_native']);users=[{'native_message_index':i,'event_line':ep['source_event_lines'][i],'original_message':m} for i,m in enumerate(ep['messages']) if m.get('role')=='user']
  entry={'episode_id':eid,'native_session_id':ep.get('native_session_id'),'source_native':ep['source_native'],'preserved_native':epcopy,
   'original_context_ref':{'file':'../audit_inputs/native1843.contexts.original.jsonl.gz','episode_id':eid},'owners':len(xs),
   'source_original_path':ep.get('source_original_path'),'original_initial_user_messages':users,'stage':ep.get('stage'),
   'no_role_name_scope_exclusion':True,'positive_loss':0,'scope_overlay_pending':True}
  eplist.append(entry)
  for original,n in sorted(xs,key=lambda z:z[1]['body_ref']['message_index']):
   p=original['original_provider_pair'];i=n['body_ref']['message_index'];nm=ep['messages'][i];assert nm.get('responseId')==p['provider_response_id']
   reqs=[]
   for v in p['request_variants']:
    raw=Path(v['source']['path']);data=json.loads(raw.read_text(encoding='utf-8-sig'));assert data.get('messages')==v['messages'] and data.get('tools',[])==v['tools']
    reqs.append({'source_original':v['source'],'preserved_actual_raw_request':copy(v['source']),
      'source_fields_in_original_API_user_payload':[{'message_index':j,'role':'user','content_sha256':bh(can(m.get('content')).encode()),'content':m.get('content')} for j,m in enumerate(v['messages']) if m.get('role')=='user'],
      'full_schema_tool_count':len(v['tools']),'exact_full_raw_messages_and_tools_match_recovered_variant':True})
   indexed.append({'owner_id':n['owner_id'],'provider_response_id':p['provider_response_id'],'episode_id':eid,'native_message_index':i,'native_event_line':ep['source_event_lines'][i],
    'original_native_message':nm,'source_native':ep['source_native'],'preserved_native':epcopy,'original_provider_response':p['response'],
    'source_response_original':p['response_source'],'preserved_raw_response':copy(p['response_source']),'actual_raw_requests':reqs,
    'full_native_prefix_ref':{'file':'../audit_inputs/native1843.contexts.original.jsonl.gz','episode_id':eid,'cutoff_message_index_inclusive':i-1},
    'request_context_to_native_prefix_causal_equivalence_not_assumed':True,'original_R_fields':original['original_reasoning_fields'],
    'current552_same_original_R_owner_covered':False,'scope_pending_actual_inputs_and_read_ancestors':True,'positive_loss':0})
 assert len(indexed)==56 and len(eplist)==6
 gzwrite(out/'INDEX56.with_original_R_and_input_locations.jsonl.gz',indexed);gzwrite(out/'EPISODE6.initial_input_and_native_pins.jsonl.gz',eplist)
 save(out/'INDEX_SUMMARY.json',{'response_owners':56,'native_episodes':6,'index':pin(out/'INDEX56.with_original_R_and_input_locations.jsonl.gz'),
  'episode_index':pin(out/'EPISODE6.initial_input_and_native_pins.jsonl.gz'),'original_provider_residual_input':pin(source),'new_positive_loss':0,'scope_overlay_pending':True,
  'by_episode':[{k:v for k,v in e.items() if k not in ['original_initial_user_messages']} for e in eplist]})
 print(js({'supplement56':pin(out/'INDEX56.with_original_R_and_input_locations.jsonl.gz'),'episodes':6}))

def extra_exec6():
 out=O/'extra_exec6';out.mkdir(exist_ok=True);(out/'objects').mkdir(exist_ok=True)
 ids={'66e542b63e52392b7e1dbfc2','45367ef84bf2439e17a581a1','fafb3212c62efbe26bdfe766','d6716e204b078560e6728d4a','43280ee97c7e5a3da3c9053c','fe6facbf46882ca14fc4cd17'}
 owners={x['canonical_owner_id']:x for x in rows(O/'CORPUS_OWNER_COVERAGE.native.jsonl.gz') if x['canonical_owner_id'] in ids};assert len(owners)==6
 wanted={x['episode_id'] for x in owners.values()};ctx={x['episode_id']:x for x in rows(O/'audit_inputs/native1843.contexts.original.jsonl.gz') if x['episode_id'] in wanted}
 resources=defaultdict(list)
 for x in rows(V9/'outcomes/recomputed_scope_overlay/resource_scope.jsonl.gz'):
  if x['episode_id'] in wanted:resources[x['episode_id']].append(x)
 indexpath=R/'output/20261026_wrd_raw_census_v7/indexes/episode_files.all.jsonl.gz';files=defaultdict(list)
 for x in rows(indexpath):
  if x['episode_id'] in wanted:files[x['episode_id']].append(x)
 scope={x['source_id']:x for x in rows(M/'clean_inputs/source_scope.metadata.jsonl.gz')};results=[]
 for oid,n in owners.items():
  ep=ctx[n['episode_id']];i=n['source_message_index'];m=ep['messages'][i];assert n['source_disposition']=='SCOPE_CLOSED_SEMANTIC_PENDING'
  original_calls=calls(m);assert any(c.get('name')=='exec' for c in original_calls)
  groupdir=out/oid;groupdir.mkdir(exist_ok=True);gzwrite(groupdir/'CONTEXT.original.jsonl.gz',[ep]);feedback=[]
  for c in original_calls:
   for j,q in enumerate(ep['messages']):
    if q.get('toolCallId')==c.get('id'):feedback.append({'message_index':j,'event_line':ep['source_event_lines'][j],'original_message':q})
  frozen=[]
  for f in files[n['episode_id']]:
   # Same audited frozen object identity convention as first6; do not guess
   # unavailable files from a final-state directory.
   rel=f['logical_path'].split('/workspace/',1)[-1]
   if '/workspace/' not in f['logical_path'] or not (rel.startswith('inputs/') or rel.startswith('outputs/')):continue
   p=f.get('physical_frozen_CAS_path');expected=f.get('stored_sha256')
   if not p or not expected or not Path(p).is_file() or sha(p)!=expected:continue
   q=out/'objects'/expected
   if not q.exists():shutil.copyfile(p,q)
   frozen.append({'original_index_record':f,'preserved_copy':pin(q)})
  prior=[r for r in resources[n['episode_id']] if r['observed_after_assistant_message_index']<i]
  group={'original_owner_id':oid,'native_owner_record':n,'original_context':ep,'original_target_message':m,'actual_feedback':feedback,
   'original_code_command_texts':[args(c).get('command') for c in original_calls if c.get('name')=='exec'],'observed_prior_resources':prior,
   'known_prior_graph_issues':[r for r in prior if r['unknown_reasons'] or r['protected_source_ids'] or any(scope.get(s,{}).get('status')!='TRAIN' for s in r['source_ids'])],
   'frozen_file_objects':frozen,'raw_episode_file_index':files[n['episode_id']],'actual_prior_calls':[{'index':j,'call':q} for j,nm in enumerate(ep['messages'][:i]) for q in calls(nm)],
   'all_current_source_statuses':{s:scope[s]['status'] for s in n['source_ids']},'source_scope_proof_existing_not_complete_independent_omission_audit':True,
   'mechanical_success_not_business_correctness':True,'complete_native_original_system_not_recovered_in_old_capture':True,'semantic_quality_admitted':False,'positive_loss':0}
  save(groupdir/'GROUP.json',group);results.append({'owner_id':oid,'episode_id':n['episode_id'],'group':pin(groupdir/'GROUP.json'),
   'code_command_characters':sum(len(x or '') for x in group['original_code_command_texts']),'graph_issues':len(group['known_prior_graph_issues'])})
 save(out/'EXTRA6_ACTUAL_COMMAND_GROUPS.json',{'groups':results,'additional_owners':6,'distinct_episodes':len(wanted),'positive_loss':0,'not_six_independent_sources':True})
 print(js(results))

def review_slices():
 out=O/'review_slices';out.mkdir(exist_ok=True)
 reviewdir=M/'historical_v6_reasoning_review_01/combined26_peer_refined_01';partpath=reviewdir/'CHARACTER_PARTITION.json';reviewpath=reviewdir/'REVIEW.json'
 partition=json.loads(partpath.read_text(encoding='utf-8'));originals={x['historical_pair_id']:x for x in rows(O/'reasoning_residual/EXTERNAL_SSE67_R_CURRENT_RANGE_RESIDUAL.with_body.jsonl.gz')}
 selected=originals.keys();outblocks=[];count=Counter();seen=defaultdict(list)
 for b in partition['blocks']:
  o=originals[b['pair_id']];t=o['actual_original_pair']['original_response']['choices'][0]['message']['reasoning_content'];piece=t[b['start']:b['end']]
  assert len(piece)==b['characters'] and bh(piece.encode())==b['text_sha256']
  count[b['classification']]+=len(piece);seen[b['pair_id']].append((b['start'],b['end']))
  outblocks.append({**b,'original_R_text':piece,'current_review_pin':pin(partpath),'positive_loss':0,'no_new_semantic_credit':True})
 assert dict(count)==partition['counts'] and sum(count.values())==396231 and count['POSITIVE_LOCAL_PLAN_INFERENCE_OR_FACT']==127833
 for pid,ss in seen.items():
  ss=sorted(ss);assert ss[0][0]==0 and all(a[1]==b[0] for a,b in zip(ss,ss[1:]));assert ss[-1][1]==len(originals[pid]['actual_original_pair']['original_response']['choices'][0]['message']['reasoning_content'])
 gzwrite(out/'HISTORICAL26_EXACT_REMAINDER_CLASSIFICATIONS.with_original_text.jsonl.gz',outblocks)
 inventory=json.loads(reviewpath.read_text(encoding='utf-8'))['inventory'];assert len(inventory)==26 and all(x['full_original_R_read_by_AI'] for x in inventory)
 summary={'original_R_owners':26,'original_R_characters':396231,'current_positive_R_chars':127833,'current_mask0_R_chars':268398,
  'exact_current_review_partition_counts':dict(count),'read_status':'ALL_26_PREVIOUS_AI_FULL_TEXT_READ; UNKNOWN_MEANS_NOT_APPROVED_NOT_UNREAD',
  'unknown_not_approved_chars':count['STILL_UNKNOWN_NOT_APPROVED'],'unknown_not_approved_is_not_quality_gold':True,
  'length_only_explanation_rejected':'The actual current review explicitly masks wrong/unsupported/repeated/unknown text; all26 complete sequences fit32K and2 fit16K. Mask0 is not solely a context length omission.',
  'views_current_range_hashes_previously_checked':True,'current_reports_are_evidence_not_new_admission':True,'partition_pin':pin(partpath),'review_pin':pin(reviewpath),
  'new_positive_loss':0}
 save(out/'HISTORICAL26_REMAINDER_SUMMARY.json',summary)
 # These are explicit original proposal/diagnostic candidates for the root's
 # further review, not a reversal of the prior UNKNOWN judgement.
 chosen={'8856374c439400f01448d478':{'mechanism':'PURE_CALCULATION_FIXTURE_VS_IMAGE_DEPENDENCY_BRANCH','candidate_focus':'Separate prospective arithmetic test from image diagnosis requiring absent OCR; inspect the finite computation code as a proposal only. Do not grant capital<=valuation as a universal legal rule.',
    'previous_zero_reason':'Unselected full computation code and business-condition claims were not independently certified; this package does not overrule that.'},
   '26a579d12f5385787683d786':{'mechanism':'WORD_XML_PRESENTATION_DIFFERENTIAL_DIAGNOSTIC','candidate_focus':'The original proposed comparison of signed-debit representations and explicit XML placement checks may support bounded test design. Need pure-resource verification; ZIP/text presence cannot imply rendered Word/business correctness.',
    'previous_zero_reason':'Synthetic fixture permissions, proposed OOXML code and final issue resolution were not established; keep those claims zero.'}}
 nodespath=R/'output/20261026_wrd_lineage_v6/controlled/reasoning_resource_nodes.jsonl.gz';nodes={x['node_id']:x for x in rows(nodespath)}
 proposals=[]
 for pid,why in chosen.items():
  o=originals[pid];nids=o['exact_original_lineage_and_current_TRAIN']['original_lineage_record']['resource_node_ids'];ns=[nodes[n] for n in nids]
  g={'historical_original_pair_id':pid,'purpose':'ROOT_FURTHER_SEMANTIC_REVIEW_OF_CURRENT_UNKNOWN_ORIGINAL_R_NOT_ADMISSION',**why,
   'actual_complete_original_pair_and_request':o['actual_original_pair'],'strict_actual_original_request_lineage_and_current_TRAIN':o['exact_original_lineage_and_current_TRAIN'],
   'current_original_R_range_coverage':o['current_R_range_anti_join'],'all_current_precise_character_classifications':[b for b in outblocks if b['pair_id']==pid],
   'original_resource_nodes':ns,'resource_node_ledger_pin':pin(nodespath),'original_scope_review':o['original_scope_review'],
   'old_wrong_repetition_or_peer_removed_ranges_must_not_be_restored_without_new_evidence':True,'source_full_request_kept_asof_not_future_states':True,'positive_loss':0}
  save(out/(pid+'.ROOT_REVIEW.json'),g);proposals.append({'pair_id':pid,'mechanism':why['mechanism'],'file':pin(out/(pid+'.ROOT_REVIEW.json'))})
 save(out/'ORIGINAL_R_ROOT_REVIEW2.json',{'groups':proposals,'new_positive_loss':0,'can_return_zero_new_admissions':True})
 # Four actual later repair actions preserve full evidence and exact legacy
 # ancestry gaps. A source-proven writer does not clear all later observations.
 targets=[('ep_4aadd96d99f2c07543c7',17),('ep_4aadd96d99f2c07543c7',31),('ep_4d412dca2c57480536e7',65),('ep_4d412dca2c57480536e7',83)]
 wanted={e for e,i in targets};ctx={x['episode_id']:x for x in rows(O/'audit_inputs/native1843.contexts.original.jsonl.gz') if x['episode_id'] in wanted}
 ids={tid(e,i) for e,i in targets};owners={x['canonical_owner_id']:x for x in rows(O/'CORPUS_OWNER_COVERAGE.native.jsonl.gz') if x['canonical_owner_id'] in ids};resources=defaultdict(list)
 for x in rows(V9/'outcomes/recomputed_scope_overlay/resource_scope.jsonl.gz'):
  if x['episode_id'] in wanted:resources[x['episode_id']].append(x)
 scopes={x['source_id']:x for x in rows(M/'clean_inputs/source_scope.metadata.jsonl.gz')};repairs=[]
 for eid,i in targets:
  ep=ctx[eid];ms=ep['messages'];oid=tid(eid,i);n=owners[oid];prior=[r for r in resources[eid] if r['observed_after_assistant_message_index']<i]
  unknown=[r for r in prior if r['unknown_reasons'] or r['protected_source_ids'] or any(scopes.get(s,{}).get('status')!='TRAIN' for s in r['source_ids'])]
  feedback=[{'message_index':j,'event_line':ep['source_event_lines'][j],'message':m} for c in calls(ms[i]) for j,m in enumerate(ms) if m.get('toolCallId')==c['id']]
  facts=[];recovered=[]
  if eid.startswith('ep_4aadd') and i==17:
   original=args(calls(ms[7])[0])['content'];lines=original.splitlines(keepends=True);assert lines[1]=='let chromium;\n'
   old="try{chromium=require('playwright');}catch(e){chromium=require('/usr/lib/node_modules/playwright');}"
   assert original.count(old)==1;bad=original.replace(old,"const chromium=require('playwright').chromium;");good=''.join(bad.splitlines(keepends=True)[:1]+bad.splitlines(keepends=True)[2:])
   assert "2:let chromium;\n3:const chromium=require('playwright').chromium;\n4:const b=" in str(ms[16]['content'][0]['text'])
   recovered=[{'path':'/workspace/tmp/test_game.js','version':'ORIGINAL_WRITE7','text':original,'sha256':bh(original.encode())},
    {'path':'/workspace/tmp/test_game.js','version':'AFTER_EXACT_SED15_BEFORE_REPAIR17','text':bad,'sha256':bh(bad.encode())},
    {'path':'/workspace/tmp/test_game.js','version':'AFTER_EXACT_SED17','text':good,'sha256':bh(good.encode())}]
   facts=[{'rule':'ORIGINAL_WRITE7_ACK8_TO_DETERMINISTIC_SED15_AND_ACTUAL_GREP_ERROR16_TO_REPAIR17_ACK18','actual_message_indices':[7,8,15,16,17,18],
    'all_dependencies_in_current_TRAIN_source_or_public_runtime':True,'unproven_external_private_file_needed':False,
    'source_lineage_local_closure_possible_for_this_generated_script':True,'does_not_recover_original_system_or_full_tool_schema':True}]
  g={'canonical_original_target_id':oid,'episode_id':eid,'original_message_index':i,'native_owner':n,'original_complete_context':ep,
   'original_repair_action':ms[i],'actual_repair_feedback':feedback,'observed_resource_ancestors':prior,'legacy_unclosed_resource_nodes':unknown,
   'current_source_scope':{s:scopes[s] for s in n['source_ids']},'locally_reconstructed_exact_versions':recovered,'finite_closure_facts':facts,
   'default_recommendation':'EXPLICIT_NEW_FUNCTIONAL_STATE_WITH_ORIGINAL_ACTION_AUTHOR_AND_CLEAN_MATERIALS_PLUS_LOCAL_QA; NOT_ORIGINAL_FULL_PREFIX_EQUIVALENCE',
   'no_observed_protected_source_is_not_proof_of_complete_closure':True,'positive_loss':0}
  save(out/(oid+'.REPAIR_ANCESTRY.json'),g);repairs.append({'target_id':oid,'episode_id':eid,'message_index':i,'legacy_unclosed_nodes':len(unknown),'file':pin(out/(oid+'.REPAIR_ANCESTRY.json'))})
 save(out/'REPAIR4_ACTUAL_ANCESTRY.json',{'groups':repairs,'new_positive_loss':0})
 print(js({'R_remainder':summary,'R_review2':proposals,'repairs':repairs}))

def finalize():
 """Independent byte/body checks plus append-only reconciliation of baseline01."""
 # No active manifest mutation. Freeze the actual original inputs and compiled
 # views identified in the already-pinned baseline, even if root later grows it.
 baseline=json.loads((O/'BASELINE_MANIFEST_552.json').read_text(encoding='utf-8'));baseqa=json.loads((O/'QA.json').read_text(encoding='utf-8'))
 compiled=[];compileddir=O/'audit_inputs/current552_compiled_objects';compileddir.mkdir(exist_ok=True)
 for ref in baseline['actual_train_files']:
  src=M/ref['path'];assert src.is_file() and sha(src)==ref['sha256'];dst=compileddir/ref['sha256']
  if not dst.exists():shutil.copyfile(src,dst)
  compiled.append({'original_compiled_file':ref,'actual_frozen_copy':pin(dst)})
 save(O/'CURRENT552_COMPILED_SNAPSHOT_INDEX.json',{'baseline_manifest_sha256':baseqa['main_manifest_start_sha256'],'files':compiled,'not_active_reassignment':True})
 # Restore the exact old script bytes recorded in base01 QA, rather than
 # silently pointing that evidence at the now-extended executable source.
 source=Path(__file__).read_text(encoding='utf-8');old=source.split('\ndef reasoning_residual():')[0]
 old=old.replace(" if (O/'BASELINE01_FROZEN_FILES.json').exists():raise RuntimeError('Baseline01 is sealed. Append a new explicit overlay instead of rewriting its old classifications.')\n",'')
 old=old.replace('import argparse,ast,gzip,hashlib,json,shutil,tarfile','import argparse,ast,gzip,hashlib,json,shutil')
 old=old.replace('current_wire=[];wire_sha_to_native={};wire_rid_to_sha={};wire_by_sha={}','current_wire=[];wire_sha_to_native={};wire_rid_to_sha={}')
 old=old.replace('    wire_by_sha[wsha]=current_wire[-1]\n','')
 old=old.replace("  if not raw_ids and resp_sha in wire_by_sha:\n   external.append(('compatible_wire:'+resp_sha,'ACTUAL_COMPATIBLE_WIRE_RESPONSE_WITHOUT_NATIVE_MESSAGE_ID_JOIN'))\n",'')
 old=old.replace("'status':'NOT_A_NATIVE_OWNER_EXPECTED' if v['new_authored_view_does_not_require_original_native_owner'] else", "'status':'NOT_A_NATIVE_OWNER_EXPECTED' if kind=='NEW_AUTHORED_ANNOTATION' else")
 old+="\nif __name__=='__main__':\n p=argparse.ArgumentParser();p.add_argument('--first6',action='store_true');p.add_argument('--full',action='store_true');a=p.parse_args()\n if a.first6:first6()\n if a.full:full()\n"
 assert bh(old.encode())==baseqa['script']['sha256'];history=O/'source_history/corpus_coverage.full01.py';history.write_bytes(old.encode())
 save(O/'source_history/SOURCE_VERSION_ALIASES02.json',{'base01_recorded_original_script_pin':baseqa['script'],'exact_old_source_bytes_recovered':pin(history),
  'current_extended_script':pin(__file__),'old_output_unchanged':True,'same_path_different_code_versions_not_claimed_identical':True})
 # Full original carrier bytes (including non-message native headers/events)
 # are preserved once by SHA in deterministic tar members. No symlinks or
 # arbitrary paths are emitted into these archives.
 eps=list(rows(O/'EPISODE_CAPTURE_COVERAGE.jsonl.gz'));assert len(eps)==1871
 def archive(name,refs,aliases=None,require_all=True):
  path=O/'audit_inputs'/name;unique={r['sha256']:r for r in refs};index=[];unavailable=[];aliases=aliases or {}
  with path.open('wb') as out:
   with gzip.GzipFile(fileobj=out,mode='wb',mtime=0,filename='') as z:
    with tarfile.open(fileobj=z,mode='w|') as tar:
     for digest,ref in sorted(unique.items()):
      p=Path(ref['path']);source_status='ORIGINAL_PATH_PRESENT_EXACT_SHA'
      if not p.is_file() and digest in aliases:p=Path(aliases[digest]['recovered_actual_bytes']['path']);source_status='EXACT_ORIGINAL_SHA_RECOVERED_FROM_PRESERVED_COMPLETE_JSON'
      if not p.is_file():
       unavailable.append({'expected_original_pin':ref,'reason':'ORIGINAL_RAW_PATH_ABSENT_AND_NO_EXACT_BYTE_SHA_RECOVERY','parsed_body_still_preserved':True});continue
      assert p.stat().st_size==ref['bytes'] and sha(p)==digest
      member='objects/'+digest;info=tarfile.TarInfo(member);info.size=ref['bytes'];info.mtime=0;info.mode=0o600
      with p.open('rb') as f:tar.addfile(info,f)
      index.append({'original_source':ref,'archive_member':member,'sha256':digest,'bytes':ref['bytes'],'source_status':source_status})
  # Independent direct tar readback checks every emitted byte stream.
  with tarfile.open(path,'r|gz') as tar:
   found=0
   for member in tar:
    assert member.isfile() and member.name.startswith('objects/') and '/' not in member.name[8:]
    f=tar.extractfile(member);assert f is not None;digest=hashlib.sha256();length=0
    for b in iter(lambda:f.read(1048576),b''):digest.update(b);length+=len(b)
    assert digest.hexdigest()==member.name[8:] and length==unique[digest.hexdigest()]['bytes'];found+=1
   assert found==len(index)
  if require_all:assert not unavailable
  return {'archive':pin(path),'expected_unique_carriers':len(unique),'unique_carriers':len(index),'original_bytes':sum(r['bytes'] for r in index),'members':index,
    'unavailable_original_raw_carriers':unavailable,'all_available_member_SHA_readback_pass':True,'complete_raw_carrier_population':not unavailable}
 native_archive=archive('native1871.carriers.original.tar.gz',[x['source_native'] for x in eps])
 save(O/'NATIVE1871_ORIGINAL_CARRIER_ARCHIVE_INDEX.json',native_archive)
 providers=list(rows(O/'audit_inputs/provider1536.pairs.original.jsonl.gz'));refs=[]
 for p in providers:
  refs.append(p['response_source']);refs.extend(v['source'] for v in p['request_variants'])
 # Some original E paths were retired. Recreate bytes only when a preserved
 # full original JSON serializes to its already-recorded original raw SHA.
 # This is hash-verified byte restoration, not an invented model output.
 wanted={r['sha256']:r for r in refs if not Path(r['path']).is_file()};restored={};restoreout=O/'audit_inputs/exact_JSON_carrier_restoration';restoreout.mkdir(exist_ok=True)
 restore_source=R/'output/20261025_wrd_reasoning_recovery_v4/controlled/raw_pairs.all.jsonl.gz';restorepin=pin(restore_source)
 for row in rows(restore_source):
  for field,body in [('source_request','original_request'),('source_response','original_response')]:
   ref=row.get(field) or {};digest=ref.get('sha256')
   if digest not in wanted or digest in restored:continue
   obj=row.get(body)
   if obj is None:continue
   found=None;recipe=None
   for ascii_mode in [False,True]:
    for indent,separators,sort in [(None,None,False),(2,None,False),(None,(',',':'),False),(None,(',',':'),True),(4,None,False)]:
     text=json.dumps(obj,ensure_ascii=ascii_mode,indent=indent,separators=separators,sort_keys=sort)
     for ending in ['', '\n','\r\n']:
      b=(text+ending).encode()
      if len(b)==wanted[digest]['bytes'] and bh(b)==digest:
       found=b;recipe={'ensure_ascii':ascii_mode,'indent':indent,'separators':separators,'sort_keys':sort,'ending':ending};break
     if found is not None:break
    if found is not None:break
   if found is not None:
    p=restoreout/digest;p.write_bytes(found);restored[digest]={'original_pin':wanted[digest],'recovered_actual_bytes':pin(p),'source_preserved_json_record_file':restorepin,
     'source_record_id':row['id'],'source_json_field':body,'exact_existing_original_SHA_equals_recovered':True,'recipe':recipe,'not_semantic_or_training_admission':True}
 save(O/'EXACT_JSON_CARRIER_RESTORATION.json',{'expected_missing_old_paths':len(wanted),'exact_byte_SHA_restored':len(restored),'restored':list(restored.values()),'not_new_model_sampling':True})
 provider_archive=archive('provider1536.response_and_request_carriers.original.tar.gz',refs,restored,require_all=False)
 save(O/'PROVIDER1536_ORIGINAL_CARRIER_ARCHIVE_INDEX.json',provider_archive)
 # A separate overlay resolves the externally captured length-limited response
 # without inventing a matching native message, and explains 460 new views.
 views=list(rows(O/'CURRENT552_VIEW_COMPONENT_COVERAGE.jsonl.gz'));natives={x['canonical_owner_id']:x for x in rows(O/'CORPUS_OWNER_COVERAGE.native.jsonl.gz')}
 cvid='native_B_phase2_cv_01_0019_4b112905bdd9499fba861f77bb54c7ba';cv=[v for v in views if v['view_id']==cvid];assert len(cv)==1
 wsha='794d8db32034ab731d00048467da9a7cff3be6e3a965912bf04661899b273306';wire=[x for x in rows(O/'CURRENT_COMPAT_WIRE.with_body.jsonl.gz') if x['compatible_response_sha256']==wsha];assert len(wire)==1 and not wire[0]['native_response_id_matches']
 targetR=[t['original_declared_target_message'].get('reasoning_content') for t in cv[0]['positive_target_messages'] if t['original_declared_target_message'].get('reasoning_content')];assert targetR==[wire[0]['parsed_original_response_fields']['reasoning_content']]
 aliases={'baseline_views':552,'native_message_linked_views':58,'historical_external_linked_views':33,'compatible_wire_only_original_R_views':1,'expected_new_authored_without_original_owner':460,
  'partition_sums_to552':58+33+1+460==552,'native_message_original_R_owners':37,'native_compatible_original_R_owners':38,
  'wire_only_alias':{'view_id':cvid,'canonical_original_wire_owner':'compatible_wire:'+wsha,'wire':wire[0],
    'reason':'Real captured completion-prefix R with finish=length; no native responseId message found in registered source. Not missing R and not a reconstructed native message.',
    'complete_original_R_matches_wire':True,'original_R_positive_scoped_tokens':cv[0]['component_tokens']['R']},
  'four_explicit_new_CV_constructions_are_not_native_owner_gaps':[v['view_id'] for v in views if v['bank']=='CV_clean_resource_construction_02'],
  'new_alias_is_not_new_loss':True}
 save(O/'CURRENT552_ALIAS_COMPONENT_OVERLAY02.json',aliases)
 # The separate reviewer proved the actual initial prompt/file/receipt static
 # ancestry of these six sessions. Propagate only that received prefix fact,
 # not an evaluation role or an unproven original226 source ID mapping.
 proofpath=R/'output/20261030_wrd_gap08/reasoning/supplement56/SIX_TASK_SCOPE_PROOFS.json';proof=json.loads(proofpath.read_text(encoding='utf-8'))
 protectedeps={p['episode_id']:p for p in proof['episodes']};assert len(protectedeps)==6 and all(p['first_proven_protected_prefix_message_index']==0 for p in protectedeps.values())
 contexts={}
 for path in [O/'audit_inputs/native1843.contexts.original.jsonl.gz',O/'EXTRA_NATIVE_CONTEXTS.original.jsonl.gz']:
  for ep in rows(path):contexts[ep['episode_id']]=ep
 over=[]
 for n in natives.values():
  if n['episode_id'] not in protectedeps:continue
  p=protectedeps[n['episode_id']];ep=contexts[n['episode_id']];u=ep['messages'][0];assert u['role']=='user';content=u['content'];rg=p['initial_prompt_field_range']
  text=content if isinstance(content,str) else '\n'.join(b['text'] for b in content if b.get('type')=='text')
  assert bh(text[rg['start']:rg['end']].encode())==rg['text_SHA'] and n['source_message_index']>0
  over.append({'canonical_owner_id':n['canonical_owner_id'],'episode_id':n['episode_id'],'original_message_index':n['source_message_index'],
   'old_base01_disposition':n['current_disposition'],'current_disposition':'ISOLATED_PROTECTED_FROZEN_STATIC_EVAL_TASK_PREFIX',
   'actual_protected_observation_index':0,'received_prompt_field_range':rg,'proof_path':str(proofpath),'proof_sha256':sha(proofpath),
   'original226_source_mapping':'UNKNOWN_NOT_INFERRED','not_based_on_role_name':True,'positive_loss':0})
 assert len(over)==73 and all(x['old_base01_disposition']=='UNKNOWN_SUPPLEMENTAL_PREFIX_NOT_AUDITED' for x in over)
 gzwrite(O/'NATIVE73_STATIC_SCOPE_OVERLAY02.jsonl.gz',over)
 # Verify each ledger owner/body and every recovered complete write against
 # the original preserved context, independently of the scope classifier.
 for oid,n in natives.items():
  ep=contexts[n['episode_id']];i=n['source_message_index'];m=ep['messages'][i]
  assert m['role']=='assistant' and tid(n['episode_id'],i)==oid and bh(can(m).encode())==n['original_message_sha256_sorted']
 assert len(natives)==34616 and len(contexts)==1871
 codes=list(rows(O/'RECOVERABLE_COMPLETE_NATIVE_WRITES.with_code.jsonl.gz'))
 for c in codes:
  n=natives[c['canonical_owner_id']];m=contexts[n['episode_id']]['messages'][n['source_message_index']];actual=[a for a in calls(m) if a['id']==c['original_tool_call_id']];assert len(actual)==1
  assert args(actual[0])['content']==c['full_code'] and bh(c['full_code'].encode())==c['original_content_utf8_SHA256']
 labels=list(rows(V9/'outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz'));fixed226={s for x in labels for s in x['original226']};hold12={s for x in labels for s in x['holdout12']}
 scopes={x['source_id']:x for x in rows(M/'clean_inputs/source_scope.metadata.jsonl.gz')};token_counts=Counter();compile_views={};range_count=0
 def compiled_rows(path):
  with gzip.open(path,'rt',encoding='utf-8-sig') as f:
   for line in f:
    if line.strip():yield json.loads(line)
 for ref in compiled:
  for r in compiled_rows(ref['actual_frozen_copy']['path']):
   assert r['id'] not in compile_views;compile_views[r['id']]=r
   spans=r['supervision_spans'];assert sum(b-a for a,b,k,w in spans)==r['supervised_tokens'];token_counts['total']+=r['supervised_tokens']
   last=0
   for a,b,k,w in spans:assert 0<=a<b<=len(r['input_ids']) and a>=last and w>0;token_counts[k]+=b-a;last=b
   for sid in r.get('source_ids',[]):assert sid not in fixed226|hold12 and scopes.get(sid,{}).get('status')=='TRAIN'
   for a in r.get('original_record_metadata',{}).get('approved_field_ranges',[]):
    text=r['messages'][a['message_index']][a['field']][a['start']:a['end']];assert bh(text.encode())==a['text_sha256'];range_count+=1
 assert len(compile_views)==552 and token_counts['total']==150674
 unknowns=Counter(n['current_disposition'] for n in natives.values());unknowns['UNKNOWN_SUPPLEMENTAL_PREFIX_NOT_AUDITED']-=73;unknowns['ISOLATED_PROTECTED_FROZEN_STATIC_EVAL_TASK_PREFIX']=73
 # Snapshot baseline01 pins are never overwritten by sidecar corrections.
 base_names=['CORPUS_OWNER_COVERAGE.native.jsonl.gz','PROVIDER_OWNER_COVERAGE.jsonl.gz','CURRENT552_VIEW_COMPONENT_COVERAGE.jsonl.gz','WITHDRAWN_VIEW_COMPONENT_COVERAGE.jsonl.gz','EXTERNAL_HISTORICAL_OWNER_COVERAGE.jsonl.gz',
  'CURRENT_COMPAT_WIRE.with_body.jsonl.gz','EPISODE_CAPTURE_COVERAGE.jsonl.gz','EXTRA_NATIVE_CONTEXTS.original.jsonl.gz','RECOVERABLE_COMPLETE_NATIVE_WRITES.with_code.jsonl.gz','SEMANTIC_AND_COMPILER_RECEIPTS.original.jsonl.gz','UNJOINED_VIEW_OWNER_CLAIMS.jsonl.gz','CAPTURE_ALIAS_CONFLICTS.json','SUMMARY.json','QA.json','BASELINE_MANIFEST_552.json']
 frozen={'sealed_snapshot':'BASELINE01','files':[pin(O/x) for x in base_names],'original_552_manifest_source_sha256':baseqa['main_manifest_start_sha256'],'no_main_manifest_updated':True}
 seal=O/'BASELINE01_FROZEN_FILES.json'
 if seal.exists():assert json.loads(seal.read_text(encoding='utf-8'))==frozen
 else:save(seal,frozen)
 qa={'status':'PASS_DIRECT_BYTES_FULL_OWNER_BODY_RAW_ARCHIVES_RANGE_ANTI_JOIN_AND_STATIC_SCOPE_OVERLAY',
  'base01_is_sealed_unchanged':True,'native_owner_body_SHA_checks':len(natives),'native_full_original_carrier_archive_members_SHA_readback':1871,
  'provider_full_original_carriers_SHA_readback':provider_archive['unique_carriers'],'provider_raw_carrier_exact_JSON_restorations':len(restored),
  'provider_raw_carriers_still_unavailable':len(provider_archive['unavailable_original_raw_carriers']),'all1536_parsed_original_pairs_preserved':True,
  'all653_full_code_bodies_equal_actual_native_write':len(codes),
  'baseline552_compiled_snapshot_actual_rows':len(compile_views),'baseline_component_token_counts':dict(token_counts),'approved_field_range_SHA_checks':range_count,
  'all_current552_source_ids_nonprotected_and_currentTRAIN':True,'fixed226_count':len(fixed226),'fixedH_count':len(hold12),
  'baseline01_alias_sidecar_partition':{k:v for k,v in aliases.items() if k not in ['wire_only_alias','four_explicit_new_CV_constructions_are_not_native_owner_gaps']},
  'appended_static_scope_overlay_original_owners':73,'current_native_dispositions_after_explicit73_overlay':dict(unknowns),
  'no_new_semantic_or_training_loss_admissions':True,'no_Agent_teacher_or_training_execution':True,'source':pin(__file__)}
 save(O/'DIRECT_QA_AND_OVERLAY02.json',qa);print(js({k:v for k,v in qa.items() if k!='source'}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--first6',action='store_true');p.add_argument('--full',action='store_true');p.add_argument('--reasoning-residual',action='store_true');p.add_argument('--supplement56-index',action='store_true');p.add_argument('--extra-exec6',action='store_true');p.add_argument('--review-slices',action='store_true');p.add_argument('--finalize',action='store_true');a=p.parse_args()

 if a.first6:first6()
 if a.full:full()
 if a.reasoning_residual:reasoning_residual()
 if a.supplement56_index:supplement56_index()
 if a.extra_exec6:extra_exec6()
 if a.review_slices:review_slices()
 if a.finalize:finalize()
