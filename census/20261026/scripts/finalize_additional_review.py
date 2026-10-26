"""Freeze a finite reconciliation of independent memory discovery against 169.

No new recursive scan, provider call or training selection. All discovered
addresses stay queryable even when outside the retained29-production scope.
"""
from collections import Counter
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/20261026_wrd_raw_census_v7'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def norm(p):return re.sub('/+','/',str(p).replace('\\','/')).rstrip('/').lower()
def save(p,r):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    first_path=OUT/'ADDITIONAL_DISCOVERY_REVIEW.json';first=json.loads(first_path.read_text(encoding='utf-8'))
    if first.get('schema_version')=='wrd-v7-independent-additional-root-discovery-final':
        print('already_final_no_changes');return
    history=OUT/'history/ADDITIONAL_DISCOVERY_REVIEW.initial_broad_registry.json';history.parent.mkdir(parents=True,exist_ok=True)
    if not history.exists():history.write_bytes(first_path.read_bytes())
    base_path=OUT/'PHYSICAL_ROOTS.json';additional_path=OUT/'ADDITIONAL_ORIGINAL_ROOTS.json'
    base=json.loads(base_path.read_text(encoding='utf-8'));additional=json.loads(additional_path.read_text(encoding='utf-8'))
    known=base['roots']+additional['roots'];assert len({norm(r['path']) for r in known})==169
    with gzip.open(OUT/'indexes/additional_shallow_root_coverage_matrix.jsonl.gz','rt',encoding='utf-8') as f:entries=[json.loads(x) for x in f]
    special=[ROOT/'output/20261024_concurrency9',ROOT/'output/20261021_pipeline_infra_audit',
        ROOT/'output/20261021_pipeline_infra_repair_v3',Path('E:/skillloop_runs/20261021_pipeline_infra_audit'),
        Path('E:/skillloop_runs/20261021_pipeline_infra_repair_v3')]
    assisted=ROOT/'output/20261023_codex_assisted_resource_repair'
    special_set={norm(p) for p in special+[assisted]};registry=[];unmatched=[]
    for entry in entries:
        path=entry['path'];rn=norm(path)
        witnesses=[r for r in known if rn==norm(r['path']) or rn.startswith(norm(r['path'])+'/')]
        if rn in special_set:status='FINITE_ORIGINAL29_RELATED_SUPPLEMENT_TRANSFERRED_FOR_METADATA_STAT'
        elif witnesses:status='ADDRESS_COVERED_BY_169_WITH_ORIGINAL_SCAN_SCOPE_RETAINED'
        elif 'ablation' in rn:status='ABLATED_BRANCH_OUTSIDE_THIS_ORIGINAL29_DISCOVERY_NOT_OPENED'
        elif any(t in Path(path).name.lower() for t in ('eval','two_arm','modified','adopt','experiment_results')):
            status='LATER_OR_INDEPENDENT_EVALUATION_REFERENCE_NOT_PROVEN_ORIGINAL29_PRODUCER'
        elif Path(path).name.startswith(('20261023_','20261024_')):
            status='STATUS_PREPARATION_OR_RESOURCE_METADATA_REFERENCE_PRODUCER_RELATION_UNCONFIRMED'
        else:status='OTHER_REFERENCE_OR_EARLIER_HISTORY_OUTSIDE_BOUNDED_ORIGINAL29_RECONCILIATION'
        value={**entry,'final_registry_status':status,
            '169_coverage_witnesses':[{'path':r['path'],'scan_status':r.get('scan_status'),
                'recursive_scan':r.get('recursive_scan'),'role':r.get('role')} for r in witnesses],
            'status_is_not_training_rejection_or_claim_of_no_value':True}
        registry.append(value)
        if not witnesses:unmatched.append({'path':path,'status':status,'reference_count':entry['memory_original_reference_count']})
    final_index=OUT/'indexes/additional_discovery.final_queryable_registry.jsonl.gz'
    with gzip.open(final_index,'wt',encoding='utf-8',newline='\n',compresslevel=3) as f:
        for row in registry:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    provenance_path=assisted/'assistance_provenance.json';provenance=json.loads(provenance_path.read_text(encoding='utf-8'))
    exact=Path(provenance['source_transcript_path'])
    supplements=[{'path':str(p),'exists':p.is_dir(),
        'purpose':'original_channel_profile_and_before_jobs_snapshot; 154 references all point to channel8/native_profile.json, not 154 Agent sessions' if 'concurrency9' in str(p) else
            'original_skill_library_infrastructure_audit_or_isolated_repair; includes original replay/audit evidence and zero-model controls, not automatically new paid Agent work',
        'source_evidence':'research/memory/2026-10-24_concurrency9.md' if 'concurrency9' in str(p) else 'research/memory/2026-10-21_pipeline_infrastructure_audit.md',
        'metadata_stat_owner':'source_audit','new_agent_or_model_call_count_not_inferred_from_address':True} for p in special]
    supplements.append({'path':str(assisted),'exists':assisted.is_dir(),
        'purpose':'Codex-authored legal-document-drafting candidate repair, failed/nonretained branch; not mislabeled original GLM production',
        'source_evidence':[str(assisted/'README.md'),str(provenance_path)],'metadata_stat_owner':'source_audit',
        'new_agent_or_model_call_count_not_inferred_from_address':True})
    exact_file={'path':str(exact),'exists':exact.is_file(),'bytes':exact.stat().st_size if exact.is_file() else None,
        'provenance_file':str(provenance_path),'provenance_file_sha256':digest(provenance_path),
        'purpose':'exact original authored-conversation reference for the assisted candidate repair',
        'content_not_read_or_exported_by_this_review':True,'entire_C_drive_or_sessions_directory_not_scanned':True}
    final={'schema_version':'wrd-v7-independent-additional-root-discovery-final','finished_at_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'finite original29 full-pipeline address discovery from 10/20-10/24 memory plus original history/resources/dispatch references',
        'memory_files_reviewed':first['memory_files_reviewed'],'shallow_D_output_E_run_roots_reviewed':len(entries),
        'baseline_known_root_addresses':169,'baseline_PHYSICAL_ROOTS_sha256':digest(base_path),
        'baseline_ADDITIONAL_ORIGINAL_ROOTS_sha256':digest(additional_path),
        'finite_additional_related_root_addresses':len(supplements),'supplement_roots':supplements,
        'finite_registry_scope_root_addresses_after_supplement':175,
        'one_additional_exact_authored_conversation_file_not_counted_as_another_root':exact_file,
        'no_new_recursive_stat_or_byte_totals_claimed_by_this_review':True,
        'all_discovered_addresses_queryable_registry':str(final_index),'registry_sha256':digest(final_index),
        'registry_status_counts':dict(Counter(r['final_registry_status'] for r in registry)),
        'all_addresses_not_covered_by_169_remain_queryable':unmatched,
        'covered_actual_production_references_in_other_unscanned_parent_roots':[
            {'parent_root':str(ROOT/'output/20261024_evidence_inputs_closeout'),'actual_referenced_child':'original_request_restore','already_in_169':True},
            {'parent_root':str(ROOT/'output/20261024_speed_audit'),'actual_referenced_children':'7 rule_decisions directories','already_in_169':True}],
        'concurrency9_reference_precision':{'references':154,'distinct_actual_referenced_paths':1,
            'path':str(ROOT/'output/20261024_concurrency9/channel8/native_profile.json'),
            'not_new_154_sessions':True,'actual_run_roots_remain_in_existing_E_ledger':True},
        'D_v11_v35_and_E_v11_v34_all_now_in_169':True,
        'scope_limit':'Other status notes, independent/later evaluations and earlier related teacher branches remain in the registry; no claim that they are valueless or unsuitable for training, and no endless expansion of this retained29-production census.',
        'original_frozen_29_graph_modified':False,'original_global_indexes_modified':False,
        'training_source_admission_or_91_106_filter_used':False,'training_started':False,'new_business_or_model_calls':0,
        'active_ablation_tree_not_opened_or_scanned':str(ROOT/'output/20261026_ablation_v2'),
        'initial_broad_discovery_report_preserved':str(history),'initial_broad_discovery_report_sha256':digest(history),
        'initial_method_memory_sources':first['memory_sources'],'creating_controller_prefix_evidence':first['dynamic_root_prefix_controller_evidence'],
        'finalizer_script_sha256':digest(Path(__file__))}
    save(first_path,final);save(OUT/'FINAL_REGISTRY_RECONCILIATION.json',final)
    print(json.dumps({'report':str(first_path),'sha256':digest(first_path),'baseline':169,'bounded_extra_roots':6,'exact_extra_files':1,
        'queryable_registry_roots':len(registry)}),flush=True)

if __name__=='__main__':main()
