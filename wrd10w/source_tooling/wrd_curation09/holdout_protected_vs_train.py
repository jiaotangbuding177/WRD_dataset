"""Isolation-only protected original user input vs actual main/staging messages.

No protected thought, assistant answer, evaluation result or quality score is
read to create patterns. Full matches remain audit evidence, not training data.
"""
import collections,gzip,hashlib,json,re
from pathlib import Path
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation09/holdout';MAIN=ROOT/'output/20261027_wrd_main_v10'
STAGING=ROOT/'output/20261031_wrd_curation09/compiled_staging01/CANDIDATES_STAGING_NOT_MAIN.jsonl.gz'
def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def norm(x):return re.sub(r'\s+','',x)
def rows(p):
 op=gzip.open if str(p).endswith('.gz') else open
 with op(p,'rt',encoding='utf-8-sig') as f:return [json.loads(s) for s in f if s.strip()]
def strings(x):
 if isinstance(x,str):
  yield x
  if x[:1] in '{[':
   try:yield from strings(json.loads(x))
   except (ValueError,TypeError):pass
 elif isinstance(x,list):
  for y in x:yield from strings(y)
 elif isinstance(x,dict):
  for y in x.values():yield from strings(y)
bindings=read(ROOT/'output/20261021_workflow_skill_library/source_bindings.json')
inventory=read(ROOT/'research/plans/20261027_wrd_main_v10/CLEAN_ACTOR_INVENTORY.json')
original226={r['session_id'] for r in rows(ROOT/'benchmark/enterprise_input_closed_v11_20261012/contracts/evaluation.jsonl')}
H=set(re.findall(r'conv_[0-9a-f]{12}',json.dumps(read(ROOT/'output/20261026_ablation_v2/holdout_registry.json'))))
static={s for s,split in inventory['source_id_to_existing_split'].items() if split in {'dev','test'}}
parents={}
def find(x):
 parents.setdefault(x,x)
 if parents[x]!=x:parents[x]=find(parents[x])
 return parents[x]
def join(x,y):parents[find(y)]=find(x)
conversations={}
for sid,b in bindings.items():
 c=read(Path(b['conversation']['path']));conversations[sid]=c
 join('source:'+sid,'original_group:'+str(c.get('leakage_component_id',sid)))
 for m in b['materials']:
  if m.get('eligible_real_input') and not m.get('synthetic') and m.get('historical_bytes_certified') and m.get('sha256'):
   join('source:'+sid,'private_actual_material:'+m['sha256'])
for entry in rows(ROOT/'output/20261026_wrd_dataset_v9/coordination/entrypoint_controller.native_paths.source_closed.jsonl.gz'):
 for sid in entry.get('source_ids',[]):
  if sid in bindings:join('source:'+entry['source_id'],'source:'+sid)
forbidden_roots={find('source:'+s) for s in original226|H|static if s in bindings}
forbidden={s for s in bindings if find('source:'+s) in forbidden_roots}
patterns=collections.defaultdict(list);np=0;users=0;pchars=0
for sid in sorted(forbidden):
 for i,m in enumerate(conversations[sid]['messages']):
  if m.get('role')!='user':continue
  text=norm('\n'.join(strings(m.get('content',''))));users+=1;pchars+=len(text)
  origin={'protected_source_id':sid,'protected_message_id':m.get('id'),'protected_message_index':i,
   'original_message_sha256':sha(json.dumps(m,ensure_ascii=False,separators=(',',':'))),
   'original_conversation_pin':bindings[sid]['conversation'],
   'direct_original226':sid in original226,'direct_H12':sid in H,'direct_old_static':sid in static,
   'protected_by_known_ancestry':True,'thought_or_assistant_answer_used':False}
  for p in range(0,len(text)-159,40):
   anchor=text[p:p+160];patterns[anchor[:40]].append((anchor,p,origin));np+=1
