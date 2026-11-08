#!/usr/bin/env python3
"""Bounded 0/26/241 stopping comparison; no tools or Agent loop are executed."""

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import signal
import sys
import time
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parent.parent
STEPS = (0, 26, 241)
SEQUENCE = ((241, 'short'), (0, 'short'), (241, 'long'), (0, 'long'), (26, 'short'), (26, 'long'))
COUNTS = {'short': 24000, 'long': 66000}
REVISIONS = {'8b': 'b968826d9c46dd6066d109eabc6255188de91218',
             '14b': '40c069824f4251a91eefaf281ebe4c544efd3e18'}
MAX_OUTPUT = 128
REQUEST_SECONDS = 180
GROUP_SECONDS = 600
PREFIX = 'Ignore this synthetic padding:\n'
PADDING = ' reference'
SUFFIX = '\nRespond ONLY with OK. Do not explain or call any tool.'
ERRORS = (OSError, ValueError, KeyError, TypeError, RuntimeError)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write('\n')


@contextmanager
def deadline(seconds):
    # The executable runs on Linux Spark; this bounds the whole request, including reads.
    if not hasattr(signal, 'setitimer'):
        raise RuntimeError('Run requests on Linux Spark: a POSIX wall-clock deadline is required')
    if signal.getitimer(signal.ITIMER_REAL)[0]:
        raise RuntimeError('An existing alarm prevents installing the request deadline')
    previous = signal.getsignal(signal.SIGALRM)
    def expired(_number, _frame):
        raise TimeoutError(f'Request exceeded {seconds} seconds')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def request_json(url, payload=None, seconds=REQUEST_SECONDS):
    body = encoded(payload) if payload is not None else None
    request = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    with deadline(seconds):
        try:
            response = urllib.request.urlopen(request, timeout=seconds)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise ValueError('Response exceeds the diagnostic evidence limit')
            return response.getcode(), raw


def startup_configuration(size, path):
    manifest = ROOT / 'local/TRAINING_SHA256_v2.txt'
    pins = dict((name, digest) for digest, name in
                (line.split() for line in manifest.read_text(encoding='utf-8').splitlines()
                 if line.strip() and not line.startswith('#')))
    raw = path.read_bytes()
    tokens = dict(token.split('=', 1) for line in raw.decode('utf-8-sig').splitlines()
                  if line.startswith('spark_service ') for token in line.split()[1:])
    expected = {f'adapter_{step}_sha256': pins[f'out58_{size}_v2/checkpoint-{step}'] for step in STEPS}
    expected.update(size=size, profile='yarn128', model_length='131072', revision=REVISIONS[size])
    if any(tokens.get(key) != value for key, value in expected.items()):
        raise ValueError('Startup log is missing or differs from pinned 0/26/241, revision or yarn128')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', tokens.get('image', '')):
        raise ValueError('Startup log must identify the exact serving image')
    return {'size': size, 'base_revision': REVISIONS[size], 'context': 131072,
            'profile': 'yarn128', 'image': tokens['image'], 'adapter_sha256': expected,
            'manifest_sha256': sha(manifest.read_bytes())}, sha(raw)


def make_payload(model, case):
    content = PREFIX + PADDING * COUNTS[case] + SUFFIX
    payload = {'model': model, 'messages': [{'role': 'user', 'content': content}],
               'chat_template_kwargs': {'enable_thinking': False},
               'seed': 58, 'temperature': 0.7, 'top_p': 0.8, 'top_k': 20, 'min_p': 0.0,
               'max_tokens': MAX_OUTPUT, 'stream': False}
    return payload, {'role': 'user', 'prefix': PREFIX, 'padding': PADDING,
                     'padding_count': COUNTS[case], 'suffix': SUFFIX,
                     'content_sha256': sha(content.encode('utf-8'))}


