"""Offline WRD coordination annotations from frozen stage states.

This writes training examples. It does not implement or run an Agent loop.
Original visible text, program-rule annotations and synthetic rule states are
separate. Every training admission defaults closed until source evidence passes.
"""
from __future__ import annotations

import collections
import argparse
import gzip
import hashlib
import io
import itertools
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / 'output/20261025_wrd_training_dataset/bundle'
OUT = ROOT / 'output/20261026_wrd_dataset_v9/coordination'
BASE_OUT = OUT
V6 = ROOT / 'output/20261026_wrd_lineage_v6/controlled'
V9 = ROOT / 'output/20261026_wrd_dataset_v9/outcomes'
STAGE_NAMES = {'routes.json','screen.json','tasks.json','development_tasks.json','making.json','review.json'}
SYSTEM = '''你在原生OpenClaw会话中协调WRD技能沉淀。依据当前可见状态输出下一步计划JSON，字段为next_stage、args、decision_basis、evidence_refs。计划不是工具执行回执；实际工作必须继续使用同一原生环境的发现、读取、工具和会话循环。判断真实资源可靠性、交付质量与全部尝试成本，不能把done、文件存在或模型自述当验证。缺证先恢复已有证据，不补造输入，不重复已完成业务。只用当前状态，不能引用未来试跑。按状态中的用户范围和预算停止。下面监督由原记录和可追溯程序规则整理，不是原模型的隐含思考。'''


def rows(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path,'rt',encoding='utf-8-sig') as f:
        for s in f:
            if s.strip():yield json.loads(s)


