"""Pin actual current model-visible input evidence for resource-content aliases."""
import gzip,hashlib,json,re
from pathlib import Path
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation09/holdout';MAIN=ROOT/'output/20261027_wrd_main_v10'
def norm(s):return re.sub(r'\s+','',s)
def strings(x):
 if isinstance(x,str):yield x
 elif isinstance(x,list):
  for y in x:yield from strings(y)
 elif isinstance(x,dict):
  for y in x.values():yield from strings(y)
def sh(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
matches=json.loads((OUT/'MATERIAL_CURRENT569_CONTENT_OVERLAP.json').read_text(encoding='utf-8-sig'))['matches']
wanted={r['view_id'] for r in matches};active={}
m=json.loads((MAIN/'TRAINING_MANIFEST.json').read_text(encoding='utf-8-sig'))
for f in m['actual_train_files']:
 for s in gzip.open(MAIN/f['path'],'rt',encoding='utf-8-sig'):
  row=json.loads(s)
  if row['id'] in wanted:active[row['id']]={'row':row,'shard':f}
out=[]
for match in matches:
 row=active[match['view_id']]['row'];anchor=match['exact_normalized160char_anchors'][0]['anchor'];locations=[];orig=[]
 for i,msg in enumerate(row['messages']):
  text='\n'.join(strings(msg));nt=norm(text)
  if anchor in nt:locations.append({'message_index':i,'role':msg.get('role'),'message_sha256':sh(json.dumps(msg,ensure_ascii=False,separators=(',',':'))),
   'normalized_offset':nt.index(anchor),'visible_input':i < len(row['messages'])-1,
   'earlier_assistant_context_is_also_model_visible':msg.get('role')=='assistant' and i<len(row['messages'])-1,
   'exact_anchor':anchor})
 for sid in match['training_source_ids']:
  original=MAIN/'clean_inputs/sources'/sid/'conversation.original.json';r=json.loads(original.read_text(encoding='utf-8-sig'))
  for i,msg in enumerate(r['messages']):
   text='\n'.join(strings(msg));nt=norm(text)
   if anchor in nt:orig.append({'source_id':sid,'original_conversation_path':str(original.relative_to(ROOT)),
    'original_conversation_sha256':sh(original.read_bytes()),'message_index':i,'message_id':msg.get('id'),
    'role':msg.get('role'),'message_sha256':sh(json.dumps(msg,ensure_ascii=False,separators=(',',':'))),
    'normalized_anchor_offset':nt.index(anchor),'exact_anchor':anchor})
 assert locations and any(r['visible_input'] for r in locations)
 out.append({**match,'active_shard':active[match['view_id']]['shard'],'actual_student_visible_input_matches':locations,
  'original_source_matches':orig,
  'candidate_disposition':'HOLD_NOT_INDEPENDENT_FROM_ALREADY_TRAINED_OR_TRAINING_INPUT_CONTENT',
  'not_an_original226_H12_or_frozen_static_match':True,
  'version_relation':'Shared private source-text/answer fragment is exact; full exported file byte version equivalence is NOT established.',
  'action':'Retain new reservation; do not count as independent dev/test; no current569 manifest mutation by this script.'})
report={'schema':'wrd09-holdout-private-content-alias-conflicts-v1','conflicts':out,
 'held_source_scope_components':['v10_group_2365935aa063c29f2119','v10_group_ce64a51bb8d5425cc463'],
 'held_reserved_sources':['conv_420fd0fd1158','conv_2e03834fce5c','conv_ea9b88b23b98'],
 'scope_warning':'Known original-group/private-file DSU is necessary but missed these content-fragment aliases. Do not promote all36 as independent from metadata-only QA.',
 'classification':'NEW_EVALUATION_CANDIDATE_COLLIDES_WITH_CURRENT_TRAIN_NOT_PROTECTED_EVAL_CONTAMINATION_PROOF',
 'source_md555ea_relation':'Original training conversation was asked to design and save frontend recruiting workflow. Exported attachment shares the private interview-stage table in actual current input. Whole-file generation identity not inferred unless matched.',
 'source_docx57be_relation':'Training source user supplied exact private POC background text before requesting an image; attachment is a longer later document containing the same private background. This is shared source text, not proof same DOCX bytes or docreview557 alias.',
 'current569_changes':0,'new_business_model_calls':0,'training_started':False,'script_sha256':sh(Path(__file__).read_bytes())}
(OUT/'PRIVATE_CONTENT_ALIAS_HOLD.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'rows':len(out),'groups':2,'current_input_locations':sum(len(x['actual_student_visible_input_matches']) for x in out),'original_source_locations':sum(len(x['original_source_matches']) for x in out),'sha256':sh((OUT/'PRIVATE_CONTENT_ALIAS_HOLD.json').read_bytes())}))
