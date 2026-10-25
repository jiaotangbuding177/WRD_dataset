"""Summarize admitted token exposure and recovered decision coverage, CPU only."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import gzip
import hashlib
import json
from pathlib import Path


def rows(p):
    with gzip.open(p,'rt',encoding='utf-8') as f:
        for line in f:yield json.loads(line)


def main():
    p=argparse.ArgumentParser();p.add_argument('--public',type=Path,required=True);a=p.parse_args()
    report=json.loads((a.public/'FINAL_ADMISSION.json').read_text(encoding='utf-8'))
    if report['status']!='PASS' or not report['release_ready']:raise ValueError('admission incomplete')
    admitted={};buckets={}
    for name in ('common16k','common32k_long_only'):
        c=Counter()
        for r in rows(a.public/'sft'/(name+'.jsonl.gz')):
            if r['id'] in admitted:raise ValueError('duplicate exposure')
            admitted[r['id']]=name;c['examples']+=1;c['input_tokens']+=len(r['input_ids'])
            c['supervised_tokens']+=sum(end-start for start,end in r['supervision_spans'])
        buckets[name]=dict(c)
    if len(admitted)!=report['counts']['final_admitted']:raise ValueError('count mismatch')
    kinds=Counter();tools=Counter();routes=Counter();episodes=set()
    for name in ('actions','labels'):
        for r in rows(a.public/'data'/('candidates.'+name+'.jsonl.gz')):
            if r['id'] not in admitted:continue
            kinds[r['kind']+':'+str(r.get('target_kind',name))]+=1
            tools.update(r.get('tool_call_names',[]));routes[str(r.get('route_id'))]+=1;episodes.add(r.get('episode_id'))
    decisions=Counter();parents=set()
    for r in rows(a.public/'support/audit_screen_write_decisions.jsonl.gz'):
        if r['parent_sample_id'] in admitted:
            parents.add(r['parent_sample_id']);decisions[str(r['observed_action'])]+=1
    total=Counter()
    for c in buckets.values():total.update(c)
    value={'schema_version':'wrd-admitted-sft-statistics-v1','buckets_exclusive':buckets,'cumulative_32k':dict(total),
           'supervised_fraction_of_processed_tokens':total['supervised_tokens']/total['input_tokens'] if total['input_tokens'] else None,
           'by_kind_and_target_kind':dict(kinds),'tool_target_counts':dict(tools),'route_id_counts':dict(routes),
           'observed_distinct_teacher_episodes':len(episodes),'episodes_are_not_independent_source_groups':True,
           'admitted_direct_route_write_parents':len(parents),'decision_subannotations_inside_admitted_parents':dict(decisions),
           'decision_subannotations_are_not_additional_sft_rows':True,'human_gold':0,
           'full_scale_training_readiness_asserted':False,'training_started':False}
    (a.public/'reports/sft_statistics.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
