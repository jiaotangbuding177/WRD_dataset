"""Cold-fetch final metadata and bind unchanged LFS to a frozen prior network proof.

This does NOT download the final commit's LFS entity again. It verifies the
first actual network body/parts and its frozen receipt, then checks final Git
blobs, exact PUBLIC_MANIFEST inventory and identical LFS path/OID/size.
"""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,os,re,subprocess
PREFIX='dataset/20261030_v10_checkpoint08'
REPOSITORY='https://github.com/jiaotangbuding177/WRD_dataset.git'
TRANSPORT='INDEPENDENT_EXACT_COMMIT_GITHUB_MEDIA_HTTP206_RANGES'
CHUNK=2*1024*1024
ROOT_PUBLIC=['README.md','TRAINING_ENTRYPOINT.json','.gitattributes']
LFS_MAGIC=b'version https://git-lfs.github.com/spec/v1\n'

def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def hash_value(x):
 assert isinstance(x,str)and re.fullmatch('[a-f0-9]{64}',x),'INVALID_SHA256'
def commit_value(x):
 assert isinstance(x,str)and re.fullmatch('[a-f0-9]{40}',x),'INVALID_COMMIT'
def unique_object(pairs):
 d={}
 for k,v in pairs:
  assert k not in d,'DUPLICATE_JSON_KEY'
  d[k]=v
 return d
def parse(b):return json.loads(b,object_pairs_hook=unique_object)
def canonical_path(name):
 assert isinstance(name,str)and name and not any(c in name for c in '\r\n\x00:\\'),'UNSAFE_PATH'
 p=PurePosixPath(name)
 assert p.parts and p.as_posix()==name and not p.is_absolute()and'..'not in p.parts,'NONCANONICAL_PATH'
 assert not any(v.endswith((' ','.'))for v in p.parts),'WINDOWS_ALIAS'
 bad={'con','prn','aux','nul',*('com'+str(i)for i in range(1,10)),*('lpt'+str(i)for i in range(1,10))}
 assert not any(v.split('.')[0].casefold()in bad for v in p.parts),'WINDOWS_DEVICE'
 return p
def safe(root,name):
 root=Path(root).resolve();p=root.joinpath(*canonical_path(name).parts)
 assert p.resolve().is_relative_to(root),'PATH_ESCAPE'
 for q in [p,*p.parents]:
  assert not q.is_symlink()and not(hasattr(q,'is_junction')and q.is_junction()),'SYMLINK_OR_JUNCTION'
  if q==root:break
 return p
def run_git(args):
 env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='never',
          GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull)
 try:
  p=subprocess.run(['git','-c','credential.helper=','-c','http.extraHeader=',*args],
                   stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=180)
 except subprocess.TimeoutExpired:
  raise RuntimeError('COLD_GIT_COMMAND_TIMEOUT phase='+str(args[0]))from None
 if p.returncode:raise RuntimeError('COLD_GIT_COMMAND_FAILED phase='+str(args[0])+' code='+str(p.returncode))from None
 return p.stdout
def git(directory,*args):return run_git(['--git-dir='+str(directory),*args])
def cold_fetch(directory,metadata_commit,data_commit):
 directory=Path(directory);assert not directory.exists(),'NEW_COLD_GIT_DIRECTORY_REQUIRED'
 directory.parent.mkdir(parents=True,exist_ok=True)
 run_git(['init','--bare',str(directory)])
 for label,commit in [('metadata',metadata_commit),('data',data_commit)]:
  git(directory,'fetch','--no-tags','--depth=1',REPOSITORY,commit)
  assert git(directory,'rev-parse','FETCH_HEAD').decode().strip()==commit,'REMOTE_FETCH_COMMIT_MISMATCH'
  assert git(directory,'cat-file','-t',commit).decode().strip()=='commit','REMOTE_OBJECT_NOT_COMMIT'
 return {'repository':REPOSITORY,'new_bare_git_directory':str(directory.resolve()),
         'metadata_commit_fetched':metadata_commit,'first_data_commit_fetched':data_commit,
         'checkout_or_smudge_executed':False,'LFS_body_downloaded':False}
def names_at(directory,commit):
 raw=git(directory,'ls-tree','-r','-z','--name-only',commit,'--',PREFIX).decode()
 assert raw.endswith('\x00');names=raw[:-1].split('\x00')
 assert names and len(names)==len(set(n.casefold()for n in names)),'EMPTY_OR_CASE_ALIAS_INVENTORY'
 for n in names:assert n.startswith(PREFIX+'/');canonical_path(n)
 assert PREFIX+'/PUBLIC_MANIFEST.json'in names
 return names
def pointer(blob):
 m=re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([a-f0-9]{64})\nsize ([0-9]+)\n',blob)
 assert m,'NONCANONICAL_LFS_POINTER'
 n=int(m.group(2));assert n>0
 return {'sha256':m.group(1).decode(),'bytes':n,'pointer_blob_SHA256':hashlib.sha256(blob).hexdigest()}
