# next51 旧记录缺口复核与有界整理建议

本文件只规划下一轮。未新增语义标注、正例、token 编译、资源执行或模型调用，未修改09主清单，也未启动训练。当前冻结09仍是595个目标、216154个正tokens；SOURCE-ID闭合不等于语义正确，新功能state不洗原prefix或代码/资源祖先。

## 以最终09 overlay重算旧8376

输入为 `output/20261031_wrd_curation09/process/batch02/coverage_overlay/CURRENT34616_OWNER_COVERAGE09_FINAL_OVERLAY.jsonl.gz`，不是旧569覆盖率。互斥优先级为新protected→reserved→已current scoped-view关联→未关联条件prefix。

| 历史队列 | 旧owner数 | 新protected | reserved（扣除protected） | 已关联current scoped-view | 未关联条件prefix |
|---|---:|---:|---:|---:|---:|
| 其它祖先待闭合 | 6076 | 111 | 835 | 4 | 5126 |
| 补录prefix | 2173 | 0 | 0 | 55 | 2118 |
| 当前source身份缺失 | 56 | 0 | 0 | 0 | 56 |
| 方法相近但producer受保护 | 63 | 6 | 5 | 0 | 52 |
| 特定缺证 | 8 | 0 | 0 | 3 | 5 |
| 合计 | 8376 | 117 | 840 | 62 | 7357 |

两个隔离flag原始计数117与886，交集46，隔离并集957。7357是条件prefix工作单位，绝非7357条可训练样本；其中52条仍属受保护producer方法族，不能改称干净余量。62个已有scoped-view关联也不代表其完整prefix、原R、原A被授正：后续只能对未授信的不重叠范围记账。

56条身份缺失实际只涉及 `conv_69ee59997792` 一个source、4个episode，均为actor、ai-news-digest路线，不能当56个独立source。补录2173涉及102个episode，overlay中的source_ids全部为空，native_readable_R_blocks均为0；后者只表示本索引未记录可读R块，不能推断provider/SSE没有原思考。首务是恢复真实身份与父资源，不是直接标注2173段思考。

## 35条历史版本/试跑/评语边的可用范围

只检查 `output/20261030_wrd_gap08/lineage/` 下既有edge、完整package、producer strict boundary元数据，未读取protected thought、Q或评语正文。35条是23个tree版本、33个actor×tree×case试跑，不能写成35个独立合格skill。29条producer有strict protected boundary，6条是protected producer方法候选；本次据此能证明干净完整utility/KEEP链和干净Q/修订反馈边均为0。0是“尚未证明可用”，不是声称全部历史中不存在其它可恢复干净链。

完整SKILL交付记录数分布为7条零、26条一、2条二。case source有11条落当前过程54source；actor episode任一owner命中protected/reserved的分别1/13条，这只是episode内存在该边界，不自动污染更早的所有prefix。必须按目标前的实际交付范围和版本SHA重核。

唯一与当前native-owner关联view相交的是 `process09-0f1603b601613eac2fecb014`，9905个A正tokens。actor `ep_62da6b3ba25f33c2b5b3` 的target为msg16/event30/call531fac1845a34086a5b2d38bfb7f73e6。关联producer `ep_8188203e94e9e8b652b2` 的strict boundary=2，但edge的actual_full_SKILL_delivery为空。

精确检查发现：target前唯一read为msg3→4读取原用户请求，toolresult SHA `defe48061771025bd154521f1ff45c478d2b22ab7332b76dc0cf65f47560733a`；记录中的其它exec路径是adapter、tmp、outputs。保护package的12个文件CAS字节SHA均与登记一致；这些文件完整文本及归一行文本在target前已记录输入中均未命中。尚无“模型实际收到保护SKILL全文”的证据，不能仅凭同episode/磁盘tree直接断言污染。

同时原system capture为INCOMPLETE、0原system、0API request capture，未排除未记录的system/资源片段，代码祖先闭合仍为UNKNOWN。不能宣布09新集合已经清白。应把该view的祖先闭合作为下一轮P0；本轮保留冻结09，不静默重写历史。

## 下一轮有界顺序

