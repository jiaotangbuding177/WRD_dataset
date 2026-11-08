"""Read-only inventory of the historical corpus and its currently projected inputs.

Writes only into this script's own inventory directory; never imports or starts
the active native/author runtimes. Source text is not echoed to stdout.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "output/20261107_official_baselines_1107/data"


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    started = time.time()
    indices = json.loads((BASE / "SOURCE_INDEX.json").read_text(encoding="utf-8"))
    assert len(indices) == 1107 and len({r['source_id'] for r in indices}) == 1107
    resources_by_path = {}
    cases, problems = [], []
    category, splits, synthetic, provenance, roots = [Counter() for _ in range(5)]
    for index in indices:
        case_path = BASE / "cases" / (index['id'] + ".json")
        raw = case_path.read_bytes()
        case = json.loads(raw)
        assert case['id'] == index['id']
        followups = case['actor'].get('followup_inputs', [])
        category[case['task_type']] += 1
        splits[index['legacy_split']] += 1
        rows = []
        for r in case.get('resources', []):
            p = Path(r['path'])
            item = {k: r.get(k) for k in ['path','mount','sha256','user_index','synthetic','provenance','original_attachment_bytes_restored','resource_kind','resource_id']}
            rows.append(item)
            if r['path'] not in resources_by_path:
                resources_by_path[r['path']] = {'path':r['path'],'expected_sha256':r['sha256'],'case_occurrences':0,'source_ids':[]}
            entry = resources_by_path[r['path']]
            entry['case_occurrences'] += 1
            entry['source_ids'].append(index['source_id'])
            if entry['expected_sha256'] != r['sha256']:
                problems.append({'kind':'conflicting_resource_sha','path':r['path'],'source_id':index['source_id']})
            if not isinstance(r.get('user_index'),int) or r['user_index'] < 0 or r['user_index'] > len(followups):
                problems.append({'kind':'invalid_dispatch_index','source_id':index['source_id'],'resource':item})
            mount = str(r.get('mount','')).replace('\\','/')
            if not mount or mount.startswith('/') or '..' in mount.split('/') or ':' in mount.split('/')[0]:
                problems.append({'kind':'unsafe_mount','source_id':index['source_id'],'mount':mount})
            synthetic[str(r.get('synthetic'))] += 1
            provenance[str(r.get('provenance'))] += 1
            try:
                rel = p.relative_to(ROOT).as_posix()
                if '/resources/' in rel: prefix = rel.split('/resources/',1)[0]+'/resources/'+rel.split('/resources/',1)[1].split('/')[0]
                elif '/recovery/' in rel: prefix = rel.split('/recovery/',1)[0]+'/recovery/'+rel.split('/recovery/',1)[1].split('/')[0]
                else: prefix = '/'.join(rel.split('/')[:4])
            except ValueError: prefix = 'OUTSIDE_WORKSPACE'
            roots[prefix] += 1
        source_path=Path(index['original_audit_copy'])
        source_raw=source_path.read_bytes() if source_path.is_file() else None
        source_sha=hashlib.sha256(source_raw).hexdigest() if source_raw is not None else None
        if source_raw is None or source_sha != index['original_audit_copy_sha256']:
            problems.append({'kind':'source_missing_or_hash_changed','source_id':index['source_id'],'path':str(source_path),'expected':index['original_audit_copy_sha256'],'actual':source_sha})
        source = json.loads(source_raw) if source_raw else {}
        message_count = len(source.get('messages',[])) if isinstance(source,dict) else None
        cases.append({'source_id':index['source_id'],'case_id':case['id'],'component_id':index['component_id'],
                      'legacy_split':index['legacy_split'],'category':case['task_type'],
                      'case_path':str(case_path),'case_sha256':hashlib.sha256(raw).hexdigest(),'case_bytes':len(raw),
                      'original_source_path':str(source_path),'original_source_expected_sha256':index['original_audit_copy_sha256'],
                      'original_source_actual_sha256':source_sha,'original_source_bytes':len(source_raw) if source_raw else 0,
                      'original_source_message_count':message_count,'human_dispatch_count':1+len(followups),
                      'resource_occurrences':len(rows),'initial_resource_occurrences':sum(r['user_index']==0 for r in rows),
                      'later_resource_occurrences':sum(r['user_index']>0 for r in rows),
                      'resources':rows,'qualification':case.get('qualification',{})})
    files=[]
    for n, item in enumerate(resources_by_path.values(),1):
        p=Path(item['path']);exists=p.is_file();actual=sha_file(p) if exists else None
        row={**item,'source_ids':sorted(set(item['source_ids'])),'exists':exists,'bytes':p.stat().st_size if exists else None,
             'actual_sha256':actual,'sha_match':actual==item['expected_sha256']}
        files.append(row)
        if not exists or not row['sha_match']:problems.append({'kind':'resource_missing_or_hash_changed','path':str(p),'expected':item['expected_sha256'],'actual':actual})
    changed_cases=[]
    for c in cases:
        if sha_file(Path(c['case_path'])) != c['case_sha256']:changed_cases.append(c['source_id'])
    unique_content={f['actual_sha256']:f['bytes'] for f in files if f['actual_sha256']}
    summary={'schema':'wrd58-full-evolution-physical-inventory-v1','model_calls':0,'source_count':len(cases),
             'component_count':len({c['component_id'] for c in cases}),'legacy_split_counts':dict(splits),
             'category_counts':dict(category),'human_dispatch_count':sum(c['human_dispatch_count'] for c in cases),
             'case_json_bytes':sum(c['case_bytes'] for c in cases),'source_json_bytes':sum(c['original_source_bytes'] for c in cases),
             'source_messages':sum(c['original_source_message_count'] or 0 for c in cases),
             'resource_occurrences':sum(c['resource_occurrences'] for c in cases),
             'initial_resource_occurrences':sum(c['initial_resource_occurrences'] for c in cases),
             'later_resource_occurrences':sum(c['later_resource_occurrences'] for c in cases),
             'unique_resource_paths':len(files),'unique_resource_content_sha256':len(unique_content),
             'resource_bytes_by_path':sum(f['bytes'] or 0 for f in files),'resource_bytes_content_dedup':sum(unique_content.values()),
             'synthetic_occurrence_counts':dict(synthetic),'provenance_occurrence_counts':dict(provenance),
             'resource_root_occurrence_counts':dict(roots),'problems':problems,'case_changed_during_inventory':changed_cases,
             'source_index_path':str(BASE/'SOURCE_INDEX.json'),'source_index_sha256':sha_file(BASE/'SOURCE_INDEX.json'),
             'elapsed_seconds':time.time()-started,'qualification':'Physical/hash inventory only; does not certify semantic suitability, original bytes, or task success. Legacy evaluation boundaries retained; official all-train role not inherited.'}
    dump('INVENTORY_SUMMARY.json',summary)
    dump('INVENTORY_CASES.json',cases)
    dump('INVENTORY_FILES.json',files)
    print(json.dumps({k:v for k,v in summary.items() if k not in ['problems','provenance_occurrence_counts']},ensure_ascii=False,indent=2))
    print('PROBLEMS',len(problems))


if __name__ == '__main__':main()
