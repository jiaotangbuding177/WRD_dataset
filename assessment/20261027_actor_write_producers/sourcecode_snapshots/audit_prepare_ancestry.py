"""Read-only exact prepare -> Actor task ancestry audit, not a lexical task gate.

Actor inputs may be valid derived tasks.  Protected ancestry is claimed only
with an exact producer output join and actual earlier protected request delivery.
Everything else stays missing pending additional resource-producer proof.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import ast
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT/'output/20261025_wrd_training_dataset/bundle'
OUT = ROOT/'output/20261027_wrd_main_v10/prepare_ancestry_audit'
SID = re.compile(r'conv_[a-f0-9]{12}')


def canonical(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
def sha(raw): return hashlib.sha256(raw if isinstance(raw,bytes) else raw.encode('utf-8')).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):
    p=Path(p).resolve(); raw=p.read_bytes()
    return {'path':str(p),'sha256':sha(raw),'bytes':len(raw)}
def rows(p):
    op=gzip.open if str(p).endswith('.gz') else open
    with op(p,'rt',encoding='utf-8-sig') as f:
        for l in f:
            if l.strip(): yield json.loads(l)
def save(p,x):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def walk(value,path=''):
    yield path,value
    if isinstance(value,dict):
        for k,v in value.items(): yield from walk(v,path+'/'+str(k))
    elif isinstance(value,list):
        for i,v in enumerate(value): yield from walk(v,path+'/'+str(i))
def calls(m):
    return [c for c in m.get('content',[]) if isinstance(c,dict) and c.get('type')=='toolCall'] if isinstance(m.get('content'),list) else []
def text(m):
    c=m.get('content','')
    return c if isinstance(c,str) else '\n'.join(x.get('text','') for x in c if isinstance(x,dict) and x.get('type')=='text')
def events(p):
    found=[]
    for n,line in enumerate(Path(p).read_bytes().split(b'\n'),1):
        if not line.strip():continue
        e=json.loads(line);e=e.get('native_event',e)
        if e.get('type')=='message':found.append((n,e['message']))
    return found


def json_chunks(raw):
    """Parse actual JSON payloads from direct reads or concatenated exec output."""
    decoder=json.JSONDecoder(); offset=0
    while offset<len(raw):
        match=re.search(r'[\[{]',raw[offset:])
        if not match:return
        start=offset+match.start()
        try:value,end=decoder.raw_decode(raw,start)
        except ValueError:offset=start+1;continue
        yield start,value
        offset=end


def emitted_json(call):
    args=call.get('arguments',{});args=json.loads(args) if isinstance(args,str) else args
    if call.get('name')=='write' and isinstance(args.get('content'),str):
        try:value=json.loads(args['content']);kind='native_write'
        except ValueError:
            try:value,end=json.JSONDecoder().raw_decode(args['content'].lstrip());kind='native_write_exact_JSON_object_with_trailing_nonJSON_later_repaired'
            except ValueError:value=None
        if value is not None:yield {'kind':kind,'path':args.get('path'),'content':args['content'],'value':value}
    if call.get('name')!='exec':return
    command=args.get('command',args.get('cmd',''))
    patterns=[r"cat\s*>\s*(?P<path>[^\s]+)\s*<<\s*['\"]?(?P<tag>[A-Za-z0-9_]+)['\"]?\s*\r?\n(?P<body>.*?)\r?\n(?P=tag)(?:\r?\n|$)",
              r"cat\s*<<\s*['\"]?(?P<tag>[A-Za-z0-9_]+)['\"]?\s*>\s*(?P<path>[^\s]+)\s*\r?\n(?P<body>.*?)\r?\n(?P=tag)(?:\r?\n|$)"]
    for pattern in patterns:
        for found in re.finditer(pattern,command,re.S):
            try:value=json.loads(found['body'])
            except ValueError:continue
            yield {'kind':'literal_shell_heredoc_no_execution_by_audit','path':found['path'],'content':found['body'],'value':value}
    python_pattern=r"python(?:3)?(?:\s+-)?\s*<<\s*['\"]?(?P<tag>[A-Za-z0-9_]+)['\"]?\s*\r?\n(?P<body>.*?)\r?\n(?P=tag)(?:\r?\n|$)"
    for found in re.finditer(python_pattern,command,re.S):
        body=found['body']
        output_name=next((name for name in ('tasks.json','routes.json') if name in body),None)
        if not output_name or not re.search(r'json\.dumps?\(',body):continue
        try:tree=ast.parse(body)
        except SyntaxError:continue
        literals={}; unknown=object(); constructors={}
        def partial(node,bindings=None):
            bindings=bindings or {}
            if isinstance(node,ast.Constant):return node.value
            if isinstance(node,ast.Name):return bindings.get(node.id,literals.get(node.id,unknown))
            if isinstance(node,(ast.List,ast.Tuple)):
                values=[partial(value,bindings) for value in node.elts]
                return [value for value in values if value is not unknown]
            if isinstance(node,ast.Dict):
                value={}
                for key,item in zip(node.keys,node.values):
                    if key is None:
                        extra=partial(item,bindings)
                        if isinstance(extra,dict):value.update(extra)
                        continue
                    k,v=partial(key,bindings),partial(item,bindings)
                    if k is not unknown and v is not unknown:value[k]=v
                return value
            if isinstance(node,ast.IfExp):
                condition=partial(node.test,bindings)
                if condition is unknown:return unknown
                return partial(node.body if condition else node.orelse,bindings)
            if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add):
                left,right=partial(node.left,bindings),partial(node.right,bindings)
                if isinstance(left,(str,list)) and type(left) is type(right):return left+right
                if isinstance(left,list) and right is unknown:return left
                if isinstance(right,list) and left is unknown:return right
            return unknown
        for node in tree.body:
            if isinstance(node,ast.FunctionDef):
                append=[c for c in ast.walk(node) if isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute)
                        and c.func.attr=='append' and isinstance(c.func.value,ast.Name) and len(c.args)==1 and isinstance(c.args[0],ast.Dict)]
                if len(append)==1:constructors[node.name]=(node,append[0])
            if isinstance(node,ast.Assign):
                value=partial(node.value)
                if value is unknown:continue
                for target in node.targets:
                    if isinstance(target,ast.Name):literals[target.id]=value
            if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id in constructors:
                fn,append=constructors[node.value.func.id];names=[arg.arg for arg in fn.args.args]
                bindings={name:partial(value) for name,value in zip(names,node.value.args)}
                for name,value in zip(names[len(names)-len(fn.args.defaults):],fn.args.defaults):bindings.setdefault(name,partial(value))
                for key in node.value.keywords:
                    if key.arg:bindings[key.arg]=partial(key.value)
                row=partial(append.args[0],bindings);destination=literals.get(append.func.value.id)
                if isinstance(row,dict) and isinstance(destination,list):destination.append(row)
        dumped=[node.args[0] for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
              and isinstance(node.func.value,ast.Name) and node.func.value.id=='json' and node.func.attr in {'dump','dumps'}
              and node.args]
        for expression in dumped:
            value=partial(expression)
            if value is unknown:continue
            yield {'kind':'native_exec_static_literal_JSON_dump_confirmed_by_output','path':'/workspace/outputs/'+output_name,
                   'content':canonical(value),'value':value,'requires_output_artifact_confirmation':True,
                   'static_projection_not_actual_output_file_bytes':True,'actual_source_command_sha256':sha(command)}


def main():
    protected=set(); original226=set(); protected_pins=[]
    for p in sorted((ROOT/'benchmark').glob('*/contracts/evaluation.jsonl')):
        ids={r.get('session_id') for r in rows(p)}-{None}
        if len(ids)==226:
            assert not original226 or original226==ids
            original226=ids; protected_pins.append(pin(p))
    assert len(original226)==226
    holdout=ROOT/'output/20261026_ablation_v2/holdout_registry.json'
    holdout12=set(SID.findall(canonical(load(holdout))))
    protected=original226|holdout12
    paid=list(rows(ROOT/'output/20261027_wrd_main_v10/clean_inputs/paid_no_skill_actor_evidence.jsonl.gz'))
    inventory={e['episode_id']:e for e in load(ROOT/'research/plans/20261027_wrd_main_v10/CLEAN_ACTOR_INVENTORY.json')['episodes']}
    jobs={j['id']:j for j in rows(BUNDLE/'catalog/jobs.jsonl')}
    episodes=list(rows(BUNDLE/'catalog/episodes.jsonl'))
    prepare_by_route=defaultdict(list)
    for e in episodes:
        if e.get('kind')=='prepare': prepare_by_route[e.get('route_id')].append(e)
    cas={}
    for f in rows(BUNDLE/'archive/file_index.jsonl'):
        cas[f['logical_path']]=BUNDLE/'archive'/f['object']
    cache={}
    route_recovery_path=OUT/'ROUTE_CREATOR_RECOVERY.json'
    route_recovery=load(route_recovery_path) if route_recovery_path.is_file() else {'joins':[]}
    route_joins=defaultdict(list)
    for join in route_recovery.get('joins',[]):
        if join.get('classification')!='TRUE_PROTECTED':continue
        assert pin(join['prepare_events']['path'])==join['prepare_events']
        for creator in join['matched_actual_screen_creators']:
            assert pin(creator['native_events']['path'])==creator['native_events']
        route_joins[join['actor_episode_id']].append(join)
    source_titles={}
    for sid in protected:
        path=ROOT/'output/20261021_workflow_skill_library/sources'/sid/'conversation.json'
        if path.is_file():
            source=load(path);title=source.get('title','')
            user_strings=[value for message in source.get('messages',[]) if message.get('role')=='user'
                          for _,value in walk(message.get('content','')) if isinstance(value,str)]
            if len(title)>=8 and any(title in value for value in user_strings):
                source_titles[sid]={'title':title,'source':pin(path),'original_pointer':'/title',
                                    'title_is_exact_substring_of_recorded_user_body':True}
    results=[]
    for item in paid:
        eid=item['episode_id']; inv=inventory[eid]; job=jobs[inv['job_id']]
        request_path=Path(inv['request_ref']['CAS_path']); request=load(request_path)
        actor_native_path=Path(inv['native_trace_ref']['CAS_path'])
        actor_deliveries=[{'event_line_1based':line,'actual_user_text_sha256':sha(text(message)),
                           'request_input_exact_substring_of_actual_native_user_message':True}
                          for line,message in events(actor_native_path)
                          if message.get('role')=='user' and request['input'] in text(message)]
        assert actor_deliveries, 'actual Actor input delivery is not established'
        case=job.get('payload',{}).get('case',{})
        result={'episode_id':eid,'actor_request':pin(request_path),'actor_task_input_sha256':sha(request['input']),
                'actor_job_id':inv['job_id'],'business_source_ids':item['source_ids'],
                'actor_native_events':pin(actor_native_path),'actual_actor_input_deliveries':actor_deliveries,
                'source_groups':item.get('source_groups',[]),'request_input_equals_catalog_case_prompt':case.get('prompt')==request['input'],
                'task_text_is_not_required_to_equal_original_user':True,'prepared_episode_declared':case.get('_prepared_episode'),
                'classification':'MISSING','missing':[],'matched_producers':[],
                'old_v9_source_scope':item['source_scope'],'content_quality_not_judged_here':True}
        candidates=[]
        explicit=case.get('_prepared_episode')
        if explicit: candidates.append((Path(explicit),None))
        for ep in prepare_by_route[inv['route_id']]:
            p=Path(ep['source_path'])
            if not any(p==q for q,_ in candidates):candidates.append((p,ep['episode_id']))
        for directory,producer_id in candidates:
            event_path=directory/'openclaw_transport/session_events.jsonl'
            if not event_path.is_file() and producer_id:
                event_path=cas.get(f'episodes/{producer_id}/openclaw_transport/session_events.jsonl',event_path)
            if not event_path.is_file():continue
            key=str(event_path)
            if key not in cache:cache[key]=events(event_path)
            messages=cache[key]
            file_states={}
            for ix,(line,m) in enumerate(messages):
                if m.get('role')!='assistant':continue
                for call in calls(m):
                  args=call.get('arguments',{});args=json.loads(args) if isinstance(args,str) else args
                  if call.get('name')=='write' and isinstance(args.get('content'),str):file_states[args.get('path')]=args['content']
                  emissions=list(emitted_json(call))
                  if call.get('name')=='edit' and args.get('path') in file_states:
                    raw=file_states[args['path']]; replacements=[];valid=True
                    for edit in args.get('edits',[]):
                        old,new=edit.get('oldText'),edit.get('newText')
                        if not isinstance(old,str) or not old or not isinstance(new,str) or raw.count(old)!=1:valid=False;break
                        position=raw.index(old);replacements.append((position,position+len(old),new))
                    ordered=sorted(replacements)
                    if any(a[1]>b[0] for a,b in zip(ordered,ordered[1:])):valid=False
                    if valid:
                        for start,end,new in reversed(ordered):raw=raw[:start]+new+raw[end:]
                        file_states[args['path']]=raw
                        try:obj=json.loads(raw)
                        except ValueError:obj=None
                        if obj is not None:emissions.append({'kind':'native_edit_exact_prior_write_state','path':args['path'],'content':raw,'value':obj,'requires_output_artifact_confirmation':True})
                  for emission in emissions:
                    output=emission['value']
                    match=[{'pointer':pointer,'case_id':obj.get('id'),'prompt_sha256':sha(obj['prompt'])}
                           for pointer,obj in walk(output) if isinstance(obj,dict) and obj.get('prompt')==request['input']]
                    if not match:continue
                    output_confirmation=None
                    if emission.get('requires_output_artifact_confirmation') or emission['kind'].endswith('later_repaired'):
                        artifact=directory/'workspace/outputs/tasks.json'
                        if not artifact.is_file():continue
                        try:actual_artifact=load(artifact)
                        except ValueError:continue
                        if not any(isinstance(obj,dict) and obj.get('prompt')==request['input'] for _,obj in walk(actual_artifact)):continue
                        output_confirmation=pin(artifact)
                    proofs=[]; prefix_ids=set(); prior_calls={}
                    for prior_line,prior in messages[:ix]:
                        for pc in calls(prior): prior_calls[pc.get('id')]=pc
                        if prior.get('role') not in {'toolResult','tool'}:continue
                        raw=text(prior);prefix_ids.update(SID.findall(raw))
                        for chunk_offset,obj in json_chunks(raw):
                          for pointer,value in walk(obj):
                            if not isinstance(value,dict) or value.get('source_id') not in protected:continue
                            requests=value.get('requests',[])
                            body=[r for r in requests if isinstance(r,dict) and isinstance(r.get('text'),str) and r['text']]
                            sid=value['source_id']; prior_call=prior_calls.get(prior.get('toolCallId'),{})
                            title=source_titles.get(sid)
                            title_proof=title if title and value.get('title')==title['title'] else None
                            if not body and not title_proof:continue
                            proofs.append({'source_id':sid,'protected_set':'original226' if sid in original226 else 'newH12',
                                'event_line_1based':prior_line,'tool_call_id':prior.get('toolCallId'),'tool_name':prior_call.get('name'),
                                'observation_text_sha256':sha(raw),'json_pointer':pointer,
                                'json_chunk_character_offset':chunk_offset,
                                'delivered_exact_original_user_title_preview':{'sha256':sha(title_proof['title']),'characters':len(title_proof['title']),
                                    'original_source':title_proof['source'],'original_pointer':'/title',
                                    'exact_title_is_substring_of_original_user_body':True} if title_proof else None,
                                'actual_request_texts':[{'id':r.get('id',r.get('message_id')),'sha256':sha(r['text']),'characters':len(r['text'])} for r in body]})
                    result['matched_producers'].append({'producer_episode_id':producer_id,'producer_directory':str(directory),
                        'native_events':pin(event_path),'actual_task_write_event_line_1based':line,'actual_task_write_call_id':call.get('id'),
                        'actual_output_path':emission['path'],'actual_write_content_sha256':sha(emission['content']),
                        'producer_operation':emission['kind'],
                        'emission_hash_is_static_projection_not_actual_file_bytes':emission.get('static_projection_not_actual_output_file_bytes',False),
                        'actual_source_command_sha256':emission.get('actual_source_command_sha256'),
                        'frozen_output_artifact_confirmation':output_confirmation,
                        'matching_task_fields':match,'exact_prompt_projection_into_actor_input':True,
                        'actual_protected_request_body_deliveries_before_task_write':proofs,
                        'all_observed_source_ids_before_write':sorted(prefix_ids),
                        'protected_ids_before_write_not_alone_body_proof':sorted(prefix_ids&protected)})
        if any(p['actual_protected_request_body_deliveries_before_task_write'] for p in result['matched_producers']):
            result['classification']='TRUE_PROTECTED'
            result['basis']='exact native task-write prompt equals actual Actor input; actual earlier protected original request bodies are present in that producer prefix'
        elif route_joins.get(eid) and result['matched_producers']:
            result['classification']='TRUE_PROTECTED'
            result['actual_protected_route_creator_joins']=route_joins[eid]
            result['basis']='exact prepare task to Actor input join; exact route fields actually observed in prepare were produced in an earlier protected native screen prefix'
        elif not result['matched_producers']:
            result['missing'].append('NO_EXACT_NATIVE_PREPARE_WRITE_TO_ACTOR_INPUT_JOIN_YET')
        else:
            result['missing'].append('NO_DIRECT_PROTECTED_BODY_PROOF; MUST_COMPLETE_ROUTE/RESOURCE_PRODUCER_CLOSURE_BEFORE_CLEAN_DERIVED')
        results.append(result)
    OUT.mkdir(parents=True,exist_ok=True)
    save(OUT/'actor_prepare_case_evidence.json',{'schema':'wrd-v10-exact-prepare-actor-ancestry-v1','cases':results})
    decisions={r['episode_id']:r for r in results}
    revocations=[];pending=[];coord_hits=[]
    v9_pins=[]
    for path in sorted((ROOT/'output/20261026_wrd_dataset_v9/sft').glob('*.jsonl.gz')):
        v9_pins.append(pin(path))
        for record in rows(path):
            eid=record.get('episode_id')
            if eid not in decisions:
                if path.name.startswith('coordination.'):
                    hits=sorted(set(decisions)&set(re.findall(r'ep_[a-f0-9]{20}',canonical(record))))
                    if hits:coord_hits.append({'record_id':record['id'],'episode_ids':hits,'shard':path.name})
                continue
            owned=[target for target in record.get('targets',[]) if target.get('supervised_tokens',0)>0]
            entry={'old_record_id':record['id'],'episode_id':eid,'old_bank':record['bank'],'old_split':record['split'],
                   'old_shard':path.name,'old_supervised_tokens':record['supervised_tokens'],
                   'old_weighted_supervised_token_equivalents':sum((hi-lo)*weight for lo,hi,component,weight in record['supervision_spans']),
                   'target_ids_to_zero':[target['id'] for target in owned],
                   'target_message_indices_to_zero':[target['message_index'] for target in owned],
                   'old_supervision_spans_sha256':record['supervision_spans_sha256'],
                   'old_input_ids_sha256_u32le':record['input_ids_sha256_u32le'],
                   'original_files_and_historical_masks_not_modified':True}
            if decisions[eid]['classification']=='TRUE_PROTECTED':
                entry.update({'action_for_future_v10_import':'REVOKE_ALL_POSITIVE_LOSS_FROM_THIS_ACTOR_RECORD',
                    'cause':'OLD_SOURCE_CLOSURE_OMITTED_ACTUAL_PREPARE_PROMPT_PRODUCER_EDGE',
                    'all_actor_targets_affected_because_protected_derived_prompt_visible_from_start':True})
                revocations.append(entry)
            elif decisions[eid]['classification']=='MISSING':
                entry.update({'action_for_future_v10_import':'HOLD_PENDING_PREPARE_RESOURCE_PRODUCER_CLOSURE',
                              'does_not_prove_protected_ancestry':True})
                pending.append(entry)
    for name,items in [('v9_confirmed_target_revocations.jsonl.gz',revocations),('v9_pending_producer_targets.jsonl.gz',pending)]:
        with gzip.open(OUT/name,'wt',encoding='utf-8',newline='\n') as handle:
            for item in items:handle.write(canonical(item)+'\n')
    v9_effect={'scope':'only these 26 historical Actor records and exact references in existing v9 shards; not a universal v9 clean certificate',
               'confirmed_revoked_sequences':len(revocations),'confirmed_revoked_targets':sum(len(r['target_ids_to_zero']) for r in revocations),
               'confirmed_revoked_supervised_tokens':sum(r['old_supervised_tokens'] for r in revocations),
               'confirmed_revoked_weighted_supervised_token_equivalents':sum(r['old_weighted_supervised_token_equivalents'] for r in revocations),
               'pending_sequences':len(pending),'pending_supervised_tokens':sum(r['old_supervised_tokens'] for r in pending),
               'coordination_exact_episode_reference_hits':coord_hits,'old_shard_pins':v9_pins,
               'old_v9_public_release_preserved':True,'v10_does_not_automatically_import_v9_native_auxiliary':True}
    save(OUT/'V9_POSITIVE_LOSS_ERRATUM.json',v9_effect)
    summary={'schema':'wrd-v10-prepare-ancestry-summary-v1','actual_actor_cases':len(results),
        'classifications':dict(Counter(r['classification'] for r in results)),
        'exact_producer_join_cases':sum(bool(r['matched_producers']) for r in results),
        'exact_protected_route_creator_recovery':pin(route_recovery_path) if route_recovery_path.is_file() else None,
        'v9_positive_loss_effect':{k:v for k,v in v9_effect.items() if k not in {'old_shard_pins','coordination_exact_episode_reference_hits'}},
        'protected_source_set_pins':protected_pins,'newH_registry':pin(holdout),
        'lexical_prompt_inequality_is_not_a_contamination_rule':True,'training_started':False,
        'original_data_or_v9_mask_edited':False,'raw_business_content_not_copied_into_report':True,
        'script':pin(Path(__file__))}
    save(OUT/'SUMMARY.json',summary)
    print(json.dumps({k:summary[k] for k in ('actual_actor_cases','classifications','exact_producer_join_cases')},ensure_ascii=False))


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    main()
