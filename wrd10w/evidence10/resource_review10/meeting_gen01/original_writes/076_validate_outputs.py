#!/usr/bin/env python3
import json, os, re, hashlib

O = '/workspace/outputs'
errors = []

# 1. parse JSONs
for f in ['evidence.json', 'resource_manifest.json', 'replay.json']:
    try:
        json.load(open(os.path.join(O, f)))
        print('parse OK:', f)
    except Exception as e:
        errors.append(f'{f}: {e}')

ev = json.load(open(f'{O}/evidence.json'))
rm = json.load(open(f'{O}/resource_manifest.json'))
rp = json.load(open(f'{O}/replay.json'))

# 2. SKILL.md documented usage consistency
skill = open(f'{O}/candidate/skill/SKILL.md').read()
m = re.findall(r'python \{SKILL\}/scripts/apply_minutes_format\.py [^`\n]+', skill)
assert m, 'no command in SKILL.md'
doc_cmd = m[0].strip()
prog = rp['programs'][0]
print('documented_usage match:', doc_cmd == prog['documented_usage'])
if doc_cmd != prog['documented_usage']:
    errors.append('documented_usage mismatch')
print('SKILL.md bytes:', len(skill.encode()), 'chars:', len(skill))

# 3. resource paths exist
for r in rm['resources']:
    p = os.path.join(O, 'candidate/skill', r['path'])
    ok = os.path.isfile(p)
    print('resource exists:', r['path'], ok)
    if not ok: errors.append(f'missing {p}')

# 4. fixture pins match actual files
for fx in rp['fixtures']:
    p = os.path.join(O, fx['path'])
    h = hashlib.sha256(open(p,'rb').read()).hexdigest()
    b = os.path.getsize(p)
    ok = (h == fx['pin']['sha256'] and b == fx['pin']['bytes'])
    print('fixture pin ok:', fx['path'], ok)
    if not ok: errors.append(f'pin mismatch {p}')

# 5. evidence source ids bind all three route_card sources
ids = sorted(e['source_id'] for e in ev['source_evidence'])
print('evidence sources:', ids)
assert ids == ['conv_2ff337f34ddc', 'conv_ce34559870b8', 'conv_d640957a9820'], 'source coverage'

# 6. style reference content checks pass
ref = open(f'{O}/candidate/skill/references/minutes_style_reference.md').read()
for c in rp['non_executable_resources'][0]['content_checks']:
    print('ref contains:', c['value'], c['value'] in ref)
    if c['value'] not in ref: errors.append(f"ref missing {c['value']}")

# 7. outputs inventory
for root, dirs, files in os.walk(O):
    for fn in sorted(files):
        p = os.path.join(root, fn)
        print(os.path.relpath(p, O), os.path.getsize(p))

print('\nERRORS:', errors if errors else 'none')
