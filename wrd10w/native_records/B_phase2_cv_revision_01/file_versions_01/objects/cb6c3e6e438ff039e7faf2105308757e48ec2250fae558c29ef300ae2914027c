#!/usr/bin/env python3
"""Validate literal quotes cited from CV PDFs (quote/page/candidate claims).

Usage:
  evidence_check.py CLAIMS.json [--json OUT.json]

CLAIMS.json: JSON array of claim objects
  [{"file": "path/to/cv.pdf", "quote": "literal text from the CV",
    "page": 2}, ...]

Public claim contract (small, checked before any extraction):
- each item must be a JSON object (mapping);
- "file" and "quote" must be nonempty strings;
- "page" is optional; when present it must be a positive JSON integer
  (booleans, floats, strings and zero are rejected).
Quotes are whitespace-normalized (line breaks inside a quote are fine), and
matching runs against the PDF's raw per-page text, so display filtering never
hides legitimate evidence.
Fails on: contract violations, quote not found, quote on a different page than
claimed, out-of-range page, or any file-level extraction error
(missing/empty/corrupt/no-text-layer).
Exit codes: 0 all claims valid; 2 any failure. Failure report goes to stdout
as JSON; contract errors carry the claim index plus "field" and a precise
"reason" (no uncaught traceback).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cvlib


def claim_shape_error(claim):
    """Return (field, reason) for the first contract violation, else None."""
    if not isinstance(claim, dict):
        return ("claim", "claim item must be an object (mapping)")
    file_val = claim.get("file")
    if not isinstance(file_val, str) or not file_val.strip():
        return ("file", "file must be a nonempty string")
    quote_val = claim.get("quote")
    if not isinstance(quote_val, str) or not quote_val.strip():
        return ("quote", "quote must be a nonempty string")
    if "page" in claim:
        page_val = claim["page"]
        if isinstance(page_val, bool) or not isinstance(page_val, int):
            kind = "boolean" if isinstance(page_val, bool) else type(page_val).__name__
            return ("page", f"page must be an integer, not {kind}")
        if page_val < 1:
            return ("page", "page must be a positive integer (>= 1)")
    return None


def main():
    ap = argparse.ArgumentParser(description="Check literal CV quotes against pages")
    ap.add_argument("claims", help="JSON file with claim array")
    ap.add_argument("--json", dest="json_out", help="also write JSON report to this path")
    args = ap.parse_args()

    claims_path = Path(args.claims)
    if not claims_path.exists():
        print(json.dumps({"ok": False, "error": "claims file not found: " + str(claims_path)},
                         ensure_ascii=False))
        return 2
    try:
        claims = json.loads(claims_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(json.dumps({"ok": False, "error": "claims file unreadable: " + str(exc)},
                         ensure_ascii=False))
        return 2
    if not isinstance(claims, list):
        print(json.dumps({"ok": False, "error": "claims must be a JSON array"},
                         ensure_ascii=False))
        return 2

    cache = {}
    report, any_fail = [], False
    for idx, claim in enumerate(claims):
        shape = claim_shape_error(claim)
        if shape is not None:
            field, reason = shape
            entry = {
                "index": idx,
                "path": ["claims", idx],
                "field": field,
                "ok": False,
                "reason": reason,
            }
            if isinstance(claim, dict) and isinstance(claim.get("file"), str):
                entry["file"] = claim["file"]
            report.append(entry)
            any_fail = True
            continue
        entry = {"index": idx, "file": claim["file"], "ok": False}
        path = claim["file"]
        if path not in cache:
            try:
                cache[path] = (cvlib.extract_pdf(path), None)
            except cvlib.ExtractError as exc:
                cache[path] = (None, str(exc))
        cv, err = cache[path]
        if err:
            entry["reason"] = "file error: " + err
            any_fail = True
        else:
            entry["candidate_id"] = cv["candidate_id"]
            res = cvlib.find_quote(cv, claim["quote"], claim.get("page"))
            entry.update(res)
            if not res["ok"]:
                any_fail = True
        report.append(entry)

    out = {"ok": not any_fail, "claims": report}
    payload = json.dumps(out, ensure_ascii=False, indent=2)
    if args.json_out:
        Path(args.json_out).write_text(payload, encoding="utf-8")
    print(payload)
    return 0 if not any_fail else 2


if __name__ == "__main__":
    sys.exit(main())
