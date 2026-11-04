"""Overlay final manifest membership onto exact native owner coverage.

Prepare-only until root freezes main and supplies its expected SHA. No training,
semantic admission or global manifest change is performed by this tool.
"""
import argparse,gzip,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
WORK=ROOT/'output/20261031_wrd_curation09'
BASE=WORK/'coverage/CURRENT34616_OWNER_COVERAGE09.jsonl.gz'
PRIOR=WORK/'coverage/CURRENT569_VIEW_COMPONENTS.jsonl.gz'
PROCESS=WORK/'process/batch02/OWNER1321_DISPOSITION09_v2.jsonl.gz'
WRITER=WORK/'writers/ALL31_SEMANTIC_VERDICTS.json'
DEST=WORK/'process/batch02/coverage_overlay'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def rows(path):
    with gzip.open(path,'rt',encoding='utf-8-sig')as stream:
        for line in stream:
            if line.strip():yield json.loads(line)
def js(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def write(path,values):
    with gzip.open(path,'wt',encoding='utf8')as stream:
        for value in values:stream.write(js(value)+'\n')

OWNER_KEYS={'canonical_owner_id','owner_id','original_recorded_action_owner','original_owner_id','native_owner_id','original_response_owner_id','original_R_response_owner','original_native_R_owner_id'}
def explicit_owner_ids(value):
    found=set()
    if isinstance(value,dict):
        for key,item in value.items():
            if key in OWNER_KEYS and isinstance(item,str):found.add(item)
            if key in {'native_owner_links','original_owner_ids','canonical_owner_ids'}and isinstance(item,list):found.update(x for x in item if isinstance(x,str))
            if isinstance(item,(dict,list)):found.update(explicit_owner_ids(item))
    elif isinstance(value,list):
        for item in value:
            if isinstance(item,(dict,list)):found.update(explicit_owner_ids(item))
    return found

def main(args):
    # No default/hash auto-detection: root must consciously provide frozen pin.
    assert sha(args.main)==args.expected_main_sha256,'ROOT_MAIN_CHANGED_OR_NOT_FROZEN'
    base=list(rows(BASE));known={r['canonical_owner_id']for r in base}
    assert len(base)==len(known)==34616
    bymessage={(r['episode_id'],r['source_message_index']):r['canonical_owner_id']for r in base}
    prior={r['view_id']:r for r in rows(PRIOR)}
    proc={r['owner_id']:r for r in rows(PROCESS)};writers={r['owner_id']:r for r in load(WRITER)['rows']}
    assert len(proc)==1321 and len(writers)==31 and set(proc)<=known and set(writers)<=known
    reserve=load(WORK/'holdout/holdout_reservation.json');closure=load(WORK/'holdout/PROTECTED_CURRENT569_REVOCATION_CLOSURE.json')
    reserved=set(reserve['reserved_source_ids']);reserved_groups=set(reserve['reserved_source_scope_components'])
    protected=set(closure['revoke_source_ids']);protected_groups=set(closure['revoke_source_scope_component_ids'])
    scope={r['source_id']:r for r in rows(ROOT/'output/20261027_wrd_main_v10/clean_inputs/source_scope.metadata.jsonl.gz')}
    manifest=load(args.main);links=defaultdict(list);views=[];seen=set();pins=[]
    for ref in manifest['actual_train_files']:
        path=args.main.parent/ref['path'];actualsha=sha(path)
        assert actualsha==ref['sha256'] and path.stat().st_size==ref['bytes'],'FINAL_MAIN_FILE_PIN_MISMATCH'
        pins.append({'path':str(path),'sha256':actualsha,'bytes':path.stat().st_size})
        for record in rows(path):
            viewid=record['id'];assert viewid not in seen;seen.add(viewid)
            meta=record['original_record_metadata'];previous=prior.get(viewid,{})
            declared=explicit_owner_ids(meta);native=set(previous.get('native_owner_links',[]))&known
            native.update(declared&known)
            ep=meta.get('original_episode_id');index=meta.get('original_message_index')
            if (ep,index)in bymessage:native.add(bymessage[(ep,index)])
            external=set(previous.get('external_historical_owner_links',[]))
            external.update(x for x in declared if x.startswith('historical_response:'))
            unknown=sorted(declared-known-external)
            ids=record.get('source_ids',[]);groups={scope[s]['component_id']for s in ids if s in scope}
            assert all(s in scope and scope[s]['status']=='TRAIN'for s in ids),'NON_TRAIN_OR_UNRESOLVED_SOURCE_IN_FINAL_MAIN'
            assert not(set(ids)&(reserved|protected)or groups&(reserved_groups|protected_groups)),'FORBIDDEN_SOURCE_IN_FINAL_MAIN'
            origin=meta.get('annotation_provenance',record.get('annotation_provenance'))
            conditioning=previous.get('view_conditioning')
            if conditioning is None:
                conditioning='NEW_EXPLICIT_FUNCTIONAL_INPUT_WITH_RECORDED_TARGET'if meta.get('original_native_prompt_equivalence_claimed')is False else 'DECLARED_METADATA_RETAINED_WITHOUT_INFERRED_AUTHORSHIP'
            view={'view_id':viewid,'bank':record['bank'],'stage':record['stage'],'compiled_file':str(path),
                'source_ids':ids,'native_owner_links':sorted(native),'external_historical_owner_links':sorted(external),
                'unresolved_declared_owner_ids':unknown,'view_conditioning':conditioning,
                'component_tokens':record.get('supervised_tokens_by_component',{}),'supervised_tokens':record['supervised_tokens'],
                'supervision_spans':record['supervision_spans'],'approved_field_ranges':meta.get('approved_field_ranges',[]),
                'target_excluded_rendered_ranges':meta.get('target_excluded_rendered_ranges',[]),
                'rendered_sha256':record['rendered_sha256'],'origin':origin,
                'owner_link_does_not_assign_all_components_or_original_prefix':True,
                'unlinked_view_status':'HAS_NATIVE_OR_EXTERNAL_HISTORICAL_OWNER_LINK'if native or external else 'NO_OWNER_LINK_AUTHORSHIP_NOT_INFERRED'}
            views.append(view)
            for owner in native:links[owner].append({'view_id':viewid,'bank':record['bank'],'stage':record['stage'],
                'view_conditioning':conditioning,'component_tokens_of_view_not_automatically_all_owned':view['component_tokens'],
                'supervised_tokens_of_view':view['supervised_tokens'],'original_prefix_admitted':False})
    output=[]
    for original in base:
        row=dict(original);oid=row['canonical_owner_id'];ids=row.get('source_ids',[]);groups={scope[s]['component_id']for s in ids if s in scope}
        protect=sorted(set(ids)&protected);pgroup=sorted(groups&protected_groups)
        reserv=sorted(set(ids)&reserved);rgroup=sorted(groups&reserved_groups)
        current=links.get(oid,[]);oldlinks=row.get('09_current_view_links',[])
        row['09_final_current_view_links']=current
        row['09_final_withdrawn_prior_view_ids']=[v['view_id']if isinstance(v,dict)else v for v in oldlinks if(v.get('view_id')if isinstance(v,dict)else v)not in seen]
        row['09_final_current_scoped_admission']=bool(current)
        row['09_final_original_prefix_admitted']=False
        row['09_final_protected_sources']=protect;row['09_final_protected_components']=pgroup
        row['09_final_reserved_sources']=reserv;row['09_final_reserved_components']=rgroup
        if oid in proc:row['09_final_process_content_decision']=proc[oid]
        if oid in writers:row['09_final_writer_content_decision']=writers[oid]
        if current:state='CURRENT_SCOPED_VIEW_ADMITTED_ORIGINAL_PREFIX_NOT_PROMOTED'
        elif protect or pgroup:state='PROTECTED_COMPONENT_ORIGINAL_OWNER_ISOLATED'
        elif reserv or rgroup:state='RESERVED_EVALUATION_COMPONENT_OWNER_ISOLATED'
        elif oid in proc:state=proc[oid]['processing_disposition']
        elif oid in writers:state=writers[oid]['disposition']
        else:state='UNCHANGED_PRIOR_COVERAGE_NO_NEW_SEMANTIC_CREDIT'
        if not current and row['09_final_withdrawn_prior_view_ids']:state='PRIOR_SCOPED_VIEW_WITHDRAWN_NOT_CURRENTLY_ADMITTED'
        row['09_final_disposition']=state
        row['09_final_note']='Current scoped targets, historical prefix isolation and new-state authorship are separate dimensions. No-owner-link views are not automatically new-authored targets.'
        output.append(row)
    assert len(output)==len({r['canonical_owner_id']for r in output})==34616
    DEST.mkdir(parents=True,exist_ok=False)
    ownerpath=DEST/'CURRENT34616_OWNER_COVERAGE09_FINAL_OVERLAY.jsonl.gz';viewpath=DEST/'FINAL_CURRENT_VIEW_COMPONENTS.jsonl.gz'
    write(ownerpath,output);write(viewpath,views)
    counts=Counter(r['09_final_disposition']for r in output)
    report={'status':'FINAL_MAIN_PINNED_OWNER_COVERAGE_OVERLAY_NOT_NEW_ADMISSION','owners':34616,'process_reviews':1321,'writer_reviews':31,
        'review_lane_owner_intersection':sorted(set(proc)&set(writers)),
        'current_views':len(views),'native_owners_with_current_scoped_views':len(links),
        'views_without_native_owner_links':sum(not r['native_owner_links']for r in views),
        'external_historical_linked_views':sum(bool(r['external_historical_owner_links'])for r in views),
        'views_without_any_owner_link':sum(not r['native_owner_links']and not r['external_historical_owner_links']for r in views),
        'no_owner_link_implies_new_authorship':False,'disposition_counts':dict(counts),
        'manifest_pin':{'path':str(args.main),'sha256':sha(args.main)},'main_train_file_pins':pins,
        'input_pins':[{'path':str(p),'sha256':sha(p)}for p in [BASE,PRIOR,PROCESS,WRITER]],
        'output_pins':[{'path':str(p),'sha256':sha(p)}for p in [ownerpath,viewpath]],
        'native_R_or_whole_original_A_admission_not_inferred_from_view_link':True,
        'training_started':False,'new_Teacher_Actor_calls':0,'curation_cost':'UNKNOWN_NOT_ZERO','script_sha256':sha(__file__)}
    dump(DEST/'FINAL_COVERAGE_RECONCILIATION.json',report);print(js({k:report[k]for k in ['owners','current_views','native_owners_with_current_scoped_views','views_without_any_owner_link']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--main',type=Path,required=True);parser.add_argument('--expected-main-sha256',required=True)
    main(parser.parse_args())
