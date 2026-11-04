"""Create real arrays and an explicit curriculum; old real main stays intact."""
from pathlib import Path
from collections import Counter,defaultdict
from array import array
import argparse,hashlib,json,shutil,sys
sys.dont_write_bytecode=True
from curriculum_loader11 import rows,standard,sha
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation11'
OUT=WORK/'curriculum01';BASE=ROOT/'output/wrd10root01';COMPILED=WORK/'compiled04'
BASE_SHA='9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def ref(p,root):return {'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
def accumulate(c,r):
 c.update(sequences=1,targets=1,sequence_tokens=r['total_tokens'],positive_tokens=r['supervised_tokens'],le16k=int(r['total_tokens']<=16384),le32k=int(r['total_tokens']<=32768))
 for a,b,component,w in r['supervision_spans']:c['weighted_positive_mass']+=(b-a)*w;c['component_'+component]+=b-a
def main():
 global OUT,COMPILED
 parser=argparse.ArgumentParser();parser.add_argument('--compiled',type=Path,default=COMPILED);parser.add_argument('--out',type=Path,default=OUT)
 parser.add_argument('--profile',choices=['full_native53','budget_projection'],default='full_native53')
 args=parser.parse_args();OUT=args.out;COMPILED=args.compiled
 assert sha(BASE/'TRAINING_MANIFEST.json')==BASE_SHA
 real=Counter();contract=Counter();by_stage=defaultdict(Counter);realids=[]
 bm=load(BASE/'TRAINING_MANIFEST.json')
 for _,_,r in rows(BASE,bm['actual_train_files']):
  if r['bank']=='source_contract_main':accumulate(contract,r)
  else:accumulate(real,r);realids.append(r['id'])
 assert real['targets']==205 and contract['targets']==418
 OUT.mkdir(parents=True,exist_ok=False)
 report=load(COMPILED/'COMPILATION_REPORT.json');refs=[]
 for original in report['files']:
  source=COMPILED/original['path'];assert source.stat().st_size==original['bytes'] and sha(source)==original['sha256']
  dest=OUT/'synthetic/compiled'/original['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest);refs.append(ref(dest,OUT))
 for name in ['CAUSAL_TEMPLATE.json','COMPILATION_REPORT.json']:
  shutil.copyfile(COMPILED/name,OUT/'synthetic/compiled'/name)
 allsynthetic=Counter();bank=defaultdict(Counter);synthetic_ids=[];max_length=0
 for _,_,r in rows(OUT,refs):
  accumulate(allsynthetic,r);accumulate(bank[r['bank']],r);accumulate(by_stage[r['stage']],r)
  assert r['source_ids']==[] and r['original_record_metadata']['teacher_original_R_supervised'] is False
  synthetic_ids.append(r['id']);max_length=max(max_length,r['total_tokens'])
 weighted_fraction=allsynthetic['weighted_positive_mass']/(real['weighted_positive_mass']+allsynthetic['weighted_positive_mass'])
 assert weighted_fraction<=0.20
 base_ref={'required_checkpoint':'AUTHENTICATED_05_THROUGH10_MERGED_ROOT','main_manifest_sha256':BASE_SHA,
  'authenticated_payload_manifest_sha256':sha(BASE/'PAYLOAD_MANIFEST.json'),'canonical_index_sha256':sha(BASE/'canonical_arrays10/ARRAY_INDEX10.json'),
  'real_process_ids':sorted(realids),'original_main_not_modified':True}
 m={'schema':'wrd11-explicit-real-and-authored-curriculum-v1','design_revision':'5.0.54','change_id':'ALG-20261031-06','profile':args.profile,
  'base_reference':base_ref,'synthetic_train_files':refs,'canonical_index_relative_path':'canonical_arrays11/ARRAY_INDEX11.json',
  'default_component_pools':['real_process','synthetic'],'contract_pool':'OPTIONAL_SEPARATE_WARMUP_NOT_DEFAULT_PROCESS_CURRICULUM',
  'real_process_counts':dict(real),'contract_optional_counts':dict(contract),'synthetic_counts':dict(allsynthetic),
  'synthetic_by_bank':{k:dict(v) for k,v in bank.items()},'synthetic_by_stage':{k:dict(v) for k,v in by_stage.items()},
  'total_available_targets_including_contract':real['targets']+contract['targets']+allsynthetic['targets'],
  'default_process_curriculum_targets':real['targets']+allsynthetic['targets'],
  'synthetic_weight':0.05,'synthetic_fraction_of_effective_process_supervision':weighted_fraction,
  'effective_fraction_is_not_compute_fraction':True,'max_synthetic_total_tokens':max_length,
  'profiles_are_mutually_exclusive_same627_targets_not_additive':True,
  'budget_projection_not_claimed_native53_request_equivalence':args.profile=='budget_projection',
  'real_process_independent_source_groups_unchanged':44,'real_process_source_ids_unchanged':56,
  'original_teacher_R_added_by_this_curriculum':0,'new_enterprise_sources':0,
  'real_native_autonomous_demonstrations':0,'real_business_qualified_KEEP':0,
  'student_effect_measured':False,'full_WRD_training_ready':False,'training_started':False,'is_launch_config':False}
 save(OUT/'CURRICULUM_MANIFEST11.json',m)
 entries=[];bytes_count=0
 for path,ordinal,r in rows(OUT,refs):
  f=standard(r);directory=OUT/'canonical_arrays11/arrays'/f'{len(entries):04d}_{hashlib.sha256(r["id"].encode()).hexdigest()[:16]}';directory.mkdir(parents=True)
  arrays={}
  for name,kind,dtype in [('input_ids','I','uint32_le'),('labels','q','int64_le'),('loss_weights','f','float32_le')]:
   values=array(kind,f[name]);assert values.itemsize=={'I':4,'q':8,'f':4}[kind]
   if sys.byteorder!='little':values.byteswap()
   p=directory/(name+'.bin');p.write_bytes(values.tobytes());arrays[name]={**ref(p,OUT),'dtype':dtype};bytes_count+=p.stat().st_size
  entries.append({'position':len(entries),'id':r['id'],'source_train_file':path,'source_record_index':ordinal,'total_tokens':r['total_tokens'],
   'supervised_tokens':r['supervised_tokens'],'supervision_spans_sha256':r['supervision_spans_sha256'],'arrays':arrays})
 index={'schema':'wrd11-authored-canonical-arrays-v1','manifest_relative_path':'CURRICULUM_MANIFEST11.json',
  'manifest_sha256':sha(OUT/'CURRICULUM_MANIFEST11.json'),'record_count':len(entries),'binary_files':len(entries)*3,'binary_bytes':bytes_count,
  'records':entries,'attention_mask':'ALL_ONES_FROM_ROW_LENGTH','training_started':False}
 save(OUT/'canonical_arrays11/ARRAY_INDEX11.json',index)
 ip=OUT/'canonical_arrays11/ARRAY_INDEX11.json';save(OUT/'canonical_arrays11/INDEX_PIN11.json',{'index_relative_path':ip.relative_to(OUT).as_posix(),'index_bytes':ip.stat().st_size,'index_sha256':sha(ip),'manifest_sha256':index['manifest_sha256']})
 shutil.copyfile(Path(__file__).with_name('curriculum_loader11.py'),OUT/'curriculum_loader11.py')
 save(OUT/'BUILD_RECEIPT11.json',{'status':'REAL_627_ARRAYS_AND_EXPLICIT_CURRICULUM_BUILT_PENDING_FULL_INDEPENDENT_QA','manifest_sha256':index['manifest_sha256'],
  'new_targets':len(entries),'binary_files':len(entries)*3,'binary_bytes':bytes_count,'real_main_unchanged':sha(BASE/'TRAINING_MANIFEST.json')==BASE_SHA,
  'synthetic_weighted_fraction':weighted_fraction,'training_started':False,'source_script_sha256':sha(__file__)})
 print(json.dumps({'real_process':dict(real),'synthetic':dict(allsynthetic),'new_arrays':len(entries)*3,'array_bytes':bytes_count,'synthetic_weighted_fraction':weighted_fraction}))
if __name__=='__main__':main()
