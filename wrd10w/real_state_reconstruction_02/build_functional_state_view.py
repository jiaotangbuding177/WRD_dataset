"""Create functional input view 02; keep view 01 immutable and auditable."""
from copy import deepcopy
import gzip, hashlib, json, re
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
OLD=BASE/'real_state_reconstruction_01'
def sha(b):return hashlib.sha256(b if isinstance(b,bytes) else b.encode('utf-8')).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text('utf-8-sig'))
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pins(folder):
    return [{'relative_path':p.relative_to(folder).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
            for p in sorted(folder.rglob('*')) if p.is_file()]

before=pins(OLD)
old_rows=[json.loads(l) for l in gzip.open(OLD/'real_state_tasks.jsonl.gz','rt',encoding='utf-8-sig')]
receipt=load(OLD/'SOURCE_RECEIPTS.json')
for f in receipt['files']:
    p=OLD/f['archive_object']; q=HERE/f['archive_object']
    b=p.read_bytes(); assert sha(b)==f['sha256'] and len(b)==f['bytes']
    q.parent.mkdir(parents=True,exist_ok=True)
    if q.exists(): assert q.read_bytes()==b
    else:q.write_bytes(b)
new_receipt=deepcopy(receipt)
new_receipt['schema']='wrd-real-state-exact-source-closure-v2-functional-view'
new_receipt['previous_candidate_view_receipt']={'path':str(OLD/'SOURCE_RECEIPTS.json'),'sha256':sha((OLD/'SOURCE_RECEIPTS.json').read_bytes())}
new_receipt['previous_candidate_tasks']={'path':str(OLD/'real_state_tasks.jsonl.gz'),'sha256':sha((OLD/'real_state_tasks.jsonl.gz').read_bytes())}
new_receipt['same_source_resources_and_actual_action_owners_as_01']=True
new_receipt['candidate_views_01_and_02_must_not_both_receive_loss']=True
save(HERE/'SOURCE_RECEIPTS.json',new_receipt)

common='''总目标：从获准的三份会话沉淀可靠、可复用的事实保真成稿 skill，验证资源可靠性，并据实际消费证据决定交付或继续修订。
权限：可以本地读取、执行CLI、自测，并在 /workspace/outputs 内做必要局修；没有外发、远端写入或创建子Agent的权限。
工作目录为 /workspace，Python为 /opt/eval-venv/bin/python，OpenClaw版本2026.9.5。会话总预算1800秒，max_tokens32768；截至当前的已用量和剩余额度均为UNKNOWN。当前无活跃exec或子Agent。
候选尚未冻结，尚无独立业务消费结果。原21项测试曾通过，但不足以证明资源完整正确。独立检查使用明确虚构的结构反例。
'''
states={
    'reproduce':'原资源及原测试已复制到输出目录，得到SETUP_OK，原版与输出副本validator的SHA相同。三个原版失败报告及完整反例见下。',
    'repair':'原CLI的三反例结果已返回：合法跨年actual/goal同值被fact_type_conflict拒绝，嵌套evidence_refs为string及[42]都被结构通过。输出副本validator仍是原版，尚未编辑。',
    'retest':'edit已返回成功替换3块。当前validator版本SHA为86336921615cb2d15ae7c7c531fa81a457ea201e353223e79de4900445b59f58，完整内容见下。该版尚未测试，不能继承旧版通过结果。',
}
system='''你在用户的原生OpenClaw环境中制作可复用技能。根据总目标、当前资源和已得到的观察，选择下一步有用的本地动作。精确编辑前应掌握文件内容；只有路径和SHA时应先读取。区分局部结构验证、语义质量及独立业务消费的证据。'''

out=[]; changes=[]
for old in old_rows:
    r=deepcopy(old)
    key=old['stage'].rsplit('_',1)[1]
    oldinput=old['messages'][1]['content']
    blocks=re.findall(r'<recorded_file path=("[^"\n]+") sha256=("[a-f0-9]+") origin=("[^"]+")>\n(.*?)\n</recorded_file>',oldinput,re.S)
    blockmap={json.loads(p):{'sha256':json.loads(s),'origin':json.loads(origin),'text':text} for p,s,origin,text in blocks}
    feedback_path='/workspace/inputs/independent/actual_repair_feedback.json'
    feedback=json.loads(blockmap[feedback_path]['text'])
    removed_keys=['schema','origin','parent_job_id','parent_job_sha256']
    functional_feedback={k:v for k,v in feedback.items() if k not in removed_keys}
    state=common+'\n当前状态：'+states[key]+'\n\n独立检查反馈：\n'+json.dumps(functional_feedback,ensure_ascii=False,indent=2)+'\n'
    # Only functional workspace references remain in input. Capture identities,
    # Windows audit paths, provenance labels and authorship stay in metadata.
    available=[]
    for p in ('SKILL.md','schemas/draft.schema.json','schemas/fact_ledger.schema.json','templates/section_templates.md'):
        mounted='/workspace/inputs/previous_skill/'+p
        hit=next(f for f in receipt['files'] if f.get('mount')==mounted)
        available.append({'path':'/workspace/outputs/skill/'+p,'sha256':hit['sha256']})
    state+='\n下列技能资源可访问，当前未读取：\n'+json.dumps(available,ensure_ascii=False,indent=2)+'\n'
    state+='三份原会话及源字段材料位于 /workspace/inputs/conversations/ 和 /workspace/inputs/a_stage/。原21项测试的runner和fixtures已复制到 /workspace/outputs/tests/；若需要依赖其中的具体内容，应先读取。\n'
    retained=[]
    for p,s,origin,text in blocks:
        path=json.loads(p)
        if path==feedback_path:continue
        assert sha(text)==json.loads(s)
        state+='\n<file path='+p+' sha256='+s+'>\n'+text+'\n</file>\n'
        retained.append({'path':path,'sha256':json.loads(s)})
    observations=re.findall(r'<delivered_native_observation[^>]+>\n(.*?)\n</delivered_native_observation>',oldinput,re.S)
    for text in observations:
        state+='\n<observation>\n'+text+'\n</observation>\n'
    r['id']=old['id'][:-3]+'_02'
    r['messages']=[{'role':'system','content':system},{'role':'user','content':state},deepcopy(old['messages'][2])]
    r['student_view']='NEW_AUTHORED_FUNCTIONAL_REAL_STATE_CORE7_VIEW_02'
    r['functional_view_revision']=2
    r['source_receipts']={**old['source_receipts'],'path':str(HERE/'SOURCE_RECEIPTS.json'),'sha256':sha((HERE/'SOURCE_RECEIPTS.json').read_bytes())}
    r['necessary_input_resource_paths']=[p for p in old['necessary_input_resource_paths'] if p!=feedback_path]
    r['functional_feedback_projection']={
        'original_file_path':feedback_path,'original_exact_text_sha256':blockmap[feedback_path]['sha256'],
        'removed_source_metadata':{k:feedback[k] for k in removed_keys},
        'retained_functional_fields':list(functional_feedback),
        'input_is_new_user_feedback_section_not_claimed_as_exact_original_file':True,
        'original_full_feedback_preserved_in_source_receipts':True}
    r['previous_candidate_view']={'record_id':old['id'],'tasks_path':str(OLD/'real_state_tasks.jsonl.gz'),
        'tasks_sha256':sha((OLD/'real_state_tasks.jsonl.gz').read_bytes()),'record_sha256':sha(js(old)),
        'mutual_exclusion':'01 and 02 are alternative views of the same 3 action owners; never both activate or add their loss.'}
    r['input_provenance_moved_to_metadata']={
        'new_authored_state_task':True,'same_native_input_claim':False,'same_original_R_claim':False,
        'new_rationale_author':'NEW_AI_SILVER_AUTHOR','author_cost':'UNKNOWN_NOT_ZERO',
        'exact_native_cutoff':old['native_delivered_cutoff'],
        'original_block_origins':{p:b['origin'] for p,b in blockmap.items()},
        'original_observation_capture_attributes_removed_from_input':True,
        'all_retained_file_texts_and_observation_contents_byte_identical_to_01':True}
    changes.append({'record_id':r['id'],'previous_record_id':old['id'],'functional_stage':key,
                    'old_system_sha256':sha(old['messages'][0]['content']),'new_system_sha256':sha(system),
                    'old_user_sha256':sha(oldinput),'new_user_sha256':sha(state),
                    'new_rationale_and_original_action_unchanged':True,
                    'retained_complete_files':retained,'retained_actual_observation_content_sha256':[sha(t) for t in observations]})
    save(HERE/'records'/(r['id']+'.json'),r)
    out.append(r)
with gzip.open(HERE/'real_state_tasks.jsonl.gz','wt',encoding='utf-8',newline='\n') as f:
    for r in out:f.write(js(r)+'\n')
assert before==pins(OLD),'01_changed_during_02_build'
save(HERE/'VIEW_01_IMMUTABILITY_CHECK.json',{'status':'PASS','files':before,'after_equals_before':True})
save(HERE/'FUNCTIONAL_VIEW_PROJECTION_REVIEW.json',{
    'schema':'wrd-functional-real-state-view-02-review-v1','status':'PASS_SELF_REVIEW_PENDING_ROOT',
    'reviewer_is_new_state_author':True,'changes':changes,
    'task_provenance_source_capture_and_authorship_metadata_not_in_input':True,
    'original_resource_files_with_functional_identifiers_remain_exact':True,
    'actual_tool_return_contents_unchanged':True,'future_credit_not_in_input':True,
    'same_three_action_owners':True,'one_view_only_for_training':True,
    'original_01_unchanged':True,'new_model_calls':0,'native_actions_reexecuted':0,'training_started':False})
print(js({'records':len(out),'owners':len({r['target_owner']['exposure_owner_id'] for r in out}),'view01_unchanged':True}))
