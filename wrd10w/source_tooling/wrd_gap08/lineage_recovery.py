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
import posixpath
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
def is_route_card(card):
    return isinstance(card.get('id'),str)and ((isinstance(card.get('steps'),list)and isinstance(card.get('reuse_reason'),(str,list)))or
        (isinstance(card.get('route_signature'),dict)and isinstance(card.get('value_plan'),dict)))
def static_cards(code):
    try:tree=ast.parse(code)
    except SyntaxError:return []
    found=[];seen=set()
    for n in ast.walk(tree):
        if not isinstance(n,(ast.Dict,ast.List)):continue
        try:value=ast.literal_eval(n)
        except (ValueError,TypeError,SyntaxError,MemoryError,RecursionError):continue
        for pointer,card in walk(value):
            if not is_route_card(card):continue
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
                    candidates=[({'json_pointer':ptr},v)for ptr,v in walk(obj)if v.get('id')in wanted and is_route_card(v)]
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
                        if card.get('id')not in wanted or not is_route_card(card):continue
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
            object_equal=all(isinstance(card.get(k),dict)and k in equal for k in ['route_signature','value_plan'])
            comparisons.append({'route_sha256':g['frozen_route_sha256'],'route_id':target['id'],'affected_targets':g['affected_targets'],
                'producer':x['proof'],'equal_fields':equal,'different_fields':different,'absent_original_fields':absent,'extra_input_fields':extras,
                'all_original_card_fields_preserved':whole,'method_fields_preserved':method_equal,'two_original_core_objects_preserved':object_equal,
                'exact_field_sha256':{k:hb(canonical(card[k]))for k in equal},'scope_is_not_quality':True})
    gz('ROUTE_VERSION_COMPARISONS.jsonl.gz',comparisons)
    print(js({'proven_producers':len(catalog),'matching_all_original_fields':dict(Counter(x['route_id']for x in comparisons if x['all_original_card_fields_preserved'])),
        'method_only_matches':dict(Counter(x['route_id']for x in comparisons if x['method_fields_preserved']and not x['all_original_card_fields_preserved'])),
        'two_core_object_matches':dict(Counter(x['route_id']for x in comparisons if x['two_original_core_objects_preserved']))}))

def scalar_strings(v,path='$'):
    if isinstance(v,str):yield path,v
    elif isinstance(v,dict):
        for k,x in v.items():yield from scalar_strings(x,path+'.'+k)
    elif isinstance(v,list):
        for i,x in enumerate(v):yield from scalar_strings(x,path+'['+str(i)+']')

def effective_scope(proof,scope):
    old=proof.get('actual_write_scope')or{}
    statuses={s:scope.get(s,{}).get('status','MISSING_CURRENT_SCOPE')for s in old.get('source_ids',[])}
    protected=sorted(set(old.get('protected_source_ids',[]))|{s for s,v in statuses.items()if v.startswith('HOLD_')})
    return {'old_scope_status':old.get('source_admission'),'scope_proof_id':old.get('scope_proof_id'),
        'source_statuses':statuses,'protected_ids':protected,
        'proven_protected':old.get('source_admission')=='HOLD_PROTECTED'or bool(protected),
        'proven_clean':old.get('source_admission')=='ADMIT'and bool(statuses)and all(v=='TRAIN'for v in statuses.values())and not old.get('unknown_reasons')}

def original_scalar_receipts(ms,card,target,fields):
    observations=[]
    original_calls={c['id']:c for z in ms for c in calls(z['message'])}
    for index,z in enumerate(ms):
        m=z['message']
        if m.get('role')!='toolResult':continue
        call=original_calls.get(m.get('toolCallId'));a=args(call)if call else{}
        explicit_route=(call and call.get('name')=='read'and a.get('path')in ['/workspace/inputs/route.json','/workspace/inputs/route_card.json'])or(
            call and call.get('name')=='exec'and any(p in a.get('command','')for p in ['/workspace/inputs/route.json','/workspace/inputs/route_card.json']))
        if not explicit_route:continue
        text=content(m);normalized=text.replace('\r\n','\n').replace('\r','')
        proofs=[]
        for field in fields:
            for pointer,value in scalar_strings(card[field],'$.'+field):
                # Identity only; never grants semantic correctness to this text.
                if len(value)<24:continue
                encoded=json.dumps(value,ensure_ascii=False);start=normalized.find(encoded)
                if start>=0:proofs.append({'original_field_path':pointer,'original_scalar_sha256':hb(value.encode()),
                    'JSON_quoted_scalar_sha256':hb(encoded.encode()),'normalized_observation_start':start,
                    'normalized_observation_end':start+len(encoded),'original_chars':len(value)})
        if proofs:observations.append({'observation_message_index':index,'event_line':z['event_line'],
            'tool_call_id':m.get('toolCallId'),'observation_text_sha256':hb(text.encode()),'original_field_scalar_receipts':proofs})
    return observations

