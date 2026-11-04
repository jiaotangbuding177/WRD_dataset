"""Freeze deterministic research exposure cards; never runs a training step."""
from pathlib import Path
from collections import defaultdict,Counter,deque
import hashlib,json,math,random
from curriculum_loader11 import rows,load,sha
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation11'
OUT=WORK/'exposure11_final';BASE=ROOT/'output/wrd10root01';SEED=20261031
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def summary(r,pool,group):
 return {'id':r['id'],'pool':pool,'group':group,'sequence_tokens':r['total_tokens'],'positive_tokens':r['supervised_tokens'],
  'weighted_mass':sum((b-a)*w for a,b,c,w in r['supervision_spans'])}
def ordered(items,seed):
 groups=defaultdict(list)
 for x in items:groups[x['group']].append(x)
 rng=random.Random(seed);names=sorted(groups);rng.shuffle(names)
 for name in sorted(groups):
  groups[name].sort(key=lambda x:(x['id'],x.get('repeated_for_mixed_batch',False)))
  rng.shuffle(groups[name])
 queues={n:deque(groups[n]) for n in names};out=[]
 while any(queues.values()):
  for n in names:
   if queues[n]:out.append(queues[n].popleft())
 return out
def make_schedule(real,synthetic):
 if not synthetic:
  real=ordered(real,SEED);steps=[real[i:i+4] for i in range(0,len(real),4)];repeats=[]
 else:
  count=max(math.ceil((len(real)+len(synthetic))/4),math.ceil(len(synthetic)/3))
  real=ordered(real,SEED);repeats=[]
  while len(real)<count:
   original=real[len(repeats)%len(real)];real.append(dict(original,repeated_for_mixed_batch=True));repeats.append(original['id'])
  realq=deque(real);sq=deque(ordered(synthetic,SEED+1));steps=[]
  for i in range(count):
   batch=[realq.popleft()]
   remaining_steps=count-i-1
   # Reserve one real for every later optimizer step.
   while len(batch)<4 and len(realq)>remaining_steps:batch.append(realq.popleft())
   while len(batch)<4 and sq:batch.append(sq.popleft())
   steps.append(batch)
  assert not realq and not sq and all(any(x['pool']=='real_process' for x in b) for b in steps)
 exposures=[x for b in steps for x in b];count=Counter();mass=Counter()
 for x in exposures:count[x['pool']]+=1;mass[x['pool']]+=x['weighted_mass']
 return {'microbatch':1,'accumulation_max':4,'optimizer_steps_candidate':len(steps),'sequence_exposures':len(exposures),
  'unique_targets':len({x['id'] for x in exposures}),'sequence_tokens_unpadded':sum(x['sequence_tokens'] for x in exposures),
  'positive_tokens_exposed':sum(x['positive_tokens'] for x in exposures),'weighted_mass_exposed':sum(mass.values()),
  'exposure_count_by_pool':dict(count),'weighted_mass_by_pool':dict(mass),'explicit_repeated_real_ids':repeats,
  'at_least_one_existing_process_sequence_each_mixed_optimizer_step':True if synthetic else None,
  'last_partial_accumulation_flushed':True,'steps':[[{'id':x['id'],'pool':x['pool']} for x in b] for b in steps]}
def main():
 OUT.mkdir(parents=True,exist_ok=False);bm=load(BASE/'TRAINING_MANIFEST.json');allbase=[];parents={}
 def find(x):
  parents.setdefault(x,x)
  if parents[x]!=x:parents[x]=find(parents[x])
  return parents[x]
 def join(a,b):
  a,b=find(a),find(b)
  if a!=b:parents[max(a,b)]=min(a,b)
 for _,_,r in rows(BASE,bm['actual_train_files']):
  item={'id':r['id'],'bank':r['bank'],'source_ids':r['source_ids'],'source_group_id':r['source_group_id'],
   'total_tokens':r['total_tokens'],'supervised_tokens':r['supervised_tokens'],'supervision_spans':r['supervision_spans']}
  allbase.append(item);join('r:'+r['id'],'g:'+r['source_group_id'])
  for s in r['source_ids']:join('r:'+r['id'],'s:'+s)
 real=[summary(r,'real_process',find('r:'+r['id'])) for r in allbase if r['bank']!='source_contract_main']
 assert len(real)==205 and len({r['group'] for r in real})==44
 cases={r['id']:r for r in [json.loads(l) for l in (WORK/'controller_cases/run07/CASES.jsonl').read_text(encoding='utf-8').splitlines()]}
 pilot_names={'材料索引','会议排版','网页交互','数据整理'}
 result={'schema':'wrd11-candidate-exposure-not-launcher','seed':SEED,'profiles':{},'training_started':False}
 for name,directory in [('full_native53','curriculum01'),('budget_projection','budget_curriculum01')]:
  root=WORK/directory;m=load(root/'CURRICULUM_MANIFEST11.json');full=[];pilot=[]
  for _,_,r in rows(root,m['synthetic_train_files']):
   item=summary(r,'synthetic',r['source_group_id']);full.append(item)
   cid=r['original_record_metadata']['case_id']
   if cid.startswith('cpu11-') or cases[cid]['point_time_state']['display_name'] in pilot_names:pilot.append(item)
  assert len(full)==627 and len(pilot)==339
  profile={'source_manifest_sha256':sha(root/'CURRICULUM_MANIFEST11.json'),'real_only':make_schedule(real,[]),
   'pilot':make_schedule(real,pilot),'full':make_schedule(real,full),
   'pilot_synthetic_ids':sorted(x['id'] for x in pilot),'full_synthetic_ids':sorted(x['id'] for x in full)}
  assert profile['pilot']['optimizer_steps_candidate']==136 and profile['full']['optimizer_steps_candidate']==209
  assert len(profile['full']['explicit_repeated_real_ids'])==4
  result['profiles'][name]=profile
 save(OUT/'EXPOSURE_SCHEDULES11.json',result)
 save(OUT/'SUMMARY.json',{'schema':result['schema'],'profiles':{p:{k:{a:b for a,b in v.items() if a!='steps'} for k,v in d.items() if k in {'real_only','pilot','full'}} for p,d in result['profiles'].items()},
  'notes':['Pilot339 is a nested parameter cohort, not new independent source groups.','full627 requires four explicit repeated real views to keep a real example in each optimizer step.','Loss mass fractions are bookkeeping, not measured gradient norm or model quality.'],
  'training_started':False,'script_sha256':sha(__file__)})
 print(json.dumps({p:{k:{a:v for a,v in d[k].items() if a in {'optimizer_steps_candidate','sequence_exposures','unique_targets','sequence_tokens_unpadded'}} for k in ['real_only','pilot','full']} for p,d in result['profiles'].items()}))
if __name__=='__main__':main()
