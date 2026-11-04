"""Independent source-asof/semantic Q audit; preserves original silver labels.

Reads only frozen local records. No Agent/model/business/test execution.
"""
from pathlib import Path
from datetime import date
import gzip,hashlib,json,re,sys
import pymupdf
sys.dont_write_bytecode=True
ROOT=Path('D:/skillloop');BASE=ROOT/'output/20261027_wrd_main_v10'
EP=BASE/'runtime_preflight/episodes/C_phase2_cv_review_01'
WS=EP/'workspace';OUT=Path(__file__).parent
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def segment(text,needle):
    start=text.index(needle);return {'start':start,'end':start+len(needle),'text':needle,'text_sha256_utf8':sha(needle.encode())}
def ptr_value(d,ptr):
    for k in ptr.strip('/').split('/'):
        k=k.replace('~1','/').replace('~0','~');d=d[int(k)] if isinstance(d,list) else d[k]
    return d
def qptr(case,arm,dimension,item):
    key=next(k for k in Q['cases'][case]['arms'][arm] if k.startswith(dimension+'_'))
    ptr=f'/cases/{case}/arms/{arm}/{key}/items/{item}'
    return {'file':'blind_quality.json','json_pointer':ptr,'original_value':ptr_value(Q,ptr)}
def original(ptr,file='decision.json'):
    d=DEC if file=='decision.json' else FEEDBACK
    return {'file':file,'json_pointer':ptr,'original_value':ptr_value(d,ptr)}

