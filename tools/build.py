"""Offline, read-only WRD record packaging; never executes agents or models."""
from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import threading

SCHEMA = 'wrd-training-bundle-v1'
IMAGE = 'sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
TEXT_EXT = {'.json', '.jsonl', '.md', '.txt', '.py', '.js', '.ts', '.html', '.css', '.csv', '.yaml', '.yml', '.toml', '.sh', '.ps1', '.log', '.xml', '.svg', '.ini'}
SECRET_KEY = re.compile(r'^(?:(?:admin|user|db|database|smtp|email|service|login|root|test)[-_]?)?(api[-_]?key|authorization|password|passwd|access[-_]?token|refresh[-_]?token|gateway[-_]?token|client[-_]?secret|private[-_]?key|secret[-_]?key)$', re.I)
SECRET_PATTERNS = [
    re.compile(r'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b'),
    re.compile(r'(?i)((?:Bearer|Basic)\s+)[A-Za-z0-9_.~+/=-]{8,}'),
    re.compile(r'(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|gateway[_-]?token|password|client[_-]?secret)[\"\x27]?\s*[:=]\s*[\"\x27])([^\"\x27\r\n]{1,})([\"\x27])'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
]


def dumps(v):
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'))


def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return default


def write_json(p, v):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def ids(v):
    return sorted(set(re.findall(r'conv_[a-f0-9]{12}', dumps(v))))


def clean_text(s):
    count = 0
    for i, pat in enumerate(SECRET_PATTERNS):
        def sub(m):
            if i == 1:
                if m.group(1).lower().startswith('basic'):
                    try:
                        value = m.group(0)[len(m.group(1)):]
                        if b':' not in base64.b64decode(value + '=' * (-len(value) % 4), validate=True):
                            return m.group(0)
                    except (ValueError, TypeError):
                        return m.group(0)
                return m.group(1) + '<REDACTED_CREDENTIAL>'
            if i == 2:
                # Environment references, documented placeholders, and Python expressions are not secrets.
                value = m.group(2)
                if any(x in value.lower() for x in ['redacted', 'os.environ', 'getenv', 'example', 'your_', 'your-', '${', '<', 'process.env']):
                    return m.group(0)
                return m.group(1) + '<REDACTED_CREDENTIAL>' + m.group(3)
            return '<REDACTED_CREDENTIAL>'
        s, n = pat.subn(sub, s)
        count += n
    # Shell/YAML-style assignments, including unquoted values, are not JSON keys.
    assignment = re.compile(r'(?im)^(\s*(?:export\s+)?(?:[A-Z0-9_]*(?:API_KEY|ACCESS_TOKEN|REFRESH_TOKEN|PASSWORD|CLIENT_SECRET)|api[-_]?key|password|authorization)\s*[:=]\s*)([^\s#\r\n]+)')
    def clean_assignment(m):
        if any(x in m.group(2).lower() for x in ['redacted', '${', '$env:', 'os.environ', 'getenv', 'your-', 'your_', '<']):
            return m.group(0)
        return m.group(1) + '<REDACTED_CREDENTIAL>'
    s, n = assignment.subn(clean_assignment, s)
    count += n
    return s, count


def clean_value(v):
    if isinstance(v, dict):
        return {k: '<REDACTED_CREDENTIAL>' if SECRET_KEY.match(str(k)) and a else clean_value(a) for k, a in v.items()}
    if isinstance(v, list):
        return [clean_value(a) for a in v]
    if isinstance(v, str):
        # Tool arguments/results may themselves be JSON strings. Clean their
        # structure before serializing, so native and OpenAI representations
        # receive identical, idempotent credential substitutions.
        if v.lstrip().startswith(('{', '[')):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, (dict, list)):
                    cleaned = clean_value(parsed)
                    return dumps(cleaned) if cleaned != parsed else v
            except ValueError:
                pass
        return clean_text(v)[0]
    return v


