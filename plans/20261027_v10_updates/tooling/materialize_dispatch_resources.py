"""Materialize only hash-verified reused input resources; execute no jobs."""
import argparse,hashlib,json,shutil
from pathlib import Path,PurePosixPath
def digest(path):
 h=hashlib.sha256()
 with path.open('rb')as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def target(root,name):
 p=PurePosixPath(name)
 if p.is_absolute()or'..'in p.parts or chr(92)in name:raise ValueError('unsafe_relative_path')
 result=root.joinpath(*p.parts)
 if not result.resolve().is_relative_to(root.resolve()):raise ValueError('path_escape')
 return result
def materialize(root):
 root=Path(root);mapping=json.loads((root/'MATERIAL_REUSE_MAP.json').read_text(encoding='utf-8'));count=0
 for row in mapping['objects']:
  source=root/'existing_source_objects'/row['sha256']
  if not source.is_file()or source.stat().st_size!=row['bytes']or digest(source)!=row['sha256']:raise ValueError('reuse_object_identity_mismatch')
  out=target(root,row['restored_relative_path']);out.parent.mkdir(parents=True,exist_ok=True)
  if out.exists():
   if digest(out)!=row['sha256']:raise ValueError('existing_target_differs')
  else:
   with source.open('rb')as f,out.open('xb')as g:shutil.copyfileobj(f,g,1048576)
  count+=1
 base=root/'dispatch_release_02';manifest=json.loads((base/'MANIFEST.json').read_text(encoding='utf-8'));verified=0
 for row in manifest['files']:
  p=target(base,row['path'])
  if p.stat().st_size!=row['bytes']or digest(p)!=row['sha256']:raise ValueError('frozen_dispatch_member_mismatch')
  verified+=1
 aliases=json.loads((root/'EVIDENCE_PATH_ALIASES.json').read_text(encoding='utf-8'))
 portable={old:str(target(root,new).resolve())for old,new in aliases['original_absolute_path_to_archive_path'].items()}
 (root/'RESTORED_RESOURCE_PATHS.json').write_text(json.dumps({'original_host_path_to_restored_path':portable,'frozen_job_bytes_not_rewritten':True,'saved_jobs_not_executed':True,'native_dispatch_requires_a_future_explicit_preparation_and_authorization':True},ensure_ascii=False,indent=2)+chr(10),encoding='utf-8')
 return {'status':'PASS','reused_material_objects_materialized':count,'all_frozen_manifest_files_verified':verified,'saved_jobs_executed':0,'new_training_positive_labels':0,'training_started':False}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);args=p.parse_args();print(json.dumps(materialize(args.root)))
if __name__=='__main__':main()
