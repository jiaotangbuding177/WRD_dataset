#!/usr/bin/env python3
"""Verify an archived return and index terminal evidence without running its artifacts."""
from __future__ import annotations

import argparse
import base64
import binascii
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import zipfile


HEX_SHA256 = re.compile(r"[0-9a-f]{64}")
ATTEMPT_PATH = re.compile(r"^(runs/([^/]+)/([^/]+)/attempt-(\d+))/")
MUTATION_TOOLS = {"write", "file_write", "edit", "apply_patch"}
TRANSPORT_ERRORS = {
    "URLError", "TimeoutError", "ConnectionError", "ConnectionResetError",
    "ConnectionRefusedError", "BrokenPipeError", "IncompleteRead",
    "RemoteDisconnected", "ConnectTimeout", "ReadTimeout", "ReadError",
    "WriteError", "RemoteProtocolError", "SSLError",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clean_name(name: str) -> bool:
    return bool(name) and not any(c in name for c in ("\\", ":", "\x00")) and all(
        part not in {"", ".", ".."} for part in name.split("/")
    )


class ReturnArchive:
    def __init__(self, archive: zipfile.ZipFile):
        self.archive = archive
        self.members = {}
        folded = set()
        for item in archive.infolist():
            name = item.filename
            file_type = stat.S_IFMT(item.external_attr >> 16)
            if (not clean_name(name) or name.casefold() in folded
                    or file_type not in {0, stat.S_IFREG} or item.is_dir()):
                raise ValueError(f"Unsafe or duplicate ZIP member: {name!r}")
            folded.add(name.casefold())
            self.members[name] = item

        self.hashes = {}
        for line in self.read("SHA256SUMS").decode("utf-8-sig").splitlines():
            pin, sep, name = line.partition("  ")
            if not sep or not HEX_SHA256.fullmatch(pin) or name in self.hashes:
                raise ValueError("Invalid or duplicate SHA256SUMS entry")
            self.hashes[name] = pin
        if set(self.members) - {"SHA256SUMS"} != set(self.hashes):
            raise ValueError("SHA256SUMS does not cover exactly the returned members")
        for name, pin in self.hashes.items():
            with self.archive.open(self.members[name]) as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != pin:
                raise ValueError(f"SHA256 mismatch: {name}")

    def read(self, name):
        return self.archive.read(self.members[name])

    def json(self, name, default=None):
        if name not in self.members:
            return default
        value = json.loads(self.read(name).decode("utf-8-sig"))
        if not isinstance(value, dict):
            raise ValueError(f"Expected JSON object: {name}")
        return value

    def pin(self, name):
        if name not in self.hashes:
            return None
        return {"path": name, "sha256": self.hashes[name], "bytes": self.members[name].file_size}


def workspace_path(value, cwd="/workspace"):
    if not isinstance(value, str) or not value:
        return None
    path = PurePosixPath(value)
    if not path.is_absolute():
        path = PurePosixPath(cwd) / path
    if not path.is_relative_to("/workspace"):
        return None
    rel = path.relative_to("/workspace").as_posix()
    return rel if clean_name(rel) else None


def command_identity(command, cwd):
    if not isinstance(command, str) or not command:
        return None
    return sha(json.dumps([cwd, command], ensure_ascii=False).encode("utf-8"))


def exec_evidence(args, details, is_error):
    command = args.get("command")
    cwd = details.get("cwd") or args.get("workdir")
    cwd = cwd if isinstance(cwd, str) else "/workspace"
    exit_code = details.get("exitCode")
    exit_code = exit_code if type(exit_code) is int else None
    try:
        tokens = shlex.split(command) if isinstance(command, str) else []
        references = [workspace_path(token, cwd) for token in tokens]
    except ValueError:
        references = []
    if details.get("timedOut") is True or details.get("exitSignal") or details.get("exitReason") in {
        "overall-timeout", "no-output-timeout",
    }:
        status = "TERMINATED"
    elif exit_code is not None and exit_code != 0:
        status = "NONZERO_EXIT"
    elif exit_code == 0 and details.get("status") == "completed" and is_error is False:
        status = "ZERO_EXIT"
    elif details.get("status") == "running" and is_error is False:
        status = "RUNNING"
    elif is_error is True:
        status = "TOOL_ERROR"
    else:
        status = "EXIT_UNCONFIRMED"
    return {
        "command_sha256": command_identity(command, cwd),
        "direct_workspace_path_tokens": sorted(set(filter(None, references))),
        "status": status,
        "exit_code": exit_code,
        "exit_reason": details.get("exitReason"),
        "process_session_id": details.get("sessionId"),
    }


def trace_audit(archive, prefix, artifacts):
    traces = [prefix + "/openclaw_transport/" + name for name in (
        "all_session_events.jsonl", "session_events.jsonl",
    )]
    path = next((name for name in traces if name in archive.hashes), None)
    if path is None:
        return {"trace": None, "mutations": [], "commands": [], "repair_sequences": []}

    pending, mutations, commands, repairs, versions, previous_failure, processes = {}, [], [], [], {}, {}, {}
    malformed = 0
    unmatched_returns = 0
    for line_number, line in enumerate(archive.read(path).decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            native = row.get("native_event", row)
            message = native.get("message", {})
            if not isinstance(message, dict):
                raise ValueError("non-object native message")
        except (AttributeError, ValueError):
            malformed += 1
            continue

        session = row.get("session_id") or native.get("sessionId") or "root"
        content = message.get("content", [])
        if message.get("role") == "assistant" and isinstance(content, list):
            for item in content:
                if not isinstance(item, dict) or item.get("type") != "toolCall":
                    continue
                tool = item.get("name")
                if isinstance(tool, str) and tool in MUTATION_TOOLS | {"exec", "process"} and isinstance(item.get("id"), str):
                    args = item.get("arguments")
                    pending[(session, item["id"])] = (
                        tool, args if isinstance(args, dict) else {}, line_number,
                    )
        if message.get("role") != "toolResult":
            continue
        tool, call_id = message.get("toolName"), message.get("toolCallId")
        if not isinstance(tool, str) or tool not in MUTATION_TOOLS | {"exec", "process"} or not isinstance(call_id, str):
            continue
        call = pending.pop((session, call_id), None)
        if not call or call[0] != tool:
            unmatched_returns += 1
            continue

        _, args, call_line = call
        details = message.get("details")
        details = details if isinstance(details, dict) else {}
        is_error = message.get("isError")
        evidence = {"session_id": session, "tool": tool, "call_id": call_id,
                    "call_line": call_line, "return_line": line_number, "is_error": is_error}
        if tool in MUTATION_TOOLS:
            target = workspace_path(args.get("path") or args.get("file_path"))
            write_acknowledged = isinstance(content, list) and any(
                isinstance(item, dict) and isinstance(item.get("text"), str)
                and item["text"].startswith("Successfully wrote ") for item in content
            )
            confirmed = is_error is False and (type(details.get("changed")) is bool or write_acknowledged)
            value = args.get("content")
            written_sha = None
            if confirmed and tool == "write" and isinstance(value, str):
                written_sha = sha(value.encode("utf-8"))
            if confirmed and tool == "file_write" and isinstance(args.get("contentBase64"), str):
                try:
                    written_sha = sha(base64.b64decode(args["contentBase64"], validate=True))
                except (binascii.Error, ValueError):
                    pass
            prior_sha = versions.get((session, target))
            changed = confirmed and (details.get("changed") is True or (
                written_sha is not None and prior_sha is not None and prior_sha != written_sha
            ))
            if confirmed and target:
                versions[(session, target)] = written_sha
            final = artifacts.get(target)
            mutations.append(evidence | {
                "workspace_path": target,
                "write_confirmed": confirmed,
                "change_observed": changed,
                "prior_observed_write_sha256": prior_sha,
                "whole_write_content_sha256": written_sha,
                "matches_returned_artifact": final["sha256"] == written_sha if final and written_sha else None,
            })
            continue

        if tool == "process":
            process_id = args.get("sessionId")
            previous = (processes.get((session, process_id))
                        if args.get("action") == "poll" and isinstance(process_id, str) else None)
            if previous:
                evidence.update(exec_evidence(previous[0], details, is_error))
                evidence["originating_exec_call_line"] = previous[1]
            else:
                evidence.update(exec_evidence({}, details, is_error))
        else:
            evidence.update(exec_evidence(args, details, is_error))
            process_id = evidence.get("process_session_id")
            if evidence["status"] == "RUNNING" and isinstance(process_id, str):
                processes[(session, process_id)] = (args, call_line)
        commands.append(evidence)

        fingerprint = evidence["command_sha256"]
        if not fingerprint:
            continue
        key = (session, fingerprint)
        if evidence["status"] == "NONZERO_EXIT":
            previous_failure[key] = evidence
        elif evidence["status"] == "ZERO_EXIT" and key in previous_failure:
            failure = previous_failure.pop(key)
            invocation_line = evidence.get("originating_exec_call_line", call_line)
            changed_paths = [m for m in mutations if (
                m["session_id"] == session and m["change_observed"]
                and failure["return_line"] < m["return_line"] < invocation_line
                and m["workspace_path"] in evidence["direct_workspace_path_tokens"]
            )]
            if changed_paths:
                repairs.append({"failed_return_line": failure["return_line"],
                                "changed_return_lines": [m["return_line"] for m in changed_paths],
                                "zero_exit_return_line": line_number,
                                "command_sha256": fingerprint,
                                "functional_pass": None})

    # Only report tokens that identify observed workspace files. Arbitrary shell
    # arguments can contain customer input and are not useful as path evidence.
    known_paths = set(artifacts) | {m["workspace_path"] for m in mutations if m["workspace_path"]}
    for command in commands:
        command["direct_workspace_path_tokens"] = sorted(known_paths.intersection(command["direct_workspace_path_tokens"]))
    return {"trace": archive.pin(path), "mutations": mutations, "commands": commands,
            "repair_sequences": repairs, "malformed_lines": malformed,
            "unmatched_tool_returns": unmatched_returns, "unreturned_tool_calls": len(pending)}


def meter_audit(archive, prefix, result):
    ledger = archive.json(prefix + "/budget.json") or (result or {}).get("budget") or {}
    calls = ledger.get("calls", {})
    if not isinstance(calls, dict):
        raise ValueError(f"Invalid calls ledger: {prefix}")
    exact = unknown = io = completion = unknown_io = unknown_completion = 0
    gaps = []
    prompt = reasoning = cache = prompt_count = reasoning_count = cache_count = 0
    for call_id, call in calls.items():
        if not isinstance(call, dict):
            raise ValueError(f"Invalid ledger call: {prefix}")
        charged_io = call.get("charged_io")
        charged_completion = call.get("charged_completion")
        if call.get("usage_state") == "EXACT" and type(charged_io) is int and charged_io >= 0:
            exact += 1
            io += charged_io
        else:
            unknown += 1
            if type(charged_io) is int and charged_io >= 0:
                unknown_io += charged_io
            else:
                gaps.append({"call_id": call_id, "reason": "invalid_or_absent_io_charge"})
        if type(charged_completion) is int and charged_completion >= 0:
            if call.get("completion_usage_state") == "EXACT":
                completion += charged_completion
            else:
                unknown_completion += charged_completion

    http_prefix = prefix + "/model_http/"
    responses = []
    for name in sorted(n for n in archive.hashes if n.startswith(http_prefix) and n.endswith("/receipt.json")):
        value = archive.json(name)
        call_dir = name.removesuffix("/receipt.json")
        call_id = call_dir.rsplit("/", 1)[1]
        binding = {}
        for field in ("request", "response"):
            advertised_sha = value.get(f"{field}_sha256")
            if not advertised_sha:
                continue
            recorded_path = value.get(f"{field}_path")
            basename = str(recorded_path or "").replace("\\", "/").rsplit("/", 1)[-1]
            member = call_dir + "/" + basename
            binding[field] = archive.hashes.get(member) == advertised_sha
            if not binding[field]:
                gaps.append({"call_id": call_id, "reason": f"{field}_hash_unbound"})
        if call_id not in calls:
            gaps.append({"call_id": call_id, "reason": "receipt_without_final_ledger_call"})
        if value.get("call_id") != call_id:
            gaps.append({"call_id": call_id, "reason": "receipt_call_identity_mismatch"})
        usage = value.get("usage")
        call = calls.get(call_id, {})
        if (isinstance(usage, dict) and call.get("usage_state") == "EXACT"
                and value.get("status") == "COMPLETE" and value.get("call_id") == call_id
                and binding.get("response") is True):
            if usage.get("total_tokens") != call.get("charged_io"):
                gaps.append({"call_id": call_id, "reason": "response_usage_differs_from_final_ledger"})
            else:
                input_tokens = usage.get("prompt_tokens")
                if type(input_tokens) is int and input_tokens >= 0:
                    prompt += input_tokens
                    prompt_count += 1
                completion_details = usage.get("completion_tokens_details")
                if isinstance(completion_details, dict):
                    reasoning_tokens = completion_details.get("reasoning_tokens")
                    if type(reasoning_tokens) is int and reasoning_tokens >= 0:
                        reasoning += reasoning_tokens
                        reasoning_count += 1
                prompt_details = usage.get("prompt_tokens_details")
                if isinstance(prompt_details, dict):
                    cached_tokens = prompt_details.get("cached_tokens")
                    if type(cached_tokens) is int and cached_tokens >= 0:
                        cache += cached_tokens
                        cache_count += 1
        responses.append({"call_id": call_id, "receipt": archive.pin(name),
                          "status": value.get("status"), "http_status": value.get("http_status"),
                          "error_type": value.get("error_type"), "raw_bindings": binding})

    admitted = ledger.get("requests_admitted") if ledger else None
    if admitted is not None and admitted != len(calls):
        gaps.append({"reason": "ledger_count_differs_from_admitted"})
    if ledger and set(calls) != {row["call_id"] for row in responses}:
        gaps.append({"reason": "receipt_coverage_differs_from_ledger"})
    return {
        "ledger_present": bool(ledger), "requests_admitted": admitted,
        "exact_usage_calls": exact, "unknown_usage_calls": unknown,
        "exact_io_tokens": io, "exact_completion_tokens": completion,
        "unknown_reserved_io_tokens": unknown_io,
        "unknown_reserved_completion_tokens": unknown_completion,
        "receipt_reported_prompt_tokens": prompt, "receipt_prompt_token_coverage": prompt_count,
        "receipt_reported_reasoning_tokens": reasoning, "receipt_reasoning_token_coverage": reasoning_count,
        "receipt_reported_cached_tokens": cache, "receipt_cached_token_coverage": cache_count,
        "ledger_wall_seconds": ledger.get("elapsed_seconds"),
        "cash": ledger.get("cash"), "receipt_audit": responses, "evidence_gaps": gaps,
    }


def stage_binding(archive, prefix, case, selection_sha, arm, number, result):
    path = prefix + "/stage_receipt.json"
    receipt = archive.json(path)
    dispatch = archive.json(prefix + "/dispatch.json")
    request_sha = archive.hashes.get(prefix + "/request.json")
    if case is None:
        return {"stage_receipt": archive.pin(path), "frozen_input_bound": None}
    problems = []
    if not receipt:
        problems.append("stage_receipt_missing")
        return {"stage_receipt": None, "frozen_input_bound": False, "issues": problems}
    if (receipt.get("schema") != "wrd58-autonomous-stage-v1" or receipt.get("case_id") != case["id"]
            or receipt.get("arm") != arm or receipt.get("attempt") != number
            or receipt.get("source_ids") != case.get("source_ids")
            or receipt.get("selection_sha256") != selection_sha):
        problems.append("stage_identity_differs_from_frozen_case")
    if not request_sha or receipt.get("request_sha256") != request_sha:
        problems.append("initial_request_hash_mismatch")
    request = archive.json(prefix + "/request.json") or {}
    goal = request.get("input")
    if (not isinstance(goal, str) or receipt.get("goal_sha256") != sha(goal.encode("utf-8"))
            or request.get("followup_inputs") != [] or request.get("learned_skills") != []):
        problems.append("initial_goal_or_single_turn_contract_mismatch")
    if dispatch and (dispatch.get("arm") != arm or dispatch.get("request_sha256") != request_sha):
        problems.append("dispatch_identity_or_request_mismatch")
    if result is not None and (result.get("arm") != arm or not dispatch):
        problems.append("result_identity_or_dispatch_unbound")

    files = receipt.get("files", {})
    if not isinstance(files, dict) or not files:
        problems.append("initial_workspace_pins_missing")
        files = {}
    expected_sources = {entry["source_id"]: entry for entry in case.get("sources", [])}
    actual_sources = {entry["source_id"]: entry for entry in receipt.get("sources", [])}
    if not expected_sources or actual_sources.keys() != expected_sources.keys():
        problems.append("source_ids_differ_from_frozen_case")
    for source_id, expected in expected_sources.items():
        actual = actual_sources.get(source_id, {})
        source_path = workspace_path(actual.get("source"))
        index_path = workspace_path(actual.get("resource_index"))
        if (not source_path or files.get(source_path) != expected.get("source_sha256")
                or any(actual.get(key) != expected.get(key) for key in ("case_sha256", "source_sha256"))):
            problems.append(f"source_hashes_diff_from_frozen_case:{source_id}")
        index_name = prefix + "/workspace/" + str(index_path)
        if not index_path or not files.get(index_path) or files[index_path] != archive.hashes.get(index_name):
            problems.append(f"resource_index_unbound:{source_id}")
            continue
        index = archive.json(index_name)
        hashes = []
        for resource in index.get("resources", []):
            mount = workspace_path(resource.get("path"))
            pin = resource.get("sha256")
            if not mount or not isinstance(pin, str) or files.get(mount) != pin:
                problems.append(f"resource_path_or_hash_unbound:{source_id}")
            else:
                hashes.append(pin)
        if sorted(hashes) != sorted(expected.get("resource_sha256", [])):
            problems.append(f"resource_hashes_diff_from_frozen_case:{source_id}")
    changed = sorted(name for name, pin in files.items() if archive.hashes.get(prefix + "/workspace/" + name) != pin)
    identity = {
        "files": files, "git_tree": receipt.get("git_tree"), "goal_sha256": receipt.get("goal_sha256"),
        "budget": receipt.get("budget"),
    }
    return {"stage_receipt": archive.pin(path), "frozen_input_bound": not problems,
            "initial_input_fingerprint": sha(json.dumps(identity, sort_keys=True).encode("utf-8")),
            "initial_files_changed_or_absent_in_return": changed, "issues": problems}


def attempt_audit(archive, prefix, source_id, arm, number, case, selection_sha):
    result_pin = archive.pin(prefix + "/producer_result.json")
    result = archive.json(prefix + "/producer_result.json")
    dispatch = archive.pin(prefix + "/dispatch.json")
    output_prefix = prefix + "/workspace/outputs/"
    outputs = {name.removeprefix(prefix + "/workspace/"): archive.pin(name)
               for name in sorted(archive.hashes) if name.startswith(output_prefix)}
    for item in outputs.values():
        if item["path"].lower().endswith(".png"):
            with archive.archive.open(archive.members[item["path"]]) as stream:
                item["png_signature_present"] = stream.read(8) == b"\x89PNG\r\n\x1a\n"
    skills = sorted(path for path in outputs if path.startswith("outputs/skill/")
                    and PurePosixPath(path).name == "SKILL.md" and outputs[path]["bytes"] > 0)
    manifest_matches = None
    if result is not None and isinstance(result.get("actual_skill_md"), list):
        declared = sorted(str(name).replace("\\", "/") for name in result["actual_skill_md"])
        manifest_matches = declared == skills

    trail = trace_audit(archive, prefix, outputs)
    decisions = []
    for path in ("outputs/evidence/decision.json", "outputs/decision.json"):
        if path not in outputs:
            continue
        try:
            value = archive.json(outputs[path]["path"])
            decision = value.get("decision") or value.get("action") or value.get("status")
            decision = decision.upper() if isinstance(decision, str) else None
            if decision is not None and decision not in {"MAKE", "REUSE", "MERGE", "REVISE", "KEEP", "STOP", "BLOCKED"}:
                decision = "UNRECOGNIZED"
        except ValueError:
            decision = None
        decisions.append({"artifact": outputs[path], "author_declared_action": decision,
                          "matches_native_write": any(m["workspace_path"] == path and m["matches_returned_artifact"]
                                                      for m in trail["mutations"])})

    meter = meter_audit(archive, prefix, result)
    infra = [r for r in meter["receipt_audit"] if r["error_type"] in TRANSPORT_ERRORS]
    returncode = (result or {}).get("returncode")
    if result is None:
        state = ("DISPATCH_WITHOUT_TERMINAL_RESULT" if dispatch or meter["receipt_audit"]
                 else "NOT_DISPATCHED")
    elif skills:
        state = "CANDIDATE_INTERRUPTED" if returncode != 0 else "CANDIDATE_PENDING_FUNCTIONAL_REVIEW"
    elif infra and returncode != 0:
        state = "TRANSPORT_ERROR_WITHOUT_CANDIDATE"
    elif returncode == 0 and any(d["author_declared_action"] in {"STOP", "BLOCKED"} for d in decisions):
        state = "DECLARED_STOP_OR_BLOCKED_PENDING_REVIEW"
    else:
        state = "TERMINAL_INCOMPLETE"
    return {
        "case_id": source_id, "arm": arm, "attempt": number, "state": state,
        "terminal_result": result_pin, "dispatch": dispatch, "returncode": returncode,
        "wall_seconds": (result or {}).get("wall_seconds"), "skill_paths": skills,
        "declared_skill_paths_match": manifest_matches, "outputs": outputs,
        "native": trail, "transport_error_count": len(infra), "usage": meter,
        "author_decision_evidence": decisions,
        "stage_binding": stage_binding(archive, prefix, case, selection_sha, arm, number, result),
        "independent_functional_pass": None, "independent_stop_correct": None,
    }


def frozen_cases(archive):
    selection = archive.json("selection.json", {})
    if "cases" not in selection:
        return {}
    rows = selection["cases"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("Invalid frozen cases list")
    cases = {}
    for row in rows:
        case_id = row.get("id") if isinstance(row, dict) else None
        if not isinstance(case_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", case_id) or case_id in cases:
            raise ValueError("Invalid or duplicate frozen case ID")
        cases[case_id] = row
    return cases


def batch_audit(archive, selection_sha):
    statuses = {}
    for path in sorted(archive.hashes):
        if not re.fullmatch(r"runs/_batch/(?:14b|8b)-\d+\.json", path):
            continue
        batch = archive.json(path)
        if batch.get("selection_sha256") != selection_sha:
            raise ValueError(f"Batch selection SHA mismatch: {path}")
        for row in batch.get("results_so_far", []):
            case_id, arm = row.get("case_id"), row.get("arm")
            if not isinstance(case_id, str) or not isinstance(arm, str):
                raise ValueError(f"Invalid batch identity: {path}")
            statuses[(case_id, arm)] = {
                "batch": archive.pin(path), "launcher_status": row.get("status"),
                "reported_returncode": row.get("returncode"), "error_type": row.get("error_type"),
                "result_sha256": row.get("result_sha256"),
            }
    return statuses


def effect_coverage(cases, attempts, statuses, size):
    observed = {(row["case_id"], row["arm"]) for row in attempts}
    candidate = {(row["case_id"], row["arm"]) for row in attempts if row["skill_paths"]}
    report = {"observed_case_arm_slots": len(observed), "observed_candidate_slots": len(candidate),
              "planned_case_groups": None, "planned_student_slots": None, "slots": [],
              "valid_functional_pairs": None, "status": "REQUIRES_INDEPENDENT_BLIND_FUNCTIONAL_REVIEW"}
    if not cases or size is None:
        return report
    arms = [f"wrd58-{size}-0", f"wrd58-{size}-241"]
    both_terminal = []
    for case_id in cases:
        terminal_pair = []
        for arm in arms:
            key = (case_id, arm)
            batch = statuses.get(key)
            rows = [a for a in attempts if (a["case_id"], a["arm"]) == key]
            latest_batch_hash = batch.get("result_sha256") if batch else None
            terminal = [a for a in rows if a["terminal_result"] is not None]
            batch_matches = (any(a["terminal_result"]["sha256"] == latest_batch_hash for a in terminal)
                             if latest_batch_hash else None)
            status = "UNISSUED"
            if rows:
                status = rows[-1]["state"] if len(rows) == 1 else "MULTIPLE_ATTEMPTS_RETAINED"
            elif batch and batch["launcher_status"] == "DISPATCH_ERROR":
                status = "LAUNCH_ERROR_WITHOUT_ATTEMPT"
            report["slots"].append({"case_id": case_id, "arm": arm, "state": status,
                                    "launcher": batch, "launcher_terminal_hash_matches": batch_matches,
                                    "observed_attempt_count": len(rows), "terminal_attempt_count": len(terminal),
                                    "independent_functional_pass": None})
            if len(rows) == 1 and terminal and terminal[0]["stage_binding"]["frozen_input_bound"] is True:
                terminal_pair.append(terminal[0]["stage_binding"]["initial_input_fingerprint"])
        if len(terminal_pair) == 2 and terminal_pair[0] == terminal_pair[1]:
            both_terminal.append(case_id)
    report.update(planned_case_groups=len(cases), planned_student_slots=len(cases) * len(arms),
                  paired_terminal_cases_with_equal_initial_input=both_terminal)
    return report


def run_audit(archive_path, selection_path, size=None):
    sidecar = archive_path.with_name(archive_path.name + ".sha256")
    fields = sidecar.read_text(encoding="utf-8-sig").split()
    if not fields or not HEX_SHA256.fullmatch(fields[0]):
        raise ValueError("Invalid archive SHA256 sidecar")
    with archive_path.open("rb") as stream:
        archive_sha = hashlib.file_digest(stream, "sha256").hexdigest()
        if fields[0] != archive_sha:
            raise ValueError("Archive SHA256 sidecar mismatch")
        stream.seek(0)
        with zipfile.ZipFile(stream) as zipped:
            archive = ReturnArchive(zipped)
            prefixes = {}
            for name in archive.hashes:
                match = ATTEMPT_PATH.match(name)
                if match:
                    path, source_id, arm, number = match.groups()
                    prefixes[path] = (source_id, arm, int(number))
            selection = archive.pin("selection.json")
            if selection_path is not None:
                if selection is None or selection["sha256"] != sha(selection_path.read_bytes()):
                    raise ValueError("Returned selection differs from trusted frozen selection")
            selection_sha = selection["sha256"] if selection else None
            cases = frozen_cases(archive)
            if size and not cases:
                raise ValueError("--size requires an archived autonomous cases selection")
            attempts = [attempt_audit(archive, path, *keys, cases.get(keys[0]), selection_sha)
                        for path, keys in sorted(prefixes.items())]
            statuses = batch_audit(archive, selection_sha) if cases else {}
            usage_fields = ("exact_usage_calls", "unknown_usage_calls", "exact_io_tokens", "exact_completion_tokens",
                            "unknown_reserved_io_tokens", "unknown_reserved_completion_tokens",
                            "receipt_reported_prompt_tokens", "receipt_prompt_token_coverage",
                            "receipt_reported_reasoning_tokens", "receipt_reasoning_token_coverage",
                            "receipt_reported_cached_tokens", "receipt_cached_token_coverage")
            return {
                "schema": "wrd58-autonomous-terminal-audit-v1",
                "archive_sha256": archive_sha, "verified_archive_members": len(archive.hashes),
                "selection": selection, "external_selection_verified": selection_path is not None,
                "attempt_states": dict(Counter(a["state"] for a in attempts)), "attempts": attempts,
                "usage_by_arm": {arm: {field: sum(a["usage"][field] for a in attempts if a["arm"] == arm)
                                       for field in usage_fields} for arm in sorted({a["arm"] for a in attempts})},
                "effect_denominator": effect_coverage(cases, attempts, statuses, size),
            }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--selection", type=Path, help="Optional trusted local frozen selection to compare by SHA")
    parser.add_argument("--size", choices=("14b", "8b"), help="Expected paired student cohort size")
    args = parser.parse_args(argv)
    try:
        result = run_audit(args.archive, args.selection, args.size)
        with args.out.open("x", encoding="utf-8", newline="\n") as output:
            json.dump(result, output, ensure_ascii=False, indent=2)
            output.write("\n")
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        parser.error(str(error))
    counts = {k: v for k, v in result["effect_denominator"].items() if k != "slots"}
    print(json.dumps({"out": str(args.out), "attempt_states": result["attempt_states"],
                      "effect_denominator": counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
