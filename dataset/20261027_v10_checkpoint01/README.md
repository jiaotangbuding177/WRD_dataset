# WRD v10：中间检查点01，完整主训练集 NOT_READY

这份包有真实正文、原R、原生工具反馈、显式loss数组和可用恢复器，尚未完成完整WRD训练集。当前唯一入口为TRAINING_MANIFEST：437序列、75248监督tokens，其中490原R tokens；267来源/255联合component。B已获授权但资源尚未派发，B/C/真实修订/D/自主控制链仍缺；未训练、未加载权重。

active仅source_events_02与native_A_partial_02。旧431/144084、旧645R及v9辅助不混入。原始中间记录与被撤的旧partial留在认证cipher的audit_only，保全不等于正loss。原226、新H与静态dev/test继续隔离。26旧Actor任务已逐项接通，23确定保护祖先、3具体缺证；v9 21序列/36目标/1260监督tokens有显式未来导入撤销清单，旧包未静默改写。

恢复：安装CPU cryptography，执行 `python tooling/restore_checkpoint.py --cipher controlled/wrd-v10-checkpoint01.tar.gz.aesgcm --receipt ENCRYPTED_DELIVERY_REPORT.json --key <本地既有v4密钥> --out <新目录>`。密钥从未上传。认证成功后逐成员SHA/大小核对，原文件不执行。再执行 `python tooling/checkpoint_loader.py --root <恢复目录>`，只读取manifest指定的3个active分片，复原labels/weights，不启动训练。父工具与证据里的绝对原路径保留原字节，PAYLOAD_MANIFEST与EVIDENCE_PATH_ALIASES提供归档别名，不能直接按原Windows路径在Spark执行。

694原会话及附件相关750对象/117118540字节已在本仓库历史dist的12分片，完整EXISTING_SOURCE_REUSE随cipher交付，未重复上传旧对象。恢复时可加 `--existing-release-root <仓库根>`，流式逐SHA取回这些既有对象。新增7份原记录已按同字节恢复入本cipher。

原A的9个兼容HTTP请求与7个实际付费模型调用分别保全；用量570932 tokens，不能把HTTP兼容记录当付费调用数。原53工具请求与核心7工具学生投影覆盖另列。部分原R通过了精确范围和原SSE校验，其余错误/未知R与动作保持loss0；这不证明A整阶段或自主pipeline成功。详见TRAINING_PLAN、CHECKPOINT_STATUS和CHECKPOINT_QA。
