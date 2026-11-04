"""Exact human review and main-positive anti-join for the meeting resource chain."""
from pathlib import Path
from collections import Counter,defaultdict
import importlib.util,json,re

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation10/identity'
s=importlib.util.spec_from_file_location('identity10review',ROOT/'research/data_prep/wrd_curation10/identity_recover.py')
a=importlib.util.module_from_spec(s);s.loader.exec_module(a)

def main():
 assert not (OUT/'MEETING_CHAIN_REVIEW_QA.json').exists()
 inventory=a.load(OUT/'ORIGINAL_ROOT_DISCOVERY.metadata.json')['entries']
 selected=[r for r in inventory if r['task_id']in ['meeting-minutes-formatting_gen_01','meeting-minutes-formatting_gen_02',
   'meeting-minutes-formatting__repair1','meeting-minutes-formatting__repair2']]
 main=a.load(a.MAIN/'TRAINING_MANIFEST.json');source=a.MAIN
 views=list(a.rows(ROOT/'output/20261031_wrd_curation09/process/batch02/coverage_overlay/FINAL_CURRENT_VIEW_COMPONENTS.jsonl.gz'))
 ownerlinks=defaultdict(list);positivecalls=defaultdict(list);positivebody=defaultdict(list)
 for v in views:
  for oid in v['native_owner_links']:ownerlinks[oid].append({'view_id':v['view_id'],'component_tokens':v['component_tokens']})
 for ref in main['actual_train_files']:
  path=source/ref['path'];assert a.digest(path)==ref['sha256']
  for record in a.rows(path):
   for t in record['targets']:
    if not t.get('supervised_tokens'):continue
    if not any(x[2]=='A'and x[3]>0 for x in t.get('owned_supervision_spans',[])):continue
    msg=record['messages'][t['message_index']]
    for call in msg.get('tool_calls',[]):
     positivecalls[call.get('id')].append(record['id'])
     func=call.get('function',{});ar=func.get('arguments',{})
     try:ar=json.loads(ar)if isinstance(ar,str)else ar
     except ValueError:continue
     for field in ['content','command','newText']:
      if isinstance(ar.get(field),str):positivebody[(field,a.h(ar[field]))].append(record['id'])
 report=[]
 for entry in selected:
  eid=entry['episode_id'];d=OUT/'recovered_native'/eid;c=next(a.rows(d/'CONTEXT.original.audit.jsonl.gz'));ms=c['messages']
  user=a.text(next((m for m in ms if m.get('role')=='user'),{}))
  lines=['EXACT ORIGINAL MEETING RESOURCE CHAIN REVIEW — NOT SEMANTIC ADMISSION',
   'episode='+eid,'task='+entry['task_id'],'native_SHA256='+entry['native']['sha256'],
   'No target receives positive loss from this review. Original source identities do not certify upstream scoring/resource ancestry.',
   '\nINITIAL ORIGINAL USER INPUT\n'+user,'\nSTARTUP RESOURCE IDENTITY\n']
  for r in entry['resource_rows']:
   lines.append(a.js({k:r[k]for k in ['native_mount','original_path','startup_current_bytes_match','original_startup_pin','actual_pin_now']}))
  index=[];resourcebody_refs=[];feedback_origins=[]
  # Literal declared-source and external feedback references only; values of
  # protected Q/grades/review paragraphs are not extracted as training labels.
  for rr in entry['resource_rows']:
   p=Path(rr['original_path']);mount=rr['native_mount']or''
   if not rr['startup_current_bytes_match']or not p.is_file():continue
   if p.suffix.lower()not in {'.json','.md','.py','.txt','.yaml','.yml','.jsonl'}:continue
   text=p.read_text(encoding='utf-8-sig',errors='replace')
   ids=sorted(set(re.findall('conv_[0-9a-f]{12}',text)))
   paths=sorted(set(re.findall(r'[DE]:\\[^\r\n"<>]+',text)))
   resourcebody_refs.append({'mount':mount,'actual_pin':rr['actual_pin_now'],'source_id_literals':ids,
     'path_literal_count':len(paths),'all_body_source_id_literals_are_not_actual_private_delivery':True})
   if any(x in mount for x in ['feedback','repair','previous']):
    feedback_origins.append({'mount':mount,'pin':rr['actual_pin_now'],'source_id_literals':ids,'upstream_path_literals':paths,
      'read_as_grades_or_semantic_supervision':False})
  a.save(d/'INPUT_RESOURCE_LITERAL_IDENTITIES.metadata.json',{'resources':resourcebody_refs,'feedback_origins':feedback_origins,
    'this_is_identity_reference_extraction_not_quality_admission':True})
  for i,m in enumerate(ms):
   if m.get('role')!='assistant':continue
   oid=a.h(eid+':'+str(i))[:24];ca=a.calls(m);callids={x.get('id')for x in ca};feedback=[]
   for j,z in enumerate(ms[i+1:],i+1):
    if z.get('role')=='assistant':break
    if z.get('role')=='toolResult'and z.get('toolCallId')in callids:feedback.append({'message_index':j,'event_line':c['source_event_lines'][j],'message':z})
   names=[x.get('name')for x in ca];maincalls=[{'call_id':x.get('id'),'views':positivecalls[x.get('id')]}for x in ca if x.get('id')in positivecalls]
   exactbodies=[]
   for call in ca:
    ar=a.args(call)
    for field in ['content','command','newText']:
     if isinstance(ar.get(field),str)and (field,a.h(ar[field]))in positivebody:
      exactbodies.append({'call_id':call.get('id'),'field':field,'field_sha256':a.h(ar[field]),
         'existing_positive_views':positivebody[(field,a.h(ar[field]))],
         'same_full_body_does_not_assert_all_old_spans_positive':True})
   publictext=a.text(m)
   facts={'owner_id':oid,'message_index':i,'event_line':c['source_event_lines'][i],
    'original_message_sha256_sorted':a.h(a.js(m,True)),'tool_names':names,
    'current_main_owner_links':ownerlinks.get(oid,[]),'current_main_positive_call_ids':maincalls,
    'current_main_positive_target_exact_argument_body_matches':exactbodies,
    'feedback_isError_flags':[z['message'].get('isError')for z in feedback],
    'feedback_exit_codes':[z['message'].get('details',{}).get('exitCode')for z in feedback],
    'feedback_status':[z['message'].get('details',{}).get('status')for z in feedback],
    'ordinary_visible_text_characters':len(publictext),
    'native_thinking_block_count':sum(b.get('type')in {'thinking','reasoning'}for b in a.blocks(m)if isinstance(b,dict)),
    'semantic_correctness_and_full_prefix_ancestry_not_inferred':True}
   exact='\nOWNER '+a.js(facts)+'\nORIGINAL TARGET MESSAGE\n'+json.dumps(m,ensure_ascii=False,indent=2)+\
     '\nIMMEDIATE ACTUAL FEEDBACK — GRADING ONLY, NOT EARLIER INPUT\n'+json.dumps(feedback,ensure_ascii=False,indent=2)+'\n'
   targetpath=d/'target_texts'/f'{i:03d}_{oid}.txt';targetpath.parent.mkdir(exist_ok=True);targetpath.write_text(exact,encoding='utf-8',newline='')
   # Complete code and execution feedback are inline; bulky original read
   # payloads remain exact in their per-target file plus full context.
   include_full=any(n in {'write','edit','apply_patch','exec','process'}for n in names)or not ca
   segment=exact if include_full else '\nOWNER '+a.js(facts)+'\nREAD ORIGINAL TARGET\n'+json.dumps(m,ensure_ascii=False,indent=2)+'\nComplete feedback: '+str(targetpath)+'\n'
   charstart=sum(len(z)+1 for z in lines);lines.append(segment)
   index.append({**facts,'full_target_and_feedback':a.pin(targetpath),'full_in_human_review':include_full,
     'review_unicode_start':charstart,'review_unicode_end':charstart+len(segment)})
  human=d/'REVIEW.txt';human.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='')
  a.save(d/'TARGET_HUMAN_INDEX.json',{'targets':index,'human_review_pin':a.pin(human),
     'read_feedback_preserved_exact_in_per_target_files':True,'code_truncated':False,'training_admitted':0})
  report.append({'episode_id':eid,'task_id':entry['task_id'],'native_new_to_old_1871':entry['is_new_native_entity'],
    'assistant_targets':len(index),'source_ids':entry['source_ids_from_actual_initial_assignment'],
    'source_statuses':entry['current_source_statuses'],'startup_resource_pins_verified':entry['startup_exact_current_files'],
    'startup_resources':entry['startup_resource_files'],'same_owner_positive_views':sum(bool(x['current_main_owner_links'])for x in index),
    'positive_call_ID_overlap_targets':sum(bool(x['current_main_positive_call_ids'])for x in index),
    'positive_exact_argument_body_overlap_targets':sum(bool(x['current_main_positive_target_exact_argument_body_matches'])for x in index),
    'human_review':a.pin(human),'target_index':a.pin(d/'TARGET_HUMAN_INDEX.json'),
    'input_resource_literal_identities':a.pin(d/'INPUT_RESOURCE_LITERAL_IDENTITIES.metadata.json')})
 qa={'status':'PASS_EXACT_MEETING_CHAIN_REVIEW_AND_POSITIVE_ANTI_JOIN_NOT_SEMANTIC_ADMISSION','episodes':report,
   'checkpoint09_sha256':a.digest(a.MAIN/'TRAINING_MANIFEST.json'),'new_training_targets':0,
   'new_business_calls':0,'weights_loaded':False,'training_started':False,'script_pin':a.pin(__file__)}
 a.save(OUT/'MEETING_CHAIN_REVIEW_QA.json',qa)
 print(a.js({k:v for k,v in qa.items()if k!='episodes'}));print(a.js({'episodes':[{k:v for k,v in r.items()if k not in ['human_review','target_index','input_resource_literal_identities']}for r in report]}))

if __name__=='__main__':main()
