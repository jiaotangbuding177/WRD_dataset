"""Concatenate reviewed compiled rows without retokenizing or changing a row."""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json,shutil
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def main(a):
 spec=importlib.util.spec_from_file_location('admit09_recount_union',ROOT/'research/data_prep/wrd_curation09/admit09.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 a.out.mkdir(parents=True,exist_ok=False);seen=set();records=[];buckets={'16k':[],'32k':[]};pins=[];templates=[]
 for p in a.report:
  report=load(p);templates.append(load(p.parent/'CAUSAL_TEMPLATE.json'));pins.append({'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p),
   'causal_template_sha256':sha(p.parent/'CAUSAL_TEMPLATE.json')})
  for ref in report['files']:
   source=mod.verify_ref(p.parent,ref)
   for line,r in mod.raw_rows(source):
    assert r['id']not in seen;seen.add(r['id']);records.append(r);buckets['16k'if r['total_tokens']<=16384 else'32k'].append(line)
 geometry=[{k:v for k,v in t.items()if k!='independent_second_tokenizer_calls'}for t in templates]
 assert all(t==geometry[0]for t in geometry),'ACTUAL_TEMPLATE_OR_TOKENIZER_ASSETS_DIFFER'
 files=[]
 for bucket,lines in buckets.items():
  if not lines:continue
  p=a.out/('curation09.train.'+bucket+'.jsonl.gz');mod.write_lines(p,lines);files.append({'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
 template=dict(templates[0]);template['independent_second_tokenizer_calls']=sum(t['independent_second_tokenizer_calls']for t in templates)
 template['concatenation_tokenizer_calls']=0;mod.save(a.out/'CAUSAL_TEMPLATE.json',template)
 report=mod.report_for(records,load(a.report[0]),files)
 report.update(status='CONCATENATED_ACTUAL_ROWS_NOT_ROOT_MAIN_ADMISSION',source_compilation_reports=pins,
  tokenizer_calls_this_concatenation=0,byte_preserved_uncompressed_rows=True,script_sha256=sha(__file__))
 with gzip.open(a.out/'held.jsonl.gz','wb'):pass
 p=a.out/'held.jsonl.gz';report['held_file']={'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}
 mod.save(a.out/'COMPILATION_REPORT.json',report)
 mod.save(a.out/'ROW_ORIGIN_PINS.json',{'source_reports':pins,'record_ids':sorted(seen),'rows_unmodified':True,'training_started':False})
 print(json.dumps({'actual_counts':report['counts'],'record_count':len(seen),'report_sha256':sha(a.out/'COMPILATION_REPORT.json')}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path,action='append',required=True);p.add_argument('--out',type=Path,required=True);main(p.parse_args())
