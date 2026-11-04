import sys, json
def transform(item):
    return [[row.get(k,None) or '' for k in item['columns']] for row in item['records']]

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