def static_resource_writes(command):
    """Recover full literal file contents from commands, without executing them."""
    result=[]
    for match in re.finditer(r"\bcat\s*>\s*([^\s]+)\s*<<\s*['\"]?([A-Za-z_][A-Za-z_0-9]*)['\"]?\s*\n",command):
        end=re.search(r'(?m)^'+re.escape(match.group(2))+r'\s*$',command[match.end():])
        if end:result.append({'path':match.group(1),'content':command[match.end():match.end()+end.start()],
            'method':'ORIGINAL_LITERAL_SHELL_HEREDOC','source_start':match.end(),'source_end':match.end()+end.start()})
    for py in python_heredocs(command):
        try:tree=ast.parse(py)
        except SyntaxError:continue
        env={}
        def literal(n):
            if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in {'Path','PurePosixPath'}and len(n.args)==1:return restricted_value(n.args[0],env)
            return restricted_value(n,env)
        for n in tree.body:
            if isinstance(n,ast.Assign):
                try:value=literal(n.value)
                except (ValueError,TypeError,KeyError):continue
                for t in n.targets:
                    if isinstance(t,ast.Name):env[t.id]=value
        for n in ast.walk(tree):
            if not isinstance(n,ast.Call)or not isinstance(n.func,ast.Attribute)or n.func.attr not in {'write','write_text'}or len(n.args)!=1:continue
            try:value=literal(n.args[0])
            except (ValueError,TypeError,KeyError):continue
            if not isinstance(value,str):continue
            receiver=n.func.value;path=None
            try:
                if n.func.attr=='write_text':path=literal(receiver)
                elif isinstance(receiver,ast.Call)and isinstance(receiver.func,ast.Name)and receiver.func.id=='open'and receiver.args:
                    path=literal(receiver.args[0]);mode=literal(receiver.args[1])if len(receiver.args)>1 else'r'
                    if not any(x in mode for x in 'wa'):continue
            except (ValueError,TypeError,KeyError):continue
            if isinstance(path,str):result.append({'path':path,'content':value,'method':'ORIGINAL_PYTHON_AST_LITERAL_FILE_WRITE',
                'source_python_line':n.lineno,'original_python_source_sha256':hb(py.encode())})
    return result

