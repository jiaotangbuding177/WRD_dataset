"""Freeze exact 14 follow-up views with content-level exclusion proofs.

This script never executes historical commands, calls a model or admits the bank.
"""
import gzip,json
from process_batch02_candidates import main as build,SPECS,OUT,sha,h,dump

EXTRAS={
'716e4c7590d78258c0c23aa2':([82,88,92,94],[], '根据已收到的税务官网前端脚本与搜索接口反馈，检索指定政策的官方标题和URL。仅执行检索定位，不根据搜索标题推断政策适用性、时效或税法结论。'),
'44d544efa0510fb714da6712':([2,6,10,12],[], '仅根据已提供的2026-10-23历史页面快照，整理DeepSeek Flash、Claude Opus 4.8及本次明确选定的Claude Fable 5.1价格表并比较单价。页面截断不能证明某项不存在，不将历史快照当作今天的实时价格。未证实的绝对断言不获监督。'),
'ac76ab7ead15378debb0e555':([4,6],[], '将已实际读到的30条用户请求整理为产物来源清单，区分请求、计划、用户粘贴的清单和实际文件证据。工作区检查只覆盖已执行find范围，不能推出所有路径不存在文件。'),
'332f3502d0b2f9f687a7a415':([2],[], '逐条审阅已提供的53条请求，按当前财务分析任务写缺件报告；没有真实财务数值时如实说明缺件，不虚构财务指标。'),
'2bfade5dc8a0e564bb4fc367':([2],[], '按照实际源请求中的修订指令改写八镜头分镜：真实实拍、专用美猎弓和泡沫箭头/护具/每人5支箭、约半个足球场；保留原顺序、时间段及镜头7/8文字。仅交文字修订，不声称成片完成或活动绝对安全。'),
}

def occurrences(value,needle,reason):
    out=[];start=0
    while True:
        start=value.find(needle,start)
        if start<0:break
        end=start+len(needle)
        out.append({'start':start,'end':end,'text':needle,'text_sha256':h(needle),'reason':reason})
        start=end
    assert out,needle
    return out

def merge(value,ranges):
    merged=[]
    for reg in sorted(ranges,key=lambda r:r['start']):
        if merged and reg['start']<merged[-1]['end']:
            prev=merged[-1];prev['end']=max(prev['end'],reg['end']);prev['reason']+='; '+reg['reason']
            prev['text']=value[prev['start']:prev['end']];prev['text_sha256']=h(prev['text'])
        else:merged.append(dict(reg))
    return merged

