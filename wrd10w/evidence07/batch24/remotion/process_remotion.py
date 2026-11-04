"""Offline provenance recovery and source-only authored decisions; no agents/models."""
from pathlib import Path
from collections import Counter
import ast
import gzip
import hashlib
import json
import shutil

ROOT = Path('D:/skillloop')
OUT = Path(__file__).resolve().parent
V9 = ROOT/'output/20261026_wrd_dataset_v9'
REC = ROOT/'output/20261029_wrd_v9_missing_evidence_recovery'
CAS = ROOT/'output/20261025_wrd_training_dataset/bundle/archive'
SOURCE_ID = 'conv_eaf2e429a225'
SOURCE_SHA = 'ef11f74b2c49b70f16bdee4e02fdb8124fd368ac10189c73933d29d17f49753c'

def h(b): return hashlib.sha256(b).hexdigest()
def pin(p): return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': h(p.read_bytes())}
def canonical(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
def rows(p): return [json.loads(s) for s in gzip.open(p, 'rt', encoding='utf-8')]
def save(n, x):
    p=OUT/n; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return pin(p)
def gz(n, rs):
    p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as f:
            for x in rs:f.write(canonical(x)+b'\n')
    return pin(p)
def messages(p):
    return [{'event_line':i,'message':x['message'],'event':x} for i,s in enumerate(p.read_text(encoding='utf-8').splitlines(),1) if (x:=json.loads(s)).get('type')=='message']
def text(m):
    c=m.get('content','');return c if isinstance(c,str) else ''.join(x.get('text','') for x in c if isinstance(x,dict))
def calls(m):return [x for x in m.get('content',[]) if isinstance(x,dict) and x.get('type')=='toolCall']

def main():
    eps=[x for x in rows(REC/'MAKE_100_EPISODE_CLUSTERS.metadata.jsonl.gz') if x['route_id']=='remotion-explainer-video']
    assert len(eps)==6 and sum(x['held_target_count'] for x in eps)==54
    scope={x['source_id']:x for x in rows(ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz')}
    assert scope[SOURCE_ID]['status']=='TRAIN'
    all_eps={x['episode_id']:x for x in rows(V9/'recovery/episodes.metadata.jsonl.gz')}
    target_rows=rows(V9/'outcomes/recomputed_scope_overlay/target_outcome_labels.jsonl.gz')
    producer_ep=all_eps['ep_098af89215167714ca8c']
    producer_native=Path(producer_ep['source_native']['path']);assert h(producer_native.read_bytes())==producer_ep['source_native']['sha256']
    pm=messages(producer_native);pc=calls(pm[29]['message'])[0]
    assert pc['name']=='exec'
    code=pc['arguments']['command'].split("<<'EOF'\n",1)[1].rsplit('\nEOF',1)[0]
    tree=ast.parse(code)
    route_values=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='routes' for t in n.targets))
    decision_values=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='decisions' for t in n.targets))
    original_route=next(r for r in route_values if r['id']=='remotion-explainer-video')
    producer_output=Path(producer_ep['source_original_path']).parent.parent/'workspace/outputs/routes.json'
    assert json.loads(producer_output.read_text(encoding='utf-8'))=={'routes':route_values,'decisions':decision_values}
    ack=pm[30]['message'];assert ack['toolCallId']==pc['id'] and ack['isError'] is False and ack['details']['exitCode']==0
    ps=next(x for x in target_rows if x['episode_id']==producer_ep['episode_id'] and x['source_message_index']==29)
    assert ps['source_admission']=='HOLD_PROTECTED' and ps['original226']
    producer_proof={'producer_episode_id':producer_ep['episode_id'],'native':pin(producer_native),'write_message_index':29,
        'write_event_line':pm[29]['event_line'],'tool_call_id':pc['id'],'original_command_sha256':h(pc['arguments']['command'].encode()),
        'literal_routes_and_decisions_equals_entire_actual_output_JSON':True,'output':pin(producer_output),
        'route_value_sha256':h(canonical(original_route)),'ack_message_index':30,'ack_event_line':pm[30]['event_line'],
        'ack_text_sha256':h(text(ack).encode()),'actual_write_scope':ps,
        'no_original_command_executed_by_this_processor':True,'protected_content_used_for_training_labels':False}
    save('ROUTE_PRODUCER_PROOF.json',producer_proof)
    resources=rows(REC/'MAKE_PRIOR_RESOURCES.metadata.jsonl.gz');decisions=[];events=[];episode_stats=[]
    for ep in eps:
        eid=ep['episode_id'];native=Path(ep['source_native']['path']);assert h(native.read_bytes())==ep['source_native']['sha256']
        ms=messages(native);r=next(x for x in resources if x['episode_id']==eid and x['native_path']=='/workspace/inputs/route.json')
        rp=CAS/r['file_identity']['object'];assert h(rp.read_bytes())==r['file_identity']['sha256'];route=json.loads(rp.read_text(encoding='utf-8'))
        assert all(route[k]==v for k,v in original_route.items())
        extra=set(route)-set(original_route);assert extra<= {'conditions','conflicts'} and all(route[k]==[] for k in extra)
        assert r['observed_after_assistant_message_index']==1
        c=calls(ms[1]['message'])[0];assert c['name'] in ('read','exec')
        observation=text(ms[2]['message']).replace('\r\n','\n').replace('\r','')
        # The actual observation starts with this route object (after a directory listing for one episode).
        start=observation.find('{');received,end=json.JSONDecoder().raw_decode(observation[start:]);assert received==route
        rr={'episode_id':eid,'route_input':pin(rp),'original_route_fields_equal':True,'extra_empty_fields':sorted(extra),
            'actual_read_call_id':c['id'],'actual_read_message_index':1,'actual_read_event_line':ms[1]['event_line'],
            'observation_message_index':2,'observation_event_line':ms[2]['event_line'],'received_route_JSON_equals_input_JSON':True,
            'observation_sha256':h(text(ms[2]['message']).encode()),'protected_producer':producer_ep['episode_id']}
        save('route_receipts/'+eid+'.json',rr)
        dest=OUT/'original_native'/f'{eid}.jsonl';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(native,dest)
        assert h(dest.read_bytes())==h(native.read_bytes())
        for tid,idx in zip(ep['held_target_ids'],ep['target_message_indices']):
            assert idx>2
            decisions.append({'id':tid,'episode_id':eid,'source_message_index':idx,'status':'HOLD_PROTECTED_RESOURCE_ANCESTOR',
                'reason':'EXACT_ROUTE_PRODUCER_WAS_EXPOSED_TO_ORIGINAL226_BEFORE_WRITE_AND_ROUTE_WAS_ACTUALLY_RECEIVED_BEFORE_TARGET',
                'source_ids':[SOURCE_ID],'route_producer_episode_id':producer_ep['episode_id'],'producer_scope_proof_id':ps['scope_proof_id'],
                'protection_starts_strictly_after_observation_message_index':2,'route_receipt_path':'route_receipts/'+eid+'.json',
                'original_R_and_actions_retained_verbatim':True,'positive_loss':0,'main_admitted':False,
                'scope_not_a_semantic_error_judgment':True})
        for i,m in enumerate(ms):
            mm=m['message'];cc=calls(mm)
            events.append({'episode_id':eid,'message_index':i,'event_line':m['event_line'],'role':mm['role'],
                'event_raw_SHA256':h(canonical(m['event'])),'content_text_chars':len(text(mm)),
                'original_thinking_block_chars':sum(len(str(x.get('thinking',''))) for x in mm.get('content',[]) if isinstance(x,dict)),
                'tool_call_ids':[x['id'] for x in cc],'tools':[x['name'] for x in cc],
                'arguments_SHA256':[h(canonical(x.get('arguments'))) for x in cc],
                'returned_tool_call_id':mm.get('toolCallId'),'is_error':mm.get('isError'),
                'raw_full_event_file':'original_native/'+eid+'.jsonl','training_loss':0})
        episode_stats.append({'episode_id':eid,'messages':len(ms),'held_positions':ep['held_target_count'],
            'raw_native':pin(dest),'all_held_positions_protected_by_actual_route_read':True,
            'positive_main_targets':0,'native_thinking_field_is_not_provider_thought_completeness_proof':True})
    assert len(decisions)==54 and len({r['id'] for r in decisions})==54
    gz('TARGET_DECISIONS_54.jsonl.gz',decisions);gz('EVENT_TIMELINE.jsonl.gz',events)
    save('EPISODE_RECOVERY.json',{'status':'ALL_54_POSITION_SOURCE_ANCESTRY_RESOLVED_PROTECTED','episodes':episode_stats,
        'remaining_unknown_in_the_54':0,'new_training_targets_from_original_54':0,'no_semantic_promotion_of_protected_code_or_feedback':True,
        'reviewer_exposure_note':'Processor inspected route/provenance and some existing native observation summaries before full producer closure; protected route and code are not used in new source-only labels. Original clean enterprise body is a separate current TRAIN source.',
        'training_started':False,'new_agent_calls':0,'weights_loaded':False})
    make_source_only(scope)

