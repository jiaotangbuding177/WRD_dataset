"""CPU checks for audit evidence rules. Tool events here are fixtures only."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import audit_autonomous58 as audit


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def native_events(*messages):
    return b"\n".join(json_bytes({"session_id": "native", "native_event": {"message": message}})
                     for message in messages)


def call(call_id, tool, **arguments):
    return {"role": "assistant", "content": [{"type": "toolCall", "id": call_id,
                                               "name": tool, "arguments": arguments}]}


def returned(call_id, tool, details, is_error=False):
    return {"role": "toolResult", "toolCallId": call_id, "toolName": tool,
            "isError": is_error, "details": details, "content": []}


def return_zip(directory, members, hashes=None):
    path = directory / "return.zip"
    hashes = hashes or {name: audit.sha(data) for name, data in members.items()}
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
        archive.writestr("SHA256SUMS", "".join(f"{pin}  {name}\n" for name, pin in hashes.items()))
    path.with_suffix(".zip.sha256").write_text(audit.sha(path.read_bytes()), encoding="utf-8")
    return path


class TerminalAuditTest(unittest.TestCase):
    def test_real_tool_return_and_binding(self):
        source = b'{"historical_message":"example"}'
        source_sha = audit.sha(source)
        case_sha = audit.sha(b"case")
        resource_sha = audit.sha(b"resource")
        source_file = "inputs/sources/source/source.json"
        resource_file = "inputs/sources/source/fixture.txt"
        resource_index_file = "inputs/sources/source/resources.json"
        resource_index = json_bytes({"resources": [{"path": "/workspace/" + resource_file,
                                                    "sha256": resource_sha}]})
        selection = json_bytes({"cases": [
            {"id": "auto01", "source_ids": ["source"], "sources": [
                {"source_id": "source", "source_sha256": source_sha, "case_sha256": case_sha,
                 "resource_sha256": [resource_sha]}]},
            {"id": "auto02", "source_ids": ["other"]},
        ]})
        request = json_bytes({"input": "Make or stop", "followup_inputs": [], "learned_skills": []})
        members = {"selection.json": selection}
        for arm in ("wrd58-14b-0", "wrd58-14b-241"):
            prefix = f"runs/auto01/{arm}/attempt-001/"
            stage = {
                "schema": "wrd58-autonomous-stage-v1", "case_id": "auto01", "attempt": 1, "arm": arm,
                "selection_sha256": audit.sha(selection), "source_ids": ["source"],
                "source_sha256": source_sha, "request_sha256": audit.sha(request),
                "goal_sha256": audit.sha(b"Make or stop"), "git_tree": "same-initial-tree",
                "sources": [{"source_id": "source", "case_sha256": case_sha, "source_sha256": source_sha,
                             "source": "/workspace/" + source_file,
                             "resource_index": "/workspace/" + resource_index_file}],
                "files": {source_file: source_sha, resource_file: resource_sha,
                          resource_index_file: audit.sha(resource_index)},
            }
            members[prefix + "stage_receipt.json"] = json_bytes(stage)
            members[prefix + "request.json"] = request
            members[prefix + "dispatch.json"] = json_bytes({"arm": arm, "request_sha256": audit.sha(request)})
            members[prefix + "workspace/" + source_file] = source
            members[prefix + "workspace/" + resource_file] = b"resource"
            members[prefix + "workspace/" + resource_index_file] = resource_index
            if arm.endswith("-0"):
                members[prefix + "producer_result.json"] = json_bytes({"arm": arm, "returncode": 0, "actual_skill_md": []})
                members[prefix + "workspace/outputs/evidence/decision.json"] = b'{"action":"STOP"}'
                continue

            artifact_path = "outputs/skill/SKILL.md"
            command = f"check /workspace/{artifact_path} customer-secret-example"
            members[prefix + "producer_result.json"] = json_bytes({"arm": arm, "returncode": 0,
                                                                     "actual_skill_md": [artifact_path]})
            members[prefix + "workspace/" + artifact_path] = b"draft two"
            members[prefix + "workspace/outputs/trials/fake.png"] = b"{}"
            members[prefix + "openclaw_transport/all_session_events.jsonl"] = native_events(
                call("write1", "write", path=artifact_path, content="draft one"),
                returned("write1", "write", {"changed": True}),
                call("test1", "exec", command=command),
                returned("test1", "exec", {"status": "completed", "exitCode": 1}),
                call("write2", "write", path=artifact_path, content="draft two"),
                returned("write2", "write", {"changed": True}),
                call("test2", "exec", command=command),
                returned("test2", "exec", {"status": "completed", "exitCode": 0}),
                {"role": "assistant", "content": [{"type": "text", "text": "Passed and published everything"}]},
            )
            ledger = {"requests_admitted": 2, "calls": {
                "one": {"usage_state": "EXACT", "charged_io": 120,
                        "completion_usage_state": "EXACT", "charged_completion": 20},
                "two": {"usage_state": "RESERVED_UNKNOWN", "charged_io": 131072,
                        "completion_usage_state": "RESERVED_UNKNOWN", "charged_completion": 4096},
            }}
            members[prefix + "budget.json"] = json_bytes(ledger)
            members[prefix + "model_http/one/response.raw.sse"] = b"response bytes"
            members[prefix + "model_http/one/receipt.json"] = json_bytes({
                "call_id": "one", "status": "COMPLETE", "response_path": r"C:\record\response.raw.sse",
                "response_sha256": audit.sha(b"response bytes"), "usage": {"total_tokens": 120, "prompt_tokens": 100},
            })
            members[prefix + "model_http/two/receipt.json"] = json_bytes({"call_id": "two", "status": "ERROR",
                                                                       "error_type": "URLError"})

        members["runs/_batch/14b-123.json"] = json_bytes({"selection_sha256": audit.sha(selection), "results_so_far": [
            {"case_id": "auto02", "arm": "wrd58-14b-241", "status": "DISPATCH_ERROR", "error_type": "TimeoutError"},
        ]})
        with tempfile.TemporaryDirectory() as tmp:
            result = audit.run_audit(return_zip(Path(tmp), members), None, "14b")
        base, candidate = result["attempts"]
        self.assertEqual(base["state"], "DECLARED_STOP_OR_BLOCKED_PENDING_REVIEW")
        self.assertIsNone(base["independent_stop_correct"])
        self.assertEqual(candidate["state"], "CANDIDATE_PENDING_FUNCTIONAL_REVIEW")
        self.assertTrue(candidate["native"]["mutations"][1]["matches_returned_artifact"])
        self.assertEqual(candidate["native"]["commands"][0]["status"], "NONZERO_EXIT")
        self.assertEqual(candidate["native"]["commands"][1]["status"], "ZERO_EXIT")
        self.assertEqual(len(candidate["native"]["repair_sequences"]), 1)
        self.assertIsNone(candidate["native"]["repair_sequences"][0]["functional_pass"])
        self.assertNotIn("customer-secret-example", json.dumps(candidate))
        self.assertFalse(candidate["outputs"]["outputs/trials/fake.png"]["png_signature_present"])
        self.assertEqual(candidate["usage"]["exact_io_tokens"], 120)
        self.assertEqual(candidate["usage"]["unknown_usage_calls"], 1)
        self.assertEqual(candidate["usage"]["receipt_reported_prompt_tokens"], 100)
        self.assertEqual(candidate["usage"]["unknown_reserved_io_tokens"], 131072)
        denominator = result["effect_denominator"]
        self.assertEqual(denominator["planned_student_slots"], 4)
        self.assertEqual(denominator["paired_terminal_cases_with_equal_initial_input"], ["auto01"])
        self.assertEqual(denominator["slots"][-1]["state"], "LAUNCH_ERROR_WITHOUT_ATTEMPT")
        self.assertIsNone(denominator["valid_functional_pairs"])

    def test_background_poll_timeout_and_late_edit_do_not_form_repair(self):
        prefix = "runs/auto01/wrd58-14b-241/attempt-001/"
        name = "outputs/skill/trial.py"
        command = "python " + name
        members = {prefix + "openclaw_transport/all_session_events.jsonl": native_events(
            call("test1", "exec", command=command),
            returned("test1", "exec", {"status": "completed", "exitCode": 2}),
            call("test2", "exec", command=command),
            returned("test2", "exec", {"status": "running", "sessionId": "p"}),
            call("late", "write", path=name, content="new"),
            returned("late", "write", {"changed": True}),
            call("poll", "process", action="poll", sessionId="p"),
            returned("poll", "process", {"status": "completed", "exitCode": 0, "sessionId": "p"}),
            call("timeout", "exec", command=command),
            returned("timeout", "exec", {"status": "completed", "exitCode": 0, "timedOut": True}),
        )}
        with tempfile.TemporaryDirectory() as tmp:
            result = audit.run_audit(return_zip(Path(tmp), members), None)
        native = result["attempts"][0]["native"]
        self.assertEqual(native["commands"][-1]["status"], "TERMINATED")
        self.assertEqual(native["repair_sequences"], [])

    def test_member_tampering_fails_before_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = return_zip(Path(tmp), {"selection.json": b"changed"}, {"selection.json": audit.sha(b"old")})
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                audit.run_audit(path, None)


if __name__ == "__main__":
    unittest.main()
