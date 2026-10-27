# 57个旧业务write：任务producer审计交付

本包是审计资料。34个write确证保护producer，23个具体缺证，新增训练序列／正loss为0。v10 ACTIVE没有导入这些旧Actor；原始业务正文、私有原件和凭据未随本包发布。未启动模型、旧程序测试或训练。

冻结32载荷及原MANIFEST.json逐字节复制，原manifest SHA为b836a5f5fd634a1145f63001318d05f686e8074a78f96ac6a2e729cb3b392610。最终审计入口为producer57_extended_static/PRODUCER_AUDIT.json，最终QA为PRODUCER57_INDEPENDENT_QA_FINAL.json。早期时点报告和源码快照保留，不当作新样本。

新增sidecar把旧26 Actor与新39 Actor的两套勘误，逐条接回同样四个冻结v9 native_process分片（train16K／32K、dev16K、test16K），核对原数组／spans SHA、split及正owner。两套record、episode、target ID都不相交，因此这次可以相加；并非只凭两份摘要相加。

| 口径 | 已证保护：序列／目标／监督tokens | 缺证hold：序列／目标／监督tokens |
|---|---|---|
| 旧26审计，train | 21／36／1260 | 3／4／151 |
| 新39审计，train | 16／24／938 | 12／21／737 |
| 合并train | 37／60／2198 | 15／25／888 |
| 合并dev | 0／0／0 | 0／0／0 |
| 合并test | 0／0／0 | 0／0／0 |
| 合并all splits | 37／60／2198 | 15／25／888 |

本次受影响行恰好全部为train，因此train与all数值相同。2198是旧v9辅助正监督在未来导入时应撤销的数量；888是尚待来源闭合、应保持hold的数量，不能与已证保护混为一类。旧v9冻结train仍登记1660序列／403788监督tokens，本sidecar不覆盖它，也不把局部勘误当成剩余v9已经通过完整质量审核。

COMBINED_V9_AUX_ERRATA.json列出实际统计宇宙、分split统计及逐目标ID。comparison_inputs/previous26/给出旧勘误的原字节；新勘误已在冻结32载荷内。COMBINED_ERRATA_QA.json记录同分片与disjoint检查。PUBLIC_MANIFEST.json是本次公开交付清单；MANIFEST.json仍是冻结32载荷的原清单。

发布前对当前两份native模型key和本地AES key进行了内存中的exact-byte排除扫描，包含gzip解压内容；没有输出、记录指纹或打包密钥。已对生成器的body-free字段及源码快照作范围审查，并以本次引用的保护源标题／完整可读消息作额外精确串扫描；这不是对任意语义片段的形式化证明。科研AI标注成本UNKNOWN_NOT_ZERO。准备脚本不执行git add、commit或push，Git上传由主Agent统一完成。
