"""Read-only delta QA for outcome-gated R and curated native windows."""
from collections import Counter
import ast
import gzip
import hashlib
import json
from pathlib import Path
import time
from independent_compiled_qa_v4 import OUT, ROOT, rows, load, digest, dumps, ush, verify_arrays


def previous_rejects():
    directory = ROOT / 'output/20261025_wrd_training_preflight/local_review'
    first, second = {}, {}
    for name in ('screen_reviews.jsonl', 'make_a_reviews.jsonl', 'make_b_reviews.jsonl', 'screen_terminal_reviews.jsonl', 'make_terminal_reviews.jsonl'):
        p = directory / name
        if p.is_file():
            for row in read_plain_rows(p): first[row['id']] = row
    for name in ('screen_second_reviews.jsonl', 'make_a_second_reviews.jsonl', 'make_b_second_reviews.jsonl'):
        p = directory / name
        if p.is_file():
            for row in read_plain_rows(p): second[row['id']] = row
    status = {}
    for key, row in first.items():
        decision = row['decision']; other = second.get(key)
        if other:
            decision = 'reject' if 'reject' in {decision, other['decision']} else decision if decision == other['decision'] else 'needs_context'
        status[key] = decision
    p = directory / 'adjudication.jsonl'
    if p.is_file():
        for row in read_plain_rows(p): status[row['id']] = row['decision']
    errata = load(ROOT / 'output/20261025_wrd_training_dataset/git_release/preflight/20261025/ANNOTATION_ERRATA.json')
    for row in errata['corrections']:
        if row['id'] in status: status[row['id']] = row['effective_semantic_decision']
    rejects = {key for key, decision in status.items() if decision == 'reject'}
    assert len(rejects) == 61
    return rejects


def read_plain_rows(p):
    with p.open(encoding='utf-8-sig') as f:
        for line in f:
            if line.strip(): yield json.loads(line)


