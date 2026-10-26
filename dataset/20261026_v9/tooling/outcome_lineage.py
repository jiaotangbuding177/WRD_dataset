"""Offline version/trial/review joins and time-local source closure for WRD v9.

Original files, business results, native execution and old masks are read-only.
The exported outcomes are historical silver evidence, not independent Q gold.
"""
from __future__ import annotations

import collections
import ast
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / 'output/20261025_wrd_training_dataset/bundle'
V6 = ROOT / 'output/20261026_wrd_lineage_v6'
V7 = ROOT / 'output/20261026_wrd_raw_census_v7'
V8 = ROOT / 'output/20261026_wrd_quality_v8'
OUT = ROOT / 'output/20261026_wrd_dataset_v9/outcomes'
SID = re.compile(r'conv_[a-f0-9]{12}')
EXTRA_RESOURCE_OVERRIDES = {}


def rows(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path, 'rt', encoding='utf-8-sig') as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def js(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def jsha(value):
    return sha(js(value).encode())


def write_rows(name, values):
    OUT.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT / name, 'wt', encoding='utf-8', newline='\n') as handle:
        for value in values:
            handle.write(js(value) + '\n')


def tree_sha(files):
    return sha(js(sorted((k, v) for k, v in files.items())).encode())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = {e['episode_id']: e for e in rows(BUNDLE / 'catalog/episodes.jsonl')}
    jobs = {j['id']: j for j in rows(BUNDLE / 'catalog/jobs.jsonl')}
    routes = {r['id']: r for r in rows(BUNDLE / 'catalog/routes.jsonl')}
    native = {e['episode_id']: e for e in rows(BUNDLE / 'canonical/native_episodes.jsonl.gz')}
    legacy = {e['episode_id']: e for e in rows(V6 / 'controlled/lineage_episode_decisions.jsonl.gz')}
    visibility = {e['episode_id']: e for e in rows(V6 / 'frozen/native_visibility_evidence.jsonl.gz')}
    resource_nodes = list(rows(V6 / 'controlled/lineage_resources.jsonl.gz'))
    targets = list(rows(V8 / 'controlled/native_targets.quality.jsonl.gz'))
    v8_routes = {r['route_id']: r for r in rows(V8 / 'controlled/route_chains.quality.jsonl.gz')}
    feedbacks = list(rows(V8 / 'controlled/feedback_projection_links.quality.jsonl.gz'))
    formal_sets = []
    for p in sorted((ROOT / 'benchmark').glob('*/contracts/evaluation.jsonl')):
        ids = {r.get('session_id') for r in rows(p)} - {None}
        if len(ids) == 226:
            formal_sets.append((p, ids))
    assert formal_sets and all(x[1] == formal_sets[0][1] for x in formal_sets)
    original226 = formal_sets[0][1]
    holdout_path = ROOT / 'output/20261026_ablation_v2/holdout_registry.json'
    holdout_registry = json.loads(holdout_path.read_text(encoding='utf-8-sig'))
    holdout12 = set(SID.findall(js(holdout_registry)))
    protected = original226 | holdout12

    wanted = {'request.json', 'workspace/inputs/review_input.json', 'workspace/outputs/review.json',
              'workspace/outputs/making.json', 'workspace/outputs/tasks.json',
              'workspace/outputs/development_tasks.json', 'workspace/inputs/route.json',
              'workspace/inputs/task_route.json', 'workspace/inputs/previous_feedback.json'}
    files = {}
    candidate_files = collections.defaultdict(dict)
    output_file_index = {}
    for f in rows(BUNDLE / 'archive/file_index.jsonl'):
        bits = f['logical_path'].split('/', 2)
        if len(bits) == 3 and bits[0] == 'episodes' and bits[2] in wanted:
            files[(bits[1], bits[2])] = f
        if len(bits) == 3 and bits[0] == 'episodes' and bits[2].startswith('workspace/inputs/candidate/'):
            candidate_files[bits[1]][bits[2][len('workspace/inputs/candidate/'):]] = f.get('source_sha256') or f['sha256']
        if len(bits) == 3 and bits[0] == 'episodes' and bits[2].startswith('workspace/outputs/'):
            output_file_index[(bits[1], bits[2])] = f

    def read(eid, rel):
        f = files.get((eid, rel))
        if not f:
            return None, None
        p = BUNDLE / 'archive' / f['object']
        data = p.read_bytes()
        assert sha(data) == f['sha256']
        ref = {'logical_path': f['logical_path'], 'sha256': f['sha256'],
               'cas_path': str(p), 'source_path': f.get('source_path'), 'bytes': len(data)}
        try:
            return json.loads(data.decode('utf-8-sig')), ref
        except (UnicodeError, ValueError):
            return None, ref

    requests = {}
    request_refs = {}
    for eid in catalog:
        value, ref = read(eid, 'request.json')
        if isinstance(value, dict):
            requests[eid], request_refs[eid] = value, ref
    normalized_route = {}
    for eid, e in catalog.items():
        rid = e.get('route_id')
        if rid not in routes:
            req = requests.get(eid, {})
            tid = str(req.get('task_id') or '')
            matches = [r for r in routes if re.fullmatch(re.escape(r) + r'(?:_devprep|_c\d+_(?:no_skill|workflow|blindjudge)|__make\d+)', tid)]
            if len(matches) == 1:
                rid = matches[0]
        normalized_route[eid] = rid
    source_dir_eid = {str(e['source_path']).replace('\\', '/').casefold(): eid for eid, e in catalog.items()}

    # Byte-identical complete package identities, not route names or final status.
    versions = list(rows(V7 / 'indexes/skill_version_trees.all.jsonl.gz'))
    producers = [v for v in versions if v['output_skill_root_logical_path'].startswith('episodes/' + v['episode_id'] + '/workspace/outputs/')]
    by_tree = collections.defaultdict(list)
    by_episode_version = collections.defaultdict(list)
    for v in producers:
        by_tree[v['tree_content_sha256']].append(v)
        by_episode_version[v['episode_id']].append(v)
    consumed = collections.defaultdict(list)
    candidate_trees = collections.defaultdict(list)
    for eid, req in requests.items():
        for item in req.get('learned_skills') or []:
            if not isinstance(item, dict) or not isinstance(item.get('files'), dict):
                continue
            hashes = item['files']
            if not all(isinstance(k, str) and isinstance(v, str) and re.fullmatch('[a-f0-9]{64}', v) for k, v in hashes.items()):
                continue
            identity = tree_sha(hashes)
            consumed[eid].append({'tree_content_sha256': identity, 'skill_id': item.get('id'),
                'request_ref': request_refs[eid], 'file_sha256': hashes,
                'version_identity_proof': 'original_request_learned_skills_complete_file_map',
                'matching_producer_episode_ids': sorted({p['episode_id'] for p in by_tree[identity]}),
                'producer_author_identity_unique': len({p['episode_id'] for p in by_tree[identity]}) == 1})
    for eid, hashes in candidate_files.items():
        if 'SKILL.md' in hashes:
            candidate_trees[eid].append({'tree_content_sha256': tree_sha(hashes), 'files': hashes,
                'version_identity_proof': 'all_original_frozen_review_candidate_input_file_SHA_map'})

    # Confirm SKILL.md actually reached the Actor; request availability is weaker.
    actual_skill_read = {}
    for eid, items in consumed.items():
        ep = native.get(eid)
        if not ep:
            continue
        msgs = ep['messages']
        results = {m.get('toolCallId'): (i, m) for i, m in enumerate(msgs) if m.get('role') == 'toolResult'}
        for item in items:
            expected = item['file_sha256'].get('SKILL.md')
            hits = []
            for i, m in enumerate(msgs):
                if m.get('role') != 'assistant':
                    continue
                for call in m.get('content') or []:
                    if not isinstance(call, dict) or call.get('type') != 'toolCall':
                        continue
                    args = call.get('arguments') or {}
                    if not isinstance(args, dict) or 'SKILL.md' not in js(args):
                        continue
                    result = results.get(call.get('id'))
                    if not result:
                        continue
                    ri, rm = result
                    chunks = [b.get('text', '') for b in rm.get('content') or [] if isinstance(b, dict) and b.get('type') == 'text']
                    for text in chunks:
                        if expected and sha(text.encode()) == expected:
                            hits.append({'assistant_message_index': i, 'result_message_index': ri,
                                'tool_call_id': call.get('id'), 'delivery_proof': 'full_result_text_byte_SHA_equals_original_SKILL_md'})
                        else:
                            for prod in by_tree[item['tree_content_sha256']]:
                                sf = next((f for f in prod['files'] if f['relative_path'] == 'SKILL.md'), None)
                                if sf:
                                    original = Path(sf['physical_frozen_CAS_path']).read_text(encoding='utf-8-sig')
                                    if original and original.replace('\r\n', '\n') in text.replace('\r\n', '\n'):
                                        hits.append({'assistant_message_index': i, 'result_message_index': ri,
                                            'tool_call_id': call.get('id'), 'delivery_proof': 'full_original_SKILL_md_span_in_result_newline_normalized'})
                                        break
            item['actual_full_SKILL_delivery'] = hits
            actual_skill_read[(eid, item['tree_content_sha256'])] = hits

    reviews = {}
    review_inputs = {}
    for eid in catalog:
        value, ref = read(eid, 'workspace/outputs/review.json')
        if isinstance(value, dict):
            reviews[eid] = (value, ref)
        value, ref = read(eid, 'workspace/inputs/review_input.json')
        if isinstance(value, dict):
            review_inputs[eid] = (value, ref)
    trial_edges = []
    reviews_by_actor = collections.defaultdict(list)
    review_evidence_checks = {}
    for reviewer, (value, ref) in reviews.items():
        original_input, input_ref = review_inputs.get(reviewer, ({}, None))
        findings = {str(c.get('case_id')): c for c in value.get('case_findings') or [] if isinstance(c, dict)}
        for item in original_input.get('cases') or []:
            if not isinstance(item, dict):
                continue
            case = item.get('case') or {}
            cid = str(case.get('id') or '')
            arms = item.get('arms') or {}
            per_arm = {}
            for arm, record in arms.items():
                if not isinstance(record, dict):
                    continue
                details = record.get('all_attempts') or {}
                paths = list(details.get('episodes') or [])
                paths += [d.get('episode') for d in details.get('attempt_details') or [] if isinstance(d, dict) and d.get('episode')]
                eids = sorted({source_dir_eid.get(str(p).replace('\\', '/').casefold()) for p in paths} - {None})
                per_arm[arm] = {'episode_ids': eids, 'tokens': record.get('tokens'), 'calls': record.get('calls'),
                    'delivery_status_is_not_quality': record.get('delivery_status'),
                    'all_attempts_cost_record': details, 'read_observation': record.get('read_observation')}
            for actor in per_arm.get('workflow', {}).get('episode_ids', []):
                candidate_ids = {x['tree_content_sha256'] for x in candidate_trees.get(reviewer, [])}
                for skill in consumed.get(actor, []):
                    identity = skill['tree_content_sha256']
                    cf = findings.get(cid)
                    review_matches_version = identity in candidate_ids
                    # Missing or ambiguous case findings stay unknown, even if retain.
                    delivery = str((cf or {}).get('delivery') or '').lower()
                    exact_case_pass = delivery in {'pass', 'passed', 'true'}
                    trial = {'reviewer_episode_id': reviewer, 'route_id': normalized_route.get(reviewer),
                        'actor_episode_id': actor, 'case_id': cid, 'source_id': case.get('source_id'),
                        'tree_content_sha256': identity, 'producer_episode_ids': skill['matching_producer_episode_ids'],
                        'candidate_tree_matches_consumed_complete_tree': review_matches_version,
                        'actual_full_SKILL_delivery': actual_skill_read.get((actor, identity), []),
                        'arms': per_arm, 'case_finding': cf, 'review_ref': ref, 'review_input_ref': input_ref,
                        'historical_review': {k: value.get(k) for k in ['decision', 'reason', 'resource_reliable', 'delivery_passed', 'resource_used', 'replaced_work', 'repair_notes']},
                        'cost_facts': {k: original_input.get(k) for k in ['totals', 'cost_reduced', 'completed_pair_reduced', 'complete_cost_pairs']},
                        'evidence_level': 'historical_paired_trial_plus_model_review_silver_not_independent_Q',
                        'version_trial_task_positive_silver': bool(review_matches_version and exact_case_pass and actual_skill_read.get((actor, identity))),
                        'all_original_steps_correct': False, 'training_admitted': False}
                    trial['edge_id'] = jsha({k: trial[k] for k in ['reviewer_episode_id', 'actor_episode_id', 'case_id', 'tree_content_sha256']})
                    trial_edges.append(trial)
                    reviews_by_actor[actor].append(trial)

        totals = original_input.get('totals') or {}
        known = original_input.get('known_totals') or {}
        valid_pairs = isinstance(totals, dict) and all(isinstance(totals.get(a), list) and len(totals[a]) == 2 for a in ['workflow', 'no_skill'])
        numeric = valid_pairs and all(isinstance(n, (int, float)) and not isinstance(n, bool) for a in ['workflow', 'no_skill'] for n in totals[a])
        calculated_reduced = bool(numeric and all(totals['workflow'][i] < totals['no_skill'][i] for i in (0, 1)))
        recorded_cost_consistent = numeric and original_input.get('cost_reduced') == calculated_reduced
        input_case_ids = {str((c.get('case') or {}).get('id') or '') for c in original_input.get('cases') or [] if isinstance(c, dict)}
        complete_findings = bool(input_case_ids) and input_case_ids <= set(findings)
        findings_passing = complete_findings and all(str(findings[c].get('delivery')).lower() in {'pass', 'passed', 'true'} for c in input_case_ids)
        bound = [e for e in trial_edges if e['reviewer_episode_id'] == reviewer]
        tested_version_all = bool(bound) and all(e['candidate_tree_matches_consumed_complete_tree'] and e['actual_full_SKILL_delivery'] for e in bound)
        decision = value.get('decision')
        retain_rule = decision == 'retain' and calculated_reduced and original_input.get('complete_cost_pairs') is True and findings_passing and value.get('resource_reliable') is True and value.get('resource_used') is True
        revise_rule = decision == 'revise' and recorded_cost_consistent and not calculated_reduced and bool(value.get('repair_notes')) and complete_findings
        reject_rule = decision == 'reject' and recorded_cost_consistent and not calculated_reduced and complete_findings and bool(value.get('reason'))
        # This certifies a historical, evidence-linked review-policy example;
        # it does not independently certify the legal/domain claims in its prose.
        evidence_candidate = bool(recorded_cost_consistent and tested_version_all and (retain_rule or revise_rule or reject_rule))
        review_evidence_checks[reviewer] = {'review_episode_id': reviewer, 'decision': decision,
            'input_totals': totals, 'input_known_totals': known,
            'calculated_both_token_and_calls_reduced': calculated_reduced if numeric else None,
            'cost_arithmetic_and_flag_consistent': bool(recorded_cost_consistent),
            'all_selected_cases_have_findings': complete_findings,
            'all_selected_cases_report_delivery_pass_silver': findings_passing,
            'all_bound_workflow_versions_exact_and_full_SKILL_observed': tested_version_all,
            'policy_consistency_rule': 'retain_with_paired_delivery_and_both_costs_reduced' if retain_rule else 'revise_specific_notes_after_nonreduced_cost' if revise_rule else 'reject_after_nonreduced_cost' if reject_rule else None,
            'evidence_review_silver_candidate': evidence_candidate,
            'trial_edge_ids': [e['edge_id'] for e in bound],
            'review_ref': ref, 'review_input_ref': input_ref,
            'independent_domain_Q_certified': False,
            'unverified_review_prose_should_not_be_called_gold': True}

    # Actual-observation events. Merely available input paths do not expose body.
    events = collections.defaultdict(list)
    bind_sources = collections.defaultdict(set)
    resource_by_id = {n['node_id']: n for n in resource_nodes}
    formal_role = set()
    for eid, ep in native.items():
        job = jobs.get(ep.get('job_id')) or {}
        case = (job.get('payload') or {}).get('case') or {}
        if legacy.get(eid, {}).get('initial_case_source_binding_proof'):
            if isinstance(case.get('source_id'), str):
                bind_sources[eid].add(case['source_id'])
        vis = visibility[eid]
        for o in vis.get('observations') or []:
            if o.get('kind') == 'source_record_path_pointer_availability_not_body':
                continue
            ids = set(o.get('source_ids') or [])
            if ids:
                events[eid].append({'at': o['native_message_index'], 'kind': 'observed_source_record',
                    'sources': sorted(ids), 'evidence': {'visibility_kind': o.get('kind'),
                    'message_index': o['native_message_index'], 'record_sha256': o.get('observed_record_sha256')}})
        for o in vis.get('unparsed_or_unstructured_protected_identifier_index') or []:
            if o.get('role') != 'user':
                events[eid].append({'at': o['native_message_index'], 'kind': 'unknown',
                    'reason': 'UNSTRUCTURED_PROTECTED_ID_IN_ACTUAL_TOOL_OBSERVATION', 'evidence': o})
        if ep.get('role_scope') == 'formal_task_identity_exclude':
            formal_role.add(eid)
    for n in resource_nodes:
        eid = n['episode_id']
        if eid not in native:
            continue
        i = n['consumer_assistant_message_index']
        # Relate it to the actual result index; the read decision precedes it.
        accesses = [a for a in visibility[eid].get('actual_access_index') or [] if a.get('message_index') == i]
        result_indices = sorted({j for a in accesses for j in a.get('result_message_indices') or [] if j > i})
        at = result_indices[0] if result_indices else i + 1
        events[eid].append({'at': at, 'kind': 'resource', 'node_id': n['node_id']})
    for eid in events:
        events[eid].sort(key=lambda e: (e['at'], e['kind'], e.get('node_id', '')))

    scope_cache = {}
    resource_scope_cache = {}
    visiting = set()
    resource_recoveries = []

    def reference_only_control(value, path):
        # A native model seeing pointer/status metadata has not seen the pointed
        # business body. These finite schemas do not contain a free-text answer.
        if path.endswith('/previous.json') and isinstance(value, dict):
            keys = {'skill_root', 'feedback', 'feedback_input'}
            return bool(value) and set(value) <= keys and all(v is None or isinstance(v, str) and '\n' not in v and ('/' in v or '\\' in v) for v in value.values())
        if path.endswith('/prior_making.json') and isinstance(value, dict) and set(value) == {'attempts'} and isinstance(value['attempts'], list):
            allowed = {'job_id', 'episode', 'attempt', 'status', 'evidence_paths', 'making_record'}
            return all(isinstance(a, dict) and set(a) <= allowed and all(isinstance(v, (str, int)) or isinstance(v, list) and all(isinstance(p, str) for p in v) for v in a.values()) for a in value['attempts'])
        return False

    feedback_resource_links = {}
    for f in feedbacks:
        feedback_resource_links[(f['consumer_episode_id'], f['feedback_ref']['frozen_sha256'])] = f

    def resource_override(n):
        if n['node_id'] in EXTRA_RESOURCE_OVERRIDES:
            return EXTRA_RESOURCE_OVERRIDES[n['node_id']]
        rec = n.get('file_identity')
        if not rec:
            return None
        path = n['native_path']
        raw_path = BUNDLE / 'archive' / rec['object']
        raw = raw_path.read_bytes()
        if sha(raw) != rec['sha256']:
            return None
        try:
            value = json.loads(raw.decode('utf-8-sig'))
        except (UnicodeError, ValueError):
            value = None
        if reference_only_control(value, path):
            return {'kind': 'CLOSED_TYPED_REFERENCE_ONLY_OUTER_CONTROL', 'parents': [], 'metadata_exposes_no_pointed_body': True}
        f = feedback_resource_links.get((n['episode_id'], rec['sha256']))
        if f:
            parents = []
            for p in f['prior_review_matches']:
                link = p.get('exact_native_write')
                if link:
                    parents.append((p['episode_id'], link['assistant_message_index'] + 1))
            if parents and len(parents) == len(f['prior_review_matches']):
                return {'kind': 'EXACT_REVIEW_FIELD_PROJECTION_TO_OBSERVED_FEEDBACK', 'parents': parents, 'feedback_ref': f['feedback_ref']}
        match = re.fullmatch(r'/workspace/inputs/making/([a-f0-9]+)/(.+)', path)
        if match:
            possible = [eid for eid in native if eid.startswith('ep_' + match.group(1))]
            if len(possible) == 1:
                parent = possible[0]
                original = output_file_index.get((parent, match.group(2)))
                if original and (original.get('source_sha256') or original['sha256']) == (rec.get('source_sha256') or rec['sha256']):
                    return {'kind': 'EXACT_NATIVE_MAKING_BUNDLE_DISPATCH_COPY',
                        'parents': [(parent, len(native[parent]['messages']))],
                        'producer_original_output_ref': {k: original[k] for k in ['logical_path', 'sha256', 'object']},
                        'frozen_input_copy_sha256': rec['sha256']}
        return None

    def combine(parts, extra_sources=(), extra_unknown=()):
        sources, bad, unknown, refs = set(extra_sources), set(), set(extra_unknown), set()
        for p in parts:
            sources.update(p['source_ids']); bad.update(p['protected_source_ids'])
            unknown.update(p['unknown_reasons']); refs.update(p['evidence_refs'])
        bad.update(sources & protected)
        return {'source_ids': sorted(sources), 'protected_source_ids': sorted(bad),
            'unknown_reasons': sorted(unknown), 'evidence_refs': sorted(refs)}

    def resource_scope(node_id):
        if node_id in resource_scope_cache:
            return resource_scope_cache[node_id]
        n = resource_by_id[node_id]
        term = n['terminal'] or ''
        ids = set(n.get('source_ids') or [])
        parts, missing = [], []
        override = resource_override(n) if term.startswith('MISSING_') else None
        if override:
            ids.update(override.get('source_ids') or [])
            for parent, end in override['parents']:
                parts.append(prefix(parent, end))
            resource_recoveries.append({'node_id': node_id, 'episode_id': n['episode_id'],
                'native_path': n['native_path'], 'original_terminal': term, **override})
        elif term.startswith('CLOSED_'):
            pass
        elif term.startswith('PROTECTED_'):
            pass
        elif term == 'FOLLOW_EXACT_ORIGINAL_WRITE_PRODUCER':
            for p in n.get('proven_producer_prefixes') or []:
                parts.append(prefix(p['episode_id'], p['prefix_end_exclusive']))
        else:
            missing.append(term or 'UNCLASSIFIED_RESOURCE')
        result = combine(parts, ids, missing)
        result['evidence_refs'] = sorted(set(result['evidence_refs']) | {node_id})
        resource_scope_cache[node_id] = result
        return result

    def prefix(eid, end):
        key = (eid, end)
        if key in scope_cache:
            return scope_cache[key]
        if key in visiting:
            return combine([], extra_unknown=['CAUSAL_ANCESTRY_CYCLE'])
        visiting.add(key)
        parts = []
        for e in events.get(eid, []):
            if e['at'] >= end:
                break
            if e['kind'] == 'resource':
                parts.append(resource_scope(e['node_id']))
            elif e['kind'] == 'observed_source_record':
                parts.append(combine([], e['sources']))
            else:
                parts.append(combine([], extra_unknown=[e['reason']]))
        result = combine(parts, bind_sources[eid], ['FORMAL_EVALUATION_TASK_IDENTITY'] if eid in formal_role else [])
        result['scope_status'] = 'HOLD_PROTECTED' if result['protected_source_ids'] else 'HOLD_UNKNOWN' if result['unknown_reasons'] else 'CLEAN_OBSERVED_SOURCE_PREFIX' if result['source_ids'] else 'CLEAN_PROTOCOL_ONLY_PREFIX'
        result['eligible_scope'] = not result['protected_source_ids'] and not result['unknown_reasons']
        result['original226'] = sorted(set(result['protected_source_ids']) & original226)
        result['holdout12'] = sorted(set(result['protected_source_ids']) & holdout12)
        result['native_prefix_end_exclusive'] = end
        visiting.remove(key)
        scope_cache[key] = result
        return result

    # Version-scoped outcome evidence is attached to exact observed contribution
    # targets only. A successful package never approves all actions in its maker.
    version_edges = collections.defaultdict(list)
    for e in trial_edges:
        version_edges[e['tree_content_sha256']].append(e)
    produced_file_hashes = collections.defaultdict(lambda: collections.defaultdict(set))
    for v in producers:
        for f in v['files']:
            produced_file_hashes[v['episode_id']][f['sha256']].add(v['tree_content_sha256'])
    feedback_by_ep = collections.defaultdict(list)
    for f in feedbacks:
        feedback_by_ep[f['consumer_episode_id']].append(f)
    target_rows = []
    scope_proofs = {}

    def compact_scope(state):
        key = jsha(state)
        scope_proofs[key] = {k: v for k, v in state.items() if k != 'evidence_refs'}
        scope_proofs[key]['transitive_resource_node_count'] = len(state.get('evidence_refs') or [])
        scope_proofs[key]['transitive_resource_node_list_sha256'] = jsha(state.get('evidence_refs') or [])
        return {**state, 'scope_proof_id': key, 'evidence_refs': ['scope_proofs.jsonl.gz#' + key]}
    for t in targets:
        eid, i = t['episode_id'], t['source_message_index']
        state = prefix(eid, i)
        msg = native[eid]['messages'][i]
        versions_written = set()
        contribution_proofs = []
        exact_review_write = False
        for b in msg.get('content') or []:
            if not isinstance(b, dict) or b.get('type') != 'toolCall' or b.get('name') != 'write':
                continue
            args = b.get('arguments') or {}
            if isinstance(args, dict) and isinstance(args.get('content'), str):
                content_hash = sha(args['content'].encode())
                if eid in reviews and content_hash == reviews[eid][1]['sha256']:
                    exact_review_write = True
                matching = produced_file_hashes[eid].get(content_hash, set())
                if matching:
                    versions_written.update(matching)
                    contribution_proofs.append({'tool_call_id': b.get('id'), 'path': args.get('path', args.get('file_path')),
                        'content_sha256': content_hash, 'matching_output_tree_ids': sorted(matching)})
        positive_edges = [e for v in versions_written for e in version_edges[v] if e['version_trial_task_positive_silver']]
        observed_feedback = [f for f in feedback_by_ep[eid] if any(j < i for j in f['observed_read_message_indices'])]
        any_trial_edges = [e for v in versions_written for e in version_edges[v]]
        review_check = review_evidence_checks.get(eid) or {}
        review_candidate = bool(exact_review_write and review_check.get('evidence_review_silver_candidate') and not t['observed_tool_failure'])
        row = {'id': t['id'], 'episode_id': eid, 'source_message_index': i,
            'source_event_line': t['source_event_line'], 'source_message_sha256': t['source_message_sha256'],
            'route_id': normalized_route.get(eid), 'stage': t['request_corrected_role'],
            **compact_scope(state), 'scope_unit': 'only_initial_user_and_observed_prior_messages_plus_exact_resource_producer_prefixes',
            'source_admission': 'ADMIT' if state['eligible_scope'] else 'HOLD_PROTECTED' if state['protected_source_ids'] else 'HOLD_MISSING_EVIDENCE',
            'source_ids_visible_prefix': state['source_ids'],
            'protected_sources_visible_prefix': state['protected_source_ids'],
            'source_scope_is_not_quality_admission': True,
            'exact_produced_file_write_proofs': contribution_proofs,
            'exact_produced_version_ids': sorted(versions_written),
            'linked_trial_edge_ids': sorted({e['edge_id'] for e in any_trial_edges}),
            'positive_silver_trial_edge_ids': sorted({e['edge_id'] for e in positive_edges}),
            'after_actual_feedback_read': bool(observed_feedback),
            'feedback_producer_episode_ids': sorted({p['episode_id'] for f in observed_feedback for p in f['prior_review_matches']}),
            'outcome_attribution': 'EXACT_FILE_CONTRIBUTION_TO_TRIAL_TESTED_VERSION_SILVER' if positive_edges else 'VERSION_LINK_WITHOUT_POSITIVE_TRIAL' if any_trial_edges else 'NOT_ESTABLISHED_PER_STEP',
            'all_steps_in_retained_route_are_positive': False,
            'positive_outcome_loss_candidate': bool(positive_edges and not t['observed_tool_failure'] and not t['arguments_invalid_under_recovered_schema']),
            'outcome_quality_tier': 'OUTCOME_BACKED_SILVER' if positive_edges and not t['observed_tool_failure'] and not t['arguments_invalid_under_recovered_schema'] else 'EVIDENCE_REVIEW_SILVER' if review_candidate else 'UNKNOWN',
            'positive_skill_action_eligible': bool(positive_edges and state['eligible_scope'] and not t['observed_tool_failure'] and not t['arguments_invalid_under_recovered_schema']),
            'quality_positive_review_candidate': review_candidate,
            'quality_positive_review_eligible_scope': bool(review_candidate and state['eligible_scope']),
            'review_evidence_check': review_check if exact_review_write else None,
            'local_tool_format_success_is_not_semantic_success': True,
            'trial_outcome_is_silver_not_independent_Q': True,
            'training_admitted': False}
        target_rows.append(row)
    episode_rows = []
    for eid, ep in native.items():
        state = prefix(eid, len(ep['messages']))
        produced = by_episode_version.get(eid, [])
        downstream = [e for v in produced for e in version_edges[v['tree_content_sha256']]]
        episode_rows.append({'episode_id': eid, 'route_id': normalized_route.get(eid), 'stage': ep.get('kind'),
            'source_scope': {'post_episode_status': state['scope_status'], **compact_scope(state)},
            'produced_skill_versions': [{k: v[k] for k in ['tree_content_sha256', 'output_skill_root_logical_path', 'file_count']} for v in produced],
            'consumed_skill_versions': consumed.get(eid, []),
            'downstream_trial_links': sorted({e['edge_id'] for e in downstream}),
            'review_links_for_actor': sorted({e['edge_id'] for e in reviews_by_actor[eid]}),
            'feedback_reads': feedback_by_ep.get(eid, []),
            'outcome_supervision': {'positive_tested_versions': sorted({e['tree_content_sha256'] for e in downstream if e['version_trial_task_positive_silver']}),
                'quality_evidence': 'historical_case_findings_silver_not_independent_Q',
                'cost_evidence': 'original_all_attempts_known_and_unknown_records_separate',
                'all_episode_steps_positive': False},
            'old_v6_episode_status': legacy.get(eid, {}).get('status'), 'training_admitted': False})
    resource_rows = []
    for n in resource_nodes:
        scope = resource_scope(n['node_id'])
        resource_rows.append({'node_id': n['node_id'], 'episode_id': n['episode_id'],
            'native_path': n['native_path'], 'observed_after_assistant_message_index': n['consumer_assistant_message_index'],
            'file_identity': n.get('file_identity'), 'original_terminal': n['terminal'], **compact_scope(scope),
            'original_proven_producer_prefixes': n.get('proven_producer_prefixes') or [],
            'eligible_scope': not scope['protected_source_ids'] and not scope['unknown_reasons'],
            'metadata_not_a_training_example': True})
    write_rows('version_trial_review_edges.jsonl.gz', trial_edges)
    write_rows('target_outcome_labels.jsonl.gz', target_rows)
    write_rows('episode_outcomes.jsonl.gz', episode_rows)
    write_rows('resource_scope.jsonl.gz', resource_rows)
    write_rows('scope_proofs.jsonl.gz', ({'scope_proof_id': key, **value} for key, value in sorted(scope_proofs.items())))
    write_rows('resource_recovery_edges.jsonl.gz', resource_recoveries)
    write_rows('review_evidence_checks.jsonl.gz', review_evidence_checks.values())
    write_rows('produced_versions.jsonl.gz', producers)
    checks = {
        'all_native_episodes_processed': len(episode_rows) == 1763,
        'all_target_positions_processed': len(target_rows) == 32342,
        'all_ids_unique': len({r['id'] for r in target_rows}) == len(target_rows),
        'no_protected_target_eligible': all(not r['eligible_scope'] for r in target_rows if r['protected_source_ids']),
        'no_unknown_target_eligible': all(not r['eligible_scope'] for r in target_rows if r['unknown_reasons']),
        'no_blanket_retained_positive': all(r['all_steps_in_retained_route_are_positive'] is False for r in target_rows),
        'no_new_training_admission': all(r['training_admitted'] is False for r in target_rows),
    }
    assert all(checks.values()), checks
    summary = {'schema_version': 'wrd-v9-version-trial-lineage-1.0', 'training_started': False,
        'old_native_episodes': len(episode_rows), 'old_targets': len(target_rows),
        'original226_count': len(original226), 'new_holdout_count': len(holdout12),
        'post_episode_scope': dict(collections.Counter(r['source_scope']['post_episode_status'] for r in episode_rows)),
        'target_prefix_scope': dict(collections.Counter(r['scope_status'] for r in target_rows)),
        'target_scope_eligible_by_stage': dict(collections.Counter(r['stage'] for r in target_rows if r['eligible_scope'])),
        'target_scope_eligible_not_admitted': sum(r['eligible_scope'] for r in target_rows),
        'produced_version_attempts': len(producers), 'distinct_produced_trees': len(by_tree),
        'native_actor_episode_consumed_skill_map': len(consumed),
        'version_trial_review_edges': len(trial_edges),
        'positive_silver_version_trial_edges': sum(e['version_trial_task_positive_silver'] for e in trial_edges),
        'target_exact_version_contributions': sum(bool(r['exact_produced_version_ids']) for r in target_rows),
        'positive_outcome_loss_candidates_before_source_quality_context': sum(r['positive_outcome_loss_candidate'] for r in target_rows),
        'positive_outcome_and_source_candidates': sum(r['positive_outcome_loss_candidate'] and r['eligible_scope'] for r in target_rows),
        'resource_recovery_edges': len(resource_recoveries),
        'evidence_review_silver_writes_before_source_filter': sum(r['quality_positive_review_candidate'] for r in target_rows),
        'evidence_review_silver_and_source_candidates': sum(r['quality_positive_review_eligible_scope'] for r in target_rows),
        'actual_feedback_then_target_positions': sum(r['after_actual_feedback_read'] for r in target_rows),
        'review_decisions_not_automatic_correctness': dict(collections.Counter(v[0].get('decision') for v in reviews.values())),
        'checks': checks,
        'limits': ['Historical trial/model-review outcomes are silver, not independent five-dimensional quality gold.',
            'Scope closes actual observed prefixes, not all merely available resources.',
            'Unknown runtime/source ancestry remains held; producer input captures may be incomplete.',
            'A positive file contribution does not certify all steps, a complete repair mechanism, causal benefit or unseen generalization.',
            'This output changes no old data, masks, final admission, production state or concurrent ablation.']}
    (OUT / 'SUMMARY.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=True), flush=True)


def recover_overlay():
    """Inspect the eight outcome-bearing unresolved episodes without rewriting base."""
    OUT.mkdir(parents=True, exist_ok=True)
    base_names = ['target_outcome_labels.jsonl.gz', 'episode_outcomes.jsonl.gz',
                  'resource_scope.jsonl.gz', 'version_trial_review_edges.jsonl.gz', 'SUMMARY.json']
    base_pins = {name: {'sha256': sha((OUT / name).read_bytes()), 'bytes': (OUT / name).stat().st_size} for name in base_names}
    tt = list(rows(OUT / 'target_outcome_labels.jsonl.gz'))
    focus_targets = [r for r in tt if r['scope_status'] == 'HOLD_UNKNOWN' and
        (r['positive_outcome_loss_candidate'] or r.get('quality_positive_review_candidate'))]
    focus_eids = {r['episode_id'] for r in focus_targets}
    maximum = {eid: max(r['source_message_index'] for r in focus_targets if r['episode_id'] == eid) for eid in focus_eids}
    catalog = {e['episode_id']: e for e in rows(BUNDLE / 'catalog/episodes.jsonl')}
    native = {e['episode_id']: e for e in rows(BUNDLE / 'canonical/native_episodes.jsonl.gz')}
    selected_nodes = [n for n in rows(V6 / 'controlled/lineage_resources.jsonl.gz')
        if n['episode_id'] in focus_eids and n['consumer_assistant_message_index'] < maximum[n['episode_id']]
        and (n.get('terminal') or '').startswith('MISSING_')]
    wanted_hashes = {(n.get('file_identity') or {}).get('sha256') for n in selected_nodes} - {None}
    aliases = collections.defaultdict(list)
    all_inputs = collections.defaultdict(dict)
    for f in rows(BUNDLE / 'archive/file_index.jsonl'):
        if f['sha256'] in wanted_hashes or f.get('source_sha256') in wanted_hashes:
            aliases[f['sha256']].append({k: f.get(k) for k in ['logical_path', 'sha256', 'source_sha256', 'bytes', 'object', 'source_path']})
        bits = f['logical_path'].split('/', 2)
        if len(bits) == 3 and bits[1] in focus_eids and bits[2].startswith('workspace/inputs/'):
            all_inputs[bits[1]][('/' + bits[2])] = f

    # Framework text is checked statically. No archived module is imported or run.
    static_witnesses = collections.defaultdict(list)
    render_literals = collections.defaultdict(list)
    for p in (ROOT / 'research/archive/workflow_legacy_20261023').rglob('*.py'):
        data = p.read_bytes()
        identity = sha(data)
        if identity in wanted_hashes:
            static_witnesses[identity].append({'path': str(p), 'sha256': identity, 'proof': 'byte_exact_archived_framework_source'})
        if p.name == 'contract.py':
            try:
                mod = ast.parse(data.decode('utf-8-sig'))
            except (ValueError, SyntaxError, UnicodeError):
                continue
            for node in mod.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'render':
                    returns = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
                    if len(returns) == 1 and isinstance(returns[0].value, ast.Constant) and isinstance(returns[0].value.value, str):
                        text = returns[0].value.value
                        render_literals[sha(text.encode())].append({'path': str(p), 'source_sha256': identity,
                            'proof': 'AST_literal_return_of_framework_render_no_execution'})

    audits = []
    explicit_overrides = []
    read_cache = {}

    def path_fact(path, expected=None):
        p = Path(path)
        key = (str(p), expected)
        if key in read_cache:
            return read_cache[key]
        exists = p.is_file()
        result = {'path': str(p), 'exists': exists}
        if exists:
            data = p.read_bytes()
            result.update({'bytes': len(data), 'sha256': sha(data), 'matches_expected_sha256': sha(data) == expected if expected else None})
        read_cache[key] = result
        return result

    for n in selected_nodes:
        eid, mi, path = n['episode_id'], n['consumer_assistant_message_index'], n['native_path']
        fi = n.get('file_identity') or {}
        expected = fi.get('sha256')
        ep = native[eid]
        callmsg = ep['messages'][mi]
        calls = [b for b in callmsg.get('content') or [] if isinstance(b, dict) and b.get('type') == 'toolCall']
        source_root = Path(catalog[eid]['source_path'])
        facts = []
        raw = None
        if expected:
            cas = BUNDLE / 'archive' / fi['object']
            facts.append(path_fact(cas, expected))
            raw = cas.read_bytes()
            assert sha(raw) == expected
            if fi.get('source_path'):
                facts.append(path_fact(fi['source_path'], fi.get('source_sha256') or expected))
            for a in aliases[expected]:
                if a.get('source_path') and a['source_path'] != fi.get('source_path'):
                    facts.append(path_fact(a['source_path'], a.get('source_sha256') or expected))
        else:
            if path.startswith('/workspace/') and '$' not in path and '…' not in path:
                facts.append(path_fact(source_root / 'workspace' / path[len('/workspace/'):]))
            # Resolve only literal assignments in the same original exec call.
            for call in calls:
                args = call.get('arguments') or {}
                command = str(args.get('command') or '') if isinstance(args, dict) else ''
                assignments = dict(re.findall(r'\b([A-Z_][A-Z0-9_]*)=(/[^;\s]+)', command))
                resolved = path
                for var, value in assignments.items():
                    resolved = resolved.replace('$' + var, value).replace('${' + var + '}', value)
                if resolved != path and resolved.startswith('/workspace/'):
                    facts.append(path_fact(source_root / 'workspace' / resolved[len('/workspace/'):]))
        witnesses = list(static_witnesses.get(expected, [])) + list(render_literals.get(expected, []))
        # Text-only code read is different from actually executing a data-reading script.
        literal_code_read = False
        for call in calls:
            args = call.get('arguments') or {}
            if isinstance(args, dict) and call.get('name') == 'read' and (args.get('path') or args.get('file_path')) == path:
                literal_code_read = True
        classification = 'ORIGINAL_CARRIERS_RECOVERED_ANCESTRY_STILL_UNRESOLVED' if expected else 'RAW_TEMP_OR_DYNAMIC_PATH_NOT_FROZEN'
        if witnesses and (literal_code_read or path.endswith('/generation.md')):
            classification = 'FIXED_FRAMEWORK_LITERAL_CODE_OR_RULE_BODY'
            explicit_overrides.append({'node_id': n['node_id'], 'episode_id': eid, 'native_path': path,
                'closure': 'CLOSED_FIXED_FRAMEWORK_BODY_ONLY', 'source_ids': [], 'protected_source_ids': [],
                'witnesses': witnesses, 'original_tool_mode': 'read_only',
                'does_not_approve_execution_runtime_dependencies': True})
        temporal_creation = []
        for earlier, message in enumerate(ep['messages'][:mi + 1]):
            if message.get('role') != 'assistant':
                continue
            for call in message.get('content') or []:
                if not isinstance(call, dict) or call.get('type') != 'toolCall':
                    continue
                args = call.get('arguments') or {}
                if not isinstance(args, dict):
                    continue
                if call.get('name') == 'write' and (args.get('path') or args.get('file_path')) == path and isinstance(args.get('content'), str) and earlier < mi:
                    cid = call.get('id')
                    result = next(((j, rm) for j, rm in enumerate(ep['messages']) if rm.get('role') == 'toolResult' and rm.get('toolCallId') == cid), None)
                    if result and not result[1].get('isError'):
                        body = args['content'].encode()
                        temporal_creation.append({'proof': 'same_literal_path_prior_native_write_and_success_result',
                            'creator_message_index': earlier, 'write_tool_call_id': cid,
                            'content_sha256': sha(body), 'bytes': len(body), 'source_prefix_end_exclusive': earlier,
                            'result_message_index': result[0], 'body_contains_replacement_character': '\ufffd' in args['content']})
                command = str(args.get('command') or '')
                for match in re.finditer(r"cat\s*>\s*(/[^\s]+)\s*<<['\"]?([A-Za-z0-9_]+)['\"]?\r?\n(.*?)\r?\n\2(?:\r?\n|$)", command, re.S):
                    created_path, marker, content = match.groups()
                    body = (content + '\n').encode()
                    # Inspect was renamed by the very next observed command.
                    possible_paths = {created_path}
                    for later_message in ep['messages'][earlier + 1:mi + 1]:
                        for b in later_message.get('content') or [] if isinstance(later_message.get('content'), list) else []:
                            if isinstance(b, dict) and b.get('type') == 'toolCall' and isinstance(b.get('arguments'), dict):
                                later_command = str(b['arguments'].get('command') or '')
                                renamed = re.search(r'\bmv\s+' + re.escape(created_path) + r'\s+(/[^\s;&]+)', later_command)
                                if renamed:
                                    possible_paths.add(renamed.group(1))
                    if path not in possible_paths:
                        continue
                    host_matches = [f for f in facts if f.get('sha256') == sha(body)]
                    if not host_matches:
                        for actual in possible_paths:
                            if actual.startswith('/workspace/'):
                                fact = path_fact(source_root / 'workspace' / actual[len('/workspace/'):], sha(body))
                                facts.append(fact)
                                if fact.get('matches_expected_sha256'):
                                    host_matches.append(fact)
                    if host_matches:
                        literal_inputs = sorted(set(re.findall(r"['\"](/workspace/inputs/[^'\"]+)['\"]", content)))
                        bound = []
                        for literal in literal_inputs:
                            f = all_inputs[eid].get(literal)
                            if f:
                                bound.append({'native_path': literal, 'source_ids_from_literal_scope': sorted(set(SID.findall(literal))),
                                    'logical_path': f['logical_path'], 'sha256': f['sha256'], 'object': f['object']})
                        temporal_creation.append({'proof': 'literal_heredoc_original_assistant_code_matches_current_D_E_temp_bytes',
                            'creator_message_index': earlier, 'content_sha256': sha(body), 'bytes': len(body),
                            'source_prefix_end_exclusive': earlier, 'literal_created_path': created_path,
                            'actual_rename_paths': sorted(possible_paths), 'runtime_input_literal_bindings': bound,
                            'runtime_input_literals_all_bound': len(bound) == len(literal_inputs),
                            'does_not_certify_complete_static_program_dataflow': True})
        if temporal_creation and not expected:
            classification = 'RAW_TEMP_RECOVERED_WITH_ORIGINAL_NATIVE_CREATION_AND_READ_CAUSAL_LINK'
        content_fields = None
        if raw:
            try:
                value = json.loads(raw.decode('utf-8-sig'))
                content_fields = sorted(value) if isinstance(value, dict) else {'root_type': type(value).__name__}
            except (UnicodeError, ValueError):
                value = None
        else:
            value = None
        # Recover the original task's immutable implementation/source pin paths.
        task_pins = []
        if isinstance(value, dict) and path.endswith('/new_route/task.json'):
            for group in ['making_implementation_pins', 'source_pins']:
                for label, pin in (value.get(group) or {}).items():
                    if isinstance(pin, dict) and isinstance(pin.get('path'), str):
                        task_pins.append({'group': group, 'name': label, 'fact': path_fact(pin['path'], pin.get('sha256'))})
        audits.append({'node_id': n['node_id'], 'episode_id': eid, 'assistant_message_index': mi,
            'native_path': path, 'original_terminal': n['terminal'], 'file_sha256': expected,
            'original_source_path': fi.get('source_path'), 'cas_object': fi.get('object'),
            'raw_D_E_and_CAS_carriers': facts, 'frozen_alias_records': aliases.get(expected, []),
            'archived_framework_witnesses': witnesses, 'task_implementation_and_source_pin_facts': task_pins,
            'original_native_temp_creation_proofs': temporal_creation,
            'content_field_names_not_body': content_fields,
            'producer_candidates': n.get('producer_candidates') or [],
            'finding': classification,
            'target_training_source_admission_changed': False,
            'why_not_auto_clean': 'Carrier recovery and fixed-code identity do not prove route/skill/trial source ancestors or a script runtime input closure.'})

    # Label evidence is itself source-controlled. Do not let protected trials
    # provide rewards or positive-loss annotations to an otherwise clean prefix.
    episodes = {e['episode_id']: e for e in rows(OUT / 'episode_outcomes.jsonl.gz')}
    trial_by = {e['edge_id']: e for e in rows(OUT / 'version_trial_review_edges.jsonl.gz')}
    label_scope = []
    for t in tt:
        if not (t['positive_outcome_loss_candidate'] or t.get('quality_positive_review_candidate')):
            continue
        edge_ids = t.get('positive_silver_trial_edge_ids') or (t.get('review_evidence_check') or {}).get('trial_edge_ids') or []
        evidence_eids = set()
        for edge_id in edge_ids:
            e = trial_by[edge_id]
            evidence_eids.add(e['reviewer_episode_id'])
            for arm in e['arms'].values():
                evidence_eids.update(arm.get('episode_ids') or [])
        states = [episodes[e]['source_scope'] for e in evidence_eids if e in episodes]
        protected_ids = sorted({s for state in states for s in state['protected_source_ids']})
        unknown = sorted({s for state in states for s in state['unknown_reasons']})
        admission = 'HOLD_PROTECTED' if protected_ids else 'HOLD_MISSING_EVIDENCE' if unknown or len(states) != len(evidence_eids) else 'ADMIT'
        label_scope.append({'id': t['id'], 'episode_id': t['episode_id'], 'source_message_index': t['source_message_index'],
            'source_admission_original_input_prefix': t['source_admission'],
            'outcome_label_evidence_source_admission': admission,
            'label_evidence_episode_ids': sorted(evidence_eids), 'label_evidence_trial_edge_ids': edge_ids,
            'protected_sources_in_label_evidence': protected_ids, 'unknown_label_evidence_reasons': unknown,
            'final_positive_skill_or_review_eligible': bool(t['eligible_scope'] and admission == 'ADMIT'),
            'not_a_new_training_admission': True})
    write_rows('recovery_overlay.resources.jsonl.gz', audits)
    write_rows('recovery_overlay.fixed_framework_overrides.jsonl.gz', explicit_overrides)
    write_rows('recovery_overlay.label_evidence_source_scope.jsonl.gz', label_scope)
    assert all(sha((OUT / name).read_bytes()) == value['sha256'] for name, value in base_pins.items())
    summary = {'schema_version': 'wrd-v9-targeted-recovery-overlay-v1', 'base_files_unchanged': base_pins,
        'focus_episode_ids': sorted(focus_eids), 'focus_target_count': len(focus_targets),
        'resource_nodes_audited': len(audits), 'resource_node_findings': dict(collections.Counter(r['finding'] for r in audits)),
        'carrier_file_checks': len(read_cache), 'carrier_checks_existing': sum(r['exists'] for r in read_cache.values()),
        'fixed_framework_body_overrides': len(explicit_overrides),
        'outcome_label_scope_counts': dict(collections.Counter(r['outcome_label_evidence_source_admission'] for r in label_scope)),
        'final_positive_eligible_after_label_scope': sum(r['final_positive_skill_or_review_eligible'] for r in label_scope),
        'base_training_admission_changed': False, 'training_started': False,
        'limits': ['This overlay records actual D/E/CAS recovery and immutable code matches without executing old programs.',
            'Fixed framework reads do not establish runtime dependencies or release a target whose route/skill/feedback source ancestors remain unknown.',
            'Label-source closure uses conservative full archived evidence episode prefixes; no protected trial/model-review is admitted as a reward or training target.']}
    (OUT / 'RECOVERY_OVERLAY_SUMMARY.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=True), flush=True)


def apply_recovery_overlay():
    """Recompute into a separate directory; never overwrite the frozen main inputs."""
    global OUT
    base = OUT
    pins = {p.name: sha(p.read_bytes()) for p in base.glob('*.jsonl.gz')}
    nodes = list(rows(V6 / 'controlled/lineage_resources.jsonl.gz'))
    fixed = list(rows(base / 'recovery_overlay.fixed_framework_overrides.jsonl.gz'))
    for item in fixed:
        EXTRA_RESOURCE_OVERRIDES[item['node_id']] = {'kind': item['closure'], 'parents': [],
            'source_ids': [], 'evidence': item['witnesses']}
    coord_path = ROOT / 'output/20261026_wrd_dataset_v9/coordination/CAUSAL_RESOURCE_OVERLAY.json'
    coord = json.loads(coord_path.read_text(encoding='utf-8'))
    for item in coord['overlays']:
        EXTRA_RESOURCE_OVERRIDES[item['node_id']] = {'kind': item['replacement_relation'],
            'parents': [(item['parent_episode_id'], item['parent_prefix_end_exclusive'])],
            'evidence': item['evidence']}
    ancestry_path = base / 'LEGACY_ROUTE_ANCESTRY_QA.json'
    ancestry = json.loads(ancestry_path.read_text(encoding='utf-8'))
    assert ancestry['status'] == 'PASS'
    batch = {x['batch']: x for x in ancestry['producer_prefixes']}
    selected = {
        'ep_6a74265b2416d7162cdb': ('batch_009', '/workspace/inputs/route_card.json'),
        'ep_b67a41ec6592861a59df': ('batch_004', '/workspace/inputs/route_card.json'),
        'ep_1f044b9ceb4f5bf0858b': ('batch_002', '/workspace/inputs/route.json'),
    }
    projection_facts = []
    protected_original_card_by_sha = {}
    for eid, (producer, path) in selected.items():
        ids = batch[producer]['protected_preview_source_ids_in_input']
        assert ids and batch[producer]['actual_protected_body_deliveries']
        for node in nodes:
            if node['episode_id'] != eid or node['native_path'] != path:
                continue
            rec = node['file_identity']
            value = json.loads((BUNDLE / 'archive' / rec['object']).read_text(encoding='utf-8-sig'))
            if eid == 'ep_1f044b9ceb4f5bf0858b':
                original = ROOT / 'output/20261021_pipeline_infra_audit/route_recovery/batch_002/card_02/derived_card.json'
                raw = json.loads(original.read_text(encoding='utf-8-sig'))
                assert value['route_signature'] == raw['route_signature'] and value['value_plan'] == raw['value_plan']
                proof = {'kind': 'EXACT_NONEMPTY_ROUTE_SIGNATURE_AND_VALUE_PLAN_FIELD_PROJECTION',
                    'original_card_path': str(original), 'original_card_sha256': sha(original.read_bytes()),
                    'matched_fields': ['id', 'route_signature', 'value_plan'],
                    'matched_signature_sha256': jsha(raw['route_signature']), 'matched_value_plan_sha256': jsha(raw['value_plan'])}
            else:
                matches = [j for j in ancestry['legacy_maker_mechanical_joins'] if j['card_source']['sha256'] == rec['sha256']]
                assert len(matches) == 1 and matches[0]['accepted_card_sha256_matches_stripped_card'] and matches[0]['stripped_card_equals_original_derived_card']
                proof = {'kind': 'PINNED_MECHANICAL_ACCEPTED_CARD_COPY', 'mechanical_join': matches[0]}
            fact = {'node_id': node['node_id'], 'episode_id': eid, 'native_path': path,
                'source_ids': ids, 'raw_ancestor_batch': producer, 'original_native_prefix_proof': batch[producer], 'projection_proof': proof}
            projection_facts.append(fact)
            protected_original_card_by_sha[rec['sha256']] = fact
            EXTRA_RESOURCE_OVERRIDES[node['node_id']] = {'kind': 'PROTECTED_EXACT_ORIGINAL_ROUTE_PROJECTION_RECOVERED',
                'parents': [], 'source_ids': ids, 'evidence': fact}
    for node in nodes:
        rec = node.get('file_identity') or {}
        fact = protected_original_card_by_sha.get(rec.get('sha256'))
        if fact and node['node_id'] not in EXTRA_RESOURCE_OVERRIDES:
            EXTRA_RESOURCE_OVERRIDES[node['node_id']] = {'kind': 'PROTECTED_BYTE_EXACT_SAME_ORIGINAL_ROUTE_INPUT_ALIAS',
                'parents': [], 'source_ids': fact['source_ids'], 'evidence': {
                    'actual_consumer_file_sha256': rec['sha256'], 'actual_consumer_native_path': node['native_path'],
                    'same_original_card_proof': fact}}
    temp_proofs = list(rows(base / 'recovery_overlay.resources.jsonl.gz'))
    for item in temp_proofs:
        # A successful prior native write with the same literal path has a
        # precise current-session source prefix. Heredoc runtime remains held.
        exact = [p for p in item.get('original_native_temp_creation_proofs') or []
            if p['proof'] == 'same_literal_path_prior_native_write_and_success_result']
        if exact:
            last = max(exact, key=lambda x: x['creator_message_index'])
            EXTRA_RESOURCE_OVERRIDES[item['node_id']] = {'kind': 'FOLLOW_PRIOR_NATIVE_WRITE_SAME_LITERAL_PATH',
                'parents': [(item['episode_id'], last['source_prefix_end_exclusive'])], 'evidence': last}
    OUT = base / 'recomputed_scope_overlay'
    write_rows('explicit_resource_updates.jsonl.gz', ({'node_id': k, **v} for k, v in EXTRA_RESOURCE_OVERRIDES.items()))
    write_rows('protected_route_projection_proofs.jsonl.gz', projection_facts)
    main()
    assert all(sha((base / name).read_bytes()) == identity for name, identity in pins.items())
    original = {x['id']: x for x in rows(base / 'target_outcome_labels.jsonl.gz')}
    updates = []
    for row in rows(OUT / 'target_outcome_labels.jsonl.gz'):
        before = original[row['id']]
        if any(row[k] != before[k] for k in ['source_admission', 'source_ids_visible_prefix', 'protected_sources_visible_prefix', 'unknown_reasons']):
            updates.append({'id': row['id'], 'episode_id': row['episode_id'], 'source_message_index': row['source_message_index'],
                'base_source_admission': before['source_admission'], 'source_admission': row['source_admission'],
                'source_ids_visible_prefix': row['source_ids_visible_prefix'], 'protected_sources_visible_prefix': row['protected_sources_visible_prefix'],
                'unknown_reasons': row['unknown_reasons'], 'evidence_refs': row['evidence_refs'],
                'positive_skill_action_eligible': row['positive_skill_action_eligible'],
                'quality_positive_review_eligible_scope': row['quality_positive_review_eligible_scope'],
                'recomputed_scope_proof_id': row['scope_proof_id'], 'training_admitted': False})
    write_rows('target_source_scope_updates.jsonl.gz', updates)
    (OUT / 'OVERLAY_RECEIPT.json').write_text(json.dumps({'base_files_preserved': pins,
        'explicit_resource_update_count': len(EXTRA_RESOURCE_OVERRIDES), 'target_scope_update_count': len(updates),
        'update_status_transitions': dict(collections.Counter(x['base_source_admission'] + '->' + x['source_admission'] for x in updates)),
        'training_started': False}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--recover-overlay' in sys.argv:
        recover_overlay()
    elif '--apply-recovery-overlay' in sys.argv:
        apply_recovery_overlay()
    else:
        main()
