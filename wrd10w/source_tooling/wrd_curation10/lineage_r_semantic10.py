"""Original-R semantic repair/testing views with real point-state resources.

These are explicitly recontextualized views, not native request equivalents.
Only source-file copying and recorded literal edits reconstruct versions.
CPU checks run the already-inspected stdlib resource test scripts, no Agent.
"""
from pathlib import Path,PurePosixPath
from copy import deepcopy
import ast,collections,gzip,hashlib,json,os,shutil,subprocess,sys
ROOT=Path('D:/skillloop');WORK=ROOT/'output/20261031_wrd_curation10';OUT=WORK/'reasoning_semantic10'
OLD=ROOT/'output/20261027_wrd_main_v10/runtime_preflight/episodes'
API=[json.loads(l)for l in gzip.open(WORK/'reasoning_native10/API67_R_A_FEEDBACK.original.audit.jsonl.gz','rt',encoding='utf-8-sig')]
CORE={'ls','read','write','edit','apply_patch','exec','process'}
def h(x):return hashlib.sha256(x if isinstance(x,bytes)else x.encode()).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):p=Path(p);return{'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def save(n,x):
    p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode());return pin(p)
def gzsave(n,rr):
    p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('wb')as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0)as g:
            for r in rr:g.write((js(r)+'\n').encode())
    return pin(p)
def one(st,co):return next(a for a in API if a['stage']==st and a['call_id'].startswith(co))
def arguments(a):
    call=a['original_response']['tool_calls'][0];args=call['function']['arguments']
    return call,json.loads(args)if isinstance(args,str)else args
def safe_asset(base,virtual):
    rel=PurePosixPath(virtual)
    assert rel.is_absolute()and rel.parts[1]=='workspace'and'..'not in rel.parts
    p=base.joinpath(*rel.parts[1:]);assert p.resolve().is_relative_to(base.resolve())
    return p
def initial(st):
    job=load(OLD/st/'job.json');state={};origins={}
    for r in job['resources']:
        p=Path(r['path']);b=p.read_bytes();assert h(b)==r['sha256']
        v='/workspace/'+r['mount'];state[v]=b
        origins[v]={'kind':'ORIGINAL_COMMISSIONED_INPUT_BEFORE_SESSION','job_pin':pin(OLD/st/'job.json'),'source_pin':pin(p)}
    return state,origins
def point_state(a):
    st=a['stage'];state,origins=initial(st)
    for prev in API:
        if prev['stage']!=st or int(prev['call_id'][:4])>=int(a['call_id'][:4]):continue
        if not prev['original_response'].get('tool_calls'):continue
        call,args=arguments(prev);name=call['function']['name'];dest=args.get('path')
        proof={'kind':'RECORDED_PRIOR_API_ACTION_LITERAL_FILE_VERSION','api_response_pin':prev['source_compatible_API_response'],
          'call_id':call['id'],'native_event_index':prev['native_message_index'],'source_owner_id':prev['owner_id']}
        if name=='write'and dest:
            state[dest]=args['content'].encode();origins[dest]=proof
        elif name=='edit'and dest:
            assert dest in state,'MISSING_RECORDED_EDIT_OLD_VERSION'
            text=state[dest].decode();edits=args.get('edits',[args])
            for e in edits:
                old,new=e['oldText'],e['newText'];assert text.count(old)==1,'LITERAL_EDIT_NOT_EXACTLY_ONE'
                text=text.replace(old,new,1)
            state[dest]=text.encode();origins[dest]={**proof,'kind':'RECORDED_LITERAL_EDIT_APPLIED_TO_EXACT_PRIOR_BYTES'}
        elif st=='B_revision_report_01'and prev['call_id'].startswith('0017'):
            assert name=='exec'and args['command'].startswith('mkdir -p /workspace/outputs/skill')
            for source,target in [('/workspace/inputs/previous_skill/','/workspace/outputs/skill/'),('/workspace/inputs/previous_tests/','/workspace/outputs/tests/')]:
                for v,b in list(state.items()):
                    if v.startswith(source):state[target+v[len(source):]]=b;origins[target+v[len(source):]]={**proof,'kind':'RECORDED_LITERAL_COPY_WITH_ACTUAL_SETUP_HASH_RECEIPT','original_source':v,'source_origin':origins[v]}
            src='/workspace/outputs/tests/test_run_log.json';dst='/workspace/outputs/tests/original_run_log_preserved.json'
            state[dst]=state[src];origins[dst]={**proof,'kind':'RECORDED_COPY_OF_ORIGINAL_LOG','source':src}
    return state,origins

