"""Strict plain public-data archive restore; never executes saved source."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,shutil,tarfile
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def unique(pairs):
 d={}
 for k,v in pairs:assert k not in d,'DUPLICATE_JSON_KEY';d[k]=v
 return d
def safe(root,name):
 assert isinstance(name,str) and name and not any(x in name for x in '\\:<>"|?*') and not any(ord(x)<32 or ord(x)==127 for x in name)
 p=PurePosixPath(name);assert p.as_posix()==name and not p.is_absolute() and '..' not in p.parts
 reserved={'con','prn','aux','nul',*('com'+str(i) for i in range(1,10)),*('lpt'+str(i) for i in range(1,10))}
 assert all(s not in {'','.','..'} and not s.endswith((' ','.')) and s.split('.')[0].casefold() not in reserved for s in p.parts)
 root=Path(root).resolve();q=root.joinpath(*p.parts);assert q.resolve().is_relative_to(root)
 for a in [q,*q.parents]:
  assert not a.is_symlink() and not (hasattr(a,'is_junction') and a.is_junction()),'SYMLINK_OR_JUNCTION'
  if a==root:break
 return q
def restore(archive,archive_sha256,manifest_sha256,out):
 archive=Path(archive);out=Path(out);assert not out.exists(),'NEW_OUTPUT_ROOT_REQUIRED'
 assert sha(archive)==archive_sha256,'ARCHIVE_SHA_MISMATCH'
 out.mkdir(parents=True,exist_ok=False);found=set()
 with tarfile.open(archive,'r|gz') as tf:
  first=tf.next();assert first and first.name=='PAYLOAD_MANIFEST11.json' and first.isfile() and first.size<=67108864
  body=tf.extractfile(first).read();assert hashlib.sha256(body).hexdigest()==manifest_sha256
  m=json.loads(body,object_pairs_hook=unique);assert m['schema']=='wrd11-public-curriculum-and-audit-v1'
  expected={};folded=set()
  for r in m['files']:
   name=r['path'];safe(out,name);assert name not in expected and name.casefold() not in folded
   assert name.casefold() not in {'payload_manifest11.json','restore_receipt11.json'},'RESERVED_GENERATED_NAME'
   assert type(r['bytes']) is int and r['bytes']>=0
   assert len(r['sha256'])==64 and all(c in '0123456789abcdef' for c in r['sha256'])
   expected[name]=r;folded.add(name.casefold())
  (out/'PAYLOAD_MANIFEST11.json').write_bytes(body)
  while True:
   member=tf.next()
   if member is None:break
   assert member.isfile() and member.name in expected and member.name not in found
   r=expected[member.name];assert member.size==r['bytes'];p=safe(out,member.name);p.parent.mkdir(parents=True,exist_ok=True)
   with tf.extractfile(member) as source,p.open('xb') as target:shutil.copyfileobj(source,target,1048576)
   assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'];found.add(member.name)
 assert found==set(expected),'MISSING_MEMBER'
 receipt={'status':'PASS_REAL_ARCHIVE_RESTORE_ALL_EXPLICIT_MEMBERS_SHA','archive_sha256':archive_sha256,'manifest_sha256':manifest_sha256,
  'files_verified':len(found),'tar_members':len(found)+1,'payload_source_executed':False,'training_started':False}
 (out/'RESTORE_RECEIPT11.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--archive-sha256',required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();print(json.dumps(restore(a.archive,a.archive_sha256,a.manifest_sha256,a.out)))
