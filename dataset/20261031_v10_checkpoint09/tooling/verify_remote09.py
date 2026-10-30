"""Verify exact Git objects and independently download the real remote LFS body.

Every run requires a fresh network body. No redirects, signed URLs, credentials
or exception bodies are printed. PUBLIC_MANIFEST covers all checkpoint files
except itself. No saved payload source is executed.
"""
from pathlib import Path,PurePosixPath
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse,hashlib,json,re,subprocess,time,urllib.request
PREFIX='dataset/20261031_v10_checkpoint09'

def is_lfs_pointer(blob):
 return blob.splitlines()[:1]==[b'version https://git-lfs.github.com/spec/v1']

def parse_pointer(blob):
 m=re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([a-f0-9]{64})\nsize ([0-9]+)\n',blob)
 assert m,'NONCANONICAL_LFS_POINTER'
 size=int(m.group(2));assert size>0,'EMPTY_LFS_BODY'
 return m.group(1).decode(),size

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  raise RuntimeError('UNEXPECTED_REMOTE_REDIRECT')

def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def git(directory,*args):return subprocess.check_output(['git','--git-dir='+str(directory),*args])
def canonical_path(name):
 assert isinstance(name,str)and name and not any(c in name for c in '\r\n\x00:\\'),'UNSAFE_PUBLIC_PATH'
 p=PurePosixPath(name)
 assert p.parts and p.as_posix()==name and not p.is_absolute()and'..'not in p.parts,'NONCANONICAL_PUBLIC_PATH'
 assert not any(v.endswith((' ','.'))for v in p.parts),'WINDOWS_PUBLIC_PATH_ALIAS'
 reserved={'con','prn','aux','nul',*('com'+str(n)for n in range(1,10)),*('lpt'+str(n)for n in range(1,10))}
 assert not any(v.split('.')[0].casefold()in reserved for v in p.parts),'WINDOWS_RESERVED_PUBLIC_PATH'
 return p
def unique_object(pairs):
 result={}
 for k,v in pairs:
  assert k not in result,'DUPLICATE_JSON_OBJECT_KEY'
  result[k]=v
 return result
def public_manifest(pm,names):
 assert isinstance(pm,dict)and isinstance(pm.get('files'),list)and pm['files'],'PUBLIC_FILES_MUST_BE_NONEMPTY_LIST'
 declared={};seen=set()
 for ref in pm['files']:
  assert isinstance(ref,dict),'INVALID_PUBLIC_FILE_REFERENCE'
  n=ref['path'];canonical_path(n);fold=n.casefold()
  assert fold not in seen,'DUPLICATE_OR_CASE_ALIAS_PUBLIC_FILE';seen.add(fold)
  assert type(ref['bytes'])is int and ref['bytes']>=0,'INVALID_PUBLIC_SIZE'
  assert isinstance(ref['sha256'],str)and re.fullmatch('[a-f0-9]{64}',ref['sha256']),'INVALID_PUBLIC_SHA256'
  declared[PREFIX+'/'+n]=ref
 expected=set(names)-{PREFIX+'/PUBLIC_MANIFEST.json'}
 assert set(declared)==expected,'PUBLIC_MANIFEST_MUST_EXACTLY_COVER_CHECKPOINT_EXCEPT_ITSELF'
 return declared
def safe(root,name):
 p=canonical_path(name);root=root.resolve();q=root.joinpath(*p.parts);assert q.resolve().is_relative_to(root)
 for ancestor in [q,*q.parents]:
  assert not ancestor.is_symlink()and not(hasattr(ancestor,'is_junction')and ancestor.is_junction()),'SYMLINK_OR_JUNCTION_PUBLIC_FILE'
  if ancestor==root:break
 return q
