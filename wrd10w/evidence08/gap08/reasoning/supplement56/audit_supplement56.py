"""Offline exact frozen-test prefix audit of56 original wire/native matches.

Protected original reasoning is copied byte-faithfully for audit only. This
program never judges its meaning, cleans it into TRAIN or executes old Agents.
"""
from pathlib import Path
from collections import Counter,defaultdict
import gzip,hashlib,json,importlib.util,re

ROOT=Path('D:/skillloop');OUT=Path(__file__).resolve().parent;CORPUS=ROOT/'output/20261030_wrd_gap08/corpus';RUNS=ROOT/'output/20261020_one_request_wrd';REL=ROOT/'output/20261013_eval250_review/release'
def H(b):return hashlib.sha256(b).hexdigest()
def C(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def J(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def Z(p):
 with gzip.open(p,'rt',encoding='utf-8-sig') as f:
  for l in f:yield json.loads(l)
def P(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':H(b)}
def save(n,d):p=OUT/n;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');return P(p)
def zr(n,rs):
 p=OUT/n
 with p.open('wb') as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as g:
   for r in rs:g.write(json.dumps(r,ensure_ascii=False,separators=(',',':')).encode()+b'\n')
 return P(p)
def text(m):
 c=m.get('content','');return c if isinstance(c,str) else ''.join(x.get('text','') for x in c or [] if isinstance(x,dict) and x.get('type')=='text')
def copy(p,expected=None):
 p=Path(p);b=p.read_bytes();h=H(b)
 if expected:assert h==expected
 q=OUT/'objects'/h
 if not q.exists():q.write_bytes(b)
 return {'original':P(p),'portable':P(q)}
def main():
 OUT.mkdir(exist_ok=True);(OUT/'objects').mkdir(exist_ok=True)
 script=ROOT/'research/data_prep/wrd_gap08/reasoning_recovery.py';sp=importlib.util.spec_from_file_location('own_offline_reasoning_helpers',script);mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
 residual=CORPUS/'reasoning_residual/PROVIDER257_R_RESIDUAL.with_body.jsonl.gz';selected=[r for r in Z(residual) if r['same_response_ID_native_candidates']];assert len(selected)==56
 episode_ids={c['body_ref']['context_episode_id'] for r in selected for c in r['same_response_ID_native_candidates']};contexts_path=CORPUS/'audit_inputs/native1843.contexts.original.jsonl.gz';contexts={r['episode_id']:r for r in Z(contexts_path) if r['episode_id'] in episode_ids};assert len(contexts)==6
 rm=REL/'review_manifest.json';vt=REL/'evaluation_visible/tasks.jsonl';assert P(rm)['sha256']=='5472c17c93a6c68a301f1400a0d7d671c7e28ed51d92705383468d7c2a03ccb4' and P(vt)['sha256']=='960ccfe108260592c2d644237dc7536a66214e188e2dbc2e4b266a8cf5629597';release=J(rm);assert release['status']=='REVIEWED_INPUTS_READY'
 scope_path=ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz';scope={r['source_id']:r for r in Z(scope_path)};taskproof={};prefixrecords=[];bodyrecords=[];carrierpins=[]
 for eid,ctx in contexts.items():
  ns=ctx['source_native'];assert P(ns['path'])==ns;original=Path(ns['path']);base=original.parents[1];q=J(base/'request.json');receipt=J(base/'delivery_receipt.json');tid=q['task_id'];tp=REL/'evaluation_visible/tasks'/tid/'task.json';task=J(tp)
  assert tid in ['T0112','T0145'] and q['input']==task['prompt'] and receipt['release_manifest_sha256']==P(rm)['sha256'] and receipt['visible_tasks_sha256']==P(vt)['sha256'] and receipt['single_dispatch_sha256']==H(task['prompt'].encode())
  ms=ctx['messages'];initial=text(ms[0]);start=initial.index(task['prompt']);assert ms[0]['role']=='user' and initial.count(task['prompt'])==1
  inputs=[]
  for a,b,d in zip(q['resources'],task['inputs'],receipt['copied_inputs']):
   assert a['name']==b['name']==d['name'] and a['sha256']==b['sha256']==d['sha256'];rp=Path(a['path']);releasep=REL/'evaluation_visible'/b['path'];assert P(rp)['sha256']==P(releasep)['sha256']==b['sha256'] and rp.stat().st_size==b['bytes'];inputs.append({'name':a['name'],'release_input':P(releasep),'actual_episode_input':P(rp),'identity':'EXACT_FROZEN_TEST_INPUT','body_semantically_read':False})
  assert len(inputs)==len(q['resources'])==len(task['inputs'])==len(receipt['copied_inputs'])==1
  reads=[]
  for i,m in enumerate(ms):
   if m.get('role')!='assistant':continue
   for call in mod.calls(m):
    name=call['name'];a=mod.args(call);path=a.get('path') if isinstance(a,dict) else None
    if name!='read' or not path:continue
    observations=[(j,z) for j,z in enumerate(ms) if j>i and z.get('role')=='toolResult' and z.get('toolCallId')==call['id']]
    if not observations:continue
    j,obs=observations[0];body=text(obs);record={'call_index':i,'call_id':call['id'],'actual_path':path,'observation_index':j,'observation_SHA':H(C(obs)),'observation_text_SHA':H(body.encode()),'observation_text_characters':len(body),'isError':bool(obs.get('isError')),'mount_alone_not_counted_as_read':True,'proven_package_file':None}
    for sk in q.get('learned_skills',[]):
     prefix='/workspace/learned_skills/'+sk['id']+'/'
     if path.startswith(prefix):
      relative=path[len(prefix):];hp=Path(sk['path'])/relative
      if hp.is_file() and relative in sk['files'] and H(hp.read_bytes())==sk['files'][relative] and hp.read_bytes().replace(b'\r\n',b'\n')==body.encode() and not obs.get('isError'):
       record['proven_package_file']={'skill_id':sk['id'],'relative':relative,'physical':P(hp),'actual_observed_same_file_bytes_CRLF_to_LF':True,'upstream_business_source_not_inferred_from_task_or_package_name':True}
    reads.append(record)
  proof={'episode_id':eid,'job':base.name,'task_id':tid,'frozen_review_manifest':P(rm),'frozen_visible_tasks':P(vt),'original_request':copy(base/'request.json'),'actual_delivery_receipt':copy(base/'delivery_receipt.json'),'frozen_task':copy(tp),'native':copy(original,ns['sha256']),'initial_user_SHA':H(C(ms[0])),'initial_prompt_field_range':{'message_index':0,'field':'content','start':start,'end':start+len(task['prompt']),'text_SHA':H(task['prompt'].encode())},'actual_inputs':inputs,'explicit_original_native_read_edges':reads,'first_proven_protected_prefix_message_index':0,'classification':'PROTECTED_FROZEN_EVAL250_TEST_TASK','original226_source_mapping':'UNKNOWN_NOT_INFERRED_FROM_TASK_ID_OR_EVALUATION_ROLE','static_boundary':'Existing frozen evaluation-task/resource isolation, confirmed by root; not a new arbitrary exclusion','all_original_messages_preserved_in_companion_context':True,'source_scope_pin':P(scope_path),'possible_T0112_generation_source_metadata_only':{'source_id':'conv_db903c616f0e','current_status':scope['conv_db903c616f0e']['status'],'proven_maker_to_consumed_package_producer_edge':False,'not_used_as_exclusion_proof':True} if tid=='T0112' else None,'positive_training_loss':0}
  taskproof[eid]=proof;carrierpins.append(proof);prefixrecords.append(ctx)
 rows_out=[];raw_R_chars=0;exact_request_count=0;exact_full_output_count=0;visible_transform_holds=[]
 for r in selected:
  assert len(r['same_response_ID_native_candidates'])==1;c=r['same_response_ID_native_candidates'][0];eid=c['body_ref']['context_episode_id'];i=c['body_ref']['message_index'];ctx=contexts[eid];m=ctx['messages'][i];pair=r['original_provider_pair'];assert m['responseId']==r['provider_response_id']==pair['provider_response_id'] and i>0
  raw_source=pair['response_source'];capture=copy(raw_source['path'],raw_source['sha256']);data=mod.parse_sse(Path(raw_source['path']).read_bytes());assert data['ids']==[r['provider_response_id']]
  original_R=pair['response'].get('reasoning_content','');assert original_R==data['reasoning_text'];raw_R_chars+=len(original_R)
  fulloutput=text(m)==data['content_text'];native_calls=mod.calls(m);fulloutput=fulloutput and len(native_calls)==len(data['tool_calls'])
  for x,y in zip(native_calls,data['tool_calls']):fulloutput=fulloutput and x['id']==y['id'] and x['name']==y['name'] and mod.args(x)==json.loads(y['arguments'])
  if fulloutput:exact_full_output_count+=1
  else:visible_transform_holds.append({'provider_response_id':r['provider_response_id'],'episode_id':eid,'message_index':i,'native_visible_text_characters':len(text(m)),'wire_visible_text_characters':len(data['content_text']),'native_visible_text_SHA':H(text(m).encode()),'wire_visible_text_SHA':H(data['content_text'].encode()),'decision':'HOLD_NATIVE_VISIBLE_TEXT_TRANSFORM_NOT_EXACT; sameID is not complete-response causality proof','protected_task_scope_does_not_require_response_equivalence':True})
  reqproof=[]
  for q in pair['request_variants']:
   p=Path(q['source']['path']);assert P(p)==q['source'];actual=J(p);assert actual['messages']==q['messages'] and actual.get('tools',[])==q.get('tools',[])
   hits=[]
   for j,z in enumerate(actual['messages']):
    if z.get('role')=='user' and taskproof[eid]['initial_prompt_field_range']['text_SHA']==H(J(Path(taskproof[eid]['frozen_task']['original']['path']))['prompt'].encode()):
     prompt=J(Path(taskproof[eid]['frozen_task']['original']['path']))['prompt'];t=text(z)
     if prompt in t:hits.append({'request_message_index':j,'field':'content','start':t.index(prompt),'end':t.index(prompt)+len(prompt),'prompt_SHA':H(prompt.encode())})
   assert hits;exact_request_count+=1;reqproof.append({'actual_request':copy(p,q['source']['sha256']),'full_original_messages_and_tools_exactly_equal_saved_pair':True,'frozen_protected_prompt_occurrences':hits})
  reads=[x for x in taskproof[eid]['explicit_original_native_read_edges'] if x['observation_index']<i]
  rows_out.append({'provider_response_id':r['provider_response_id'],'canonical_native_owner_id':c['owner_id'],'episode_id':eid,'message_index':i,'source_native':c['source_native'],'classification':'PROTECTED_FROZEN_EVAL250_TEST_TASK','initial_exposure_at0_strictly_before_target':True,'original226_source_mapping':'UNKNOWN_NOT_INFERRED','provider_raw_original_capture':capture,'request_proofs':reqproof,'actual_original_response_message':pair['response'],'original_R_field':'reasoning_content','original_R_characters':len(original_R),'original_R_SHA':H(original_R.encode()),'original_R_frames':data['original_R_frame_spans'],'reasoning_origin':'ORIGINAL_COMPAT_REASONING_CONTENT; ACP_THOUGHT_VS_PROGRESS_NOT_UNIFORMLY_TYPED','actual_full_native_output_and_all_tool_ids_names_args_match':fulloutput,'R_as_complete_native_same_response_attribution':fulloutput,'actual_original_native_target':m,'native_prefix_range':{'context_episode_id':eid,'start_message_index':0,'end_exclusive':i,'companion_context_file':'SIX_NATIVE_CONTEXTS.original.audit.jsonl.gz'},'actual_explicit_read_observations_before_target':reads,'actual_next_observation_audit_only':ctx['messages'][i+1] if i+1<len(ctx['messages']) else None,'original_thought_content_semantically_reviewed':False,'new_original_R_missing_data_increment_credit':False,'positive_loss':0,'TRAIN_admission':False})
 zr('SIX_NATIVE_CONTEXTS.original.audit.jsonl.gz',prefixrecords);zr('RECORDS56.with_original_R_and_exact_prefix_refs.audit.jsonl.gz',rows_out);save('SIX_TASK_SCOPE_PROOFS.json',{'episodes':carrierpins,'classification_policy':'Existing static evaluation isolation applies to exact frozen eval250 test prompts/resources; original226 mapping remains unknown.'})
 report={'schema':'wrd-gap08-supplement56-exact-static-scope-and-original-R-audit-v1','status':'ALL56_PROVEN_PROTECTED_FROZEN_EVAL250_TEST_TASK_AUDIT_ONLY','provider_records':56,'native_episodes':6,'original_R_characters_preserved_with_original_raw_frames':raw_R_chars,'full_response_and_all_tool_ID_name_arguments_exact_matches':exact_full_output_count,'visible_text_transformation_unresolved_native_pairs':visible_transform_holds,'actual_raw_request_message_tools_exact_variants':exact_request_count,'prompt_and_input_identity_protected_before_all_targets':True,'original226_source_mapping':'UNKNOWN_FOR_BOTH_TASKS; not fabricated','new_TRAIN_eligible_original_R':0,'positive_loss':0,'cleaned_by_response_ID_or_success_or_evaluation_role':False,'no_protected_R_meaning_review_or_teacher_synthesis':True,'no_old_Agent_or_program_execution':True,'new_business_Teacher_Actor_calls':0,'AI_curation_and_CPU_cost':'UNKNOWN_NOT_ZERO','immutable_inputs':[P(residual),P(contexts_path),P(scope_path)],'helper_script':P(script),'script':P(__file__),'per_episode_counts':dict(Counter(x['episode_id'] for x in rows_out))}
 save('REPORT.json',report);save('MANIFEST.json',{'files':[P(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'],'role':'PROTECTED_AUDIT_ONLY_NO_TRAINING'});print(json.dumps(report))

if __name__=='__main__':main()
