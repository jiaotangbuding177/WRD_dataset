"""Independent authored QA and invariant audit of a frozen controller curriculum.

No model, native tool, network or training. The only executed subject is the
trusted research solve() function, whose native tool outputs are inert dicts.
Adapters receive policy ID and visible state only. Audit answers are read only
after subject calls; unsupported objectives/state cannot be forced to match.
"""
from pathlib import Path
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal
import argparse, hashlib, json, types, sys

ROOT=Path(__file__).resolve().parents[3]

def canonical(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def D(x): return Decimal(str(x))
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 assert not p.exists(), 'PRESERVE_PRIOR_QA_OUTPUT'
 p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())

def request(kind,facts,policy=None):
 return {'case_alias':'independent_given_state','display_name':'independent QA only',
  'request_kind':kind,'policy':deepcopy(policy or {'q_min':80,'strict_cost_improvement':True}),
  'facts':deepcopy(facts)}

def ledger_from_visible(s,expand_references=False):
 items=[{'expense_id':i['cost_event_id'],'amount':i['amount']} for i in s['cost_events']]
 if expand_references:
  byid={i['cost_event_id']:i for i in s['cost_events']}
  for ref in s.get('allocation_references',[]):
   # A reference points to the SAME physical expense. It is not a new fraction
   # payment. The solver sees repeated expense IDs and must not sum them again.
   e=byid[ref['cost_event_id']]
   items.append({'expense_id':e['cost_event_id'],'amount':e['amount']})
 return items

def known_physical_total(s):
 seen={}
 for item in s['cost_events']:
  k=item['cost_event_id'];v=item['amount']
  if v is None or (k in seen and seen[k]!=D(v)): return None
  seen[k]=D(v)
 return sum(seen.values(),D(0))

