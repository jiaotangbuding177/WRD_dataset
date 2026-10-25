"""Export complete frozen archive coverage without personal filenames/host paths.

Metadata only: does not execute or copy archive contents. Hashes identify
aliases and objects, not additional training examples.
"""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import time


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    started=time.monotonic();source=a.bundle/'archive/file_index.jsonl';before=sha(source)
    a.output.mkdir(parents=True,exist_ok=True);target=a.output/'archive_opaque_inventory.jsonl.gz'
    scopes=Counter();objects=set();n=0
    with source.open(encoding='utf-8-sig') as inp,gzip.open(target,'wt',encoding='utf-8',newline='\n',compresslevel=3) as out:
        for line in inp:
            raw=json.loads(line)
            for k in ('sha256','source_sha256'):
                if not re.fullmatch('[0-9a-f]{64}',raw[k]):raise ValueError('invalid digest')
            logical=raw['logical_path'];scope=logical.replace('\\','/').split('/')[0]
            if scope not in {'pipeline','sources','source_materials','episodes','history','protocol'}:scope='other'
            row={'alias_path_sha256':hashlib.sha256(logical.encode('utf-8')).hexdigest(),
                 'scope':scope,'stored_sha256':raw['sha256'],'source_sha256':raw['source_sha256'],
                 'stored_bytes':int(raw['bytes']),'source_bytes':int(raw['source_bytes']),
                 'historical_credential_redacted':bool(raw['credential_redacted']),
                 'content_publication_not_asserted':True,'independent_training_sample':False}
            out.write(json.dumps(row,separators=(',',':'))+'\n');scopes[scope]+=1;objects.add(raw['sha256']);n+=1
    if sha(source)!=before:raise ValueError('source changed')
    report={'schema_version':'wrd-opaque-archive-inventory-v1','aliases':n,'unique_stored_objects':len(objects),
            'scopes':dict(scopes),'original_index_sha256':before,'source_unchanged':True,
            'output':{'name':target.name,'sha256':sha(target),'bytes':target.stat().st_size},
            'host_paths_and_personal_filenames_included':False,'content_publication_not_asserted':True,
            'training_started':False,'elapsed_seconds':round(time.monotonic()-started,3)}
    (a.output/'archive_coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
