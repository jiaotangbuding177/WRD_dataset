"""Authenticate/extract the v9 dataset. Never executes a model or saved code."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile


def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def safe_target(root,name):
    path=PurePosixPath(name)
    if path.is_absolute()or'..'in path.parts or'\\'in name:raise ValueError('unsafe_archive_member')
    target=root/Path(*path.parts)
    if not target.resolve().is_relative_to(root.resolve()):raise ValueError('member_outside_destination')
    return target


def restore_resources(out,release):
    reuse=json.loads((out/'EXISTING_RESOURCE_REUSE.json').read_text(encoding='utf-8'))
    replay=json.loads((out/'REPLAY_INPUT_MANIFEST.json').read_text(encoding='utf-8'))
    refs={r['sha256']:r for r in reuse['objects']}
    wanted={r['sha256']:r for r in replay['files']if r['kind']=='material'}
    source_index={refs[h]['existing_archive_member']:h for h in wanted}
    spec=importlib.util.spec_from_file_location('wrd_split_archive_reader',Path(__file__).with_name('verify_existing_resources.py'))
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    parts=[]
    for row in reuse['existing_parts']:
        p=release/row['path'];assert p.stat().st_size==row['bytes']and digest(p)==row['sha256'];parts.append(p)
    cas=out/'restored_material_objects';cas.mkdir(exist_ok=False);found=set()
    with io.BufferedReader(reader.Parts(parts),buffer_size=1048576)as stream:
        with tarfile.open(fileobj=stream,mode='r|gz')as tf:
            for member in tf:
                if not member.isfile()or member.name not in source_index:continue
                h=source_index[member.name];target=cas/h
                with tf.extractfile(member)as source,target.open('xb')as dest:shutil.copyfileobj(source,dest,1048576)
                assert digest(target)==h and target.stat().st_size==wanted[h]['bytes'];found.add(h)
                if len(found)==len(wanted):break
    assert found==set(wanted)
    for row in replay['files']:
        if row['kind']!='material':continue
        target=safe_target(out,row['path']);target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():assert digest(target)==row['sha256']
        else:shutil.copyfile(cas/row['sha256'],target)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cipher',required=True,type=Path);parser.add_argument('--receipt',required=True,type=Path)
    parser.add_argument('--key',required=True,type=Path);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--existing-release-root',type=Path)
    args=parser.parse_args();receipt=json.loads(args.receipt.read_text(encoding='utf-8'))
    assert digest(args.cipher)==receipt['ciphertext_sha256'];assert args.key.stat().st_size==32
    args.out.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('wrd_authenticated_archive',Path(__file__).with_name('shared_encryption_v4.py'))
    crypto=importlib.util.module_from_spec(spec);spec.loader.exec_module(crypto)
    plain=args.out/'payload.verified.tar.gz'
    assert crypto.decrypt_hash(args.cipher,args.key,output=plain)==receipt['plaintext_sha256']
    with tarfile.open(plain,'r:gz')as tf:
        for member in tf:
            target=safe_target(args.out,member.name)
            if member.isdir():target.mkdir(parents=True,exist_ok=True);continue
            if not member.isfile():raise ValueError('links_and_special_files_not_allowed')
            target.parent.mkdir(parents=True,exist_ok=True)
            with tf.extractfile(member)as source,target.open('xb')as dest:shutil.copyfileobj(source,dest,1048576)
    manifest=json.loads((args.out/'PAYLOAD_MANIFEST.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        p=safe_target(args.out,row['path']);assert p.stat().st_size==row['bytes']and digest(p)==row['sha256']
    if args.existing_release_root:restore_resources(args.out,args.existing_release_root)
    print(json.dumps({'status':'PASS','files':len(manifest['files']),'training_started':False,'restored_data_are_not_automatic_training_admission':True}))


if __name__=='__main__':main()
