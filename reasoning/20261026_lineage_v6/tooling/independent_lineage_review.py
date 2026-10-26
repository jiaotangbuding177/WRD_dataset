"""Independent, offline review of the 20 non-make visibility candidates.

No execution, teacher calls, training, or fabricated missing provenance. Actual
messages, exact CAS files and record projections are distinguished from merely
available files. Candidate producer matches are evidence edges, not a claim that
their complete ancestors have been cleared.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import ast
import gzip
import hashlib
import json
from pathlib import Path
import re
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / 'output/20261025_wrd_training_dataset/bundle'
V5 = ROOT / 'output/20261026_wrd_strict226_expansion'
OUT = ROOT / 'output/20261026_wrd_lineage_v6'
SID = re.compile(r'conv_[a-f0-9]{12}')
PATH = re.compile(r'/workspace/[^\s\"\'`;,)\]}]+')
BRIEF = ('id', 'name', 'category', 'source_ids', 'learning_source_ids',
         'development_source_ids', 'steps', 'reuse_reason', 'conditions',
         'additional_conditions', 'conflicts', 'route_signature', 'value_plan')
BODY = ('conversation', 'messages', 'turns', 'requests', 'user_requests',
        'user_input', 'text', 'user_request', 'user_request_preview')


def js(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def rows(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def walk(value, pointer=''):
    if isinstance(value, dict):
        yield pointer, value
        for key, child in value.items():
            yield from walk(child, pointer + '/' + str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, pointer + '/' + str(index))


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def decoded(text):
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(text):
        found = re.search(r'[\[{]', text[pos:])
        if not found:
            break
        start = pos + found.start()
        try:
            value, end = decoder.raw_decode(text, start)
        except ValueError:
            pos = start + 1
            continue
        yield start, end, value
        pos = end


def is_pointer(value):
    if isinstance(value, str):
        return value.startswith(('/workspace/', 'D:\\', 'E:\\', 'D:/', 'E:/'))
    if isinstance(value, dict):
        return bool(value.get('path') or value.get('native_path') or value.get('mount')) and not any(
            value.get(k) for k in ('text', 'messages', 'requests', 'turns'))
    return False


def exact_ids(value):
    result = set()
    for key in ('source_id', 'session_id', 'conversation_id', 'source_ids',
                'learning_source_ids', 'development_source_ids'):
        v = value.get(key)
        if isinstance(v, str) and SID.fullmatch(v):
            result.add(v)
        elif isinstance(v, list):
            result.update(s for s in v if isinstance(s, str) and SID.fullmatch(s))
    return result


def texts(message):
    content = message.get('content')
    if isinstance(content, str):
        yield 0, content
    elif isinstance(content, list):
        for i, block in enumerate(content):
            if isinstance(block, dict) and block.get('type') == 'text':
                yield i, block.get('text', '')


def brief(value):
    return {k: value[k] for k in BRIEF if k in value}


def projection_comparison(target, origin):
    """Only a complete field comparison earns exact projection status."""
    options = [('direct_route_brief', brief(origin))]
    if isinstance(origin.get('route_signature'), dict):
        imported = {k: origin[k] for k in ('id', 'name', 'category', 'source_ids',
                    'route_signature', 'value_plan') if k in origin}
        imported['steps'] = origin['route_signature'].get('steps', [])
        options.append(('legacy_card_to_route_steps_from_signature', imported))
    results = []
    for kind, value in options:
        missing = sorted(set(target) - set(value))
        different = sorted(k for k in target if k in value and target[k] != value[k])
        results.append({'projection': kind, 'missing_fields': missing,
                        'different_fields': different,
                        'matching_fields': sorted(k for k in target if k in value and target[k] == value[k]),
                        'all_consumer_brief_fields_match': not missing and not different})
    return sorted(results, key=lambda r: (not r['all_consumer_brief_fields_match'],
                  len(r['missing_fields']) + len(r['different_fields'])))[0]


def function_pin(path, name):
    text = path.read_text(encoding='utf-8-sig')
    node = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    return {'path': str(path.relative_to(ROOT)).replace('\\', '/'), 'file_sha256': digest(path),
            'function': name, 'line': node.lineno, 'end_line': node.end_lineno,
            'function_source_sha256': sha(ast.get_source_segment(text, node).encode()),
            'current_source_only_not_automatically_historical_runtime_pin': True}


def stamp(value):
    if isinstance(value, (int, float)):
        return float(value) / 1000 if value > 100000000000 else float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
        except ValueError:
            return None
    return None


def creation_values(content, tool_name):
    for lo, hi, value in decoded(content):
        yield 'json_literal', [lo, hi], value
    if tool_name != 'exec':
        return
    # Parse literal data only. No historical code or AST expression is executed.
    candidates = [content]
    match = re.search(r'python(?:3)?\s+-\s+<<[\"\']?(\w+)[\"\']?[^\n]*\n', content)
    if match:
        candidates.append(content[match.end():].split('\n' + match.group(1), 1)[0])
    seen = set()
    for source in candidates:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Dict, ast.List, ast.Tuple)):
                continue
            try:
                value = ast.literal_eval(node)
            except (ValueError, TypeError, SyntaxError):
                continue
            try:
                fingerprint = sha(js(value).encode())
            except (TypeError, ValueError):
                # Historical code may contain tuple-key lookup tables, which
                # are not JSON resource records and are outside this proof.
                continue
            if fingerprint not in seen:
                seen.add(fingerprint)
                yield 'python_ast_literal_data_only', [node.lineno, node.end_lineno], value


def identity_copy_calls(episode):
    """Bounded AST proof for the recorded load→unchanged-routes→dump pattern."""
    found = []
    for i, m in enumerate(episode['messages']):
        for block in m.get('content', []) if isinstance(m.get('content'), list) else []:
            if block.get('type') != 'toolCall' or block.get('name') != 'exec':
                continue
            command = (block.get('arguments') or {}).get('command', '')
            match = re.search(r'python(?:3)?\s+-\s+<<[\"\']?(\w+)[\"\']?[^\n]*\n', command)
            if not match:
                continue
            code = command[match.end():].split('\n' + match.group(1), 1)[0]
            try:
                tree = ast.parse(code)
            except SyntaxError:
                continue
            assignments = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)]
            route_sets = [n for n in assignments if any(isinstance(t, ast.Name) and t.id == 'routes' for t in n.targets)]
            if len(route_sets) != 1 or ast.unparse(route_sets[0].value) != "json.load(open('inputs/existing_routes.json'))":
                continue
            out = [n for n in assignments if any(isinstance(t, ast.Name) and t.id == 'out' for t in n.targets)]
            if len(out) != 1 or not isinstance(out[0].value, ast.Dict):
                continue
            routes_identity = any(isinstance(k, ast.Constant) and k.value == 'routes' and
                                  isinstance(v, ast.Name) and v.id == 'routes'
                                  for k, v in zip(out[0].value.keys, out[0].value.values))
            allowed_calls = {'json.load', 'json.dump', 'open', 'all', 'print', 'len', 'any', 'r.get'}
            call_names = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
            assignments_plain_names = all(all(isinstance(t, ast.Name) for t in n.targets) for n in assignments)
            mutations = any(isinstance(n, (ast.AugAssign, ast.Delete, ast.AnnAssign, ast.For, ast.While,
                                           ast.FunctionDef, ast.Lambda, ast.ImportFrom)) for n in ast.walk(tree))
            if not (routes_identity and call_names <= allowed_calls and assignments_plain_names and not mutations):
                continue
            found.append({'assistant_native_message_index': i,
                'assistant_message_sha256': sha(js(m).encode()),
                'tool_arguments_sha256': sha(js(block.get('arguments')).encode()),
                'python_source_sha256': sha(code.encode()),
                'input_native_path': '/workspace/inputs/existing_routes.json',
                'proof': 'single routes=json.load(existing_routes); out.routes is same Name; no reassignment, field assignment, mutating call, exec/eval or route-transforming loop',
                'calls_whitelist_verified': sorted(call_names),
                'record_copy_is_not_new_semantic_route_creation': True})
    return found


def producer_evidence(episode, protected):
    """Inspect actual inputs before exact creation; no future observation leak."""
    writes = defaultdict(list)
    protected_observations = []
    for i, m in enumerate(episode['messages']):
        if m.get('role') in ('user', 'tool', 'toolResult'):
            for block_index, text in texts(m):
                for lo, hi, value in decoded(text):
                    for pointer, rec in walk(value):
                        ids = exact_ids(rec) & protected
                        body_keys = [k for k in BODY if rec.get(k) and not is_pointer(rec[k])]
                        derived_keys = [k for k in ('steps', 'route_signature', 'value_plan', 'reuse_reason') if rec.get(k)]
                        if ids and (body_keys or derived_keys):
                            protected_observations.append({'native_message_index': i,
                                'message_sha256': sha(js(m).encode()), 'block_index': block_index,
                                'json_character_range': [lo, hi], 'record_pointer': pointer,
                                'record_sha256': sha(js(rec).encode()), 'protected_source_ids': sorted(ids),
                                'evidence_type': 'actual_source_body' if body_keys else 'actual_derived_route_content',
                                'body_keys': body_keys, 'derived_keys': derived_keys,
                                'body_exported': False})
        if m.get('role') != 'assistant' or not isinstance(m.get('content'), list):
            continue
        for block in m['content']:
            if block.get('type') != 'toolCall' or block.get('name') not in ('write', 'exec'):
                continue
            args = block.get('arguments', {})
            if not isinstance(args, dict):
                continue
            content = args.get('content') if block['name'] == 'write' else args.get('command')
            if not isinstance(content, str):
                continue
            results = [(j, result) for j, result in enumerate(episode['messages'][i + 1:], i + 1)
                       if result.get('role') in ('tool', 'toolResult')
                       and result.get('toolCallId') == block.get('id')]
            seen = set()
            for literal_kind, bounds, value in creation_values(content, block['name']):
                for pointer, rec in walk(value):
                    if not rec.get('id') or not ('steps' in rec or 'route_signature' in rec):
                        continue
                    fingerprint = sha(js(rec).encode())
                    if fingerprint in seen:
                        continue
                    seen.add(fingerprint)
                    writes[fingerprint].append({'assistant_native_message_index': i,
                        'assistant_message_sha256': sha(js(m).encode()), 'tool_name': block['name'],
                        'tool_call_id_sha256': sha(str(block.get('id')).encode()),
                        'arguments_sha256': sha(js(args).encode()),
                        'creation_literal_kind': literal_kind,
                        'creation_literal_bounds': bounds, 'record_pointer': pointer,
                        'timestamp': m.get('timestamp'),
                        'result_messages': [{'native_message_index': j, 'is_error': result.get('isError'),
                            'message_sha256': sha(js(result).encode())} for j, result in results],
                        'successful_nonerror_result_recorded': len(results) == 1 and results[0][1].get('isError') is False})
    return writes, protected_observations


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    controlled = OUT / 'controlled'
    controlled.mkdir(exist_ok=True)
    source_paths = [V5 / 'VISIBILITY_REVIEW.json', BUNDLE / 'canonical/native_episodes.jsonl.gz',
                    BUNDLE / 'archive/file_index.jsonl', BUNDLE / 'catalog/episodes.jsonl',
                    ROOT / 'output/20261025_wrd_fullchain_reaudit/controlled_linkage/input_artifacts.jsonl.gz',
                    ROOT / 'output/20261013_eval250_review/release/learning/evolution_index.jsonl',
                    ROOT / 'output/20261025_wrd_reasoning_recovery_v4/controlled/historical_native_sessions.jsonl.gz']
    source_before = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in source_paths}
    review = json.loads(source_paths[0].read_text(encoding='utf-8'))
    wanted = set(review['pending_positive_candidate_episode_ids'])
    all_episodes = {r['episode_id']: r for r in rows(source_paths[1])}
    historical_episodes = {r['episode_id']: r for r in rows(source_paths[6])}
    all_episodes.update(historical_episodes)
    episodes = {eid: e for eid, e in all_episodes.items() if eid in wanted and e['kind'] != 'make'}
    assert Counter(e['kind'] for e in episodes.values()) == {'prepare': 16, 'screen': 1, 'legacy': 3}
    contracts = sorted((ROOT / 'benchmark').glob('*/contracts/evaluation.jsonl'))
    protected = {r['session_id'] for p in contracts for r in rows(p)}
    evolution = {r['source_id']: r for r in rows(source_paths[5]) if r['source_id'] not in protected}
    artifacts = defaultdict(list)
    for a in rows(source_paths[4]):
        if a['episode_id'] in episodes:
            artifacts[a['episode_id']].append(a)
    routes = {eid: next((a['content'] for a in arts if a['artifact_name'] == 'task_route.json'), None)
              for eid, arts in artifacts.items()}
    route_ids = {r['id'] for r in routes.values() if r}
    aliases, object_aliases = defaultdict(list), defaultdict(list)
    origin_files = []
    for a in rows(source_paths[2]):
        logical = a['logical_path']
        match = re.match(r'episodes/(ep_[a-f0-9]+)/', logical)
        if match and match.group(1) in episodes:
            aliases[match.group(1)].append(a)
        if (logical.endswith(('/outputs/routes.json', '/outputs/screen.json', '/outputs/cards.json',
                             '/checked_cards.json')) or '/cards/' in logical or logical == 'pipeline/routes.json'):
            origin_files.append(a)
        object_aliases[a['sha256']].append(logical)
    origin_records = []
    cas_checked = {}
    for a in origin_files:
        p = BUNDLE / 'archive' / a['object']
        if not p.is_file():
            continue
        if a['sha256'] not in cas_checked:
            cas_checked[a['sha256']] = digest(p) == a['sha256'] and p.stat().st_size == a['bytes']
        raw = p.read_bytes()
        if not any(rid.encode() in raw for rid in route_ids):
            continue
        try:
            value = json.loads(raw.decode('utf-8-sig'))
        except (ValueError, UnicodeError):
            continue
        for pointer, record in walk(value):
            if record.get('id') in route_ids and ('steps' in record or 'route_signature' in record):
                producer = re.match(r'episodes/(ep_[a-f0-9]+)/workspace/outputs/', a['logical_path'])
                origin_records.append({'alias': a, 'pointer': pointer, 'record': record,
                                       'producer_episode_id': producer.group(1) if producer else None})
    historical_seen = set()
    for hid, h in historical_episodes.items():
        event_pin = h.get('source_events') or {}
        event_sha = event_pin.get('sha256')
        if not event_sha or event_sha not in object_aliases:
            continue
        event_object = BUNDLE / 'archive/objects' / event_sha[:2] / event_sha
        if not event_object.is_file():
            continue
        assert digest(event_object) == event_sha and event_object.stat().st_size == event_pin['bytes']
        cas_checked[event_sha] = True
        for i, message in enumerate(h['messages']):
            for block in message.get('content', []) if isinstance(message.get('content'), list) else []:
                if block.get('type') != 'toolCall' or block.get('name') not in ('write', 'exec'):
                    continue
                args = block.get('arguments') or {}
                content = args.get('content') if block['name'] == 'write' else args.get('command')
                if not isinstance(content, str):
                    continue
                for kind, bounds, value in creation_values(content, block['name']):
                    for pointer, record in walk(value):
                        fingerprint = sha(js(record).encode())
                        if (record.get('id') not in route_ids or
                            not ('steps' in record or 'route_signature' in record) or
                            (hid, fingerprint) in historical_seen):
                            continue
                        historical_seen.add((hid, fingerprint))
                        origin_records.append({'alias': {'logical_path': object_aliases[event_sha][0],
                            'sha256': event_sha},
                            'pointer': 'native_message/' + str(i) + '/literal' + pointer,
                            'record': record, 'producer_episode_id': hid,
                            'historical_source_events_cas_verified': True,
                            'literal_kind': kind})
    producer_input_aliases = {}
    producer_ids = {o['producer_episode_id'] for o in origin_records if o['producer_episode_id']}
    for a in rows(source_paths[2]):
        match = re.fullmatch(r'episodes/(ep_[a-f0-9]+)/workspace/inputs/existing_routes.json', a['logical_path'])
        if match and match.group(1) in producer_ids:
            producer_input_aliases[match.group(1)] = a
    producer_cache = {}
    reports = []; counts = Counter()
    with gzip.open(controlled / 'independent_nonmake_context_evidence.jsonl.gz', 'wt', encoding='utf-8', newline='\n') as body:
        for eid, e in sorted(episodes.items()):
            file_rows = aliases[eid]
            by_native = {}
            for a in file_rows:
                marker = '/workspace/'
                if marker in a['logical_path']:
                    by_native['/workspace/' + a['logical_path'].split(marker, 1)[1]] = a
            initial = e['messages'][0]
            initial_text = '\n'.join(t for _, t in texts(initial))
            # Availability names are kept separately from original user context.
            chunks = initial_text.split('用户提供的上下文：\n', 1)
            actual_context = chunks[1].split('\n\n用户任务：\n', 1)[0] if len(chunks) == 2 else initial_text
            actual_context_ids = set(SID.findall(actual_context))
            calls = []; observations = []; leaves = []; input_records = []
            actual_read_paths = set()
            for i, m in enumerate(e['messages']):
                if m.get('role') == 'assistant' and isinstance(m.get('content'), list):
                    for b in m['content']:
                        if b.get('type') != 'toolCall':
                            continue
                        args = b.get('arguments', {})
                        native_paths = sorted(set(PATH.findall(js(args))))
                        name = b.get('name')
                        # A write path, ls directory, or path mentioned inside
                        # generated code is not automatically an external read.
                        if name == 'read' and isinstance(args, dict) and isinstance(args.get('path'), str):
                            input_candidates = [args['path']]
                            path_role = 'explicit_native_read'
                        elif name == 'exec':
                            input_candidates = [p for p in native_paths if p.startswith('/workspace/inputs/')]
                            path_role = 'exec_lexical_input_reference_requires_dataflow_review'
                        elif name == 'ls':
                            input_candidates = []
                            path_role = 'directory_availability_listing_not_file_body_dependency'
                        else:
                            input_candidates = []
                            path_role = 'write_or_other_reference_not_automatically_read'
                        actual_read_paths.update(input_candidates)
                        calls.append({'native_message_index': i, 'tool': b.get('name'),
                                      'tool_call_id': b.get('id'), 'arguments_sha256': sha(js(args).encode()),
                                      'explicit_paths': native_paths, 'path_role': path_role,
                                      'input_read_candidates': input_candidates})
                if m.get('role') not in ('user', 'tool', 'toolResult'):
                    continue
                for block_index, text in texts(m):
                    for lo, hi, value in decoded(text):
                        for pointer, rec in walk(value):
                            ids = exact_ids(rec)
                            if not ids:
                                continue
                            body_keys = [k for k in BODY if rec.get(k) and not is_pointer(rec[k])]
                            observations.append({'native_message_index': i, 'content_block_index': block_index,
                                'message_role': m.get('role'), 'message_sha256': sha(js(m).encode()),
                                'json_character_range': [lo, hi], 'record_pointer': pointer,
                                'record_sha256': sha(js(rec).encode()), 'source_ids': sorted(ids),
                                'protected_ids': sorted(ids & protected),
                                'actual_body_keys': body_keys,
                                'path_pointer_keys': [k for k in BODY if rec.get(k) and is_pointer(rec[k])]})
            relevant = set(actual_read_paths)
            # Full priority-source/route files were delivered even when only
            # an offset-limited portion is observed. Preserve that distinction.
            relevant.update('/workspace/inputs/' + a['artifact_name'] for a in artifacts[eid])
            for path in sorted(relevant):
                a = by_native.get(path)
                if not a:
                    input_records.append({'native_path': path, 'exact_cas_alias_found': False})
                    continue
                p = BUNDLE / 'archive' / a['object']
                exists = p.is_file()
                ok = exists and digest(p) == a['sha256'] and p.stat().st_size == a['bytes']
                cas_checked[a['sha256']] = ok
                item = {'native_path': path, 'logical_path': a['logical_path'],
                        'object': a['object'], 'sha256': a['sha256'], 'bytes': a['bytes'],
                        'cas_hash_size_verified': ok, 'original_source_sha256': a['source_sha256'],
                        'credential_redacted': a.get('credential_redacted'),
                        'source_bytes_equal_cas_bytes': a['source_sha256'] == a['sha256']}
                try:
                    value = json.loads(p.read_text(encoding='utf-8-sig')) if ok else None
                except (UnicodeError, ValueError):
                    value = None
                if value is not None:
                    item['json_sorted_compact_sha256'] = sha(js(value).encode())
                    item['all_named_source_ids'] = sorted({sid for _, rec in walk(value) for sid in exact_ids(rec)})
                    item['all_named_protected_source_ids'] = sorted(set(item['all_named_source_ids']) & protected)
                    for pointer, rec in walk(value):
                        ids = exact_ids(rec)
                        body_keys = [k for k in BODY if rec.get(k) and not is_pointer(rec[k])]
                        if ids and body_keys:
                            leaves.append({'native_path': path, 'pointer': pointer,
                                'record_sha256': sha(js(rec).encode()), 'source_ids': sorted(ids),
                                'protected_ids': sorted(ids & protected), 'body_keys': body_keys,
                                'all_named_sources_in_nonprotected_evolution_index': ids <= set(evolution),
                                'exact_source_text_pin_not_inferred_from_id': True})
                input_records.append(item)
            target = brief(routes[eid]) if routes.get(eid) else None
            origins = []
            if target:
                for origin in origin_records:
                    if origin['record'].get('id') != target['id']:
                        continue
                    cmp = projection_comparison(target, origin['record'])
                    peid = origin['producer_episode_id']
                    production = []
                    copy_edges = []
                    if peid in all_episodes:
                        if peid not in producer_cache:
                            producer_cache[peid] = producer_evidence(all_episodes[peid], protected)
                        writes, producer_observations = producer_cache[peid]
                        for creation in writes.get(sha(js(origin['record']).encode()), []):
                            before = [x for x in producer_observations
                                      if x['native_message_index'] < creation['assistant_native_message_index']]
                            consumer_start = stamp(e['messages'][0].get('timestamp'))
                            created = stamp(creation['timestamp'])
                            production.append({**creation,
                                'created_before_consumer_first_message': created < consumer_start
                                    if created is not None and consumer_start is not None else None,
                                'protected_observations_before_creation': before,
                                'proven_mixed_protected_context_before_creation': bool(before)})
                        input_alias = producer_input_aliases.get(peid)
                        if input_alias:
                            input_path = BUNDLE / 'archive' / input_alias['object']
                            copy_ok = digest(input_path) == input_alias['sha256'] and input_path.stat().st_size == input_alias['bytes']
                            assert copy_ok
                            cas_checked[input_alias['sha256']] = copy_ok
                            source_records = [(pointer, rec) for pointer, rec in walk(json.loads(input_path.read_text(encoding='utf-8-sig')))
                                              if sha(js(rec).encode()) == sha(js(origin['record']).encode())]
                            for pointer, rec in source_records:
                                for call in identity_copy_calls(all_episodes[peid]):
                                    copy_edges.append({**call, 'input_cas_alias': input_alias['logical_path'],
                                        'input_cas_sha256': input_alias['sha256'], 'input_cas_hash_size_verified': copy_ok,
                                        'input_json_pointer': pointer, 'identical_record_sha256': sha(js(rec).encode()),
                                        'input_source_ancestors_still_need_review': True,
                                        'do_not_newly_taint_unchanged_record_from_future_or_other_record_context': True})
                    origins.append({'source_alias': origin['alias']['logical_path'],
                        'file_sha256': origin['alias']['sha256'], 'json_pointer': origin['pointer'],
                        'record_sha256': sha(js(origin['record']).encode()),
                        'producer_episode_id': peid,
                        'producer_canonical_available': peid in all_episodes if peid else False,
                        'exact_record_in_actual_creation_call': production,
                        'proven_record_identity_copy_edges': copy_edges,
                        'creation_is_semantic_original_not_record_copy_proven': False,
                        'actual_dispatch_lineage_link_proven': False,
                        'unique_earliest_matching_version_proven': False,
                        'matching_writer_mixed_context_does_not_alone_prove_consumer_protected_ancestor': True,
                        **cmp,
                        'producer_complete_ancestor_closure_not_established_by_record_match': True})
            prior = {k: {'type': type(v).__name__, 'empty': not bool(v),
                         'sha256': sha(js(v).encode()),
                         'named_source_ids': sorted({sid for _, rec in walk(v) for sid in exact_ids(rec)}),
                         'protected_id_mentions': sorted(set(SID.findall(js(v))) & protected)}
                     for k, v in (routes.get(eid) or {}).items()
                     if k.startswith('previous_') or k in ('existing_tasks', 'full_catalog')}
            protected_observations = [x for x in observations if x['protected_ids'] and x['actual_body_keys']]
            protected_inputs = [x for x in input_records if x.get('all_named_protected_source_ids')]
            summary = {'episode_id': eid, 'kind': e['kind'], 'native_verified': e['native_verified'],
                'canonical_episode_sorted_sha256': sha(js(e).encode()), 'message_count': len(e['messages']),
                'initial_user_sha256': sha(initial_text.encode()), 'initial_context_empty': actual_context == '',
                'initial_actual_context_source_ids': sorted(actual_context_ids),
                'initial_actual_context_protected_ids': sorted(actual_context_ids & protected),
                'tool_calls': calls, 'actual_observation_records': observations,
                'explicit_read_or_write_paths_not_all_assumed_reads': sorted(actual_read_paths),
                'cas_resource_receipts': input_records, 'source_projection_records': leaves,
                'route_projection_sha256': sha(js(target).encode()) if target else None,
                'route_projection_source_ids': target.get('source_ids', []) if target else [],
                'upstream_route_record_matches': origins, 'continuation_fields': prior,
                'protected_body_positive_observations': len(protected_observations),
                'protected_id_metadata_in_relevant_input_files': len(protected_inputs),
                'direct_context_only_evolution_is_not_complete_lineage_proof': True,
                'arbitrary_exec_dynamic_file_dependencies_completely_proven': False,
                'full_training_admission_proven_by_this_independent_report': False,
                'historical_trace_not_current_native_pipeline': not e['native_verified'],
                'do_not_delete_mixed_context_to_admit_later_teacher_targets': True}
            reports.append(summary)
            counts[e['kind'] + ':episodes'] += 1
            counts['exact_route_projection_matches'] += sum(x['all_consumer_brief_fields_match'] for x in origins)
            counts['episodes_with_exact_route_projection_match'] += int(any(x['all_consumer_brief_fields_match'] for x in origins))
            counts['episodes_with_exact_projection_and_prior_mixed_matching_literal_write'] += int(any(
                x['all_consumer_brief_fields_match'] and any(c['proven_mixed_protected_context_before_creation']
                for c in x['exact_record_in_actual_creation_call']) for x in origins))
            counts['episodes_with_proven_identity_route_copy_edge'] += int(any(
                x['all_consumer_brief_fields_match'] and x['proven_record_identity_copy_edges'] for x in origins))
            counts['positive_protected_body_observations'] += len(protected_observations)
            counts['actual_tool_calls'] += len(calls)
            counts['actual_user_or_tool_observation_json_records'] += len(observations)
            body.write(js({'episode_id': eid, 'system': e['system'], 'messages': e['messages'],
                'input_artifacts': artifacts[eid], 'source_context_evidence': summary}) + '\n')
    source_after = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in source_paths}
    assert source_before == source_after
    pins = [function_pin(ROOT / 'research/workflow/stages.py', n) for n in ('_route_brief', 'prepare_task')]
    pins += [function_pin(ROOT / 'pipeline.py', 'apply_routes'),
             function_pin(ROOT / 'research/workflow/legacy.py', 'import_legacy')]
    report = {'schema_version': 'wrd-independent-nonmake-lineage-review-v6',
        'status': 'INDEPENDENT_EVIDENCE_REVIEW_NOT_AUTOMATIC_ADMISSION',
        'scope': '16 prepare + one historical no-skill actor labelled screen + three historical actor/judge traces',
        'counts': dict(counts), 'cas_objects_checked': len(cas_checked),
        'cas_hash_size_failures': [k for k, v in cas_checked.items() if not v],
        'all_original_source_hashes_unchanged': source_before == source_after,
        'source_sha256': source_before,
        'protected_contract_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in contracts},
        'projection_contract_current_code_pins': pins,
        'matching_writer_proof_qualification': {
            'earlier_four_hard_ancestor_wording_corrected': True,
            'actual_matching_literal_write_and_prior_observation_verified': True,
            'actual_consumer_dispatch_link_or_unique_earliest_semantic_creation_still_required': True,
            'do_not_union_all_matching_producer_alternatives_as_ancestors': True},
        'proof_standard': [
            'Actual initial user context and each native tool return are causal inputs; directory availability names are a separate field.',
            'Byte-identical CAS and exact record projections support edges; source id absence alone never establishes safe ancestry.',
            'Current _route_brief has a field allowlist. A full task_route hash cannot equal a card because deterministic projection and continuation fields are added.',
            'apply_routes unions source_ids, conditions and conflicts into old routes; steps are not overwritten. Every merged component needs its own ancestor.',
            'Legacy card import maps steps from route_signature.steps. Match all consumer fields or explicitly mark a partial candidate edge.',
            'Full task_sources contents delivered are distinguished from the subset actually returned under offset/truncation.',
            'Existing_tasks and previous preparation/review fields require recursive producer closure even if their direct source_ids are nonprotected.',
            'Full producer prefix must precede resource creation and must be source-safe; exact route content alone does not cleanse a mixed-context teacher.',
            'A verified unchanged record copy is an identity edge to its input, not a new semantic creation; do not newly taint old field values from unrelated or future context.',
            'A static generic protocol can close as a pinned code leaf; no need to invent a business producer for every generic instruction.',
            'Historical no_skill/judge traces are not A-screen demonstrations or current native full-pipeline trajectories.'
        ],
        'episodes': reports,
        'controlled_evidence': {'path': 'controlled/independent_nonmake_context_evidence.jsonl.gz',
            'sha256': digest(controlled / 'independent_nonmake_context_evidence.jsonl.gz'),
            'body_included_only_in_controlled_file': True},
        'complete_training_rows_admitted_by_this_review': 0,
        'training_started': False, 'model_weights_loaded': False, 'gpu_used': False,
        'new_business_or_native_agent_runs': 0, 'new_teacher_actor_judge_calls': 0,
        'script_sha256': digest(Path(__file__))}
    (OUT / 'INDEPENDENT_NONMAKE_REVIEW.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(js({'counts': dict(counts), 'cas_checked': len(cas_checked), 'cas_failures': len(report['cas_hash_size_failures']),
              'training_admission': 0, 'report_sha256': digest(OUT / 'INDEPENDENT_NONMAKE_REVIEW.json')}))


if __name__ == '__main__':
    main()
