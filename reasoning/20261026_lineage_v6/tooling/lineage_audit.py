"""Finite offline resource ancestry audit, preserving original226 isolation.

The graph separates availability, actual read observations, immutable resource
identity and producer ancestry.  Unknown producers are concrete HOLD reasons,
not proof of protected exposure.  No agent/model/tool loop is executed here.
"""
from collections import Counter, defaultdict
import ast
import gzip
import hashlib
import importlib.util
import json
import posixpath
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys

ROOT = Path('D:/skillloop')
BUNDLE = ROOT / 'output/20261025_wrd_training_dataset/bundle'
V5 = ROOT / 'output/20261026_wrd_strict226_expansion'
OUT = ROOT / 'output/20261026_wrd_lineage_v6'
RELEASE = ROOT / 'output/20261025_wrd_training_dataset/git_release'
COMMIT = '4cc8fdb9097c55a4b1fce84da6fc628f6d600ea3'
GIT_REPORT = 'reasoning/20261026_strict226/VISIBILITY_REVIEW.json'
SID = re.compile(r'conv_[a-f0-9]{12}')
ABS = re.compile(r'/workspace/[^\s\"\'<>`;,(){}\[\]]+')
READER = re.compile(r'\b(cat|head|tail|sed|grep|rg|open|read_text|read_bytes|json\.load)\b')
LISTER = re.compile(r'\b(ls|find|stat|wc)\b')
READ_NAMES = {'read', 'read_file', 'search', 'grep', 'view_image'}


def js(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
def h(v): return hashlib.sha256(v).hexdigest()
def hf(p):
    z = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): z.update(b)
    return z.hexdigest()
def rows(p):
    op = gzip.open if p.suffix == '.gz' else open
    with op(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip(): yield json.loads(line)
def dump_gz(p, values):
    with gzip.open(p, 'wt', encoding='utf-8', newline='\n') as f:
        for v in values: f.write(js(v) + '\n')
def object_path(row):
    p = BUNDLE / row['object']
    return p if p.exists() else BUNDLE / 'archive' / row['object']


def freeze():
    f = OUT / 'frozen'; f.mkdir(parents=True, exist_ok=True)
    gb = subprocess.check_output(['git', 'show', COMMIT + ':' + GIT_REPORT], cwd=RELEASE)
    gp = f / 'git_4cc8fdb_VISIBILITY_REVIEW.json'
    if gp.exists(): assert gp.read_bytes() == gb
    else: gp.write_bytes(gb)
    lp = f / 'local_v5_VISIBILITY_REVIEW.json'
    if not lp.exists(): shutil.copy2(V5 / 'VISIBILITY_REVIEW.json', lp)
    git = json.loads(gb); local = json.loads(lp.read_text(encoding='utf-8'))
    gi = set(git['pending_positive_candidate_episode_ids']); li = set(local['pending_positive_candidate_episode_ids'])
    assert len(gi) == 91 and gi == li, 'Fixed91 disagreement must not be silently replaced'
    files = {}
    for name in ('native_visibility_evidence.jsonl.gz', 'structured_decision_visibility_evidence.jsonl.gz'):
        dest = f / name
        if not dest.exists(): shutil.copy2(V5 / 'controlled' / name, dest)
        files[name] = {'path': str(dest.relative_to(OUT)), 'sha256': hf(dest)}
    result = {'git_commit': COMMIT, 'git_report_path': GIT_REPORT,
        'git_report_sha256': h(gb), 'local_report_sha256': hf(lp),
        'local_report_equals_git_bytes': gb == lp.read_bytes(),
        'fixed91_ids_equal': True, 'fixed91_episode_ids': sorted(gi),
        'local_additional_artifact_evidence_preserved_not_overwriting_git': True,
        'frozen_local_evidence': files}
    (f / 'FREEZE.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return gi, result


def module_v5():
    p = ROOT / 'research/data_prep/wrd_reasoning_v5/visibility_review.py'
    spec = importlib.util.spec_from_file_location('visibility_v5_readonly', p)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def source_ids(v): return set(SID.findall(js(v)))


def flat_source_roots(v, parser):
    body, metadata, pointers = set(), set(), set()
    for kind, ids, pointer, keys, record in parser.walk_records(v):
        if kind == 'source_body': body.update(ids)
        elif kind == 'source_record_path_pointer_availability_not_body': pointers.update(ids)
        else: metadata.update(ids)
    # Source-tagged judgments/prompts are derived business content even when
    # they use `reason`/`action` instead of an original conversation-body key.
    # Plain source inventory/pin/path rows are deliberately not promoted here.
    for pointer, obj in walk_dicts(v):
        tagged = parser.named(obj)
        if tagged and any(obj.get(k) for k in ('action','decision','reason','prompt','workflow','evidence_refs')):
            metadata.update(tagged)
    return body, metadata, pointers


def core_route(v):
    if not isinstance(v, dict) or not v.get('id'): return None
    wanted = ('id', 'name', 'category', 'source_ids', 'learning_source_ids',
        'development_source_ids', 'steps', 'reuse_reason', 'conditions',
        'additional_conditions', 'conflicts', 'route_signature', 'value_plan')
    if not all(k in v for k in ('id','name','category','source_ids','steps')): return None
    return {k: v[k] for k in wanted if k in v}


def walk_dicts(v, pointer=''):
    if isinstance(v, dict):
        yield pointer, v
        for k, c in v.items():
            if isinstance(c, (dict, list)): yield from walk_dicts(c, pointer + '/' + str(k))
    elif isinstance(v, list):
        for i, c in enumerate(v):
            if isinstance(c, (dict, list)): yield from walk_dicts(c, pointer + '/' + str(i))


def constant_paths(node, env):
    if isinstance(node, ast.Constant) and isinstance(node.value, str): return {node.value}
    if isinstance(node, ast.Name): return env.get(node.id, set())
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return set().union(*(constant_paths(x, env) for x in node.elts))
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Div)):
        left, right = constant_paths(node.left, env), constant_paths(node.right, env)
        return {(a + b) if isinstance(node.op, ast.Add) else posixpath.join(a, b) for a in left for b in right}
    if isinstance(node, ast.JoinedStr):
        values = {''}
        for x in node.values:
            part = constant_paths(x.value, env) if isinstance(x, ast.FormattedValue) else constant_paths(x, env)
            if not part: return set()
            values = {a + b for a in values for b in part}
            if len(values) > 128: return set()
        return values
    if isinstance(node, ast.Call):
        name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ''
        if name in {'Path', 'str', 'PurePosixPath'} and node.args: return constant_paths(node.args[0], env)
        if name == 'join' and node.args:
            vals = {''}
            for x in node.args:
                p = constant_paths(x, env)
                if not p: return set()
                vals = {posixpath.join(a, b) for a in vals for b in p}
            return vals
    return set()


