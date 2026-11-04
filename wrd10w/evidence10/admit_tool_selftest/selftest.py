"""Small synthetic-only tests. Never opens or writes the actual DATA hub."""
from pathlib import Path
import importlib.util,json,gzip,hashlib,shutil,sys
from array import array
ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/'research/data_prep/wrd_curation10/admit10.py'
OUT=Path(__file__).resolve().parent/'run02'
spec=importlib.util.spec_from_file_location('test_admit10',SCRIPT);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def save(p,x):m.save(p,x)
def row(identity,source,bank='source_contract_main',component='D'):
 ids=[11,12,13,14];spans=[[2,3,component,.25]]
 return {'id':identity,'bank':bank,'stage':'fixture_only','split':'train','source_ids':[source],'source_group_id':'g_'+source,
  'input_ids':ids,'total_tokens':4,'input_ids_sha256_u32le':hashlib.sha256(array('I',ids).tobytes()).hexdigest(),
  'supervision_spans':spans,'supervision_spans_sha256':m.hs(m.js(spans)),'supervised_tokens':1,'supervised_tokens_by_component':{component:1},
  'messages':[{'role':'user','content':'synthetic'},{'role':'assistant','content':'synthetic','tool_calls':[{'id':'call_'+identity}]}],
  'targets':[{'message_index':1,'owned_supervision_spans':spans}],
  'binary_arrays':{'legacy':'C:/not-portable-and-deliberately-ignored'},
  'original_record_metadata':{'owner_id':identity,'training_admitted':True,'source_admission':'ADMIT','supervision_message_indices':[1],
    'actual_native_tool_dispatch':False,'teacher_original_R_supervised':False}}
def bank(directory,records):
 directory.mkdir(parents=True);p=directory/'train.jsonl.gz';m.write_lines(p,[(json.dumps(r,ensure_ascii=False,indent=None)+'\n').encode()for r in records])
 save(directory/'CAUSAL_TEMPLATE.json',{'variant':'synthetic-do-not-train'})
 refs=[{'path':p.name,'bytes':p.stat().st_size,'sha256':m.sha(p)}]
 report={'counts':{},'files':refs};save(directory/'COMPILATION_REPORT.json',report);return report
def fixture(base):
 base.mkdir(parents=True);data=base/'data';data.mkdir();new=base/'new'
 old=[row('oldclean','clean'),row('oldbad','bad'),row('unaffected','other')]
 bank(data/'compiled/old1',old[:2]);bank(data/'compiled/old2',old[2:])
 files=[];reports=[]
 for name in ['old1','old2']:
  d=data/'compiled'/name;r=m.load(d/'COMPILATION_REPORT.json')
  files.extend({**x,'path':'compiled/'+name+'/'+x['path']}for x in r['files']);reports.append({'path':'compiled/'+name+'/COMPILATION_REPORT.json','sha256':m.sha(d/'COMPILATION_REPORT.json')})
 counted=m.recount(old);counted.pop('component_by_record_id')
 manifest={'status':'SYNTHETIC_FIXTURE_ONLY','actual_train_files':files,'active_compilation_reports':reports,'external_root_admission_receipts':[],**counted}
 save(data/'TRAINING_MANIFEST.json',manifest);save(data/'ACTUAL_DATA_STATISTICS.json',{'fixture':True})
 p=data/'clean_inputs/source_scope.metadata.jsonl.gz';p.parent.mkdir()
 with gzip.open(p,'wt',encoding='utf-8')as f:
  for s in ['clean','bad','other','new']:f.write(json.dumps({'source_id':s,'status':'TRAIN','component_id':'scope_'+s})+'\n')
 newreport=bank(new,[row('newclean','new','curation10_fixture','A'),row('newbad','bad','curation10_fixture','A')])
 rev={'status':'ROOT_APPROVED_REVOCATION_SET','baseline_manifest_sha256':m.sha(data/'TRAINING_MANIFEST.json'),'revoked_record_ids':['oldbad'],
  'protected_source_ids':['bad'],'protected_source_scope_components':['scope_bad'],'new_allowed_record_ids':['newclean'],'new_revoked_record_ids':['newbad']}
 save(base/'rev.json',rev);save(base/'accept.json',{'status':'ADMIT_SYNTHETIC_FIXTURE_ONLY','record_ids':['newclean'],'compilation_report_sha256':m.sha(new/'COMPILATION_REPORT.json')})
 save(base/'qa.json',{'status':'PASS_SYNTHETIC_FIXTURE_ONLY'})
 f={'status':'ROOT_FROZEN_CURATION10_STAGE_AUTHORIZATION','admit10_script_sha256':m.sha(SCRIPT),'baseline_manifest_sha256':m.sha(data/'TRAINING_MANIFEST.json')}
 for key,p in [('revocations',base/'rev.json'),('new_compilation_report',new/'COMPILATION_REPORT.json'),('root_semantic_acceptance',base/'accept.json'),('independent_token_qa',base/'qa.json')]:f[key]=m.pin(p)
 save(base/'freeze.json',f);return data,base/'freeze.json'