def jdump(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def sha(value):
    return hashlib.sha256(value if isinstance(value,bytes) else value.encode('utf-8')).hexdigest()


def dump_rows(path,values):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=io.BytesIO()
    with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as z:
        for v in values:z.write((jdump(v)+'\n').encode('utf-8'))
    data=raw.getvalue()
    if path.exists():
        assert path.read_bytes()==data,'Refuse overwrite; use --output-revision for a new overlay: '+str(path)
    else:path.write_bytes(data)


def source_ids(value):
    return sorted(set(re.findall(r'conv_[a-f0-9]{12}',jdump(value))))


def line_ref(text,needle,source_sha):
    lines=text.splitlines()
    n=next((i+1 for i,s in enumerate(lines) if needle in s),None)
    assert n is not None,needle
    return {'path':'pipeline.py','sha256':source_sha,'sha256_normalization':'UTF8_TEXT_UNIVERSAL_NEWLINES_TO_LF',
            'line':n,'rule_anchor':needle}


def json_doc(file):
    p=BUNDLE/file['object']
    if not p.is_file():p=BUNDLE/'archive'/file['object']
    data=p.read_bytes()
    assert sha(data)==file['sha256']
    text=data.decode('utf-8-sig')
    try:return json.loads(text),text,None
    except json.JSONDecodeError as e:return None,text,{'line':e.lineno,'column':e.colno,'message':e.msg}


def temporal_write(native,relative,digest):
    matches=[]
    declared_workspace=any(m.get('role')=='user' and isinstance(m.get('content'),str) and
        '当前工作目录为 /workspace' in m['content'] for m in native.get('messages',[]))
    for i,m in enumerate(native.get('messages',[])):
        if m.get('role')!='assistant' or not isinstance(m.get('content'),list):continue
        for b in m['content']:
            if not isinstance(b,dict) or b.get('type')!='toolCall':continue
            a=b.get('arguments') or {}
            if not isinstance(a,dict):continue
            path=str(a.get('path') or a.get('file_path') or '')
            normalized=path.replace('\\','/')
            relative_from_recorded_cwd=False
            if normalized and not normalized.startswith('/') and declared_workspace:
                normalized='/workspace/'+normalized.removeprefix('./')
                relative_from_recorded_cwd=True
            content=a.get('content') if isinstance(a.get('content'),str) else a.get('text')
            if normalized=='/'+relative.removeprefix('workspace/') or normalized=='/'+relative:
                if isinstance(content,str) and sha(content)==digest:
                    matches.append({'message_index':i,'source_event_line':(native.get('source_event_lines') or [None]*len(native['messages']))[i],
                                    'timestamp':int(m.get('timestamp') or 0),'tool_call_id':b.get('id'),
                                    'original_path_argument':path,'normalized_native_path':normalized,
                                    'relative_path_resolved_by_recorded_workspace_root':relative_from_recorded_cwd,
                                    'written_content_sha256':digest,'exact_native_write':True})
    return matches[-1] if matches else None


def action(stage,args,basis,refs):
    return {'next_stage':stage,'args':args,'decision_basis':basis,'evidence_refs':refs}


def annotate(name,value,parse_issue,refs,rule_refs):
    """Labels depend only on artifact content already supplied in the state."""
    output=[]
    if parse_issue:
        return [('invalid_stage_json',action('make',{'operation':'repair_existing_stage_json','artifact':name,'parse_error':parse_issue},
                '已有阶段文件不能解析；先局部修复格式并复查，不视为制作或试跑成功。',refs),rule_refs['invalid_review'])]
    if not isinstance(value,dict):return output
    if name in ('routes.json','screen.json'):
        for i,card in enumerate(value.get('routes') or []):
            if not isinstance(card,dict):continue
            rid=card.get('merge_into') or card.get('id')
            if not rid:continue
            merged=bool(card.get('merge_into'))
            a=action('route_update' if merged else 'make',
                     {'operation':'merge_existing_route' if merged else 'construct_candidate','route_id':rid,
                      'route_card':card,'preserve_existing_results':True},
                     '筛选记录声明归并已有路线；保留已有资源与费用，不能把归并当新成功技能。' if merged else
                     '筛选已给出可复用路线与依据；下一步构建候选资源，之后仍须复现和独立试跑，不能现在冻结。',refs)
            output.append((f'route_{i}',a,rule_refs['apply_routes']))
        for i,d in enumerate(value.get('decisions') or []):
            if not isinstance(d,dict):continue
            typ=d.get('action')
            if typ not in ('new','reuse','merge','defer','reject','no_value'):continue
            if typ in ('reuse','merge'):st,op='route_update','merge_existing_route'
            elif typ=='new':st,op='make','construct_candidate'
            elif typ=='defer':st,op='wait','defer_with_recorded_reason'
            else:st,op='stop','stop_no_reuse_value'
            output.append((f'decision_{i}',action(st,{'operation':op,'screen_decision':d},
                    '按当前筛选记录处理本来源；只执行该决定对应步骤，不把无价值或暂缓改记成失败制作。',refs),rule_refs['apply_routes']))
    elif name in ('tasks.json','development_tasks.json'):
        cases=value.get('cases') or value.get('tasks') or []
        if cases:
            output.append(('selected_cases',action('actor',{'operation':'paired_trials','cases':cases,
                'arms':['no_skill','workflow'],'validate_real_inputs_and_learning_source_independence':True,
                'reuse_identical_completed_baseline':True},
                '当前选题输出有真实需求候选；先核对真实输入和与学习来源独立性，再用相同题目/资源条件试跑两臂，复用已有同条件基线。',refs),rule_refs['paired_trials']))
        else:
            output.append(('empty_cases',action('request_inputs',{'operation':'record_missing_or_inapplicable_inputs',
                'reason':value.get('reason') or value.get('note'),'blocked_inputs':value.get('blocked_inputs') or [],
                'case_decisions':value.get('case_decisions') or [],'run_business':False},
                '当前没有可独立执行的case；保留已检索范围和具体缺件/错配原因，不伪造任务，不为填槽派业务或付费评审。',refs),rule_refs['empty_cases']))
    elif name=='making.json':
        if value.get('skip') or value.get('skip_reason'):
            output.append(('maker_skip',action('stop',{'operation':'record_no_reusable_resource','reason':value.get('skip_reason') or value.get('reason')},
                '制作记录明确跳过；保留理由，不能把文件写出视为有效技能。',refs),rule_refs['skip']))
        else:
            output.append(('maker_verify',action('make',{'operation':'verify_existing_resources_before_trials',
                'skill_files':value.get('skill_files') or [],'reported_program_runs':value.get('program_runs') or [],
                'known_issues':value.get('known_issues') or [],'reuse_existing_resources':True,'do_not_claim_business_success':True},
                '候选资源已产生，但program_runs是原制作记录自述，须核已有工具回执和正常/边界/错误输入复现；未有业务试跑，不给制作整体成功结论。',refs),rule_refs['make_to_prepare']))
    elif name=='review.json':
        dec=value.get('decision')
        if dec=='retain':
            output.append(('review_retain_check',action('finalize',{'operation':'verify_trial_evidence_then_freeze',
                'required_checks':['exact_candidate_version_used_in_trials','all_cases_delivery_passed','resources_reliable',
                'resources_actually_used','all_attempt_cost_reduced','no_missing_usage','independent_quality_check'],
                'if_any_missing':'recover_existing_evidence_or_defer','review_decision':'retain'},
                '收到retain仍不能直接给所有历史动作正标；冻结前核对应版本的真实试跑、交付、实际使用与完整成本，缺证则恢复或暂缓。',refs),rule_refs['retain_guard']))
        elif dec=='revise':
            nxt=value.get('next_step')
            if nxt=='recover_evidence':st,op='recover_evidence','recover_existing_usage_and_artifacts'
            elif nxt in ('find_inputs','recover_inputs','reselect_tasks','reselect'):st,op='prepare','recover_real_inputs_or_reselect'
            else:st,op='make','local_resource_revision'
            output.append(('review_revise',action(st,{'operation':op,'repair_notes':value.get('repair_notes') or [],
                'case_findings':value.get('case_findings') or [],'reason':value.get('reason'),
                'next_step_from_original_review':nxt,'respect_user_scope_and_revision_budget':True,
                'verify_revised_version_in_later_trials':True},
                '当前评审记录了具体问题；按问题类型恢复既有证据、真实输入或局部修订。修订正确性必须等对应新版本后续试跑，不由revise指令本身证明。',refs),rule_refs['review_state']))
        elif dec=='defer':
            output.append(('review_defer',action('wait',{'operation':'defer_preserving_evidence','reason':value.get('reason'),
                'next_step_from_original_review':value.get('next_step'),'repair_notes':value.get('repair_notes') or [],
                'do_not_invent_success':True},'已有评审判断证据或条件不足；保留未知，不补零、估算成完整成本或宣称已合格。',refs),rule_refs['review_state']))
        elif dec=='reject':
            output.append(('review_reject',action('stop',{'operation':'stop_no_benefit','reason':value.get('reason'),
                'retain_all_original_attempts_and_costs':True},'当前评审拒绝该候选；保留资源与失败成本，不再把整条失败链的每一步都标错误。',refs),rule_refs['review_state']))
    return output


def main(refresh_real_only=False):
    OUT.mkdir(parents=True,exist_ok=True)
    pipeline=(ROOT/'pipeline.py').read_text(encoding='utf-8')
    pipeline_sha=sha(pipeline)
    anchors={'initial_screen':'for index in range(0, len(remaining), size):',
        'apply_routes':'def apply_routes(', 'paired_trials':'for arm in ("no_skill", "workflow"):',
        'empty_cases':'# An empty preparation is a data limitation', 'skip':'if route.get("skip_reason"):',
        'make_to_prepare':'if not route.get("tasks"):', 'retain_guard':"if review['decision']=='retain' and not (",
        'review_state':"route['value_review']=review", 'invalid_review':"筛选未给出有效取舍"}
    rule_refs={k:line_ref(pipeline,v,pipeline_sha) for k,v in anchors.items()}
    native={x['episode_id']:x for x in rows(BUNDLE/'canonical/native_episodes.jsonl.gz')}
    catalog={x['episode_id']:x for x in rows(BUNDLE/'catalog/episodes.jsonl')}
    old_scope={x['episode_id']:x for x in rows(V6/'lineage_episode_decisions.jsonl.gz')}
    outcome_file=V9/'episode_outcomes.jsonl.gz'
    new_scope={x['episode_id']:x for x in rows(outcome_file)} if outcome_file.is_file() else {}
    target_file=V9/'target_outcome_labels.jsonl.gz'
    target_scope={(x['episode_id'],x['source_message_index']):x for x in rows(target_file)} if target_file.is_file() else {}
    protected_sets=[]
    for p in sorted((ROOT/'benchmark').glob('*/contracts/evaluation.jsonl')):
        ids={x.get('session_id') for x in rows(p)}-{None}
        if len(ids)==226:protected_sets.append(ids)
    assert protected_sets and all(x==protected_sets[0] for x in protected_sets)
    protected=protected_sets[0]
    holdout_registry=ROOT/'output/20261026_ablation_v2/holdout_registry.json'
    holdout12=set(source_ids(json.loads(holdout_registry.read_text(encoding='utf-8-sig'))))
    protected=protected|holdout12
    files=[]
    for f in rows(BUNDLE/'archive/file_index.jsonl'):
        bits=f['logical_path'].split('/',2)
        if len(bits)==3 and bits[0]=='episodes' and bits[2].startswith('workspace/outputs/') and bits[2].split('/')[-1] in STAGE_NAMES:
            files.append((bits[1],bits[2],f))
    compiled=[]; issues=[]; by_route=collections.defaultdict(list)
    for eid,rel,f in files:
        e=native.get(eid)
        if not e:continue
        value,text,parse_issue=json_doc(f)
        temporal=temporal_write(e,rel,f['sha256'])
        native_end=max((int(m.get('timestamp') or 0) for m in e.get('messages',[])),default=0)
        at=(temporal or {}).get('timestamp') or native_end
        ref={'episode_id':eid,'logical_path':f['logical_path'],'sha256':f['sha256'],'source_path':f.get('source_path'),
             'cas_object':f['object'],'exact_native_write':temporal,'available_after_ms':at,
             'availability_proven':bool(temporal)}
        if parse_issue:issues.append({'episode_id':eid,'source':ref,'issue':parse_issue})
        prompt=next((m.get('content') for m in e.get('messages',[]) if m.get('role')=='user' and isinstance(m.get('content'),str)),'')
        state={'stage':e.get('kind'),'route_id':e.get('route_id'),'original_stage_request':prompt,
               'observed_output':{'path':'/'+rel,'json':value} if parse_issue is None else {'path':'/'+rel,'raw_text':text,'parse_error':parse_issue},
               'state_boundary':'after_this_exact_output_write' if temporal else 'after_episode_frozen_output_unproven_time',
               'state_time_ms':at,'future_trial_results_included':False,
               'current_user_scope_and_revision_budget':'not_reconstructed_do_not_assume_permission_for_paid_work'}
        ids=source_ids(state)
        old=old_scope.get(eid,{})
        new=(new_scope.get(eid) or {}).get('source_scope') or {}
        precise=target_scope.get((eid,(temporal or {}).get('message_index')),{})
        protected_direct=sorted(set(ids)&protected)
        if protected_direct or precise.get('source_admission')=='HOLD_PROTECTED':scope='HOLD_PROTECTED'
        elif precise.get('source_admission')=='ADMIT':scope='CLEAN_PRODUCER_TARGET_PREFIX_V9'
        elif precise:scope='HOLD_SCOPE_REQUIRES_V9_TARGET_OR_RESOURCE_CLOSURE'
        elif new.get('post_episode_status')=='HOLD_PROTECTED':scope='HOLD_PROTECTED'
        elif new.get('post_episode_status')=='CLEAN_PREFIX':scope='CLEAN_POSTSTATE_V9'
        elif old.get('status')=='ADMIT':scope='CLEAN_EPISODE_V6'
        else:scope='HOLD_SCOPE_REQUIRES_V9_TARGET_OR_RESOURCE_CLOSURE'
        for key,target,rule in annotate(rel.split('/')[-1],value,parse_issue,[ref],rule_refs):
            rid=target.get('args',{}).get('route_id') or e.get('route_id')
            row_id='coord_'+sha(eid+'|'+rel+'|'+key)[:24]
            target_text=jdump(target)
            admitted=scope.startswith('CLEAN_') and bool(temporal)
            row={'schema_version':'wrd-v9-coordination-example-1.0','id':row_id,'episode_id':eid,'route_id':rid,
                'source_group_id':e.get('component_id'),'source_ids':ids,'state_time_ms':at,
                'data_origin':'program_rule_annotation_of_observed_native_stage_output',
                'annotation_is_original_teacher_CoT':False,'original_teacher_output_preserved_in_state':True,
                'scope_status':scope,'direct_protected_source_ids':protected_direct,'training_admitted':admitted,
                'producer_target_scope':precise,
                'hold_reasons':[] if admitted else ([scope] if not scope.startswith('CLEAN_') else [])+([] if temporal else ['EXACT_ARTIFACT_AVAILABILITY_TIME_NOT_PROVEN']),
                'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':jdump(state)},
                            {'role':'assistant','content':target_text}],
                'message_loss_mask':[False,False,admitted],
                'supervision_candidate_message_indices':[2],'next_stage':target['next_stage'],
                'rule_provenance':rule,'original_output_ref':ref,
                'semantic_scope':'coordination_policy_conditioned_on_observation_not_trial_success_or_mutation_correctness',
                'recommended_relative_sampling_weight':0.25,
                'outcome_credit_assignment':'no_positive_resource_revision_credit_without_later_matching_version_trial',
                'loss_scope_if_admitted':'annotated_assistant_plan_only','example_view':'single_decision',
                'same_source_alternate_view_not_new_task':True}
            compiled.append(row);by_route[str(rid)].append(row)
    traces=[]
    for rid,rr in sorted(by_route.items()):
        rr.sort(key=lambda x:(x['state_time_ms'],x['id']))
        messages=[{'role':'system','content':SYSTEM}];mask=[False]
        for row in rr:
            messages.extend(row['messages'][1:]);mask.extend([False,row['training_admitted']])
        traces.append({'schema_version':'wrd-v9-coordination-trace-1.0','id':'coord_trace_'+sha(rid)[:20],
            'route_id':rid,'data_origin':'chronological_reconstruction_of_multiple_native_stage_states_plus_program_labels',
            'original_single_model_autonomous_trajectory':False,'decision_ids':[x['id'] for x in rr],
            'episode_ids':sorted({x['episode_id'] for x in rr}),'source_ids':sorted(set().union(*(set(x['source_ids']) for x in rr))),
            'messages':messages,'message_loss_mask':mask,'training_admitted':all(x['training_admitted'] for x in rr),
            'count_as_additional_independent_tasks':False,'example_view':'full_available_route_history',
            'ordering_assertion':'nondecreasing_original_message_timestamp_no_future_document_in_earlier_state',
            'complete_A_to_D_claimed':False})
    synthetic=list(rows(BASE_OUT/'rule_boundary_augmentation.jsonl.gz')) if refresh_real_only else synthetic_rule_states(rule_refs)
    entrypoints=list(rows(BASE_OUT/'entrypoint_controller.native_paths.source_closed.jsonl.gz')) if refresh_real_only else entrypoint_controller(protected,rule_refs)
    dump_rows(OUT/'decisions.all.jsonl.gz',compiled)
    dump_rows(OUT/'decisions.source_closed.jsonl.gz',[x for x in compiled if x['training_admitted']])
    dump_rows(OUT/'route_traces.all.jsonl.gz',traces)
    dump_rows(OUT/'route_traces.source_closed.jsonl.gz',[x for x in traces if x['training_admitted']])
    if not refresh_real_only:
        dump_rows(OUT/'rule_boundary_augmentation.jsonl.gz',synthetic)
        dump_rows(OUT/'entrypoint_controller.native_paths.source_closed.jsonl.gz',entrypoints)
    qa={'all_decision_ids_unique':len({x['id'] for x in compiled})==len(compiled),
        'all_loss_masks_have_only_assistant_targets':all(x['message_loss_mask'][:2]==[False,False] for x in compiled),
        'no_protected_direct_id_in_admitted':all(not x['direct_protected_source_ids'] for x in compiled if x['training_admitted']),
        'all_admitted_exact_native_write_anchored':all(x['original_output_ref']['exact_native_write'] for x in compiled if x['training_admitted']),
        'future_trials_not_used_in_state':all(json.loads(x['messages'][1]['content'])['future_trial_results_included'] is False for x in compiled),
        'all_annotations_marked_not_teacher_CoT':all(x['annotation_is_original_teacher_CoT'] is False for x in compiled),
        'synthetic_do_not_claim_real_tasks':all(x['count_as_real_task'] is False for x in synthetic),
        'entrypoints_have_no_protected_source':all(not(set(x['source_ids'])&protected) for x in entrypoints),
        'entrypoints_preserve_complete_record_messages':all(x['complete_source_message_list_preserved'] for x in entrypoints),
        'no_agent_loop_or_model_run':True}
    assert all(qa.values())
    summary={'schema_version':'wrd-v9-coordination-summary-1.0','original226_isolated':True,'training_started':False,
        'native_stage_artifacts_processed':len(files),'native_episodes_with_rows':len({x['episode_id'] for x in compiled}),
        'program_annotated_real_state_decisions':len(compiled),'admitted_source_closed_real_state_decisions':sum(x['training_admitted'] for x in compiled),
        'decision_next_stage_counts':dict(collections.Counter(x['next_stage'] for x in compiled)),
        'admitted_decision_next_stage_counts':dict(collections.Counter(x['next_stage'] for x in compiled if x['training_admitted'])),
        'scope_counts':dict(collections.Counter(x['scope_status'] for x in compiled)),
        'original_route_trace_views':len(traces),'route_trace_groups_include_original_screen_proposal_ids_not_only_final_121_routes':True,
        'source_closed_route_trace_views':sum(x['training_admitted'] for x in traces),
        'pure_rule_boundary_augmentation_count':len(synthetic),'synthetic_counted_as_real_tasks':False,
        'independently_annotated_clean_entrypoints':len(entrypoints),
        'entrypoint_category_counts':dict(collections.Counter(x['category'] for x in entrypoints)),
        'entrypoints_not_original_teacher_pipeline_trajectories':True,
        'old_scope_used_as_fallback_only':True,'v9_outcome_scope_file_present':outcome_file.is_file(),
        'v9_target_scope_file_present':target_file.is_file(),
        'rule_source_sha256':pipeline_sha,'qa':qa,'parse_issues':issues,
        'limits':['Program labels are annotated policies, not original private reasoning.',
                  'Control examples do not prove resource mutations correct or real closed-loop model performance.',
                  'All-source body views are explicitly held; only source_closed and source-independent augmentation are train candidates.',
                  'Re-run after final v9 scope recovery to expand the real-state admitted view.']}
    summary_text=json.dumps(summary,ensure_ascii=False,indent=2)+'\n'
    if (OUT/'SUMMARY.json').exists():assert (OUT/'SUMMARY.json').read_text(encoding='utf-8')==summary_text,'Refuse overwrite existing summary; use a new overlay'
    else:(OUT/'SUMMARY.json').write_text(summary_text,encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('parse_issues','limits')},ensure_ascii=False))


