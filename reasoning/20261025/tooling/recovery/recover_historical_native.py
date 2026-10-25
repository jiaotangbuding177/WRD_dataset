"""Recover previously unrepresented historical native sessions, without execution."""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import time

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261025_wrd_reasoning_recovery_v4';BUNDLE=ROOT/'output/20261025_wrd_training_dataset/bundle'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,default=None):
    try:return json.loads(p.read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return default
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def line(f,x):f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
def original_id(p):
    try:
        with p.open('r',encoding='utf-8-sig') as f:
            for _ in range(4):
                s=f.readline(200000)
                if not s:break
                try:r=json.loads(s)
                except ValueError:continue
                if r.get('type')=='session':return r.get('id')
    except OSError:return None
    return None
def ref(p):return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} if p.is_file() else None
def tools_names(v):
    items=v.get('tools',[]) if isinstance(v,dict) else v if isinstance(v,list) else []
    return sorted({x.get('function',x).get('name') for x in items if isinstance(x,dict) and isinstance(x.get('function',x).get('name'),str)})
def classify(ep,request):
    task=str((request or{}).get('task_id',''));path=str(ep).replace('\\','/').lower();name=ep.name.lower()
    if any(s in path for s in ['/controls/','/technical/','/technical_probe/']):return 'legacy','technical_exclude'
    if re.search(r'\bT\d{4}\b',task,re.I) or re.match(r'^T\d{4}',name,re.I) or '/formal/' in path:return 'actor','formal_task_identity_exclude'
    if any(s in task.lower() for s in ['prepare','select_case']):return 'prepare','historical_prepare_candidate'
    if 'review' in task.lower():return 'review','historical_review_candidate'
    if any(s in task.lower() for s in ['screen','classif']):return 'screen','historical_screen_candidate'
    if re.match(r'^(?:gen|make|resource|revise|repair)[_-]',task,re.I) or re.match(r'^(?:gen|make)[_-]',name):return 'make','historical_make_candidate_requires_source_audit'
    return 'legacy','historical_role_unknown_requires_source_audit'

