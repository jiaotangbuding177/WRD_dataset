"""Python-standard-library loader for input-only eval arrays.
No tokenizer/model/torch dependency. Returns four real serialized features.
"""
from array import array
from pathlib import Path
import hashlib,json,sys

def load_index(root):
 return json.loads((Path(root)/'INDEX.json').read_text(encoding='utf-8'))
def validate_features(features):
 n=len(features['input_ids'])
 assert n>0 and all(len(v)==n for v in features.values()),'FEATURE_LENGTH_MISMATCH'
 assert all(v==-100 for v in features['labels']),'EVAL_LABEL_MUST_IGNORE'
 assert all(v==0 for v in features['loss_weights']),'EVAL_WEIGHT_MUST_ZERO'
 assert all(v==1 for v in features['attention_mask']),'ATTENTION_MASK_MUST_ONE'
 return True
def load_record(root,profile_id,task_id):
 root=Path(root);index=load_index(root)
 profile=next(x for x in index['profiles'] if x['profile_id']==profile_id)
 row=next(x for x in profile['records'] if x['task_id']==task_id)
 out={}
 for name,meta in row['features'].items():
  path=(root/meta['path']).resolve()
  assert path.is_relative_to(root.resolve()),'ARRAY_PATH_ESCAPE'
  b=path.read_bytes()
  assert len(b)==meta['bytes'] and hashlib.sha256(b).hexdigest()==meta['sha256'],'ARRAY_ENTITY_SHA_MISMATCH'
  a=array(meta['typecode']);a.frombytes(b)
  if sys.byteorder!='little' and a.itemsize>1:a.byteswap()
  assert len(a)==row['tokens'],'ARRAY_TOKEN_LENGTH_MISMATCH'
  out[name]=list(a)
 validate_features(out)
 return out
def iter_records(root,profile_id,split=None):
 index=load_index(root);profile=next(x for x in index['profiles'] if x['profile_id']==profile_id)
 for row in profile['records']:
  if split is None or row['split']==split:yield row,load_record(root,profile_id,row['task_id'])
