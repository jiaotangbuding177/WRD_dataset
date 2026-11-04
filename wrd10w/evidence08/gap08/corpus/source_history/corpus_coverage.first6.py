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
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--first6',action='store_true');a=p.parse_args()
 if a.first6:first6()
