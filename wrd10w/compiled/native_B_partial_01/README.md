# B02 原R局部银行 01

实际编译 **1 条唯一样本／1 个目标，30,296 输入tokens，2,460 个原R监督tokens**；全部为R，sample loss multiplier统一0.25，加权等效615。16K桶0条、32K桶1条。没有训练或修改ACTIVE。

原独立银标的21个正范围，经root逐段读取后授权，仅按call合并为19个区间；共13,923字符。`approved_components=[]`，六处明确错误与其余未批准文本均为0。本银行使用统一保守权重，不加载原review逐范围的0.25–0.5建议。

| call | 完整render tokens | 进入当前R的token位置 | 最后批准token末端 | 实际状态 |
|---|---:|---:|---:|---|
| 7 | 35,269 | 16,031 | 30,296 | 原token前缀编译 |
| 14 | 38,884 | 34,874 | 35,501 | 超32K保留hold |
| 16 | 38,842 | 38,368 | 38,708 | 超32K保留hold |
| 18 | 40,128 | 39,789 | 39,862 | 原工具参数schema错误；当前R前亦已超32K |
| 21 | 40,892 | 40,555 | 40,560 | 超32K保留hold |

call7完整输入保全，仅省略最后批准token之后4,973个未来未监督completion tokens；原`messages`中完整73,530字符R仍在。没有删过去、删R中间段、补EOS或补`</think>`。该call获批11,146字符，其中11,130字符有完全落在批准范围内的正token覆盖；其余16字符因边界/空白未得到正token。4个hold保留另外2,777个获批字符，没有撤回或改写其语义审核，也没有迁就长度生成替代输入。

本次新提取的24条原响应与已有`raw_recovery`逐对象完全相同，原R总80,567字符。银标审核截止call21的78,698字符，最后3次的1,869字符没有获得正监督。5个reviewed views各自保留原request的system、past内容和工具观察；旧R没有被补进后续request。7工具学生目录为各原53工具registry的精确声明子集，属于已声明蒸馏视图。

输入绑定原job、五个冻结资源及原allowlist/ancestry回执。样本沿同一B02父任务与一个source group；输入含两个主学习源及一个不适用边界源，不增加独立业务任务数。

[SCOPED_TOKEN_QA.json](SCOPED_TOKEN_QA.json) 已PASS：全数组/span、owner、mask、权重、32K、来源、独立双分词器直接重分词。[B01_RAW_MASK_COVERAGE_QA.json](B01_RAW_MASK_COVERAGE_QA.json) 已PASS：原24条完整保全、原past/R、实际registry、原字符/offset、六处零loss、全部非R零loss、精确未来前缀及逐call长度/hold核验。

这是AI银标，非human gold。call7只批准局部资源设计与验证计划；后续21例自测及fixture死代码清理没有被当作完整技能修复、独立消费或收益证明。成本`UNKNOWN_NOT_ZERO`，未运行Teacher/Actor、未加载权重、未训练。