def entrypoint_controller(protected,rule_refs):
    """Fresh control annotations of clean raw inputs, without old stage labels."""
    corpus=ROOT/'benchmark/enterprise_input_closed_v11_20261012/有效轨迹.jsonl'
    bindings=json.loads((ROOT/'output/20261021_workflow_skill_library/source_bindings.json').read_text(encoding='utf-8-sig'))
    result=[]
    material_hash_cache={}
    for physical_line,line in enumerate(corpus.read_bytes().split(b'\n'),1):
        if not line.strip():continue
        record=json.loads(line)
        sid=record['session_id']
        if sid in protected:continue
        binding=bindings.get(sid)
        assert binding and binding['physical_line']==physical_line and binding['source_record_sha256']==sha(line)
        # Original-record hash is preserved. No pre-existing WRD response or
        # quality conclusion is imported into this new annotation.
        conversation=binding.get('conversation') or {}
        cp=Path(conversation['path'])
        assert cp.is_file() and sha(cp.read_bytes())==conversation['sha256']
        materials=[]
        for material_index,material in enumerate(binding.get('materials') or []):
            rel=material.get('relative_path')
            declared=[material.get('path'),(material.get('pin') or {}).get('path')]
            candidates=[Path(x) for x in declared if isinstance(x,str)]
            candidates += [ROOT/'benchmark/enterprise_input_closed_v11_20261012'/str(rel),ROOT/str(rel)] if rel else []
            path=next((p for p in candidates if p.is_file()),None)
            expected=material.get('sha256') or (material.get('pin') or {}).get('sha256')
            identity=None
            if path and material.get('eligible_real_input') is True and material.get('synthetic') is not True:
                key=str(path.resolve())
                if key not in material_hash_cache:material_hash_cache[key]=sha(path.read_bytes())
                identity=bool(expected) and material_hash_cache[key]==expected
            materials.append({'relative_path':rel,'provenance':material.get('provenance'),
                'synthetic':material.get('synthetic'),'historical_bytes_certified':material.get('historical_bytes_certified'),
                'eligible_real_input':material.get('eligible_real_input'),
                'declared_pin_sha256':expected,'eligible_file_current_sha256_verified':identity,
                'resolved_existing_path':str(path) if path else None,
                'declared_native_path':('/workspace/inputs/materials/'+sid+'/'+str(material_index+1)+'_'+
                    re.sub(r'[^\w.-]+','_',path.name,flags=re.UNICODE).strip('._')) if path else None,
                'declared_available':material.get('available'),'file_exists_now':bool(path),
                'file_bytes_now':path.stat().st_size if path else None,
                'availability_is_not_historical_identity_or_quality':True})
        state={'stage':'new_complete_conversation','source_id':sid,'category':record.get('task_category'),
            'title':record.get('title'),'complete_conversation_messages':record.get('messages') or [],
            'source_sequence_basis':record.get('sequence_basis'),
            'native_reply_to_verified':record.get('native_reply_to_verified'),
            'historical_event_identity_verified':record.get('historical_event_identity_verified'),
            'file_inputs':materials,'source_limitations':binding.get('limitations') or [],
            'conversation_native_path_contract':'/workspace/inputs/conversations/'+sid+'.json',
            'native_path_contract_source':'research/workflow/stages.py::_source_inputs/_materials',
            'native_paths_are_resource_binding_declarations_not_execution_receipts':True,
            'no_prior_WRD_result_assumed':True,'future_skill_trial_results':None}
        observed_ids=source_ids(state)
        if set(observed_ids)&protected:continue
        refs=[{'path':str(corpus),'physical_line':physical_line,'source_record_sha256':sha(line)},
              {'path':str(cp),'sha256':conversation['sha256'],'bytes':cp.stat().st_size}]
        readable=[{'input_index':i,'path':m['declared_native_path'],'sha256':m['declared_pin_sha256']}
                  for i,m in enumerate(materials)
                  if m['eligible_real_input'] is True and m['synthetic'] is not True and m['file_exists_now'] and m['eligible_file_current_sha256_verified']]
        unavailable=[i for i,m in enumerate(materials)
                     if not(m['eligible_real_input'] is True and m['synthetic'] is not True and m['file_exists_now'] and m['eligible_file_current_sha256_verified'])]
        target=action('screen',{'operation':'extract_and_compare_reusable_routes','source_id':sid,
            'category':record.get('task_category'),
            'read_conversation_ref':{'path':'/workspace/inputs/conversations/'+sid+'.json','sha256':conversation['sha256']},
            'read_input_refs':readable,'unavailable_or_unverified_input_indices':unavailable,
            'preserve_user_corrections_and_failed_attempts':True,
            'missing_input_policy':'record_missing_originals_do_not_invent_or_promote_synthetic_materials',
            'do_not_claim_reuse_value_or_skill_success_before_analysis':True},
            '收到一份完整原会话，应先归纳同构步骤、用户纠正与复用边界，再与已有路线比较；当前尚无制作或试跑结果。附件清单的存在不证明历史真实，合成或未认证材料不得冒充原件。',refs)
        result.append({'schema_version':'wrd-v9-coordination-example-1.0','id':'coord_entry_'+sha(sid)[:24],
            'episode_id':None,'route_id':None,'source_id':sid,'source_ids':observed_ids,
            'source_group_id':record.get('leakage_component_id') or sid,'category':record.get('task_category'),
            'data_origin':'INDEPENDENT_ANNOTATION_FROM_CLEAN_SOURCE_INPUT','annotation_is_original_teacher_CoT':False,
            'original_teacher_output_preserved_in_state':False,'complete_source_message_list_preserved':True,
            'source_message_count':len(record.get('messages') or []),
            'scope_status':'CLEAN_ORIGINAL_INPUT_EXCLUDING_226_AND_HOLDOUT12','training_admitted':True,
            'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':jdump(state)},
                        {'role':'assistant','content':jdump(target)}],
            'message_loss_mask':[False,False,True],'supervision_candidate_message_indices':[2],
            'next_stage':'screen','recommended_relative_sampling_weight':0.1,
            'rule_provenance':rule_refs['initial_screen'],'source_evidence_refs':refs,
            'count_as_complete_autonomous_pipeline_task':False,
            'loss_scope_if_admitted':'new_annotated_controller_plan_only_not_embedded_business_assistant_text',
            'example_view':'complete_source_entrypoint_new_control_annotation'})
    return result


