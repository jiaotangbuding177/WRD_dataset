"""Recover actual provider reasoning/actions and make explicitly reviewed views.

Raw API bytes are immutable evidence, never an automatic semantic approval.
The core-seven student view is explicitly distinct from the 53-tool runtime.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

CORE={'ls','read','write','edit','apply_patch','exec','process'}

def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def recover(folder):
    receipt=load(folder/'receipt.json')
    assert receipt['status']=='COMPLETE' and receipt['http_status']==200
    request=folder/'request.raw.json'; response=Path(receipt['response_path'])
    assert digest(request)==receipt['request_sha256'] and digest(response)==receipt['response_sha256']
    blob=response.read_bytes()
    if receipt['response_mode']=='JSON':
        value=json.loads(blob); message=value['choices'][0]['message']
        return message,{'finish_reason':value['choices'][0].get('finish_reason'),'usage':value.get('usage')},request,response
    content=[]; reasoning=[]; calls={}; finish=None; usage=None; saw_done=False; reasoning_keys=set()
    for block in blob.decode('utf-8').replace('\r\n','\n').split('\n\n'):
        payload='\n'.join(line[5:].lstrip(' ') for line in block.splitlines() if line.startswith('data:'))
        if not payload:continue
        if payload=='[DONE]':saw_done=True;continue
        value=json.loads(payload)
        if value.get('usage') is not None:usage=value['usage']
        for choice in value.get('choices',[]):
            if choice.get('index',0)!=0:continue
            delta=choice.get('delta',{})
            if delta.get('content'):content.append(delta['content'])
            for key in ('reasoning_content','reasoning'):
                if isinstance(delta.get(key),str) and delta[key]:
                    reasoning_keys.add(key)
                    if key=='reasoning_content':reasoning.append(delta[key])
            for part in delta.get('tool_calls',[]):
                c=calls.setdefault(part.get('index',0),{'id':'','type':'function','function':{'name':'','arguments':''}})
                if part.get('id'):c['id']=part['id']
                f=part.get('function',{})
                c['function']['name']+=f.get('name','');c['function']['arguments']+=f.get('arguments','')
            if choice.get('finish_reason') is not None:finish=choice['finish_reason']
    assert saw_done and finish in {'stop','tool_calls'}, 'incomplete_or_unexpected_provider_finish'
    message={'role':'assistant','content':''.join(content),'reasoning_content':''.join(reasoning)}
    if calls:message['tool_calls']=[calls[k] for k in sorted(calls)]
    return message,{'finish_reason':finish,'usage':usage,'reasoning_keys_seen':sorted(reasoning_keys),
        'only_explicit_reasoning_content_was_recovered':True},request,response


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--episode',type=Path,required=True)
    ap.add_argument('--review',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    job=load(a.episode/'job.json'); review=load(a.review) if a.review else {'responses':[]}
    decisions={r['call_id']:r for r in review['responses']}
    ledger=[];admitted=[]; held=[]
    for folder in sorted((a.episode/'api_audit').iterdir()):
        if not folder.is_dir():continue
        try:message,meta,request,response=recover(folder)
        except (AssertionError,KeyError,ValueError,OSError) as exc:
            held.append({'call_id':folder.name,'reason':'INCOMPLETE_OR_UNSUPPORTED_CAPTURE','error_type':type(exc).__name__});continue
        actual=load(request)
        row={'call_id':folder.name,'message':message,'provider_meta':meta,
            'response_layer':'FIXED_NATIVE_COMPATIBLE_API_RETURN',
            'independent_upstream_provider_generation_is_not_assumed':True,
            'request':str(request),'request_sha256':digest(request),'response':str(response),'response_sha256':digest(response),
            'native_messages':actual['messages'],'native_tools':actual.get('tools',[]),'original_reasoning_chars':len(message.get('reasoning_content',''))}
        ledger.append(row)
        d=decisions.get(folder.name)
        if not d or d.get('semantic_approved') is not True:
            held.append({'call_id':folder.name,'reason':'NOT_INDEPENDENTLY_SEMANTICALLY_REVIEWED'});continue
        assert d.get('rationale') and (d.get('approved_components') or d.get('approved_field_ranges')) and d.get('evidence_refs')
        assert d['response_sha256']==row['response_sha256']
        messages=deepcopy(actual['messages']);messages.append(message)
        text_projections=[]
        unsupported=False
        for index,m in enumerate(messages):
            content=m.get('content')
            if isinstance(content,list):
                if not all(isinstance(b,dict) and b.get('type')=='text' and isinstance(b.get('text'),str) for b in content):
                    unsupported=True;break
                m['content']='\n'.join(b['text'] for b in content)
                text_projections.append({'message_index':index,'rule':'JOIN_COMPLETE_TEXT_BLOCKS_WITH_NEWLINE',
                    'original_blocks_sha256':hashlib.sha256(js(content).encode()).hexdigest(),
                    'projected_text_sha256':hashlib.sha256(m['content'].encode()).hexdigest()})
        if unsupported:
            held.append({'call_id':folder.name,'reason':'NON_TEXT_BLOCK_REQUIRES_OTHER_DECLARED_INTERFACE'});continue
        # Preserve actual system, past tool observations and target payload.
        # Only unrelated tool definitions are omitted in this declared view.
        tools=[t for t in actual.get('tools',[]) if t.get('type')=='function' and t['function']['name'] in CORE]
        previous_names={c['function']['name'] for m in messages for c in m.get('tool_calls',[])}
        if not previous_names<=CORE:
            held.append({'call_id':folder.name,'reason':'NON_CORE_HISTORY_REQUIRES_OTHER_DECLARED_INTERFACE'});continue
        identity='native_'+job['job_id']+'_'+folder.name
        group='v10_native_group_'+hashlib.sha256(js(sorted(job['source_ids'])).encode()).hexdigest()[:20]
        admitted.append({'id':identity,'source_ids':job['source_ids'],'source_group_id':group,'split':'train',
            'stage':job['stage'],'bank':'native_wrd_main','source_admission':'ADMIT','training_admitted':True,
            'annotation_provenance':'ACTUAL_NATIVE_COMPATIBLE_API_RESPONSE_WITH_INDEPENDENT_AI_SILVER_REVIEW',
            'messages':messages,'tools':tools,'supervision_message_indices':[len(messages)-1],
            'message_loss_mask':[0]*(len(messages)-1)+[1], 'approved_components':d.get('approved_components',[]),
            'approved_field_ranges':[{**r,'message_index':len(messages)-1} for r in d.get('approved_field_ranges',[])],
            'allow_reviewed_completion_prefix':d.get('allow_reviewed_completion_prefix',False),
            'loss_multiplier':d.get('loss_multiplier',1.0),
            'tool_schema_provenance':{'path':str(request),'sha256':row['request_sha256']},
            'student_view':'DECLARED_CORE7_TOOL_CATALOG_PROJECTION_FULL_SYSTEM_AND_PAST_MESSAGES_RETAINED',
            'complete_text_block_projection':text_projections,
            'is_original_native_request_identical':False,'runtime_still_has_53_tools':True,
            'is_full_autonomous_execution_demonstration':False,'evidence':{k:row[k] for k in ('call_id','request','request_sha256','response','response_sha256','provider_meta')},
            'semantic_review':d,'frozen_job_sha256':digest(a.episode/'job.json'),
            'source_allowlist_sha256':job['source_allowlist_sha256'],'resource_ancestry_sha256':job['resource_ancestry_sha256'],
            'future_feedback_in_model_input':False})
    for name, values in [('provider_responses.original.jsonl.gz',ledger),('reviewed.student_views.jsonl.gz',admitted)]:
        with gzip.open(a.output/name,'wt',encoding='utf-8',newline='\n') as f:
            for row in values:f.write(js(row)+'\n')
    save(a.output/'EXTRACTION_REPORT.json',{'captured_complete_responses':len(ledger),'original_readable_R_chars':sum(r['original_reasoning_chars'] for r in ledger),
        'response_count_unit':'native-compatible HTTP responses, not necessarily independent paid upstream generations',
        'provider_responses_filename_is_a_historical_name_not_a_cost_count':True,
        'reviewed_student_records':len(admitted),'held':held,'raw_fields_and_messages_preserved':True,
        'semantic_review_file':str(a.review) if a.review else None,'weights_loaded':False,'training_started':False,
        'script_sha256':digest(Path(__file__))})
    print(js({'responses':len(ledger),'reviewed_student_records':len(admitted),'held':len(held)}))

if __name__=='__main__':main()
