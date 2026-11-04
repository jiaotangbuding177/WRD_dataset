"""Recount explicit banks and write a non-launching owner exposure schedule."""
from collections import Counter,defaultdict,deque
import gzip,hashlib,json,math
from pathlib import Path
from copy import deepcopy

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261027_wrd_main_v10'
WORK=ROOT/'output/20261029_wrd_delivery05'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8')as f:
  for l in f:
   if l.strip():yield json.loads(l)

def main():
 old=load(OUT/'TRAINING_MANIFEST.json');assert old['actual_counts']['targets']==526
 history=OUT/'manifest_history/pre_checkpoint05_526_20261029';history.mkdir(exist_ok=False)
 for n in ['TRAINING_MANIFEST.json','ACTUAL_DATA_STATISTICS.json']:(history/n).write_bytes((OUT/n).read_bytes())
 m=deepcopy(old)
 for bank in ['historical_style_repair_02','historical_helpers_construction_01','historical_test_oracle_repair_02']:
  relative='compiled/'+bank;report=load(OUT/relative/'COMPILATION_REPORT.json')
  m['active_compilation_reports'].append({'path':relative+'/COMPILATION_REPORT.json','sha256':digest(OUT/relative/'COMPILATION_REPORT.json')})
  for ref in report['files']:m['actual_train_files'].append({**ref,'path':relative+'/'+ref['path']})
  proof=relative+'/ROOT_SEMANTIC_ADMISSION.json'
  m['external_root_admission_receipts'].append({'path':proof,'sha256':digest(OUT/proof),'compiled_bank':relative,'scope':'scoped_resource_or_test_repair_not_whole_skill'})
 counts=Counter();banks=defaultdict(Counter);stages=defaultdict(Counter);allrows=[];sources=set();owners=set();u={}
 def find(x):
  u.setdefault(x,x)
  if u[x]!=x:u[x]=find(u[x])
  return u[x]
 def join(x,y):
  a,b=find(x),find(y)
  if a!=b:u[max(a,b)]=min(a,b)
 for ref in m['actual_train_files']:
  p=OUT/ref['path'];assert digest(p)==ref['sha256'] and p.stat().st_size==ref['bytes']
  for r in rows(p):
   meta=r['original_record_metadata'];owner=meta.get('owner_id',r['id']);assert owner not in owners;owners.add(owner)
   allrows.append(r);join('r:'+r['id'],'g:'+r['source_group_id'])
   for source in r['source_ids']:sources.add(source);join('r:'+r['id'],'s:'+source)
   for c in [counts,banks[r['bank']],stages[r['stage']]]:
    c.update(sequences=1,targets=len(meta['supervision_message_indices']),input_tokens=r['total_tokens'],supervised_tokens=r['supervised_tokens'],le16k_sequences=int(r['total_tokens']<=16384),le32k_sequences=int(r['total_tokens']<=32768))
    for k,v in r['supervised_tokens_by_component'].items():c['component_'+k]+=v
 m.update(design_revision='5.0.43',change_id='ALG-20261029-01',actual_counts=dict(counts),
          by_bank={k:dict(v)for k,v in banks.items()},by_stage={k:dict(v)for k,v in stages.items()},
          distinct_source_ids=len(sources),source_connected_components_across_banks=len({find('r:'+r['id'])for r in allrows}),
          new_authored_projected_action_owners=old['new_authored_projected_action_owners']+3,
          recorded_cumulative_original_R_excerpt_owners=1,
          script_sha256=digest(__file__),training_started=False,full_WRD_main_training_ready=False)
 m['supervision_origin_tokens']['new_authored_R_tokens']+=126
 m['supervision_origin_tokens']['new_authored_native_action_projection_A_tokens']+=2396
 m['supervision_origin_tokens']['recorded_cumulative_original_R_excerpt_tokens']=391
 assert sum(m['supervision_origin_tokens'].values())==counts['supervised_tokens']
 m['all_original_R_sources_are_not_equivalent_to_per_turn_native_reasoning']=True
 m['cumulative_excerpt_does_not_add_independent_source_or_complete_trajectory']=True
 m['withdrawn_local_banks']+=['historical_v6_action_recovery_01/test_oracle_repair_01/native_projection_01']
 save(OUT/'TRAINING_MANIFEST.json',m)
 save(OUT/'ACTUAL_DATA_STATISTICS.json',{k:m[k]for k in ['status','actual_counts','by_stage','by_bank','supervision_origin_tokens','distinct_source_ids','source_connected_components_across_banks','missing_main_stages','full_WRD_main_training_ready','training_started']})
 # Round-robin connected source components, then rotate banks within each component.
 contracts=[r for r in allrows if r['bank']=='source_contract_main']
 process=[r for r in allrows if r['bank']!='source_contract_main']
 def rr(records):
  groups=defaultdict(lambda:defaultdict(deque))
  for r in sorted(records,key=lambda r:r['id']):groups[find('r:'+r['id'])][r['bank']].append(r)
  component_queues={}
  for g,bb in sorted(groups.items()):
   q=deque();names=deque(sorted(bb))
   while names:
    n=names.popleft();q.append(bb[n].popleft())
    if bb[n]:names.append(n)
   component_queues[g]=q
  names=deque(sorted(component_queues));ordered=[]
  while names:
   g=names.popleft();ordered.append(component_queues[g].popleft())
   if component_queues[g]:names.append(g)
  return ordered
 A=rr(contracts);P=rr(process);schedule=[]
 def append(records,phase,pass_number,accum,offset):
  for i,r in enumerate(records):schedule.append({'phase':phase,'pass':pass_number,'optimizer_update':offset+i//accum+1,'microbatch':i%accum+1,
   'id':r['id'],'owner':r['original_record_metadata'].get('owner_id',r['id']),'joined_component':find('r:'+r['id']),
   'bank':r['bank'],'tokens':r['total_tokens'],'supervised_tokens':r['supervised_tokens'],
   'weighted_labels':sum((b-a)*w for a,b,_,w in r['supervision_spans'])})
 append(A,'A_contract',1,16,0);a_steps=math.ceil(len(A)/16);p_steps=math.ceil(len(P)/4)
 for epoch in range(1,4):append(P,'process',epoch,4,a_steps+(epoch-1)*p_steps)
 perstep=defaultdict(lambda:Counter())
 for r in schedule:perstep[r['optimizer_update']].update(sequences=1,tokens=r['tokens'],valid_labels=r['supervised_tokens'])
 inventory={}
 for name,records in [('contracts',contracts),('process',process),('all',allrows)]:
  inventory[name]={'targets':len(records),'input_tokens':sum(r['total_tokens']for r in records),
   'supervised_tokens':sum(r['supervised_tokens']for r in records),'weighted_label_mass':sum((b-a)*w for r in records for a,b,_,w in r['supervision_spans']),
   'source_ids':len({s for r in records for s in r['source_ids']}),'joined_components':len({find('r:'+r['id'])for r in records}),
   'le16K':sum(r['total_tokens']<=16384 for r in records),'le32K':len(records)}
 inv={'status':'ACTUAL_INVENTORY_AND_PROPOSED_NOT_EXECUTED_EXPOSURE','design_revision':'5.0.43','inventory':inventory,
      'contract_accum16_updates':a_steps,'process_accum4_updates_per_full_pass':p_steps,'primary_matched_updates':a_steps+p_steps,
      'maximum_matched_updates_three_process_passes':a_steps+3*p_steps,'per_pass_exposure_limits':1,
      'row_repetition_does_not_increase_independent_data':True,'full_WRD_main_ready':False,'training_started':False}
 save(WORK/'CURRENT_DATA_AND_EXPOSURE.json',inv)
 save(WORK/'OWNER_EXPOSURE_SCHEDULE.json',{'is_launch_configuration':False,'status':'PROPOSED_CPU_SCHEDULE_NOT_RUN',
      'manifest_sha256':digest(OUT/'TRAINING_MANIFEST.json'),'primary_stop_after_update':a_steps+p_steps,
      'additional_passes_require_independent_dev_evidence':True,'schedule':schedule,'per_update_valid_label_denominators':dict(perstep),
      'normalize_across_whole_update_not_each_microbatch_mean':True,'training_started':False})
 print(json.dumps(inv,ensure_ascii=False))

if __name__=='__main__':main()