def recover():
    gap,eps,scope,labels_at=common();scope_targets=load(OLD/'REMAINING_GAPS_FINAL196.json')['targets']
    assert len(scope_targets)==196 and sum(e['targets']for e in gap['episode_groups'])==196
    catalog_rows=rows(OUT/'PRODUCER_CARD_CATALOG.jsonl.gz');comparisons=rows(OUT/'ROUTE_VERSION_COMPARISONS.jsonl.gz')
    bysha=defaultdict(list)
    for c in comparisons:
        if c['all_original_card_fields_preserved']or c['two_original_core_objects_preserved']or c['method_fields_preserved']:bysha[c['route_sha256']].append(c)
    all_targets={}
    for branch in ['crossroutes','remaining76']:
        for t in rows(OLD/branch/'TARGET_DECISIONS_AND_ORIGINAL_BODIES.jsonl.gz'):all_targets[t['id']]=t
    new_overlays=[];all_events=[];route_links=[];resource_versions=[];patches=[];episode_summaries=[];resource_refs=[]
    prior_resources=rows(ROOT/'output/20261029_wrd_v9_missing_evidence_recovery/MAKE_PRIOR_RESOURCES.metadata.jsonl.gz')
    resources_byep=defaultdict(list)
    for rr in prior_resources:resources_byep[rr['episode_id']].append(rr)
    known_routes={x['frozen_route_sha256']:x for x in gap['route_SHA_groups']}
    for ep in gap['episode_groups']:
        eid=ep['episode_id'];native=Path(ep['native_frozen_carrier']['path'])
        assert digest(native)==ep['native_frozen_carrier']['sha256'];ms=messages(native);native_carrier=preserve(native)
        base=Path(ep['native_original_path']).parent.parent;current={};local_resources=[];local_patches=[];input_versions=[]
        # Preserve the actual bounded request and results; credential configs are
        # not opened. The request does not certify missing hidden/system data.
        adjacent=[]
        for name in ['request.json','response.json','result.json','episode_receipt.json']:
            p=base/name
            if p.is_file():adjacent.append(preserve(p))
        for rr in resources_byep[eid]:
            identity=rr.get('file_identity')or{};sha=identity.get('sha256');attempts=[];chosen=None
            if sha:
                candidates=[OLD/b/'objects'/sha for b in ['crossroutes','remaining76','late_producer_closure']]
                if identity.get('source_path'):candidates.append(Path(identity['source_path']))
                if identity.get('object'):candidates.append(CAS/identity['object'])
                for p in candidates:
                    ok=p.is_file()and digest(p)==sha;attempts.append({'path':str(p),'exists':p.is_file(),'matches_frozen_SHA':ok})
                    if ok:chosen=p;break
            record={'episode_id':eid,'node_id':rr['node_id'],'native_path':rr['native_path'],
                'observed_after_assistant_message_index':rr['observed_after_assistant_message_index'],
                'frozen_identity':identity or None,'retrieval_attempts':attempts,'resource':preserve(chosen)if chosen else None,
                'unknown_reasons':rr['unknown_reasons'],'resource_carrier_is_not_original_system_or_quality_proof':True}
            resource_refs.append(record)
            if chosen and rr['native_path'].startswith('/workspace/'):
                try:body=chosen.read_text(encoding='utf-8-sig')
                except UnicodeError:continue
                # A frozen final input snapshot is not silently installed as a
                # step-before version. Require its actual full prior delivery.
                if '/inputs/'in rr['native_path']:input_versions.append({'native_path':rr['native_path'],'content':body,
                    'after_call_index':rr['observed_after_assistant_message_index'],'carrier':pin(chosen)})
        for i,z in enumerate(ms):
            message=z['message'];cc=calls(message)
            if message.get('role')=='toolResult':
                observed=content(message).replace('\r\n','\n')
                for initial in input_versions:
                    if initial['after_call_index']>=i:continue
                    body=initial['content'];needle=body.replace('\r\n','\n')
                    if needle and needle in observed:
                        current[initial['native_path']]={'content':body,'sha256':hb(body.encode()),
                            'version_evidence':{'full_actual_body_delivered_at_message_index':i,
                                'actual_observation_sha256':hb(content(message).encode()),'frozen_input':initial['carrier']}}
            all_events.append({'episode_id':eid,'message_index':i,'event_line':z['event_line'],'message':message,
                'message_sha256':hb(canonical(message)),'full_native':native_carrier,'scope_role':'AUDIT_ONLY_PENDING_OR_PROTECTED',
                'original_thinking_field_chars':sum(len(str(b.get('thinking','')))for b in message.get('content',[])if isinstance(b,dict)),
                'positive_loss':0})
            for call in cc:
                a=args(call);ack=ack_for(ms,i,call);writes=[]
                if call.get('name')=='write'and isinstance(a.get('content'),str):writes=[{'path':a.get('path'),'content':a['content'],'method':'ORIGINAL_NATIVE_WRITE_ARGUMENTS'}]
                if call.get('name')=='exec'and isinstance(a.get('command'),str):writes=static_resource_writes(a['command'])
                for write in writes:
                    path=write['path'];body=write['content']
                    if not isinstance(path,str):continue
                    if not path.startswith('/workspace/'):
                        if not PurePosixPath(path).is_absolute()and '$'not in path:path=posixpath.normpath('/workspace/'+path)
                        else:continue
                    digest_body=hb(body.encode());dest=OUT/'objects'/digest_body
                    if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(body.encode())
                    actual=native_to_physical(base,path);exact_actual=bool(actual and actual.is_file()and digest(actual)==digest_body)
                    parsed=None
                    if path.endswith('.py'):
                        try:ast.parse(body);parsed=True
                        except SyntaxError:parsed=False
                    entry={'episode_id':eid,'source_message_index':i,'event_line':z['event_line'],'tool_call_id':call['id'],
                        'native_path':path,'body_sha256_utf8':digest_body,'body_chars':len(body),'body_bytes':len(body.encode()),
                        'body_object':'objects/'+digest_body,'original_literal':write,
                        'actual_ack':{'message_index':ack[0],'event_line':ack[1]['event_line'],'message':ack[1]['message']}if ack else None,
                        'outer_command_ack_success':good_ack(ack),'same_current_final_file_SHA':exact_actual,
                        'actual_current_file':pin(actual)if exact_actual else None,'python_syntax_only':parsed,
                        'syntax_or_ACK_is_not_correctness':True,'training_admitted':False,'positive_loss':0}
                    local_resources.append(entry);resource_versions.append(entry)
                    if good_ack(ack):current[path]={'content':body,'sha256':digest_body,'version_evidence':entry}
                if call.get('name')=='edit':
                    path=a.get('path');before=current.get(path)if isinstance(path,str)else None
                    changes=a.get('edits')if isinstance(a.get('edits'),list)else [a]if all(k in a for k in ['oldText','newText'])else[]
                    after=before['content']if before else None;checks=[]
                    for edit in changes:
                        old=edit.get('oldText');new=edit.get('newText')
                        count=after.count(old)if after is not None and isinstance(old,str)and old else None
                        checks.append({'oldText_sha256':hb(old.encode())if isinstance(old,str)else None,
                            'newText_sha256':hb(new.encode())if isinstance(new,str)else None,'selector_occurrences':count})
                        if count==1 and isinstance(new,str):after=after.replace(old,new,1)
                        else:after=None
                    entry={'episode_id':eid,'source_message_index':i,'event_line':z['event_line'],'tool_call_id':call['id'],
                        'native_path':path,'original_edit_arguments':a,'old_resource_sha256':before['sha256']if before else None,
                        'exact_selector_checks_in_sequence':checks,'actual_ack':ack[1]if ack else None,
                        'actual_ack_success':good_ack(ack),'new_resource_sha256':None,'local_repair_correctness':'NOT_YET_SEMANTICALLY_REVIEWED',
                        'training_admitted':False,'positive_loss':0}
                    if before and changes and after is not None and good_ack(ack):
                        sa=hb(after.encode());dest=OUT/'objects'/sa
                        if not dest.exists():dest.write_bytes(after.encode())
                        entry.update(new_resource_sha256=sa,new_resource_object='objects/'+sa,
                            exact_patch_applied_offline_not_old_program_execution=True)
                        actual=native_to_physical(base,path)
                        entry['exact_current_final_file_SHA']=bool(actual and actual.is_file()and digest(actual)==sa)
                        current[path]={'content':after,'sha256':sa,'version_evidence':entry}
                    patches.append(entry);local_patches.append(entry)
        # Bind each exact route version and actual downstream original content.
        ep_links=[]
        for sha,g in known_routes.items():
            if eid not in g['episode_ids']:continue
            target=load(g['CAS_paths'][0])
            for comparison in bysha[sha]:
                producer=comparison['producer'];card=next(x['card']for x in catalog_rows if x['proof']['episode_id']==producer['episode_id']and
                    x['proof']['tool_call_id']==producer['tool_call_id']and hb(canonical(x['card']))==producer['card_canonical_sha256'])
                fields=['route_signature','value_plan']if comparison['two_original_core_objects_preserved']else ['steps','reuse_reason']
                receipts=original_scalar_receipts(ms,card,target,fields)
                ps=effective_scope(producer,scope)
                strict=comparison['all_original_card_fields_preserved']or comparison['two_original_core_objects_preserved']
                relation='EXACT_ORIGINAL_CARD_OR_TWO_CORE_OBJECTS'if strict else'METHOD_FIELDS_EXACT_BUT_SOURCE_OR_CONDITION_MERGE_NOT_ORIGINALLY_FROZEN'
                link={'episode_id':eid,'route_id':ep['route_id'],'frozen_route_sha256':sha,'route_input':preserve(Path(g['CAS_paths'][0])),
                    'producer':producer,'comparison':comparison,'producer_effective_scope':ps,'actual_downstream_scalar_receipts':receipts,
                    'earliest_actual_inherited_content_observation':min((z['observation_message_index']for z in receipts),default=None),
                    'relation':relation,'strict_protected_producer_and_receipt':strict and ps['proven_protected']and bool(receipts),
                    'method_dependency_candidate_not_final_origin_equivalence':not strict,'positive_loss':0}
                ep_links.append(link);route_links.append(link)
        protected_boundary=min((l['earliest_actual_inherited_content_observation']for l in ep_links if l['strict_protected_producer_and_receipt']),default=None)
        candidate_boundary=min((l['earliest_actual_inherited_content_observation']for l in ep_links if not l['strict_protected_producer_and_receipt']and l['producer_effective_scope']['proven_protected']and l['actual_downstream_scalar_receipts']),default=None)
        for tid in ep['target_ids']:
            t=next(x for x in scope_targets if x['id']==tid);original=all_targets[tid]
            assert original['source_message_index']==t['message_index']and original['original_message']==ms[t['message_index']]['message']
            idx=t['message_index'];status='HOLD_SPECIFIC_MISSING_ANCESTRY_OR_CAPTURE'
            if protected_boundary is not None and idx>protected_boundary:status='HOLD_PROTECTED_EXACT_ROUTE_ANCESTOR_AND_ACTUAL_CONTENT_RECEIPT'
            elif candidate_boundary is not None and idx>candidate_boundary:status='HOLD_EXACT_METHOD_ANCESTOR_NEEDS_FROZEN_MERGE_OR_IDENTITY_CLOSURE'
            overlay={'id':tid,'episode_id':eid,'route_id':ep['route_id'],'source_message_index':idx,
                'current_decision':status,'positive_loss':0,'training_admitted':False,'scope_is_not_semantic_correctness':True,
                'original_message':original['original_message'],'actual_original_tool_feedback':original['actual_tool_feedback'],
                'original_message_sha256':original['original_message_sha256'],'new_protected_observation_boundary':protected_boundary,
                'method_candidate_observation_boundary':candidate_boundary,'original_unknown_reasons':t['original_unknown_reasons'],
                'route_evidence_links':[i for i,l in enumerate(route_links)if l['episode_id']==eid],
                'original_system_capture_status':ep['original_system_status'],'no_original_native_condition_equivalence_claimed':True}
            new_overlays.append(overlay)
        episode_summaries.append({'episode_id':eid,'route_id':ep['route_id'],'target_count':ep['targets'],
            'native':native_carrier,'actual_messages':len(ms),'adjacent_original_files':adjacent,
            'resource_literal_versions_recovered':len(local_resources),'original_edit_actions':len(local_patches),
            'strict_protected_boundary':protected_boundary,'method_only_candidate_boundary':candidate_boundary,
            'missing_original_system':True,'training_admitted':False})
    assert len(new_overlays)==196 and len({x['id']for x in new_overlays})==196
    gz('TARGET_EVIDENCE_AND_DECISIONS_196.jsonl.gz',new_overlays);gz('ORIGINAL_EVENTS_WITH_R_TOOL_FEEDBACK.jsonl.gz',all_events)
    gz('ROUTE_PRODUCER_TO_ACTUAL_RECEIPT.jsonl.gz',route_links);gz('ACTUAL_RESOURCE_INPUTS.jsonl.gz',resource_refs)
    gz('ORIGINAL_RESOURCE_LITERAL_VERSIONS.jsonl.gz',resource_versions);gz('ORIGINAL_EDIT_VERSION_CHAINS.jsonl.gz',patches)
    save('EPISODE_RECOVERY_46.json',{'episodes':episode_summaries,'status':'ACTUAL_BODY_VERSION_AND_SOURCE_RECOVERY_NO_TRAINING_ADMISSION'})
    # Preserve same-version trial edges and exact frozen package files. Existing
    # silver outcomes are retained as such, never automatically positive labels.
    members={e['episode_id']for e in gap['episode_groups']};meta=V9/'outcomes/recomputed_scope_overlay'
    versions=[v for v in rows(meta/'produced_versions.jsonl.gz')if v['episode_id']in members]
    trees={v['tree_content_sha256']for v in versions};edges=[x for x in rows(meta/'version_trial_review_edges.jsonl.gz')if
        set(x.get('producer_episode_ids',[]))&members or x.get('tree_content_sha256')in trees]
    final_files=[]
    for v in versions:
        for f in v['files']:
            p=Path(f['physical_frozen_CAS_path']);ok=p.is_file()and digest(p)==f['sha256']
            final_files.append({'episode_id':v['episode_id'],'tree_content_sha256':v['tree_content_sha256'],'relative_path':f['relative_path'],
                'frozen_sha256':f['sha256'],'carrier':preserve(p)if ok else None,'final_snapshot_not_assumed_step_before_version':True})
    gz('FROZEN_COMPLETE_PACKAGE_VERSIONS.jsonl.gz',versions);gz('FROZEN_PACKAGE_ACTUAL_FILES.jsonl.gz',final_files)
    gz('SAME_VERSION_TRIAL_AND_REVIEW_EDGES.audit.jsonl.gz',edges)
    summary={'status':'ACTUAL_OFFLINE_RECOVERY_196_MAIN_ADMISSION_PENDING','target_positions':196,'episodes':46,
        'decision_counts':dict(Counter(x['current_decision']for x in new_overlays)),
        'original_messages_and_feedback_preserved':len(all_events),'route_dependency_links':len(route_links),
        'full_literal_resource_versions':len(resource_versions),'unique_literal_resource_SHA':len({x['body_sha256_utf8']for x in resource_versions}),
        'original_edit_actions':len(patches),'patches_with_exact_before_and_after_SHA':sum(bool(x['new_resource_sha256'])for x in patches),
        'input_resource_nodes':len(resource_refs),'input_nodes_exactly_recovered':sum(bool(x['resource'])for x in resource_refs),
        'frozen_package_versions':len(versions),'actual_package_files':len(final_files),'same_version_trial_review_edges':len(edges),
        'new_training_admissions':0,'original_system_gaps_preserved':True,'method_only_matches_not_laundered_to_clean':True,
        'no_old_Agent_loop_or_captured_code_executed':True,'new_Teacher_Actor_calls':0,'training_started':False,
        'scope_provenance':pin(GAPS),'source_scope':pin(SCOPE),'script':pin(__file__)}
    save('RECOVERY_SUMMARY.json',summary)
    print(js({k:v for k,v in summary.items()if k in ['status','decision_counts','original_messages_and_feedback_preserved','full_literal_resource_versions','original_edit_actions','patches_with_exact_before_and_after_SHA','frozen_package_versions','actual_package_files','same_version_trial_review_edges']}))