def inspect_response(row, response):
    model = row['model']
    if not isinstance(response, dict) or response.get('model') != model:
        raise ValueError('Response model differs from the requested adapter alias')
    choices, usage = response.get('choices'), response.get('usage')
    if (not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict)
            or not isinstance(usage, dict)):
        raise ValueError('Missing unique choice or actual token usage')
    if (not all(type(usage.get(k)) is int for k in ('prompt_tokens', 'completion_tokens', 'total_tokens'))
            or usage['prompt_tokens'] <= 0 or not 0 <= usage['completion_tokens'] <= MAX_OUTPUT
            or usage['total_tokens'] != usage['prompt_tokens'] + usage['completion_tokens']):
        raise ValueError('Invalid, unbalanced or over-budget actual usage')
    row.update(usage=usage, finish_reason=choices[0].get('finish_reason'), stop_reason=choices[0].get('stop_reason'),
               output_budget_exhausted=usage['completion_tokens'] == MAX_OUTPUT)
    condition = (usage['prompt_tokens'] + MAX_OUTPUT <= 32768 if row['case'] == 'short'
                 else usage['prompt_tokens'] >= 65806 and usage['prompt_tokens'] + MAX_OUTPUT <= 131072)
    row['input_condition_met'] = condition
    message = choices[0].get('message', {})
    content = message.get('content') if isinstance(message, dict) else None
    row['answer_is_ok'] = isinstance(content, str) and content.strip() == 'OK'
    finish = row['finish_reason']
    if not condition:
        row['status'] = 'INPUT_CONDITION_MISMATCH'
    elif finish == 'length':
        row['status'] = 'OUTPUT_LIMIT_REACHED'
    elif finish == 'stop':
        row['status'] = 'NATURAL_STOP_OK' if row['answer_is_ok'] else 'NATURAL_STOP_WRONG_ANSWER'
    else:
        row['status'] = 'UNEXPECTED_FINISH'
    row['natural_stop_observed'] = finish == 'stop'
    row['termination_task_pass'] = condition and finish == 'stop' and row['answer_is_ok']


