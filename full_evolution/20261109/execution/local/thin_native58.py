"""Provider selection for the fixed WRD58 native OpenClaw runner."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

import run_autonomous58
from thin_corpus58 import run_native


SPARK_ARMS = ("wrd58-14b-0", "wrd58-14b-241")
GLM_ARM = "glm-5.3-flash"
CONTEXT = 131072
LIMIT_FIELDS = {"max_requests", "max_reply_tokens", "max_completion_tokens", "wall_seconds"}


@dataclass(frozen=True)
class Provider:
    arm: str
    receipt: dict
    credential_file: Path | None = field(default=None, repr=False)


def _credential_file(path):
    try:
        path = Path(path).expanduser().resolve(strict=True)
        if any((parent / ".git").exists() for parent in path.parents):
            raise ValueError("GLM credentials must be outside Git worktrees")
        if path.is_relative_to(Path(__file__).resolve().parents[2]):
            raise ValueError("GLM credentials must be outside the experiment release")
        config = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, RuntimeError, TypeError, UnicodeError, json.JSONDecodeError):
        raise ValueError("Could not read the private GLM credentials JSON") from None
    if not isinstance(config, dict):
        raise ValueError("GLM credentials JSON must be an object")
    if config.get("model") != GLM_ARM:
        raise ValueError("GLM credentials must identify glm-5.3-flash")
    key = config.get("api_key")
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_.~+/=-]{8,4096}", key):
        raise ValueError("GLM credentials require a valid bearer key")
    raw_url = config.get("base_url")
    try:
        if not isinstance(raw_url, str) or not re.fullmatch(r"[!-~]+", raw_url):
            raise ValueError()
        url = urlsplit(raw_url)
        if (not url.hostname or url.username is not None or url.password is not None
                or "?" in raw_url or "#" in raw_url or "\\" in raw_url
                or not url.path.rstrip("/").endswith("/v1")
                or not (url.scheme == "https" or (url.scheme == "http" and url.hostname == "127.0.0.1"))
                or url.port == 0 or (url.hostname == "127.0.0.1" and url.port == 18759)
                or key in raw_url):
            raise ValueError()
    except ValueError:
        raise ValueError("GLM base_url must be an HTTPS /v1 route or an HTTP 127.0.0.1 /v1 route") from None
    if (type(config.get("context_window")) is not int or config["context_window"] < CONTEXT
            or type(config.get("max_tokens")) is not int or config["max_tokens"] < 32768):
        raise ValueError("Declare GLM route capability of at least 131072 context and 32768 reply tokens")
    return path, config


def build_provider(helper, arm, startup_log=None, glm_credentials=None):
    """Check the pinned native runtime, and bind the selected provider without inference."""
    if arm not in (*SPARK_ARMS, GLM_ARM):
        raise ValueError("Unknown thin-pipeline model arm")
    helper.check_runtime()
    env = os.environ.copy()
    if arm in SPARK_ARMS:
        if startup_log is None:
            raise ValueError("Spark requires the actual 14B two-adapter startup log")
        endpoint = run_autonomous58.check_endpoint(helper, arm, startup_log, env)
        return Provider(arm, endpoint | {"provider": "spark-vllm", "context_window": CONTEXT})
    if glm_credentials is None:
        raise ValueError("GLM requires an out-of-repository credentials JSON")
    credential_file, config = _credential_file(glm_credentials)
    actual = subprocess.check_output(
        ["docker", "image", "inspect", helper.IMAGE, "--format", "{{.Id}} {{.Os}}/{{.Architecture}}"],
        env=env, text=True, timeout=30,
    ).strip()
    if actual != helper.IMAGE + " linux/amd64":
        raise ValueError("Native tool image differs")
    return Provider(arm, {
        "provider": "openai-compatible-glm",
        "requested_model": GLM_ARM,
        "native_image": actual,
        "common_context_window": CONTEXT,
        "declared_provider_context_window": config["context_window"],
        "declared_provider_max_tokens": config["max_tokens"],
        "capability_status": "DECLARED_NOT_TESTED",
    }, credential_file)


def run_native_attempt(helper, attempt_root, provider, limits):
    """Dispatch one prepared native session through the byte-preserving audit relay."""
    if (set(limits) != LIMIT_FIELDS or any(type(value) is not int or value < 1 for value in limits.values())
            or limits["max_reply_tokens"] > 32768
            or limits["max_reply_tokens"] > limits["max_completion_tokens"]):
        raise ValueError("Invalid bounded native-session budget")
    attempt = Path(attempt_root).resolve(strict=True)
    if not (attempt / "request.json").is_file() or not (attempt / "workspace/.git").exists():
        raise ValueError("Expected a prepared request and ordinary Git workspace")
    if any((attempt / name).exists() for name in (
        "dispatch.json", "producer_result.json", "response.json", "budget.json", "model_http",
    )):
        raise ValueError("Attempt has prior dispatch or execution evidence")
    if provider.arm == GLM_ARM:
        path, config = _credential_file(provider.credential_file)
        if path.is_relative_to(attempt):
            raise ValueError("GLM credentials must be outside the attempt directory")
        if (config["context_window"] != provider.receipt["declared_provider_context_window"]
                or config["max_tokens"] != provider.receipt["declared_provider_max_tokens"]):
            raise ValueError("GLM route capabilities changed after provider check")
    elif provider.arm in SPARK_ARMS and provider.credential_file is None:
        config = None
    else:
        raise ValueError("Invalid prepared provider")
    env = os.environ.copy()
    lease = helper.reserve_relay(helper.relay_bind(env))
    original = helper.LIMITS
    try:
        helper.LIMITS = dict(limits)
        return run_native(helper, attempt, provider, env, lease, config)
    finally:
        helper.LIMITS = original
        lease.close()
