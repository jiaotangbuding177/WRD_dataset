# WRD检查点07：真实恢复数据、状态标签与训练方案

2026-10-30。当前实际主集 **552目标、150674监督tokens、3300896输入tokens**，472≤16K／80在16–32K。所有552行均直接双tokenizer、mask、来源、owner及loader核验通过。436契约与116过程分报；完整自主训练仍未就绪，没有启动训练。

本轮实际处理100个maker会话的969待核位置；原1050中另81已证保护位置继续隔离。最终854／1050有保护祖先、196具体缺证。恢复的原native、目标正文、工具、反馈、资源版本与裁定均在真实认证载荷，不能把审计恢复数量算作训练量。[详细结果与缺口](RECOVERY_REPORT.md)。

新增22训练目标／3675监督tokens：19个新作者状态判断（961R＋2636决策正文）与3个读取保护资源前的新状态动作投影（78A）。新增原CoT、完整程序、已证修复、合格KEEP和单native自主链均0。不是22条完整成功沉淀；不能保证这份数据已经足够达到完整自主目标。[训练配置和可证伪因果链](TRAINING_PLAN.md)。

## 实际还原与加载

沿用用户现有本地v4密钥，密钥不在Git。先按[检查点05](../20261029_v10_checkpoint05/README.md)还原，再按[检查点06](../20261029_v10_checkpoint06/README.md)合并得到 `wrd06`。在本目录执行：

```sh
python3 tooling/merge_delta.py --base /path/wrd06 --cipher controlled/wrd-v10-delta07.tar.gz.aesgcm --receipt ENCRYPTED_DELIVERY_REPORT.json --key /secure/path/wrd-reasoning-v4.key --delta-out /new/path/delta07 --out /new/path/wrd07
python3 tooling/checkpoint_loader.py --root /new/path/wrd07 --assets /new/path/wrd07/tokenizer_assets --out /new/path/wrd07.qa.json
python3 /new/path/wrd07/canonical_arrays07/binary_loader.py --root /new/path/wrd07
```

输出必须是新目录；07核前一merged06认证清单和530训练清单的SHA，逐文件认证、保存被替换旧版本，再合并。训练仅消费 `TRAINING_MANIFEST.json.actual_train_files`。audit、旧draft、旧数组、条件长窗和原保护正文均不可通配加入训练。载荷保全原件与修订记录，除新22目标的66个数组原件，还提供覆盖全部552行的canonical数组入口：1656个真实小端数组、52814336字节。旧49行147个源银行binary_arrays引用只作legacy；读取当前可迁移数组应使用canonical索引与标准库读取器，不能跟随旧字段。

07增量实体为30210262字节，3127认证成员；公开校验数、密文和载荷manifest SHA见[认证收据](ENCRYPTED_DELIVERY_REPORT.json)。本地合并根和全部552行的实际还原核验、远端冷LFS实体验证另列回执；仅有LFS指针或Git push不能替代这些检查。

14B主／8B对照的未运行组件预算随实际数据重算为57更新、最多115更新；完整dev/test数组仍0，Spark ARM64／GB10、长窗和梯度实现待验，默认完整训练入口null。原226／H12／静态及资源祖先隔离；AI标注和CPU整理成本已发生、完整用量未知且非零。

远端实物核验已通过：[23个普通Git文件与30.21MB实体的收据](REMOTE_CHECKPOINT07_VERIFICATION.json)。上传由Git LFS完成；其下载客户端多次断连后，校验使用指定commit的GitHub媒体端HTTP206独立取全，完整大小及SHA与远端LFS指针完全一致。没有用本地密文冒充下载结果。补充[各阶段覆盖](STAGE_COVERAGE.md)区分实际执行与新标签。
