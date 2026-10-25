"""Compile newly located old native sessions under explicit historical conditions.

Only 32 make/screen/review sources are considered. No unproved core-tool schema
is injected. Missing execution provenance is a condition label, not a reason to
erase real events; missing CURRENT tool schemas still prevents action loss.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import gzip
from pathlib import Path
import time
from compile_native import CausalCompiler,readrows,save,digest,js,native_messages,formal_status,owned_native,valid_registry,prefix_record,sha_bytes


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    compiler=CausalCompiler(a.assets);source_sha=digest(a.source);start=time.monotonic()
    counts=Counter();by_stage=defaultdict(Counter);holds=Counter()
    names=['full_stage_records.jsonl.gz','prefix32k_records.jsonl.gz','target_inventory.jsonl.gz','nonselected_source_inventory.jsonl.gz']
    streams={n:gzip.open(a.output/n,'wt',encoding='utf-8',newline='\n',compresslevel=3) for n in names}
    try:
        for ordinal,r in enumerate(readrows(a.source),1):
            counts['source_sessions_in_recovery']+=1
            stage=r.get('kind','unknown');scope=r.get('role_scope','unknown')
            if stage not in ('make','screen','review'):
                counts['not_selected_'+scope]+=1
                streams['nonselected_source_inventory.jsonl.gz'].write(js({'episode_id':r['episode_id'],'kind':stage,
                    'role_scope':scope,'source_ordinal':ordinal,'status':'source_preserved_not_positive_compiled','body_emitted':False})+'\n')
                continue
            counts['selected_historical_stage_sessions']+=1;c=by_stage[stage];c['sessions']+=1
            registry,schema_issues=valid_registry(r.get('tools',[]))
            messages,indices,issues=native_messages(r);marker=formal_status(r)
            owned=owned_native(r,messages,indices,registry,issues,marker)
            for t in owned.values():
                # This layer intentionally represents historical native use,
                # not a claim to current 97a0 execution equivalence.
                t['mechanical_reasons']=[x for x in t['mechanical_reasons'] if x!='historical_runtime_not_verified_native']
                stop=r['messages'][t['source_message_index']].get('stopReason');t['observed_native_stop_reason']=stop
                if stop in ('length','aborted','error'):t['mechanical_reasons'].append('native_response_'+str(stop)+'_not_complete_positive')
                t['mechanical_usable']=not t['mechanical_reasons']
                t['training_tier']='historical_mechanical_silver_requires_runtime_and_semantic_compatibility' if t['mechanical_usable'] else 'held_or_context_only'
                t['historical_execution_condition_not_reverified']=True
                counts['assistant_positions']+=1;c['assistant_positions']+=1
                counts['nonempty_targets']+=t['nonempty'];c['nonempty_targets']+=t['nonempty']
                counts['mechanical_usable_targets']+=t['mechanical_usable'];c['mechanical_usable_targets']+=t['mechanical_usable']
                for reason in t['mechanical_reasons']:holds[reason]+=1
            result=compiler.compile_messages(messages,list(registry.values()),owned,independent=True)
            record={'schema_version':'wrd-historical-native-causal-process-v4','id':r['episode_id'],'episode_id':r['episode_id'],
                    'kind':stage,'role_scope':scope,'scope':'controlled_historical_native',
                    'view':'historical_complete_native_stage_causal_serialization',
                    'source_session_file_sha256':source_sha,'source_session_ordinal_1based':ordinal,
                    'historical_condition':r.get('historical_condition'),'native_verified':False,
                    'current_97a0_runtime_equivalence_claimed':False,
                    'source_events':r.get('source_events'),'source_request':r.get('source_request'),
                    'source_system':r.get('source_system'),'source_tools':r.get('source_tools'),
                    'tools':list(registry.values()),'tool_schema_issues':schema_issues,
                    'unproved_core7_schema_injection':False,'original_tool_placeholders_not_deleted_from_source':True,
                    'marker_audit':marker,'semantic_approved':False,'human_gold':False,'training_admitted':False,
                    'publication_approved':False,'stage_complete_in_this_view':True,'full_autonomous_controller_demonstration':False,
                    'mechanical_teacher_silver_available':bool(result['supervised_tokens']),
                    'serialization':compiler.proof['causal_template_sha256'],**result}
            counts['sessions_compiled']+=1;c['sessions_compiled']+=1;counts['processed_full_stage_tokens']+=record['total_tokens']
            counts['candidate_supervised_tokens_before_length']+=record['supervised_tokens']
            for cl,n in record['supervised_tokens_by_component'].items():counts['supervised_component_'+cl]+=n
            length=record['total_tokens'];record['length_bucket']='complete_le16k' if length<=16384 else 'complete_16k_to32k' if length<=32768 else 'over32k_archive'
            if length<=16384:counts['complete_stage_le16k']+=1;c['complete_stage_le16k']+=1
            if length<=32768:counts['complete_stage_le32k']+=1;c['complete_stage_le32k']+=1
            else:counts['complete_stage_over32k']+=1;c['complete_stage_over32k']+=1
            for t in record['targets']:
                if t['mechanical_usable'] and t['response_end_token_exclusive']<=32768:
                    counts['mechanical_target_causal_end_le32k']+=1;c['mechanical_target_causal_end_le32k']+=1
                streams['target_inventory.jsonl.gz'].write(js({'episode_id':r['episode_id'],'kind':stage,**t})+'\n')
            record['native_target_owner_view']='full_stage' if length<=32768 else 'archive_only_choose_explicit_prefix'
            streams['full_stage_records.jsonl.gz'].write(js(record)+'\n')
            window=record if length<=32768 else prefix_record(record,32768)
            if window and window['supervised_tokens']:
                if length>32768:
                    counts['explicit_prefix32k_windows']+=1;streams['prefix32k_records.jsonl.gz'].write(js(window)+'\n')
                counts['training_windows_with_owned_targets']+=1;c['training_windows_with_owned_targets']+=1
                counts['training_window_supervised_tokens']+=window['supervised_tokens'];c['training_window_supervised_tokens']+=window['supervised_tokens']
            if counts['selected_historical_stage_sessions']%8==0:
                print(js({'historical_sessions_compiled':counts['sessions_compiled'],'elapsed_seconds':round(time.monotonic()-start,2)}),flush=True)
    finally:
        for f in streams.values():f.close()
    assert counts['selected_historical_stage_sessions']==32 and counts['source_sessions_in_recovery']==97
    assert digest(a.source)==source_sha
    report={'schema_version':'wrd-historical-native-compilation-report-v4','counts':dict(counts),
            'by_stage':{k:dict(v) for k,v in by_stage.items()},'mechanical_hold_reasons':dict(holds),
            'source_sha256':source_sha,'source_unchanged':True,'script_sha256':digest(Path(__file__)),
            'causal_compiler_script_sha256':digest(Path(__file__).with_name('compile_native.py')),
            'tokenizer_equivalence_and_calls':compiler.proof,'historical_runtime_condition_kept_separate':True,
            'no_unproved_fixed_97a0_core_schema_added':True,'semantic_gold_created':0,
            'training_started':False,'gpu_used':False,'model_weights_loaded':False,'elapsed_seconds':round(time.monotonic()-start,3),
            'outputs':{n:{'sha256':digest(a.output/n),'bytes':(a.output/n).stat().st_size} for n in names}}
    save(a.output/'HISTORICAL_COMPILATION_REPORT.json',report)
    print(js({'status':'historical_compilation_completed','counts':dict(counts)}),flush=True)


if __name__=='__main__':main()
