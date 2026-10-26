"""Independent numerical/address check of the v7 consolidated census report."""
import csv
import gzip
import hashlib
import json
import ntpath
import re
import sys
from collections import Counter
from pathlib import Path

B = Path(__file__).resolve().parents[3] / "output/20261026_wrd_raw_census_v7"


def load(name):
    return json.loads((B / name).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    S, P, M, E, N, V, A = [load(n) for n in ("SUMMARY.json", "PHYSICAL_ROOTS.json", "SKILL29_LINEAGE_MAP.json", "EXPORT_COVERAGE_AUDIT.json", "NINE_CHANNEL_SERVICE_CENSUS.json", "EVALUATION_BRANCH_ROOTS.json", "ADDITIONAL_ORIGINAL_ROOTS.json")]
    checks, failures = [], []

    def check(name, condition, detail=None):
        checks.append({"check": name, "passed": bool(condition), "detail": detail})
        if not condition:
            failures.append(name)

    check("primary totals exact", S["primary_physical_totals"] == P["totals"])
    check("copy cache exact", S["workspace_input_or_copy_cache"] == P["category_totals"]["workspace_input_or_copy_cache"])
    all_original_roots = P["roots"] + A["roots"]
    check("root statuses", S["root_scan_status_counts"] == dict(Counter(r["scan_status"] for r in all_original_roots)))
    check("frozen physical base SHA unchanged", A["frozen_base_sha256_unchanged"] == sha(B / "PHYSICAL_ROOTS.json"))
    check("frozen base totals unchanged", A["frozen_base_totals_preserved"] == P["totals"])
    check("address count169", S["root_addresses"] == A["known_address_union_count"] == len(all_original_roots) == 169)
    check("additional root count119", S["additional_original_iteration_or_case_control_roots"] == A["additional_address_count"] == len(A["roots"]) == 119)
    check("additional incremental files", S["additional_incremental_file_paths"] == A["totals"]["incremental_files"] == 51701)
    check("additional incremental bytes", S["additional_incremental_logical_bytes"] == A["totals"]["incremental_logical_bytes"] == 2561362264)
    check("base plus additional logical files", S["base_plus_additional_path_files"] == A["base_plus_additional_path_files"] == P["totals"]["logical_path_files"] + A["totals"]["incremental_files"] == 791868)
    check("base plus additional logical bytes", S["base_plus_additional_path_bytes_without_content_dedup"] == A["base_plus_additional_path_bytes_without_content_dedup"] == P["totals"]["logical_path_bytes"] + A["totals"]["incremental_logical_bytes"] == 75189980899)
    check("carrier counts remain filename counts", S["additional_carrier_filename_counts_not_new_unique_sessions"] == A["filename_counts"])
    for a, b in [("original_enterprise_sources", "original_enterprise_conversations"), ("retained_skills", "retained_skills"), ("logical_jobs", "logical_jobs"), ("catalog_attempt_references", "catalog_episode_references"), ("recoverable_native_contexts", "canonical_recoverable_contexts"), ("assistant_response_positions", "canonical_assistant_response_positions"), ("tool_call_blocks", "canonical_tool_call_blocks")]:
        check("summary/map:" + a, S[a] == M[b])
    stage = E["frozen_canonical"]["by_original_kind_not_semantic_gold"]
    check("canonical messages", S["canonical_messages"] == sum(x["messages"] for x in stage.values()) == 64559)
    check("canonical nonempty", S["nonempty_assistant_response_positions"] == sum(x["nonempty_assistant_positions"] for x in stage.values()) == 32014)
    check("nine service bytes", S["service_event_bytes"] == N["channel_event_file_bytes"] == sum(r["bytes"] for r in N["channels"]))
    check("nine service ids", S["service_distinct_native_request_ids"] == N["union_distinct_identifiers"]["native_request_id"])
    check("nine service lanes", S["original_service_lanes"] == N["unique_original_channel_event_files"] == 9)
    for r in N["channels"]:
        p = Path(r["original_event_file"])
        check("original service file stat/hash:" + str(r["lane"]), p.is_file() and p.stat().st_size == r["bytes"] and sha(p) == r["sha256_before"] == r["sha256_after"])
    check("eval metadata files", S["later_evaluation_metadata_files_not_additive_with_primary"] == V["logical_metadata_files"] == sum(r["files"] for r in V["roots"]))
    check("eval metadata bytes", S["later_evaluation_metadata_bytes_not_additive_with_primary"] == V["logical_metadata_bytes"] == sum(r["logical_metadata_bytes"] for r in V["roots"]))

    roots = list(csv.DictReader((B / "ROOTS_ALL_50.csv").open(encoding="utf-8-sig")))
    pr = {r["path"]: r for r in P["roots"]}
    check("frozen50 root csv identities", len(roots) == 50 and {r["path"] for r in roots} == set(pr))
    for r in roots:
        for k in ("path", "role", "purpose", "exists", "scan_status", "files", "logical_path_bytes", "filesystem_identity_unique_files", "filesystem_identity_unique_file_bytes"):
            check("root csv:" + r["path"] + ":" + k, r[k] == str(pr[r["path"]].get(k, "")))
    check("frozen50 original root addresses exist", all(Path(r["path"]).exists() for r in roots))
    all_csv = list(csv.DictReader((B / "ROOTS_ALL.csv").open(encoding="utf-8-sig")))
    roots_union = {r["path"]: r for r in all_original_roots}
    check("union root csv identities", len(all_csv) == len(roots_union) == 169 and {r["path"] for r in all_csv} == set(roots_union))
    for r in all_csv:
        original = roots_union[r["path"]]
        for k in ("path", "role", "purpose", "scan_status", "files", "logical_path_bytes", "filesystem_identity_unique_files", "filesystem_identity_unique_file_bytes"):
            check("union root csv:" + r["path"] + ":" + k, r[k] == str(original.get(k, "")))
        check("union original root exists:" + r["path"], Path(r["path"]).exists())

    # Recount the supplemental closed metadata ledger, without rescanning the
    # 740k original physical tree or opening recorded bodies.
    def norm(path):
        return ntpath.normcase(ntpath.normpath(str(path)))

    added_counts, added_bytes, added_names = Counter(), Counter(), Counter()
    added_paths, added_ids = set(), set()
    duplicate_paths, wrong_roots, old_overlap = [], [], []
    extra_by_id = {r["root_id"]: r for r in A["roots"]}
    old_scanned = [norm(r["path"]) for r in P["roots"] if r.get("recursive_scan")]
    with gzip.open(A["controlled_file_ledger"], "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            p = norm(r["source_path"])
            if p in added_paths:
                duplicate_paths.append(p)
            added_paths.add(p)
            root = norm(extra_by_id[r["root_id"]]["path"])
            if not p.startswith(root + "\\"):
                wrong_roots.append(p)
            if any(p.startswith(root + "\\") for root in old_scanned):
                old_overlap.append(p)
            added_counts[r["root_id"]] += 1
            added_bytes[r["root_id"]] += r["bytes"]
            added_names[str(r.get("original_filename", Path(r["source_path"]).name))] += 1
            added_ids.add((r["filesystem_device"], r["filesystem_file_id"]))
    check("supplement ledger paths unique", not duplicate_paths)
    check("supplement paths contained in declared root", not wrong_roots)
    check("supplement old counted descendant roots pruned", not old_overlap, {"overlap_path_count": len(old_overlap)})
    check("supplement ledger total files", len(added_paths) == A["totals"]["logical_path_files"] == 51701)
    check("supplement ledger total bytes", sum(added_bytes.values()) == A["totals"]["logical_path_bytes"])
    check("supplement ledger file identities", len(added_ids) == A["totals"]["within_additional_unique_file_identities"])
    for r in A["roots"]:
        check("supplement root closed count:" + r["path"], added_counts[r["root_id"]] == r["files"])
        check("supplement root closed bytes:" + r["path"], added_bytes[r["root_id"]] == r["logical_path_bytes"])
    check("supplement no global identity dedup claim", A["global_identity_union_across_base_and_additional_not_computed"])
    for r in csv.DictReader((B / "STAGE_COUNTS.csv").open(encoding="utf-8-sig")):
        k = r["old_catalog_stage_not_semantic_gold"]
        check("stage jobs:" + k, r["logical_jobs"] == str(M["jobs_by_stage"].get(k, "")))
        check("stage attempts:" + k, int(r["catalog_attempt_directory_references"]) == M["episodes_by_stage"][k])
        for j in ("sessions", "messages", "assistant_positions", "nonempty_assistant_positions", "tool_call_positions", "visible_text_positions"):
            check("stage csv:" + k + ":" + j, int(r[j]) == stage[k][j])
    overview = list(csv.DictReader((B / "SKILL29_OVERVIEW.csv").open(encoding="utf-8-sig")))
    skills = {r["skill_id"]: r for r in M["skills"]}
    check("29 skill csv identities", len(overview) == 29 and {r["skill_id"] for r in overview} == set(skills))
    final_count = 0
    for r in overview:
        for k in r:
            check("skill csv:" + r["skill_id"] + ":" + k, r[k] == str(skills[r["skill_id"]][k]))
        p = Path(r["entrypoint"])
        check("skill entrypoint exists:" + r["skill_id"], p.is_file())
        x = json.loads(p.read_text(encoding="utf-8"))
        check("skill episode count:" + r["skill_id"], len(x["all_related_episode_ids"]) == int(r["all_related_episodes"]))
        check("skill direct jobs:" + r["skill_id"], len(x["direct_job_ids"]) == int(r["direct_jobs"]))
        for f in x["final_files"]:
            p = Path(f["frozen_skill_file"])
            check("frozen final resource:" + r["skill_id"] + "/" + f["relative_path"], p.is_file() and p.stat().st_size == f["bytes"] and sha(p) == f["sha256"])
            final_count += 1
    check("final resources154", final_count == 154)

    # Independent recount: tool blocks are not generally the same unit as
    # assistant positions, even though these native transcripts have max one.
    block_count, max_blocks = 0, 0
    canonical_path = B.parent / "20261025_wrd_training_dataset/bundle/canonical/native_episodes.jsonl.gz"
    with gzip.open(canonical_path, "rt", encoding="utf-8") as f:
        for line in f:
            for m in json.loads(line)["messages"]:
                if m.get("role") == "assistant" and isinstance(m.get("content"), list):
                    n = sum(isinstance(b, dict) and b.get("type") == "toolCall" for b in m["content"])
                    block_count += n
                    max_blocks = max(max_blocks, n)
    check("actual tool blocks independent canonical recount", block_count == S["tool_call_blocks"] == 30438, {"max_blocks_per_response": max_blocks})
    examples = load("REPRESENTATIVE_ORIGINAL_PATHS.json")
    for x in examples:
        for k in ("attempt_path", "session_events", "request.json", "result.json"):
            check("original sample address:" + x["stage"] + ":" + k, Path(x[k]).exists())
    md = (B / "RAW_DATA_LOCATIONS.md").read_text(encoding="utf-8")
    links = re.findall(r"\]\(<(/?[DE]:/[^>]+)>\)", md)
    missing = []
    for p in links:
        q = p[1:] if re.match(r"^/[DE]:/", p) else p
        if not Path(q).exists():
            missing.append(q)
    check("absolute original markdown links currently exist", not missing, {"links": len(links), "missing": missing})
    check("226 is training isolation not address exclusion", S["original226_training_boundary_unchanged"] and "其地址/元数据可在普查单列" in md and len(V["roots"]) == 8)
    check("no raw sufficiency or full semantic claim", not S["actual_trainable_sample_count_established_by_this_census"] and not S["all_raw_data_semantically_audited"] and not S["content_deduplication_of_all_physical_files_complete"])
    check("no directory-omission means archive-missing inference", "清单漏根不自动等于相关所有会话没归档" in md)
    check("1763 explicitly old parsed entrance only", "旧已解析入口的原生会话上下文" in md and "不是新发现全部目录的会话总量" in md and "Old parsed 1763 contexts only" in S["canonical_semantic_counts_scope"])
    check("supplement carrier counts not semantic examples", "additional_carrier_filename_counts_not_new_unique_sessions" in S and "独立新会话" in md and "载体" in md)
    missing_d = "D:/skillloop/output/20261021_v10_reuse_iterations"
    supplementary = []
    for p in B.glob("*.json"):
        if not any(k in p.name for k in ("SUPPLEMENT", "ADDENDUM", "ADDITIONAL")):
            continue
        item = json.loads(p.read_text(encoding="utf-8"))
        if str(item.get("source_path", "")).replace("\\", "/").lower() == missing_d.lower():
            supplementary.append(p.name)
            check("supplement preserves original primary SHA:" + p.name, item.get("primary_census_sha256_unchanged") == sha(B / "PHYSICAL_ROOTS.json"))
            ledger = Path(item["controlled_file_ledger"])
            with gzip.open(ledger, "rt", encoding="utf-8") as f:
                contents = [json.loads(line) for line in f if line.strip()]
            check("D-v10 metadata ledger counts", len(contents) == item["files"] and sum(r["bytes"] for r in contents) == item["logical_path_bytes"])
            check("D-v10 original metadata files stat", all(Path(r["source_path"]).is_file() and Path(r["source_path"]).stat().st_size == r["bytes"] for r in contents))
    d_scope_fixed = str(Path(missing_d)) in roots_union and missing_d in md
    check("named D-v10 root included or explicit supplementary", d_scope_fixed, {"exists": Path(missing_d).exists(), "supplementary_candidates": supplementary})
    review_names = ["RAW_DATA_LOCATIONS.md", "SUMMARY.json", "ROOTS_ALL_50.csv", "ROOTS_ALL.csv", "STAGE_COUNTS.csv", "SKILL29_OVERVIEW.csv", "PHYSICAL_ROOTS.json", "SKILL29_LINEAGE_MAP.json", "EXPORT_COVERAGE_AUDIT.json", "NINE_CHANNEL_SERVICE_CENSUS.json", "EVALUATION_BRANCH_ROOTS.json", "ADDITIONAL_ORIGINAL_ROOTS.json"]
    review_names.extend(supplementary)
    report = {
        "schema_version": "wrd-v7-independent-summary-review",
        "status": "PASS_WITH_LIMITED_SCOPE" if not failures else "FAIL_PENDING_CORRECTION",
        "reviewed_artifact_pins": [{"path": str(B / n), "sha256": sha(B / n), "bytes": (B / n).stat().st_size} for n in review_names],
        "checks": checks, "failure_count": len(failures), "failures": failures,
        "actual_checks_summary": {"structured_and_address_checks": len(checks), "frozen50_original_root_addresses_stat_only": 50, "union_original_root_addresses_stat_only": len(all_csv), "additional_closed_metadata_ledger_rows_recounted": len(added_paths), "service_original_files_SHA_rechecked": 9, "final_frozen_skill_resources_SHA_rechecked": final_count, "representative_stage_paths_stat_only": len(examples) * 4, "absolute_markdown_original_links_stat_only": len(links), "canonical_tool_call_blocks_independently_recounted": block_count},
        "scope_issue_reported_to_parent_and_corrected": "D:/skillloop/output/20261021_v10_reuse_iterations was absent from frozen50 roots. D-v10 and further discovered roots are now explicitly counted in the supplemental ledger and169-address union, while the frozen72.63GB remains unchanged. Directory omission alone does not establish missing archived sessions.",
        "interpretation_review": ["93/106 are explicitly filtered derived subsets, not raw population.", "Actor/review original bodies remain in canonical even when old auxiliary rows carry references only.", "Stage labels are expressly old catalog labels, not role gold.", "Output versions and shared skill lineage counts are not independent training tasks.", "Original226 isolation is unchanged; later evaluation roots are counted separately rather than hidden."],
        "limitations": ["No740k physical rescan; original full physical ledgers remain pinned report evidence.", "No complete semantic/provenance or training-admission audit.", "No global complete-disk census claim.", "Markdown/table language was manually reviewed, with numerical consistency checked against pinned source reports."],
        "training_started": False, "new_model_or_agent_calls": 0, "original_reports_modified": False,
        "script_sha256": sha(__file__),
    }
    destination = B / "REVIEW.json"
    if destination.is_file():
        old_bytes = destination.read_bytes()
        old_sha = hashlib.sha256(old_bytes).hexdigest()
        history = B / "history" / ("independent_review_" + old_sha + ".json")
        history.parent.mkdir(exist_ok=True)
        if not history.exists():
            history.write_bytes(old_bytes)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(checks), "failures": failures, "final_files": final_count, "md_links": len(links), "review_sha256": sha(B / "REVIEW.json")}, ensure_ascii=True))


