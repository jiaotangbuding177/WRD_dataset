# SDK原始消息捕获的独立证据补充

本文件是原5.0.39计划快照之外的事实增量，不改原计划、dispatch输入cipher或旧checkpoint。现存真实SDK generation消息恢复A的1/7与probe的2/6；13个request ID元数据全部核对。三份消息各包含16,112字符额外SDK system与真实user映射，原11个去headers投影/矩阵/代码证据文件全部在独立认证密文中。三份私有原trace及任何认证值均不入包。

最终provider HTTP body和最终tools仍为0/13已证，另外10次prompt不能复制首条或源码模板倒补。SDK结构消息捕获不等于最终wire完整性，也不保证学生core7投影与Teacher同输入；仍须后续相同学生服务条件下的闭环验证。这不是新增训练样本：active仍437序列／75248监督tokens／490原R，完整WRD主集未就绪，无新模型或训练。

在仓库根目录可用既有恢复工具，输出目录必须新建，key只指向原本地v4 key且不上传：

```powershell
python dataset/20261027_v10_checkpoint01/tooling/restore_checkpoint.py --cipher plans/20261027_v10_updates/controlled/wrd-v10-sdk-capture-evidence01.tar.gz.aesgcm --receipt plans/20261027_v10_updates/PROVIDER_CAPTURE_ENCRYPTION_RECEIPT.json --key <LOCAL_V4_KEY_PATH> --out <NEW_RESTORE_DIRECTORY>
```

不需要旧750对象；恢复只验证/写出13个成员，不执行归档脚本、保存的任务或训练。PROVIDER_CAPTURE_ARCHIVE_QA.json记录本地真实恢复与成员SHA验证，PROVIDER_CAPTURE_COVERAGE.json只公开覆盖统计，长system与业务输入没有明文公开。
