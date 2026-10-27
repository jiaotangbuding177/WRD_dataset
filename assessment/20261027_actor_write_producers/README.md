# 57个旧业务write的真实任务producer复核

本目录接续`clean_prefix_rescue_01`，检查原先被列为“当前train-source可复核”的57个业务write。这个名称只描述直接原源状态，不能充当完整资源血缘或语义正确证明。全部原记录继续保全；本轮未执行旧程序、启动模型或训练。

最终结果为**34个write已证实受保护任务producer影响，23个仍缺具体生产者闭包，0个proven-clean，新增execution_main为0**。范围是57个write／39个Actor episode，不推断其它未审目标也全部不可用。

## 已完成的实际核查

`producer57_extended_static/PRODUCER_AUDIT.json`是最终入口。每条任务均先把原request中的input，接到实际Actor native user消息；再寻找实际prepare／旧`*_devprep`中的对应任务生成语句和任务产物。保护仅由确证生成边，以及生成之前实际送达的受保护请求或原用户标题建立。源ID、路径、同路线名称、任务与原user不逐字相等均不是单独的污染证据。

独立回读核验通过：39个真实Actor任务投递、43个任务生成边、66个原226／新H集合核对、64个JSON请求／标题记录、2个纯文本原用户标题前缀和7个实际任务产物。共62份native原件按SHA核过。所有报告只保存必要的SHA、位置和结构，不复制受保护业务正文。

核查修复了三个实际遗漏，旧报告仍按时点保留：

1. 原producer有时通过exec打印`=== source_id | 标题 | 类别`，而非返回完整JSON。现将实际打印前缀与原用户正文中的标题逐字对应，不能把这类真实已送达内容遗漏。
2. 旧`*_devprep`被catalog误分为screen／review／legacy，不能只按prepare角色找生产者。现按原目录与真实事件补回。
3. 旧静态解析器把`development_tasks.json`的输出错认成`tasks.json`；部分实际JSON还使用列表／字典推导式。现只作有界AST字面量投影，恢复prompt进入JSON dump的关系，并强制核对真实产物。**未执行原代码、未编造工具返回**，该部分投影不是完整实际文件字节。

## 对语义质量的影响

首8个内容pilot确实找到了完整失败、诊断、修订和复测记录。例如一个演示资源首次write成功，但后续真实试跑发现状态转换错误，再经局部修改复测；因此不能把最终成功反授给最初错误write。该链的原任务producer后来核出受保护来源，仍不能进入正loss。程序功能合格不能消除来源边界。

招聘流程两个程序所在的原Actor任务已接到实际受保护prepare，连同同episode的另一个write保持loss0。旧简历报告的`*_devprep`原task生成边也已恢复，但上游的`development_sources.json`包含6个来源及`user_requirements`，其中2源当前受共享私有输入边界保护；不能用最后选中的2个train源代表整个可见packet已闭合。`SOURCE_PACKET_STRUCTURAL_NOTE.json`只记录该结构问题，没有据此伪造“直接见到原226全文”的结论。

23个未决write的实际Actor、任务SHA、已找回生成边、相应原scope证明和具体未闭合资源CAS／路径见`REMAINING_GAPS.json`。未知项没有被改成已证保护，也没有被改成clean。部分还缺精确原task生成，部分已找回task但需继续核route或输入packet；这些原因分列。

## 训练入口与历史勘误

`PRODUCER57_IMPACT_FINAL.json`逐57目标规定future import时loss0。实际v10 ACTIVE银行没有导入这些旧Actor，所以当前主训练数组不变。

这些39个Actor与前一轮26 Actor审计互不重叠。对旧v9辅助分片的额外影响是：16序列／24目标／938个监督tokens在未来导入时撤销；12序列／21目标／737tokens因缺证继续hold。旧分片及历史成本未修改，也不将这938／737再次计成新增训练量。详见`V9_AUX_FUTURE_IMPORT_ERRATUM.json`。

最终核验回执为`PRODUCER57_INDEPENDENT_QA_FINAL.json`。其它`producer57*`目录和snapshot脚本记录先前时点，用于解释机械缺边如何修复，不当作新增独立样本或当前准入入口。科研AI标注费用为UNKNOWN_NOT_ZERO。
