"""Dense exact 160-character material overlap against current569 message bodies.

Every40 material starts are checked against every training character start via
40-character prefix lookup, then exact full160 confirmation. No fuzzy credit.
"""
import collections,gzip,hashlib,json,re
from pathlib import Path
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation09/holdout';MAIN=ROOT/'output/20261027_wrd_main_v10'
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
recovery=json.loads((OUT/'MATERIAL_RECOVERY_AND_ANCESTRY.json').read_text(encoding='utf-8-sig'))
patterns=collections.defaultdict(list);total=0
for mat in recovery['materials']:
 text=norm((OUT/'material_review/text'/f'{mat["sha256"]}.txt').read_text(encoding='utf-8'))
 for offset in range(0,len(text)-159,40):
  full=text[offset:offset+160];patterns[full[:40]].append((full,mat['sha256'],offset,mat['example_original_filename']));total+=1
manifest=json.loads((MAIN/'TRAINING_MANIFEST.json').read_text(encoding='utf-8-sig'));results=[];n=0;characters=0
for shard in manifest['actual_train_files']:
 for line in gzip.open(MAIN/shard['path'],'rt',encoding='utf-8-sig'):
  row=json.loads(line);text=norm('\n'.join(strings(row['messages'])));characters+=len(text);n+=1
  hits=collections.defaultdict(list)
  for i in range(len(text)-159):
   possibilities=patterns.get(text[i:i+40])
   if possibilities:
    full=text[i:i+160]
    for expected,h,offset,name in possibilities:
     if full==expected:
      hits[(h,name)].append({'material_normalized_offset':offset,'training_normalized_offset':i,'text':full,'sha256':hashlib.sha256(full.encode()).hexdigest()})
  for (h,name), anchors in hits.items():
   results.append({'material_sha256':h,'material_name':name,'view_id':row['id'],'training_source_ids':row['source_ids'],
    'exact160_anchors':anchors,'classification':'EXACT_CONTENT_OVERLAP_NEEDS_ANCESTRY_SEMANTIC_REVIEW'})
assert n==569
report={'schema':'wrd09-dense-material-overlap-v1','current_views':n,'normalized_training_characters_scanned':characters,
 'material160_patterns_stride40':total,'matches':results,'match_rows':len(results),
 'new_private_ancestry_not_automatically_inferred':True,
 'limits':'Checks every40th material start and every training character start; any uninterrupted normalized common substring>=199chars will contain a tested full160 anchor. Shorter or paraphrased lineage can remain unknown.',
 'normalization':'Unicode whitespace removal only','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(OUT/'DENSE_MATERIAL_CURRENT569_CONTENT_OVERLAP.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'patterns':total,'current_views':n,'scanned_chars':characters,'match_rows':len(results),
 'pairs':[{'name':r['material_name'],'view':r['view_id'],'sources':r['training_source_ids'],'hits':len(r['exact160_anchors'])} for r in results]},ensure_ascii=False))
