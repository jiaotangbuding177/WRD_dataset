"""Inspect original metadata and exact identities; do not execute old commands."""
from pathlib import Path
import gzip, hashlib, json, re
from recover_two_lineage import ROOT, DEST, V9, safe_file, pin, sha, rows, save

def text(m):return '\n'.join(c.get('text','') for c in m.get('content',[]) if isinstance(c,dict))
def messages(p):
    out=[]
    with safe_file(p).open('rt',encoding='utf-8-sig') as f:
        for line_no,line in enumerate(f,1):
            e=json.loads(line)
            if isinstance(e.get('message'),dict):out.append({'event_line':line_no,'message':e['message']})
    return out
def h(b):return hashlib.sha256(b).hexdigest()
def copy_exact(p,expected):
    p=safe_file(p);b=p.read_bytes();assert h(b)==expected
    d=DEST/'recovered_objects'/expected;d.parent.mkdir(exist_ok=True)
    if not d.exists():d.write_bytes(b)
    assert sha(d)==expected
    return {'source':pin(p),'recovered_same_SHA_object':pin(d)}

def main():
    current=json.loads((DEST/'TWO_EPISODE_IDENTITY_RECOVERY_01.json').read_text(encoding='utf-8'))
    producers={'8e91a3e383a94eeaac2eb001161a0a1f651ea0d23e75ca15e26bf0a8832261b4':'ep_e01474a388e594b3efba',
      '0c06216e10fdf2e4c9657ceceb22945d33e52f4ea58ed306761f9e59bc9b2383':'ep_c0372b3d3ec39fcaa055',
      'b107d098954e84dfb1a30f9fd2eb2979de6e5f297a60bfabf68b7d8d471767e5':'ep_af9ec1f94bc12f273666'}
    target_source=V9/'outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz'
    prodrows=[]
    for r in rows(target_source):
        if r['episode_id'] not in producers.values():continue
        for w in r['exact_produced_file_write_proofs']:
            if producers.get(w['content_sha256'])==r['episode_id']:
                prodrows.append({'target_metadata':r,'exact_matching_write_proof':w})
    assert {r['exact_matching_write_proof']['content_sha256'] for r in prodrows}==set(producers)
    docroot=Path('E:/skillloop_runs/workflow_library/make__docx-standardize-export/attempt_2')
    docnative=docroot/'openclaw_transport/session_events.jsonl';dm=messages(docnative)
    call=next(c for c in dm[11]['message']['content'] if c.get('type')=='toolCall')
    assert call['name']=='exec' and 'head -c 3000' in call['arguments']['command']
    observed=text(dm[12]['message']);parts=[];headviews=[]
    nativepaths=['/workspace/inputs/reusable/skill_'+str(i)+'/SKILL.md' for i in [1,2,3]]+['/workspace/inputs/reusable.json']
    for native in nativepaths:
        p=docroot/'workspace'/native.removeprefix('/workspace/');b=safe_file(p).read_bytes();head=b[:3000]
        parts.append('====='+native+'=====\n'+head.decode('utf-8',errors='replace')+'\n')
        headviews.append({'native_path':native,'source_file':pin(p),'head_max_bytes':3000,
          'head_actual_bytes':len(head),'head_bytes_sha256':h(head),
          'whole_file_visible_within_head':len(b)<=3000,
          'matching_original_write_proof':next((r for r in prodrows if r['exact_matching_write_proof']['content_sha256']==h(b)),None)})
    expected=''.join(parts)
    assert expected.startswith(observed) and expected[len(observed):]=='\r\n\n'
    assert all(v['matching_original_write_proof'] is not None for v in headviews[:3])
    assert all(v['matching_original_write_proof']['target_metadata']['source_admission']=='HOLD_PROTECTED' for v in headviews[:3])
    doc=current['episodes']['ep_5de7f066feaed4c4b254']
    affected=[t for t,i in zip(doc['held_target_ids'],doc['held_target_indices']) if i>12]
    unaffected=[t for t,i in zip(doc['held_target_ids'],doc['held_target_indices']) if i<=12]
    dproof={'status':'EXACT_PROTECTED_DERIVED_SKILL_HEADS_ACTUALLY_RECEIVED_RESOURCE_GRAPH_OMISSION',
      'native_original_and_CAS_pin':doc['native_carriers'],'call_message_index':11,'observation_message_index':12,
      'call_event_line':dm[11]['event_line'],'observation_event_line':dm[12]['event_line'],
      'tool_call_id':call['id'],'command_sha256':h(call['arguments']['command'].encode()),
      'observation_text_chars':len(observed),'observation_text_sha256':h(observed.encode()),
      'blind_comparison':'Expected original four-file head stdout equals actual observation except exactly terminal CRLF+LF removed by captured tool display; all three SKILL segments are interior, unmodified and actually present.',
      'comparison_exact_terminal_difference_repr':'\\r\\n\\n','head_views_metadata_only_no_protected_body_copied':headviews,
      'original_v9_resource_graph_omits_three_skill_heads':True,
      'newly_proven_protected_descendant_held_target_count':len(affected),'newly_proven_protected_descendant_held_target_ids':affected,
      'earlier_still_missing_producer_held_target_count':len(unaffected),'earlier_still_missing_producer_held_target_ids':unaffected,
      'not_an_admission':'No original label or training bank modified. Exact protected ancestry must be respected; no private original source body was inspected.'}
    htmlroot=Path('E:/skillloop_runs/w10/native_episodes/teaching-html-demo__make1')
    hn=htmlroot/'openclaw_transport/session_events.jsonl';hm=messages(hn)
    boundary_sha='82ee0387a74b164590951efe2e7aeb01eb6a9752d0f562b348c265a38feb719d'
    obs62=text(hm[62]['message'])
    assert boundary_sha+'  tmp/cases/ex_boundary/page_spec.json' in obs62
    exact_boundary=copy_exact(htmlroot/'workspace/outputs/tmp/cases/ex_boundary/page_spec.json',boundary_sha)
    obs74=text(hm[74]['message']);assert 'solar.err: No such file or directory' in obs74 and 'code 1' in obs74
    obs76=text(hm[76]['message']);assert 'solar_plan.err' in obs76 and 'build_teaching_page_error:' in obs76
    obs90=text(hm[90]['message']);assert "No such file or directory: 'tmp/cases/normal/teaching.html'" in obs90
    obs92=text(hm[92]['message']);assert 'normal expected 9776f72e4343 actual 9776f72e4343 MATCH' in obs92
    helper=ROOT/'output/20261029_wrd_v9_missing_evidence_recovery/html_source_reader_peer/HTML_READER_BINDING_CANDIDATE.json'
    assert sha(helper)=='d01609d872af80c64aa58bc24742cfaef245641268899e8a1cc30c2c86292c7d'
    dynamic=[
      {'original_unknown_native_path':'/workspace/outputs/$T/ex_boundary/page_spec.json','call_index':61,'observation_index':62,
       'status':'RESOLVED_SHELL_VARIABLE_PATH_AND_EXACT_ORIGINAL_OBSERVED_SHA',
       'resolved_native_path':'/workspace/outputs/tmp/cases/ex_boundary/page_spec.json','exact_carrier':exact_boundary,
       'observation_text_sha256':h(obs62.encode()),'original_observation_SHA_is_not_future_input':True},
      {'original_unknown_native_path':'/workspace/outputs/tmp/cases/solar.err','call_index':73,'observation_index':74,
       'status':'ORIGINAL_TOOL_PROVES_ABSENT_FILE_NO_FILE_CONTENT_TO_RESTORE',
       'observation_text_sha256':h(obs74.encode()),'body_copied_or_recreated':False},
      {'original_unknown_native_path':'/workspace/outputs/tmp/cases/solar_plan.err','call_index':75,'observation_index':76,
       'status':'ACTUAL_CAPTURED_ERROR_TEXT_AVAILABLE_BUT_ORIGINAL_PHYSICAL_FILE_IDENTITY_NOT_RECOVERED',
       'observation_text_sha256':h(obs76.encode()),'physical_path_now_exists':(htmlroot/'workspace/outputs/tmp/cases/solar_plan.err').exists(),
       'body_copied_or_recreated':False,'trailing_newline_not_inferred_into_original_bytes':True},
      {'original_unknown_native_path':'<dynamic Python read target>','call_index':89,'observation_index':90,
       'status':'ORIGINAL_INLINE_PROGRAM_FAILS_ON_NONEXISTENT_NORMAL_HTML_BEFORE_LATER_READS',
       'attempted_native_path':'/workspace/outputs/tmp/cases/normal/teaching.html','observation_text_sha256':h(obs90.encode()),
       'not_claimed':'Do not turn this failed read into a successful resource consumption; shell later continues separate preflight.'},
      {'original_unknown_native_path':'<dynamic Python read target>','call_index':91,'observation_index':92,
       'status':'FINITE_VISIBLE_INLINE_PATH_DOMAIN_IDENTIFIED_NOT_A_WHOLE_PROGRAM_QUALITY_PASS',
       'inline_read_paths':['replay.json','tmp/cases/build_normal/teaching.html','tmp/cases/build_boundary/teaching.html',
         'tmp/cases/ex_normal/page_spec.json','reproduction_inputs/page_spec_friction.json','resource_manifest.json','evidence.json'],
       'observation_text_sha256':h(obs92.encode()),
       'not_claimed':'Current terminal trees are not inserted into the earlier observation; twelve-character reported HTML digests are not upgraded into full SHA evidence.'}]
    out={'schema':'wrd-two-selected-lineage-candidate-edges-v2','status':'PARTIAL_RECOVERY_AND_NEW_PROTECTED_ANCESTRY_NOT_AUTOMATIC_ADMISSION',
      'metadata_proof_source':pin(target_source),'identity_recovery_receipt':pin(DEST/'TWO_EPISODE_IDENTITY_RECOVERY_01.json'),
      'docx_actual_omitted_dependencies':dproof,
      'html_actual_runtime_reader_binding_independent_peer':pin(helper),'html_dynamic_read_resolution':dynamic,
      'html_remaining_unknowns':['Route-card/value-plan actual producer prefix not proved by its two TRAIN tags.',
         'Generic instructions/input-index/source-bindings need exact construction/derivation ancestry, not blanket script-SHA admission.',
         'The original solar_plan.err physical-file byte identity has not been recovered; only actual delivered tool text is available.',
         'Late calculated-path inputs require per-call original versions; final same-SHA carriers do not alone establish prior versions.'],
      'raw_native_pins':[pin(docnative),pin(hn)],'new_training_targets_admitted':0,'source_bank_and_05_unchanged':True,
      'protected_source_body_inspected':False,'old_commands_or_helpers_executed':False,'new_native_or_training':False}
    receipt=save('SOURCE_CLOSURE_CANDIDATES_02.json',out)
    print(json.dumps({'receipt':receipt,'docx_new_protected_descendant_targets':len(affected),
      'docx_earlier_unresolved_targets':len(unaffected),'html_dynamic_resource_types':4,'html_actual_call_bindings':5,
      'new_exact_same_SHA_synthetic_object':boundary_sha,'new_admissions':0}))

if __name__=='__main__':main()
