# 五份实质原R再情境化样本：语义、资源版本与动作信用

本批是原兼容API思考的连续摘录，配合同响应实际A及真实齐全局部功能状态的研究投影。明确银行`recontextualized_compat_R_process10`、权重0.25、`RECONTEXTUALIZED_ORIGINAL_COMPAT_R`；不冒充原请求、原生完整前缀、私有upstream CoT或自主A—D示范。没有修改原R、原A或原始失败；本子任务只提交待root准入候选，没有激活主manifest。

## 最终冻结

原候选：`CANDIDATES.proposed.raw.jsonl.gz`，168046B，SHA **b26347fbeef8408980ff06f60964f82fb1885a0ece94256cb3213e3b88495b84**。下文和QA不再修改该raw。5条共17418个原R摘录字符，错误／过度结论及流程过渡的885字符保留而不授R正loss；这些是字符，不冒充编译后的token数。

14B与8B各自真实调用tokenizer，两者IDs／offset一致，完整新状态＋全部目标tokens分别 **29719、29302、27748、23974、24432**，都在32K内。六份忠实全system／past＋core7原请求版本分别50685、56354、58167、38884、38842、40892，均超32K，另存`FULL_ORIGINAL6_OVERWINDOW_DUAL_TOKENIZER_QA.json`，未暗裁原输入来称原生配对。全原R、原请求、SSE和反馈仍在reasoning_native10的67份原件中。

## 逐项实质内容与授信范围

| 原响应 | 原R内容及证据 | 原A与局部信用 | 不授予什么 |
|---|---|---|---|
| Brevision17 | 连续5287字符：同subject/value/unit的actual与goal不必矛盾；保留planned→achieved误用拒绝；任意遇到的refs需校验形状，空可选refs与必需缺证有别。全文旧CLI、原runner、fixture生成器、独立反馈和legal材料均在prompt；旧CLI真实有`evidence_ref_invalid`两处，对应缺ID／空quote，未误引错误名。 | 同响应exec建立skill/tests副本、保留旧日志、计算旧资源SHA。实际SETUP_OK与原CLI／副本SHA一致。它准备修订，不是已完成修复。 | 未摘录后续有关递归实现范围的犹豫／代码草稿；不把“所有refs应校验”的设计合同当程序已穷尽实现。 |
| Brevision24 | 从“Now build supplementary tests”开始连续6131字符：12类正常／边界／错误反例的退出码、failure ID、路径和可选证据断言。当前CLI、原runner、反馈全文可见；source／年份均声明合成用例。 | 同响应实际写make_fixtures_extra.py；完整源程序经AST／依赖检查，离线实际生成夹具并与原runner验证12案例。 | 原首70字“21/21且旧fixtures不变”保存在原件但不进入本摘录，避免据只列SHA声称模型读完旧fixture；“to prove genericity”及流程过渡明确零loss，12例不证明普遍泛化。 |
| Brevision25 | 连续2177字符：检查X9可选空refs、X12事实层畸形、planned→achieved类型错用，以及各case精确断言／日志。当前CLI、新fixture生成器和反馈全文可见，R所讨论的X1—X12来源已完整提供。 | 实际写run_tests_extra.py，经完整代码检查并离线跑12案例；退出码／具体ID／路径有真实断言。 | native记录有6字符变量→`***`脱敏例外，不称native参数字节全同；原API body、同ID写入字节回执和最终源文件整SHA共同保全。 |
| Bmake14 | 连续2125字符：21案例的正常／边界／错误／classify判据，精确错误ID与证据路径，退出码不代替正确性。旧CLI及当时fixture生成器全文可见。 | 实际写run_tests.py，完整原API源代码可由最终实体和写入字节回执核验，离线原21案例通过。 | 同样保留native脱敏例外，不重写为无差异；末尾纯实现过渡零loss；21例不是技能业务质量或复用效用证明。 |
| Bmake16 | 连续1698字符：对21测试通过作断言有效性核查，检查600字边界与fixture截断不会切坏数值，识别dead-code需要资源修订后复测。CLI、原runner、原始未清理fixture生成器全文可见；原API15的21案例通过输出在此前观测中。 | 实际read边界600字报告；同ID成功读取及完整返回保全，局部动作正确。报告实体由原API15测试运行在target16前产生，并以实际读取版本及独立CPU JSON等价重建。 | 报告内容作为实际文件实体保全，未把当前read之后的反馈放入较早prompt。两处纯进度转接零loss；不把已通过案例推出未覆盖业务正确性。 |

