"""Recheck original stop reasons and exact token/mask bytes without retokenizing.

Original compiled views remain immutable. New final views exclude truncated
responses as positive targets while preserving them as source evidence/history.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import gzip
from pathlib import Path
import time
from compile_native import readrows,save,digest,int_sha,sha_bytes,js,prefix_record


def rebuild(record, stop_lookup):
    spans=[]
    for t in record['targets']:
        stop=stop_lookup.get((record['episode_id'],t['source_message_index']))
        t['observed_native_stop_reason']=stop
        if stop in ('length','aborted','error') and t['mechanical_usable']:
            t['mechanical_usable']=False
            t['mechanical_reasons']=sorted(set(t['mechanical_reasons']+['native_response_'+str(stop)+'_not_complete_positive']))
            t['training_tier']='held_or_context_only'
            t['owned_supervision_spans']=[];t['supervised_tokens']=0
        spans.extend(t['owned_supervision_spans'])
    spans.sort(key=lambda z:z[0]);components=Counter()
    last=0
    for a,b,c,w in spans:
        assert 0<=a<b<=record['total_tokens'] and a>=last
        last=b;components[c]+=b-a
    record['supervision_spans']=spans
    record['supervised_tokens']=sum(z[1]-z[0] for z in spans)
    record['supervised_tokens_by_component']=dict(components)
    record['supervision_spans_sha256']=sha_bytes(js(spans).encode())
    record['mechanical_teacher_silver_available']=bool(spans)
    record['truncated_original_responses_preserved_but_not_positive']=True
    assert int_sha(record['input_ids'])==record['input_ids_sha256_u32le']
    return record


def one(root,scope,source):
    start=time.monotonic();src=root/('native_compiled_'+scope);out=root/('native_compiled_'+scope+'_final')
    out.mkdir(exist_ok=False);lookup={}
    for r in readrows(source):
        for i,m in enumerate(r['messages']):
            if m.get('role')=='assistant':lookup[(r['episode_id'],i)]=m.get('stopReason')
    counts=Counter();stages=defaultdict(Counter);reasons=Counter();classes=Counter()
    files=['full_stage_records.jsonl.gz','prefix32k_records.jsonl.gz','target_inventory.jsonl.gz']
    streams={n:gzip.open(out/n,'wt',encoding='utf-8',newline='\n',compresslevel=3) for n in files}
    try:
        for original in readrows(src/'full_stage_records.jsonl.gz'):
            r=rebuild(original,lookup);c=stages[r['kind']]
            counts['sessions_seen']+=1;counts['sessions_compiled']+=1;c['sessions_seen']+=1;c['sessions_compiled']+=1
            counts['assistant_positions']+=len(r['targets']);c['assistant_positions']+=len(r['targets'])
            n=r['total_tokens'];counts['processed_full_stage_tokens']+=n;c['processed_full_stage_tokens']+=n
            counts['candidate_supervised_tokens_before_length']+=r['supervised_tokens']
            for cl,v in r['supervised_tokens_by_component'].items():counts['supervised_component_'+cl]+=v
            if n<=16384:counts['complete_stage_le16k']+=1;c['complete_stage_le16k']+=1
            if n<=32768:counts['complete_stage_le32k']+=1;c['complete_stage_le32k']+=1
            else:counts['complete_stage_over32k']+=1;c['complete_stage_over32k']+=1
            for t in r['targets']:
                counts['nonempty_targets']+=t['nonempty'];c['nonempty_targets']+=t['nonempty']
                if t['observed_native_stop_reason'] in ('length','aborted','error') and t['nonempty']:
                    counts['nonempty_incomplete_stop_targets']+=1;c['nonempty_incomplete_stop_targets']+=1
                for reason in t['mechanical_reasons']:reasons[reason]+=1
                if t['mechanical_usable']:
                    counts['mechanically_usable_targets_before_length']+=1;c['mechanically_usable_targets_before_length']+=1
                    if t['response_end_token_exclusive']<=16384:counts['mechanical_target_causal_end_le16k']+=1;c['mechanical_target_causal_end_le16k']+=1
                    if t['response_end_token_exclusive']<=32768:counts['mechanical_target_causal_end_le32k']+=1;c['mechanical_target_causal_end_le32k']+=1
                streams['target_inventory.jsonl.gz'].write(js({'episode_id':r['episode_id'],'kind':r['kind'],'scope':scope,
                    'full_stage_tokens':n,**t})+'\n')
            streams['full_stage_records.jsonl.gz'].write(js(r)+'\n')
            training_view=r if n<=32768 else prefix_record(r,32768)
            if training_view:
                if n>32768:
                    counts['explicit_prefix32k_windows']+=1;streams['prefix32k_records.jsonl.gz'].write(js(training_view)+'\n')
                if training_view['supervised_tokens']:
                    counts['training_windows_with_owned_targets']+=1
                    counts['training_window_supervised_tokens']+=training_view['supervised_tokens']
                    c['training_windows_with_owned_targets']+=1;c['training_window_supervised_tokens']+=training_view['supervised_tokens']
                    for cl,v in training_view['supervised_tokens_by_component'].items():counts['training_window_component_'+cl]+=v;c['training_window_component_'+cl]+=v
            if counts['sessions_seen']%128==0:
                print(js({'finalize_scope':scope,'sessions':counts['sessions_seen'],'elapsed_seconds':round(time.monotonic()-start,2)}),flush=True)
    finally:
        for f in streams.values():f.close()
    report={'schema_version':'wrd-final-native-causal-data-v4','scope':scope,'output_directory':out.as_posix(),
            'counts':dict(counts),'by_stage':{k:dict(v) for k,v in stages.items()},'mechanical_hold_reasons':dict(reasons),
            'source_native_sessions_sha256':digest(source),'original_compilation_report_sha256':digest(src/'REPORT.json'),
            'all_input_id_hashes_recomputed_and_matched':True,'all_supervision_spans_rebuilt_from_target_ownership':True,
            'source_truncated_responses_masked_not_deleted':True,'script_sha256':digest(Path(__file__)),
            'new_semantic_gold':0,'training_started':False,'gpu_used':False,'model_weights_loaded':False,
            'elapsed_seconds':round(time.monotonic()-start,3),
            'outputs':{n:{'sha256':digest(out/n),'bytes':(out/n).stat().st_size} for n in files}}
    save(out/'REPORT.json',report);return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--controlled-source',type=Path,required=True)
    p.add_argument('--public-source',type=Path,required=True);a=p.parse_args()
    reports={s:one(a.root,s,src) for s,src in [('controlled',a.controlled_source),('public',a.public_source)]}
    save(a.root/'FINAL_NATIVE_COMPILATION_REPORT.json',{'schema_version':'wrd-final-native-compilation-v4','reports':reports,
        'status':'MECHANICAL_SILVER_WITH_ACTUAL_ARRAYS_NOT_SEMANTIC_GOLD','training_started':False,
        'initial_report_preserved':'NATIVE_COMPILATION_REPORT.json','script_sha256':digest(Path(__file__))})
    print(js({'status':'finalized','counts':{k:v['counts'] for k,v in reports.items()}}),flush=True)


if __name__=='__main__':main()
