"""Prepare bounded version/feedback-grounded repair projections for root review.

Only CPU checks on isolated literal verifier fragments are run. No captured
shell, old Agent, model, training or original task workspace is executed/edited.
Original native code, failures and successful later output remain separately pinned.
"""
from pathlib import Path
from collections import Counter
from copy import deepcopy
from types import SimpleNamespace
import ast,gzip,hashlib,importlib.util,json,os

ROOT=Path('D:/skillloop');WORK=ROOT/'output/20261031_wrd_curation10';OUT=WORK/'identity_semantic'
DATA=ROOT/'output/20261027_wrd_main_v10'

def h(x):return hashlib.sha256(x if isinstance(x,bytes)else x.encode()).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':h(b)}
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for line in f:
   if line.strip():yield json.loads(line)
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode())
def text(m):return m.get('content','')if isinstance(m.get('content'),str)else'\n'.join(b.get('text','')for b in m.get('content',[])if b.get('type')=='text')
def call(m):return next(b for b in m['content']if b.get('type')=='toolCall')
def args(c):return json.loads(c['arguments'])if isinstance(c['arguments'],str)else c['arguments']
def local_heredoc_python(command):
 assert "<<'EOF'\n"in command
 return command.split("<<'EOF'\n",1)[1].split('\nEOF',1)[0]

