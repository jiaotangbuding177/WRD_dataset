"""Recover reserved original input entities and audit source/material ancestry.
No saved business program or agent loop is executed.
"""
import collections, gzip, hashlib, json, re, shutil, zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
import pymupdf

ROOT=Path('D:/skillloop'); OUT=ROOT/'output/20261031_wrd_curation09/holdout'
CLEAN=ROOT/'output/20261027_wrd_main_v10/clean_inputs'
RES=OUT/'holdout_reservation.json'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):
 op=gzip.open if str(p).endswith('.gz') else open
 with op(p,'rt',encoding='utf-8-sig') as f:return [json.loads(s) for s in f if s.strip()]
def sha(b):return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def pin(p):return {'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
reservation=read(RES); reserved=set(reservation['reserved_source_ids'])
pool={r['source_id']:r for r in rows(CLEAN/'source_pool.with_body.jsonl.gz')}
scope={r['source_id']:r for r in rows(CLEAN/'source_scope.metadata.jsonl.gz')}
bindings_path=ROOT/'output/20261021_workflow_skill_library/source_bindings.json'
bindings=read(bindings_path)
inventory_path=ROOT/'research/plans/20261027_wrd_main_v10/CLEAN_ACTOR_INVENTORY.json'
inventory=read(inventory_path);existing=inventory['source_id_to_existing_split']
eval_path=ROOT/'benchmark/enterprise_input_closed_v11_20261012/contracts/evaluation.jsonl'
original226={r['session_id'] for r in rows(eval_path)}
h_path=ROOT/'output/20261026_ablation_v2/holdout_registry.json'
H=set(re.findall(r'conv_[0-9a-f]{12}',json.dumps(read(h_path))))
assert len(original226)==226 and len(H)==12
entry_path=ROOT/'output/20261026_wrd_dataset_v9/coordination/entrypoint_controller.native_paths.source_closed.jsonl.gz'
entries={r['source_id']:r for r in rows(entry_path)}
parent={}
def find(x):
 parent.setdefault(x,x)
 if parent[x]!=x:parent[x]=find(parent[x])
 return parent[x]
def join(x,y):parent[find(y)]=find(x)
conv_meta={}
for sid,b in bindings.items():
 p=Path(b['conversation']['path']);c=read(p)
 assert sha(p.read_bytes())==b['conversation']['sha256']
 conv_meta[sid]={'original_group':c.get('leakage_component_id',sid),'declared_materials':len(b['materials'])}
 join('source:'+sid,'original_group:'+str(c.get('leakage_component_id',sid)))
 for m in b['materials']:
  if m.get('eligible_real_input') and not m.get('synthetic') and m.get('historical_bytes_certified') and m.get('sha256'):
   join('source:'+sid,'private_actual_material:'+m['sha256'])
for sid,e in entries.items():
 for ref in e.get('source_ids',[]):
  if ref in bindings:join('source:'+sid,'source:'+ref)
protected_roots={find('source:'+s) for s in original226|H}
static_roots={find('source:'+s) for s,sp in existing.items() if sp in {'dev','test'} and s in bindings}
used=set(read(ROOT/'output/20261031_wrd_readiness_plan/reviews/source_registry_current569.json')['current569_used_source_ids'])
used_roots={find('source:'+s) for s in used}
group_members=collections.defaultdict(list)
for sid in bindings:group_members[find('source:'+sid)].append(sid)
closure=[]
for group in reservation['groups']:
 members=sorted({s for sid in group['source_ids'] for s in group_members[find('source:'+sid)]})
 assert members==sorted(group['source_ids']), (group['source_scope_component_id'],members)
 assert 'v10_group_'+sha(json.dumps(members,ensure_ascii=False,separators=(',',':')))[:20]==group['source_scope_component_id']
 roots={find('source:'+sid) for sid in members}
 assert not roots&protected_roots and not roots&static_roots and not roots&used_roots
 closure.append({'source_scope_component_id':group['source_scope_component_id'],'split':group['split'],
  'actual_ancestry_members':members,'current_train_ancestor_intersection':[],
  'original226_H12_ancestor_intersection':[],'old_static_ancestor_intersection':[],
  'closure_basis':['exact original source component','all actual private user-input SHA across bindings','known source content references from source-closed entrypoints'],
  'scope_of_proof':'Known captured source/material graph. Arbitrary unrecorded provenance not inferred. Task input omits generated skills, route resources, old model answers and unknown tool outputs.'})
materials={}; refs=[];requirements=[]
for sid in sorted(reserved):
 r=pool[sid]; source_dir=OUT/'sources'/sid;source_dir.mkdir(parents=True,exist_ok=True)
 # Keep actual source requirements complete for audit. They are not automatically mounted to an evaluated model.
 save(source_dir/'requirements.original.json',{'source_id':sid,'source_scope_component_id':r['source_group_id'],
  'title':r['title'],'source_user_messages':r['user_messages'],
  'historical_assistant_answers_included':False,'full_conversation_may_contain_several_unrelated_tasks':True})
 requirements.append({'source_id':sid,'user_messages':len(r['user_messages']),
  'user_chars':sum(len(m['content']) for m in r['user_messages']),
  'pin':pin(source_dir/'requirements.original.json')})
 for m in r['authentic_materials']:
  p=CLEAN/m['path'];b=p.read_bytes();assert len(b)==m['bytes'] and sha(b)==m['sha256']
  target=OUT/'objects'/m['sha256'][:2]/m['sha256'];target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():target.write_bytes(b)
  assert sha(target.read_bytes())==m['sha256']
  relevant=[x for x in bindings[sid]['materials'] if x.get('sha256')==m['sha256']]
  assert len(relevant)==1
  orig=relevant[0];original=Path(orig['path']);assert original.is_file() and sha(original.read_bytes())==m['sha256']
  assert orig.get('eligible_real_input') and not orig.get('synthetic') and orig.get('historical_bytes_certified')
  refs.append({'source_id':sid,'native_path':m['native_path'],'sha256':m['sha256'],'bytes':len(b),
   'object_path':str(target.relative_to(OUT)).replace('\\','/'),'original_binding':orig,
   'actual_original_entity_SHA_matches':True})
  if m['sha256'] in materials:continue
  name=Path(m['native_path']).name;ext=Path(name).suffix.lower();text='';pages=None;diagnostics=[]
  if ext=='.pdf':
   doc=pymupdf.open(stream=b,filetype='pdf');pages=len(doc)
   blocks=[page.get_text(sort=True) for page in doc]
   text='\n'.join('--- PAGE '+str(i+1)+' ---\n'+s for i,s in enumerate(blocks))
   if sum(map(len,blocks))<40:diagnostics.append('PDF_TEXT_TOO_SHORT_NEEDS_VISUAL_OR_OCR')
   if doc: # One audit render, not task output or visual-quality approval.
    pix=doc[0].get_pixmap(matrix=pymupdf.Matrix(.65,.65))
    q=OUT/'material_review'/'first_pages'/f'{m["sha256"]}.png';q.parent.mkdir(parents=True,exist_ok=True);pix.save(q)
   doc.close()
  elif ext in {'.docx','.pptx'}:
   with zipfile.ZipFile(p) as z:
    keys=['word/document.xml'] if ext=='.docx' else sorted(x for x in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',x))
    parts=[]
    for key in keys:
     e=ET.fromstring(z.read(key));parts.append('--- '+key+' ---\n'+'\n'.join(x.text for x in e.iter() if x.tag.endswith('}t') and x.text))
    text='\n'.join(parts);pages=len(keys) if ext=='.pptx' else None
  elif ext in {'.md','.txt'}:text=b.decode('utf-8-sig')
  elif ext in {'.png','.jpg','.jpeg'}:diagnostics.append('IMAGE_REQUIRES_DIRECT_VISUAL_REVIEW_NOT_OCR_GOLD')
  else:diagnostics.append('UNSUPPORTED_READ_ONLY_EXTRACTION')
  txt=OUT/'material_review'/'text'/f'{m["sha256"]}.txt';txt.parent.mkdir(parents=True,exist_ok=True);txt.write_text(text,encoding='utf-8')
  materials[m['sha256']]={'sha256':m['sha256'],'bytes':len(b),'example_original_filename':name,'extension':ext,
   'object_pin':pin(target),'extracted_text_pin':pin(txt),'text_chars':len(text),'pages_if_known':pages,
   'diagnostics':diagnostics,'visual_layout_quality_not_inferred_from_text':True}
assert len(refs)==51 and len(materials)==49
report={'schema':'wrd09-holdout-material-recovery-v1','status':'PASS_ENTITY_AND_KNOWN_ANCESTRY_RECONSTRUCTION_TASK_SEMANTICS_PENDING',
 'reservation':pin(RES),'script':pin(Path(__file__).resolve()),
 'ancestry_inputs':[pin(p) for p in [bindings_path,inventory_path,eval_path,h_path,entry_path]],
 'known_ancestry_proofs':closure,'reserved_sources':len(reserved),'reserved_groups':len(closure),
 'authentic_reference_count':len(refs),'unique_material_entities':len(materials),'unique_material_bytes':sum(r['bytes'] for r in materials.values()),
 'references':refs,'materials':list(materials.values()),'source_requirements':requirements,
 'limits':['Authentic export binding and exact bytes are not proof of relevance to every task in the source.',
 'Some exported files may be earlier user-authored or AI-assisted documents; no claim that all49 are original raw task inputs.',
 'No generated route/skill/teacher answer is mounted in the task pack; each task must select its actual required inputs separately.',
 'No result, execution receipt or model quality score was fabricated or generated.'],
 'new_business_Teacher_Actor_calls':0,'training_started':False,'AI_curation_cost':'UNKNOWN_NOT_ZERO'}
save(OUT/'MATERIAL_RECOVERY_AND_ANCESTRY.json',report)
print(json.dumps({'pin':pin(OUT/'MATERIAL_RECOVERY_AND_ANCESTRY.json'),'sources':len(reserved),'groups':len(closure),'refs':len(refs),'entities':len(materials),'bytes':report['unique_material_bytes'],'filetypes':dict(collections.Counter(r['extension'] for r in materials.values()))},ensure_ascii=False))
