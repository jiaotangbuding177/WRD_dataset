"""Explicit-file encrypted checkpoint05, including real arrays and evidence.

No source tree outside named frozen material directories is traversed. A
prepared allowlist must be pinned before building. Does not train or run code
from the archive. The local key is never added to the publication directory.
"""
from __future__ import annotations
import argparse
import base64
import gzip
import hashlib
import importlib.util
import io
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import tarfile

ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/'output/20261027_wrd_main_v10'
WORK=ROOT/'output/20261029_wrd_delivery05'
BASE=ROOT/'output/wrd04root'
KEY=ROOT/'output/20261025_wrd_reasoning_recovery_v4/local_delivery_key/wrd-reasoning-v4.key'
RELEASE=ROOT/'output/20261025_wrd_training_dataset/git_release'
DEST=RELEASE/'dataset/20261029_v10_checkpoint05'

def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pin(p):return {'source':str(p.resolve()),'bytes':p.stat().st_size,'sha256':digest(p)}
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def source_guard(p):
    p=Path(p)
    for ancestor in [p,*p.parents]:
        assert not ancestor.is_symlink() and not (hasattr(ancestor,'is_junction') and ancestor.is_junction()),str(p)
    assert not any(x.lower() in {'private','.ssh','.git','sdk_traces','sdk-traces'} for x in p.parts),str(p)
    assert p.suffix.lower() not in {'.key','.db','.sqlite','.sqlite3','.pyc'},str(p)
    assert p.name not in {'model_consumer.json','model_upstream.json'}
    return p

