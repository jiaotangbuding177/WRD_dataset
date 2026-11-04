"""Blind JSON/SHA lineage for an actually received old route card; no model."""
from pathlib import Path
import hashlib, json
from recover_two_lineage import ROOT, DEST, V9, ARCHIVE, pin, sha, rows, save
from resolve_evidence_edges import messages, text, h

def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()

def main():
    result0=json.loads((DEST/'TWO_EPISODE_IDENTITY_RECOVERY_01.json').read_text(encoding='utf-8'))
    html=result0['episodes']['ep_df95d2f3cf09628aa3ac']
    htmlbase=Path('E:/skillloop_runs/w10/native_episodes/teaching-html-demo__make1')
    routepath=htmlbase/'workspace/inputs/route_card.json'; route=json.loads(routepath.read_text(encoding='utf-8-sig'))
    htmlnative=htmlbase/'openclaw_transport/session_events.jsonl';hm=messages(htmlnative)
    rc=next(c for c in hm[3]['message']['content'] if c.get('type')=='toolCall')
    assert rc['name']=='read' and rc['arguments']['path']=='/workspace/inputs/route_card.json'
    assert text(hm[4]['message']).encode()==routepath.read_bytes()
    sourcebase=Path('E:/skillloop_runs/w10/native_episodes/screen_017')
    srcpath=sourcebase/'workspace/outputs/screen.json'; screened=json.loads(srcpath.read_text(encoding='utf-8-sig'))
    original=next(c for c in screened['cards'] if c['id']=='teaching-html-demo')
    assert set(route)-set(original)=={'candidate_gate'}
    assert all(route[k]==v for k,v in original.items())
    assert route['candidate_gate']['value_plan']==original['value_plan']
    srcnative=sourcebase/'openclaw_transport/session_events.jsonl';sm=messages(srcnative)
    sc=next(c for c in sm[5]['message']['content'] if c.get('type')=='toolCall')
    assert sc['name']=='write' and sc['arguments']['path']=='/workspace/outputs/screen.json'
    assert sc['arguments']['content'].encode()==srcpath.read_bytes()
    assert sm[6]['message']['toolCallId']==sc['id'] and sm[6]['message']['isError'] is False
    eps={r['episode_id']:r for r in rows(V9/'recovery/episodes.metadata.jsonl.gz')}
    source_meta=eps['ep_41bcac6f099728e10cce']
    assert sha(srcnative)==source_meta['source_native']['sha256']
    assert sha(Path(source_meta['source_native']['path']))==sha(srcnative)
    tfile=V9/'outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz'
    target=next(r for r in rows(tfile) if r['episode_id']=='ep_41bcac6f099728e10cce' and r['source_message_index']==5)
    assert target['source_admission']=='HOLD_PROTECTED' and target['protected_source_ids']
    resolution=ROOT/'output/20261021_workflow_library_v10/resolution/screen_017'
    taskpath=resolution/'task.json'; acceptpath=resolution/'result.json'
    task=json.loads(taskpath.read_text(encoding='utf-8-sig')); accepted=json.loads(acceptpath.read_text(encoding='utf-8-sig'))
    assert next(x for x in task['new_cards'] if x['id']=='teaching-html-demo')==route
    assert next(x for x in accepted['accepted'] if x['id']=='teaching-html-demo')==route
    affected=[t for t,i in zip(html['held_target_ids'],html['held_target_indices']) if i>4]
    earlier=[t for t,i in zip(html['held_target_ids'],html['held_target_indices']) if i<=4]
    rawsha=sha(srcpath);cas=ARCHIVE/'objects'/rawsha[:2]/rawsha
    out={'schema':'wrd-actual-html-route-card-producer-closure-v1',
      'status':'EXACT_PROTECTED_PRODUCER_AND_ACTUAL_DOWNSTREAM_RECEIPT_IDENTIFIED_NO_TRAINING_ADMISSION',
      'input_card':pin(routepath),'input_card_read':{'call_index':3,'call_event_line':hm[3]['event_line'],
        'tool_call_id':rc['id'],'observation_index':4,'observation_event_line':hm[4]['event_line'],
        'entire_actual_observation_exactly_equals_input_file_bytes':True,'observation_bytes':len(text(hm[4]['message']).encode()),
        'observation_SHA256':h(text(hm[4]['message']).encode())},
      'original_producer':{'episode_id':'ep_41bcac6f099728e10cce','native_original_pin':pin(srcnative),
        'native_CAS_pin':source_meta['source_native'],'native_CAS_original_SHA_equal':True,
        'write_message_index':5,'write_event_line':sm[5]['event_line'],'tool_call_id':sc['id'],
        'native_write_content_exactly_matches_actual_output_bytes':True,'actual_output_pin':pin(srcpath),
        'output_CAS_exists':cas.exists(),'output_CAS_matches':cas.exists() and sha(cas)==rawsha,
        'ack_observation_index':6,'ack_event_line':sm[6]['event_line'],'ack_is_error':False,
        'ack_text_sha256':h(text(sm[6]['message']).encode()),'scope_proof_at_actual_write':target},
      'card_derivation':{'original_card_id':'teaching-html-demo','original_card_canonical_SHA256':h(canonical(original)),
        'input_card_canonical_SHA256':h(canonical(route)),
        'all_original_card_fields_preserved_exactly':True,'additional_input_field_only':'candidate_gate',
        'additional_candidate_gate_value_plan_is_same_original_value_plan':True,
        'fieldwise_original_canonical_SHA256':{k:h(canonical(v)) for k,v in original.items()},
        'resolution_task_pin':pin(taskpath),'resolution_accepted_result_pin':pin(acceptpath),
        'same_input_card_JSON_value_in_resolution_task_and_accepted_result':True,
        'cannot_cleanse_protected_producer_by_two_selected_TRAIN_source_tags':True},
      'downstream_impact':{'newly_proven_protected_descendant_held_target_count':len(affected),
        'newly_proven_protected_descendant_held_target_ids':affected,
        'earlier_still_missing_producer_held_target_count':len(earlier),
        'earlier_still_missing_producer_held_target_ids':earlier,
        'boundary':'Only targets strictly after observation index4 inherit this proven route-card exposure; the read action itself is not retrospectively exposed.'},
      'not_claimed':['This is metadata/SHA provenance, not semantic validation of the old route.',
        'No protected conversation body was inspected or copied; mixed-producer card fields were compared blindly by JSON value and hash.',
        'No previous unknown labels, old source banks, checkpoint05 bytes or current training manifest were edited.',
        'No captured old command, helper, model or training was executed.'],
      'new_admissions':0,'new_native_or_training':False}
    p=save('HTML_ROUTE_CARD_PROTECTED_PRODUCER_CLOSURE_03.json',out)
    print(json.dumps({'receipt':p,'new_protected_descendant_held_targets':len(affected),'earlier_unresolved_held_targets':len(earlier),
      'actual_route_card_received_bytes':len(text(hm[4]['message']).encode()),'new_admissions':0}))

if __name__=='__main__':main()
