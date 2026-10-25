"""Reconstruct saved original teacher SSE deltas, preserving reasoning and order."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import time

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261025_wrd_reasoning_recovery_v4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def blobsha(x):return hashlib.sha256(x.encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def source(p):return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
def line(f,x):f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')

def main():
    started=time.monotonic();reportp=OUT/'EXTRA_TEACHER_SOURCE_DISCOVERY.json';inventory=load(reportp);controlled=OUT/'controlled';controlled.mkdir(exist_ok=True)
    paths=[controlled/'sse_reasoning_pairs.all.jsonl.gz',controlled/'sse_reasoning_pairs.mechanical.jsonl.gz',controlled/'sse_event_order.index.jsonl.gz']
    for p in paths:
        if p.exists():raise ValueError('new SSE recovery outputs required')
    counts=Counter();errors=Counter();by_source=Counter();original_hashes={};episodes=set();reports=[]
    with gzip.open(paths[0],'wt',encoding='utf-8',newline='\n',compresslevel=3) as af,gzip.open(paths[1],'wt',encoding='utf-8',newline='\n',compresslevel=3) as mf,gzip.open(paths[2],'wt',encoding='utf-8',newline='\n',compresslevel=3) as ef:
        for entry in inventory['files']:
            if not entry['is_sse']:continue
            p=Path(entry['path']);assert sha(p)==entry['sha256'];original_hashes[str(p)]=entry['sha256'];base=p.parent
            qp=base/'request.raw.json';rjp=base/'response.json';parsedp=base/'parsed.json';receiptp=base/'receipt.json'
            q=load(qp) if qp.is_file() else None;original=load(rjp) if rjp.is_file() else None
            c=Counter();ids=set();models=set();content=[];reason=[];callparts={};finish=None;usage=None;first={};done=False;problem=[]
            targetid=blobsha(str(base)+'|'+entry['sha256'])[:24]
            for lineno,s in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
                if not s.startswith('data:'):continue
                raw=s[5:].strip()
                if raw=='[DONE]':done=True;c['done_frames']+=1;continue
                try:v=json.loads(raw)
                except json.JSONDecodeError:c['parse_errors']+=1;continue
                c['json_frames']+=1
                if not first:first=v
                if v.get('id'):ids.add(v['id'])
                if v.get('model'):models.add(v['model'])
                if v.get('usage') is not None:usage=v['usage'];c['usage_frames']+=1
                frame_meta={'pair_id':targetid,'source_line_1based':lineno,'json_sha256':blobsha(raw),'choice_delta_spans':[]}
                if v.get('error'):c['error_frames']+=1
                for choice in v.get('choices')or[]:
                    if choice.get('index',0)!=0:problem.append('multiple_choice_indices');continue
                    delta=choice.get('delta')or{}
                    for field,bucket in [('content',content),('reasoning_content',reason)]:
                        val=delta.get(field)
                        if isinstance(val,str) and val:
                            # Every original string increment is kept, even a word such as "off" or "true".
                            start=sum(len(x) for x in bucket);bucket.append(val);c[field+'_nonempty_deltas']+=1;c[field+'_characters']+=len(val)
                            frame_meta['choice_delta_spans'].append({'field':field,'start':start,'end':start+len(val),'delta_sha256':blobsha(val)})
                    for call in delta.get('tool_calls')or[]:
                        idx=call.get('index',0);part=callparts.setdefault(idx,{'id':'','type':'function','function':{'name':'','arguments':''}})
                        if call.get('id'):part['id']+=call['id']
                        if call.get('type'):part['type']=call['type']
                        for key in ['name','arguments']:
                            if isinstance(call.get('function',{}).get(key),str):part['function'][key]+=call['function'][key]
                    if choice.get('finish_reason') is not None:finish=choice['finish_reason'];c['finish_reason_frames']+=1
                line(ef,frame_meta)
            contentstr=''.join(content);reasonstr=''.join(reason);msg={'role':'assistant','content':contentstr,'reasoning_content':reasonstr}
            if callparts:msg['tool_calls']=[callparts[k] for k in sorted(callparts)]
            reconstructed={'id':first.get('id'),'model':first.get('model'),'created':first.get('created'),
                'choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':usage,
                '_mechanically_reconstructed_from_original_saved_sse':True}
            oldmsg=((original or{}).get('choices')or[{}])[0].get('message')or{}
            same_content=oldmsg.get('content')==contentstr
            if not q:problem.append('missing_request')
            if not done:problem.append('missing_sse_done')
            if finish not in {'stop','tool_calls'}:problem.append('non_success_finish_reason_'+str(finish))
            if c['parse_errors']:problem.append('invalid_json_sse_frame')
            if c['error_frames']:problem.append('provider_error_frame')
            if len(ids)>1:problem.append('mixed_response_ids')
            if len(models)>1:problem.append('mixed_models')
            if not (contentstr or callparts):problem.append('no_final_content_or_tool_call')
            if original is not None and not same_content:problem.append('content_differs_from_stored_response_json')
            mechanical=not problem
            episode=next((part for part in p.parts if part.startswith('conv_')),None)
            if episode:episodes.add(episode)
            role='historical_ewi_model_decision_teacher' if episode else 'historical_m5_teacher'
            item={'schema_version':'wrd-original-sse-pair-v4','id':targetid,'episode_id':episode,'request_ordinal':base.name,
                'role_scope':role,'historical_condition':'historical_ewi_selfbuilt_teacher_not_current_native_agent_equivalence',
                'original_request':q,'original_response':reconstructed,'stored_original_response_json':original,
                'original_response_finish_reason':finish,'original_reasoning_characters':len(reasonstr),
                'original_reasoning_pointer':'/choices/0/message/reasoning_content','original_usage':usage,
                'stream_reconstruction_state':'complete_saved_sse' if done and not c['parse_errors'] else 'partial_or_invalid_saved_sse',
                'source_sse':source(p),'source_request':source(qp) if qp.is_file() else None,'source_stored_response':source(rjp) if rjp.is_file() else None,
                'observed_parsed_output':load(parsedp) if parsedp.is_file() else None,'observed_receipt':load(receiptp) if receiptp.is_file() else None,
                'source_parsed':source(parsedp) if parsedp.is_file() else None,'source_receipt':source(receiptp) if receiptp.is_file() else None,
                'source_content_matches_stored_response':same_content,'observed_original_sse_reasoning_not_derived_annotation':True,
                'mechanical_usable':mechanical,'mechanical_exclusion_reasons':sorted(set(problem)),'source_role_audit_pending':True,
                'context_is_exact_observed_request':True,'future_artifacts_added_to_prompt':False,
                'semantic_approved':False,'training_admitted':False,'publication_approved':False,'human_gold':False}
            line(af,item)
            if mechanical:line(mf,item);counts['mechanically_usable_pairs']+=1;counts['mechanically_usable_reasoning_characters']+=len(reasonstr)
            counts['sse_pairs']+=1;counts['pairs_with_original_reasoning']+=bool(reasonstr);counts['original_reasoning_characters']+=len(reasonstr);counts['final_content_characters']+=len(contentstr)
            counts['with_done_frame']+=done;counts['stored_response_content_equal']+=same_content;counts['reasoning_omitted_in_old_response_json']+=bool(reasonstr and not oldmsg.get('reasoning_content'))
            counts.update(c);errors.update(set(problem));by_source[role]+=1
            reports.append({'id':targetid,'episode_id':episode,'source_sse_path':str(p),'source_sse_sha256':entry['sha256'],'reasoning_characters':len(reasonstr),
                'finish_reason':finish,'mechanical_usable':mechanical,'mechanical_exclusion_reasons':sorted(set(problem))})
            for f in [qp,rjp,parsedp,receiptp]:
                if f.is_file():original_hashes[str(f)]=sha(f)
    for p,h in original_hashes.items():assert sha(Path(p))==h
    report={'schema_version':'wrd-original-sse-recovery-report-v4','counts':dict(counts),'mechanical_exclusions':dict(errors),'by_source_role':dict(by_source),
        'different_episode_ids':len(episodes),'pairs':reports,'source_files_unchanged':True,'source_files_hashed':len(original_hashes),
        'controlled_files':[{'path':str(p.relative_to(OUT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in paths],
        'source_inventory_sha256':sha(reportp),'script_sha256':sha(Path(__file__)),'semantic_admission_completed':False,
        'training_started':False,'new_model_calls':0,'elapsed_seconds':round(time.monotonic()-started,3)}
    save(OUT/'SSE_REASONING_RECOVERY_REPORT.json',report)
    print(json.dumps({k:report[k] for k in ['counts','mechanical_exclusions','by_source_role','different_episode_ids','elapsed_seconds']},ensure_ascii=False))

if __name__=='__main__':main()
