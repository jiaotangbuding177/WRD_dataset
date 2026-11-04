"""Bind actual source-reader argv and received UTF8 chunks without rerunning it."""
from pathlib import Path
import gzip,hashlib,json,re,shlex
ROOT=Path('D:/skillloop');BASE=ROOT/'output';OUT=Path(__file__).parent
CENSUS=OUT.parent
V9=BASE/'20261026_wrd_dataset_v9';EPID='ep_df95d2f3cf09628aa3ac'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return list(map(json.loads,gzip.open(p,'rt',encoding='utf-8')))
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pointer(d,p):
    if not p:return d
    for k in p.strip('/').split('/'):
        k=k.replace('~1','/').replace('~0','~');d=d[int(k)] if isinstance(d,list) else d[k]
    return d
def main():
    assert not(OUT/'HTML_READER_BINDING_CANDIDATE.json').exists()
    scope={x['source_id']:x for x in rows(BASE/'20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz')}
    ep=next(x for x in rows(V9/'recovery/episodes.metadata.jsonl.gz') if x['episode_id']==EPID)
    native=Path(ep['source_native']['path']);assert pin(native)['sha256']==ep['source_native']['sha256']
    events={i:json.loads(line) for i,line in enumerate(native.open(encoding='utf-8'),1)}
    messages=[events[i]['message'] for i in ep['source_event_lines']]
    resources=[x for x in rows(CENSUS/'MAKE_PRIOR_RESOURCES.metadata.jsonl.gz') if x['episode_id']==EPID]
    indexnode=next(x for x in resources if x['native_path']=='/workspace/inputs/making_input_index.json')
    indexpath=Path(next(x['path'] for x in indexnode['carriers'] if x['matches_expected_sha256']))
    index=load(indexpath);selected=index['selected_sources'];assert len(selected)==2 and all(scope[x['source_id']]['status']=='TRAIN' for x in selected)
    workspace=Path(ep['source_original_path']).parent.parent/'workspace'
    recordpaths={};records={};recordpins=[]
    for x in selected:
        mounted=workspace/x['conversation'].removeprefix('/workspace/')
        resource=next(r for r in index['resources'] if r['native_path']==x['conversation'])
        expected=resource['pin']['sha256'];assert pin(mounted)['sha256']==expected
        record=load(mounted);assert record.get('session_id',record.get('source_id'))==x['source_id']
        records[x['source_id']]=record;recordpaths[x['conversation']]=x['source_id']
        recordpins.append({'source_id':x['source_id'],'current_scope':scope[x['source_id']],'mounted_native_path':x['conversation'],'actual_mounted_file':pin(mounted),'original_pin_metadata':resource['pin'],
            'source_record_sha256_is_separate_field_not_assumed_file_SHA':x['source_record_sha256']})
    calls=[];previous_cursor=None;totalchunks=0;deliveredbytes=0
    for index_m,m in enumerate(messages):
        if m.get('role')!='assistant' or not isinstance(m.get('content'),list):continue
        for call in m['content']:
            if call.get('type')!='toolCall' or call.get('name')!='exec':continue
            command=call['arguments'].get('command','')
            if '/inputs/making_tools/read_source.py' not in command:continue
            args=shlex.split(command);p=args.index('--source')+1;end=next((i for i in range(p,len(args)) if args[i].startswith('--')),len(args));paths=args[p:end]
            ids=[recordpaths[x] for x in paths];assert all(scope[x]['status']=='TRAIN' for x in ids)
            cursor=args[args.index('--cursor')+1] if '--cursor' in args else '0:0'
            following=messages[index_m+1];assert following['role']=='toolResult' and following.get('toolCallId')==call['id']
            c=following['content'];text='\n'.join(x['text'] for x in c if x.get('type')=='text') if isinstance(c,list) else c
            payload=json.loads(text);assert payload['schema']=='wrd-source-text-chunks-v1' and payload['source_ids']==ids and payload['cursor_in']==cursor
            if calls:assert cursor==previous_cursor
            else:assert cursor=='0:0'
            proof=[]
            for chunk in payload['chunks']:
                sid=chunk['source_id'];assert sid in ids and scope[sid]['status']=='TRAIN'
                original=next(x for x in records[sid]['messages'] if x['id']==chunk['message_id'])
                leaf=pointer(original.get('content',''),chunk['leaf_path']);raw=leaf.encode();part=raw[chunk['byte_start']:chunk['byte_end']]
                assert sha(raw)==chunk['leaf_sha256'] and part.decode()==chunk['text'] and sha(part)==chunk['text_sha256']
                deliveredbytes+=len(part);totalchunks+=1
                proof.append({k:chunk[k] for k in ['source_id','message_id','leaf_path','leaf_sha256','byte_start','byte_end','text_sha256']})
            previous_cursor=payload['next_cursor'];calls.append({'assistant_message_index':index_m,'source_event_line':ep['source_event_lines'][index_m],'tool_call_id':call['id'],
                'command_sha256_utf8':sha(command.encode()),'actual_source_argv_paths':paths,'source_ids_all_current_TRAIN':ids,'cursor_in':cursor,'next_cursor':previous_cursor,'complete':payload['complete'],
                'actual_received_tool_result_message_index':index_m+1,'actual_tool_result_source_event_line':ep['source_event_lines'][index_m+1],'received_payload_sha256_utf8':sha(text.encode()),
                'original_message_leaf_UTF8_byte_exact_chunks':proof})
    assert calls and calls[-1]['complete'] and previous_cursor is None
    scriptnode=next(x for x in resources if x['native_path']=='/workspace/inputs/making_tools/read_source.py')
    result={'schema':'wrd-original-native-source-reader-specific-runtime-binding-candidate-v1','status':'PARTIAL_SOURCE_RUNTIME_EDGE_CLOSED_CANDIDATE_NOT_WHOLE_EPISODE_TRAIN_ADMISSION',
        'episode_id':EPID,'native_original':pin(native),'making_input_index':pin(indexpath),'read_source_script_identity':scriptnode['file_identity'],
        'actual_current_TRAIN_source_files':recordpins,'actual_reader_calls':calls,'calls_count':len(calls),'original_received_chunks':totalchunks,'original_received_text_UTF8_bytes':deliveredbytes,
        'complete_cursor_chain_and_each_actual_received_chunk_matches_exact_original_leaf':'PASS','actual_native_source_reader_not_rerun':True,
        'proposed_graph_edge':{'child_node_id':scriptnode['node_id'],'condition':'Only these exact original invocation sites/argv and matching tool feedback; do not close all reads of this script by source SHA alone.',
            'runtime_source_ids':[x['source_id'] for x in selected],'parent_source_files':[x['actual_mounted_file'] for x in recordpins]},
        'still_unresolved':['route/new_route producer exact original prefix','generic making contract/index/framework derivation and specifically read contents','resource catalog and merge context actual producers','dynamic/malformed shell-variable read path identities','all program versions and correctness/feedback semantic credit'],
        'original_episode_metadata_other_source_IDs_are_not_automatically_read':True,'no_protected_source_body_read':True,'whole_held46_targets_source_scope_unchanged':True,'candidate_positive_loss':0,
        'no_new_native_Agent_model_business_training_run':True,'curation_cost':'UNKNOWN_NOT_ZERO'}
    save('HTML_READER_BINDING_CANDIDATE.json',result)
    save('HTML_READER_BINDING_MANIFEST.json',{'files':[pin(OUT/'audit.py'),pin(OUT/'HTML_READER_BINDING_CANDIDATE.json')],'source_pins':[pin(native),pin(indexpath)],'positive_loss':0,'frozen05_modified':False})
    print(json.dumps({'status':result['status'],'calls':len(calls),'chunks':totalchunks,'received_UTF8bytes':deliveredbytes,'source_ids':[x['source_id'] for x in selected],'sha256':pin(OUT/'HTML_READER_BINDING_CANDIDATE.json')['sha256']}))

if __name__=='__main__':main()