def sanitized_bytes(p, raw):
    if p.suffix.lower() not in TEXT_EXT and p.name not in {'SKILL.md', 'config', 'HEAD'}:
        return raw, False
    try:
        s = raw.decode('utf-8-sig')
    except UnicodeError:
        return raw, False
    if p.suffix.lower() == '.json':
        try:
            v = json.loads(s)
            cleaned = clean_value(v)
            if cleaned != v:
                return (dumps(cleaned) + '\n').encode('utf-8'), True
        except ValueError:
            pass
    if p.suffix.lower() == '.jsonl':
        lines = []
        changed = False
        for line in s.splitlines(keepends=True):
            try:
                v = json.loads(line)
                cleaned = clean_value(v)
                if cleaned != v:
                    line = dumps(cleaned) + '\n'
                    changed = True
            except ValueError:
                cleaned_line, _ = clean_text(line)
                changed |= cleaned_line != line
                line = cleaned_line
            lines.append(line)
        if changed:
            return ''.join(lines).encode('utf-8'), True
    t, _ = clean_text(s)
    if t != s:
        return t.encode('utf-8'), True
    return raw, False


class Archive:
    def __init__(self, root, resume=False):
        self.root = root
        (root / 'objects').mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=8)
        self.cache = {}
        self.seen_logical = set()
        self.objects = set()
        self.stats = Counter()
        self.errors = []
        index_path = root / 'file_index.jsonl'
        if resume and index_path.exists():
            with index_path.open('rb') as src:
                good_end = 0
                for line in src:
                    try:
                        e = json.loads(line)
                    except ValueError:
                        break
                    self.seen_logical.add(e['logical_path'])
                    self.objects.add(e['sha256'])
                    self.stats['logical_files'] += 1
                    self.stats['referenced_bytes'] += e['bytes']
                    self.stats['redacted_logical_files'] += int(e.get('credential_redacted', False))
                    good_end = src.tell()
            if good_end != index_path.stat().st_size:
                with index_path.open('r+b') as f:
                    f.seek(good_end)
                    (root / 'interrupted_index_tail.bin').write_bytes(f.read())
                    f.truncate(good_end)
        self.index = index_path.open('a' if resume else 'w', encoding='utf-8')

    def add(self, source, logical, scope, **extra):
        p = Path(source)
        logical = str(logical).replace('\\', '/')
        if logical in self.seen_logical:
            return
        self.seen_logical.add(logical)
        try:
            if p.is_symlink() or not p.is_file():
                raise OSError('missing file or symbolic link excluded')
            stat = p.stat()
            key = (str(p.absolute()).lower(), stat.st_size, stat.st_mtime_ns)
            if key not in self.cache:
                raw = p.read_bytes()
                source_sha = hashlib.sha256(raw).hexdigest()
                data, changed = sanitized_bytes(p, raw)
                sha = hashlib.sha256(data).hexdigest()
                obj = self.root / 'objects' / sha[:2] / sha
                with self.lock:
                    if not obj.exists():
                        obj.parent.mkdir(exist_ok=True)
                        obj.write_bytes(data)
                self.cache[key] = {'source_sha256': source_sha, 'sha256': sha, 'bytes': len(data), 'source_bytes': len(raw), 'credential_redacted': changed}
            entry = dict(self.cache[key])
            entry.update(logical_path=logical, source_path=str(p.absolute()), object='objects/' + entry['sha256'][:2] + '/' + entry['sha256'], scope=scope, **extra)
            with self.lock:
                self.index.write(dumps(entry) + '\n')
                self.objects.add(entry['sha256'])
                self.stats['logical_files'] += 1
                self.stats['referenced_bytes'] += entry['bytes']
                self.stats['redacted_logical_files'] += int(entry['credential_redacted'])
        except (OSError, ValueError) as e:
            self.errors.append({'source_path': str(p), 'logical_path': logical, 'reason': str(e)[:250], 'scope': scope})

    def tree(self, source, logical, scope):
        source = Path(source)
        if not source.exists():
            self.errors.append({'source_path': str(source), 'logical_path': logical, 'reason': 'directory missing', 'scope': scope})
            return
        def onerror(e):
            self.errors.append({'source_path': str(e.filename), 'reason': str(e), 'scope': scope})
        pending = []
        def submit(item):
            self.add(*item)
        for base, dirs, files in os.walk(source, followlinks=False, onerror=onerror):
            # Cached environments and credential stores are not task artifacts.
            dirs[:] = sorted(d for d in dirs if d not in {'node_modules', '__pycache__', '.venv', '.cache', '.claude', 'private', 'credentials'} and not (Path(base) / d).is_symlink())
            for n in sorted(files):
                p = Path(base) / n
                if n.lower() == '.env' or n.lower().startswith('.env.') or n in {'auth-profiles.json', 'model_credentials.json'}:
                    self.stats['excluded_credential_files'] += 1
                    continue
                pending.append((p, str(Path(logical) / p.relative_to(source)), scope))
                if len(pending) >= 256:
                    list(self.pool.map(submit, pending))
                    pending.clear()
        if pending:
            list(self.pool.map(submit, pending))

    def close(self):
        self.pool.shutdown(wait=True)
        self.index.close()
        self.stats['unique_objects'] = len(self.objects)
        self.stats['unique_bytes'] = sum(p.stat().st_size for d in (self.root / 'objects').iterdir() for p in d.iterdir())
        write_json(self.root / 'missing_or_excluded.json', self.errors)
        return dict(self.stats)


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        if self.p[a] != a:
            self.p[a] = self.find(self.p[a])
        return self.p[a]

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.p[max(a, b)] = min(a, b)


