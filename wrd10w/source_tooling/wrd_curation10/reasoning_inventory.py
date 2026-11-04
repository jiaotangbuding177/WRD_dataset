"""Recover exact historical R/action/request payloads for causality review.

Offline originals only; does not grant credit, alter main data or execute tools.
"""
from pathlib import Path
from collections import Counter,defaultdict
import gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/'output/20261027_wrd_main_v10'
OUT=ROOT/'output/20261031_wrd_curation10/reasoning'
OLD=DATA/'historical_v6_reasoning_review_01/combined26_peer_refined_01'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig')as f:
  for l in f:
   if l.strip():yield json.loads(l)
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def main():
 assert not (OUT/'INVENTORY.json').exists()
 review=load(OLD/'REVIEW.json');part=load(OLD/'CHARACTER_PARTITION.json')
 source=Path(review['source_file']);assert sha(source.read_bytes())==review['source_file_sha256']
 wanted={r['pair_id']for r in review['inventory']};originals={r['id']:r for r in rows(source)if r['id']in wanted};assert len(originals)==26
 blocks=defaultdict(list)
 for b in part['blocks']:blocks[b['pair_id']].append(b)
 stats=[];OUT.mkdir(parents=True,exist_ok=True)
 for inv in review['inventory']:
  oid=inv['pair_id'];original=originals[oid];reason=original['original_response']
  for key in original['original_reasoning_pointer'].strip('/').split('/'):reason=reason[int(key)]if isinstance(reason,list)else reason[key]
  assert sha(reason.encode())==inv['original_R_utf8_sha256']and len(reason)==inv['original_R_characters']
  folder=OUT/'owners'/oid;folder.mkdir(parents=True)
  dump(folder/'ORIGINAL_RECORD.json',original);(folder/'ORIGINAL_R.txt').write_bytes(reason.encode())
  dump(folder/'CHARACTER_PARTITION.json',blocks[oid]);dump(folder/'PRIOR_REVIEW_INVENTORY.json',inv)
  unknown=[b for b in blocks[oid]if b['classification']=='STILL_UNKNOWN_NOT_APPROVED']
  unknowntext='\n\n'.join(f'BLOCK {b["start"]}:{b["end"]}\n'+reason[b['start']:b['end']]for b in unknown)
  (folder/'UNKNOWN_REVIEW.txt').write_bytes(unknowntext.encode())
  stats.append({'owner_id':oid,'source_id':inv['source_id'],'decision':inv['decision'],'R_characters':len(reason),
    'unknown_characters':sum(b['end']-b['start']for b in unknown),'unknown_blocks':len(unknown),
    'source_request':inv['source_request'],'source_response':inv['source_sse'],
    'original_record':pin(folder/'ORIGINAL_RECORD.json'),'original_R':pin(folder/'ORIGINAL_R.txt'),
    'fields':list(original),'original_response_fields':list(original['original_response'])if isinstance(original['original_response'],dict)else None,
    'classification_counts':dict(Counter({k:sum(b['end']-b['start']for b in blocks[oid]if b['classification']==k)for k in {b['classification']for b in blocks[oid]}}))})
 dump(OUT/'INVENTORY.json',{'status':'EXACT_ORIGINAL_RECOVERY_NOT_SEMANTIC_ADMISSION','source':pin(source),'review':pin(OLD/'REVIEW.json'),
   'partition':pin(OLD/'CHARACTER_PARTITION.json'),'rows':stats,'new_supervision':0,'training_started':False})
 print(json.dumps([{'owner':r['owner_id'],'source':r['source_id'],'decision':r['decision'],'R':r['R_characters'],'unknown':r['unknown_characters'],'blocks':r['unknown_blocks']}for r in stats],ensure_ascii=False))
if __name__=='__main__':main()
