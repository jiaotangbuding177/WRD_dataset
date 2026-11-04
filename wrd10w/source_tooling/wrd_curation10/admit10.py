"""Frozen-input, append-only curation10 rebase and canonical binary preparation.

stage never replaces the active manifest. activate is a separate explicit action
requiring its exact staged SHA. No weights, trainer, teacher or agent is loaded.
"""
from pathlib import Path,PurePosixPath
from collections import Counter,defaultdict
from copy import deepcopy
from array import array
import argparse,gzip,hashlib,importlib.util,json,math,os,re,shutil,sys

ROOT=Path(__file__).resolve().parents[3]
LOADER_SOURCE=ROOT/'output/20261029_wrd_batch24/canonical_arrays07/binary_loader.py'
LOADER_SOURCE_SHA='edf1d3b8e1834fd7205e2f920112408cbeb062271ca372e509be2149ae3d8777'
NATIVE_R={'native_wrd_main','native_C_review_partial_02','native_CV_B_training_01','native_HTML_B_training_01','native_recovered_read_process10'}
NATIVE_A={'native_C_execution_local_02','native_CV_B_training_01','native_HTML_B_training_01','native_recovered_read_process10'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hs(t):return hashlib.sha256(t.encode('utf-8')).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pin(p):p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}
def safe(root,relative):
 assert isinstance(relative,str)and relative and '\\'not in relative and ':'not in relative
 p=PurePosixPath(relative);assert not p.is_absolute()and p.as_posix()==relative and '..'not in p.parts
 assert not any(c in relative for c in '\r\n\0')and all(x not in {'','.','..'}and not x.endswith((' ','.'))for x in p.parts)
 q=Path(root).joinpath(*p.parts);assert q.resolve().is_relative_to(Path(root).resolve());return q
def verify_ref(root,ref):
 p=safe(root,ref['path']);assert p.is_file()and not p.is_symlink()and p.stat().st_size==ref['bytes']and sha(p)==ref['sha256'];return p
def raw_rows(p):
 with gzip.open(p,'rb')as f:
  for line in f:
   if line.strip():yield line,json.loads(line.decode('utf-8-sig'))
def write_lines(p,lines):
 with Path(p).open('wb')as raw:
  with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0)as f:
   for line in lines:f.write(line)
def unique(values,name):
 assert isinstance(values,list)and all(isinstance(x,str)and x for x in values)
 assert len(values)==len(set(values)),('DUPLICATE_ID',name);return set(values)

def origins(row):
 b=row['bank'];m=row['original_record_metadata'];out=Counter()
 for c,n in row['supervised_tokens_by_component'].items():
  if b=='source_contract_main':key='new_source_contract_annotation_tokens'
  elif c=='R':
   if b in NATIVE_R:key='original_native_R_tokens'
   elif b=='historical_semantic_R_main':key='historical_original_R_tokens'
   elif b=='historical_test_oracle_repair_02':key='recorded_cumulative_original_R_excerpt_tokens'
   elif b=='recontextualized_compat_R_process10':
    provenance=m.get('original_R_provenance')
    assert (provenance.get('kind')if isinstance(provenance,dict)else provenance)=='RECONTEXTUALIZED_ORIGINAL_COMPAT_R'
    key='recorded_compatible_R_excerpt_recontextualized_tokens'
   elif b=='source_only_controller_batch24':key='new_authored_source_only_controller_R_tokens'
   else:
    assert b in {'real_state_repair_main','new_real_state_cost_stop_02','historical_v6_native_repair_01','CV_clean_resource_construction_02','historical_style_repair_02','historical_helpers_construction_01','gap08_resource_and_repair_process'}or m.get('teacher_original_R_supervised')is False,('UNCLASSIFIED_R',b)
    key='new_authored_R_tokens'
  elif c=='A':
   if b=='recontextualized_compat_R_process10':
    assert m.get('A_original_action_arguments_identical')is True
    key='recorded_compatible_action_A_recontextualized_tokens'
   elif b=='real_state_repair_main':key='revalidated_original_action_A_tokens'
   elif b=='native_C_execution_local_02':key='original_native_execution_A_tokens'
   elif b in NATIVE_A:key='original_native_local_process_A_tokens'
   else:
    assert m.get('actual_native_tool_dispatch')is False,('UNCLASSIFIED_ACTION_ORIGIN',b)
    key='new_authored_native_action_projection_A_tokens'
  elif c=='D':
   if b=='new_real_state_cost_stop_02':key='new_authored_cost_stop_D_tokens'
   elif b=='source_only_controller_batch24':key='new_authored_source_only_controller_D_tokens'
   else:
    assert m.get('rationale_provenance')=='ORIGINAL_VISIBLE_ASSISTANT_TEXT_NOT_THOUGHT_FIELD',('UNCLASSIFIED_D',b)
    key='recorded_visible_commentary_D_tokens'
  elif c=='E':
   assert m.get('rationale_provenance')=='ORIGINAL_VISIBLE_ASSISTANT_TEXT_NOT_THOUGHT_FIELD',('UNCLASSIFIED_E',b)
   key='recorded_visible_explanation_E_tokens'
  else:raise AssertionError(('UNCLASSIFIED_COMPONENT',b,c))
  out[key]+=n
 return out

