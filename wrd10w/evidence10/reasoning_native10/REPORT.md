# 原生兼容API原R、动作和反馈恢复（67个交换）

本子任务没有修改当前主集、编译结果或授予新增正loss；没有调用Teacher／Actor、模型、推理或训练。当前09基线595只用来去重，root后续真正准入的增量另计。新reserved `conv_34b56ae9c535`／组`v10_group_3e68bcc9a5055cb91951`不进入本批训练来源；所查5个episode均为现有TRAIN来源，整条前缀资源血缘不由本恢复自动批准。

## 实际找到的原件

identity整理的5个原生场中，A_screen_narrative_01、B_make_report_02、B_revision_report_01的原 `api_audit/request.raw.json`、`response.raw.sse`、receipt和原native session实体齐全。identity旧context的API计数0只是未接这份索引，不代表明文原R不存在。

| 原场 | API交换 | 原reasoning_content字符 | 当前595已批准字符并集 | 尚未正向监督字符 |
|---|---:|---:|---:|---:|
| A_screen_narrative_01 | 9 | 34473 | 8228 | 26245 |
| B_make_report_02 | 24 | 80567 | 11146 | 69421 |
| B_revision_report_01 | 34 | 46134 | 0 | 46134 |
| 合计 | 67 | 161174 | 19374 | 141800 |

这些是**原字段Unicode字符**，不是新增tokens、独立任务、67次底层付费推理或已准入数据量。仍只有现有3个业务source所构成的同一连接组；不增加独立来源。

所有67原API响应ID均在同场原native记录中找到唯一owner；65个还满足完整可见输出、工具JSON和call ID完全相同，原运行image／模型／backend与实际request/response/receipt字节SHA共同核对。另2个（Bmake14、Brevision25）同RID／工具ID／path，但native记录把代码中同一6字符变量替成了`***`；原API写入body与对应实际最终源文件均整字节相同。这2个作为明确记录例外另列，不静默归一化或宣称native字节全同。早期15不含这些例外。

已从全部原SSE按43461个reasoning_content字段帧重建161174字符，并核对每帧原字节边界／SHA及解码Unicode范围，不用usage或响应时间推断思考。该字段属于真实录制的**兼容API响应层**；bridge后SDK最终provider完整请求仍未捕获，不能据字段名保证它全是底层私有CoT。实际公开content与原R分别保全，原R中的短步骤宣告也不因字段名而自动得到高等级推理或业务效用信用。

## 去重、已知负例和未知分区

`R67_COMPLETE_CHARACTER_PARTITION.metadata.json`逐原响应进行完整、不重叠分区：

- 当前595已批准R：19374字符；由原call／response SHA、完整R字段SHA与实际approved_field_ranges精确连接。
- 旧银标正建议但未入当前主集：2799字符；仍须root复核，不能自动恢复旧未采纳建议。
- 旧明确mask0的负例或未知：890字符；保留原拒绝依据，不回授正loss。
- 其余未批准／未审：138111字符；完整原件保全、默认零loss，不能把恢复成功当语义正确。

四类之和161174。并集字符与精确token边界不同，不能由19374字符反算当前R监督tokens；非本67来源的已有历史原R、新作者R和其它native原R继续保持原银行，不因匹配不到本67而删除。

## 已立即交root审查的小包

`EARLY15_READ_LS_R_A_FEEDBACK.original.audit.jsonl.gz`包含A1—3、Bmake1—6、Brevision1—6的15个真实read／ls动作；其中6条有原R，共967字符，当前R覆盖均0。原R是局部计划、任务复述或步骤过渡，真实工具反馈确认实际读取；不据此授予skills质量、KEEP或完整自主信用。

该包保留完整原API messages／53工具schema、原response、native index／owner／RID、原件pins和独立反馈字段，后来的反馈没有放入较早输入。`EARLY15_READ_LS_SEMANTIC_REVIEW.json`提供小包原R正文和实际调用索引，root可逐条审查后做明确声明的core7投影；本子任务交付时训练准入仍0。原R全文、原A和错误等保全于完整 `API67_R_A_FEEDBACK.original.audit.jsonl.gz`。

## 真正旧根中仍未找到明文R的范围

另查E盘原repair1、repair2和此前不在34616账中的gen01真根的native／metering原件。native均无非空thinking／reasoning正文，meter只有native_start、usage、finish、done、stream_end事件及数值reasoning_tokens；metrics API调用列表为空。这些具体载体不足以恢复原R，数值token量不能合成思考文字，不推断全盘／整个历史从未存在R。其来源、原native和meter pins在 `REPAIR1_REPAIR2_GEN01_ORIGINAL_R_CARRIER_AUDIT.json`。

## 文件入口

- `API67_R_A_FEEDBACK.original.audit.jsonl.gz`：完整原R／同响应A／原请求及实际反馈。
- `API67_R_DEDUP_AND_UNSUPERVISED_INDEX.metadata.json`：67条逐字段去重与未授范围。
- `CURRENT595_R_COHORT_MATCHES.metadata.json`：已有监督view及canonical映射依据。
- `R67_COMPLETE_CHARACTER_PARTITION.metadata.json`：正／旧负或未知／未批准完整分区。
- `ORIGINAL_SSE_R_FIELD_FRAME_MAP.metadata.jsonl.gz`：43461个原字段帧及原字节范围。
- `EARLY15_READ_LS_R_A_FEEDBACK.original.audit.jsonl.gz`：root可直接独审的15份小包。
- `API_NATIVE_BODY_RECORDING_EXCEPTION.json`：2个native正文mask例外与实际文件字节证据。
- `RECOVERY_QA.json`、`FIELD_AND_CARRIER_QA.json`、`R67_PARTITION_SUMMARY.json`：实际数量与限制。

本报告表示原件恢复与逐字符授信账已完成，不表示141800字符已经语义全审、全部可训或能达到完整自主目标。root实际主集的语义批准、token mask与新增数量必须由其后续编译／独立QA报告给出。
