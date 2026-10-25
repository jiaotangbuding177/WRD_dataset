"""Compile curated public request/response projections into actual R/A/D arrays.

This checks exact equality to the PUBLIC transformed fields, never claims
identity with original unsanitized bytes. No weights, GPU or agent execution.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import gzip
from pathlib import Path
import time
from compile_native import CausalCompiler,readrows,save,digest,js,sha_bytes,HEADER,THINK_OPEN,THINK_CLOSE,int_sha
from compile_raw import current_protocol,valid_registry


def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-input',type=Path,action='append',required=True)
    p.add_argument('--assets',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--bank-role',choices=['core','actor_auxiliary'],required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);compiler=CausalCompiler(a.assets);start=time.monotonic()
    counts=Counter();by_input=defaultdict(Counter);failures=Counter();seen=set();fingerprints={};sources=[]
    names=['all_records.jsonl.gz','common16k.jsonl.gz','common32k_long_only.jsonl.gz','over32k.jsonl.gz','compile_holds.jsonl.gz']
    streams={n:gzip.open(a.output/n,'wt',encoding='utf-8',newline='\n',compresslevel=3) for n in names}
    try:
        for source in a.raw_input:
            source_sha=digest(source);sources.append({'name':source.name,'sha256':source_sha,'bytes':source.stat().st_size})
            for ordinal,r in enumerate(readrows(source),1):
                counts['source_pairs']+=1;c=by_input[source.name];c['source_pairs']+=1
                try:
                    if r['id'] in seen:raise ValueError('duplicate_source_id')
                    seen.add(r['id'])
                    if r.get('publication_approved') is not True:raise ValueError('source_not_publication_approved')
                    transform=r.get('privacy_transform') or {}
                    if transform.get('context_and_reasoning_transformed_consistently') is not True:
                        raise ValueError('missing_consistent_public_transform_proof')
                    if transform.get('not_the_original_raw_bytes') is not True:
                        raise ValueError('public_source_transform_status_not_explicit')
                    request=r['original_request'];response=r['original_response'];target=dict(response['choices'][0]['message'])
                    messages=[dict(x) for x in request['messages']];target['role']='assistant'
                    reasoning=target.get('reasoning_content') or '';content=target.get('content') or ''
                    counts['public_source_pairs_with_recorded_reasoning']+=bool(reasoning);c['public_source_pairs_with_recorded_reasoning']+=bool(reasoning)
                    counts['public_transformed_reasoning_characters']+=len(reasoning);c['public_transformed_reasoning_characters']+=len(reasoning)
                    registry,tool_issues=valid_registry(request.get('tools',[]))
                    reasons,flags=current_protocol(messages,target,registry)
                    if r.get('mechanical_usable') is not True:reasons+=r.get('mechanical_exclusion_reasons') or ['source_mechanical_hold']
                    finish=r.get('original_response_finish_reason')
                    if finish not in ('stop','tool_calls','function_call'):reasons.append('response_not_complete_for_positive')
                    original_outcome=r.get('original_action_outcome') or {}
                    if isinstance(original_outcome,dict):
                        if original_outcome and original_outcome.get('mechanically_eligible_action_after_real_outcome_gate') is not True:
                            reasons.append('original_action_outcome_not_positive')
                    elif isinstance(original_outcome,str):
                        if original_outcome not in ('APPLIED','OBSERVED','FINISHED'):
                            reasons.append('original_action_outcome_not_positive')
                    else:reasons.append('unsupported_original_action_outcome_shape')
                    if r.get('source_role_audit_pending') is True:reasons.append('source_role_still_pending')
                    reasons=sorted(set(reasons));owned_index=len(messages)
                    spec={'id':r['id'],'nonempty':bool(reasoning or content or target.get('tool_calls')),
                          'mechanical_usable':not reasons,'mechanical_reasons':reasons,'context_flags':flags,
                          'semantic_approved':False,'human_gold':False,
                          'reasoning_origin':'recorded_teacher_reasoning_consistently_privacy_transformed' if reasoning else 'none',
                          'public_transformed_reasoning_sha256':sha_bytes(reasoning.encode()) if reasoning else None,
                          'source_response_public_message_sha256':sha_bytes(js(target).encode()),
                          'current_native_runtime_equivalence_claimed':False}
                    result=compiler.compile_messages(messages+[target],list(registry.values()),{owned_index:spec},
                                                     independent=counts['source_pairs']<=64 or counts['source_pairs']%97==0)
                    current=next(t for t in result['targets'] if t.get('id')==r['id'])
                    # Every public reasoning response is independently decoded
                    # and checked against this transformed source's exact text.
                    if reasoning:
                        decoded=compiler.tokenizers['primary_14b'].decode(result['input_ids'],skip_special_tokens=False,
                                                                         clean_up_tokenization_spaces=False)
                        if sha_bytes(decoded.encode())!=result['rendered_sha256']:raise ValueError('decoded_public_render_sha_mismatch')
                        lo,hi=current['rendered_assistant_span'];chunk=decoded[lo:hi]
                        if not chunk.startswith(HEADER+THINK_OPEN+reasoning+THINK_CLOSE+content):
                            raise ValueError('public_reasoning_or_content_not_exactly_preserved')
                        if not reasons and not any(s[2] in ('R','R_BOUNDARY_MIXED') for s in current['owned_supervision_spans']):
                            raise ValueError('recorded_public_reasoning_not_supervised')
                        counts['public_reasoning_decode_source_exact_checks']+=1;c['public_reasoning_decode_source_exact_checks']+=1
                    record={'schema_version':'wrd-public-recorded-reasoning-compiled-v4','id':r['id'],
                            'bank_role':a.bank_role,'source_pair_file':source.name,'source_pair_ordinal_1based':ordinal,
                            'source_public_pair_file_sha256':source_sha,'source_public_record_sha256':sha_bytes(js(r).encode()),
                            'role_scope':r.get('role_scope'),'historical_condition':r.get('historical_condition'),
                            'candidate_tier':r.get('candidate_tier'),'privacy_transform':transform,
                            'source_scope_review_sha256':r.get('source_scope_review_sha256'),
                            'original_action_outcome':original_outcome,
                            'recorded_reasoning_is_privacy_transformed_not_unmodified_original_bytes':True,
                            'public_transformed_reasoning_characters':len(reasoning),
                            'source_tools_registry_issues':tool_issues,'publication_approved':True,
                            'semantic_approved':False,'human_gold':False,'training_admitted':False,
                            'mechanical_teacher_silver_available':not reasons,
                            'current_native_runtime_equivalence_claimed':False,
                            'source_thoughts_not_replaced_by_summary':True,
                            'optional_actor_auxiliary_recommended_max_loss_fraction':0.10 if a.bank_role=='actor_auxiliary' else None,
                            'serialization':compiler.proof['causal_template_sha256'],**result}
                    fingerprint=record['input_ids_sha256_u32le']+':'+record['supervision_spans_sha256']
                    if fingerprint in fingerprints:
                        counts['duplicate_exact_render_and_mask']+=1
                        record['duplicate_of']=fingerprints[fingerprint]
                    else:fingerprints[fingerprint]=r['id']
                    record['length_bucket']='complete_le16k' if result['total_tokens']<=16384 else 'complete_16k_to32k' if result['total_tokens']<=32768 else 'over32k_not_truncated'
                    counts['pairs_compiled']+=1;c['pairs_compiled']+=1
                    counts['processed_tokens']+=record['total_tokens'];counts['supervised_tokens_before_length']+=record['supervised_tokens']
                    for cl,n in record['supervised_tokens_by_component'].items():counts['supervised_component_'+cl]+=n;c['supervised_component_'+cl]+=n
                    for reason in reasons:failures[reason]+=1
                    streams['all_records.jsonl.gz'].write(js(record)+'\n')
                    if reasons:
                        streams['compile_holds.jsonl.gz'].write(js({'id':r['id'],'reasons':reasons,'source':source.name})+'\n')
                    elif 'duplicate_of' not in record:
                        if record['total_tokens']<=16384:bucket='common16k.jsonl.gz'
                        elif record['total_tokens']<=32768:bucket='common32k_long_only.jsonl.gz'
                        else:bucket='over32k.jsonl.gz'
                        streams[bucket].write(js(record)+'\n');counts[bucket+'_records']+=1;c[bucket+'_records']+=1
                        if record['total_tokens']<=32768:
                            counts['positive_complete_le32k']+=1;c['positive_complete_le32k']+=1
                            counts['le32k_supervised_tokens']+=record['supervised_tokens'];c['le32k_supervised_tokens']+=record['supervised_tokens']
                            counts['le32k_records_with_reasoning']+=bool(reasoning);c['le32k_records_with_reasoning']+=bool(reasoning)
                            for cl,n in record['supervised_tokens_by_component'].items():counts['le32k_supervised_component_'+cl]+=n;c['le32k_supervised_component_'+cl]+=n
                except Exception as exc:
                    counts['pair_compile_failures']+=1;c['pair_compile_failures']+=1
                    code=type(exc).__name__+':'+str(exc) if isinstance(exc,ValueError) else type(exc).__name__
                    failures['compile_'+code]+=1
                    streams['compile_holds.jsonl.gz'].write(js({'id':r.get('id'),'source':source.name,'failure_code':code})+'\n')
                if counts['source_pairs']%32==0:
                    print(js({'public_bank':a.bank_role,'seen':counts['source_pairs'],'compiled':counts['pairs_compiled'],
                              'recorded_reasoning_pairs':counts['public_source_pairs_with_recorded_reasoning'],
                              'elapsed_seconds':round(time.monotonic()-start,2)}),flush=True)
    finally:
        for f in streams.values():f.close()
    for src,proof in zip(a.raw_input,sources):assert digest(src)==proof['sha256']
    report={'schema_version':'wrd-public-reasoning-array-compilation-v4','bank_role':a.bank_role,'counts':dict(counts),
            'by_input':{k:dict(v) for k,v in by_input.items()},'mechanical_holds_and_compile_failures':dict(failures),
            'source_public_pairs':sources,'source_files_unchanged':True,
            'every_public_recorded_reasoning_field_decoded_and_exactly_matched':counts['public_reasoning_decode_source_exact_checks']==counts['public_source_pairs_with_recorded_reasoning'],
            'identity_is_to_public_transformed_text_not_original_raw_bytes':True,
            'tokenizer_equivalence_and_calls':compiler.proof,'script_sha256':digest(Path(__file__)),
            'causal_compiler_script_sha256':digest(Path(__file__).with_name('compile_native.py')),
            'elapsed_seconds':round(time.monotonic()-start,3),'semantic_gold_created':0,
            'training_started':False,'model_weights_loaded':False,'gpu_used':False,
            'outputs':{n:{'sha256':digest(a.output/n),'bytes':(a.output/n).stat().st_size} for n in names}}
    save(a.output/'PUBLIC_REASONING_COMPILATION_REPORT.json',report)
    save(a.output/'CAUSAL_TEMPLATE.json',{'variant':compiler.template,**compiler.proof})
    save(a.output/'TRAINING_ENTRYPOINT.json',{'schema_version':'wrd-public-reasoning-entry-v4','bank_role':a.bank_role,
        'status':'CURATED_PUBLIC_TEACHER_SILVER_WITH_ACTUAL_ARRAYS_NOT_GOLD_OR_PROVEN_MODEL_EFFECT',
        'common16k':'common16k.jsonl.gz','common32k_long_only':'common32k_long_only.jsonl.gz',
        'cumulative_32k_records':counts['positive_complete_le32k'],'mutually_exclusive_buckets':True,
        'current_response_owned_targets_only':True,'label_definition':'input_ids within supervision_spans, otherwise -100; explicit component weights',
        'required_future_inference_template_sha256':compiler.proof['causal_template_sha256'],
        'causal_variant_currently_integrated_with_live_api':False,
        'teacher_historical_runtime_not_current_native_equivalence':True,
        'privacy_transformed_original_reasoning_not_verbatim_raw':True,'training_execution_authorized':False,
        'optional_actor_auxiliary_recommended_max_loss_fraction':0.10 if a.bank_role=='actor_auxiliary' else None})
    print(js({'status':'completed','bank_role':a.bank_role,'counts':dict(counts)}),flush=True)


if __name__=='__main__':main()
