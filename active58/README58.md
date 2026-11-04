# WRD58可训练主集与课程

**版本5.0.58 / ALG-20261102-01。1260唯一目标、295478正监督tokens、241候选更新。**原来源与ID不增加；57版本完整保留。

默认入口为`TRAINING_ENTRYPOINT58.json`。依次核验其文件hash，按`COURSE58.json`逐step/microbatch读目标并应用明确的额外辅助系数。`CONFIG58.json`是未执行的配置合同，不是已启动的trainer。

## 数据与目录

- 401来源契约＋178旧过程＋54过程增量＋627辅助＝1260。
- 新33与57同ID/输入序列，保留原R2916/A19376/D19，只给31个schema有效且原native ACK的调用补650个F/.25。API5错误edit及API33终态保持原mask，不把错误参数合法化；新F范围另有独立审核。
- 原数组mass85003.30；默认budget10631405序列、934短/326长，互斥full21207839序列、532短/728长。两者目标/正token相同，0超32K。
- `banks/`完整保存21个原目标（2个小bank）及33目标替换bank需要的训练正文、数组和index；原base10与package11仍按`DATA_DEPENDENCIES58.json`绑定此前Git实体。原provider/SSE/raw轨迹从native57历史实体取得，不重复打包。

`ACTIVE_DATASET_MANIFEST58.json`和兼容文件名`ACTIVE_DATASET_MANIFEST57.json`内容逐字相同，都是58版本。PIN58/PIN57也是同内容。固定受审loader57仍按v1文件名读取，并以ENTRY58钉住的manifest hash和原parser SHA验证；并非借旧名绕过hash。其旧字段`course_schedule_for_new_active_ids`不参与58课程入口；实际课程始终由ENTRY58/CONFIG58的hash绑定。新root没有复制旧57默认ready或训练入口，`metadata_history58/`只保留本轮元数据清晰化前的真实构建回执，不作现行入口。

## 必须按课程应用loss

原bin中的辅助span权重仍为0.05。每个优化器step从未缩放权重计算M_real与M_aux，使用：

`alpha = min(1, M_real / (4*M_aux))`，M_aux=0时alpha=1。

课程`phase.steps[].auxiliary_extra_loss_scale`给出精确分数及float64；每个microbatch的`extra_course_loss_scale`为真实样本1、辅助样本alpha。不能只调用默认`iter_features`就声称20%已经应用；它返回原数组权重。

一个累积step的loss分子为全部正监督token的`original_span_weight × extra_course_scale × CE`之和；分母为该step全部非ignore shifted targets数，**不随alpha缩小**。每个microbatch可按该共同分母反向累积，但不得再由框架额外除accumulation，不能按权重和或各microbatch均值归一化。每个step只应用一次alpha，bin不得被改写或再次缩放。

92个过程step需要额外缩放，每步辅助有效系数mass≤20%。总课程effective mass84227.1375（原数组85003.30），其中辅助2091.9375/2.48369%；过程effective mass45744.4375，辅助占4.57310%，各step归一化系数之和中辅助占9.39425%。这些都是loss系数mass，不是CE贡献、梯度norm或Adam参数更新上限。

## 验证与checkpoint

`FEATURE_TO_COURSE_LOSS_QA58.json`从实际两profile四features读取1260目标并逐482个profile-step核对分母、mass、scale和cap；CPU变动per-token CE代理只用于数学合同检查，不能当模型loss或准确率。`INDEPENDENT_FEATURE_COURSE_QA58.json`另行重新读取实际features，核验ENTRY、相同正payload及课程不重缩放。

主课程仍单pass、26契约＋215过程，共241更新，同adapter/optimizer贯穿；每ID一次，尾批1/3真实flush，215过程批均有真实锚点。候选checkpoint为0/base、26、80、134、188、241，base不占更新；冻结dev的原生闭环TSR/Q/每合格技能成本选择checkpoint，test不参与选择。

14B主、8B对照，BF16 LoRA r32/alpha64/dropout0.05等原超参保持。原226及保留source/resource闭包隔离。当前没有加载学生模型、forward/backward或训练，也没有新增native业务采集。
