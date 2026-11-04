"""Dense exact selected-request audit. Reads data only; writes a QA receipt."""
import json,gzip,re,collections,hashlib
from pathlib import Path
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation09/holdout';MAIN=ROOT/'output/20261027_wrd_main_v10'
def norm(x):return re.sub(r'\s+','',x)
def strings(x):
 if isinstance(x,str):yield x
 elif isinstance(x,list):
  for y in x:yield from strings(y)
 elif isinstance(x,dict):
  for y in x.values():yield from strings(y)
catalog=json.loads((OUT/'TASK_CATALOG_ALL36_04.json').read_text(encoding='utf-8-sig'));patterns=collections.defaultdict(list);n=0
for task in catalog:
 if task['status']=='HOLD':continue
 body=json.loads((OUT/task['task_input_pin']['path']).read_text(encoding='utf-8-sig'))['messages'][0]['content'];text=norm(body)
 for offset in range(0,len(text)-159,40):
  full=text[offset:offset+160];patterns[full[:40]].append((full,task['task_id'],task['selected_source_id'],offset));n+=1
manifest=json.loads((MAIN/'TRAINING_MANIFEST.json').read_text(encoding='utf-8-sig'));matches=[];views=0
for shard in manifest['actual_train_files']:
 for line in gzip.open(MAIN/shard['path'],'rt',encoding='utf-8-sig'):
  row=json.loads(line);text=norm('\n'.join(strings(row['messages'])));views+=1;hits=collections.defaultdict(list)
  for i in range(len(text)-159):
   possibilities=patterns.get(text[i:i+40])
   if possibilities:
    full=text[i:i+160]
    for expected,tid,sid,p in possibilities:
     if full==expected:hits[(tid,sid)].append({'task_normalized_offset':p,'training_normalized_offset':i,'text':full})
  for (tid,sid),anchors in hits.items():matches.append({'task_id':tid,'selected_source_id':sid,'training_view_id':row['id'],'training_source_ids':row['source_ids'],'exact160_anchors':anchors})
report={'schema':'wrd09-dense-active30-request-overlap-v1','active_task_inputs':30,'current569_views':views,
 'patterns_stride40':n,'matches':matches,'no_uninterrupted_normalized_common_substring_ge199_found':not matches,
 'limits':'Unicode whitespace only. Every40 request start vs every training character start. Exact current-message scan does not prove absence of paraphrase or shorter/uncaptured ancestry.',
 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'input_catalog_sha256':hashlib.sha256((OUT/'TASK_CATALOG_ALL36_04.json').read_bytes()).hexdigest()}
assert views==569
(OUT/'DENSE_ACTIVE30_REQUEST_CURRENT569_OVERLAP.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'patterns':n,'matches':len(matches),'sources':sorted({r['selected_source_id'] for r in matches})}))
