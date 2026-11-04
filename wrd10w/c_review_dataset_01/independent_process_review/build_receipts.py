"""Offline, content-local review receipts; does not admit data or change native files."""
import hashlib
import json
from pathlib import Path

ROOT = Path(r"D:\skillloop\output\20261027_wrd_main_v10\runtime_preflight\episodes")
OUT = Path(__file__).parent
NAMES = ["C_E_no_skill_01", "C_E_skill_01", "C_L_no_skill_01", "C_L_skill_01"]


def sha(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def assemble(path):
    text, reasoning, tools = "", "", {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("data: ") or line[6:] == "[DONE]":
            continue
        obj = json.loads(line[6:])
        for choice in obj.get("choices", []):
            delta = choice.get("delta", {})
            text += delta.get("content") or ""
            reasoning += delta.get("reasoning_content") or ""
            for item in delta.get("tool_calls", []):
                ix = item.get("index", 0)
                dest = tools.setdefault(ix, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                if item.get("id"):
                    dest["id"] = item["id"]
                function = item.get("function", {})
                dest["function"]["name"] += function.get("name") or ""
                dest["function"]["arguments"] += function.get("arguments") or ""
    return {"content": text, "reasoning_content": reasoning, "tool_calls": [tools[ix] for ix in sorted(tools)]}


summary = {"schema": "v10-independent-c-process-content-review-v1", "reviewer": "independent AI assistant; silver, not human calibration", "root_main_admission": False, "file_receipts": [], "candidates": [], "not_admitted": []}
for name in NAMES:
    root = ROOT / name
    source_path = root / "workspace/inputs/task/source_input.json"
    delivery_path = root / "workspace/outputs/deliverable.md"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    delivery = delivery_path.read_text(encoding="utf-8")
    for path in [source_path, delivery_path, root / "openclaw_transport/session_events.jsonl"]:
        summary["file_receipts"].append({"path": str(path), "sha256": sha(path.read_bytes()), "bytes": path.stat().st_size})
    if name.endswith("no_skill_01"):
        reason = (
            "Whole write not admitted: paragraph 2 turns '难以持续承担' into '无法承担'; closing sentence calls named person 当前最合适的人选, stronger than supplied 条件. Locally faithful paragraphs remain recoverable but are not granted whole-action credit."
            if name.startswith("C_E") else
            "Whole write not admitted: user's 600字 boundary needs explicit counting; source '不同学段' becomes '各学段', an unnecessary strengthening; greeting/final meta also enlarge artifact. Faithful local spans could be reviewed separately."
        )
        summary["not_admitted"].append({"episode": name, "reason": reason, "delivery_characters": len(delivery), "non_whitespace_characters": sum(not c.isspace() for c in delivery)})
        continue
    events = [json.loads(line) for line in (root / "openclaw_transport/session_events.jsonl").read_text(encoding="utf-8").splitlines()]
    for event_ix, event in enumerate(events):
        message = event.get("message", {})
        if message.get("role") != "assistant":
            continue
        for block in message.get("content", []):
            arguments = block.get("arguments", {})
            if block.get("type") != "toolCall" or block.get("name") != "write" or arguments.get("path") != "/workspace/outputs/deliverable.md":
                continue
            assert arguments["content"] == delivery
            tool_id = block["id"]
            match = None
            for directory in sorted((root / "api_audit").iterdir()):
                response_path = directory / "response.raw.sse"
                if not directory.is_dir() or not response_path.exists():
                    continue
                response = assemble(response_path)
                for tool in response["tool_calls"]:
                    if tool["id"] == tool_id:
                        match = (directory, response_path, response, tool)
            assert match is not None
            directory, response_path, response, tool = match
            raw_arguments = tool["function"]["arguments"]
            assert json.loads(raw_arguments) == arguments
            request_path = directory / "request.raw.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            write_schema = next(item for item in request["tools"] if item["function"]["name"] == "write")
            required = write_schema["function"]["parameters"].get("required", [])
            assert all(field in arguments for field in required)
            assert set(arguments) <= set(write_schema["function"]["parameters"].get("properties", {}))
            observation = events[event_ix + 1]["message"]
            assert observation["role"] == "toolResult" and observation["toolCallId"] == tool_id
            assert observation.get("isError", False) is False
            preserved = OUT / (name + ".actual_write_arguments.txt")
            preserved.write_text(raw_arguments, encoding="utf-8", newline="")
            candidate = {
                "episode": name,
                "native_session_path": str(root / "openclaw_transport/session_events.jsonl"),
                "native_event_index_zero_based": event_ix,
                "native_line_one_based": event_ix + 1,
                "assistant_message_id": event["id"],
                "tool_call_id": tool_id,
                "tool_name": "write",
                "raw_actual_fields": list(arguments),
                "request_path": str(request_path),
                "request_sha256": sha(request_path.read_bytes()),
                "response_path": str(response_path),
                "response_sha256": sha(response_path.read_bytes()),
                "api_call_id": directory.name,
                "raw_arguments_path": str(preserved),
                "raw_arguments_sha256": sha(raw_arguments),
                "raw_arguments_character_range": [0, len(raw_arguments)],
                "decoded_content_sha256": sha(arguments["content"]),
                "decoded_content_character_range": [0, len(arguments["content"])],
                "delivery_sha256": sha(delivery_path.read_bytes()),
                "delivery_characters": len(delivery),
                "non_whitespace_characters": sum(not c.isspace() for c in delivery),
                "original_write_schema": write_schema,
                "write_schema_sha256": sha(json.dumps(write_schema, ensure_ascii=False, separators=(",", ":"))),
                "actual_success_observation": observation,
                "source_path": str(source_path),
                "source_sha256": sha(source_path.read_bytes()),
                "source_id": source["source_id"],
                "source_group_id": source["source_group_id"],
                "proposed_role": "execution_main_local_candidate_only",
                "root_main_admission": False,
                "does_not_grant_whole_episode_or_skill_credit": True,
            }
            if name.startswith("C_E"):
                source_text = source["current_original_request"]["content"]
                markers = ["（一）", "（二）", "（三）", "（四）", "（五）"]
                semantic = []
                for number, marker in enumerate(markers):
                    start = source_text.index(marker)
                    end = source_text.index(markers[number + 1]) if number + 1 < len(markers) else len(source_text)
                    out_start = delivery.index(marker)
                    out_end = delivery.index(markers[number + 1]) if number + 1 < len(markers) else len(delivery)
                    semantic.append({"point": number + 1, "source_field": "current_original_request.content", "source_character_range": [start, end], "source_slice_sha256": sha(source_text[start:end]), "delivery_character_range": [out_start, out_end], "delivery_slice_sha256": sha(delivery[out_start:out_end]), "review": "Core point, causal direction, temporal/modal limitations, proper names and named subject preserved; redundant examples compressed. No person-ranking conclusion added."})
                candidate["semantic_claim_receipts"] = semantic
                candidate["source_material_characters"] = len(source_text)
                candidate["local_content_assessment"] = "Pass as concise source-preserving five-point rewrite. This assesses delivery content, not whether the costly pack-building route was necessary or optimal."
            else:
                source_text = source["messages"][0]["content"]
                phrases = ["20多个省市", "不同学段", "一年的从原型到产品的研究和研发", "40余项AI应用", "80%的备课与教学外延工作", "92.75%资深教师盲审采纳", "实测显示", "约13小时", "教学效率提升85%", "32个省份3000+所学校", "2026年1月", "6个AI智能工具之一"]
                semantic = []
                for phrase in phrases:
                    start = source_text.index(phrase)
                    semantic.append({"source_phrase": phrase, "source_field": "messages[0].content", "source_character_range": [start, start + len(phrase)], "source_slice_sha256": sha(phrase), "review": "Supplied user claim or qualifier preserved in delivered report; not asserted independently externally verified."})
                candidate["semantic_claim_receipts"] = semantic
                candidate["local_content_assessment"] = "Pass as official report on construction and promotion, retaining persona and source-supported quantities and qualifiers; 486 total Unicode characters and 479 non-whitespace characters, both below 600."
                candidate["word_boundary_resolution"] = "Entire local deliverable is below 600 using both all-codepoint and non-whitespace count, so no boundary exception is needed. Counting is reported descriptively, not treated as a trained historical user convention."
            summary["candidates"].append(candidate)

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "PROCESS_CANDIDATES.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"candidates": [{k: c[k] for k in ["episode", "api_call_id", "native_line_one_based", "raw_arguments_character_range", "raw_arguments_sha256", "delivery_characters", "non_whitespace_characters"]} for c in summary["candidates"]], "not_admitted": summary["not_admitted"]}, ensure_ascii=False, indent=2))
