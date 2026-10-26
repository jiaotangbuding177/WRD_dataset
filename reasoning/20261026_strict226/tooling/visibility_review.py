"""Offline source visibility review with original-226 boundary intact.

This is an evidence overlay, not a training exporter or a new agent loop.  It
recognizes original request-body schemas and concatenated JSON tool output that
the earlier complete-single-JSON scan did not cover.  No original is changed.
"""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path('D:/skillloop')
BUNDLE = ROOT / 'output/20261025_wrd_training_dataset/bundle'
BASE = ROOT / 'output/20261025_wrd_reasoning_recovery_v4'
OUT = ROOT / 'output/20261026_wrd_strict226_expansion'
SID = re.compile(r'conv_[a-f0-9]{12}')
PATH = re.compile(r'/workspace/[^\s\"\'<>`;,(){}\[\]]+')
DECODER = json.JSONDecoder()
BODY_KEYS = ('conversation', 'user_input', 'messages', 'turns', 'requests',
             'user_requests', 'user_request', 'user_request_preview', 'text')
DERIVED_KEYS = {'route_signature', 'workflow', 'steps', 'conditions', 'conflicts',
                'skills', 'skill', 'routes', 'route', 'cases', 'case', 'task'}


def rows(p):
    op = gzip.open if p.suffix == '.gz' else open
    with op(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def js(v):
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def sha_bytes(v):
    return hashlib.sha256(v).hexdigest()


def sha_file(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def exact_ids(v):
    if isinstance(v, str):
        return {v} if SID.fullmatch(v) else set()
    if isinstance(v, list):
        return set().union(*(exact_ids(x) for x in v)) if v else set()
    return set()


def named(v):
    if not isinstance(v, dict):
        return set()
    return set().union(*(exact_ids(v.get(k)) for k in (
        'source_id', 'session_id', 'conversation_id', 'source_ids', 'selected_source_ids')))


def texts(m):
    c = m.get('content')
    if isinstance(c, str):
        yield 0, c
    elif isinstance(c, list):
        for i, b in enumerate(c):
            if isinstance(b, dict) and b.get('type') == 'text' and isinstance(b.get('text'), str):
                yield i, b['text']


def decoded_values(t):
    """Decode complete JSON values, including `cat a.json b.json` and wrappers.

    A failed/truncated outer value may contain a complete inner record.  Such an
    inner record is positive evidence of visibility only, never proof that all
    surrounding content has been recovered or that its missing siblings are safe.
    """
    pos = 0
    while pos < len(t):
        match = re.search(r'[\[{]', t[pos:])
        if not match:
            return
        start = pos + match.start()
        try:
            v, end = DECODER.raw_decode(t, start)
        except ValueError:
            pos = start + 1
            continue
        if isinstance(v, (dict, list)):
            yield v, start, end
        pos = end


def walk_records(v, pointer=''):
    if isinstance(v, dict):
        ids = named(v)
        if ids:
            body_keys = [k for k in BODY_KEYS if v.get(k) and not is_path_pointer(v[k])]
            # A top-level `text` with an explicit source id is an observed source
            # request/chunk; metadata-only message ids and file pin rows are not.
            if body_keys:
                yield 'source_body', ids, pointer, body_keys, v
            elif any(v.get(k) and is_path_pointer(v[k]) for k in BODY_KEYS):
                yield 'source_record_path_pointer_availability_not_body', ids, pointer, [], v
            elif DERIVED_KEYS.intersection(v) or ('name' in v and 'category' in v and 'source_ids' in v):
                yield 'derived_resource_source_metadata', ids, pointer, [], v
            elif 'source_ids' in v or 'selected_source_ids' in v:
                yield 'observed_explicit_source_metadata', ids, pointer, [], v
        for k, child in v.items():
            if isinstance(child, (dict, list)):
                yield from walk_records(child, pointer + '/' + str(k))
    elif isinstance(v, list):
        for i, child in enumerate(v):
            yield from walk_records(child, pointer + '/' + str(i))


def is_path_pointer(v):
    if isinstance(v, str):
        return bool(re.fullmatch(r'/workspace/[^\s]+\.(?:json|jsonl|txt|md)', v.strip()))
    if isinstance(v, list) and v:
        return all(is_path_pointer(x) for x in v)
    return False


def process_episode(ep, old, formal, evolution):
    eid = ep['episode_id']
    observations = []
    accesses = []
    calls = {}
    body_ids = set()
    dependency_ids = set()
    requested_read_ids = set()
    raw_protected_refs = []
    unparsed_refs = []
    # Command strings are not exported: the metadata index retains the exact
    # original call/message hashes and path references, never enterprise bodies.
    for mi, m in enumerate(ep['messages']):
        c = m.get('content')
        if m.get('role') == 'assistant' and isinstance(c, list):
            for bi, block in enumerate(c):
                if not isinstance(block, dict) or block.get('type') != 'toolCall':
                    continue
                args = block.get('arguments') or {}
                at = js(args)
                tool = block.get('name')
                paths = sorted(set(PATH.findall(at)))
                input_paths = [p for p in paths if p.startswith('/workspace/inputs/')]
                # read tools or actual shell reads are source-access evidence;
                # generated output writes with an input fixture in the text are not.
                command = str(args.get('command', args.get('cmd', ''))) if isinstance(args, dict) else ''
                readlike = tool in {'read', 'read_file', 'search', 'grep'} or (
                    tool == 'exec' and bool(re.search(r'\b(cat|head|tail|sed|grep|rg|open|read_text|read_bytes|json\.load|find|ls|wc)\b', command)))
                source_paths = [p for p in input_paths if SID.search(p)] if readlike else []
                call = {'message_index': mi, 'content_block_index': bi, 'tool_name': tool,
                        'tool_call_id': block.get('id'), 'arguments_sha256': sha_bytes(at.encode()),
                        'input_paths': input_paths, 'source_path_ids': sorted(set(SID.findall(js(source_paths)))),
                        'source_read_or_listing_heuristic': readlike,
                        'command_body_exported': False, 'result_message_indices': []}
                calls[block.get('id')] = call
                accesses.append(call)
        if m.get('role') not in {'user', 'tool', 'toolResult'}:
            continue
        call_id = m.get('toolCallId', m.get('tool_call_id'))
        call = calls.get(call_id)
        if call is not None:
            call['result_message_indices'].append(mi)
            # Explicitly named source paths in an executed read are a dependency
            # guard; listing alone is not called proof of plaintext visibility.
            if call['source_read_or_listing_heuristic']:
                requested_read_ids.update(call['source_path_ids'])
        for bi, t in texts(m):
            if 'conv_' not in t:
                continue
            raw_ids = set(SID.findall(t))
            ranges = []
            for value, start, end in decoded_values(t):
                ranges.append((start, end))
                for kind, ids, pointer, body_keys, record in walk_records(value):
                    if kind == 'source_body':
                        body_ids.update(ids)
                    elif kind != 'source_record_path_pointer_availability_not_body':
                        dependency_ids.update(ids)
                    observations.append({
                        'kind': kind, 'native_message_index': mi, 'content_block_index': bi,
                        'message_role': m.get('role'), 'json_text_character_range': [start, end],
                        'json_pointer_within_value': pointer, 'source_ids': sorted(ids),
                        'protected_source_ids': sorted(ids & formal), 'body_schema_keys': body_keys,
                        'native_message_sha256': sha_bytes(js(m).encode()),
                        'observed_record_sha256': sha_bytes(js(record).encode()),
                        'observed_record_serialization': 'sorted_key_compact_utf8_json',
                        'source_fixture_pin': record.get('source_fixture_pin'),
                        'source_record_sha256': record.get('source_record_sha256'),
                        'body_exported': False})
            if raw_ids & formal:
                raw_protected_refs.append({'native_message_index': mi, 'content_block_index': bi,
                    'source_ids': sorted(raw_ids & formal), 'native_message_sha256': sha_bytes(js(m).encode())})
                # A complete decoded substring does not explain unrelated text
                # around it.  Protected identifiers outside decoded values remain
                # unresolved; reference-only instructions are recorded separately.
                residue = t
                for start, end in reversed(ranges):
                    residue = residue[:start] + (' ' * (end - start)) + residue[end:]
                residual = set(SID.findall(residue)) & formal
                if residual:
                    unparsed_refs.append({'native_message_index': mi, 'content_block_index': bi,
                        'source_ids': sorted(residual), 'role': m.get('role'),
                        'native_message_sha256': sha_bytes(js(m).encode()),
                        'body_visibility_not_proven_by_identifier_alone': True})
    body_formal = body_ids & formal
    dep_formal = dependency_ids & formal
    path_formal = requested_read_ids & formal
    known_formal = set(old['direct_formal_source_ids'])
    unindexed = (body_ids | dependency_ids | requested_read_ids) - set(evolution)
    if known_formal or body_formal:
        status = 'HOLD_PROTECTED_ORIGINAL_SOURCE_BODY_OR_PRIOR_EXPLICIT_DEPENDENCY'
    elif dep_formal or path_formal:
        status = 'HOLD_ACTUALLY_OBSERVED_RESOURCE_METADATA_OR_EXPLICIT_READ_DEPENDENCY_REQUIRES_LINEAGE'
    elif unparsed_refs:
        status = 'HOLD_PROTECTED_IDENTIFIER_IN_UNPARSED_OR_UNSTRUCTURED_OBSERVATION'
    elif body_ids and not unindexed:
        status = 'EVOLUTION_ONLY_OBSERVED_SOURCE_BODIES_TRANSITIVE_LINEAGE_NOT_PROVEN'
    elif body_ids:
        status = 'HOLD_SOURCE_BODY_IDS_NOT_IN_CURRENT_EVOLUTION_INDEX'
    else:
        status = 'HOLD_NO_POSITIVE_INDEPENDENT_SOURCE_BODY_PROOF'
    return {
        'episode_id': eid, 'kind': ep['kind'], 'prior_scope_label': old['scope_label'],
        'review_status': status, 'native_verified': ep.get('native_verified'),
        'context_fully_recoverable': ep.get('context_fully_recoverable'),
        'canonical_episode_sha256': sha_bytes(js(ep).encode()),
        'canonical_episode_serialization': 'sorted_key_compact_utf8_json',
        'native_message_range': [0, len(ep['messages'])],
        'message_count': len(ep['messages']), 'observed_source_body_ids': sorted(body_ids),
        'observed_protected_source_body_ids': sorted(body_formal),
        'actually_observed_resource_source_metadata_ids': sorted(dependency_ids),
        'actually_observed_protected_resource_source_metadata_ids': sorted(dep_formal),
        'explicit_input_source_path_read_or_listing_ids': sorted(requested_read_ids),
        'protected_input_source_path_read_or_listing_ids': sorted(path_formal),
        'observed_ids_not_in_current_evolution_index': sorted(unindexed),
        'source_record_provenance': [{'source_id': sid,
            'original_source_record_sha256': evolution[sid].get('source_record_sha256'),
            'original_source_file': evolution[sid].get('source_file'),
            'original_source_physical_line': evolution[sid].get('physical_line'),
            'original226': sid in formal} for sid in sorted(body_ids | dependency_ids | requested_read_ids) if sid in evolution],
        'observations': observations, 'actual_access_index': accesses,
        'protected_identifier_message_index': raw_protected_refs,
        'unparsed_or_unstructured_protected_identifier_index': unparsed_refs,
        'training_admitted': False, 'complete_transitive_resource_isolation_proven': False,
        'scope_review_is_not_semantic_gold': True, 'body_exported': False}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    controlled = OUT / 'controlled'
    controlled.mkdir(exist_ok=True)
    contracts = [p for p in (ROOT / 'benchmark').glob('*/contracts/evaluation.jsonl')
        if p.parent.parent.name in {'enterprise_split_v9_20261010', 'enterprise_input_closed_v11_20261012',
                                    'enterprise_original_inputs_v10_20261011', 'enterprise_final_delivery_v8_20261010'}]
    formal_contract_rows = [(p, r) for p in contracts for r in rows(p)]
    formal = {r['session_id'] for p, r in formal_contract_rows}
    formal_provenance = defaultdict(list)
    for p, r in formal_contract_rows:
        src = r.get('source') or {}
        formal_provenance[r['session_id']].append({
            'contract_path': str(p.relative_to(ROOT)), 'contract_sha256': sha_file(p),
            'original_session_sha256': src.get('session_sha256'),
            'original_audit_copy_sha256': src.get('audit_copy_sha256'),
            'original_source_file_sha256': src.get('file_sha256')})
    evo_path = ROOT / 'output/20261013_eval250_review/release/learning/evolution_index.jsonl'
    evolution = {r['source_id']: r for r in rows(evo_path) if r.get('logical_role') == 'evolution'}
    labels_path = BASE / 'controlled/native_source_split.labels.jsonl.gz'
    labels = {r['episode_id']: r for r in rows(labels_path)}
    canonical = BUNDLE / 'canonical/native_episodes.jsonl.gz'
    reviewed = {r['episode_id']: process_episode(r, labels[r['episode_id']], formal, evolution) for r in rows(canonical)}
    catalog_episodes = BUNDLE / 'catalog/episodes.jsonl'
    catalog_jobs = BUNDLE / 'catalog/jobs.jsonl'
    jobs = {r['id']: r for r in rows(catalog_jobs)}
    for line, catalog in enumerate(rows(catalog_episodes), 1):
        if catalog['episode_id'] not in reviewed:
            continue
        r = reviewed[catalog['episode_id']]
        r['catalog_episode_row'] = line
        r['catalog_episode_sha256'] = sha_bytes(js(catalog).encode())
        r['catalog_reference_is_not_actual_model_observation'] = True
        r['catalog_job_provenance'] = [{'job_id': jid, 'catalog_job_sha256': sha_bytes(js(jobs[jid]).encode())}
            for jid in sorted({catalog.get('job_id'), *(catalog.get('job_refs') or [])} - {None}) if jid in jobs]
    artifacts_path = ROOT / 'output/20261025_wrd_fullchain_reaudit/controlled_linkage/input_artifacts.jsonl.gz'
    artifact_matches = 0
    for a in rows(artifacts_path):
        if a['episode_id'] not in reviewed:
            continue
        r = reviewed[a['episode_id']]
        matches = defaultdict(list)
        for kind, ids, pointer, body_keys, record in walk_records(a.get('content')):
            matches[sha_bytes(js(record).encode())].append(pointer)
        for obs in r['observations']:
            if obs['observed_record_sha256'] in matches:
                obs.setdefault('matching_contemporaneous_input_artifacts', []).append({
                    'artifact_name': a['artifact_name'], 'logical_path': a['logical_path'],
                    'artifact_sha256': a['sha256'],
                    'json_pointers_within_artifact': matches[obs['observed_record_sha256']],
                    'match_kind': 'exact_sorted_compact_json_record_sha256',
                    'artifact_availability_alone_not_called_model_visibility': True})
                artifact_matches += 1
    source_index = controlled / 'native_visibility_evidence.jsonl.gz'
    with gzip.open(source_index, 'wt', encoding='utf-8', newline='\n') as f:
        for eid in sorted(reviewed):
            f.write(js(reviewed[eid]) + '\n')
    pending = [r for r in reviewed.values() if r['prior_scope_label'] in {
        'available_protected_pool_only_requires_visibility_review', 'ambiguous_catalog_reference_or_unmapped_source'}]
    by_stage = defaultdict(Counter)
    for r in pending:
        by_stage[r['kind']][r['review_status']] += 1
    decisions_path = ROOT / 'output/20261025_wrd_fullchain_reaudit/controlled_linkage/structured_decisions.jsonl.gz'
    decision_index = controlled / 'structured_decision_visibility_evidence.jsonl.gz'
    decision_counts = Counter()
    decision_by_unit = defaultdict(Counter)
    with gzip.open(decision_index, 'wt', encoding='utf-8', newline='\n') as f:
        for d in rows(decisions_path):
            episode_ids = list(dict.fromkeys([*(d.get('episode_ids') or []), *([d['original_episode_id']] if d.get('original_episode_id') else [])]))
            parents = [reviewed[e] for e in episode_ids if e in reviewed]
            all_pure = bool(parents) and len(parents) == len(episode_ids) and all(
                p['review_status'] == 'EVOLUTION_ONLY_OBSERVED_SOURCE_BODIES_TRANSITIVE_LINEAGE_NOT_PROVEN' for p in parents)
            label_ids = sorted(set(SID.findall(js(d.get('label')))))
            if any(p['review_status'].startswith('HOLD_PROTECTED_ORIGINAL') for p in parents):
                status = 'HOLD_PARENT_OBSERVED_OR_EXPLICIT_PROTECTED_SOURCE'
            elif any(p['review_status'].startswith('HOLD_') for p in parents) or len(parents) != len(episode_ids):
                status = 'HOLD_PARENT_RESOURCE_OR_VISIBILITY_OR_SOURCE_SCOPE_UNRESOLVED'
            elif set(label_ids) & formal:
                status = 'HOLD_DECISION_LABEL_REFERENCES_PROTECTED_SOURCE'
            elif all_pure:
                status = 'CANDIDATE_ORIGINAL_DECISION_OBSERVED_EVOLUTION_ONLY_CONTEXT_LINEAGE_STILL_PENDING'
            else:
                status = 'HOLD_INDEPENDENT_PARENT_CONTEXT_NOT_PROVEN'
            out = {k: d.get(k) for k in ('id', 'unit', 'episode_ids', 'original_episode_id', 'artifact_sha256', 'logical_path', 'json_pointer', 'evidence_type')}
            out.update({'decision_label_sha256': sha_bytes(js(d.get('label')).encode()),
                'label_source_ids': label_ids, 'review_status': status,
                'parent_visibility_status': {p['episode_id']: p['review_status'] for p in parents},
                'parent_native_message_ranges': {p['episode_id']: p['native_message_range'] for p in parents},
                'training_admitted': False, 'body_exported': False,
                'isolating_label_does_not_remove_parent_context': True,
                'future_artifact_added_to_past_prompt': False})
            decision_counts[status] += 1
            decision_by_unit[d['unit']][status] += 1
            f.write(js(out) + '\n')
    eligible = [r for r in pending if r['review_status'] == 'EVOLUTION_ONLY_OBSERVED_SOURCE_BODIES_TRANSITIVE_LINEAGE_NOT_PROVEN']
    eligible_ids = {r['episode_id'] for r in eligible}
    existing_strict_rechecks = [r for r in reviewed.values() if r['prior_scope_label'] == 'confirmed_evolution_direct_source_scope'
                               and r['review_status'].startswith('HOLD_')]
    existing_strict_conflicts = [r for r in reviewed.values() if r['prior_scope_label'] == 'confirmed_evolution_direct_source_scope'
                                and r['observed_protected_source_body_ids']]
    conflict_ids = {r['episode_id'] for r in existing_strict_conflicts}
    recheck_ids = {r['episode_id'] for r in existing_strict_rechecks}
    curated_impact = Counter()
    body_conflict_impact = Counter()
    candidate_impact = Counter()
    for name in ('controlled.core32k.jsonl.gz', 'controlled.actor_aux32k.jsonl.gz',
                 'public.core32k.jsonl.gz', 'public.actor_aux32k.jsonl.gz'):
        for r in rows(BASE / 'curated_native' / name):
            e = reviewed[r['episode_id']]
            if e['episode_id'] in eligible_ids:
                candidate_impact[name + ':' + r['kind'] + ':windows'] += 1
                candidate_impact[name + ':' + r['kind'] + ':supervised_tokens'] += r['supervised_tokens']
            if e['episode_id'] in conflict_ids:
                body_conflict_impact[name + ':windows'] += 1
                body_conflict_impact[name + ':targets'] += sum(bool(t['owned_supervision_spans']) for t in r['targets'])
                body_conflict_impact[name + ':supervised_tokens'] += r['supervised_tokens']
                body_conflict_impact[name + ':total_tokens'] += r['total_tokens']
            if e['episode_id'] not in recheck_ids:
                continue
            curated_impact[name + ':windows'] += 1
            curated_impact[name + ':targets'] += sum(bool(t['owned_supervision_spans']) for t in r['targets'])
            curated_impact[name + ':supervised_tokens'] += r['supervised_tokens']
            curated_impact[name + ':' + e['review_status'] + ':windows'] += 1
    override_items = []
    for r in existing_strict_conflicts:
        positive = [o for o in r['observations'] if o['kind'] == 'source_body' and o['protected_source_ids']]
        override_items.append({'episode_id': r['episode_id'], 'kind': r['kind'],
            'prior_scope_label': r['prior_scope_label'],
            'effective_scope_label': 'known_original226_source_body_observed_v5',
            'mandatory_whole_episode_hold_for_existing_strict_profile': True,
            'first_actual_protected_body_native_message_index': min(o['native_message_index'] for o in positive),
            'canonical_episode_sha256': r['canonical_episode_sha256'],
            'original226_source_ids': r['observed_protected_source_body_ids'],
            'original226_contract_provenance': {s: formal_provenance[s] for s in r['observed_protected_source_body_ids']},
            'evolution_record_provenance': [p for p in r['source_record_provenance'] if p['original226']],
            'positive_body_observation_evidence': positive,
            'actual_access_index_for_positive_observations': [a for a in r['actual_access_index'] if any(
                o['native_message_index'] in a['result_message_indices'] for o in positive)],
            'do_not_automatically_admit_pre_exposure_prefixes': True,
            'body_exported': False, 'training_admitted': False})
    override = {'schema_version': 'wrd-strict226-visibility-positive-overrides-v5',
        'status': 'POSITIVE_BODY_PROOF_ONLY_NOT_ALL_UNRESOLVED_ROWS',
        'original226_policy_overridden': False, 'items': override_items,
        'existing_strict_body_conflict_impact': dict(body_conflict_impact),
        'manual_path_pointer_retraction': {'episode_id': 'ep_761f5c4f1786ff744bd9',
            'message_index': 8, 'finding': 'user_input is a source-file path pointer, not original request body',
            'protected_body_proof_found_by_this_review': False,
            'metadata_or_lineage_scope_is_not_automatically_cleared': True},
        'no_absence_of_match_whitelist': True, 'training_started': False, 'new_model_calls': 0}
    override_path = OUT / 'STRICT_SOURCE_VISIBILITY_OVERRIDES.json'
    override_path.write_text(json.dumps(override, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    inputs = [canonical, labels_path, decisions_path, evo_path, artifacts_path, catalog_episodes, catalog_jobs, *contracts]
    report = {
        'schema_version': 'wrd-strict226-native-visibility-review-v5',
        'status': 'OFFLINE_EVIDENCE_REVIEW_NO_AUTOMATIC_TRAINING_ADMISSION',
        'protected_original_source_ids': len(formal), 'all_canonical_episodes_scanned': len(reviewed),
        'requested_pending_episodes_reviewed': len(pending),
        'pending_prior_scope_counts': dict(Counter(r['prior_scope_label'] for r in pending)),
        'pending_review_counts': dict(Counter(r['review_status'] for r in pending)),
        'pending_by_stage': {k: dict(v) for k, v in by_stage.items()},
        'pending_positive_evolution_observed_context_candidates': len(eligible),
        'pending_positive_candidates_by_stage': dict(Counter(r['kind'] for r in eligible)),
        'pending_positive_candidates_native_verified_by_stage': dict(Counter(r['kind'] for r in eligible if r['native_verified'])),
        'pending_positive_context_candidates_in_curated_views_not_admitted': dict(candidate_impact),
        'pending_positive_candidate_episode_ids': sorted(r['episode_id'] for r in eligible),
        'contemporaneous_artifact_exact_record_matches_in_actual_observations': artifact_matches,
        'existing_confirmed_direct_scope_review_counts': dict(Counter(r['review_status'] for r in reviewed.values()
            if r['prior_scope_label'] == 'confirmed_evolution_direct_source_scope')),
        'existing_confirmed_direct_scope_positive_protected_body_conflict_episodes': len(existing_strict_conflicts),
        'existing_confirmed_direct_scope_positive_body_conflicts_by_stage': dict(Counter(r['kind'] for r in existing_strict_conflicts)),
        'existing_strict_positive_body_conflict_impact': dict(body_conflict_impact),
        'other_guard_or_missing_positive_body_evidence_is_not_proven_contamination': True,
        'curated_windows_requiring_different_kinds_of_evidence_review_not_all_contamination': dict(curated_impact),
        'structured_decision_counts': dict(decision_counts),
        'structured_decision_by_unit': {k: dict(v) for k, v in decision_by_unit.items()},
        'actual_safe_new_training_admissions': 0,
        'complete_transitive_resource_dependency_isolation_proven_for_new_candidates': False,
        'findings': [
            'Original screen inputs include sources[].requests[].text. These are visible original request bodies, not metadata-only source identifiers.',
            'Actual exec cat may concatenate task_route.json and task_sources.json. Whole-message json.loads failure does not mean the model did not see those bodies.',
            'Complete inner source records in otherwise truncated/unstructured text are positive visibility evidence only; missing outer context remains unresolved.',
            'Actually observed route/source metadata and executed source-path reads require resource lineage review; dropping those parent observations cannot make a label independent.',
            'Evolution-only observed bodies are a candidate entrance, not proof that all derived resources or teacher context were independent of original226.',
            'Structured decisions inherit their complete original parent context. A source-local label is not admitted by slicing it from a mixed protected batch.'
        ],
        'path_pointer_first_pass_correction': {
            'initial_unfiltered_user_input_classifier_was_overinclusive': True,
            'user_input_that_is_only_a_source_file_path_is_availability_not_body': True,
            'initial_two_old_strict_body_conflicts_corrected_to_one': True,
            'retracted_episode_id': 'ep_761f5c4f1786ff744bd9',
            'retained_positive_episode_id': 'ep_2b53d347db76105816c8',
            'retained_positive_message_index': 16},
        'limitations': [
            'This bounded parser is not an exhaustive semantic source/body classifier.',
            'A source-id-free body, unresolved tool output, implicit derived resource, or teacher hidden state cannot be certified independent by absence of matches.',
            'Input source-path read/listing guards are dependency holds, not assertions that every file byte was exposed.',
            'The current evolution index includes historical reclassified original226; formal original contracts take precedence.',
            'Original observations, not future artifacts, were inspected. No summary or generated rationale was inserted into any historical prompt.'
        ],
        'source_sha256': {str(p.relative_to(ROOT)): sha_file(p) for p in inputs},
        'evidence_indexes': [{'path': str(p.relative_to(OUT)), 'sha256': sha_file(p), 'bytes': p.stat().st_size}
                             for p in (source_index, decision_index)],
        'positive_visibility_override': {'path': str(override_path.relative_to(OUT)), 'sha256': sha_file(override_path)},
        'script_sha256': sha_file(Path(__file__)), 'training_started': False, 'new_model_calls': 0,
        'new_business_or_native_agent_runs': 0, 'original_files_mutated': False,
        'publication_approval_created_by_this_review': False}
    (OUT / 'VISIBILITY_REVIEW.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('requested_pending_episodes_reviewed', 'pending_by_stage',
        'pending_positive_candidates_by_stage', 'existing_confirmed_direct_scope_positive_protected_body_conflict_episodes',
        'existing_strict_positive_body_conflict_impact',
        'structured_decision_counts')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
