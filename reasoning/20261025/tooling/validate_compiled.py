"""Independent read-back checks for actual arrays, masks, source CoT and prefixes."""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
import time
from compile_native import readrows,digest,save,int_sha,sha_bytes,js,HEADER,THINK_OPEN,THINK_CLOSE


def verify_record(r):
    ids=r['input_ids'];spans=r['supervision_spans']
    assert len(ids)==r['total_tokens']
    assert int_sha(ids)==r['input_ids_sha256_u32le']
    assert sha_bytes(js(spans).encode())==r['supervision_spans_sha256']
    assert sum(x[1]-x[0] for x in spans)==r['supervised_tokens']
    owned=[];last=0;components=Counter()
    for a,b,component,weight in spans:
        assert 0<=a<b<=len(ids) and a>=last and weight>=0
        last=b;components[component]+=b-a
    assert dict(components)==r['supervised_tokens_by_component']
    for t in r['targets']:
        if t.get('mechanical_usable') is not True:assert t['owned_supervision_spans']==[]
        if t.get('observed_native_stop_reason') in ('length','aborted','error'):
            assert t.get('mechanical_usable') is not True and t['owned_supervision_spans']==[]
        owned.extend(t['owned_supervision_spans'])
    assert sorted(owned,key=lambda x:x[0])==spans
    assert r['human_gold'] is False and r['semantic_approved'] is False
    return components


def main():
    from transformers import AutoTokenizer
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--assets',type=Path,required=True)
    a=p.parse_args();start=time.monotonic();tok=AutoTokenizer.from_pretrained(a.assets/'primary_14b',local_files_only=True,trust_remote_code=False)
    counts=Counter();failures=[];source_reason={}
    for source in [a.root/'controlled/sse_reasoning_pairs.evolution.mechanical.jsonl.gz',a.root/'controlled/raw_pairs.all.jsonl.gz']:
        for r in readrows(source):
            if source.name.startswith('raw_pairs') and r.get('role_scope')!='historical_skill_generation_candidate':continue
            target=r['original_response']['choices'][0]['message']
            source_reason[r['id']]={'reasoning':target.get('reasoning_content') or '', 'content':target.get('content') or ''}
    for scope in ('controlled','public'):
        root=a.root/('native_compiled_'+scope+'_final')
        prefixes=iter(readrows(root/'prefix32k_records.jsonl.gz'));current=next(prefixes,None)
        for ordinal,r in enumerate(readrows(root/'full_stage_records.jsonl.gz'),1):
            try:
                verify_record(r);counts[scope+'_full_records']+=1
                if ordinal<=8 or ordinal%233==0:
                    decoded=tok.decode(r['input_ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
                    assert sha_bytes(decoded.encode())==r['rendered_sha256']
                    counts[scope+'_decoded_full_render_sha_samples']+=1
                if current and current['episode_id']==r['episode_id']:
                    verify_record(current)
                    n=current['total_tokens'];assert n<=32768 and n<r['total_tokens']
                    assert current['input_ids']==r['input_ids'][:n]
                    assert current['supervision_spans']==[x for x in r['supervision_spans'] if x[1]<=n]
                    counts[scope+'_prefix_records_verified']+=1
                    current=next(prefixes,None)
            except Exception as exc:
                failures.append({'scope':scope,'id':r['id'],'failure':type(exc).__name__})
        assert current is None
    seen={}
    for r in readrows(a.root/'raw_reasoning_evolution_final/historical_original_reasoning_records.jsonl.gz'):
        try:
            verify_record(r);counts['historical_raw_records']+=1
            fingerprint=r['input_ids_sha256_u32le']+':'+r['supervision_spans_sha256']
            if fingerprint in seen:counts['raw_duplicate_exact_render_and_mask']+=1
            else:seen[fingerprint]=r['id']
            original=source_reason[r['id']]
            if original['reasoning']:
                decoded=tok.decode(r['input_ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
                assert sha_bytes(decoded.encode())==r['rendered_sha256']
                target=next(t for t in r['targets'] if t.get('id')==r['id'])
                lo,hi=target['rendered_assistant_span'];chunk=decoded[lo:hi]
                assert chunk.startswith(HEADER+THINK_OPEN+original['reasoning']+THINK_CLOSE+original['content'])
                if target.get('mechanical_usable') is True:
                    assert any(z[2] in ('R','R_BOUNDARY_MIXED') for z in target['owned_supervision_spans'])
                    counts['original_reasoning_positive_target_after_observed_outcome_gate']+=1
                else:
                    assert target['owned_supervision_spans']==[]
                    counts['original_rejected_reasoning_preserved_but_zero_loss']+=1
                counts['original_reasoning_source_and_decoded_target_exactly_matched']+=1
        except Exception as exc:
            failures.append({'scope':'historical_raw','id':r['id'],'failure':type(exc).__name__})
    report={'schema_version':'wrd-independent-array-mask-validation-v4','status':'PASS' if not failures else 'FAIL',
            'counts':dict(counts),'failures':failures,'all_array_hashes_spans_and_target_ownership_checked':True,
            'native_render_decode_check_is_stratified_sample_not_every_record':True,
            'all_47_actual_original_reasoning_records_decoded_and_source_matched':counts['original_reasoning_source_and_decoded_target_exactly_matched']==47,
            'all_12_rejected_original_reasoning_targets_have_zero_loss':counts['original_rejected_reasoning_preserved_but_zero_loss']==12,
            'raw_exact_render_mask_unique_records':len(seen),'script_sha256':digest(Path(__file__)),
            'elapsed_seconds':round(time.monotonic()-start,3),'training_started':False}
    save(a.root/'COMPILED_DATA_VALIDATION.json',report);print(js(report),flush=True)
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
