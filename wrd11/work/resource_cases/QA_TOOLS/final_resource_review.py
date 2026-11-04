"""Read-only byte, Unicode, timing and resource-body audit for frozen run02."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,importlib.util,json,re,sys
ROOT=Path('D:/skillloop')
BASE=ROOT/'output/20261031_wrd_curation11/resource_cases/run02'
OUT=BASE.parent/'FINAL_RESOURCE_REVIEW.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def text_sha(s):return hashlib.sha256(s.encode()).hexdigest()
def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))

def main():
 assert not OUT.exists()
 src=ROOT/'research/data_prep/wrd_curation11/resource_cases11.py'
 q=load(BASE/'CPU_CASES_QA.json');assert sha(src)==q['source_code']['sha256']
 rows=[json.loads(line) for line in (BASE/'CASES.jsonl').read_text(encoding='utf-8').splitlines()]
 spec=importlib.util.spec_from_file_location('trusted_new_fixture_builder',src)
 mod=importlib.util.module_from_spec(spec);sys.dont_write_bytecode=True;spec.loader.exec_module(mod)
 families={f['family_id']:f for f in mod.families()}
 bad_markers=['\ufffd','锟斤拷','Ã','Â']
 file_count=0;marker_hits=[];surrogates=[]
 for p in BASE.rglob('*'):
  if not p.is_file():continue
  if p.suffix not in ['.json','.jsonl','.md','.py'] and p.name not in ['stdout.bin','stderr.bin']:continue
  data=p.read_bytes();s=data.decode('utf-8',errors='strict');file_count+=1
  for marker in bad_markers:
   if marker in s:marker_hits.append({'path':str(p),'marker_codepoints':[hex(ord(c)) for c in marker]})
  if re.search('[\ud800-\udfff]',s):surrogates.append(str(p))
 assert not marker_hits and not surrogates
 write_count=0;future_separated=0;allpins=0
 duplicates=defaultdict(list);reasoning_duplicates=defaultdict(list)
 for row in rows:
  f=families[row['family_id']];st=row['point_time_state']
  assert st['resource_contract']==f['mechanism']
  assert st['declared_fixture_inputs']==f['fixtures']
  assert st['expected_local_outputs']==f['expected']
  assert st['resource_file']['sha256']==text_sha(st['resource_file']['content'])
  assert st['visible_run']['program']['sha256']==st['resource_file']['sha256']
  assert row['target']['new_author_reasoning'] is True
  assert any('\u4e00'<=c<='\u9fff' for c in row['target']['R'])
  assert row['provenance']['proposed_supervision_weight']==0.05
  assert 'target' not in st and 'rejected_alternative' not in st and 'future_same_input_credit_evidence' not in st
  for proof in row['available_evidence_pins']:
   p=proof['pin'];assert sha(p['path'])==p['sha256'] and Path(p['path']).stat().st_size==p['bytes'];allpins+=1
  act=row['target'].get('resource_action_projection')
  if act:
   write_count+=1;version=BASE/'families'/f['family_id']/'versions/v1/resource.py'
   assert act['content']==version.read_text(encoding='utf-8')
   assert act['content_sha256']==sha(version)==text_sha(act['content'])
   assert act['path']=='resources/'+f['family_id']+'/resource.py' and not Path(act['path']).is_absolute()
   fut=row['validation']['future_same_input_credit_evidence']['pin']
   assert sha(fut['path'])==fut['sha256']
   assert st['current_version']=='v0' and not st['visible_prior_runs']
   assert fut['sha256'] not in [e['pin']['sha256'] for e in row['available_evidence_pins']]
   assert st['resource_file']['sha256']!=act['content_sha256'];future_separated+=1
  duplicates[canonical(st)].append(row['id']);reasoning_duplicates[row['target']['R']].append(row['id'])
 case_duplicates=[ids for ids in duplicates.values() if len(ids)>1]
 reason_duplicates=[ids for ids in reasoning_duplicates.values() if len(ids)>1]
 assert len(case_duplicates)==10 and all(len(ids)==2 for ids in case_duplicates)
 cost_rows=[r for r in rows if r['id'].endswith('-cost_unknown_hold')]
 assert len(cost_rows)==10 and len({r['target']['R'] for r in cost_rows})==1
 result={'status':'PASS_FROZEN_RESOURCE_BYTES_UNICODE_VERSION_AND_FUTURE_SEPARATION_WITH_CONVERSION_REQUIREMENTS',
  'cases':len(rows),'families':len(families),'strict_UTF8_text_files_checked':file_count,
  'replacement_character_or_mojibake_marker_hits':marker_hits,'surrogate_codepoint_hits':surrogates,
  'exact_resource_contracts_equal_authored_source':True,'actual_evidence_pins_checked':allpins,
  'write_targets_full_v1_source_body_and_SHA_verified':write_count,
  'future_v1_receipts_only_in_audit_not_v0_input':future_separated,
  'duplicate_pointstate_pairs':case_duplicates,
  'conversion_requirement':'For each diagnose/write pair, root must add distinct explicit user task: decision-only vs repair/write. Do not compile identical input with conflicting output objectives.',
  'declared_local_expected_outputs_are_user_fixture_contract_not_decision_labels':True,
  'all_exact_reasoning_duplicate_groups':reason_duplicates,
  'ten_cost_R_exact_duplicate_case_ids':[r['id'] for r in cost_rows],
  'cost_case_recommendation':'Choose one or sample as correlated auxiliary views; duplicated generic cost/local-pass reasoning is not independent experience.',
  'audit_initial_assumption_correction':'First audit expected only cost R to duplicate; local-pass R with equal check totals also duplicates. Audit assumption corrected, frozen source data unchanged.',
  'business_qualified_KEEP_count':0,'native_agent_trace_count':0,
  'training_admission_granted':False,'new_or_weighted_training_started':False,
  'frozen_case_source':pin(BASE/'CASES.jsonl'),'frozen_CPU_QA':pin(BASE/'CPU_CASES_QA.json'),
  'builder_source':pin(src),'review_source':pin(Path(__file__))}
 OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:result[k] for k in ['status','cases','families','strict_UTF8_text_files_checked','write_targets_full_v1_source_body_and_SHA_verified','future_v1_receipts_only_in_audit_not_v0_input']}))
if __name__=='__main__':main()
