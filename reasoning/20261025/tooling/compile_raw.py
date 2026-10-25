"""Compile recovered original-response/SSE reasoning as separate historical views.

No conversion to native execution provenance. No weights, GPU or new model calls.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import gzip
import json
from pathlib import Path
import time
from compile_native import CausalCompiler,readrows,save,digest,js,sha_bytes,valid_registry


def current_protocol(messages,target,registry):
    from jsonschema import Draft202012Validator
    reasons=[];flags=[];pending=set();seen=set()
    for m in messages:
        if m.get('role')=='assistant':
            if pending:reasons.append('historical_pending_tool_results')
            for call in m.get('tool_calls') or []:
                cid=call.get('id');name=(call.get('function') or {}).get('name')
                if not cid or cid in seen:reasons.append('historical_call_id_missing_or_duplicate')
                if name not in registry:flags.append('historical_tool_schema_gap')
                if cid:seen.add(cid);pending.add(cid)
        elif m.get('role')=='tool':
            cid=m.get('tool_call_id')
            if cid not in pending:reasons.append('historical_orphan_tool_result')
            else:pending.remove(cid)
    if pending:reasons.append('historical_pending_tool_results')
    for call in target.get('tool_calls') or []:
        cid=call.get('id');fn=call.get('function') or {};name=fn.get('name')
        if not cid or cid in seen:reasons.append('current_call_id_missing_or_duplicate')
        if name not in registry:reasons.append('current_tool_schema_missing');continue
        try:
            a=fn.get('arguments');a=json.loads(a) if isinstance(a,str) else a
            if next(Draft202012Validator(registry[name]['function']['parameters']).iter_errors(a),None) is not None:
                reasons.append('current_tool_arguments_schema_invalid')
        except Exception:reasons.append('current_tool_arguments_or_schema_unparseable')
    if not any(m.get('role')=='system' and m.get('content') for m in messages):reasons.append('original_system_not_recovered')
    if not(target.get('content') or target.get('tool_calls') or target.get('reasoning_content')):reasons.append('empty_current_target')
    return sorted(set(reasons)),sorted(set(flags))


def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-source',type=Path,required=True);p.add_argument('--sse-source',type=Path,required=True)
    p.add_argument('--assets',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--include-actor-aux',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    compiler=CausalCompiler(a.assets);start=time.monotonic();counts=Counter();by_scope=defaultdict(Counter);failures=Counter();source_hashes={}
    records=gzip.open(a.output/'historical_original_reasoning_records.jsonl.gz','wt',encoding='utf-8',newline='\n',compresslevel=3)
    inventory=gzip.open(a.output/'raw_target_inventory.jsonl.gz','wt',encoding='utf-8',newline='\n',compresslevel=3)
    try:
        for source in (a.sse_source,a.raw_source):
            source_hashes[source.name]=digest(source)
            for ordinal,r in enumerate(readrows(source),1):
                scope=r.get('role_scope','unknown')
                if source==a.raw_source and not a.include_actor_aux and scope!='historical_skill_generation_candidate':continue
                if scope in ('formal_evaluation_exclude','technical_fixture_exclude'):counts['formal_or_fixture_excluded']+=1;continue
                c=by_scope[scope];counts['selected_source_pairs']+=1;c['selected_source_pairs']+=1
                try:
                    request=r['original_request'];response=r['original_response'];target=dict(response['choices'][0]['message'])
                    messages=[dict(x) for x in request['messages']]
                    target['role']='assistant'
                    original_reason=target.get('reasoning_content') or ''
                    counts['pairs_with_original_reasoning']+=bool(original_reason);c['pairs_with_original_reasoning']+=bool(original_reason)
                    counts['original_reasoning_characters']+=len(original_reason);c['original_reasoning_characters']+=len(original_reason)
                    registry,tool_issues=valid_registry(request.get('tools',[]))
                    reasons,flags=current_protocol(messages,target,registry)
                    if r.get('mechanical_usable') is not True:reasons+=r.get('mechanical_exclusion_reasons') or ['source_mechanical_hold']
                    if r.get('source_content_matches_stored_response') is False:reasons.append('sse_content_not_equal_saved_response')
                    reasons=sorted(set(reasons));owned_index=len(messages)
                    spec={'id':r['id'],'nonempty':True,'mechanical_usable':not reasons,'mechanical_reasons':reasons,
                          'context_flags':flags,'human_gold':False,'semantic_approved':False,
                          'source_message_sha256':sha_bytes(js(target).encode()),
                          'reasoning_origin':'original_saved_sse_reconstructed_in_order' if source==a.sse_source else 'original_response_field',
                          'transition_origin':'observed_model_decision_not_autonomous_native_controller',
                          'historical_runtime_not_current_native':True}
                    result=compiler.compile_messages(messages+[target],list(registry.values()),{owned_index:spec},
                                                     independent=counts['selected_source_pairs']<=64 or counts['selected_source_pairs']%97==0)
                    record={'schema_version':'wrd-historical-original-reasoning-compiled-v4','id':r['id'],
                            'view':'original_request_current_response_causal_template',
                            'source_pair_file':source.name,'source_pair_ordinal_1based':ordinal,
                            'source_pair_file_sha256':source_hashes[source.name],
                            'source_request':r.get('source_request'),'source_response':r.get('source_response'),
                            'source_sse':r.get('source_sse'),'source_stored_response':r.get('source_stored_response'),
                            'role_scope':scope,'historical_condition':r.get('historical_condition'),
                            'source_tools_registry_issues':tool_issues,
                            'original_reasoning_characters':len(original_reason),'original_reasoning_replaced_by_summary':False,
                            'native_runtime_equivalence_claimed':False,'semantic_approved':False,'human_gold':False,
                            'training_admitted':False,'publication_approved':False,
                            'mechanical_teacher_silver_available':not reasons,
                            'source_role_audit_pending':r.get('source_role_audit_pending',True),
                            'serialization':compiler.proof['causal_template_sha256'],**result}
                    record['length_bucket']='complete_le16k' if result['total_tokens']<=16384 else 'complete_16k_to32k' if result['total_tokens']<=32768 else 'over32k_not_truncated'
                    counts['pairs_compiled']+=1;c['pairs_compiled']+=1
                    counts['mechanically_usable_pairs']+=not reasons;c['mechanically_usable_pairs']+=not reasons
                    counts['processed_tokens']+=result['total_tokens'];counts['supervised_tokens_before_length']+=result['supervised_tokens']
                    for component,n in result['supervised_tokens_by_component'].items():counts['supervised_component_'+component]+=n;c['supervised_component_'+component]+=n
                    if not reasons:
                        if result['total_tokens']<=16384:counts['mechanical_complete_le16k']+=1;c['mechanical_complete_le16k']+=1
                        if result['total_tokens']<=32768:
                            counts['mechanical_complete_le32k']+=1;c['mechanical_complete_le32k']+=1
                            counts['training_window_supervised_tokens']+=result['supervised_tokens']
                            for component,n in result['supervised_tokens_by_component'].items():
                                counts['le32k_supervised_component_'+component]+=n;c['le32k_supervised_component_'+component]+=n
                    for reason in reasons:failures[reason]+=1
                    records.write(js(record)+'\n')
                    inventory.write(js({k:v for k,v in record.items() if k not in ('input_ids','assistant_generation_spans')})+'\n')
                except Exception as exc:
                    code=type(exc).__name__+':'+str(exc) if isinstance(exc,ValueError) else type(exc).__name__
                    failures['compile_'+code]+=1;counts['pairs_compile_failed']+=1;c['pairs_compile_failed']+=1
                    inventory.write(js({'id':r.get('id'),'role_scope':scope,'failure_code':code})+'\n')
                if counts['selected_source_pairs']%32==0:
                    print(js({'raw_pairs_seen':counts['selected_source_pairs'],'compiled':counts['pairs_compiled'],
                              'reasoning_characters':counts['original_reasoning_characters'],'elapsed_seconds':round(time.monotonic()-start,2)}),flush=True)
    finally:records.close();inventory.close()
    for source in (a.raw_source,a.sse_source):assert digest(source)==source_hashes[source.name]
    report={'schema_version':'wrd-historical-original-reasoning-compilation-v4','counts':dict(counts),
            'by_role_scope':{k:dict(v) for k,v in by_scope.items()},'failure_reasons':dict(failures),
            'source_file_sha256':source_hashes,'source_files_unchanged':True,
            'tokenizer_equivalence_and_calls':compiler.proof,'causal_compiler_script_sha256':digest(Path(__file__).with_name('compile_native.py')),
            'script_sha256':digest(Path(__file__)),'elapsed_seconds':round(time.monotonic()-start,3),
            'original_reasoning_actually_tokenized_and_supervised':counts.get('supervised_component_R',0)>0,
            'ordinary_visible_explanations_not_claimed_original_reasoning':True,
            'historical_conditions_preserved_not_falsely_native':True,
            'new_semantic_gold':0,'training_started':False,'model_weights_loaded':False,'gpu_used':False,
            'outputs':{n:{'sha256':digest(a.output/n),'bytes':(a.output/n).stat().st_size} for n in
                ('historical_original_reasoning_records.jsonl.gz','raw_target_inventory.jsonl.gz')}}
    save(a.output/'RAW_COMPILATION_REPORT.json',report);save(a.output/'CAUSAL_TEMPLATE.json',{'variant':compiler.template,**compiler.proof})
    print(js({'status':'completed','counts':dict(counts),'elapsed_seconds':report['elapsed_seconds']}),flush=True)


if __name__=='__main__':main()
