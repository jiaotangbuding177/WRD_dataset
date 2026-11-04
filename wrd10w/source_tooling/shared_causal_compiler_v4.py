"""CPU-only causal process compilation; no model weights, GPU or agent loop.

The declared Qwen3 causal template variant removes future-dependent assistant
wrapping, preserves explicit reasoning fields, and never interprets literal
closing-think text in a body as an unrecorded reasoning field. It is NOT claimed
to be the unmodified official template or already wired into a live API.
"""
from __future__ import annotations
import argparse
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from array import array

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

HEADER = '<|im_start|>assistant\n'
THINK_OPEN = '<think>\n'
THINK_CLOSE = '\n</think>\n\n'
END = '<|im_end|>\n'
POLICIES = ('不得访问正式250测试任务或答案', '不读正式250测试集', '未引用正式250测试集')
import re
FORMAL = re.compile(r'\bT\d{4}\b|eval(?:uation)?[_ -]?250|evaluation_visible|正式\s*250|固定\s*226|当前\s*250', re.I)
INCOMPLETE = ('trajectory-depth-limit', '[Truncated]', '[Malformed diagnostic JSON redacted]')


def js(x): return json.dumps(x, ensure_ascii=False, separators=(',', ':'))
def sha_bytes(x): return hashlib.sha256(x).hexdigest()
def digest(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()
def readrows(p):
    op = gzip.open if str(p).endswith('.gz') else open
    with op(p, 'rt', encoding='utf-8-sig') as f:
        for line in f:
            if line.strip(): yield json.loads(line)
def save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def int_sha(ids):
    x = array('I', ids)
    if sys.byteorder != 'little': x.byteswap()
    return sha_bytes(x.tobytes())
def gzwrite(f, x): f.write(js(x)+'\n')


class CausalCompiler:
    """Reusable renderer for OpenAI messages/tools and explicit owned targets.

    owned_specs maps a message index to metadata including mechanical_usable.
    Actual original reasoning is only the explicit reasoning_content string.
    Ordinary body text is never reclassified as original reasoning.
    """
    def __init__(self, assets: Path):
        from transformers import AutoTokenizer
        from transformers.utils.chat_template_utils import _compile_jinja_template
        self.assets = assets
        self.asset_hashes = {}
        names = ('tokenizer_config.json', 'tokenizer.json', 'vocab.json', 'merges.txt', 'generation_config.json')
        for key in ('primary_14b', 'control_8b'):
            self.asset_hashes[key] = {n:digest(assets/key/n) for n in names}
        if self.asset_hashes['primary_14b'] != self.asset_hashes['control_8b']:
            raise ValueError('tokenizer_assets_not_byte_identical')
        self.tokenizers = {k:AutoTokenizer.from_pretrained(assets/k, local_files_only=True, trust_remote_code=False)
                           for k in ('primary_14b', 'control_8b')}
        self.original = self.tokenizers['primary_14b'].chat_template
        self.template = self.original.replace('{%- if loop.index0 > ns.last_query_index %}', '{%- if true %}')
        self.template = self.template.replace('{%- if loop.last or (not loop.last and reasoning_content) %}', '{%- if true %}')
        self.template = self.template.replace("reasoning_content.strip('\\n')", 'reasoning_content')
        self.template = self.template.replace("content.lstrip('\\n')", 'content')
        # Explicit empty reasoning_content avoids the official fallback which
        # interprets a literal </think> in generated code/documentation as CoT.
        self.instrumented = self.template.replace('{%- elif message.role == "assistant" %}',
            '{%- elif message.role == "assistant" %}{%- generation -%}')
        self.instrumented = self.instrumented.replace('{%- elif message.role == "tool" %}',
            '{%- endgeneration -%}{%- elif message.role == "tool" %}')
        if self.template == self.original or self.instrumented == self.template:
            raise ValueError('unexpected_official_template_cannot_instrument')
        self.compiled = _compile_jinja_template(self.instrumented)
        self.plain_compiled = _compile_jinja_template(self.template)
        self.proof = {'official_template_sha256':sha_bytes(self.original.encode()),
                      'causal_template_sha256':sha_bytes(self.template.encode()),
                      'instrumented_template_sha256':sha_bytes(self.instrumented.encode()),
                      'variant_is_not_unmodified_official_template':True,
                      'future_inference_api_must_use_same_causal_variant':True,
                      'inference_api_variant_already_integrated':False,
                      'two_tokenizer_asset_sets_byte_identical':True,
                      'asset_sha256':self.asset_hashes,
                      'independent_second_tokenizer_calls':0,
                      'reuse_rule':'identical assets + identical rendered bytes; independent canary then every 97th window'}

    def compile_messages(self, messages, tools, owned_specs, independent=False):
        from transformers.utils.chat_template_utils import _render_with_assistant_indices
        m = []
        for x in messages:
            y = dict(x)
            if y.get('role') == 'assistant':
                # Do not mine reasoning from ordinary content delimiters.
                y['reasoning_content'] = y.get('reasoning_content') if isinstance(y.get('reasoning_content'), str) else ''
            m.append(y)
        kwargs = dict(self.tokenizers['primary_14b'].special_tokens_map)
        kwargs['enable_thinking'] = False
        rendered, generation_indices = _render_with_assistant_indices(
            self.compiled, m, tools or None, None, False, **kwargs)
        plain = self.plain_compiled.render(messages=m, tools=tools or None, documents=None,
                                           add_generation_prompt=False, **kwargs)
        if plain != rendered: raise ValueError('instrumentation_changed_rendered_bytes')
        indices = [i for i,x in enumerate(m) if x.get('role') == 'assistant']
        if len(indices) != len(generation_indices): raise ValueError('assistant_span_count_mismatch')
        tok = self.tokenizers['primary_14b'](rendered, add_special_tokens=False, return_offsets_mapping=True)
        ids, offsets = tok['input_ids'], tok['offset_mapping']
        if independent:
            other = self.tokenizers['control_8b'](rendered, add_special_tokens=False, return_offsets_mapping=True)
            if ids != other['input_ids'] or offsets != other['offset_mapping']:
                raise ValueError('independent_tokenizer_pair_mismatch')
            self.proof['independent_second_tokenizer_calls'] += 1
        starts = [p[0] for p in offsets]
        ends = [p[1] for p in offsets]
        def interval(a,b):
            if a >= b:return None
            lo = bisect_right(ends,a)
            hi = bisect_left(starts,b)
            if lo >= hi:return None
            if any(not(a <= s and e <= b and e > s) for s,e in offsets[lo:hi]):
                raise ValueError('token_crosses_segment_boundary')
            return [lo,hi]
        spans=[]; target_meta=[]; subtoken_counts=Counter(); message_ends=[]
        for i, (a,b) in zip(indices,generation_indices):
            chunk=rendered[a:b]
            if not chunk.startswith(HEADER) or not chunk.endswith(END):raise ValueError('assistant_control_boundary_mismatch')
            body_a=a+len(HEADER)
            thought=m[i]['reasoning_content']
            content=m[i].get('content') or ''
            expected_prefix=HEADER+THINK_OPEN+thought+THINK_CLOSE+content
            if not chunk.startswith(expected_prefix):raise ValueError('original_fields_not_preserved_in_variant')
            ra=body_a+len(THINK_OPEN); rb=ra+len(thought)
            ca=rb+len(THINK_CLOSE); cb=ca+len(content)
            end_a=b-len(END)
            ranges=[]
            # Format controls and every original payload get distinct labels.
            if ra>body_a:ranges.append((body_a,ra,'F',0.2))
            if rb>ra:ranges.append((ra,rb,'R',1.0))
            if ca>rb:ranges.append((rb,ca,'F',0.2))
            body_class='E' if m[i].get('tool_calls') else 'D'
            if cb>ca:ranges.append((ca,cb,body_class,1.0))
            if end_a>cb:ranges.append((cb,end_a,'A',1.0))
            ranges.append((end_a,b,'F',0.2))
            spec=dict(owned_specs.get(i,{})); admissible=spec.get('mechanical_usable') is True
            # Cross-boundary merges entirely inside assistant output are allowed
            # and classified MIXED; never label role/header/input tokens.
            full=interval(body_a,b)
            converted=[]
            if admissible and full:
                for lo in range(full[0],full[1]):
                    s,e=offsets[lo]
                    labels=[(cl,w) for x,y,cl,w in ranges if s<y and e>x]
                    if not labels:raise ValueError('unclassified_owned_token')
                    cl,w=labels[0] if len({x[0] for x in labels})==1 else (
                        ('R_BOUNDARY_MIXED',1.0) if any(x[0]=='R' for x in labels) else ('MIXED',1.0))
                    if converted and converted[-1][2:]==[cl,w] and converted[-1][1]==lo:converted[-1][1]=lo+1
                    else:converted.append([lo,lo+1,cl,w])
                spans.extend(converted)
                for lo,hi,cl,w in converted:subtoken_counts[cl]+=hi-lo
            ending=bisect_left(starts,b)
            message_ends.append((i,ending))
            target_meta.append({**spec,'message_index':i,'rendered_assistant_span':[a,b],
                                'response_end_token_exclusive':ending,
                                'owned_supervision_spans':converted,'supervised_tokens':sum(z[1]-z[0] for z in converted),
                                'original_reasoning_characters':len(thought),
                                'ordinary_visible_text_characters':len(content),
                                'body_text_kind':'observed_visible_explanation' if body_class=='E' else 'ordinary_response_or_decision_not_gold'})
        # Check global mask ownership, explicit sentinel, role/input exclusion.
        last=0
        for lo,hi,cl,w in spans:
            if not 0<=lo<hi<=len(ids) or lo<last:raise ValueError('overlapping_or_invalid_loss_spans')
            last=hi
        return {'input_ids':ids,'supervision_spans':spans,'targets':target_meta,
                'total_tokens':len(ids),'supervised_tokens':sum(z[1]-z[0] for z in spans),
                'supervised_tokens_by_component':dict(subtoken_counts),
                'input_ids_sha256_u32le':int_sha(ids),
                'supervision_spans_sha256':sha_bytes(js(spans).encode()),
                'rendered_sha256':sha_bytes(rendered.encode()),
                'assistant_generation_spans':generation_indices,
                'second_tokenizer_independently_called':independent,
                'tokenizer_pair_proof':'independent_call_equal' if independent else 'byte_identical_assets_and_deterministic_reuse',
                'label_definition':'labels=input_ids only in owned supervision_spans, otherwise -100; span component weight explicit',
                'label_ignore_index':-100}


def valid_registry(raw):
    if isinstance(raw,dict):raw=raw.get('tools',[])
    registry={}; issues=Counter()
    for x in raw if isinstance(raw,list) else []:
        if not isinstance(x,dict):issues['non_dictionary_tool_placeholders']+=1;continue
        f=x.get('function',x)
        if not isinstance(f,dict) or not isinstance(f.get('name'),str) or not isinstance(f.get('parameters'),dict):
            issues['incomplete_tool_schema']+=1;continue
        if any(y in js(f) for y in INCOMPLETE):issues['explicitly_truncated_tool_schema']+=1;continue
        registry[f['name']]={'type':'function','function':f}
    return registry,dict(issues)


def load_schema_index(bundle):
    refs={}
    with (bundle/'archive/file_index.jsonl').open(encoding='utf-8-sig') as f:
        for line in f:
            if '/tools.json' not in line:continue
            r=json.loads(line)
            if r['logical_path'].endswith('/tools.json'):refs[r['logical_path']]=r
    return refs


def native_messages(r):
    messages=[]; native_indices=[]; issues=Counter()
    system=r.get('system')
    if isinstance(system,str) and system:messages.append({'role':'system','content':system});native_indices.append(None)
    for index,m in enumerate(r['messages']):
        role=m.get('role'); content=m.get('content',''); text='';calls=[]
        if isinstance(content,str):text=content
        elif isinstance(content,list):
            for block in content:
                if not isinstance(block,dict):issues['nontext_native_block']+=1;continue
                kind=block.get('type')
                if kind=='text':text+=str(block.get('text',''))
                elif kind=='toolCall':calls.append({'id':block.get('id'),'type':'function','function':{
                    'name':block.get('name'),'arguments':js(block.get('arguments',{}))}})
                elif kind in ('thinking','reasoning'):
                    # Future native recovery may add real recorded fields.
                    pass
                else:issues['nontext_native_block']+=1
        else:issues['nontext_native_content']+=1
        if role in ('toolResult','tool'):
            out={'role':'tool','tool_call_id':m.get('toolCallId'),'content':text}
        elif role in ('user','system','assistant'):
            out={'role':role,'content':text}
            if calls:out['tool_calls']=calls
            if role=='assistant':
                reasoning=m.get('reasoning_content')
                if not isinstance(reasoning,str):
                    reasoning=''.join(str(x.get('thinking',x.get('text',''))) for x in content
                        if isinstance(x,dict) and x.get('type') in ('thinking','reasoning')) if isinstance(content,list) else ''
                out['reasoning_content']=reasoning or ''
        else:issues['unsupported_native_role']+=1;continue
        messages.append(out);native_indices.append(index)
    return messages,native_indices,dict(issues)


def formal_status(r):
    s=js(r.get('messages',[])); removed=0
    for p in POLICIES:removed+=s.count(p);s=s.replace(p,'')
    remaining=FORMAL.findall(s)
    return {'status':'unresolved_formal_marker_hold' if remaining else 'policy_mentions_only' if removed else 'no_marker_detected',
            'remaining_marker_occurrences':len(remaining),'policy_occurrences':removed,
            'semantic_nonoverlap_proven':False}


def owned_native(r,messages,native_indices,registry,base_issues,marker):
    from jsonschema import Draft202012Validator
    results={};duplicates=set()
    for i,m in enumerate(r['messages']):
        if m.get('role') in ('toolResult','tool'):
            cid=m.get('toolCallId')
            if cid in results:duplicates.add(cid)
            results[cid]=m
    seen=set();pending=set();history_missing_schemas=set();context_pairing_issue=False
    owned={}; system_ok=isinstance(r.get('system'),str) and bool(r['system'])
    for j,(m,ni) in enumerate(zip(messages,native_indices)):
        role=m['role']
        if role=='tool':
            cid=m.get('tool_call_id')
            if cid not in pending:context_pairing_issue=True
            else:pending.remove(cid)
            continue
        if role not in ('assistant',):continue
        source=r['messages'][ni];calls=m.get('tool_calls',[]);nonempty=bool(calls or (m.get('content') or '').strip() or m.get('reasoning_content'))
        reasons=[]; flags=[]
        if not nonempty:reasons.append('empty_assistant_target')
        if not system_ok:reasons.append('original_system_prompt_not_recovered')
        if r.get('native_verified') is not True:reasons.append('historical_runtime_not_verified_native')
        if r.get('context_fully_recoverable') is not True:reasons.append('canonical_context_parse_incomplete')
        if base_issues:reasons.append('text_projection_has_unsupported_native_content')
        if marker['status']=='unresolved_formal_marker_hold':reasons.append('unresolved_formal_marker_hold')
        if pending or context_pairing_issue:reasons.append('historical_tool_pairing_incomplete')
        target_names=[]
        for call in calls:
            cid=call.get('id'); fn=call.get('function',{});name=fn.get('name');target_names.append(name)
            if not isinstance(cid,str) or not cid or cid in seen:reasons.append('target_call_id_missing_or_duplicate')
            if name not in registry:reasons.append('current_tool_schema_missing')
            else:
                try:
                    args=json.loads(fn['arguments']) if isinstance(fn.get('arguments'),str) else fn.get('arguments')
                    error=next(Draft202012Validator(registry[name]['function']['parameters']).iter_errors(args),None)
                    if error is not None:reasons.append('current_tool_arguments_schema_invalid')
                except Exception:reasons.append('current_tool_schema_or_arguments_unparseable')
            outcome=results.get(cid)
            if cid in duplicates:reasons.append('current_tool_result_duplicate')
            if outcome is None:reasons.append('current_tool_result_not_recorded')
            elif outcome.get('isError') is True or (isinstance(outcome.get('details'),dict) and
                outcome['details'].get('exitCode') not in (None,0)):
                reasons.append('observed_tool_error_requires_probe_or_repair_review')
            if name not in registry:history_missing_schemas.add(str(name))
            if isinstance(cid,str):seen.add(cid);pending.add(cid)
        if history_missing_schemas:flags.append('historical_tool_schema_gap_observed_context_preserved')
        owned[j]={'id':sha_bytes((r['episode_id']+':'+str(ni)).encode())[:24],
                  'source_message_index':ni,'source_event_line':r.get('source_event_lines',[None]*len(r['messages']))[ni],
                  'source_message_sha256':sha_bytes(js(source).encode()),'nonempty':nonempty,
                  'mechanical_usable':not reasons,'mechanical_reasons':sorted(set(reasons)),
                  'context_flags':flags,'target_tool_names':target_names,
                  'semantic_approved':False,'human_gold':False,
                  'training_tier':'mechanical_teacher_silver_requires_semantic_calibration' if not reasons else 'held_or_context_only',
                  'reasoning_origin':'original_recorded_field' if m.get('reasoning_content') else
                      'observed_visible_explanation' if calls and m.get('content') else 'none',
                  'full_autonomous_controller_demonstration':False}
    return owned


def prefix_record(record, max_tokens):
    # Choose an actual complete assistant boundary; this is explicitly a prefix
    # view, never reported as a complete-stage 32K success.
    possible=[t['response_end_token_exclusive'] for t in record['targets']
              if t['response_end_token_exclusive']<=max_tokens and t['supervised_tokens']>0]
    if not possible:return None
    end=max(possible)
    if end==record['total_tokens']:return None
    targets=[t for t in record['targets'] if t['response_end_token_exclusive']<=end]
    spans=[z for z in record['supervision_spans'] if z[1]<=end]
    ids=record['input_ids'][:end]
    component_counts=Counter()
    for lo,hi,component,weight in spans:component_counts[component]+=hi-lo
    return {**record,'view':'explicit_causal_stage_prefix32k_not_complete_stage','input_ids':ids,
            'total_tokens':end,'targets':targets,'supervision_spans':spans,
            'supervised_tokens':sum(z[1]-z[0] for z in spans),'input_ids_sha256_u32le':int_sha(ids),
            'supervised_tokens_by_component':dict(component_counts),
            'supervision_spans_sha256':sha_bytes(js(spans).encode()),
            'full_parent_total_tokens':record['total_tokens'],'stage_complete_in_this_view':False,
            'native_target_owner_view':'this_prefix_only; full_overlength_is_archive_not_simultaneous_training'}


def compile_scope(compiler,bundle,source,out,scope,schema_refs,limit=None):
    out.mkdir(parents=True,exist_ok=False);start=time.monotonic();counts=Counter();by_stage=defaultdict(Counter);failures=Counter()
    core,core_issues=valid_registry(json.loads((bundle/'protocol/native_coding_tools_97a0.json').read_text(encoding='utf-8-sig')))
    cache={};source_hash=digest(source)
    names=('full_stage_records.jsonl.gz','prefix32k_records.jsonl.gz','target_inventory.jsonl.gz','episode_failures.jsonl.gz')
    streams={n:gzip.open(out/n,'wt',encoding='utf-8',newline='\n',compresslevel=3) for n in names}
    try:
        for ordinal,r in enumerate(readrows(source),1):
            if limit and ordinal>limit:break
            stage=r.get('kind','unknown');c=by_stage[stage];counts['sessions_seen']+=1;c['sessions_seen']+=1
            try:
                registry={};refs=[];schema_issues={};ref=schema_refs.get(r.get('tools_definition_path',''))
                if ref:
                    key=ref['sha256']
                    if key not in cache:
                        p=bundle/'archive'/ref['object']
                        if not p.is_file():p=bundle/ref['object']
                        if digest(p)!=key:raise ValueError('schema_cas_hash_mismatch')
                        cache[key]=valid_registry(json.loads(p.read_text(encoding='utf-8-sig')))
                    registry.update(cache[key][0]);schema_issues=cache[key][1]
                    refs.append({'source':'recorded_episode_schema','sha256':key,'logical_path':ref['logical_path']})
                if r.get('native_verified') is True:
                    for name,definition in core.items():registry.setdefault(name,definition)
                    refs.append({'source':'fixed_97a0_core_schema_recovery','sha256':digest(bundle/'protocol/native_coding_tools_97a0.json'),
                                 'is_full_original_tool_access_policy':False})
                messages,indices,issues=native_messages(r);marker=formal_status(r)
                owned=owned_native(r,messages,indices,registry,issues,marker)
                counts['assistant_positions']+=len(owned);c['assistant_positions']+=len(owned)
                for t in owned.values():
                    counts['nonempty_targets']+=t['nonempty'];c['nonempty_targets']+=t['nonempty']
                    counts['mechanically_usable_targets_before_length']+=t['mechanical_usable'];c['mechanically_usable_targets_before_length']+=t['mechanical_usable']
                    for reason in t['mechanical_reasons']:failures[reason]+=1
                result=compiler.compile_messages(messages,list(registry.values()),owned,
                    independent=ordinal<=64 or ordinal%97==0)
                record={'schema_version':'wrd-causal-native-process-compiled-v4','id':r['episode_id'],
                        'episode_id':r['episode_id'],'kind':stage,'scope':scope,
                        'view':'complete_native_stage_causal_serialization',
                        'stage_complete_in_this_view':True,'full_autonomous_controller_demonstration':False,
                        'historical_condition':'fixed_native' if r.get('native_verified') else 'historical_unverified_runtime',
                        'source_session_ordinal_1based':ordinal,'source_sessions_sha256':source_hash,
                        'source_tools_schema_refs':refs,'original_tool_catalog_completeness':schema_issues,
                        'native_tool_history_not_deleted_to_fit_core7':True,
                        'tools':list(registry.values()),'marker_audit':marker,'text_projection_issues':issues,
                        'semantic_approved':False,'human_gold':False,'training_admitted':False,
                        'mechanical_teacher_silver_available':result['supervised_tokens']>0,
                        'publication_approved':scope=='public','controlled_body_must_not_be_automatically_published':scope!='public',
                        'actual_original_reasoning_not_replaced_by_summary':True,
                        'serialization':compiler.proof['causal_template_sha256'],**result}
                counts['sessions_compiled']+=1;c['sessions_compiled']+=1
                counts['processed_full_stage_tokens']+=record['total_tokens'];c['processed_full_stage_tokens']+=record['total_tokens']
                counts['candidate_supervised_tokens_before_length']+=record['supervised_tokens']
                for cl,n in record['supervised_tokens_by_component'].items():counts['supervised_component_'+cl]+=n
                n=record['total_tokens']
                if n<=16384:counts['complete_stage_le16k']+=1;c['complete_stage_le16k']+=1
                if n<=32768:counts['complete_stage_le32k']+=1;c['complete_stage_le32k']+=1
                else:counts['complete_stage_over32k']+=1;c['complete_stage_over32k']+=1
                eligible_targets=[]
                for t in record['targets']:
                    if t['mechanical_usable']:
                        if t['response_end_token_exclusive']<=16384:counts['mechanical_target_causal_end_le16k']+=1;c['mechanical_target_causal_end_le16k']+=1
                        if t['response_end_token_exclusive']<=32768:counts['mechanical_target_causal_end_le32k']+=1;c['mechanical_target_causal_end_le32k']+=1
                    gzwrite(streams['target_inventory.jsonl.gz'],{'episode_id':r['episode_id'],'kind':stage,'scope':scope,
                        'full_stage_tokens':n,**t})
                record['length_bucket']='complete_le16k' if n<=16384 else 'complete_16k_to32k' if n<=32768 else 'overlength_archive'
                record['native_target_owner_view']='full_stage' if n<=32768 else 'archive_only_choose_explicit_prefix_or_future_state_view'
                gzwrite(streams['full_stage_records.jsonl.gz'],record)
                if n<=32768:
                    counts['training_window_supervised_tokens']+=record['supervised_tokens']
                    counts['training_windows_with_owned_targets']+=record['supervised_tokens']>0
                else:
                    prefix=prefix_record(record,32768)
                    if prefix:
                        gzwrite(streams['prefix32k_records.jsonl.gz'],prefix)
                        counts['explicit_prefix32k_windows']+=1
                        counts['training_window_supervised_tokens']+=prefix['supervised_tokens']
                        counts['training_windows_with_owned_targets']+=prefix['supervised_tokens']>0
            except Exception as exc:
                counts['session_compile_failures']+=1;c['session_compile_failures']+=1
                code=type(exc).__name__+':'+str(exc) if isinstance(exc,ValueError) else type(exc).__name__
                # All ValueError strings are fixed code paths, never raw data.
                failures['session_'+code]+=1
                gzwrite(streams['episode_failures.jsonl.gz'],{'episode_id':r['episode_id'],'kind':stage,'failure_code':code,
                    'source_ordinal':ordinal,'body_emitted':False})
            if ordinal%32==0:
                save(out/'progress.json',{'scope':scope,'counts':dict(counts),'elapsed_seconds':round(time.monotonic()-start,2)})
                print(js({'scope':scope,'sessions':counts['sessions_seen'],'compiled':counts['sessions_compiled'],
                          'targets':counts['assistant_positions'],'tokens':counts['processed_full_stage_tokens'],
                          'elapsed_seconds':round(time.monotonic()-start,2)}),flush=True)
    finally:
        for f in streams.values():f.close()
    report={'schema_version':'wrd-native-causal-compilation-report-v4','scope':scope,'counts':dict(counts),
            'by_stage':{k:dict(v) for k,v in by_stage.items()},'mechanical_hold_reasons':dict(failures),
            'source_sha256':source_hash,'source_unchanged':digest(source)==source_hash,
            'script_sha256':digest(Path(__file__)),'elapsed_seconds':round(time.monotonic()-start,3),
            'original_reasoning_field_count_in_this_canonical_source_expected_zero':True,
            'new_raw_reasoning_adapter_required_and_not_counted_here':True,
            'semantic_gold_created':0,'full_autonomous_chains_proven_by_this_compilation':0,
            'training_started':False,'model_weights_loaded':False,'gpu_used':False,
            'full_stage_and_explicit_prefix_coverage_separately_counted':True,
            'whole_dataset_not_declared_semantically_approved':True,
            'outputs':{n:{'sha256':digest(out/n),'bytes':(out/n).stat().st_size} for n in names}}
    save(out/'REPORT.json',report)
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--public-source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--limit',type=int);p.add_argument('--scope',choices=['controlled','public','both'],default='both');a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True);start=time.monotonic();compiler=CausalCompiler(a.assets)
    refs=load_schema_index(a.bundle);reports={}
    sources={'controlled':a.bundle/'canonical/native_episodes.jsonl.gz','public':a.public_source}
    for scope in ('controlled','public'):
        if a.scope not in ('both',scope):continue
        reports[scope]=compile_scope(compiler,a.bundle,sources[scope],a.output/('native_compiled_'+scope),scope,refs,a.limit)
    save(a.output/'CAUSAL_TEMPLATE.json',{'variant':compiler.template,'instrumented':compiler.instrumented,**compiler.proof})
    report={'schema_version':'wrd-native-pair-compilation-v4','status':'MECHANICAL_DATA_COMPILED_NOT_FULL_SEMANTIC_READINESS',
            'reports':reports,'tokenizer_equivalence_and_calls':compiler.proof,'elapsed_seconds':round(time.monotonic()-start,3),
            'training_started':False,'script_sha256':digest(Path(__file__))}
    save(a.output/'NATIVE_COMPILATION_REPORT.json',report)
    print(js({'status':'completed','scopes':list(reports),'elapsed_seconds':report['elapsed_seconds'],
              'counts':{k:r['counts'] for k,r in reports.items()}}),flush=True)


if __name__=='__main__':main()
