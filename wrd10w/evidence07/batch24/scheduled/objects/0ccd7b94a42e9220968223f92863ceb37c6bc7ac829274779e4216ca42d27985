#!/usr/bin/env python3
"""Summarize the dated artifacts produced by a scheduled task.

Method: read a JSON array of artifact records ([{"name": "<file name>"}, ...]),
extract YYYY-MM-DD dates from the file names, group the artifacts by date, and
flag names without a valid date as overwrite risks (generic naming let later
runs overwrite earlier files in the learned sources).

Validation order (first failure stops with exit 2):
  1. input readable and valid JSON; input is a JSON array
  2. every record is an object with a non-empty string field "name"

Inputs: artifacts JSON array.
Outputs: report JSON {total, dated, undated, by_date, first_date, last_date};
by_date maps each date to its artifact count; first/last are null when no
dated artifact exists.
Errors: "artifact_error: <reason>" on stderr, exit 2.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def fail(reason):
    print("artifact_error: " + reason, file=sys.stderr)
    raise SystemExit(2)


def extract_date(name):
    match = DATE_PATTERN.search(name)
    if not match:
        return None
    try:
        datetime.strptime(match.group(0), "%Y-%m-%d")
    except ValueError:
        return None
    return match.group(0)


def main():
    parser = argparse.ArgumentParser(description="Summarize dated scheduled-task artifacts")
    parser.add_argument("artifacts", help="artifacts JSON array path")
    parser.add_argument("--out", required=True, help="output report JSON path")
    args = parser.parse_args()
    try:
        raw = Path(args.artifacts).read_text(encoding="utf-8-sig")
    except OSError as error:
        fail("cannot read artifacts file: " + str(error))
    try:
        records = json.loads(raw)
    except (json.JSONDecodeError, UnicodeError) as error:
        fail("invalid JSON: " + str(error))
    if not isinstance(records, list):
        fail("artifacts must be a JSON array")
    names = []
    for index, record in enumerate(records):
        if not isinstance(record, dict) or "name" not in record:
            fail("artifact record " + str(index) + " is missing field: name")
        name = record["name"]
        if not isinstance(name, str) or not name:
            fail("artifact record " + str(index) + " name must be a non-empty string")
        names.append(name)
    by_date = {}
    undated = []
    for name in names:
        date = extract_date(name)
        if date is None:
            undated.append(name)
        else:
            by_date[date] = by_date.get(date, 0) + 1
    report = {
        "total": len(names),
        "dated": sum(by_date.values()),
        "undated": undated,
        "by_date": {key: by_date[key] for key in sorted(by_date)},
        "first_date": min(by_date) if by_date else None,
        "last_date": max(by_date) if by_date else None,
    }
    out_path = Path(args.out)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        fail("cannot write output: " + str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