def main():
    global Q,DEC,FEEDBACK
    assert not(OUT/'PEER.json').exists()
    paths=[WS/f'outputs/{n}.json' for n in ['blind_quality','decision','feedback']]
    Q,DEC,FEEDBACK=[load(p) for p in paths]
    protocol=load(WS/'inputs/review/source_only_quality_protocol.json')
    tasks={c:load(WS/f'inputs/review/tasks/{c}.json') for c in ['E1','E2']}
    outputs={}
    for c in ['E1','E2']:
        for arm in 'AB':
            p=WS/f'inputs/review/outputs/{c}_{arm}.txt'
            originalp=BASE/f'runtime_preflight/jobs/C_phase2_cv_review_01_preparation/inputs/outputs/{c}_{arm}.txt'
            assert p.read_bytes()==originalp.read_bytes();outputs[c+arm]=p.read_text(encoding='utf-8')
            paths.extend([p,originalp])
    request=EP/'api_audit/0001_5d8c04ba1b7c439a9d33081ffb0c5059/request.raw.json'
    assert pin(request)['sha256']=='50f060c189c26f8d6f36613891a2682f10bf1a62d264b59246248a323d7c8f0d'
    req=load(request);system=req['messages'][0]['content'];visible_date=segment(system,'Current date: 2026-10-27')
    assert (visible_date['start'],visible_date['end'])==(11837,11861)
    assert '[Tue 2026-10-27 06:41 UTC]' in req['messages'][1]['content']
    nativeaudit=BASE/'runtime_preflight/quality/C_PHASE2_CV_REVIEW_AUDIT_02/AUDIT.json'
    audit=load(nativeaudit);timeline=audit['full_action_timeline'];obsproof=[]
    for event in timeline:
        ob=event['actual_observation'];p=ROOT/ob['request_path'];assert pin(p)['sha256']==ob['request_sha256']
        d=load(p);message=d['messages'][ob['message_index']]
        obj=BASE/'native_records/C_phase2_cv_review_01/file_versions_01/objects'/ob['object']
        assert pin(obj)['sha256']==ob['object'] and load(obj)==message
        assert message['role']=='tool' and message['tool_call_id']==event['tool_call_id']
        obsproof.append({'actor_call_id':event['call_id'],'tool':event['tool'],'command':event.get('command',''),'path':event.get('path',''),
            'first_received_request':pin(p),'message_index':ob['message_index'],'actual_tool_message_CAS':pin(obj),'tool_call_id':event['tool_call_id']})
        paths.extend([p,obj])
    # Independent raw ledger read binds the one actual write to the frozen Q.
    ledger=BASE/'native_records/C_phase2_cv_review_01/raw_recovery/provider_responses.original.jsonl.gz'
    rows={x['call_id']:x for x in map(json.loads,gzip.open(ledger,'rt',encoding='utf-8'))}
    writer=rows['0014_8a42d6aff4d4471bb51b7fbffd815c7f']
    call=next(c for c in writer['message']['tool_calls'] if c['function']['name']=='write')
    args=json.loads(call['function']['arguments']);assert args['path']=='/workspace/outputs/blind_quality.json'
    assert args['content'].encode()==paths[0].read_bytes()
    assert 'Successfully wrote' in rows['0015_d5ceb61d31084e36837b5aea3ae03170']['native_messages'][29]['content']
    assert 'valid JSON' in rows['0016_3ef6cf3e03d8457b82c6568cb7d6a51c']['native_messages'][31]['content']
    # Costs/resources were first requested after successful write and JSON parse.
    assert timeline[13]['path']=='/workspace/outputs/blind_quality.json'
    assert 'phase2_arm_costs' in timeline[15]['command']
    prewrite=rows['0014_8a42d6aff4d4471bb51b7fbffd815c7f']['native_messages']
    wang_obs=prewrite[19]['content'];assert '停车资源数据看板' in wang_obs and '2021.07-2023.07' in wang_obs and 'Vue3、TypeScript、ECharts' in wang_obs
    wang_received={'request':pin(Path(writer['request'])),'message_index':19,'role':'tool','known_before_quality_write':True,
        'date_segment':segment(wang_obs,'2021.07-2023.07'),'project_segment':segment(wang_obs,'停车资源数据看板'),'stack_segment':segment(wang_obs,'Vue3、TypeScript、ECharts')}
    # Exact authentic PDFs and own text extraction; text only, no layout/render claim.
    pdfpages={};pdfstats=[]
    for case in tasks.values():
        for ref in case['material_alias_map']:
            p=WS/ref['available_native_path'].removeprefix('/workspace/')
            assert pin(p)['sha256']==ref['sha256'] and p.stat().st_size==ref['actual_bytes']
            doc=pymupdf.open(p);texts=[page.get_text() for page in doc];pdfpages[p.stem]=texts
            pdfstats.append({**pin(p),'pages':len(doc),'extracted_text_characters':sum(map(len,texts)),'own_extraction_text_sha256':sha('\f'.join(texts).encode())});paths.append(p)
    assert len(pdfstats)==7
    def pdfquote(stem,page,needle):
        p=WS/f'inputs/task/materials/{stem}.pdf';return {'file':pin(p),'page':page,'extraction':'PyMuPDF '+str(pymupdf.VersionBind),'extracted_page_text_sha256':sha(pdfpages[stem][page-1].encode()),**segment(pdfpages[stem][page-1],needle)}
    e2jd=tasks['E2']['current_original_request']['content'];optional='有跨端开发经验（小程序/快应用/H5）者优先，熟悉Uniapp/Taro框架更佳'
    assert optional in e2jd and '具备WebSocket通信协议开发经验' in e2jd
    arithmetic=[]
    for case in ['E1','E2']:
        for arm in 'AB':
            d=Q['cases'][case]['arms'][arm];dims=[];total=0
            for dim in ['D1','D2','D3','D4','D5']:
                key=next(k for k in d if k.startswith(dim+'_'));v=d[key];n=len(v['items']);s=sum(x['score'] for x in v['items']);w=protocol['dimensions'][dim]['weight'];total+=100*w*s/n
                dims.append({'dimension':dim,'item_sum':s,'n_items':n,'reported_dimension_score':v['score'],'matches':s==v['score']})
            arithmetic.append({'case':case,'arm':arm,'dimensions':dims,'raw_items_weighted_total_100':total,'reported_total_100':d['weighted_total_100'],'is_new_correct_quality_score':False})
    a=next(x for x in arithmetic if x['case']=='E2' and x['arm']=='A');assert a['raw_items_weighted_total_100']==88.75 and a['reported_total_100']==91.25
    costpath=WS/'inputs/review/phase2_arm_costs.json';cost=load(costpath);usage=cost['case_arm_map_and_actual_cost']
    s=usage['E2']['A']['actual_usage'];n=usage['E2']['B']['actual_usage']
    assert s['known_total_tokens']==739012 and n['known_total_tokens']==360358 and n['unknown_usage_calls']==1
    issues=[]
    def issue(id,status,reason,targets,evidence,limits):issues.append({'id':id,'decision':status,'reason':reason,'original_targets':targets,'actual_source_evidence':evidence,'scope_limits':limits,'positive_training_credit':False})
    future=[qptr('E2',arm,dim,index) for arm in 'AB' for dim,index in [('D1',3),('D2',3)]]
    future +=[original('/current_version_concrete_defects/2', 'feedback.json')]
    issue('Q_DATE_ASOF','WITHDRAW_FALSE_FUTURE_DATE_CLAIMS_AND_DESCENDANTS','2026-02/03/04 precede the model-visible 2026-10-27. These are not future endpoints. The same alleged defect is charged in both D1 and D2 and propagated to F3.',future,
        [{'actual_first_request':pin(request),'message_index':0,'role':'system',**visible_date},pdfquote('96f97ee12f59ed80',1,'2023-12\u00a0～\u00a02026-04'),pdfquote('8ad152dae625eda9',1,'2023.09 - 2026.03'),pdfquote('6ce6df1590fed877',2,'2025.07-2026.02')],
        'Do not infer future defects from the filename, historical source date, or later audit clock. Remaining self-claimed tenure discrepancies require separate checks; no automatic full credit.')
    issue('Q_OPTIONAL_HARDENING','WITHDRAW_ALL_THREE_CROSS_PLATFORM_AND_UNIAPP_TARO_HARD_GATE','The actual JD calls cross-platform experience preferred and Uniapp/Taro better. No evidence of all three platforms is not a hard failure. WebSocket is explicitly required and remains independently evaluable.',
        [qptr('E2','A','D2',0),qptr('E2','A','D2',3),qptr('E2','B','D2',3)],
        [{'file':pin(WS/'inputs/review/tasks/E2.json'),'json_pointer':'/current_original_request/content',**segment(e2jd,optional)},{'file':pin(WS/'inputs/review/tasks/E2.json'),'json_pointer':'/current_original_request/content',**segment(e2jd,'具备WebSocket通信协议开发经验')}],
        'Cross-platform can still be a job-related preferred differentiator. Evidence absence, actual inexperience and mandatory failure must remain distinct; no hiring decision certified.')
    issue('Q_WANG_CONCURRENT_PROJECT','HOLD_UNSUPPORTED_DEFINITIVE_FRONTEND_TENURE_REDUCTION','Both arm outputs and Q assert actual frontend tenure ~3 years by excluding the operations-title period. The same already-received PDF P2 lists a 2021.07–2023.07 frontend dashboard project. Job title alone cannot erase this project.',
        [qptr('E2','A','D1',2),qptr('E2','B','D1',1),{'file':'E2_A.txt',**segment(outputs['E2A'],'2021.07-2023.06 为法院信息化运维岗，实际前端开发约 3 年')},{'file':'E2_B.txt',**segment(outputs['E2B'],'王丹（前端约3年+，自称5年）')}],
        [pdfquote('9c667aab99eaada6',2,'2021.07-2023.06\n某法院信息化支持岗'),pdfquote('9c667aab99eaada6',2,'2021.07-2023.07\n停车资源数据看板\n技术栈：Vue3、TypeScript、ECharts'),wang_received],
        'Concurrent project does not prove full-time frontend employment or validate five years. Preserve both job and project and ask clarification about duration/intensity; no replacement tenure total is assigned.')
    issue('Q_APPROX_INTERVAL','WITHDRAW_INTERNAL_CONTRADICTION_REASON_HOLD_ABSOLUTE_SUM','Approximately2 years and approximately1.5–2 years overlap. Their wording alone does not establish an internal contradiction. Reviewer also claims listed spans total under2 years without fixing the asof for the ongoing job.',
        [qptr('E1','A','D1',3),original('/quality_vs_cost_reading/E1'),original('/current_version_concrete_defects/2','feedback.json')],
        [pdfquote('3f8a1c51032c2b97',1,'2025.8-至今'),pdfquote('3f8a1c51032c2b97',1,'2024.5-2024.9'),pdfquote('3f8a1c51032c2b97',1,'2023.2-2023.12'),{'file':'E1_A.txt',**segment(outputs['E1A'],'累计约 2 年')},{'file':'E1_A.txt',**segment(outputs['E1A'],'实际约 1.5–2 年')}],
        'If ongoing employment is evaluated at 2026-10, month-difference arithmetic gives10+4+14=28 months (endpoint conventions change the number); below2 years is not supported under that assumption. Resume snapshot date/continued employment are not authenticated, so this is a diagnostic conditional calculation, not a new exact tenure gold. Both arms need the same asof policy.')
    issue('Q_ARITHMETIC','WITHDRAW_REPORTED_E2_A_SCORE_AND_Q_DEPENDENT_TIE','E2A D2 items sum2.5, stored3. Raw-item arithmetic yields88.75, not91.25. Underlying semantic items also require correction;88.75 is not a replacement correct Q.',
        [{'file':'blind_quality.json','json_pointer':'/cases/E2/arms/A','arithmetic_diagnostic':a},original('/quality_vs_cost_reading/E2'),original('/frozen_blind_quality/scores/E2')],[],
        'Preserve original score and failure. Do not simply substitute arithmetic score or train equal-quality conclusion.')
    issue('Q_COST_BOUND_DIRECTION','WITHDRAW_FLOOR_AND_2_05_TO_2_85_PREMIUM_CONCLUSION','E2 S cost complete739012; N cost unknown subtotal360358. N>=360358 gives S/N<=2.050771732554848, not >=2.05. No exact E2 premium is established.',
        [original('/costs_actual/E2/readable_ratios'),original('/recommendation/basis/1')],[{'file':pin(costpath),'json_pointer':'/case_arm_map_and_actual_cost/E2','S_complete':s,'N_partial':n,'S_over_N_upper_bound':739012/360358}],
        'E1 measured token ratio remains468104/164470≈2.846744. Token is not cash. E2 interrupted wall time is not attributable wholly to the skill. Cost of qualified skill remains undefined with zero qualified skills.')
    issue('Q_DUTIES_FULL_MATRIX','HOLD_DERIVED_COVERAGE_DEDUCTION_NO_MANDATORY_MATRIX','The original E1 task requests an interview recommendation, not a full duty matrix. Mapping material duties can be relevant; a deduction requires identifying a material missing ability or resulting decision weakness instead of requiring every JD line by format.',
        [qptr('E1','A','D2',3),original('/current_version_concrete_defects/3','feedback.json')],[{'file':pin(WS/'inputs/review/tasks/E1.json'),'json_pointer':'/current_original_request/content','request':'是否可推荐面试'},{'file':pin(WS/'inputs/review/source_only_quality_protocol.json'),'json_pointer':'/source_based_criteria/no_forced_output'}],
        'This is a hold for criterion justification, not proof every omitted duty is irrelevant or score should be full. Original reviewer did classify the deduction as derived_quality.')
    issue('Q_METHOD_CAUSALITY','HOLD_CAUSAL_BENEFIT_WORDING_RETAIN_LOCAL_OUTPUT_OBSERVATION','Both skill outputs visibly supply page references and both baselines do not. The two limited-blind development cases do not isolate a causal skill contribution or establish semantic hiring gain.',
        [original('/quality_vs_cost_reading/skill_genuine_distinct_benefit'),original('/recommendation/basis/0')],[{'four_original_output_pins':[pin(WS/f'inputs/review/outputs/{c}_{arm}.txt') for c in ['E1','E2'] for arm in 'AB']}],
        'Actual full native skill reads/version match establish availability and consumption, not benefit; literal/page correctness is separate from meaning and hiring correctness. Output method cues prevent complete blinding.')
    save('SOURCE_ASOF_EVIDENCE.json',{'first_actual_request':pin(request),'visible_date':visible_date,'visible_date_role':'system','not_from_later_metadata':True,
        'all_actual_tool_receipts_and_request_boundaries_verified':obsproof,'blind_write_raw_ledger':pin(ledger),'actual_blind_write':{'call_id':writer['call_id'],'tool_call_id':call['id'],'content_exact_frozen_quality':True},
        'write_ack_then_parse_then_first_cost_read':'PASS','Wang_project_already_delivered_before_blind_write':wang_received,'PDF_source_pins_and_own_text_extraction':pdfstats,
        'PDF_full_text_read_scope':'All7 full textual extractions read; no independent visual rendering/layout or hiring-expert verification claimed.'})
    save('FINDINGS.json',{'schema':'wrd-independent-CV-Q-causal-silver-audit-v1','issues':issues,'original_labels_preserved':True,'any_new_Q_numeric_rescore':False,'any_positive_training_admission':False})
    save('ARITHMETIC_ONLY.json',{'raw_item_calculations':arithmetic,'E2_cost_ratio':{'S':739012,'N_known_subtotal':360358,'N_unknown_usage_calls':1,'direction':'S/N <= S/N_known','upper_bound':739012/360358,'complete_ratio':'UNKNOWN'},'semantic_score_gold':False})
    receipt={'status':'HOLD_ORIGINAL_Q_TOTALS_AND_DEPENDENT_DECISION_AS_POSITIVE_TRAINING_LABELS','reviewer':'Independent Codex AI, not human/hiring-expert gold',
        'original_Q_decision_feedback':[pin(x) for x in paths[:3]],'scope':'Actual system/user date, full functional tasks/protocol, all4 unchanged output texts, all7 authentic PDF textual extractions; D1/D2 disputed points, decision and feedback. No blanket D3-D5 or every literal/page quote approval.',
        'source_asof_and_actual_past_receipts':'PASS','blind_write_success_before_phase2_read':'PASS_LIMITED_BLIND_ONLY','findings':pin(OUT/'FINDINGS.json'),
        'independently_confirmed_concrete_problems':[x['id'] for x in issues],'new_Wang_project_conflict_not_in_previous_native_errata':True,
        'reasonable_exploration_not_discarded':'Full original R/actions/feedback/code and proposed review criteria remain preserved. Valid asof gathering, source reading, read-before-write sequence, uncertainty statements and explicitly bounded revision proposals may be separately selected only after precise semantic review.',
        'local_strengths_not_promoted_to_gold':['Actual source and arm reads before quality write','Quality write succeeded and parse confirmed before cost/resource access','Both skill outputs have page references','Q expressly admits limited blinding and uncalibrated AI silver','Same-version duplicated SKILL paragraphs can be a local concrete defect; not measured business harm'],
        'admission_scope':'No new positive Q/D/F/R labels produced; root may review precise valid spans separately. Do not train current REVISE recommendation as whole gold because invalid Q and false premises feed it. A later correctly motivated revision proposal remains possible.',
        'no_full_pipeline_or_student_effect_evidence_added':True,'originals_modified':False,'new_Agent_model_business_runs':0,'training_started':False,'curation_cost':'UNKNOWN_NOT_ZERO'}
    save('PEER.json',receipt)
    paths.extend([request,nativeaudit,ledger,costpath,WS/'inputs/review/source_only_quality_protocol.json',*[WS/f'inputs/review/tasks/{c}.json' for c in ['E1','E2']]])
    save('MANIFEST.json',{'status':receipt['status'],'new_audit_files':[pin(OUT/x) for x in ['PEER.json','FINDINGS.json','SOURCE_ASOF_EVIDENCE.json','ARITHMETIC_ONLY.json','audit.py']],
        'read_sources':[pin(x) for x in sorted(set(paths),key=str)],'original_files_unchanged':True,'training_started':False})
    print(json.dumps({'status':receipt['status'],'issues':len(issues),'peer_sha256':pin(OUT/'PEER.json')['sha256'],'manifest_sha256':pin(OUT/'MANIFEST.json')['sha256']}))

if __name__=='__main__':main()
