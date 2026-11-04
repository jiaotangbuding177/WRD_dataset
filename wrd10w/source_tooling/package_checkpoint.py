"""Build an authenticated intermediate v10 checkpoint, never train or push.

Only explicit allowlists are used.  Protected runtime directories and keys are
never archived.  gzip/tar, AES-GCM, credential scans and restoration use bounded
1 MiB streams.  No HF, torch, model or Agent runtime is loaded.
"""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile
import time

sys.dont_write_bytecode=True

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261027_wrd_main_v10'
RELEASE=ROOT/'output/20261025_wrd_training_dataset/git_release'
DEST=RELEASE/'dataset/20261027_v10_checkpoint01'
KEY=ROOT/'output/20261025_wrd_reasoning_recovery_v4/local_delivery_key/wrd-reasoning-v4.key'
BLOCK=1048576
FORBIDDEN={'.claude','.codex','private','private_credential_audit','credential_audit','reparse','__pycache__','.git'}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for b in iter(lambda:f.read(BLOCK),b''):h.update(b)
    return h.hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pin(path):
    path=Path(path).resolve()
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':digest(path)}
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
def safe_name(name):
    p=PurePosixPath(name)
    if p.is_absolute()or'..'in p.parts or'\\'in name or any(x.lower()in FORBIDDEN for x in p.parts):raise ValueError('archive_path_not_allowed')
    if p.suffix.lower()in {'.key','.pem','.pfx','.p12','.pyc'}:raise ValueError('private_or_generated_file_not_allowed')
    return p


RESTORE = r'''"""Authenticate and restore the v10 checkpoint; no saved code is executed."""
import argparse, hashlib, io, json, shutil, tarfile
from pathlib import Path, PurePosixPath
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
MAGIC=b'WRDENC4\x00'; BLOCK=1048576
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(BLOCK),b''):h.update(b)
 return h.hexdigest()
def target(root,name):
 p=PurePosixPath(name)
 if p.is_absolute()or'..'in p.parts or'\\'in name:raise ValueError('unsafe_archive_path')
 out=root.joinpath(*p.parts)
 if not out.resolve().is_relative_to(root.resolve()):raise ValueError('path_escape')
 return out
def decrypt(cipher,key_path,out):
 key=key_path.read_bytes()
 if len(key)!=32:raise ValueError('key_must_be_32_bytes')
 size=cipher.stat().st_size; temp=out.with_suffix(out.suffix+'.unverified');h=hashlib.sha256()
 with cipher.open('rb')as f,temp.open('xb')as g:
  if f.read(len(MAGIC))!=MAGIC:raise ValueError('wrong_encryption_format')
  nonce=f.read(12);f.seek(size-16);tag=f.read(16);f.seek(len(MAGIC)+12)
  dec=Cipher(algorithms.AES(key),modes.GCM(nonce,tag)).decryptor();dec.authenticate_additional_data(MAGIC)
  remaining=size-len(MAGIC)-12-16
  while remaining:
   b=f.read(min(BLOCK,remaining))
   if not b:raise ValueError('truncated_ciphertext')
   remaining-=len(b);plain=dec.update(b);g.write(plain);h.update(plain)
  final=dec.finalize();g.write(final);h.update(final)
 temp.replace(out);return h.hexdigest()
class Parts(io.RawIOBase):
 def __init__(self,paths):self.paths=iter(paths);self.handle=None
 def readable(self):return True
 def readinto(self,b):
  while True:
   if self.handle is None:
    p=next(self.paths,None)
    if p is None:return 0
    self.handle=Path(p).open('rb')
   n=self.handle.readinto(b)
   if n:return n
   self.handle.close();self.handle=None
 def close(self):
  if self.handle:self.handle.close()
  super().close()
def restore_existing(out,release):
 reuse=json.loads((out/'EXISTING_SOURCE_REUSE.json').read_text(encoding='utf-8'))
 wanted={row['existing_archive_member']:row for row in reuse['verified_objects']};parts=[]
 for row in reuse['existing_parts']:
  p=target(release,row['path'])
  if p.stat().st_size!=row['bytes']or digest(p)!=row['sha256']:raise ValueError('existing_part_pin_mismatch')
  parts.append(p)
 dest=out/'existing_source_objects';dest.mkdir(exist_ok=False);found=set()
 with io.BufferedReader(Parts(parts),buffer_size=BLOCK)as stream:
  with tarfile.open(fileobj=stream,mode='r|gz')as tf:
   for member in tf:
    if not member.isfile()or member.name not in wanted:continue
    row=wanted[member.name];p=dest/row['sha256'];h=hashlib.sha256()
    with tf.extractfile(member)as f,p.open('xb')as g:
     for b in iter(lambda:f.read(BLOCK),b''):g.write(b);h.update(b)
    if member.size!=row['bytes']or h.hexdigest()!=row['sha256']:raise ValueError('existing_object_pin_mismatch')
    found.add(member.name)
    if len(found)==len(wanted):break
 if found!=set(wanted):raise ValueError('existing_objects_missing')
 return {'objects':len(found),'bytes':sum(wanted[x]['bytes']for x in found)}
def restore(cipher,receipt_path,key,out,release=None):
 receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
 if digest(cipher)!=receipt['ciphertext_sha256']:raise ValueError('cipher_pin_mismatch')
 out.mkdir(parents=True,exist_ok=False);plain=out/'payload.verified.tar.gz'
 if decrypt(cipher,key,plain)!=receipt['plaintext_sha256']:raise ValueError('plain_pin_mismatch')
 found=set()
 with tarfile.open(plain,'r|gz')as tf:
  first=tf.next()
  if not first or first.name!='PAYLOAD_MANIFEST.json'or not first.isfile():raise ValueError('manifest_must_be_first')
  raw=tf.extractfile(first).read()
  if hashlib.sha256(raw).hexdigest()!=receipt['payload_manifest_sha256']:raise ValueError('payload_manifest_pin_mismatch')
  manifest=json.loads(raw);expected={row['path']:row for row in manifest['files']}
  (out/'PAYLOAD_MANIFEST.json').write_bytes(raw)
  while True:
   member=tf.next()
   if member is None:break
   if not member.isfile()or member.name not in expected or member.name in found:raise ValueError('unexpected_or_duplicate_member')
   p=target(out,member.name);p.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256()
   with tf.extractfile(member)as f,p.open('xb')as g:
    for b in iter(lambda:f.read(BLOCK),b''):g.write(b);h.update(b)
   row=expected[member.name]
   if member.size!=row['bytes']or h.hexdigest()!=row['sha256']:raise ValueError('member_pin_mismatch')
   found.add(member.name)
 if found!=set(expected):raise ValueError('missing_member')
 old=restore_existing(out,release)if release else None
 return {'status':'PASS','authenticated_files':len(found)+1,'existing_objects_restored':old,'training_started':False,'full_WRD_main_training_ready':False}
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['cipher','receipt','key','out']:p.add_argument('--'+name,required=True,type=Path)
 p.add_argument('--existing-release-root',type=Path);args=p.parse_args()
 print(json.dumps(restore(args.cipher,args.receipt,args.key,args.out,args.existing_release_root)))
if __name__=='__main__':main()
'''


