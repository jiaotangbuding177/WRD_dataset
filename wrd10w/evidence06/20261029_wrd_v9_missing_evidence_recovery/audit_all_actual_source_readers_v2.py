"""100-maker metadata cohort: actual bounded reader calls, no helper rerun."""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json,re,shlex
ROOT=Path('D:/skillloop');BASE=ROOT/'output';OUT=Path(__file__).parent;V9=BASE/'20261026_wrd_dataset_v9'
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def rows(p):return list(map(json.loads,gzip.open(p,'rt',encoding='utf-8')))
def pointer(d,p):
    for k in p.strip('/').split('/') if p else []:
        k=k.replace('~1','/').replace('~0','~');d=d[int(k)] if isinstance(d,list) else d[k]
    return d
def main():
    output=OUT/'ALL_ACTUAL_SOURCE_READER_BINDINGS_V2.json';assert not output.exists()
    scope={x['source_id']:x for x in rows(BASE/'20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz')}
    clusters=rows(OUT/'MAKE_100_EPISODE_CLUSTERS.metadata.jsonl.gz')
    epmeta={x['episode_id']:x for x in rows(V9/'recovery/episodes.metadata.jsonl.gz')}
    findings=[]
    for cluster in clusters:
        ep=epmeta[cluster['episode_id']];native=Path(ep['source_native']['path']);assert pin(native)['sha256']==ep['source_native']['sha256']
        events={i:json.loads(x) for i,x in enumerate(native.open(encoding='utf-8'),1)};messages=[events[i]['message'] for i in ep['source_event_lines']]
        workspace=Path(ep['source_original_path']).parent.parent/'workspace'
        for index in cluster['target_message_indices']:
            message=messages[index];content=message.get('content',[])
            if not isinstance(content,list):continue
            for call in content:
                if call.get('type')!='toolCall' or call.get('name')!='exec':continue
                command=call['arguments'].get('command','')
                if '/inputs/making_tools/read_source.py' not in command:continue
                f={'episode_id':cluster['episode_id'],'source_message_index':index,'source_event_line':ep['source_event_lines'][index],'tool_call_id':call['id'],'native_record':ep['source_native'],
                    'command_sha256_utf8':sha(command.encode()),'positive_loss':0,'original_source_scope_unchanged':True}
                try:
                    args=shlex.split(command)
                    if '--source' not in args:
                        f['status']='NOT_READER_INVOCATION_COMMAND_ONLY_REFERENCES_OR_READS_HELPER';findings.append(f);continue
                    start=args.index('--source')+1;end=next((i for i in range(start,len(args)) if args[i].startswith('--')),len(args));sourcepaths=args[start:end]
                    sourceids=[re.fullmatch(r'/workspace/inputs/conversations/(conv_[0-9a-f]+)\.json',x).group(1) for x in sourcepaths]
                    f['actual_source_argv_paths']=sourcepaths;f['current_sources']=[{'source_id':s,'status':scope.get(s,{}).get('status','MISSING')} for s in sourceids]
                    # Do not open or inspect any protected source record.
                    if any(scope.get(s,{}).get('status')!='TRAIN' for s in sourceids):
                        f['status']='HOLD_CURRENT_NONTRAIN_RUNTIME_SOURCE_ID_ONLY_BODY_NOT_READ';findings.append(f);continue
                    tool=messages[index+1];assert tool['role']=='toolResult' and tool['toolCallId']==call['id']
                    text='\n'.join(x['text'] for x in tool['content'] if x.get('type')=='text') if isinstance(tool['content'],list) else tool['content']
                    anchor=re.search(r'\{\s*"schema"\s*:\s*"wrd-source-text-chunks-v1"',text)
                    if anchor is None:
                        f['status']='HOLD_SOURCE_READER_OUTPUT_NOT_PRESENT_IN_ACTUAL_RETURN';f['note']='Command may redirect a batch to a local file; actual receipt of its contents must be bound separately.';findings.append(f);continue
                    payload,unused_end=json.JSONDecoder().raw_decode(text[anchor.start():]);assert payload['schema']=='wrd-source-text-chunks-v1' and payload['source_ids']==sourceids
                    f.update(cursor_in=payload['cursor_in'],next_cursor=payload['next_cursor'],complete=payload['complete'],actual_next_tool_message_index=index+1,actual_payload_sha256_utf8=sha(text.encode()))
                    records={};pins=[]
                    for path,sid in zip(sourcepaths,sourceids):
                        source=workspace/path.removeprefix('/workspace/');record=json.loads(source.read_text(encoding='utf-8-sig'))
                        assert record.get('session_id',record.get('source_id'))==sid
                        records[sid]=record;pins.append({'source_id':sid,'actual_mounted_file':pin(source)})
                    proof=[]
                    for chunk in payload['chunks']:
                        sid=chunk['source_id'];assert sid in sourceids
                        original=next(x for x in records[sid]['messages'] if x['id']==chunk['message_id']);leaf=pointer(original.get('content',''),chunk['leaf_path']);raw=leaf.encode()
                        part=raw[chunk['byte_start']:chunk['byte_end']]
                        assert sha(raw)==chunk['leaf_sha256'] and part.decode()==chunk['text'] and sha(part)==chunk['text_sha256']
                        proof.append({k:chunk[k] for k in ['source_id','message_id','leaf_path','leaf_sha256','byte_start','byte_end','text_sha256']})
                    f.update(status='PASS_ACTUAL_RECEIVED_CHUNKS_CURRENT_TRAIN_LEAF_BYTES_BOUND',source_files=pins,chunk_metadata_no_body=proof,chunks=len(proof),received_UTF8_bytes=sum(x['byte_end']-x['byte_start'] for x in proof))
                except (ValueError,KeyError,AssertionError,AttributeError,OSError,StopIteration) as error:
                    f['status']='HOLD_LOCAL_PARSE_OR_IDENTITY_OR_PAYLOAD_GAP';f['error_type']=type(error).__name__;f['gap_note']=str(error)[:180]
                findings.append(f)
    passrows=[x for x in findings if x['status'].startswith('PASS_')]
    data={'schema':'wrd-100-maker-actual-bounded-source-reader-edge-audit-v1','known_source_TRAIN100_episode_metadata_cohort':100,'command_mentions':len(findings),'actual_matching_invocations':sum(x['status']!='NOT_READER_INVOCATION_COMMAND_ONLY_REFERENCES_OR_READS_HELPER' for x in findings),
        'statuses':dict(Counter(x['status'] for x in findings)),'passed_calls':len(passrows),'passed_distinct_episodes':len({x['episode_id'] for x in passrows}),
        'actual_passed_chunks':sum(x['chunks'] for x in passrows),'actual_passed_received_UTF8bytes':sum(x['received_UTF8_bytes'] for x in passrows),'records':findings,
        'not_whole_source_ancestry_or_semantic_admission':True,'no_helper_or_Agent_model_business_execution':True,'no_protected_source_body_opened':True,'positive_loss':0,'curation_cost':'UNKNOWN_NOT_ZERO'}
    output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest={'files':[pin(Path(__file__)),pin(output)],'source_metadata_pins':[pin(OUT/'MAKE_100_EPISODE_CLUSTERS.metadata.jsonl.gz'),pin(V9/'recovery/episodes.metadata.jsonl.gz')],'frozen05_modified':False,'positive_loss':0}
    (OUT/'ALL_ACTUAL_SOURCE_READER_BINDINGS_V2_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:data[k] for k in ['command_mentions','actual_matching_invocations','statuses','passed_distinct_episodes','actual_passed_chunks','actual_passed_received_UTF8bytes']}))

if __name__=='__main__':main()


