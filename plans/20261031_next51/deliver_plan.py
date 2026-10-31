"""Publish/verify only the explicit next51 planning files, never training data.

Run from the original research workspace with --workspace D:/skillloop.
No model libraries, Agent launches, corpus admission or execution are used.
The build reuses existing credential guards without printing any values.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys

BASE = '9577220bbf13a3bbcaf9123e0a613189a3c5b67f'
PLAN = 'plans/20261031_next51'
BRANCH = 'codex/wrd-training-data-20261025'
REPOSITORY = 'https://github.com/jiaotangbuding177/WRD_dataset.git'

def digest(b):
    return hashlib.sha256(b).hexdigest()

def save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def git(repo, *args):
    return subprocess.check_output(['git','-c','http.version=HTTP/1.1',
        '-c','http.sslBackend=openssl',*args], cwd=repo)

def module(name, path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s)
    previous=sys.dont_write_bytecode
    sys.dont_write_bytecode=True
    try:
        s.loader.exec_module(m)
    finally:
        sys.dont_write_bytecode=previous
    return m

def mappings(root):
    local = root/'research/plans/20261031_wrd_next51'
    pairs=[(local/n,n) for n in ['PLAN.md','READINESS_STATUS.json','deliver_plan.py']]
    pairs += [(root/'research/designs'/n,'designs/'+n) for n in ['A_B_MODULES.md','PIPELINE.md']]
    pairs += [(root/'research/designs/history/5.0.50/next51_plan_20261031'/n,
        'history/5.0.50/'+n) for n in ['A_B_MODULES.md','PIPELINE.md']]
    pairs += [(root/'research/memory/2026-10-31_wrd_next51_plan.md','MEMORY.md')]
    work=root/'output/20261031_wrd_next51_planning'
    for group, names in {
      'gap_review':['GAP_REVIEW_AND_BOUNDED_PLAN.md','GAP_REVIEW_METADATA.json',
        'OLD8376_REBASED_OWNER_WORKLOAD.metadata.jsonl.gz',
        'OUTCOME35_CURRENT09_CROSSCHECK.metadata.json',
        'SLIDE_CURRENT_VIEW_RESOURCE_LINEAGE_METADATA.json',
        'recount_planning_metadata.py','inspect_slide_lineage.py'],
      'train_review':['REVIEW.md','PLANNING_FACTS.json','recount.py','ROOT_PLAN_REVIEW.md'],
      'autonomy_review':['PROPOSAL.md'],
    }.items():
        pairs += [(work/group/n,'reviews/'+group+'/'+n) for n in names]
    return pairs

def build(root, release, out):
    assert git(release,'rev-parse','HEAD').decode().strip()==BASE
    assert git(release,'branch','--show-current').decode().strip()==BRANCH
    assert not git(release,'status','--porcelain').strip(), 'RELEASE_MUST_START_CLEAN'
    destination=release/PLAN
    assert not destination.exists(), 'PLAN_DESTINATION_EXISTS'
    for name in ['A_B_MODULES.md','PIPELINE.md']:
        txt=(root/'research/designs'/name).read_text(encoding='utf-8-sig')
        assert '设计版本：5.0.51' in txt and '变更编号：ALG-20261031-03' in txt
    facts=json.loads((root/'research/plans/20261031_wrd_next51/READINESS_STATUS.json').read_text())
    assert facts['new_admitted_targets_this_round']==0
    assert not facts['model_backward_or_optimizer_this_round']
    entries=[]
    for source, relative in mappings(root):
        b=source.read_bytes()
        target=destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b)
        entries.append({'path':relative,'bytes':len(b),'sha256':digest(b),
          'source':source.relative_to(root).as_posix(), 'category':'READ_ONLY_PLANNING_OR_METADATA'})
    pm={'schema':'wrd-next51-public-plan-manifest-v1','scope':'PLAN_ONLY_NOT_NEW_DATA',
      'design_revision':'5.0.51','actual_data_revision':'5.0.50',
      'baseline_git_commit':BASE,'files':entries,
      'research_source_head':git(root,'rev-parse','HEAD').decode().strip(),
      'full_pipeline_training_ready':False,'new_training_rows':0,'new_business_calls':0,
      'model_weights_loaded':False,'model_training_started':False}
    save(destination/'PUBLIC_MANIFEST.json',pm)
    readme=release/'README.md'
    original=readme.read_bytes()
    prefix=('**2026-10-31 下一轮计划51，尚未执行处理：** '
      '[完整计划](plans/20261031_next51/PLAN.md) · '
      '[就绪状态](plans/20261031_next51/READINESS_STATUS.json) · '
      '[只读核账与独立复核](plans/20261031_next51/reviews/train_review/ROOT_PLAN_REVIEW.md)。'
      '先复核资源血缘并恢复原R—动作—版本—反馈，准备完整父输入，再生成真实下一主集。'
      '原R的91.78%在R-only，原生原R＋当前动作仅2来源；保留全部原R-only。'
      '当前09仍595目标／216154正tokens，完整自主与合格KEEP仍0；'
      '本轮无新增行、采集或训练。计划51不取代实际09／50入口。\n\n').encode()
    readme.write_bytes(prefix+original)
    attrs=release/'.gitattributes'
    b=attrs.read_bytes()
    attrs.write_bytes(b+(b'' if b.endswith(b'\n') else b'\n')+f'{PLAN}/** -text\n'.encode())
    guard=module('next51_guard',root/'research/data_prep/wrd_curation09/package09.py')
    old=module('next51_known',root/'research/data_prep/wrd_main_v10/package_checkpoint05.py')
    needles=old.credential_needles()
    scans=[]
    for p in [*sorted(destination.rglob('*')),readme,attrs]:
        if p.is_file():
            scans.append({'path':p.relative_to(release).as_posix(),**guard.scan_file(p,needles)})
    assert git(release,'diff',BASE,'--','dataset').strip()==b''
    assert git(release,'diff',BASE,'--','TRAINING_ENTRYPOINT.json').strip()==b''
    report={'status':'PASS_PLAN_ONLY_BUILD','baseline':BASE,'file_count':len(entries)+1,
      'public_manifest_sha256':digest((destination/'PUBLIC_MANIFEST.json').read_bytes()),
      'known_credential_and_generic_raw_gzip_scan':'PASS','scans':scans,
      'all_dataset_tree_unchanged':True,'training_entrypoint_unchanged':True,
      'new_admitted_rows':0,'new_business_calls':0,'training_started':False}
    save(out/'LOCAL_PLAN_BUILD_QA.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='scans'}))

def verify(root, release, out, revision):
    assert len(revision)==40 and all(c in '0123456789abcdef' for c in revision)
    cold=out/('remote_'+revision[:12]+'.git')
    assert not cold.exists(), 'FRESH_REMOTE_DIRECTORY_REQUIRED'
    cold.mkdir(parents=True)
    git(cold,'init','--bare')
    git(cold,'remote','add','origin',REPOSITORY)
    git(cold,'config','remote.origin.promisor','true')
    git(cold,'config','remote.origin.partialclonefilter','blob:none')
    git(cold,'fetch','--no-tags','--depth=1','--filter=blob:none','origin',revision)
    assert git(cold,'rev-parse','FETCH_HEAD').decode().strip()==revision
    pm_bytes=git(cold,'show',revision+':'+PLAN+'/PUBLIC_MANIFEST.json')
    pm=json.loads(pm_bytes)
    assert pm_bytes==(release/PLAN/'PUBLIC_MANIFEST.json').read_bytes()
    wanted={r['path'] for r in pm['files']}|{'PUBLIC_MANIFEST.json'}
    got=git(cold,'ls-tree','-r','--name-only',revision,'--',PLAN).decode().splitlines()
    assert {n[len(PLAN)+1:] for n in got}==wanted
    checked=[]
    for row in pm['files']:
        p=PLAN+'/'+row['path']
        b=git(cold,'show',revision+':'+p)
        assert len(b)==row['bytes'] and digest(b)==row['sha256']
        assert b==(release/p).read_bytes()
        checked.append({'path':p,'bytes':len(b),'sha256':digest(b)})
    for p in ['README.md','.gitattributes','TRAINING_ENTRYPOINT.json']:
        b=git(cold,'show',revision+':'+p)
        assert b==(release/p).read_bytes()
        checked.append({'path':p,'bytes':len(b),'sha256':digest(b)})
    same={}
    for p in ['dataset','dataset/20261031_v10_checkpoint09','TRAINING_ENTRYPOINT.json']:
        baseline=git(release,'rev-parse',BASE+':'+p).decode().strip()
        remote=git(cold,'rev-parse',revision+':'+p).decode().strip()
        assert baseline==remote
        same[p]=remote
    result={'status':'PASS_FRESH_REMOTE_PLAN_BYTES','revision':revision,
      'ordinary_files_read':len(checked)+1,'public_manifest_sha256':digest(pm_bytes),
      'files':checked,'unchanged_from_baseline_objects':same,
      'dataset_payload_downloaded_this_round':False,
      'note':'Plan-only publication; existing dataset object trees unchanged. No new AES/LFS body exists or was redownloaded.',
      'new_business_calls':0,'new_admitted_rows':0,'training_started':False}
    save(out/'REMOTE_PLAN_QA.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('action',choices=['build','verify'])
    ap.add_argument('--workspace',type=Path,required=True)
    ap.add_argument('--revision')
    a=ap.parse_args()
    workspace=a.workspace.resolve()
    release=workspace/'output/20261025_wrd_training_dataset/git_release'
    out=workspace/'output/20261031_wrd_next51_planning/delivery'
    out.mkdir(parents=True,exist_ok=True)
    if a.action=='build':
        build(workspace,release,out)
    else:
        verify(workspace,release,out,a.revision)