def adapt_visible(policy_id,visible_state):
 """No audit-answer argument. No case ID, expected decision, target or reason.

 Mode FULL means the finite challenge can be answered at this solver interface.
 PARTIAL calls a stated subproblem only and is NOT a full challenge pass.
 """
 s=deepcopy(visible_state)
 def full(call,scope): return {'mode':'FULL','scope':scope,'calls':[call]}
 def partial(calls,reason): return {'mode':'PARTIAL','reason':reason,'calls':calls}
 def unsupported(reason): return {'mode':'NOT_COMPARABLE','reason':reason,'calls':[]}
 if policy_id=='P_PARENT':
  if s['remaining_calls']<s['next_call_cost']:
   return full(request('dispatch_requests',{'required_requests':s['next_call_cost'],'remaining_requests':s['remaining_calls']}),
    'CALL_BUDGET_BLOCKER_ONLY_NO_DISPATCH_RECOMMENDATION')
  return unsupported('Parent fixtures specify call budget but not the positive seconds/tool-result-path fields required by this solver. Do not invent bounds or result paths.')
 if policy_id=='P_VERSION':
  return unsupported('Multiple producer/artifact/consumer identities, finite retest budget and review eligibility are not the single receipt_version policy. No forced version/status projection.')
 if policy_id=='P_PAIRING':
  if 'case_records' in s or len(s.get('NS',[]))!=1 or len(s.get('skill',[]))!=1:
   return unsupported('Multi-receipt joining/independence cannot be delegated to the single matched_case input without an adapter solving the challenge first.')
  a,b=s['NS'][0],s['skill'][0]
  fields=['case_id','model','environment','evaluation_policy']
  if any(a.get(k)!=b.get(k) for k in fields):
   return unsupported('Environment/model/evaluation/case matching differs. matched_case checks only input identity and would assume the other conditions.')
  if b.get('version')!=s['requested_version']:
   return unsupported('Requested version is not matched; matched_case would silently assume it.')
  if s['minimum_independent_inputs']!=1:
   return unsupported('One matched_case result cannot establish a multi-input independence threshold.')
  return full(request('matched_case',{'baseline_input_sha256':a['original_input_digest'],
   'skill_input_sha256':b['original_input_digest'],'skill_version_frozen':True,
   'skill_version_sha256':b['version'],'execution_and_scoring_conditions_fixed':True}),
   'ONE_PAIR_INPUT_ELIGIBILITY_OPAQUE_SYNTHETIC_DIGEST_ALIASES_NOT_FILE_SHA_PROOF')
 if policy_id=='P_Q_OBSERVABILITY':
  if any(v is None for v in s['skill_Q']):
   return full(request('quality_known',{'quality_score':None,'delivery_success':s['required_delivery_passed']}),
    'UNKNOWN_Q_IS_A_SUFFICIENT_GATE_BLOCKER_NO_SCORE_IMPUTATION')
  if not s['required_delivery_passed']:
   return full(request('delivery_success',{'delivery_accepted':False,'quality_vector_given_separately':s['skill_Q']}),
    'FAILED_REQUIRED_DELIVERY_ONLY_NO_POSITIVE_KEEP_PREREQUISITES_ADDED')
  ledger=[{'expense_id':k,'amount':v} for k,v in s['known_costs'].items()]
  return partial([request('shared_cost',{'ledger':ledger,'unit':'abstract_credit',
   'ledger_scope':'CLOSED_COSTS_GIVEN_BY_THIS_INDEPENDENT_FIXTURE'})],
   'Only known/zero cost subtotal can be tested. A five-dimensional admission gate is not the scalar quality_threshold KEEP question.')
 if policy_id=='P_NET_BENEFIT':
  required=['baseline_per_use','skill_per_use','total_one_time_cost','planned_uses']
  if any(s.get(k) is None for k in required): return unsupported('Economic inputs unknown.')
  call=request('amortization',{'baseline_per_task':s['baseline_per_use'],'skill_per_task':s['skill_per_use'],
   'fixed_cost':s['total_one_time_cost'],'future_tasks':s['planned_uses'],
   'quality_score':min(s['skill_Q']),'quality_equal':s['baseline_Q']==s['skill_Q'],
   'delivery_both_success':s['required_delivery_passed'],'unit':s['cost_unit'],
   'fixed_cost_scope':'ALL_ONE_TIME_COSTS_EXPLICIT_IN_FINITE_FIXTURE'})
  if s['baseline_Q']==s['skill_Q'] and s['required_delivery_passed']:
   return full(call,'STRICT_NET_BENEFIT_ARITHMETIC_GIVEN_OTHER_FIXTURE_CONDITIONS_NOT_REAL_UTILITY')
  if D(s['skill_per_use'])>=D(s['baseline_per_use']):
   return partial([call],'Nonpositive marginal savings suffice to reject, but the solver does not evaluate the full five-dimensional dominance relation.')
  return unsupported('Quality non-inferiority differs; amortization alone cannot decide the combined policy.')
 if policy_id=='P_PARETO':
  return unsupported('NOT_COMPARABLE_POLICY: this objective allows strict Q improvement at equal cost; solver uses strict cash reduction.')
 if policy_id=='P_ACCOUNTING':
  total=known_physical_total(s)
  ids=[x['final_digest'] for x in s['final_artifact_receipts'] if x['qualified']]
  ledger=ledger_from_visible(s,expand_references=True)
  first=request('shared_cost',{'ledger':ledger,'unit':s['cost_unit'],
   'ledger_scope':'ALL_PHYSICAL_COSTS_IN_FINITE_FIXTURE_ALLOCATIONS_ARE_REFERENCES'})
  if total is None:
   return partial([first],'Unknown-cost status can be tested; solver HOLD does not itself report known subtotal, K and null unit cost.')
  second=request('qualified_denominator',{'total_cost':str(total),'qualified_terminal_skill_ids':ids})
  if s.get('allocation_references'):
   return partial([first,second],'Two primitive accounting calls are checked, not one end-to-end raw-ledger policy. Numerator of second call is independently recomputed from visible physical events, not copied from first solver answer.')
  return full(second,'TERMINAL_DIGEST_DEDUP_AND_DIVISION_GIVEN_INDEPENDENTLY_SUMMED_VISIBLE_NUMERATOR')
 return unsupported('Unknown independent policy.')

def normalized_expected(decision):
 if decision.startswith('HOLD'):return 'HOLD'
 if decision.startswith('STOP'):return 'STOP'
 if decision.startswith('KEEP'):return 'KEEP'
 if decision.startswith('REVISE'):return 'REVISE'
 return {'UNDEFINED_K_ZERO':'UNDEFINED','REPORT_KNOWN_UNIT_COST':'ACCOUNT',
  'VALID_PAIRED_EVIDENCE':'COMPARE','READY_FOR_COMPARISON':'COMPARE','QUALITY_ADMISSIBLE':'COMPARE',
  'EVIDENCE_COMPLETE_WITH_ZERO_COST':'ACCOUNT','WAIT_EXISTING':'WAIT','DISPATCH_ONCE':'DISPATCH',
  'INSPECT_EXISTING_FAILURE':'INSPECT','INSPECT_EXISTING_RESULT':'INSPECT','RUN_VERSIONED_RETEST':'RETEST'}.get(decision,decision)

def call_subject(subject,s):
 before=canonical(s)
 try:
  result=subject.solve(deepcopy(s))
  return {'status':'RETURNED','result':result,'input_unchanged':canonical(s)==before}
 except Exception as e:
  return {'status':'EXCEPTION','exception_type':type(e).__name__,'exception_message':str(e),'input_unchanged':canonical(s)==before}