def incremental_final_binding():
    """Retain the169-version audit and audit only the final six roots/deltas."""
    destination = B / "REVIEW.json"
    prior_bytes = destination.read_bytes()
    prior_sha = hashlib.sha256(prior_bytes).hexdigest()
    prior = json.loads(prior_bytes)
    assert prior_sha == "8fd426b9c09abaf0b0ea4ffd43b64421dee6d8fefeddc9d99fc6cc751bb91a13"
    checks, failures = [], []

    def check(name, value, detail=None):
        checks.append({"check": name, "passed": bool(value), "detail": detail})
        if not value:
            failures.append(name)

    S, P, A, F, R, G = [load(n) for n in ("SUMMARY.json", "PHYSICAL_ROOTS.json", "ADDITIONAL_ORIGINAL_ROOTS.json", "FINAL_DISCOVERY_ROOTS.json", "ASSISTED_REPAIR_SOURCE.json", "FINAL_REGISTRY_RECONCILIATION.json")]
    check("prior169 full audit passed", prior["status"] == "PASS_WITH_LIMITED_SCOPE" and prior["failure_count"] == 0 and len(prior["checks"]) == 2866)
    changed = {"RAW_DATA_LOCATIONS.md", "SUMMARY.json", "ROOTS_ALL.csv"}
    for p in prior["reviewed_artifact_pins"]:
        if Path(p["path"]).name not in changed:
            check("prior verified source remains byte identical:" + Path(p["path"]).name, sha(p["path"]) == p["sha256"])
    check("final root supplement original SHA pins", F["primary_census_sha256_unchanged"] == sha(B / "PHYSICAL_ROOTS.json") and F["additional_census_sha256_unchanged"] == sha(B / "ADDITIONAL_ORIGINAL_ROOTS.json"))
    for name, expected in R["frozen_prior_census_sha256"].items():
        check("assisted repair prior SHA:" + name, sha(B / name) == expected)
    previous_roots = P["roots"] + A["roots"]
    final_roots = F["roots"] + R["roots"]
    all_roots = previous_roots + final_roots
    norm = lambda p: ntpath.normcase(ntpath.normpath(str(p)))
    old_dirs = [norm(r["path"]) for r in previous_roots]
    new_dirs = [norm(r["path"]) for r in final_roots]
    check("six additional directory addresses unique", len(new_dirs) == len(set(new_dirs)) == 6)
    check("six directory roots do not overlap old169", not any(n == p or n.startswith(p + "\\") or p.startswith(n + "\\") for n in new_dirs for p in old_dirs))
    check("six directory roots mutually disjoint", not any(a != b and (a.startswith(b + "\\") or b.startswith(a + "\\")) for a in new_dirs for b in new_dirs))
    check("six original directory addresses exist", all(Path(r["path"]).is_dir() for r in final_roots))
    seen_paths, records = set(), []
    final_count, final_bytes = Counter(), Counter()
    roots_by_id = {r["root_id"]: r for r in F["roots"]}
    with gzip.open(F["controlled_file_ledger"], "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            records.append(row)
            final_count[row["root_id"]] += 1
            final_bytes[row["root_id"]] += row["bytes"]
            check("final ledger original file stat:" + row["source_path"], Path(row["source_path"]).is_file() and Path(row["source_path"]).stat().st_size == row["bytes"])
            check("final ledger path contained:" + row["source_path"], norm(row["source_path"]).startswith(norm(roots_by_id[row["root_id"]]["path"]) + "\\"))
            seen_paths.add(norm(row["source_path"]))
    check("final five ledger total count", len(records) == len(seen_paths) == F["totals"]["incremental_files"] == 2288)
    check("final five ledger total bytes", sum(row["bytes"] for row in records) == F["totals"]["incremental_logical_bytes"] == 79705856)
    for root in F["roots"]:
        check("final root closed count:" + root["path"], final_count[root["root_id"]] == root["files"])
        check("final root closed bytes:" + root["path"], final_bytes[root["root_id"]] == root["logical_path_bytes"])
    repair_records = [json.loads(line) for line in gzip.open(R["directory_file_ledger"], "rt", encoding="utf-8") if line.strip()]
    check("repair ledger66/bytes", len(repair_records) == R["totals"]["incremental_directory_files"] == 66 and sum(r["bytes"] for r in repair_records) == R["totals"]["incremental_directory_logical_bytes"] == 1162823)
    repair_root = norm(R["roots"][0]["path"])
    check("repair ledger paths unique and contained", len({norm(r["source_path"]) for r in repair_records}) == 66 and all(norm(r["source_path"]).startswith(repair_root + "\\") for r in repair_records))
    check("repair original file metadata stat", all(Path(r["source_path"]).is_file() and Path(r["source_path"]).stat().st_size == r["bytes"] for r in repair_records))
    check("six new ledger paths not inside old roots", not any(norm(r["source_path"]).startswith(d + "\\") for r in records + repair_records for d in old_dirs))
    check("final175 directory count", S["root_addresses"] == R["known_directory_address_union_count"] == len(all_roots) == 175)
    check("final175 logical path count", S["base_plus_additional_path_files"] == A["base_plus_additional_path_files"] + len(records) + len(repair_records) == 794222)
    check("final175 logical path bytes", S["base_plus_additional_path_bytes_without_content_dedup"] == A["base_plus_additional_path_bytes_without_content_dedup"] + sum(r["bytes"] for r in records + repair_records) == 75270849578)
    check("final175 root scan statuses", S["root_scan_status_counts"] == dict(Counter(r["scan_status"] for r in all_roots)))
    check("final summary supplement count fields", S["final_independent_discovery_roots"] == 5 and S["final_independent_discovery_incremental_paths"] == 2288 and S["final_independent_discovery_incremental_logical_bytes"] == 79705856 and S["historical_assisted_repair_directory_roots"] == 1 and S["historical_assisted_repair_incremental_paths"] == 66 and S["historical_assisted_repair_incremental_logical_bytes"] == 1162823)
    check("final carrier counts named as filenames only", S["final_independent_discovery_carrier_filename_counts_not_unique_sessions"] == F["filename_counts"])
    csv_roots = list(csv.DictReader((B / "ROOTS_ALL.csv").open(encoding="utf-8-sig")))
    all_by_path = {r["path"]: r for r in all_roots}
    check("final CSV175 root identities", len(csv_roots) == len(all_by_path) == 175 and {r["path"] for r in csv_roots} == set(all_by_path))
    for row in csv_roots:
        for key in ("path", "role", "purpose", "scan_status", "files", "logical_path_bytes"):
            check("final CSV root field:" + row["path"] + ":" + key, row[key] == str(all_by_path[row["path"]].get(key, "")))
    # The exact C-file is a stat-only exception, never opened or hashed here.
    external = R["external_exact_file"]
    external_stat = Path(external["source_path"]).stat()
    check("external C exact original stat only", external_stat.st_size == external["bytes"] == 75555936 and not external["content_opened"] and not external["content_hashed"] and not external["parent_directory_enumerated"])
    check("external C exact file separate from directory totals", R["totals"]["directory_and_external_single_file_kept_separate"] and S["external_exact_original_session_stat_only_not_added_to_directory_totals"] == external and not any(norm(external["source_path"]).startswith(norm(r["path"]) + "\\") for r in all_roots))
    # Independently resolve154 old references:77 catalog job fields and77
    # episode execution/profile fields, all to the same configuration object.
    ROOT = B.parents[1]
    ref_paths = [B / "indexes/job_physical_path_references.jsonl.gz", B / "indexes/provider_runtime_path_references.jsonl.gz"]
    refs = []
    for p in ref_paths:
        refs.extend(json.loads(line) for line in gzip.open(p, "rt", encoding="utf-8") if "20261024_concurrency9" in line)
    check("concurrency9 actual154 references", len(refs) == G["concurrency9_reference_precision"]["references"] == 154)
    check("concurrency9 profile only one path", len({norm(r["path"]) for r in refs}) == 1 and all(norm(r["path"]).endswith("\\channel8\\native_profile.json") and r["json_pointer"].endswith("/profile") for r in refs))
    job_ids = {r["job_id"] for r in refs if r.get("job_id")}
    jobs_path = ROOT / "output/20261025_wrd_training_dataset/bundle/catalog/jobs.jsonl"
    jobs = {r["id"]: r for r in (json.loads(line) for line in jobs_path.open(encoding="utf-8")) if r["id"] in job_ids}
    resolved = 0
    for r in refs:
        value = jobs[r["job_id"]] if r.get("job_id") else json.loads(Path(r["source_metadata_file"]).read_text(encoding="utf-8-sig"))
        for key in r["json_pointer"].split("/")[1:]:
            key = key.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if isinstance(value, list) else value[key]
        check("original profile reference resolves:" + str(resolved), norm(value) == norm(r["path"]))
        resolved += 1
    md = (B / "RAW_DATA_LOCATIONS.md").read_text(encoding="utf-8")
    check("final Markdown exact requested SHA", sha(B / "RAW_DATA_LOCATIONS.md") == "b4d6bb1fc394d5324851085b30284da22ad51567f6ecdec8598073c4c772fe68")
    check("C file is not176th directory in prose", "不计为第176个目录" in md and "75,555,936" in md and "未读取/哈希/解析正文" in md)
    check("profile refs not154 new sessions in prose", "不是154个新会话" in md and "channel8/native_profile.json" in md)
    check("old parsed1763 scope and226 isolation retained", "不是新发现全部目录的会话总量" in md and S["original226_training_boundary_unchanged"] and not S["actual_trainable_sample_count_established_by_this_census"] and not S["training_started"])
    check("registry bound175 and supplemental roots", G["finite_registry_scope_root_addresses_after_supplement"] == 175 and {norm(r["path"]) for r in G["supplement_roots"]} == set(new_dirs) and sha(G["all_discovered_addresses_queryable_registry"]) == G["registry_sha256"])
    check("registry is bounded discovery not semantic exclusion", G["no_new_recursive_stat_or_byte_totals_claimed_by_this_review"] and not G["training_source_admission_or_91_106_filter_used"])
    prior_history = B / "history" / ("independent_review_" + prior_sha + ".json")
    prior_history.parent.mkdir(exist_ok=True)
    if not prior_history.exists():
        prior_history.write_bytes(prior_bytes)
    binding_names = ["RAW_DATA_LOCATIONS.md", "SUMMARY.json", "ROOTS_ALL.csv", "FINAL_DISCOVERY_ROOTS.json", "ASSISTED_REPAIR_SOURCE.json", "FINAL_REGISTRY_RECONCILIATION.json"]
    report = {"schema_version": "wrd-v7-independent-summary-review-final175-incremental", "status": "PASS_WITH_LIMITED_SCOPE" if not failures else "FAIL_PENDING_CORRECTION", "prior169_full_review": {"path": str(prior_history), "sha256": prior_sha, "passed_checks_reused": 2866}, "reviewed_artifact_pins": [{"path": str(B / n), "sha256": sha(B / n), "bytes": (B / n).stat().st_size} for n in binding_names], "incremental_checks": checks, "incremental_check_count": len(checks), "failure_count": len(failures), "failures": failures, "actual_incremental_work": {"new_directory_roots": 6, "new_file_ledger_rows_and_original_file_stats": len(records) + len(repair_records), "new_file_path_bytes": sum(r["bytes"] for r in records + repair_records), "concurrency9_original_profile_fields_independently_resolved": resolved, "external_exact_C_file": "stat only; no contents/hash/parent enumeration", "old740k_rescan": False, "old2866_checks_rerun": False}, "final_scope": {"directory_addresses": 175, "logical_path_files": 794222, "logical_path_bytes_without_content_dedup": 75270849578, "external_exact_original_file_not_in_directory_totals_bytes": 75555936}, "limitations": prior["limitations"] + ["Final registry preserves earlier/independent/semantic-unconfirmed references for lookup;175 is the bounded registered directory census, not a claim that every historical WRD artifact on disk was recovered.", "A physical carrier, configuration reference or shared copy is not an independent episode, SFT example, reasoning span or complete successful pipeline."], "training_started": False, "new_model_or_business_calls": 0, "reports_modified": False, "script_sha256": sha(__file__)}
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "incremental_checks": len(checks), "failures": failures, "report_sha256": sha(destination)}, ensure_ascii=True))


if __name__ == "__main__":
    incremental_final_binding() if "--incremental-final" in sys.argv else main()
