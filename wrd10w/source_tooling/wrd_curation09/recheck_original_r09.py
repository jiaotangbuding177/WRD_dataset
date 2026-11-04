"""Recheck all historical R partitions against actual preserved originals.

This is identity/coverage verification, not a fresh semantic approval.
"""
from pathlib import Path
from collections import Counter, defaultdict
import gzip, hashlib, json
ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/'output/20261027_wrd_main_v10'
OUT=ROOT/'output/20261031_wrd_curation09/reasoning'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hs(s):return hashlib.sha256(s.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def main():
 OUT.mkdir(parents=True,exist_ok=True);assert not (OUT/'ORIGINAL26_IDENTITY_PARTITION_RECHECK09.json').exists()
 base=DATA/'historical_v6_reasoning_review_01/combined26_peer_refined_01'
 part=load(base/'CHARACTER_PARTITION.json');review=load(base/'REVIEW.json')
 source=Path(review['source_file']);assert sha(source)==review['source_file_sha256']
 originals={r['id']:r for r in rows(source)}
 compiled={r['original_record_metadata']['canonical_original_response_owner']:r for p in (DATA/'compiled/historical_semantic_R_26_01').glob('*.train.*.jsonl.gz')for r in rows(p)}
 assert len(compiled)==26
 groups=defaultdict(list);counts=Counter();receipt=[]
 for b in part['blocks']:groups[b['pair_id']].append(b)
 for inv in review['inventory']:
  owner=inv['pair_id'];raw=originals[owner];text=raw['original_response']
  for key in raw['original_reasoning_pointer'].strip('/').split('/'):text=text[int(key)]if isinstance(text,list)else text[key]
  row=compiled[owner]
  assert len(text)==inv['original_R_characters']and hs(text)==inv['original_R_utf8_sha256']
  assert row['messages'][row['targets'][0]['message_index']]['reasoning_content']==text
  blocks=sorted(groups[owner],key=lambda x:x['start']);previous=0;approved=[]
  for b in blocks:
   a,z=b['start'],b['end'];assert a==previous and a<z<=len(text);previous=z
   assert b['characters']==z-a and hs(text[a:z])==b['text_sha256'];counts[b['classification']]+=z-a
   if b['classification']=='POSITIVE_LOCAL_PLAN_INFERENCE_OR_FACT':approved.append((a,z,b['text_sha256']))
  assert previous==len(text)
  selected=[(r['start'],r['end'],r['text_sha256'])for r in row['original_record_metadata']['approved_field_ranges']]
  assert selected==approved
  receipt.append({'owner_id':owner,'original_R_characters':len(text),'original_R_sha256':hs(text),'positive_characters':sum(z-a for a,z,_ in approved),
   'positive_R_tokens':row['supervised_tokens_by_component']['R'],'whole_original_body_preserved':True,'complete_partition_no_gap':True,'approved_ranges_match_current_compilation':True,
   'semantic_review_inherited_not_newly_repeated':True,'current_total_tokens':row['total_tokens']})
 assert dict(counts)==part['counts']and sum(counts.values())==396231
 result={'status':'PASS_ORIGINAL_IDENTITY_PARTITION_AND_CURRENT_RANGE_RECHECK_ONLY','original_R_owners':26,'original_R_characters':sum(counts.values()),
  'partition_character_counts':dict(counts),'actual_positive_R_tokens':sum(x['positive_R_tokens']for x in receipt),'all_original_bodies_preserved':True,
  'all26_fit32k':all(x['current_total_tokens']<=32768 for x in receipt),'new_positive_R_tokens':0,'new_semantic_full_text_review_claimed':False,
  'remaining_unknown_not_approved_chars':counts['STILL_UNKNOWN_NOT_APPROVED'],'unknown_is_not_discarded_or_proven_wrong':True,
  'source':pin(source),'partition':pin(base/'CHARACTER_PARTITION.json'),'prior_semantic_review':pin(base/'REVIEW.json'),'rows':receipt,
  'training_started':False,'model_weights_loaded':False,'script_sha256':sha(__file__)}
 (OUT/'ORIGINAL26_IDENTITY_PARTITION_RECHECK09.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:result[k]for k in ['status','original_R_owners','original_R_characters','actual_positive_R_tokens','remaining_unknown_not_approved_chars','new_positive_R_tokens']}))
if __name__=='__main__':main()