def check_response(question,response):
 """Independent checks of values or the limited predicate at this interface."""
 if response['status']!='RETURNED':return ['SUBJECT_EXCEPTION']
 t=response['result'];x=question['facts'];k=question['request_kind'];d=t['D'];bad=[]
 if d.get('real_skill_qualified_claim') is not False:bad.append('FALSE_REAL_KEEP_CLAIM')
 if t.get('native_tool_intent') is not None:bad.append('UNEXPECTED_NATIVE_INTENT_IN_THIS_ADAPTER_SCOPE')
 vals=d.get('derived_values',{})
 if k=='dispatch_requests':
  if not(x['remaining_requests']<x['required_requests'] and d['decision']=='HOLD'):bad.append('EXHAUSTED_REQUEST_BUDGET_NOT_HELD')
 elif k=='matched_case':
  want='HOLD' if x['baseline_input_sha256']!=x['skill_input_sha256'] else 'COMPARE'
  if d['decision']!=want:bad.append('INPUT_PAIR_ELIGIBILITY')
 elif k=='quality_known':
  if x['quality_score'] is None and (d['decision']!='HOLD' or vals.get('quality_score') is not None):bad.append('UNKNOWN_Q_IMPUTED_OR_ACCEPTED')
 elif k=='delivery_success':
  if x['delivery_accepted'] is False and d['decision']!='REVISE':bad.append('FAILED_DELIVERY_ACCEPTED')
 elif k=='amortization':
  a,b,f,n=map(D,[x['baseline_per_task'],x['skill_per_task'],x['fixed_cost'],x['future_tasks']])
  benefit=n*(a-b)-f
  want='KEEP' if benefit>0 else 'STOP'
  if d['decision']!=want:bad.append('STRICT_NET_BENEFIT_DECISION')
  if a<=b:
   if vals.get('break_even_tasks','MISSING') is not None:bad.append('FALSE_FINITE_BREAK_EVEN')
  else:
   # Enumerating the first positive-benefit integer independently of the
   # subject's Decimal ROUND_FLOOR division formula.
   first=next(i for i in range(100000) if D(i)*(a-b)>f)
   if vals.get('strict_break_even_tasks')!=first:bad.append('STRICT_INTEGER_BREAK_EVEN')
 elif k=='qualified_denominator':
  count=len(set(x['qualified_terminal_skill_ids']))
  if vals.get('K')!=count:bad.append('TERMINAL_DEDUP_K')
  if count==0:
   if d['decision']!='UNDEFINED' or vals.get('cost_per_qualified_skill','MISSING') is not None:bad.append('K_ZERO_NOT_UNDEFINED')
  elif d['decision']!='ACCOUNT' or D(vals['cost_per_qualified_skill'])!=D(x['total_cost'])/count:bad.append('UNIT_COST_DIVISION')
 elif k=='shared_cost':
  groups=defaultdict(list)
  for item in x['ledger']:groups[item['expense_id']].append(item['amount'])
  unknown=any(any(v is None for v in vs) or len({D(v) for v in vs if v is not None})!=1 for vs in groups.values())
  if unknown:
   if d['decision']!='HOLD' or 'total_cost' in vals:bad.append('UNKNOWN_OR_CONFLICT_COST_AS_KNOWN_TOTAL')
  else:
   total=sum((D(vs[0]) for vs in groups.values()),D(0))
   if d['decision']!='ACCOUNT' or D(vals['total_cost'])!=total or vals['unique_expenses']!=len(groups):bad.append('PHYSICAL_COST_DEDUP_OR_SUM')
 return bad

def answer_poison_test(policy_id,state):
 # Answers are not in either adapter argument. This also verifies state copies
 # cannot contain the outer challenge's expected fields by accidental capture.
 clean={'policy_id':policy_id,'visible_state':deepcopy(state)}
 outer={**deepcopy(clean),'expected_decision':'INTENTIONALLY_WRONG','critical_reason':'POISON','required_semantics':{'K':999}}
 return canonical(adapt_visible(clean['policy_id'],clean['visible_state']))==canonical(adapt_visible(outer['policy_id'],outer['visible_state']))

