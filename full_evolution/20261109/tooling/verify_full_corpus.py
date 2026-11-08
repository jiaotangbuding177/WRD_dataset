"""Cold CPU verification of an already materialized corpus, no model imports."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3]
CORPUS=ROOT/'output/20261108_wrd58_full_evolution/package/corpus'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main():
    errors=[];declared={}
    for line in (CORPUS/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        expected,rel=line.split('  ',1)
        if rel in declared:errors.append('duplicate manifest path '+rel)
        p=CORPUS/rel
        if not p.is_file():errors.append('missing '+rel);continue
        if digest(p)!=expected:errors.append('sha '+rel)
        declared[rel]=expected
    actual={p.relative_to(CORPUS).as_posix() for p in CORPUS.rglob('*') if p.is_file() and p.name!='SHA256SUMS'}
    if actual!=set(declared):errors.append('manifest membership difference')
    rows=[json.loads(l) for l in (CORPUS/'INDEX.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows)==1107 and len({r['source_id'] for r in rows})==1107
    freeze_path=CORPUS/'EFFECT_FREEZE12.json';freeze=json.loads(freeze_path.read_text(encoding='utf-8'))
    freeze_sha=digest(freeze_path)
    if 'semantic_review' in freeze:
        sr=freeze['semantic_review']
        if declared.get(sr['path'])!=sr['sha256']:errors.append('semantic review pin')
        if freeze['evaluation_targets']['skill_delivery_denominator']!=10 or freeze['evaluation_targets']['route_decision_denominator']!=12:errors.append('semantic denominators')
        if set(freeze['rejection_source_ids'])!={'conv_276e97b595fc','conv_34843d227bc0'}:errors.append('semantic STOP identity')
    message_roles=Counter();counts=Counter();ids=set();secret_candidates=[]
    strong_patterns=[('private_key',re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
                     ('github_pat',re.compile(rb'(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{40,})')),
                     ('openai_key',re.compile(rb'(?<![A-Za-z0-9])sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{35,}')),
                     ('aws_key',re.compile(rb'AKIA[0-9A-Z]{16}'))]
    for r in rows:
        sid=r['source_id'];ids.add(sid)
        saved=json.loads((CORPUS/'cases'/sid/'case.json').read_text(encoding='utf-8'))
        if saved!=r:errors.append('index/case mismatch '+sid)
        for field in ['source','raw_audit','prompt','delivery_index','replay']:
            pin=r[field];p=CORPUS/pin['path']
            if p.stat().st_size!=pin['bytes'] or declared.get(pin['path'])!=pin['sha256']:errors.append('pin '+sid+' '+field)
        source=json.loads((CORPUS/r['source']['path']).read_text(encoding='utf-8'))
        if source.get('session_id')!=sid:errors.append('source identity '+sid)
        for m in source.get('messages',[]):message_roles[str(m.get('role'))]+=1
        resource_index=json.loads((CORPUS/r['delivery_index']['path']).read_text(encoding='utf-8'))
        if resource_index['resources']!=r['resources']:errors.append('resource index '+sid)
        mounts=set()
        for q in r['resources']:
            if q['path']!='objects/'+q['sha256']:errors.append('object identity '+sid)
            if q['mount'] in mounts:errors.append('mount collision '+sid)
            mounts.add(q['mount'])
            if declared.get(q['path'])!=q['sha256']:errors.append('resource pin '+sid)
            counts['resources']+=1
            counts['later']+=q['user_index']>0
        e=r['student_eligibility']
        if r['original_split']=='evaluation' and (not e['original_eval226'] or e['sft_admission']):errors.append('protected split '+sid)
        if e['effect_evaluation_allowed']:
            explicit57=e['student_split57'] in ['dev','test'] and e['recorded_candidate_safe']
            newfreeze=e.get('effect_split')=='EFFECT_EVAL' and e.get('new_freeze',{}).get('path')=='EFFECT_FREEZE12.json' and e['recorded_candidate_safe']
            if not (explicit57 or newfreeze):errors.append('unsafe evaluation '+sid)
            if newfreeze and e['new_freeze']['sha256']!=freeze_sha:errors.append('new freeze pin '+sid)
        if any(q['path'].startswith('evaluator_only/') for q in r['resources']):errors.append('evaluator leakage '+sid)
    # Detect only strong credential signatures; save paths/rules, never values.
    # Binary resources are included because credential archives must not be
    # silently declared absent merely based on a filename extension.
    for rel in sorted(actual):
        if rel.startswith('objects/') or rel.endswith('.json') or rel.endswith('.jsonl'):
            p=CORPUS/rel
            raw=p.read_bytes()
            for name,pattern in strong_patterns:
                if pattern.search(raw):secret_candidates.append({'path':rel,'rule':name})
    report={'schema':'wrd58-full-corpus-cold-verification-v1','status':'PASS' if not errors else 'FAIL',
            'source_count':len(rows),'hash_verified_members':len(declared),'resource_occurrences':counts['resources'],
            'later_resource_occurrences':counts['later'],'source_message_roles':dict(message_roles),
            'original_eval226_count':sum(r['original_split']=='evaluation' for r in rows),
            'effect_evaluation_allowed_count':sum(r['student_eligibility']['effect_evaluation_allowed'] for r in rows),
            'errors':errors,'strong_secret_signature_candidates':secret_candidates,
            'secret_scan_qualification':'Strong signature scan is not universal secret absence certification; values never emitted.',
            'new_model_calls':0}
    p=Path(__file__).parent/'COLD_VERIFICATION.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
