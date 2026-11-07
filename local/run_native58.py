#!/usr/bin/env python3
"""Start one pinned OpenClaw session and record the model HTTP exchange."""

import argparse
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request


HERE = Path(__file__).resolve().parent
RUNTIME = HERE / 'runtime'
IMAGE = 'sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
ARM_IDS = tuple(f'wrd58-{size}-{step}' for size in ('8b', '14b') for step in (0, 26))
CONTEXT = {'smoke32': 32768, 'yarn128': 131072}
SPARK = 'http://127.0.0.1:18758/v1'
LOCAL = 'http://host.docker.internal:18759/v1'
SKILL = 'wrd58-route-check'
DEV_FREEZE_SHA = '92c05839fc9bdc755117cdd00feda549ccd9ee1c95a7cce06ac9aa2379ee04b7'
PILOT = HERE / 'dev_pilot'
BASE_REVISIONS = {'8b': 'b968826d9c46dd6066d109eabc6255188de91218',
                  '14b': '40c069824f4251a91eefaf281ebe4c544efd3e18'}


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_image(env):
    image = subprocess.check_output(
        ['docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}} {{.Os}}/{{.Architecture}}'],
        text=True, env=env, timeout=30).strip()
    if image != IMAGE + ' linux/amd64':
        raise ValueError('Frozen OpenClaw image differs: ' + image)


def relay_bind(env):
    if sys.platform == 'win32':
        return '127.0.0.1'
    if sys.platform != 'linux':
        raise ValueError('Use an amd64 Linux host or Windows Docker Desktop with the pinned image')
    return subprocess.check_output(
        ['docker', 'network', 'inspect', 'bridge', '--format', '{{(index .IPAM.Config 0).Gateway}}'],
        text=True, env=env, timeout=15).strip()


def check_spark(arm, profile):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(SPARK + '/models', timeout=5) as response:
        rows = json.load(response)['data']
    expected = {f'wrd58-{arm.split("-")[1]}-{step}' for step in (0, 26)}
    matches = [row for row in rows if row['id'] in expected]
    if {row['id'] for row in matches} != expected:
        raise ValueError(f'Spark /v1/models must expose the pinned pair {sorted(expected)}')
    bare_id = f'wrd58-{arm.split("-")[1]}-bare'
    lengths = {row['max_model_len'] for row in rows if row['id'] in expected | {bare_id}
               and row.get('max_model_len') is not None}
    if lengths != {CONTEXT[profile]}:
        raise ValueError(f'Spark model context differs: expected {CONTEXT[profile]}, saw {lengths}')
    return {'selected': arm, 'pair': sorted(expected), 'max_model_len': CONTEXT[profile]}


def check_runtime():
    receipt = load(RUNTIME / 'WRAPPER_RECEIPT.json')
    if receipt['image_id'] != IMAGE or receipt['provider_base_url'] != LOCAL:
        raise ValueError('Prepared runtime has different image or provider')
    for name, sha in receipt['prepared_sha256'].items():
        if Path(name).name != name or digest(RUNTIME / name) != sha:
            raise ValueError('Runtime pin differs: ' + name)


def pinned_file(materials, pin):
    path = (materials / pin['path']).resolve()
    if (not path.is_relative_to(materials) or path.stat().st_size != pin['bytes']
            or digest(path) != pin['sha256']):
        raise ValueError('DEV file pin differs: ' + pin['path'])
    return path