def recount(records):
 counts=Counter();banks=defaultdict(Counter);stages=defaultdict(Counter);origin=Counter();sources=set();parents={};ids=set();owners=set();calls=set()
 native_calls=set();projected_calls=set();revalidated_calls=set();native_R=set();historical_R=set();component_by_id={}
 def find(x):
  parents.setdefault(x,x)
  if parents[x]!=x:parents[x]=find(parents[x])
  return parents[x]
 def join(a,b):
  a,b=find(a),find(b)
  if a!=b:parents[max(a,b)]=min(a,b)
 for row in records:
  m=row['original_record_metadata'];identity=row['id'];owner=m.get('owner_id',identity)
  assert identity not in ids and owner not in owners;ids.add(identity);owners.add(owner)
  assert row['split']=='train'and m['training_admitted']is True and m['source_admission']=='ADMIT'
  assert not any(m.get(k)for k in ['original226','holdout12','protected_sources_visible_prefix','protected_source_ids'])
  assert 0<row['supervised_tokens']and len(row['input_ids'])==row['total_tokens']<=32768
  positive=Counter();last=0
  for a,b,c,w in row['supervision_spans']:
   assert 0<=last<=a<b<=row['total_tokens']and 0<w<=1;last=b;positive[c]+=b-a
  assert dict(positive)==row['supervised_tokens_by_component']and sum(positive.values())==row['supervised_tokens']
  assert hs(js(row['supervision_spans']))==row['supervision_spans_sha256']
  join('r:'+identity,'g:'+row['source_group_id'])
  for source in row['source_ids']:sources.add(source);join('r:'+identity,'s:'+source)
  for target in row['targets']:
   if any(x[2]=='A'for x in target['owned_supervision_spans']):
    for call in row['messages'][target['message_index']].get('tool_calls',[]):
     assert call['id']not in calls;calls.add(call['id'])
     if row['bank']in NATIVE_A:native_calls.add(call['id'])
     elif row['bank']=='real_state_repair_main':revalidated_calls.add(call['id'])
     else:projected_calls.add(call['id'])
  if positive['R']and row['bank']in NATIVE_R:native_R.add(m.get('canonical_response_owner')or m.get('actual_response_sha256')or m.get('evidence',{}).get('response_sha256')or identity)
  if positive['R']and row['bank']=='historical_semantic_R_main':historical_R.add(m['canonical_original_response_owner'])
  origin.update(origins(row))
  for c in[counts,banks[row['bank']],stages[row['stage']]]:
   c.update(sequences=1,targets=len(m['supervision_message_indices']),input_tokens=row['total_tokens'],supervised_tokens=row['supervised_tokens'],le16k_sequences=int(row['total_tokens']<=16384),le32k_sequences=int(row['total_tokens']<=32768))
   for k,v in positive.items():
    if v:c['component_'+k]+=v
 for identity in ids:component_by_id[identity]=find('r:'+identity)
 assert sum(origin.values())==counts['supervised_tokens']
 return {'actual_counts':dict(counts),'by_bank':{k:dict(v)for k,v in banks.items()},'by_stage':{k:dict(v)for k,v in stages.items()},
  'supervision_origin_tokens':dict(origin),'distinct_source_ids':len(sources),'source_connected_components_across_banks':len(set(component_by_id.values())),
  'actual_action_owners_with_positive_loss':len(native_calls),'revalidated_action_owners_with_positive_loss':len(revalidated_calls),
  'new_authored_projected_action_owners':len(projected_calls),'original_native_R_response_owners':len(native_R),'historical_original_R_response_owners':len(historical_R),
  'component_by_record_id':component_by_id,'all_positive_action_call_count':len(calls)}

