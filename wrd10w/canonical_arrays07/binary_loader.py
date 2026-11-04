"""Portable, standard-library-only canonical checkpoint07 binary feature loader.

Call iter_features(restored_manifest_root). Legacy per-row binary_arrays fields
are deliberately ignored. No model, trainer, saved source or network is loaded.
"""
from array import array
from itertools import zip_longest
from pathlib import Path, PurePosixPath
import gzip
import hashlib
import json
import sys

INDEX_RELATIVE='canonical_arrays07/ARRAY_INDEX07.json'
PIN_RELATIVE='canonical_arrays07/INDEX_PIN07.json'

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,separators=(',',':')).encode()
def safe(root,name):
    assert isinstance(name,str) and name and '\\' not in name and ':' not in name
    q=PurePosixPath(name)
    assert q.parts and q.as_posix()==name and not q.is_absolute() and '..' not in q.parts
    assert not any(c in name for c in '\r\n\x00')
    root=Path(root).resolve();p=root.joinpath(*q.parts)
    assert p.resolve().is_relative_to(root),'PATH_ESCAPE'
    assert p.is_file() and not p.is_symlink(),'FILE_MISSING_OR_SYMLINK'
    return p

def _read_array(root,ref,kind,dtype,length):
    assert ref['dtype']==dtype
    p=safe(root,ref['path'])
    assert ref['path'].startswith('canonical_arrays07/arrays/')
    assert p.stat().st_size==ref['bytes'] and digest(p)==ref['sha256'],'BINARY_PIN_MISMATCH'
    a=array(kind);assert a.itemsize=={'I':4,'q':8,'f':4}[kind]
    a.frombytes(p.read_bytes())
    if sys.byteorder!='little':a.byteswap()
    assert len(a)==length and ref['bytes']==length*a.itemsize,'BINARY_SHAPE_MISMATCH'
    return a

def _source_rows(root,manifest):
    seen=set()
    for ref in manifest['actual_train_files']:
        assert ref['path'].casefold() not in seen,'DUPLICATE_TRAIN_FILE'
        seen.add(ref['path'].casefold());p=safe(root,ref['path'])
        assert p.stat().st_size==ref['bytes'] and digest(p)==ref['sha256'],'TRAIN_FILE_PIN_MISMATCH'
        with gzip.open(p,'rt',encoding='utf-8-sig')as f:
            ordinal=0
            for line in f:
                if not line.strip():continue
                yield ref['path'],ordinal,json.loads(line)
                ordinal+=1

def iter_features(root):
    """Return exactly the standard loader's four Python-list features.

    All context has attention=1. Binary float32 weights are checked against
    IEEE754 rounding of the authenticated source-span weights. Returned Python
    weights use those original canonical values, avoiding float64-vs-float32
    representation drift relative to verify_main05.iter_features.
    """
    root=Path(root).resolve();index_path=safe(root,INDEX_RELATIVE)
    index_pin=json.loads(safe(root,PIN_RELATIVE).read_text(encoding='utf-8-sig'))
    assert index_pin['index_relative_path']==INDEX_RELATIVE
    assert index_path.stat().st_size==index_pin['index_bytes'] and digest(index_path)==index_pin['index_sha256'],'INDEX_PIN_MISMATCH'
    index=json.loads(index_path.read_text(encoding='utf-8-sig'))
    assert index['schema']=='wrd-canonical-binary-array-index07-v1'
    manifest_path=safe(root,index['manifest_relative_path'])
    assert digest(manifest_path)==index['manifest_sha256']==index_pin['manifest_sha256'],'MANIFEST_PIN_MISMATCH'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    assert len(index['records'])==index['record_count']==manifest['actual_counts']['sequences']
    ids_seen=set();paths_seen=set();observed=0;positive=0
    for position,pair in enumerate(zip_longest(index['records'],_source_rows(root,manifest))):
        entry,source=pair;assert entry is not None and source is not None,'INDEX_SOURCE_ROW_COUNT_MISMATCH'
        train_file,ordinal,row=source
        assert entry['position']==position and entry['source_train_file']==train_file and entry['source_record_index']==ordinal
        assert entry['id']==row['id'] and row['id'] not in ids_seen,'INDEX_SOURCE_OWNER_MISMATCH'
        ids_seen.add(row['id'])
        spans=row['supervision_spans'];spans_sha=hashlib.sha256(canonical(spans)).hexdigest()
        assert spans_sha==row['supervision_spans_sha256']==entry['supervision_spans_sha256'],'SUPERVISION_SPAN_PIN_MISMATCH'
        n=row['total_tokens'];assert entry['total_tokens']==n
        refs=entry['arrays'];assert set(refs)=={'input_ids','labels','loss_weights'}
        for ref in refs.values():
            assert ref['path'].casefold() not in paths_seen,'DUPLICATE_BINARY_PATH'
            paths_seen.add(ref['path'].casefold())
        input_ids=_read_array(root,refs['input_ids'],'I','uint32_le',n)
        labels=_read_array(root,refs['labels'],'q','int64_le',n)
        weights32=_read_array(root,refs['loss_weights'],'f','float32_le',n)
        assert list(input_ids)==row['input_ids'],'BINARY_INPUT_IDS_DISAGREE_WITH_SOURCE'
        assert refs['input_ids']['sha256']==row['input_ids_sha256_u32le'],'INPUT_ID_SHA_DISAGREEMENT'
        canonical_labels=[-100]*n;canonical_weights=[0.]*n;last=0;count=0
        for lo,hi,_,w in spans:
            assert 0<=last<=lo<hi<=n and 0<w<=1
            last=hi
            for i in range(lo,hi):canonical_labels[i]=row['input_ids'][i];canonical_weights[i]=w
            count+=hi-lo
        assert count==entry['supervised_tokens']==row['supervised_tokens']
        assert list(labels)==canonical_labels,'BINARY_LABELS_DISAGREE_WITH_SOURCE_SPANS'
        assert weights32.tobytes()==array('f',canonical_weights).tobytes(),'BINARY_WEIGHTS_DISAGREE_WITH_SOURCE_SPANS'
        assert all((labels[i]==-100)==(weights32[i]==0.) for i in range(n)),'BINARY_MASK_DISAGREEMENT'
        observed+=1;positive+=count
        yield {'input_ids':list(input_ids),'attention_mask':[1]*n,'labels':list(labels),'loss_weights':canonical_weights}
    assert observed==index['record_count'] and positive==index['supervised_tokens']

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    count=positive=positions=0
    for row in iter_features(a.root):
        count+=1;positions+=len(row['input_ids']);positive+=sum(x!=-100 for x in row['labels'])
    print(json.dumps({'status':'PASS','sequences':count,'input_tokens':positions,'supervised_tokens':positive,'training_started':False}))
