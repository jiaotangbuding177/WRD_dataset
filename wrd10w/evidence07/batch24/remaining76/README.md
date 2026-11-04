# 其余76个episode的实际批量恢复

2026-10-29。按原计划100个maker episode去掉首24，且排除原先已证81保护位置，实际覆盖76个episode、590个待核位置。无新Teacher/Actor、业务执行、模型加载或训练，原边界与主集不改。

实际恢复4243条冻结原消息、2041次工具调用；686个同SHA对象共35308296字节。原目标全文/工具反馈、完整native、可找到的旧依赖和最终资源均为实际字节，非只有候选索引。792条原资源引用中745条冻结载体实恢复，余47条无完整冻结身份，保留具体缺口；最终402资源引用全部实恢复。重复对象、后续版本、消息、目标和独立来源分别计量，不把这些数字相加当训练量。

同一原producer与实际receipt规则得到341个明确保护派生位置；249个仍未闭合资源祖先，不能因顶层source为TRAIN就转正。这249个不是已证无用或已证错误：`REMAINING_GAPS.json`逐条保存原unknown理由、未闭节点和实际动作。所有590个目标完整保存在`TARGET_DECISIONS_AND_ORIGINAL_BODIES.jsonl.gz`。恢复脚本新增主训练准入为0。

路线识别严格核实际原write JSON与ACK；只接纳全对象、空conflicts默认、完整输入字段包含，或六原字段+steps复制route_signature.steps这四种明确机械变换。名字相同不能闭合。收到的工具正文以完整原文、明确CRLF/外空白归一，或实际收到的原JSON标量精确范围证明；保护只传播到对应实际接收之后。`ROUTE_PRODUCER_CLOSURE.json`保留所有证明，`SCREEN_PRODUCER_IDENTITY_INDEX.json`可复用原producer SHA映射。

原native未含显式thinking/reasoning块，与原provider-pair库也无responseId交集；该结论仅针对查到的载体，不能推成原全程没有思考。不能据最终包、工具ACK或自动通过状态赋予内容正loss。本轮未对受保护代码开展训练语义改写，不制造干净完整链。

核验由另一个parser重查完整原native、原字段变换、实际receipt范围、266/341等算术、对象SHA及所有复制资源，见`LOCAL_INTEGRITY_QA.json`。它是文件/归因核验，不是模型或整包效果证明。实际文件清单为`FINAL_ALLOWLIST.jsonl`和`FINAL_MANIFEST.json`，运行副产物pyc排除。