def stage_pilot(materials):
    manifest = materials / 'DEV_MATERIALS.json'
    if digest(manifest) != DEV_FREEZE_SHA:
        raise ValueError('Frozen DEV material manifest differs')
    groups = load(manifest)['source_groups']
    ready, = [item for item in groups if item['status'] == 'READY_TEXT_ONLY_DEV']
    maker = ready['maker']
    source = pinned_file(materials, maker['source'])
    prompt = pinned_file(materials, maker['prompt']).read_text(encoding='utf-8-sig')
    PILOT.mkdir(parents=True, exist_ok=False)
    producer_pins = {}
    for arm in ARM_IDS:
        attempt = PILOT / 'producers' / arm
        inputs = attempt / 'workspace/inputs'
        inputs.mkdir(parents=True)
        staged = inputs / 'source.json'
        shutil.copyfile(source, staged)
        request = {'protocol': 'native-openclaw-only-v1', 'stage': 'wrd58_dev_producer',
                   'task_id': ready['source_id'], 'input': prompt, 'context': [], 'followup_inputs': [],
                   'resources': [{'path': str(staged), 'mount': 'inputs/source.json'}], 'learned_skills': []}
        path = attempt / 'request.json'
        save(path, request)
        producer_pins[arm] = {'request_sha256': digest(path), 'source_sha256': digest(staged)}
    receipt = {'status': 'STAGED_AWAITING_SPARK', 'scope': 'one_text_only_development_source_producer_only',
               'source_id': ready['source_id'], 'frozen_groups': len(groups), 'ready_groups': 1,
               'maker_arms': producer_pins, 'consumer_briefs': {},
               'shared_consumer_briefs': 0, 'planned_independent_consumer_runs': 0,
               'planned_consumer_runs': 0, 'downstream_consumption': 'deferred_by_user',
               'dev_materials_sha256': DEV_FREEZE_SHA, 'model_calls': 0}
    save(PILOT / 'stage_receipt.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False))


def check_business_gate():
    image_ids = set()
    manifest = HERE / 'TRAINING_SHA256_v2.txt'
    pins = {name: sha for sha, name in (line.split() for line in manifest.read_text(encoding='utf-8').splitlines()
                                      if line.strip() and not line.startswith('#'))}
    for size in ('8b', '14b'):
        folder = HERE / 'spark_receipts'
        path = folder / f'smoke_{size}_128k.json'
        report = load(path)
        rows = report['synthetic_long_input_arms']
        expected = {f'wrd58-{size}-{step}' for step in (0, 26)}
        if (report['status'] != 'pass' or report['requested_context'] != 131072
                or {row['model'] for row in rows} != expected
                or not all(row['requested_max_tokens'] == 32768
                           and row['usage']['prompt_tokens'] >= 65806 for row in rows)):
            raise ValueError(f'Spark long-context receipt differs: {path}')
        startup = (folder / f'serve_{size}_128k.log').read_text(encoding='utf-8-sig')
        tokens = dict(token.split('=', 1) for line in startup.splitlines() if line.startswith('spark_service ')
                      for token in line.split()[1:])
        if (tokens.get('size') != size or tokens.get('profile') != 'yarn128'
                or tokens.get('model_length') != '131072' or tokens.get('revision') != BASE_REVISIONS[size]
                or any(tokens.get(f'adapter_{step}_sha256') != pins[f'out58_{size}_v2/checkpoint-{step}']
                       for step in (0, 26)) or not tokens.get('image', '').startswith('sha256:')):
            raise ValueError(f'Spark startup adapter, revision or image evidence differs for {size}')
        image_ids.add(tokens['image'])
    if len(image_ids) != 1:
        raise ValueError('Spark must use one common serving image digest for both sizes')
    for arm in ARM_IDS:
        receipts = (HERE / 'runs').glob(f'smoke-yarn128-{arm}-*/smoke_result.json')
        if not any(all((row['status'] == 'PASS', row['arm'] == arm, row['profile'] == 'yarn128'))
                   for row in map(load, receipts)):
            raise ValueError(f'Native yarn128 smoke has no PASS receipt for {arm}')


def smoke_request(attempt):
    workspace = attempt / 'workspace'
    inputs = workspace / 'inputs'
    skill = workspace / 'learned_skills' / SKILL
    inputs.mkdir(parents=True)
    skill.mkdir(parents=True)
    save(inputs / 'values.json', {'a': 17, 'b': 25})
    (skill / 'SKILL.md').write_text(
        '---\nname: wrd58-route-check\ndescription: 读取输入 JSON 并实际生成技术验机结果。\n---\n'
        '# 路由技术验收\n请使用 exec 运行 `python /workspace/skills/wrd58-route-check/check.py`。'
        '脚本读取 inputs/values.json，生成 outputs/result.json。随后读回输出并报告路径。\n',
        encoding='utf-8')
    (skill / 'check.py').write_text(
        'import json\nfrom pathlib import Path\n'
        'data=json.loads(Path("/workspace/inputs/values.json").read_text())\n'
        'out=Path("/workspace/outputs/result.json")\nout.parent.mkdir(exist_ok=True)\n'
        'out.write_text(json.dumps({"sum":data["a"]+data["b"],"proof":"native_exec"}))\n',
        encoding='utf-8')
    request = {'protocol': 'native-openclaw-only-v1', 'stage': 'technical',
               'task_id': 'wrd58-spark-native-transport',
               'input': '完成路由技术验收。原生发现 wrd58-route-check 技能，使用 read 完整读取 SKILL.md，'
                        '按技能用 exec 运行程序，读回 outputs/result.json 并告知路径。',
               'context': [], 'followup_inputs': [], 'required_commands': ['python'],
               'resources': [{'path': str(inputs / 'values.json'), 'mount': 'inputs/values.json'}],
               'learned_skills': [{'id': SKILL, 'path': str(skill),
                                   'files': {f.name: digest(f) for f in sorted(skill.iterdir())}}]}
    save(attempt / 'request.json', request)


def run_session(attempt, arm, context, output_tokens, timeout, env):
    max_requests = 8 if timeout == 300 else 24
    relay_module = import_file('relay57', HERE / 'lib/audit_relay57.py')
    budgets = import_file('budget57', HERE / 'lib/native_budget.py')
    ledger = budgets.AdmissionLedger(max_requests=max_requests, max_io_tokens=context * max_requests,
                                      max_seconds=timeout, reservation_tokens=context,
                                      reservation_basis='one full frozen Spark model context per HTTP request',
                                      model=arm, output=attempt / 'budget.json')
    placeholder = 'loopback-' + secrets.token_hex(16)
    model = {'api_key': placeholder, 'model': arm, 'input_modalities': ['text'],
             'max_tokens': output_tokens, 'context_window': context,
             'context_tokens': context,
             'compatibility': {'supportsUsageInStreaming': True}}
    class PrivateHandler(relay_module.AuditHandler):
        def do_POST(self):
            expected = 'Bearer ' + placeholder
            if not hmac.compare_digest(self.headers.get('Authorization', '').encode(), expected.encode()):
                return self.reply_error(401, 'This relay serves only the pinned isolated run')
            super().do_POST()

    with tempfile.TemporaryDirectory(prefix='wrd58-credentials-') as temp:
        local_cfg = Path(temp) / 'model_local.json'
        upstream_cfg = Path(temp) / 'model_upstream.json'
        save(local_cfg, model | {'base_url': LOCAL})
        save(upstream_cfg, model | {'base_url': SPARK})
        server = relay_module.AuditServer((relay_bind(env), 18759), upstream_cfg, attempt / 'model_http',
                                          timeout=timeout, max_calls=max_requests,
                                          purpose='wrd58_native_dev', budget_guard=ledger)
        server.RequestHandlerClass = PrivateHandler
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            launch = [sys.executable, '-B', '-X', 'utf8', str(RUNTIME / 'consumer.py'),
                      str(attempt / 'request.json'), str(attempt / 'response.json'), '--image', IMAGE,
                      '--timeout', str(timeout), '--credentials', str(local_cfg), '--backend', 'native']
            result = subprocess.run(launch, cwd=attempt / 'workspace', env=env, check=False)
            return result.returncode, ledger.snapshot()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


def smoke_result(attempt, returncode, budget):
    transport = attempt / 'openclaw_transport'
    response = load(attempt / 'response.json') if (attempt / 'response.json').is_file() else {}
    artifact = attempt / 'workspace/outputs/result.json'
    traces = list((attempt / 'model_http').glob('*/receipt.json'))
    receipts = [load(path) for path in traces]
    requests = [load(path) for path in (attempt / 'model_http').glob('*/request.raw.json')]
    responses = []
    for path in (attempt / 'model_http').glob('*/response.raw.*'):
        blob = path.read_text(encoding='utf-8')
        parts = [line.removeprefix('data:').strip() for line in blob.splitlines() if line.startswith('data:')]
        if path.suffix == '.json':
            parts = [blob]
        for part in parts:
            if part and part != '[DONE]':
                try:
                    responses.extend(choice.get('delta', choice.get('message', {}))
                                     for choice in json.loads(part).get('choices', []))
                except ValueError:
                    continue
    try:
        correct_artifact = load(artifact) == {'sum': 42, 'proof': 'native_exec'}
    except (OSError, ValueError):
        correct_artifact = False
    checks = {'native_finished': returncode == 0,
              'full_skill_read': SKILL in response.get('loaded_skill_ids', []),
              'native_exec_observed': any(row.get('name') == 'exec' and not row.get('observed_failure')
                                          for row in response.get('runtime', {}).get('tools', [])),
              'artifact_ok': correct_artifact,
              'native_trace_saved': (transport / 'session_events.jsonl').is_file(),
              'tools_forwarded': any(row.get('tools_count', 0) > 0 for row in receipts),
              'tool_result_in_next_model_request': any(message.get('role') == 'tool' for row in requests
                                                       for message in row.get('messages', [])),
              'structured_tool_calls': any(message.get('tool_calls') for message in responses),
              'reasoning_field_observed': any(message.get('reasoning_content') or message.get('reasoning')
                                              for message in responses),
              'complete_reported_usage': bool(receipts) and len(receipts) == budget['requests_admitted']
                                         and budget['unknown_usage_calls'] == 0 and not budget['breached'],
              'upstream_identity_matches': bool(receipts) and all(row.get('model_returned') == budget['model']
                                                              for row in receipts)}
    return checks


def skill_tree(root):
    if not root.resolve().is_relative_to(root.parent.parent.resolve()):
        raise ValueError('Skill escapes its producer workspace')
    if not (root / 'SKILL.md').is_file() or root.is_symlink() or root.parent.is_symlink():
        raise ValueError('Expected a regular skill tree with SKILL.md')
    entries = sorted(root.rglob('*'))
    if any(path.is_symlink() or not (path.is_dir() or path.is_file()) for path in entries):
        raise ValueError('Skill tree has a symlink or non-regular entry')
    return {path.relative_to(root).as_posix(): digest(path) for path in entries if path.is_file()}


def freeze_skills():
    rows = {}
    for arm in ARM_IDS:
        producer = PILOT / 'producers' / arm
        result = load(producer / 'producer_result.json')
        skill = producer / 'workspace/outputs/skill'
        if result['returncode'] != 0 or not (skill / 'SKILL.md').is_file():
            rows[arm] = {'status': 'HOLD', 'producer_returncode': result['returncode']}
        else:
            try:
                rows[arm] = {'status': 'PINNED', 'files': skill_tree(skill)}
            except ValueError as error:
                rows[arm] = {'status': 'HOLD', 'reason': str(error)}
    path = PILOT / 'skill_freeze.json'
    with path.open('x', encoding='utf-8') as handle:
        json.dump({'schema': 'wrd58-dev-skill-freeze-v1', 'arms': rows}, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps(rows, ensure_ascii=False))


def consumer_case(case, arm, env):
    brief_root = PILOT / 'consumer_inputs' / case
    stage = load(PILOT / 'stage_receipt.json')
    pins = stage['consumer_briefs'].get(case)
    if not pins or {p.name: digest(p) for p in brief_root.iterdir()} != pins:
        raise ValueError('Unknown or changed staged consumer brief')
    freeze = load(PILOT / 'skill_freeze.json')['arms']
    attempt = PILOT / 'consumers' / case / arm
    attempt.mkdir(parents=True, exist_ok=False)
    actor = 'wrd58-8b-0'
    if arm != 'no-skill' and freeze[arm]['status'] != 'PINNED':
        result = {'status': 'HOLD_MISSING_PRODUCER_SKILL', 'model_calls': 0, 'actor': actor}
        save(attempt / 'consumer_result.json', result)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    workspace = attempt / 'workspace'
    inputs = workspace / 'inputs'
    shutil.copytree(brief_root, inputs)
    resources = [{'path': str(inputs / name), 'mount': 'inputs/' + name} for name in sorted(pins)]
    learned_skills = []
    if arm != 'no-skill':
        source = PILOT / 'producers' / arm / 'workspace/outputs/skill'
        files = freeze[arm]['files']
        if skill_tree(source) != files:
            raise ValueError('Producer skill bytes differ from frozen skill')
        target = workspace / 'learned_skills' / 'wrd58-pilot-skill'
        shutil.copytree(source, target)
        if skill_tree(target) != files:
            raise ValueError('Staged copy differs from frozen skill')
        learned_skills.append({'id': target.name, 'path': str(target), 'files': files})
    save(attempt / 'request.json',
         {'protocol': 'native-openclaw-only-v1', 'stage': 'wrd58_dev_consumer', 'task_id': case,
          'input': (inputs / 'request.txt').read_text(encoding='utf-8-sig'), 'context': [],
          'followup_inputs': [], 'resources': resources, 'learned_skills': learned_skills})
    save(attempt / 'endpoint.json', check_spark(actor, 'yarn128'))
    return run_business(attempt, actor, env, 'consumer')


def run_business(attempt, model, env, role):
    record = {'model': model, 'scope': f'single_dev_{role}_not_quality_judgment'}
    path = attempt / f'{role}_result.json'
    try:
        rc, budget = run_session(attempt, model, 131072, 32768, 1800, env)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        save(path, record | {'returncode': 1, 'error': str(error)})
        raise
    save(path, record | {'returncode': rc, 'budget': budget})
    return rc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'doctor', 'smoke', 'producer', 'freeze-skills', 'consume'))
    parser.add_argument('--arm', choices=(*ARM_IDS, 'no-skill'))
    parser.add_argument('--case', choices=('partner_notice_confirmed_and_pending', 'public_notice_sparse_brief'))
    parser.add_argument('--profile', choices=tuple(CONTEXT), default='yarn128')
    parser.add_argument('--materials', type=Path)
    parser.add_argument('--attempt', type=int, default=1)
    args = parser.parse_args()
    if args.action in ('freeze-skills', 'consume'):
        parser.error('deferred_by_user: downstream skill consumption is paused; '
                     'this handoff evaluates skill generation with producer only')
    env = os.environ.copy()
    try:
        if args.action == 'stage':
            if args.materials is None:
                parser.error('--materials is required for stage')
            stage_pilot(args.materials.resolve())
            return 0
        if args.action == 'freeze-skills':
            freeze_skills()
            return 0
        if not args.arm:
            parser.error('--arm is required for this action')
        if args.arm == 'no-skill' and args.action != 'consume':
            parser.error('no-skill is only valid for consume')
        if args.action == 'consume':
            if args.case is None or args.profile != 'yarn128':
                parser.error('consume requires --case and the shared yarn128 profile')
            check_image(env)
            check_runtime()
            check_business_gate()
            return consumer_case(args.case, args.arm, env)
        check_image(env)
        check = check_spark(args.arm, args.profile)
        if args.action == 'doctor':
            print(json.dumps({'local_image': IMAGE, 'spark': check}, ensure_ascii=False))
            return 0
        check_runtime()
        if args.profile != 'yarn128':
            raise ValueError('The pinned native 53-tool request requires the shared yarn128 profile')
        if args.action == 'producer':
            check_business_gate()
            attempt = PILOT / 'producers' / args.arm
            staged = load(PILOT / 'stage_receipt.json')['maker_arms'][args.arm]
            if (digest(attempt / 'request.json') != staged['request_sha256']
                    or digest(attempt / 'workspace/inputs/source.json') != staged['source_sha256']):
                raise ValueError('Producer staging pins differ')
            if (attempt / 'endpoint.json').exists():
                raise ValueError('Producer already dispatched; preserve the existing evidence')
            save(attempt / 'endpoint.json', check)
            return run_business(attempt, args.arm, env, 'producer')
        attempt = HERE / 'runs' / f'smoke-{args.profile}-{args.arm}-{args.attempt:02d}'
        attempt.mkdir(parents=True, exist_ok=False)
        save(attempt / 'endpoint.json', check)
        smoke_request(attempt)
        rc, budget = run_session(attempt, args.arm, CONTEXT[args.profile], 1024, 300, env)
        checks = smoke_result(attempt, rc, budget)
        verdict = {'status': 'PASS' if all(checks.values()) else 'HOLD',
                   'scope': 'synthetic_native_transport_only', 'checks': checks,
                   'arm': args.arm, 'profile': args.profile, 'attempt': str(attempt)}
        save(attempt / 'smoke_result.json', verdict)
        print(json.dumps(verdict, ensure_ascii=False))
        return int(verdict['status'] != 'PASS')
    except (KeyError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
