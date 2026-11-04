"""P4 isolation-only audit of proposed source inputs; no scores/CoT reused."""
from pathlib import Path
import collections,gzip,hashlib,json,re

ROOT=Path('D:/skillloop')
MAIN=ROOT/'output/20261027_wrd_main_v10'
OLD=ROOT/'output/20261031_wrd_curation09/holdout'
OUT=ROOT/'output/20261031_wrd_curation10/parent_inputs'
IDS=['conv_6347576535a5','conv_2b8fd8fdd8bc','conv_c1ce48280769','conv_e35903a5c526',
 'conv_12fc39ca6b57','conv_692eb36fe8af','conv_778bb56fc693','conv_589813f393e6','conv_007d40b3886f',
 'conv_0400aac342b0','conv_15f0f4d89d3f','conv_ca2369adba0b','conv_24de551a33dd',
 'conv_34b56ae9c535','conv_3c7308af3676']

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(l) for l in gzip.open(p,'rt',encoding='utf-8-sig') if l.strip()]
def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def pin(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def strings(x):
 if isinstance(x,str):yield x
 elif isinstance(x,list):
  for y in x:yield from strings(y)
 elif isinstance(x,dict):
  for y in x.values():yield from strings(y)
def norm(x):return re.sub(r'\s+','',x)
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
 pool={x['source_id']:x for x in rows(MAIN/'clean_inputs/source_pool.with_body.jsonl.gz')}
 bindings=read(ROOT/'output/20261021_workflow_skill_library/source_bindings.json')
 inventory=read(ROOT/'research/plans/20261027_wrd_main_v10/CLEAN_ACTOR_INVENTORY.json')
 with (ROOT/'benchmark/enterprise_input_closed_v11_20261012/contracts/evaluation.jsonl').open(encoding='utf-8-sig') as f:
  original226={json.loads(l)['session_id'] for l in f if l.strip()}
 H=set(re.findall(r'conv_[0-9a-f]{12}',json.dumps(read(ROOT/'output/20261026_ablation_v2/holdout_registry.json'))))
 static={s for s,v in inventory['source_id_to_existing_split'].items() if v in {'dev','test'}}
 parent={}
 def find(s):
  parent.setdefault(s,s)
  if parent[s]!=s:parent[s]=find(parent[s])
  return parent[s]
 def join(a,b):parent[find(b)]=find(a)
 conv={}
 for sid,b in bindings.items():
  c=read(b['conversation']['path']);conv[sid]=c
  join('source:'+sid,'original_group:'+str(c.get('leakage_component_id',sid)))
  for m in b['materials']:
   if m.get('eligible_real_input') and not m.get('synthetic') and m.get('historical_bytes_certified') and m.get('sha256'):
    join('source:'+sid,'private_material:'+m['sha256'])
 for row in rows(ROOT/'output/20261026_wrd_dataset_v9/coordination/entrypoint_controller.native_paths.source_closed.jsonl.gz'):
  for sid in row.get('source_ids',[]):
   if sid in bindings:join('source:'+row['source_id'],'source:'+sid)
 forbidden_roots={find('source:'+s) for s in original226|H|static if s in bindings}
 forbidden={s for s in bindings if find('source:'+s) in forbidden_roots}
 patterns=collections.defaultdict(list)
 for sid in sorted(forbidden):
  for i,msg in enumerate(conv[sid]['messages']):
   if msg.get('role')!='user':continue
   text=norm('\n'.join(strings(msg.get('content',''))))
   for k in range(0,len(text)-159,40):
    anchor=text[k:k+160]
    patterns[anchor[:40]].append((anchor,sid,i,k))
 man=read(MAIN/'TRAINING_MANIFEST.json')
 train=[r for sh in man['actual_train_files'] for r in rows(MAIN/sh['path'])]
 train_sids={s for r in train for s in r['source_ids']}
 train_groups={pool[s]['source_group_id'] for s in train_sids if s in pool}
 train_mats={a['sha256'] for s in train_sids if s in pool for a in pool[s]['authentic_materials']}
 # Private source-answer aliases are used only to enlarge isolation, never to
 # assign quality, labels or answers. Do not inspect protected226 assistant/Q.
 reserved=read(OLD/'holdout_reservation.json')
 private_patterns=collections.defaultdict(list)
 for sid in reserved['reserved_source_ids']:
  for i,msg in enumerate(pool[sid]['historical_assistant_messages']):
   text=norm('\n'.join(strings(msg.get('content',''))))
   for k in range(0,len(text)-159,40):
    anchor=text[k:k+160]
    private_patterns[anchor[:40]].append((anchor,sid,i,k))
 train_message_text=[(r['id'],norm('\n'.join(strings(r['messages'])))) for r in train]
 results=[]
 for sid in IDS:
  r=pool[sid];matches=[]
  for i,msg in enumerate(r['user_messages']):
   t=norm(msg['content']);seen=set()
   for pos in range(len(t)-159):
    for anchor,ps,pi,po in patterns.get(t[pos:pos+40],[]):
     if t[pos:pos+160]==anchor and (ps,pi,po) not in seen:
      seen.add((ps,pi,po));matches.append({'selected_user_index':i,'selected_normalized_offset':pos,
       'protected_source_id':ps,'protected_user_message_index':pi,'protected_normalized_offset':po,'anchor_sha256':sha(anchor)})
  private_hits=[]
  for i,msg in enumerate(r['user_messages']):
   t=norm(msg['content']);seen=set()
   for pos in range(len(t)-159):
    for anchor,ps,pi,po in private_patterns.get(t[pos:pos+40],[]):
     if t[pos:pos+160]==anchor and (ps,pi,po) not in seen:
      seen.add((ps,pi,po));private_hits.append({'selected_user_index':i,'selected_normalized_offset':pos,
       'reserved_source_id':ps,'reserved_assistant_index':pi,'reserved_normalized_offset':po,'anchor_sha256':sha(anchor),
       'used_for_isolation_only_not_quality_or_training':True})
  current_hits=[]
  for i,msg in enumerate(r['user_messages']):
   t=norm(msg['content'])
   if len(t)<32:continue
   for vid,body in train_message_text:
    if t in body:current_hits.append({'source_user_occurrence_index':i,'view_id':vid,'whole_normalized_request_sha256':sha(t)})
  results.append({'source_id':sid,'source_group_id':r['source_group_id'],
   'direct_protected_or_known_private_ancestry':sid in forbidden,
   'in_current_train_ids':sid in train_sids,'known_scope_in_train':r['source_group_id'] in train_groups,
   'known_material_train_intersection':sorted({a['sha256'] for a in r['authentic_materials']}&train_mats),
   'protected_original_user_exact160_matches':matches,'protected_input_alias_detected':bool(matches),
   'reserved_source_private_answer_alias_hits':private_hits,
   'reserved_private_answer_alias_detected':bool(private_hits),
   'current_train_whole_original_user_request_hits_ge32':current_hits,
   'all_user_body_sha256':[sha(x['content']) for x in r['user_messages']],
   'original_conversation_pin':r['original_conversation_pin'],
   'protected_assistant_thought_grade_or_Q_used':False})
 report={'schema':'wrd10-parent-source-isolation-v1','status':'ISOLATION_ONLY_NOT_SEMANTIC_OR_RUNTIME_READY',
  'results':results,'candidate_source_count':len(results),'protected_sources':len(forbidden),
  'no_protected226_thought_or_assistant_answer_or_Q_used':True,
  'reserved_source_assistant_body_used_only_for_private_alias_isolation':True,
  'exact_match_limits':'Whitespace-only exact160, protected starts stride40 vs every candidate user character. No absence-of-paraphrase proof. Complete parent audit only uses original user content for isolation.',
  'pins':[pin(p) for p in [MAIN/'TRAINING_MANIFEST.json',MAIN/'clean_inputs/source_pool.with_body.jsonl.gz',Path(__file__)]],
  'new_model_calls':0,'training_started':False}
 save(OUT/'SOURCE_ISOLATION_AUDIT.json',report)
 print(json.dumps({'sources':len(results),'protected_ancestry':[r['source_id'] for r in results if r['direct_protected_or_known_private_ancestry']],
  'protected_user_alias':[r['source_id'] for r in results if r['protected_input_alias_detected']],
  'reserved_private_alias':[r['source_id'] for r in results if r['reserved_private_answer_alias_detected']]},ensure_ascii=False))

if __name__=='__main__':main()
