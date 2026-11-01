"""Cold-read ordinary Git blobs at a pushed commit; no model or Git mutations."""
from pathlib import Path
import argparse,base64,concurrent.futures,hashlib,json,os,subprocess,time,urllib.request,urllib.parse,urllib.error

ROOT=Path('D:/skillloop')
REPO=ROOT/'output/20261025_wrd_training_dataset/git_release'
OUT=ROOT/'output/20261101_wrd_git_full_delivery'
BASE='75b70424f0c7a650da4a94b8b5288ca077c050ce'
TARGET='c9277e8c97c877dedde8e7811ec1b1fcc55e864b'
OWNER_REPO='jiaotangbuding177/WRD_dataset'
BRANCH='codex/wrd-training-data-20261025'
PREFIX='plans/20261101_full_pipeline_sft/'
EXPECTED_MANIFEST='aabc40e636da90e2732b8c311b116267b16f9739c4aa98e4c9e58f21970e448c'
AUTH=None

def digest(data):return hashlib.sha256(data).hexdigest()
def git(*args):
    return subprocess.run(['git',*args],cwd=REPO,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
def local_inputs():
    paths=[p.decode('utf-8') for p in git('diff','--name-only','--diff-filter=ACMRT','-z',BASE,TARGET).split(b'\0') if p]
    ordinary={};lfs=[]
    for p in paths:
        body=git('show',TARGET+':'+p)
        blob_sha1=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
        if body.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
            fields=dict(line.split(' ',1) for line in body.decode('ascii').splitlines()[1:])
            lfs.append({'path':p,'git_pointer_sha1':blob_sha1,'entity_sha256':fields['oid'].removeprefix('sha256:'),'entity_bytes':int(fields['size']),'body_verification':'DELEGATED_TO_INDEPENDENT_SEVEN_PACKAGE_ENTITY_AUDIT'})
        else:ordinary[p]={'body':body,'bytes':len(body),'sha256':digest(body),'git_blob_sha1':blob_sha1}
    if digest(ordinary[PREFIX+'PUBLIC_MANIFEST.json']['body'])!=EXPECTED_MANIFEST:raise RuntimeError('FINAL_MANIFEST_PIN_MISMATCH')
    return ordinary,lfs

def gcm_auth():
    global AUTH
    if AUTH is not None:return AUTH
    env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'}
    result=subprocess.run(['git','credential','fill'],cwd=REPO,input=b'protocol=https\nhost=github.com\n\n',stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=30)
    if result.returncode:raise RuntimeError('GCM_AUTH_UNAVAILABLE')
    fields=dict(line.split('=',1) for line in result.stdout.decode('utf-8').splitlines() if '=' in line)
    if not fields.get('password'):raise RuntimeError('GCM_PASSWORD_MISSING')
    AUTH='Bearer '+fields['password']
    return AUTH

def get_bytes(url,cap,api=False):
    headers={'User-Agent':'WRD55-independent-artifact-verification','Cache-Control':'no-cache'}
    if api:headers['Accept']='application/vnd.github+json'
    if api and AUTH is not None:headers['Authorization']=AUTH
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=45) as response:
                data=response.read(cap+1)
                if len(data)>cap:raise RuntimeError('UNEXPECTED_REMOTE_SIZE')
                return data
        except urllib.error.HTTPError as error:
            if api and error.code in (401,403) and 'Authorization' not in headers:
                headers['Authorization']=gcm_auth();continue
            if error.code in (429,500,502,503,504) and attempt<2:
                time.sleep(2*(attempt+1));continue
            raise RuntimeError('REMOTE_HTTP_'+str(error.code)) from None
        except urllib.error.URLError:
            if attempt<2:time.sleep(2*(attempt+1));continue
            raise RuntimeError('REMOTE_NETWORK_ERROR') from None
    raise RuntimeError('REMOTE_RETRIES_EXHAUSTED')

def get_json(path):
    return json.loads(get_bytes('https://api.github.com/repos/'+OWNER_REPO+'/'+path,5000000,api=True))

