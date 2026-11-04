from pathlib import Path
import json, subprocess, sys, shutil, time
def run(name,cmd,expected):
    t=time.monotonic();r=subprocess.run(cmd,cwd='/workspace',text=True,capture_output=True)
    Path('/workspace/qa_logs').mkdir(exist_ok=True)
    Path('/workspace/qa_logs/'+name+'.stdout.txt').write_text(r.stdout,encoding='utf-8')
    Path('/workspace/qa_logs/'+name+'.stderr.txt').write_text(r.stderr,encoding='utf-8')
    assert r.returncode==expected,(name,r.returncode,r.stdout,r.stderr)
    return {'name':name,'exit_code':r.returncode,'wall_seconds':time.monotonic()-t}
actions=json.loads(Path('/workspace/QA_ACTIONS.json').read_text())
cost=[]
cost.append(run('bad_batch',[sys.executable,'work/batch_runner.py'],0))
cost.append(run('bad_evidence_check',['/bin/bash','-c',actions['verify_exec']],1))
shutil.copytree('outputs','bad_outputs_archive')
Path('outputs/local_evidence_verification.json').rename('outputs/prior_failed_evidence_check.json')
cost.append(run('fixed_batch',['/bin/bash','-c',actions['runner_fix_exec']],0))
# Freeze all available before the independent evidence-check target. Future
# verification output and QA-driver files are deliberately not in this state.
state=Path('/workspace/verify_state_snapshot');state.mkdir()
for d in ['inputs','outputs','work']:shutil.copytree(d,state/d)
cost.append(run('fixed_evidence_check',['/bin/bash','-c',actions['verify_exec']],0))
report=Path('/workspace/outputs/report_repair_tests/dev_01/outputs/masking_report.json')
original=report.read_bytes()
for name,key,value in [('wrong_check5_hash','input_sha256','0'*64),('wrong_check6_selected','selected_cells',-1)]:
    obj=json.loads(original);idx=5 if name.startswith('wrong_check5')else 6
    obj['checks'][idx]['evidence'][key]=value;report.write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8')
    cost.append(run(name,['/bin/bash','-c',actions['verify_exec']],1));report.write_bytes(original)
cost.append(run('restored_evidence_check',['/bin/bash','-c',actions['verify_exec']],0))
Path('/workspace/RESOURCE_TOOL_QA.json').write_text(json.dumps({'status':'PASS','steps':cost,'agent_sessions':0,'model_calls':0,'training':False},indent=2))
