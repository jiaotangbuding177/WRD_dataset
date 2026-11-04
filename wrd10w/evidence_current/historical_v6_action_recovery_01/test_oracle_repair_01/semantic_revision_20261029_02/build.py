"""Non-destructive oracle02: exact72char withdrawal and a real old-file backup."""
from array import array
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
os.environ['USE_TORCH']='0';os.environ['USE_TF']='0';os.environ['CUDA_VISIBLE_DEVICES']='-1'
HERE=Path(__file__).resolve().parent;RESOURCE=HERE.parent;OLD=RESOURCE/'native_projection_01';OUT=RESOURCE/'native_projection_02';ROOT=next(p for p in HERE.parents if(p/'AGENTS.md').is_file())
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(Path(p).read_bytes())
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def one(p):
    with gzip.open(p,'rt',encoding='utf-8')as f:return json.loads(next(f))
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def dump(p,v):
    with gzip.open(p,'wt',encoding='utf-8',newline='\n')as f:f.write(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n')
def binref(p,k,v):
    a=array(k,v)
    if sys.byteorder!='little':a.byteswap()
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(a.tobytes());return{'path':p.relative_to(OUT).as_posix(),'sha256':digest(p),'bytes':p.stat().st_size,'dtype':{'I':'uint32_le','q':'int64_le','f':'float32_le'}[k]}
def main():
    assert not OUT.exists();OUT.mkdir();state=OUT/'state';shutil.copytree(RESOURCE/'state_before_edit',state)
    backup=state/'inputs/previous_failed_edge_case_tests.py';shutil.copyfile(state/'outputs/validation_history/edge_case_tests.py',backup)
    source=load(RESOURCE/'SOURCE_STATE_AND_RANGES.json');excerpt=(RESOURCE/'resources/original_contiguous_cumulative_R_excerpt.txt').read_text(encoding='utf-8');excluded=deepcopy(source['mask0_exclusions'])
    text='(logs already saved: run_edge_transposed.log + edge_case_tests_run1.log)';assert excerpt[1289:1361]==text
    excluded.append({'start':1289,'end':1361,'text':text,'text_sha256':sha(text.encode()),'reason':'The two specifically named log files are not delivered in this reconstructed state. Prior source creator could write them, but that alone does not ground a state-known saved-log claim.'});excluded.sort(key=lambda x:x['start']);positive=[];p=0
    for e in excluded:
        if p<e['start']:positive.append({'start':p,'end':e['start'],'text':excerpt[p:e['start']],'text_sha256':sha(excerpt[p:e['start']].encode())})
        p=e['end']
    if p<len(excerpt):positive.append({'start':p,'end':len(excerpt),'text':excerpt[p:],'text_sha256':sha(excerpt[p:].encode())})
    rev={'schema':'wrd-oracle-exact-peer-correction-v2','parent_source_state_ranges_sha256':digest(RESOURCE/'SOURCE_STATE_AND_RANGES.json'),'parent_profile01_preserved_and_not_admitted':True,'new_withdrawal':excluded[-2]if excluded[-2]['start']==1289 else next(e for e in excluded if e['start']==1289),'mask0_exclusions':excluded,'positive_excerpt_ranges':positive,'positive_original_R_characters':sum(x['end']-x['start']for x in positive),'additional_withdrawn_original_R_characters':72,'real_readonly_input_backup':{'path':'/workspace/inputs/previous_failed_edge_case_tests.py','sha256':digest(backup),'bytes':backup.stat().st_size,'exact_full_old_test_file':True,'new_functional_state_author':'Codex curation; not claimed original025 input'},'root_main_admission':False,'ACTIVE_modified':False,'training_started':False,'script_sha256':digest(Path(__file__))};save(OUT/'SEMANTIC_REVISION.json',rev)
    files=[{'path':'/workspace/'+p.relative_to(state).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}for p in sorted(state.rglob('*'))if p.is_file()]
    prototype=one(OLD/'native_oracle.core7.raw.jsonl.gz');prefix=prototype['messages'][1]['content'].split('文件清单：\n')[0]
    phrase='当前已保存原失败返回，修订前版本仍须保留。';assert phrase in prefix
    prefix=prefix.replace(phrase,'原失败返回已保存；修订前旧测试脚本的逐字完整副本已放在 inputs/previous_failed_edge_case_tests.py，由 inputs 只读规则保全，不得覆盖它。当前只修改 outputs 中的测试脚本。')
    user=prefix+'文件清单：\n'+json.dumps(files,ensure_ascii=False,indent=2)+'\n'
    for rel in('inputs/task_contract.functional.json','outputs/validation_history/edge_case_tests.py','outputs/validation_history/previous_failed_run.json'):
        user+='\n文件 /workspace/'+rel+' 完整正文：\n<file>\n'+(state/rel).read_text(encoding='utf-8')+'\n</file>\n'
    user+='候选 scripts/run.py 已存在于清单所示路径，本步没有获得其完整正确性结论。旧测试脚本的只读完整副本已保全；请先修订这两个可定位测试预期。'
    shutil.copyfile(OLD/'TOOLS_CAPTURE_53.json',OUT/'TOOLS_CAPTURE_53.json');shutil.copyfile(OLD/'ACTIVE_FOR_DEDUP.original.json',OUT/'ACTIVE_FOR_DEDUP.original.json')
    path=ROOT/'research/data_prep/wrd_reasoning_v4/compile_native.py';spec=importlib.util.spec_from_file_location('oracle02_original_causal',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);compiler=m.CausalCompiler(ROOT/'output/20261025_wrd_training_preflight/tokenizer_assets');save(OUT/'CAUSAL_TEMPLATE.json',{'variant':compiler.template,'compiler_sha256':digest(path)})
    counts=[]
    for profile in('core7','full53'):
        raw=one(OLD/f'native_oracle.{profile}.raw.jsonl.gz');raw['id']=raw['id'].replace('oracle_01:','oracle_02:');raw['bank']='historical_test_oracle_repair_02';raw['messages'][1]['content']=user;raw['state_path']=str(state);raw['approved_field_ranges']=[{'message_index':2,'field':'reasoning_content','start':x['start'],'end':x['end'],'text_sha256':x['text_sha256']}for x in positive];raw['semantic_revision_path']=str(OUT/'SEMANTIC_REVISION.json');raw['semantic_revision_sha256']=digest(OUT/'SEMANTIC_REVISION.json');raw['original_profile01_HOLD_not_selected']=True
        dump(OUT/f'native_oracle.{profile}.raw.jsonl.gz',raw);c=compiler.compile_messages(raw['messages'],raw['tools'],{2:{'id':raw['id'],'mechanical_usable':True}},independent=True)
        rendered=compiler.plain_compiled.render(messages=raw['messages'],tools=raw['tools'],documents=None,add_generation_prompt=False,**{**compiler.tokenizers['primary_14b'].special_tokens_map,'enable_thinking':False});enc=compiler.tokenizers['primary_14b'](rendered,add_special_tokens=False,return_offsets_mapping=True);assert enc['input_ids']==c['input_ids'];targetbase=c['targets'][0]['rendered_assistant_span'][0]+len('<|im_start|>assistant\n<think>\n');ranges=[(targetbase+x['start'],targetbase+x['end'])for x in positive]
        spans=[];by=Counter()
        for lo,hi,kind,w in c['supervision_spans']:
            for i in range(lo,hi):
                a,b=enc['offset_mapping'][i]
                if kind=='A'or kind=='R'and any(x<=a<b<=y for x,y in ranges):
                    by[kind]+=1
                    if spans and spans[-1][1]==i and spans[-1][2]==kind:spans[-1][1]=i+1
                    else:spans.append([i,i+1,kind,.25])
        c.update(supervision_spans=spans,supervised_tokens=sum(by.values()),supervised_tokens_by_component=dict(by));c['targets'][0]['owned_supervision_spans']=spans;c['targets'][0]['supervised_tokens']=sum(by.values());labels=[-100]*len(c['input_ids']);weights=[0.]*len(labels)
        for a,b,k,w in spans:
            for i in range(a,b):labels[i]=c['input_ids'][i];weights[i]=.25
        c.update({k:v for k,v in raw.items()if k not in('messages','tools')});c.update(messages=raw['messages'],tools=raw['tools'],supervision_spans_sha256=sha(json.dumps(spans,ensure_ascii=False,separators=(',',':')).encode()),binary_arrays=[binref(OUT/'arrays'/profile/n,k,v)for n,k,v in[('input_ids.u32le.bin','I',c['input_ids']),('labels.i64le.bin','q',labels),('weights.f32le.bin','f',weights)]]);dump(OUT/f'native_oracle.{profile}.compiled.jsonl.gz',c);counts.append({'profile':profile,'total_tokens':c['total_tokens'],'supervised_tokens':c['supervised_tokens'],'by_component':dict(by)})
    save(OUT/'BUILD.json',{'schema':'wrd-oracle-new-state-peer-refined-actual-build-v2','status':'ACTUAL_ARRAYS_PEER_ROOT_PENDING','counts':counts,'parent01_preserved':True,'withdrawn_original_characters':72,'positive_original_R_characters':rev['positive_original_R_characters'],'backup_exact_old_test_bytes':backup.stat().st_size,'backup_sha256':digest(backup),'semantic_revision_sha256':digest(OUT/'SEMANTIC_REVISION.json'),'root_main_admission':False,'ACTIVE_modified':False,'training_started':False,'new_Agent_calls':0,'script_sha256':digest(Path(__file__))});print(json.dumps(load(OUT/'BUILD.json')))
if __name__=='__main__':main()
