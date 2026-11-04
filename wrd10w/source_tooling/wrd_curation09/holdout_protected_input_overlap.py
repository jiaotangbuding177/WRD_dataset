"""Isolation-only exact scan of protected ORIGINAL USER INPUT, never thought.
No protected model answers, reasoning, evaluation result, rubric or score is
used to author the new tasks or their quality thresholds.
"""
import collections,gzip,hashlib,json,re
from pathlib import Path
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation09/holdout'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def norm(s):return re.sub(r'\s+','',s)
def strings(x):
 if isinstance(x,str):yield x
 elif isinstance(x,list):
  for y in x:yield from strings(y)
 elif isinstance(x,dict):
  for y in x.values():yield from strings(y)
def rows(p):
 op=gzip.open if str(p).endswith('.gz') else open
 with op(p,'rt',encoding='utf-8-sig') as f:return [json.loads(s) for s in f if s.strip()]
bindings=read(ROOT/'output/20261021_workflow_skill_library/source_bindings.json')
inventory=read(ROOT/'research/plans/20261027_wrd_main_v10/CLEAN_ACTOR_INVENTORY.json')
original226={r['session_id'] for r in rows(ROOT/'benchmark/enterprise_input_closed_v11_20261012/contracts/evaluation.jsonl')}
H=set(re.findall(r'conv_[0-9a-f]{12}',json.dumps(read(ROOT/'output/20261026_ablation_v2/holdout_registry.json'))))
static={s for s,sp in inventory['source_id_to_existing_split'].items() if sp in {'dev','test'}}
parent={}
def find(x):
 parent.setdefault(x,x)
 if parent[x]!=x:parent[x]=find(parent[x])
 return parent[x]
def join(x,y):parent[find(y)]=find(x)
conversations={}
for sid,binding in bindings.items():
 c=read(Path(binding['conversation']['path']));conversations[sid]=c
 join('source:'+sid,'original_group:'+str(c.get('leakage_component_id',sid)))
 for m in binding['materials']:
  if m.get('eligible_real_input') and not m.get('synthetic') and m.get('historical_bytes_certified') and m.get('sha256'):
   join('source:'+sid,'private_actual_material:'+m['sha256'])
for entry in rows(ROOT/'output/20261026_wrd_dataset_v9/coordination/entrypoint_controller.native_paths.source_closed.jsonl.gz'):
 for sid in entry.get('source_ids',[]):
  if sid in bindings:join('source:'+entry['source_id'],'source:'+sid)
protected_roots={find('source:'+s) for s in original226|H|static if s in bindings}
protected_sources={s for s in bindings if find('source:'+s) in protected_roots}
catalog=read(OUT/'TASK_CATALOG_ALL36_04.json');patterns=collections.defaultdict(list);active_materials={}
for task in catalog:
 if task['status']=='HOLD':continue
 packet=read(OUT/task['task_input_pin']['path']);text=norm(packet['messages'][0]['content'])
 for p in range(0,len(text)-159,40):
  a=text[p:p+160];patterns[a[:40]].append((a,'TASK_REQUEST',task['task_id'],p))
 for material in task['material_aliases']:active_materials[material['sha256']]=True
for h in active_materials:
 text=norm((OUT/'material_review/text'/f'{h}.txt').read_text(encoding='utf-8'))
 for p in range(0,len(text)-159,40):
  a=text[p:p+160];patterns[a[:40]].append((a,'TASK_MATERIAL',h,p))
matches=[];nuser=0;chars=0
for sid in sorted(protected_sources):
 for i,msg in enumerate(conversations[sid]['messages']):
  if msg.get('role')!='user':continue
  text=norm('\n'.join(strings(msg.get('content',''))));chars+=len(text);nuser+=1
  found=collections.defaultdict(list)
  for offset in range(len(text)-159):
   candidates=patterns.get(text[offset:offset+40])
   if candidates:
    actual=text[offset:offset+160]
    for expected,kind,owner,p in candidates:
     if actual==expected:found[(kind,owner)].append({'task_normalized_offset':p,'protected_user_normalized_offset':offset,'anchor_sha256':hashlib.sha256(actual.encode()).hexdigest()})
  for (kind,owner),anchors in found.items():matches.append({'kind':kind,'task_or_material_owner':owner,
   'protected_source_id':sid,'protected_original_message_id':msg.get('id'),'protected_original_message_index':i,
   'exact160_anchor_hashes':anchors,'content_not_printed_or_used_for_Q':'ISOLATION_ONLY'})
report={'schema':'wrd09-protected-user-input-only-overlap-v1','purpose':'Isolation check only; no protected thought, model answer, result, score or quality rule read for task authoring.',
 'original226_count':len(original226),'H12_count':len(H),'old_static_direct_source_count':len(static),
 'known_graph_protected_sources_scanned':len(protected_sources),'only_user_message_count':nuser,
 'only_user_normalized_characters_scanned':chars,'active_tasks':30,'active_material_SHA':len(active_materials),
 'match_rows':len(matches),'matches':matches,
 'limits':'Every40 task/material start vs every protected user character; exact160 matches only. No match is not proof of absence of paraphrase, shorter or uncaptured ancestry. Existing static task-result files were not consulted.',
 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'task_catalog_sha256':hashlib.sha256((OUT/'TASK_CATALOG_ALL36_04.json').read_bytes()).hexdigest()}
(OUT/'PROTECTED_USER_INPUT_ISOLATION_ONLY_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'protected_sources':len(protected_sources),'user_messages':nuser,'characters':chars,'active_material_SHA':len(active_materials),'matches':len(matches),'matched_owners':sorted({r['task_or_material_owner'] for r in matches})}))
