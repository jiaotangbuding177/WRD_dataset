"""Audit actual historical raw request/response pairs without exporting bodies."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261025_wrd_reasoning_recovery_v4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def scope(path):
    s=str(path).replace('\\','/').lower()
    if '/technical/' in s:return 'technical_fixture_exclude'
    if '/formal/' in s or 'eval250' in s or 'evaluation_visible' in s:return 'formal_evaluation_exclude'
    if '/generation/' in s:return 'historical_skill_generation_candidate'
    if '/development/' in s:return 'historical_development_actor_candidate'
    if '/execution/' in s or '/validation' in s:return 'historical_business_actor_or_validation_requires_source_audit'
    return 'role_unknown_requires_source_audit'

def main():
    discovery=load(OUT/'RAW_SOURCE_DISCOVERY.json');by_scope=defaultdict(Counter);by_root=defaultdict(Counter);runs=defaultdict(Counter);pairs=[]
    for row in discovery['unique_file_inventory']:
        p=Path(row['path'])
        if p.name!='response.raw.json':continue
        response=load(p);message=(response.get('choices')or[{}])[0].get('message')or{};reason=message.get('reasoning_content')or''
        request=p.with_name('request.json');sc=scope(p);root=str(p).split('model_requests')[0]
        c=by_scope[sc];c['raw_response_pairs']+=1;c['reasoning_responses']+=bool(reason);c['reasoning_characters']+=len(reason);c['assistant_content_characters']+=len(message.get('content')or'')
        calls=message.get('tool_calls')or[];c['response_tool_call_messages']+=bool(calls);c['reasoning_and_tool_call_same_response']+=bool(reason and calls)
        c['request_file_present']+=request.is_file()
        request_data=load(request) if request.is_file() else {};messages=request_data.get('messages')or[];tools=request_data.get('tools')or[]
        c['request_with_messages']+=bool(messages);c['request_with_tools']+=bool(tools)
        observed_ids=set();missing=0
        for m in messages:
            if m.get('role')=='assistant':
                for call in m.get('tool_calls')or[]:
                    if call.get('id'):observed_ids.add(call['id'])
            elif m.get('role')=='tool':
                if m.get('tool_call_id') not in observed_ids:missing+=1
        c['history_with_unmatched_tool_results']+=bool(missing)
        run=p.parents[2];runs[str(run)].update({'responses':1,'reasoning_responses':bool(reason),'reasoning_characters':len(reason)})
        public={'response_path':str(p),'request_path':str(request) if request.is_file() else None,'response_sha256':sha(p),
                'request_sha256':sha(request) if request.is_file() else None,'scope':sc,'run_path':str(run),'request_ordinal':p.parent.name,
                'reasoning_json_pointer':'/choices/0/message/reasoning_content' if reason else None,
                'reasoning_characters':len(reason),'reasoning_sha256':hashlib.sha256(reason.encode()).hexdigest() if reason else None,
                'response_has_tool_calls':bool(calls),'request_messages':len(messages),'request_tools':len(tools),
                'history_unmatched_tool_result_count':missing,'reasoning_ownership':'observed_original_assistant_response_field',
                'training_admitted':False,'human_gold':False,'body_exported':False}
        pairs.append(public)
    # Group stable aggregate roots without revealing response bodies.
    for item in pairs:
        p=Path(item['response_path']);root=next((str(Path(r['path'])) for r in discovery['roots'] if Path(r['path']) in p.parents),None)
        if root:
            by_root[root].update({'raw_response_pairs':1,'reasoning_responses':bool(item['reasoning_characters']),'reasoning_characters':item['reasoning_characters']})
    report={'schema_version':'wrd-original-reasoning-pair-audit-v4','counts_by_scope':{k:dict(v) for k,v in by_scope.items()},
        'counts_by_root':{k:dict(v) for k,v in by_root.items()},'runs':[{ 'path':k,**dict(v)} for k,v in runs.items()],
        'pairs':pairs,'raw_response_unique_files':len(pairs),'reasoning_response_unique_files':sum(bool(x['reasoning_characters']) for x in pairs),
        'scope_classification_is_path_evidence_not_final_semantic_approval':True,'formal_evaluation_not_training':True,
        'source_discovery_sha256':sha(OUT/'RAW_SOURCE_DISCOVERY.json'),'script_sha256':sha(Path(__file__)),
        'training_started':False,'new_model_calls':0,'bodies_copied':False}
    save(OUT/'RAW_REASONING_PAIRS_AUDIT.json',report)
    print(json.dumps({'counts_by_scope':report['counts_by_scope'],'raw_response_unique_files':len(pairs),'reasoning_responses':report['reasoning_response_unique_files']},ensure_ascii=False))

if __name__=='__main__':main()
