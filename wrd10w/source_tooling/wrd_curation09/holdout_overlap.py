"""Exact long-text anchor audit against actual current training message inputs/outputs.
Matches are candidates for lineage review, never proof of task identity by themselves.
"""
import collections,gzip,hashlib,json,re
from pathlib import Path
ROOT=Path('D:/skillloop');BASE=ROOT/'output/20261031_wrd_curation09/holdout';MAIN=ROOT/'output/20261027_wrd_main_v10'
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
manifest=json.loads((MAIN/'TRAINING_MANIFEST.json').read_text(encoding='utf-8-sig'))
training=[]
for f in manifest['actual_train_files']:
 for s in gzip.open(MAIN/f['path'],'rt',encoding='utf-8-sig'):
  r=json.loads(s);training.append({'id':r['id'],'source_ids':r['source_ids'],'text':norm('\n'.join(strings(r['messages'])))})
assert len(training)==569
recovery=json.loads((BASE/'MATERIAL_RECOVERY_AND_ANCESTRY.json').read_text(encoding='utf-8-sig'))
matches=[];tested=0
for material in recovery['materials']:
 text=norm((BASE/'material_review/text'/f'{material["sha256"]}.txt').read_text(encoding='utf-8'))
 # Deterministic bounded long anchors; short commonplace strings do not establish ancestry.
 positions=sorted(set([0,max(0,len(text)-160)]+list(range(300,len(text)-160,max(300,len(text)//24)))))
 anchors=[(p,text[p:p+160]) for p in positions if len(text[p:p+160])==160]
 for row in training:
  hits=[{'material_normalized_offset':p,'anchor_sha256':hashlib.sha256(a.encode()).hexdigest(),'anchor':a} for p,a in anchors if a in row['text']]
  if hits:matches.append({'material_sha256':material['sha256'],'material_name':material['example_original_filename'],
   'view_id':row['id'],'training_source_ids':row['source_ids'],'exact_normalized160char_anchors':hits,
   'status':'CONTENT_OVERLAP_CANDIDATE_REQUIRES_SEMANTIC_ANCESTRY_REVIEW'})
 tested+=len(anchors)
report={'schema':'wrd09-material-current569-long-anchor-overlap-v1','current569_views':569,'materials':49,
 'normalization':'Remove Unicode whitespace only; retain every other original character. 160char sampled anchors.',
 'tested_material_anchors':tested,'matches':matches,'match_rows':len(matches),
 'limitation':'No match is not proof of absence of paraphrase, other offsets or nontext ancestry. A match may be shared boilerplate; literal private-document lineage needs review.',
 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'training_manifest_sha256':hashlib.sha256((MAIN/'TRAINING_MANIFEST.json').read_bytes()).hexdigest()}
(BASE/'MATERIAL_CURRENT569_CONTENT_OVERLAP.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'anchors':tested,'match_rows':len(matches),'matches':[{'name':m['material_name'],'view':m['view_id'],'sources':m['training_source_ids'],'hits':len(m['exact_normalized160char_anchors'])} for m in matches]},ensure_ascii=False))
