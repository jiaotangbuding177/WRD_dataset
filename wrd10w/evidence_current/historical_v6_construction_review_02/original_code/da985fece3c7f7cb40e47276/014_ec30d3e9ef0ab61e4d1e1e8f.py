import json, os, hashlib
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

trials = json.load(open('outputs/repair_trials.json', encoding='utf-8'))

candidate_files = {}
for rel in ['README.md','workflow_spec.json','scripts/run.py']:
    p = f'outputs/candidate/{rel}'
    candidate_files[rel] = {'path': os.path.abspath(p), 'sha256': sha(p), 'bytes': os.path.getsize(p)}

repair_summary = {
  'condition': '第五次报告证据修复（另行登记）；前四次共96接口条件失败，旧候选/失败/费用全部保留，本次不重置历史',
  'prior_status': {
    'previous_attempts_failed': 4,
    'previous_interface_conditions': 96,
    'retained': True,
    'business_checks_19_pass': True,
    'remaining_issue': '报告JSON中checks[5](types_and_tables_preserved)证据无可定位路径/SHA，checks[6](counting_identity)证据引用外部会话绝对路径，检查器evidence_validation判unverifiable_check_indices=[5,6]'
  },
  'this_attempt': {
    'copy_source': 'inputs/previous_candidate -> outputs/candidate（逐字节复制，含README.md/scripts/run.py/workflow_spec.json）',
    'learning_evidence': 'inputs/previous_learning_evidence.json -> outputs/learning_evidence.json（原样复制）',
    'candidate_plan': 'inputs/previous_candidate_plan.json -> outputs/candidate_plan.json（原样复制）',
    'modification_scope': '仅报告本体checks[5]/checks[6]两条证据改为结构化记录（含本次实际计算路径、SHA、计数），其余脱敏/类型/表格/schema逻辑未动',
    'run_py_sha256_before': 'ff3d3a67e75747d094983c0d652446b662f79225504e561daeea6603fc31d6b8',
    'run_py_sha256_after': candidate_files['scripts/run.py']['sha256'],
    'validation_history': ['outputs/validation_history/run.py.original', 'outputs/validation_history/reason.json', 'outputs/validation_history/changes.json']
  },
  'batch_runs': {
    'total': 9,
    'entry': 'python outputs/candidate/scripts/run.py --request <request.json> --output-root outputs/report_repair_tests/<id>[case_root]',
    'valid_processed': sum(1 for t in trials if t['result']=='processed_ok'),
    'invalid_refused': sum(1 for t in trials if t['result']=='refused_as_expected'),
    'per_case_isolated': True,
    'run_records': '每次实际返回码/stdout/stderr保存于 outputs/report_repair_tests/<id>/run_meta.json'
  },
  'independent_verification': {
    'method': '重开每次实际JSON报告与输入/输出工作簿，独立复算checks[5]的逐格data_type比对与表格定义比对、checks[6]的totals恒等式，并核对报告input_sha256/output_sha256/masking与实际文件',
    'result': '7/7有效请求全部复算一致且all checks PASS；2/2无效请求exit 2且未写任何输出',
    'detail_file': 'work/verification_pass.json'
  },
  'unresolved': [
    '未在原生Excel应用程序中做视觉渲染验证（沿用交付报告uncovered声明，非本次新增）',
    '公式仅做xlsx定义层面识别与保留，未做重算引擎结果验证',
    '检查器Q18对本次新结构化证据的最终判定未知，需外部验收确认'
  ],
  'trials_file': os.path.abspath('outputs/repair_trials.json')
}
json.dump(repair_summary, open('outputs/repair_summary.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)

candidate_manifest = {
  'manifest_version': 1,
  'candidate_root': os.path.abspath('outputs/candidate'),
  'files': [
    {'path': 'README.md', 'purpose': '公开候选说明（开发实例已清除）', **candidate_files['README.md']},
    {'path': 'scripts/run.py', 'purpose': '组合入口程序：--request 执行脱敏并输出工作簿与JSON报告（checks[5]/[6]证据为结构化可复算记录）', **candidate_files['scripts/run.py']},
    {'path': 'workflow_spec.json', 'purpose': '8节点workflow规范', **candidate_files['workflow_spec.json']}
  ],
  'consumed_resources': [],
  'excluded_from_public_candidate': [
    '测试与开发附件（inputs/development_cases/**, inputs/dev_input.xlsx, inputs/dev_request.json）',
    '原值/答案/学习证据（outputs/learning_evidence.json、outputs/candidate_plan.json 为登记文件，不作为消费资源）',
    'outputs/report_repair_tests/**（本次试验产物）'
  ],
  'evidence': {
    'trials': os.path.abspath('outputs/repair_trials.json'),
    'repair_summary': os.path.abspath('outputs/repair_summary.json'),
    'reports': [t['report_file'] for t in trials if t['result']=='processed_ok'],
    'all_valid_runs_all_checks_pass': True,
    'invalid_runs_refused_exit2': True
  },
  'open_items': [
    'Q18对checks[5]/[6]新结构化证据的最终核验结果待外部检查器确认'
  ]
}
json.dump(candidate_manifest, open('outputs/candidate_manifest.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)
print('repair_summary.json + candidate_manifest.json written')
print(json.dumps(candidate_files, ensure_ascii=False, indent=1))