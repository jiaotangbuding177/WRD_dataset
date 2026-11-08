"""Freeze twelve source-independent maker-effect cases without model outcomes.

This assigns evaluation use only. It never admits any source to SFT, changes
the old 57 split, or removes anything from the complete archive.
"""
from collections import Counter
from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
CORPUS=ROOT/'output/20261108_wrd58_full_evolution/package/corpus'
SEED='wrd58-effect-20261108:'
CATEGORIES=['office','legal','edu','hr','biz','data']
LEDGER=ROOT/'output/20261102_wrd_final_audit58_delivery/fresh_restore01/active58/ACTIVE_TARGET_LEDGER58.json'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    reg=CORPUS/'provenance'
    groups=load(reg/'SOURCE_GROUP_REBASE57.json')['all_groups']
    old_freeze=load(reg/'SPLIT_FREEZE57.json')['groups']
    rows=[json.loads(l) for l in (CORPUS/'INDEX.jsonl').read_text(encoding='utf-8').splitlines()]
    byid={r['source_id']:r for r in rows}
    # Rebuild the exact enterprise-only identity57 component names used by the
    # actual compiled 58 ledger, rather than treating a role label as evidence.
    identity_path=ROOT/'output/20261101_wrd_increment57/source_registry/RECORDED_IDENTITY_EDGES57.json'
    edges=load(identity_path)['edges'];parent={}
    def find(x):
        parent.setdefault(x,x)
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    for edge in edges:
        a,b=find(edge['a']),find(edge['b'])
        if a!=b:parent[max(a,b)]=min(a,b)
    components=defaultdict(list)
    for value in parent:
        if __import__('re').fullmatch(r'conv_[0-9a-f]{12}',value):components[find(value)].append(value)
    identity_by_source={s:'identity57_'+sha('|'.join(sorted(ids)).encode())[:20] for ids in components.values() for s in ids}
    active=load(LEDGER)['profiles']
    if {k:len(v) for k,v in active.items()}!={'budget_projection':1260,'full_native53':1260}:raise ValueError('Unexpected actual58 profiles')
    active_sources={s for profile in active.values() for row in profile for key in ['source_ids','enterprise_source_ids'] for s in row.get(key,[])}
    active_identities={s for profile in active.values() for row in profile for s in row.get('recorded_identity_source_components',[])}
    for src,dst in [(identity_path,reg/'RECORDED_IDENTITY_EDGES57.json'),(LEDGER,reg/'ACTIVE_TARGET_LEDGER58.json')]:
        if dst.exists() and sha(dst.read_bytes())!=sha(src.read_bytes()):raise ValueError('Different boundary evidence')
        if not dst.exists():dst.write_bytes(src.read_bytes())
    prior_role_ids={s for r in old_freeze for s in r['source_ids']}
    seen_ids={s for r in groups if r['new_to_full_train267'] is False for s in r['source_ids']}
    seen_ids|={s for r in old_freeze if r['role']=='TRAIN-MINING' for s in r['source_ids']}
    seen_components={byid[s]['component_id'] for s in seen_ids if s in byid}
    rejected=[];candidates={k:[] for k in CATEGORIES}
    for group in groups:
        reasons=[];sids=group['source_ids']
        if len(sids)!=1:reasons.append('NOT_SINGLE_SOURCE_RECORDED_GROUP')
        if group['candidate_eligible_on_recorded_identity_graph'] is not True:reasons.append('RECORDED_GRAPH_NOT_ELIGIBLE')
        if group['new_to_full_train267'] is not True:reasons.append('RECORDED_TRAIN_CLOSURE')
        if group.get('exclusion_reasons'):reasons+=['REGISTRY:'+x for x in group['exclusion_reasons']]
        if set(sids)&prior_role_ids:reasons.append('OLD_24_FROZEN_SOURCE_ROLE')
        if set(sids)&active_sources:reasons.append('ACTUAL_ACTIVE58_DIRECT_SOURCE_INTERSECTION')
        if any(identity_by_source.get(s) in active_identities for s in sids):reasons.append('ACTUAL_ACTIVE58_RECORDED_IDENTITY_INTERSECTION')
        if any(s not in identity_by_source for s in sids):reasons.append('UNRESOLVED_EXACT_IDENTITY57_COMPONENT')
        if any(s not in byid for s in sids):reasons.append('NOT_IN_FULL_CORPUS')
        if any(s in byid and byid[s]['component_id'] in seen_components for s in sids):reasons.append('ORIGINAL_COMPONENT_INTERSECTS_SEEN_TRAIN_CLOSURE')
        for sid in sids:
            if sid not in byid:continue
            row=byid[sid]
            for pin in [row['source'],row['delivery_index'],*row['resources']]:
                p=CORPUS/pin['path']
                if not p.is_file() or p.stat().st_size!=pin['bytes']:
                    reasons.append('DECLARED_MATERIAL_NOT_PHYSICALLY_READY');break
        if reasons:
            rejected.append({'group_id':group['group_id'],'source_ids':sids,'reasons':sorted(set(reasons))});continue
        sid=sids[0];row=byid[sid];cat=row['category']
        if cat in candidates:
            candidates[cat].append({'source_id':sid,'component57':group['group_id'],'component_id':row['component_id'],
                                    'identity_component57':identity_by_source[sid],
                                    'category':cat,'selection_hash':sha((SEED+sid).encode()),
                                    'case_path':'cases/'+sid+'/case.json','source_sha256':row['source']['sha256'],
                                    'resources':len(row['resources']),'material_bytes':sum(r['bytes'] for r in row['resources'])})
    for v in candidates.values():v.sort(key=lambda x:x['selection_hash'])
    selected=[];used_groups=set();used_components=set()
    for slot in range(2):
        for cat in CATEGORIES:
            chosen=None
            for c in candidates[cat]:
                if c['component57'] in used_groups or c['component_id'] in used_components:continue
                chosen=c;break
            if chosen is None:raise ValueError('Not enough distinct ready components for '+cat)
            selected.append({**chosen,'execution_order':len(selected)+1})
            used_groups.add(chosen['component57']);used_components.add(chosen['component_id'])
    assert len(selected)==12 and len(used_components)==12
    freeze={'schema':'wrd58-new-maker-effect-evaluation-freeze12-v1','freeze_id':'EFFECT_EVAL_20261108_12',
            'model_calls':0,'training_admissions':0,'source_count':12,'categories':dict(Counter(x['category'] for x in selected)),
            'selection_rule':{'seed_prefix':SEED,'sort':'SHA256(seed_prefix + source_id), ascending within category',
                              'category_order':CATEGORIES,'per_category':2,'execution_order':'category round-robin, two passes',
                              'required':['single-source recorded group','recorded graph eligible','new_to_full_train267',
                                          'no recorded exclusion reasons','not in old24 frozen source roles',
                                          'no original component shared with recorded seen TRAIN closure','all declared material files exist'],
                              'no_model_outcome_selection':True,'source_and_recorded_components_unique':True},
            'seen_train_closure_source_count':len(seen_ids),'seen_train_original_component_count':len(seen_components),
            'actual_active58_boundary':{'ledger':'provenance/ACTIVE_TARGET_LEDGER58.json','ledger_sha256':sha(LEDGER.read_bytes()),
                                       'profile_target_counts':{k:len(v) for k,v in active.items()},
                                       'unique_direct_source_ids':len(active_sources),'unique_recorded_identity_components':len(active_identities),
                                       'selected_direct_source_intersections':[],
                                       'selected_recorded_identity_intersections':[]},
            'old24_roles_excluded':sorted(prior_role_ids),
            'candidate_counts_before_distinct_component_selection':{k:len(v) for k,v in candidates.items()},
            'selected':selected,'rejected_recorded_groups':rejected,
            'boundary_policy':'EFFECT_EVAL_ONLY_NEVER_SFT; original226 remains protected; old57 split untouched',
            'registry_pins':[{'path':'provenance/'+n,'sha256':sha((reg/n).read_bytes())} for n in ['SOURCE_GROUP_REBASE57.json','SPLIT_FREEZE57.json','RECORDED_IDENTITY_EDGES57.json','ACTIVE_TARGET_LEDGER58.json']]}
    save(CORPUS/'EFFECT_FREEZE12.json',freeze)
    fp={'path':'EFFECT_FREEZE12.json','sha256':sha((CORPUS/'EFFECT_FREEZE12.json').read_bytes()),'bytes':(CORPUS/'EFFECT_FREEZE12.json').stat().st_size}
    selected_ids={x['source_id'] for x in selected}
    for r in rows:
        e=r['student_eligibility'];sid=r['source_id']
        e['student_identity_component57']=identity_by_source.get(sid)
        e['actual_active58_source_intersection']=sid in active_sources
        e['actual_active58_identity_intersection']=identity_by_source.get(sid) in active_identities
        if e['actual_active58_source_intersection'] or e['actual_active58_identity_intersection']:
            e['effect_evaluation_allowed']=False
            e['reason']='ACTUAL_ACTIVE58_SOURCE_OR_RECORDED_IDENTITY_SEEN'
        if r['source_id'] not in selected_ids:continue
        e.update(effect_evaluation_allowed=True,reason='NEW_FROZEN_EFFECT12_RECORDED_TRAIN_COMPONENT_DISJOINT',
                 effect_split='EFFECT_EVAL',new_freeze=fp,sft_admission=False)
    for r in rows:save(CORPUS/'cases'/r['source_id']/'case.json',r)
    (CORPUS/'INDEX.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8',newline='\n')
    manifest=load(CORPUS/'MANIFEST.json')
    manifest['new_effect_eval_sources']=12
    manifest['effect_evaluation_allowed_sources']=sum(r['student_eligibility']['effect_evaluation_allowed'] for r in rows)
    manifest['effect_freeze']=fp
    save(CORPUS/'MANIFEST.json',manifest)
    files=sorted(p for p in CORPUS.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
    (CORPUS/'SHA256SUMS').write_text(''.join(sha(p.read_bytes())+'  '+p.relative_to(CORPUS).as_posix()+'\n' for p in files),encoding='utf-8',newline='\n')
    print(json.dumps({'freeze':fp,'selected':selected,'new_effect_count':12,'all_allowed':manifest['effect_evaluation_allowed_sources']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
