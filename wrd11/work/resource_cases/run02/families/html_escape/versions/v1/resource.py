import sys, json
import html
from urllib.parse import urlsplit
def transform(item):
    label=html.escape(item['label'],quote=True)
    if urlsplit(item['url']).scheme.lower() not in ['http','https']:return '<span>'+label+'</span>'
    return '<a href="'+html.escape(item['url'],quote=True)+'">'+label+'</a>'

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
