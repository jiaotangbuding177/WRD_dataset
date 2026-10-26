"""Read-only, per-sequence v9 payload/token/mask/provenance verification.

No weights are loaded. Only the frozen two tokenizers run on CPU. Writes a QA
receipt; it never edits compiled data, production files, or training arrays.
"""
from __future__ import annotations
from array import array
from collections import Counter, defaultdict
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261026_wrd_dataset_v9'


def js(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def rows(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path, 'rt', encoding='utf-8-sig') as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def integer_sha(ids):
    a = array('I', ids)
    if sys.byteorder != 'little':
        a.byteswap()
    return sha(a.tobytes())


def main():
    from transformers.utils.chat_template_utils import _render_with_assistant_indices
    spec = importlib.util.spec_from_file_location('v9_QA_native_renderer', ROOT / 'research/data_prep/wrd_reasoning_v4/compile_native.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    compiler = module.CausalCompiler(ROOT / 'output/20261025_wrd_training_preflight/tokenizer_assets')
    canonical = {r['episode_id']: r for r in rows(ROOT / 'output/20261025_wrd_training_dataset/bundle/canonical/native_episodes.jsonl.gz')}
    native_sources = {r['episode_id']: r for r in rows(OUT / 'recovery/episodes.contexts.jsonl.gz')}
    native_quality_flags = defaultdict(dict)
    for original_quality in rows(ROOT / 'output/20261026_wrd_quality_v8/controlled/native_targets.quality.jsonl.gz'):
        native_quality_flags[original_quality['episode_id']][original_quality['source_message_index']] = {
            'observed_tool_failure': original_quality.get('observed_tool_failure'),
            'current_exchange_structurally_paired': original_quality.get('current_exchange_structurally_paired')}
    protected = set()
    for p in (ROOT / 'benchmark').glob('*/contracts/evaluation.jsonl'):
        group = {r.get('session_id') for r in rows(p)} - {None}
        if len(group) == 226:
            protected |= group
    registry = json.loads((ROOT / 'output/20261026_ablation_v2/holdout_registry.json').read_text(encoding='utf-8-sig'))
    import re
    protected.update(re.findall(r'conv_[0-9a-f]{12}', js(registry)))
    labels = defaultdict(dict)
    for r in rows(OUT / 'processed/targets.processing.jsonl.gz'):
        labels[r['episode_id']][r['source_message_index']] = r
    compilation_report = json.loads((OUT / 'COMPILATION_REPORT.json').read_text(encoding='utf-8'))
    coordination_sources = {}
    coordination_input_pins = [p for p in compilation_report.get('immutable_input_pins', []) if Path(p['path']).parent == OUT / 'coordination']
    assert coordination_input_pins, 'Actual bound coordination inputs must be pinned'
    for input_pin in coordination_input_pins:
        path = Path(input_pin['path'])
        assert path.stat().st_size == input_pin['bytes'] and digest(path) == input_pin['sha256']
        for original in rows(path):
            coordination_sources[original['id']] = original
    counts, banks, components = Counter(), defaultdict(Counter), defaultdict(set)
    source_splits, route_splits, lineage_group_splits = defaultdict(set), defaultdict(set), defaultdict(set)
    failures, seen, files = [], set(), []
    rule_sources_verified = {}
    for path in sorted((OUT / 'sft').glob('*.jsonl.gz')):
        files.append({'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path)})
        for row in rows(path):
            rid = row.get('id')
            try:
                assert rid not in seen, 'duplicate row id'
                seen.add(rid)
                messages, tools = row['messages'], row.get('tools') or []
                assert row.get('training_started') is False
                assert not (set(row.get('source_ids') or []) & protected), 'protected source in payload provenance'
                assert all(isinstance(x, dict) and x.get('role') in {'system', 'user', 'assistant', 'tool'} for x in messages)
                kwargs = dict(compiler.tokenizers['primary_14b'].special_tokens_map)
                kwargs['enable_thinking'] = False
                rendered, ranges = _render_with_assistant_indices(compiler.compiled, messages, tools or None, None, False, **kwargs)
                assert rendered == compiler.plain_compiled.render(messages=messages, tools=tools or None, documents=None, add_generation_prompt=False, **kwargs)
                a = compiler.tokenizers['primary_14b'](rendered, add_special_tokens=False, return_offsets_mapping=True)
                b = compiler.tokenizers['control_8b'](rendered, add_special_tokens=False, return_offsets_mapping=True)
                assert a['input_ids'] == b['input_ids'] == row['input_ids'], 'actual tokenizer ids mismatch'
                assert a['offset_mapping'] == b['offset_mapping'], 'actual tokenizer offsets mismatch'
                compiler.proof['independent_second_tokenizer_calls'] += 1
                counts['independent_dual_tokenizer_sequence_checks'] += 1
                ids, offsets = a['input_ids'], a['offset_mapping']
                assert len(ids) == row['total_tokens'] <= 32768
                if '.16k.' in path.name:
                    assert len(ids) <= 16384
                if '.32k.' in path.name:
                    assert 16384 < len(ids) <= 32768
                assert integer_sha(ids) == row['input_ids_sha256_u32le']
                if 'rendered_sha256' in row:
                    assert sha(rendered) == row['rendered_sha256'], 'row rendered hash binds discarded future messages'
                spans = row['supervision_spans']
                assert sha(js(spans)) == row['supervision_spans_sha256']
                assert spans and sum(hi - lo for lo, hi, _, _ in spans) == row['supervised_tokens']
                assistants = [i for i, m in enumerate(messages) if m['role'] == 'assistant']
                assert len(assistants) == len(ranges)
                boundaries = {i: (lo + len(module.HEADER), hi) for i, (lo, hi) in zip(assistants, ranges)}
                for i, (lo, hi) in zip(assistants, ranges):
                    assert rendered[lo:hi].startswith(module.HEADER) and rendered[lo:hi].endswith(module.END)
                    text = messages[i].get('reasoning_content') or ''
                    assert rendered[lo:hi].startswith(module.HEADER + module.THINK_OPEN + text + module.THINK_CLOSE + (messages[i].get('content') or ''))
                owned = []
                owner_by_token = {}
                for t in row['targets']:
                    mi = t['message_index']
                    assert messages[mi]['role'] == 'assistant'
                    assert t.get('mechanical_usable') is True
                    assert t['supervised_tokens'] == sum(s[1] - s[0] for s in t['owned_supervision_spans']), 'per-target token count stale after masking'
                    for span in t['owned_supervision_spans']:
                        lo, hi, component, weight = span
                        assert 0 <= lo < hi <= len(ids)
                        assert component in {'F', 'R', 'E', 'D', 'A', 'MIXED', 'R_BOUNDARY_MIXED'}
                        assert isinstance(weight, (int, float)) and math.isfinite(weight) and 0 < weight <= 1
                        left, right = boundaries[mi]
                        for token in range(lo, hi):
                            assert token not in owner_by_token
                            s, e = offsets[token]
                            assert left <= s < e <= right, 'positive loss crosses assistant body into input/header'
                            owner_by_token[token] = mi
                        owned.append(span)
                assert sorted(owned) == spans, 'target owned masks differ from actual global masks'
                previous = 0
                for lo, hi, _, _ in spans:
                    assert lo >= previous
                    previous = hi
                # Materialize actual labels and assert all non-owned positions
                # retain -100; no system, user, tool or unapproved assistant loss.
                loss_labels = [-100] * len(ids)
                for lo, hi, _, _ in spans:
                    loss_labels[lo:hi] = ids[lo:hi]
                assert sum(v != -100 for v in loss_labels) == row['supervised_tokens']
                if row['bank'] == 'native_process':
                    original = native_sources[row['episode_id']]
                    converted, native_indices, _ = module.native_messages({'system': messages[0]['content'], 'messages': original['messages']})
                    position = {ni: i for i, ni in enumerate(native_indices) if ni is not None}
                    for overlay in original['reasoning_overlays_same_response_id']:
                        converted[position[overlay['message_index']]]['reasoning_content'] = overlay['text']
                    assert converted[:len(messages)] == messages, 'native student prefix or original R changed'
                    for t in row['targets']:
                        ni = t['source_message_index']
                        entry = labels[row['episode_id']][ni]
                        label = entry['scope_and_outcome_label']
                        assert entry['admitted_in_common_32k'] is True and entry['supervision_tier'] == t['supervision_tier']
                        assert label['source_admission'] == 'ADMIT' and not label.get('protected_sources_visible_prefix')
                        assert original['source_event_lines'][ni] == label['source_event_line']
                        if row['episode_id'] in canonical:
                            expected = canonical[row['episode_id']]['messages'][ni]
                            assert sha(js(expected)) == label['source_message_sha256']
                            assert expected.get('content') == original['messages'][ni].get('content')
                        if t['supervision_tier'] in {'outcome_skill_silver', 'evidence_review_silver'}:
                            scope_values = [label.get(k) for k in ['label_source_admission', 'outcome_label_source_admission', 'quality_label_source_admission']]
                            assert 'ADMIT' in scope_values, 'positive selected using unclosed future outcome label'
                        if t['supervision_tier'] == 'read_only_protocol_auxiliary':
                            current = messages[t['message_index']]
                            assert not current.get('content') and not current.get('reasoning_content')
                            assert all(x['function']['name'] in {'read', 'ls'} for x in current['tool_calls'])
                            flags = native_quality_flags[row['episode_id']].get(ni, {})
                            assert flags.get('observed_tool_failure') is False, 'unreviewed observed tool failure has positive protocol loss'
                            counts['native_positive_protocol_targets_without_observed_tool_failure'] += 1
                        counts['native_owned_targets_checked'] += 1
                elif row['bank'] == 'coordination':
                    original = row['coordination_original_record']
                    assert original.get('training_admitted') is True or original.get('source_admission') == 'ADMIT'
                    assert not original.get('direct_protected_source_ids')
                    assert not original.get('hold_reasons')
                    assert row['is_original_teacher_CoT'] is False
                    assert row['is_full_autonomous_execution_demonstration'] is False
                    source = coordination_sources[original['id']]
                    source_messages = [dict(m, reasoning_content=m.get('reasoning_content', '')) if m['role'] == 'assistant' else m for m in source['messages']]
                    assert source_messages == messages, 'coordination source messages changed'
                    assert row.get('rule_provenance') == source.get('rule_provenance')
                    for t in row['targets']:
                        assert not messages[t['message_index']].get('reasoning_content'), 'new annotation mislabelled as original R'
                        assert source['message_loss_mask'][t['message_index']] is True
                        annotation = json.loads(messages[t['message_index']]['content'])
                        references = annotation.get('evidence_refs') or []
                        assert references, 'rule annotation has no original source reference'
                        for reference in references:
                            if reference.get('path') != 'pipeline.py':
                                continue
                            expected = reference['sha256']
                            frozen = OUT / 'frozen_rule_sources' / ('pipeline.' + expected + '.py')
                            if expected not in rule_sources_verified:
                                assert frozen.is_file() and digest(frozen) == expected
                                rule_sources_verified[expected] = frozen.read_text(encoding='utf-8').splitlines()
                            lines = rule_sources_verified[expected]
                            assert reference['rule_anchor'] in lines[int(reference['line']) - 1], 'captured program rule line/anchor mismatch'
                            counts['frozen_rule_anchor_references_checked'] += 1
                    grouping = original.get('source_group_id')
                    if grouping:
                        lineage_group_splits[grouping].add(row['split'])
                else:
                    raise AssertionError('unknown bank')
                for source in row.get('source_ids') or []:
                    source_splits[source].add(row['split'])
                if row.get('route_id'):
                    route_splits[row['route_id']].add(row['split'])
                components[row['source_component_id']].add(row['split'])
                banks[row['bank']]['rows'] += 1
                banks[row['bank']]['input_tokens'] += len(ids)
                banks[row['bank']]['supervised_tokens'] += row['supervised_tokens']
                for lo, hi, component, _ in spans:
                    banks[row['bank']]['component_' + component] += hi - lo
                counts['verified_sequences'] += 1
            except Exception as exc:
                counts['failed_sequences'] += 1
                if len(failures) < 50:
                    failures.append({'file': path.name, 'id': rid, 'error_type': type(exc).__name__, 'reason': str(exc)[:400]})
            if (counts['verified_sequences'] + counts['failed_sequences']) % 100 == 0:
                print(js({'phase': 'independent_compiled_QA', 'counts': dict(counts)}), flush=True)
    split_errors = {}
    for name, groups in [('source', source_splits), ('route', route_splits), ('original_lineage_component', lineage_group_splits), ('compiled_component', components)]:
        split_errors[name] = {k: sorted(v) for k, v in groups.items() if len(v) > 1}
    assert files, 'No actual sft payloads exist'
    report = {'schema_version': 'wrd-v9-independent-per-sequence-QA-1.0',
        'status': 'PASS' if not failures and not any(split_errors.values()) else 'FAIL',
        'counts': dict(counts), 'by_bank': {k: dict(v) for k, v in banks.items()},
        'failures': failures, 'cross_split_errors': split_errors,
        'tokenizer_and_template_proof': compiler.proof,
        'actual_coordination_input_pins_verified': coordination_input_pins,
        'frozen_LF_rule_source_sha256_verified': sorted(rule_sources_verified),
        'all_sequences_reencoded_with_both_actual_frozen_tokenizers': True,
        'actual_ignore_index_labels_reconstructed': True,
        'quality_gold_or_closed_loop_effect_not_certified': True,
        'training_started': False, 'weights_loaded': False,
        'verified_files': files, 'verifier_script_sha256': digest(Path(__file__))}
    (OUT / 'COMPILED_QA.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(js({k: report[k] for k in ['status', 'counts', 'by_bank', 'failures', 'cross_split_errors']}), flush=True)
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
