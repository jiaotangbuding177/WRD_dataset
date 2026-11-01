"""Fresh full joint-data read; no model, optimizer, or training computation."""
from pathlib import Path
from collections import Counter,defaultdict
from itertools import zip_longest
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261101_wrd_training_value'
DATA=ROOT/'output/wrd11publicroot01/work/budget_curriculum01';BASE=ROOT/'output/wrd10root01'
LOADER=ROOT/'research/data_prep/wrd_curation11/curriculum_loader11.py'
EXPECTED='a2d5f03fb9dec90763b238c5c499199176f1eddbf54b935475274981bc952c1c'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def save(p,x):assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def main():
 assert sha(LOADER)==EXPECTED
 spec=importlib.util.spec_from_file_location('fixed_joint_curriculum_reader11',LOADER);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
 pools=('real_process','synthetic','contract_optional')
 features=reader.iter_features(DATA,BASE,pools=pools,use_binary=True,with_metadata=True)
 records=reader.iter_records(DATA,BASE,pools=pools)
 totals=Counter();by_pool=defaultdict(Counter);by_bank=defaultdict(Counter);by_stage=defaultdict(Counter)
 comp_rows=Counter();comp_tokens=Counter();comp_pool=defaultdict(Counter);toolnames=Counter();toolpool=defaultdict(Counter)
 ids=set();call_ids=set();rowdetails=[];contract_keys=Counter();meta_source_ids=set();sources_by_pool=defaultdict(set)
 for rec,entry in zip_longest(records,features):
  assert rec is not None and entry is not None
  pool,source,index,row=rec;assert pool==entry['pool'] and row['id']==entry['id']
  assert row['id'] not in ids;ids.add(row['id'])
  f=entry['features'];n=len(f['input_ids']);assert n==row['total_tokens']<=32768
  assert set(f)=={'input_ids','attention_mask','labels','loss_weights'}
  assert all(len(v)==n for v in f.values())
  positive=0
  for tok,att,label,weight in zip(f['input_ids'],f['attention_mask'],f['labels'],f['loss_weights']):
   assert att==1 and label in {-100,tok} and ((label==-100)==(weight==0))
   assert 0<=weight<=1
   positive+=(label!=-100)
  assert positive==row['supervised_tokens']>0
  c=Counter()
  for a,b,component,w in row['supervision_spans']:c[component]+=b-a
  assert dict(c)==row['supervised_tokens_by_component'] and sum(c.values())==positive
  comps=set(c)
  for component in comps:comp_rows[component]+=1;comp_pool[pool][component]+=1
  comp_rows['R+A']+=int('R' in comps and 'A' in comps)
  comp_rows['R+D']+=int('R' in comps and 'D' in comps)
  comp_rows['R_without_A_or_D']+=int('R' in comps and not ({'A','D'}&comps))
  comp_tokens.update(c)
  calls=[]
  for target in row['targets']:
   if any(span[2]=='A' for span in target['owned_supervision_spans']):
    for call in row['messages'][target['message_index']].get('tool_calls',[]):
     assert call['id'] not in call_ids;call_ids.add(call['id']);name=call['function']['name'];toolnames[name]+=1;toolpool[pool][name]+=1;calls.append(name)
  for counter in [totals,by_pool[pool],by_bank[row['bank']],by_stage[row['stage']]]:
   counter.update(rows=1,sequence_tokens=n,positive_tokens=positive,le16k=int(n<=16384),long16to32k=int(n>16384))
   counter['weighted_mass']+=sum((b-a)*w for a,b,_,w in row['supervision_spans'])
  sources_by_pool[pool].update(row['source_ids']);meta_source_ids.update(row['source_ids'])
  if pool=='contract_optional':
   for i in row['original_record_metadata']['supervision_message_indices']:
    text=row['messages'][i].get('content','')
    try:
     parsed=json.loads(text)
     if isinstance(parsed,dict):contract_keys.update(parsed.keys())
    except json.JSONDecodeError:contract_keys['NON_JSON_TEXT']+=1
  rowdetails.append({'id':row['id'],'pool':pool,'bank':row['bank'],'stage':row['stage'],'sequence_tokens':n,'positive_tokens':positive,'components':dict(c),'positive_tool_names':calls})
 assert totals['rows']==1250 and totals['positive_tokens']==284595 and totals['sequence_tokens']==10207038
 assert totals['le16k']==941 and totals['long16to32k']==309
 assert by_pool['real_process']['rows']==205 and by_pool['contract_optional']['rows']==418 and by_pool['synthetic']['rows']==627
 assert 'torch' not in sys.modules
 qa={'schema':'wrd1250-fresh-joint-data-read-not-model-training','status':'PASS_ALL1250_JOINT_BINARY_TRAINING_FEATURES_AND_POSITIVE_LOSS_TARGETS',
 'source':{'loader':pin(LOADER),'budget_manifest':pin(DATA/'CURRICULUM_MANIFEST11.json'),'original_primary_manifest':pin(BASE/'TRAINING_MANIFEST.json')},
 'scope':'FRESH_ALL_THREE_POOLS_JOINT_READ_WITH_BINARY_TRUE_AND_ACTUAL_COMPILED_RECORD_PAIRING',
 'counts':dict(totals),'by_pool':{k:dict(v) for k,v in by_pool.items()},'unique_target_ids':len(ids),
 'four_features_all_rows_complete_and_equal_length':True,'all_rows_have_positive_loss_target':True,'all_label_values_match_input_or_ignore':True,
 'all_masks_and_weights_match_spans':True,'all_attention_masks_one_before_padding':True,'binary_SHA_LE_bytes_float32_checked_by_fixed_loader':True,
 'model_weights_loaded':False,'forward_or_backward_executed':False,'optimizer_steps_executed':0,'training_started':False,
 'does_not_claim_Spark_runtime_or_student_quality_benchmark':True,'script':pin(Path(__file__))}
 modules={'schema':'wrd1250-actual-overlapping-supervision-counts','status':'PASS_ACTUAL_COMPILED_ROWS_AND_JOINT_FEATURES_COUNTED',
 'counts':dict(totals),'by_pool':{k:dict(v) for k,v in by_pool.items()},'by_bank':{k:dict(v) for k,v in by_bank.items()},'by_stage':{k:dict(v) for k,v in by_stage.items()},
 'target_rows_with_positive_component':dict(comp_rows),'target_rows_by_pool_and_component':{k:dict(v) for k,v in comp_pool.items()},'positive_tokens_by_component':dict(comp_tokens),
 'supervised_tool_calls_total':len(call_ids),'supervised_tool_call_names':dict(toolnames),'supervised_tool_call_names_by_pool':{k:dict(v) for k,v in toolpool.items()},
 'distinct_source_ids':len(meta_source_ids),'distinct_source_ids_by_pool':{k:len(v) for k,v in sources_by_pool.items()},
 'contract_response_top_level_keys':dict(contract_keys),'overlap_notice':'R/A/D rows overlap; tool-call counts count calls, not independent skills or enterprise tasks.',
 'row_details':rowdetails,'training_started':False}
 save(OUT/'ALL1250_JOINT_TRAINABILITY_QA.json',qa);save(OUT/'MODULE_TARGET_COUNTS.json',modules)
 print(json.dumps({'status':qa['status'],'counts':dict(totals),'component_rows':dict(comp_rows),'tools':dict(toolnames),'contract_response_keys':dict(contract_keys)},ensure_ascii=False))
if __name__=='__main__':main()
