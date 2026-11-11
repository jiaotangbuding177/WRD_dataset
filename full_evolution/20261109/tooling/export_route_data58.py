"""Project historical WRD route cards and verifiable native trial inputs."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3


ROUTE_KEYS = ('id', 'name', 'category', 'source_ids', 'steps', 'conditions', 'library_status')
SECRET = re.compile(rb'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|(?:sk-proj-|sk-ant-api\d\d-)[A-Za-z0-9_-]{24,}')


class Ineligible(ValueError):
    pass


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def source_requests(value):
    if 'requests' in value:
        return [row.get('text') for row in value['requests']
                if isinstance(row, dict) and set(row) <= {'id', 'text'}]
    if 'messages' in value:
        if any(not isinstance(row, dict) or row.get('role') != 'user' for row in value['messages']):
            return []
        return [row.get('content') for row in value['messages']]
    return []


def text_projection_ok(path, sid, case, corpus):
    try:
        value = read_json(path)
    except (ValueError, UnicodeError):
        return False
    if not isinstance(value, dict) or value.get('source_id') != sid:
        return False
    if set(value) not in ({'source_id', 'requests'}, {'source_id', 'messages'}):
        return False
    requests = source_requests(value)
    source = read_json(corpus / case['source']['path'])
    messages = source if isinstance(source, list) else source.get('messages', [])
    original = {row.get('content') for row in messages if row.get('role') == 'user'
                and isinstance(row.get('content'), str)}
    count = len(value.get('requests', value.get('messages', [])))
    return len(requests) == count and bool(requests) and all(
        isinstance(request, str) and request in original for request in requests
    )


def safe_mount(value):
    if not isinstance(value, str):
        raise Ineligible('invalid_mount')
    path = PurePosixPath(value)
    if (not value.startswith('inputs/') or path.as_posix() != value or '\\' in value
            or any(part in {'.', '..'} or ':' in part for part in path.parts)):
        raise Ineligible('invalid_mount')
    return path.as_posix()


def original_request(episode, case, arm):
    if not episode:
        raise Ineligible('historical_native_request_missing')
    root = Path(episode)
    request_path = root / 'request.json'
    if not request_path.is_file():
        raise Ineligible('historical_native_request_missing')
    request = read_json(request_path)
    if (request.get('protocol') != 'native-openclaw-only-v1' or request.get('input') != case['prompt']
            or request.get('followup_inputs')
            or (arm == 'no_skill' and (request.get('context') or request.get('learned_skills')))):
        raise Ineligible('historical_native_request_mismatch')
    resources = {}
    for item in request.get('resources', []):
        mount = safe_mount(item.get('mount'))
        physical = root / 'workspace' / mount
        if mount in resources or not physical.is_file() or physical.is_symlink():
            raise Ineligible('workspace_resource_missing_or_duplicate')
        physical.resolve().relative_to((root / 'workspace').resolve())
        resources[mount] = (physical, sha256(physical))
    case_mounts = {safe_mount(item.get('mount')) for item in case.get('fixtures', [])}
    if case_mounts != set(resources):
        raise Ineligible('historical_request_resource_set_mismatch')
    return resources, sha256(request_path)


def candidate(row, pair, route, cases, corpus, blocked_components, eval_resource_shas):
    case = row['case']
    if not isinstance(case, dict) or case.get('id') != row['case_id']:
        raise Ineligible('missing_original_case_payload')
    sid = case.get('source_id')
    source = cases.get(sid)
    if not source:
        raise Ineligible('outside_frozen_corpus')
    eligibility = source.get('student_eligibility', {})
    if (source['original_split'] != 'evolution' or source['component_id'] in blocked_components
            or eligibility.get('effect_evaluation_allowed')
            or 'EVAL' in str(eligibility.get('effect_split')).upper()):
        raise Ineligible('reserved_evaluation_lineage')
    learning_ids = set(route['source_ids']) | set(route.get('learning_source_ids') or [])
    learning_cases = [cases[key] for key in learning_ids]
    if sid in learning_ids or source['component_id'] in {c['component_id'] for c in learning_cases}:
        raise Ineligible('same_lineage_as_route_source')
    prompt = case.get('prompt')
    if not isinstance(prompt, str) or not prompt.strip() or SECRET.search(prompt.encode('utf-8')):
        raise Ineligible('invalid_trial_prompt')
    resources, request_sha = original_request(row['episode'], case, 'no_skill')
    if not pair or not pair['episode']:
        raise Ineligible('historical_paired_request_missing')
    paired, pair_sha = original_request(pair['episode'], case, 'workflow')
    if {k: v[1] for k, v in resources.items()} != {k: v[1] for k, v in paired.items()}:
        raise Ineligible('historical_paired_fixture_mismatch')
    maker_sha = {item['sha256'] for c in learning_cases for item in c.get('resources', [])}
    source_sha = {item['sha256'] for item in source.get('resources', [])}
    fixtures = []
    bundled = {}
    for mount, (file, digest) in sorted(resources.items()):
        if digest in maker_sha or digest in eval_resource_shas:
            raise Ineligible('trial_fixture_has_maker_or_eval_overlap')
        if any(part.lower() == 'skill.md' or part.lower() in {'answers', 'gold', 'outputs'}
               for part in PurePosixPath(mount).parts):
            raise Ineligible('non_input_fixture')
        path = f'objects/{digest}'
        if digest in source_sha and (corpus / path).is_file() and sha256(corpus / path) == digest:
            root = 'corpus'
        elif file.suffix.lower() == '.json' and text_projection_ok(file, sid, source, corpus):
            if SECRET.search(file.read_bytes()):
                raise Ineligible('strong_secret_signature')
            root = 'bundle'
            bundled[digest] = file
        else:
            raise Ineligible('fixture_not_from_source_or_verified_user_projection')
        fixtures.append({'mount': mount, 'sha256': digest, 'path': path, 'root': root})
    # Keep provenance separate from the model's task and artifact inputs.
    trial_id = f"{route['id']}--{case['id']}"
    trial = {'id': trial_id, 'route_id': route['id'], 'source_id': sid,
             'prompt': prompt, 'fixtures': fixtures}
    provenance = {'id': trial_id, 'historical_case_id': case['id'],
                  'case_sha256': source['_case_sha256'], 'source_component': source['component_id'],
                  'no_skill_request_sha256': request_sha, 'workflow_request_sha256': pair_sha}
    return trial, bundled, provenance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--decisions', type=Path, required=True)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    state = args.state.resolve()
    corpus = args.corpus.resolve()
    out = args.out.resolve()
    if out.exists():
        parser.error('--out must be a new directory')
    cases = {}
    for path in sorted((corpus / 'cases').glob('*/case.json')):
        case = read_json(path)
        sid = case['source_id']
        if sid in cases or path.parent.name != sid:
            raise ValueError('Duplicate or misplaced corpus case')
        cases[sid] = {**case, '_case_sha256': sha256(path)}
    with sqlite3.connect(state.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        sources = dict(db.execute('select id,processed from sources'))
        full_routes = {route_id: json.loads(payload)
                       for route_id, payload in db.execute('select id,payload from routes order by id')}
        db.row_factory = sqlite3.Row
        actor_jobs = [dict(row) for row in db.execute(
            "select route_id,case_id,arm,payload,episode from jobs where kind='actor' order by route_id,case_id,arm"
        )]
    decisions = read_json(args.decisions)
    if (len(sources) != 1107 or set(sources) != set(cases) or not all(sources.values())
            or len(full_routes) != 121 or len(decisions) != 1107
            or {row['source_id'] for row in decisions} != set(sources)):
        raise ValueError('Historical route/coverage does not match the frozen 1107 source corpus')
    routes = [{key: row[key] for key in ROUTE_KEYS} for row in full_routes.values()]
    if any(SECRET.search(json.dumps(r, ensure_ascii=False).encode('utf-8')) for r in routes):
        raise ValueError('Strong secret signature in historical route card')
    covered = {sid for route in routes for sid in route['source_ids']}
    if covered - set(cases):
        raise ValueError('Historical route references unknown corpus sources')
    eval_cases = [c for c in cases.values() if c['original_split'] != 'evolution'
                  or c.get('student_eligibility', {}).get('effect_evaluation_allowed')
                  or 'EVAL' in str(c.get('student_eligibility', {}).get('effect_split')).upper()]
    eval_components = {c['component_id'] for c in eval_cases}
    eval_resource_shas = {r['sha256'] for c in eval_cases for r in c.get('resources', [])}
    job_pairs = {}
    for row in actor_jobs:
        row['case'] = json.loads(row.pop('payload')).get('case')
        job_pairs[(row['route_id'], row['case_id'], row['arm'])] = row
    eligible = defaultdict(list)
    excluded = Counter()
    for row in actor_jobs:
        if row['arm'] != 'no_skill':
            continue
        route = full_routes[row['route_id']]
        if route['library_status'] == 'rejected':
            excluded['historical_route_rejected'] += 1
            continue
        pair = job_pairs.get((row['route_id'], row['case_id'], 'workflow'))
        try:
            item = candidate(row, pair, route, cases, corpus, eval_components, eval_resource_shas)
        except Ineligible as exc:
            excluded[str(exc)] += 1
        else:
            eligible[row['route_id']].append(item)
    trials, provenance, bundle = [], [], {}
    used_sources = set()
    for route_id, options in sorted(eligible.items(), key=lambda item: (len(item[1]), item[0])):
        trial, files, audit = min(options, key=lambda option: (
            option[0]['source_id'] in used_sources, option[0]['source_id'], option[0]['id']
        ))
        trials.append(trial)
        bundle.update(files)
        provenance.append(audit)
        used_sources.add(trial['source_id'])
    trials.sort(key=lambda trial: trial['route_id'])
    provenance.sort(key=lambda row: row['id'])
    out.mkdir(parents=True)
    if bundle:
        (out / 'objects').mkdir()
    for digest, path in sorted(bundle.items()):
        target = out / 'objects' / digest
        shutil.copyfile(path, target)
        if sha256(target) != digest:
            raise ValueError('Trial projection changed during export')
    write_json(out / 'ROUTES.json', {'schema': 'wrd58-reused-routes-v1', 'source_count': len(sources),
                                    'routes': routes})
    write_json(out / 'SOURCE_DECISIONS.json', {
        'schema': 'wrd58-historical-source-decisions-v1', 'source_count': len(sources),
        'decisions': [{k: r.get(k) for k in ('source_id', 'action', 'route_id')} for r in decisions],
        'role': 'Historical coverage audit. Do not mount with trial inputs.',
    })
    write_json(out / 'TRIALS.json', {'schema': 'wrd58-reused-trials-v1', 'trials': trials})
    receipt = {
        'schema': 'wrd58-historical-route-trial-export-v1', 'state_sha256': sha256(state),
        'decisions_source_sha256': sha256(args.decisions),
        'corpus_manifest_sha256': sha256(corpus / 'MANIFEST.json'), 'processed_sources': len(sources),
        'historical_routes': len(routes), 'route_states': dict(Counter(r['library_status'] for r in routes)),
        'route_linked_sources': len(covered), 'source_ledger_only': len(sources) - len(covered),
        'historical_source_actions': dict(Counter(r['action'] for r in decisions)),
        'historical_trial_pairs': sum(row['arm'] == 'no_skill' for row in actor_jobs),
        'eligible_trial_pairs': sum(map(len, eligible.values())), 'selected_trials': len(trials),
        'selected_unique_trial_sources': len(used_sources), 'excluded_trial_pairs': dict(excluded),
        'trial_sources_in_other_route_scopes': len(used_sources & covered),
        'fixture_bindings': dict(Counter(f['root'] for trial in trials for f in trial['fixtures'])),
        'bundle_objects': len(bundle), 'bundle_bytes': sum(p.stat().st_size for p in bundle.values()),
        'excluded_evaluation_sources': len(eval_cases), 'excluded_evaluation_components': len(eval_components),
        'selected_trial_provenance': provenance,
        'outputs_sha256': {name: sha256(out / name)
                           for name in ('ROUTES.json', 'TRIALS.json', 'SOURCE_DECISIONS.json')},
        'qualification': 'Input projection only. No historical output, answer, skill, review, or score is included.',
    }
    write_json(out / 'EXPORT_RECEIPT.json', receipt)
    print(json.dumps({key: value for key, value in receipt.items() if key != 'selected_trial_provenance'},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
