# 09业务过程lane：真实原件、局部候选与未审范围

本lane恢复706其它业务owner＋615业务辅助owner，共1321个原始目标、343个完整原生context。每个target与旧账的sorted和insertion-order SHA都匹配；全文、工具参数、反馈、失败和未来片段按原消息序列保全。没有执行原程序、业务Agent、模型或训练。

`OWNER1321_EXACT_CONTENT.audit.jsonl.gz`与`ORIGINAL_CONTEXTS_343.audit.jsonl.gz`是实际正文；`INLINE_PROGRAM_INDEX.json`含27个从原exec heredoc精确截出的代码体，`inline_programs/`有实际源码；`packets/`为66个资源型目标的完整审读包。字面分类不等于语义信用，退出0不当业务正确。

已提交5个功能状态资源／修订候选和12个原可见过程说明候选，共17个、14来源。四份完整内联代码为36页本地截图、组织图、Excel和合同DOCX，另有真实HTML五处字母纠错；108个代码Unicode区间不给正loss。12份说明逐字保留原公开assistant文本，标为D正文，**不冒称内部思考R**；11个未证或错误片段不给正loss，包括财务源实际53条却称约70条、缺失附件无法比对内容一致、404无法证明账号权限、代码写出不证明逻辑正确等。原R与新R均新增0。

候选入口：`FUNCTIONAL_CANDIDATES05.jsonl.gz`、`VISIBLE_DECISION_CANDIDATES12.jsonl.gz`。均显式新作者状态、原输入非等价、银标0.25、root_main_admission=false且需外置根准入。`CANDIDATE17_STRUCTURAL_QA.json`只证明schema与精确排除范围结构，不代替资源运行、独立语义审查、tokenizer、mask及编译QA。根须完成后才可计入主集。没有任何KEEP或完整自主链准入。

`OWNER1321_DISPOSITION09.jsonl.gz`的互斥处理状态为：172新dev/test预留隔离、555字面read/ls仅作上下文、17局部候选待根QA、1原exec参数错误、576仍需深入语义审查。不能称全部1321已人工语义审完。615业务辅助的原始目标全部为read432／ls183；这不说明其读到的业务材料无价值。

保留集依据`holdout/holdout_reservation.json`按source及component检查，不回收预留来源进训练。简历DOCX与整合报告等有价值长程序因命中预留，已保全但未生成train标注。后续血缘扩张需根再次检查，旧reservation SHA只证明本lane当时的边界。

源码为research/data_prep/wrd_curation09/process_*.py。`RECOVERY_RECEIPT.json`及`LANE_SUMMARY09.json`记录输入与代码SHA。模型未加载、训练未开始、业务Teacher／Actor调用0；Codex整理与CPU成本UNKNOWN_NOT_ZERO。
