"""Freeze explicit new synthetic artifacts, scan, and package real data bytes."""
from pathlib import Path
from collections import Counter
import gzip,hashlib,importlib.util,json,sys,tarfile
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation11';DEL=ROOT/'output/20261031_wrd_curation11_delivery'
DEST=ROOT/'output/20261025_wrd_training_dataset/git_release/dataset/20261031_v10_curriculum11'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def original_guard(path,declared_root):
 original=Path(path).absolute();scope=Path(declared_root).absolute()
 assert original.is_relative_to(scope),'ORIGINAL_PATH_OUTSIDE_DECLARED_SOURCE_TREE'
 for a in [original,*original.parents]:
  info=a.lstat()
  assert not a.is_symlink() and not (getattr(info,'st_file_attributes',0)&0x400),'SOURCE_REPARSE_POINT'
  assert not (hasattr(a,'is_junction') and a.is_junction()),'SOURCE_JUNCTION'
 resolved=original.resolve();resolved_scope=scope.resolve()
 assert resolved_scope.is_relative_to(ROOT.resolve()) and resolved.is_relative_to(resolved_scope),'RESOLVED_SOURCE_ESCAPES_DECLARED_ROOT'
 return resolved
def main():
 assert not DEST.exists(),'NEW_PUBLIC_CHECKPOINT_REQUIRED'
 qa=WORK/'ROOT_ACCEPTANCE11.json';assert load(qa)['status']=='ROOT_ACCEPTED_FINITE_CURRICULUM_DATA_NOT_FULL_AUTONOMOUS_READY'
 guard=mod('guard05_public11',ROOT/'research/data_prep/wrd_main_v10/package_checkpoint05.py')
 pkg=mod('scan10_public11',ROOT/'research/data_prep/wrd_curation10/package10.py')
 validator=mod('strict_restore11',Path(__file__).with_name('restore_package11.py'))
 entries={};folded=set();aliases=[];scans=Counter();needles=guard.credential_needles()
 def add(name,p,kind,declared_root=None):
  original=Path(p).absolute();scope=Path(declared_root).absolute() if declared_root is not None else original.parent
  p=original_guard(original,scope);validator.safe(DEL/'nominal_archive_validation_root',name)
  assert name not in entries and name.casefold() not in folded and name.casefold() not in {'payload_manifest11.json','restore_receipt11.json'},'DUPLICATE_CASE_ALIAS_OR_RESERVED_ARCHIVE_NAME'
  assert p.is_file() and not p.is_symlink()
  assert not any(s in p.parts for s in ['.git','__pycache__','local_delivery_key','private'])
  assert p.suffix.casefold() not in {'.pyc','.key','.env','.pem','.p12','.pfx'}
  for a in [p,*p.parents]:assert not a.is_symlink() and not (hasattr(a,'is_junction') and a.is_junction())
  first_size=p.stat().st_size;first_sha=sha(p)
  scan=pkg.scan_file(p,needles);scans.update(scan)
  assert original_guard(original,scope)==p and p.stat().st_size==first_size and sha(p)==first_sha,'SOURCE_CHANGED_BETWEEN_SCAN_AND_PIN'
  r={'path':name,'source':str(p),'bytes':first_size,'sha256':first_sha,'category':kind};entries[name]=r;folded.add(name.casefold())
  aliases.append({'original_absolute_path':str(p),'archive_path':name,'sha256':r['sha256']})
 def tree(prefix,p,kind):
  original_guard(p,p)
  for f in sorted(p.rglob('*')):
   if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc':add(prefix+'/'+f.relative_to(p).as_posix(),f,kind,declared_root=p)
 # New synthetic records, all intermediate failures, full evidence and real
 # arrays are preserved. Default reading is still manifest-only, never glob.
 tree('work',WORK,'AUTHORED_DATA_OR_AUDIT')
 tree('source/wrd_curation11',ROOT/'research/data_prep/wrd_curation11','TOOLING')
 tree('plans',ROOT/'research/plans/20261031_wrd_curation11','DESIGN')
 for n in ['A_B_MODULES.md','PIPELINE.md']:add('designs/'+n,ROOT/'research/designs'/n,'DESIGN')
 tree('designs/history52',ROOT/'research/designs/history/5.0.52/curation11_20261031','DESIGN')
 tree('designs/history53',ROOT/'research/designs/history/5.0.53/curation11_before_budget_profile','DESIGN')
 tree('designs/history54',ROOT/'research/designs/history/5.0.54/curation11_before_final_summary','DESIGN')
 add('MEMORY11_PRE_DELIVERY.md',ROOT/'research/memory/2026-10-31_wrd_curation11.md','DESIGN')
 assets=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'
 for name in ['primary_14b','control_8b']:
  for p in sorted((assets/name).iterdir()):
   if p.is_file() and p.suffix in {'.json','.jinja','.txt'}:add('tokenizer_assets/'+name+'/'+p.name,p,'TOKENIZER_ONLY_NO_WEIGHTS')
 alias=DEL/'EVIDENCE_PATHS11.json';save(alias,{'schema':'wrd11-original-local-path-to-archive-map','aliases':aliases,'audit_is_not_default_training':True});add('EVIDENCE_PATHS11.json',alias,'QA')
 refs=[{k:r[k] for k in ['path','bytes','sha256','category']} for r in entries.values()]
 pm={'schema':'wrd11-public-curriculum-and-audit-v1','design_revision':'5.0.54','files':refs,'root_acceptance_sha256':sha(qa),
  'unique_new_training_targets':627,'same_targets_two_profiles_not_additive':True,'original_main_target_count':623,
  'requires_existing_checkpoint10_for_original_pool':True,'new_data_contains_no_enterprise_source_text':True,
  'full_autonomous_training_ready':False,'training_started':False}
 DEL.mkdir(parents=True,exist_ok=True);pmanifest=DEL/'PAYLOAD_MANIFEST11.json';save(pmanifest,pm)
 save(DEL/'EXPLICIT_FILE_FREEZE11.json',{'files':list(entries.values()),'payload_manifest_sha256':sha(pmanifest),'scan':dict(scans),'script_sha256':sha(__file__)})
 DEST.mkdir(parents=True,exist_ok=False);(DEST/'data').mkdir();archive=DEST/'data/wrd-curriculum11.tar.gz'
 with archive.open('xb') as out:
  with gzip.GzipFile(fileobj=out,mode='wb',filename='',mtime=0) as compressed:
   with tarfile.open(fileobj=compressed,mode='w|') as tf:
    for name,p in [('PAYLOAD_MANIFEST11.json',pmanifest)]+[(r['path'],Path(r['source'])) for r in entries.values()]:
     if name!='PAYLOAD_MANIFEST11.json':assert sha(p)==entries[name]['sha256']
     info=tarfile.TarInfo(name);info.size=p.stat().st_size;info.mode=0o644;info.mtime=0
     with p.open('rb') as f:tf.addfile(info,f)
     if name!='PAYLOAD_MANIFEST11.json':assert sha(p)==entries[name]['sha256'],'SOURCE_CHANGED_DURING_ARCHIVE'
 receipt={'status':'REAL_PUBLIC_SYNTHETIC_ARCHIVE_BUILT_PENDING_REAL_RESTORE_QA_AND_GIT','archive_path':'data/wrd-curriculum11.tar.gz',
  'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'payload_manifest_sha256':sha(pmanifest),
  'files':len(refs),'tar_members':len(refs)+1,'source_bytes':sum(r['bytes'] for r in refs),'credential_scan':'PASS_KNOWN_AND_GENERIC_RAW_GZIP_NO_EXCEPTIONS',
  'scan':dict(scans),'key_needed_for_new_synthetic_archive':False,'training_started':False,'remote_upload_performed':False}
 save(DEST/'ARCHIVE_RECEIPT11.json',receipt);save(DEL/'BUILD_RECEIPT11.json',receipt)
 print(json.dumps(receipt))
if __name__=='__main__':main()
