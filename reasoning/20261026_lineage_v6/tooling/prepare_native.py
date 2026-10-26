"""Inventory the fixed 91 real native contexts without granting admission.

Preserves original contexts, tool-call/result edges, observed output labels and
quality masks. Outer stage dispatch, original model actions and later derived
annotations are separate. No fabricated conversation or environment result.
"""
from __future__ import annotations
import ast
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/20261025_wrd_reasoning_recovery_v4'
BUNDLE=ROOT/'output/20261025_wrd_training_dataset/bundle'
OUT=ROOT/'output/20261026_wrd_sequences_v6'
FROZEN_COMMIT='4cc8fdb9097c55a4b1fce84da6fc628f6d600ea3'
VIS_REL='reasoning/20261026_strict226/VISIBILITY_REVIEW.json'

def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def bsha(x):return hashlib.sha256(x).hexdigest()
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def rows(p):
    op=gzip.open if str(p).endswith('.gz') else open
    with op(p,'rt',encoding='utf-8-sig') as f:
        for l in f:
            if l.strip():yield json.loads(l)
def dump(p,rs):
    p.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(p,'wt',encoding='utf-8',newline='\n') as f:
        for r in rs:f.write(js(r)+'\n')
def save(p,r):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def blocks(m):return m.get('content',[]) if isinstance(m.get('content'),list) else []
def calls(m):return [b for b in blocks(m) if isinstance(b,dict) and b.get('type')=='toolCall']
def texts(m):
    if isinstance(m.get('content'),str):return [m['content']]
    return [b.get('text','') for b in blocks(m) if isinstance(b,dict) and b.get('type')=='text']
def target_id(e,i):return bsha((e+':'+str(i)).encode())[:24]
def safe_json(s):
    try:return json.loads(s)
    except (ValueError,TypeError):return None
