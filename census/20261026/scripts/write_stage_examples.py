"""Supplement the raw census with carrier roles, stage addresses and old R paths.

Reads raw indexes only; never selects SFT admission or runs historical agents.
"""
from collections import Counter,defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261026_wrd_raw_census_v7'
BASE=ROOT/'output/20261025_wrd_reasoning_recovery_v4'
FORMAL_ROOTS=[Path('E:/skillloop_runs/w16light_1024'),Path('E:/skillloop_runs/wrd6if_1024')]+[
    ROOT/'output'/name for name in ('20261024_eval33_two_arm','20261024_eval6_two_arm','20261024_modified20_as_ts',
    '20261024_wrd16_light_two_arm','20261024_wrd250_library_run','20261024_wrd6_interface_retry')]
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def save(p,r):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def dump(p,rs):
    with gzip.open(p,'wt',encoding='utf-8',newline='\n',compresslevel=3) as f:
        for r in rs:f.write(js(r)+'\n')
def norm(p):return str(p).replace('/','\\').rstrip('\\').lower()

def main():
    summary=json.loads((OUT/'SKILL29_LINEAGE_MAP.json').read_text(encoding='utf-8'))
    episodes={r['episode_id']:r for r in rows(OUT/'indexes/episodes.all.jsonl.gz')}
    retained={s['skill_id'] for s in summary['skills']};examples={};types=Counter();hashes=defaultdict(set);headers=set()
    for e in episodes.values():
        for f in e['key_recording_files']:
            if Path(f['physical_original_path']).name not in {'native_events.jsonl','session_events.jsonl'}:continue
            p=Path(f['physical_frozen_CAS_path'])
            if not p.is_file():continue
            with p.open(encoding='utf-8-sig') as h:line=h.readline(1048576)
            try:first=json.loads(line)
            except ValueError:first={}
            if first.get('type')=='session':role='OpenClaw_native_Agent_session_transcript';headers.add(first.get('id'))
            elif first.get('native_request_id') or first.get('schema') and first.get('event'):role='native_provider_meter_or_bridge_event_log'
            else:role='other_native_event_log'
            types[role]+=1;hashes[role].add(f['stored_sha256'])
    for kind in ('prepare','make','actor','review'):
        options=[e for e in episodes.values() if e['kind']==kind and e['cohort']=='current_pipeline'
                 and e['native_verified_metadata'] and e['source_directory_exists_now'] and e['route_id'] in retained]
        if options:examples[kind]={'episode_id':options[0]['episode_id'],'entry':options[0]}
    screen_ids=[]
    for s in summary['skills']:
        entry=json.loads(Path(s['entrypoint']).read_text(encoding='utf-8'));screen_ids.extend(entry['screen_output_linked_episode_ids'])
    screen=next((episodes[eid] for eid in screen_ids if eid in episodes and episodes[eid]['cohort']=='current_pipeline'
                 and episodes[eid]['native_verified_metadata'] and episodes[eid]['source_directory_exists_now']),None)
    if screen:examples['screen']={'episode_id':screen['episode_id'],'entry':screen}
    eids={v['episode_id'] for v in examples.values()};outputs=defaultdict(list)
    for row in rows(OUT/'indexes/episode_files.all.jsonl.gz'):
        if row['episode_id'] in eids and row['role']=='workspace_output':outputs[row['episode_id']].append(row)
    desired={'screen':'routes.json','prepare':'tasks.json','make':'SKILL.md','review':'review.json'}
    final={}
    for kind,value in examples.items():
        e=value['entry'];files=e['key_recording_files']
        pick=lambda suffix:next((f['physical_original_path'] for f in files if f['logical_path'].endswith(suffix)),None)
        produced=outputs[e['episode_id']]
        output=next((f['physical_original_path'] for f in produced if Path(f['physical_original_path']).name==desired.get(kind)),None)
        if output is None:
            output=next((f['physical_original_path'] for f in produced if Path(f['physical_original_path']).suffix.lower() in {'.docx','.pdf','.xlsx','.pptx','.html','.md','.json','.png'}),None)
        final[kind]={'episode_id':e['episode_id'],'route_id':e['route_id'],'original_episode_directory':e['source_path'],
            'original_Agent_session_events_file':(e.get('raw_native_session') or {}).get('event_file'),
            'OpenClaw_session_header_id':(e.get('raw_native_session') or {}).get('native_session_id'),
            'original_task_request_file':pick('/request.json'),'original_Agent_result_file':pick('/result.json'),
            'original_Agent_final_response_file':pick('/response.json'),'example_actual_generated_output_resource':output,
            'original_request_interface':e['original_request_interface'],
            'original_provider_meter_file':next((f['path'] for f in e['referenced_provider_runtime_files'] if f['json_pointer'].endswith('/event_file')),None),
            'provider_meter_references_are_not_claimed_raw_model_request_bodies':True,
            'all_other_original_files_are_in':'indexes/episode_files.all.jsonl.gz'}
    # Preserve every recovered original pair/carrier, including failures,
    # evaluation-related history and empty/incomplete R. This is an address map.
    historical=[];sse_count=0;raw_count=0;rchars=Counter();rresponses=Counter()
    for filename,kind in [('sse_reasoning_pairs.all.jsonl.gz','original_saved_SSE'),('raw_pairs.all.jsonl.gz','original_request_response_JSON')]:
        path=BASE/'controlled'/filename
        for r in rows(path):
            row={'pair_id':r['id'],'carrier_kind':kind,'episode_id':r.get('episode_id'),'parent_run_id':r.get('run_id'),
                'request_ordinal':r['request_ordinal'],'historical_condition':r.get('historical_condition'),'original_role_scope':r.get('role_scope'),
                'original_reasoning_characters':r['original_reasoning_characters'],
                'original_response_finish_reason':r.get('original_response_finish_reason'),
                'stream_reconstruction_state':r.get('stream_reconstruction_state'),
                'source_request':r.get('source_request'),'source_response':r.get('source_response'),
                'source_SSE':r.get('source_sse'),'source_stored_response_JSON':r.get('source_stored_response'),
                'source_parsed_output':r.get('source_parsed'),'source_execution_receipt':r.get('source_receipt'),
                'no_training_or_protected_source_filter_applied':True,'old_protocol_not_current_native_Agent_equivalence':True}
            historical.append(row);rchars[kind]+=r['original_reasoning_characters'];rresponses[kind]+=bool(r['original_reasoning_characters'])
            if kind=='original_saved_SSE':sse_count+=1
            else:raw_count+=1
    dump(OUT/'indexes/historical_model_pair_carriers.all.jsonl.gz',historical)
    r_example=next(r for r in historical if r['carrier_kind']=='original_saved_SSE' and r['original_reasoning_characters']>0)
    save(OUT/'STAGE_ADDRESS_EXAMPLES.json',{'scope':'original paths only, not body or SFT admission',
        'production_stage_examples':final,'other_historical_recorded_thinking_example':r_example,
        'all_historical_pairs':len(historical),'saved_SSE_carriers':sse_count,'raw_request_response_pairs':raw_count,
        'original_R_nonempty_responses_by_carrier':dict(rresponses),'original_R_characters_by_carrier':dict(rchars),
        'historical_source_index':'indexes/historical_model_pair_carriers.all.jsonl.gz',
        'not_added_as_new_enterprise_sources_or_new_29_skills':True})
    save(OUT/'NATIVE_EVENT_CARRIER_ROLES.json',{'scope':'all frozen episode recording files named native_events.jsonl or session_events.jsonl',
        'carrier_file_reference_counts_by_role':dict(types),'unique_carrier_content_hashes_by_role':{k:len(v) for k,v in hashes.items()},
        'all_roles_unique_carrier_content_hashes':len(set().union(*hashes.values())),
        'OpenClaw_Agent_session_header_ids':len(headers),
        '3341_unique_carrier_hashes_are_not_3341_Agent_sessions':True,
        'unit_explanation':'Provider meter/bridge JSONL and original OpenClaw session transcript JSONL are different carriers; one Agent session contains many model API rounds/tool actions.'})
    formal_refs=[]
    for name in ('provider_runtime_path_references.jsonl.gz','job_physical_path_references.jsonl.gz'):
        for row in rows(OUT/'indexes'/name):
            path=norm(row['path'])
            matches=[str(p) for p in FORMAL_ROOTS if path==norm(p) or path.startswith(norm(p)+'\\')]
            if matches:formal_refs.append({'source_index':name,'matching_formal_or_later_branch_roots':matches,**row})
    save(OUT/'FORMAL_ROOT_REFERENCE_CHECK.json',{'roots':[str(p) for p in FORMAL_ROOTS],
        'all_recorded_metadata_reference_matches':formal_refs,'match_count':len(formal_refs),
        'scanned_indexes':['indexes/provider_runtime_path_references.jsonl.gz','indexes/job_physical_path_references.jsonl.gz'],
        'not_deleted_or_unscanned_because_of_training_exclusion':True,
        'root_filesystem_stat_is_handled_by_sibling_physical_census':True,
        'lack_of_exact_path_reference_is_not_proof_of_no_historical_influence':True})
    print(js({'roles':{k:len(v) for k,v in hashes.items()},'session_ids':len(headers),'examples':len(final),
        'historical_pairs':len(historical),'SSE':sse_count,'raw':raw_count,'Rcounts':dict(rresponses),'Rchars':dict(rchars),
        'formal_or_later_branch_exact_path_references':len(formal_refs)}),flush=True)

if __name__=='__main__':main()
