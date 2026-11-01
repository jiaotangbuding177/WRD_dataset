"""Prepare a one-pass course for a final reviewed native incremental bank.

Dynamic counts come only from actual active four-features. No model imports,
optimizer, forward/backward, or business programs are executed.
"""
from pathlib import Path
from decimal import Decimal
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys

sys.dont_write_bytecode=True
V1_HELPER_SHA='7ad2def36f65ba893d4da6bfd2da6d58b08b369806ebd01f1876e344c189875d'
BASELINE_CONFIG_SHA='496cf907f0f1e696aa173e60b8146eb1b0c2a72dbde8601821f8a9ef2eaeedde'
SEED=20261101
def require(value,message):
 if not value:raise ValueError(message)
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def module(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def real_quotas(capacities,number_real):
 batches=len(capacities);total=sum(capacities)
 require(0<=number_real<=total,'REAL_COUNT_EXCEEDS_CAPACITY')
 if number_real<batches:
  pure=batches-number_real
  pure_positions={((2*i+1)*batches)//(2*pure) for i in range(pure)}
  quotas=[0 if i in pure_positions else 1 for i in range(batches)]
 else:
  quotas=[1]*batches;extra=number_real-batches;remaining=total-batches;before=0
  for i,capacity in enumerate(capacities):
   after=before+capacity-1
   quotas[i]+=(after*extra)//remaining-(before*extra)//remaining if remaining else 0
   before=after
 require(sum(quotas)==number_real and all(0<=q<=c for q,c in zip(quotas,capacities)),'REAL_ALLOCATION_INVALID')
 require(sum(q==0 for q in quotas)==max(0,batches-number_real),'PURE_AUXILIARY_BATCH_COUNT_NOT_MINIMAL')
 return quotas

def process_phase(records,offset,helper):
 real=helper.order_source_balanced([r for r in records if r['pool'] in {'real_process','increment_process'}])
 auxiliary=helper.order_source_balanced([r for r in records if r['pool']=='synthetic'])
 require(len(real)+len(auxiliary)==len(records) and records,'UNKNOWN_OR_EMPTY_PROCESS_POOL')
 capacities=[min(4,len(records)-i) for i in range(0,len(records),4)]
 quotas=real_quotas(capacities,len(real));ri=ai=0;steps=[]
 for i,(capacity,nreal) in enumerate(zip(capacities,quotas)):
  naux=capacity-nreal;group=real[ri:ri+nreal]+auxiliary[ai:ai+naux];ri+=nreal;ai+=naux
  require(len(group)==capacity,'ROW_UNDERFLOW')
  summary=helper.summarise(group)
  steps.append({'phase_step_one_based':i+1,'global_step_one_based':offset+i+1,'microbatches':group,
   'actual_accumulation_count':capacity,'actual_real_process_rows':nreal,'actual_auxiliary_rows':naux,
   'valid_shifted_target_denominator':summary['valid_shifted_target_denominator'],
   'weighted_mass':summary['weighted_mass_exposed'],'synthetic_weighted_mass':summary['synthetic_weighted_mass'],
   'synthetic_fraction_of_weighted_mass':summary['synthetic_fraction_of_weighted_mass']})
 require(ri==len(real) and ai==len(auxiliary),'PROCESS_ROWS_NOT_EXHAUSTIVE')
 all_rows=[r for s in steps for r in s['microbatches']]
 return {'name':'process','accumulation_max':4,'microbatch':1,'single_pass':True,'repeat_views_to_fill_tail':False,
  'flush_final_partial_accumulation':True,'summary':helper.summarise(all_rows),'steps':steps,'optimizer_updates_candidate':len(steps),
  'ordering':'real-source components and auxiliary families separately balanced at seed20261101; minimize pure auxiliary updates; scatter unavoidable pure updates at equal-interval midpoints; spread extra real rows by remaining capacity',
  'real_rows':len(real),'auxiliary_rows':len(auxiliary),'pure_auxiliary_phase_steps':[i+1 for i,q in enumerate(quotas) if q==0],
  'minimum_pure_auxiliary_updates_without_repetition':max(0,len(steps)-len(real))}

def main():
 require(not sys.flags.optimize,'OPTIMIZED_PYTHON_REJECTED')
 parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--reference-root',type=Path,required=True)
 parser.add_argument('--base-root',type=Path,required=True);parser.add_argument('--package11-root',type=Path,required=True)
 a=parser.parse_args();root=a.root.resolve();reference=a.reference_root.resolve()
 outputs=['COURSE57_NATIVE.json','CONFIG57_NATIVE.json','COURSE_QA57_NATIVE.json','TRAINING_ENTRYPOINT57.json']
 require(root!=reference and not any((root/n).exists() for n in outputs),'NEW_ACTIVE_ROOT_AND_UNUSED_COURSE_OUTPUT_REQUIRED')
 helper_path=reference/'tooling/build_course57.py';config_path=reference/'CONFIG57_v2.json'
 require(sha(helper_path)==V1_HELPER_SHA and sha(config_path)==BASELINE_CONFIG_SHA,'BASELINE_HELPER_OR_CONFIG_CHANGED')
 helper=module(helper_path,'native57_fixed_course_helpers');loader=module(root/'tooling/active_loader57.py','native57_actual_active_loader')
 _,manifest=loader.validated_manifest(root)
 component_map=load(loader.verified(root,manifest['source_component_map']))['source_to_component']
 ledger=load(root/'ACTIVE_TARGET_LEDGER57.json')['profiles'];records={}
 for profile in manifest['profiles']:
  rows=[];pins={r['id']:r for r in ledger[profile]}
  for item in loader.iter_features(root,a.base_root,a.package11_root,profile=profile,with_metadata=True):
   f=item['features'];p=pins[item['id']];sources=[s for s in item['source_ids'] if s in component_map]
   group='enterprise:'+'|'.join(sorted({component_map[s] for s in sources})) if sources else 'declared:'+str(item['source_group_id'])
   positive=[x for x in f['labels'] if x!=-100]
   require(len(positive)==p['positive_tokens'] and helper.token_sha(positive)==p['positive_token_ids_sha256_u32le'],'POSITIVE_PAYLOAD_DIFFERS_FROM_ACTUAL_LEDGER')
   rows.append({'id':item['id'],'pool':item['pool'],'stage':item['stage'],'bank':item['bank'],'ordering_group':group,
    'sequence_tokens':len(f['input_ids']),'positive_tokens':len(positive),'valid_shifted_target_count':sum(x!=-100 for x in f['labels'][1:]),
    'weighted_mass':str(sum((Decimal(str(w)) for x,w in zip(f['labels'],f['loss_weights']) if x!=-100),Decimal(0))),
    'positive_token_ids_sha256_u32le':p['positive_token_ids_sha256_u32le'],'positive_by_component':p['positive_by_component']})
  records[profile]=rows
 course={'schema':'wrd57-final-native-increment-mixed-single-pass-course-not-launcher','design_revision':'5.0.57','seed':SEED,
  'actual_counts_only_not_draft_estimates':True,'profiles_are_mutually_exclusive':True,'same_adapter_and_optimizer_across_phases':True,
  'previous1227_course_immutable':True,'profiles':{},'training_started':False}
 oldcourse=load(reference/'COURSE57_v2.json')
 for profile,rows in records.items():
  contract=[r for r in rows if r['pool']=='contract_optional'];process=[r for r in rows if r['pool']!='contract_optional']
  p1=helper.make_phase(contract,'contract',16,0);p2=process_phase(process,len(p1['steps']),helper)
  require(p1==oldcourse['profiles'][profile]['phases'][0],'UNCHANGED_CONTRACT_ORDER_DIFFERS')
  steps=p1['steps']+p2['steps'];ordered=[r for s in steps for r in s['microbatches']]
  require(len(ordered)==len({r['id'] for r in ordered})==len(rows),'REPEATED_OR_OMITTED_ACTIVE_ID')
  require(not set(manifest['excluded_original_primary_ids'])&{r['id'] for r in ordered},'REVOKED_ID_IN_NATIVE_COURSE')
  summary=helper.summarise(ordered)
  require(summary['synthetic_fraction_of_weighted_mass']<=.2 and p2['summary']['synthetic_fraction_of_weighted_mass']<=.2,'GLOBAL_AUXILIARY_MASS_CAP')
  fractions=[s['synthetic_fraction_of_weighted_mass'] for s in p2['steps']]
  course['profiles'][profile]={'active_manifest_sha256':sha(root/'ACTIVE_DATASET_MANIFEST57.json'),'phases':[p1,p2],
   'summary':summary,'optimizer_updates_candidate':len(steps),'phase_tail_microbatches':[len(p1['steps'][-1]['microbatches']),len(p2['steps'][-1]['microbatches'])],
   'batch_mass_audit':{'process_batches':len(p2['steps']),'batches_with_real_process':sum(s['actual_real_process_rows']>0 for s in p2['steps']),
    'pure_auxiliary_batches':len(p2['pure_auxiliary_phase_steps']),'pure_auxiliary_phase_steps':p2['pure_auxiliary_phase_steps'],
    'local_synthetic_fraction_over20percent_batches':sum(x>.2 for x in fractions),'local_synthetic_fraction100percent_batches':sum(x==1 for x in fractions),
    'max_local_synthetic_fraction':max(fractions),'global20percent_is_not_a_local_cap_or_gradient_claim':True}}
 order=lambda p:[[r['id'] for r in s['microbatches']] for phase in course['profiles'][p]['phases'] for s in phase['steps']]
 names=list(course['profiles']);require(order(names[0])==order(names[1]),'CROSS_PROFILE_BATCH_IDS_DIFFER')
 selected=course['profiles'][manifest['default_profile']];config=load(config_path)
 config.update({'schema':'wrd57-final-native-increment-sft-config-not-launcher','course_version':'native_increment',
  'dataset_manifest_sha256':sha(root/'ACTIVE_DATASET_MANIFEST57.json'),'course_file':'COURSE57_NATIVE.json',
  'phases':[{'name':p['name'],'unique_targets':p['summary']['unique_targets'],'sequence_exposures':p['summary']['sequence_exposures'],
    'accumulation_max':p['accumulation_max'],'optimizer_updates_candidate':len(p['steps']),'last_partial_flushed':True} for p in selected['phases']],
  'candidate_optimizer_updates':selected['optimizer_updates_candidate'],'unique_targets':selected['summary']['unique_targets'],
  'candidate_sequence_exposures':selected['summary']['sequence_exposures'],'positive_tokens_exposed':selected['summary']['positive_tokens_exposed'],
  'candidate_checkpoint_global_steps':[p['steps'][-1]['global_step_one_based'] for p in selected['phases']],
  'process_batch_mixing':selected['batch_mass_audit'],'baseline1227_config_sha256':BASELINE_CONFIG_SHA})
 save(root/'COURSE57_NATIVE.json',course);config['course_sha256']=sha(root/'COURSE57_NATIVE.json');save(root/'CONFIG57_NATIVE.json',config)
 shutil.copyfile(Path(__file__),root/'tooling/build_course57_native.py')
 qa={'status':'PASS_ACTUAL_NATIVE_INCREMENT_COURSE_ALL_IDS_ONCE_BOTH_PROFILES_IDENTICAL','actual_four_features_reread':True,
  'course_sha256':sha(root/'COURSE57_NATIVE.json'),'config_sha256':sha(root/'CONFIG57_NATIVE.json'),'source_sha256':sha(Path(__file__)),
  'actual_profiles':{p:{k:v[k] for k in ['summary','optimizer_updates_candidate','phase_tail_microbatches','batch_mass_audit']} for p,v in course['profiles'].items()},
  'old1227_config_unchanged':sha(config_path)==BASELINE_CONFIG_SHA,'student_model_loaded':False,'optimizer_updates_executed':0,'training_started':False}
 save(root/'COURSE_QA57_NATIVE.json',qa)
 ref=lambda n:{'path':n,'bytes':(root/n).stat().st_size,'sha256':sha(root/n)}
 save(root/'TRAINING_ENTRYPOINT57.json',{'schema':'wrd57-final-native-increment-entrypoint-not-launcher','design_revision':'5.0.57',
  'dataset_manifest':ref('ACTIVE_DATASET_MANIFEST57.json'),'dataset_pin':ref('ACTIVE_DATASET_PIN57.json'),'loader':ref('tooling/active_loader57.py'),
  'course':ref('COURSE57_NATIVE.json'),'config':ref('CONFIG57_NATIVE.json'),'course_QA':ref('COURSE_QA57_NATIVE.json'),
  'default_profile':manifest['default_profile'],'profiles_are_mutually_exclusive':True,'unique_targets':selected['summary']['unique_targets'],
  'positive_tokens':selected['summary']['positive_tokens_exposed'],'candidate_optimizer_updates':selected['optimizer_updates_candidate'],
  'training_execution_authorized':False,'training_started':False})
 print(json.dumps({'status':qa['status'],'profiles':qa['actual_profiles'],'course_sha256':qa['course_sha256'],'training_started':False}))

if __name__=='__main__':main()
