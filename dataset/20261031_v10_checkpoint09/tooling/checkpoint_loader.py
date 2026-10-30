"""CPU-only checkpoint09 audit, inherited from the unchanged checkpoint05 audit.

Loads tokenizer assets only. Does not import a trainer, instantiate a model,
perform a forward pass or invoke an agent. Files are selected by the manifest.
"""
from __future__ import annotations
import argparse
from array import array
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['USE_TORCH'] = '0'
os.environ['USE_TF'] = '0'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'


def sha(b): return hashlib.sha256(b).hexdigest()
def digest(p): return sha(Path(p).read_bytes())
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def js(v): return json.dumps(v, ensure_ascii=False, separators=(',', ':'))
def each(p):
    with gzip.open(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip(): yield json.loads(line)
def safe(root, name):
    p = PurePosixPath(name)
    assert not p.is_absolute() and '..' not in p.parts and '\\' not in name, name
    q = Path(root).joinpath(*p.parts)
    assert q.resolve().is_relative_to(Path(root).resolve())
    return q
def ids_sha(ids):
    b = array('I', ids)
    if sys.byteorder != 'little': b.byteswap()
    return sha(b.tobytes())


def iter_rows(root):
    m = load(Path(root)/'TRAINING_MANIFEST.json')
    for ref in m['actual_train_files']:
        p = safe(root, ref['path'])
        assert p.stat().st_size == ref['bytes'] and digest(p) == ref['sha256']
        for r in each(p): yield ref['path'], r


def iter_features(root):
    """All context participates in attention. Only approved labels incur loss."""
    for _, r in iter_rows(root):
        ids = r['input_ids']; labels = [-100]*len(ids); weights = [0.0]*len(ids)
        for lo, hi, _, w in r['supervision_spans']:
            for i in range(lo, hi):
                assert labels[i] == -100
                labels[i], weights[i] = ids[i], w
        yield {'input_ids': ids, 'attention_mask': [1]*len(ids),
               'labels': labels, 'loss_weights': weights}


def verify_token_row(row, template, toks):
    meta = row['original_record_metadata']; messages = row['messages']
    kwargs = dict(toks['primary_14b'].special_tokens_map, enable_thinking=False)
    text = template.render(messages=messages, tools=row.get('tools') or None,
                           documents=None, add_generation_prompt=False, **kwargs)
    first = toks['primary_14b'](text, add_special_tokens=False, return_offsets_mapping=True)
    second = toks['control_8b'](text, add_special_tokens=False, return_offsets_mapping=True)
    assert first == second, 'DUAL_TOKENIZER_MISMATCH'
    ids = row['input_ids']
    if row.get('view') == 'EXACT_TOKEN_PREFIX_OMITTING_ONLY_UNSUPERVISED_FUTURE_COMPLETION':
        assert first['input_ids'][:len(ids)] == ids
        assert len(first['input_ids']) == row['complete_rendered_tokens']
        assert ids_sha(first['input_ids']) == row['complete_input_ids_sha256_u32le']
        assert sha(text.encode()) == row['complete_rendered_sha256']
        assert meta['allow_reviewed_completion_prefix'] is True
        decoded = toks['primary_14b'].decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
        assert sha(decoded.encode()) == row['rendered_sha256']
    else:
        assert first['input_ids'] == ids, 'INDEPENDENT_RENDER_IDS_MISMATCH'
        assert sha(text.encode()) == row['rendered_sha256'], 'RENDER_HASH_MISMATCH'
    approved = set(meta.get('supervision_message_indices', meta.get('supervision_candidate_message_indices', [])))
    allowed = []
    target_map = {t['message_index']:t for t in row['targets']}
    for i in approved:
        t = target_map[i]; a,b = t['rendered_assistant_span']
        assert messages[i]['role'] == 'assistant'
        assert text[a:b].startswith('<|im_start|>assistant\n')
        assert text[a:b].endswith('<|im_end|>\n')
        allowed.append((a+len('<|im_start|>assistant\n'), b))
    reviewed = []
    for reg in meta.get('approved_field_ranges', []):
        i,f = reg['message_index'],reg['field']; raw = messages[i].get(f,'') or ''
        a,b = reg['start'],reg['end']
        assert 0 <= a < b <= len(raw) and sha(raw[a:b].encode()) == reg['text_sha256']
        base = target_map[i]['rendered_assistant_span'][0]+len('<|im_start|>assistant\n<think>\n')
        if f == 'content': base += len(messages[i].get('reasoning_content',''))+len('\n</think>\n\n')
        assert text[base+a:base+b] == raw[a:b]
        reviewed.append((base+a,base+b))
    excluded = []
    for reg in meta.get('target_excluded_rendered_ranges', []):
        a,b = reg['start'],reg['end']
        assert text[a:b] == reg['text'] and sha(text[a:b].encode()) == reg['text_sha256']
        assert reg['message_index'] in approved and reg['field'] == 'serialized_tool_arguments'
        field = reg['subfield']
        assert field in {'content','command'}
        calls = messages[reg['message_index']].get('tool_calls', [])
        call = next(c for c in calls if c['id'] == reg['tool_call_id'])
        assert (call['function']['name'],field) in {('write','content'),('exec','command')}
        args = call['function']['arguments']
        if isinstance(args,str): args=json.loads(args)
        assert isinstance(args[field], str)
        scope = meta['serialized_tool_argument_rendered_span']
        assert scope['start'] <= a < b <= scope['end']
        serialized = text[scope['start']:scope['end']]
        assert sha(serialized.encode()) == scope['text_sha256']
        assert json.loads(serialized) == args
        encoded_content = json.dumps(args[field], ensure_ascii=False)
        assert serialized.count(encoded_content) == 1
        content_start = scope['start']+serialized.index(encoded_content)+1
        assert content_start <= a < b <= content_start+len(encoded_content)-2
        excluded.append((a,b))
    offsets = first['offset_mapping']
    for lo,hi,component,w in row['supervision_spans']:
        for a,b in offsets[lo:hi]:
            assert any(x <= a < b <= y for x,y in allowed), 'INPUT_OR_ROLE_HEADER_HAS_LOSS'
            if meta.get('approved_components') is not None or meta.get('approved_field_ranges'):
                assert component in set(meta.get('approved_components') or []) or any(x<=a<b<=y for x,y in reviewed), 'UNREVIEWED_FIELD_HAS_LOSS'
            assert not any(a<y and b>x for x,y in excluded), 'EXCLUDED_OR_CROSSING_TOKEN_HAS_LOSS'
    return len(ids), len(excluded)


def verify(root, assets=None):
    root=Path(root); m=load(root/'TRAINING_MANIFEST.json')
    reports={str(PurePosixPath(r['path']).parent):r for r in m['active_compilation_reports']}
    for r in reports.values(): assert digest(safe(root,r['path'])) == r['sha256']
    admissions={}
    for ref in m['external_root_admission_receipts']:
        p=safe(root,ref['path']); assert digest(p)==ref['sha256']; proof=load(p)
        assert proof['status'].startswith('ADMIT_')
        assert proof['compilation_report_sha256'] == reports[ref['compiled_bank']]['sha256']
        assert len(proof['record_ids']) == len(set(proof['record_ids']))
        admissions[ref['compiled_bank']]=set(proof['record_ids'])
    source_scope = root/'clean_inputs/source_scope.metadata.jsonl.gz'
    if not source_scope.exists(): source_scope=root/'evidence_current/clean_inputs/source_scope.metadata.jsonl.gz'
    scopes={s['source_id']:s for s in each(source_scope)}
    toks=None
    if assets:
        from transformers import AutoTokenizer
        from transformers.utils.chat_template_utils import _compile_jinja_template
        toks={name:AutoTokenizer.from_pretrained(Path(assets)/name,local_files_only=True,trust_remote_code=False)
              for name in ['primary_14b','control_8b']}
    counts=Counter(); bankcounts=defaultdict(Counter); stages=defaultdict(Counter)
    ids=set(); owners=set(); action_owners=set(); banks=defaultdict(set); sources=set(); groups=set(); parents={}
    weighted=Counter(); direct=0; excluded_count=0
    def find(x):
        parents.setdefault(x,x)
        if parents[x]!=x: parents[x]=find(parents[x])
        return parents[x]
    def join(x,y):
        a,b=find(x),find(y)
        if a!=b:parents[max(a,b)]=min(a,b)
    for relative,row in iter_rows(root):
        bank=str(PurePosixPath(relative).parent); banks[bank].add(row['id'])
        meta=row['original_record_metadata']; identity=row['id']; owner=meta.get('owner_id',identity)
        assert identity not in ids and owner not in owners
        ids.add(identity);owners.add(owner)
        assert meta['training_admitted'] is True and meta['source_admission']=='ADMIT'
        assert not any(meta.get(k) for k in ['original226','holdout12','protected_sources_visible_prefix','protected_source_ids'])
        if meta.get('root_main_admission') is False:
            assert bank in admissions and identity in admissions[bank]
        assert row['split']=='train'
        for s in row['source_ids']:
            assert scopes[s]['status']=='TRAIN', (identity,s)
            sources.add(s);join('r:'+identity,'s:'+s)
        groups.add(row['source_group_id']);join('r:'+identity,'g:'+row['source_group_id'])
        arr=row['input_ids'];spans=row['supervision_spans']
        assert len(arr)==row['total_tokens']<=32768 and ids_sha(arr)==row['input_ids_sha256_u32le']
        assert sha(js(spans).encode())==row['supervision_spans_sha256']
        components=Counter();last=0
        for lo,hi,component,w in spans:
            assert 0<=last<=lo<hi<=len(arr) and 0<w<=1
            assert abs(w-float(meta.get('loss_multiplier',1))*(.2 if component=='F' else 1))<1e-8
            last=hi;components[component]+=hi-lo;weighted[component]+=(hi-lo)*w
        assert dict(components)==row['supervised_tokens_by_component']
        assert sum(components.values())==row['supervised_tokens']>0
        assert [s for t in row['targets'] for s in t['owned_supervision_spans']]==spans
        approved=meta.get('supervision_message_indices',meta.get('supervision_candidate_message_indices'))
        if approved is None: approved=[i for i,x in enumerate(meta['message_loss_mask']) if x]
        assert approved and set(approved)=={t['message_index'] for t in row['targets'] if t['owned_supervision_spans']}
        if 'message_loss_mask' in meta:
            assert len(meta['message_loss_mask'])==len(row['messages'])
            assert set(approved)=={i for i,x in enumerate(meta['message_loss_mask']) if x}
        registry={t['function']['name']:t['function'] for t in row.get('tools',[]) if t.get('type')=='function'}
        from jsonschema import Draft202012Validator
        for target in row['targets']:
            assert target['supervised_tokens']==sum(b-a for a,b,_,_ in target['owned_supervision_spans'])
            if not any(s[2]=='A' for s in target['owned_supervision_spans']):continue
            for call in row['messages'][target['message_index']].get('tool_calls',[]):
                assert call['id'] not in action_owners;action_owners.add(call['id'])
                f=call['function'];args=f['arguments']
                if isinstance(args,str):args=json.loads(args)
                assert not list(Draft202012Validator(registry[f['name']]['parameters']).iter_errors(args))
        if toks:
            template=_compile_jinja_template(load(safe(root,bank+'/CAUSAL_TEMPLATE.json'))['variant'])
            _,n=verify_token_row(row,template,toks);direct+=1;excluded_count+=n
        for c in [counts,bankcounts[row['bank']],stages[row['stage']]]:
            c.update(sequences=1,targets=len(approved),input_tokens=len(arr),supervised_tokens=row['supervised_tokens'],
                     le16k_sequences=int(len(arr)<=16384),le32k_sequences=int(len(arr)<=32768))
            for k,v in components.items():c['component_'+k]+=v
    for bank,expected in admissions.items():assert banks[bank]==expected
    assert dict(counts)==m['actual_counts']
    assert {k:dict(v) for k,v in bankcounts.items()}==m['by_bank']
    assert {k:dict(v) for k,v in stages.items()}==m['by_stage']
    assert len(sources)==m['distinct_source_ids']
    assert len({find('r:'+i) for i in ids})==m['source_connected_components_across_banks']
    loadercounts=Counter()
    for f in iter_features(root):
        assert all((l==-100)==(w==0) for l,w in zip(f['labels'],f['loss_weights']))
        assert all(l in [-100,t] for l,t in zip(f['labels'],f['input_ids']))
        loadercounts.update(sequences=1,supervised_tokens=sum(l!=-100 for l in f['labels']))
    assert loadercounts['sequences']==counts['sequences'] and loadercounts['supervised_tokens']==counts['supervised_tokens']
    return {'status':'PASS','actual_counts':dict(counts),'loader_counts':dict(loadercounts),
            'source_ids':len(sources),'joined_components':len({find('r:'+i) for i in ids}),
            'external_root_admissions':len(admissions),'unique_positive_tool_call_owners':len(action_owners),
            'weighted_label_mass_by_component':dict(weighted),'every_row_direct_dual_tokenized':direct,
            'exact_serialized_argument_exclusions_checked':excluded_count,'mask0_context_preserved':True,
            'weights_loaded':False,'training_started':False,'semantic_validity_not_inferred_from_array_checks':True,
            'script_sha256':digest(__file__),'manifest_sha256':digest(root/'TRAINING_MANIFEST.json')}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--assets',type=Path)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=verify(a.root,a.assets);a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
