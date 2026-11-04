"""Independent exact delta/array check; no candidate/test/model execution."""
from pathlib import Path
from array import array
import importlib.util,json,os,sys
sys.dont_write_bytecode=True
os.environ['USE_TORCH']='0';os.environ['USE_TF']='0'
HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('prior_peer',HERE.parent/'oracle01/audit.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

def main():
    assert not(HERE/'PEER.json').exists()
    oldfolder=p.P/'native_projection_01';folder=p.P/'native_projection_02'
    revision=p.load(folder/'SEMANTIC_REVISION.json')
    a=p.row(oldfolder/'native_oracle.core7.raw.jsonl.gz');b=p.row(folder/'native_oracle.core7.raw.jsonl.gz')
    assert a['messages'][-1]==b['messages'][-1] and a['target_owner']==b['target_owner']
    assert b['actual_native_tool_dispatch'] is False and b['root_main_admission'] is False
    state=Path(b['state_path']);before=Path(a['state_path'])
    oldfiles={str(x.relative_to(before)).replace('\\','/'):p.digest(x) for x in before.rglob('*') if x.is_file()}
    newfiles={str(x.relative_to(state)).replace('\\','/'):p.digest(x) for x in state.rglob('*') if x.is_file()}
    backup='inputs/previous_failed_edge_case_tests.py'
    assert set(newfiles)-set(oldfiles)=={backup} and all(newfiles[k]==v for k,v in oldfiles.items())
    assert newfiles[backup]==oldfiles['outputs/validation_history/edge_case_tests.py']=='6d300f207207d163b8a5b8d9b0cfc731228943e07e0b66b7e493ab4260dd5469'
    assert 'inputs/previous_failed_edge_case_tests.py' in b['messages'][1]['content']
    excerpt=b['messages'][-1]['reasoning_content'];assert len(excerpt)==1596
    assert revision['new_withdrawal']['start']==1289 and revision['new_withdrawal']['end']==1361
    for x in revision['mask0_exclusions']+revision['positive_excerpt_ranges']:
        assert excerpt[x['start']:x['end']]==x['text'] and p.sha(x['text'].encode())==x['text_sha256']
    assert sum(x['end']-x['start'] for x in revision['positive_excerpt_ranges'])==1467
    sel=p.load(folder/'PORTABLE_SELECTION.json')
    s=importlib.util.spec_from_file_location('oracle02_cpu_compiler',p.ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    compiler=m.CausalCompiler(p.ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
    profiles=[]
    for name in ['core7','full53']:
        rr=p.row(p.portable(folder,sel['profiles'][name]['messages']));cr=p.row(p.portable(folder,sel['profiles'][name]['compiled']))
        assert rr['messages']==b['messages'] and rr['target_owner']==b['target_owner']
        kw=dict(compiler.tokenizers['primary_14b'].special_tokens_map);kw['enable_thinking']=False
        rendered=compiler.plain_compiled.render(messages=rr['messages'],tools=rr['tools'],documents=None,add_generation_prompt=False,**kw)
        t=compiler.tokenizers['primary_14b'](rendered,add_special_tokens=False,return_offsets_mapping=True)
        control=compiler.tokenizers['control_8b'](rendered,add_special_tokens=False,return_offsets_mapping=True)
        assert t==control and t['input_ids']==cr['input_ids']
        start=rendered.rindex('<|im_start|>assistant\n<think>\n')+len('<|im_start|>assistant\n<think>\n')
        assert rendered[start:start+1596]==excerpt
        allowed=[(start+x['start'],start+x['end']) for x in revision['positive_excerpt_ranges']]
        allowed.append((start+1596+len('\n</think>\n\n'),rendered.rindex('<|im_end|>\n')))
        expected={i for i,(lo,hi) in enumerate(t['offset_mapping']) if lo<hi and any(x<=lo and hi<=y for x,y in allowed)}
        assert expected=={i for lo,hi,c,w in cr['supervision_spans'] for i in range(lo,hi)}
        for excluded in revision['mask0_exclusions']:
            x,y=start+excluded['start'],start+excluded['end']
            assert not any(i in expected and lo<y and x<hi for i,(lo,hi) in enumerate(t['offset_mapping']))
        arrays={}
        for ref in sel['profiles'][name]['arrays']:
            f=p.portable(folder,ref);values=array('I' if 'input_ids' in f.name else 'q' if 'labels' in f.name else 'f');values.frombytes(f.read_bytes());arrays[f.name]=values.tolist()
        ids=next(v for k,v in arrays.items() if 'input_ids' in k);labels=next(v for k,v in arrays.items() if 'labels' in k);weights=next(v for k,v in arrays.items() if 'weights' in k)
        assert ids==cr['input_ids'] and len(ids)==len(labels)==len(weights)
        for i,(token,label,weight) in enumerate(zip(ids,labels,weights)):
            assert (label==token and weight==.25) if i in expected else (label==-100 and weight==0)
        assert cr['supervised_tokens_by_component']=={'R':391,'A':457}
        profiles.append({'profile':name,'total_tokens':cr['total_tokens'],'supervised_tokens_by_component':cr['supervised_tokens_by_component'],'fresh_dual_tokenizer_ids_offsets':'PASS','every_binary_label_weight':'PASS','all_tokens_crossing_each_exclusion_zero':'PASS'})
    receipt={'status':'PASS_SCOPED_ORACLE02_EXACT_TWO_LOCAL_REPAIRS_PENDING_ROOT','reviewer':'Independent Codex AI; not human gold','parent_independent_peer':p.pin(HERE.parent/'oracle01/PEER.json'),
        'parent01_remains_HOLD_and_unchanged':True,'semantic_revision':p.pin(folder/'SEMANTIC_REVISION.json'),'portable_selection':p.pin(folder/'PORTABLE_SELECTION.json'),
        'target_complete_original1596char_excerpt_and_two_edits_unchanged':True,'original_cumulative_R_not_original025_per_turn_faithful_CoT':True,
        'extra72char_saved_logs_claim_preserved_but_all_overlap_tokens_zero':True,'new_input_backup_exact_old_test':p.pin(state/backup),'all_four_original_state_files_byte_identical':True,
        'new_functional_input_read_in_full':'Ordinary task, explicit read-only backup and preservation; no future PASS or new test solution added. Original logs are not claimed available as functional files.',
        'remaining_snapshot_revision_note_rerun_text_is_plan_not_execution':True,'two_C2_C3_oracle_fixes_and_asof_premises':'Previously independently reviewed; unchanged. No global candidate or full31-test business correctness approval.',
        'owner':b['target_owner'],'profiles_mutually_exclusive':True,'profiles':profiles,'actual_native_tool_dispatch':False,'original_bank_files_modified':False,
        'new_Agent_model_business_runs':0,'training_started':False,'root_admission':False,'curation_cost':'UNKNOWN_NOT_ZERO'}
    p.save(HERE/'PEER.json',receipt)
    p.save(HERE/'MANIFEST.json',{'files':[p.pin(HERE/'PEER.json'),p.pin(Path(__file__))],'status':receipt['status'],'training_started':False})
    print(json.dumps({'status':receipt['status'],'peer_sha256':p.digest(HERE/'PEER.json'),'manifest_sha256':p.digest(HERE/'MANIFEST.json'),'profiles':profiles}))

if __name__=='__main__':main()
