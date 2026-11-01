"""Audit actual active provenance, source units and unchanged baseline. CPU only."""
from pathlib import Path
from decimal import Decimal
import argparse
import collections
import hashlib
import importlib.util
import json
import re
import sys

sys.dont_write_bytecode=True
def require(value,message):
 if not value:raise ValueError(message)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def module(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def source_counts(records):
 return {'targets':len(records),'positive_tokens':sum(r['positive_tokens'] for r in records),
  'enterprise_source_ids':len({s for r in records for s in r['enterprise_source_ids']}),
  'actual_identity_components57':len({s for r in records for s in r['recorded_identity_source_components']}),
  'original_source_group_labels_separate_unit':len({r['source_group_id'] for r in records})}
def entities(records):return {s for r in records for s in r['enterprise_source_ids']}
def components(records):return {s for r in records for s in r['recorded_identity_source_components']}

def main():
 require(not sys.flags.optimize,'OPTIMIZED_PYTHON_REJECTED')
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--baseline-root',type=Path,required=True)
 p.add_argument('--base-root',type=Path,required=True);p.add_argument('--package11-root',type=Path,required=True)
 p.add_argument('--before-inventory',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();root=a.root.resolve();baseline=a.baseline_root.resolve();a.out.mkdir(parents=True,exist_ok=True)
 old_inventory=load(a.before_inventory);old_files={p.relative_to(baseline).as_posix():p for p in baseline.rglob('*') if p.is_file()}
 require(set(old_files)=={r['path'] for r in old_inventory['files']},'BASELINE1227_FILESET_CHANGED')
 for r in old_inventory['files']:
  f=old_files[r['path']];require(f.stat().st_size==r['bytes'] and sha(f)==r['sha256'],'BASELINE1227_FILE_BYTES_CHANGED')
 loader=module(root/'tooling/active_loader57.py','native57_source_provenance_loader');_,manifest=loader.validated_manifest(root)
 ledger=load(root/'ACTIVE_TARGET_LEDGER57.json')['profiles'];prior=load(baseline/'ACTIVE_TARGET_LEDGER57.json')['profiles']
 profile=manifest['default_profile'];allrows=ledger[profile];oldrows=prior[profile]
 process=[r for r in allrows if r['pool'] in {'real_process','increment_process'}]
 oldprocess=[r for r in oldrows if r['pool'] in {'real_process','increment_process'}]
 original1206process=[r for r in oldrows if r['pool']=='real_process']
 require(entities(allrows)==entities(oldrows) and components(allrows)==components(oldrows),'BFC_SAME_SOURCE_DEEPENING_MUST_NOT_ADD_ENTERPRISE_SOURCE')
 require(entities(process)==entities(oldprocess) and components(process)==components(oldprocess),'BFC_SAME_PROCESS_SOURCE_MUST_NOT_ADD_GROUP')
 bfc_ids={v for b in manifest['incremental_banks'] if b['bank_id']=='bfc_native_producer57' for v in b['active_ids']}
 require(bfc_ids and not bfc_ids&{r['id'] for r in oldrows},'BFC_NEW_TARGET_IDS_INVALID')
 stage=collections.Counter();positive=collections.Counter();weights=collections.Counter();all_weights=collections.Counter();provider_chars=0
 sessions=set();request_ids=set();bfc_rows=[];bank_positive=collections.Counter();pool_positive=collections.Counter()
 for pool,source,entry,row in loader.iter_records(root,a.base_root,a.package11_root,profile=profile):
  for lo,hi,component,weight in row['supervision_spans']:
   all_weights[str(weight)]+=hi-lo;bank_positive[(row['bank'],component)]+=hi-lo;pool_positive[(pool,component)]+=hi-lo
  if row['id'] not in bfc_ids:continue
  bfc_rows.append(row);m=row['original_record_metadata'];assistant=row['messages'][-1];R=assistant.get('reasoning_content','')
  require(m['training_admitted'] and m['root_main_admission'] and not m['draft_requires_root_state_dependency_review'],'FINAL_BANK_NOT_ADMITTED')
  require(m['original_provider_R_kept_unmodified_including_whitespace'] and len(R)==m['original_provider_R_characters'] and hashlib.sha256(R.encode()).hexdigest()==m['original_provider_R_sha256'],'ORIGINAL_PROVIDER_R_NOT_EXACT')
  require(m['new_authored_R_tokens']==0 and m['native_original_R_characters']==0,'WRONG_R_ORIGIN_CLASS')
  require(not m['future_consumer_Q_inserted'] and not m['whole_skill_KEEP_or_utility_approved'],'FUTURE_UTILITY_INSERTED')
  require(row['source_ids']==['conv_bfc446b95374'],'UNEXPECTED_NATIVE_SOURCE')
  feature=loader.immutable_module(root/'tooling/immutable_curriculum_loader11.py').binary(source,entry,row)
  loader.validate_features(row,feature)
  require(all(w==.25 for l,w in zip(feature['labels'],feature['loss_weights']) if l!=-100),'NEW_NATIVE_POSITIVE_WEIGHTS_NOT025')
  provider_chars+=len(R);sessions.add(m['cross_layer_identity']['native_session_id']);request_ids.add(m['cross_layer_identity']['provider_request_id'])
  stage[row['stage'].split('_',1)[0]]+=1
  for lo,hi,component,weight in row['supervision_spans']:positive[component]+=hi-lo;weights[str(weight)]+=hi-lo
 require(len(bfc_rows)==len(bfc_ids) and len(sessions)==1 and len(request_ids)==len(bfc_ids),'NATIVE_ROW_EXPERIENCE_UNIT_MISMATCH')
 # Raw source chain verification was performed separately; aggregate only that
 # one identified V0→V1 smoke-driver revision, not every edit/window as a chain.
 source_review=root.parents[1]/'bfc_semantic_review57/RESOURCE_AND_TEST_EVIDENCE57.json'
 require(source_review.is_file(),'MISSING_INDEPENDENT_VERSION_CHAIN_QA')
 version_review=load(source_review);require(version_review['generator_no_change_between_v0_v1'] and version_review['v0_files']==version_review['v1_files']==7,'VERSION_EVIDENCE_DIFFERS')
 require({r['relative'] for r in version_review['files'] if not r['equal']}=={'SKILL.md','scripts/smoke_test.py'},'REVISION_UNIT_IS_NOT_EXPECTED_VERSION_PAIR')
 origin={'baseline1227_R_component_mixed_origin_unchanged':sum(r['positive_by_component'].get('R',0) for r in oldrows),
  'baseline_origin_notice':'Original reasoning, recontextualized original reasoning and explicit author reasoning remain separately traceable in certified10/11; this audit does not relabel their mixed total as original native CoT.',
  'new_native_bank':{'origin':'ORIGINAL_PROVIDER_P_REASONING_EXPLICITLY_RECONTEXTUALIZED_IN_NEW_AUTHORED_CAUSAL_STATE',
   'original_provider_R_characters_preserved':provider_chars,'original_provider_R_positive_tokens':positive['R'],
   'original_native_persisted_R_positive_tokens':0,'new_authored_R_positive_tokens':0,'positive_weight':.25,
   'positive_tokens_by_component':dict(positive),'positive_weight_histogram':dict(weights)},
  'active_total_R_component_tokens':sum(r['positive_by_component'].get('R',0) for r in allrows),
  'characters_are_not_tokens':True,'no_unknown_bank_fallback_to_new_author_R':True}
 independent={'all_TRAIN_including_contracts':source_counts(allrows),
  'real_process_plus_reviewed_increment_only_excluding_contracts_and_auxiliary':source_counts(process),
  'baseline1227_real_process_pool':source_counts(oldprocess),'original1206_real_process_pool':source_counts(original1206process),
  'native_bfc_deepening_relative_to1227':{'new_targets':len(bfc_rows),'new_source_ids':len(entities(process)-entities(oldprocess)),
    'new_identity_components':len(components(process)-components(oldprocess))},
  'all_increment57_relative_to_original1206_process':{'new_source_ids':len(entities(process)-entities(original1206process)),
    'new_identity_components':len(components(process)-components(original1206process))},
  'verified_current_native_collection_experiences':{'complete_producer_parent_chains':len(sessions),'versioned_resource_revision_chains':1,
    'fault_repair_regression_subchains_within_that_one_version_chain':2,'native_sessions':sorted(sessions),
    'definition':'One real completed bfc producer parent; V0→V1 changes the smoke-test resource with observed sub_dept and relative-URL faults, actual fixes and regressions. Not 33 tasks, not 33 sources, and not a qualified whole-skill utility result.',
    'legacy_partial_window_rows_not_reclassified_as_complete_parents_by_this_count':True},
  'bfc_source_already_among_prior_five_increment57_groups':True,'synthetic_auxiliary_families_are_not_enterprise_sources':True}
 save(a.out/'SOURCE_UNITS_AND_REASONING_ORIGIN57.json',{'status':'PASS_ACTUAL_SOURCE_COMPONENT_SETS_AND_ORIGINAL_PROVIDER_R_MASK_ORIGIN','independence':independent,'reasoning_origin':origin,
  'native_stage_counts':dict(stage),'all_actual_span_weight_histogram':dict(all_weights),
  'baseline1227_all_files_unchanged':len(old_files),'baseline_inventory_sha256':sha(a.before_inventory),
  'source_chain_evidence_sha256':sha(source_review),'active_manifest_sha256':sha(root/'ACTIVE_DATASET_MANIFEST57.json'),
  'consumer_Q_read_or_used':False,'whole_skill_utility_credit':False,'training_started':False})
 print(json.dumps({'status':'PASS_SOURCE_UNITS_ORIGINAL_PROVIDER_R_AND_BASELINE_IMMUTABILITY','independence':independent,'reasoning_origin':origin,'old_files_unchanged':len(old_files)}))

if __name__=='__main__':main()
