"""Independent real-pool wiring and actual synthetic binary four-feature QA.

Only trusted SHA-pinned stdlib reader code is executed. No model, training or
native Agent call occurs. Python span weights and IEEE f32 disk bytes are
validated separately so 0.05 rounding cannot create a false data failure.
"""
from pathlib import Path
from collections import Counter
from array import array
from copy import deepcopy
import argparse,hashlib,importlib.util,json,shutil,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation11'
LOADER_SHA='a2d5f03fb9dec90763b238c5c499199176f1eddbf54b935475274981bc952c1c'
MAIN_SHA='9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'

def hs(b):return hashlib.sha256(b).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def pin(p):return dict(path=str(Path(p).resolve()),bytes=Path(p).stat().st_size,sha256=sha(p))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists(),'PRESERVE_PREVIOUS_QA'
 p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def module(path):
 assert sha(path)==LOADER_SHA,'LOADER_NOT_EXACT_REVIEWED_BYTES'
 s=importlib.util.spec_from_file_location('trusted_exact_curriculum_reader11',path)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def encoded(values,kind):
 v=array(kind,values);assert v.itemsize=={'I':4,'q':8,'f':4}[kind]
 if sys.byteorder!='little':v.byteswap()
 return v.tobytes()
def independent_features(row):
 ids=row['input_ids'];labels=[-100]*len(ids);weights=[0.0]*len(ids)
 last=0
 for start,stop,component,weight in row['supervision_spans']:
  assert 0<=start<stop<=len(ids) and start>=last;last=stop
  for p in range(start,stop):assert labels[p]==-100;labels[p]=ids[p];weights[p]=weight
 return dict(input_ids=ids,attention_mask=[1]*len(ids),labels=labels,loss_weights=weights)