def main():
    start=time.monotonic();discovery=load(OUT/'RAW_SOURCE_DISCOVERY.json');current=set()
    with gzip.open(BUNDLE/'canonical/native_episodes.jsonl.gz','rt',encoding='utf-8') as f:
        for s in f:current.add(json.loads(s)['episode_id'])
    known_sha=set();known_native_ids=set();archive_refs=0
    with (BUNDLE/'archive/file_index.jsonl').open(encoding='utf-8') as f:
        for s in f:
            r=json.loads(s);parts=r['logical_path'].replace('\\','/').split('/')
            if len(parts)<3 or parts[0]!='episodes' or parts[1] not in current or parts[-1]!='session_events.jsonl':continue
            known_sha.add(r['source_sha256']);known_sha.add(r['sha256']);archive_refs+=1
            p=BUNDLE/r['object']
            if not p.is_file():p=BUNDLE/'archive'/r['object']
            sid=original_id(p)
            if sid:known_native_ids.add(sid)
    candidates=[];inventory=[];stats=Counter();by_role=Counter();sidgroups=defaultdict(list)
    for row in discovery['unique_file_inventory']:
        p=Path(row['path'])
        if p.name!='session_events.jsonl':continue
        stats['selected_historical_unique_event_files']+=1
        sid=original_id(p);samehash=row['sha256'] in known_sha;samesid=sid in known_native_ids if sid else False
        inv={'path':str(p),'sha256':row['sha256'],'bytes':row['bytes'],'native_session_id':sid,'already_current_by_source_sha':samehash,'already_current_by_native_id':samesid}
        if samehash or samesid:
            stats['already_current_native_session_or_bytes']+=1;inventory.append(inv);continue
        assert sha(p)==row['sha256']
        messages=[];eventlines=[];eventids=[];header=None;parseerrors=0;types=Counter();reasonblocks=0
        with p.open(encoding='utf-8-sig') as f:
            for i,s in enumerate(f,1):
                if not s.strip():continue
                try:r=json.loads(s)
                except ValueError:parseerrors+=1;continue
                types[str(r.get('type'))]+=1
                if r.get('type')=='session':header=r
                m=r.get('message')
                if r.get('type')=='message' and isinstance(m,dict) and m.get('role') in {'system','user','assistant','tool','toolResult'}:
                    messages.append(m);eventlines.append(i);eventids.append(r.get('id'))
                    if isinstance(m.get('content'),list):reasonblocks+=sum(isinstance(x,dict) and x.get('type') in {'thinking','reasoning','redacted_thinking'} for x in m['content'])
        transport=p.parent;ep=transport.parent;requestp=ep/'request.json'
        if not requestp.is_file():requestp=transport/'request.json'
        request=load(requestp,{})
        systemp=transport/'evidence/system-prompt.txt';toolsp=transport/'evidence/tools.json';resultp=ep/'result.json';receiptp=ep/'episode_receipt.json';responsep=ep/'response.json';execp=ep/'execution.json'
        system=systemp.read_text(encoding='utf-8-sig') if systemp.is_file() else ''
        tools=load(toolsp,[]);kind,scope=classify(ep,request);names=tools_names(tools)
        status=(load(resultp,{}) or{}).get('status') or (load(receiptp,{}) or{}).get('status') or 'historical_unknown'
        key=sid or row['sha256'];snapshot={'inv':inv,'native_session_id':sid,'messages':messages,'event_ids':eventids,'event_lines':eventlines,
            'header':header,'parseerrors':parseerrors,'types':dict(types),'request':request,'system':system,'tools':tools,'kind':kind,'scope':scope,
            'names':names,'status':status,'reasoning_blocks':reasonblocks,'source_request':ref(requestp),'source_system':ref(systemp),'source_tools':ref(toolsp),
            'source_receipt':ref(receiptp),'source_response':ref(responsep),'source_execution':ref(execp),'source_result':ref(resultp)}
        sidgroups[key].append(snapshot);inv.update(kind=kind,role_scope=scope,messages=len(messages),assistant_targets=sum(x.get('role')=='assistant' for x in messages),raw_reasoning_blocks=reasonblocks)
        inventory.append(inv)
    out=OUT/'controlled/historical_native_sessions.jsonl.gz'
    if out.exists():raise ValueError('new output required')
    exported=[]
    with gzip.open(out,'wt',encoding='utf-8',newline='\n',compresslevel=3) as f:
        for sid,variants in sidgroups.items():
            # Exact session id can have prefix snapshots; keep longest only when event-id prefix is proved.
            variants.sort(key=lambda x:len(x['event_ids']),reverse=True);longest=variants[0]
            for v in variants[1:]:
                if v['event_ids']==longest['event_ids'][:len(v['event_ids'])]:stats['prefix_snapshot_aliases_not_new_session']+=1
                else:
                    stats['nonprefix_same_session_variants']+=1;candidates.append(v)
            candidates.append(longest)
        for v in candidates:
            inv=v['inv'];identifier='hist_native_'+hashlib.sha256((str(v['native_session_id'])+'|'+inv['sha256']).encode()).hexdigest()[:20]
            row={'schema_version':'wrd-historical-native-session-v4','episode_id':identifier,'native_session_id':v['native_session_id'],
                'job_id':v['request'].get('task_id'),'kind':v['kind'],'role_scope':v['scope'],'status':v['status'],
                'historical_condition':'historical_native_openclaw_original_events_environment_and_source_scope_separate',
                'system':v['system'],'messages':v['messages'],'source_event_lines':v['event_lines'],'source_event_ids':v['event_ids'],
                'native_session_header':v['header'],'original_request':v['request'],'tools':v['tools'],
                'tools_definition_path':(v['source_tools']or{}).get('path'),'complete_tool_schema_names':v['names'],
                'source_events':{'path':inv['path'],'sha256':inv['sha256'],'bytes':inv['bytes']},
                'source_request':v['source_request'],'source_system':v['source_system'],'source_tools':v['source_tools'],
                'source_receipt':v['source_receipt'],'source_response':v['source_response'],'source_execution':v['source_execution'],'source_result':v['source_result'],
                'native_verified':False,'native_environment_status':'original_native_events_preserved_environment_not_certified_by_this_recovery',
                'context_fully_recoverable':bool(v['system'] and v['names'] and not v['parseerrors']),
                'message_parse_issues':{'malformed_event_lines':v['parseerrors']},'reasoning_exported':True,'reasoning_fields_never_removed':True,
                'messages_sanitized_before_derivation':False,'requires_private_storage':True,'source_ids':[],
                'split':'quarantine','source_split':'historical_scope_pending','benchmark_exposed':v['scope']=='formal_task_identity_exclude',
                'human_gold':False,'semantic_approved':False,'training_admitted':False,'publication_approved':False}
            line(f,row);stats['new_unique_native_sessions_exported']+=1;stats['new_assistant_targets']+=sum(m.get('role')=='assistant' for m in v['messages']);stats['raw_reasoning_blocks']+=v['reasoning_blocks'];by_role[v['scope']]+=1
            stats['sessions_with_recorded_system_and_tools']+=bool(v['system'] and v['names']);exported.append({'episode_id':identifier,'native_session_id':v['native_session_id'],'kind':v['kind'],'role_scope':v['scope'],'source_sha256':inv['sha256'],'messages':len(v['messages'])})
    for v in candidates:assert sha(Path(v['inv']['path']))==v['inv']['sha256']
    report={'schema_version':'wrd-historical-native-recovery-report-v4','counts':dict(stats),'new_sessions_by_role':dict(by_role),
        'current_canonical_sessions':len(current),'current_archived_event_refs':archive_refs,'current_distinct_native_session_ids':len(known_native_ids),
        'source_inventory':inventory,'exported_sessions':exported,'controlled_output':{'path':str(out.relative_to(OUT)),'sha256':sha(out),'bytes':out.stat().st_size},
        'native_verified_not_automatically_true':True,'semantic_admission_completed':False,'original_sources_unchanged':True,
        'script_sha256':sha(Path(__file__)),'source_discovery_sha256':sha(OUT/'RAW_SOURCE_DISCOVERY.json'),'training_started':False,'new_model_calls':0,'elapsed_seconds':round(time.monotonic()-start,3)}
    save(OUT/'HISTORICAL_NATIVE_RECOVERY_REPORT.json',report)
    print(json.dumps({k:report[k] for k in ['counts','new_sessions_by_role','current_distinct_native_session_ids','elapsed_seconds']},ensure_ascii=False))

if __name__=='__main__':main()
