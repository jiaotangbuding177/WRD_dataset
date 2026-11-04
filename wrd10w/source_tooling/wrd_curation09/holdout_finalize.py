"""Validate and freeze exact input-only evaluation entrypoints; no token/model run."""
import collections,hashlib,json
from pathlib import Path
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation09/holdout'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(b):return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def pin(p):return {'path':str(p.relative_to(OUT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())}
catalog=read(OUT/'TASK_CATALOG_ALL36_05.json');active=[r for r in catalog if r['status']!='HOLD']
assert len(catalog)==36 and len(active)==26
assert collections.Counter(r['split'] for r in active)=={'dev':9,'test':17}
assert collections.Counter(r['task_class'] for r in active)=={'component_delivery':24,'clarification_only':2}
entries=[];materials=set();group_members=set()
for r in catalog:
 for field in ['task_input_pin','rubric_pin']:
  expected=r[field];p=OUT/expected['path'];assert pin(p)==expected,(r['task_id'],field)
 packet=read(OUT/r['task_input_pin']['path']);rubric=read(OUT/r['rubric_pin']['path'])
 assert rubric['qualified_skill_threshold'] is None and rubric['student_quality_observed'] is None
 for m in r['material_aliases']:
  p=(OUT/r['task_input_pin']['path']).parent/m['relative_path'];b=p.read_bytes()
  assert len(b)==m['bytes'] and digest(b)==m['sha256']
 if r['status']=='HOLD':continue
 assert r['evaluation_level']=='COMPONENT_OR_CONSUMPTION' and not r['eligible_for_training']
 assert packet['messages'] and all(m['role']=='user' for m in packet['messages'])
 group_members.update(r['reserved_source_ids']);materials.update(m['sha256'] for m in r['material_aliases'])
 message_bytes=json.dumps(packet['messages'],ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()
 entries.append({'task_id':r['task_id'],'split':r['split'],'title':r['title'],'task_class':r['task_class'],
  'evaluation_level':r['evaluation_level'],'source_scope_component_id':r['source_scope_component_id'],
  'reserved_source_ids':r['reserved_source_ids'],'input_packet':r['task_input_pin'],
  'messages_canonical_sha256_sorted_utf8':digest(message_bytes),
  'user_content_sha256_utf8':[digest(m['content']) for m in packet['messages']],
  'user_content_characters':sum(len(m['content']) for m in packet['messages']),
  'evaluator_only_rubric':r['rubric_pin'],'material_aliases':r['material_aliases'],
  'expected_output_kind':r['output_kind'],'mechanism':r['mechanism'],
  'business_component_TSR_denominator_eligible':r['task_class']=='component_delivery',
  'full_WRD_TSR_or_qualified_skill_denominator_eligible':False,
  'runtime_preflight_or_execution_done':False})
assert len(group_members)==28 and len(materials)==11
for split in ['dev','test']:
 file=OUT/f'{split}.tasks05.jsonl'
 parsed=[json.loads(s) for s in file.read_text(encoding='utf-8-sig').splitlines()]
 assert {r['task_id'] for r in parsed}=={r['task_id'] for r in entries if r['split']==split}
report={'schema':'wrd09-input-only-eval-entrypoint05-v1','status':'FROZEN_INPUT_CONDITIONS_ONLY_NOT_RUNTIME_READY',
 'active_catalog':pin(OUT/'TASK_CATALOG_ALL36_05.json'),
 'active_dev_index':pin(OUT/'dev.tasks05.jsonl'),'active_test_index':pin(OUT/'test.tasks05.jsonl'),
 'only_these_entrypoints_may_be_compiled_do_not_glob_history':True,
 'actual_counts':{'input_tasks':26,'dev':9,'test':17,'source_scope_groups':26,'reserved_sources':28,
  'component_delivery':24,'clarification_only':2,'actual_material_SHA_entities_mounted':11,
  'held_groups':10,'all_initial_reserved_groups':36,'all_initial_reserved_sources':40},
 'entries':entries,'holdout_reservation':pin(OUT/'holdout_reservation.json'),
 'independent_input_QA05':pin(OUT/'TASK_SEMANTIC_QA05.json'),
 'protected_request_exclusion_QA':pin(OUT/'PROTECTED_INPUT_INDEPENDENT_QA.json'),
 'known_metadata_ancestry_QA':pin(OUT/'independent_ancestry_QA.json'),
 'current569_revocation_proposal':pin(OUT/'PROTECTED_CURRENT569_REVOCATION_CLOSURE.json'),
 'no_SFT_or_gold_response':True,'input_only_labels_contract':'If compiled, every label=-100; do not add to TRAINING_MANIFEST or positive-loss banks.',
 'token_arrays_produced_by_this_script':0,'models_loaded_or_training_runs':0,
 'evaluation_level':'COMPONENT_OR_CONSUMPTION','full_WRD_autonomous_dev_test_ready':0,
 'qualified_KEEP_or_consumer_pair_evidence_created':0,
 'Q_status':'Five-dimension new rubric not calibrated; no student scores/quality outcomes. Only dev may calibrate a later frozen revision; original226/H12/static results not used.',
 'runtime_limit':'Binary inputs and artifact tasks require fixed native runtime tools/OCR/renderer/image service as applicable; none preflighted here. A readable task packet is not a successful rollout.',
 'cost_status':'AI curation happened; usage/cost UNKNOWN_NOT_ZERO. No new business Teacher/Actor calls; no weight loading/training.',
 'script_sha256':digest(Path(__file__).read_bytes())}
path=OUT/'INPUT_ONLY_EVAL_ENTRYPOINT05.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'entrypoint':pin(path),'catalog':report['active_catalog'],'dev':report['active_dev_index'],
 'test':report['active_test_index'],'actual_counts':report['actual_counts']},ensure_ascii=False))
