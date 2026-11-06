"""Secret-free OpenClaw 2026.9.5 configuration for isolated container runs.

The runtime and its tools remain OpenClaw's own implementations.  This module
does not load skill bodies into a prompt, implement tools, or call the model.
Paths are container paths: do not resolve them against the Windows host.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence


OPENCLAW_VERSION = "2026.9.5"
ECNU_BASE_URL = "https://chat.ecnu.edu.cn/open/api/v1"
NO_BUNDLED_SKILLS = "__eval_no_bundled_skills__"


def _absolute_container_path(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.startswith("/") or "\x00" in value:
        raise ValueError(f"{name} must be an absolute Linux container path")
    return value


def build_openclaw_config(
    workspace: str = "/workspace",
    *,
    agent_id: str = "eval",
    provider_id: str = "ecnu",
    model_id: str = "ecnu-plus",
    base_url: str = ECNU_BASE_URL,
    api_key_env: str = "ECNU_API_KEY",
    browser_executable: str = "/usr/bin/chromium",
    exec_path_prepend: Sequence[str] = ("/opt/eval-venv/bin", "/opt/openclaw/bin", "/opt/node-tools/bin"),
    timeout_seconds: int = 600,
    max_tokens: int = 4096,
    context_window: int | None = None,
    context_tokens: int | None = None,
    input_modalities: Sequence[str] = ("text",),
    compatibility: Mapping[str, Any] | None = None,
    bundled_skill_names: Sequence[str] = (),
    extra_skill_dirs: Sequence[str] = (),
    skill_names: Sequence[str] | None = None,
    enable_memory: bool = True,
    enable_cron: bool = True,
    enable_background_maintenance: bool = False,
    allow_browser_private_network: bool = True,
    gateway_port: int = 18789,
    gateway_token_env: str = "OPENCLAW_EVAL_GATEWAY_TOKEN",
) -> dict[str, Any]:
    """Build the actual pinned-version schema, keeping API keys out of JSON.

    ``max_tokens`` is the experiment's requested output budget, not a verified
    ECNU model limit.  Unknown context/multimodal capabilities are not invented.
    ``skill_names=None`` allows native discovery of workspace skills, including
    a skill the task explicitly asks the agent to download during execution.
    An explicit list is an OpenClaw agent skill allowlist, not an OS boundary.
    ``bundled_skill_names`` names bundled skills intentionally admitted by the
    experiment.  Empty uses a nonmatching sentinel because the pinned runtime
    interprets ``allowBundled=[]`` as unrestricted.
    Background memory dreaming and automatic Skill Workshop review are off
    by default as research controls. Native memory tools and user-created cron
    jobs stay enabled; enabling these maintenance routines is a separate
    experimental choice.
    Browser private-network navigation is allowed in the isolated experiment
    container, including HTTP servers started by the task on loopback. An
    explicit hostname allowlist would also restrict public browsing, so none
    is added here. This does not add support for non-HTTP URL schemes.
    """
    _absolute_container_path(workspace, "workspace")
    _absolute_container_path(browser_executable, "browser_executable")
    if not re.fullmatch(r"[a-z0-9_][a-z0-9_-]{0,63}", agent_id):
        raise ValueError("invalid OpenClaw agent_id")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", api_key_env):
        raise ValueError("invalid API key environment variable name")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", gateway_token_env):
        raise ValueError("invalid Gateway token environment variable name")
    if isinstance(gateway_port, bool) or not isinstance(gateway_port, int) or not 1 <= gateway_port <= 65535:
        raise ValueError("gateway_port must be between 1 and 65535")
    if not provider_id or "/" in provider_id or not model_id:
        raise ValueError("provider_id and model_id must form provider/model")
    if base_url != 'http://host.docker.internal:18759/v1':
        raise ValueError("WRD58 model base_url must match the isolated relay")
    for name, value in (("timeout_seconds", timeout_seconds), ("max_tokens", max_tokens)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    for name, value in (("context_window", context_window), ("context_tokens", context_tokens)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value <= 0):
            raise ValueError(f"{name} must be a positive integer when supplied")
    if context_tokens is not None and context_window is not None and context_tokens > context_window:
        raise ValueError("context_tokens cannot exceed context_window")
    if not isinstance(enable_background_maintenance, bool):
        raise ValueError("enable_background_maintenance must be boolean")
    if not isinstance(allow_browser_private_network, bool):
        raise ValueError("allow_browser_private_network must be boolean")
    modalities = list(input_modalities)
    if not modalities or any(item not in {"text", "image", "audio", "video"} for item in modalities):
        raise ValueError("invalid input modalities")
    for directory in extra_skill_dirs:
        _absolute_container_path(directory, "extra_skill_dirs item")
    for directory in exec_path_prepend:
        _absolute_container_path(directory, "exec_path_prepend item")
    model_ref = f"{provider_id}/{model_id}"
    compat: dict[str, Any] = {
        "supportsStore": False,
        "supportsDeveloperRole": False,
        "supportsReasoningEffort": False,
        "supportsUsageInStreaming": False,
        "supportsStrictMode": False,
        "maxTokensField": "max_tokens",
    }
    if compatibility is not None:
        compat.update(compatibility)
    model: dict[str, Any] = {
        "id": model_id,
        "name": model_id,
        "reasoning": True,
        "input": modalities,
        "maxTokens": max_tokens,
        "compat": compat,
    }
    if context_window is not None:
        model["contextWindow"] = context_window
    if context_tokens is not None:
        model["contextTokens"] = context_tokens
    entry: dict[str, Any] = {"workspace": workspace}
    if skill_names is not None:
        entry["skills"] = list(skill_names)
    config: dict[str, Any] = {
        "env": {"shellEnv": {"enabled": False}},
        "models": {
            "mode": "replace",
            "catalogRefresh": {"enabled": False},
            "providers": {
                provider_id: {
                    "baseUrl": base_url.rstrip("/"),
                    "api": "openai-completions",
                    "apiKey": "${" + api_key_env + "}",
                    "models": [model],
                }
            },
        },
        "agents": {
            "ownership": "explicit",
            "defaults": {
                "model": {"primary": model_ref, "fallbacks": []},
                "models": {model_ref: {"codeMode": False}},
                "workspace": workspace,
                "skipBootstrap": True,
                "startupContext": {"enabled": False},
                "heartbeat": {"every": "0m"},
                "timeoutSeconds": timeout_seconds,
                "sandbox": {"mode": "off"},
            },
            "entries": {agent_id: entry},
        },
        "tools": {
            "profile": "full",
            "codeMode": False,
            "exec": {
                "host": "gateway",
                "mode": "full",
                "strictInlineEval": False,
                "timeoutSeconds": timeout_seconds,
                "pathPrepend": list(exec_path_prepend),
            },
            "fs": {"workspaceOnly": False},
        },
        "browser": {
            "enabled": True,
            "headless": True,
            "noSandbox": True,
            "executablePath": browser_executable,
            "defaultProfile": "openclaw",
            "allowSystemProfileImport": False,
            "ssrfPolicy": {"dangerouslyAllowPrivateNetwork": allow_browser_private_network},
        },
        "skills": {
            "allowBundled": list(bundled_skill_names) or [NO_BUNDLED_SKILLS],
            "load": {"extraDirs": list(extra_skill_dirs), "watch": False},
            "workshop": {"autonomous": {"mode": "auto" if enable_background_maintenance else "off"}},
        },
        "plugins": {"entries": {"memory-core": {"config": {
            "dreaming": {"enabled": enable_background_maintenance}
        }}}},
        "cron": {"enabled": enable_cron},
        "gateway": {
            "mode": "local",
            "bind": "loopback",
            "port": gateway_port,
            "auth": {"mode": "token", "token": "${" + gateway_token_env + "}"},
        },
    }
    if enable_memory:
        config["memory"] = {"search": {
            "enabled": True,
            "provider": "none",
            "fallback": "none",
            "store": {"vector": {"enabled": False}, "fts": {"tokenizer": "trigram"}},
        }}
    else:
        config["memory"] = {"search": {"enabled": False}}
        config["plugins"]["slots"] = {"memory": "none"}
        config["agents"]["defaults"]["compaction"] = {"memoryFlush": {"enabled": False}}
    return config


def build_process_env(
    state_dir: str = "/tmp/openclaw-eval-state",
    config_path: str = "/tmp/openclaw-eval-config.json",
) -> dict[str, str]:
    """Return only nonsecret env overrides; the runner separately injects key.

    The runner must allocate a fresh state directory per independent trial and
    keep it unchanged for all user turns in that trial.  This function never
    copies a host environment, credential store, or source conversation.
    """
    return {
        "OPENCLAW_STATE_DIR": _absolute_container_path(state_dir, "state_dir"),
        "OPENCLAW_CONFIG_PATH": _absolute_container_path(config_path, "config_path"),
    }


def build_agent_argv(
    message_file: str,
    session_id: str,
    *,
    agent_id: str = "eval",
    timeout_seconds: int = 600,
    executable: str = "openclaw",
    local: bool = False,
) -> list[str]:
    """One native turn, preserving a session across user messages.

    Gateway mode is the default because automations depend on live Gateway RPC.
    ``local=True`` is an explicit embedded-only mode and must never coexist with
    a Gateway that owns the same state directory.  No fallback is performed.
    """
    _absolute_container_path(message_file, "message_file")
    if not session_id.strip() or not agent_id.strip():
        raise ValueError("session_id and agent_id must not be blank")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be a positive integer")
    return [
        executable, "agent", *(["--local"] if local else []), "--agent", agent_id,
        "--session-id", session_id, "--message-file", message_file,
        "--thinking", "off", "--timeout", str(timeout_seconds), "--json",
    ]


def build_gateway_argv(*, executable: str = "openclaw") -> list[str]:
    """Start the foreground Gateway using this run's config and env token."""
    return [executable, "gateway", "run"]


def build_gateway_health_argv(*, executable: str = "openclaw") -> list[str]:
    """Authenticated native readiness check; timeout unit is milliseconds."""
    return [executable, "health", "--json", "--timeout", "2000"]


def build_trajectory_export_argv(
    session_key: str,
    *,
    workspace: str = "/workspace",
    output_name: str = "eval-evidence",
    agent_id: str = "eval",
    executable: str = "openclaw",
) -> list[str]:
    """Export native redacted tool/transcript evidence after the turn exits."""
    _absolute_container_path(workspace, "workspace")
    if not session_key.strip():
        raise ValueError("session_key must not be blank")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", output_name):
        raise ValueError("output_name must be a simple relative directory name")
    return [
        executable, "sessions", "export-trajectory", "--agent", agent_id,
        "--session-key", session_key, "--workspace", workspace,
        "--output", output_name, "--json",
    ]


def write_config(path: Path, config: Mapping[str, Any]) -> None:
    """Write generated JSON; supplied config should contain env references only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
