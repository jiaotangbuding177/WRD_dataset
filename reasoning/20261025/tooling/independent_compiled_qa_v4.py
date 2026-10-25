"""Independent read-only byte/mask/source QA; never modifies compiler outputs."""
from array import array
from bisect import bisect_right
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
ROOT = Path('D:/skillloop')
OUT = ROOT / 'output/20261025_wrd_reasoning_recovery_v4'
ASSETS = ROOT / 'output/20261025_wrd_training_preflight/tokenizer_assets'
HEADER = '<|im_start|>assistant\n'
THINK_OPEN = '<think>\n'
THINK_CLOSE = '\n</think>\n\n'


def dumps(x): return json.dumps(x, ensure_ascii=False, separators=(',', ':'))
def hbytes(x): return hashlib.sha256(x).hexdigest()
def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()
def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip(): yield json.loads(line)
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def ush(ids):
    packed = array('I', ids)
    if sys.byteorder != 'little': packed.byteswap()
    return hbytes(packed.tobytes())


def verify_arrays(r):
    ids = r['input_ids']; spans = r['supervision_spans']
    assert len(ids) == r['total_tokens']
    assert ush(ids) == r['input_ids_sha256_u32le']
    assert hbytes(dumps(spans).encode()) == r['supervision_spans_sha256']
    counter = Counter(); end = 0
    for a, b, label, weight in spans:
        assert type(a) is int and type(b) is int and 0 <= a < b <= len(ids) and a >= end
        assert isinstance(weight, (float, int)) and weight > 0
        assert label in {'F', 'R', 'R_BOUNDARY_MIXED', 'A', 'E', 'D', 'MIXED'}
        counter[label] += b - a; end = b
    assert dict(counter) == r['supervised_tokens_by_component']
    assert sum(counter.values()) == r['supervised_tokens']
    owned = []; incomplete = 0
    for t in r['targets']:
        owned.extend(t['owned_supervision_spans'])
        assert sum(b - a for a, b, _, _ in t['owned_supervision_spans']) == t['supervised_tokens']
        assert all(b <= t['response_end_token_exclusive'] for a, b, _, _ in t['owned_supervision_spans'])
        if t.get('mechanical_usable') is not True:
            assert t['owned_supervision_spans'] == []
        if t.get('observed_native_stop_reason') in {'length', 'aborted', 'error'}:
            assert not t['mechanical_usable'] and not t['owned_supervision_spans']
            incomplete += bool(t.get('nonempty'))
    assert sorted(owned, key=lambda s: s[0]) == spans
    assert r.get('human_gold') is False and r.get('semantic_approved') is False
    return counter, incomplete