def subject_scope_gaps(subject,question):
 """A new global subject contract must not be satisfied by invented givens.

 The first audit predates these guards. Source recognition only enables stricter
 compatibility checks, never fills a field or changes a challenge answer.
 """
 if not getattr(subject,'_qa_has_combined_policy_guards',False):return []
 k=question['request_kind'];x=question['facts'];missing=[]
 if k in {'dispatch_time','dispatch_requests','dispatch_io'} or (k=='skill_actual_read' and x.get('full_text_received')):
  if 'read_only_inputs_ready' not in x:missing.append('UNKNOWN_READ_ONLY_INPUT_READINESS')
  for dimension in ['seconds','requests','io_tokens']:
   for prefix in ['remaining_','required_']:
    if prefix+dimension not in x:missing.append('UNSPECIFIED_'+(prefix+dimension).upper())
 gates={
  'quality_threshold':['same_input','same_version','independent_consumer','delivery_success','costs_complete'],
  'delivery_success':['same_input','same_version','independent_consumer','costs_complete'],
  'dominated_cost':['quality_equal','delivery_both_success','matched_independent_consumer','same_version','costs_complete'],
  'amortization':['quality_equal','matched_independent_consumer','same_version','delivery_both_success','fixed_cost_prospective_not_sunk']}
 if k in gates:
  for name in gates[k]:
   if name not in x:missing.append('UNSPECIFIED_COMPARISON_PREMISE_'+name.upper())
   elif x[name] is not True:missing.append('FALSE_COMPARISON_PREMISE_'+name.upper())
  if k in {'dominated_cost','amortization'}:
   for name in ['tested_version_sha256','current_version_sha256']:
    if name not in x:missing.append('UNSPECIFIED_'+name.upper())
 return missing

def evaluate_challenge(subject,policy_id,state,audit_expected):
 plan=adapt_visible(policy_id,state)  # does not receive the audit answer
 calls=[]
 for question in plan['calls']:
  gaps=subject_scope_gaps(subject,question)
  response=call_subject(subject,question)
  calls.append({'input':question,'response':response,'independent_failures':[] if gaps else check_response(question,response),
   'new_subject_contract_gaps':gaps,'actual_call_counted_as_challenge_pass':not gaps})
 requested_mode=plan['mode']
 if calls and all(c['new_subject_contract_gaps'] for c in calls):
  plan={**plan,'mode':'NOT_COMPARABLE','reason':'The new subject global guard needs givens absent or false in this finite challenge. Actual legacy-adapter calls are retained as diagnostics, not counted as failure or pass.'}
 elif plan['mode']=='FULL' and any(c['new_subject_contract_gaps'] for c in calls):
  plan={**plan,'mode':'PARTIAL','reason':'Some subject queries are outside its new global input contract; only compatible subqueries can be checked.'}
 bad=[b for c in calls for b in c['independent_failures']]
 if plan['mode']=='FULL':
  actual=calls[-1]['response']
  if actual['status']=='RETURNED' and actual['result']['D']['decision']!=normalized_expected(audit_expected):bad.append('INDEPENDENT_AUTHORED_DECISION_MISMATCH')
  status='PASS_FULL_FINITE_CHALLENGE_SCOPE' if not bad else 'FAIL'
 elif plan['mode']=='PARTIAL':status='NOT_COMPARABLE_FULL_CHALLENGE_SUBCHECKS_'+('PASS' if not bad else 'FAIL')
 else:status='NOT_COMPARABLE'
 return {'status':status,'adaptation_mode':plan['mode'],'legacy_requested_adaptation_mode':requested_mode,'scope':plan.get('scope'),
  'reason':plan.get('reason'),'calls':calls,'failures':bad,'answer_poison_test':answer_poison_test(policy_id,state),
  'expected_answer_used_only_after_subject_execution':True}

def apply_counterfactual(state,changes):
 out=deepcopy(state)
 for c in changes:
  parts=c['pointer'].strip('/').split('/');obj=out
  for k in parts[:-1]:obj=obj[int(k)] if isinstance(obj,list) else obj[k]
  key=int(parts[-1]) if isinstance(obj,list) else parts[-1];assert key in obj if isinstance(obj,dict) else 0<=key<len(obj)
  obj[key]=deepcopy(c['value'])
 return out