LOADER = r'''"""Load only checkpoint active arrays. No model, optimizer or training runner."""
from array import array
from collections import Counter
import argparse,gzip,hashlib,json,sys
from pathlib import Path,PurePosixPath
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def js(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))
def active_paths(root):
 manifest=json.loads((root/'TRAINING_MANIFEST.json').read_text(encoding='utf-8'))
 if manifest['full_WRD_main_training_ready']is not False or manifest['training_started']is not False:raise ValueError('wrong_checkpoint_contract')
 for row in manifest['actual_train_files']:
  p=PurePosixPath(row['path'])
  if p.is_absolute()or'..'in p.parts or'\\'in row['path']:raise ValueError('unsafe_training_path')
  path=root.joinpath(*p.parts)
  if path.stat().st_size!=row['bytes']or digest(path)!=row['sha256']:raise ValueError('active_array_pin_mismatch')
  yield path
def iter_features(root):
 for path in active_paths(Path(root)):
  with gzip.open(path,'rt',encoding='utf-8')as f:
   for line in f:
    if not line.strip():continue
    row=json.loads(line);ids=row['input_ids'];labels=[-100]*len(ids);weights=[0.0]*len(ids);last=0
    for lo,hi,component,weight in row['supervision_spans']:
     if not 0<=last<=lo<hi<=len(ids)or not 0<weight<=1:raise ValueError('invalid_mask_span')
     labels[lo:hi]=ids[lo:hi];weights[lo:hi]=[float(weight)]*(hi-lo);last=hi
    if sum(x!=-100 for x in labels)!=row['supervised_tokens']or len(ids)>32768:raise ValueError('mask_or_length_mismatch')
    yield {'input_ids':ids,'attention_mask':[1]*len(ids),'labels':labels,'loss_weights':weights}
def verify(root):
 root=Path(root);manifest=json.loads((root/'TRAINING_MANIFEST.json').read_text(encoding='utf-8'));counts=Counter();seen=set();samples=[]
 for path in active_paths(root):
  with gzip.open(path,'rt',encoding='utf-8')as f:
   for line in f:
    if not line.strip():continue
    row=json.loads(line);ids=row['input_ids'];data=array('I',ids)
    if sys.byteorder!='little':data.byteswap()
    if row['id']in seen:raise ValueError('duplicate_active_owner')
    seen.add(row['id'])
    if hashlib.sha256(data.tobytes()).hexdigest()!=row['input_ids_sha256_u32le']:raise ValueError('ids_hash_mismatch')
    if hashlib.sha256(js(row['supervision_spans']).encode()).hexdigest()!=row['supervision_spans_sha256']:raise ValueError('mask_hash_mismatch')
    spans=[]
    for target in row['targets']:spans.extend(target['owned_supervision_spans'])
    if spans!=row['supervision_spans']:raise ValueError('owner_global_mask_mismatch')
    counts['sequences']+=1;counts['input_tokens']+=len(ids);counts['supervised_tokens']+=row['supervised_tokens']
    for component,value in row['supervised_tokens_by_component'].items():counts['component_'+component]+=value
    counts['le16k_sequences']+=len(ids)<=16384;counts['le32k_sequences']+=len(ids)<=32768
 for feature in iter_features(root):
  n=sum(value!=-100 for value in feature['labels']);counts['loader_supervised_tokens']+=n;counts['loader_sequences']+=1
  if any((label==-100)!=(weight==0)for label,weight in zip(feature['labels'],feature['loss_weights'])):raise ValueError('labels_weights_disagree')
  if len(samples)<2:samples.append(feature)
 for key in ('sequences','input_tokens','supervised_tokens','le16k_sequences','le32k_sequences','component_F','component_D','component_R'):
  if counts[key]!=manifest['actual_counts'][key]:raise ValueError('manifest_counter_mismatch_'+key)
 if counts['loader_supervised_tokens']!=counts['supervised_tokens']or counts['loader_sequences']!=counts['sequences']:raise ValueError('loader_counter_mismatch')
 if len(samples)==2:
  maximum=max(len(x['input_ids'])for x in samples)
  for sample in samples:
   n=maximum-len(sample['input_ids']);labels=sample['labels']+[-100]*n;weights=sample['loss_weights']+[0.0]*n
   if any(x!=-100 for x in labels[len(sample['input_ids']):])or any(weights[len(sample['input_ids']):]):raise ValueError('pad_has_loss')
 return {'status':'PASS','counts':dict(counts),'only_manifest_active_arrays_loaded':True,'old_431_645_and_v9_not_loaded':True,'weights_loaded':False,'training_started':False,'full_WRD_main_training_ready':False}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);args=p.parse_args();print(json.dumps(verify(args.root)))
if __name__=='__main__':main()
'''


