"""Prepare existing production/read evidence for the ordinary native review.

No model calls, acceptance rules, skill edits or native-tool changes live here.
Observations describe saved tool results; they never decide ``resource_used``.
"""
from __future__ import annotations

import ast
import hashlib
import json
import posixpath
import re
import shlex
from pathlib import Path


_SKILL_PREFIXES = (
    "/workspace/learned_skills/", "/workspace/skills/",
    "/workspace/.claude/skills/",
)
_PRIVATE = re.compile(r"(?i)(?:credential|api[_-]?key|access[_-]?token|private[_-]?key|\.env$)")


def _load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        return None


def _save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _name(value):
    return re.sub(r"[^\w.-]+", "_", str(value)).strip("._") or "unknown"


def _message(row):
    return row.get("message", row) if isinstance(row, dict) else {}


def _visible(message):
    content = message.get("content", [])
    if isinstance(content, str):
        return content
    return "\n".join(x.get("text", "") for x in content
                     if isinstance(x, dict) and x.get("type") == "text")


def _path(value, cwd="/workspace"):
    if not isinstance(value, str) or not value or "$" in value or any(x in value for x in "*?[]"):
        return None
    return posixpath.normpath(value if value.startswith("/") else posixpath.join(cwd, value))


def _skill(path, roots):
    return bool(path and any(path.startswith(root.rstrip("/") + "/") for root in roots))


def _success(message):
    if message is None:
        return None
    details = message.get("details") or {}
    if not isinstance(details, dict):
        details = {}
    if message.get("isError") is True or details.get("status") in ("error", "failed", "cancelled", "timeout"):
        return False
    code = details.get("exitCode", details.get("exit_code"))
    if code is not None:
        return code == 0
    if details.get("status") in ("running", "pending"):
        return None
    if message.get("isError") is False:
        return True
    return None


def _truncated(message, text):
    details = (message or {}).get("details") or {}
    if isinstance(details, dict):
        for key in ("truncated", "outputTruncated", "contentTruncated"):
            if isinstance(details.get(key), bool):
                return details[key]
    if re.search(r"(?im)(?:^\[?output (?:was )?truncated|\[\.\.\.\s*truncated|\[truncated|^\[Showing lines .*of|^\[Output .*truncat)", text):
        return True
    return None


def _shell_read_outcome(command, text, tool_ok):
    """Do not let an echo/last subcommand mask a failed read in the shell."""
    if tool_ok is not True:
        return tool_ok
    if re.search(r"(?im)^(?:cat|sed|head|tail|less|more):.*(?:No such file|not found|cannot open|Permission denied)", text):
        return False
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split, lexer.commenters = True, ""
        tokens = list(lexer)
    except ValueError:
        return None
    if tokens and posixpath.basename(tokens[0]) in ("bash", "sh", "zsh") and "-c" in tokens:
        index = tokens.index("-c")
        return _shell_read_outcome(tokens[index + 1], text, tool_ok) if len(tokens) > index + 1 else None
    # A complete multi-command tool result proves neither which file was
    # returned nor whether each read succeeded. Keep the original lines for review.
    if any(token in (";", "&&", "||", "|", "&") for token in tokens) or "\n" in command:
        return None
    return True


