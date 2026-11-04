"""Exact excerpt/edit/causal-state peer. No business execution."""
from array import array
import ast,gzip,hashlib,importlib.util,json,os,re,sys
from pathlib import Path
sys.dont_write_bytecode=True;os.environ['USE_TORCH']='0';os.environ['USE_TF']='0'
ROOT=Path('D:/skillloop');BASE=ROOT/'output/20261027_wrd_main_v10';P=BASE/'historical_v6_action_recovery_01/test_oracle_repair_01';OUT=Path(__file__).parent
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()).decode())
def row(p):return json.loads(next(gzip.open(p,'rt',encoding='utf-8')))
def pin(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)}
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def source(ref):p=Path(ref['path']);assert p.stat().st_size==ref['bytes']and digest(p)==ref['sha256'];return p
def portable(folder,ref):
    p=folder/ref['path']
    if not p.is_file():p=P.parent/ref['path']
    assert p.resolve().is_relative_to(P.parent.resolve())and p.stat().st_size==ref['bytes']and digest(p)==ref['sha256'];return p
def main():
    assert not(OUT/'PEER.json').exists()
    d=load(P/'SOURCE_STATE_AND_RANGES.json');old=source(d['original_old_test_script']).read_text(encoding='utf-8');new=source(d['new_original_two_literal_edits_result']).read_text(encoding='utf-8')
    excerpt=(P/'resources/original_contiguous_cumulative_R_excerpt.txt').read_text(encoding='utf-8');allR=gz(source(d['original_cumulative_R_response']))['choices'][0]['message']['reasoning_content']
    assert len(allR)==49942 and sha(allR.encode())==d['original_R_full_field_sha256']
    assert allR[d['original_R_excerpt_source_start']:d['original_R_excerpt_source_end']]==excerpt and len(excerpt)==1596 and sha(excerpt.encode())==d['original_R_excerpt_sha256']
    for x in d['positive_excerpt_ranges']+d['mask0_exclusions']:assert excerpt[x['start']:x['end']]==x['text']and sha(x['text'].encode())==x['text_sha256']
    q=gz(source(d['original_asof_request']));creator=gz(source(d['original_old_test_creator_response']))['choices'][0]['message'];patch=gz(source(d['original_action_response']))['choices'][0]['message']
    getcode=lambda m:json.loads(next(c for c in m['tool_calls']if c['function']['name']=='execute_python')['function']['arguments'])['code']
    ccode=getcode(creator);assignment=next(n for n in ast.parse(ccode).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='code'for t in n.targets));assert ast.literal_eval(assignment.value)==old
    assert q['messages'][48]==creator;feedback=json.loads(q['messages'][49]['content']);assert feedback==load(P/'resources/actual_previous_failed_test_observation.json')
    vals={n.targets[0].id:ast.literal_eval(n.value)for n in ast.parse(getcode(patch)).body if isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)and isinstance(n.value,ast.Constant)}
    args=load(source(d['native_edit']));assert len(args['edits'])==2 and args['path']=='/workspace/outputs/validation_history/edge_case_tests.py'
    text=old
    for i,e in enumerate(args['edits'],1):assert e=={'oldText':vals['old'+str(i)],'newText':vals['new'+str(i)]}and text.count(e['oldText'])==1;text=text.replace(e['oldText'],e['newText'])
    assert text==new
    # Independent literal arithmetic only; never executes candidate or tests.
    c2=' 北京某某科技有限公司 ';c3='上海某某厂'
    assert len(c2)==12 and(c2[:2],c2[-2:])==(' 北','司 ')and c2[:2]+'***'+c2[-2:]==' 北***司 '
    assert len(c3)==5 and c3[:2]+'***'+c3[-2:]=='上海***某厂'
    assert '"data_start_row": 2, "data_end_row": 3'in old and '"columns": ["客户名称", "联系电话"]'in old
    qa=load(P/'RESOURCE_QA.json');erp=Path(qa['execution_receipt_path']);execution=load(erp);assert digest(erp)==qa['execution_receipt_sha256']and execution['exit_code']==0
    assert qa['candidate_program_unchanged']and qa['candidate_program_sha256_before_after'].startswith('f3815290')and qa['old_failure_count']==2 and qa['new_failure_count']==0
    driver=(P/'resource_qa_01/workspace/qa_driver.py').read_text(encoding='utf-8');assert 'out[\'C2\'].value!=\' 北京***公司 \''in driver and 'out[\'C3\'].value!=\'上海某某厂\''in driver
    folder=P/'native_projection_01';sel=load(folder/'PORTABLE_SELECTION.json');raw=row(folder/'native_oracle.core7.raw.jsonl.gz');user=raw['messages'][1]['content']
    assert raw['messages'][-1]['reasoning_content']==excerpt and raw['actual_native_tool_dispatch']is False
    state=Path(raw['state_path']);assert digest(state/'outputs/validation_history/edge_case_tests.py')==sha(old.encode())
    assert digest(state/'outputs/candidate/scripts/run.py')==qa['candidate_program_sha256_before_after']
    assert old in user and json.loads(raw['messages'][-1]['tool_calls'][0]['function']['arguments'])==args
    logs='(logs already saved: run_edge_transposed.log + edge_case_tests_run1.log)';assert excerpt[1289:1361]==logs
    missing=[n for n in ['run_edge_transposed.log','edge_case_tests_run1.log']if not(state/'outputs/validation_history'/n).exists()]
    assert len(missing)==2
    # Existing source/schema/array mechanical correctness does not promote an
    # unsupported R claim. The candidate01 remains held for the local gaps.
    spec=importlib.util.spec_from_file_location('oracle_peer_compiler',ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    compiler=m.CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets');profiles=[]
    for name in ['core7','full53']:
        rr=row(portable(folder,sel['profiles'][name]['messages']));cr=row(portable(folder,sel['profiles'][name]['compiled']));kw=dict(compiler.tokenizers['primary_14b'].special_tokens_map);kw['enable_thinking']=False
        rendered=compiler.plain_compiled.render(messages=rr['messages'],tools=rr['tools'],documents=None,add_generation_prompt=False,**kw)
        a=compiler.tokenizers['primary_14b'](rendered,add_special_tokens=False,return_offsets_mapping=True);b=compiler.tokenizers['control_8b'](rendered,add_special_tokens=False,return_offsets_mapping=True);assert a==b and a['input_ids']==cr['input_ids']
        start=rendered.rindex('<|im_start|>assistant\n<think>\n')+len('<|im_start|>assistant\n<think>\n');assert rendered[start:start+len(excerpt)]==excerpt
        allowed=[(start+x['start'],start+x['end'])for x in d['positive_excerpt_ranges']]+[(start+len(excerpt)+len('\n</think>\n\n'),rendered.rindex('<|im_end|>\n'))]
        expected={i for i,(x,y)in enumerate(a['offset_mapping'])if x<y and any(lo<=x and y<=hi for lo,hi in allowed)};assert expected=={i for lo,hi,c,w in cr['supervision_spans']for i in range(lo,hi)}
        arrays={}
        for ref in sel['profiles'][name]['arrays']:
            p=portable(folder,ref);kind='I'if'input_ids'in p.name else'q'if'labels'in p.name else'f';v=array(kind);v.frombytes(p.read_bytes());arrays[p.name]=v.tolist()
        ids=next(v for k,v in arrays.items()if'input_ids'in k);labels=next(v for k,v in arrays.items()if'labels'in k);weights=next(v for k,v in arrays.items()if'weights'in k);assert ids==cr['input_ids']
        for i,(token,label,w)in enumerate(zip(ids,labels,weights)):assert(label==token and w==.25)if i in expected else(label==-100 and w==0)
        profiles.append({'profile':name,'tokens':cr['total_tokens'],'components':cr['supervised_tokens_by_component'],'fresh_dual_tokenizer_all_IDs_offsets':'PASS','binary_every_label_weight':'PASS',
            'unsupported_logs_claim_tokens_currently_positive':sum(start+1289<=x<y<=start+1361 and i in expected for i,(x,y)in enumerate(a['offset_mapping']))})
    peer={'status':'HOLD_LOCAL_R_PREMISE_AND_BACKUP_STATE_GAP_NOT_WHOLE_ORACLE_REPAIR_REJECTION','reviewer':'Independent Codex AI, not human gold','source_and_ranges':pin(P/'SOURCE_STATE_AND_RANGES.json'),
        'whole_original_test_read_characters':len(old),'whole_original_test_and_QA_driver_read':True,'original1596char_excerpt_entirely_read':True,
        'contiguous_original_cumulative_R_source_exact':{'start':47691,'end':49287,'full_chars':49942,'full_sha256':sha(allR.encode()),'excerpt_sha256':sha(excerpt.encode())},
        'not_original025_per_turn_reasoning_or_faithfulness_claim':True,'originalR_owner_distinct_from_originalA_owner':raw['target_owner'],
        'old024_full_test_in_actual025_request':True,'old024_two_FAIL_whole_tool_observation_in_actual025_request':True,
        'two_literal_oracle_edits_exact_original025_and_new_SHA':sha(new.encode()),'independent_C2_C3_codepoint_and_inclusive_region_reasoning':'PASS',
        'candidate_change_required_for_these_two_failures':False,'candidate_unchanged_only_target_test_oracles_changed':True,
        'existing57char_zero_exclusions_appropriate':True,'local_issues':[{'field':'reasoning_content','start':1289,'end':1361,'text':logs,'text_sha256':sha(logs.encode()),
            'reason':'Both named logs were created in original historical024 wrapper, but neither is mounted/asserted as known in this new4file state. Preserve original text, require extra mask0 or actual pre-existing log evidence.'},
            {'field':'functional_state','reason':'User asks pre-revision script preserved; only current target file in4file state, no immutable backup explicitly available. Clarify existing version preservation or provide a read-only old-test backup before edit. Do not turn planned snapshot into executed observation.'}],
        'reasonable_snapshot_revision_note_and_retest_plans_not_rejected_for_being_future':True,
        'resource_QA':pin(P/'RESOURCE_QA.json'),'execution_receipt':pin(erp),'QA_driver':pin(P/'resource_qa_01/workspace/qa_driver.py'),
        'QA_scope':'31 finite checks0FAIL after2 oracle corrections, two old wrong oracles independently rejected, fixed candidate SHA unchanged; not complete workbook/business correctness.',
        'other_test_limit':'Existing edge_basic_style expression reduces to style_ok and only checks finite B2 properties. No whole-test/program quality approval.',
        'profiles':profiles,'original01_bytes_not_changed':True,'new_business_or_model_or_Agent_runs':0,'training_started':False,'root_admission':False,'curation_cost':'UNKNOWN_NOT_ZERO'}
    save(OUT/'PEER.json',peer);save(OUT/'MANIFEST.json',{'files':[pin(OUT/'PEER.json'),pin(Path(__file__))],'status':peer['status'],'originals_unchanged':True,'training_started':False})
    print(json.dumps({'status':peer['status'],'peer_sha256':digest(OUT/'PEER.json'),'manifest_sha256':digest(OUT/'MANIFEST.json')}))
if __name__=='__main__':main()
