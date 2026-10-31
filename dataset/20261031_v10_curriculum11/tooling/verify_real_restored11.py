"""Fresh verification of actual restored plain curriculum data and binaries.

Never imports arbitrary payload source; only the reviewed workspace reader is
imported after an exact SHA check. No tokenizer, model, native call or training.
"""
from pathlib import Path,PurePosixPath
from collections import Counter,defaultdict
from copy import deepcopy
from decimal import Decimal
from array import array
import hashlib,importlib.util,json,os,shutil,stat,sys,tarfile
sys.dont_write_bytecode=True
ROOT=Path('D:/skillloop');RESTORED=ROOT/'output/wrd11publicroot01';BASE=ROOT/'output/wrd10root01'
DEL=ROOT/'output/20261031_wrd_curation11_delivery';OUT=DEL/'restored_qa11'
ARCHIVE=ROOT/'output/20261025_wrd_training_dataset/git_release/dataset/20261031_v10_curriculum11/data/wrd-curriculum11.tar.gz'
ARCHIVE_SHA='7b2f8b6d2719340d2d3d2f8090a3d6c5c580960c7c9fb233de8396445aaad0a7'
PM_SHA='e17ad42a98967641d0fd24779012791a5052a8d7919f398309f6081af5b371a6'
MAIN_SHA='9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'
LOADER_SHA='a2d5f03fb9dec90763b238c5c499199176f1eddbf54b935475274981bc952c1c'
TRUSTED_LOADER=ROOT/'research/data_prep/wrd_curation11/curriculum_loader11.py'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def pin(p):p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}
def unique(pairs):
 d={}
 for k,v in pairs:assert k not in d;d[k]=v
 return d
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'),object_pairs_hook=unique)
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True)
def safe(root,name):
 assert isinstance(name,str)and name and not any(x in name for x in '\\:<>"|?*')and not any(ord(x)<32 or ord(x)==127 for x in name)
 p=PurePosixPath(name);assert p.as_posix()==name and not p.is_absolute()and'..'not in p.parts
 devices={'con','prn','aux','nul',*('com'+str(i)for i in range(1,10)),*('lpt'+str(i)for i in range(1,10))}
 assert all(not x.endswith((' ','.'))and x.split('.')[0].casefold()not in devices for x in p.parts)
 root=Path(root).resolve();q=root.joinpath(*p.parts);assert q.resolve().is_relative_to(root)
 for a in [q,*q.parents]:
  if a.exists():assert not a.is_symlink()and not(a.lstat().st_file_attributes&0x400)
  if a==root:break
 return q
def save(name,x):
 p=OUT/name;assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode());return pin(p)
def encoded(values,kind):
 v=array(kind,values);assert v.itemsize=={'I':4,'q':8,'f':4}[kind]
 if sys.byteorder!='little':v.byteswap()
 return v.tobytes()
def independent(row):
 ids=row['input_ids'];labels=[-100]*len(ids);weights=[0.0]*len(ids);last=0
 for a,b,c,w in row['supervision_spans']:
  assert 0<=last<=a<b<=len(ids)and 0<w<=1;last=b
  for i in range(a,b):assert labels[i]==-100;labels[i]=ids[i];weights[i]=w
 return {'input_ids':ids,'attention_mask':[1]*len(ids),'labels':labels,'loss_weights':weights}
