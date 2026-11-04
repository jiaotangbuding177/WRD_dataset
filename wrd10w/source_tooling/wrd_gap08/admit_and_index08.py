"""Root-scoped admission of 17 audited resource/repair components and real arrays.

Preserves all checkpoint07 shards and its manifest snapshot. No weights/train.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter,defaultdict,deque
from array import array
import argparse,gzip,hashlib,json,math,shutil,sys
ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/'output/20261027_wrd_main_v10'
WORK=ROOT/'output/20261030_wrd_gap08'
BANK=WORK/'process_bank03/compiled02'
REL='compiled/gap08_process_01'
EXPECTED_BASE='94770ad82f082c55cf780f8a85108b9429cfa9ee5ee168c43198878f18633541'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hs(s):return hashlib.sha256(s.encode()).hexdigest()
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def pin(p):return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}


def admit():
 assert sha(DATA/'TRAINING_MANIFEST.json')==EXPECTED_BASE
 qa=WORK/'process_bank03/INDEPENDENT_TOKEN_AND_SCOPE_QA.json';q=load(qa)
 assert q['status'].startswith('PASS')
 for p in [WORK/'semantic_peer/ACTUAL_CORRECTED_DOCX_INDEPENDENT_QA.json',WORK/'semantic_peer/NEW_R_INPUT_CAUSALITY_QA02.json',WORK/'semantic_peer_html/PEER.json']:
  assert load(p)['status'].startswith('PASS')
 report=load(BANK/'COMPILATION_REPORT.json');assert report['counts']['targets']==17 and report['counts']['supervised_tokens']==26888
 destination=DATA/REL;assert not destination.exists();destination.mkdir()
 for p in BANK.iterdir():
  if p.is_file():shutil.copyfile(p,destination/p.name)
 rs=[r for ref in report['files']for r in rows(destination/ref['path'])]
 assert len(rs)==17
 source_scopes={s['source_id']:s for s in rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
 frozen=list(rows(ROOT/'output/20261026_wrd_dataset_v9/outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz'))
 original226={s for x in frozen for s in x.get('original226',[])}
 H={s for x in frozen for k,v in x.items()if 'holdout12' in k.lower()and isinstance(v,list)for s in v}
 assert len(original226)==226
 assert not {s for r in rs for s in r['source_ids']} & (original226|H)
 for r in rs:assert all(source_scopes[s]['status']=='TRAIN'for s in r['source_ids'])
 proof={'status':'ADMIT_SCOPED_RESOURCE_IMPLEMENTATION_AND_NEW_FUNCTIONAL_STATE_REPAIRS',
  'record_ids':[r['id']for r in rs],'compilation_report_sha256':sha(destination/'COMPILATION_REPORT.json'),
  'independent_token_scope_QA':pin(qa),'independent_source_text_and_rationale_QA':[pin(WORK/'semantic_peer'/n)for n in ['ACTUAL_CORRECTED_DOCX_INDEPENDENT_QA.json','NEW_R_INPUT_CAUSALITY_QA02.json']],
  'independent_HTML_local_repair_QA':pin(WORK/'semantic_peer_html/PEER.json'),
  'root_semantic_review':'Read all HTML/game/video source and the source-preservation corrections; use separate full-selected-text reviewer for the four Word programs. Checked actual fixed-image resource failures/retests and four first-page renders. Scope is implementation and specific repair, not hiring decisions, external legal/accounting truth, entire-video quality, KEEP or autonomous orchestration.',
  'exact_code_negative_ranges':22,'original_R_new_positive_tokens':0,'new_authored_R_tokens':226,'new_state_projected_A_tokens':26662,
  'original_bad_test_harness_whole_target_excluded':True,'old_unsafe_preparations':['process_bank','process_bank02'],
  'original_held_repair_prefixes_not_promoted':True,
  'new_states_are_not_original_prompt_equivalent':True,'actual_new_OpenClaw_dispatch':False,
  'credit_does_not_make_all_literal_task_assertions_or_program_edge_cases_gold':True,
  'new_business_Teacher_Actor_calls':0,'AI_curation_cost':'UNKNOWN_NOT_ZERO','training_started':False}
 save(destination/'ROOT_SEMANTIC_ADMISSION.json',proof)
 hist=DATA/'manifest_history/pre_gap08_552_20261030';hist.mkdir(exist_ok=False)
 for n in ['TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json']:shutil.copyfile(DATA/n,hist/n)
 m=load(DATA/'TRAINING_MANIFEST.json')
 m['actual_train_files'] += [{**r,'path':REL+'/'+r['path']}for r in report['files']]
 m['active_compilation_reports'].append({'path':REL+'/COMPILATION_REPORT.json','sha256':sha(destination/'COMPILATION_REPORT.json')})
 m['external_root_admission_receipts'].append({'path':REL+'/ROOT_SEMANTIC_ADMISSION.json','sha256':sha(destination/'ROOT_SEMANTIC_ADMISSION.json'),'compiled_bank':REL,'scope':'audited_resource_and_specific_repairs_only'})
 allrows=[];counts=Counter();banks=defaultdict(Counter);stages=defaultdict(Counter);sources=set();owners=set();calls=set();parents={}
 def find(x):
  parents.setdefault(x,x)
  if parents[x]!=x:parents[x]=find(parents[x])
  return parents[x]
 def join(a,b):
  a,b=find(a),find(b)
  if a!=b:parents[max(a,b)]=min(a,b)
 for ref in m['actual_train_files']:
  p=DATA/ref['path'];assert sha(p)==ref['sha256']and p.stat().st_size==ref['bytes']
  for r in rows(p):
   meta=r['original_record_metadata'];owner=meta.get('owner_id',r['id']);assert owner not in owners;owners.add(owner);allrows.append(r)
   join('r:'+r['id'],'g:'+r['source_group_id'])
   for s in r['source_ids']:sources.add(s);join('r:'+r['id'],'s:'+s)
   for t in r['targets']:
    if any(x[2]=='A'for x in t['owned_supervision_spans']):
     for call in r['messages'][t['message_index']].get('tool_calls',[]):assert call['id']not in calls;calls.add(call['id'])
   for c in [counts,banks[r['bank']],stages[r['stage']]]:
    c.update(sequences=1,targets=len(meta['supervision_message_indices']),input_tokens=r['total_tokens'],supervised_tokens=r['supervised_tokens'],le16k_sequences=int(r['total_tokens']<=16384),le32k_sequences=int(r['total_tokens']<=32768))
    for k,v in r['supervised_tokens_by_component'].items():c['component_'+k]+=v
 m.update(design_revision='5.0.48',change_id='ALG-20261030-02',actual_counts=dict(counts),by_bank={k:dict(v)for k,v in banks.items()},by_stage={k:dict(v)for k,v in stages.items()},
  distinct_source_ids=len(sources),source_connected_components_across_banks=len({find('r:'+r['id'])for r in allrows}),
  new_authored_projected_action_owners=m['new_authored_projected_action_owners']+17,
  full_WRD_main_training_ready=False,default_full_pipeline_training_entrypoint=None,training_started=False,model_weights_loaded=False,
  script_sha256=sha(__file__))
 m['supervision_origin_tokens']['new_authored_R_tokens']+=226
 m['supervision_origin_tokens']['new_authored_native_action_projection_A_tokens']+=26662
 assert sum(m['supervision_origin_tokens'].values())==counts['supervised_tokens']
 assert counts['targets']==569 and counts['supervised_tokens']==177562 and counts['input_tokens']==3496949
 m['gap08_component_admission']={'new_targets':17,'new_positive_tokens':26888,'new_original_R_tokens':0,'new_R_tokens':226,'new_A_tokens':26662,'writer_or_retry_views':8,'local_repair_projections':4,'new_source_preservation_repairs':4,'new_viewport_repair':1,'new_autonomous_or_KEEP_chains':0,'not17_independent_tasks':True,'old_held_preparations_not_active':True}
 save(DATA/'TRAINING_MANIFEST.json',m)
 save(DATA/'ACTUAL_DATA_STATISTICS.json',{k:m[k]for k in ['status','actual_counts','by_stage','by_bank','supervision_origin_tokens','distinct_source_ids','source_connected_components_across_banks','missing_main_stages','full_WRD_main_training_ready','training_started']})
 def inventory(records):
  return {'targets':len(records),'input_tokens':sum(r['total_tokens']for r in records),'supervised_tokens':sum(r['supervised_tokens']for r in records),
    'weighted_label_mass':sum((b-a)*w for r in records for a,b,_,w in r['supervision_spans']),
    'source_ids':len({s for r in records for s in r['source_ids']}),'joined_components':len({find('r:'+r['id'])for r in records}),
    'le16K':sum(r['total_tokens']<=16384 for r in records),'le32K':len(records)}
 contracts=[r for r in allrows if r['bank']=='source_contract_main'];process=[r for r in allrows if r['bank']!='source_contract_main']
 schedule=[]
 def ordered(records):
  queues=defaultdict(deque)
  for r in sorted(records,key=lambda x:(x['bank'],x['id'])):queues[find('r:'+r['id'])].append(r)
  names=deque(sorted(queues))
  while names:
   key=names.popleft();yield queues[key].popleft()
   if queues[key]:names.append(key)
 a=math.ceil(len(contracts)/16);b=math.ceil(len(process)/4)
 for name,records,accum,passes,offset in [('contracts',contracts,16,1,0),('process',process,4,3,a)]:
  for epoch in range(passes):
   for i,r in enumerate(ordered(records)):schedule.append({'phase':name,'pass':epoch+1,'optimizer_update':offset+epoch*math.ceil(len(records)/accum)+i//accum+1,
    'id':r['id'],'owner':r['original_record_metadata'].get('owner_id',r['id']),'joined_component':find('r:'+r['id']),
    'tokens':r['total_tokens'],'valid_labels':r['supervised_tokens'],'weighted_label_mass':sum((y-x)*w for x,y,_,w in r['supervision_spans'])})
 save(WORK/'CURRENT_DATA_AND_EXPOSURE08.json',{'status':'ACTUAL_COUNTS_PROPOSED_NOT_RUN_COMPONENT_SCHEDULE','contracts':inventory(contracts),'process':inventory(process),'all':inventory(allrows),
  'first_pass_component_updates':a+b,'max_with_three_process_passes':a+3*b,'independent_student_dev_test_arrays':0,
  'not_a_training_launcher':True,'full_pipeline_ready':False,'training_started':False,'manifest_sha256':sha(DATA/'TRAINING_MANIFEST.json')})
 save(WORK/'OWNER_EXPOSURE_SCHEDULE08.json',{'status':'PROPOSED_NOT_EXECUTED','rows':schedule,'training_started':False})
 print(js({'counts':dict(counts),'sources':len(sources),'components':m['source_connected_components_across_banks'],'proposed_updates':a+b,'max_updates':a+3*b}))


def arrays():
 manifest=DATA/'TRAINING_MANIFEST.json';m=load(manifest);out=DATA/'canonical_arrays08';out.mkdir(exist_ok=False)
 entries=[];total=positive=byte_count=0
 for f in m['actual_train_files']:
  for ordinal,r in enumerate(rows(DATA/f['path'])):
   ids=r['input_ids'];labels=[-100]*len(ids);weights=[0.]*len(ids)
   for lo,hi,_,w in r['supervision_spans']:
    for i in range(lo,hi):labels[i]=ids[i];weights[i]=w
   base=out/'arrays'/f'{len(entries):04d}_{hs(r["id"])[:24]}';base.mkdir(parents=True)
   refs={}
   for name,kind,dtype,values,suffix in [('input_ids','I','uint32_le',ids,'u32le'),('labels','q','int64_le',labels,'i64le'),('loss_weights','f','float32_le',weights,'f32le')]:
    a=array(kind,values)
    if sys.byteorder!='little':a.byteswap()
    p=base/f'{name}.{suffix}.bin';p.write_bytes(a.tobytes());byte_count+=p.stat().st_size
    refs[name]={'path':p.relative_to(DATA).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p),'dtype':dtype}
   assert refs['input_ids']['sha256']==r['input_ids_sha256_u32le']
   entries.append({'position':len(entries),'id':r['id'],'source_train_file':f['path'],'source_record_index':ordinal,'total_tokens':len(ids),
    'supervised_tokens':r['supervised_tokens'],'supervision_spans_sha256':r['supervision_spans_sha256'],'source_input_ids_sha256_u32le':r['input_ids_sha256_u32le'],'arrays':refs})
   total+=len(ids);positive+=r['supervised_tokens']
 index={'schema':'wrd-canonical-binary-array-index08-v1','manifest_relative_path':'TRAINING_MANIFEST.json','manifest_sha256':sha(manifest),
  'record_count':len(entries),'input_tokens':total,'supervised_tokens':positive,'binary_files':3*len(entries),'binary_bytes':byte_count,'records':entries,
  'attention_mask':'all ones generated from length','loss_weights_storage':'float32 little endian; canonical Python weights returned from checked source spans',
  'python_weight_return':'original authenticated source values','legacy_row_binary_arrays':'IGNORED; use this complete canonical index','training_started':False,'weights_loaded':False}
 save(out/'ARRAY_INDEX08.json',index)
 save(out/'INDEX_PIN08.json',{'index_relative_path':'canonical_arrays08/ARRAY_INDEX08.json','index_bytes':(out/'ARRAY_INDEX08.json').stat().st_size,
  'index_sha256':sha(out/'ARRAY_INDEX08.json'),'manifest_sha256':sha(manifest)})
 code=(ROOT/'output/20261029_wrd_batch24/canonical_arrays07/binary_loader.py').read_text(encoding='utf-8').replace('07','08')
 (out/'binary_loader.py').write_text(code,encoding='utf-8',newline='')
 print(js({'sequences':len(entries),'binary_files':3*len(entries),'binary_bytes':byte_count,'input_tokens':total,'supervised_tokens':positive}))


if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['admit','arrays']);a=ap.parse_args()
 admit()if a.operation=='admit'else arrays()
