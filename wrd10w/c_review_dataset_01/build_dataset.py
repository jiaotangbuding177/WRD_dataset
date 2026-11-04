"""Offline, bounded C-review dataset preparation; no native or model calls.

The unchanged shared extractor/token compiler supply their declared projections.
Every candidate remains outside root admission until an independent root review.
"""
from pathlib import Path
from copy import deepcopy
from collections import defaultdict
import gzip, hashlib, importlib.util, json, shutil

ROOT=Path('D:/skillloop')
BASE=ROOT/'output/20261027_wrd_main_v10'
OUT=BASE/'c_review_dataset_01'
RT=BASE/'runtime_preflight'
EP=RT/'episodes/C_review_report_01'
QDIR=RT/'quality/FIRST_CHAIN_INDEPENDENT_REVIEW'
SOURCE_IDS=['conv_246b5e915810','conv_27abfa260f9c','conv_41874c950938','conv_d1ef29d65e7a']
def js(x): return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def sha(x): return hashlib.sha256(x).hexdigest()
def digest(p): return sha(Path(p).read_bytes())
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_rows(p,rows):
    with gzip.open(p,'wt',encoding='utf-8',newline='\n') as h:
        for row in rows:h.write(js(row)+'\n')
def pin(p):return {'path':str(Path(p).resolve()),'sha256':digest(p),'bytes':Path(p).stat().st_size}

GROUP='v10_native_group_'+sha(js(sorted(SOURCE_IDS)).encode())[:20]
spec=importlib.util.spec_from_file_location('unchanged_extractor',ROOT/'research/data_prep/wrd_main_v10/extract_native_main.py')
ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
job=load(EP/'job.json')
assert job['source_ids']==SOURCE_IDS
allow=Path(job['source_allowlist_receipt']); ancestry=Path(job['resource_ancestry_receipt'])
assert digest(allow)==job['source_allowlist_sha256'] and digest(ancestry)==job['resource_ancestry_sha256']
assert load(allow)['status']==load(ancestry)['status']=='PASS'
assert load(allow)['train_source_ids']==SOURCE_IDS
assert all(load(allow)[k] and load(ancestry)[k] for k in ['original226_isolated','newH_isolated','static_dev_test_isolated'])
resources={item['mount']:item for item in job['resources']}
for item in job['resources']:assert digest(item['path'])==item['sha256']
originals=[json.loads(x) for x in gzip.open(OUT/'C_review.original_responses.jsonl.gz','rt',encoding='utf-8')]
by_seq={int(r['call_id'][:4]):r for r in originals}
positive=[]
def approve(seq,start,end,reason,evidence,stop_at_anchor=True):
    row=by_seq[seq]; r=row['message']['reasoning_content']; a=r.index(start)
    b=r.index(end,a)+(len(end) if stop_at_anchor else 0)
    prefix=js(row['native_messages'])
    assert all(q in prefix for q in evidence),(seq,evidence)
    positive.append({'id':f'C_R_{seq:04}_{len(positive)+1:02}','call_id':row['call_id'],'field':'reasoning_content',
        'start':a,'end':b,'sha256':sha(r[a:b].encode()),'text':r[a:b],'mask':1,'label':'LOCAL_CONTENT_VERIFIED_AI_SILVER_NOT_HUMAN_GOLD',
        'reason':reason,'delivered_evidence_substrings':evidence,'request_sha256':row['request_sha256'],'response_sha256':row['response_sha256']})

# Read the whole 30,514-character R, but approve only independently checked local
# statements. Speculation, wrong intermediate arithmetic, and all other R stay 0.
approve(9,'Also "张豈明是当前最合适的人选"','That\'s a deduction for E_A.',
        'The actual E_A conclusion asserts a superlative absent from the source; local factual comparison only.',
        ['张豈明是当前最合适的人选','具备较快承担实际任务的条件'])
approve(9,'Condensing is allowed','those are preserved.',
        'The source asks for concision; the delivered protocol distinguishes derived quality from explicit requirements.',
        ['简明扼要一点描述','derived_quality_items_are_not_explicit_user_requirements'])
