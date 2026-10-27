# 原3149个clean前缀的逐目标复核

本目录完成一个明确范围的重新核查：旧v9认定为ADMIT的3149个助手位置，是否因“只认最终文件write”的旧准入方法而遗漏了可用的WRD设计、制作、验证、诊断、修订或收尾内容。原件和旧标签未修改。本轮没有新模型调用、训练或历史命令执行，AI审阅成本为UNKNOWN_NOT_ZERO。

实际结果为**新增WRD主样本0**。这不是素材无价值，也不表示全部其它未闭合原记录已经排除；是该指定3149位置集合的实查结论。

| 当前结构分类 | 目标数 | 含义 |
|---|---:|---|
| 原协议前缀分类 | 1278 | 主要为读文件／环境操作，不能当领域正确或完整自主示范；也不是新核准的企业内容零依赖证书 |
| 当前train来源可复核，语义尚未认证 | 1142 | 1100 Actor、40旧业务Actor、2 Maker的route读取；没有以来源合格替代质量标签 |
| 新证实保护producer | 207 | 原26 Actor审计中的23个保护来源生产链影响，撤销旧直接来源口径 |
| 缺producer证据 | 14 | 原3 Actor生产链未闭合，继续保全 |
| 当前原源／共享私有输入范围不准入 | 423 | 包括静态dev/test、保护或未决源，不重新划train |
| 旧native静态dev/test | 85 | 维持旧群组划分 |
| 合计 | 3149 | 每个位置只有一个分类 |

全部3149位置的学生视图显式R为0。另逐一检查其原native assistant内容块，同样没有readable thinking／reasoning块；因此不能通过重编译从这个特定集合恢复原R。这不推断其它已记录API／受保护轨迹也没有R。357位置有可见正文，其中184仍处于当前train来源可复核集合，主要是具体业务执行说明与交付。

make／prepare／screen／review及旧相应角色中，排除新26个Actor问题后，共25个非空位置出现在native message index≥3。这25个已逐一读取，全部仍为read／cat route、lineage、review_input等证据获取动作；其中5个之前未获协议辅助标签，20个早已为协议辅助。它们没有实际资源构建、实质评审或修订正文。不能把有用的读输入动作改名为B/C主数据来补数量。

旧clean集合中有94个write目标。当前train来源可复核57个，另1个仍只有协议来源分类，其余受新producer或当前来源边界约束。这些是业务Actor输出文稿、程序或页面，并不是遗漏的WRD技能制作会话。未来可按原版本、真实产物和独立语义检查构建执行资源监督；本目录只给出结构库存，不对它们授正loss，不把57计作已合格训练目标。

`TARGET_AUDIT.jsonl.gz`逐3149目标保存原episode、native行号、原消息SHA、当前分类、工具形状、正文/R长度与0新增loss。`NONINITIAL_WRD_STAGE_TARGET_REVIEW.json`给出25个目标的限定语义复核，`BUSINESS_ACTOR_WRITE_INVENTORY.json`给出94个write的来源／形状库存。所有报告均没有复制原业务正文、程序内容或凭据。`RAW_IDENTITY_QA.json`以原始CAS逐字节SHA及对应原事件行核对消息身份，范围和数量以该实际回执为准。

未解决部分包括其它HOLD_MISSING_EVIDENCE资源祖先、原系统／工具接口恢复、可独立认证的业务执行资源，以及新干净make→trial→feedback链；本次不会用空白或错误正loss代替它们。

实现：`research/data_prep/wrd_main_v10/rescue_clean_prefixes.py`与`verify_clean_prefix_rescue.py`。`draft_history_01/`仅保全首轮草稿（原SHA字段名称随后作了明确澄清），不作为当前报告入口，不打包为新增数据。
