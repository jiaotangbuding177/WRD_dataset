"""Offline exact provenance recovery for checkpoint07's196 unresolved targets.

Parses original JSON/Python AST; never executes captured code or an agent loop.
All source/code/response bodies remain evidence until independent admission.
"""
from pathlib import Path, PurePosixPath
from collections import Counter, defaultdict
import argparse
import ast
import gzip
import hashlib
import json
import re

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261030_wrd_gap08/lineage'
OLD=ROOT/'output/20261029_wrd_batch24';V9=ROOT/'output/20261026_wrd_dataset_v9'
CAS=ROOT/'output/20261025_wrd_training_dataset/bundle/archive'
GAPS=ROOT/'research/plans/20261030_wrd_gap_completion/reviews/gaps196_review.json'
SCOPE=ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz'

def hb(b):return hashlib.sha256(b).hexdigest()
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def digest(p):return hb(Path(p).read_bytes())
def pin(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)}
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(s)for s in gzip.open(p,'rt',encoding='utf-8-sig')if s.strip()]
def save(name,v):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return pin(p)
def gz(name,rs):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('wb')as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)as f:
            for r in rs:f.write((js(r)+'\n').encode())
    return pin(p)
def preserve(p):
    p=Path(p);b=p.read_bytes();s=hb(b);q=OUT/'objects'/s;q.parent.mkdir(parents=True,exist_ok=True)
    if not q.exists():q.write_bytes(b)
    assert digest(q)==s
    return {'original':pin(p),'preserved':{'path':'objects/'+s,'bytes':len(b),'sha256':s}}
def messages(p):
    result=[]
    for i,line in enumerate(Path(p).read_text(encoding='utf-8-sig').splitlines(),1):
        try:e=json.loads(line)
        except ValueError:continue
        if e.get('type')=='message' and isinstance(e.get('message'),dict):result.append({'event_line':i,'event':e,'message':e['message']})
    return result
def content(m):
    c=m.get('content',[])
    return c if isinstance(c,str)else ''.join(x.get('text','')for x in c if isinstance(x,dict))
def calls(m):
    c=m.get('content',[])
    return [x for x in c if isinstance(x,dict)and x.get('type')=='toolCall']if isinstance(c,list)else[]
def args(c):
    a=c.get('arguments',{})
    try:return json.loads(a)if isinstance(a,str)else a
    except ValueError:return {}
def ack_for(ms,i,c):
    return next(((j,z)for j,z in enumerate(ms[i+1:],i+1)if z['message'].get('toolCallId')==c['id']),None)
def good_ack(ack):
    if not ack:return False
    m=ack[1]['message'];d=m.get('details',{})
    return m.get('isError')is False and d.get('exitCode',0)==0 and d.get('status','completed')not in {'running','error','failed'}
def walk(v,path='$'):
    if isinstance(v,dict):
        if isinstance(v.get('id'),str):yield path,v
        for k,x in v.items():yield from walk(x,path+'.'+k)
    elif isinstance(v,list):
        for i,x in enumerate(v):yield from walk(x,path+'['+str(i)+']')
def static_cards(code):
    try:tree=ast.parse(code)
    except SyntaxError:return []
    found=[];seen=set()
    for n in ast.walk(tree):
        if not isinstance(n,(ast.Dict,ast.List)):continue
        try:value=ast.literal_eval(n)
        except (ValueError,TypeError,SyntaxError,MemoryError,RecursionError):continue
        for pointer,card in walk(value):
            if not isinstance(card.get('steps'),list)or not isinstance(card.get('reuse_reason'),(str,list)):continue
            key=hb(canonical(card))
            if key not in seen:seen.add(key);found.append(({'line':getattr(n,'lineno',None),'value_pointer':pointer},card))
    return found
def restricted_value(node,env):
    """Literal substitution only, without evaluating functions or captured code."""
    if isinstance(node,ast.Constant):return node.value
    if isinstance(node,ast.Name)and node.id in env:return env[node.id]
    if isinstance(node,ast.List):return [restricted_value(x,env)for x in node.elts]
    if isinstance(node,ast.Tuple):return tuple(restricted_value(x,env)for x in node.elts)
    if isinstance(node,ast.Dict):
        result={}
        for k,v in zip(node.keys,node.values):
            if k is None:result.update(restricted_value(v,env))
            else:result[restricted_value(k,env)]=restricted_value(v,env)
        return result
    if isinstance(node,ast.IfExp):return restricted_value(node.body if restricted_value(node.test,env)else node.orelse,env)
    raise ValueError('nonliteral AST expression')
