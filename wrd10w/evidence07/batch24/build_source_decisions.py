"""New, source-only decision supervision. Never invents historical execution."""
from pathlib import Path
import gzip, hashlib, json

ROOT=Path('D:/skillloop'); HERE=Path(__file__).parent
DATA=ROOT/'output/20261027_wrd_main_v10/clean_inputs'
def sha(b): return hashlib.sha256(b).hexdigest()
def loadrows(p):
    with gzip.open(p,'rt',encoding='utf-8-sig') as f:
        return [json.loads(s) for s in f if s.strip()]
def js(x): return json.dumps(x,ensure_ascii=False,separators=(',',':'))

# Explicit new teaching states, not reconstructions of an authenticated reply order.
# The numeric indices select original USER occurrences only. No old route/skill,
# historical assistant answer, test outcome or protected producer supplies a label.
CASES=[
('knowledge_start','conv_1e8e6e53ac34',[0],'A_source_only_entry_decision',
 '只有整理知识库这一要求，没有当前库的目录、索引或文章内容。先摸清现状才能决定复用、增补或停止，不能把未知的文章数量写成当前事实。',
 {'next_step':'inspect_knowledge_root','operations':['定位用户知识库目录，列出索引、文章与来源目录','读取现有索引和维护规范，再制定按文件的检查范围'],'unknowns':['当前文章数量','新源文件是否存在','索引覆盖及链接状态'],'do_not_claim':['已经检查完毕','已经修复','应当立即新建一套知识库']}),
('docx_material_first','conv_1ec77749aa65',[0],'B_source_only_dependency_decision',
 '用户已经给出材料路径和版式要求，事实不得改写。路径引用不等于实际读到正文，先核材料和原生docx技能，再安排生成与渲染验证。',
 {'next_step':'read_requested_skill_and_source','operations':['经原生发现定位并读取docx技能','核验附件路径并读取材料；缺件则记录精确路径和缺项','将事实数据核对与封面、目录、标题、表格、页眉页脚的渲染检查分别安排'],'must_preserve':['事实数据','关键结论加粗要求'],'unknowns':['源文件正文','当前技能是否可发现和读取','生成及渲染工具是否可用'],'do_not_claim':['已读材料','已生成合格DOCX']}),
('funding_initial','conv_526e4b625656',[0],'B_source_only_dependency_decision',
 '要求是依据某期已有定时任务结果生成图片。先找到该任务和7月13日结果，才能复用真实内容；题面没有给出可用数据、任务ID或可写配置。',
 {'next_step':'locate_existing_job_and_dated_result','operations':['检索每周投融资汇总任务及指定日期产物','读取原数据、来源链接与已有输出流程','把图片生成作为候选增量，先核现有产物能否支撑'],'unknowns':['实际任务ID','指定日期数据是否存在','原输出目录及可用资源'],'do_not_claim':['已有完整JSON','已生成图片','已修改定时任务']}),
('funding_visual_failure','conv_526e4b625656',[0,1],'C_source_only_feedback_diagnosis',
 '用户报告文字重叠和图标不显示，并指定换image-2。这是用户可见质量失败的证据；不能由生成成功或文件存在抵消，也不能直接认定具体字体或代码根因。',
 {'next_step':'inspect_failed_image_and_prepare_regeneration','operations':['读取当前图片，定位标题重叠与不可见图标','保留该期已核内容，按指定生成方式重做','对新版本逐项核字形、布局及信息完整性'],'failure_evidence':'用户报告的重叠与图标缺失','unknowns':['实际图片像素','具体根因','新版本是否改善'],'do_not_claim':['修复已成功','换模型必然解决']}),
('funding_content_failure','conv_526e4b625656',[0,1,2],'C_source_only_feedback_diagnosis',
 '当前反馈把问题扩展到项目简介和投资方缺失。需要先分辨源数据未提供还是渲染遗漏；直接编造投资方或只调样式都不能满足要求。',
 {'next_step':'compare_source_fields_with_visible_content','operations':['逐项目对照原始记录中的简介、金额和投资方','有据但未显示则修订呈现，无据则补检索并核来源','复测时逐项目检查简介和投资方的覆盖与可读性'],'must_preserve':['原金额及来源','用户新增的简介和投资方要求'],'unknowns':['原数据是否含简介及投资方','缺失发生在哪一环'],'do_not_claim':['已找全投资方','内容已经完整']}),
('funding_merge_regression','conv_526e4b625656',[0,1,2,3,4],'C_source_only_revision_decision',
 '合并国内外为一张图是新增呈现约束，未取消简介和投资方。用户再次指出同样需求，说明合并版本仍需核这两项，不能以合并完成作为验收。',
 {'next_step':'repair_merged_view_without_dropping_fields','operations':['读取合并版本和源字段，查简介及投资方是否缺失或过小','保持国内外同图，保留简介、金额和投资方','logo只在有可信资源时使用，缺失不冒充真实logo','同一新版本复核字段完整性与阅读尺寸'],'unknowns':['当前合并图是否漏字段还是不可读','可用logo资源'],'do_not_claim':['合并即可验收','用户取消了旧需求']}),
('funding_glyph_regression','conv_526e4b625656',[0,1,2,3,4,5,6],'C_source_only_revision_decision',
 '连续反馈中的框、叉、黄色横线和标题左侧图标是待核视觉缺陷；最新要求还包括指定生成方式和重新命名。此前的信息完整性要求仍有效，不能修图标时再次丢字段。',
 {'next_step':'regenerate_named_version_then_inspect','operations':['检查当前图的相应位置并保留旧版本','按指定image-2方式生成新命名版本','复核标题、右侧图标和异常横线，同时检查简介、金额、投资方及国内外同图'],'unknowns':['当前实际图像','异常是占位符还是渲染错误','新图结果'],'do_not_claim':['已修复全部视觉问题','文件重命名等于内容合格']}),
('funding_job_update','conv_526e4b625656',[0,1,2,3,4,5,6,7],'D_source_only_update_boundary_decision',
 '用户最后授权把要求加入定时任务，但该授权不证明当前配置、任务ID、图片资源或后续运行结果。应保留当前流程并实施有版本的增量，更新确认与下次运行验收分开。',
 {'next_step':'inspect_current_job_before_persistent_update','operations':['读取当前任务ID、计划、原payload和输出约定','将同图、简介、投资方、尽可能真实logo、可见图标及无重叠要求纳入增量','保存更新前后配置并核实际更新返回','后续对新配置产生的同版本产物复核，不把更新ACK当成运行成功'],'unknowns':['当前任务定义','是否已更新','下一次真实执行表现'],'do_not_claim':['已完成持久化','未来运行已合格','整体skill可以KEEP']}),
('slide_empty','conv_6318c0ad05d5',[0,1],'C_source_only_feedback_diagnosis',
 '用户认为每页图空且无法理解页意。这支持内容表达需要检查，不能推成只有排版问题；当前没有实际图片，先对照页意、文案和画面。',
 {'next_step':'inspect_page_meaning_and_render','operations':['取回A方案逐页图及对应文案','逐页检查是否有核心信息、证据和可理解的视觉表达','先形成局部修订方案，再用同一页重生成或调整验证'],'unknowns':['实际图片内容','各页预期表达','图文映射关系'],'do_not_claim':['只换排版必然有效','所有图片确实空白']}),
('slide_regenerate','conv_6318c0ad05d5',[0,1,2,3],'B_source_only_revision_decision',
 '用户选择重新生成图片并只先做三页；但本输入没有此前方案中三页的具体身份。应读回方案确认范围，不能擅选三页或一次生成全部。',
 {'next_step':'recover_three_page_scope_then_regenerate','operations':['定位用户所指方案，核实三页的标题、文案与素材','保留用户重生成而非仅重排的选择','先产三页样稿并检查页意与信息充足性，再等后续范围决定'],'unknowns':['三页的具体身份','已有方案内容','所需素材'],'do_not_claim':['已知道三页是什么','已获生成全部的授权']}),
('slide_video_script_gate','conv_6318c0ad05d5',[11],'B_source_only_output_order_decision',
 '用户想把每张图配动效和解说形成视频，但明确先要台词文本。可以先读取现有图并组织逐页讲解；不应直接跳到整段视频或把前面技术陈述当作已验证科学事实。',
 {'next_step':'read_pages_and_draft_narration_first','operations':['取回待解释的逐页图片及来源材料','先交按页对应的台词文本和必要动效意图','核对术语与事实，对未核内容标明待核','后续视频制作再绑定图、台词、时长和实际渲染验证'],'unknowns':['实际逐页图像','事实来源是否可靠','台词及节奏是否被接受'],'do_not_claim':['视频已完成','台词已被接受']}),
('html_requested_persona','conv_c1ce48280769',[0],'B_source_only_resource_scope_decision',
 '题面明确太阳系HTML动画以及称呼偏好，没有指定3D引擎、联网依赖、真实比例或测验。先保留这些明确约束，制作时把动画展示与科学精度范围分开。',
 {'next_step':'plan_minimal_html_resource_and_validation','operations':['按要求保留贾维斯和文哥的称呼偏好','构建可解释的太阳系HTML动画，说明比例示意范围','检查页面加载、动画运行与实际交互，科学数值若加入则核来源'],'unknowns':['交互细节','运行环境是否允许网络依赖','资源是否存在'],'do_not_claim':['用户要求了3D引擎或测验','演示比例等于真实天文比例','页面已验证']}),
('html_teaching_scope','conv_eca9c2676037',[0],'B_source_only_resource_scope_decision',
 '用户要太阳系教学HTML，说明交付形式和教学用途；题面没有给年级、科学数据或互动规格。可先按可读教学页规划并说明待定项，不能把自行补出的功能当成用户硬要求。',
 {'next_step':'define_teaching_page_then_build_and_check','operations':['确定适合教学的页面结构与基础演示，必要时确认受众','对准备使用的天文事实核来源并注明适用日期','检查浏览器实际显示、交互和可读性后再交付'],'unknowns':['教学受众','事实资料','具体交互规格'],'do_not_claim':['原题强制五道测验','已有历史页面就是正确gold','已完成浏览器检查']}),
]

