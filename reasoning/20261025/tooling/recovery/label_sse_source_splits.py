"""Attach original source split evidence without rewriting frozen SSE recovery."""
import gzip
import hashlib
import json
from pathlib import Path
from collections import Counter

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261025_wrd_reasoning_recovery_v4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def line(f,x):f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
def main():
    src=ROOT/'output/20261015_ewi_teacher_DATA/data/construction_sources.jsonl'
    lookup={}
    for ordinal,s in enumerate(src.read_text(encoding='utf-8').splitlines(),1):
        if not s.strip():continue
        r=json.loads(s);lookup[r['session_id']]={'split':r.get('split'),'ordinal':ordinal,'source_row_sha256':hashlib.sha256(s.encode()).hexdigest(),'leakage_component_id':r.get('leakage_component_id')}
    inp=OUT/'controlled/sse_reasoning_pairs.all.jsonl.gz';before=sha(inp)
    selected=OUT/'controlled/sse_reasoning_pairs.evolution.mechanical.jsonl.gz';labels=OUT/'controlled/sse_source_split.labels.jsonl.gz'
    if selected.exists() or labels.exists():raise ValueError('new outputs required')
    c=Counter();chars=Counter()
    with gzip.open(inp,'rt',encoding='utf-8') as rf,gzip.open(selected,'wt',encoding='utf-8',newline='\n',compresslevel=3) as sf,gzip.open(labels,'wt',encoding='utf-8',newline='\n',compresslevel=3) as lf:
        for s in rf:
            r=json.loads(s);m=lookup.get(r.get('episode_id'));split=m['split'] if m else 'unmapped'
            eligible=split=='evolution' and r['mechanical_usable'] is True
            ann={'id':r['id'],'episode_id':r.get('episode_id'),'original_teacher_source_split':split,
                'source_split_evidence_file':str(src),'source_split_evidence_file_sha256':sha(src),
                'source_split_evidence_row_1based':m['ordinal'] if m else None,
                'source_split_evidence_row_sha256':m['source_row_sha256'] if m else None,
                'original_leakage_component_id':m['leakage_component_id'] if m else None,
                'source_evolution_and_mechanically_eligible':eligible,
                'historical_evaluation_or_unmapped_not_promoted_to_training':split!='evolution',
                'annotation_origin':'exact_original_source_id_match_not_inferred_semantics','semantic_approved':False,'training_admitted':False}
            line(lf,ann);c[split+':all']+=1
            if eligible:
                line(sf,{**r,'source_split':split,'source_split_evidence':ann});c[split+':mechanically_eligible']+=1;chars[split]+=r['original_reasoning_characters']
    assert sha(inp)==before
    report={'schema_version':'wrd-sse-original-source-split-overlay-v4','counts':dict(c),'eligible_reasoning_characters':dict(chars),
        'frozen_sse_input_unchanged':True,'frozen_sse_input_sha256':before,'source_file_sha256':sha(src),
        'outputs':[{'path':str(p.relative_to(OUT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in [selected,labels]],
        'semantic_approval_completed':False,'training_started':False,'new_model_calls':0,'script_sha256':sha(Path(__file__))}
    (OUT/'SSE_SOURCE_SPLIT_OVERLAY_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
