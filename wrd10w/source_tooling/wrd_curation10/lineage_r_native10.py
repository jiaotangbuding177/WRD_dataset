"""Restore original compatible-API R/A and actual native feedback, no admission.

All original fields are retained. Exact source/event/response/action and run
conditions are required; source/body identity is not semantic correctness.
"""
from pathlib import Path
import collections,gzip,hashlib,importlib.util,json,re,sys

ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation10/reasoning_native10'
MAIN=ROOT/'output/20261027_wrd_main_v10'
BASE='01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42'
STAGES={'A_screen_narrative_01','B_make_report_02','B_revision_report_01'}
CORE={'read','ls','write','edit','apply_patch','exec','process'}

def h(b):return hashlib.sha256(b if isinstance(b,bytes)else b.encode()).hexdigest()
def canon(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True)
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
def module(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s)
    old=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:s.loader.exec_module(m)
    finally:sys.dont_write_bytecode=old
    return m
def text(m):
    c=m.get('content',[])
    return c if isinstance(c,str)else''.join(b.get('text','')for b in c if isinstance(b,dict)and b.get('type')=='text')
def native_calls(m):
    c=m.get('content',[])
    return[b for b in c if isinstance(b,dict)and b.get('type')=='toolCall']if isinstance(c,list)else[]
def norm(m,ids=True):
    cc=[]
    for c in m.get('tool_calls',[])or[]:
        f=c['function'];a=f.get('arguments',{})
        try:a=json.loads(a)if isinstance(a,str)else a
        except ValueError:a={'UNPARSED':a}
        cc.append({'name':f['name'],'arguments':a,**({'id':c['id']}if ids else{})})
    for c in native_calls(m):
        a=c.get('arguments',{})
        try:a=json.loads(a)if isinstance(a,str)else a
        except ValueError:a={'UNPARSED':a}
        cc.append({'name':c['name'],'arguments':a,**({'id':c['id']}if ids else{})})
    return{'content':text(m).replace('\r\n','\n'),'tool_calls':cc}
def merge_intervals(rr):
    result=[]
    for a,b in sorted(rr):
        if result and a<=result[-1][1]:result[-1][1]=max(result[-1][1],b)
        else:result.append([a,b])
    return result
def complement(length,rr):
    out=[];start=0
    for a,b in merge_intervals(rr):
        if a>start:out.append([start,a])
        start=b
    if start<length:out.append([start,length])
    return out

