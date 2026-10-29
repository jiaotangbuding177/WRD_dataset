"""Authenticate delta06 and merge with verified checkpoint05 into a NEW root.

Only manifest-listed ordinary files are copied. No saved source is executed.
"""
from pathlib import Path,PurePosixPath
import argparse,hashlib,importlib.util,json,shutil
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def safe(root,name):
 q=PurePosixPath(name);assert not q.is_absolute()and'..'not in q.parts and'\\'not in name
 p=Path(root).joinpath(*q.parts);assert p.resolve().is_relative_to(Path(root).resolve());return p
def main(a):
 base=a.base.resolve();out=a.out.resolve();delta=a.delta_out.resolve()
 assert not out.exists()and not delta.exists()and base.is_dir()
 spec=importlib.util.spec_from_file_location('restore06',Path(__file__).with_name('restore_checkpoint.py'))
 restore=importlib.util.module_from_spec(spec);spec.loader.exec_module(restore)
 result=restore.restore(a.cipher,a.receipt,a.key,delta)
 dm=load(delta/'PAYLOAD_MANIFEST.json');base_manifest=base/'PAYLOAD_MANIFEST.json'
 assert sha(base_manifest)==dm['base05_payload_manifest_sha256']
 assert sha(base/'TRAINING_MANIFEST.json')==dm['base05_training_manifest_sha256']
 bm=load(base_manifest);out.mkdir(parents=True,exist_ok=False);combined={};replaced=[]
 def copy(ref,origin):
  p=safe(origin,ref['path']);assert p.is_file()and p.stat().st_size==ref['bytes']and sha(p)==ref['sha256']
  dst=safe(out,ref['path']);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
  assert sha(dst)==ref['sha256'];combined[ref['path']]={k:ref[k]for k in ['path','bytes','sha256']}
 for ref in bm['files']:copy(ref,base)
 for ref in dm['files']:
  if ref['path']in combined and combined[ref['path']]['sha256']!=ref['sha256']:
   old=combined[ref['path']];prior=safe(out,'history/pre_delta06/'+old['sha256'][:12]+'/'+ref['path']);prior.parent.mkdir(parents=True,exist_ok=True)
   shutil.copyfile(safe(out,ref['path']),prior);n=prior.relative_to(out).as_posix();combined[n]={'path':n,'bytes':old['bytes'],'sha256':old['sha256']};replaced.append(ref['path'])
  copy(ref,delta)
 for name,p in [('base05',base_manifest),('delta06',delta/'PAYLOAD_MANIFEST.json')]:
  target=safe(out,'merge_evidence/'+name+'_authenticated_manifest.json');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
  n=target.relative_to(out).as_posix();combined[n]={'path':n,'bytes':target.stat().st_size,'sha256':sha(target)}
 merged={'schema':'wrd-authenticated-base05-plus-delta06-file-union','files':list(combined.values()),
         'base_authenticated_manifest_sha256':sha(base_manifest),'delta_authenticated_manifest_sha256':sha(delta/'PAYLOAD_MANIFEST.json'),
         'current_training_manifest_sha256':sha(out/'TRAINING_MANIFEST.json'),'no_saved_source_executed':True,'training_started':False}
 (out/'PAYLOAD_MANIFEST.json').write_text(json.dumps(merged,indent=2)+'\n',encoding='utf-8')
 proof={'status':'PASS_AUTHENTICATED_BASE05_AND_DELTA06_MERGED_EXPLICIT_FILES_NEW_ROOT','base_files':len(bm['files']),
        'delta_files':len(dm['files']),'merged_files':len(combined),'replaced_old_bytes_preserved':replaced,
        'delta_authenticated_members':result['authenticated_files'],'training_started':False,'requires_independent_loader_QA':True}
 (out/'MERGE_RESULT.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8');print(json.dumps(proof))
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['base','cipher','receipt','key','out','delta-out']:p.add_argument('--'+n,type=Path,required=True)
 main(p.parse_args())
