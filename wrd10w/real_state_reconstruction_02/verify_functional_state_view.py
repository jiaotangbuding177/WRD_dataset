"""Offline check of the functional projection and optional compiled arrays."""
import gzip,hashlib,json,re,sys
from array import array
from collections import Counter
from pathlib import Path
from jsonschema import Draft202012Validator
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'real_state_reconstruction_01'
COMP=HERE.parent/'compiled/real_state_repair_02'
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def sha(b):return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text('utf-8-sig'))
def rows(p):return [json.loads(l) for l in gzip.open(p,'rt',encoding='utf-8-sig')]
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def intsha(ids):
    a=array('I',ids)
    if sys.byteorder!='little':a.byteswap()
    return sha(a.tobytes())
current=rows(HERE/'real_state_tasks.jsonl.gz')
old={r['id']:r for r in rows(OLD/'real_state_tasks.jsonl.gz')}
closure=load(HERE/'SOURCE_RECEIPTS.json')
immutable=load(HERE/'VIEW_01_IMMUTABILITY_CHECK.json')
for f in immutable['files']:
    b=(OLD/f['relative_path']).read_bytes()
    assert sha(b)==f['sha256'] and len(b)==f['bytes']
for f in closure['files']:
    b=(HERE/f['archive_object']).read_bytes()
    assert sha(b)==f['sha256'] and len(b)==f['bytes']
    assert Path(f['path']).read_bytes()==b
checks=[]
for r in current:
    prior=old[r['previous_candidate_view']['record_id']]
    assert r['source_ids']==prior['source_ids'] and r['source_group_id']==prior['source_group_id'] and r['split']=='train'
    assert r['target_owner']==prior['target_owner'] and r['messages'][2]==prior['messages'][2]
    assert r['tools']==prior['tools'] and r['message_loss_mask']==[0,0,1] and r['loss_multiplier']==0.5
    assert r['source_receipts']['sha256']==sha((HERE/'SOURCE_RECEIPTS.json').read_bytes())
    assert r['root_main_admission'] is False
    text=r['messages'][0]['content']+'\n'+r['messages'][1]['content']
    for marker in ['NEW_AUTHORED_STATE_TASK','NEW_AI_SILVER_AUTHOR','native_message_index','exact_message_sha256','first_delivered_in_compatible_call_id','parent_job_id','parent_job_sha256','D:\\skillloop','sameinput','原模型当时','来源投影','研究整理','EXACT_DIRECT_REVISION_JOB_RESOURCE','AVAILABLE_ONLY_NOT_READ_IN_NEW_INPUT']:
        assert marker not in text,(r['id'],marker)
    assert not re.search(r'\bcall[a-f0-9]{20,}\b',text)
    assert not re.search(r'\b\d{4}_[a-f0-9]{32}\b',text)
    assert 'UNKNOWN' in text and '1800' in text and '32768' in text
    for future in ['RESOURCE_REVIEW.json','21+8','COMPILE_OK','=== FIXED 1:','new_independent_cases_passed']:
        assert future not in text
    blocks=re.findall(r'<file path=("[^"\n]+") sha256=("[a-f0-9]+")>\n(.*?)\n</file>',r['messages'][1]['content'],re.S)
    oldblocks={json.loads(p):(json.loads(s),t) for p,s,o,t in re.findall(r'<recorded_file path=("[^"\n]+") sha256=("[a-f0-9]+") origin=("[^"]+")>\n(.*?)\n</recorded_file>',prior['messages'][1]['content'],re.S)}
    assert len(blocks)==10
    for p,s,t in blocks:
        path=json.loads(p); digest=json.loads(s)
        assert sha(t)==digest and oldblocks[path]==(digest,t)
    assert set(r['necessary_input_resource_paths'])=={json.loads(p) for p,s,t in blocks}
    prior_obs=re.findall(r'<delivered_native_observation[^>]+>\n(.*?)\n</delivered_native_observation>',prior['messages'][1]['content'],re.S)
    now_obs=re.findall(r'<observation>\n(.*?)\n</observation>',r['messages'][1]['content'],re.S)
    assert now_obs==prior_obs
    functional=oldblocks['/workspace/inputs/independent/actual_repair_feedback.json'][1]
    f=json.loads(functional)
    retained={k:v for k,v in f.items() if k not in r['functional_feedback_projection']['removed_source_metadata']}
    assert json.dumps(retained,ensure_ascii=False,indent=2) in r['messages'][1]['content']
    schema={t['function']['name']:t['function'] for t in r['tools']}
    call=r['messages'][2]['tool_calls'][0]
    assert not list(Draft202012Validator(schema[call['function']['name']]['parameters']).iter_errors(json.loads(call['function']['arguments'])))
    assert sha(call['function']['arguments'])==r['target_owner']['exact_function_arguments_sha256_utf8']
    checks.append({'id':r['id'],'status':'PASS','complete_file_texts_preserved':10,'actual_observations_preserved':len(now_obs),
                   'same_R_action_owner_schema_and_train_ancestry':True,'source_metadata_outside_input':True,'functional_feedback_preserved':True})
