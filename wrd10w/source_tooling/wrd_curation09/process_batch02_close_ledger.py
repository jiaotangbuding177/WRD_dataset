"""Close all1321 owner states without mutating the v1 lane or main manifest."""
import gzip,hashlib,json
from collections import Counter
from pathlib import Path
from process_batch02_review import BASE,OUT,read,dump,main as write_reviews
from process_batch02_candidates import sha,h,DATA,RES

def rows(path):
    return list(map(json.loads,gzip.open(path,'rt',encoding='utf8')))

def main():
    write_reviews()
    old=read('OWNER1321_DISPOSITION09.jsonl.gz'); owners={r['owner_id']:r for r in read('OWNER1321_EXACT_CONTENT.audit.jsonl.gz')}
    reviews={r['owner_id']:r for r in rows(OUT/'CONTENT_REVIEW_BATCH02.jsonl.gz')}
    assert len(old)==len({r['owner_id']for r in old})==1321 and len(reviews)==576
    reservation=json.loads(RES.read_text(encoding='utf8'))
    closure_path=RES.parent/'PROTECTED_CURRENT569_REVOCATION_CLOSURE.json'
    closure=json.loads(closure_path.read_text(encoding='utf8'))
    reserved=set(reservation['reserved_source_ids']);components=set(reservation['reserved_source_scope_components'])
    revoked=set(closure['revoke_source_ids']);revoked_components=set(closure['revoke_source_scope_component_ids'])
    scope={r['source_id']:r for r in rows(DATA/'clean_inputs/source_scope.metadata.jsonl.gz')}
    input_files=[OUT/'SCOPED_CANDIDATES_FINAL14_v2.jsonl.gz',OUT/'SCOPED_ADDITIONAL_CANDIDATES03_v3.jsonl.gz']
    supplied={r['owner_id']:{'id':r['id'],'path':str(path),'sha256':sha(path)} for path in input_files for r in rows(path)}
    assert len(supplied)==17
    final=[];delta=[]
    for before in old:
        row=dict(before);oid=row['owner_id'];owner=owners[oid];ids=row['source_ids']
        row['v1_processing_disposition']=before['processing_disposition'];row['v1_ledger_sha256']=sha(BASE/'OWNER1321_DISPOSITION09.jsonl.gz')
        row['schema_version']='wrd09-process1321-disposition-v2'
        row['original_message_index']=owner['source_message_index']
        row['original_internal_R_admitted']=False;row['new_positive_loss_admitted_by_this_lane']=False
        row['root_final_training_admission']='EXTERNAL_ROOT_MANIFEST_DECISION_NOT_WRITTEN_BY_PROCESS_LANE'
        if oid in reviews:
            review=reviews[oid]
            row['content_review']=review
            row['semantic_review_scope']=review['review_scope']
            row['processing_disposition']=review['review_disposition']
            row['specific_reason']=review['concrete_reason']
            row['future_review_required']=False
            if review['review_disposition']=='SCOPED_VALIDATION_ACTION_CANDIDATE_PENDING_ROOT_QA':
                if oid in supplied:
                    row['processing_disposition']='COMPLETE_SCOPED_VIEW_SUPPLIED_FOR_ROOT_FINAL_DECISION'
                    row['candidate_file_pin']=supplied[oid]
                else:
                    assert oid=='fe6facbf46882ca14fc4cd17'
        else:
            row['semantic_review_scope']='NOT_CLAIMED_IN_BATCH02_576_CONTENT_REVIEW; ORIGINAL_V1_MECHANICAL_CONTEXT_OR_ISOLATION_OR_PREVIOUS17_REVIEW_PRESERVED'
        groups={scope[s]['component_id']for s in ids if s in scope}
        protected=bool(set(ids)&revoked or groups&revoked_components)
        if protected:
            row['pre_protected_closure_disposition']=row['processing_disposition']
            row['processing_disposition']='ISOLATED_PROTECTED_REVOCATION_COMPONENT_NO_TRAIN_LOSS'
            row['source_scope_at09_reservation']='ISOLATED_PROTECTED_CLOSURE'
            row['specific_isolation_evidence']={'direct_source_ids':sorted(set(ids)&revoked),'scope_component_ids':sorted(groups&revoked_components),'closure_path':str(closure_path),'closure_sha256':sha(closure_path)}
            row['candidate_file_pin']=None;row['future_review_required']=False
            delta.append({'owner_id':oid,'v1':before['processing_disposition'],'v2':row['processing_disposition'],'source_ids':ids})
        elif set(ids)&reserved or groups&components:
            row['processing_disposition']='ISOLATED_NEW_DEV_TEST_RESERVATION_NO_NEW_LOSS'
            row['future_review_required']=False
        if row['processing_disposition']=='CONTEXT_ONLY_READ_LIST_NO_TARGET_SUPERVISION_PROPOSED':row['future_review_required']=False
        assert row['processing_disposition']!='HOLD_NEEDS_SEMANTIC_REVIEW'
        assert row['processing_disposition']!='SCOPED_VALIDATION_ACTION_CANDIDATE_PENDING_ROOT_QA'
        final.append(row)
    out=OUT/'OWNER1321_DISPOSITION09_v2.jsonl.gz'
    with gzip.open(out,'wt',encoding='utf8')as stream:
        for row in final:stream.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    initial_pending={r['owner_id']for r in old if r['processing_disposition']=='HOLD_NEEDS_SEMANTIC_REVIEW'}
    assert initial_pending==set(reviews)
    summary={'status':'ALL_ORIGINAL576_CONTENT_DECISIONS_CLOSED_1321_UNIQUE_OWNER_LEDGER_NOT_WHOLE_CORPUS_BUSINESS_GOLD',
        'owners':len(final),'unique_owners':len({r['owner_id']for r in final}),
        'original_v1_counts':dict(Counter(r['processing_disposition']for r in old)),
        'all576_review_counts_before_latest_protection':dict(Counter(r['review_disposition']for r in reviews.values())),
        'v2_counts_after_protection':dict(Counter(r['processing_disposition']for r in final)),
        'original576_remaining_needs_semantic_review':0,'original576_distinct_episodes':len({r['episode_id']for r in reviews.values()}),
        'full_causal_packets_added':17,'actual_training_admitted_by_process_lane':0,
        'candidate_files':[{'path':str(p),'count':len(rows(p)),'sha256':sha(p)}for p in input_files],
        'protected_closure_affected_owners':len(delta),'protected_closure_delta':delta,
        'ledger_pin':{'path':str(out),'bytes':out.stat().st_size,'sha256':sha(out)},
        'content_review_pin':{'path':str(OUT/'CONTENT_REVIEW_BATCH02.jsonl.gz'),'sha256':sha(OUT/'CONTENT_REVIEW_BATCH02.jsonl.gz')},
        'reservation_sha256':sha(RES),'revocation_closure_sha256':sha(closure_path),
        'original_v1_preserved':True,'qualified_KEEP_gold':0,'complete_autonomy_gold':0,'original_internal_R_targets':0,
        'no_claim_all555_reads_or_long_program_business_bodies_wholly_semantically_verified':True,
        'Teacher_calls':0,'Actor_calls':0,'training_runs':0,'Codex_curation_cost':'UNKNOWN_NOT_ZERO','script_sha256':sha(__file__)}
    dump(OUT/'FINAL_1321_LEDGER_REVIEW.json',summary)
    # White/#00c4a3 exact relative-luminance calculation supports a specific held CSS claim.
    def linear(v):
        x=v/255
        return x/12.92 if x<=0.04045 else ((x+0.055)/1.055)**2.4
    lum=sum(w*linear(v)for w,v in zip([0.2126,0.7152,0.0722],[0,196,163]))
    dump(OUT/'CONTRAST_NUMERICAL_DEFECT.json',{'foreground':'#ffffff','background':'#00c4a3','relative_luminance_background':lum,'contrast_ratio':1.05/(lum+0.05),'large_text_minimum_ratio':3,'historical_claim':2.9,'method':'sRGB relative luminance and (Llight+0.05)/(Ldark+0.05); offline arithmetic, no image modification','scope':'Specific contrast statement defect, not full CSS browser evaluation'})
    print(json.dumps({k:summary[k]for k in ['owners','original576_remaining_needs_semantic_review','v2_counts_after_protection','protected_closure_affected_owners']},ensure_ascii=False))

if __name__=='__main__':main()