def constructor_cards(code):
    try:tree=ast.parse(code)
    except SyntaxError:return []
    templates={}
    for n in tree.body:
        if not isinstance(n,ast.FunctionDef)or not n.body:continue
        first=n.body[0]
        if not isinstance(first,ast.Expr)or not isinstance(first.value,ast.Call):continue
        call=first.value
        if not isinstance(call.func,ast.Attribute)or call.func.attr!='append'or len(call.args)!=1 or not isinstance(call.args[0],ast.Dict):continue
        templates[n.name]=(n,call.args[0])
    found=[]
    for n in tree.body:
        if not isinstance(n,ast.Expr)or not isinstance(n.value,ast.Call)or not isinstance(n.value.func,ast.Name)or n.value.func.id not in templates:continue
        fn,template=templates[n.value.func.id];names=[x.arg for x in fn.args.args]
        try:
            env={k:ast.literal_eval(v)for k,v in zip(names[len(names)-len(fn.args.defaults):],fn.args.defaults)}
            env.update({k:ast.literal_eval(v)for k,v in zip(names,n.value.args)})
            env.update({k.arg:ast.literal_eval(k.value)for k in n.value.keywords})
            card=restricted_value(template,env)
        except (ValueError,TypeError,KeyError):continue
        if isinstance(card.get('id'),str)and isinstance(card.get('steps'),list)and isinstance(card.get('reuse_reason'),(str,list)):
            found.append(({'constructor_name':fn.name,'constructor_definition_line':fn.lineno,'literal_call_line':n.lineno,
                'only_literal_parameter_substitution_no_function_executed':True},card))
    return found
def python_heredocs(command):
    found=[]
    # Only parse literal here-document text; never evaluate the shell or Python.
    for m in re.finditer(r"(?:python3?|/[^\s]+/python3?)\b[^\n]*<<\s*['\"]?([A-Za-z_][A-Za-z_0-9]*)['\"]?\s*\n",command):
        end=re.search(r'(?m)^'+re.escape(m.group(1))+r'\s*$',command[m.end():])
        if end:found.append(command[m.end():m.end()+end.start()])
    return found
def literal_shell_json_writes(command):
    result=[]
    for match in re.finditer(r"\bcat\s*>\s*([^\s]+)\s*<<\s*['\"]?([A-Za-z_][A-Za-z_0-9]*)['\"]?\s*\n",command):
        end=re.search(r'(?m)^'+re.escape(match.group(2))+r'\s*$',command[match.end():])
        if not end:continue
        body=command[match.end():match.end()+end.start()]
        try:obj=json.loads(body)
        except ValueError:continue
        result.append((match.group(1),body,obj))
    return result
def output_literals(code):
    try:tree=ast.parse(code)
    except SyntaxError:return []
    result=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='open'and n.args:
            try:path=ast.literal_eval(n.args[0]);mode=ast.literal_eval(n.args[1])if len(n.args)>1 else next((ast.literal_eval(k.value)for k in n.keywords if k.arg=='mode'),'r')
            except (ValueError,TypeError):continue
            if isinstance(path,str)and any(x in mode for x in 'wa')and path.endswith('.json'):result.append(path)
    return sorted(set(result))
def native_to_physical(base,native):
    p=PurePosixPath(native)
    if native.startswith('/workspace/'):return Path(base)/'workspace'/str(p.relative_to('/workspace'))
    if not p.is_absolute():return Path(base)/'workspace'/str(p)
    return None

def common():
    gap=load(GAPS);eps={x['episode_id']:x for x in rows(V9/'recovery/episodes.metadata.jsonl.gz')}
    scope={x['source_id']:x for x in rows(SCOPE)}
    labels=rows(V9/'outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz')
    labels_at={(x['episode_id'],x['source_message_index']):x for x in labels}
    return gap,eps,scope,labels_at

