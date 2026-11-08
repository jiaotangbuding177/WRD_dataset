#!/usr/bin/env python3
"""CPU-only interface checks; no Docker, student inference, or skill fixture."""
from __future__ import annotations
import hashlib
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import io
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    native = module('cpu_corpus_runner', HERE / 'run_corpus58.py')
    budget = module('cpu_base_budget', HERE / 'lib/native_budget.py')
    packer = module('cpu_corpus_packer', HERE / 'package_corpus_return58.py')
    effect = module('cpu_effect_dispatch', HERE / 'run_effect58.py')
    passed = []
    native.check_runtime()
    passed.append('fixed native runtime files remain byte-identical to receipt')
    Ledger = native.make_ledger_class(budget)
    def ledger(clock=None):
        kw = dict(max_requests=24, max_io_tokens=131072 * 24, max_seconds=3600,
                  reservation_tokens=131072, reservation_basis='CPU interface bound', model='wrd58-8b-241')
        if clock is not None:
            kw['monotonic'] = clock
        return Ledger(**kw)
    a = ledger()
    for i in range(4):
        a.admit(str(i), model='wrd58-8b-241')
    try:
        a.admit('fifth', model='wrd58-8b-241')
        raise AssertionError('Unknown calls did not reserve the completion cap')
    except budget.BudgetExceeded:
        pass
    assert a.snapshot()['charged_completion_including_unknown_reservations'] == 32768
    a.settle('0', usage={'prompt_tokens': 7, 'completion_tokens': 5, 'total_tokens': 12})
    try:
        a.admit('too_little_refunded', model='wrd58-8b-241')
        raise AssertionError('A whole native reply reserve did not fit')
    except budget.BudgetExceeded:
        pass
    a.settle('1', usage={'prompt_tokens': 7, 'completion_tokens': 5, 'total_tokens': 12})
    a.admit('after_two_exact_refunds', model='wrd58-8b-241')
    assert a.snapshot()['charged_completion_including_unknown_reservations'] == 24586
    passed.append('unknown completion reservations consume the shared limit')
    b = ledger()
    for i in range(24):
        b.admit(str(i), model='wrd58-8b-241')
        b.settle(str(i), usage={'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2})
    try:
        b.admit('25', model='wrd58-8b-241')
        raise AssertionError('25th call was admitted')
    except budget.BudgetExceeded:
        pass
    passed.append('24 HTTP calls include finalization and retries without hidden extra allowance')
    clock = [0]
    c = ledger(lambda: clock[0])
    clock[0] = 3600
    try:
        c.admit('late', model='wrd58-8b-241')
        raise AssertionError('Wall deadline was refreshed')
    except budget.BudgetExceeded:
        pass
    passed.append('persistent per-session wall deadline is not refreshed by calls')
    native.check_native_body({'model': 'wrd58-8b-241', 'messages': [], 'max_tokens': 8192}, 'wrd58-8b-241')
    for payload in [{'model': 'other', 'messages': [], 'max_tokens': 8192},
                    {'model': 'wrd58-8b-241', 'messages': [], 'max_tokens': 8193}]:
        try:
            native.check_native_body(payload, 'wrd58-8b-241')
            raise AssertionError('Wrong model or oversized reply accepted')
        except ValueError:
            pass
    passed.append('fixed arm and native per-reply cap are checked without rewriting body')

    with tempfile.TemporaryDirectory(prefix='wrd58-corpus-cpu-') as directory:
        tmp = Path(directory)
        corpus = tmp / 'corpus'
        case_dir = corpus / 'cases' / 'cpu_input'
        case_dir.mkdir(parents=True)
        def file_pin(name, blob):
            path = corpus / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
            return {'path': name, 'sha256': hashlib.sha256(blob).hexdigest(), 'bytes': len(blob)}
        source = file_pin('objects/source', b'{"messages":[],"turns":[]}')
        prompt = file_pin('objects/prompt', 'CPU input-delivery interface fixture, not a skill task.'.encode())
        index = file_pin('objects/index', b'{"resources":[]}')
        replay = file_pin('objects/replay', b'{"historical_delivery":true}')
        resource = file_pin('objects/resource', b'ordinary input bytes')
        case = {'source_id': 'cpu_input', 'source': source, 'prompt': prompt,
                'delivery_index': index, 'replay': replay,
                'resources': [resource | {'mount': 'inputs/source_resources/t0/input.txt'}],
                'student_eligibility': {'effect_evaluation_allowed': True}}
        (case_dir / 'case.json').write_text(json.dumps(case), encoding='utf-8')
        attempt, receipt = native.prepare(corpus, 'cpu_input', 'wrd58-8b-241', 1, tmp / 'runs')
        assert (attempt / 'workspace/.git/HEAD').is_file()
        assert not list((attempt / 'workspace').rglob('SKILL.md'))
        assert (attempt / 'workspace/inputs/source_resources/t0/input.txt').read_bytes() == b'ordinary input bytes'
        assert receipt['ordinary_repository_initialized'] is True
        binding = receipt['native_workspace_binding']
        assert binding['receiver_backing_git_inside_work_tree'] == 'true'
        assert binding['receiver_backing_git_head'] == receipt['git_commit']
        assert binding['git_objects'] > 0 and binding['copy_filter'] is None
        native.verify_prepared(attempt, corpus, 'cpu_input', 'wrd58-8b-241', 1, False)
        other, _ = native.prepare(corpus, 'cpu_input', 'wrd58-14b-241', 1, tmp / 'runs')
        assert other != attempt
        try:
            native.prepare(corpus, 'cpu_input', 'wrd58-8b-241', 1, tmp / 'runs')
            raise AssertionError('Existing numbered attempt was overwritten')
        except FileExistsError:
            pass
        passed.append('real Git workspace, all pinned resources, arm isolation and numbered attempt preservation')
        (corpus / resource['path']).write_bytes(b'tampered')
        try:
            native.verify_case(corpus, 'cpu_input')
            raise AssertionError('Changed resource pin accepted')
        except ValueError:
            pass
        (corpus / resource['path']).write_bytes(b'ordinary input bytes')
        passed.append('resource mutation is rejected before model dispatch')

        received = []
        sse = ('data: {"id":"cpu-transport","model":"wrd58-8b-241","choices":'
               '[{"index":0,"delta":{"content":"CPU transport"},"finish_reason":"stop"}]}\n\n'
               'data: {"id":"cpu-transport","model":"wrd58-8b-241","choices":[],"usage":'
               '{"prompt_tokens":10,"completion_tokens":3,"total_tokens":13}}\n\n'
               'data: [DONE]\n\n').encode()
        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                received.append(self.rfile.read(int(self.headers['Content-Length'])))
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Content-Length', str(len(sse)))
                self.end_headers()
                self.wfile.write(sse)
        upstream = ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
        upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        upstream_thread.start()
        lease = native.reserve_relay('127.0.0.1', 0)
        address = lease.getsockname()
        try:
            try:
                native.reserve_relay(*address)
                raise AssertionError('A second relay owner acquired the reserved socket')
            except OSError:
                pass
            passed.append('exclusive socket ownership rejects a concurrent relay before dispatch')
            old_spark = native.SPARK
            native.SPARK = f'http://127.0.0.1:{upstream.server_port}/v1'
            exact_body = b'{ "model":"wrd58-8b-241", "messages":[{"role":"user","content":"CPU transport"}], "max_tokens":8192, "stream":true }'
            real_run = native.subprocess.run
            def cpu_only_native_launcher(argv, **kwargs):
                if argv[0] == 'git':
                    return real_run(argv, **kwargs)
                cfg = json.loads(Path(argv[argv.index('--credentials') + 1]).read_text(encoding='utf-8'))
                request = urllib.request.Request(f'http://127.0.0.1:{address[1]}/v1/chat/completions',
                         exact_body, {'Authorization': 'Bearer ' + cfg['api_key'], 'Content-Type': 'application/json'})
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(request, timeout=10) as response:
                    assert response.read() == sse
                return subprocess.CompletedProcess(argv, 0)
            native.subprocess.run = cpu_only_native_launcher
            try:
                result = native.run_native(attempt, 'wrd58-8b-241', {}, lease, {'CPU_only': True})
            finally:
                native.subprocess.run = real_run
                native.SPARK = old_spark
            assert received == [exact_body]
            assert result['budget']['charged_completion_including_unknown_reservations'] == 3
            assert result['artifact_status'] == 'NO_SKILL_ARTIFACT'
            assert result['quality_judged'] is False
            traces = list((attempt / 'model_http').glob('*/request.raw.json'))
            assert len(traces) == 1 and traces[0].read_bytes() == exact_body
            assert list((attempt / 'model_http').glob('*/response.raw.sse'))[0].read_bytes() == sse
            passed.append('actual local fake-upstream relay preserves request and SSE bytes and settles exact usage')
            try:
                native.verify_prepared(attempt, corpus, 'cpu_input', 'wrd58-8b-241', 1, False)
                raise AssertionError('Dispatched attempt was reusable')
            except ValueError:
                pass
            passed.append('dispatched evidence cannot be overwritten or silently resumed')
        finally:
            lease.close()
            upstream.shutdown()
            upstream.server_close()
            upstream_thread.join()
        out = tmp / 'return.zip'
        assert packer.main(['--runs', str(tmp / 'runs'), '--out', str(out)]) == 0
        with zipfile.ZipFile(out) as archive:
            pins = archive.read('SHA256SUMS').decode().splitlines()
            for pin in pins:
                sha, name = pin.split('  ', 1)
                assert hashlib.sha256(archive.read(name)).hexdigest() == sha
            assert archive.read('runs/cpu_input/wrd58-8b-241/attempt-001/workspace/inputs/source_resources/t0/input.txt') == b'ordinary input bytes'
        passed.append('return archive preserves all attempts/input/artifacts/traces and every member SHA')
        ids = ['cpu_input', 'cpu_input_2', 'cpu_input_3', 'cpu_input_4']
        for source_id in ids[1:]:
            directory = corpus / 'cases' / source_id
            directory.mkdir()
            (directory / 'case.json').write_text(json.dumps(case | {'source_id': source_id}), encoding='utf-8')
        selection = tmp / 'selection.json'
        selection.write_text(json.dumps({'sources': [{'source_id': value} for value in ids]}), encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            assert effect.main(['--corpus', str(corpus), '--selection', str(selection), '--phase', 'first3',
                                '--size', '8b', '--startup-log', str(tmp / 'not_read_in_dry_run.log'),
                                '--runs', str(tmp / 'phase_runs'), '--dry-run']) == 0
        dry = json.loads(stdout.getvalue())
        assert len(dry['commands']) == 6 and dry['new_model_calls'] == 0
        assert dry['commands'][0][dry['commands'][0].index('--arm') + 1] == 'wrd58-8b-0'
        assert dry['commands'][2][dry['commands'][2].index('--arm') + 1] == 'wrd58-8b-241'
        actual_subprocess_run = effect.subprocess.run
        effect.subprocess.run = lambda argv, **kwargs: subprocess.CompletedProcess(
            argv, 1, stdout=b'CPU dispatcher fixture stdout', stderr=b'CPU dispatcher fixture stderr')
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                assert effect.main(['--corpus', str(corpus), '--selection', str(selection), '--phase', 'first3',
                                    '--size', '8b', '--startup-log', str(tmp / 'no_model.log'),
                                    '--runs', str(tmp / 'dispatch_failures')]) == 1
        finally:
            effect.subprocess.run = actual_subprocess_run
        assert len(list((tmp / 'dispatch_failures/_batch').glob('*.stderr.log'))) == 6
        assert all(p.read_bytes() == b'CPU dispatcher fixture stderr'
                   for p in (tmp / 'dispatch_failures/_batch').glob('*.stderr.log'))
        review_rows = []
        for source_id in ids[:3]:
            for arm in native.ARMS:
                file = tmp / 'phase_runs' / source_id / arm / 'attempt-001/producer_result.json'
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(json.dumps({'arm': arm, 'CPU_interface_fixture_only': True}), encoding='utf-8')
                review_rows.append({'source_id': source_id, 'arm': arm, 'attempt': 1,
                       'producer_result_sha256': native.digest(file), 'review_status': 'CONTENT_REVIEWED',
                       'qualified': False, 'qualification_count': 0,
                       'review_evidence': 'CPU negative gate fixture, not production evaluation'})
        review = tmp / 'review.json'
        review.write_text(json.dumps({'selection_sha256': native.digest(selection), 'rows': review_rows}), encoding='utf-8')
        gate = effect.reviewed_prefix(review, selection, ids, tmp / 'phase_runs', 1, native)
        assert gate['stop_both_final_models_zero'] is True
        review_rows[0]['review_status'] = 'NOT_EVALUATED'
        review.write_text(json.dumps({'selection_sha256': native.digest(selection), 'rows': review_rows}), encoding='utf-8')
        try:
            effect.reviewed_prefix(review, selection, ids, tmp / 'phase_runs', 1, native)
            raise AssertionError('Unreviewed prefix was accepted as independent content approval')
        except ValueError:
            pass
        passed.append('frozen task dispatch alternates arms and all-four-arm content review gates remaining sources')
    result = {'status': 'PASS', 'scope': 'CPU interfaces only; no Docker, model inference, or generated skill',
              'checks': passed, 'count': len(passed), 'actual_model_requests': 0,
              'CPU_fake_upstream_requests': 1, 'new_training': 0, 'skill_fixtures': 0}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    main()
