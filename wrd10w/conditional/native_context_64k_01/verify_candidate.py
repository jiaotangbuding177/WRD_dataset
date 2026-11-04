"""Independent read-only-source QA: derive every label from raw char approvals."""
import os
os.environ['USE_TORCH']='0'
os.environ['USE_TF']='0'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from array import array
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=Path('D:/skillloop')
def sha(x):return hashlib.sha256(x).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def rows(p):
    with gzip.open(p,'rt',encoding='utf-8') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def getarray(p,code):
    x=array(code);x.frombytes(p.read_bytes())
    if sys.byteorder!='little':x.byteswap()
    return x.tolist()
def main():
    assert not (HERE/'INDEPENDENT_QA.json').exists()
    from transformers import AutoTokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    report=load(HERE/'REPORT.json');template=load(HERE/'CAUSAL_TEMPLATE.json')['variant']
    renderer=_compile_jinja_template(template)
    tok=AutoTokenizer.from_pretrained(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets/control_8b',local_files_only=True,trust_remote_code=False)
    originals={(r['episode'],r['call_id']):r for r in rows(HERE/'recovered_originals.jsonl.gz')}
    checked=[]
    for r in rows(HERE/'candidate_native64k.jsonl.gz'):
        e=r['evidence'];raw=originals[e['episode'],e['call_id']]
        actual=raw['request'];past=deepcopy(actual['messages'])
        for m in past:
            if isinstance(m.get('content'),list):m['content']='\n'.join(x['text'] for x in m['content'])
            if m['role']=='assistant':m.setdefault('reasoning_content','')
        assert r['messages'][:-1]==past
        assert r['messages'][-1]==raw['response_message']
        assert r['tools']==actual['tools'] and len(r['tools'])==53
        assert not any(m.get('reasoning_content') for m in past if m['role']=='assistant')
        kw=dict(tok.special_tokens_map)
        rendered=renderer.render(messages=r['messages'],tools=r['tools'],documents=None,
            add_generation_prompt=False,enable_thinking=False,**kw)
        enc=tok(rendered,add_special_tokens=False,return_offsets_mapping=True)
        full_ids=enc['input_ids'];ids=r['input_ids'];n=len(ids)
        assert full_ids[:n]==ids
        assert sha(rendered.encode())==r['complete_rendered_sha256']
        assert sha(tok.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False).encode())==r['rendered_sha256']
        assert sha(js(r['supervision_spans']).encode())==r['supervision_spans_sha256']
        arrays={Path(a['path']).name:HERE/a['path'] for a in r['candidate_audit']['arrays']}
        assert getarray(arrays['input_ids.u32'],'I')==ids
        labels=getarray(arrays['labels.i64'],'q');weights=getarray(arrays['loss_weights.f32'],'f')
        assert len(labels)==len(weights)==n
        # Parse exact current-field position within the already asserted raw
        # response. Every positive token must fit a reviewed character interval;
        # no selector/span helper is used to derive this independent mask.
        t=r['targets'][-1];start=t['rendered_assistant_span'][0]
        base=start+len('<|im_start|>assistant\n<think>\n')
        thought=raw['response_message']['reasoning_content']
        assert rendered[base:base+len(thought)]==thought
        ranges=[]
        for item in r['semantic_review']['approved_field_ranges']:
            a,b=item['start'],item['end'];assert sha(thought[a:b].encode())==item['text_sha256']
            ranges.append((base+a,base+b))
        expected=[]
        for i,(a,b) in enumerate(enc['offset_mapping'][:n]):
            accept=any(lo<=a<b<=hi for lo,hi in ranges)
            assert labels[i]==(ids[i] if accept else -100),'label_outside_raw_approval_or_missing'
            assert weights[i]==(0.25 if accept else 0.0),'weight_outside_raw_approval'
            if accept:expected.append(i)
        span_indices=[i for a,b,c,w in r['supervision_spans'] for i in range(a,b)]
        assert expected==span_indices and len(expected)==r['supervised_tokens']
        assert all(c=='R' and w==0.25 for a,b,c,w in r['supervision_spans'])
        assert n==len(full_ids) or n==max(expected)+1
        checked.append({'id':r['id'],'tokens':n,'whole_tokens':len(full_ids),'positive_R_tokens':len(expected),
            'all_original_past_messages_and_53_tools_exact':True,'labels_directly_derived_from_original_character_ranges':True,
            'zero_loss_body_actions_past_and_unapproved_R':True,'prefix_matches_complete_tokens_exactly':True})
    pins=load(HERE/'SOURCE_PINS.json')
    for p in pins:assert sha(Path(p['path']).read_bytes())==p['sha256']
    with zipfile.ZipFile(HERE/'raw_api_originals.zip') as z:
        assert z.testzip() is None
        base=ROOT/'output/20261027_wrd_main_v10'
        for name in z.namelist():assert z.read(name)==(base/name).read_bytes()
    out={'status':'PASS','candidate_status':report['status'],'candidate_records_checked':len(checked),
        'candidate_R_tokens_checked':sum(r['positive_R_tokens'] for r in checked),'checks':checked,
        'source_pins_unchanged':len(pins),'raw_zip_exact_files_checked':len(z.namelist()),
        'independent_second_tokenizer_used':True,'shared_compiler_main_not_called':True,
        'Spark_remote_test':False,'weights_loaded':False,'training_started':False,
        'verifier_sha256':sha(Path(__file__).read_bytes())}
    (HERE/'INDEPENDENT_QA.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(js(out))
if __name__=='__main__':main()
