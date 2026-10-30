"""Read-only metadata/set recount; writes only the new readiness review directory."""
import collections
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path('D:/skillloop')
OUT = ROOT / 'output/20261031_wrd_readiness_plan/reviews'
CORPUS = ROOT / 'output/20261030_wrd_gap08/corpus'
LINEAGE = ROOT / 'output/20261030_wrd_gap08/lineage'
MAIN = ROOT / 'output/20261027_wrd_main_v10'


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8-sig') as handle:
        return [json.loads(line) for line in handle]


def pin(path):
    body = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)).replace('\\', '/'),
            'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


def describe(owner_ids):
    selected = [by_owner[x] for x in sorted(owner_ids)]
    return {'owners': len(selected),
            'episodes': len({r['episode_id'] for r in selected}),
            'source_ids': sorted({s for r in selected for s in r['source_ids']}),
            'route_counts': dict(collections.Counter(r['route_id'] for r in selected)),
            'role_counts': dict(collections.Counter(r['historical_role'] for r in selected)),
            'owner_ids': sorted(owner_ids)}


owner_path = CORPUS / 'CORPUS_OWNER_COVERAGE.native.jsonl.gz'
write_path = CORPUS / 'RECOVERABLE_COMPLETE_NATIVE_WRITES.with_code.jsonl.gz'
overlay_path = CORPUS / 'NATIVE73_STATIC_SCOPE_OVERLAY02.jsonl.gz'
receipt_path = CORPUS / 'SEMANTIC_AND_COMPILER_RECEIPTS.original.jsonl.gz'
alias_path = CORPUS / 'CURRENT552_VIEW_COMPONENT_COVERAGE.jsonl.gz'
target_path = LINEAGE / 'TARGET_EVIDENCE_AND_DECISIONS_196.jsonl.gz'
edge_path = LINEAGE / 'ROUTE_PRODUCER_TO_ACTUAL_RECEIPT.jsonl.gz'
manifest_path = MAIN / 'TRAINING_MANIFEST.json'
bank_path = ROOT / 'output/20261030_wrd_gap08/process_bank03/candidate17.jsonl.gz'
held_path = ROOT / 'output/20261030_wrd_gap08/process_bank03/HELD_ORIGINAL_BAD_WRITER.json'
registry_path = OUT / 'source_registry_current569.json'
owners = rows(owner_path)
by_owner = {r['canonical_owner_id']: r for r in owners}
assert len(owners) == len(by_owner) == 34616
writes = rows(write_path)
write_by_owner = {r['canonical_owner_id']: r for r in writes}
assert len(writes) == len(write_by_owner) == 653
overlay = rows(overlay_path)
overlay_by_owner = {r['canonical_owner_id']: r for r in overlay}
assert len(overlay) == len(overlay_by_owner) == 73
targets = rows(target_path)
edges = rows(edge_path)
manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
bank = rows(bank_path)
held = json.loads(held_path.read_text(encoding='utf-8-sig'))
registry = json.loads(registry_path.read_text(encoding='utf-8-sig'))
base_count = collections.Counter(r['current_disposition'] for r in owners)
source_count = collections.Counter(r['source_disposition'] for r in owners)
effective_count = collections.Counter(overlay_by_owner.get(r['canonical_owner_id'], r)['current_disposition'] for r in owners)
cross = collections.defaultdict(collections.Counter)
for row in owners:
    cross[row['current_disposition']]['nonempty_source_ids' if row['source_ids'] else 'empty_source_ids'] += 1

business = {r['canonical_owner_id'] for r in owners if r['source_disposition'] == 'SCOPE_CLOSED_SEMANTIC_PENDING'}
assert len(business) == 1363 and all(by_owner[x]['source_ids'] for x in business)
pending = {x for x in business if by_owner[x]['current_disposition'] == 'SOURCE_CLOSED_SEMANTIC_PENDING'}
auxiliary = {x for x in business if by_owner[x]['current_disposition'] == 'PROTOCOL_AUXILIARY_REVIEW_ONLY_COMPLEX_SEMANTICS_PENDING'}
readonly = {x for x in business if by_owner[x]['current_disposition'] == 'LOCAL_READONLY_BYTE_REVIEW_NO_COMPLEX_PROGRAM_IN_TARGET'}
assert (len(pending), len(auxiliary), len(readonly)) == (746, 615, 2)
assert pending | auxiliary | readonly == business
complete = {r['canonical_owner_id'] for r in writes if r['source_disposition'] == 'SCOPE_CLOSED_SEMANTIC_PENDING'}
assert len(complete) == 40 and complete <= pending
admitted = {r['original_recorded_action_owner'] for r in bank if r['stage'] == 'B_resource_implementation_from_execution_auxiliary'}
known_bad = {r['owner'] for r in held}
assert len(admitted) == 8 and len(known_bad) == 1 and admitted | known_bad <= complete
remaining_complete = complete - admitted - known_bad
assert len(remaining_complete) == 31
other_pending = pending - complete
assert len(other_pending) == 706
for x in complete:
    r = write_by_owner[x]
    assert r['whole_tool_write_content_recovered']
    assert hashlib.sha256(r['full_code'].encode()).hexdigest() == r['original_content_utf8_SHA256']

