"""Apply observed original action outcomes to recovered original-reasoning loss.

Rejected outputs remain intact source evidence; all their R/A/D loss is zero.
No teacher self-evaluation is upgraded into semantic gold.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import gzip
from pathlib import Path
from compile_native import readrows,save,digest,js,sha_bytes,int_sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    source=a.root/'raw_reasoning_evolution_compiled';out=a.root/'raw_reasoning_evolution_final';out.mkdir(exist_ok=False)
    label_source=a.root/'controlled/sse_action_outcome.labels.jsonl.gz'
    labels={r['id']:r for r in readrows(label_source)};counts=Counter();by_scope=defaultdict(Counter);statuses=Counter()
    files=['historical_original_reasoning_records.jsonl.gz','raw_target_inventory.jsonl.gz']
    streams={n:gzip.open(out/n,'wt',encoding='utf-8',newline='\n',compresslevel=3) for n in files}
    seen=set()
    try:
        for r in readrows(source/files[0]):
            old_spans=r['supervision_spans'];scope=r['role_scope'];c=by_scope[scope];label=labels.get(r['id'])
            counts['source_pairs_preserved']+=1;c['source_pairs_preserved']+=1
            original_reason=r['original_reasoning_characters'];counts['source_pairs_with_original_reasoning']+=bool(original_reason)
            counts['original_reasoning_characters_preserved']+=original_reason
            counts['input_tokens_preserved']+=r['total_tokens']
            original_positive=r['mechanical_teacher_silver_available'] is True
            if label:
                seen.add(r['id']);status=label.get('original_status');statuses[str(status)]+=1
                r['observed_original_action_status']=status
                r['original_outcome_evidence']={k:label.get(k) for k in
                    ['annotation_origin','original_action_id','arguments_is_object','source_proposal_exact_equal',
                     'source_transcript_path','source_transcript_sha256','event_json_pointer','actual_observation_flag',
                     'actual_tool_exit_code','definite_negative_action']}
                positive=label.get('mechanically_eligible_action_after_real_outcome_gate') is True
                counts['sse_source_action_outcome_labels']+=1
                if not positive:
                    counts['sse_rejected_or_unapplied_targets_masked']+=1;c['sse_rejected_or_unapplied_targets_masked']+=1
                    for target in r['targets']:
                        if target.get('id')==r['id']:
                            target['mechanical_usable']=False
                            target['mechanical_reasons']=sorted(set(target['mechanical_reasons']+['observed_original_action_rejected_or_unapplied']))
                            target['owned_supervision_spans']=[];target['supervised_tokens']=0
                    r['supervision_spans']=[];r['supervised_tokens']=0;r['supervised_tokens_by_component']={}
                    r['supervision_spans_sha256']=sha_bytes(js([]).encode())
                    r['mechanical_teacher_silver_available']=False
                r['correct_original_action_outcome_is_not_current_skill_retain']=True
            else:
                if scope=='historical_ewi_model_decision_teacher':raise ValueError('missing_sse_outcome_label')
                positive=original_positive
                r['observed_original_action_status']=None
                r['generation_scope_audit']='evolution-source teacher construction/revision; final artifact quality remains separate'
            r['request_response_technical_completeness_before_outcome_gate']=original_positive
            r['positive_target_after_original_outcome_gate']=positive and original_positive
            r['original_negative_reasoning_and_output_preserved_as_zero_loss_history_evidence']=True
            r['semantic_approved']=False;r['human_gold']=False;r['training_admitted']=False
            if r['supervised_tokens']:
                counts['positive_candidate_pairs']+=1;c['positive_candidate_pairs']+=1
                counts['positive_candidate_supervised_tokens_before_length']+=r['supervised_tokens']
                counts['positive_candidate_pairs_with_original_reasoning']+=bool(original_reason)
                for cl,n in r['supervised_tokens_by_component'].items():counts['positive_supervised_component_'+cl]+=n;c['positive_supervised_component_'+cl]+=n
                if r['total_tokens']<=16384:counts['positive_complete_le16k']+=1;c['positive_complete_le16k']+=1
                if r['total_tokens']<=32768:
                    counts['positive_complete_le32k']+=1;c['positive_complete_le32k']+=1
                    counts['training_window_supervised_tokens']+=r['supervised_tokens'];c['training_window_supervised_tokens']+=r['supervised_tokens']
                    counts['le32k_positive_pairs_with_original_reasoning']+=bool(original_reason)
                    for cl,n in r['supervised_tokens_by_component'].items():counts['le32k_supervised_component_'+cl]+=n;c['le32k_supervised_component_'+cl]+=n
            assert int_sha(r['input_ids'])==r['input_ids_sha256_u32le']
            assert r['supervised_tokens']==sum(z[1]-z[0] for z in r['supervision_spans'])
            streams[files[0]].write(js(r)+'\n')
            streams[files[1]].write(js({k:v for k,v in r.items() if k not in ['input_ids','assistant_generation_spans']})+'\n')
    finally:
        for f in streams.values():f.close()
    assert len(seen)==45
    report={'schema_version':'wrd-outcome-gated-original-reasoning-final-v4','counts':dict(counts),
            'by_role_scope':{k:dict(v) for k,v in by_scope.items()},'observed_sse_action_statuses':dict(statuses),
            'original_45_sse_targets_preserved':True,'rejected_12_targets_all_components_zero_loss':counts['sse_rejected_or_unapplied_targets_masked']==12,
            'evolution_only_sse_not_historical_evaluation_or_unknown_m5':True,
            'mechanical_outcome_compatibility_is_not_semantic_gold':True,
            'source_action_outcome_labels_sha256':digest(label_source),
            'source_compiled_report_sha256':digest(source/'RAW_COMPILATION_REPORT.json'),
            'script_sha256':digest(Path(__file__)),'training_started':False,'gpu_used':False,
            'outputs':{n:{'sha256':digest(out/n),'bytes':(out/n).stat().st_size} for n in files}}
    save(out/'RAW_COMPILATION_REPORT.json',report)
    print(js({'status':'outcome_gated','counts':dict(counts),'statuses':dict(statuses)}),flush=True)


if __name__=='__main__':main()
