"""Independent file/state/API/array peer, no business or native execution."""
from array import array
import ast,gzip,hashlib,importlib.util,json,os,re,sys
from pathlib import Path
sys.dont_write_bytecode=True
os.environ['USE_TORCH']='0';os.environ['USE_TF']='0';os.environ['TOKENIZERS_PARALLELISM']='false'
ROOT=Path('D:/skillloop');BASE=ROOT/'output/20261027_wrd_main_v10';B=BASE/'historical_v6_action_recovery_01';OUT=Path(__file__).parent
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def row(p):return json.loads(next(gzip.open(p,'rt',encoding='utf-8')))
def pin(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)}
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def verify_ref(base,ref):
    p=Path(ref['path']);p=p if p.is_absolute()else base/p
    assert p.is_file()and p.stat().st_size==ref['bytes']and digest(p)==ref['sha256'];return p
def module(p,name):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def verify_profiles(folder,compiler):
    selection=load(folder/'PORTABLE_SELECTION.json');parent=folder.parent;results=[];owner=selection['canonical_original_action_owner']
    for p in selection['state_files']:verify_ref(parent,p)
    for profile,ref in selection['profiles'].items():
        raw=row(verify_ref(folder,ref['messages']));r=row(verify_ref(folder,ref['compiled']));assert r['messages']==raw['messages']and r['tools']==raw['tools']
        assert raw['actual_native_tool_dispatch']is False and raw['target_owner']['canonical_original_action_owner_id']==owner
        assert raw['message_loss_mask']==[0,0,1]and len(raw['messages'])==3
        call=raw['messages'][-1]['tool_calls'][0];args=json.loads(call['function']['arguments']);registry={t['function']['name']:t['function']for t in raw['tools']}
        from jsonschema import Draft202012Validator
        Draft202012Validator(registry[call['function']['name']]['parameters']).validate(args)
        kw=dict(compiler.tokenizers['primary_14b'].special_tokens_map);kw['enable_thinking']=False
        text=compiler.plain_compiled.render(messages=raw['messages'],tools=raw['tools'],documents=None,add_generation_prompt=False,**kw)
        a=compiler.tokenizers['primary_14b'](text,add_special_tokens=False,return_offsets_mapping=True)
        b=compiler.tokenizers['control_8b'](text,add_special_tokens=False,return_offsets_mapping=True);assert a==b and a['input_ids']==r['input_ids']
        h='<|im_start|>assistant\n<think>\n';start=text.rindex(h)+len(h);R=raw['messages'][-1]['reasoning_content'];assert text[start:start+len(R)]==R
        stop=start+len(R);action_start=stop+len('\n</think>\n\n');action_end=text.rindex('<|im_end|>\n')
        positives={i for i,(x,y)in enumerate(a['offset_mapping'])if x<y and(start<=x and y<=stop or action_start<=x and y<=action_end)}
        assert positives=={i for x,y,c,w in r['supervision_spans']for i in range(x,y)}
        values={}
        for f in ref['arrays']:
            p=verify_ref(folder,f);kind='I'if 'input_ids'in p.name else'q'if 'labels'in p.name else'f';v=array(kind);v.frombytes(p.read_bytes());values[p.name]=v.tolist()
        ids=next(v for k,v in values.items()if'input_ids'in k);labels=next(v for k,v in values.items()if'labels'in k);weights=next(v for k,v in values.items()if'weights'in k)
        assert ids==r['input_ids']and len(ids)==len(labels)==len(weights)==r['total_tokens']
        for i,(token,label,w)in enumerate(zip(ids,labels,weights)):assert(label==token and w==.25)if i in positives else(label==-100 and w==0)
        results.append({'profile':profile,'raw':pin(folder/ref['messages']['path']),'compiled':pin(folder/ref['compiled']['path']),
            'total_tokens':r['total_tokens'],'supervised_tokens':r['supervised_tokens'],'components':r['supervised_tokens_by_component'],
            'dual_tokenizer_all_IDs_and_offsets':'PASS','every_array_position_labels_weights':'PASS','actual_tool_schema_arguments':'PASS',
            'canonical_original_action_owner':owner,'actual_native_dispatch':False})
    return selection,results