def public_inventory(pm,names):
 assert isinstance(pm,dict)and isinstance(pm.get('files'),list)and pm['files'],'NONEMPTY_PUBLIC_FILES_REQUIRED'
 refs={};folds=set()
 for r in pm['files']:
  assert isinstance(r,dict);canonical_path(r['path']);k=r['path'].casefold()
  assert k not in folds,'DUPLICATE_OR_CASE_ALIAS_PUBLIC_PATH';folds.add(k)
  assert type(r['bytes'])is int and r['bytes']>=0;hash_value(r['sha256'])
  refs[PREFIX+'/'+r['path']]=r
 assert set(refs)==set(names)-{PREFIX+'/PUBLIC_MANIFEST.json'},'PUBLIC_MANIFEST_INVENTORY_NOT_EXACT'
 return refs
def verify_first_network(receipt_path,receipt_sha,body_path,body_sha,data_commit):
 hash_value(receipt_sha);hash_value(body_sha);commit_value(data_commit)
 assert digest(receipt_path)==receipt_sha,'FIRST_RECEIPT_FROZEN_SHA_MISMATCH'
 receipt=parse(Path(receipt_path).read_bytes())
 assert receipt['status']=='PASS_REMOTE_ORDINARY_BLOBS_AND_ACTUAL_LFS_ENTITY'
 assert receipt['commit']==data_commit,'FIRST_DATA_COMMIT_MISMATCH'
 assert receipt['transport']==TRANSPORT,'FIRST_RECEIPT_NOT_FRESH_NETWORK_TRANSPORT'
 assert receipt['local_payload_never_used_as_download']is True
 assert receipt['fresh_network_body_required_every_run']is True
 assert receipt['PUBLIC_MANIFEST_exact_inventory_coverage']is True
 body=Path(body_path).resolve()
 assert body==Path(receipt['downloaded_file']).resolve(),'BODY_MUST_BE_ORIGINAL_RECEIPT_DOWNLOAD_PATH'
 assert body.name=='INDEPENDENT_REMOTE_LFS_BODY.bin','ORIGINAL_NETWORK_BODY_FILENAME_REQUIRED'
 assert body.is_file()and not body.is_symlink()
 entity=receipt['LFS_actual_entity'];canonical_path(entity['path']);hash_value(entity['sha256'])
 assert entity['path'].startswith(PREFIX+'/controlled/')and entity['path'].endswith('.aesgcm')
 assert type(entity['bytes'])is int and entity['bytes']>0
 assert body.stat().st_size==entity['bytes']and digest(body)==body_sha==entity['sha256'],'FIRST_BODY_SHA_OR_SIZE_MISMATCH'
 parts=receipt['parts'];assert isinstance(parts,list)and parts,'FIRST_NETWORK_PARTS_REQUIRED'
 assert all(isinstance(p,dict)and type(p['index'])is int for p in parts)
 ordered=sorted(parts,key=lambda x:x['index']);expected_count=(entity['bytes']+CHUNK-1)//CHUNK
 assert len(ordered)==expected_count,'FIRST_PART_COUNT_MISMATCH'
 verified=[];position=0
 with body.open('rb')as f:
  for index,p in enumerate(ordered):
   assert p['index']==index,'FIRST_PART_DUPLICATE_OR_GAP'
   n=min(CHUNK,entity['bytes']-position)
   assert all(type(p[k])is int for k in ['start','end','bytes','attempts'])
   assert p['start']==position and p['end']==position+n-1 and p['bytes']==n,'FIRST_PART_NOT_CONTIGUOUS_2MIB_COVER'
   assert 1<=p['attempts']<=4;hash_value(p['sha256'])
   chunk=f.read(n);assert len(chunk)==n and hashlib.sha256(chunk).hexdigest()==p['sha256'],'FIRST_BODY_RANGE_SHA_MISMATCH'
   actual_part=safe(body.parent,f'part_{index:04d}.bin')
   assert actual_part.is_file()and actual_part.stat().st_size==n and digest(actual_part)==p['sha256'],'FIRST_ACTUAL_NETWORK_PART_MISSING_OR_WRONG'
   verified.append({'index':index,'start':position,'end':position+n-1,'bytes':n,'sha256':p['sha256']})
   position+=n
  assert f.read(1)==b''and position==entity['bytes'],'FIRST_PART_COVER_INCOMPLETE'
 return receipt,{'receipt_sha256':receipt_sha,'data_commit':data_commit,'original_downloaded_body':str(body),
    'actual_body_sha256':body_sha,'actual_body_bytes':entity['bytes'],'transport':TRANSPORT,
    'contiguous_2MiB_parts':verified,'verified_part_count':len(verified),'actual_first_part_files_checked':True}
