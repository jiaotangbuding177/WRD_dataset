import sys, json
def bucket(records, classifier):
    result={'fact':[],'plan':[],'uncertain':[]}
    for row in records:
        group=classifier(row)
        result[group].append({'id':row['id'],'text':row['text']})
    return result

def transform(item):
    return bucket(item['records'],lambda row:'fact')

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
