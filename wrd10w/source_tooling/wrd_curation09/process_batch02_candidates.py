"""Exact historical actions in explicit, evidence-grounded functional states.

Only candidate input artifacts. No original prompt equivalence, native deployment,
full-skill success, or admission is claimed. Never execute recorded commands.
"""
import gzip, hashlib, json
from pathlib import Path
from process_batch02_review import BASE, OUT, REVIEWS, read, dump

ROOT=Path.cwd()
DATA=ROOT/'output/20261027_wrd_main_v10'
RES=ROOT/'output/20261031_wrd_curation09/holdout/holdout_reservation.json'
CAP=DATA/'historical_v6_native_repair_01/TOOLS_CAPTURE_53.json'

SPECS={
'e2d506cd3f4eabeee6eae154':([10],[5,7], '执行当前已经写入的游戏自测脚本；本步仅运行诊断，不声称游戏或测试脚本已正确。'),
'3753dbff1b53e9b307fa971d':([2,6,8,10],[], '搜索工具当前不可用，改用真实公开书目元数据接口取得待筛文献；不能用标题或DOI存在性证明科学假说。'),
'adae12dd285bb0ca9f14cd4f':([2,12],[], '对先前实际检索返回的石斑鱼相关DOI核对作者、期刊和出版信息；本步只核书目元数据，不声称已阅读全文或验证论文观点。'),
'0ddec296a38c6ec24a2e9b18':([8,10,12],[], '网页搜索provider不可用，视频oEmbed探针返回200。本步尝试读取YouTube检索页提取真实候选ID；画面是否有人物讲解仍待实际检查。'),
'10cb6178ac2a09e2cfbbcf23':([8,10,12,14],[], '已有直接YouTube检索页ID反馈。编写并运行结构化元数据提取程序，去重候选并保留频道、时长等；不把元数据等同视频内容验收。'),
'84f39667be6fefa3fbc09266':([8,10,12],[13,15,17], '图片API不可用。当前已明确委托将三份既有本地HTML草图渲染成PNG；此局部变换不表示原文章及全部视觉要求已验收。'),
'af98d54fb39ba95526215440':([20],[13,15,17], '三份HTML草图已产生非空PNG。本步对封面提交实际视觉检查，不能声称所有图片内容已经通过。'),
'0da13410d543f90f6dcc4e35':([2],[], '将真实用户八镜头分镜整理成可执行的JSON素材计划，保持旁白原文、镜头顺序和规定时间段。当前仅交分镜资源，不声称图片、声音或成片已生成。'),
'ab410b79e6bdbf7bc6642f2f':([14,18],[11], '素材生成脚本已返回assets done，但尚未确认逐项结果。检查真实详细日志及素材目录，依据每项反馈判断是否失败，不信任包装脚本的结束字符串。'),
}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def h(text): return hashlib.sha256(text.encode()).hexdigest()
def text(message):
    value=message.get('content','')
    return value if isinstance(value,str) else '\n'.join(b.get('text','') for b in value if b.get('type')=='text')