def scan_stream(stream,patterns):
    carry=b'';keep=max(len(x)for x in patterns)-1
    for block in iter(lambda:stream.read(BLOCK),b''):
        value=carry+block
        if any(pattern in value for pattern in patterns):return False
        carry=value[-keep:]if keep else b''
    return True


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',action='store_true');args=parser.parse_args()
    if not args.build:parser.error('use --build; this does not train, commit or push')
    if DEST.exists():raise ValueError('checkpoint_destination_already_exists')
    if not DEST.resolve().is_relative_to((RELEASE/'dataset').resolve()):raise ValueError('destination_outside_named_dataset_root')
    active=load(OUT/'TRAINING_MANIFEST.json')
    assert active['full_WRD_main_training_ready']is False and active['training_started']is False
    assert active['actual_counts']['sequences']==437 and active['actual_counts']['supervised_tokens']==75248 and active['actual_counts']['component_R']==490
    assert {str(PurePosixPath(row['path']).parent)for row in active['actual_train_files']}=={'compiled/source_events_02','compiled/native_A_partial_02'}
    reuse=load(OUT/'EXISTING_SOURCE_REUSE.json');assert reuse['status']=='PASS'and len(reuse['verified_objects'])==750 and reuse['verified_bytes']==117118540
    work=OUT/'checkpoint_build_01'/('attempt_'+str(time.time_ns()));work.mkdir(parents=True,exist_ok=False)
    stage=work/'public';stage.mkdir();members={}
    def add(name,path):
        safe_name(name);path=Path(path).resolve()
        if path.is_symlink()or not path.is_file()or any(x.lower()in FORBIDDEN for x in path.parts):raise ValueError('source_is_not_an_allowed_regular_file')
        if name in members and members[name]!=path:raise ValueError('duplicate_archive_name')
        members[name]=path
    def folder(rel,archive_prefix=None):
        base=OUT/rel
        if not base.is_dir():raise ValueError('explicit_allowlisted_directory_missing')
        for path in sorted(base.rglob('*')):
            if path.is_dir():continue
            add((archive_prefix or rel)+'/'+path.relative_to(base).as_posix(),path)
    for rel in ['clean_inputs/source_event_release_02','clean_inputs/publishable_original_recovery_01','compiled/source_events_02','compiled/native_A_partial_02','prepare_ancestry_audit']:
        folder(rel)
    add('clean_inputs/source_event_release_02_METADATA_ERRATA.json',OUT/'clean_inputs/source_event_release_02_METADATA_ERRATA.json')
    folder('native_records/A_screen_narrative_01','audit_only/native_records/A_screen_narrative_01')
    episode=OUT/'runtime_preflight/episodes/A_screen_narrative_01'
    for name in ['CAPTURE_ASSESSMENT.json','dispatch.json','execution.json','job.json','native_events.jsonl','outer_recording_receipt.json','process.json','request.json','response.json','result.json','stderr.log','stdout.log','STUDENT_NATIVE_PREFIX_LENGTH.json','usage.json']:
        add('original_native_A/'+name,episode/name)
    for path in sorted((episode/'api_audit').glob('*/*')):
        if path.is_file()and path.name in {'receipt.json','request.raw.json','response.inspection.json','response.raw.sse'}:
            add('original_native_A/api_audit/'+path.relative_to(episode/'api_audit').as_posix(),path)
    add('original_native_A/api_audit/audit_manifest.jsonl',episode/'api_audit/audit_manifest.jsonl')
    transport_names=['all_session_events.jsonl','config-validation.log','container_receipt.json','episode_turns.json','export.stderr.log','export.stdout.log','gateway.health.log','gateway.stderr.log','gateway.stdout.log','host_receipt.json','native_result.json','request.json','response.json','runtime_observation.json','sessions.stderr.log','sessions.stdout.log','session_events.jsonl','skill_reads.json','stderr.log','stdout.log','turn_0001.native_result.json','turn_0001.stderr.log','turn_0001.stdout.log']
    for name in transport_names:add('original_native_A/openclaw_transport/'+name,episode/'openclaw_transport'/name)
    for path in sorted((episode/'workspace/outputs').rglob('*')):
        if path.is_file():add('original_native_A/outputs/'+path.relative_to(episode/'workspace/outputs').as_posix(),path)
    job=load(episode/'job.json')
    for item in job['resources']:
        path=Path(item['path']);assert digest(path)==item['sha256']
        add('actual_source_inputs/'+PurePosixPath(item['mount']).as_posix(),path)
    for field in ['source_allowlist_receipt','resource_ancestry_receipt']:
        ref=job.get(field)
        path=Path(ref['path']if isinstance(ref,dict)else ref)
        add('native_ancestry/'+path.name,path)
    for name in ['TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json','EXISTING_SOURCE_REUSE.json']:add(name,OUT/name)
    for path in sorted(Path(__file__).parent.glob('*.py')):add('source_tooling/'+path.name,path)
    add('source_tooling/shared_causal_compiler_v4.py',ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py')
    for name in ['TRAINING_PLAN.md','PLAN.md','STRATEGY_REVIEW.md']:add('design_reference/'+name,ROOT/'research/plans/20261027_wrd_main_v10'/name)
    for name in ['A_B_MODULES.md','PIPELINE.md']:add('design_reference/'+name,ROOT/'research/designs'/name)
    audit_only={'status':'AUDIT_ONLY_NEVER_TRAIN_BY_GLOB','active_manifest':'TRAINING_MANIFEST.json',
        'audit_only_roots':['audit_only','prepare_ancestry_audit','original_native_A'],
        'superseded_banks':['compiled/source_events_01','compiled/native_A_partial_01','clean_inputs/source_event_release_01'],
        'old_source_events_01_and_authorization_code_release01_not_archived':True,
        'v9_native_auxiliary_not_in_this_checkpoint':True,'B_authorized_but_resources_not_dispatched':True,
        'full_WRD_main_training_ready':False,'training_started':False}
    save(work/'AUDIT_ONLY_BANKS.json',audit_only);add('AUDIT_ONLY_BANKS.json',work/'AUDIT_ONLY_BANKS.json')
    aliases={str(path):name for name,path in sorted(members.items())}
    save(work/'EVIDENCE_PATH_ALIASES.json',{'original_absolute_path_to_archive_path':aliases,'original_files_not_rewritten':True})
    add('EVIDENCE_PATH_ALIASES.json',work/'EVIDENCE_PATH_ALIASES.json')
    # Load exactly the two configured model keys only in memory.  Never log,
    # serialize, hash into reports, or archive the configuration files or key.
    credentials=[OUT/'runtime_preflight/private/model_consumer.json',OUT/'runtime_preflight/private/model_upstream.json']
    secrets=[load(path)['api_key']for path in credentials]
    assert all(isinstance(value,str)and value for value in secrets)
    patterns={value.encode('utf-8')for value in secrets}
    patterns.update(json.dumps(value,ensure_ascii=False)[1:-1].encode()for value in secrets)
    patterns.add(KEY.read_bytes());assert len(KEY.read_bytes())==32
    scanned=0
    for name,path in sorted(members.items()):
        with path.open('rb')as f:
            if not scan_stream(f,patterns):raise ValueError('credential_bytes_in_allowlisted_member_packaging_stopped')
        if path.suffix=='.gz':
            with gzip.open(path,'rb')as f:
                if not scan_stream(f,patterns):raise ValueError('credential_bytes_in_decompressed_member_packaging_stopped')
        scanned+=1
    files=[{'path':name,'bytes':path.stat().st_size,'sha256':digest(path),'original_path':str(path)}for name,path in sorted(members.items())]
    inner={'schema_version':'wrd-v10-authenticated-checkpoint01-payload','status':'INTERMEDIATE_NOT_FINAL_FULL_WRD_NOT_READY',
        'active_manifest':'TRAINING_MANIFEST.json','full_WRD_main_training_ready':False,'training_started':False,
        'default_full_pipeline_training_entrypoint':None,'B_authorized_but_resources_not_dispatched':True,
        'original226_newH_static_dev_test_boundary_unchanged':True,'files':files}
    inner_path=work/'PAYLOAD_MANIFEST.json';save(inner_path,inner)
    plain=work/'wrd-v10-checkpoint01.tar.gz'
    with tarfile.open(plain,'w:gz',compresslevel=3,format=tarfile.PAX_FORMAT)as tf:
        tf.add(inner_path,arcname='PAYLOAD_MANIFEST.json',recursive=False)
        for name,path in sorted(members.items()):tf.add(path,arcname=name,recursive=False)
    expected={r['path']:r for r in files};seen=set()
    with tarfile.open(plain,'r|gz')as tf:
        for member in tf:
            if not member.isfile():raise ValueError('archive_nonregular_member')
            if member.name=='PAYLOAD_MANIFEST.json':assert tf.extractfile(member).read()==inner_path.read_bytes();continue
            row=expected[member.name];h=hashlib.sha256()
            with tf.extractfile(member)as source:
                for b in iter(lambda:source.read(BLOCK),b''):h.update(b)
            assert member.size==row['bytes']and h.hexdigest()==row['sha256'];seen.add(member.name)
    assert seen==set(expected)
    crypto=module(ROOT/'research/data_prep/wrd_reasoning_v4/encrypted_delivery.py','checkpoint_crypto_v4')
    controlled=stage/'controlled';controlled.mkdir();cipher=controlled/'wrd-v10-checkpoint01.tar.gz.aesgcm'
    receipt=crypto.encrypt(plain,cipher,KEY,reuse_key=True)
    receipt.update(schema_version='wrd-v10-checkpoint01-encryption-receipt',payload_manifest_sha256=digest(inner_path),
        plaintext_bytes=plain.stat().st_size,authenticated_files=len(files)+1,full_WRD_main_training_ready=False,training_started=False)
    save(stage/'ENCRYPTED_DELIVERY_REPORT.json',receipt)
    tools=stage/'tooling';tools.mkdir();(tools/'restore_checkpoint.py').write_text(RESTORE,encoding='utf-8');(tools/'checkpoint_loader.py').write_text(LOADER,encoding='utf-8')
    restore=module(tools/'restore_checkpoint.py','portable_checkpoint_restore')
    restored=work/'restore_validation'
    restoration=restore.restore(cipher,stage/'ENCRYPTED_DELIVERY_REPORT.json',KEY,restored,RELEASE)
    loader=module(tools/'checkpoint_loader.py','portable_checkpoint_loader');loaded=loader.verify(restored)
    assert loaded['counts']['sequences']==437 and loaded['counts']['supervised_tokens']==75248 and loaded['counts']['component_R']==490
    for name in ['TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json']:shutil.copyfile(OUT/name,stage/name)
    plan=(ROOT/'research/plans/20261027_wrd_main_v10/TRAINING_PLAN.md').read_text(encoding='utf-8')
    prefix='# 中间检查点：完整WRD主训练集 NOT_READY\n\n当前只有437序列/75248监督tokens，其中490原R tokens；source_events_02＋native_A_partial_02为唯一active入口。B已授权但资源尚未派发，B/C/真实修订/D/自主控制链缺失。本包不是最终完成，不启动训练，也不保证完整自主skills沉淀。以下为后续14B主／8B对照计划；旧Actor准入已被本次prepare血缘勘误纠正。\n\n'
    (stage/'TRAINING_PLAN.md').write_text(prefix+plan,encoding='utf-8')
    a_usage=load(episode/'usage.json');http=len(list((episode/'api_audit').glob('*/request.raw.json')))
    assert http==9 and a_usage['model_calls']==7
    checkpoint={'status':'INTERMEDIATE_NOT_FINAL_FULL_WRD_NOT_READY','active_counts':active['actual_counts'],
        'active_banks':['compiled/source_events_02','compiled/native_A_partial_02'],'distinct_sources':267,'joined_source_components':255,
        'B':{'authorized':True,'resources_dispatched':False,'native_B_started':False},
        'A_accounting':{'captured_compatibility_HTTP_requests':http,'paid_model_calls':a_usage['model_calls'],'known_total_tokens':a_usage['known_total_tokens'],'HTTP_requests_are_not_paid_model_call_count':True},
        'existing_source_reuse':{'original_conversation_occurrences':694,'existing_objects':750,'existing_object_bytes':117118540,'old_parts':12,'missing_original_objects_recovered_in_cipher':7,'old_objects_not_reuploaded':True},
        'full_WRD_main_training_ready':False,'training_started':False,'weights_loaded':False,'default_full_pipeline_training_entrypoint':None,
        'runtime_private_credentials_claude_reparse_directories_included':False}
    save(stage/'CHECKPOINT_STATUS.json',checkpoint)
    qa={'status':'PASS','authenticated_member_count':len(files)+1,'every_member_size_and_sha_read_back':True,
        'AES_GCM_roundtrip':receipt['authenticated_roundtrip_sha_verified'],'actual_restoration':restoration,'actual_loader_verification':loaded,
        'credential_exact_bytes_scan':{'configured_model_key_files_read_only_in_memory':2,'serialized_or_printed_key_values':False,
          'source_members_scanned_including_decompressed_gzip':scanned,'matches':0,'local_AES_key_not_archived':True},
        'source_event_02_independent_QA_sha256':digest(OUT/'prepare_ancestry_audit/COMPILED_SOURCE_EVENTS_02_INDEPENDENT_QA.json'),
        'native_A_V2_raw_identity_semantic_QA_sha256':digest(OUT/'prepare_ancestry_audit/NATIVE_A_PARTIAL_V2_RAW_IDENTITY_AND_SEMANTIC_QA.json'),
        'token_QA_is_not_full_pipeline_semantic_success':True,'training_started':False}
    save(stage/'CHECKPOINT_QA.json',qa)
    save(stage/'EXISTING_SOURCE_RESTORE_QA.json',{'status':'PASS','actual_portable_restore_tool_sha256':digest(tools/'restore_checkpoint.py'),
        'existing_objects_restored':restoration['existing_objects_restored']['objects'],
        'existing_object_bytes':restoration['existing_objects_restored']['bytes'],'old_part_count':12,'stream_buffer_bytes':BLOCK,
        'new_cipher_includes_no_duplicate_old_objects':True,'new_training_arrays_unchanged':True,'training_started':False,'weights_loaded':False})
    (stage/'README.md').write_text('''# WRD v10：中间检查点01，完整主训练集 NOT_READY

这份包有真实正文、原R、原生工具反馈、显式loss数组和可用恢复器，尚未完成完整WRD训练集。当前唯一入口为TRAINING_MANIFEST：437序列、75248监督tokens，其中490原R tokens；267来源/255联合component。B已获授权但资源尚未派发，B/C/真实修订/D/自主控制链仍缺；未训练、未加载权重。

active仅source_events_02与native_A_partial_02。旧431/144084、旧645R及v9辅助不混入。原始中间记录与被撤的旧partial留在认证cipher的audit_only，保全不等于正loss。原226、新H与静态dev/test继续隔离。26旧Actor任务已逐项接通，23确定保护祖先、3具体缺证；v9 21序列/36目标/1260监督tokens有显式未来导入撤销清单，旧包未静默改写。

恢复：安装CPU cryptography，执行 `python tooling/restore_checkpoint.py --cipher controlled/wrd-v10-checkpoint01.tar.gz.aesgcm --receipt ENCRYPTED_DELIVERY_REPORT.json --key <本地既有v4密钥> --out <新目录>`。密钥从未上传。认证成功后逐成员SHA/大小核对，原文件不执行。再执行 `python tooling/checkpoint_loader.py --root <恢复目录>`，只读取manifest指定的3个active分片，复原labels/weights，不启动训练。父工具与证据里的绝对原路径保留原字节，PAYLOAD_MANIFEST与EVIDENCE_PATH_ALIASES提供归档别名，不能直接按原Windows路径在Spark执行。

694原会话及附件相关750对象/117118540字节已在本仓库历史dist的12分片，完整EXISTING_SOURCE_REUSE随cipher交付，未重复上传旧对象。恢复时可加 `--existing-release-root <仓库根>`，流式逐SHA取回这些既有对象。新增7份原记录已按同字节恢复入本cipher。

原A的9个兼容HTTP请求与7个实际付费模型调用分别保全；用量570932 tokens，不能把HTTP兼容记录当付费调用数。原53工具请求与核心7工具学生投影覆盖另列。部分原R通过了精确范围和原SSE校验，其余错误/未知R与动作保持loss0；这不证明A整阶段或自主pipeline成功。详见TRAINING_PLAN、CHECKPOINT_STATUS和CHECKPOINT_QA。
''',encoding='utf-8')
    # Recheck the frozen source snapshot and public material before publishing.
    for row in files:
        path=Path(row['original_path']);assert path.stat().st_size==row['bytes']and digest(path)==row['sha256'],'source_changed_during_checkpoint'
    for path in stage.rglob('*'):
        if path.is_file():
            safe_name(path.relative_to(stage).as_posix())
            with path.open('rb')as f:
                if not scan_stream(f,patterns):raise ValueError('credential_bytes_in_public_delivery_packaging_stopped')
    payload=[{'path':p.relative_to(stage).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}for p in sorted(stage.rglob('*'))if p.is_file()]
    public_manifest={'schema_version':'wrd-v10-checkpoint01-public-manifest','status':'INTERMEDIATE_NOT_FINAL_FULL_WRD_NOT_READY',
        'files':payload,'payload_files':len(payload),'payload_bytes':sum(r['bytes']for r in payload),
        'authenticated_private_members':len(files)+1,'full_WRD_main_training_ready':False,'training_started':False,'weights_loaded':False,
        'contains_actual_data_encrypted':True,'no_keys_uploaded':True,'not_a_final_completion_claim':True}
    save(stage/'MANIFEST.json',public_manifest)
    shutil.copytree(stage,DEST)
    result={'status':'CHECKPOINT_BUILT_NOT_FINAL_NOT_PUSHED','destination':str(DEST),'manifest_sha256':digest(DEST/'MANIFEST.json'),
        'payload_files':len(payload)+1,'cipher_bytes':cipher.stat().st_size,'authenticated_private_files':len(files)+1,
        'actual_counts':active['actual_counts'],'restore_and_loader':'PASS','credential_matches':0,
        'training_started':False,'full_WRD_main_training_ready':False,'git_commit_or_push_performed':False}
    save(OUT/'CHECKPOINT01_BUILD_RECEIPT.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