def materialize(folder,state,origins):
    refs=[]
    for virtual,b in sorted(state.items()):
        p=safe_asset(folder,virtual);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        refs.append({'virtual_path':virtual,'actual_asset':pin(p),'provenance':origins[virtual]})
    return refs

def inspect_python(p):
    t=ast.parse(p.read_text(encoding='utf-8'))
    allowed={'argparse','collections','hashlib','json','os','re','subprocess','sys','zipfile','xml','xml.etree.ElementTree','pathlib','copy','validate_pack'}
    imports=[]
    for n in ast.walk(t):
        if isinstance(n,ast.Import):imports.extend(x.name for x in n.names)
        elif isinstance(n,ast.ImportFrom):imports.append(n.module or'')
        elif isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and isinstance(n.func.value,ast.Name):
            assert(n.func.value.id,n.func.attr)not in {('os','system'),('os','popen')}
    assert all(x in allowed or x.split('.')[0]in allowed for x in imports),imports
    return imports
def cpu_checks():
    results=[]
    for label,st,stop in [('bmake_original21','B_make_report_02','0015'),('brevision_original21_and_extra12','B_revision_report_01','0026')]:
        a=one(st,stop);state,origins=point_state(a)
        folder=OUT/'cpu_checks02'/label
        assert not folder.exists(),'PRESERVE_PRIOR_CPU_CHECK'
        refs=materialize(folder,state,origins)
        tests=folder/'workspace/outputs/tests';cli=folder/'workspace/outputs/skill/scripts/validate_pack.py'
        inspected={str(p.relative_to(folder)):inspect_python(p)for p in [cli,*tests.glob('*.py')]}
        names=['run_tests.py']if st=='B_make_report_02'else['run_tests.py','make_fixtures_extra.py','run_tests_extra.py']
        commands=[];env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
        for name in names:
            command=[sys.executable,'-X','utf8',str(tests/name)]
            r=subprocess.run(command,cwd=tests,env=env,capture_output=True,timeout=60)
            p=folder/(name+'.stdout');p.write_bytes(r.stdout+r.stderr)
            commands.append({'argv':command,'returncode':r.returncode,'stdout_stderr_pin':pin(p)})
            assert r.returncode==0,(label,name,r.returncode)
        logs={}
        for name in ['test_run_log.json','extra_test_log.json']:
            if(tests/name).exists():
                d=load(tests/name);assert d['summary']['failed']==0
                logs[name]={'pin':pin(tests/name),'summary':d['summary'],'cli_sha256':d.get('cli_sha256')}
        assert logs['test_run_log.json']['summary']['total']==21
        if st=='B_revision_report_01':assert logs['extra_test_log.json']['summary']['total']==12
        results.append({'label':label,'point_before_original_API_call':a['call_id'],'CLI_pin':pin(cli),
          'inspected_stdlib_only_resource_modules':inspected,'commands':commands,'logs':logs,
          'interpretation':'OFFLINE_CPU_RESOURCE_CHECK_NOT_NATIVE_AGENT_TRIAL_OR_BUSINESS_Q','resources':len(refs)})
    return save('CPU_RESOURCE_CHECKS.json',{'status':'PASS_ORIGINAL21_AND_REVISED21_PLUS12','results':results,
      'original_resource_code_not_rewritten':True,'new_Agent_calls':0,'model_training_started':False,'script':pin(__file__)})

