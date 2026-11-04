"""Independent collection-only OpenAI-compatible JSON/SSE audit relay.

Request and response bodies are forwarded byte-for-byte. Authorization headers
are built only in memory from the existing private configuration and are never
recorded. Recorded calls are SFT-only API evidence, not gold or training labels.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL = ROOT / 'output/20261008_openclaw_eval/private/model_evolution_32768.json'
DESIGN = {'design_revision': '1.3.0', 'change_id': 'ALG-20261013-02',
          'schema_version': 'verified-trace-skills-v3'}


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def parse_sse(blob):
    """Reconstruct an inspection view only; original SSE bytes stay untouched."""
    events = []
    for block in blob.decode('utf-8', errors='strict').replace('\r\n', '\n').split('\n\n'):
        payload = '\n'.join(line[5:].lstrip(' ') for line in block.splitlines() if line.startswith('data:'))
        if not payload or payload == '[DONE]':
            continue
        events.append(json.loads(payload))
    content = []; tool_calls = {}; usage = None; model = None; response_id = None
    finish_reason = None; role = 'assistant'
    for event in events:
        model = event.get('model') or model; response_id = event.get('id') or response_id
        if event.get('usage') is not None:
            usage = event['usage']
        for choice in event.get('choices', []):
            if choice.get('index', 0) != 0:
                continue
            delta = choice.get('delta', {})
            role = delta.get('role') or role
            if delta.get('content'):
                content.append(delta['content'])
            for call in delta.get('tool_calls', []):
                index = call.get('index', 0)
                row = tool_calls.setdefault(index, {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}})
                if call.get('id'):
                    row['id'] = call['id']
                if call.get('type'):
                    row['type'] = call['type']
                function = call.get('function', {})
                row['function']['name'] += function.get('name', '')
                row['function']['arguments'] += function.get('arguments', '')
            finish_reason = choice.get('finish_reason') or finish_reason
    message = {'role': role, 'content': ''.join(content)}
    if tool_calls:
        message['tool_calls'] = [tool_calls[index] for index in sorted(tool_calls)]
    return {'id': response_id, 'model': model, 'usage': usage,
            'choices': [{'index': 0, 'message': message, 'finish_reason': finish_reason}],
            '_inspection_only_reconstructed_from_SSE': True, '_event_count': len(events)}


class AuditServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, model_config, output, *, timeout=90, max_calls=None, purpose='collection_api_audit'):
        self.model = json.loads(Path(model_config).read_text(encoding='utf-8-sig'))
        if not self.model.get('api_key') or not self.model.get('base_url'):
            raise ValueError('Private upstream model configuration is incomplete')
        self.secret = self.model['api_key'].encode()
        self.output = Path(output); self.output.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout; self.max_calls = max_calls; self.purpose = purpose
        self.counter = 0; self.counter_lock = threading.Lock(); self.log_lock = threading.Lock()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.source_sha256 = digest(Path(__file__).read_bytes())
        self.design_files = {str(ROOT / 'research/designs' / name): digest((ROOT / 'research/designs' / name).read_bytes())
                             for name in ['A_B_MODULES.md', 'PIPELINE.md']}
        super().__init__(address, AuditHandler)


class AuditHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, format, *args):
        pass  # No accidental URL/header/credential logs.

    def reply_error(self, status, reason):
        blob = json.dumps({'error': {'type': 'audit_relay_error', 'message': reason}}).encode()
        self.send_response(status); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(blob))); self.end_headers(); self.wfile.write(blob)

    def do_GET(self):
        if self.path != '/health':
            return self.reply_error(404, 'Unsupported endpoint')
        blob = json.dumps({'status': 'listening', 'upstream_called': False,
                           'ordinary_JSON_supported': True, 'SSE_supported': True}).encode()
        self.send_response(200); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(blob))); self.end_headers(); self.wfile.write(blob)

    def do_POST(self):
        server = self.server
        if self.path not in ['/v1/chat/completions', '/chat/completions']:
            return self.reply_error(404, 'Only chat/completions is supported; no silent endpoint fallback')
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 128 * 1024 * 1024:
                return self.reply_error(413, 'Missing or excessive body length')
            body = self.rfile.read(length)
            if len(body) != length:
                return self.reply_error(400, 'Incomplete request body')
            if server.secret in body:
                return self.reply_error(400, 'Credential appears in request body; request was not forwarded or recorded')
            parsed = json.loads(body)
            if not isinstance(parsed, dict) or not isinstance(parsed.get('messages'), list):
                return self.reply_error(400, 'Expected actual messages array')
            with server.counter_lock:
                if server.max_calls is not None and server.counter >= server.max_calls:
                    return self.reply_error(429, 'Relay control budget exhausted')
                server.counter += 1; index = server.counter
            call_id = f'{index:04d}_{uuid.uuid4().hex}'
            folder = server.output / call_id; folder.mkdir()
            request_path = folder / 'request.raw.json'; request_path.write_bytes(body)
            receipt = {'schema': 'collection-actual-api-audit-v1', 'call_id': call_id, 'started_at': utc(),
                'purpose': server.purpose, 'bound_design': DESIGN, 'design_source_sha256': server.design_files,
                'relay_source_sha256': server.source_sha256, 'request_path': str(request_path),
                'request_sha256': digest(body), 'model_requested': parsed.get('model'),
                'messages_count': len(parsed['messages']), 'tools_count': len(parsed.get('tools', [])),
                'stream_requested': parsed.get('stream', False), 'request_body_rewritten': False,
                'headers_recorded': False, 'credential_recorded': False, 'raw_token_ids': None,
                'raw_logprobs': None, 'training_eligibility': 'SFT_ONLY_API_EVIDENCE',
                'gold_verified': False, 'is_training_label': False, 'status': 'FORWARDING'}
            write_json(folder / 'receipt.json', receipt)
            request = urllib.request.Request(server.model['base_url'].rstrip('/') + '/chat/completions', body,
                {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + server.model['api_key'],
                 'Accept-Encoding': 'identity'})
            started = time.monotonic(); response = None
            try:
                response = server.opener.open(request, timeout=server.timeout)
            except urllib.error.HTTPError as exc:
                response = exc
            if response is None:
                raise RuntimeError('No upstream response')
            status = response.getcode(); content_type = response.headers.get('Content-Type', 'application/json')
            # Record no headers: just the parser mode needed to reconstruct bodies.
            is_sse = 'text/event-stream' in content_type.lower()
            self.send_response(status); self.send_header('Content-Type', content_type)
            self.send_header('Connection', 'close'); self.end_headers()
            response_path = folder / ('response.raw.sse' if is_sse else 'response.raw.json')
            received = bytearray()
            client_failed = False
            with response_path.open('wb') as file:
                while True:
                    chunk = response.read1(65536)
                    if not chunk:
                        break
                    if server.secret in chunk:
                        raise RuntimeError('Credential appears in upstream response; record aborted')
                    received.extend(chunk); file.write(chunk)
                    if not client_failed:
                        try:
                            self.wfile.write(chunk); self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            client_failed = True
            response.close(); self.close_connection = True
            blob = bytes(received)
            if server.secret in blob:
                response_path.write_bytes(b'[REDACTED: credential unexpectedly present]')
                raise RuntimeError('Credential appeared across response chunks; raw record is unavailable')
            receipt.update(status='COMPLETE', http_status=status, elapsed_seconds=round(time.monotonic()-started, 3),
                response_path=str(response_path), response_sha256=digest(blob), response_bytes=len(blob),
                response_mode='SSE' if is_sse else 'JSON', response_body_rewritten=False, client_disconnected=client_failed)
            try:
                view = parse_sse(blob) if is_sse else json.loads(blob)
                receipt.update(model_returned=view.get('model'), usage=view.get('usage'), response_id=view.get('id'))
                if is_sse:
                    write_json(folder / 'response.inspection.json', view)
            except (ValueError, UnicodeError, TypeError, AttributeError) as exc:
                receipt['inspection_error'] = type(exc).__name__
            write_json(folder / 'receipt.json', receipt)
            with server.log_lock:
                with (server.output / 'audit_manifest.jsonl').open('a', encoding='utf-8') as log:
                    log.write(json.dumps(receipt, ensure_ascii=False) + '\n')
        except Exception as exc:
            if 'receipt' in locals():
                receipt.update(status='ERROR', error_type=type(exc).__name__)
                write_json(folder / 'receipt.json', receipt)
            if not getattr(self, '_headers_buffer', None):
                try:
                    self.reply_error(502, type(exc).__name__)
                except (OSError, ValueError):
                    pass
            self.close_connection = True


def start_local(model_config, output, *, max_calls=3, purpose='non_business_doctor_control'):
    server = AuditServer(('127.0.0.1', 0), model_config, output, max_calls=max_calls, purpose=purpose)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    return server, thread


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-config', type=Path, default=DEFAULT_MODEL)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=18891)
    parser.add_argument('--max-calls', type=int, default=3)
    args = parser.parse_args(argv)
    server = AuditServer((args.host, args.port), args.model_config, args.output, max_calls=args.max_calls)
    print(json.dumps({'listening': f'http://{args.host}:{server.server_port}/v1', 'source_sha256': server.source_sha256,
                      'upstream_credentials_logged': False, 'max_calls': args.max_calls}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