approve(9,'- L_A: greeting + report.','"实测显示" ok.',
        'The two quoted numeric statements reproduce the supplied user claims; no external verification is credited.',
        ['覆盖80%的备课与教学外延工作','教学效率提升85%'])
approve(9,'- L_A dropped','allowed to compress non-essential details.',
        'The omitted source example is not independently a mandatory detail; this respects the actual compression instruction.',
        ['一次教材改版甚至都要教师重新手写教案','600字以内'])
approve(9,'- L_A\'s report body:','Yes.',
        'Both requested report angles are visible in the actual delivery.',
        ['一、建设成果','二、推广应用'])
approve(9,'1. Core metrics preserved accurately','score1 each.',
        'Both L deliveries preserve these specific original user-supplied figures.',
        ['92.75%','3000','2026年1月','6个'])
approve(9,'1. Covers建设成果 and推广:','both yes; L_A merges into建设成果, fine.',
        'Both requested main aspects and the actual platform/research discussion are present.',
        ['建设成果','推广','五大场景'])
approve(9,'1. Five reasons preserved:','both preserve.',
        'Actual E outputs cover the five reasons and retain current need/candidate readiness; this does not approve the E_A added superlative.',
        ['科研成果工程化','重点横向项目','学生工程实践','贵州','可较快承担实际任务'])
approve(9,'Now the TSR:','TSR pass for all four.',
        'Before this request the reviewer had received successful reads of the four full UTF-8 deliverables; artifact checks remain separate from Q.',
        ['word_count_and_content_quality_are_Q_not_TSR','L_A.md','E_B.md'])
approve(11,'E_A stronger claim:','"具备较快承担实际任务的条件".',
        'Narrow comparison of an actual unsupported superlative against the original candidate-readiness qualifier.',
        ['张豈明是当前最合适的人选','具备较快承担实际任务的条件'])
approve(11,'L accuracy check:','both fine.',
        'Quoted L statements and coverage quantities match the actual source and deliveries; user claims remain user claims.',
        ['团队通过一年的从原型到产品','用户覆盖32个省份3000'])
approve(11,'L_B title "立项背景"','Not a fault.',
        'Using the actual research/pain-point material as report background is compatible with the official-report request.',
        ['立项背景','做一个官方的汇报'])
approve(11,'But rule: one primary dimension.','So D4 =1.0.',
        'Explicitly avoids deducting the same unsupported superlative twice; the delivered protocol requires one primary dimension.',
        ['same_issue_one_primary_deduction_dimension'])
approve(15,'- Cost: skill arm costs were hugely higher:','E skill864,484/13 vs E no-skill161,545/3 (~5.3x).',
        'Each actual per-run token/call tuple is already delivered in phase2; only this local comparison, not nearby wrong cumulative estimates, is credited.',
        ['1156866','216325','864484','161545'])
approve(15,'Two cases = bounded development evidence,','not generalization proof.',
        'Scope matches the actual two-case development protocol.',
        ['two_cases_are_bounded_development_evidence_not_generalization_proof'])
approve(15,'So decision = STOP','Must not fake a seal.',
        'Given no demonstrated reduction in these two actual trials, bounded STOP is protocol-compatible; this credits a proposed decision rather than claiming an executed seal.',
        ['correct_but_more_expensive_resource_work_can_receive_local_credit_while_cost_stop_is_the_correct_terminal_label'])
approve(20,'Cost (actual usage):','- Skill development:',
        'Actual per-case costs and ratios are locally correct; end before the wrong development subtotal.',
        ['1156866','216325','864484','161545'],False)
approve(20,'- cash_cost UNKNOWN_NOT_ZERO;','cost per qualified skill UNDEFINED.',
        'The delivered accounting explicitly keeps cash/curation unknown and the zero-qualified denominator undefined.',
        ['UNKNOWN_NOT_ZERO','UNDEFINED'])
approve(20,'- Costs: preserve all failure/interruption costs;','do not claim domain-wide.',
        'Correct accounting and scope constraints already present in delivered protocol.',
        ['all_actual_NS_and_skill_attempts_including_failure_and_recovery','two_cases_are_bounded_development_evidence_not_generalization_proof'])
