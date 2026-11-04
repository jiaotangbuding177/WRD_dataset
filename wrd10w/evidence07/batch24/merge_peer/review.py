"""Independent static + key-free temporary-fixture review of delta07 merge layer."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
from types import SimpleNamespace

ROOT=Path('D:/skillloop');HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'research/data_prep/wrd_main_v10/merge_delta07.py'
RESTORE=ROOT/'output/20261025_wrd_training_dataset/git_release/dataset/20261029_v10_checkpoint06/tooling/restore_checkpoint.py'
def h(b):return hashlib.sha256(b).hexdigest()
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def ref(p,root):return {'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}

def one(case,code,base_duplicate=False,delta_duplicate=False,wrong_base=False,metadata_collision=False,traversal=False,lowercase_metadata=False):
    f=HERE/'fixtures'/h(code.encode())[:12]/case;f.mkdir(parents=True,exist_ok=False)
    module_path=f/'merge_delta07.py';module_path.write_text(code,encoding='utf-8')
    (f/'restore_checkpoint.py').write_text('''from pathlib import Path
import shutil,json
def restore(cipher,receipt,key,out):
    # Key-free fixture stub: only merge validation is being tested.
    shutil.copytree(cipher,out)
    return {'authenticated_files':len(json.loads((out/'PAYLOAD_MANIFEST.json').read_text())['files'])+1}
''',encoding='utf-8')
    base=f/'base';seed=f/'seed';base.mkdir();seed.mkdir()
    (base/'TRAINING_MANIFEST.json').write_text('{"targets":530}\n',encoding='utf-8')
    bf=ref(base/'TRAINING_MANIFEST.json',base);bm={'schema':'fixture-base','files':[bf,bf]if base_duplicate else[bf]}
    write(base/'PAYLOAD_MANIFEST.json',bm)
    (seed/'TRAINING_MANIFEST.json').write_text('{"targets":549}\n',encoding='utf-8');df=ref(seed/'TRAINING_MANIFEST.json',seed)
    files=[df,df]if delta_duplicate else[df]
    if metadata_collision or lowercase_metadata:
        name='merge_result.json' if lowercase_metadata else 'MERGE_RESULT.json'
        (seed/name).write_text('payload bytes that must not be silently overwritten',encoding='utf-8');files.append(ref(seed/name,seed))
    if traversal:files.append({'path':'../escape.txt','bytes':1,'sha256':h(b'x')})
    dm={'schema':'fixture-delta','base_payload_manifest_sha256':'0'*64 if wrong_base else h((base/'PAYLOAD_MANIFEST.json').read_bytes()),
        'base_training_manifest_sha256':h((base/'TRAINING_MANIFEST.json').read_bytes()),'files':files}
    write(seed/'PAYLOAD_MANIFEST.json',dm)
    spec=importlib.util.spec_from_file_location('merge_fixture_'+case,module_path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    out=f/'merged';args=SimpleNamespace(base=base,out=out,delta_out=f/'delta',cipher=seed,receipt=f/'NO_RECEIPT',key=f/'NO_KEY_READ')
    try:m.main(args);accepted=True;error=None
    except Exception as e:accepted=False;error={'type':type(e).__name__,'message':str(e)}
    bad=[]
    if accepted:
        mm=json.loads((out/'PAYLOAD_MANIFEST.json').read_text())
        for r in mm['files']:
            p=out/r['path']
            if not p.is_file() or p.stat().st_size!=r['bytes'] or h(p.read_bytes())!=r['sha256']:bad.append(r['path'])
    return {'case':case,'accepted':accepted,'error':error,'new_root_created':out.exists(),'merged_manifest_pin_mismatches':bad,
        'fixture_path':str(f),'real_key_or_cipher_read':False,'crypto_authentication_tested':False}

def main():
    code=SOURCE.read_text(encoding='utf-8');results=[one('valid_change',code),one('wrong_base',code,wrong_base=True),
        one('duplicate_base_manifest_entries',code,base_duplicate=True),one('duplicate_delta_manifest_entries',code,delta_duplicate=True),
        one('generated_metadata_collision',code,metadata_collision=True),one('generated_metadata_case_alias',code,lowercase_metadata=True),
        one('path_traversal',code,traversal=True)]
    issues=[]
    for r in results:
        if r['case']=='valid_change' and not r['accepted']:
            issues.append({'case':r['case'],'severity':'must_fix_ordinary_merge','finding':'Valid exact-base change was rejected.'})
        if r['case'] in {'wrong_base','path_traversal','generated_metadata_collision','generated_metadata_case_alias'} and r['accepted']:
            issues.append({'case':r['case'],'severity':'must_fix_required_rejection','finding':'An invalid-base, path or reserved metadata fixture was accepted.'})
        if r['case'] in {'duplicate_base_manifest_entries','duplicate_delta_manifest_entries'} and r['accepted']:
            issues.append({'case':r['case'],'severity':'must_fix_explicit_manifest_contract','finding':'Identical duplicate manifest entries are accepted; require unique canonical paths in both base and delta manifests before copying.'})
        if r['merged_manifest_pin_mismatches']:
            issues.append({'case':r['case'],'severity':'must_fix_manifest_integrity','finding':'Generated MERGE_RESULT overwrites a payload-listed file without updating/preserving its manifest reference. Reserve generated metadata paths or reject collision.'})
    spec=importlib.util.spec_from_file_location('reviewed_validate_refs',SOURCE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    invalid_names=['','.','a//b','a/./b','a/../b','a\\b','D:drive','a\nb','a\x00b','a.','a ',
        'merge_result.json','MERGE_EVIDENCE/MERGED06_AUTHENTICATED_MANIFEST.JSON','HISTORY/PRE_DELTA07/x']
    direct_validation=[]
    for n in invalid_names:
        try:module.validate_refs([{'path':n,'bytes':0,'sha256':'0'*64}]);rejected=False
        except (AssertionError,ValueError,TypeError):rejected=True
        direct_validation.append({'path_repr':repr(n),'rejected':rejected})
        if not rejected:issues.append({'case':'path_validation','severity':'must_fix_path','finding':repr(n)+' was accepted'})
    try:module.validate_refs([{'path':n,'bytes':0,'sha256':'0'*64}for n in ['X.txt','x.txt']]);rejected=False
    except AssertionError:rejected=True
    direct_validation.append({'case_insensitive_alias_pair':['X.txt','x.txt'],'rejected':rejected})
    if not rejected:issues.append({'case':'case_alias_pair','severity':'must_fix_path','finding':'Case-insensitive duplicate alias was accepted'})
    result={'schema':'wrd-delta07-independent-merger-peer-v1','status':'REPAIR_REQUIRED'if issues else'PASS_REVIEWED_MERGE_LAYER',
        'reviewed_merger':pin(SOURCE),'reviewed_restore_protocol':pin(RESTORE),'key_free_fixtures':results,'issues':issues,
        'direct_path_validation_canaries':direct_validation,
        'static_positive_findings':['Delta restore authenticates existing WRDENC4 AES-GCM format through the existing trusted restore module.',
            'Authenticated delta binds exact bytes of base merged06 PAYLOAD_MANIFEST and original TRAINING_MANIFEST before output merge.',
            'Only manifest-listed ordinary source files are copied, and source size/SHA and copied SHA are checked.',
            'Output and decrypted delta directories must be absent; no saved payload source is executed.',
            'Changed old paths are preserved under history/pre_delta07/<oldSHA-prefix>/path.',
            'Absolute/path-traversal and symlink leaf checks are present; resolve containment protects the chosen root.'],
        'restore_protocol_observation':'Existing restore verifies cipher/plain/manifest/member SHA and rejects duplicate tar members. Its expected=dict(files) construction alone does not reject duplicate manifest list entries; merge layer must independently reject them.',
        'remaining_recommendations':['Keep final real authenticated restore, cold-object verification and independent main-loader QA separate from this key-free review.'],
        'no_real_key_read':True,'full_merged_dataset_not_reprocessed':True,'training_started':False,'weights_loaded':False,
        'review_script_sha256':h(Path(__file__).read_bytes())}
    if (HERE/'PEER.json').exists():shutil.copyfile(HERE/'PEER.json',HERE/('PEER.previous.'+h((HERE/'PEER.json').read_bytes())[:12]+'.json'))
    write(HERE/'PEER.json',result)
    print(json.dumps({'status':result['status'],'issues':issues,'cases':[{k:r[k]for k in['case','accepted','merged_manifest_pin_mismatches']}for r in results]}))

if __name__=='__main__':main()
