"""Explicit path compatibility for isolated public reference packages.

No skill body is read, modified or installed. Supporting docs remain outside
native skills discovery; missing docs are errors, not guessed replacements.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Sequence


REFERENCE_TARGETS = {
    'lark-doc': {
        '../lark-drive/': 'reference_support/lark/skills/lark-drive/',
        '../lark-whiteboard/': 'reference_support/lark/skills/lark-whiteboard/',
        '../lark-shared/': 'reference_support/lark/skills/lark-shared/',
    },
    'nature-reviewer': {
        '../nature-shared/': 'reference_support/nature/skills/nature-shared/',
    },
    'image-editing': {
        '../../MODELS.md': 'reference_support/image-editing-context/MODELS.md',
        '../../references/muapi-image-tools.md': 'reference_support/image-editing-context/references/muapi-image-tools.md',
    },
}


def _skill_name(value: str) -> str:
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}',value) or value in {'.','..'}:
        raise ValueError('skill must be one directory name')
    return value


def _contained_file(workspace: Path, candidate: Path) -> Path:
    resolved=candidate.resolve()
    if not resolved.is_relative_to(workspace.resolve()):
        raise ValueError('reference must remain inside this container workspace')
    if not resolved.is_file():
        raise FileNotFoundError(str(candidate))
    return resolved


def configure_runtime_compat(workspace: Path) -> dict:
    """Create only a path alias and return environment/guide for both arms."""
    workspace=workspace.resolve()
    skills=workspace/'skills'
    skills.mkdir(exist_ok=True)
    legacy=workspace/'.claude'
    if legacy.is_symlink():
        raise ValueError('existing .claude symlink is not a runtime alias')
    legacy.mkdir(exist_ok=True)
    alias=legacy/'skills'
    if alias.is_symlink():
        if alias.resolve()!=skills.resolve():
            raise ValueError('existing .claude/skills alias conflicts with native skills')
    elif alias.exists():
        raise ValueError('existing .claude/skills path conflicts with native skills')
    else:
        alias.symlink_to('../skills',target_is_directory=True)
    return {
        'env':{'CLAUDE_PLUGIN_ROOT':str(workspace)},
        'aliases':[{ 'path':str(alias),'target':str(skills),'changes_skill_bytes':False}],
        'guide':(
            '公开参考skill的实际目录是 /workspace/skills/<名称>，脚本相对该skill根解析。'
            '兼容目录 /workspace/.claude/skills 指向同一目录；CLAUDE_PLUGIN_ROOT=/workspace。'
            '需要CLAUDE_SKILL_DIR的命令可用exec运行 '
            'python /opt/eval-adapter/runtime_compat.py run-skill --skill <名称> -- <命令及参数>，'
            '该变量只针对本条命令，不在多个skill之间共享固定值。'
            '跨包参考正文如果本题准入，会放在 /workspace/reference_support，作为依赖资料而非新增active skill；'
            '可运行 python /opt/eval-adapter/runtime_compat.py reference-path --skill <名称> '
            '--reference "<SKILL中原相对引用>" 查询真实存在的位置，再用read读取；不存在就报告缺项。'
            'GetNotes参考SDK的原缓存含跨平台开发依赖，从该skill的scripts目录可运行 '
            'getnote-tsx <tsx参数> 使用固定Linux兼容loader；这只修本地加载，不提供账号认证。'
            'agent-browser和lark-cli是通过exec运行的公共CLI，不是新增原生工具名；'
            'agent-browser使用本容器/usr/bin/chromium，外部Lark/邮件/GetNotes服务仍以实际认证结果为准。'
        ),
    }


def resolve_reference_path(workspace: Path, skill: str, reference: str) -> Path:
    skill=_skill_name(skill)
    if not reference or '\\' in reference or '\x00' in reference or PurePosixPath(reference).is_absolute():
        raise ValueError('reference must be a relative POSIX source path')
    workspace=workspace.resolve()
    # The caller must have this actual native skill; supporting context alone
    # never grants an active skill admission.
    _contained_file(workspace,workspace/'skills'/skill/'SKILL.md')
    direct=workspace/'skills'/skill/reference
    if direct.resolve().is_relative_to(workspace/'skills') and direct.is_file():
        return _contained_file(workspace,direct)
    for prefix,target in REFERENCE_TARGETS.get(skill,{}).items():
        if reference==prefix or prefix.endswith('/') and reference.startswith(prefix):
            suffix=reference[len(prefix):]
            if '..' in PurePosixPath(suffix).parts:
                raise ValueError('declared reference suffix must not escape its support directory')
            return _contained_file(workspace,workspace/(target+suffix))
    raise FileNotFoundError('No declared existing reference mapping for '+skill+': '+reference)


def skill_command_env(workspace: Path, skill: str, env: dict[str,str] | None = None) -> dict[str,str]:
    skill=_skill_name(skill)
    workspace=workspace.resolve()
    _contained_file(workspace,workspace/'skills'/skill/'SKILL.md')
    result=dict(os.environ if env is None else env)
    result.update(CLAUDE_PLUGIN_ROOT=str(workspace),CLAUDE_SKILL_DIR=str(workspace/'skills'/skill))
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',default='/workspace')
    sub=parser.add_subparsers(dest='mode',required=True)
    reference=sub.add_parser('reference-path')
    reference.add_argument('--skill',required=True)
    reference.add_argument('--reference',required=True)
    command=sub.add_parser('run-skill')
    command.add_argument('--skill',required=True)
    command.add_argument('argv',nargs=argparse.REMAINDER)
    args=parser.parse_args(argv)
    workspace=Path(args.workspace)
    if args.mode=='reference-path':
        print(str(resolve_reference_path(workspace,args.skill,args.reference)))
        return 0
    executable_args=args.argv[1:] if args.argv[:1]==['--'] else args.argv
    if not executable_args:
        parser.error('run-skill requires a command after --')
    return subprocess.run(executable_args,env=skill_command_env(workspace,args.skill),cwd=workspace).returncode


if __name__=='__main__':
    raise SystemExit(main())
