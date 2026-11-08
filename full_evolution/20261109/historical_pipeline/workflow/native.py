"""One native OpenClaw session, with passive cost recording.

This adapter stages files and starts the existing per-lane consumer.  It does
not implement an Agent/tool loop or import the historical pipeline wrappers.
The caller owns lane scheduling: at most one session may use a lane at a time.
All new files stay under ``episode_dir``; existing lane configuration is read
only.  A dispatched episode is never automatically dispatched a second time.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone


IMAGE = "sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2"
MODEL = "glm-5.3-flash"
OPENCLAW_VERSION = "2026.9.5"
TIMEOUT = 1800
MAX_TOKENS = 32768
DOCKER_DIR = Path("C:/Users/22142/AppData/Local/Programs/DockerDesktop/resources/bin")
SKILL_NOTICE = (
    "本题已挂载专用技能，入口位于 /workspace/learned_skills/ 下对应目录的 SKILL.md。"
    "任务相关时读取首页，按照路线按需使用其中的程序、模板和阶段说明。"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _relative_mount(value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Resource mount must be a relative workspace path")
    parts = PurePosixPath(value)
    if parts.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError("Resource mount must stay inside this workspace")
    if parts.parts[0] in ("learned_skills", "skills"):
        raise ValueError("Use the skills argument for learned skill packages")
    return Path(*parts.parts)


def _copy(source: Path, target: Path) -> None:
    if source.is_symlink():
        raise ValueError("Input must be an ordinary file or directory: " + str(source))
    if not source.exists():
        raise FileNotFoundError(source)
    if source.is_dir():
        if any(item.is_symlink() for item in source.rglob("*")):
            raise ValueError("Input directory contains a symbolic link: " + str(source))
        shutil.copytree(source, target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def _skill_files(root: Path) -> dict:
    # The unchanged native consumer needs this file map to discover/copy skills.
    return {
        file.relative_to(root).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted(root.rglob("*")) if file.is_file()
    }


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 and value < float("inf")


def _usage(raw: bytes, *, event_file_present: bool, read_error: str | None = None) -> dict:
    """Count distinct provider request identities; missing usage remains unknown."""
    groups, errors = {}, []
    if read_error:
        errors.append(read_error)
    if not event_file_present:
        errors.append("native_event_file_missing")
    for line_no, line in enumerate(raw.splitlines(), 1):
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("event is not an object")
            identity = (event.get("pid"), event.get("native_request_id"))
            if not all(identity):
                errors.append("missing_request_identity_at_line_" + str(line_no))
                continue
            groups.setdefault(identity, []).append(event)
        except (ValueError, TypeError) as error:
            errors.append("invalid_event_line_" + str(line_no) + ":" + str(error))
    rows = []
    for (pid, request_id), events in groups.items():
        starts = [item for item in events if item.get("event") == "native_start"]
        complete_usages = [
            item["usage"] for item in events
            if item.get("event") == "native_usage" and isinstance(item.get("usage"), dict)
            and _number(item["usage"].get("prompt_tokens"))
            and _number(item["usage"].get("completion_tokens"))
        ]
        values = {(item["prompt_tokens"], item["completion_tokens"]) for item in complete_usages}
        chosen = complete_usages[-1] if len(values) == 1 else None
        ended = any(item.get("event") in ("native_stream_end", "native_done_frame") for item in events)
        issues = []
        if len(starts) != 1:
            issues.append("request_start_missing_or_duplicated")
        if not ended:
            issues.append("request_end_not_recorded")
        if len(values) > 1:
            issues.append("conflicting_provider_usage")
        if chosen is None:
            issues.append("complete_provider_usage_missing")
        if any(item.get("event") in ("observer_error", "native_frame_parse_error") for item in events):
            issues.append("observer_error")
        if any(item.get("event") == "native_stream_end" and
               item.get("unparsed_tail_non_whitespace_bytes", item.get("unparsed_tail_bytes", 0)) for item in events):
            issues.append("unparsed_stream_tail")
        rows.append({
            "pid": pid, "request_id": request_id,
            "model": (starts[0] if starts else events[0]).get("model"),
            "input_tokens": chosen["prompt_tokens"] if chosen else None,
            "output_tokens": chosen["completion_tokens"] if chosen else None,
            "complete": not issues, "issues": issues,
        })
    known_input = sum(row["input_tokens"] or 0 for row in rows)
    known_output = sum(row["output_tokens"] or 0 for row in rows)
    complete = bool(rows) and not errors and all(row["complete"] for row in rows)
    return {
        "measurement_status": "complete" if complete else "partial" if rows else "unknown",
        "known_input_tokens": known_input, "known_output_tokens": known_output,
        "known_total_tokens": known_input + known_output,
        "total_tokens": known_input + known_output if complete else None,
        "model_calls": len(rows) if rows and not errors else None,
        "known_model_calls": len(rows),
        "complete_usage_calls": sum(row["complete"] for row in rows),
        "unknown_usage_calls": sum(not row["complete"] for row in rows),
        "errors": errors, "requests": rows,
        "cash_cost": None,
        "definition": "One distinct native provider request is one model call; missing usage is unknown, never zero. Reading and error recovery remain included.",
    }


def _event_offset(event_file: Path) -> int:
    return event_file.stat().st_size if event_file.is_file() else 0


def _collect_usage(root: Path, event_file: Path, start: int) -> dict:
    end, raw, error = start, b"", None
    present = event_file.is_file()
    try:
        end = _event_offset(event_file)
        if end < start:
            raise ValueError("native event file shrank during this session")
        if present:
            with event_file.open("rb") as stream:
                stream.seek(start)
                raw = stream.read(end - start)
    except (OSError, ValueError) as exception:
        error = type(exception).__name__ + ": " + str(exception)
    (root / "native_events.jsonl").write_bytes(raw)
    result = _usage(raw, event_file_present=present, read_error=error)
    result.update(event_file=str(event_file), start_offset=start, end_offset=end)
    _save(root / "usage.json", result)
    return result


def _process_birth(pid: int):
    try:
        import psutil
        return psutil.Process(pid).create_time()
    except Exception:
        return None


def _process_state(record: dict) -> str:
    """PID and birth identify the original consumer, including after restart."""
    try:
        import psutil
        try:
            process = psutil.Process(record["pid"])
        except psutil.NoSuchProcess:
            return "exited"
        birth = record.get("create_time")
        if birth is None:
            return "unknown"
        if abs(process.create_time() - birth) > .01:
            return "pid_reused"
        return "running" if process.is_running() else "exited"
    except Exception:
        return "unknown"


def _finish(root: Path, event_file: Path, start_offset: int, *, returncode,
            error, seconds: float, recording_errors=(), recovered=False,
            unresolved=False) -> dict:
    usage = _collect_usage(root, event_file, start_offset)
    stderr_path = root / 'stderr.log'
    stderr = stderr_path.read_text(encoding='utf-8', errors='replace')[-6000:] if stderr_path.is_file() else ''
    # The unchanged native consumer inspects the image before launching any
    # container. This exact failure cannot have made a model request.
    not_started = (returncode not in (None, 0) and
                   "inspect=subprocess.run(prefix+['image','inspect',image" in stderr and
                   'CalledProcessError' in stderr and not usage.get('requests'))
    if not_started:
        error = 'Docker镜像访问失败，原生容器尚未启动；详见stderr.log。'
        usage.update(measurement_status='complete', total_tokens=0, model_calls=0)
        _save(root / 'usage.json', usage)
    elif returncode not in (None, 0) and not error:
        error = '原生执行进程退出，exit=' + str(returncode) + '；详见stderr.log。'
    response = None
    if (root / "response.json").is_file():
        try:
            response = _load(root / "response.json")
        except (OSError, ValueError) as exception:
            error = (error + "; " if error else "") + "response: " + str(exception)
    if response is not None and (not isinstance(response, dict) or response.get("error")
                                 or response.get("ok") is False or response.get("success") is False
                                 or response.get("status") in ("failed", "error", "timeout", "timed_out")):
        error = (error + "; " if error else "") + "native_consumer_reported_error"
    # A recovered response does not invent the lost host exit code.  Retain any
    # native consumer failure/cleanup error already recorded in its own receipt.
    host_path = root / "openclaw_transport" / "host_receipt.json"
    if recovered and host_path.is_file():
        host = _load(host_path)
        if host.get("status") in ("failed", "timeout") or host.get("cleanup_error"):
            error = (error + "; " if error else "") + "native_host_reported_error"
    completed = (returncode == 0 or recovered) and response is not None and not error
    result = {
        "status": "dispatched_unresolved" if unresolved else "completed" if completed else "failed",
        "delivery_status": "not_evaluated", "episode_dir": str(root), "finished_at": _now(),
        "returncode": returncode, "error": error, "seconds": seconds,
        "recording_errors": list(recording_errors), "response": response, "usage": usage,
        "dispatch_state": 'not_started' if not_started else 'native_consumer_started',
        "execution": _load(root / "execution.json") if (root / "execution.json").is_file() else {},
    }
    if recovered:
        result["recovered_without_model_call"] = True
        result["completion_basis"] = "saved_response_and_original_consumer_exited"
    _save(root / "result.json", result)
    return result


def _adopt(root: Path) -> dict:
    claim = _load(root / "dispatch.json")
    record = _load(root / "process.json") if (root / "process.json").is_file() else {}
    try:
        started = datetime.fromisoformat(claim["started_at"]).timestamp()
    except (KeyError, TypeError, ValueError):
        started = 0
    deadline = started + TIMEOUT
    state = _process_state(record)
    while state == "running" and time.time() < deadline:
        time.sleep(max(0, min(1, deadline - time.time())))
        state = _process_state(record)
    if state == "exited" and (root / "response.json").is_file():
        return _finish(root, Path(claim["event_file"]), claim["event_start_offset"],
                       returncode=None, error=None, seconds=max(0, time.time() - started), recovered=True)
    return {
        "status": "dispatched_unresolved", "episode_dir": str(root),
        "consumer_state": state,
        "error": "Original episode has no settled terminal response; preserved without automatic reissue.",
        "usage": _load(root / "usage.json") if (root / "usage.json").is_file() else {
            "measurement_status": "unknown", "total_tokens": None, "model_calls": None,
        },
    }


def run_native(episode_dir: Path, prompt: str, resources: list, skills: list,
               lane_id: int, config: dict) -> dict:
    """Stage and run exactly one existing native OpenClaw consumer.

    ``config`` requires ``lanes_file``; ``python`` may identify the original
    host Python.  Resources are ``{path, mount}``, skills are ``{id, path}``.
    The caller must reserve the lane exclusively.  Consumer defaults are never
    used: image, 1800-second episode, native Docker and original credentials are
    explicit.  The 32768 reply budget comes from those unchanged credentials.

    Existing results are reused.  An existing dispatch is adopted without a new
    call: wait for its original consumer within the original remaining budget,
    then consume a saved response.  Missing or ambiguous outcomes stay unknown.
    Usage completeness never blocks completion.
    """
    root = Path(episode_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    result_path = root / "result.json"
    if result_path.is_file():
        return _load(result_path)
    claim_path = root / "dispatch.json"
    if claim_path.exists():
        return _adopt(root)
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Task prompt is empty")
    if type(lane_id) is not int:
        raise ValueError("lane_id must be an integer")
    lanes = _load(Path(config["lanes_file"]))
    lane = next(item for item in lanes if item["id"] == lane_id)
    profile_ref = lane["profile"]
    profile = _load(Path(profile_ref["path"] if isinstance(profile_ref, dict) else profile_ref))
    consumer = Path(profile["runtime_dir"]) / "consumer.py"
    credentials = Path(lane["credentials"])
    model = _load(credentials)
    if model.get("model") != MODEL or model.get("max_tokens") != MAX_TOKENS:
        raise ValueError("Original lane model/reply budget differs from glm-5.3-flash/32768")
    del model
    event_file = Path(profile["event_file"])
    workspace = root / "workspace"
    workspace.mkdir(exist_ok=True)
    staged_resources, staged_skills = [], []
    seen_mounts, seen_skills = set(), set()
    for item in resources:
        mount = _relative_mount(item["mount"])
        if mount.as_posix().casefold() in seen_mounts:
            raise ValueError("Duplicate resource destination: " + str(mount))
        seen_mounts.add(mount.as_posix().casefold())
        target = workspace / mount
        _copy(Path(item["path"]).resolve(), target)
        staged_resources.append({"path": str(target), "mount": mount.as_posix()})
    for item in skills:
        skill_id = item["id"]
        if not isinstance(skill_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", skill_id):
            raise ValueError("Invalid skill directory name")
        if skill_id in seen_skills:
            raise ValueError("Duplicate skill id: " + skill_id)
        seen_skills.add(skill_id)
        target = workspace / "learned_skills" / skill_id
        _copy(Path(item["path"]).resolve(), target)
        staged_skills.append({"id": skill_id, "path": str(target), "files": _skill_files(target)})
    request = {
        "protocol": "native-openclaw-only-v1", "stage": "generation",
        "task_id": root.name, "input": prompt,
        "context": [SKILL_NOTICE] if staged_skills else [],
        "followup_inputs": [], "required_commands": ["python", "openclaw"],
        "resources": staged_resources, "learned_skills": staged_skills,
    }
    request_path, response_path = root / "request.json", root / "response.json"
    _save(request_path, request)
    if response_path.exists() or (root / "openclaw_transport").exists():
        raise ValueError("Native execution artifacts already exist; do not reissue this episode")
    execution = {
        "image": IMAGE, "openclaw_version": OPENCLAW_VERSION, "model": MODEL,
        "max_tokens": MAX_TOKENS, "timeout_seconds": TIMEOUT,
        "backend": "native", "lane": lane_id, "consumer": str(consumer),
        "credentials": str(credentials), "profile": str(profile_ref["path"] if isinstance(profile_ref, dict) else profile_ref),
        "custom_agent_loop": False,
    }
    _save(root / "execution.json", execution)
    command = [str(config.get("python", sys.executable)), "-B", "-X", "utf8", str(consumer),
               str(request_path), str(response_path), "--image", IMAGE,
               "--timeout", str(TIMEOUT), "--credentials", str(credentials), "--backend", "native"]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PATH"] = str(DOCKER_DIR) + os.pathsep + env.get("PATH", "")
    start_offset = _event_offset(event_file)
    claim = {"started_at": _now(), "owner_pid": os.getpid(), "lane": lane_id,
             "event_start_offset": start_offset, "event_file": str(event_file)}
    # This is the sole admission state, not a source/freeze/validation gate.
    with claim_path.open("x", encoding="utf-8") as stream:
        json.dump(claim, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    started = time.monotonic()
    returncode, error, process = None, None, None
    recording_errors = []
    try:
        with (root / "stdout.log").open("xb") as stdout, (root / "stderr.log").open("xb") as stderr:
            process = subprocess.Popen(
                command, cwd=workspace, env=env, stdout=stdout, stderr=stderr,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                _save(root / "process.json", {"pid": process.pid, "create_time": _process_birth(process.pid),
                                              "started_at": _now(), "command": command})
            except OSError as exception:
                # A status-file failure must not abandon a running paid session.
                recording_errors.append("process_status: " + type(exception).__name__ + ": " + str(exception))
            returncode = process.wait()
    except Exception as exception:
        error = type(exception).__name__ + ": " + str(exception)
    # A short passive flush observes already incurred work, never another call.
    if process is not None:
        time.sleep(1)
    return _finish(root, event_file, start_offset, returncode=returncode, error=error,
                   seconds=time.monotonic() - started, recording_errors=recording_errors,
                   unresolved=process is not None and returncode is None)
