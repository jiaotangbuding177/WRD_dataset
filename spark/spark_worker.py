#!/usr/bin/env python3
"""Forward one verified file request to the Spark loopback model API."""

import argparse
import base64
import binascii
import hashlib
import http.client
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


PORT = 18758
MAX_REQUEST_BYTES = 16 * 1024 * 1024
MAX_RESPONSE_BYTES = 32 * 1024 * 1024
PROFILES = {"smoke32": (32768, 1024), "yarn128": (131072, 32768)}
REQUEST_FIELDS = {"schema", "request_id", "model", "request_sha256", "request_b64"}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def unique_fields(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate JSON field")
    return result


def invalid_constant(value):
    raise ValueError(f"Invalid JSON numeric constant: {value}")


def decode_json(data):
    return json.loads(data.decode("utf-8"), object_pairs_hook=unique_fields,
                      parse_constant=invalid_constant)


def load_request(path, size, cap):
    match = re.fullmatch(r"wrd58-request-([0-9a-f]{32})\.json", path.name)
    if match is None:
        raise ValueError("Expected wrd58-request-<32 lowercase hex>.json")
    request_id = match.group(1)
    envelope_limit = 4 * ((MAX_REQUEST_BYTES + 2) // 3) + 4096
    with path.open("rb") as source:
        encoded = source.read(envelope_limit + 1)
    if len(encoded) > envelope_limit:
        raise ValueError("Request envelope is too large")
    envelope = decode_json(encoded)
    if not isinstance(envelope, dict) or set(envelope) != REQUEST_FIELDS:
        raise ValueError("Request envelope has unexpected fields")
    if envelope["schema"] != "wrd58-airgap-request-v1" or envelope["request_id"] != request_id:
        raise ValueError("Request schema or filename identity mismatch")
    model = envelope["model"]
    if model not in (f"wrd58-{size}-0", f"wrd58-{size}-26"):
        raise ValueError("Request model is outside the active size pair")
    if not isinstance(envelope["request_b64"], str):
        raise ValueError("Request body must be base64 text")
    try:
        body = base64.b64decode(envelope["request_b64"], validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Malformed request base64") from error
    if not body or len(body) > MAX_REQUEST_BYTES or sha256(body) != envelope["request_sha256"]:
        raise ValueError("Request body length or SHA256 mismatch")
    request = decode_json(body)
    if not isinstance(request, dict) or request.get("model") != model:
        raise ValueError("Request body model does not match its envelope")
    if not isinstance(request.get("messages"), list) or not request["messages"]:
        raise ValueError("Chat request must include messages")
    caps = [request[key] for key in ("max_tokens", "max_completion_tokens") if key in request]
    if not caps or any(type(value) is not int or not 0 < value <= cap for value in caps) or len(set(caps)) != 1:
        raise ValueError(f"Require an explicit, consistent output cap between 1 and {cap}")
    return request_id, model, envelope["request_sha256"], body


def check_server(size, context):
    connection = http.client.HTTPConnection("127.0.0.1", PORT, timeout=15)
    try:
        connection.request("GET", "/v1/models", headers={"Accept-Encoding": "identity"})
        response = connection.getresponse()
        data = response.read(1024 * 1024 + 1)
        if response.status != 200 or len(data) > 1024 * 1024:
            raise ValueError(f"Spark model list unavailable: HTTP {response.status}")
    finally:
        connection.close()
    cards = {card["id"]: card for card in decode_json(data)["data"]}
    expected = {f"wrd58-{size}-{step}" for step in (0, 26)}
    bare = cards.get(f"wrd58-{size}-bare", {})
    if not expected.issubset(cards) or bare.get("max_model_len") != context:
        raise ValueError(f"Spark model IDs or advertised context differ from the selected {size}/{context} profile")


def inference(body, timeout):
    connection = http.client.HTTPConnection("127.0.0.1", PORT, timeout=timeout)
    try:
        connection.request("POST", "/v1/chat/completions", body=body, headers={
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",
        })
        response = connection.getresponse()
        content_type = response.getheader("Content-Type") or "application/octet-stream"
        if (response.getheader("Content-Encoding") or "identity").lower() != "identity":
            raise ValueError("Unexpected encoded Spark response body")
        data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise ValueError("Spark response exceeded the byte limit")
        if response.length not in (None, 0):
            raise ValueError("Spark response closed before the advertised body length")
        return response.status, content_type, data
    finally:
        connection.close()


def publish(path, content):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                     prefix=".wrd58-", dir=path.parent, delete=False) as file:
        temp = Path(file.name)
        try:
            json.dump(content, file, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    try:
        if path.exists():
            raise FileExistsError(path)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def process(args):
    context, cap = PROFILES[args.profile]
    request_id, model, request_sha, body = load_request(args.request, args.size, cap)
    args.outbox.mkdir(mode=0o700, parents=True, exist_ok=True)
    response_path = args.outbox / f"wrd58-response-{request_id}.json"
    receipt_path = args.outbox / f"wrd58-receipt-{request_id}.json"
    claim_path = args.outbox / f".wrd58-dispatch-{request_id}.json"
    if any(path.exists() for path in (claim_path, response_path, receipt_path)):
        raise FileExistsError(f"Request {request_id} already has a dispatch or output in this outbox")
    check_server(args.size, context)
    claim = {"request_id": request_id, "model": model, "profile": args.profile,
             "request_sha256": request_sha, "dispatch_utc": now()}
    descriptor = os.open(claim_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as claim_file:
        json.dump(claim, claim_file, ensure_ascii=True)
        claim_file.flush()
        os.fsync(claim_file.fileno())
    started = time.monotonic()
    try:
        http_status, content_type, data = inference(body, args.timeout)
    except (OSError, ValueError, http.client.HTTPException) as error:
        publish(receipt_path, {**claim, "status": "delivery_unknown", "wall_seconds": round(time.monotonic() - started, 3),
                               "completed_utc": now(), "error_type": type(error).__name__})
        raise RuntimeError(f"Delivery for {request_id} is uncertain; preserve the dispatch marker and do not replay automatically") from error
    response_sha = sha256(data)
    publish(response_path, {
        "schema": "wrd58-airgap-response-v1", "request_id": request_id, "model": model,
        "request_sha256": request_sha, "http_status": http_status, "content_type": content_type,
        "response_sha256": response_sha, "response_b64": base64.b64encode(data).decode("ascii"),
    })
    publish(receipt_path, {**claim, "status": "response_written", "http_status": http_status,
                           "response_sha256": response_sha, "response_bytes": len(data),
                           "wall_seconds": round(time.monotonic() - started, 3), "completed_utc": now()})
    return {"response": str(response_path), "receipt": str(receipt_path), "http_status": http_status}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--outbox", required=True, type=Path)
    parser.add_argument("--size", required=True, choices=("8b", "14b"))
    parser.add_argument("--profile", required=True, choices=PROFILES)
    parser.add_argument("--timeout", type=int, default=300, help="Spark local socket timeout, in seconds")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 1800:
        parser.error("--timeout must be 1..1800 seconds")
    try:
        print(json.dumps(process(args), ensure_ascii=True))
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, http.client.HTTPException) as error:
        print(f"Spark worker: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
