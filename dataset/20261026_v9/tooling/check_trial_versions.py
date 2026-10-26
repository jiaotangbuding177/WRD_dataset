"""Independent static check of Actor/producer/reviewer package identity.

Uses original file_index and requests, not the candidate-tree field produced by
the outcome compiler. No generated skill code, Agent, or model is executed.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / 'output/20261025_wrd_training_dataset/bundle'
OUT = ROOT / 'output/20261026_wrd_dataset_v9/outcomes'
CASES = [
    ('document-error-review', 'ep_5d7dbe9ad965b4cde4f8', 'ep_c5db87aa2f39b9ea55c4', 'ep_32d76c94c6293f394738', True),
    ('org-chart-design', 'ep_a50c8ed4c9d44fe2ac21', 'ep_00c5bf5d24a489a4ed4c', 'ep_6a1b2be331796755f3e5', True),
    ('jd-resume-screening', 'ep_0242f66686e468bf4356', 'ep_af4664e359ed5b62d785', 'ep_8eeac16c28117684f2b6', True),
    ('paper-drafting', 'ep_095732d8b3f3215f58b2', 'ep_75d2d0280bd278319519', 'ep_dce1e051866bfeccebdd', False),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def js(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def tree(value):
    return sha(js(sorted(value.items())).encode())


def rows(path):
    op = gzip.open if str(path).endswith('.gz') else open
    with op(path, 'rt', encoding='utf-8-sig') as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def main():
    index = {}
    candidate = defaultdict(dict)
    for entry in rows(BUNDLE / 'archive/file_index.jsonl'):
        bits = entry['logical_path'].split('/', 2)
        if len(bits) != 3 or bits[0] != 'episodes':
            continue
        eid, rel = bits[1:]
        if rel.startswith('workspace/inputs/candidate/'):
            candidate[eid][rel.removeprefix('workspace/inputs/candidate/')] = entry
        if eid in {x for c in CASES for x in c[1:4]}:
            index[(eid, rel)] = entry
    versions = list(rows(ROOT / 'output/20261026_wrd_raw_census_v7/indexes/skill_version_trees.all.jsonl.gz'))
    actual_input_root_types = defaultdict(int)
    for value in versions:
        if '/workspace/inputs/' in value['output_skill_root_logical_path']:
            actual_input_root_types[value['output_skill_root_logical_path'].split('/workspace/inputs/', 1)[1].split('/')[0]] += 1

    def read(entry):
        p = BUNDLE / 'archive' / entry['object']
        raw = p.read_bytes()
        assert sha(raw) == entry['sha256']
        return raw

    observations = []
    for route, reviewer, actor, producer, retained in CASES:
        req_entry = index[(actor, 'request.json')]
        req = json.loads(read(req_entry).decode('utf-8-sig'))
        skills = [s for s in req.get('learned_skills', []) if s.get('id') == route]
        assert len(skills) == 1
        skill = skills[0]
        actor_map = skill['files']
        candidate_files = candidate[reviewer]
        candidate_map = {k: f.get('source_sha256', f['sha256']) for k, f in candidate_files.items()}
        assert actor_map == candidate_map, route
        produced = [v for v in versions if v['episode_id'] == producer and v['output_skill_root_logical_path'].startswith('episodes/' + producer + '/workspace/outputs/')]
        matches = [v for v in produced if {f['relative_path']: f['sha256'] for f in v['files']} == actor_map]
        assert len(matches) == 1, route
        produced_files = {f['relative_path']: f for f in matches[0]['files']}
        file_checks = []
        for name, expected in sorted(actor_map.items()):
            cf = candidate_files[name]
            producer_raw = Path(produced_files[name]['physical_frozen_CAS_path']).read_bytes()
            candidate_raw = read(cf)
            assert sha(producer_raw) == expected == sha(candidate_raw)
            assert producer_raw == candidate_raw
            source_path = Path(cf['source_path'])
            assert source_path.is_file() and sha(source_path.read_bytes()) == expected
            file_checks.append({'relative_path': name, 'sha256': expected, 'bytes': len(producer_raw),
                'review_candidate_logical_path': cf['logical_path'],
                'candidate_original_path_rehashed': str(source_path),
                'producer_original_path': produced_files[name]['physical_original_path'],
                'producer_frozen_path': produced_files[name]['physical_frozen_CAS_path'],
                'original_candidate_and_producer_frozen_bytes_equal': True})
        review_entry = index[(reviewer, 'workspace/outputs/review.json')]
        review = json.loads(read(review_entry).decode('utf-8-sig'))
        if retained:
            assert review['decision'] == 'retain'
        observations.append({'route_id': route, 'reviewer_episode_id': reviewer, 'actor_episode_id': actor,
            'producer_episode_id': producer, 'historical_review_decision': review['decision'],
            'tree_content_sha256': tree(actor_map), 'files_checked': file_checks,
            'complete_actor_request_map_equals_review_candidate_map_equals_producer_map': True,
            'not_an_independent_quality_or_positive_loss_certification': True})
    result = {'schema_version': 'wrd-v9-independent-trial-version-identity-qa-1.0', 'status': 'PASS',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'root_cause_of_initial_zero': 'Outcome compiler sought candidate roots only in v7 skill-tree index, whose input root coverage omitted workspace/inputs/candidate; original archive/file_index contains the actual candidate files.',
        'v7_index_input_root_types': dict(actual_input_root_types),
        'original_file_index_review_candidate_episode_count': len(candidate),
        'retained_route_cases_checked': sum(c[-1] for c in CASES),
        'other_diagnostic_cases_checked': sum(not c[-1] for c in CASES),
        'complete_file_triplets_checked': sum(len(x['files_checked']) for x in observations),
        'all_three_way_complete_maps_exact': True, 'cases': observations,
        'training_started': False, 'generated_code_executed': False,
        'warning': 'Review decisions and task findings remain historical silver. Version identity alone cannot certify any action positive, teacher-equivalent quality, causal benefit, source cleanliness, or generalization.'}
    path = OUT / 'VERSION_IDENTITY_QA.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'retained_cases': result['retained_route_cases_checked'],
        'other_cases': result['other_diagnostic_cases_checked'], 'file_triplets': result['complete_file_triplets_checked'],
        'source_candidate_episode_count': len(candidate), 'output': str(path)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