def nuisance_state(case_id,state):
 """Follow the authored non-answer perturbation description, never its answer."""
 s=deepcopy(state);suffix=case_id.split('-')[-1]
 if suffix=='P01':s['children'][0]['child_id']='child-z9'
 elif suffix=='P02':s['children'].append({'child_id':'irrelevant','purpose_key':'other-purpose','state':'DONE'})
 elif suffix=='P03':s['saved_state_display_path']='renamed-snapshot.json'
 elif suffix=='P04':s['purpose_key']='renamed-purpose'
 elif suffix in {'V05','V08','E18'}:s['display_name']='irrelevant display rename'
 elif suffix=='V06':s['consumer_receipts'][0]=dict(reversed(list(s['consumer_receipts'][0].items())))
 elif suffix=='V07':s['additional_local_unit_test']={'version':s['requested_version'],'passed':True}
 elif suffix=='M09':
  e=deepcopy(s['case_records'][1]);e['case_id']='duplicate-new-display-id';e['NS']['case_id']=e['case_id'];e['skill']['case_id']=e['case_id'];s['case_records'].append(e)
 elif suffix=='M10':s['additional_delivery_scores']={'NS':100,'skill':100}
 elif suffix=='M11':s=dict(reversed(list(s.items())))
 elif suffix=='M12':s['NS']=list(reversed(s['NS']));s['skill']=list(reversed(s['skill']))
 elif suffix=='Q13':s['skill_Q']=list(reversed(s['skill_Q']))
 elif suffix=='Q14':s['skill_Q']=[None if v is None else 100 for v in s['skill_Q']]
 elif suffix in {'Q15','E20'}:
  def z(v):
   if isinstance(v,dict):return {k:z(w) for k,w in v.items()}
   if isinstance(v,list):return [z(w) for w in v]
   return 0.0 if type(v) in {int,float} and v==0 else v
  s=z(s)
 elif suffix=='Q16':s['process_exit_code']=19
 elif suffix=='E17':s['one_time_breakdown']={'construction':20,'training':40}
 elif suffix=='E19':s['planned_uses']+=5
 elif suffix=='A21':
  e=deepcopy(s['final_artifact_receipts'][0]);e['display_name']='duplicate-unqualified';s['final_artifact_receipts'].append(e)
 elif suffix=='A22':
  e=deepcopy(s['final_artifact_receipts'][0]);e['display_name']='duplicate-qualified';s['final_artifact_receipts'].append(e)
 elif suffix=='A23':s['allocation_references'][0]['fraction']=0.25;s['allocation_references'][1]['fraction']=0.75
 elif suffix=='A24':s['final_artifact_receipts'][0]['display_name']='renamed-qualified'
 else:raise AssertionError(('UNKNOWN_AUTHORED_NUISANCE',case_id))
 return s