| 优先级 | 已知输入和单位 | 下一轮动作 | 可产生训练目标的条件与停止条件 |
|---|---|---|---|
| P0 现有高权重view祖先 | 上述1 view、1 native CAS、1 protected producer、12 package文件 | 在原native与原provider/SSE索引两个既有根内找原system、实际工具交付/截断回执；按target前后划界并保全SHA。以相同方式复核09新增49 view与protected producer实际资源SHA的交集 | 找到严格target前交付则按来源隔离；两根均无闭合证据则停止为UNKNOWN，在下一版拟训练清单中隔离待核，不以新state重述解除祖先风险 |
| P1 身份补齐 | 56 owner/1 source/4 episode；补录2173 owner/102 episode（其中55已关联scoped-view） | 一次性只建source、native response、原工具、父producer、资源SHA、实际送达时点索引。恢复的source先过226/H12/static/新40reserved和protected组件屏障 | 身份/祖先闭合后才进入内容审阅；同一source/episode只恢复一次。没有原标识则保留UNKNOWN，不自行发明TRAIN身份或把0 readable-R当无R |
| P2 R→动作→版本→反馈 | 26历史R正文396231字符，其中UNKNOWN208040字符；当前原R-only与A目标关联缺口 | 先对所有26及当前R-only owner作元数据因果连接，优先找到原R后的真实A、具体版本、实际工具反馈、试跑/Q/修订边；首批最多12个响应owner、3个干净来源族、UNKNOWN原R最多50000字符，按完整局部因果段切而非机械截断 | R中的事实/局部计划被目标时可用证据支持，A本身语义正确且作用版本闭合，反馈确为该版本才授相应范围正loss；失败事实可作输入，错误动作/虚假完成不授正。无A/反馈则不把新增R文本量当调度能力，达到首批边界即复盘 |
| P3 既审具体HOLD的修复链 | 139 owner/58 episode/36 source/35 route；writers31已有11关联owner+19HOLD+1reserved | 先合并既有具体缺陷与后继原版本回执，首批最多10个owner、3个任务族，只打开有新增版本/反馈证据的候选 | 新证据能精确解除旧缺陷才重审；无新证据不重复整批审阅。新写修复单列new-authored，不能冒充原教师动作/原思考，不能用修复成功回授旧错误动作 |
| P4 大祖先队列 | 5126未关联条件owner；52方法族；5特缺证 | 对5126仅按实际producer/version SHA归并一次，查是否已有边；52先保持方法族隔离账；5逐条对旧具体缺证表。只有新发现干净原证据的owner进入下一轮有界内容队列，首批最多20 owner | 不按route名做祖先等价。保护资源只做身份/实际交付元数据过滤，不读其Q与思考充训练。只重复已有理由而无新增证据即停止 |

P2优先弥合“原思考之后究竟怎么行动、该版本在真实试跑如何、反馈怎样触发修订”的关系，而不是继续只扩R-only。当前相关响应owner的精确重叠与原R-only配对数需采用同轮训练统计复核结果，不能把来源相同或字符相邻替代同一因果边。

## 交付合同

下一轮每个可授信单元至少保留：source/component及保护状态、原native/API响应pin、target前可见输入、原R范围与原字段、原A/工具call、原toolresult/截断范围、输出或package版本SHA、实际消费回执、Q/修订/STOP的版本化连接。每条边标 `observed / inferred / unknown`；未来评分不得进入较早输入。未知与错误范围保全并mask，不能因done/retain/exit0自动正向监督。

只在上述关口通过后才增加16K/32K共同训练view，使用09已有严格token/mask/loader验证，原R与new-authored理由分别记账。当前局部subtask目标与完整自主A–D调度示范、合格KEEP链、每个合格skill成本统计分开；后者目前仍未被这些35条历史元数据证明。首轮候选处理量是预算上限，不预测新增正例或正tokens产量。

## 本轮机器产物

- `GAP_REVIEW_METADATA.json`：输入pins、最终覆盖重算、139HOLD与31writers摘要、35edge交叉、当前过程54source元数据。
- `OLD8376_REBASED_OWNER_WORKLOAD.metadata.jsonl.gz`：8376个owner的互斥当前工作状态、原native pin与具体ID；不含思考/企业正文。
- `OUTCOME35_CURRENT09_CROSSCHECK.metadata.json`：35边的producer、交付计数、current-view交叉及边界限制。
- `SLIDE_CURRENT_VIEW_RESOURCE_LINEAGE_METADATA.json`：0f1603逐消息工具path/call/result文本SHA、保护包12文件精确字节与完整文本交付匹配结果；无protected Q/思考正文。

所有路径均相对于 `D:/skillloop/`。这份文件是可执行范围与条件设计，不是已完成数据整理或收益实证。
