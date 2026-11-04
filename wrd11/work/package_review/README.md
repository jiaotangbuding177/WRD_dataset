# 公开构造包工具代码独立预审

`PACKAGE_CODE_QA11.json`已通过当前源码的62个有限纯合成检查：7个正例、55个拒绝负例。**此回执不代表已经构建或还原真实WRD11包。** 完整构建、真实新根还原、数组与Git远端实体验收仍是后续步骤。

预审发现并由root修复：原路径在resolve后才查链接会丢失reparse证据；扫描后才首次pin留有不一致窗口；restore生成名可能被payload同名项覆盖；pack端casefold与Windows路径检查需同合同收紧。当前版本在resolve前检查原路径各祖先，限制声明源树与workspace，扫描前后核同一size／SHA，并在pack与restore同时保留两个生成文件名及其大小写别名。

检查实际调用了当前可信工具的路径校验、restore和继承扫描函数；抽取当前pack.add原AST到只含合成文件的隔离上下文，验证case别名、保留名和同长度扫描后变更被拒绝。只还原了一个很小的纯合成tar，确认声明文件SHA正确、payload中的Python文本未执行。测试拒绝了路径穿越、Windows非法／设备名、重复JSON键、重复／缺失／多余成员、大小写别名、错SHA／size，以及符号链接、硬链接、目录和FIFO成员。

还实际建立了一个指向另一个纯合成目录的NTFS junction，确认source guard在resolve前拒绝。测试结束只对精确链接调用非递归删除，链接已移除、真实合成target的SHA保持；WORK和测试目录均无遗留reparse。所有负例实物位于`D:/skillloop/output/20261031_wrd_curation11_delivery/package_negative_tests01/`，不在将公开打包的WORK树中。那里仅有新建普通文本、A/B变更字节、无害扫描needle、tar和惰性源码；没有原企业正文、真实或伪装的API凭据、密钥或权重。

公开包源合同限本轮新构造WORK、科研源码／计划／设计快照和本地tokenizer JSON／Jinja／text。原205过程池只按metadata引用，不由这些树复制正文。真实packager会使用本地既有凭据比较needle做raw及gzip解码扫描，未设置任何URL或其他例外；needle本身不导出。

本审查未调用完整pack.main、未创建或检查假定的`wrd11publicroot01`，没有提前使用“真实包restore通过”的结论。无模型、原生Agent或训练。