def prepare(native_manifest):
    dest=WORK/'prepared05';dest.mkdir(exist_ok=False)
    entries={};aliases=[];history=[]
    def add(name,p,expected=None,original=None):
        assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts and '\\' not in name
        source_guard(p)
        p=Path(p);assert p.is_file() and not p.is_symlink(),str(p)
        for ancestor in [p,*p.parents]:
            assert not ancestor.is_symlink() and not (hasattr(ancestor,'is_junction') and ancestor.is_junction()),str(p)
        assert p.suffix.lower() not in {'.key','.db','.sqlite','.sqlite3','.pyc'},str(p)
        assert not any(x.lower() in {'private','.ssh','.git','sdk_traces','sdk-traces'} for x in p.parts),str(p)
        assert p.name not in {'model_consumer.json','model_upstream.json'}
        r=pin(p)
        if expected is not None:assert r['sha256']==expected,(name,'source changed')
        if name in entries and entries[name]['sha256']!=r['sha256']:
            old=entries[name];oldname='history/checkpoint04_or_prior/'+old['sha256'][:12]+'/'+name
            entries[oldname]=old;history.append({'replaced_path':name,'old_sha256':old['sha256'],'preserved_at':oldname})
        entries[name]=r
        aliases.append({'original_absolute_path':original or str(p.resolve()),'archive_path':name,'sha256':r['sha256']})
    def tree(prefix,folder):
        folder=Path(folder);assert folder.is_dir(),str(folder)
        for p in sorted(folder.rglob('*')):
            assert not p.is_symlink(),str(p)
            if not p.is_file() or p.suffix.lower()=='.pyc' or '__pycache__' in p.parts:continue
            add(prefix+'/'+p.relative_to(folder).as_posix(),p)
    # Start from authenticated, restored checkpoint04 actual files, not live paths.
    old=load(BASE/'PAYLOAD_MANIFEST.json')
    receipt=load(RELEASE/'dataset/20261027_v10_checkpoint04/ENCRYPTED_DELIVERY_REPORT.json')
    assert digest(BASE/'PAYLOAD_MANIFEST.json')==receipt['payload_manifest_sha256']
    for ref in old['files']:
        p=BASE/ref['path'];assert p.stat().st_size==ref['bytes']
        add(ref['path'],p,ref['sha256'],ref.get('original_path'))
    add('history/checkpoint04/PAYLOAD_MANIFEST.json',BASE/'PAYLOAD_MANIFEST.json')
    for rel in ['TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json','COST_ACCOUNTING_SCOPE.json']:
        add(rel,DATA/rel)
    active=load(DATA/'TRAINING_MANIFEST.json')
    for ref in active['active_compilation_reports']:
        relative=PurePosixPath(ref['path'])
        assert not relative.is_absolute() and '..' not in relative.parts and '\\' not in ref['path']
        rel=str(relative.parent);assert (DATA/rel).resolve().is_relative_to(DATA.resolve())
        tree(rel,DATA/rel)
    for ref in active['external_root_admission_receipts']:add(ref['path'],DATA/ref['path'],ref['sha256'])
    add('clean_inputs/source_scope.metadata.jsonl.gz',DATA/'clean_inputs/source_scope.metadata.jsonl.gz')
    for rel in ['native_HTML_B_training_01','CV_clean_resource_construction_01','CV_clean_resource_construction_02',
                'historical_v6_action_recovery_01','historical_v6_construction_review_02',
                'independent_resume_audit_20261029','training_strategy_review_02']:
        tree('evidence_current/'+rel,DATA/rel)
    for name in ['MAIN_526_FRESH_QA.json','MAIN_FINAL_FRESH_QA.json','ROOT_THREE_RECOVERIES_ACCEPTANCE.json',
                 'CURRENT_DATA_AND_EXPOSURE.json','OWNER_EXPOSURE_SCHEDULE.json','SOURCE_RECOVERY_RECEIPT.json',
                 'LOSS_MASK_NEGATIVE_CANARY.json','COST_SCOPE_REFRESH.json','FINAL_CAUSAL_COVERAGE.md',
                 'RAW_POPULATION_RECONCILIATION.md','TRAINING_CANDIDATES.json']:
        add('quality_current/'+name,WORK/name)
    for name in ['A_B_MODULES.md','PIPELINE.md']:add('design_reference/'+name,ROOT/'research/designs'/name)
    for p in (ROOT/'research/plans/20261027_wrd_main_v10').glob('*'):
        if p.is_file():add('design_reference/'+p.name,p)
    for p in (ROOT/'research/data_prep/wrd_main_v10').glob('*.py'):add('source_tooling/'+p.name,p)
    add('source_tooling/restore_checkpoint.py',RELEASE/'dataset/20261027_v10_checkpoint04/tooling/restore_checkpoint.py')
    # Both independent tokenizer asset sets are real files; never model weights.
    for name in ['primary_14b','control_8b']:
        folder=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets'/name
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.suffix in ['.json','.jinja','.txt']:
                add('tokenizer_assets/'+name+'/'+p.name,p)
    # Closed native trace/CAS collection produced by a separate owner and re-read.
    source_guard(native_manifest)
    nm=load(native_manifest);nbase=native_manifest.parent
    listed=nbase/'FINAL_ALLOWLIST_02.jsonl'
    source_guard(listed)
    assert digest(listed)==nm['allowlist_sha256']
    objects={}
    for line in listed.read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        ref=json.loads(line);name=ref['cas_relative_path']
        assert name=='objects/'+ref['sha256'] and len(ref['sha256'])==64
        p=source_guard(nbase/name);assert p.stat().st_size==ref['bytes'] and digest(p)==ref['sha256']
        objects[name]=p
        aliases.append({'original_absolute_path':ref['source_path'],'archive_path':'native_material05/'+name,'sha256':ref['sha256']})
    assert len(objects)==nm['unique_CAS_objects']
    for name,p in sorted(objects.items()):add('native_material05/'+name,p)
    for name in ['ALLOWLIST.jsonl','COST_CENSUS.json','EXCLUSIONS.json','EXPLICIT_REFERENCE_CLOSURE_CHECK_01.json',
                 'FINAL_ALLOWLIST_02.jsonl','FINAL_MANIFEST_02.json','MANIFEST.json','MISSING_OR_MISMATCHED.json',
                 'OPTIONAL_ABSENCE_CLASSIFICATION_01.json','Q_RECHECK_20261029.json','RAW_HTTP_CENSUS.json']:
        add('native_material05/'+name,nbase/name)
    add('native_material05_source_manifest.json',native_manifest)
    save(dest/'EVIDENCE_PATH_ALIASES05.json',{'aliases':aliases,'versioned_replacements':history,
        'same_original_path_may_have_multiple_frozen_SHA_versions':True,'all_data_body_bytes_unchanged':True})
    add('EVIDENCE_PATH_ALIASES05.json',dest/'EVIDENCE_PATH_ALIASES05.json')
    m={'schema':'wrd-checkpoint05-explicit-prepared-allowlist','status':'PREPARED_NOT_BUILT',
       'files':[dict(path=n,**r) for n,r in sorted(entries.items())],
       'actual_manifest_sha256':digest(DATA/'TRAINING_MANIFEST.json'),'actual_counts':active['actual_counts'],
       'native_material_manifest_sha256':digest(native_manifest),'training_started':False,
       'source_code_versions_not_recovered_are_disclosed_not_fabricated':True}
    save(dest/'ALLOWLIST.json',m)
    print(json.dumps({'prepared':str(dest/'ALLOWLIST.json'),'sha256':digest(dest/'ALLOWLIST.json'),
          'files':len(entries),'source_bytes':sum(r['bytes'] for r in entries.values())}))

