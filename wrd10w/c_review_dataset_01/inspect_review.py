from pathlib import Path
import gzip, hashlib, importlib.util, json

ROOT=Path('D:/skillloop')
BASE=ROOT/'output/20261027_wrd_main_v10'
OUT=BASE/'c_review_dataset_01'
EP=BASE/'runtime_preflight/episodes/C_review_report_01'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
spec=importlib.util.spec_from_file_location('extractor',ROOT/'research/data_prep/wrd_main_v10/extract_native_main.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
inventory=[]; paragraphs=[]; originals=[]
for f in sorted((EP/'api_audit').iterdir()):
    if not f.is_dir(): continue
    msg,meta,req,resp=m.recover(f)
    request=json.loads(req.read_text(encoding='utf-8-sig'))
    r=msg.get('reasoning_content',''); cursor=0
    inventory.append({'call_id':f.name,'request':str(req),'request_sha256':sha(req),'response':str(resp),'response_sha256':sha(resp),'reasoning_chars':len(r),'reasoning_sha256':hashlib.sha256(r.encode()).hexdigest(),'content_chars':len(msg.get('content','')),'tool_calls':[c['function']['name'] for c in msg.get('tool_calls',[])],'messages':len(request['messages'])})
    originals.append({'call_id':f.name,'message':msg,'native_messages':request['messages'],'native_tools':request['tools'],'request':str(req),'request_sha256':sha(req),'response':str(resp),'response_sha256':sha(resp)})
    paragraphs.append(f'\n===== {f.name} R chars {len(r)} =====\n')
    for part in r.splitlines(keepends=True):
        paragraphs.append(f'[{cursor}:{cursor+len(part)}] {part}')
        cursor+=len(part)
    paragraphs.append('\nCONTENT:\n'+msg.get('content','')+'\nTOOLS:\n'+json.dumps(msg.get('tool_calls',[]),ensure_ascii=False,indent=2)+'\n')
(OUT/'review_reading.txt').write_text(''.join(paragraphs),encoding='utf-8')
save(OUT/'REVIEW_CALL_INVENTORY.json',inventory)
with gzip.open(OUT/'C_review.original_responses.jsonl.gz','wt',encoding='utf-8',newline='\n') as h:
    for row in originals: h.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps(inventory,ensure_ascii=False,indent=2))
