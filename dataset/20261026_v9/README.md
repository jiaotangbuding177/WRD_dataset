# WRD真实训练数据处理v9

[实际处理与训练计划](TRAINING_PLAN.md) · [实际数据量](FINAL_DATA_STATISTICS.json) · [训练文件清单](TRAINING_MANIFEST.json) · [独立数组QA](COMPILED_QA.json)

本次有实际正文、input_ids、loss spans和loader，不是候选清单。完整WRD制作/修订主监督仍被来源/结果标准阻塞；当前放行的是只读工具辅助和明确新增的协调标注，不能用总行数冒充完整自主任务。原226及新H继续隔离，未训练。

`controlled/wrd-causal-dataset-v9.tar.gz.aesgcm`包含全部恢复正文、原可读字段、工具/反馈/修订、版本-试跑-评审图、原件增量、实际SFT数组与分组；母本还包含隔离/未知资料，训练必须仅按TRAINING_MANIFEST加载sft文件。这里没有丢弃中间过程，也没有把它们全设为正loss。

沿用用户本地v4密钥（不在Git）。使用 `python tooling/restore_payload.py --cipher controlled/wrd-causal-dataset-v9.tar.gz.aesgcm --receipt ENCRYPTED_DELIVERY_REPORT.json --key <本地wrd-reasoning-v4.key> --out <新目录>` 认证解包。它只恢复文件，不执行训练或原保存代码。解包后以tooling/dataset_loader.py按显式span重建labels和weights。

867份原输入会话和112个真实附件绑定已准备；93个不同附件对象已在原仓库dist的12分片逐字节核验，按包内EXISTING_RESOURCE_REUSE引用。需要恢复真实附件时加 `--existing-release-root <仓库根>`；这样无需重复上传同字节418MB。原文/个人资料/可能含凭据的历史记录保持认证加密，密钥留本地。

源代码规则的LF文本hash与原CRLF字节hash分开记录，完整规则源码随包保留。协调规则trace是明确假设状态，不是实际工具反馈/试跑或原教师CoT；不替代原生Agent执行循环。旧v6原R与数组保持历史不同执行条件的引用，不自动混入当前主集。

[远端数据实体回读](DATA_COMMIT_REMOTE_VERIFICATION.json) · [独立实包核验](PACKAGE_INDEPENDENT_QA.json) · [实际解包与loader验证](RESTORE_AND_LOADER_QA.json)。这些收据针对数据提交c13d8e6；后续仅补交校验元数据，数据密文与训练数组未改。
