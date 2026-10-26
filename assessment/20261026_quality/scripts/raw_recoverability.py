"""Audit saved original carrier recoverability, without execution or admission.

Reads v7 supplemental ledgers and exactly one authorized C-side session file.
Outputs metadata/hashes/counts only; no prompt, reasoning, or business body is
copied into public reports. Native, historical custom runners, and Codex remain
separate conditions. This script does not touch SQLite, containers, or models.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path('D:/skillloop')
V7 = ROOT / 'output/20261026_wrd_raw_census_v7'
V4 = ROOT / 'output/20261025_wrd_reasoning_recovery_v4'
BUNDLE = ROOT / 'output/20261025_wrd_training_dataset/bundle'
OUT = ROOT / 'output/20261026_wrd_quality_v8'
SID = re.compile(r'conv_[0-9a-f]{12}')
EXACT_CODEX = Path('C:/Users/22142/.codex/sessions/2026/10/23/rollout-2026-10-23T01-11-23-01a16469-7614-7e01-ba76-1ad2d9707177_01a16498-9504-7342-80c4-b714199ce710.jsonl')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def objsha(value):
    return sha(canonical(value).encode('utf-8'))


def lines(path):
    op = gzip.open if Path(path).suffix == '.gz' else open
    with op(path, 'rt', encoding='utf-8-sig') as f:
        for n, text in enumerate(f, 1):
            if text.strip():
                yield n, json.loads(text)


def load(path, default=None):
    try:
        op = gzip.open if Path(path).suffix == '.gz' else open
        with op(path, 'rt', encoding='utf-8-sig') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_rows(path, rows):
    with gzip.open(path, 'wt', encoding='utf-8', compresslevel=3) as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')


def schema_names(value):
    items = value.get('tools', []) if isinstance(value, dict) else value if isinstance(value, list) else []
    valid = set()
    invalid = 0
    for tool in items:
        if not isinstance(tool, dict):
            invalid += 1
            continue
        fn = tool.get('function', tool)
        if isinstance(fn, dict) and isinstance(fn.get('name'), str) and isinstance(fn.get('parameters', fn.get('input_schema')), dict):
            valid.add(fn['name'])
        else:
            invalid += 1
    return valid, invalid


def nonempty_reasoning(message):
    values = []
    if not isinstance(message, dict):
        return values
    for field in ['reasoning_content', 'reasoning', 'thinking']:
        if isinstance(message.get(field), str) and message[field]:
            values.append((field, message[field]))
    for item in message.get('content', []) if isinstance(message.get('content'), list) else []:
        if isinstance(item, dict) and item.get('type') in {'thinking', 'reasoning'}:
            for field in ['thinking', 'reasoning', 'text']:
                if isinstance(item.get(field), str) and item[field]:
                    values.append(('block:' + item['type'] + ':' + field, item[field]))
    return values


def openai_history_quality(request):
    messages = request.get('messages', []) if isinstance(request, dict) else []
    calls, outputs = set(), set()
    names = set()
    reasoning = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get('role') == 'assistant':
            reasoning.extend(nonempty_reasoning(message))
            for call in message.get('tool_calls') or []:
                if call.get('id'):
                    calls.add(call['id'])
                if isinstance(call.get('function'), dict) and call['function'].get('name'):
                    names.add(call['function']['name'])
        if message.get('role') in {'tool', 'toolResult'}:
            cid = message.get('tool_call_id', message.get('toolCallId'))
            if cid:
                outputs.add(cid)
    schemas, invalid = schema_names(request)
    return {'request_messages': len(messages), 'request_tools_valid_schema_names': sorted(schemas), 'request_invalid_or_truncated_tool_entries': invalid, 'history_tool_call_ids': len(calls), 'history_tool_result_ids': len(outputs), 'history_unmatched_tool_results': len(outputs - calls), 'history_pending_tool_calls': len(calls - outputs), 'history_called_tool_names_without_schema': sorted(names - schemas), 'history_reasoning_fields': len(reasoning)}


def unwrap_request(value):
    if not isinstance(value, dict):
        return None
    if isinstance(value.get('messages'), list):
        return value
    for field in ['body', 'request', 'payload']:
        child = value.get(field)
        if isinstance(child, str):
            try:
                child = json.loads(child)
            except ValueError:
                continue
        if isinstance(child, dict) and isinstance(child.get('messages'), list):
            return child
    return None


def find_request(response_path):
    candidates = ['forwarded_request.raw.json', 'request.raw.json', 'request.json', 'request.json.gz', 'native_request.raw.json']
    # Historical metering probes use 02.response.raw.json + 02.request.json.
    # A missing generic request.json is not evidence that the original request
    # was absent when its ordinal-prefixed recording is present.
    match = re.match(r'^(.*?)(?:response(?:\.raw|_public)?)(?:\.json)?(?:\.gz)?$', response_path.name)
    if match and match.group(1):
        prefix = match.group(1)
        candidates = [prefix + n for n in ['request.json', 'request.json.gz', 'request.raw.json']] + candidates
    for name in candidates:
        p = response_path.parent / name
        if p.is_file():
            value = unwrap_request(load(p))
            if value is not None:
                return p, value
    return None, None


def sse_response(text):
    content, reasoning, tc = [], [], {}
    ids, models, finishes = set(), set(), []
    counts = Counter()
    for rawline in text.split('\n'):
        if not rawline.startswith('data:'):
            continue
        raw = rawline[5:].strip()
        if raw == '[DONE]':
            counts['done_frames'] += 1
            continue
        try:
            frame = json.loads(raw)
        except ValueError:
            counts['malformed_json_frames'] += 1
            continue
        counts['json_frames'] += 1
        if frame.get('id'):
            ids.add(frame['id'])
        if frame.get('model'):
            models.add(frame['model'])
        if frame.get('error'):
            counts['error_frames'] += 1
        for choice in frame.get('choices') or []:
            delta = choice.get('delta') or choice.get('message') or {}
            if isinstance(delta.get('content'), str):
                content.append(delta['content'])
            if isinstance(delta.get('reasoning_content'), str):
                reasoning.append(delta['reasoning_content'])
            for call in delta.get('tool_calls') or []:
                index = call.get('index', 0)
                entry = tc.setdefault(index, {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}})
                if call.get('id'):
                    entry['id'] += call['id']
                for field in ['name', 'arguments']:
                    v = call.get('function', {}).get(field)
                    if isinstance(v, str):
                        entry['function'][field] += v
            if choice.get('finish_reason') is not None:
                finishes.append(choice['finish_reason'])
    if not counts['json_frames']:
        return None
    message = {'role': 'assistant', 'content': ''.join(content)}
    if reasoning:
        message['reasoning_content'] = ''.join(reasoning)
    if tc:
        message['tool_calls'] = [tc[k] for k in sorted(tc)]
    return {'id': next(iter(ids)) if len(ids) == 1 else None, 'model': next(iter(models)) if len(models) == 1 else None, 'choices': [{'message': message, 'finish_reason': finishes[-1] if finishes else None}], '_stream_quality': dict(counts), '_stream_response_ids': sorted(ids)}


def baseline_metadata():
    canonical_ids = {r['episode_id'] for _, r in lines(BUNDLE / 'canonical/native_episodes.jsonl.gz')}
    native_ids, hashes, by_id = set(), set(), {}
    for _, row in lines(V7 / 'indexes/episodes.all.jsonl.gz'):
        if row['episode_id'] not in canonical_ids:
            continue
        meta = row.get('raw_native_session') or {}
        if meta.get('native_session_id'):
            native_ids.add(meta['native_session_id'])
            by_id[meta['native_session_id']] = row['episode_id']
        if meta.get('sha256'):
            hashes.add(meta['sha256'])
    old_native = load(V4 / 'HISTORICAL_NATIVE_RECOVERY_REPORT.json', {})
    v4_ids = {r.get('native_session_id') for r in old_native.get('source_inventory', []) if r.get('native_session_id')}
    v4_hashes = {r.get('sha256') for r in old_native.get('source_inventory', []) if r.get('sha256')}
    provider_ids, message_hashes, reasoning_hashes, pair_hashes = set(), set(), set(), set()
    prior_pair_scope, prior_pair_condition = {}, {}
    for name in ['raw_pairs.all.jsonl.gz', 'sse_reasoning_pairs.all.jsonl.gz']:
        for _, row in lines(V4 / 'controlled' / name):
            response = row.get('original_response') or {}
            if response.get('id'):
                provider_ids.add(response['id'])
                prior_pair_scope[response['id']] = row.get('role_scope')
                prior_pair_condition[response['id']] = row.get('historical_condition')
            pair_hashes.add(objsha(response))
            for choice in response.get('choices') or []:
                msg = choice.get('message') or {}
                message_hashes.add(objsha(msg))
                reasoning_hashes.update(sha(v.encode()) for _, v in nonempty_reasoning(msg))
    labels = {r['episode_id']: r for _, r in lines(V4 / 'controlled/native_source_split.labels.jsonl.gz')}
    prior_run_labels = {r['run_path']: r for _, r in lines(V4 / 'controlled/raw_scope_review.by_run.jsonl.gz')}
    historical_labels = {r['native_session_id']: {k: r.get(k) for k in ['role_scope', 'source_ids', 'source_split', 'benchmark_exposed']} for _, r in lines(V4 / 'controlled/historical_native_sessions.jsonl.gz')}
    return {'canonical_ids': canonical_ids, 'native_ids': native_ids, 'native_hashes': hashes, 'by_native_id': by_id, 'v4_native_ids': v4_ids, 'v4_native_hashes': v4_hashes, 'v4_provider_ids': provider_ids, 'v4_message_hashes': message_hashes, 'v4_reasoning_hashes': reasoning_hashes, 'v4_response_hashes': pair_hashes, 'labels': labels, 'prior_run_labels': prior_run_labels, 'historical_labels': historical_labels, 'prior_pair_scope': prior_pair_scope, 'prior_pair_condition': prior_pair_condition}


def audit_native(path, raw, baseline):
    messages, parse_errors = [], []
    sid = None
    for n, line in enumerate(raw.decode('utf-8-sig').split('\n'), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            parse_errors.append(n)
            continue
        if row.get('type') == 'session' and sid is None:
            sid = row.get('id')
        if row.get('type') == 'message' and isinstance(row.get('message'), dict):
            messages.append((n, row['message']))
    episode = path.parent.parent
    packet = load(episode / 'request.json', {})
    execution = load(episode / 'execution.json', {})
    tool_file = episode / 'openclaw_transport/evidence/tools.json'
    tools, invalid = schema_names(load(tool_file, []))
    api_schemas = set()
    api_contexts = []
    for api_file in sorted((episode / 'openclaw_transport/api_audit').glob('*/native_request.raw.json')):
        api_request = unwrap_request(load(api_file))
        if api_request is None:
            continue
        names, bad = schema_names(api_request)
        api_schemas.update(names)
        systems = [m.get('content') for m in api_request.get('messages', []) if m.get('role') == 'system' and isinstance(m.get('content'), str)]
        api_contexts.append({'source_path': str(api_file), 'sha256': sha(api_file.read_bytes()), 'message_count': len(api_request['messages']), 'system_characters': sum(map(len, systems)), 'system_text_sha256': [sha(t.encode()) for t in systems], 'system_has_truncation_marker': any('<truncated>' in t or '[Truncated]' in t for t in systems), 'valid_tool_schema_names': sorted(names), 'invalid_schema_entries': bad, 'tools_array_sha256': objsha(api_request.get('tools'))})
    call_ids, result_ids, called_names = set(), set(), set()
    reasons, visible_chars, roles, stops = [], 0, Counter(), Counter()
    model_receipts = []
    error_results = 0
    declared_reason_fields = Counter()
    for n, msg in messages:
        roles[msg.get('role')] += 1
        if msg.get('role') == 'assistant':
            reasons.extend(nonempty_reasoning(msg))
            model_receipts.append({'source_line_1based': n, 'response_id': msg.get('responseId'), 'separate_readable_reasoning_characters': sum(len(v) for _, v in nonempty_reasoning(msg))})
            stops[str(msg.get('stopReason'))] += 1
            for item in msg.get('content', []) if isinstance(msg.get('content'), list) else []:
                if not isinstance(item, dict):
                    continue
                if item.get('type') == 'text' and isinstance(item.get('text'), str):
                    visible_chars += len(item['text'])
                    if re.search(r'"(?:reason|reasoning|replaced_work|repair_notes)"\s*:', item['text']):
                        declared_reason_fields['assistant_visible_structured_reason_or_repair_field_messages'] += 1
                if item.get('type') == 'toolCall':
                    if item.get('id'):
                        call_ids.add(item['id'])
                    if item.get('name'):
                        called_names.add(item['name'])
        if msg.get('role') == 'toolResult':
            if msg.get('toolCallId'):
                result_ids.add(msg['toolCallId'])
            details = msg.get('details') or {}
            error_results += bool(msg.get('isError') or isinstance(details, dict) and details.get('exitCode') not in [None, 0])
    result = load(episode / 'result.json', {})
    receipt = load(episode / 'episode_receipt.json', {})
    old_ep = baseline['by_native_id'].get(sid)
    label = baseline['labels'].get(old_ep, {})
    fixed = ROOT / 'research/data_prep/wrd_training/resources/native_coding_tools_97a0.json'
    fixed_names, _ = schema_names(load(fixed, []))
    image_pin = execution.get('image') == 'sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
    return {'native_session_id': sid, 'valid_session_header_present': bool(sid), 'native_named_artifact_without_session_header': not bool(sid), 'source_path': str(path), 'source_sha256': sha(raw), 'decoded_content_sha256': sha(raw), 'bytes': len(raw), 'message_roles': dict(roles), 'messages': len(messages), 'assistant_responses': roles['assistant'], 'assistant_model_response_receipts': model_receipts, 'assistant_visible_text_characters': visible_chars, 'separate_readable_reasoning_fields': len(reasons), 'separate_readable_reasoning_characters': sum(len(v) for _, v in reasons), 'readable_reasoning_sha256': sorted({sha(v.encode()) for _, v in reasons}), 'visible_process_explanation_indicators': dict(declared_reason_fields), 'malformed_json_line_numbers': parse_errors, 'request_packet_file_present': (episode / 'request.json').is_file(), 'native_user_prompt_present': bool(roles['user']), 'recorded_stage': packet.get('stage'), 'recorded_task_id': packet.get('task_id'), 'recorded_protocol': packet.get('protocol'), 'recorded_execution_condition': {k: execution.get(k) for k in ['backend', 'custom_agent_loop', 'image', 'openclaw_version', 'model'] if k in execution}, 'recorded_status': result.get('status', receipt.get('status')), 'assistant_stop_reasons': dict(stops), 'tool_call_ids': len(call_ids), 'tool_result_ids': len(result_ids), 'tool_calls_without_recorded_result': len(call_ids - result_ids), 'tool_results_without_recorded_call': len(result_ids - call_ids), 'tool_error_or_nonzero_exit_results': error_results, 'called_tool_names': sorted(called_names), 'valid_original_schema_names': sorted(tools), 'called_names_without_original_recorded_schema': sorted(called_names - tools), 'same_episode_original_API_contexts': api_contexts, 'called_names_without_original_or_same_episode_API_schema': sorted(called_names - tools - api_schemas), 'pinned_native_image_for_saved_factory_schema': image_pin, 'called_names_without_original_or_matching_pinned_factory_schema': sorted(called_names - tools - api_schemas - (fixed_names if image_pin else set())), 'invalid_or_truncated_schema_entries': invalid, 'same_native_session_as_old1763': sid in baseline['native_ids'], 'same_bytes_as_old1763_archive': sha(raw) in baseline['native_hashes'], 'already_in_v4_historical_native_inventory': sid in baseline['v4_native_ids'] or sha(raw) in baseline['v4_native_hashes'], 'prior_original226_scope_label': label.get('scope_label', 'not_assessed_in_this_recoverability_audit'), 'prior_observed_protected_source_ids': label.get('model_observed_protected_source_body_ids', []), 'prior_direct_protected_source_ids': label.get('direct_formal_source_ids', []), 'no_source_admission_performed': True}


def audit_codex(path, controlled):
    before_stat = path.stat()
    raw = path.read_bytes()
    counts, item_types, event_types = Counter(), Counter(), Counter()
    call_ids, result_ids, summaries = set(), set(), {}
    session_meta = {}
    marker_turns, current_turn = set(), None
    marker_lines = []
    rows = []
    target = '20261023_codex_assisted_resource_repair'
    for n, line in enumerate(raw.decode('utf-8-sig').split('\n'), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            counts['malformed_json_lines'] += 1
            continue
        typ, value = record.get('type'), record.get('payload') or {}
        counts['json_lines'] += 1
        if typ == 'session_meta':
            session_meta = {k: value.get(k) for k in ['id', 'session_id', 'forked_from_id', 'history_mode', 'model_provider', 'cli_version']}
        if typ == 'event_msg':
            event_types[value.get('type')] += 1
            if value.get('type') == 'task_started':
                current_turn = value.get('turn_id')
            item = value.get('item') or {}
            if value.get('type') == 'item_completed' and item.get('type') == 'Reasoning':
                counts['event_reasoning_items'] += 1
                counts['event_reasoning_nonempty_raw_content'] += bool(item.get('raw_content'))
            if value.get('type') == 'item_completed' and item.get('type') == 'CommandExecution':
                counts['event_command_execution_items'] += 1
                counts['event_command_nonzero_exit_items'] += item.get('exit_code') not in [None, 0]
        if target in canonical(value):
            marker_lines.append(n)
            if current_turn:
                marker_turns.add(current_turn)
        if typ != 'response_item':
            continue
        subtype = value.get('type')
        item_types[subtype] += 1
        row = {'source_line_1based': n, 'ordinal': record.get('ordinal'), 'timestamp': record.get('timestamp'), 'type': subtype, 'item_id': value.get('id'), 'turn_id_from_prior_task_started': current_turn, 'role': value.get('role')}
        if subtype in ['custom_tool_call', 'function_call']:
            if value.get('call_id'):
                call_ids.add(value['call_id'])
            row['tool_name'] = value.get('name')
            row['arguments_or_input_sha256'] = objsha(value.get('arguments', value.get('input')))
        elif subtype in ['custom_tool_call_output', 'function_call_output']:
            if value.get('call_id'):
                result_ids.add(value['call_id'])
            row['output_sha256'] = objsha(value.get('output'))
        elif subtype == 'reasoning':
            text = ''.join(x.get('text', '') for x in value.get('summary') or [] if isinstance(x, dict))
            row.update(readable_summary_characters=len(text), readable_summary_sha256=sha(text.encode()) if text else None, encrypted_content_present=bool(value.get('encrypted_content')), raw_reasoning_recoverable_from_encryption=False)
            counts['reasoning_items'] += 1
            counts['encrypted_reasoning_items'] += bool(value.get('encrypted_content'))
            counts['readable_summary_items'] += bool(text)
            counts['readable_summary_characters'] += len(text)
            if text:
                summaries[sha(text.encode())] = len(text)
        elif subtype == 'message':
            text = ''.join(x.get('text', '') for x in value.get('content') or [] if isinstance(x, dict))
            row['content_characters'] = len(text)
            row['content_sha256'] = sha(text.encode())
            if value.get('role') == 'assistant':
                counts['assistant_message_items'] += 1
        rows.append(row)
    write_rows(controlled / 'codex_exact_session.items.metadata.jsonl.gz', rows)
    after_stat = path.stat()
    return {'source_path': str(path), 'source_sha256': sha(raw), 'bytes': len(raw), 'source_stat_stable_during_read': (before_stat.st_size, before_stat.st_mtime_ns) == (after_stat.st_size, after_stat.st_mtime_ns), 'session_metadata_identity': session_meta, 'counts': dict(counts), 'response_item_types': dict(item_types), 'event_types': dict(event_types), 'call_ids': len(call_ids), 'output_ids': len(result_ids), 'calls_without_output': len(call_ids - result_ids), 'outputs_without_call': len(result_ids - call_ids), 'readable_summary_unique_contents': len(summaries), 'exact_repair_path_marker_line_count': len(marker_lines), 'exact_repair_path_marker_lines': marker_lines, 'repair_marker_turn_ids': sorted(marker_turns), 'full_session_is_not_one_repair_episode': True, 'historical_execution_condition': 'Codex historical auxiliary resource-repair conversation, including inherited/multiple task turns and subagent activity; not native OpenClaw maker equivalence.', 'original_full_model_requests_and_complete_initial_tool_schemas_verified': False, 'no_training_admission_performed': True, 'encrypted_reasoning_is_not_plaintext_recovery': True}


def main():
    OUT.mkdir(exist_ok=True)
    controlled = OUT / 'controlled'
    controlled.mkdir(exist_ok=True)
    baseline = baseline_metadata()
    carrier_paths = {}
    for name in ['ADDITIONAL_ORIGINAL_FILES.jsonl.gz', 'FINAL_DISCOVERY_FILES.jsonl.gz', 'ASSISTED_REPAIR_DIRECTORY_FILES.jsonl.gz']:
        for _, row in lines(V7 / 'controlled' / name):
            p = Path(row['source_path'])
            if p.name == 'session_events.jsonl' or p.suffix.lower() == '.raw' or '.sse' in p.name.lower() or ('response' in p.name.lower() and p.suffix.lower() in {'.json', '.gz'}):
                carrier_paths[str(p).lower()] = p
    files, native, pairs = [], [], []
    native_hash_groups, pair_groups, all_reasoning = {}, {}, {}
    file_counts = Counter()
    issues = []
    for count, p in enumerate(sorted(carrier_paths.values(), key=lambda p: str(p).lower()), 1):
        try:
            raw = p.read_bytes()
            file_sha = sha(raw)
            text = gzip.decompress(raw).decode('utf-8-sig') if p.suffix.lower() == '.gz' else raw.decode('utf-8-sig')
        except (OSError, UnicodeError, ValueError) as e:
            issues.append({'source_path': str(p), 'error_type': type(e).__name__})
            continue
        meta = {'source_path': str(p), 'source_sha256': file_sha, 'bytes': len(raw), 'decoded_content_sha256': sha(text.encode()), 'format': None}
        if p.name == 'session_events.jsonl':
            meta['format'] = 'native_session_jsonl'
            row = audit_native(p, raw, baseline)
            row['prior_v4_historical_source_overlay'] = baseline['historical_labels'].get(row['native_session_id'], {})
            if file_sha not in native_hash_groups:
                row['source_alias_paths'] = [str(p)]
                native_hash_groups[file_sha] = row
                native.append(row)
            else:
                old = native_hash_groups[file_sha]
                aliases = old['source_alias_paths'] + [str(p)]
                def quality_context(r):
                    return (bool(r['same_episode_original_API_contexts']), r['request_packet_file_present'], len(r['valid_original_schema_names']))
                if quality_context(row) > quality_context(old):
                    row['source_alias_paths'] = aliases
                    native[native.index(old)] = row
                    native_hash_groups[file_sha] = row
                else:
                    old['source_alias_paths'] = aliases
        elif p.name in {'stdout.raw', 'stderr.raw'}:
            meta['format'] = 'tool_stdout_stderr_raw_not_provider_response'
        else:
            try:
                value = json.loads(text)
            except ValueError:
                value = None
            response = value if isinstance(value, dict) and isinstance(value.get('choices'), list) else sse_response(text)
            if response is None or not response.get('choices'):
                meta['format'] = 'other_response_artifact_or_unrecognized_raw'
            else:
                stream = '_stream_quality' in response
                meta['format'] = 'provider_sse_response' if stream else 'provider_json_response'
                message = response['choices'][0].get('message') or {}
                message_sha = objsha(message)
                response_id = response.get('id')
                key = ('provider_id:' + response_id) if isinstance(response_id, str) and response_id else ('message:' + message_sha)
                qp, request = find_request(p)
                reasons = nonempty_reasoning(message)
                r_hashes = {sha(v.encode()): len(v) for _, v in reasons}
                all_reasoning.update(r_hashes)
                prior = next((v for run, v in sorted(baseline['prior_run_labels'].items(), key=lambda x: len(x[0]), reverse=True) if str(p).lower().startswith(run.lower() + '\\')), {})
                role_label = prior.get('reviewed_scope') or baseline['prior_pair_scope'].get(response_id) or 'unassessed_original_role'
                if not prior and ('technical_probe' in str(p).lower() or '/controls/' in p.as_posix().lower()):
                    role_label = 'technical_capture_path_marker_not_a_business_maker_claim'
                response_tool_names = {c.get('function', {}).get('name') for c in message.get('tool_calls') or [] if c.get('function', {}).get('name')}
                argument_parse_errors = 0
                for call in message.get('tool_calls') or []:
                    arguments = call.get('function', {}).get('arguments')
                    if isinstance(arguments, str):
                        try:
                            json.loads(arguments)
                        except ValueError:
                            argument_parse_errors += 1
                request_schemas, _ = schema_names(request or {})
                stored = load(p.parent / 'response.json', {}) if stream else {}
                stored_msg = ((stored or {}).get('choices') or [{}])[0].get('message') or {}
                row = {'provider_response_id': response_id, 'provider_model': response.get('model'), 'response_message_sha256': message_sha, 'response_sha256': objsha(response), 'message_variant_hashes': [message_sha], 'source_response_paths': [str(p)], 'source_response_sha256': [file_sha], 'source_request_paths': [str(qp)] if qp else [], 'request_present': request is not None, 'request_quality': openai_history_quality(request) if request else None, 'request_model_parameters': {k: request.get(k) for k in ['model', 'stream', 'thinking', 'reasoning_effort'] if request and k in request}, 'response_finish_reason': response['choices'][0].get('finish_reason'), 'reasoning_characters': sum(len(v) for _, v in reasons), 'reasoning_fields': [k for k, v in reasons], 'reasoning_content_sha256': sorted(r_hashes), 'response_visible_content_characters': len(message.get('content') or '') if isinstance(message.get('content'), str) else 0, 'response_tool_calls': len(message.get('tool_calls') or []), 'response_called_names_missing_request_schema': sorted(response_tool_names - request_schemas), 'stream_quality': response.get('_stream_quality'), 'adjacent_saved_response_readable_reasoning_characters': sum(len(v) for _, v in nonempty_reasoning(stored_msg)) if stored else None, 'prior_v4_role_label': role_label, 'historical_condition': 'Original provider JSON or SSE; per-run recorded execution must distinguish historical custom runner from native transport.', 'already_in_v4_by_provider_response_id': response_id in baseline['v4_provider_ids'] if response_id else False, 'same_response_message_as_v4': message_sha in baseline['v4_message_hashes'], 'reasoning_content_already_in_v4': sorted(h for h in r_hashes if h in baseline['v4_reasoning_hashes']), 'original226_scope': 'preserved_pending_lineage_or_existing_role_overlay_not_admitted_here', 'no_training_admission_performed': True}
                if key in pair_groups:
                    old = pair_groups[key]
                    old['source_response_paths'].append(str(p))
                    old['source_response_sha256'].append(file_sha)
                    if message_sha not in old['message_variant_hashes']:
                        old['message_variant_hashes'].append(message_sha)
                    if qp and str(qp) not in old['source_request_paths']:
                        old['source_request_paths'].append(str(qp))
                    if row['reasoning_characters'] > old['reasoning_characters']:
                        for k in ['reasoning_characters', 'reasoning_fields', 'reasoning_content_sha256', 'stream_quality']:
                            old[k] = row[k]
                    if request is not None and not old['request_present']:
                        old['request_present'], old['request_quality'] = True, row['request_quality']
                else:
                    pair_groups[key] = row
                    pairs.append(row)
                active = pair_groups[key]
                active['prior_recorded_historical_execution_condition'] = baseline['prior_pair_condition'].get(response_id, 'not_yet_pinned_for_this_response')
                active['response_tool_arguments_json_parse_errors'] = argument_parse_errors
        files.append(meta)
        file_counts[meta['format']] += 1
        if count % 500 == 0:
            print('RECOVERABILITY_FILES', count, len(carrier_paths), flush=True)
    # Session identity is the unit for unique native conversation counts; byte
    # snapshots with the same ID remain visible and are not called new sessions.
    sessions = defaultdict(list)
    for row in native:
        if row['native_session_id']:
            sessions[row['native_session_id']].append(row)
    representatives = [max(group, key=lambda r: (r['messages'], bool(r['same_episode_original_API_contexts']), r['request_packet_file_present'], r['bytes'])) for group in sessions.values()]
    native_totals = Counter()
    for row in representatives:
        native_totals['unique_native_session_ids'] += 1
        native_totals['same_as_old1763'] += row['same_native_session_as_old1763'] or row['same_bytes_as_old1763_archive']
        native_totals['outside_old1763'] += not (row['same_native_session_as_old1763'] or row['same_bytes_as_old1763_archive'])
        native_totals['outside_old1763_and_v4_native_inventory'] += not (row['same_native_session_as_old1763'] or row['same_bytes_as_old1763_archive'] or row['already_in_v4_historical_native_inventory'])
        native_totals['already_in_v4_historical_inventory'] += row['already_in_v4_historical_native_inventory']
        native_totals['assistant_responses'] += row['assistant_responses']
        native_totals['readable_separate_reasoning_fields'] += row['separate_readable_reasoning_fields']
        native_totals['readable_separate_reasoning_characters'] += row['separate_readable_reasoning_characters']
        native_totals['sessions_missing_outer_request_packet'] += not row['request_packet_file_present']
        native_totals['sessions_missing_user_prompt'] += not row['native_user_prompt_present']
        native_totals['sessions_called_tool_without_original_schema'] += bool(row['called_names_without_original_recorded_schema'])
        native_totals['sessions_with_same_episode_original_API_contexts'] += bool(row['same_episode_original_API_contexts'])
        native_totals['sessions_called_tool_without_original_or_same_episode_API_schema'] += bool(row['called_names_without_original_or_same_episode_API_schema'])
        native_totals['sessions_called_tool_without_original_or_matching_pinned_factory_schema'] += bool(row['called_names_without_original_or_matching_pinned_factory_schema'])
        native_totals['calls_without_feedback'] += row['tool_calls_without_recorded_result']
        native_totals['feedback_without_call'] += row['tool_results_without_recorded_call']
        native_totals['sessions_with_parse_errors'] += bool(row['malformed_json_line_numbers'])
    pair_totals = Counter()
    run_groups = set()
    for row in pairs:
        pair_totals['distinct_provider_id_or_response_content_groups'] += 1
        pair_totals['with_original_readable_reasoning'] += bool(row['reasoning_characters'])
        pair_totals['reasoning_characters'] += row['reasoning_characters']
        pair_totals['request_present'] += row['request_present']
        pair_totals['request_missing'] += not row['request_present']
        pair_totals['already_v4_provider_id'] += row['already_in_v4_by_provider_response_id']
        pair_totals['same_response_message_as_v4'] += row['same_response_message_as_v4']
        pair_totals['outside_v4_provider_id_and_message_content_references'] += not (row['already_in_v4_by_provider_response_id'] or row['same_response_message_as_v4'])
        pair_totals['terminal_stop_or_tool_calls'] += row['response_finish_reason'] in {'stop', 'tool_calls'}
        if row['request_quality']:
            pair_totals['request_without_valid_tool_schema'] += not bool(row['request_quality']['request_tools_valid_schema_names'])
            pair_totals['request_with_unmatched_history_feedback'] += bool(row['request_quality']['history_unmatched_tool_results'])
        pair_totals['response_tool_calls_missing_original_request_schema'] += bool(row['response_called_names_missing_request_schema'])
        pair_totals['response_tool_argument_json_parse_errors'] += row['response_tool_arguments_json_parse_errors']
        pair_totals['response_ids_with_multiple_saved_message_variants'] += len(row['message_variant_hashes']) > 1
        pair_totals['sse_readable_reasoning_missing_from_adjacent_saved_response'] += bool(row['stream_quality'] and row['reasoning_characters'] and row['adjacent_saved_response_readable_reasoning_characters'] == 0)
        for p in row['source_response_paths']:
            q = Path(p)
            for ancestor in q.parents:
                if ancestor.name in {'model_requests', 'model_calls', 'api_audit', 'host_api_queue'}:
                    run_groups.add(str(ancestor.parent))
                    break
    codex = audit_codex(EXACT_CODEX, controlled)
    write_rows(controlled / 'carrier_files.metadata.jsonl.gz', files)
    write_rows(controlled / 'native_sessions.metadata.jsonl.gz', native)
    write_rows(controlled / 'provider_responses.metadata.jsonl.gz', pairs)
    service_root = Path('E:/skillloop_runs/20261021_T0012_native_two_arm/observed_service')
    code_evidence = [{'source_path': str(service_root / n), 'sha256': sha((service_root / n).read_bytes())} for n in ['src/response-builder.js', 'src/sink-factory.js', 'src/stream-driver.js', 'native_observer.cjs']]
    report = {'schema_version': 'wrd-original-raw-recoverability-quality-v8', 'measured_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'Full supplemental v7 carrier inventory (119 roots + final5 + assisted root) and exactly one authorized Codex file; no generalization to all 175 directories or all training suitability.', 'sampling': {'carrier_format_counts': 'full enumeration of selected carrier filename classes in closed v7 ledgers', 'native_statistics': 'all byte-unique native event files, then identity-group representative snapshots', 'provider_statistics': 'all recognizable JSON/SSE provider responses selected from supplemental ledgers', 'semantic_success_or_business_quality': 'not assessed by this script'}, 'old_baseline': {'canonical_episode_ids': len(baseline['canonical_ids']), 'native_session_ids_from_v7_old_parsed_index': len(baseline['native_ids']), 'native_sha256_from_v7_old_parsed_index': len(baseline['native_hashes']), 'v4_native_inventory_ids': len(baseline['v4_native_ids']), 'v4_provider_response_ids': len(baseline['v4_provider_ids']), 'v4_unique_reasoning_contents': len(baseline['v4_reasoning_hashes'])}, 'carrier_files': {'selected_paths': len(carrier_paths), 'successfully_read_paths': len(files), 'unique_raw_file_sha256': len({r['source_sha256'] for r in files}), 'by_format': dict(file_counts)}, 'native': {'selected_paths': file_counts['native_session_jsonl'], 'unique_file_sha256_snapshots': len(native), 'totals': dict(native_totals), 'recorded_stages': dict(Counter(str(r['recorded_stage']) for r in representatives)), 'recorded_statuses': dict(Counter(str(r['recorded_status']) for r in representatives)), 'source_ids_original226_labels_preserved_without_new_admission': True}, 'provider_responses': {'totals': dict(pair_totals), 'unique_readable_reasoning_content_sha256': len(all_reasoning), 'reasoning_contents_outside_v4_reference': len(set(all_reasoning) - baseline['v4_reasoning_hashes']), 'identified_run_container_paths': len(run_groups), 'native_session_independence_not_inferred_from_response_count': True}, 'exact_codex_session': codex, 'reasoning_visibility_diagnosis': {'observed_native_field_absence_does_not_prove_model_did_not_think': True, 'provider_thinking_disabled_or_unpublished_for_all_old1763': 'unknown; not inferred from empty exported fields', 'static_original_service_code_evidence': code_evidence, 'code_observation': ['Streaming onReasoning accumulates state.reasoning and writes reasoning_content.', 'Streaming onProgress also writes reasoning_content but does not enter state.reasoning, so progress and model thought need separation.', 'Nonstreaming final response copies state.reasoning; the separate tool-call response branch omits state.reasoning.', 'native_observer records usage/finish metadata rather than provider response bodies.'], 'actual_episode_loaded_code_identity_and_provider_R_for_every_old_session': 'not established by this static inspection', 'native_visible_explanation_structured_reason_and_tool_feedback_are_distinct_process_targets': True}, 'read_or_parse_issues': issues, 'outputs': [str(controlled / n) for n in ['carrier_files.metadata.jsonl.gz', 'native_sessions.metadata.jsonl.gz', 'provider_responses.metadata.jsonl.gz', 'codex_exact_session.items.metadata.jsonl.gz']], 'training_admission_performed': False, 'model_calls_started': 0, 'training_started': False, 'limitations': ['Native event snapshots and API response copies are deduplicated separately; they are not summed as independent workflows.', 'A provider response missing a complete next-request or tool schema is a recoverability gap, not automatically a bad skill or unusable training record.', 'Inherited/multi-turn Codex history and encrypted reasoning are not converted into native-maker or plaintext-R claims.', 'Existing original226 labels are preserved; unassessed new resources remain pending lineage audit, without blanket admission or rejection.', 'No sensitive body text is included in these metadata outputs.']}
    report['native']['native_named_artifacts_without_session_header'] = [{'source_path': r['source_path'], 'bytes': r['bytes'], 'alias_paths': r['source_alias_paths'], 'excluded_from_independent_native_session_counts': True} for r in native if not r['valid_session_header_present']]
    report['native']['outside_old1763_and_v4_by_recorded_stage'] = dict(Counter(str(r['recorded_stage']) for r in representatives if not (r['same_native_session_as_old1763'] or r['same_bytes_as_old1763_archive'] or r['already_in_v4_historical_native_inventory'])))
    report['native']['preserved_v4_role_labels'] = dict(Counter(str(r['prior_v4_historical_source_overlay'].get('role_scope', 'not_previously_labeled')) for r in representatives))
    report['provider_responses']['preserved_prior_v4_run_scope_labels'] = dict(Counter(r['prior_v4_role_label'] for r in pairs))
    report['provider_responses']['responses_outside_v4_by_prior_scope'] = dict(Counter(r['prior_v4_role_label'] for r in pairs if not (r['already_in_v4_by_provider_response_id'] or r['same_response_message_as_v4'])))
    report['provider_responses']['recorded_historical_conditions_from_v4'] = dict(Counter(r['prior_recorded_historical_execution_condition'] for r in pairs))
    report['provider_responses']['observed_request_thinking_parameters'] = dict(Counter(canonical(r['request_model_parameters'].get('thinking', 'absent')) for r in pairs))
    report['provider_responses']['observed_request_stream_flags'] = dict(Counter(str(r['request_model_parameters'].get('stream', 'absent')) for r in pairs))
    report['provider_responses']['no_tools_schema_is_not_a_defect_when_no_tools_are_used'] = True
    report['native']['source_context_restoration_limits'] = 'Original exported tools.json, complete same-episode native API capture, and image-pinned schema recovery are separately reported. A schema missing from the truncated export is not assumed unrecoverable.'
    provider_lookup = {r['provider_response_id']: r for r in pairs if r['provider_response_id']}
    correlation = []
    for row in representatives:
        for receipt in row['assistant_model_response_receipts']:
            target = provider_lookup.get(receipt['response_id'])
            if target is not None:
                correlation.append({'native_session_id': row['native_session_id'], 'native_source_path': row['source_path'], 'native_source_line_1based': receipt['source_line_1based'], 'response_id': receipt['response_id'], 'provider_source_paths': target['source_response_paths'], 'provider_readable_reasoning_field_characters': target['reasoning_characters'], 'native_readable_separate_reasoning_characters': receipt['separate_readable_reasoning_characters'], 'field_visibility_loss_between_wire_and_selected_native_export': target['reasoning_characters'] > 0 and receipt['separate_readable_reasoning_characters'] == 0})
    write_rows(controlled / 'wire_native_response_identity_links.metadata.jsonl.gz', correlation)
    report['reasoning_visibility_diagnosis']['actual_same_response_id_wire_native_comparison'] = {'matched_responses': len(correlation), 'wire_readable_reasoning_field_nonempty_but_native_separate_field_empty': sum(r['field_visibility_loss_between_wire_and_selected_native_export'] for r in correlation), 'evidence': str(controlled / 'wire_native_response_identity_links.metadata.jsonl.gz'), 'interpretation': 'These original wire field values existed and were not present as separate readable native export fields. This does not establish that every value is model-internal reasoning rather than progress, nor identify the exact persistence/parser mechanism for all old1763.'}
    report['reasoning_visibility_diagnosis']['readable_R_definition'] = 'Counts named reasoning fields/blocks in original records; not a claim of complete internal chain-of-thought. Streaming progress can share reasoning_content.'
    report['outputs'].append(str(controlled / 'wire_native_response_identity_links.metadata.jsonl.gz'))
    report['method_corrections_before_publication'] = ['Empty files and headerless tool-result fixtures named session_events.jsonl are carrier artifacts, not independent native conversations.', 'Ordinal-prefixed request filenames are matched to ordinal-prefixed responses; absence of generic request.json is not labeled a missing request.', 'Byte-identical event aliases may differ in adjacent context availability; the richest actual recorded alias is selected without synthesizing a model request.', 'JSONL/SSE lines are split on LF only; legal Unicode U+2028/U+2029 inside JSON strings must not become fake malformed lines or missing output records.']
    report['script_sha256'] = sha(Path(__file__).read_bytes())
    report['frozen_v7_input_ledgers'] = [{'path': str(V7 / 'controlled' / name), 'sha256': sha((V7 / 'controlled' / name).read_bytes())} for name in ['ADDITIONAL_ORIGINAL_FILES.jsonl.gz', 'FINAL_DISCOVERY_FILES.jsonl.gz', 'ASSISTED_REPAIR_DIRECTORY_FILES.jsonl.gz']]
    report['output_metadata_file_receipts'] = [{'path': name, 'sha256': sha(Path(name).read_bytes()), 'bytes': Path(name).stat().st_size} for name in report['outputs']]
    (OUT / 'RAW_RECOVERABILITY.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(OUT / 'RAW_RECOVERABILITY.json'), 'files': report['carrier_files'], 'native': report['native'], 'provider': report['provider_responses'], 'codex_summary': {'reasoning_items': codex['counts'].get('reasoning_items'), 'readable_summary_items': codex['counts'].get('readable_summary_items')}, 'read_errors': len(issues)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
