"""Independent byte/schema/causal-input check of the scoped resource export.

No code-under-test is run. This validates candidate source/argument logic,
not root semantic admission, tokenizer masks, skill utility or native ancestry.
"""
from pathlib import Path
import copy,gzip,hashlib,json
from jsonschema import Draft202012Validator
ROOT=Path('D:/skillloop');MAIN=ROOT/'output/20261027_wrd_main_v10'
OUT=ROOT/'output/20261031_wrd_curation10/resource_review10/meeting_gen01'
HIST=Path('E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/native_episodes/meeting-minutes-formatting_gen_01/workspace')
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(l) for l in gzip.open(p,'rt',encoding='utf-8-sig') if l.strip()]
def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def main():
 candidates=rows(OUT/'CANDIDATES.raw.jsonl.gz');assert len(candidates)==6
 byid={r['id']:r for r in candidates};assert len(byid)==6
 timeline=load(OUT/'TIMELINE.original.audit.json')
 pool={r['source_id']:r for r in rows(MAIN/'clean_inputs/source_pool.with_body.jsonl.gz')}
 scopes={r['source_id']:r for r in rows(MAIN/'clean_inputs/source_scope.metadata.jsonl.gz')}
 cap=MAIN/'historical_v6_native_repair_01/TOOLS_CAPTURE_53.json';actual=load(cap)
 registry={t['function']['name']:t['function'] for t in actual['tools']}
 newheld=load(ROOT/'output/20261031_wrd_curation10/parent_inputs/reservation.json')['reserved_source_ids']
 oldheld=load(ROOT/'output/20261031_wrd_curation09/holdout/holdout_reservation.json')['reserved_source_ids']
 styles=load(OUT/'RESOURCE_SEMANTIC_REVIEW.json')['source_user_style_evidence']
 for e in styles:
  got=[u for u in pool[e['source_id']]['user_messages'] if u['id']==e['message_id']]
  assert len(got)==1 and got[0]['content']==e['original_content'] and sha(got[0]['content'])==e['body_sha256']
 checked=[]
 for r in candidates:
  assert r['source_admission']=='ADMIT' and r['requires_external_root_admission'] and not r['root_main_admission']
  assert r['split']=='train' and all(scopes[s]['status']=='TRAIN' for s in r['source_ids'])
  assert not set(r['source_ids'])&set(oldheld+newheld)
  assert not r['actual_native_tool_dispatch'] and not r['old_prefix_promoted_or_claimed_clean']
  assert not r['original_native_request_equivalence_claimed'] and not r['teacher_original_R_supervised']
  assert r['historical_prefix_ancestry_status'].startswith('UNKNOWN')
  assert r['loss_multiplier']==0.25 and not r['future_feedback_in_model_input']
  assert not r['is_full_autonomous_execution_demonstration'] and not r['is_qualified_KEEP_demonstration']
  assert not r['training_started'] and not r['model_weights_loaded']
  i=r['supervision_message_indices'][0];assert r['message_loss_mask']==[0]*i+[1]
  assert i==len(r['messages'])-1
  call=r['messages'][i]['tool_calls'][0];assert len(r['messages'][i]['tool_calls'])==1
  name=call['function']['name'];args=call['function']['arguments'];assert isinstance(args,dict)
  assert not list(Draft202012Validator(registry[name]['parameters']).iter_errors(args))
  assert all(t['function']==registry[t['function']['name']] for t in r['tools'])
  assert sha(cap.read_bytes())==r['tool_schema_provenance']['sha256']
  assert call['id']==r['target_tool_call_id']
  target_body=args.get('content',args.get('command'))
  if target_body is not None:assert sha(target_body)==r['target_original_code_sha256']
  ex=sorted(r['target_code_unicode_exclusions'],key=lambda x:x['start'])
  for x in ex:assert 0<=x['start']<x['end']<=len(target_body) and sha(target_body[x['start']:x['end']])==x['text_sha256']
  assert all(a['end']<=b['start'] for a,b in zip(ex,ex[1:]))
  # Every future result remains unrendered metadata. No repaired QA score or
  # universal pass statement was introduced before the repair action.
  content='\n'.join(m.get('content','') for m in r['messages'] if isinstance(m.get('content',''),str))
  assert '14/14' not in content and 'curator_fixed01/CPU_QA.json' not in content
  if 'new-fixed' in r['id']:
   assert r['messages'][i]['reasoning_content'] and r['rationale_provenance']=='NEW_CURATOR_CONCISE_REPAIR_EXPLANATION'
  else:assert not r['messages'][i]['reasoning_content']
  checked.append({'id':r['id'],'target_tool':name,'negative_ranges':len(ex),
   'new_state_sources_TRAIN_known_scope_only':True,'target_schema_valid':True,
   'original_ancestor_unknown_preserved':True,'future_feedback_not_rendered':True})
 original=byid['resource10-meeting-original27-partial'];call=original['messages'][-1]['tool_calls'][0]
 assert call['function']['arguments']==timeline[27]['calls'][0]['arguments']
 assert '普通DOCX段落' in original['messages'][1]['content']
 assert len(original['target_code_unicode_exclusions'])==4
 for label,index in [('original54-report-edit',54),('original58-runner-exec',58)]:
  r=byid['resource10-meeting-'+label]
  assert r['messages'][-1]['tool_calls'][0]['function']['arguments']==timeline[index]['calls'][0]['arguments']
 r=byid['resource10-meeting-reconciled37-shell-retry']
 assert r['messages'][-1]['tool_calls'][0]['function']['arguments']['command']==timeline[37]['calls'][0]['arguments']['command'].replace('SKILL=…kill','SKILL=/workspace/outputs/candidate/skill')
 assert r['messages'][2]['tool_calls'][0]['function']['arguments']==timeline[35]['calls'][0]['arguments']
 assert r['messages'][3]['role']=='tool' and r['messages'][3]['content']==timeline[36]['text']
 r=byid['resource10-meeting-reconciled56-runner-write'];body=r['messages'][-1]['tool_calls'][0]['function']['arguments']['content']
 assert body.encode()==(HIST/'tmp/run_cases.sh').read_bytes()
 assert body==timeline[56]['calls'][0]['arguments']['content'].replace('SKILL=…kill','SKILL=/workspace/outputs/candidate/skill')
 repaired=byid['resource10-meeting-new-fixed-formatter']['messages'][-1]['tool_calls'][0]['function']['arguments']['content']
 assert repaired.encode()==(OUT/'new_curator_resources/apply_minutes_format.py').read_bytes()
 # Preserve final module version identity without source execution.
 edit=timeline[54]['calls'][0]['arguments']['edits'][0]
 code=timeline[27]['calls'][0]['arguments']['content']
 assert code.count(edit['oldText'])==1
 assert code.replace(edit['oldText'],edit['newText']).encode()==(HIST/'outputs/candidate/skill/scripts/apply_minutes_format.py').read_bytes()
 result={'schema':'wrd10-meeting-resource-source-artifact-QA-v1','status':'PASS_SOURCE_BYTES_ARGUMENT_SCHEMA_AND_NEW_STATE_CAUSAL_BOUNDARY_ONLY',
  'candidates':6,'checks':checked,'source_user_style_occurrences_checked':len(styles),
  'all_actual_target_call_arguments_schema_valid':True,'all_negative_code_spans_SHA_exact_nonoverlapping':True,
  'initial27_plus_edit54_equals_final5148_bytes':True,'reconciled56_equals_archived_runner3694_bytes':True,
  'original_event_abbreviations_not_mislabeled_as_verbatim_API':True,
  'old_original_prefix_route_card_ancestry_is_not_proven':True,
  'original_variant_capability_scope':'Plain top-level runs with recognized Heading styles only. No original-version hyperlink fonts or Title/Subtitle support promised; indent/strip failures explicitly masked.',
  'new_repair_capability_scope':'DOCX XML and visible text checked locally. No font installation/render, business factual correctness, independent Q or skill utility claimed.',
  'new_diagnostic_fixture_author':'Curator, not historical Teacher or business sources',
  'independence_limit':'This script is separate from candidate assembly but same resource-review agent. Root semantics and independent tokenizer/mask verification still required.',
  'new_Agent_model_native_or_training':False,'candidate_file':pin(OUT/'CANDIDATES.raw.jsonl.gz'),'QA_script':pin(Path(__file__))}
 p=OUT/'SOURCE_ARTIFACT_QA.json';p.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({'status':result['status'],'candidates':6,'source_artifact_QA':pin(p)},ensure_ascii=False))
if __name__=='__main__':main()
