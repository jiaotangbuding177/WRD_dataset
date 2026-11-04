"""Independent final17 original identity, exact-isolation and image bridge audit.
No producer code imported; no saved business action, model or training executed.
Only this directory is writable by this verifier.
"""
import collections
import copy
import datetime
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import time

ROOT = Path('D:/skillloop')
BASE = ROOT / 'output/20261031_wrd_curation09'
OUT = Path(__file__).resolve().parent
FAIL = []


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rows(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8-sig') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def canonical(value, sort=True):
    return sha(json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=sort))


def pin(path):
    return {'path': str(path.relative_to(ROOT)).replace('\\', '/') if path.is_relative_to(ROOT) else str(path),
            'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}


def pin_ok(path, descriptor):
    return path.is_file() and path.stat().st_size == descriptor['bytes'] and sha(path.read_bytes()) == descriptor['sha256']


def strings(value):
    if isinstance(value, str):
        yield value
        if value[:1] in '{[':
            try:
                yield from strings(json.loads(value))
            except (ValueError, TypeError):
                pass
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)


def normal(value):
    return re.sub(r'\s+', '', '\n'.join(strings(value)))


def decoded_messages(messages):
    result = copy.deepcopy(messages)
    for msg in result:
        for call in msg.get('tool_calls', []):
            fn = call.get('function', {})
            if isinstance(fn.get('arguments'), str):
                fn['arguments'] = json.loads(fn['arguments'])
    return result


