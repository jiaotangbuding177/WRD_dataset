"""Independent direct-token, resource, owner and array QA for new v6 views."""
from __future__ import annotations
from array import array
from collections import Counter
import importlib.util,os,sys
os.environ['USE_TORCH']='0';os.environ['USE_TF']='0'
from build_historical_v6_native_repair_01 import ROOT,OUT,OLD,AUDIT,IDS,load,rows,save,dump,digest,sha,js,readtxt,old_contexts,code

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def write_bin(path,code,values):
    a=array(code,values)
    if sys.byteorder!='little':a.byteswap()
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(a.tobytes())
    return {'path':str(path.relative_to(OUT)),'bytes':path.stat().st_size,'sha256':digest(path)}
def main():
    assert not (OUT/'DIRECT_TOKEN_AND_RESOURCE_QA.json').exists()
    compiler_module=module(ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py','v6_projection_independent_tokenizer')
    compiler=compiler_module.CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
    core=list(rows(OUT/'native_adaptation.core7.jsonl.gz'));full=list(rows(OUT/'native_adaptation.full53.jsonl.gz'))
    compiled_dir=ROOT/'output/20261027_wrd_main_v10/compiled/historical_v6_native_repair_01'
    compiled={r['id']:r for p in compiled_dir.glob('*.train.*.jsonl.gz')for r in rows(p)}
    assert len(core)==len(full)==len(compiled)==3
    capture=load(OUT/'TOOLS_CAPTURE_53.json');original=load(__import__('pathlib').Path(capture['original_capture']['path']))
    assert capture['tools']==original['tools']and len(original['tools'])==53
    assert digest(__import__('pathlib').Path(capture['original_capture']['path']))==capture['original_capture']['sha256']
    owners=set();stats=[];bins=[];conditional=[];origins=Counter()
    from jsonschema import Draft202012Validator
    for raw,complete in zip(core,full):
        assert raw['messages']==complete['messages']and raw['target_owner']==complete['target_owner']
        owner=raw['target_owner']['exposure_owner_id'];assert owner not in owners;owners.add(owner)
        assert raw['root_main_admission']is False and raw['loss_multiplier']==0.25
        assert raw['message_loss_mask']==[0,0,1]and raw['rationale_provenance']=='NEW_AUTHORED_CONCISE_RATIONALE_NOT_ORIGINAL_TEACHER_COT'
        target=raw['messages'][2];fn=target['tool_calls'][0]['function'];registry={t['function']['name']:t['function']for t in capture['tools']}
        Draft202012Validator(registry[fn['name']]['parameters']).validate(__import__('json').loads(fn['arguments']))
        assert all(t['function']==registry[t['function']['name']]for t in raw['tools'])
        for view,result in [('core7',compiled[raw['id']]),('full53',None)]:
            item=raw if view=='core7'else complete
            if result is None:
                result=compiler.compile_messages(item['messages'],item['tools'],{2:{'id':item['id']+':m2','mechanical_usable':True}},independent=False)
                # Explicit R and A only; formatting/cross-boundary tokens0.
                ss=[[a,b,c,w*.25]for a,b,c,w in result['supervision_spans']if c in {'R','A'}]
                cc=Counter()
                for a,b,c,w in ss:cc[c]+=b-a
                result.update({'supervision_spans':ss,'supervised_tokens_by_component':dict(cc),'supervised_tokens':sum(cc.values()),
                    'schema_version':item['schema_version'],'id':item['id'],'messages':item['messages'],'tools':item['tools'],
                    'target_owner':item['target_owner'],'default_active':False,'root_main_admission':False,'profile':'FULL53_CONDITIONAL_64K_NO_SILENT_TRUNCATION',
                    'bank':item['bank'],'stage':item['stage'],'split':item['split'],'source_ids':item['source_ids'],'source_group_id':item['source_group_id'],
                    'annotation_provenance':item['annotation_provenance'],'original_record_metadata':{k:v for k,v in item.items()if k not in {'messages','tools'}}})
                for target_meta in result['targets']:
                    target_meta['owned_supervision_spans']=[[a,b,c,w*.25]for a,b,c,w in target_meta['owned_supervision_spans']if c in {'R','A'}]
                    target_meta['supervised_tokens']=sum(b-a for a,b,c,w in target_meta['owned_supervision_spans'])
                result['supervision_spans_sha256']=sha(js(ss).encode())
                assert 32768<result['total_tokens']<=65536
                conditional.append(result)
            kwargs=dict(compiler.tokenizers['primary_14b'].special_tokens_map);kwargs['enable_thinking']=False
            rendered=compiler.plain_compiled.render(messages=item['messages'],tools=item['tools'],documents=None,add_generation_prompt=False,**kwargs)
            primary=compiler.tokenizers['primary_14b'](rendered,add_special_tokens=False,return_offsets_mapping=True)
            control=compiler.tokenizers['control_8b'](rendered,add_special_tokens=False,return_offsets_mapping=True)
            assert primary==control and primary['input_ids']==result['input_ids']
            pos=rendered.rfind('<|im_start|>assistant\n');assert pos>=0
            start=pos+len('<|im_start|>assistant\n<think>\n');end=start+len(target['reasoning_content'])
            assert rendered[start:end]==target['reasoning_content']
            action_start=end+len('\n</think>\n\n');action_end=len(rendered)-len('<|im_end|>\n')
            assert rendered[action_start:action_end].lstrip().startswith('<tool_call>')
            expected={i for i,(a,b)in enumerate(primary['offset_mapping'])if a<b and(start<=a and b<=end or action_start<=a and b<=action_end)}
            actual={i for a,b,c,w in result['supervision_spans']for i in range(a,b)}
            assert expected==actual,(item['id'],len(expected),len(actual),sorted(expected^actual)[:8])
            labels=[-100]*len(primary['input_ids']);weights=[0.0]*len(labels)
            for i in expected:labels[i]=primary['input_ids'][i];weights[i]=.25
            for i in range(len(labels)):
                assert (labels[i]==primary['input_ids'][i]and weights[i]==.25)if i in expected else(labels[i]==-100 and weights[i]==0)
            name=raw['id'].split(':')[1]
            for suffix,kind,values in [('input_ids.u32le.bin','I',primary['input_ids']),('labels.i64le.bin','q',labels),('weights.f32le.bin','f',weights)]:
                bins.append(write_bin(OUT/'arrays'/view/name/suffix,kind,values))
            stats.append({'id':item['id'],'profile':view,'input_tokens':len(labels),'supervised_tokens':len(expected),
                'components':result['supervised_tokens_by_component'],'independent_both_tokenizers_all_tokens_and_offsets':True,
                'direct_all_positions_mask_and_weights':True,'core_full_same_owner_mutually_exclusive':True})
            if view=='core7':origins.update({'new_authored_R':result['supervised_tokens_by_component']['R'],'new_authored_native_action_projection_A':result['supervised_tokens_by_component']['A']})
    dump(OUT/'native_adaptation.full53.conditional64k.compiled.v2.jsonl.gz',conditional)
    a=load(OUT/'OFFLINE_ACTIONS.json');old=readtxt(OUT/'states/report_edit/outputs/candidate/scripts/run.py');new=old
    for edit in a['report_edits']:assert new.count(edit['oldText'])==1;new=new.replace(edit['oldText'],edit['newText'])
    assert sha(new.encode())==a['new_program_sha256']==digest(OUT/'states/runner_fix/outputs/candidate/scripts/run.py')
    bad=readtxt(OUT/'states/runner_fix/work/batch_runner.py');fixed=bad
    for oldline,newline in [(a['runner_old_line'],a['runner_new_line']),(a['runner_metadata_old_line'],a['runner_metadata_new_line'])]:
        assert fixed.count(oldline)==1;fixed=fixed.replace(oldline,newline)
    assert sha(fixed.encode())==a['fixed_runner_sha256']==digest(OUT/'states/verify_local/work/batch_runner.py')
    qa=load(OUT/'RESOURCE_QA.json');assert [(x['name'],x['exit_code'])for x in qa['steps']]==[
        ('bad_batch',0),('bad_evidence_check',1),('fixed_batch',0),('fixed_evidence_check',0),('wrong_check5_hash',1),('wrong_check6_selected',1),('restored_evidence_check',0)]
    assert not (OUT/'states/verify_local/outputs/local_evidence_verification.json').exists()
    current=next(x for x in rows(ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz')if x['source_id']=='conv_b5e6f3d3bab9')
    assert current['status']=='TRAIN'and all(x['source_group_id']==current['component_id']for x in core)
    # All files promised in the common manifest are actual byte-identical files
    # in each staged state, including binaries, not just a JSON filename list.
    checks=0
    for state in ['report_edit','runner_fix','verify_local']:
        for p in (OUT/'resources/common').rglob('*'):
            if p.is_file():
                q=OUT/'states'/state/p.relative_to(OUT/'resources/common');assert q.is_file()and digest(q)==digest(p);checks+=1
    receipts=[load(p)for p in OUT.glob('resource_qa*/EXECUTION_RECEIPT.json')]
    assert len(receipts)==3 and [r['exit_code']for r in receipts].count(0)==1
    save(OUT/'RESOURCE_QA_COST_LEDGER.json',{'resource_QA_attempts':len(receipts),'failed_attempts_retained':2,
        'measured_total_container_wall_seconds':sum(r['wall_seconds']for r in receipts),'attempts':receipts,
        'separate_CPU_user_system_time':'UNKNOWN_NOT_ZERO','cash':'UNKNOWN_NOT_ZERO','Codex_curation_cost':'UNKNOWN_NOT_ZERO',
        'model_calls':0,'native_agent_sessions':0,'training':False,'no_failed_author_mapping_positive_labels':True})
    save(OUT/'DIRECT_TOKEN_AND_RESOURCE_QA.json',{'status':'PASS_SCOPED_LOCAL_NEW_AUTHOR_BANK_PENDING_ROOT','core_sequences':3,
        'core_input_tokens':sum(r['input_tokens']for r in stats if r['profile']=='core7'),'core_supervised_tokens':sum(origins.values()),
        'core_origins':dict(origins),'core_all_le16k':all(r['input_tokens']<=16384 for r in stats if r['profile']=='core7'),
        'conditional_full53_sequences':3,'conditional_not_default':True,'profiles_same_three_owners_not_six_targets':True,
        'schema_from_real53_capture_exact':True,'states_have_complete_promised_files_verified':checks,
        'exact_old_new_report_program_and_runner':True,'all_binaries_written_and_checked':bins,'rows':stats,
        'future_verification_PASS_not_in_states':True,'no_whole_package_or_retain_credit':True,
        'original_hidden_R_reused':0,'original_E_reused':0,'old_v6_labels_auto_inherited':False,
        'weights_loaded':False,'training_started':False,'native_tool_dispatch':False,'AI_annotation_cost':'UNKNOWN_NOT_ZERO'})
    print(js({'status':'PASS','rows':stats,'origins':dict(origins),'binary_files':len(bins)}))
if __name__=='__main__':main()
