#!/usr/bin/env python3
"""Dispatch frozen real maker tasks; never choose agent actions or grade skills."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def runner():
    spec = importlib.util.spec_from_file_location('effect_corpus_runner', HERE / 'run_corpus58.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def selection_sources(path):
    value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    sources = value.get('sources', value.get('selected')) if isinstance(value, dict) else None
    if not isinstance(sources, list) or not 3 <= len(sources) <= 12:
        raise ValueError('Expected frozen selection.sources/selected with 3 to 12 independent cases')
    ids = [row['source_id'] for row in sources]
    if len(set(ids)) != len(ids):
        raise ValueError('Selection repeats a source')
    return value, ids


def reviewed_prefix(review_path, selection_path, ids, runs, attempt_number, helper):
    review = helper.load(review_path)
    if review.get('selection_sha256') != helper.digest(selection_path):
        raise ValueError('Review is not bound to this frozen selection')
    rows = review.get('rows')
    if not isinstance(rows, list):
        raise ValueError('Missing independent artifact-review rows')
    needed = {(source, arm) for source in ids[:3] for arm in helper.ARMS}
    found = {}
    for row in rows:
        key = (row.get('source_id'), row.get('arm'))
        if key not in needed or key in found or row.get('attempt') != attempt_number:
            raise ValueError('Unexpected, duplicate or differently numbered prefix review')
        path = runs / key[0] / key[1] / f'attempt-{attempt_number:03d}' / 'producer_result.json'
        if row.get('producer_result_sha256') != helper.digest(path):
            raise ValueError('Review result SHA differs from actual evidence')
        if (row.get('review_status') != 'CONTENT_REVIEWED' or type(row.get('qualified')) is not bool
                or type(row.get('qualification_count')) is not int or row['qualification_count'] < 0
                or row['qualified'] != (row['qualification_count'] > 0)
                or not isinstance(row.get('review_evidence'), str) or not row['review_evidence'].strip()):
            raise ValueError('Prefix needs actual content review; file presence or unreviewed status is insufficient')
        found[key] = row['qualified']
    if set(found) != needed:
        raise ValueError('Review must cover all four arms on the first three sources before continuing')
    finals = {size: sum(found[(source, f'wrd58-{size}-241')] for source in ids[:3])
              for size in ('8b', '14b')}
    return {'final_qualified_sources': finals, 'stop_both_final_models_zero': all(v == 0 for v in finals.values()),
            'review_sha256': helper.digest(review_path)}


def review_template(args, ids, helper):
    rows = []
    for source in ids[:3]:
        for arm in helper.ARMS:
            result_path = args.runs.resolve() / source / arm / f'attempt-{args.attempt:03d}' / 'producer_result.json'
            if not result_path.is_file():
                raise ValueError('Prefix result not returned: ' + str(result_path))
            rows.append({'source_id': source, 'arm': arm, 'attempt': args.attempt,
                         'producer_result_path': str(result_path),
                         'producer_result_sha256': helper.digest(result_path),
                         'review_status': 'NOT_EVALUATED', 'qualified': None,
                         'review_evidence': '', 'quality_dimensions': None,
                         'qualification_count': None})
    return {'schema': 'wrd58-prefix-independent-artifact-review-v1',
            'selection_sha256': helper.digest(args.selection), 'rows': rows,
            'note': 'Fill after reviewing actual skill content, source fidelity and real tests. '
                    'A SKILL.md filename or exit code alone is not a qualified skill.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--phase', choices=('first3', 'remaining', 'review-template'), required=True)
    parser.add_argument('--size', choices=('8b', '14b'))
    parser.add_argument('--startup-log', type=Path)
    parser.add_argument('--runs', type=Path, required=True)
    parser.add_argument('--attempt', type=int, default=1)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    helper = runner()
    try:
        selection, ids = selection_sources(args.selection)
        entries = selection.get('sources', selection.get('selected'))
        for source, selected in zip(ids, entries):
            case, _, _ = helper.verify_case(args.corpus, source)
            if not helper.is_effect_eligible(case):
                raise ValueError('Selection includes a source not explicitly cleared for effect evaluation: ' + source)
            if (selected.get('source_sha256', case['source']['sha256']) != case['source']['sha256']
                    or selected.get('category', case.get('category')) != case.get('category')
                    or selected.get('component_id', case.get('component_id')) != case.get('component_id')):
                raise ValueError('Frozen selected source identity/pin differs: ' + source)
        if args.phase == 'review-template':
            if args.out is None:
                parser.error('--out is required for review-template')
            helper.save_new(args.out, review_template(args, ids, helper))
            print(json.dumps({'review_template': str(args.out), 'model_calls': 0}))
            return 0
        if not args.size or (args.startup_log is None and not args.dry_run):
            parser.error('--size is required; --startup-log is required for real dispatch')
        startup_log = args.startup_log or Path('receipts') / f'serve_{args.size}_128k.log'
        gate = None
        if args.phase == 'remaining':
            if args.review is None:
                parser.error('--review is required for remaining; it must review all four prefix arms')
            gate = reviewed_prefix(args.review, args.selection, ids, args.runs.resolve(), args.attempt, helper)
            if gate['stop_both_final_models_zero']:
                print(json.dumps({'status': 'STOP_PREFIX_BOTH_FINAL_MODELS_ZERO', 'review': gate,
                                  'new_model_calls': 0, 'remaining_sources_not_dispatched': ids[3:]}))
                return 3
        target = ids[:3] if args.phase == 'first3' else ids[3:]
        commands = []
        for source in target:
            index = ids.index(source)
            steps = (0, 241) if index % 2 == 0 else (241, 0)
            for step in steps:
                arm = f'wrd58-{args.size}-{step}'
                commands.append([sys.executable, '-B', '-X', 'utf8', str(HERE / 'run_corpus58.py'), 'producer',
                    '--corpus', str(args.corpus.resolve()), '--source', source, '--arm', arm,
                    '--attempt', str(args.attempt), '--out-dir', str(args.runs.resolve()),
                    '--startup-log', str(startup_log.resolve())])
        if args.dry_run:
            print(json.dumps({'phase': args.phase, 'size': args.size,
                              'selection_sha256': helper.digest(args.selection), 'commands': commands,
                              'new_model_calls': 0}, ensure_ascii=False, indent=2))
            return 0
        # This is only task-level dispatch. Each child runs the fixed native agent.
        # Failed tasks do not erase evidence or prevent other frozen tasks from returning.
        summaries = []
        for command in commands:
            source = command[command.index('--source') + 1]
            arm = command[command.index('--arm') + 1]
            folder = args.runs.resolve() / source / arm / f'attempt-{args.attempt:03d}'
            result_file = folder / 'producer_result.json'
            if result_file.is_file():
                old = helper.load(result_file)
                stage = helper.load(folder / 'stage_receipt.json')
                _, case_path, _ = helper.verify_case(args.corpus, source)
                if (stage['case_sha256'] != helper.digest(case_path) or stage['arm'] != arm
                        or stage['source_id'] != source or old.get('arm') != arm
                        or stage['request_sha256'] != helper.digest(folder / 'request.json')):
                    raise ValueError('Previously returned task does not match this frozen dispatch')
                row = {'source_id': source, 'arm': arm, 'status': 'PRESERVED_EXISTING_RESULT',
                       'returncode': old.get('returncode'), 'result_sha256': helper.digest(result_file)}
            elif (folder / 'dispatch.json').exists():
                row = {'source_id': source, 'arm': arm, 'status': 'UNKNOWN_PRIOR_DISPATCH_NOT_RETRIED',
                       'returncode': None}
            else:
                done = subprocess.run(command, check=False, capture_output=True)
                log_dir = args.runs.resolve() / '_batch'
                log_dir.mkdir(parents=True, exist_ok=True)
                log_stem = f'{source}-{arm}-attempt-{args.attempt:03d}-{time.time_ns()}'
                for suffix, blob in [('stdout', done.stdout), ('stderr', done.stderr)]:
                    (log_dir / f'{log_stem}.{suffix}.log').write_bytes(blob)
                row = {'source_id': source, 'arm': arm, 'status': 'RETURNED' if result_file.is_file() else 'NO_RESULT',
                       'returncode': done.returncode,
                       'task_stdout_log': str(log_dir / f'{log_stem}.stdout.log'),
                       'task_stderr_log': str(log_dir / f'{log_stem}.stderr.log'),
                       'result_sha256': helper.digest(result_file) if result_file.is_file() else None}
            summaries.append(row)
            batch_dir = args.runs.resolve() / '_batch'
            batch_dir.mkdir(parents=True, exist_ok=True)
            helper.save_new(batch_dir / f'{args.phase}-{args.size}-{time.time_ns()}.json',
                {'selection_sha256': helper.digest(args.selection), 'phase': args.phase, 'size': args.size,
                 'review_gate': gate, 'created_at': datetime.now(timezone.utc).isoformat(), 'results_so_far': summaries})
        print(json.dumps({'phase': args.phase, 'size': args.size, 'results': summaries}, ensure_ascii=False, indent=2))
        return int(any(row['returncode'] != 0 for row in summaries))
    except (KeyError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