approve(21,'Total4,968,017+2,399,220=7,367,237.','per-qualified-skill cost UNDEFINED.',
        'The explicit addition is correct as pre-review costs from delivered phase2. It is never credited as including this then-in-progress review.',
        ['110236','1781339','2259517','570932','245993','UNKNOWN_NOT_ZERO','UNDEFINED'])
approve(21,'Decision: STOP. Local correctness credit noted.','No revision fabricated.',
        'A bounded decision and non-fabrication constraint, without blanket resource correctness or hindsight final costs.',
        ['correct_but_more_expensive_resource_work_can_receive_local_credit_while_cost_stop_is_the_correct_terminal_label'])
approve(21,'4. Generalization bounded to two cases.','independent reassessment.',
        'Correctly keeps claims to the observed development scope and requires new evidence after byte changes.',
        ['new_or_changed_skill_bytes_require_corresponding_new_trials_and_independent_reassessment'])

selected_by=defaultdict(list)
for item in positive:selected_by[item['call_id']].append(item)
segments=[]
for row in originals:
    r=row['message']['reasoning_content']; cursor=0
    for item in sorted(selected_by[row['call_id']],key=lambda x:x['start']):
        assert item['start']>=cursor,'overlapping original R credit'
        if cursor<item['start']:segments.append({'call_id':row['call_id'],'start':cursor,'end':item['start'],'sha256':sha(r[cursor:item['start']].encode()),'mask':0,'reason':'UNAPPROVED_OR_ERROR_OR_SPECULATIVE_OR_PROCEDURAL_ONLY'})
        segments.append({k:item[k] for k in ['call_id','start','end','sha256','mask','id']});cursor=item['end']
    if cursor<len(r):segments.append({'call_id':row['call_id'],'start':cursor,'end':len(r),'sha256':sha(r[cursor:].encode()),'mask':0,'reason':'UNAPPROVED_OR_ERROR_OR_SPECULATIVE_OR_PROCEDURAL_ONLY'})
assert sum(x['end']-x['start'] for x in segments)==30514
save(OUT/'ORIGINAL_R_LOCAL_REVIEW.json',{'schema':'v10-C-review-exact-local-R-review-v1','annotator':'Codex AI silver; not human calibrated; parent root review pending',
    'root_main_admission':False,'full_original_R_read_characters':30514,'positive_original_characters':sum(x['end']-x['start'] for x in positive),
    'positive_ranges':positive,'complete_disjoint_R_mask_partition':segments,'all_original_content_and_tool_actions_default_mask':0,
    'original_outcome_not_used_as_blanket_R_approval':True,'future_cost_never_inserted_into_original_past':True})

