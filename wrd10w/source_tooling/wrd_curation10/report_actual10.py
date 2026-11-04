"""Recount the activated10 data and emit data-level, non-training statistics."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,importlib.util,json,math
ROOT=Path(__file__).resolve().parents[3];DATA=ROOT/'output/20261027_wrd_main_v10';WORK=ROOT/'output/20261031_wrd_curation10'
OUT=ROOT/'research/plans/20261031_wrd_curation10'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=ROOT/'research/data_prep/wrd_curation10/admit10.py';s=importlib.util.spec_from_file_location('actual10_count',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 manifest=load(DATA/'TRAINING_MANIFEST.json');assert sha(DATA/'TRAINING_MANIFEST.json')=='9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'
 records=[r for _,_,r in m.bank_records(DATA,manifest)];assert len(records)==623
 summary=m.recount(records);groups=summary.pop('component_by_record_id')
 assert summary['actual_counts']==manifest['actual_counts']
 def facts(rs):
  src={s for r in rs for s in r['source_ids']};counts=Counter();mass=0
  for r in rs:
   counts.update(targets=1,input_tokens=r['total_tokens'],positive_tokens=r['supervised_tokens'],le16k=int(r['total_tokens']<=16384),long16to32=int(r['total_tokens']>16384))
   mass+=sum((b-a)*w for a,b,_,w in r['supervision_spans'])
  return{**dict(counts),'source_ids':len(src),'global_connected_groups':len({groups[r['id']]for r in rs}),'weighted_positive_mass':round(mass,8)}
 contract=[r for r in records if r['bank']=='source_contract_main'];process=[r for r in records if r['bank']!='source_contract_main']
 assert len(contract)==418 and len(process)==205
 stages=Counter();stage_detail=Counter();pairs=defaultdict(list)
 for r in records:
  stage=r['stage'];cl='R_historical'if stage.startswith('historical_workflow')else stage[0]
  assert cl in ['A','B','C','D','R_historical'];stages[cl]+=1
  if r['bank']=='source_contract_main':stage_detail['A_auxiliary']+=1
  else:stage_detail[cl+'_process']+=1
  c=r['supervised_tokens_by_component'];hasR=c.get('R',0)>0;hasA=c.get('A',0)>0 or c.get('D',0)>0
  if r in process and hasR and not hasA:pairs['R_only'].append(r)
  if r in process and hasR and hasA:
   pairs['all_R_with_A_or_business_D'].append(r)
   if r['bank']in m.NATIVE_R:pairs['faithful_compatible_R_with_A_or_D'].append(r)
   elif r['bank']=='recontextualized_compat_R_process10':pairs['recontextualized_compatible_R_with_A'].append(r)
   elif r['bank']=='historical_test_oracle_repair_02':pairs['recorded_cumulative_R_with_A'].append(r)
   else:pairs['new_authored_R_with_A_or_D'].append(r)
 before=load(DATA/'manifest_history/pre_curation10_01380a42195dd888/TRAINING_MANIFEST.json')
 origin=summary['supervision_origin_tokens']
 result={'schema':'wrd10-actual-data-not-launch-configuration','status':'ACTIVATED_SCOPED_COMPONENT_MAIN_FULL_PIPELINE_NOT_READY',
  'design_revision':'5.0.52','change_id':'ALG-20261031-04','main_manifest_sha256':sha(DATA/'TRAINING_MANIFEST.json'),
  **summary,'contract':facts(contract),'process':facts(process),'all':facts(records),
  'literal_stage_targets':dict(stages),'stage_roles':dict(stage_detail),'R_pairing':{k:facts(v)for k,v in pairs.items()},
  'original_R_faithful_and_historical_tokens':origin['original_native_R_tokens']+origin['historical_original_R_tokens']+origin['recorded_cumulative_original_R_excerpt_tokens'],
  'recorded_R_recontextualized_tokens':origin['recorded_compatible_R_excerpt_recontextualized_tokens'],
  'new_authored_R_tokens':origin['new_authored_R_tokens']+origin['new_authored_source_only_controller_R_tokens'],
  'delta_from09':{'new_targets':29,'new_positive_tokens':20984,'new_input_tokens':353285,
    'withdrawn_targets':1,'withdrawn_positive_A_tokens':9905,'withdrawn_input_tokens':18040,
    'net_targets':28,'net_positive_tokens':11079,'net_input_tokens':335245,'original_R_withdrawn':0},
  'rendered_assistant_metadata_objects':sum(len(r['targets'])for r in records),
  'zero_loss_assistant_metadata_objects':sum(sum(not t['owned_supervision_spans']for t in r['targets'])for r in records),
  'max_sequence_tokens':max(r['total_tokens']for r in records),
  'candidate_component_updates':{'process_one_pass_accum4':math.ceil(len(process)/4),'contract_one_pass_accum16':math.ceil(len(contract)/16),
    'contract1_process1':math.ceil(len(contract)/16)+math.ceil(len(process)/4),'contract1_process3':math.ceil(len(contract)/16)+3*math.ceil(len(process)/4),'actually_run':False},
  'unpacked_sequence_workload':{'process_one_pass':sum(r['total_tokens']for r in process),'joint_one_pass':sum(r['total_tokens']for r in records),
    'contract1_process3':sum(r['total_tokens']for r in contract)+3*sum(r['total_tokens']for r in process),'not_GPU_hours_or_new_experience':True},
  'corpus_bound_discovery':{'baseline_native_entities':1871,'new_native_entities':6,'known_total_native_entities':1877,
    'baseline_native_assistant_owners':34616,'new_native_owners':278,'new_tail_owners':2,'known_total_native_owners':34896,
    'bounded_original_exports_crosschecked':17,'not_a_proof_of_disk_wide_completeness':True},
  'full_native_autonomy_A_D':0,'qualified_keep_skills':0,'full_wrd_student_evaluations':0,
  'unit_total_cost_per_qualified_skill':None,'cost_reason':'K=0; AI curation/CPU/energy/shared historical cost unknown is not zero',
  'full_pipeline_training_ready':False,'default_full_pipeline_training_entrypoint':None,
  'original226_isolated':True,'new_reserved_source_ids':['conv_34b56ae9c535'],
  'tokenizer_data_compatibility_both_models':True,'Spark_model_training_compatibility_verified':False,
  'new_business_calls':0,'weights_loaded':False,'training_started':False,'script_sha256':sha(__file__)}
 OUT.mkdir(parents=True,exist_ok=True)
 p=OUT/'ACTUAL_DATA_STATISTICS10.json';p.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({k:result[k]for k in ['status','actual_counts','literal_stage_targets','contract','process','R_pairing','candidate_component_updates','max_sequence_tokens']},ensure_ascii=False))
if __name__=='__main__':main()
