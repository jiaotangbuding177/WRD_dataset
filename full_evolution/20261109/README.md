# 全量演化集与真实skills制作

本目录已包含1107来源的完整会话、全部现有资源实物、时序映射、历史投递记录和新的原生制作执行入口。

先读 [PLAN.md](PLAN.md)，再按其中命令恢复：

```bash
python3 tooling/restore_corpus58.py --delivery DELIVERY.json --out corpus
```

54个实际二进制分卷，共900092964字节，无AES密钥依赖。恢复后9983文件/1366771398字节，逐成员SHA验证。原226继续隔离。本次新效果实验12来源：10制作+2正确STOP，四臂0/241；首3真实制作完成内容审核后再继续。

[历史怎样投递](HISTORICAL_DELIVERY.md) · [执行命令](execution/EXECUTION_README.md) · [实际清单](MANIFEST.json) · [执行数据冻结](EFFECT_FREEZE12.json)。

只交付准备，不启动模型或训练；实际技能需由同事按新入口运行产生。旧已完成的mini和26/填充测试不重跑。