def report_for(records,base_report,files):
 report=deepcopy(base_report);summary=recount(records);counts=Counter();banks=defaultdict(Counter);stages=defaultdict(Counter)
 for r in records:
  for c in[counts,banks[r['bank']],stages[r['stage']]]:
   bucket='16k'if r['total_tokens']<=16384 else'32k'
   c.update(sequences=1,targets=sum(bool(t['owned_supervision_spans'])for t in r['targets']),input_tokens=r['total_tokens'],supervised_tokens=r['supervised_tokens'],train_sequences=1,train_supervised_tokens=r['supervised_tokens'],**{bucket+'_sequences':1})
   for k,v in r['supervised_tokens_by_component'].items():c['component_'+k]+=v
 report.update(counts=dict(counts),banks={k:dict(v)for k,v in banks.items()},stages={k:dict(v)for k,v in stages.items()},files=files,
  is_filtered_curation10_bank=True,weights_loaded=False,training_started=False)
 if 'tokenizer_proof'in report:
  proof=report['tokenizer_proof'];proof['prior_report_independent_second_tokenizer_calls']=proof.get('independent_second_tokenizer_calls')
  proof['independent_second_tokenizer_calls']=0
  proof['this_operation_only_filters_byte_preserved_rows_no_new_tokenizer_call']=True
 return report

def loader_code():
 assert sha(LOADER_SOURCE)==LOADER_SOURCE_SHA
 text=LOADER_SOURCE.read_text(encoding='utf-8').replace('07','10')
 text=text.replace('def iter_features(root):','def iter_features(root, *, manifest_override=None):')
 text=text.replace("manifest_path=safe(root,index['manifest_relative_path'])", "manifest_path=safe(root,manifest_override or index['manifest_relative_path'])")
 return text

