"""Independent full-code/input/math-scope and CPU array peer; no business run."""
from pathlib import Path
from array import array
import ast,gzip,hashlib,importlib.util,json,os,sys
sys.dont_write_bytecode=True;os.environ['USE_TORCH']='0';os.environ['USE_TF']='0'
ROOT=Path('D:/skillloop');BASE=ROOT/'output';P=BASE/'20261029_wrd_ewi_probe_recovery';OUT=Path(__file__).parent
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def row(p):return json.loads(gzip.decompress(Path(p).read_bytes()).decode())
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    assert not(OUT/'PEER.json').exists()
    review=load(P/'SOURCE_REVIEW.json');selection=load(P/'PORTABLE_SELECTION.json');qa=load(P/'FINITE_RESOURCE_QA.json')
    for ref in selection['all_actual_files']:
        f=P/ref['path'];assert pin(f)['bytes']==ref['bytes'] and pin(f)['sha256']==ref['sha256']
    for rec in review['original_files']:
        for ref in rec.values():assert pin(ref['path'])['bytes']==ref['bytes'] and pin(ref['path'])['sha256']==ref['sha256']
    newpath=P/'resources/proportional_split.py';new=newpath.read_text(encoding='utf-8');oldpath=P/'original/00_probe.py';old=oldpath.read_text(encoding='utf-8')
    original=load(P/'original/13_parsed.json');assert original['kind']=='TRY' and original['action_id']==review['original_action_id']
    code=original['arguments']['code'];assert old==code and len(code)==3661 and sha(code.encode())==review['original_action_code_LF_sha256']
    assert sha(oldpath.read_bytes())==review['original_physical_probe_CRLF_sha256'] and sha(oldpath.read_bytes())!=sha(code.encode())
    # Rebuild exact original policy content directly from that single SSE.
    content=[];done=0
    for line in (P/'original/10_response.partial.raw').read_text(encoding='utf-8').splitlines():
        if not line.startswith('data:'):continue
        data=line[5:].strip()
        if data=='[DONE]':done+=1;continue
        if not data:continue
        event=json.loads(data)
        for choice in event.get('choices',[]):
            text=choice.get('delta',{}).get('content')
            if isinstance(text,str):content.append(text)
    policy=json.loads(''.join(content));assert policy==original and done==1
    oldast=ast.parse(code);newast=ast.parse(new);functions=[]
    for name in ['compute_valuation','main']:
        a=next(n for n in oldast.body if isinstance(n,ast.FunctionDef) and n.name==name);b=next(n for n in newast.body if isinstance(n,ast.FunctionDef) and n.name==name)
        ao=ast.get_source_segment(code,a);bn=ast.get_source_segment(new,b);assert ao==bn and ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
        functions.append({'name':name,'characters':len(ao),'exact_original_function_LF_sha256':sha(ao.encode())})
    assert isinstance(newast.body[-1],ast.If) and len(newast.body[-1].body)==1
    assert ast.dump(newast.body[-1].body[0],include_attributes=False)==ast.dump(ast.parse('main()').body[0],include_attributes=False)
    assert '--increase" in sys.argv' in code and 'sys.argv' not in new
    originalobs=load(P/'original/02_observation.json');assert originalobs['actual'] and originalobs['exit_code']==0 and originalobs['script_sha256']==sha(oldpath.read_bytes())
    assert sha(originalobs['stdout'].encode())==pin(P/'original/03_stdout.raw')['sha256']
    driver=P/'finite_qa_01/workspace/driver.py';drivertext=driver.read_text(encoding='utf-8');ast.parse(drivertext)
    execution=load(P/'finite_qa_01/EXECUTION_RECEIPT.json');assert pin(P/'finite_qa_01/EXECUTION_RECEIPT.json')['sha256']==qa['execution_receipt']['sha256'] and execution['exit_code']==0
    assert qa['checks_passed']==414 and qa['fraction_oracle_parameter_cases']==60 and qa['new_complete_resource_sha256']==pin(newpath)['sha256']
    assert 'Fraction(i)*c/pre' in drivertext and "rel_tol=1e-10" in drivertext and "parameters+=1" in drivertext
    r=row(P/'native_construction_01/math_resource.core7.raw.jsonl.gz');user=r['messages'][1]['content'];target=r['messages'][-1]
    args=json.loads(target['tool_calls'][0]['function']['arguments']);assert args=={'path':'/workspace/outputs/proportional_split.py','content':new}
    assert target['reasoning_content']=='' and target['content']=='' and r['approved_components']==['A'] and r['loss_multiplier']==.25
    assert r['actual_native_tool_dispatch'] is False and r['is_original_native_request_identical'] is False
    assert r['source_ids']==['conv_1702b763a7ee'] and r['root_main_admission'] is False
    assert '1<=I<=1000000' in user and '0.01<=s<=0.99' in user and '1e-3<=C<=Pre' in user and 'tol只使用默认1e-6' in user
    assert not any(x.is_file() for x in (P/'state_before_write').rglob('*')) and not(P/'state_before_write/outputs/proportional_split.py').exists()
    assert 'new_authored' not in user.lower() and 'not_original' not in user.lower() and 'PASS' not in user
    # Full function code and finite test driver have been read independently;
    # no original or new program/helper is executed by this audit.
    spec=importlib.util.spec_from_file_location('math_cpu_peer',ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    compiler=m.CausalCompiler(BASE/'20261025_wrd_training_preflight/tokenizer_assets');profiles=[]
    other=row(BASE/'20261027_wrd_main_v10/historical_v6_action_recovery_01/helpers_construction_01/native_projection_01/native_helpers.full53.raw.jsonl.gz')
    for name in ['core7','full53']:
        ref=selection['profiles'][name];rr=row(P/ref['messages']['path']);cr=row(P/ref['compiled']['path']);assert rr['messages']==r['messages'] and rr['target_owner']==r['target_owner']
        if name=='full53':assert rr['tools']==other['tools'] and len(rr['tools'])==53
        kw=dict(compiler.tokenizers['primary_14b'].special_tokens_map);kw['enable_thinking']=False
        rendered=compiler.plain_compiled.render(messages=rr['messages'],tools=rr['tools'],documents=None,add_generation_prompt=False,**kw)
        a=compiler.tokenizers['primary_14b'](rendered,add_special_tokens=False,return_offsets_mapping=True);b=compiler.tokenizers['control_8b'](rendered,add_special_tokens=False,return_offsets_mapping=True)
        assert a==b and a['input_ids']==cr['input_ids'] and sha(rendered.encode())==cr['rendered_sha256']
        start=rendered.rindex('<tool_call>');end=rendered.rindex('</tool_call>')+len('</tool_call>')
        expected={i for i,(lo,hi) in enumerate(a['offset_mapping']) if start<=lo<hi<=end}
        assert expected=={i for lo,hi,comp,w in cr['supervision_spans'] for i in range(lo,hi)} and cr['supervised_tokens_by_component']=={'A':930}
        arrays={}
        for f in ref['arrays']:
            path=P/f['path'];v=array('I' if 'input_ids' in path.name else 'q' if 'labels' in path.name else 'f');v.frombytes(path.read_bytes());arrays[path.name]=v.tolist()
        ids=next(v for k,v in arrays.items() if 'input_ids' in k);labels=next(v for k,v in arrays.items() if 'labels' in k);weights=next(v for k,v in arrays.items() if 'weights' in k)
        assert ids==cr['input_ids'] and len(ids)==len(labels)==len(weights)
        for i,(token,label,weight) in enumerate(zip(ids,labels,weights)):
            assert (label==token and weight==.25) if i in expected else (label==-100 and weight==0)
        profiles.append({'profile':name,'total_tokens':cr['total_tokens'],'A':930,'R':0,'fresh_dual_tokenizer_ids_offsets_every_binary_label_and_weight':'PASS','end_markers_input_and_empty_R_zero':True})
    peer={'status':'PASS_SCOPED_MATHEMATICAL_CONSTRUCTION_PENDING_ROOT','reviewer':'Independent Codex AI, not human gold','full_new_program_read_characters':len(new),'full_original_program_read_characters':len(code),'full_driver_read':pin(driver),
        'source_review':pin(P/'SOURCE_REVIEW.json'),'portable':pin(P/'PORTABLE_SELECTION.json'),'original_single_SSE_policy_exact_code_restored':True,'original_LF_action_and_CRLF_physical_bytes_separately_verified':True,'original_functions_verbatim':functions,
        'independent_algebra':'For I>0,0<s<1, Post=I/s and Pre=I(1-s)/s>0. Given0<C<=Pre, New=IC/Pre, Reserve=I-New>=0 and New/(C+New)=I/(Pre+I)=s. WithoutC the unique numeric split is underdetermined; returning parameterized formulas is correct.',
        'validity_scope':'Explicit caller-supplied finite-float model1<=I<=1e6,0.01<=s<=.99,optional1e-3<=C<=Pre, defaulttol1e-6, non-optimized Python. This checks a declared mathematical model, not a financial/accounting/legal rule or actual enterprise deal.',
        'known_old_dispatch_defect_and_new_entrypoint':'Exact--increase token test sent equals-form flags to implicitfixed demo. New standard main alwaysparsesbothforms and noflagscannotfall back. Two original functions remain unchanged; new dispatch/header/imports are author curation.',
        'basic_validation_limits':['Ordinaryassertions;not fulltype/schema/NaN/permissions validator','C<=Pre+tol mayaccepttinyoverage but caller domainisC<=Pre','Caller-owned outputpath and overwrite/permissions;no pathauthorization promise','Nearoverflow/underflow/customtol/optimizedPython not within contracted scope'],
        'new_functional_input':'Fullordinaryarithmetic construction request; emptyoutputs, targetabsent, stdlibonly; nooldcodeororiginal/futurePASS included. Newuser explicitly suppliesmodelassumptions ratherthan pretending originalteacherinputequivalence.',
        'prior_and_new_evidence_separated':{'original_observation':pin(P/'original/02_observation.json'),'old_scope':'Onehistoricalfixedselfverification C1000andNone; nooriginalCLI proof andnoindependentbusinessgold','new_finite_QA':pin(P/'FINITE_RESOURCE_QA.json'),'new_scope':'60parametercombinations rationalFraction oracle; separate CLIcases;414finiteassertions withwrongarithmeticmutant. Drivercontainsindependent arithmetic expectations. No unseenqualificationorstudentbenefit proved.'},
        'resource_target_code_byte_identical_to_QA_resource':pin(newpath),'actual_native_tool_dispatch':False,'new_action_projection_not_original_tool_ABI_or_historical_nativewrite':True,
        'owner':r['target_owner'],'existing_original_R_owner_not_reexposed_or_resupervised':True,'profiles_mutually_exclusive':True,'profiles':profiles,
        'original_bank_and_main_manifest_modified':False,'new_native_Agent_model_business_training_runs':0,'training_started':False,'root_admission':False,'curation_cost':'UNKNOWN_NOT_ZERO'}
    save('PEER.json',peer);save('MANIFEST.json',{'files':[pin(OUT/'PEER.json'),pin(Path(__file__))],'audited_source_manifest':pin(P/'PORTABLE_SELECTION.json'),'status':peer['status'],'positive_admission_by_this_peer':False})
    print(json.dumps({'status':peer['status'],'peer_sha256':pin(OUT/'PEER.json')['sha256'],'manifest_sha256':pin(OUT/'MANIFEST.json')['sha256'],'profiles':profiles}))

if __name__=='__main__':main()
