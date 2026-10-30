# 精确加密审计 URL 例外合同

根任务已明确允许保全这3份原件：它们仅以既有 AES 加密载荷交付，密钥留本地，不作为 public_export 或默认 SFT 输入。本机制的状态是 `POTENTIALLY_SENSITIVE_EMBEDDED_URLS_ENCRYPTED_ONLY`，不声称所有 URL 无敏感性，也不把所有匹配称为真实可用凭据。

原4171文件冻结清单、扫描失败记录、完整原文件 SHA 和300次命中的诊断均保留。冻结清单及源数据没有因本工具变更而被修改。旧 `package08.py`（SHA `aa394cd4e73bebe4d3ad923699e585e23b28c2f867bac4be8072c9fd60297c7c`）保存在本目录 `history/`；新工具 SHA 为 `ffdbdb2393e589bd41bf604b216108c4a35d580aa8295f6df47fee5de2d5bddf`。

## 新冻结清单字段

根创建 allowlist02 时，从 `ENCRYPTED_AUDIT_URL_EXCEPTIONS_PROPOSED.json` 原样取两字段：

- `encrypted_audit_url_policy`：上述固定状态字符串。
- `encrypted_audit_url_exceptions`：3个元素；每项包含 `archive_path`、`source_sha256`，以及 `matches` 列表。每条 match 包含 `layer`（raw/gzip_decoded）、`match_sha256`、严格正整数 `count`。

该精确列表现为3文件/300次；列表紧凑 JSON 的 SHA256 为 `0c54b072cebe54a2c84d98005c25ce8f6bdd2aa4b78cc84924b66f63a27622fc`。matchSHA 认证的是旧扫描器实际命中的原始序列化字节，不是 URL 解码后的值。清单和此列表都没有存完整 URL 或参数值。

新 ROOT_FREEZE_RECEIPT 除原有 allowlist/base/current/canonical 四身份绑定外，需增加：

```json
{
  "encrypted_audit_url_policy": "POTENTIALLY_SENSITIVE_EMBEDDED_URLS_ENCRYPTED_ONLY",
  "encrypted_audit_url_exceptions_sha256": "0c54b072cebe54a2c84d98005c25ce8f6bdd2aa4b78cc84924b66f63a27622fc"
}
```

只有根批准的最终清单与 policy freeze 后才可 build。当前没有运行新全量 audit、真实 build、AES 或 Git。

## 只豁免一个启发式

仅当文件确为 `CONTROLLED_AUDIT`、与源 SHA 精确相同、没有任何明文导出，且不在当前 manifest 的 actual_train_files 中时，允许该文件中的 **SIGNED_OR_TOKENIZED_URL** 匹配通过。所有层/匹配 SHA/次数必须完全一致，既不允许新命中，也不允许遗漏已声明命中。

以下检查仍无条件拒绝：已知 credential 值、Bearer、JSON credential 值、私钥正文、key-shaped 值、嵌入密码 URL、私有配置/密钥文件与不安全路径。例外不会改变这些规则。相同文件 SHA 经另一个 archive_path 申请明文 public_export 也拒绝。

源任意一字节变动、额外 URL、同 URL 额外一次、换文件/换 raw-gzip 层、伪标 TRAINING 为审计、明文导出以及 policy 未冻结均不准入。根若决定另行制作脱敏投影，应另存新字节与映射，不能覆盖原件；本轮没有制作这种投影。

## 实际小型验证

`URL_EXCEPTION_CANARIES_QA.json` 共23项通过：明确 raw/gzip 审计例外正例，以及上述跨文件/SHA/类别/训练入口/明文别名/新命中/次数/层、所有保留秘密检查的负例。SHA 为 `ee5911dca03a680b9acc28641556cec3c766914f8bf72383999ed79498f1f627`。旧32项基础封包/恢复小夹具再次通过，见 `preparation/run04_url_policy/SELFTEST.json`，SHA `d3e72506539cfce7e23fe4d5fa431fb2198e0470253d5591d3cf276becc75ebd`。

这些是人工构造的有限夹具，无生产密钥/凭据配置读取、无新业务 Teacher/Actor 或训练；AI整理与CPU成本为 UNKNOWN_NOT_ZERO。真实全量 credential 扫描、认证封包、还原、双 tokenizer 与远端实体核验仍由根在新冻结后执行，不能由小夹具替代。
