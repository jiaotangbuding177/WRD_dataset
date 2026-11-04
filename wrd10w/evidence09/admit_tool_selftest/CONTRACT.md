# admit09：冻结后接线合同

工具位置：research/data_prep/wrd_curation09/admit09.py。当前只运行了本目录synthetic fixture，未对真实DATA执行stage或activate。run01保留早期19项；run02为最终21项验证。不会训练、加载权重、运行业务Agent或改设计Markdown。

根freeze JSON的最小结构如下。所有path建议用绝对路径，sha256必须为实际文件SHA。工具自身SHA填写最终版本；不把下面占位符当作可执行freeze。

```json
{
  "status": "ROOT_FROZEN_CURATION09_STAGE_AUTHORIZATION",
  "admit09_script_sha256": "ACTUAL_TOOL_SHA256",
  "baseline_manifest_sha256": "cbb233f2a44bcb61035e4fcb046830178510529cb149cf3ea6100c613babe555",
  "revocations": {"path": "ABSOLUTE_CLOSURE_JSON", "sha256": "ACTUAL_SHA256"},
  "new_compilation_report": {"path": "ABSOLUTE_COMPILED02_REPORT", "sha256": "ACTUAL_SHA256"},
  "root_semantic_acceptance": {"path": "ABSOLUTE_ROOT_ACCEPTANCE", "sha256": "ACTUAL_SHA256"},
  "independent_token_qa": {"path": "ABSOLUTE_TOKEN_QA", "sha256": "ACTUAL_SHA256"},
  "independent_protection_qa": {"path": "ABSOLUTE_PROTECTION_QA", "sha256": "ACTUAL_SHA256"},
  "new_candidate_prefix_scan": {"path": "ABSOLUTE_REAL_PREFIX_SCAN", "sha256": "ACTUAL_SHA256"},
  "new_allowed_record_ids": ["EXPLICIT_NEW_RECORD_IDS"],
  "new_revoked_record_ids": [],
  "new_bank_relative": "compiled/curation09_process_01",
  "expected_rebased_counts": {"targets":546,"supervised_tokens":162835,"input_tokens":3258561},
  "expected_final_counts": {"targets":578,"supervised_tokens":205154,"input_tokens":3420959}
}
```

正式closure可保持原字节及READY_FOR_ROOT_REBASE_REVIEW_MAIN_NOT_MODIFIED状态。工具在root freeze授权下，使用main_manifest_pin、revoke_current_view_ids、revoke_source_ids、revoke_source_scope_component_ids映射；不改独立报告。new allowed/revoked必须互斥且完整覆盖本次compiled bank全部ID。root_semantic_acceptance要求status以ADMIT_开头，record_ids精确等于allowed，compilation_report_sha256绑定原32报告。独立token QA要求PASS状态。两个保护证据pin若提供也逐SHA核实。

stage操作新建manifest_staging09、受影响bank的compiled/curation09_rebase_*、过滤后的新bank及canonical_arrays09。未受影响的分片与引用字典保持不变；重基线保留行的未压缩JSON行逐字复制，token/messages/metadata不重编不改值。新rebase receipt只含clean子集并引用旧bank／旧admission和当前撤销依据。新bank也按root显式allowed筛选，不能隐式收录未通过的新样本。

工具先独立重算旧主账，要求actual_counts与12项原监督来源tokens账完全一致，随后按实际保留行重算计数、阶段、逻辑bank、来源DSU、owner/call、原R／新R／可见D／原A／投影A。未能归类的来源类型立即停止。新tokenizer调用为0，重基线report明确其tokenizer proof来自逐字保留旧行的历史验证，不冒称本次重新调用。实际新32的双tokenizer QA仍由其已有独立回执支持。

canonical_arrays09为最终全部n行各生成input_ids uint32LE、labels int64LE、loss_weights float32LE共3n个实体。ARRAY_INDEX09绑定未来主manifest精确SHA、逐行原shard位置、ID、跨度SHA与每bin尺寸／SHA／dtype。binary_loader09.py默认只认当前TRAINING_MANIFEST.json，忽略全部legacy row.binary_arrays；stage QA显式使用同SHA的manifest_staging09/TRAINING_MANIFEST09.json。四features逐行核对，返回原权重Python精确值，二进制float32仅按正确舍入核实。

stage不会替换主manifest、statistics或任何旧shard。根审查stage输出后，另行显式activate命令并传精确staged manifest SHA；工具再次核所有canonical数组，再保存旧manifest/statistics快照，statistics先写、manifest最后作为入口切换。操作不是训练启动配置，full_WRD_main_training_ready恒为false，完整主入口null。最终保护别名审查与真实交付仍由根负责。

21项synthetic验证覆盖：旧文件不变、未影响引用不变、旧／新撤销过滤、保留行原值不变、clean子集收据、3n数组及四features、legacy路径忽略、未激活默认loader拒绝、改坏label后即使重算文件／index pin仍拒绝、显式激活和旧快照、重复／未知撤销ID、保护新样本误准入、freeze SHA错、路径逃逸、正式closure字段映射，以及冻结预期数量不符时在写入前拒绝。测试不代表真实数据已准入。