def main():
    started = time.monotonic()
    scan_path = BASE / 'protection_followup09/FINAL17_01_ISOLATION_SCAN.json'
    producer = read(scan_path)
    raw_paths = [BASE / 'process/batch02/SCOPED_CANDIDATES_FINAL14_v2.jsonl.gz',
                 BASE / 'process/batch02/SCOPED_ADDITIONAL_CANDIDATES03_v3.jsonl.gz']
    raw = [r for p in raw_paths for r in rows(p)]
    prepared_path = BASE / 'compiled_followup_final02/CANDIDATES_STAGING_NOT_MAIN.jsonl.gz'
    prepared = {r['id']: r for r in rows(prepared_path)}
    old_path = BASE / 'holdout/PROTECTED_USER_VS_REAL_NATIVE_PREFIXES02.json'
    old_targets = collections.defaultdict(list)
    for record in read(old_path)['targets']:
        old_targets[record['original_owner_id']].append(record)
    ledger_path = ROOT / 'output/20261030_wrd_gap08/corpus/CORPUS_OWNER_COVERAGE.native.jsonl.gz'
    owner_ids = {r['owner_id'] for r in raw}
    ledger = {r['canonical_owner_id']: r for r in rows(ledger_path) if r['canonical_owner_id'] in owner_ids}
    contexts, carriers, identities = {}, {}, []
    for record in raw:
        owner = record['owner_id']
        packet_path = Path(record['source_context']['path'])
        packet = read(packet_path)
        context = packet['original_context']
        contexts[owner] = context
        index = record['original_message_index']
        proof = packet['owner']
        native = context['source_native']
        digest = native['sha256']
        if digest not in carriers:
            carrier_path = Path(native['path'])
            data = carrier_path.read_bytes()
            carriers[digest] = {'pin': pin(carrier_path), 'verified': len(data) == native['bytes'] and sha(data) == digest,
                                'events': [json.loads(s) if s.strip() else None for s in data.decode('utf-8-sig').splitlines()]}
        carrier = carriers[digest]
        event_lines = context['source_event_lines']
        target_line = event_lines[index]
        target_sha = canonical(context['messages'][index])
        original = ledger[owner]
        exact = all(carrier['events'][event_lines[j] - 1].get('type') == 'message'
                    and canonical(carrier['events'][event_lines[j] - 1].get('message')) == canonical(msg)
                    and event_lines[j] <= target_line
                    for j, msg in enumerate(context['messages'][:index + 1]))
        raw_lines = [i + 1 for i, event in enumerate(carrier['events'][:target_line])
                     if event and event.get('type') == 'message' and isinstance(event.get('message'), dict)]
        checks = {
            'packet_pin': pin_ok(packet_path, record['source_context']),
            'owner_episode_index': proof['owner_id'] == owner and proof['episode_id'] == record['original_episode_id']
                                    and proof['source_message_index'] == index,
            'target_SHA_all_sources': target_sha == record['original_target_sha256_sorted']
                                     == proof['target_original_SHA256_sorted'] == original['original_message_sha256_sorted'],
            'frozen_owner_native_identity': original['episode_id'] == record['original_episode_id']
                                           and original['source_message_index'] == index
                                           and original['source_event_line'] == target_line
                                           and original['source_native']['sha256'] == digest,
            'raw_carrier_SHA': carrier['verified'],
            'all_prefix_messages_match_raw': exact,
            'all_raw_message_events_through_target_preserved': raw_lines == event_lines[:index + 1],
            'prepared_identity_metadata': all(prepared[record['id']].get(k) == record.get(k) for k in
                ['owner_id', 'source_ids', 'source_context', 'original_episode_id', 'original_message_index', 'original_target_sha256_sorted']),
            'prepared_messages_after_JSON_argument_decode_only': decoded_messages(prepared[record['id']]['messages'])
                                                               == decoded_messages(record['messages']),
        }
        old_overlap = []
        for old in old_targets.get(owner, []):
            old_packet = read(ROOT / old['packet_pin']['path'])
            old_context = read(ROOT / old['context_pin']['path']) if old['context_pin'] else old_packet['original_context']
            same = old['target_message_index'] == index and old['episode_id'] == record['original_episode_id']
            same = same and old['original_target_SHA_verified'] == target_sha
            same = same and canonical(old_context['messages'][:index + 1]) == canonical(context['messages'][:index + 1])
            old_overlap.append({'lane': old['lane'], 'same_identity_and_prefix': same})
        checks['old118_overlaps_exact'] = all(x['same_identity_and_prefix'] for x in old_overlap)
        if not all(checks.values()):
            FAIL.append({'owner': owner, 'failed': [k for k, v in checks.items() if not v]})
        identities.append({'owner_id': owner, 'candidate_id': record['id'], 'source_ids': record['source_ids'],
                           'episode_id': record['original_episode_id'], 'target_index': index,
                           'target_SHA_sorted': target_sha, 'packet_pin': pin(packet_path), 'raw_carrier_pin': carrier['pin'],
                           'prefix_messages_compared': index + 1, 'future_messages_excluded': len(context['messages']) - index - 1,
                           'old118_overlaps': old_overlap, 'system_capture': context.get('system_capture_status'), 'checks': checks})

    comp_dir = BASE / 'compiled_followup_final02/compiled02'
    comp_report_path = comp_dir / 'COMPILATION_REPORT.json'
    comp_report = read(comp_report_path)
    compiled, compiled_pins = {}, []
    for descriptor in comp_report['files']:
        path = comp_dir / descriptor['path']
        assert pin_ok(path, descriptor)
        compiled_pins.append(pin(path))
        compiled.update({r['id']: r for r in rows(path)})
    assert set(compiled) == set(prepared) == {r['id'] for r in raw}
    assert all(compiled[rid]['messages'] == record['messages'] for rid, record in prepared.items())
    producer_prepared_path = ROOT / producer['prepared_pin']['path']
    assert pin_ok(producer_prepared_path, producer['prepared_pin'])
    previous_prepared = {r['id']: r for r in rows(producer_prepared_path)}
    assert set(previous_prepared) == set(prepared)
    assert all(previous_prepared[rid]['messages'] == row['messages'] for rid, row in prepared.items())
    previous_dir = BASE / 'compiled_followup_final01/compiled02'
    previous_report = read(previous_dir / 'COMPILATION_REPORT.json')
    previous_compiled = {r['id']: r for f in previous_report['files'] for r in rows(previous_dir / f['path'])}
    prune_checks = []
    for rid, row in compiled.items():
        before = previous_compiled[rid]
        old_positive = {i for start, end, component, weight in before['supervision_spans'] if weight > 0 for i in range(start, end)}
        new_positive = {i for start, end, component, weight in row['supervision_spans'] if weight > 0 for i in range(start, end)}
        assert row['messages'] == before['messages'] and row['input_ids'] == before['input_ids']
        assert new_positive <= old_positive
        prune_checks.append({'id': rid, 'messages_and_input_ids_unchanged': True,
                             'positive_mask_subset_only': True, 'before_positive': len(old_positive),
                             'after_positive': len(new_positive)})

    # Independently rebuild the1107 known source graph and user-only patterns.
    binding_path = ROOT / 'output/20261021_workflow_skill_library/source_bindings.json'
    bindings = read(binding_path)
    conv, groups, materials = {}, collections.defaultdict(list), collections.defaultdict(list)
    parent = {s: s for s in bindings}

    def root(s):
        if parent[s] != s:
            parent[s] = root(parent[s])
        return parent[s]

    def join(a, b):
        x, y = root(a), root(b)
        if x != y:
            parent[max(x, y)] = min(x, y)

    for sid, binding in bindings.items():
        context = read(Path(binding['conversation']['path']))
        conv[sid] = context
        groups[context.get('leakage_component_id') or sid].append(sid)
        for material in binding['materials']:
            if material.get('eligible_real_input') and not material.get('synthetic') and material.get('historical_bytes_certified'):
                materials[material['sha256']].append(sid)
    for buckets in [groups, materials]:
        for members in buckets.values():
            for sid in members[1:]:
                join(members[0], sid)
    for e in rows(ROOT / 'output/20261026_wrd_dataset_v9/coordination/entrypoint_controller.native_paths.source_closed.jsonl.gz'):
        for sid in e.get('source_ids', []):
            if sid in bindings:
                join(e['source_id'], sid)
    original = {r['session_id'] for r in rows(ROOT / 'benchmark/enterprise_input_closed_v11_20261012/contracts/evaluation.jsonl')}
    h12 = {r['source_id'] for r in read(ROOT / 'output/20261026_ablation_v2/holdout_registry.json')['H']}
    inventory = read(ROOT / 'research/plans/20261027_wrd_main_v10/CLEAN_ACTOR_INVENTORY.json')
    static = {sid for sid, split in inventory['source_id_to_existing_split'].items() if split in ['dev', 'test']}
    protected_roots = {root(s) for s in original | h12 | static}
    protected = {s for s in bindings if root(s) in protected_roots}
    patterns = collections.defaultdict(list)
    pattern_count, user_count = collections.Counter(), 0

    def add_patterns(text, family, owner):
        for offset in range(0, len(text) - 159, 40):
            block = text[offset:offset + 160]
            patterns[sha(block)].append((block, family, owner, offset))
            pattern_count[family] += 1

    for sid in protected:
        for i, message in enumerate(conv[sid]['messages']):
            if message.get('role') == 'user':
                user_count += 1
                add_patterns(normal(message['content']), 'protected', (sid, i))
    catalog = read(BASE / 'holdout/TASK_CATALOG_ALL36_05.json')
    eval_shas = set()
    for task in catalog:
        if task['status'] == 'HOLD':
            continue
        add_patterns(normal(read(BASE / 'holdout' / task['task_input_pin']['path'])['messages'][0]['content']),
                     'eval', ('EVAL_REQUEST', task['task_id']))
        eval_shas.update(m['sha256'] for m in task['material_aliases'])
    for digest in eval_shas:
        add_patterns(normal((BASE / 'holdout/material_review/text' / (digest + '.txt')).read_text(encoding='utf-8')),
                     'eval', ('EVAL_MATERIAL', digest))
    assert len(protected) == 411 and user_count == 1927
    assert pattern_count == {'protected': 7651, 'eval': 1213}
    actual_matches = collections.Counter()
    normalized_characters = collections.Counter()
    for record in raw:
        owner = record['owner_id']
        index = record['original_message_index']
        for population, messages in [('prefix', contexts[owner]['messages'][:index + 1]),
                                     ('state', prepared[record['id']]['messages'])]:
            for mi, message in enumerate(messages):
                text = normal(message)
                normalized_characters[population] += len(text)
                # Different matcher from producer: hash EVERY160-character window,
                # not the producer's40-character candidate-prefix lookup.
                for offset in range(len(text) - 159):
                    block = text[offset:offset + 160]
                    for expected, family, origin, source_offset in patterns.get(sha(block), []):
                        if block == expected:
                            actual_matches[(record['id'], population, mi, family, origin, source_offset, offset, sha(block))] += 1
    declared = collections.Counter()
    reported_match_rows = []
    old_ac = {a['anchor_sha256'] for t in read(old_path)['targets'] if t['original_owner_id'] == 'ac76ab7ead15378debb0e555'
              for m in t['matches'] for a in m['anchors']}
    for row in producer['rows']:
        for population in ['prefix', 'state']:
            for family, field in [('protected', 'protected_user_' + ('original_prefix' if population == 'prefix' else 'new_state') + '_matches'),
                                  ('eval', 'eval26_' + ('original_prefix' if population == 'prefix' else 'new_state') + '_matches')]:
                for hit in row[field]:
                    origin = hit['source_origin']
                    key = ((origin['protected_source_id'], origin['protected_message_index']) if family == 'protected'
                           else (origin['kind'], origin.get('task_id', origin.get('sha256'))))
                    for anchor in hit['anchors']:
                        declared[(row['id'], population, hit['message_index'], family, key,
                                  anchor['source_normalized_offset'], anchor['message_normalized_offset'], anchor['sha256'])] += 1
                    template_only = family == 'protected' and row['owner_id'] == 'ac76ab7ead15378debb0e555' and all(a['sha256'] in old_ac for a in hit['anchors'])
                    reported_match_rows.append({'owner_id': row['owner_id'], 'population': population, 'family': family,
                        'message_index': hit['message_index'], 'message_SHA_sorted': hit['message_SHA_sorted'],
                        'protected_origin_metadata': {k: v for k, v in origin.items() if k != 'original_conversation_pin'},
                        'anchors_hashes_offsets_only': [{k: v for k, v in a.items() if k != 'text'} for a in hit['anchors']],
                        'classification': 'SAME_SHARED_PROMPTGUARD_AS_OLD_AC76' if template_only else 'REQUIRES_PRIVATE_REVIEW'})
                    assert template_only
    assert actual_matches == declared, (len(actual_matches), len(declared))
    assert not any(key[3] == 'eval' for key in actual_matches)

    image_record = next(r for r in raw if r['owner_id'] == '66e542b63e52392b7e1dbfc2')
    dep = image_record['execution_material_dependencies'][0]
    image_sha = dep['sha256']
    same_binding = [(sid, m) for sid, b in bindings.items() for m in b['materials'] if m.get('sha256') == image_sha]
    binding = next(m for sid, m in same_binding if sid == 'conv_e785906dc669')
    image_paths = [Path(binding['path']), Path(dep['actual_historical_workspace_path']), Path(dep['restored_path'])]
    image_pins = [pin(p) for p in image_paths]
    assert all(p['sha256'] == image_sha and p['bytes'] == 254392 for p in image_pins)
    assert {sid for sid, _ in same_binding} == {'conv_e785906dc669'}
    assert 'conv_e785906dc669' not in protected and image_sha not in eval_shas
    episode_catalog_path = ROOT / 'output/20261025_wrd_training_dataset/bundle/catalog/episodes.jsonl'
    line, episode = next((i, e) for i, e in enumerate(rows(episode_catalog_path), 1) if e.get('episode_id') == image_record['original_episode_id'])
    workspace_file = Path(episode['source_path']) / 'workspace' / PurePosixPath(dep['original_native_path']).relative_to('/workspace')
    assert str(workspace_file).replace('\\', '/').lower() == str(Path(dep['actual_historical_workspace_path'])).replace('\\', '/').lower()
    ctx = contexts[image_record['owner_id']]
    read_call = next(c for c in ctx['messages'][3]['content'] if c.get('type') == 'toolCall')
    feedback = '\n'.join(c['text'] for c in ctx['messages'][4]['content'] if c.get('type') == 'text')
    target_call = next(c for c in ctx['messages'][5]['content'] if c.get('type') == 'toolCall')
    assert read_call['arguments']['path'] == dep['original_native_path']
    assert dep['original_native_path'] in target_call['arguments']['command']
    assert feedback == 'Read image file [image/jpeg]\n[Current model does not support images. The image will be omitted from this request.]'
    image_bridge = {'SHA256': image_sha, 'bytes': 254392, 'source_id': 'conv_e785906dc669',
        'original_export_retained_workspace_and_restored_exact_pins': image_pins,
        'binding_provenance': {k: binding[k] for k in ['provenance', 'eligible_real_input', 'historical_bytes_certified', 'synthetic']},
        'all1107_binding_sources_with_same_SHA': sorted({sid for sid, _ in same_binding}),
        'known411_protected_binding_SHA_intersection': [], 'eval11_material_SHA_intersection': [],
        'episode_catalog_pin': pin(episode_catalog_path), 'episode_catalog_line': line,
        'original_episode_source_path': episode['source_path'], 'workspace_image_path_reconstructed_exactly': True,
        'native_read_index': 3, 'native_read_call_id': read_call['id'], 'omitted_image_feedback_index': 4,
        'feedback_SHA_sorted': canonical(ctx['messages'][4]), 'target_exec_index': 5,
        'target_exec_call_id': target_call['id'], 'command_SHA': sha(target_call['arguments']['command']),
        'native_read_did_not_deliver_image_bytes_to_model': True,
        'contemporaneous_native_read_byte_hash_receipt_present': False}
    assert all(prepared[rid]['messages'] == previous_prepared[rid]['messages'] for rid in prepared)
    assert len(raw) == len(prepared) == len(compiled) == 17
    covered = [r['owner_id'] for r in raw if old_targets.get(r['owner_id'])]
    new = [r['owner_id'] for r in raw if not old_targets.get(r['owner_id'])]
    report = {
        'schema': 'wrd09-final17-independent-original-prefix-and-isolation-QA-v1',
        'status': 'PASS_CAPTURED_PREFIX_IDENTITIES_AND_INDEPENDENT_EXACT_ISOLATION_SCAN' if not FAIL else 'FAIL',
        'review_authorship': 'Independent current_source_registry child. Producer scanner/compiler not imported or executed. Protected patterns only original role=user. Independent full160SHA-window matching was used for every final17 originalprefix and newstate.',
        'at': datetime.datetime.now().isoformat(),
        'pins': [pin(P) for P in [scan_path, BASE / 'protection_followup09/FINAL17_FINAL02_INHERITANCE_QA.json',
                                 prepared_path, comp_report_path, producer_prepared_path,
                                 previous_dir / 'COMPILATION_REPORT.json', ledger_path, old_path, binding_path]]
                + [pin(p) for p in raw_paths] + compiled_pins,
        'script_pin': pin(Path(__file__).resolve()),
        'counts': {'records': 17, 'unique_original_owners': 17, 'original_carriers_hashed': len(carriers),
                   'native_prefix_message_instances_compared_to_raw': sum(x['prefix_messages_compared'] for x in identities),
                   'owners_covered_by_old118': len(covered), 'owners_new_to_old118': len(new),
                   'compiled_messages_exactly_equal_prepared': 17, 'protected_sources': len(protected),
                   'protected_original_user_messages': user_count, 'protected_patterns': pattern_count['protected'],
                   'eval_patterns': pattern_count['eval'], 'scanned_normalized_characters': dict(normalized_characters),
                   'positive_pair_rows': len(reported_match_rows), 'positive_anchor_instances': sum(actual_matches.values()),
                   'protected_prefix_origin_pairs': sum(r['family'] == 'protected' and r['population'] == 'prefix' for r in reported_match_rows),
                   'protected_state_origin_pairs': sum(r['family'] == 'protected' and r['population'] == 'state' for r in reported_match_rows),
                   'eval_prefix_and_state_matches': 0, 'private_business_matches_in_exact160_scope': 0},
        'new_owner_ids_vs_old118': sorted(new), 'per_owner_identity': identities,
        'independent_scan_exactly_equals_producer_match_multiset': True,
        'final02_vs_final01_pruning_identity_QA': prune_checks,
        'final02_supervised_tokens': sum(r['supervised_tokens'] for r in compiled.values()),
        'final02_input_tokens': sum(r['total_tokens'] for r in compiled.values()),
        'reported_match_QA_hashes_only': reported_match_rows,
        'image_dependency_SHA_bridge': image_bridge,
        'limits': [
            'PASS is exact captured identity and exact160-string isolation only, not global ancestry closure, semantic quality admission, completeWRD capability or KEEP evidence.',
            'Original prefix slices stop at target. New authored functional state remains different from original input; originalsystem capture remains incomplete.',
            'All17 compiled message objects equal prepared ones. Raw toolarguments can be JSONstrings and prepared dictionaries; only exact JSONobject equality is claimed for that representation change.',
            'Final14v2 af98 helper precondition and additional03v2 representative-color wording are new functional-state choices; they do not rewrite originaltarget or historical thought.',
            'Reported matches are only the sharedac76 PromptGuard wrapper, equal to the old audited template hashes. No other exact160 protected/eval hit was found by the independent scan.',
            '160patterns at40stride detect every uninterrupted normalized common substring>=199chars in strings actually scanned. Shorter, paraphrased, image-only, reencoded or unrecorded ancestors remain UNKNOWN.',
            'Image byte bridge compares authenticexport, retained originalworkspace and restoredfile, but the originalnative read acknowledgement has no byteSHA and explicitly omitted the image from modelinput.',
            'No originalbusiness program, palette extraction, externalAPI, modelinference or training was run. Modelweights0; no semantic success inferred from old completed/exit0.',
            'Frozenholdout, evalarrays, QA05 and mainmanifest were not written. Only this independentdirectory was modified.',
        ],
        'failures': FAIL, 'main_manifest_changed': False, 'training_started': False,
        'elapsed_seconds': round(time.monotonic() - started, 3),
    }
    path = OUT / 'FINAL17_ISOLATION_INDEPENDENT_QA.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'QA': pin(path), 'status': report['status'], 'counts': report['counts'],
                      'new_owner_ids': sorted(new), 'failures': FAIL}, ensure_ascii=False))


if __name__ == '__main__':
    main()