def audit_current_rows(rows,pairs,nuisance,subject):
 failures=[];counts=Counter();byid={r['id']:r for r in rows};keep=[];numeric=0;intent_checks=0;numeric_guard_blockers=0
 def fail(ident,code):failures.append({'case_id':ident,'code':code})
 for r in rows:
  ident=r['id'];s=r['point_time_state'];x=s['facts'];k=s['request_kind'];t=r['target'];d=t['D'];v=d.get('derived_values',{})
  counts[k]+=1
  if r['enterprise_source_ids'] or r['provenance']['recorded_native_execution'] or r['provenance']['recorded_teacher_R']:fail(ident,'FALSE_ORIGINAL_PROVENANCE')
  if d.get('real_skill_qualified_claim') is not False or d.get('scope')!='SYNTHETIC_GIVEN_POLICY_ONLY':fail(ident,'FALSE_REAL_SKILL_CLAIM')
  if {'expected_decision','target','critical_reason','required_semantics'}&s.keys():fail(ident,'ANSWER_IN_POINT_STATE')
  call=t.get('native_tool_intent')
  if call:
   intent_checks+=1;a=call['arguments']
   if call['name']=='sessions_spawn':
    for dimension in ['seconds','requests','io_tokens']:
     if 'required_'+dimension in x and ('remaining_'+dimension not in x or x['remaining_'+dimension]<x['required_'+dimension]):fail(ident,'SPAWN_EXCEEDS_GLOBAL_'+dimension.upper())
    if not(0<a['runTimeoutSeconds']<=x['remaining_seconds']):fail(ident,'SPAWN_TIMEOUT_BOUND')
    if x.get('same_task_active_children'):fail(ident,'DUPLICATE_ACTIVE_SPAWN')
   elif call['name']=='subagents' and a.get('action')=='wait':
    if not(0<a['timeoutSeconds']<=60 and a['timeoutSeconds']<=x['remaining_seconds']):fail(ident,'WAIT_TIMEOUT_BOUND')
    if not a.get('taskIds') or any(v is None for v in a['taskIds']):fail(ident,'WAIT_UNKNOWN_CHILD')
  if d['decision']=='KEEP':
   keep.append(ident)
   if k=='quality_threshold':
    required=['same_input','same_version','independent_consumer','delivery_success','costs_complete']
    ok=all(x.get(z) is True for z in required) and D(x['quality_score'])>=D(s['policy']['q_min']) and D(x['skill_total_cost'])<D(x['baseline_total_cost'])
   elif k=='delivery_success':
    required=['same_input','same_version','independent_consumer','delivery_accepted','costs_complete']
    ok=all(x.get(z) is True for z in required) and D(x['quality_score'])>=D(s['policy']['q_min']) and D(x['skill_total_cost'])<D(x['baseline_total_cost'])
   elif k=='dominated_cost':
    ok=all(x.get(z) is True for z in ['quality_equal','delivery_both_success','matched_independent_consumer','costs_complete']) and D(x['baseline_quality'])==D(x['skill_quality']) and D(x['skill_cost'])<D(x['baseline_cost']) and x['skill_seconds']<=x['baseline_seconds'] and x['cost_scope']=='ALL_INCLUSIVE_MATCHED_TRIAL_TOTAL'
   elif k=='amortization':
    ok=all(x.get(z) is True for z in ['quality_equal','delivery_both_success','matched_independent_consumer']) and D(x['quality_score'])>=D(s['policy']['q_min']) and D(x['future_tasks'])*(D(x['baseline_per_task'])-D(x['skill_per_task']))>D(x['fixed_cost']) and x['fixed_cost_scope']=='ALL_FIXED_EXPENSES_INCLUDING_FAILURES'
   else:ok=False
   if not ok:fail(ident,'KEEP_PREMISES_OR_STRICT_BENEFIT_NOT_ENTAILED')
  comparison_blocked=False
  if k=='amortization' and getattr(subject,'_qa_has_combined_policy_guards',False):
   fields=['quality_equal','matched_independent_consumer','same_version','delivery_both_success','fixed_cost_prospective_not_sunk']
   comparison_blocked=any(x.get(z) is not True for z in fields) or x.get('tested_version_sha256')!=x.get('current_version_sha256')
   if comparison_blocked:
    numeric_guard_blockers+=1
    if d['decision']!='HOLD' or t.get('native_tool_intent') is not None:fail(ident,'INELIGIBLE_COMPARISON_NOT_BLOCKED')
    if any(z in v for z in ['strict_break_even_tasks','break_even_tasks','cost_per_qualified_skill']):fail(ident,'INELIGIBLE_COMPARISON_REPORTED_AS_CALCULATED_POLICY')
  if k in {'amortization','qualified_denominator','shared_cost'} and not comparison_blocked:
   numeric+=1
   # Apply the independent checker to stored targets, not a re-call of solve.
   for error in check_response(s,{'status':'RETURNED','result':t,'input_unchanged':True}):fail(ident,error)
  if k=='cost_known':
   numeric+=1
   if x['repair_cost'] is None:
    if d['decision']!='HOLD' or 'total_cost' in v:fail(ident,'MISSING_REPAIR_FEE_TREATED_AS_ZERO')
   elif d['decision']!='ACCOUNT' or D(v['total_cost'])!=sum((D(x[z]) for z in ['make_cost','repair_cost','consume_cost']),D(0)):fail(ident,'MAKE_REPAIR_CONSUME_SUM')
  if k=='consumer_identity' and x['consumer_content_sha256']!=x['construction_content_sha256'] and d['decision']!='INSPECT':fail(ident,'DIFFERENT_CONTENT_WASHED_AS_INDEPENDENCE')
  if k=='closure_truth' and x['artifact_exists'] and d['next_step']!='REPORT_EXISTS_BUT_UNVALIDATED':fail(ident,'EXISTENCE_WASHED_AS_ACCEPTED_DELIVERY')
 for pair in pairs['pairs']:
  a,b=[byid[z] for z in pair['case_ids']];x=a['point_time_state']['facts'];y=b['point_time_state']['facts']
  diff=[z for z in set(x)|set(y) if x.get(z)!=y.get(z)]
  if len(diff)!=1 or pair['changed_field']!='facts.'+diff[0]:fail(pair['pair_id'],'NOT_ONE_VISIBLE_PREMISE')
  if a['target']['D']['decision']==b['target']['D']['decision']:fail(pair['pair_id'],'NO_OBSERVED_CONDITIONAL_DECISION_CHANGE')
 nuisance_checks=[]
 for item in nuisance['variants']:
  original=byid[item['case_id']];state=item['perturbed_point_time_state'];before=deepcopy(original['point_time_state'])
  changes=[z for z in set(state)|set(before) if state.get(z)!=before.get(z)]
  actual=call_subject(subject,state)
  ok=changes==['display_name'] and actual['status']=='RETURNED' and canonical(actual['result'])==canonical(original['target'])
  if not ok:fail(original['id'],'QA_NUISANCE_TARGET_CHANGED_OR_NOT_ONLY_DISPLAY_NAME')
  nuisance_checks.append({'case_id':original['id'],'status':'PASS' if ok else 'FAIL'})
 return {'status':'PASS_CURRENT_ROWS_SCOPED_INVARIANTS' if not failures else 'FAIL_CURRENT_ROWS_INVARIANTS',
  'rows':len(rows),'families':dict(counts),'keep_targets':len(keep),'keep_ids':keep,'independent_numeric_target_checks':numeric,
  'additional_arithmetic_policy_blockers_checked_without_requiring_values':numeric_guard_blockers,
  'native_intents_checked_without_execution':intent_checks,'counterfactual_pairs_checked':len(pairs['pairs']),
  'nuisance_actual_solver_calls':len(nuisance_checks),'nuisance_all_passed':all(x['status']=='PASS' for x in nuisance_checks),
  'failures':failures,'scope_warning':'These are finite conditional policy fixtures. Counts do not establish multi-turn native autonomous ability or real utility.'}

