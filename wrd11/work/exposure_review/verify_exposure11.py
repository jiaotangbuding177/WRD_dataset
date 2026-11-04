"""Independent actual-row exposure accounting; no loader/trainer is executed."""
from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
import gzip,hashlib,json,math
ROOT=Path('D:/skillloop');WORK=ROOT/'output/20261031_wrd_curation11';BASE=ROOT/'output/wrd10root01';OUT=WORK/'exposure_review'
MAIN_SHA='9aace2dc6b39d0dde3bafbf9f7f3d6763e485609017dd70a5c40c17a2c30277e'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(p):p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True)
def readrows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def metric(r):
 assert len(r['input_ids'])==r['total_tokens']
 assert sum(b-a for a,b,_,_ in r['supervision_spans'])==r['supervised_tokens']
 return {'sequence':len(r['input_ids']),'positive':r['supervised_tokens'],'mass':sum((Decimal(b-a)*Decimal(str(w))for a,b,_,w in r['supervision_spans']),Decimal(0))}
def approx(a,b):return abs(float(a)-float(b))<1e-7
def main():
 output=OUT/'INDEPENDENT_EXPOSURE_QA11.json';assert not output.exists()
 refs=[];bm=load(BASE/'TRAINING_MANIFEST.json');assert sha(BASE/'TRAINING_MANIFEST.json')==MAIN_SHA
 assert sha(ROOT/'output/20261027_wrd_main_v10/TRAINING_MANIFEST.json')==MAIN_SHA
 refs.append(pin(BASE/'TRAINING_MANIFEST.json'))
 allbase={};parents={}
 def find(x):
  parents.setdefault(x,x)
  if parents[x]!=x:parents[x]=find(parents[x])
  return parents[x]
 def join(a,b):
  a,b=find(a),find(b)
  if a!=b:parents[b]=a
 for ref in bm['actual_train_files']:
  p=BASE/ref['path'];assert pin(p)['sha256']==ref['sha256']and p.stat().st_size==ref['bytes'];refs.append(pin(p))
  for r in readrows(p):
   assert r['id']not in allbase
   allbase[r['id']]={'bank':r['bank'],'source_ids':r['source_ids'],'source_group_id':r['source_group_id'],**metric(r)}
   join('r:'+r['id'],'g:'+r['source_group_id'])
   for source in r['source_ids']:join('r:'+r['id'],'s:'+source)
 assert len(allbase)==623
 real={i:v for i,v in allbase.items()if v['bank']!='source_contract_main'}
 assert len(real)==205 and len({find('r:'+i)for i in real})==44 and len({s for x in real.values()for s in x['source_ids']})==56
 # Derive the nested cohort from actual case states, not the exposure summary.
 casepath=WORK/'controller_cases/run07/CASES.jsonl';cases={x['id']:x for x in (json.loads(l)for l in casepath.read_text(encoding='utf-8-sig').splitlines())}
 pilot_names={'材料索引','会议排版','网页交互','数据整理'}
 pairlinks=[]
 for fn in ['COUNTERFACTUAL_PAIRS.json','CROSS_CONDITION_PAIRS.json','POLICY_GUARD_PAIRS.json']:
  p=casepath.parent/fn;refs.append(pin(p))
  for e in load(p)['pairs']:
   pairlinks.append(e['case_ids']if 'case_ids'in e else[e['positive_case_id'],e['negative_case_id']])
 assert len(pairlinks)==320
 profiles={};targetmaps={}
 for profile,dirname in [('full_native53','curriculum01'),('budget_projection','budget_curriculum01')]:
  root=WORK/dirname;manifest=root/'CURRICULUM_MANIFEST11.json';m=load(manifest);refs.append(pin(manifest))
  assert set(m['base_reference']['real_process_ids'])==set(real)and m['base_reference']['main_manifest_sha256']==MAIN_SHA
  assert sha(BASE/'PAYLOAD_MANIFEST.json')==m['base_reference']['authenticated_payload_manifest_sha256']
  synthetic={};case_ids={};pilot=set();targetmaps[profile]={}
  for ref in m['synthetic_train_files']:
   p=root/ref['path'];assert sha(p)==ref['sha256']and p.stat().st_size==ref['bytes'];refs.append(pin(p))
   for r in readrows(p):
    ident=r['id'];assert ident not in synthetic and ident not in real
    meta=r['original_record_metadata'];cid=meta['case_id'];synthetic[ident]={'case_id':cid,'group':r['source_group_id'],**metric(r)};case_ids[cid]=ident
    targetmaps[profile][ident]=hashlib.sha256(js(r['messages'][-1]).encode()).hexdigest()
    if cid.startswith('cpu11-')or cases[cid]['point_time_state']['display_name']in pilot_names:pilot.add(ident)
  assert len(synthetic)==627 and len(pilot)==339
  assert len([i for i in pilot if synthetic[i]['case_id'].startswith('cpu11-')])==51
  profiles[profile]={'manifest_pin':pin(manifest),'synthetic':synthetic,'pilot':pilot,'case_ids':case_ids}
 assert set(profiles['full_native53']['synthetic'])==set(profiles['budget_projection']['synthetic'])
 assert targetmaps['full_native53']==targetmaps['budget_projection']
 def check_schedule(card,expected_synthetic,profile,mixed=True):
  synthetic=profiles[profile]['synthetic'];steps=card['steps'];count=Counter();idcount=Counter();mass=defaultdict(lambda:Decimal(0));seq=0;positive=0;sfrac=[];stepdetails=[]
  assert card['microbatch']==1 and card['accumulation_max']==4 and card['last_partial_accumulation_flushed']is True
  assert len(steps)==card['optimizer_steps_candidate']and all(1<=len(b)<=4 for b in steps)
  assert all(len(b)==4 for b in steps[:-1])
  for n,batch in enumerate(steps):
   assert len({x['id']for x in batch})==len(batch)
   pools=Counter();bmasses=defaultdict(lambda:Decimal(0));bseq=0;bpos=0
   for item in batch:
    i,pool=item['id'],item['pool'];assert pool in {'real_process','synthetic'}
    row=real[i]if pool=='real_process'else synthetic[i]
    if pool=='synthetic':assert i in expected_synthetic
    count[pool]+=1;idcount[i]+=1;mass[pool]+=row['mass'];seq+=row['sequence'];positive+=row['positive']
    pools[pool]+=1;bmasses[pool]+=row['mass'];bseq+=row['sequence'];bpos+=row['positive']
   if mixed:assert pools['real_process']>=1
   fraction=float(bmasses['synthetic']/(bmasses['real_process']+bmasses['synthetic']))
   sfrac.append(fraction);stepdetails.append({'step1based':n+1,'sequence_tokens':bseq,'positive_tokens':bpos,'pool_counts':dict(pools),'mass_by_pool':{k:float(v)for k,v in bmasses.items()},'synthetic_mass_fraction_bookkeeping_only':fraction})
  assert {i for i in idcount if i in real}==set(real)
  assert {i for i in idcount if i in synthetic}==set(expected_synthetic)
  assert all(idcount[i]==1 for i in expected_synthetic)
  repeats=Counter(card['explicit_repeated_real_ids']);assert all(i in real for i in repeats)
  assert all(idcount[i]==1+repeats[i]for i in real)
  assert card['sequence_exposures']==sum(count.values())and card['unique_targets']==len(idcount)
  assert card['sequence_tokens_unpadded']==seq and card['positive_tokens_exposed']==positive and approx(card['weighted_mass_exposed'],sum(mass.values()))
  assert card['exposure_count_by_pool']==dict(count)
  assert set(card['weighted_mass_by_pool'])==set(count)and all(approx(card['weighted_mass_by_pool'][k],mass[k])for k in count)
  if mixed:
   assert card['at_least_one_existing_process_sequence_each_mixed_optimizer_step']is True
   assert float(mass['synthetic']/sum(mass.values()))<=0.20
  closure=[]
  chosen_cases={synthetic[i]['case_id']for i in expected_synthetic}
  for pair in pairlinks:
   seen=[c in chosen_cases for c in pair];assert seen[0]==seen[1],'PARTIAL_COUNTERFACTUAL_PAIR'
   if all(seen):closure.append(pair)
  result={'steps':len(steps),'exposures':sum(count.values()),'unique_targets':len(idcount),'sequence_tokens':seq,'positive_tokens':positive,'mass':float(sum(mass.values())),
   'pool_exposures':dict(count),'pool_mass':{k:float(v)for k,v in mass.items()},'repeated_real_ids':list(card['explicit_repeated_real_ids']),
   'counterfactual_links_closed':len(closure),'synthetic_mass_fraction_global':float(mass['synthetic']/sum(mass.values())),
   'max_step_synthetic_mass_fraction_bookkeeping':max(sfrac),'steps_over20_percent_synthetic_mass':sum(x>0.20 for x in sfrac),
   'global_cap_not_a_per_step_or_gradient_norm_guarantee':True,'last_step_exposures':len(steps[-1]),'every_mixed_step_has_real':all(any(x['pool']=='real_process'for x in b)for b in steps)if mixed else None}
  return result,stepdetails,idcount
 def check_file(dirname):
  root=WORK/dirname;p=root/'EXPOSURE_SCHEDULES11.json';schedule=load(p);summary=load(root/'SUMMARY.json');refs.extend([pin(p),pin(root/'SUMMARY.json')]);details={};totals={};multisets={}
  for profile,pdata in schedule['profiles'].items():
   assert pdata['source_manifest_sha256']==profiles[profile]['manifest_pin']['sha256']
   assert set(pdata['pilot_synthetic_ids'])==profiles[profile]['pilot']and set(pdata['full_synthetic_ids'])==set(profiles[profile]['synthetic'])
   totals[profile]={};details[profile]={};multisets[profile]={}
   for mode in ['real_only','pilot','full']:
    card=pdata[mode];expected=set()if mode=='real_only'else(profiles[profile]['pilot']if mode=='pilot'else set(profiles[profile]['synthetic']))
    actual,d,idcount=check_schedule(card,expected,profile,mixed=mode!='real_only')
    assert summary['profiles'][profile][mode]=={k:v for k,v in card.items()if k!='steps'}
    totals[profile][mode]=actual;details[profile][mode]=d;multisets[profile][mode]=idcount
    if mode=='real_only':assert (actual['steps'],actual['exposures'],len(actual['repeated_real_ids']))==(52,205,0)
    elif mode=='pilot':assert (actual['steps'],actual['exposures'],len(actual['repeated_real_ids']))==(136,544,0)and actual['counterfactual_links_closed']==160
    else:assert (actual['steps'],actual['exposures'],len(actual['repeated_real_ids']))==(209,836,4)and actual['counterfactual_links_closed']==320
  equal={};mismatch={}
  for mode in ['real_only','pilot','full']:
   a,b=schedule['profiles']['full_native53'][mode]['steps'],schedule['profiles']['budget_projection'][mode]['steps']
   equal[mode]=a==b;mismatch[mode]=sum(x!=y for x,y in zip(a,b))
   assert multisets['full_native53'][mode]==multisets['budget_projection'][mode]
  controlpath=root/'FULL_REAL_EXPOSURE_CONTROL11.json';control=load(controlpath);refs.append(pin(controlpath));rcontrol,dc,ic=check_schedule(control,set(),'full_native53',mixed=False)
  assert (rcontrol['steps'],rcontrol['exposures'],rcontrol['unique_targets'],rcontrol['last_step_exposures'])==(53,209,205,1)
  for profile in profiles:
   target=Counter({i:n for i,n in multisets[profile]['full'].items()if i in real})
   assert target==ic
   assert approx(rcontrol['mass'],totals[profile]['full']['pool_mass']['real_process'])
  return {'directory':dirname,'numerical_and_pair_accounting':'PASS','identical_ID_order_per_step_across_profiles':equal,'mismatched_steps_across_profiles':mismatch,
   'actual_schedule_totals':totals,'full_real_exposure_control':rcontrol,'control_real_multiset_matches_full_mixed':True,
   'control_is_real_exposure_matched_not_optimizer_step_or_compute_matched':True},details
 old,olddetails=check_file('exposure11');assert old['mismatched_steps_across_profiles']=={'real_only':0,'pilot':113,'full':209}
 final,details=check_file('exposure11_final');assert all(final['identical_ID_order_per_step_across_profiles'].values())
 assert (WORK/'exposure11/EXPOSURE_SCHEDULES11.json').read_bytes()!=(WORK/'exposure11_final/EXPOSURE_SCHEDULES11.json').read_bytes()
 # Every proof binds actual rows; artifacts are unchanged during this audit.
 for ref in refs:assert pin(ref['path'])==ref
 report={'schema':'wrd11-independent-actual-row-exposure-accounting','status':'PASS_FINAL_EXPOSURE11_WITH_OLD_PROFILE_ORDER_CONFOUND_PRESERVED',
  'actual_row_input_pins':refs,'review_script_pin':pin(__file__),'real_main623_pin_unchanged':MAIN_SHA,
  'real_process_targets_independently_recounted':205,'real_process_source_ids':56,'real_process_global_connected_groups_from_all623_DSU':44,
  'synthetic_target_ids_same_across_profiles':627,'same_assistant_target_text_across_profiles':True,'pilot_synthetic':339,'pilot_controller':288,'pilot_resource':51,
  'pilot_is_first4_display_parameter_contexts_not4_independent_domains_or_holdout_groups':True,
  'original_exposure11_finding':old,'accepted_exposure11_final':final,
  'remaining_optimizer_or_compute_match_control_needed_for_causal_claim':True,
  'profile_conditioning_note':'Both profiles are mutually-exclusive interfaces over the same627 target IDs. budget selection uses known offline target structure to construct a declared decision-only task; it is not an inference-time selector using unknown gold answers and does not alter the native environment.',
  'low_weight_note':'Global synthetic weighted label mass stays below20%; some individual steps exceed20%. This is only bookkeeping and does not claim per-step gradient norm proportions or model quality.',
  'native_business_calls':0,'model_forward_or_training_runs':0,'complete_autonomous_or_real_KEEP_claim':False}
 OUT.mkdir(parents=True,exist_ok=True);output.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
 (OUT/'PER_STEP_ACTUAL_ACCOUNTING11.json').write_bytes((json.dumps({'final':details,'old':olddetails},ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({'status':report['status'],'QA_sha256':sha(output),'final_totals':final['actual_schedule_totals'],'control':final['full_real_exposure_control']},ensure_ascii=False))
if __name__=='__main__':main()
