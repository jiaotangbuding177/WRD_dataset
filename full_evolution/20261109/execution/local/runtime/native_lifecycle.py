"""Read-only observer for a pinned OpenClaw run that yielded to native children.

This module never sends a prompt, wakes a session, executes a tool, or edits a
native result. The gateway owns all continuation. Observation uses the same
episode deadline and requires a new, run-tagged parent event after its exact
yield anchor; an earlier assistant stop cannot complete a later turn.
"""
from __future__ import annotations

import time


def result_data(native):
    return native.get("result", native)


def is_native_pause(native):
    meta = result_data(native).get("meta", {})
    return meta.get("yielded") is True or meta.get("livenessState") == "paused"


def _message(event):
    return event.get("message", {}) if event.get("type") == "message" else {}


def _run(event):
    return _message(event).get("__openclaw", {}).get("runId")


def _text(message):
    content = message.get("content", [])
    if isinstance(content, str):
        return content
    return "\n\n".join(p.get("text", "") for p in content
                       if isinstance(p, dict) and p.get("type") == "text" and p.get("text"))


def classify_parent_events(native, events, *, expected_session_id):
    """Return WAIT or native terminal evidence, never infer from historical text.

    ``events`` must be this session's native SQLite event_json in stored order.
    A session header and the initial run's actual sessions_yield result anchor
    are mandatory. The final event must be downstream in the native parentId
    chain, run-tagged, later in time, ordinary assistant stop, and contain text.
    """
    data = result_data(native)
    meta = data.get("meta", {})
    run_id = native.get("runId") or meta.get("runId")
    actual_session = meta.get("agentMeta", {}).get("sessionId")
    if actual_session != expected_session_id or not run_id:
        raise ValueError("Native run/session identity is missing or mismatched")
    if not any(e.get("type") == "session" and e.get("id") == expected_session_id for e in events):
        raise ValueError("Read-only export does not contain the expected native session header")
    anchor_index = None
    for index, event in enumerate(events):
        msg = _message(event)
        if (_run(event) == run_id and msg.get("role") == "toolResult"
                and msg.get("toolName") == "sessions_yield"
                and msg.get("details", {}).get("status") == "yielded"):
            anchor_index = index
    if anchor_index is None:
        return {"status": "WAIT", "reason": "exact_run_yield_anchor_not_persisted"}
    anchor = events[anchor_index]
    if not anchor.get("id") or not anchor.get("timestamp"):
        raise ValueError("Native yield anchor lacks event/time identity")
    descendants = {anchor["id"]}
    for event in events[anchor_index + 1:]:
        if event.get("parentId") not in descendants:
            continue
        if event.get("id"):
            descendants.add(event["id"])
        msg = _message(event)
        if not _run(event) or event.get("timestamp", "") <= anchor["timestamp"]:
            continue
        # Native automatic delivery may introduce new user/system messages.
        # Only the gateway-produced final assistant event is a terminal answer.
        if msg.get("role") != "assistant":
            continue
        reason = msg.get("stopReason")
        if reason in ("error", "aborted"):
            return {"status": "FAILED", "reason": reason, "event_id": event.get("id"),
                    "run_id": _run(event), "session_id": expected_session_id}
        content = msg.get("content", [])
        has_tool = isinstance(content, list) and any(isinstance(p, dict) and
            p.get("type") in ("toolCall", "toolUse", "tool_call") for p in content)
        text = _text(msg)
        if reason in ("stop", "end_turn") and text.strip() and not has_tool:
            return {"status": "COMPLETE", "answer": text, "event_id": event["id"],
                    "run_id": _run(event), "initial_run_id": run_id,
                    "session_id": expected_session_id, "timestamp": event["timestamp"],
                    "yield_anchor_id": anchor["id"],
                    "completion_basis": "new_native_parent_descendant_assistant_terminal_event",
                    "native_result_rewritten": False, "gateway_continuation_owned_by": "OpenClaw"}
    return {"status": "WAIT", "reason": "native_parent_has_no_post_yield_terminal_answer",
            "yield_anchor_id": anchor["id"], "initial_run_id": run_id}


def observe_native_resume(native, *, expected_session_id, read_events, deadline,
                          monotonic=time.monotonic, sleep=time.sleep, interval=0.5,
                          write_observation=lambda value: None):
    """Keep the gateway alive and observe; do not extend the episode deadline."""
    if not is_native_pause(native):
        raise ValueError("Observer is restricted to native yielded/paused results")
    last = {"status": "WAIT", "reason": "not_yet_observed"}
    while monotonic() < deadline:
        try:
            events = read_events()
            last = classify_parent_events(native, events, expected_session_id=expected_session_id)
        except (OSError, ValueError, RuntimeError) as exc:
            # Partial exports during an active native SQLite write are unknown,
            # not success. Keep the actual error class without private content.
            last = {"status": "WAIT", "reason": "native_export_incomplete",
                    "error_type": type(exc).__name__}
        write_observation(last)
        if last["status"] == "COMPLETE":
            return last
        if last["status"] == "FAILED":
            raise RuntimeError("Native resumed parent failed: " + last["reason"])
        sleep(min(interval, max(0, deadline - monotonic())))
    last = dict(last, status="TIMEOUT", original_episode_deadline_preserved=True)
    write_observation(last)
    raise TimeoutError("Native parent did not reach an observed post-yield terminal answer before deadline")