def synthetic_rule_states(rule_refs):
    """Exhaustive finite rule boundary combinations, never teacher trajectories."""
    output=[]
    # Distinct cross-product states, not random paraphrases or duplicated rows.
    for quality,reliability,used,cost,budget in itertools.product(('pass','fail','unknown'),('reliable','unreliable','unknown'),
                                                               (True,False,None),('reduced','not_reduced','unknown'),('available','exhausted')):
        state={'stage':'post_trial_review','delivery_quality':quality,'resource_reliability':reliability,
               'resource_actually_used':used,'all_attempt_cost':cost,'resource_revision_budget':budget,
               'exact_version_and_source_independence_verified':True,'user_allows_current_scope':True,
               'is_synthetic_rule_boundary_state':True}
        if cost=='unknown':st,op,basis='recover_evidence','recover_existing_usage','用量缺失时先恢复既有账，不补零或重复业务。'
        elif 'unknown' in (quality,reliability) or used is None:st,op,basis='recover_evidence','recover_existing_trial_evidence','先核已有交付、资源与实际读用证据，未知不记通过。'
        elif quality=='pass' and reliability=='reliable' and used is True and cost=='reduced':st,op,basis='finalize','freeze_verified_skill','对应版本已通过交付、资源可靠、实际使用且完整成本下降，可冻结。'
        elif budget=='exhausted':st,op,basis='stop','stop_at_revision_limit','尚未达到保留依据且用户修订预算耗尽，停止新修订，保留旧结果与费用。'
        else:st,op,basis='make','local_revision_then_matching_version_trial','已有失败或未减负证据且仍有修订预算，按证据局修并验证新版本，不直接冻结。'
        target=action(st,{'operation':op},basis,[rule_refs['retain_guard']])
        row={'schema_version':'wrd-v9-coordination-example-1.0','id':'coord_rule_'+sha(jdump(state))[:24],
             'episode_id':None,'route_id':None,'source_ids':[],'source_group_id':'pure_source_independent_program_rules',
             'data_origin':'synthetic_exhaustive_program_rule_boundary_state','annotation_is_original_teacher_CoT':False,
             'training_admitted':True,'scope_status':'SOURCE_INDEPENDENT_RULE_NO_ENTERPRISE_CONTENT',
             'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':jdump(state)},{'role':'assistant','content':jdump(target)}],
             'message_loss_mask':[False,False,True],'supervision_candidate_message_indices':[2],
             'next_stage':st,'count_as_real_task':False,'original_teacher_output_preserved_in_state':False,
             'recommended_relative_sampling_weight':0.05,
             'rule_provenance':rule_refs['retain_guard'],'loss_scope_if_admitted':'annotated_assistant_plan_only',
             'example_view':'synthetic_boundary_decision'}
        output.append(row)
    return output


