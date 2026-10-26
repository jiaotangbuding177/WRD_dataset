"""Verify clean replay attachments already exist in the uploaded v1 archive.

Reads split gzip/tar in a stream, verifies desired members, extracts nothing.
"""
import hashlib
import io
import gzip
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/20261026_wrd_dataset_v9'
RELEASE=ROOT/'output/20261025_wrd_training_dataset/git_release'


def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


class Parts(io.RawIOBase):
    def __init__(self,paths):self.paths=iter(paths);self.handle=None
    def readable(self):return True
    def readinto(self,b):
        while True:
            if self.handle is None:
                p=next(self.paths,None)
                if p is None:return 0
                self.handle=Path(p).open('rb')
            n=self.handle.readinto(b)
            if n:return n
            self.handle.close();self.handle=None
    def close(self):
        if self.handle:self.handle.close()
        super().close()


def main():
    material=json.loads((OUT/'REPLAY_INPUT_MANIFEST.json').read_text(encoding='utf-8'))
    wanted={r['sha256']:r for r in material['files']if r['kind']=='material'}
    materials=set(wanted)
    raw={}
    def add(ref):
        if isinstance(ref,dict) and ref.get('path') and ref.get('sha256'):
            raw[ref['sha256']]={'path':ref['path'],'bytes':ref['bytes'],'sha256':ref['sha256']}
    with gzip.open(OUT/'recovery/episodes.contexts.jsonl.gz','rt',encoding='utf-8')as handle:
        for line in handle:
            row=json.loads(line);add(row['source_native'])
            for overlay in row.get('reasoning_overlays_same_response_id',[]):add(overlay.get('source'))
    with gzip.open(OUT/'recovery/provider_pairs.original.jsonl.gz','rt',encoding='utf-8')as handle:
        for line in handle:
            row=json.loads(line);add(row['response_source'])
            for variant in row['request_variants']:add(variant['source'])
    wanted.update(raw)
    old=json.loads((RELEASE/'package_manifest.json').read_text(encoding='utf-8'))
    parts=[]
    for i,r in enumerate(old['parts'],1):
        p=RELEASE/r['path'];assert p.stat().st_size==r['bytes'] and digest(p)==r['sha256'];parts.append(p)
        print(json.dumps({'phase':'existing_archive_part_hash_verified','part':i,'parts':len(old['parts'])}),flush=True)
    verified={}
    with io.BufferedReader(Parts(parts),buffer_size=1048576)as stream:
        with tarfile.open(fileobj=stream,mode='r|gz')as tf:
            for member in tf:
                if not member.isfile():continue
                h=Path(member.name).name
                if h not in wanted or '/archive/objects/' not in '/'+member.name:continue
                data=tf.extractfile(member);value=hashlib.sha256()
                for b in iter(lambda:data.read(1048576),b''):value.update(b)
                assert value.hexdigest()==h and member.size==wanted[h]['bytes']
                verified[h]={'sha256':h,'bytes':member.size,'existing_archive_member':member.name}
                if len(verified)==len(wanted):break
    material_missing=materials-set(verified)
    delta=[]
    for h in sorted(set(wanted)-set(verified)):
        row=wanted[h];p=Path(row.get('path',row.get('original_path','')))
        assert p.is_file()and p.stat().st_size==row['bytes']and digest(p)==h
        delta.append({'sha256':h,'bytes':row['bytes'],'source_path':str(p)})
    report={'schema_version':'wrd-v9-verified-existing-resource-reuse','status':'PASS','training_started':False,
        'unique_material_objects':len(materials),'material_objects_already_in_uploaded_archive':len(materials)-len(material_missing),
        'raw_source_objects_requested':len(raw),'verified_existing_objects':len(verified),'verified_object_bytes':sum(r['bytes']for r in verified.values()),
        'all_old_archive_part_hashes_verified':True,'existing_package_manifest_sha256':digest(RELEASE/'package_manifest.json'),
        'existing_package_manifest_path':'package_manifest.json','existing_parts':old['parts'],
        'all_materials_already_in_existing_git':not material_missing,'new_upload_not_needed_for_identical_existing_bytes':True,
        'delta_objects_require_new_authenticated_archive':delta,'delta_object_bytes':sum(r['bytes']for r in delta),
        'objects':list(verified.values())}
    (OUT/'EXISTING_RESOURCE_REUSE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items()if k not in {'objects','existing_parts','delta_objects_require_new_authenticated_archive'}}),flush=True)


if __name__=='__main__':main()
