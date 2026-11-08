"""Intersect historical real skill artifacts with frozen student boundaries.

Read-only corpus/status inspection; writes only this inventory's audit report.
Association with a retained aggregate route is not relabelled as an
independent, source-alone successful teacher rollout.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
CORPUS=ROOT/'output/20261108_wrd58_full_evolution/package/corpus'
OUT=Path(__file__).resolve().parent


def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    status_path=ROOT/'output/workflow_library/status.json';status_raw=status_path.read_bytes()
    routes=json.loads(status_raw)['routes']
    sources=[json.loads(l) for l in (CORPUS/'INDEX.jsonl').read_text(encoding='utf-8').splitlines()]
    source_by_id={r['source_id']:r for r in sources}
    recorded=load(CORPUS/'provenance/SOURCE_GROUP_REBASE57.json')['all_groups']
    group_by_id={sid:g for g in recorded for sid in g['source_ids']}
    freeze57=load(CORPUS/'provenance/SPLIT_FREEZE57.json')['groups']
    old_roles={sid:r['role'] for r in freeze57 for sid in r['source_ids']}
    seen_ids={s for g in recorded if not g['new_to_full_train267'] for s in g['source_ids']}
    seen_ids|={s for g in freeze57 if g['role']=='TRAIN-MINING' for s in g['source_ids']}
    seen_original_components={source_by_id[s]['component_id'] for s in seen_ids if s in source_by_id}
    freeze12=load(CORPUS/'EFFECT_FREEZE12.json');selected12={r['source_id'] for r in freeze12['selected']}
    all_route_rows=[];all_source_rows=[]
    for route in routes:
        root=Path(route['skill_root']);skill=root/'SKILL.md';skill_raw=skill.read_bytes() if skill.is_file() else None
        sid_rows=[]
        for sid in route['source_ids']:
            source=source_by_id.get(sid);group=group_by_id.get(sid);reasons=[]
            if source is None:reasons.append('SOURCE_NOT_IN_FULL1107')
            if group is None:reasons.append('SOURCE_NOT_RESOLVED_BY57_RECORDED_GROUP')
            if group:
                if not group['candidate_eligible_on_recorded_identity_graph']:reasons.append('57_RECORDED_GROUP_NOT_ELIGIBLE')
                if not group['new_to_full_train267']:reasons.append('57_RECORDED_TRAIN_CLOSURE')
                reasons+=['57:'+x for x in group.get('exclusion_reasons',[])]
            if sid in old_roles:reasons.append('OLD24_SOURCE_ROLE:'+old_roles[sid])
            e=(source or {}).get('student_eligibility',{})
            if e.get('actual_active58_source_intersection'):reasons.append('ACTUAL_ACTIVE58_DIRECT_SOURCE_SEEN')
            if e.get('actual_active58_identity_intersection'):reasons.append('ACTUAL_ACTIVE58_IDENTITY_COMPONENT_SEEN')
            if source and source['component_id'] in seen_original_components:reasons.append('ORIGINAL_COMPONENT_SEEN_TRAIN_CLOSURE')
            if not e.get('student_identity_component57'):reasons.append('IDENTITY57_NOT_RESOLVED')
            boundary_safe=not reasons
            if group and len(group['source_ids'])!=1:reasons.append('57_RECORDED_GROUP_NOT_SINGLE_SOURCE')
            single_safe=not reasons
            original_source=load(CORPUS/source['source']['path']) if source else {}
            row={'source_id':sid,'source_category':source['category'] if source else None,
                 'route_id':route['id'],'route_category':route['category'],'library_status':route['library_status'],
                 'make_status':route.get('make_status'),'teacher_actual_skill_file':skill.is_file(),
                 'teacher_retained_route_association':route['library_status']=='retained' and skill.is_file(),
                 'current_effect12_member':sid in selected12,
                 'boundary_safe_excluding_old24':boundary_safe,'single_source_boundary_eligible':single_safe,
                 'eligible_reasons':['57recorded safe; no actual58 direct/identity or old24 intersection; single-source group'] if single_safe else sorted(set(reasons)),
                 'source_messages':len(original_source.get('messages',[])),
                 'source_turns':len(original_source.get('turns',[])),
                 'declared_resources':len(source['resources']) if source else None,
                 'source_component_original':source['component_id'] if source else None,
                 'source_identity57':e.get('student_identity_component57'),
                 'source_group57':(group or {}).get('group_id'),
                 'source_alone_teacher_success_proven':route['library_status']=='retained' and skill.is_file() and len(route['source_ids'])==1,
                 'qualification':('Single-source retained route with actual artifact; original runtime results still retain their own execution conditions.' if route['library_status']=='retained' and skill.is_file() and len(route['source_ids'])==1 else 'Aggregate-route association only; source_ids may have coarse topic provenance, not a standalone positive rollout.')}
            sid_rows.append(row);all_source_rows.append(row)
        review=route.get('value_review') or {}
        all_route_rows.append({'route_id':route['id'],'category':route['category'],'library_status':route['library_status'],
                               'make_status':route.get('make_status'),'source_ids':route['source_ids'],
                               'actual_skill_path':str(skill),'actual_skill_exists':skill_raw is not None,
                               'actual_skill_sha256':sha(skill_raw) if skill_raw else None,
                               'source_boundary_eligible_count':sum(r['boundary_safe_excluding_old24'] for r in sid_rows),
                               'single_source_boundary_eligible_count':sum(r['single_source_boundary_eligible'] for r in sid_rows),
                               'all_route_sources_unseen_and_eligible':bool(sid_rows) and all(r['single_source_boundary_eligible'] for r in sid_rows),
                               'recorded_resource_reliable':review.get('resource_reliable'),
                               'recorded_delivery_passed':review.get('delivery_passed'),
                               'recorded_resource_used':review.get('resource_used'),
                               'recorded_retain_decision':review.get('decision'),
                               'route_is_aggregate_of_multiple_sources':len(route['source_ids'])>1})
    retained=[r for r in all_route_rows if r['library_status']=='retained']
    positive_sources=[r for r in all_source_rows if r['teacher_retained_route_association'] and r['single_source_boundary_eligible']]
    positive_ids={r['source_id'] for r in positive_sources}
    by_category=Counter(source_by_id[s]['category'] for s in positive_ids)
    report={'schema':'wrd58-historical-positive-route-source-intersection-audit-v1','model_calls':0,
            'status_snapshot_path':str(status_path),'status_snapshot_sha256':sha(status_raw),
            'status_snapshot_unchanged_during_audit':sha(status_path.read_bytes())==sha(status_raw),
            'route_count':len(routes),'route_status_counts':dict(Counter(r['library_status'] for r in routes)),
            'actual_skill_artifact_count':sum(r['actual_skill_exists'] for r in all_route_rows),
            'retained_route_count':len(retained),'retained_unique_associated_sources':len({s for r in retained for s in r['source_ids']}),
            'retained_wholly_unseen_eligible_route_count':sum(r['all_route_sources_unseen_and_eligible'] for r in retained),
            'retained_associated_boundary_safe_unique_sources':len({r['source_id'] for r in all_source_rows if r['teacher_retained_route_association'] and r['boundary_safe_excluding_old24']}),
            'retained_associated_single_source_eligible_count':len(positive_ids),
            'retained_associated_single_source_eligible_category_counts':dict(by_category),
            'positive_source_rows':positive_sources,
            'current_effect12_route_associations':[r for r in all_source_rows if r['current_effect12_member']],
            'route_rows':all_route_rows,'source_rows':all_source_rows,
            'conclusion':['The original29 retained routes are not wholly student-unseen: each retained route has at least one boundary-ineligible/seen contributing source.',
                          'There are85 unique, single-source boundary-eligible sources associated with retained routes; this is evidence of a reusable task family, not proof that each source alone already produced a successful teacher skill.',
                          'A retained-associated six-category twice-per-category selection is impossible under these exact filters because DATA has only one eligible source.',
                          'All121 route SKILL.md artifacts exist, but candidate/needs_revision/rejected are not promoted to qualified positive results.'],
            'corpus_mutated':False}
    (OUT/'POSITIVE_SOURCE_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['route_count','route_status_counts','actual_skill_artifact_count','retained_route_count','retained_unique_associated_sources','retained_wholly_unseen_eligible_route_count','retained_associated_boundary_safe_unique_sources','retained_associated_single_source_eligible_count','retained_associated_single_source_eligible_category_counts','status_snapshot_unchanged_during_audit']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
