"""Freeze this offline audit corpus. Does not invoke models or alter ACTIVE."""
from pathlib import Path
import hashlib,json,shutil

root=Path(__file__).resolve().parent
source=Path('D:/skillloop/research/data_prep/wrd_gap08/corpus_coverage.py')
shutil.copyfile(source,root/'source_history/corpus_coverage.final.py')
def pin(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return {'path':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':h.hexdigest()}
files=[pin(p) for p in sorted(root.rglob('*')) if p.is_file() and p.name!='MANIFEST.json' and '__pycache__' not in p.parts]
manifest={'schema':'wrd-gap08-corpus-frozen-evidence-manifest-v1','files':files,'file_count':len(files),
 'bytes':sum(p['bytes'] for p in files),'new_positive_loss_admissions':0,'training_started':False,
 'baseline01_immutable':'BASELINE01_FROZEN_FILES.json','later_corrections_are_explicit_sidecars':True,
 'raw_carriers_restored_and_readback_checked':True,'not_all_global_disk_records_or_all_semantic_reviews_claimed_complete':True}
(root/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in manifest.items() if k!='files'},ensure_ascii=False))
