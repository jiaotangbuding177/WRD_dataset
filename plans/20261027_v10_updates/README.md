# WRD v10方案更新与真实输入扩展

这是5.0.39／ALG-20261027-03的方案与输入交付，不是新增训练集，也不是完整工作完成声明。原checkpoint01的437序列／75248监督tokens／490原R tokens不变；本次0新增positive、0模型调用、0任务执行。旧checkpoint manifest和cipher未修改；仓库root入口由主管单独更新。

MODEL_INPUT_OUTPUT是外置接口说明，不作为训练样本。PROVIDER_CAPTURE_COVERAGE及独立SDK证据包补齐13个底层request身份的实际查找矩阵：只找到A1/7、probe2/6的真实SDK结构消息；最终provider HTTP正文／tools仍0/13已证，不能称完整恢复。私有原trace与headers不上传，实际可恢复的投影随认证cipher交付。

SOURCE_ANCESTRY_POST_AUDIT复核169处已引用观察，区分真实任务请求／背景与公共语言／人设模板；23保护／3具体缺证结论不变，30个直接title来源及5个最小语义复核有独立AI证据（非human gold）。它只证明实际送达片段，不宣称整原source被看过；没有新增准入或训练量。

COST_ACCOUNTING_SCOPE说明“0新增调用”仅指本增量没有新增原生Teacher／业务采集，并非AI整理免费。已知原生probe+A为13次／816925 tokens；Codex整理与AI审核已发生，但其逐次tokens／金额当前未导出，记UNKNOWN_NOT_ZERO，不能遗漏后冒充全成本。

TRAINING_PLAN、COVERAGE_EXPANSION、CONTROLLER_VIEW_PROPOSAL为当前本地方案的逐字副本。RESEARCH_PLAN_REVIEW_02保留其独立审读5.0.38时的输入SHA，不反写为5.0.39；IMPLEMENTATION_RECORD按其记录逐项核验，结果在SOURCE_RECORD_CHECK，原件没有擅改。REMOTE_CHECKPOINT01_VERIFICATION保留root提交a10b054完整身份、普通blob与独立冷缓存LFS实体回读全部字段。

historical_snapshot/CAPTURE_SCOPE_CLARIFICATION_20261026_174242.{md,json}是2026-10-26 17:42:42 UTC、5.0.38刷新前的历史时点原件，文件名及本说明明确其时点。其中B waiter状态不代表当前状态。其关于兼容API捕获边界、底层最终SDK prompt字节未取得、core7为蒸馏投影的范围说明仍需结合最新5.0.39计划阅读，不能声称同输入faithfulness已经证明。

MODEL_CONTEXT_REQUIREMENTS与model_metadata三份JSON是独立事实补充，不改写已复制的TRAINING_PLAN。两冻结revision配置均为max_position_embeddings=40960、rope_scaling=null；64K／128K不能当开箱可用。本次未下载权重、未启用YaRN、未修改当前16K／32K参数或扩大执行授权。

认证输入包实际含冻结dispatch_release_02的58个case和23个cohort所需原文、81个替代job、source/material receipts、manifest和QA。case与cohort是替代组织方式，不是应全部执行的81场队列。58来源群、23机制是输入准备范围；40条C输入就绪、18条仍缺件，不是已验证skills或业务成功数。包括一个明确标记的旧过程草稿输入，不作为答案gold。

10件实际材料／40,903,999字节均逐SHA命中已在Git旧12分片中的750对象，本cipher只携映射，没有重复上传这些二进制。已用已有checkpoint的portable恢复器真实认证解包、从旧分片取回10对象，并恢复全部冻结成员逐SHA核验；不会执行保存的job。

在仓库根运行：

`python dataset/20261027_v10_checkpoint01/tooling/restore_checkpoint.py --cipher plans/20261027_v10_updates/controlled/wrd-v10-dispatch02-inputs.tar.gz.aesgcm --receipt plans/20261027_v10_updates/INPUT_EXTENSION_ENCRYPTION_RECEIPT.json --key <本地既有v4密钥> --out <新恢复目录> --existing-release-root <仓库根>`

然后：`python plans/20261027_v10_updates/tooling/materialize_dispatch_resources.py --root <新恢复目录>`。

需本地已有cryptography及旧dist实分片；密钥不在Git。冻结原job和receipt字节含原宿主路径，恢复器不改写它们。RESTORED_RESOURCE_PATHS提供实际恢复位置映射，供后续另行准备新宿主输入；不能直接把旧Windows路径当Spark可执行配置。恢复和材料化仅是文件操作，不授权派发、训练或外部业务副作用。
