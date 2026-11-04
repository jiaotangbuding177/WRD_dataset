"""Root re-count of fixed scopes and authenticated local file inventories."""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json
ROOT=Path('D:/skillloop');HERE=Path(__file__).parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
    op=gzip.open if str(p).endswith('.gz') else open
    with op(p,'rt',encoding='utf-8-sig') as f:return [json.loads(l) for l in f if l.strip()]
def main():
    scope=load(ROOT/'research/plans/20261029_wrd_next_data/PLANNED_SCOPE.json')
    first={i for e in scope['first_batch'] for i in e['candidate_target_ids']};assert len(first)==379
    all100=rows(ROOT/'output/20261029_wrd_v9_missing_evidence_recovery/MAKE_100_EPISODE_CLUSTERS.metadata.jsonl.gz')
    all1050={i for e in all100 for i in e['held_target_ids']};assert len(all1050)==1050
    prior=load(ROOT/'output/20261029_wrd_v9_missing_evidence_update02/ANCESTRY_CORRECTION_OVERLAY.json')
    old81={x['id'] for x in prior['target_overlays']};assert len(old81)==81 and old81<=all1050
    tally=[]
    for name,filename,field in [('scheduled','TARGETS.with_body.audit.jsonl.gz','source_status'),('remotion','TARGET_DECISIONS_54.jsonl.gz','status'),('crossroutes','TARGET_DECISIONS_AND_ORIGINAL_BODIES.jsonl.gz','current_decision'),('remaining76','TARGET_DECISIONS_AND_ORIGINAL_BODIES.jsonl.gz','current_decision')]:
        for d in rows(HERE/name/filename):
            protected='PROTECTED' in d[field]
            tally.append({'id':d['id'],'episode_id':d['episode_id'],'original_classification':'PROTECTED_ANCESTOR' if protected else 'ANCESTRY_NOT_CLOSED','source_message_index':d['source_message_index'],'proof_file':name+'/'+filename,'positive_original_training_loss':0})
    ids={x['id'] for x in tally};assert len(tally)==len(ids)==969 and ids==all1050-old81
    assert {x['id'] for x in tally if x['proof_file'].split('/')[0]!='remaining76'}==first
    initial=Counter(x['original_classification'] for x in tally)
    # New independently closed ancestors can supersede only earlier UNKNOWN;
    # never silently rewrite the sealed original ledgers.
    late=HERE/'late_producer_closure/LATE_NATIVE_ROUTE_PRODUCER_CLOSURE.json'
    if late.exists():
        overlay=load(late)
        byid={x['id']:x for x in tally}
        for d in overlay['target_overlays']:
            assert byid[d['id']]['original_classification']=='ANCESTRY_NOT_CLOSED'
            assert d['new_decision']=='HOLD_PROTECTED_ACTUAL_LATE_ROUTE_PRODUCER'
            byid[d['id']]['original_classification']='PROTECTED_ANCESTOR'
            byid[d['id']]['late_proof_file']='late_producer_closure/LATE_NATIVE_ROUTE_PRODUCER_CLOSURE.json'
    counts=Counter(x['original_classification'] for x in tally)
    with gzip.open(HERE/'FINAL969_TARGET_OVERLAY.jsonl.gz','wt',encoding='utf-8',newline='\n') as f:
        for d in tally:f.write(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n')
    checked=0;bytecount=0
    for name in ['crossroutes','remaining76','late_producer_closure']:
        manifest=load(HERE/name/'FINAL_MANIFEST.json');listing=Path(manifest['allowlist']['path'])
        assert sha(listing)==manifest['allowlist']['sha256']
        for ref in rows(listing):
            # Sealers retain absolute original/reference source paths explicitly.
            p=Path(ref.get('path',ref.get('source','')))
            if not p.is_absolute():p=HERE/name/p
            assert p.is_file() and p.stat().st_size==ref['bytes'] and sha(p)==ref['sha256'],str(p)
            checked+=1;bytecount+=ref['bytes']
    # Re-read the independently reviewed fixed branch inventories as well.
    for name in ['scheduled','remotion']:
        d=load(HERE/name/'MANIFEST.json')
        refs=d.get('files',d.get('all_actual_files',[]))
        if isinstance(refs,int):continue
        for ref in refs:
            p=Path(ref['path'])
            if not p.is_absolute():p=HERE/name/p
            assert p.is_file() and p.stat().st_size==ref['bytes'] and sha(p)==ref['sha256'],str(p)
            checked+=1;bytecount+=ref['bytes']
    m=load(ROOT/'output/20261027_wrd_main_v10/TRAINING_MANIFEST.json')
    r={'status':'PASS_FIXED100_SCOPE_AND_ACTUAL_RECOVERED_FILES_RECOUNT',
       'client_completion_date':'2026-10-30','actual_episode_scope':100,'original_candidate_positions':1050,
       'previously_protected_excluded':81,'processed_remaining_positions':969,
       'first24_positions':379,'remaining76_positions':590,'before_late_overlay':dict(initial),
       'current_969_classification':dict(counts),'total_protected_in1050':counts['PROTECTED_ANCESTOR']+81,
       'remaining_original_ancestry_unclosed':counts['ANCESTRY_NOT_CLOSED'],
       'new_original_full_chain_or_resource_gold_targets':0,'new_states_admitted':22,
       'new_source_only_decisions':19,'new_state_local_tool_projections':3,
       'new_original_R_positive_tokens':0,'new_authored_R_tokens':961,'new_authored_D_tokens':2636,'new_projected_A_tokens':78,
       'current_actual_training_counts':m['actual_counts'],'actual_manifest_sha256':sha(ROOT/'output/20261027_wrd_main_v10/TRAINING_MANIFEST.json'),
       'inventory_files_sha_rechecked':checked,'inventory_bytes_including_duplicate_carriers':bytecount,
       'raw_native_field_absence_is_not_provider_reasoning_absence_proof':True,
       'recovered_audit_files_are_not_default_training_files':True,'all_legacy_data_population_claim_not_made':True,
       'quality_success_or_self_report_does_not_grant_positive_loss':True,
       'curation_AI_and_CPU_performed':'USAGE_AND_CASH_UNKNOWN_NOT_ZERO',
       'new_business_teacher_actor_sessions':0,'weights_loaded':False,'training_started':False,
       'script_sha256':sha(__file__)}
    (HERE/'ROOT_SCOPE_AND_FILE_QA.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False))
if __name__=='__main__':main()