def verify_and_seal():
    gap=load(GAPS);eps={e['episode_id']:e for e in gap['episode_groups']}
    expected={tid for e in eps.values()for tid in e['target_ids']};targets=rows(OUT/'TARGET_EVIDENCE_AND_DECISIONS_196.jsonl.gz')
    assert len(targets)==196 and {t['id']for t in targets}==expected
    native_cache={eid:messages(e['native_frozen_carrier']['path'])for eid,e in eps.items()}
    links=rows(OUT/'ROUTE_PRODUCER_TO_ACTUAL_RECEIPT.jsonl.gz');protected=0
    for t in targets:
        ms=native_cache[t['episode_id']];assert ms[t['source_message_index']]['message']==t['original_message']
        assert t['positive_loss']==0 and t['training_admitted']is False
        for feedback in t['actual_original_tool_feedback']:assert ms[feedback['message_index']]['message']==feedback['message']
        if t['current_decision']=='HOLD_PROTECTED_EXACT_ROUTE_ANCESTOR_AND_ACTUAL_CONTENT_RECEIPT':
            valid=[links[i]for i in t['route_evidence_links']if links[i]['strict_protected_producer_and_receipt']]
            assert valid and t['source_message_index']>min(x['earliest_actual_inherited_content_observation']for x in valid)
            protected+=1
    scalar_count=0
    for link in links:
        ms=native_cache[link['episode_id']]
        for observed in link['actual_downstream_scalar_receipts']:
            z=ms[observed['observation_message_index']];s=content(z['message']);assert hb(s.encode())==observed['observation_text_sha256']
            c=next(c for m in ms for c in calls(m['message'])if c['id']==observed['tool_call_id']);a=args(c)
            assert (c['name']=='read'and a.get('path')in ['/workspace/inputs/route.json','/workspace/inputs/route_card.json'])or(
                c['name']=='exec'and any(p in a.get('command','')for p in ['/workspace/inputs/route.json','/workspace/inputs/route_card.json']))
            s=s.replace('\r\n','\n').replace('\r','')
            for proof in observed['original_field_scalar_receipts']:
                text=s[proof['normalized_observation_start']:proof['normalized_observation_end']]
                assert hb(text.encode())==proof['JSON_quoted_scalar_sha256']
                assert hb(json.loads(text).encode())==proof['original_scalar_sha256'];scalar_count+=1
    actual_objects=[]
    for p in sorted((OUT/'objects').iterdir()):
        assert p.is_file()and p.name==digest(p)
        actual_objects.append({'path':'objects/'+p.name,'bytes':p.stat().st_size,'sha256':p.name})
    versions=rows(OUT/'ORIGINAL_RESOURCE_LITERAL_VERSIONS.jsonl.gz');checked_versions=0
    for v in versions:
        body=v['original_literal']['content'];assert hb(body.encode())==v['body_sha256_utf8']
        assert (OUT/v['body_object']).read_bytes()==body.encode();checked_versions+=1
        ms=native_cache[v['episode_id']];c=next(c for c in calls(ms[v['source_message_index']]['message'])if c['id']==v['tool_call_id'])
        if v['original_literal']['method']=='ORIGINAL_NATIVE_WRITE_ARGUMENTS':assert args(c)['content']==body and args(c)['path']==v['native_path']
    patches=rows(OUT/'ORIGINAL_EDIT_VERSION_CHAINS.jsonl.gz');patch_count=0
    for patch in patches:
        if not patch['new_resource_sha256']:continue
        before=(OUT/'objects'/patch['old_resource_sha256']).read_text(encoding='utf-8');a=patch['original_edit_arguments']
        edits=a.get('edits')if isinstance(a.get('edits'),list)else[a]
        for edit in edits:assert before.count(edit['oldText'])==1;before=before.replace(edit['oldText'],edit['newText'],1)
        assert hb(before.encode())==patch['new_resource_sha256']
        assert (OUT/patch['new_resource_object']).read_bytes()==before.encode()
        ms=native_cache[patch['episode_id']];c=next(c for c in calls(ms[patch['source_message_index']]['message'])if c['id']==patch['tool_call_id'])
        assert args(c)==a and good_ack(ack_for(ms,patch['source_message_index'],c));patch_count+=1
    refs=rows(OUT/'FROZEN_PACKAGE_ACTUAL_FILES.jsonl.gz');package_checked=0
    for ref in refs:
        if ref['carrier']:
            p=OUT/ref['carrier']['preserved']['path'];assert digest(p)==ref['frozen_sha256'];package_checked+=1
    summary=load(OUT/'RECOVERY_SUMMARY.json');counts=dict(Counter(x['current_decision']for x in targets));assert summary['decision_counts']==counts
    qa={'status':'PASS_ALL196_RAW_TARGETS_ROUTE_RECEIPTS_AND_EXACT_RESOURCE_PATCH_BYTES',
        'targets_checked':196,'episodes_checked':46,'proven_protected_positions':protected,'decision_counts':counts,
        'actual_original_scalar_receipts_checked':scalar_count,'resource_literal_versions_checked':checked_versions,
        'exact_patch_transformations_recomputed_without_executing_programs':patch_count,
        'frozen_package_file_bytes_checked':package_checked,'objects_checked':len(actual_objects),
        'method_only63_not_promoted_to_unique_ancestry_or_clean':True,'no_semantic_correctness_inferred_from_syntax_ACK_or_final_files':True,
        'new_training_admissions':0,'Teacher_Actor_calls':0,'training_started':False,'weights_loaded':False,'script':pin(__file__)}
    save('QA.json',qa)
    text='''# 196位置的实际来源、资源与修订恢复\n\n本目录是离线恢复实体，不是新训练银行。46个原会话、196目标及实际工具反馈全文，原native和资源版本均保留。原226/H/static继续隔离，没有调用Teacher/Actor、运行旧Agent或启动训练。\n\n已恢复此前JSON-write单一提取漏掉的exec cat-heredoc、Python字面量构造及无reuse_reason的旧route card。135个已有screen/resolve元数据限定载体约32.6MB被逐一核验，不是重扫十几GB后凭名字猜来源。首94位置实际属于7条路线、9种route SHA；interview与patent各有两版，不能按一个文件版本处理。\n\n125位置：原card全部字段或两个原route_signature/value_plan对象与下游精确相等，原writer/exec、实际ACK及写出前保护scope可核，下游实际route读取返回含原字段标量，保护只作用于收到之后的目标。63位置：steps/reuse_reason等method精确保留，但source_ids/conditions有累积变化；仍缺原冻结合并/派生的足够身份，不以相似文本或当前幸存源码证明唯一历史因果，继续HOLD。8位置：making_lineage/rubric派生具体缺项仍在。它们都不是内容错误或没有价值的裁定。\n\n新增可复核内容包括191份完整literal文件版本、77次原edit（含参数缺path等失败）、21次可逐字重算的已知前后版本补丁、46终包263文件及35条旧同版本trial/review元数据边。后者保留旧silver身份，不作为新的独立Q或效用结论。Python AST只做字面量/选择器还原和语法检查，没有执行捕获程序。\n\nworkitem-weekly-report：collect_workitems.py完整初版3488字符，weekly_stats.py完整初版7271字符；原idx37缺path失败，idx39正确形式替换两块、idx45再局修一块，精确最终SHA与现存终版匹配。原测试命令、输出、mock服务器启动/终止失败及making记录都保留，不能据最终绿灯把整个程序或原诊断洗正。intro-document-drafting：旧SKILL/模板/阶段说明、原idx43样稿字面修订与反馈均可查，但route两个核心对象的原producer受保护，不能因为输入重新标TRAIN而纳入原制作链。\n\nTARGET_EVIDENCE_AND_DECISIONS_196含实际完整目标和反馈；ORIGINAL_EVENTS_WITH_R_TOOL_FEEDBACK含所有原消息；ROUTE_PRODUCER_TO_ACTUAL_RECEIPT逐版本绑定写出/接收；ORIGINAL_RESOURCE_LITERAL_VERSIONS和ORIGINAL_EDIT_VERSION_CHAINS含全文/参数及前后SHA；FROZEN_COMPLETE_PACKAGE_VERSIONS、FROZEN_PACKAGE_ACTUAL_FILES和SAME_VERSION_TRIAL_AND_REVIEW_EDGES.audit保存包版本与已存在消费边。objects为实际字节实体。\n\n所有原system缺失、原生schema/请求等价、原始provider思考归属仍独立记录；native thinking字段为空不能推成无原R。当前无新正loss准入，没有把恢复实体数或ACK/语法通过当训练样本数。63个方法保留组仍需冻结派生证据，8个元数据仍需原producer；本目录给出实际已取得内容，供根语义审核、独立复核和后续打包，不冒称完整主集已充足。\n'''
    (OUT/'README.md').write_text(text,encoding='utf-8')
    files=[{'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}for p in sorted(OUT.rglob('*'))
        if p.is_file()and p.name!='DELIVERY_MANIFEST.json'and '__pycache__'not in p.parts]
    save('DELIVERY_MANIFEST.json',{'status':'ACTUAL_LINEAGE_RESOURCE_RECOVERY_ROOT_READY_NOT_TRAINING_BANK',
        'files':files,'actual_files':len(files),'actual_bytes':sum(f['bytes']for f in files),'source':pin(GAPS),
        'source_scope':pin(SCOPE),'QA':pin(OUT/'QA.json'),'script':pin(__file__),
        'new_training_admissions':0,'Teacher_Actor_calls':0,'training_started':False,'curation_cost':'UNKNOWN_NOT_ZERO'})
    print(js(qa))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['catalog','recover','verify'],required=True);a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);preserve(Path(__file__))
    if a.phase=='catalog':catalog()
    if a.phase=='recover':recover()
    if a.phase=='verify':verify_and_seal()
