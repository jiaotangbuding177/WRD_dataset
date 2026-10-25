"""Create a new privacy projection; preserve raw records locally and never train.

Publication permission is independent of local training admission. This does not
certify complete anonymization or change original source/log bytes.
"""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'research/data_prep/wrd_training_preflight'))
from privacy import Sanitizer
from publication_gate import assess


def rows(p):
    with gzip.open(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def js(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':'))


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def main():
    base = ROOT / 'output/20261025_wrd_reasoning_recovery_v4'
    dest = base / 'reasoning_privacy_projection'
    dest.mkdir(parents=True, exist_ok=False)
    private = dest / 'local_restricted'
    private.mkdir()
    old = ROOT / 'output/20261025_wrd_training_preflight/prepared_gated/local_restricted'
    for name in ('privacy_hmac_salt.bin', 'privacy_private_mapping.json'):
        shutil.copy2(old / name, private / name)
    sanitizer = Sanitizer(private)
    sources = {
        'sse': base / 'controlled/sse_reasoning_pairs.mechanical.jsonl.gz',
        'raw': base / 'controlled/raw_pairs.nonformal.mechanical.jsonl.gz',
    }
    before = {k: sha(p) for k, p in sources.items()}
    start = time.monotonic()
    # A single global mapping avoids one thought and its context naming the same
    # individual differently. Tools are source-derived and still post-scanned.
    for source in sources.values():
        for r in rows(source):
            sanitizer.discover(r)
    discovery = sanitizer.freeze()
    counts = {}
    public = dest / 'public'
    public.mkdir()
    with gzip.open(dest / 'PUBLICATION_INDEX.jsonl.gz', 'wt', encoding='utf-8', newline='\n') as index:
        for scope, source in sources.items():
            c = Counter()
            with gzip.open(public / (scope + '.reasoning_pairs.jsonl.gz'), 'wt', encoding='utf-8', newline='\n') as accepted, \
                 gzip.open(private / (scope + '.cleaned_all.jsonl.gz'), 'wt', encoding='utf-8', newline='\n') as all_cleaned:
                for ordinal, original in enumerate(rows(source), 1):
                    clean = sanitizer.clean_row(original)
                    gate = assess(clean)
                    okay = clean['privacy_review']['status'] == 'known_pattern_scan_clear' and gate['status'] != 'hold_for_review'
                    clean['publication_approved'] = okay
                    clean['privacy_transform'] = {
                        'source_record_sha256': hashlib.sha256(js(original).encode()).hexdigest(),
                        'policy': 'wrd-public-privacy-v1 plus tabular gate',
                        'raw_original_retained_locally': True,
                        'context_and_reasoning_transformed_consistently': True,
                        'not_the_original_raw_bytes': True,
                        'semantic_preservation_requires_review': True,
                    }
                    clean['publication_gate'] = gate
                    all_cleaned.write(js(clean) + '\n')
                    c['records'] += 1
                    c['original_reasoning_records'] += bool(original.get('original_reasoning_characters'))
                    c['public_records' if okay else 'held_records'] += 1
                    c['public_reasoning_records' if okay else 'held_reasoning_records'] += bool(original.get('original_reasoning_characters'))
                    if okay:
                        accepted.write(js(clean) + '\n')
                    index.write(js({'id': original['id'], 'scope': scope, 'source_ordinal_1based': ordinal,
                                    'source_sha256': before[scope], 'publication_approved': okay,
                                    'reasoning_present': bool(original.get('original_reasoning_characters')),
                                    'privacy_status': clean['privacy_review']['status'], 'gate_status': gate['status'],
                                    'risk_flags': clean['privacy_review'].get('risk_flags', []) + gate.get('risk_flags', []),
                                    'local_cleaned_file': scope + '.cleaned_all.jsonl.gz'}) + '\n')
            counts[scope] = dict(c)
    sanitizer.save_private_mapping()
    assert before == {k: sha(p) for k, p in sources.items()}
    report = {'schema_version': 'wrd-reasoning-privacy-projection-v4', 'counts': counts,
              'source_sha256': before, 'source_files_unchanged': True, 'discovery': discovery,
              'privacy': sanitizer.report(), 'elapsed_seconds': round(time.monotonic() - start, 3),
              'training_started': False, 'publication_is_not_semantic_training_approval': True,
              'private_mapping_and_raw_bodies_not_for_publication': True,
              'claim': 'Public derivative with known-pattern and tabular checks; not absolute privacy or semantic-fidelity certification.'}
    (dest / 'REASONING_PUBLICATION_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(js({'counts': counts, 'elapsed_seconds': report['elapsed_seconds']}))


if __name__ == '__main__':
    main()
