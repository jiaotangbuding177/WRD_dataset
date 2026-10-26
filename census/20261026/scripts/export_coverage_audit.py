"""Read-only audit of the old WRD export entrance and its successive filters.

This deliberately does not decide training admission, run a model, or claim that
the frozen bundle is the complete physical source universe.  No conversation or
reasoning body is copied to the report.
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / "output/20261025_wrd_training_dataset/bundle"
OUT = ROOT / "output/20261026_wrd_raw_census_v7"
TAG = re.compile(r"<(think|thinking|reasoning)(?:\s[^>]*)?>.*?</\1\s*>", re.I | re.S)


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def rel(p):
    try:
        return Path(p).relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def rows(p):
    p = Path(p)
    op = gzip.open if p.suffix == ".gz" else open
    with op(p, "rt", encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def pin(p):
    p = Path(p)
    return {"path": rel(p), "sha256": sha(p), "bytes": p.stat().st_size}


def nonempty(c):
    if isinstance(c, str):
        return bool(c.strip())
    if isinstance(c, list):
        return any(isinstance(x, dict) and (x.get("type") == "toolCall" or (x.get("type") == "text" and str(x.get("text", "")).strip())) for x in c)
    return bool(c)


def reasoning(c):
    n = chars = 0
    if isinstance(c, str):
        matches = list(TAG.finditer(c))
        return len(matches), sum(len(m.group()) for m in matches)
    if isinstance(c, list):
        for x in c:
            if not isinstance(x, dict):
                continue
            if x.get("type") in ("thinking", "reasoning", "redacted_thinking"):
                n += 1
                chars += len(str(x.get("thinking", x.get("reasoning", x.get("text", "")))))
            elif x.get("type") == "text":
                a, b = reasoning(x.get("text", ""))
                n += a
                chars += b
    return n, chars


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": "wrd-old-export-coverage-independent-audit-v7", "created_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Frozen old exporter entrance, every frozen native canonical/event object, and named successive derivation reports. Physical roots outside the frozen bundle are separately censused; no assertion of global original-source completeness.",
              "training_started": False, "new_model_calls": 0, "original_data_mutated": False,
              "units_warning": "enterprise source / native session / assistant position / token window / model call / reasoning delta frame are different units; counts below cannot be added across projections or treated as independent tasks."}
    scripts = {
        "old_builder": "research/data_prep/wrd_training/build.py",
        "old_training_exporter": "research/data_prep/wrd_training/training.py",
        "old_preflight": "research/data_prep/wrd_training_preflight/prepare.py",
        "v4_compiler": "research/data_prep/wrd_reasoning_v4/compile_native.py",
        "v4_curator": "research/data_prep/wrd_reasoning_v4/curate_native.py",
    }
    report["script_pins"] = {k: pin(ROOT / p) for k, p in scripts.items()}
    report["code_contract_findings"] = [
        {"category": "intentional_old_scope_choice_inadequate_for_requested_full_pipeline", "path": scripts["old_training_exporter"], "lines": [322, 323, 379, 380], "finding": "Only make/screen are primary; prepare/review/actor/legacy surviving targets go to auxiliary metadata references. Canonical holds their visible message bodies, but they were not equivalent compiled primary training inputs."},
        {"category": "not_included_in_primary_not_not_recorded", "path": scripts["old_preflight"], "lines": [41, 42, 43, 44, 46], "finding": "Preflight uses native_actions_core7.train plus recovered terminal labels as candidates; canonical histories are support/evidence, not the same fullchain primary SFT input."},
        {"category": "reasoning_omission_code_path_actual_effect_measured_separately", "path": scripts["old_training_exporter"], "lines": [44, 58, 63, 85, 97, 313], "finding": "Old cleaner deletes thinking/reasoning blocks and tagged text. Message-copy allowlist also does not copy top-level reasoning_content. Actual frozen event effect is counted below; this code is not evidence that these 1763 sessions contained nonempty hidden reasoning."},
        {"category": "format_specific_parser", "path": scripts["old_training_exporter"], "lines": [71, 85, 86, 89, 279], "finding": "Only openclaw_transport/session_events.jsonl type=message/message dict with five known roles is parsed. Raw OpenAI request-response pairs and SSE reasoning deltas are different formats and are not discovered or parsed by this entrance."},
        {"category": "legacy_mechanical_kind_inference", "path": scripts["old_builder"], "lines": [325, 329, 331], "finding": "Imported history kind is inferred by first substring make/screen/prepare/review/actor in the directory name. A business resume-screening route therefore falsely matches WRD screen; kind strings are not validated semantic stages."},
        {"category": "bounded_discovery_not_global_root_scan", "path": scripts["old_builder"], "lines": [291, 312, 320, 325, 414, 416], "finding": "Old sessions are discovered from state.db job episode paths/sibling attempts/record result episode_dir and legacy_usage references. Unreferenced historical roots or other log formats are outside discovery even when their records physically exist."},
    ]
    catalog = {r["episode_id"]: r for r in rows(BUNDLE / "catalog/episodes.jsonl")}
    by_stage = collections.defaultdict(collections.Counter)
    canonical = {}
    for r in rows(BUNDLE / "canonical/native_episodes.jsonl.gz"):
        c = by_stage[r["kind"]]
        c["sessions"] += 1
        c["messages"] += len(r["messages"])
        c["benchmark_flagged_sessions_by_old_detector"] += bool(r.get("benchmark_exposed"))
        for m in r["messages"]:
            if m.get("role") != "assistant":
                continue
            c["assistant_positions"] += 1
            c["nonempty_assistant_positions"] += nonempty(m.get("content"))
            c["tool_call_positions"] += isinstance(m.get("content"), list) and any(isinstance(b, dict) and b.get("type") == "toolCall" for b in m["content"])
            c["visible_text_positions"] += isinstance(m.get("content"), str) and bool(m["content"].strip()) or isinstance(m.get("content"), list) and any(isinstance(b, dict) and b.get("type") == "text" and bool(str(b.get("text", "")).strip()) for b in m["content"])
        canonical[r["episode_id"]] = {"kind": r["kind"], "messages": len(r["messages"]), "source_event_lines": r["source_event_lines"], "parse_issues": r.get("message_parse_issues", {})}
    report["frozen_canonical"] = {"pin": pin(BUNDLE / "canonical/native_episodes.jsonl.gz"), "catalog_sessions": len(catalog), "parsed_native_sessions": len(canonical), "by_original_kind_not_semantic_gold": dict(by_stage)}

    # Read every file-index row, then read each selected raw event CAS once.
    idx = {}
    aliases = unique = 0
    shas = set()
    for r in rows(BUNDLE / "archive/file_index.jsonl"):
        aliases += 1
        shas.add(r["sha256"])
        logical = r["logical_path"]
        if logical.startswith("episodes/") and (logical.count("/") <= 3 or logical.endswith("session_events.jsonl")) or logical in ("pipeline/conversations.json", "sources/original_evolution_corpus.jsonl", "sources/source_bindings.json"):
            idx[logical] = r
    report["frozen_archive_index"] = {"pin": pin(BUNDLE / "archive/file_index.jsonl"), "logical_aliases": aliases, "unique_content_objects": len(shas), "alias_is_not_sample": True}
    raw_counts = collections.Counter()
    raw_event_types = collections.Counter()
    raw_message_keys = collections.Counter()
    raw_unknown_roles = collections.Counter()
    event_issues = []
    raw_events_pins = []
    missing_canonical = []
    for eid, e in catalog.items():
        logical = f"episodes/{eid}/openclaw_transport/session_events.jsonl"
        ref = idx.get(logical)
        if not ref:
            if eid not in canonical:
                present = sorted(k[len(e["archive_path"]) + 1:] for k in idx if k.startswith(e["archive_path"] + "/"))
                missing_canonical.append({"episode_id": eid, "kind": e["kind"], "source_path": e["source_path"], "reason": "no_session_events_object_at_old_required_path", "frozen_other_files": present})
            continue
        p = BUNDLE / "archive" / ref["object"]
        data = p.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != ref["sha256"]:
            raise RuntimeError("Event CAS hash mismatch: " + eid)
        cnt = collections.Counter()
        event_lines = []
        # JSONL uses LF records. str.splitlines() would incorrectly split literal
        # Unicode line separators inside JSON strings and invent malformed rows.
        for line_number, line in enumerate(data.decode("utf-8-sig").split("\n"), 1):
            if not line.strip():
                continue
            cnt["nonblank_event_lines"] += 1
            try:
                r = json.loads(line)
            except (ValueError, TypeError):
                cnt["malformed_lines"] += 1
                continue
            if not isinstance(r, dict):
                cnt["nonobject_lines"] += 1
                continue
            raw_event_types[str(r.get("type"))] += 1
            m = r.get("message")
            if r.get("type") != "message" or not isinstance(m, dict):
                cnt["nonmessage_metadata_lines"] += 1
                # Count possible alternate message-shaped records, without assuming all metadata is missing content.
                if r.get("role") in ("assistant", "user", "tool", "toolResult"):
                    cnt["alternate_top_level_role_rows_not_parsed_by_old_exporter"] += 1
                continue
            raw_message_keys.update(m.keys())
            role = m.get("role")
            if role not in ("system", "user", "assistant", "toolResult", "tool"):
                raw_unknown_roles[str(role)] += 1
                cnt["unknown_role_lines"] += 1
                continue
            event_lines.append(line_number)
            cnt["accepted_messages"] += 1
            if role == "assistant":
                cnt["assistant_positions"] += 1
                cnt["assistant_nonempty_content"] += nonempty(m.get("content"))
                n, chars = reasoning(m.get("content"))
                cnt["reasoning_blocks_or_tags_old_cleaner_would_remove"] += n
                cnt["reasoning_block_or_tag_characters"] += chars
                for key in ("reasoning_content", "reasoning", "thinking"):
                    if m.get(key):
                        cnt["nonempty_top_level_" + key + "_not_copied_by_old_exporter"] += 1
                        cnt["top_level_" + key + "_characters"] += len(str(m[key]))
        raw_counts.update(cnt)
        raw_events_pins.append({"episode_id": eid, "logical_path": logical, "source_path": ref["source_path"], "sha256": digest, "bytes": len(data), "credential_redacted_archive_projection": ref.get("credential_redacted", False)})
        if eid in canonical:
            expected = canonical[eid]
            if cnt["accepted_messages"] != expected["messages"] or event_lines != expected["source_event_lines"]:
                event_issues.append({"episode_id": eid, "reason": "raw_accepted_event_line_mapping_differs_from_frozen_canonical"})
        else:
            missing_canonical.append({"episode_id": eid, "reason": "event_exists_but_no_accepted_messages" if not cnt["accepted_messages"] else "event_has_messages_but_canonical_omitted", "counts": dict(cnt)})
    for key in ("nonempty_top_level_reasoning_content_not_copied_by_old_exporter", "nonempty_top_level_reasoning_not_copied_by_old_exporter", "nonempty_top_level_thinking_not_copied_by_old_exporter", "alternate_top_level_role_rows_not_parsed_by_old_exporter", "malformed_lines", "unknown_role_lines"):
        raw_counts.setdefault(key, 0)
    report["status"] = "PASS_WITH_LIMITED_SCOPE" if not event_issues and len(raw_events_pins) == len(canonical) else "REQUIRES_INVESTIGATION"
    report["frozen_raw_event_reinspection"] = {"event_objects_independently_hashed": len(raw_events_pins), "all_selected_event_object_hashes_match_index": True, "counts": dict(raw_counts), "event_types": dict(raw_event_types), "message_field_presence_counts": dict(raw_message_keys), "unknown_roles": dict(raw_unknown_roles), "canonical_line_mapping_issues": event_issues, "not_in_canonical": missing_canonical, "no_reasoning_generalization_beyond_these_selected_event_objects": True}
    report["frozen_raw_event_reinspection"]["event_object_index"] = raw_events_pins
    absent = {r["episode_id"] for r in missing_canonical}
    known_event_shas = {r["sha256"] for r in raw_events_pins}
    copied_events = [r for k, r in idx.items() if k.endswith("/session_events.jsonl") and len(k.split("/")) > 4 and k.split("/")[1] in absent]
    report["frozen_raw_event_reinspection"]["59_missing_direct_event_summary"] = {
        "episodes": len(absent),
        "episodes_with_request": sum(any(k == f"episodes/{eid}/request.json" or k == f"episodes/{eid}/openclaw_transport/request.json" for k in idx) for eid in absent),
        "episodes_with_result": sum(f"episodes/{eid}/result.json" in idx for eid in absent),
        "copied_upstream_session_event_resources_inside_their_workspace": len(copied_events),
        "copied_upstream_session_unique_shas": len({r["sha256"] for r in copied_events}),
        "copied_upstream_sessions_matching_existing_canonical_event_sha": sum(r["sha256"] in known_event_shas for r in copied_events),
        "copied_upstream_sessions_are_not_59_own_missing_responses": True,
        "other_physical_paths_or_formats_not_ruled_out": True,
    }

    # This small source list is an index, while the separately frozen corpus and
    # per-conversation source objects contain original messages.
    source_index_ref = idx["pipeline/conversations.json"]
    source_index = load(BUNDLE / "archive" / source_index_ref["object"])
    report["enterprise_source_entrance"] = {"pipeline_index": {"rows": len(source_index), "keys_union": sorted(set().union(*(x.keys() for x in source_index))), "pin": {k: source_index_ref[k] for k in ("logical_path", "source_path", "sha256", "bytes", "object")}}, "index_is_not_native_skill_builder_sessions": True, "actual_body_source_bindings": "output/20261021_workflow_skill_library/source_bindings.json -> sources/<conversation_id>/conversation.json", "original_corpus_frozen": idx.get("sources/original_evolution_corpus.jsonl"), "source_bindings_frozen": idx.get("sources/source_bindings.json"), "not_all_source_conversations_are_independent_successful_skill_production_chains": True}
    actions = collections.defaultdict(collections.Counter)
    for r in rows(BUNDLE / "training_audit/action_index.jsonl"):
        c = actions[r["kind"]]
        c["assistant_positions"] += 1
        c["old_filter_pass"] += not r["filter_reasons"]
        c["old_filter_hold"] += bool(r["filter_reasons"])
        for reason in r["filter_reasons"]:
            c["reason:" + reason] += 1
    streams = {}
    for p in sorted((BUNDLE / "datasets").glob("*.jsonl.gz")):
        c = collections.Counter()
        keys = set()
        for r in rows(p):
            c["rows"] += 1
            c["kind:" + str(r.get("kind"))] += 1
            keys.update(r)
        streams[p.name] = {"pin": pin(p), "counts": dict(c), "contains_prompt_body": "prompt" in keys, "contains_completion_body": "completion" in keys, "metadata_reference_only_when_no_prompt_completion": "prompt" not in keys and "completion" not in keys}
    report["old_primary_auxiliary_split"] = {"all_position_audit_by_kind": dict(actions), "all_dataset_streams": streams}
    eligibility_path = ROOT / "output/20261025_wrd_training_preflight/prepared_gated/public/audit/eligibility.jsonl.gz"
    elig = collections.Counter()
    structures = collections.Counter()
    combinations = collections.Counter()
    for r in rows(eligibility_path):
        elig["rows"] += 1
        elig["kind:" + r["kind"]] += 1
        elig["review:" + r["semantic_review"]] += 1
        elig["publication_approved"] += r["publication_approved"]
        elig["training_eligible"] += r["training_eligible"]
        combinations[(r["semantic_review"], r["publication_approved"], r["training_eligible"])] += 1
        for k in ("structural_errors", "structural_warnings"):
            for v in r[k]:
                structures[k + ":" + str(v)] += 1
    report["old_preflight_eligibility_independent_table_census"] = {"pin": pin(eligibility_path), "counts": dict(elig), "review_publication_eligibility_combinations": [{"review": k[0], "publication_approved": k[1], "training_eligible": k[2], "rows": v} for k, v in combinations.items()], "structural_reason_occurrences_not_disjoint_rows": dict(structures), "not_ai_reviewed_is_not_negative_semantic_quality": True, "public_hold_is_not_source_unusable_proof": True}
    legacy = []
    for e in catalog.values():
        if e.get("cohort") == "imported_history":
            name = Path(e["source_path"]).name
            reqref = idx.get(e["archive_path"] + "/request.json")
            req = load(BUNDLE / "archive" / reqref["object"]) if reqref else {}
            legacy.append({"episode_id": e["episode_id"], "directory_name": name, "original_inferred_kind": e["kind"], "route_id": e["route_id"], "has_canonical": e["episode_id"] in canonical, "old_native_verified": e.get("native_verified"), "semantic_kind_not_proven_by_substring": True, "original_request_pin": {k: reqref[k] for k in ("logical_path", "sha256", "source_sha256", "bytes", "object")} if reqref else None, "original_request_stage": req.get("stage"), "original_request_task_id": req.get("task_id"), "known_business_route_false_screen_match": "jd-resume-screening" in name and e["kind"] == "screen", "original_evaluation_stage_mislabelled_review": e["kind"] == "review" and req.get("stage") == "evaluation"})
    report["legacy_name_based_kind_requires_reclassification"] = {"episodes": len(legacy), "by_inferred_kind": dict(collections.Counter(r["original_inferred_kind"] for r in legacy)), "by_original_request_stage": dict(collections.Counter(str(r["original_request_stage"]) for r in legacy)), "known_resume_route_false_screen_matches": sum(r["known_business_route_false_screen_match"] for r in legacy), "evaluation_arms_false_review_matches": sum(r["original_evaluation_stage_mislabelled_review"] for r in legacy), "old_native_verified_count": sum(bool(r["old_native_verified"]) for r in legacy), "old_quarantine_due_native_verification_not_an_admitted_positive_count": True, "generation_stage_is_generic_protocol_and_not_proof_of_skill_maker_role": True, "rows": legacy}

    # Separate report branches, never describe later accepted subset as raw size.
    extracts = {
        "initial_export": ("output/20261025_wrd_training_dataset/bundle/summary.json", ["original_sources", "episodes", "jobs", "retained29_verified", "training"]),
        "preflight_input_and_publication_selection": ("output/20261025_wrd_training_preflight/prepared_gated/public/reports/preparation.json", ["counts", "written_rows", "ai_reviewed_targets", "ai_adjudicated_decisions", "unreviewed_targets_not_training_eligible", "human_gold"]),
        "old_public_token_compilation": ("output/20261025_wrd_training_preflight/work_compiled_full/report.json", ["counts", "by_kind", "coverage_public_candidates", "coverage_training_eligible", "failure_counts"]),
        "old_controlled_all_token_compilation": ("output/20261025_wrd_training_preflight/work_compiled_controlled_all/report.json", ["counts", "by_kind", "coverage_public_candidates", "coverage_training_eligible", "failure_counts"]),
        "actual_93_published_subset": ("output/20261025_wrd_training_preflight/prepared_gated/public/reports/sft_statistics.json", ["buckets_exclusive", "cumulative_32k", "by_kind_and_target_kind", "observed_distinct_teacher_episodes", "human_gold"]),
        "v3_fullchain_recovery_same_frozen_sessions": ("output/20261025_wrd_fullchain_reaudit/FULLCHAIN_COVERAGE.json", ["status", "controlled_master", "public_projection"]),
        "v4_native_mechanical_compilation_same_frozen_sessions": ("output/20261025_wrd_reasoning_recovery_v4/native_compiled_controlled_final/REPORT.json", ["counts", "by_stage", "mechanical_hold_reasons"]),
        "v4_quality_curated_native": ("output/20261025_wrd_reasoning_recovery_v4/curated_native/CURATED_NATIVE_REPORT.json", ["reports", "prior_effective_ai_reject_ids", "readiness", "note"]),
        "v4_raw_request_response_branch_not_old_native_parser": ("output/20261025_wrd_reasoning_recovery_v4/RAW_RECOVERY_REPORT.json", ["counts_by_scope", "run_counts", "continuity_counts", "unique_reasoning_content_sha256_count", "source_files_hashed"]),
        "v4_raw_original_request_scope_review_overrides_directory_guess": ("output/20261025_wrd_reasoning_recovery_v4/RAW_SCOPE_REVIEW.json", ["counts_by_old_scope", "aggregate", "historical_synthetic_probes_not_original_enterprise_source_conversations", "historical_generation_endstate_summary"]),
        "v4_SSE_reasoning_branch_not_old_native_parser": ("output/20261025_wrd_reasoning_recovery_v4/SSE_REASONING_RECOVERY_REPORT.json", ["counts", "mechanical_exclusions", "by_source_role", "different_episode_ids"]),
        "v4_additional_native_sessions_outside_old_frozen_entrance": ("output/20261025_wrd_reasoning_recovery_v4/HISTORICAL_NATIVE_RECOVERY_REPORT.json", ["counts", "new_sessions_by_role", "current_canonical_sessions"]),
        "v6_source_resource_closure_filter_not_raw_corpus_size": ("output/20261026_wrd_lineage_v6/LINEAGE_AUDIT_REPORT.json", ["fixed91_terminal_counts", "fixed91_by_stage", "all_native_episode_counts", "protected_original226_count", "limitations"]),
        "v6_historical_source_closure": ("output/20261026_wrd_lineage_v6/REASONING_LINEAGE_REPORT.json", ["pairs", "terminal_counts", "by_branch", "missing_reasons", "resource_nodes", "verified_resource_nodes", "scope_admission_not_outcome_or_semantic_gold"]),
        "v6_positive_process_subset_not_original_record_population": ("output/20261026_wrd_sequences_v6/ADMITTED_DATA_REPORT.json", ["reasoning_resource_closed_original_pairs", "reasoning_quality_positive_original_pairs", "historical_raw_quality_overlay_counts", "source_closed_reasoning_pairs_held_by_additional_raw_quality", "all_native_resource_closed_episodes", "all_native_quality_positive_episodes", "historical_unique_proven_business_sources", "all_native_and_historical_unique_proven_business_sources", "native_lineage_decision_status_counts", "historical_lineage_decision_status_counts", "scopes", "actual_full_A_D_autonomous_native_chains"]),
    }
    branches = {}
    for name, (s, fields) in extracts.items():
        p = ROOT / s
        if not p.is_file():
            branches[name] = {"missing_named_report": s}
            continue
        x = load(p)
        branches[name] = {"pin": pin(p), "reported_not_independently_recompiled_in_this_audit": True, "selected_fields": {k: x[k] for k in fields if k in x}, "available_top_level_fields": list(x)}
    report["successive_entrance_and_filter_report_evidence"] = branches
    report["reason_taxonomy"] = [
        {"reason": "not_discovered_by_old_entrance", "evidence": "Raw request-response and SSE roots, plus historical native97, are separate recovery branches; old state/job/reference-only discovery was not a global format/root census.", "not_equivalent_to": "records do not exist"},
        {"reason": "not_included_as_primary", "evidence": "Old make/screen choice and preflight input list omit prepare/review/actor bodies from primary stream despite canonical preservation.", "not_equivalent_to": "no intermediate actions recorded"},
        {"reason": "not_parsed_by_that_format_adapter", "evidence": "Old parser accepts only native message wrappers; raw OpenAI reasoning_content and SSE delta.reasoning_content need their own exact adapters.", "not_equivalent_to": "teacher never thought"},
        {"reason": "index_only_or_support_only", "evidence": "Auxiliary rows and catalog/source tables can reference full bodies but do not themselves constitute complete supervised trajectories.", "not_equivalent_to": "full pipeline compiled"},
        {"reason": "mechanical_export_or_classification_error", "evidence": "prepare policy marker falsely triggered old benchmark detector; legacy substring screen can mean business resume screening; old response.json omitted67 original SSE reasoning fields.", "not_equivalent_to": "actual protected-source exposure"},
        {"reason": "source_lineage_not_proven", "evidence": "v6 native560 missing closure includes resource creation/dispatch linkage unknown; absence of proof is not proof of forbidden ancestor.", "not_equivalent_to": "actual original226 dependency"},
        {"reason": "actual_original226_dependency", "evidence": "v6 verified protected resource/body paths are isolated under the user-confirmed original226 boundary.", "not_equivalent_to": "all raw data unusable or data absent"},
        {"reason": "quality_or_length_filter", "evidence": "Later known rejected responses, failed writer versions, completion length, supported tool schema and current-target masks act after original preservation.", "not_equivalent_to": "raw record count"},
    ]
    report["audit_conclusions"] = [
        "93 is a public reviewed make/screen current-action subset at <=32K, not the original dataset and not full-pipeline training. Presenting it as sufficient full WRD training was a scope/communication failure.",
        "The old frozen bundle itself preserves1763 native histories/32342 assistant positions; primary SFT deliberately excluded other recorded stages. Original1107 source conversations are a different input unit.",
        "The old Actor-as-auxiliary and <=10% training-mixture suggestions were research choices, not a user requirement to discard execution records. Actor trials/no-skill and skill-enhanced execution, observations, resource reproduction, feedback and subsequent revision contexts are essential parts of the requested pipeline. Different target roles require a declared training-role adapter, not an assertion that these records have no training value.",
        "The old1763 is not a complete census of all physical historical formats/roots: later recovery found raw request-response, SSE reasoning and additional native sessions outside that entrance. The separate physical v7 census must establish any further missing roots/records.",
        "106 is the later source-and-quality-qualified historical process subset from one narrow branch, not evidence that the original full records are few. It does not prove autonomous A-D skill distillation.",
        "No held mixed context is washed into training by removing protected messages, and original226 isolation is unchanged. An unproven resource is not relabelled as an actual forbidden dependency.",
    ]
    report["unknowns_and_limits"] = [
        "This audit does not scan unrelated private files or assert all original records across disks are covered. Read physical/source and production29 companion reports before any global completeness claim.",
        "Original imported stage kinds and historical actor/maker roles require actual original requests and tool context, not filenames or these old labels. This audit flags all134 imported episodes for such review and proves the known resume substring error only.",
        "v4/v6 report selections are pinned report evidence, not a second independent rerun of their CPU compilers or resource lineage engines.",
        "Archive credential-redacted event projections can differ from physical original bytes; both index source_sha256 and archive sha256 remain distinguishable. No enterprise body or credential is reproduced here.",
        "Native service request IDs, raw SFT rows, repeated workflow versions and reasoning SSE frames have different granularities; no subtraction between them establishes missing records.",
    ]
    report["script_sha256"] = sha(Path(__file__))
    dest = OUT / "EXPORT_COVERAGE_AUDIT.json"
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": rel(dest), "sha256": sha(dest), "catalog_sessions": len(catalog), "canonical_sessions": len(canonical), "raw_event_objects_hashed": len(raw_events_pins), "raw_counts": raw_counts, "canonical_event_mapping_issues": len(event_issues), "not_in_canonical": len(missing_canonical), "legacy_known_false_screen": report["legacy_name_based_kind_requires_reclassification"]["known_resume_route_false_screen_matches"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
