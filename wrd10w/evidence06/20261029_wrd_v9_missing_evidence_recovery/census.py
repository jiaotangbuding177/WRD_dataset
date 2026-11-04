"""Metadata-only final-v9 missing-evidence census. No native/model execution.

Frozen metadata and actual carriers are read only for identities/size/SHA. No
protected task/conversation or program body is printed, interpreted or admitted.
"""
from pathlib import Path,PurePosixPath
from collections import Counter,defaultdict
import gzip,hashlib,json,sys
ROOT=Path('D:/skillloop');BASE=ROOT/'output';V9=BASE/'20261026_wrd_dataset_v9'
META=V9/'outcomes/recomputed_scope_overlay';OUT=Path(__file__).parent
CAS=BASE/'20261025_wrd_training_dataset/bundle/archive'
def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def pin(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':digest(p)}
def rows(p):return [json.loads(x) for x in gzip.open(p,'rt',encoding='utf-8')]
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_rows(n,rs):
    with (OUT/n).open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
            for d in rs:gz.write((json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n').encode())
def counts(xs):return dict(sorted(Counter(xs).items()))
CACHE={}
def check(path,expected):
    p=Path(path);key=(str(p),expected)
    if key not in CACHE:
        is_file=p.is_file();d={'path':str(p),'exists_regular_file':is_file,'expected_sha256':expected}
        if is_file:d.update(bytes=p.stat().st_size,actual_sha256=digest(p));d['matches_expected_sha256']=d['actual_sha256']==expected
        else:d['matches_expected_sha256']=None
        CACHE[key]=d
    return CACHE[key]
def main():
    assert not(OUT/'CENSUS.json').exists()
    sourcepath=BASE/'20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz'
    scope={x['source_id']:x for x in rows(sourcepath)}
    alltargets=rows(META/'target_outcome_labels.jsonl.gz');held=[x for x in alltargets if x['source_admission']=='HOLD_MISSING_EVIDENCE']
    assert len(held)==9096 and all(x['scope_status']=='HOLD_UNKNOWN' and not x['training_admitted'] for x in held)
    eps={x['episode_id']:x for x in rows(V9/'recovery/episodes.metadata.jsonl.gz')}
    resources=rows(META/'resource_scope.jsonl.gz');byep=defaultdict(list)
    for r in resources:byep[r['episode_id']].append(r)
    versions=rows(META/'produced_versions.jsonl.gz');vep=defaultdict(list)
    for v in versions:vep[v['episode_id']].append(v)
    def known_status(x):
        ids=x.get('source_ids',[])
        return 'EMPTY' if not ids else '|'.join(sorted({scope.get(s,{}).get('status','MISSING_CURRENT_SOURCE_SCOPE') for s in ids}))
    def current_sources(ids):return [{'source_id':s,'current_status':scope.get(s,{}).get('status','MISSING_CURRENT_SOURCE_SCOPE'),'component_id':scope.get(s,{}).get('component_id')} for s in sorted(set(ids))]
    makers=[x for x in held if x['stage'] in ['make','legacy_skill_make']]
    trainmakers=[x for x in makers if known_status(x)=='TRAIN'];epids={x['episode_id'] for x in trainmakers}
    assert len(makers)==1434 and len(trainmakers)==1050 and len(epids)==100
    annotated=[]
    for x in held:
        prior=[r for r in byep[x['episode_id']] if r['observed_after_assistant_message_index']<x['source_message_index']]
        unknown=[r for r in prior if r['unknown_reasons']]
        annotated.append({'id':x['id'],'episode_id':x['episode_id'],'stage':x['stage'],'route_id':x['route_id'],'source_message_index':x['source_message_index'],
            'source_event_line':x['source_event_line'],'source_message_sha256':x['source_message_sha256'],'source_ids':x['source_ids'],'known_source_status_combination':known_status(x),
            'current_sources':current_sources(x['source_ids']),'unknown_reasons':x['unknown_reasons'],'scope_proof_id':x['scope_proof_id'],'native_prefix_end_exclusive':x['native_prefix_end_exclusive'],
            'original226':x['original226'],'holdout12':x['holdout12'],'protected_source_ids':x['protected_source_ids'],
            'observed_prior_direct_resource_node_ids':[r['node_id'] for r in prior],
            'observed_prior_unresolved_direct_resource_nodes':[{'node_id':r['node_id'],'native_path':r['native_path'],'original_terminal':r['original_terminal'],'unknown_reasons':r['unknown_reasons']} for r in unknown],
            'scope_only_is_not_quality_admission':True,'original_HOLD_unchanged':True,'positive_loss':0})
    write_rows('HOLD_TARGETS_9096.metadata.jsonl.gz',annotated)
    makerby=defaultdict(list)
    for x in trainmakers:makerby[x['episode_id']].append(x)
    clusters=[];resource_rows=[];programs=[]
    for eid,targets in sorted(makerby.items()):
        ep=eps[eid];maxi=max(x['source_message_index'] for x in targets)
        prior=[r for r in byep[eid] if r['observed_after_assistant_message_index']<maxi]
        bad=[r for r in prior if r['unknown_reasons']]
        unique={r['node_id']:r for r in prior}
        native=ep['source_native'];checks=[check(native['path'],native['sha256']),check(ep['source_original_path'],native['sha256'])]
        vfiles=[]
        for v in vep[eid]:
            for f in v['files']:
                q={'episode_id':eid,'route_id':ep['route_id'],'tree_content_sha256':v['tree_content_sha256'],'relative_path':f['relative_path'],'sha256':f['sha256'],
                    'is_program_by_extension':PurePosixPath(f['relative_path']).suffix.lower() in ['.py','.js','.ts','.tsx','.jsx','.html','.sh'],
                    'carriers':[check(f['physical_frozen_CAS_path'],f['sha256']),check(f['physical_original_path'],f['sha256'])],
                    'final_snapshot_only_not_same_version_at_target_or_correctness':True,'positive_loss':0}
                vfiles.append(q)
                if q['is_program_by_extension']:programs.append(q)
        for r in unique.values():
            identity=r['file_identity'];carriers=[]
            if identity:
                if identity.get('object'):carriers.append(check(CAS/identity['object'],identity['sha256']))
                if identity.get('source_path'):carriers.append(check(identity['source_path'],identity['sha256']))
            path=r['native_path']
            bucket='FROZEN_IDENTITY_AND_CARRIER_METADATA' if identity else 'NO_EXACT_READ_IDENTITY_IN_OLD_GRAPH'
            if not identity and ('$' in path or '<dynamic' in path or '\ufffd' in path):bucket='DYNAMIC_OR_VARIABLE_OR_MALFORMED_READ_PATH_NEEDS_ACTUAL_COMMAND_RESOLUTION'
            resource_rows.append({'episode_id':eid,'route_id':ep['route_id'],'node_id':r['node_id'],'native_path':path,'observed_after_assistant_message_index':r['observed_after_assistant_message_index'],
                'original_terminal':r['original_terminal'],'unknown_reasons':r['unknown_reasons'],'source_ids':r['source_ids'],'current_sources':current_sources(r['source_ids']),
                'protected_source_ids':r['protected_source_ids'],'original_proven_producer_prefixes':r['original_proven_producer_prefixes'],'file_identity':identity,
                'identity_bucket':bucket,'carriers':carriers,'byte_carrier_is_not_source_or_runtime_ancestry_proof':True,'positive_loss':0})
        clusters.append({'episode_id':eid,'route_id':ep['route_id'],'stage':ep['stage'],'held_target_count':len(targets),'held_target_ids':[x['id'] for x in targets],
            'target_message_indices':[x['source_message_index'] for x in targets],'current_known_target_sources':current_sources(s for x in targets for s in x['source_ids']),
            'known_source_train_only_but_unknown_resource_ancestry_not_resolved':True,'source_native':native,'source_original_path':ep['source_original_path'],'native_carrier_checks':checks,
            'called_tool_names_episode_metadata_only':ep['called_tool_names'],'unknown_reason_counts':counts(r for x in targets for r in x['unknown_reasons']),
            'direct_resource_observations_in_max_held_prefix':len(prior),'unique_direct_resource_nodes':len(unique),'unresolved_direct_resource_observations':len(bad),
            'old_episode_metadata_source_status_counts':counts(scope.get(s,{}).get('status','MISSING_CURRENT_SOURCE_SCOPE') for s in ep['old_episode_source_ids_metadata']),
            'final_tree_snapshots':len(vep[eid]),'final_tree_file_count':len(vfiles),'final_program_count_by_extension':sum(f['is_program_by_extension'] for f in vfiles),
            'final_snapshot_files':vfiles,'exact_original_tool_arguments_and_version_timeline_not_yet_semantically_reviewed':True,'positive_loss':0})
    write_rows('MAKE_100_EPISODE_CLUSTERS.metadata.jsonl.gz',clusters)
    write_rows('MAKE_PRIOR_RESOURCES.metadata.jsonl.gz',resource_rows)
    write_rows('FINAL_PROGRAM_SNAPSHOT_CARRIERS.metadata.jsonl.gz',programs)
    save('CARRIER_CHECKS.json',{'checks':list(CACHE.values()),'summary':{'distinct_path_expected_sha_checks':len(CACHE),'regular_files':sum(x['exists_regular_file'] for x in CACHE.values()),'matching':sum(x['matches_expected_sha256'] is True for x in CACHE.values()),'missing_paths':sum(not x['exists_regular_file'] for x in CACHE.values())},'missing_path_does_not_mean_missing_record_or_missing_bytes':True,'content_body_not_exposed_or_semantically_reviewed':True})
    report={'schema':'wrd-v9-final-missing-evidence-recovery-metadata-v1','final_target_base':pin(META/'target_outcome_labels.jsonl.gz'),'current_scope':pin(sourcepath),'final_HOLD_missing':len(held),
        'stages':counts(x['stage'] for x in held),'reason_occurrences_not_mutually_exclusive':counts(r for x in held for r in x['unknown_reasons']),
        'reason_combinations':counts('|'.join(sorted(x['unknown_reasons'])) for x in held),'current_known_source_status':counts(known_status(x) for x in held),
        'make_plus_legacy_skill_make':len(makers),'maker_current_known_source_status':counts(known_status(x) for x in makers),'known_source_train_only_make_targets':len(trainmakers),'known_source_train_only_make_episodes':len(epids),
        'make_reason_occurrences':counts(r for x in makers for r in x['unknown_reasons']),'100_episode_final_snapshots':sum(c['final_tree_snapshots'] for c in clusters),
        '100_episode_with_final_snapshot':sum(c['final_tree_snapshots']>0 for c in clusters),'100_episode_with_program_final_snapshot':sum(c['final_program_count_by_extension']>0 for c in clusters),
        'final_program_snapshot_references':len(programs),'distinct_final_program_SHA':len({x['sha256'] for x in programs}),
        'max_held_prefix_direct_resource_unique_ep_node_pairs':len(resource_rows),'resource_identity_buckets':counts(x['identity_bucket'] for x in resource_rows),
        'largest_maker_clusters':[{'episode_id':x['episode_id'],'route_id':x['route_id'],'held_target_count':x['held_target_count'],'final_program_count_by_extension':x['final_program_count_by_extension'],'unknown_reason_counts':x['unknown_reason_counts']} for x in sorted(clusters,key=lambda x:-x['held_target_count'])[:20]],
        'not_proof_of_trainable1050':'Known source IDs TRAIN alone do not close unknown route producers, dynamic runtime inputs, reusable resource inputs or feedback ancestors. No source scope changed and no positive loss added.',
        'no_protected_body_read_or_printed':True,'no_native_Agent_model_training_or_business_run':True,'curation_cost':'UNKNOWN_NOT_ZERO'}
    save('CENSUS.json',report)
    save('MANIFEST.json',{'files':[pin(OUT/n) for n in ['census.py','CENSUS.json','CARRIER_CHECKS.json','HOLD_TARGETS_9096.metadata.jsonl.gz','MAKE_100_EPISODE_CLUSTERS.metadata.jsonl.gz','MAKE_PRIOR_RESOURCES.metadata.jsonl.gz','FINAL_PROGRAM_SNAPSHOT_CARRIERS.metadata.jsonl.gz']],
        'source_pins':[pin(p) for p in [sourcepath,META/'target_outcome_labels.jsonl.gz',META/'resource_scope.jsonl.gz',META/'produced_versions.jsonl.gz',V9/'recovery/episodes.metadata.jsonl.gz']],
        'scope':'Metadata and actual carrier size/SHA only; not semantic or positive admission.','frozen05_modified':False,'positive_loss':0})
    print(json.dumps({k:report[k] for k in ['final_HOLD_missing','stages','make_plus_legacy_skill_make','known_source_train_only_make_targets','known_source_train_only_make_episodes','100_episode_with_final_snapshot','100_episode_with_program_final_snapshot','final_program_snapshot_references','distinct_final_program_SHA','resource_identity_buckets']}))

if __name__=='__main__':main()
