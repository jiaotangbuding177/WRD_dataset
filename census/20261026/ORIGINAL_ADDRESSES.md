# WRD 原始物理地址与文件普查

最后明确补充为历史 Codex 辅助修复目录：66 文件/1,162,823 字节；已定位目录地址并集为 175。另有一份精确外部原 session 文件，仅 stat 为 75,555,936 字节，未读取正文或扩扫 C 盘。两者分账见 [ASSISTED_REPAIR_SOURCE.json](/D:/skillloop/output/20261026_wrd_raw_census_v7/ASSISTED_REPAIR_SOURCE.json)，外部单文件不算另一个目录根。

后续独立反查再补 5 个生产/基础设施原根，全部存在，新增 2288 文件路径/79,705,856 字节，见 [FINAL_DISCOVERY_ROOTS.json](/D:/skillloop/output/20261026_wrd_raw_census_v7/FINAL_DISCOVERY_ROOTS.json)。连同下述基础账与 119 补根，已定位地址并集为 174，路径账为 794,156 文件/75,269,686,755 字节；仍不宣称内容去重、全部历史穷尽或可监督训练量。

**范围更正：下方 50 地址/72.63GB 是冻结的首批基础账，并未涵盖全部原制作数据。** 独立复核发现原目录规则偏重 `workflow*library`，漏了 D/E 的 v10—v35、早期 WRD/native/交接控制载体及临时根。现已另扫 119 根，新增 51,701 文件路径/2,561,362,264 字节；已知地址并集 169，基础账加补根为 791,868 路径/75,189,980,899 字节。旧子根重叠已剔除，未作内容去重，也不将文件数称为独立会话/训练量。完整补表：[ADDITIONAL_ORIGINAL_ROOTS.json](/D:/skillloop/output/20261026_wrd_raw_census_v7/ADDITIONAL_ORIGINAL_ROOTS.json)。D-v10 单独补表已包含在此 119 根中，不能再次相加。

本表从原 D/E 地址重新读取文件系统元数据。没有进行训练准入筛选，没有使用 106/91 作为入口，也没有运行模型或改动原实验。

本次列出 50 个原根/地址线索，其中 34 个不重叠根实际递归扫描；父根已覆盖的子根和正式评测目录只列地址。统计 740,167 条文件路径、72,628,618,635 字节。按卷号与文件 ID 只去掉 3 个硬链接等重复地址，得到 740,164 个物理文件身份、72,628,618,530 字节。**这是副本与缓存占用，不是独立训练语料量。** 内容去重和可监督量不在本轮判定。

原始企业语料入口：[有效轨迹.jsonl](/D:/skillloop/benchmark/enterprise_input_closed_v11_20261012/有效轨迹.jsonl)（55,556,390 字节，SHA 与原 inventory 声明一致）。1107 个会话的原绑定：[source_bindings.json](/D:/skillloop/output/20261021_workflow_skill_library/source_bindings.json)；分会话正文位于同根 sources/<conv>/conversation.json。

主控制与镜像：[D 盘 workflow_library](/D:/skillloop/output/workflow_library)；真实 native attempt：[E 盘 workflow_library](/E:/skillloop_runs/workflow_library)。九通道原 event_file 分散在 v10_reuse_iterations、parallel4/lane_1..3、recovery1/lane_4..7 及 workflow_library/channel8；不能只找 parallel4 一个目录。

