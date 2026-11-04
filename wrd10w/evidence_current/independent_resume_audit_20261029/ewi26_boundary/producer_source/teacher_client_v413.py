"""ECNU teacher transport: actual six-action decisions with retained receipts.

No optimizer, chain-of-thought supervision, automatic HTTP retry or service
configuration mutation. Credentials are read from the existing private file.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request

from ..skillsloop_graph.core import parse_json_object, read_json, write_json


def request_body(messages, model, max_tokens, thinking=False, reasoning_effort="low"):
    body = {"model": model, "messages": messages, "stream": True,
            "max_tokens": max_tokens, "temperature": 0.1}
    if thinking:
        body.update(thinking={"type": "enabled"}, reasoning_effort=reasoning_effort)
    return body


def transport(body, directory, *, cfg_path, seconds, opener=None):
    directory = Path(directory)
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    config_digest = hashlib.sha256(Path(cfg_path).read_bytes()).hexdigest()
    receipt_path = directory / "receipt.json"
    if receipt_path.exists():
        receipt = read_json(receipt_path)
        if receipt.get("request_sha256") != digest or receipt.get("status") != "COMPLETE":
            raise ValueError("Existing incomplete/different request cannot be blindly retried")
        if receipt.get("model_config_sha256") != config_digest:
            raise ValueError("Completed request model configuration changed")
        for name, expected in (("request.raw.json", digest),
                               ("response.received.raw", receipt.get("response_sha256")),
                               ("response.json", receipt.get("response_json_sha256"))):
            path = directory / name
            if not expected or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("Completed request evidence changed or missing: " + name)
        return read_json(directory / "response.json"), receipt
    if directory.exists():
        raise ValueError("Ambiguous pre-existing request directory: inspect before recovery")
    if seconds <= 0:
        raise RuntimeError("Model deadline exhausted")
    cfg = read_json(cfg_path)
    directory.mkdir(parents=True)
    (directory / "request.raw.json").write_bytes(raw)
    started = time.monotonic()
    deadline = started + seconds
    receipt = {"status": "STARTED", "requested_model": body["model"],
               "request_sha256": digest, "max_output_tokens": body["max_tokens"],
               "model_config_sha256": config_digest,
               "thinking": body.get("thinking"), "reasoning_effort": body.get("reasoning_effort"),
               "credentials_logged": False, "automatic_http_retries": 0,
               "started_at_epoch": time.time(), "request_deadline_seconds": seconds}
    write_json(receipt_path, receipt)
    received = bytearray()
    buffer = b""
    done = False
    try:
        request = urllib.request.Request(cfg["base_url"].rstrip("/") + "/chat/completions", data=raw,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg["api_key"]})
        opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=max(.01, deadline-time.monotonic())) as response:
            content_type = response.headers.get("Content-Type", "")
            while True:
                left = deadline-time.monotonic()
                if left <= 0:
                    raise TimeoutError("Absolute model deadline")
                sock = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
                if sock is not None:
                    sock.settimeout(left)
                part = response.read1(65536)
                if part:
                    received.extend(part)
                    (directory / "response.partial.raw").write_bytes(received)
                if time.monotonic() >= deadline:
                    raise TimeoutError("Absolute model deadline after read")
                if not part:
                    break
                buffer = (buffer+part).replace(b"\r\n", b"\n")
                while b"\n\n" in buffer:
                    frame, buffer = buffer.split(b"\n\n", 1)
                    data = b"\n".join(line[5:].lstrip(b" ") for line in frame.split(b"\n") if line.startswith(b"data:"))
                    if data == b"[DONE]":
                        done = True
                        break
                if done:
                    break
        (directory / "response.received.raw").write_bytes(received)
        if "event-stream" in content_type or bytes(received).lstrip().startswith(b"data:"):
            if not done:
                raise EOFError("SSE response lacks complete logical DONE frame")
            # A logical DONE does not make an upstream error event successful.
            for frame in bytes(received).replace(b"\r\n", b"\n").split(b"\n\n"):
                lines = frame.split(b"\n")
                data = b"\n".join(line[5:].lstrip(b" ") for line in lines if line.startswith(b"data:"))
                if any(line.startswith(b"event:") and line[6:].strip().lower() == b"error" for line in lines):
                    raise ValueError("Provider SSE error event retained")
                if data and data != b"[DONE]" and json.loads(data).get("error"):
                    raise ValueError("Provider SSE error payload retained")
            from ..enterprise_sft_collection.audit_relay import parse_sse
            view = parse_sse(bytes(received))
        else:
            view = json.loads(received)
        if view.get("error") or not view.get("choices"):
            raise ValueError("Provider response lacks choices")
        write_json(directory / "response.json", view)
        receipt.update(status="COMPLETE", model_returned=view.get("model"), usage=view.get("usage"),
            finish_reason=view["choices"][0].get("finish_reason"),
            response_sha256=hashlib.sha256(received).hexdigest(),
            response_json_sha256=hashlib.sha256((directory / "response.json").read_bytes()).hexdigest(),
            stream_logical_done=done)
        return view, receipt
    except urllib.error.HTTPError as exc:
        (directory / "error_response.raw").write_bytes(exc.read())
        receipt.update(status="ERROR", error_type="HTTPError", http_status=exc.code)
        raise RuntimeError("Model HTTP error retained: " + str(exc.code)) from None
    except Exception as exc:
        receipt.update(status="ERROR", error_type=type(exc).__name__)
        raise
    finally:
        receipt["wall_seconds"] = round(time.monotonic()-started, 3)
        write_json(receipt_path, receipt)


class TeacherClient:
    def __init__(self, directory, config, budget):
        self.directory, self.config, self.budget = Path(directory), config, budget
        self.records = read_json(self.directory / "model_ledger.json") if (self.directory / "model_ledger.json").exists() else []
        self.lock = threading.RLock()

    def _save_records(self):
        with self.lock:
            write_json(self.directory / "model_ledger.json", self.records)

    def ask(self, role, call_id, system, payload, max_tokens=24576):
        path = self.directory / call_id
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
        thinking = role == "EWI_TEACHER"
        model = "ecnu-max" if thinking else "ecnu-plus"
        body = request_body(messages, model, max_tokens, thinking)
        cached = (path / "receipt.json").exists() and read_json(path / "receipt.json").get("status") == "COMPLETE"
        if not cached and not self.budget.admit_model(max_output_tokens=max_tokens):
            raise RuntimeError("Cumulative model budget exhausted")
        entry = {"role": role, "call_id": call_id, "directory": str(path), "cached": cached,
                 "status": "ADMITTED", "max_output_tokens": max_tokens}
        with self.lock:
            self.records.append(entry)
            self._save_records()
        try:
            view, receipt = transport(body, path, cfg_path=self.config["model_config_path"],
                seconds=min(self.budget.remaining()["seconds"], 900 if thinking else 300))
            entry.update(status="RETURNED", receipt=receipt)
            message = view["choices"][0]["message"]
            # Provider reasoning fields stay only in restricted raw artifacts;
            # public actions and candidate SFT rows use content exclusively.
            content = message.get("content") or ""
            result = parse_json_object(content)
            write_json(path / "parsed.json", result)
            return result
        except Exception as exc:
            entry.update(status="FAILED_RETAINED", error_type=type(exc).__name__, error=str(exc)[:240])
            if (path / "receipt.json").exists():
                entry["receipt"] = read_json(path / "receipt.json")
            raise
        finally:
            self._save_records()

