"""Expose the same four repeated real views as the full mixed control."""
from pathlib import Path
import json
from build_exposure11 import ROOT,WORK,BASE,SEED,make_schedule,summary,rows,load,save
def main():
 schedule=load(WORK/'exposure11_final/EXPOSURE_SCHEDULES11.json');reference=schedule['profiles']['full_native53']['full']
 ids=reference['explicit_repeated_real_ids'];assert len(ids)==4
 m=load(BASE/'TRAINING_MANIFEST.json');real=[]
 for _,_,r in rows(BASE,m['actual_train_files']):
  if r['bank']!='source_contract_main':real.append(summary(r,'real_process',r['source_group_id']))
 byid={r['id']:r for r in real};extended=real+[dict(byid[i],repeated_for_mixed_batch=True) for i in ids]
 result=make_schedule(extended,[]);result['explicit_repeated_real_ids']=ids
 assert result['sequence_exposures']==209 and result['unique_targets']==205 and result['optimizer_steps_candidate']==53
 result.update(scope='MATCH_REAL_VIEW_EXPOSURES_WITH_FULL_MIXED_ARM_NOT_MATCH_COMPUTE_OR_OPTIMIZER_STEPS',training_started=False)
 save(WORK/'exposure11_final/FULL_REAL_EXPOSURE_CONTROL11.json',result)
 print(json.dumps({k:v for k,v in result.items() if k!='steps'}))
if __name__=='__main__':main()