def positive_R_ranges(records,api):
    byhash=collections.defaultdict(list)
    for a in api:
        if a['original_R']:byhash[h(a['original_R'])].append(a)
    mapped=[];unmapped=[]
    for r in records:
        if not r['supervised_tokens_by_component'].get('R'):continue
        md=r['original_record_metadata'];finger=canon(md)
        for t in r['targets']:
            if not any(s[2]=='R'for s in t.get('owned_supervision_spans',[])):continue
            i=t['message_index'];field=r['messages'][i].get('reasoning_content','')or''
            candidates=byhash.get(h(field),[])
            explicit=[a for a in candidates if a['call_id']in finger or a['source_compatible_API_response']['sha256']in finger]
            a=explicit[0]if len(explicit)==1 else candidates[0]if len(candidates)==1 else None
            if a is None:
                unmapped.append({'view_id':r['id'],'message_index':i,'R_field_sha256':h(field),'R_field_characters':len(field),
                  'reason':'NOT_SAME_FULL_R_FIELD_OF_THIS67_COHORT_OR_AMBIGUOUS_CANONICAL_OWNER'})
                continue
            allowed=md.get('approved_components')or[]
            intervals=[[0,len(field)]]if 'R'in allowed else[[v['start'],v['end']]for v in md.get('approved_field_ranges',[])if v['message_index']==i and v['field']=='reasoning_content']
            assert intervals,'POSITIVE_R_WITHOUT_EXACT_CHARACTER_CREDIT_MAP'
            for v in md.get('approved_field_ranges',[]):
                if v['message_index']==i and v['field']=='reasoning_content':assert h(field[v['start']:v['end']])==v['text_sha256']
            mapped.append({'view_id':r['id'],'target_message_index':i,'call_id':a['call_id'],'episode_id':a['episode_id'],
              'original_compatible_response_id':a['response_id'],'R_field_sha256':h(field),
              'canonical_match':'PINNED_CALL_OR_RESPONSE_SHA_AND_FULL_FIELD'if len(explicit)==1 else'UNIQUE_EXACT_FULL_ORIGINAL_R_FIELD_SHA',
              'approved_unicode_ranges':merge_intervals(intervals),
              'positive_R_tokens_in_existing_view_target':sum(s[1]-s[0]for s in t['owned_supervision_spans']if s[2]=='R')})
    for a in api:
        matches=[m for m in mapped if m['call_id']==a['call_id']and m['episode_id']==a['episode_id']]
        credit=merge_intervals([v for m in matches for v in m['approved_unicode_ranges']])
        a['existing_positive_R_credit_views']=matches
        a['existing_positive_R_approved_unicode_ranges']=credit
        a['existing_positive_R_approved_unicode_characters']=sum(b-a for a,b in credit)
        a['not_previously_positive_R_unicode_ranges']=complement(len(a['original_R']),credit)
        a['not_previously_positive_R_unicode_characters']=len(a['original_R'])-sum(b-a for a,b in credit)
    return mapped,unmapped

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert h((MAIN/'TRAINING_MANIFEST.json').read_bytes())==BASE
    idx=load(ROOT/'output/20261031_wrd_curation10/identity/CONTENT_REVIEW_INDEX.json')
    wanted=[e for e in idx['episodes']if e['episode_id'].startswith('native_')]
    assert len(wanted)==5
    reserve=load(ROOT/'output/20261031_wrd_curation10/parent_inputs/reservation.json')
    protected=load(ROOT/'research/plans/20261027_wrd_main_v10/CLEAN_ACTOR_INVENTORY.json')
    forbidden={s for s,v in protected['source_id_to_existing_split'].items()if v in {'dev','test'}}
    evaluation=ROOT/'benchmark/enterprise_input_closed_v11_20261012/contracts/evaluation.jsonl'
    forbidden|={json.loads(l)['session_id']for l in evaluation.read_text(encoding='utf-8-sig').splitlines()if l.strip()}
    forbidden|=set(re.findall(r'conv_[0-9a-f]{12}',canon(load(ROOT/'output/20261026_ablation_v2/holdout_registry.json'))))
    forbidden.add('conv_34b56ae9c535')
    m=module('read_only_compatible_R_recover',ROOT/'research/data_prep/wrd_main_v10/extract_native_main.py')
    api=[];early=[];ctxmap={};allscopes=[]
    for e in wanted:
        assert not forbidden.intersection(e['source_ids'])
        assert pin(e['context']['path'])['sha256']==e['context']['sha256']
        ctx=rows(e['context']['path'])[0];ctxmap[e['episode_id']]=ctx
        targets=rows(e['target_index']['path']);owners={t['source_message_index']:t for t in targets}
        allscopes.append({'episode_id':e['episode_id'],'source_ids':e['source_ids'],'direct_226_H12_static_new_reserved_hit':False,
          'context_pin':e['context'],'source_resource_scope_pin':e['source_and_resource_metadata'],
          'full_prefix_resource_ancestry_not_approved_here':True})
        if e.get('stage')not in STAGES:continue
        base=Path(ctx['source_original_path']).parent.parent
        execution=load(base/'execution.json')
        assert execution['image']=='sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2'
        assert execution['model']=='glm-5.3-flash'and execution['backend']=='native'and not execution['custom_agent_loop']
        native_by_rid=collections.defaultdict(list)
        for i,n in enumerate(ctx['messages']):
            if n.get('responseId'):native_by_rid[n['responseId']].append(i)
        for folder in sorted((base/'api_audit').iterdir()):
            if not folder.is_dir():continue
            msg,meta,reqp,respp=m.recover(folder);receipt=load(folder/'receipt.json');request=load(reqp)
            rid=receipt['response_id'];ni=native_by_rid[rid];assert len(ni)==1
            i=ni[0];native=ctx['messages'][i]
            exact=norm(msg)==norm(native)
            tools={c['function']['name']for c in request.get('tools',[])if c.get('type')=='function'}
            assert set(c['function']['name']for c in msg.get('tool_calls',[]))<=tools
            feedback=[]
            callids={c['id']for c in msg.get('tool_calls',[])}
            for j,q in enumerate(ctx['messages'][i+1:],i+1):
                if q.get('role')=='assistant':break
                if q.get('role')=='toolResult'and q.get('toolCallId')in callids:
                    feedback.append({'message_index':j,'event_line':ctx['source_event_lines'][j],
                      'message':q,'message_sha256_sorted':h(canon(q)),
                      'future_feedback_not_in_target_input':True})
            owner=owners.get(i)
            row={'episode_id':e['episode_id'],'stage':e['stage'],'call_id':folder.name,'response_id':rid,
              'owner_id':owner['owner_id']if owner else None,'source_ids':e['source_ids'],
              'native_session_id':ctx['native_session_id'],'native_message_index':i,
              'native_event_line':ctx['source_event_lines'][i],'native_message_SHA_sorted':h(canon(native)),
              'source_native':ctx['source_native'],'source_compatible_API_request':pin(reqp),
              'source_compatible_API_response':pin(respp),'original_receipt_pin':pin(folder/'receipt.json'),
              'recorded_execution_condition':{k:execution[k]for k in ['image','openclaw_version','model','max_tokens','timeout_seconds','backend','custom_agent_loop']},
              'native_same_recorded_response_ID_and_full_nonthought_output_tool_JSON_ID_exact':exact,
              'event_crosswalk_status':'EXACT_RID_VISIBLE_OUTPUT_AND_ORIGINAL_RUN_CONDITION'if exact else'HOLD_SAME_RID_BUT_NATIVE_ARGUMENT_BODY_DIFFERENCE',
              'API_nonthought_message_sha256':h(canon(norm(msg))),
              'native_nonthought_message_sha256':h(canon(norm(native))),
              'request_and_response_unrewritten':not receipt['request_body_rewritten']and not receipt['response_body_rewritten'],
              'compatible_request_messages_original':request['messages'],
              'compatible_request_tools_original':request.get('tools',[]),
              'original_R_field':'reasoning_content','original_R':msg.get('reasoning_content',''),
              'original_R_sha256':h(msg.get('reasoning_content','')),'original_response':msg,
              'actual_native_tool_feedback':feedback,
              'visible_public_text':msg.get('content',''),
              'private_upstream_CoT_provenance_not_inferred_from_compatible_R_field':True,
              'bridge_hidden_upstream_full_provider_request_not_captured':True,
              'full_original_resource_scope_requires_root_review':True,
              'training_admitted':False,'positive_loss':0,'training_started':False}
            api.append(row)
    assert len(api)==67
    man=load(MAIN/'TRAINING_MANIFEST.json');records=[r for f in man['actual_train_files']for r in rows(MAIN/f['path'])]
    mapped,unmapped=positive_R_ranges(records,api)
    for a in api:
        r=a['original_R'];n=len(r)
        # These are triage buckets, not positive semantic labels.
        a['R_triage_class']='EMPTY_R_FIELD'if not r else'LONG_ANALYSIS_REQUIRES_CLAIM_LEVEL_REVIEW'if n>1500 else'SHORT_LOCAL_PLAN_OR_TRANSITION_REQUIRES_REVIEW'
        if a['native_same_recorded_response_ID_and_full_nonthought_output_tool_JSON_ID_exact']and int(a['call_id'][:4])<=6 and a['original_response'].get('tool_calls')and all(c['function']['name']in {'read','ls'}for c in a['original_response']['tool_calls']):
            a['early_read_ls_review_packet']=True;early.append(a)
        else:a['early_read_ls_review_packet']=False
        if r:
            p=OUT/'original_R'/a['stage']/(a['call_id']+'.txt');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(r.encode())
            a['original_R_text_pin']=pin(p)
    assert len(early)==15
    rawpin=gzsave('API67_R_A_FEEDBACK.original.audit.jsonl.gz',api)
    earlypin=gzsave('EARLY15_READ_LS_R_A_FEEDBACK.original.audit.jsonl.gz',early)
    metadata=[]
    for a in api:
        metadata.append({k:v for k,v in a.items()if k not in ['original_R','original_response','compatible_request_messages_original','compatible_request_tools_original','actual_native_tool_feedback','visible_public_text']})
    save('API67_R_DEDUP_AND_UNSUPERVISED_INDEX.metadata.json',metadata)
    save('CURRENT595_R_COHORT_MATCHES.metadata.json',{'exact_current_R_matches':mapped,'noncohort_or_ambiguous_current_R_targets':unmapped,
      'scope':'Only this67-cohort R is de-duplicated; unmatching existing R is retained in its original bank.',
      'unicode_credit_ranges_are_not_token_counts':True})
    earlysmall=[]
    for a in early:
        earlysmall.append({'episode_id':a['episode_id'],'stage':a['stage'],'call_id':a['call_id'],'response_id':a['response_id'],
          'owner_id':a['owner_id'],'native_message_index':a['native_message_index'],
          'R_characters':len(a['original_R']),'R':a['original_R'],
          'already_positive_R_chars':a['existing_positive_R_approved_unicode_characters'],
          'original_tool_calls':a['original_response'].get('tool_calls',[]),
          'actual_tool_feedback_metadata':[{'message_index':q['message_index'],'event_line':q['event_line'],
            'toolCallId':q['message'].get('toolCallId'),'isError':q['message'].get('isError'),
            'text_characters':len(text(q['message'])),'message_sha256_sorted':q['message_sha256_sorted']}for q in a['actual_native_tool_feedback']],
          'semantic_admission':False})
    save('EARLY15_READ_LS_SEMANTIC_REVIEW.json',earlysmall)
    summary=[]
    for st in sorted(STAGES):
        aa=[a for a in api if a['stage']==st]
        summary.append({'stage':st,'API_exchanges':len(aa),'original_R_characters':sum(len(a['original_R'])for a in aa),
          'existing_approved_unicode_characters_union':sum(a['existing_positive_R_approved_unicode_characters']for a in aa),
          'not_previously_positive_unicode_characters':sum(a['not_previously_positive_R_unicode_characters']for a in aa),
          'early_read_ls_packets':sum(a['early_read_ls_review_packet']for a in aa),
          'early_read_ls_nonempty_original_R':sum(a['early_read_ls_review_packet']and bool(a['original_R'])for a in aa),
          'early_read_ls_R_characters':sum(len(a['original_R'])for a in aa if a['early_read_ls_review_packet'])})
    save('RECOVERY_QA.json',{'status':'PASS_ORIGINAL_FIELD_RECOVERY_AND_CURRENT595_EXACT_R_DEDUP_NOT_SEMANTIC_ADMISSION',
      'baseline_manifest_sha256':BASE,'new_reserved_pin':pin(ROOT/'output/20261031_wrd_curation10/parent_inputs/reservation.json'),
      'scope_checks':allscopes,'stages':summary,'original_R_total_characters':sum(len(a['original_R'])for a in api),
      'API67_exchanges_are_not67_independent_provider_generations':True,
      'original_R_is_recorded_compatible_API_field_not_guaranteed_private_upstream_CoT':True,
      'public_visible_content_kept_separate':True,'empty_native_thinking_does_not_prove_absent_compatible_R':True,
      'raw_packet_pin':rawpin,'early_packet_pin':earlypin,'new_positive_R_tokens_admitted_here':0,
      'new_business_calls':0,'training_started':False,'script_pin':pin(__file__)})
    print(json.dumps({'stages':summary,'raw':rawpin,'early':earlypin},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