def save(p,j):p.write_bytes((json.dumps(j,ensure_ascii=False,indent=2)+'\n').encode())

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--commit',required=True);ap.add_argument('--git-dir',type=Path,required=True)
 ap.add_argument('--release-root',type=Path,required=True);ap.add_argument('--download-dir',type=Path,required=True)
 ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 assert re.fullmatch('[a-f0-9]{40}',a.commit)
 assert git(a.git_dir,'rev-parse',a.commit).decode().strip()==a.commit
 names=git(a.git_dir,'ls-tree','-r','-z','--name-only',a.commit,'--',PREFIX).decode().split('\x00')
 assert names[-1]=='';names=names[:-1]
 assert names and len(names)==len(set(n.casefold()for n in names)),'EMPTY_OR_CASE_ALIASED_CHECKPOINT_INVENTORY'
 for name in names:
  assert name.startswith(PREFIX+'/');canonical_path(name)
 assert PREFIX+'/PUBLIC_MANIFEST.json'in names,'PUBLIC_MANIFEST_MISSING'
 pm=json.loads(git(a.git_dir,'show',a.commit+':'+PREFIX+'/PUBLIC_MANIFEST.json'),object_pairs_hook=unique_object)
 declared=public_manifest(pm,names)
 assert not a.output.exists(),'PRESERVE_PREVIOUS_REMOTE_VERIFICATION_RECEIPT'
 assert not a.download_dir.exists()or(a.download_dir.is_dir()and not any(a.download_dir.iterdir())),'FRESH_OR_EMPTY_DOWNLOAD_DIRECTORY_REQUIRED'
 records=[];lfs=None
 for name in names+['README.md','TRAINING_ENTRYPOINT.json','.gitattributes']:
  blob=git(a.git_dir,'show',a.commit+':'+name);local=safe(a.release_root,name)
  if name.endswith('.aesgcm'):
   assert name.startswith(PREFIX+'/controlled/'),'LFS_MUST_BE_CONTROLLED_CIPHERTEXT'
   oid,size=parse_pointer(blob)
   assert size>0 and local.stat().st_size==size and digest(local)==oid
   assert lfs is None;lfs={'path':name,'sha256':oid,'bytes':size,'pointer_blob_SHA256':hashlib.sha256(blob).hexdigest()}
  else:
   assert not is_lfs_pointer(blob),'UNEXPECTED_ORDINARY_LFS_POINTER'
   assert local.read_bytes()==blob,name
   records.append({'path':name,'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()})
 assert lfs
 for path,r in declared.items():
  blob=git(a.git_dir,'show',a.commit+':'+path)
  if path.endswith('.aesgcm'):assert r['bytes']==lfs['bytes']and r['sha256']==lfs['sha256']
  else:assert len(blob)==r['bytes']and hashlib.sha256(blob).hexdigest()==r['sha256']
 a.download_dir.mkdir(parents=True,exist_ok=True);assembled=a.download_dir/'INDEPENDENT_REMOTE_LFS_BODY.bin'
 assert not assembled.exists(),'PRESERVE_PREVIOUS_DOWNLOAD'
 url='https://media.githubusercontent.com/media/jiaotangbuding177/WRD_dataset/'+a.commit+'/'+lfs['path']
 chunk=2*1024*1024;parts=[];tasks=[(i,start,min(start+chunk,lfs['bytes'])-1)for i,start in enumerate(range(0,lfs['bytes'],chunk))]
 assert tasks,'EMPTY_LFS_ENTITY_NOT_ALLOWED'
 def get(t):
  i,start,end=t;part=a.download_dir/f'part_{i:04d}.bin';n=end-start+1
  for attempt in range(4):
   try:
    req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}','User-Agent':'WRD-checkpoint09-independent-byte-verifier','Accept-Encoding':'identity'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(req,timeout=35)as response:
     assert response.status==206,'RANGE_NOT_206'
     assert response.geturl()==url,'REMOTE_RESPONSE_URL_CHANGED'
     assert response.headers.get('Content-Encoding','identity').lower()in {'','identity'},'UNEXPECTED_CONTENT_ENCODING'
     assert response.headers.get('Content-Range')==f'bytes {start}-{end}/{lfs["bytes"]}','CONTENT_RANGE_MISMATCH'
     b=response.read(n+1);assert len(b)==n,'INCOMPLETE_RANGE_BODY'
    part.write_bytes(b)
    return {'index':i,'start':start,'end':end,'bytes':n,'sha256':hashlib.sha256(b).hexdigest(),'attempts':attempt+1,
            'http_status':206,'content_range':f'bytes {start}-{end}/{lfs["bytes"]}',
            'response_url_sha256':hashlib.sha256(url.encode()).hexdigest()}
   except Exception as e:
    if attempt==3:raise RuntimeError('REMOTE_RANGE_FAILED index='+str(i)+' type='+type(e).__name__)from None
    time.sleep(1+attempt)
 with ThreadPoolExecutor(max_workers=4)as pool:
  pending=[pool.submit(get,t)for t in tasks]
  for f in as_completed(pending):
   parts.append(f.result())
   if len(parts)%10==0 or len(parts)==len(tasks):print(json.dumps({'remote_chunks':len(parts),'chunks_total':len(tasks),'verified_bytes':sum(x['bytes']for x in parts)}),flush=True)
 with assembled.open('xb')as out:
  for r in sorted(parts,key=lambda x:x['index']):
   p=a.download_dir/f'part_{r["index"]:04d}.bin';assert p.stat().st_size==r['bytes']and digest(p)==r['sha256'];out.write(p.read_bytes())
 assert assembled.stat().st_size==lfs['bytes']and digest(assembled)==lfs['sha256']
 receipt={'status':'PASS_REMOTE_ORDINARY_BLOBS_AND_ACTUAL_LFS_ENTITY','commit':a.commit,'ordinary_files':records,
  'ordinary_files_verified':len(records),'checkpoint_files_including_LFS':len(names),'LFS_actual_entity':lfs,
  'downloaded_file':str(assembled.resolve()),'transport':'INDEPENDENT_EXACT_COMMIT_GITHUB_MEDIA_HTTP206_RANGES',
  'parts':parts,'local_payload_never_used_as_download':True,'PUBLIC_MANIFEST_exact_inventory_coverage':True,
  'fresh_network_body_required_every_run':True,
  'ordinary_blob_proof':'IMMUTABLE_OBJECTS_FROM_SUPPLIED_GIT_DIR; record external fresh remote fetch provenance separately',
  'weights_loaded':False,'training_started':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);save(a.output,receipt)
 print(json.dumps({'status':receipt['status'],'commit':a.commit,'ordinary_files':len(records),'LFS_bytes':lfs['bytes'],'LFS_SHA256':lfs['sha256']}))

if __name__=='__main__':main()