def python_read_paths(source):
    try: tree = ast.parse(source)
    except SyntaxError: return set(), ['python source not statically parseable'], set()
    paths, unresolved, writepaths = set(), [], set(); env = {}
    def visit(nodes, scope):
        for n in nodes:
            if isinstance(n, (ast.Assign, ast.AnnAssign)):
                value = constant_paths(n.value, scope)
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                for target in targets:
                    if isinstance(target, ast.Name) and value: scope[target.id] = value
            if isinstance(n, ast.For):
                vals = constant_paths(n.iter, scope)
                if isinstance(n.target, ast.Name) and vals and len(vals) <= 128:
                    local = dict(scope); local[n.target.id] = vals; visit(n.body, local); visit(n.orelse, dict(scope)); continue
            for x in ast.walk(n):
                if not isinstance(x, ast.Call): continue
                fn = x.func.id if isinstance(x.func, ast.Name) else x.func.attr if isinstance(x.func, ast.Attribute) else ''
                if fn == 'open' and x.args:
                    mode = x.args[1].value if len(x.args) > 1 and isinstance(x.args[1], ast.Constant) else next(
                        (k.value.value for k in x.keywords if k.arg == 'mode' and isinstance(k.value, ast.Constant)), 'r')
                    values = constant_paths(x.args[0], scope)
                    writing = isinstance(mode, str) and any(c in mode for c in 'wax') and '+' not in mode
                    if writing: writepaths.update(values)
                    elif values: paths.update(values)
                    else: unresolved.append('dynamic Python open target: ' + ast.dump(x.args[0], include_attributes=False)[:160])
                elif fn in {'read_excel','read_csv','read_json','read_parquet','read_pickle','load_workbook',
                             'ExcelFile','PdfReader','Presentation','Document','ZipFile'} and x.args:
                    values = constant_paths(x.args[0],scope)
                    if values: paths.update(values)
                    else: unresolved.append('dynamic library business-file read target: '+ast.dump(x.args[0],include_attributes=False)[:160])
                elif fn in {'read_text', 'read_bytes'} and isinstance(x.func, ast.Attribute):
                    values = constant_paths(x.func.value, scope)
                    if values: paths.update(values)
                    else: unresolved.append('dynamic Python pathlib read target: ' + ast.dump(x.func.value, include_attributes=False)[:160])
            # ast.walk above handles if/with blocks; do not execute any code.
    visit(tree.body, env)
    return paths, sorted(set(unresolved)), writepaths


def actual_paths(call):
    args = call.get('arguments') or {}; name = call.get('name')
    if not isinstance(args, dict): return [], False, False, []
    command = str(args.get('command', args.get('cmd', '')))
    read = name in READ_NAMES
    listing = False
    if name in READ_NAMES:
        v = args.get('path', args.get('file_path', ''))
        return [v] if isinstance(v, str) and v else [], read, listing, []
    if name != 'exec': return [], False, False, []
    paths = set(); unresolved = []; writepaths = set()
    cwd = args.get('workdir', '/workspace')
    cd = re.search(r'\bcd\s+(/workspace/[^\s;&]+)', command)
    if cd: cwd = cd.group(1)
    sources = []
    heredoc = re.compile(r'\bpython(?:3)?[^\n]*<<\s*[\"\']?([A-Za-z_][A-Za-z_0-9]*)[\"\']?[^\n]*\n(.*?)\n\1(?:\n|$)', re.S)
    for match in heredoc.finditer(command): sources.append(match.group(2))
    shell = heredoc.sub(' python __HEREDOC__ ', command)
    try: tokens = shlex.split(shell, posix=True)
    except ValueError: tokens = []
    for i, token in enumerate(tokens):
        if re.fullmatch(r'python(?:3)?', token) and i + 2 < len(tokens) and tokens[i+1] == '-c':
            sources.append(tokens[i+2])
    for source in sources:
        pp, uu, ww = python_read_paths(source); paths.update(pp); unresolved.extend(uu); writepaths.update(ww)
    # Only operands of actual shell read commands count.  All workspace strings
    # inside Python writes, constants or f-string templates are not read targets.
    for part in re.split(r'&&|;|\n|\|', shell):
        try: ts = shlex.split(part, posix=True)
        except ValueError: continue
        if not ts: continue
        base = posixpath.basename(ts[0]); operands = []
        if base in {'cat', 'head', 'tail', 'sed', 'grep', 'rg'}:
            if base == 'cat' and any(t in {'>', '>>'} or t.startswith('>') for t in ts[1:]): continue
            operands = [t for t in ts[1:] if not t.startswith('-') and (t.startswith('/workspace/') or re.search(r'\.(jsonl?|txt|md|py|csv|xlsx|pdf)$', t))]
        elif re.fullmatch(r'python(?:3)?', base) and len(ts) > 1 and ts[1] != '-c' and ts[1].endswith('.py'):
            operands = [ts[1]]
        elif base in {'libreoffice','soffice','pandoc','pdftoppm','pdftotext','ffmpeg','convert','magick'}:
            operands = [t for t in ts[1:] if t.startswith(('/workspace/inputs/','/workspace/skills/'))]
        elif base in {'ls', 'find', 'stat', 'wc'}:
            listing = True
            # Listing operand paths are retained separately; they are not reads.
        paths.update(operands)
    paths = {posixpath.normpath(p if p.startswith('/') else str(cwd) + '/' + p) for p in paths}
    read = bool(paths or unresolved)
    return sorted(paths), read, listing, sorted(set(unresolved))


