"""Bind final17 scan, actual compiled report and recovered image bytes.
Only writes the new follow-up audit directory; no sealed tree mutation.
"""
import ast,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation09';OUT=WORK/'protection_followup09';HOLD=WORK/'holdout'
def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt',encoding='utf-8-sig')]
def pin(p):p=p.resolve();return {'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
basis_path=ROOT/'research/data_prep/wrd_curation09/holdout_protected_vs_train.py';tree=ast.parse(basis_path.read_text(encoding='utf-8-sig'));prefix=[]
for n in tree.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='manifest' for t in n.targets):break
 prefix.append(n)
environment={'__file__':str(basis_path)};exec(compile(ast.Module(body=prefix,type_ignores=[]),str(basis_path),'exec'),environment)
forbidden=environment['forbidden'];bindings=environment['bindings']
prepared=WORK/'compiled_followup_final01/CANDIDATES_STAGING_NOT_MAIN.jsonl.gz'
compiled=WORK/'compiled_followup_final01/compiled02/COMPILATION_REPORT.json';scanpath=OUT/'FINAL17_01_ISOLATION_SCAN.json'
scan=read(scanpath);assert pin(prepared)==scan['prepared_pin'] and scan['compiled_actual_messages_checked']==17
report=read(compiled);assert report['counts']['targets']==17
assert {x['path']:x['sha256'] for x in scan['compiled_file_pins']}=={str((compiled.parent/f['path']).relative_to(ROOT)).replace('\\','/'):f['sha256'] for f in report['files']}
dataset=rows(prepared);material_QA=[];all_reserved=read(HOLD/'holdout_reservation.json')
eval_catalog=read(HOLD/'TASK_CATALOG_ALL36_05.json');eval_materials={m['sha256'] for t in eval_catalog if t['status']!='HOLD' for m in t['material_aliases']}
initial_materials={m['sha256'] for m in read(HOLD/'MATERIAL_RECOVERY_AND_ANCESTRY.json')['materials']}
for record in dataset:
 for material in record.get('execution_material_dependencies',[]):
  expected=material['sha256'];restored=Path(material['restored_path']);original=Path(material['actual_historical_workspace_path'])
  assert restored.is_file() and original.is_file()
  assert restored.stat().st_size==original.stat().st_size==material['bytes']
  assert sha(restored.read_bytes())==sha(original.read_bytes())==expected==material['restored_sha256']
  matches=[]
  for sid,b in bindings.items():
   for i,m in enumerate(b['materials']):
    if m.get('sha256')==expected:
     path=Path(m['path']);assert path.is_file() and sha(path.read_bytes())==expected
     matches.append({'source_id':sid,'material_binding_index':i,'binding':m,'actual_source_file_pin':pin(path),
      'source_in_known_protected_ancestry':sid in forbidden,'source_reserved_for_new_holdout':sid in set(all_reserved['reserved_source_ids'])})
  assert matches and all(not x['source_in_known_protected_ancestry'] and not x['source_reserved_for_new_holdout'] for x in matches)
  assert expected not in eval_materials and expected not in initial_materials
  packet=read(Path(record['source_context']['path']));target=packet['original_context']['messages'][record['original_message_index']]
  target_json=json.dumps(target,ensure_ascii=False)
  material_QA.append({'candidate_id':record['id'],'material':material,'restored_actual_pin':pin(restored),
   'original_actual_workspace_pin':{'path':str(original),'bytes':original.stat().st_size,'sha256':sha(original.read_bytes())},
   'all1107_binding_SHA_occurrences':matches,'active_eval11_material_SHA_intersection':False,
   'initial_reserved49_material_SHA_intersection':False,
   'original_target_has_declared_native_path_literal':material['original_native_path'] in target_json,
   'scope_limit':'Exact byte identity and recorded producer binding only; no assertion that visual similarity or arbitrary unrecorded ancestry was exhaustively checked.'})
assert len(material_QA)==1 and material_QA[0]['material']['sha256']=='6619dbb5d40d092b9a6048b49321e593e90eb4a2e69f55b8a43606c2af30ceb1'
matches=[r for r in scan['rows'] if any(r[k] for k in ['protected_user_original_prefix_matches','eval26_original_prefix_matches','protected_user_new_state_matches','eval26_new_state_matches'])]
assert len(matches)==1 and matches[0]['owner_id']=='ac76ab7ead15378debb0e555'
all_anchors={a['text'] for r in matches for key in ['protected_user_original_prefix_matches','protected_user_new_state_matches'] for m in r[key] for a in m['anchors']}
assert len(all_anchors)==2 and all('trustedlocalEvomindskillcontents' in a for a in all_anchors)
assert all(not r['eval26_original_prefix_matches'] and not r['eval26_new_state_matches'] for r in scan['rows'])
qa={'schema':'wrd09-final17-isolation-binding-and-image-identity-v1','status':'PASS_CAPTURED_LONG_TEXT_AND_KNOWN_IMAGE_BYTE_ISOLATION_ONLY',
 'scan_pin':pin(scanpath),'prepared_pin':pin(prepared),'actual_compilation_report_pin':pin(compiled),
 'actual_compilation_counts':report['counts'],'compiled_messages_compared':17,
 'raw_inputs_v2_pins':[pin(WORK/'process/batch02/SCOPED_CANDIDATES_FINAL14_v2.jsonl.gz'),pin(WORK/'process/batch02/SCOPED_ADDITIONAL_CANDIDATES03_v2.jsonl.gz')],
 'protected_private_business_long_text_matches':0,'eval26_long_text_matches':0,
 'generic_only_match':{'owner_id':matches[0]['owner_id'],'classification':'REUSED_PROMPTGUARD_WRAPPER_NO_PRIVATE_BUSINESS_CONTENT_IN_MATCHED_RANGE',
  'actual_distinct_anchor_count':2,'anchor_sha256':[sha(a) for a in sorted(all_anchors)],
  'original_prefix_matched_message_indices':sorted({m['message_index'] for m in matches[0]['protected_user_original_prefix_matches']}),
  'new_state_matched_message_indices':sorted({m['message_index'] for m in matches[0]['protected_user_new_state_matches']})},
 'actual_recovered_image_QA':material_QA,'images_executed_or_recreated_by_this_review':False,
 'scope_limit':'Exact known text/byte evidence, not proof against paraphrase, unknown resource producers or uncaptured system. No whole-WRD or quality efficacy claim.',
 'sealed_holdout_manifest_pin':pin(HOLD/'MANIFEST.json'),'sealed_eval_array_manifest_pin':pin(WORK/'eval_input_arrays09/MANIFEST.json'),
 'main_manifest_modified':False,'protected_results_or_thought_used_to_change_Q':False,'training_or_model_started':False,
 'script_pin':pin(Path(__file__).resolve())}
path=OUT/'FINAL17_ACCEPTANCE_BINDING_AND_IMAGE_QA.json';assert not path.exists();path.write_bytes((json.dumps(qa,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps({'pin':pin(path),'prepared':qa['prepared_pin'],'compiled_report':qa['actual_compilation_report_pin'],
 'private_matches':0,'eval_matches':0,'image6619_byte_identity':True,'target_literal':material_QA[0]['original_target_has_declared_native_path_literal']},ensure_ascii=False))