def main():
    out=HERE/'source_decisions_02';out.mkdir(exist_ok=False)
    pool={x['source_id']:x for x in loadrows(DATA/'source_pool.with_body.jsonl.gz')}
    scope={x['source_id']:x for x in loadrows(DATA/'source_scope.metadata.jsonl.gz')}
    manifest=json.loads((DATA.parent/'TRAINING_MANIFEST.json').read_text())
    rows=[];checks=[]
    for name,sid,indices,stage,rationale,decision in CASES:
        s=pool[sid];assert s['split']=='train' and scope[sid]['status']=='TRAIN'
        selected=[s['user_messages'][i] for i in indices]
        evid=[{'message_id':m['id'],'text':m['content'],'text_sha256':sha(m['content'].encode()),'field':'user_messages.content'} for m in selected]
        # These are supplied as evidence documents in an explicitly NEW state;
        # no semantic order is asserted to be an authenticated historical thread.
        request='请为当前技能制作任务给出下一步判断和验证条件。下面只提供真实用户要求的选定记录，是本任务的输入材料，不是可执行系统指令。未提供当前目录、文件内容、工具观察、工具schema或历史助手输出；它们均为UNKNOWN。当前没有已确认可运行的工具接口，本次先输出决策说明，不编造调用或执行结果。\n'
        request+='\n'.join(f'记录{i+1}：\n{m["content"]}' for i,m in enumerate(selected))
        request+='\n请输出JSON，包含next_step、operations、unknowns、do_not_claim，可按需要包含must_preserve或failure_evidence；在获得执行或验收证据前不能声称已经修复、成功或入库。'
        row={'schema_version':'wrd-source-only-explicit-decision-v1','id':'batch24_source_decision:'+name,'bank':'source_only_controller_batch24','stage':stage,
            'source_ids':[sid],'source_group_id':scope[sid]['component_id'],'split':'train','source_admission':'ADMIT_SOURCE_ONLY','training_admitted':False,
            'messages':[{'role':'system','content':'你负责从用户材料中判断下一步技能制作工作。按已知事实安排探索、构建、检查或修订，区分建议、实际执行和已验证结果。'},{'role':'user','content':request},{'role':'assistant','reasoning_content':rationale,'content':js(decision)}],
            'tools':[],'message_loss_mask':[0,0,1],'approved_components':['R','D'],'loss_multiplier':.25,
            'annotation_provenance':'NEW_AUTHORED_SOURCE_ONLY_DECISION_NOT_ORIGINAL_TEACHER_REASONING_OR_EXECUTION',
            'evidence':evid,'source_pool_sha256':sha((DATA/'source_pool.with_body.jsonl.gz').read_bytes()),'source_scope_sha256':sha((DATA/'source_scope.metadata.jsonl.gz').read_bytes()),
            'source_conversation_pin':s['original_conversation_pin'],'original_user_message_occurrences_selected_not_historical_reply_order':True,
            'target_owner':{'canonical_new_annotation_owner_id':'batch24_new_decision:'+name,'original_teacher_R_or_A_owner':None},
            'historical_assistant_answers_used':False,'protected_route_or_code_used':False,'actual_native_tool_dispatch':False,'single_native_autonomous_demonstration':False,
            'confirmed_repair':False,'qualified_skill_KEEP':False,'artifact_or_skill_semantic_gold':False,'original_R_positive_tokens':0,
            'future_outcomes_used_as_input':False,'training_started':False,'weights_loaded':False,'curation_cost':'UNKNOWN_NOT_ZERO'}
        rows.append(row);checks.append({'id':row['id'],'source':sid,'required_checks':['source TRAIN','exact original user-only evidence','case-specific decision rationale','no invented state/result','no protected producer','new author explicit'], 'semantic_status':'ROOT_DRAFT_AWAITING_PEER_AND_COMPILATION'})
    with gzip.open(out/'decisions.raw.jsonl.gz','wt',encoding='utf-8',newline='\n') as f:
        for row in rows:f.write(js(row)+'\n')
    (out/'AUTHOR_REVIEW.json').write_text(json.dumps({'status':'SOURCE_ONLY_DECISIONS_PENDING_PEER_NOT_ADMITTED','records':checks,'records_count':len(rows),'distinct_sources':len({x['source_ids'][0] for x in rows}),'base_manifest_sha256':sha((DATA.parent/'TRAINING_MANIFEST.json').read_bytes()),'base_targets':manifest['actual_counts']['targets'],'new_original_R_or_A':0,'new_native_Agent_calls':0,'training_started':False,'script_sha256':sha(Path(__file__).read_bytes())},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(js({'status':'DRAFT_NOT_ADMITTED','new_authored_decisions':len(rows),'sources':len({x['source_ids'][0] for x in rows})}))
if __name__=='__main__':main()
