"""Authenticate delta07 against the exact merged06 root; copy explicit files only."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, importlib.util, json, shutil
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def safe(root,name):
    q=PurePosixPath(name)
    assert not q.is_absolute() and '..' not in q.parts and '\\' not in name
    p=Path(root).joinpath(*q.parts)
    assert p.resolve().is_relative_to(Path(root).resolve())
    return p
def validate_refs(refs):
    assert isinstance(refs,list)
    seen={}
    reserved={'PAYLOAD_MANIFEST.json','MERGE_RESULT.json',
        'merge_evidence/merged06_authenticated_manifest.json',
        'merge_evidence/delta07_authenticated_manifest.json'}
    for ref in refs:
        n=ref['path'];q=PurePosixPath(n)
        assert isinstance(n,str) and n and q.parts and q.as_posix()==n
        assert not q.is_absolute() and '..' not in q.parts and '\\' not in n
        assert n.casefold() not in {x.casefold() for x in reserved}
        assert not n.casefold().startswith('history/pre_delta07/')
        assert not any(c in n for c in '\r\n\x00:')
        assert not any(x.endswith((' ','.')) for x in q.parts)
        assert n.casefold() not in seen,'DUPLICATE_OR_CASE_ALIAS_MANIFEST_PATH'
        assert type(ref['bytes']) is int and ref['bytes']>=0
        assert len(ref['sha256'])==64 and all(c in '0123456789abcdef' for c in ref['sha256'])
        seen[n.casefold()]=n
    return seen
def main(a):
    base=a.base.resolve();out=a.out.resolve();delta=a.delta_out.resolve()
    assert base.is_dir() and not out.exists() and not delta.exists()
    spec=importlib.util.spec_from_file_location('restore07',Path(__file__).with_name('restore_checkpoint.py'))
    restore=importlib.util.module_from_spec(spec);spec.loader.exec_module(restore)
    result=restore.restore(a.cipher,a.receipt,a.key,delta)
    dm=load(delta/'PAYLOAD_MANIFEST.json');bm=load(base/'PAYLOAD_MANIFEST.json')
    bnames=validate_refs(bm['files']);dnames=validate_refs(dm['files'])
    for name in bnames.keys() & dnames.keys():
        assert bnames[name]==dnames[name],'CROSS_MANIFEST_CASE_ALIAS'
    assert sha(base/'PAYLOAD_MANIFEST.json')==dm['base_payload_manifest_sha256']
    assert sha(base/'TRAINING_MANIFEST.json')==dm['base_training_manifest_sha256']
    out.mkdir(parents=True,exist_ok=False);combined={};replaced=[]
    def copy(ref,origin):
        p=safe(origin,ref['path'])
        assert p.is_file() and not p.is_symlink()
        assert p.stat().st_size==ref['bytes'] and sha(p)==ref['sha256']
        dst=safe(out,ref['path']);dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,dst);assert sha(dst)==ref['sha256']
        combined[ref['path']]={k:ref[k] for k in ['path','bytes','sha256']}
    for ref in bm['files']:copy(ref,base)
    for ref in dm['files']:
        old=combined.get(ref['path'])
        if old and old['sha256']!=ref['sha256']:
            n='history/pre_delta07/'+old['sha256'][:12]+'/'+ref['path']
            p=safe(out,n);p.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(safe(out,ref['path']),p)
            combined[n]={'path':n,'bytes':old['bytes'],'sha256':old['sha256']}
            replaced.append(ref['path'])
        copy(ref,delta)
    for n,p in [('merged06',base/'PAYLOAD_MANIFEST.json'),('delta07',delta/'PAYLOAD_MANIFEST.json')]:
        name='merge_evidence/'+n+'_authenticated_manifest.json';dst=safe(out,name)
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
        combined[name]={'path':name,'bytes':dst.stat().st_size,'sha256':sha(dst)}
    merged={'schema':'wrd-authenticated-merged06-plus-delta07-file-union','files':list(combined.values()),
        'base_authenticated_manifest_sha256':sha(base/'PAYLOAD_MANIFEST.json'),
        'delta_authenticated_manifest_sha256':sha(delta/'PAYLOAD_MANIFEST.json'),
        'current_training_manifest_sha256':sha(out/'TRAINING_MANIFEST.json'),
        'no_saved_source_executed':True,'training_started':False}
    (out/'PAYLOAD_MANIFEST.json').write_text(json.dumps(merged,indent=2)+'\n',encoding='utf-8')
    proof={'status':'PASS_AUTHENTICATED_MERGED06_AND_DELTA07_EXPLICIT_FILES_NEW_ROOT',
        'base_files':len(bm['files']),'delta_files':len(dm['files']),'merged_files':len(combined),
        'replaced_old_bytes_preserved':replaced,'delta_authenticated_members':result['authenticated_files'],
        'training_started':False,'requires_independent_loader_QA':True}
    (out/'MERGE_RESULT.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(proof))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['base','cipher','receipt','key','out','delta-out']:p.add_argument('--'+n,type=Path,required=True)
    main(p.parse_args())
