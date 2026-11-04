"""Root-reviewed, finite-scope admissions only; no model execution or trainer."""
from pathlib import Path
from collections import Counter,defaultdict,deque
from copy import deepcopy
import gzip,hashlib,json,math,shutil
ROOT=Path('D:/skillloop');HERE=Path(__file__).parent
DATA=ROOT/'output/20261027_wrd_main_v10';WORK=ROOT/'output/20261029_wrd_delivery07'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8-sig') as f:
        return [json.loads(l) for l in f if l.strip()]
def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    accepted=load(HERE/'ROOT_ACCEPTANCE.json')
    assert accepted['status']=='ADMIT_ONLY_SPECIFIED_NEW_STATES_AFTER_CONTENT_AND_CAUSAL_REVIEW'
    base=load(DATA/'TRAINING_MANIFEST.json');baseline=load(HERE/'RUN_SCOPE.json')['baseline_manifest']
    assert sha(DATA/'TRAINING_MANIFEST.json')==baseline['sha256']
    assert base['actual_counts']['targets']==530
    for ref in accepted['required_files']:
        p=Path(ref['path']);assert p.stat().st_size==ref['bytes'] and sha(p)==ref['sha256']
    WORK.mkdir(exist_ok=False)
    history=DATA/'manifest_history/pre_batch07_530_20261029';history.mkdir(exist_ok=False)
    for n in ['TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json']:shutil.copyfile(DATA/n,history/n)
    m=deepcopy(base);newrows=[]
    for bank in accepted['banks']:
        source=Path(bank['compiled_directory']);dest=DATA/'compiled'/bank['name']
        dest.mkdir(exist_ok=False)
        report=load(source/'COMPILATION_REPORT.json');ids=[]
        for file in report['files']:
            p=source/file['path'];assert sha(p)==file['sha256'] and p.stat().st_size==file['bytes']
            rs=rows(p)
            for row in rs:
                meta=row['original_record_metadata']
                assert meta['training_admitted'] is True and meta['source_admission']=='ADMIT'
                assert meta.get('root_main_admission') is False and meta['requires_external_root_admission'] is True
                assert row['bank']==bank['name'] and row['split']=='train'
                assert row['id'] in bank['record_ids']
                assert not row.get('is_full_autonomous_execution_demonstration')
                assert not any(meta.get(k) for k in ['original226','holdout12','protected_sources_visible_prefix','protected_source_ids'])
                ids.append(row['id']);newrows.append(row)
            shutil.copyfile(p,dest/file['path'])
            m['actual_train_files'].append({**file,'path':'compiled/'+bank['name']+'/'+file['path']})
        assert sorted(ids)==sorted(bank['record_ids'])
        for n in ['COMPILATION_REPORT.json','CAUSAL_TEMPLATE.json','held.jsonl.gz']:shutil.copyfile(source/n,dest/n)
        proof={'status':'ADMIT_BOUNDED_NEW_STATE_DECISIONS_OR_PRE_RECEIPT_EXPLORATION',
            'record_ids':ids,'compilation_report_sha256':sha(dest/'COMPILATION_REPORT.json'),
            'root_acceptance_path':str(HERE/'ROOT_ACCEPTANCE.json'),'root_acceptance_sha256':sha(HERE/'ROOT_ACCEPTANCE.json'),
            'scope':bank['scope'],'new_input_not_original_native_equivalence':True,
            'original_R_added':0,'full_resource_construction_credit_added':0,'confirmed_repair_credit_added':0,
            'positive_skill_KEEP_added':0,'single_native_autonomous_chains_added':0,'training_started':False}
        save(dest/'ROOT_SEMANTIC_ADMISSION.json',proof)
        prefix='compiled/'+bank['name']
        m['active_compilation_reports'].append({'path':prefix+'/COMPILATION_REPORT.json','sha256':sha(dest/'COMPILATION_REPORT.json')})
        m['external_root_admission_receipts'].append({'path':prefix+'/ROOT_SEMANTIC_ADMISSION.json','sha256':sha(dest/'ROOT_SEMANTIC_ADMISSION.json'),'compiled_bank':prefix,'scope':bank['scope']})
    allrows=[r for f in m['actual_train_files'] for r in rows(DATA/f['path'])]
    total=Counter();bybank=defaultdict(Counter);bystage=defaultdict(Counter);sources=set();parents={}
    def find(x):
        parents.setdefault(x,x)
        if parents[x]!=x:parents[x]=find(parents[x])
        return parents[x]
    def join(a,b):
        a,b=find(a),find(b)
        if a!=b:parents[max(a,b)]=min(a,b)
    owners=set()
    for r in allrows:
        meta=r['original_record_metadata'];owner=meta.get('owner_id',r['id'])
        assert owner not in owners;owners.add(owner)
        for sid in r['source_ids']:sources.add(sid);join('r:'+r['id'],'s:'+sid)
        join('r:'+r['id'],'g:'+r['source_group_id'])
        for c in [total,bybank[r['bank']],bystage[r['stage']]]:
            c.update(sequences=1,targets=len(meta['supervision_message_indices']),input_tokens=r['total_tokens'],supervised_tokens=r['supervised_tokens'],le16k_sequences=int(r['total_tokens']<=16384),le32k_sequences=int(r['total_tokens']<=32768))
            for k,v in r['supervised_tokens_by_component'].items():c['component_'+k]+=v
    origins=Counter()
    for r in newrows:
        for k,v in r['supervised_tokens_by_component'].items():
            if r['bank']=='source_only_controller_batch24':origins['new_authored_source_only_controller_'+k+'_tokens']+=v
            else:assert k=='A';origins['new_authored_native_action_projection_A_tokens']+=v
    for k,v in origins.items():m['supervision_origin_tokens'][k]=m['supervision_origin_tokens'].get(k,0)+v
    assert sum(m['supervision_origin_tokens'].values())==total['supervised_tokens']
    m.update(design_revision='5.0.46',change_id='ALG-20261029-04',actual_counts=dict(total),by_bank={k:dict(v) for k,v in bybank.items()},by_stage={k:dict(v) for k,v in bystage.items()},distinct_source_ids=len(sources),source_connected_components_across_banks=len({find('r:'+r['id']) for r in allrows}),script_sha256=sha(__file__),training_started=False)
    m['source_only_new_controller_decision_targets']=sum(r['bank']=='source_only_controller_batch24' for r in newrows)
    m['new_authored_projected_action_owners']+=sum(r['bank']!='source_only_controller_batch24' for r in newrows)
    m['new_states_are_not_recovered_original_reasoning_or_verified_pipeline_execution']=True
    m['batch07_root_acceptance_sha256']=sha(HERE/'ROOT_ACCEPTANCE.json')
    assert total['targets']==530+len(newrows)
    save(DATA/'TRAINING_MANIFEST.json',m)
    save(DATA/'ACTUAL_DATA_STATISTICS.json',{k:m[k] for k in ['status','design_revision','actual_counts','by_stage','by_bank','supervision_origin_tokens','distinct_source_ids','source_connected_components_across_banks','missing_main_stages','full_WRD_main_training_ready','training_started']})
    inventory=defaultdict(Counter);proc_sources=set();proc_components=set();groups=defaultdict(list)
    for r in allrows:
        is_contract=r['bank']=='source_contract_main';phase='A_contract' if is_contract else 'process'
        component=find('r:'+r['id']);groups[(phase,component)].append(r)
        if not is_contract:proc_sources.update(r['source_ids']);proc_components.add(component)
        for key in ['all','contracts' if is_contract else 'process']:
            inventory[key].update(targets=1,input_tokens=r['total_tokens'],supervised_tokens=r['supervised_tokens'],weighted_label_mass=sum((b-a)*w for a,b,k,w in r['supervision_spans']),le16K=int(r['total_tokens']<=16384),le32K=int(r['total_tokens']<=32768))
    def rotate(phase):
        buckets=[deque(sorted(v,key=lambda x:x['id'])) for (p,c),v in sorted(groups.items()) if p==phase]
        ordered=[]
        while any(buckets):
            for b in buckets:
                if b:ordered.append(b.popleft())
        return ordered
    schedules=[];update=0;primary=0
    for phase,epoch,acc in [('A_contract',1,16),('process',1,4),('process',2,4),('process',3,4)]:
        seq=rotate(phase)
        for i,r in enumerate(seq):schedules.append({'phase':phase,'pass':epoch,'optimizer_update':update+i//acc+1,'microbatch':i%acc+1,'id':r['id'],'owner':r['original_record_metadata'].get('owner_id',r['id']),'joined_component':find('r:'+r['id']),'bank':r['bank'],'tokens':r['total_tokens'],'supervised_tokens':r['supervised_tokens'],'weighted_labels':sum((b-a)*w for a,b,k,w in r['supervision_spans'])})
        update+=math.ceil(len(seq)/acc)
        if phase=='process' and epoch==1:primary=update
    denominators=defaultdict(Counter)
    for x in schedules:denominators[x['optimizer_update']].update(sequences=1,tokens=x['tokens'],valid_labels=x['supervised_tokens'])
    save(WORK/'OWNER_EXPOSURE_SCHEDULE.json',{'status':'PROPOSED_NOT_RUN','is_launch_configuration':False,'manifest_sha256':sha(DATA/'TRAINING_MANIFEST.json'),'primary_stop_after_update':primary,'maximum_updates_if_dev_justifies_three_process_passes':update,'additional_passes_require_dev_evidence':True,'schedule':schedules,'per_update_valid_label_denominators':dict(denominators),'training_started':False})
    save(WORK/'CURRENT_DATA_AND_EXPOSURE.json',{'status':'ACTUAL_ARRAY_INVENTORY_AND_UNRUN_EXPOSURE_PLAN','inventory':{k:dict(v) for k,v in inventory.items()},'process_distinct_source_ids':len(proc_sources),'process_joined_components':len(proc_components),'primary_updates':primary,'maximum_updates':update,'new_data_origin_tokens':dict(origins),'new_targets':len(newrows),'full_WRD_main_training_ready':False,'qualified_keep_chains':0,'single_native_autonomous_chains':0,'independent_dev_test_arrays':0,'curation_AI_and_CPU_cost':'PERFORMED_USAGE_UNKNOWN_NOT_ZERO','new_business_teacher_actor_sessions':0,'training_started':False})
    print(json.dumps({'counts':dict(total),'new_targets':len(newrows),'new_origin_tokens':dict(origins),'sources':len(sources),'process_sources':len(proc_sources),'primary_updates':primary,'maximum_updates':update},ensure_ascii=False))
if __name__=='__main__':main()