def audit_unknown_reviews():
    """Concrete read/copy/provider joins for four difficult original reviews."""
    ids={'ep_064bcfc97d47426a726c','ep_0e0f8423ba9f6d2f04ed',
         'ep_3bc45a61c30186110fbb','ep_8c264cd169d86d306e08'}
    native={x['episode_id']:x for x in rows(BUNDLE/'canonical/native_episodes.jsonl.gz')}
    catalog={x['episode_id']:x for x in rows(BUNDLE/'catalog/episodes.jsonl')}
    by_source={str(x['source_path']).replace('\\','/').casefold():x['episode_id'] for x in catalog.values()}
    scopes={x['episode_id']:x['source_scope'] for x in rows(V9/'episode_outcomes.jsonl.gz')}
    target_scopes={(x['episode_id'],x['source_message_index']):x for x in rows(V9/'target_outcome_labels.jsonl.gz')}
    nodes=[x for x in rows(V9/'resource_scope.jsonl.gz') if x.get('episode_id') in ids]
    files={};root_files={};candidate=collections.defaultdict(dict)
    for f in rows(BUNDLE/'archive/file_index.jsonl'):
        bits=f['logical_path'].split('/',2)
        if len(bits)!=3 or bits[0]!='episodes':continue
        eid,rel=bits[1:]
        if eid in ids:files[(eid,rel)]=f
        if rel in ('response.json','request.json','openclaw_transport/session_events.jsonl','openclaw_transport/skill_reads.json'):
            root_files[(eid,rel)]=f
        if eid in ids and rel.startswith('workspace/inputs/candidate/'):
            candidate[eid][rel.removeprefix('workspace/inputs/candidate/')]=f.get('source_sha256') or f['sha256']
    output_trees=[x for x in rows(ROOT/'output/20261026_wrd_raw_census_v7/indexes/skill_version_trees.all.jsonl.gz')
                  if x['output_skill_root_logical_path'].startswith('episodes/'+x['episode_id']+'/workspace/outputs/')]
    def data(f):
        p=BUNDLE/'archive'/f['object'];b=p.read_bytes();assert sha(b)==f['sha256'];return b
    def ref(f):return {k:f.get(k) for k in ('logical_path','sha256','source_sha256','source_path','object','bytes')}
    case_actor={};provider_evidence={}
    import importlib.util
    evidence_module_path=ROOT/'research/workflow/evidence.py'
    spec=importlib.util.spec_from_file_location('wrd_original_evidence_parser',evidence_module_path)
    evidence_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(evidence_module)
    # read_usage_evidence carries an exact source_host, rather than a guessed
    # source ID or an inference from a file's basename.
    for (review_eid,rel),f in files.items():
        np='/'+rel
        if '/cases/' in np and np.endswith('/read_usage_evidence.json'):
            v=json.loads(data(f).decode('utf-8-sig'))
            host=str(v.get('source_host') or '').replace('\\','/')
            suffix='/openclaw_transport/session_events.jsonl'
            producer=by_source.get(host[:-len(suffix)].casefold()) if host.endswith(suffix) else None
            key=(review_eid,np.rsplit('/',1)[0])
            case_actor[key]=producer
            provider_evidence[key]={'source_host':host,'read_usage_ref':ref(f),
                'original_read_usage_source':v.get('source'),'provider_episode_id':producer,
                'provider_post_scope':scopes.get(producer),
                'read_usage_observation_count':len(v.get('observations') or [])}
            original_session=root_files.get((producer,'openclaw_transport/session_events.jsonl'))
            if original_session:
                session_path=BUNDLE/'archive'/original_session['object'];data(original_session)
                rebuilt=evidence_module.read_usage_evidence(session_path)
                rebuilt['source_host']=v.get('source_host');rebuilt['source']=v.get('source')
                for observation in rebuilt.get('observations') or []:
                    observation['source_ref']=v.get('source')+':'+str(observation['completion_line'] or observation['call_line'])
                provider_evidence[key]['usage_replay']={'parser_path':str(evidence_module_path),
                    'parser_sha256':sha(evidence_module_path.read_bytes()),'source_session_ref':ref(original_session),
                    'same_full_json_after_declared_source_path_projection':jdump(rebuilt)==jdump(v),
                    'same_summary':rebuilt.get('summary')==v.get('summary'),
                    'same_observations':rebuilt.get('observations')==v.get('observations'),
                    'original_value_json_sha256':sha(jdump(v)),'replayed_value_json_sha256':sha(jdump(rebuilt)),
                    'only_saved_trace_parser_executed_not_generated_resource_or_model':True}
    reports=[]
    for eid in sorted(ids):
        request=root_files.get((eid,'request.json'));req=json.loads(data(request).decode('utf-8-sig')) if request else {}
        review_doc=files.get((eid,'workspace/inputs/review_input.json'))
        rd=json.loads(data(review_doc).decode('utf-8-sig')) if review_doc else {}
        matches=[]
        for tree in output_trees:
            mapping={f['relative_path']:f['sha256'] for f in tree['files']}
            if mapping==candidate[eid]:
                pe=tree['episode_id'];pe_native=native.get(pe,{})
                file_writes=[]
                for f in tree['files']:
                    pth=tree['output_skill_root_logical_path'].split('/',2)[2]+'/'+f['relative_path']
                    exact=temporal_write(pe_native,pth,f['sha256'])
                    file_writes.append({'relative_path':f['relative_path'],'sha256':f['sha256'],
                        'exact_native_write':exact,
                        'producer_target_scope':target_scopes.get((pe,(exact or {}).get('message_index')))})
                matches.append({'producer_episode_id':pe,'tree_content_sha256':tree['tree_content_sha256'],
                    'output_root':tree['output_skill_root_logical_path'],'file_count':tree['file_count'],
                    'post_episode_source_scope':scopes.get(pe),'file_write_scope_proofs':file_writes})
        audited=[]
        for node in nodes:
            if node['episode_id']!=eid:continue
            np=node['native_path'];f=files.get((eid,np.removeprefix('/')))
            mi=node.get('observed_after_assistant_message_index');ep=native[eid]
            alines=ep.get('source_event_lines') or []
            rr={'node_id':node['node_id'],'native_path':np,'original_unknown_reasons':node.get('unknown_reasons'),
                'original_observed_after_message_index':mi,'original_call_event_line':alines[mi] if isinstance(mi,int) and mi<len(alines) else None,
                'original_call_timestamp':ep['messages'][mi].get('timestamp') if isinstance(mi,int) and mi<len(ep['messages']) else None,
                'file_ref':ref(f) if f else None,'file_bytes_rehashed':False,'recovery_status':'UNRESOLVED'}
            if f:data(f);rr['file_bytes_rehashed']=True
            if '/cases/' in np:
                mat=re.match(r'(/workspace/inputs/cases/\d+/(?:no_skill|workflow))(?:/(.*))?$',np)
                if mat:
                    base,suffix=mat.groups();pe=case_actor.get((eid,base))
                    rr['case_provider_binding']=provider_evidence.get((eid,base))
                    expected=root_files.get((pe,suffix)) if pe else None
                    rr['exact_original_provider_file']=ref(expected) if expected else None
                    if f and expected:
                        b=data(expected)
                        same=(f['sha256']==expected['sha256'])
                        raw_same=bool(f.get('source_sha256')) and f.get('source_sha256')==expected.get('source_sha256')
                        rr['frozen_bytes_equal_bound_provider']=same
                        rr['pre_sanitization_sha_equal_bound_provider']=raw_same
                        if same:
                            rr['recovery_status']='EXACT_CASE_PROVIDER_BYTES_RECOVERED_SCOPE_INHERIT_REQUIRED'
                            rr['remaining_source_scope']=scopes.get(pe)
                    elif suffix=='read_usage_evidence.json' and pe:
                        ev=provider_evidence[(eid,base)];session=root_files.get((pe,'openclaw_transport/session_events.jsonl'))
                        rr['deterministic_derivation_source_session']=ref(session) if session else None
                        replay=ev.get('usage_replay') or {}
                        rr['usage_replay']=replay
                        rr['recovery_status']='EXACT_ORIGINAL_USAGE_RECIPE_REPLAYED_SCOPE_INHERIT_REQUIRED' if replay.get('same_full_json_after_declared_source_path_projection') else 'BOUND_USAGE_DERIVATION_INPUT_FOUND_REPLAY_DIFFERENCE_REQUIRES_REVIEW'
            elif np.startswith('/workspace/inputs/candidate/'):
                rr['exact_complete_candidate_tree_matches']=matches
                rr['recovery_status']='EXACT_COMPLETE_TREE_PRODUCERS_FOUND_SCOPE_INHERIT_REQUIRED' if matches else 'MISSING_EXACT_COMPLETE_TREE_PRODUCER'
            elif np=='/workspace/inputs/review_input.json':
                rr['declared_case_sources']=[c.get('case',{}).get('source_id') for c in rd.get('cases',[])]
                rr['recovery_status']='OUTER_REVIEW_INPUT_METADATA_RECIPE_AND_ALL_ACTUAL_DEPENDENCIES_REQUIRED'
            elif np=='/workspace/outputs/review.json':
                rr['recovery_status']='OWN_REVIEW_OUTPUT_DEPENDS_ON_PRIOR_OBSERVED_INPUTS'
            audited.append(rr)
        reports.append({'episode_id':eid,'route_id':catalog[eid].get('route_id'),'request_ref':ref(request) if request else None,
            'review_input_ref':ref(review_doc) if review_doc else None,'case_provider_bindings':[
                {'native_case_root':k[1],**v} for k,v in provider_evidence.items() if k[0]==eid],
            'candidate_complete_tree_files':candidate[eid],'candidate_complete_tree_producers':matches,
            'observed_resource_audits':audited,'source_closed_by_this_report':False,
            'reason':'Exact identity recovery is distinct from recursive source closure; no unknown is silently admitted.'})
    report={'schema_version':'wrd-v9-four-review-resource-recovery-1.0','kind':'actual_native_reads_to_exact_case_and_version_providers',
        'training_started':False,'new_model_or_business_calls':0,'old_inputs_unchanged':True,'review_count':len(reports),
        'source_scope_snapshot_sha256':sha((V9/'episode_outcomes.jsonl.gz').read_bytes()),
        'resource_scope_snapshot_sha256':sha((V9/'resource_scope.jsonl.gz').read_bytes()),
        'reviews':reports,'no_training_admission_changed':True}
    p=OUT/'UNKNOWN_STATE_RECOVERY.json'
    p.parent.mkdir(parents=True,exist_ok=True)
    assert not p.exists(),'Keep the earlier recovery report; use a new overlay name'
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'review_count':len(reports),'resource_nodes':sum(len(x['observed_resource_audits']) for x in reports),
        'case_provider_bindings':len(provider_evidence),'candidate_version_producer_refs':sum(len(x['candidate_complete_tree_producers']) for x in reports),
        'recovery_report':str(p)},ensure_ascii=False))