def credential_needles():
    values=[]
    def walk(x,key=''):
        if isinstance(x,dict):
            for k,v in x.items():walk(v,str(k))
        elif isinstance(x,list):
            for v in x:walk(v,key)
        elif isinstance(x,str) and len(x)>=12 and any(k in key.lower() for k in ['api_key','apikey','token','bearer','authorization','password','secret']):
            values.append(x.encode())
    for name in ['model_consumer.json','model_upstream.json']:
        walk(load(DATA/'runtime_preflight/private'/name))
    key=KEY.read_bytes();values.extend([key,key.hex().encode(),base64.b64encode(key)])
    return set(values)

def build(allowlist,expected):
    assert digest(allowlist)==expected,'PREPARED_ALLOWLIST_CHANGED'
    prepared=load(allowlist);assert not DEST.exists(),'PUBLIC_DESTINATION_MUST_BE_NEW'
    needles=credential_needles();scan=CounterLike()
    sources={}
    for ref in prepared['files']:
        p=source_guard(ref['source']);assert p.stat().st_size==ref['bytes'] and digest(p)==ref['sha256']
        b=p.read_bytes()
        raw=b
        if b.startswith(b'\x1f\x8b'):
            b=gzip.decompress(b)
        for view in [raw,b]:
            assert not any(n in view for n in needles),'PRIVATE_CREDENTIAL_VALUE_IN_PAYLOAD'
            assert not re.search(rb'\bsk-[A-Za-z0-9_-]{24,}\b',view),'UNREVIEWED_KEY_SHAPED_VALUE_IN_PAYLOAD'
            assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\r\n]{64,}',view),'PRIVATE_KEY_BODY_IN_PAYLOAD'
        scan.add(len(b));sources[ref['path']]=p
    work=WORK/'build05';work.mkdir(exist_ok=False)
    pm={'schema':'wrd-checkpoint05-authenticated-payload','status':'ACTUAL_BYTES_NOT_A_CANDIDATE_INDEX',
        'files':[{'path':r['path'],'bytes':r['bytes'],'sha256':r['sha256'],'original_path':r['source']} for r in prepared['files']],
        'actual_counts':prepared['actual_counts'],'prepared_allowlist_sha256':expected,
        'full_WRD_main_training_ready':False,'training_started':False}
    save(work/'PAYLOAD_MANIFEST.json',pm)
    plain=work/'wrd-v10-checkpoint05.tar.gz'
    with tarfile.open(plain,'w:gz',compresslevel=3,format=tarfile.PAX_FORMAT) as tf:
        tf.add(work/'PAYLOAD_MANIFEST.json',arcname='PAYLOAD_MANIFEST.json',recursive=False)
        for n,p in sorted(sources.items()):tf.add(p,arcname=n,recursive=False)
    DEST.mkdir(parents=True);(DEST/'controlled').mkdir();(DEST/'tooling').mkdir()
    cipher=DEST/'controlled/wrd-v10-checkpoint05.tar.gz.aesgcm'
    enc=module('frozen_encrypt05',ROOT/'research/data_prep/wrd_reasoning_v4/encrypted_delivery.py')
    report=enc.encrypt(plain,cipher,KEY,reuse_key=True)
    report.update(schema_version='wrd-v10-checkpoint05-encryption-receipt',payload_manifest_sha256=digest(work/'PAYLOAD_MANIFEST.json'),
        authenticated_files=len(sources)+1,plaintext_bytes=plain.stat().st_size,training_started=False,
        full_WRD_main_training_ready=False,prepared_allowlist_sha256=expected)
    save(DEST/'ENCRYPTED_DELIVERY_REPORT.json',report)
    def public_copy(name,archive_name):
        source=sources[archive_name];ref=next(r for r in prepared['files'] if r['path']==archive_name)
        assert digest(source)==ref['sha256']
        shutil.copyfile(source,DEST/name)
        assert digest(DEST/name)==ref['sha256']
    public_copy('tooling/restore_checkpoint.py','source_tooling/restore_checkpoint.py')
    public_copy('tooling/checkpoint_loader.py','source_tooling/verify_main05.py')
    for name in ['TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json','COST_ACCOUNTING_SCOPE.json']:
        public_copy(name,name)
    for name in ['TRAINING_PLAN.md','MODEL_INPUT_OUTPUT.md','MODEL_CONTEXT_REQUIREMENTS.md','COVERAGE_EXPANSION.md']:
        public_copy(name,'design_reference/'+name)
    for name in ['FINAL_CAUSAL_COVERAGE.md','RAW_POPULATION_RECONCILIATION.md','TRAINING_CANDIDATES.json',
                 'CURRENT_DATA_AND_EXPOSURE.json','SOURCE_RECOVERY_RECEIPT.json','MAIN_FINAL_FRESH_QA.json',
                 'LOSS_MASK_NEGATIVE_CANARY.json']:
        public_copy(name,'quality_current/'+name)
    save(DEST/'PACKAGING_SCAN.json',{'status':'PASS','files_scanned':scan.n,'decoded_bytes_scanned':scan.b,
        'private_known_credential_matches':0,'key_not_uploaded':True,'training_started':False})
    save(WORK/'CHECKPOINT05_BUILD_RECEIPT.json',{'status':'BUILT_AUTHENTICATED_NOT_YET_ROOT_RESTORED_OR_REMOTE_VERIFIED',
        'publication_directory':str(DEST),'authenticated_files':len(sources)+1,'source_bytes':sum(r['bytes'] for r in prepared['files']),
        'ciphertext_bytes':report['ciphertext_bytes'],'ciphertext_sha256':report['ciphertext_sha256'],
        'training_started':False})
    print(json.dumps({'status':'BUILT','files':len(sources)+1,'ciphertext_bytes':report['ciphertext_bytes'],
                     'ciphertext_sha256':report['ciphertext_sha256']}))

class CounterLike:
    def __init__(self):self.n=0;self.b=0
    def add(self,b):self.n+=1;self.b+=b

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare-native-manifest',type=Path)
    p.add_argument('--build-allowlist',type=Path);p.add_argument('--expected-sha256');a=p.parse_args()
    if a.prepare_native_manifest:prepare(a.prepare_native_manifest)
    else:assert a.build_allowlist and a.expected_sha256;build(a.build_allowlist,a.expected_sha256)