def make_source_only(scope):
    p=CAS/'objects'/SOURCE_SHA[:2]/SOURCE_SHA;assert h(p.read_bytes())==SOURCE_SHA
    source=json.loads(p.read_text(encoding='utf-8'));ms=source['messages'];assert len(ms)==112
    destination=OUT/'source_only/original_conversation.json';destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,destination)
    # Targets below are newly authored expert decisions; only the indicated original prefixes are inputs.
    annotations=[
      {'key':'entry_resource_spec','prefix_end':1,'stage':'B_source_only_entry_decision',
       'question':'从当前会话识别值得沉淀的工作方法，给出资源制作的入口和所需事实。现在没有工作目录清单、已安装技能正文、素材内容或任何工具返回。',
       'rationale':'用户委托从指定制作包生成视频，并强调数字人尺寸。制作包内容、既有技能接口和当前目录均未实际读取，不能把用户提及路径当作资源已经可用。应先恢复输入与现有能力，再判断哪些重复步骤适合资源化。',
       'decision':{'stage':'DISCOVER_INPUTS','next_action':'读取用户指定的既有视频技能用法并列出制作包，确认工作目录中的实际路径、素材、脚本与授权输出位置。',
         'reuse_scope':'用户明确指定了 remotion-video-generator，先查其当前版本和用法；尚不能认定必须另建相同能力的技能。',
         'resource_spec':['素材索引：文件类型、路径和用途，与现有脚本/分镜逐项对应。','场景布局参数：数字人占比与画中画可读性分别可调。','渲染与断点记录：记录项目/素材版本及未完成阶段，便于接续。','验收记录：元数据、画面内容和用户纠正分开保存。'],
         'unknown':['制作包在当前环境是否存在','既有技能的真实资源及依赖','用户指定的大尺寸对应的可读性阈值','素材/成片是否正确'],
         'closure':'CONTINUE_DISCOVERY','confirmed_execution':False,'qualified_skill':False}},
      {'key':'reported_failure_evidence','prefix_end':59,'stage':'B_source_only_evidence_decision',
       'question':'会话中有多次失败诊断、重试和声称修复。请决定哪些记录可以直接作为正确程序或已验证修复的训练依据，以及下一步怎样补证。当前只有会话文本，原工具请求、返回和产物均未提供。',
       'rationale':'历史文本先将404归因于中文路径，又转向 staticFile 包装；绿幕也经历多种方案。它们是探索假设及自述，缺少原请求、失败返回和版本，不能将后来一句“找到根因”追认所有此前判断正确。没有实际代码时也不能据这些句子重建一个声称已验证的实现。',
       'decision':{'stage':'RECOVER_CAUSAL_EVIDENCE','next_action':'按出现顺序索取或定位原工具调用、错误返回、每次编辑前后内容及对应预览，建立同对象的失败—假设—补丁—复测链。',
          'retain':['全部探索和错误自述原文','相互矛盾的404归因','绿幕透明度逻辑与视频解码相关的尝试','重复文本及其原消息身份'],
          'positive_credit':'仅在同版本原始结果支持后，给准确诊断和有效局部改动授信用；仅有当前文本时不批准程序正确或修复通过。',
          'do_not_generalize':['把一次路径失败推广为中文文件名必然不可用','把缺少图像证据的自述当已完成视觉验收','把重复记录当多次独立成功'],
          'closure':'HOLD_IMPLEMENTATION_CREDIT_PENDING_EVIDENCE','confirmed_execution':False,'qualified_skill':False}},
      {'key':'resume_timeout','prefix_end':60,'stage':'B_source_only_resume_scheduling',
       'question':'在当前用户“继续，前次超时”要求下，制定接续顺序。只提供截至此处的原会话，当前文件、进程、已用预算及剩余预算都未知；不要宣称工具已运行。',
       'rationale':'用户要求接续同一制作任务，超时只说明前次运行未正常继续。文本可能记录了未落实的编辑和重复状态，既不能从头复制全部劳动，也不能假设最后声称的修改已落盘。恢复当前项目、版本和任务状态是执行下一步的前提。',
       'decision':{'stage':'RESUME_EXISTING_ATTEMPT','next_action':'确认当前项目目录、已写资源、渲染输出及后台渲染状态，检查任务是否仍在运行；读取保存的版本和最近的原始错误后再接续。',
          'order':['核对素材和项目版本，保留旧结果。','若原渲染仍在进行，核对它的输入版本后等待或读取状态，避免重发。','若已终止，定位最后完成的检查点和实际失败对象，仅恢复未完成步骤。','核对数字人尺寸与当前帧内容，再决定预览或成片渲染。'],
          'budget':'当前已用和剩余预算UNKNOWN，接续前核实；不据历史等待描述承诺新的完成时间。',
          'closure':'CONTINUE_AFTER_STATE_RECOVERY','confirmed_execution':False,'qualified_skill':False}},
      {'key':'feedback_readability','prefix_end':80,'stage':'C_source_only_feedback_diagnosis',
       'question':'新用户纠正为“电脑素材和视频画中画要大到能看清内容”。判断这对刚才声称完成的结果意味着什么，给出修订与复测计划。当前没有成片像素、工程文件或实际QA记录。',
       'rationale':'前一条助手报告分辨率、时长、帧率和若干“通过”，随后用户仍要求放大。元数据合格并不能证明屏幕操作可读或满足用户偏好。用户纠正需要绑定刚才交付版本，尺寸应以实际画面测定，不能凭文本给出固定像素的保证。',
       'decision':{'stage':'REVISE_LAYOUT','next_action':'恢复用户针对的交付版本及对应工程，定位电脑/录屏区域，在保持数字人要求的同时增大有效屏幕内容，并检查被遮挡元素。',
          'acceptance':['代表性操作画面中的关键文字和步骤在目标观看尺寸可辨。','放大后不遮挡关键按钮、标题和报告内容。','数字人仍满足原需求，但允许结合画面重新布局。','从实际成片抽取对应时刻复核，而不只看工程预览或元数据。'],
          'version_link':'原交付版本身份、修订工程版本和新成片身份均待恢复；保留旧版以便对照。',
          'closure':'REVISE_NOT_KEEP','confirmed_execution':False,'qualified_skill':False}},
      {'key':'latest_correction','prefix_end':111,'stage':'C_source_only_revision_spec',
       'question':'依据最后一条用户纠正，给出精确的修订范围、原要求冲突处理和复测点。当前只有原对话，工程与成片没有读取，不能声称修改已完成。',
       'rationale':'最新用户明确要求电脑再放大至原本1.5倍、允许字幕压在键盘位置，并指出开头文字仍重叠。应将“操作内容可看清”作为本次优先目标，不能继续把键盘与字幕重叠本身判为失败，也不能把开头仍重叠的事实掩盖为前次QA通过。尺寸基准必须绑定用户指向的版本。',
       'decision':{'stage':'REVISE_LOCAL_RESOURCES','next_action':'先恢复用户指向版本的电脑尺寸和开头布局；按该基准将电脑显示尺寸目标调为1.5倍，在画布可用区域内调整位置，并修复开头文字碰撞。',
          'correction_contract':{'requested_scale':1.5,'scale_baseline':'用户所说“原本”的具体版本/参数尚待核对，不凭助手旧数字擅定。','allowed_overlap':'字幕与键盘区域可重叠；不能遮住需要看清的实际操作内容。','must_fix':'开头文字重叠。','preserve':'原制作包内容、视频主题和用户此前的数字人呈现要求；若空间冲突，先布局协商而非静默丢弃。'},
          'verification':['比较实际修改前后对应帧中的电脑有效屏幕区域。','检查开头出现/过渡阶段的文字包围区域，不能只检一帧。','检查录屏关键操作及字幕位置，按用户允许的键盘重叠判定。','预览通过后生成新版本，再从新成片复核相同时刻。'],
          'closure':'REVISE_PENDING_REAL_EXECUTION','confirmed_execution':False,'qualified_skill':False}},
      {'key':'final_outcome_gate','prefix_end':112,'stage':'C_source_only_outcome_gate',
       'question':'整理这段完整会话的收尾证据，判断能否将整条制作/修订链标为合格技能保留。只依据当前文本；没有原始工具日志、实际视频、独立消费对照或费用明细。',
       'rationale':'最终助手声称交付v3和QA通过，但没有实际文件身份或画面证据。此前同类“清晰/通过”后出现用户重复纠正，说明这些自述不能直接当正向终态。可提取纠正需求和待验证方法，不能据此批准所有修订动作、全技能质量或节约成本。',
       'decision':{'stage':'HOLD_OUTCOME_ADMISSION','observed':'存在明确的视频委托、接续请求、画中画可读性与开头重叠纠正，末条有交付自述。',
          'local_credit':'用户需求与纠正规则可以保存；原诊断/代码正确性须另以原始动作、版本和复测证明。',
          'required_before_keep':['恢复v3实际文件及工程身份。','核对最新用户纠正在同一成片版本上的可读性和重叠检查。','若要证明复用价值，准备同条件无技能与技能消费及独立质量评价。','汇总制作、失败、修订、验证和消费全部成本，并按合格结果计算成本。'],
          'closure':'HOLD_NOT_QUALIFIED_KEEP','confirmed_execution':False,'qualified_skill':False,'cost_per_qualified_skill':'UNDEFINED_WITHOUT_QUALIFIED_DENOMINATOR_AND_COST_EVIDENCE'}},
    ]
    result=[];evidence=[]
    for a in annotations:
        end=a['prefix_end'];prefix=ms[:end]
        prompt=a['question']+'\n以下为按导出出现顺序保留的原始会话前缀。助手陈述是历史自述，不能代替原始工具观察；未提供的文件和工具状态仍未知。\n'+json.dumps(prefix,ensure_ascii=False,separators=(',',':'))
        owner='source_only_remotion:'+a['key']
        out={'schema_version':'wrd-source-only-authored-controller-v1','id':owner,'bank':'source_only_controller_batch24',
            'stage':a['stage'],'source_ids':[SOURCE_ID],'source_group_id':scope[SOURCE_ID]['component_id'],'split':'train',
            'source_admission':'ADMIT_SOURCE_ONLY','training_admitted':False,'root_main_admission':False,
            'messages':[{'role':'system','content':'根据真实会话证据整理可复用工作方法与下一步决策。区分用户要求、助手历史自述、原始工具证据、待执行计划和已验证结果；不要将未知状态写成完成。'},
                {'role':'user','content':prompt},{'role':'assistant','reasoning_content':a['rationale'],'content':json.dumps(a['decision'],ensure_ascii=False,indent=2)}],
            'tools':[],'message_loss_mask':[0,0,1],'approved_components':['R','D'],'loss_multiplier':.25,
            'annotation_provenance':'NEW_AUTHORED_SOURCE_ONLY_DECISION_NOT_ORIGINAL_TEACHER_REASONING_OR_EXECUTION',
            'original_conversation_pin':pin(destination),'source_scope_pin':pin(ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz'),
            'prefix_end_exclusive':end,'original_input_prefix_sha256':h(canonical(prefix)),
            'input_contains_no_future_messages':True,'source_only_excludes_historical_maker_route_code_feedback':True,
            'target_owner':{'canonical_original_action_owner_id':owner,'scope':'new_authored_decision_unit_not_original_native_action'},
            'is_original_native_request_identical':False,'is_original_native_next_action_identical':False,'actual_native_tool_dispatch':False,
            'is_full_autonomous_execution_demonstration':False,'positive_skill_outcome_claimed':False,'original226':[],'holdout12':[],
            'protected_sources_visible_prefix':[],'training_started':False,'weights_loaded':False,'new_agent_calls':0,'curation_cost':'UNKNOWN_NOT_ZERO'}
        result.append(out)
        evidence.append({'id':owner,'stage':a['stage'],'source_id':SOURCE_ID,'prefix_end_exclusive':end,
            'prefix_sha256':h(canonical(prefix)),'new_rationale_sha256':h(a['rationale'].encode()),'new_decision_sha256':h(json.dumps(a['decision'],ensure_ascii=False,indent=2).encode()),
            'all_input_message_proofs':[{'message_index':i,'message_id':m['id'],'role':m['role'],'field':'content','start':0,'end':len(m['content']),
                'content_text_sha256':h(m['content'].encode()),'message_canonical_sha256':h(canonical(m))} for i,m in enumerate(prefix)],
            'future_outcome_not_used_in_input':True,'new_label_not_original_CoT':True,'semantic_review_scope':'bounded source-only evidence reasoning and proposed scheduling; no code or achieved result credit'})
    gz('source_only/source_only_controller.raw.jsonl.gz',result);gz('source_only/LABEL_EVIDENCE.jsonl.gz',evidence)
    save('source_only/SOURCE_ONLY_REVIEW.json',{'status':'NEW_SOURCE_ONLY_LABELS_ROOT_REVIEW_AND_COMPILATION_PENDING',
        'source':pin(destination),'source_id':SOURCE_ID,'current_scope':scope[SOURCE_ID],'authored_targets':len(result),
        'stage_counts':dict(Counter(x['stage'] for x in result)),'independent_enterprise_sources':1,
        'no_historical_protected_route_or_code_in_labels':True,'original_maker_54_main_admitted':0,
        'no_original_native_tool_or_CoT_claim_for_new_labels':True,'two_tokenizer_compilation':'ROOT_PENDING',
        'training_started':False,'new_agent_calls':0,'weights_loaded':False,'curation_cost':'UNKNOWN_NOT_ZERO'})
    files=[pin(p) for p in sorted(OUT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name not in {'MANIFEST.json'}]
    save('MANIFEST.json',{'schema':'wrd-batch24-remotion-processed-v1','status':'PROVENANCE_COMPLETE_54_PROTECTED_AND_6_REAL_SOURCE_ONLY_RAW_LABELS',
        'original_episode_count':6,'original_target_positions':54,'resolved_protected_positions':54,'remaining_unknown_positions':0,
        'new_source_only_raw_targets':6,'actual_compiled_new_targets':0,'root_main_admitted_new_targets':0,'files':files,
        'training_started':False,'new_agent_calls':0,'weights_loaded':False})
    print(json.dumps({'protected':54,'source_only_raw_targets':6,'actual_compiled_new_targets':0,'files':len(files)}))

if __name__=='__main__':main()