| 原地址 | 用途身份 | 文件路径数 | 路径字节 |
|---|---|---:|---:|
| [E:\skillloop_runs\20261021_v10_reuse_iterations](/E:/skillloop_runs/20261021_v10_reuse_iterations) | original_provider_event_root | 82 | 13,816,868 |
| [E:\skillloop_runs\20261021_workflow_library_parallel4](/E:/skillloop_runs/20261021_workflow_library_parallel4) | historical_library_original_root | 128 | 314,124,344 |
| [E:\skillloop_runs\20261021_workflow_library_parallel4_recovery1](/E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1) | historical_library_original_root | 1,153 | 717,526,499 |
| [E:\skillloop_runs\20261021_workflow_library_v2](/E:/skillloop_runs/20261021_workflow_library_v2) | historical_library_original_root | 175 | 11,204,210 |
| [E:\skillloop_runs\20261021_workflow_skill_library](/E:/skillloop_runs/20261021_workflow_skill_library) | historical_library_original_root | 36 | 869,112 |
| [E:\skillloop_runs\w10](/E:/skillloop_runs/w10) | historical_library_original_root | 12,058 | 1,196,214,662 |
| [E:\skillloop_runs\w4](/E:/skillloop_runs/w4) | historical_library_original_root | 1,417 | 668,691,269 |
| [E:\skillloop_runs\w4_controls](/E:/skillloop_runs/w4_controls) | historical_library_original_root | 2,704 | 33,277,202 |
| [E:\skillloop_runs\w5](/E:/skillloop_runs/w5) | historical_library_original_root | 487 | 509,200 |
| [E:\skillloop_runs\w5_controls](/E:/skillloop_runs/w5_controls) | historical_library_original_root | 749 | 487,191 |
| [E:\skillloop_runs\w6](/E:/skillloop_runs/w6) | historical_library_original_root | 213 | 2,011,821 |
| [E:\skillloop_runs\w6_controls](/E:/skillloop_runs/w6_controls) | historical_library_original_root | 1,721 | 11,509,135 |
| [E:\skillloop_runs\w9](/E:/skillloop_runs/w9) | historical_library_original_root | 1,475 | 260,498,253 |
| [E:\skillloop_runs\workflow_library](/E:/skillloop_runs/workflow_library) | primary_native_runtime_root | 309,821 | 27,706,756,303 |
| [D:\skillloop\output\20261021_workflow_library_parallel4](/D:/skillloop/output/20261021_workflow_library_parallel4) | historical_library_original_root | 93 | 1,987,089 |
| [D:\skillloop\output\20261021_workflow_library_parallel4_recovery1](/D:/skillloop/output/20261021_workflow_library_parallel4_recovery1) | historical_library_original_root | 325 | 7,364,482 |
| [D:\skillloop\output\20261021_workflow_library_v10](/D:/skillloop/output/20261021_workflow_library_v10) | historical_library_original_root | 9,921 | 175,285,659 |
| [D:\skillloop\output\20261021_workflow_library_v2](/D:/skillloop/output/20261021_workflow_library_v2) | historical_library_original_root | 338 | 3,764,538 |
| [D:\skillloop\output\20261021_workflow_library_v4](/D:/skillloop/output/20261021_workflow_library_v4) | historical_library_original_root | 1,619 | 16,257,305 |
| [D:\skillloop\output\20261021_workflow_library_v7](/D:/skillloop/output/20261021_workflow_library_v7) | historical_library_original_root | 378 | 3,566,679 |
| [D:\skillloop\output\20261021_workflow_library_v8](/D:/skillloop/output/20261021_workflow_library_v8) | historical_library_original_root | 459 | 4,949,113 |
| [D:\skillloop\output\20261021_workflow_library_v9](/D:/skillloop/output/20261021_workflow_library_v9) | historical_library_original_root | 2,472 | 736,607,350 |
| [D:\skillloop\output\20261021_workflow_skill_library](/D:/skillloop/output/20261021_workflow_skill_library) | historical_library_original_root | 1,127 | 69,846,153 |
| [D:\skillloop\output\20261024_wrd12_library](/D:/skillloop/output/20261024_wrd12_library) | derived_category_library | 392 | 2,441,970 |
| [D:\skillloop\output\workflow_library](/D:/skillloop/output/workflow_library) | primary_library_control_and_mirrors | 389,780 | 40,497,632,317 |
| [E:\skillloop_runs\20261021_T0012_native_two_arm\observed_service](/E:/skillloop_runs/20261021_T0012_native_two_arm/observed_service) | shared_original_native_service_source | 1,027 | 154,283,846 |
| [D:\skillloop\output\20261024_evidence_inputs_closeout\original_request_restore](/D:/skillloop/output/20261024_evidence_inputs_closeout/original_request_restore) | original_referenced_episode_directory | 3 | 16,886,622 |
| [D:\skillloop\output\20261024_speed_audit\rule_decisions\44d48bf94838db40](/D:/skillloop/output/20261024_speed_audit/rule_decisions/44d48bf94838db40) | original_referenced_episode_directory | 2 | 13,962 |
| [D:\skillloop\output\20261024_speed_audit\rule_decisions\50e206fec0d86a65](/D:/skillloop/output/20261024_speed_audit/rule_decisions/50e206fec0d86a65) | original_referenced_episode_directory | 2 | 93,220 |
| [D:\skillloop\output\20261024_speed_audit\rule_decisions\95f867d47a057547](/D:/skillloop/output/20261024_speed_audit/rule_decisions/95f867d47a057547) | original_referenced_episode_directory | 2 | 16,321 |
| [D:\skillloop\output\20261024_speed_audit\rule_decisions\9946032b6e154a38](/D:/skillloop/output/20261024_speed_audit/rule_decisions/9946032b6e154a38) | original_referenced_episode_directory | 2 | 13,263 |
| [D:\skillloop\output\20261024_speed_audit\rule_decisions\a1268959874f42b6](/D:/skillloop/output/20261024_speed_audit/rule_decisions/a1268959874f42b6) | original_referenced_episode_directory | 2 | 35,696 |
| [D:\skillloop\output\20261024_speed_audit\rule_decisions\ae4e8801a37082d5](/D:/skillloop/output/20261024_speed_audit/rule_decisions/ae4e8801a37082d5) | original_referenced_episode_directory | 2 | 54,668 |
| [D:\skillloop\output\20261024_speed_audit\rule_decisions\d3c591932d2eb780](/D:/skillloop/output/20261024_speed_audit/rule_decisions/d3c591932d2eb780) | original_referenced_episode_directory | 2 | 22,313 |

