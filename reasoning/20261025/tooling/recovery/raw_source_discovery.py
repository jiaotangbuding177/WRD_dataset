"""Read-only discovery of historical WRD raw outputs; no source bodies exported."""
from __future__ import annotations
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import time

ROOT=Path('D:/skillloop')
OUT=ROOT/'output/20261025_wrd_reasoning_recovery_v4'
PRUNE={'node_modules','.git','.venv','venv','__pycache__','inputs','staged_sources','source_materials','attachments','assets','credentials','.cache'}
REASON_KEYS={'reasoning_content','reasoningContent','thinking_content','analysis_content','reasoning','thinking','analysis'}
REASON_TYPES={'thinking','reasoning','redacted_thinking','analysis'}
BAD_NAMES={'auth-profiles.json','credentials.json','common_model.json','model.json','.env','accounts.json','auth.json'}
NAME=re.compile(r'(?:request|response|session_events|events|trace|trajectory|transcript|capture|model_calls|journal|proposal|llm)',re.I)
TAG=re.compile(r'<(?:think|thinking|reasoning)>([\s\S]*?)</(?:think|thinking|reasoning)>',re.I)

def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def walk(d):
    for b,ds,fs in os.walk(d,followlinks=False):
        ds[:]=[x for x in ds if x.lower() not in PRUNE and not (Path(b)/x).is_symlink()]
        for f in fs:
            p=Path(b)/f
            if p.is_symlink() or f.lower() in BAD_NAMES or f.lower().startswith(('.env','model_')):continue
            if p.suffix.lower() in {'.json','.jsonl','.ndjson','.raw','.log','.txt'} and NAME.search(f):yield p

def inspect(v, c, hits, where='$', role=None, is_response=False, depth=0):
    if depth>35:return
    if isinstance(v,dict):
        role=v.get('role',role)
        typ=v.get('type')
        if isinstance(typ,str) and typ in REASON_TYPES:
            payload=v.get('thinking') or v.get('reasoning') or v.get('text') or v.get('data')
            if isinstance(payload,str) and len(payload.strip())>3:
                c['explicit_reasoning_blocks']+=1;hits.append({'path':where,'kind':'typed_'+str(typ),'characters':len(payload),'payload_sha256':sha_bytes(payload.encode())})
        if isinstance(v.get('channel'),str) and v.get('channel') in {'analysis','thinking','reasoning'} and role=='assistant':
            payload=v.get('text') or v.get('content')
            if isinstance(payload,str) and payload.strip():
                c['assistant_analysis_channel_payloads']+=1;hits.append({'path':where,'kind':'assistant_channel','characters':len(payload),'payload_sha256':sha_bytes(payload.encode())})
        for k,x in v.items():
            path=where+'.'+k
            if k in REASON_KEYS and isinstance(x,str) and x.strip():
                if x.strip().lower() in {'off','on','none','null','false','true','high','medium','low','minimal','enabled','disabled'}:
                    c['reasoning_configuration_enums']+=1
                elif role=='assistant' or (is_response and k in {'reasoning_content','reasoningContent','thinking_content','analysis_content'}):
                    c['explicit_reasoning_fields']+=1;hits.append({'path':path,'kind':'field_'+k,'characters':len(x),'payload_sha256':sha_bytes(x.encode())})
                else:c['unconfirmed_reasoning_named_strings']+=1
            if role=='assistant' and isinstance(x,str) and k in {'text','content'}:
                c['assistant_visible_text_fields']+=1;c['assistant_visible_text_characters']+=len(x)
                for m in TAG.finditer(x):
                    z=m.group(1);c['assistant_think_tag_blocks']+=1;hits.append({'path':path,'kind':'assistant_think_tag','characters':len(z),'payload_sha256':sha_bytes(z.encode())})
            inspect(x,c,hits,path,role,is_response,depth+1)
    elif isinstance(v,list):
        for i,x in enumerate(v):inspect(x,c,hits,where+'['+str(i)+']',role,is_response,depth+1)

