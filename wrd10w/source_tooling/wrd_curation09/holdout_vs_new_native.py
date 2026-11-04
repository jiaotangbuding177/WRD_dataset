"""Freeze-aware exact audit: selected eval inputs vs new states AND old prefixes."""
import collections,gzip,hashlib,json,re
from pathlib import Path
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation09/holdout';NEW=ROOT/'output/20261031_wrd_curation09'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def norm(s):return re.sub(r'\s+','',s)
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
catalog=read(OUT/'TASK_CATALOG_ALL36_05.json');patterns=collections.defaultdict(list);material_owners=collections.defaultdict(set);n=0
for task in catalog:
 if task['status']=='HOLD':continue
 text=norm(read(OUT/task['task_input_pin']['path'])['messages'][0]['content'])
 for p in range(0,len(text)-159,40):
  a=text[p:p+160];patterns[a[:40]].append((a,'EVAL_REQUEST',task['task_id'],p));n+=1
 for material in task['material_aliases']:material_owners[material['sha256']].add(task['task_id'])
for h,tids in material_owners.items():
 text=norm((OUT/'material_review/text'/f'{h}.txt').read_text(encoding='utf-8'))
 for p in range(0,len(text)-159,40):
  a=text[p:p+160];patterns[a[:40]].append((a,'EVAL_MATERIAL',h,p));n+=1
def scan_messages(messages,identity):
 hits=[]
 for mi,msg in enumerate(messages):
  text=norm('\n'.join(strings(msg)));found=collections.defaultdict(list)
  for i in range(len(text)-159):
   pp=patterns.get(text[i:i+40])
   if pp:
    actual=text[i:i+160]
    for expected,kind,owner,p in pp:
     if actual==expected:found[(kind,owner)].append({'eval_normalized_offset':p,'native_message_normalized_offset':i,'anchor':actual,'sha256':sha(actual)})
  for (kind,owner),anchors in found.items():hits.append({**identity,'message_index':mi,'message_role':msg.get('role'),
   'message_sha256_sorted':sha(json.dumps(msg,ensure_ascii=False,separators=(',',':'),sort_keys=True)),
   'eval_kind':kind,'eval_task_or_material_owner':owner,
   'eval_task_ids':sorted(material_owners[owner]) if kind=='EVAL_MATERIAL' else [owner],'anchors':anchors})
 return hits
staging_path=NEW/'compiled_staging01/CANDIDATES_STAGING_NOT_MAIN.jsonl.gz';staging=[json.loads(s) for s in gzip.open(staging_path,'rt',encoding='utf-8-sig')]
staging_hits=[]
for r in staging:staging_hits+=scan_messages(r['messages'],{'population':'NEW_FUNCTIONAL_STATE','record_id':r['id'],'source_ids':r['source_ids']})
prefixes=read(OUT/'PROTECTED_USER_VS_REAL_NATIVE_PREFIXES02.json');native_hits=[]
for target in prefixes['targets']:
 packet=read(ROOT/target['packet_pin']['path'])
 if target['lane']=='writers':ctx=read(ROOT/target['context_pin']['path'])
 else:ctx=packet['original_context']
 i=target['target_message_index'];assert sha(json.dumps(ctx['messages'][i],ensure_ascii=False,separators=(',',':'),sort_keys=True))==target['original_target_SHA_verified']
 native_hits+=scan_messages(ctx['messages'][:i+1],{'population':'ACTUAL_OLD_PREFIX_THROUGH_TARGET','original_owner_id':target['original_owner_id'],
  'source_ids':target['source_ids'],'lane':target['lane'],'target_message_index':i,'episode_id':target['episode_id']})
report={'schema':'wrd09-selected26-eval-vs-new-state-and-actual-native-prefix-v1','active_eval_inputs':26,'active_eval_material_SHA':len(material_owners),
 'patterns160_stride40':n,'staging_records':len(staging),'native_packets':len(prefixes['targets']),
 'staging_matches':staging_hits,'native_prefix_matches':native_hits,
 'staging_pin':{'path':str(staging_path.relative_to(ROOT)),'bytes':staging_path.stat().st_size,'sha256':sha(staging_path.read_bytes())},
 'task_catalog_sha256':sha((OUT/'TASK_CATALOG_ALL36_05.json').read_bytes()),'script_sha256':sha(Path(__file__).read_bytes()),
 'no_match_not_global_proof':'No conclusion about shorter, paraphrased, uncaptured or image-only lineage. Positive matches require private-vs-generic adjudication and propagation to new-resource owners.',
 'new_training_manifest_changed':False,'training_started':False}
path=OUT/'ACTIVE26_VS_STAGING_AND_REAL_PREFIX_QA.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'patterns':n,'staging_matches':len(staging_hits),'native_prefix_matches':len(native_hits),
 'matches':[{'population':r['population'],'native_owner_or_view':r.get('original_owner_id',r.get('record_id')),'sources':r['source_ids'],'eval':r['eval_task_ids'],'kind':r['eval_kind'],'hits':len(r['anchors'])} for r in staging_hits+native_hits]},ensure_ascii=False))