core_rows=[]; full53_rows=[]
def make_row(episode,call_id,bank,components,ranges,review,identity_suffix):
    source_job=load(episode/'job.json')
    msg,meta,request,response=ex.recover(episode/'api_audit'/call_id)
    actual=load(request); messages=deepcopy(actual['messages'])+[msg];projections=[]
    for i,m in enumerate(messages):
        if isinstance(m.get('content'),list):
            blocks=m['content'];assert all(b.get('type')=='text' and isinstance(b.get('text'),str) for b in blocks)
            m['content']='\n'.join(b['text'] for b in blocks)
            projections.append({'message_index':i,'rule':'JOIN_COMPLETE_TEXT_BLOCKS_WITH_NEWLINE','original_blocks_sha256':sha(js(blocks).encode()),'projected_text_sha256':sha(m['content'].encode())})
    assert {c['function']['name'] for m in messages for c in m.get('tool_calls',[])}<=ex.CORE
    tools=[t for t in actual['tools'] if t['type']=='function' and t['function']['name'] in ex.CORE]
    assert len(tools)==7 and len(actual['tools'])==53
    row={'id':f'native_{source_job["job_id"]}_{call_id}_{identity_suffix}','source_ids':source_job['source_ids'],'source_group_id':GROUP,
        'parent_source_union':SOURCE_IDS,'split':'train','stage':source_job['stage'],'bank':bank,
        'source_admission':'ADMIT','training_admitted':True,'compiler_admission_is_local_provisional_only':True,'root_main_admission':False,
        'annotation_provenance':'ACTUAL_NATIVE_COMPATIBLE_API_RESPONSE_LOCAL_INDEPENDENT_AI_SILVER_NOT_HUMAN_GOLD',
        'messages':messages,'tools':tools,'supervision_message_indices':[len(messages)-1],'message_loss_mask':[0]*(len(messages)-1)+[1],
        'approved_components':components,'approved_field_ranges':[{**r,'message_index':len(messages)-1} for r in ranges],
        'allow_reviewed_completion_prefix':True,'loss_multiplier':0.25,
        'tool_schema_provenance':pin(request),'student_view':'DECLARED_CORE7_TOOL_CATALOG_PROJECTION_FULL_SYSTEM_AND_PAST_MESSAGES_RETAINED',
        'complete_text_block_projection':projections,'is_original_native_request_identical':False,'runtime_still_has_53_tools':True,
        'is_full_autonomous_execution_demonstration':False,'semantic_review':review,
        'evidence':{'call_id':call_id,'request':str(request),'request_sha256':digest(request),'response':str(response),'response_sha256':digest(response),'provider_meta':meta},
        'frozen_job':pin(episode/'job.json'),'source_allowlist':pin(source_job['source_allowlist_receipt']),
        'resource_ancestry':pin(source_job['resource_ancestry_receipt']),'future_feedback_in_model_input':False}
    full=deepcopy(row);full['id']+='_full53_candidate';full['bank']+='_full53_long_candidate';full['tools']=actual['tools']
    full['student_view']='FULL53_CATALOG_FULL_SYSTEM_AND_FULL_PAST_TEXT_BLOCK_PROJECTION_ONLY'
    full['long_context_candidate_only']=True;full['mutually_exclusive_same_owner_as']=row['id']
    return row,full

for call_id,items in sorted(selected_by.items()):
    if not items:continue
    r,full=make_row(EP,call_id,'native_C_review_partial_01',[],[{'field':'reasoning_content','start':x['start'],'end':x['end'],'text_sha256':x['sha256']} for x in items],
        {'review':pin(OUT/'ORIGINAL_R_LOCAL_REVIEW.json'),'approved_range_ids':[x['id'] for x in items],'approval_scope':'ONLY_EXACT_ORIGINAL_R_RANGES_ALL_OTHER_R_CONTENT_ACTIONS_MASK0'},'local_R')
    core_rows.append(r);full53_rows.append(full)
process_review_path=OUT/'independent_process_review/PROCESS_CANDIDATES.json'
process_review=load(process_review_path)
execution_rows=[]
for item in process_review['candidates']:
    episode=RT/'episodes'/item['episode']
    r,full=make_row(episode,item['api_call_id'],'native_C_execution_local_01',['A'],[],
        {'review':pin(process_review_path),'approval_scope':'ONLY_ACTUAL_DELIVERABLE_WRITE_TOOL_ARGUMENTS_AND_NAME','independent_content_receipts':item['semantic_claim_receipts'],
         'action_not_approved_from_done_alone':True,'future_success_feedback_is_metadata_only':item['actual_success_observation']},'local_write')
    target=r['messages'][-1]
    assert len(target.get('tool_calls',[]))==1
    call=target['tool_calls'][0];assert call['id']==item['tool_call_id'] and call['function']['name']=='write'
    args=json.loads(call['function']['arguments'])
    assert sha(call['function']['arguments'].encode())==item['raw_arguments_sha256']
    assert sha(args['content'].encode())==item['decoded_content_sha256']
    assert args['path']=='/workspace/outputs/deliverable.md'
    execution_rows.append(r);full53_rows.append(full)

