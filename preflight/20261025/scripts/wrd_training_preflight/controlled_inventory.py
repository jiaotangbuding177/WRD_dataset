"""Publish body-free, uniquely locatable references for every controlled hold."""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re


def main():
    p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);a=p.parse_args()
    target=a.prepared/'public/audit/controlled_inventory.jsonl.gz';target.parent.mkdir(parents=True,exist_ok=True)
    counts=Counter();flags=Counter()
    with gzip.open(target,'wt',encoding='utf-8',newline='\n',compresslevel=3) as out:
        for source in sorted((a.prepared/'local_restricted').glob('held.*.jsonl.gz')):
            kind=source.name.removeprefix('held.').removesuffix('.jsonl.gz')
            with gzip.open(source,'rb') as f:
                for line_no,line in enumerate(f,1):
                    r=json.loads(line);identifiers={}
                    for k in ('id','episode_id','job_id','route_id','support_id','source_id','source_sha256'):
                        v=r.get(k)
                        if isinstance(v,str) and re.fullmatch(r'(?:[a-zA-Z_]+_)?[0-9a-f]{8,64}',v):identifiers[k]=v
                    reasons=r.get('privacy_review',{}).get('risk_flags',[])
                    if not all(isinstance(x,str) and re.fullmatch('[a-z0-9_]+',x) for x in reasons):raise ValueError('unknown risk-flag shape')
                    row={'stream':kind,'controlled_basename':source.name,'controlled_row_1based':line_no,
                         'controlled_record_sha256':hashlib.sha256(line).hexdigest(),'opaque_identifiers':identifiers,
                         'risk_flags':reasons,'publication_approved':False,'body_included':False,
                         'content_retained_in_original_work_source':True}
                    out.write(json.dumps(row,separators=(',',':'))+'\n');counts[kind]+=1;flags.update(reasons)
    report={'schema_version':'wrd-controlled-reference-inventory-v1','counts':dict(counts),'total':sum(counts.values()),
            'risk_flag_counts_nonexclusive':dict(flags),'private_bodies_or_paths_included':False,
            'locator_root':'local_restricted in the retained local preparation directory; not a public URL',
            'basename_and_row_uniquely_identify_each_held_record':True,'training_started':False}
    (a.prepared/'public/reports/controlled_inventory.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
