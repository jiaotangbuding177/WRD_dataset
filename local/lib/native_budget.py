"""Thread-safe admission ledger for the existing byte-forwarding model relay.

Reservations cover unknown usage and concurrent parent/child calls. Currency is
not inferred from the provider's coefficient. This is budget management only,
not an agent loop or an alteration of native tool returns.
"""
from __future__ import annotations

import json
from pathlib import Path
import threading
import time


class BudgetExceeded(RuntimeError):
    pass


def actual_io(usage):
    """Return exact reported input+output; missing/invalid usage stays unknown."""
    if not isinstance(usage, dict):
        return None
    p = usage.get("prompt_tokens", usage.get("input_tokens"))
    c = usage.get("completion_tokens", usage.get("output_tokens"))
    if any(type(v) is not int or v < 0 for v in (p, c)):
        return None
    total = usage.get("total_tokens")
    if total is not None and (type(total) is not int or total < p + c):
        return None
    # Some providers report additional billable IO in total; use the larger
    # exact declared number rather than silently dropping it.
    return max(p + c, total or 0)


class AdmissionLedger:
    def __init__(self, *, max_requests, max_io_tokens, max_seconds,
                 reservation_tokens, reservation_basis, model, output=None,
                 monotonic=time.monotonic):
        for name, value in (("max_requests", max_requests), ("max_io_tokens", max_io_tokens),
                            ("max_seconds", max_seconds), ("reservation_tokens", reservation_tokens)):
            if type(value) is not int or value <= 0:
                raise ValueError(name + " must be a positive integer")
        if reservation_tokens > max_io_tokens or not reservation_basis or not model:
            raise ValueError("Explicit conservative per-call bound/basis and fixed model are required")
        self.max_requests = max_requests
        self.max_io_tokens = max_io_tokens
        self.max_seconds = max_seconds
        self.reservation_tokens = reservation_tokens
        self.reservation_basis = reservation_basis
        self.model = model
        self.output = Path(output) if output else None
        self.monotonic = monotonic
        self.started = monotonic()
        self.lock = threading.RLock()
        self.calls = {}
        self.breached = False

    def snapshot(self):
        with self.lock:
            used = sum(v["charged_io"] for v in self.calls.values())
            unknown = sum(not v["usage_state"].startswith("EXACT") for v in self.calls.values())
            return {"schema": "wrd57-relay-budget-v1", "model": self.model,
                    "requests_admitted": len(self.calls), "max_requests": self.max_requests,
                    "charged_io_including_unknown_reservations": used,
                    "max_io_tokens": self.max_io_tokens, "unknown_usage_calls": unknown,
                    "elapsed_seconds": self.monotonic() - self.started, "max_seconds": self.max_seconds,
                    "reservation_tokens": self.reservation_tokens,
                    "reservation_basis": self.reservation_basis, "breached": self.breached,
                    "cash": "UNKNOWN_NOT_ZERO", "requests_scope": "all_forwarded_compatible_HTTP_calls",
                    "provider_request_count": "SEPARATE_NATIVE_METER_REQUIRED",
                    "native_pool": getattr(self, "native_pool", None),
                    "calls": {k: dict(v) for k, v in self.calls.items()}}

    def _save(self):
        if self.output:
            self.output.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.output.with_suffix(self.output.suffix + ".tmp")
            temporary.write_text(json.dumps(self.snapshot(), indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.output)

    def admit(self, call_id, *, model, reservation_tokens=None, reservation_basis=None):
        with self.lock:
            reservation = self.reservation_tokens if reservation_tokens is None else reservation_tokens
            if type(reservation) is not int or reservation <= 0 or reservation > self.max_io_tokens:
                raise BudgetExceeded("Per-request conservative reservation is outside the total IO budget")
            if model != self.model or call_id in self.calls:
                raise ValueError("Fixed-model identity or unique admission ID mismatch")
            current = sum(v["charged_io"] for v in self.calls.values())
            if (self.breached or self.monotonic() - self.started >= self.max_seconds
                    or len(self.calls) >= self.max_requests
                    or current + reservation > self.max_io_tokens):
                raise BudgetExceeded("Unified request/time/IO admission budget exhausted")
            self.calls[call_id] = {"charged_io": reservation, "reservation_tokens": reservation,
                "reservation_basis": reservation_basis or self.reservation_basis,
                "usage_state": "RESERVED_UNKNOWN", "response_id": None, "http_finished": False}
            self._save()
            return dict(self.calls[call_id])

    def settle(self, call_id, *, usage, response_id=None):
        """Missing usage retains its full reserve; errors are not free calls."""
        with self.lock:
            row = self.calls[call_id]
            row["http_finished"] = True
            amount = actual_io(usage)
            if row["usage_state"] == "EXACT":
                if amount is not None and row["charged_io"] != amount:
                    raise ValueError("Conflicting exact usage for the same response")
                return
            row["response_id"] = response_id or row["response_id"]
            if amount is not None:
                row.update(charged_io=amount, usage_state="EXACT")
                if amount > row["reservation_tokens"]:
                    self.breached = True
                    row["reservation_bound_violated"] = True
                if sum(v["charged_io"] for v in self.calls.values()) > self.max_io_tokens:
                    self.breached = True
            self._save()

    def reconcile_native_pool(self, events):
        """Charge a dedicated relay epoch exactly, without false HTTP/ID pairs.

        Compatible continuation exchanges and actual provider requests need not
        have the same IDs/counts. An entire isolated epoch is refundable only
        when every admitted HTTP request finished, every actual provider start
        has a stream end AND exact usage. Otherwise all unknown reserves stay.
        No per-HTTP attribution is invented from this aggregate reconciliation.
        """
        with self.lock:
            if not self.calls or not all(v["http_finished"] for v in self.calls.values()):
                return False
            starts, ended, usage = set(), set(), {}
            for event in events:
                identity = event.get("native_request_id")
                if not identity:
                    continue
                if event.get("model") != self.model:
                    raise ValueError("Native meter epoch contains a different model")
                kind = event.get("event")
                if kind == "native_start":
                    starts.add(identity)
                elif kind == "native_stream_end":
                    ended.add(identity)
                elif kind == "native_usage":
                    amount = actual_io(event.get("usage"))
                    if amount is not None:
                        usage[identity] = max(usage.get(identity, 0), amount)
            if not starts or not starts.issubset(ended) or not starts.issubset(usage):
                return False
            if not ended.issubset(starts) or not set(usage).issubset(starts):
                raise ValueError("Native meter epoch has orphan records; do not refund")
            total = sum(usage[key] for key in starts)
            first = True
            for row in self.calls.values():
                row.update(charged_io=total if first else 0, usage_state="EXACT_NATIVE_POOL",
                           attribution="dedicated_epoch_aggregate_not_HTTP_response_mapping")
                first = False
            if total > self.max_io_tokens or len(starts) > self.max_requests:
                self.breached = True
            self.native_pool = {"provider_requests": len(starts), "actual_io_tokens": total,
                                "all_usage_known": True, "per_HTTP_attribution": False}
            self._save()
            return True

    def settle_native(self, provider_completion_id, usage):
        """Only exact response-ID matches release an unknown reservation."""
        with self.lock:
            matches = [key for key, value in self.calls.items()
                       if value["response_id"] == provider_completion_id]
            if len(matches) != 1:
                return False
            self.settle(matches[0], usage=usage, response_id=provider_completion_id)
            return True


def read_native_epoch(path, byte_offset):
    """Read complete meter lines after an explicit dedicated-lane dispatch epoch."""
    if type(byte_offset) is not int or byte_offset < 0:
        raise ValueError("Native meter epoch offset must be explicit and nonnegative")
    file = Path(path)
    if not file.exists():
        return []
    with file.open("rb") as stream:
        stream.seek(byte_offset)
        blob = stream.read()
    # A concurrent append may expose an incomplete final JSON line. Keep its
    # reservation until the complete event can be read on a subsequent check.
    complete = blob.rsplit(b"\n", 1)[0] if b"\n" in blob else b""
    return [json.loads(line) for line in complete.splitlines() if line.strip()]
