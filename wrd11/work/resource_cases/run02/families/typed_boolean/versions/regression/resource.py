import sys, json
def transform(item):
    v=item['value']
    if isinstance(v,str):return {'valid':True,'value':v.strip().lower()=='true'}
    return {'valid':True,'value':bool(v)}

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