def export_case_overlay(source_report):
    report_path=Path(source_report)
    report=json.loads(report_path.read_text(encoding='utf-8'))
    native={x['episode_id']:x for x in rows(BUNDLE/'canonical/native_episodes.jsonl.gz')}
    overlay=[];available_only=[]
    for review in report['reviews']:
        for resource in review['observed_resource_audits']:
            provider=resource.get('case_provider_binding') or {}
            pe=provider.get('provider_episode_id')
            if not pe:continue
            prefix=len(native[pe].get('messages') or [])
            relation=None;evidence={}
            if resource.get('frozen_bytes_equal_bound_provider') is True:
                relation='FOLLOW_EXACT_CASE_FILE_PROVIDER_PREFIX'
                original=resource['exact_original_provider_file']
                if resource['native_path'].endswith('/response.json'):
                    p=BUNDLE/'archive'/original['object'];data=p.read_bytes();assert sha(data)==original['sha256']
                    response=json.loads(data.decode('utf-8-sig'));answer=response.get('answer')
                    final_matches=[]
                    for i,m in enumerate(native[pe].get('messages') or []):
                        if m.get('role')!='assistant' or not isinstance(m.get('content'),list):continue
                        text='\n'.join(b.get('text','') for b in m['content'] if isinstance(b,dict) and b.get('type')=='text')
                        if isinstance(answer,str) and text==answer:final_matches.append(i)
                    if final_matches:prefix=max(final_matches)+1
                    evidence['exact_final_answer_message_indices']=final_matches
                    evidence['response_final_prefix_is_conservative_full_session_if_no_exact_text_match']=not bool(final_matches)
                evidence.update({'consumer_file':resource['file_ref'],'provider_file':original,
                    'same_frozen_sha256':True,'same_pre_sanitization_sha256':resource.get('pre_sanitization_sha_equal_bound_provider'),
                    'provider_bound_by_original_usage_source_host':provider.get('source_host')})
            elif resource.get('recovery_status')=='EXACT_ORIGINAL_USAGE_RECIPE_REPLAYED_SCOPE_INHERIT_REQUIRED':
                relation='FOLLOW_REPLAYED_READ_USAGE_FULL_SESSION'
                replay=resource['usage_replay'];assert replay['same_full_json_after_declared_source_path_projection']
                evidence.update({'consumer_file':resource['file_ref'],'original_usage_recipe_replay':replay,
                    'provider_bound_by_original_usage_source_host':provider.get('source_host')})
            if relation:
                overlay.append({'node_id':resource['node_id'],'replacement_relation':relation,
                    'parent_episode_id':pe,'parent_prefix_end_exclusive':prefix,
                    'consumer_episode_id':review['episode_id'],'consumer_observed_after_assistant_message_index':resource['original_observed_after_message_index'],
                    'native_path':resource['native_path'],'evidence':evidence,
                    'original_observed_node_and_identity_preserved':True,
                    'no_new_training_admission_or_outcome_positive_label':True})
        observed_usage={x['native_path'] for x in review['observed_resource_audits'] if x['native_path'].endswith('/read_usage_evidence.json')}
        for provider in review['case_provider_bindings']:
            path=provider['native_case_root']+'/read_usage_evidence.json'
            if path not in observed_usage:
                available_only.append({'consumer_episode_id':review['episode_id'],'native_path':path,
                    'parent_episode_id':provider['provider_episode_id'],'usage_replay':provider.get('usage_replay'),
                    'node_id':None,'not_observed_by_this_native_reviewer':True,'no_scope_effect_until_observed':True})
    result={'schema_version':'wrd-v9-exact-review-resource-causal-overlay-1.0',
        'source_report':str(report_path),'source_report_sha256':sha(report_path.read_bytes()),
        'node_overlay_count':len(overlay),'replacement_relation_counts':dict(collections.Counter(x['replacement_relation'] for x in overlay)),
        'overlays':overlay,'additional_unobserved_but_exact_replayed_usage_inputs':available_only,
        'actual_resource_nodes_only_no_invented_observations':True,'training_started':False,
        'all_scope_and_quality_must_be_recomputed_by_parent_graph':True}
    p=BASE_OUT/'CAUSAL_RESOURCE_OVERLAY.json';assert not p.exists()
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('overlays','additional_unobserved_but_exact_replayed_usage_inputs')},ensure_ascii=False))


