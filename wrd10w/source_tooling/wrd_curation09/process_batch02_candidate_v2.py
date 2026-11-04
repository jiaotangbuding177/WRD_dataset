"""Explicit root-reviewed supplemental masks and prior helper declaration."""
import gzip,json
from pathlib import Path
from process_batch02_candidates import OUT,sha,h,text,dump

def main():
    source=OUT/'SCOPED_CANDIDATES_FINAL14.jsonl.gz';dest=OUT/'SCOPED_CANDIDATES_FINAL14_v2.jsonl.gz'
    rows=list(map(json.loads,gzip.open(source,'rt',encoding='utf8')));proofs=[]
    for row in rows:
        oid=row['owner_id'];target=row['messages'][2]
        if oid in {'44d544efa0510fb714da6712','ac76ab7ead15378debb0e555'}:
            content=json.loads(target['tool_calls'][0]['function']['arguments'])['content']
            lo,hi,expected,reason=(681,684,'现役的','Historical table snapshot does not establish current/active generation status.')if oid.startswith('44d')else(2092,2095,'第③项','Source pasted filename has no explicit3; preserve wrong source-number attribution at loss0.')
            assert content[lo:hi]==expected,(oid,content[lo:hi])
            extra={'start':lo,'end':hi,'text':expected,'text_sha256':h(expected),'reason':reason}
            old=list(row['target_code_unicode_exclusions']);row['target_code_unicode_exclusions']=sorted(old+[extra],key=lambda x:x['start'])
            for a,b in zip(row['target_code_unicode_exclusions'],row['target_code_unicode_exclusions'][1:]):assert a['end']<=b['start']
            proofs.append({'owner_id':oid,'operation':'ADD_EXACT_ARGUMENT_CONTENT_NEGATIVE_SPAN','added':extra,'all_prior_spans_unchanged':all(x in row['target_code_unicode_exclusions']for x in old),'target_original_code_sha256':h(content)})
        if oid=='af98d54fb39ba95526215440':
            packet=json.loads(Path(row['source_context']['path']).read_text(encoding='utf8'))
            native=packet['original_context']['messages'][0];value=text(native)
            lo=value.index('图像生成命令是 python ');end='工具执行成功与否以本次实际结果为准。';hi=value.index(end,lo)+len(end);excerpt=value[lo:hi]
            proof={'author':'NEW_CURATOR_STATE_ADDITION_FROM_PRE_ACTION_ORIGINAL_ENVIRONMENT',
                'original_context_message_index':0,'original_context_message_sha256_sorted':h(json.dumps(native,ensure_ascii=False,sort_keys=True,separators=(',',':'))),
                'original_content_unicode_start':lo,'original_content_unicode_end':hi,'text':excerpt,'text_sha256':h(excerpt),
                'source_packet_sha256':row['source_context']['sha256'],'causal_precondition':0<row['original_message_index'],
                'service_success_or_image_truth_prejudged':False}
            row['messages'][1]['content']+='\n本步开始前原环境已明确提供下列CLI说明（原消息0逐字片段；只说明如何尝试，不保证本次后端服务成功）：\n'+excerpt+'\n'
            row['curator_state_addendum_provenance']=proof;proofs.append({'owner_id':oid,'operation':'ADD_CAUSAL_HELPER_DECLARATION_TO_NEW_FUNCTIONAL_STATE','proof':proof})
    with gzip.open(dest,'wt',encoding='utf8')as stream:
        for row in rows:stream.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    dump(OUT/'CANDIDATE_FINAL14_v2_TRANSFORM.json',{'status':'FROZEN_ROOT_REQUESTED_V2_NOT_MAIN_ADMISSION','base':{'path':str(source),'sha256':sha(source)},
        'output':{'path':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size},'count':14,'transformations':proofs,
        'original_target_args_and_public_text_unchanged':True,'original_R':0,'new_R':0,'training_started':False,'business_calls':0,'script_sha256':sha(__file__)})
    print(json.dumps({'path':str(dest),'sha256':sha(dest),'changes':len(proofs)},ensure_ascii=False))

if __name__=='__main__':main()
