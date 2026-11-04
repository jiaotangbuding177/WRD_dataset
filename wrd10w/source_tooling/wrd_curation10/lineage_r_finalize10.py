"""Add exact original SSE field provenance and bounded old-root R absence audit.
Never changes supplied early15 packets or admits a training label.
"""
from pathlib import Path
import collections,difflib,gzip,hashlib,json,re

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation10/reasoning_native10'
def h(b):return hashlib.sha256(b if isinstance(b,bytes)else b.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8-sig')as f:return[json.loads(l)for l in f if l.strip()]
def pin(p):p=Path(p);return{'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def save(n,x):
    p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode());return pin(p)
def gzsave(n,rr):
    p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('wb')as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)as f:
            for r in rr:f.write((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode())
    return pin(p)

def raw_R_fields(api):
    result=[]
    for a in api:
        p=Path(a['source_compatible_API_response']['path']);b=p.read_bytes();assert h(b)==a['source_compatible_API_response']['sha256']
        ids=set();assembled=[];offset=0
        for fi,match in enumerate(re.finditer(rb'(.*?)(?:\r?\n\r?\n|$)',b,re.S)):
            block=match.group(1);payload=b'\n'.join(l[5:].lstrip(b' ')for l in block.splitlines()if l.startswith(b'data:'))
            if not payload or payload==b'[DONE]':continue
            v=json.loads(payload)
            if v.get('id'):ids.add(v['id'])
            for ci,c in enumerate(v.get('choices',[])):
                if c.get('index',0)!=0:continue
                r=c.get('delta',{}).get('reasoning_content','')
                if not r:continue
                result.append({'episode_id':a['episode_id'],'call_id':a['call_id'],'response_id':a['response_id'],
                  'source_response_pin':a['source_compatible_API_response'],'frame_index':fi,
                  'source_frame_byte_start':match.start(1),'source_frame_byte_end':match.end(1),'source_frame_sha256':h(block),
                  'field':f'choices[{ci}].delta.reasoning_content',
                  'decoded_field_unicode_start':0,'decoded_field_unicode_end':len(r),'field_text_sha256':h(r),
                  'joined_original_R_unicode_start':offset,'joined_original_R_unicode_end':offset+len(r),
                  'frame_offsets_are_raw_bytes_field_offsets_are_decoded_unicode_not_escaped_JSON_bytes':True})
                offset+=len(r);assembled.append(r)
        assert ids=={a['response_id']}and''.join(assembled)==a['original_R']
    return gzsave('ORIGINAL_SSE_R_FIELD_FRAME_MAP.metadata.jsonl.gz',result),len(result)

def old_roots():
    base=Path('E:/skillloop_runs/w4/native_episodes')
    roots=[base/'meeting-minutes-formatting__repair1',base/'meeting-minutes-formatting__repair2',
      Path('E:/skillloop_runs/20261021_workflow_library_parallel4_recovery1/native_episodes/meeting-minutes-formatting_gen_01')]
    result=[]
    for root in roots:
        native=root/'openclaw_transport/session_events.jsonl';events=[json.loads(l)for l in native.read_text(encoding='utf-8-sig').splitlines()if l.strip()]
        ms=[e['message']for e in events if e.get('type')=='message'];sid=next(e['id']for e in events if e.get('type')=='session')
        rt=[b for m in ms for b in (m.get('content',[])if isinstance(m.get('content'),list)else[])if isinstance(b,dict)and b.get('type')in {'thinking','reasoning'}and (b.get('thinking')or b.get('text')or b.get('reasoning'))]
        fields=[m[k]for m in ms for k in ['reasoning_content','reasoning']if isinstance(m.get(k),str)and m[k]]
        meter=root/'metering'/(root.name+'.native.jsonl');mm=[json.loads(l)for l in meter.read_text(encoding='utf-8-sig').splitlines()if l.strip()]
        types=collections.Counter(m.get('event')for m in mm)
        keys=sorted({k for m in mm for k in m})
        md=load(root/'metering'/(root.name+'.metrics.json'))
        assert not rt and not fields
        assert set(types)<={'native_start','native_usage','native_finish_reason','native_done_frame','native_stream_end'}
        result.append({'root':str(root),'native_session_id':sid,'native_pin':pin(native),'native_messages':len(ms),
          'native_nonempty_explicit_thinking_blocks':len(rt),'native_nonempty_original_R_fields':len(fields),
          'meter_pin':pin(meter),'meter_event_types':dict(types),'meter_union_field_names':keys,
          'meter_has_R_text_body':False,'metrics_pin':pin(root/'metering'/(root.name+'.metrics.json')),
          'metrics_reasoning_tokens_reported_numeric_only':md.get('measured_reasoning_tokens_subset'),
          'metrics_API_exchanges':md.get('api_exchanges'),'metrics_API_calls_length':len(md.get('api_calls',[])),
          'direct_episode_api_audit_directory_exists':(root/'api_audit').exists(),
          'decision':'NO_PLAINTEXT_ORIGINAL_R_IN_CHECKED_NATIVE_AND_METER_CARRIERS',
          'original_R_missing_in_checked_carriers_is_not_a_global_no_R_claim':True})
    return save('REPAIR1_REPAIR2_GEN01_ORIGINAL_R_CARRIER_AUDIT.json',result)

def mismatch(api):
    out=[]
    for a in api:
        if a['native_same_recorded_response_ID_and_full_nonthought_output_tool_JSON_ID_exact']:continue
        cp=ROOT/'output/20261031_wrd_curation10/identity/content_review'/a['episode_id']/'CONTEXT.original.audit.jsonl.gz'
        c=rows(cp)[0];n=c['messages'][a['native_message_index']]
        call=next(x for x in n['content']if x.get('type')=='toolCall');args=json.loads(a['original_response']['tool_calls'][0]['function']['arguments'])
        aa=args['content'];bb=call['arguments']['content']
        diff=[{'op':tag,'API_unicode_range':[i,j],'native_unicode_range':[k,l],
          'API_slice_sha256':h(aa[i:j]),'native_slice_sha256':h(bb[k:l]),
          'API_slice_characters':j-i,'native_slice_characters':l-k,
          'native_slice_is_literal_mask_marker':bool(bb[k:l])and set(bb[k:l])=={'*'}}
          for tag,i,j,k,l in difflib.SequenceMatcher(None,aa,bb,autojunk=False).get_opcodes()if tag!='equal']
        output=ROOT/'output/20261027_wrd_main_v10/runtime_preflight/episodes'/a['stage']/'workspace'/args['path'].removeprefix('/workspace/')
        assert output.read_bytes()==aa.encode()
        out.append({'episode_id':a['episode_id'],'call_id':a['call_id'],'response_id':a['response_id'],
          'same_RID_and_tool_name_id_path':True,'native_body_differences':diff,
          'final_recorded_output_artifact':pin(output),'API_write_content_sha256':h(aa),
          'final_artifact_exact_API_write_body':True,
          'native_field_is_not_byte_identical_and_not_silently_normalized':True,
          'decision':'HOLD_NATIVE_BYTE_EQUIVALENCE_EXCEPTION_REQUIRES_SEPARATE_ROOT_REVIEW',
          'model_R_or_action_semantic_approval':False})
    return save('API_NATIVE_BODY_RECORDING_EXCEPTION.json',out)

def main():
    api=rows(OUT/'API67_R_A_FEEDBACK.original.audit.jsonl.gz')
    before=pin(OUT/'EARLY15_READ_LS_R_A_FEEDBACK.original.audit.jsonl.gz')
    sp,n=raw_R_fields(api);rp=old_roots();mp=mismatch(api)
    qa={'status':'PASS_ORIGINAL_SSE_FIELD_RECONSTRUCTION_AND_BOUNDED_OLD_ROOT_AUDIT',
      'API_exchanges':len(api),'exact_RID_plus_visible_action_ID_JSON_native_matches':sum(a['native_same_recorded_response_ID_and_full_nonthought_output_tool_JSON_ID_exact']for a in api),
      'same_RID_with_native_mask_marker_body_exception':sum(not a['native_same_recorded_response_ID_and_full_nonthought_output_tool_JSON_ID_exact']for a in api),'original_R_characters':sum(len(a['original_R'])for a in api),
      'previously_positive_R_approved_unicode_characters_union':sum(a['existing_positive_R_approved_unicode_characters']for a in api),
      'not_previously_positive_R_unicode_characters':sum(a['not_previously_positive_R_unicode_characters']for a in api),
      'not_previously_positive_does_not_mean_semantically_approved':True,
      'original_SSE_R_frames':n,'R_frame_map':sp,'old_roots':rp,'body_exception':mp,
      'early15_packet_unchanged':pin(OUT/'EARLY15_READ_LS_R_A_FEEDBACK.original.audit.jsonl.gz')==before,
      'semantic_approval':False,'new_business_calls':0,'training_started':False,'script_pin':pin(__file__)}
    save('FIELD_AND_CARRIER_QA.json',qa)
    print(json.dumps({k:v for k,v in qa.items()if k not in ['R_frame_map','old_roots','body_exception']},ensure_ascii=False))

if __name__=='__main__':main()
