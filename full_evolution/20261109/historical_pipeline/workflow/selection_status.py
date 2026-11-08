"""Explain saved selection progress and costs; never dispatch or change the DB."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import math

from . import business_cost


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def _active_cases(route):
    cases = route.get("tasks") or []
    if "active_case_ids" in route:
        wanted = set(route["active_case_ids"])
        return [case for case in cases if case.get("id") in wanted]
    return [case for case in cases if case.get("value_revision_of")] or cases


def _progress(route, jobs):
    follow = route.get("selection_repair") or {}
    active = [job for job in jobs if job.get("status") in ("pending", "running", "unknown")]
    if active:
        unknown = any(job.get("status") == "unknown" for job in active)
        return {"state": "evidence_pending" if unknown else "continuing",
                "label": "执行状态不明，先核对原记录" if unknown else "本次接续中" if follow else "原任务继续处理中",
                "reason": "；".join(f"{job.get('kind')}:{job.get('status')}" for job in active)}
    if follow.get("status") in ("blocked", "blocked_inputs"):
        return {"state": "awaiting_independent_input" if follow["status"] == "blocked_inputs" else "evidence_pending",
                "reason": route.get("task_note") or "接续被阻塞，原结果和费用保留"}
    if not _active_cases(route):
        return {"state": "awaiting_independent_input", "reason": route.get("task_note") or "尚无可独立执行的同类真实任务"}
    if route.get("library_status") == "retained":
        return {"state": "retained", "reason": "资源与交付沿原评审，包含本版失败的业务成本已双降"}
    if route.get("library_status") == "rejected":
        return {"state": "rejected", "reason": (route.get("value_review") or {}).get("reason", "")}
    if route.get("library_status") == "needs_revision":
        return {"state": "repair_parked", "reason": "当前没有在排队的修复任务；已有失败、资源及费用保留"}
    return {"state": "evidence_pending", "reason": route.get("retention_display_note") or (route.get("value_review") or {}).get("reason") or "等待完整业务证据"}


def enrich(routes, jobs, records_root, campaign=None):
    """Enrich snapshot route dicts only; return the campaign/status summary.

    Filesystem access is delegated solely to the cached business-cost reader.
    All attempt history and old conclusions remain untouched. Display-only
    downgrades do not rewrite saved review outcomes or trigger model work.
    """
    by_id = {job["id"]: job for job in jobs}
    by_route, by_case = {}, {}
    for job in jobs:
        by_route.setdefault(job.get("route_id"), []).append(job)
        if job.get("kind") == "actor":
            by_case[(job.get("route_id"), job.get("case_id"), job.get("arm"))] = job
    before = sum(route.get("library_status") == "retained" for route in routes)
    changed = []
    for route in routes:
        sid = route["id"]
        cases = {case.get("id"): case for case in route.get("tasks", [])}
        active = {case.get("id") for case in _active_cases(route)}
        costs = {}
        for comparison in route.get("comparison", []):
            cid = comparison.get("case_id")
            comparison["scope_note"] = cases.get(cid, {}).get("scope_note", "")
            if cid not in active and not comparison["scope_note"]:
                comparison["scope_note"] = "历史任务/旧版本，原结果与费用保留"
            for arm in ("no_skill", "workflow"):
                job = by_case.get((sid, cid, arm))
                if job:
                    costs[(cid, arm)] = business_cost.all_attempts(job, by_id, records_root)
                    if isinstance(comparison.get(arm), dict):
                        comparison[arm]["all_attempts"] = deepcopy(costs[(cid, arm)])
        current = {arm: [0, 0] for arm in ("no_skill", "workflow")}
        totals = {arm: [0, 0] for arm in current}
        complete_pair, complete_all = bool(active), bool(active)
        for cid in active:
            for arm in current:
                job = by_case.get((sid, cid, arm)) or {}
                result = job.get("result") or {}
                usage = result.get("usage") or {}
                tokens = result.get("tokens", usage.get("total_tokens"))
                calls = result.get("calls", usage.get("model_calls"))
                measured = job.get("status") == "done" and _number(tokens) and _number(calls)
                complete_pair = complete_pair and measured
                if measured:
                    current[arm][0] += tokens
                    current[arm][1] += calls
                cost = costs.get((cid, arm))
                if cost is None and job:
                    cost = business_cost.all_attempts(job, by_id, records_root)
                cost = cost or {}
                values = (cost.get("total_tokens"), cost.get("model_calls"))
                complete_all = complete_all and measured and all(_number(v) for v in values) and cost.get("unknown_calls") == 0
                for column, value in enumerate(values):
                    if not _number(value):
                        totals[arm][column] = None
                    elif totals[arm][column] is not None:
                        totals[arm][column] += value
        pair_reduced = all(current["workflow"][i] < current["no_skill"][i] for i in (0, 1)) if complete_pair else None
        all_reduced = all(totals["workflow"][i] < totals["no_skill"][i] for i in (0, 1)) if complete_all else None
        route["performance"] = {"completed_pair_reduced": pair_reduced, "all_attempts_reduced": all_reduced,
                                "completed_totals": current if complete_pair else None,
                                "all_attempt_totals": totals, "active_case_ids": sorted(active),
                                "basis": "本版活动任务全部业务尝试，含失败；制作、准备、评审费用单列"}
        if route.get("library_status") == "retained" and all_reduced is not True:
            route["original_library_status"] = "retained"
            route["library_status"] = "candidate"
            route["retention_display_note"] = "原成功对照保留记录仍在；含本版失败的业务总开销未证明双降" if pair_reduced else "原保留记录仍在；当前业务成本证据不足或未双降"
            route["make_status"] = "候选：含失败的业务减负待证"
            changed.append({"id": sid, "completed_pair_reduced": pair_reduced,
                            "all_attempts_reduced": all_reduced, "reason": route["retention_display_note"]})
        route["selection_progress"] = _progress(route, by_route.get(sid, []))
    summary = deepcopy(campaign or {})
    campaign_id = summary.get("id")
    source_job_ids = set(summary.get("source_job_ids", []))
    selected_jobs = [job for job in jobs if campaign_id and (
        (job.get("payload") or {}).get("selection_repair") == campaign_id or job.get("id") in source_job_ids)]
    counts = Counter(job.get("status") for job in selected_jobs)
    route_counts = Counter((route.get("selection_repair") or {}).get("status", "waiting") for route in routes
                           if campaign_id and (route.get("selection_repair") or {}).get("id") == campaign_id)
    summary["counts"] = {state: counts.get(state, 0) for state in ("pending", "running", "done", "failed", "unknown", "held")}
    summary["route_status_counts"] = dict(route_counts)
    if campaign_id:
        blocked = route_counts["blocked"] or route_counts["blocked_inputs"]
        unfinished = sum(count for state, count in route_counts.items() if state != "complete")
        summary["status"] = ("running" if counts["running"] else "pending" if counts["pending"] else
                             "unknown" if counts["unknown"] else "failed" if counts["failed"] or counts["held"] else
                             "held" if blocked else "pending" if unfinished else "done")
    summary["retention_reconciliation"] = {"original_retained": before,
        "including_failed_attempts_retained": sum(route.get("library_status") == "retained" for route in routes),
        "display_only_downgrades": changed, "saved_reviews_unchanged": True}
    return summary
