import sys, json
def transform(item):
    v=item['value']
    if type(v) is bool:return {'valid':True,'value':v}
    if type(v) is int and v in [0,1]:return {'valid':True,'value':v==1}
    if isinstance(v,str) and v.strip().lower() in ['true','false']:return {'valid':True,'value':v.strip().lower()=='true'}
    return {'valid':False,'value':None}

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