def _python_read_paths(code, cwd, roots):
    """Recognize literal file reads, not arbitrary mentions inside Python strings."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return []
    result = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # open('...','r') reads in the process, but does not prove model receipt.
        if isinstance(node.func, ast.Name) and node.func.id == "open" and node.args:
            mode = node.args[1] if len(node.args) > 1 else next(
                (k.value for k in node.keywords if k.arg == "mode"), ast.Constant(value="r"))
            if not isinstance(mode, ast.Constant) or any(x in str(mode.value) for x in "wax+"):
                continue
            value = node.args[0]
        elif isinstance(node.func, ast.Attribute) and node.func.attr in ("read_text", "read_bytes"):
            owner = node.func.value
            if not isinstance(owner, ast.Call) or not owner.args:
                continue
            value = owner.args[0]
        else:
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            path = _path(value.value, cwd)
            if _skill(path, roots):
                result.append((path, "read_in_process", False))
    return result


def _shell_resources(command, cwd, roots):
    """Conservative shell syntax recognition; successful wrappers can mask subcommands."""
    found = []
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return []
    segments, current = [], []
    for token in tokens:
        if token in (";", "&&", "||", "|", "&"):
            if current:
                segments.append(current)
            current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    for segment in segments:
        while segment and re.match(r"^[A-Za-z_][\w]*=", segment[0]):
            segment = segment[1:]
        if not segment:
            continue
        tool = posixpath.basename(segment[0])
        if tool == "cd" and len(segment) > 1:
            cwd = _path(segment[1], cwd) or cwd
            continue
        if tool in ("bash", "sh", "zsh") and "-c" in segment:
            index = segment.index("-c")
            if len(segment) > index + 1:
                found.extend(_shell_resources(segment[index + 1], cwd, roots))
            continue
        if tool in ("cat", "sed", "head", "tail", "less", "more"):
            # cat > file is creation. Listing, echo and stat never count as reads.
            if ">" in segment or ">>" in segment:
                segment = segment[:next(i for i, x in enumerate(segment) if x in (">", ">>"))]
            for value in segment[1:]:
                if value.startswith("-") or value in ("<", ">", ">>", "2>", "2>&1"):
                    continue
                if tool == "sed" and re.fullmatch(r"[0-9,$]+[a-z]", value):
                    continue
                path = _path(value, cwd)
                if _skill(path, roots):
                    found.append((path, "read", tool != "cat"))
        elif re.fullmatch(r"python(?:\d+(?:\.\d+)*)?|node|ruby|perl|bash|sh|zsh", tool):
            if "-c" in segment and tool.startswith("python"):
                index = segment.index("-c")
                if len(segment) > index + 1:
                    found.extend(_python_read_paths(segment[index + 1], cwd, roots))
            else:
                # The first non-option argument is the executed program, not its data args.
                candidate = next((x for x in segment[1:] if not x.startswith("-")), None)
                path = _path(candidate, cwd)
                if _skill(path, roots):
                    found.append((path, "exec_resource", False))
        elif tool in ("cp", "install"):
            for value in segment[1:-1]:
                path = _path(value, cwd)
                if _skill(path, roots):
                    found.append((path, "copy_resource", False))
        else:
            # A builtin/executable name in a skill working directory is not a
            # skill resource. Only explicit relative/absolute executable paths.
            path = _path(segment[0], cwd) if "/" in segment[0] else None
            if _skill(path, roots):
                found.append((path, "exec_resource", False))
    # Python heredocs are common; parse the saved source without executing it.
    for match in re.finditer(r"(?ms)\bpython\d*\s*[^\n]*<<\s*['\"]?(\w+)['\"]?[^\n]*\n(.*?)\n\1(?:\n|$)", command):
        found.extend(_python_read_paths(match.group(2), cwd, roots))
    return list(dict.fromkeys(found))


def read_usage_evidence(session_events, *, skill_roots=()):
    """Summarize actual saved tool results with 1-based source line references.

    Missing/failed returns remain unknown/false. A successful exec describes the
    whole command only. No automatic assertion that every subcommand succeeded,
    a complete file reached the model, or the resource improved delivery is made.
    """
    source = Path(session_events)
    roots = tuple(skill_roots) or _SKILL_PREFIXES
    calls, results, read_errors = [], {}, []
    try:
        stream = source.open(encoding="utf-8-sig")
    except OSError as exc:
        return {"source": str(source), "observations": [], "source_errors": [type(exc).__name__],
                "summary": {"read_attempts": 0, "read_successes": 0, "exec_resource_attempts": 0}}
    with stream:
        for line, raw in enumerate(stream, 1):
            try:
                message = _message(json.loads(raw))
            except (ValueError, TypeError):
                read_errors.append({"line": line, "error": "invalid_json"})
                continue
            if message.get("role") == "assistant":
                content = message.get("content", [])
                for part in content if isinstance(content, list) else []:
                    if isinstance(part, dict) and part.get("type") in ("toolCall", "tool_call"):
                        calls.append((line, part))
            elif message.get("role") in ("toolResult", "tool"):
                call_id = message.get("toolCallId", message.get("tool_call_id"))
                if call_id:
                    results[str(call_id)] = (line, message)
    observations = []
    followups = {}
    for follow_line, follow_call in calls:
        follow_args = follow_call.get("arguments", follow_call.get("input", {}))
        if (str(follow_call.get("name", "")).split(".")[-1] != "process"
                or not isinstance(follow_args, dict)
                or follow_args.get("action") not in ("poll", "log")):
            continue
        session_id = follow_args.get("sessionId", follow_args.get("session_id"))
        follow_result = results.get(str(follow_call.get("id", "")))
        if session_id and follow_result:
            followups.setdefault(str(session_id), []).append(follow_result)
    for line, call in calls:
        args = call.get("arguments", call.get("input", {}))
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                continue
        if not isinstance(args, dict):
            continue
        tool = str(call.get("name", "")).split(".")[-1]
        result_line, result = results.get(str(call.get("id", "")), (None, None))
        text = _visible(result or {})
        ok = _success(result)
        details = (result or {}).get("details") or {}
        cwd = details.get("cwd", "/workspace") if isinstance(details, dict) else "/workspace"
        completed_line, followup_lines = result_line, []
        session_id = details.get("sessionId") if isinstance(details, dict) else None
        for followup_line, followup_result in followups.get(str(session_id), []) if session_id else []:
            if followup_line <= (result_line or line):
                continue
            followup_lines.append(followup_line)
            text += "\n" + _visible(followup_result)
            if _success(followup_result) is not None:
                ok, completed_line = _success(followup_result), followup_line
        candidates = []
        if tool in ("read", "read_file"):
            path = _path(args.get("path", args.get("file_path", args.get("filePath"))), cwd)
            if _skill(path, roots):
                candidates.append((path, "read", any(args.get(k) is not None for k in ("offset", "limit", "start_line", "end_line"))))
        elif tool in ("exec", "shell", "bash", "exec_command"):
            command = args.get("command", args.get("cmd", args.get("script", "")))
            if isinstance(command, str):
                candidates = _shell_resources(command, cwd, roots)
        for path, operation, partial in candidates:
            read_ok = (ok if operation == "read" and result is not None else None)
            if operation == "read" and tool in ("exec", "shell", "bash", "exec_command"):
                read_ok = _shell_read_outcome(command, text, ok)
            observation = {
                "resource_path": path, "operation": operation, "tool": tool,
                "tool_call_id": call.get("id"), "call_line": line, "result_line": result_line,
                "completion_line": completed_line, "followup_result_lines": followup_lines,
                "source_ref": str(source) + ":" + str(completed_line or line),
                "tool_succeeded": ok, "success_scope": "whole_tool_result",
                "read_attempted": operation in ("read", "read_in_process"),
                "read_succeeded": read_ok,
                "exec_resource_invoked": operation == "exec_resource",
                "exec_resource_succeeded": None,
                "content_delivery": ("some_text_returned" if text.strip() not in ("", "(no output)") and read_ok is True and operation == "read" else "not_confirmed"),
                "visible_text_chars": len(text),
                "visible_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if result is not None else None,
                "read_truncated": _truncated(result, text), "partial_requested": partial,
                "full_content_received": None,
            }
            # Report useful generic execution receipts, never business paragraphs.
            receipts = re.findall(r"(?i)\b(?:extracted|processed|saved)\s+\d+\s+(?:paragraphs|rows|pages|files|records)\b", text)
            if receipts:
                observation["result_receipts"] = list(dict.fromkeys(receipts))
            if operation == "exec_resource":
                observation["execution_note"] = "命令已调用资源；tool_succeeded仅指整个工具命令，不单独保证子程序或业务成功。"
            observations.append(observation)
    return {
        "source": str(source), "source_errors": read_errors, "observations": observations,
        "summary": {
            "read_attempts": sum(o["read_attempted"] for o in observations),
            "read_successes": sum(o["read_succeeded"] is True for o in observations),
            "read_failures": sum(o["read_succeeded"] is False for o in observations),
            "exec_resource_attempts": sum(o["exec_resource_invoked"] for o in observations),
            "exec_tool_successes": sum(o["exec_resource_invoked"] and o["tool_succeeded"] is True for o in observations),
            "copy_resource_attempts": sum(o["operation"] == "copy_resource" for o in observations),
        },
        "limitations": ["仅解析已保存轨迹，不用skill_reads空摘要作未读结论。", "目录列举、失败请求不算成功读取。",
                        "未估计全文送达；成功exec只证明整条命令返回，不自动判资源已有效复用。"],
    }


def build_read_usage_evidence(episode, workdir, *, mount="inputs/read_usage_evidence.json", skill_roots=(), source_mount=None):
    evidence = read_usage_evidence(Path(episode) / "openclaw_transport/session_events.jsonl", skill_roots=skill_roots)
    # The existing reviewer mounts this original trace next to the evidence.
    native_trace = "/workspace/" + (source_mount or posixpath.join(
        posixpath.dirname(mount), "openclaw_transport/session_events.jsonl")).lstrip("/")
    evidence["source_host"] = evidence["source"]
    evidence["source"] = native_trace
    for observation in evidence["observations"]:
        observation["source_ref"] = native_trace + ":" + str(observation["completion_line"] or observation["call_line"])
    path = _save(Path(workdir) / "read_usage_evidence.json", evidence)
    return {"resource": {"path": str(path.resolve()), "mount": mount}, "evidence": evidence}


def collect_making_evidence(route_id, jobs, workdir):
    """Return resources/attempt descriptions from finished make work, including history.

    Does not make a manifest or add a validation stage. All mounted paths are
    explicit /workspace/inputs/making/... references for the existing reviewer.
    The original result is projected to omit execution.credentials/profile.
    """
    resources, attempts, records, seen_files, seen_episodes = [], [], [], {}, set()

    def add(path, mount):
        path = Path(path)
        if (not path.is_file() or path.is_symlink() or _PRIVATE.search(path.name)
                or {"private", "secrets", "credentials"}.intersection(x.lower() for x in path.parts)):
            return None
        key = str(path.resolve()).casefold()
        if key in seen_files:
            return seen_files[key]
        seen_files[key] = "/workspace/" + mount
        resources.append({"path": str(path.resolve()), "mount": mount})
        return "/workspace/" + mount

    def previous_episodes(value):
        if not isinstance(value, dict):
            return []
        found = [value[k] for k in ("episode", "episode_dir") if value.get(k)]
        for key in ("previous", "payload", "result"):
            child = value.get(key)
            if isinstance(child, str):
                try:
                    child = json.loads(child)
                except ValueError:
                    continue
            found.extend(previous_episodes(child))
        return found

    for job in jobs:
        if job.get("kind") != "make" or job.get("route_id") != route_id:
            continue
        episodes = []
        for value in previous_episodes(job):
            ep = Path(value)
            episodes.extend(sorted(ep.parent.glob("attempt_*")) if re.fullmatch(r"attempt_\d+", ep.name) else [ep])
        for ep in episodes:
            identity = str(ep.resolve()).casefold()
            if identity in seen_episodes:
                continue
            seen_episodes.add(identity)
            result = _load(ep / "result.json") or {}
            if not result or result.get("status") in ("running", "pending", "unknown") or not result.get("finished_at"):
                continue
            # Review roots already contain the long job identity. Repeating it
            # here can exceed Windows path limits before OpenClaw is started.
            # Keep the full identity below; only the mounted directory is short.
            tag = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
            prefix = "inputs/making/" + tag
            row = {"job_id": job.get("id"), "episode": str(ep), "attempt": ep.name,
                   "status": result.get("status"), "evidence_paths": []}
            outputs = ep / "workspace/outputs"
            if outputs.is_dir():
                for path in sorted(outputs.rglob("*")):
                    if {"__pycache__", ".git", ".pytest_cache"}.intersection(path.parts):
                        continue
                    native = add(path, prefix + "/workspace/outputs/" + path.relative_to(outputs).as_posix())
                    if native:
                        row["evidence_paths"].append(native)
                        if path == outputs / "making.json":
                            row["making_record"] = native
                            records.append(native)
            # Include input/tmp files actually named in the recorded program runs.
            making = _load(outputs / "making.json") or {}
            run_text = json.dumps(making.get("program_runs", []), ensure_ascii=False)
            for name in re.findall(r"/workspace/(?:inputs|tmp)/[^\s\"'`<>]+", run_text):
                relative = Path(name.removeprefix("/workspace/"))
                path = ep / "workspace" / relative
                if ".." in relative.parts or "conversations" in relative.parts:
                    continue
                native = add(path, prefix + "/workspace/" + relative.as_posix())
                if native:
                    row["evidence_paths"].append(native)
            for rel in ("openclaw_transport/session_events.jsonl",):
                native = add(ep / rel, prefix + "/" + rel)
                if native:
                    row["evidence_paths"].append(native)
            response = _load(ep / "response.json")
            if isinstance(response, dict):
                projection = {k: response[k] for k in ("answer", "turn_answers", "artifacts") if k in response}
                path = _save(Path(workdir) / "making_evidence" / tag / "response.json", projection)
                native = add(path, prefix + "/response.json")
                if native:
                    row["evidence_paths"].append(native)
            request = _load(ep / "request.json")
            if isinstance(request, dict):
                # No source host paths, credential/profile/config payloads in this view.
                projection = {k: request[k] for k in ("protocol", "stage", "task_id", "input") if k in request}
                projection["resource_mounts"] = [r.get("mount") for r in request.get("resources", []) if isinstance(r, dict)]
                path = _save(Path(workdir) / "making_evidence" / tag / "request.json", projection)
                native = add(path, prefix + "/request.json")
                if native:
                    row["evidence_paths"].append(native)
            projection = {k: result[k] for k in ("status", "delivery_status", "finished_at", "returncode", "error", "seconds", "recording_errors") if k in result}
            path = _save(Path(workdir) / "making_evidence" / tag / "result.json", projection)
            native = add(path, prefix + "/result.json")
            if native:
                row["evidence_paths"].append(native)
            attempts.append(row)
    return {"resources": resources, "attempts": attempts, "making_records": records}
