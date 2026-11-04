import sys, json
def transform(item):
    return {'valid':True,'value':bool(item['value'])}

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
