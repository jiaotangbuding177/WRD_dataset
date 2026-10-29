# WRD检查点05：真实过程训练数据与证据

实际主集529目标／146069监督tokens／3237312序列tokens；449≤16K，80在16—32K。436需求契约与93过程目标分账，过程来自12源／9联合component。相对04新增34目标／21617监督tokens，包含HTML过程、CV完整三脚本与SKILL、Excel模块构建和两种真实局修。

真实数据载荷是`controlled/wrd-v10-checkpoint05.tar.gz.aesgcm`：189578320字节、7250认证成员。包含完整消息、token数组、loss mask、必要状态文件、原思考／工具／反馈／错误／修订、真实资源与QA；不是候选清单。原226、新H及静态dev/test继续隔离。source/target作者、原逐HTTP思考／历史决策／累计摘录／新理由明确区分；互斥视图不重复计量。

恢复需本地原v4密钥（保存在用户本机，不上传Git）。CPU依赖复核版本：Python3.11、cryptography50.0.1、transformers4.57.6、tokenizers0.22.2、Jinja2 3.1.6、jsonschema4.26.0；不需要模型权重或Torch。Linux/Spark可用python3运行：

```sh
python3 tooling/restore_checkpoint.py --cipher controlled/wrd-v10-checkpoint05.tar.gz.aesgcm --receipt ENCRYPTED_DELIVERY_REPORT.json --key /secure/path/wrd-reasoning-v4.key --out /new/path/wrd05
python3 tooling/checkpoint_loader.py --root /new/path/wrd05 --assets /new/path/wrd05/tokenizer_assets --out /new/path/wrd05.loader_qa.json
python3 tooling/audit_restored_evidence.py --root /new/path/wrd05 --out /new/path/wrd05.evidence_qa.json
```

loader仅按主manifest读取19个实际分片，构建input_ids／attention_mask／labels／loss_weights；不会glob历史／条件／审计材料，不加载模型或启动训练。可从tokenizer_assets独立重渲染每条记录。native_material05中339原HTTP与460514思考字符、2554逻辑文件的2170个CAS实体均有实际字节和路径映射，全部C新增评审默认audit_only。EWI26原request／SSE和旧113旁支原件同时保全。

[具体训练方案](TRAINING_PLAN.md)按14B主、8B对照，给出BF16 LoRA、分阶段52次主更新／最多100次、损失与曝光日程、Spark长窗验收及每合格技能总成本。日程在认证包quality_current/OWNER_EXPOSURE_SCHEDULE.json；不是启动配置。当前完整自主A—D示范0、合格保留0、独立dev/test数组0，完整训练NOT_READY；不能保证理想模型已具足量数据。

已实际认证还原、529行两tokenizer／mask／loader及339原响应重解析PASS，详见CHECKPOINT_QA和ROOT_RESTORED_*收据。费用范围20outer／21native、22156371known tokens／286身份／3unknown，不是全项目成本；AI／CPU／现金UNKNOWN_NOT_ZERO，合格分母0则单位成本未定义。处理源码缺失与原数据缺失分账；5.0.43双设计及精确恢复记录在包中。

[母体与差额对账](RAW_POPULATION_RECONCILIATION.md)中的405前缀已在本包冻结后完成逐字节普查，追加实体、脚本和报告见`../../assessment/20261029_maker405_audit/README.md`。结果只说明这405个早期前缀未创建程序，不外推1763会话或29技能。9096缺证目标和其它跨机制恢复仍继续，未审不说无价值。