def main():
    specs=dict(SPECS);specs.update(EXTRAS)
    build(specs,'SCOPED_CANDIDATES_FINAL14','CANDIDATE_FINAL14_BASE_REVIEW.json')
    path=OUT/'SCOPED_CANDIDATES_FINAL14.jsonl.gz'
    rows=list(map(json.loads,gzip.open(path,'rt',encoding='utf8')))
    byid={r['owner_id']:r for r in rows}
    reports=[]
    for oid in EXTRAS:
        row=byid[oid];target=row['messages'][2]
        row['target_original_code_sha256']=None
        row['original_recorded_action_owner']=oid
        if oid=='716e4c7590d78258c0c23aa2':continue
        call=target['tool_calls'][0];args=json.loads(call['function']['arguments'])
        assert call['function']['name']=='write' and isinstance(args['content'],str)
        value=args['content'];code=[];public=[]
        row['target_tool_call_id']=call['id'];row['target_original_code_sha256']=h(value)
        row['exclusion_target_field']='messages[2].tool_calls[0].function.arguments.content'
        if oid=='332f3502d0b2f9f687a7a415':
            code+=occurrences(value,'约 70 条','Actual source has 53 requests, not approximately 70; preserve wrong historical text at loss0.')
        elif oid=='2bfade5dc8a0e564bb4fc367':
            code+=occurrences(value,'箭不会伤人','Absolute injury-free assurance is not established; retain user-provided creative revision but no safety guarantee gold.')
        elif oid=='44d544efa0510fb714da6712':
            for needle in [
                'Anthropic 官方定价文档中**不存在仅名为 "Fable" 的模型**，',
                '官方现役名称为 ',
                '上一代为 ',
                '官方文档现役模型名为 ',
                '缓存写入不单独计价（官方仅列缓存命中/未命中两档输入价）。',
                '无高峰/非高峰时段差异；上下文长度未在官方定价页列示（缺失项，未估算）。',
                '官方现役名称：',
                '| 缓存写入 | 不单独计价 | $6.25（5 分钟档） | $12.50（5 分钟档） |',
                '4. **缓存写入**：仅 Anthropic 两款模型对缓存写入单独计价（Opus 4.8 $6.25 / Fable 5.1 $12.50 每 MTok，5 分钟档）；DeepSeek 官方定价页无缓存写入计费项，属口径差异而非缺失。',
                '5. **计价结构差异**：DeepSeek Flash 是三者中唯一分高峰/非高峰时段计价的模型（非高峰为高峰半价）；Anthropic 两款为全天统一价、无时段折扣。',
                '- "Fable" 精确名称的模型不存在，已按官方现役最新一代 Claude Fable 5.1 对应，另附上一代 Fable 5 价格供核对；如用户原意指其他模型，需另行确认。',
                '- Anthropic 官方定价页未列示 Claude Opus 4.8 与 Fable 的上下文长度字段，本文件标注为缺失，未做估算。',
            ]:
                code+=occurrences(value,needle,'A table/partial page establishes displayed prices, not exhaustive absence, latest/retired generation, fee exclusion or time-independent policy.')
            public+=occurrences(target['content'],'"Fable" 精确名称不存在，官方现役为 ','Truncated official capture does not establish global name absence or latest-model status.')
            public+=occurrences(target['content'],'上一代 ','Snapshot lists both rows but does not establish generation status.')
            public+=occurrences(target['content'],'现役模型 ','Snapshot row alias is established; active/latest status is not independently verified.')
        elif oid=='ac76ab7ead15378debb0e555':
            for needle,why in [
                ('26 条','Source requests array has 30 entries, not 26.'),
                ('已检查当前工作区（/workspace），未发现任何实际产物文件（无 .md 文章、无图片）。','Bounded find maxdepth3 and excluded subtrees cannot prove global artifact absence.'),
                ('当前工作区无文件','Bounded find cannot prove global absence.'),
                ('当前工作区也无图片文件','Bounded find cannot prove global image absence.'),
                ('表明图片曾生成但用户一度找不到','Asking where/show image does not prove generation happened.'),
                ('用户在请求"帮我列出来上面这些产物"（msg_104）后贴回了助手给出的清单，清单中明确列出第③–⑧项共 6 篇文章及文件名、大小。编号从③开始，暗示此前还有①②两项，但清单中未显示其名称，无法对应。','Pasted source has first filename then numbered4-8; explicit3 and assistant authorship/earlier1-2 provenance are not proven.'),
                ('msg_116 清单编号从③开始，**①②两项产物存在与否及名称无从得知**（有可能对应第一节中定时任务的两类文档，也可能为更早生成的两篇文章，记录不足，不作认定）。','Source first filename lacks explicit3; absence1-2 inference not evidence.'),
                ('msg_84（"按 A 型人/B 型朋友的角度重写并附原文链接"）','Source84 uses general interpersonal analogy; exact A/B wording appears153, so this attributed quotation is false.'),
                ('msg_104 + msg_116：助手列出 6 篇文章清单','Only user-pasted list is available; assistant response itself is not in this source.'),
                ('会话中生成的文章','Source is requests and user-pasted filenames, not actual generation receipts.'),
                ('会话中生成的','Requests do not prove actual generated resources.'),
            ]:
                if needle=='会话中生成的':continue
                code+=occurrences(value,needle,why)
            public+=occurrences(target['content'],'工作区中除输入文件外没有任何实际产物文件，','Bounded find does not establish exhaustive workspace absence.')
        row['target_code_unicode_exclusions']=merge(value,code)
        row['target_content_unicode_exclusions']=merge(target['content'],public)
        reports.append({'owner_id':oid,'tool_call_id':call['id'],'target_field':row['exclusion_target_field'],
            'target_original_code_sha256':h(value),'content_characters':len(value),
            'code_exclusions':row['target_code_unicode_exclusions'],'public_text_exclusions':row['target_content_unicode_exclusions'],
            'whole_code_or_document_business_correctness_claimed':False,
            'source_snapshot_only_not_current_external_truth':True})
    with gzip.open(path,'wt',encoding='utf8') as stream:
        for row in rows:stream.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    dump(OUT/'CANDIDATE_FINAL14_EXCLUSION_REVIEW.json',{'status':'FROZEN_CANDIDATES_PENDING_ROOT_SEMANTIC_AND_TOKEN_QA','count':len(rows),
        'candidate_file':str(path.resolve()),'candidate_sha256':sha(path),'write_content_reviews':reports,
        'target_arguments_exact_original_values':True,'new_functional_state_authored':True,
        'original_R':0,'new_R':0,'full_autonomy_gold':0,'KEEP_gold':0,'training_started':False,'business_calls':0,
        'curation_cost':'UNKNOWN_NOT_ZERO','script_sha256':sha(__file__)})
    print('Frozen candidates:',len(rows),'masked content targets:',len(reports))

if __name__=='__main__':main()