baseline_alias = rows(alias_path)
baseline_native_links = {x for r in baseline_alias for x in r['native_owner_links']}
assert len(baseline_alias) == 552 and len(baseline_native_links) == 58
assert not (baseline_native_links & business)
baseline_receipts = rows(receipt_path)
receipt_matches = {}
for r in baseline_receipts:
    text = json.dumps(r['original_receipt'], ensure_ascii=False)
    matches = sorted(x for x in complete if x in text)
    if matches:
        receipt_matches[r['source']['path']] = matches
assert not receipt_matches

decision_sets = collections.defaultdict(set)
for r in targets:
    decision_sets[r['current_decision']].add(r['id'])
protected196 = decision_sets['HOLD_PROTECTED_EXACT_ROUTE_ANCESTOR_AND_ACTUAL_CONTENT_RECEIPT']
method63 = decision_sets['HOLD_EXACT_METHOD_ANCESTOR_NEEDS_FROZEN_MERGE_OR_IDENTITY_CLOSURE']
missing8 = decision_sets['HOLD_SPECIFIC_MISSING_ANCESTRY_OR_CAPTURE']
assert (len(protected196), len(method63), len(missing8)) == (125, 63, 8)
all196 = protected196 | method63 | missing8
assert len(all196) == 196 and not (all196 & business)
assert not (all196 & set(overlay_by_owner))
assert all(by_owner[x]['current_disposition'] == 'HOLD_ANCESTRY_UNRESOLVED' for x in all196)
lineage_links = sorted({i for r in targets if r['id'] in method63 for i in r['route_evidence_links']})
edge_summaries = []
for i in lineage_links:
    r = edges[i]
    scope = r['producer_effective_scope']
    producer = r['producer']
    actual = producer.get('actual_write_scope', {})
    edge_summaries.append({'index': i, 'route_id': r['route_id'], 'relation': r['relation'],
        'producer_episode': producer.get('episode_id'),
        'proven_protected': scope.get('proven_protected'), 'proven_clean': scope.get('proven_clean'),
        'producer_scope': actual.get('scope_status'),
        'actual_producer_prefix_original226_count': len(actual.get('original226', [])),
        'actual_producer_prefix_H12_count': len(actual.get('holdout12', [])),
        'producer_source_status_counts': dict(collections.Counter(scope.get('source_statuses', {}).values())),
        'strict_origin_protection_equivalence': r['strict_protected_producer_and_receipt'],
        'candidate_not_final_origin_equivalence': r['method_dependency_candidate_not_final_origin_equivalence']})
assert len(edge_summaries) == 9 and all(r['proven_protected'] and not r['proven_clean'] for r in edge_summaries)

held_all = {r['canonical_owner_id'] for r in owners if r['current_disposition'] == 'HOLD_ANCESTRY_UNRESOLVED'}
pure_protocol = {r['canonical_owner_id'] for r in owners if r['source_disposition'] == 'PROTOCOL_PREFIX_NO_BUSINESS_SOURCE'}
unknown = {r['canonical_owner_id'] for r in owners if overlay_by_owner.get(r['canonical_owner_id'],r)['current_disposition'] == 'UNKNOWN_SUPPLEMENTAL_PREFIX_NOT_AUDITED'}
identity = {r['canonical_owner_id'] for r in owners if r['current_disposition'] == 'HOLD_CURRENT_SOURCE_IDENTITY_MISSING'}
base_protected = {r['canonical_owner_id'] for r in owners if overlay_by_owner.get(r['canonical_owner_id'],r)['current_disposition'].startswith('ISOLATED_')}
queue_sets = {'already_scoped_partial_A_admitted_writers': admitted, 'known_bad_full_writer_hold': known_bad,
    'priority_remaining_complete_writers': remaining_complete, 'other_business_semantic_pending': other_pending,
    'business_protocol_auxiliary': auxiliary, 'business_readonly_not_complex_program': readonly,
    'pure_protocol_no_business_source': pure_protocol, 'lineage125_now_confirmed_protected': protected196,
    'lineage63_method_equivalent_but_protected_producer_and_no_frozen_merge': method63,
    'lineage8_specific_missing_evidence': missing8, 'other_ancestry_hold': held_all - all196,
    'unreviewed_supplemental_prefix': unknown, 'current_source_identity_missing': identity,
    'corpus_base_plus73_explicit_protected': base_protected}
