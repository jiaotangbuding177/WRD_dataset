"""Passive native read/version evidence for settled consumption episodes."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'output/20261027_wrd_main_v10/runtime_preflight'


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--job-id', required=True)
    args = ap.parse_args()
    ep = BASE / 'episodes' / args.job_id
    job = load(ep / 'job.json')
    result = load(ep / 'result.json')
    assert result['status'] in ('completed', 'failed')
    response = load(ep / 'response.json') if (ep / 'response.json').is_file() else {}
    versions = []
    for skill in job['skills']:
        parent = Path(skill['path'])
        expected = {p.relative_to(parent).as_posix(): sha(p) for p in parent.rglob('*') if p.is_file()}
        for location in ('learned_skills', 'skills'):
            actual = ep / 'workspace' / location / skill['id']
            rows = []
            for rel, digest in expected.items():
                path = actual / rel
                rows.append({'path': rel, 'expected_sha256': digest,
                             'actual_sha256': sha(path) if path.is_file() else None,
                             'matches': path.is_file() and sha(path) == digest})
            versions.append({'skill_id': skill['id'], 'workspace_location': location,
                             'functional_files': rows, 'all_functional_files_match': all(r['matches'] for r in rows)})
    native = ep / 'openclaw_transport/all_session_events.jsonl'
    data = {'schema': 'wrd-passive-native-skill-consumption-and-version-audit-v1',
            'job_id': args.job_id, 'actual_job_sha256': sha(ep / 'job.json'),
            'native_terminal_status': result['status'], 'response_sha256': sha(ep / 'response.json') if response else None,
            'original_native_loading_evidence': response.get('loading_evidence'),
            'loaded_skill_ids': response.get('loaded_skill_ids', []), 'functional_version_checks': versions,
            'native_events_path': str(native), 'native_events_sha256': sha(native) if native.is_file() else None,
            'no_skill_arm_has_no_learned_skill_in_native_request': load(ep / 'request.json')['learned_skills'] == [],
            'all_supplied_skill_functional_bytes_stable': all(v['all_functional_files_match'] for v in versions),
            'read_evidence_is_not_proof_of_useful_semantic_effect': True,
            'artifact_success_is_not_Q_or_benefit': True, 'model_calls': 0}
    output = ep / 'CONSUMPTION_AUDIT.json'
    assert not output.exists()
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'job_id': args.job_id, 'loaded_skill_ids': data['loaded_skill_ids'],
                      'functional_bytes_stable': data['all_supplied_skill_functional_bytes_stable']}))


if __name__ == '__main__':
    main()