def main():
    start=time.monotonic();OUT.mkdir(parents=True,exist_ok=True)
    inventory=json.loads((ROOT/'research/data_prep/wrd_training/resources/history_inventory.json').read_text(encoding='utf-8-sig'))
    known={str(Path(x['path'])).lower() for x in inventory['roots']}
    roots=[]
    for home in [ROOT/'output',Path('E:/skillloop_runs')]:
        for d in home.iterdir():
            if not d.is_dir():continue
            name=d.name.lower()
            if not re.search(r'(?:workflow|wrd|trace2skill|^w\d+$|^20261021_v\d+|native_openclaw|native_case)',name):continue
            if name.startswith('20261025_wrd_') or name in {'workflow_library'}:continue
            if re.search(r'(?:eval|ablation|formal|250|controls|_t\d{4})',name):scope='evaluation_or_controls_excluded_from_training'
            else:scope='historical_wrd_requires_per_episode_scope_audit'
            roots.append({'path':str(d),'scope':scope,'in_prior_28_root_inventory':str(d).lower() in known})
    records=[];seen={};tot=Counter();rootstats=[];hitsall=[];shapes=Counter()
    for n,r in enumerate(roots):
        s=Counter();bybase=Counter()
        for p in walk(Path(r['path'])):
            try:size=p.stat().st_size
            except OSError:s['stat_error']+=1;continue
            bybase[p.name]+=1;s['selected_files']+=1;s['selected_bytes']+=size
            # During discovery, formal/control roots are inventory-only.
            if r['scope']=='evaluation_or_controls_excluded_from_training':continue
            if size>200_000_000:s['oversize_deferred']+=1;continue
            try:raw=p.read_bytes()
            except OSError:s['read_error']+=1;continue
            h=sha_bytes(raw)
            if h in seen:s['byte_duplicate_files']+=1;continue
            seen[h]=str(p);c=Counter();hits=[];errors=0;objs=0
            is_response=bool(re.search(r'(response|proposal|capture|trace|events|trajectory|transcript|llm)',p.name,re.I)) and 'request' not in p.name.lower()
            try:text=raw.decode('utf-8-sig')
            except UnicodeDecodeError:s['non_utf8']+=1;continue
            if p.suffix.lower() in {'.jsonl','.ndjson'}:
                iterator=((i,line) for i,line in enumerate(text.splitlines(),1) if line.strip())
            else:iterator=[(None,text)]
            for line_no,line in iterator:
                try:v=json.loads(line)
                except json.JSONDecodeError:errors+=1;continue
                objs+=1
                if isinstance(v,dict):
                    shapes.update([str(p.name)+':'+','.join(sorted(v.keys())[:15])])
                local=[];inspect(v,c,local,is_response=is_response)
                for x in local:x['line_1based']=line_no
                hits+=local
            s['unique_files_inspected']+=1;s['json_objects']+=objs;s['json_parse_failures']+=errors;s.update(c)
            if hits:
                entry={'path':str(p),'sha256':h,'bytes':size,'counts':dict(c),'hits':hits,'scope':r['scope']}
                hitsall.append(entry)
            if objs:records.append({'path':str(p),'sha256':h,'bytes':size,'objects':objs,'parse_failures':errors,'counts':dict(c),'scope':r['scope']})
        rootstats.append({**r,'counts':dict(s),'selected_filenames':dict(bybase)})
        tot.update(s)
        dump(OUT/'RAW_SOURCE_DISCOVERY.progress.json',{'roots_done':n+1,'counts':dict(tot),'reasoning_payload_files':hitsall,'roots':rootstats,'unique_file_inventory':records})
        if n%12==0:print(json.dumps({'roots_done':n+1,'unique_files':tot['unique_files_inspected'],'reasoning_hit_files':len(hitsall)}),flush=True)
    # Only metadata and payload hashes, never original text, are written.
    dump(OUT/'RAW_SOURCE_DISCOVERY.json',{'schema_version':'wrd-raw-source-discovery-v4','scope':'historical raw discovery, not train admission',
        'roots':rootstats,'counts':dict(tot),'reasoning_payload_files':hitsall,'unique_file_inventory':records,
        'json_top_level_shapes_top60':shapes.most_common(60),'known_inventory_roots':len(known),
        'source_bodies_copied':False,'training_started':False,'new_model_calls':0,
        'script_sha256':sha_bytes(Path(__file__).read_bytes()),'elapsed_seconds':round(time.monotonic()-start,3)})
    print(json.dumps({'status':'DISCOVERY_COMPLETE','roots':len(roots),'counts':dict(tot),'reasoning_hit_files':len(hitsall),'seconds':round(time.monotonic()-start,3)}),flush=True)

if __name__=='__main__':main()
