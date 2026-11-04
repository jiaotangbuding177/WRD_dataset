import json, re, sys, urllib.parse, urllib.request
def search(q):
    url = 'https://www.youtube.com/results?search_query=' + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36','Accept-Language':'en-US,en;q=0.9'})
    html = urllib.request.urlopen(req, timeout=25).read().decode('utf-8','ignore')
    m = re.search(r'var ytInitialData = (\{.*?\});</script>', html)
    data = json.loads(m.group(1)) if m else None
    out = {}
    def walk(o):
        if isinstance(o, dict):
            if 'videoRenderer' in o:
                v = o['videoRenderer']
                vid = v.get('videoId')
                if vid and vid not in out:
                    title = ''.join(r.get('text','') for r in v.get('title',{}).get('runs',[]))
                    ch = ''.join(r.get('text','') for r in v.get('ownerText',{}).get('runs',[]))
                    dur = v.get('lengthText',{}).get('simpleText','')
                    views = v.get('viewCountText',{}).get('simpleText','')
                    pub = v.get('publishedTimeText',{}).get('simpleText','')
                    out[vid] = {'id':vid,'title':title,'channel':ch,'duration':dur,'views':views,'published':pub}
            for vv in o.values(): walk(vv)
        elif isinstance(o, list):
            for vv in o: walk(vv)
    if data: walk(data)
    return list(out.values())
for q in sys.argv[1:]:
    print('### QUERY:', q)
    for r in search(q)[:10]:
        print(json.dumps(r, ensure_ascii=False))
    print()
