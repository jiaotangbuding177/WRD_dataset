"""Keep the configured native model channels under the single pipeline's lifetime.

No completion probes, replacement agent, new watchdog or business retries.
Busy/unknown native lanes must settle before a lost service is restarted.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.request import build_opener, ProxyHandler, Request

import psutil


def _now():
    return datetime.now().astimezone().isoformat()


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def _norm(value):
    return str(value).replace('\\', '/').casefold()


def _write(path, value):
    temporary = path.with_name(path.name + '.' + str(os.getpid()) + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def _ancestors(process):
    try:
        chain = [process] + process.parents()
    except psutil.Error:
        chain = [process]
    rows = []
    for item in chain[:12]:
        try:
            rows.append({'pid': item.pid, 'birth': item.create_time(),
                         'name': item.name(), 'command': item.cmdline()})
        except psutil.Error:
            rows.append({'pid': item.pid, 'identity': 'unavailable'})
    return rows


def _codex_host(chain):
    return any('codex' in _norm(row.get('name', '')) or
               any('openai.codex' in _norm(arg) or '/codex.exe' in _norm(arg)
                   for arg in row.get('command', [])) for row in chain)


def windows_job_state(process=None):
    """A child can be in an outer Job after escaping one nested Job.

    Query only facts available to this process. IsProcessInJob(child, NULL)
    does not disclose the child's Job limits or prove independent ownership.
    """
    if os.name != 'nt':
        return {'platform': os.name, 'in_job': False, 'limits_known': True}
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
    kernel.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
        wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    owned = None
    try:
        if process is None:
            handle = kernel.GetCurrentProcess()
        else:
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            owned = kernel.OpenProcess(0x1000, False, int(process))
            if not owned:
                return {'in_job': None, 'limits_known': False, 'error': ctypes.get_last_error()}
            handle = owned
        inside = wintypes.BOOL()
        if not kernel.IsProcessInJob(handle, None, ctypes.byref(inside)):
            return {'in_job': None, 'limits_known': False, 'error': ctypes.get_last_error()}
        result = {'in_job': bool(inside.value), 'limits_known': not bool(inside.value)}
        if not inside.value or process is not None:
            return result
        class BASIC(ctypes.Structure):
            _fields_ = [('ProcessTime', ctypes.c_longlong), ('JobTime', ctypes.c_longlong),
                ('LimitFlags', wintypes.DWORD), ('MinWorking', ctypes.c_size_t),
                ('MaxWorking', ctypes.c_size_t), ('ActiveLimit', wintypes.DWORD),
                ('Affinity', ctypes.c_size_t), ('Priority', wintypes.DWORD),
                ('Scheduling', wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in
                ('ReadOps', 'WriteOps', 'OtherOps', 'ReadBytes', 'WriteBytes', 'OtherBytes')]
        class EXTENDED(ctypes.Structure):
            _fields_ = [('Basic', BASIC), ('Io', IO), ('ProcessMemory', ctypes.c_size_t),
                ('JobMemory', ctypes.c_size_t), ('PeakProcessMemory', ctypes.c_size_t),
                ('PeakJobMemory', ctypes.c_size_t)]
        info = EXTENDED()
        if kernel.QueryInformationJobObject(None, 9, ctypes.byref(info), ctypes.sizeof(info), None):
            flags = int(info.Basic.LimitFlags)
            result.update(limits_known=True, limit_flags=flags,
                kill_on_job_close=bool(flags & 0x2000),
                breakaway_allowed=bool(flags & (0x800 | 0x1000)),
                silent_breakaway=bool(flags & 0x1000))
        else:
            result['error'] = ctypes.get_last_error()
        return result
    finally:
        if owned:
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle(owned)


def _launch_policy():
    chain = _ancestors(psutil.Process())
    job = windows_job_state()
    codex = _codex_host(chain)
    scheduler = any(_norm(row.get('name', '')) in ('taskeng.exe', 'taskhostw.exe') or
        (_norm(row.get('name', '')) == 'svchost.exe' and
         any('schedule' in _norm(a) for a in row.get('command', []))) for row in chain)
    marker = os.environ.get('SKILLLOOP_OS_TASK') == 'SkillLoop_SinglePipeline'
    # Never present escaping one nested tool Job as a durable independent host.
    allowed = not codex and (scheduler or marker or job.get('in_job') is False)
    mode = ('same_windows_task' if scheduler or marker else 'uncontained_pipeline') if allowed else 'temporary_host_refused'
    return {'allowed': allowed, 'mode': mode,
            'job': job, 'ancestors': chain, 'task': 'SkillLoop_SinglePipeline' if scheduler or marker else None,
            'reason': None if allowed else
            '临时/未知宿主不能托管生产服务；请从原SkillLoop_SinglePipeline Windows任务启动。'}


class ServicePool:
    def __init__(self, config):
        from . import native
        self.config, self.native = config, native
        self.out = Path(config['output']) / 'services'
        self.out.mkdir(parents=True, exist_ok=True)
        self.lanes = _read(config['lanes_file'])
        self.rows, self.handles, self.identities = {}, {}, {}
        self.futures, self.health, self.next_start, self.failures = {}, {}, {}, {}
        self.identity_cache, self.catalog_checked = {}, set()
        self.closed = False
        self.executor = ThreadPoolExecutor(max_workers=min(3,len(self.lanes)), thread_name_prefix='service-readiness')
        self.opener = build_opener(ProxyHandler({}))
        self.policy = _launch_policy()
        self._last_disk, self._last_heartbeat = None, 0
        self._last_tick, self._last_snapshot, self._last_active = 0, None, None
        self.ready_lanes = set()
        for lane in self.lanes:
            old = _read(lane['service_receipt']['path'])
            profile = _read(lane['profile']['path'])
            entry, event = Path(old['entrypoint']), Path(profile['event_file'])
            self.rows[int(lane['id'])] = {'lane': int(lane['id']), 'port': int(lane['port']),
                'node': old['node'], 'entrypoint': str(entry), 'event_file': str(event),
                'service_dir': str(entry.parent.parent), 'status': 'unchecked',
                'pid': None, 'birth': None, 'exit_code': None, 'launch_mode': None}

    def _event(self, name, row=None, **extra):
        value = {'at': _now(), 'event': name, 'supervisor_pid': os.getpid(),
                 'supervisor_birth': psutil.Process().create_time()}
        if row is not None:
            value.update({k: row.get(k) for k in
                          ('lane', 'port', 'pid', 'birth', 'entrypoint', 'launch_mode')})
        value.update(extra)
        with (self.out / 'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(value, ensure_ascii=False) + '\n')

    def _owners(self):
        return {c.laddr.port: c.pid for c in psutil.net_connections(kind='tcp')
                if c.status == 'LISTEN' and c.laddr}

    def _identity(self, pid, row):
        try:
            process = psutil.Process(pid)
            birth = process.create_time()
            key = (pid, birth, _norm(row['entrypoint']), _norm(row['node']))
            if key in self.identity_cache:
                return self.identity_cache[key]
            command = process.cmdline()
            correct = (any(_norm(arg) == _norm(row['entrypoint']) for arg in command)
                       and _norm(process.exe()) == _norm(row['node']))
            result = {'pid': pid, 'birth': birth, 'matches': correct,
                    'command': command, 'ancestors': _ancestors(process),
                    'process_job': windows_job_state(pid)}
            self.identity_cache[key] = result
            return result
        except psutil.Error as error:
            return {'pid': pid, 'matches': False, 'error': type(error).__name__}

    def _probe(self, row, catalog=False, warm=False):
        try:
            if catalog:
                with self.opener.open(f"http://127.0.0.1:{row['port']}/v1/models", timeout=30) as response:
                    value = json.load(response)
                if not any(v.get('id') == self.native.MODEL for v in value.get('data', [])):
                    return {'ok':False,'error':'original model missing'}
            if warm:
                request = Request(f"http://127.0.0.1:{row['port']}/internal/backend-ready",
                    data=b'{}',headers={'Content-Type':'application/json'},method='POST')
                with self.opener.open(request,timeout=310) as response:
                    value = json.load(response)
                ok = value.get('ready') is True and value.get('inference_requests') == 0
                return {'ok':ok,'backend_ready':ok,'backend_warmed_monotonic':time.monotonic(),
                    'at':_now(),'method':'POST backend-ready','inference_requests':0,'backend_pid':value.get('backend_pid'),
                    'meaning':'后端进程预热与TCP就绪，无ACP会话、无推理请求'}
            request = Request(f"http://127.0.0.1:{row['port']}/", method='OPTIONS')
            with self.opener.open(request, timeout=3) as response:
                ok = response.status == 204
            return {'ok': ok, 'at': _now(), 'method': 'OPTIONS',
                    'meaning': 'HTTP早期204存活回复，未进入模型路由或启动后台模型'}
        except Exception as error:
            return {'ok': False, 'at': _now(), 'error': type(error).__name__ + ': ' + str(error),
                    **({'backend_ready':False,'backend_warmed_monotonic':0} if warm else {})}

    def _mark_exit(self, lane, row, reason):
        handle = self.handles.get(lane)
        code = handle.poll() if handle else None
        self._event('service_exited', row, exit_code=code,
                    exit_code_known=code is not None, reason=reason)
        row.update(last_exit_at=_now(), last_exit_pid=row.get('pid'),
                   last_exit_birth=row.get('birth'), exit_code=code,
                   exit_code_known=code is not None)
        self.identities.pop(lane, None)
        self.handles.pop(lane, None)
        self.health.pop(lane, None)
        self.failures[lane] = self.failures.get(lane, 0) + 1
        self.next_start[lane] = time.monotonic() + min(30, 2 ** min(self.failures[lane] - 1, 5))
        row['pid'], row['birth'] = None, None

    def _launch(self, lane, row):
        if not self.policy['allowed']:
            row.update(status='launch_blocked', error=self.policy['reason'], launch_mode=self.policy['mode'])
            return
        event, service = Path(row['event_file']), Path(row['service_dir'])
        env = dict(os.environ)
        env.pop('GATEWAY_URL', None)
        env.update(HOST='127.0.0.1', PORT=str(row['port']),
                   BUDDY2API_STATE_DIR=str(event.parent / 'service_state'),
                   BUDDY2API_ACCOUNTS_DIR='C:/Users/22142/AppData/Local/Programs/buddy2api/data/accounts',
                   CODEBUDDY_CLI_PATH=str(service / 'vendor/codebuddy-cli/bin/codebuddy'),
                   WORKFLOW_NATIVE_METER_FILE=str(event),
                   TOKEN_STATS_FILE=str(event.parent / 'interface_usage.jsonl'),
                   NATIVE_FAILURE_WIRE=str(event.parent / 'failure_wire.jsonl'))
        try:
            with (self.out / f'{lane}.stdout.log').open('ab') as stdout, (self.out / f'{lane}.stderr.log').open('ab') as stderr:
                handle = subprocess.Popen([row['node'], row['entrypoint']], cwd=service, env=env,
                    stdout=stdout, stderr=stderr,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            self.handles[lane] = handle
            identity = self._identity(handle.pid, row)
            if not identity.get('birth'):
                try:
                    identity['birth'] = psutil.Process(handle.pid).create_time()
                except psutil.Error:
                    identity['birth'] = None
            self.identities[lane] = identity
            row.update(pid=handle.pid, birth=identity.get('birth'), started_at=_now(),
                       launch_mode=self.policy['mode'], process_job=identity.get('process_job'),
                       supervisor_job=self.policy['job'], status='starting', error=None)
            self._event('service_started', row, process_job=identity.get('process_job'),
                        supervisor_job=self.policy['job'], model_posts=0)
        except Exception as error:
            row.update(status='launch_failed', error=type(error).__name__ + ': ' + str(error))
            self.failures[lane] = self.failures.get(lane, 0) + 1
            self.next_start[lane] = time.monotonic() + min(30, 2 ** min(self.failures[lane], 5))
            self._event('service_launch_failed', row, error=row['error'])

    def _migrate_idle(self, lane, row, identity):
        try:
            process = psutil.Process(identity['pid'])
            if abs(process.create_time() - identity['birth']) >= .01:
                return
            children = [(p.pid, p.create_time()) for p in process.children(recursive=True)]
            self._event('idle_temporary_service_migration', row, old_identity=identity)
            process.terminate()
            for pid, birth in reversed(children):
                try:
                    child = psutil.Process(pid)
                    if abs(child.create_time() - birth) < .01:
                        child.terminate()
                except psutil.Error:
                    pass
            self.next_start[lane] = time.monotonic() + 1
            row['status'] = 'migrating_idle_host'
        except psutil.Error as error:
            row.update(status='migration_wait', error=type(error).__name__)

    def startup(self, active_lanes=None):
        docker = str(self.native.DOCKER_DIR / 'docker.exe') if os.name == 'nt' else 'docker'
        subprocess.run([docker, 'image', 'inspect', self.native.IMAGE], check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30)
        self._event('supervisor_started', launch_policy=self.policy, model_posts=0)
        active = set(active_lanes or ())
        deadline = time.monotonic() + 960
        while True:
            snapshot = self.tick(active)
            if len(self.ready_lanes | active) >= len(self.rows):
                return snapshot
            if any(row['status'] in ('launch_blocked', 'blocked_owner') for row in snapshot['services']):
                return snapshot
            if time.monotonic() >= deadline:
                return snapshot
            time.sleep(.2)

    def tick(self, active_lanes=None):
        active, now = set(active_lanes or ()), time.monotonic()
        # Fast dispatch rechecks are separate. Full ownership/HTTP monitoring
        # need not walk process ancestry on every scheduler iteration.
        if (self._last_snapshot is not None and active == self._last_active and
                now - self._last_tick < 3):
            return self._last_snapshot
        self._last_tick, self._last_active = now, set(active)
        owners = self._owners()
        self.ready_lanes = set()
        for lane, row in self.rows.items():
            pid, old = owners.get(row['port']), self.identities.get(lane)
            if old:
                try:
                    live = psutil.Process(old['pid'])
                    matches_birth = abs(live.create_time() - (old.get('birth') or 0)) < .01
                except psutil.Error:
                    matches_birth = False
                handle = self.handles.get(lane)
                if not matches_birth or (handle and handle.poll() is not None):
                    self._mark_exit(lane, row, 'original_pid_exited_or_reused')
                    old = None
            future = self.futures.get(lane)
            if future and future[0].done():
                self.futures.pop(lane, None)
                if old and future[1] == (old['pid'], old.get('birth')):
                    self.health[lane] = {**self.health.get(lane, {}), **future[0].result(), 'checked_monotonic': now}
            if pid:
                identity = self._identity(pid, row)
                if not identity.get('matches'):
                    row.update(status='blocked_owner', error='原端口被非原Node入口占用；未结束该进程。',
                               listener_pid=pid)
                    continue
                if old and (old['pid'], old.get('birth')) != (pid, identity.get('birth')):
                    self._mark_exit(lane, row, 'listener_identity_changed')
                    old = None
                if not old:
                    self.identities[lane] = identity
                    row.update(pid=pid, birth=identity['birth'], error=None,
                               launch_mode='adopted_independent', process_job=identity['process_job'])
                    self._event('existing_listener_adopted', row, identity=identity)
                temporary = lane not in self.handles and _codex_host(identity.get('ancestors', []))
                if temporary:
                    if lane in active:
                        row.update(status='draining_temporary_host', error='原通道仍有在途/未知会话，先自然收尾。')
                    elif self.policy['allowed']:
                        self._migrate_idle(lane, row, identity)
                    else:
                        row.update(status='launch_blocked', error=self.policy['reason'])
                    continue
                health = self.health.get(lane, {})
                if lane not in self.futures and now - health.get('checked_monotonic', -100) >= 5:
                    token = (pid, identity['birth'])
                    catalog = token not in self.catalog_checked
                    self.catalog_checked.add(token)
                    warm = lane not in active and (not health.get('backend_ready') or now-health.get('backend_warmed_monotonic',0)>60)
                    self.futures[lane] = (self.executor.submit(self._probe, dict(row), catalog, warm), token, warm)
                row['health'] = {k: v for k, v in health.items() if k != 'checked_monotonic'}
                warming = lane in self.futures and len(self.futures[lane])>2 and self.futures[lane][2]
                backend = health.get('backend_ready') and now-health.get('backend_warmed_monotonic',0)<180
                if lane in active and health.get('ok') and now-health.get('checked_monotonic',0)<20:
                    row.update(status='busy_healthy',error=None)
                elif health.get('ok') and backend and not warming and now - health.get('checked_monotonic', 0) < 20:
                    row.update(status='ready', error=None)
                    self.ready_lanes.add(lane)
                    self.failures[lane] = 0
                else:
                    row.update(status='backend_warming' if warming or not backend else 'http_unavailable',
                               error=health.get('error'))
            elif old:
                row.update(status='starting' if lane in self.handles else 'http_unavailable',
                           error='原进程存在但端口尚未监听；不启动第二个服务。')
            elif lane in active:
                row.update(status='busy_wait', error='原通道有在途/未知会话；等原终态后恢复服务。')
            elif now < self.next_start.get(lane, 0):
                row.update(status='backoff', retry_in_seconds=round(self.next_start[lane] - now, 2))
            else:
                self._launch(lane, row)
        busy_healthy=sum(row.get('status')=='busy_healthy' for row in self.rows.values())
        snapshot = {'checked_at': _now(), 'services': [dict(row) for row in self.rows.values()],
            'healthy_count':len(self.ready_lanes)+busy_healthy,'busy_healthy_count':busy_healthy,
            'ready_count': len(self.ready_lanes), 'ready_lanes': sorted(self.ready_lanes),
            'message': f'健康{len(self.ready_lanes)+busy_healthy}/{len(self.rows)}：空闲已预热{len(self.ready_lanes)}，在途{busy_healthy}；在途结束后重新预热再派发。',
            'supervisor_pid': os.getpid(), 'supervisor_birth': psutil.Process().create_time(),
            'same_ports_entrypoints_state_and_environment': True, 'model_posts': 0}
        fingerprint = json.dumps({k: snapshot[k] for k in ('services', 'ready_lanes')}, sort_keys=True)
        if fingerprint != self._last_disk or now - self._last_heartbeat > 5:
            _write(self.out / 'current.json', snapshot)
            self._last_disk, self._last_heartbeat = fingerprint, now
        self._last_snapshot = snapshot
        return snapshot

    def can_dispatch(self, lane):
        """Last-moment TCP + original PID/birth check; never a model call."""
        # A worker reserves its lane before preparing inputs. A concurrent
        # health tick then calls that exact healthy lane busy_healthy and
        # removes it from the *idle* set. This must not cancel its own first
        # dispatch after a slower attachment/catalog build.
        if lane not in self.ready_lanes and self.rows.get(lane, {}).get('status') != 'busy_healthy':
            return False
        row, old = self.rows[lane], self.identities.get(lane)
        if not old:
            return False
        try:
            process = psutil.Process(old['pid'])
            if abs(process.create_time() - old['birth']) >= .01:
                self.ready_lanes.discard(lane)
                return False
            identity = self._identity(old['pid'], row)
            if not identity.get('matches'):
                self.ready_lanes.discard(lane)
                return False
            if self._owners().get(row['port']) != old['pid']:
                self.ready_lanes.discard(lane)
                return False
            with socket.create_connection(('127.0.0.1', row['port']), timeout=.15):
                return True
        except (OSError, psutil.Error):
            self.ready_lanes.discard(lane)
            return False

    def close(self, stop_owned=False):
        """Default: probes only. Optional cleanup requires caller-proven idle.

        Stop only this Pool's Popen children after ALL native work settled.
        Windows terminate is forced process termination, not Node SIGTERM.
        Independently adopted listeners are never stopped here.
        """
        if stop_owned:
            for lane, handle in list(self.handles.items()):
                row, identity = self.rows[lane], self.identities.get(lane, {})
                try:
                    process = psutil.Process(handle.pid)
                    if abs(process.create_time() - (identity.get('birth') or 0)) >= .01:
                        self._event('idle_cleanup_identity_changed', row)
                        continue
                    children = [(p.pid, p.create_time()) for p in process.children(recursive=True)]
                    self._event('idle_supervisor_shutdown', row,
                        mechanism='TerminateProcess' if os.name == 'nt' else 'SIGTERM',
                        caller_requires_all_native_work_terminal=True)
                    if handle.poll() is None:
                        handle.terminate()
                    for pid, birth in reversed(children):
                        try:
                            child = psutil.Process(pid)
                            if abs(child.create_time() - birth) < .01:
                                child.terminate()
                        except psutil.Error:
                            pass
                    try:
                        handle.wait(timeout=.5)
                    except subprocess.TimeoutExpired:
                        self._event('idle_service_shutdown_wait', row)
                    if handle.poll() is not None:
                        self._mark_exit(lane, row, 'caller_confirmed_idle_shutdown')
                        row['status'] = 'stopped_idle'
                        self.ready_lanes.discard(lane)
                except psutil.NoSuchProcess:
                    self._mark_exit(lane, row, 'already_exited_at_idle_shutdown')
                    row['status'] = 'stopped_idle'
                    self.ready_lanes.discard(lane)
                except psutil.Error as error:
                    self._event('idle_service_shutdown_error', row, error=type(error).__name__)
            if self._last_snapshot is not None:
                snapshot = {**self._last_snapshot, 'checked_at': _now(),
                    'services': [dict(row) for row in self.rows.values()],
                    'ready_count': len(self.ready_lanes), 'ready_lanes': sorted(self.ready_lanes),
                    'message': '主管道确认业务终态后清理自身空闲服务；外部服务和未知会话未结束。'}
                _write(self.out / 'current.json', snapshot)
                self._last_snapshot = snapshot
        if not self.closed:
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.closed = True


def ensure(config):
    """Compatibility only; the single runner should retain its ServicePool."""
    pool = ServicePool(config)
    try:
        return pool.startup()
    finally:
        pool.close()
