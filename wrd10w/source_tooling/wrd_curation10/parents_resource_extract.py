"""Extract original meeting generation actions without executing them."""
from pathlib import Path
import gzip,json,hashlib
ROOT=Path('D:/skillloop')
SRC=ROOT/'output/20261031_wrd_curation10/identity/recovered_native/native_recovered10_61c70099-9493-4dd8-aade-5da80bedb3f0'
OUT=ROOT/'output/20261031_wrd_curation10/resource_review10/meeting_gen01'
def sha(b):return hashlib.sha256(b if isinstance(b,bytes) else b.encode()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode())
def text(m):
 c=m.get('content','')
 return c if isinstance(c,str) else '\n'.join(x.get('text','') for x in c if x.get('type')=='text')
def main():
 ctx=json.loads(next(gzip.open(SRC/'CONTEXT.original.audit.jsonl.gz','rt',encoding='utf-8-sig')))
 targets=[json.loads(l) for l in gzip.open(SRC/'NEW_TARGETS.with_actual_feedback.audit.jsonl.gz','rt',encoding='utf-8-sig')]
 byidx={t['source_message_index']:t for t in targets};timeline=[];writes=[]
 for i,m in enumerate(ctx['messages']):
  row={'i':i,'event':ctx['source_event_lines'][i],'role':m['role'],'text_chars':len(text(m)),'text':text(m),'toolCallId':m.get('toolCallId'),'toolName':m.get('toolName'),'isError':m.get('isError')}
  if i in byidx:
   t=byidx[i];row['owner']=t['canonical_owner_id'];row['calls']=[]
   for call in m.get('content',[]):
    if call.get('type')!='toolCall':continue
    args=call['arguments'];row['calls'].append(call)
    if call['name']=='write':
     body=args.get('content','');p=OUT/'original_writes'/f"{i:03d}_{Path(args.get('path','MISSING_PATH.invalid')).name}"
     p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body.encode())
     writes.append({'owner':t['canonical_owner_id'],'message_index':i,'event':ctx['source_event_lines'][i],'call_id':call['id'],'native_path':args.get('path'),'body_sha256':sha(body),'characters':len(body),'extracted_path':str(p)})
   save(OUT/'original_actions'/f"{i:03d}_{t['canonical_owner_id']}.json",t)
  timeline.append(row)
 save(OUT/'TIMELINE.original.audit.json',timeline)
 save(OUT/'ORIGINAL_WRITES.json',writes)
 print(json.dumps({'messages':len(timeline),'targets':len(targets),'writes':writes},ensure_ascii=False))
if __name__=='__main__':main()
