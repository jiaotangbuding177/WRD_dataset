import sys, json
from pathlib import PurePosixPath
import hashlib
def encoded(path):
    return hashlib.sha256(path.encode()).hexdigest()[:8]+'_'+PurePosixPath(path).name

def transform(item):
    seen=set();outputs=[]
    for p in item['paths']:
        q=PurePosixPath(p)
        if q.is_absolute() or '..' in q.parts:return {'outputs':[],'error':'UNSAFE_RELATIVE_PATH'}
        if p.casefold() in seen:return {'outputs':[],'error':'CASE_ALIAS_SOURCE'}
        seen.add(p.casefold());outputs.append({'source':p,'output':encoded(p)})
    return {'outputs':outputs,'error':None}

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
