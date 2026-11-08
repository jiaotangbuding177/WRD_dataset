#!/usr/bin/env python3
"""Prepare or run one real corpus maker task in the fixed native OpenClaw.

This is input delivery, a byte-forwarding budget relay, and terminal collection.
It contains no agent/tool loop and never repairs a generated skill or tool call.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / 'runtime'
IMAGE = 'sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
LOCAL = 'http://host.docker.internal:18759/v1'
SPARK = 'http://127.0.0.1:18758/v1'
ARMS = tuple(f'wrd58-{size}-{step}' for size in ('8b', '14b') for step in (0, 241))
LIMITS = {'max_requests': 24, 'max_reply_tokens': 8192,
          'max_completion_tokens': 32768, 'wall_seconds': 3600}
BASE_REVISIONS = {'8b': 'b968826d9c46dd6066d109eabc6255188de91218',
                  '14b': '40c069824f4251a91eefaf281ebe4c544efd3e18'}
NOTICE = ('\n\n【共同制作预算】本次原生会话最多3600秒、最多24次模型HTTP请求，'
          '每回复最多8192 tokens，累计completion最多32768 tokens（包括reasoning、'
          '原生重试与收尾）。单次请求会保守预留其回复上限；未知用量不退还预留。'
          '请自主安排探索、制作、实际试跑、必要修订及交付；按实际证据报告未完成项。')
OWNERSHIP = ('\n\n【当前用户的仓库源码任务】/workspace是为本次任务真实初始化的普通Git仓库，'
             'README.md及初始Git提交记录其用途。用户要求你制作该仓库自有的技能源码，'
             '目标为outputs/skill/；这是普通仓库源码工作，不是修改Workshop-owned目录或'
             '全局发布技能。请按当前原生规则使用仓库文件工具，实际写文件并真实试跑。'
             '不要把待审批Workshop提案当成本仓库已交付文件。')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_relative(value):
    if (not isinstance(value, str) or not value or '\\' in value or ':' in value
            or value.startswith('/') or any(p in ('', '.', '..') for p in value.split('/'))):
        raise ValueError('Expected a plain safe relative POSIX path')
    return PurePosixPath(value)


def pinned_file(root, pin):
    relative = safe_relative(pin['path'])
    original = root / str(relative)
    path = original.resolve()
    if (not path.is_relative_to(root) or not path.is_file() or original.is_symlink()
            or type(pin['bytes']) is not int or path.stat().st_size != pin['bytes']
            or digest(path) != pin['sha256']):
        raise ValueError('Corpus pin differs: ' + str(relative))
    return path


def verify_case(corpus, source_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', source_id):
        raise ValueError('Invalid source identity')
    corpus = Path(corpus).resolve()
    path = corpus / 'cases' / source_id / 'case.json'
    case = load(path)
    if case.get('source_id') != source_id:
        raise ValueError('Case identity differs from its path')
    for key in ('source', 'prompt', 'delivery_index', 'replay'):
        pinned_file(corpus, case[key])
    seen = {'inputs/source.json', 'inputs/resource_index.json'}
    for pin in case['resources']:
        pinned_file(corpus, pin)
        mount = str(safe_relative(pin['mount']))
        if mount.split('/')[0] not in ('inputs', 'reference_inputs') or mount in seen:
            raise ValueError('Duplicate or unsupported resource mount: ' + mount)
        seen.add(mount)
    return case, path, corpus


def is_effect_eligible(case):
    value = case.get('student_eligibility')
    return isinstance(value, dict) and value.get('effect_evaluation_allowed') is True


def run_git(workspace, *args):
    return subprocess.check_output(['git', '-c', 'core.autocrlf=false', '-C', str(workspace),
                                    *args], text=True, encoding='utf-8').strip()


def native_workspace_binding_proof(attempt):
    consumer = import_file('corpus_fixed_native_consumer', RUNTIME / 'consumer.py')
    workspace = attempt / 'workspace'
    argv = consumer.build_command(IMAGE, 'cpu-binding-declaration-only', workspace,
                                  attempt / 'openclaw_transport', attempt / 'not-mounted-private-config.json',
                                  LIMITS['wall_seconds'], backend='native')
    mounts = [argv[i + 1] for i, value in enumerate(argv[:-1]) if value == '--mount']
    target = [mount for mount in mounts if ',target=/workspace' in mount]
    expected = 'type=bind,source=' + str(workspace.resolve()) + ',target=/workspace'
    if target != [expected]:
        raise ValueError('Fixed native consumer does not bind the complete prepared repository')
    # The actual receiver mount resolves to this same directory, not a filtered copy.
    if not (workspace / '.git/HEAD').is_file() or not (workspace / '.git/objects').is_dir():
        raise ValueError('Actual source of /workspace bind lacks Git HEAD/objects')
    return {'scope': 'CPU_REPOSITORY_AND_FIXED_NATIVE_BIND_DECLARATION_NOT_CONTAINER_EXECUTION',
            'workspace_mount': expected, 'receiver_target': '/workspace',
            'receiver_backing_git_head': run_git(workspace, 'rev-parse', 'HEAD'),
            'receiver_backing_git_inside_work_tree': run_git(workspace, 'rev-parse', '--is-inside-work-tree'),
            'git_objects': len([p for p in (workspace / '.git/objects').rglob('*') if p.is_file()]),
            'copy_filter': None, 'fixed_consumer_sha256': digest(RUNTIME / 'consumer.py'),
            'container_execution_performed': False}


def prepare(corpus, source_id, arm, attempt_number, out_dir, *, allow_seen=False):
    if arm not in ARMS or type(attempt_number) is not int or attempt_number < 1:
        raise ValueError('Expected a pinned arm and positive attempt number')
    case, case_path, corpus = verify_case(corpus, source_id)
    if not is_effect_eligible(case) and not allow_seen:
        raise ValueError('Case is not explicitly eligible for student effect evaluation; '
                         'use --allow-seen-diagnostic only for a disclosed diagnostic')
    attempt = Path(out_dir).resolve() / source_id / arm / f'attempt-{attempt_number:03d}'
    attempt.mkdir(parents=True, exist_ok=False)
    workspace = attempt / 'workspace'
    workspace.mkdir()
    pins = [('inputs/source.json', case['source']),
            ('inputs/resource_index.json', case['delivery_index'])]
    pins.extend((pin['mount'], pin) for pin in case['resources'])
    resources = []
    staged = {}
    for mount, pin in pins:
        target = workspace / str(safe_relative(mount))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pinned_file(corpus, pin), target)
        if digest(target) != pin['sha256']:
            raise ValueError('Delivered file differs: ' + mount)
        staged[mount] = pin['sha256']
        resources.append({'path': str(target), 'mount': mount})
    readme = ('# User-owned WRD skill source repository\n\n'
              'This ordinary Git repository is prepared for the user\'s requested skill-source task.\n'
              'Create the repository-owned source under outputs/skill/.\n'
              'The repository is not a Workshop-managed directory and contains no supplied skill answer.\n'
              'Input materials remain historical evidence; use inputs/resource_index.json for provenance.\n')
    (workspace / 'README.md').write_text(readme, encoding='utf-8', newline='\n')
    (workspace / '.gitignore').write_text('.openclaw/\n__pycache__/\n', encoding='utf-8', newline='\n')
    save_new(workspace / 'CORPUS_INPUT_PINS.json', {'source_id': source_id,
             'case_sha256': digest(case_path), 'files': staged})
    run_git(workspace, 'init', '--quiet')
    run_git(workspace, 'config', 'user.name', 'WRD corpus preparation')
    run_git(workspace, 'config', 'user.email', 'wrd-local@invalid')
    run_git(workspace, 'add', '--', 'README.md', '.gitignore', 'CORPUS_INPUT_PINS.json')
    run_git(workspace, 'commit', '--quiet', '-m', 'Initialize user-owned skill source task')
    commit = run_git(workspace, 'rev-parse', 'HEAD')
    tree = run_git(workspace, 'rev-parse', 'HEAD^{tree}')
    prompt = pinned_file(corpus, case['prompt']).read_text(encoding='utf-8-sig') + OWNERSHIP + NOTICE
    request = {'protocol': 'native-openclaw-only-v1', 'stage': 'wrd58_corpus_producer',
               'task_id': source_id, 'input': prompt, 'context': [], 'followup_inputs': [],
               'seed': 58, 'resources': resources, 'learned_skills': []}
    save_new(attempt / 'request.json', request)
    receipt = {'schema': 'wrd58-corpus-stage-v1', 'source_id': source_id, 'arm': arm,
               'attempt': attempt_number, 'case_sha256': digest(case_path), 'files': staged,
               'request_sha256': digest(attempt / 'request.json'), 'budget': LIMITS,
               'git_commit': commit, 'git_tree': tree, 'ordinary_repository_initialized': True,
               'effect_evaluation_allowed': is_effect_eligible(case),
               'scope': 'EFFECT' if is_effect_eligible(case) and not allow_seen else 'SEEN_DIAGNOSTIC',
               'initial_skill_artifacts': 0, 'model_calls': 0}
    receipt['native_workspace_binding'] = native_workspace_binding_proof(attempt)
    save_new(attempt / 'stage_receipt.json', receipt)
    return attempt, receipt


def verify_prepared(attempt, corpus, source_id, arm, attempt_number, allow_seen):
    case, case_path, corpus = verify_case(corpus, source_id)
    receipt = load(attempt / 'stage_receipt.json')
    expected_scope = 'EFFECT' if is_effect_eligible(case) and not allow_seen else 'SEEN_DIAGNOSTIC'
    if (receipt['case_sha256'] != digest(case_path) or receipt['source_id'] != source_id
            or receipt['arm'] != arm or receipt['attempt'] != attempt_number
            or receipt['request_sha256'] != digest(attempt / 'request.json')
            or receipt['budget'] != LIMITS
            or receipt['scope'] != expected_scope
            or not is_effect_eligible(case) and not allow_seen):
        raise ValueError('Prepared request, identity or case pins differ')
    for mount, sha in receipt['files'].items():
        if digest(attempt / 'workspace' / mount) != sha:
            raise ValueError('Prepared input differs: ' + mount)
    if run_git(attempt / 'workspace', 'rev-parse', 'HEAD') != receipt['git_commit']:
        raise ValueError('Prepared source repository HEAD differs')
    if run_git(attempt / 'workspace', 'diff', '--name-only', 'HEAD', '--',
               'README.md', '.gitignore', 'CORPUS_INPUT_PINS.json'):
        raise ValueError('Prepared source repository tracked scaffold differs')
    if (attempt / 'dispatch.json').exists() or (attempt / 'producer_result.json').exists():
        raise ValueError('Attempt was already dispatched; retain it and choose a new attempt number')
    return receipt


def check_runtime():
    receipt = load(RUNTIME / 'WRAPPER_RECEIPT.json')
    if receipt['image_id'] != IMAGE or receipt['provider_base_url'] != LOCAL:
        raise ValueError('Fixed native runtime identity differs')
    for name, expected in receipt['prepared_sha256'].items():
        if Path(name).name != name or digest(RUNTIME / name) != expected:
            raise ValueError('Fixed native runtime bytes differ: ' + name)


def relay_bind(env):
    if sys.platform == 'win32':
        return '127.0.0.1'
    if sys.platform != 'linux':
        raise ValueError('Use Windows Docker Desktop or an amd64 Linux native-tool host')
    return subprocess.check_output(['docker', 'network', 'inspect', 'bridge', '--format',
                                   '{{(index .IPAM.Config 0).Gateway}}'], text=True,
                                  env=env, timeout=15).strip()


def reserve_relay(host, port=18759):
    lease = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lease.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            lease.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        lease.bind((host, port))
        return lease
    except BaseException:
        lease.close()
        raise


def check_endpoint(arm, startup_log, env):
    import urllib.request
    actual = subprocess.check_output(['docker', 'image', 'inspect', IMAGE, '--format',
                                     '{{.Id}} {{.Os}}/{{.Architecture}}'], env=env,
                                    text=True, timeout=30).strip()
    if actual != IMAGE + ' linux/amd64':
        raise ValueError('Native tool image differs')
    size, step = arm.split('-')[1], arm.rsplit('-', 1)[1]
    pins = {name: sha for sha, name in (line.split() for line in
            (HERE / 'TRAINING_SHA256_v2.txt').read_text(encoding='utf-8').splitlines()
            if line.strip() and not line.startswith('#'))}
    text = Path(startup_log).read_text(encoding='utf-8-sig')
    values = dict(token.split('=', 1) for line in text.splitlines()
                  if line.startswith('spark_service ') for token in line.split()[1:])
    if (values.get('size') != size or values.get('profile') != 'yarn128'
            or values.get('model_length') != '131072'
            or values.get('revision') != BASE_REVISIONS[size]
            or values.get(f'adapter_{step}_sha256') != pins[f'out58_{size}_v2/checkpoint-{step}']
            or not values.get('image', '').startswith('sha256:')):
        raise ValueError('Spark actual startup identity differs')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(SPARK + '/models', timeout=10) as stream:
        models = json.load(stream)['data']
    selected = [row for row in models if row.get('id') == arm]
    if len(selected) != 1 or selected[0].get('max_model_len') != 131072:
        raise ValueError('Live Spark arm or context differs')
    return {'startup': values, 'startup_log_sha256': digest(startup_log),
            'native_image': actual, 'live_model': selected[0]}


def make_ledger_class(base):
    class CompletionLedger(base.AdmissionLedger):
        def __init__(self, **kwargs):
            self.completion_limit = LIMITS['max_completion_tokens']
            self.reply_reservation = LIMITS['max_reply_tokens']
            super().__init__(**kwargs)

        def snapshot(self):
            with self.lock:
                result = super().snapshot()
                result.update(max_completion_tokens=self.completion_limit,
                              charged_completion_including_unknown_reservations=sum(
                                  row.get('charged_completion', self.reply_reservation)
                                  for row in self.calls.values()),
                              completion_reservation_per_call=self.reply_reservation,
                              completion_reservation_policy='reserve full native reply cap without rewriting body')
                return result

        def admit(self, call_id, **kwargs):
            with self.lock:
                used = sum(row.get('charged_completion', self.reply_reservation)
                           for row in self.calls.values())
                if used + self.reply_reservation > self.completion_limit:
                    raise base.BudgetExceeded('Unified cumulative completion budget exhausted')
                result = super().admit(call_id, **kwargs)
                self.calls[call_id]['charged_completion'] = self.reply_reservation
                self.calls[call_id]['completion_usage_state'] = 'RESERVED_UNKNOWN'
                self._save()
                return result

        def settle(self, call_id, *, usage, response_id=None):
            with self.lock:
                super().settle(call_id, usage=usage, response_id=response_id)
                row = self.calls[call_id]
                value = usage.get('completion_tokens', usage.get('output_tokens')) if isinstance(usage, dict) else None
                if type(value) is int and value >= 0 and base.actual_io(usage) is not None:
                    previous = row.get('charged_completion')
                    if row.get('completion_usage_state') == 'EXACT' and value != previous:
                        raise ValueError('Conflicting exact completion usage')
                    row.update(charged_completion=value, completion_usage_state='EXACT')
                    if value > self.reply_reservation:
                        self.breached = True
                    if sum(v.get('charged_completion', self.reply_reservation) for v in self.calls.values()) > self.completion_limit:
                        self.breached = True
                self._save()
    return CompletionLedger


def check_native_body(parsed, arm):
    if not isinstance(parsed, dict) or parsed.get('model') != arm or not isinstance(parsed.get('messages'), list):
        raise ValueError('Expected unchanged fixed-arm native messages')
    caps = [parsed[k] for k in ('max_tokens', 'max_completion_tokens') if k in parsed]
    if not caps or any(type(v) is not int or not 0 < v <= LIMITS['max_reply_tokens'] for v in caps):
        raise ValueError('Native per-reply budget differs')


def run_native(attempt, arm, env, lease, endpoint):
    relay = import_file('corpus_audit_relay57', HERE / 'lib/audit_relay57.py')
    budgets = import_file('corpus_native_budget', HERE / 'lib/native_budget.py')
    Ledger = make_ledger_class(budgets)
    ledger = Ledger(max_requests=LIMITS['max_requests'], max_io_tokens=131072 * LIMITS['max_requests'],
                    max_seconds=LIMITS['wall_seconds'], reservation_tokens=131072,
                    reservation_basis='one full fixed Spark context per admitted HTTP call',
                    model=arm, output=attempt / 'budget.json')
    secret = 'loopback-' + secrets.token_hex(16)
    model = {'api_key': secret, 'model': arm, 'input_modalities': ['text'],
             'max_tokens': LIMITS['max_reply_tokens'], 'context_window': 131072,
             'context_tokens': 131072, 'compatibility': {'supportsUsageInStreaming': True}}

    class PrivateHandler(relay.AuditHandler):
        def do_POST(self):
            if not hmac.compare_digest(self.headers.get('Authorization', '').encode(), ('Bearer ' + secret).encode()):
                return self.reply_error(401, 'This relay belongs to one pinned isolated attempt')
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 128 * 1024 * 1024:
                    return self.reply_error(413, 'Missing or excessive request body')
                body = self.rfile.read(length)
                if len(body) != length:
                    return self.reply_error(400, 'Incomplete native request body')
                check_native_body(json.loads(body), arm)
                remaining = LIMITS['wall_seconds'] - (time.monotonic() - ledger.started)
                self.server.timeout = min(self.server.timeout, max(0.1, remaining))
            except (ValueError, TypeError) as error:
                return self.reply_error(400, str(error))
            original = self.rfile
            self.rfile = io.BytesIO(body)
            try:
                super().do_POST()
            finally:
                self.rfile = original

    class ExclusiveAuditServer(relay.AuditServer):
        allow_reuse_address = False
        daemon_threads = False

        def server_bind(self):
            self.socket.close()
            self.socket = lease
            self.server_address = lease.getsockname()
            self.server_name = socket.getfqdn(self.server_address[0])
            self.server_port = self.server_address[1]

    server = None
    thread = None
    started = time.monotonic()
    result = {'schema': 'wrd58-corpus-producer-result-v1', 'arm': arm,
              'budget_limits': LIMITS, 'quality_judged': False,
              'native_loop_modified': False, 'tool_returns_modified': False}
    with tempfile.TemporaryDirectory(prefix='wrd58-private-') as directory:
        local_cfg = Path(directory) / 'local.json'
        upstream_cfg = Path(directory) / 'upstream.json'
        local_cfg.write_text(json.dumps(model | {'base_url': LOCAL}), encoding='utf-8')
        upstream_cfg.write_text(json.dumps(model | {'base_url': SPARK}), encoding='utf-8')
        try:
            server = ExclusiveAuditServer(lease.getsockname(), upstream_cfg, attempt / 'model_http',
                       timeout=LIMITS['wall_seconds'], max_calls=LIMITS['max_requests'],
                       purpose='wrd58_real_skill_production_effect_evaluation_not_SFT', budget_guard=ledger)
            server.RequestHandlerClass = PrivateHandler
            save_new(attempt / 'dispatch.json', {'arm': arm, 'limits': LIMITS, 'endpoint': endpoint,
                     'request_sha256': digest(attempt / 'request.json'),
                     'native_workspace_binding': native_workspace_binding_proof(attempt),
                     'relay_single_owner': True, 'pid': os.getpid()})
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            launch = [sys.executable, '-B', '-X', 'utf8', str(RUNTIME / 'consumer.py'),
                      str(attempt / 'request.json'), str(attempt / 'response.json'), '--image', IMAGE,
                      '--timeout', str(LIMITS['wall_seconds']), '--credentials', str(local_cfg), '--backend', 'native']
            completed = subprocess.run(launch, cwd=attempt / 'workspace', env=env, check=False)
            result['returncode'] = completed.returncode
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            result.update(returncode=1, error_type=type(error).__name__, error=str(error))
        finally:
            if thread is not None:
                server.shutdown()
                thread.join()
            if server is not None:
                server.server_close()
            result.update(budget=ledger.snapshot(), wall_seconds=time.monotonic() - started)
            result['actual_skill_md'] = sorted(str(p.relative_to(attempt / 'workspace'))
                for p in (attempt / 'workspace/outputs/skill').rglob('SKILL.md') if p.is_file())
            result['artifact_status'] = ('ARTIFACT_PRESENT_UNREVIEWED' if result['actual_skill_md']
                                         else 'NO_SKILL_ARTIFACT')
            save_new(attempt / 'producer_result.json', result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('verify', 'prepare', 'producer'))
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--attempt', type=int, default=1)
    parser.add_argument('--out-dir', type=Path, default=HERE / 'corpus_runs')
    parser.add_argument('--startup-log', type=Path)
    parser.add_argument('--allow-seen-diagnostic', action='store_true')
    args = parser.parse_args(argv)
    try:
        case, _, _ = verify_case(args.corpus, args.source)
        if args.action == 'verify':
            print(json.dumps({'source_id': args.source, 'files_verified': len(case['resources']) + 4,
                              'effect_eligible': is_effect_eligible(case), 'model_calls': 0}))
            return 0
        if not args.arm:
            parser.error('--arm is required for prepare/producer')
        if args.action == 'prepare':
            attempt, receipt = prepare(args.corpus, args.source, args.arm, args.attempt, args.out_dir,
                                       allow_seen=args.allow_seen_diagnostic)
            print(json.dumps({'attempt': str(attempt), 'receipt': receipt}, ensure_ascii=False))
            return 0
        if args.startup_log is None:
            parser.error('--startup-log is required for producer')
        env = os.environ.copy()
        check_runtime()
        endpoint = check_endpoint(args.arm, args.startup_log, env)
        lease = reserve_relay(relay_bind(env))
        try:
            attempt = args.out_dir.resolve() / args.source / args.arm / f'attempt-{args.attempt:03d}'
            if attempt.exists():
                verify_prepared(attempt, args.corpus, args.source, args.arm, args.attempt,
                                args.allow_seen_diagnostic)
            else:
                attempt, _ = prepare(args.corpus, args.source, args.arm, args.attempt, args.out_dir,
                                     allow_seen=args.allow_seen_diagnostic)
            result = run_native(attempt, args.arm, env, lease, endpoint)
            print(json.dumps(result, ensure_ascii=False))
            return int(result['returncode'] != 0)
        finally:
            lease.close()
    except (KeyError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
