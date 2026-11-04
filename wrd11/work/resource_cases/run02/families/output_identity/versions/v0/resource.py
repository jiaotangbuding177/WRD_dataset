import sys, json
from pathlib import PurePosixPath
import hashlib
def encoded(path):
    return hashlib.sha256(path.encode()).hexdigest()[:8]+'_'+PurePosixPath(path).name

def transform(item):
    outputs={}
    for p in item['paths']:outputs[PurePosixPath(p).name]={'source':p,'output':PurePosixPath(p).name}
    return {'outputs':list(outputs.values()),'error':None}

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