# An explicitly NEW post-terminal state. It never claims to be the original D
# prefix, original teacher reasoning, an executed tool call, or a new native run.
L=load(resources['inputs/review/tasks/L.json']['path'])
E=load(resources['inputs/review/tasks/E.json']['path'])
qpath=EP/'workspace/outputs/quality_blind.json'; quality=load(qpath)
cost=load(QDIR/'ACTUAL_COST_RECONCILIATION.json')
blind=load(QDIR/'BLIND_ORDER_AUDIT.json')
assert blind['status']=='PASS_SCOPED_ACTUAL_READ_ORDER' and blind['quality_write_actual_native_tool_result']['native_seq']==39
assert cost['known_total_tokens']==8660547 and cost['actual_request_identities']==110 and cost['unknown_usage_calls']==1
assert load(QDIR/'Q_ARITHMETIC_AUDIT.json')['status']=='PASS_ARITHMETIC_ONLY'
cases={}
for c in ['L','E']:
    cases[c]={'original_user_requests':[{'role':'user','content':m['content']} for m in L['messages']] if c=='L' else [{'role':'user','content':E['current_original_request']['content']}],
        'actual_deliverables':{label:Path(resources[f'inputs/review/outputs/{c}_{label}.md']['path']).read_text(encoding='utf-8') for label in ['A','B']},
        'AI_blind_quality':{label:{'dimensions':quality['cases'][c][label]['dimensions'],'weighted_total':quality['cases'][c][label]['weighted_total']} for label in ['A','B']}}
state={'objective':'仅在资源可靠、质量可接受且实际替代公共工作并减负时保留候选技能。依据已提供的实际证据作当前保留、修订、停止或暂缓判断；结论限于已观察范围。',
    'current_state':'同一候选版本的两例双臂消费、盲评和终评已经全部结束；下面明确补充终评之后才可得到的累计费用。现在为新的决策状态。',
    'candidate':{'mechanism':'把用户素材整理为带引文的事实/目标/约束账本，按用途成稿，再做结构、类型、数字、长度及引文检查；语义保真仍需独立复核。',
        'tested_scope':'现成短文本材料的官方汇报/机构理由精简成稿。L是Maker见过的复现；E的原文未给Maker，但仍是训练发展案例。两例不代表其他体量、所有写作或全部WRD机制。',
        'resources':'轻量SKILL、两份JSON schema、成稿模板、标准库校验程序，共五个功能文件。',
        'version_and_consumption':'两次技能消费均实际全文读取了技能；五个功能文件在提供的候选、两次消费副本及评审副本中逐文件SHA一致，无消费后改包。真实读用不自动证明收益。',
        'local_validation':'修订后原21项及独立8个正反例均通过，清洁投递视图也复现通过。这是已测试局部行为的证据；不证明任意输入正确或语义自动通过。'},
    'cases':cases,'arm_map':{'L':{'A':'Skill','B':'NoSkill'},'E':{'A':'NoSkill','B':'Skill'}},
    'quality_identity':{'kind':'探索性、未经人工校准的AI独立盲Q报告，非human gold。','weights':{'D1':0.3,'D2':0.2,'D3':0.2,'D4':0.2,'D5':0.1},
        'actual_order':'原盲Q文件成功写入后才读取臂身份和成本，之后未重写；本次只核过计分结构与算术。',
        'limits':'条目及分数作为原AI观察输入，语义评分未获人工校准；两例分差不能测定统计噪声幅度，也不能证明泛化。',
        'original_length_measurement':quality['length_measurement'],
        'scope_note':'L整份文本与仅报告正文是不同计数边界；624（含非换行空白）与620（去空白）都超过600，534来自去掉标题、问候和收尾后的正文，不能说是空白计数造成跨线。E无数值字数限制。',
        'semantic_limit_note':'校验程序诚实保留独立语义复核，不把这一范围限制自动判为代码缺陷；强评价词扫描的有效性未验证。'},
    'delivery_acceptance':'四份具名deliverable均真实存在、非空、可打开；2/2与2/2。TSR只作基础交付验收，Q单列，不相乘。',
    'actual_usage':{'per_run':[{'case':'L','arm':'NoSkill','tokens':216325,'model_calls':4},{'case':'L','arm':'Skill','tokens':1156866,'model_calls':17},
        {'case':'E','arm':'NoSkill','tokens':161545,'model_calls':3},{'case':'E','arm':'Skill','tokens':864484,'model_calls':13}],
        'NoSkill_total':{'tokens':377870,'model_calls':7},'Skill_total':{'tokens':2021350,'model_calls':30},
        'accounting_scope':'Token是原生实付请求的已知输入加输出，读取、失败与恢复开销保留；调用指实际模型调用，兼容HTTP续接不另算付费请求。',
        'pre_review':{'known_tokens':7367237,'includes_current_review':False},'current_review_after_terminal':{'known_tokens':1293310,'model_calls':15},
        'all_stages_after_terminal':{'known_tokens':8660547,'actual_request_identities':110,'unknown_usage_calls':1,
          'included':'技术probe、A、B中断、B制作、局修、四次消费、本次终评；失败和中断不抹去。'},
        'cash_cost':'未知，不能按0','AI_curation_and_code_work_cost':'未知，不能按0','device_energy':'未测量，不能按0',
        'qualified_retained_skill_count':0,'cost_per_qualified_skill':'未定义（零合格分母）'}}