seen = set()
for name, ids in queue_sets.items():
    assert not (ids & seen), (name, sorted(ids & seen))
    seen |= ids
assert seen == set(by_owner)

shard_pins = []
counts = collections.Counter()
stages = collections.defaultdict(collections.Counter)
for declared in manifest['actual_train_files']:
    path = MAIN / declared['path']
    p = pin(path)
    assert (p['bytes'], p['sha256']) == (declared['bytes'], declared['sha256'])
    shard_pins.append(p)
    for row in rows(path):
        counts['sequences'] += 1
        counts['input_tokens'] += row['total_tokens']
        counts['supervised_tokens'] += row['supervised_tokens']
        counts['le16k_sequences'] += row['total_tokens'] <= 16384
        counts['le32k_sequences'] += row['total_tokens'] <= 32768
        counts.update({'component_' + k: v for k,v in row['supervised_tokens_by_component'].items()})
        group = row['stage'][0] if row['stage'][0] in 'ABCD' else 'HISTORICAL_WORKFLOW_R'
        stages[group]['sequences'] += 1
        stages[group]['supervised_tokens'] += row['supervised_tokens']
assert len(shard_pins) == 24 and counts['sequences'] == 569
assert all(counts[k] == v for k,v in manifest['actual_counts'].items() if k != 'targets')

