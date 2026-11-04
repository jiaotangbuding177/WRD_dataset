# WRD 最终 SFT 入口

先检查上一级 FINAL_ADMISSION.json 的 status=PASS、release_ready=true，再读取 admission.jsonl.gz 中 final_admitted=true 的 ID。编译候选上的 training_eligible 是编译前标记，不能作为最终入口。

- 16K：只使用 common16k.jsonl.gz。
- 32K：使用 common16k.jsonl.gz 与 common32k_long_only.jsonl.gz 的并集，两文件 ID 互斥，不重复曝光。
- 大于32K、未审、拒绝、隐私hold或编译/mask失败的样本均不在这两个SFT文件中。

文件保留 input_ids、supervision_spans 与 label_ignore_index=-100，未重新分词、未裁剪。重建labels：

```python
labels = [-100] * len(row["input_ids"])
for begin, end in row["supervision_spans"]:
    labels[begin:end] = row["input_ids"][begin:end]
```

本轮未启动训练。所有语义审核是AI局部证据银标，人工gold为0；不代表独立测试通过或Spark训练性能已实测。