def load_state(root):
    uri = 'file:' + (root / 'output/workflow_library/state.db').as_posix() + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as cx:
        cx.row_factory = sqlite3.Row
        jobs = [dict(r) for r in cx.execute('select * from jobs order by id')]
        routes = [json.loads(r[0]) for r in cx.execute('select payload from routes order by id')]
        meta = {r[0]: read_json_string(r[1]) for r in cx.execute('select key,value from meta')}
        tables = {}
        for name in [r[0] for r in cx.execute("select name from sqlite_master where type='table'")]:
            if name not in {'jobs', 'routes', 'meta'}:
                tables[name] = [dict(r) for r in cx.execute('select * from "' + name.replace('"', '""') + '"')]
    for j in jobs:
        for k in ['payload', 'result']:
            j[k] = read_json_string(j.get(k))
    return jobs, routes, meta, tables


def read_json_string(s):
    try:
        return json.loads(s) if isinstance(s, str) else s
    except ValueError:
        return s


def write_jsonl(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as f:
        for r in rows:
            f.write(dumps(clean_value(r)) + '\n')


def discover_episodes(root, jobs, meta):
    out = {}
    def add(path, job, cohort='current_pipeline'):
        if not path:
            return
        p = Path(path)
        key = str(p.absolute()).lower()
        if key in out:
            out[key]['job_refs'] = sorted(set(out[key]['job_refs'] + [job['id']]))
            return
        eid = 'ep_' + hashlib.sha256(key.encode()).hexdigest()[:20]
        execution = read_json(p / 'execution.json', {})
        if not execution:
            execution = read_json(p / 'openclaw_transport/execution.json', {})
        native = execution.get('backend') == 'native' and execution.get('custom_agent_loop') is False and execution.get('image') == IMAGE
        original_result = read_json(p / 'result.json', {})
        status = original_result.get('status', job.get('status', 'unknown'))
        if str(status).lower() in {'completed', 'complete'}:
            status = 'done'
        attempt = int(p.name.split('_')[-1]) if re.fullmatch('attempt_[0-9]+', p.name) else job.get('attempt', 0)
        out[key] = dict(episode_id=eid, job_id=job['id'], job_refs=[job['id']], kind=job.get('kind', 'legacy'), route_id=job.get('route_id', ''), status=status, attempt=attempt, native_verified=native, execution=execution, cohort=cohort, source_path=str(p), archive_path='episodes/' + eid, source_ids=ids(job.get('payload', {})), payload=job.get('payload', {}))
    for j in jobs:
        add(j.get('episode'), j)
        if j.get('episode'):
            p = Path(j['episode'])
            if p.name.startswith('attempt_') and p.parent.exists():
                for a in sorted(p.parent.glob('attempt_*')):
                    if a.is_dir():
                        add(str(a), j)
        rec = root / 'output/workflow_library/records' / j['id']
        if rec.exists():
            for result in rec.glob('attempt_*/result.json'):
                v = read_json(result, {})
                add(v.get('episode_dir'), j)
    for ep in (meta.get('legacy_usage') or {}).get('episodes', []):
        path = ep.get('episode')
        if path:
            name = Path(path).name
            kind = next((k for k in ['make', 'screen', 'prepare', 'review', 'actor'] if k in name.lower()), 'legacy')
            route = name.split('__')[0]
            add(path, dict(id='legacy__' + name, kind=kind, route_id=route, status=ep.get('status', 'unknown'), payload={}, attempt=0), 'imported_history')
    return sorted(out.values(), key=lambda e: e['episode_id'])


def assign_splits(routes, jobs, episodes, conversations):
    d = DSU()
    route_map = {r['id']: r for r in routes}
    source_map = {c['id']: c for c in conversations}
    for r in routes:
        rn = 'route:' + r['id']
        for source in ids(r):
            d.union(rn, 'source:' + source)
    # Exact conversation bytes connect duplicates, without inventing semantic independence.
    hashes = {}
    for sid, c in source_map.items():
        sha = (c.get('conversation') or {}).get('sha256')
        if sha:
            if sha in hashes:
                d.union('source:' + sid, 'source:' + hashes[sha])
            hashes[sha] = sid
    for e in episodes:
        rn = 'route:' + e['route_id'] if e['route_id'] else 'episode:' + e['episode_id']
        if e['kind'] == 'screen':
            # A multi-source screen completion is indivisible: all its observed sources co-locate.
            for sid in e['source_ids']:
                d.union(rn, 'source:' + sid)
        elif e['route_id'] in route_map:
            e['source_ids'] = sorted(set(e['source_ids'] + ids(route_map[e['route_id']])))
            for sid in e['source_ids']:
                d.union(rn, 'source:' + sid)
        else:
            for sid in e['source_ids']:
                d.union(rn, 'source:' + sid)
    groups = defaultdict(list)
    for node in sorted(d.p):
        groups[d.find(node)].append(node)
    components = []
    node_group = {}
    for nodes in sorted(groups.values(), key=lambda ns: ns[0]):
        cid = 'group_' + hashlib.sha256('\n'.join(nodes).encode()).hexdigest()[:16]
        # Strict hash split. A giant connected component stays intact, even if that removes held-out coverage.
        bucket = int(hashlib.sha256(('wrd-20261025-v1/' + cid).encode()).hexdigest()[:8], 16) % 100
        split = 'test' if bucket < 10 else 'validation' if bucket < 20 else 'train'
        components.append({'component_id': cid, 'split': split, 'nodes': nodes, 'sources': sum(n.startswith('source:') for n in nodes), 'routes': sum(n.startswith('route:') for n in nodes)})
        for node in nodes:
            node_group[node] = (cid, split)
    for e in episodes:
        node = 'route:' + e['route_id'] if e['route_id'] else 'episode:' + e['episode_id']
        e['component_id'], e['split'] = node_group.get(node, ('unresolved', 'quarantine'))
        if e['cohort'] != 'current_pipeline' or not e['native_verified']:
            e['split'] = 'quarantine'
            e['quarantine_reason'] = 'historical_execution_cohort_or_unverified_native'
    return components


META_FILES = [
    'execution.json', 'request.json', 'response.json', 'result.json', 'usage.json', 'accounting.json',
    'native_events.jsonl', 'dispatch.json',
    'openclaw_transport/session_events.jsonl', 'openclaw_transport/container_receipt.json',
    'openclaw_transport/host_receipt.json', 'openclaw_transport/request.json',
    'openclaw_transport/response.json', 'openclaw_transport/native_result.json',
    'openclaw_transport/episode_turns.json', 'openclaw_transport/skill_reads.json',
    'openclaw_transport/evidence/tools.json', 'openclaw_transport/evidence/prompts.json',
    'openclaw_transport/evidence/system-prompt.txt', 'openclaw_transport/evidence/session-branch.json',
    'openclaw_transport/evidence/metadata.json', 'openclaw_transport/evidence/manifest.json',
    'openclaw_transport/evidence/artifacts.json', 'openclaw_transport/evidence/events.jsonl',
]


def make_evaluation_exclusions(root):
    paths = [root / 'output/20261024_experiment_adopt35/current_tasks250.json']
    rows = []
    for p in paths:
        for v in read_json(p, []):
            task = v.get('task', {})
            rows.append({'task_id': v.get('task_id'), 'task_sha256': v.get('task_sha256'), 'revision': v.get('revision'), 'known_source_ids': ids({k: a for k, a in task.items() if k not in ['prompt', 'title']}), 'reserved': True})
    return {'policy': 'No formal evaluation tasks, outputs, judges, or performance labels imported. Original authorized evolution sources remain source data; correlation is not blind generalization.', 'tasks250': rows, 'fixed226': 'Reserved; never use its checkpoints, outputs or scores for training.', 'evaluation_artifact_roots_excluded': ['output/20261024_wrd250_library_run', 'output/experiment_results', 'handoff/20261021_eval250_q_scoring']}


def build(root, output, include_artifacts=True, training=True, resume=False):
    if output.exists() and any(output.iterdir()) and not resume:
        raise SystemExit('Output must be empty; do not overwrite a previous delivery: ' + str(output))
    output.mkdir(parents=True, exist_ok=True)
    jobs, routes, meta, tables = load_state(root)
    conversations = read_json(root / 'output/workflow_library/conversations.json', [])
    episodes = discover_episodes(root, jobs, meta)
    components = assign_splits(routes, jobs, episodes, conversations)
    write_jsonl(output / 'catalog/jobs.jsonl', jobs)
    write_jsonl(output / 'catalog/routes.jsonl', routes)
    write_jsonl(output / 'catalog/episodes.jsonl', [{k: v for k, v in e.items() if k != 'payload'} for e in episodes])
    write_json(output / 'catalog/state_meta.json', clean_value(meta))
    write_json(output / 'catalog/state_other_tables.json', clean_value(tables))
    write_json(output / 'splits/components.json', components)
    write_json(output / 'splits/evaluation_exclusions.json', make_evaluation_exclusions(root))
    arc = Archive(output / 'archive', resume=resume)
    library = root / 'output/workflow_library'
    for n in ['conversations.json', 'routes.json', 'legacy_import.json', 'legacy_costs.json', 'status.json']:
        if (library / n).exists():
            arc.add(library / n, 'pipeline/' + n, 'pipeline_snapshot')
    for n in ['selected_followup_20261024/final', 'delivery_20261024_closeout', 'history', 'confirmed_snapshots', 'skills', 'automatic_continuation']:
        arc.tree(library / n, 'pipeline/' + n, 'history_and_skill_versions')
    arc.add(root / 'output/20261021_workflow_skill_library/source_bindings.json', 'sources/source_bindings.json', 'source_index')
    source_metadata = root / 'output/20261021_workflow_skill_library'
    inventory = read_json(source_metadata / 'inventory.json', {})
    for name in ['inventory.json', 'source_freeze.json', 'source_freeze_before_offline_fixes.json']:
        if (source_metadata / name).exists():
            arc.add(source_metadata / name, 'sources/' + name, 'source_index')
    corpus_path = Path((inventory.get('corpus') or {}).get('path', ''))
    if corpus_path.is_file():
        arc.add(corpus_path, 'sources/original_evolution_corpus.jsonl', 'original_evolution_source')
    bindings = read_json(source_metadata / 'source_bindings.json', {})
    material_index = []
    for sid, binding in bindings.items():
        for m in binding.get('materials', []):
            relative = m.get('relative_path', '')
            if not relative:
                continue
            p = corpus_path.parent / relative
            logical = 'source_materials/' + relative.replace('\\', '/')
            material_index.append(dict(source_id=sid, logical_path=logical, provenance=m))
            if p.is_file():
                arc.add(p, logical, 'original_or_reconstructed_input_material')
            else:
                arc.errors.append({'source_path': str(p), 'logical_path': logical, 'scope': 'source_material', 'reason': 'bound material missing; original available flag preserved', 'source_id': sid})
    write_jsonl(output / 'catalog/source_materials.jsonl', material_index)
    for c in conversations:
        p = c.get('conversation', {}).get('path')
        if p:
            arc.add(p, 'sources/' + c['id'] + '/conversation.json', 'original_evolution_source', source_id=c['id'])
    for i, e in enumerate(episodes):
        p = Path(e['source_path'])
        for n in META_FILES:
            if (p / n).exists():
                arc.add(p / n, e['archive_path'] + '/' + n, e['cohort'], episode_id=e['episode_id'])
        if include_artifacts:
            for n in ['inputs', 'outputs', 'skills']:
                if (p / 'workspace' / n).exists():
                    arc.tree(p / 'workspace' / n, e['archive_path'] + '/workspace/' + n, 'episode_materials_and_outputs')
        if i % 50 == 0:
            print(dumps({'phase': 'archive', 'episodes': i, 'total': len(episodes), 'logical_files': arc.stats['logical_files'], 'unique_objects': len(arc.objects)}), flush=True)
    # Every records attempt includes dispatchless failures and reused baseline receipts too.
    arc.tree(library / 'records', 'pipeline/records', 'all_attempt_records')
    archive_stats = arc.close()
    final_root = library / 'selected_followup_20261024/final/skills'
    shutil.copytree(final_root, output / 'skills/retained29', dirs_exist_ok=resume)
    final_expected = read_json(library / 'selected_followup_20261024/final/29技能文件清单.json', {})
    final_actual = {p.relative_to(final_root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in final_root.rglob('*') if p.is_file()}
    final_ok = all((v if isinstance(v, str) else v.get('sha256')) == final_actual.get(k) for k, v in final_expected.items()) and len(final_expected) == len(final_actual)
    write_json(output / 'catalog/retained_skills_verification.json', {'matches_original_manifest': final_ok, 'expected_files': len(final_expected), 'actual_files': len(final_actual), 'sha256': final_actual})
    shutil.copy2(root / 'research/plans/2026-10-25_wrd_training_dataset.md', output / 'PLAN.md')
    for n in ['A_B_MODULES.md', 'PIPELINE.md']:
        shutil.copy2(root / 'research/designs' / n, output / ('DESIGN_' + n))
    train_stats = {}
    if training:
        from training import export_training
        train_stats = export_training(episodes, routes, output)
        # Apply the identical deterministic credential redaction to derivative JSONL.
        for folder in ['canonical', 'datasets', 'review', 'action_records']:
            d = output / folder
            if not d.exists():
                continue
            for p in d.rglob('*.jsonl'):
                tmp = p.with_suffix('.sanitizing')
                with p.open(encoding='utf-8') as src, tmp.open('w', encoding='utf-8') as dst:
                    for line in src:
                        dst.write(dumps(clean_value(json.loads(line))) + '\n')
                tmp.replace(p)
    summary = {'schema': SCHEMA, 'built_at': datetime.now(timezone.utc).isoformat(), 'design_revision': '5.0.16', 'change_id': 'ALG-20261025-02', 'execution_schema': 'workflow-pipeline-v1', 'source_git_head': os.popen('git -C "' + str(root) + '" rev-parse HEAD').read().strip(), 'jobs': len(jobs), 'jobs_by_kind_status': dict(Counter(j['kind'] + '/' + j['status'] for j in jobs)), 'routes': len(routes), 'route_statuses': dict(Counter(r.get('library_status', 'unknown') for r in routes)), 'original_sources': len(conversations), 'episodes': len(episodes), 'episode_cohorts': dict(Counter(e['cohort'] for e in episodes)), 'native_verified': sum(e['native_verified'] for e in episodes), 'components': len(components), 'components_by_split': dict(Counter(c['split'] for c in components)), 'largest_component_sources': max((c['sources'] for c in components), default=0), 'archive': archive_stats, 'archive_missing_or_excluded': len(arc.errors), 'retained29_verified': final_ok, 'training': train_stats, 'new_model_calls': 0, 'weight_training_started': False, 'student_size': '7B-9B', 'tokenizer': None, 'privacy': 'PRIVATE enterprise data; automated credential removal; no claim of full personal-data anonymization.'}
    write_json(output / 'summary.json', summary)
    print(dumps(summary), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('D:/skillloop'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--metadata-only', action='store_true')
    parser.add_argument('--no-training', action='store_true')
    parser.add_argument('--resume', action='store_true', help='Resume this offline archive from its existing logical index')
    a = parser.parse_args()
    build(a.root.resolve(), a.output.resolve(), not a.metadata_only, not a.no_training, a.resume)