def empty_protocol(v):
    if v is None or v == [] or v == {}: return True
    # Only genuinely empty control values.  Business strings, explanations and
    # source ids never become generic just because their key sounds procedural.
    if isinstance(v, dict): return bool(v) and all(empty_protocol(x) for x in v.values())
    if isinstance(v, list): return all(empty_protocol(x) for x in v)
    return False


def main():
    OUT.mkdir(parents=True, exist_ok=True); controlled = OUT / 'controlled'; controlled.mkdir(exist_ok=True)
    old = OUT / 'history/initial_whole_episode_regex_ancestry'
    if (OUT / 'LINEAGE_AUDIT_REPORT.json').exists() and not old.exists():
        old.mkdir(parents=True)
        shutil.copy2(OUT / 'LINEAGE_AUDIT_REPORT.json', old / 'LINEAGE_AUDIT_REPORT.json')
        for p in controlled.glob('lineage*.gz'): shutil.copy2(p, old / p.name)
    if (OUT / 'LINEAGE_AUDIT_REPORT.json').exists():
        snapshot = OUT / 'history' / ('prior_' + hf(OUT / 'LINEAGE_AUDIT_REPORT.json')[:16])
        if not snapshot.exists():
            snapshot.mkdir(parents=True)
            shutil.copy2(OUT/'LINEAGE_AUDIT_REPORT.json',snapshot/'LINEAGE_AUDIT_REPORT.json')
            for p in controlled.glob('lineage*.gz'):shutil.copy2(p,snapshot/p.name)
    fixed91, freeze_report = freeze(); parser = module_v5()
    canonical = BUNDLE / 'canonical/native_episodes.jsonl.gz'
    episodes = {e['episode_id']: e for e in rows(canonical)}
    canonical_episode_ids=set(episodes)
    visibility = {r['episode_id']: r for r in rows(OUT / 'frozen/native_visibility_evidence.jsonl.gz')}
    labels_path = ROOT / 'output/20261025_wrd_reasoning_recovery_v4/controlled/native_source_split.labels.jsonl.gz'
    labels = {r['episode_id']: r for r in rows(labels_path)}
    jobs = {r['id']: r for r in rows(BUNDLE / 'catalog/jobs.jsonl')}
    protocol_code=ROOT/'research/workflow/stages.py'
    fixed_empty_material_protocols=set()
    for node in ast.walk(ast.parse(protocol_code.read_text(encoding='utf-8-sig'))):
        if isinstance(node,ast.Dict):
            try: literal=ast.literal_eval(node)
            except (ValueError,TypeError):continue
            if isinstance(literal,dict) and set(literal)=={'materials','rule'} and literal['materials']==[] and isinstance(literal['rule'],str):
                fixed_empty_material_protocols.add(h(js(literal).encode()))
    for node in ast.walk(ast.parse(protocol_code.read_text(encoding='utf-8-sig'))):
        if isinstance(node,ast.Dict):
            keys=[k.value if isinstance(k,ast.Constant) else None for k in node.keys]
            if set(keys)=={'materials','rule'}:
                rule=node.values[keys.index('rule')]
                if isinstance(rule,ast.Constant) and isinstance(rule.value,str):
                    fixed_empty_material_protocols.add(h(js({'materials':[],'rule':rule.value}).encode()))
    contracts = [p for p in (ROOT / 'benchmark').glob('*/contracts/evaluation.jsonl') if p.parent.parent.name in {
        'enterprise_split_v9_20261010', 'enterprise_input_closed_v11_20261012',
        'enterprise_original_inputs_v10_20261011', 'enterprise_final_delivery_v8_20261010'}]
    protected = {r['session_id'] for p in contracts for r in rows(p)}
    evo_path = ROOT / 'output/20261013_eval250_review/release/learning/evolution_index.jsonl'
    evolution = {r['source_id']: r for r in rows(evo_path) if r.get('logical_role') == 'evolution'}
    historical_path=ROOT/'output/20261025_wrd_reasoning_recovery_v4/controlled/historical_native_sessions.jsonl.gz'
    historical={r['episode_id']:r for r in rows(historical_path)}
    historical_roots=[]
    for eid,ep in historical.items():
        episodes[eid]=ep
        stub={'episode_id':eid,'kind':ep['kind'],'scope_label':'historical_producer_scope_requires_original_observation',
            'direct_formal_source_ids':[],'direct_source_ids':[],'evidence':[]}
        labels[eid]=stub
        visibility[eid]=parser.process_episode(ep,stub,protected,evolution)
        source_events=ep.get('source_events') or {}
        path=source_events.get('path') if isinstance(source_events,dict) else source_events
        if isinstance(path,str):
            normalized=path.replace('\\','/')
            suffix='/openclaw_transport/session_events.jsonl'
            if normalized.endswith(suffix):historical_roots.append((normalized[:-len(suffix)].lower(),eid))
    # Resource aliases are immutable evidence; final workspace output existence
    # alone does not certify that the model wrote that version or when it did.
    index_path = BUNDLE / 'archive/file_index.jsonl'
    inputs = defaultdict(dict); outputs_by_sha = defaultdict(list); source_material_aliases = defaultdict(list)
    output_json = []; resource_nodes = {}; file_count = 0
    for a in rows(index_path):
        logical = a['logical_path']; m = re.match(r'episodes/(ep_[^/]+)/workspace/(.+)', logical)
        if m is None and logical.startswith('history/'):
            sp=str(a.get('source_path','')).replace('\\','/')
            for source_root,he in historical_roots:
                if sp.lower().startswith(source_root+'/workspace/'):
                    tail=sp[len(source_root+'/workspace/'):]
                    m=re.match(r'(.*)',tail)
                    # Reuse the same path/index processing without relabeling
                    # the immutable history alias as a current native episode.
                    class HistoricalMatch:
                        def groups(self):return he,tail
                    m=HistoricalMatch();break
        if m:
            eid, tail = m.groups(); path = '/workspace/' + tail
            rec = {k: a[k] for k in ('logical_path', 'sha256', 'source_sha256', 'bytes', 'object','source_path')}
            rec['episode_id'] = eid; rec['native_path'] = path
            inputs[eid][path] = rec
            if tail.startswith('outputs/'):
                outputs_by_sha[a['sha256']].append(rec)
                if path.lower().endswith('.json') and a['bytes'] < 4000000: output_json.append(rec)
            file_count += 1
        elif logical.startswith('source_materials/'):
            source_material_aliases[logical].append({k: a[k] for k in ('logical_path', 'sha256', 'bytes', 'object')})
    source_materials_path = BUNDLE / 'catalog/source_materials.jsonl'
    material_roots = defaultdict(list)
    for s in rows(source_materials_path):
        for a in source_material_aliases.get(s.get('logical_path'), []):
            material_roots[a['sha256']].append({'source_id': s['source_id'], 'logical_path': s['logical_path'],
                'provenance_sha256': h(js(s.get('provenance')).encode()),
                'synthetic': (s.get('provenance') or {}).get('synthetic'),
                'historical_bytes_certified': (s.get('provenance') or {}).get('historical_bytes_certified')})
    # Actual assistant writes establish creators, with timestamp and successful
    # tool result.  Exec-generated outputs retain weaker snapshot creator edges.
    write_producers = defaultdict(list); route_producers = defaultdict(list)
    all_calls = {}; episode_refs = defaultdict(list); actual_edges = []; availability_edges = []
    for eid, ep in episodes.items():
        results = {m.get('toolCallId'): (i, m) for i, m in enumerate(ep['messages']) if m.get('role') in {'toolResult', 'tool'}}
        for mi, m in enumerate(ep['messages']):
            if m.get('role') != 'assistant' or not isinstance(m.get('content'), list): continue
            for bi, call in enumerate(m['content']):
                if not isinstance(call, dict) or call.get('type') != 'toolCall': continue
                args = call.get('arguments') or {}; result = results.get(call.get('id'))
                all_calls[(eid, call.get('id'))] = (mi, call, result)
                if call.get('name') == 'write' and isinstance(args, dict) and isinstance(args.get('content'), str):
                    body = args['content'].encode(); digest = h(body)
                    proof = {'episode_id': eid, 'native_message_index': mi, 'tool_call_id': call.get('id'),
                        'timestamp': m.get('timestamp'), 'native_path': args.get('path', args.get('file_path')),
                        'write_content_sha256': digest, 'assistant_message_sha256': h(js(m).encode()),
                        'tool_result_index': result[0] if result else None,
                        'tool_result_success': bool(result and not result[1].get('isError')),
                        'proof_kind': 'original_assistant_write_exact_content'}
                    write_producers[digest].append(proof)
                    try: value = json.loads(args['content'])
                    except ValueError: value = None
                    for pointer, obj in walk_dicts(value):
                        core = core_route(obj)
                        if core: route_producers[h(js(core).encode())].append({**proof, 'json_pointer': pointer,
                            'proof_kind': 'original_assistant_write_exact_route_core_projection',
                            'projection_fields': list(core)})
                paths, reading, listing, dynamic = actual_paths(call)
                if not reading and not listing: continue
                if dynamic and result and not result[1].get('isError'):
                    episode_refs[eid].append({'episode_id': eid, 'assistant_message_index': mi,
                        'tool_result_message_index': result[0], 'tool_call_id': call.get('id'),
                        'requested_path': '<dynamic Python read target>', 'timestamp': m.get('timestamp'),
                        'file_identity': None, 'dynamic_read_evidence': dynamic,
                        'tool_result_success': True})
                for path in paths:
                    if not path.startswith('/workspace/'):
                        # Explicit generic runtime/library reads are fixed
                        # protocol, not an unbounded business-source whitelist.
                        if path.startswith(('/usr/','/lib/','/opt/eval-adapter/','/opt/openclaw/','/proc/')) or path in {'/dev/null','/etc/os-release'}:
                            availability_edges.append({'episode_id':eid,'assistant_message_index':mi,
                                'requested_path':path,'relation':'fixed_runtime_protocol_read',
                                'initial_system_sha256':h(js(ep.get('system')).encode()),
                                'business_source_claimed':False})
                        elif reading and result and not result[1].get('isError'):
                            episode_refs[eid].append({'episode_id':eid,'assistant_message_index':mi,
                                'tool_result_message_index':result[0],'requested_path':path,
                                'timestamp':m.get('timestamp'),'file_identity':None,
                                'outside_proven_workspace_or_protocol':True,'tool_result_success':True})
                        continue
                    # Exact preserved input path, no wildcard expansion pretending
                    # all listed files were read or shown to the model.
                    alias = inputs.get(eid, {}).get(path)
                    edge = {'episode_id': eid, 'assistant_message_index': mi, 'tool_call_id': call.get('id'),
                        'tool_name': call.get('name'), 'requested_path': path,
                        'timestamp': m.get('timestamp'), 'assistant_message_sha256': h(js(m).encode()),
                        'tool_result_message_index': result[0] if result else None,
                        'tool_result_sha256': h(js(result[1]).encode()) if result else None,
                        'tool_result_success': bool(result and not result[1].get('isError')),
                        'read_operation_syntax_detected': reading, 'directory_metadata_only_operation': listing,
                        'file_identity': alias, 'glob_or_directory_not_expanded_as_visibility': '*' in path or alias is None,
                        'body_exported': False}
                    (actual_edges if reading else availability_edges).append(edge)
                    if reading and result and not result[1].get('isError'): episode_refs[eid].append(edge)
    # Snapshot-derived route producer matches are secondary to exact original
    # assistant writes.  They remain candidates until original trace time/write
    # is proven, rather than claiming a final file existed earlier.
    seen_output = set()
    for rec in output_json:
        key = (rec['episode_id'], rec['sha256'])
        if key in seen_output: continue
        seen_output.add(key); p = object_path(rec)
        if not p.exists(): continue
        try: value = json.loads(p.read_text(encoding='utf-8-sig'))
        except (ValueError, UnicodeError): continue
        for pointer, obj in walk_dicts(value):
            core = core_route(obj)
            if core:
                route_producers[h(js(core).encode())].append({'episode_id': rec['episode_id'],
                    'resource_sha256': rec['sha256'], 'logical_path': rec['logical_path'], 'json_pointer': pointer,
                    'proof_kind': 'snapshot_output_route_core_match_without_original_write_time'})
    independent_path = OUT / 'INDEPENDENT_NONMAKE_REVIEW.json'
    independent_route_facts = []
    independent_sha=None
    if independent_path.exists():
        independent_bytes=independent_path.read_bytes();independent_sha=h(independent_bytes)
        independent_frozen=OUT/'frozen'/('nonmake_'+independent_sha+'.json')
        if not independent_frozen.exists():independent_frozen.write_bytes(independent_bytes)
        independent = json.loads(independent_bytes)
        for consumer in independent['episodes']:
            eid = consumer['episode_id']; rec = inputs.get(eid,{}).get('/workspace/inputs/task_route.json')
            if rec is None: continue
            value = json.loads(object_path(rec).read_text(encoding='utf-8-sig')); core = core_route(value)
            if core is None: continue
            for match in consumer.get('upstream_route_record_matches',[]):
                if not match.get('all_consumer_brief_fields_match'): continue
                parent = match.get('producer_episode_id')
                for p in match.get('exact_record_in_actual_creation_call',[]):
                    if not p.get('created_before_consumer_first_message') or not p.get('successful_nonerror_result_recorded'): continue
                    fact = {'consumer_episode_id':eid,'producer_episode_id':parent,
                        'matching_record_sha256':match['record_sha256'],'source_alias':match['source_alias'],
                        'creation_message_index':p['assistant_native_message_index'],
                        'creation_message_sha256':p['assistant_message_sha256'],
                        'projection_fields':match['matching_fields'],
                        'independent_report_sha256':independent_sha}
                    independent_route_facts.append(fact)
                    if parent in episodes:
                        mi=p['assistant_native_message_index'];msg=episodes[parent]['messages'][mi]
                        assert h(js(msg).encode())==p['assistant_message_sha256']
                        route_producers[h(js(core).encode())].append({'episode_id':parent,'native_message_index':mi,
                            'assistant_message_sha256':p['assistant_message_sha256'],'timestamp':p['timestamp'],
                            'tool_result_success':True,'proof_kind':'independently_checked_exact_literal_brief_projection',
                            'independent_evidence':fact})
    resource_cache = {}; resource_details = []; verified_bytes = {}; decoded_features = {}
    def resource(edge):
        rec = edge.get('file_identity'); eid = edge['episode_id']; path = edge['requested_path']
        key = (eid, path, edge['assistant_message_index'])
        if key in resource_cache: return resource_cache[key]
        result = {'node_id': h((eid + '\n' + path + '\n' + str(edge['assistant_message_index'])).encode()),
            'episode_id': eid, 'native_path': path, 'consumer_assistant_message_index': edge['assistant_message_index'],
            'file_identity': rec, 'source_ids': [], 'protected_source_ids': [], 'producer_candidates': [],
            'terminal': None, 'specific_missing_evidence': [], 'body_exported': False}
        if rec is None:
            result['terminal'] = 'MISSING_EXACT_FILE_IDENTITY_FOR_ACTUAL_READ'
            result['specific_missing_evidence'].append('literal path is directory/glob/unpreserved or parser cannot resolve original read target')
        else:
            p = object_path(rec)
            if rec['sha256'] not in verified_bytes:
                verified_bytes[rec['sha256']] = p.exists() and hf(p) == rec['sha256']
            if not verified_bytes[rec['sha256']]:
                result['terminal'] = 'MISSING_OR_HASH_MISMATCHED_IMMUTABLE_BYTES'
            else:
                result['immutable_object_sha256_verified'] = True
                if rec['sha256'] not in decoded_features:
                    raw = p.read_bytes()
                    try: value = json.loads(raw.decode('utf-8-sig'))
                    except (UnicodeError, ValueError): value = None
                    decoded_features[rec['sha256']] = (value, *flat_source_roots(value, parser))
                value, bid, mid, pointer_ids = decoded_features[rec['sha256']]
                ids = bid | mid
                path_ids = set(SID.findall(path))
                result.update({'source_ids': sorted(ids), 'protected_source_ids': sorted(ids & protected),
                    'path_pointer_source_ids_not_body': sorted(pointer_ids), 'body_source_ids': sorted(bid)})
                if ids & protected:
                    result['terminal'] = 'PROTECTED_BUSINESS_RESOURCE_RECORD_OR_EXPLICIT_DERIVED_SOURCE'
                elif value is not None and h(js(value).encode()) in fixed_empty_material_protocols:
                    result['terminal']='CLOSED_EMPTY_MATERIALS_AND_EXACT_FIXED_PROTOCOL_RULE'
                    result['protocol_semantic_identity_proof']={'current_source_code_path':str(protocol_code.relative_to(ROOT)),
                        'source_code_sha256':hf(protocol_code),'literal_dictionary_matches_observed_resource':True,
                        'historical_executed_code_identity_claimed':False,'business_materials_empty':True}
                elif path.endswith('/reusable.json') and isinstance(value,list) and all(isinstance(v,dict) and
                    set(v)=={'id','name','path'} and isinstance(v['path'],str) and v['path'].startswith('/workspace/inputs/reusable/')
                    and not SID.fullmatch(str(v['id'])) for v in value):
                    result['terminal']='CLOSED_AVAILABLE_SKILL_PATH_INDEX_WITHOUT_SKILL_BODY'
                    result['index_availability_not_skill_content_or_producer_proof']=True
                elif value is not None and empty_protocol(value):
                    result['terminal'] = 'CLOSED_EMPTY_CONTROL_RESOURCE'
                elif bid and not mid and not (bid - set(evolution)):
                    # Root source packets must be preserved, explicitly bound to
                    # original sources; no arbitrary id-free business file passes.
                    if any(x in path for x in ('/conversations/', '/user_requests/', '/recall_catalog/sources/')) or path.endswith(('task_sources.json', 'sources.json')):
                        result['terminal'] = 'CLOSED_ALLOWED_ORIGINAL_SOURCE_PACKET'
                    else: result['terminal'] = 'MISSING_DERIVATION_OF_SOURCE_TAGGED_RESOURCE'
                elif material_roots.get(rec['sha256']):
                    bound = path_ids or set(labels[eid]['direct_source_ids']) or set(visibility[eid]['observed_source_body_ids'])
                    matching = [a for a in material_roots[rec['sha256']] if a['source_id'] in bound and
                        a['source_id'] in evolution and a['source_id'] not in protected]
                    if matching:
                        result['terminal'] = 'CLOSED_ALLOWED_SOURCE_SCOPED_MATERIAL'
                        result['source_material_roots'] = matching
                    else: result['terminal'] = 'MISSING_EXACT_SOURCE_SCOPED_MATERIAL_BINDING'
                else:
                    candidates = []
                    for prod in write_producers.get(rec['sha256'], []):
                        if prod['tool_result_success'] and isinstance(prod.get('timestamp'), (int, float)) and isinstance(edge.get('timestamp'), (int, float)) and prod['timestamp'] < edge['timestamp']:
                            candidates.append(prod)
                    core = core_route(value)
                    if core:
                        for prod in route_producers.get(h(js(core).encode()), []):
                            if prod['episode_id'] != eid or prod.get('native_message_index', 10**9) < edge['assistant_message_index']:
                                candidates.append(prod)
                        result['route_core_projection_sha256'] = h(js(core).encode())
                    result['producer_candidates'] = candidates
                    # A projected record match is a candidate, even when its
                    # writer saw protected context.  It is not the actual
                    # dispatch/creator identity.  Exact complete-file bytes with
                    # one prior original writer are a stronger identity edge.
                    time_proven = [p for p in candidates if
                        (p.get('proof_kind')=='original_assistant_write_exact_content' or
                         p.get('actual_dispatch_lineage_link_proven') is True) and
                        p.get('tool_result_success') and isinstance(p.get('timestamp'), (int, float)) and
                        isinstance(edge.get('timestamp'), (int, float)) and p['timestamp'] < edge['timestamp']]
                    unique = {(p['episode_id'], p['native_message_index']): p for p in time_proven}
                    if len(unique) == 1:
                        result['terminal'] = 'FOLLOW_EXACT_ORIGINAL_WRITE_PRODUCER'
                        result['proven_producer_prefixes'] = [{'episode_id': p['episode_id'],
                            'prefix_end_exclusive': p['native_message_index'] + 1,
                            'creation_message_index': p['native_message_index'],
                            'creation_message_sha256': p['assistant_message_sha256']} for p in unique.values()]
                    elif len(unique) > 1:
                        result['terminal'] = 'MISSING_UNIQUE_ACTUAL_PRODUCER_IDENTITY'
                        result['specific_missing_evidence'].append('same bytes/core match several original writes; require dispatch/version/source-copy link, not union contamination')
                    else:
                        result['terminal'] = 'MISSING_ACTUAL_ROUTE_RECORD_PRODUCER_IDENTITY' if core and candidates else 'MISSING_VERIFIED_BUSINESS_RESOURCE_PRODUCER'
                        result['specific_missing_evidence'].append('need exact original creator/write and earlier timestamp, or source-scoped input root; id absence and mutable route catalog are insufficient')
                    if core:
                        extras = {k:v for k,v in value.items() if k not in core}
                        catalog = extras.pop('full_catalog', None)
                        catalog_ok = catalog is None or (isinstance(catalog,dict) and set(catalog) <= {
                            'native_requests_path','native_materials_path','source_count','request_count'} and
                            all(isinstance(v,int) if k.endswith('_count') else isinstance(v,str) and
                                v.startswith('/workspace/inputs/recall_catalog/') for k,v in catalog.items()))
                        unresolved_fields = [k for k,v in extras.items() if not empty_protocol(v)]
                        if unresolved_fields or not catalog_ok:
                            result['terminal']='MISSING_ADDITIONAL_ROUTE_CONTEXT_PRODUCER'
                            result.pop('proven_producer_prefixes',None)
                            result['specific_missing_evidence'].append({'untraced_nonempty_extra_fields':unresolved_fields,
                                'catalog_is_typed_availability_metadata':catalog_ok})
                if path.endswith('.py') and result['terminal'] not in {'PROTECTED_BUSINESS_RESOURCE_RECORD_OR_EXPLICIT_DERIVED_SOURCE'}:
                    # Following the creator of a script does not by itself prove
                    # the runtime input files it reads.  Do not silently admit a
                    # pandas/CLI input hidden behind `python script.py`.
                    raw=object_path(rec).read_text(encoding='utf-8-sig',errors='replace')
                    runtime_paths,runtime_dynamic,_=python_read_paths(raw)
                    if runtime_paths or runtime_dynamic:
                        result['terminal']='MISSING_SCRIPT_RUNTIME_INPUT_DEPENDENCY_BINDING'
                        result.pop('proven_producer_prefixes',None)
                        result['specific_missing_evidence'].append({'static_runtime_read_paths':sorted(runtime_paths),
                            'dynamic_runtime_read_syntax':runtime_dynamic,
                            'needed':'bind script argv/cwd and original runtime file read or uniquely source-scoped immutable inputs'})
        resource_cache[key] = result; resource_details.append(result)
        return result
    # Concrete native observations can expose source content even when the tool
    # command's path cannot be resolved.  Preserve these positive source facts.
    local = {}
    def local_prefix(eid, end):
        if (eid, end) in local: return local[(eid, end)]
        ep = episodes[eid]
        vis = visibility[eid]; proof = []; missing = []; ancestry = set(); rnodes = []
        direct_protected = set().union(*(set(p['formal_source_ids']) for p in labels[eid]['evidence'] if
            p['direct_source_payload'] and p['type'] != 'model_observed_user_or_tool_source_content'))
        if ep.get('role_scope')=='formal_task_identity_exclude':
            direct_protected.add('FORMAL_EVALUATION_TASK_IDENTITY:'+str(ep.get('job_id')))
        # Actual observed derived source metadata is a declared resource edge;
        # it is not called a verbatim original-body exposure.
        observed_sources = set()
        source_binding_proof = []
        job = jobs.get(ep.get('job_id')) or {}; payload = job.get('payload') or {}
        case = payload.get('case') or {}
        initial_user = '\n'.join(t for m in ep['messages'][:1] for bi,t in parser.texts(m))
        if isinstance(case,dict) and isinstance(case.get('prompt'),str) and case['prompt'] and case['prompt'] in initial_user:
            observed_sources.update(parser.named(case))
            source_binding_proof.append({'reason':'EXACT_SELECTED_CASE_PROMPT_IN_ORIGINAL_INITIAL_USER',
                'case_prompt_sha256':h(case['prompt'].encode()),'job_id':ep.get('job_id'),
                'catalog_job_sha256':h(js(job).encode()),'initial_user_sha256':h(initial_user.encode())})
        for o in vis['observations']:
            if o['native_message_index'] >= end: continue
            if o['kind'] == 'source_body': observed_sources.update(o['source_ids']); direct_protected.update(o['protected_source_ids'])
            elif o['kind'] != 'source_record_path_pointer_availability_not_body': direct_protected.update(o['protected_source_ids'])
        for edge in episode_refs[eid]:
            if edge['assistant_message_index'] >= end or edge['tool_result_message_index'] >= end: continue
            rr = resource(edge); rnodes.append(rr['node_id'])
            if rr['terminal'].startswith('PROTECTED_'): direct_protected.update(rr['protected_source_ids'])
            elif rr['terminal'] == 'FOLLOW_EXACT_ORIGINAL_WRITE_PRODUCER': ancestry.update(
                (p['episode_id'], p['prefix_end_exclusive']) for p in rr['proven_producer_prefixes'])
            elif rr['terminal'].startswith('MISSING_'):
                missing.append({'reason': rr['terminal'], 'resource_node_id': rr['node_id'],
                    'native_path': rr['native_path'], 'assistant_message_index': edge['assistant_message_index'],
                    'tool_result_message_index': edge['tool_result_message_index']})
            else: proof.append({'reason': rr['terminal'], 'resource_node_id': rr['node_id']})
        if not observed_sources and not labels[eid]['direct_source_ids']:
            missing.append({'reason': 'NO_POSITIVE_ALLOWED_ORIGINAL_SOURCE_BINDING_FOR_EPISODE'})
        if any(s not in evolution for s in observed_sources):
            missing.append({'reason': 'OBSERVED_SOURCE_NOT_IN_FROZEN_EVOLUTION_INDEX',
                'source_ids': sorted(s for s in observed_sources if s not in evolution)})
        # Unparsed user inventory paths are availability only.  Unstructured tool
        # observations with protected ids still need exact source/view resolution.
        for o in vis['unparsed_or_unstructured_protected_identifier_index']:
            if o['native_message_index'] < end and o['role'] != 'user': missing.append({'reason': 'UNRESOLVED_PROTECTED_IDENTIFIER_IN_ACTUAL_TOOL_OBSERVATION',
                'native_message_index': o['native_message_index'], 'native_message_sha256': o['native_message_sha256']})
        local[(eid, end)] = {'episode_id': eid, 'kind': ep['kind'], 'fixed91_member': eid in fixed91,
            'native_verified': ep.get('native_verified'), 'canonical_episode_sha256': h(js(ep).encode()),
            'observed_allowed_source_ids': sorted(observed_sources - protected),
            'observed_evolution_source_ids': sorted(observed_sources - protected),
            'initial_case_source_binding_proof':source_binding_proof,
            'direct_protected_source_ids': sorted(direct_protected), 'local_missing_evidence': missing,
            'local_closed_roots': proof, 'direct_producer_prefixes': [list(x) for x in sorted(ancestry)],
            'resource_node_ids': sorted(set(rnodes)), 'native_message_range': [0, end]}
        return local[(eid, end)]
    final = {}; visiting = set()
    def close(eid, end):
        key = (eid, end)
        if key in final: return final[key]
        r = local_prefix(eid, end)
        if key in visiting:
            return {'status': 'HOLD_MISSING_EVIDENCE', 'resource_closure_proven': False,
                'protected_ancestor_present': False, 'blocking_evidence': [{'reason': 'ANCESTRY_CYCLE_WITHOUT_EXTERNAL_ROOT'}],
                'ancestor_episode_ids': []}
        visiting.add(key); ancestors = set(); blocking = list(r['local_missing_evidence'])
        protected_found = bool(r['direct_protected_source_ids'])
        for parent, prefix_end in r['direct_producer_prefixes']:
            pr = close(parent, prefix_end); ancestors.add(parent); ancestors.update(pr['ancestor_episode_ids'])
            if pr['protected_ancestor_present']: protected_found = True
            if pr['status'] != 'ADMIT': blocking.append({'reason': 'UPSTREAM_PRODUCER_NOT_CLOSED',
                'producer_episode_id': parent, 'producer_prefix_end_exclusive': prefix_end, 'producer_status': pr['status']})
        visiting.remove(key)
        status = 'HOLD_PROTECTED' if protected_found else 'HOLD_MISSING_EVIDENCE' if blocking else 'ADMIT'
        result = {**r, 'status': status, 'resource_closure_proven': status == 'ADMIT',
            'protected_ancestor_present': protected_found, 'blocking_evidence': blocking,
            'ancestor_episode_ids': sorted(ancestors), 'evidence_refs': ['controlled/lineage_resources.jsonl.gz',
                'controlled/lineage_actual_read_edges.jsonl.gz', 'frozen/native_visibility_evidence.jsonl.gz'],
            'source_scope_admission_only_not_semantic_gold': True, 'training_started': False}
        final[key] = result; return result
    full = {eid: close(eid, len(episodes[eid]['messages'])) for eid in sorted(canonical_episode_ids)}
    paths = {
        'episodes': controlled / 'lineage_episode_decisions.jsonl.gz',
        'resources': controlled / 'lineage_resources.jsonl.gz',
        'actual_reads': controlled / 'lineage_actual_read_edges.jsonl.gz',
        'producer_prefixes': controlled / 'lineage_producer_prefix_decisions.jsonl.gz',
        'availability': controlled / 'lineage_availability_edges.jsonl.gz'}
    paths['independent_route_projection_facts'] = controlled / 'lineage_independent_route_projection_facts.jsonl.gz'
    dump_gz(paths['episodes'], (full[k] for k in sorted(full)))
    dump_gz(paths['producer_prefixes'], (final[k] for k in sorted(final)))
    dump_gz(paths['resources'], resource_details)
    dump_gz(paths['actual_reads'], actual_edges)
    dump_gz(paths['availability'], availability_edges)
    dump_gz(paths['independent_route_projection_facts'],independent_route_facts)
    selected = [full[e] for e in sorted(fixed91)]
    candidate_pool = {e for e, lab in labels.items() if lab['scope_label'] == 'confirmed_evolution_direct_source_scope'}
    report = {'schema_version': 'wrd-finite-actual-resource-lineage-v6',
        'status': 'FINITE_LOGGED_INPUT_AND_BUSINESS_RESOURCE_ANCESTRY_AUDIT',
        'fixed91_freeze': freeze_report, 'fixed91_terminal_counts': dict(Counter(r['status'] for r in selected)),
        'fixed91_by_stage': {k: dict(Counter(r['status'] for r in selected if r['kind'] == k)) for k in sorted({r['kind'] for r in selected})},
        'fixed91_specific_missing_evidence': dict(Counter(b['reason'] for r in selected for b in r['blocking_evidence'])),
        'all_native_episode_counts': dict(Counter(r['status'] for r in full.values())),
        'historical_native_producer_sessions_indexed':len(historical),
        'prior_direct_source_pool_counts': dict(Counter(full[e]['status'] for e in candidate_pool)),
        'indexed_episode_workspace_aliases': file_count, 'actual_read_path_edges': len(actual_edges),
        'availability_listing_edges_not_body': len(availability_edges), 'resource_nodes': len(resource_details),
        'resource_terminal_counts': dict(Counter(r['terminal'] for r in resource_details)),
        'source_body_scope_is_not_file_identity_or_resource_producer_proof': True,
        'fixed_empty_material_protocol_literals':len(fixed_empty_material_protocols),
        'fixed_empty_material_protocol_source_sha256':hf(protocol_code),
        'no_latent_teacher_memory_assumption_or_infinite_ancestry_required': True,
        'protected_original226_count': len(protected), 'new_model_calls': 0, 'new_native_business_runs': 0,
        'training_started': False, 'original_files_mutated': False,
        'limitations': ['Source admission is separate from outcome/semantic-silver quality and model training readiness.',
            'Literal read target extraction is bounded; unresolved paths/globs/filtered catalog queries retain concrete HOLD reasons.',
            'Snapshot output aliases alone are not proof of creator or creation time.',
            'No source-id match is not a whitelist; generic empty control resources are distinguished from arbitrary id-free business text.',
            'Protocol/model/system templates are recorded in the original canonical episode; this audit does not require unverifiable latent teacher history.'],
        'source_sha256': {str(p.relative_to(ROOT)): hf(p) for p in [canonical,historical_path,index_path,labels_path,source_materials_path,evo_path,*contracts]},
        'independent_route_projection_report_sha256':independent_sha,
        'earlier_regex_whole_episode_graph_superseded_and_preserved':True,
        'artifacts': [{'path': str(p.relative_to(OUT)), 'sha256': hf(p), 'bytes': p.stat().st_size} for p in paths.values()],
        'script_sha256': hf(Path(__file__))}
    (OUT / 'LINEAGE_AUDIT_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('fixed91_terminal_counts', 'fixed91_by_stage',
        'fixed91_specific_missing_evidence', 'all_native_episode_counts', 'prior_direct_source_pool_counts', 'resource_terminal_counts')}, ensure_ascii=False))


if __name__ == '__main__': main()
