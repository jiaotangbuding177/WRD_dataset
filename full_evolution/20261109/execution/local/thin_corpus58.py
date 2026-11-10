"""Thin release binding of the inherited native launcher and byte-preserving audit relay."""
from __future__ import annotations

import hmac
import io
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class CredentialCheckedResponse:
    """Preserve upstream bytes, withholding any credential across read boundaries."""

    def __init__(self, response, forbidden):
        self.response = response
        self.forbidden = forbidden
        self.tail_size = max(map(len, forbidden)) - 1
        self.tail = b""

    def __getattr__(self, name):
        return getattr(self.response, name)

    def read1(self, size):
        while True:
            chunk = self.response.read1(size)
            pending = self.tail + chunk
            if any(secret in pending for secret in self.forbidden):
                raise RuntimeError("Unexpected credential in upstream body")
            if not chunk:
                self.tail = b""
                return pending
            if len(pending) > self.tail_size:
                split = len(pending) - self.tail_size
                self.tail = pending[split:]
                return pending[:split]
            self.tail = pending


class PrivateOpener:
    def __init__(self, forbidden):
        self.forbidden = forbidden
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def open(self, request, timeout):
        try:
            response = self.opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as error:
            response = error
        except OSError as error:
            raise OSError(type(error).__name__) from None
        if any(secret in str(response.headers.get("Content-Type", "")).encode() for secret in self.forbidden):
            response.close()
            raise RuntimeError("Unexpected credential in upstream content type")
        return CredentialCheckedResponse(response, self.forbidden)


def run_native(helper, attempt, provider, env, lease, credentials):
    arm = provider.arm
    limits = helper.LIMITS
    context = 131072
    relay = helper.import_file("thin_audit_relay57", helper.HERE / "lib/audit_relay57.py")
    budgets = helper.import_file("thin_native_budget", helper.HERE / "lib/native_budget.py")
    Ledger = helper.make_ledger_class(budgets)
    ledger = Ledger(
        max_requests=limits["max_requests"], max_io_tokens=context * limits["max_requests"],
        max_seconds=limits["wall_seconds"], reservation_tokens=context,
        reservation_basis="one full common native context per admitted HTTP call",
        model=arm, output=attempt / "budget.json",
    )
    local_key = "loopback-" + secrets.token_hex(16)
    model = {
        "api_key": local_key, "model": arm, "input_modalities": ["text"],
        "max_tokens": limits["max_reply_tokens"], "context_window": context, "context_tokens": context,
        "compatibility": {"supportsUsageInStreaming": True},
    }

    class PrivateHandler(relay.AuditHandler):
        def do_POST(self):
            supplied = self.headers.get("Authorization", "").encode()
            if not hmac.compare_digest(supplied, ("Bearer " + local_key).encode()):
                return self.reply_error(401, "This relay belongs to one pinned isolated attempt")
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 128 * 1024 * 1024:
                    return self.reply_error(413, "Missing or excessive request body")
                body = self.rfile.read(length)
                if len(body) != length:
                    return self.reply_error(400, "Incomplete native request body")
                if any(secret in body for secret in self.server.opener.forbidden):
                    return self.reply_error(400, "Credential in request body")
                helper.check_native_body(json.loads(body), arm)
                remaining = limits["wall_seconds"] - (time.monotonic() - ledger.started)
                self.server.timeout = min(self.server.timeout, max(0.1, remaining))
            except (ValueError, TypeError):
                return self.reply_error(400, "Invalid native request or per-reply budget")
            original = self.rfile
            self.rfile = io.BytesIO(body)
            try:
                super().do_POST()
            finally:
                self.rfile = original

    class ExclusiveAuditServer(relay.AuditServer):
        allow_reuse_address = False
        daemon_threads = False

        def server_bind(self):
            self.socket.close()
            self.socket = lease
            self.server_address = lease.getsockname()
            self.server_name = socket.getfqdn(self.server_address[0])
            self.server_port = self.server_address[1]

    started = time.monotonic()
    result = {
        "schema": "wrd58-corpus-producer-result-v1", "arm": arm, "budget_limits": limits,
        "quality_judged": False, "native_loop_modified": False, "tool_returns_modified": False,
    }
    with tempfile.TemporaryDirectory(prefix="wrd58-private-") as directory:
        local_cfg = Path(directory) / "local.json"
        local_cfg.write_text(json.dumps(model | {"base_url": helper.LOCAL}), encoding="utf-8")
        server = None
        thread = None
        try:
            server = ExclusiveAuditServer(
                lease.getsockname(), local_cfg, attempt / "model_http",
                timeout=limits["wall_seconds"], max_calls=limits["max_requests"],
                purpose="wrd58_thin_pipeline_native_effect_not_SFT", budget_guard=ledger,
            )
            if credentials is None:
                server.model["base_url"] = helper.SPARK
            else:
                server.model.update(base_url=credentials["base_url"], api_key=credentials["api_key"])
            server.secret = server.model["api_key"].encode()
            keys = {local_key.encode(), server.secret, server.secret.replace(b"/", b"\\/")}
            server.opener = PrivateOpener(tuple(keys))
            server.RequestHandlerClass = PrivateHandler
            helper.save_new(attempt / "dispatch.json", {
                "arm": arm, "limits": limits, "endpoint": provider.receipt,
                "request_sha256": helper.digest(attempt / "request.json"),
                "native_workspace_binding": helper.native_workspace_binding_proof(attempt),
                "relay_single_owner": True, "pid": os.getpid(),
            })
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            launch = [
                sys.executable, "-B", "-X", "utf8", str(helper.RUNTIME / "consumer.py"),
                str(attempt / "request.json"), str(attempt / "response.json"), "--image", helper.IMAGE,
                "--timeout", str(limits["wall_seconds"]), "--credentials", str(local_cfg), "--backend", "native",
            ]
            result["returncode"] = subprocess.run(launch, cwd=attempt / "workspace", env=env, check=False).returncode
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            result.update(returncode=1, error_type=type(error).__name__)
        finally:
            if thread is not None:
                server.shutdown()
                thread.join()
            if server is not None:
                server.server_close()
            result.update(budget=ledger.snapshot(), wall_seconds=time.monotonic() - started)
            result["actual_skill_md"] = sorted(
                p.relative_to(attempt / "workspace").as_posix()
                for p in (attempt / "workspace/outputs/skill").rglob("SKILL.md") if p.is_file()
            )
            result["artifact_status"] = ("ARTIFACT_PRESENT_UNREVIEWED" if result["actual_skill_md"]
                                         else "NO_SKILL_ARTIFACT")
            helper.save_new(attempt / "producer_result.json", result)
    return result
