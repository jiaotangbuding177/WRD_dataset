"""One entry: python pipeline.py resume. All business work uses native OpenClaw.

The queued operations are screen, make, prepare, actor and review. SQLite stores
their progress. No old pipeline, source-proof, replay validator or freeze gate
is imported. Old records are inputs, never executable dependencies.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time

import psutil
from research.workflow import legacy, native, stages, view, continuation

ROOT = Path(__file__).resolve().parent
WAITING_JOB_STATUSES = ('pending', 'running', 'unknown', 'maintenance', 'held')


def route_in_scope(config, route_id):
    """An explicit user continuation scope never wakes unrelated old work."""
    selected = config.get('active_route_ids')
    return selected is None or route_id in selected


def dispatch_lane(job, occupied, config, ready_lanes=None, business_waiting=()):
    """Only non-Actor work may use any idle equivalent model channel."""
    available = set(range(config['workers'])) if ready_lanes is None else set(ready_lanes)
    free = available - set(occupied)
    if job['kind'] == 'actor' or job['payload'].get('__adopt_episode'):
        return job['lane'] if job['lane'] in free else None
    # Prefer an idle channel with no queued paid business pair. If no such
    # channel exists, remain work-conserving rather than deadlock preparation.
    free = (free - set(business_waiting)) or free
    if job['lane'] in free:
        return job['lane']
    extra = config.get('auxiliary_lane')
    return extra if extra in free else min(free) if free else None


def route_dispatch_blocked(job, active_jobs):
    for other in active_jobs:
        if other['route_id'] != job['route_id']:
            continue
        separate_pair = (job['kind'] == other['kind'] == 'actor'
            and other['status'] == 'running' and job['case_id'] != other['case_id']
            and job['lane'] != other['lane']
            and (job['payload'].get('__paired_idle_allocation')
                 or other['payload'].get('__paired_idle_allocation')))
        if not separate_pair:
            return True
    return False


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        return default


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + str(os.getpid()) + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def safe(value):
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value)).strip("._")[:100] or "task"


def episode_path(root, job_id, attempt):
    # Host-only layout; native workspace/mounts and execution remain identical.
    key = hashlib.sha256(job_id.encode("utf-8")).hexdigest()[:16]
    return Path(root) / "episodes" / key / ("attempt_" + str(attempt))


def active_cases(route):
    cases = route.get('tasks', [])
    if 'active_case_ids' in route:
        wanted = set(route['active_case_ids'])
        return [c for c in cases if c.get('id') in wanted]
    return [c for c in cases if c.get('value_revision_of')] or cases


def package_bytes(root):
    if not root or not Path(root).is_dir():
        return {}
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path(root).rglob('*') if p.is_file() and
            not {'__pycache__','.git'}.intersection(p.parts)}


def alive(pid, birth):
    try:
        return abs(psutil.Process(pid).create_time() - birth) < .01
    except (psutil.Error, TypeError):
        return False


def output_json(episode, names):
    base = Path(episode) / "workspace/outputs"
    for name in names:
        value = read(base / name)
        if value is not None:
            return value
    return None


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


class State:
    def __init__(self, out):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.path = self.out / "state.db"
        with self.connect() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
              CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,line INTEGER,processed INTEGER DEFAULT 0);
              CREATE TABLE IF NOT EXISTS routes(id TEXT PRIMARY KEY,payload TEXT);
              CREATE TABLE IF NOT EXISTS jobs(
                id TEXT PRIMARY KEY,kind TEXT,route_id TEXT,case_id TEXT,arm TEXT,
                payload TEXT,status TEXT DEFAULT 'pending',attempt INTEGER DEFAULT 0,
                lane INTEGER,episode TEXT,result TEXT,error TEXT);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15, factory=ClosingConnection)
        db.row_factory = sqlite3.Row
        return db

    def meta(self, key, value=None):
        with self.connect() as db:
            if value is not None:
                db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, json.dumps(value, ensure_ascii=False)))
                return value
            row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else None

    def routes(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM routes ORDER BY id")]

    def route(self, value):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO routes VALUES(?,?)", (value["id"], json.dumps(value, ensure_ascii=False)))

    def jobs(self):
        with self.connect() as db:
            return [self.decode_job(row) for row in db.execute("SELECT * FROM jobs ORDER BY rowid")]

    @staticmethod
    def decode_job(row):
        if row is None:
            return None
        row = dict(row)
        row['payload'] = json.loads(row['payload'])
        row['result'] = json.loads(row['result']) if row['result'] else None
        return row

    def job(self, key, **updates):
        if not updates:
            with self.connect() as db:
                return self.decode_job(db.execute('SELECT * FROM jobs WHERE id=?',(key,)).fetchone())
        fields, values = [], []
        for name, value in updates.items():
            if name not in {"status", "attempt", "lane", "episode", "result", "error", "payload"}:
                raise ValueError(name)
            fields.append(name + "=?")
            values.append(json.dumps(value, ensure_ascii=False) if name in {"result", "payload"} else value)
        with self.connect() as db:
            db.execute("UPDATE jobs SET " + ",".join(fields) + " WHERE id=?", (*values, key))

    def enqueue(self, kind, route_id, payload, lane, case_id="", arm="", result=None):
        allocation=payload.get('case',{}).get('_paired_idle_allocation')
        if kind=='actor' and allocation and allocation.get('to')==lane:
            payload={**payload,'__paired_idle_allocation':allocation}
        key = "__".join(safe(part) for part in (kind, route_id, case_id, arm) if part)
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO jobs(id,kind,route_id,case_id,arm,payload,lane,status,result) VALUES(?,?,?,?,?,?,?,?,?)",
                       (key, kind, route_id, case_id, arm, json.dumps(payload, ensure_ascii=False), lane,
                        "done" if result else "pending", json.dumps(result, ensure_ascii=False) if result else None))
        return key


class Pipeline:
    def __init__(self, config, run_native=None):
        self.config = config
        self.out = Path(config["output"])
        self.state = State(self.out)
        self.execute_native = run_native or native.run_native
        self.bindings = read(config["source_bindings"], {})
        self.service_pool = None
        self.service_state = None

    def initialize(self):
        if self.state.meta("imported"):
            return
        old = legacy.import_legacy(self.config)
        screened = set(old["screened_source_ids"])
        with self.state.connect() as db:
            db.executemany("INSERT OR IGNORE INTO sources VALUES(?,?,?)", [
                (sid, binding.get("physical_line"), int(sid in screened)) for sid, binding in old["bindings"].items()])
        for index, route in enumerate(old["routes"]):
            route["lane"] = route.get("lane") if isinstance(route.get("lane"), int) else index % 8
            route["make_status"] = "待制作"
            if route.get("existing_skill_root"):
                route["skill_root"] = self.publish(route["id"], route["existing_skill_root"])
                route["make_status"] = "候选资源已归档（复用原资源）"
                route['library_status'] = 'candidate'
            route["tasks"] = route.get("existing_tasks", [])
            self.state.route(route)
            for cid, arms in route.get("existing_runs", {}).items():
                for arm, result in arms.items():
                    if result.get("complete") or result.get('dispatched'):
                        key = self.state.enqueue("actor", route["id"], {}, route["lane"], cid, arm, result)
                        if not result.get('complete'):
                            self.state.job(key, status='unknown', error='旧任务已派发但未正常结束，原费用保留，不盲目再发。')
        write(self.out / "legacy_import.json", {"summary": old["summary"], "runs": old["legacy_runs"]})
        self.state.meta("legacy_usage", old.get("legacy_usage", {}))
        self.state.meta("legacy_summary", old["summary"])
        self.state.meta("imported", datetime.now().astimezone().isoformat())
        write(self.out / "conversations.json", [
            {"id": sid, "line": b.get("physical_line"), "conversation": b.get("conversation")}
            for sid, b in old["bindings"].items()])
        self.plan()
        self.refresh("已导入", "已完成的制作和业务结果直接复用。")

    def publish(self, sid, skill):
        """Store a candidate package. Copying files is not value-based admission."""
        dest = self.out / "skills" / safe(sid)
        source = Path(skill).resolve()
        def files(root):
            return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in root.rglob('*') if p.is_file() and
                    '__pycache__' not in p.parts and '.git' not in p.parts}
        if dest.exists() and files(source) == files(dest):
            return str(dest)
        # A whole-directory replacement mirrors deletions too. Keep the old
        # package outside the skill library; never merge stale programs back in.
        staging = self.out / 'publish_staging' / (safe(sid) + '-' + str(time.time_ns()))
        staging.resolve().relative_to(self.out.resolve())
        dest.resolve().relative_to((self.out / 'skills').resolve())
        staging.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, staging, ignore=shutil.ignore_patterns('__pycache__', '.git'))
        dest.parent.mkdir(parents=True, exist_ok=True)
        backup = self.out / 'history/skill_packages' / (safe(sid) + '-' + str(time.time_ns()))
        backup.resolve().relative_to((self.out / 'history/skill_packages').resolve())
        if dest.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            os.replace(dest, backup)
        try:
            os.replace(staging, dest)
        except Exception:
            if backup.exists() and not dest.exists():
                os.replace(backup, dest)
            raise
        return str(dest)

    def review_key(self, route, jobs):
        """A request identity for new evidence, not a pass/fail gate."""
        root = Path(route['skill_root'])
        package = {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        cases = active_cases(route)
        case_ids = {str(c.get('id','c'+str(i+1))) for i,c in enumerate(cases)}
        basis = {'skill':package, 'cases':cases,
                 'jobs':[{k:j.get(k) for k in ('id','status','attempt','episode','result')}
                         for j in jobs if j['kind']=='make' or (j['kind']=='actor' and j['case_id'] in case_ids)],
                 'recording':'complete-making-and-raw-read-evidence-v1'}
        supplements = continuation.evidence_receipts(jobs)
        if supplements:
            basis['usage_supplements'] = supplements
        return hashlib.sha256(json.dumps(basis,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]

    def repair_selection(self, plan_path):
        """Resume only the explicitly requested missing work in the same queue."""
        plan = read(plan_path)
        if not isinstance(plan, dict) or not plan.get('id'):
            raise ValueError('补接计划缺少id')
        campaign = safe(plan['id'])
        saved = self.out/'selection_repair'/campaign/'plan.json'
        if saved.exists() and read(saved) != plan:
            raise ValueError('同一补接计划内容已固定；不覆盖旧派发范围')
        write(saved, plan)
        from research.workflow import coverage
        source_plan = saved.with_name('sources.json')
        write(source_plan, plan.get('sources', []))
        source_receipt = coverage.prepare_recheck(self, source_plan) if plan.get('sources') else {}
        routes = {r['id']:r for r in self.state.routes()}
        attached = []
        for item in plan.get('routes', []):
            route = routes.get(item['route_id'])
            if not route or route.get('selection_repair', {}).get('id') == campaign:
                continue
            if route.get('selection_repair'):
                route.setdefault('selection_repair_history', []).append(route['selection_repair'])
            if item.get('materials_file'):
                route['continuation_materials_file'] = item['materials_file']
            route['selection_repair'] = {
                'id':campaign, 'reselect':bool(item.get('reselect')),
                'repair':bool(item.get('repair')), 'reason':item.get('reason',''),
                'status':'waiting', 'created_at':datetime.now().astimezone().isoformat()}
            # Keep the original task list, results and decisions. An old task
            # changes scope only after the preparer explains its work mismatch.
            route['active_case_ids'] = [c['id'] for c in active_cases(route)]
            self.state.route(route)
            attached.append(route['id'])
        prior = self.state.meta('selection_repair') or {}
        self.state.meta('selection_repair', {'id':campaign,'plan_path':str(saved),
            'started_at':prior.get('started_at') if prior.get('id')==campaign else datetime.now().astimezone().isoformat(),
            'source_rechecks':len(plan.get('sources',[])),
            'task_reselections':sum(bool(x.get('reselect')) for x in plan.get('routes',[])),
            'resource_repairs':sum(bool(x.get('repair')) for x in plan.get('routes',[])),
            'source_receipt':source_receipt})
        self.plan()
        return {'id':campaign,'new_route_continuations':attached,'source_receipt':source_receipt}

    def continue_selection(self, route, jobs):
        follow = route.get('selection_repair')
        if not follow:
            return False
        waiting = [j for j in jobs if j['status'] in WAITING_JOB_STATUSES]
        if follow.get('status') == 'complete':
            if not waiting:
                if follow.get('outcome') == 'unchanged_resource':
                    return True
                return False
            # A review made while actors were temporarily held is not the end
            # of the route. Keep that paid review and continue the same actors.
            follow['status'] = 'trial' if any(j['kind'] == 'actor' for j in waiting) else 'blocked'
            follow.pop('outcome', None)
            self.state.route(route)
        if waiting:
            return True  # Existing paid work finishes; no package switch in flight.
        if route.get('skip_reason'):
            follow.update(status='complete',outcome='no_reuse')
            self.state.route(route)
            return True
        sid, lane = route['id'], route['lane']
        if follow.get('reselect'):
            key = follow.get('prepare_job')
            if not key:
                key = self.state.enqueue('prepare',sid,{
                    'selection_repair':follow['id'], 'full_catalog':True,
                    'repair_scope':follow['reason'], 'previous_reason':route.get('task_note',''),
                    'previous_case_decisions':route.get('case_decisions',[])},lane,
                    'reselect-'+follow['id'])
                follow.update(prepare_job=key,status='preparing')
                self.state.route(route)
                return True
            previous = self.state.job(key)
            if previous['status'] != 'done':
                follow['status'] = 'blocked'; self.state.route(route); return True
            if not active_cases(route):
                follow['status'] = 'blocked_inputs'; self.state.route(route); return True
        if follow.get('repair'):
            key = follow.get('make_job')
            if not key:
                used, limit, exhausted = continuation.resource_revision_budget(self, route, jobs)
                if exhausted:
                    follow.update(status='complete', outcome='resource_revision_limit')
                    route['resource_revision_policy'] = {'limit':limit, 'used':used,
                        'resource_repair_closed':True, 'reason':'用户限定最多4轮资源修订；不新增第5轮，已有证据与材料仍可补齐。'}
                    self.state.route(route)
                    return True
                if self.config.get('resource_revision_mode') == 'evidence_inputs_only':
                    follow.update(status='complete', outcome='resource_repair_paused')
                    route['resource_revision_policy'] = {'limit':limit, 'used':used,
                        'resource_repair_paused':True, 'reason':'用户本轮只补证据和独立输入，不开下一轮资源修订。'}
                    self.state.route(route)
                    return True
                feedback = self.out/'selection_repair'/follow['id']/sid/'feedback.json'
                write(feedback, {'prior_review':route.get('value_review',{}),
                    'repair_scope':follow['reason'],
                    'instruction':'沿现有资源只修具体重复工作；直接用程序，不默认全读、等确认或加核验循环。制作记录留包外，所有公开程序完整复现。'})
                key = self.state.enqueue('make',sid,{'selection_repair':follow['id'],
                    'previous':{'skill_root':route.get('skill_root'),'feedback':str(feedback),
                                'making_jobs':[j for j in jobs if j['kind']=='make']}},lane,
                    'repair-'+follow['id'])
                follow.update(make_job=key,status='making')
                self.state.route(route)
                return True
            if self.state.job(key)['status'] != 'done':
                follow['status']='blocked'; self.state.route(route); return True
        cases = active_cases(route)
        if not cases:
            follow['status']='blocked_inputs'; self.state.route(route); return True
        new = False
        known = {j['id'] for j in jobs}
        for case in cases:
            for arm in ('no_skill','workflow'):
                expected_key='__'.join(safe(p) for p in ('actor',sid,case['id'],arm))
                if expected_key in known:
                    continue
                baseline = self.reusable_baseline(route,case,jobs) if arm=='no_skill' else None
                reused = {**baseline['result'],'reused_from_job':baseline['id']} if baseline else None
                key = self.state.enqueue('actor',sid,{'case':case,'selection_repair':follow['id']},self.case_lane(route,case,jobs),case['id'],arm,result=reused)
                new = new or key not in known
        follow['status']='trial'
        if not new:
            key = self.review_key(route,jobs)
            if (self.state.meta('review_evidence_reused') or {}).get(sid)==key:
                follow.update(status='complete',outcome=route.get('value_review',{}).get('decision','defer'),
                              review_reused=True)
                self.state.route(route)
                return True
            follow['review_job'] = self.state.enqueue('review',sid,{
                'selection_repair':follow['id'],'evidence_key':key,'after_revision':bool(follow.get('repair'))},
                lane,'evidence-'+key)
            follow['status']='reviewing'
            existing = self.state.job(follow['review_job'])
            if existing['status']=='done':
                follow.update(status='complete',outcome=route.get('value_review',{}).get('decision','defer'))
            elif existing['status'] in ('failed','held','unknown'):
                follow['status']='blocked'
        self.state.route(route)
        return True

    def case_lane(self, route, case, jobs):
        """A revision inherits its ancestor's actual paired business channel."""
        cases = {c['id']:c for c in route.get('tasks',[])}
        current = case
        seen = set()
        while current and current.get('id') not in seen:
            cid = current.get('id'); seen.add(cid)
            # Explicit pair allocation is authoritative even before dispatch.
            allocated = [j for j in jobs if j.get('route_id')==route['id'] and
                j.get('case_id')==cid and j.get('payload',{}).get('__paired_idle_allocation')]
            if allocated:
                return allocated[0]['lane']
            if isinstance(current.get('native_lane'),int):
                return current['native_lane']
            started = [j for j in jobs if j.get('route_id')==route['id'] and
                j.get('case_id')==cid and j.get('kind')=='actor' and
                (j.get('attempt') or j.get('result'))]
            if started:
                return started[0]['lane']
            current = cases.get(current.get('value_revision_of'))
        return route['lane']

    def reusable_baseline(self, route, case, jobs):
        """Reuse only identical prompt/files and the unchanged native execution."""
        workspace = Path(case['_prepared_episode'])/'workspace' if case.get('_prepared_episode') else None
        if workspace is None:
            preparer=self.state.job('prepare__'+route['id'])
            if preparer and preparer.get('episode'):
                workspace=Path(preparer['episode'])/'workspace'
        expected = stages.actor_task(case, workspace)
        case_lane = self.case_lane(route,case,jobs)
        lane = next((x for x in read(self.config.get('lanes_file'),[]) if x['id']==case_lane),None)
        if not lane:
            return None
        profile_ref=lane['profile']['path'] if isinstance(lane['profile'],dict) else lane['profile']
        profile=read(profile_ref,{})
        identity={'profile':profile_ref,'credentials':lane['credentials'],
                  'consumer':str(Path(profile['runtime_dir'])/'consumer.py')}
        for job in jobs:
            if (job['kind']!='actor' or job['route_id']!=route['id'] or job['arm']!='no_skill'
                    or job['status'] not in ('done','failed') or job['payload'].get('__excluded_condition')):
                continue
            result=job.get('result') or {}
            episode=result.get('episode_dir') or result.get('episode') or job.get('episode')
            if not episode: continue
            base=Path(episode); request=read(base/'request.json',{}); env=read(base/'execution.json',{})
            if job['status']=='failed':
                host=read(base/'openclaw_transport/host_receipt.json',{})
                if (native._process_state(read(base/'process.json',{}))!='exited' or
                        host.get('cleanup_returncode')!=0 or host.get('cleanup_error')):
                    continue
            fixed={'image':native.IMAGE,'openclaw_version':native.OPENCLAW_VERSION,'model':native.MODEL,
                   'max_tokens':native.MAX_TOKENS,'timeout_seconds':native.TIMEOUT,'lane':case_lane,
                   'backend':'native','custom_agent_loop':False}
            if request.get('input')!=expected['prompt'] or any(env.get(k)!=v for k,v in fixed.items()):
                continue
            if request.get('learned_skills') or request.get('context') or request.get('followup_inputs') or \
                    set(request.get('required_commands',[]))!={'python','openclaw'} or any(
                    not env.get(k) or Path(env[k]).resolve()!=Path(v).resolve() for k,v in identity.items()):
                continue
            # Compare the bytes actually mounted in the completed baseline,
            # not a mutable source file that may have changed afterwards.
            old={x['mount']:base/'workspace'/x['mount'] for x in request.get('resources',[])}
            if set(old)!=set(x['mount'] for x in expected['resources']): continue
            try:
                same=all(old[x['mount']].is_file() and
                    hashlib.sha256(old[x['mount']].read_bytes()).digest()==hashlib.sha256(Path(x['path']).read_bytes()).digest()
                    for x in expected['resources'])
            except OSError:
                same=False
            if same: return job
        return None

    def revised_trials(self, route, suffix):
        jobs=self.state.jobs(); revised=[]
        for case in active_cases(route):
            cid=case['id']; new_id=cid[:55]+'--'+safe(suffix)[:24]+'-'+hashlib.sha256(cid.encode()).hexdigest()[:8]
            copied={**case,'id':new_id,'value_revision_of':cid,
                    'native_lane':self.case_lane(route,case,jobs)}
            ancestors={cid};parents={c['id']:c for c in route.get('tasks',[])};parent=case
            while parent.get('value_revision_of') and parent['value_revision_of'] not in ancestors:
                ancestors.add(parent['value_revision_of'])
                parent=parents.get(parent['value_revision_of'],{})
            allocation=case.get('_paired_idle_allocation') or next((
                j['payload']['__paired_idle_allocation'] for j in jobs
                if j['route_id']==route['id'] and j['case_id'] in ancestors and
                not j['payload'].get('__excluded_condition') and j['lane']==copied['native_lane']
                and j['payload'].get('__paired_idle_allocation')),None)
            if allocation: copied['_paired_idle_allocation']=allocation
            baseline=self.reusable_baseline(route,copied,jobs)
            if baseline:
                self.state.enqueue('actor',route['id'],{'case':copied},copied['native_lane'],new_id,'no_skill',
                    {**baseline['result'],'reused_from_job':baseline['id']})
            revised.append(copied)
        existing={c['id']:c for c in route.get('tasks',[])}
        existing.update({c['id']:c for c in revised})
        route['tasks']=list(existing.values()); route['active_case_ids']=[c['id'] for c in revised]
        self.state.route(route)

    def recover_legacy_routes(self):
        """Continue paid proposals omitted by the old formal-card export."""
        if self.state.meta('legacy_routes_recovered'):
            first = self.state.job('screen__legacy-route-continuation')
            if (first and first['status'] == 'done' and not self.state.meta('legacy_deferred_recovered')):
                prior = read(self.out / 'history/legacy_route_continuation.json', {})
                deferred = prior.get('deferred_sources', [])
                source_ids = sorted({row['source_id'] for row in deferred if row.get('source_id') in self.bindings})
                if source_ids:
                    self.state.enqueue('screen', 'legacy-deferred-continuation', {
                        'source_ids': source_ids, 'recovery': {'candidates': [], 'new_without_cards': deferred,
                        'continuation_type': 'previously_deferred'}}, 0)
                self.state.meta('legacy_deferred_recovered', {'source_count': len(source_ids)})
            return
        recovery = legacy.recover_pending_routes(self.config, self.state.routes())
        known = {r['id']: r for r in self.state.routes()}
        for merge in recovery.get('explicit_merges', []) + recovery.get('reuse_links', []):
            target = known.get(merge.get('target_id') or merge.get('route_id'))
            if target:
                target['source_ids'] = sorted(set(target.get('source_ids', [])) |
                                              set(merge.get('source_ids', [])))
                for field in ('conditions', 'conflicts'):
                    values = target.get(field) or []
                    values = values if isinstance(values, list) else [values]
                    for item in merge.get(field, []):
                        if item not in values:
                            values.append(item)
                    target[field] = values
                self.state.route(target)
        source_ids = sorted({sid for item in recovery.get('candidates', [])
                             for sid in item.get('source_ids', []) if sid in self.bindings} |
                            {item.get('source_id') for item in recovery.get('new_without_cards', [])
                             if item.get('source_id') in self.bindings})
        if source_ids:
            # The fixed job identity and the normal receipt make recovery
            # resumable without re-screening paid conversations on restart.
            self.state.enqueue('screen', 'legacy-route-continuation',
                               {'source_ids': source_ids, 'recovery': recovery}, 0)
        write(self.out / 'history/legacy_route_continuation.json', recovery)
        self.state.meta('legacy_routes_recovered', recovery.get('summary', {}))

    def plan(self):
        owner = self.state.meta('owner') or {}
        if owner.get('pid') == os.getpid():
            self.recover_legacy_routes()
        binding_file = Path(self.config['source_bindings'])
        stamp = (binding_file.stat().st_size,binding_file.stat().st_mtime_ns)
        if getattr(self,'_binding_stamp',None) != stamp:
            self.bindings = read(binding_file,{})
            self._binding_stamp = stamp
        all_jobs = self.state.jobs()
        by_route, known_jobs = {}, {j['id']:j for j in all_jobs}
        for job in all_jobs:
            by_route.setdefault(job['route_id'],[]).append(job)
        reused_reviews = self.state.meta('review_evidence_reused') or {}
        screens = [job for job in all_jobs if job['kind'] == 'screen']
        covered = {sid for job in screens if job['status'] != 'done'
                   for sid in job['payload'].get('source_ids', [])}
        tried = {}
        for job in screens:
            for sid in job['payload'].get('source_ids', []):
                tried[sid] = tried.get(sid, 0) + job['attempt']
        with self.state.connect() as db:
            remaining = [row[0] for row in db.execute("SELECT id FROM sources WHERE processed=0 ORDER BY line,id")
                         if row[0] not in covered and tried.get(row[0], 0) < 2]
        size = int(self.config.get("screen_batch_size", 16))
        for index in range(0, len(remaining), size):
            if self.config.get('active_route_ids') is not None:
                break  # This run resumes selected resources, not source discovery.
            batch = remaining[index:index + size]
            key = hashlib.sha256("\n".join(batch).encode()).hexdigest()[:12]
            # Follow up only omitted sources; never resend a completed batch.
            if any(tried.get(sid) for sid in batch):
                key += '_remaining'
            self.state.enqueue("screen", key, {"source_ids": batch}, (index // size) % 8)
        for route in self.state.routes():
            sid, lane = route["id"], route["lane"]
            if not route_in_scope(self.config, sid):
                continue
            if continuation.automatic_followup(self, route, by_route.get(sid, []),known_jobs):
                continue
            if self.continue_selection(route, by_route.get(sid, [])):
                continue
            route_jobs = [j for j in by_route.get(sid,[]) if j['kind']!='review']
            if route.get("skip_reason"):
                continue
            if not route.get("skill_root"):
                self.state.enqueue("make", sid, {}, lane)
                continue
            if not route.get("tasks"):
                if any(j['kind']=='make' and j['status'] in WAITING_JOB_STATUSES for j in route_jobs):
                    continue
                # A finished preparer may already have written tasks despite an old gate.
                prepared = route.get("prepared_tasks_output")
                recovered = read(prepared, {}) if prepared else {}
                cases = route.get('prepared_tasks') or (recovered.get("cases", []) if isinstance(recovered, dict) else [])
                if cases:
                    route["tasks"] = cases
                    self.state.route(route)
                else:
                    prepare_jobs = [j for j in route_jobs if j['kind']=='prepare']
                    if not prepare_jobs:
                        self.state.enqueue("prepare", sid, {'full_catalog':True}, lane)
                    elif (all(j['status']=='done' for j in prepare_jobs) and
                          not any(j['payload'].get('full_catalog') for j in prepare_jobs)):
                        # One complete-search continuation, reusing the prior
                        # zero-case result. No repeated pages of paid searches.
                        seen = []
                        for j in prepare_jobs:
                            old = read(self.out/'records'/j['id']/('attempt_'+str(j['attempt']))/'input/task_sources.json', [])
                            seen.extend(v.get('source_id') for v in old if v.get('source_id'))
                        self.state.enqueue('prepare',sid,{'full_catalog':True,
                            'previous_source_ids':sorted(set(seen)),
                            'previous_reason':route.get('task_note','')},lane,'full-search')
                    continue
            new_actor = False
            for index, case in enumerate(active_cases(route)):
                cid = str(case.get("id", "c" + str(index + 1)))
                for arm in ("no_skill", "workflow"):
                    expected_key='__'.join(safe(p) for p in ('actor',sid,cid,arm))
                    if expected_key in known_jobs:
                        continue
                    baseline = self.reusable_baseline(route,case,by_route.get(sid,[])) if arm=='no_skill' else None
                    reused = {**baseline['result'],'reused_from_job':baseline['id']} if baseline else None
                    key = self.state.enqueue("actor", sid, {"case": case}, self.case_lane(route,case,by_route.get(sid,[])), cid, arm,result=reused)
                    new_actor = new_actor or key not in known_jobs
            # An empty preparation is a data limitation, not a paid review.
            # Wait for the actual business arms, then assess each evidence set once.
            if new_actor or any(j['status'] in WAITING_JOB_STATUSES for j in route_jobs):
                continue
            reviews = [j for j in by_route.get(sid,[]) if j['kind']=='review']
            if any(j['status'] in WAITING_JOB_STATUSES for j in reviews):
                continue
            if route.get('library_status') in ('retained','rejected'):
                continue
            # Review only a new evidence identity. Repair count is not a terminal
            # outcome; explicitly requested continuations use the same queue.
            key = self.review_key(route,route_jobs)
            if reused_reviews.get(sid)==key:
                continue
            self.state.enqueue('review',sid,{'evidence_key':key,
                'after_revision':any(j['kind']=='make' and j.get('case_id')=='value-revision' and j['status']=='done' for j in route_jobs)},lane,'evidence-'+key)

    def build(self, job):
        route = next((r for r in self.state.routes() if r["id"] == job["route_id"]), None)
        workdir = self.out / "records" / job["id"] / ("attempt_" + str(job["attempt"])) / "input"
        workdir.mkdir(parents=True, exist_ok=True)
        if job["kind"] == "screen":
            task = stages.screen_task(self.bindings, job["payload"]["source_ids"], self.state.routes(), workdir,
                                      recovery=job['payload'].get('recovery'))
        elif job["kind"] == "make":
            previous = job["payload"].get("previous") or {
                "episode": route.get("previous_episode"), "skill_root": route.get("candidate_skill_root"),
                "feedback": route.get("previous_feedback")}
            task = stages.make_task(route, self.bindings, self.state.routes(), previous, workdir)
        elif job["kind"] == "prepare":
            task = stages.prepare_task(route, self.bindings, workdir, continuation=job['payload'])
        elif job['kind'] == 'review':
            from research.workflow.business_cost import all_attempts
            jobs=self.state.jobs()
            evidence_jobs=[{**j,'all_attempts':all_attempts(j,jobs,self.out/'records')}
                           if j['kind']=='actor' else j for j in jobs]
            task = stages.review_task(route, evidence_jobs, workdir)
        else:
            preparer = self.state.job('prepare__' + route['id'])
            prepared_episode = job['payload']['case'].get('_prepared_episode')
            workspace = Path(prepared_episode) / 'workspace' if prepared_episode else (
                Path(preparer['episode']) / 'workspace' if preparer and preparer.get('episode') else None)
            task = stages.actor_task(job["payload"]["case"], workspace)
        skills = [{"id": route["id"], "path": route["skill_root"]}] if job["arm"] == "workflow" else []
        return task, skills

    def execute(self, job):
        try:
            if job['payload'].get('__adopt_episode'):
                return self.execute_native(Path(job['episode']), '', [], [], job['lane'], self.config)
            task, skills = self.build(job)
            if self.service_pool is not None and not self.service_pool.can_dispatch(job['lane']):
                return {'status':'deferred_service','error':'模型服务在实际投递前失联，未启动原生会话。',
                        'episode_dir':job['episode'],'dispatch_state':'not_started',
                        'usage':{'total_tokens':0,'model_calls':0,'unknown_calls':0}}
            return self.execute_native(Path(job["episode"]), task["prompt"], task["resources"], skills,
                                       job["lane"], self.config)
        except Exception as error:
            not_started = not (Path(job['episode']) / 'dispatch.json').is_file()
            return {"status": "failed", "error": str(error), "episode_dir": job["episode"],
                    "dispatch_state": 'not_started' if not_started else 'unknown',
                    "usage": {"total_tokens": 0 if not_started else None,
                              "model_calls": 0 if not_started else None, "unknown_calls": 0 if not_started else None}}

    def finish(self, job, result):
        episode = Path(job["episode"])
        write(self.out / "records" / job["id"] / ("attempt_" + str(job["attempt"])) / "result.json", result)
        if result.get("status") != "completed":
            status = "unknown" if result.get("status") == "dispatched_unresolved" else "failed"
            self.state.job(job["id"], status=status, result=result, error=result.get("error", "原生会话未正常结束"))
            return
        route = next((r for r in self.state.routes() if r["id"] == job["route_id"]), None)
        if job["kind"] == "screen":
            value = output_json(episode, ("routes.json", "screen.json")) or {}
            processed = self.apply_routes(job, value)
            if job['payload'].get('recovery'):
                missing = set(job['payload']['source_ids']) - processed
                if missing and job['attempt'] < 2:
                    recovery = dict(job['payload']['recovery'])
                    recovery['candidates'] = [{**item, 'source_ids': [s for s in item.get('source_ids', []) if s in missing]}
                        for item in recovery.get('candidates', []) if missing.intersection(item.get('source_ids', []))]
                    recovery['new_without_cards'] = [item for item in recovery.get('new_without_cards', [])
                                                     if item.get('source_id') in missing]
                    self.state.job(job['id'], status='pending', result=result,
                                   payload={'source_ids': sorted(missing), 'recovery': recovery},
                                   error='已回答的路线已接回；只继续遗漏的旧候选，不重复初筛。')
                    self.plan()
                    return
                if missing:
                    self.state.job(job['id'], status='failed', result=result,
                                   error='旧候选仍有'+str(len(missing))+'条来源未回应，保留原结果，其他路线继续。')
                    self.plan()
                    return
        elif job["kind"] == "make":
            before_package = package_bytes(route.get('skill_root'))
            before_library_status = route.get('library_status')
            making = output_json(episode, ("making.json",)) or {}
            making = making if isinstance(making, dict) else {}
            skill = next((p for p in [episode / "workspace/outputs/skill", episode / "workspace/outputs/candidate/skill"]
                          if (p / "SKILL.md").is_file()), None)
            if making.get("skip_reason") or making.get("no_reuse"):
                route["skip_reason"] = making.get("skip_reason", "无可替代的公共工作")
                route["make_status"] = "不生成：" + route["skip_reason"]
            elif skill:
                route["skill_root"] = self.publish(route["id"], skill)
                route["make_status"] = "候选资源已生成，复用价值待确认"
                route['library_status'] = 'candidate'
            elif job["attempt"] < int(self.config.get("making_attempts", 2)):
                self.state.job(job["id"], status="pending", result=result, payload={**job['payload'], "previous": {
                    "episode": str(episode), "feedback": str(episode / "workspace/outputs/making.json")}},
                    error="原生制作结束但没有技能目录，保留原结果后局部接续。")
                return
            else:
                self.state.job(job["id"], status="failed", result=result, error="制作没有产生技能目录；其它路线继续。")
                return
            self.state.route(route)
            if job['payload'].get('selection_repair') and route.get('skill_root') and not route.get('skip_reason'):
                if before_package and before_package == package_bytes(route['skill_root']):
                    # A maker returning the same bytes is not a new business
                    # condition. Preserve its fee, never rerun completed actors.
                    route['selection_repair'].update(status='complete',
                        outcome='unchanged_resource', business_reused=True)
                    route['continuation_note']='制作返回相同资源，复用原业务结果，不重新付费试用。'
                    route['library_status']=before_library_status or 'candidate'
                    self.state.route(route)
                    prior = self.state.meta('review_evidence_reused') or {}
                    prior[route['id']] = self.review_key(route,self.state.jobs())
                    self.state.meta('review_evidence_reused',prior)
                else:
                    self.revised_trials(route,job['payload']['selection_repair'])
            elif job.get('case_id') == 'value-revision' and route.get('skill_root') and not route.get('skip_reason'):
                self.revised_trials(route,'value-revision')
        elif job["kind"] == "prepare":
            value = output_json(episode, ("tasks.json", "development_tasks.json")) or {}
            value = value if isinstance(value, dict) else {}
            cases = value.get("cases") or []
            if job['payload'].get('selection_repair'):
                old_cases={c['id']:c for c in route.get('tasks',[])}
                previous_ids={c['id'] for c in active_cases(route)}
                selected=[]; decisions=value.get('case_decisions',[])
                for case in cases if isinstance(cases,list) else []:
                    if not isinstance(case,dict): continue
                    old_id=case.get('reuse_existing_case_id')
                    if old_id in old_cases:
                        # Reuse the exact old task, not a model's rewritten copy.
                        if old_cases[old_id].get('source_id') in set(route.get('learning_source_ids',route.get('source_ids',[]))):
                            decisions.append({'case_id':old_id,'action':'exclude','reason':'原任务来源已经参与当前技能制作，不能算独立试用；原结果保留'})
                            continue
                        selected.append(old_cases[old_id]); continue
                    if case.get('source_id') not in self.bindings:
                        value.setdefault('blocked_inputs',[]).append({'source_id':case.get('source_id'),
                            'reason':'没有对应的真实来源记录；原输出保留'})
                        continue
                    if case.get('source_id') in set(route.get('learning_source_ids',route.get('source_ids',[]))):
                        value.setdefault('blocked_inputs',[]).append({'source_id':case.get('source_id'),
                            'reason':'已用于本技能制作，不能当独立试用；原输出保留'})
                        continue
                    digest=hashlib.sha256(json.dumps(case,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:12]
                    cid='dev-'+safe(case.get('source_id','source'))[:35]+'-'+digest
                    selected.append({**case,'id':cid,'_prepared_episode':str(episode)})
                selected=list({c['id']:c for c in selected}.values())
                selected_ids={c['id'] for c in selected}
                for cid in previous_ids-selected_ids:
                    prior_case=old_cases.get(cid,{})
                    if prior_case.get('source_id') in set(route.get('learning_source_ids',route.get('source_ids',[]))):
                        reason='原任务来源已参与当前技能制作，不能算独立试用；原结果与费用保留'
                        old_cases[cid]={**prior_case,'scope_note':reason}
                        decisions.append({'case_id':cid,'action':'exclude','reason':reason})
                        continue
                    decision=next((x for x in decisions if x.get('case_id')==cid),None)
                    if not decision or decision.get('action')!='exclude' or not decision.get('reason'):
                        # An omitted matching negative is not silently dropped.
                        if cid in old_cases:
                            selected.append(old_cases[cid]); selected_ids.add(cid)
                    else:
                        old_cases[cid]={**old_cases[cid],'scope_note':'历史错配/输入不适用，原结果与费用保留：'+decision['reason']}
                old_cases.update({c['id']:c for c in selected})
                route['tasks']=list(old_cases.values())
                route['active_case_ids']=[c['id'] for c in selected]
                route['case_decisions']=decisions
                route['blocked_inputs']=value.get('blocked_inputs',[])
                route['selection_repair']['status']='prepared' if selected else 'blocked_inputs'
            else:
                independent=[]
                for case in cases if isinstance(cases,list) else []:
                    if not isinstance(case,dict): continue
                    source=case.get('source_id')
                    if source not in self.bindings or source in set(route.get('learning_source_ids',route.get('source_ids',[]))):
                        value.setdefault('blocked_inputs',[]).append({'source_id':source,'reason':'缺真实独立来源，不派业务；原准备输出保留'})
                        continue
                    independent.append({**case,'_prepared_episode':str(episode)})
                route['tasks']=independent
                route['blocked_inputs']=value.get('blocked_inputs',[])
            route["task_note"] = value.get("reason", "没有足够的真实业务输入") if not active_cases(route) else ""
            self.state.route(route)
        elif job['kind'] == 'review':
            review = output_json(episode, ('review.json',))
            if not isinstance(review, dict) or review.get('decision') not in ('retain','revise','reject','defer'):
                self.state.job(job['id'], status='failed', result=result, error='筛选未给出有效取舍；原结果保留，不重复付费。')
                return
            evidence = read(self.out/'records'/job['id']/('attempt_'+str(job['attempt']))/'input/review_input.json', {})
            if review['decision']=='retain' and not (
                evidence.get('cost_reduced') and all(review.get(k) is True for k in
                ('resource_reliable','delivery_passed','resource_used')) and review.get('evidence_refs') and
                len(review.get('case_findings', []))==len(evidence.get('cases', [])) and
                all(c.get('delivery')=='pass' for c in review.get('case_findings', []))):
                review['original_decision']='retain'
                review['decision']='defer'
                review['reason']='保留依据不齐，不能用模型口头结论覆盖缺少的实证。'+str(review.get('reason',''))
            route['value_review']=review
            if job['payload'].get('selection_repair'):
                route['selection_repair']['status']='complete'
                route['selection_repair']['outcome']=review['decision']
            route['performance']={'completed_pair_reduced':evidence.get('completed_pair_reduced',evidence.get('cost_reduced')),
                                  'all_attempts_reduced':evidence.get('cost_reduced'),
                                  'basis':'全部当前版本业务尝试，含失败；制作费用单列'}
            route['library_status']={'retain':'retained','revise':'needs_revision','reject':'rejected','defer':'candidate'}[review['decision']]
            route['make_status']={'retain':'保留：可靠且实际减负','revise':'待局部修正','reject':'不入库：无复用价值','defer':'候选：证据不足'}[review['decision']]
            self.state.route(route)
        self.state.job(job["id"], status="done", result=result, error=None)
        self.plan()

    def apply_routes(self, job, value):
        value = value if isinstance(value, (dict, list)) else {}
        rows = (value if isinstance(value, list) else value.get("routes")) or []
        rows = rows if isinstance(rows, list) else []
        known = {r["id"]: r for r in self.state.routes()}
        processed = set()
        for new in rows:
            if not isinstance(new, dict) or not new.get("id"):
                continue
            sid = safe(new.get("merge_into") or new["id"]).lower().replace('_', '-')[:64].strip('-') or 'workflow'
            source_ids = list(dict.fromkeys(s for s in new.get("source_ids", []) if s in self.bindings))
            old = known.get(sid)
            if old:
                if old.get('skill_root') and 'learning_source_ids' not in old:
                    old['learning_source_ids']=list(old.get('source_ids',[]))
                old["source_ids"] = sorted(set(old["source_ids"]) | set(source_ids))
                for field in ('conditions', 'conflicts'):
                    additions = new.get(field) or []
                    additions = additions if isinstance(additions, list) else [additions]
                    values = old.get(field) or []
                    values = values if isinstance(values, list) else [values]
                    for item in additions:
                        if item not in values:
                            values.append(item)
                    old[field] = values
                self.state.route(old)
            elif source_ids:
                route = {**new, "id": sid, "source_ids": source_ids, "lane": len(known) % 8,
                         "make_status": "待制作", "tasks": []}
                # Reserve one independent same-route source before making a new
                # package. Never retroactively pretend an old learned task is new.
                if len(source_ids)>1:
                    reserve=next((s for s in new.get('development_source_ids',[]) if s in source_ids),source_ids[-1])
                    route['development_source_ids']=[reserve]
                    route['learning_source_ids']=[s for s in source_ids if s!=reserve]
                self.state.route(route)
                known[sid] = route
            processed.update(source_ids)
        decisions = (value.get("decisions") or []) if isinstance(value, dict) else []
        decisions = decisions if isinstance(decisions, list) else []
        for item in decisions:
            if isinstance(item, dict) and item.get("source_id") in job["payload"]["source_ids"]:
                target = known.get(item.get('route_id'))
                if target and item.get('action') in ('new', 'reuse'):
                    if target.get('skill_root') and 'learning_source_ids' not in target:
                        target['learning_source_ids']=list(target.get('source_ids',[]))
                    target['source_ids'] = sorted(set(target.get('source_ids', [])) | {item['source_id']})
                    self.state.route(target)
                processed.add(item["source_id"])
        with self.state.connect() as db:
            db.executemany("UPDATE sources SET processed=1 WHERE id=?", [(sid,) for sid in processed])
        write(self.out / "records" / job["id"] / ("screen_attempt_" + str(job["attempt"]) + ".json"),
              {"processed_source_ids": sorted(processed), "model_output": value})
        return processed

    def settle(self, job, result):
        # A malformed model file belongs to this task, not to every other lane.
        try:
            self.finish(job, result)
        except Exception as error:
            message = '结果收尾失败：' + type(error).__name__ + ': ' + str(error)
            self.state.job(job['id'], status='failed', result=result, error=message)
            write(self.out / 'records' / job['id'] / ('attempt_' + str(job['attempt'])) / 'result.json', result)

    def repair_saved_gaps(self):
        """Reconnect saved outputs once, without another business/model execution."""
        if self.state.meta('saved_gaps_reconnected'):
            return
        archive = self.out / 'history/saved_gap_reconnection'
        archive.mkdir(parents=True, exist_ok=True)
        with self.state.connect() as source, sqlite3.connect(archive/'before.db') as backup:
            source.backup(backup)
        jobs = self.state.jobs()
        log = {'superseded_reviews':[], 'repackaged':[], 'reused_review_evidence':[], 'reading_corrections':[],
               'reviews_needing_evidence':[], 'failed_before':[j for j in jobs if j['status']=='failed']}
        # These queued empty reviews have not started a new attempt. Keep old
        # receipts/results; wait for actual cases and both business arms instead.
        for job in jobs:
            if job['kind']=='prepare' and job['status']=='pending' and not job['payload'].get('__adopt_episode'):
                self.state.job(job['id'],payload={**job['payload'],'full_catalog':True})
            if job['kind']!='review' or job['status']!='pending' or job['payload'].get('__adopt_episode'):
                continue
            result = job.get('result') or read(Path(job.get('episode') or '.')/'result.json', {})
            definitely_unstarted = job['attempt']==0 or (result and result.get('finished_at') and
                result.get('status') not in ('running','pending','unknown','dispatched_unresolved'))
            if definitely_unstarted:
                self.state.job(job['id'],status='superseded',error='原结果和费用保留；等待真实试用后合并缺失证据评审。')
                log['superseded_reviews'].append(job)
        for route in self.state.routes():
            sid = route['id']
            package_changed = False
            route_jobs = [j for j in jobs if j['route_id']==sid]
            # Do not swap a package under an in-flight or already queued actor.
            if route.get('skill_root') and not any(j['kind']=='actor' and j['status'] in WAITING_JOB_STATUSES for j in route_jobs):
                completed = []
                for job in route_jobs:
                    if job['kind']!='make' or not job.get('episode'):
                        continue
                    ep = Path(job['episode'])
                    result = job.get('result') or {}
                    if result.get('status')!='completed' or not result.get('finished_at'):
                        continue
                    if (output_json(ep,('making.json',)) or {}).get('no_reuse'):
                        continue
                    root = next((p for p in (ep/'workspace/outputs/skill',ep/'workspace/outputs/candidate/skill') if (p/'SKILL.md').is_file()),None)
                    if root:
                        completed.append((result['finished_at'],root))
                if completed:
                    source = max(completed,key=lambda x:x[0])[1]
                    before = self.review_key(route,[])
                    route['skill_root'] = self.publish(sid,source)
                    self.state.route(route)
                    if self.review_key(route,[])!=before:
                        package_changed = True
                        log['repackaged'].append({'route_id':sid,'source':str(source),'published':route['skill_root']})
            # Keep a completed, sufficiently informed old review. Only the
            # proven missing evidence (or new cases/results) calls for review.
            reviews = [j for j in route_jobs if j['kind']=='review' and j['status']=='done' and j.get('episode')]
            if not reviews or not route.get('skill_root'):
                continue
            last = reviews[-1]
            original = read(self.out/'records'/last['id']/('attempt_'+str(last['attempt']))/'input/review_input.json',{})
            review = output_json(last['episode'],('review.json',)) or {}
            active = [c for c in route.get('tasks',[]) if c.get('value_revision_of')] or route.get('tasks',[])
            same_cases = bool(active) and [c.get('id') for c in active]==[c.get('case',{}).get('id') for c in original.get('cases',[])]
            same_business = same_cases
            for index,case in enumerate(active):
                for arm in ('no_skill','workflow'):
                    job = next((j for j in route_jobs if j['kind']=='actor' and j['case_id']==case.get('id') and j['arm']==arm),{})
                    result = job.get('result') or {}; usage = result.get('usage') or {}
                    old_arm = original.get('cases',[])[index].get('arms',{}).get(arm,{}) if same_cases else {}
                    if (result.get('tokens',usage.get('total_tokens')),result.get('calls',usage.get('model_calls'))) != (old_arm.get('tokens'),old_arm.get('calls')):
                        same_business = False
                    saved_response = Path(last['episode'])/f'workspace/inputs/cases/{index+1}/{arm}/response.json'
                    current_response = Path(job.get('episode') or '.')/'response.json'
                    if saved_response.is_file() and current_response.is_file() and saved_response.read_bytes()!=current_response.read_bytes():
                        same_business = False
            saved_package = Path(last['episode'])/'workspace/inputs/candidate'
            def contents(root):
                return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
            same_package = saved_package.is_dir() and contents(saved_package)==contents(Path(route['skill_root']))
            all_finished = not any(j['kind'] in ('make','prepare','actor') and j['status'] in WAITING_JOB_STATUSES for j in route_jobs)
            has_samples = any(any(p.is_file() for p in (Path(j['episode'])/'workspace/outputs/making_samples').rglob('*'))
                for j in route_jobs if j['kind']=='make' and j.get('episode'))
            missing_making = has_samples and not original.get('making_attempts') and review.get('resource_reliable') is not True
            missing_read = False
            if review.get('resource_used') is False:
                for job in route_jobs:
                    if job['kind']!='actor' or job['arm']!='workflow' or not job.get('episode'):
                        continue
                    observed = stages.saved_evidence.read_usage_evidence(Path(job['episode'])/'openclaw_transport/session_events.jsonl')['summary']
                    if observed['read_successes'] and (observed['exec_tool_successes'] or observed['copy_resource_attempts']):
                        missing_read = True
                        correction = stages.saved_evidence.build_read_usage_evidence(job['episode'],archive/'read_observations'/job['id'])
                        log['reading_corrections'].append({'route_id':sid,'job_id':job['id'],
                            'observation':correction['resource']['path'],'note':'仅更正原始读取/调用事实，不升级收益或交付结论。'})
            # The current legacy set with genuinely omitted production evidence
            # has either no case or a stale case list. Keep sufficient old
            # reviews, including negative outcomes, without another paid call.
            if same_business and same_package and all_finished and not package_changed:
                reused = self.state.meta('review_evidence_reused') or {}
                reused[sid] = self.review_key(route,[j for j in route_jobs if j['kind']!='review'])
                self.state.meta('review_evidence_reused',reused)
                log['reused_review_evidence'].append({'route_id':sid,'review_job':last['id']})
            elif active:
                log['reviews_needing_evidence'].append({'route_id':sid,'same_cases':same_cases,
                    'missing_making':missing_making,'missing_read':missing_read})
        write(archive/'reconnection.json',log)
        self.state.meta('saved_gaps_reconnected',{'at':datetime.now().astimezone().isoformat(),
            **{k:len(log[k]) for k in ('superseded_reviews','repackaged','reused_review_evidence','reviews_needing_evidence')}})

    def recover(self):
        self.rejoin_finished_unknown()
        for job in self.state.jobs():
            if (job['status'] == 'failed' and (job.get('result') or {}).get('status') == 'completed'
                    and str(job.get('error', '')).startswith('结果收尾失败')):
                # The model has finished. A local copy/JSON/queue error must
                # resume its saved output, never start another paid attempt.
                self.settle(job, job['result'])
                continue
            if job['status'] == 'failed' and (job.get('result') or {}).get('dispatch_state') == 'not_started':
                # No container/model was launched. A later resume may safely
                # retry after Docker access returns, retaining the old failure.
                self.state.job(job['id'], status='pending', error='原生容器尚未启动，上次失败保留；本次继续。')
                continue
            if job["status"] != "running":
                continue
            saved = read(Path(job["episode"]) / "result.json")
            if saved:
                self.settle(job, saved)
            else:
                # Rejoin this exact consumer/result; never allocate a fresh attempt.
                if (Path(job['episode']) / 'dispatch.json').is_file():
                    payload = dict(job['payload']); payload['__adopt_episode'] = job['episode']
                    self.state.job(job['id'], status='pending', payload=payload,
                                   error='接回原生进程或已写回复，不重新发模型。')
                else:
                    self.state.job(job['id'], status='pending', error='上次尚未派发，继续原任务。')

    def rejoin_finished_unknown(self):
        for job in self.state.jobs():
            if job['status'] != 'unknown' or not job.get('episode'):
                continue
            episode = Path(job['episode'])
            process = read(episode / 'process.json', {})
            if ((episode / 'dispatch.json').is_file() and process and
                native._process_state(process) == 'exited' and (episode / 'response.json').is_file()):
                payload = dict(job['payload']); payload['__adopt_episode'] = job['episode']
                self.state.job(job['id'], status='pending', payload=payload,
                               error='原生会话已收尾，接回同一回复，不重发模型。')

    def reserved_lanes(self):
        return {job['lane'] for job in self.state.jobs() if job['status'] == 'unknown' and job.get('episode')
                and native._process_state(read(Path(job['episode']) / 'process.json', {})) == 'running'}

    def retry_terminal_service_failure(self, job, result):
        """One bounded recovery only after a provider transport and native exit."""
        if job.get('payload',{}).get('__excluded_condition'):
            return False
        if self.service_pool is None:
            return False
        if result.get('status')!='failed' or not result.get('finished_at'):
            return False
        ep = Path(job['episode'])
        process = read(ep/'process.json',{})
        host = read(ep/'openclaw_transport/host_receipt.json',{})
        if (native._process_state(process)!='exited' or host.get('status')!='failed' or
                host.get('cleanup_returncode')!=0 or host.get('cleanup_error')):
            return False
        services = (self.service_state or {}).get('services',[])
        row = next((r for r in services if r['lane']==job['lane']),{})
        log = ep/'openclaw_transport/gateway.stderr.log'
        text = ''
        if log.is_file():
            with log.open('rb') as stream:
                stream.seek(max(0,log.stat().st_size-12000))
                text = stream.read().decode('utf-8',errors='replace')
        if 'embedded run timeout' in text or 'Request timed out before a response' in text:
            return False  # An exhausted unchanged business budget is not a transport retry.
        startup_failure = 'codebuddy startup timed out' in text
        refused = (row.get('port') and 'ECONNREFUSED' in text and
                   re.search(r'127\.0\.0\.1:'+str(int(row['port']))+r'(?!\d)',text))
        if not (startup_failure or refused):
            return False
        health = row.get('health',{})
        if not health.get('backend_ready'):
            return False
        generation = str((row.get('pid'),row.get('birth'),health.get('backend_pid')))
        if job['payload'].get('__service_transport_retry_generation') == generation:
            return False
        current = self.state.job(job['id'])
        if current['status']!='failed' or current['attempt']!=job['attempt']:
            return False
        # Receipt/result remain at their original attempt. Never clear a claim.
        write(self.out/'records'/job['id']/('attempt_'+str(job['attempt']))/'service_recovery.json',
              {'at':datetime.now().astimezone().isoformat(),'job_before':current,
               'reason':'后端启动/连接故障终态确认且后端已预热；同后端代次不重复恢复。', 'backend_generation':generation})
        payload = {**current['payload'],'__service_transport_retry':True,'__service_transport_retry_generation':generation,
                   'previous_failed_episode':str(ep)}
        payload.pop('__adopt_episode',None)
        if job['kind']=='make':
            payload['previous'] = {**payload.get('previous',{}),'failed_episode':str(ep)}
        self.state.job(job['id'],status='pending',payload=payload,
                       error='服务故障终态已确认；保留失败和费用，服务恢复后接续一次。')
        return True

    def ledger_totals(self, jobs):
        """Read unchanged paid-result files once; still include every attempt."""
        if not hasattr(self,'_ledger_paths'):
            self._ledger_paths=set((self.out/'records').glob('*/attempt_*/result.json'))
            self._ledger_cache={}
        for job in jobs:
            for attempt in range(1,int(job.get('attempt') or 0)+1):
                self._ledger_paths.add(self.out/'records'/job['id']/f'attempt_{attempt}'/'result.json')
        def stamp(path):
            try:
                st=path.stat();return st.st_mtime_ns,st.st_size
            except OSError:return None
        totals={'known_tokens':0,'model_calls':0,'unknown_calls':0}
        fields=('total_tokens','known_total_tokens','model_calls','known_model_calls',
                'unknown_usage_calls','unknown_calls','errors')
        for path in self._ledger_paths:
            item=self._ledger_cache.get(path);current=stamp(path)
            if current and (not item or item['stamp']!=current):
                result=read(path)
                if isinstance(result,dict):
                    item={'stamp':current,'value':{'episode_dir':result.get('episode_dir') or result.get('episode'),
                        'usage':{k:v for k,v in (result.get('usage') or {}).items() if k in fields}}}
                    self._ledger_cache[path]=item
            if not item:continue
            ep=item['value'].get('episode_dir')
            receipt=stamp(Path(ep)/'usage_supplement.json') if ep else None
            raw=stamp(Path(ep)/'native_events.jsonl') if receipt else None
            signature=(item['stamp'],receipt,raw)
            if item.get('usage_signature')!=signature:
                item['usage']=continuation.supplement(item['value']);item['usage_signature']=signature
            usage=item['usage']
            totals['known_tokens']+=usage.get('total_tokens') or usage.get('known_total_tokens') or 0
            totals['model_calls']+=usage.get('model_calls') or usage.get('known_model_calls') or 0
            totals['unknown_calls']+=usage.get('unknown_usage_calls',usage.get('unknown_calls')) or int(bool(usage.get('errors')))
        return totals

    def refresh(self, status, message=""):
        routes, jobs = self.state.routes(), self.state.jobs()
        jobs_by_id = {j['id']:j for j in jobs}
        new_cost = self.ledger_totals(jobs)
        for route in routes:
            route["comparison"] = []
            for index, case in enumerate(route.get("tasks", [])):
                cid = str(case.get("id", "c" + str(index + 1)))
                row = {"case_id": cid}
                for arm in ("no_skill", "workflow"):
                    key = "__".join(safe(p) for p in ("actor", route["id"], cid, arm))
                    entry = jobs_by_id.get(key)
                    result = entry.get("result") if entry else None
                    if result:
                        usage = result.get("usage", {})
                        row[arm] = {"tokens": result.get("tokens", usage.get("total_tokens")),
                                    "calls": result.get("calls", usage.get("model_calls")),
                                    "status": result.get("delivery_status") or result.get("status"),
                                    "outputs": result.get("outputs", str(Path(entry["episode"] or ".") / "workspace/outputs"))}
                    else:
                        row[arm] = None
                route["comparison"].append(row)
            route["task_count"] = len(route.get("tasks", []))
        from research.workflow.selection_status import enrich
        campaign = self.state.meta('selection_repair') or {}
        campaign['source_job_ids'] = [j['id'] for j in jobs if j['kind']=='screen' and
            j['payload'].get('recovery',{}).get('continuation_type')=='old_constraint_recheck']
        selection = enrich(routes,jobs,self.out/'records',campaign)
        with self.state.connect() as db:
            total, screened = db.execute("SELECT count(*),coalesce(sum(processed),0) FROM sources").fetchone()
        owner = self.state.meta('owner') or {}
        actual_alive = bool(owner.get('pid') and alive(owner['pid'], owner.get('birth')))
        legacy_cost = self.state.meta('legacy_usage') or {}
        if legacy_cost and not (self.out / 'legacy_costs.json').is_file():
            write(self.out / 'legacy_costs.json', legacy_cost)
        snapshot = {"updated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
                    "runner": {"pid": owner.get('pid'), "alive": actual_alive, "status": status, "message": message},
                    "workers": self.config["workers"], "conversations": {"total": total, "screened": screened, "remaining": total - screened},
                    "routes": routes, "jobs": [{k: j[k] for k in ("id", "kind", "route_id", "status", "lane", "episode", "error")} for j in jobs],
                    "costs": {"legacy": {k:legacy_cost.get(k) for k in ('known_tokens','model_calls','unknown_calls')}, "new": new_cost},
                    "counts": {"generated": sum(bool(r.get("skill_root")) for r in routes),
                               "published": sum(r.get('library_status') == 'retained' for r in routes),
                               **{name: sum(j["status"] == value for j in jobs) for name, value in
                                  [("failed", "failed"), ("unknown", "unknown"), ("active", "running"), ("pending", "pending")]}}}
        snapshot['legacy_continuation'] = self.state.meta('legacy_routes_recovered') or {}
        snapshot['selection_repair'] = selection
        snapshot['services'] = self.service_state or read(self.out/'services/current.json',{})
        try:
            view.write_view(self.out, snapshot)
            write(self.out / "routes.json", routes)
            old_page = Path(self.config["legacy_output"]) / "实时进度_完整用量.html"
            if old_page.parent.is_dir():
                archive = self.out / "history/legacy_progress_before.html"
                if not archive.exists() and old_page.is_file():
                    archive.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(old_page, archive)
                if (self.out / "progress.html").is_file():
                    shutil.copy2(self.out / "progress.html", old_page)
        except OSError as error:
            print('进度展示写入失败，业务继续：' + str(error), file=sys.stderr)
        return snapshot

    def allocate_unstarted_pairs(self, jobs, occupied, ready_lanes):
        free = set(ready_lanes) - set(occupied) - {self.config.get('auxiliary_lane')}
        unknown_routes = {j['route_id'] for j in jobs if j['status']=='unknown'}
        pairs = {}
        for j in jobs:
            if j['kind']=='actor':
                pairs.setdefault((j['route_id'],j['case_id']),[]).append(j)
        changed = False
        for (rid,cid), pair in pairs.items():
            if (rid in unknown_routes or len(pair)!=2 or {j['arm'] for j in pair}!={'no_skill','workflow'}
                    or any(j['status']!='pending' or j['attempt'] or j.get('episode') or j.get('result') for j in pair)
                    or pair[0]['payload'].get('case')!=pair[1]['payload'].get('case')):
                continue
            original = pair[0]['lane']
            route = next((r for r in self.state.routes() if r['id']==rid),None)
            case = pair[0]['payload'].get('case',{})
            if case.get('value_revision_of') or (route and any(j['kind']=='actor' and
                    j['route_id']==rid and j['arm']=='no_skill' and j['status']=='done' for j in jobs)
                    and self.reusable_baseline(route,case,jobs)):
                continue
            if original not in occupied or not free:
                continue
            target = min(free)
            with self.state.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                current = [self.state.decode_job(row) for row in db.execute(
                    "SELECT * FROM jobs WHERE id IN (?,?)",(pair[0]['id'],pair[1]['id']))]
                if any(j['status']!='pending' or j['attempt'] or j.get('episode') or j.get('result') for j in current):
                    continue
                for j in current:
                    payload = {**j['payload'], '__original_lane':original,
                        '__paired_idle_allocation':{'case_id':cid,'from':original,'to':target,
                            'authorization':'2026-10-24用户允许未派发完整案例对整体换闲置业务通道'}}
                    db.execute('UPDATE jobs SET lane=?,payload=? WHERE id=?',
                        (target,json.dumps(payload,ensure_ascii=False),j['id']))
            free.remove(target)
            if route:
                for case in route.get('tasks',[]):
                    if case['id']==cid:
                        case['native_lane']=target
                        case['_paired_idle_allocation']=payload['__paired_idle_allocation']
                self.state.route(route)
            changed = True
        return changed

    def resume(self, limit=None):
        with self.state.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT value FROM meta WHERE key='owner'").fetchone()
            owner = json.loads(row[0]) if row else {}
            if owner.get('pid') and alive(owner['pid'], owner.get('birth')):
                raise RuntimeError('已有运行进程 PID '+str(owner['pid'])+'；没有开第二条管道。')
            db.execute("INSERT OR REPLACE INTO meta VALUES('owner',?)", (json.dumps(
                {'pid':os.getpid(),'birth':psutil.Process().create_time()}),))
        self.state.meta("stop", False)
        running, count, last_view, blocked = {}, 0, 0, ""
        try:
            if self.service_pool is not None:
                self.service_state = {'checked_at':datetime.now().astimezone().isoformat(),
                    'services':[],'ready_count':0,'message':'正在由原Windows任务启动模型服务，未派发业务。'}
                self.refresh('正在启动原模型服务','同一个Windows任务托管；未派发业务。')
                busy = {j['lane'] for j in self.state.jobs() if j['status'] in ('running','unknown') or
                        (j['status']=='pending' and j['payload'].get('__adopt_episode'))}
                self.service_state = self.service_pool.startup(busy)
            self.repair_saved_gaps()
            self.recover()
            self.recover_legacy_routes()
            self.plan()
            with ThreadPoolExecutor(max_workers=self.config["workers"]) as pool:
                while True:
                    # Native containers may still be cleaning up after their
                    # actor budget ends. Keep that lane occupied and consume
                    # its eventual reply without another model request.
                    self.rejoin_finished_unknown()
                    reserved = self.reserved_lanes()
                    jobs = self.state.jobs()
                    if self.service_pool is not None:
                        busy = {j['lane'] for j in jobs if j['status'] in ('running','unknown') or
                                (j['status']=='pending' and j['payload'].get('__adopt_episode'))}
                        self.service_state = self.service_pool.tick(busy)
                    if not blocked and not self.state.meta("stop"):
                        for failed in jobs:
                            if (route_in_scope(self.config, failed['route_id'])
                                    and failed['status']=='failed' and failed.get('episode')):
                                self.retry_terminal_service_failure(failed,failed.get('result') or {})
                        jobs = self.state.jobs()
                        occupied = {j["lane"] for j in running.values()} | reserved
                        ready_lanes = self.service_pool.ready_lanes if self.service_pool else set(range(self.config['workers']))
                        if self.allocate_unstarted_pairs(jobs, occupied, ready_lanes):
                            jobs = self.state.jobs()
                        active_route_jobs = list(running.values()) + [j for j in jobs if j['status']=='unknown']
                        business_waiting = {j['lane'] for j in jobs if j['kind']=='actor'
                            and j['status']=='pending' and route_in_scope(self.config,j['route_id'])}
                        for job in sorted(jobs, key=lambda j: (j['kind'] != 'actor', j['kind'] != 'screen')):
                            if (not route_in_scope(self.config, job['route_id'])
                                    or job["status"] != "pending" or route_dispatch_blocked(job, active_route_jobs)
                                    or len(occupied) >= self.config["workers"]):
                                continue
                            selected_lane = dispatch_lane(job, occupied, self.config, ready_lanes, business_waiting)
                            if selected_lane is None:
                                continue
                            if limit is not None and count >= limit:
                                break
                            adopted = job['payload'].get('__adopt_episode')
                            if not adopted and self.service_pool is not None and not self.service_pool.can_dispatch(selected_lane):
                                continue
                            if self.state.meta('stop'):
                                break
                            attempt = job["attempt"] if adopted else job["attempt"] + 1
                            run_root = self.out/'prepare_runs' if job['kind']=='prepare' else Path(self.config['run_root'])
                            episode = Path(adopted) if adopted else episode_path(run_root, job["id"], attempt)
                            payload = job['payload']
                            if selected_lane != job['lane']:
                                payload = {**payload, '__original_lane':job['lane'],
                                           '__auxiliary_dispatch':'idle_equivalent_generation_channel'}
                            self.state.job(job["id"], status="running", attempt=attempt, episode=str(episode),
                                           lane=selected_lane, payload=payload, error=None)
                            current = self.state.job(job["id"])
                            running[pool.submit(self.execute, current)] = current
                            occupied.add(selected_lane)
                            active_route_jobs.append(current)
                            count += 1
                    if time.monotonic()-getattr(self,'_last_continuation_tick',0)>30 and not self.state.meta('stop'):
                        self._last_continuation_tick=time.monotonic()
                        self.plan()
                    if not running and not reserved:
                        waiting = (not blocked and not self.state.meta('stop') and
                                   (limit is None or count<limit) and
                                   any(j['status']=='pending' and route_in_scope(self.config,j['route_id'])
                                       for j in self.state.jobs()))
                        if not waiting or self.service_pool is None:
                            break
                    if not running:
                        time.sleep(1)
                    ready, _ = wait(running, timeout=1, return_when=FIRST_COMPLETED) if running else (set(), set())
                    for future in ready:
                        job = running.pop(future)
                        result = future.result()
                        if result.get('status')=='deferred_service' and not (Path(job['episode'])/'dispatch.json').exists():
                            write(self.out/'records'/job['id']/('attempt_'+str(job['attempt']))/'result.json',result)
                            self.state.job(job['id'],status='pending',result=result,error=result['error'])
                            continue
                        self.settle(job, result)
                        self.retry_terminal_service_failure(job,result)
                        error = str(result.get("error", "")) + json.dumps(result.get("response") or {}, ensure_ascii=False)
                        log = Path(job['episode']) / 'stderr.log'
                        if log.is_file():
                            error += log.read_text(encoding='utf-8',errors='replace')[-5000:]
                        if result.get("status") != "completed" and any(s in error.casefold() for s in
                                ("permission", "access is denied", "access denied", "拒绝访问", "dockerdesktoplinuxengine", "cannot connect to the docker", "error during connect", "['docker', 'image', 'inspect'")):
                            blocked = "Docker或运行目录访问被拒；原错误已保存，未切换执行器。"
                    if time.time() - last_view > 4:
                        service_message = (self.service_state or {}).get('message','')
                        self.refresh("模型通道恢复中" if self.service_pool is not None and (self.service_state or {}).get('healthy_count',0)<len(self.service_pool.rows) else "运行中",
                                     blocked or service_message)
                        last_view = time.time()
        except KeyboardInterrupt:
            self.state.meta("stop", True)
            raise
        except Exception as error:
            blocked = '外层调度/服务异常：'+type(error).__name__+': '+str(error)
            raise
        finally:
            if self.service_pool is not None:
                busy = any(j['status'] in ('running','unknown') or
                           (j['status']=='pending' and j['payload'].get('__adopt_episode'))
                           for j in self.state.jobs())
                self.service_pool.close(stop_owned=not busy)
            self.state.meta("owner", {})
            self.state.meta('last_run', {'status':'受运行环境阻断' if blocked else '本次运行已结束',
                                        'message':blocked or '已有结果保留；resume继续尚未完成的工作。'})
            snapshot = self.refresh("受运行环境阻断" if blocked else "本次运行已结束", blocked or "已有结果保留；resume继续尚未完成的工作。")
        print(json.dumps({"status": snapshot["runner"]["status"], "started_jobs": count,
                          "counts": snapshot["counts"], "progress": str(self.out / "progress.html")}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="唯一工作流管道：会话→技能→业务对照")
    parser.add_argument("command", choices=["init", "resume", "status", "stop", "retry", "complete-coverage", "coverage-status", "repair-selection"], nargs="?", default="status")
    parser.add_argument("job", nargs="?")
    parser.add_argument("--config", default=str(ROOT / "pipeline.json"))
    parser.add_argument("--workers", type=int)
    parser.add_argument("--run-root")
    parser.add_argument("--limit", type=int, help="只启动指定数量任务，便于首次接线")
    args = parser.parse_args()
    config = read(args.config)
    if not config:
        parser.error("没有找到pipeline.json")
    config["workers"] = max(1, min(9, args.workers or config.get("workers", 8)))
    if args.run_root:
        config["run_root"] = str(Path(args.run_root).resolve())
    app = Pipeline(config)
    if args.command in ('complete-coverage', 'coverage-status'):
        from research.workflow import coverage
        result = coverage.prepare(app) if args.command == 'complete-coverage' else coverage.status(app)
        print(json.dumps(result, ensure_ascii=False))
        return
    if args.command == "stop":
        app.state.meta("stop", True)
        print("已停止新派发；在途原生会话按原预算结束。")
        return
    app.initialize()
    if args.command == 'repair-selection':
        if not args.job:
            parser.error('请给出补接计划JSON路径')
        print(json.dumps(app.repair_selection(args.job),ensure_ascii=False))
        return
    if args.command == "resume":
        owner = app.state.meta('owner') or {}
        if owner.get('pid') and alive(owner['pid'], owner.get('birth')):
            raise RuntimeError('已有运行进程 PID ' + str(owner['pid']) + '；不重复启动服务或任务。')
        from research.workflow import services
        host_policy = services._launch_policy()
        if os.name=='nt' and (host_policy['mode']!='same_windows_task' or not host_policy['allowed']):
            if Path(args.config).resolve()!=(ROOT/'pipeline.json').resolve() or args.run_root or args.limit is not None or config['workers']!=read(ROOT/'pipeline.json').get('workers',8):
                raise RuntimeError('自定义接续参数须由独立Windows任务托管；未在临时工具宿主启动服务。')
            subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-WindowStyle','Hidden',
                            '-Command',"Start-ScheduledTask -TaskName 'SkillLoop_SinglePipeline'"],check=True)
            print('已交给原Windows任务独立续跑；实时进度：'+str(app.out/'progress.html'))
            return
        app.service_pool = services.ServicePool(config)
        app.resume(args.limit)
    elif args.command == "retry":
        job = app.state.job(args.job)
        if not job or job["status"] not in ("failed", "unknown"):
            parser.error("只为失败或不明任务创建下一次独立尝试；请先查看status。")
        if job["status"] == "unknown":
            parser.error("原生会话状态不明，不能自动重复计费；先确认原进程已结束。")
        app.state.job(args.job, status="pending", error=None)
        print("已保留旧尝试并排入下一次运行：" + args.job)
    else:
        owner = app.state.meta("owner") or {}
        running = bool(owner.get("pid") and alive(owner["pid"], owner.get("birth")))
        last = app.state.meta('last_run') or {}
        snapshot = app.refresh("运行中" if running else last.get('status', '未运行'),
                               "正在接续未完成工作，无需重复启动。" if running else last.get('message', '用python pipeline.py resume续跑。'))
        print(json.dumps({"runner": snapshot["runner"], "conversations": snapshot["conversations"],
                          "counts": snapshot["counts"], "costs": snapshot["costs"], "progress": str(app.out / "progress.html")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