report = {'schema': 'wrd08-corpus-readiness-set-audit-20261031-v1',
    'status': 'PASS_METADATA_RECOUNT_NOT_NEW_TRAINING_ADMISSION',
    'reviewer': '/root/scheduled_batch24',
    'recount_script': pin(Path(__file__).resolve()),
    'performed': 'Metadata/set joins, entity SHA and existing approved shard recount only; no business resource execution, model, Teacher/Actor, training or new data collection.',
    'input_pins': [pin(x) for x in [owner_path,write_path,overlay_path,receipt_path,alias_path,target_path,edge_path,manifest_path,bank_path,held_path,registry_path]],
    'current569_shards': shard_pins, 'current569_recount': dict(counts),
    'current569_stage_groups': {k:dict(v) for k,v in stages.items()},
    'current569_manifest_provenance_tokens': manifest['supervision_origin_tokens'],
    'current569_process_targets': 569 - manifest['by_bank']['source_contract_main']['targets'],
    'current569_process_supervised_tokens': counts['supervised_tokens'] - manifest['by_bank']['source_contract_main']['supervised_tokens'],
    'known_readiness_limits': {k:manifest[k] for k in ['distinct_source_ids','source_connected_components_across_banks','observed_stage_linked_chains','positive_qualified_retained_skill_chains','single_native_session_autonomous_A_through_D_demonstrations','missing_main_stages','full_WRD_main_training_ready','default_full_pipeline_training_entrypoint','model_weights_loaded','training_started']},
    'population': {'registered_native_owners':34616,'population_counts':dict(collections.Counter(r['population'] for r in owners)),
        'base_current_disposition':dict(base_count),'base_source_disposition':dict(source_count),
        'effective_only_Native73_overlay':dict(effective_count),'base_current_nonempty_source_cross_table':{k:dict(v) for k,v in cross.items()},
        'native_full_write_carriers':653,'source_closed_nonempty_business_owner_count':1363,
        'source_closed_nonempty_business_source_count':len({s for x in business for s in by_owner[x]['source_ids']}),
        'source_closed_pending_business_count':746,'source_closed_pending_total_including483_pure_protocol':1229,
        'source_closed_business_auxiliary_count':615,'source_closed_business_readonly_count':2,
        'pure_protocol_count':1363,
        'warning':'The 1363 business owners and 1363 pure-protocol owners are two distinct equally-sized sets; 1229=746 business+483 protocol. Source, owner, view and token units are not interchangeable.'},
    'source_closed_full_writes': {'count':40,'unique_whole_code_SHA':len({write_by_owner[x]['original_content_utf8_SHA256'] for x in complete}),
        'source_count':len({s for x in complete for s in by_owner[x]['source_ids']}),
        'is_subset_of_business_pending746':True, 'all40_code_entity_SHA_recomputed':True,
        'partial_A_already_admitted8':describe(admitted),'known_bad_full_writer1':describe(known_bad),
        'remaining31_not_in_first6_or_current_writer_bank':describe(remaining_complete),
        'old552_native_link_intersection_with1363':0,'old552_native_link_count':len(baseline_native_links),
        'sealed29_baseline_receipts_containing40_exact_owner_IDs':receipt_matches,
        'review_history_limit':'31 is the residual under explicit first6/08/current-bank receipts; absence of an exact owner ID in 29 baseline receipts is not proof nobody historically read the code. None of31 is newly admitted.'},
    'lineage196':{'decision_counts':{k:len(v) for k,v in decision_sets.items()},
        'all196_within_base6272_ancestry_hold':True,'intersection_with_business1363':0,'intersection_with_native73_static_overlay':0,
        'remaining71_source_clean_not_proven':True,'method63_route_counts':describe(method63)['route_counts'],
        'missing8_route_counts':describe(missing8)['route_counts'], 'method63_producer_edge_metadata':edge_summaries,
        'method63_warning':'All 9 candidate method-producer edges are proven-protected producers. They do not establish the exact original source/condition merge for downstream route. Do not treat63 or71 as salvageable training examples. Original226 producer inputs cannot be laundered by new labels.',
        'known125_limit':'125 now explicitly protected in lineage overlay; old sealed owner rows remain HOLD and are not silently rewritten.'},
    'disjoint_primary_owner_work_queue':{name:describe(ids) for name,ids in queue_sets.items()},
    'disjoint_primary_queue_count_sum':sum(map(len,queue_sets.values())),
    'all_primary_sets_pairwise_disjoint_and_cover34616':True,
    'remaining_source_pool_registry':{'pin':pin(registry_path),'current569':{k:v for k,v in registry['current569'].items() if k!='remaining_materials'},
        'remaining_authentic_materials':{k:v for k,v in registry['current569']['remaining_materials'].items() if k not in ['source_ids','unique_SHA']},
        'remaining387_intersect_sourceClosed1363_sources':34,'remaining387_intersect_sourceClosed40_sources':8,
        'warning':'387 sources/378 source_scope groups overlap existing owner work queues; not additive to746/1363/40. 19 material-bearing sources are not19 qualified tasks. 271 used source_scope groups differ from264 training cross-bank DSU components.'},
    'recommended_order':[
        {'priority':1,'unit':'31 complete-writer owners','action':'Read actual source requirement + whole original code + actual local observations; assign API/execution/semantic credit separately; exact mask for unsupported literals; keep one full-program unit per edit and deduplicate variants.','acceptance':'Explicit scoped semantic receipt, source/version/read/call/obs pins, verified minimal execution if later authorized, dual tokenizer exact mask. No new positive count predicted.'},
        {'priority':2,'unit':'706 other business semantic-pending owners','action':'Group by episode/actual artifact lineage, distinguish workflow choices, reads, resource construction, edits and feedback; attach action verdict to last verified resource/trial result, preserving both failed and fixed versions.','acceptance':'Step correctness and causal input boundary explicit; completed/exit0 alone gives no positive loss. Original R only when native/provider identity and chronological prefix are exact.'},
        {'priority':3,'unit':'615 business auxiliary owners; 2 read-only owners separately','action':'Recover genuinely reusable complete resource/control actions only; routine protocol/read-only observations remain context or zero loss, not extra business demonstrations.','acceptance':'Source closure plus independent semantic judgment; counts not inflated by splitting contracts or calls.'},
        {'priority':4,'unit':'387 unused independent-source candidates, including19 with material refs','action':'Reserve source_scope components for student dev/test BEFORE any further labels or resources enter training. Inspect material bodies and task diversity only inside selected clean components. Reuse existing owner/artifact work rather than double counting.','acceptance':'Authentic inputs validated; no material/source ancestry intersection with training; nonzero holdout arrays and executable whole-skill rubric with TSR, Q, cost/qualifiedskill.'},
        {'priority':5,'unit':'63 method/8 missing targeted lineage owners','action':'Close exact original source/condition/version bridges if available; if protected inheritance established, isolate. Otherwise retain HOLD. Do not synthesize original thought or replace protected route with nominal clean labels.','acceptance':'Exact entity identity + actual read/observation boundary; never inferred from route name, nearby timestamp or method-field similarity.'},
        {'priority':6,'unit':'6076 other old ancestry HOLD +2173 unreviewed supplemental +56 identity-missing','action':'Metadata triage with separate identities and source/producer graphs; only move exact proven clean subsets to semantic review.','acceptance':'No blanket positive-loss import or estimated recoverable yield.'}],
    'no_new_training_count_claimed':True,'new_admitted_targets_this_review':0,
    'AI_curation_cost':'Existing offline AI curation occurred; usage/cost unknown, not zero. new_business_Teacher_Actor_calls0 only excludes new business model dispatch.'}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'corpus_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':report['status'],'report':pin(OUT/'corpus_audit.json'),
    'remaining31_episodes':report['source_closed_full_writes']['remaining31_not_in_first6_or_current_writer_bank']['episodes'],
    'remaining31_sources':len(report['source_closed_full_writes']['remaining31_not_in_first6_or_current_writer_bank']['source_ids']),
    'queue_counts':{k:len(v) for k,v in queue_sets.items()},'current569_recount':dict(counts),
    'stage_groups':report['current569_stage_groups']},ensure_ascii=False))
