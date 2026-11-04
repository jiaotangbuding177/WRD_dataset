"""Copy the exact staged main/refs into a separate root for independent QA."""
from pathlib import Path,PurePosixPath
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[3];DATA=ROOT/'output/20261027_wrd_main_v10'
OUT=ROOT/'output/20261031_wrd_curation10/full_stage_root01'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def main():
 assert not OUT.exists()
 staged=DATA/'manifest_staging10/TRAINING_MANIFEST10.json';m=load(staged)
 assert m['actual_counts']['targets']==623
 assert sha(DATA/'TRAINING_MANIFEST.json')=='01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42'
 OUT.mkdir(parents=True);copied={}
 def copy(name,expected=None):
  pp=PurePosixPath(name);assert not pp.is_absolute()and '..'not in pp.parts and '\\'not in name
  src=DATA/name;dest=OUT/name
  if expected:assert sha(src)==expected
  if name not in copied:
   dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest);assert sha(src)==sha(dest)
   copied[name]=sha(dest)
 for key in ['actual_train_files','active_compilation_reports','external_root_admission_receipts']:
  for ref in m[key]:copy(ref['path'],ref['sha256'])
 for ref in m['active_compilation_reports']:copy(str(PurePosixPath(ref['path']).parent/'CAUSAL_TEMPLATE.json'))
 copy('clean_inputs/source_scope.metadata.jsonl.gz')
 shutil.copytree(DATA/'canonical_arrays10',OUT/'canonical_arrays10')
 shutil.copyfile(staged,OUT/'TRAINING_MANIFEST.json')
 shutil.copyfile(DATA/'manifest_staging10/ACTUAL_DATA_STATISTICS10.json',OUT/'ACTUAL_DATA_STATISTICS.json')
 result={'status':'EXACT_STAGED_REFERENCE_ROOT_COPIED_NOT_ACTIVATED','root':str(OUT),'manifest_sha256':sha(OUT/'TRAINING_MANIFEST.json'),
  'reference_files':len(copied),'binary_files':m['actual_counts']['targets']*3,'data_hub_manifest_unchanged':True,'training_started':False}
 report=OUT.parent/'STAGED_ROOT_COPY_QA.json';report.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode());print(json.dumps(result))
if __name__=='__main__':main()
