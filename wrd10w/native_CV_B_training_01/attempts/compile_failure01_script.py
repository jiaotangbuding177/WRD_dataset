"""Recover a real native CV-maker process into precise reviewed data views.

CPU-only data curation; no model, Agent, old executor, Docker or resource rerun.
All original reasoning/actions/past remain; wrong/unreviewed targets get0loss.
"""
from __future__ import annotations
from array import array
from collections import Counter
from copy import deepcopy
import gzip,hashlib,importlib.util,json,os,sys
from pathlib import Path
os.environ['USE_TORCH']='0';os.environ['USE_TF']='0'
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/20261027_wrd_main_v10'
NATIVE=BASE/'native_records/B_phase2_cv_01'
EP=BASE/'runtime_preflight/episodes/B_phase2_cv_01'
OUT=BASE/'native_CV_B_training_01'
CORE={'ls','read','write','edit','apply_patch','exec','process'}

def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(Path(p).read_bytes())
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8-sig')as f:
        for line in f:
            if line.strip():yield json.loads(line)
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def dump(p,values):
    p.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(p,'wt',encoding='utf-8',newline='\n')as f:
        for v in values:f.write(js(v)+'\n')
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)}
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def binary(p,kind,values):
    a=array(kind,values)
    if sys.byteorder!='little':a.byteswap()
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(a.tobytes());return {'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}

def recover_all():
    old=list(rows(NATIVE/'raw_recovery/provider_responses.original.jsonl.gz'))
    extra=load(NATIVE/'raw_recovery/NONSTOP_0019_ORIGINAL_FIELDS.json');folder=EP/'api_audit'/extra['call_id'];receipt=load(folder/'receipt.json')
    assert receipt['status']=='COMPLETE'and receipt['http_status']==200 and extra['DONE_frame']and extra['finish_reason']=='length'
    p=folder/'request.raw.json';sse=Path(receipt['response_path']);request=load(p)
    assert digest(p)==receipt['request_sha256']and digest(sse)==receipt['response_sha256']==extra['response_sha256']
    thoughts=[];content=[];finish=None;done=False
    for block in sse.read_text(encoding='utf-8').replace('\r\n','\n').split('\n\n'):
        payload='\n'.join(line[5:].lstrip()for line in block.splitlines()if line.startswith('data:'))
        if not payload:continue
        if payload=='[DONE]':done=True;continue
        v=json.loads(payload)
        for c in v.get('choices',[]):
            d=c.get('delta',{});thoughts.append(d.get('reasoning_content')or'');content.append(d.get('content')or'')
            if c.get('finish_reason')is not None:finish=c['finish_reason']
    assert done and finish=='length'and ''.join(thoughts)==extra['reasoning_content']and ''.join(content)==extra['content']
    old.append({'call_id':extra['call_id'],'message':{'role':'assistant','reasoning_content':extra['reasoning_content'],'content':extra['content']},
        'provider_meta':{'finish_reason':'length','transport_status':'COMPLETE_200_DONE','not_missing_capture':True},
        'response_layer':'FIXED_NATIVE_COMPATIBLE_API_RETURN','independent_upstream_provider_generation_is_not_assumed':True,
        'request':str(p),'request_sha256':digest(p),'response':str(sse),'response_sha256':digest(sse),
        'native_messages':request['messages'],'native_tools':request['tools'],'original_reasoning_chars':len(extra['reasoning_content'])})
    old.sort(key=lambda r:r['call_id']);assert len(old)==27 and sum(r['original_reasoning_chars']for r in old)==22806
    for r in old:assert digest(Path(r['request']))==r['request_sha256']and digest(Path(r['response']))==r['response_sha256']
    return old

def make_review(raw):
    decisions=[];ranges=[];zero=[]
    # Scope-correct original tool actions: reads, probes, a verified fixture
    # generator, running/diagnosing actual tests, and the actual fixture repair.
    # Known defective whole resource writes, malformed delegate calls, private
    # semantic eligibility judgements and completion claims are never inherited.
    action_ok={1:'read the authorized maker brief',2:'read the single authorized source',3:'inspect available local tools and actual PDF header',
        4:'extract the actual maker PDF per page with pymupdf',11:'syntax/normal-path extraction probe for this actual file, not general filter correctness',
        14:'read installed font files after subset failure',15:'actual successful small CJK fixture generator, tested round-trip by independent resource review',
        17:'run existing tests and record their real failure, not a test-pass target',18:'inspect the failing claims file against the documented checker API',
        22:'repair three fixture wrappers to the already documented bare-array API and rerun; no resource source code changed'}
    full_R={1,3,4,8,11,12,13,14,15,16,18,20,23,24}
    for row in raw:
        n=int(row['call_id'][:4]);s=row['message'].get('reasoning_content','');allowed=[];denied=[]
        if n in full_R and s:allowed=[(0,len(s),'BOUNDED_ORIGINAL_PLANNING_DIAGNOSIS_OR_LOCAL_OBSERVATION')]
        if n==5:
            allowed=[(0,len(s),'SOURCE_GROUNDED_FACTS_BOUNDED_SEMANTIC_HYPOTHESES_AND_RESOURCE_TEST_DESIGN')]
            lo=s.index('Hainan University is a211');hi=s.index('- Experience:')
            denied.append((lo,hi,'UNVERIFIED_EXTERNAL_SCHOOL_TIER_AND_HARD_QUALIFICATION_CONCLUSION'))
            lo=s.index('Decision: conditional recommend interview');hi=s.index('For the deliverable of this Maker run:')
            denied.append((lo,hi,'UNPROVEN_FINAL_RECOMMENDATION_AND_HARD_REQUIREMENT_SATISFACTION_NOT_GOLD'))
        if n==6:
            allowed=[(s.index('Now identify the repeated operations'),len(s),'RESOURCE_DESIGN_WITH_EXPLICIT_INPUTS_AND_BOUNDED_TEST_PLANS')]
            lo=s.index('Also strip resume-tracker watermark lines?');hi=s.index('Actually to keep checker consistent')
            denied.append((lo,hi,'KNOWN_OVERBROAD_LONG_ALNUM_DELETION_CAN_REMOVE_LEGITIMATE_QUALIFICATION_TEXT'))
        if n==7:
            lo=s.index('Let me verify syntax');allowed=[(lo,len(s),'VERIFY_SYNTAX_RATHER_THAN_UNSUPPORTED_VALID_PYTHON_CONCLUSION')]
            denied.append((0,lo,'KNOWN_WRONG_QUOTING_VALIDITY_ASSERTION_AND_UNRESOLVED_COUNTS'))
        if n==19:
            hi=s.index('Inconsistency:');allowed=[(0,hi,'CORRECT_WRAPPED_FIXTURE_VS_BARE_ARRAY_API_DIAGNOSIS_ONLY')]
            denied.append((hi,len(s),'FALSE_RESOURCE_INCONSISTENCY_AND_UNNECESSARY_API_CHANGE_PRESCRIPTION'))
        if n==22:
            lo=s.index('Let me retry with the proper structure');allowed=[(lo,len(s),'RETRY_CORRECT_PUBLIC_EXEC_SHAPE_AFTER_BAD_NESTING')]
            denied.append((0,lo,'UNSUPPORTED_DELEGATE_TOOL_BLAME_AND_INACCURATE_RECOUNT_OF_ACTUAL_WRONG_ARGUMENTS'))
        # Apply exact zero overlays, preserving the original whole reasoning.
        for lo,hi,why in denied:
            next_allowed=[]
            for a,b,reason in allowed:
                if b<=lo or hi<=a:next_allowed.append((a,b,reason));continue
                if a<lo:next_allowed.append((a,lo,reason))
                if hi<b:next_allowed.append((hi,b,reason))
            allowed=next_allowed
            zero.append({'call_id':row['call_id'],'start':lo,'end':hi,'text':s[lo:hi],'text_sha256':sha(s[lo:hi].encode()),'reason':why,'mask':0})
        for lo,hi,why in allowed:
            assert 0<=lo<hi<=len(s)
            ranges.append({'call_id':row['call_id'],'field':'reasoning_content','start':lo,'end':hi,'text':s[lo:hi],
                'text_sha256':sha(s[lo:hi].encode()),'mask':1,'speech_act_or_scope':why,'loss_multiplier':.25})
        decisions.append({'call_id':row['call_id'],'original_R_characters':len(s),'approved_R_characters':sum(b-a for a,b,_ in allowed),
            'original_action_approved':n in action_ok,'action_credit':action_ok.get(n,'ZERO_LOSS_NOT_WHOLE_RESOURCE_OR_FINAL_OUTPUT_APPROVED'),
            'all_original_visible_content_D_E_loss':0,'source_request_sha256':row['request_sha256'],'source_response_sha256':row['response_sha256'],
            'transport_finish':row['provider_meta'].get('finish_reason'),'original_past_unchanged':True})
    return {'schema_version':'wrd-native-CV-B-exact-range-process-review-v1','status':'AUTHOR_AI_SILVER_CANDIDATE_PENDING_INDEPENDENT_ROOT',
        'ranges':ranges,'explicit_zero_ranges':zero,'responses':decisions,'whole_original_R_preserved':22806,
        'stop_tool_R_characters':22447,'transport_complete_length_R_characters':359,'semantic_gold_or_human_annotation':False,
        'known_resource_defects':['24+alnum line filter deletes legitimate CV text','image-only PDF exits0 with empty extraction instead of explicit OCR/error signal',
            'claims item/quote/page malformed types can traceback without declared JSON diagnostics'],
        'resource_credit':'original22 normal tests and independent8authentic PDFs20pages are valid scoped evidence; not whole-skill success',
        'call22_credit':'test fixture wrapper/JSON contract repair only; terminal skill code unchanged',
        'actual_original_R_target_author':'ORIGINAL_NATIVE_TEACHER','new_annotations_author':'Codex AI silver','curation_cost':'UNKNOWN_NOT_ZERO',
        'root_main_admission':False,'training_started':False,'new_model_calls':0}

def main():
    assert not OUT.exists();OUT.mkdir()
    raw=recover_all();review=make_review(raw)
    dump(OUT/'original_provider_responses.all27.jsonl.gz',raw);save(OUT/'REVIEW.json',review)
    job=load(EP/'job.json');assert job['source_ids']==['conv_2b8fd8fdd8bc']
    scope=next(r for r in rows(BASE/'clean_inputs/source_scope.metadata.jsonl.gz')if r['source_id']==job['source_ids'][0]);assert scope['status']=='TRAIN'
    for field in ['source_allowlist','resource_ancestry']:
        assert digest(Path(job[field+'_receipt']))==job[field+'_sha256']
    save(OUT/'SOURCE_CAUSAL_RECEIPTS.json',{'source_ids':job['source_ids'],'scope':scope,'job':pin(EP/'job.json'),
        'source_allowlist':pin(Path(job['source_allowlist_receipt'])),'resource_ancestry':pin(Path(job['resource_ancestry_receipt'])),
        'raw26':pin(NATIVE/'raw_recovery/provider_responses.original.jsonl.gz'),'original19':pin(NATIVE/'raw_recovery/NONSTOP_0019_ORIGINAL_FIELDS.json'),
        'actual_versions':pin(NATIVE/'file_versions_01/VERSION_GRAPH.json'),'actual_fixture_versions':pin(NATIVE/'fixture_and_exec_versions_01/VERSION_SUPPLEMENT.json'),
        'independent_resource_credit_metadata_only':pin(BASE/'runtime_preflight/quality/B_PHASE2_CV_RESOURCE_AUDIT_01/RESOURCE_REVIEW.json'),
        'later_eight_PDF_outcomes_not_added_to_original_inputs':True,'current_CV_revision_never_read':True,'new_native_or_model_calls':0,'training_started':False})
    shared=module(ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py','CV_independent_causal_compiler')
    masking=module(ROOT/'research/data_prep/wrd_main_v10/compile_main.py','CV_exact_mask_helper')
    compiler=shared.CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
    decisions={r['call_id']:r for r in review['responses']};rr={}
    for r in review['ranges']:rr.setdefault(r['call_id'],[]).append(r)
    core_candidates=[];full_candidates=[];compiled_core=[];compiled_long=[];compiled_full=[];stats=[];allbins=[];owners=[]
    for row in raw:
        decision=decisions[row['call_id']];selected=rr.get(row['call_id'],[])
        if not selected and not decision['original_action_approved']:continue
        messages=deepcopy(row['native_messages'])+[deepcopy(row['message'])];idx=len(messages)-1;textprojections=[]
        for i,m in enumerate(messages):
            if isinstance(m.get('content'),list):
                assert all(x.get('type')=='text'and isinstance(x.get('text'),str)for x in m['content'])
                old=m['content'];m['content']='\n'.join(x['text']for x in old)
                textprojections.append({'message_index':i,'original_blocks_sha256':sha(js(old).encode()),'rule':'JOIN_COMPLETE_TEXT_BLOCKS_WITH_NEWLINE'})
            if m.get('role')=='assistant':m.setdefault('reasoning_content','')
        group='v10_native_group_'+sha(js(sorted(job['source_ids'])).encode())[:20]
        record={'schema_version':'wrd-native-CV-B-range-reviewed-v1','id':'native_B_phase2_cv_01_'+row['call_id'],
            'bank':'native_CV_B_training_01','stage':'B_make_CV_extract_evidence_process','split':'train','source_ids':job['source_ids'],'source_group_id':group,
            'source_admission':'ADMIT','training_admitted':True,'root_main_admission':False,'annotation_provenance':'ACTUAL_NATIVE_R_AND_SCOPED_ACTION_WITH_AI_RANGE_REVIEW',
            'rationale_provenance':'ORIGINAL_NATIVE_TEACHER_VERBATIM','messages':messages,'tools':[t for t in row['native_tools']if t['function']['name']in CORE],
            'message_loss_mask':[0]*idx+[1],'supervision_message_indices':[idx],'approved_components':['A']if decision['original_action_approved']else[],
            'approved_field_ranges':[{'message_index':idx,'field':'reasoning_content','start':r['start'],'end':r['end'],'text_sha256':r['text_sha256']}for r in selected],
            'loss_multiplier':.25,'tool_schema_provenance':{'path':row['request'],'sha256':row['request_sha256']},
            'original_past_mask0':True,'past_recovered_R_never_injected':True,'full_target_original_R_unchanged':True,
            'student_view':'CORE7_CATALOG_PROJECTION_FULL_ACTUAL_SYSTEM_AND_PAST','runtime_still_has_53_tools':True,'complete_text_block_projection':textprojections,
            'canonical_response_owner':'native_B_phase2_cv_01_'+row['call_id'],'canonical_original_tool_call_ids':[x['id']for x in row['message'].get('tool_calls',[])],
            'core_full_and_any_future_recontext_views_mutually_exclusive':True,'actual_request_sha256':row['request_sha256'],'actual_response_sha256':row['response_sha256'],
            'actual_provider_finish':row['provider_meta'].get('finish_reason'),'original_visible_content_all_zero':True,
            'is_full_autonomous_execution_demonstration':False,'original226':False,'holdout12':False,'protected_sources_visible_prefix':False,'training_started':False}
        full={**record,'id':record['id']+':full53','tools':deepcopy(row['native_tools']),'student_view':'FULL_ACTUAL53_TOOLS_AND_PAST_ORIGINAL_R','default_active':False}
        core_candidates.append(record);full_candidates.append(full);owners.append({'owner':record['canonical_response_owner'],'original_tool_call_ids':record['canonical_original_tool_call_ids'],
            'views':[record['id'],full['id']],'positive_A':decision['original_action_approved'],'mutually_exclusive':True})
        for label,item in [('core7',record),('full53',full)]:
            if decision['original_action_approved']:
                from jsonschema import Draft202012Validator
                registry={t['function']['name']:t['function']for t in item['tools']}
                for call in item['messages'][-1].get('tool_calls',[]):Draft202012Validator(registry[call['function']['name']]['parameters']).validate(json.loads(call['function']['arguments']))
            result=compiler.compile_messages(item['messages'],item['tools'],{idx:{'id':record['canonical_response_owner']+':m'+str(idx),'mechanical_usable':True}},independent=False)
            masking.select_reviewed_spans(compiler,item['messages'],item['tools'],result,item['approved_components'],item['approved_field_ranges'])
            if row['provider_meta'].get('finish_reason')=='length':
                # The HTTP is complete but no stop/EOS occurred. Keep only the
                # exact token prefix through approved R; never fabricate a stop.
                upto=max(b for a,b,c,w in result['supervision_spans']);result['full_template_tokens_before_prefix']=result['total_tokens']
                result['input_ids']=result['input_ids'][:upto];result['total_tokens']=upto
                result['view']='ORIGINAL_LENGTH_LIMITED_RESPONSE_EXACT_REVIEWED_TOKEN_PREFIX_NO_EOS'
                result['no_artificial_think_close_stop_or_EOS_in_used_prefix']=True
            result['supervision_spans']=[[a,b,c,w*.25]for a,b,c,w in result['supervision_spans']]
            for t in result['targets']:t['owned_supervision_spans']=[[a,b,c,w*.25]for a,b,c,w in t['owned_supervision_spans']]
            result['input_ids_sha256_u32le']=shared.int_sha(result['input_ids']);result['supervision_spans_sha256']=sha(js(result['supervision_spans']).encode())
            kwargs=dict(compiler.tokenizers['primary_14b'].special_tokens_map);kwargs['enable_thinking']=False
            rendered=compiler.plain_compiled.render(messages=item['messages'],tools=item['tools'],documents=None,add_generation_prompt=False,**kwargs)
            p=compiler.tokenizers['primary_14b'](rendered,add_special_tokens=False,return_offsets_mapping=True)
            c=compiler.tokenizers['control_8b'](rendered,add_special_tokens=False,return_offsets_mapping=True);assert p==c
            assert p['input_ids'][:result['total_tokens']]==result['input_ids']
            # A direct independent char-interval construction, separate from
            # masking.select_reviewed_spans, verifies every positive token.
            start=result['targets'][0]['rendered_assistant_span'][0]+len('<|im_start|>assistant\n<think>\n')
            field=item['messages'][-1].get('reasoning_content','');assert rendered[start:start+len(field)]==field
            intervals=[(start+r['start'],start+r['end'])for r in selected]
            if decision['original_action_approved']:
                a=start+len(field)+len('\n</think>\n\n')+len(item['messages'][-1].get('content')or'')
                b=result['targets'][0]['rendered_assistant_span'][1]-len('<|im_end|>\n');intervals.append((a,b))
            expected={i for i,(a,b)in enumerate(p['offset_mapping'][:result['total_tokens']])if a<b and any(lo<=a and b<=hi for lo,hi in intervals)}
            actual={i for a,b,cl,w in result['supervision_spans']for i in range(a,b)};assert expected==actual,(row['call_id'],label,len(expected),len(actual))
            labels=[-100]*result['total_tokens'];weights=[0.0]*result['total_tokens']
            for i in actual:labels[i]=result['input_ids'][i];weights[i]=.25
            assert len(actual)==result['supervised_tokens']
            if result['total_tokens']>131072:raise AssertionError('do_not_silently_truncate')
            bucket='32k'if result['total_tokens']<=32768 else'64k'if result['total_tokens']<=65536 else'128k'
            for suffix,kind,values in [('input_ids.u32le.bin','I',result['input_ids']),('labels.i64le.bin','q',labels),('weights.f32le.bin','f',weights)]:
                allbins.append(binary(OUT/'arrays'/label/row['call_id'][:4]/suffix,kind,values))
            result.update({'id':item['id'],'schema_version':item['schema_version'],'bank':item['bank'],'stage':item['stage'],'split':'train',
                'source_ids':item['source_ids'],'source_group_id':item['source_group_id'],'messages':item['messages'],'tools':item['tools'],
                'original_record_metadata':{k:v for k,v in item.items()if k not in {'messages','tools'}},'root_main_admission':False,
                'conditional_profile':bucket if label=='full53'or bucket!='32k'else None,'training_started':False})
            (compiled_core if label=='core7'and bucket=='32k'else compiled_long if label=='core7'else compiled_full).append(result)
            stats.append({'call_id':row['call_id'],'profile':label,'bucket':bucket,'input_tokens':result['total_tokens'],
                'supervised_tokens':result['supervised_tokens'],'components':result['supervised_tokens_by_component'],
                'both_tokenizers_all_ids_and_offsets':'PASS','independent_all_position_mask':'PASS','original_R_SHA256':sha(field.encode()),
                'past_indices_mask0':list(range(idx)),'HTTP_complete_length_limited':row['provider_meta'].get('finish_reason')=='length'})
    dump(OUT/'candidate.core7.jsonl.gz',core_candidates);dump(OUT/'candidate.full53.jsonl.gz',full_candidates)
    dump(OUT/'compiled.core32.jsonl.gz',compiled_core);dump(OUT/'compiled.core_long.conditional.jsonl.gz',compiled_long);dump(OUT/'compiled.full53.conditional.jsonl.gz',compiled_full)
    save(OUT/'EXPOSURE_OWNERS.json',{'owners':owners,'profiles_not_extra_independent_tasks':True,'root_main_admission':False})
    counts=Counter();components=Counter()
    for r in stats:
        if r['profile']=='core7':counts[r['bucket']+'_sequences']+=1;counts['sequences']+=1;counts['input_tokens']+=r['input_tokens'];counts['supervised_tokens']+=r['supervised_tokens'];components.update(r['components'])
    save(OUT/'COMPILATION_AND_DIRECT_QA.json',{'status':'ACTUAL_ARRAYS_DUAL_TOKENIZER_EXACT_MASK_PASS_PENDING_SECOND_AI_ROOT','core_all_buckets':dict(counts),
        'core_components':dict(components),'original_R_characters_reviewed':22806,'approved_original_R_characters':sum(r['end']-r['start']for r in review['ranges']),
        'reviewed_R_range_count':len(review['ranges']),'original_complete_stop_tool_responses':26,'HTTP_COMPLETE_length_response':1,
        'core32_default_candidate_sequences':len(compiled_core),'core_long_conditional_sequences':len(compiled_long),'full53_conditional_sequences':len(compiled_full),
        'profiles_same_canonical_owners_mutually_exclusive':True,'binary_files':allbins,'rows':stats,
        'new_native_calls':0,'new_model_calls':0,'weights_loaded':False,'training_started':False,'curation_cost':'UNKNOWN_NOT_ZERO'})
    print(js({'core':dict(counts),'components':dict(components),'Rranges':len(review['ranges']),'binary_files':len(allbins)}))
if __name__=='__main__':main()