def write_syntax_hold(m):
    reasons=[]
    for c in calls(m):
        if c.get('name')!='write' or not isinstance(c.get('arguments'),dict):continue
        a=c['arguments'];p=str(a.get('path',a.get('file_path','')));body=a.get('content')
        if not isinstance(body,str):continue
        try:
            if p.lower().endswith('.py'):ast.parse(body)
            elif p.lower().endswith('.json'):json.loads(body,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonstandard')))
        except (ValueError,SyntaxError,RecursionError):reasons.append('generated_declared_python_or_json_not_parseable_requires_review')
    return sorted(set(reasons))

def candidate_record(r,quality_holds):
    r=deepcopy(r);spans=[]
    for t in r['targets']:
        why=quality_holds.get(t['id'],[])
        if why:
            t['candidate_quality_hold_reasons']=why
            t['owned_supervision_spans']=[];t['supervised_tokens']=0
        t['candidate_owned_supervision_spans']=t['owned_supervision_spans']
        t['candidate_supervised_tokens']=t['supervised_tokens']
        spans.extend(t['owned_supervision_spans'])
        t['owned_supervision_spans']=[];t['supervised_tokens']=0
    r['candidate_supervision_spans']=sorted(spans)
    r['candidate_supervised_tokens']=sum(s[1]-s[0] for s in spans)
    r['candidate_supervision_spans_sha256']=bsha(js(sorted(spans)).encode())
    r['candidate_supervised_tokens_by_component']=dict(sum((Counter({s[2]:s[1]-s[0]}) for s in spans),Counter()))
    r['supervision_spans']=[];r['supervised_tokens']=0;r['supervised_tokens_by_component']={}
    r['supervision_spans_sha256']=bsha(js([]).encode())
    r['training_admitted']=False;r['training_manifest_admitted']=False
    r['lineage_admission_pending']=True;r['full_autonomous_controller_demonstration']=False
    r['candidate_is_not_active_training_loss']=True
    return r

def main():
    local_vis=ROOT/'output/20261026_wrd_strict226_expansion/VISIBILITY_REVIEW.json'
    raw=subprocess.run(['git','-C',str(ROOT/'output/20261025_wrd_training_dataset/git_release'),
        'show',FROZEN_COMMIT+':'+VIS_REL],check=True,capture_output=True).stdout
    frozen=json.loads(raw);current=json.loads(local_vis.read_text(encoding='utf-8'))
    ids=set(frozen['pending_positive_candidate_episode_ids'])
    assert ids==set(current['pending_positive_candidate_episode_ids']) and len(ids)==91
    save(OUT/'FROZEN_NATIVE91_SET.json',{'source_git_commit':FROZEN_COMMIT,'source_git_path':VIS_REL,
        'source_git_blob_sha256':bsha(raw),'local_visibility_report_sha256':digest(local_vis),
        'episode_ids':sorted(ids),'local_and_git_episode_id_sets_equal':True})
    source=BUNDLE/'canonical/native_episodes.jsonl.gz'
    episodes={r['episode_id']:r for r in rows(source) if r['episode_id'] in ids};assert set(episodes)==ids
    artifact_path=ROOT/'output/20261025_wrd_fullchain_reaudit/controlled_linkage/input_artifacts.jsonl.gz'
    artifacts=[r for r in rows(artifact_path) if r['episode_id'] in ids]
    artifact_by_e=defaultdict(list)
    for a in artifacts:artifact_by_e[a['episode_id']].append(a)
    structured_path=ROOT/'output/20261025_wrd_fullchain_reaudit/controlled_linkage/structured_decisions.jsonl.gz'
    structured=[r for r in rows(structured_path) if r['original_episode_id'] in ids or set(r['episode_ids'])&ids]
    extracted_path=ROOT/'output/20261025_wrd_fullchain_reaudit/controlled_linkage/stage_decisions.extracted.jsonl.gz'
    extracted=[r for r in rows(extracted_path) if r['episode_id'] in ids or set(r.get('episode_ids',[]))&ids]
    file_index_path=BUNDLE/'archive/file_index.jsonl'
    files=[r for r in rows(file_index_path) if r['logical_path'].startswith('episodes/') and r['logical_path'].split('/')[1] in ids]
    # Preserve the exact global review policy including the timeout erratum.
    sys.path.insert(0,str(ROOT/'research/data_prep/wrd_training_preflight'))
    from prepare import review_map
    reviews=review_map(ROOT/'output/20261025_wrd_training_preflight/local_review')
    errata_path=ROOT/'output/20261025_wrd_training_dataset/git_release/preflight/20261025/ANNOTATION_ERRATA.json'
    for fix in json.loads(errata_path.read_text(encoding='utf-8-sig'))['corrections']:
        if fix['id'] in reviews:reviews[fix['id']]['decision']=fix['effective_semantic_decision']
    rejects={i for i,r in reviews.items() if r['decision']=='reject'};assert len(rejects)==61
    quality_holds={i:['prior_local_ai_reject_retained_as_hold_not_human_gold'] for i in rejects}
    for e in episodes.values():
        for i,m in enumerate(e['messages']):
            why=write_syntax_hold(m) if m.get('role')=='assistant' else []
            if why:quality_holds[target_id(e['episode_id'],i)]=sorted(set(quality_holds.get(target_id(e['episode_id'],i),[])+why))
    full_path=BASE/'native_compiled_controlled_final/full_stage_records.jsonl.gz'
    full={r['episode_id']:r for r in rows(full_path) if r['episode_id'] in ids};assert set(full)==ids
    candidates={e:candidate_record(r,quality_holds) for e,r in full.items()}
    selected={scope:[r for r in rows(BASE/('curated_native/'+scope+'.core32k.jsonl.gz')) if r['episode_id'] in ids]
              for scope in ('controlled','public')}
    edges=[];message_index=[];summaries=[];writes=defaultdict(list);feedback_edges=[];quality=[]
    totals=Counter();by_kind=defaultdict(Counter)
    for eid,e in sorted(episodes.items()):
        pending={};counts=Counter();first_time=None;last_time=None;feedback_observations=[]
        for i,m in enumerate(e['messages']):
            role=m.get('role');counts[role+'_messages']+=1
            mh=bsha(js(m).encode());entry={'episode_id':eid,'native_message_index':i,
                'source_event_line':e['source_event_lines'][i],'role':role,'message_sha256':mh}
            if m.get('timestamp') is not None:
                first_time=m['timestamp'] if first_time is None else min(first_time,m['timestamp'])
                last_time=m['timestamp'] if last_time is None else max(last_time,m['timestamp'])
            if role=='assistant':
                tid=target_id(eid,i);entry['target_id']=tid
                thought=m.get('reasoning_content') or ''.join(str(b.get('thinking',b.get('text',''))) for b in blocks(m)
                    if isinstance(b,dict) and b.get('type') in {'thinking','reasoning'})
                visible=''.join(texts(m));counts['original_R_messages']+=bool(thought);counts['original_R_characters']+=len(thought)
                counts['visible_text_messages']+=bool(visible);counts['visible_text_characters']+=len(visible)
                entry['recorded_reasoning_characters']=len(thought);entry['visible_text_characters']=len(visible)
                entry['transition_origin']='observed_model_decision'
                counts['non_tool_response_endpoints']+=not bool(calls(m)) and bool(visible)
                if tid in quality_holds:quality.append({'id':tid,'episode_id':eid,'reasons':quality_holds[tid]})
                for c in calls(m):
                    cid=c.get('id');a=c.get('arguments');name=c.get('name');counts['tool_calls']+=1;counts['tool:'+str(name)]+=1
                    if cid in pending:counts['duplicate_call_ids']+=1
                    pending[cid]=(i,tid,c)
                    if name=='write' and isinstance(a,dict) and isinstance(a.get('content'),str):
                        path=str(a.get('path',a.get('file_path','')))
                        writes[eid].append({'target_id':tid,'source_message_index':i,'source_event_line':e['source_event_lines'][i],
                            'path':path,'content_sha256':bsha(a['content'].encode()),'parsed':safe_json(a['content'])})
                        if path.endswith('/SKILL.md'):counts['skill_md_write_actions_not_freeze']+=1
                    if name in {'edit','apply_patch'}:
                        counts['local_edit_or_patch_actions']+=1
                        for fi,artifact_sha in feedback_observations:
                            feedback_edges.append({'episode_id':eid,'feedback_native_message_index':fi,
                                'feedback_artifact_sha256':artifact_sha,'later_revision_target_id':tid,
                                'revision_native_message_index':i,'edge_type':'actual_feedback_observation_temporally_precedes_model_edit',
                                'annotation_origin':'derived_temporal_annotation_not_proven_specific_causality'})
            elif role in {'tool','toolResult'}:
                cid=m.get('toolCallId',m.get('tool_call_id'));entry['tool_call_id']=cid
                predecessor=pending.pop(cid,None)
                if predecessor:
                    ai,tid,c=predecessor;counts['matched_action_result_edges']+=1
                    edges.append({'episode_id':eid,'edge_type':'original_native_tool_call_result',
                        'parent_target_id':tid,'assistant_native_message_index':ai,'tool_result_native_message_index':i,
                        'tool_call_id':cid,'tool_name':c.get('name'),'assistant_source_event_line':e['source_event_lines'][ai],
                        'result_source_event_line':e['source_event_lines'][i],'result_message_sha256':mh,
                        'is_error':m.get('isError'),'transition_origin':'observed_model_action_and_actual_environment_result'})
                else:counts['orphan_tool_results']+=1
                counts['tool_error_results']+=bool(m.get('isError'))
                # Exact complete JSON feedback observation only; a read path or
                # a delivered feedback file is not sufficient.
                parsed=[safe_json(t) for t in texts(m)]
                for a in artifact_by_e[eid]:
                    if a['artifact_name']=='previous_feedback.json' and any(v is not None and v==a['content'] for v in parsed):
                        feedback_observations.append((i,a['sha256']));counts['exact_feedback_json_observations']+=1
            message_index.append(entry)
        counts['unreturned_tool_calls']=len(pending)
        totals.update(counts);by_kind[e['kind']].update(counts)
        candidates[eid]['process_stage_provenance']={'origin':'outer_pipeline', 'original_dispatch_kind':e['kind'],
            'learner_autonomous_stage_transition_proven':False,
            'module':'C_prepare_requirement_selection' if e['kind']=='prepare' else
                'B_build_resources_D_package_candidate_without_freeze' if e['kind']=='make' else 'legacy_business_execution_not_WRD_A'}
        summaries.append({'episode_id':eid,'kind':e['kind'],'job_id':e['job_id'],'route_id':e['route_id'],
            'status':e['status'],'native_verified':e['native_verified'],'context_fully_recoverable':e['context_fully_recoverable'],
            'original_system_recovered':isinstance(e.get('system'),str) and bool(e.get('system')),
            'original_episode_canonical_sha256':bsha(js(e).encode()),'first_timestamp':first_time,'last_timestamp':last_time,
            'counts':dict(counts),'stage_annotation_origin':'outer_pipeline',
            'full_autonomous_pipeline_demonstration_proven':False})
    labels=[];mapped=Counter()
    for original in structured:
        r=deepcopy(original);parents=[]
        relevant=set(r['episode_ids'])&ids
        if r['original_episode_id'] in ids:relevant.add(r['original_episode_id'])
        relative=r['logical_path'].split('/workspace/',1)[-1]
        mounted='/workspace/'+relative
        for eid in relevant:
            for w in writes[eid]:
                if w['path'].lstrip('/') not in {mounted.lstrip('/'),relative.lstrip('/')} and not w['path'].endswith('/'+relative):continue
                if w['content_sha256']==r['artifact_sha256']:
                    parents.append({k:v for k,v in w.items() if k!='parsed'}|{'episode_id':eid,'mapping':'byte_exact_original_write_content_to_artifact_sha256'})
                elif not r['json_pointer'] and w['parsed']==r['label']:
                    parents.append({k:v for k,v in w.items() if k!='parsed'}|{'episode_id':eid,'mapping':'same_path_complete_original_write_JSON_equal_to_original_output_document'})
        r['parent_native_targets']=parents
        r['label_origin']='observed_model_decision' if parents else 'observed_structured_output_artifact_without_exact_response_link'
        r['missing_original_decision_reason_or_close_fields_not_invented']=True
        r['original_fields_present']=sorted(r['label']) if isinstance(r['label'],dict) else []
        r['closure_semantics']='original_candidate_making_report_not_retain_or_frozen' if r['unit']=='making_report' else 'original_business_requirement_selection_not_actor_execution'
        r['is_additional_independent_training_target']=False;r['future_artifact_added_to_past_prompt']=False
        labels.append(r);mapped[r['label_origin']]+=1
    grouped=defaultdict(list)
    for e in summaries:grouped[e['route_id']].append(e)
    groups=[]
    for route,items in sorted(grouped.items()):
        items=sorted(items,key=lambda x:(x['first_timestamp'] or 0,x['episode_id']))
        groups.append({'group_id':bsha(route.encode())[:24],'route_id':route,
            'episode_interfaces':[{'episode_id':i['episode_id'],'kind':i['kind'],'job_id':i['job_id'],
                'context_source':'native91.original_contexts.jsonl.gz','context_canonical_sha256':i['original_episode_canonical_sha256']} for i in items],
            'grouping_origin':'outer_pipeline_route_metadata','actual_cross_episode_resource_causality_requires_lineage_edges':True,
            'must_not_concatenate_as_one_original_conversation':True,'full_autonomous_chain_proven':False})
    outputs={
        'native91.original_contexts.jsonl.gz':episodes.values(),'native91.input_artifacts.original.jsonl.gz':artifacts,
        'native91.file_dependencies.original_index.jsonl.gz':files,'native91.message_index.jsonl.gz':message_index,
        'native91.action_observation_edges.jsonl.gz':edges,'native91.feedback_revision_temporal_edges.jsonl.gz':feedback_edges,
        'native91.structured_decisions.mapped.jsonl.gz':labels,'native91.stage_fields.original.jsonl.gz':extracted,
        'native91.episode_inventory.jsonl.gz':summaries,'native91.task_group_interfaces.jsonl.gz':groups,
        'native91.quality_holds.jsonl.gz':quality,'native91.candidate_full_stage.jsonl.gz':candidates.values(),
        'native91.candidate_common32k.jsonl.gz':[candidate_record(r,quality_holds) for r in selected['controlled']],
    }
    for n,rs in outputs.items():dump(OUT/'controlled'/n,rs)
    public_candidates=[candidate_record(r,{}) for r in selected['public']]
    dump(OUT/'public/native91.candidate_common32k.jsonl.gz',public_candidates)
    global_length={t['id'] for r in rows(full_path) for t in r['targets'] if t.get('observed_native_stop_reason')=='length' and t.get('nonempty')}
    assert len(global_length)==9
    all91ids={t['id'] for r in full.values() for t in r['targets']}
    def profile_stats(rs,candidate=False):
        return {'windows':len(rs),'by_stage':dict(Counter(r['kind'] for r in rs)),
            'input_tokens':sum(r['total_tokens'] for r in rs),
            'positive_targets':sum(sum(bool(t['owned_supervision_spans']) for t in r['targets']) for r in rs),
            'supervised_tokens':sum(r['supervised_tokens'] for r in rs),
            'le16k_windows':sum(r['total_tokens']<=16384 for r in rs),
            'le32k_windows':sum(r['total_tokens']<=32768 for r in rs),
            'complete_stage_windows':sum(r['stage_complete_in_this_view'] for r in rs),
            'explicit_prefix_windows':sum(not r['stage_complete_in_this_view'] for r in rs)}
    report={'schema_version':'wrd-v6-fixed-native91-sequence-preparation','frozen_git_commit':FROZEN_COMMIT,
        'fixed_episode_count':len(ids),'source_kinds':dict(Counter(e['kind'] for e in episodes.values())),
        'source_kind_screen_is_legacy_business_resume_screening_not_WRD_A':True,
        'actual_WRD_A_route_screen_episodes':0,'actual_C_review_efficiency_episodes':0,
        'actual_C_prepare_requirement_selection_episodes':16,'actual_B_candidate_make_episodes':71,
        'D_skill_md_writes_are_candidate_packaging_not_freeze':True,'D_frozen_retain_events_proven':0,
        'native_counts':dict(totals),'native_counts_by_original_kind':{k:dict(v) for k,v in by_kind.items()},
        'existing_controlled_quality_profile':profile_stats(selected['controlled']),
        'existing_public_quality_profile':profile_stats(selected['public']),
        'full_context_archive':{'windows':len(full),'input_tokens':sum(r['total_tokens'] for r in full.values()),
            'le16k_windows':sum(r['total_tokens']<=16384 for r in full.values()),
            'le32k_windows':sum(r['total_tokens']<=32768 for r in full.values())},
        'unavailable_curated_episodes':[{'episode_id':eid,'kind':full[eid]['kind'],
            'original_positive_tokens':full[eid]['supervised_tokens'],
            'mechanical_reasons':dict(Counter(x for t in full[eid]['targets'] for x in t['mechanical_reasons']))}
            for eid in sorted(ids-{r['episode_id'] for r in selected['controlled']})],
        'structured_documents_in_fixed_91':len(labels),'structured_documents_by_unit':dict(Counter(r['unit'] for r in labels)),
        'structured_document_to_parent_response_mapping':dict(mapped),
        'old_119_structured_candidate_documents_cover_whole_1763_not_only_these_91':True,
        'child_stage_fields_not_additive_independent_examples':len(extracted),
        'file_dependency_index_rows':len(files),'file_dependency_unique_sha256':len({r['sha256'] for r in files}),
        'file_dependency_logical_bytes_including_duplicates':sum(r['bytes'] for r in files),
        'task_groups_from_route_metadata_not_independent_sources':len(groups),
        'global_known_AI_reject_target_ids':len(rejects),'known_AI_reject_targets_in_fixed_91':len(rejects&all91ids),
        'global_nonempty_length_target_ids':len(global_length),'length_targets_in_fixed_91':len(global_length&all91ids),
        'all_known_rejects_syntax_holds_and_truncated_responses_zero_loss':True,
        'original_R_messages_in_fixed_91':totals['original_R_messages'],
        'stage_control_provenance':{'stage_dispatch':'outer_pipeline','native_tool_decisions':'observed_model_decision',
            'temporal_feedback_edges_and_module_labels':'derived_annotation','autonomous_inter_stage_control_proven':False},
        'actual_final_training_admissions_created':0,'all_active_v6_candidate_spans_zero_until_lineage_admission':True,
        'no_source_context_deleted_or_future_resource_added':True,'new_model_calls':0,'training_started':False,
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [local_vis,source,artifact_path,structured_path,extracted_path,file_index_path,full_path,errata_path]},
        'outputs':{n:{'sha256':digest(OUT/'controlled'/n),'bytes':(OUT/'controlled'/n).stat().st_size} for n in outputs},
        'public_candidate_output':{'path':'public/native91.candidate_common32k.jsonl.gz','sha256':digest(OUT/'public/native91.candidate_common32k.jsonl.gz')},
        'script_sha256':digest(Path(__file__))}
    save(OUT/'NATIVE91_PREPARATION_REPORT.json',report)
    print(js({k:report[k] for k in ['fixed_episode_count','original_R_messages_in_fixed_91','structured_documents_in_fixed_91',
        'structured_document_to_parent_response_mapping','existing_controlled_quality_profile','existing_public_quality_profile','known_AI_reject_targets_in_fixed_91']}),flush=True)

if __name__=='__main__':main()