def export_full_controller_traces():
    """Small finite, explicitly hypothetical controller curriculum, no runs."""
    pipeline=(ROOT/'pipeline.py').read_text(encoding='utf-8');psha=sha(pipeline)
    refs={k:line_ref(pipeline,anchor,psha) for k,anchor in {
        'screen':'for index in range(0, len(remaining), size):',
        'make':'if not route.get("skill_root"):',
        'prepare':'if not route.get("tasks"):',
        'actor':'for arm in ("no_skill", "workflow"):',
        'review':'# Wait for the actual business arms',
        'retain':"if review['decision']=='retain' and not ("}.items()}
    def state(phase,**changes):
        return {'phase':phase,'hypothetical_state':True,'not_an_actual_tool_or_trial_observation':True,
            'user_scope_authorized':True,'user_stop':False,'candidate_version':'v0','candidate_present':False,
            'resource_verification':'unknown','case_selection_complete':False,'selected_case_count':0,
            'paired_trial_state':'not_started','latest_pair_version_matches_candidate':False,
            'review_decision':None,'delivery_quality':'unknown','resource_actually_used':None,
            'all_attempt_cost':'unknown','revision_budget_remaining':1,'evidence_missing':False,
            '_explicit_overrides':list(changes),**changes}
    def policy(s):
        p=s['phase'];basis=''
        if s['user_stop'] or not s['user_scope_authorized']:
            nxt,args,basis='stop',{'operation':'stop_at_user_scope','retain_existing_results_and_costs':True},'用户已停止或当前范围未授权，不继续派工作。'
        elif p=='new_conversation':nxt,args,basis='screen',{'operation':'extract_and_compare_reusable_routes'},'先从完整会话识别公共路线、用户纠正和适用边界，未分析前不声明成功。'
        elif p=='screened':
            dec=s.get('route_decision')
            if dec=='no_value':nxt,args,basis='stop',{'operation':'record_no_reuse_value'},'已给定筛选无复用价值，记录理由而不强造技能。'
            elif dec=='defer':nxt,args,basis='request_inputs',{'operation':'request_missing_original_inputs'},'缺少原输入时保留具体缺项，不补造。'
            elif dec=='reuse':nxt,args,basis='route_update',{'operation':'merge_existing_route','preserve_existing_resources_and_trials':True},'先归并已有路线，保留旧资源和已付试跑，不当作新技能。'
            else:nxt,args,basis='make',{'operation':'construct_candidate_resources'},'已给定新路线，开始构建候选工作流、脚本、模板与资料。'
        elif p=='frozen':nxt,args,basis='stop',{'operation':'deliver_frozen_skill_and_evidence_refs'},'已满足冻结条件，交付当前冻结包与证据引用，结束该路线。'
        elif s.get('environment_capability_missing'):
            nxt,args,basis='wait',{'operation':'record_environment_dependency','do_not_change_native_environment':True},'必要环境能力缺失，保留阻塞，不改环境假装验证成功。'
        elif p=='candidate':
            if s['resource_verification']=='fail':
                if s['revision_budget_remaining']<=0:nxt,args,basis='stop',{'operation':'stop_at_revision_budget'},'已知资源失败且预算耗尽，保留失败与费用，停止新修订。'
                else:nxt,args,basis='make',{'operation':'local_resource_repair'},'已有资源检查失败，针对实际问题局修，再完整复查。'
            elif s['resource_verification']!='pass':nxt,args,basis='make',{'operation':'finish_resource_reproduction_and_usage_checks'},'候选存在不等于可靠，在制作阶段核正常、边界、错误输入和公开用法。'
            elif not s['case_selection_complete']:nxt,args,basis='prepare',{'operation':'select_independent_real_cases'},'资源检查已给定通过，寻找同型、资料齐备、未用于学习的真实试做需求。'
            else:nxt,args,basis='actor',{'operation':'paired_trials_of_current_version','reuse_identical_baseline':True},'新版本需要实际试跑，保留相同任务/资源条件，已有同条件基线直接复用。'
        elif p=='prepared':
            if s['selected_case_count']<=0:nxt,args,basis='request_inputs',{'operation':'record_missing_or_inapplicable_inputs','run_business':False},'没有可独立执行的同型需求，不改题、不伪造附件、不为填槽试跑。'
            else:nxt,args,basis='actor',{'operation':'paired_trials_of_current_version','arms':['no_skill','workflow']},'真实独立case已给定，启动两臂同条件试做。'
        elif p=='trials_running':nxt,args,basis='wait',{'operation':'wait_for_existing_native_trials','do_not_duplicate':True},'原生业务尚在途，等待已派会话，不重复发起或提前判成功。'
        elif p=='trials_done':nxt,args,basis='review',{'operation':'review_current_version_delivery_quality_and_all_attempt_cost'},'两臂证据已给定齐备，分别核交付、资源使用和全部尝试成本。'
        elif p=='reviewed':
            if s['evidence_missing'] or s['all_attempt_cost']=='unknown':
                nxt,args,basis='recover_evidence',{'operation':'recover_existing_evidence','do_not_rerun_completed_trials':True},'先恢复已有日志/用量/版本证据，不补零或为找账重跑业务。'
            elif s['review_decision']=='reject':nxt,args,basis='stop',{'operation':'stop_no_benefit','preserve_attempts':True},'已有明确拒绝依据，停止该候选并保留旧过程。'
            elif s['review_decision']=='defer':nxt,args,basis='wait',{'operation':'defer_without_claiming_success'},'当前仍有条件未满足，保留未知，不冻结。'
            elif (s['review_decision']=='retain' and s['resource_verification']=='pass' and s['delivery_quality']=='pass'
                  and s['resource_actually_used'] is True and s['all_attempt_cost']=='reduced' and s['latest_pair_version_matches_candidate']):
                nxt,args,basis='finalize',{'operation':'freeze_verified_current_version'},'已给定对应版本的资源可靠、交付通过、实际使用和完整成本下降，可冻结当前版本。'
            elif s['revision_budget_remaining']<=0:nxt,args,basis='stop',{'operation':'stop_at_revision_budget'},'尚未达到保留依据且预算耗尽，停止新修订，不改写为成功。'
            else:nxt,args,basis='make',{'operation':'local_revision_then_matching_version_trial'},'根据当前失败或未减负证据局修，后续验证对应新版本；修订指令本身不证明修订正确。'
        else:raise AssertionError(p)
        if s.get('candidate_present'):args['candidate_version']=s['candidate_version']
        return action(nxt,args,basis,[refs.get(nxt,refs['retain'])])
    common=[state('new_conversation'),state('screened',route_decision='new'),state('candidate',candidate_present=True),
            state('candidate',candidate_present=True,resource_verification='pass'),
            state('prepared',candidate_present=True,resource_verification='pass',case_selection_complete=True,selected_case_count=1),
            state('trials_running',candidate_present=True,selected_case_count=1,paired_trial_state='one_arm_running'),
            state('trials_done',candidate_present=True,selected_case_count=1,paired_trial_state='both_done',latest_pair_version_matches_candidate=True)]
    passed=state('reviewed',candidate_present=True,resource_verification='pass',selected_case_count=1,
        paired_trial_state='both_done',latest_pair_version_matches_candidate=True,review_decision='retain',
        delivery_quality='pass',resource_actually_used=True,all_attempt_cost='reduced',evidence_missing=False)
    frozen=state('frozen',candidate_present=True)
    revision=state('reviewed',candidate_present=True,resource_verification='pass',review_decision='revise',
        delivery_quality='fail',resource_actually_used=True,all_attempt_cost='not_reduced')
    revised=[state('candidate',candidate_present=True,candidate_version='v1',case_selection_complete=True,selected_case_count=1),
        state('candidate',candidate_present=True,candidate_version='v1',resource_verification='pass',case_selection_complete=True,selected_case_count=1),
        state('trials_done',candidate_present=True,candidate_version='v1',selected_case_count=1,paired_trial_state='both_done',latest_pair_version_matches_candidate=True),
        {**passed,'candidate_version':'v1'},frozen]
    scenarios={
        'normal_freeze':common+[passed,frozen],
        'delivery_revision_then_fresh_version_trial':common+[revision]+revised,
        'no_reuse_value':[common[0],state('screened',route_decision='no_value')],
        'screen_defer_missing_originals':[common[0],state('screened',route_decision='defer')],
        'no_independent_case':common[:4]+[state('prepared',candidate_present=True,resource_verification='pass',case_selection_complete=True,selected_case_count=0)],
        'review_reject_no_benefit':common+[state('reviewed',review_decision='reject',all_attempt_cost='not_reduced')],
        'missing_cost_recovery_then_freeze':common+[state('reviewed',review_decision='defer',evidence_missing=True),passed,frozen],
        'revision_budget_stop':common+[{**revision,'revision_budget_remaining':0,'_explicit_overrides':revision['_explicit_overrides']+['revision_budget_remaining']}],
        'user_scope_stop':[common[0],{**common[1],'user_stop':True,'_explicit_overrides':common[1]['_explicit_overrides']+['user_stop']}],
        'resource_failure_local_repair':common[:3]+[state('candidate',candidate_present=True,resource_verification='fail')]+
            [{**common[3],'candidate_version':'v1','_explicit_overrides':common[3]['_explicit_overrides']+['candidate_version']}]+common[4:]+[passed,frozen],
        'reuse_existing_route_and_trials':[common[0],state('screened',route_decision='reuse')]+common[2:]+[passed,frozen],
        'environment_dependency_wait':common[:3]+[state('candidate',candidate_present=True,environment_capability_missing=True)],
    }
    values=[];continuity_checks=[]
    for name,states in scenarios.items():
        messages=[{'role':'system','content':SYSTEM+' 当前整条轨迹是source-free有限状态教学案例，所有状态均为假设，不是实际执行记录。'}]
        mask=[False];positions=[]
        prior=None;resolved=[]
        for i,raw_state in enumerate(states):
            explicit=set(raw_state['_explicit_overrides'])
            if prior is None:s={k:v for k,v in raw_state.items() if not k.startswith('_')}
            else:
                s=dict(prior);s['phase']=raw_state['phase']
                if 'candidate_version' in explicit and raw_state['candidate_version']!=prior['candidate_version']:
                    s.update(resource_verification='unknown',paired_trial_state='not_started',
                        latest_pair_version_matches_candidate=False,review_decision=None,
                        delivery_quality='unknown',resource_actually_used=None,all_attempt_cost='unknown',evidence_missing=False,
                        revision_budget_remaining=max(0,prior['revision_budget_remaining']-1))
                s.update({k:raw_state[k] for k in explicit})
            if prior and s['phase']=='frozen':continuity_checks.append(s['candidate_version']==prior['candidate_version'])
            if prior and s['candidate_version']==prior['candidate_version'] and prior['resource_verification']=='pass':
                continuity_checks.append(s['resource_verification']!='unknown')
            target=policy(s)
            if target['next_stage']=='finalize':
                continuity_checks.append(s['latest_pair_version_matches_candidate'] and s['resource_verification']=='pass'
                    and s['delivery_quality']=='pass' and s['resource_actually_used'] is True and s['all_attempt_cost']=='reduced'
                    and not s['evidence_missing'])
            resolved.append(s);prior=s
            messages.extend([{'role':'user','content':jdump({'scenario':name,'step':i,'hypothetical_state':s})},
                             {'role':'assistant','content':jdump(target)}]);mask.extend([False,True]);positions.append(len(messages)-1)
        provenance={}
        for mm in messages:
            if mm['role']=='assistant':
                for ref in json.loads(mm['content'])['evidence_refs']:provenance[(ref['path'],ref['sha256'],ref['line'])]=ref
        values.append({'schema_version':'wrd-v9-coordination-example-1.0','id':'coord_full_rule_'+sha(name)[:24],
            'episode_id':None,'route_id':None,'source_ids':[],'source_group_id':'source_free_full_controller_rules',
            'data_origin':'SYNTHETIC_HYPOTHETICAL_FULL_CONTROLLER_RULE_TRACE','annotation_is_original_teacher_CoT':False,
            'training_admitted':True,'scope_status':'SOURCE_INDEPENDENT_RULE_NO_ENTERPRISE_CONTENT',
            'messages':messages,'message_loss_mask':mask,'supervision_candidate_message_indices':positions,
            'recommended_relative_sampling_weight':0.05,'next_stage':'mixed_full_controller_sequence',
            'scenario':name,'count_as_real_task':False,'count_as_complete_real_autonomous_pipeline_task':False,
            'supersedes_training_view':'full_controller_rule_traces.synthetic.jsonl.gz',
            'rule_provenance':list(provenance.values()),'state_continuity_rule':'inherit_prior_observed_state; reset trial validation on explicitly observed new candidate version',
            'single_decision_view_is_not_an_additional_training_dataset':True,'example_view':'full_synthetic_controller_trace'})
    path=BASE_OUT/'full_controller_rule_traces.synthetic.v2.jsonl.gz';dump_rows(path,values)
    checks={'all_examples_hypothetical_not_teacher_CoT':all(x['annotation_is_original_teacher_CoT'] is False for x in values),
        'all_loss_positions_are_assistant_and_list_matches_mask':all(x['supervision_candidate_message_indices']==[i for i,v in enumerate(x['message_loss_mask']) if v]
            and all(x['messages'][i]['role']=='assistant' for i in x['supervision_candidate_message_indices']) for x in values),
        'no_enterprise_source_ids_in_content':all('conv_' not in jdump(x) for x in values),
        'all_user_states_explicitly_hypothetical':all(json.loads(m['content'])['hypothetical_state']['hypothetical_state']
            for x in values for m in x['messages'] if m['role']=='user'),
        'no_single_decision_duplicate_training_view':True,'only_data_generation_no_model_or_tool_execution':True}
    checks['frozen_version_and_verified_facts_preserved_across_state_transitions']=all(continuity_checks)
    assert all(checks.values())
    qa={'schema_version':'wrd-v9-full-controller-rule-trace-qa-1.0','status':'PASS','path':path.name,
        'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size,'trace_count':len(values),
        'assistant_targets':sum(len(x['supervision_candidate_message_indices']) for x in values),
        'scenarios':list(scenarios),'next_stage_counts':dict(collections.Counter(json.loads(m['content'])['next_stage']
            for x in values for m in x['messages'] if m['role']=='assistant')),'checks':checks,
        'pure_program_rule_annotation_not_performance_evidence':True,'rule_source_sha256':psha}
    q=BASE_OUT/'FULL_CONTROLLER_TRACE_V2_QA.json';assert not q.exists();q.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(qa,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--refresh-real-only',action='store_true')
    parser.add_argument('--output-revision')
    parser.add_argument('--audit-unknown-review',action='store_true')
    parser.add_argument('--export-case-overlay',type=Path)
    parser.add_argument('--export-full-controller-traces',action='store_true')
    args=parser.parse_args()
    if args.output_revision:
        assert re.fullmatch(r'[A-Za-z0-9_-]{1,64}',args.output_revision)
        OUT=BASE_OUT/args.output_revision
    if args.export_full_controller_traces:export_full_controller_traces()
    elif args.export_case_overlay:export_case_overlay(args.export_case_overlay)
    elif args.audit_unknown_review:audit_unknown_reviews()
    else:main(refresh_real_only=args.refresh_real_only)
