"""Verify a check-stage claim against the native trace and final package bytes."""

import hashlib
import json
import posixpath
import re
import shlex
from pathlib import PurePosixPath


WORKSPACE = '/workspace'
PACKAGE_ROOTS = {'inputs/candidate', 'outputs/skill'}
DECISION = 'outputs/evidence/decision.json'
EVENT_FILES = {
    'openclaw_transport/all_session_events.jsonl',
    'openclaw_transport/session_events.jsonl',
}
INSPECTION = set('''
    basename cat cd chmod cmp cp cut date diff dirname du echo env false file find grep
    head install jq-lint ln ls mkdir mv printenv printf pwd readlink realpath rm sed sha256sum
    sort stat tail tee test touch true uniq wc which xargs
'''.split())
SHELL_CONTROL = {';', ';;', '|', '|&', '||', '&', ';&', ';;&'}
NO_EXECUTION = {'--help', '-h', '--version', '--dry-run'}
RUNTIME_FAILURE = re.compile(
    r'Command exited with code [1-9]\d*|Traceback \(most recent call last\):|'
    r'(?:^|\n)\s*(?:SyntaxError:|Error: no export filter)', re.IGNORECASE
)


def _unverified(reason):
    return {'status': 'CHECK_UNVERIFIED', 'reason': reason}


def _ordinary_file(root, relative):
    if not isinstance(relative, str) or '\\' in relative:
        return None
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or '..' in path.parts or path.as_posix() != relative:
        return None
    for part in path.parts:
        root = root / part
        if root.is_symlink() or getattr(root, 'is_junction', lambda: False)():
            return None
    return root if root.is_file() else None


def _bound_file(helper, root, relative, digest):
    path = _ordinary_file(root, relative)
    if path is None or not isinstance(digest, str) or helper.digest(path) != digest:
        return None
    return path


def _native_actions(path):
    pending = {}
    with path.open(encoding='utf-8-sig') as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            event = record.get('native_event', record)
            message = event.get('message', {})
            session = (record.get('agent_id'), record.get('session_id'))
            if message.get('role') == 'assistant':
                for item in message.get('content') or ():
                    if isinstance(item, dict) and item.get('type') == 'toolCall' and item.get('id'):
                        key = (*session, item['id'])
                        pending[key] = item if key not in pending else None
            elif message.get('role') == 'toolResult':
                key = (*session, message.get('toolCallId'))
                call = pending.pop(key, None)
                if (call and call.get('name') == message.get('toolName')
                        and message.get('isError') is False and isinstance(call.get('arguments'), dict)):
                    yield line_number, call, message


def _segments(command, cwd):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    tokens = list(lexer)
    if any(token in SHELL_CONTROL for token in tokens):
        return
    words = []
    for token in (*tokens, '&&'):
        if token != '&&':
            words.append(token)
            continue
        if words[:1] == ['cd'] and len(words) == 2:
            cwd = posixpath.normpath(posixpath.join(cwd, words[1]))
        elif words:
            yield words, cwd
        words = []


def _path_spellings(cwd, relative):
    absolute = WORKSPACE + '/' + relative
    local = posixpath.relpath(absolute, cwd)
    return {absolute, local, './' + local}


def _mentions(words, cwd, relative):
    return any(re.search(r'(?<![\w./-])' + re.escape(value) + r'(?![\w./-])', word)
               for value in _path_spellings(cwd, relative) for word in words)


def _path_argument(words, cwd, relative):
    spellings = _path_spellings(cwd, relative)
    return any((word.partition('=')[2] if word.startswith('-') and '=' in word else word) in spellings
               for word in words)


def _functional_segment(words):
    while words and re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*=.*', words[0], re.DOTALL):
        words = words[1:]
    if not words or NO_EXECUTION.intersection(words):
        return False
    executable = posixpath.basename(words[0])
    return (executable not in INSPECTION and not words[0].startswith(('-', '$'))
            and not (executable in {'bash', 'sh', 'zsh'} and len(words) > 1
                     and re.fullmatch(r'-[a-zA-Z]*c[a-zA-Z]*', words[1])))


def _successful_exec(message):
    details = message.get('details')
    if (not isinstance(details, dict) or details.get('status') != 'completed'
            or type(details.get('exitCode')) is not int or details['exitCode'] != 0
            or details.get('exitSignal') or details.get('noOutputTimedOut')):
        return None
    output = details.get('aggregated')
    if not isinstance(output, str):
        output = '\n'.join(item['text'] for item in message.get('content') or ()
                           if isinstance(item, dict) and isinstance(item.get('text'), str))
    if RUNTIME_FAILURE.search(output):
        return None
    cwd = details.get('cwd')
    return (cwd if isinstance(cwd, str) and cwd.startswith('/') else WORKSPACE), output


def _stdout_matches(path, output):
    if not output.strip() or path.stat().st_size > 1024 * 1024:
        return False
    try:
        return path.read_text(encoding='utf-8-sig').rstrip('\n') == output.replace('\r\n', '\n').rstrip('\n')
    except UnicodeError:
        return False


