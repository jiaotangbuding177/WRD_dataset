"""Raw-address census anchored in all 29 retained skills, not an SFT funnel.

Read frozen catalogs/CAS and, optionally, compare the production database via
SQLite mode=ro. Inventory every stage, failed attempt and discarded route.
Do not train, select training admission, mutate production or walk live run
trees. The sibling physical census supplies that independent root inventory.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[3]
BUNDLE=ROOT/'output/20261025_wrd_training_dataset/bundle'
OUT=ROOT/'output/20261026_wrd_raw_census_v7'
PRODUCTION=ROOT/'output/workflow_library'
STAGES=('screen','prepare','make','review','actor')
KEY_NAMES={'execution.json','request.json','response.json','result.json','usage.json','accounting.json',
    'native_events.jsonl','dispatch.json','session_events.jsonl','container_receipt.json','host_receipt.json',
    'native_result.json','episode_turns.json','skill_reads.json','tools.json','prompts.json','system-prompt.txt',
    'session-branch.json','metadata.json','events.jsonl','manifest.json','artifacts.json'}
SENSITIVE_PARTS=('credential','password','secret','api_key','access_token','refresh_token','private_key')

def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def bsha(x):return hashlib.sha256(x).hexdigest()
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def read_json(p,default=None):
    try:return json.loads(p.read_text(encoding='utf-8-sig'))
    except (ValueError,UnicodeError,OSError):return default
def rows(p):
    op=gzip.open if str(p).endswith('.gz') else open
    with op(p,'rt',encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def dump(p,values):
    p.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(p,'wt',encoding='utf-8',newline='\n',compresslevel=3) as f:
        for value in values:f.write(js(value)+'\n')
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def norm(value):return str(value or '').replace('/','\\').rstrip('\\').lower()
def abs_path(value):return isinstance(value,str) and bool(re.match(r'^[A-Za-z]:[\\/]',value)) and '\n' not in value
def walk(value,pointer=''):
    if isinstance(value,dict):
        for key,child in value.items():
            yield pointer+'/'+str(key),str(key),child
            if isinstance(child,(dict,list)):yield from walk(child,pointer+'/'+str(key))
    elif isinstance(value,list):
        for i,child in enumerate(value):
            if isinstance(child,(dict,list)):yield from walk(child,pointer+'/'+str(i))
def references(value):
    for pointer,key,v in walk(value):
        if any(part in pointer.lower() for part in SENSITIVE_PARTS):continue
        if abs_path(v) and any(part in key.lower() for part in ('file','path','dir','root','consumer','profile','episode')):
            yield {'json_pointer':pointer,'path':v,'exists':Path(v).exists()}
@lru_cache(maxsize=None)
def cas_object_path(obj):
    choices=[BUNDLE/'archive'/obj,BUNDLE/obj]
    return next((p for p in choices if p.is_file()),None)
def cas_path(row):return cas_object_path(row['object'])
def raw_stage(ep,request=None):
    if ep.get('cohort')=='imported_history' and request:
        task=str(request.get('task_id',''));stage=request.get('stage')
        if stage=='evaluation' and re.search(r'_c\d+_(?:no_skill|workflow)$',task):return 'legacy_business_actor'
        if stage=='generation' and task.endswith('_blindjudge'):return 'legacy_blind_judge'
        if stage=='generation' and task.endswith('_devprep'):return 'legacy_devprep'
        if stage=='generation' and re.fullmatch(r'(?:resolve_)?screen_\d+',task):return 'legacy_WRD_screen'
        if stage=='generation' and re.fullmatch(r'route_merge_\d+',task):return 'legacy_route_merge'
        if stage=='generation' and re.search(r'__make\d+$',task):return 'legacy_skill_make'
    name=Path(ep['source_path']).name.lower()
    if ep.get('cohort')=='imported_history' and re.search(r'_c\d+_(?:no_skill|workflow|blindjudge)',name):
        return 'legacy_business_actor_or_judge'
    return ep['kind']

def live_ro_comparison(frozen_jobs,frozen_routes):
    path=PRODUCTION/'state.db';before={p.name:{'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}
        for p in (path,Path(str(path)+'-wal')) if p.is_file()}
    with sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True,timeout=10) as cx:
        cx.execute('PRAGMA query_only=ON');cx.execute('BEGIN')
        job_ids={r[0] for r in cx.execute('SELECT id FROM jobs')}
        stages={r[0]:r[1] for r in cx.execute('SELECT kind,COUNT(*) FROM jobs GROUP BY kind')}
        routes=[json.loads(r[0]) for r in cx.execute('SELECT payload FROM routes ORDER BY id')]
        sources=cx.execute('SELECT COUNT(*) FROM sources').fetchone()[0]
        cx.rollback()
    after={p.name:{'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}
        for p in (path,Path(str(path)+'-wal')) if p.is_file()}
    frozen_ids={r['id'] for r in frozen_routes if r.get('library_status')=='retained'}
    live_ids={r['id'] for r in routes if r.get('library_status')=='retained'}
    return {'uri_mode':'ro','query_only':True,'production_database':str(path),'source_rows':sources,
        'live_jobs':len(job_ids),'live_jobs_by_stage':stages,'live_routes':len(routes),
        'live_retained_skill_ids':sorted(live_ids),'frozen_retained_skill_ids':sorted(frozen_ids),
        'live_and_frozen_retained_sets_equal':live_ids==frozen_ids,
        'live_and_frozen_job_id_sets_equal':job_ids=={j['id'] for j in frozen_jobs},
        'new_live_job_ids_since_snapshot':sorted(job_ids-{j['id'] for j in frozen_jobs}),
        'database_and_WAL_stat_before':before,'database_and_WAL_stat_after':after,
        'database_and_WAL_stat_unchanged_during_read':before==after,'no_write_SQL_or_checkpoint_executed':True}

def main():
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'indexes').mkdir(exist_ok=True);(OUT/'skills29').mkdir(exist_ok=True)
    catalogs=BUNDLE/'catalog'
    routes=list(rows(catalogs/'routes.jsonl'));jobs=list(rows(catalogs/'jobs.jsonl'));episodes=list(rows(catalogs/'episodes.jsonl'))
    meta=read_json(catalogs/'state_meta.json',{});source_table=read_json(catalogs/'state_other_tables.json',{})['sources']
    retained={r['id']:r for r in routes if r.get('library_status')=='retained'};assert len(retained)==29
    jobs_by_id={j['id']:j for j in jobs};episodes_by_id={e['episode_id']:e for e in episodes}
    ep_by_path=defaultdict(set);ep_by_job=defaultdict(set)
    for e in episodes:
        ep_by_path[norm(e['source_path'])].add(e['episode_id'])
        for jid in e['job_refs']:ep_by_job[jid].add(e['episode_id'])
    job_edges=[];job_path_refs=[]
    for job in jobs:
        for pointer,key,v in walk(job):
            if isinstance(v,str) and v in jobs_by_id and v!=job['id'] and any(t in key.lower() for t in ('job','reuse','previous','prior')):
                job_edges.append({'consumer_job_id':job['id'],'referenced_job_id':v,'json_pointer':pointer,
                    'relation':'exact_recorded_job_reference_not_new_execution'})
            if not any(part in pointer.lower() for part in SENSITIVE_PARTS) and abs_path(v) and any(t in key.lower() for t in ('file','path','dir','root','episode')):
                job_path_refs.append({'job_id':job['id'],'route_id':job['route_id'],'json_pointer':pointer,'path':v,'exists':Path(v).exists()})
        for p in (job.get('episode'),(job.get('result') or {}).get('episode_dir')):
            ep_by_job[job['id']].update(ep_by_path.get(norm(p),set()))
    ep_meta=defaultdict(list);file_counts=Counter();file_bytes=Counter();output_files=defaultdict(list);request_interfaces={}
    gold_files=defaultdict(list);frozen_native_events={};provider_refs=[];alias_event_hashes=defaultdict(set)
    api_requests={};usage_slices={};api_without_ids=[];original_paths=set();archive_files=0
    index_path=BUNDLE/'archive/file_index.jsonl'
    source_index_paths=[];history_paths=[]
    with gzip.open(OUT/'indexes/episode_files.all.jsonl.gz','wt',encoding='utf-8',newline='\n',compresslevel=3) as file_out:
        for row in rows(index_path):
            logical=row['logical_path'];parts=logical.split('/')
            if logical.startswith('pipeline/selected_followup_20261024/final/') and '/skills/' not in logical:
                source_index_paths.append({'logical_path':logical,'physical_original_path':row['source_path'],
                    'CAS_path':str(cas_path(row)),'sha256':row['sha256'],'bytes':row['bytes']})
            if logical.startswith('history/'):
                history_paths.append({'logical_path':logical,'physical_original_path':row['source_path'],'sha256':row['sha256'],
                    'bytes':row['bytes'],'CAS_path':str(cas_path(row))})
            if len(parts)<2 or parts[0]!='episodes' or parts[1] not in episodes_by_id:continue
            eid=parts[1];archive_files+=1;file_counts[eid]+=1;file_bytes[eid]+=row['bytes'];original_paths.add(norm(row['source_path']))
            role='workspace_input' if '/workspace/inputs/' in logical else 'workspace_output' if '/workspace/outputs/' in logical else 'native_record_or_protocol'
            item={'episode_id':eid,'role':role,'logical_path':logical,'physical_original_path':row['source_path'],
                'physical_frozen_CAS_path':str(cas_path(row)),'source_sha256':row.get('source_sha256'),
                'stored_sha256':row['sha256'],'source_bytes':row.get('source_bytes'),'stored_bytes':row['bytes'],
                'credential_redacted_in_frozen_copy':row.get('credential_redacted')}
            file_out.write(js(item)+'\n')
            if '/workspace/outputs/' in logical:output_files[eid].append(item)
            if re.search(r'gold|golden|replay',logical,re.I):gold_files[eid].append(item)
            name=parts[-1];p=cas_path(row)
            if name in KEY_NAMES and '/workspace/' not in logical:
                key={**item,'original_exists_now':Path(row['source_path']).is_file(),'frozen_CAS_exists':p is not None}
                ep_meta[eid].append(key)
                if name in {'execution.json','dispatch.json','host_receipt.json','container_receipt.json','metadata.json','session-branch.json','usage.json','accounting.json','request.json'} and p:
                    value=read_json(p,{})
                    for reference in references(value):provider_refs.append({'episode_id':eid,'source_metadata_file':row['source_path'],**reference})
                    if name=='request.json' and isinstance(value,dict) and value.get('stage') and len(parts)==3:
                        request_interfaces[eid]={'episode_id':eid,'protocol':value.get('protocol'),'stage':value.get('stage'),
                            'task_id':value.get('task_id'),'source_file':row['source_path'],'source_sha256':row.get('source_sha256'),
                            'frozen_CAS_file':str(p),'frozen_sha256':row['sha256'],
                            'resources_count':len(value.get('resources',[])),'context_type':type(value.get('context')).__name__}
                    if name in {'usage.json','accounting.json'} and isinstance(value,dict):
                        usage=value.get('usage',value)
                        event=usage.get('event_file');start=usage.get('start_offset');end=usage.get('end_offset')
                        if event is not None:
                            key=(norm(event),start,end)
                            usage_slices.setdefault(key,{'event_file':event,'start_offset':start,'end_offset':end,
                                'episode_ids':set(),'declared_model_calls':usage.get('model_calls'),'declared_unknown_usage_calls':usage.get('unknown_usage_calls')})['episode_ids'].add(eid)
                        for req in usage.get('requests',[]) or []:
                            if not isinstance(req,dict):continue
                            rid=req.get('request_id');pid=req.get('pid')
                            if rid is None:api_without_ids.append({'episode_id':eid,'usage_metadata_file':row['source_path']});continue
                            key=(str(pid),str(rid));entry=api_requests.setdefault(key,{'pid':pid,'request_id':rid,
                                'model':req.get('model'),'complete_usage':req.get('complete'),'issues':req.get('issues'),
                                'episode_ids':set(),'meter_event_files':set(),'usage_metadata_paths':set()})
                            entry['episode_ids'].add(eid)
                            if event:entry['meter_event_files'].add(event)
                            entry['usage_metadata_paths'].add(row['source_path'])
                if name in {'native_events.jsonl','session_events.jsonl'} and p:
                    alias_event_hashes[row['sha256']].add(eid)
                    with p.open('r',encoding='utf-8-sig') as f:first=f.readline(1048576)
                    try:header=json.loads(first)
                    except ValueError:header={}
                    if eid not in frozen_native_events or header.get('type')=='session':
                        frozen_native_events[eid]={'event_file':row['source_path'],'CAS_path':str(p),'sha256':row['sha256'],
                            'first_record_type':header.get('type'),'native_session_id':header.get('id') if header.get('type')=='session' else None,
                            'header_timestamp':header.get('timestamp')}
    # Jobs can retain a reused meter slice while lacking their own episode.
    for j in jobs:
        usage=(j.get('result') or {}).get('usage') or {};event=usage.get('event_file')
        for req in usage.get('requests',[]) or []:
            if not isinstance(req,dict) or req.get('request_id') is None:continue
            key=(str(req.get('pid')),str(req['request_id']))
            entry=api_requests.setdefault(key,{'pid':req.get('pid'),'request_id':req['request_id'],'model':req.get('model'),
                'complete_usage':req.get('complete'),'issues':req.get('issues'),'episode_ids':set(),'meter_event_files':set(),'usage_metadata_paths':set()})
            entry['episode_ids'].update(ep_by_job.get(j['id'],set()))
            if event:entry['meter_event_files'].add(event)
    # Source-stage counts are a census, not training or correctness decisions.
    canonical_path=BUNDLE/'canonical/native_episodes.jsonl.gz';canon_counts={};native_tool_names=Counter()
    for r in rows(canonical_path):
        c=Counter(m.get('role','unknown') for m in r['messages']);actions=Counter();rfields=0
        for m in r['messages']:
            if m.get('role')!='assistant':continue
            content=m.get('content');rfields+=bool(m.get('reasoning_content'))
            if isinstance(content,list):
                for b in content:
                    if isinstance(b,dict) and b.get('type')=='toolCall':actions[str(b.get('name'))]+=1
                    elif isinstance(b,dict) and b.get('type') in {'thinking','reasoning'}:rfields+=1
        native_tool_names.update(actions);canon_counts[r['episode_id']]={'message_roles':dict(c),'tool_calls':sum(actions.values()),'tool_names':dict(actions),'explicit_reasoning_fields_or_blocks':rfields}
    # Exact output routes.json links are stronger than a shared source batch.
    screen_links=defaultdict(set);screen_evidence=[]
    artifact_path=ROOT/'output/20261025_wrd_fullchain_reaudit/controlled_master/resource_and_stage_artifact_texts.jsonl.gz'
    for a in rows(artifact_path):
        if a['kind']!='screen' or not a['logical_path'].endswith('/routes.json'):continue
        try:value=json.loads(a['content'])
        except ValueError:continue
        for card in value.get('routes',[]) if isinstance(value,dict) else []:
            if not isinstance(card,dict):continue
            for field in ('id','merge_into'):
                rid=card.get(field)
                if rid in retained:
                    screen_links[rid].add(a['episode_id']);screen_evidence.append({'skill_id':rid,'screen_episode_id':a['episode_id'],
                        'field':field,'artifact_logical_path':a['logical_path'],'artifact_sha256':a['stored_sha256']})
    # Skill trees are grouped by byte content; copied aliases are not new tasks.
    version_trees=[]
    for eid,items in output_files.items():
        skill_roots={v['logical_path'].rsplit('/',1)[0] for v in items if v['logical_path'].endswith('/SKILL.md')}
        for prefix in skill_roots:
            members=[v for v in items if v['logical_path'].startswith(prefix+'/')]
            manifest=[{'relative_path':v['logical_path'][len(prefix)+1:],'sha256':v['source_sha256'] or v['stored_sha256'],
                'physical_original_path':v['physical_original_path'],'physical_frozen_CAS_path':v['physical_frozen_CAS_path']} for v in members]
            fingerprint=bsha(js(sorted((v['relative_path'],v['sha256']) for v in manifest)).encode())
            version_trees.append({'episode_id':eid,'catalog_route_id':episodes_by_id[eid]['route_id'],
                'output_skill_root_logical_path':prefix,'output_skill_root_physical_path':str(Path(members[0]['physical_original_path']).parents[len(Path(members[0]['logical_path'][len(prefix)+1:]).parts)-1]),
                'file_count':len(manifest),'tree_content_sha256':fingerprint,'files':manifest,
                'is_execution_attempt_not_new_independent_enterprise_source':True})
    job_inventory=[]
    for j in jobs:
        usage=(j.get('result') or {}).get('usage') or {}
        job_inventory.append({'job_id':j['id'],'kind':j['kind'],'route_id':j['route_id'],'case_id':j.get('case_id'),
            'arm':j.get('arm'),'status':j['status'],'attempt_field':j['attempt'],'lane':j.get('lane'),
            'episode_ids':sorted(ep_by_job.get(j['id'],set())),'recorded_episode_path':j.get('episode'),
            'recorded_result_episode_path':(j.get('result') or {}).get('episode_dir'),
            'metadata_records_directory':str(PRODUCTION/'records'/j['id']),
            'reused_from_job':(j.get('result') or {}).get('reused_from_job'),
            'usage_event_file':usage.get('event_file'),'usage_start_offset':usage.get('start_offset'),
            'usage_end_offset':usage.get('end_offset'),'reported_model_calls_not_additive_if_reused':usage.get('model_calls'),
            'reported_unknown_usage_calls':usage.get('unknown_usage_calls'),'job_is_not_one_model_API_round':True})
    episode_inventory=[]
    for e in episodes:
        eid=e['episode_id'];provider=[r for r in provider_refs if r['episode_id']==eid]
        episode_inventory.append({'episode_id':eid,'job_id':e['job_id'],'job_refs':e['job_refs'],'kind':e['kind'],
            'role_hint_separate_from_raw_catalog_kind':raw_stage(e,request_interfaces.get(eid)),
            'role_hint_evidence':'exact_original_request_stage_and_task_id_plus_legacy_controller_contract' if e['cohort']=='imported_history' else 'original_catalog_job_dispatch',
            'original_request_interface':request_interfaces.get(eid),'route_id':e['route_id'],'status':e['status'],'attempt':e['attempt'],
            'cohort':e['cohort'],'source_path':e['source_path'],'source_directory_exists_now':Path(e['source_path']).is_dir(),
            'frozen_archive_prefix':e['archive_path'],'native_verified_metadata':e['native_verified'],
            'raw_native_session':frozen_native_events.get(eid),'key_recording_files':ep_meta[eid],
            'referenced_provider_runtime_files':provider,'frozen_file_count':file_counts[eid],'frozen_logical_bytes':file_bytes[eid],
            'canonical_message_inventory':canon_counts.get(eid),'gold_or_replay_named_files':gold_files[eid],
            'no_SFT_or_source_boundary_admission_filter_applied':True})
    api_rows=[]
    for key,row in sorted(api_requests.items()):
        api_rows.append({**row,'provider_request_identity':list(key),'episode_ids':sorted(row['episode_ids']),
            'meter_event_files':sorted(row['meter_event_files']),'usage_metadata_paths':sorted(row['usage_metadata_paths']),
            'body_presence_not_inferred_from_billing_reference':True})
    slice_rows=[{**v,'episode_ids':sorted(v['episode_ids'])} for v in usage_slices.values()]
    index_outputs={'jobs.all.jsonl.gz':job_inventory,'episodes.all.jsonl.gz':episode_inventory,
        'job_reference_edges.jsonl.gz':job_edges,'provider_runtime_path_references.jsonl.gz':provider_refs,
        'job_physical_path_references.jsonl.gz':job_path_refs,'original_request_interfaces.jsonl.gz':request_interfaces.values(),
        'model_api_requests.references.jsonl.gz':api_rows,'meter_event_slices.jsonl.gz':slice_rows,
        'skill_version_trees.all.jsonl.gz':version_trees,'screen_to_retained_route.links.jsonl.gz':screen_evidence,
        'historical_frozen_paths.all.jsonl.gz':history_paths}
    for name,values in index_outputs.items():dump(OUT/'indexes'/name,values)
    inventory_by_e={e['episode_id']:e for e in episode_inventory}
    api_by_e=defaultdict(set)
    for r in api_rows:
        for eid in r['episode_ids']:api_by_e[eid].add(tuple(r['provider_request_identity']))
    skill_maps=[]
    for rid,route in retained.items():
        direct_jobs={j['id'] for j in jobs if j['route_id']==rid}
        for _,key,v in walk(route):
            if isinstance(v,str) and v in jobs_by_id:direct_jobs.add(v)
        direct_eids={e['episode_id'] for e in episodes if e['route_id']==rid}|{eid for jid in direct_jobs for eid in ep_by_job.get(jid,set())}
        # Name aliases are disclosed as hints, never silently upgraded to a
        # proven parent task or substituted for exact artifact/job edges.
        hinted={e['episode_id'] for e in episodes if e['cohort']=='imported_history' and any(
            Path(e['source_path']).name.startswith(rid+suffix) for suffix in ('__','_c','_devprep'))}
        related=direct_eids|screen_links[rid]|hinted
        manifest_files=[]
        finalroot=BUNDLE/'skills/retained29'/rid
        for p in sorted(finalroot.rglob('*')):
            if p.is_file():manifest_files.append({'relative_path':p.relative_to(finalroot).as_posix(),
                'frozen_skill_file':str(p),'sha256':digest(p),'bytes':p.stat().st_size})
        versions=[v for v in version_trees if v['episode_id'] in direct_eids|hinted]
        unique_versions={v['tree_content_sha256'] for v in versions}
        final_tree_sha=bsha(js(sorted((v['relative_path'],v['sha256']) for v in manifest_files)).encode())
        late_versions=[]
        for version_root in (BUNDLE/'quarantine/late_skill_versions').glob('*/skills/'+rid):
            members=[{'relative_path':p.relative_to(version_root).as_posix(),'sha256':digest(p),'physical_path':str(p)}
                for p in sorted(version_root.rglob('*')) if p.is_file()]
            late_versions.append({'frozen_version_root':str(version_root),'file_count':len(members),
                'tree_content_sha256':bsha(js(sorted((v['relative_path'],v['sha256']) for v in members)).encode()),
                'files':members,'is_snapshot_not_new_model_execution':True})
        stage_counts=Counter(episodes_by_id[eid]['kind'] for eid in related)
        corrected_stages=Counter(inventory_by_e[eid]['role_hint_separate_from_raw_catalog_kind'] for eid in related)
        apis=set().union(*(api_by_e[eid] for eid in related)) if related else set()
        skillmap={'skill_id':rid,'name':route['name'],'library_status_in_frozen_catalog':'retained',
            'original_business_source_ids_in_route_record':route.get('source_ids',[]),
            'final_frozen_skill_root':str(finalroot),'production_skill_root':route.get('skill_root'),
            'final_delivery_skill_root':str(PRODUCTION/'selected_followup_20261024/final/skills'/rid),
            'final_files':manifest_files,'final_file_count':len(manifest_files),
            'final_tree_content_sha256':final_tree_sha,
            'native_output_versions_byte_exact_equal_final_tree':[v['episode_id'] for v in versions if v['tree_content_sha256']==final_tree_sha],
            'late_frozen_version_snapshots':late_versions,
            'direct_job_ids':sorted(direct_jobs),'direct_episode_ids':sorted(direct_eids),
            'screen_output_linked_episode_ids':sorted(screen_links[rid]),
            'legacy_name_hint_episode_ids':sorted(hinted-direct_eids),
            'all_related_episode_ids':sorted(related),'related_catalog_stage_counts':dict(stage_counts),
            'related_request_corrected_role_counts':dict(corrected_stages),
            'job_statuses':dict(Counter(jobs_by_id[j]['kind']+'/'+jobs_by_id[j]['status'] for j in direct_jobs)),
            'raw_episode_entries':[inventory_by_e[eid] for eid in sorted(related)],
            'observed_output_skill_tree_versions':versions,'unique_output_tree_content_versions':len(unique_versions),
            'output_tree_aliases_not_counted_as_new_version_tasks':len(versions)-len(unique_versions),
            'distinct_meter_request_ids_in_this_shared_lineage':len(apis),
            'gold_replay_files':[f for eid in sorted(related) for f in gold_files[eid]],
            'gold_named_artifact_is_not_proof_of_separate_gold_agent_or_success':True,
            'raw_census_only_no_training_admission_or_quality_rejection':True}
        path=OUT/'skills29'/(rid+'.json');save(path,skillmap)
        skill_maps.append({'skill_id':rid,'name':route['name'],'entrypoint':str(path),'final_file_count':len(manifest_files),
            'direct_jobs':len(direct_jobs),'direct_episodes':len(direct_eids),'screen_output_linked_episodes':len(screen_links[rid]),
            'legacy_hint_episodes':len(hinted-direct_eids),'all_related_episodes':len(related),'stage_counts':dict(stage_counts),
            'request_corrected_role_counts':dict(corrected_stages),
            'unique_output_tree_content_versions':len(unique_versions),'meter_request_ids_not_additive_across_skills':len(apis)})
    not_retained=[r for r in routes if r['id'] not in retained]
    not_retained_ids={r['id'] for r in not_retained}
    non_success={'routes':[{'id':r['id'],'name':r['name'],'library_status':r.get('library_status'),
        'skill_root':r.get('skill_root'),'job_ids':[j['id'] for j in jobs if j['route_id']==r['id']],
        'episode_ids':[e['episode_id'] for e in episodes if e['route_id']==r['id']]} for r in not_retained],
        'all_nonretained_route_job_ids':[j['id'] for j in jobs if j['route_id'] in not_retained_ids],
        'all_failed_held_superseded_job_ids':[j['id'] for j in jobs if j['status']!='done'],
        'all_failed_or_unknown_episode_ids':[e['episode_id'] for e in episodes if str(e['status']).lower() not in {'done','completed'}],
        'unassigned_screen_batch_job_ids':[j['id'] for j in jobs if j['kind']=='screen'],
        'no_failure_or_exploration_record_dropped_for_not_entering_29':True}
    save(OUT/'NON_RETAINED_AND_FAILED_PROCESS_INDEX.json',non_success)
    try:live=live_ro_comparison(jobs,routes)
    except (sqlite3.Error,OSError) as exc:live={'comparison_status':'READ_ONLY_COMPARISON_UNAVAILABLE','failure_type':type(exc).__name__,'frozen_catalog_remains_census_anchor':True}
    save(OUT/'PRODUCTION_READONLY_COMPARISON.json',live)
    original_count=len(read_json(PRODUCTION/'conversations.json',[]))
    summary={'schema_version':'wrd-v7-raw-skill29-lineage-address-census','generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':'UNFILTERED_RAW_ADDRESS_MAP_NOT_TRAINING_ADMISSION','retained_skills':len(retained),'retained_skill_files':sum(s['final_file_count'] for s in skill_maps),
        'skills':skill_maps,'unit_definitions':{'original_enterprise_conversations':'original source conversations, not Agent attempts',
            'logical_jobs':'outer pipeline jobs; aliases/reused jobs can reference the same execution',
            'catalog_episode_references':'recorded attempt directories; native session identity and copied event aliases are separate',
            'provider_request_ids':'deduplicated (pid,request_id) from original usage records; not one per job or tool call',
            'assistant_responses':'original native assistant message positions, may contain zero/multiple tool actions',
            'tool_calls':'actual native toolCall blocks; not source enterprise conversations or independent skills'},
        'original_enterprise_conversations':original_count,'frozen_source_table_rows':len(source_table),
        'logical_jobs':len(jobs),'jobs_by_stage':dict(Counter(j['kind'] for j in jobs)),
        'jobs_by_stage_status':dict(Counter(j['kind']+'/'+j['status'] for j in jobs)),
        'catalog_routes':len(routes),'routes_by_library_status':dict(Counter(r.get('library_status') for r in routes)),
        'catalog_episode_references':len(episodes),'episodes_by_stage':dict(Counter(e['kind'] for e in episodes)),
        'episodes_by_cohort':dict(Counter(e['cohort'] for e in episodes)),
        'episodes_by_request_corrected_role':dict(Counter(e['role_hint_separate_from_raw_catalog_kind'] for e in episode_inventory)),
        'legacy_role_controller_contracts':['research/archive/workflow_legacy_20261023/wrd_workflow_library_v2/library.py:156',
            'research/archive/workflow_legacy_20261023/wrd_workflow_library_v2/library.py:196'],
        'source_directory_refs_exist_now':sum(e['source_directory_exists_now'] for e in episode_inventory),
        'normalized_source_directory_paths':len(ep_by_path),
        'native_event_file_unique_content_hashes':len(alias_event_hashes),
        'native_event_identical_content_alias_groups':sum(len(v)>1 for v in alias_event_hashes.values()),
        'native_session_header_ids':len({v['native_session_id'] for v in frozen_native_events.values() if v['native_session_id']}),
        'canonical_recoverable_contexts':len(canon_counts),'catalog_refs_without_canonical_context':sorted(set(episodes_by_id)-set(canon_counts)),
        'canonical_assistant_response_positions':sum(r['message_roles'].get('assistant',0) for r in canon_counts.values()),
        'canonical_tool_call_blocks':sum(r['tool_calls'] for r in canon_counts.values()),'canonical_tool_names':dict(native_tool_names),
        'deduplicated_provider_request_id_references':len(api_rows),'meter_usage_slices':len(slice_rows),
        'provider_request_id_reference_scope':'current pipeline usage.requests; legacy accounting without IDs is separately preserved, not silently zero',
        'legacy_declared_model_calls_in_original_meta_not_added_without_identity_dedup':(meta.get('legacy_usage') or {}).get('model_calls'),
        'legacy_declared_unknown_calls_in_original_meta':(meta.get('legacy_usage') or {}).get('unknown_calls'),
        'requests_missing_identity_not_filled_with_zero':len(api_without_ids),
        'API_raw_body_presence_not_inferred_from_usage_references':True,
        'raw_recording_files_indexed':archive_files,'physical_original_file_paths_distinct':len(original_paths),
        'all_raw_29_related_stage_addresses_are_in_per_skill_entrypoints':True,
        'all_nonretained_or_failed_processes_retained_in_global_indexes':True,
        'final_delivery_source_indexes':source_index_paths,
        'production_readonly_comparison':str(OUT/'PRODUCTION_READONLY_COMPARISON.json'),
        'scope_not_based_on_v6_91_or_106':True,'no_training_or_source_boundary_filter_applied':True,
        'no_database_WAL_or_production_mutations':True,'new_model_or_agent_runs':0,'training_started':False,
        'physical_root_census_sibling_scope':'source_audit maps all physical original run roots; this file maps frozen lineage references',
        'source_sha256':{str(p):digest(p) for p in [catalogs/'routes.jsonl',catalogs/'jobs.jsonl',catalogs/'episodes.jsonl',
            catalogs/'state_meta.json',catalogs/'state_other_tables.json',catalogs/'retained_skills_verification.json',index_path,canonical_path,artifact_path]},
        'script_sha256':digest(Path(__file__))}
    save(OUT/'SKILL29_LINEAGE_MAP.json',summary)
    print(js({k:summary[k] for k in ['retained_skills','retained_skill_files','original_enterprise_conversations','logical_jobs','catalog_episode_references',
        'canonical_recoverable_contexts','canonical_assistant_response_positions','canonical_tool_call_blocks','deduplicated_provider_request_id_references']}),flush=True)

if __name__=='__main__':main()