reason='该版本在两例上都有真实读用与局部校验证据，四份基础交付也均通过；AI盲Q未人工校准，只能作有限质量参考。技能臂合计2021350tokens/30次调用，无技能377870tokens/7次，约5.35倍Token和4.29倍调用，未观察到实际减负，保留条件不满足。因此对当前版本作有界STOP。局部正确资源仍有过程价值；这不证明所有写作技能或WRD均无价值，也不宣称STOP是全局最优。'
decision={'decision':'STOP','scope':'当前同版本候选及已完成的两例开发消费','reason':'质量有局部支持，但实际公共执行开销明显增加，尚无净减负证据。',
    'local_credit':'已通过的局部程序修复、资源校验和保真成稿分别保留信用，不批准整段原R或全部技能。',
    'cost':'终评后全部已知原生8660547tokens，110个实际请求身份中1次usage未知；现金、AI整理费用和能耗未知。零合格技能的每合格技能总成本未定义。',
    'next_state':'本次不保留、不封存；如以后改变技能字节，需另有对应消费与独立复评。'}
new_messages=[{'role':'system','content':'你负责依据实际材料和已知结果判断候选技能是否值得保留。保留需同时满足资源可靠、质量可接受、真实使用以及实际公共工作减负；区分观察、未知与未校准AI判断，限定结论范围。'},
    {'role':'user','content':js(state)}, {'role':'assistant','reasoning_content':reason,'content':js(decision)}]
state_row={'id':'NEW_AUTHORED_REAL_STATE_COST_STOP_01','source_ids':SOURCE_IDS,'source_group_id':GROUP,'parent_source_union':SOURCE_IDS,'split':'train',
    'stage':'D_new_post_terminal_state','bank':'new_real_state_cost_stop_01','source_admission':'ADMIT','training_admitted':True,
    'compiler_admission_is_local_provisional_only':True,'root_main_admission':False,'annotation_provenance':'NEW_AUTHORED_AI_SILVER_SUMMARY_ON_REAL_POST_TERMINAL_STATE_NOT_ORIGINAL_TEACHER_R',
    'messages':new_messages,'tools':[],'supervision_message_indices':[2],'message_loss_mask':[0,0,1],'approved_components':['R','D'],
    'loss_multiplier':0.25,'is_full_autonomous_execution_demonstration':False,'is_original_native_request_identical':False,
    'same_condition_as_original_D':False,'new_current_state_after_original_review_terminal':True,'new_author':'Codex research data curator AI silver, not human gold',
    'authoring_claim':'New concise rationale and ordinary assistant final decision. No native tool call or seal execution is fabricated.',
    'source_allowlist':pin(allow),'resource_ancestry':pin(ancestry),'original_job':pin(EP/'job.json'),
    'evidence_receipts':[pin(qpath),pin(QDIR/'ACTUAL_COST_RECONCILIATION.json'),pin(QDIR/'BLIND_ORDER_AUDIT.json'),pin(QDIR/'Q_ARITHMETIC_AUDIT.json'),pin(QDIR/'SEMANTIC_ERRATA.json')],
    'original_artifacts_are_preserved_separately':True,'state_cannot_supervise_original_blinding_actions_with_hindsight':True,'does_not_prove_globally_optimal_STOP':True}
