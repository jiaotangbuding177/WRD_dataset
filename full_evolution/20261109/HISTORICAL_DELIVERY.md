# 全量演化集与历史WRD管道的实际投递血缘

本报告只读追溯既有记录，没有启动、停止或改变任何模型/管道/在途任务。原文件与投递条件以同目录 `LINEAGE_EVIDENCE.json` 的SHA为准。

## 全量来源在哪里

根 `pipeline.json` 的 `source_bindings` 指向 `output/20261021_workflow_skill_library/source_bindings.json`，包含1107来源。其 `source_freeze.json` 固定母本 `benchmark/enterprise_input_closed_v11_20261012/有效轨迹.jsonl`，55,556,390字节、SHA256 `877de9787229069946da0fc58dff2dfbc7af46aaa6f1aeb120accf266ee1e901`。

逐源实核：`output/20261021_workflow_skill_library/sources/<source_id>/conversation.json` 的1107个JSON对象全部等于母本对应行，合计22070条清洗消息，保留用户与历史助手。母本另保留原用户需求、别名及配对投影信息。

`benchmark/enterprise_input_closed_v11_20261012/sources/<source_id>.json` 是更早原始审计导出副本，含跨导出重复/别名及不同元数据，并不等于清洗投影。例conv_497a2363eddb：清洗会话26条，原始审计58条。完整包应保全两者，模型默认使用清洗母本，不将别名重复当新会话/新训练经验。

12类来源数：OFFICE208、BIZ191、EDU176、LEGAL139、HR122、COMM44、TECH43、KNOW43、NEWS41、ASSIST36、LIFE33、DATA31。原contracts为881 evolution＋226 evaluation；全量存档不改变学生的原226隔离。

## 当时怎样给pipeline

1. `pipeline.py`读取完整1107 bindings，按原队列调用 `research/workflow/stages.py` 的screen、make、prepare、actor、review。当前 `pipeline.json` 含精选6路线续接范围，不等于仅有6个输入来源。
2. `stages._source_inputs`把完整会话挂到 `inputs/conversations/<source_id>.json`；`inputs/sources.json`只作短索引/预览，完整会话仍在。材料按 `inputs/materials/<source_id>/<序号>_<文件名>` 挂载。
3. make收到所选路线的学习来源、附件、已有可复用资源、实际旧技能/反馈和历次制作记录。它是原生OpenClaw制作任务，不是宿主替模型写技能。
4. prepare通过 `recall.build_catalog`获得全1107的逐用户请求JSONL、逐源全文和材料索引，模型从真实需求整理试用委托；Actor只收到最终选择的本来源输入。试用任务不是原250正式测试，也不全是逐字原委托。
5. 无技能/技能两组原生执行后，review读取真实交付、用量、版本与制作证据，决定保留、修订或停止。技能写在 `output/workflow_library/skills/<route>/`。

**已发现的历史限制：** 旧bindings共有8058条资源关联，但只有122条 `eligible_real_input=True`；`recall.source_materials`会直接跳过其余项，包括已存在的重建材料。这解释了为何不能直接复制旧bindings，就声称全量附件已经投递。旧规则强调认证原件，不能静默拿它覆盖用户已授权的重建输入政策。

## 29skills是什么记录

`output/workflow_library/status.json`的2026-10-24 22:28终态：1107已初筛，121路线/121已生成包中，29 retained、60 candidate、19 rejected、13 needs_revision。文件目录121不等于121成功。

`actual_pipeline_explanation_20261024/任务来源核对.json`及同日研究记忆保留29保留路线49开发试用记录；4记录/3技能的实际制作来源与试用来源重合。其余45仅源ID未重合，不能把历史29全部说成严格独立盲测。旧成功/失败/费用都应留档，不能把29个最终技能当作新实验输入答案。

## 现在可复用的完整材料投递版本

11月7日全1107官方基线已从同一v11母本构建 `output/20261107_official_baselines_1107/data/SOURCE_INDEX.json` 和 `data/cases/evo_<source_id>.json`。这些public cases是完整人类多轮委托＋文件投递时点，不包含历史助手答案，故不能取代上面的完整历史会话。

现有活动合同还叠加 `recovery/input_semantic_overlay_20261108/PUBLIC_CASE_OVERLAY_v2.json` 的6来源修订。应先核base_case_sha及overlay SHA，再整对象替换对应public case；不影响其余1101来源。

本轮对该合并版本逐项只读统计：1107来源、5567人类轮次、最长162轮；769来源有资源、8231次资源投递关联（初始6915／后轮1316），3591唯一路径，缺实物0。资源标注synthetic=True2087关联、False5018、未指定1126；全部保留原字段，不升级为原件认证。具体素材用途正确性需要和实物/任务审核分开。

保留每项 `path/mount/user_index/sha256/synthetic/provenance`。原mount包括`对话附件/`和`inputs/`，不能统一改名后让原正文引用失效。业务连续重放时仅user_index0初始可见，后轮通过turn_resources按轮投递；制作学习可以按需读取已完成历史的全资源，但必须保留时序与来源，不能将本次待生成答案或历史产物冒充初始附件。

本轮所称“可复用完整材料版本”只复用已完成的数据对齐/重建及原生输入适配，不引入MetaClaw/EvoSkill/SkillOpt算法、其训练身份或评分答案。尤其其all1107训练标签是该并行基线合同，不能解除本学生原226和冻结DEV/TEST隔离。

## 仍需在新包明确的条件

- 原始、清洗、重建和运行输入分视图保全，不丢历史思考/助手响应，也不把原始重复投影算新增经验。
- 物理存在与可打开不是语义适用性和真实原件恢复认证；保留全部重建来源与未知项。
- 某些需求依赖邮箱、飞书、IMA、Gitee模拟或远端服务。旧运行环境的认证/OAuth状态不是可公开打包的材料，另列服务前提，不能放凭据或把未恢复外部能力算模型失败。
- 不默认恢复旧pipeline、当前官方基线、模型训练或任何全量生成。新实验执行以用户后续授权及新冻结任务清单为准。

证据同时包括10月8文件修复、10月9完整环境对齐、10月23原管道五处漏接修复、10月24真实试用来源核对记忆及当前源码pin；详见 `LINEAGE_EVIDENCE.json`。