def main():
    assert not (OUT/'helpers/PEER.json').exists()
    comp=module(ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py','read_only_peer_compiler_20261029')
    compiler=comp.CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
    old=(B/'style_repair_01/resources/old_run.py').read_text(encoding='utf-8');original_contract=load(B/'style_repair_01/resources/inputs/task_contract.json')
    expected_contract={k:v for k,v in original_contract.items()if k not in ['source_boundary','projection_note']}
    H=B/'helpers_construction_01';scope=load(H/'SOURCE_AND_API_SCOPE.json');code=(H/'resources/masking_helpers.py').read_text(encoding='utf-8')
    assert len(code)==5862 and sha(code.encode())==scope['target_module_sha256']=='ff6f2544028eb40a5fb2f98e775dc075341a8866217a43c7d0f8d97c970825a1'
    funcs={n.name:n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef)};assert set(funcs)=={r['name']for r in scope['verbatim_functions']}and 'style_sig'not in funcs and'main'not in funcs
    function_proofs=[]
    for f in scope['verbatim_functions']:
        s=old[f['source_original_code_start']:f['source_original_code_end']];assert sha(s.encode())==f['source_original_code_text_sha256']and s in code
        assert ast.dump(ast.parse(s).body[0],include_attributes=False)==ast.dump(funcs[f['name']],include_attributes=False)
        function_proofs.append({'function':f['name'],'original_range':[f['source_original_code_start'],f['source_original_code_end']],'original_text_sha256':f['source_original_code_text_sha256'],'verbatim_and_AST_match':True})
    hsel,hqa=verify_profiles(H/'native_projection_01',compiler);hraw=row(H/'native_projection_01/native_helpers.core7.raw.jsonl.gz');hu=hraw['messages'][1]['content'];ha=json.loads(hraw['messages'][-1]['tool_calls'][0]['function']['arguments'])
    assert ha['content']==code and ha['path']=='/workspace/outputs/candidate/scripts/masking_helpers.py'and code not in hu
    state=H/hsel['state_root'];assert not(state/'outputs/candidate/scripts/masking_helpers.py').exists()
    assert load(state/'inputs/task_contract.functional.json')==expected_contract
    assert all(s in hu for s in ['不拒额外字段','不能替代完整JSON Schema','不承担路径授权','错误单元格/富文本','不包含完整样式','当前没有它的试跑结果'])
    assert not any(s in hu for s in ['source_boundary','projection_note','root_main_admission','EXPLICIT_NEW_AUTHORED','creator_owner'])
    hres=load(H/'RESOURCE_QA.json');hr=Path(hres['execution_receipt_path']);hexec=load(hr);assert digest(hr)==hres['execution_receipt_sha256']
    assert hres['checks_passed']==len(hres['checks'])==41 and hres['module_sha256']==sha(code.encode())and hexec['exit_code']==0
    assert hexec['host_available_before_bytes']>=7*1024**3 and hexec['image'].endswith('97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2')
    driver=(H/'resource_qa_01/workspace/qa_driver.py').read_text(encoding='utf-8');assert 'reject_trim_mutant'in driver and'reject_negative_zero_slice_mutant'in driver
    helper={'status':'PASS_SCOPED_COMPLETE_HELPER_MODULE_AND_NEW_FUNCTIONAL_STATE_PENDING_ROOT','reviewer':'Independent Codex AI, not human gold','source_id':'conv_b5e6f3d3bab9',
        'reviewed_full_module_characters':len(code),'reviewed_full_user_state':True,'reviewed_full_new_rationale_and_write':True,'target':pin(H/'resources/masking_helpers.py'),
        'seven_verbatim_functions':function_proofs,'API_semantic_scope':{'sha256_file':'Readable local file hash only','resolve_path':'Lexical absolute/base resolution, not path authorization',
            'validate_request':'Required/basic types/ranges/selection checks, explicitly not full JSON Schema or additionalProperties enforcement',
            'mask_text':'Validated string/parameter preconditions, Unicode codepoints, no trim, suffix0, idempotent under same parameters',
            'classify':'Ordinary cells/formulas/blank/text/nontext; excludes error and rich-text cell semantics',
            'locate_columns':'Exact unique header mapping with missing/duplicate failure','layout_sig':'Declared partial defined-property fingerprint, no full tables/style/render proof'},
        'new_header_imports_constant_and_exception_author':'New author, seven function bodies original Teacher; neither whole old main nor bad style comparator copied',
        'necessary_functional_files_complete_and_target_absent':True,'original_contract_functional_values_unchanged_except_2_audit_fields_omitted':True,
        'future_QA_or_target_code_in_input':False,'resource_QA':pin(H/'RESOURCE_QA.json'),'resource_execution_receipt':pin(hr),'complete_current_QA_driver':pin(H/'resource_qa_01/workspace/qa_driver.py'),
        'existing_QA_scope':'41 finite checks including2 mutants; not all workbook/business/skill quality','existing_QA_wall_seconds':hexec['wall_seconds'],
        'profiles':hqa,'owner':hsel['canonical_original_action_owner'],'views_mutually_exclusive':True,'full_old_creator_action_not_approved':True,
        'additional_business_or_model_or_Agent_runs':0,'training_started':False,'root_admission_by_this_peer':False,'curation_cost':'UNKNOWN_NOT_ZERO'}
    save(OUT/'helpers/PEER.json',helper)
    S=B/'style_repair_01';ssel,sqa=verify_profiles(S/'native_projection_02',compiler);sr=row(S/'native_projection_02/native_style.core7.raw.jsonl.gz');u=sr['messages'][1]['content'];a=json.loads(sr['messages'][-1]['tool_calls'][0]['function']['arguments'])
    assert a==load(S/'resources/new_authored_native_edit_02.arguments.json')and len(a['edits'])==2
    state=S/ssel['state_root'];assert digest(state/'outputs/candidate/scripts/run.py')==sha(old.encode())
    assert load(state/'inputs/task_contract.json')==expected_contract and old in u
    assert 'root_main_admission'not in u and 'source_boundary'not in u and 'projection_note'not in u
    blocks=re.findall(r'<file>\n(.*?)\n</file>',u,re.S);assert len(blocks)==3 and old in blocks
    assert any(json.loads(x)==expected_contract for x in blocks if x.strip().startswith('{'))
    text=old
    for e in a['edits']:assert text.count(e['oldText'])==1;text=text.replace(e['oldText'],e['newText'])
    assert sha(text.encode())=='ebee935045a173afad679af22a3ae8a05096d57fec3a46b511fbd091fd9af2f0'
    assert ast.dump(ast.parse(text),include_attributes=False)==ast.dump(ast.parse((S/'resources/new_run.py').read_text(encoding='utf-8')),include_attributes=False)
    assert 'total 129 mismatch 0'in u and '尚未应用本次copy修补，也没有修后PASS'in u
    assert sr['rationale_provenance']=='NEW_AUTHORED_CONCISE_RATIONALE_NOT_ORIGINAL_TEACHER_COT'
    style={'status':'PASS_SCOPED_STYLE02_FUNCTIONAL_STATE_R_AND_TWO_EDITS_PENDING_ROOT','source_id':'conv_b5e6f3d3bab9','reviewed_full_user_state_characters':len(u),
        'complete_old15834char_program_seen':True,'complete_functional_contract_and_dev_request_seen':True,'both_binary_workbooks_available_by_exact_SHA':True,
        'old_failure_and129cell_copy_diagnostic_present_before_target':True,'new_program_or_new_PASS_in_prestate':False,
        'new_R_semantics':'Limited actual false-style failure and delivered129cell unwrapping comparison; proposes only local import/return repair and requires retest.',
        'two_native_edits':pin(S/'resources/new_authored_native_edit_02.arguments.json'),'new_program_SHA':sha(text.encode()),'AST_equals_historical_f381':True,
        'different_bytes_and_omitted_inaccurate_original_comment_declared':True,'actual_native_dispatch':False,'original_bad_text_as_edit_selector_is_not_new_program_correctness_credit':True,
        'known_remaining_main_limits':['Additional properties not rejected','Same output/report path can overwrite artifact','Full tables/types/visual preservation not proved'],
        'finite_resource_QA':pin(S/'RESOURCE_QA.json'),'earlier_independent_resource_receipt':pin(S/'independent_peer_review_01/NATIVE_EDIT02_AND_FINITE_RESOURCE_QA.json'),
        'profiles':sqa,'owner':ssel['canonical_original_action_owner'],'distinct_from_helpers_creator_owner':ssel['canonical_original_action_owner']!=hsel['canonical_original_action_owner'],
        'view01_not_approved':True,'core_full_same_owner_mutually_exclusive':True,'model_or_Agent_or_business_runs':0,'training_started':False,'root_admission_by_this_peer':False,'curation_cost':'UNKNOWN_NOT_ZERO'}
    save(OUT/'style02/PEER.json',style)
    for name in ['helpers','style02']:
        save(OUT/name/'MANIFEST.json',{'files':[pin(OUT/name/'PEER.json'),pin(Path(__file__))],'status':'INDEPENDENT_SCOPED_PEER_COMPLETE','original_banks_changed':False,'training_started':False})
    print(json.dumps({'helpers_peer_sha256':digest(OUT/'helpers/PEER.json'),'helpers_manifest_sha256':digest(OUT/'helpers/MANIFEST.json'),
        'style02_peer_sha256':digest(OUT/'style02/PEER.json'),'style02_manifest_sha256':digest(OUT/'style02/MANIFEST.json')}))
if __name__=='__main__':main()
