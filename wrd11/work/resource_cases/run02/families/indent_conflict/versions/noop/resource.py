import sys, json
import xml.etree.ElementTree as ET
def start(item):
    root=ET.fromstring(item['xml']);ind=root.find('ind')
    if ind is None: ind=ET.SubElement(root,'ind')
    ind.set('firstLine',str(item['first_line_twips']))
    return root,ind

def transform(item):
    root,ind=start(item)
    return dict(ind.attrib)

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print(json.dumps([transform(x) for x in data], ensure_ascii=False, sort_keys=True))
