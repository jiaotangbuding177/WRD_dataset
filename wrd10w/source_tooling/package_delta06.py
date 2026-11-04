"""Publish a small real-data delta; checkpoint05 remains immutable."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,re,shutil,tarfile
ROOT=Path(__file__).resolve().parents[3];DATA=ROOT/'output/20261027_wrd_main_v10';WORK=ROOT/'output/20261029_wrd_delivery06'
RELEASE=ROOT/'output/20261025_wrd_training_dataset/git_release';DEST=RELEASE/'dataset/20261029_v10_checkpoint06';PLAN=ROOT/'research/plans/20261027_wrd_main_v10'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def module(n,p):s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 assert not DEST.exists();stage=WORK/'delta_build';stage.mkdir(exist_ok=False)
 helper=module('package05',ROOT/'research/data_prep/wrd_main_v10/package_checkpoint05.py');needles=helper.credential_needles();entries={};aliases=[]
 def add(n,p):
  p=helper.source_guard(p);b=p.read_bytes();expanded=gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b
  assert not any(k in b or k in expanded for k in needles),'credential value in delta'
  assert not re.search(rb'\bsk-[A-Za-z0-9_-]{24,}\b',expanded),'unreviewed key-shaped value'
  assert n not in entries;entries[n]={'path':n,'source':str(p.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
  aliases.append({'original_absolute_path':str(p.resolve()),'archive_path':n,'sha256':entries[n]['sha256']})
 def tree(n,p):
  for f in sorted(Path(p).rglob('*')):
   if f.is_file()and f.suffix!='.pyc'and'__pycache__'not in f.parts:add(n+'/'+f.relative_to(p).as_posix(),f)
 for n in ['TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json']:add(n,DATA/n)
 tree('compiled/ewi_math_resource_construction_01',DATA/'compiled/ewi_math_resource_construction_01')
 for n in ['20261029_wrd_ewi_probe_recovery','20261029_wrd_ewi_probe_peer_01','20261029_wrd_v9_missing_evidence_recovery','20261029_wrd_v9_missing_evidence_update02','20261029_wrd_missing_lineage_native']:
  tree('evidence06/'+n,ROOT/'output'/n)
 for n in ['A_B_MODULES.md','PIPELINE.md']:add('design_reference/'+n,ROOT/'research/designs'/n)
 for n in ['TRAINING_PLAN.md','COVERAGE_EXPANSION.md','MODEL_INPUT_OUTPUT.md','MODEL_CONTEXT_REQUIREMENTS.md','IMPLEMENTATION_RECORD.json']:add('design_reference/'+n,PLAN/n)
 for n in ['ROOT_MATH_ADMISSION.json','MAIN530_QA.json','CURRENT_DATA_AND_EXPOSURE.json','OWNER_EXPOSURE_SCHEDULE.json','TRAINING_CANDIDATES.json']:add('quality06/'+n,WORK/n)
 for n in ['prepare_delta06.py','package_delta06.py','merge_delta06.py','verify_main05.py']:add('source_tooling/'+n,ROOT/'research/data_prep/wrd_main_v10'/n)
 save(stage/'EVIDENCE_PATH_ALIASES06.json',{'aliases':aliases,'all_newline_and_original_LF_CRLF_identities_preserved':True,'lineage_audit_only_not_training_admission':True});add('EVIDENCE_PATH_ALIASES06.json',stage/'EVIDENCE_PATH_ALIASES06.json')
 base=load(RELEASE/'dataset/20261029_v10_checkpoint05/ENCRYPTED_DELIVERY_REPORT.json')
 refs=list(entries.values())
 pm={'schema':'wrd-base05-authenticated-delta06','base05_payload_manifest_sha256':base['payload_manifest_sha256'],
     'base05_training_manifest_sha256':'f9752b7a14238f07d0b504f83e93d40f13282c878ab2e8b5dcfae844bdc9a82b',
     'base05_ciphertext_sha256':base['ciphertext_sha256'],'files':refs,'actual_targets':530,'actual_supervised_tokens':146999,
     'delta_positive_targets':1,'delta_positive_A_tokens':930,'delta_original_R_positive_tokens':0,
     'ancestry_audits_are_not_positive_examples':True,'training_started':False,'full_WRD_main_training_ready':False}
 save(stage/'PAYLOAD_MANIFEST.json',pm)
 plain=stage/'wrd-v10-delta06.tar.gz'
 with tarfile.open(plain,'w:gz',compresslevel=3,format=tarfile.PAX_FORMAT)as tf:
  tf.add(stage/'PAYLOAD_MANIFEST.json',arcname='PAYLOAD_MANIFEST.json',recursive=False)
  for r in refs:tf.add(r['source'],arcname=r['path'],recursive=False)
 DEST.mkdir(parents=True);(DEST/'controlled').mkdir();(DEST/'tooling').mkdir()
 enc=module('enc06',ROOT/'research/data_prep/wrd_reasoning_v4/encrypted_delivery.py')
 receipt=enc.encrypt(plain,DEST/'controlled/wrd-v10-delta06.tar.gz.aesgcm',ROOT/'output/20261025_wrd_reasoning_recovery_v4/local_delivery_key/wrd-reasoning-v4.key',reuse_key=True)
 receipt.update(payload_manifest_sha256=sha(stage/'PAYLOAD_MANIFEST.json'),authenticated_files=len(refs)+1,base_checkpoint_required='20261029_v10_checkpoint05',training_started=False)
 save(DEST/'ENCRYPTED_DELIVERY_REPORT.json',receipt)
 for n,source in [('restore_checkpoint.py',RELEASE/'dataset/20261029_v10_checkpoint05/tooling/restore_checkpoint.py'),('checkpoint_loader.py',ROOT/'research/data_prep/wrd_main_v10/verify_main05.py'),('merge_delta.py',ROOT/'research/data_prep/wrd_main_v10/merge_delta06.py')]:shutil.copyfile(source,DEST/'tooling'/n)
 for n,p in [('TRAINING_MANIFEST.json',DATA/'TRAINING_MANIFEST.json'),('ACTUAL_DATA_STATISTICS.json',DATA/'ACTUAL_DATA_STATISTICS.json'),('TRAINING_PLAN.md',PLAN/'TRAINING_PLAN.md'),('COVERAGE_EXPANSION.md',PLAN/'COVERAGE_EXPANSION.md'),('MAIN530_QA.json',WORK/'MAIN530_QA.json'),('CURRENT_DATA_AND_EXPOSURE.json',WORK/'CURRENT_DATA_AND_EXPOSURE.json'),('TRAINING_CANDIDATES.json',WORK/'TRAINING_CANDIDATES.json')]:
  shutil.copyfile(p,DEST/n)
 save(WORK/'BUILD_RECEIPT.json',{'status':'BUILT_NOT_YET_MERGED_RESTORED_OR_REMOTE_VERIFIED','files':len(refs)+1,'ciphertext_bytes':receipt['ciphertext_bytes'],'ciphertext_sha256':receipt['ciphertext_sha256'],'training_started':False})
 print(json.dumps({'files':len(refs)+1,'ciphertext_bytes':receipt['ciphertext_bytes'],'ciphertext_sha256':receipt['ciphertext_sha256']}))
if __name__=='__main__':main()
