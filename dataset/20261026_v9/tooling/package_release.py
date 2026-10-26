"""Package actual v9 data with a strict active allowlist and complete evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tarfile

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261026_wrd_dataset_v9'
RELEASE=ROOT/'output/20261025_wrd_training_dataset/git_release'
DEST=RELEASE/'dataset/20261026_v9'


def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    assert read(OUT/'COMPILED_QA.json')['status']=='PASS'
    plan_review=read(OUT/'PLAN_REVIEW.json')
    assert plan_review['status']=='PASS_WITH_FULL_GOAL_MAIN_TRAINING_BLOCKED'
    assert all(r['status']=='PASS'for r in plan_review['checks'])
    assert plan_review['static_guard_review']['current_guard_matches_final_receipt']is True
    for row in plan_review['reviewed_final_artifact_pins']+plan_review['verified_SFT_files']+plan_review['verified_immutable_source_inputs']:
        p=Path(row['path']);p=p if p.is_absolute()else OUT/p
        assert p.stat().st_size==row['bytes']and digest(p)==row['sha256']
    manifest=read(OUT/'TRAINING_MANIFEST.json');assert manifest['full_goal_main_training_ready']is False and manifest['training_started']is False
    for row in manifest['actual_files_with_messages_input_ids_masks']:assert digest(OUT/row['path'])==row['sha256']
    reuse=read(OUT/'EXISTING_RESOURCE_REUSE.json');assert reuse['status']=='PASS'and reuse['all_materials_already_in_existing_git']
    DEST.mkdir(parents=True,exist_ok=False)
    for name in ('TRAINING_PLAN.md','TRAINING_PLAN.json','TRAINING_MANIFEST.json','FINAL_DATA_STATISTICS.json','COMPILATION_REPORT.json','COMPILED_QA.json','SOURCE_GROUP_SPLIT.json','CLEAN_RECOLLECTION_PLAN.json','PLAN_REVIEW.json','TARGET_QUALITY_ERRATA.json','FAILED_READ_ERRATUM_INDEPENDENT_QA.json'):
        shutil.copyfile(OUT/name,DEST/name)
    tooling=DEST/'tooling';tooling.mkdir()
    for p in sorted(Path(__file__).parent.glob('*.py')):shutil.copyfile(p,tooling/p.name)
    shutil.copyfile(ROOT/'research/data_prep/wrd_reasoning_v4/encrypted_delivery.py',tooling/'shared_encryption_v4.py')
    shutil.copyfile(ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py',tooling/'shared_causal_compiler_v4.py')
    shutil.copyfile(ROOT/'research/data_prep/wrd_raw_census_v7/verify_remote_index.py',tooling/'shared_remote_verify_v7.py')
    design=DEST/'design_reference';design.mkdir()
    for name in ('A_B_MODULES.md','PIPELINE.md'):shutil.copyfile(ROOT/'research/designs'/name,design/name)
    # Real data including held originals stay in an authenticated, usable
    # archive; no credentials/private keys or personal raw records go to public text.
    members={}
    for folder in ('recovery','outcomes','coordination','processed','sft','processing_history','frozen_rule_sources'):
        for p in sorted((OUT/folder).rglob('*')):
            if p.is_file()and p.suffix!='.pyc':members[p.relative_to(OUT).as_posix()]=p
    for p in sorted((OUT/'replay_inputs/conversations').glob('*.json')):members[p.relative_to(OUT).as_posix()]=p
    for p in sorted(OUT.glob('*.json')):
        if p.name not in {'ENCRYPTED_DELIVERY_REPORT.json','PACKAGING_RECEIPT.json','REMOTE_GIT_VERIFICATION.json'}:members[p.name]=p
    members['TRAINING_PLAN.md']=OUT/'TRAINING_PLAN.md'
    for row in reuse['delta_objects_require_new_authenticated_archive']:
        p=Path(row['source_path']);assert p.stat().st_size==row['bytes']and digest(p)==row['sha256']
        members['source_objects_delta/'+row['sha256']]=p
    codex=Path('C:/Users/22142/.codex/sessions/2026/10/23/rollout-2026-10-23T01-11-23-01a16469-7614-7e01-ba76-1ad2d9707177_01a16498-9504-7342-80c4-b714199ce710.jsonl')
    assert digest(codex)=='607e02c2943822e4beca1ac199bc5abd5c237066a798cc3dac72515dd4f8fee2'
    members['historical_external_Codex/not_native_WRD/'+codex.name]=codex
    for name,p in members.items():assert not p.is_symlink()and p.suffix.lower()not in{'.key','.pem','.pfx','.p12'}
    internal={'schema_version':'wrd-v9-actual-data-and-evidence-payload','training_manifest':'TRAINING_MANIFEST.json','training_started':False,
        'original226_and_new_H_held_not_training':True,'held_data_not_implicitly_admitted':True,'private_key_included':False,
        'files':[{'path':name,'bytes':p.stat().st_size,'sha256':digest(p)}for name,p in sorted(members.items())]}
    encdir=OUT/'encrypted_delivery';encdir.mkdir(exist_ok=False);private_manifest=encdir/'PAYLOAD_MANIFEST.json';save(private_manifest,internal)
    plain=encdir/'wrd-causal-dataset-v9.tar.gz'
    with tarfile.open(plain,'w:gz',compresslevel=3,format=tarfile.PAX_FORMAT)as tf:
        for name,p in sorted(members.items()):tf.add(p,arcname=name,recursive=False)
        tf.add(private_manifest,arcname='PAYLOAD_MANIFEST.json',recursive=False)
    expected={r['path']:r for r in internal['files']};checked=set()
    with tarfile.open(plain,'r|gz')as tf:
        for member in tf:
            assert member.isfile()
            if member.name=='PAYLOAD_MANIFEST.json':
                assert tf.extractfile(member).read()==private_manifest.read_bytes();continue
            row=expected[member.name];h=hashlib.sha256()
            with tf.extractfile(member)as source:
                for block in iter(lambda:source.read(1048576),b''):h.update(block)
            assert member.size==row['bytes']and h.hexdigest()==row['sha256'];checked.add(member.name)
    assert checked==set(expected)
    spec=importlib.util.spec_from_file_location('wrd_v9_crypto',ROOT/'research/data_prep/wrd_reasoning_v4/encrypted_delivery.py');crypto=importlib.util.module_from_spec(spec);spec.loader.exec_module(crypto)
    key=ROOT/'output/20261025_wrd_reasoning_recovery_v4/local_delivery_key/wrd-reasoning-v4.key'
    cipher=encdir/'wrd-causal-dataset-v9.tar.gz.aesgcm';receipt=crypto.encrypt(plain,cipher,key,reuse_key=True)
    receipt.update(schema_version='wrd-v9-authenticated-data-delivery',files=len(members)+1,plaintext_bytes=plain.stat().st_size,training_started=False,
        every_archive_member_size_and_hash_independently_read_back=True,
        key_path_local_only=str(key),archive_active_manifest='TRAINING_MANIFEST.json',archive_is_not_full_goal_training_readiness=True)
    save(OUT/'ENCRYPTED_DELIVERY_REPORT.json',receipt)
    public_receipt={k:v for k,v in receipt.items()if k!='key_path_local_only'};save(DEST/'ENCRYPTED_DELIVERY_REPORT.json',public_receipt)
    private=DEST/'controlled';private.mkdir();shutil.copyfile(cipher,private/cipher.name)
    shutil.copyfile(ROOT/'research/memory/2026-10-26_wrd_dataset_v9.md',DEST/'RESEARCH_MEMORY.md')
    (DEST/'README.md').write_text('''# WRD真实训练数据处理v9

[实际处理与训练计划](TRAINING_PLAN.md) · [实际数据量](FINAL_DATA_STATISTICS.json) · [训练文件清单](TRAINING_MANIFEST.json) · [独立数组QA](COMPILED_QA.json)

本次有实际正文、input_ids、loss spans和loader，不是候选清单。完整WRD制作/修订主监督仍被来源/结果标准阻塞；当前放行的是只读工具辅助和明确新增的协调标注，不能用总行数冒充完整自主任务。原226及新H继续隔离，未训练。

`controlled/wrd-causal-dataset-v9.tar.gz.aesgcm`包含全部恢复正文、原可读字段、工具/反馈/修订、版本-试跑-评审图、原件增量、实际SFT数组与分组；母本还包含隔离/未知资料，训练必须仅按TRAINING_MANIFEST加载sft文件。这里没有丢弃中间过程，也没有把它们全设为正loss。

沿用用户本地v4密钥（不在Git）。使用 `python tooling/restore_payload.py --cipher controlled/wrd-causal-dataset-v9.tar.gz.aesgcm --receipt ENCRYPTED_DELIVERY_REPORT.json --key <本地wrd-reasoning-v4.key> --out <新目录>` 认证解包。它只恢复文件，不执行训练或原保存代码。解包后以tooling/dataset_loader.py按显式span重建labels和weights。

867份原输入会话和112个真实附件绑定已准备；93个不同附件对象已在原仓库dist的12分片逐字节核验，按包内EXISTING_RESOURCE_REUSE引用。需要恢复真实附件时加 `--existing-release-root <仓库根>`；这样无需重复上传同字节418MB。原文/个人资料/可能含凭据的历史记录保持认证加密，密钥留本地。

源代码规则的LF文本hash与原CRLF字节hash分开记录，完整规则源码随包保留。协调规则trace是明确假设状态，不是实际工具反馈/试跑或原教师CoT；不替代原生Agent执行循环。旧v6原R与数组保持历史不同执行条件的引用，不自动混入当前主集。
''',encoding='utf-8')
    payload=[]
    for p in sorted(DEST.rglob('*')):
        if p.is_file():payload.append({'path':p.relative_to(DEST).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)})
    outer={'schema_version':'wrd-v9-public-delivery-manifest','payload_files':len(payload),'payload_bytes':sum(r['bytes']for r in payload),
        'training_started':False,'original226_training_boundary_unchanged':True,'actual_data_enclosed_authenticated':True,
        'full_goal_main_training_ready':False,'old_training_payloads_changed':False,'files':payload}
    save(DEST/'MANIFEST.json',outer);save(OUT/'PACKAGING_RECEIPT.json',{'destination':str(DEST),'payload_files':len(payload),'payload_bytes':outer['payload_bytes'],'manifest_sha256':digest(DEST/'MANIFEST.json'),'encrypted_payload_authenticated':True})
    print(json.dumps({'payload_files':len(payload),'payload_bytes':outer['payload_bytes'],'inner_files':len(members)+1,'cipher_bytes':cipher.stat().st_size,'training_started':False}))


if __name__=='__main__':main()
