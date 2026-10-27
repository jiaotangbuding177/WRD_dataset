"""Authenticate and restore the v10 checkpoint; no saved code is executed."""
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
