"""Bounded WRD data recollection through the unchanged native session adapter.

prepare/preflight are offline.  Network/service/session operations require an
explicit --execute-authorized flag.  This is an outer input/recording adapter,
not an Agent loop: every paid job is one research.workflow.native.run_native.
No current experiment lane, service, source record or training weight is edited.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time
from urllib.request import build_opener, ProxyHandler, Request


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/20261027_wrd_main_v10/runtime_preflight"
OLD = Path("E:/skillloop_runs/ablation49_1025")
SOURCE_RUNTIME = OLD / "runtime_0"
SOURCE_CREDENTIAL = OLD / "private/model_0.json"
BRIDGE = OLD / "bridge"
NODE = Path("C:/Users/22142/AppData/Local/Programs/buddy2api/runtime/node.exe")
DOCKER = Path("C:/Users/22142/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe")
NATIVE_FILE = ROOT / "research/workflow/native.py"
AUDIT_FILE = ROOT / "research/pipelines/enterprise_sft_collection/audit_relay.py"
IMAGE = "sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2"
MODEL = "glm-5.3-flash"
VERSION = "2026.9.5"
TIMEOUT = 1800
MAX_TOKENS = 32768
LANE = 10
BRIDGE_PORT = 8090
AUDIT_PORT = 8091
PLAN_LIMIT = 120
PILOT_LIMIT = 12
RUNTIME_FILES = ["consumer.py", "container_runner.py", "openclaw_config.py",
                 "ecnu_tools.py", "runtime_compat.py", "pdf_form.py"]
STAGES = {"technical_probe", "A_screen", "B_make", "B_prepare", "C_trial_no_skill",
          "C_trial_skill", "C_review", "B_revision", "D_freeze", "teacher_controller"}


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for blob in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(blob)
    return digest.hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def design():
    values = {}
    for name in ("A_B_MODULES.md", "PIPELINE.md"):
        path = ROOT / "research/designs" / name
        text = path.read_text(encoding="utf-8")
        revision = next(line.split("：", 1)[1].strip() for line in text.splitlines()
                        if line.startswith("设计版本："))
        change = next(line.split("：", 1)[1].strip() for line in text.splitlines()
                      if line.startswith("变更编号："))
        values[name] = {"path": str(path), "sha256": sha(path),
                        "design_revision": revision, "change_id": change}
    if len({(v["design_revision"], v["change_id"]) for v in values.values()}) != 1:
        raise RuntimeError("Design pair does not have the same current revision")
    return values


def port_owners(port):
    import psutil
    return sorted({c.pid for c in psutil.net_connections(kind="tcp")
                   if c.status == psutil.CONN_LISTEN and c.laddr.port == port})


def docker_snapshot():
    if not DOCKER.is_file():
        return {"status": "unavailable", "reason": "docker_executable_missing"}
    proc = subprocess.run([str(DOCKER), "ps", "--filter", "label=skillloop.owner=openclaw-eval",
                           "--format", "{{json .}}"], capture_output=True, text=True,
                          encoding="utf-8", errors="strict", timeout=20)
    if proc.returncode:
        return {"status": "unavailable", "reason": "docker_ps_failed", "returncode": proc.returncode}
    rows = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    result = {"status": "observed", "native_containers": rows, "native_container_count": len(rows)}
    image = subprocess.run([str(DOCKER), "image", "inspect", IMAGE, "--format", "{{.Id}}"],
                           capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=20)
    result["pinned_image_present"] = image.returncode == 0 and image.stdout.strip() == IMAGE
    return result


def preflight():
    import psutil
    memory = psutil.virtual_memory()
    status_path = ROOT / "output/20261026_ablation_v2/status.json"
    status = load(status_path) if status_path.is_file() else {}
    sources = [NATIVE_FILE, ROOT / "research/workflow/stages.py", AUDIT_FILE,
               BRIDGE / "src/index.js", BRIDGE / "src/account-pool.js",
               ROOT / "output/20261026_ablation_v2/native_engine.py"]
    sources += [SOURCE_RUNTIME / name for name in RUNTIME_FILES]
    model = load(SOURCE_CREDENTIAL)
    if model.get("model") != MODEL or model.get("max_tokens") != MAX_TOKENS:
        raise RuntimeError("Pinned source model/budget mismatch")
    result = {"schema": "wrd-native-rebuild-runtime-preflight-v1", "at": now(),
        "status": "READ_ONLY_NO_SERVICES_NO_SESSIONS", "training_started": False,
        "services_started": 0, "new_model_calls": 0, "image": IMAGE, "model": MODEL,
        "openclaw_version": VERSION, "session_timeout_seconds": TIMEOUT,
        "per_reply_max_tokens": MAX_TOKENS,
        "container_quota": {"memory_gib": 6, "cpus": 4, "shm_gib": 1},
        "host": {"platform": sys.platform, "logical_cpu": psutil.cpu_count(),
                 "total_memory_bytes": memory.total, "available_memory_bytes": memory.available,
                 "is_user_reported_spark": False},
        "isolated_lane": {"id": LANE, "bridge_port": BRIDGE_PORT, "audit_port": AUDIT_PORT,
                          "port_owners": {str(p): port_owners(p) for p in (BRIDGE_PORT, AUDIT_PORT)},
                          "maximum_rebuild_concurrency": 1,
                          "existing_experiment_lanes_0_to_9_reused": False},
        "parallel_experiment_status": {k: status.get(k) for k in
            ("updated_at", "runner_pid", "phase", "finished", "maximum_concurrency", "active")},
        "parallel_admission": {
            "existing_driver_counts_external_native_containers": True,
            "cross_process_atomic_reservation": False,
            "warning": "Admission is thread-local to each driver. A launch race is possible; do not claim a global atomic cap.",
            "account_state": "reuse existing private accounts without copying, resetting, or changing rotation",
            "backend_registry": "new lane has its own BUDDY2API_STATE_DIR; upstream account/quota availability remains unknown"},
        "unit_cost": {"new_lane_measured": False, "cash_cost": None,
                      "provider_quota_remaining": None,
                      "historical_mixed_stage_tokens_are_not_a_forecast": True},
        "source_files": [{"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size}
                         for p in sources if p.is_file()], "design_pair": design()}
    save(OUT / "RUNTIME_PREFLIGHT.json", result)
    return result


# Appended only to the fresh recording runtime. It runs after the native loop
# and gateway shutdown; native tool implementations/returns are never touched.
ALL_SESSION_RECORDING = '''
def record_all_native_sessions(state_dir, transport, secret_values, receipt):
    """Record all persisted native events in this disposable attempt, read-only."""
    rows_written=0; databases=[]
    try:
        state_dir=Path(state_dir).resolve()
        target=Path(transport)/'all_session_events.jsonl'
        with target.open('w',encoding='utf-8',newline='\\n') as out:
            for database in sorted((state_dir/'agents').glob('*/agent/openclaw-agent.sqlite')):
                if database.is_symlink() or not database.resolve().is_relative_to(state_dir):
                    raise RuntimeError('Recording database escaped disposable state')
                agent_id=database.parent.parent.name
                with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)) as connection:
                    connection.execute('PRAGMA query_only=ON')
                    columns={r[1] for r in connection.execute('PRAGMA table_info(transcript_events)')}
                    if not {'session_id','seq','event_json'}.issubset(columns):
                        raise RuntimeError('Native transcript schema changed')
                    rows=connection.execute('SELECT session_id,seq,event_json FROM transcript_events ORDER BY session_id,seq').fetchall()
                sessions={}
                for session_id,sequence,text in rows:
                    event=json.loads(text)
                    if not isinstance(event,dict):raise RuntimeError('Native event is not an object')
                    row={'agent_id':agent_id,'session_id':session_id,'seq':sequence,'native_event':event}
                    out.write(json.dumps(redact_runtime(row,*secret_values),ensure_ascii=False)+'\\n')
                    rows_written+=1;sessions[session_id]=sessions.get(session_id,0)+1
                databases.append({'agent_id':agent_id,'sessions':sessions,'rows':len(rows)})
        receipt['all_session_transcript_recording']={'status':'recorded','rows':rows_written,
            'databases':databases,'read_only':True,'native_tool_returns_modified':False,
            'scope':'all persisted transcripts in fresh disposable attempt state; child completion is not assumed',
            'redaction':'exact_model_key_and_gateway_token_only'}
    except Exception as error:
        receipt['all_session_transcript_recording']={'status':'failed',
            'error':redact_runtime(str(error),*secret_values),'partial_rows':rows_written}

'''


def prepare():
    """Create reviewed runtime/profile/credentials; never bind a listening port."""
    OUT.mkdir(parents=True, exist_ok=True)
    private = OUT / "private"
    private.mkdir(exist_ok=True)
    # Repository policy ignores **/private/. Refuse to place a secret where Git
    # would track it, including a newly changed ignore policy.
    ignored = subprocess.run(["git", "check-ignore", "--no-index", str(private / "model_consumer.json")],
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="strict")
    if ignored.returncode:
        raise RuntimeError("Private credential destination is not Git-ignored")
    runtime = OUT / "runtime_10"
    runtime.mkdir(exist_ok=True)
    modifications = []
    for name in RUNTIME_FILES:
        source = SOURCE_RUNTIME / name
        text = source.read_text(encoding="utf-8")
        original = text
        if name == "openclaw_config.py":
            old = "http://host.docker.internal:8080/v1"
            if old not in text:
                raise RuntimeError("Pinned endpoint exception anchor missing")
            text = text.replace(old, f"http://host.docker.internal:{AUDIT_PORT}/v1")
        if name == "container_runner.py":
            anchor = "def episode_messages(first_message, followup_inputs):"
            if text.count(anchor) != 1:
                raise RuntimeError("Pinned post-loop recorder insertion anchor mismatch")
            text = text.replace(anchor, ALL_SESSION_RECORDING + "\n" + anchor)
            anchor = "        try:export_gateway_logs(gateway_log_dir,transport,*secret_values)"
            if text.count(anchor) != 1:
                raise RuntimeError("Pinned final recording anchor mismatch")
            text = text.replace(anchor,
                "        record_all_native_sessions(state,transport,secret_values,receipt)\n" + anchor)
        target = runtime / name
        blob = text.encode("utf-8")
        if target.exists() and target.read_bytes() != blob:
            raise RuntimeError("Existing prepared runtime differs; inspect rather than replace: " + str(target))
        target.write_bytes(blob)
        compile(text, str(target), "exec")
        modifications.append({"file": name, "source_sha256": sha(source), "prepared_sha256": sha(target),
                              "semantic_change": name in ("openclaw_config.py", "container_runner.py")})
        if text != original:
            (OUT / (name + ".recording.diff")).write_text("".join(difflib.unified_diff(
                original.splitlines(True), text.splitlines(True), fromfile="pinned/"+name,
                tofile="recording_only/"+name)), encoding="utf-8")
    credentials = load(SOURCE_CREDENTIAL)
    if credentials.get("model") != MODEL or credentials.get("max_tokens") != MAX_TOKENS:
        raise RuntimeError("Source credential model/budget mismatch")
    consumer_credentials = dict(credentials, base_url=f"http://host.docker.internal:{AUDIT_PORT}/v1")
    upstream_credentials = dict(credentials, base_url=f"http://127.0.0.1:{BRIDGE_PORT}/v1")
    save(private / "model_consumer.json", consumer_credentials)
    save(private / "model_upstream.json", upstream_credentials)
    source_config = module(SOURCE_RUNTIME / "openclaw_config.py", "v10_source_native_config")
    target_config = module(runtime / "openclaw_config.py", "v10_recording_native_config")
    source_value = source_config.build_openclaw_config(model_id=MODEL,
        base_url="http://host.docker.internal:8080/v1", timeout_seconds=TIMEOUT, max_tokens=MAX_TOKENS)
    target_value = target_config.build_openclaw_config(model_id=MODEL,
        base_url=f"http://host.docker.internal:{AUDIT_PORT}/v1", timeout_seconds=TIMEOUT, max_tokens=MAX_TOKENS)
    normalize = lambda value, port: json.dumps(value, sort_keys=True).replace(
        f"http://host.docker.internal:{port}/v1", "http://host.docker.internal:PORT/v1")
    if normalize(source_value, 8080) != normalize(target_value, AUDIT_PORT):
        raise RuntimeError("Native config differs by more than recording endpoint")
    profile = OUT / "profile_10.json"
    save(profile, {"runtime_dir": str(runtime), "event_file": str(OUT / "lane_10/native_events.jsonl"),
                   "image_id": IMAGE, "custom_agent_loop": False, "native_tools_overridden": False,
                   "recording_only_all_session_export": True})
    save(OUT / "lane.json", [{"id": LANE, "port": AUDIT_PORT,
         "credentials": str(private / "model_consumer.json"), "profile": str(profile)}])
    probe = {"schema": "wrd-native-rebuild-job-v1", "job_id": "technical_native_child_capture_probe",
        "stage": "technical_probe", "source_ids": [], "source_split": "technical_only",
        "resources": [], "skills": [], "protected_ancestry_checked": True,
        "prompt": "这是仅一次原生能力核验，不处理企业任务、不制作skill、不训练。"
          "请调用agents_list查看允许的Agent，再用原生sessions_spawn创建一个隐藏的只读子任务，"
          "要求子任务只报告当前目录并读取/workspace中目录清单，不修改文件、不联网、不递归生成子任务；"
          "使用runtime=subagent、context=isolated、cleanup=keep、mode=run、completionTarget=parent，"
          "不覆盖model/thinking，不创建worktree。等待原生子任务回传后报告真实结果及边界。"
          "若原工具不支持或拒绝，保留错误并停止，不改配置或绕过限制。"
          "不要据cwd/context声称文件系统隔离或公平两臂；不要启动任何业务工作。",
        "training_eligibility": "TECHNICAL_PROBE_NOT_MAIN_POSITIVE"}
    save(OUT / "technical_probe.job.json", probe)
    save(OUT / "JOB_INTERFACE.json", {
        "schema": "wrd-native-rebuild-job-v1", "required": ["job_id", "stage", "prompt", "source_ids",
            "source_split", "protected_ancestry_checked", "resources", "skills"],
        "stage_enum": sorted(STAGES), "resource": {"path": "absolute ordinary source file/directory",
            "mount": "relative workspace path", "sha256": "mandatory for every supplied file"},
        "skill": {"id": "native discovery id", "path": "fresh clean skill directory",
                  "sha256_tree": "mandatory canonical relative-path/file-sha mapping hash"},
        "source_split": "train only; never original226/newH/static dev/test",
        "ancestry": "frozen source allowlist receipt required for every business job; filenames/status are not evidence",
        "resource_manifest": {"required_for_business": True, "status": "PASS",
            "source_allowlist_sha256": "exact allowlist receipt hash",
            "files": [{"path": "absolute file path", "sha256": "original immutable bytes hash",
                       "ancestry_source_ids": ["all transitive enterprise source ancestors"]}],
            "note": "Every mounted resource and every learned-skill file must have an exact path/SHA row. Source IDs must be inside both job and frozen train allowlist."},
        "chain": "chain_id, parent_job_ids, exact skill/version sha and result ids are explicit metadata; do not supply future feedback",
        "original_reasoning": "raw API request/JSON/SSE + native transcript; unavailable readable R stays unavailable",
        "phase_control": "outer dispatch only complete sessions. No step-level tool/loop control.",
        "teacher_controller": "not main-eligible until native child tool/model/trace/resource-scope probe passes",
        "two_arm_fairness": "separate fresh native sessions unless native child resource isolation is independently proven",
        "source_examples": "CLEAN_ACTOR_INVENTORY.json entries are candidates, not quality labels"})
    manifest = {"schema": "wrd-native-recording-lane-v1", "at": now(), "status": "PREPARED_NOT_STARTED",
        "preparation_script": {"path": str(Path(__file__).resolve()), "sha256": sha(Path(__file__))},
        "native_adapter": {"path": str(NATIVE_FILE), "sha256": sha(NATIVE_FILE)},
        "audit_relay": {"path": str(AUDIT_FILE), "sha256": sha(AUDIT_FILE),
                        "request_response_body_rewritten": False, "max_calls": None},
        "image": IMAGE, "model": MODEL, "openclaw_version": VERSION,
        "timeout_seconds": TIMEOUT, "per_reply_max_tokens": MAX_TOKENS,
        "new_lane": LANE, "bridge_port": BRIDGE_PORT, "recording_port": AUDIT_PORT,
        "maximum_rebuild_concurrency": 1, "pilot_stage_limit": PILOT_LIMIT,
        "plan_stage_limit": PLAN_LIMIT, "runtime": modifications,
        "native_config_equal_except_endpoint": True, "custom_agent_loop": False,
        "native_tools_overridden": False, "native_tool_returns_modified": False,
        "credentials_in_manifest": False, "services_started": 0, "new_model_calls": 0,
        "training_started": False, "design_pair": design()}
    save(OUT / "PREPARED_LANE.json", manifest)
    return manifest


def authorize(flag):
    if not flag:
        raise RuntimeError("Explicit --execute-authorized is required; prepare/preflight never start execution")


def alive(info):
    import psutil
    try:
        return abs(psutil.Process(info["pid"]).create_time() - info["birth"]) < 0.05
    except psutil.Error:
        return False


def start_service(authorized):
    """Start this one new bridge only. Never adopt/stop another port owner."""
    authorize(authorized)
    import psutil
    prepared = load(OUT / "PREPARED_LANE.json")
    if prepared["design_pair"] != design() or prepared["preparation_script"]["sha256"] != sha(Path(__file__)):
        raise RuntimeError("Design pair / preparation script changed; refresh reviewed offline preparation")
    if prepared["native_adapter"]["sha256"] != sha(NATIVE_FILE):
        raise RuntimeError("Native source changed since prepare")
    current = docker_snapshot()
    if current.get("status") != "observed" or not current.get("pinned_image_present"):
        raise RuntimeError("Pinned image and actual container occupancy must be observed before startup")
    if current["native_container_count"] >= 8 or psutil.virtual_memory().available < 7 * 2**30:
        raise RuntimeError("New-lane startup requires fewer than8 native containers and at least7GiB free RAM")
    service_path = OUT / "bridge_service.json"
    if service_path.is_file() and alive(load(service_path)):
        info = load(service_path)
        if port_owners(BRIDGE_PORT) != [info["pid"]]:
            raise RuntimeError("Own saved service listener mismatch")
        return dict(info, adopted=True)
    if port_owners(BRIDGE_PORT) or port_owners(AUDIT_PORT):
        raise RuntimeError("A proposed new-lane port is occupied; no process will be replaced")
    for port in (BRIDGE_PORT, AUDIT_PORT):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))
    directory = OUT / "lane_10"
    directory.mkdir(exist_ok=True)
    env = dict(os.environ)
    env.pop("GATEWAY_URL", None)
    env.update(HOST="127.0.0.1", PORT=str(BRIDGE_PORT),
        BUDDY2API_STATE_DIR=str(directory / "service_state"),
        BUDDY2API_ACCOUNTS_DIR=str(OLD / "private/accounts"),
        CODEBUDDY_CLI_PATH=str(BRIDGE / "vendor/codebuddy-cli/bin/codebuddy"),
        WORKFLOW_NATIVE_METER_FILE=str(directory / "native_events.jsonl"),
        TOKEN_STATS_FILE=str(directory / "interface_usage.jsonl"),
        NATIVE_FAILURE_WIRE=str(directory / "failure_wire.jsonl"))
    with (OUT / "bridge.stdout.log").open("ab") as out, (OUT / "bridge.stderr.log").open("ab") as err:
        handle = subprocess.Popen([str(NODE), str(BRIDGE / "src/index.js")], cwd=BRIDGE,
            env=env, stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
    info = {"pid": handle.pid, "birth": psutil.Process(handle.pid).create_time(),
            "port": BRIDGE_PORT, "lane": LANE, "at": now(), "private_account_state_reset": False,
            "shared_upstream_accounts": True, "new_model_calls_requested_by_start": 0}
    save(service_path, info)
    opener = build_opener(ProxyHandler({}))
    for _ in range(45):
        if handle.poll() is not None:
            raise RuntimeError("New bridge exited before readiness; inspect saved logs; no auto restart")
        try:
            with opener.open(Request(f"http://127.0.0.1:{BRIDGE_PORT}/", method="OPTIONS"), timeout=2) as response:
                if response.status == 204:
                    return dict(info, ready=True)
        except Exception:
            time.sleep(1)
    raise RuntimeError("New bridge readiness unresolved; inspect saved pid; no duplicate launch")


def validate_job(job):
    for key in ("job_id", "stage", "prompt", "source_ids", "source_split", "resources", "skills"):
        if key not in job:
            raise ValueError("Missing job key: " + key)
    if job["stage"] not in STAGES or not job.get("protected_ancestry_checked"):
        raise ValueError("Stage or ancestry receipt is missing")
    if not isinstance(job["job_id"], str) or not job["job_id"] or any(c not in
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in job["job_id"]):
        raise ValueError("job_id must be a simple immutable filename")
    if job["stage"] == "technical_probe":
        expected = load(OUT / "technical_probe.job.json")
        if job != expected:
            raise ValueError("Technical-only exception is restricted to the frozen read-only probe")
    permitted_files = {}
    if job["stage"] != "technical_probe":
        if job["source_split"] != "train" or not job["source_ids"]:
            raise ValueError("Business reconstruction accepts training sources only")
        receipt = load(job["source_allowlist_receipt"])
        if receipt.get("status") != "PASS" or not set(job["source_ids"]).issubset(receipt.get("train_source_ids", [])):
            raise ValueError("Frozen clean ancestry allowlist receipt does not cover this job")
        if not receipt.get("original226_isolated") or not receipt.get("newH_isolated") or not receipt.get("static_dev_test_isolated"):
            raise ValueError("All three protected boundaries must be verified")
        if sha(job["source_allowlist_receipt"]) != job.get("source_allowlist_sha256"):
            raise ValueError("Frozen source receipt SHA differs")
        resource_receipt = load(job["resource_ancestry_receipt"])
        if resource_receipt.get("status") != "PASS" or resource_receipt.get("source_allowlist_sha256") != job["source_allowlist_sha256"]:
            raise ValueError("Resource ancestry receipt is not bound to the clean source allowlist")
        if sha(job["resource_ancestry_receipt"]) != job.get("resource_ancestry_sha256"):
            raise ValueError("Resource ancestry receipt SHA differs")
        for row in resource_receipt.get("files", []):
            ancestors = row.get("ancestry_source_ids")
            if not isinstance(ancestors, list) or not set(ancestors).issubset(job["source_ids"]):
                raise ValueError("Resource transitive ancestors are outside the job training sources")
            if not ancestors and row.get("origin") != "new_protocol_metadata_without_enterprise_content":
                raise ValueError("Empty resource ancestry is permitted only for explicit new protocol metadata")
            key = str(Path(row["path"]).resolve()).casefold()
            if key in permitted_files and permitted_files[key] != row["sha256"]:
                raise ValueError("Resource receipt has conflicting file identities")
            permitted_files[key] = row["sha256"]
    if job["stage"] == "teacher_controller":
        proof = load(job["native_controller_probe_receipt"])
        required = ("verified_same_model", "verified_native_tools", "child_event_capture_complete",
                    "resource_scopes_verified")
        if proof.get("status") != "PASS" or not all(proof.get(key) is True for key in required):
            raise ValueError("Single Teacher orchestration requires actual native child/resource-scope proof")
        if proof.get("prepared_lane_manifest_sha256") != sha(OUT / "PREPARED_LANE.json"):
            raise ValueError("Native controller proof is not bound to the current prepared environment")
    for item in job["resources"]:
        source = Path(item["path"])
        if not source.is_file() or source.is_symlink() or sha(source) != item.get("sha256"):
            raise ValueError("Resource must be a checksum-verified ordinary file: " + str(source))
        if job["stage"] != "technical_probe" and permitted_files.get(str(source.resolve()).casefold()) != item["sha256"]:
            raise ValueError("Mounted resource is not present in the frozen ancestry receipt")
    for item in job["skills"]:
        root = Path(item["path"])
        if not (root / "SKILL.md").is_file() or root.is_symlink():
            raise ValueError("Native skill entry is missing")
        files = {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}
        digest = hashlib.sha256(json.dumps(files, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if digest != item.get("sha256_tree") or any(p.is_symlink() for p in root.rglob("*")):
            raise ValueError("Skill immutable tree mismatch")
        if any(permitted_files.get(str((root / rel).resolve()).casefold()) != digest
               for rel, digest in files.items()):
            raise ValueError("A learned-skill file is not present in the frozen ancestry receipt")
    if job["stage"] == "C_trial_no_skill" and job["skills"]:
        raise ValueError("No-skill trial cannot mount learned skills")
    return job


def inspect_capture(episode):
    """Offline evidence inventory; never turns process completion into quality."""
    episode = Path(episode).resolve()
    if not episode.is_relative_to((OUT / "episodes").resolve()):
        raise ValueError("Capture assessment must stay in this reconstruction tree")
    calls = []
    models = set()
    readable_fields = {}
    names = {"agents_list": 0, "sessions_spawn": 0}

    def visit(value, path="$", *, response=False):
        if isinstance(value, dict):
            if response and isinstance(value.get("model"), str):
                models.add(value["model"])
            if response and value.get("name") in names:
                names[value["name"]] += 1
            for key, item in value.items():
                child = path + "." + key
                if key.lower() in {"reasoning", "reasoning_content", "reasoning_text", "thinking", "analysis"} and isinstance(item, str) and item:
                    field = readable_fields.setdefault(child, {"occurrences": 0, "utf8_bytes": 0})
                    field["occurrences"] += 1
                    field["utf8_bytes"] += len(item.encode("utf-8"))
                visit(item, child, response=response)
        elif isinstance(value, list):
            for item in value:
                visit(item, path + "[]", response=response)

    for folder in sorted((episode / "api_audit").glob("*")):
        if not folder.is_dir() or not (folder / "request.raw.json").is_file():
            continue
        request = load(folder / "request.raw.json")
        receipt = load(folder / "receipt.json") if (folder / "receipt.json").is_file() else {}
        response_file = next((folder / name for name in ("response.raw.sse", "response.raw.json")
                              if (folder / name).is_file()), None)
        row = {"call_id": folder.name, "request_sha256": sha(folder / "request.raw.json"),
            "request_bytes": (folder / "request.raw.json").stat().st_size,
            "request_sha_matches_receipt": sha(folder / "request.raw.json") == receipt.get("request_sha256"),
            "receipt_status": receipt.get("status"), "http_status": receipt.get("http_status"),
            "model_requested": request.get("model"), "system_messages": sum(
                m.get("role") == "system" for m in request.get("messages", [])),
            "tools_count": len(request.get("tools", [])), "messages_count": len(request.get("messages", [])),
            "request_body_rewritten": receipt.get("request_body_rewritten"),
            "response_body_rewritten": receipt.get("response_body_rewritten"),
            "response_sha_matches_receipt": bool(response_file) and sha(response_file) == receipt.get("response_sha256")}
        if response_file:
            row.update(response_sha256=sha(response_file), response_bytes=response_file.stat().st_size,
                       response_format=response_file.suffix)
            try:
                text = response_file.read_text(encoding="utf-8")
                values = []
                if response_file.suffix == ".sse":
                    for block in text.replace("\r\n", "\n").split("\n\n"):
                        payload = "\n".join(line[5:].lstrip(" ") for line in block.splitlines() if line.startswith("data:"))
                        if payload and payload != "[DONE]":
                            values.append(json.loads(payload))
                else:
                    values = [json.loads(text)]
                for value in values:
                    visit(value, response=True)
            except (UnicodeError, ValueError, TypeError) as error:
                row["raw_response_parse_error"] = type(error).__name__
        calls.append(row)
    all_events = episode / "openclaw_transport/all_session_events.jsonl"
    sessions = {}
    native_models = set()
    if all_events.is_file():
        for line in all_events.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            key = event["agent_id"] + ":" + str(event["session_id"])
            sessions[key] = sessions.get(key, 0) + 1
            visit(event.get("native_event"), "$native", response=False)
            # Only explicit native model fields are evidence, never inference
            # from the parent's configured model.
            def model_fields(value):
                if isinstance(value, dict):
                    for key, item in value.items():
                        if key in ("model", "modelId") and isinstance(item, str):
                            native_models.add(item)
                        model_fields(item)
                elif isinstance(value, list):
                    for item in value:
                        model_fields(item)
            model_fields(event["native_event"])
    result = {"schema": "wrd-native-full-capture-assessment-v1", "at": now(),
        "scope": "offline recorded evidence only; no quality/skill-effect claim",
        "api_calls": calls, "api_calls_count": len(calls), "raw_response_models": sorted(models),
        "native_event_models": sorted(native_models), "native_sessions": sessions,
        "native_all_session_file_present": all_events.is_file(),
        "original_readable_fields": readable_fields,
        "original_readable_reasoning_is_not_synthesized": True,
        "response_tool_call_name_fragments": names,
        "child_same_model_verified": "not inferred: inspect child event identity + actual API trace",
        "child_filesystem_isolation_verified": False,
        "main_positive_eligibility": False, "training_started": False}
    save(episode / "CAPTURE_ASSESSMENT.json", result)
    return result


@contextlib.contextmanager
def exclusive_lane():
    import msvcrt
    guard = (OUT / "lane_10.lock").open("a+b")
    try:
        guard.seek(0)
        if not guard.read(1):
            guard.write(b"0"); guard.flush()
        guard.seek(0)
        msvcrt.locking(guard.fileno(), msvcrt.LK_NBLCK, 1)
        yield
    finally:
        guard.close()


def run_job(path, authorized, pilot_only=True):
    authorize(authorized)
    import psutil
    job = validate_job(load(path))
    prepared = load(OUT / "PREPARED_LANE.json")
    if prepared["design_pair"] != design() or prepared["preparation_script"]["sha256"] != sha(Path(__file__)):
        raise RuntimeError("Design pair / preparation script changed; refresh reviewed offline preparation")
    if prepared["native_adapter"]["sha256"] != sha(NATIVE_FILE) or prepared["audit_relay"]["sha256"] != sha(AUDIT_FILE):
        raise RuntimeError("Prepared source SHA changed; explicitly re-review before execution")
    for row in prepared["runtime"]:
        if sha(OUT / "runtime_10" / row["file"]) != row["prepared_sha256"]:
            raise RuntimeError("Recording runtime bytes changed after preparation")
    service = load(OUT / "bridge_service.json")
    if not alive(service) or port_owners(BRIDGE_PORT) != [service["pid"]]:
        raise RuntimeError("Own bridge is not ready; never use a current experiment lane")
    with exclusive_lane():
        episodes = OUT / "episodes"
        episodes.mkdir(exist_ok=True)
        episode = episodes / job["job_id"]
        # Native adapter owns adoption/no-replay once a dispatch exists. Before
        # starting a fresh one, bound physical stages and check actual resources.
        if not (episode / "dispatch.json").is_file():
            used = sum(1 for _ in episodes.glob("*/dispatch.json"))
            if used >= (PILOT_LIMIT if pilot_only else PLAN_LIMIT):
                raise RuntimeError("Bounded physical stage limit reached; no automatic expansion")
            snap = docker_snapshot()
            if snap.get("status") != "observed" or not snap.get("pinned_image_present"):
                raise RuntimeError("Pinned image / actual native container count is unavailable")
            if snap["native_container_count"] >= 8 or psutil.virtual_memory().available < 7 * 2**30:
                raise RuntimeError("Insufficient observed headroom; no experiment service will be touched")
        if port_owners(AUDIT_PORT):
            raise RuntimeError("Recording port occupied; do not replace/adopt another recorder")
        episode.mkdir(exist_ok=True)
        snapshot = dict(job)
        if (episode / "job.json").exists() and load(episode / "job.json") != snapshot:
            raise RuntimeError("Existing paid job cannot be changed")
        save(episode / "job.json", snapshot)
        audit = module(AUDIT_FILE, "v10_native_passive_audit")
        pair = design()
        first = next(iter(pair.values()))
        audit.DESIGN = {"design_revision": first["design_revision"], "change_id": first["change_id"],
                        "schema_version": "workflow-pipeline-v1"}
        server = audit.AuditServer(("0.0.0.0", AUDIT_PORT), OUT / "private/model_upstream.json",
            episode / "api_audit", timeout=TIMEOUT, max_calls=None, purpose="bounded_clean_wrd_native_rebuild")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            native = module(NATIVE_FILE, "v10_original_native_adapter")
            result = native.run_native(episode, job["prompt"], job["resources"], job["skills"], LANE,
                                       {"lanes_file": str(OUT / "lane.json"), "python": sys.executable})
            save(episode / "outer_recording_receipt.json", {"at": now(), "job_sha256": sha(episode / "job.json"),
                "design_pair": pair, "native_adapter_sha256": sha(NATIVE_FILE),
                "runtime_manifest_sha256": sha(OUT / "PREPARED_LANE.json"),
                "request_response_body_rewritten": False, "max_calls_override": None,
                "native_tools_overridden": False, "training_started": False,
                "stage_completed_is_not_content_quality_or_positive_loss": True})
            return result
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "prepare", "validate-job", "start-service", "run-job", "inspect-capture"))
    parser.add_argument("--job", type=Path)
    parser.add_argument("--episode", type=Path)
    parser.add_argument("--execute-authorized", action="store_true")
    parser.add_argument("--after-pilot-review", action="store_true",
                        help="Explicitly use plan-wide120 stage cap rather than pilot12; never trains")
    args = parser.parse_args()
    if args.command == "preflight":
        result = preflight()
    elif args.command == "prepare":
        result = prepare()
    elif args.command == "start-service":
        result = start_service(args.execute_authorized)
    elif args.command == "validate-job":
        if not args.job:
            parser.error("--job is required")
        result = {"status": "VALID", "job_id": validate_job(load(args.job))["job_id"], "new_model_calls": 0}
    elif args.command == "inspect-capture":
        if not args.episode:
            parser.error("--episode is required")
        result = inspect_capture(args.episode)
    else:
        if not args.job:
            parser.error("--job is required")
        result = run_job(args.job, args.execute_authorized, not args.after_pilot_review)
    print(json.dumps({k: result.get(k) for k in ("status", "at", "job_id", "ready", "pid", "services_started",
                      "new_model_calls", "training_started") if k in result}, ensure_ascii=False))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
