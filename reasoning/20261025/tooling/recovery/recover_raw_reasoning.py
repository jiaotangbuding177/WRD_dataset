"""Recover original historical request/response bodies, keeping them controlled.

No model, Agent, native runtime, training or source modification is performed.
"""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import time

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261025_wrd_reasoning_recovery_v4'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def blobsha(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def writeline(f,x):f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
def message_body(m):return {k:v for k,v in m.items() if k not in {'reasoning_content','reasoning','thinking','usage'}}
def source_ref(p):return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}

def main():
    started=time.monotonic();source=OUT/'RAW_REASONING_PAIRS_AUDIT.json';audit=load(source);dest=OUT/'controlled';dest.mkdir(exist_ok=True)
    allpath=dest/'raw_pairs.all.jsonl.gz';mechanicalpath=dest/'raw_pairs.nonformal.mechanical.jsonl.gz';runpath=dest/'raw_run_trajectories.jsonl.gz'
    for p in [allpath,mechanicalpath,runpath]:
        if p.exists():raise ValueError('new raw recovery files required')
    counts=defaultdict(Counter);run_groups=defaultdict(list);all_input_hashes={};reasonings=set()
    with gzip.open(allpath,'wt',encoding='utf-8',newline='\n',compresslevel=3) as af,gzip.open(mechanicalpath,'wt',encoding='utf-8',newline='\n',compresslevel=3) as mf:
        for meta in audit['pairs']:
            rp=Path(meta['response_path']);qp=Path(meta['request_path']);assert sha(rp)==meta['response_sha256'] and sha(qp)==meta['request_sha256']
            q=load(qp);r=load(rp);message=(r.get('choices')or[{}])[0].get('message')or{};messages=q.get('messages')or[]
            why=message.get('reasoning_content')or'';sc=meta['scope'];c=counts[sc];c['raw_pairs']+=1;c['reasoning_pairs']+=bool(why);c['reasoning_characters']+=len(why)
            errors=[]
            if not messages:errors.append('missing_request_messages')
            if message.get('role')!='assistant':errors.append('response_role_not_assistant')
            if not (message.get('content') or message.get('tool_calls') or why):errors.append('empty_assistant_response')
            if meta['history_unmatched_tool_result_count']:errors.append('orphan_tool_result_in_request_history')
            excluded=sc in {'formal_evaluation_exclude','technical_fixture_exclude'}
            if excluded:errors.append(sc)
            mechanical=not errors
            item={'schema_version':'wrd-historical-raw-pair-v4','id':blobsha({'request':meta['request_sha256'],'response':meta['response_sha256']})[:24],
                'run_id':blobsha(meta['run_path'])[:24],'run_path':meta['run_path'],'request_ordinal':meta['request_ordinal'],
                'historical_condition':'historical_selfbuilt_executor_before_native_only_correction_not_current_native_training_equivalence',
                'role_scope':sc,'original_model':q.get('model') or r.get('model'),'original_request':q,'original_response':r,
                'original_response_finish_reason':(r.get('choices')or[{}])[0].get('finish_reason'),
                'stream_reconstruction_state':'complete_saved_nonstream_raw_response_no_stream_invented','original_request_stream_flag':q.get('stream'),
                'original_reasoning_pointer':'/choices/0/message/reasoning_content' if why else None,'original_reasoning_characters':len(why),
                'original_usage':r.get('usage'),'source_request':source_ref(qp),'source_response':source_ref(rp),
                'context_is_exact_observed_request':True,'future_artifacts_added_to_prompt':False,
                'mechanical_usable':mechanical,'mechanical_exclusion_reasons':errors,
                'source_role_audit_pending':sc=='historical_business_actor_or_validation_requires_source_audit',
                'semantic_approved':False,'training_admitted':False,'human_gold':False,'publication_approved':False,
                'policy':'controlled originals; this export does not certify semantics or permission to publish'}
            writeline(af,item)
            if mechanical:writeline(mf,item);c['mechanically_usable_nonformal_pairs']+=1
            run_groups[meta['run_path']].append(item);all_input_hashes[str(rp)]=meta['response_sha256'];all_input_hashes[str(qp)]=meta['request_sha256']
            if why:reasonings.add(hashlib.sha256(why.encode()).hexdigest())
    runstats=Counter();continuities=Counter()
    with gzip.open(runpath,'wt',encoding='utf-8',newline='\n',compresslevel=3) as rf:
        for runstr,items in sorted(run_groups.items()):
            items.sort(key=lambda x:int(x['request_ordinal']));run=Path(runstr);steps=[]
            for i,item in enumerate(items):
                req=item['original_request'];messages=req['messages'];step={'pair_id':item['id'],'request_ordinal':item['request_ordinal'],
                    'request_messages':messages,'request_tools':req.get('tools'),
                    'actual_response_message':(item['original_response']['choices'][0].get('message')or{}),
                    'actual_finish_reason':item['original_response_finish_reason'],'source_request':item['source_request'],'source_response':item['source_response']}
                if i+1<len(items):
                    nxt=items[i+1]['original_request']['messages'];prefix=nxt[:len(messages)]==messages
                    observed=nxt[len(messages):] if prefix else []
                    actual=message_body(step['actual_response_message']);match=any(m.get('role')=='assistant' and message_body(m)==actual for m in observed)
                    step['next_request_has_exact_current_prefix']=prefix;step['next_request_contains_current_response_body']=match
                    step['observations_before_next_response']=observed if prefix else None
                    continuities['adjacent_raw_pairs']+=1;continuities['exact_request_prefix_continuations']+=prefix;continuities['response_body_found_in_next_request_delta']+=match
                steps.append(step)
            final=items[-1]['original_response'];finish=items[-1]['original_response_finish_reason'];resultp=run/'result.json';inputp=run/'input_packet.json';finalp=run/'messages_final.json'
            result=load(resultp) if resultp.is_file() else None
            rr={'schema_version':'wrd-historical-raw-trajectory-v4','run_id':items[0]['run_id'],'run_path':runstr,'role_scope':items[0]['role_scope'],
                'historical_condition':items[0]['historical_condition'],'raw_pair_ids':[x['id'] for x in items],'actual_steps':steps,
                'observed_input_packet':load(inputp) if inputp.is_file() else None,
                'observed_final_messages':load(finalp) if finalp.is_file() else None,
                'observed_result':result,'terminal_finish_reason':finish,'source_result':source_ref(resultp) if resultp.is_file() else None,
                'source_input_packet':source_ref(inputp) if inputp.is_file() else None,'source_final_messages':source_ref(finalp) if finalp.is_file() else None,
                'complete_autonomous_pipeline_demonstration_proven':False,'semantic_approved':False,'training_admitted':False,'publication_approved':False,
                'future_final_messages_never_added_to_earlier_request':True}
            writeline(rf,rr);runstats['runs']+=1;runstats['has_result']+=result is not None;runstats['last_raw_finish_stop']+=finish=='stop';runstats['last_raw_finish_tools']+=finish=='tool_calls';runstats['has_input_packet']+=inputp.is_file();runstats['has_final_messages']+=finalp.is_file()
    for p,h in all_input_hashes.items():assert sha(Path(p))==h
    paths=[allpath,mechanicalpath,runpath]
    report={'schema_version':'wrd-original-raw-recovery-v4','source_audit_sha256':sha(source),'source_files_unchanged':True,
        'counts_by_scope':{k:dict(v) for k,v in counts.items()},'run_counts':dict(runstats),'continuity_counts':dict(continuities),
        'unique_reasoning_content_sha256_count':len(reasonings),'source_files_hashed':len(all_input_hashes),
        'controlled_files':[{'path':str(p.relative_to(OUT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in paths],
        'semantic_approval_completed':False,'all_rows_training_admitted':False,'raw_original_reasoning_preserved':True,
        'formal_and_technical_never_in_nonformal_mechanical_subset':True,'script_sha256':sha(Path(__file__)),
        'training_started':False,'new_model_calls':0,'elapsed_seconds':round(time.monotonic()-started,3)}
    save(OUT/'RAW_RECOVERY_REPORT.json',report)
    print(json.dumps({k:report[k] for k in ['counts_by_scope','run_counts','continuity_counts','unique_reasoning_content_sha256_count','elapsed_seconds']},ensure_ascii=False))

if __name__=='__main__':main()
