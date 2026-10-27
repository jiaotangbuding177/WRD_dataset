# WRD v10 检查点03：完整主集仍 NOT_READY

本包交付实际可恢复的默认训练数组及其原始推理、工具操作、观察、失败、修订、版本、独立试跑与评审证据。默认数量以TRAINING_MANIFEST和ACTUAL_DATA_STATISTICS为准，不能把158次HTTP、272486原思考字符或所有audit文件数量当正监督量。原226、新H和静态dev/test继续隔离，旧v9辅助不会自动混入。

首次有界链共有10 outer阶段、11原生sessions、147兼容HTTP，其中145完整、2部分响应；实际110上游身份、8660547已知tokens及1个未知usage。现金和AI整理费用UNKNOWN_NOT_ZERO。两例技能消费比无技能更贵，原决策STOP，0个合格留存技能，每合格技能总成本因此未定义。保全负结果不等于批准全部原R/动作；局修仅授原21＋独立8所支持的局部信用，新状态理由与原Teacher R分别标记。训练尚未开始。

已完成A2筛查另作为audit_only第11 outer阶段保全：11完整HTTP、37441原R字符，1134348已知tokens、11实际请求身份，0新增正监督。其错误quote ID、错误归并或无依据的半页上限判断均不因completed被授信用。合计11 outer／12 native／158 HTTP（156完整＋2部分）、272486原R字符，9794895已知tokens／121请求身份／1未知usage；首10链的旧原报告与费用不回写。A2的36 SQLite事件／22 message／1 session与55 provider meter行分开统计，不能互换。

恢复：安装CPU cryptography，执行 `python tooling/restore_checkpoint.py --cipher controlled/wrd-v10-checkpoint03.tar.gz.aesgcm --receipt ENCRYPTED_DELIVERY_REPORT.json --key <本地既有v4密钥> --out <新目录>`，随后执行 `python tooling/checkpoint_loader.py --root <恢复目录> --verify-conditional --verify-evidence`。恢复先认证密文并逐成员SHA，loader只按主manifest指定路径重建labels/weights，验证外置root准入与真实owner唯一，不加载模型或训练；证据全量统计与条件64K另行核查，不增加默认训练量。

conditional/native_context_64k_01另有6个full53候选、5980原R tokens和18个二进制数组，非默认ACTIVE，不能与core32同owner重复曝光。其111请求窗口统计不包含后续终评或A2，不是全部158请求的覆盖率；Spark未前向或训练。原冻结manifest65文件中的3个pyc只保存SHA/size元数据，不发布为训练资源；失败CPU尝试也是审计记录，不能glob训练。完整原生53工具与core7学生投影、训练序列长度与服务总窗口在方案中分别解释。

历史checkpoint01/02、old750对象/12dist和producer公开勘误只按精确SHA引用，不覆盖或重复整个旧库。source_tooling提供复现源码；EVIDENCE_PATH_ALIASES说明原绝对证据路径与归档路径的关系。不要递归扫描旧银行或条件目录作为训练入口。该交付是经过审阅的主子任务检查点，仍须扩充更多真实机制与完整自主调度证据，不能据此保证达到目标模型能力。
