# Checkpoint10 独立端口复核合同

本报告由 `/root/curation10_lineage` 对根持有的 package10、merge_delta10、admit10 独立只读复核。结论为**端口源码、无密钥反例与当前活动 DATA 预核通过**；本报告生成时尚未执行真实 checkpoint10 解密还原，不能据此写“真实 restore 通过”或“远端交付通过”。完整机器回执为 `PORT_REVIEW10.json`，复核实现为 `research/data_prep/wrd_curation10/lineage_port_review10.py`。

## 旧认证依据与版本端口

实际读取原 `output/wrd09root01/merge_evidence/delta09_authenticated_manifest.json` 和 09 合并清单。原 package09、merge_delta09、checkpoint05_guard、既有 AES API 的当前源码 SHA 均与已认证 09 记录完全一致；admit09 与 09 文件清单 SHA 一致。逐项读取 09→10 diff，并用 AST 提取所有 64 位 SHA 常量。

10 的 base schema 精确匹配实际 09 根的 `wrd-authenticated-merged08-plus-delta09-file-union`，delta schema 为 `wrd-exact-merged09-authenticated-delta10`。没有将旧 hash 内出现的 `09` 当版本号替换：admit 的旧 07 loader 来源常量仍为 `edf1d3b8e1834fd7205e2f920112408cbeb062271ca372e509be2149ae3d8777`，实际源文件字节匹配。package 无 SHA 字面量；merge 的变化仅为明确批准的新 loader 字节身份。

根据已认证旧 loader 生成的 10 源码，独立计算得到 LF `2d9a7787376276e74ebe07c98ec0860deb03c0bb1734bd2584620849a5f814e6`、CRLF `6906845d321c4091984556027e630bfe730a2e726549834344cab21a4753cce9`。批准集合恰好为这两个值，当前活动 loader 属于该集合；不存在任意换行正规化后接受未知代码的合同。

## package 与 merge 的合同

package 只接根冻结的显式文件白名单，依次验证白名单、freeze receipt、base 清单、当前主清单与 index 的精确 SHA。复用既有 checkpoint05 来源守卫和 AES API，不从 payload 导入程序。来源守卫拒绝 symlink、可识别 junction、私有凭据目录、数据库、密钥及 bytecode 等；原件冻结后再次逐文件校验与复制。

凭据扫描覆盖原始字节和 gzip 解压层，真实已知凭据另在 build 扫描；本次独立复核没有读取本地密钥。URL 例外只允许指定 CONTROLLED_AUDIT 文件、精确源 SHA、扫描层、匹配 SHA 和出现次数，不允许默认训练或公开导出。44 个真实执行的负例覆盖路径、大小、重复键、凭据形态、gzip、URL 例外等；匹配值只为临时构造的人工测试值，临时文件已删除。

merge 在解密前要求新的互不嵌套 base/delta/out 根和可信本地 restore 工具 SHA。既有 AES-GCM 认证完成后才打开 tar；要求首成员为有大小上限的普通 manifest，核其 receipt SHA 并先验证所有声明路径。成员必须是清单中的唯一普通文件，名称、大小和 SHA 精确一致，使用 `xb` 创建，缺失和多余成员均失败。没有使用 `extractall`，不执行归档中的程序。文件目录冲突、大小写别名、路径遍历、Windows 设备名、ADS、尾点空格、symlink/junction 和保留路径有显式拒绝。tar 的这些结论来自源码阅读；本次没有伪装成实际解密或恶意 tar 运行测试。

合并是完整 base09 文件与显式 delta10 的新根并集。被替换旧文件保存在 `history/pre_delta10/<旧完整SHA>/<原路径>`，认证的 base09/delta10 manifest 各自另存。合并前后均校验训练引用和 canonical 数组，绝不调用保存的 loader 执行校验。

## admit 与实际活动数据

admit10 要求自己源码与所有冻结输入 SHA、精确准入／撤回 ID 集、根语义许可和独立 QA；保留 594 条原记录的原始 JSON 行字节。本轮新 accounting 明确区分再情境化兼容 R 和 A，原 R provenance 与 A 原参数 identity 均须满足相应断言。stage 不替换活动清单；activate 另需精确 staged SHA，备份旧清单和统计，再用清单作为最后的激活指针。

admit 的 `safe` 是可信冻结输入上的内部路径约束，**不是通用不可信归档校验器**：它未像 merge 一样显式拒绝 Windows 设备名、跨引用 case alias 或检查所有 junction 祖先。本轮最终路径还须经过 package/merge 的更强验证，不能将 admit 的存在解释为已完成任意恶意输入认证。本轮实际 623 路径及数据已独立检查，无此问题证据。

本次真实调用 merge10 的 JSON/gzip/struct 独立验证器，校验当前活动主清单 `9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e`：623 行、3,853,977 序列 tokens、227,233 正监督 tokens；1,869 个数组文件共 61,663,632 字节全部精确匹配源 input_ids、labels、loss_weights，attention_mask 为全 1。该预核不导入保存 loader。此前 `full_stage_qa01/INDEPENDENT_FULL_STAGED10_QA.json` 已对全 623 做双 tokenizer、精确 mask、来源、标准／二进制四 features 及 594 原行保真核验；那是 staged 根核验，不能自动升级为尚未发生的 10 还原结果。

## 待完成的真实交付认证

收到实际认证还原后的 checkpoint10 根后，再对该根执行全 623 双 tokenizer、精确 mask、来源／ABI、594 原行保真、1,869 数组及标准／二进制四 features 复验，并单独输出真实 restore QA。远端实体冷回读另验。本报告不授予训练或模型能力结论，训练和权重加载均为 0。

本地诊断中生成的 `.pyc.evidence` 不作为训练素材或默认打包内容；保留诊断 metadata、原数据与原源程序。报告未修改 package10、merge_delta10、admit10、stage 或活动 DATA 文件。
