"""Extract real historical action outcomes before treating thought/action as positive."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261025_wrd_reasoning_recovery_v4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def line(f,x):f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
def main():
    inp=OUT/'controlled/sse_reasoning_pairs.evolution.mechanical.jsonl.gz';dest=OUT/'controlled/sse_action_outcome.labels.jsonl.gz'
    if dest.exists():raise ValueError('new output required')
    counts=Counter();cache={};items=[]
    with gzip.open(inp,'rt',encoding='utf-8') as rf,gzip.open(dest,'wt',encoding='utf-8',newline='\n',compresslevel=3) as wf:
        for s in rf:
            r=json.loads(s);ep=r['episode_id'];path=ROOT/'output/20261015_ewi_teacher_DATA/episodes'/ep/'decision_transcript.json'
            if ep not in cache:cache[ep]=load(path)
            proposal=r['observed_parsed_output'];aid=proposal.get('action_id');matches=[(i,x) for i,x in enumerate(cache[ep]) if x.get('proposal',{}).get('action_id')==aid]
            exact=len(matches)==1
            i,eventrow=matches[0] if exact else (None,{})
            eq=eventrow.get('proposal')==proposal;event=eventrow.get('event',{});status=event.get('status','unmatched');obs=event.get('observation',{})
            args_dict=isinstance(proposal.get('arguments'),dict);definite_reject=status=='REJECTED';counts[status]+=1
            if not args_dict:counts['arguments_not_object']+=1
            if not eq:counts['proposal_mismatch_or_unmatched']+=1
            row={'id':r['id'],'episode_id':ep,'request_ordinal':r['request_ordinal'],'original_action_id':aid,'kind':proposal.get('kind'),
                'annotation_origin':'exact_original_action_id_and_proposal_match_to_original_outcome','original_status':status,
                'source_proposal_exact_equal':eq,'arguments_is_object':args_dict,'actual_observation_flag':obs.get('actual'),
                'actual_tool_exit_code':obs.get('exit_code'),'original_error_type':event.get('error_type'),'original_error':event.get('error'),
                'source_transcript_path':str(path),'source_transcript_sha256':sha(path),'event_json_pointer':'/'+str(i)+'/event' if i is not None else None,
                'definite_negative_action':definite_reject or not args_dict or not eq,
                'mechanically_eligible_action_after_real_outcome_gate':exact and eq and args_dict and not definite_reject,
                'semantic_approved':False,'training_admitted':False,'human_gold':False,
                'reasoning_is_not_gold_just_because_response_was_complete':True}
            line(wf,row);items.append(row)
    report={'schema_version':'wrd-sse-original-action-outcome-audit-v4','input_sha256':sha(inp),'source_status_counts':dict(counts),
        'total':len(items),'definite_negative_actions':sum(x['definite_negative_action'] for x in items),
        'outcome_compatible_action_candidates':sum(x['mechanically_eligible_action_after_real_outcome_gate'] for x in items),
        'output':{'path':str(dest.relative_to(OUT)),'sha256':sha(dest),'bytes':dest.stat().st_size},'rows':items,
        'all_semantically_approved':False,'human_gold':False,'training_started':False,'new_model_calls':0,'script_sha256':sha(Path(__file__))}
    (OUT/'SSE_ACTION_OUTCOME_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['source_status_counts','total','definite_negative_actions','outcome_compatible_action_candidates']},ensure_ascii=False))

if __name__=='__main__':main()
