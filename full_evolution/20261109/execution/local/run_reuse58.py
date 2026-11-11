#!/usr/bin/env python3
"""Reuse frozen historical routes and run new native WRD production stages."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from tempfile import TemporaryDirectory

import run_thin58 as thin
import thin_native58 as native


HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / 'route_data'
ARM = 'wrd58-14b-241'
STATUSES = {'retained', 'candidate', 'needs_revision', 'rejected'}
PHASE_LIMITS = {
    **{phase: thin.LIMITS[phase] for phase in ('make', 'check')},
    'trial_no_skill': {'max_requests': 32, 'max_reply_tokens': 32768,
                       'max_completion_tokens': 65536, 'wall_seconds': 1800},
    'trial_with_skill': {'max_requests': 32, 'max_reply_tokens': 32768,
                         'max_completion_tokens': 65536, 'wall_seconds': 1800},
    'review': {'max_requests': 16, 'max_reply_tokens': 16384,
               'max_completion_tokens': 32768, 'wall_seconds': 1800},
}


def pin_json(value):
    return hashlib.sha256((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()).hexdigest()


def load_catalog(helper, args, corpus):
    route_data = helper.load(args.routes)
    trial_data = helper.load(args.trials)
    if (route_data['schema'] != 'wrd58-reused-routes-v1'
            or trial_data['schema'] != 'wrd58-reused-trials-v1'
            or route_data['source_count'] != 1107 or len(corpus['registry']) != 1107):
        raise ValueError('Expected the full historical WRD58 material and route catalog')
    routes, trials = {}, {}
    for route in route_data['routes']:
        key = route['id']
        sources = route['source_ids']
        if (not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', key) or key in routes
                or route['library_status'] not in STATUSES or not sources
                or len(sources) != len(set(sources)) or not set(sources) <= set(corpus['registry'])):
            raise ValueError('Invalid or unresolvable historical route: ' + key)
        routes[key] = route
    if len(routes) != 121:
        raise ValueError('Expected all 121 historical route decisions')
    for trial in trial_data['trials']:
        key, source_id = trial['route_id'], trial['source_id']
        route = routes[key]
        if key in trials or not isinstance(trial['prompt'], str) or not trial['prompt'].strip():
            raise ValueError('Expected at most one valid frozen trial per route')
        if source_id in route['source_ids'] or source_id not in corpus['registry']:
            raise ValueError('Trial must have a separate historical source: ' + key)
        source = corpus['registry'][source_id]
        maker = [corpus['registry'][item] for item in route['source_ids']]
        if source['original_split'] != 'evolution' or source['component_id'] in {x['component_id'] for x in maker}:
            raise ValueError('Trial is held out or shares the original source component: ' + key)
        maker_objects = {r['sha256'] for row in maker for r in row['resources']}
        mounts = set()
        for fixture in trial['fixtures']:
            mount = helper.safe_relative(fixture['mount']).as_posix()
            path = helper.safe_relative(fixture['path']).as_posix()
            if (not mount.startswith(('inputs/', 'reference_inputs/')) or mount.casefold() in mounts
                    or fixture['sha256'] in maker_objects or not re.fullmatch('[0-9a-f]{64}', fixture['sha256'])):
                raise ValueError('Invalid, duplicate or overlapping trial fixture: ' + key)
            source_root = {'corpus': corpus['root'], 'bundle': args.bundle}[fixture['root']]
            file = source_root / path
            if (file.is_symlink() or not file.resolve().is_relative_to(source_root) or not file.is_file()
                    or helper.digest(file) != fixture['sha256']):
                raise ValueError('Trial fixture absent or differs: ' + key)
            mounts.add(mount.casefold())
        trials[key] = trial
    return routes, trials


def route_sources(corpus, route):
    sources = []
    for source_id in route['source_ids']:
        case = corpus['registry'][source_id]
        sources.append({'source_id': source_id,
                        'case_sha256': corpus['pins'][f'cases/{source_id}/case.json'],
                        'source_sha256': case['source']['sha256'],
                        'resource_index_sha256': case['delivery_index']['sha256'],
                        'resource_sha256': [item['sha256'] for item in case['resources']],
                        'component_id': case['component_id'],
                        'identity_component57': case['student_eligibility'].get('student_identity_component57')})
    return {'id': route['id'], 'source_ids': route['source_ids'], 'sources': sources}


def write_once(helper, path, value):
    if path.exists():
        if helper.load(path) != value:
            raise ValueError('Frozen record changed: ' + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        helper.save_new(path, value)


def phase_limits(phase):
    return PHASE_LIMITS[phase.removeprefix('v2_')]


def production_prompt(phase, prompt):
    limits = phase_limits(phase)
    return (prompt + f'\n\n本阶段最多 {limits["max_requests"]} 次模型请求，'
            f'{limits["wall_seconds"]} 秒。按实际产物与试跑证据收尾。')


def prepare_stage(helper, stage, plan, phase, prompt, copies, generated=None, skill_root=None, mounts=None):
    workspace = stage / 'workspace'
    generated = generated or {}
    mount_names = list(mounts) if mounts is not None else sorted({*copies, *generated})
    if set(copies) & set(generated) or not set(mount_names) <= {*copies, *generated}:
        raise ValueError('Duplicate or undeclared stage input')
    for name in (*copies, *generated):
        if helper.safe_relative(name).parts[0] not in ('inputs', 'reference_inputs'):
            raise ValueError('Unexpected stage input directory')
    if skill_root is not None and not phase.endswith('trial_with_skill'):
        raise ValueError('Learned skill may only be mounted in its trial arm')
    skill_files = thin.artifact_files(helper, skill_root) if skill_root is not None else {}
    if skill_root is not None and ('SKILL.md' not in skill_files or not (skill_root / 'SKILL.md').stat().st_size):
        raise ValueError('Expected a nonempty frozen skill home page')
    skill_relative = 'learned_skills/' + plan['route_id']
    skills = [{'id': plan['route_id'], 'path': str(workspace / skill_relative), 'files': skill_files}] if skill_files else []
    request = {'protocol': 'native-openclaw-only-v1', 'stage': 'wrd58_reuse_' + phase,
               'task_id': plan['route_id'] + '-' + phase, 'input': prompt, 'context': [],
               'followup_inputs': [], 'learned_skills': skills,
               'resources': [{'path': str(workspace / path), 'mount': path} for path in mount_names]}
    files = {path: sha for path, (_, sha) in copies.items()}
    files.update((path, pin_json(value)) for path, value in generated.items())
    files.update((skill_relative + '/' + path, sha) for path, sha in skill_files.items())
    if not stage.exists():
        stage.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix='.preparing-', dir=stage.parent) as temp:
            scratch = Path(temp) / 'attempt'
            folder = scratch / 'workspace'
            folder.mkdir(parents=True)
            for mount, (path, sha) in copies.items():
                dest = folder / mount
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
                if helper.digest(dest) != sha:
                    raise ValueError('Prepared file SHA differs: ' + mount)
            for mount, value in generated.items():
                (folder / mount).parent.mkdir(parents=True, exist_ok=True)
                helper.save_new(folder / mount, value)
            if skill_files:
                shutil.copytree(skill_root, folder / skill_relative)
            (folder / 'README.md').write_text('# WRD native task workspace\n', encoding='utf-8')
            (folder / '.gitignore').write_text('.openclaw/\n__pycache__/\n', encoding='utf-8')
            helper.run_git(folder, 'init', '--quiet', '--template=')
            helper.run_git(folder, 'config', 'user.name', 'WRD corpus preparation')
            helper.run_git(folder, 'config', 'user.email', 'wrd-local@invalid')
            helper.run_git(folder, 'add', '--', 'README.md', '.gitignore')
            helper.run_git(folder, 'commit', '--quiet', '-m', 'Initialize native WRD task')
            helper.save_new(scratch / 'request.json', request)
            snapshot = thin.autonomous.file_hashes(helper, folder)
            if any(snapshot.get(path) != sha for path, sha in files.items()):
                raise ValueError('Native stage input does not match its pins')
            helper.save_new(scratch / 'stage_receipt.json', {
                'schema': 'wrd58-route-reuse-stage-v1', 'plan': plan, 'phase': phase,
                'budget': phase_limits(phase), 'files': snapshot,
                'git_commit': helper.run_git(folder, 'rev-parse', 'HEAD'),
                'request_sha256': helper.digest(scratch / 'request.json'), 'model_calls': 0,
            })
            scratch.rename(stage)
    receipt = helper.load(stage / 'stage_receipt.json')
    if (receipt['plan'] != plan or receipt['phase'] != phase or receipt['budget'] != phase_limits(phase)
            or receipt['request_sha256'] != helper.digest(stage / 'request.json')
            or helper.load(stage / 'request.json') != request
            or any(receipt['files'].get(path) != sha for path, sha in files.items())):
        raise ValueError('Prepared stage binding changed: ' + phase)
    if not (stage / 'dispatch.json').exists():
        if (thin.autonomous.file_hashes(helper, workspace) != receipt['files']
                or helper.run_git(workspace, 'rev-parse', 'HEAD') != receipt['git_commit']):
            raise ValueError('Prepared workspace changed before dispatch: ' + phase)
        helper.native_workspace_binding_proof(stage)
    return receipt


def preserve_qualified(helper, skill, slot, attempt, trial_result):
    package = slot / 'qualified' / attempt.name
    manifest = thin.artifact_files(helper, skill)
    if not package.exists():
        package.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix='.qualified-', dir=package.parent) as temp:
            pending = Path(temp) / 'package'
            shutil.copytree(skill, pending / 'skill')
            if thin.artifact_files(helper, pending / 'skill') != manifest:
                raise ValueError('Qualified skill changed while being copied')
            helper.save_new(pending / 'receipt.json', {'files': manifest, 'trial': trial_result})
            pending.rename(package)
    if (thin.artifact_files(helper, package / 'skill') != manifest
            or helper.load(package / 'receipt.json') != {'files': manifest, 'trial': trial_result}):
        raise ValueError('Previously delivered qualified skill changed')
    return str(package / 'skill')


def run_route(helper, corpus, route, trial, prompts, args):
    route_id = route['id']
    slot = args.runs / route_id / args.arm
    attempt = slot / f'attempt-{args.attempt:03d}'
    plan = {'schema': 'wrd58-route-reuse-plan-v1', 'route_id': route_id, 'arm': args.arm,
            'historical_status': route['library_status'], 'source_ids': route['source_ids'],
            'route_catalog_sha256': helper.digest(args.routes), 'trial_catalog_sha256': helper.digest(args.trials),
            'corpus_binding': corpus['binding'], 'trial_id': trial['id'] if trial else None,
            'prompts_sha256': pin_json(prompts), 'limits': PHASE_LIMITS}
    row = route_sources(corpus, route)
    route_artifact = {'status': 'MAKE', 'reason': 'Reuse the frozen historical grouping and scope',
                      'route': {key: route[key] for key in ('id', 'name', 'category', 'source_ids', 'steps', 'conditions')}}
    with thin.slot_lock(slot):
        for dispatch in slot.glob('attempt-*/stages/*/attempt-*/dispatch.json'):
            if not (dispatch.parent / 'producer_result.json').is_file():
                raise RuntimeError('Unresolved native dispatch: ' + str(dispatch.parent))
        attempt.mkdir(exist_ok=True)
        write_once(helper, attempt / 'plan.json', plan)
        frozen = attempt / 'frozen_route'
        write_once(helper, frozen / thin.ROUTE_FILE, route_artifact)
        prior = {'route': (frozen, helper.digest(frozen / thin.ROUTE_FILE))}
        provider = None
        calls = {}

        def execute(phase, prompt, copies, generated=None, skill_root=None, mounts=None):
            nonlocal provider
            stage = thin.stage_path(attempt, phase)
            prepare_stage(helper, stage, plan, phase, prompt, copies, generated, skill_root, mounts)
            terminal = stage / 'producer_result.json'
            dispatch = stage / 'dispatch.json'
            if not terminal.exists():
                if dispatch.exists():
                    raise RuntimeError('Unresolved native dispatch: ' + str(stage))
                if provider is None:
                    provider = native.build_provider(helper, args.arm, args.startup_log, args.glm_credentials)
                native.run_native_attempt(helper, stage, provider, phase_limits(phase))
            result = helper.load(terminal)
            if result.get('arm') != args.arm or result.get('budget_limits') != phase_limits(phase):
                raise ValueError('Native terminal is for a different arm or budget')
            if dispatch.exists() and helper.load(dispatch).get('request_sha256') != helper.digest(stage / 'request.json'):
                raise ValueError('Native terminal refers to a different request')
            calls[phase] = {'stage': stage.relative_to(attempt).as_posix(),
                            'producer_result_sha256': helper.digest(terminal),
                            'budget': result.get('budget'), 'wall_seconds': result.get('wall_seconds')}
            return stage, result

        def production(phase, prompt, inputs):
            copies, generated, mounts = thin.stage_inputs(helper, corpus, row, phase, inputs)
            return execute(phase, prompt, copies, generated, mounts=mounts)

        make_prompt = production_prompt('make',
            '本轮采用已经归并的历史路线卡，直接按其工作范围制作。每个来源的完整会话、纠正和可用材料'
            '见 inputs/index.json。交付技能的名称用路线 ID。请在约定位置写下实际技能与试跑记录。\n\n'
            + prompts['make'])
        if args.action == 'prepare':
            copies, generated, mounts = thin.stage_inputs(helper, corpus, row, 'make', prior)
            stage = thin.stage_path(attempt, 'make')
            receipt = prepare_stage(helper, stage, plan, 'make', make_prompt, copies, generated, mounts=mounts)
            return {'route': route_id, 'status': 'PREPARED', 'files': len(receipt['files']),
                    'trial_available': trial is not None, 'model_calls': 0}

        import reuse_checks58
        import reuse_trials58

        def finish(status, **details):
            receipt = {'schema': 'wrd58-route-reuse-terminal-v1', 'plan': plan, 'status': status,
                       'stages': calls, 'cost': thin.sum_meter(list(calls.values())), **details}
            write_once(helper, attempt / 'receipt.json', receipt)
            return {'route': route_id, 'status': status, 'receipt': str(attempt / 'receipt.json')}

        stage, result = production('make', make_prompt, prior)
        make = thin.stage_output(helper, stage, result, 'make', row['source_ids'])
        write_once(helper, stage / 'outcome.json', make)
        skill_md = stage / 'workspace' / thin.SKILL_ROOT / 'SKILL.md'
        if (make['status'] in ('STOP', 'BLOCKED') or make['changed_inputs']
                or 'SKILL.md' not in make['skill_files'] or not skill_md.stat().st_size):
            return finish(make['status'], make=make)
        prior['make'] = (stage / 'workspace', make['skill_files'], make['outputs'], make['native_events'])

        check_prompt = (prompts['check'] + '\n\n用原生 exec 前台运行实际公开入口，将选定技能的资源文件作为命令参数。'
                        '功能结果或实际命令输出保存到 outputs/evidence/，tests 每条填写 command、input、result、evidence_path，'
                        '其中 command 逐字引用实际运行的整条命令，evidence_path 指向实际存在的功能证据文件。'
                        '修改后的包必须以触发错误的输入复验。')
        stage, result = production('check', production_prompt('check', check_prompt), prior)
        check = thin.stage_output(helper, stage, result, 'check', row['source_ids'])
        write_once(helper, stage / 'outcome.json', check)
        evidence = reuse_checks58.check_evidence(helper, stage, check)
        write_once(helper, stage / 'functional_evidence.json', evidence)
        workflow_trial = (check['status'] == 'CANDIDATE_PRESENT' and trial is not None
                          and set(check['skill_files']) == {'SKILL.md'})
        if evidence['status'] != 'CHECK_VERIFIED' and not workflow_trial:
            return finish(evidence['status'], make=make, check=check, functional_evidence=evidence)
        skill = stage / 'workspace' / check['package_root']
        if trial is None:
            return finish('FUNCTION_CHECKED_NO_TRIAL', make=make, check=check, functional_evidence=evidence)
        trial_result = reuse_trials58.run_trials(helper, route, trial, corpus['root'], args.bundle, skill, execute)
        details = {'make': make, 'check': check, 'functional_evidence': evidence, 'trial': trial_result}
        if workflow_trial and evidence['status'] != 'CHECK_VERIFIED':
            details['workflow_trial_without_executable_resource'] = True
        if trial_result['status'] == 'REVISE' and trial_result.get('repair_inputs'):
            copies, generated, mounts = thin.stage_inputs(helper, corpus, row, 'check', prior)
            for path in [name for name in copies if name.startswith('inputs/candidate/')]:
                del copies[path]
            selected_files = thin.artifact_files(helper, skill)
            for path, sha in selected_files.items():
                copies['inputs/candidate/' + path] = (skill / path, sha)
            generated['inputs/candidate_manifest.json']['files'] = selected_files
            for name, pin in trial_result['repair_inputs'].items():
                path = Path(pin['path']).resolve(strict=True)
                if not path.is_relative_to(attempt) or name in copies or name in generated:
                    raise ValueError('Repair input must point to this attempt and a new mount')
                copies[name] = (path, pin['sha256'])
                mounts.append(name)
            stage, result = execute('v2_check', production_prompt('v2_check', check_prompt +
                '\n\n附带第一次业务试用的实物、调用与审核。先定位可复现缺陷，再将修改实际写进新包。'
                '修订后以相同的失败输入复验。'), copies, generated, mounts=mounts)
            repaired = thin.stage_output(helper, stage, result, 'check', row['source_ids'])
            write_once(helper, stage / 'outcome.json', repaired)
            repaired_evidence = reuse_checks58.check_evidence(helper, stage, repaired)
            write_once(helper, stage / 'functional_evidence.json', repaired_evidence)
            details.update(repaired=repaired, repaired_evidence=repaired_evidence)
            if repaired_evidence['status'] != 'CHECK_VERIFIED':
                return finish('BUSINESS_REPAIR_UNVERIFIED', **details)
            skill = stage / 'workspace' / repaired['package_root']

            def retest(phase, prompt, copies, generated=None, skill_root=None):
                selected_phase = phase if phase == 'trial_no_skill' else 'v2_' + phase
                return execute(selected_phase, prompt, copies, generated, skill_root)

            trial_result = reuse_trials58.run_trials(helper, route, trial, corpus['root'], args.bundle, skill, retest)
            details['retrial'] = trial_result
        if trial_result['status'] == 'RETAIN' and (evidence['status'] == 'CHECK_VERIFIED' or details.get('repaired_evidence')):
            details['qualified_skill'] = preserve_qualified(helper, skill, slot, attempt, trial_result)
        status = trial_result['status'] if 'qualified_skill' in details or trial_result['status'] != 'RETAIN' else 'PENDING'
        return finish(status, **details)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('verify', 'prepare', 'run'))
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--delivery', type=Path)
    parser.add_argument('--routes', type=Path, default=DATA / 'ROUTES.json')
    parser.add_argument('--trials', type=Path, default=DATA / 'TRIALS.json')
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--runs', type=Path)
    parser.add_argument('--route', action='append')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--arm', choices=(*thin.SPARK_ARMS, thin.GLM), default=ARM)
    parser.add_argument('--attempt', type=int, default=1)
    parser.add_argument('--startup-log', type=Path)
    parser.add_argument('--glm-credentials', type=Path)
    args = parser.parse_args(argv)
    args.bundle = (args.bundle or args.trials.parent).resolve(strict=True)
    if args.route and args.all:
        parser.error('Choose explicit --route entries or --all')
    if args.action != 'verify' and (not args.runs or not (args.route or args.all) or args.attempt < 1):
        parser.error('prepare/run require --runs, --route or --all, and a positive attempt')
    if args.action == 'run' and not (args.glm_credentials if args.arm == thin.GLM else args.startup_log):
        parser.error('run requires the actual Spark startup log or private GLM credentials')
    try:
        helper = thin.autonomous.engine()
        helper.check_runtime()
        corpus = thin.autonomous.load_corpus(helper, args.corpus, args.delivery)
        routes, trials = load_catalog(helper, args, corpus)
        selected = list(dict.fromkeys(args.route or [key for key, value in routes.items()
                                                    if value['library_status'] != 'rejected']))
        if any(routes[key]['library_status'] == 'rejected' for key in selected):
            raise ValueError('Historical rejection remains in the ledger and is not scheduled')
        if args.action == 'verify':
            for key in selected:
                thin.autonomous.source_tree(helper, corpus, route_sources(corpus, routes[key]))
            print(json.dumps({'status': 'VERIFIED', 'corpus_sources': len(corpus['registry']),
                              'historical_routes': len(routes), 'selected_routes': len(selected),
                              'trial_routes': sum(key in trials for key in selected), 'model_calls': 0}))
            return 0
        args.runs = args.runs.resolve()
        if any(args.runs.is_relative_to(root) for root in (corpus['root'], args.bundle)):
            raise ValueError('Run directories must be outside the frozen materials')
        if args.glm_credentials and args.glm_credentials.resolve().is_relative_to(args.runs):
            raise ValueError('Private credentials must remain outside the run archive')
        prompts, _ = thin.prompt_set(helper, Path(thin.__file__).with_name('thin_prompts58.json'))
        failed = False
        for key in selected:
            try:
                result = run_route(helper, corpus, routes[key], trials.get(key), prompts, args)
            except thin.ERRORS as exc:
                failed = True
                result = {'route': key, 'status': 'LOCAL_ERROR_OR_UNRESOLVED', 'error': str(exc)}
            print(json.dumps(result, ensure_ascii=False), flush=True)
        return int(failed)
    except thin.ERRORS as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
