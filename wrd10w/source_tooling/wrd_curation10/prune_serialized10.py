"""Preserve exact write bodies; remove only reviewed serialized-token ranges."""
from pathlib import Path
from collections import Counter,defaultdict
from copy import deepcopy
import argparse,gzip,hashlib,importlib.util,json,os,shutil
os.environ.update(USE_TORCH='0',USE_TF='0',CUDA_VISIBLE_DEVICES='-1',TOKENIZERS_PARALLELISM='false')
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hs(s):return hashlib.sha256(s.encode()).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def main(a):
 spec=importlib.util.spec_from_file_location('prune10_causal',ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 compiler=mod.CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets')
 spec=importlib.util.spec_from_file_location('prune10_recount',ROOT/'research/data_prep/wrd_curation10/admit10.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 a.out.mkdir(parents=True,exist_ok=False);report=load(a.compiled/'COMPILATION_REPORT.json');buckets=defaultdict(list);records=[];audit=[]
 for ref in report['files']:
  p=helper.verify_ref(a.compiled,ref)
  for _,row in helper.raw_rows(p):
   meta=row['original_record_metadata'];ranges=meta.get('target_code_unicode_exclusions',[])
   if ranges:
    kwargs=dict(compiler.tokenizers['primary_14b'].special_tokens_map,enable_thinking=False)
    text=compiler.plain_compiled.render(messages=row['messages'],tools=row['tools']or None,documents=None,add_generation_prompt=False,**kwargs)
    enc=compiler.tokenizers['primary_14b'](text,add_special_tokens=False,return_offsets_mapping=True);assert enc['input_ids']==row['input_ids'];offsets=enc['offset_mapping']
    assert len(row['targets'])==1;target=row['targets'][0];i=target['message_index'];calls=row['messages'][i]['tool_calls'];assert len(calls)==1
    call=calls[0];field=meta.get('target_exclusion_argument_field','content');assert (call['function']['name'],field)in {('write','content'),('exec','command')}
    args=call['function']['arguments'];assert isinstance(args,dict)
    body=args[field];assert hs(body)==meta['target_original_code_sha256'];lo,hi=target['rendered_assistant_span'];decoder=json.JSONDecoder();found=[]
    for pos in range(lo,hi):
     if text[pos]!='{':continue
     try:value,n=decoder.raw_decode(text[pos:hi])
     except ValueError:continue
     if value==args:found.append((pos,pos+n))
    assert len(found)==1;start,end=found[0];encoded=json.dumps(body,ensure_ascii=False);serialized=text[start:end];assert serialized.count(encoded)==1
    begin=start+serialized.index(encoded)+1;excluded=[]
    for x in sorted(ranges,key=lambda x:x['start']):
     aa,bb=x['start'],x['end'];assert hs(body[aa:bb])==x['text_sha256']
     aa=begin+len(json.dumps(body[:aa],ensure_ascii=False))-2;bb=begin+len(json.dumps(body[:bb],ensure_ascii=False))-2
     actual=text[aa:bb];assert actual==json.dumps(body[x['start']:x['end']],ensure_ascii=False)[1:-1]
     excluded.append({'start':aa,'end':bb,'text_sha256':hs(actual),'text':actual,'message_index':i,'field':'serialized_tool_arguments','subfield':field,'tool_call_id':call['id'],'reason':x['reason']})
    meta['serialized_tool_argument_rendered_span']={'start':start,'end':end,'text_sha256':hs(serialized)}
    meta['target_excluded_rendered_ranges']=excluded;meta['requires_exact_serialized_body_pruning_before_admission']=False
    spans=[];counts=Counter()
    for aa,bb,kind,w in row['supervision_spans']:
     for token in range(aa,bb):
      xx,yy=offsets[token]
      if any(xx<q['end']and yy>q['start']for q in excluded):continue
      if spans and spans[-1][1]==token and spans[-1][2:]==[kind,w]:spans[-1][1]=token+1
      else:spans.append([token,token+1,kind,w])
      counts[kind]+=1
    row.update(supervision_spans=spans,supervised_tokens=sum(counts.values()),supervised_tokens_by_component=dict(counts),supervision_spans_sha256=hs(js(spans)))
    target.update(owned_supervision_spans=spans,supervised_tokens=row['supervised_tokens'])
    audit.extend({'record_id':row['id'],**x}for x in excluded)
   records.append(row);buckets['16k'if row['total_tokens']<=16384 else'32k'].append((js(row)+'\n').encode())
 files=[]
 for bucket,lines in buckets.items():
  p=a.out/('followup10.train.'+bucket+'.jsonl.gz');helper.write_lines(p,lines);files.append({'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
 shutil.copyfile(a.compiled/'CAUSAL_TEMPLATE.json',a.out/'CAUSAL_TEMPLATE.json')
 result=helper.report_for(records,report,files)
 with gzip.open(a.out/'held.jsonl.gz','wb'):pass
 p=a.out/'held.jsonl.gz';result.update(held_file={'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)},exact_excluded_code_ranges=len(audit),
  pruning_source_sha256=sha(__file__),staging_only_not_root_main_admission=True,source_compilation_report_sha256=sha(a.compiled/'COMPILATION_REPORT.json'))
 helper.save(a.out/'COMPILATION_REPORT.json',result);helper.save(a.out/'EXACT_ZERO_SERIALIZED_RANGES.json',audit)
 print(js({'counts':result['counts'],'negative_body_ranges':len(audit),'not_main':True}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--compiled',type=Path,required=True);p.add_argument('--out',type=Path,required=True);main(p.parse_args())
