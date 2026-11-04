"""Freeze explicit new data/evidence files and encrypt delta07; never trains."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,re,shutil,tarfile
ROOT=Path(__file__).resolve().parents[3];DATA=ROOT/'output/20261027_wrd_main_v10'
WORK=ROOT/'output/20261029_wrd_delivery07';EVIDENCE=ROOT/'output/20261029_wrd_batch24'
RELEASE=ROOT/'output/20261025_wrd_training_dataset/git_release'
DEST=RELEASE/'dataset/20261030_v10_checkpoint07';BASE=ROOT/'output/wrd06root'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def module(n,p):
    s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
    assert not DEST.exists();assert load(WORK/'MAIN552_QA.json')['status']=='PASS'
    assert load(EVIDENCE/'ROOT_SCOPE_AND_FILE_QA.json')['status']=='PASS_FIXED100_SCOPE_AND_ACTUAL_RECOVERED_FILES_RECOUNT'
    assert load(EVIDENCE/'merge_peer/PEER.json')['status'].startswith('PASS')
    stage=WORK/'delta_build03';stage.mkdir(exist_ok=False)
    helper=module('delta07_guard',ROOT/'research/data_prep/wrd_main_v10/package_checkpoint05.py')
    needles=helper.credential_needles();entries={};aliases=[]
    def add(name,p):
        p=helper.source_guard(p);assert p.is_file();b=p.read_bytes()
        expanded=gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b
        assert not any(k in b or k in expanded for k in needles),'known credential in '+name
        assert not re.search(rb'\bsk-[A-Za-z0-9_-]{24,}\b',expanded),'key-shaped value in '+name
        assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\r\n]+[A-Za-z0-9+/]{16}',expanded)
        assert name not in entries
        entries[name]={'path':name,'source':str(p.resolve()),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
        aliases.append({'original_absolute_path':str(p.resolve()),'archive_path':name,'sha256':entries[name]['sha256']})
    def tree(name,p,skip_first=()):
        for q in sorted(Path(p).rglob('*')):
            if q.relative_to(p).parts[0] in skip_first:continue
            if q.is_file() and q.suffix!='.pyc' and '__pycache__' not in q.parts:add(name+'/'+q.relative_to(p).as_posix(),q)
    for n in ['TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json']:add(n,DATA/n)
    for n in ['source_only_controller_batch24','local_exploration_pre_protection_batch24']:tree('compiled/'+n,DATA/'compiled'/n)
    tree('evidence07/batch24',EVIDENCE,skip_first=('canonical_arrays07',))
    tree('canonical_arrays07',EVIDENCE/'canonical_arrays07')
    tree('design_reference/next_data_plan',ROOT/'research/plans/20261029_wrd_next_data')
    tree('design_reference/history5.0.45',ROOT/'research/designs/history/5.0.45/batch07_20261029')
    for n in ['A_B_MODULES.md','PIPELINE.md']:add('design_reference/'+n,ROOT/'research/designs'/n)
    for n in ['MAIN552_QA.json','FULL226_MAIN_SOURCE_QA.json','OPTIONAL_ARRAY_REFERENCE_AUDIT.json','CURRENT_DATA_AND_EXPOSURE.json','OWNER_EXPOSURE_SCHEDULE.json']:add('quality07/'+n,WORK/n)
    for n in ['package_delta07.py','merge_delta07.py','verify_main05.py','verify_remote05.py']:add('source_tooling/'+n,ROOT/'research/data_prep/wrd_main_v10'/n)
    save(stage/'EVIDENCE_PATH_ALIASES07.json',{'aliases':aliases,'old_version_or_audit_records_never_glob_as_training':True})
    add('EVIDENCE_PATH_ALIASES07.json',stage/'EVIDENCE_PATH_ALIASES07.json')
    refs=list(entries.values());m=load(DATA/'TRAINING_MANIFEST.json')
    pm={'schema':'wrd-exact-merged06-authenticated-delta07','base_payload_manifest_sha256':sha(BASE/'PAYLOAD_MANIFEST.json'),
        'base_training_manifest_sha256':sha(BASE/'TRAINING_MANIFEST.json'),'base_checkpoint_required':'05_plus_06_merged_root',
        'files':refs,'actual_targets':m['actual_counts']['targets'],'actual_supervised_tokens':m['actual_counts']['supervised_tokens'],
        'new_targets':22,'new_source_only_decision_targets':19,'new_pre_receipt_local_action_projections':3,
        'new_original_R_positive_tokens':0,'new_complete_resource_or_repair_gold_targets':0,
        'training_started':False,'full_WRD_main_training_ready':False}
    save(stage/'PAYLOAD_MANIFEST.json',pm)
    plain=stage/'wrd-v10-delta07.tar.gz'
    with tarfile.open(plain,'w:gz',compresslevel=3,format=tarfile.PAX_FORMAT) as tf:
        tf.add(stage/'PAYLOAD_MANIFEST.json',arcname='PAYLOAD_MANIFEST.json',recursive=False)
        for ref in refs:
            p=Path(ref['source']);assert p.stat().st_size==ref['bytes'] and sha(p)==ref['sha256']
            tf.add(p,arcname=ref['path'],recursive=False)
            assert sha(p)==ref['sha256'],'source changed during package'
    DEST.mkdir(parents=True);(DEST/'controlled').mkdir();(DEST/'tooling').mkdir()
    enc=module('delta07_encryption',ROOT/'research/data_prep/wrd_reasoning_v4/encrypted_delivery.py')
    receipt=enc.encrypt(plain,DEST/'controlled/wrd-v10-delta07.tar.gz.aesgcm',ROOT/'output/20261025_wrd_reasoning_recovery_v4/local_delivery_key/wrd-reasoning-v4.key',reuse_key=True)
    receipt.update(payload_manifest_sha256=sha(stage/'PAYLOAD_MANIFEST.json'),authenticated_files=len(refs)+1,base_checkpoint_required='05_plus_06_merged_root',training_started=False)
    save(DEST/'ENCRYPTED_DELIVERY_REPORT.json',receipt)
    for n,p in [('restore_checkpoint.py',RELEASE/'dataset/20261029_v10_checkpoint05/tooling/restore_checkpoint.py'),('checkpoint_loader.py',ROOT/'research/data_prep/wrd_main_v10/verify_main05.py'),('merge_delta.py',ROOT/'research/data_prep/wrd_main_v10/merge_delta07.py')]:shutil.copyfile(p,DEST/'tooling'/n)
    for n,p in [('TRAINING_MANIFEST.json',DATA/'TRAINING_MANIFEST.json'),('ACTUAL_DATA_STATISTICS.json',DATA/'ACTUAL_DATA_STATISTICS.json'),('TRAINING_PLAN.md',ROOT/'research/plans/20261029_wrd_next_data/TRAINING_PLAN_07.md'),('ROOT_SCOPE_AND_FILE_QA.json',EVIDENCE/'ROOT_SCOPE_AND_FILE_QA.json'),('MAIN552_QA.json',WORK/'MAIN552_QA.json'),('FULL226_MAIN_SOURCE_QA.json',WORK/'FULL226_MAIN_SOURCE_QA.json'),('CURRENT_DATA_AND_EXPOSURE.json',WORK/'CURRENT_DATA_AND_EXPOSURE.json'),('MERGER_INDEPENDENT_PEER.json',EVIDENCE/'merge_peer/PEER.json')]:shutil.copyfile(p,DEST/n)
    save(WORK/'BUILD_RECEIPT.json',{'status':'BUILT_AUTHENTICATED_DELTA_PENDING_REAL_MERGE_AND_REMOTE_VERIFICATION','authenticated_members':len(refs)+1,'ciphertext_bytes':receipt['ciphertext_bytes'],'ciphertext_sha256':receipt['ciphertext_sha256'],'known_credential_scan':'PASS_RAW_AND_GZIP_EXPANDED_ALL_FILES','pyc_excluded':True,'training_started':False})
    print(json.dumps(load(WORK/'BUILD_RECEIPT.json')))
if __name__=='__main__':main()
