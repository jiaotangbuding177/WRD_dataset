"""Machine-consumable proposed revocation closure; never changes main data."""
import collections,gzip,hashlib,json
from pathlib import Path
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation09/holdout';MAIN=ROOT/'output/20261027_wrd_main_v10'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt',encoding='utf-8-sig')]
def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def pin(p):return {'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
manifest=read(MAIN/'TRAINING_MANIFEST.json');records=[r for f in manifest['actual_train_files'] for r in rows(MAIN/f['path'])]
pool={r['source_id']:r for r in rows(MAIN/'clean_inputs/source_pool.with_body.jsonl.gz')}
audit_path=OUT/'PROTECTED_ORIGINAL_USER_VS_CURRENT569_AND_STAGING.json';audit=read(audit_path)
private_seeds={'conv_66a8dc558785','conv_a96d4e307332','conv_b4bfa1b742fd','conv_c72721b62d56','conv_d85b915effeb','conv_e0cc09d72959','conv_e497d1970d81','conv_7ba0e0439045'}
scope_groups={pool[s]['source_group_id'] for s in private_seeds}
closure_sources={s for s,r in pool.items() if r['source_group_id'] in scope_groups}
assert len(private_seeds)==8 and len(scope_groups)==8 and len(closure_sources)==9
selected=[r for r in records if closure_sources.intersection(r['source_ids'])]
assert len(selected)==23
direct=[r for r in audit['matches'] if private_seeds.intersection(r['current_source_ids'])]
direct_ids={r['current_record_id'] for r in direct};assert len(direct_ids)==15
generic=[r for r in audit['matches'] if r['current_record_id'] not in direct_ids]
generic_ids={r['current_record_id'] for r in generic};assert len(generic_ids)==7
counts=collections.Counter();view_rows=[]
for r in selected:
 md=r['original_record_metadata'];counts['targets']+=1;counts['supervised_tokens']+=r['supervised_tokens'];counts['input_tokens']+=r['total_tokens']
 counts.update({k:v for k,v in r['supervised_tokens_by_component'].items()})
 view_rows.append({'view_id':r['id'],'source_ids':r['source_ids'],'source_group_id':r['source_group_id'],'bank':r['bank'],'stage':r['stage'],
  'owner_id':md.get('owner_id'),'original_recorded_action_owner':md.get('original_recorded_action_owner'),
  'original_episode_id':md.get('original_episode_id'),'original_message_index':md.get('original_message_index'),
  'target_original_code_sha256':md.get('target_original_code_sha256'),'output_content_provenance':md.get('output_content_provenance'),
  'source_context':md.get('source_context'),'original_R_supervised':md.get('teacher_original_R_supervised',False),
  'rationale_provenance':md.get('rationale_provenance'),'supervised_tokens':r['supervised_tokens'],
  'supervised_tokens_by_component':r['supervised_tokens_by_component'],'input_tokens':r['total_tokens'],
  'revocation_basis':'DIRECT_EXACT_PRIVATE_USER_INPUT_RECEIVED' if r['id'] in direct_ids else 'CONSERVATIVE_EXISTING_SOURCE_SCOPE_AND_RECORDED_RESOURCE_DERIVATION_CLOSURE',
  'actual_direct_private_input_match_receipts':[m for m in direct if m['current_record_id']==r['id']]})
assert (counts['supervised_tokens'],counts['input_tokens'],counts['R'],counts['A'],counts['D'],counts['F'])==(14727,238388,79,10782,3758,108)
entry_path=ROOT/'output/20261026_wrd_dataset_v9/coordination/entrypoint_controller.native_paths.source_closed.jsonl.gz'
entry_receipts=[]
for i,e in enumerate(rows(entry_path),1):
 if {'conv_4dff386a54ac','conv_e497d1970d81'}<=set(e.get('source_ids',[])):
  entry_receipts.append({'physical_line':i,'id':e['id'],'source_id':e['source_id'],'source_ids':e['source_ids'],
   'source_group_id_original_field':e['source_group_id'],'canonical_row_SHA256':sha(json.dumps(e,ensure_ascii=False,separators=(',',':'),sort_keys=True)),
   'edge_type':'FROZEN_DECLARED_CONTENT_SOURCE_IDS_JOIN_NOT_SHARED_PRIVATE_FILE_OR_SAME_ORIGINAL_GROUP'})
assert len(entry_receipts)==1
origins={}
for m in direct:
 o=m['source_origin'];origins[o['protected_source_id']]= {k:o[k] for k in ['protected_source_id','direct_original226','direct_H12','direct_old_static','protected_by_known_ancestry']}
report={'schema':'wrd09-proposed-current569-private-input-revocation-closure-v1',
 'status':'READY_FOR_ROOT_REBASE_REVIEW_MAIN_NOT_MODIFIED','main_manifest_pin':pin(MAIN/'TRAINING_MANIFEST.json'),
 'direct_scan_pin':pin(audit_path),'script_pin':pin(Path(__file__).resolve()),
 'private_seed_source_ids':sorted(private_seeds),'revoke_source_ids':sorted(closure_sources),
 'revoke_source_scope_component_ids':sorted(scope_groups),
 'revoke_current_view_ids':sorted(r['id'] for r in selected),
 'revoke_original_recorded_action_owners':sorted({r['original_record_metadata']['original_recorded_action_owner'] for r in selected if r['original_record_metadata'].get('original_recorded_action_owner')}),
 'revoke_positive_owner_ids':sorted({r['original_record_metadata']['owner_id'] for r in selected}),
 'direct_private_hit_view_ids':sorted(direct_ids),'direct_private_views':15,
 'conservative_additional_component_or_resource_views':8,
 'current_training_source_scope_groups':[{'source_scope_component_id':g,'full_source_members':sorted(s for s,r in pool.items() if r['source_group_id']==g)} for g in sorted(scope_groups)],
 'e497_4dff_join_receipt':{'file_pin':pin(entry_path),'entries':entry_receipts,
  'limit':'The two sources have different original leakage groups and neither has authentic material refs. This is a frozen declared-source edge; no claim that4dff directly read the protected business JD. Conservative whole-component policy extends revocation.'},
 'protected_seed_origin_types':list(origins.values()),'views':view_rows,'revoked_counts':dict(counts),
 'bank_counts':dict(collections.Counter(r['bank'] for r in selected)),
 'original_R_tokens_in_identified_closure':0,'new_authored_R_tokens_in_identified_closure':79,
 'native_CV_process_views_in_identified_closure':0,
 'no_literal_originalR_or_CV_hit_does_not_prove_every_unknown_ancestor_clean':True,
 'generic_match_current_view_ids_not_automatically_revoked':sorted(generic_ids),
 'generic_classes':{'conv_27a5d2df0f04':'PromptGuard wrapper','conv_f4b82e638325':'PromptGuard wrapper',
  'conv_2d8b571e6392':'law persona/instruction template','conv_fbf6d789df0f':'law persona/instruction template',
  'conv_c4d47b40b366':'recruiting persona template','conv_d416261a283e':'recruiting persona template',
  'conv_61034c4c6675':'generic image API flower example with masked authorization, no proof of public provenance added'},
 'arithmetic_only_if_root_revokes_exact23_before_any_new_data':{'targets':546,'supervised_tokens':162835,'input_tokens':3258561},
 'not_a_new_active_manifest':True,'main_changed_by_this_script':False,'training_started':False,
 'no_protected_assistant_thought_or_eval_result_used_for_new_labels_or_Q':True}
path=OUT/'PROTECTED_CURRENT569_REVOCATION_CLOSURE.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pin':pin(path),'sources':len(closure_sources),'view_ids':len(selected),'counts':dict(counts),
 'original_action_owners':report['revoke_original_recorded_action_owners'],'generic_keep_pending':len(generic_ids)},ensure_ascii=False))
