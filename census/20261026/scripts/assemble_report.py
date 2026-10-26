"""Assemble a raw-address census, never an SFT eligibility report."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/20261026_wrd_raw_census_v7"


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def link(path, label=None):
    value = str(path).replace("\\", "/")
    target = "/" + value if len(value) > 1 and value[1] == ":" else value
    return f"[{label or value}](<{target}>)"


def csv_write(name, columns, rows):
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    physical = read("PHYSICAL_ROOTS.json")
    graph = read("SKILL29_LINEAGE_MAP.json")
    audit = read("EXPORT_COVERAGE_AUDIT.json")
    channels = read("NINE_CHANNEL_SERVICE_CENSUS.json")
    supplement = read("EVALUATION_BRANCH_ROOTS.json")
    additional = read("ADDITIONAL_ORIGINAL_ROOTS.json")
    final_discovery = read("FINAL_DISCOVERY_ROOTS.json")
    assisted = read("ASSISTED_REPAIR_SOURCE.json")
    combined_files = additional["base_plus_additional_path_files"] + final_discovery["totals"]["incremental_files"] + assisted["totals"]["incremental_directory_files"]
    combined_bytes = additional["base_plus_additional_path_bytes_without_content_dedup"] + final_discovery["totals"]["incremental_logical_bytes"] + assisted["totals"]["incremental_directory_logical_bytes"]
    assert physical["totals"]["logical_path_files"] == 740167
    assert physical["totals"]["logical_path_bytes"] == 72628618635
    assert graph["canonical_assistant_response_positions"] == 32342
    assert graph["retained_skills"] == len(graph["skills"]) == 29
    assert sum(graph["jobs_by_stage"].values()) == graph["logical_jobs"] == 1751
    assert sum(graph["episodes_by_stage"].values()) == 1822
    assert channels["union_distinct_identifiers"]["native_request_id"] == 31249
    roots = physical["roots"] + additional["roots"] + final_discovery["roots"] + assisted["roots"]
    normalized = [str(item["path"]).replace("\\", "/").lower().rstrip("/") for item in roots]
    assert len(normalized) == len(set(normalized)) == assisted["known_directory_address_union_count"]
    root_columns = ["path", "role", "purpose", "exists", "scan_status", "files", "logical_path_bytes", "filesystem_identity_unique_files", "filesystem_identity_unique_file_bytes"]
    csv_write("ROOTS_ALL_50.csv", root_columns, physical["roots"])
    csv_write("ROOTS_ALL.csv", root_columns, roots)
    csv_write("SKILL29_OVERVIEW.csv", ["skill_id", "name", "entrypoint", "final_file_count", "direct_jobs", "direct_episodes", "screen_output_linked_episodes", "legacy_hint_episodes", "all_related_episodes", "unique_output_tree_content_versions"], graph["skills"])
    csv_write("NINE_CHANNELS.csv", ["lane", "original_event_file", "exists", "bytes", "sha256_before", "stable_during_read"], channels["channels"])

    stage_order = ["screen", "prepare", "make", "actor", "review", "legacy"]
    stage_names = {"screen": "路线筛选", "prepare": "需求/试做准备", "make": "技能/资源制作与修订", "actor": "无技能/有技能业务试做", "review": "评审/反馈", "legacy": "旧格式待重分类"}
    canonical = audit["frozen_canonical"]["by_original_kind_not_semantic_gold"]
    stage_rows = []
    for stage in stage_order:
        row = {"old_catalog_stage_not_semantic_gold": stage,
               "logical_jobs": graph["jobs_by_stage"].get(stage, ""),
               "catalog_attempt_directory_references": graph["episodes_by_stage"][stage],
               **canonical[stage]}
        stage_rows.append(row)
    csv_write("STAGE_COUNTS.csv", ["old_catalog_stage_not_semantic_gold", "logical_jobs", "catalog_attempt_directory_references", "sessions", "messages", "assistant_positions", "nonempty_assistant_positions", "tool_call_positions", "visible_text_positions"], stage_rows)

    examples = []
    with gzip.open(OUT / "indexes/episodes.all.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            episode = json.loads(line)
            stage = episode["kind"]
            if stage == "legacy" or stage in {x["stage"] for x in examples}:
                continue
            files = episode["key_recording_files"]
            sessions = [x for x in files if x["physical_original_path"].replace("\\", "/").endswith("/openclaw_transport/session_events.jsonl")]
            if not sessions:
                continue
            chosen = {"stage": stage, "episode_id": episode["episode_id"], "attempt_path": episode["source_path"], "session_events": sessions[0]["physical_original_path"], "session_exists_now": Path(sessions[0]["physical_original_path"]).is_file()}
            for name in ["request.json", "result.json"]:
                selected = [x for x in files if x["physical_original_path"] == str(Path(episode["source_path"]) / name)]
                chosen[name] = selected[0]["physical_original_path"] if selected else None
            examples.append(chosen)
    (OUT / "REPRESENTATIVE_ORIGINAL_PATHS.json").write_text(json.dumps(examples, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "schema_version": "wrd-raw-census-v7-summary",
        "scope": "Original 29-skill production roots and catalog lineage, without a training-admission filter; separately labelled later evaluation metadata and historical recovery entrances.",
        "answer": "Old preparation failed to align entrance, roles and export scope with the requested whole pipeline. No evidence supports attributing the small 93/106 subset to most original data being unsuitable.",
        "original_enterprise_sources": 1107,
        "retained_skills": 29,
        "root_addresses": len(roots),
        "root_scan_status_counts": dict(Counter(x["scan_status"] for x in roots)),
        "primary_physical_totals": physical["totals"],
        "first50_are_frozen_base_not_all_original_addresses": True,
        "additional_original_iteration_or_case_control_roots": additional["additional_address_count"],
        "additional_incremental_file_paths": additional["totals"]["incremental_files"],
        "additional_incremental_logical_bytes": additional["totals"]["incremental_logical_bytes"],
        "base_plus_additional_path_files": combined_files,
        "base_plus_additional_path_bytes_without_content_dedup": combined_bytes,
        "final_independent_discovery_roots": len(final_discovery["roots"]),
        "final_independent_discovery_incremental_paths": final_discovery["totals"]["incremental_files"],
        "final_independent_discovery_incremental_logical_bytes": final_discovery["totals"]["incremental_logical_bytes"],
        "final_independent_discovery_carrier_filename_counts_not_unique_sessions": final_discovery["filename_counts"],
        "historical_assisted_repair_directory_roots": len(assisted["roots"]),
        "historical_assisted_repair_incremental_paths": assisted["totals"]["incremental_directory_files"],
        "historical_assisted_repair_incremental_logical_bytes": assisted["totals"]["incremental_directory_logical_bytes"],
        "external_exact_original_session_stat_only_not_added_to_directory_totals": assisted["external_exact_file"],
        "additional_carrier_filename_counts_not_new_unique_sessions": additional["filename_counts"],
        "canonical_semantic_counts_scope": "Old parsed 1763 contexts only; not all newly located roots or a global upper bound.",
        "workspace_input_or_copy_cache": physical["category_totals"]["workspace_input_or_copy_cache"],
        "logical_jobs": 1751,
        "catalog_attempt_references": 1822,
        "recoverable_native_contexts": 1763,
        "canonical_messages": 64559,
        "assistant_response_positions": 32342,
        "nonempty_assistant_response_positions": 32014,
        "tool_call_blocks": 30438,
        "stages_original_catalog_labels_not_semantic_gold": stage_rows,
        "original_service_lanes": 9,
        "service_distinct_native_request_ids": 31249,
        "service_event_bytes": channels["channel_event_file_bytes"],
        "service_metadata_is_not_response_body": True,
        "old_auxiliary_metadata_only_rows": 14380,
        "old_primary_rows_not_ai_reviewed": 6692,
        "later_evaluation_metadata_roots": len(supplement["roots"]),
        "later_evaluation_metadata_files_not_additive_with_primary": supplement["logical_metadata_files"],
        "later_evaluation_metadata_bytes_not_additive_with_primary": supplement["logical_metadata_bytes"],
        "actual_trainable_sample_count_established_by_this_census": False,
        "all_raw_data_semantically_audited": False,
        "content_deduplication_of_all_physical_files_complete": False,
        "original226_training_boundary_unchanged": True,
        "original_data_modified": False,
        "training_started": False,
        "new_model_or_agent_runs": 0,
    }
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# WRD原始过程数据地址与旧整理范围核查（v7）", "",
        "本轮回答的是：生成29个skills时留下了哪些原始过程记录、地址在哪里、此前为什么只报93／106条。**已经证实此前整理的入口、角色分类和导出范围没有对齐完整pipeline；不能据此认定大部分原数据没有训练价值。**", "",
        "本轮覆盖29制作主目录，并补入此前遗漏的版本迭代、前序WRD探索、原生病例/控制和交接载体。补根的语义相关性分别待核，不全部冒充29制作的独立新会话。没有启动训练或新业务模型调用，也没有将未审核记录冒充可训练数据集。原226继续隔离训练；其地址/元数据可在普查单列。", "",
        "## 1. 实际核到的规模", "",
        "| 计数对象 | 实际数量 | 含义 |", "|---|---:|---|",
        "| 原始企业输入会话 | 1,107 | 被WRD分析的业务来源，不是制作Agent步数 |",
        "| 路线 | 121 | retained29 / candidate60 / rejected19 / needs_revision13 |",
        "| 制作pipeline逻辑任务 | 1,751 | 包括筛选、准备、制作、业务试做、评审；有复用/重试 |",
        "| attempt目录引用 | 1,822 | 当前pipeline1688＋导入历史134，不能当1822独立业务来源 |",
        "| 旧已解析入口的原生会话上下文 | 1,763 | 64,559条消息；逐一SHA/行号核对，不是新发现全部目录的会话总量 |",
        "| 助手响应位置 | 32,342 | 32,014个非空；不是已经审核准入的SFT条数 |",
        "| 实际工具调用块 | 30,438 | 一个响应可以有多个工具块 |",
        "| 最终留存技能 | 29 | 154个最终包文件，逐文件与原清单SHA一致 |",
        "| 九通道原服务记录 | 9个事件文件 / 76,480,390字节 | 去重native_request_id共31,249；为用量/传输元数据，不能代替响应正文 |",
        "| 首份冻结物理账 | 740,167个 / 72,628,618,635字节 | 34个不重叠根实扫；首50地址另含父根覆盖/后续支线 |",
        f"| 新补迭代/病例/控制载体根 | {additional['additional_address_count']:,}根 / {additional['totals']['incremental_files']:,}文件路径 / {additional['totals']['incremental_logical_bytes']:,}字节 | 包含D-v10—v35、E-v11—v34与前序历史载体，旧子根重叠已剪除 |",
        f"| 独立记忆/原引用反查末批5根 | {final_discovery['totals']['incremental_files']:,}文件路径 / {final_discovery['totals']['incremental_logical_bytes']:,}字节 | concurrency9及D/E原基础设施审计/修复，均实际存在 |",
        f"| 额外Codex辅助修复目录 | {assisted['totals']['incremental_directory_files']:,}文件路径 / {assisted['totals']['incremental_directory_logical_bytes']:,}字节 | 与主GLM制作历史条件分列；另有一个外部原会话文件只stat |",
        f"| 截至本轮已定位地址与物理账合计 | {len(roots):,}根地址 / {combined_files:,}文件路径 / {combined_bytes:,}字节 | 后续8根受限metadata不相加，不等于全盘绝对完整或独立训练语料 |", "",
        f"当前合计约{combined_bytes / 10**9:.2f}GB，采用十进制GB和路径逻辑文件大小，不是实际分配磁盘空间或内容去重训练文本。首份72.63GB基础账中，路径规则识别的输入复制/工作区缓存约63.78GB，新增账另列。基础账按卷号/文件ID去掉3个别名后为740,164身份/72,628,618,530字节；尚未做跨集文件身份或全量内容SHA去重。", "",
        "## 2. 主要原始入口与原文件结构", "",
        f"- 原1107会话母本：{link(ROOT / 'benchmark/enterprise_input_closed_v11_20261012/有效轨迹.jsonl')}（55,556,390字节，SHA与原inventory声明一致）。",
        f"- 原会话到资源绑定：{link(ROOT / 'output/20261021_workflow_skill_library/source_bindings.json')}；拆分正文在同目录 `sources/<conv_id>/conversation.json`。",
        f"- D盘主控制记录、反馈、输入副本、历史版本和镜像：{link(ROOT / 'output/workflow_library')}（389,780文件路径，40,497,632,317字节）。重点入口是 `records/`、`runs/`、`prepare_runs/`、`history/`、`confirmed_snapshots/`、`selection_repair/`、`selected_followup_20261024/final/`。",
        f"- E盘真实执行attempt与工作区：{link('E:/skillloop_runs/workflow_library')}（309,821文件路径，27,706,756,303字节）。包括 `screen__*`、`prepare__*`、`make__*`、`actor__*`、`review__*` 及 `episodes/<id>/attempt_*`。",
        f"- 最终29技能原始文件清单：{link(ROOT / 'output/workflow_library/selected_followup_20261024/final/29技能文件清单.json')}；资源包之外仍保留制作和评审记录。", "",
        "每个原attempt一般同时包含：`request.json`（当时实际输入/资源地址）、`openclaw_transport/session_events.jsonl`（原生助手消息、工具调用和工具返回）、`native_events.jsonl`（调用与用量事件）、`result.json`／`native_result.json`（执行结果），以及 `workspace/inputs`、`workspace/outputs`、修订中的脚本/模板/资料。具体存在性逐条记录，缺失时不补造。`native_events`与`session_events`不能混为同一种正文记录。", "",
        "下面给出每阶段一个实际原会话地址；所有1822个attempt见完整索引。", "",
        "| 旧阶段标签 | 原生会话正文地址 |", "|---|---|",
    ]
    for example in sorted(examples, key=lambda x: stage_order.index(x["stage"])):
        lines.append(f"| {stage_names[example['stage']]} | {link(example['session_events'])} |")
    lines += ["", "## 3. 九并发原服务地址", "", f"来自原始服务清单 {link(ROOT / 'output/workflow_library/services/current.json')}（记录时点2026-10-24 22:19:11 +08:00）；九个文件均存在，读取前后SHA相同。", "", "| 通道 | 原事件文件 | 字节 |", "|---:|---|---:|"]
    for channel in channels["channels"]:
        lines.append(f"| {channel['lane']} | {link(channel['original_event_file'])} | {channel['bytes']:,} |")
    lines += ["", "九通道共享的原入口在 `E:/skillloop_runs/20261021_T0012_native_two_arm/observed_service/src/index.js`。旧28根清单及首轮50地址均漏D盘 `20261021_v10_reuse_iterations`；本轮独审后补账33文件/1,172,454字节，并进一步发现D/E版本迭代及前序载体。清单漏根不自动等于相关所有会话没归档，须按文件/请求血缘核对。九通道ID与catalog响应身份/范围不同，不能相减推算丢失量。", "", "## 4. 旧已解析入口中，各阶段确实有大量过程记录", "", "| 旧目录阶段标签 | 逻辑任务 | attempt引用 | 已恢复会话 | 助手响应位置 | 非空响应 |", "|---|---:|---:|---:|---:|---:|"]
    for row in stage_rows:
        lines.append(f"| {stage_names[row['old_catalog_stage_not_semantic_gold']]} | {row['logical_jobs'] if row['logical_jobs'] != '' else '—'} | {row['catalog_attempt_directory_references']:,} | {row['sessions']:,} | {row['assistant_positions']:,} | {row['nonempty_assistant_positions']:,} |")
    lines += ["", "此表只复核旧已解析入口，**不是新发现全部目录的阶段总量或重标后的阶段金标**。实际原request证实导入历史有角色误分：`jd-resume-screening` 因名称含screen被误作WRD筛选，`contract-review-revision` 的业务对照执行因名称含review被误作WRD评审。134条导入记录需按实际职责重分类。job、attempt和正文计数不能相互替代。", "", "## 5. 29个最终技能的原制作地址图", "", "每个入口列出原业务source、逻辑job、attempt、原请求/会话/用量地址、结果/反馈、输出资源树版本和最终包文件SHA。直接job关联、screen输出关联、仅名称推测的legacy关联分别保留，不把弱关联升级为确定因果。未留存/失败/被替代任务仍在全局索引。", "", "| 最终技能 | 直接job | 直接attempt | 含筛选/历史线索的关联attempt | 输出树内容版本 | 逐技能地址入口 |", "|---|---:|---:|---:|---:|---|"]
    for skill in graph["skills"]:
        lines.append(f"| {skill['name']} (`{skill['skill_id']}`) | {skill['direct_jobs']} | {skill['direct_episodes']} | {skill['all_related_episodes']} | {skill['unique_output_tree_content_versions']} | [JSON](skills29/{skill['skill_id']}.json) |")
    lines += ["", "各技能共享筛选/资源/试做，行数不能相加当独立来源。资源树版本按内容签名区分副本，不将复制的同一skill当新训练案例；输出树存在也不自动证明质量合格。", "", "## 6. 此前为什么会只剩93／106：已经证实的整理问题", "",
        "1. **先把主训练范围缩成make/screen。** 旧主流为6774动作＋343终态标签=7117行；执行/评审另有14380行（Actor8089＋review6291），但只导出canonical引用和目标位置，**没有完整prompt/completion正文**。原正文仍在会话记录内。Actor作为辅助及≤10%混合是旧研究建议，不能据此丢弃试做观察、复现、评估反馈和修订上下文。",
        "2. **把‘未审核’变成了很小的已交付数量。** 7117行中只审核425行，还有6692行未审；250行语义pass后再经公开表门得到134行，其中32行≤16K、61行16–32K、41行>32K，因此公开≤32K最终报93。未审核不等于负质量，公开门槛不等于训练价值。",
        "3. **prepare有整阶段误拦截。** 329会话/3190助手位置被旧benchmark字符串规则拦下，触发文本包含‘不读正式250测试集’这类禁止句。这个误因成立，但修正它仍须逐项保留真实原226资源依赖隔离，不能反向宣称所有prepare都可训练。",
        "4. **按名称子串识别角色不可靠。** 已查到业务筛简历、审合同、devprep和blindjudge混入WRD stage标签的问题；职责必须由实际request与工具上下文决定。",
        "5. **后续106仍是窄分支。** 它是历史请求响应经过资源闭包与质量审核的子集，不是从所有原制作过程算出的可用上限。此前用它解释整个pipeline的数据充分性，范围不成立。",
        "6. **目录发现范围过窄。** 旧清单和首轮普查偏重 `workflow*library` 名称，漏掉D/E的v10—v35迭代及前序WRD生成/原生病例/交接/控制载体。本轮新增完整文件账；是否旧CAS已有、是否同内容/同会话仍需逐项匹配，不由漏根反推全部正文遗漏。", "",
        "旧make/screen的7117行曾有7100行机械编译成功、4874行≤32K；公开投影也有4109行机械编译成功。这些数据证明‘只导出93’不是‘只能解析93’，但机械编译成功本身仍不代表语义/血缘合格。", "", "## 7. 思考、缺失和后续支线不能一刀切", "",
        "原始响应、可见分析说明、工具参数、反馈与修订在地址账中保留。1763段选定native事件无非空独立reasoning字段，不能推广成全盘无思考记录：历史raw request/response已有143个不同reasoning内容，SSE另67响应含原reasoning，且旧response.json曾遗漏SSE字段。两支线粒度/范围不同，不相加当独立WRD任务。其历史恢复报告与首72.63GB基础账分开；本次补根也可能覆盖其中原目录，不能重复相加。", "",
        f"历史request/response恢复证据：{link(ROOT / 'output/20261025_wrd_reasoning_recovery_v4/RAW_RECOVERY_REPORT.json')}；原地址逐条位于对应 `controlled/raw_pairs.all.jsonl.gz`。",
        f"历史SSE证据与原地址：{link(ROOT / 'output/20261025_wrd_reasoning_recovery_v4/SSE_REASONING_RECOVERY_REPORT.json')}；例如 {link(ROOT / 'output/20261015_ewi_teacher_DATA/episodes/conv_1702b763a7ee/model_calls/decision_001/response.partial.raw')}。",
        f"旧入口之外的97段历史native（含正式评测/技术/角色未知，未等同训练准入）：{link(ROOT / 'output/20261025_wrd_reasoning_recovery_v4/HISTORICAL_NATIVE_RECOVERY_REPORT.json')}。", "",
        "1822个attempt中59个没有旧解析器预期位置的自身session_events；其中24个仍有request，27个仍有result。32个内嵌上游事件副本已存在于canonical，不能拿来冒充59个缺失自身响应的新恢复。目录存在1804/1822，存在性与正文可解析性分别列账。", "",
        "50个根地址中34个已实扫、8个子根由父根覆盖，另8个后续正式评测/修订根另做受限metadata stat：3466文件/42,998,543字节，不含它们的workspace/input缓存。对限定820个原制作控制/反馈文件未观察到这8根basename引用，但不据此断言全语义无因果。后续8/4包修订支线保留地址，不把评测隔离误当成不许统计。", "",
        "| 后续评测/修订支线原地址 | 本轮metadata文件数 | metadata字节 |", "|---|---:|---:|"]
    for item in supplement["roots"]:
        lines.append(f"| {link(item['path'])} | {item['files']:,} | {item['logical_metadata_bytes']:,} |")
    lines += ["", "独立记忆和原引用反查另外补入D盘concurrency9及D/E的pipeline_infra_audit、pipeline_infra_repair_v3五根（2288文件/79,705,856字节）。concurrency9的154次原引用实际都指向同一个 `channel8/native_profile.json`，不是154个新会话；其jobs_before快照/配置保留在账。", "",
        f"候选legal-document-drafting还接受过额外Codex修复：{link(assisted['roots'][0]['path'])}。明确分列历史条件，不冒充GLM/OpenClaw同条件制作。其精确原会话地址为 {link(assisted['external_exact_file']['source_path'])}（{assisted['external_exact_file']['bytes']:,}字节）。本轮仅确认该文件stat，未读取/哈希/解析正文，未枚举父目录；它不计为第176个目录，也未混入上述目录总字节。原思考/动作字段内容仍待后续按授权完整解析。", ""]
    lines += ["", "## 8. 新补根的记录载体与全部已定位地址", "",
        f"本轮补扫{additional['additional_address_count']}根，增量{additional['totals']['incremental_files']:,}文件路径/{additional['totals']['incremental_logical_bytes']:,}字节，扫描错误{len(additional['scan_errors'])}。补根父目录中的旧observed_service子根已剪除，D-v10已在补根内，不能另加一次。以下只是文件名载体数，包含复制/缓存，尚未全量解析或内容去重，不能叫新增独立会话/响应。", "",
        "| 新补根中的记录载体文件名 | 文件数（非新独立样本） |", "|---|---:|"]
    for name, count in additional["filename_counts"].items():
        lines.append(f"| `{name}` | {count:,} |")
    lines += ["", f"截至本轮共定位{len(roots)}个地址；这是一份有明确发现规则/统计限制的地址登记，不声称穷尽全盘所有历史记录。原制作主根、版本/病例/控制支线、少量研究衍生材料与正式评测支线的职责分别保留在JSON。`实扫`/`补根实扫`按明确依赖/凭据/重解析排除完成元数据遍历；`父根覆盖`不重复计数；`后续支线`受限metadata另列。", "", "| 原地址 | 状态 | 路径文件数（各自账口径） | 路径字节 |", "|---|---|---:|---:|"]
    labels = {"scanned_and_closed_ledger_verified_against_original_stat": "基础实扫", "complete_regular_file_stat_with_explicit_reference_and_dependency_exclusions": "补根实扫", "complete_regular_file_metadata_stat_with_explicit_exclusions": "末批补根实扫", "complete_regular_file_metadata_stat": "历史辅助修复实扫", "covered_by_parent": "父根覆盖", "existence_only_no_recursive_scan": "后续支线（metadata另列）"}
    for item in roots:
        lines.append(f"| {link(item['path'])} | {labels.get(item['scan_status'], item['scan_status'])} | {item.get('files', '—')} | {item.get('logical_path_bytes', '—')} |")
    lines += ["", "## 9. 可复核产物与结论边界", "",
        "- [SUMMARY.json](SUMMARY.json)、[ROOTS_ALL.csv](ROOTS_ALL.csv)、[NINE_CHANNELS.csv](NINE_CHANNELS.csv)、[STAGE_COUNTS.csv](STAGE_COUNTS.csv)、[SKILL29_OVERVIEW.csv](SKILL29_OVERVIEW.csv)：汇总与全部已定位地址；ROOTS_ALL_50.csv仅保留首份基础表。",
        "- [PHYSICAL_ROOTS.json](PHYSICAL_ROOTS.json)、[controlled/PHYSICAL_FILES.jsonl.gz](controlled/PHYSICAL_FILES.jsonl.gz)：740167条原路径/文件身份/大小/时间账，不含正文。",
        "- [SKILL29_LINEAGE_MAP.json](SKILL29_LINEAGE_MAP.json)、[indexes/episodes.all.jsonl.gz](indexes/episodes.all.jsonl.gz)、[indexes/jobs.all.jsonl.gz](indexes/jobs.all.jsonl.gz)、[indexes/episode_files.all.jsonl.gz](indexes/episode_files.all.jsonl.gz)：原job→attempt→正文/工具/资源文件地址。",
        "- [indexes/skill_version_trees.all.jsonl.gz](indexes/skill_version_trees.all.jsonl.gz)、[NON_RETAINED_AND_FAILED_PROCESS_INDEX.json](NON_RETAINED_AND_FAILED_PROCESS_INDEX.json)：资源版本和未留存/失败支线。",
        "- [EXPORT_COVERAGE_AUDIT.json](EXPORT_COVERAGE_AUDIT.json)：旧解析器、角色、筛选漏斗和1763原event对象的独立核查证据。",
        "- [EVALUATION_BRANCH_ROOTS.json](EVALUATION_BRANCH_ROOTS.json)、[controlled/EVALUATION_METADATA_FILES.jsonl.gz](controlled/EVALUATION_METADATA_FILES.jsonl.gz)：后续正式评测/修订支线，分账保留。", "",
        "- [ADDITIONAL_ORIGINAL_ROOTS.json](ADDITIONAL_ORIGINAL_ROOTS.json)、[controlled/ADDITIONAL_ORIGINAL_FILES.jsonl.gz](controlled/ADDITIONAL_ORIGINAL_FILES.jsonl.gz)：补根闭合路径账、发现规则、旧范围更正、重叠剪除及载体文件名统计。",
        "- [FINAL_DISCOVERY_ROOTS.json](FINAL_DISCOVERY_ROOTS.json)、[ASSISTED_REPAIR_SOURCE.json](ASSISTED_REPAIR_SOURCE.json)：并发配置/原设施回接的末批五根，以及Codex辅助修复目录和精确C盘原会话单文件stat，均分账。",
        "- [FINAL_REGISTRY_RECONCILIATION.json](FINAL_REGISTRY_RECONCILIATION.json)、[indexes/additional_discovery.final_queryable_registry.jsonl.gz](indexes/additional_discovery.final_queryable_registry.jsonl.gz)：独立反查217份10/20—24记忆、原29引用和418个顶层地址。其余状态快照、独立评测、早期参考、语义待核及父子覆盖地址全部登记可查，未递归不等于训练拒绝；不是把418地址冒充418原制作根。",
        "- [STAGE_ADDRESS_EXAMPLES.json](STAGE_ADDRESS_EXAMPLES.json)、[NATIVE_EVENT_CARRIER_ROLES.json](NATIVE_EVENT_CARRIER_ROLES.json)、[indexes/historical_model_pair_carriers.all.jsonl.gz](indexes/historical_model_pair_carriers.all.jsonl.gz)：原阶段产物实例、3341载体hash分解（1763会话转录/1577计量桥接/1其他），以及全部已恢复历史raw/SSE原地址。", "",
        "物理盘点有11个WinError1920，均为临时venv/python或node_modules_*链接，逐项保留，未当作训练不合格。凭据/依赖/重解析目录不跨引用递归，SQLite物理普查仅stat；另一次独立生产目录核对采用只读SQL/query_only，无写入/checkpoint且DB/WAL前后stat不变。未干预当前并行消融。", "",
        "**目前可以明确归因于此前整理范围和导出处理问题；不能归因于‘大部分原始数据不适训’。** 这个普查建立了后续完整整理必须使用的入口。下一阶段须按实际角色和时间顺序恢复输入→原始响应/思考→工具操作→观测反馈→资源版本→评审修订→终态，并分别核真实原226血缘、去重、因果可见性及监督mask，才能给最终可训练条数/监督tokens。", "",
        "这轮没有重新承诺数据充分或效果必达，没有将32342响应位置直接叫32342合格训练样本；也没有把地址清单当成已经完成的全链路训练集。", "",
    ]
    (OUT / "RAW_DATA_LOCATIONS.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"report": str(OUT / "RAW_DATA_LOCATIONS.md"), "root_rows": len(roots), "skills": len(graph["skills"]), "representative_sessions": len(examples), "report_sha256": hashlib.sha256((OUT / "RAW_DATA_LOCATIONS.md").read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
