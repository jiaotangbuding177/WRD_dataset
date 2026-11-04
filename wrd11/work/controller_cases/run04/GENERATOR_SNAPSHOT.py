"""Authored conditional decision curriculum, never an Agent execution loop.

All metrics are explicit givens, not business measurements. Each pair changes
exactly one visible premise; nuisance variants are QA-only, not added to SFT.
No enterprise source, original thought, tool execution or real KEEP is invented.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter
from decimal import Decimal, ROUND_FLOOR
import hashlib,json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261031_wrd_curation11/controller_cases/run04'
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True)
def hs(x):return hashlib.sha256((x if isinstance(x,bytes) else x.encode())).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())

def solve(s):
 """Return a policy derivation and optional *unexecuted* native tool intent."""
 k=s['request_kind'];x=s['facts'];p=s['policy'];call=None;extra={}
 def answer(decision,reason,next_step,tool=None,values=None):
  d={'decision':decision,'next_step':next_step,'scope':'SYNTHETIC_GIVEN_POLICY_ONLY','real_skill_qualified_claim':False}
  if values is not None:d['derived_values']=values
  return {'R':reason,'D':d,'native_tool_intent':tool,'new_author_reasoning':True}
 def spawn(task,seconds):
  assert 0<seconds<=x['remaining_seconds']
  return {'name':'sessions_spawn','arguments':{'task':task,'taskName':'wrd_'+s['case_alias'],
   'runtime':'subagent','context':'isolated','visible':False,'runTimeoutSeconds':seconds,'expectsCompletionMessage':True,'cleanup':'keep'}}
 if k in {'dispatch_time','dispatch_requests','dispatch_io'}:
  key={'dispatch_time':'seconds','dispatch_requests':'requests','dispatch_io':'io_tokens'}[k]
  required=x['required_'+key];left=x['remaining_'+key]
  if left<required:return answer('HOLD',f'本次保守上界需要{required}{key}，只剩{left}；完整工作不能在硬预算内投递，也不能用无限超时补偿。','REPORT_BUDGET_GAP')
  seconds=min(x['required_seconds'],x['remaining_seconds'])
  return answer('DISPATCH',f'需求与只读输入已给齐，当前没有同任务在途子会话；{key}所需{required}不超过剩余{left}，按正超时上界投递，不声称子任务已完成。','WAIT_FOR_NATIVE_RESULT',spawn(x['task'],seconds))
 if k=='active_duplicate':
  if x['child_state']=='running':return answer('WAIT','同一幂等任务已有在途子会话；再次投递会造成重复工作和费用，应等待原任务。','CHECK_EXISTING_CHILD',{'name':'subagents','arguments':{'action':'wait','taskIds':[x['child_id']],'timeoutSeconds':min(60,x['remaining_seconds'])}})
  return answer('INSPECT','原子会话已经结束；应先读取该任务的实际结果，再决定复试或修订，不能按在途状态反复等待。','READ_CHILD_RESULT',{'name':'read','arguments':{'path':x['result_path']}})
 if k=='unknown_child_identity':
  if x['child_id'] is None:return answer('LIST','没有可核的子会话ID，不能编造ID或启动替代任务；先查询原生任务列表。','RECOVER_NATIVE_CHILD_ID',{'name':'subagents','arguments':{'action':'list'}})
  return answer('WAIT','已有明确子会话ID且尚未终态，应有界等待该ID，不用路径名冒充任务身份。','AWAIT_CHILD',{'name':'subagents','arguments':{'action':'wait','taskIds':[x['child_id']],'timeoutSeconds':min(60,x['remaining_seconds'])}})
 if k=='wait_bound':
  seconds=min(x['requested_wait_seconds'],x['remaining_seconds'],60)
  if seconds<=0:return answer('HOLD','剩余经过时间为零，不能发起正时长等待或新工作；保留未终态记录并报告未完成。','REPORT_UNFINISHED_CHILD')
  return answer('WAIT',f'原生subagents单次等待最多60秒；本次请求{x["requested_wait_seconds"]}，剩余{x["remaining_seconds"]}，取{seconds}秒，不创建新会话。','BOUNDED_WAIT',{'name':'subagents','arguments':{'action':'wait','taskIds':[x['child_id']],'timeoutSeconds':seconds}})
 if k=='skill_actual_read':
  if not x['full_text_received']:return answer('READ_SKILL','原生发现只给了技能位置；尚无模型实际收到全文的记录，应先按原生read读取SKILL.md。','READ_NATIVE_SKILL',{'name':'read','arguments':{'path':x['skill_path']}})
  return answer('DISPATCH','技能全文已实际收到，任务、边界与输入位置已给齐；可让原生子会话按该资源执行，不能由外层代做步骤。','NATIVE_GOLD_REPLAY',spawn(x['task'],x['required_seconds']))
 if k=='resource_pin':
  if x['actual_sha256']!=x['expected_sha256']:return answer('HOLD','资源实际SHA与冻结计划不同，旧版本反馈不能为当前字节背书；先核对版本和来源。','RESOLVE_RESOURCE_VERSION')
  return answer('INSPECT','实际资源SHA与计划相等；可继续读取具体资源，但哈希一致本身不授予内容正确或技能效用。','READ_RESOURCE_CONTENT',{'name':'read','arguments':{'path':x['resource_path']}})
 if k=='required_input':
  if x['required_input_present']:return answer('INSPECT','任务要求的附件在给定输入目录中存在，先读取原件再构建；不凭文件名推内容。','READ_REQUIRED_INPUT',{'name':'read','arguments':{'path':x['input_path']}})
  return answer('CLARIFY','该任务依赖的原始附件缺失，不能补造企业事实或用空文件当原输入。','REQUEST_MISSING_INPUT')
 if k=='route_merge':
  if x['requirements_covered']:return answer('REUSE','现有路线边界和资源覆盖本次要求；先读原技能并复用，不因名称变化重复制作。','READ_EXISTING_SKILL',{'name':'read','arguments':{'path':x['skill_path']}})
  return answer('REVISE','本次明确要求超出现有路线声明边界；应构造有界增量及其检验，而不能直接承诺旧技能覆盖。','SPECIFY_DELTA_AND_TESTS')
 if k=='resource_regression':
  if x['current_failed_cases']>0:return answer('REVISE',f'当前版本在{x["current_failed_cases"]}个明确案例失败，旧版本通过不能覆盖当前回归；保留失败并修订后同输入复测。','REPAIR_CURRENT_AND_RETEST')
  return answer('HOLD','当前局部回归检查通过，但未给出独立消费与业务Q；只能授局部资源信用，不能冻结为合格技能。','REQUEST_INDEPENDENT_CONSUMER_TRIAL')
 if k=='receipt_version':
  if x['tested_version_sha256']!=x['current_version_sha256']:return answer('RETEST','已通过回执绑定另一版本，不能迁移到当前资源；应测试当前精确字节。','TEST_CURRENT_VERSION')
  return answer('HOLD','测试回执与当前精确版本相符，局部检查可继承；完整复用效用仍缺独立消费。','COLLECT_CONSUMER_EVIDENCE')
 if k=='boundary_cases':
  if x['edge_cases_tested']==0:return answer('ADD_TESTS','正常案例与错误输入已有通过记录，但没有边界案例覆盖；已有错误输入不能替代边界检查。','TEST_MISSING_EDGE_INPUTS')
  return answer('HOLD','声明的边界与错误输入也已覆盖，但这些是资源检查，仍不能代替业务Q与复用对照。','EVALUATE_REAL_CONSUMPTION')
 if k=='stale_failure':
  if x['latest_failure_reproduced']:return answer('REVISE','当前同输入仍复现失败；后面的success状态不是修复证据，应以实际输出继续修订。','REPAIR_REPRODUCED_FAILURE')
  return answer('HOLD','给定同输入的当前版本已经不复现旧故障，旧坏版本保留审计；没有业务效用证据时仍不能作合格KEEP。','COLLECT_BUSINESS_EVIDENCE')
 if k=='matched_case':
  if x['baseline_input_sha256']!=x['skill_input_sha256']:return answer('HOLD','无技能与技能臂使用不同输入，交付或成本差异不能归因于技能。','RERUN_MATCHED_INPUT_COMPARISON')
  return answer('COMPARE','两臂输入一致且版本已固定，可以比较给定指标；这只建立可比条件，不提前宣布优胜。','COMPARE_SEPARATE_TSR_Q_AND_COST')
 if k=='consumer_identity':
  if x['consumer_content_sha256']==x['construction_content_sha256']:return answer('HOLD','消费输入与制作输入内容相同；不同ID不构成独立复用证据。','OBTAIN_UNSEEN_CONSUMER_INPUT')
  return answer('INSPECT','消费内容hash不同只能排除精确副本；即使其他条件固定，也仍需核对需求与来源独立性，不能直接当未见复用。','CHECK_CONSUMER_LINEAGE_AND_DEMAND')
 if k=='quality_known':
  if x['quality_score'] is None:return answer('HOLD','交付状态成功但独立Q未知，不能把未知写0或从success推高质量。','OBTAIN_BLIND_QUALITY_SCORE')
  return answer('COMPARE',f'独立质量分{x["quality_score"]}已给出，可以按给定阈值{p["q_min"]}比较，不能把TSR与Q乘成一个指标。','COMPARE_GIVEN_POLICY')
 if k=='quality_threshold':
  q=x['quality_score'];bar=p['q_min']
  if q<bar:return answer('REVISE',f'给定Q={q}低于政策阈值{bar}；即使文件已交付，也不能按本政策保留。','REPAIR_QUALITY_GAP')
  return answer('KEEP',f'在本构造题给定的匹配、独立消费、成功、费用完整及同口径总费用下降均成立时，Q={q}达到阈值{bar}；按题给政策保留，不声称真实模型已产出合格技能。','FREEZE_UNDER_GIVEN_POLICY')
 if k=='delivery_success':
  if not x['delivery_accepted']:return answer('REVISE','基础终态验收未通过；高Q或低开销不能替代未完成的交付。Q仍单独保留，不被归零。','FIX_DELIVERY_FAILURE')
  return answer('KEEP','在该合成题给定的其余质量、匹配、独立消费及收益条件均成立时，交付通过满足最后一项政策门槛；只作条件保留判断。','FREEZE_UNDER_GIVEN_POLICY')
 if k=='cost_known':
  if x['repair_cost'] is None:return answer('HOLD','修订费用缺失，不能当0来宣称总费用下降；应补账并保留未知。','RECOVER_MISSING_COST')
  total=sum(Decimal(str(v)) for v in [x['make_cost'],x['repair_cost'],x['consume_cost']])
  return answer('ACCOUNT',f'制作、修订、消费费用均已给出，同币种总额={total}；账户总额不自动证明质量或合格KEEP。','REPORT_TOTAL_SEPARATELY',values={'total_cost':str(total),'unit':x['unit']})
 if k=='dominated_cost':
  if x['skill_cost']>=x['baseline_cost']:return answer('STOP',f'给定同输入成功和Q均等，而技能成本{x["skill_cost"]}不低于基线{x["baseline_cost"]}、时间也不更好；本政策不保留这条无减负路线，历史费用照留。','STOP_FUTURE_WORK_KEEP_COST_HISTORY')
  return answer('KEEP',f'在题给成功、质量与独立匹配条件下，技能成本{x["skill_cost"]}低于基线{x["baseline_cost"]}且时间不更差；按此政策保留，尚非真实效用实证。','FREEZE_UNDER_GIVEN_POLICY')
 if k=='amortization':
  saving=Decimal(str(x['baseline_per_task']))-Decimal(str(x['skill_per_task']))
  fixed=Decimal(str(x['fixed_cost']));n=x['future_tasks']
  if saving<=0:return answer('STOP','边际费用不下降，固定投入不可能靠增加重复次数回收；不能编造有限回本点。','REPORT_NO_FINITE_BREAK_EVEN',values={'break_even_tasks':None})
  # Strict improvement: N*saving > fixed. Equality is not a saving.
  needed=int((fixed/saving).to_integral_value(rounding=ROUND_FLOOR))+1
  decision='KEEP' if n>=needed else 'STOP'
  return answer(decision,f'每次给定节省{saving}、固定投入{fixed}，严格总成本下降需N>{fixed/saving}，最小整数{needed}；题给未来次数{n}，按此条件作{decision}，不是实际回本预测。','REPORT_CONDITIONAL_AMORTIZATION',values={'strict_break_even_tasks':needed,'given_future_tasks':n})
 if k=='qualified_denominator':
  k_count=len(set(x['qualified_terminal_skill_ids']))
  if k_count==0:return answer('UNDEFINED','去重终版合格技能数K=0，每合格技能总成本未定义；不得报0或用候选数当分母。','REPORT_UNDEFINED_K_ZERO',values={'K':0,'cost_per_qualified_skill':None})
  value=Decimal(str(x['total_cost']))/k_count
  return answer('ACCOUNT',f'按终版技能ID去重后K={k_count}，题给总额{x["total_cost"]}除以K={value}；重复命名与消费次数不增加K。','REPORT_GIVEN_UNIT_COST',values={'K':k_count,'cost_per_qualified_skill':str(value)})
 if k=='shared_cost':
  amounts={};unknown=False
  for item in x['ledger']:
   key=item['expense_id'];value=item['amount']
   if value is None:unknown=True;continue
   if key in amounts and amounts[key]!=Decimal(str(value)):unknown=True
   amounts[key]=Decimal(str(value))
  if unknown:return answer('HOLD','共享费用记录缺额或同一费用ID冲突；不能在不确定时重复相加或选更低值。','RECONCILE_SHARED_LEDGER')
  total=sum(amounts.values(),Decimal(0))
  return answer('ACCOUNT',f'同一expense_id只计一次，{len(x["ledger"])}条记录对应{len(amounts)}项独立费用，总额{total}；共享项不重复归入不同模型。','REPORT_DEDUPLICATED_TOTAL',values={'unique_expenses':len(amounts),'total_cost':str(total)})
 if k=='cost_units':
  if x['baseline_unit']!=x['skill_unit']:return answer('HOLD','两臂费用单位不同且没有已知换算；不能把金额与token直接比较后宣布节省。','REQUEST_COMMON_COST_UNIT')
  return answer('COMPARE','两臂指标使用同一单位，具备数值比较条件；仍需把交付、Q、固定费用与时间各自核清。','COMPARE_COST_WITHIN_UNIT')
 if k=='sunk_cost':
  if x['future_saving_per_task']<=0:return answer('STOP',f'已发生费用{x["past_spend"]}必须保留，但不使未来非正节省{x["future_saving_per_task"]}变成继续理由。','STOP_FUTURE_KEEP_SUNK_COST')
  return answer('TRY',f'已发生费用{x["past_spend"]}不重复摊进本次边际选择；给定未来每次净节省{x["future_saving_per_task"]}为正，可在已有剩余预算内作有界验证，不能称已回本。','BOUNDED_FUTURE_VALIDATION')
 if k=='skill_references':
  if x['unresolved_references']>0:return answer('REVISE',f'当前轻量首页有{x["unresolved_references"]}个引用无法解析；不能以目录文件多或旧版本通过代替当前可消费性。','REPAIR_CURRENT_RESOURCE_INDEX')
  return answer('HOLD','当前引用解析通过，仅证明包内接线成立；独立消费和质量未给出，不能直接KEEP。','CHECK_ACTUAL_CONSUMPTION')
 if k=='lightweight_pack':
  if x['history_embedded_in_skill']:return answer('REVISE','制作和评审日志被塞进轻量SKILL首页；应外置日志，首页保留适用边界、workflow和按需资源索引。','EXTERNALIZE_BUILD_AND_REVIEW_LOGS')
  return answer('HOLD','轻量首页与资源目录结构符合给定封装要求，但格式正确不等于技能效用，应等待实际消费证据。','VERIFY_CONSUMER_UTILITY')
 if k=='closure_truth':
  if x['artifact_exists']:return answer('REPORT_PARTIAL','实际产物存在但给定Q仍未知，可报告文件已存在和待验范围；存在不证明已验收交付，不能说合格入库。','REPORT_EXISTS_BUT_UNVALIDATED')
  return answer('HOLD','终态状态字段写success但目标产物缺失；应报告实物缺口，不能复制success标签完成收尾。','RECOVER_OR_RECREATE_MISSING_ARTIFACT')
 if k=='retry_observation':
  if not x['command_exit_zero']:return answer('REVISE','工具实际退出非零，应读取错误并进行有界修复；不能据上层success或文件名假定执行完成。','INSPECT_ACTUAL_FAILURE')
  return answer('HOLD','命令退出0只证明进程终态，未检验输出语义；应读产物并测内容，不能直接冻结。','INSPECT_OUTPUT_CONTENT')
 if k=='global_quality':
  if x['quality_current_version'] is None:return answer('HOLD','当前版本未评分，旧版本高分不可转移；即使本次TSR通过也应补当前独立Q。','SCORE_CURRENT_EXACT_VERSION')
  return answer('COMPARE',f'给定当前版本独立Q={x["quality_current_version"]}，可与其余匹配指标分项比较，旧版本分数只保留历史。','COMPARE_CURRENT_VERSION_ONLY')
 if k=='empty_read':
  if not x['read_has_required_body']:return answer('INSPECT','原read没有返回任务所需正文，不能把open/调用记录当收到全文；先按真实路径补读内容。','READ_REQUIRED_BODY',{'name':'read','arguments':{'path':x['input_path'],'offset':1,'limit':200}})
  return answer('PLAN','必要正文已给齐，可整理需求与纠正，再规划有界工作；读取成功仍不是技能收益。','BUILD_SCOPE_AND_WORKFLOW')
 raise AssertionError(('UNSUPPORTED_REQUEST_KIND',k))

def templates(i):
 h=hs('authored-resource-'+str(i));alt=hs('authored-other-version-'+str(i));n=5+i
 base={'remaining_seconds':180+i,'required_seconds':60+i,'remaining_requests':8+i,'required_requests':3,
  'remaining_io_tokens':400000+100*i,'required_io_tokens':200000+100*i,
  'budget_scope':'PARENT_PLUS_CHILD_ALL_REQUESTS_AND_IO_GIVEN_UPPER_BOUNDS_NOT_DEVICE_MEASUREMENTS',
  'read_only_inputs_ready':True,'same_task_active_children':[],
  'parent_child_workspace':'SHARED_/workspace_GIVEN_ENVIRONMENT_PREMISE',
  'input_snapshot':{'path':f'/workspace/inputs/task_{i}/source.txt','content':'这是一份公开构造材料。请生成保留引用标记的索引；空输入不得报成功。'},
  'task':f'父子共享/workspace。仅使用只读/workspace/inputs/task_{i}/source.txt的给定构造材料，制作保留引用标记的索引资源并测试空输入；结果写/workspace/outputs/task_{i}/，保留错误及缺证据，不运行正式评测。'}
 # key, mechanism group, stage, common facts, changed field, values
 return [
 ('dispatch_time','budget','B',base,'remaining_seconds',(60+i,59+i)),
 ('dispatch_requests','budget','B',base,'remaining_requests',(3,2)),
 ('dispatch_io','budget','B',base,'remaining_io_tokens',(200000+100*i,199999+100*i)),
 ('active_duplicate','async_control','B',{'child_id':f'child_{i}','remaining_seconds':120,'result_path':f'/workspace/outputs/child_{i}/result.json'},'child_state',('running','completed')),
 ('unknown_child_identity','async_control','B',{'remaining_seconds':120,'child_state':'running'},'child_id',(None,f'child_{i}')),
 ('wait_bound','async_control','B',{'child_id':f'child_{i}','child_state':'running','requested_wait_seconds':90+i},'remaining_seconds',(0,30+i)),
 ('skill_actual_read','native_skill_read','B',{**base,'skill_path':f'/workspace/skills/item_{i}/SKILL.md','task_boundary_confirmed':True,
  'task':base['task']+f'原生技能已发现于/workspace/skills/item_{i}/SKILL.md；子会话须原生读取该路径，按所述边界使用，不能仅据发现索引假称已收到全文。'},'full_text_received',(False,True)),
 ('resource_pin','resource_identity','B',{'expected_sha256':h,'resource_path':f'/workspace/skills/item_{i}/scripts/run.py'},'actual_sha256',(h,alt)),
 ('required_input','input_and_route','A',{'input_path':f'/workspace/inputs/task_{i}/source.txt'},'required_input_present',(False,True)),
 ('route_merge','input_and_route','A',{'skill_path':f'/workspace/skills/route_{i}/SKILL.md','new_requirement':'必须保持表格与原始引用'},'requirements_covered',(False,True)),
 ('resource_regression','version_and_regression','C',{'baseline_passed':True,'current_version_sha256':h,'current_test_count':20,'current_test_run_completed':True,'independent_consumer_trials':[]},'current_failed_cases',(1+i,0)),
 ('receipt_version','version_and_regression','C',{'current_version_sha256':h,'tested_success':True},'tested_version_sha256',(alt,h)),
 ('boundary_cases','test_coverage','C',{'normal_cases_passed':2+i,'edge_cases_all_passed':True,'error_cases_tested':2+i,'error_cases_all_passed':True,'business_quality_Q':None},'edge_cases_tested',(0,2+i)),
 ('stale_failure','version_and_regression','C',{'status':'success','old_failed_version_sha256':alt,'current_version_sha256':h,'current_same_input_retest_executed':True,'retest_input_sha256':hs('same-input-'+str(i))},'latest_failure_reproduced',(True,False)),
 ('matched_case','consumer_comparability','C',{'baseline_input_sha256':h,'baseline_success':True,'skill_success':True,'skill_version_frozen':True,'skill_version_sha256':h,'execution_and_scoring_conditions_fixed':True},'skill_input_sha256',(alt,h)),
 ('consumer_identity','consumer_comparability','C',{'construction_content_sha256':h,'different_database_ids':True,'execution_and_scoring_conditions_fixed':True,'comparison_arms_share_consumer_input':True,'skill_version_frozen':True},'consumer_content_sha256',(h,alt)),
 ('quality_known','quality','C',{'delivery_success':True,'quality_score_scope':'CURRENT_VERSION_INDEPENDENT_BLIND_RUBRIC'},'quality_score',(None,85+i)),
 ('quality_threshold','quality','D',{'same_input':True,'same_version':True,'independent_consumer':True,'delivery_success':True,'costs_complete':True,'baseline_total_cost':100+i,'skill_total_cost':90+i,'cost_scope':'ALL_FIXED_AND_VARIABLE_EXPENSES_INCLUDED_IN_COMPARISON','unit':'CNY'},'quality_score',(79,80)),
 ('delivery_success','quality','D',{'quality_score':90,'same_input':True,'same_version':True,'independent_consumer':True,'costs_complete':True,'baseline_total_cost':100+i,'skill_total_cost':90+i,'cost_scope':'ALL_FIXED_AND_VARIABLE_EXPENSES_INCLUDED_IN_COMPARISON','unit':'CNY'},'delivery_accepted',(False,True)),
 ('cost_known','cost_accounting','C',{'make_cost':10+i,'consume_cost':3+i,'unit':'CNY','ledger_scope':'EXACTLY_MAKE_REPAIR_CONSUME_NO_OTHER_CATEGORIES','all_category_units':'CNY'},'repair_cost',(None,0)),
 ('dominated_cost','utility','D',{'baseline_cost':10+i,'baseline_seconds':20+i,'skill_seconds':20+i,'baseline_quality':88,'skill_quality':88,'quality_equal':True,'delivery_both_success':True,'matched_independent_consumer':True,'costs_complete':True,'unit':'CNY','cost_scope':'ALL_INCLUSIVE_MATCHED_TRIAL_TOTAL'},'skill_cost',(10+i,9+i)),
 ('amortization','utility','D',{'baseline_per_task':10+i,'skill_per_task':8+i,'fixed_cost':2*n,'quality_score':90,'quality_equal':True,'matched_independent_consumer':True,'delivery_both_success':True,'unit':'CNY','fixed_cost_scope':'ALL_FIXED_EXPENSES_INCLUDING_FAILURES'},'future_tasks',(n,n+1)),
 ('qualified_denominator','cost_accounting','D',{'total_cost':100+i},'qualified_terminal_skill_ids',([],['s_a','s_a','s_b'])),
 ('shared_cost','cost_accounting','C',{'unit':'CNY','ledger_scope':'ALL_EXPENSES_IN_GIVEN_EXERCISE_CLOSED_NO_OTHER_ITEMS'},'ledger',([{'expense_id':'shared','amount':10+i},{'expense_id':'shared','amount':10+i},{'expense_id':'repair','amount':None}],[{'expense_id':'shared','amount':10+i},{'expense_id':'shared','amount':10+i},{'expense_id':'repair','amount':2+i}])),
 ('cost_units','cost_accounting','C',{'baseline_unit':'CNY','baseline_value':10+i,'skill_value':8+i},'skill_unit',('tokens','CNY')),
 ('sunk_cost','utility','D',{'past_spend':1000+100*i,'remaining_trial_budget':5+i,'trial_cost_upper_bound':1+i,'existing_trial_authorization':True,'unit':'CNY','other_trial_limits_satisfied':True},'future_saving_per_task',(0,2+i)),
 ('skill_references','packaging','D',{'skill_sha256':h,'prior_pack_passed':True},'unresolved_references',(1+i,0)),
 ('lightweight_pack','packaging','D',{'has_applicability':True,'has_workflow':True,'resource_index_resolves':True},'history_embedded_in_skill',(True,False)),
 ('closure_truth','honest_closure','D',{'outer_status':'success','quality_score':None},'artifact_exists',(False,True)),
 ('retry_observation','honest_closure','C',{'outer_status':'success','content_checked':False},'command_exit_zero',(False,True)),
 ('global_quality','quality','C',{'delivery_success':True,'previous_version_Q':95,'current_version_sha256':h,'quality_score_scope':'CURRENT_VERSION_INDEPENDENT_BLIND_RUBRIC'},'quality_current_version',(None,82+i)),
 ('empty_read','native_skill_read','A',{'input_path':f'/workspace/inputs/task_{i}/source.txt','tool_invoked':True},'read_has_required_body',(False,True)),
 ]

def main():
 OUT.mkdir(parents=True,exist_ok=False);cases=[];pairs=[];nuisance=[];families=Counter();decisions=Counter()
 for i in range(8):
  for kind,mechanism,stage,facts,field,values in templates(i):
   pair_id='pair11-'+hs(kind+':'+str(i))[:20];pair=[]
   for side,value in enumerate(values):
    ident='ctrl11-'+hs(pair_id+':'+str(side))[:22]
    s={'case_alias':hs(pair_id)[:12],'request_kind':kind,'display_name':['材料索引','会议排版','网页交互','数据整理','简历结构','岗位筛选','文档生成','研发报告'][i],
      'policy':{'q_min':80,'strict_cost_improvement':True,'costs_include_failures':True,'same_version_and_input_required':True},'facts':deepcopy(facts)}
    s['facts'][field]=deepcopy(value);target=solve(s)
    case={'schema':'wrd11-authored-conditional-controller-v1','id':ident,'pair_id':pair_id,'family_id':kind,'mechanism_group':mechanism,
      'synthetic_root_id':'controller11-'+mechanism,'stage':stage,'enterprise_source_ids':[],
      'provenance':{'kind':'NEW_AUTHORED_GIVEN_POLICY_NOT_OBSERVED_METRICS','recorded_teacher_R':False,'recorded_native_execution':False,'proposed_supervision_weight':0.05},
      'point_time_state':s,'target':target,'validation':{'oracle':'TRANSPARENT_GIVEN_POLICY_ARITHMETIC_OR_STATE_RULE','true_business_Q_measured':False,'real_qualified_KEEP':False,'future_receipt_in_input':False}}
    cases.append(case);pair.append(case);families[kind]+=1;decisions[target['D']['decision']]+=1
    perturbed=deepcopy(s);perturbed['display_name']='无关展示名称-'+hs(ident)[:8]
    other=solve(perturbed);assert js(other)==js(target),'NUISANCE_CHANGED_SEMANTIC_TARGET'
    nuisance.append({'case_id':ident,'perturbed_point_time_state':perturbed,'expected_semantic_target_sha256':hs(js(target)),'usage':'QA_ONLY_NEVER_ADD_TO_SFT'})
   a,b=pair;assert a['target']['D']['decision']!=b['target']['D']['decision']
   fa,fb=a['point_time_state']['facts'],b['point_time_state']['facts'];diff=[k for k in set(fa)|set(fb) if fa.get(k)!=fb.get(k)]
   assert diff==[field],('NOT_SINGLE_PREMISE_FLIP',kind,diff)
   pairs.append({'pair_id':pair_id,'case_ids':[x['id'] for x in pair],'changed_field':'facts.'+field,'decisions':[x['target']['D']['decision'] for x in pair],'same_group':True})
 p=OUT/'CASES.jsonl';p.write_bytes(b''.join((js(x)+'\n').encode() for x in cases))
 save(OUT/'COUNTERFACTUAL_PAIRS.json',{'pairs':pairs,'all_single_visible_premise_flip':True})
 save(OUT/'NUISANCE_QA_ONLY.json',{'variants':nuisance,'not_training_rows':True})
 save(OUT/'GENERATION_QA.json',{'status':'PASS_AUTHORED_GIVEN_POLICY_PAIR_AND_NUISANCE_CHECKS_PENDING_INDEPENDENT_SEMANTIC_REVIEW',
  'cases':len(cases),'single_premise_pairs':len(pairs),'qa_only_nuisance_variants':len(nuisance),'scenario_families':len(families),
  'mechanism_groups':len({c['mechanism_group'] for c in cases}),'family_counts':dict(families),'decision_counts':dict(decisions),
  'synthetic_conditional_KEEP_labels':decisions['KEEP'],'real_qualified_KEEP':0,'new_enterprise_source_ids':0,'native_execution':0,
  'training_started':False,'cases_sha256':hs(p.read_bytes()),'generator_sha256':hs(Path(__file__).read_bytes()),
  'independence_warning':'512 authored states are not 512 independent enterprise experiences; variants and pairs share mechanism groups.'})
 print(json.dumps({'cases':len(cases),'pairs':len(pairs),'decisions':dict(decisions),'training_started':False}))
if __name__=='__main__':main()