def project_native(source):
    result = []
    if isinstance(source.get('system'), str) and source['system']:
        result.append({'role': 'system', 'content': source['system']})
    for raw in source['messages']:
        content = raw.get('content', '')
        text = content if isinstance(content, str) else ''.join(b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text')
        calls = []
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get('type') == 'toolCall':
                    calls.append({'id': b.get('id'), 'type': 'function', 'function': {'name': b.get('name'), 'arguments': dumps(b.get('arguments', {}))}})
        role = raw.get('role')
        if role in {'tool', 'toolResult'}:
            result.append({'role': 'tool', 'content': text, 'tool_call_id': raw.get('toolCallId')})
        elif role in {'assistant', 'system', 'user'}:
            value = {'role': role, 'content': text}
            if calls: value['tool_calls'] = calls
            if role == 'assistant':
                thought = raw.get('reasoning_content')
                if not isinstance(thought, str):
                    thought = ''.join(str(b.get('thinking', b.get('text', ''))) for b in content if isinstance(b, dict) and b.get('type') in {'thinking', 'reasoning'}) if isinstance(content, list) else ''
                value['reasoning_content'] = thought or ''
            result.append(value)
    return result


def main():
    started = time.monotonic(); checks = Counter(); errors = []; source_hashes = {}; samples = []
    main = load(OUT / 'FINAL_NATIVE_COMPILATION_REPORT.json')
    owners_by_scope = {}; stats_by_scope = {}; sample_records = {}
    for scope in ('controlled', 'public'):
        directory = OUT / ('native_compiled_' + scope + '_final')
        for name, meta in main['reports'][scope]['outputs'].items():
            p = directory / name
            assert digest(p) == meta['sha256'] and p.stat().st_size == meta['bytes']
            source_hashes[str(p.relative_to(OUT))] = digest(p)
        prefix_iter = iter(rows(directory / 'prefix32k_records.jsonl.gz'))
        prefix = next(prefix_iter, None); counts = Counter(); owners = set(); sampled_stages = set()
        for index, record in enumerate(rows(directory / 'full_stage_records.jsonl.gz'), 1):
            _, incomplete = verify_arrays(record)
            counts['full_records'] += 1; counts['all_target_positions'] += len(record['targets'])
            counts['incomplete_nonempty_targets_zero_loss'] += incomplete
            counts['full_tokens'] += record['total_tokens']
            training = None
            if record['total_tokens'] <= 32768:
                counts['complete_stage_le32k'] += 1
                counts['complete_stage_le16k'] += record['total_tokens'] <= 16384
                training = record
            if prefix is not None and prefix['episode_id'] == record['episode_id']:
                verify_arrays(prefix)
                n = prefix['total_tokens']
                assert 0 < n <= 32768 < record['total_tokens']
                assert prefix['input_ids'] == record['input_ids'][:n]
                assert prefix['supervision_spans'] == [s for s in record['supervision_spans'] if s[1] <= n]
                assert prefix['targets'] == [t for t in record['targets'] if t['response_end_token_exclusive'] <= n]
                assert prefix['stage_complete_in_this_view'] is False
                training = prefix; counts['prefix_records'] += 1
                prefix = next(prefix_iter, None)
            if training is not None and training['supervised_tokens'] > 0:
                counts['train_windows_with_nonempty_loss'] += 1
                counts['training_supervised_tokens'] += training['supervised_tokens']
                for t in training['targets']:
                    if t['owned_supervision_spans']:
                        key = (record['episode_id'], t['id'])
                        assert key not in owners
                        owners.add(key)
                if record['kind'] not in sampled_stages:
                    sample_records[(scope, record['episode_id'])] = record
                    sampled_stages.add(record['kind'])
            if index % 256 == 0:
                print(dumps({'qa_scope': scope, 'read_full_records': index, 'elapsed_seconds': round(time.monotonic() - started, 2)}), flush=True)
        assert prefix is None
        expected = main['reports'][scope]['counts']
        assert counts['full_records'] == expected['sessions_compiled']
        assert counts['all_target_positions'] == expected['assistant_positions']
        assert counts['train_windows_with_nonempty_loss'] == expected['training_windows_with_owned_targets']
        assert counts['training_supervised_tokens'] == expected['training_window_supervised_tokens']
        assert counts['incomplete_nonempty_targets_zero_loss'] == expected['nonempty_incomplete_stop_targets']
        counts['unique_owned_targets_in_training_views'] = len(owners)
        owners_by_scope[scope] = owners; stats_by_scope[scope] = dict(counts)

    # Resolve sample inputs only after exact target identities are selected.
    source_paths = {'controlled': ROOT / 'output/20261025_wrd_training_dataset/bundle/canonical/native_episodes.jsonl.gz',
                    'public': ROOT / 'output/20261025_wrd_training_preflight/prepared_gated/public/support/canonical_native_episodes.jsonl.gz'}
    source_samples = {}
    for scope, path in source_paths.items():
        assert digest(path) == main['reports'][scope]['source_native_sessions_sha256']
        for source in rows(path):
            key = (scope, source['episode_id'])
            if key in sample_records: source_samples[key] = source

    # All recovered reasoning source targets, with body remaining local/in-memory.
    target_sources = {}; source_scope_by_pair = {}
    for source in (OUT / 'controlled/raw_pairs.all.jsonl.gz', OUT / 'controlled/sse_reasoning_pairs.mechanical.jsonl.gz'):
        for r in rows(source):
            target_sources[r['id']] = r['original_response']['choices'][0]['message']
            source_scope_by_pair[r['id']] = r.get('role_scope')
    scope_report = load(OUT / 'RAW_SCOPE_REVIEW.json')
    run_scopes = {r['run_path']: r for r in rows(OUT / 'controlled/raw_scope_review.by_run.jsonl.gz')}
    raw_gen_allowed = set()
    for r in rows(OUT / 'controlled/raw_pairs.all.jsonl.gz'):
        if r.get('role_scope') == 'historical_skill_generation_candidate':
            assert run_scopes[r['run_path']]['reviewed_scope'] == 'source_proven_learning_development_candidate'
            raw_gen_allowed.add(r['id'])
    sse_scopes = {r['pair_id']: r for r in rows(OUT / 'controlled/sse_scope_review.by_pair.jsonl.gz')}
    banned_sse = {key for key, r in sse_scopes.items() if r['reviewed_scope'] != 'source_proven_learning_development_candidate'}
    allowed_sse = {key for key, r in sse_scopes.items() if r['reviewed_scope'] == 'source_proven_learning_development_candidate'}
    assert len(allowed_sse) == 45 and len(banned_sse) == 8 and len(raw_gen_allowed) == 113
    rawdir = OUT / 'raw_reasoning_evolution_compiled'
    raw_report = load(rawdir / 'RAW_COMPILATION_REPORT.json')
    for name, meta in raw_report['outputs'].items():
        p = rawdir / name
        assert digest(p) == meta['sha256'] and p.stat().st_size == meta['bytes']
        source_hashes[str(p.relative_to(OUT))] = digest(p)
    raw_stats = Counter(); raw_ids = set(); reasoning_sample_records = []; raw_training_owners = set(); fingerprints = set()
    all_raw_reasoning_records = []
    for r in rows(rawdir / 'historical_original_reasoning_records.jsonl.gz'):
        verify_arrays(r); raw_stats['records'] += 1
        assert r['id'] not in raw_ids and r['id'] not in banned_sse
        raw_ids.add(r['id'])
        assert r['id'] in allowed_sse or r['id'] in raw_gen_allowed
        fingerprint = (r['input_ids_sha256_u32le'], r['supervision_spans_sha256'])
        raw_stats['duplicate_exact_render_and_mask'] += fingerprint in fingerprints
        fingerprints.add(fingerprint)
        source = target_sources[r['id']]
        assert len(source.get('reasoning_content') or '') == r['original_reasoning_characters']
        if source.get('reasoning_content'):
            all_raw_reasoning_records.append(r)
            raw_stats['records_with_original_reasoning'] += 1
        if r['total_tokens'] <= 32768 and r['supervised_tokens']:
            raw_stats['train_windows'] += 1; raw_stats['training_supervised_tokens'] += r['supervised_tokens']
            for t in r['targets']:
                if t['owned_supervision_spans']:
                    assert t['id'] == r['id'] and t['id'] not in raw_training_owners
                    raw_training_owners.add(t['id'])
            if source.get('reasoning_content') and len(reasoning_sample_records) < 4:
                reasoning_sample_records.append(r)
    assert raw_ids == allowed_sse | raw_gen_allowed
    assert raw_stats['records'] == 158 and raw_stats['records_with_original_reasoning'] == 47
    assert raw_stats['training_supervised_tokens'] == raw_report['counts']['training_window_supervised_tokens']

    # Independent tokenizers and template application, not compiler helper calls.
    from transformers import AutoTokenizer
    t14 = AutoTokenizer.from_pretrained(ASSETS / 'primary_14b', local_files_only=True, trust_remote_code=False)
    t8 = AutoTokenizer.from_pretrained(ASSETS / 'control_8b', local_files_only=True, trust_remote_code=False)
    names = ('tokenizer_config.json', 'tokenizer.json', 'vocab.json', 'merges.txt', 'generation_config.json')
    assets = {key: {n: digest(ASSETS / key / n) for n in names} for key in ('primary_14b', 'control_8b')}
    assert assets['primary_14b'] == assets['control_8b']
    template_info = load(OUT / 'CAUSAL_TEMPLATE.json'); template = template_info['variant']
    assert hbytes(template.encode()) == template_info['causal_template_sha256']
    assert template != t14.chat_template and template_info['variant_is_not_unmodified_official_template'] is True
    for (scope, eid), record in sample_records.items():
        messages = project_native(source_samples[(scope, eid)])
        rendered = t14.apply_chat_template(messages, tools=record['tools'] or None, chat_template=template,
            tokenize=False, add_generation_prompt=False, enable_thinking=False)
        assert hbytes(rendered.encode()) == record['rendered_sha256']
        a = t14(rendered, add_special_tokens=False, return_offsets_mapping=True)
        b = t8(rendered, add_special_tokens=False, return_offsets_mapping=True)
        assert a['input_ids'] == b['input_ids'] == record['input_ids']
        assert a['offset_mapping'] == b['offset_mapping']
        checks['independent_dual_tokenizer_native_samples'] += 1
        owned = [t for t in record['targets'] if t['owned_supervision_spans']]
        for target in owned[:3]:
            i = target['message_index']
            before = t14.apply_chat_template(messages[:i], tools=record['tools'] or None, chat_template=template,
                tokenize=False, add_generation_prompt=False, enable_thinking=False)
            through = t14.apply_chat_template(messages[:i+1], tools=record['tools'] or None, chat_template=template,
                tokenize=False, add_generation_prompt=False, enable_thinking=False)
            assert rendered.startswith(through) and through.startswith(before)
            assert target['rendered_assistant_span'] == [len(before), len(through)]
            assert rendered[len(before):].startswith(HEADER)
            for lo, hi, label, weight in target['owned_supervision_spans']:
                for s, e in a['offset_mapping'][lo:hi]:
                    assert len(before) + len(HEADER) <= s < e <= len(through)
            checks['native_assistant_target_ownership_source_render_samples'] += 1

    # Exact full-source thought check for all 47; offsets plus two assets on four trainable R records.
    for record in all_raw_reasoning_records:
        source = target_sources[record['id']]; thought = source['reasoning_content']
        decoded = t14.decode(record['input_ids'], skip_special_tokens=False, clean_up_tokenization_spaces=False)
        assert hbytes(decoded.encode()) == record['rendered_sha256']
        target = next(t for t in record['targets'] if t.get('id') == record['id'])
        lo, hi = target['rendered_assistant_span']; begin = lo + len(HEADER) + len(THINK_OPEN)
        assert decoded[lo:begin] == HEADER + THINK_OPEN
        assert decoded[begin:begin+len(thought)] == thought
        assert decoded[begin+len(thought):].startswith(THINK_CLOSE + (source.get('content') or ''))
        assert any(s[2] in {'R', 'R_BOUNDARY_MIXED'} for s in target['owned_supervision_spans'])
        checks['all_original_reasoning_decoded_exactly_matches_source'] += 1
    for record in reasoning_sample_records:
        decoded = t14.decode(record['input_ids'], skip_special_tokens=False, clean_up_tokenization_spaces=False)
        a = t14(decoded, add_special_tokens=False, return_offsets_mapping=True)
        b = t8(decoded, add_special_tokens=False, return_offsets_mapping=True)
        assert a['input_ids'] == b['input_ids'] == record['input_ids']
        assert a['offset_mapping'] == b['offset_mapping']
        target = next(t for t in record['targets'] if t.get('id') == record['id'])
        start = target['rendered_assistant_span'][0] + len(HEADER) + len(THINK_OPEN)
        finish = start + record['original_reasoning_characters']; cursor = start
        for lo, hi, label, weight in target['owned_supervision_spans']:
            if label not in {'R', 'R_BOUNDARY_MIXED'}: continue
            for s, e in a['offset_mapping'][lo:hi]:
                left, right = max(start, s), min(finish, e)
                if left < right:
                    assert left <= cursor
                    cursor = max(cursor, right)
        assert cursor == finish
        checks['independent_dual_tokenizer_trainable_original_R_samples'] += 1
        samples.append({'id': record['id'], 'source_role': record['role_scope'], 'total_tokens': record['total_tokens'],
                        'reasoning_characters': record['original_reasoning_characters'], 'full_thought_sha256': hbytes(target_sources[record['id']]['reasoning_content'].encode()),
                        'source_text_exact_and_complete': True, 'reasoning_characters_fully_covered_by_owned_R_tokens': True})
    assert len(samples) == 4
    report = {'schema_version': 'wrd-compiled-data-independent-qa-v4', 'status': 'PASS_TECHNICAL_BYTES_SOURCE_AND_MASK_NOT_SEMANTIC_QUALITY',
        'native_by_scope': stats_by_scope, 'historical_raw': dict(raw_stats), 'actual_independent_checks': dict(checks),
        'original_reasoning_canary_samples_no_body': samples, 'all_native_input_hashes_and_target_ownership_checked': True,
        'all_native_assistant_input_exclusion_character_checks_sampled_not_every_record': True,
        'all_47_original_reasoning_texts_decoded_and_source_matched': True,
        'second_tokenizer_called_on_independent_samples_not_every_row': True,
        'byte_identical_assets_independent_reuse_proof': assets,
        'custom_causal_qwen_variant_is_not_official_template': True,
        'runtime_variant_integration_still_unproven': True,
        'native_public_controlled_shared_owned_targets': len(owners_by_scope['public'] & owners_by_scope['controlled']),
        'public_and_controlled_banks_are_alternatives_must_not_concatenate': True,
        'formal_226_sse_pairs_excluded': 7, 'unmapped_m5_sse_pairs_excluded': 1,
        'raw_113_source_proof_report_sha256': digest(OUT / 'RAW_SCOPE_REVIEW.json'),
        'source_and_array_hashes': source_hashes, 'failures': errors,
        'script_sha256': digest(Path(__file__)), 'elapsed_seconds': round(time.monotonic()-started, 3),
        'training_started': False, 'model_weights_loaded': False, 'gpu_used': False,
        'semantic_gold_created': 0, 'full_autonomous_success_proven': False}
    (OUT / 'COMPILED_DATA_INDEPENDENT_QA.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(dumps({'status': report['status'], 'native': stats_by_scope, 'raw': dict(raw_stats), 'checks': dict(checks),
                 'elapsed_seconds': report['elapsed_seconds']}), flush=True)


if __name__ == '__main__':
    main()