表中的文件时间范围、扩展名与角色分类，见 [PHYSICAL_ROOTS.json](/D:/skillloop/output/20261026_wrd_raw_census_v7/PHYSICAL_ROOTS.json)。分类按透明的路径/文件名规则生成，不能代替消息血缘判断。

- [完整受控文件清单](/D:/skillloop/output/20261026_wrd_raw_census_v7/controlled/PHYSICAL_FILES.jsonl.gz)：每个原 source_path、文件 ID、大小、mtime/ctime、类型；不含正文。
- [原记录指向的地址](/D:/skillloop/output/20261026_wrd_raw_census_v7/controlled/ORIGINAL_PATH_REFERENCES.jsonl.gz)：从原 result/dispatch/service 元数据的实际路径引用发现，未从旧训练包倒推。
- [未递归的目录/重解析引用](/D:/skillloop/output/20261026_wrd_raw_census_v7/controlled/NONTRAVERSED_DIRECTORY_REFERENCES.jsonl.gz)：2922 个凭据/依赖目录与 2 个重解析引用，不跨引用递归。
- [九通道原服务统计](/D:/skillloop/output/20261026_wrd_raw_census_v7/NINE_CHANNEL_SERVICE_CENSUS.json)：原事件来源、请求去重及 SHA 单列；请求数不是 SFT 样本数。

另对 8 个后续正式评测/资源轻修分支做了独立 metadata stat：3466 文件、42,998,543 字节，见 [EVALUATION_BRANCH_ROOTS.json](/D:/skillloop/output/20261026_wrd_raw_census_v7/EVALUATION_BRANCH_ROOTS.json)。这部分不加入上述冻结主集总量，也不作为训练数据；没有因为训练隔离而禁止其地址/元数据普查。限定审计的 820 份原制作控制/反馈文件未观察到对这 8 根的直接路径名引用，此事实不证明全语义无因果。

本轮 11 个 WinError 1920 地址均为 venv-tts 的 python/lib64 或 node_modules_* 临时依赖链接，逐项保留在 PHYSICAL_ROOTS.json；没有把这些路径记作不适训。SQLite 仅 stat，没有打开；没有触碰原生容器、当前并行消融或凭据。完整扫描不测逐文件分配空间；较慢的部分 allocation 尝试另存 partial_allocated_attempt1，并明确不计入总量。首轮末尾读取 Windows 非符号链接 reparse target 的异常已保留，修正后完整 gzip 校验通过，并再走原根验证所有 path/size/file-ID 集合一致。

