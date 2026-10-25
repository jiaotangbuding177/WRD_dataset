"""Independent, body-free provenance scope review for historical raw pairs.

No model, training, sandbox execution or remote calls. Original bodies unchanged.
"""
from collections import Counter, defaultdict
import ast
import gzip
import hashlib
import json
from pathlib import Path
import re
import unicodedata


ROOT = Path('D:/skillloop')
OUT = ROOT / 'output/20261025_wrd_reasoning_recovery_v4'


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def textsha(s):
    return hashlib.sha256(str(s).encode()).hexdigest()


def normalize(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', str(s)))


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def iter_strings(x, pointer=''):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from iter_strings(v, pointer + '/' + str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from iter_strings(v, pointer + '/' + str(i))
    elif isinstance(x, str):
        yield pointer, x


def formal_inventory():
    formal_texts = defaultdict(list)
    attachment_hashes = set()
    sources = []
    formal_session_refs = defaultdict(list)
    paths = sorted((ROOT / 'benchmark').glob('*/evaluation/用户输入与文件投递.jsonl'))
    for p in paths:
        contract = p.parent.parent / 'contracts/evaluation.jsonl'
        allowed = set()
        if contract.is_file():
            with contract.open(encoding='utf-8-sig') as f:
                for lineno, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    sid = r.get('session_id')
                    if sid:
                        allowed.add(sid)
                        formal_session_refs[sid].append({'path': str(contract.relative_to(ROOT)), 'record_1based': lineno,
                                                        'task_id': r.get('task_id')})
        count = 0
        selected = 0
        with p.open(encoding='utf-8-sig') as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                count += 1
                if r.get('session_id') not in allowed:
                    continue
                selected += 1
                body = r.get('user_input')
                if isinstance(body, str) and body.strip():
                    formal_texts[normalize(body)].append({'source_file': str(p.relative_to(ROOT)),
                        'record_1based': count, 'session_id_sha256': textsha(r.get('session_id')),
                        'user_input_sha256': textsha(body)})
                for a in r.get('attachments') or []:
                    if a.get('sha256'):
                        attachment_hashes.add(a['sha256'])
        sources.append({'path': str(p.relative_to(ROOT)), 'sha256': sha(p), 'all_rows': count,
                        'formal_selected_rows': selected, 'formal_contract_sessions': len(allowed),
                        'selection_contract_sha256': sha(contract) if contract.is_file() else None})
    current = ROOT / 'output/20261025_ablation_remaining/frozen/tasks250.json'
    tasks = load(current)
    for index, task in enumerate(tasks, 1):
        body = task.get('prompt')
        if isinstance(body, str) and body.strip():
            formal_texts[normalize(body)].append({'source_file': str(current.relative_to(ROOT)),
                'record_1based': index, 'task_id': task.get('task_id'), 'user_input_sha256': textsha(body)})
        for a in task.get('resources') or []:
            if isinstance(a, dict) and a.get('sha256'):
                attachment_hashes.add(a['sha256'])
    sources.append({'path': str(current.relative_to(ROOT)), 'sha256': sha(current),
                    'all_rows': len(tasks), 'formal_selected_rows': len(tasks), 'fixed_current_250': True})
    return formal_texts, attachment_hashes, sources, formal_session_refs


def review_sse(formal_texts, formal_session_refs):
    mechanical = OUT / 'controlled/sse_reasoning_pairs.mechanical.jsonl.gz'
    ledgerpath = ROOT / 'output/20261015_ewi_teacher_DATA/data/training_index.jsonl'
    ledger = {}
    with ledgerpath.open(encoding='utf-8-sig') as f:
        for lineno, line in enumerate(f, 1):
            r = json.loads(line)
            ledger[r['source_id']] = {**r, '_ledger_line': lineno}
    rows = []
    totals = Counter()
    original_line_cache = {}
    with gzip.open(mechanical, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            pair = json.loads(line)
            parsed = pair.get('observed_parsed_output') or {}
            sid = parsed.get('source_id') if isinstance(parsed, dict) else None
            if not sid and re.fullmatch(r'conv_[a-zA-Z0-9]+', pair.get('episode_id') or ''):
                sid = pair['episode_id']
            entry = ledger.get(sid)
            source_proof = {'in_current_evolution_index': bool(entry and entry.get('logical_role') == 'evolution'),
                            'physical_line_sha_matches': False, 'source_identity_matches': False}
            if entry:
                p = Path(entry['source_file'])
                if str(p) not in original_line_cache:
                    original_line_cache[str(p)] = p.read_bytes().split(b'\n')
                raw = original_line_cache[str(p)][entry['physical_line'] - 1]
                obj = json.loads(raw)
                actual_sid = obj.get('session_id') or obj.get('source_id') or obj.get('id')
                source_proof.update({'source_file': str(p), 'physical_line': entry['physical_line'],
                    'source_record_sha256': hashlib.sha256(raw).hexdigest(),
                    'expected_source_record_sha256': entry['source_record_sha256'],
                    'physical_line_sha_matches': hashlib.sha256(raw).hexdigest() == entry['source_record_sha256'],
                    'source_identity_matches': actual_sid == sid,
                    'original_split_preserved': entry.get('original_split'),
                    'ledger_line_1based': entry['_ledger_line']})
            matches = []
            for i, m in enumerate(pair['original_request'].get('messages') or []):
                if not isinstance(m.get('content'), str):
                    continue
                normalized = normalize(m['content'])
                for formal, refs in formal_texts.items():
                    if normalized == formal or len(formal) >= 100 and formal in normalized:
                        matches.append({'message_index': i, 'formal_refs': refs})
            protected_old = list(formal_session_refs.get(sid, []))
            if matches or protected_old:
                reviewed = 'formal_evaluation_exclude'
                basis = 'formal task-input match or protected original 226 source identity'
            elif all(source_proof[k] for k in ('in_current_evolution_index', 'physical_line_sha_matches', 'source_identity_matches')):
                reviewed = 'source_proven_learning_development_candidate'
                basis = 'current evolution ledger plus physical original source-line SHA and source identity verified'
            else:
                reviewed = 'unknown_requires_source_review'
                basis = 'no exact original source proof; naming and source role label not sufficient'
            row = {'pair_id': pair['id'], 'episode_id': pair['episode_id'], 'source_id': sid,
                   'original_role': pair['role_scope'], 'reviewed_scope': reviewed, 'scope_basis': basis,
                   'source_proof': source_proof, 'formal_input_matches': matches,
                   'protected_original_evaluation_source_refs': protected_old,
                   'source_sse': pair['source_sse'], 'source_request': pair['source_request'],
                   'original_reasoning_characters': pair['original_reasoning_characters'],
                   'historical_selfbuilt_executor_not_native_equivalent': True,
                   'semantic_approved': False, 'training_admitted': False, 'publication_approved': False}
            rows.append(row)
            totals[reviewed + ':pairs'] += 1
            totals[reviewed + ':reasoning_characters'] += pair['original_reasoning_characters']
    dest = OUT / 'controlled/sse_scope_review.by_pair.jsonl.gz'
    with gzip.open(dest, 'wt', encoding='utf-8', newline='\n') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    return {'counts': dict(totals), 'rows': len(rows), 'source_ledger': {'path': str(ledgerpath), 'sha256': sha(ledgerpath)},
            'original_mechanical_pairs_sha256': sha(mechanical),
            'controlled_index': {'path': str(dest.relative_to(OUT)), 'sha256': sha(dest), 'bytes': dest.stat().st_size},
            'protected_original_eval_source_matches': sum(bool(r['protected_original_evaluation_source_refs']) for r in rows),
            'formal_task_text_matched_pairs': sum(bool(r['formal_input_matches']) for r in rows),
            'full_semantic_and_endstate_approval_completed': False}


def generation_evidence(root):
    genpath = root / 'new_attachment_generation.json'
    if not genpath.is_file():
        return {'present': False, 'synthetic_provenance_declared': False, 'generator_hash_matches': False}
    obj = load(genpath)
    generator = obj.get('generator') or obj.get('source') or {}
    p = Path(generator.get('path', ''))
    declared = obj.get('synthetic') is True or obj.get('new_simulated_enterprise_attachments') is True
    return {'present': True, 'path': str(genpath), 'sha256': sha(genpath),
        'synthetic_provenance_declared': declared,
        'generator_reference': {'path': str(p), 'declared_sha256': generator.get('sha256'),
            'observed_sha256': sha(p) if p.is_file() else None},
        'generator_hash_matches': p.is_file() and sha(p) == generator.get('sha256'),
        'generated_at': obj.get('generated_at'), 'skill_frozen_at': obj.get('skill_frozen_at'),
        'not_proof_of_semantic_independence': True}


def file_reference_evidence(packet, formal_attachments):
    evidence = []
    for entry in packet.get('copies') or []:
        if not isinstance(entry, dict):
            continue
        source_ref = entry.get('source') or ''
        source = Path(source_ref.get('path', '') if isinstance(source_ref, dict) else source_ref)
        copy = entry.get('copy') if isinstance(entry.get('copy'), dict) else {}
        expected_sha = copy.get('sha256') or (source_ref.get('sha256') if isinstance(source_ref, dict) else None)
        row = {'source_path': str(source), 'source_exists': source.is_file(),
               'declared_copy_sha256': expected_sha, 'source_sha256': None,
               'source_matches_copy_hash': False, 'formal_attachment_sha_overlap': False}
        if source.is_file():
            h = sha(source)
            row.update(source_sha256=h, source_matches_copy_hash=h == expected_sha,
                       formal_attachment_sha_overlap=h in formal_attachments)
        evidence.append(row)
    return evidence


def semantic_source_proof(copies, formal_session_refs):
    semantic = next((Path(r['source_path']) for r in copies
                     if Path(r['source_path']).name == 'semantic_session.complete.json'), None)
    proof = {'present': semantic is not None, 'verified_current_evolution_complete_source': False}
    if semantic is None or not semantic.is_file():
        return proof
    obj = load(semantic)
    sid = obj.get('session_id') or obj.get('source_id')
    ledgerpath = ROOT / 'output/20261015_ewi_teacher_DATA/data/training_index.jsonl'
    entry = None
    with ledgerpath.open(encoding='utf-8-sig') as f:
        for lineno, line in enumerate(f, 1):
            row = json.loads(line)
            if row.get('source_id') == sid:
                entry = row
                proof['ledger_line_1based'] = lineno
                break
    if not entry:
        return proof
    original = Path(entry['source_file'])
    raw = original.read_bytes().split(b'\n')[entry['physical_line'] - 1]
    orig = json.loads(raw)
    pin_ok = hashlib.sha256(raw).hexdigest() == entry['source_record_sha256']
    turns_ok = obj.get('turns') == orig.get('turns')
    messages_ok = obj.get('messages') == orig.get('messages')
    evolution = entry.get('logical_role') == 'evolution'
    proof.update({'semantic_source_path': str(semantic), 'semantic_source_sha256': sha(semantic),
        'source_id': sid, 'current_role': entry.get('logical_role'),
        'original_source_path': str(original), 'physical_line': entry['physical_line'],
        'original_source_record_sha256': hashlib.sha256(raw).hexdigest(),
        'physical_source_sha_matches': pin_ok, 'complete_turns_match': turns_ok,
        'complete_messages_match': messages_ok,
        'protected_original_evaluation_source_refs': list(formal_session_refs.get(sid, [])),
        'verified_current_evolution_complete_source': pin_ok and turns_ok and messages_ok and evolution})
    return proof


def existing_validation_evidence(run):
    candidate = run / 'workspace/outputs/candidate'
    study_root = run.parents[3]
    rows = []
    for p in sorted(study_root.glob('validation_attempt_*/validation.json')):
        obj = load(p)
        if str(Path(obj.get('candidate', ''))).lower() != str(candidate).lower():
            continue
        files = []
        for item in obj.get('candidate_files') or []:
            actual = candidate / item['relative_path']
            files.append({'relative_path': item['relative_path'], 'expected_sha256': item.get('sha256'),
                          'actual_sha256': sha(actual) if actual.is_file() else None,
                          'sha_matches': actual.is_file() and sha(actual) == item.get('sha256')})
        validator = obj.get('validator_source') or {}
        validator_path = Path(validator.get('path', ''))
        cases = obj.get('development_cases') or []
        rows.append({'validation_path': str(p), 'validation_sha256': sha(p),
            'recorded_passed': obj.get('passed'), 'recorded_candidate_tree_sha256': obj.get('candidate_tree_sha256'),
            'recorded_candidate_unchanged': obj.get('candidate_unchanged_by_validation'),
            'recorded_development_cases': len(cases), 'recorded_cases_passed': sum(c.get('passed') is True for c in cases),
            'recorded_program_runs': obj.get('validation_program_runs'),
            'recorded_model_posts': obj.get('model_posts'), 'recorded_human_semantic_code_edits': obj.get('human_semantic_code_edits'),
            'candidate_file_checks': files, 'all_recorded_candidate_file_hashes_match': bool(files) and all(f['sha_matches'] for f in files),
            'validator_source': validator, 'validator_source_current_sha_matches': validator_path.is_file() and sha(validator_path) == validator.get('sha256'),
            'historical_validator_not_current_independent_five_dimension_Q': True,
            'this_audit_did_not_execute_programs_or_regrade': True})
    return rows


def main():
    auditpath = OUT / 'RAW_REASONING_PAIRS_AUDIT.json'
    audit = load(auditpath)
    watched = [OUT / 'controlled' / n for n in ('raw_pairs.all.jsonl.gz', 'raw_pairs.nonformal.mechanical.jsonl.gz',
                                               'raw_run_trajectories.jsonl.gz', 'sse_reasoning_pairs.mechanical.jsonl.gz')]
    original_raw_hashes = {str(p): sha(p) for p in watched}
    formal_texts, formal_attachments, formal_sources, formal_session_refs = formal_inventory()
    inventorypath = ROOT / 'research/data_prep/wrd_training/resources/history_inventory.json'
    inventory = load(inventorypath)
    excluded_roots = [Path(r['path']) for r in inventory['roots'] if r['role'] == 'eval_excluded']
    by_run = defaultdict(list)
    for r in audit['pairs']:
        if r['scope'] in {'historical_business_actor_or_validation_requires_source_audit', 'historical_skill_generation_candidate',
                          'historical_development_actor_candidate'}:
            by_run[r['run_path']].append(r)
    rows = []
    counts = defaultdict(Counter)
    aggregate = Counter()
    generator_cache = {}
    for runstr, pairs in sorted(by_run.items()):
        run = Path(runstr)
        kind = pairs[0]['scope']
        input_path = run / 'input_packet.json'
        packet = load(input_path) if input_path.is_file() else {}
        protocol_ref = packet.get('protocol') or {}
        protocol_path = Path(protocol_ref.get('path', ''))
        protocol = load(protocol_path) if protocol_path.is_file() else {}
        job = packet.get('job') or {}
        task_id = job.get('task_id')
        task = (protocol.get('tasks') or {}).get(task_id) if isinstance(protocol.get('tasks'), dict) else None
        observed_text = (packet.get('packet') or {}).get('完整用户委托')
        formal_matches = []
        text_candidates = [('input_packet/packet/完整用户委托', observed_text)]
        if isinstance(task, dict):
            text_candidates.append(('protocol/tasks/current/user_request', task.get('user_request')))
        # Actual first request user text catches wrappers around an exact formal task.
        observed_contents = set()
        for pair in sorted(pairs, key=lambda r: int(r['request_ordinal'])):
            request_path = Path(pair['request_path'])
            assert sha(request_path) == pair['request_sha256']
            req = load(request_path)
            for i, message in enumerate(req.get('messages') or []):
                body = message.get('content')
                if not isinstance(body, str) or body in observed_contents:
                    continue
                observed_contents.add(body)
                text_candidates.append((f'request/{pair["request_ordinal"]}/messages/{i}/content', body))
        for pointer, body in text_candidates:
            if not isinstance(body, str):
                continue
            normalized = normalize(body)
            for formal, refs in formal_texts.items():
                exact = normalized == formal
                contained = len(formal) >= 100 and formal in normalized
                if exact or contained:
                    formal_matches.append({'input_pointer': pointer, 'match': 'normalized_exact' if exact else 'full_formal_text_contained',
                                           'matched_formal_record_refs': refs})
        excluded_by_inventory = [str(p) for p in excluded_roots if p == run or p in run.parents]
        root = next((p for p in [run, *run.parents] if (p / 'new_attachment_generation.json').is_file()), None)
        if root:
            if str(root) not in generator_cache:
                generator_cache[str(root)] = generation_evidence(root)
            gen = generator_cache[str(root)]
        else:
            gen = {'present': False, 'synthetic_provenance_declared': False, 'generator_hash_matches': False}
        protocol_pinned = protocol_path.is_file() and sha(protocol_path) == protocol_ref.get('sha256')
        request_identity = isinstance(task, dict) and isinstance(observed_text, str) and normalize(task.get('user_request')) == normalize(observed_text)
        copies = file_reference_evidence(packet, formal_attachments)
        copies_ok = bool(copies) and all(x['source_exists'] and x['source_matches_copy_hash'] for x in copies)
        attachment_overlap = any(x['formal_attachment_sha_overlap'] for x in copies)
        semantic_proof = semantic_source_proof(copies, formal_session_refs)
        if formal_matches or excluded_by_inventory or semantic_proof.get('protected_original_evaluation_source_refs'):
            classification = 'formal_evaluation_exclude'
            basis = 'actual formal user-input match or previously documented formal root'
        elif gen['synthetic_provenance_declared'] and gen['generator_hash_matches'] and protocol_pinned and request_identity and copies_ok and not attachment_overlap:
            classification = 'source_proven_learning_development_candidate'
            basis = 'pinned synthetic-input generator plus exact task/input identity and copied-file SHA evidence'
        elif semantic_proof['verified_current_evolution_complete_source'] and protocol_pinned and request_identity and copies_ok and not attachment_overlap:
            classification = 'source_proven_learning_development_candidate'
            basis = 'complete current-evolution conversation physically source-SHA verified, matching all original turns/messages, plus pinned task/input and copied-file hashes'
        else:
            classification = 'unknown_requires_source_review'
            basis = 'not enough positive source evidence; absence of formal text match alone does not prove learning scope'
        resultpath = run / 'result.json'
        result = load(resultpath) if resultpath.is_file() else {}
        row = {'run_path': runstr, 'run_id': textsha(runstr)[:24], 'old_scope': kind,
            'reviewed_scope': classification, 'scope_basis': basis, 'raw_response_pairs': len(pairs),
            'reasoning_responses': sum(bool(x['reasoning_characters']) for x in pairs),
            'reasoning_characters': sum(x['reasoning_characters'] for x in pairs),
            'formal_user_input_matches': formal_matches, 'documented_formal_roots': excluded_by_inventory,
            'all_recorded_request_history_contents_checked_not_only_first_request': True,
            'input_packet': {'path': str(input_path), 'sha256': sha(input_path) if input_path.is_file() else None},
            'protocol': {'path': str(protocol_path), 'declared_sha256': protocol_ref.get('sha256'),
                         'observed_sha256': sha(protocol_path) if protocol_path.is_file() else None,
                         'pin_matches': protocol_pinned},
            'task_id': task_id, 'task_identity_matches_observed_user_request': request_identity,
            'observed_request_sha256': textsha(observed_text) if observed_text is not None else None,
            'synthetic_generation_evidence': gen, 'source_copy_evidence': copies,
            'complete_semantic_source_evidence': semantic_proof,
            'formal_attachment_overlap_is_not_sole_formal_label': attachment_overlap,
            'result': {'exists': resultpath.is_file(), 'sha256': sha(resultpath) if resultpath.is_file() else None,
                       'keys': list(result), 'status': result.get('status'), 'stop_reason': result.get('stop_reason'),
                       'success': result.get('success'), 'output_file_count': len(result.get('output_files') or [])},
            'historical_selfbuilt_executor_not_native_equivalent': True,
            'independent_new_test_source_proven': False, 'semantic_approved': False,
            'training_admitted': False, 'publication_approved': False}
        if kind == 'historical_skill_generation_candidate':
            artifacts = []
            for work in [run / 'workspace/output', run / 'workspace/outputs']:
                if not work.is_dir():
                    continue
                for p in work.rglob('*'):
                    if not p.is_file():
                        continue
                    artifact = {'relative_path': str(p.relative_to(run)), 'sha256': sha(p), 'bytes': p.stat().st_size,
                                'python_ast_parses': None, 'skill_frontmatter_present': None}
                    if p.suffix == '.py':
                        try:
                            ast.parse(p.read_text(encoding='utf-8-sig'))
                            artifact['python_ast_parses'] = True
                        except (SyntaxError, UnicodeError):
                            artifact['python_ast_parses'] = False
                    if p.name == 'SKILL.md':
                        artifact['skill_frontmatter_present'] = p.read_text(encoding='utf-8-sig').startswith('---')
                    artifacts.append(artifact)
            row['generation_artifacts'] = artifacts
            row['generation_artifact_count'] = len(artifacts)
            row['static_file_validity_not_resource_execution_success'] = True
            row['existing_historical_validation_receipts'] = existing_validation_evidence(run)
        rows.append(row)
        counts[kind][classification + ':runs'] += 1
        counts[kind][classification + ':pairs'] += len(pairs)
        counts[kind][classification + ':reasoning_responses'] += row['reasoning_responses']
        aggregate['runs'] += 1
        aggregate['response_pairs'] += len(pairs)
        aggregate['formal_text_matched_runs'] += bool(formal_matches)
        aggregate['synthetic_generator_reference_proven_runs'] += gen['generator_hash_matches']
        aggregate['protocol_pin_matches'] += protocol_pinned
        aggregate['task_identity_matches'] += request_identity
        aggregate['all_source_copies_sha_match'] += copies_ok
    index = OUT / 'controlled/raw_scope_review.by_run.jsonl.gz'
    with gzip.open(index, 'wt', encoding='utf-8', newline='\n') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    report = {'schema_version': 'wrd-historical-raw-scope-review-v4', 'status': 'SOURCE_SCOPE_AUDIT_NOT_SEMANTIC_APPROVAL',
              'counts_by_old_scope': {k: dict(v) for k, v in counts.items()}, 'aggregate': dict(aggregate),
              'formal_corpora': formal_sources, 'formal_unique_normalized_user_inputs': len(formal_texts),
              'formal_unique_attachment_hashes': len(formal_attachments),
              'historical_synthetic_probes_not_original_enterprise_source_conversations': True,
              't_number_pattern_not_used_as_formal_evidence': True,
              'absence_of_eval_in_directory_not_used_as_learning_evidence': True,
              'source_audit_sha256': sha(auditpath), 'history_inventory_sha256': sha(inventorypath),
              'controlled_run_index': {'path': str(index.relative_to(OUT)), 'sha256': sha(index), 'bytes': index.stat().st_size},
              'raw_mother_tables_unchanged': True, 'semantic_review_completed': False,
              'training_started': False, 'new_model_calls': 0, 'script_sha256': sha(Path(__file__))}
    report['sse_mechanical_scope_review'] = review_sse(formal_texts, formal_session_refs)
    generations = [r for r in rows if r['old_scope'] == 'historical_skill_generation_candidate']
    report['historical_generation_endstate_summary'] = {
        'runs': len(generations), 'statuses': dict(Counter(r['result']['status'] for r in generations)),
        'artifact_file_aliases_not_unique_examples': sum(r['generation_artifact_count'] for r in generations),
        'python_file_aliases': sum(a['python_ast_parses'] is not None for r in generations for a in r['generation_artifacts']),
        'python_ast_failures': sum(a['python_ast_parses'] is False for r in generations for a in r['generation_artifacts']),
        'existing_validation_receipts': [v for r in generations for v in r['existing_historical_validation_receipts']],
        'full_autonomous_native_pipeline_success_not_asserted': True}
    for path, expected in original_raw_hashes.items():
        assert sha(Path(path)) == expected
    report['raw_mother_table_sha256_unchanged'] = original_raw_hashes
    save(OUT / 'RAW_SCOPE_REVIEW.json', report)
    print(json.dumps({'counts': report['counts_by_old_scope'], 'aggregate': report['aggregate'],
                      'sse_counts': report['sse_mechanical_scope_review']['counts']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