def main():
 assert not (OUT/'CANDIDATES.raw.jsonl.gz').exists()
 OUT.mkdir(parents=True,exist_ok=True)
 sources=['conv_2ff337f34ddc','conv_ce34559870b8','conv_d640957a9820']
 scopes={r['source_id']:r for r in rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
 assert all(scopes[s]['status']=='TRAIN'for s in sources)
 reserved=load(WORK/'parent_inputs/reservation.json');assert not set(sources)&set(__import__('re').findall('conv_[0-9a-f]{12}',js(reserved)))
 root=WORK/'identity/recovered_native'
 gen=root/'native_recovered10_34372b2c-6560-4e50-9a3d-cf5a14318296'
 rep=root/'native_b8d96350-2801-46e6-8f61-333c6a15c2e0'
 ctx=next(rows(gen/'CONTEXT.original.audit.jsonl.gz'));ms=ctx['messages']
 repair=next(rows(rep/'CONTEXT.original.audit.jsonl.gz'))
 source0=args(call(ms[53]))['content'];assert len(source0)==4549
 # Parse only literal replacement arguments; captured Python/shell is not run.
 tree57=ast.parse(local_heredoc_python(args(call(ms[57]))['command']))
 pairs=[]
 for n in ast.walk(tree57):
  if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='replace'and len(n.args)==2:
   pairs.append(tuple(ast.literal_eval(z)for z in n.args))
 assert len(pairs)==2
 source1=source0
 for old,new in pairs:
  assert source1.count(old)==1
  source1=source1.replace(old,new)
 tree59=ast.parse(local_heredoc_python(args(call(ms[59]))['command']))
 constants={n.targets[0].id:ast.literal_eval(n.value)for n in tree59.body if isinstance(n,ast.Assign)
    and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)and n.targets[0].id in {'old','new'}}
 old,new=constants['old'],constants['new'];assert source1.count(old)==1
 source2=source1.replace(old,new)
 for s in [source0,source1,source2]:ast.parse(s)
 finalpath=Path('E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/native_episodes/meeting-minutes-formatting_gen_02/workspace/outputs/making_history/replay_verify.py')
 assert finalpath.read_bytes()==source2.encode(), 'LITERAL_TWO_PATCH_CHAIN_MUST_REBUILD_FINAL_FILE_EXACTLY'
 for name,body in [('verifier_before_path_fix.py',source0),('verifier_after_path_fix.py',source1),('verifier_after_stderr_fix.py',source2)]:
  (OUT/name).write_bytes(body.encode())
 # Local CPU counterexamples are independent of the formatter and replay score.
 # Only the original check_assertion function is evaluated on task-owned data.
 function_nodes=[n for n in ast.parse(source0).body if isinstance(n,ast.FunctionDef)and n.name in {'expand','check_assertion'}]
 namespace={'os':os,'json':json,'zipfile':__import__('zipfile'),'SKILL':'/workspace/outputs/candidate/skill',
   'FIXTURE':'/workspace/outputs/reproduction_inputs','OUT':'/tmp/replay_verify'}
 exec(compile(ast.Module(body=function_nodes,type_ignores=[]),'<original-verifier-check_assertion>','exec'),namespace)
 check=namespace['check_assertion'];cpu=OUT/'cpu_checks'/'run02';cpu.mkdir(parents=True,exist_ok=False)
 assert cpu.resolve().is_relative_to(OUT.resolve())
 pathout=cpu/'path';pathout.mkdir();(pathout/'format_summary.json').write_text('{"ok": true}',encoding='utf-8')
 spec={'kind':'json_equals','path':'format_summary.json','value':{'ok':True}}
 before_dir=pathout/'case_normal_0';before_dir.mkdir()
 before_failed=False
 try:check(spec,str(before_dir))
 except FileNotFoundError:before_failed=True
 assert before_failed and check(spec,str(pathout))is True
 # Reproduce expected-invalid exit==2: the old branch did not write stderr.
 def probe(block,folder,returncode,expected):
  folder.mkdir();assert folder.resolve().is_relative_to(cpu.resolve())
  env={'os':os,'cp':SimpleNamespace(returncode=returncode,stdout='actual stdout\n',stderr='error: input file not found\n'),
    'case':{'expected_exit':expected,'assertions':[{'kind':'contains','path':'stderr.txt','value':'input file not found'}]},
    'outdir':str(folder),'ok_all':True,'check_assertion':check}
  error=None
  try:exec(compile(__import__('textwrap').dedent(block),'<isolated-original-verifier-branch>','exec'),env)
  except FileNotFoundError:error='FileNotFoundError'
  return {'exception':error,'exit_ok':env.get('exit_ok'),'checks':env.get('checks'),
    'stderr_file_exists':(folder/'stderr.txt').is_file(),
    'actual_stderr_retained_exact':(folder/'stderr.txt').read_text(encoding='utf-8')==env['cp'].stderr if (folder/'stderr.txt').is_file()else False}
 oldprobe=probe(old,cpu/'stderr_before',2,2);newprobe=probe(new,cpu/'stderr_after',2,2)
 mismatch=probe(new,cpu/'exit_mismatch',0,2)
 assert oldprobe['exception']=='FileNotFoundError'
 assert newprobe['exception']is None and newprobe['exit_ok']and newprobe['checks'][0]['ok']and newprobe['actual_stderr_retained_exact']
 assert mismatch['exit_ok']is False,'NEW_PATCH_MUST_NOT_REDEFINE_EXPECTED_EXIT_TO_HIDE_FAILURE'
 original_feedback={'path_fix_failure':text(ms[56]),'after_path_fix_new_error':text(ms[58]),'after_stderr_fix_actual_result':text(ms[60])}
 assert 'format_summary.json'in original_feedback['path_fix_failure']and'stderr.txt'in original_feedback['after_path_fix_new_error']
 assert 'ALL_OK'in original_feedback['after_stderr_fix_actual_result']
 # Accurate old HOLD paragraph is used only in a new explicit functional state.
 original_end=text(repair['messages'][112]);needle='候选**未完成、未自评通过**：'
 assert needle in original_end
 hold=original_end.split(needle,1)[1];hold=needle+hold
 old_workspace=Path('E:/skillloop_runs/w4/native_episodes/meeting-minutes-formatting__repair1/workspace/outputs')
 missing={name:not(old_workspace/name).exists()for name in ['resource_manifest.json','evidence.json']}
 assert all(missing.values())
 replay=load(old_workspace/'replay.json')
 assert 'generated_fixture'in js(replay)and ('未恢复'in js(replay)or'not'in js(replay).lower()or'未知'in js(replay))
 # Tools and system are taken from a real currently captured native request.
 template=next(rows(WORK/'early_reads/CANDIDATES.raw.jsonl.gz'))
 tools=deepcopy(template['tools']);system=deepcopy(template['messages'][0]);assert system['role']=='system'
 assert {t['function']['name']for t in tools}=={'ls','read','write','edit','apply_patch','exec','process'}
 provenance=template['tool_schema_provenance'];assert pin(provenance['path'])['sha256']==provenance['sha256']
 group='v10_native_group_'+h(js(sorted(sources)))[:20]
 candidates=[];review=[]
 def common(identity,owner,index,stage,components,user,assistant,bank,rationale_provenance):
  messages=[deepcopy(system),{'role':'user','content':user},assistant]
  return {'id':identity,'owner_id':owner,'source_ids':sources,'source_group_id':group,'split':'train','stage':stage,
    'bank':bank,'source_admission':'ADMIT','training_admitted':True,'root_main_admission':False,'requires_external_root_admission':True,
    'staging_only_not_selected_by_main_manifest':True,'supervision_message_indices':[2],'message_loss_mask':[0,0,1],
    'messages':messages,'tools':deepcopy(tools),'approved_components':components,'loss_multiplier':0.25,
    'allow_reviewed_completion_prefix':False,'teacher_original_R_supervised':False,
    'tool_schema_provenance':provenance,'student_view':'EXPLICIT_NEW_FUNCTIONAL_STATE_WITH_REAL_CODE_AND_OLD_OBSERVATION_PINS',
    'is_original_native_request_identical':False,'original_native_prompt_equivalence_claimed':False,'actual_native_tool_dispatch':False,
    'original_recorded_action_owner':h(ctx['episode_id']+':'+str(index))[:24]if index is not None else h(repair['episode_id']+':112')[:24],
    'original_native_session_id':ctx['native_session_id']if index is not None else repair['native_session_id'],
    'original_native_message_index':index if index is not None else 112,'annotation_provenance':'NEW_EXPLICIT_FUNCTIONAL_STATE_FROM_VERIFIED_ORIGINAL_VERSION_AND_FEEDBACK; NOT_AN_ORIGINAL_NATIVE_REQUEST_REPLAY',
    'rationale_provenance':rationale_provenance,'future_feedback_in_model_input':False,
    'is_full_autonomous_execution_demonstration':False,'is_qualified_KEEP_demonstration':False,
    'source_entity_identity_not_new_independent_experience':True,'full_pipeline_or_skill_utility_approved':False,
    'evidence':{'original_context':pin(gen/'CONTEXT.original.audit.jsonl.gz')if index is not None else pin(rep/'CONTEXT.original.audit.jsonl.gz'),
      'original_final_verifier':pin(finalpath),'local_cpu_counterexample_is_not_native_consumption_or_business_Q':True},
    'model_weights_loaded':False,'training_started':False}
 # Path correction is two exact edit actions, not the old shell/rm invocation.
 user0='离线重建的局部资源修订状态，不是原native请求重放。\n任务：修正复现校验器的断言目录定位，不改case命令、expected_exit或断言值，不宣称技能合格。下面文件已作为当前状态文本提供于 /workspace/outputs/making_history/replay_verify.py：\n```python\n'+source0+'\n```\n旧记录实际错误（只到本次修订前）：\n'+original_feedback['path_fix_failure']+'\ncase命令的{OUT}展开为统一OUT目录；断言文件名也相对该OUT。请作最小定位修订。'
 action0={'role':'assistant','content':'','reasoning_content':'case命令把结果写入统一OUT目录，断言却多拼接了case或composition子目录；只统一断言根目录，保留原命令和期待值。',
   'tool_calls':[{'id':'call-identity10-path-'+str(k),'type':'function','function':{'name':'edit','arguments':{'path':'/workspace/outputs/making_history/replay_verify.py','oldText':p[0],'newText':p[1]}}}for k,p in enumerate(pairs)]}
 c0=common('identity10-verifier-path-repair','new_state:identity10-verifier-path-repair',57,'B',['R','A'],user0,action0,'versioned_resource_repair_projection10','NEW_AUTHORED_LOCAL_REPAIR_REASON_NOT_ORIGINAL_COT')
 c0.update(target_code_provenance='VERBATIM_LITERAL_REPLACEMENT_PAIRS_FROM_ORIGINAL_NATIVE_EXEC_PROJECTED_TO_EDIT',
   new_authored_R=True,version_before_sha256=h(source0),version_after_sha256=h(source1),
   actual_feedback_for_credit_only=[{'native_message_index':58,'text':original_feedback['after_path_fix_new_error']}],
   semantic_scope='LOCAL_OUTPUT_PATH_CONTRACT_ONLY; NEW_ERROR_IS_NOT_A_FULL_VERIFIER_PASS')
 candidates.append(c0)
 user1='离线重建的局部资源修订状态，不是原native请求重放。\n任务：修复错误用例的stderr落盘；expected_exit和所有断言必须保持。文件 /workspace/outputs/making_history/replay_verify.py 当前内容：\n```python\n'+source1+'\n```\n旧记录实际错误（仅本次修订前）：\n'+original_feedback['after_path_fix_new_error']+'\n某case的expected_exit=2、实际returncode=2，断言需要读取真实stderr.txt。只作最小修订，不宣称整skill通过。'
 action1={'role':'assistant','content':'','reasoning_content':'期待的失败同样属于exit_ok分支，原逻辑因此没有保存stderr。应先无条件保存真实stdout和stderr，再照原期待退出码和断言判定，避免缺文件或伪造通过。',
  'tool_calls':[{'id':'call-identity10-stderr','type':'function','function':{'name':'edit','arguments':{'path':'/workspace/outputs/making_history/replay_verify.py','oldText':old,'newText':new}}}]}
 c1=common('identity10-verifier-stderr-repair','new_state:identity10-verifier-stderr-repair',59,'B',['R','A'],user1,action1,'versioned_resource_repair_projection10','NEW_AUTHORED_LOCAL_REPAIR_REASON_NOT_ORIGINAL_COT')
 c1.update(target_code_provenance='VERBATIM_ORIGINAL_NATIVE_REPLACEMENT_BLOCKS_PROJECTED_TO_EDIT',new_authored_R=True,
   version_before_sha256=h(source1),version_after_sha256=h(source2),
   actual_feedback_for_credit_only=[{'native_message_index':60,'text':original_feedback['after_stderr_fix_actual_result']}],
   semantic_scope='ACTUAL_STREAM_PERSISTENCE_AND_EXPECTED_FAILURE_ORACLE_ONLY; NO_FULL_SKILL_QUALITY_CREDIT')
 candidates.append(c1)
 user2='离线重建的收尾状态，不是原native请求重放。任务：依据已知交付账本作保守状态结算，不再执行工具，不将局部程序测试等同完整skill验收。\n事实：resource_manifest.json和evidence.json未写入，portable preflight尚未运行，making_history未齐；本次只能使用generated_fixture，原始附件未恢复；replay.json已保留这些限制。当前没有消费侧减负结论。请如实报告候选状态与待办。'
 action2={'role':'assistant','content':hold,'reasoning_content':''}
 c2=common('identity10-recorded-incomplete-hold','new_state:identity10-recorded-incomplete-hold',None,'D',['D'],user2,action2,'recorded_visible_process10','ORIGINAL_VISIBLE_ASSISTANT_TEXT_NOT_THOUGHT_FIELD')
 c2.update(teacher_original_R_supervised=False,new_authored_R=False,
   original_visible_D_sha256=h(hold),original_visible_D_source_message_sha256=h(js(repair['messages'][112])),
   original_visible_D_unicode_start=original_end.index(needle),original_visible_D_unicode_end=len(original_end),
   original_visible_D_verbatim=True,semantic_scope='INCOMPLETE_DELIVERY_HOLD_ONLY; NO_QUALIFIED_SKILL_KEEP')
 candidates.append(c2)
 for c in candidates:review.append({'id':c['id'],'decision':'RECOMMEND_ROOT_ADMISSION_OF_SCOPED_NEW_FUNCTIONAL_STATE_ONLY',
   'approved_components':c['approved_components'],'loss_multiplier':0.25,'native_original_R':False,
   'original_native_request_replay':False,'actual_native_dispatch_for_projected_action':False,
   'version_before_sha256':c.get('version_before_sha256'),'version_after_sha256':c.get('version_after_sha256'),
   'original_native_message_index':c['original_native_message_index'],'semantic_scope':c['semantic_scope']})
 with (OUT/'CANDIDATES.raw.jsonl.gz').open('wb')as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)as f:
   for c in candidates:f.write((js(c)+'\n').encode())
 qa={'status':'PASS_SCOPED_VERSION_CHAIN_LOCAL_CPU_COUNTEREXAMPLES_AND_RECORDED_HOLD_NOT_MAIN_ADMISSION',
   'reconstructed_versions':[{'name':name,'sha256':h(code),'bytes':len(code.encode())}for name,code in [('v0',source0),('v1',source1),('v2',source2)]],
   'two_observed_native_literal_patches_rebuild_actual_final_verifier_exactly':True,
   'path_bug_before_FileNotFoundError':before_failed,'path_corrected_same_expected_file_assertion':True,
   'stderr_before':oldprobe,'stderr_after':newprobe,'wrong_exit_still_wrong':mismatch,
   'actual_old_native_errors_and_feedback':original_feedback,'original_hold_missing_files':missing,
   'new_candidates':3,'new_original_R_candidates':0,'new_authored_R_candidates':2,'recorded_visible_D_candidates':1,
   'new_independent_sources':0,'new_native_business_calls':0,'weights_loaded':False,'training_started':False,
   'no_original_task_workspace_modified':True,'no_captured_shell_or_Agent_loop_executed':True,
   'limited_original_literal_function_CPU_checks_executed_in_task_owned_directory':True,
   'candidate_pin':pin(OUT/'CANDIDATES.raw.jsonl.gz'),'script_pin':pin(__file__)}
 save(OUT/'LOCAL_REPAIR_CPU_QA.json',qa)
 save(OUT/'SEMANTIC_RECOMMENDATIONS.json',{'rows':review,'qa':pin(OUT/'LOCAL_REPAIR_CPU_QA.json'),
   'root_main_admission_required':True,'training_started':False})
 print(js({'candidates':3,'versions_match_actual_final_file':True,'local_before_after_counterexamples':'PASS',
   'recorded_HOLD_original_visible_text_verbatim':True,'main_not_modified':True,'training_started':False}))

if __name__=='__main__':main()