def composite_probes(rows,subject):
 """Fresh QA-only combined boundaries beyond the generated one-field pairs."""
 probes=[]
 def record(base,field,value,claim):
  s=deepcopy(base['point_time_state']);s['facts'][field]=deepcopy(value)
  response=call_subject(subject,s);bad=[]
  if response['status']!='RETURNED':bad.append('SUBJECT_EXCEPTION_INSTEAD_OF_SAFE_DISPOSITION')
  else:
   t=response['result'];intent=t.get('native_tool_intent');x=s['facts']
   if claim=='NO_KEEP' and t['D']['decision']=='KEEP':bad.append('KEEP_WITH_FALSE_GIVEN_PREREQUISITE')
   if claim=='HARD_BUDGET':
    if intent is not None:bad.append('NATIVE_INTENT_DESPITE_EXHAUSTED_OR_INSUFFICIENT_COMPOSITE_BUDGET')
    if t['D']['decision'] not in {'HOLD','STOP','REPORT_PARTIAL'}:bad.append('BUDGET_GAP_NOT_REPORTED')
  probes.append({'base_case_id':base['id'],'request_kind':s['request_kind'],'changed_field':field,
   'changed_value':value,'required_global_property':claim,'point_time_state':s,'response':response,
   'status':'PASS' if not bad else 'FAIL','failures':bad,
   'scope':'NEW_QA_ONLY_COMPOSITE_NOT_A_CLAIM_THAT_CURRENT_GENERATED_ROW_WAS_WRONG'})
 for kind in ['dispatch_time','dispatch_requests','dispatch_io','skill_actual_read']:
  base=next(r for r in rows if r['point_time_state']['request_kind']==kind and r['target']['D']['decision']=='DISPATCH')
  for dimension in ['seconds','requests','io_tokens']:
   required=base['point_time_state']['facts'].get('required_'+dimension)
   if required is not None:record(base,'remaining_'+dimension,max(0,required-1),'HARD_BUDGET')
 for kind in ['active_duplicate','unknown_child_identity']:
  base=next(r for r in rows if r['point_time_state']['request_kind']==kind and r['target']['D']['decision']=='WAIT')
  record(base,'remaining_seconds',0,'HARD_BUDGET')
 for kind,fields in [('quality_threshold',['same_input','costs_complete']),('delivery_success',['same_version','independent_consumer']),
                     ('dominated_cost',['quality_equal','matched_independent_consumer']),('amortization',['quality_equal','matched_independent_consumer'])]:
  base=next(r for r in rows if r['point_time_state']['request_kind']==kind and r['target']['D']['decision']=='KEEP')
  for field in fields:record(base,field,False,'NO_KEEP')
 return {'status':'PASS_COMPOSITE_BOUNDARIES' if all(p['status']=='PASS' for p in probes) else 'COMPOSITE_GAPS_FOUND',
  'count':len(probes),'passed':sum(p['status']=='PASS' for p in probes),'failed':sum(p['status']=='FAIL' for p in probes),
  'probes':probes,'not_training_rows':True,'student_model_effect_measured':False}

