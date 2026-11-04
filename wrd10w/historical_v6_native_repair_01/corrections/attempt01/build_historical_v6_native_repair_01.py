"""Build explicit new-author native action projections from two old repairs.

Never invokes an Agent, a model, the old controller, or any training code. The
optional bounded resource QA runs only supplied Python CLIs in the fixed image.
"""
from __future__ import annotations
import argparse, ast, gzip, hashlib, json, shutil, subprocess, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261027_wrd_main_v10/historical_v6_native_repair_01'
OLD=ROOT/'output/20261026_wrd_sequences_v6/controlled'
AUDIT=ROOT/'output/20261027_wrd_main_v10/historical_v6_reuse_audit_01'
IMAGE='sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
SCHEMA='wrd-historical-semantic-native-adaptation-v1'
IDS=['0753780cad3b696a12766199','0ef558c25137e296148ca0cc','82b9c29cc2544f668555c7d2','998b0849c7513f3cc55d5126']

def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8-sig')as f:
        for line in f:
            if line.strip():yield json.loads(line)
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def dump(p,values):
    p.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(p,'wt',encoding='utf-8',newline='\n')as f:
        for v in values:f.write(js(v)+'\n')
def pin(p):return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':digest(p)}
def cp(p,d):d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
def code(r):return json.loads(r['original_response']['choices'][0]['message']['tool_calls'][0]['function']['arguments'])['code']
def old_contexts():return {r['pair_id']:r for r in rows(OLD/'admitted.reasoning_source_contexts.jsonl.gz')if r['pair_id']in IDS}
def readtxt(p):return p.read_bytes().decode('utf-8')

