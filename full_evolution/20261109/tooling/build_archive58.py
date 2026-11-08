"""Freeze material bytes into a reproducible tar.gz and <=16 MiB Git entities."""
import argparse, gzip, hashlib, json, tarfile
from pathlib import Path

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--corpus',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);p.add_argument('--entities',type=Path,required=True);p.add_argument('--subset',choices=['all','objects','records'],default='all');a=p.parse_args()
    a.archive.parent.mkdir(parents=True,exist_ok=True);a.entities.mkdir(parents=True,exist_ok=True)
    files=sorted(x for x in a.corpus.rglob('*') if x.is_file())
    if a.subset=='objects':files=[x for x in files if x.relative_to(a.corpus).parts[0]=='objects']
    if a.subset=='records':files=[x for x in files if x.relative_to(a.corpus).parts[0]!='objects']
    with a.archive.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',compresslevel=6,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w|',format=tarfile.PAX_FORMAT) as tar:
        for x in files:
            if x.is_symlink():raise ValueError('Archive cannot include symlink')
            info=tar.gettarinfo(str(x),arcname='corpus/'+x.relative_to(a.corpus).as_posix());info.mtime=0;info.uid=0;info.gid=0;info.uname='';info.gname='';info.mode=0o644
            with x.open('rb') as src:tar.addfile(info,src)
    parts=[]
    with a.archive.open('rb') as src:
        while chunk:=src.read(16*1024*1024):
            name='part-'+str(len(parts)+1).zfill(4)+'.bin';q=a.entities/name;q.write_bytes(chunk)
            parts.append({'path':name,'bytes':len(chunk),'sha256':hashlib.sha256(chunk).hexdigest()})
    d={'schema':'wrd58-full-evolution-git-volumes-v1','subset':a.subset,'archive_name':a.archive.name,'archive_bytes':a.archive.stat().st_size,'archive_sha256':sha(a.archive),'corpus_files':len(files),'corpus_bytes':sum(x.stat().st_size for x in files),'part_bytes_limit':16*1024*1024,'parts':parts,'encrypted':False,'restore':'python tooling/restore_corpus58.py --delivery DELIVERY.json --out restored/corpus'}
    (a.entities/'PARTS.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in d.items() if k!='parts'}|{'parts':len(parts)}))

if __name__=='__main__':main()