write_rows(OUT/'original_R.core7.candidates.jsonl.gz',core_rows)
write_rows(OUT/'execution_local.core7.candidates.jsonl.gz',execution_rows)
write_rows(OUT/'original_native.full53.long_candidates.jsonl.gz',full53_rows)
write_rows(OUT/'new_real_state_cost_stop.candidate.jsonl.gz',[state_row])
save(OUT/'NEW_AUTHORED_REAL_STATE_COST_STOP.input.json',state)
save(OUT/'NEW_AUTHORED_REAL_STATE_COST_STOP.output.json',{'new_AI_silver_summary':reason,'assistant_final_decision':decision})
evidence_out=OUT/'preserved_original_artifacts';evidence_out.mkdir(exist_ok=True)
copies=[]
for p in [qpath,EP/'workspace/outputs/decision.json',EP/'workspace/outputs/feedback.json',allow,ancestry,QDIR/'SEMANTIC_ERRATA.json']:
    dst=evidence_out/p.name
    if not dst.exists():shutil.copyfile(p,dst)
    assert digest(dst)==digest(p);copies.append({'original':pin(p),'preserved_copy':pin(dst),'positive_loss':False})
pins=[pin(EP/'job.json'),pin(allow),pin(ancestry),*[pin(x['path']) for x in job['resources']],*[pin(QDIR/x) for x in ['ACTUAL_COST_RECONCILIATION.json','BLIND_ORDER_AUDIT.json','Q_ARITHMETIC_AUDIT.json','SEMANTIC_ERRATA.json']]]
for epname in ['C_L_skill_01','C_E_skill_01','C_L_no_skill_01','C_E_no_skill_01']:
    p=RT/'episodes'/epname
    for name in ['job.json','CONSUMPTION_AUDIT.json','usage.json','result.json']:
        pins.append(pin(p/name))
        if name=='CONSUMPTION_AUDIT.json':
            a=load(p/name);assert a['all_supplied_skill_functional_bytes_stable']
save(OUT/'SOURCE_AND_ORIGINAL_ARTIFACT_RECEIPTS.json',{'schema':'v10-C-review-sources-and-state-receipts-v1','status':'PASS_SCOPED_TRAIN4_CLOSED_ANCESTRY',
    'source_ids':SOURCE_IDS,'source_group_id':GROUP,'split':'train','all_4_banks_share_parent_group':True,
    'root_main_admission':False,'original226_isolated':True,'newH_isolated':True,'static_dev_test_isolated':True,
    'functional_input_has_no_capture_path_or_callID_or_admission_flags':True,'functional_input_digest':sha(new_messages[1]['content'].encode()),
    'files':pins,'preserved_original_copies':copies,'shared_compiler':pin(ROOT/'research/data_prep/wrd_main_v10/compile_main.py'),
    'unchanged_extractor':pin(ROOT/'research/data_prep/wrd_main_v10/extract_native_main.py'),'original_execution_design_revision':'5.0.39','current_design_revision_for_data_preparation':'5.0.40',
    'all_other_source_bodies_not_read':True,'no_model_calls_or_training_or_native_mutation':True})
save(OUT/'PREPARATION_SUMMARY.json',{'original_R_chars':30514,'positive_R_ranges':len(positive),'positive_R_chars':sum(x['end']-x['start'] for x in positive),
    'core7_R_response_candidates':len(core_rows),'execution_local_write_candidates':len(execution_rows),'new_authored_real_state_candidates':1,
    'full53_long_candidates':len(full53_rows),'root_main_admission':False,'training_started':False,'script':pin(Path(__file__))})
print(js(load(OUT/'PREPARATION_SUMMARY.json')))