manifest=read(MAIN/'TRAINING_MANIFEST.json');populations={
 'CURRENT569_MAIN':[r for file in manifest['actual_train_files'] for r in rows(MAIN/file['path'])],
 'STAGING_NOT_MAIN':rows(STAGING)}
assert len(populations['CURRENT569_MAIN'])==569
matches=[];counts={}
for population,records in populations.items():
 chars=0;messages=0
 for row in records:
  for mi,msg in enumerate(row['messages']):
   text=norm('\n'.join(strings(msg)));chars+=len(text);messages+=1;hits=collections.defaultdict(list);origins={}
   for i in range(len(text)-159):
    options=patterns.get(text[i:i+40])
    if options:
     actual=text[i:i+160]
     for expected,p,origin in options:
      if actual==expected:
       key=(origin['protected_source_id'],origin['protected_message_index']);origins[key]=origin
       hits[key].append({'protected_user_normalized_offset':p,'current_message_normalized_offset':i,
        'exact160char_anchor':actual,'anchor_sha256':sha(actual)})
   for key,anchors in hits.items():
    matches.append({'population':population,'current_record_id':row['id'],'current_source_ids':row.get('source_ids'),
     'current_owner_id':row.get('owner_id',row.get('original_record_metadata',{}).get('owner_id')),
     'original_recorded_action_owner':row.get('original_recorded_action_owner',row.get('original_record_metadata',{}).get('original_recorded_action_owner')),
     'current_message_index':mi,'current_message_role':msg.get('role'),
     'current_message_sha256':sha(json.dumps(msg,ensure_ascii=False,separators=(',',':'))),
     'earlier_input_before_last_target':mi<len(row['messages'])-1,
     'stage':row.get('stage'),'bank':row.get('bank'),
     'source_origin':origins[key],'anchors':anchors,
     'disposition':'UNREVIEWED_EXACT_USER_CONTENT_MATCH_DISTINGUISH_GENERIC_TEMPLATE_FROM_PRIVATE_BUSINESS',
     'not_automatic_main_withdrawal_or_positive_loss_admission':True})
 counts[population]={'records':len(records),'messages':messages,'normalized_chars':chars,
  'matched_record_ids':sorted({x['current_record_id'] for x in matches if x['population']==population}),
  'match_message_origin_pairs':sum(x['population']==population for x in matches)}
report={'schema':'wrd09-protected-original-user-vs-main-and-staging-isolation-v1',
 'status':'EXACT_MATCH_CANDIDATES_REQUIRE_PRIVATE_VS_GENERIC_REVIEW',
 'source_pattern_basis':'Only original role=user messages; no protected assistant/thought/result/score for patterns or rubric.',
 'protected_sources':len(forbidden),'original_user_messages':users,'protected_user_normalized_chars':pchars,
 'pattern160_count_stride40':np,'populations':counts,'matches':matches,
 'training_manifest_pin':{'sha256':sha((MAIN/'TRAINING_MANIFEST.json').read_bytes()),'bytes':(MAIN/'TRAINING_MANIFEST.json').stat().st_size},
 'staging_pin':{'sha256':sha(STAGING.read_bytes()),'bytes':STAGING.stat().st_size},
 'scope_limit':'Exact normalized >=199 common text guarantees one full160 pattern; shorter/paraphrased/uncaptured ancestry remains unknown. Reused generic persona/retrieval wrappers alone are not private ancestry.',
 'classification_not_yet_semantic_reviewed':True,'main_manifest_changed':False,'training_started':False,
 'script_sha256':sha(Path(__file__).read_bytes())}
path=OUT/'PROTECTED_ORIGINAL_USER_VS_CURRENT569_AND_STAGING.json'
path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pin':{'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())},
 'protected_sources':len(forbidden),'users':users,'patterns':np,
 'populations':{k:{'records':v['records'],'matched_records':len(v['matched_record_ids']),'pairs':v['match_message_origin_pairs']} for k,v in counts.items()}},ensure_ascii=False))
