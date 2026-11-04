import sys, json
def transform(item):
    return '<a href="'+item['url']+'">'+item['label']+'</a>'

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
