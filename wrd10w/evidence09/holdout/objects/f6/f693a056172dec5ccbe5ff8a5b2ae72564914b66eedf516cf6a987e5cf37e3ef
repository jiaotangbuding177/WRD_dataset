# Agent Memory / Self-Evolving Agent Security CCF-A 论文矩阵 v1

> 来源清单：`docs/agent_memory_self_evolving_security_ccfa_list.md`  
> 方法：每篇论文由一个 subagent 独立分析，提取 venue/CCF-A 状态、记忆机制、安全覆盖面和研究缺口。  
> 范围：仅覆盖来源清单中的 CCF-A 主会 / regular / full / long / poster-track 论文；不混入 workshop、Findings、short/demo、arXiv-only、博客或工业报告。

## 论文矩阵

| # | 论文 | 会议 / CCF-A 状态 | 类别 | Memory 类型 | 演化操作 | 谁控制演化 | 已研究的安全问题 | 攻击者 / 评估设置 | 与本题相关的缺口 | 相关性 | 论文中可能用途 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [Your Agent May Misevolve: Emergent Risks in Self-evolving LLM Agents](https://arxiv.org/abs/2509.26354) | ICLR 2026 Poster；ICLR 属 CCF-A。 | 自进化 agent 安全总框架 | 经验型长期记忆；轨迹总结 / 策略蒸馏记忆 | 经验积累、轨迹总结/蒸馏、成功/失败记忆存储、相关记忆检索进上下文 | 由 agent 的自演化机制根据任务轨迹和反馈触发；不是攻击者直接控制 | misevolution：安全对齐下降、部署期 reward hacking、风险意识下降 | 没有统一强攻击者模型；评估覆盖代码、销售、客服、医疗、金融等场景 | 不是 memory 专项；缺少 summary、reflection、merge、forget、link、retrieval tuning、shared propagation 的操作级威胁模型；缺 provenance collapse、semantic drift、retrieval dominance 等指标 | high | 作为 CCF-A 级别的 broad framing，引出“自演化会带来动态安全风险”，再收窄到 memory evolution audit |
| 2 | [AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases](https://proceedings.neurips.cc/paper_files/paper/2024/hash/eb113910e9c3f6242541c1652e30dfd6-Abstract-Conference.html) | NeurIPS 2024 Main Conference Track；NeurIPS 属 CCF-A。 | memory / RAG poisoning；agent red-teaming | 长期记忆 / RAG knowledge base；query-solution key-value demonstrations | 投毒写入、trigger-driven retrieval | 攻击者控制少量恶意 memory / KB 条目和 trigger 优化 | 触发条件下检索中毒 demonstrations，诱导目标恶意行为；干净查询尽量保持正常 | 攻击者可部分访问 victim RAG database；评估 Agent-Driver、ReAct-StrategyQA、EHRAgent | 不研究投毒条目被 summary、merge、link、forgetting、retrieval tuning 或跨轮传播后如何变形、放大或洗白；缺生命周期 provenance 和治理机制 | high | 作为写入/检索阶段 memory poisoning 的核心 CCF-A baseline，用来对比本文关注的 post-evolution poisoning |
| 3 | [Memory Injection Attacks on LLM Agents via Query-Only Interaction / MINJA](https://proceedings.neurips.cc/paper_files/paper/2025/hash/42a97bbd9844d2bf68596730af80bcdf-Abstract-Conference.html) | NeurIPS 2025 Main Conference Track；NeurIPS 属 CCF-A。 | query-only memory injection / poisoning | 长期记忆库；episodic execution records | 存储、检索、攻击者诱导生成恶意记录、indication prompt、progressive shortening | 正常 agent memory 写入/检索机制控制演化；攻击者不能直接写库，只能通过 query 间接注入 | 普通交互可诱导 agent 写入恶意 records，后续 victim query 检索后被带偏 | query-only attacker；共享 memory 或身份伪装路径；评估 RAP/WebShop、EHRAgent、QA Agent/MMLU | 不分析注入后 summary、reflection、merge、forgetting、linking、retrieval tuning、跨用户传播如何改变攻击；缺 provenance/governance 闭环 | high | 作为低权限真实攻击模型；用于 threat model 和 related work |
| 4 | [Unveiling Privacy Risks in LLM Agent Memory / MEXTRA](https://aclanthology.org/2025.acl-long.1227/) | ACL 2025 Long Papers；ACL 属 CCF-A。 | memory privacy / extraction attack | 长期情节/示例记忆；历史用户 query-answer pairs | 检索、排序、选择性加入 reflection；实验中未评估动态记忆更新 | agent 框架控制 memory retrieval；黑盒攻击者只控制 prompts | 从 agent memory 中抽取历史用户查询，造成隐私泄露和未授权访问 | 黑盒攻击，basic / advanced knowledge 两档；评估 EHRAgent 和 RAP/WebShop，静态 memory size 200 | 主要是静态检索泄露；缺动态生命周期、summary/merge/forget/link/tune、传播、authority inheritance、多 agent 或 session 隔离分析 | high | 作为 confidentiality / privacy 维度，说明 memory 本身就是攻击面，即使还没有自演化 |
| 5 | [A-MemGuard: A Proactive Defense Framework for LLM-Based Agent Memory](https://arxiv.org/abs/2510.02373) | 分层核验：作者主页标 ICML 2026，ICML 属 CCF-A；但 arXiv/DBLP 层面的正式出版元数据仍需后续复核。 | 主动 memory 防御 | 检索式 primary memory + lesson memory | 写入/归档、检索、过滤/清洗、异常 reasoning path 蒸馏成 lesson、检索 lesson 修正行为 | 攻击者可污染 primary memory；A-MemGuard 验证模块控制清洗和 lesson-memory 更新 | context-activated poisoned memory 与 self-reinforcing error cycle | 黑盒攻击者知道 memory schema；覆盖 direct poisoning、query-only injection、自强化多轮场景和多 agent misinformation 扩展 | 不审查完整自演化操作：summary、reflection、merge、forget、link、tune、shared propagation；lesson memory 本身可能被污染或绕过；provenance、version、rollback 治理不足 | high | 作为最接近的防御 baseline；用于对比本文的 lifecycle-level provenance-preserving memory evolution |
| 6 | [A-Mem: Agentic Memory for LLM Agents](https://proceedings.neurips.cc/paper_files/paper/2025/hash/19909c36f51abc4856b4560aff3d36d6-Abstract-Conference.html) | NeurIPS 2025 Main Conference Track；NeurIPS 属 CCF-A。 | 自进化 agent memory 架构；非安全论文 | Zettelkasten 风格原子笔记：raw content、timestamp、LLM 生成的 keywords/tags/context、embedding、links | note construction、dynamic indexing/link generation、更新旧 memory 的 context/keywords/tags、linked-memory retrieval；prompt 中有 strengthen/update_neighbor；schema 中有 merge/prune 但非正文核心机制 | LLM 驱动的 A-MEM memory evolution agent 控制；新 memory 写入后触发；无人工或安全审批层 | 未研究安全问题；“adversarial questions”是不可回答 QA 类别，不是攻击模型 | 无攻击者；评估 LoCoMo、DialSim 长对话 QA，并与 ReadAgent、MemoryBank、MemGPT 等比较 | 缺 threat model、投毒/间接注入、provenance、semantic drift 审计、检索概率放大、behavioral persistence、shared-memory propagation、rollback/quarantine | high | 作为最清晰的 CCF-A self-evolving memory 目标系统；用于定义 link/update/context evolution 等审查操作 |
| 7 | [ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory](https://openreview.net/forum?id=jL7fwchScm) | ICLR 2026；ICLR 属 CCF-A。venue 证据来自 Google Research / 项目 BibTeX；subagent 环境中 OpenReview 页面遇到验证阻挡，需后续复核。 | test-time self-evolution / reasoning memory；非安全论文 | 结构化 reasoning memory / strategy-level memory，从成功与失败轨迹中蒸馏 title、description、content 三段式记忆 | 检索、抽取、append-only consolidation；LLM judge 标注成功/失败；失败轨迹生成预防型记忆；merge/forget/prune 留作未来工作 | LLM judge 和 extractor 控制记忆生成；系统直接 append 到 memory pool，无人工审批或 ground truth | 未研究安全问题 | 无攻击者；评估 WebArena、Mind2Web、SWE-Bench-Verified 等正常浏览和软件工程任务 | 缺 threat model、poisoned experience、judge manipulation、provenance/audit、写入审批、rollback、隔离、持久性和传播安全指标 | high | 作为顶会 self-evolving reasoning-memory 闭环正例；用于说明“轨迹判断 -> 抽取策略记忆 -> 写回 -> 后续检索进 prompt”这一能力链缺安全审查 |

## 建议阅读顺序

1. **Your Agent May Misevolve**：先建立 CCF-A 层面的总框架，说明 self-evolution 为什么会产生动态安全风险。
2. **A-Mem** 和 **ReasoningBank**：作为机制背景，说明 memory 已经会通过连边、上下文更新、经验到策略抽取等方式自我演化。
3. **AgentPoison** 和 **MINJA**：作为核心 memory poisoning baseline，分别覆盖 direct / partial-write 和 query-only injection。
4. **MEXTRA**：补上 agent memory 的 privacy / confidentiality 攻击面。
5. **A-MemGuard**：作为最接近的防御 baseline，用来对比检索后验证、lesson memory 与 lifecycle audit 的差异。

## 研究缺口声明

现有 CCF-A 文献已经分别证明了三件事：self-evolving agent 可能发生 misevolution，agent memory 可以被投毒或抽取，现代 memory 架构确实会持续更新内容、链接、上下文和 reasoning strategy。然而，即使是最接近的安全论文，也大多停留在写入阶段投毒、触发阶段检索，或检索后的验证防御。它们尚未系统审查 memory evolution operations——包括 summary、reflection、merge、forgetting、linking、retrieval tuning、lesson-memory update 和 shared propagation——如何改变初始污染记忆的来源属性、语义强度、检索概率、行为影响、持久性和回滚路径。这正是 self-evolving agent memory security 需要补上的核心缺口。

## 备注

- **A-MemGuard** 和 **ReasoningBank** 的正式 proceedings 元数据建议后续继续复核；目前矩阵已保留“强 venue 证据但需复核”的状态。
- **A-Mem** 是最适合作为 graph / linking evolution 审查对象的 CCF-A 架构论文。
- **AgentPoison** 和 **MINJA** 是最适合作为普通 memory poisoning baseline 的 CCF-A 攻击论文。