def main(a):
 out=a.out/'ALL832_CURRICULUM_BINARY_FOUR_FEATURES_QA.json';assert not out.exists()
 m=load(a.root/'CURRICULUM_MANIFEST11.json');assert sha(a.base/'TRAINING_MANIFEST.json')==MAIN_SHA
 assert sha(a.base/'PAYLOAD_MANIFEST.json')==m['base_reference']['authenticated_payload_manifest_sha256']
 assert sha(a.base/'canonical_arrays10/ARRAY_INDEX10.json')==m['base_reference']['canonical_index_sha256']
 assert sha(ROOT/'output/20261027_wrd_main_v10/TRAINING_MANIFEST.json')==MAIN_SHA
 tokenqa=load(a.out/'ALL627_SYNTHETIC_TOKEN_MASK_SOURCE_QA.json')
 assert tokenqa['status'].startswith('PASS') and tokenqa['direct_dual_tokenized_rows']==627
 trusted=ROOT/'research/data_prep/wrd_curation11/curriculum_loader11.py'
 saved=a.root/'curriculum_loader11.py';assert sha(trusted)==sha(saved)==LOADER_SHA
 reader=module(saved)
 idxpin=load(a.root/'canonical_arrays11/INDEX_PIN11.json')
 assert idxpin['manifest_sha256']==sha(a.root/'CURRICULUM_MANIFEST11.json')
 indexpath=a.root/idxpin['index_relative_path'];assert sha(indexpath)==idxpin['index_sha256']
 assert indexpath.stat().st_size==idxpin['index_bytes']
 index=load(indexpath);assert index['record_count']==627 and index['binary_files']==1881
 assert index['binary_bytes']==270871920 and len(index['records'])==627
 assert index['manifest_sha256']==idxpin['manifest_sha256']
 compile_report=load(WORK/'compiled04/COMPILATION_REPORT.json')
 expected_shards={r['path']:r for r in compile_report['files']}
 for ref in m['synthetic_train_files']:
  n=Path(ref['path']).name;original=expected_shards[n]
  assert ref['sha256']==original['sha256'] and ref['bytes']==original['bytes']
 synthetic_ids={r['id'] for r in index['records']};seen=set();poolcounts={k:Counter() for k in ['real_process','synthetic']}
 binaries={k:Counter() for k in poolcounts};float_differences={k:0 for k in poolcounts};details=[];canary_example=None
 record_iter=reader.iter_records(a.root,a.base,pools=('real_process','synthetic'))
 feature_iter=reader.iter_features(a.root,a.base,pools=('real_process','synthetic'),use_binary=True,with_metadata=True)
 while True:
  try:record=next(record_iter)
  except StopIteration:
   try:next(feature_iter)
   except StopIteration:break
   raise AssertionError('FEATURE_READER_HAS_EXTRA_ROWS')
  try:feature=next(feature_iter)
  except StopIteration:raise AssertionError('FEATURE_READER_MISSING_ROW')
  pool,root,entry,row=record
  assert pool in poolcounts and feature['id']==row['id']==entry['id'] and feature['pool']==pool
  assert row['id'] not in seen;seen.add(row['id'])
  expected=independent_features(row)
  assert reader.standard(row)==expected and feature['features']==expected,'FOUR_FEATURES_NOT_CANONICAL_PYTHON_VALUES'
  assert entry['total_tokens']==len(expected['input_ids'])==row['total_tokens']
  assert entry['supervised_tokens']==row['supervised_tokens']
  if pool=='synthetic':
   assert row['id'] in synthetic_ids and row['source_ids']==[]
   assert all(w==0.05 for _,_,_,w in row['supervision_spans'])
  else:
   assert row['id'] in m['base_reference']['real_process_ids'] and row['bank']!='source_contract_main'
  bytes_for_record=0
  for key,kind,dtype in [('input_ids','I','uint32_le'),('labels','q','int64_le'),('loss_weights','f','float32_le')]:
   ref=entry['arrays'][key];p=reader.safe(root,ref['path']);actual=p.read_bytes()
   assert ref['dtype']==dtype and len(actual)==ref['bytes'] and hs(actual)==ref['sha256']
   assert actual==encoded(expected[key],kind),'ACTUAL_BINARY_BYTES_NOT_EXPECTED_LITTLE_ENDIAN'
   binaries[pool].update(files=1,bytes=len(actual));bytes_for_record+=len(actual)
  assert bytes_for_record==16*row['total_tokens']
  rounded=array('f',expected['loss_weights']).tolist()
  float_differences[pool]+=sum(p!=q for p,q in zip(expected['loss_weights'],rounded))
  assert all((l==-100)==(w==0) for l,w in zip(expected['labels'],expected['loss_weights']))
  positive=sum(l!=-100 for l in expected['labels'])
  poolcounts[pool].update(rows=1,sequence_tokens=row['total_tokens'],positive_tokens=positive,
      le16k=int(row['total_tokens']<=16384),le32k=int(row['total_tokens']<=32768))
  poolcounts[pool]['weighted_mass']+=sum((b-a)*w for a,b,_,w in row['supervision_spans'])
  details.append({'id':row['id'],'pool':pool,'sequence_tokens':row['total_tokens'],'positive_tokens':positive,'actual_array_bytes':bytes_for_record})
  if pool=='synthetic' and canary_example is None:canary_example=(root,deepcopy(entry),deepcopy(row))
 assert len(seen)==832 and poolcounts['real_process']['rows']==205 and poolcounts['synthetic']['rows']==627
 assert {r['id'] for r in index['records']}=={x['id'] for x in details if x['pool']=='synthetic'}
 assert set(m['base_reference']['real_process_ids'])=={x['id'] for x in details if x['pool']=='real_process'}
 assert poolcounts['real_process']['sequence_tokens']==2537926 and poolcounts['real_process']['positive_tokens']==156341
 assert poolcounts['synthetic']['sequence_tokens']==16929495 and poolcounts['synthetic']['positive_tokens']==57362
 assert binaries['synthetic']==Counter(files=1881,bytes=270871920)
 assert binaries['real_process']==Counter(files=615,bytes=40606816)
 mass=poolcounts['synthetic']['weighted_mass']/(poolcounts['synthetic']['weighted_mass']+poolcounts['real_process']['weighted_mass'])
 assert abs(mass-m['synthetic_fraction_of_effective_process_supervision'])<1e-12 and mass<=0.2
 # Verify an actual validly hashed corrupted label file is rejected after the
 # pin check, rather than merely exercising a mismatching SHA rejection.
 cr,ce,crow=canary_example;negative=a.out/'actual_binary_prompt_loss_canary';negative.mkdir(parents=True,exist_ok=False)
 changed=deepcopy(ce)
 for key in ['input_ids','labels','loss_weights']:
  old=reader.safe(cr,ce['arrays'][key]['path']);dest=negative/(key+'.bin');shutil.copyfile(old,dest)
  if key=='labels':
   content=bytearray(dest.read_bytes());assert int.from_bytes(content[:8],'little',signed=True)==-100
   content[:8]=int(crow['input_ids'][0]).to_bytes(8,'little',signed=True);dest.write_bytes(content)
  changed['arrays'][key]={**changed['arrays'][key],'path':dest.name,'bytes':dest.stat().st_size,'sha256':sha(dest)}
 try:reader.binary(negative,changed,crow)
 except AssertionError:negative_status='REJECTED_VALID_HASH_BINARY_WITH_PROMPT_LABEL_LOSS'
 else:raise AssertionError('PROMPT_BINARY_NEGATIVE_NOT_REJECTED')
 assert sha(a.base/'TRAINING_MANIFEST.json')==MAIN_SHA and sha(saved)==LOADER_SHA
 assert 'torch' not in sys.modules
 result={'schema':'wrd11-independent-all832-actual-array-and-reader-QA',
  'status':'PASS_ALL627_NEW_ARRAYS_AND205_REAL_POOL_FOUR_FEATURES_WITH_EXACT_LITTLE_ENDIAN_BYTES',
  'curriculum_manifest':pin(a.root/'CURRICULUM_MANIFEST11.json'),'new_index':pin(indexpath),'new_pin':pin(a.root/'canonical_arrays11/INDEX_PIN11.json'),
  'exact_loader_checked_before_import':pin(saved),'trusted_source_loader':pin(trusted),
  'new_synthetic_rows':627,'new_synthetic_binary_files':1881,'new_synthetic_binary_bytes':270871920,
  'real_process_rows_bound_to_unchanged10':205,'base_real_binary_files_checked':615,'base_real_binary_bytes_checked':40606816,
  'default_curriculum_rows':832,'optional418_contract_rows_not_in_default_pool':True,
  'counts_by_pool':{k:dict(v) for k,v in poolcounts.items()},'binary_by_pool':{k:dict(v) for k,v in binaries.items()},
  'canonical_Python_four_features_equal_all_rows':True,'all_disk_array_SHA_sizes_and_little_endian_values_verified':True,
  'Python_weights_preserved_from_spans':True,'float32_rounding_checked_independently_at_byte_level':True,
  'positions_with_expected_Python_vs_f32_rounding_difference':float_differences,
  'synthetic_effective_supervision_fraction':mass,
  'synthetic_sequence_compute_fraction':16929495/(16929495+2537926),
  'negative_actual_valid_SHA_binary_canary':negative_status,
  'all627_HF_proof':pin(a.out/'ALL627_SYNTHETIC_TOKEN_MASK_SOURCE_QA.json'),
  'base623_main_manifest_unchanged':MAIN_SHA,'base_authenticated_payload_manifest_pin':m['base_reference']['authenticated_payload_manifest_sha256'],
  'script':pin(Path(__file__)),'training_started':False,'weights_loaded':False,'native_business_sessions_started':0,
  'business_quality_or_real_KEEP_not_proven_by_arrays':True}
 save(a.out/'ALL832_CURRICULUM_ARRAY_ROW_DETAILS.json',{'rows':details})
 save(out,result)
 print(json.dumps({k:result[k] for k in ['status','new_synthetic_rows','new_synthetic_binary_files','new_synthetic_binary_bytes','real_process_rows_bound_to_unchanged10','synthetic_effective_supervision_fraction','synthetic_sequence_compute_fraction','negative_actual_valid_SHA_binary_canary']}))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--root',type=Path,default=WORK/'curriculum01')
 p.add_argument('--base',type=Path,default=ROOT/'output/wrd10root01')
 p.add_argument('--out',type=Path,default=WORK/'technical_qa01')
 main(p.parse_args())
