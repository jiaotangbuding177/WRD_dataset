"""Recover full-chain candidate coverage from frozen records, without agents/models.

Every assistant message remains a candidate/reference, not a semantic positive.
Controlled originals and the already-published privacy projection stay separate.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import time


def dumps(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def rows(p):
    op=gzip.open if p.suffix=='.gz' else open
    with op(p,'rt',encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def helper():
    p=Path(__file__).resolve().parents[1]/'wrd_training/training.py'
    spec=importlib.util.spec_from_file_location('frozen_wrd_training',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m,p


POLICY_TEXTS=('不得访问正式250测试任务或答案','不读正式250测试集','未引用正式250测试集')
STAGE_PURPOSE={'screen':'conversation_understanding_route_selection','make':'reuse_and_skill_resource_generation',
               'prepare':'learning_task_selection','review':'review_trial_interpretation_and_revision_request',
               'actor':'task_trial_execution_separate_role','legacy':'historical_execution_conditions_separate'}


def marker_audit(r,t):
    original=t._json(r['messages']);normalized=original;removed=Counter()
    for phrase in POLICY_TEXTS:
        n=normalized.count(phrase)
        if n:removed[phrase]=n;normalized=normalized.replace(phrase,'')
    hits=list(t.FORMAL_MARKER.finditer(normalized))
    return {'legacy_marker_flag':bool(r.get('benchmark_exposed')),
            'policy_phrase_occurrences':sum(removed.values()),
            'status':'unresolved_other_marker_requires_review' if hits else 'policy_mentions_only' if removed else 'no_marker_detected',
            'remaining_marker_count':len(hits),'semantic_nonoverlap_proven':False,
            'normalization_not_automatic_training_admission':True}


def richness(kind,m,t):
    calls=t._calls(m);names={c.get('name') for c in calls}
    if not calls:return 'assistant_text'
    if names<={'read','ls','process'}:return 'tool_io_or_process_control'
    if names & {'write','edit','apply_patch'}:
        return {'screen':'route_decision_or_resource_write','prepare':'task_selection_or_fixture_write',
                'review':'review_or_revision_report_write','make':'skill_resource_generation_or_revision'}.get(kind,'artifact_write')
    if 'exec' in names:return 'execution_or_programmatic_generation_needs_subclassification'
    return 'other_native_tool_action'


def export_sessions(source,out,old,t,controlled):
    counts=defaultdict(Counter);markers=defaultdict(Counter);tools=defaultdict(Counter);episode_ids=set();seen=set()
    shutil.copy2(source,out/'fullchain.native_sessions.jsonl.gz')
    with gzip.open(out/'assistant_targets.native.jsonl.gz','wt',encoding='utf-8',newline='\n',compresslevel=3) as f, \
         gzip.open(out/'stage_finals.native.jsonl.gz','wt',encoding='utf-8',newline='\n',compresslevel=3) as finals, \
         gzip.open(out/'episode_inventory.jsonl.gz','wt',encoding='utf-8',newline='\n',compresslevel=3) as eps:
        for episode_line,r in enumerate(rows(source),1):
            kind=r.get('kind','unknown');c=counts[kind];eid=r['episode_id'];episode_ids.add(eid);c['episodes']+=1
            ma=marker_audit(r,t);markers[kind][ma['status']]+=1
            ms=r['messages'];assistant=[i for i,m in enumerate(ms) if m.get('role')=='assistant'];last=assistant[-1] if assistant else None
            c['assistant_messages']+=len(assistant);c['native_verified_episodes']+=r.get('native_verified') is True
            ep={'episode_id':eid,'kind':kind,'purpose':STAGE_PURPOSE.get(kind,'unknown'),
                'source_session_line_1based':episode_line,'source_message_count':len(ms),'assistant_targets':len(assistant),
                'native_verified':r.get('native_verified'),'historical_episode_status':r.get('status'),
                'marker_audit':ma,'publication_approved':not controlled,'training_admitted':False}
            eps.write(dumps(ep)+'\n')
            for i in assistant:
                m=ms[i];identifier=hashlib.sha256((eid+':'+str(i)).encode()).hexdigest()[:24]
                if identifier in seen:raise ValueError('duplicate assistant position')
                seen.add(identifier);calls=t._calls(m);text=t._text(m);has_text=bool(text.strip());c['tool_action_messages']+=bool(calls);c['text_only_messages']+=bool(not calls and has_text);c['empty_messages']+=bool(not calls and not has_text)
                for call in calls:tools[kind][str(call.get('name'))]+=1
                historical=old.get(identifier,{});reasons=historical.get('filter_reasons',[])
                c['legacy_filter_pass']+=not reasons;c['legacy_filtered']+=bool(reasons)
                target={k:v for k,v in m.items() if k not in {'timestamp','details'}}
                row={'schema_version':'wrd-fullchain-native-target-v2','id':identifier,'episode_id':eid,'kind':kind,
                     'purpose':STAGE_PURPOSE.get(kind,'unknown'),'target_kind':'tool_calls' if calls else 'assistant_text' if has_text else 'empty',
                     'target_richness_heuristic':richness(kind,m,t),'heuristic_is_not_quality_gold':True,
                     'session_ref':'fullchain.native_sessions.jsonl.gz','session_line_1based':episode_line,
                     'prompt_messages_range_exclusive':[0,i],'system_ref':'same_session.system',
                     'target_message_index':i,'target_event_line':r.get('source_event_lines',[None]*len(ms))[i],
                     'completion_native':[target],'target_source_sha256':hashlib.sha256(dumps(m).encode()).hexdigest(),
                     'native_verified':r.get('native_verified'),'historical_episode_status':r.get('status'),
                     'context_fully_recoverable':r.get('context_fully_recoverable'),'legacy_filter_reasons':reasons,
                     'legacy_primary_stage':kind in {'make','screen'},'marker_audit':ma,
                     'actual_last_assistant':i==last,'observed_stop_reason':m.get('stopReason'),
                     'independent_new_task':False,'human_gold':False,'semantic_review':'not_reviewed_by_this_recovery',
                     'training_admitted':False,'publication_approved':not controlled,
                     'privacy_scope':'controlled historical credential-scrubbed source' if controlled else 'inherits previously cleared whole-session projection',
                     'future_artifact_added_to_prompt':False}
                f.write(dumps(row)+'\n')
                if i==last:
                    finals.write(dumps(row)+'\n');c['actual_last_assistant_targets']+=1
                    c['stop_text_finals']+=bool(not calls and has_text and m.get('stopReason')=='stop')
            if sum(x['episodes'] for x in counts.values())%250==0:print(dumps({'scope':'controlled' if controlled else 'public','episodes':len(episode_ids),'targets':len(seen)}),flush=True)
    return {'by_stage':{k:dict(v) for k,v in counts.items()},'marker_audit_by_stage':{k:dict(v) for k,v in markers.items()},
            'tools_by_stage':{k:dict(v) for k,v in tools.items()},'episodes':len(episode_ids),'assistant_targets':len(seen)},episode_ids


def archive_inventory(a,out,canonical_ids):
    source=a.bundle/'archive/file_index.jsonl';catalog={r['episode_id']:r for r in rows(a.bundle/'catalog/episodes.jsonl')}
    artifact_count=Counter();unique=set();pairs=defaultdict(dict);annotation_names=Counter();body_count=Counter();body_bytes=0
    text_extensions={'.md','.py','.js','.ts','.json','.txt','.yaml','.yml','.sh','.html','.css'}
    with gzip.open(out/'episode_output_artifacts.index.jsonl.gz','wt',encoding='utf-8',newline='\n',compresslevel=3) as refs, \
         gzip.open(out/'resource_and_stage_artifact_texts.jsonl.gz','wt',encoding='utf-8',newline='\n',compresslevel=3) as bodies:
        for r in rows(source):
            logical=r['logical_path'].replace('\\','/');parts=logical.split('/');basename=parts[-1]
            if re.search(r'(?:annotat|understand|source[_-](?:digest|summary|analysis))',basename,re.I):annotation_names[parts[0]+':'+Path(basename).suffix]+=1
            if len(parts)<3 or parts[0]!='episodes':continue
            eid=parts[1];kind=catalog.get(eid,{}).get('kind','unknown');relative='/'.join(parts[2:])
            if eid not in canonical_ids and relative in {'request.json','response.json','result.json','openclaw_transport/request.json','openclaw_transport/response.json'}:pairs[eid][relative]={'sha256':r['sha256'],'object':r['object'],'bytes':r['bytes']}
            if not relative.startswith('workspace/outputs/'):continue
            artifact_count[kind]+=1
            item={'episode_id':eid,'kind':kind,'logical_path':logical,'stored_sha256':r['sha256'],'source_sha256':r['source_sha256'],
                  'bytes':r['bytes'],'cas_object':r['object'],'artifact_injected_into_past_prompt':False,'training_admitted':False,'publication_approved':False}
            refs.write(dumps(item)+'\n')
            wanted=relative.startswith('workspace/outputs/skill/') or (kind in {'prepare','review','screen','make'} and Path(basename).suffix=='.json')
            if not wanted or Path(basename).suffix.lower() not in text_extensions or r['sha256'] in unique:continue
            p=a.bundle/r['object']
            if not p.is_file():p=a.bundle/'archive'/r['object']
            if not p.is_file():body_count['missing_cas_object']+=1;continue
            raw=p.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('CAS object hash mismatch')
            try:content=raw.decode('utf-8-sig')
            except UnicodeDecodeError:body_count['non_utf8_object_indexed_not_decoded']+=1;continue
            unique.add(r['sha256']);body_count[kind]+=1;body_bytes+=len(raw)
            bodies.write(dumps({**item,'content':content,'evidence_type':'observed_artifact_not_native_assistant_message',
                'requires_task_context_and_quality_audit_before_sft':True,'duplicate_aliases_not_new_examples':True})+'\n')
    save(out/'missing_canonical_evidence.json',{'missing_episode_count':len(set(catalog)-canonical_ids),
        'episodes':[{'episode_id':eid,'kind':catalog[eid].get('kind'),'request_response_result_references':pairs.get(eid,{}),
            'status':'needs_request_response_parser_not_silently_discarded'} for eid in sorted(set(catalog)-canonical_ids)]})
    return {'output_artifact_aliases_by_stage':dict(artifact_count),'unique_text_objects_by_stage':dict(body_count),
            'unique_resource_or_stage_json_text_objects':len(unique),'text_object_bytes':body_bytes,
            'annotation_like_filename_counts_not_proof_of_label_recovery':dict(annotation_names)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--public-sessions',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('new output directory required')
    a.output.mkdir(parents=True);start=time.monotonic();t,h=helper()
    watched=[a.bundle/'canonical/native_episodes.jsonl.gz',a.bundle/'training_audit/action_index.jsonl',a.bundle/'archive/file_index.jsonl',a.public_sessions]
    before={str(x):digest(x) for x in watched};old={r['id']:r for r in rows(watched[1])}
    controlled=a.output/'controlled_master';public=a.output/'public_projection';controlled.mkdir();public.mkdir()
    master,ids=export_sessions(watched[0],controlled,old,t,True)
    projection,_=export_sessions(a.public_sessions,public,old,t,False)
    archive=archive_inventory(a,controlled,ids)
    for x in watched:
        if digest(x)!=before[str(x)]:raise ValueError('source changed')
    report={'schema_version':'wrd-fullchain-coverage-reaudit-v2','status':'CANDIDATE_RECOVERY_COMPLETE_NOT_TRAINING_ADMISSION',
            'controlled_master':master,'public_projection':projection,'artifact_recovery':archive,
            'previous_primary_stage_policy':'make/screen only; prepare/review/actor emitted as metadata-only auxiliary after legacy filters',
            'previous_93_are_not_fullchain_training_data':True,'all_recovered_targets_are_candidates_not_approved_positives':True,
            'legacy_marker_flags_are_not_confirmed_leakage':True,'no_formal_eval_outputs_newly_ingested':True,
            'original_sources_unchanged':True,'source_sha256':before,'audit_script_sha256':digest(Path(__file__)),
            'historical_helper_sha256':digest(h),'training_started':False,'new_model_calls':0,'elapsed_seconds':round(time.monotonic()-start,3)}
    save(a.output/'FULLCHAIN_COVERAGE.json',report)
    save(a.output/'CONTROLLED_ONLY.json',{'controlled_master_must_not_be_publicly_uploaded':True,
         'public_projection_comes_only_from_previously_cleared_sessions':True,'not_a_train_launch_configuration':True,
         'training_admitted_by_this_recovery':0,'candidate_count_does_not_equal_correctness_or_independent_tasks':True})
    print(dumps({'episodes':master['episodes'],'targets':master['assistant_targets'],'public_targets':projection['assistant_targets'],'artifact_texts':archive['unique_resource_or_stage_json_text_objects'],'elapsed_seconds':report['elapsed_seconds']}),flush=True)


if __name__=='__main__':main()
