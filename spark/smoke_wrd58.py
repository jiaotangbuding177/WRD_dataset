#!/usr/bin/env python3
"""Verify the model API with a synthetic streaming tool call and no tool execution."""

import argparse
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


def check_long_input(base, model):
    # Same synthetic text and request budget for every arm. Keep the receipt to usage only.
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Ignore this synthetic padding:\n" + " reference" * 66000 + "\nRespond briefly with OK."},
        ],
        "chat_template_kwargs": {"enable_thinking": True},
        "max_tokens": 32768,
        "stream": False,
    }
    started = time.monotonic()
    with urllib.request.urlopen(chat_request(base, payload), timeout=300) as response:
        output = json.load(response)
    usage = output.get("usage", {})
    check(output.get("model") == model and output["choices"][0]["finish_reason"] == "stop", f"Long probe did not complete normally: {model}")
    check(type(usage.get("prompt_tokens")) is int and usage["prompt_tokens"] >= 65806, f"Actual long prefill is below 65,806 tokens: {usage}")
    return {"model": model, "requested_max_tokens": 32768, "usage": usage, "wall_seconds": round(time.monotonic() - started, 3)}


def run(base, size, context, long_input=False):
    ids = [f"wrd58-{size}-{step}" for step in (0, 26)]
    with urllib.request.urlopen(f"{base}/models", timeout=15) as response:
        models = {card["id"]: card for card in json.load(response)["data"]}
    check(all(model in models for model in ids), f"Missing API model IDs: {ids}; found {sorted(models)}")
    bare = models.get(f"wrd58-{size}-bare", {})
    observed_context = bare.get("max_model_len")
    if observed_context is not None:
        check(observed_context == context, f"Unexpected API context: {observed_context}")
    arms = []
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
        with urllib.request.urlopen(chat_request(base, payload), timeout=180) as response:
            arms.append(inspect_stream(response, model))
    result = {"status": "pass", "size": size, "requested_context": context, "api_reported_context": observed_context, "synthetic_transport_arms": arms}
    if long_input:
        result["synthetic_long_input_arms"] = [check_long_input(base, model) for model in ids]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("size", choices=("8b", "14b"))
    parser.add_argument("--context", type=int, choices=(32768, 131072), default=32768)
    parser.add_argument("--base-url", default="http://127.0.0.1:18758/v1")
    parser.add_argument("--long-input", action="store_true", help="Also send a 66K synthetic prefill and a 32768 output budget to each arm")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.long_input and args.context != 131072:
        parser.error("--long-input requires --context 131072")
    try:
        result = run(args.base_url.rstrip("/"), args.size, args.context, args.long_input)
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {"status": "fail", "size": args.size, "requested_context": args.context, "error": str(error)}
    report = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8") as file:
            file.write(report)
    print(report, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
