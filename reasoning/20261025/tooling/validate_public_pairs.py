"""Read back public arrays and compare every R to public transformed sources."""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
from compile_native import readrows,save,digest,sha_bytes,js,HEADER,THINK_OPEN,THINK_CLOSE
from validate_compiled import verify_record


def main():
    from transformers import AutoTokenizer
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);a=p.parse_args()
    tok=AutoTokenizer.from_pretrained(a.assets/'primary_14b',local_files_only=True,trust_remote_code=False)
    sources={};counts=Counter();failures=[];files={}
    for name in ('sse_core.pairs.jsonl.gz','historical_generation.pairs.jsonl.gz','historical_actor_aux.pairs.jsonl.gz'):
        for r in readrows(a.root/'curated_reasoning/public'/name):sources[r['id']]=r
    for bank in ('public_reasoning_compiled_final','public_actor_aux_compiled'):
        root=a.root/bank;all_ids={};bucket_ids=set()
        for r in readrows(root/'all_records.jsonl.gz'):
            try:
                verify_record(r);all_ids[r['id']]=r;counts[bank+'_all_arrays']+=1
                source=sources[r['id']]
                assert r['publication_approved'] is True
                assert r['source_public_record_sha256']==sha_bytes(js(source).encode())
                assert r['privacy_transform']['not_the_original_raw_bytes'] is True
                target=source['original_response']['choices'][0]['message'];reason=target.get('reasoning_content') or ''
                if reason:
                    decoded=tok.decode(r['input_ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
                    assert sha_bytes(decoded.encode())==r['rendered_sha256']
                    t=next(t for t in r['targets'] if t.get('id')==r['id']);lo,hi=t['rendered_assistant_span']
                    assert decoded[lo:hi].startswith(HEADER+THINK_OPEN+reason+THINK_CLOSE+(target.get('content') or ''))
                    counts[bank+'_public_R_source_exactly_decoded']+=1
            except Exception as exc:failures.append({'bank':bank,'id':r.get('id'),'failure':type(exc).__name__})
        for name in ('common16k.jsonl.gz','common32k_long_only.jsonl.gz','over32k.jsonl.gz'):
            for r in readrows(root/name):
                try:
                    verify_record(r);assert r['id'] not in bucket_ids;bucket_ids.add(r['id'])
                    assert 'duplicate_of' not in r and r['mechanical_teacher_silver_available'] is True
                    assert js(r)==js(all_ids[r['id']])
                    if name=='common16k.jsonl.gz':assert r['total_tokens']<=16384
                    elif name=='common32k_long_only.jsonl.gz':assert 16384<r['total_tokens']<=32768
                    else:assert r['total_tokens']>32768
                    counts[bank+'_'+name+'_verified']+=1
                except Exception as exc:failures.append({'bank':bank,'id':r.get('id'),'file':name,'failure':type(exc).__name__})
        files[bank]={p.name:{'sha256':digest(p),'bytes':p.stat().st_size} for p in root.iterdir() if p.is_file()}
    report={'schema_version':'wrd-public-reasoning-independent-validation-v4','status':'PASS' if not failures else 'FAIL',
            'counts':dict(counts),'failures':failures,'all_array_and_span_hashes_checked':True,
            'all_public_recorded_reasoning_fields_decoded_against_transformed_sources':True,
            'identity_to_unsanitized_raw_bytes_not_claimed':True,'training_buckets_mutually_exclusive':True,
            'core_and_actor_auxiliary_banks_kept_separate':True,'source_and_output_files':files,
            'training_started':False,'script_sha256':digest(Path(__file__))}
    save(a.root/'PUBLIC_REASONING_DATA_VALIDATION.json',report)
    print(js({'status':report['status'],'counts':dict(counts),'failures':failures}),flush=True)
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
