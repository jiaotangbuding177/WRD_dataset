# 实际阶段覆盖与恢复优先级

2026-10-29，实际529目标／146069监督tokens；契约436、过程93，过程仅12来源／9联合component。

| 实际stage | 目标 | 监督tokens |
|---|---:|---:|
| A_source_contract_management | 429 | 73295 |
| A_current_user_delta_checkpoint | 7 | 1463 |
| A_screen | 1 | 2742 |
| B_make | 1 | 2460 |
| B_revision_real_state_reproduce | 1 | 332 |
| B_revision_real_state_repair | 1 | 1676 |
| B_revision_real_state_retest | 1 | 306 |
| C_trial_skill | 2 | 781 |
| C_review | 1 | 387 |
| D_new_post_terminal_state | 1 | 290 |
| historical_workflow_design_diagnosis_and_falsifiable_plan | 26 | 33153 |
| B_historical_local_resource_repair | 3 | 1098 |
| B_make_CV_extract_evidence_process | 21 | 6469 |
| B_make_HTML_animation_resource_process | 27 | 14193 |
| B_new_state_complete_verified_resource_write | 4 | 4511 |
| B_historical_style_verifier_repair | 1 | 174 |
| B_historical_helpers_resource_construction | 1 | 1891 |
| B_test_oracle_diagnosis_and_revision | 1 | 848 |

token component_D是正文类别，不能当作pipeline D封装覆盖。原生自主A—D示范0、正向合格保留0、独立dev/test数组0，整体训练NOT_READY。当前可用于组件学习的假设与反证见TRAINING_PLAN。

扩充顺序：其它干净来源的完整资源→真实失败归因／局修→同版本复试及独立质量→正向合格封装／反向STOP→原生自主调度。原226／H／静态dev-test继续隔离，未知保留，不靠重放或切窗补独立数据。
