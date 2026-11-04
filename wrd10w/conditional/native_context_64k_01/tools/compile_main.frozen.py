"""CPU-only explicit-mask v10 compilation. Never loads model weights or trains.

New source-grounded annotations and original native demonstrations retain their
different provenance. Nothing is promoted merely because an assistant wrote it.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/20261027_wrd_main_v10'
os.environ['USE_TORCH']='0'
os.environ['USE_TF']='0'


def js(x): return json.dumps(x, ensure_ascii=False, separators=(',', ':'))
def sha(x): return hashlib.sha256(x.encode('utf-8')).hexdigest()
def digest(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()
def rows(p):
    op = gzip.open if str(p).endswith('.gz') else open
    with op(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip(): yield json.loads(line)
def save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def select_reviewed_spans(compiler, messages, tools, result, allowed, field_ranges):
    """Approve intact components and/or exact independently reviewed substrings.

    The original response stays verbatim. Wrong/unreviewed reasoning is context,
    not discarded, and a token crossing a reviewed substring edge is masked.
    """
    if allowed is None and not field_ranges: return
    allowed=set(allowed or [])
    assert allowed <= {'F','R','R_BOUNDARY_MIXED','A','D','E','MIXED'}
    by_message=defaultdict(list)
    if field_ranges:
        kwargs=dict(compiler.tokenizers['primary_14b'].special_tokens_map)
        kwargs['enable_thinking']=False
        rendered=compiler.plain_compiled.render(messages=messages,tools=tools or None,documents=None,add_generation_prompt=False,**kwargs)
        encoded=compiler.tokenizers['primary_14b'](rendered,add_special_tokens=False,return_offsets_mapping=True)
        assert encoded['input_ids']==result['input_ids'], 'span_selection_render_changed'
        offsets=encoded['offset_mapping']
        targets={t['message_index']:t for t in result['targets']}
        for entry in field_ranges:
            index=entry['message_index']; field=entry['field']
            assert type(index) is int and field in {'reasoning_content','content'} and index in targets
            text=messages[index].get(field,'') or ''
            start,end=entry['start'],entry['end']
            assert type(start) is int and type(end) is int and 0 <= start < end <= len(text)
            assert sha(text[start:end])==entry['text_sha256']
            base=targets[index]['rendered_assistant_span'][0]+len('<|im_start|>assistant\n')+len('<think>\n')
            if field=='content':base+=len(messages[index].get('reasoning_content',''))+len('\n</think>\n\n')
            assert rendered[base+start:base+end]==text[start:end], 'field_offset_not_exact'
            by_message[index].append((base+start,base+end))
    components=Counter(); global_spans=[]
    for target in result['targets']:
        selected=[]; ranges=by_message[target['message_index']]
        for lo,hi,cl,w in target.get('owned_supervision_spans',[]):
            for token in range(lo,hi):
                accepted=cl in allowed
                if not accepted and ranges:
                    a,b=offsets[token]
                    accepted=any(start<=a<b<=end for start,end in ranges)
                if accepted:
                    if selected and selected[-1][1]==token and selected[-1][2:]==[cl,w]:selected[-1][1]=token+1
                    else:selected.append([token,token+1,cl,w])
                    components[cl]+=1
        target['owned_supervision_spans']=selected
        target['supervised_tokens']=sum(b-a for a,b,_,_ in selected)
        global_spans.extend(selected)
    result['supervision_spans']=global_spans
    result['supervised_tokens_by_component']=dict(components)
    result['supervised_tokens']=sum(components.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path, action='append', required=True)
    ap.add_argument('--output', type=Path, default=OUT/'compiled')
    args = ap.parse_args()
    spec = importlib.util.spec_from_file_location('v10_reused_causal_tokenizer', ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    compiler = module.CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('output_must_be_new_or_empty_no_stale_shards')
    args.output.mkdir(parents=True, exist_ok=True)
    counts = Counter(); stage = defaultdict(Counter); banks = defaultdict(Counter)
    sources = defaultdict(set); groups = defaultdict(set); seen = set(); handles = {}
    identity_splits = {}
    pins = [{'path':str(p.resolve()),'sha256':digest(p),'bytes':p.stat().st_size} for p in args.input]
    held = args.output/'held.jsonl.gz'
    try:
        with gzip.open(held, 'wt', encoding='utf-8', newline='\n') as rejected:
            for path in args.input:
                for original in rows(path):
                    counts['input_records'] += 1
                    owner = str(original.get('id', original.get('annotation_id', '')))
                    assert owner and owner not in seen, 'missing_or_duplicate_record_identity'
                    seen.add(owner)
                    reason = None
                    if original.get('training_admitted') is not True: reason = 'NOT_SEMANTICALLY_ADMITTED'
                    if original.get('split') not in {'train','dev','test'}: reason = 'MISSING_FROZEN_SPLIT'
                    if original.get('source_admission') != 'ADMIT': reason = 'SOURCE_NOT_ADMITTED'
                    if original.get('original226') or original.get('holdout12') or original.get('protected_sources_visible_prefix'): reason = 'PROTECTED_SOURCE'
                    if not isinstance(original.get('source_group_id'),str) or not original['source_group_id']: reason = 'MISSING_SOURCE_GROUP'
                    if reason:
                        rejected.write(js({'id':owner,'reason':reason})+'\n'); counts['held_'+reason] += 1; continue
                    messages = deepcopy(original['messages'])
                    approved = original.get('supervision_message_indices', original.get('supervision_candidate_message_indices'))
                    if approved is None and 'message_loss_mask' in original:
                        approved = [i for i, v in enumerate(original['message_loss_mask']) if v]
                    assert approved and all(type(i) is int and 0 <= i < len(messages) and messages[i]['role']=='assistant' for i in approved)
                    assert len(approved)==len(set(approved)) and approved==sorted(approved)
                    if 'message_loss_mask' in original:
                        mask = original['message_loss_mask']
                        assert len(mask)==len(messages) and all(type(v) is int and v in {0,1} for v in mask)
                        assert approved == [i for i,v in enumerate(mask) if v]
                    for identity in ['group:'+original['source_group_id']]+['source:'+s for s in original.get('source_ids',[])]:
                        if identity in identity_splits: assert identity_splits[identity]==original['split'], 'cross_split_source_or_group'
                        identity_splits[identity]=original['split']
                    registry={t['function']['name']:t['function'] for t in original.get('tools',[]) if t.get('type')=='function'}
                    tool_error=None
                    schema_proof=original.get('tool_schema_provenance')
                    calls_present=any(messages[i].get('tool_calls') for i in approved)
                    if calls_present:
                        try:
                            capture=Path(schema_proof['path'])
                            assert digest(capture)==schema_proof['sha256']
                            actual=json.loads(capture.read_text(encoding='utf-8-sig'))['tools']
                            actual_registry={t['function']['name']:t['function'] for t in actual if t.get('type')=='function'}
                            assert all(name in actual_registry and fn==actual_registry[name] for name,fn in registry.items())
                        except (KeyError,TypeError,ValueError,AssertionError,OSError):
                            tool_error='TOOL_SCHEMA_REAL_CAPTURE_NOT_VERIFIED'
                    for i in approved:
                        for call in messages[i].get('tool_calls',[]):
                            fn=call.get('function',{}); name=fn.get('name')
                            if name not in registry or not schema_proof:
                                tool_error='TOOL_SCHEMA_OR_REAL_CAPTURE_PROVENANCE_MISSING'; continue
                            from jsonschema import Draft202012Validator
                            try:
                                arguments=fn.get('arguments',{})
                                if isinstance(arguments,str): arguments=json.loads(arguments)
                                if list(Draft202012Validator(registry[name]['parameters']).iter_errors(arguments)): tool_error='TOOL_ARGUMENT_SCHEMA_INVALID'
                            except (ValueError,KeyError,TypeError): tool_error='TOOL_ARGUMENT_SCHEMA_INVALID'
                    if tool_error:
                        rejected.write(js({'id':owner,'reason':tool_error})+'\n'); counts['held_'+tool_error]+=1; continue
                    for m in messages:
                        if m.get('role') == 'assistant': m.setdefault('reasoning_content','')
                    multiplier = float(original.get('loss_multiplier', 1.0))
                    assert 0 < multiplier <= 1
                    owned = {i:{'id':owner+':m'+str(i),'mechanical_usable':True,'supervision_tier':original.get('bank','source_contract_main')} for i in approved}
                    result = compiler.compile_messages(messages, original.get('tools',[]), owned,
                        independent=counts['input_records'] <= 32 or counts['input_records'] % 97 == 0)
                    select_reviewed_spans(compiler,messages,original.get('tools',[]),result,
                        original.get('approved_components'),original.get('approved_field_ranges'))
                    if result['total_tokens'] > 32768 and result['supervision_spans']:
                        end=max(s[1] for s in result['supervision_spans'])
                        # Only an unsupervised FUTURE completion suffix may be
                        # omitted. Every past input token remains unchanged;
                        # no end-of-thinking or EOS token is fabricated.
                        if original.get('allow_reviewed_completion_prefix') is True and end<=32768:
                            assert approved==[len(messages)-1] and messages[-1]['role']=='assistant'
                            result['complete_rendered_tokens']=result['total_tokens']
                            result['complete_input_ids_sha256_u32le']=result['input_ids_sha256_u32le']
                            result['complete_rendered_sha256']=result['rendered_sha256']
                            result['input_ids']=result['input_ids'][:end]
                            result['total_tokens']=end
                            result['input_ids_sha256_u32le']=module.int_sha(result['input_ids'])
                            result['rendered_sha256']=sha(compiler.tokenizers['primary_14b'].decode(result['input_ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False))
                            result['view']='EXACT_TOKEN_PREFIX_OMITTING_ONLY_UNSUPERVISED_FUTURE_COMPLETION'
                            result['full_response_in_this_window']=False
                            result['no_past_context_token_removed']=True
                            result['no_artificial_stop_token_inserted']=True
                            counts['explicit_reviewed_completion_prefix_sequences']+=1
                    if result['total_tokens'] > 32768:
                        rejected.write(js({'id':owner,'reason':'GT32K_NO_SILENT_TRUNCATION','tokens':result['total_tokens']})+'\n')
                        counts['held_GT32K_NO_SILENT_TRUNCATION'] += 1; continue
                    result['supervision_spans'] = [[a,b,c,w*multiplier] for a,b,c,w in result['supervision_spans']]
                    for target in result['targets']:
                        target['owned_supervision_spans']=[[a,b,c,w*multiplier] for a,b,c,w in target.get('owned_supervision_spans',[])]
                    result['supervision_spans_sha256']=sha(js(result['supervision_spans']))
                    if result['supervised_tokens'] <= 0:
                        rejected.write(js({'id':owner,'reason':'NO_APPROVED_COMPONENTS_REMAIN'})+'\n'); counts['held_NO_APPROVED_COMPONENTS_REMAIN']+=1; continue
                    split = original['split']; bank = original.get('bank','source_contract_main')
                    label = original.get('stage','A_source_contract')
                    bucket = '16k' if result['total_tokens'] <= 16384 else '32k'
                    filename = f'{bank}.{split}.{bucket}.jsonl.gz'
                    if filename not in handles: handles[filename] = gzip.open(args.output/filename,'wt',encoding='utf-8',newline='\n')
                    row = {**result,'schema_version':'wrd-verified-main-v10','id':owner,'messages':messages,
                        'tools':original.get('tools',[]),'bank':bank,'stage':label,'split':split,
                        'source_ids':original.get('source_ids',[]),'source_group_id':original.get('source_group_id'),
                        'annotation_provenance':original.get('annotation_provenance'),
                        'original_record_metadata':{k:v for k,v in original.items() if k not in {'messages','tools'}},
                        'training_started':False,'is_full_autonomous_execution_demonstration':original.get('is_full_autonomous_execution_demonstration',False)}
                    handles[filename].write(js(row)+'\n')
                    for counter in (counts,stage[label],banks[bank]):
                        counter['sequences'] += 1; counter['targets'] += len(approved)
                        counter['input_tokens'] += result['total_tokens']; counter['supervised_tokens'] += result['supervised_tokens']
                        counter[bucket+'_sequences'] += 1; counter[split+'_sequences'] += 1
                        counter[split+'_supervised_tokens'] += result['supervised_tokens']
                        for component,n in result['supervised_tokens_by_component'].items(): counter['component_'+component] += n
                    sources[bank].update(original.get('source_ids',[]))
                    if original.get('source_group_id'): groups[bank].add(original['source_group_id'])
                    if counts['sequences'] % 100 == 0: print(js({'compiled':counts['sequences'],'supervised_tokens':counts['supervised_tokens']}),flush=True)
    finally:
        for f in handles.values(): f.close()
    for pin in pins: assert digest(Path(pin['path'])) == pin['sha256'], 'input_changed_while_compiling'
    report = {'schema_version':'wrd-v10-actual-token-compilation','counts':dict(counts),
        'stages':{k:dict(v) for k,v in stage.items()},
        'banks':{k:{**dict(v),'distinct_sources':len(sources[k]),'distinct_source_groups':len(groups[k])} for k,v in banks.items()},
        'files':[{'path':n,'bytes':(args.output/n).stat().st_size,'sha256':digest(args.output/n)} for n in sorted(handles)],
        'held_file':{'path':held.name,'bytes':held.stat().st_size,'sha256':digest(held)},
        'tokenizer_proof':compiler.proof,'script_sha256':digest(Path(__file__)),'immutable_inputs':pins,
        'weights_loaded':False,'training_started':False,'future_outcomes_are_metadata_only':True,
        'input_size_does_not_prove_autonomous_pipeline_capability':True}
    save(args.output/'COMPILATION_REPORT.json',report)
    save(args.output/'CAUSAL_TEMPLATE.json',{'variant':compiler.template,**compiler.proof})
    print(js({'counts':dict(counts),'banks':report['banks']}),flush=True)


if __name__ == '__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    main()
