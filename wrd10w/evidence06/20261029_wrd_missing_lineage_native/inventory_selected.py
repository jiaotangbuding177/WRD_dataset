"""Read metadata only for two parent-assigned historical makers. Never train."""
from pathlib import Path
import gzip, hashlib, json

ROOT = Path(__file__).resolve().parents[2]
V9 = ROOT / 'output/20261026_wrd_dataset_v9'
DEST = Path(__file__).resolve().parent
WANTED = {'ep_df95d2f3cf09628aa3ac', 'ep_5de7f066feaed4c4b254'}
FILES = {
    'episodes': 'recovery/episodes.metadata.jsonl.gz',
    'targets': 'outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz',
    'resources': 'outcomes/recomputed_scope_overlay/resource_scope.jsonl.gz',
    'produced_versions': 'outcomes/recomputed_scope_overlay/produced_versions.jsonl.gz',
}

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def main():
    out={'schema':'wrd-missing-lineage-selected-metadata-v1',
         'status':'METADATA_INVENTORY_NOT_TRAINING_ADMISSION',
         'episodes':{e:{} for e in sorted(WANTED)},'metadata_sources':[],
         'new_native_or_training':False}
    for label,rel in FILES.items():
        path=V9/rel
        out['metadata_sources'].append({'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size})
        for ep in WANTED:out['episodes'][ep][label]=[]
        with gzip.open(path,'rt',encoding='utf-8-sig') as f:
            for i,line in enumerate(f,1):
                r=json.loads(line)
                if r.get('episode_id') in WANTED:
                    out['episodes'][r['episode_id']][label].append({'metadata_line':i,'row':r})
    path=DEST/'SELECTED_METADATA_01.json'
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'path':str(path),'sha256':sha(path),
      'counts':{e:{k:len(v) for k,v in row.items()} for e,row in out['episodes'].items()}}))

if __name__=='__main__':main()