def main(a):
 a.out.mkdir(parents=True,exist_ok=False)
 qa=load(a.case_root/'GENERATION_QA.json');raw=a.source.read_bytes();source_sha=hashlib.sha256(raw).hexdigest()
 pins={'source':str(a.source.resolve()),'source_sha256':source_sha,'declared_source_sha256':qa['generator_sha256'],
  'case_root':str(a.case_root.resolve()),'cases_sha256':digest(a.case_root/'CASES.jsonl'),
  'declared_cases_sha256':qa['cases_sha256'],'challenge_sha256':digest(a.challenges),'checker_sha256':digest(__file__)}
 save(a.out/'INPUT_PINS.json',pins)
 assert source_sha==qa['generator_sha256'], 'SOURCE_NOT_EXACTLY_THE_FROZEN_CASE_GENERATOR'
 assert pins['cases_sha256']==qa['cases_sha256'], 'CASES_PIN_MISMATCH'
 (a.out/'SUBJECT_SOURCE_SNAPSHOT.py').write_bytes(raw)
 subject=types.ModuleType('trusted_research_controller_under_test');subject.__file__=str(a.source.resolve())
 old=sys.dont_write_bytecode;sys.dont_write_bytecode=True
 try:exec(compile(raw,str(a.source.resolve()),'exec'),subject.__dict__)
 finally:sys.dont_write_bytecode=old
 subject._qa_has_combined_policy_guards=b'fixed_cost_prospective_not_sunk' in raw and b'dispatching=k in' in raw
 challenge=load(a.challenges);results=[]
 for item in challenge['cases']:
  # Only these two clean objects enter adaptation and root solve; audit answers
  # are used after the plan and subject call have been constructed and run.
  pid=item['policy_id'];state=deepcopy(item['visible_state'])
  base=evaluate_challenge(subject,pid,state,item['expected_decision'])
  changed=apply_counterfactual(state,item['counterfactual']['changes'])
  counter=evaluate_challenge(subject,pid,changed,item['counterfactual']['expected_decision'])
  perturb=nuisance_state(item['id'],state)
  other=evaluate_challenge(subject,pid,perturb,item['expected_decision'])
  comparable=base['adaptation_mode']=='FULL' and other['adaptation_mode']=='FULL'
  invariant_ok=None
  if comparable:
   original=[c['response'] for c in base['calls']];nuisance=[c['response'] for c in other['calls']]
   invariant_ok=canonical(original)==canonical(nuisance)
  results.append({'case_id':item['id'],'mechanism_family':item['mechanism_family'],'base':base,'counterfactual':counter,
   'nuisance':other,'invariance_comparable':comparable,'invariance_passed':invariant_ok,
   'audit_expected_decision_not_input':item['expected_decision']})
 save(a.out/'AUTHORED24_ACTUAL_SUBJECT_COMPARISONS.json',{'results':results,'not_comparable_not_counted_as_pass':True})
 rows=[json.loads(line) for line in (a.case_root/'CASES.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
 current=audit_current_rows(rows,load(a.case_root/'COUNTERFACTUAL_PAIRS.json'),load(a.case_root/'NUISANCE_QA_ONLY.json'),subject)
 save(a.out/'CURRENT512_INDEPENDENT_INVARIANTS.json',current)
 probes=composite_probes(rows,subject);save(a.out/'NEW_COMPOSITE_BOUNDARY_PROBES.json',probes)
 base_counts=Counter(r['base']['status'] for r in results);counter_counts=Counter(r['counterfactual']['status'] for r in results)
 full_failures=[r['case_id'] for r in results if r['base']['status']=='FAIL' or r['counterfactual']['status']=='FAIL' or r['invariance_passed'] is False]
 summary={'status':'SCOPED_CHALLENGE_AND_CURRENT_FIXTURE_CHECKS_WITH_REPORTED_COMPOSITE_RESULTS',
  'authored_base24_status_counts':dict(base_counts),'authored_counterfactual24_status_counts':dict(counter_counts),
  'full_comparison_failures':full_failures,'comparable_nuisance_count':sum(r['invariance_comparable'] for r in results),
  'comparable_nuisance_all_pass':all(r['invariance_passed'] is not False for r in results),
  'current_rows_actual_count':len(rows),'historical_512_in_output_identifiers_is_not_current_count':True,
  'current512_status':current['status'],'current512_failures':len(current['failures']),
  'new_subject_contract_compatibility_checks_enabled':subject._qa_has_combined_policy_guards,
  'new_composite_status':probes['status'],'new_composite_passed':probes['passed'],'new_composite_failed':probes['failed'],
  'root_source_sha256':source_sha,'current_cases_sha256':pins['cases_sha256'],'independent_challenges_sha256':pins['challenge_sha256'],
  'adapter_receives_audit_answers':False,'adaptation_scopes_not_full_agent_capability':True,
  'challenge_used_for_correction_if_root_changes':True,'actual_native_calls':0,'model_weights_or_training':False,
  'student_model_success_rate_measured':False,'real_qualified_KEEP_added':0}
 save(a.out/'SUMMARY.json',summary);print(json.dumps(summary,ensure_ascii=False))
 assert digest(a.source)==source_sha, 'SOURCE_CHANGED_DURING_QA_FROZEN_OUTPUTS_RETAINED'

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--source',type=Path,required=True)
 p.add_argument('--case-root',type=Path,required=True)
 p.add_argument('--challenges',type=Path,default=ROOT/'output/20261031_wrd_curation11/independent_challenges/CHALLENGES.json')
 p.add_argument('--out',type=Path,default=ROOT/'output/20261031_wrd_curation11/independent_challenge_execution/run01')
 main(p.parse_args())
