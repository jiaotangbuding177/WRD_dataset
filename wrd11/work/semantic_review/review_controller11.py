"""Independent offline case/ABI/premise audit. Never imports the generator.

All arithmetic and decisions are recomputed from visible givens. The audit
cannot turn hypothetical metrics into measured business outcomes.
"""
from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
from fractions import Fraction
import argparse,hashlib,json,re
from jsonschema import Draft202012Validator

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation11/semantic_review'
CAT=ROOT/'output/20261031_wrd_curation11/protocol_review/OPENCLAW_TOOLS53.json'
EXPECTED_CAT_SHA='460eaba88426437ec7d9b768979912bbd6ce01079d694fb6e4dc7488daed46f0'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True)
def pin(p):p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':h(p)}
def main(a):
 assert not a.out.exists();assert h(CAT)==EXPECTED_CAT_SHA
 rows=[json.loads(l)for l in a.cases.read_text(encoding='utf-8-sig').splitlines()if l.strip()]
 generation=load(a.cases.parent/'GENERATION_QA.json');assert h(a.cases)==generation['cases_sha256']
 source=a.cases.parent/'GENERATOR_SNAPSHOT.py'
 if not source.exists():source=ROOT/'research/data_prep/wrd_curation11/controller_cases11.py'
 assert h(source)==generation['generator_sha256'],'EXACT_HISTORICAL_GENERATOR_SOURCE_REQUIRED'
 tools={t['function']['name']:t['function']for t in load(CAT)}
 problems=[];checks=Counter();families=Counter();patterns=defaultdict(set);pairs=defaultdict(list);native=Counter()
 def require(ok,row,code,explanation):
  checks[code]+=1
  if not ok:problems.append({'case_id':row['id'],'family':row['family_id'],'code':code,'explanation':explanation})
 def has_fields(row,keys,scope='facts'):
  x=row['point_time_state'][scope]
  return all(k in x for k in keys)
 for r in rows:
  s=r['point_time_state'];x=s['facts'];p=s['policy'];t=r['target'];d=t['D'];k=r['family_id'];expected=None
  families[k]+=1;pairs[r['pair_id']].append(r);patterns[k].add(re.sub(r'\d+(?:\.\d+)?','<N>',t['R']))
  require(not r['enterprise_source_ids'] and r['provenance']['recorded_teacher_R']is False and r['provenance']['recorded_native_execution']is False,r,'HONEST_NEW_AUTHOR_PROVENANCE','No enterprise source or original native/Teacher reasoning claim is introduced.')
  require(t['new_author_reasoning']is True and d['real_skill_qualified_claim']is False and d['scope']=='SYNTHETIC_GIVEN_POLICY_ONLY',r,'NO_REAL_KEEP_OR_COT_CLAIM','Every R/D must stay an authored conditional judgment.')
  require(r['validation']['true_business_Q_measured']is False and r['validation']['real_qualified_KEEP']is False and r['validation']['future_receipt_in_input']is False,r,'METRICS_ARE_GIVENS','A given score or task ID is not an actually measured receipt.')
  intent=t['native_tool_intent']
  if intent:
   n=intent['name'];args=intent['arguments'];native[n]+=1
   require(n in tools,r,'CAPTURED_TOOL_NAME','Native action must use a captured tool name.')
   if n in tools:require(not list(Draft202012Validator(tools[n]['parameters']).iter_errors(args)),r,'EXACT_NATIVE_JSON_SCHEMA','Parameters must satisfy the actual captured ABI.')
   if n=='sessions_spawn':
    require(args.get('runtime')=='subagent' and args.get('visible')is False and args.get('context')=='isolated'and args.get('cleanup')=='keep',r,'HIDDEN_ISOLATED_NATIVE_CHILD','No visible task or unreviewed fork is manufactured.')
    require('collect'not in args and 'model'not in args and 'agentId'not in args and 'attachments'not in args,r,'NO_MODEL_COLLECT_OR_ATTACHMENT_OVERRIDE','Ordinary bounded work uses no model override, collector or injected attachment.')
    require(type(args.get('runTimeoutSeconds'))is int and 0<args['runTimeoutSeconds']<=x['remaining_seconds'],r,'POSITIVE_BOUNDED_CHILD_TIMEOUT','Zero disables a child timeout; positive timeout must fit visible remaining time.')
    require(x.get('read_only_inputs_ready')is True and x.get('same_task_active_children')==[],r,'DISPATCH_READY_AND_NO_DUPLICATE_GIVEN','R claims inputs are ready and no duplicate is running; both must be visible givens.')
    require(has_fields(r,['input_snapshot','parent_child_workspace']) and x['input_snapshot']['path']in args['task'],r,'CHILD_RECEIVES_EXPLICIT_PATH','An isolated child needs the commissioned shared resource path, not an invisible parent assumption.')
    require(all(x['remaining_'+unit]>=x['required_'+unit]for unit in ['seconds','requests','io_tokens']),r,'ALL_VISIBLE_BUDGET_DIMENSIONS_FIT','A favorable single field cannot override another known exhausted budget.')
    require(x['required_io_tokens']>=26693,r,'FULL53_IO_UPPER_BOUND_NOT_IMPOSSIBLE','An all-requests IO upper bound below the measured minimal full53 input is inconsistent.')
    if k=='skill_actual_read':require(x['skill_path']in args['task'] and '读取'in args['task'],r,'CHILD_SKILL_PATH_AND_ACTUAL_READ','A parent reading SKILL does not transfer it to an isolated child; the task must reference native reading.')
   if n=='subagents':
    require(args.get('action')in {'wait','list','cancel'},r,'EXPLICIT_NATIVE_SUBAGENT_ACTION','Do not infer a default or invent dispatch.')
    if args['action']=='wait':require(0<args['timeoutSeconds']<=min(60,x['remaining_seconds'])and args['taskIds']==[x['child_id']],r,'WAIT_ID_AND_TIME_BOUND','Wait only for the visible actual hypothetical child ID, within the captured 60-second ABI.')
  if k.startswith('dispatch_'):
   units=['seconds','requests','io_tokens'];expected='DISPATCH'if all(x['remaining_'+u]>=x['required_'+u]for u in units)else'HOLD'
  elif k=='active_duplicate':expected='WAIT'if x['child_state']=='running'else'INSPECT'
  elif k=='unknown_child_identity':expected='LIST'if x['child_id']is None else'WAIT'
  elif k=='wait_bound':expected='WAIT'if min(x['remaining_seconds'],x['requested_wait_seconds'],60)>0 else'HOLD'
  elif k=='skill_actual_read':expected='DISPATCH'if x['full_text_received']else'READ_SKILL'
  elif k=='resource_pin':expected='INSPECT'if x['actual_sha256']==x['expected_sha256']else'HOLD'
  elif k=='required_input':expected='INSPECT'if x['required_input_present']else'CLARIFY'
  elif k=='route_merge':expected='REUSE'if x['requirements_covered']else'REVISE'
  elif k=='resource_regression':
   expected='REVISE'if x['current_failed_cases']>0 else'HOLD'
   require(x.get('current_test_run_completed')is True and x.get('current_test_count',0)>0 and x['current_failed_cases']<=x.get('current_test_count',-1),r,'ZERO_FAILURES_NOT_ZERO_TESTS','Saying a current regression check passed requires an executed nonempty current-version suite.')
  elif k=='receipt_version':expected='HOLD'if x['tested_version_sha256']==x['current_version_sha256']else'RETEST'
  elif k=='boundary_cases':
   expected='ADD_TESTS'if x['edge_cases_tested']==0 else'HOLD'
   require(x.get('error_cases_tested',0)>0 and x.get('error_cases_all_passed')is True,r,'ERROR_COVERAGE_EXPLICIT','Edge-case count alone does not prove invalid/error inputs were checked.')
  elif k=='stale_failure':
   expected='REVISE'if x['latest_failure_reproduced']else'HOLD'
   require(x.get('current_same_input_retest_executed')is True,r,'CURRENT_MATCHED_RETEST_GIVEN','A false reproduced flag alone cannot stand for a current-version matched rerun.')
  elif k=='matched_case':
   expected='COMPARE'if x['baseline_input_sha256']==x['skill_input_sha256']else'HOLD'
   require(x.get('skill_version_frozen')is True and x.get('execution_and_scoring_conditions_fixed')is True,r,'MATCHED_COMPARISON_OTHER_CONDITIONS_GIVEN','Same input alone does not freeze the skill version or scoring conditions.')
  elif k=='consumer_identity':
   expected='HOLD'if x['consumer_content_sha256']==x['construction_content_sha256']else'INSPECT'
   if expected=='INSPECT':require('不能直接当未见复用'in t['R'],r,'HASH_DIFFERENCE_NOT_INDEPENDENCE','A different hash can still be a whitespace/edit duplicate and cannot certify unseen independent reuse.')
  elif k=='quality_known':
   expected='HOLD'if x['quality_score']is None else'COMPARE'
   require(x.get('quality_score_scope')=='CURRENT_VERSION_INDEPENDENT_BLIND_RUBRIC',r,'QUALITY_SCORE_SCOPE_GIVEN','The R calls the score current independent Q; that scope must be explicit.')
  elif k=='quality_threshold':expected='REVISE'if x['quality_score']<p['q_min']else'KEEP'
  elif k=='delivery_success':expected='KEEP'if x['delivery_accepted']else'REVISE'
  elif k=='cost_known':
   expected='HOLD'if x['repair_cost']is None else'ACCOUNT'
   require(x.get('ledger_scope')=='EXACTLY_MAKE_REPAIR_CONSUME_NO_OTHER_CATEGORIES'and x.get('all_category_units')==x['unit'],r,'CLOSED_SAME_UNIT_COST_CATEGORIES','A subtotal cannot be called the total without explicit category closure and common units.')
   if expected=='ACCOUNT':require(Decimal(d['derived_values']['total_cost'])==sum(Decimal(str(x[z]))for z in ['make_cost','repair_cost','consume_cost']),r,'COST_SUM_EXACT','Recompute cost from numeric givens, not the generator oracle.')
  elif k=='dominated_cost':
   expected='KEEP'if x['skill_cost']<x['baseline_cost']else'STOP'
   require(x['skill_seconds']<=x['baseline_seconds']and x['baseline_quality']==x['skill_quality']>=p['q_min'],r,'DOMINANCE_ACTUAL_NUMERIC_CONDITIONS','The R claims time is no worse and Q is equal: verify actual numbers.')
  elif k=='amortization':
   saving=Fraction(str(x['baseline_per_task']))-Fraction(str(x['skill_per_task']));fixed=Fraction(str(x['fixed_cost']))
   needed=int(fixed//saving)+1;expected='KEEP'if x['future_tasks']>=needed else'STOP'
   require(d['derived_values']['strict_break_even_tasks']==needed,r,'STRICT_INTEGER_AMORTIZATION','At equality no strict saving occurs; recompute with exact rational arithmetic.')
   require(x.get('fixed_cost_prospective_not_sunk')is True,r,'PROSPECTIVE_NOT_SUNK_INVESTMENT','Using an already-paid fixed cost to STOP future marginally cheaper reuse would contradict sunk-cost reasoning; the investment timing must be explicit.')
  elif k=='qualified_denominator':
   count=len(set(x['qualified_terminal_skill_ids']));expected='ACCOUNT'if count else'UNDEFINED'
   require(d['derived_values']['K']==count,r,'TERMINAL_SKILL_IDS_DEDUPLICATED','Repeated IDs cannot increase the qualified skill denominator.')
   if count:require(Decimal(d['derived_values']['cost_per_qualified_skill'])==Decimal(str(x['total_cost']))/count,r,'UNIT_COST_EXACT','Recompute the given unit cost.')
   else:require(d['derived_values']['cost_per_qualified_skill']is None,r,'K_ZERO_UNDEFINED','K=0 cost is undefined, not zero.')
  elif k=='shared_cost':
   amounts={};unknown=False
   for e in x['ledger']:
    if e['amount']is None:unknown=True;continue
    if e['expense_id']in amounts and amounts[e['expense_id']]!=Decimal(str(e['amount'])):unknown=True
    amounts[e['expense_id']]=Decimal(str(e['amount']))
   expected='HOLD'if unknown else'ACCOUNT'
   require(x.get('unit')and x.get('ledger_scope')=='ALL_EXPENSES_IN_GIVEN_EXERCISE_CLOSED_NO_OTHER_ITEMS',r,'SHARED_COST_COMMON_UNIT_AND_CLOSED_SCOPE','Deduplication does not establish unit compatibility or the completeness of the total.')
   if not unknown:require(Decimal(d['derived_values']['total_cost'])==sum(amounts.values()),r,'SHARED_EXPENSE_ONCE','Each equal expense ID contributes once.')
  elif k=='cost_units':expected='COMPARE'if x['baseline_unit']==x['skill_unit']else'HOLD'
  elif k=='sunk_cost':
   expected='TRY'if x['future_saving_per_task']>0 else'STOP'
   if expected=='TRY':require(x.get('trial_cost_upper_bound',float('inf'))<=x['remaining_trial_budget']and x.get('existing_trial_authorization')is True and x.get('other_trial_limits_satisfied')is True,r,'AFFORDABLE_AUTHORIZED_BOUNDED_TRIAL','Positive marginal savings do not themselves make an unspecified trial affordable or authorized.')
  elif k=='skill_references':
   expected='REVISE'if x['unresolved_references']>0 else'HOLD'
   if not x['unresolved_references']:require(x.get('current_reference_scan_completed')is True and x.get('current_reference_count',0)>0,r,'ZERO_UNRESOLVED_NOT_UNRUN_SCAN','Zero unresolved references is not evidence of an executed nonempty current scan.')
  elif k=='lightweight_pack':expected='REVISE'if x['history_embedded_in_skill']else'HOLD'
  elif k=='closure_truth':
   expected='REPORT_PARTIAL'if x['artifact_exists']else'HOLD'
   if x['artifact_exists']:require('可报告文件已交付'not in t['R'],r,'EXISTENCE_IS_NOT_DELIVERY_ACCEPTANCE','An artifact existing does not establish accepted delivery.')
  elif k=='retry_observation':
   expected='HOLD'if x['command_exit_zero']else'REVISE'
   require(x.get('expected_exit_zero')is True,r,'NONZERO_IS_FAILURE_ONLY_WHEN_EXPECTED_ZERO','A deliberately failing negative test can require a nonzero exit; the expected outcome must be given.')
  elif k=='global_quality':
   expected='HOLD'if x['quality_current_version']is None else'COMPARE'
   require(x.get('quality_score_scope')=='CURRENT_VERSION_INDEPENDENT_BLIND_RUBRIC',r,'CURRENT_QUALITY_SCOPE_EXPLICIT','Old-version Q cannot be reassigned to a current score whose scope is unknown.')
  elif k=='empty_read':expected='PLAN'if x['read_has_required_body']else'INSPECT'
  else:require(False,r,'KNOWN_FAMILY','Every family must receive an independent semantic rule.')
  require(d['decision']==expected,r,'INDEPENDENT_POLICY_DECISION','Decision must follow the givens without executing the producer solver.')
  if d['decision']=='KEEP':
   require(x.get('same_version')is True,r,'KEEP_CURRENT_VERSION_BOUND','The common policy requires the evaluated resource version to match the current version.')
   if k in {'quality_threshold','delivery_success'}:
    require(x.get('same_input')is True and x.get('independent_consumer')is True and x.get('costs_complete')is True and x.get('cost_scope')=='ALL_FIXED_AND_VARIABLE_EXPENSES_INCLUDED_IN_COMPARISON',r,'KEEP_ALL_REQUIRED_PREMISES','Conditional KEEP requires matched input, independent consumer, and complete total-cost comparison.')
    require(has_fields(r,['baseline_total_cost','skill_total_cost'])and x['skill_total_cost']<x['baseline_total_cost']and x['quality_score']>=p['q_min'],r,'KEEP_TOTAL_SAVING_AND_Q','Marginal saving alone does not show strict total saving.')
 for pair,group in pairs.items():
  assert len(group)==2
  a0,a1=group;diff=[k for k in set(a0['point_time_state']['facts'])|set(a1['point_time_state']['facts'])if a0['point_time_state']['facts'].get(k)!=a1['point_time_state']['facts'].get(k)]
  assert len(diff)==1 and a0['point_time_state']['policy']==a1['point_time_state']['policy'] and a0['family_id']==a1['family_id']
  assert a0['target']['D']['decision']!=a1['target']['D']['decision']
 assert len({r['id']for r in rows})==len(rows)==512 and len(pairs)==256 and len(families)==32
 summary={'schema':'wrd-controller11-independent-semantic-protocol-review','status':'PASS_CONDITIONAL_POLICY_AND_NATIVE_ABI_ONLY'if not problems else'FAIL_DO_NOT_ADMIT_THIS_RUN',
  'cases_pin':pin(a.cases),'exact_generator_snapshot_pin':pin(source),'technical_catalog_pin':pin(CAT),'review_script_pin':pin(__file__),
  'cases':len(rows),'pairs':len(pairs),'families':len(families),'mechanism_groups':len({r['mechanism_group']for r in rows}),
  'all_cases_machine_read_and_checked':True,'literal_family_branch_patterns_read':sum(len(v)for v in patterns.values()),
  'review_method':'Read the complete generator and representative literal family/side wording; independently inspect all 512 visible states, numeric consequences, premise guards and native ABI. Never import or call solve().',
  'same_family_parameter_variants_not_independent_experiences':True,'native_intents_by_tool':dict(native),'native_intents_all_JSON_schema_valid':not any(z['code']=='EXACT_NATIVE_JSON_SCHEMA'for z in problems),
  'checks_by_code':dict(checks),'problems':problems,'problem_counts':dict(Counter(z['code']for z in problems)),
  'affected_cases':len({z['case_id']for z in problems}),
  'scope_limits':['Givens are authored hypothetical premises, not empirical scores or recovered thought.','A JSON-valid intent is not a dispatched native call or actual handler acceptance.','The 32 conditional families do not establish autonomous full-pipeline skill production.','Full53 tokenization and exact training masks require separate compiler QA.','Pending future results were never added to these point-time states by this audit.'],
  'business_qualified_KEEP_added':0,'native_calls_executed':0,'model_weights_loaded':False,'training_started':False}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes((json.dumps(summary,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({'status':summary['status'],'affected_cases':summary['affected_cases'],'problem_counts':summary['problem_counts'],'SHA256':h(a.out)},ensure_ascii=False))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--cases',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);main(ap.parse_args())
