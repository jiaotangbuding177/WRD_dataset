"""Audit selected task request long-text overlap, separately from material aliases."""
import gzip,hashlib,json,re
from pathlib import Path
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation09/holdout';MAIN=ROOT/'output/20261027_wrd_main_v10'
def norm(s):return re.sub(r'\s+','',s)
def ss(x):
 if isinstance(x,str):yield x
 elif isinstance(x,list):
  for t in x:yield from ss(t)
 elif isinstance(x,dict):
  for t in x.values():yield from ss(t)
m=json.loads((MAIN/'TRAINING_MANIFEST.json').read_text(encoding='utf-8-sig'));train=[]
for f in m['actual_train_files']:
 for line in gzip.open(MAIN/f['path'],'rt',encoding='utf-8-sig'):
  r=json.loads(line);train.append({'id':r['id'],'source_ids':r['source_ids'],'text':norm('\n'.join(ss(r['messages'])))})
catalog=json.loads((OUT/'TASK_CATALOG_ALL36.json').read_text(encoding='utf-8-sig'));matches=[]
for task in catalog:
 if task['status']=='HOLD':continue
 body=json.loads((OUT/task['task_input_pin']['path']).read_text(encoding='utf-8-sig'))['messages'][0]['content'];text=norm(body)
 anchors=[(p,text[p:p+160]) for p in range(0,len(text)-159,80)]
 for row in train:
  hits=[{'normalized_task_offset':p,'text':a,'sha256':hashlib.sha256(a.encode()).hexdigest()} for p,a in anchors if a in row['text']]
  if hits:matches.append({'task_id':task['task_id'],'selected_source_id':task['selected_source_id'],'split':task['split'],
   'training_view':row['id'],'training_source_ids':row['source_ids'],'hits':hits,'classification':'UNREVIEWED_REQUEST_OVERLAP_NOT_AUTOMATIC_SCOPE_EQUIVALENCE'})
report={'schema':'wrd09-request-current569-overlap-v1','matches':matches,'match_rows':len(matches),
 'matched_task_ids':sorted({r['task_id'] for r in matches}),'matched_sources':sorted({r['selected_source_id'] for r in matches}),
 'normalization':'Unicode whitespace only;160char windows each80 chars over selected actual task body',
 'limits':'A shared instruction/persona template is not private ancestry. A private JD or private source text requires explicit review; unseen raw materials alone do not establish whole-source independence.'}
(OUT/'REQUEST_CURRENT569_OVERLAP.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'rows':len(matches),'sources':report['matched_sources'],
 'pairs':[{'test':r['selected_source_id'],'train':r['training_source_ids'],'hits':len(r['hits'])} for r in matches]},ensure_ascii=False))