def prepare():
    assert not (OUT/'PREPARED.json').exists(),'never overwrite an existing release'
    OUT.mkdir(parents=True,exist_ok=True);contexts=old_contexts();r=contexts[IDS[0]]
    scoped=next(x for x in rows(ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz')if x['source_id']=='conv_b5e6f3d3bab9')
    assert scoped['status']=='TRAIN'
    copies={c['destination']:c for c in r['parent_run_record']['observed_input_packet']['copies']}
    common=OUT/'resources/common';source_pins=[]
    for dest,c in copies.items():
        if dest in {'inputs/task_contract.json','inputs/dev_request.json','inputs/dev_input.xlsx','inputs/development_cases.json'}or dest.startswith('inputs/development_cases/'):
            p=Path(c['copy']['path']);assert digest(p)==c['copy']['sha256']==c['source']['sha256'];cp(p,common/dest)
            source_pins.append({**pin(p),'destination':dest,'role':'ORIGINAL_DISPATCHED_SYNTHETIC_DEV_OR_PUBLIC_CONTRACT'})
    helper=Path(__file__).with_name('historical_v6_local_evidence_check.py');cp(helper,common/'inputs/local_evidence_check.py')
    source_pins.append({**pin(helper),'destination':'inputs/local_evidence_check.py','role':'NEW_AUTHORED_FINITE_QA_RESOURCE_NOT_TEACHER_RECORD'})
    oldpin=copies['inputs/previous_candidate/scripts/run.py']['copy'];oldp=Path(oldpin['path']);assert digest(oldp)==oldpin['sha256']
    oldprogram=oldp.read_bytes();tree=ast.parse(code(r));aa={n.targets[0].id:n.value for n in tree.body if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Name)}
    lines=oldprogram.decode('utf-8').split('\r\n');edits=[]
    for name,new in [('i5','new5'),('i6','new6')]:
        needle=next(n.value for n in ast.walk(aa[name])if isinstance(n,ast.Constant)and isinstance(n.value,str))
        matches=[s for s in lines if needle in s];assert len(matches)==1
        edits.append({'oldText':matches[0],'newText':'\r\n'.join(ast.literal_eval(aa[new]))})
    newprogram=oldprogram.decode('utf-8')
    for edit in edits:assert newprogram.count(edit['oldText'])==1;newprogram=newprogram.replace(edit['oldText'],edit['newText'])
    newbytes=newprogram.encode('utf-8');assert sha(newbytes)=='43ab93fb0ba3ffc205415f15df8e82d836c44d741d8a67be1c03da70b5d67b19'
    assert sha(oldprogram)=='ff3d3a67e75747d094983c0d652446b662f79225504e561daeea6603fc31d6b8'
    bad=code(contexts[IDS[3]]);ast.parse(bad)
    oldline='    outroot = os.path.join(run_root, cid)\n'
    newline="    outroot = os.path.join(run_root, cid) if cid == 'original_recovery' else os.path.join(run_root, cid, 'case_root')\n"
    assert bad.count(oldline)==1;fixed=bad.replace(oldline,newline);ast.parse(fixed)
    # Bind the mapping to the actually recorded successful correction. The new
    # projection does not copy its unrelated directory deletion or explanation.
    original_fixed=code(contexts[IDS[1]])
    assert "outroot = os.path.join(run_root, cid) if cid == 'original_recovery' else os.path.join(run_root, cid, 'case_root')"in original_fixed
    fix_command="set -e\npython - <<'PY'\nfrom pathlib import Path\np = Path('/workspace/work/batch_runner.py')\ns = p.read_text(encoding='utf-8')\nold = "+repr(oldline)+"\nnew = "+repr(newline)+"\nassert s.count(old) == 1\np.write_text(s.replace(old, new), encoding='utf-8')\nPY\npython /workspace/work/batch_runner.py"
    verify_command='python /workspace/inputs/local_evidence_check.py --cases /workspace/inputs/development_cases.json --baseline /workspace/inputs/dev_request.json --meta-root /workspace/outputs/report_repair_tests --report /workspace/outputs/local_evidence_verification.json'
    states=OUT/'states'
    for name,program in [('report_edit',oldprogram),('runner_fix',newbytes)]:
        shutil.copytree(common,states/name);d=states/name/'outputs/candidate/scripts/run.py';d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(program)
    (states/'runner_fix/work').mkdir(parents=True);(states/'runner_fix/work/batch_runner.py').write_text(bad,encoding='utf-8')
    audit=OUT/'audit_only';audit.mkdir(exist_ok=True)
    feedback=Path(copies['inputs/report_repair_feedback.json']['copy']['path']);f=load(feedback)
    functional_feedback={'business_status':'本次仅修报告证据的可定位与可复算性；UNKNOWN不等于工作簿业务计算已证错误。',
        'report_findings':[{'case_id':x['id'],'exit_code':x['exit_code'],'checks':x['all_nonpassing_checks']}for x in f['actual_development_results']],
        'check5_previous_evidence':f['actual_report_checks'][5]['evidence'],
        'required_evidence':'检查5在本次报告中记录可重开输入/输出路径、各自SHA、逐格类型比较数量及表定义数量/相同与否；检查6记录当前totals、各组成之和、selected及恒等式布尔。保留现有业务计算和拒绝规则。'}
    save(common/'inputs/report_feedback.functional.json',functional_feedback)
    for name in ['report_edit','runner_fix']:
        cp(common/'inputs/report_feedback.functional.json',states/name/'inputs/report_feedback.functional.json')
    # Preserve original observations verbatim outside the training input.
    oldmsgs=contexts[IDS[1]]['original_request']['messages'];diag=[{'message_index':i,'message':m}for i,m in enumerate(oldmsgs)if i in [15,17,19]]
    save(audit/'ORIGINAL_RUNNER_OBSERVATIONS.json',diag)
    cp(feedback,audit/'report_repair_feedback.original.json')
    for pid,c in contexts.items():
        save(audit/(pid+'.original_current_response.json'),c['original_response'])
        source_pins.extend({**x,'role':'ORIGINAL_REQUEST_RESPONSE_DEPENDENCY_ALREADY_OLD_GIT'}for x in c['source_file_dependencies'])
    schema_source=load(ROOT/'output/20261027_wrd_main_v10/real_state_reconstruction_02/SOURCE_RECEIPTS.json')
    first=next(rows(ROOT/'output/20261027_wrd_main_v10/real_state_reconstruction_02/real_state_tasks.jsonl.gz'))
    capture=Path(first['tool_schema_provenance']['path']);assert digest(capture)==first['tool_schema_provenance']['sha256'];tools=load(capture)['tools'];assert len(tools)==53
    save(OUT/'TOOLS_CAPTURE_53.json',{'tools':tools,'original_capture':pin(capture),'native_image':IMAGE,'openclaw_version':'2026.9.5'})
    save(OUT/'OFFLINE_ACTIONS.json',{'report_edits':edits,'runner_old_line':oldline,'runner_new_line':newline,
        'runner_fix_exec':fix_command,'verify_exec':verify_command,'old_program_sha256':sha(oldprogram),'new_program_sha256':sha(newbytes),
        'bad_runner_sha256':sha(bad.encode()),'fixed_runner_sha256':sha(fixed.encode()),
        'projection_marker':'NEW_AUTHORED_NATIVE_ACTION_PROJECTION_VERIFIED_OFFLINE','actual_native_tool_dispatch':False})
    save(OUT/'SOURCE_RECEIPTS.json',{'schema_version':SCHEMA,'source_ids':['conv_b5e6f3d3bab9'],'source_group_id':scoped['component_id'],
        'split':'train','current_scope':scoped,'source_pins':source_pins,'original_feedback':pin(feedback),
        'original_177_closure_audit':pin(AUDIT/'MANIFEST.json'),'old_Git_exact_members':pin(AUDIT/'OLD_GIT_ARCHIVE_MEMBER_REUSE.json'),
        'original_canonical_owners':[{'pair_id':pid,'tool_call_id':contexts[pid]['original_response']['choices'][0]['message']['tool_calls'][0]['id']}for pid in IDS[:3]],
        'old_context_original_Git_member':'sequences/controlled/admitted.reasoning_source_contexts.jsonl.gz',
        'original_context_sha256':digest(OLD/'admitted.reasoning_source_contexts.jsonl.gz'),
        'new_full_old_file_delivery_not_original_request_identity':True,'old_original_partial_feedback_not_claimed_full_model_delivery':True,
        'new_author_annotation_cost':'UNKNOWN_NOT_ZERO','cash_cost':'UNKNOWN_NOT_ZERO','training_started':False})
    save(OUT/'PREPARED.json',{'status':'PREPARED_FOR_FINITE_TOOL_RESOURCE_QA','image':IMAGE,'source_ids':['conv_b5e6f3d3bab9'],'script':pin(Path(__file__)),
        'source_old_program':pin(oldp),'no_agent_or_model_execution':True,'new_positive_main_labels':0})
    print('PREPARED',OUT)

def run_resource_qa():
    assert (OUT/'PREPARED.json').exists()and not (OUT/'RESOURCE_QA.json').exists()
    osmem=subprocess.run(['powershell','-NoProfile','-Command','(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory*1024'],capture_output=True,text=True,check=True)
    available=int(osmem.stdout.strip());assert available>=7*1024**3,('host_below_7GiB',available)
    ps=subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True,check=True)
    native=sum(n.startswith('skillloop-eval-')for n in ps.stdout.splitlines());assert native<8
    qa=OUT/'resource_qa';qa.mkdir();work=qa/'workspace';shutil.copytree(OUT/'states/runner_fix',work)
    (work/'qa_driver.py').write_text('''from pathlib import Path
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
''',encoding='utf-8')
    cp(OUT/'OFFLINE_ACTIONS.json',work/'QA_ACTIONS.json')
    image=subprocess.run(['docker','image','inspect',IMAGE,'--format','{{.Id}}'],capture_output=True,text=True,check=True).stdout.strip();assert image==IMAGE
    argv=['docker','run','--rm','--network','none','--memory','6g','--cpus','4','--shm-size','1g','--mount',f'type=bind,source={work.resolve()},target=/workspace','--workdir','/workspace','--entrypoint','/opt/eval-venv/bin/python',IMAGE,'/workspace/qa_driver.py']
    start=time.time();r=subprocess.run(argv,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (qa/'container.stdout.txt').write_text(r.stdout,encoding='utf-8');(qa/'container.stderr.txt').write_text(r.stderr,encoding='utf-8')
    save(OUT/'RESOURCE_QA_ATTEMPT.json',{'argv':argv,'host_available_bytes_before':available,'native_container_count_before':native,
        'exit_code':r.returncode,'wall_seconds':time.time()-start,'image':image,'agent_sessions':0,'model_calls':0,'training':False,
        'OpenClaw_tool_dispatch_performed':False,'CPU_resource_QA_cost':'MEASURED_WALL_TIME_ONLY_CPU_ACCOUNTING_AND_CASH_UNKNOWN_NOT_ZERO'})
    assert r.returncode==0,(r.stdout,r.stderr)
    shutil.copytree(work/'verify_state_snapshot',OUT/'states/verify_local')
    qaresult=load(work/'RESOURCE_TOOL_QA.json');qaresult['execution_receipt']=pin(OUT/'RESOURCE_QA_ATTEMPT.json')
    save(OUT/'RESOURCE_QA.json',qaresult);print('RESOURCE_QA PASS',qaresult['steps'])

def finalize():
    assert load(OUT/'RESOURCE_QA.json')['status']=='PASS'and not (OUT/'native_adaptation.core7.jsonl.gz').exists()
    sr=load(OUT/'SOURCE_RECEIPTS.json');a=load(OUT/'OFFLINE_ACTIONS.json');capture=load(OUT/'TOOLS_CAPTURE_53.json');alltools=capture['tools']
    core=[t for t in alltools if t['function']['name']in {'apply_patch','edit','exec','ls','process','read','write'}]
    assert len(core)==7;proof={'path':str((OUT/'TOOLS_CAPTURE_53.json').resolve()),'sha256':digest(OUT/'TOOLS_CAPTURE_53.json')}
    common=OUT/'resources/common';contract=readtxt(common/'inputs/task_contract.json');cases=readtxt(common/'inputs/development_cases.json')
    bad=readtxt(OUT/'states/runner_fix/work/batch_runner.py');fixed=readtxt(OUT/'states/verify_local/work/batch_runner.py')
    assert sha(bad.encode())==a['bad_runner_sha256']and sha(fixed.encode())==a['fixed_runner_sha256']
    goal='总目标：从获准会话中的字段脱敏任务沉淀可靠可复用的Excel资源。当前只修复可定位复算的报告证据及本地测试隔离；局部通过不能决定技能保留或成本收益。\n'
    environment='工作目录 /workspace。Python /opt/eval-venv/bin/python，OpenClaw2026.9.5。可以读取inputs，在outputs和work修订及执行本地CLI；inputs只读，无网络、外发或子Agent权限。总时限1800秒、max_tokens32768；本状态的已用量和剩余预算UNKNOWN。没有活动后台进程。附件均为已披露的合成DEV工作簿，不宣称历史原附件等价。\n'
    def block(path,text):return '\n完整文本文件 '+path+'：\n<file>\n'+text+'\n</file>\n'
    paths=[]
    for p in sorted(common.rglob('*')):
        if p.is_file():paths.append({'path':'/workspace/'+p.relative_to(common).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p),
            'binary':p.suffix=='.xlsx'})
    manifest='已实际投递的只读资源（完整二进制文件存在，可由CLI重开；以下不是其文本替代）：\n'+json.dumps(paths,ensure_ascii=False,indent=2)+'\n'
    base=goal+environment+block('/workspace/inputs/task_contract.json',contract)+manifest
    feedback=readtxt(common/'inputs/report_feedback.functional.json')
    u1=base+'当前状态：旧候选已完整复制到outputs/candidate，尚未做本次两证据局修；以下是该当前文件的完整正文。开发反馈仅指出检查5/6的报告证据UNKNOWN，不要求改变已工作的业务规则。\n'+block('/workspace/outputs/candidate/scripts/run.py',readtxt(OUT/'states/report_edit/outputs/candidate/scripts/run.py'))+block('/workspace/inputs/report_feedback.functional.json',feedback)+'选择下一步局部动作。'
    diag='原批量执行7个有效请求均exit0、2个无效请求exit2；但重开产物时dev_01/dev_02出现input_sha、masking、check5_recompute不符，dev_03重开报KeyError: Worksheet 本期客户 does not exist。已查看dev_01/02/03请求，输出均为../outputs/masked.xlsx及../outputs/masking_report.json，原对应case目录只有run_meta.json。此为已发生的失败观察摘要，不能把exit0当隔离成功。\n'
    u2=base+'当前状态：报告两证据局修已应用；首次批测的隔离失败待修，未运行修后批测。仅针对给定9个DEV请求修runner，不重构业务程序，也不删原失败。\n'+diag+block('/workspace/outputs/candidate/scripts/run.py',readtxt(OUT/'states/runner_fix/outputs/candidate/scripts/run.py'))+block('/workspace/work/batch_runner.py',bad)+block('/workspace/inputs/development_cases.json',cases)+block('/workspace/inputs/dev_request.json',readtxt(common/'inputs/dev_request.json'))+'路径约定：baseline原请求的相对输出不含父级，DEV请求的相对输出为../outputs。修订runner使每个case的解析结果处于各自目录；然后真实重跑并保存各自run_meta，尚不宣称独立重算通过。'
    ledger=[]
    for p in sorted((OUT/'states/verify_local/outputs/report_repair_tests').glob('*/run_meta.json')):
        x=load(p);ledger.append({k:x[k]for k in ['id','exit_code','request','output_root']})
    assert len(ledger)==9 and sum(x['exit_code']==0 for x in ledger)==7 and sum(x['exit_code']==2 for x in ledger)==2
    u3=base+'当前状态：给定runner已修订，9次实际进程记录如下；7个有效exit0、2个无效exit2，仅说明进程退出状态。尚未运行下述独立重开证据检查。实际报告与工作簿、各case的run_meta完整文件已经在对应输出目录。\n'+json.dumps(ledger,ensure_ascii=False,indent=2)+block('/workspace/outputs/candidate/scripts/run.py',readtxt(OUT/'states/verify_local/outputs/candidate/scripts/run.py'))+block('/workspace/work/batch_runner.py',fixed)+block('/workspace/inputs/local_evidence_check.py',readtxt(common/'inputs/local_evidence_check.py'))+block('/workspace/inputs/development_cases.json',cases)+'使用已提供检查程序对真实产物做有限核验，保留失败细节；不要由退出码或旧PASS推断本次证据正确。'
    specs=[('report_edit',IDS[0],u1,'检查5/6仍只有文字证据，当前旧程序完整可见。仅把这两条证据改为本次路径、SHA和真实计数的结构化记录，保留业务计算、状态判据和拒绝逻辑。','edit',{'path':'/workspace/outputs/candidate/scripts/run.py','edits':a['report_edits']}),
        ('runner_fix',IDS[1],u2,'失败观察和请求路径共同指向输出目录合流：case目录下的../outputs落到了共享父目录。针对已给定的baseline与DEV请求，用case_root承接DEV的父级，再重跑9例保留逐次进程记录。','exec',{'command':a['runner_fix_exec'],'workdir':'/workspace','title':'修复给定批测的输出隔离并重跑','timeoutSeconds':120}),
        ('verify_local',IDS[2],u3,'9次进程退出符合预期还不足以确认报告正确。用已提供的独立检查逐例重开输入、输出和JSON，重新计算目标值、计数、类型及表定义，并将检查5/6的每个证据对象与本次文件绑定；这只给局部资源信用。','exec',{'command':a['verify_exec'],'workdir':'/workspace','title':'重开实际产物复算局部报告证据','timeoutSeconds':120})]
    core_records=[];full_records=[];exposure=[]
    system='你在原生OpenClaw环境中把已获准任务的工作路线制作成可复用技能。按完整目标、当前资源与真实观察选择下一项本地动作；精确编辑需掌握正文，遇到失败先定位原因。区分局部核验、整体语义质量及实际消费收益。'
    for name,pid,user,rationale,tool,args in specs:
        owner=next(o for o in sr['original_canonical_owners']if o['pair_id']==pid)
        target={'role':'assistant','content':'','reasoning_content':rationale,'tool_calls':[{'id':'call_v6_adapt_'+name,'type':'function','function':{'name':tool,'arguments':js(args)}}]}
        rec={'schema_version':SCHEMA,'id':'historical_v6_native_repair_01:'+name+':core7','bank':'historical_v6_native_repair_01',
            'stage':'B_historical_local_resource_repair','source_ids':sr['source_ids'],'source_group_id':sr['source_group_id'],
            'split':'train','source_admission':'ADMIT','training_admitted':True,'root_main_admission':False,
            'admission_scope':'AUTHOR_LOCAL_SILVER_FOR_CPU_COMPILATION_PENDING_ROOT','annotation_provenance':'NEW_AUTHORED_NATIVE_ACTION_PROJECTION_VERIFIED_OFFLINE',
            'rationale_provenance':'NEW_AUTHORED_CONCISE_RATIONALE_NOT_ORIGINAL_TEACHER_COT','loss_multiplier':0.25,'approved_components':['R','A'],
            'messages':[{'role':'system','content':system},{'role':'user','content':user},target],'message_loss_mask':[0,0,1],'supervision_message_indices':[2],
            'tools':core,'tool_schema_provenance':proof,'original226':False,'holdout12':False,'protected_sources_visible_prefix':False,
            'is_original_native_request_identical':False,'is_original_native_next_action_identical':False,'is_full_autonomous_execution_demonstration':False,
            'student_view':'EXPLICIT_CORE7_PROJECTION_FROM_ACTUAL_FIXED_53_SCHEMA','new_input_author':'Codex silver annotation','human_gold':False,
            'target_owner':{'canonical_original_action_owner_id':'historical_v6:'+owner['tool_call_id'],'original_pair_id':pid,
                'original_tool_call_id':owner['tool_call_id'],'new_projection_tool_call_id':target['tool_calls'][0]['id'],
                'exposure_owner_id':'historical_v6:'+owner['tool_call_id'],'same_original_action_views_mutually_exclusive':True},
            'resource_state_path':str((OUT/'states'/name).resolve()),'resource_state_has_full_files':True,
            'original_visible_explanation_E_reused':False,'original_hidden_reasoning_reused':False,'actual_native_tool_dispatch':False,
            'native_action_projection_status':'NEW_AUTHORED_NATIVE_ACTION_PROJECTION_VERIFIED_OFFLINE','future_outcomes_metadata_only':True,
            'functional_state_contains_explicit_new_full_resource_delivery_not_teacher_request_equivalence':True,
            'new_state_has_no_future_verification_report':not (OUT/'states'/name/'outputs/local_evidence_verification.json').exists(),
            'independent_resource_QA':str((OUT/'RESOURCE_QA.json').resolve()),'budget':{'total_seconds':1800,'max_output_tokens':32768,'used':'UNKNOWN','remaining':'UNKNOWN'},
            'new_author_annotation_cost':'UNKNOWN_NOT_ZERO','training_started':False,'weights_loaded':False}
        assert rec['new_state_has_no_future_verification_report']
        if name=='report_edit':
            for patch in args['edits']:assert patch['newText']not in user,'future_patch_leaked'
        if name=='runner_fix':assert a['runner_new_line']not in user,'future_runner_patch_leaked'
        core_records.append(rec)
        full={**rec,'id':rec['id'].replace(':core7',':full53'),'tools':alltools,'student_view':'FULL_ACTUAL_53_SCHEMA_NEW_AUTHORED_STATE','default_active':False}
        full_records.append(full);exposure.append({'owner':rec['target_owner'],'views':[rec['id'],full['id']],
            'mutually_exclusive_with':['old v6 same action positive labels','other new adaptations of same original action'],'new_independent_source_count':0})
    dump(OUT/'native_adaptation.core7.jsonl.gz',core_records);dump(OUT/'native_adaptation.full53.jsonl.gz',full_records)
    save(OUT/'EXPOSURE_OWNERS.json',{'schema_version':SCHEMA,'owners':exposure,'old76_and_old_AD_not_automatically_supervised':True})
    save(OUT/'CAUSAL_CONTRACT.json',{'schema_version':SCHEMA,'design_revision':'5.0.41','change_id':'ALG-20261027-05',
        'chain':['actual old Q18 UNKNOWN5/6 and complete old program -> new authored native edit -> exact new43ab program',
            'actual old shared-root failures plus bad runner and given requests -> new authored native exec local correction/rerun',
            'new actual same-image CLI run receipts and full files -> independent evidence-check next action; its future PASS is metadata only'],
        'first_state_full_feedback_delivery_change':'New state supplies a disclosed functional feedback projection and full old program, not an assertion that the original model saw the full15903byte feedback file.',
        'runner_file_reification':'The old execute_python action code is newly materialized as work/batch_runner.py; that filename was not a historical native tool resource.',
        'verification_helper':'New finite resource QA program; original82 revalidation intent is transferred, original helper code is not mislabelled native execution.',
        'original_R_and_E':'All historical original reasoning/explanation remains preserved in prior Git; this bank has only explicitly new authored conciseR and action projections.',
        'known_claim_limits':['three local process targets from one source, not three skills or new independent tasks','no retain or cost benefit demonstrated','no student capability evaluated','no native Agent or model action occurred'],
        'root_main_admission':False,'training_started':False})
    print('FINALIZED 3 targets; root pending')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','resource-qa','finalize']);args=ap.parse_args()
    {'prepare':prepare,'resource-qa':run_resource_qa,'finalize':finalize}[args.action]()
