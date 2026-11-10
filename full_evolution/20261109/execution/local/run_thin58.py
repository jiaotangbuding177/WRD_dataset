#!/usr/bin/env python3
"""Dispatch one native session per WRD phase and preserve each physical handoff."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import run_autonomous58 as autonomous


HERE = Path(__file__).resolve().parent
PHASES = ('route', 'make', 'check')
LIMITS = dict(zip(PHASES, (
    {'max_requests': 12, 'max_reply_tokens': 8192, 'max_completion_tokens': 32768, 'wall_seconds': 1800},
    {'max_requests': 48, 'max_reply_tokens': 32768, 'max_completion_tokens': 98304, 'wall_seconds': 5400},
    {'max_requests': 36, 'max_reply_tokens': 16384, 'max_completion_tokens': 65536, 'wall_seconds': 3600},
)))
GLM = 'glm-5.3-flash'
SPARK_ARMS = ('wrd58-14b-0', 'wrd58-14b-241')
ROUTE_FILE = 'outputs/route.json'
DECISION_FILE = 'outputs/evidence/decision.json'
SKILL_ROOT = 'outputs/skill'
ERRORS = (KeyError, OSError, TypeError, ValueError, RuntimeError, subprocess.SubprocessError)


@contextmanager
def slot_lock(root):
    """Protect an arm across all of its numbered attempts, including process death."""
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.slot.lock').open('a+b') as lock:
        lock.seek(0)
        try:
            if sys.platform == 'win32':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError('This case and arm already have an active launcher') from error
        yield


def prompt_set(helper, path):
    prompts = helper.load(path)
    if set(prompts) != set(PHASES) or any(not isinstance(s, str) or not s.strip() for s in prompts.values()):
        raise ValueError('Expected route, make and check prompt strings')
    return prompts, helper.digest(path)


def stage_path(attempt, phase):
    return attempt / 'stages' / phase / 'attempt-001'


def request_for(workspace, phase, prompt, mounts):
    limits = LIMITS[phase]
    notice = (f'\n\n本阶段上限：{limits["max_requests"]} 次模型 HTTP 请求，'
              f'单次回复 {limits["max_reply_tokens"]} tokens，累计输出 '
              f'{limits["max_completion_tokens"]} tokens（含思考和收尾），'
              f'总计 {limits["wall_seconds"]} 秒。请按真实工件报告。')
    return {'protocol': 'native-openclaw-only-v1', 'stage': 'wrd58_thin_' + phase,
            'task_id': 'thin-wrd58-' + phase, 'input': prompt + notice, 'context': [],
            'followup_inputs': [], 'learned_skills': [],
            'resources': [{'path': str(workspace / mount), 'mount': mount} for mount in mounts]}


def artifact_files(helper, root):
    if not root.exists() and not root.is_symlink():
        return {}
    if not root.is_dir() or root.is_symlink() or getattr(root, 'is_junction', lambda: False)():
        raise ValueError('Artifact root must be an ordinary directory')
    files = {}
    for item in sorted(root.rglob('*')):
        if item.is_symlink() or getattr(item, 'is_junction', lambda: False)():
            raise ValueError('Native artifact tree contains a link')
        if item.is_file():
            files[item.relative_to(root).as_posix()] = helper.digest(item)
        elif not item.is_dir():
            raise ValueError('Native artifact tree contains a nonregular entry')
    return files


def stage_inputs(helper, corpus, row, phase, prior):
    index, copies, indexes = autonomous.source_tree(helper, corpus, row)
    generated = {'inputs/index.json': {'sources': [
        {k: v for k, v in source.items() if k != 'case_sha256'} for source in index]}, **indexes}
    mounts = ['inputs/index.json']
    if phase != 'route':
        route_workspace, route_sha = prior['route']
        copies['inputs/route.json'] = (route_workspace / ROUTE_FILE, route_sha)
        mounts.append('inputs/route.json')
    if phase == 'check':
        make_workspace, candidate, make_outputs, native_events = prior['make']
        for path, sha in candidate.items():
            copies['inputs/candidate/' + path] = (make_workspace / SKILL_ROOT / path, sha)
        evidence = {path: sha for path, sha in make_outputs.items() if not path.startswith('skill/')}
        for path, sha in evidence.items():
            copies['inputs/make_evidence/' + path] = (make_workspace / 'outputs' / path, sha)
        events_mount = None
        if native_events is not None:
            events_path, events_sha = native_events
            events_mount = 'inputs/make_native_events.jsonl'
            copies[events_mount] = (make_workspace.parent / events_path, events_sha)
        generated['inputs/candidate_manifest.json'] = {'candidate_root': '/workspace/inputs/candidate',
                                                       'files': candidate,
                                                       'make_evidence_root': '/workspace/inputs/make_evidence',
                                                       'make_evidence_files': evidence,
                                                       'make_native_events': '/workspace/' + events_mount if events_mount else None}
        mounts.append('inputs/candidate_manifest.json')
    return copies, generated, mounts


def verify_stage(helper, stage, plan, phase, prompt, copies, generated, mounts):
    workspace = stage / 'workspace'
    receipt = helper.load(stage / 'stage_receipt.json')
    req = stage / 'request.json'
    expected = request_for(workspace, phase, prompt, mounts)
    if (receipt['plan'] != plan or receipt['phase'] != phase or receipt['request_sha256'] != helper.digest(req)
            or helper.load(req) != expected or receipt['budget'] != LIMITS[phase]):
        raise ValueError('Prepared stage request or experiment binding differs')
    files = receipt['files']
    if set(files) != {'README.md', '.gitignore', *copies, *generated}:
        raise ValueError('Prepared stage file set differs')
    generated_sha = {path: hashlib.sha256((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()).hexdigest()
                     for path, value in generated.items()}
    if (any(files[path] != sha for path, (_, sha) in copies.items())
            or any(files[path] != sha for path, sha in generated_sha.items())):
        raise ValueError('Frozen source or preceding artifact differs')
    if not (stage / 'dispatch.json').exists():
        if (autonomous.file_hashes(helper, workspace) != files
                or helper.run_git(workspace, 'rev-parse', 'HEAD') != receipt['git_commit']):
            raise ValueError('Unexpected pre-dispatch file or Git HEAD change')
    return receipt


def prepare_stage(helper, corpus, row, attempt, plan, phase, prompt, prior):
    stage = stage_path(attempt, phase)
    workspace = stage / 'workspace'
    copies, generated, mounts = stage_inputs(helper, corpus, row, phase, prior)
    helper.LIMITS = dict(LIMITS[phase])
    if not stage.exists():
        workspace.mkdir(parents=True, exist_ok=False)
        for mount, (source, sha) in copies.items():
            target = workspace / mount
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if helper.digest(target) != sha:
                raise ValueError('Copied source or preceding artifact differs: ' + mount)
        for mount, value in generated.items():
            target = workspace / mount
            target.parent.mkdir(parents=True, exist_ok=True)
            helper.save_new(target, value)
        (workspace / 'README.md').write_text(autonomous.README, encoding='utf-8', newline='\n')
        (workspace / '.gitignore').write_text('.openclaw/\n__pycache__/\n', encoding='utf-8', newline='\n')
        helper.run_git(workspace, 'init', '--quiet', '--template=')
        helper.run_git(workspace, 'config', 'user.name', 'WRD corpus preparation')
        helper.run_git(workspace, 'config', 'user.email', 'wrd-local@invalid')
        helper.run_git(workspace, 'add', '--', 'README.md', '.gitignore', 'inputs/index.json')
        helper.run_git(workspace, 'commit', '--quiet', '-m', 'Initialize repository-owned WRD task')
        helper.save_new(stage / 'request.json', request_for(workspace, phase, prompt, mounts))
        helper.save_new(stage / 'stage_receipt.json', {
            'schema': 'wrd58-thin-stage-v1', 'plan': plan, 'phase': phase,
            'budget': LIMITS[phase], 'files': autonomous.file_hashes(helper, workspace),
            'request_sha256': helper.digest(stage / 'request.json'), 'initial_user_turns': 1,
            'git_commit': helper.run_git(workspace, 'rev-parse', 'HEAD'),
            'git_tree': helper.run_git(workspace, 'rev-parse', 'HEAD^{tree}'),
            'native_workspace_binding': helper.native_workspace_binding_proof(stage), 'model_calls': 0,
        })
    return stage, verify_stage(helper, stage, plan, phase, prompt, copies, generated, mounts)


def read_artifact(helper, workspace, path, outputs):
    digest = outputs.get(path.removeprefix('outputs/'))
    if digest is None:
        return None
    try:
        value = helper.load(workspace / path)
    except (UnicodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def route_status(route, source_ids):
    if not route or route.get('status') not in ('MAKE', 'STOP', 'BLOCKED'):
        return 'INVALID_ROUTE_ARTIFACT'
    evidence = route.get('evidence')
    if (not isinstance(evidence, list) or not evidence
            or any(not isinstance(item, dict) or item.get('source_id') not in source_ids
                   or not item.get('ref') or not item.get('fact') for item in evidence)):
        return 'INVALID_ROUTE_ARTIFACT'
    detail = route.get('route')
    if route['status'] == 'MAKE' and (not isinstance(detail, dict) or not detail.get('id') or not detail.get('scope')):
        return 'INVALID_ROUTE_ARTIFACT'
    return route['status']


def stage_output(helper, stage, result, phase, source_ids):
    workspace = stage / 'workspace'
    output_files = artifact_files(helper, workspace / 'outputs')
    decision_path = ROUTE_FILE if phase == 'route' else DECISION_FILE
    decision = read_artifact(helper, workspace, decision_path, output_files)
    candidate = {path.removeprefix('skill/'): sha for path, sha in output_files.items()
                 if path.startswith('skill/')}
    selected_root = SKILL_ROOT
    has_skill = 'SKILL.md' in candidate and (workspace / SKILL_ROOT / 'SKILL.md').stat().st_size > 0
    expected_inputs = {path.removeprefix('inputs/'): sha
                       for path, sha in helper.load(stage / 'stage_receipt.json')['files'].items()
                       if path.startswith('inputs/')}
    actual_inputs = artifact_files(helper, workspace / 'inputs')
    changed_inputs = sorted(path for path, sha in expected_inputs.items() if actual_inputs.get(path) != sha)
    changed_inputs += sorted(path for path in actual_inputs if path.startswith('candidate/')
                             and path not in expected_inputs)
    event_paths = ('openclaw_transport/all_session_events.jsonl', 'openclaw_transport/session_events.jsonl')
    native_events = next(([path, helper.digest(stage / path)] for path in event_paths
                          if (stage / path).is_file() and not (stage / path).is_symlink()), None)
    budget = result.get('budget') or {}
    transport_errors = []
    for path in sorted((stage / 'model_http').glob('*/receipt.json')):
        receipt = helper.load(path)
        if receipt.get('status') != 'COMPLETE' or not 200 <= (receipt.get('http_status') or 0) < 300:
            transport_errors.append({'call': path.parent.name, 'status': receipt.get('status'),
                                     'http_status': receipt.get('http_status')})
    if result.get('returncode') != 0:
        status = 'NATIVE_NONZERO_EXIT'
    elif not (stage / 'dispatch.json').is_file() or not budget.get('requests_admitted') or transport_errors:
        status = 'NATIVE_TRANSPORT_INCOMPLETE'
    elif budget.get('breached'):
        status = 'NATIVE_BUDGET_BREACHED'
    elif changed_inputs:
        status = 'NATIVE_INPUT_CHANGED'
    elif phase == 'route':
        status = route_status(decision, source_ids)
    elif phase == 'make':
        verdict = (decision or {}).get('status')
        if verdict in ('STOP', 'BLOCKED'):
            status = verdict
        elif verdict == 'CANDIDATE':
            status = 'CANDIDATE_PRESENT' if has_skill else 'NO_SKILL_ARTIFACT'
        else:
            status = 'UNDECLARED_SKILL_ARTIFACT' if has_skill else 'NO_SKILL_ARTIFACT'
    else:
        decision = decision or {}
        verdict = decision.get('status')
        if verdict == 'KEEP':
            root = decision.get('package_root')
            if isinstance(root, str):
                root = root.removeprefix('/workspace/').removesuffix('/')
            if root == 'inputs/candidate':
                selected_root = root
                candidate = {path.removeprefix('candidate/'): sha for path, sha in actual_inputs.items()
                             if path.startswith('candidate/')}
                has_skill = 'SKILL.md' in candidate and (workspace / root / 'SKILL.md').stat().st_size > 0
            if root not in ('inputs/candidate', SKILL_ROOT):
                status = 'INVALID_CHECK_ARTIFACT'
            else:
                status = 'CANDIDATE_PRESENT' if has_skill else 'NO_CHECKED_SKILL_ARTIFACT'
        else:
            status = verdict if verdict in ('STOP', 'BLOCKED') else 'INVALID_CHECK_ARTIFACT'
    return {'phase': phase, 'status': status, 'returncode': result.get('returncode'),
            'budget': result.get('budget'), 'wall_seconds': result.get('wall_seconds'),
            'request_sha256': helper.digest(stage / 'request.json'),
            'producer_result_sha256': helper.digest(stage / 'producer_result.json'),
            'outputs': output_files, 'decision_path': decision_path,
            'decision_sha256': output_files.get(decision_path.removeprefix('outputs/')),
            'changed_inputs': changed_inputs, 'skill_files': candidate, 'native_events': native_events,
            'transport_errors': transport_errors,
            'package_root': selected_root if status == 'CANDIDATE_PRESENT' else None}


def run_stage(helper, native, stage, phase, plan, args):
    result_path = stage / 'producer_result.json'
    if (stage / 'dispatch.json').exists() and not result_path.exists():
        raise RuntimeError('Unfinished native dispatch already exists: ' + str(stage))
    if not result_path.exists():
        provider = native.build_provider(helper, plan['arm'], args.startup_log, args.glm_credentials)
        native.run_native_attempt(helper, stage, provider, LIMITS[phase])
    result = helper.load(result_path)
    if result.get('arm') != plan['arm'] or result.get('budget_limits') != LIMITS[phase]:
        raise ValueError('Native result belongs to another arm or budget')
    dispatch = stage / 'dispatch.json'
    if dispatch.is_file() and helper.load(dispatch).get('request_sha256') != helper.digest(stage / 'request.json'):
        raise ValueError('Native dispatch request binding differs')
    outcome = stage_output(helper, stage, result, phase, plan['source_ids'])
    path = stage / 'outcome.json'
    if path.exists():
        if helper.load(path) != outcome:
            raise ValueError('Preserved native artifact changed: ' + str(stage))
    else:
        helper.save_new(path, outcome)
    return outcome


def sum_meter(outcomes):
    keys = ('requests_admitted', 'charged_io_including_unknown_reservations',
            'charged_completion_including_unknown_reservations', 'unknown_usage_calls')
    meters = [outcome['budget'] or {} for outcome in outcomes]
    total = {}
    for key in keys:
        values = [meter.get(key) for meter in meters]
        total[key] = sum(values) if all(isinstance(v, int) for v in values) else None
    walls = [outcome['wall_seconds'] for outcome in outcomes]
    total['native_wall_seconds'] = sum(walls) if all(isinstance(v, (float, int)) for v in walls) else None
    return total


def build_plan(corpus, row, freeze_sha, prompt_sha, arm, args):
    return {'schema': 'wrd58-thin-plan-v1', 'case_id': row['id'], 'arm': arm,
            'attempt': args.attempt, 'source_ids': row['source_ids'], 'selection_sha256': freeze_sha,
            'corpus_binding': corpus['binding'], 'prompts_sha256': prompt_sha,
            'check_enabled': not args.skip_check, 'limits': LIMITS}


def run_slot(helper, native, corpus, row, freeze_sha, prompts, prompt_sha, arm, args):
    root = args.runs / row['id'] / arm
    attempt = root / f'attempt-{args.attempt:03d}'
    plan = build_plan(corpus, row, freeze_sha, prompt_sha, arm, args)
    with slot_lock(root):
        for dispatch in root.glob('attempt-*/stages/*/attempt-*/dispatch.json'):
            if not (dispatch.parent / 'producer_result.json').is_file():
                raise RuntimeError('Unfinished native dispatch already exists: ' + str(dispatch.parent))
        plan_path = attempt / 'plan.json'
        if not plan_path.exists():
            attempt.mkdir(exist_ok=False)
            helper.save_new(plan_path, plan)
        if helper.load(plan_path) != plan:
            raise ValueError('Attempt is already bound to a different plan')
        stage, prepared = prepare_stage(helper, corpus, row, attempt, plan, 'route', prompts['route'], {})
        if args.action == 'prepare':
            return {'status': 'PREPARED', 'attempt': str(attempt), 'stage': prepared}
        prior = {}
        outcomes = []
        selected = None
        phases = PHASES[:2] if args.skip_check else PHASES
        for phase in phases:
            if phase != 'route':
                stage, _ = prepare_stage(helper, corpus, row, attempt, plan, phase, prompts[phase], prior)
            outcome = run_stage(helper, native, stage, phase, plan, args)
            outcomes.append(outcome)
            status = outcome['status']
            if phase == 'route' and status == 'MAKE':
                prior['route'] = (stage / 'workspace', outcome['decision_sha256'])
            elif (phase == 'make' and status in ('CANDIDATE_PRESENT', 'UNDECLARED_SKILL_ARTIFACT')
                  and not args.skip_check):
                prior['make'] = (stage / 'workspace', outcome['skill_files'], outcome['outputs'],
                                 outcome['native_events'])
            else:
                if status == 'CANDIDATE_PRESENT':
                    selected = phase
                break
        final = {'schema': 'wrd58-thin-terminal-v1', 'plan': plan, 'status': status,
                 'phase': phase, 'selected_phase': selected,
                 'selected_package_root': outcome['package_root'] if selected else None,
                 'qualified_package': None,
                 'cost': sum_meter(outcomes), 'stages': outcomes}
        path = attempt / 'receipt.json'
        if path.exists():
            if helper.load(path) != final:
                raise ValueError('Preserved thin pipeline receipt changed')
        else:
            helper.save_new(path, final)
        return final


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('verify', 'prepare', 'run', 'pair'))
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--delivery', type=Path)
    parser.add_argument('--prompts', type=Path, default=HERE / 'thin_prompts58.json')
    parser.add_argument('--runs', type=Path)
    parser.add_argument('--case')
    parser.add_argument('--arm')
    parser.add_argument('--size', choices=('14b',), default='14b')
    parser.add_argument('--attempt', type=int, default=1)
    parser.add_argument('--startup-log', type=Path)
    parser.add_argument('--glm-credentials', type=Path)
    parser.add_argument('--include-glm', action='store_true')
    parser.add_argument('--skip-check', action='store_true')
    args = parser.parse_args(argv)
    try:
        helper = autonomous.engine()
        helper.check_runtime()
        rows, freeze_sha = autonomous.frozen_cases(helper, args.selection, args.case)
        corpus = autonomous.load_corpus(helper, args.corpus, args.delivery)
        prompts, prompt_sha = prompt_set(helper, args.prompts)
        if args.action == 'verify':
            for row in rows:
                autonomous.source_tree(helper, corpus, row)
            prepared = None
            if args.runs is not None:
                if args.case is None or args.arm not in (*SPARK_ARMS, GLM) or args.attempt < 1:
                    parser.error('verify --runs requires one --case, a pinned --arm and positive --attempt')
                attempt = args.runs.resolve() / args.case / args.arm / f'attempt-{args.attempt:03d}'
                row = rows[0]
                plan = build_plan(corpus, row, freeze_sha, prompt_sha, args.arm, args)
                if helper.load(attempt / 'plan.json') != plan:
                    raise ValueError('Prepared plan differs')
                copies, generated, mounts = stage_inputs(helper, corpus, row, 'route', {})
                stage = stage_path(attempt, 'route')
                if (stage / 'dispatch.json').exists():
                    raise ValueError('verify --runs is for undispatched preparation')
                prepared = verify_stage(helper, stage, plan, 'route', prompts['route'], copies, generated, mounts)
            print(json.dumps({'status': 'VERIFIED', 'selection_sha256': freeze_sha,
                              'prompts_sha256': prompt_sha, 'cases': [row['id'] for row in rows],
                              'prepared': prepared, 'limits': LIMITS, 'model_calls': 0}, ensure_ascii=False))
            return 0
        if args.runs is None or args.attempt < 1:
            parser.error('--runs and a positive --attempt are required')
        args.runs = args.runs.resolve()
        if args.runs.is_relative_to(args.corpus.resolve()):
            raise ValueError('Run workspaces must be outside the restored corpus')
        if args.glm_credentials is not None and args.glm_credentials.resolve().is_relative_to(args.runs):
            raise ValueError('GLM credentials must be outside the packaged runs tree')
        if args.action != 'pair' and (args.case is None or args.arm not in (*SPARK_ARMS, GLM)):
            parser.error('prepare/run requires one --case and one pinned --arm')
        if args.action == 'pair' and args.arm is not None:
            parser.error('pair uses --size and optional --include-glm')
        if args.action in ('run', 'pair'):
            if (args.action == 'pair' or args.arm != GLM) and args.startup_log is None:
                parser.error('--startup-log is required for Spark dispatch')
            if (args.include_glm or args.arm == GLM) and args.glm_credentials is None:
                parser.error('--glm-credentials is required for GLM dispatch')
            import thin_native58 as native
        else:
            native = None
        summaries = []
        for row in rows:
            if args.action == 'pair':
                steps = (0, 241) if row['frozen_position'] % 2 == 0 else (241, 0)
                arms = [f'wrd58-{args.size}-{step}' for step in steps]
                if args.include_glm:
                    arms.append(GLM)
            else:
                arms = [args.arm]
            for arm in arms:
                try:
                    result = run_slot(helper, native, corpus, row, freeze_sha, prompts, prompt_sha, arm, args)
                except ERRORS as error:
                    result = {'case_id': row['id'], 'arm': arm, 'status': 'DISPATCH_ERROR',
                              'error_type': type(error).__name__, 'error': str(error)}
                    if args.action in ('run', 'pair'):
                        root = args.runs / row['id'] / arm
                        root.mkdir(parents=True, exist_ok=True)
                        helper.save_new(root / f'launcher-error-{time.time_ns()}.json', result)
                summaries.append(result)
        print(json.dumps(summaries[0] if args.action != 'pair' else {'results': summaries}, ensure_ascii=False))
        return int(any(result['status'] in ('DISPATCH_ERROR', 'NATIVE_NONZERO_EXIT',
                                            'NATIVE_TRANSPORT_INCOMPLETE', 'NATIVE_BUDGET_BREACHED')
                       for result in summaries))
    except ERRORS as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
