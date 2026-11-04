"""Prepare an explicit public/controlled derivative before CPU compilation.

No archived code, agent, model weights or training are executed. Original
sources remain read-only. All content passes the same frozen privacy mapping.
"""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import time

from audit_structure import rows, target_checks
from privacy import Sanitizer
from publication_gate import assess, preassess


def compact(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()


class Output:
    def __init__(self,root):self.root=root;self.handles={};self.counts=Counter()
    def write(self,name,value):
        if name not in self.handles:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
            self.handles[name]=gzip.open(p,'wt',encoding='utf-8',newline='\n',compresslevel=3)
        self.handles[name].write(compact(value)+'\n');self.counts[name]+=1
    def close(self):
        for f in self.handles.values():f.close()


def input_streams(a):
    yield 'actions',a.bundle/'datasets/native_actions_core7.train.jsonl.gz'
    yield 'labels',a.work_labels/'terminal_candidates.core7.jsonl.gz'
    # Full frozen native histories and provenance remain evidence-only. Their
    # tool failures and non-core calls must not disappear behind the SFT filter.
    yield 'canonical_native_episodes',a.bundle/'canonical/native_episodes.jsonl.gz'
    for name in ('episodes','jobs','routes','source_materials'):
        yield 'catalog_'+name,a.bundle/('catalog/'+name+'.jsonl')
    yield 'terminal_noncore_quarantine',a.work_labels/'terminal_candidates.quarantine.jsonl.gz'
    for name in ['screen_write_decisions.jsonl','screen_artifact_decisions.jsonl','screen_artifact_routes.jsonl','screen_artifacts_index.jsonl','terminal_audit.jsonl']:
        yield 'audit_'+name.removesuffix('.jsonl'),a.work_labels/name
    if a.support:
        yield 'support',a.support/'support.text.jsonl.gz'
        yield 'support_inventory',a.support/'support.manifest.jsonl.gz'
        yield 'archive_members_inventory',a.support/'archive_members.manifest.jsonl.gz'


def review_map(directory):
    initial={};secondary={}
    for name in ('screen_reviews.jsonl','make_a_reviews.jsonl','make_b_reviews.jsonl','screen_terminal_reviews.jsonl','make_terminal_reviews.jsonl'):
        p=directory/name
        if p.exists():
            for row in rows(p):
                if row['id'] in initial:raise ValueError('duplicate primary review id')
                initial[row['id']]=row
    for name in ('screen_second_reviews.jsonl','make_a_second_reviews.jsonl','make_b_second_reviews.jsonl'):
        p=directory/name
        if p.exists():
            for row in rows(p):secondary[row['id']]=row
    final={}
    for identifier,first in initial.items():
        second=secondary.get(identifier)
        decision=first['decision']
        if second:
            # This default is conservative, not adjudication of every dispute.
            if 'reject' in (decision,second['decision']):decision='reject'
            elif decision!=second['decision']:decision='needs_context'
        final[identifier]={'id':identifier,'decision':decision,'first_review':first,
                           'second_review':second,'human_gold':False,
                           'scope':'AI local-evidence review; disagreement not silently approved'}
    overrides=directory/'adjudication.jsonl'
    if overrides.exists():
        for override in rows(overrides):
            if override['id'] not in final:raise ValueError('adjudication without initial review')
            final[override['id']]['decision']=override['decision']
            final[override['id']]['adjudication']=override
    return final


def prepare(a):
    started=time.monotonic();a.output.mkdir(parents=True,exist_ok=True)
    streams=list(input_streams(a))
    for _,path in streams:
        if not path.is_file():raise ValueError('required input not ready: '+path.name)
    fingerprints={str(p):sha(p) for _,p in streams}
    sanitizer=Sanitizer(a.output/'local_restricted',pseudonymize_source_ids=True)
    counts=Counter();out=Output(a.output);audit={r['id']:r for r in rows(a.structure/'structure_audit.jsonl')}
    preheld={}
    # Learn names/values across all representations before writing any output.
    for kind,path in streams:
        for position,row in enumerate(rows(path)):
            gate=preassess(row)
            if gate['status']=='hold_for_review':preheld[(kind,position)]=gate
            # Large uncertain cell tables stay in the controlled work source.
            # Discover their metadata but do not duplicate their unreviewed body.
            value={k:v for k,v in row.items() if k!='content'} if kind=='support' and (kind,position) in preheld else row
            sanitizer.discover(value);counts['discovered:'+kind]+=1
        print(json.dumps({'stage':'privacy_discovery','kind':kind,'rows':counts['discovered:'+kind],
                          'elapsed_seconds':round(time.monotonic()-started,1)}),flush=True)
    sanitizer.freeze()
    # Reviews may be completed in parallel with read-only discovery, but are
    # frozen before any eligibility decision is written.
    reviews=review_map(a.reviews)
    for kind,path in streams:
        for position,raw in enumerate(rows(path)):
            pre_gate=preheld.get((kind,position))
            value={k:v for k,v in raw.items() if k!='content'} if kind=='support' and pre_gate else raw
            clean=sanitizer.clean_row(value)
            gate=pre_gate or assess(clean)
            clean['privacy_review']['table_publication_gate']=gate
            if gate['status']=='hold_for_review':
                clean['privacy_review']['status']='hold_for_review'
                clean['privacy_review']['risk_flags']=sorted(set(clean['privacy_review']['risk_flags']+gate['risk_flags']))
                counts['table_gate_hold:'+kind]+=1
                if kind=='support':
                    clean['content_withheld_in_controlled_work_source']=True
            public=clean['privacy_review']['status']=='known_pattern_scan_clear'
            if 'requires_publication_privacy_review' in clean:
                clean['source_record_requested_publication_privacy_review']=clean['requires_publication_privacy_review']
                clean['requires_publication_privacy_review']=not public
            if kind in ('actions','labels'):
                check=audit.get(raw['id'],{'errors':['missing_structure_audit'],'warnings':[]})
                errors,warnings=target_checks(clean)
                errors=sorted(set(check['errors']+errors))
                warnings=sorted(set(check['warnings']+warnings))
                review=reviews.get(raw['id'])
                if review:
                    valid_hashes={hashlib.sha256(json.dumps(raw['completion'],ensure_ascii=False,sort_keys=sort,
                                  **({'separators':(',',':')} if tight else {})).encode('utf-8')).hexdigest()
                                  for sort in (False,True) for tight in (False,True)}
                    bound=[review['first_review'],review.get('second_review'),review.get('adjudication')]
                    if any(r and r.get('target_sha256') not in valid_hashes for r in bound):
                        errors=sorted(set(errors+['ai_review_target_sha_mismatch']))
                clean['publication_approved']=public
                clean['training_eligible']=bool(public and not errors and review and review['decision']=='pass')
                clean['semantic_review']=review['decision'] if review else 'not_ai_semantically_reviewed'
                clean['evidence_grade']='ai_local_evidence_reviewed_silver' if clean['training_eligible'] else 'candidate_not_admitted'
                clean['preflight_structure']={'errors':errors,'warnings':warnings,'source_structure_record_checked':raw['id'] in audit}
                clean['privacy_transformed']=True
                clean['context_is_actual_past_prefix']=False
                clean['context_relationship']='same historical message/target positions with explicit privacy transformations, no future information added'
                clean['original_candidate_position_preserved']=True
                clean['human_gold']=False
                out.write('local_clean_inputs/candidates.'+kind+'.jsonl.gz',clean)
                counts['rows:'+kind]+=1;counts['public:'+kind]+=int(public);counts['eligible:'+kind]+=int(clean['training_eligible'])
                if public:out.write('public/data/candidates.'+kind+'.jsonl.gz',clean)
                else:
                    out.write('local_restricted/held.'+kind+'.jsonl.gz',clean)
                    out.write('public/audit/publication_holds.jsonl.gz',{'id':clean['id'],'kind':clean['kind'],'target_kind':clean.get('target_kind'),
                                  'privacy_flags':clean['privacy_review']['risk_flags'],'publication_approved':False,'training_eligible':False,
                                  'original_retained_locally':True})
                out.write('public/audit/eligibility.jsonl.gz',{'id':clean['id'],'kind':clean['kind'],'target_kind':clean.get('target_kind'),
                             'publication_approved':public,'training_eligible':clean['training_eligible'],'semantic_review':clean['semantic_review'],
                             'structural_errors':errors,'structural_warnings':warnings,'human_gold':False})
            else:
                clean['publication_approved']=public
                clean['training_eligible']=False
                clean['training_use']='support_evidence_only_not_primary_targets'
                counts['rows:'+kind]+=1;counts['public:'+kind]+=int(public)
                if public:out.write('public/support/'+kind+'.jsonl.gz',clean)
                else:
                    out.write('local_restricted/held.'+kind+'.jsonl.gz',clean)
                    out.write('public/audit/support_holds.jsonl.gz',{'support_id':clean.get('support_id'),
                         'kind':kind,'source_sha256':clean.get('source_sha256'),'privacy_flags':clean['privacy_review']['risk_flags'],
                         'publication_approved':False,'original_retained_locally':True})
            if sum(v for k,v in counts.items() if k.startswith('rows:'))%250==0:
                print(json.dumps({'stage':'privacy_transform','counts':dict(counts),'elapsed_seconds':round(time.monotonic()-started,1)}),flush=True)
    for review in reviews.values():out.write('public/audit/semantic_reviews.jsonl.gz',sanitizer.clean_value(review))
    out.close();sanitizer.save_private_mapping()
    for _,path in streams:
        if sha(path)!=fingerprints[str(path)]:raise ValueError('source input changed during preparation')
    report={'schema_version':'wrd-public-preparation-v1','status':'COMPLETE_WITH_EXPLICIT_HOLDS','counts':dict(counts),
            'written_rows':dict(out.counts),'privacy':sanitizer.report(),
            'ai_reviewed_targets':len(reviews),'ai_adjudicated_decisions':dict(Counter(r['decision'] for r in reviews.values())),
            'unreviewed_targets_not_training_eligible':True,'human_gold':0,'no_future_context_added':True,
            'original_input_hashes_checked_unchanged':True,'training_started':False,
            'scope':'Controlled original and cleaned candidates kept locally; only known-pattern-clear derived contents and aggregate hold manifests prepared for publication.',
            'elapsed_seconds':round(time.monotonic()-started,3)}
    (a.output/'work_preparation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    p=a.output/'public/reports/preparation.json';p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'counts':report['counts'],'training_started':False,'elapsed_seconds':report['elapsed_seconds']}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--work-labels',type=Path,required=True);p.add_argument('--structure',type=Path,required=True);p.add_argument('--reviews',type=Path,required=True);p.add_argument('--support',type=Path);p.add_argument('--output',type=Path,required=True)
    prepare(p.parse_args())
