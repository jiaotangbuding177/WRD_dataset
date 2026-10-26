"""Offline census of documented WRD task groups and causal supervision.

This is an audit, not a training admission rule. Original bodies stay in their
existing frozen CAS. Reports contain references and deidentified observations.
No model, database, Docker, network, or historical program execution is used.
"""
from __future__ import annotations

import collections
import ast
import gzip
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / "output/20261025_wrd_training_dataset/bundle"
OUT = ROOT / "output/20261026_wrd_quality_v8"
V7 = ROOT / "output/20261026_wrd_raw_census_v7"
V6 = ROOT / "output/20261026_wrd_lineage_v6/controlled"


def rows(path):
    op = gzip.open if str(path).endswith(".gz") else open
    with op(path, "rt", encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def jsha(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":")).encode())


def count(values):
    return dict(sorted(collections.Counter(values).items()))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


REVIEW_NOTES = {
    "ai-adoption-advisory": ("BIZ", "model_review_and_paired_interface", "原评审明确区分方案型与场景说明型委托，记录检索不可用时标注不确定性、按分型成文及导出。两个业务委托和版本读取可追溯；本文未重新核算方案ROI或外部事实，不能把原评审pass当独立Q。"),
    "ai-news-digest": ("NEWS", "boundary_and_revision", "原评审中一个case采用新闻骨架，另一论文日报case明确不适用而走普通做法；后者是边界判断示范，不能计作新闻技能程序成功复用。原评审承认docx/pdf分支未有业务试用，只有制作期测试；不把全部分支标为业务已证。"),
    "document-error-review": ("OFFICE", "conditional_resource_use", "原评审区分正文已内嵌时直接审查与附件修订时调用程序；还明确单case成本上升、路线合计下降，不能给两个case都贴降本正标。原始核对清单和程序过程有监督价值，独立查错完整性仍未重评。"),
    "email-reply-drafting": ("COMM", "honest_missing_facts", "原评审依据两个真实回复委托检查事实边界、条款未提供时不编造承诺，并记录检索失败后的替代取证。可用于成文/缺事实处理过程；本轮未独立核实文献和法律内容。"),
    "git-contribution-report": ("DATA", "valid_blocked_delivery_not_full_business_solution", "唯一业务case缺账号与仓库线索，委托允许缺项清单，实际输出是缺项说明而非采集完整提交并生成贡献年报。脚本制作期用demo仓库/mock分页测试与真实业务运行必须分列；此case支持缺输入短路，不能证明完整贡献分析能力。"),
    "memory-profile-compilation": ("LIFE", "fallback_and_privacy_boundary", "原评审记录记忆文件缺失分支、按现有材料成形画像，以及图片端点404后用本地渲染；文档与卡片的敏感维度范围不同。可学缺源与工具替代，但当前没有独立人物画像事实完整性评价。"),
    "org-chart-design": ("HR", "paired_version_and_tool_completion", "原委托、当前候选SKILL全文返回、程序执行到process最终exit0可逐工具调用核对。长exec初次running不是完成；最终回执有21签收栏。原评审对两案作结构检查，后续是否保留/发下一轮由外层接线，不能作为同一个模型自主A-D示范。"),
    "patent-annuity-compliance": ("LEGAL", "real_feedback_then_revision", "原反馈保存上版已交付但多轮核验开销增加的具体原因，后一制作看到该反馈和旧包，后续Actor读取新版本与模板并重写截断交付。原学习来源应读取learning_source_ids，不能把另一个开发source误算制作学习。法律准确性与收窄核验建议没有独立专业重评，不作为质量gold。"),
    "web-html-prototype": ("EDU", "scope_choice_real_program_receipt", "真实两案一适用一不适用：周期性太阳系示例实际读取当前SKILL/规格后build返回BUILD_OK、verify返回PASS且exit0；摩擦力按收窄边界直接编写。两个case不是两次相同程序成功。原路线关联的会话有真实用户反馈黑屏/卡片不显示与催促未开工；当前太阳系/摩擦力验证不能追认为原游戏全部修复，不能覆盖原需求全部分支。"),
    "review-response-letter": ("EDU", "cross_domain_partial_route", "原评审自己说明唯一业务case是企业意见回复函而非学术审稿，采用了逐条答复的公共步骤并变通编号。这支持公共成文过程，不能据此声称学术审稿原稿修改/逐项意见对应全过程获得独立业务验证。"),
    "contract-review-revision": ("LEGAL", "negative_no_benefit_stop", "原review明确资源可靠、两案交付可读且版本一致，但两案Token/调用均增加，next_step=no_benefit，原作者选择reject。保留合法读取/测试和取舍理由；不能把整个失败路线当每个中间动作都错误，也不能把拒绝理由升级为旧BCD有效性结论。"),
    "document-translation-route": ("OFFICE", "concrete_revision_vs_outer_stop", "原review是revise/repair_resource，明确短文本分支和强制脚本-first规则冲突、逐页读取增加轮次；当前catalog状态却rejected，不能把外层修订限额/用户停轮当模型主动reject目标。长文件/扫描件分支业务收益原评审明确未测。"),
    "excel-data-analysis-report": ("DATA", "unknown_cost_recover_evidence", "原评审指出workflow已有1个未知用量，完整Token为null；next_step=recover_evidence要求只找既有账、不重跑/估算/补零。资源运行、交付与成本证据完整性是不同轴，不把缺账标成业务失败，也不把已知下界当完整降本结果。"),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    routes = list(rows(BUNDLE / "catalog/routes.jsonl"))
    jobs = list(rows(BUNDLE / "catalog/jobs.jsonl"))
    episodes = list(rows(BUNDLE / "catalog/episodes.jsonl"))
    route_by = {r["id"]: r for r in routes}
    episode_by = {e["episode_id"]: e for e in episodes}
    path_to_eid = {e["source_path"].replace("\\", "/").casefold(): e["episode_id"] for e in episodes}
    job_by = {j["id"]: j for j in jobs}
    job_episodes = collections.defaultdict(set)
    for e in episodes:
        for jid in [e.get("job_id")] + list(e.get("job_refs") or []):
            if isinstance(jid, dict):
                jid = jid.get("job_id") or jid.get("id")
            if jid in job_by:
                job_episodes[jid].add(e["episode_id"])

    formal_files = sorted((ROOT / "benchmark").glob("*/contracts/evaluation.jsonl"))
    formal_sets = []
    for p in formal_files:
        ids = {r.get("session_id") for r in rows(p)} - {None}
        if len(ids) == 226:
            formal_sets.append((p, ids))
    assert formal_sets, "Original protected226 contract not found"
    formal = formal_sets[0][1]
    assert all(ids == formal for _, ids in formal_sets)

    wanted = {"request.json", "workspace/outputs/tasks.json", "workspace/outputs/making.json",
              "workspace/outputs/review.json", "workspace/outputs/routes.json", "workspace/outputs/screen.json",
              "workspace/inputs/previous_feedback.json", "workspace/inputs/previous.json",
              "workspace/inputs/review_input.json", "workspace/inputs/route.json",
              "workspace/inputs/task_route.json", "workspace/inputs/task_sources.json",
              "workspace/outputs/development_tasks.json", "workspace/outputs/replay.json",
              "workspace/outputs/evidence.json"}
    files = {}
    for r in rows(BUNDLE / "archive/file_index.jsonl"):
        bits = r["logical_path"].split("/", 2)
        extra = len(bits) == 3 and (bits[2] == "openclaw_transport/session_events.jsonl" or
            bits[2] == "workspace/inputs/candidate/SKILL.md" or
            bits[2].endswith("/scripts/check_paper.py") or
            re.fullmatch(r"workspace/inputs/cases/\d+/workflow/read_usage_evidence.json", bits[2]))
        if len(bits) == 3 and bits[0] == "episodes" and (bits[2] in wanted or extra):
            files[(bits[1], bits[2])] = r

    def read_bytes(eid, rel):
        f = files.get((eid, rel))
        if not f:
            return None, None
        p = BUNDLE / f["object"]
        if not p.is_file():
            p = BUNDLE / "archive" / f["object"]
        data = p.read_bytes()
        assert sha(data) == f["sha256"]
        ref = {"episode_id": eid, "logical_path": f["logical_path"],
               "frozen_sha256": f["sha256"], "source_sha256": f.get("source_sha256"),
               "source_path": f.get("source_path"), "cas_object": f["object"],
               "bytes": len(data), "json_pointer": "", "line": 1}
        return data, ref

    def read(eid, rel):
        data, ref = read_bytes(eid, rel)
        if data is None:
            return None, None
        try:
            return json.loads(data.decode("utf-8-sig")), ref
        except (UnicodeError, json.JSONDecodeError):
            return None, ref

    docs = collections.defaultdict(dict)
    refs = {}
    stage_json_parse_issues = []
    for eid, rel in files:
        if rel in wanted:
            value, ref = read(eid, rel)
            if isinstance(value, (dict, list)):
                docs[eid][rel] = value
                refs[(eid, rel)] = ref
            elif rel.startswith("workspace/outputs/") and rel.endswith(".json"):
                data, same_ref = read_bytes(eid, rel)
                try:
                    parsed = json.loads(data.decode("utf-8-sig"))
                    issue = {"type": "unexpected_root_type", "root_type": type(parsed).__name__}
                except json.JSONDecodeError as ex:
                    issue = {"type": "JSONDecodeError", "message": ex.msg, "line": ex.lineno, "column": ex.colno, "char": ex.pos}
                except UnicodeError:
                    issue = {"type": "UnicodeError"}
                stage_json_parse_issues.append({"source": same_ref, "issue": issue,
                    "original_bytes_preserved": True, "whole_episode_not_rejected": True})

    # Legacy catalog route_id sometimes contains the devprep/Actor suffix.
    # Resolve only the exact original request task_id under the archived
    # generation/evaluation producer interface; never a substring role guess.
    normalized_route_by_episode = {}
    normalized_route_evidence = {}
    for e in episodes:
        rid = e.get("route_id")
        req = docs.get(e["episode_id"], {}).get("request.json") or {}
        tid = req.get("task_id", "")
        if rid not in route_by and req.get("stage") in ("generation", "evaluation"):
            matches = [r for r in route_by if re.fullmatch(re.escape(r) + r"(?:_devprep|_c\d+_(?:no_skill|workflow|blindjudge)|__make\d+)", tid)]
            if len(matches) == 1:
                rid = matches[0]
                normalized_route_evidence[e["episode_id"]] = {"raw_catalog_route_id": e.get("route_id"),
                    "original_request_stage": req.get("stage"), "original_request_task_id": tid,
                    "request_ref": refs.get((e["episode_id"], "request.json"))}
        normalized_route_by_episode[e["episode_id"]] = rid

    lineage = {x["episode_id"]: x for x in rows(V6 / "lineage_episode_decisions.jsonl.gz")}
    resource_nodes = list(rows(V6 / "lineage_resources.jsonl.gz"))
    version_trees = [x for x in rows(V7 / "indexes/skill_version_trees.all.jsonl.gz")
                     if x["output_skill_root_logical_path"].startswith("episodes/" + x["episode_id"] + "/workspace/outputs/")]
    nodes_by_ep = collections.defaultdict(list)
    for n in resource_nodes:
        nodes_by_ep[n["episode_id"]].append(n)

    native_profiles = {}
    output_write_links = {}
    source_lineage_refs = {}
    for ep in rows(BUNDLE / "canonical/native_episodes.jsonl.gz"):
        eid = ep["episode_id"]
        calls = []
        response_counts = collections.Counter()
        text_chars = 0
        msg_lines = ep.get("source_event_lines") or []
        observed = []
        for i, m in enumerate(ep.get("messages") or []):
            if m.get("role") != "assistant":
                continue
            for block in m.get("content") or []:
                if not isinstance(block, dict):
                    continue
                typ = block.get("type")
                response_counts[str(typ)] += 1
                if typ == "text":
                    text_chars += len(block.get("text") or "")
                if typ != "toolCall":
                    continue
                args = block.get("arguments") or {}
                calls.append((i, block.get("name"), block.get("id")))
                if not isinstance(args, dict):
                    continue
                path = str(args.get("path") or args.get("file_path") or "")
                content = args.get("content") or args.get("text")
                if path.startswith("/workspace/outputs/") and isinstance(content, str):
                    rel = "workspace/outputs/" + path.split("/workspace/outputs/", 1)[1]
                    f = files.get((eid, rel))
                    if f and sha(content.encode()) == f["sha256"]:
                        output_write_links[(eid, rel)] = {"assistant_message_index": i,
                            "source_event_line": msg_lines[i] if i < len(msg_lines) else None,
                            "tool_call_id": block.get("id"), "tool_name": block.get("name"),
                            "exact_content_sha256": f["sha256"]}
        native_profiles[eid] = {"messages": len(ep.get("messages") or []),
            "assistant_content_types": dict(response_counts), "visible_assistant_text_chars": text_chars,
            "tool_call_names": count(n for _, n, _ in calls),
            "actual_tool_calls": len(calls), "job_kind": ep.get("kind"),
            "canonical_episode_sha256": jsha(ep),
            "first_user_message_chars": next((len(json.dumps(m, ensure_ascii=False)) for m in ep.get("messages", []) if m.get("role") == "user"), 0)}

    outputs = []
    for eid, dd in docs.items():
        for rel, value in dd.items():
            if not rel.startswith("workspace/outputs/"):
                continue
            e = episode_by.get(eid, {})
            outputs.append({"episode_id": eid, "route_id": normalized_route_by_episode.get(eid),
                "kind": e.get("kind"), "name": rel.split("/")[-1], "value": value,
                "ref": refs[(eid, rel)], "write_link": output_write_links.get((eid, rel))})
    tasks = [o for o in outputs if o["name"] == "tasks.json"]
    legacy_tasks = [o for o in outputs if o["name"] == "development_tasks.json"]
    making = [o for o in outputs if o["name"] == "making.json"]
    reviews = [o for o in outputs if o["name"] == "review.json"]
    screens = [o for o in outputs if o["name"] in ("routes.json", "screen.json")]
    a_links = collections.defaultdict(set)
    for o in screens:
        value = o["value"]
        cards = value.get("routes", []) if isinstance(value, dict) else []
        for card in cards:
            for rid in [card.get("id"), card.get("merge_into")]:
                if rid in route_by:
                    a_links[rid].add(o["episode_id"])
        for card in value.get("decisions", []) if isinstance(value, dict) else []:
            rid = card.get("route_id") or card.get("merge_into")
            if rid in route_by:
                a_links[rid].add(o["episode_id"])

    route_rows = []
    for r in routes:
        rid = r["id"]
        rjobs = [j for j in jobs if j.get("route_id") == rid]
        direct = {e["episode_id"] for e in episodes if normalized_route_by_episode.get(e["episode_id"]) == rid}
        for j in rjobs:
            direct |= job_episodes[j["id"]]
        grouped = collections.defaultdict(dict)
        for j in rjobs:
            if j["kind"] != "actor":
                continue
            result = j.get("result") or {}
            p = j.get("episode") or result.get("episode_dir")
            original = path_to_eid.get(str(p).replace("\\", "/").casefold())
            grouped[j.get("case_id")][j.get("arm")] = {"job_id": j["id"],
                "episode_id": original, "actual_source_dir": p,
                "reused_from_job": result.get("reused_from_job"), "status": j["status"],
                "source_id": ((j.get("payload") or {}).get("case") or {}).get("source_id"),
                "result_status": result.get("status"), "delivery_status": result.get("delivery_status")}
        pairs = [{"case_id": c, "arms": arms} for c, arms in grouped.items()
                 if {"no_skill", "workflow"} <= set(arms)]
        directory_pairs = [p for p in pairs if all(a.get("episode_id") for a in p["arms"].values())]
        physical_pairs = [p for p in directory_pairs if all(a.get("episode_id") in native_profiles for a in p["arms"].values())]
        original_pair_ids = {(p["arms"]["no_skill"]["episode_id"], p["arms"]["workflow"]["episode_id"])
                             for p in physical_pairs}
        tdocs = [o for o in tasks if o["route_id"] == rid]
        ltdocs = [o for o in legacy_tasks if o["route_id"] == rid]
        route_skill_versions = [v for v in version_trees if v["catalog_route_id"] == rid]
        mdocs = [o for o in making if o["route_id"] == rid]
        rdocs = [o for o in reviews if o["route_id"] == rid]
        selected_sources = {c.get("source_id") for o in tdocs + ltdocs for c in o["value"].get("cases", []) if isinstance(c, dict)} - {None}
        actual_cases = {a.get("source_id") for p in pairs for a in p["arms"].values()} - {None}
        all_related = direct | a_links[rid]
        known_protected = {e for e in all_related if lineage.get(e, {}).get("status") == "HOLD_PROTECTED"}
        unresolved = {e for e in all_related if lineage.get(e, {}).get("status") == "HOLD_MISSING_EVIDENCE"}
        known_clear = {e for e in all_related if lineage.get(e, {}).get("status") == "ADMIT"}
        unassessed = all_related - set(lineage)
        current = r.get("value_review") or {}
        current_matches = [o for o in rdocs if jsha(o["value"]) == jsha(current)] if current else []
        feedback_nodes = [n for e in direct for n in nodes_by_ep[e]
                          if "previous_feedback" in n.get("native_path", "")]
        feedback_producers = [n for n in feedback_nodes if n.get("proven_producer_prefixes")]
        retained_info = None
        per_skill = V7 / "skills29" / (rid + ".json")
        if per_skill.is_file():
            sx = json.loads(per_skill.read_text(encoding="utf-8"))
            retained_info = {k: sx[k] for k in ("final_tree_content_sha256", "final_file_count",
                "native_output_versions_byte_exact_equal_final_tree", "unique_output_tree_content_versions",
                "gold_replay_files")}
        outer_abc = bool(a_links[rid] and route_skill_versions and any(o["value"].get("cases") for o in tdocs + ltdocs)
                         and physical_pairs and rdocs)
        route_rows.append({"route_id": rid, "category": r.get("category"),
            "library_status": r.get("library_status"), "all_route_source_ids_not_necessarily_selected_learning": r.get("source_ids", []),
            "declared_learning_source_ids": r.get("learning_source_ids", r.get("source_ids", [])),
            "declared_learning_original226": sorted(set(r.get("learning_source_ids", r.get("source_ids", []))) & formal),
            "selected_business_source_ids": sorted(selected_sources),
            "selected_business_original226": sorted(selected_sources & formal),
            "actor_case_source_ids": sorted(actual_cases), "actor_case_original226": sorted(actual_cases & formal),
            "current_active_business_source_ids": sorted({c.get("source_id") for c in r.get("tasks", [])
                if (str(c.get("id", "")) in set(r.get("active_case_ids") or []))} - {None}) if "active_case_ids" in r else
                sorted({c.get("source_id") for c in r.get("tasks", [])} - {None}),
            "direct_job_count": len(rjobs), "direct_attempt_refs": len(direct),
            "screen_output_linked_attempt_ids": sorted(a_links[rid]),
            "tasks_output_attempts": len(tdocs), "tasks_positive_attempts": sum(bool(o["value"].get("cases")) for o in tdocs),
            "tasks_zero_case_attempts": sum(not o["value"].get("cases") for o in tdocs),
            "legacy_development_tasks_attempts": len(ltdocs),
            "legacy_development_tasks_positive_attempts": sum(bool(o["value"].get("cases")) for o in ltdocs),
            "making_output_attempts": len(mdocs), "making_skip_attempts": sum(bool(o["value"].get("skip_reason")) for o in mdocs),
            "original_native_output_skill_tree_versions": len(route_skill_versions),
            "review_output_attempts": len(rdocs), "review_decisions": count(str(o["value"].get("decision")) for o in rdocs),
            "actor_logical_paired_cases": len(pairs), "actor_pairs_with_original_directory_refs": len(directory_pairs),
            "actor_pairs_with_original_contexts": len(physical_pairs),
            "actor_distinct_physical_pairs_not_aliases": len(original_pair_ids),
            "actor_pairs": physical_pairs,
            "documented_outer_A_B_C_interface_group": outer_abc,
            "documented_D_final_copy": bool(retained_info), "final_version_evidence": retained_info,
            "current_decision": current.get("decision"),
            "current_decision_exact_original_review_matches": [o["episode_id"] for o in current_matches],
            "round_closeout_present": bool(r.get("round_closeout")),
            "round_closeout_author": "outer_pipeline_or_user_stop_record" if r.get("round_closeout") else None,
            "selection_repair_present": bool(r.get("selection_repair")),
            "selection_repair_history_length": len(r.get("selection_repair_history") or []),
            "feedback_observed_resource_nodes": len(feedback_nodes),
            "feedback_exact_producer_prefix_proven_nodes": len(feedback_producers),
            "source_scope_v6_related_episode_status": {"explicit_or_observed_or_resource_protected": len(known_protected),
                "specific_missing_evidence": len(unresolved), "closed_non226": len(known_clear), "not_in_old_v6_scope": len(unassessed)},
            "source_scope_all_selected_stage_attempts_closed_non226": bool(all_related) and all_related <= known_clear,
            "legacy_exact_request_route_bindings": {e: normalized_route_evidence[e] for e in sorted(direct) if e in normalized_route_evidence},
            "not_training_admission": True})

    def components(rr):
        remaining = {r["route_id"]: set(r["declared_learning_source_ids"]) | set(r["actor_case_source_ids"]) for r in rr}
        groups = []
        while remaining:
            rid, ids = remaining.popitem()
            group = {rid}
            changed = True
            while changed:
                changed = False
                for k, v in list(remaining.items()):
                    if ids & v:
                        group.add(k); ids |= remaining.pop(k); changed = True
            groups.append({"route_ids": sorted(group), "source_count": len(ids)})
        return sorted(groups, key=lambda x: (-len(x["route_ids"]), x["route_ids"]))

    task_reasons = collections.Counter()
    for o in tasks:
        if o["value"].get("cases"):
            continue
        reason = str(o["value"].get("reason") or "")
        # Overlapping text signals, not semantic labels or error judgments.
        for label, pattern in {"missing_input_text_signal": "缺|未提供|不存在|资料不全|附件",
                               "main_work_mismatch_text_signal": "不匹配|误配|主要工作|非本路线|不适用|不相同",
                               "previous_decision_reuse_text_signal": "上次|已有|已排除|复用|前轮"}.items():
            if re.search(pattern, reason):
                task_reasons[label] += 1

    rret = [r for r in route_rows if r["library_status"] == "retained"]
    for r in route_rows:
        r["within_route_learning_and_all_actor_source_overlap"] = sorted(set(r["declared_learning_source_ids"]) & set(r["actor_case_source_ids"]))
        r["within_route_learning_and_current_active_business_overlap"] = sorted(set(r["declared_learning_source_ids"]) & set(r["current_active_business_source_ids"]))
    feedback_exact_content_links = []
    for eid, dd in docs.items():
        feedback = dd.get("workspace/inputs/previous_feedback.json")
        if not isinstance(feedback, dict) or not isinstance(feedback.get("prior_review"), dict):
            continue
        prior = feedback["prior_review"]
        # Outer feedback projections legitimately omit repair_notes. Compare
        # every retained original field; this is not a same-session join.
        linked = [o for o in reviews if prior and all(o["value"].get(k) == v for k, v in prior.items())]
        observed_nodes = [n for n in nodes_by_ep[eid] if "previous_feedback" in n.get("native_path", "")]
        if linked:
            feedback_exact_content_links.append({"consumer_episode_id": eid,
                "route_id": normalized_route_by_episode.get(eid),
                "feedback_ref": refs[(eid, "workspace/inputs/previous_feedback.json")],
                "observed_read_message_indices": sorted({n.get("consumer_assistant_message_index") for n in observed_nodes if isinstance(n.get("consumer_assistant_message_index"), int)}),
                "prior_review_matches": [{"episode_id": o["episode_id"], "source": o["ref"],
                                          "exact_native_write": o["write_link"]} for o in linked],
                "comparison": "all_original_prior_review_fields_equal; projected_feedback_not_new_model_review",
                "time_visibility": "observed actual native read when indices nonempty; producer-event timestamp ordering not inferred from filenames",
                "training_admitted": False})
    all_pair_ids = {(p["arms"]["no_skill"]["episode_id"], p["arms"]["workflow"]["episode_id"])
                    for r in route_rows for p in r["actor_pairs"]}
    brief = {
        "schema_version": "wrd-chain-quality-v8.1", "scope": "Frozen production121 routes/1751 jobs/1822 attempt references, not all newly discovered175 roots",
        "unit_contract": {"route": "a task-type route, not independent business source or model trajectory",
            "pair": "matching logical case with two original physical Agent context references; exact candidate consumption requires separate review",
            "artifact_attempt": "one indexed attempt output; identical byte copies are not independent demonstrations",
            "full_autonomous_chain": "one observed policy chooses and executes A/B/C/revision/D transitions, including delegation; outer scripts wiring stages do not count"},
        "original_catalog": {"routes": len(routes), "retained": len(rret), "jobs": len(jobs),
            "attempt_refs": len(episodes), "canonical_contexts": len(native_profiles),
            "categories_all": count(str(r.get("category")) for r in routes),
            "categories_retained": count(str(r.get("category")) for r in routes if r.get("library_status") == "retained"),
            "route_library_status": count(str(r.get("library_status")) for r in routes),
            "current_value_review_decision": count(str((r.get("value_review") or {}).get("decision")) for r in routes)},
        "output_branch_coverage": {
            "original_stage_output_file_refs": count(rel.rsplit("/", 1)[-1] for eid, rel in files if rel in wanted and rel.startswith("workspace/outputs/")),
            "stage_json_parse_issues": stage_json_parse_issues,
            "tasks_attempts": len(tasks), "tasks_unique_byte_versions": len({o["ref"]["frozen_sha256"] for o in tasks}),
            "tasks_positive_attempts": sum(bool(o["value"].get("cases")) for o in tasks),
            "tasks_zero_case_attempts": sum(not o["value"].get("cases") for o in tasks),
            "legacy_development_tasks_attempts_separate": len(legacy_tasks),
            "legacy_development_tasks_positive_attempts": sum(bool(o["value"].get("cases")) for o in legacy_tasks),
            "legacy_development_tasks_cases_attempt_records": sum(len(o["value"].get("cases") or []) for o in legacy_tasks),
            "selected_cases_total_attempt_records_not_independent": sum(len(o["value"].get("cases") or []) for o in tasks),
            "zero_case_overlapping_reason_text_signals_not_error_labels": dict(task_reasons),
            "making_attempts": len(making), "making_unique_byte_versions": len({o["ref"]["frozen_sha256"] for o in making}),
            "making_skip_reason_attempts": sum(bool(o["value"].get("skip_reason")) for o in making),
            "making_program_run_report_entries_not_verified_execution": sum(len(o["value"].get("program_runs") or []) for o in making),
            "review_attempts": len(reviews), "review_unique_byte_versions": len({o["ref"]["frozen_sha256"] for o in reviews}),
            "review_attempt_decisions": count(str(o["value"].get("decision")) for o in reviews),
            "review_current_decision_matches_original_artifact_routes": sum(bool(r["current_decision_exact_original_review_matches"]) for r in route_rows),
            "logical_actor_pairs_with_original_contexts_sum_by_route": sum(r["actor_pairs_with_original_contexts"] for r in route_rows),
            "distinct_original_actor_pairs_not_aliases": len(all_pair_ids),
            "no_skill_job_reuse_aliases": sum(bool((j.get("result") or {}).get("reused_from_job")) for j in jobs if j["kind"] == "actor"),
            "current_round_closeout_records": sum(bool(r.get("round_closeout")) for r in routes),
            "model_current_decision_to_catalog_state": count(str((r.get("value_review") or {}).get("decision")) + "->" + str(r.get("library_status")) for r in routes),
            "closeout_records_are_outer_or_user_stop_not_model_D_targets": True},
        "documented_chain_coverage": {
            "interface_group_test": "An original screen output card/decision refers to the route; an original native output skill tree exists; positive tasks/development_tasks exist; a matching no_skill/workflow case has both recoverable native contexts; an original review exists. This is a documentary association proxy, not verification of every timestamp/version/semantic transition.",
            "all_routes_A_B_C_outer_interface_groups": sum(r["documented_outer_A_B_C_interface_group"] for r in route_rows),
            "retained29_A_B_C_outer_interface_groups": sum(r["documented_outer_A_B_C_interface_group"] for r in rret),
            "retained29_final_trees_equal_at_least_one_original_native_output": sum(bool(r["final_version_evidence"]["native_output_versions_byte_exact_equal_final_tree"]) for r in rret),
            "retained29_final_files": sum(r["final_version_evidence"]["final_file_count"] for r in rret),
            "retained29_distinct_output_content_tree_versions_sum_not_independent_tasks": sum(r["final_version_evidence"]["unique_output_tree_content_versions"] for r in rret),
            "routes_with_observed_feedback_reads": sum(bool(r["feedback_observed_resource_nodes"]) for r in route_rows),
            "legacy_v6_feedback_node_producer_prefix_field_nonempty_routes": sum(bool(r["feedback_exact_producer_prefix_proven_nodes"]) for r in route_rows),
            "legacy_v6_feedback_field_zero_interpretation": "The old generic resource graph did not prove this field for outer-generated feedback packets. This is not a count of actual causal repair chains; explicit projected-review/read links and bounded original native examples below provide separate evidence.",
            "feedback_inputs_with_exact_prior_review_field_projection": len(feedback_exact_content_links),
            "feedback_inputs_with_exact_prior_review_projection_and_actual_read": sum(bool(x["observed_read_message_indices"]) for x in feedback_exact_content_links),
            "feedback_projection_links_are_not_model_controller_transitions": True,
            "full_autonomous_A_to_D_native_demonstrations_verified": 0,
            "why_not_inferred_from_stage_files": "Production contracts dispatch separate screen/make/prepare/Actor/review native sessions. Review proposes retain/revise/reject/defer, outer scheduling and user constraints choose next jobs/copy/final stop. No verified single policy-level A-to-D controller demonstration is established by this taskgroup graph.",
            "all_roots_global_autonomous_count": "unknown: newly recovered bodies require task-boundary and author analysis"},
        "source_independence": {
            "all_route_declared_learning_sources": len({s for r in route_rows for s in r["declared_learning_source_ids"]}),
            "retained29_declared_learning_sources": len({s for r in rret for s in r["declared_learning_source_ids"]}),
            "all_actor_case_sources": len({s for r in route_rows for s in r["actor_case_source_ids"]}),
            "retained29_actor_case_sources": len({s for r in rret for s in r["actor_case_source_ids"]}),
            "retained29_declared_learning_and_actor_overlap": len({s for r in rret for s in r["declared_learning_source_ids"]} & {s for r in rret for s in r["actor_case_source_ids"]}),
            "retained_routes_with_within_route_all_historical_actor_overlap": sum(bool(r["within_route_learning_and_all_actor_source_overlap"]) for r in rret),
            "retained_routes_with_within_route_current_active_case_overlap": sum(bool(r["within_route_learning_and_current_active_business_overlap"]) for r in rret),
            "retained29_current_active_business_sources": len({s for r in rret for s in r["current_active_business_source_ids"]}),
            "all_source_overlap_components": components(route_rows),
            "retained29_source_overlap_components": components(rret),
            "component_interpretation": "Conservative declared-source/selected-case overlap groups. Not proof of independent draws or complete reusable-resource closure; catalog availability alone is excluded."},
        "original226_boundary": {
            "contracts": [{"path": str(p), "sha256": sha(p.read_bytes()), "ids": len(ids)} for p, ids in formal_sets],
            "routes_with_declared_learning226": sum(bool(r["declared_learning_original226"]) for r in route_rows),
            "retained29_with_declared_learning226": sum(bool(r["declared_learning_original226"]) for r in rret),
            "routes_with_selected_business226": sum(bool(r["selected_business_original226"]) for r in route_rows),
            "retained29_with_selected_business226": sum(bool(r["selected_business_original226"]) for r in rret),
            "outer_groups_with_no_declared_learning_or_selected_case226": sum(r["documented_outer_A_B_C_interface_group"] and not (r["declared_learning_original226"] or r["selected_business_original226"] or r["actor_case_original226"]) for r in route_rows),
            "all_selected_stage_attempts_source_closed_non226_groups": sum(r["documented_outer_A_B_C_interface_group"] and r["source_scope_all_selected_stage_attempts_closed_non226"] for r in route_rows),
            "interpretation": "Declared selected protected sources are explicit dependencies, not merely prohibition mentions. Actual body/resource ancestor proof and missing evidence are separated per route using the frozen v6 graph. All-attempt closure is deliberately stronger than existence of an alternate clean path; zero here does not establish that no recoverable clean subchain exists. No training admission is changed.",
            "policy_mentions_only_not_read_evidence": True,
            "independent_complete_autonomous_demonstrations_after_exclusion_verified": 0},
        "quality_not_equal_outcome": {
            "old_BCD_effect_results": "invalidated_by_user; original trace/cost facts retained",
            "retain_is": "observed historical model/outer decision, not current independent quality gold",
            "review_delivery_passed_is": "reviewer assertion until its artifacts/requirements are independently inspected",
            "zero_case_is": "potentially correct boundary/missing-input supervision; not a successful skill construction and not automatically bad",
            "failure_then_edit_is": "temporal relation, not repair success without exact-version actual test receipt"},
        "training_sufficiency_assessment": {
            "verified_value": "Original stage decisions, tool actions/observations, honest zero-case choices, negative no-benefit/recover-evidence judgments, and real feedback-driven local repairs are present. The original corpus is materially richer than93/106 selected responses.",
            "what_is_not_established": "These records do not yet demonstrate that a14B model can autonomously operate the whole WRD pipeline or achieve target per-qualified-skill cost. Native stage dispatch/final copying are outer actions; independent source-safe full-chain selection, independent business-Q calibration, held-out runtime evaluation, and a learning curve remain incomplete.",
            "data_volume_not_sufficient_proof": "More windows/epochs and identical baseline aliases do not add independent task families or missing controller decisions. Conversely, source-proof gaps/failed tools/zero cases do not justify deleting original process records.",
            "no_effect_guarantee": True, "model_training_or_business_validation_run": False},
        "source_pins": {"script_sha256": sha(Path(__file__).read_bytes()),
            "v7_skill_graph_sha256": sha((V7 / "SKILL29_LINEAGE_MAP.json").read_bytes()),
            "catalog_routes_sha256": sha((BUNDLE / "catalog/routes.jsonl").read_bytes()),
            "catalog_jobs_sha256": sha((BUNDLE / "catalog/jobs.jsonl").read_bytes()),
            "catalog_episodes_sha256": sha((BUNDLE / "catalog/episodes.jsonl").read_bytes()),
            "lineage_episode_decisions_sha256": sha((V6 / "lineage_episode_decisions.jsonl.gz").read_bytes())},
        "route_details": "controlled/route_chains.quality.jsonl.gz",
        "semantic_sample": "CASE_REVIEWS.jsonl (stratified qualitative reviews; not population semantic accuracy)",
        "training_started": False, "new_model_calls": 0, "admission_changed": False,
        "database_or_production_mutated": False}
    (OUT / "controlled").mkdir(exist_ok=True)
    with gzip.GzipFile(filename=str(OUT / "controlled/route_chains.quality.jsonl.gz"), mode="wb", mtime=0) as f:
        for r in route_rows:
            f.write((json.dumps(r, ensure_ascii=False) + "\n").encode())
    # A reference-only audit index: no business text is copied into this report.
    audit_refs = [{"episode_id": o["episode_id"], "route_id": o["route_id"], "kind": o["kind"],
                   "name": o["name"], "source": o["ref"], "exact_native_write": o["write_link"]} for o in outputs]
    with gzip.GzipFile(filename=str(OUT / "controlled/stage_output_refs.quality.jsonl.gz"), mode="wb", mtime=0) as f:
        for r in audit_refs:
            f.write((json.dumps(r, ensure_ascii=False) + "\n").encode())
    with gzip.GzipFile(filename=str(OUT / "controlled/feedback_projection_links.quality.jsonl.gz"), mode="wb", mtime=0) as f:
        for r in feedback_exact_content_links:
            f.write((json.dumps(r, ensure_ascii=False) + "\n").encode())

    case_reviews = []
    row_by_route = {r["route_id"]: r for r in route_rows}
    sample_original_event_cache = {}

    def event_messages(eid):
        if eid not in sample_original_event_cache:
            data, ref = read_bytes(eid, "openclaw_transport/session_events.jsonl")
            events = [json.loads(l) for l in data.decode("utf-8-sig").splitlines() if l.strip()] if data else []
            sample_original_event_cache[eid] = (events, ref)
        return sample_original_event_cache[eid]

    for rid, (category, review_type, note) in REVIEW_NOTES.items():
        current = route_by[rid].get("value_review") or {}
        matched = [o for o in reviews if o["route_id"] == rid and o["value"] == current]
        assert matched, (rid, "missing exact original review")
        o = matched[0]
        eid = o["episode_id"]
        inp = docs.get(eid, {}).get("workspace/inputs/review_input.json") or {}
        observed_pairs = []
        candidate, candidate_ref = read_bytes(eid, "workspace/inputs/candidate/SKILL.md")
        for n, c in enumerate(inp.get("cases") or [], 1):
            info = {"case_index": n, "source_id": c.get("case", {}).get("source_id"),
                "original_requirements_ref": {**refs[(eid, "workspace/inputs/review_input.json")],
                    "json_pointer": f"/cases/{n-1}/case/prompt"},
                "case_id": c.get("case", {}).get("id"), "arms": {}, "verified_native_observations": []}
            for arm, a in (c.get("arms") or {}).items():
                eps = (a.get("all_attempts") or {}).get("episodes") or []
                a_eids = [path_to_eid.get(str(p).replace("\\", "/").casefold()) for p in eps]
                info["arms"][arm] = {"physical_episode_ids": a_eids,
                    "all_attempts": (a.get("all_attempts") or {}).get("attempts"),
                    "known_tokens": (a.get("all_attempts") or {}).get("known_tokens"),
                    "total_tokens": (a.get("all_attempts") or {}).get("total_tokens"),
                    "model_calls": (a.get("all_attempts") or {}).get("model_calls"),
                    "unknown_calls": (a.get("all_attempts") or {}).get("unknown_calls"),
                    "outer_delivery_status_not_semantic_gold": a.get("delivery_status")}
                if arm != "workflow" or not a_eids or not a_eids[-1]:
                    continue
                a_eid = a_eids[-1]
                ob, ob_ref = read(eid, f"workspace/inputs/cases/{n}/workflow/read_usage_evidence.json")
                events, events_ref = event_messages(a_eid)
                for x in (ob or {}).get("observations", []):
                    ci, ri = x.get("call_line"), x.get("result_line")
                    if not isinstance(ci, int) or not isinstance(ri, int) or not (0 < ci <= len(events) and 0 < ri <= len(events)):
                        continue
                    call = events[ci-1].get("message") or {}
                    result = events[ri-1].get("message") or {}
                    call_id = x.get("tool_call_id")
                    blocks = [b for b in call.get("content") or [] if isinstance(b, dict) and b.get("type") == "toolCall" and b.get("id") == call_id]
                    if not blocks or result.get("toolCallId") != call_id:
                        continue
                    text = "\n".join(b.get("text", "") for b in result.get("content") or [] if isinstance(b, dict) and b.get("type") == "text")
                    entry = {"resource_path": x.get("resource_path"), "operation": x.get("operation"),
                        "tool_call_id": call_id, "actual_call_and_return_id_match": True,
                        "actual_tool_name": blocks[0].get("name"), "actual_return_is_error": result.get("isError"),
                        "actual_return_exit_code": (result.get("details") or {}).get("exitCode"),
                        "actual_return_status": (result.get("details") or {}).get("status"),
                        "actual_visible_text_sha256": sha(text.encode()), "actual_visible_text_chars": len(text),
                        "derived_observation_sha_equals_actual_return": x.get("visible_text_sha256") == sha(text.encode()) if x.get("visible_text_sha256") else None,
                        "source": {**(events_ref or {}), "call_line": ci, "result_line": ri,
                            "completion_line": x.get("completion_line")},
                        "candidate_SKILL_byte_sha_equal_actual_return": sha(candidate) == sha(text.encode()) if candidate and str(x.get("resource_path", "")).endswith("/SKILL.md") else None}
                    if candidate and str(x.get("resource_path", "")).endswith("/SKILL.md"):
                        candidate_text = candidate.decode("utf-8-sig")
                        span = text.find(candidate_text)
                        entry["candidate_SKILL_full_text_contiguous_span_in_actual_return"] = [span, span + len(candidate_text)] if span >= 0 else None
                        terminal_only = candidate_text.rstrip("\r\n")
                        terminal_span = text.find(terminal_only)
                        entry["candidate_SKILL_full_text_span_after_terminal_linebreak_only_normalization"] = [terminal_span, terminal_span + len(terminal_only)] if terminal_span >= 0 else None
                        entry["terminal_linebreak_comparison_does_not_modify_original_training_data"] = True
                        entry["combined_exec_return_is_not_expected_to_equal_single_file"] = blocks[0].get("name") == "exec"
                    if x.get("completion_line") and x["completion_line"] != ri and x["completion_line"] <= len(events):
                        completion = events[x["completion_line"]-1].get("message") or {}
                        entry["actual_later_completion_exit_code"] = (completion.get("details") or {}).get("exitCode")
                        complete_text = "\n".join(b.get("text", "") for b in completion.get("content") or [] if isinstance(b, dict) and b.get("type") == "text")
                        entry["actual_later_completion_text_sha256"] = sha(complete_text.encode())
                        entry["derived_observation_sha_equals_later_completion"] = x.get("visible_text_sha256") == sha(complete_text.encode())
                        entry["running_is_not_completed"] = True
                    info["verified_native_observations"].append(entry)
            observed_pairs.append(info)
        rr = row_by_route[rid]
        case_reviews.append({"case_id": "chain_" + rid, "route_id": rid, "category": category,
            "sampling_reason": review_type, "review_level": "original_review_and_requirement_read; actual_native_read_action_return_links_checked; not_independent_full_business_Q",
            "deidentified_observation_zh": note,
            "original_model_decision": o["value"].get("decision"),
            "original_model_next_step": (o["value"].get("next_step") or {}).get("action"),
            "catalog_library_status": route_by[rid].get("library_status"),
            "decision_author": "observed_model_review", "final_stage_control_author": "outer_pipeline_and_user_constraints",
            "source_review": o["ref"], "source_review_reason_pointer": "/reason",
            "source_review_exact_native_write": o["write_link"],
            "source_request": refs.get((eid, "request.json")),
            "source_review_input": refs.get((eid, "workspace/inputs/review_input.json")),
            "candidate_SKILL": candidate_ref, "paired_cases": observed_pairs,
            "feedback_projection_examples": [x for x in feedback_exact_content_links if x["route_id"] == rid][:3],
            "original226_status": {k: rr[k] for k in ["declared_learning_original226", "selected_business_original226", "actor_case_original226", "source_scope_v6_related_episode_status"]},
            "not_human_gold": True, "not_new_training_admission": True})

    for rid in ["adlaw-compliance-copy", "homework-mastery-analysis"]:
        candidates = [o for o in tasks if o["route_id"] == rid and not o["value"].get("cases")]
        o = candidates[-1]
        case_reviews.append({"case_id": "zero_case_" + rid, "route_id": rid,
            "category": route_by[rid].get("category"), "sampling_reason": "zero_case_boundary_missing_real_input",
            "review_level": "original_preparer_request_and_full_output_reason_read; reported_exhaustive_search_not_independently_repeated",
            "deidentified_observation_zh": "原输出明确cases=[]，区分学习来源有意隔离、召回命中主工作错配与真正附件缺失，保留既有排除和缺件记录，不改任务来凑试用。是可学的选题/停止与诚实缺输入判断，不是成功建库示范；其全库搜索完整性尚未独立重查。",
            "original_model_decision": "zero_cases", "decision_author": "observed_model_prepare",
            "source": o["ref"], "reason_json_pointer": "/reason", "blocked_inputs_json_pointer": "/blocked_inputs",
            "exact_native_write": o["write_link"],
            "source_request": refs.get((o["episode_id"], "request.json")),
            "prohibition_text_is_not_protected_body_observation": True,
            "not_human_gold": True, "not_new_training_admission": True})

    # A bounded native feedback->repair->regression example. Parse data and AST
    # constants only; never import or run the historical candidate program.
    peid = "ep_01d59386f68d59e981d5"
    feedback = docs[peid]["workspace/inputs/previous_feedback.json"]
    events, eref = event_messages(peid)
    result = events[9]["message"]  # original session line10
    observed_text = "\n".join(b.get("text", "") for b in result["content"] if b.get("type") == "text")
    observed_json, consumed = json.JSONDecoder().raw_decode(observed_text.lstrip())
    assert observed_json == feedback
    projection = [x for x in feedback_exact_content_links if x["consumer_episode_id"] == peid]
    assert projection and projection[0]["observed_read_message_indices"]
    prior_eid = "ep_5c9c233269172ae34071"
    assert any(z["episode_id"] == prior_eid for z in projection[0]["prior_review_matches"])
    prior_events, prior_event_ref = event_messages(prior_eid)
    prior_initial = [b for b in prior_events[77]["message"]["content"] if b.get("type") == "toolCall"][0]
    assert prior_initial["name"] == "write" and prior_initial["arguments"]["path"] == "/workspace/outputs/review.json"
    reconstructed_review = json.loads(prior_initial["arguments"]["content"])
    prior_final = [b for b in prior_events[89]["message"]["content"] if b.get("type") == "toolCall"][0]
    prior_command = prior_final["arguments"]["command"]
    prior_code = prior_command.split("<<'EOF'\n", 1)[1].split("\nEOF", 1)[0]
    assigned_fields = []
    for node in ast.parse(prior_code).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Subscript):
            target = node.targets[0]
            assert isinstance(target.value, ast.Name) and target.value.id == "d"
            key, value = ast.literal_eval(target.slice), ast.literal_eval(node.value)
            reconstructed_review[key] = value
            assigned_fields.append(key)
    assert assigned_fields == ["next_step"]
    assert reconstructed_review == docs[prior_eid]["workspace/outputs/review.json"]
    prior_return = prior_events[90]["message"]
    assert prior_return["toolCallId"] == prior_final["id"] and not prior_return.get("isError") and prior_return["details"]["exitCode"] == 0
    assert prior_return["timestamp"] < events[9]["message"]["timestamp"]
    prior_producer_proof = {"episode_id": prior_eid, "source": prior_event_ref,
        "initial_write_line": 78, "initial_write_return_line": 79,
        "final_literal_next_step_assignment_call_line": 90, "final_actual_return_line": 91,
        "actual_call_id": prior_final["id"], "actual_return_exit_code": 0,
        "safe_initial_json_plus_literal_assignment_equals_final_original_review": True,
        "prior_tool_return_timestamp_ms": prior_return["timestamp"],
        "later_actual_feedback_read_timestamp_ms": events[9]["message"]["timestamp"],
        "prior_production_before_later_read": True, "historical_code_executed_by_auditor": False,
        "scope": "This one original review producer, outer exact-field projection, and later observed feedback JSON; no generic producer inference"}
    old_data, old_ref = read_bytes(peid, "workspace/inputs/previous_skill/scripts/check_paper.py")
    new_data, new_ref = read_bytes(peid, "workspace/outputs/skill/scripts/check_paper.py")
    assert old_data and new_data and old_data != new_data

    def pattern_from_script(data):
        tree = ast.parse(data.decode("utf-8-sig"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SUPERCITE" for t in node.targets):
                assert isinstance(node.value, ast.Call) and node.value.args
                return ast.literal_eval(node.value.args[0])
        raise AssertionError("SUPERCITE literal missing")

    old_pattern, new_pattern = pattern_from_script(old_data), pattern_from_script(new_data)
    literal_fixture = "^[1][2]^ ^[1,2]^ ^[3]^"
    old_matches = [m.group(0) for m in re.finditer(old_pattern, literal_fixture)]
    new_matches = [m.group(0) for m in re.finditer(new_pattern, literal_fixture)]
    assert old_matches == ["^[1,2]^", "^[3]^"] and new_matches == ["^[1][2]^", "^[1,2]^", "^[3]^"]
    causal_events = []
    for call_line, return_line in [(9, 10), (18, 19), (21, 22), (24, 25), (27, 28), (30, 31),
                                   (33, 34), (36, 37), (42, 43), (45, 46), (48, 49)]:
        call = events[call_line-1]["message"]
        ret = events[return_line-1]["message"]
        calls_here = [b for b in call.get("content") or [] if b.get("type") == "toolCall"]
        assert len(calls_here) == 1 and calls_here[0]["id"] == ret.get("toolCallId")
        text = "\n".join(b.get("text", "") for b in ret.get("content") or [] if b.get("type") == "text")
        causal_events.append({"source": {**eref, "call_line": call_line, "return_line": return_line},
            "tool_call_id": calls_here[0]["id"], "tool_name": calls_here[0]["name"],
            "arguments_sha256": jsha(calls_here[0].get("arguments")), "return_text_sha256": sha(text.encode()),
            "return_exit_code": (ret.get("details") or {}).get("exitCode"),
            "return_is_error": ret.get("isError"), "contains_traceback": "Traceback" in text,
            "contains_assertion_error": "AssertionError" in text})
    raw_regression = "\n".join(b.get("text", "") for b in events[36]["message"]["content"] if b.get("type") == "text")
    assert "--- 1 good" in raw_regression and "--- 2 bad" in raw_regression and "exit=0" in raw_regression and "exit=1" in raw_regression and "exit=2" in raw_regression
    diff_text = "\n".join(b.get("text", "") for b in events[48]["message"]["content"] if b.get("type") == "text")
    assert len([l for l in diff_text.splitlines() if l.startswith("Files ")]) == 3
    case_reviews.append({"case_id": "native_paper_citation_feedback_repair", "route_id": "paper-drafting", "category": "EDU",
        "sampling_reason": "bounded_native_true_feedback_revision_regression",
        "review_level": "prior_review_projection_exact_json_equality; actual_pre_action_read; observed_state_and_regression_receipts; safe_AST_literal_regex_data_check",
        "deidentified_observation_zh": "原反馈明确相邻括号多引文被检查器漏识别并造成合法引用被删。当前原生会话先读真实反馈/旧脚本，再局部修正并测试好例/坏例/干净与脏样例及缺输入边界。独立只解析原脚本AST常量并用标准库regex核对：旧pattern漏相邻括号，新pattern识别；未执行旧候选程序。注意apply_patch虽报publish错误，后续读取证明修改已生效；另一次shell整体exit0却含AssertionError，不能仅按exit0判整条成功。原记录保留这些失败和状态核对，最后diff仅三文件。此例证明真实局部因果修订，不证明独立业务Q、成本改善或自主A-D控制。",
        "feedback": refs[(peid, "workspace/inputs/previous_feedback.json")],
        "prior_review_producer_projection": projection,
        "prior_review_exact_original_producer_and_time_proof": prior_producer_proof,
        "actual_feedback_read_line": 10, "observed_first_json_exact_equal_frozen_feedback": True,
        "old_script": old_ref, "new_script": new_ref, "safe_literal_pattern_check": {"old_matches": old_matches, "new_matches": new_matches,
            "candidate_code_executed_by_auditor": False},
        "actual_original_event_chain": causal_events,
        "regression_scope": "same-version program fixture and negative/boundary cases, not a new held-out business rerun",
        "source_scope": lineage.get(peid), "not_new_training_admission": True})

    for label, path, note in [
        ("outer_controller", ROOT / "pipeline.py", "原控制器plan/continue_selection/finish/publish负责派发分场、基线复用、审核决策映射、原子复制发布；不是从Agent工具输出中恢复出的自主阶段控制。将这些接线记录作为state/action接口标注可研究，但必须标derived/outer_pipeline，不能伪装成教师原响应。"),
        ("external_codex_assistance", ROOT / "output/20261023_codex_assisted_resource_repair/assistance_provenance.json", "原provenance明确Codex辅助而非GLM产出、孤立副本修资源、原GLM失败和成本未改、新GLM请求0且本修复无原生业务复跑。不能将辅助文件追认为原GLM自主修复成功；精确C会话是多任务载体，encrypted_content不是可训练原始思考。"),
        ("historical_exact_version_repair", ROOT / "output/20261026_wrd_lineage_v6/INDEPENDENT_REASONING_REVIEW.json", "历史原request→带真实反馈的局部代码修订→同tool_call_id实际exit0→同43ab93fb版本验证12/12已由逐字AST数据重建和原回执独审证明。先前失败版本继续是失败，不因最终成功追认。该例是反馈修订子链，不能当原生A-D控制全链。"),
    ]:
        data = path.read_bytes()
        case_reviews.append({"case_id": label, "sampling_reason": label,
            "review_level": "original_producer_contract_or_frozen_independent_receipt_read",
            "deidentified_observation_zh": note,
            "source": {"path": str(path), "sha256": sha(data), "bytes": len(data),
                       "json_pointer": "/complete_causal_repair_example_without_enterprise_body" if label == "historical_exact_version_repair" else "",
                       "line_ranges": [[248, 279], [338, 434], [579, 680], [728, 883]] if label == "outer_controller" else None},
            "contract_scope": "Pinned current producer reference corroborates original staged request/job interfaces; not a claim that these exact code bytes ran in every historical iteration" if label == "outer_controller" else None,
            "author_class": "outer_pipeline" if label == "outer_controller" else "external_Codex" if label == "external_codex_assistance" else "observed_historical_teacher_action_and_actual_tool_result",
            "not_new_training_admission": True})
    pointer_rows = json.loads((ROOT / "output/workflow_library/conversations.json").read_text(encoding="utf-8"))
    correction_refs = []
    for sid, indices in [("conv_80a93aaff78b", [15, 101, 125, 143]), ("conv_2d85bcabcb65", [31])]:
        binding = next(x for x in pointer_rows if x["id"] == sid)
        pin = binding["conversation"]
        path = Path(pin["path"])
        data = path.read_bytes()
        assert sha(data) == pin["sha256"]
        source = json.loads(data.decode("utf-8-sig"))
        for i in indices:
            msg = source["messages"][i]
            assert msg["role"] == "user"
            correction_refs.append({"source_id": sid, "source_pin": pin, "original_mother_line": binding["line"],
                "message_id": msg["id"], "json_pointer": f"/messages/{i}/content",
                "original_user_content_sha256": sha(msg["content"].encode()),
                "source_is_original226": sid in formal})
    case_reviews.append({"case_id": "original_user_corrections_not_success_labels", "route_id": "web-html-prototype",
        "sampling_reason": "real_user_feedback_authorship_and_uncovered_branch",
        "review_level": "pinned_original_user_messages_read; no_reconstructed_hidden_thought_or_assumed_business_success",
        "deidentified_observation_zh": "原消息确有重复黑屏、卡片不显示、技能不可用及未按开工指令执行的用户纠正。它们应与后续修订和用户个性条件一起保留；用户投诉是实际负反馈，不等于后续每个版本都修复成功。本次建库试做的太阳系/摩擦力不是原复杂游戏回归，不能当原游戏全通过证据。",
        "author_class": "original_business_user", "sources": correction_refs,
        "causal_scope": "User feedback existence and original order only; consumption by every later maker and exact repair causality require their own native read/version links",
        "not_human_gold": True, "not_new_training_admission": True})
    with (OUT / "CASE_REVIEWS.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for x in case_reviews:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    brief["semantic_sample_summary"] = {"cases": len(case_reviews), "route_review_cases": len(REVIEW_NOTES),
        "route_review_categories": sorted({v[0] for v in REVIEW_NOTES.values()}),
        "zero_case_prepare_examples": 2, "controller_external_author_and_historical_repair_examples": 3,
        "bounded_native_feedback_repair_examples": 1,
        "original_user_correction_examples": 1,
        "actual_call_return_pairs_rechecked": sum(len(c["verified_native_observations"]) for x in case_reviews for c in x.get("paired_cases", [])),
        "full_population_semantic_accuracy_estimated": False,
        "scope": "Stratified original reasoning/requirements and exact tool evidence, not a representative random sample or independent Q calibration"}
    brief["documented_chain_coverage"]["bounded_native_feedback_revision_regression_proof"] = "CASE_REVIEWS.jsonl case native_paper_citation_feedback_repair"
    write(OUT / "CHAIN_QUALITY.json", brief)
    print(json.dumps({k: brief[k] for k in ["output_branch_coverage", "documented_chain_coverage", "original226_boundary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
