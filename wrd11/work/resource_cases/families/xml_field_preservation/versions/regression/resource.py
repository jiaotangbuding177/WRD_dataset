import sys, json
import xml.etree.ElementTree as ET
import re
def summary(root):
    return {'visible_text':''.join(n.text or '' for n in root.iter('t')),
            'field_nodes':len(list(root.iter('fldChar'))),
            'instructions':[n.text or '' for n in root.iter('instrText')]}
def trim_prefix(nodes):
    text=''.join(n.text or '' for n in nodes)
    match=re.match(r'^\s*\d+[.、]\s*', text)
    left=match.end() if match else 0
    for n in nodes:
        old=n.text or ''; take=min(left,len(old));n.text=old[take:];left-=take

def transform(item):
    root=ET.fromstring(item['xml']);trim_prefix(root.findall('r/t'))
    return summary(root)

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