def verify(a):
 commit_value(a.metadata_commit);commit_value(a.first_data_commit)
 assert a.metadata_commit!=a.first_data_commit,'FOLLOWUP_MUST_BE_NEW_METADATA_COMMIT'
 assert not a.output.exists(),'NEW_RECEIPT_PATH_REQUIRED'
 first,first_proof=verify_first_network(a.first_receipt,a.first_receipt_sha256,a.first_body,a.first_body_sha256,a.first_data_commit)
 fetch=cold_fetch(a.cold_git_dir,a.metadata_commit,a.first_data_commit)
 data_names=names_at(a.cold_git_dir,a.first_data_commit)
 first_entity=first['LFS_actual_entity'];lfs_name=first_entity['path']
 assert [n for n in data_names if n.endswith('.aesgcm')]==[lfs_name],'FIRST_DATA_LFS_INVENTORY_MISMATCH'
 data_pointer=pointer(git(a.cold_git_dir,'show',a.first_data_commit+':'+lfs_name))
 assert all(data_pointer[k]==first_entity[k]for k in ['sha256','bytes','pointer_blob_SHA256']),'FIRST_REMOTE_POINTER_DISAGREES_WITH_FROZEN_NETWORK_RECEIPT'
 old_records=first['ordinary_files'];assert isinstance(old_records,list)and len(old_records)==first['ordinary_files_verified']
 assert len({r['path']for r in old_records})==len(old_records),'FIRST_ORDINARY_RECORD_DUPLICATE'
 assert {r['path']for r in old_records}==(set(data_names)-{lfs_name})|set(ROOT_PUBLIC),'FIRST_ORDINARY_INVENTORY_MISMATCH'
 for r in old_records:
  canonical_path(r['path']);blob=git(a.cold_git_dir,'show',a.first_data_commit+':'+r['path'])
  assert len(blob)==r['bytes']and hashlib.sha256(blob).hexdigest()==r['sha256'],'FIRST_FROZEN_ORDINARY_BLOB_MISMATCH'
 names=names_at(a.cold_git_dir,a.metadata_commit)
 assert [n for n in names if n.endswith('.aesgcm')]==[lfs_name],'FINAL_LFS_PATH_OR_COUNT_CHANGED'
 final_pointer=pointer(git(a.cold_git_dir,'show',a.metadata_commit+':'+lfs_name))
 assert final_pointer['sha256']==first_entity['sha256']and final_pointer['bytes']==first_entity['bytes'],'FINAL_LFS_OID_OR_SIZE_CHANGED'
 pm_blob=git(a.cold_git_dir,'show',a.metadata_commit+':'+PREFIX+'/PUBLIC_MANIFEST.json')
 declared=public_inventory(parse(pm_blob),names)
 records=[]
 for name in names+ROOT_PUBLIC:
  blob=git(a.cold_git_dir,'show',a.metadata_commit+':'+name)
  if name==lfs_name:continue
  assert not blob.startswith(LFS_MAGIC),'UNEXPECTED_ORDINARY_LFS_POINTER'
  local=safe(a.release_root,name);assert local.is_file()and local.read_bytes()==blob,'FINAL_LOCAL_PUBLIC_BLOB_MISMATCH'
  records.append({'path':name,'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()})
 for name,r in declared.items():
  if name==lfs_name:assert r['bytes']==final_pointer['bytes']and r['sha256']==final_pointer['sha256']
  else:
   blob=git(a.cold_git_dir,'show',a.metadata_commit+':'+name)
   assert len(blob)==r['bytes']and hashlib.sha256(blob).hexdigest()==r['sha256'],'FINAL_PUBLIC_MANIFEST_BLOB_PIN_MISMATCH'
 return {'status':'PASS_METADATA_COLD_FETCH_AND_SAME_FROZEN_NETWORK_LFS_OBJECT',
   'verification_kind':'NEW_ORDINARY_BLOBS_PLUS_SAME_PREVIOUSLY_NETWORK_VERIFIED_LFS_OID_NOT_A_NEW_LFS_DOWNLOAD',
   'metadata_commit':a.metadata_commit,'first_network_data_commit':a.first_data_commit,
   'cold_fetch':fetch,'ordinary_files':records,'ordinary_files_verified':len(records),
   'PUBLIC_MANIFEST_exact_inventory_coverage':True,'PUBLIC_MANIFEST_sha256':hashlib.sha256(pm_blob).hexdigest(),
   'first_network_proof':first_proof,'first_remote_data_pointer':data_pointer,'final_metadata_pointer':final_pointer,
   'LFS_path':lfs_name,'same_previously_network_verified_OID_and_size':True,
   'final_commit_LFS_redownload_performed':False,'local_cipher_used_as_new_network_download':False,
   'weights_loaded':False,'training_started':False}
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['metadata-commit','first-data-commit','first-receipt-sha256','first-body-sha256']:p.add_argument('--'+n,required=True)
 for n in ['first-receipt','first-body','cold-git-dir','release-root','output']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();result=verify(a);a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({'status':result['status'],'metadata_commit':a.metadata_commit,
   'ordinary_files':result['ordinary_files_verified'],'same_LFS_OID':result['final_metadata_pointer']['sha256'],
   'LFS_redownload_performed':False}))
if __name__=='__main__':main()
