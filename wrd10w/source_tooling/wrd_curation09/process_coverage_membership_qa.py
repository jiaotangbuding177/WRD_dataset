"""Validate final595 view/owner membership without inferring full-prefix credit."""
import gzip,json,hashlib
from pathlib import Path
from collections import Counter,defaultdict

ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'output/20261031_wrd_curation09'
DEST=WORK/'process/batch02/coverage_overlay'
MAIN=ROOT/'output/20261027_wrd_main_v10/TRAINING_MANIFEST.json'
EXPECTED='01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rows(path):return list(map(json.loads,gzip.open(path,'rt',encoding='utf8')))

def main():
    assert sha(MAIN)==EXPECTED
    prior={r['view_id']:r for r in rows(WORK/'coverage/CURRENT569_VIEW_COMPONENTS.jsonl.gz')}
    current={r['view_id']:r for r in rows(DEST/'FINAL_CURRENT_VIEW_COMPONENTS.jsonl.gz')}
    ledger=rows(DEST/'CURRENT34616_OWNER_COVERAGE09_FINAL_OVERLAY.jsonl.gz')
    assert len(prior)==569 and len(current)==595 and len(ledger)==len({r['canonical_owner_id']for r in ledger})==34616
    nativeowners={o for v in current.values()for o in v['native_owner_links']}
    byowner={r['canonical_owner_id']:r for r in ledger};assert nativeowners<=set(byowner)
    for owner in nativeowners:
        expected={v['view_id']for v in current.values()if owner in v['native_owner_links']}
        actual={v['view_id']for v in byowner[owner]['09_final_current_view_links']}
        assert expected==actual and byowner[owner]['09_final_current_scoped_admission']
    allmain=set()
    manifest=json.loads(MAIN.read_text(encoding='utf8'))
    for ref in manifest['actual_train_files']:
        path=MAIN.parent/ref['path'];assert sha(path)==ref['sha256']
        for record in rows(path):
            assert record['id']not in allmain;allmain.add(record['id'])
    assert allmain==set(current)
    removed=sorted(set(prior)-set(current));added=sorted(set(current)-set(prior));kept=sorted(set(prior)&set(current))
    assert len(removed)==23 and len(added)==49 and len(kept)==546
    result={'status':'PASS595_FINAL_MANIFEST_AND34616_DISTINCT_OWNER_MEMBERSHIP',
        'main_sha256':sha(MAIN),'prior_views':569,'current_views':595,'kept_prior_views':546,'withdrawn_prior_views':23,'added_views':49,
        'native_owners_with_any_current_scoped_view':len(nativeowners),
        'current_views_with_native_owner_links':sum(bool(v['native_owner_links'])for v in current.values()),
        'current_views_with_external_historical_owner_links':sum(bool(v['external_historical_owner_links'])for v in current.values()),
        'current_views_without_either_owner_link':sum(not v['native_owner_links']and not v['external_historical_owner_links']for v in current.values()),
        'no_owner_link_implies_new_authorship':False,
        'current_native_owner_count_is_not_original_native_A_R_or_whole_pipeline_success_count':True,
        'original_prefix_dimension':{
            'owner_with_reserved_source_or_component':sum(bool(r['09_final_reserved_sources']or r['09_final_reserved_components'])for r in ledger),
            'owner_with_protected_source_or_component':sum(bool(r['09_final_protected_sources']or r['09_final_protected_components'])for r in ledger),
            'current_linked_owner_with_reserved_prefix':sum(bool(byowner[o]['09_final_reserved_sources']or byowner[o]['09_final_reserved_components'])for o in nativeowners),
            'current_linked_owner_with_protected_prefix':sum(bool(byowner[o]['09_final_protected_sources']or byowner[o]['09_final_protected_components'])for o in nativeowners),
            'whole_original_prefix_admitted':0},
        'withdrawn_prior_view_ids':removed,'added_view_ids':added,
        'withdrawn_view_metadata':[{'id':oid,'bank':prior[oid]['bank'],'source_ids':prior[oid]['source_ids'],
            'native_owner_links':prior[oid]['native_owner_links'],'external_historical_owner_links':prior[oid]['external_historical_owner_links'],
            'view_conditioning':prior[oid]['view_conditioning']}for oid in removed],
        'final_view_by_bank':dict(Counter(v['bank']for v in current.values())),
        'final_view_conditioning_labels_with_authorship_not_inferred_for_unresolved':dict(Counter(v['view_conditioning']for v in current.values())),
        'view_membership_and_owner_ancestry_are_different_units':True,'training_started':False,'new_Teacher_Actor_calls':0,
        'input_pins':[{'path':str(p),'sha256':sha(p)}for p in [WORK/'coverage/CURRENT569_VIEW_COMPONENTS.jsonl.gz',DEST/'FINAL_CURRENT_VIEW_COMPONENTS.jsonl.gz',DEST/'CURRENT34616_OWNER_COVERAGE09_FINAL_OVERLAY.jsonl.gz']],
        'script_sha256':sha(__file__)}
    out=DEST/'FINAL595_VIEW_OWNER_MEMBERSHIP_QA.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k]for k in ['current_views','kept_prior_views','withdrawn_prior_views','added_views','native_owners_with_any_current_scoped_view','current_views_with_native_owner_links','current_views_with_external_historical_owner_links','current_views_without_either_owner_link']},ensure_ascii=False))

if __name__=='__main__':main()
