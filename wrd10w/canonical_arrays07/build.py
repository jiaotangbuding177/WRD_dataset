"""Create canonical binary entrypoint for the exact current552 manifest only."""
from pathlib import Path
from array import array
from itertools import zip_longest
import hashlib
import importlib.util
import json
import os
import shutil
import sys

os.environ['USE_TORCH']='0';os.environ['USE_TF']='0';os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.dont_write_bytecode=True
ROOT=Path('D:/skillloop');HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'output/20261027_wrd_main_v10'
EXPECTED='94770ad82f082c55cf780f8a85108b9429cfa9ee5ee168c43198878f18633541'
def h(b):return hashlib.sha256(b).hexdigest()
def pin(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def js(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def module(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def write_array(p,kind,values):
    a=array(kind,values)
    if sys.byteorder!='little':a.byteswap()
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(a.tobytes())
    return {'path':'canonical_arrays07/'+p.relative_to(HERE).as_posix(),'bytes':p.stat().st_size,'sha256':h(p.read_bytes()),
        'dtype':{'I':'uint32_le','q':'int64_le','f':'float32_le'}[kind]}

def main():
    manifest=SOURCE/'TRAINING_MANIFEST.json';assert h(manifest.read_bytes())==EXPECTED
    data=json.loads(manifest.read_text(encoding='utf-8'));assert data['actual_counts']['sequences']==552
    standard=module('standard_features07',ROOT/'research/data_prep/wrd_main_v10/verify_main05.py')
    assert not (HERE/'ARRAY_INDEX07.json').exists() and not(HERE/'arrays').exists()
    records=[];rows_total=positive=bytes_total=0;legacy_rows=legacy_refs=0
    for position,((train_file,row),features) in enumerate(zip_longest(standard.iter_rows(SOURCE),standard.iter_features(SOURCE))):
        assert row['total_tokens']==len(features['input_ids'])
        ordinal=sum(r['source_train_file']==train_file for r in records)
        key=f'{position:04d}_'+h(row['id'].encode())[:24];p=HERE/'arrays'/key
        arrays={name:write_array(p/filename,kind,features[name])for name,filename,kind in
            [('input_ids','input_ids.u32le.bin','I'),('labels','labels.i64le.bin','q'),('loss_weights','loss_weights.f32le.bin','f')]}
        records.append({'position':position,'id':row['id'],'source_train_file':train_file,'source_record_index':ordinal,
            'total_tokens':row['total_tokens'],'supervised_tokens':row['supervised_tokens'],
            'supervision_spans_sha256':row['supervision_spans_sha256'],'source_input_ids_sha256_u32le':row['input_ids_sha256_u32le'],
            'arrays':arrays})
        rows_total+=row['total_tokens'];positive+=row['supervised_tokens'];bytes_total+=sum(r['bytes']for r in arrays.values())
        if row.get('binary_arrays'):legacy_rows+=1;legacy_refs+=len(row['binary_arrays'])
    assert len(records)==552 and rows_total==3300896 and positive==150674
    assert h(manifest.read_bytes())==EXPECTED
    index={'schema':'wrd-canonical-binary-array-index07-v1','manifest_relative_path':'TRAINING_MANIFEST.json','manifest_sha256':EXPECTED,
        'record_count':552,'input_tokens':rows_total,'supervised_tokens':positive,'binary_files':1656,'binary_bytes':bytes_total,
        'records':records,'attention_mask':'ALL_ONES_NO_CONTEXT_REMOVED','loss_weights_storage':'IEEE754_FLOAT32_LITTLE_ENDIAN',
        'python_weight_return':'Exact original span-weight values after validating stored float32 conversion.',
        'legacy_row_binary_arrays':'LEGACY_ARTIFACT_REFERENCES_IGNORED_NOT_REPAIRED_OR_USED',
        'training_started':False,'weights_loaded':False}
    save(HERE/'ARRAY_INDEX07.json',index)
    ix=pin(HERE/'ARRAY_INDEX07.json');save(HERE/'INDEX_PIN07.json',{'index_relative_path':'canonical_arrays07/ARRAY_INDEX07.json',
        'index_sha256':ix['sha256'],'index_bytes':ix['bytes'],'manifest_sha256':EXPECTED})
    # A temporary root layout is unnecessary: pass a root mapping for this local
    # source during QA, then test the final literal layout with a lightweight
    # directory containing only pinned manifest/shards and canonical arrays.
    qa_root=HERE/'_local_portability_fixture'
    assert not qa_root.exists();qa_root.mkdir()
    shutil.copyfile(manifest,qa_root/'TRAINING_MANIFEST.json')
    for ref in data['actual_train_files']:
        dst=qa_root/ref['path'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(SOURCE/ref['path'],dst)
    # A junction/symlink is not required. Copy actual binaries into the test root
    # so portable lookup and pin checks exercise the exact restored layout.
    (qa_root/'canonical_arrays07').mkdir()
    shutil.copytree(HERE/'arrays',qa_root/'canonical_arrays07/arrays')
    for name in ['ARRAY_INDEX07.json','INDEX_PIN07.json','binary_loader.py']:
        shutil.copyfile(HERE/name,qa_root/'canonical_arrays07'/name)
    loader=module('portable_binary_features07',HERE/'binary_loader.py')
    checked=0
    for expected,actual in zip_longest(standard.iter_features(qa_root),loader.iter_features(qa_root)):
        assert expected is not None and actual is not None
        assert set(actual)=={'input_ids','attention_mask','labels','loss_weights'}
        assert expected==actual,'BINARY_FEATURES_NOT_IDENTICAL_TO_STANDARD'
        checked+=1
    assert checked==552
    original_reader=loader._read_array;injected=False
    def bad_mask_reader(root,ref,kind,dtype,length):
        nonlocal injected
        a=original_reader(root,ref,kind,dtype,length)
        if not injected and dtype=='int64_le':a[0]=1;injected=True
        return a
    loader._read_array=bad_mask_reader
    try:next(loader.iter_features(qa_root))
    except AssertionError as e:
        assert str(e)=='BINARY_LABELS_DISAGREE_WITH_SOURCE_SPANS';negative={'status':'PASS_REJECTED','error':str(e),
            'injection':'in-memory decoded labels after binary pin verification; first prompt token changed to positive label','source_or_binary_files_modified':False}
    else:raise AssertionError('bad mask escaped')
    finally:loader._read_array=original_reader
    assert h(manifest.read_bytes())==EXPECTED
    # Delete only our explicitly named, resolved temporary fixture after checks.
    # No original input, shard or canonical delivery array is inside this target.
    resolved_fixture=qa_root.resolve()
    assert resolved_fixture.parent==HERE.resolve() and resolved_fixture.name=='_local_portability_fixture'
    shutil.rmtree(resolved_fixture)
    qa={'status':'PASS_CANONICAL_BINARY_ENTRYPOINT_ALL552','manifest_sha256':EXPECTED,'all552_four_features_exactly_equal_standard_loader':checked,
        'binary_files':1656,'binary_bytes':bytes_total,'input_tokens':rows_total,'supervised_tokens':positive,
        'all_binary_size_SHA_dtype_endianness_checked':True,'all_source_shard_pins_and_owner_spans_checked':True,
        'negative_mask_canary':negative,'float32_storage_and_exact_python_weight_return_explained':True,
        'legacy_rows_with_binary_arrays':legacy_rows,'legacy_references':legacy_refs,'legacy_fields_not_rewritten_or_automatically_followed':True,
        'legacy_fields_not_claimed_portable':True,'loader_pin':pin(HERE/'binary_loader.py'),'index_pin':ix,
        'standard_loader_pin':pin(ROOT/'research/data_prep/wrd_main_v10/verify_main05.py'),
        'actual_literal_portable_root_fixture_checked_and_cleaned':True,'original_shards_or_manifest_modified':False,'weights_loaded':False,'training_started':False,
        'new_Agent_calls':0,'curation_cost':'UNKNOWN_NOT_ZERO','build_script_sha256':h(Path(__file__).read_bytes())}
    save(HERE/'QA.json',qa)
    save(HERE/'DELIVERY_MANIFEST.json',{'status':'ROOT_READY_CANONICAL_BINARY_ENTRYPOINT_NOT_TRAINING_LAUNCH',
        'copy_directory_to_manifest_root_as':'canonical_arrays07','manifest_sha256':EXPECTED,
        'files':[{'path':p.relative_to(HERE).as_posix(),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
            for p in sorted(HERE.rglob('*'))if p.is_file()and p.name!='DELIVERY_MANIFEST.json'and '__pycache__'not in p.parts],
        'binary_files':1656,'legacy_original_fields_unchanged':True,'training_started':False})
    print(js({k:v for k,v in qa.items()if k in ['status','all552_four_features_exactly_equal_standard_loader','binary_files','binary_bytes','input_tokens','supervised_tokens','legacy_references']}))

if __name__=='__main__':main()
