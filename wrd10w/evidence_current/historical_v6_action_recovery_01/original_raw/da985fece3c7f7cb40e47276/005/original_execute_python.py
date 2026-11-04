import shutil, hashlib, os, json
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''):
            h.update(c)
    return h.hexdigest()

os.makedirs('outputs/candidate/scripts', exist_ok=True)
os.makedirs('outputs/validation_history', exist_ok=True)

# 1) candidate copy
for rel in ['README.md','workflow_spec.json','scripts/run.py']:
    src=f'inputs/previous_candidate/{rel}'
    dst=f'outputs/candidate/{rel}'
    shutil.copy2(src,dst)
    print(rel, sha(src)==sha(dst), sha(dst))

# 2) learning evidence & plan
shutil.copy2('inputs/previous_learning_evidence.json','outputs/learning_evidence.json')
shutil.copy2('inputs/previous_candidate_plan.json','outputs/candidate_plan.json')
print('learning_evidence', sha('inputs/previous_learning_evidence.json')==sha('outputs/learning_evidence.json'))
print('candidate_plan', sha('inputs/previous_candidate_plan.json')==sha('outputs/candidate_plan.json'))

# 3) validation_history snapshot of original run.py + reason
shutil.copy2('inputs/previous_candidate/scripts/run.py','outputs/validation_history/run.py.original')
reason = {
  'snapshot_of': 'inputs/previous_candidate/scripts/run.py',
  'snapshot_file': 'outputs/validation_history/run.py.original',
  'sha256': sha('inputs/previous_candidate/scripts/run.py'),
  'bytes': os.path.getsize('inputs/previous_candidate/scripts/run.py'),
  'modification_reason': '报告JSON中checks[5](types_and_tables_preserved)证据缺少可定位的输入/输出文件路径与SHA，checks[6](counting_identity)证据引用了外部会话的绝对路径，导致检查器evidence_validation判定unverifiable_check_indices=[5,6]。本次将这两条证据改为结构化记录，包含本次实际计算的路径、SHA与计数，可由检查器重开文件复算。其余逻辑不变。',
  'date': '2026-10-19'
}
json.dump(reason, open('outputs/validation_history/reason.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)
print('snapshot done')