"""Freeze a conservative holdout exclusion reservation before further curation.

This is not qualification of task completeness or closed resource ancestry.
"""
import gzip, hashlib, json
from pathlib import Path

ROOT=Path('D:/skillloop')
OUT=ROOT/'output/20261031_wrd_curation09/holdout'
REG=ROOT/'output/20261031_wrd_readiness_plan/reviews/source_registry_current569.json'
POOL=ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_pool.with_body.jsonl.gz'
SCOPE=ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz'
MAN=ROOT/'output/20261027_wrd_main_v10/TRAINING_MANIFEST.json'

def rows(path):
 with gzip.open(path,'rt',encoding='utf-8-sig') as f:return [json.loads(s) for s in f]
def pin(path):
 b=path.read_bytes();return {'path':str(path.relative_to(ROOT)).replace('\\','/'),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

registry=json.loads(REG.read_text(encoding='utf-8-sig'))
metadata={r['source_id']:r for r in registry['remaining_source_metadata']}
pool={r['source_id']:r for r in rows(POOL)}
assert len(metadata)==387
groups={}
for r in metadata.values():groups.setdefault(r['source_scope_component_id'],[]).append(r['source_id'])
assert len(groups)==378
material_groups=sorted({r['source_scope_component_id'] for r in metadata.values() if r['authentic_material_metadata_refs']})
assert len(material_groups)==17
text_ids=['conv_007d40b3886f','conv_0400aac342b0','conv_08457c6c88dc','conv_12ac99dd2fa7','conv_15f0f4d89d3f','conv_24de551a33dd','conv_24e59c8da83e','conv_2dff0a98f3d5','conv_2e1d20b1fc34','conv_30474e7027ac','conv_3a27f499e502','conv_589813f393e6','conv_9bc7947f7ce1','conv_b0766d5cdf61','conv_dd0ca1b95895','conv_ca2369adba0b','conv_874f133d1919','conv_2670b00882a9','conv_143452559f75']
text_groups=sorted({metadata[s]['source_scope_component_id'] for s in text_ids})
assert len(text_groups)==19 and not set(text_groups)&set(material_groups)
selected=material_groups+text_groups
used=set(registry['current569_used_source_ids'])
used_groups={r['source_group_id'] for s,r in pool.items() if s in used}
assert len(used)==284
all_reserved={s for g in selected for s in groups[g]}
assert not all_reserved&used and not set(selected)&used_groups
all_material_sha={m['sha256'] for s in all_reserved for m in pool[s]['authentic_materials']}
used_material_sha={m['sha256'] for s in used for m in pool[s]['authentic_materials']}
assert not all_material_sha&used_material_sha
order=lambda g:hashlib.sha256(('wrd09-reservation-v1|'+g).encode()).hexdigest()
dev=set(sorted(material_groups,key=order)[:6]+sorted(text_groups,key=order)[:6])
assert len(dev)==12
entries=[]
for g in sorted(selected):
 ids=sorted(groups[g])
 entries.append({'source_scope_component_id':g,'split':'dev' if g in dev else 'test',
   'source_ids':ids,'categories':sorted({metadata[s]['category'] for s in ids}),
   'titles':{s:pool[s]['title'] for s in ids},
   'authentic_material_SHA':sorted({m['sha256'] for s in ids for m in pool[s]['authentic_materials']}),
   'status':'RESERVED_EXCLUDE_FROM_FURTHER_TRAINING_PENDING_FULL_TASK_AND_ANCESTRY_QA',
   'source_and_source_scope_intersection_with_current569':0,
   'resource_byte_SHA_intersection_with_current569_known_authentic_materials':0,
   'resource_ancestry_closure':'NOT_YET_PROVEN_BY_THIS_RESERVATION',
   'task_readiness':'NOT_YET_QUALIFIED','do_not_use_for_training':True})
report={'schema':'wrd09-holdout-reservation-v1','authorship':'New offline research reservation by /root/scheduled_batch24; not historical dataset label or teacher rollout.',
 'pins':[pin(p) for p in [REG,POOL,SCOPE,MAN,Path(__file__).resolve()]],
 'purpose':'Protect whole candidate source_scope components before further training labels; ancestry joins may enlarge exclusions or lower usable task count, never return reserved content to train.',
 'candidate_inventory':{'sources':387,'source_scope_groups':378,'material_sources':19,'material_groups':17,'material_reference_entries':51,'distinct_material_SHA':49},
 'reserved_groups':36,'reserved_sources':len(all_reserved),'dev_groups':12,'test_groups':24,
 'groups':entries,'reserved_source_ids':sorted(all_reserved),'reserved_source_scope_components':sorted(selected),
 'current569_source_intersection':sorted(all_reserved&used),'current569_scope_intersection':sorted(set(selected)&used_groups),
 'known_authentic_material_SHA_intersection':sorted(all_material_sha&used_material_sha),
 'closure_limit':'Zero source_scope or known material SHA intersection alone is insufficient ancestry proof. No executable-task qualification or holdout token arrays claimed yet.',
 'new_training_admissions':0,'model_or_actor_calls':0,'training_started':False}
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'holdout_reservation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pin':pin(OUT/'holdout_reservation.json'),'groups':len(entries),'sources':len(all_reserved),'dev':12,'test':24,'material_SHA':len(all_material_sha)},ensure_ascii=False))
