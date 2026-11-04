import sys, json
def walk(node, refs, lists=True):
    if isinstance(node, dict):
        if '$ref' in node: refs.add(node['$ref'])
        for value in node.values(): walk(value, refs, lists)
    elif lists and isinstance(node,list):
        for value in node: walk(value, refs, lists)
def answer(item, refs):
    return {'references':sorted(refs),'missing':sorted(refs-set(item['resources']))}

def transform(item):
    refs=set()
    if '$ref' in item['document']: refs.add(item['document']['$ref'])
    return answer(item,refs)

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
