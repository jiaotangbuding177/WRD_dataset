#!/usr/bin/env python3
"""Build a platform scheduled-task config from a JSON task spec.

Method: read the spec, validate it, optionally merge it over an existing
config (--base), and write the normalized automation config used to create or
update a scheduled task. Merge rule: fields present in the spec override the
base; every other field is preserved from the base, so an update only changes
what the user asked to change. The output filename pattern is always
recomputed from the merged name and format as "{date}-<name>.<ext>".

Validation order (first failure stops with exit 2):
  1. spec/base readable and valid JSON; spec and base are JSON objects
  2. required fields present: name, schedule, message, output_format, output_dir
  3. name/message/output_dir are non-empty strings
  4. schedule.kind == "cron"; schedule.expr has exactly 5 fields;
     schedule.tz is a valid IANA timezone (one-off schedules are unsupported)
  5. output_format in {md, pdf, image}
  6. timeout_seconds, if present, is a positive integer (default 900)
  7. delivery, if present, is one of {announce, none} (default announce)

Inputs: task spec JSON with keys {name, schedule{kind,expr,tz}, message,
output_format, output_dir[, timeout_seconds][, delivery]}; optional existing
config JSON for --base update merges.
Outputs: normalized config JSON {name, schedule, payload, delivery, output}.
Errors: "task_spec_error: <reason>" on stderr, exit 2.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

FORMAT_EXT = {"md": "md", "pdf": "pdf", "image": "png"}
DELIVERY_MODES = ("announce", "none")
DEFAULT_TIMEOUT = 900
REQUIRED = ("name", "schedule", "message", "output_format", "output_dir")


def fail(reason):
    print("task_spec_error: " + reason, file=sys.stderr)
    raise SystemExit(2)


def load_json(path, label):
    try:
        raw = Path(path).read_text(encoding="utf-8-sig")
    except OSError as error:
        fail("cannot read " + label + ": " + str(error))
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeError) as error:
        fail("invalid JSON in " + label + ": " + str(error))
    if not isinstance(value, dict):
        fail(label + " must be a JSON object")
    return value


def base_to_spec(base):
    converted = {}
    try:
        converted["name"] = base["name"]
        converted["schedule"] = base["schedule"]
        converted["message"] = base["payload"]["message"]
        converted["output_format"] = base["output"]["format"]
        converted["output_dir"] = base["output"]["output_dir"]
        converted["timeout_seconds"] = base["payload"]["timeoutSeconds"]
        converted["delivery"] = base["delivery"]["mode"]
    except (KeyError, TypeError):
        fail("base config is missing a required section")
    return converted


def build(spec):
    for key in REQUIRED:
        if key not in spec:
            fail("missing required field: " + key)
    for key in ("name", "message", "output_dir"):
        if not isinstance(spec[key], str) or not spec[key].strip():
            fail(key + " must be a non-empty string")
    schedule = spec["schedule"]
    if not isinstance(schedule, dict) or not all(k in schedule for k in ("kind", "expr", "tz")):
        fail("schedule must be an object with kind, expr and tz")
    if schedule["kind"] != "cron":
        fail("schedule.kind must be 'cron'; one-off schedules are unsupported")
    expr = schedule["expr"]
    if not isinstance(expr, str) or len(expr.split()) != 5:
        fail("schedule.expr must contain 5 fields")
    tz = schedule["tz"]
    if not isinstance(tz, str):
        fail("schedule.tz must be a string")
    try:
        ZoneInfo(tz)
    except Exception:
        fail("schedule.tz is not a valid IANA timezone")
    if spec["output_format"] not in FORMAT_EXT:
        fail("output_format must be one of: md, pdf, image")
    timeout = spec.get("timeout_seconds", DEFAULT_TIMEOUT)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        fail("timeout_seconds must be a positive integer")
    delivery = spec.get("delivery", "announce")
    if delivery not in DELIVERY_MODES:
        fail("delivery must be one of: announce, none")
    return {
        "name": spec["name"],
        "schedule": {"kind": "cron", "expr": expr, "tz": tz},
        "payload": {"kind": "agentTurn", "message": spec["message"], "timeoutSeconds": timeout},
        "delivery": {"mode": delivery},
        "output": {
            "format": spec["output_format"],
            "filename_pattern": "{date}-" + spec["name"] + "." + FORMAT_EXT[spec["output_format"]],
            "output_dir": spec["output_dir"],
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Build a scheduled-task config from a task spec")
    parser.add_argument("spec", help="task spec JSON path")
    parser.add_argument("--out", required=True, help="output config JSON path")
    parser.add_argument("--base", help="existing config JSON to merge over (update mode)")
    args = parser.parse_args()
    spec = load_json(args.spec, "task spec")
    if args.base is not None:
        base = load_json(args.base, "base config")
        merged = base_to_spec(base)
        merged.update(spec)
        spec = merged
    config = build(spec)
    out_path = Path(args.out)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        fail("cannot write output: " + str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
