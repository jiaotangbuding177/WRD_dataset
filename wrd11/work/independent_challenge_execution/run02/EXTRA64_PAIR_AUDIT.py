"""Independent integrity check of the two additional negative-pair manifests.

No solver re-call, expected answer adaptation, native tool or training.
"""
from pathlib import Path
from collections import Counter
import hashlib,json
ROOT=Path('D:/skillloop/output/20261031_wrd_curation11/controller_cases/run07')
OUT=Path(__file__).parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
rows=[json.loads(v) for v in (ROOT/'CASES.jsonl').read_text(encoding='utf-8').splitlines() if v]
counts=Counter(r['id'] for r in rows);assert len(rows)==576 and set(counts.values())=={1}
byid={r['id']:r for r in rows};details=[]
for filename,positive_decision in [('CROSS_CONDITION_PAIRS.json','DISPATCH'),('POLICY_GUARD_PAIRS.json','KEEP')]:
 spec=load(ROOT/filename);assert len(spec['pairs'])==32
 for pair in spec['pairs']:
  a,b=byid[pair['positive_case_id']],byid[pair['negative_case_id']]
  sa,sb=a['point_time_state'],b['point_time_state'];xa,xb=sa['facts'],sb['facts']
  errors=[];delta=[k for k in set(xa)|set(xb) if xa.get(k)!=xb.get(k)]
  if len(delta)!=1 or pair['changed_field']!='facts.'+delta[0]:errors.append('NOT_ONE_VISIBLE_FACT')
  if {k:v for k,v in sa.items() if k!='facts'}!={k:v for k,v in sb.items() if k!='facts'}:errors.append('OTHER_POINT_STATE_CHANGE')
  if a['synthetic_root_id']!=b['synthetic_root_id']:errors.append('GROUP_CHANGED')
  if a['target']['D']['decision']!=positive_decision or b['target']['D']['decision']!='HOLD':errors.append('WRONG_CONDITIONAL_DISPOSITION')
  if b['target'].get('native_tool_intent') is not None:errors.append('NEGATIVE_STILL_ISSUES_TOOL_INTENT')
  if counts[a['id']]!=1:errors.append('DUPLICATED_POSITIVE_ROW')
  if filename=='CROSS_CONDITION_PAIRS.json':
   if not any(xb['remaining_'+dim]<xb['required_'+dim] for dim in ['seconds','requests','io_tokens']):errors.append('NO_ACTUAL_HARD_BUDGET_GAP')
  elif delta and xb[delta[0]] is not False:errors.append('POLICY_GIVEN_NOT_FALSE')
  details.append({'manifest':filename,'positive_id':a['id'],'negative_id':b['id'],'changed_field':delta,
   'status':'PASS' if not errors else 'FAIL','failures':errors})
result={'status':'PASS_64_NEW_NEGATIVE_ONE_PREMISE_PAIRS' if all(r['status']=='PASS' for r in details) else 'FAIL',
 'rows_current':len(rows),'additional_pairs_checked':len(details),'existing_pairs_checked_in_main_audit':256,
 'combined_pair_links_checked':256+len(details),'positive_training_rows_not_duplicated':True,
 'cases_sha256':sha(ROOT/'CASES.jsonl'),'extra_pair_manifest_sha256':{n:sha(ROOT/n) for n in ['CROSS_CONDITION_PAIRS.json','POLICY_GUARD_PAIRS.json']},
 'details':details,'checker_sha256':sha(__file__),'native_calls':0,'training_started':False}
p=OUT/'EXTRA64_PAIR_QA.json';assert not p.exists();p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='details'},ensure_ascii=False))
