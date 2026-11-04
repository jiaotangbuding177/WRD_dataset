"""Display small-episode original targets for bounded content review, no execution."""
import argparse, gzip,json
from process_batch02_review import BASE, read, REVIEWS
from process_batch02_inspect import txt
p=argparse.ArgumentParser();p.add_argument('start',type=int);p.add_argument('end',type=int);a=p.parse_args()
pending={r['owner_id']for r in read('OWNER1321_DISPOSITION09.jsonl.gz')if r['processing_disposition']=='HOLD_NEEDS_SEMANTIC_REVIEW'}
rows=read('OWNER1321_EXACT_CONTENT.audit.jsonl.gz');contexts={r['episode_id']:r for r in read('ORIGINAL_CONTEXTS_343.audit.jsonl.gz')}
groups={}
for row in rows:
    if row['owner_id']in pending and row['episode_id']not in REVIEWS:groups.setdefault(row['episode_id'],[]).append(row)
small=sorted([(ep,r)for ep,r in groups.items()if len(r)<=3])
for pos,(ep,records) in enumerate(small[a.start:a.end],a.start):
    c=contexts[ep]
    print('\nGROUP',pos,ep,c.get('route_id'),'OWNERS',len(records),'TASKEND',txt(c['messages'][0])[-650:])
    for r in sorted(records,key=lambda q:q['source_message_index']):
        print('OWNER',r['owner_id'],'IDX',r['source_message_index'])
        for b in r['target_message_original'].get('content',[]):
            print('TARGET',json.dumps(b,ensure_ascii=False)[:1800])
        for f in r['immediate_original_tool_feedback']:
            s=txt(f['message'])
            try:
                j=json.loads(s);s=str(j.get('error') or j.get('text') or j)
            except:pass
            if '\n---\n'in s and '<<<EXTERNAL_UNTRUSTED_CONTENT'in s:s=s.split('\n---\n',1)[-1]
            s=s.split('<<<END_EXTERNAL_UNTRUSTED_CONTENT')[0]
            print('OBS',f['message_index'],s[:550])