def arrays(root,manifest_path,records_with_refs):
 m=load(manifest_path);out=root/'canonical_arrays10';out.mkdir(exist_ok=False);entries=[];total=positive=bytes_=0
 for file,ordinal,r in records_with_refs:
  ids=r['input_ids'];labels=[-100]*len(ids);weights=[0.]*len(ids)
  for a,b,_,w in r['supervision_spans']:
   for i in range(a,b):labels[i]=ids[i];weights[i]=w
  directory=out/'arrays'/f'{len(entries):04d}_{hs(r["id"])[:20]}';directory.mkdir(parents=True)
  refs={}
  for name,kind,dtype,values,suffix in [('input_ids','I','uint32_le',ids,'u32le'),('labels','q','int64_le',labels,'i64le'),('loss_weights','f','float32_le',weights,'f32le')]:
   data=array(kind,values);assert data.itemsize=={'I':4,'q':8,'f':4}[kind]
   if sys.byteorder!='little':data.byteswap()
   p=directory/f'{name}.{suffix}.bin';p.write_bytes(data.tobytes());bytes_+=p.stat().st_size
   refs[name]={'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p),'dtype':dtype}
  assert refs['input_ids']['sha256']==r['input_ids_sha256_u32le']
  entries.append({'position':len(entries),'id':r['id'],'source_train_file':file,'source_record_index':ordinal,'total_tokens':len(ids),
   'supervised_tokens':r['supervised_tokens'],'supervision_spans_sha256':r['supervision_spans_sha256'],'source_input_ids_sha256_u32le':r['input_ids_sha256_u32le'],'arrays':refs})
  total+=len(ids);positive+=r['supervised_tokens']
 index={'schema':'wrd-canonical-binary-array-index10-v1','manifest_relative_path':'TRAINING_MANIFEST.json','manifest_sha256':sha(manifest_path),
  'record_count':len(entries),'input_tokens':total,'supervised_tokens':positive,'binary_files':3*len(entries),'binary_bytes':bytes_,'records':entries,
  'attention_mask':'all ones from authenticated row length','legacy_row_binary_arrays':'IGNORED; complete canonical index is the default binary entrypoint',
  'training_started':False,'weights_loaded':False}
 save(out/'ARRAY_INDEX10.json',index);save(out/'INDEX_PIN10.json',{'index_relative_path':'canonical_arrays10/ARRAY_INDEX10.json','index_bytes':(out/'ARRAY_INDEX10.json').stat().st_size,'index_sha256':sha(out/'ARRAY_INDEX10.json'),'manifest_sha256':sha(manifest_path)})
 (out/'binary_loader10.py').write_text(loader_code(),encoding='utf-8')
 return index

def bank_records(root,m):
 for ref in m['actual_train_files']:
  p=verify_ref(root,ref)
  for ordinal,(_,row)in enumerate(raw_rows(p)):yield ref['path'],ordinal,row

def frozen_inputs(root,freeze_path,freeze_sha):
 assert sha(freeze_path)==freeze_sha;f=load(freeze_path)
 assert f['status']=='ROOT_FROZEN_CURATION10_STAGE_AUTHORIZATION'
 assert f['admit10_script_sha256']==sha(__file__),'SCRIPT_NOT_ROOT_FROZEN'
 assert sha(root/'TRAINING_MANIFEST.json')==f['baseline_manifest_sha256']
 for name in['revocations','new_compilation_report','root_semantic_acceptance','independent_token_qa']:
  ref=f[name];p=Path(ref['path']);assert p.is_file()and sha(p)==ref['sha256'],('FROZEN_INPUT_CHANGED',name)
 for name in['independent_protection_qa','new_candidate_prefix_scan']:
  if name in f:
   ref=f[name];assert Path(ref['path']).is_file()and sha(ref['path'])==ref['sha256'],('FROZEN_INPUT_CHANGED',name)
 return f

def stage(root,freeze_path,freeze_sha):
 root=Path(root).resolve();f=frozen_inputs(root,freeze_path,freeze_sha);oldpath=root/'TRAINING_MANIFEST.json';old=load(oldpath)
 old_records=list(bank_records(root,old));old_count=recount([r for _,_,r in old_records])
 assert old_count['actual_counts']==old['actual_counts']and old_count['supervision_origin_tokens']==old['supervision_origin_tokens'],'BASE_RECOUNT_MISMATCH'
 rev=load(f['revocations']['path'])
 if rev['status']=='READY_FOR_ROOT_REBASE_REVIEW_MAIN_NOT_MODIFIED':
  assert rev['main_manifest_pin']['sha256']==sha(oldpath)
  # Root-frozen approval wraps the immutable independent closure; do not alter
  # its review-only status or replace the original independent evidence bytes.
  rev={'status':'ROOT_APPROVED_REVOCATION_SET','baseline_manifest_sha256':rev['main_manifest_pin']['sha256'],
       'revoked_record_ids':rev['revoke_current_view_ids'],'protected_source_ids':rev['revoke_source_ids'],
       'protected_source_scope_components':rev['revoke_source_scope_component_ids'],
       'new_allowed_record_ids':f['new_allowed_record_ids'],'new_revoked_record_ids':f['new_revoked_record_ids'],
       'immutable_closure_pin':deepcopy(f['revocations'])}
 assert rev['status']=='ROOT_APPROVED_REVOCATION_SET'and rev['baseline_manifest_sha256']==sha(oldpath)
 revoked=unique(rev['revoked_record_ids'],'revoked_record_ids');protected=unique(rev['protected_source_ids'],'protected_source_ids')
 protected_groups=unique(rev['protected_source_scope_components'],'protected_source_scope_components')
 allowed=unique(rev['new_allowed_record_ids'],'new_allowed_record_ids');new_revoked=unique(rev['new_revoked_record_ids'],'new_revoked_record_ids')
 assert not allowed&new_revoked
 scopes={r['source_id']:r for _,r in raw_rows(root/'clean_inputs/source_scope.metadata.jsonl.gz')}
 def blocked(r):return bool(set(r['source_ids'])&protected or {scopes[s]['component_id']for s in r['source_ids']}&protected_groups)
 old_ids={r['id']for _,_,r in old_records};assert revoked<=old_ids
 assert {r['id']for _,_,r in old_records if blocked(r)}<=revoked,'REVOCATION_SET_MISSES_PROTECTED_SOURCE'
 new_report_path=Path(f['new_compilation_report']['path']);newroot=new_report_path.parent;newreport=load(new_report_path)
 new_source=[]
 for ref in newreport['files']:
  p=verify_ref(newroot,ref);new_source.extend(r for _,r in raw_rows(p))
 new_ids={r['id']for r in new_source};assert len(new_ids)==len(new_source)and new_ids==allowed|new_revoked
 assert not {r['id']for r in new_source if blocked(r)}&allowed,'PROTECTED_NEW_CANDIDATE_ALLOWED'
 acceptance=load(f['root_semantic_acceptance']['path']);assert acceptance['status'].startswith('ADMIT_')and set(acceptance['record_ids'])==allowed
 assert acceptance['compilation_report_sha256']==sha(new_report_path)
 assert load(f['independent_token_qa']['path'])['status'].startswith('PASS')
 if 'expected_rebased_counts'in f:
  actual=recount([r for _,_,r in old_records if r['id']not in revoked])['actual_counts']
  assert all(actual[k]==v for k,v in f['expected_rebased_counts'].items()),'REBASED_ARITHMETIC_MISMATCH'
 if 'expected_final_counts'in f:
  actual=recount([r for _,_,r in old_records if r['id']not in revoked]+[r for r in new_source if r['id']in allowed])['actual_counts']
  assert all(actual[k]==v for k,v in f['expected_final_counts'].items()),'FINAL_ARITHMETIC_MISMATCH'
 stage_dir=root/'manifest_staging10';assert not stage_dir.exists()and not(root/'canonical_arrays10').exists();stage_dir.mkdir()
 save(stage_dir/'FROZEN_INPUTS.json',f);save(stage_dir/'REVOCATION_SET.json',rev)
 current=deepcopy(old);affected={str(PurePosixPath(p).parent)for p,_,r in old_records if r['id']in revoked}
 assert {str(PurePosixPath(r['path']).parent)for r in old['active_compilation_reports']} >= affected
 current['actual_train_files']=[];current['active_compilation_reports']=[];current['external_root_admission_receipts']=[]
 old_receipts=defaultdict(list)
 for ref in old['external_root_admission_receipts']:old_receipts[ref['compiled_bank']].append(ref)
 newrefs=[];rebases=[]
 def build_bank(source_root,source_refs,source_report,relative,keep,receipt):
  destination=safe(root,relative);destination.mkdir(parents=True,exist_ok=False);files=[];kept=[]
  for ref in source_refs:
   source=verify_ref(source_root,ref);lines=[]
   for raw,row in raw_rows(source):
    if keep(row):lines.append(raw);kept.append(row)
   name=PurePosixPath(ref['path']).name;target=destination/name;assert not target.exists();write_lines(target,lines)
   files.append({'path':name,'bytes':target.stat().st_size,'sha256':sha(target)})
  template=source_root/'CAUSAL_TEMPLATE.json';assert template.is_file();shutil.copyfile(template,destination/'CAUSAL_TEMPLATE.json')
  report=report_for(kept,source_report,files);report['source_compilation_report_sha256']=receipt['source_compilation_report_sha256']
  with gzip.open(destination/'held.jsonl.gz','wb'):pass
  report['held_file']={'path':'held.jsonl.gz','bytes':(destination/'held.jsonl.gz').stat().st_size,'sha256':sha(destination/'held.jsonl.gz')}
  save(destination/'COMPILATION_REPORT.json',report)
  receipt.update(record_ids=[r['id']for r in kept],compilation_report_sha256=sha(destination/'COMPILATION_REPORT.json'),unchanged_retained_row_values=True,no_new_semantic_credit_for_rebase=True)
  save(destination/'ROOT_SEMANTIC_ADMISSION.json',receipt)
  newrefs.extend({**ref,'path':relative+'/'+ref['path']}for ref in files)
  current['active_compilation_reports'].append({'path':relative+'/COMPILATION_REPORT.json','sha256':sha(destination/'COMPILATION_REPORT.json')})
  current['external_root_admission_receipts'].append({'path':relative+'/ROOT_SEMANTIC_ADMISSION.json','sha256':sha(destination/'ROOT_SEMANTIC_ADMISSION.json'),'compiled_bank':relative,'scope':receipt['status']})
 for reportref in old['active_compilation_reports']:
  bank=str(PurePosixPath(reportref['path']).parent)
  if bank not in affected:
   current['active_compilation_reports'].append(deepcopy(reportref));current['external_root_admission_receipts']+=deepcopy(old_receipts[bank]);continue
  path=safe(root,reportref['path']);assert sha(path)==reportref['sha256'];source_root=path.parent;source_report=load(path)
  refs=[{**ref,'path':PurePosixPath(ref['path']).name}for ref in old['actual_train_files']if str(PurePosixPath(ref['path']).parent)==bank]
  relative='compiled/curation10_rebase_'+PurePosixPath(bank).name+'_'+hs(bank)[:8]
  receipt={'status':'ADMIT_ROOT_SCOPED_REBASE_RETAINED_LOCAL_CREDIT_ONLY','source_compilation_report_sha256':sha(path),'original_compiled_bank':bank,
   'original_admission_receipts':deepcopy(old_receipts[bank]),'revocation_pin':deepcopy(f['revocations']),'freeze_sha256':freeze_sha}
  build_bank(source_root,refs,source_report,relative,lambda r:r['id']not in revoked,receipt);rebases.append({'old_bank':bank,'new_bank':relative})
 # Preserve original file order for unaffected banks; filtered files are appended.
 current['actual_train_files']=[deepcopy(ref)for ref in old['actual_train_files']if str(PurePosixPath(ref['path']).parent)not in affected]+newrefs
 newrefs=[]
 new_relative=f.get('new_bank_relative','compiled/curation10_process_01');safe(root,new_relative)
 build_bank(newroot,newreport['files'],newreport,new_relative,lambda r:r['id']in allowed,
   {'status':'ADMIT_ROOT_FROZEN_CURATION10_SCOPED_INPUT_AND_LOCAL_CREDIT_ONLY','source_compilation_report_sha256':sha(new_report_path),
    'root_semantic_acceptance':f['root_semantic_acceptance'],'independent_token_qa':f['independent_token_qa'],'revocation_pin':f['revocations'],'freeze_sha256':freeze_sha})
 current['actual_train_files']+=newrefs
 final_records=list(bank_records(root,current));recomputed=recount([r for _,_,r in final_records]);component_map=recomputed.pop('component_by_record_id')
 assert not {r['id']for _,_,r in final_records}&revoked and all(not blocked(r)for _,_,r in final_records)
 current.update(recomputed,design_revision='5.0.52',change_id='ALG-20261031-04',status='ACTUAL_REBASED_SCOPED_COMPONENT_DATA_NOT_FULL_WRD_READY',
  full_WRD_main_training_ready=False,default_full_pipeline_training_entrypoint=None,model_weights_loaded=False,training_started=False,is_training_launch_configuration=False,
  script_sha256=sha(__file__),curation10_rebase={'baseline_manifest_sha256':f['baseline_manifest_sha256'],'revoked_record_ids':sorted(revoked),
  'new_allowed_record_ids':sorted(allowed),'new_revoked_record_ids':sorted(new_revoked),'rebased_banks':rebases,'protected_sources':sorted(protected),
  'protected_scope_components':sorted(protected_groups),'revocation_pin':f['revocations'],'frozen_inputs_sha256':freeze_sha})
 # Historical admission summaries describe prior snapshots, not retained rows.
 history=current.setdefault('historical_admission_summaries',{})
 for key in['gap08_component_admission','source_only_new_controller_decision_targets']:
  if key in current:history[key]=current.pop(key)
 current['withdrawn_local_banks']=list(dict.fromkeys(current.get('withdrawn_local_banks',[])+sorted(affected)))
 staged=stage_dir/'TRAINING_MANIFEST10.json';save(staged,current)
 save(stage_dir/'ACTUAL_DATA_STATISTICS10.json',{k:current[k]for k in['status','design_revision','change_id','actual_counts','by_bank','by_stage','supervision_origin_tokens','distinct_source_ids','source_connected_components_across_banks','full_WRD_main_training_ready','training_started']})
 index=arrays(root,staged,final_records)
 spec=importlib.util.spec_from_file_location('canonical10_staged_loader',root/'canonical_arrays10/binary_loader10.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 for actual,(_,_,r)in zip(module.iter_features(root,manifest_override='manifest_staging10/TRAINING_MANIFEST10.json'),final_records,strict=True):
  expected_labels=[-100]*r['total_tokens'];expected_weights=[0.]*r['total_tokens']
  for a,b,_,w in r['supervision_spans']:
   for i in range(a,b):expected_labels[i]=r['input_ids'][i];expected_weights[i]=w
  assert actual=={'input_ids':r['input_ids'],'attention_mask':[1]*r['total_tokens'],'labels':expected_labels,'loss_weights':expected_weights}
 assert sha(oldpath)==f['baseline_manifest_sha256'],'ACTIVE_MANIFEST_CHANGED_DURING_STAGE'
 save(stage_dir/'STAGE_RECEIPT.json',{'status':'PASS_STAGED_REBASE_AND_COMPLETE_CANONICAL_ARRAYS_NOT_ACTIVATED','staged_manifest':pin(staged),
  'active_manifest_unchanged_sha256':sha(oldpath),'record_count':len(final_records),'binary_files':index['binary_files'],'canonical_index':pin(root/'canonical_arrays10/ARRAY_INDEX10.json'),
  'binary_loader':pin(root/'canonical_arrays10/binary_loader10.py'),
  'all_four_features_match_source':True,'design_markdown_changed':False,'training_started':False,'model_weights_loaded':False,'ai_cpu_curation_cost':'UNKNOWN_NOT_ZERO'})
 return load(stage_dir/'STAGE_RECEIPT.json')

def activate(root,freeze_path,freeze_sha,expected_staged_sha):
 root=Path(root).resolve();f=frozen_inputs(root,freeze_path,freeze_sha);directory=root/'manifest_staging10';receipt=load(directory/'STAGE_RECEIPT.json')
 staged=directory/'TRAINING_MANIFEST10.json';assert sha(staged)==expected_staged_sha==receipt['staged_manifest']['sha256']
 assert sha(root/'canonical_arrays10/ARRAY_INDEX10.json')==receipt['canonical_index']['sha256']
 loader=root/'canonical_arrays10/binary_loader10.py';assert sha(loader)==receipt['binary_loader']['sha256']and loader.read_text(encoding='utf-8')==loader_code()
 assert receipt['all_four_features_match_source']is True
 spec=importlib.util.spec_from_file_location('canonical10_activation_validation',loader);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 assert sum(1 for _ in module.iter_features(root,manifest_override='manifest_staging10/TRAINING_MANIFEST10.json'))==receipt['record_count']
 backup=root/'manifest_history'/('pre_curation10_'+f['baseline_manifest_sha256'][:16]);backup.mkdir(parents=True,exist_ok=False)
 for name in['TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json']:
  if(root/name).exists():shutil.copyfile(root/name,backup/name)
 # Stats first; manifest is the final activation pointer. No payload is run.
 for source,destination in[(directory/'ACTUAL_DATA_STATISTICS10.json',root/'ACTUAL_DATA_STATISTICS.json'),(staged,root/'TRAINING_MANIFEST.json')]:
  temporary=destination.with_name(destination.name+'.curation10.tmp');assert not temporary.exists();temporary.write_bytes(source.read_bytes());os.replace(temporary,destination)
 assert sha(root/'TRAINING_MANIFEST.json')==expected_staged_sha
 save(directory/'ACTIVATION_RECEIPT.json',{'status':'ACTIVATED_ROOT_FROZEN_CURATION10_SCOPED_DATA','manifest_sha256':expected_staged_sha,'original_manifest_backup':pin(backup/'TRAINING_MANIFEST.json'),'training_started':False})
 return load(directory/'ACTIVATION_RECEIPT.json')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=['stage','activate']);p.add_argument('--root',type=Path,required=True)
 p.add_argument('--freeze',type=Path,required=True);p.add_argument('--freeze-sha256',required=True);p.add_argument('--expected-staged-manifest-sha256')
 a=p.parse_args()
 if a.operation=='stage':result=stage(a.root,a.freeze,a.freeze_sha256)
 else:
  assert a.expected_staged_manifest_sha256,'EXPLICIT_STAGED_SHA_REQUIRED_FOR_ACTIVATION';result=activate(a.root,a.freeze,a.freeze_sha256,a.expected_staged_manifest_sha256)
 print(js(result))