def run(base, size, out_dir, startup_log, selected_case='all'):
    invocation_epoch, invocation_monotonic = time.time(), time.monotonic()
    serving, log_sha = startup_configuration(size, startup_log)
    config = {'schema': 'wrd58-final241-comparison-v1', 'serving': serving,
              'script_sha256': sha(Path(__file__).read_bytes()), 'max_output_tokens': MAX_OUTPUT,
              'request_deadline_seconds': REQUEST_SECONDS, 'group_wall_seconds': GROUP_SECONDS,
              'cases': COUNTS, 'checkpoints': STEPS, 'request_sequence': SEQUENCE,
              'sampling': {'enable_thinking': False, 'seed': 58, 'temperature': 0.7,
                           'top_p': 0.8, 'top_k': 20, 'min_p': 0.0}}
    config_hash = sha(encoded(config))
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / 'comparison_config.json'
    if manifest.exists():
        if json.loads(manifest.read_text(encoding='utf-8')) != json.loads(encoded(config)):
            raise ValueError('Output directory belongs to another frozen comparison configuration')
    else:
        save_new(manifest, config)
    budget_path = out_dir / 'wall_budget.json'
    if budget_path.exists():
        budget = json.loads(budget_path.read_text(encoding='utf-8'))
        if (budget.get('configuration_sha256') != config_hash or budget.get('limit_seconds') != GROUP_SECONDS
                or budget.get('deadline_epoch') != budget.get('started_epoch', 0) + GROUP_SECONDS
                or time.time() < budget['started_epoch']):
            raise ValueError('Persistent group budget differs or the wall clock moved backwards')
    else:
        budget = {'configuration_sha256': config_hash, 'started_epoch': invocation_epoch,
                  'deadline_epoch': invocation_epoch + GROUP_SECONDS, 'limit_seconds': GROUP_SECONDS}
        save_new(budget_path, budget)
    def remaining():
        return min(budget['deadline_epoch'] - time.time(),
                   GROUP_SECONDS - (time.monotonic() - invocation_monotonic))
    if remaining() > 0:
        code, raw = request_json(base + '/models', seconds=min(15, remaining()))
        models = json.loads(raw)
        if not isinstance(models, dict) or not isinstance(models.get('data'), list):
            raise ValueError('Invalid model inventory response')
        aliases = {item['id'] for item in models['data']}
        if code != 200 or not {f'wrd58-{size}-{step}' for step in STEPS} <= aliases:
            raise ValueError('Serving endpoint must expose all pinned 0/26/241 aliases')
    rows, calls, reused = [], 0, 0
    cases = list(COUNTS) if selected_case == 'all' else [selected_case]
    for step, case in SEQUENCE:
        if case not in cases:
            continue
        model = f'wrd58-{size}-{step}'
        payload, recipe = make_payload(model, case)
        request_hash = sha(encoded(payload))
        stem = out_dir / f'{model}__{case}'
        result_path, admission_path = Path(str(stem) + '.json'), Path(str(stem) + '.admission.json')
        if result_path.exists():
            row = json.loads(result_path.read_text(encoding='utf-8'))
            if (not isinstance(row, dict) or row.get('request_sha256') != request_hash
                    or row.get('configuration_sha256') != config_hash):
                raise ValueError(f'Existing receipt differs from the frozen request: {result_path}')
            rows.append(row)
            reused += 1
            continue
        if admission_path.exists():
            row = json.loads(admission_path.read_text(encoding='utf-8'))
            if row.get('request_sha256') != request_hash or row.get('configuration_sha256') != config_hash:
                raise ValueError(f'Pending admission differs: {admission_path}')
            row.update(status='UNKNOWN_INTERRUPTED_REQUEST', state='UNKNOWN_INTERRUPTED_REQUEST', wall_seconds=None,
                       error='Prior admission has no response; preserved without retry')
            save_new(result_path, row)
            rows.append(row)
            reused += 1
            continue
        row = {'schema': config['schema'], 'model': model, 'checkpoint': step, 'case': case,
               'input_label': 'nominal24k' if case == 'short' else 'nominal66k',
               'request_sha256': request_hash, 'configuration_sha256': config_hash,
               'startup_log_sha256': log_sha, 'request_json_key_order': list(payload),
               'request_parameters': {k: v for k, v in payload.items() if k != 'messages'},
               'request_messages_recipe': [recipe], 'status': 'REQUEST_ERROR',
               'natural_stop_observed': False, 'termination_task_pass': False}
        if remaining() <= 0:
            row.update(status='SKIP_GROUP_WALL_BUDGET', wall_seconds=0, new_model_requests=0)
            save_new(result_path, row)
            rows.append(row)
            continue
        save_new(admission_path, row | {'state': 'ADMITTED_RESPONSE_PENDING'})
        started = time.monotonic()
        try:
            timeout = min(REQUEST_SECONDS, remaining())
            if timeout <= 0:
                row.update(status='SKIP_GROUP_WALL_BUDGET', new_model_requests=0)
                continue
            row['effective_request_deadline_seconds'] = timeout
            calls += 1
            code, raw = request_json(base + '/chat/completions', payload, seconds=timeout)
            row.update(http_status=code, response_raw=raw.decode('utf-8', errors='replace'), response_sha256=sha(raw))
            response = json.loads(raw)
            row['response'] = response
            if code != 200:
                raise ValueError(f'HTTP {code}')
            inspect_response(row, response)
        except ERRORS as error:
            row['error'] = f'{type(error).__name__}: {error}'
        finally:
            row['wall_seconds'] = round(time.monotonic() - started, 3)
            save_new(result_path, row)
            rows.append(row)
    observed = sum('input_condition_met' in row and row.get('http_status') == 200 for row in rows)
    valid_slots = sum(row.get('input_condition_met') is True for row in rows)
    skipped = sum(row['status'] == 'SKIP_GROUP_WALL_BUDGET' for row in rows)
    status = ('COMPLETE' if valid_slots == len(rows) else 'BUDGET_EXHAUSTED' if skipped
              else 'PARTIAL' if observed else 'ERROR')
    return {'schema': config['schema'], 'size': size, 'new_model_requests': calls,
            'matrix_status': status, 'selected_case': selected_case,
            'selected_slots': len(STEPS) * len(cases), 'processed_slots': len(rows),
            'observed_slots': observed, 'valid_comparison_slots': valid_slots,
            'termination_pass_count': sum(row['termination_task_pass'] for row in rows),
            'request_error_count': sum(row['status'] == 'REQUEST_ERROR' for row in rows),
            'group_budget_skip_count': sum(row['status'] == 'SKIP_GROUP_WALL_BUDGET' for row in rows),
            'unknown_interrupted_count': sum(row['status'] == 'UNKNOWN_INTERRUPTED_REQUEST' for row in rows),
            'group_wall_seconds': GROUP_SECONDS, 'persistent_deadline_epoch': budget['deadline_epoch'],
            'reused_receipts': reused, 'new_completion_token_ceiling': calls * MAX_OUTPUT,
            'max_requests_per_size': 6, 'max_completion_tokens_per_size': 768,
            'results': [{k: row.get(k) for k in ('model', 'case', 'status', 'finish_reason', 'stop_reason',
                        'natural_stop_observed', 'answer_is_ok', 'input_condition_met',
                        'termination_task_pass', 'usage', 'wall_seconds', 'error')} for row in rows],
            'scope': 'Bounded synthetic stopping comparison; skill generation requires native producer evidence.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('size', choices=tuple(REVISIONS))
    parser.add_argument('--base-url', default='http://127.0.0.1:18758/v1')
    parser.add_argument('--startup-log', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--case', choices=('short', 'long', 'all'), default='all')
    args = parser.parse_args()
    try:
        report = run(args.base_url.rstrip('/'), args.size, args.out_dir, args.startup_log, args.case)
        summary = args.out_dir / 'summary.json'
        try:
            save_new(summary, report)
        except FileExistsError:
            summary = args.out_dir / f'summary.resume-{time.time_ns()}.json'
            save_new(summary, report)
    except ERRORS as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1
    print(json.dumps(report | {'summary_file': str(summary)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
