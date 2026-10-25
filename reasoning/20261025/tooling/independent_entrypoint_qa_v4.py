"""Read-only QA of the newest curated reasoning and public training partitions."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from independent_compiled_qa_v4 import OUT, ROOT, ASSETS, HEADER, THINK_OPEN, THINK_CLOSE, rows, load, digest, dumps, verify_arrays


def main():
    reviewed = load(OUT / 'curated_reasoning/CURATED_REASONING_REPORT.json')
    forbidden = set(reviewed['semantic_hold_ids'])
    base = {r['id']: r for r in rows(OUT / 'raw_reasoning_evolution_final/historical_original_reasoning_records.jsonl.gz')}
    expected = {key for key, r in base.items() if r['total_tokens'] <= 32768 and r['supervised_tokens'] and key not in forbidden}
    actual = set(); controlled = Counter()
    for r in rows(OUT / 'curated_reasoning/controlled.original_reasoning32k.jsonl.gz'):
        verify_arrays(r); original = base[r['id']]
        assert r['id'] not in actual and r['id'] not in forbidden
        actual.add(r['id'])
        assert r['input_ids'] == original['input_ids'] and r['supervision_spans'] == original['supervision_spans']
        assert r['total_tokens'] <= 32768 and r['supervised_tokens'] > 0
        assert r['source_scope_review_sha256'] == digest(OUT / 'RAW_SCOPE_REVIEW.json')
        assert r['training_admitted'] is True and r['human_gold'] is False and r['semantic_approved'] is False
        controlled['records'] += 1; controlled['supervised_tokens'] += r['supervised_tokens']
        controlled['original_reasoning_records'] += bool(r['original_reasoning_characters'])
        controlled['R_tokens'] += r['supervised_tokens_by_component'].get('R', 0)
        controlled['R_boundary_tokens'] += r['supervised_tokens_by_component'].get('R_BOUNDARY_MIXED', 0)
    assert actual == expected and len(actual) == 116
    assert controlled['supervised_tokens'] == 196294
    assert controlled['original_reasoning_records'] == 30 and controlled['R_tokens'] == 121511
    assert controlled['R_boundary_tokens'] == 30
    public_sources = {}
    for p in (OUT / 'curated_reasoning/public').glob('*.pairs.jsonl.gz'):
        for r in rows(p):
            assert r['publication_approved'] is True
            assert r['id'] not in public_sources
            public_sources[r['id']] = {'record': r, 'file_sha': digest(p)}
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(ASSETS / 'primary_14b', local_files_only=True, trust_remote_code=False)
    public_counts = {}; bindings = {}; source_scopes = {r['pair_id']: r['reviewed_scope'] for r in rows(OUT / 'controlled/sse_scope_review.by_pair.jsonl.gz')}
    outcomes = {r['id']: r for r in rows(OUT / 'controlled/sse_action_outcome.labels.jsonl.gz')}
    for bank in ('public_reasoning_compiled_final', 'public_actor_aux_compiled'):
        directory = OUT / bank; counts = Counter(); all_ids = set(); partition_ids = set(); fingerprints = set()
        report = load(directory / 'PUBLIC_REASONING_COMPILATION_REPORT.json')
        for r in rows(directory / 'all_records.jsonl.gz'):
            verify_arrays(r); source = public_sources[r['id']]
            assert r['id'] not in all_ids; all_ids.add(r['id'])
            assert r['source_public_pair_file_sha256'] == source['file_sha']
            assert r['source_public_record_sha256'] == hashlib.sha256(dumps(source['record']).encode()).hexdigest()
            assert r['source_scope_review_sha256'] == digest(OUT / 'RAW_SCOPE_REVIEW.json')
            assert r['publication_approved'] is True and r['current_native_runtime_equivalence_claimed'] is False
            if r['source_pair_file'] == 'sse_core.pairs.jsonl.gz':
                assert source_scopes[r['id']] == 'source_proven_learning_development_candidate'
                assert outcomes[r['id']]['mechanically_eligible_action_after_real_outcome_gate'] is True
                assert r['id'] not in forbidden
            target = source['record']['original_response']['choices'][0]['message']
            thought = target.get('reasoning_content') or ''
            if thought:
                decoded = tokenizer.decode(r['input_ids'], skip_special_tokens=False, clean_up_tokenization_spaces=False)
                assert hashlib.sha256(decoded.encode()).hexdigest() == r['rendered_sha256']
                t = next(t for t in r['targets'] if t.get('id') == r['id'])
                a, b = t['rendered_assistant_span']; chunk = decoded[a:b]
                assert chunk.startswith(HEADER + THINK_OPEN + thought + THINK_CLOSE + (target.get('content') or ''))
                counts['privacy_transformed_reasoning_decode_matches_source'] += 1
            counts['all_compiled_records'] += 1
        for name, low, high in (('common16k.jsonl.gz', 0, 16384), ('common32k_long_only.jsonl.gz', 16384, 32768)):
            path = directory / name; bindings[str(path.relative_to(OUT))] = digest(path)
            for r in rows(path):
                verify_arrays(r)
                assert r['id'] not in partition_ids and r['id'] in all_ids
                assert low < r['total_tokens'] <= high and r['supervised_tokens'] > 0
                partition_ids.add(r['id'])
                fingerprint = (r['input_ids_sha256_u32le'], r['supervision_spans_sha256'])
                assert fingerprint not in fingerprints; fingerprints.add(fingerprint)
                counts['trainable_le32k_records'] += 1
                counts['trainable_le32k_supervised_tokens'] += r['supervised_tokens']
                counts['trainable_R_tokens'] += r['supervised_tokens_by_component'].get('R', 0)
                counts['trainable_R_boundary_tokens'] += r['supervised_tokens_by_component'].get('R_BOUNDARY_MIXED', 0)
        assert counts['all_compiled_records'] == report['counts']['pairs_compiled']
        assert counts['trainable_le32k_records'] == report['counts']['positive_complete_le32k']
        assert counts['trainable_le32k_supervised_tokens'] == report['counts']['le32k_supervised_tokens']
        public_counts[bank] = dict(counts)
    result = {'schema_version': 'wrd-latest-reasoning-entrypoint-independent-qa-v4',
        'status': 'PASS_LATEST_ARRAYS_PARTITIONS_SCOPE_AND_OUTCOME_NOT_SEMANTIC_GOLD',
        'controlled_curated_reasoning': dict(controlled), 'public_banks': public_counts,
        'semantic_numeric_boundary_hold_excluded': sorted(forbidden),
        'public_reasoning_is_explicitly_privacy_transformed_not_original_byte_claim': True,
        'original_12_rejected_sse_and_7_formal_source_sse_and_m5_not_positive': True,
        'native_source_scope_overlay_is_separate_required_gate': 'NATIVE_SOURCE_SPLIT_AUDIT.json',
        'native_source_scope_audit_sha256': digest(OUT / 'NATIVE_SOURCE_SPLIT_AUDIT.json'),
        'source_scope_report_sha256': digest(OUT / 'RAW_SCOPE_REVIEW.json'),
        'prior_quality_delta_qa_sha256': digest(OUT / 'COMPILED_DATA_INDEPENDENT_QA.final.json'),
        'latest_partition_sha256': bindings, 'training_started': False, 'semantic_gold_created': 0,
        'script_sha256': digest(Path(__file__))}
    (OUT / 'COMPILED_DATA_INDEPENDENT_QA.entrypoints.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(dumps({'status': result['status'], 'controlled': dict(controlled), 'public': public_counts}), flush=True)


if __name__ == '__main__': main()