def run():
    ordinary,lfs=local_inputs();OUT.mkdir(parents=True,exist_ok=True)
    prepared={'schema':'wrd55-local-plan-remote-audit-preparation-not-remote-proof','base_commit':BASE,'target_commit':TARGET,'ordinary_blob_count':len(ordinary),'ordinary_blob_bytes':sum(v['bytes'] for v in ordinary.values()),'lfs_pointer_count':len(lfs),'lfs_entities_delegated':lfs,'public_manifest_sha256':EXPECTED_MANIFEST,'remote_requests_made':0,'is_remote_verification':False,'ordinary_expected':[{'path':p,**{k:v for k,v in info.items() if k!='body'}} for p,info in ordinary.items()]}
    if args.prepare_only:
        destination=OUT/'REMOTE_PLAN_BLOBS55_PREPARED.json';destination.write_text(json.dumps(prepared,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'status':'PREPARED_LOCAL_ONLY','ordinary_blobs':len(ordinary),'bytes':prepared['ordinary_blob_bytes'],'LFS_entities_skipped':len(lfs),'sha256':digest(destination.read_bytes())}),flush=True);return

    remote_commit=get_json('git/commits/'+TARGET)
    local_tree=git('rev-parse',TARGET+'^{tree}').decode().strip()
    if remote_commit.get('sha')!=TARGET or remote_commit.get('tree',{}).get('sha')!=local_tree:raise RuntimeError('REMOTE_COMMIT_OR_TREE_MISMATCH')
    remote_ref=get_json('git/ref/heads/'+urllib.parse.quote(BRANCH,safe='/'))
    ref_sha=remote_ref['object']['sha']
    if ref_sha!=TARGET:
        comparison=get_json('compare/'+TARGET+'...'+ref_sha)
        if comparison.get('status') not in ('ahead','identical'):raise RuntimeError('REMOTE_BRANCH_DOES_NOT_CONTAIN_TARGET')
    print(json.dumps({'status':'REMOTE_COMMIT_AND_BRANCH_CONFIRMED','commit':TARGET,'branch_head':ref_sha,'ordinary_blobs_to_read':len(ordinary)}),flush=True)
    cold=OUT/'cold_plan_blobs55';cold.mkdir(parents=True,exist_ok=True)
    fetched={};results=[]
    def fetch(item):
        p,expected=item
        raw='https://raw.githubusercontent.com/'+OWNER_REPO+'/'+TARGET+'/'+urllib.parse.quote(p,safe='/')
        body=get_bytes(raw,max(expected['bytes'],1024)+1024)
        if len(body)!=expected['bytes'] or digest(body)!=expected['sha256']:raise RuntimeError('ORDINARY_BLOB_MISMATCH:'+p)
        destination=cold.joinpath(*p.split('/'))
        if not destination.resolve().is_relative_to(cold.resolve()):raise RuntimeError('UNSAFE_GIT_PATH')
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(body)
        return p,body,{'path':p,'bytes':len(body),'sha256':digest(body),'git_blob_sha1':expected['git_blob_sha1'],'download':'FRESH_PINNED_COMMIT_PUBLIC_RAW','same_as_local_commit_blob':True}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for future in concurrent.futures.as_completed([pool.submit(fetch,item) for item in ordinary.items()]):
            p,body,record=future.result();fetched[p]=body;results.append(record)
            if len(results)%10==0 or len(results)==len(ordinary):print(json.dumps({'ordinary_blobs_freshly_verified':len(results),'total':len(ordinary)}),flush=True)
    manifest=json.loads(fetched[PREFIX+'PUBLIC_MANIFEST.json'])
    for ref in manifest['files']:
        body=fetched[PREFIX+ref['path']]
        if len(body)!=ref['bytes'] or digest(body)!=ref['sha256']:raise RuntimeError('REMOTE_PUBLIC_MANIFEST_REF_MISMATCH')
    if len(manifest['files'])!=manifest['file_count']:raise RuntimeError('REMOTE_PUBLIC_MANIFEST_COUNT_MISMATCH')
    entry=json.loads(fetched['TRAINING_ENTRYPOINT.json']);config=json.loads(fetched[PREFIX+'TRAINING_CONFIG.json'])
    if entry['current_plan_design_revision']!='5.0.55' or entry['current_complete_course_candidate_optimizer_updates']!=236 or entry['current_complete_course_unique_targets']!=1250 or entry['current_complete_course_exposures']!=1254 or entry['training_execution_authorized']:raise RuntimeError('REMOTE_ENTRYPOINT_SCOPE_MISMATCH')
    if config['design_revision']!='5.0.55' or config['training_started'] or config['training_execution_authorized'] or config['Spark_training_runtime_verified']:raise RuntimeError('REMOTE_CONFIG_SCOPE_MISMATCH')
    for path in ['README.md',PREFIX+'PLAN.md',PREFIX+'designs/A_B_MODULES.md',PREFIX+'designs/PIPELINE.md']:
        if b'5.0.55' not in fetched[path] and path!='README.md':raise RuntimeError('REMOTE_DESIGN_VERSION_MISMATCH')
    report={'schema':'wrd55-independent-cold-remote-ordinary-git-blobs-v1','status':'PASS_ALL_ADDED_MODIFIED_ORDINARY_BLOBS_AND_REMOTE_PLAN_MANIFEST','repository':'https://github.com/'+OWNER_REPO,'branch':BRANCH,'base_commit':BASE,'verified_remote_commit':TARGET,'verified_remote_tree':local_tree,'observed_remote_branch_head':ref_sha,'remote_branch_contains_verified_commit':True,'remote_commit_and_tree_verified_by_official_GitHub_API':True,'ordinary_blobs_freshly_downloaded':len(results),'ordinary_blob_bytes':sum(r['bytes'] for r in results),'ordinary_blob_content_sha256_all_match_local_commit':True,'download_source':'Pinned commit raw.githubusercontent.com, every ordinary blob fetched anew; no local body used as remote evidence','public_manifest_sha256':digest(fetched[PREFIX+'PUBLIC_MANIFEST.json']),'public_manifest_references_freshly_verified':len(manifest['files']),'root_entrypoint_and_README_verified':True,'both_design55_blobs_verified':True,'lfs_pointer_blobs_excluded_from_ordinary_body_count':lfs,'LFS_body_verification_is_external_not_claimed_here':True,'normal_authentication_credentials_in_memory_only':AUTH is not None,'credential_or_signed_URL_written':False,'model_or_training_or_business_calls':0,'git_mutations':False,'files':sorted(results,key=lambda x:x['path'])}
    destination=OUT/'REMOTE_PLAN_BLOBS55.json';destination.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'ordinary_blobs':len(results),'bytes':report['ordinary_blob_bytes'],'manifest_refs':len(manifest['files']),'report_sha256':digest(destination.read_bytes())}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    try:run()
    except Exception as error:
        print(json.dumps({'status':'INCOMPLETE_REMOTE_AUDIT_NOT_A_PASS','error_type':type(error).__name__,'reason':str(error) if isinstance(error,RuntimeError) else 'DETAILS_NOT_PRINTED','target_commit':TARGET}),flush=True)
        raise SystemExit(1)
