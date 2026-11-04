"""Independent entire staged623 dual-tokenizer and binary four-feature audit.
No data mutation, resource execution, model weights or training.
"""
from pathlib import Path,PurePosixPath
from array import array
from copy import deepcopy
import argparse,collections,gzip,hashlib,importlib.util,json,os,sys
os.environ['USE_TORCH']='0';os.environ['USE_TF']='0';os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ['TOKENIZERS_PARALLELISM']='false'
ROOT=Path('D:/skillloop');WORK=ROOT/'output/20261031_wrd_curation10'
def h(b):return hashlib.sha256(b).hexdigest()
def pin(p):p=Path(p);return{'path':str(p),'bytes':p.stat().st_size,'sha256':h(p.read_bytes())}
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def module(n,p):
    s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s)
    old=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:s.loader.exec_module(m)
    finally:sys.dont_write_bytecode=old
    return m
def each(root):
    m=load(root/'TRAINING_MANIFEST.json')
    for f in m['actual_train_files']:
        p=root/f['path'];assert pin(p)['sha256']==f['sha256']
        with gzip.open(p,'rb')as g:
            for line in g:
                if line.strip():yield f['path'],line,json.loads(line)
def lebytes(kind,v):
    a=array(kind,v)
    if sys.byteorder!='little':a.byteswap()
    return a.tobytes()
def main(a):
    root=a.root.resolve();manifest=load(root/'TRAINING_MANIFEST.json')
    verify=module('peer10_verify_full_union',ROOT/'research/data_prep/wrd_curation10/verify_main10.py')
    standard=verify.verify(root,a.assets)
    assert standard['every_row_direct_dual_tokenized']==623
    baseline=Path('D:/skillloop/output/wrd09root01')
    assert pin(baseline/'TRAINING_MANIFEST.json')['sha256']=='01380a42195dd888aded4140db7dc7013364f6bc66594502487387259d174f42'
    old={r['id']:(line,r)for _,line,r in each(baseline)}
    new={r['id']:(line,r)for _,line,r in each(root)}
    expected_removed={'process09-0f1603b601613eac2fecb014'}
    assert len(old)==595 and len(new)==623 and set(old)-set(new)==expected_removed
    kept=set(old)&set(new);assert len(kept)==594
    assert all(old[i][0]==new[i][0]for i in kept),'RETAINED594_ORIGINAL_JSON_ROW_BYTES_CHANGED'
    added=set(new)-set(old);assert len(added)==29
    compiled=WORK/'compiled_combined29';report=load(compiled/'COMPILATION_REPORT.json')
    expected={json.loads(l)['id']for f in report['files']for l in gzip.open(compiled/f['path'],'rt',encoding='utf-8-sig')}
    assert added==expected
    index=load(root/'canonical_arrays10/ARRAY_INDEX10.json')
    assert index['record_count']==623 and index['manifest_sha256']==pin(root/'TRAINING_MANIFEST.json')['sha256']
    assert index['binary_files']==1869
    admission=module('peer10_trusted_loader_source',ROOT/'research/data_prep/wrd_curation10/admit10.py')
    loaderpath=root/'canonical_arrays10/binary_loader10.py'
    assert loaderpath.read_text(encoding='utf-8')==admission.loader_code()
    loader=module('peer10_binary_loader',loaderpath)
    binaries=iter(loader.iter_features(root));stats=collections.Counter()
    for e in index['records']:
        row=new[e['id']][1];ids=row['input_ids'];labels=[-100]*len(ids);weights=[0.0]*len(ids)
        for lo,hi,cl,w in row['supervision_spans']:
            for i in range(lo,hi):
                assert labels[i]==-100;labels[i]=ids[i];weights[i]=w
        f32=list(array('f',weights))
        # The portable loader returns the standard Python span values; its
        # persisted float32 body is separately checked with exact IEEE bytes.
        expected_features={'input_ids':ids,'attention_mask':[1]*len(ids),'labels':labels,'loss_weights':weights}
        got=next(binaries);assert got==expected_features,'CANONICAL_BINARY_FOUR_FEATURES_MISMATCH'
        for feature,kind,values in [('input_ids','I',ids),('labels','q',labels),('loss_weights','f',weights)]:
            ref=e['arrays'][feature];p=root/ref['path'];b=p.read_bytes()
            assert len(b)==ref['bytes']and h(b)==ref['sha256']and b==lebytes(kind,values)
            stats['binary_files']+=1;stats['binary_bytes']+=len(b)
        assert all((label==-100)==(weight==0)for label,weight in zip(labels,f32))
        stats['records']+=1;stats['input_tokens']+=len(ids);stats['supervised_tokens']+=row['supervised_tokens']
    assert next(binaries,None)is None
    assert stats['records']==623 and stats['binary_files']==1869
    assert stats['input_tokens']==index['input_tokens']and stats['supervised_tokens']==index['supervised_tokens']
    assert stats['binary_bytes']==index['binary_bytes']
    # Actual negative control: one prompt token is illicitly assigned A loss in
    # a copied row in memory. No archive or training data is changed.
    from transformers import AutoTokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    toks={k:AutoTokenizer.from_pretrained(a.assets/k,local_files_only=True,trust_remote_code=False)for k in ['primary_14b','control_8b']}
    file,_,original=next(each(root));bad=deepcopy(original)
    bad['supervision_spans']=[[0,1,'A',0.25]]
    template=_compile_jinja_template(load(root/PurePosixPath(file).parent/'CAUSAL_TEMPLATE.json')['variant'])
    failed=False
    try:verify.verify_token_row(bad,template,toks)
    except AssertionError as exc:
        assert str(exc)=='INPUT_OR_ROLE_HEADER_HAS_LOSS';failed=True
    assert failed,'PROMPT_NEGATIVE_CANARY_WAS_NOT_REJECTED'
    result={'status':'PASS_INDEPENDENT_STAGED623_DUAL_TOKEN_MASK_SOURCE_AND_CANONICAL_FOUR_FEATURES',
      'root':str(root),'manifest':pin(root/'TRAINING_MANIFEST.json'),'standard_QA':standard,
      'retained_original_rows_byte_exact':594,'specific_removed_original_view_ids':sorted(expected_removed),
      'new_views_exact_compiled29_membership':29,'canonical':dict(stats),
      'four_features_all_rows_equal':True,'all1869_array_body_SHA_and_little_endian_bytes_equal':True,
      'Python_feature_weights_equal_standard_canonical_span_values':True,
      'persisted_weight_bytes_independently_equal_IEEE_float32_rounding':True,
      'actual_in_memory_prompt_label_negative_canary':'REJECTED_INPUT_OR_ROLE_HEADER_HAS_LOSS',
      'canonical_index_pin':pin(root/'canonical_arrays10/ARRAY_INDEX10.json'),
      'no_models_or_weights_loaded':True,'training_started':False,'new_business_calls':0,
      'semantic_effectiveness_not_inferred_from_array_checks':True,'script_pin':pin(__file__)}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps({'status':result['status'],'canonical':dict(stats),'QA':pin(a.out)}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--assets',type=Path,default=ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
    p.add_argument('--out',type=Path,required=True);main(p.parse_args())
