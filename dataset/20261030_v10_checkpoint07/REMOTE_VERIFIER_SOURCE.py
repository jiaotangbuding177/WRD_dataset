"""Resume cold LFS verification after batch EOF; never uses release LFS cache."""
from pathlib import Path
import argparse,hashlib,io,json,os,subprocess,urllib.request,urllib.parse
ROOT=Path('D:/skillloop');RELEASE=ROOT/'output/20261025_wrd_training_dataset/git_release'
PREFIXES=['README.md','TRAINING_ENTRYPOINT.json','dataset/20261030_v10_checkpoint07']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(cmd,cwd,env):
    r=subprocess.run(cmd,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if r.returncode:raise RuntimeError(r.stderr.decode('utf-8','replace')[-2400:])
    return r.stdout
def main(a):
    cold=a.cold.resolve();assert cold.is_dir()
    env=dict(os.environ,GODEBUG='http2client=0',GIT_LFS_SKIP_SMUDGE='1',GIT_TERMINAL_PROMPT='0')
    commit=run(['git','rev-parse','FETCH_HEAD'],cold,env).decode().strip()
    assert commit==run(['git','rev-parse','HEAD'],RELEASE,env).decode().strip()
    names=run(['git','ls-tree','-r','--name-only','-z',commit,'--',*PREFIXES],RELEASE,env).decode().strip('\0').split('\0')
    queries=''.join(commit+':'+n+'\n' for n in names).encode()
    stream=io.BytesIO(subprocess.run(['git','cat-file','--batch'],cwd=cold,env=env,input=queries,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout)
    normal=0;large=[]
    for name in names:
        header=stream.readline().decode().split();assert len(header)==3 and header[1]=='blob'
        b=stream.read(int(header[2]));assert stream.read(1)==b'\n'
        p=RELEASE/name
        if b.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
            lines=b.decode().splitlines();oid=next(x[11:] for x in lines if x.startswith('oid sha256:'));size=int(next(x[5:] for x in lines if x.startswith('size ')))
            assert oid==sha(p) and size==p.stat().st_size;large.append({'path':name,'oid_sha256':oid,'bytes':size})
        else:assert len(b)==p.stat().st_size and hashlib.sha256(b).hexdigest()==sha(p);normal+=1
    assert len(large)==1 and normal==23
    configured=run(['git','config','--get','lfs.storage'],cold,env).decode().strip();storage=Path(configured)
    if not storage.is_absolute():storage=cold/storage
    storage=storage.resolve();assert storage.is_relative_to(cold)
    assert not (storage/'objects').exists() or not any(p.is_file() for p in (storage/'objects').rglob('*')),'INDEPENDENT_LFS_CACHE_NOT_EMPTY'
    print('ALL23_REMOTE_GIT_FILES_RECHECKED_AND_INDEPENDENT_LFS_STORAGE_EMPTY',flush=True)
    include=','.join(x['path'] for x in large)
    # A public GitHub media GET fetches the actual LFS entity, independent of
    # git-lfs's failing POST/download transport. Never read a local object as a
    # substitute. No credential or presigned URL is printed or published.
    print('DOWNLOADING_EXACT_COMMIT_LFS_ENTITY_VIA_VERIFIED_HTTP_RANGES',flush=True)
    ranges=[];resumed=0
    for ref in large:
        url='https://media.githubusercontent.com/media/jiaotangbuding177/WRD_dataset/'+commit+'/'+urllib.parse.quote(ref['path'],safe='/')
        p=cold/'independent_media_download.bin'
        if not p.exists():p.open('xb').close()
        offset=p.stat().st_size;assert offset<=ref['bytes'];resumed=offset
        # Verify an existing incomplete REMOTE prefix without copying any local
        # bytes into it. This is resumption, not reuse of the release LFS cache.
        with p.open('rb') as previous,(RELEASE/ref['path']).open('rb') as expected:
            while True:
                b=previous.read(1048576)
                if not b:break
                assert b==expected.read(len(b)),'PARTIAL_REMOTE_PREFIX_MISMATCH'
        while offset<ref['bytes']:
            end=min(offset+2*1048576,ref['bytes'])-1
            request=urllib.request.Request(url,headers={'User-Agent':'WRD-dataset-verifier','Range':f'bytes={offset}-{end}','Accept':'application/octet-stream'})
            last=None
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(request,timeout=90) as response:
                        assert response.status==206 and response.headers.get('Content-Range')==f'bytes {offset}-{end}/{ref["bytes"]}'
                        b=response.read(end-offset+2)
                    assert len(b)==end-offset+1
                    break
                except Exception as error:last=error
            else:raise RuntimeError('REMOTE_RANGE_FAILED_AFTER_THREE_ATTEMPTS') from last
            with p.open('ab') as output:output.write(b)
            ranges.append({'start':offset,'end_inclusive':end,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
            offset=end+1;print('VERIFIED_REMOTE_DOWNLOAD_BYTES '+str(offset)+'/'+str(ref['bytes']),flush=True)
        assert p.stat().st_size==ref['bytes'] and sha(p)==ref['oid_sha256']
    result={'status':'PASS_REMOTE_ORDINARY_BYTES_AND_COLD_ACTUAL_LFS_ENTITIES','commit':commit,'branch':'codex/wrd-training-data-20261025',
        'ordinary_files_verified':normal,'actual_LFS_objects_verified':large,'actual_LFS_bytes':sum(x['bytes'] for x in large),
        'completed_LFS_entity_cache_empty_before_fetch':True,'prior_LFS_client_requests_failed_or_incomplete_not_verified':True,
        'actual_entity_transport':'exact_commit_public_GitHub_media_verified_HTTP206_ranges_into_independent_file',
        'previous_partial_remote_bytes_resumed':resumed,'new_verified_HTTP_ranges':ranges,
        'local_release_LFS_cache_not_reused':True,'ordinary_and_LFS_pointer_only_checks_not_confused':True,
        'source_restored_dual_tokenizer_loader_and_canonical_arrays_previously_passed':True,
        'training_started':False,'script_sha256':sha(__file__)}
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cold',type=Path,required=True);p.add_argument('--out',type=Path,required=True);main(p.parse_args())