def counterexamples():
    base=OUT/'cpu_checks02';inputs=base/'brevision_original21_and_extra12/workspace/inputs/independent'
    old=base/'bmake_original21/workspace/outputs/skill/scripts/validate_pack.py'
    new=base/'brevision_original21_and_extra12/workspace/outputs/skill/scripts/validate_pack.py'
    cases=[('legal_temporal','legal_ledger.json','legal_draft.json',1,0,'fact_type_conflict',None),
      ('nested_not_list','nested_refs_not_list.json','valid_single_draft.json',0,1,None,'evidence_refs_not_list'),
      ('nested_not_object','nested_refs_non_object_item.json','valid_single_draft.json',0,1,None,'evidence_refs_item_not_object')]
    out=[];folder=OUT/'counterexamples';folder.mkdir(exist_ok=True)
    for name,ledger,draft,oldexit,newexit,oldfail,newfail in cases:
        pair=[]
        for version,cli,expected,failid in [('old',old,oldexit,oldfail),('revised',new,newexit,newfail)]:
            rp=folder/(name+'_'+version+'.json')
            cmd=[sys.executable,'-X','utf8',str(cli),'validate','--ledger',str(inputs/ledger),'--draft',str(inputs/draft),'--sources',str(inputs/'legal_sources.json'),'--report',str(rp)]
            r=subprocess.run(cmd,capture_output=True,timeout=30,env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8'))
            assert r.returncode==expected,(name,version,r.returncode)
            d=load(rp);ids=[x['id']for x in d['failures']]
            if failid:assert failid in ids
            else:assert not ids
            pair.append({'version':version,'CLI':pin(cli),'command':cmd,'returncode':r.returncode,'report':pin(rp),'failure_ids':ids,'verdict':d['verdict']})
        out.append({'case':name,'same_input_pins':[pin(inputs/ledger),pin(inputs/draft),pin(inputs/'legal_sources.json')],'observations':pair})
    save('OLD_VS_REVISED_REAL_COUNTEREXAMPLES.json',{'status':'PASS_THREE_REAL_LOCAL_BEFORE_AFTER_CASES','pairs':out,
      'scope':'Offline CPU reproduction of already-provided synthetic counterexamples, not new business native/Q','new_Agent_calls':0,'training_started':False})

def before_read16(a,state,origins):
    call,args=arguments(a);assert call['function']['name']=='read'
    feedback=a['actual_native_tool_feedback'][0]['message'];blocks=feedback['content']
    t='\n'.join(b.get('text','')for b in blocks)if isinstance(blocks,list)else blocks
    actual=load(OUT/'cpu_checks02/bmake_original21/workspace/outputs/tests/reports/B1a_length_exactly_at_limit_report.json')
    assert json.loads(t)==actual
    state[args['path']]=t.encode()
    origins[args['path']]={'kind':'PRIOR_ARTIFACT_CREATED_BY_RECORDED_API15_EXEC_BEFORE_TARGET16',
      'creator_response_pin':one(a['stage'],'0015')['source_compatible_API_response'],
      'exact_version_recovered_from_subsequent_read_and_independent_CPU_JSON_EQUALITY':True,
      'same_call_read_feedback_is_credit_only_not_prompt_observation':True}

def excerpt(a):
    r=a['original_R'];start=0;end=len(r);negative=[]
    if a['stage']=='B_revision_report_01'and a['call_id'].startswith('0017'):
        start=r.index(' - Defect1');end=r.index('\n Implementation:')
    if a['stage']=='B_revision_report_01'and a['call_id'].startswith('0024'):
        # Local new-case design is the teaching state. The original21-history
        # sentence remains in the raw original field, outside this continuous
        # excerpt; we do not infer a full old-fixture semantic reading from SHA.
        start=r.index('Now build the supplementary tests:')
        for bad in [' to prove genericity']:
            x=r.index(bad);negative.append((x,x+len(bad),'Varying dates is a counterexample probe, not a proof of genericity.'))
        x=r.index('Then run. Then build');negative.append((x,len(r),'Future delivery progress is not substantive reasoning or an observed outcome.'))
        x=r.index('Now write make_fixtures_extra.py');y=r.index('\n\nThen run.',x)
        negative.append((x,y,'Procedural transition and runner bookkeeping are kept but not reasoning loss.'))
    if a['stage']=='B_make_report_02'and a['call_id'].startswith('0014'):
        x=r.index('Implement straightforwardly.');negative.append((x,len(r),'Procedural transition retained as context, not reasoning credit.'))
    if a['stage']=='B_make_report_02'and a['call_id'].startswith('0016'):
        for bad in ['Let me quickly inspect one or two reports to be thorough, then check for the dead code cleanup in make_fixtures.py (edit it, rerun to confirm identical results). Since editing the test generator is a resource revision, rerun tests after edit and keep the chain.',
          'Let me clean the dead code, and also double-check a couple of report files.']:
            x=r.index(bad);negative.append((x,x+len(bad),'Procedural next-step transition retained, not substantive R credit.'))
    selected=r[start:end];zero=[]
    for lo,hi,reason in negative:
        lo=max(lo,start);hi=min(hi,end)
        if lo<hi:zero.append({'start':lo-start,'end':hi-start,'original_field_start':lo,'original_field_end':hi,'text_sha256':h(r[lo:hi]),'reason':reason})
    cuts=sorted({0,len(selected),*(v for q in zero for v in [q['start'],q['end']])})
    good=[]
    for lo,hi in zip(cuts,cuts[1:]):
        if not any(q['start']<=lo<hi<=q['end']for q in zero):
            if selected[lo:hi]:good.append({'message_index':2,'field':'reasoning_content','start':lo,'end':hi,'text_sha256':h(selected[lo:hi])})
    return selected,{'start':start,'end':end,'text_sha256':h(selected)},good,zero

def build():
    rr=[];ledger=[];job=load(OLD/'B_revision_report_01/job.json')
    originals=[('B_revision_report_01','0017'),('B_revision_report_01','0024'),('B_revision_report_01','0025'),('B_make_report_02','0014'),('B_make_report_02','0016')]
    for st,co in originals:
        a=one(st,co);state,origins=point_state(a)
        if st=='B_make_report_02'and co=='0016':before_read16(a,state,origins)
        ident='recontext10-'+st+'-'+co;refs=materialize(OUT/'functional_states'/ident,state,origins)
        excerpts,region,good,bad=excerpt(a)
        assert not a['existing_positive_R_approved_unicode_ranges'],'ORIGINAL_R_ALREADY_SUPERVISED'
        if st=='B_revision_report_01'and co=='0017':
            selected=['/workspace/inputs/independent/actual_repair_feedback.json','/workspace/inputs/previous_skill/scripts/validate_pack.py','/workspace/inputs/previous_tests/run_tests.py',
              '/workspace/inputs/previous_tests/make_fixtures.py',
              '/workspace/inputs/independent/legal_sources.json','/workspace/inputs/independent/legal_ledger.json','/workspace/inputs/independent/legal_draft.json']
            goal='Analyze the two observed validator defects and plan a bounded revision with reproducible checks. Preserve original resources and logs; do not treat structural tests as business quality.'
        elif st=='B_revision_report_01':
            selected=['/workspace/inputs/independent/actual_repair_feedback.json','/workspace/outputs/skill/scripts/validate_pack.py']
            if co=='0024':selected+=['/workspace/outputs/tests/run_tests.py']
            if co=='0025':selected.append('/workspace/outputs/tests/make_fixtures_extra.py')
            goal='Expand normal, boundary and invalid-shape tests for the locally revised validator using its public CLI; preserve the original21 expectations. Do not hardcode a specific case into the validator.'
        else:
            selected=['/workspace/outputs/skill/scripts/validate_pack.py','/workspace/outputs/tests/make_fixtures.py']
            if co=='0016':selected.append('/workspace/outputs/tests/run_tests.py')
            goal='Build or inspect exact assertions for the existing local CLI normal/boundary/error fixtures. Test passes establish only the covered checks; retain source/assumption boundaries.'
        observations=[]
        prior='0023'if st=='B_revision_report_01'and co in {'0024','0025'}else'0015'if st=='B_make_report_02'and co=='0016'else None
        if prior:
            prev=one(st,prior)
            observations=[{'original_response_pin':prev['source_compatible_API_response'],
              'actual_past_tool_feedback':[f['message']for f in prev['actual_native_tool_feedback']],
              'observed_before_target':True}]
        payload={'task':goal,'state_type':'NEW_CURATOR_DECLARED_COMPLETE_LOCAL_FUNCTIONAL_STATE',
          'actual_files':[{'path':v,'sha256':h(b),'bytes':len(b)}for v,b in sorted(state.items())],
          'visible_file_contents':[{'path':v,'sha256':h(state[v]),'content':state[v].decode('utf-8-sig')}for v in selected],
          'past_observations':observations,
          'available_file_entities_are_bundled':True,
          'only_local_state_not_the_original_full_native_history':True}
        original=deepcopy(a['original_response']);original['reasoning_content']=excerpts
        # Ordinary visible progress remains verbatim but not positive E loss.
        system=next(m['content']for m in a['compatible_request_messages_original']if m['role']=='system')
        if isinstance(system,list):system='\n'.join(b['text']for b in system)
        c={'id':ident,'owner_id':ident,'source_ids':a['source_ids'],'source_group_id':'v10_native_group_a6a1c69fa6400f282a9a','split':'train','stage':'B',
          'bank':'recontextualized_compat_R_process10','source_admission':'ADMIT','training_admitted':False,
          'root_main_admission':False,'requires_external_root_admission':True,
          'messages':[{'role':'system','content':system},{'role':'user','content':js(payload)},original],
          'tools':[t for t in a['compatible_request_tools_original']if t['function']['name']in CORE],
          'supervision_message_indices':[2],'message_loss_mask':[0,0,1],
          'approved_components':['A'],'approved_field_ranges':good,'loss_multiplier':0.25,
          'allow_reviewed_completion_prefix':False,'is_original_native_request_identical':False,
          'actual_native_tool_dispatch':False,'recorded_original_native_action_executed':True,
          'teacher_original_R_supervised':True,'original_R_provenance':{'kind':'RECONTEXTUALIZED_ORIGINAL_COMPAT_R',
            'original_episode_id':a['episode_id'],'original_response_id':a['response_id'],
            'source_response_pin':a['source_compatible_API_response'],'source_original_R_sha256':a['original_R_sha256'],
            'original_R_field':'reasoning_content','continuous_excerpt':region,
            'original_R_not_rewritten':True,'hidden_upstream_private_CoT_claimed':False},
          'original_recorded_action_owner':a['owner_id'],'canonical_response_owner':a['source_compatible_API_response']['sha256'],
          'original_native_session_id':a['native_session_id'],'original_native_message_index':a['native_message_index'],
          'original_A_byte_identity':a['native_same_recorded_response_ID_and_full_nonthought_output_tool_JSON_ID_exact'],
          'A_original_action_arguments_identical':True,
          'A_original_action_arguments_identical_to':'RECORDED_COMPATIBLE_API_ARGUMENTS_VERBATIM',
          'A_original_native_record_arguments_identical':a['native_same_recorded_response_ID_and_full_nonthought_output_tool_JSON_ID_exact'],
          'A_original_API_arguments_sha256':h(original['tool_calls'][0]['function']['arguments']),
          'API_native_body_exception_for_separate_root_review':not a['native_same_recorded_response_ID_and_full_nonthought_output_tool_JSON_ID_exact'],
          'source_API_original_request_preserved':a['source_compatible_API_request'],
          'tool_schema_provenance':{'path':a['source_compatible_API_request']['path'],'sha256':a['source_compatible_API_request']['sha256']},
          'student_view':'RECONTEXTUALIZED_ORIGINAL_COMPAT_R_CONTINUOUS_EXCERPT_AND_RECORDED_ACTION_CORE7',
          'functional_state_resource_manifest':refs,
          'target_R_zero_unicode_ranges':bad,'future_feedback_in_model_input':False,
          'actual_feedback_for_credit_only':a['actual_native_tool_feedback'],
          'full_pipeline_or_skill_utility_approved':False,'is_full_autonomous_execution_demonstration':False,
          'new_authored_R_tokens':0,'new_business_calls':0,'training_started':False}
        rr.append(c)
        ledger.append({'id':ident,'source_episode':a['episode_id'],'call_id':a['call_id'],'R_owner_response_sha256':a['source_compatible_API_response']['sha256'],
          'R_continuous_excerpt':region,'R_characters':len(excerpts),'R_zero_spans':bad,
          'A_owner':a['owner_id'],'A_original_call_ID':original['tool_calls'][0]['id'],
          'proposed_components':['EXACT_ORIGINAL_COMPAT_R_EXCERPT','RECORDED_A_WITH_SEPARATE_BYTE_EXCEPTION_REVIEW_IF_ANY'],
          'state_asset_count':len(refs),'new_state_not_original_native':True,'root_approval_pending':True})
    cp=gzsave('CANDIDATES.proposed.raw.jsonl.gz',rr)
    save('COMPONENT_CREDIT_AND_OWNER_LEDGER.json',{'rows':ledger,'candidate_pin':cp,'new_semantic_approval_here':'PROPOSED_PENDING_ROOT',
      'A_current595_call_ID_dedup_required_by_root':True,'R_existing_credit_union_checked_zero_for_selected5':True,
      'source_group_is_previously_seen_not_new_independent_experience':True})
    print(json.dumps({'candidates':len(rr),'R_chars':sum(x['R_characters']for x in ledger),'output':cp},ensure_ascii=False))

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    if '--cpu'in sys.argv:cpu_checks()
    if '--counterexamples'in sys.argv:counterexamples()
    if '--build'in sys.argv:build()
