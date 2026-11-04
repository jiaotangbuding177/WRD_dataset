"""Freeze the proposed5 for root review; no candidate/data changes."""
from pathlib import Path
import collections,gzip,hashlib,json,os
os.environ['USE_TORCH']='0';os.environ['USE_TF']='0';os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path('D:/skillloop');WORK=ROOT/'output/20261031_wrd_curation10';OUT=WORK/'reasoning_semantic10'
def h(x):return hashlib.sha256(x if isinstance(x,bytes)else x.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return[json.loads(l)for l in gzip.open(p,'rt',encoding='utf-8-sig')if l.strip()]
def pin(p):p=Path(p);return{'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def save(n,d):(OUT/n).write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
if __name__=='__main__':
    from transformers import AutoTokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    assets=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
    toks={k:AutoTokenizer.from_pretrained(assets/k,local_files_only=True,trust_remote_code=False)for k in ['primary_14b','control_8b']}
    template=_compile_jinja_template(load(WORK/'early_reads/compiled01/CAUSAL_TEMPLATE.json')['variant'])
    p=OUT/'CANDIDATES.proposed.raw.jsonl.gz';rr=rows(p);api=rows(WORK/'reasoning_native10/API67_R_A_FEEDBACK.original.audit.jsonl.gz')
    main=ROOT/'output/20261027_wrd_main_v10';manifest=load(main/'TRAINING_MANIFEST.json')
    assert h((main/'TRAINING_MANIFEST.json').read_bytes())=='01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42'
    old=[r for f in manifest['actual_train_files']for r in rows(main/f['path'])]
    oldcalls={c['id']for r in old for t in r['targets']if any(s[2]=='A'for s in t.get('owned_supervision_spans',[]))for c in r['messages'][t['message_index']].get('tool_calls',[])}
    cases=[]
    for r in rr:
        origin=r['original_R_provenance'];a=next(a for a in api if a['response_id']==origin['original_response_id'])
        region=origin['continuous_excerpt'];selected=a['original_R'][region['start']:region['end']]
        assert selected==r['messages'][2]['reasoning_content']and h(selected)==region['text_sha256']
        assert not a['existing_positive_R_approved_unicode_ranges']
        assert r['messages'][2]['tool_calls']==a['original_response']['tool_calls']
        assert all(c['id']not in oldcalls for c in r['messages'][2]['tool_calls'])
        assert r['A_original_action_arguments_identical']and not r['is_original_native_request_identical']
        assert r['loss_multiplier']==0.25 and r['approved_components']==['A']
        for q in r['approved_field_ranges']:
            assert q['field']=='reasoning_content'and h(selected[q['start']:q['end']])==q['text_sha256']
            assert not any(q['start']<z['end']and q['end']>z['start']for z in r['target_R_zero_unicode_ranges'])
        for z in r['target_R_zero_unicode_ranges']:assert h(selected[z['start']:z['end']])==z['text_sha256']
        payload=json.loads(r['messages'][1]['content']);visible={f['path']:f for f in payload['visible_file_contents']}
        for f in payload['visible_file_contents']:assert h(f['content'])==f['sha256']
        for ref in r['functional_state_resource_manifest']:assert pin(ref['actual_asset']['path'])==ref['actual_asset']
        # Every actual input mentioned in the selected causal rationale is made
        # available as a real entity; file semantics used by R have full text.
        if r['id'].endswith('0017'):
            key='/workspace/inputs/previous_skill/scripts/validate_pack.py'
            assert 'evidence_ref_invalid'in visible[key]['content']
            assert '/workspace/inputs/previous_tests/make_fixtures.py'in visible
            assert '/workspace/inputs/previous_tests/run_tests.py'in visible
        if r['id'].endswith('0024'):
            assert '/workspace/outputs/tests/run_tests.py'in visible
            assert selected.startswith('Now build the supplementary tests:')
        if r['id'].endswith('0025'):assert '/workspace/outputs/tests/make_fixtures_extra.py'in visible
        kwargs=dict(toks['primary_14b'].special_tokens_map,enable_thinking=False)
        rendered=template.render(messages=r['messages'],tools=r['tools'],documents=None,add_generation_prompt=False,**kwargs)
        t=toks['primary_14b'](rendered,add_special_tokens=False,return_offsets_mapping=True)
        other=toks['control_8b'](rendered,add_special_tokens=False,return_offsets_mapping=True)
        assert t==other and len(t['input_ids'])<=32768,(r['id'],len(t['input_ids']),t==other)
        cases.append({'id':r['id'],'dual_tokenizer_full_tokens':len(t['input_ids']),
          'R_original_owner':a['source_compatible_API_response']['sha256'],'R_field_original_range':region,
          'R_unicode_characters':len(selected),'R_zero_unicode_characters':sum(z['end']-z['start']for z in r['target_R_zero_unicode_ranges']),
          'A_original_owner':a['owner_id'],'A_call_id':r['messages'][2]['tool_calls'][0]['id'],
          'R_current595_overlap_characters':0,'A_current595_positive_call_ID_overlap':False,
          'recorded_native_argument_byte_identity':a['native_same_recorded_response_ID_and_full_nonthought_output_tool_JSON_ID_exact'],
          'real_assets_SHA_verified':len(r['functional_state_resource_manifest']),
          'full_visible_resource_paths':sorted(visible),'point_state':'ORIGINAL_COMMISSIONED_FILES_AND_PRIOR_LITERAL_WRITES_EDITS_ONLY',
          'source_request_equivalence':False,'root_approval_pending':True})
    wanted={('B_revision_report_01','0017'),('B_revision_report_01','0024'),('B_revision_report_01','0025'),('B_make_report_02','0014'),('B_make_report_02','0016'),('B_make_report_02','0021')}
    full=[]
    for a in api:
        if(a['stage'],a['call_id'][:4])not in wanted:continue
        msgs=a['compatible_request_messages_original']+[a['original_response']];msgs=json.loads(json.dumps(msgs))
        for m in msgs:
            if isinstance(m.get('content'),list):m['content']='\n'.join(b['text']for b in m['content'])
        tools=[t for t in a['compatible_request_tools_original']if t['function']['name']in {'read','ls','write','edit','exec','apply_patch','process'}]
        text=template.render(messages=msgs,tools=tools,documents=None,add_generation_prompt=False,**dict(toks['primary_14b'].special_tokens_map,enable_thinking=False))
        ids=toks['primary_14b'](text,add_special_tokens=False)['input_ids'];other=toks['control_8b'](text,add_special_tokens=False)['input_ids'];assert ids==other and len(ids)>32768
        full.append({'stage':a['stage'],'call_id':a['call_id'],'full_system_past_and_full_original_response_core7_tokens':len(ids),
          'source_request':a['source_compatible_API_request'],'source_response':a['source_compatible_API_response'],
          'disposition':'HOLD_FULL_ORIGINAL_STATE_OVER32K_NO_INPUT_TRUNCATION'})
    save('FULL_ORIGINAL6_OVERWINDOW_DUAL_TOKENIZER_QA.json',{'rows':full,'all_full_original_inputs_preserved':True,'no_original_input_truncation':True})
    save('FROZEN5_SEMANTIC_STATE_AND_SOURCE_QA.json',{'status':'PASS_PROPOSED5_READY_FOR_ROOT_ADMISSION_AND_COMPILATION',
      'candidate_pin':pin(p),'rows':cases,'source_recorded_original_R_characters':sum(c['R_unicode_characters']for c in cases),
      'independent_source_groups_added':0,'original_R_not_rewritten':True,
      'R_original_compatible_API_recontextualized_not_original_native':True,
      'CPU_resource_evidence':[pin(OUT/'CPU_RESOURCE_CHECKS.json'),pin(OUT/'OLD_VS_REVISED_REAL_COUNTEREXAMPLES.json')],
      'new_business_calls':0,'training_started':False,'script_pin':pin(__file__)})
    print(json.dumps({'candidate':pin(p),'full_tokens':[c['dual_tokenizer_full_tokens']for c in cases],'ready_for_root':True}))
