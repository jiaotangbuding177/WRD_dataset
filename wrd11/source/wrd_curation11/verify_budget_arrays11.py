"""Actual budget-profile binaries and205 real-pool wiring, no models/training.

Uses only exact pinned prior stdlib helper definitions and the exact reviewed
reader. The full53 source/QA/arrays remain unchanged and are not overwritten.
"""
from pathlib import Path
from collections import Counter
from copy import deepcopy
from array import array
import argparse,importlib.util,json,shutil,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation11'
HELPER_SHA='3ecad83d41034be431b1504a6bb4e9be9130b134b172577375624734cb7a21c4'
LOADER_SHA='a2d5f03fb9dec90763b238c5c499199176f1eddbf54b935475274981bc952c1c'
BASE_SHA='9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'

def import_helper():
 import hashlib
 p=ROOT/'research/data_prep/wrd_curation11/verify_curriculum_arrays11.py'
 assert hashlib.sha256(p.read_bytes()).hexdigest()==HELPER_SHA
 s=importlib.util.spec_from_file_location('exact_full53_array_helpers_only',p)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def main(a):
 h=import_helper();dest=a.out/'ALL832_BUDGET_ACTUAL_ARRAY_FOUR_FEATURES_QA.json';assert not dest.exists()
 m=h.load(a.root/'CURRICULUM_MANIFEST11.json');assert m['profile']=='budget_projection' and m['design_revision']=='5.0.54'
 fullmanifest=WORK/'curriculum01/CURRICULUM_MANIFEST11.json'
 assert h.sha(fullmanifest)=='a209934dac8dfe0eb5d91ef200d07fe07dd5adf2603c7c89ee0a811a4799778a'
 assert m['base_reference']==h.load(fullmanifest)['base_reference']
 assert h.sha(a.base/'TRAINING_MANIFEST.json')==BASE_SHA
 assert h.sha(a.base/'PAYLOAD_MANIFEST.json')==m['base_reference']['authenticated_payload_manifest_sha256']
 assert h.sha(a.base/'canonical_arrays10/ARRAY_INDEX10.json')==m['base_reference']['canonical_index_sha256']
 tokpath=a.out/'ALL627_BUDGET_FRESH_DUAL_TOKEN_MASK_PAIRED_TARGET_QA.json';tok=h.load(tokpath)
 assert tok['status'].startswith('PASS') and tok['direct_dual_tokenized_rows']==627
 assert tok['all627_ids_and_target_assistant_text_equal'] and tok['all627_positive_component_token_ID_sequences_equal']
 saved=a.root/'curriculum_loader11.py';trusted=ROOT/'research/data_prep/wrd_curation11/curriculum_loader11.py'
 assert h.sha(saved)==h.sha(trusted)==LOADER_SHA
 reader=h.module(saved)
 p=h.load(a.root/'canonical_arrays11/INDEX_PIN11.json');assert p['manifest_sha256']==h.sha(a.root/'CURRICULUM_MANIFEST11.json')
 ip=a.root/p['index_relative_path'];assert h.sha(ip)==p['index_sha256'] and ip.stat().st_size==p['index_bytes']
 index=h.load(ip);assert index['record_count']==627 and index['binary_files']==1881 and index['binary_bytes']==101648976
 assert index['manifest_sha256']==p['manifest_sha256']
 fullindex=h.load(WORK/'curriculum01/canonical_arrays11/ARRAY_INDEX11.json')
 syntheticids={e['id'] for e in index['records']};assert syntheticids=={e['id'] for e in fullindex['records']}
 report=h.load(WORK/'compiled_budget01/COMPILATION_REPORT.json');shards={x['path']:x for x in report['files']}
 for ref in m['synthetic_train_files']:
  old=shards[Path(ref['path']).name];assert ref['sha256']==old['sha256'] and ref['bytes']==old['bytes']
 stats={k:Counter() for k in ['real_process','synthetic']};binaries={k:Counter() for k in stats};rounding={k:0 for k in stats}
 seen=set();details=[];first=None
 records=reader.iter_records(a.root,a.base,pools=('real_process','synthetic'))
 features=reader.iter_features(a.root,a.base,pools=('real_process','synthetic'),use_binary=True,with_metadata=True)
 while True:
  try:item=next(records)
  except StopIteration:
   try:next(features)
   except StopIteration:break
   raise AssertionError('EXTRA_FEATURE_ROW')
  feature=next(features);pool,root,entry,row=item
  assert pool in stats and feature['pool']==pool and feature['id']==row['id']==entry['id']
  assert row['id'] not in seen;seen.add(row['id'])
  wanted=h.independent_features(row)
  assert reader.standard(row)==wanted==feature['features'],'STANDARD_OR_BINARY_FOUR_FEATURES_MISMATCH'
  assert entry['total_tokens']==row['total_tokens']==len(wanted['input_ids']) and entry['supervised_tokens']==row['supervised_tokens']
  if pool=='synthetic':
   assert row['id'] in syntheticids and row['source_ids']==[]
   assert row['original_record_metadata']['conditioning_interface_profile']=='budget_projection01'
   assert all(w==0.05 for _,_,_,w in row['supervision_spans'])
  else:assert row['id'] in m['base_reference']['real_process_ids'] and row['bank']!='source_contract_main'
  total=0
  for key,kind,dtype in [('input_ids','I','uint32_le'),('labels','q','int64_le'),('loss_weights','f','float32_le')]:
   ref=entry['arrays'][key];actual=reader.safe(root,ref['path']).read_bytes()
   assert ref['dtype']==dtype and len(actual)==ref['bytes'] and h.hs(actual)==ref['sha256']
   assert actual==h.encoded(wanted[key],kind),'ACTUAL_LITTLE_ENDIAN_BINARY_DIFFERS_FROM_EXPECTED'
   binaries[pool].update(files=1,bytes=len(actual));total+=len(actual)
  assert total==row['total_tokens']*16
  rounding[pool]+=sum(x!=y for x,y in zip(wanted['loss_weights'],array('f',wanted['loss_weights']).tolist()))
  assert all((l==-100)==(w==0) for l,w in zip(wanted['labels'],wanted['loss_weights']))
  stats[pool].update(rows=1,sequence_tokens=row['total_tokens'],positive_tokens=sum(l!=-100 for l in wanted['labels']),
      le16k=int(row['total_tokens']<=16384),le32k=int(row['total_tokens']<=32768))
  stats[pool]['weighted_mass']+=sum((stop-start)*w for start,stop,_,w in row['supervision_spans'])
  details.append({'id':row['id'],'pool':pool,'sequence_tokens':row['total_tokens'],'positive_tokens':row['supervised_tokens'],'actual_array_bytes':total})
  if pool=='synthetic' and first is None:first=(root,deepcopy(entry),deepcopy(row))
 assert len(seen)==832 and stats['real_process']['rows']==205 and stats['synthetic']['rows']==627
 assert stats['real_process']['sequence_tokens']==2537926 and stats['real_process']['positive_tokens']==156341
 assert stats['synthetic']['sequence_tokens']==6353061 and stats['synthetic']['positive_tokens']==57362
 assert stats['synthetic']['le16k']==402 and stats['real_process']['le16k']==133
 assert binaries['synthetic']==Counter(files=1881,bytes=101648976)
 assert binaries['real_process']==Counter(files=615,bytes=40606816)
 assert {x['id'] for x in details if x['pool']=='real_process'}==set(m['base_reference']['real_process_ids'])
 assert {x['id'] for x in details if x['pool']=='synthetic'}==syntheticids
 weighted=stats['synthetic']['weighted_mass']/(stats['synthetic']['weighted_mass']+stats['real_process']['weighted_mass'])
 assert abs(weighted-m['synthetic_fraction_of_effective_process_supervision'])<1e-12 and weighted<=0.2
 cr,ce,crow=first;negative=a.out/'actual_budget_binary_prompt_loss_canary';negative.mkdir(parents=True,exist_ok=False)
 changed=deepcopy(ce)
 for key in ['input_ids','labels','loss_weights']:
  source=reader.safe(cr,ce['arrays'][key]['path']);target=negative/(key+'.bin');shutil.copyfile(source,target)
  if key=='labels':
   b=bytearray(target.read_bytes());assert int.from_bytes(b[:8],'little',signed=True)==-100
   b[:8]=int(crow['input_ids'][0]).to_bytes(8,'little',signed=True);target.write_bytes(b)
  changed['arrays'][key]={**changed['arrays'][key],'path':target.name,'bytes':target.stat().st_size,'sha256':h.sha(target)}
 try:reader.binary(negative,changed,crow)
 except AssertionError:canary='REJECTED_VALID_HASH_BINARY_WITH_PROMPT_LABEL_LOSS'
 else:raise AssertionError('BUDGET_BAD_PROMPT_LABEL_NOT_REJECTED')
 assert h.sha(a.base/'TRAINING_MANIFEST.json')==BASE_SHA and h.sha(saved)==LOADER_SHA and 'torch' not in sys.modules
 result={'schema':'wrd11-independent-budget832-array-and-pool-QA',
  'status':'PASS_BUDGET627_ACTUAL1881_ARRAYS_AND205_REAL_POOL_ALL_FOUR_FEATURES_AND_LE_BYTES',
  'manifest':h.pin(a.root/'CURRICULUM_MANIFEST11.json'),'index':h.pin(ip),'index_pin':h.pin(a.root/'canonical_arrays11/INDEX_PIN11.json'),
  'loader_exact_SHA_checked_before_import':h.pin(saved),'reviewed_loader_source':h.pin(trusted),
  'same_627_logical_target_IDs_as_full53':True,'mutually_exclusive_profiles_not1254_new_targets':True,
  'source_assistant_and_positive_tokens_paired_equality_proof':h.pin(tokpath),
  'new_synthetic_rows':627,'new_synthetic_binary_files':1881,'new_synthetic_binary_bytes':101648976,
  'base_real_rows':205,'base_real_binary_files':615,'base_real_binary_bytes':40606816,
  'default_curriculum_rows':832,'counts_by_pool':{k:dict(v) for k,v in stats.items()},
  'binary_by_pool':{k:dict(v) for k,v in binaries.items()},'all_four_features_equal_canonical_Python_values':True,
  'every_actual_binary_SHA_size_and_little_endian_body_verified':True,
  'float32_disk_rounding_independent_of_Python_span_values':True,'positions_with_normal_f32_difference':rounding,
  'synthetic_effective_supervision_fraction':weighted,'synthetic_sequence_compute_fraction':6353061/(6353061+2537926),
  'default_one_pass_sequence_tokens':8890987,'default_le16k':535,'default_16k_to32k':297,
  'actual_valid_SHA_corrupt_prompt_label_canary':canary,'original623_main_unchanged':BASE_SHA,
  'full53_manifest_preserved':h.pin(fullmanifest),'full53_passed_array_helper':h.pin(ROOT/'research/data_prep/wrd_curation11/verify_curriculum_arrays11.py'),
  'script':h.pin(Path(__file__)),'training_started':False,'model_weights_loaded':False,'native_business_sessions_started':0,
  'GPU_cost_model_quality_lossless_transfer_and_native_readiness_not_measured':True}
 h.save(a.out/'ALL832_BUDGET_ARRAY_ROW_DETAILS.json',{'rows':details})
 h.save(dest,result)
 print(json.dumps({k:result[k] for k in ['status','new_synthetic_rows','new_synthetic_binary_files','new_synthetic_binary_bytes','base_real_rows','default_one_pass_sequence_tokens','actual_valid_SHA_corrupt_prompt_label_canary']}))

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--root',type=Path,default=WORK/'budget_curriculum01')
 ap.add_argument('--base',type=Path,default=ROOT/'output/wrd10root01')
 ap.add_argument('--out',type=Path,default=WORK/'technical_budget_qa01')
 main(ap.parse_args())
