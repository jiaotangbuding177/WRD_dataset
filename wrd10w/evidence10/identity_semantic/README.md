# 版本与反馈约束的局部修订候选

这三行是供根审与编译的**显式新功能状态**，不是原native完整请求重放，也不是新增原始CoT。main未改、原226继续隔离、没有新业务调用／权重／训练。沿用已有三来源，不增加独立来源数。

当前提交根复编的是`CANDIDATES_TOOL_ABI_V2.raw.jsonl.gz`，含两条修正A投影与不变的原HOLD投影，root_main_admission=false、requires_external_root_admission=true。候选仅为局部正确推荐；根须独审后才能进入活动主集。新state/新理由统一0.25。

前版`CANDIDATES.raw.jsonl.gz`完整保留。根真实compiler发现其中两条A用了旧的顶层oldText/newText，与我引用的实际capture edit schema不符，返回TOOL_ARGUMENT_SCHEMA_INVALID；**前版两条A不可训练，不计编译成功**。这属于本轮整理器的ABI投影错误，不改写为旧原生模型错误。v2已按实际edit(path, edits[])重建，首条两处非重叠替换合为一次调用，第二条一次单替换；原literal replacement字符串／前后文件SHA不变。`TOOL_ABI_V2_FIX_REVIEW.json`保留失败v1 pin、实际schema、代码一致与JSONschema检查；本子模块只完成schema验证，token编译状态由根后续真实回执决定。

两条修订都针对原gen02**制作端自行新写的辅助脚本**`outputs/making_history/replay_verify.py`，不是外部评分器或正式检查器；不得改外部validator、期待退出码、业务断言或准入阈值。原公开反馈显示：

1. 原write msg53的4549B verifier将断言根目录拼成case子目录，但原case命令实际把文件写在统一OUT。msg57实际literal replace只修目录定位，重建4454B中间版；下次真实运行出现新的stderr缺文件，不能据前一个错误消失称全部通过。
2. msg59实际literal replace修的是期待失败也应保留真实stderr。此前returncode=expected_exit=2时进入exit_ok分支，没有写stderr.txt，断言因此FileNotFound。先无条件落真实stdout/stderr，再使用不变的expected_exit和断言；重建4318B版与现存原工作区最终文件逐字同SHA。

投影输出为真实edit工具，对原文件版本作精确oldText／newText替换；oldText是定位选择器，不是把旧错误程序当修复后代码授信。原replacement块的作者仍是原模型，调用形式与输入状态是本轮整理投影，actual_native_tool_dispatch=false。两个短R均为新作者局部理由，不冒充旧内部思考。未来msg60 ALL_OK只在credit证据中，不进入msg59之前的输入；完整skill效用未获授信。

CPU只在本目录的任务自有目录验证原literal函数片段，不运行原shell/rm命令、全Agent、完整业务case或外部评分器。初次检查脚手架缺expand函数，运行报NameError并保留首次目录；修正脚手架后run02的反例证明：旧目录/FileNotFound与旧stderr/FileNotFound均能复现，新版本通过同一期待文件／真实stderr断言，而错误退出码仍判失败。没有以检查通过代替业务Q。

第三行保留repair1原msg112最后一段**原可见HOLD文本**。原resource_manifest.json和evidence.json确未落盘，原始附件未恢复，只有generated_fixture；因此“未完成、不宣称资源复现通过／节省、缺证据HOLD”具有限定事实依据。输入账本为显式新state，不伪造完整旧对话；输出D原文逐字保留，原R为0。

`LOCAL_REPAIR_CPU_QA.json`保留版本SHA、原错误与后续反馈、旧错／新对／错退出仍失败、实际文件缺项和全部执行条件。`SEMANTIC_RECOMMENDATIONS.json`逐行给适用范围；本模块没有提供完整自主A—D、独立消费Q或KEEP正例。

gen01两处省略号参数另已在原transport/evidence定点核对：runtime／transcript副本仍保留省略号或36B诊断占位，不能拿工具success及幸存完整文件倒填原调用。该疑点不涉及这里使用的gen02两个原literal替换块；实际body、错误和版本链保持独立。
