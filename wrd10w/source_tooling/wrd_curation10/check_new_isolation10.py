"""Isolation-only fingerprint scan of explicit newly compiled train inputs.

Protected original users/materials are only a forbidden-match basis; no grades,
protected assistant answers or hidden thoughts are used to teach the model.
"""
from pathlib import Path
from collections import Counter
import argparse,gzip,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[3];DATA=ROOT/'output/20261027_wrd_main_v10';WORK=ROOT/'output/20261031_wrd_curation10'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return[json.loads(l)for l in gzip.open(p,'rt',encoding='utf-8-sig')if l.strip()]
def pin(p):p=Path(p);b=p.read_bytes();return{'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def main(a):
 p=ROOT/'research/data_prep/wrd_curation10/lineage_recheck.py';s=importlib.util.spec_from_file_location('isolation10_reused_basis',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 protected=m.original_user_basis();ep,einfo=m.get_eval_basis()
 catalog=load(ROOT/'output/20261031_wrd_curation09/holdout/TASK_CATALOG_ALL36_05.json')
 reserved={s for r in catalog for s in r['reserved_source_ids']}
 assert len(reserved)==40
 forbidden=set(protected['forbidden'])|reserved|{'conv_34b56ae9c535'}
 closure=load(ROOT/'output/20261031_wrd_curation09/holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json')
 forbidden.update(closure['revoke_source_ids'])
 scopes={r['source_id']:r for r in rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
 forbidden_groups={scopes[s]['component_id']for s in forbidden if s in scopes}
 report=load(a.report);hits=[];record_ids=[]
 for ref in report['files']:
  pp=a.report.parent/ref['path'];assert pin(pp)['sha256']==ref['sha256']and pp.stat().st_size==ref['bytes']
  for r in rows(pp):
   record_ids.append(r['id']);assert not forbidden.intersection(r['source_ids'])
   assert all(scopes[s]['status']=='TRAIN'for s in r['source_ids'])
   assert not forbidden_groups.intersection(scopes[s]['component_id']for s in r['source_ids'])
   for basis,patterns in [('PROTECTED_ORIGINAL_USER_ISOLATION',protected['patterns']),('COMPONENT_EVAL_ORIGINAL_INPUT_MATERIAL',ep)]:
    for hit in m.scan_messages(r['messages'],patterns):hits.append({'record_id':r['id'],'basis':basis,**hit})
 result={'status':'PASS_NO_EXACT_PROTECTED_OR_COMPONENT_EVAL_INPUT_MATCH'if not hits else'ROOT_REVIEW_REQUIRED_EXACT_MATCHES_NOT_AUTOMATIC_CONTAMINATION',
  'new_compilation_report':pin(a.report),'record_ids':record_ids,'records':len(record_ids),'matches':hits,
  'protected_original_users':protected['users'],'protected_sources':len(protected['forbidden']),
  'new_reserved_source_ids':['conv_34b56ae9c535'],'known_old_reserved_source_ids':len(reserved),
  'whole_unknown_ancestry_not_proven_clean_by_absence_of_match':True,
  'all_functional_state_origin_limits_preserved':True,'grade_or_protected_assistant_used':False,'training_started':False,'script':pin(__file__)}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({'status':result['status'],'records':len(record_ids),'exact_matches':len(hits)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--out',type=Path,required=True);main(p.parse_args())
