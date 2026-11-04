#!/usr/bin/env python3
"""Making-side replay verifier (NOT part of the skill).

Reads outputs/replay.json and executes every case exactly as documented,
including assertion checks (json_equals/contains/zip_members/zip_xml_contains/
record_count). Exits non-zero if anything fails.
"""
import json
import os
import re
import subprocess
import sys
import zipfile

ROOT = "/workspace"
REPLAY = os.path.join(ROOT, "outputs/replay.json")
SKILL = os.path.join(ROOT, "outputs/candidate/skill")
FIXTURE = os.path.join(ROOT, "outputs/reproduction_inputs")
OUT = "/tmp/replay_verify"

doc = json.load(open(REPLAY, encoding="utf-8"))
os.makedirs(OUT, exist_ok=True)
results = []


def expand(tok):
    return (tok.replace("{SKILL}", SKILL)
               .replace("{FIXTURE}", FIXTURE)
               .replace("{OUT}", OUT)
               .replace("{INPUT}", FIXTURE))


def check_assertion(a, outdir):
    path = os.path.join(outdir, expand(a["path"]).replace(SKILL + "/", "").replace(FIXTURE + "/", ""))
    # a["path"] is OUT-relative already in replay.json
    path = os.path.join(outdir, a["path"])
    kind = a["kind"]
    val = a["value"]
    if kind == "json_equals":
        return json.load(open(path, encoding="utf-8")) == val
    if kind == "contains":
        return val in open(path, encoding="utf-8").read()
    if kind == "record_count":
        data = json.load(open(path, encoding="utf-8"))
        return data.get(val["field"]) == val["equals"]
    if kind == "zip_members":
        members = zipfile.ZipFile(path).namelist()
        return all(m in members for m in val["required"])
    if kind == "zip_xml_contains":
        xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
        return val in xml
    raise ValueError("unknown assertion kind " + kind)


ok_all = True
for prog in doc["programs"]:
    for case in prog["cases"]:
        outdir = os.path.join(OUT, "case_%s_%d" % (case["kind"], len(results)))
        os.makedirs(outdir, exist_ok=True)
        argv = [expand(t) for t in case["argv"]]
        cp = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT)
        exit_ok = cp.returncode == case["expected_exit"]
        checks = []
        if exit_ok:
            for a in case["assertions"]:
                r = check_assertion(a, outdir)
                checks.append({"kind": a["kind"], "path": a["path"], "ok": r})
                ok_all = ok_all and r
        else:
            # keep actual stderr for error cases
            with open(os.path.join(outdir, "stderr.txt"), "w", encoding="utf-8") as f:
                f.write(cp.stderr)
            for a in case["assertions"]:
                r = check_assertion(a, outdir)
                checks.append({"kind": a["kind"], "path": a["path"], "ok": r})
                ok_all = ok_all and r
        case_ok = exit_ok and all(c["ok"] for c in checks)
        ok_all = ok_all and case_ok
        results.append({"kind": case["kind"], "argv0": case["argv"][2] if len(case["argv"]) > 2 else case["argv"][0], "exit": cp.returncode, "expected_exit": case["expected_exit"], "ok": case_ok, "assertions": checks, "stderr": cp.stderr.strip()})

for i, comp in enumerate(doc["composition_cases"]):
    outdir = os.path.join(OUT, "composition_%d" % i)
    os.makedirs(outdir, exist_ok=True)
    exits = []
    stderr = ""
    for cmd in comp["commands"]:
        argv = [expand(t) for t in cmd]
        cp = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT)
        exits.append(cp.returncode)
        stderr += cp.stderr
    exit_ok = all(e == comp["expected_exit"] for e in exits)
    checks = []
    if exit_ok:
        for a in comp["assertions"]:
            r = check_assertion(a, outdir)
            checks.append({"kind": a["kind"], "path": a["path"], "ok": r})
            ok_all = ok_all and r
    comp_ok = exit_ok and all(c["ok"] for c in checks)
    ok_all = ok_all and comp_ok
    results.append({"kind": "composition", "commands": len(comp["commands"]), "exits": exits, "ok": comp_ok, "assertions": checks, "stderr": stderr.strip()})

json.dump(results, open(os.path.join(ROOT, "outputs/making_history/replay_verify_results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
for r in results:
    print(r.get("kind"), "OK" if r["ok"] else "FAIL", json.dumps({k: v for k, v in r.items() if k not in ("ok", "kind", "assertions")}, ensure_ascii=False))
    if not r["ok"]:
        print(json.dumps(r.get("assertions"), ensure_ascii=False))
print("ALL_OK" if ok_all else "SOME_FAILED")
sys.exit(0 if ok_all else 1)
