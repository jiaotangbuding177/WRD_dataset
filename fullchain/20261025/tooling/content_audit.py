"""Offline content/schema census; never emits enterprise text or reasoning bodies."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import gzip, hashlib, json, re, time
from pathlib import Path

CORE={'ls','read','edit','write','apply_patch','exec','process'}
REASON_KEYS={'thinking','reasoning','reasoning_content','reasoning_details','analysis','redacted_thinking','thinking_content','analysis_content'}
TAG=re.compile(r'<(?:think|thinking|reasoning)>[\s\S]*?</(?:think|thinking|reasoning)>',re.I)

def rows(p):
    op=gzip.open if p.suffix=='.gz' else open
    with op(p,'rt',encoding='utf-8-sig') as f:
        for line in f:
            if line.strip(): yield json.loads(line)

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def visible(m):
    c=m.get('content','')
    if isinstance(c,str):return c
    return '\n'.join(str(b.get('text','')) for b in c if isinstance(b,dict) and b.get('type')=='text') if isinstance(c,list) else ''

def calls(m):
    c=m.get('content',[])
    return [b for b in c if isinstance(b,dict) and b.get('type')=='toolCall'] if isinstance(c,list) else []

def primitive_schema(x):
    """Only metadata; nonempty explicit reasoning payload count, no value output."""
    found=Counter()
    def walk(v,path=()):
        if isinstance(v,dict):
            typ=v.get('type')
            if typ in {'thinking','reasoning','redacted_thinking'}:
                payload=v.get('thinking') or v.get('reasoning') or v.get('text') or v.get('data')
                found['typed_reasoning_blocks']+=1
                found['typed_reasoning_blocks_with_nonempty_string_payload']+=isinstance(payload,str) and bool(payload.strip())
            for k,a in v.items():
                if k in REASON_KEYS:
                    found['field_present:'+k]+=1
                    if isinstance(a,str) and a.strip():
                        found['nonempty_string_field:'+k]+=1
                        if a.lower() in {'off','on','none','minimal','low','medium','high','disabled','enabled','false','true'}:
                            found['known_configuration_enum:'+k+':'+a.lower()]+=1
                        else:
                            found['nonconfiguration_string_field:'+k]+=1
                            found['nonconfiguration_string_characters:'+k]+=len(a)
                    elif isinstance(a,(list,dict)) and a:found['nonempty_container_field:'+k]+=1
                walk(a,path+(str(k),))
        elif isinstance(v,list):
            for a in v:walk(a,path+('[]',))
        elif isinstance(v,str):found['embedded_reasoning_tag_segments']+=len(TAG.findall(v))
    walk(x)
    return found

def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();start=time.monotonic()
    canonical=a.bundle/'canonical/native_episodes.jsonl.gz';index=a.bundle/'archive/file_index.jsonl'
    source_sha={'canonical':sha(canonical),'archive_index':sha(index)}
    stage=defaultdict(Counter);tools=defaultdict(Counter);keys=Counter();types=Counter();thinking=Counter();rolecounts=Counter();targets=Counter()
    for r in rows(canonical):
        s=r.get('kind','unknown');c=stage[s];c['episodes']+=1;c['native_verified_episodes']+=r.get('native_verified') is True
        c['nonempty_system_episodes']+=isinstance(r.get('system'),str) and bool(r['system'].strip());c['context_fully_recoverable_episodes']+=r.get('context_fully_recoverable') is True
        seen=set();schemas=set(r.get('complete_tool_schema_names',[]));assistant=[i for i,m in enumerate(r['messages']) if m.get('role')=='assistant'];last=assistant[-1] if assistant else -1
        for i,m in enumerate(r['messages']):
            rolecounts[m.get('role','unknown')]+=1
            if m.get('role')!='assistant':continue
            keys.update(m.keys());cs=calls(m);txt=visible(m);names={str(x.get('name')) for x in cs};seen.update(names)
            c['assistant_targets']+=1;c['tool_action_targets']+=bool(cs);c['visible_text_targets']+=bool(txt.strip());c['mixed_text_and_calls_targets']+=bool(txt.strip() and cs)
            c['text_only_targets']+=bool(txt.strip() and not cs);c['empty_targets']+=bool(not txt.strip() and not cs);c['visible_text_characters']+=len(txt)
            c['target_calls_core7_compatible']+=bool(cs and names<=CORE);c['prefix_and_target_calls_core7_compatible']+=bool(cs and seen<=CORE)
            c['observed_prefix_tool_names_covered_by_recorded_schema_names']+=seen<=schemas
            c['actual_last_nonempty_text_only']+=bool(i==last and txt.strip() and not cs)
            c['actual_last_nonempty_tool_target']+=bool(i==last and cs)
            for z in cs:tools[s][str(z.get('name'))]+=1
            content=m.get('content')
            if isinstance(content,list):types.update(str(z.get('type','unknown')) if isinstance(z,dict) else type(z).__name__ for z in content)
            else:types['content_'+type(content).__name__]+=1
            thinking.update(primitive_schema(m))
            if re.search(r'(?:因为|因此|所以|判断|依据|原因|需要|应当|选择|修订|修正|保留|淘汰|because|therefore|reason|revise|retain)',txt,re.I):c['visible_text_reason_decision_keyword_heuristic']+=1
    # Inspect only native-event / model response / request archives. Deduplicate exact bytes;
    # requests can contain copied history: counts are fields, NOT unique teacher thoughts.
    rawcounts=defaultdict(Counter);raw_evidence=[];seenobjects=set();kinds=Counter()
    for r in rows(index):
        logical=r['logical_path'].replace('\\','/');base=logical.rsplit('/',1)[-1].lower()
        if base not in {'session_events.jsonl','request.json','response.json','native_session.json','native_session.jsonl'}:continue
        if not logical.startswith('episodes/'):continue
        category=base;kinds[category]+=1;h=r['sha256']
        if (category,h) in seenobjects:continue
        seenobjects.add((category,h));rawcounts[category]['unique_objects']+=1
        obj=a.bundle/r['object']
        if not obj.is_file():obj=a.bundle/'archive'/r['object']
        if not obj.is_file():rawcounts[category]['missing_object']+=1;continue
        raw=obj.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=h:raise ValueError('CAS hash mismatch')
        try:txt=raw.decode('utf-8-sig')
        except UnicodeDecodeError:rawcounts[category]['not_utf8']+=1;continue
        vals=[]
        if base.endswith('.jsonl'):
            for line in txt.splitlines():
                if not line.strip():continue
                try:vals.append(json.loads(line))
                except json.JSONDecodeError:rawcounts[category]['malformed_lines']+=1
        else:
            try:vals=[json.loads(txt)]
            except json.JSONDecodeError:rawcounts[category]['malformed_json_objects']+=1
        count=Counter()
        for v in vals:count.update(primitive_schema(v))
        if any(v for k,v in count.items() if k.startswith('nonempty_') or k in {'typed_reasoning_blocks_with_nonempty_string_payload','embedded_reasoning_tag_segments'}):
            rawcounts[category]['objects_with_any_reasoning_named_payload_or_tags']+=1
            raw_evidence.append({'logical_path':logical,'stored_sha256':h,'object':r['object'],'counts':dict(count),'classification':'metadata_only_not_validated_model_reasoning'})
        rawcounts[category].update(count);rawcounts[category]['parsed_values']+=len(vals)
    summary=json.loads((a.bundle/'summary.json').read_text(encoding='utf-8-sig'))
    out={'schema_version':'wrd-fullchain-content-audit-v1','scope':'offline_count_only_no_text_or_reasoning_bodies_emitted',
         'by_stage':{k:dict(v) for k,v in stage.items()},'tool_calls_by_stage':{k:dict(v) for k,v in tools.items()},
         'assistant_message_keys':dict(keys),'assistant_content_types':dict(types),'canonical_reasoning_metadata':dict(thinking),'all_message_role_counts':dict(rolecounts),
         'raw_archive_inspection':{'logical_alias_counts':dict(kinds),'by_filename':{k:dict(v) for k,v in rawcounts.items()},'objects_with_reasoning_named_payload_metadata':raw_evidence,
         'limitations':'Reasoning/analysis field names may occur in schemas, user-supplied material, copied prompts or generated files; metadata count is not validated teacher reasoning.'},
         'historical_export_reasoning_blocks_removed':summary.get('training',{}).get('counts',{}).get('reasoning_blocks_removed'),
         'canonical_reasoning_exported_flag_is_not_original_absence_proof':True,'source_sha256':source_sha,'script_sha256':sha(Path(__file__)),
         'training_started':False,'new_model_calls':0,'elapsed_seconds':round(time.monotonic()-start,3)}
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'CONTENT_AUDIT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'stages':{k:{i:v[i] for i in ('episodes','assistant_targets','visible_text_targets','mixed_text_and_calls_targets','empty_targets')} for k,v in stage.items()},'canonical_reasoning':dict(thinking),'raw_counts':{k:dict(v) for k,v in rawcounts.items()},'seconds':out['elapsed_seconds']},ensure_ascii=False))
if __name__=='__main__':main()