def main(specs=None, output_stem='SCOPED_ACTION_CANDIDATES09', review_name='CANDIDATE09_REVIEW.json'):
    OUT.mkdir(parents=True,exist_ok=True)
    reservation=json.loads(RES.read_text(encoding='utf8'))
    reserved=set(reservation['reserved_source_ids']); components=set(reservation['reserved_source_scope_components'])
    closure_path=RES.parent/'PROTECTED_CURRENT569_REVOCATION_CLOSURE.json'
    closure=json.loads(closure_path.read_text(encoding='utf8'))
    reserved.update(closure['revoke_source_ids']); components.update(closure['revoke_source_scope_component_ids'])
    with gzip.open(DATA/'clean_inputs/source_scope.metadata.jsonl.gz','rt',encoding='utf8') as stream:
        scopes={r['source_id']:r for r in map(json.loads,stream)}
    owners={r['owner_id']:r for r in read('OWNER1321_EXACT_CONTENT.audit.jsonl.gz')}
    contexts={r['episode_id']:r for r in read('ORIGINAL_CONTEXTS_343.audit.jsonl.gz')}
    cap=json.loads(CAP.read_text(encoding='utf8')); core={'apply_patch','edit','exec','ls','process','read','write'}
    tools=[tool for tool in cap['tools'] if tool['function']['name'] in core]
    candidates=[]; manifest=[]
    for oid,(observations,resources,purpose) in (SPECS if specs is None else specs).items():
        owner=owners[oid]; context=contexts[owner['episode_id']]; index=owner['source_message_index']; original=owner['target_message_original']
        assert not reserved.intersection(owner['source_ids'])
        assert all(scopes[source]['status']=='TRAIN' and scopes[source]['component_id'] not in components for source in owner['source_ids'])
        assert all(i<index for i in observations+resources)
        evidence=[{'index':i,'message':context['messages'][i]} for i in observations]
        resource_messages=[{'index':i,'message':context['messages'][i]} for i in resources]
        task=text(context['messages'][0]).split('用户任务：')[-1].strip()
        prompt='当前明确委托的局部操作：'+purpose+'\n\n原任务（当前局部步骤不等于全部完成）：\n'+task+'\n\n'
        for entry in evidence:
            prompt+=f'已经收到的真实工具反馈（原消息{entry["index"]}，未改写）：\n{text(entry["message"])}\n\n'
        for entry in resource_messages:
            prompt+=f'在本步开始前已经实际提交写入的资源（原消息{entry["index"]}的完整原始工具参数；不是新造要求或已验证结论）：\n'
            prompt+=json.dumps(entry['message'].get('content',[]),ensure_ascii=False)+'\n\n'
        blocks=original.get('content',[])
        calls=[{'id':block['id'],'type':'function','function':{'name':block['name'],'arguments':json.dumps(block['arguments'],ensure_ascii=False,separators=(',',':'))}} for block in blocks if block.get('type')=='toolCall']
        assert calls and all(call['function']['name'] in core for call in calls)
        target={'role':'assistant','content':text(original),'reasoning_content':'','tool_calls':calls}
        packet={'schema_version':'wrd09-batch02-exact-action-review-packet-v1','owner':owner,'original_context':context,
                'original_target':original,'selected_before_observations':evidence,'selected_before_resources':resource_messages,
                'authorship':'NEW_CURATOR_FUNCTIONAL_DELEGATION_WITH_VERBATIM_OLD_ACTION_AND_OBSERVATIONS',
                'future_feedback_in_training_input':False,'original_internal_R_admitted':False,'whole_skill_KEEP':False}
        path=OUT/'packets'/f'{oid}.json'; path.parent.mkdir(exist_ok=True); dump(path,packet)
        candidate={'schema_version':'wrd09-batch02-functional-action-v1','id':'process09-batch02-'+oid,'owner_id':oid,
            'bank':'process09_batch02_action','stage':'B_local_resource_and_validation_action','split':'train',
            'source_ids':owner['source_ids'],'source_group_id':'process09_'+h('|'.join(sorted(owner['source_ids'])))[:20],
            'source_admission':'ADMIT','training_admitted':True,'root_main_admission':False,'requires_external_root_admission':True,
            'original226':False,'holdout12':False,'protected_sources_visible_prefix':False,'protected_source_ids':[],
            'original_episode_id':owner['episode_id'],'original_message_index':index,
            'original_target_sha256_sorted':owner['target_original_SHA256_sorted'],
            'source_context':{'path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':sha(path)},
            'original_native_prompt_equivalence_claimed':False,'original_system_capture':context['system_capture_status'],
            'student_view':'NEW_EXPLICIT_CORE7_FUNCTIONAL_STATE_WITH_EXACT_RECORDED_ACTION',
            'annotation_provenance':'CURATOR_SCOPE_ONLY; ORIGINAL_PUBLIC_TEXT_AND_TOOL_ARGS_VERBATIM; NO_INVENTED_R_OR_TOOL_RESULT',
            'actual_native_tool_dispatch':False,'loss_multiplier':0.25,'tools':tools,
            'tool_schema_provenance':{'path':str(CAP),'sha256':sha(CAP)},
            'is_full_autonomous_execution_demonstration':False,'is_qualified_KEEP_demonstration':False,
            'credit':purpose,'data_design_revision':'5.0.50','data_change_id':'ALG-20261031-02',
            'curation_cost':'UNKNOWN_NOT_ZERO','new_business_Teacher_Actor_calls':0,'training_started':False,
            'holdout_reservation_sha256':sha(RES),'teacher_original_R_supervised':False,
            'protected_revocation_closure_sha256':sha(closure_path),
            'rationale_provenance':'ORIGINAL_VISIBLE_PUBLIC_TEXT_ONLY_NOT_INTERNAL_R',
            'messages':[{'role':'system','content':'根据真实已收到状态完成当前委托的局部操作，不以工具退出码替代资源内容与业务正确性验收。'},
                        {'role':'user','content':prompt},target],
            'supervision_message_indices':[2],'message_loss_mask':[0,0,1],
            'approved_components':['A','D'] if target['content'] else ['A'],
            'target_content_unicode_exclusions':[],'target_code_unicode_exclusions':[],
        }
        candidates.append(candidate);manifest.append({'owner_id':oid,'target_index':index,'packet':str(path.relative_to(OUT)),'packet_sha256':sha(path),'scope':purpose})
    with gzip.open(OUT/(output_stem+'.jsonl.gz'),'wt',encoding='utf8') as stream:
        for row in candidates: stream.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    dump(OUT/review_name,{'status':'PENDING_ROOT_QA_NOT_ADMISSION','candidates':manifest,'original_R':0,'new_R':0,'full_autonomy':0,'KEEP':0,'new_business_calls':0,'training_runs':0,'reservation_sha256':sha(RES),'script_sha256':sha(__file__)})
    print('Candidate views',len(candidates),'not admission')

if __name__=='__main__': main()
