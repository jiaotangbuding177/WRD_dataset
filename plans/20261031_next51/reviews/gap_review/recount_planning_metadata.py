"""Read existing final09 metadata only; no content labeling, compiling or admission."""
from pathlib import Path
import gzip,json,hashlib,collections
ROOT=Path('D:/skillloop'); OUT=Path(__file__).parent
def h(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(l) for l in gzip.open(p,'rt',encoding='utf-8-sig') if l.strip()]
def pin(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def dump(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 overlay=ROOT/'output/20261031_wrd_curation09/process/batch02/coverage_overlay/CURRENT34616_OWNER_COVERAGE09_FINAL_OVERLAY.jsonl.gz'
 viewp=overlay.parent/'FINAL_CURRENT_VIEW_COMPONENTS.jsonl.gz'
 manifest=ROOT/'output/20261027_wrd_main_v10/TRAINING_MANIFEST.json'
 allrows=rows(overlay); views=rows(viewp); man=load(manifest)
 names=['other_ancestry_hold','unreviewed_supplemental_prefix','current_source_identity_missing',
 'lineage63_method_equivalent_but_protected_producer_and_no_frozen_merge','lineage8_specific_missing_evidence']
 old=[r for r in allrows if r['09_effective_queue'] in names]
 def flags(r):
  protected=bool(r['09_final_protected_sources'] or r['09_final_protected_components'])
  reserved=bool(r['09_final_reserved_sources'] or r['09_final_reserved_components'])
  linked=bool(r['09_final_current_scoped_admission'])
  return protected,reserved,linked
 def category(r):
  p,q,a=flags(r)
  return 'new_protected_isolated' if p else 'reserved_isolated_after_protected' if q else 'already_current_scoped_view_linked_prefix_not_promoted' if a else 'unlinked_conditional_prefix_not_admitted'
 summary={}
 for name in names:
  rr=[r for r in old if r['09_effective_queue']==name]
  summary[name]={'historical_owner_count':len(rr),'exclusive_current_dispositions':dict(collections.Counter(category(r)for r in rr)),
   'episodes':len(set(r['episode_id']for r in rr)),'sources':sorted(set(s for r in rr for s in r['source_ids'])),
   'historical_roles':dict(collections.Counter(str(r.get('historical_role'))for r in rr)),
   'native_readable_R_blocks':dict(collections.Counter(str(r.get('native_readable_R_blocks'))for r in rr))}
 inv=OUT/'OLD8376_REBASED_OWNER_WORKLOAD.metadata.jsonl.gz'
 with gzip.GzipFile(filename=str(inv),mode='wb',mtime=0) as gz:
  for r in old:
   o={k:r.get(k)for k in ['canonical_owner_id','episode_id','native_session_id','source_message_index','source_event_line','historical_role','route_id','source_ids','current_source_statuses','source_native','native_response_id','native_readable_R_blocks','09_effective_queue','09_final_disposition','09_final_current_view_links','09_final_protected_sources','09_final_protected_components','09_final_reserved_sources','09_final_reserved_components']}
   o['next51_mutually_exclusive_metadata_workload']=category(r)
   o['source_closed_not_semantic_good']=True;o['current_view_does_not_promote_original_prefix']=True
   gz.write((json.dumps(o,ensure_ascii=False,separators=(',',':'))+'\n').encode())
 process_views=[v for v in views if v['bank']!='source_contract_main']
 process_sources=set(s for v in process_views for s in v['source_ids'])
 current_owners={o:v['view_id']for v in views for o in v['native_owner_links']}
 current_ep={r['episode_id']for r in allrows if r['canonical_owner_id'] in current_owners}
 episode_rows=collections.defaultdict(list)
 for r in allrows:episode_rows[r['episode_id']].append(r)
 holds=[r for r in allrows if r['09_final_disposition']=='HOLD_SPECIFIC_CONTENT_OR_EVIDENCE_DEFECT']
 writers=[r for r in allrows if r['09_effective_queue']=='priority_remaining_complete_writers']
 d=ROOT/'output/20261030_wrd_gap08/lineage'
 edgep=d/'SAME_VERSION_TRIAL_AND_REVIEW_EDGES.audit.jsonl.gz';pkgp=d/'FROZEN_COMPLETE_PACKAGE_VERSIONS.jsonl.gz';epp=d/'EPISODE_RECOVERY_46.json';recp=d/'ROUTE_PRODUCER_TO_ACTUAL_RECEIPT.jsonl.gz'
 edges=rows(edgep); packages=rows(pkgp);eps={e['episode_id']:e for e in load(epp)['episodes']}; receipts=rows(recp)
 meta=[]
 for e in edges:
  producers=[eps[p]for p in e['producer_episode_ids']]
  actorrows=episode_rows[e['actor_episode_id']]
  involved={e['actor_episode_id'],e['reviewer_episode_id'],*e['producer_episode_ids']}
  intersections=[]
  for ep in involved:
   intersections.extend({'episode_id':ep,'canonical_owner_id':r['canonical_owner_id'],'view_id':current_owners[r['canonical_owner_id']]}for r in episode_rows[ep]if r['canonical_owner_id']in current_owners)
  m={k:e[k]for k in ['edge_id','actor_episode_id','producer_episode_ids','reviewer_episode_id','route_id','source_id','case_id','tree_content_sha256','candidate_tree_matches_consumed_complete_tree']}
  m.update({'producer_strict_boundary':any(p.get('strict_protected_boundary') is not None for p in producers),
   'producer_method_candidate_boundary':any(p.get('method_only_candidate_boundary') is not None for p in producers),
   'actual_full_SKILL_delivery_record_count':len(e['actual_full_SKILL_delivery']),
   'case_source_in_current_process54':e['source_id']in process_sources,
   'actor_episode_has_any_owner_protected_metadata':any(flags(r)[0]for r in actorrows),'actor_episode_has_any_owner_reserved_metadata':any(flags(r)[1]for r in actorrows),
   'episode_any_owner_overlay_not_automatically_target_prefix_boundary':True,
   'current_view_intersections':intersections,'historical_Q_and_review_text_not_inspected_or_reused':True,
   'admissible_clean_complete_utility_chain_proven':False})
  meta.append(m)
 edgeout=OUT/'OUTCOME35_CURRENT09_CROSSCHECK.metadata.json';dump(edgeout,meta)
 result={'status':'READ_ONLY_PLANNING_METADATA_NOT_NEW_TRAINING_DATA_OR_SEMANTIC_REVIEW',
  'input_pins':[pin(p)for p in [overlay,viewp,manifest,edgep,pkgp,epp,recp]],'current09_actual_counts':man['actual_counts'],
  'old8376_rebased':{'historical_owner_count':len(old),'exclusive_current_dispositions':dict(collections.Counter(category(r)for r in old)),
   'protected_flag_count':sum(flags(r)[0]for r in old),'reserved_flag_count':sum(flags(r)[1]for r in old),'protected_reserved_flag_overlap':sum(flags(r)[0]and flags(r)[1]for r in old),
   'by_historical_queue':summary,'metadata_workload_pin':pin(inv),'not_trainable_sample_count':True},
  'already_specific_reviewed_holds':{'owners':len(holds),'episodes':len(set(r['episode_id']for r in holds)),
   'sources':len(set(s for r in holds for s in r['source_ids'])),'routes':dict(collections.Counter(r['route_id']for r in holds)),
   'new_positive_promise':None,'must_join_previous_specific_defect_and_new_evidence_first':True},
  'writer31':{'owners':len(writers),'dispositions':dict(collections.Counter(r['09_final_disposition']for r in writers)),
   'current_scoped_linked_owners':sum(flags(r)[2]for r in writers),'whole_original_prefix_admission_not_inferred':True},
  'current_process':{'views':len(process_views),'source_count':len(process_sources),'source_ids':sorted(process_sources)},
  'outcome35':{'metadata_edges':len(meta),'distinct_tree_versions':len(set(e['tree_content_sha256']for e in meta)),
   'distinct_actor_tree_case_trials':len(set((e['actor_episode_id'],e['tree_content_sha256'],str(e['case_id']))for e in meta)),
   'distinct_actors':len(set(e['actor_episode_id']for e in meta)),
   'producer_strict_boundary_edges':sum(e['producer_strict_boundary']for e in meta),
   'producer_method_candidate_boundary_edges':sum(e['producer_method_candidate_boundary']for e in meta),
   'actual_full_SKILL_delivery_count_distribution':dict(collections.Counter(e['actual_full_SKILL_delivery_record_count']for e in meta)),
   'case_source_in_current_process54_edges':sum(e['case_source_in_current_process54']for e in meta),
   'actor_episode_any_owner_protected_metadata_edges':sum(e['actor_episode_has_any_owner_protected_metadata']for e in meta),'actor_episode_any_owner_reserved_metadata_edges':sum(e['actor_episode_has_any_owner_reserved_metadata']for e in meta),
   'current_view_intersections':[x for e in meta for x in e['current_view_intersections']],
   'clean_complete_utility_or_KEEP_chains_proven':0,
   'clean_Q_revision_feedback_edges_proven':0,
   'zero_proven_does_not_assert_no_other_recoverable_clean_edges_exist':True,
   'metadata_crosscheck_pin':pin(edgeout)},
  'no_protected_thought_or_Q_or_review_text_used':True,'main_modified':False,'new_token_compilation':False,'training_started':False}
 p=OUT/'GAP_REVIEW_METADATA.json';dump(p,result)
 print(json.dumps({'summary_pin':pin(p),'rebased':result['old8376_rebased']['exclusive_current_dispositions'],'by_queue':{k:v['exclusive_current_dispositions']for k,v in summary.items()},'holds':{k:v for k,v in result['already_specific_reviewed_holds'].items()if k!='routes'},'writers':result['writer31'],'current_process_sources':len(process_sources),'outcome35':result['outcome35']},ensure_ascii=False))
if __name__=='__main__':main()
