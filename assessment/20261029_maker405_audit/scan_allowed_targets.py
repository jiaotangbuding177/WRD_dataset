"""Byte-level creator scan of exactly405 source-admissible maker targets.

Only allowlisted target JSON objects are decoded from the canonical archive.
Native event files are byte-hashed; only the allowlisted event lines are JSON
decoded. Later protected messages are never parsed or used as label evidence.
No shell/Python snippet is executed; AST/literal/shlex are static parsers.
"""
import ast
from collections import Counter,defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import shlex
import time
ROOT=next(p for p in Path(__file__).resolve().parents if(p/'AGENTS.md').is_file());OUT=Path(__file__).resolve().parent
LABELS=ROOT/'output/20261026_wrd_dataset_v9/outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz'
METADATA=ROOT/'output/20261026_wrd_dataset_v9/recovery/episodes.metadata.jsonl.gz'
CANONICAL=ROOT/'output/20261025_wrd_training_dataset/bundle/canonical/native_episodes.jsonl.gz'
SCOPE=ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz'
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8')as f:
        for line in f:
            if line.strip():yield json.loads(line)
def save(p,v):
    assert not p.exists(),str(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def choose_messages(raw,wanted):
    """Select byte-delimited message objects; never decode later messages."""
    key=raw.index(b'"messages"');start=raw.index(b'[',key)+1;depth=1;quoted=False;escaped=False;begin=None;index=0;found={}
    for i in range(start,len(raw)):
        c=raw[i]
        if quoted:
            if escaped:escaped=False
            elif c==92:escaped=True
            elif c==34:quoted=False
            continue
        if c==34:quoted=True;continue
        if c in(123,91):
            if depth==1:begin=i
            depth+=1
        elif c in(125,93):
            depth-=1
            if depth==1 and begin is not None:
                if index in wanted:found[index]=json.loads(raw[begin:i+1])
                index+=1;begin=None
                if index>max(wanted):break
    assert set(found)==set(wanted),(set(found),set(wanted));return found
def static_value(n,env):
    if isinstance(n,ast.Constant):return n.value
    if isinstance(n,ast.Name)and n.id in env:return env[n.id]
    if isinstance(n,(ast.List,ast.Tuple)):return [static_value(x,env)for x in n.elts]
    if isinstance(n,ast.Dict):return{static_value(k,env):static_value(v,env)for k,v in zip(n.keys,n.values)}
    if isinstance(n,ast.BinOp)and isinstance(n.op,ast.Add):return static_value(n.left,env)+static_value(n.right,env)
    if isinstance(n,ast.BinOp)and isinstance(n.op,ast.Div):
        a,b=static_value(n.left,env),static_value(n.right,env)
        if isinstance(a,str)and isinstance(b,str):return a.rstrip('/')+'/'+b.lstrip('/')
    if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in('Path','str')and len(n.args)==1:return str(static_value(n.args[0],env))
    if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and isinstance(n.func.value,ast.Name)and n.func.value.id=='json'and n.func.attr=='dumps':
        value=static_value(n.args[0],env);kwargs={x.arg:static_value(x.value,env)for x in n.keywords};return json.dumps(value,**kwargs)
    raise ValueError('not closed literal')
def python_writes(text):
    try:tree=ast.parse(text)
    except SyntaxError as e:return[],{'status':'SYNTAX_ERROR','line':e.lineno,'message':e.msg}
    found=[];env={};unclosed=[]
    # Top-level statements and closed with-block writes are interpreted only as
    # proposed literal text. Function/control-flow bodies are not simulated.
    def visit(body,env):
        for n in body:
            if isinstance(n,ast.Assign):
                try:v=static_value(n.value,env)
                except Exception:continue
                for target in n.targets:
                    if isinstance(target,ast.Name):env[target.id]=v
            if isinstance(n,ast.With):
                local=dict(env)
                for item in n.items:
                    call=item.context_expr
                    if isinstance(call,ast.Call)and isinstance(call.func,ast.Name)and call.func.id=='open'and call.args and item.optional_vars and isinstance(item.optional_vars,ast.Name):
                        try:
                            path=static_value(call.args[0],env);mode=static_value(call.args[1],env)if len(call.args)>1 else'r'
                            if 'w'in mode or'a'in mode:local[item.optional_vars.id]=('OPEN_FILE',path,mode)
                        except Exception:pass
                visit(n.body,local);continue
            candidates=[n.value]if isinstance(n,(ast.Expr,ast.Assign))and isinstance(n.value,ast.Call)else[]
            for call in candidates:
                if not isinstance(call.func,ast.Attribute):continue
                attr=call.func.attr
                if attr not in('write_text','write_bytes','write'):continue
                try:
                    receiver=call.func.value
                    if attr in('write_text','write_bytes'):path=static_value(receiver,env)
                    elif isinstance(receiver,ast.Call)and isinstance(receiver.func,ast.Name)and receiver.func.id=='open':path=static_value(receiver.args[0],env)
                    else:
                        file=static_value(receiver,env);assert isinstance(file,tuple)and file[0]=='OPEN_FILE';path=file[1]
                    content=static_value(call.args[0],env);assert isinstance(path,str)and isinstance(content,(str,bytes))
                    found.append({'path':path,'content':content.decode('utf-8')if isinstance(content,bytes)else content,'static_statement_line':n.lineno,'mode':'STATIC_LITERAL_PROPOSED_WRITE_NOT_EXECUTED'})
                except Exception:unclosed.append({'line':n.lineno,'method':attr,'reason':'PATH_OR_CONTENT_NOT_CLOSED_LITERAL'})
    visit(tree.body,env);return found,{'status':'AST_PARSE_PASS','unclosed_writes':unclosed}
def command_sources(command):
    sources=[];direct=[]
    for match in re.finditer(r"(?m)(?:python(?:3)?|/\S*/python)\s+-\s*<<\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?\s*\n",command):
        end=re.search(r'(?m)^'+re.escape(match.group(1))+r'\s*$',command[match.end():])
        if end:sources.append(command[match.end():match.end()+end.start()])
    try:
        parts=shlex.split(command)
        for i,p in enumerate(parts[:-1]):
            if p=='-c'and i>0 and('python'in parts[i-1]):sources.append(parts[i+1])
    except ValueError:pass
    for match in re.finditer(r"(?m)cat\s*>\s*([^\s]+)\s*<<\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?\s*\n",command):
        end=re.search(r'(?m)^'+re.escape(match.group(2))+r'\s*$',command[match.end():])
        if end:direct.append({'path':match.group(1).strip('"\''),'content':command[match.end():match.end()+end.start()],'mode':'SHELL_STATIC_HEREDOC_NOT_EXECUTED'})
    return sources,direct
def main():
    started=time.monotonic();assert not(OUT/'REPORT.json').exists()
    scope={x['source_id']:x['status']for x in rows(SCOPE)}
    selected=[x for x in rows(LABELS)if x.get('eligible_scope')and x.get('stage')in('make','legacy_skill_make')];assert len(selected)==405
    for x in selected:
        assert x['source_admission']=='ADMIT'and not x['original226']and not x['holdout12']and not x['protected_sources_visible_prefix']
        assert all(scope.get(s)=='TRAIN'for s in x.get('source_ids_visible_prefix',[]))
    by_episode=defaultdict(list)
    for x in selected:by_episode[x['episode_id']].append(x)
    metadata={x['episode_id']:x for x in rows(METADATA)if x['episode_id']in by_episode};assert set(metadata)==set(by_episode)
    canonical={};canonical_seen=0
    with gzip.open(CANONICAL,'rb')as f:
        for raw in f:
            canonical_seen+=1;header=re.search(rb'"episode_id"\s*:\s*"([^"]+)"',raw[:6000])
            if not header:continue
            episode=header.group(1).decode()
            if episode in by_episode:
                wanted={x['source_message_index']for x in by_episode[episode]};objects=choose_messages(raw,wanted)
                for x in by_episode[episode]:
                    m=objects[x['source_message_index']];assert sha(js(m).encode())==x['source_message_sha256'];canonical[x['id']]=m
    assert len(canonical)==405
    records=[];toolcounts=Counter();operations=Counter();extractions=[];missing=[];native_hashes=[]
    for episode,targets in by_episode.items():
        meta=metadata[episode];ref=meta['source_native'];path=Path(ref['path'])
        if not path.is_file():
            alternate=Path(meta['source_original_path']);path=alternate if alternate.is_file()and digest(alternate)==ref['sha256']else path
        if not path.is_file():missing.append({'episode_id':episode,'expected_native':ref,'targets':[x['id']for x in targets]});continue
        assert digest(path)==ref['sha256'];native_hashes.append({'episode_id':episode,'actual_path':str(path),'sha256':ref['sha256']})
        wanted={x['source_event_line']for x in targets};events={}
        with path.open('rb')as f:
            for number,line in enumerate(f,1):
                if number in wanted:events[number]=json.loads(line)
                if number>=max(wanted):break
        for target in targets:
            event=events[target['source_event_line']];native=event['message'];derived=canonical[target['id']];same_content=native.get('content')==derived.get('content');assert native['role']==derived['role']=='assistant'
            features=[]
            content=native.get('content')
            calls=[b for b in content if isinstance(b,dict)and b.get('type')=='toolCall']if isinstance(content,list)else[]
            for call in calls:
                fn=call['name'];args=call.get('arguments',{});toolcounts[fn]+=1;features.append({'tool_call_id':call.get('id'),'name':fn,'argument_sha256':sha(js(args).encode()),'argument_characters':len(js(args))})
                writes=[];patches=[];parse=[]
                if fn=='write'and isinstance(args.get('content'),str):writes.append({'path':args.get('path',args.get('file_path','PATH_MISSING')),'content':args['content'],'mode':'ORIGINAL_COMPLETE_WRITE_ARGUMENT'})
                elif fn=='edit':operations['edit_calls']+=1;patches.append({'path':args.get('path'),'oldText_sha256':sha(str(args.get('oldText','')).encode()),'newText_sha256':sha(str(args.get('newText','')).encode()),'newText_characters':len(str(args.get('newText',''))),'mode':'ORIGINAL_LOCAL_EDIT_NOT_COMPLETE_PROGRAM'})
                elif fn=='apply_patch':
                    operations['apply_patch_calls']+=1;diff=args.get('input',args.get('patch',''))
                    if isinstance(diff,str):
                        current=None;lines=[]
                        for line in diff.splitlines(keepends=True):
                            if line.startswith('*** Add File: '):
                                if current is not None:writes.append({'path':current,'content':''.join(lines),'mode':'ORIGINAL_NEW_FILE_PATCH'})
                                current=line[len('*** Add File: '):].strip();lines=[]
                            elif line.startswith('*** ')and current is not None:writes.append({'path':current,'content':''.join(lines),'mode':'ORIGINAL_NEW_FILE_PATCH'});current=None
                            elif current is not None and line.startswith('+'):lines.append(line[1:])
                        if current is not None:writes.append({'path':current,'content':''.join(lines),'mode':'ORIGINAL_NEW_FILE_PATCH'})
                        patches.append({'characters':len(diff),'sha256':sha(diff.encode()),'mode':'ORIGINAL_PATCH_PRESERVED_NOT_EXECUTED'})
                elif fn in('exec','execute_python'):
                    code=args.get('code');command=args.get('command','');snippets=[]
                    if isinstance(code,str):snippets.append(code)
                    if isinstance(command,str):s,direct=command_sources(command);snippets+=s;writes+=direct
                    for snippet in snippets:
                        w,proof=python_writes(snippet);writes+=w;parse.append({'python_characters':len(snippet),'sha256':sha(snippet.encode()),**proof})
                for write in writes:
                    value=write.pop('content');blob=value.encode('utf-8');content_sha=sha(blob);p=OUT/'extracted_objects'/content_sha[:2]/content_sha;p.parent.mkdir(parents=True,exist_ok=True)
                    if p.exists():assert p.read_bytes()==blob
                    else:p.write_bytes(blob)
                    syntax=None
                    if str(write['path']).endswith('.py'):
                        try:ast.parse(value);syntax='PYTHON_AST_PASS'
                        except SyntaxError:syntax='PYTHON_AST_FAIL'
                    extract={'target_id':target['id'],'episode_id':episode,'route_id':target['route_id'],'tool_name':fn,'tool_call_id':call.get('id'),**write,'characters':len(value),'bytes':len(blob),'content_sha256':content_sha,'portable_object_path':p.relative_to(OUT).as_posix(),'syntax':syntax,'source_ids_visible_prefix':target['source_ids_visible_prefix'],'source_scope_status':target['scope_status'],'native_event_content_equal_old_canonical':same_content,'business_quality_reviewed':False,'training_admitted':False};extractions.append(extract)
                features[-1].update(static_python_parsers=parse,local_patches=patches,complete_proposed_write_count=len(writes))
            record={'target_id':target['id'],'episode_id':episode,'route_id':target['route_id'],'stage':target['stage'],'scope_status':target['scope_status'],'source_ids_visible_prefix':target['source_ids_visible_prefix'],'current_visible_source_statuses':[scope[s]for s in target['source_ids_visible_prefix']],'source_event_line':target['source_event_line'],'source_message_index':target['source_message_index'],'canonical_message_sha256':target['source_message_sha256'],'original_native_file_path':str(path),'original_native_file_sha256':ref['sha256'],'original_event_sha256':sha(js(event).encode()),'native_content_equal_old_canonical':same_content,'native_tool_features':features,'old_exact_writeproof_empty':not bool(target['exact_produced_file_write_proofs']),'actual_extractions_for_this_target':sum(e['target_id']==target['id']for e in extractions),'training_admitted':False}
            records.append(record);p=OUT/'allowed_targets'/f"{target['id']}.json";save(p,{'provenance':record,'actual_original_target_message':native,'old_canonical_message':derived,'no_past_or_future_protected_messages_copied':True})
    with gzip.open(OUT/'TARGET_SCAN_405.jsonl.gz','wt',encoding='utf-8',newline='\n')as f:
        for x in records:f.write(js(x)+'\n')
    save(OUT/'EXTRACTED_PROPOSED_WRITES.json',extractions)
    report={'schema':'wrd-current-TRAIN-maker405-static-byte-recovery-v1','status':'ACTUAL_ALLOWED_TARGET_SCAN_NOT_QUALITY_ADMISSION','selected_targets':405,'current_TRAIN_visible_source_ids':len(set(s for x in selected for s in x['source_ids_visible_prefix'])),'protocol_only_targets':sum(not x['source_ids_visible_prefix']for x in selected),'observed_source_targets':sum(bool(x['source_ids_visible_prefix'])for x in selected),'selected_episodes':len(by_episode),'actual_native_targets_scanned':len(records),'canonical_target_hashes_matched':len(canonical),'canonical_records_byte_walked_without_decoding_unselected_messages':canonical_seen,'native_file_hashes':native_hashes,'tool_counts':dict(toolcounts),'operation_counts':dict(operations),'complete_static_proposed_writes':len(extractions),'unique_proposed_write_bytes':len({x['content_sha256']for x in extractions}),'actual_extracted_bytes':sum(x['bytes']for x in extractions),'local_edit_or_patch_not_full_program_count':sum(len(f['local_patches'])for x in records for f in x['native_tool_features']),'missing_actual_native_targets':missing,'all_source_scope_guards_passed':True,'protected_message_bodies_decoded_or_copied':0,'only_allowed_native_event_lines_JSON_decoded':True,'code_and_shell_execution_count':0,'new_Agent_calls':0,'training_started':False,'quality_positive_targets_created':0,'ACTIVE_modified':False,'input_pins':[{'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)}for p in(LABELS,METADATA,CANONICAL,SCOPE)],'script_sha256':digest(Path(__file__)),'wall_seconds':time.monotonic()-started,'limitations':['Static proposed writes do not prove action execution, output version, business correctness, source completeness or utility.','Closed-literal parser does not execute control flow, arbitrary function calls or variable formats; unclosed expressions are reported, not called nonexistent.','Current405 is a source-prefix subset, not the entire1763 corpus or all29skills; no inference about unreviewed/protected writers outside this allowlist.']};save(OUT/'REPORT.json',report);print(json.dumps({k:v for k,v in report.items()if k in('selected_targets','actual_native_targets_scanned','tool_counts','complete_static_proposed_writes','unique_proposed_write_bytes','actual_extracted_bytes','missing_actual_native_targets','wall_seconds')}))
if __name__=='__main__':main()
