"""Read-only audit of actual results and serialised positive targets.

Parses Python/JSON as data only; never executes archived tools or code.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re


def rows(path):
    opener=gzip.open if Path(path).suffix=='.gz' else open
    with opener(path,'rt',encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():yield json.loads(line)


def text(message):
    content=message.get('content','')
    if isinstance(content,str):return content
    if isinstance(content,list):return '\n'.join(str(x.get('text','')) for x in content if isinstance(x,dict) and x.get('type')=='text')
    return ''


def target_checks(row):
    errors=[];warnings=[]
    for m in row.get('completion',[]):
        for call in m.get('tool_calls',[]):
            fn=call.get('function',{})
            try:a=json.loads(fn.get('arguments','{}')) if isinstance(fn.get('arguments'),str) else fn.get('arguments',{})
            except (TypeError,ValueError):errors.append('invalid_target_arguments_json');continue
            if not isinstance(a,dict):errors.append('target_arguments_not_object');continue
            if fn.get('name')=='write':
                path=str(a.get('path',a.get('file_path','')))
                content=a.get('content')
                if not isinstance(content,str):continue
                fixture=('/making_samples/' in path and re.search(r'bad|invalid|malformed|error|坏|错误',Path(path).name,re.I))
                if path.endswith('.py') and not fixture:
                    try:ast.parse(content)
                    except (SyntaxError,ValueError,TypeError):errors.append('written_python_target_syntax_invalid')
                    if re.search(r'raise\s+(?:SystemExit|NotImplementedError)\s*\(\s*[\'\"](?:internal|TODO|not implemented|未实现)',content,re.I):
                        errors.append('written_program_contains_explicit_unimplemented_exit')
                if path.endswith('.json') and not fixture:
                    try:json.loads(content)
                    except (ValueError,TypeError):errors.append('written_json_target_invalid')
                if path.endswith('/SKILL.md'):
                    if not content.lstrip().startswith('---'):
                        errors.append('skill_write_missing_frontmatter')
                    else:
                        parts=content.lstrip().split('---',2)
                        front=parts[1] if len(parts)>2 else ''
                        if not re.search(r'(?m)^\s*name\s*:\s*\S',front):errors.append('skill_write_missing_name')
                        if not re.search(r'(?m)^\s*description\s*:\s*\S',front):errors.append('skill_write_missing_description')
            body=json.dumps(a,ensure_ascii=False)
            user='\n'.join(text(x) for x in row.get('prompt',[]) if x.get('role')=='user')
            if '硬限调用' in user and re.search(r'连续失败\s*\d+\s*次|核验只做一次|不追加第二轮|完成后即落稿',body):
                warnings.append('possible_instruction_conflict_hard_cap_requires_review')
    return sorted(set(errors)),sorted(set(warnings))


def audit(bundle, inputs, output):
    requested=defaultdict(dict); result={};counts=Counter()
    for path in inputs:
        for r in rows(path):
            if r['id'] in result:raise ValueError('duplicate input target id')
            errors,warnings=target_checks(r)
            result[r['id']]={'id':r['id'],'kind':r['kind'],'target_kind':r.get('target_kind'),
                             'errors':errors,'warnings':warnings,'actual_target_result_checked':False}
            requested[r['episode_id']][r['target_message_index']]=r['id']
    for ep in rows(bundle/'canonical/native_episodes.jsonl.gz'):
        wanted=requested.get(ep.get('episode_id'),{})
        if not wanted:continue
        messages=ep.get('messages',[])
        for index,identifier in wanted.items():
            row=result[identifier]
            if not 0<=index<len(messages):row['errors'].append('canonical_target_index_missing');continue
            message=messages[index]
            calls=[x for x in message.get('content',[]) if isinstance(x,dict) and x.get('type')=='toolCall'] if isinstance(message.get('content'),list) else []
            if not calls:
                row['actual_target_result_checked']=True
                continue
            linked={}
            for later in messages[index+1:]:
                if later.get('role')=='assistant':break
                if later.get('role') in ('tool','toolResult'):linked[later.get('toolCallId',later.get('tool_call_id'))]=later
            for call in calls:
                observed=linked.get(call.get('id'))
                if observed is None:row['errors'].append('actual_target_result_missing');continue
                value=text(observed)
                name=call.get('name')
                if name in ('read','ls','write','edit','apply_patch'):
                    patterns=[(r'offset\s+\d+\s+is\s+beyond\s+end','actual_read_offset_beyond_end'),
                              (r'\[Current model does not support images','actual_media_omitted_not_received'),
                              (r'(?im)^Error:\s*(?:ENOENT|EISDIR|EACCES|Could not|Cannot|File not found)','actual_file_tool_text_error'),
                              (r'(?i)"status"\s*:\s*"error"','actual_file_tool_json_error')]
                    for pat,reason in patterns:
                        if re.search(pat,value,re.I):row['errors'].append(reason)
                if observed.get('isError') is True:row['errors'].append('actual_tool_is_error_true')
            row['actual_target_result_checked']=True
    for row in result.values():
        if not row['actual_target_result_checked']:row['errors'].append('canonical_episode_not_resolved')
        row['errors']=sorted(set(row['errors']));row['warnings']=sorted(set(row['warnings']))
        row['structural_eligible']=not row['errors']
        counts['rows']+=1;counts['structural_eligible']+=int(row['structural_eligible'])
        for e in row['errors']:counts['error:'+e]+=1
        for e in row['warnings']:counts['warning:'+e]+=1
    output.mkdir(parents=True,exist_ok=True)
    with (output/'structure_audit.jsonl').open('w',encoding='utf-8',newline='\n') as f:
        for row in result.values():f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    report={'schema_version':'wrd-preflight-structure-audit-v1','counts':dict(counts),
            'scope':'Actual tool result delivery plus positive write Python/JSON/frontmatter parsing; no source code execution or blanket semantic approval.',
            'training_started':False,'original_sources_modified':False}
    (output/'structure_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--input',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();audit(a.bundle,a.input,a.output)
