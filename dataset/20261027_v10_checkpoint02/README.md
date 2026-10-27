# WRD v10 中间检查点02：完整主训练集 NOT_READY

本包实际包含3个活跃数组、77,500监督tokens及完整原思考恢复记录和审核证据：437序列、267来源、255联合来源component，420序列≤16K、17序列在16—32K。唯一活跃银行为source_events_02和native_A_partial_03。这里的主数据是获批语义子任务；B/C/结果挂钩资源修订/D和完整原生自主控制仍缺，不能据此宣称足量或保证自主沉淀。

R03替代旧A02：同一真实原响应的正监督由490增至2,742原R tokens，新增2,252；独立任务、来源和序列数均未增加。原33,083字符R完整保留，16个批准范围共8,228字符，过宽停止条件精确撤出；其余思考、正文和工具动作零loss。统一multiplier0.25，AI银标、非人类gold，不证明候选已实现或实际收益成立。Codex标注成本为UNKNOWN_NOT_ZERO。未加载权重、未启动训练。

恢复：安装CPU cryptography，然后执行 `python tooling/restore_checkpoint.py --cipher controlled/wrd-v10-checkpoint02.tar.gz.aesgcm --receipt ENCRYPTED_DELIVERY_REPORT.json --key <本地既有v4密钥> --out <全新目录>`。密钥不在Git。认证及成员SHA核验后，执行 `python tooling/checkpoint_loader.py --root <恢复目录>`，会复原437序列/77,500个非-100 labels和相应loss_weights。加载器只使用本包manifest指定的3个数组，不会训练模型。

未变的原需求标注输入及A九次HTTP原始请求、响应、工具观察、资源血缘已在检查点01，按EXTERNAL_EVIDENCE_REFERENCES.json逐文件SHA引用，避免再次复制整个原始库。若要重现审查证据，把检查点01恢复到另一个目录；勿把其旧manifest或旧A02银行合并进本包。数组已自含训练所需messages/tools；绝对原证据路径仅为历史引用，恢复别名另见cipher中的EVIDENCE_PATH_ALIASES.json。

中断B01的6个兼容API原请求/响应/收据、原生恢复事件、已知费用和原R片段另存cipher的audit_only；第6响应缺DONE、原receipt为FORWARDING，不伪造完整响应或成功，全部0新增正loss。新B02重试仍未独立验收，其持续写入数据不纳入本冻结包。训练加载器不会读取audit_only。

本包附当前TRAINING_PLAN；前次已核验方案在同仓库plans/20261027_v10_updates。REMOTE_PLAN_UPDATES_VERIFICATION.json记录该次独立远端回读，不能代替本检查点的后续远端核验。所有原226、新H及静态dev/test边界继续隔离。