## 资源的时间与可见性

`functional_states/`内是真实完整文件实体，来自原job逐SHA提供的输入、target前实际write的完整原API body，以及原edit对精确旧文件的逐项唯一替换。Brevision17原copy动作按字面源文件复制关系恢复，并有同call实际SETUP／SHA回执，不执行替代Agent循环。Brevision21三项实际literal edit使CLI从`6a1e9515…`变为`86336921…`，与原测试log及最终文件相同；因此Brevision24／25使用的是当时已存在的修订版本，未把未来版本提前塞入状态。

每个sample的`visible_file_contents`明确给出R判断所用资源全文。`actual_files`列出的其它文件只表示环境有实体，不声称模型已读取全文。Brevision17的原21fixture生成器已完整提供，能直接确认N1／N2、E6空必需证据及各ledger事实类型；Brevision24的局部目标是设计新反例，原21历史主张移出摘录，保留新case推理所需CLI／原runner／反馈全文；Brevision25所有Xcase来自已写入的新生成器全文。后来的测试仅用于授信，不进入较早输入。

完整原生历史没有被删改；这里新造的是**明确署名的局部状态用户输入**，原R仍逐字符连续来自真实字段。不能将这些5行与6条原请求读取R配对混称为11条原生完整条件示范。

## 实际资源验证与负结果

已经离线运行原API源程序：旧CLI原21案例21通过；实际原edit恢复的修订CLI原21案例21通过，补充12案例12通过。还对同一批既有独立输入做旧／修订三对反例验证：合法时态同值旧版错误拒绝→修订接受；nested refs字符串和[42]旧版错误接受→修订明确拒绝。程序源码未修改；结果、命令、输入／输出／CLI的真实SHA见`CPU_RESOURCE_CHECKS.json`和`OLD_VS_REVISED_REAL_COUNTEREXAMPLES.json`。这是CPU资源检验，不是新native试跑、专业语义Q或KEEP。

另审Bmake21原资源检查，原反馈确有`SKILL.md False`但同时`ALL_REFS_RESOLVE: True`。检查使用错误根目录且没有把该项计入ok，不能给A正loss；该原响应完整保留HOLD，不因exit0／最终字样洗正。

## 原A参数与owner去重

五条A均逐字保留原兼容API参数，`A_original_action_arguments_identical=True`的比较对象明确为原API；另由`A_original_native_record_arguments_identical`准确记录两个脱敏例外。Bmake14原API body11748B、Brevision25 body9835B，同ID原tool反馈的实际写入字节数相同，最终资源整字节／SHA也相同；没有静默改native原记录或把`***`当原可运行源码。

当前595所有正A的call ID与这5条均无交集；选中R原owner范围当前正监督均为0。早期15的owner／范围与这5条也不同。source仍是原三来源组成的已见连接组，增加教学行为和内容，**不增加独立source组**。最终root对所有其它新银行再统一去重，不能用本报告绕过跨银行重复核对。

## 冻结产物

`FROZEN5_SEMANTIC_STATE_AND_SOURCE_QA.json`记录最终raw pin、真实资产SHA、可见资源全文路径、原R连续范围、R/A owner去重、双tokenizer完整长度。`COMPONENT_CREDIT_AND_OWNER_LEDGER.json`记录逐component归属，`FULL_ORIGINAL6_OVERWINDOW_DUAL_TOKENIZER_QA.json`保全原state超窗证据。原R信用尚须root准入及实际编译／token-mask独立复核；本报告不把候选数当主集新增数。

本轮无新业务Teacher／Actor、模型权重、推理或训练。AI整理／CPU资源检验成本未知，不能登记为零。最初CPU检查在执行前因本地已知validate_pack模块导入白名单不足停止，保全该检查目录，后用独立cpu_checks02目录完成原程序验证；未覆盖负记录。
