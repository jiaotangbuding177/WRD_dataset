"""Freeze reviewed real files and exact encrypted-audit URL exceptions.

No key/config read, encryption, model, training or Git action occurs here.
"""
from pathlib import Path
from collections import Counter
import gzip,hashlib,importlib.util,json,re
ROOT=Path(__file__).resolve().parents[3];DATA=ROOT/'output/20261027_wrd_main_v10'
WORK=ROOT/'output/20261031_wrd_curation09';DEL=ROOT/'output/20261031_wrd_curation09_delivery';BASE=ROOT/'output/wrd08root01'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def main():
 assert load(WORK/'full_stage_qa02/INDEPENDENT_FULL_STAGED_REBASE09_QA.json')['status'].startswith('PASS')
 assert sha(DATA/'TRAINING_MANIFEST.json')=='01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42'
 snapshot=load(DEL/'EXPLICIT_EVIDENCE_CANDIDATES09.json');entries={};aliases=[];exports=[]
 def add(name,path,category,public=None):
  p=Path(path).resolve();assert p.is_file()and name not in entries
  assert not any(s in p.parts for s in ['__pycache__','.git','private','local_delivery_key'])and p.suffix!='.pyc'
  entries[name]={'path':name,'source':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'category':category}
  aliases.append({'original_absolute_path':str(p),'archive_path':name,'sha256':sha(p)})
  if public:exports.append({'archive_path':name,'path':public,'root_reviewed_public':True})
 def tree(prefix,p,category):
  for f in sorted(p.rglob('*')):
   if f.is_file()and '__pycache__'not in f.parts and f.suffix!='.pyc':add(prefix+'/'+f.relative_to(p).as_posix(),f,category)
 for r in snapshot['files']:
  p=Path(r['absolute_path']);assert sha(p)==r['sha256']and p.stat().st_size==r['bytes'],'EVIDENCE_CHANGED_AFTER_SNAPSHOT'
  relative=p.relative_to(WORK).as_posix();add('evidence09/'+relative,p,'CONTROLLED_AUDIT')
 for n in ['TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json']:add(n,DATA/n,'TRAINING',n)
 for p in sorted((DATA/'compiled').glob('curation09_*')):tree('compiled/'+p.name,p,'TRAINING')
 tree('canonical_arrays09',DATA/'canonical_arrays09','CANONICAL_ARRAY')
 tree('manifest_staging09',DATA/'manifest_staging09','QA')
 tree('manifest_history/pre_curation09_cbb233f2a44bcb61',DATA/'manifest_history/pre_curation09_cbb233f2a44bcb61','CONTROLLED_AUDIT')
 tree('source_tooling/wrd_curation09',ROOT/'research/data_prep/wrd_curation09','TOOLING')
 tree('design_reference/curation09_plan',ROOT/'research/plans/20261031_wrd_curation09','DESIGN')
 for n in ['A_B_MODULES.md','PIPELINE.md']:add('design_reference/'+n,ROOT/'research/designs'/n,'DESIGN')
 tree('design_reference/history49',ROOT/'research/designs/history/5.0.49/curation09_20261031','DESIGN')
 tree('design_reference/history50',ROOT/'research/designs/history/5.0.50/curation09_before_final_summary','DESIGN')
 add('design_reference/MEMORY09.md',ROOT/'research/memory/2026-10-31_wrd_curation09.md','DESIGN')
 for n in ['verify_remote09.py','verify_metadata_followup09.py']:add('tooling/'+n,DEL/n,'TOOLING','tooling/'+n)
 for n in ['CONTRACT.md','PORT_REVIEW09.json']:
  add('quality09/remote_preparation/'+n,DEL/'remote_preparation'/n,'QA')
 for name,source,public in [
  ('tooling/merge_delta09.py',ROOT/'research/data_prep/wrd_curation09/merge_delta09.py','tooling/merge_delta09.py'),
  ('tooling/checkpoint_loader.py',ROOT/'research/data_prep/wrd_curation09/verify_main09.py','tooling/checkpoint_loader.py'),
  ('tooling/restore_checkpoint.py',ROOT/'output/20261025_wrd_training_dataset/git_release/dataset/20261029_v10_checkpoint05/tooling/restore_checkpoint.py','tooling/restore_checkpoint.py'),
  ('quality09/README.md',DEL/'prepared_public/README.md','README.md'),
  ('quality09/ACTIVE_USE_ERRATUM09.md',DEL/'prepared_public/ACTIVE_USE_ERRATUM09.md','ACTIVE_USE_ERRATUM09.md'),
 ]:add(name,source,'TOOLING'if name.startswith('tooling/')else'QA',public)
 public_refs={
  'design_reference/curation09_plan/TRAINING_STRATEGY_09.md':'TRAINING_PLAN.md',
  'design_reference/curation09_plan/ACTUAL_DATA_REPORT.md':'ACTUAL_DATA_REPORT.md',
  'evidence09/ACTUAL_DATA_AND_COVERAGE09.json':'ACTUAL_DATA_AND_COVERAGE09.json',
  'evidence09/full_stage_qa02/INDEPENDENT_FULL_STAGED_REBASE09_QA.json':'FULL_STAGED_DATA_QA.json',
  'evidence09/eval_input_arrays09/BUILD_QA.json':'EVAL_INPUT_ARRAYS_QA.json',
  'evidence09/process/batch02/FINAL_1321_LEDGER_REVIEW.json':'PROCESS1321_REVIEW_SUMMARY.json',
  'evidence09/reasoning/ORIGINAL26_IDENTITY_PARTITION_RECHECK09.json':'ORIGINAL26_RECHECK.json',
 }
 # Detailed aliases/private proof are encrypted, not public exports.
 for name,public in public_refs.items():assert name in entries;exports.append({'archive_path':name,'path':public,'root_reviewed_public':True})
 exports.append({'archive_path':'design_reference/curation09_plan/TRAINING_STRATEGY_09.md','path':'TRAINING_STRATEGY_09.md','root_reviewed_public':True})
 alias=DEL/'EVIDENCE_PATH_ALIASES09.json';save(alias,{'schema':'wrd-original-source-to-restored09-paths','aliases':aliases,'audit_never_default_training':True})
 add('EVIDENCE_PATH_ALIASES09.json',alias,'QA')
 pattern=re.compile(rb'https?://[^\s"\x27<>]{1,8192}[?&](?:x-amz-signature|x-amz-credential|signature|sig|access_token|api_key|apikey|token|key-pair-id)=[^&\s"\x27<>]{8,}',re.I)
 policies=[]
 public_archives={e['archive_path']for e in exports}
 for r in entries.values():
  p=Path(r['source']);raw=p.read_bytes();layers=[('raw',raw)]
  if raw[:2]==b'\x1f\x8b':layers.append(('gzip_decoded',gzip.decompress(raw)))
  matches=Counter((layer,hashlib.sha256(m.group()).hexdigest())for layer,b in layers for m in pattern.finditer(b))
  if matches:
   assert r['category']=='CONTROLLED_AUDIT'and r['path']not in public_archives,('SENSITIVE_URL_OUTSIDE_ENCRYPTED_AUDIT',r['path'])
   policies.append({'archive_path':r['path'],'source_sha256':r['sha256'],'matches':[{'layer':l,'match_sha256':h,'count':n}for(l,h),n in sorted(matches.items())]})
 policy_sha=hashlib.sha256(json.dumps(policies,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
 allow={'schema':'wrd-delta09-root-frozen-allowlist-v1','base_checkpoint_required':'05_plus_06_plus_07_plus_08_authenticated_merged_root',
  'base_payload_manifest_sha256':sha(BASE/'PAYLOAD_MANIFEST.json'),'base_training_manifest_sha256':sha(BASE/'TRAINING_MANIFEST.json'),
  'current_training_manifest_sha256':sha(DATA/'TRAINING_MANIFEST.json'),'canonical_index_relative_path':'canonical_arrays09/ARRAY_INDEX09.json',
  'canonical_pin_relative_path':'canonical_arrays09/INDEX_PIN09.json','canonical_index_sha256':sha(DATA/'canonical_arrays09/ARRAY_INDEX09.json'),
  'encrypted_audit_url_policy':'POTENTIALLY_SENSITIVE_EMBEDDED_URLS_ENCRYPTED_ONLY','encrypted_audit_url_exceptions':policies,
  'files':list(entries.values()),'public_exports':exports,'actual_counts':load(DATA/'TRAINING_MANIFEST.json')['actual_counts'],'training_started':False,'is_training_launcher':False}
 p=DEL/'ROOT_ALLOWLIST09.json';save(p,allow)
 freeze={'status':'ROOT_FROZEN_ALLOWLIST_APPROVED_FOR_PACKAGE09','allowlist_sha256':sha(p),
  **{k:allow[k]for k in ['base_payload_manifest_sha256','base_training_manifest_sha256','current_training_manifest_sha256','canonical_index_sha256']},
  'execution_scope':'Authenticated offline data delivery only; no model weights, training or new business collection',
  'encrypted_audit_url_policy':allow['encrypted_audit_url_policy'],'encrypted_audit_url_exceptions_sha256':policy_sha,'source_code_sha256':sha(__file__),'training_started':False}
 save(DEL/'ROOT_FREEZE_RECEIPT09.json',freeze)
 save(DEL/'ALLOWLIST_PREPARATION09.json',{'status':'EXPLICIT_SNAPSHOT_REHASHED_AND_ENCRYPTED_AUDIT_URL_POLICY_FROZEN_PENDING_CREDENTIAL_SCAN_AND_BUILD',
  'files':len(entries),'source_bytes':sum(r['bytes']for r in entries.values()),'encrypted_audit_URL_files':len(policies),
  'encrypted_audit_URL_occurrences':sum(x['count']for p in policies for x in p['matches']),'policy_sha256':policy_sha,'public_exports':len(exports),
  'allowlist_sha256':sha(p),'key_or_config_read':False,'training_started':False})
 print(json.dumps(load(DEL/'ALLOWLIST_PREPARATION09.json')))
if __name__=='__main__':main()