def syntax_holds_and_source_targets(source):
    holds = set(); provenance = {}
    for record in rows(source):
        for index, message in enumerate(record['messages']):
            if message.get('role') != 'assistant': continue
            key = hashlib.sha256((record['episode_id'] + ':' + str(index)).encode()).hexdigest()[:24]
            provenance[key] = {'sha': hashlib.sha256(dumps(message).encode()).hexdigest(), 'stop': message.get('stopReason')}
            for block in message.get('content', []) if isinstance(message.get('content'), list) else []:
                if not isinstance(block, dict) or block.get('type') != 'toolCall' or block.get('name') != 'write': continue
                args = block.get('arguments') or {}
                if not isinstance(args, dict) or not isinstance(args.get('content'), str): continue
                path = str(args.get('path', args.get('file_path', ''))).lower()
                try:
                    if path.endswith('.py'): ast.parse(args['content'])
                    elif path.endswith('.json'):
                        json.loads(args['content'], parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonstandard_constant')))
                except (ValueError, SyntaxError, RecursionError): holds.add(key)
    return holds, provenance


def main():
    started = time.monotonic(); counts = Counter(); source_bindings = {}; audit_samples = []
    original_qa = load(OUT / 'COMPILED_DATA_INDEPENDENT_QA.json')
    assert original_qa['status'].startswith('PASS')
    for name, expected in original_qa['source_and_array_hashes'].items():
        assert digest(OUT / name) == expected
    # Original native arrays are not retested: only metadata is indexed for exact delta comparison.
    rejects = previous_rejects(); curated_report = load(OUT / 'curated_native/CURATED_NATIVE_REPORT.json')
    scope_counts = {}
    for scope in ('controlled', 'public'):
        source = ROOT / ('output/20261025_wrd_training_dataset/bundle/canonical/native_episodes.jsonl.gz' if scope == 'controlled' else
                         'output/20261025_wrd_fullchain_reaudit/public_projection/fullchain.native_sessions.jsonl.gz')
        syntax, provenance = syntax_holds_and_source_targets(source)
        old = {}; expected_positive_ids = set(); incomplete_source_targets = set()
        for name in ('full_stage_records.jsonl.gz', 'prefix32k_records.jsonl.gz'):
            for r in rows(OUT / ('native_compiled_' + scope + '_final') / name):
                if r['total_tokens'] > 32768: continue
                assert r['episode_id'] not in old
                for t in r['targets']:
                    original = provenance[t['id']]
                    assert t['source_message_sha256'] == original['sha']
                    assert t['observed_native_stop_reason'] == original['stop']
                    if original['stop'] in {'length', 'aborted', 'error'}:
                        assert t['owned_supervision_spans'] == []
                        incomplete_source_targets.add(t['id'])
                old[r['episode_id']] = {'tokens_sha': r['input_ids_sha256_u32le'], 'total_tokens': r['total_tokens'],
                    'view': r['view'], 'kind': r['kind'], 'spans': r['supervision_spans'],
                    'targets': {t['id']: t for t in r['targets']}}
                kept = [s for t in r['targets'] if t['id'] not in rejects | syntax for s in t['owned_supervision_spans']]
                if kept and r['kind'] in {'screen', 'make', 'prepare', 'review', 'actor'}:
                    expected_positive_ids.add(r['episode_id'])
        actual_episodes = set(); owners = set(); stats = Counter()
        for role in ('core32k', 'actor_aux32k'):
            path = OUT / 'curated_native' / (scope + '.' + role + '.jsonl.gz')
            source_bindings[str(path.relative_to(OUT))] = digest(path)
            for r in rows(path):
                verify_arrays(r)
                assert r['episode_id'] not in actual_episodes
                actual_episodes.add(r['episode_id']); base = old[r['episode_id']]
                assert r['total_tokens'] <= 32768 and r['supervised_tokens'] > 0
                assert r['input_ids_sha256_u32le'] == base['tokens_sha'] and r['total_tokens'] == base['total_tokens']
                assert r['view'] == base['view'] and r['kind'] == base['kind']
                assert r['training_admitted'] is True and r['semantic_approved'] is False and r['human_gold'] is False
                assert (r['kind'] == 'actor') == (role == 'actor_aux32k')
                expected_spans = []
                for t in r['targets']:
                    before = base['targets'][t['id']]
                    assert t['source_message_sha256'] == before['source_message_sha256']
                    expected = [] if t['id'] in rejects | syntax else before['owned_supervision_spans']
                    assert t['owned_supervision_spans'] == expected
                    if expected:
                        assert t['id'] not in owners
                        owners.add(t['id']); expected_spans.extend(expected)
                        stats[role + ':targets'] += 1
                assert sorted(expected_spans) == r['supervision_spans']
                stats[role + ':windows'] += 1
                stats[role + ':supervised_tokens'] += r['supervised_tokens']
                stats[role + ':processed_tokens'] += r['total_tokens']
        assert actual_episodes == expected_positive_ids
        for role in ('core32k', 'actor_aux32k'):
            expected = curated_report['reports'][scope]['counts']
            for field in ('windows', 'supervised_tokens', 'processed_tokens'):
                assert stats[role + ':' + field] == expected[role + ':' + field]
            assert stats[role + ':targets'] == expected[role + ':owned_targets']
        assert not owners & rejects and not owners & syntax and not owners & incomplete_source_targets
        stats['source_syntax_hold_ids'] = len(syntax)
        stats['old_61_ai_reject_ids_intersection_with_training_owners'] = len(owners & rejects)
        stats['positive_owned_targets_unique'] = len(owners)
        scope_counts[scope] = dict(stats)
        print(dumps({'curated_qa_scope': scope, 'counts': dict(stats), 'elapsed_seconds': round(time.monotonic()-started, 2)}), flush=True)

    # Source proposal / original outcome labels, independent of finalize_raw logic.
    label_path = OUT / 'controlled/sse_action_outcome.labels.jsonl.gz'
    labels = {r['id']: r for r in rows(label_path)}
    sse = {r['id']: r for r in rows(OUT / 'controlled/sse_reasoning_pairs.evolution.mechanical.jsonl.gz')}
    transcripts = {}; bad = set()
    for key, label in labels.items():
        path = Path(label['source_transcript_path'])
        assert digest(path) == label['source_transcript_sha256']
        if str(path) not in transcripts: transcripts[str(path)] = load(path)
        index = int(label['event_json_pointer'].split('/')[1])
        row = transcripts[str(path)][index]
        assert row['proposal'] == sse[key]['observed_parsed_output']
        event = row['event']
        assert event['action_id'] == label['original_action_id']
        assert event['status'] == label['original_status']
        expected_positive = event['status'] != 'REJECTED' and isinstance(row['proposal'].get('arguments'), dict)
        assert label['mechanically_eligible_action_after_real_outcome_gate'] == expected_positive
        if not expected_positive: bad.add(key)
        counts['original_outcome_labels_joined_exactly'] += 1
    assert len(labels) == 45 and len(bad) == 12
    previous = {r['id']: r for r in rows(OUT / 'raw_reasoning_evolution_compiled/historical_original_reasoning_records.jsonl.gz')}
    final_report = load(OUT / 'raw_reasoning_evolution_final/RAW_COMPILATION_REPORT.json')
    assert final_report['source_action_outcome_labels_sha256'] == digest(label_path)
    final_ids = set(); raw_stats = Counter()
    for r in rows(OUT / 'raw_reasoning_evolution_final/historical_original_reasoning_records.jsonl.gz'):
        verify_arrays(r); base = previous[r['id']]
        assert r['id'] not in final_ids; final_ids.add(r['id'])
        assert r['input_ids'] == base['input_ids']
        assert r['rendered_sha256'] == base['rendered_sha256']
        assert r['original_reasoning_characters'] == base['original_reasoning_characters']
        if r['id'] in bad:
            assert r['supervision_spans'] == [] and r['supervised_tokens'] == 0
            assert r['positive_target_after_original_outcome_gate'] is False
            counts['actual_rejected_targets_all_components_zero_loss'] += 1
        else:
            assert r['supervision_spans'] == base['supervision_spans']
        raw_stats['preserved_records'] += 1
        if r['supervised_tokens']:
            raw_stats['positive_records'] += 1
            if r['total_tokens'] <= 32768:
                raw_stats['trainable_complete_le32k_records'] += 1
                raw_stats['trainable_complete_le32k_supervised_tokens'] += r['supervised_tokens']
                for c, n in r['supervised_tokens_by_component'].items(): raw_stats['le32k_component_' + c] += n
    assert final_ids == set(previous)
    assert raw_stats['preserved_records'] == 158 and raw_stats['positive_records'] == 146
    assert raw_stats['trainable_complete_le32k_records'] == 117
    assert raw_stats['trainable_complete_le32k_supervised_tokens'] == 206840
    assert raw_stats['le32k_component_R'] == 128545 and raw_stats['le32k_component_R_BOUNDARY_MIXED'] == 31
    for name, meta in final_report['outputs'].items():
        path = OUT / 'raw_reasoning_evolution_final' / name
        assert digest(path) == meta['sha256'] and path.stat().st_size == meta['bytes']
        source_bindings[str(path.relative_to(OUT))] = digest(path)
    report = {'schema_version': 'wrd-independent-outcome-and-curated-qa-v4',
        'status': 'PASS_DELTA_BYTES_MASKS_SOURCE_AND_REAL_OUTCOME_NOT_SEMANTIC_GOLD',
        'prior_diagnostic_qa_preserved': 'COMPILED_DATA_INDEPENDENT_QA.json',
        'prior_diagnostic_qa_sha256': digest(OUT / 'COMPILED_DATA_INDEPENDENT_QA.json'),
        'native_curated_counts': scope_counts, 'raw_final_counts': dict(raw_stats), 'checks': dict(counts),
        'curated_inputs_exact_sha_match_original_verified_arrays': True,
        'curated_spans_only_remove_known_rejects_or_unparseable_declared_writes': True,
        'curated_no_new_or_duplicate_target_owners': True,
        'real_source_target_hash_and_original_stop_references_checked': True,
        'raw_original_thought_and_inputs_unchanged_12_actual_rejects_have_zero_loss': True,
        'source_scope_report_sha256': digest(OUT / 'RAW_SCOPE_REVIEW.json'),
        'original_action_outcome_labels_sha256': digest(label_path), 'new_output_sha256': source_bindings,
        'raw_formal_sse_and_unknown_m5_still_excluded': True,
        'official_qwen_variant_not_claimed_unchanged_or_runtime_integrated': True,
        'tokenizer_independent_call_samples_from_prior_qa_remain_valid_inputs_unchanged': True,
        'all_rows_dual_tokenizer_independent_calls_not_claimed': True,
        'semantic_gold_created': 0, 'training_started': False, 'gpu_used': False,
        'script_sha256': digest(Path(__file__)), 'elapsed_seconds': round(time.monotonic()-started, 3)}
    (OUT / 'COMPILED_DATA_INDEPENDENT_QA.final.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(dumps({'status': report['status'], 'native': scope_counts, 'raw': dict(raw_stats), 'checks': dict(counts),
                 'elapsed_seconds': report['elapsed_seconds']}), flush=True)


if __name__ == '__main__': main()
