"""Authenticate and restore explicit WRD57 files; never execute payload code."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tarfile

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb")as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def unique(pairs):
    r={}
    for k,v in pairs:assert k not in r,"DUPLICATE_JSON_KEY";r[k]=v
    return r
def safe(root,name):
    assert isinstance(name,str)and name and not any(c in name for c in '\\:<>"|?*')
    assert not any(ord(c)<32 or ord(c)==127 for c in name)
    p=PurePosixPath(name);assert p.as_posix()==name and not p.is_absolute()and ".."not in p.parts
    reserved={"con","prn","aux","nul",*("com"+str(i)for i in range(1,10)),*("lpt"+str(i)for i in range(1,10))}
    assert all(s not in {"",".",".."}and not s.endswith((" ","."))and s.split(".")[0].casefold()not in reserved for s in p.parts)
    root=Path(root).resolve();dest=root.joinpath(*p.parts)
    assert dest.resolve().is_relative_to(root)
    for q in [dest,*dest.parents]:
        assert not q.is_symlink()and not(hasattr(q,"is_junction")and q.is_junction()),"RESTORE_LINK_OR_JUNCTION"
        if q.exists():assert not(getattr(q.lstat(),"st_file_attributes",0)&0x400),"RESTORE_REPARSE_POINT"
        if q==root:break
    return dest
def restore_plain(plain,manifest_sha256,out):
    plain=Path(plain);out=Path(out);assert not out.exists(),"NEW_RESTORE_ROOT_REQUIRED"
    out.mkdir(parents=True,exist_ok=False);found=set();expected={};folded=set()
    with tarfile.open(plain,"r|gz")as tf:
        first=tf.next();assert first and first.name=="PAYLOAD_MANIFEST57.json"and first.isfile()and first.size<=67108864
        body=tf.extractfile(first).read();assert hashlib.sha256(body).hexdigest()==manifest_sha256,"MANIFEST_SHA_MISMATCH"
        manifest=json.loads(body,object_pairs_hook=unique)
        assert manifest["schema"]=="wrd57-authenticated-offline-increment-payload-v1"
        for r in manifest["files"]:
            name=r["path"];safe(out,name)
            assert name not in expected and name.casefold()not in folded,"DUPLICATE_OR_CASE_ALIAS"
            assert name.casefold()not in {"payload_manifest57.json","restore_receipt57.json"}
            assert type(r["bytes"])is int and r["bytes"]>=0
            assert isinstance(r["sha256"],str)and len(r["sha256"])==64 and all(c in"0123456789abcdef"for c in r["sha256"])
            expected[name]=r;folded.add(name.casefold())
        (out/"PAYLOAD_MANIFEST57.json").write_bytes(body)
        while True:
            member=tf.next()
            if member is None:break
            assert member.isfile()and member.name in expected and member.name not in found,"UNEXPECTED_DUPLICATE_OR_NONREGULAR_MEMBER"
            r=expected[member.name];assert member.size==r["bytes"],"MEMBER_SIZE_MISMATCH"
            dest=safe(out,member.name);dest.parent.mkdir(parents=True,exist_ok=True)
            with tf.extractfile(member)as source,dest.open("xb")as target:shutil.copyfileobj(source,target,1048576)
            assert dest.stat().st_size==r["bytes"]and sha(dest)==r["sha256"],"RESTORED_FILE_SHA_MISMATCH"
            found.add(member.name)
    assert found==set(expected),"MISSING_EXPLICIT_MEMBER"
    return {"status":"PASS_REAL_AUTHENTICATED_ARCHIVE_RESTORE_EVERY_EXPLICIT_FILE_SHA","files_verified":len(found),"tar_members":len(found)+1,"restored_source_bytes":sum(r["bytes"]for r in expected.values()),"manifest_sha256":manifest_sha256,"payload_source_executed":False,"training_started":False}
def restore(cipher,cipher_sha256,manifest_sha256,key_file,aes_api,out):
    cipher=Path(cipher);key_file=Path(key_file);aes_api=Path(aes_api);out=Path(out)
    assert sha(cipher)==cipher_sha256,"CIPHERTEXT_SHA_MISMATCH"
    assert not out.exists();assert key_file.is_file()
    spec=importlib.util.spec_from_file_location("approved_existing_AES_restore57",aes_api)
    api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
    plain=out.with_name(out.name+".authenticated.tar.gz")
    assert not plain.exists(),"NEW_DECRYPTED_ARCHIVE_PATH_REQUIRED"
    plain_hash=api.decrypt_hash(cipher,key_file,plain)
    assert sha(plain)==plain_hash
    receipt=restore_plain(plain,manifest_sha256,out)
    receipt.update(ciphertext_sha256=cipher_sha256,plaintext_sha256=plain_hash,plaintext_bytes=plain.stat().st_size,key_never_copied=True)
    (out/"RESTORE_RECEIPT57.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return receipt
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--cipher",type=Path,required=True);p.add_argument("--cipher-sha256",required=True);p.add_argument("--manifest-sha256",required=True);p.add_argument("--key-file",type=Path,required=True);p.add_argument("--aes-api",type=Path,default=Path(__file__).with_name("existing_AES_API.py"));p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();print(json.dumps(restore(a.cipher,a.cipher_sha256,a.manifest_sha256,a.key_file,a.aes_api,a.out)))
