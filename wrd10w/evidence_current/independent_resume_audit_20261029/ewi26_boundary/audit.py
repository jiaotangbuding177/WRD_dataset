"""Independent CPU-only capture-boundary audit; does not execute old clients."""
import gzip,hashlib,json,zipfile
from collections import Counter
from pathlib import Path
ROOT=Path('D:/skillloop');BASE=ROOT/'output/20261027_wrd_main_v10';OUT=Path(__file__).parent
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pin(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)}
def overlap(a,b):
    assert '\0'not in a+b;s=b+'\0'+a[-len(b):];pi=[0]*len(s)
    for i in range(1,len(s)):
        j=pi[i-1]
        while j and s[i]!=s[j]:j=pi[j-1]
        if s[i]==s[j]:j+=1
        pi[i]=j
    return pi[-1]
def main():
    assert not(OUT/'AUDIT.json').exists()
    mp=BASE/'TRAINING_MANIFEST.json';manifest=load(mp);entries=[]
    for f in manifest['actual_train_files']:
        if'historical_semantic_R_26'not in f['path']:continue
        p=BASE/f['path'];assert digest(p)==f['sha256']
        entries.extend(json.loads(x)for x in gzip.open(p,'rt',encoding='utf-8'))
    assert len(entries)==26 and sum(r['supervised_tokens']for r in entries)==33153
    reports=[];thoughts={};models=Counter()
    for r in entries:
        meta=r['original_record_metadata'];qp=Path(meta['source_request']['path']);sp=Path(meta['source_original_SSE']['path']);rp=qp.parent/'receipt.json';receipt=load(rp)
        assert digest(qp)==meta['source_request']['sha256']==receipt['request_sha256']
        assert digest(sp)==meta['source_original_SSE']['sha256']==receipt['response_sha256']
        q=load(qp);assert [x['role']for x in q['messages']]==['system','user']and not q.get('tools')and q['stream']is True
        payload=json.loads(q['messages'][1]['content']);assert 'action_contract'in payload and 'state'in payload and 'recent_interactions'in payload
        body={'model':q['model'],'messages':q['messages'],'stream':True,'max_tokens':q['max_tokens'],'temperature':.1}
        if q.get('thinking'):body.update(thinking={'type':'enabled'},reasoning_effort=q['reasoning_effort'])
        assert q==body and json.dumps(body,ensure_ascii=False).encode()==qp.read_bytes()
        R=[];C=[];ids=set();returned=set();fin=[];chunks=[];tc=0;done=0;frames=0
        for frame in sp.read_text(encoding='utf-8').replace('\r\n','\n').split('\n\n'):
            data='\n'.join(x[5:].lstrip()for x in frame.splitlines()if x.startswith('data:'))
            if not data:continue
            if data=='[DONE]':done+=1;continue
            v=json.loads(data);frames+=1;assert not v.get('error')
            if v.get('id'):ids.add(v['id'])
            if v.get('model'):returned.add(v['model'])
            for choice in v.get('choices',[]):
                d=choice.get('delta',{});text=d.get('reasoning_content')or'';R.append(text);C.append(d.get('content')or'')
                if text:chunks.append(text)
                tc+=len(d.get('tool_calls')or[])
                if choice.get('finish_reason')is not None:fin.append(choice['finish_reason'])
        R=''.join(R);C=''.join(C);assert R==r['messages'][-1]['reasoning_content']and len(ids)==1 and done==1 and fin==['stop']and tc==0
        assert receipt['status']=='COMPLETE'and receipt['stream_logical_done']is True
        assert meta['current_native_runtime_equivalence_claimed']is False and meta['old_ActionProposal_JSON_output_loss']==0
        assert set(r['supervised_tokens_by_component'])=={'R'}
        action=json.loads(C);assert isinstance(action,dict)and action.get('kind')in ['READ','INSPECT','REPLAY','TRY','UPDATE','FINISH']
        owner=meta['canonical_original_response_owner'];thoughts[owner]=R;models.update(returned)
        reports.append({'owner':owner,'source_id':r['source_ids'][0],'ordinal':qp.parent.name,'request':pin(qp),'SSE':pin(sp),'receipt':pin(rp),
            'request_keys':list(q),'request_model':q['model'],'reasoning_effort':q.get('reasoning_effort'),'max_tokens':q['max_tokens'],
            'returned_models':sorted(returned),'SSE_ids':sorted(ids),'R_chars':len(R),'R_sha256':sha(R.encode()),
            'SSE_JSON_frames':frames,'DONE':done,'finish':fin,'tool_deltas':tc,'R_delta_events':len(chunks),'largest_R_delta_chars':max(map(len,chunks)),
            'content_one_policy_JSON_object':True,'action_kind':action['kind'],'selected_R_tokens':r['supervised_tokens'],'captured_usage':receipt.get('usage')})
    pairs=[]
    for i,x in enumerate(reports):
        for y in reports[i+1:]:
            if x['source_id']!=y['source_id']:continue
            a,b=sorted([x,y],key=lambda v:v['ordinal']);s,t=thoughts[a['owner']],thoughts[b['owner']];n=0
            for c,d in zip(s,t):
                if c!=d:break
                n+=1
            pairs.append({'source':a['source_id'],'earlier':a['ordinal'],'later':b['ordinal'],'common_prefix_chars':n,
                'earlier_full_R_in_later_at':t.find(s),'later_full_R_in_earlier_at':s.find(t),'suffix_prefix_overlap_chars':overlap(s,t),
                'full_prefix_cumulative_pattern':t.startswith(s)})
    assert not any(x['full_prefix_cumulative_pattern']or x['earlier_full_R_in_later_at']>=0 or x['later_full_R_in_earlier_at']>=0 for x in pairs)
    frozen=ROOT/'output/20261015_ewi_teacher_DATA/frozen/source_snapshot_v414_manifest.json';fm=load(frozen);archive=frozen.with_name('source_snapshot_v414.zip')
    assert digest(archive)==fm['zip_sha256'];sourceproof=[];(OUT/'producer_source').mkdir(exist_ok=True)
    with zipfile.ZipFile(archive)as z:
        for rel in ['research/pipelines/skillsloop_ewi_v2/teacher_client.py','research/pipelines/skillsloop_ewi_v2/pipeline.py']:
            original=ROOT/rel;expected=next(x['sha256']for x in fm['pins']if Path(x['path'])==original)
            members=[n for n in z.namelist()if n.replace('\\','/').endswith(rel)or n.replace('\\','/').endswith(rel.removeprefix('research/pipelines/'))]
            assert len(members)==1;blob=z.read(members[0]);assert sha(blob)==expected
            dst=OUT/'producer_source'/Path(rel).name;dst.write_bytes(blob)
            sourceproof.append({'original_frozen_path':str(original),'expected_sha256':expected,'copy':pin(dst),'frozen_archive':pin(archive),'member':members[0],
                'current_original_path_exists':original.is_file(),'current_path_matches_if_present':digest(original)==expected if original.is_file()else None})
    client=(OUT/'producer_source/teacher_client.py').read_text(encoding='utf-8');pipeline=(OUT/'producer_source/pipeline.py').read_text(encoding='utf-8')
    assert all(s in client for s in ['received = bytearray()','buffer = b""','done = False','"stream": True'])
    assert not any(s in client+pipeline for s in ['pendingTool','_consumePending','baseState'])
    assert 'client.ask("EWI_TEACHER", "decision_%03d" % serial'in pipeline
    # Original high-effort calls predate the default-low revision. Retain all
    # four frozen variants, rather than assigning v414 to every old request.
    versions=[]
    for suffix in ['', '_v411', '_v413', '_v414']:
        mp2=frozen.parent/('source_snapshot'+suffix+'_manifest.json');m2=load(mp2);zp=mp2.with_name('source_snapshot'+suffix+'.zip')
        assert digest(zp)==m2['zip_sha256'];pins2=m2.get('pins',m2.get('files'))
        expected=next(x['sha256']for x in pins2 if x['path'].endswith('skillsloop_ewi_v2\\teacher_client.py'))
        with zipfile.ZipFile(zp)as z:
            member=next(n for n in z.namelist()if n.replace('\\','/').endswith('skillsloop_ewi_v2/teacher_client.py'));blob=z.read(member)
        assert sha(blob)==expected;text=blob.decode('utf-8');dst=OUT/'producer_source'/('teacher_client'+(suffix or '_initial')+'.py');dst.write_bytes(blob)
        assert all(s in text for s in ['received = bytearray()','buffer = b""','done = False'])
        assert not any(s in text for s in ['pendingTool','_consumePending','baseState'])
        versions.append({'frozen_manifest':pin(mp2),'archive':pin(zp),'member':member,'source_copy':pin(dst),
            'default_effort':'high'if suffix in ['', '_v411']else'low_configurable','fresh_transport_response_buffer':True,
            'exact_individual_call_execution_SHA_not_in_receipt':'Not inferred merely from compatible request parameters.'})
    cp=BASE/'historical_v6_action_recovery_01/cumulative_reasoning_audit_01';prior=load(cp/'AUDIT.json');contrast=[]
    for name,lo,hi in [('sink-factory.js',41,57),('response-builder.js',8,37),('openai-handler.js',507,565)]:
        p=cp/'collector_source/src'/name;ref=next(x for x in prior['collector_source_pins']if Path(x['portable_copy']['path'])==p)
        assert digest(p)==ref['portable_copy']['sha256'];lines=p.read_text(encoding='utf-8').splitlines();contrast.append({'source':pin(p),'first_line':lo,'last_line':hi,'lines':lines[lo-1:hi]})
    audit={'schema':'wrd-EWI26-independent-response-boundary-audit-v1','reviewed_at':'2026-10-29','status':'PASS_CAPTURE_BOUNDARY_NO_DETECTED_CROSS_DECISION_CUMULATION',
        'scope':'26 currentTRAIN historicalEWI R responses only; no protected4 reviewed, no banks/labels/ACTIVE changed.',
        'current_manifest':pin(mp),'responses':reports,'original_R_chars':sum(x['R_chars']for x in reports),'selected_R_tokens':33153,
        'returned_models':dict(models),'largest_R_delta_chars':max(x['largest_R_delta_chars']for x in reports),
        'same_source_pairwise_exact_prefix_overlap':pairs,'max_common_prefix_chars':max(x['common_prefix_chars']for x in pairs),
        'max_suffix_prefix_overlap_chars':max(x['suffix_prefix_overlap_chars']for x in pairs),'full_prior_R_containment_detected':False,
        'pinned_EWI_snapshot':pin(frozen),'EWI_producer_source':sourceproof,'all_four_historical_client_variants':versions,'old_CodeBuddy_contrast':contrast,
        'actual_effort_counts':dict(Counter(x['reasoning_effort']for x in reports)),
        'source_mechanism':'Fresh independent system/user stream request perdecision; local received/buffer/DONE state; only policy JSON content is parsed. No native tools or pendingTool/baseState continuation in this pinned caller implementation.',
        'do_not_infer_from_ABI_difference_alone':True,'old_bridge_evidence':'The separate old nonstream CodeBuddy sink appends state.reasoning; pending resumes retain baseState; final builder returns the accumulated field. Those concrete files are distinct from the verified EWI caller and captured DeepSeek SSE.',
        'captured_reasoning_identity':'Verbatim explicit perHTTP reasoning_content field, not authenticated hidden cognition.',
        'provider_internal_generation_trace_or_reasoning_faithfulness':'UNKNOWN_NOT_PROVEN','new_semantic_timing_review':'Not provided by an overlap check; existing independent semantic range reviews remain separate.',
        'historical_native_runtime_equivalence_claimed':False,'old_policy_JSON_output_loss':0,'all_original_R_preserved':True,
        'training_started':False,'model_or_Agent_or_business_runs':0,'curation_cost':'UNKNOWN_NOT_ZERO'}
    assert audit['original_R_chars']==396231
    save(OUT/'AUDIT.json',audit)
    save(OUT/'MANIFEST.json',{'status':audit['status'],'files':[pin(p)for p in sorted(OUT.rglob('*'))if p.is_file()and p.name!='MANIFEST.json'],'training_started':False})
    print(json.dumps({'status':audit['status'],'R_chars':audit['original_R_chars'],'pairs':len(pairs),'maxprefix':audit['max_common_prefix_chars'],'maxsuffixprefix':audit['max_suffix_prefix_overlap_chars'],
        'audit_sha256':digest(OUT/'AUDIT.json'),'manifest_sha256':digest(OUT/'MANIFEST.json')}))
if __name__=='__main__':main()
