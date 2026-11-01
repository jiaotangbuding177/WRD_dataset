"""Stdlib-only, explicit-pool four-feature reader. Never loads model weights."""
from pathlib import Path,PurePosixPath
from array import array
import gzip,hashlib,json,sys
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def safe(root,name):
 assert isinstance(name,str) and name and not any(c in name for c in '\\:\x00\r\n')
 p=PurePosixPath(name);assert not p.is_absolute() and p.as_posix()==name and '..' not in p.parts
 assert all(v not in {'','.','..'} and not v.endswith((' ','.')) for v in p.parts)
 result=Path(root).joinpath(*p.parts);assert result.resolve().is_relative_to(Path(root).resolve())
 for q in [result,*result.parents]:
  assert not q.is_symlink() and not (hasattr(q,'is_junction') and q.is_junction())
  if q==Path(root).resolve():break
 return result
def verified(root,ref):
 p=safe(root,ref['path']);assert p.is_file() and p.stat().st_size==ref['bytes'] and sha(p)==ref['sha256'];return p
def rows(root,refs):
 for ref in refs:
  with gzip.open(verified(root,ref),'rt',encoding='utf-8-sig') as stream:
   for ordinal,line in enumerate(stream):
    if line.strip():yield ref['path'],ordinal,json.loads(line)
def standard(row):
 ids=row['input_ids'];labels=[-100]*len(ids);weights=[0.0]*len(ids)
 for a,b,component,w in row['supervision_spans']:
  for i in range(a,b):
   assert labels[i]==-100;labels[i]=ids[i];weights[i]=w
 return {'input_ids':ids,'attention_mask':[1]*len(ids),'labels':labels,'loss_weights':weights}
def decoded(root,ref,kind):
 p=verified(root,ref);v=array(kind);v.frombytes(p.read_bytes())
 assert v.itemsize=={'I':4,'q':8,'f':4}[kind]
 if sys.byteorder!='little':v.byteswap()
 return v.tolist()
def binary(root,entry,row):
 expected=standard(row);a=entry['arrays'];ids=decoded(root,a['input_ids'],'I');labels=decoded(root,a['labels'],'q');weights32=decoded(root,a['loss_weights'],'f')
 assert ids==expected['input_ids'] and labels==expected['labels']
 v=array('f',expected['loss_weights']);assert v.itemsize==4
 assert weights32==v.tolist(),'PERSISTED_FLOAT32_WEIGHTS_DIFFER_FROM_SPAN_VALUES'
 # Keep the same canonical Python values as the span reader. The disk bytes
 # are separately verified after IEEE float32 conversion, never confused.
 return {'input_ids':ids,'attention_mask':[1]*len(ids),'labels':labels,'loss_weights':expected['loss_weights']}
def iter_records(root,base_root=None,*,pools=('real_process','synthetic')):
 root=Path(root).resolve();m=load(root/'CURRICULUM_MANIFEST11.json')
 assert m['schema']=='wrd11-explicit-real-and-authored-curriculum-v1'
 assert set(pools)<={'real_process','synthetic','contract_optional'}
 if {'real_process','contract_optional'} & set(pools):
  assert base_root is not None,'EXPLICIT_AUTHENTICATED_CHECKPOINT10_ROOT_REQUIRED'
  base=Path(base_root).resolve();b=m['base_reference'];assert sha(base/'TRAINING_MANIFEST.json')==b['main_manifest_sha256']
  assert sha(base/'PAYLOAD_MANIFEST.json')==b['authenticated_payload_manifest_sha256']
  bm=load(base/'TRAINING_MANIFEST.json');index=load(base/'canonical_arrays10/ARRAY_INDEX10.json')
  assert sha(base/'canonical_arrays10/ARRAY_INDEX10.json')==b['canonical_index_sha256']
  entries={e['id']:e for e in index['records']}
  for path,ordinal,row in rows(base,bm['actual_train_files']):
   iscontract=row['bank']=='source_contract_main';pool='contract_optional' if iscontract else 'real_process'
   if pool not in pools:continue
   e=entries[row['id']];assert e['source_train_file']==path and e['source_record_index']==ordinal
   yield pool,base,e,row
 if 'synthetic' in pools:
  pin=load(root/'canonical_arrays11/INDEX_PIN11.json');assert pin['manifest_sha256']==sha(root/'CURRICULUM_MANIFEST11.json')
  indexpath=safe(root,pin['index_relative_path']);assert sha(indexpath)==pin['index_sha256'] and indexpath.stat().st_size==pin['index_bytes']
  index=load(indexpath);assert index['manifest_sha256']==pin['manifest_sha256'];entries={e['id']:e for e in index['records']}
  assert len(entries)==index['record_count']
  for path,ordinal,row in rows(root,m['synthetic_train_files']):
   e=entries.pop(row['id']);assert e['source_train_file']==path and e['source_record_index']==ordinal
   yield 'synthetic',root,e,row
  assert not entries,'UNREAD_CANONICAL_RECORD'
def iter_features(root,base_root=None,*,pools=('real_process','synthetic'),use_binary=True,with_metadata=False):
 for pool,source,entry,row in iter_records(root,base_root,pools=pools):
  f=binary(source,entry,row) if use_binary else standard(row)
  if with_metadata:yield {'pool':pool,'id':row['id'],'stage':row['stage'],'bank':row['bank'],'features':f}
  else:yield f