def reload_freeze(f):
 x=m.load(f)
 for k in ['revocations','new_compilation_report','root_semantic_acceptance','independent_token_qa']:x[k]=m.pin(x[k]['path'])
 save(f,x)
def main():
 OUT.mkdir(exist_ok=False);tests=[]
 data,f=fixture(OUT/'valid');before={p.relative_to(data).as_posix():m.sha(p)for p in data.rglob('*')if p.is_file()}
 stage=m.stage(data,f,m.sha(f));assert stage['record_count']==3 and stage['binary_files']==9
 assert all(m.sha(data/p)==h for p,h in before.items());tests.append('STAGE_PRESERVES_ALL_OLD_FILES_AND_MAIN')
 active=m.load(data/'TRAINING_MANIFEST.json');future=m.load(data/'manifest_staging10/TRAINING_MANIFEST10.json')
 assert next(r for r in active['actual_train_files']if'/old2/'in r['path'])in future['actual_train_files'];tests.append('UNAFFECTED_REFERENCE_IDENTICAL')
 rr=list(m.bank_records(data,future));assert {r['id']for _,_,r in rr}=={'oldclean','unaffected','newclean'};tests.append('OLD_AND_NEW_REVOKED_IDS_FILTERED')
 original=row('oldclean','clean');assert next(r for _,_,r in rr if r['id']=='oldclean')==original;tests.append('RETAINED_ROW_ALL_VALUES_UNCHANGED')
 for proof in future['external_root_admission_receipts']:
  p=m.load(data/proof['path']);assert 'oldbad'not in p['record_ids']and'newbad'not in p['record_ids']
 tests.append('REBASE_RECEIPT_CLEAN_SUBSET_ONLY')
 loader=data/'canonical_arrays10/binary_loader10.py';s=importlib.util.spec_from_file_location('fixture_binary10',loader);l=importlib.util.module_from_spec(s);s.loader.exec_module(l)
 features=list(l.iter_features(data,manifest_override='manifest_staging10/TRAINING_MANIFEST10.json'));assert len(features)==3
 assert all(x['labels']==[-100,-100,13,-100]and x['loss_weights']==[0.,0.,.25,0.]and x['attention_mask']==[1]*4 for x in features);tests.append('COMPLETE_BINARY_FEATURES_AND_LEGACY_REFS_IGNORED')
 try:list(l.iter_features(data))
 except AssertionError:tests.append('DEFAULT_LOADER_REJECTS_NOT_YET_ACTIVE_MANIFEST')
 else:raise AssertionError('old main accepted')
 # Repin a corrupt label file and index: source-span equality must still reject.
 ip=data/'canonical_arrays10/ARRAY_INDEX10.json';pp=data/'canonical_arrays10/INDEX_PIN10.json';ib=ip.read_bytes();pb=pp.read_bytes();ix=m.load(ip)
 ref=ix['records'][0]['arrays']['labels'];bp=data/ref['path'];bb=bp.read_bytes();bad=array('q');bad.frombytes(bb);bad[0]=11;bp.write_bytes(bad.tobytes());ref['sha256']=m.sha(bp);save(ip,ix)
 ppobj=m.load(pp);ppobj['index_bytes']=ip.stat().st_size;ppobj['index_sha256']=m.sha(ip);save(pp,ppobj)
 try:list(l.iter_features(data,manifest_override='manifest_staging10/TRAINING_MANIFEST10.json'))
 except AssertionError as e:assert 'LABELS' in str(e);tests.append('REPinned_BAD_MASK_REJECTED_BY_SOURCE_COMPARISON')
 else:raise AssertionError('corrupt binary accepted')
 bp.write_bytes(bb);ip.write_bytes(ib);pp.write_bytes(pb)
 result=m.activate(data,f,m.sha(f),m.sha(data/'manifest_staging10/TRAINING_MANIFEST10.json'));assert len(list(l.iter_features(data)))==3
 assert m.sha(data/'manifest_history'/('pre_curation10_'+before['TRAINING_MANIFEST.json'][:16])/'TRAINING_MANIFEST.json')==before['TRAINING_MANIFEST.json'];tests.append('EXPLICIT_ACTIVATION_AND_ORIGINAL_SNAPSHOT')
 for name,mutate in [('duplicate_revocation',lambda r:r['revoked_record_ids'].append('oldbad')),('unknown_revocation',lambda r:r['revoked_record_ids'].append('not-an-old-id')),('protected_new_allowed',lambda r:(r.update(new_allowed_record_ids=['newclean','newbad'],new_revoked_record_ids=[])))]:
  d,fp=fixture(OUT/name);rv=m.load(OUT/name/'rev.json');mutate(rv);save(OUT/name/'rev.json',rv);reload_freeze(fp);baseline=m.sha(d/'TRAINING_MANIFEST.json')
  try:m.stage(d,fp,m.sha(fp))
  except AssertionError:assert m.sha(d/'TRAINING_MANIFEST.json')==baseline;tests.append(name+'_REJECTED_WITH_MAIN_UNCHANGED')
  else:raise AssertionError(name+' accepted')
 d,fp=fixture(OUT/'bad_freeze')
 try:m.stage(d,fp,'0'*64)
 except AssertionError:tests.append('FREEZE_SHA_MISMATCH_REJECTED')
 else:raise AssertionError('bad freeze accepted')
 for badpath in ['../escape','C:/escape','x\\y','/absolute','x/../y','x/./y']:
  try:m.safe(OUT,badpath)
  except AssertionError:tests.append('UNSAFE_PATH_REJECTED_'+badpath)
  else:raise AssertionError('unsafe path accepted '+badpath)
 d,fp=fixture(OUT/'direct_closure');rv=m.load(OUT/'direct_closure/rev.json')
 save(OUT/'direct_closure/rev.json',{'status':'READY_FOR_ROOT_REBASE_REVIEW_MAIN_NOT_MODIFIED','main_manifest_pin':m.pin(d/'TRAINING_MANIFEST.json'),
  'revoke_current_view_ids':rv['revoked_record_ids'],'revoke_source_ids':rv['protected_source_ids'],'revoke_source_scope_component_ids':rv['protected_source_scope_components']})
 ff=m.load(fp);ff.update(new_allowed_record_ids=['newclean'],new_revoked_record_ids=['newbad'],
  expected_rebased_counts={'targets':2,'supervised_tokens':2,'input_tokens':8},expected_final_counts={'targets':3,'supervised_tokens':3,'input_tokens':12});save(fp,ff);reload_freeze(fp)
 assert m.stage(d,fp,m.sha(fp))['record_count']==3;tests.append('IMMUTABLE_FORMAL_CLOSURE_MAPPED_UNDER_ROOT_FROZEN_APPROVAL')
 d,fp=fixture(OUT/'wrong_expected_count');ff=m.load(fp);ff['expected_final_counts']={'targets':999};save(fp,ff)
 try:m.stage(d,fp,m.sha(fp))
 except AssertionError:assert not(d/'manifest_staging10').exists();tests.append('WRONG_FROZEN_EXPECTED_COUNTS_REJECTED_BEFORE_WRITES')
 else:raise AssertionError('wrong count accepted')
 save(OUT/'SELFTEST.json',{'status':'PASS_SYNTHETIC_ONLY_NOT_REAL_ADMISSION','tests':tests,'count':len(tests),'admit10_sha256':m.sha(SCRIPT),'real_DATA_read_or_changed':False,'training_started':False,'model_or_business_Agent_calls':0})
 print(json.dumps({'status':'PASS_SYNTHETIC_ONLY','tests':len(tests),'report_sha256':m.sha(OUT/'SELFTEST.json')}))
if __name__=='__main__':main()
