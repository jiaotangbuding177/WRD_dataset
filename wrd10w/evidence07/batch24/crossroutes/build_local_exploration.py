"""Three disclosed new states with verbatim original pre-protection read actions."""
from pathlib import Path
import json,gzip,hashlib
from jsonschema import Draft202012Validator
from recover_crossroutes import R,O,V9,REC,rows,pin,h,can,messages,txt,calls,args,zr,save

def main():
 source=R/'output/20261027_wrd_main_v10'; sp=source/'clean_inputs/source_scope.metadata.jsonl.gz'
 scopes={x['source_id']:x for x in rows(sp)}
 eps={x['episode_id']:x for x in rows(V9/'recovery/episodes.metadata.jsonl.gz')}
 spec=[('ep_1de03a2b0f4590a448d9',3,2),('ep_cbd039ef2f0c6eb1c1fb',3,2),('ep_b58b64f773ea15ec35e6',5,4)]
 wanted={x[0] for x in spec}; ctx={}
 for x in rows(V9/'recovery/episodes.contexts.jsonl.gz'):
  if x['episode_id'] in wanted:ctx[x['episode_id']]=x
 targets={x['id']:x for x in rows(O/'TARGET_DECISIONS_AND_ORIGINAL_BODIES.jsonl.gz')}
 schema_path=R/'output/20261025_wrd_training_dataset/bundle/tools/resources/native_coding_tools_97a0.json'
 prov_path=schema_path.with_suffix('.provenance.json')
 schema=json.loads(schema_path.read_text(encoding='utf-8'))
 mp=source/'TRAINING_MANIFEST.json';manifest=json.loads(mp.read_text(encoding='utf-8'));active=[]
 for f in manifest['actual_train_files']:active.extend(rows(source/f['path']))
 out=[]; proofs=[]
 for eid,i,lastobs in spec:
  t=next(x for x in targets.values() if x['episode_id']==eid and x['source_message_index']==i)
  assert t['current_decision']=='HOLD_ANCESTRY_NOT_CLOSED' and i<t['protected_dependency_observation_index']
  ep=eps[eid];ms=messages(ep['source_native']['path']);original=ms[i]['message'];cc=calls(original)
  assert len(cc)==1 and cc[0]['name'] in ['read','exec'];call=cc[0];a=args(call)
  fn=next(x for x in schema if x['name']==call['name']);Draft202012Validator(fn['parameters']).validate(a)
  if call['name']=='exec':assert a=={'command':'cat /workspace/inputs/route_card.json'}
  assert all(b.get('type')=='toolCall' for b in original['content']) and not ctx[eid]['reasoning_overlays_same_response_id']
  sourceids=sorted(t['original_target_metadata']['source_ids']);assert sourceids and all(scopes[s]['status']=='TRAIN' for s in sourceids)
  past=[{'message_index':j,'event_line':ms[j]['event_line'],'message':ms[j]['message'],'message_sha256':h(can(ms[j]['message']))} for j in range(i)]
  earlier_observation=ms[lastobs]['message'];obs=txt(earlier_observation)
  p=Path(ep['source_original_path']).parents[1]/'workspace/inputs'
  desired=a.get('path','/workspace/inputs/route_card.json');name=Path(desired).name
  assert name in str(ms[0]['message']['content'])
  prior_same_read=any(args(c).get('path')==desired for z in ms[:i] for c in calls(z['message']))
  assert not prior_same_read
  for row in active:
   encoded=json.dumps(row,ensure_ascii=False,separators=(',',':'))
   assert call['id'] not in encoded and t['id'] not in encoded
  # This is explicitly a different declared student state, not a recovered
  # original system or an assumption that the teacher saw this shorter prompt.
  request='请继续把当前已选的工作路线制作为可复用技能。当前目录为/workspace；材料在/workspace/inputs，交付目录为/workspace/outputs。允许通过提供的原生工具读取已投递文件并按要求写交付；不要读取凭据。运行预算和未提供的文件正文均为UNKNOWN。\n'
  request+='先按要求阅读making_lineage.json、route_card.json、generation.md和making_input_index.json，再决定后续操作。目录或路径列出不等于正文已经读过；未知内容不能假定，工具返回成功也不等于资源正确。\n'
  observed_metadata=json.loads(obs)
  assert observed_metadata.get('attempt')==2 and observed_metadata.get('previous',{}).get('skill_present') is True
  request+='当前已经读到制作接续说明：这是第二次接续，说明中标记有旧技能；旧技能和反馈正文尚未读取，效果未知。route_card.json、generation.md和making_input_index.json也尚未读取。这里只依据已读说明安排下一次读取，不据此认定旧技能正确。'
  request+='\n请按上述阅读顺序继续一次工具操作。不要提前引用尚未读到的路线、旧程序、反馈内容或结果。'
  target={'role':'assistant','content':'','tool_calls':[{'id':call['id'],'type':'function','function':{'name':call['name'],'arguments':json.dumps(a,ensure_ascii=False,separators=(',',':'))}}]}
  owner='native_tool_call:'+call['id'];rid='batch24_local_read:'+t['id']
  row={'schema_version':'wrd-new-state-original-action-local-exploration-v1','id':rid,'bank':'local_exploration_pre_protection_batch24',
   'stage':'B_local_exploration_pre_protection','source_ids':sourceids,'source_group_id':scopes[sourceids[0]]['component_id'],'split':'train',
   'source_admission':'ADMIT_LOCAL_PRE_PROTECTION_STATE_PENDING_ROOT','training_admitted':False,
   'messages':[{'role':'system','content':'你负责使用提供的工具从当前可见材料制作可复用技能。先读必要输入，再依据实际反馈推进；不得把未知内容当作事实。'},{'role':'user','content':request},target],
   'tools':[{'type':'function','function':fn}],'message_loss_mask':[0,0,1],'approved_components':['A'],'loss_multiplier':.25,
   'annotation_provenance':'NEW_AUTHORED_FUNCTIONAL_STATE_WITH_VERBATIM_ORIGINAL_TOOL_ACTION_NOT_ORIGINAL_NATIVE_INPUT',
   'target_owner':{'canonical_original_action_owner_id':owner,'original_tool_call_id':call['id'],'canonical_original_target_id':t['id'],
      'original_episode_id':eid,'original_message_index':i,'owner_exposure_components':['A'],'original_R_owner':None},
   'evidence':{'native':ep['source_native'],'original_event_line':ms[i]['event_line'],'original_message_sha256_sorted':h(can(original)),
      'verbatim_original_tool_arguments_sha256':h(can(a)),'past_observation_index':lastobs,'past_observation_sha256':h(can(earlier_observation)),
      'route_protection_observation_index':t['protected_dependency_observation_index'],'protected_future_response_in_input':False,
      'captured_original_system':ctx[eid]['system_capture_status'],'original_system_or_schema_claimed_complete':False,
      'new_schema':pin(schema_path),'new_schema_provenance':pin(prov_path),'scope':pin(sp),'baseline_manifest':pin(mp)},
   'source_admission_explanation':'Initial functional directive/path names plus metadata or directory listing only; before actual protected route receipt. Technical prior coverage metadata is not resource semantic success.',
   'actual_native_tool_dispatch':False,'original_action_was_actually_dispatched':True,'future_outcomes_used_as_input':False,
   'original_R_positive_tokens':0,'full_skill_success_positive_loss':False,'qualified_skill_KEEP':False,'single_native_autonomous_demonstration':False,
   'curriculum_role':'BOUNDED_INPUT_EXPLORATION_ONLY_NOT_COMPLEX_PIPELINE_MAIN_VOLUME','training_started':False,'curation_cost':'UNKNOWN_NOT_ZERO'}
  # Exact next tool ACK is audit-only; it is never appended to the new input.
  proofs.append({'id':rid,'past_original_messages_complete':past,'original_target':original,'actual_tool_feedback_audit_only':t['actual_tool_feedback'],
    'facts':[{'claim':'Requested file was explicitly listed and reading order instructed','original_user_message_index':0,'original_user_sha256':h(can(ms[0]['message']))},
      {'claim':'Prior directory / metadata observation already delivered','observation_message_index':lastobs,'observation_sha256':h(can(earlier_observation))},
      {'claim':'Next requested input body not yet read','prior_read_same_path':prior_same_read},
      {'claim':'No original R loss assigned','native_target_only_one_toolCall':True,'same_response_R_overlays':0},
      {'claim':'Old native system missing so declared new interface used','actual_original_system_capture_status':ctx[eid]['system_capture_status']},
      {'claim':'Actual original tool args satisfy provided native97a0 schema','schema_validation':'PASS'},
      {'claim':'Original226/H/static source IDs excluded and no matching canonical owner or actual call ID occurs in active530','active_rows_scanned':len(active),'status':'PASS'}],
    'scope_source_ids':sourceids,'scope_statuses':{s:scopes[s]['status'] for s in sourceids},'new_input_sha256':h(request.encode()),
    'new_input_has_future_tool_message':False,'root_admission_required':True})
  out.append(row)
 zr('LOCAL_EXPLORATION.raw.jsonl.gz',out);zr('LOCAL_EXPLORATION_PROOFS.jsonl.gz',proofs)
 save('LOCAL_EXPLORATION_AUTHOR_REVIEW.json',{'status':'THREE_LOCAL_READ_PROJECTIONS_PENDING_ROOT_COMPILATION',
  'rows':3,'source_ids':sorted({s for x in out for s in x['source_ids']}),'tools':'2 read and1 exec cat, native97a0 factory capture',
  'original_R_targets':0,'original_actions_projected_into_new_states':3,'original_system_complete_claimed':False,
   'scope':'Local exploration only, not resource construction, semantic QA, closure or autonomous workflow; input projects only attempt2 and previous skill-present metadata, not audit IDs or research flags',
  'no_training_or_business_run':True,'script':pin(__file__),'schema':pin(schema_path),'provenance':pin(prov_path)})
 print(json.dumps({'local_read_candidates':len(out),'new_original_R':0,'active_rows_owner_checked':len(active)}))
if __name__=='__main__':main()
