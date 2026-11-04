import json
fb = json.load(open('inputs/validation_feedback.json', encoding='utf-8'))
# print top-level structure and the failing parts
def walk(o, prefix=''):
    if isinstance(o, dict):
        for k,v in o.items():
            walk(v, prefix+'/'+k)
    elif isinstance(o, list):
        print(prefix, f'[list len={len(o)}]')
    else:
        s = str(o)
        print(prefix, ':', s[:200])
walk(fb)