"""Read-only mask metadata recount for a training-plan review, not compilation."""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json
ROOT=Path('D:/skillloop');DATA=ROOT/'output/20261027_wrd_main_v10';OUT=ROOT/'output/20261031_wrd_next51_planning/train_review'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def main():
 m=load(DATA/'TRAINING_MANIFEST.json');assert sha(DATA/'TRAINING_MANIFEST.json')=='01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42'
 rs=[]
 for ref in m['actual_train_files']:
  p=DATA/ref['path'];assert p.stat().st_size==ref['bytes']and sha(p)==ref['sha256']
  with gzip.open(p,'rt',encoding='utf-8-sig')as f:rs.extend(json.loads(l)for l in f if l.strip())
 process=[r for r in rs if r['bank']!='source_contract_main'];contract=[r for r in rs if r['bank']=='source_contract_main']
 paired=[r for r in process if 'R'in r['supervised_tokens_by_component']and any(c in r['supervised_tokens_by_component']for c in ['A','D'])]
 native=[r for r in paired if r['bank']in {'native_wrd_main','native_C_review_partial_02','native_CV_B_training_01','native_HTML_B_training_01'}]
 excerpt=[r for r in paired if r['bank']=='historical_test_oracle_repair_02'];new=[r for r in paired if r not in native+excerpt]
 ronly=[r for r in process if set(r['supervised_tokens_by_component'])=={'R'}]
 parent={}
 def find(x):
  parent.setdefault(x,x)
  if parent[x]!=x:parent[x]=find(parent[x])
  return parent[x]
 def join(x,y):parent[find(x)]=find(y)
 for r in rs:
  node='r:'+r['id'];join(node,'g:'+r['source_group_id'])
  for s in r['source_ids']:join(node,'s:'+s)
 assert len({find('r:'+r['id'])for r in process})==44
 def summary(rows):return{'views':len(rows),'source_ids':len({s for r in rows for s in r['source_ids']}),'global_connected_components':len({find('r:'+r['id'])for r in rows}),'input_tokens':sum(r['total_tokens']for r in rows),'supervised_tokens':sum(r['supervised_tokens']for r in rows),'R_tokens':sum(r['supervised_tokens_by_component'].get('R',0)for r in rows)}
 result={'status':'READ_ONLY_PLANNING_METADATA_RECOUNT_NOT_NEW_DATA_OR_EXPERIMENT','main_manifest_sha256':sha(DATA/'TRAINING_MANIFEST.json'),
  'process_combinations':{'/'.join(k):v for k,v in Counter(tuple(sorted(r['supervised_tokens_by_component']))for r in process).items()},
  'current_step_R_with_A_or_D':summary(paired),'native_original_R_with_A_or_D':summary(native),'recorded_cumulative_excerpt_with_A':summary(excerpt),'new_author_R_with_A_or_D':summary(new),'R_only':summary(ronly),
  'process':summary(process),'contract':summary(contract),'all':summary(rs),
  'original_R_positive_tokens':54745,'R_only_original_share':summary(ronly)['R_tokens']/54745,
  'one_contract_plus_three_process_passes_unpadded_sequence_tokens':sum(r['total_tokens']for r in contract)+3*sum(r['total_tokens']for r in process),
  'source_aggregation':'Source ID counts above are not independent DSU counts; frozen main process has54 IDs/44 global connected components.',
  'no_original_text_copied':True,'model_weights_loaded':False,'training_started':False,'new_business_calls':0,
  'source_pins':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size}for p in [ROOT/'research/plans/20261031_wrd_curation09/TRAINING_STRATEGY_09.md',ROOT/'research/plans/20261031_wrd_curation09/ACTUAL_DATA_REPORT.md',ROOT/'output/20261031_wrd_curation09/eval_input_arrays09/BUILD_QA.json']],
  'script_sha256':sha(__file__)}
 (OUT/'PLANNING_FACTS.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode());print(json.dumps(result))
if __name__=='__main__':main()
