"""Restore complete WRD evolution materials from ordinary Git binary volumes."""
import argparse, hashlib, json, os, shutil, tarfile, tempfile
from pathlib import Path, PurePosixPath

def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def verify(root):
    hashes=root/'SHA256SUMS'
    if not hashes.is_file():raise ValueError('Corpus SHA256SUMS missing')
    count=0;total=0
    for line in hashes.read_text(encoding='utf-8').splitlines():
        if not line:continue
        expected,name=line.split('  ',1);rel=PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe manifest path')
        p=root.joinpath(*rel.parts)
        if not p.is_file() or digest(p)!=expected:raise ValueError('Corpus member differs: '+name)
        count+=1;total+=p.stat().st_size
    return {'status':'PASS','verified_members':count,'verified_bytes':total}

def restore(parts_path,out,allow_existing=False,defer_verify=False):
    d=json.loads(parts_path.read_text(encoding='utf-8'))
    if out.exists() and not allow_existing:raise FileExistsError('Restore destination must be new; use --verify-only for an existing corpus')
    out.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='wrd58-restore-',suffix='.tar.gz',dir=out.parent);os.close(fd)
    archive=Path(name);complete=hashlib.sha256();size=0
    try:
        with archive.open('wb') as joined:
            for item in d['parts']:
                rel=PurePosixPath(item['path'])
                if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe part path')
                p=parts_path.parent.joinpath(*rel.parts)
                if p.stat().st_size!=item['bytes'] or digest(p)!=item['sha256']:raise ValueError('Part SHA mismatch: '+item['path'])
                with p.open('rb') as src:
                    while chunk:=src.read(4*1024*1024):joined.write(chunk);complete.update(chunk);size+=len(chunk)
        if complete.hexdigest()!=d['archive_sha256'] or size!=d['archive_bytes']:raise ValueError('Joined archive SHA mismatch')
        out.mkdir(exist_ok=allow_existing)
        with tarfile.open(archive,'r|gz') as tar:
            for member in tar:
                rel=PurePosixPath(member.name)
                if rel.is_absolute() or '..' in rel.parts or not rel.parts or rel.parts[0]!='corpus' or not member.isfile():
                    raise ValueError('Unexpected archive member')
                target=out.joinpath(*rel.parts[1:]);target.parent.mkdir(parents=True,exist_ok=True)
                with tar.extractfile(member) as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
        return ({} if defer_verify else verify(out))|{'archive_sha256':d['archive_sha256'],'archive_bytes':size,'parts':len(d['parts'])}
    finally:archive.unlink(missing_ok=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parts',type=Path);p.add_argument('--delivery',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    if a.verify_only:r=verify(a.out)
    elif a.delivery:
        d=json.loads(a.delivery.read_text(encoding='utf-8'));layers=[]
        for i,item in enumerate(d['archives']):
            path=a.delivery.parent/item['parts_manifest']
            if digest(path)!=item['parts_manifest_sha256']:raise ValueError('Delivery parts manifest differs')
            layers.append(restore(path,a.out,allow_existing=i>0,defer_verify=True))
        r=verify(a.out)|{'layers':layers}
    else:r=restore(a.parts,a.out)
    print(json.dumps(r,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
