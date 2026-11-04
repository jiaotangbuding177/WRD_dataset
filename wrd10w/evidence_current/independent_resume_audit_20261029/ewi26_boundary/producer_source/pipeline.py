"""Bounded DATA teacher collection, fixed packaging and independent consumption.

Run explicitly: python -m research.pipelines.skillsloop_ewi_v2.pipeline --stage ...
No training, baseline mutation or automatic HTTP retries.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
import platform
import sys
import time

from .budgets import EpisodeBudget, PilotBudget
from .contracts import action_contract
from .data_profile import build_profile, canonical_sha, read, sha, verify_profile, write
from .engine import EpisodeEngine
from .teacher_client import TeacherClient

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/20261015_ewi_teacher_DATA"
PRIVATE = ROOT / "output/20261008_openclaw_eval/private/model_evolution_32768.json"
BINDING = {"design_revision": "4.1.4", "change_id": "ALG-20261015-13", "schema_version": "skillsloop-ewi-rl-v2"}
PROTOCOL_NAME = "frozen_protocol.v414.json"
TEACHER_OUTPUT_CAP = 12288

SYSTEM = '''你是EWI教师策略，完整原始会话→有证据的可复用工作流。现在收集真实探索示范，并非训练或解正式评测题。
原始完整用户及其全部AI段落是学习材料；历史AI可能说错、失败或只声称成功。将用户纠正及个性化要求作为有生效范围的依据；不能照抄AI错误，也不能假装本机环境是历史环境。
你拥有六个动作READ/INSPECT/REPLAY/TRY/UPDATE/FINISH。W初始为空，自主决定需要什么证据。先看完整原会话和资源真实情况；可从L0直接形成有据工作流，也可检查文件、局部执行、有限对照。不要凑调用或skill数量。
G为证据关系，W为工作流，U为影响做法的疑点，L为宿主真实资产账本。仅UPDATE能原子修订G/W/U；模型不能改L或造actual/verified回执。历史陈述不升为已验证执行，工具exit0也不是业务正确。
本轮每source最多12次教师决策（含格式错误和拒绝），6工具调用，共2执行分支，1200秒。paired_comparison占2分支。不要只消耗工具却来不及更新并FINISH；保留最后决策用于合法结束。有明确阻塞但预算不足则DEFERRED，不把它写成成功。
工作流id必须以当前source_id加'_w'开头，跨episode唯一。step id可以s1等。引用用实际source_id和实际turn_index，若quote则必须原文逐字子串。当前执行引用必须取真实observation.execution_id。
参数包括未来输入路径、输出路径、字段、数量、业务实体；实例中的公司、人名、金额、时间、文件名不能机械固化成泛用规则。用户纠正中真正稳定的偏好应保留，并说明范围。不要把个别会话个人昵称传播到其他用户。
若需要脚本：先建立W再TRY；Python仅操作WORKSPACE内明确投递资源和outputs。先INSPECT真实结构，读取全表而非只样本；用可复用函数/命令行参数，不把本次输入内容写死成答案。脚本若是只用于诊断的一次性尝试，reusable_asset=false。所声明checks需要在代码里实际assert。失败/报错是需要吸收的观察，不重写为成功。
若当前可复用资产确实测试通过，UPDATE时可以把真实asset_id纳入W并用operation说明未来如何传参调用；禁止引用一个不存在的scripts路径。原始输入仅作为未来用户参数，不作为skill附件。不需要脚本的程序性工作流可以只交文字，但明确步骤、条件、关键动作、最基本交付检查和未知。
每轮仅返回一个可json.loads的ActionProposal对象，不输出Markdown或私有思维链。short purpose解释可公开的证据需求。严格照action_contract字段。最近一次拒绝应按真实错误修正，不一再重复同样提案。FINISH必须对每个当前W恰好给一个READY/DEFERRED/NO_REUSABLE决定，不能漏；READY只是可进行独立消费，不代表有效或准入。没有可复用W时FINISH arguments={decisions:[],resolution:'NO_REUSABLE',reason:'具体理由'}。
不访问正式250、开发题、旧skill基线、凭据或外部服务。可用资源/能力仅限payload。'''


def rows(path):
    return [json.loads(line) for line in Path(path).read_text("utf-8-sig").split("\n") if line.strip()]


def prepare(out=OUT):
    out = Path(out)
    profile_path = out / "data/profile.json"
    profile = read(profile_path) if profile_path.exists() else build_profile(out / "data")
    verify_profile(profile)
    frozen_design = out / "frozen/designs_v414"
    frozen_design.mkdir(parents=True, exist_ok=True)
    for name in ("A_B_MODULES.md", "PIPELINE.md"):
        original, target = ROOT / "research/designs" / name, frozen_design / name
        if target.exists() and target.read_bytes() != original.read_bytes():
            raise ValueError("Design changed since pilot freeze")
        target.write_bytes(original.read_bytes())
    code_dirs = [Path(__file__).parent, ROOT / "research/pipelines/skillsloop_ewi", ROOT / "research/pipelines/skillsloop_graph"]
    pins = [{"path": str(path), "sha256": sha(path)} for directory in code_dirs
            for path in sorted(directory.glob("*.py"))]
    pins.extend({"path": str(frozen_design / name), "sha256": sha(frozen_design / name)}
                for name in ("A_B_MODULES.md", "PIPELINE.md"))
    if (out / "frozen_protocol.v411.json").exists():
        pins.append({"path": str(out / "frozen_protocol.v411.json"), "sha256": sha(out / "frozen_protocol.v411.json")})
    if (out / "frozen_protocol.v413.json").exists():
        pins.append({"path": str(out / "frozen_protocol.v413.json"), "sha256": sha(out / "frozen_protocol.v413.json")})
    native = deepcopy(read(ROOT / "output/20261015_DATA_four_arm_comparison/protocol.json")["native"])
    native.update(bound_design=BINDING, design_directory=str(frozen_design), model_config_path=str(PRIVATE), actor_max_tokens=8192)
    native["limits"] = {"model_calls": 24, "tool_calls": 40, "output_tokens": 24*8192,
                        "wall_seconds": 900, "new_bytes": 104857600}
    protocol = {"schema": "ewi-teacher-DATA-pilot-v2", "bound_design": BINDING,
        "profile_fingerprint": profile["profile_fingerprint"], "pins": pins,
        "teacher": {"model": "ecnu-max", "thinking": {"type": "enabled"}, "reasoning_effort": "low",
                    "max_tokens": TEACHER_OUTPUT_CAP, "max_decisions": 12, "max_tools": 6, "execution_branches": 2,
                    "source_output_reservation_cap": 147456,
                    "source_seconds": 1200, "concurrency_after_first": 3, "request_seconds": 900},
        "teacher_prompt_sha256": canonical_sha(SYSTEM), "action_contract_sha256": canonical_sha(action_contract()),
        "fixed_M5": {"model": "ecnu-plus", "max_tokens": 16000, "max_calls": 29, "request_seconds": 300},
        "private_config_path": str(PRIVATE), "private_config_sha256": sha(PRIVATE), "native": native,
        "environment": {"python": sys.executable, "python_version": sys.version, "platform": platform.platform(),
                        "S0": "fresh source-owned copies per physical branch; historical machine state not restored"},
        "limits": {"model_calls": 475, "tool_calls": 334, "output_tokens": 5551232, "wall_seconds": 21600},
        "sft_approved": False, "rl_on_policy": False, "weight_training": False, "formal250_used": False,
        "compatible_retained_parent_protocols": [str(out / name) for name in
            ("frozen_protocol.v411.json", "frozen_protocol.v413.json") if (out / name).exists()],
        "transport_projection": "Preserve complete paired turns and all provenance; omit messages only if deep-equal to complete turn expansion",
        "resource_adaptation": {"parent_protocol": str(out / "frozen_protocol.json"),
            "parent_protocol_sha256": sha(out / "frozen_protocol.json") if (out / "frozen_protocol.json").exists() else None,
            "reason": "Two high/12288 responses exhausted reasoning allowance with zero public action; identical observation was triplicated",
            "same_global_and_source_caps_and_original_clocks": True,
            "retained_physical_observations_not_rerun": True, "complete_source_never_truncated": True}}
    protocol["fingerprint"] = canonical_sha(protocol)
    destination = out / PROTOCOL_NAME
    if destination.exists() and read(destination) != protocol:
        raise ValueError("Existing protocol differs; preserve it and investigate, do not overwrite")
    write(destination, protocol)
    return protocol, profile


def load(out):
    protocol, profile = read(out / PROTOCOL_NAME), read(out / "data/profile.json")
    verify_profile(profile)
    for pin in protocol["pins"]:
        if sha(pin["path"]) != pin["sha256"]:
            raise ValueError("Frozen code/design changed: " + pin["path"])
    if sha(PRIVATE) != protocol["private_config_sha256"]:
        raise ValueError("Model configuration changed")
    for key, actual in (("python", sys.executable), ("python_version", sys.version), ("platform", platform.platform())):
        if protocol["environment"][key] != actual:
            raise ValueError("Frozen execution environment changed: " + key)
    return protocol, profile


def source_fingerprint(source, assets, protocol):
    return canonical_sha({"source": source, "assets": assets, "protocol": protocol["fingerprint"],
                          "S0": protocol["environment"]["S0"]})


def policy_view(engine):
    """Remove identical transport copies, preserving one full observation.

    This is not a summary, evidence filter or source-turn truncation.
    """
    view = deepcopy(engine.view())
    view.get("state", {}).pop("latest_observation", None)
    # assets is the real L, including execution assets absent from input_assets.
    # Keep both catalogs; only demonstrably identical observations are deduped.
    return view


def public_interactions(transcript):
    values = deepcopy(transcript[-4:])
    for item in values:
        event = item.get("event", {})
        observation = event.pop("observation", None)
        if observation is not None:
            event["observation_ref"] = {key: observation.get(key) for key in
                ("execution_id", "tool_return_ref", "tool_return_sha256")}
    return values


def retained_model_floor(directory):
    # Physical request files are written before HTTP. Charging every admission
    # conservatively also covers a process interrupted before a final receipt.
    calls = {path.parent.name: read(path)["max_tokens"] for path in
             sorted((directory / "model_calls").glob("*/request.raw.json"))}
    ledger = directory / "model_calls/model_ledger.json"
    if ledger.exists():
        for item in read(ledger):
            if not item.get("cached"):
                calls[item["call_id"]] = max(calls.get(item["call_id"], 0), item["max_output_tokens"])
    return {"model_calls": len(calls), "output_tokens": sum(calls.values())}


def source_for_policy(source):
    projected = deepcopy(source)
    expanded = [message for turn in projected["turns"] for message in
                [turn["user"], *turn["assistant_messages"]]]
    if projected.get("messages") == expanded:
        del projected["messages"]
    return projected


def run_source(source, assets, out, protocol, global_budget):
    source = deepcopy(source)
    sid = source["source_id"] = source.get("source_id", source.get("session_id"))
    assets = [asset for asset in assets if asset["source_id"] == sid]
    fingerprint = source_fingerprint(source, assets, protocol)
    directory, regpath = out / "episodes" / sid, out / "registry" / (sid + ".json")
    if regpath.exists():
        registry = read(regpath)
        import_receipt = None
        if registry["fingerprint"] != fingerprint:
            parents = [read(path) for path in protocol.get("compatible_retained_parent_protocols", [])]
            compatible = next((parent for parent in parents if source_fingerprint(source, assets, parent)
                               == registry["fingerprint"]), None)
            if compatible is None:
                raise ValueError("Retained episode fingerprint changed")
            import_receipt = {"source_id": sid,
                "original_protocol_fingerprint": compatible["fingerprint"],
                "consuming_protocol_fingerprint": protocol["fingerprint"],
                "mode": "IMMUTABLE_PARENT_TERMINAL_IMPORT", "new_teacher_calls": 0, "new_tool_calls": 0,
                "same_source_and_assets_verified": True, "original_outcome_unchanged": registry["status"]}
        for pin in registry["pins"]:
            if sha(pin["path"]) != pin["sha256"]:
                raise ValueError("Retained source episode bytes changed")
        if import_receipt is not None:
            write(out / "reused_episodes" / (sid + ".json"), import_receipt)
        return read(directory / "export.json")
    resume_permit = directory / "resource_adaptation_resume_permit.json"
    if directory.exists():
        if not resume_permit.exists():
            raise RuntimeError("Incomplete episode retained without explicit technical adaptation permit: " + sid)
        permit = read(resume_permit)
        if permit.get("target_design_revision") != BINDING["design_revision"]:
            raise ValueError("Technical continuation permit does not match this design")
        floor = retained_model_floor(directory)
        budget = EpisodeBudget(global_budget, inherited_spent=floor)
        engine = EpisodeEngine.resume(directory, budget)
        if canonical_sha(engine.by_source[sid]) != canonical_sha(source):
            raise ValueError("Complete source changed during technical continuation")
        serial_start = 1 + max(int(path.name.rsplit("_", 1)[1]) for path in
            (directory / "model_calls").glob("decision_*") if path.is_dir())
        transcript = read(directory / "decision_transcript.json")
        transcript.append({"status": "RESOURCE_ADAPTATION_CONTINUATION", "prior_model_admissions": floor,
            "prior_completed_observations_retained": True, "model_and_tool_replays": 0,
            "old_inflight_request": permit.get("interrupted_request"), "reason": permit["reason"]})
        if permit.get("allow_reopen_transport_failure") and engine.status == "INFRA_ERROR":
            if any(event["status"] == "PENDING" for event in engine.actions):
                raise ValueError("An interrupted physical tool cannot be automatically repeated")
            transcript[-1]["original_infrastructure_stop"] = engine.stop_reason
            engine.status, engine.stop_reason = "RUNNING", None
            engine.persist()
    else:
        budget = EpisodeBudget(global_budget)
        engine = EpisodeEngine(source, assets, directory, budget, config={"category": "DATA", "episode_id": sid,
            "max_actions": 12, "max_local_replays": 2, "max_comparisons": 1, "max_execution_branches": 2,
            "execution_timeout_seconds": 120, "python_executable": sys.executable})
        serial_start, transcript = 1, []
    client = TeacherClient(directory / "model_calls", {"model_config_path": str(PRIVATE)}, budget)
    failure = None
    for serial in range(serial_start, 13):
        remaining = budget.remaining()
        if (engine.status != "RUNNING" or remaining["seconds"] <= 0
                or remaining["model_calls"] < 1 or remaining["output_tokens"] < TEACHER_OUTPUT_CAP):
            break
        payload = {"action_contract": action_contract(), "current_source_id": sid,
                   "complete_source": source_for_policy(source), "original_complete_source_sha256": canonical_sha(source),
                   "state": policy_view(engine), "recent_interactions": public_interactions(transcript),
                   "decision_number": serial,
                   "decisions_left_including_this": min(remaining["model_calls"], remaining["output_tokens"]//TEACHER_OUTPUT_CAP),
                   "true_admissible_model_calls": min(remaining["model_calls"], remaining["output_tokens"]//TEACHER_OUTPUT_CAP),
                   "configured_request_output_cap": TEACHER_OUTPUT_CAP,
                   "remaining_budget": remaining}
        write(directory / "decision_inputs" / ("%03d.json" % serial), payload)
        try:
            proposal = client.ask("EWI_TEACHER", "decision_%03d" % serial, SYSTEM, payload, TEACHER_OUTPUT_CAP)
        except Exception as exc:
            item = {"decision": serial, "status": "MODEL_OR_FORMAT_ERROR", "error_type": type(exc).__name__, "error": str(exc)[:300]}
            transcript.append(item)
            write(directory / "decision_transcript.json", transcript)
            engine.persist()
            receipt_path = directory / "model_calls" / ("decision_%03d" % serial) / "receipt.json"
            # Complete but malformed/empty public content can be corrected by
            # a new, budgeted policy decision. Unknown/failed HTTP is terminal.
            if isinstance(exc, TimeoutError) and budget.remaining()["seconds"] <= 0:
                item["status"] = "POLICY_CLOCK_TRUNCATED"
                write(directory / "decision_transcript.json", transcript)
                break
            if not receipt_path.exists() or read(receipt_path).get("status") != "COMPLETE":
                failure = item
                break
            continue
        try:
            if proposal.get("kind") == "UPDATE":
                for entry in proposal.get("arguments", {}).get("workflows", []):
                    if "spec" in entry and not entry["spec"].get("id", "").startswith(sid + "_w"):
                        raise ValueError("New workflow id must start with current source_id+'_w'")
            event = engine.step(proposal)
        except (ValueError, KeyError, TypeError) as exc:
            # Repeated ids are refused before engine mutation to avoid
            # executing the same physical tool twice; the policy can repair.
            event = {"status": "REJECTED", "error_type": type(exc).__name__, "error": str(exc)}
        transcript.append({"decision": serial, "proposal": proposal, "event": event})
        write(directory / "decision_transcript.json", transcript)
    if engine.status == "RUNNING":
        engine.status = "INFRA_ERROR" if failure else "TRUNCATED"
        engine.stop_reason = "Model transport error retained" if failure else "Teacher decision/wall limit; no forced FINISH"
        engine.persist()
    export = engine.export()
    write(directory / "export.json", export)
    paths = [path for path in directory.rglob("*") if path.is_file()]
    write(regpath, {"source_id": sid, "fingerprint": fingerprint, "status": engine.status,
        "reusable_without_rerun": engine.status == "FINISHED", "retry_automatically": False,
        "pins": [{"path": str(path), "sha256": sha(path)} for path in sorted(paths)],
        "sft_approved": False, "rl_on_policy": False})
    print(json.dumps({"source_id": sid, "status": engine.status, "decisions": len(client.records),
                     "actions": len(engine.actions), "ready": len(export["ready_workflows"]),
                     "observations": len(engine.ewi.observations)}, ensure_ascii=False), flush=True)
    return export


def explore(out, first_only=False):
    protocol, profile = load(out)
    sources, assets = rows(profile["construction_sources"]), rows(profile["asset_refs"])
    # One complete small real source validates the live action/observation
    # integration first. This ordering never accesses development task text.
    sources.sort(key=lambda source: len(json.dumps(source, ensure_ascii=False)))
    budget = PilotBudget(out / "budget.json")
    results, gate_sources, fresh_canaries = [], 0, 0
    # Completed parent outcomes are immutable imports, not new low-effort
    # samples. The new resource condition gets at most two untouched canaries.
    for source in sources:
        sid = source.get("source_id", source.get("session_id"))
        retained = (out / "registry" / (sid + ".json")).exists()
        if not retained and fresh_canaries >= 2:
            break
        results.append(run_source(source, assets, out, protocol, budget))
        gate_sources += 1
        if not retained:
            fresh_canaries += 1
        if results[-1]["episode_status"] == "FINISHED":
            break
    if not first_only:
        if not any(result["episode_status"] == "FINISHED" for result in results):
            raise RuntimeError("Two calibration sources did not close; no wider teacher concurrency")
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(run_source, source, assets, out, protocol, budget) for source in sources[gate_sources:]]
            for future in as_completed(futures):
                results.append(future.result())
    summary = {"status": "FIRST_SOURCE_ONLY" if first_only else "EXPLORATION_RETAINED", "sources": len(results),
        "source_status_counts": dict(Counter(result["episode_status"] for result in results)),
        "ready_workflows": sum(len(result["ready_workflows"]) for result in results),
        "budget_spent": budget.spent(), "formal250_used": False, "training_performed": False}
    write(out / "exploration_summary.json", summary)
    return summary


def package(out):
    from .packaging import package_workflows
    protocol, _ = load(out)
    registry = [read(path) for path in sorted((out / "registry").glob("*.json"))]
    exports = [read(out / "episodes" / item["source_id"] / "export.json") for item in registry]
    client = TeacherClient(out / "M5_model_calls", {"model_config_path": str(PRIVATE)}, PilotBudget(out / "budget.json"))
    return package_workflows(out / "packaging", exports, client, BINDING)


def trial(out):
    from .trial import run_comparison
    from ..skillsloop_graph.native_bridge import run_episode
    protocol, profile = load(out)
    manifest = read(out / "packaging/M5/candidate_1/manifest.json")
    budget = PilotBudget(out / "budget.json")
    ticket_file = out / "comparison_budget_ticket.json"
    if ticket_file.exists():
        ticket = read(ticket_file)["ticket"]
    else:
        ticket = budget.reserve_external(model_calls=96, tool_calls=160, output_tokens=96*8192)
        write(ticket_file, {"ticket": ticket})
    def guarded_runner(*args):
        # Each native run already has an absolute 900s bound. Reserve this
        # bound before starting; never launch it with insufficient whole time.
        if budget.remaining()["seconds"] < 900:
            raise RuntimeError("Cumulative wall clock cannot admit another bounded native trial")
        return run_episode(*args)
    result = run_comparison(out / "comparison", Path(manifest["library_path"]), protocol["native"], profile,
                            runner=guarded_runner)
    if ticket in budget.pending:
        costs = result["actual_costs"]
        budget.settle_external(ticket, model_calls=costs["actual_model_calls"], tool_calls=costs["actual_tool_calls"],
                               output_tokens=None)  # Native reservations are conservative when per-call caps unavailable.
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--stage", choices=["prepare", "first", "explore", "package", "trial"], required=True)
    args = parser.parse_args()
    if args.stage == "prepare":
        protocol, profile = prepare(args.out)
        print(json.dumps({"status": "FROZEN", "fingerprint": protocol["fingerprint"], "counts": profile["counts"]}, ensure_ascii=False))
    else:
        result = {"first": lambda: explore(args.out, True), "explore": lambda: explore(args.out),
                  "package": lambda: package(args.out), "trial": lambda: trial(args.out)}[args.stage]()
        print(json.dumps(result, ensure_ascii=False, default=str), flush=True)


if __name__ == "__main__":
    main()