def main():
 assert RESTORED.is_dir()and(BASE/'TRAINING_MANIFEST.json').is_file()
 assert not(OUT/'REAL_RESTORED_CURRICULUM11_QA.json').exists()
 assert ARCHIVE.stat().st_size==329185069 and sha(ARCHIVE)==ARCHIVE_SHA
 pmfile=RESTORED/'PAYLOAD_MANIFEST11.json';assert sha(pmfile)==PM_SHA
 pm=load(pmfile);assert pm['schema']=='wrd11-public-curriculum-and-audit-v1'and len(pm['files'])==4241
 with tarfile.open(ARCHIVE,'r|gz')as tf:
  first=tf.next();assert first.name=='PAYLOAD_MANIFEST11.json'and first.isfile()
  assert tf.extractfile(first).read()==pmfile.read_bytes()
 refs={};fold=set();allbytes=0
 for ref in pm['files']:
  name=ref['path'];assert name not in refs and name.casefold()not in fold
  q=safe(RESTORED,name);info=q.lstat();assert stat.S_ISREG(info.st_mode)and not(info.st_file_attributes&0x400)
  assert q.stat().st_size==ref['bytes']and sha(q)==ref['sha256'];refs[name]=ref;fold.add(name.casefold());allbytes+=ref['bytes']
 actual=set()
 for q in RESTORED.rglob('*'):
  assert not(q.lstat().st_file_attributes&0x400)and not q.is_symlink()
  if q.is_file():actual.add(q.relative_to(RESTORED).as_posix())
 assert actual==set(refs)|{'PAYLOAD_MANIFEST11.json','RESTORE_RECEIPT11.json'}
 receipt=load(RESTORED/'RESTORE_RECEIPT11.json');assert receipt['archive_sha256']==ARCHIVE_SHA and receipt['manifest_sha256']==PM_SHA and receipt['files_verified']==4241
 assert sha(BASE/'TRAINING_MANIFEST.json')==sha(ROOT/'output/20261027_wrd_main_v10/TRAINING_MANIFEST.json')==MAIN_SHA
 selection=load(RESTORED/'work/CURRICULUM_SELECTION11.json');acceptance=load(RESTORED/'work/ROOT_ACCEPTANCE11.json')
 assert selection['unique_new_targets']==627 and selection['available_unique_targets']==1250 and selection['default_process_unique_targets']==832
 assert selection['default_training_entrypoint']is None and selection['full_autonomous_WRD_ready']is False
 assert acceptance['selection']['sha256']==sha(RESTORED/'work/CURRICULUM_SELECTION11.json')
 # Exact saved/readable loader and manifests/indices must match prior reviewed
 # pins before any import. Import only the trusted workspace source copy.
 assert sha(TRUSTED_LOADER)==LOADER_SHA
 assert sha(RESTORED/'source/wrd_curation11/curriculum_loader11.py')==LOADER_SHA
 configs=[('full_native53','curriculum01','technical_qa01/ALL832_CURRICULUM_BINARY_FOUR_FEATURES_QA.json',270871920,16929495,0),
          ('budget_projection','budget_curriculum01','technical_budget_qa01/ALL832_BUDGET_ACTUAL_ARRAY_FOUR_FEATURES_QA.json',101648976,6353061,402)]
 profile_pins={}
 for profile,directory,qafile,_,_,_ in configs:
  root=RESTORED/'work'/directory;mfile=root/'CURRICULUM_MANIFEST11.json';idx=root/'canonical_arrays11/ARRAY_INDEX11.json';pfile=root/'canonical_arrays11/INDEX_PIN11.json';loader=root/'curriculum_loader11.py'
  old=load(RESTORED/'work'/qafile);assert old['status'].startswith('PASS')
  fields=('curriculum_manifest','new_index','new_pin')if profile=='full_native53'else('manifest','index','index_pin')
  for current,key in zip([mfile,idx,pfile],fields):assert sha(current)==old[key]['sha256']and current.stat().st_size==old[key]['bytes']
  s=selection['profiles'][profile];assert sha(mfile)==s['manifest_sha256']and sha(idx)==s['index_sha256']and sha(loader)==s['loader_sha256']==LOADER_SHA
  m=load(mfile);assert sha(BASE/'PAYLOAD_MANIFEST.json')==m['base_reference']['authenticated_payload_manifest_sha256']
  assert sha(BASE/'canonical_arrays10/ARRAY_INDEX10.json')==m['base_reference']['canonical_index_sha256']
  assert m['base_reference']['main_manifest_sha256']==MAIN_SHA
  profile_pins[profile]={'manifest':pin(mfile),'index':pin(idx),'index_pin':pin(pfile),'saved_loader':pin(loader),'prior_exact_QA':pin(RESTORED/'work'/qafile)}
 spec=importlib.util.spec_from_file_location('reviewed_workspace_reader_for_actual_restored11',TRUSTED_LOADER);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
 details=[];summaries={};targets={};metrics={};synthetic_paths=set();base_paths=set();base_ids=None;canaries={}
 for profile,directory,qafile,bytecount,seqcount,short in configs:
  root=RESTORED/'work'/directory;m=load(root/'CURRICULUM_MANIFEST11.json');index=load(root/'canonical_arrays11/ARRAY_INDEX11.json')
  assert index['record_count']==627 and index['binary_files']==1881 and index['binary_bytes']==bytecount
  stats=defaultdict(Counter);rounds=Counter();binaries=defaultdict(Counter);seen=set();realids=set();synids=set();targets[profile]={};metrics[profile]={};canary=None
  for pool,source,entry,row in reader.iter_records(root,BASE,pools=('real_process','synthetic')):
   ident=row['id'];assert ident==entry['id']and ident not in seen;seen.add(ident)
   wanted=independent(row);assert reader.standard(row)==wanted and reader.binary(source,entry,row)==wanted
   assert len(wanted['input_ids'])==entry['total_tokens']==row['total_tokens']and sum(l!=-100 for l in wanted['labels'])==entry['supervised_tokens']==row['supervised_tokens']
   assert all((label==-100)==(weight==0)for label,weight in zip(wanted['labels'],wanted['loss_weights']))
   count=0;actual_array_pins={}
   for key,kind,dtype in [('input_ids','I','uint32_le'),('labels','q','int64_le'),('loss_weights','f','float32_le')]:
    ref=entry['arrays'][key];p=safe(source,ref['path']);body=p.read_bytes()
    assert ref['dtype']==dtype and len(body)==ref['bytes']and hashlib.sha256(body).hexdigest()==ref['sha256']
    assert body==encoded(wanted[key],kind)
    count+=len(body);binaries[pool].update(files=1,bytes=len(body));actual_array_pins[key]=ref['sha256']
    if pool=='synthetic':assert p.resolve().is_relative_to((root/'canonical_arrays11').resolve());synthetic_paths.add(str(p.resolve()))
    else:assert p.resolve().is_relative_to((BASE/'canonical_arrays10').resolve());base_paths.add(str(p.resolve()))
   assert count==row['total_tokens']*16
   rounds[pool]+=sum(a!=b for a,b in zip(wanted['loss_weights'],array('f',wanted['loss_weights']).tolist()))
   mass=sum(Decimal(b-a)*Decimal(str(w))for a,b,_,w in row['supervision_spans'])
   metrics[profile][ident]={'pool':pool,'seq':row['total_tokens'],'pos':row['supervised_tokens'],'mass':mass}
   stats[pool].update(rows=1,seq=row['total_tokens'],positive=row['supervised_tokens'],le16k=int(row['total_tokens']<=16384),le32k=int(row['total_tokens']<=32768))
   stats[pool]['mass']+=mass
   if pool=='real_process':
    realids.add(ident);assert ident in m['base_reference']['real_process_ids']and row['bank']!='source_contract_main'
   else:
    synids.add(ident);assert row['source_ids']==[]and all(w==0.05 for _,_,_,w in row['supervision_spans'])
    user=json.loads(row['messages'][1]['content']);pos=defaultdict(list)
    for a,b,c,w in row['supervision_spans']:pos[c].extend(row['input_ids'][a:b])
    targets[profile][ident]={'target':hashlib.sha256(js(row['messages'][-1]).encode()).hexdigest(),'positive_by_component':dict(pos),
     'state':hashlib.sha256(js(user['state']).encode()).hexdigest(),'arrays':actual_array_pins,'tools':len(row['tools'])}
    if profile=='budget_projection':
     old=targets['full_native53'][ident];current=targets[profile][ident]
     assert current['target']==old['target']and current['positive_by_component']==old['positive_by_component']and current['state']==old['state']
     if row['tools']:assert current['arrays']==old['arrays']and len(row['tools'])==53
     else:assert not row['messages'][-1].get('tool_calls')and '无工具'in user['request']
    if canary is None:canary=(source,deepcopy(entry),deepcopy(row))
   details.append({'profile':profile,'id':ident,'pool':pool,'sequence_tokens':row['total_tokens'],'positive_tokens':row['supervised_tokens'],'actual_binary_bytes':count})
  assert len(seen)==832 and len(realids)==205 and len(synids)==627 and realids==set(m['base_reference']['real_process_ids'])
  if base_ids is None:base_ids=realids
  else:assert base_ids==realids
  assert stats['real_process']['seq']==2537926 and stats['real_process']['positive']==156341 and stats['real_process']['le16k']==133
  assert stats['synthetic']['seq']==seqcount and stats['synthetic']['positive']==57362 and stats['synthetic']['le16k']==short and stats['synthetic']['mass']==Decimal('2868.1')
  assert binaries['synthetic']==Counter(files=1881,bytes=bytecount)and binaries['real_process']==Counter(files=615,bytes=40606816)
  # Valid-SHA but wrong prompt label canary: mutate only a copy under DEL.
  source,entry,row=canary;folder=OUT/('bad_prompt_label_'+profile);folder.mkdir(exist_ok=False)
  for key in ['input_ids','labels','loss_weights']:
   ref=entry['arrays'][key];p=folder/(key+'.bin');shutil.copyfile(safe(source,ref['path']),p)
   if key=='labels':
    body=bytearray(p.read_bytes());assert int.from_bytes(body[:8],'little',signed=True)==-100
    body[:8]=int(row['input_ids'][0]).to_bytes(8,'little',signed=True);p.write_bytes(body)
   entry['arrays'][key]={**ref,'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}
  try:reader.binary(folder,entry,row)
  except AssertionError:canaries[profile]='REJECTED_VALID_HASH_PROMPT_LABEL_CORRUPTION'
  else:raise AssertionError('PROMPT_LABEL_CORRUPTION_NOT_REJECTED')
  summaries[profile]={'rows_read':len(seen),'counts_by_pool':{k:{a:float(b)if isinstance(b,Decimal)else b for a,b in v.items()}for k,v in stats.items()},
   'binary_by_pool':{k:dict(v)for k,v in binaries.items()},'normal_float32_rounding_difference_positions':dict(rounds),'all_four_features_exact_canonical_Python_values':True,'all_disk_bytes_SHA_and_little_endian_rounding_exact':True}
 assert len(synthetic_paths)==3762 and len(base_paths)==615 and len(targets['full_native53'])==len(targets['budget_projection'])==627
 # Final selection and all exposure ID cards are actual restored files. Recount
 # their sequence/positive/mass workload from the just-verified row metrics.
 cardpath=RESTORED/'work/exposure11_final/EXPOSURE_SCHEDULES11.json';cards=load(cardpath);exposure={}
 for mode in ['real_only','pilot','full']:
  assert cards['profiles']['full_native53'][mode]['steps']==cards['profiles']['budget_projection'][mode]['steps']
 for profile,pdata in cards['profiles'].items():
  exposure[profile]={}
  for mode in ['real_only','pilot','full']:
   card=pdata[mode];flat=[x for batch in card['steps']for x in batch];rows=[metrics[profile][x['id']]for x in flat]
   assert all(x['pool']==r['pool']for x,r in zip(flat,rows))
   assert card['sequence_exposures']==len(flat)and card['unique_targets']==len({x['id']for x in flat})
   assert card['sequence_tokens_unpadded']==sum(r['seq']for r in rows)and card['positive_tokens_exposed']==sum(r['pos']for r in rows)
   assert abs(card['weighted_mass_exposed']-float(sum(r['mass']for r in rows)))<1e-7
   if mode!='real_only':assert all(any(x['pool']=='real_process'for x in b)for b in card['steps'])
   exposure[profile][mode]={'steps':len(card['steps']),'exposures':len(flat),'unique_ids':len({x['id']for x in flat}),'seq':sum(r['seq']for r in rows),'positive':sum(r['pos']for r in rows),'mass':float(sum(r['mass']for r in rows))}
 controlpath=RESTORED/'work/exposure11_final/FULL_REAL_EXPOSURE_CONTROL11.json';control=load(controlpath);controlids=[x['id']for b in control['steps']for x in b]
 assert len(controlids)==209 and len(control['steps'])==53
 for profile in cards['profiles']:
  mixed=Counter(x['id']for b in cards['profiles'][profile]['full']['steps']for x in b if x['pool']=='real_process');assert mixed==Counter(controlids)
 assert sha(ROOT/'output/20261027_wrd_main_v10/TRAINING_MANIFEST.json')==MAIN_SHA and 'torch'not in sys.modules
 report={'schema':'wrd11-independent-fresh-actual-public-restore-QA','status':'PASS_ACTUAL_PUBLIC_RESTORE_ALL4241_FILES_BOTH1254_VIEWS3762_BINARIES_AND_BASE205_FOUR_FEATURES',
  'archive':pin(ARCHIVE),'payload_manifest':pin(pmfile),'PM_files_independently_SHA_size_verified':4241,'PM_source_bytes':allbytes,
  'exact_root_inventory_no_extra_files_except_generated_PM_and_restore_receipt':True,'physical_root_files':len(actual),
  'first_archive_member_exact_manifest':True,'strict_restore_receipt':pin(RESTORED/'RESTORE_RECEIPT11.json'),
  'trusted_workspace_loader_SHA_checked_before_import':pin(TRUSTED_LOADER),'saved_payload_source_never_executed':True,
  'two_profile_manifest_index_pin_loader_bytes_equal_prior_passed_QA':profile_pins,
  'actual_new_profile_row_visits':1254,'unique_logical_new_targets':627,'actual_new_physical_binary_files':3762,'actual_new_physical_binary_bytes':372520896,
  'original_base205_visited_each_profile':True,'unique_base_binary_files_verified':615,'base_binary_bytes':40606816,
  'default_pool_total_row_visits_both_profiles':1664,'base623_main_unchanged':MAIN_SHA,
  'profile_actual_counts':summaries,'valid_SHA_wrong_prompt_label_canaries':canaries,
  'all627_target_text_positive_token_ids_and_point_state_equal_across_profiles':True,
  'full53_retained225_physical_array_bytes_identical_between_profiles':True,
  'selection_file':pin(RESTORED/'work/CURRICULUM_SELECTION11.json'),'final_exposure_file':pin(cardpath),'final_exposure_fresh_row_accounting':exposure,
  'full_real_exposure_control':pin(controlpath),'full_control_real209_multiset_matches_both_mixed_cards':True,
  'tokenizer_rerun':False,'prior_tokenizer_proofs_preserved_by_exact_decompressed_file_SHA':True,
  'profiles_not_additional_independent_targets_or_inference_gold_router':True,'native_calls':0,'model_or_training':False,'remote_upload_verified_by_this_QA':False,
  'review_script':pin(__file__)}
 save('REAL_RESTORED_CURRICULUM11_ROW_DETAILS.json',{'rows':details})
 ref=save('REAL_RESTORED_CURRICULUM11_QA.json',report)
 print(json.dumps({'status':report['status'],'QA_sha256':ref['sha256'],'all_PM_files':4241,'new_physical_bins':3762,'new_profile_row_visits':1254,'unique_logical_new_targets':627}))
if __name__=='__main__':main()
