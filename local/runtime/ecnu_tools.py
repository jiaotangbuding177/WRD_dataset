"""Explicit media API clients for the configured experimental ECNU account."""
import argparse
import base64
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import time
import urllib.request
import urllib.error


def request(cfg,path,body):
    req=urllib.request.Request(cfg['base_url'].rstrip('/')+path,data=json.dumps(body).encode(),
        headers={'Authorization':'Bearer '+cfg['api_key'],'Content-Type':'application/json'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req,timeout=180) as response:
            return response.headers.get('Content-Type',''),response.read()
    except urllib.error.HTTPError as exc:
        detail=exc.read().decode(errors='replace').replace(cfg['api_key'],'[REDACTED]')
        raise RuntimeError(f'ECNU HTTP {exc.code}: {detail[:2000]}') from None


def execute(command,text,output,credentials='/run/secrets/model.json',image_path=None):
    cfg=json.loads(Path(credentials).read_text(encoding='utf-8-sig'));out=Path(output)
    out.parent.mkdir(parents=True,exist_ok=True);start=time.monotonic()
    if out.exists(): raise ValueError('Output already exists; choose a fresh path')
    if command=='image':
        model='ecnu-image';content_type,body=request(cfg,'/images/generations',{'model':model,'prompt':text,'size':'512x512','response_format':'b64_json'})
        result=json.loads(body)
        if result.get('err_message'):raise RuntimeError(result['err_message'])
        rows=result.get('data',[])
        if not rows or not rows[0].get('b64_json'):raise RuntimeError('Image endpoint did not return requested b64_json')
        out.write_bytes(base64.b64decode(rows[0]['b64_json'],validate=True))
        receipt={'model':model,'content_type':content_type,'provider_created':result.get('created'),'revised_prompt':rows[0].get('revised_prompt')}
    elif command=='speech':
        model='ecnu-tts';fmt=out.suffix.lstrip('.') or 'wav'
        content_type,body=request(cfg,'/audio/speech',{'model':model,'input':text,'voice':'xiayu','response_format':fmt,'speed':1})
        if 'json' in content_type or len(body)<128:raise RuntimeError('TTS endpoint did not return usable audio bytes')
        out.write_bytes(body);receipt={'model':model,'content_type':content_type}
    elif command=='vision':
        image=Path(image_path);mime=mimetypes.guess_type(image.name)[0] or 'image/png'
        payload={'model':cfg['model'],'messages':[{'role':'user','content':[{'type':'text','text':text},
          {'type':'image_url','image_url':{'url':'data:'+mime+';base64,'+base64.b64encode(image.read_bytes()).decode()}}]}],
          'max_tokens':2048,'temperature':0}
        _,body=request(cfg,'/chat/completions',payload);result=json.loads(body)
        answer=result['choices'][0]['message']['content'];out.write_text(answer,encoding='utf-8')
        receipt={'model':result.get('model'),'requested_model':cfg['model'],'usage':result.get('usage')}
    else:raise ValueError('Unsupported tool command')
    receipt.update(command=command,output=str(out),bytes=out.stat().st_size,
                   sha256=hashlib.sha256(out.read_bytes()).hexdigest(),seconds=time.monotonic()-start)
    out.with_suffix(out.suffix+'.receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['image','speech','vision']);p.add_argument('--text',required=True)
    p.add_argument('--output',required=True);p.add_argument('--credentials',default='/run/secrets/model.json');p.add_argument('--image-path')
    a=p.parse_args();print(json.dumps(execute(a.command,a.text,a.output,a.credentials,a.image_path),ensure_ascii=False))
