"""Offline exact ancestry and outcome audit. Never executes historical programs.

All outputs are audit-only. Source-protected material is not turned into labels.
"""
from pathlib import Path
from collections import Counter
import copy, gzip, hashlib, json, re

ROOT=Path('D:/skillloop'); OUT=Path(__file__).resolve().parent
BASE=ROOT/'output/20261029_wrd_v9_missing_evidence_recovery'
V9=ROOT/'output/20261026_wrd_dataset_v9'
NATIVE=Path('E:/skillloop_runs/w9/native_episodes/scheduled-task-config__make1')
PROD=Path('E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/native_episodes/route_batch_007')
REC=ROOT/'output/20261021_pipeline_infra_audit/route_recovery/batch_007/card_02'
LIB=ROOT/'output/20261021_workflow_library_v9'
EID='ep_04149c237fc7afb2bd67'

def h(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def j(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(v) for v in gzip.open(p,'rt',encoding='utf-8-sig')]
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':h(b)}
def save(n,d):p=OUT/n;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');return pin(p)
def write_rows(n,rs):
    with (OUT/n).open('wb') as f:
        with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as z:
            for d in rs:z.write(json.dumps(d,ensure_ascii=False,separators=(',',':')).encode()+b'\n')
    return pin(OUT/n)
def messages(p):
    return [{'event_line':i,'message':v['message']} for i,v in enumerate((json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines()),1) if isinstance(v.get('message'),dict)]
def text(m):
    c=m.get('content');return c if isinstance(c,str) else '\n'.join(x.get('text','') for x in c or [] if isinstance(x,dict) and x.get('type')=='text')
def calls(m):return [x for x in m.get('content',[]) if isinstance(x,dict) and x.get('type')=='toolCall']

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cohort=next(x for x in rows(BASE/'MAKE_100_EPISODE_CLUSTERS.metadata.jsonl.gz') if x['episode_id']==EID)
    scope={x['source_id']:x for x in rows(ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz')}
    targets={x['id']:x for x in rows(BASE/'HOLD_TARGETS_9096.metadata.jsonl.gz') if x['episode_id']==EID}
    native=NATIVE/'openclaw_transport/session_events.jsonl'; nm=messages(native)
    assert pin(native)['sha256']==cohort['source_native']['sha256']
    assert len(nm)==116
    prodnative=PROD/'openclaw_transport/session_events.jsonl'; pm=messages(prodnative)
    assert len(pm)==12
    compact=PROD/'workspace/inputs/compact_proposals.json'
    # Capture normalizes CRLF to LF. Preserve both actual byte identities.
    observed=text(pm[4]['message']); assert j(compact)==json.loads(observed)
    assert compact.read_bytes().replace(b'\r\n',b'\n')==observed.encode()
    pc=calls(pm[3]['message'])[0]; assert pc['name']=='read' and pc['arguments']['path']=='/workspace/inputs/compact_proposals.json'
    ids=sorted(set(re.findall(r'conv_[a-f0-9]{12}',observed)))
    statuses={s:scope.get(s,{}).get('status','MISSING_CURRENT_SOURCE_SCOPE') for s in ids}
    protected=[s for s,st in statuses.items() if st.startswith('HOLD_')]
    assert set(protected)=={'conv_1caa4df498cc','conv_f8a56f4505e3','conv_f9a02361c038'}
    wc=calls(pm[7]['message'])[0]; output=PROD/'workspace/outputs/cards.json'
    assert wc['name']=='write' and wc['arguments']['path']=='/workspace/outputs/cards.json'
    assert wc['arguments']['content'].encode()==output.read_bytes()
    assert pm[8]['message']['toolCallId']==wc['id'] and not pm[8]['message']['isError']
    raw=j(REC/'raw_card.json'); actual=next(x for x in j(output)['cards'] if x['id']=='scheduled-task-config')
    assert actual==raw
    checked=j(ROOT/'output/20261021_workflow_library_parallel4_recovery1/route_reviews/batch_007/checked_cards.json')
    assert checked['holds'][1]['raw_card']==raw
    derived=j(REC/'derived_card.json'); expected=copy.deepcopy(raw)
    for v in j(REC/'audit.json')['transformations']:
        assert v['operation']=='copy_existing_exact_step_reference_to_top_level'
        expected['source_evidence'].append(v['value'])
    assert expected==derived
    route=NATIVE/'workspace/inputs/route_card.json'; routejson=j(route)
    assert set(routejson)-set(derived)=={'merge_context','candidate_gate'}
    assert all(routejson[k]==v for k,v in derived.items())
    task=NATIVE/'workspace/inputs/new_route/task.json'; taskjson=j(task)
    assert taskjson['value_gate_is_hypothesis_not_benefit']['value_plan']==raw['value_plan']
    assert text(nm[4]['message']).encode()==task.read_bytes()
    assert calls(nm[3]['message'])[0]['arguments']['path']=='/workspace/inputs/new_route/task.json'
    assert text(nm[6]['message']).encode()==route.read_bytes()
    ancestry={'schema':'wrd-scheduled-actual-protected-card-producer-v1',
      'status':'PROVEN_PROTECTED_DERIVATION_AUDIT_ONLY',
      'producer_native':pin(prodnative),'producer_missing_from_prior_v9_episode_table':not any(x['source_native']['sha256']==pin(prodnative)['sha256'] for x in rows(V9/'recovery/episodes.metadata.jsonl.gz')),
      'actual_producer_input':{'file':pin(compact),'read_message_index':3,'read_event_line':pm[3]['event_line'],'tool_call_id':pc['id'],'observation_message_index':4,'observation_event_line':pm[4]['event_line'],'actual_observation_bytes':len(observed.encode()),'actual_observation_sha256':h(observed.encode()),'physical_CRLF_to_actual_LF_exact':True,'JSON_value_equal':True,'visible_source_count':len(ids),'visible_source_statuses':statuses,'proven_protected_or_shared_sources':protected,'protected_business_bodies_printed_or_reused_as_new_labels':False},
      'actual_producer_output':{'file':pin(output),'write_message_index':7,'write_event_line':pm[7]['event_line'],'tool_call_id':wc['id'],'content_equals_frozen_output_bytes':True,'actual_ack_message_index':8,'actual_ack_event_line':pm[8]['event_line'],'actual_ack_sha256':h(text(pm[8]['message']).encode()),'selected_card_JSON_equals_original_raw_card':True},
      'mechanical_derivation':{'raw_card':pin(REC/'raw_card.json'),'checked_cards':pin(ROOT/'output/20261021_workflow_library_parallel4_recovery1/route_reviews/batch_007/checked_cards.json'),'raw_card_exact_pointer':'/holds/1/raw_card','audit':pin(REC/'audit.json'),'derived_card':pin(REC/'derived_card.json'),'only_two_existing_step_references_appended_to_top_level':True,'input_route_card_preserves_all_derived_fields':True,'additional_route_fields':['merge_context','candidate_gate'],'task_value_plan_equals_protected_original_value_plan':True,'route_merge_may_add_additional_ancestors_but_cannot_remove_this_proof':True},
      'actual_downstream_receipt':{'native':pin(native),'first_proven_exposure':{'input_file':pin(task),'read_message_index':3,'observation_message_index':4,'observation_event_line':nm[4]['event_line'],'actual_full_observation_exactly_equals_file':True,'value_plan_JSON_sha256':h(canon(raw['value_plan']))},'second_confirming_route_read':{'input_file':pin(route),'read_message_index':5,'observation_message_index':6,'actual_full_observation_exactly_equals_file':True}},
      'impact':{'candidate_targets':56,'all_target_indices_strictly_after_first_exposure':all(i>4 for i in cohort['target_message_indices']),'target_ids':cohort['held_target_ids'],'new_training_targets':0,'positive_loss':0,'scope':'Only 56 fixed planned targets; do not retroactively mark earlier read3 as exposed or rewrite entire business-source scope.'},
      'original226_isolation_preserved':True,'new_model_calls':0,'training_started':False}
    ancestry_pin=save('ANCESTRY_PROOF.json',ancestry)
    # Preserve exact original carriers. No private config, key, SQLite or SDK traces.
    originals=[native,Path(cohort['source_native']['path']),prodnative,compact,output,REC/'audit.json',REC/'raw_card.json',REC/'derived_card.json',task,route,
      NATIVE/'response.json',NATIVE/'openclaw_transport/response.json',NATIVE/'metering/scheduled-task-config__make1.native.jsonl',
      LIB/'w/scheduled-task-config/r1/evaluation.json']
    originals += [p for p in (NATIVE/'workspace/inputs').rglob('*') if p.is_file() and p.suffix.lower() in {'.json','.md','.py'}]
    originals += [p for p in (NATIVE/'workspace/outputs').rglob('*') if p.is_file() and p.suffix.lower() in {'.json','.md','.py'}]
    originals += [p for p in (NATIVE/'openclaw_transport/evidence').iterdir() if p.is_file() and p.suffix.lower() in {'.json','.jsonl','.txt'}]
    rep=Path('E:/skillloop_runs/w9/rep/scheduled-task-config/r1/check/runs/run_01')
    originals += [p for p in rep.rglob('*') if p.is_file() and p.suffix.lower() in {'.json','.stdout','.stderr'}]
    versions=[];seen={};(OUT/'objects').mkdir(exist_ok=True)
    for p in dict.fromkeys(originals):
        b=p.read_bytes();s=h(b);dest=OUT/'objects'/s
        if not dest.exists():dest.write_bytes(b)
        assert h(dest.read_bytes())==s
        versions.append({'original':pin(p),'portable_exact_object':pin(dest),'role':'PROTECTED_ANCESTRY_AUDIT_ONLY_NO_POSITIVE_LOSS'})
        seen[s]=dest
    preserved=save('PRESERVED_OBJECTS.json',{'schema':'wrd-scheduled-explicit-audit-object-allowlist-v1','references':versions,'unique_objects':len(seen),'positive_loss':0})
    canonical_episode=next(x for x in rows(ROOT/'output/20261025_wrd_training_dataset/bundle/canonical/native_episodes.jsonl.gz') if x['episode_id']==EID)
    targetrows=[];events=[]
    for tid in cohort['held_target_ids']:
        t=targets[tid];i=t['source_message_index'];m=nm[i]['message']
        cm=canonical_episode['messages'][i]
        assert h(json.dumps(cm,ensure_ascii=False,separators=(',',':')).encode())==t['source_message_sha256']
        assert cm['content']==m['content'] and cm['role']==m['role']
        cs=calls(m);nxt=nm[i+1] if i+1<len(nm) else None
        targetrows.append({'schema':'wrd-audit-full-original-target-v1','id':tid,'episode_id':EID,'route_id':'scheduled-task-config','source_event_line':nm[i]['event_line'],'source_message_index':i,'source_message_sha256':t['source_message_sha256'],
          'messages_original_prefix':[x['message'] for x in nm[:i]],'target_original_unmodified':m,'actual_next_observation_audit_only_not_input':nxt,
          'original_native_message_canonical_sorted_sha256':h(canon(m)),'old_source_message_sha256_names_reduced_canonical_message_not_full_native_message':True,
          'native_source':pin(native),'portable_native_object':pin(OUT/'objects'/pin(native)['sha256']),
          'source_status':'HOLD_PROTECTED_DERIVED','proof':ancestry_pin,'positive_loss':0,'training_admitted':False,
          'reason':'Received exact value_plan derived from mixed protected/static/shared source producer at observation4 before this target. Four selected TRAIN source tags do not remove ancestor exposure.',
          'semantic_correctness':'NOT_GRANTED_BY_SUCCESS_OR_PROTECTED_LINEAGE','original_reasoning_unmodified':True})
        for c in cs:
            a=c.get('arguments',{});a=json.loads(a) if isinstance(a,str) else a
            rec={'target_id':tid,'message_index':i,'event_line':nm[i]['event_line'],'tool_call_id':c['id'],'tool':c['name'],'argument_sha256':h(canon(a)),'next_observation_message_index':i+1 if nxt else None,'next_observation_event_line':nxt['event_line'] if nxt else None,'next_observation_sha256':h(canon(nxt['message'])) if nxt else None,'source_status':'HOLD_PROTECTED_DERIVED','positive_loss':0}
            if c['name']=='write':
                rec.update(write_native_path=a.get('path'),write_content_sha256=h(a.get('content','').encode()),write_content_UTF8bytes=len(a.get('content','').encode()),ack_same_tool_call=bool(nxt and nxt['message'].get('toolCallId')==c['id']),ack_is_error=nxt['message'].get('isError') if nxt else None)
            events.append(rec)
    targetpin=write_rows('TARGETS.with_body.audit.jsonl.gz',targetrows)
    eventpin=save('ACTUAL_CALL_OBSERVATION_VERSION_EDGES.json',{'schema':'wrd-scheduled-actual-call-version-edges-v1','records':events,'target_count':56,'actual_write_events':sum(e['tool']=='write' for e in events),'no_agent_or_program_executed':True,'training_admitted':False})
    report=j(rep/'reproduction_report.json');ev=j(LIB/'w/scheduled-task-config/r1/evaluation.json')
    cases=[{'program':p['path'],**{k:c.get(k) for k in ['id','kind','status','reasons','returncode','full_input','full_output','public_usage_executed','actual_argv']}} for p in report['programs'] for c in p['cases']]
    assert len(cases)==4 and cases[0]['status']=='HOLD' and cases[0]['actual_argv'] is None
    outcome=save('VERSION_OUTCOME_AUDIT.json',{'schema':'wrd-scheduled-version-outcome-audit-v1','same_version_program_SHA256s':report['package_sha256'],
      'native_self_report':{'message_index':99,'claim_text_sha256':h(text(nm[99]['message']).encode()),'claim':'Seven cases passed; update preserves delivery. This is a historical claim, not blanket correctness.'},
      'actual_make_execution_observations':{'message96':'set -e exited code2 at expected invalid case, after normal/update/boundary exit0','message98':'later actual rerun reports invalid2, list-normal0/list-boundary0/list-invalid2; full actual outputs preserved in original carrier'},
      'independent_resource_reproduction':{'file':pin(rep/'reproduction_report.json'),'evaluation':pin(LIB/'w/scheduled-task-config/r1/evaluation.json'),'status':report['status'],'reasons':report['reasons'],'evaluation_status':ev['status'],'evaluation_reasons':ev['reasons'],'complete_reproduction':report['complete_reproduction'],'documented_usage_verified':report['documented_usage_verified'],'cases':cases,
        'specific_gap':'Public example uses {INPUT}/task_spec.json, which was not supplied; corresponding actual_argv and returncode are null. Other update/boundary/invalid actual cases pass. This is a fixture/contract wiring gap, not proof that the normal program computation failed.',
        'list_program_scope':'File is in same package SHA map, but no list_artifacts case record exists in this independent report (program list contains only build_task_config). Do not upgrade making-side self-tests into independent coverage.'},
      'static_resource_review_audit_only':[{'resource':'scripts/build_task_config.py','issue':'Header says every other base field preserved, but base_to_spec selects seven known fields and build reconstructs only fixed fields; unknown base properties are discarded. Existing fixed-field test does not prove arbitrary preservation.','execution':'NOT_RUN_IN_THIS_AUDIT'},
        {'resource':'scripts/build_task_config.py','issue':'output_format membership uses dict keys before validating scalar type; list/dict raises TypeError rather than promised exit2 error. Cron validation intentionally checks only five fields, so it is not a complete platform cron validator.','execution':'STATIC_ONLY_NOT_A_NEW_TEST_RESULT'},
        {'resource':'scripts/list_artifacts.py','issue':'Only the first YYYY-MM-DD-like match is considered, and whitespace-only names pass nonempty check. These are domain limits/possible contract weaknesses, not independently executed failures.','execution':'STATIC_ONLY'}],
      'same_version_actor_trials_or_independent_quality_or_total_cost_link':'NOT_ESTABLISHED_IN_THIS_EPISODE_AUDIT','qualified_skill_keep_credit':False,'positive_loss':0,'new_execution_or_training':False})
    aggregate_response_files=[NATIVE/'response.json',NATIVE/'openclaw_transport/response.json']
    reasoning={'schema':'wrd-scheduled-original-reasoning-preservation-audit-v1','native_reasoning_fields':sum(1 for x in nm for c in (x['message'].get('content') if isinstance(x['message'].get('content'),list) else []) if isinstance(c,dict) and c.get('type') in ['thinking','reasoning']),
      'v9_same_episode_API_capture_count':cohort.get('same_episode_API_capture_count','EPISODE_TABLE_CHECK_REQUIRED'),
      'actual_prior_v9_episode_metadata':{k:next(x for x in rows(V9/'recovery/episodes.metadata.jsonl.gz') if x['episode_id']==EID).get(k) for k in ['native_reasoning_fields','same_id_reasoning_overlay_fields','same_episode_API_capture_count','api_request_captures']},
      'aggregate_response_files':[pin(p) for p in aggregate_response_files],
      'explicit_reasoning_text_fields_in_aggregate_responses':{str(p):sorted(set(re.findall(r'"([^"\n]*reason[^"\n]*)"\s*:',p.read_text(encoding='utf8')))) for p in aggregate_response_files},
      'additional_native_export_evidence_checked_and_preserved':[pin(p) for p in (NATIVE/'openclaw_transport/evidence').iterdir() if p.is_file() and p.suffix.lower() in {'.json','.jsonl','.txt'}],
      'additional_evidence_explicit_thinking_block_count':sum(p.read_text(encoding='utf8').count('"type":"thinking"')+p.read_text(encoding='utf8').count('"type": "thinking"') for p in (NATIVE/'openclaw_transport/evidence').iterdir() if p.is_file() and p.suffix.lower() in {'.json','.jsonl','.txt'}),
      'metering_preserved_exactly':pin(NATIVE/'metering/scheduled-task-config__make1.native.jsonl'),
      'interpretation':'Native contains zero explicit thinking/reasoning blocks, aggregate responses have no reasoning-text field, prior v9 lists zero same-session API captures. Metering reasoning_tokens is a usage subset, not recoverable thought text. These checked carriers do not establish that no separate provider trace ever existed. No original thought was reconstructed or fabricated.',
      'all_original_text_tool_actions_observations_preserved':True,'new_original_R_tokens_admitted':0}
    rp=save('ORIGINAL_REASONING_AUDIT.json',reasoning)
    summary={'schema':'wrd-batch24-scheduled-completed-offline-audit-v1','status':'FIXED56_PROCESSED_AND_PRESERVED_NO_NEW_TRAINING_ADMISSION','episode_id':EID,'planned_targets':56,'processed_targets_with_original_body_and_prefix':56,'newly_proven_protected_targets':56,'unknown_lineage_targets_in_fixed56':0,'new_train_targets':0,'new_supervised_tokens':0,'original226_H_static_boundary_preserved':True,'new_agent_or_model_or_resource_program_execution':0,'training_started':False,'ancestry':ancestry_pin,'actual_targets':targetpin,'actual_edges':eventpin,'outcome':outcome,'original_reasoning':rp,'preservation_allowlist':preserved,'unique_preserved_original_objects':len(seen),'audit_cost':'UNKNOWN_NOT_ZERO','no_replacement_of_original_or_main_manifest':True}
    save('RESULT.json',summary)
    print(json.dumps({'status':summary['status'],'processed':56,'protected':56,'new_train_targets':0,'unique_objects':len(seen),'actual_write_events':sum(e['tool']=='write' for e in events)}))

if __name__=='__main__':main()