def _write_targets(actions):
    for line, call, _ in actions:
        if call['name'] in {'write', 'edit'}:
            target = call['arguments'].get('path', call['arguments'].get('file_path'))
            if isinstance(target, str):
                yield line, posixpath.normpath(posixpath.join(WORKSPACE, target))


def check_evidence(helper, stage, outcome):
    """Return verified evidence for a completed check without executing a candidate."""
    if outcome.get('status') != 'CANDIDATE_PRESENT':
        return _unverified('CHECK_DID_NOT_SELECT_A_CANDIDATE')
    workspace = stage / 'workspace'
    package = outcome.get('package_root')
    files = outcome.get('skill_files')
    outputs = outcome.get('outputs')
    if (not isinstance(package, str) or package not in PACKAGE_ROOTS
            or not isinstance(files, dict) or not isinstance(outputs, dict)):
        return _unverified('MISSING_PACKAGE_OR_OUTPUT_BINDING')
    try:
        decision_path = _bound_file(helper, workspace, DECISION, outcome.get('decision_sha256'))
        if decision_path is None or outcome.get('decision_path') != DECISION:
            return _unverified('MISSING_BOUND_CHECK_DECISION')
        decision = helper.load(decision_path)
        tests = decision.get('tests') if isinstance(decision, dict) and decision.get('status') == 'KEEP' else None
        if not isinstance(tests, list) or not tests:
            return _unverified('MISSING_DECLARED_TESTS')
        event = outcome.get('native_events')
        if not isinstance(event, (list, tuple)) or len(event) != 2 or event[0] not in EVENT_FILES:
            return _unverified('MISSING_BOUND_NATIVE_EVENTS')
        event_path = _bound_file(helper, stage, *event)
        if event_path is None:
            return _unverified('NATIVE_EVENT_DIGEST_MISMATCH')
        homepage = _bound_file(helper, workspace, package + '/SKILL.md', files.get('SKILL.md'))
        if homepage is None or homepage.stat().st_size == 0:
            return _unverified('MISSING_BOUND_PACKAGE_HOMEPAGE')
        actions = list(_native_actions(event_path))
        writes = list(_write_targets(actions))
        package_prefix = WORKSPACE + '/' + package + '/'
        for test_index, test in enumerate(tests):
            if not isinstance(test, dict):
                continue
            command = test.get('command', test.get('usage'))
            evidence = test.get('evidence_path', test.get('evidence'))
            reported = test.get('result')
            if not isinstance(command, str) or not command.strip() or not isinstance(evidence, str) or not reported:
                continue
            if isinstance(reported, str) and re.match(r'\s*(?:fail(?:ed|ure)?\b|blocked\b|失败|未通过|未执行)', reported, re.I):
                continue
            evidence = evidence.removeprefix(WORKSPACE + '/').removeprefix('./')
            if evidence.startswith('evidence/'):
                evidence = 'outputs/' + evidence
            if evidence == DECISION or not evidence.startswith('outputs/evidence/'):
                continue
            digest = outputs.get(evidence.removeprefix('outputs/'))
            artifact = _bound_file(helper, workspace, evidence, digest)
            if artifact is None or artifact.stat().st_size == 0:
                continue
            evidence_authored = any(target == WORKSPACE + '/' + evidence for _, target in writes)
            for line, call, message in actions:
                executed = call['arguments'].get('command')
                if call['name'] != 'exec' or not isinstance(executed, str) or executed.strip() != command.strip():
                    continue
                result = _successful_exec(message)
                if result is None or any(i > line and path.startswith(package_prefix) for i, path in writes):
                    continue
                cwd, output = result
                try:
                    for words, directory in _segments(command, cwd):
                        if not _functional_segment(words):
                            continue
                        if ((evidence_authored or not _mentions(words, directory, evidence))
                                and not _stdout_matches(artifact, output)):
                            continue
                        arguments = [word for index, word in enumerate(words)
                                     if index == 0 or words[index - 1] not in {'>', '>>'}]
                        for resource in sorted(files, key=lambda name: name == 'SKILL.md'):
                            resource_digest = files[resource]
                            relative = package + '/' + resource
                            if (_path_argument(arguments, directory, relative)
                                    and _bound_file(helper, workspace, relative, resource_digest)):
                                return {'status': 'CHECK_VERIFIED', 'reason': 'BOUND_NATIVE_FUNCTIONAL_EXEC',
                                        'test_index': test_index, 'tool_call_id': call['id'],
                                        'native_result_line': line, 'native_events_sha256': event[1],
                                        'command_sha256': hashlib.sha256(command.strip().encode('utf-8')).hexdigest(),
                                        'package_resource': relative, 'package_resource_sha256': resource_digest,
                                        'evidence_path': evidence, 'evidence_sha256': digest}
                except ValueError:
                    continue
    except (AttributeError, OSError, TypeError, ValueError):
        return _unverified('INVALID_OR_UNREADABLE_CHECK_EVIDENCE')
    return _unverified('NO_MATCHED_NATIVE_FUNCTIONAL_TEST')