def catalog():
    gap,eps,scope,labels_at=common();wanted={e['route_id']for e in gap['episode_groups']}
    catalog=[];scanned=[];unproven=[]
    # Metadata-bounded 135 screen/resolve native records (~32.6MB), not a GB scan.
    for eid,e in sorted(eps.items()):
        if e['stage']!='screen':continue
        p=Path(e['source_native']['path'])
        if not p.is_file()or digest(p)!=e['source_native']['sha256']:
            scanned.append({'episode_id':eid,'native':e['source_native'],'status':'MISSING_OR_CHANGED'});continue
        ms=messages(p);base=Path(e['source_original_path']).parent.parent;script_writes={};matches=0
        for i,z in enumerate(ms):
            for c in calls(z['message']):
                a=args(c);ack=ack_for(ms,i,c)
                if c.get('name')=='write'and isinstance(a.get('content'),str):
                    if str(a.get('path','')).endswith('.py')and good_ack(ack):
                        script_writes[a['path']]={'index':i,'call':c,'code':a['content'],'ack':ack}
                    try:obj=json.loads(a['content'])
                    except ValueError:continue
                    candidates=[({'json_pointer':ptr},v)for ptr,v in walk(obj)if v.get('id')in wanted and isinstance(v.get('steps'),list)and isinstance(v.get('reuse_reason'),(str,list))]
                    if not good_ack(ack):continue
                    for where,card in candidates:
                        proof={'method':'ORIGINAL_NATIVE_JSON_WRITE_AND_SUCCESS_ACK','episode_id':eid,'source_original_path':e['source_original_path'],
                            'native':pin(p),'write_message_index':i,'write_event_line':z['event_line'],'tool_call_id':c['id'],
                            'write_path':a.get('path'),'whole_write_sha256':hb(a['content'].encode()),'ack_message_index':ack[0],
                            'ack_event_line':ack[1]['event_line'],'ack_message_sha256':hb(canonical(ack[1]['message'])),'location':where,
                            'actual_write_scope':labels_at.get((eid,i))}
                        catalog.append({'proof':proof,'card':card});matches+=1
                if c.get('name')!='exec' or not isinstance(a.get('command'),str)or not good_ack(ack):continue
                command=a['command']
                for native_path,body,obj in literal_shell_json_writes(command):
                    op=native_to_physical(base,native_path)
                    if not op or not op.is_file():continue
                    try:observed=load(op)
                    except (ValueError,UnicodeError):continue
                    if observed!=obj:continue
                    for pointer,card in walk(obj):
                        if card.get('id')not in wanted or not isinstance(card.get('steps'),list)or not isinstance(card.get('reuse_reason'),(str,list)):continue
                        proof={'method':'ORIGINAL_EXEC_LITERAL_CAT_JSON_WRITE_SUCCESS_ACK_AND_EXACT_ACTUAL_OUTPUT',
                            'episode_id':eid,'source_original_path':e['source_original_path'],'native':pin(p),'write_message_index':i,
                            'write_event_line':z['event_line'],'tool_call_id':c['id'],'command_sha256':hb(command.encode()),
                            'whole_write_sha256':hb(body.encode()),'write_path':native_path,'actual_output':pin(op),
                            'whole_actual_output_JSON_exact_equal':True,'ack_message_index':ack[0],
                            'ack_event_line':ack[1]['event_line'],'ack_message_sha256':hb(canonical(ack[1]['message'])),
                            'location':{'json_pointer':pointer},'actual_write_scope':labels_at.get((eid,i)),
                            'no_captured_shell_or_agent_executed_by_this_recovery':True}
                        catalog.append({'proof':proof,'card':card});matches+=1;preserve(op)
                code_sources=[{'code':s,'origin':'INLINE_PYTHON_HEREDOC'}for s in python_heredocs(command)]
                for path,sw in script_writes.items():
                    # Exact recorded script path token in an actual Python invocation.
                    if re.search(r'(?:python3?|/[^\s]+/python3?)\s+'+re.escape(path)+r'(?:\s|$)',command):
                        code_sources.append({'code':sw['code'],'origin':'PRIOR_NATIVE_WRITTEN_PYTHON_SCRIPT_EXECUTED','script_write_index':sw['index'],
                            'script_write_call_id':sw['call']['id'],'script_native_path':path,'script_write_sha256':hb(sw['code'].encode())})
                for cs in code_sources:
                    cards=[(where,v)for where,v in static_cards(cs['code'])+constructor_cards(cs['code'])if v.get('id')in wanted]
                    if not cards:continue
                    outputs=[]
                    for np in output_literals(cs['code']):
                        q=native_to_physical(base,np)
                        if q and q.is_file():
                            try:output=load(q)
                            except (ValueError,UnicodeError):continue
                            outputs.append((np,q,output))
                    for where,card in cards:
                        pins=[]
                        for np,q,output in outputs:
                            locs=[ptr for ptr,v in walk(output)if v==card]
                            if locs:pins.append({'native_output_path':np,'output':pin(q),'actual_output_JSON_exact_card_locations':locs})
                        proof={'method':cs['origin']+'_STATIC_LITERAL_TO_ACTUAL_JSON_OUTPUT','episode_id':eid,
                            'source_original_path':e['source_original_path'],'native':pin(p),'write_message_index':i,'write_event_line':z['event_line'],
                            'tool_call_id':c['id'],'command_sha256':hb(command.encode()),'python_code_sha256':hb(cs['code'].encode()),'location':where,
                            'ack_message_index':ack[0],'ack_event_line':ack[1]['event_line'],'ack_message_sha256':hb(canonical(ack[1]['message'])),
                            'actual_write_scope':labels_at.get((eid,i)),'exact_output_bindings':pins,
                            'static_ast_only_no_old_code_executed':True,**{k:v for k,v in cs.items()if k not in {'code','origin'}}}
                        if pins:catalog.append({'proof':proof,'card':card});matches+=1
                        else:unproven.append({'proof':proof,'card_id':card['id'],'card_canonical_sha256':hb(canonical(card)),
                            'reason':'Actual successful exec exists but exact JSON output carrier not bound; literal alone not promoted.'})
        scanned.append({'episode_id':eid,'native':e['source_native'],'status':'READ_HASH_VERIFIED','messages':len(ms),'proven_cards':matches})
        if matches:preserve(p)
    # Retain actual cards and full producer response/ACK as evidence, never gold.
    for x in catalog:
        proof=x['proof'];proof['card_id']=x['card']['id'];proof['card_canonical_sha256']=hb(canonical(x['card']))
    gz('PRODUCER_CARD_CATALOG.jsonl.gz',catalog);save('CATALOG_SCAN.json',{'status':'BOUNDED_ACTUAL_PRODUCER_RECOVERY_NOT_SEMANTIC_ADMISSION',
        'scanned_native_records':scanned,'proven_card_records':len(catalog),'by_route':dict(Counter(x['card']['id']for x in catalog)),
        'unproved_static_literals':unproven,'source_metadata':pin(V9/'recovery/episodes.metadata.jsonl.gz'),'scope_source':pin(SCOPE),
        'script':pin(__file__),'training_started':False,'new_Agent_calls':0})
    # Blind field comparison against exact pending route versions.
    comparisons=[]
    for g in gap['route_SHA_groups']:
        p=Path(g['CAS_paths'][0]);assert digest(p)==g['frozen_route_sha256'];target=load(p);preserve(p)
        for x in catalog:
            if x['card']['id']!=target['id']:continue
            card=x['card'];equal=[k for k,v in card.items()if k in target and target[k]==v]
            different=[k for k,v in card.items()if k in target and target[k]!=v]
            absent=sorted(set(card)-set(target));extras=sorted(set(target)-set(card))
            whole=not different and not absent
            method_equal=all(k in equal for k in ['id','name','category','steps','reuse_reason'])
            comparisons.append({'route_sha256':g['frozen_route_sha256'],'route_id':target['id'],'affected_targets':g['affected_targets'],
                'producer':x['proof'],'equal_fields':equal,'different_fields':different,'absent_original_fields':absent,'extra_input_fields':extras,
                'all_original_card_fields_preserved':whole,'method_fields_preserved':method_equal,
                'exact_field_sha256':{k:hb(canonical(card[k]))for k in equal},'scope_is_not_quality':True})
    gz('ROUTE_VERSION_COMPARISONS.jsonl.gz',comparisons)
    print(js({'proven_producers':len(catalog),'matching_all_original_fields':dict(Counter(x['route_id']for x in comparisons if x['all_original_card_fields_preserved'])),
        'method_only_matches':dict(Counter(x['route_id']for x in comparisons if x['method_fields_preserved']and not x['all_original_card_fields_preserved']))}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['catalog'],required=True);a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if a.phase=='catalog':catalog()
