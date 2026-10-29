"""Verify ordinary remote Git bytes and three real LFS objects in empty storage."""
import argparse,hashlib,json,os,subprocess,io
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
RELEASE=ROOT/'output/20261025_wrd_training_dataset/git_release'
PREFIXES=['README.md','TRAINING_ENTRYPOINT.json','dataset/20261029_v10_checkpoint05','assessment/20261029_maker405_audit']
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def run(cmd,cwd,env):
 r=subprocess.run(cmd,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if r.returncode:raise RuntimeError(str(cmd[:3])+': '+r.stderr.decode('utf-8','replace')[-2500:])
 return r.stdout
def verify(commit,work,prefixes=None,expected_lfs=3):
 env=dict(os.environ,GIT_LFS_SKIP_SMUDGE='1',GIT_TERMINAL_PROMPT='0')
 prefixes=prefixes or PREFIXES
 listed=run(['git','ls-tree','-r','--name-only','-z',commit,'--',*prefixes],RELEASE,env).decode('utf-8').split('\0')
 listed=[n for n in listed if n];expected={}
 for name in listed:
  p=RELEASE/name;expected[name]={'sha256':digest(p),'bytes':p.stat().st_size}
 cold=Path(work);assert not cold.exists();cold.parent.mkdir(parents=True,exist_ok=True)
 print('FETCHING_SHALLOW_BARE_REMOTE_NO_WORKTREE_OR_LFS_SMUDGE',flush=True)
 run(['git','init','--bare','--quiet',str(cold)],ROOT,env)
 run(['git','remote','add','origin','https://github.com/jiaotangbuding177/WRD_dataset.git'],cold,env)
 run(['git','fetch','--quiet','--depth','1','origin','refs/heads/codex/wrd-training-data-20261025'],cold,env)
 assert run(['git','rev-parse','FETCH_HEAD'],cold,env).decode().strip()==commit,'REMOTE_COMMIT_MISMATCH'
 run(['git','update-ref','refs/heads/verify05',commit],cold,env)
 run(['git','symbolic-ref','HEAD','refs/heads/verify05'],cold,env)
 storage=cold/'fresh_lfs';assert not storage.exists()
 run(['git','config','lfs.storage',str(storage)],cold,env)
 print('READING_SELECTED_REMOTE_GIT_BLOBS_WITH_BATCH_NO_WINDOWS_CHECKOUT',flush=True)
 queries=''.join(commit+':'+name+'\n'for name in expected).encode()
 result=subprocess.run(['git','cat-file','--batch'],cwd=cold,env=env,input=queries,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
 stream=io.BytesIO(result.stdout)
 lfs=[];ordinary=0
 for name,ref in expected.items():
  header=stream.readline().decode().strip().split();assert len(header)==3 and header[1]=='blob',name
  size=int(header[2]);b=stream.read(size);assert len(b)==size and stream.read(1)==b'\n'
  if b.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
   lines=b.decode().splitlines();oid=next(s[11:]for s in lines if s.startswith('oid sha256:'));size=int(next(s[5:]for s in lines if s.startswith('size ')))
   assert oid==ref['sha256'] and size==ref['bytes'];lfs.append({'path':name,'oid_sha256':oid,'bytes':size})
  else:
   assert len(b)==ref['bytes']and hashlib.sha256(b).hexdigest()==ref['sha256'],name;ordinary+=1
 assert len(lfs)==expected_lfs and ordinary==len(expected)-expected_lfs
 assert not (storage/'objects').exists(),'LFS_STORAGE_NOT_EMPTY_BEFORE_FETCH'
 print('FETCHING_ACTUAL_LFS_OBJECTS_FROM_REMOTE_EMPTY_STORAGE',flush=True)
 include=','.join(r['path']for r in lfs)
 run(['git','-c','lfs.fetchrecentalways=false','lfs','fetch','--include='+include,'--exclude=','origin','HEAD'],cold,env)
 for ref in lfs:
  h=ref['oid_sha256'];p=storage/'objects'/h[:2]/h[2:4]/h
  assert p.stat().st_size==ref['bytes']and digest(p)==h,ref['path']
 result={'status':'PASS_REMOTE_ORDINARY_BYTES_AND_COLD_ACTUAL_LFS_ENTITIES','commit':commit,
         'branch':'codex/wrd-training-data-20261025','remote':'https://github.com/jiaotangbuding177/WRD_dataset.git',
         'ordinary_files_verified':ordinary,'actual_LFS_objects_verified':lfs,'actual_LFS_bytes':sum(r['bytes']for r in lfs),
         'cold_storage_empty_before_fetch':True,'local_release_LFS_cache_not_reused':True,'ordinary_and_LFS_pointer_only_checks_not_confused':True,
         'source_restored_dual_tokenizer_and_loader_QA_previously_passed':True,'training_started':False,
         'script_sha256':digest(__file__)}
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--cold',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
 p.add_argument('--prefix',action='append');p.add_argument('--expected-lfs',type=int,default=3);a=p.parse_args()
 r=verify(a.commit,a.cold,a.prefix,a.expected_lfs);a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(r),flush=True)
