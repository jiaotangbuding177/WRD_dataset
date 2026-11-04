# Checkpoint09封包／合并工具准备

仅准备与合成夹具验证，未build真实09、未合并真实08、未读取生产密钥／认证配置、未上传Git。原08两工具未修改。最终文件清单与公开导出由根逐文件冻结，不能把本目录fixture、伪密钥样例、临时目录或敏感proof用glob收入发布。

真实基底默认output/wrd08root01，PAYLOAD_MANIFEST SHA为acb51477c1ad657912d3df120af11c577543a0c354405e9adc643c75f5f19265。BASE_SCHEMA按该实体读取确认为wrd-authenticated-merged07-plus-delta08-file-union；不是把07基底的schema继续沿用。新delta schema为wrd-exact-merged08-authenticated-delta09，合并输出schema为wrd-authenticated-merged08-plus-delta09-file-union。

新工具：research/data_prep/wrd_curation09/package09.py、merge_delta09.py。package允许清单schema为wrd-delta09-root-frozen-allowlist-v1，build freeze状态为ROOT_FROZEN_ALLOWLIST_APPROVED_FOR_PACKAGE09。root freeze必须绑定allowlist、基底payload／main、当前main及canonical index的实际SHA；有受控URL例外时，还须绑定完整政策列表SHA及加密限定处置。auto封入两份root冻结证据，正文与冻结元数据都过相同凭据扫描。

canonical入口为canonical_arrays09/ARRAY_INDEX09.json、INDEX_PIN09.json、binary_loader09.py，与admit09一致。loader只接受两个已审定精确字节SHA：LF为61598377d258f126faeebc6cc2f7f4f9046aec77fb274c6f5a58402995ce122d；Windows实际110处CRLF为4a4836cfb78f3d30212ac1e14b7562b443febd40173a2b9b06e42806b5f6099e。两者除行尾外逐字相同，不在恢复时归一化，也不接受其它混合行尾或代码修改。合并器逐个结构化核验所有3n数组的ID／labels／weights，而不执行载荷中的loader或其它程序；保存的程序只是实体。旧row.binary_arrays不参与默认加载。所有训练shard、report与准入收据须是显式union的实文件，不能用未列出的磁盘文件填补引用。

完整合并只写NEW root。替换冲突的旧字节保存到history/pre_delta09/<oldSHA>/<原路径>；旧07／08 merge_evidence保留，新08基底证据与09 delta证据另存。路径遍历、大小写别名、重复manifest键／成员、目录文件冲突、缺实体及LF／CRLF LFS pointer均拒绝。最后再逐实体验证实际union、全部训练引用与全部canonical元素。

package09的guard_source、validate_url_policy、scan_file三函数与最终package08逐字一致，独立比较已验证。known credential、Bearer、JSON credential、private key与key形状守卫没有放宽；既有精确REDACTED literal规则不变。受控URL例外仍限CONTROLLED_AUDIT的逐文件source SHA＋逐raw/gzip层match SHA＋次数；TRAINING、default train、public export及同SHA公开别名均拒绝。例外只针对SIGNED_OR_TOKENIZED_URL启发式，不宣称URL无敏感性。

验证结果：run03/SELFTEST.json为33项key-free合成检查；restore_policy02/QA.json为21项还原／union／秘密策略检查，共54项。正向严格tar还原后全文件SHA及union核验通过，旧证据和冲突原字节完整保留；缺成员、错误loader、误mask与误weight、错基底、坏路径和精确URL例外越界均拒绝。tar还原测试使用显式FakeDecrypt，仅验证归档／引用边界，未冒充新AES密码学验证；真实交付仍沿用已验证的checkpoint05 AES API，并在根freeze后完成真实加密及还原。

后续Windows兼容修正保留旧工具原件于history：run04_crlf/SELFTEST.json重新跑33项，restore_policy03/QA.json重新跑21项，run04_crlf/EXACT_CRLF_QA.json另有6项：真实loader行尾字节证明、精确二SHA集合、CRLF合成union成功，以及重pin后的尾空格／混合行尾／代码修改均拒绝。这里的真实文件只读，不改stage或activate；主数据实际595的准入与全量QA由根另外记录。

最简key-free审计入口：

```text
python research/data_prep/wrd_curation09/package09.py audit --allowlist <ROOT_ALLOWLIST09.json> --expected-sha256 <allowlistSHA> --base output/wrd08root01 --report <新AUDIT09.json>
```

根明确冻结后才可build：

```text
python research/data_prep/wrd_curation09/package09.py build --allowlist <ROOT_ALLOWLIST09.json> --expected-sha256 <allowlistSHA> --freeze-receipt <ROOT_FREEZE_RECEIPT09.json> --base output/wrd08root01 --key <既有本地AESkey路径> --work <新build目录> --dest <新checkpoint09目录>
```

真实还原与合并入口（restore-tool使用08已验证的同一可信checkpoint05还原工具及SHA，不能来自载荷内未验证程序）：

```text
python research/data_prep/wrd_curation09/merge_delta09.py --base output/wrd08root01 --cipher <controlled/wrd-v10-delta09.tar.gz.aesgcm> --receipt <ENCRYPTED_DELIVERY_REPORT.json> --key <本地AESkey路径> --restore-tool <可信还原工具> --restore-tool-sha256 <工具SHA> --delta-out <全新delta09还原目录> --out <全新合并根>
```

本工具不做Git、不启动训练／Teacher／Actor，不执行保存的业务程序。最终tokenizer／源隔离／schema／数组loader／实际远端实体核验仍需根完成，不能以准备工具或54个合成用例说真实09已经交付。
