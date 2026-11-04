"""Build deterministic local AI-review units. Never runs source tools/models.

Raw excerpts stay in the local work directory. Review is evidence-scoped and
must not be described as human approval or complete trajectory validation.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def stable(row):
    return hashlib.sha256(('wrd-preflight-review42:' + row['id']).encode()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    items = list(rows(a.bundle/'datasets/native_actions_core7.train.jsonl.gz'))
    strong = {x['id'] for x in rows(a.bundle/'datasets/artifact_verified_write.train.jsonl.gz')
              if x.get('schema_version') == 'wrd-openai-tool-completion-v1'}
    by = defaultdict(list)
    for row in items:
        by[row['kind']].append(row)
    selected = {}
    for kind, size in [('screen', 100), ('make', 200)]:
        candidates = sorted(by[kind], key=stable)
        chosen = {r['id']:r for r in candidates if r['id'] in strong or
                  (kind=='screen' and any(c['function']['name']=='write' for m in r['completion'] for c in m.get('tool_calls', [])))}
        # Cover tool types, then actual route strata before deterministic fill.
        for tool in ['ls', 'read', 'edit', 'write', 'apply_patch', 'exec', 'process']:
            matching = [r for r in candidates if tool in r.get('tool_call_names', [])]
            if matching and not any(tool in r.get('tool_call_names', []) for r in chosen.values()):
                chosen[matching[0]['id']] = matching[0]
        route_groups = defaultdict(list)
        for r in candidates:
            route_groups[r.get('route_id') or '<none>'].append(r)
        for route in sorted(route_groups):
            if len(chosen)>=size:
                break
            if not any((r.get('route_id') or '<none>')==route for r in chosen.values()):
                r=route_groups[route][0];chosen[r['id']]=r
        for r in candidates:
            if len(chosen)>=size:
                break
            chosen[r['id']]=r
        assert len(chosen)==size
        selected[kind] = sorted(chosen.values(), key=stable)
    assert strong.issubset({r['id'] for r in selected['make']})
    groups = {'screen':selected['screen'], 'make_a':selected['make'][:100], 'make_b':selected['make'][100:]}
    result = {}
    for group, rs in groups.items():
        path=a.output/(group+'.jsonl')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w',encoding='utf-8',newline='\n') as f:
            for r in rs:
                user = [m for m in r['prompt'] if m.get('role')=='user']
                last = r['prompt'][-3:]
                # This view is for triage. The full row can be inspected by ID.
                view = {'id':r['id'], 'kind':r['kind'], 'route_id':r.get('route_id'),
                        'tools':r.get('tool_call_names'), 'artifact_identical_subset':r['id'] in strong,
                        'target_sha256':hashlib.sha256(json.dumps(r['completion'],ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
                        'user_messages':user, 'last_context_messages':last,
                        'completion':r['completion'], 'full_prompt_messages':len(r['prompt']),
                        'scope':'actual user messages, last three observations and full current target; earlier evidence requires full-row lookup',
                        'not_human_gold':True}
                f.write(json.dumps(view,ensure_ascii=False,separators=(',',':'))+'\n')
        result[group]={'rows':len(rs),'local_file':str(path),'ids':[r['id'] for r in rs],
                       'tools':dict(Counter(t for r in rs for t in r.get('tool_call_names',[])))}
    dump(a.output/'selection.json',{'schema_version':'wrd-review-selection-v1','groups':result,
                                  'strong_standard_subset':len(strong),'human_gold':0,
                                  'selection_is_not_semantic_approval':True})
    print(json.dumps({'status':'SELECTED_NOT_REVIEWED','counts':{k:v['rows'] for k,v in result.items()},
                      'strong_standard_subset':len(strong)},ensure_ascii=True))


if __name__=='__main__':main()