save(HERE/'FUNCTIONAL_SOURCE_CLOSED_QA.json',{'status':'PASS_SELF_REVIEW_PENDING_ROOT','checks':checks,'source_files_checked':len(closure['files']),
    'view01_unchanged':True,'one_view_only_for_training':True,'new_model_calls':0,'native_actions_reexecuted':0,'training_started':False})
if (COMP/'COMPILATION_REPORT.json').exists():
    report=load(COMP/'COMPILATION_REPORT.json')
    assert report['immutable_inputs'][0]['sha256']==sha((HERE/'real_state_tasks.jsonl.gz').read_bytes())
    assert report['tokenizer_proof']['independent_second_tokenizer_calls']==3
    assert list(gzip.open(COMP/'held.jsonl.gz','rt',encoding='utf-8-sig'))==[]
    original={r['id']:r for r in current}; totals=Counter(); seq=[]; seen=set()
    for p in COMP.glob('real_state_repair_main.*.jsonl.gz'):
        for r in rows(p):
            seen.add(r['id']); s=original[r['id']]
            assert r['messages']==s['messages'] and r['tools']==s['tools']
            assert r['total_tokens']==len(r['input_ids'])<=32768
            assert intsha(r['input_ids'])==r['input_ids_sha256_u32le']
            assert sha(js(r['supervision_spans']))==r['supervision_spans_sha256']
            assert r['tokenizer_pair_proof']=='independent_call_equal' and r['second_tokenizer_independently_called'] is True
            labels=[-100]*len(r['input_ids']); counts=Counter()
            for a,b,c,w in r['supervision_spans']:
                assert 0<=a<b<=len(labels) and c in ('R','A') and w==0.5
                assert all(x==-100 for x in labels[a:b])
                labels[a:b]=r['input_ids'][a:b]; counts[c]+=b-a
            assert dict(counts)==r['supervised_tokens_by_component'] and sum(counts.values())==r['supervised_tokens']
            assert r['targets'][0]['message_index']==2 and len(r['targets'])==1
            totals['sequences']+=1;totals['input_tokens']+=len(labels);totals['supervised_tokens']+=sum(counts.values())
            totals['new_ai_silver_R']+=counts['R'];totals['exact_original_A']+=counts['A']
            seq.append({'id':r['id'],'total_tokens':len(labels),'supervised_tokens':sum(counts.values()),'components':dict(counts),
                        'mask_and_weights_verified':True,'double_tokenizer_equal':True,'no_truncation':True})
    assert seen==set(original) and totals['sequences']==3
    save(HERE/'COMPILED_BANK_QA.json',{'status':'PASS','counts':dict(totals),'sequence_checks':seq,'loss_multiplier':0.5,
         'effective_weighted_supervision_tokens':totals['supervised_tokens']*0.5,'distinct_action_owners':3,'distinct_parent_chains':1,
         'distinct_source_ids':3,'distinct_source_groups':1,'root_admission_pending':True,'one_view_only_for_training':True,
         'new_model_calls':0,'native_actions_reexecuted':0,'training_started':False,'active_main_manifest_changed':False})
    print(js({'source_closed':'PASS','compiled':'PASS','counts':dict(totals),'sequence_tokens':[s['total_tokens'] for s in seq]}))
else:print(js({'source_closed':'PASS','compiled':'NOT_YET_RUN','records':len(current)}))
