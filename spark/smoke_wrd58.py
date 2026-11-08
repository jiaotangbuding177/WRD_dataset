#!/usr/bin/env python3
"""Verify the model API with a synthetic streaming tool call and no tool execution."""

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path


LOOKUP = {
    "type": "function",
    "function": {
        "name": "wrd58_lookup",
        "description": "Look up a synthetic receipt by its exact key",
        "parameters": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
            "additionalProperties": False,
        },
    },
}
KEY = "wrd58-protocol-smoke"
LONG_OUTPUT_BUDGETS = (64, 128, 256)
PROBE_ERRORS = (OSError, ValueError, KeyError, TypeError, IndexError)


def check(condition, message):
    if not condition:
        raise ValueError(message)


def inspect_stream(lines, model):
    usage = None
    ended = False
    finish = []
    calls = {}
    reasoning_chars = 0
    reasoning_fields = set()
    responses = set()
    for line in lines:
        if not line.startswith(b"data:"):
            continue
        value = line[5:].strip()
        if value == b"[DONE]":
            ended = True
            break
        event = json.loads(value)
        check("error" not in event, f"SSE returned error: {event.get('error')}")
        if event.get("model"):
            responses.add(event["model"])
        if event.get("usage") is not None:
            usage = event["usage"]
        for choice in event.get("choices", []):
            if choice.get("finish_reason"):
                finish.append(choice["finish_reason"])
            delta = choice.get("delta", {})
            for field in ("reasoning", "reasoning_content"):
                if isinstance(delta.get(field), str) and delta[field]:
                    reasoning_fields.add(field)
                    reasoning_chars += len(delta[field])
            for item in delta.get("tool_calls") or []:
                call = calls.setdefault(item["index"], {"id": "", "name": "", "arguments": ""})
                call["id"] += item.get("id") or ""
                function = item.get("function") or {}
                call["name"] += function.get("name") or ""
                call["arguments"] += function.get("arguments") or ""
    check(ended and responses == {model}, f"Unexpected SSE completion or response model: {ended}, {responses}")
    check(finish == ["tool_calls"] and len(calls) == 1, f"Expected one structured tool call, finish={finish}, calls={calls}")
    call = next(iter(calls.values()))
    check(call["id"] and call["name"] == "wrd58_lookup" and json.loads(call["arguments"]) == {"key": KEY}, f"Unexpected tool call: {call}")
    check(reasoning_chars > 0, "No non-empty reasoning delta observed with thinking enabled")
    check(isinstance(usage, dict) and all(type(usage.get(key)) is int and usage[key] > 0 for key in ("prompt_tokens", "completion_tokens", "total_tokens")), "Missing or invalid actual token usage")
    check(usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"], "Actual token usage total does not balance")
    return {"model": model, "finish_reason": "tool_calls", "tool": call["name"], "reasoning_fields": sorted(reasoning_fields), "reasoning_chars": reasoning_chars, "usage": usage}


def chat_request(base, payload):
    return urllib.request.Request(f"{base}/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})


def check_long_input(base, model, max_tokens=64):
    check(max_tokens in LONG_OUTPUT_BUDGETS, "Long capacity output budget must be 64, 128 or 256")
    prefix, padding, count, suffix = "Ignore this synthetic padding:\n", " reference", 66000, "\nRespond briefly with OK."
    content = prefix + padding * count + suffix
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": content},
        ],
        "chat_template_kwargs": {"enable_thinking": True},
        "max_tokens": max_tokens,
        "stream": False,
    }
    started = time.monotonic()
    row = {"model": model, "status": "fail", "capacity_status": "fail",
           "termination_status": "NOT_OBSERVED", "requested_max_tokens": max_tokens,
           "request_parameters": {key: value for key, value in payload.items() if key != "messages"},
           "request_json_key_order": list(payload),
           "request_messages_recipe": [{"role": "user", "prefix": prefix, "padding": padding,
                                         "padding_count": count, "suffix": suffix,
                                         "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}],
           "request_sha256": hashlib.sha256(json.dumps(payload).encode()).hexdigest()}
    try:
        with urllib.request.urlopen(chat_request(base, payload), timeout=300) as response:
            row["http_status"] = response.getcode()
            output = json.load(response)
        row["response"] = output
        usage = output.get("usage", {})
        row["usage"] = usage
        choices = output.get("choices")
        check(row["http_status"] == 200 and output.get("model") == model,
              f"Unexpected long-probe HTTP status or model: {model}")
        check(isinstance(choices, list) and len(choices) == 1, "Expected one long-probe choice")
        finish = choices[0].get("finish_reason")
        row["finish_reason"] = finish
        check(finish in ("stop", "length"), f"Unexpected long-probe finish: {finish}")
        check(isinstance(usage, dict) and all(type(usage.get(key)) is int and usage[key] > 0
              for key in ("prompt_tokens", "completion_tokens", "total_tokens")), "Invalid actual long-probe usage")
        check(usage["prompt_tokens"] >= 65806, f"Actual long prefill is below 65,806 tokens: {usage}")
        check(usage["completion_tokens"] <= max_tokens and
              usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"],
              "Long-probe usage does not balance or exceeds the bounded output budget")
        row.update(status="pass", capacity_status="pass",
                   termination_status="NATURAL_STOP_OBSERVED" if finish == "stop" else "OUTPUT_LIMIT_REACHED",
                   natural_stop_observed=finish == "stop")
    except PROBE_ERRORS as error:
        row["error"] = f"{type(error).__name__}: {error}"
    row["wall_seconds"] = round(time.monotonic() - started, 3)
    return row


def run(base, size, context, long_input=False, arm="both", long_output_tokens=64):
    check(arm in ("0", "26", "both"), "Unknown selected arm")
    check(long_output_tokens in LONG_OUTPUT_BUDGETS, "Unbounded long output budget rejected")
    steps = (0, 26) if arm == "both" else (int(arm),)
    ids = [f"wrd58-{size}-{step}" for step in steps]
    with urllib.request.urlopen(f"{base}/models", timeout=15) as response:
        models = {card["id"]: card for card in json.load(response)["data"]}
    bare = models.get(f"wrd58-{size}-bare", {})
    observed_context = bare.get("max_model_len")
    if observed_context is not None:
        check(observed_context == context, f"Unexpected API context: {observed_context}")
    arms, long_arms = [], []
    for model in ids:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": f"Use the lookup function to retrieve receipt {KEY}. Call the tool exactly once. I need the tool result to know its value. Wait for the result."}],
            "tools": [LOOKUP],
            "tool_choice": "auto",
            "chat_template_kwargs": {"enable_thinking": True},
            "stream": True,
            "stream_options": {"include_usage": True},
            "max_tokens": 1024,
        }
        row = {"model": model, "status": "fail", "request": payload}
        lines = []
        try:
            check(model in models, f"Missing API model ID: {model}")
            with urllib.request.urlopen(chat_request(base, payload), timeout=180) as response:
                row["http_status"] = response.getcode()
                for line in response:
                    lines.append(line)
            check(row["http_status"] == 200, f"Unexpected tool-probe HTTP status: {row['http_status']}")
            row.update(inspect_stream(lines, model), status="pass")
        except PROBE_ERRORS as error:
            row["error"] = f"{type(error).__name__}: {error}"
        finally:
            if lines:
                row["response_sse"] = b"".join(lines).decode("utf-8", errors="replace")
        arms.append(row)
        if long_input:
            if model in models:
                long_arms.append(check_long_input(base, model, long_output_tokens))
            else:
                long_arms.append({"model": model, "status": "fail", "capacity_status": "fail",
                                  "termination_status": "NOT_OBSERVED", "error": "Missing API model ID"})
    transport = "pass" if all(row["status"] == "pass" for row in arms) else "fail"
    capacity = ("pass" if all(row["capacity_status"] == "pass" for row in long_arms) else "fail") if long_input else "not_tested"
    result = {"schema": "wrd58-spark-smoke-v2", "status": "pass" if transport == "pass" and capacity != "fail" else "fail",
              "size": size, "selected_arms": ids, "requested_context": context,
              "api_reported_context": observed_context, "transport_status": transport,
              "capacity_status": capacity, "synthetic_transport_arms": arms,
              "synthetic_long_input_arms": long_arms,
              "termination_status_by_arm": {row["model"]: row["termination_status"] for row in long_arms},
              "capacity_note": "A length finish accepts the bounded prefill capacity test only; it is not natural-stop success or skill-generation acceptance."}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("size", choices=("8b", "14b"))
    parser.add_argument("--context", type=int, choices=(32768, 131072), default=32768)
    parser.add_argument("--base-url", default="http://127.0.0.1:18758/v1")
    parser.add_argument("--arm", choices=("0", "26", "both"), default="both")
    parser.add_argument("--long-input", action="store_true", help="Also test 66K synthetic prefill capacity with a bounded output budget")
    parser.add_argument("--long-output-tokens", type=int, choices=LONG_OUTPUT_BUDGETS, default=64)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.long_input and args.context != 131072:
        parser.error("--long-input requires --context 131072")
    if args.out and args.out.exists():
        parser.error("--out already exists; preserve the existing receipt and choose a new path")
    try:
        result = run(args.base_url.rstrip("/"), args.size, args.context, args.long_input, args.arm, args.long_output_tokens)
    except PROBE_ERRORS as error:
        result = {"schema": "wrd58-spark-smoke-v2", "status": "fail", "size": args.size,
                  "requested_context": args.context, "synthetic_transport_arms": [], "synthetic_long_input_arms": [],
                  "error": f"{type(error).__name__}: {error}"}
    report = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8") as file:
            file.write(report)
    print(report, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
